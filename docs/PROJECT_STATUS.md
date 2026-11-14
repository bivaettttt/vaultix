# Состояние проекта / Project status

Реализованы клиентский кабинет, операции и аудит, PostgreSQL-журнал, исторические проводки, идемпотентность, управление пользователями и лимитами, изолированная лаборатория. [Результаты](testing/results.md) содержат фактические проверки pytest и Playwright на PostgreSQL и Compose.

Системный анализ и архитектура в [спецификации](analysis/mvp.md) и [архитектуре](architecture/system.md). Контракт экспортирован из FastAPI. Исходники диаграмм лежат в `docs/diagrams`. BPMN XML проверен на структуру ссылок. [Трассируемость](testing/traceability.md) связывает требования, правила, реализацию и тесты.

Проверки GitHub Actions прошли для коммита сборки и тестов. Результат каждого последующего коммита доступен в [GitHub Actions](https://github.com/bivaettttt/vaultix/actions). Ограничения стенда и дальнейшее развитие описаны в [README](../README.ru.md) и [модели угроз](architecture/threats.md).
