# Stage 1 Merge & Test Playbook

Документ фиксирует последовательность действий для доведения веток Stage 1 до состояния готовности к релизу и описывает критерии приёма на каждом этапе. Все операции выполняются **только через GitHub** (ветки/PR/Actions/Codespaces) согласно пользовательским требованиям и правилам `/AGENTS.md` из ветки `chore/agents-policy`.

## 0. Предварительная проверка
1. Откройте список веток: <https://github.com/alexandrivanov-1/LMS/branches>.
2. Убедитесь, что доступны ветки `main`, `chore/agents-policy`, `feat/stage1-full`, `feat/stage1-env-doc`, `feat/indexer-onnx`.
3. Зафиксируйте дату проверки и сделайте скриншот/заметку в issue, если какая-либо ветка отсутствует.

## 1. Ветка `chore/agents-policy`
- **PR:** <https://github.com/alexandrivanov-1/LMS/compare/main...chore/agents-policy>
- **Что проверить:**
  - Diff содержит `AGENTS.md` и сопутствующие документы (без кода сервисов).
  - Guard для CI (если появится) корректно определяет наличие `AGENTS.md`.
- **Workflows:**
  - CI (`ci.yml`): <https://github.com/alexandrivanov-1/LMS/actions?query=workflow%3ACI+branch%3Achore%2Fagents-policy>
  - Integration (`integration.yml`): <https://github.com/alexandrivanov-1/LMS/actions?query=workflow%3AIntegration+branch%3Achore%2Fagents-policy>
- **Локальные проверки:** `pytest services/parser/tests -q` — подтверждает, что модульные тесты парсера проходят после фиксов.
- **Действия при падении Integration:**
  1. Перезапустить workflow через UI.
  2. Скачать артефакты логов, определить сервис/контейнер, на котором произошёл сбой.
  3. Оформить отдельный PR с исправлением конфигурации/кода, затем повторить проверки.
- **Acceptance:** оба workflow зелёные; после ревью выполнить squash-merge в `main` и удалить ветку.

## 2. Ветка `feat/stage1-full`
- **PR:** <https://github.com/alexandrivanov-1/LMS/compare/main...feat/stage1-full>
- **Ключевые пути для ревью:**
  - `services/indexer/app/main.py`
  - `services/search/app/main.py`
  - `services/mask/app/main.py`
  - `services/gateway/app/main.py`
  - `infra/docker-compose.yml`
  - `infra/nginx/www/admin.html`
  - `docs/api/openapi-stage1.yaml`
  - `README.md`
- **Workflows:**
  - CI: <https://github.com/alexandrivanov-1/LMS/actions?query=workflow%3ACI+branch%3Afeat%2Fstage1-full>
  - Integration: <https://github.com/alexandrivanov-1/LMS/actions?query=workflow%3AIntegration+branch%3Afeat%2Fstage1-full>
- **Требуемый e2e-сценарий Integration:** загрузка источника → парсер → ONNX-индексатор → поиск с `as_of` и `citations` → построение подграфа → CRUD маски знаний → импорт MCQ → экспорт карточек.
- **Действия при сбоях:** анализ логов, фиксы кода/Compose, повторные прогоны до зелёного статуса.
- **Acceptance:** зелёные CI и Integration, актуальные OpenAPI/README; после ревью — squash-merge и удаление ветки.

## 3. Ветка `feat/stage1-env-doc`
- **PR:** <https://github.com/alexandrivanov-1/LMS/compare/main...feat/stage1-env-doc>
- **Контроль diff:** только документация (`README.md`, `docs/**`) без изменений сервисов/инфры.
- **Workflows:**
  - CI: <https://github.com/alexandrivanov-1/LMS/actions?query=workflow%3ACI+branch%3Afeat%2Fstage1-env-doc>
  - Integration: <https://github.com/alexandrivanov-1/LMS/actions?query=workflow%3AIntegration+branch%3Afeat%2Fstage1-env-doc>
- **Acceptance:** оба workflow зелёные; текст соответствует реализованному коду из `main`. Выполнить squash-merge и удалить ветку.

## 4. Ветка `feat/indexer-onnx`
- **PR / сравнение:** <https://github.com/alexandrivanov-1/LMS/compare/main...feat/indexer-onnx>
- **Проверка diff:**
  - Если изменений относительно `main` нет либо они дублируют `feat/stage1-full`, удалить ветку через интерфейс.
  - Если есть уникальные правки — запустить CI/Integration, устранить ошибки, затем слить через PR.
- **Workflows:**
  - CI: <https://github.com/alexandrivanov-1/LMS/actions?query=workflow%3ACI+branch%3Afeat%2Findexer-onnx>
  - Integration: <https://github.com/alexandrivanov-1/LMS/actions?query=workflow%3AIntegration+branch%3Afeat%2Findexer-onnx>

## 5. Проверка ветки `main`
После каждого merge:
1. Запустить CI (`ci.yml`) для `main`: <https://github.com/alexandrivanov-1/LMS/actions?query=workflow%3ACI+branch%3Amain>.
2. Запустить Integration (`integration.yml`) для `main`: <https://github.com/alexandrivanov-1/LMS/actions?query=workflow%3AIntegration+branch%3Amain>.
3. Если какой-либо workflow падает — создать отдельную ветку/PR с фиксом и дождаться зелёных статусов.

## 6. Smoke-тест в Codespaces
1. Создать Codespace из ветки `main` (кнопка **Code → Create codespace on main**).
2. Проверить вручную:
   - Демо-страница `/`: загрузка файла, шаги «Сканировать» и «Индексировать», выполнение поиска с `as_of` и `citations`.
   - Админ-панель `/admin`: CRUD атомов/контекстов, отображение графа, импорт MCQ (XLSX), экспорт карточек (TSV).
   - Граф Neo4j: эндпоинт `/graph?node_id=<id>&depth=2` возвращает подграф.
3. Зафиксировать результаты в issue; баги исправлять отдельными PR.

## 7. Релиз Stage 1
1. Убедиться, что `main` стабилен (зелёные CI/Integration, успешный smoke-тест).
2. Создать релиз `v0.1.0-stage1`: <https://github.com/alexandrivanov-1/LMS/releases/new>.
3. В release notes перечислить ключевые возможности Stage 1 и добавить ссылки на `docs/api/openapi-stage1.yaml` и `README.md`.
4. Удалить устаревшие ветки (`feat/indexer-onnx`, `feat/stage1-env-doc` и др.), если в них не осталось уникальных коммитов.

## 8. Статус выполнения (обновить после действий на GitHub)

| Этап | Статус | Последняя проверка | Статус Actions | Действия для завершения |
| --- | --- | --- | --- | --- |
| `chore/agents-policy` | Pending | 2025-10-10 18:49 UTC: обновлён smoke-шаг integration.yml, локально пройден `pytest services/parser/tests -q` | Не запускались в этой сессии | Запустить workflows из PR, приложить ссылки на зелёные прогоны и выполнить squash-merge |
| `feat/parser-read-object` | Pending | 2025-10-10 18:49 UTC: повторно выполнен `pytest services/parser/tests -q` (успешно) | Не запускались в этой сессии | Открыть PR в `main`, дождаться CI/Integration и смержить |
| `feat/stage1-full` | Pending | Интеграция не запускалась в текущей сессии | Не запускались в этой сессии | Запустить полный сценарий Integration, устранить сбои и слить в `main` |
| `feat/stage1-env-doc` | Pending | Ожидает синхронизации с актуальным `main` | Не запускались в этой сессии | После мерджа Stage 1 кода обновить документацию, проверить CI/Integration и слить |
| `feat/indexer-onnx` | Pending | Не проверялась на уникальные изменения | Не запускались в этой сессии | Сравнить с `main`; при отсутствии diff удалить ветку, иначе пройти стандартный цикл PR |
| `main` post-merge | Pending | 2025-10-10: локальные модульные тесты парсера пройдены | Не запускались в этой сессии | После слияний запустить CI/Integration и smoke-тест в Codespaces |
| `codex/show-project-lms-document-structure` | In Progress | 2025-10-11 10:00 UTC: повторный запуск Integration завершился ошибкой (`apache/tika:2.9.0-full` отсутствует) | Integration: FAIL (см. run 18427737532), CI: не запускался | Обновить образ Tika в `infra/docker-compose.yml`, перезапустить CI и Integration, затем выполнить squash-merge PR #4 |

> **Напоминание.** После выполнения каждого шага обновляйте таблицу: фиксируйте дату проверки, ссылки на успешные Actions и краткий результат (OK/FAIL). Это упрощает аудит выполнения Stage 1.

## Дополнительные заметки
- Для всех шагов храните ссылки на конкретные прогоны Actions и результаты ревью в issue/комментариях PR.
- При недоступности логов через прямые ссылки используйте кнопку **Download logs** в интерфейсе Actions.
- Все изменения в коде/конфигурации выполняйте через отдельные ветки с обязательными зелёными CI/Integration перед merge.
- Перед публикацией убедитесь, что выполнен чеклист из `docs/github-sync-checklist.md`, чтобы ветка `main` на GitHub содержала полный актуальный проект.
