import hashlib
import json
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from sqlalchemy import Connection, Engine

from vaultix.domain.rules import BusinessError, Role, Status, validate_debit
from vaultix.infrastructure.db import many, one, query

CLEARING = UUID(int=1)


@dataclass(frozen=True)
class Receipt:
    status: int
    body: dict
    replay: bool = False


def audit(
    conn: Connection,
    request_id: UUID,
    action: str,
    result: str,
    actor_id: UUID | None = None,
    object_id: UUID | None = None,
) -> None:
    query(
        conn,
        """INSERT INTO audit(request_id, action, result, actor_id, object_id)
                VALUES (:request_id, :action, :result, :actor_id, :object_id)""",
        request_id=request_id,
        action=action,
        result=result,
        actor_id=actor_id,
        object_id=object_id,
    )


def post(
    conn: Connection,
    source: UUID,
    destination: UUID,
    amount: int,
    actor_id: UUID | None,
    kind: str,
    created_at: datetime,
) -> dict:
    journal = one(
        conn,
        """INSERT INTO journals(kind, actor_id, source_id, destination_id,
                       amount, created_at) VALUES (:kind, :actor, :source, :destination,
                       :amount, :created_at) RETURNING *""",
        kind=kind,
        actor=actor_id,
        source=source,
        destination=destination,
        amount=amount,
        created_at=created_at,
    )
    assert journal is not None
    query(
        conn,
        """INSERT INTO entries(journal_id, side, account_id, amount)
                VALUES (:journal, 'DEBIT', :source, :amount),
                       (:journal, 'CREDIT', :destination, :amount)""",
        journal=journal["id"],
        source=source,
        destination=destination,
        amount=amount,
    )
    return journal


def open_account(
    conn: Connection, owner: UUID, name: str, funding: int, actor_id: UUID | None
) -> dict:
    customer = one(
        conn,
        "SELECT id FROM users WHERE id=:id AND role='CUSTOMER' AND active FOR SHARE",
        id=owner,
    )
    if customer is None:
        raise BusinessError(404, "CUSTOMER_NOT_FOUND")
    account = one(
        conn,
        "INSERT INTO accounts(owner_id, name) VALUES (:owner, :name) RETURNING *",
        owner=owner,
        name=name,
    )
    assert account is not None
    if funding:
        now = query(conn, "SELECT clock_timestamp()").scalar_one()
        post(conn, CLEARING, account["id"], funding, actor_id, "FUNDING", now)
    return {**account, "balance_minor": funding}


def prepare_transfer(
    conn: Connection, actor: dict, source: UUID, destination: UUID, amount: int
) -> datetime:
    if source == destination:
        raise BusinessError(409, "SAME_ACCOUNT")
    if CLEARING in (source, destination):
        raise BusinessError(404, "ACCOUNT_NOT_FOUND")
    limits = one(conn, "SELECT per_transfer, per_day FROM limits WHERE id=1 FOR SHARE")
    assert limits is not None
    accounts = {
        row["id"]: row
        for row in many(
            conn,
            "SELECT * FROM accounts WHERE id IN (:source, :destination) ORDER BY id FOR UPDATE",
            source=source,
            destination=destination,
        )
    }
    if len(accounts) != 2 or (
        actor["role"] == Role.CUSTOMER and accounts[source]["owner_id"] != actor["id"]
    ):
        raise BusinessError(404, "ACCOUNT_NOT_FOUND")
    if any(row["status"] != Status.ACTIVE for row in accounts.values()):
        raise BusinessError(409, "ACCOUNT_BLOCKED")
    now = query(conn, "SELECT clock_timestamp()").scalar_one()
    balance = query(
        conn,
        "SELECT balance_minor FROM account_balances WHERE id=:source",
        source=source,
    ).scalar_one()
    spent = query(
        conn,
        """SELECT COALESCE(sum(amount), 0)::bigint FROM journals
                          WHERE source_id=:source AND kind='TRANSFER'
                          AND created_at >= date_trunc('day', CAST(:now AS timestamptz), 'UTC')""",
        source=source,
        now=now,
    ).scalar_one()
    validate_debit(amount, balance, spent, limits["per_transfer"], limits["per_day"])
    return now


def transfer(
    engine: Engine,
    actor: dict,
    source: UUID,
    destination: UUID,
    amount: int,
    key: str,
    request_id: UUID,
    *,
    after_post: Callable[[], None] | None = None,
) -> Receipt:
    actor_id = actor["id"]
    digest = hashlib.sha256(f"{source}/{destination}/{amount}/RUB".encode()).hexdigest()
    with engine.begin() as conn:
        query(
            conn,
            "SELECT pg_advisory_xact_lock(hashtextextended(:scope, 0))",
            scope=f"vaultix-transfer/{actor_id}/{key}",
        )
        previous = one(
            conn,
            """SELECT digest, status, body FROM idempotency
                                WHERE actor_id=:actor AND key=:key""",
            actor=actor_id,
            key=key,
        )
        if previous is not None:
            if previous["digest"] != digest:
                audit(conn, request_id, "TRANSFER", "IDEMPOTENCY_CONFLICT", actor_id)
                return Receipt(409, {"code": "IDEMPOTENCY_CONFLICT"})
            object_id = previous["body"].get("id")
            audit(
                conn,
                request_id,
                "TRANSFER",
                "REPLAY",
                actor_id,
                UUID(object_id) if object_id else None,
            )
            return Receipt(previous["status"], previous["body"], True)

        try:
            now = prepare_transfer(conn, actor, source, destination, amount)
        except BusinessError as error:
            receipt = Receipt(error.status, {"code": error.code})
            audit(conn, request_id, "TRANSFER", error.code, actor_id)
        else:
            journal = post(conn, source, destination, amount, actor_id, "TRANSFER", now)
            if after_post is not None:
                after_post()
            receipt = Receipt(201, {"id": str(journal["id"]), "status": "POSTED"})
            audit(conn, request_id, "TRANSFER", "POSTED", actor_id, journal["id"])

        query(
            conn,
            """INSERT INTO idempotency(actor_id, key, digest, status, body)
                    VALUES (:actor, :key, :digest, :status, CAST(:body AS jsonb))""",
            actor=actor_id,
            key=key,
            digest=digest,
            status=receipt.status,
            body=json.dumps(receipt.body),
        )
        return receipt
