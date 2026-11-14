# Архитектура / Architecture

React обслуживает интерфейс через nginx, который проксирует /api в FastAPI. Слои: domain (чистые правила), application (транзакционные сценарии), infrastructure (SQLAlchemy, PostgreSQL, Alembic), API (HTTP, сессии, контракты). Docker публикует фронтенд на loopback. OpenAPI экспортируется из FastAPI.

React runs behind nginx, which proxies /api to FastAPI. Layers: domain (pure rules), application (transactional workflows), infrastructure (SQLAlchemy, PostgreSQL, Alembic), API (HTTP, sessions, contracts). Docker exposes the frontend on loopback. OpenAPI is exported from FastAPI.

## Транзакционная модель / Transaction model

Остаток = сумма кредитов минус сумма дебетов клиентского счёта. Синтетическое финансирование дебетует клиринг, а перевод дебетует источник и кредитует получателя. Каждая операция состоит из строго двух равных встречных записей. Deferred constraint trigger проверяет состав журнала на commit. Проведённые строки защищены триггерами от UPDATE/DELETE. Отдельное поле остатка отсутствует.

Balance is the sum of credits less debits on the customer's liability account. Demo funding debits clearing. A transfer debits the source and credits the destination. A deferred constraint trigger checks the two equal and opposite lines at commit. Triggers block updates and deletes on posted rows. Balances are derived from entries.

READ COMMITTED. Сначала транзакционная advisory-блокировка ключа, затем shared lock конфигурации и row locks счетов по UUID. Последующие запросы на чтение остатка и лимита видят проводки предыдущего владельца блокировки. Изменение статуса захватывает ту же блокировку счёта. Время операции берётся после захвата блокировок, дневные лимиты считаются по UTC. Ошибка СУБД откатывает проводки, сохранённый результат и аудит успеха.

READ COMMITTED uses a transaction advisory lock for the actor/key, a shared lock for limits and ordered row locks for accounts. Subsequent balance and limit queries see the prior holder's committed postings. Status changes lock the same account. The operation clock is read after acquiring locks and daily limits use UTC. Database failures roll back postings, the stored response and success audit together.

## Границы доверия / Trust boundaries

Opaque sessions with hashed tokens at rest, HttpOnly SameSite cookies, Origin checks for unsafe browser requests, Argon2id passwords and server-side role/ownership checks. Audit contains identifiers and outcomes. The lab uses a separate database and fixed scenarios. Trusted local operators control database ownership, backups and startup configuration.

## Диаграммы / Diagrams

[BPMN 2.0](../diagrams/transfer.bpmn) · [UML sequence](../diagrams/transfer.mmd) · [Operation state machine](../diagrams/operation.mmd) · [ERD](../diagrams/ledger.mmd) · [C4 context](../diagrams/context.mmd) · [C4 containers](../diagrams/container.mmd)

PostgreSQL references: [READ COMMITTED](https://www.postgresql.org/docs/16/transaction-iso.html) and [explicit locks](https://www.postgresql.org/docs/16/explicit-locking.html).
