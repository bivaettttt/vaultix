# Фактические результаты / Observed results

| Check | Observed outcome |
|---|---|
| pytest, separate PostgreSQL 16 test and lab databases | 18 passed, including 8 lab scenarios |
| Playwright Chromium against Docker Compose | 3 passed: customer posting and logout, mobile operator, concurrent lab |
| Python static and format checks | Ruff passed |
| Frontend static and format checks | TypeScript build and Prettier passed |
| Documentation checks | OpenAPI snapshot and local links, BPMN XML references passed |
| Docker Compose | PostgreSQL and API healthy. Frontend returned HTTP and served passing browser flows. |

Pytest reported a Starlette warning about its HTTPX test client. The warning did not alter observed outcomes.

## Reproduce

Start with Python 3.14, Node 24, Docker and two dedicated test databases on PostgreSQL 16. Export `TEST_DATABASE_URL` and `TEST_LAB_DATABASE_URL` as SQLAlchemy URLs.

```sh
python -m venv .venv
. .venv/bin/activate
pip install -r backend/requirements.txt pytest==9.2.0 ruff==0.17.5
DATABASE_URL="$TEST_DATABASE_URL" alembic -c backend/alembic.ini upgrade head
DATABASE_URL="$TEST_LAB_DATABASE_URL" alembic -c backend/alembic.ini upgrade head
pytest -q
ruff check backend tests scripts
ruff format --check backend tests scripts
PYTHONPATH=backend python scripts/openapi.py --check
python scripts/verify-docs.py
docker compose up --build --wait
cd frontend
npm ci
npm run format:check
npm run build
npx playwright install chromium
VAULTIX_URL=http://127.0.0.1:8080 npm run test:e2e
```

GitHub Actions verified the Compose and test revision on Ubuntu in the [Quality workflow](https://github.com/bivaettttt/vaultix/actions/runs/43606970838).
