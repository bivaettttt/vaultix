# Модель угроз / Threat model

| Актив / Asset | Угроза / Threat | Защита / Control |
|---|---|---|
| Чужой счёт / Another customer's account | Object ID guessing | Scoped account and journal reads, ownership check under source lock |
| Журнал / Ledger | Concurrent overdraft or duplicate posting | Ordered row locks, per-key advisory locks, database receipt uniqueness |
| Проводки / Postings | Partial posting or mutation | Atomic PostgreSQL transactions, deferred shape validation, immutability triggers |
| Сессия / Session | Token exposure or cross-site writes | Hashed opaque tokens, HttpOnly SameSite cookies, Origin validation, Secure outside demo |
| Панель / Staff interface | Privilege escalation | Server role checks for each privileged route |
| Лаборатория / Lab | Failure injection in the main ledger | Separate database, fixed scenario enum, private hook, ADMIN gate |
| Аудит / Audit | Secret disclosure | Audit stores IDs and enumerated outcomes. SQLAlchemy parameter logging disabled. |

Assumptions / Допущения. Localhost demo, trusted host and PostgreSQL administrator. Internet deployment needs TLS, rate limiting, operational database roles, personal-data governance, backup and monitoring. The PostgreSQL table owner can alter or disable database protections. Revoking a session prevents new authenticated requests and allows an already authorized request to finish.
