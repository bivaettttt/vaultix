import asyncio
from dataclasses import dataclass
from enum import StrEnum
from uuid import UUID, uuid4

import httpx
from sqlalchemy import Engine

from vaultix.application.identity import passwords
from vaultix.application.ledger import open_account
from vaultix.infrastructure.db import many, one, query


class Scenario(StrEnum):
    SUCCESS = "success"
    INSUFFICIENT = "insufficient"
    REPLAY = "replay"
    CONFLICT = "conflict"
    CONCURRENT = "concurrent"
    ROLLBACK = "rollback"
    BLOCKED = "blocked"
    LIMIT = "limit"


@dataclass(frozen=True)
class Case:
    amounts: tuple[int, ...]
    keys: tuple[str, ...]
    outcomes: tuple[tuple[int, str], ...]
    posted: int = 0


CASES = {
    Scenario.SUCCESS: Case((3000,), ("a",), ((201, "POSTED"),), 3000),
    Scenario.INSUFFICIENT: Case((11000,), ("a",), ((409, "INSUFFICIENT_FUNDS"),)),
    Scenario.REPLAY: Case(
        (3000, 3000), ("a", "a"), ((201, "POSTED"), (201, "POSTED")), 3000
    ),
    Scenario.CONFLICT: Case(
        (3000, 4000), ("a", "a"), ((201, "POSTED"), (409, "IDEMPOTENCY_CONFLICT")), 3000
    ),
    Scenario.CONCURRENT: Case(
        (7000, 7000), ("a", "b"), ((201, "POSTED"), (409, "INSUFFICIENT_FUNDS")), 7000
    ),
    Scenario.ROLLBACK: Case((3000,), ("a",), ((500, "INTERNAL_ERROR"),)),
    Scenario.BLOCKED: Case((3000,), ("a",), ((409, "ACCOUNT_BLOCKED"),)),
    Scenario.LIMIT: Case((5000001,), ("a",), ((409, "OPERATION_LIMIT"),)),
}


def fixtures(engine: Engine, blocked: bool):
    run = uuid4()
    username = f"lab-{run.hex}"
    password = uuid4().hex
    with engine.begin() as conn:
        user = one(
            conn,
            """INSERT INTO users(username,name,role,password_hash)
                    VALUES (:username,'Lab user','CUSTOMER',:digest) RETURNING id""",
            username=username,
            digest=passwords.hash(password),
        )
        assert user is not None
        source = open_account(conn, user["id"], "Lab source", 10000, None)["id"]
        destination = open_account(conn, user["id"], "Lab destination", 0, None)["id"]
        if blocked:
            query(conn, "UPDATE accounts SET status='BLOCKED' WHERE id=:id", id=source)
    return run, username, password, source, destination


def snapshot(engine: Engine, source: UUID, destination: UUID):
    with engine.connect().execution_options(isolation_level="REPEATABLE READ") as conn:
        balances = many(
            conn,
            """SELECT id, status, balance_minor FROM account_balances
                      WHERE id IN (:source,:destination) ORDER BY id""",
            source=source,
            destination=destination,
        )
        journals = many(
            conn,
            """SELECT id, kind, source_id, destination_id, amount FROM journals
                      WHERE source_id IN (:source,:destination)
                         OR destination_id IN (:source,:destination) ORDER BY created_at,id""",
            source=source,
            destination=destination,
        )
        entries = many(
            conn,
            """SELECT e.journal_id, e.side, e.account_id, e.amount FROM entries e
                     JOIN journals j ON j.id=e.journal_id
                     WHERE j.source_id IN (:source,:destination)
                        OR j.destination_id IN (:source,:destination)
                     ORDER BY e.journal_id,e.side""",
            source=source,
            destination=destination,
        )
    return {"accounts": balances, "journals": journals, "entries": entries}


def fail_after_post():
    raise RuntimeError("Lab rollback")


def run_scenario(engine: Engine, scenario: Scenario):
    from vaultix.api.main import create_app

    case = CASES[scenario]
    run, username, password, source, destination = fixtures(
        engine, scenario == Scenario.BLOCKED
    )
    before = snapshot(engine, source, destination)
    app = create_app(
        engine,
        secure=False,
        after_post=fail_after_post if scenario == Scenario.ROLLBACK else None,
    )
    inputs = [
        {
            "source_id": str(source),
            "destination_id": str(destination),
            "currency": "RUB",
            "amount_minor": amount,
        }
        for amount in case.amounts
    ]

    async def execute():
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://lab"
        ) as client:
            login = await client.post(
                "/api/login", json={"username": username, "password": password}
            )
            login.raise_for_status()

            async def send(payload, key):
                response = await client.post(
                    "/api/transfers", json=payload, headers={"Idempotency-Key": key}
                )
                return {
                    "status": response.status_code,
                    "body": response.json(),
                    "replayed": response.headers.get("Idempotency-Replayed") == "true",
                    "request_id": response.headers["X-Request-ID"],
                }

            calls = [
                send(payload, key)
                for payload, key in zip(inputs, case.keys, strict=True)
            ]
            results = (
                await asyncio.gather(*calls)
                if scenario == Scenario.CONCURRENT
                else [await call for call in calls]
            )
            (await client.post("/api/logout")).raise_for_status()
            return results

    responses = asyncio.run(execute())
    after = snapshot(engine, source, destination)
    balances = {a["id"]: a["balance_minor"] for a in after["accounts"]}
    checks = {
        "http_outcomes": sorted(
            (r["status"], r["body"].get("code", r["body"].get("status")))
            for r in responses
        )
        == sorted(case.outcomes),
        "expected_balances": balances
        == {source: 10000 - case.posted, destination: case.posted},
        "journal_count": len(after["journals"]) - len(before["journals"])
        == bool(case.posted),
        "entries_balanced": all(
            sorted(
                (entry["side"], entry["account_id"], entry["amount"])
                for entry in after["entries"]
                if entry["journal_id"] == j["id"]
            )
            == [
                ("CREDIT", j["destination_id"], j["amount"]),
                ("DEBIT", j["source_id"], j["amount"]),
            ]
            for j in after["journals"]
        ),
    }
    if not case.posted:
        checks["ledger_unchanged"] = before == after
    if scenario == Scenario.REPLAY:
        checks["same_receipt"] = (
            responses[1]["replayed"] and responses[0]["body"] == responses[1]["body"]
        )
    return {
        "id": run,
        "scenario": scenario,
        "passed": all(checks.values()),
        "checks": checks,
        "requests": [
            {"key": key, "body": payload}
            for key, payload in zip(case.keys, inputs, strict=True)
        ],
        "responses": responses,
        "before": before,
        "after": after,
    }
