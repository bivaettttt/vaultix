# Vaultix · Banking Transaction Platform

[Русский](README.ru.md)

Vaultix is an educational FinTech project about preserving ledger integrity through retries, concurrent debits, and failures. Customers manage their own RUB accounts and post internal transfers. Operators open and freeze accounts, inspect journals, and review audit events. Administrators manage synthetic users and limits and run the reliability lab.

## Run

```sh
docker compose up --build
```

Open the [local demo](http://127.0.0.1:8080) or [Swagger UI](http://127.0.0.1:8080/api/docs). Compose waits for PostgreSQL, migrates the primary and lab databases with Alembic, and seeds synthetic fixtures. The `demo`, `recipient`, `operator`, and `admin` accounts share the local default `Vaultix-demo-local`.

[.env.example](.env.example) lists the port, PostgreSQL password, and initial demo password. Use a URL-safe PostgreSQL password. The initial demo password is applied when an account is first created. The demo binds to loopback. Running `docker compose down -v` deletes all data in this demo stack.

```sh
docker compose exec backend alembic upgrade head
docker compose exec backend python -m vaultix.seed
docker compose stop
```

## Rules and API

Amounts use integer kopecks. The source and destination must be different active accounts. A transfer must fit the balance, per-operation limit, and UTC-day limit. Customers can debit their own accounts. Staff may post on a customer's behalf. Opening funding debits the clearing account and credits the customer liability. A transfer debits the sender's liability and credits the recipient's.

`POST /api/login` accepts `username` and `password` and sets a session cookie. `GET /api/accounts` lists authorized accounts. `POST /api/transfers` accepts `source_id`, `destination_id`, `amount_minor`, and `currency` with a required `Idempotency-Key` header. HTTP 201 returns a journal ID. `GET /api/transfers/{id}` returns both entries. A matching retry replays its saved outcome. A changed body yields HTTP 409. `X-Request-ID` correlates responses and audit events. See the [OpenAPI contract](docs/api/openapi.json).

## Architecture and repository

The modular monolith uses FastAPI, Pydantic, SQLAlchemy Core, Alembic, and PostgreSQL 16. React, TypeScript, Vite, React Router, and TanStack Query run behind nginx. Docker Compose provides the demo runtime and GitHub Actions runs checks. `backend` contains domain, application, infrastructure, and HTTP layers, `frontend` contains the UI and Playwright, `tests` contains pytest, `docs` contains requirements, BPMN and other diagrams, ADRs, and results, and `scripts` contains maintenance and validation commands.

Balances are derived from ledger entries. A deferred trigger validates two opposite postings at commit. Separate triggers prevent mutation of posted rows. At READ COMMITTED, an advisory lock serializes a principal's retry key. Account row locks are acquired in UUID order. A shared lock protects the limits read. Entries, the replay receipt, and the success audit commit atomically.

[Requirements and roles](docs/analysis/mvp.md) · [Architecture](docs/architecture/system.md) · [Ledger ADR](docs/decisions/001-posting.md) · [Lab ADR](docs/decisions/002-lab.md) · [Traceability](docs/testing/traceability.md)

## Demonstration

Sign in as `operator`, open Ilya's settlement account and copy its ID. Sign in as `demo`, send a transfer and inspect its debit and credit entries. Sign in as `admin` and run the concurrent debit and rollback scenarios. The lab displays request inputs, HTTP responses, PostgreSQL snapshots and invariant results. Other scenarios cover success, insufficient funds, replay, key conflict, a blocked account, and a limit violation.

- [Sign-in](assets/screenshots/sign-in.png)
- [Accounts](assets/screenshots/accounts.png)
- [Journal](assets/screenshots/journal.png)
- [Operations workspace](assets/screenshots/operations.png)
- [Reliability lab](assets/screenshots/lab.png)

## Testing, security and status

[Test plan](docs/testing/plan.md) · [Results and commands](docs/testing/results.md) · [Threat model](docs/architecture/threats.md) · [Project status](docs/PROJECT_STATUS.md)

Passwords use Argon2id. Session cookies use HttpOnly and SameSite. The API validates role, ownership, and Origin on browser writes. Non-demo mode sets Secure cookies and disables the lab. The lab requires a distinct database and an administrator and only runs fixed scenarios. Audit events store identifiers and outcomes.

The intended environment is a local synthetic-data portfolio demo. External settlement, FX, reversals, automated secret rotation and load-tested SLOs are outside scope. Replay receipts and lab fixtures accumulate until the demo is reset. Potential extensions include corrective postings, cursor pagination, reconciliation, retention, and ledger load measurement.
