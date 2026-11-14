# Трассируемость / Traceability

| Ценность / Need | Требование / Rule | API / data | Implementation | Verification |
|---|---|---|---|---|
| Авторизованное действие / Authorized action | FR-001, BR-001 | login, me, sessions | [identity](../../backend/vaultix/application/identity.py) | TC-001 session and role checks, TC-008 Playwright |
| Собственные данные / Own data | FR-002, BR-005 | accounts, transfers | [API](../../backend/vaultix/api/main.py) | TC-001 object scope, TC-008 journal |
| Корректный перевод / Valid posting | FR-003, BR-004…BR-010 | transfers, journals, entries | [ledger](../../backend/vaultix/application/ledger.py), [DDL](../../backend/alembic/versions/0001_ledger.py) | TC-002 debit rules and constraints, TC-004 concurrent debits |
| Безопасный повтор / Safe retry | FR-004, BR-002/003 | Idempotency-Key, idempotency | [ledger](../../backend/vaultix/application/ledger.py) | TC-003 concurrent matching retry and conflict |
| Открытие и блокировка / Opening and freezing | FR-005, BR-006/010 | accounts | [API](../../backend/vaultix/api/main.py) | TC-006 staff workflow |
| Администрирование / Administration | FR-006, BR-007 | users, limits | [identity](../../backend/vaultix/application/identity.py), [API](../../backend/vaultix/api/main.py) | TC-006 staff workflow |
| Расследование / Investigation | FR-007 | audit, X-Request-ID | [ledger](../../backend/vaultix/application/ledger.py), [API](../../backend/vaultix/api/main.py) | TC-006 correlated audit |
| Демонстрация отказов / Failure demonstration | FR-008, NFR-002 | lab, separate database | [lab](../../backend/vaultix/application/lab.py) | TC-005 rollback, TC-007 eight cases, TC-008 browser |
| Воспроизведение / Reproducibility | NFR-003 | PostgreSQL 16 | [Compose](../../compose.yaml), [workflow](../../.github/workflows/quality.yml) | Health checks, contract checks, pytest, Playwright |

[Test source](../../tests/test_posting.py) · [Browser tests](../../frontend/e2e/flows.spec.ts) · [Observed outcomes](results.md)
