# Спецификация MVP / MVP specification

## Видение и границы / Vision and scope

Vaultix показывает полный жизненный цикл внутреннего перевода в RUB: от проверки прав до проводок и наблюдаемого результата при повторе, конкуренции и отказе. Пользователи, деньги и счета синтетические. Внешние расчёты, FX, проценты, отмены проведённых операций, открытая регистрация, KYC и AML вне MVP.

Vaultix demonstrates the complete lifecycle of an internal RUB transfer, including authorization, posting, retries, concurrency and rollback. All identities and funds are synthetic. External settlement, FX, interest, reversals, public signup, KYC and AML are outside MVP.

| Участник / Stakeholder | Цель / Goal | Критерий / Acceptance |
|---|---|---|
| Клиент / Customer | Видеть свои остатки и отправлять деньги / See and move own funds | История доступна владельцу. Чужие счета в деталях недоступны / Owner can inspect history and cannot read unrelated accounts |
| Оператор / Operator | Расследовать операции и блокировать счета / Investigate and freeze | Доступ к общей истории, блокировка оставляет запись аудита / Can inspect history and change account status with an audit record |
| Администратор / Admin | Управлять учебными пользователями, лимитами и лабораторией / Manage users, limits and lab | Административные маршруты проверяют роль / Administrative routes enforce role checks |
| Аналитик / Analyst | Проследить правило до результата / Trace a rule to its outcome | Сценарии лаборатории сравнивают ответы API и состояние PostgreSQL / Lab compares HTTP outcomes with PostgreSQL state |

## Словарь / Glossary

- **Клиентский счёт / Customer account** — обязательство учебного банка / A liability of the simulated bank.
- **Журнал / Journal** — проведённая операция и её две записи / A posted operation with two lines.
- **Клиринговый счёт / Funding clearing account** — источник синтетических средств при открытии / Counteraccount for demo opening funding.
- **Копейки / Minor units** — целые единицы хранения, 100 на RUB / Integer storage units, 100 per RUB.
- **Идемпотентность / Idempotency** — результат закрепляется за субъектом и ключом / Result is bound to a principal and key.
- **Correlation ID** — идентификатор запроса, возвращаемый в заголовке и сохраняемый в аудите / Request identifier returned in headers and stored in audit.

## Требования, истории и критерии / Requirements, stories and acceptance

| ID | История / User story | Критерий / Acceptance |
|---|---|---|
| FR-001 | Войти в систему / Sign in | Без сессии 401, запрещённая роль 403 / No session yields 401, forbidden role yields 403 |
| FR-002 | Видеть счета и историю / View accounts and history | Клиент видит только собственные счета и относящиеся к ним операции / Customer can see only own accounts and related operations |
| FR-003 | Отправить RUB / Transfer RUB | 201 и ровно одна сбалансированная операция / 201 and exactly one balanced journal |
| FR-004 | Повторить запрос / Retry a request | Совпадение возвращает сохранённый результат, изменение даёт 409 / Matching request replays result, changed request yields 409 |
| FR-005 | Управлять счетами / Manage accounts | Оператор открывает и блокирует, статус проверяется под блокировкой / Operator opens and freezes accounts, posting checks locked status |
| FR-006 | Управлять пользователями и лимитами / Manage users and limits | Администратор создаёт пользователей, отключает клиентов и обновляет лимиты / Admin can create users, disable customers and change limits |
| FR-007 | Исследовать аудит / Inspect audit | Инициатор, тип, время, результат, объект и запрос доступны сотрудникам / Staff can inspect actor, action, time, result, object and request |
| FR-008 | Воспроизвести отказ / Reproduce failure | Восемь сценариев используют изолированный PostgreSQL и реальный HTTP-обработчик / Eight scenarios use isolated PostgreSQL and real HTTP handlers |

| ID | Атрибут / Quality | Проверка / Measurement |
|---|---|---|
| NFR-001 | Целостность / Integrity | Нулевая сумма дебетов и кредитов в разрезе операции, отсутствие отрицательных остатков клиента / Each journal balances, no negative customer balances |
| NFR-002 | Восстановление / Recovery | Сбой после записи проводок откатывает журнал и обе записи / Failure after writing entries rolls back the entire journal |
| NFR-003 | Воспроизводимость / Reproducibility | Миграции и тесты на PostgreSQL, локальный запуск Compose / PostgreSQL migrations and tests, local Compose startup |
| NFR-004 | Доступ / Access | Серверная авторизация, изолированный стенд лаборатории, аудит без секретов / Server-side authorization, isolated lab, audit without secrets |

## Варианты использования / Use cases

- **UC-01 Перевод / Transfer.** Клиент выбирает свой счёт, вводит идентификатор получателя и сумму. API блокирует ключ, фиксирует лимиты, запирает счета в порядке ID, проверяет доступ и ограничения, проводит запись и фиксирует результат. Повтор возвращает результат первого запроса с тем же телом. Ошибка проверки сохраняется как результат ключа, при изменении параметров нужен новый ключ. Внутренняя ошибка откатывает операцию и допускает повтор. / Customer selects a source, enters destination ID and amount. API locks the key, captures limits, locks accounts in ID order, validates and posts. Matching retries replay the first outcome. Business rejections are stored, changed parameters require a new key. Internal failure rolls back and allows retry.
- **UC-02 Открытие / Opening.** Сотрудник выбирает клиента, задаёт имя счёта и необязательное стартовое финансирование. Счёт и финансирование фиксируются атомарно. / Staff sets owner, name and optional funding. Account and funding commit atomically.
- **UC-03 Блокировка / Freeze.** Сотрудник меняет ACTIVE ↔ BLOCKED. Повтор текущего состояния допустим, а запись аудита отражает запрос. / Staff toggles ACTIVE ↔ BLOCKED. Repeating the same state is accepted and audited.
- **UC-04 Лаборатория / Lab.** Администратор запускает предопределённый сценарий. Стенд создаёт новую пару счетов, выполняет запросы и проверяет состояние до и после. / Admin runs a predefined scenario. The lab creates a fresh pair of accounts, makes requests and checks database state before and after.

## Таблица решений / Decision table

Порядок строк применяется после структурной валидации. First matching row wins after structural validation.

| ID | Условие / Condition | Результат / Outcome |
|---|---|---|
| BR-001 | Сессия отсутствует или субъект отключён / Missing session or disabled actor | 401 |
| BR-002 | Ключ существует для субъекта и тело совпадает / Existing actor/key with same body | Replay |
| BR-003 | Ключ существует, тело изменено / Existing actor/key with different body | 409 IDEMPOTENCY_CONFLICT |
| BR-004 | Источник совпадает с назначением / Same account | 409 SAME_ACCOUNT |
| BR-005 | Счёт отсутствует либо источник скрыт для клиента / Missing account or hidden source | 404 ACCOUNT_NOT_FOUND |
| BR-006 | Один счёт заблокирован / Either account is blocked | 409 ACCOUNT_BLOCKED |
| BR-007 | Сумма превышает максимум или накопление за UTC-день превышает лимит / Amount exceeds per-transfer or UTC-day limit | 409 OPERATION_LIMIT / DAILY_LIMIT |
| BR-008 | Остаток меньше суммы / Balance below amount | 409 INSUFFICIENT_FUNDS |
| BR-009 | Все проверки пройдены / All checks pass | Journal posted once, 201 |
| BR-010 | Финансирование при открытии / Opening funding | Дебет клиринга, кредит клиента / Debit clearing, credit customer |

## Матрица ролей / Role matrix

| Действие / Action | CUSTOMER | OPERATOR | ADMIN |
|---|---|---|---|
| Счета и операции / Accounts and transfers | Own | All | All |
| Перевод / Transfer | Own source | Any customer source | Any customer source |
| Открытие и статус счёта / Open and freeze | — | ✓ | ✓ |
| Аудит и список клиентов / Audit and customer list | — | ✓ | ✓ |
| Пользователи и лимиты / Users and limits | — | — | ✓ |
| Лаборатория / Lab | — | — | Enabled environment only |
