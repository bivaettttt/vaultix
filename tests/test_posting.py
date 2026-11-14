import os
from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import IntegrityError
from vaultix.api.main import create_app
from vaultix.application.identity import passwords
from vaultix.application.lab import Scenario, run_scenario
from vaultix.application.ledger import open_account
from vaultix.domain.rules import BusinessError, validate_debit
from vaultix.infrastructure.db import connect_engine, one, query


@pytest.mark.parametrize(
    ("amount", "balance", "spent", "code"),
    [
        (501, 1000, 0, "OPERATION_LIMIT"),
        (500, 1000, 501, "DAILY_LIMIT"),
        (500, 499, 0, "INSUFFICIENT_FUNDS"),
        (500, 500, 500, None),
    ],
)
def test_debit_rules(amount, balance, spent, code):
    if code is None:
        validate_debit(amount, balance, spent, 500, 1000)
    else:
        with pytest.raises(BusinessError, match=code):
            validate_debit(amount, balance, spent, 500, 1000)


@pytest.fixture(scope="session")
def engine():
    engine = connect_engine(os.environ["TEST_DATABASE_URL"])
    yield engine
    engine.dispose()


@pytest.fixture
def pair(engine):
    username = f"test-{uuid4().hex}"
    with engine.begin() as conn:
        rows = []
        for label, funding in (("source", 10000), ("recipient", 0)):
            user = one(
                conn,
                """INSERT INTO users(username,name,password_hash,role)
                              VALUES (:username,:name,:digest,'CUSTOMER') RETURNING id""",
                username=username if funding else f"test-{uuid4().hex}",
                name=label,
                digest=passwords.hash("test-password-local"),
            )
            rows.append(open_account(conn, user["id"], label, funding, None))
    return username, *(str(row["id"]) for row in rows)


def signed(app, username):
    client = TestClient(app)
    assert (
        client.post(
            "/api/login", json={"username": username, "password": "test-password-local"}
        ).status_code
        == 204
    )
    return client


@pytest.mark.parametrize(
    ("same_key", "statuses"), [(True, [201, 201]), (False, [201, 409])]
)
def test_concurrent_debits(engine, pair, same_key, statuses):
    username, source, destination = pair
    app = create_app(engine, secure=False)
    with signed(app, username) as client:
        payload = {
            "source_id": source,
            "destination_id": destination,
            "amount_minor": 7000,
        }

        def send(index):
            return client.post(
                "/api/transfers",
                json=payload,
                headers={"Idempotency-Key": "same" if same_key else str(index)},
            )

        with ThreadPoolExecutor(2) as pool:
            results = list(pool.map(send, range(2)))
        assert sorted(r.status_code for r in results) == statuses
        if same_key:
            assert results[0].json() == results[1].json()
            assert sorted(r.headers["Idempotency-Replayed"] for r in results) == [
                "false",
                "true",
            ]
        assert client.get(f"/api/accounts/{source}").json()["balance_minor"] == 3000
        assert client.get(f"/api/accounts/{destination}").status_code == 404
        history = client.get(f"/api/transfers?account_id={source}").json()
        assert len(history) == 2
        journal = client.get(f"/api/transfers/{history[0]['id']}").json()
        assert sorted((e["side"], e["amount"]) for e in journal["entries"]) == [
            ("CREDIT", 7000),
            ("DEBIT", 7000),
        ]
        conflict = client.post(
            "/api/transfers",
            json={**payload, "amount_minor": 1},
            headers={"Idempotency-Key": "same" if same_key else "0"},
        )
        assert conflict.json() == {"code": "IDEMPOTENCY_CONFLICT"}


def test_rollback(engine, pair):
    username, source, destination = pair

    def fail():
        raise RuntimeError("test rollback")

    payload = {"source_id": source, "destination_id": destination, "amount_minor": 7000}
    headers = {"Idempotency-Key": "rollback"}
    with signed(create_app(engine, secure=False, after_post=fail), username) as client:
        assert (
            client.post("/api/transfers", json=payload, headers=headers).status_code
            == 500
        )
        assert client.get(f"/api/accounts/{source}").json()["balance_minor"] == 10000
    with signed(create_app(engine, secure=False), username) as client:
        assert (
            client.post("/api/transfers", json=payload, headers=headers).status_code
            == 201
        )


def test_session_and_role_checks(engine, pair):
    username, source, destination = pair
    app = create_app(engine, secure=False)
    with TestClient(app) as client:
        assert client.get("/api/accounts").status_code == 401
        assert (
            client.post(
                "/api/login",
                headers={"Origin": "https://untrusted.example"},
                json={"username": username, "password": "test-password-local"},
            ).status_code
            == 403
        )
    with signed(app, username) as client:
        assert client.get("/api/audit").status_code == 403
        assert client.get("/api/users").status_code == 403
        assert (
            client.patch(
                f"/api/accounts/{source}", json={"status": "BLOCKED"}
            ).status_code
            == 403
        )
        payload = {
            "source_id": destination,
            "destination_id": source,
            "amount_minor": 1,
        }
        assert (
            client.post(
                "/api/transfers", json=payload, headers={"Idempotency-Key": "foreign"}
            ).status_code
            == 404
        )
        assert (
            client.post(
                "/api/transfers",
                json={**payload, "amount_minor": 1.5},
                headers={"Idempotency-Key": "invalid"},
            ).status_code
            == 422
        )


def test_ledger_constraints(engine, pair):
    _, source, destination = pair
    with pytest.raises(IntegrityError), engine.begin() as conn:
        query(
            conn,
            """INSERT INTO journals(kind, source_id, destination_id, amount, created_at)
                    VALUES ('TRANSFER', :source, :destination, 100, clock_timestamp())""",
            source=source,
            destination=destination,
        )
    with pytest.raises(IntegrityError), engine.begin() as conn:
        query(conn, "UPDATE entries SET amount=1 WHERE account_id=:id", id=source)


@pytest.mark.parametrize("scenario", list(Scenario))
def test_lab_scenarios(engine, scenario):
    sandbox = connect_engine(os.environ["TEST_LAB_DATABASE_URL"])
    assert sandbox.url.database != engine.url.database
    try:
        result = run_scenario(sandbox, scenario)
        assert result["passed"], result["checks"]
    finally:
        sandbox.dispose()
