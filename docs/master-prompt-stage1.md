Мастер‑промпт для Codex: завершение Stage 1 и синхронизация веток

Этот промпт предназначен для Codex (агента), который будет выполнять реальную работу по завершению Stage 1 проекта LMS. Пожалуйста, передайте ему текст ниже без изменений, чтобы он понимал, что делать. Промпт сформулирован на русском.

🛡 Общие правила

Работаем только через GitHub. Никаких локальных песочниц. Репозиторий: https://github.com/alexandrivanov-1/LMS, основная ветка — main.

Следуй правилам из AGENTS.md: не коммить напрямую в main, работай через фиче‑ветки, каждый PR должен проходить CI и Integration; только после зелёных статусов выполняй squash‑merge. Не храни секреты в коде.

Читаем документацию. Перед началом прочитай актуальные файлы:

- docs/merge-report.md — таблица статусов веток и рекомендации по дальнейшим действиям.
- docs/task-log.md — журнал задач со списком затронутых файлов.
- docs/operation-algorithm.md — алгоритм работы агента.
- docs/consultation-guidelines.md — правила консультаций.
- docs/github-sync-checklist.md (если есть) — чек‑лист синхронизации с GitHub.

Локальные тесты. Используй `pytest services/parser/tests -q`, чтобы убедиться, что функции парсера работают; особенно `_read_object`, который закрывает соединения MinIO и оборачивает ошибки `S3Error`.

🚦 Шаг 0. Подготовка и проверка

Проверь ветки через страницу Branches репозитория. Должны существовать:

- chore/agents-policy — правила агента и guard;
- feat/parser-read-object — исправления парсера;
- feat/stage1-full — основная реализация Stage 1;
- feat/stage1-env-doc — синхронизация документации;
- feat/indexer-onnx — устаревшая ветка индексатора (скорее всего дубликат);
- main и возможные служебные ветки (chore/sync-main).

Изучи `merge-report.md`: он показывает, что CI/Integration не запускались или падают, и даёт рекомендации. Это твоя карта действий: сначала запустить CI на правилах, затем Stage 1, потом документацию.

Запусти локальные тесты: `pytest services/parser/tests -q`. Убедись, что тесты `_split` и `_read_object` проходят. Если что‑то падает — исправь парсер (файлы в `services/parser/app` и `services/parser/tests`).

🛠 Шаг 1. Починка Integration workflow

От ветки `chore/agents-policy` создай новую ветку `fix/integration-workflow`. В ней открой файл `.github/workflows/integration.yml`.

В шаге smoke‑теста измени имя, чтобы оно не содержало двоеточий и кавычек (например, `Smoke upload parser index search`), и объедини команду `curl` в одну строку, чтобы YAML корректно парсился. Запрос должен использовать согласованный поисковый запрос `azhynka` (пример в `merge-report.md`).

Закоммить изменения и запушь ветку. Создай Pull Request (`fix/integration-workflow` → `chore/agents-policy`). Укажи в описании, что исправляешь синтаксис YAML и объединяешь `curl` для smoke‑теста.

Запусти CI (`ci.yml`) и Integration для PR. Если падают, прочитай логи, исправь ошибки и повторяй до зелёного статуса.

После зелёных статусов выполни squash‑merge PR в `chore/agents-policy` и удали `fix/integration-workflow`.

Затем создай PR `chore/agents-policy` → `main`. Дождись зелёных CI/Integration и выполни squash‑merge. Теперь политика агента и исправленный workflow будут в `main`.

🐍 Шаг 2. Слияние `feat/parser-read-object`

Переключись на ветку `feat/parser-read-object`. Убедись, что код парсера содержит функцию `_read_object`, которая закрывает соединение MinIO и оборачивает `S3Error`.

Запусти `pytest services/parser/tests -q` — тесты должны быть зелёные.

Создай PR `feat/parser-read-object` → `main`. В описании перечисли изменённые файлы (`services/parser/app/main.py`, `services/parser/tests/test_main.py`, `services/parser/app/__init__.py`, `services/parser/tests/__init__.py`, `services/__init__.py`) и цель (фикс MinIO / `S3Error`).

Дождись зелёных CI/Integration, затем сделай squash‑merge. Удаляй ветку после слияния.

🧩 Шаг 3. Синхронизация и завершение Stage 1

Перебазируй (`rebase`) ветку `feat/stage1-full` от свежего `main`. Разреши конфликты (в основном в `infra/docker-compose.yml`, `services/*`, `docs/api/openapi-stage1.yaml`).

Запусти CI и Integration на `feat/stage1-full`. Integration должен пройти полный сценарий: загрузка → парсер → ONNX‑индексатор → поиск с `as_of` и цитатами → построение графа Neo4j → CRUD атомов и контекстов → импорт MCQ и экспорт карточек. Используй логи и правь код, пока не получишь зелёный статус.

Создай PR `feat/stage1-full` → `main`. В описании укажи ключевые файлы (`services/gateway/app/main.py`, `services/ingest/app/main.py`, `services/parser/app/main.py`, `services/indexer/app/main.py`, `services/search/app/main.py`, `services/mask/app/main.py`, `services/search/app/graph_build.py`, `infra/nginx/www/admin.html`, `docs/api/openapi-stage1.yaml`) и что реализовано. После зелёных CI/Integration выполни squash‑merge.

Синхронизируй ветку `feat/stage1-env-doc` с `main` (`rebase` или `merge`). Проверь, что она содержит только изменения в документации (`README`, `docs/*`). Убедись, что `docs/merge-report.md` и `docs/task-log.md` отражают текущий статус и список файлов. Создай PR `feat/stage1-env-doc` → `main`, дождись зелёных CI/Integration и слей.

Проанализируй ветку `feat/indexer-onnx`: если её изменения полностью поглощены в `feat/stage1-full`, просто удали ветку. Если есть уникальные правки — создавай PR и сливай аналогично.

🚢 Шаг 4. Финализация и релиз Stage 1

Когда `main` содержит все изменения Stage 1, запусти CI и Integration на ветке `main`. Убедись, что все пайплайны зелёные.

Подними Codespaces из `main` и пройди сквозной сценарий: загрузить тестовый файл через демо‑страницу, нажать «Сканировать», затем «Индексировать», выполнить поиск с параметром `as_of`, открыть админ‑панель `/admin` и проверить CRUD атомов/контекстов, построение графа, импорт MCQ и экспорт карточек.

При успехе обнови документацию (`README.md`, `docs/merge-report.md`, `docs/task-log.md`) — убери упоминания о планах Stage 1 и отметь завершённые задачи. Добавь в `merge-report.md` ссылки на успешные прогоны Actions и релизную информацию.

Создай релиз `v0.1.0-stage1` на GitHub с описанием: что реализовано, ссылки на OpenAPI и демо.

Удали устаревшие ветки (`feat/indexer-onnx`, `feat/stage1-env-doc`, `feat/stage1-full`, `chore/sync-main`) после проверки.

Начни планировать Stage 2 — это не входит в текущий промпт, но можно создать issue с roadmap.

✅ Критерии готовности

- `integration.yml` парсится без ошибок: шаги CI и Integration зелёные.
- Парсер безопасно читает файлы MinIO через `_read_object`, тесты в `services/parser/tests` проходят.
- `main` содержит все сервисы Stage 1: ingest, parser, ONNX‑indexer, search с `as_of` и цитатами, mask‑service, graph‑build, MCQ import/export, admin‑UI.
- Документация синхронизирована: `merge-report.md` отображает актуальный статус, `README` не содержит устаревших планов, `task-log.md` перечисляет завершённые задачи и обновлённые файлы.
- Выпущен релиз `v0.1.0-stage1`.

⚠️ Возможные риски и проверки

- Ошибки YAML: всегда проверяй синтаксис шагов и команд (двоеточия, кавычки, переносы). См. рекомендации в `operation-algorithm.md`.
- Конфликты при слиянии: ветки Stage 1 могут сильно отстать от `main`. Используй `rebase` и внимательно решай конфликты.
- Документация ≠ код: не добавляй в README/merge-report планы, пока код не реализован. Соблюдай принцип «документируем реализованное».
- Секреты и токены: PAT должен использоваться только в окружении и не попадать в репозиторий; см. `AGENTS.md`.
- Проверка логов CI/Integration: при падении тестов скачивай и анализируй артефакты; не мержи ветку, пока не найдена и не устранена причина.
