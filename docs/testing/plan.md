# План проверок / Test plan

| ID | Trace | Test and acceptance |
|---|---|---|
| TC-001 | FR-001, FR-002, NFR-004 | Auth, role and object checks return 401, 403 or 404 as specified |
| TC-002 | FR-003, BR-004…BR-010, NFR-001 | Check account/amount/status/limit decisions and equal opposite entries |
| TC-003 | FR-004, BR-002, BR-003 | Parallel matching requests produce a single journal and match the stored response |
| TC-004 | FR-003, NFR-001 | Concurrent debits that together exceed funds produce one posting |
| TC-005 | FR-008, NFR-002 | Inject failure after posting and assert rows and balances roll back |
| TC-006 | FR-005, FR-006, FR-007 | Staff routes mutate authorized objects and produce correlated audit |
| TC-007 | FR-008, NFR-003 | Run all eight cases and assert actual HTTP outcomes and database invariants |
| TC-008 | FR-001…FR-004 | Playwright verifies sign-in, account view, posting and history |

Unit tests cover decisions. HTTP integration tests use real PostgreSQL and independent connections under concurrency. CI will validate format, types, build, tests and contract drift. Results are recorded from actual runs.
