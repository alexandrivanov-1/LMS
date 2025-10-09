# Stage 1 — статус веток и проверки

## Ветки в работе
- `chore/agents-policy` — добавляет правила агента и CI-guard.
- `feat/stage1-full` — основная реализация Stage 1.
- `feat/stage1-env-doc` — синхронизация документации с реализацией.
- `feat/indexer-onnx` — устаревшая ветка индексатора, требует проверки на дублирование.

## Последние прогоны CI/Integration
| Ветка | CI | Integration | Комментарии |
| --- | --- | --- | --- |
| chore/agents-policy | pending | pending | Guard не активирован, требуется запуск workflows |
| feat/stage1-full | pending | pending | Интеграционный сценарий ещё не запускался |
| feat/stage1-env-doc | pending | pending | Ждёт синхронизации после Stage 1 |
| feat/indexer-onnx | pending | pending | Вероятно дублирует `feat/stage1-full` |

## Блокеры
- Нет свежих запусков GitHub Actions, необходима ручная активация.
- Логи интеграционных тестов недоступны — нужно пересоздать запускаемый workflow.
- Не подтверждена совместимость документации с кодом Stage 1.

## Рекомендации по действиям
1. Запустить CI и Integration для `chore/agents-policy`, убедиться в наличии проверки на `/AGENTS.md`.
2. После мерджа `chore/agents-policy` прогнать полный сценарий Stage 1 на ветке `feat/stage1-full`.
3. Синхронизировать документацию `feat/stage1-env-doc` с актуальным кодом и завершить интеграцию.
4. Проверить `feat/indexer-onnx` на уникальные изменения и удалить при отсутствии отличий.
5. После слияния веток выполнить sanity-проверку `main` и подготовить релиз `v0.1.0-stage1`.
