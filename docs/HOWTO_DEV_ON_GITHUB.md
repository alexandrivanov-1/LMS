# Как разрабатывать без сервера (только GitHub)

## Вариант A — Codespaces (рекомендуется)
1. Открой репозиторий → Code → **Create codespace on main**.
2. Codespaces сам поднимет Docker-Compose (см. .devcontainer). Через 20–60 сек:
   - демо-страница: **forwarded port 80** (open in browser);
   - MinIO Console: порт 9001; Neo4j: 7474; Qdrant: 6333.
3. Если сервисы не поднялись: `cd infra && docker compose up -d --build`.

> Чтобы делиться ссылкой на демо, в панели Ports укажи порт 80 → Visibility: **Public**.

## Вариант B — Интеграционные прогонки в Actions
При каждом PR workflow `integration.yml`:
- поднимет Docker-Compose на runner’е,
- выполнит health-чеки и базовые вызовы (`/ingest/upload`, `/parser/scan`, `/indexer/run`, `/search`),
- приложит логи контейнеров как artifacts.

## Переменные и пароли
Скопируй `.env.example` в `.env`. В Codespaces `infra/docker compose` использует `.env` из корня (переменные проброшены через compose). Для CI значения задаются прямо в workflow.

## Что именно проверять
1) Загрузка: открыть `/` и загрузить тестовый PDF/DOCX.  
2) Парсер → «Сканировать» и «Разметить нормы».  
3) Индексация → «Indexer run».  
4) Поиск → запрос «единственный поставщик» (должны вернуться фрагменты и цитаты).

---
