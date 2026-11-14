import logging
import os
from collections.abc import Callable
from typing import Annotated
from uuid import UUID, uuid4

from fastapi import Depends, FastAPI, Header, Query, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy import Engine

from vaultix.api import contracts as c
from vaultix.application.identity import (
    PUBLIC_USER,
    authenticate,
    create_user,
    current_user,
    set_customer_active,
    token_hash,
)
from vaultix.application.lab import Scenario, run_scenario
from vaultix.application.ledger import audit, open_account, transfer
from vaultix.domain.rules import BusinessError, Role
from vaultix.infrastructure.db import connect_engine, many, one, query

COOKIE = "vaultix_session"
log = logging.getLogger("vaultix")


def create_app(
    engine: Engine,
    *,
    secure: bool = True,
    after_post: Callable[[], None] | None = None,
    lab_engine: Engine | None = None,
) -> FastAPI:
    app = FastAPI(
        title="Vaultix",
        version="1.0.0",
        docs_url="/api/docs",
        redoc_url=None,
        openapi_url="/api/openapi.json",
        responses={
            code: {"model": c.ErrorBody} for code in (401, 403, 404, 409, 422, 500)
        },
    )

    @app.middleware("http")
    async def request_context(request: Request, call_next):
        request.state.id = uuid4()
        try:
            origin = request.headers.get("origin")
            if origin and request.method in {"POST", "PATCH", "PUT", "DELETE"}:
                expected_origin = os.getenv(
                    "PUBLIC_ORIGIN", str(request.base_url).rstrip("/")
                )
                if origin != expected_origin:
                    raise BusinessError(403, "ORIGIN_FORBIDDEN")
            response = await call_next(request)
        except BusinessError as error:
            response = JSONResponse({"code": error.code}, error.status)
        except Exception as error:
            log.error(
                "request_failed id=%s exception=%s",
                request.state.id,
                type(error).__name__,
            )
            response = JSONResponse({"code": "INTERNAL_ERROR"}, 500)
        response.headers["X-Request-ID"] = str(request.state.id)
        response.headers["Cache-Control"] = "no-store"
        return response

    @app.exception_handler(BusinessError)
    async def handle_business(request: Request, error: BusinessError):
        return JSONResponse({"code": error.code}, error.status)

    @app.exception_handler(RequestValidationError)
    async def handle_validation(request: Request, error: RequestValidationError):
        return JSONResponse({"code": "INVALID_INPUT"}, 422)

    def actor(request: Request):
        return current_user(engine, request.cookies.get(COOKIE))

    def staff(user: dict = Depends(actor)):
        if user["role"] == Role.CUSTOMER:
            raise BusinessError(403, "ROLE_FORBIDDEN")
        return user

    def admin(user: dict = Depends(staff)):
        if user["role"] != Role.ADMIN:
            raise BusinessError(403, "ROLE_FORBIDDEN")
        return user

    @app.get("/api/health")
    def health():
        with engine.connect() as conn:
            query(conn, "SELECT id FROM limits WHERE id=1").scalar_one()
        return {"status": "ok"}

    @app.post("/api/login", status_code=204)
    def login(payload: c.Credentials, request: Request, response: Response):
        token = authenticate(
            engine, payload.username, payload.password, request.state.id
        )
        response.set_cookie(
            COOKIE,
            token,
            max_age=28800,
            httponly=True,
            secure=secure,
            samesite="strict",
            path="/api",
        )

    @app.post("/api/logout", status_code=204)
    def logout(request: Request, response: Response, user: dict = Depends(actor)):
        with engine.begin() as conn:
            query(
                conn,
                "DELETE FROM sessions WHERE token_hash=:hash",
                hash=token_hash(request.cookies[COOKIE]),
            )
            audit(conn, request.state.id, "LOGOUT", "SUCCESS", user["id"])
        response.delete_cookie(COOKIE, path="/api")

    @app.get("/api/me", response_model=c.User)
    def me(user: dict = Depends(actor)):
        return user

    def owner_scope(user: dict) -> UUID | None:
        return user["id"] if user["role"] == Role.CUSTOMER else None

    @app.get("/api/accounts", response_model=list[c.Account])
    def accounts(user: dict = Depends(actor)):
        with engine.connect() as conn:
            return many(
                conn,
                """SELECT * FROM account_balances WHERE owner_id IS NOT NULL
                      AND (CAST(:owner AS uuid) IS NULL OR owner_id=:owner) ORDER BY name, id""",
                owner=owner_scope(user),
            )

    @app.get("/api/accounts/{account_id}", response_model=c.Account)
    def account(account_id: UUID, user: dict = Depends(actor)):
        with engine.connect() as conn:
            row = one(
                conn,
                """SELECT * FROM account_balances WHERE id=:id AND owner_id IS NOT NULL
                    AND (CAST(:owner AS uuid) IS NULL OR owner_id=:owner)""",
                id=account_id,
                owner=owner_scope(user),
            )
        if row is None:
            raise BusinessError(404, "ACCOUNT_NOT_FOUND")
        return row

    @app.post("/api/accounts", response_model=c.Account, status_code=201)
    def create_account(
        payload: c.NewAccount, request: Request, user: dict = Depends(staff)
    ):
        with engine.begin() as conn:
            row = open_account(
                conn, payload.owner_id, payload.name, payload.funding_minor, user["id"]
            )
            audit(
                conn, request.state.id, "ACCOUNT_OPEN", "SUCCESS", user["id"], row["id"]
            )
            return row

    @app.patch("/api/accounts/{account_id}", response_model=c.Account)
    def change_status(
        account_id: UUID,
        payload: c.AccountChange,
        request: Request,
        user: dict = Depends(staff),
    ):
        with engine.begin() as conn:
            changed = query(
                conn,
                """UPDATE accounts SET status=:status WHERE id=:id
                                  AND owner_id IS NOT NULL RETURNING id""",
                id=account_id,
                status=payload.status,
            ).scalar_one_or_none()
            if changed is None:
                raise BusinessError(404, "ACCOUNT_NOT_FOUND")
            audit(
                conn,
                request.state.id,
                "ACCOUNT_STATUS",
                payload.status,
                user["id"],
                account_id,
            )
            return one(
                conn, "SELECT * FROM account_balances WHERE id=:id", id=account_id
            )

    @app.post(
        "/api/transfers",
        response_model=c.TransferResult,
        status_code=201,
        responses={
            201: {"headers": {"Idempotency-Replayed": {"schema": {"type": "boolean"}}}}
        },
    )
    def post_transfer(
        payload: c.Transfer,
        request: Request,
        response: Response,
        key: Annotated[
            str, Header(alias="Idempotency-Key", pattern=r"^[A-Za-z0-9._-]{1,128}$")
        ],
        user: dict = Depends(actor),
    ):
        try:
            result = transfer(
                engine,
                user,
                payload.source_id,
                payload.destination_id,
                payload.amount_minor,
                key,
                request.state.id,
                after_post=after_post,
            )
        except Exception:
            with engine.begin() as conn:
                audit(conn, request.state.id, "TRANSFER", "INTERNAL_ERROR", user["id"])
            raise
        headers = {"Idempotency-Replayed": str(result.replay).lower()}
        if result.status != 201:
            return JSONResponse(result.body, result.status, headers=headers)
        response.headers.update(headers)
        return result.body

    visible = """(CAST(:owner AS uuid) IS NULL OR EXISTS (
        SELECT 1 FROM accounts a WHERE a.owner_id=:owner AND a.id IN (j.source_id, j.destination_id)
    ))"""

    @app.get("/api/transfers", response_model=list[c.Journal])
    def history(
        account_id: UUID | None = None,
        limit: Annotated[int, Query(ge=1, le=100)] = 50,
        offset: Annotated[int, Query(ge=0)] = 0,
        user: dict = Depends(actor),
    ):
        if account_id is not None:
            account(account_id, user)
        with engine.connect() as conn:
            return many(
                conn,
                f"""SELECT j.* FROM journals j WHERE {visible}
                      AND (CAST(:account AS uuid) IS NULL OR :account IN (source_id,destination_id))
                      ORDER BY created_at DESC, id DESC LIMIT :limit OFFSET :offset""",
                owner=owner_scope(user),
                account=account_id,
                limit=limit,
                offset=offset,
            )

    @app.get("/api/transfers/{journal_id}", response_model=c.JournalDetail)
    def detail(journal_id: UUID, user: dict = Depends(actor)):
        with engine.connect() as conn:
            row = one(
                conn,
                f"SELECT j.* FROM journals j WHERE {visible} AND id=:id",
                id=journal_id,
                owner=owner_scope(user),
            )
            if row is None:
                raise BusinessError(404, "TRANSFER_NOT_FOUND")
            row["entries"] = many(
                conn,
                """SELECT side, account_id, amount FROM entries
                                        WHERE journal_id=:id ORDER BY side DESC""",
                id=journal_id,
            )
            return row

    @app.get("/api/users", response_model=list[c.User])
    def users(user: dict = Depends(staff)):
        with engine.connect() as conn:
            return many(
                conn,
                f"""SELECT {PUBLIC_USER} FROM users
                       WHERE :all_users OR role='CUSTOMER' ORDER BY username""",
                all_users=user["role"] == Role.ADMIN,
            )

    @app.post("/api/users", response_model=c.User, status_code=201)
    def add_user(payload: c.NewUser, request: Request, user: dict = Depends(admin)):
        return create_user(engine, user["id"], request.state.id, **payload.model_dump())

    @app.patch("/api/users/{user_id}", response_model=c.User)
    def change_user(
        user_id: UUID,
        payload: c.UserChange,
        request: Request,
        user: dict = Depends(admin),
    ):
        return set_customer_active(
            engine, user["id"], request.state.id, user_id, payload.active
        )

    @app.get("/api/limits", response_model=c.Limits)
    def get_limits(user: dict = Depends(actor)):
        with engine.connect() as conn:
            return one(conn, "SELECT per_transfer, per_day FROM limits WHERE id=1")

    @app.put("/api/limits", response_model=c.Limits)
    def change_limits(payload: c.Limits, request: Request, user: dict = Depends(admin)):
        with engine.begin() as conn:
            query(
                conn,
                "UPDATE limits SET per_transfer=:per_transfer, per_day=:per_day WHERE id=1",
                **payload.model_dump(),
            )
            audit(conn, request.state.id, "LIMITS_UPDATE", "SUCCESS", user["id"])
            return payload

    @app.get("/api/audit", response_model=list[c.Audit])
    def events(
        limit: Annotated[int, Query(ge=1, le=100)] = 50,
        offset: Annotated[int, Query(ge=0)] = 0,
        user: dict = Depends(staff),
    ):
        with engine.connect() as conn:
            return many(
                conn,
                """SELECT * FROM audit ORDER BY created_at DESC, id DESC
                              LIMIT :limit OFFSET :offset""",
                limit=limit,
                offset=offset,
            )

    @app.post("/api/lab/{scenario}", response_model=c.LabResult)
    def lab(scenario: Scenario, request: Request, user: dict = Depends(admin)):
        if lab_engine is None:
            raise BusinessError(403, "LAB_DISABLED")
        result = run_scenario(lab_engine, scenario)
        with engine.begin() as conn:
            audit(
                conn,
                request.state.id,
                "LAB_RUN",
                "PASS" if result["passed"] else "FAIL",
                user["id"],
                result["id"],
            )
        return result

    return app


def configured_app():
    engine = connect_engine()
    demo = os.getenv("APP_ENV") == "demo"
    lab_url = os.getenv("LAB_DATABASE_URL")
    lab_engine = connect_engine(lab_url) if demo and lab_url else None
    if lab_engine is not None:
        # Compare server identity and database name, including aliases of the same URL.
        sql = "SELECT current_database(), inet_server_addr(), inet_server_port()"
        with engine.connect() as primary, lab_engine.connect() as sandbox:
            if query(primary, sql).one() == query(sandbox, sql).one():
                raise RuntimeError("The lab requires a separate database")
    return create_app(engine, secure=not demo, lab_engine=lab_engine)


app = configured_app()
