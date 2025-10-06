# KPK Stage 1 — Обновляемые курсы по закупкам (44-ФЗ/223-ФЗ)

![CI](https://github.com/alexandrivanov-1/LMS/actions/workflows/ci.yml/badge.svg)
![Integration](https://github.com/alexandrivanov-1/LMS/actions/workflows/integration.yml/badge.svg)

Stage 1 создаёт фундамент платформы обучения госзакупкам: ingest источников, нормализация норм до подпункта, детерминированная ONNX-векторизация, поиск с фильтром «на дату» и цитатами, CRUD «маски знаний», импорт MCQ и экспорт карточек, админ-панель и базовые smoke-проверки в CI.

## Быстрый старт

### GitHub Codespaces (рекомендуется)
1. Открой репозиторий → **Code → Create codespace on main**.
2. После запуска devcontainer автоматически поднимет Docker Compose (см. `.devcontainer/devcontainer.json`).
3. В панели **Ports** доступны ключевые сервисы:
   - 80 — Nginx/gateway (`/` — демо, `/admin` — админ-панель)
   - 9001 — MinIO Console
   - 7474 — Neo4j Browser
   - 6333 — Qdrant
4. Если сервисы не поднялись автоматически:
   ```bash
   cd infra
   docker compose up -d --build
   ```

### Локально (Docker Compose)
```bash
git clone https://github.com/alexandrivanov-1/LMS
cd LMS
cp .env.example .env
cd infra && docker compose up -d --build
cat ../db/schema.sql | docker compose exec -T postgres \
  psql -U "$POSTGRES_USER" -d "$POSTGRES_DB"
```

## Сквозной сценарий
1. Откройте `http://<host>/admin` — лёгкий админ-UI (Nginx).
2. Загрузите документ (PDF/DOCX/TXT) → ingest сохранит его в MinIO и создаст задачу.
3. Нажмите «Сканировать» → parser + Tika сохранят чанки и метаданные в Postgres.
4. Нажмите «Индексировать» → indexer рассчитает ONNX-эмбеддинги (768) и запишет в Qdrant коллекцию `chunks` с `valid_from/valid_to`.
5. В разделе «Маска знаний» создайте атомы и контексты, проверьте их наличие через таблицы.
6. Импортируйте вопросы через API `POST /questions/import_xlsx` и выгрузите карточки `GET /cards/export/anki` (curl/Postman).
7. В форме «Просмотр графа» запросите подграф Neo4j по `node_id` — gateway пересоберёт граф и вернёт JSON для визуализации.

## Компоненты
- **gateway** — FastAPI, проксирующий внешние запросы к внутренним сервисам.
- **ingest** — загрузка файлов в MinIO и запись метаданных в Postgres.
- **parser** — интеграция с Apache Tika, разбивка текста на чанки.
- **indexer** — FastAPI + ONNX Runtime (CPU, 768) для векторизации чанков и записи в Qdrant с payload `source_id/norm_ref/page/slide/timecode/valid_*`.
- **search** — векторизация запросов тем же пайплайном, фильтрация по `as_of`, возврат `citations[]`, API для экспорта графа в Neo4j.
- **mask** — CRUD по атомам/контекстам, импорт MCQ из XLSX, экспорт карточек Anki (TSV).
- **frontend** — placeholder контейнер.
- **infra** — Docker Compose, Nginx, вспомогательные скрипты.

## Документация
- [docs/TZ_Stage1.md](docs/TZ_Stage1.md) — техническое задание.
- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) — обзор архитектуры.
- [docs/api/openapi-stage1.yaml](docs/api/openapi-stage1.yaml) — API Stage 1.
- [docs/HOWTO_DEV_ON_GITHUB.md](docs/HOWTO_DEV_ON_GITHUB.md) — руководство по GitHub-only разработке.
- [docs/HOWTO_PUSH_TO_GITHUB.md](docs/HOWTO_PUSH_TO_GITHUB.md) — инструкция по публикации из окружения с доступом к GitHub.

## CI/CD
- `CI` — линтеры/тесты Python-сервисов и фронтенда, сборка Docker-образов.
- `Integration (Compose)` — сборка Docker Compose, ожидание health-check'ов и smoke: upload → parser → indexer (ONNX) → search(as_of) → graph → CRUD mask.
- `Deploy` — SSH-деплой по тэгу `v*.*.*`.

## Структура репозитория
```
.devcontainer/          # конфигурация Codespaces
.github/                # workflows, шаблоны PR/Issue
infra/                  # docker-compose, nginx, демо-страница
services/               # FastAPI-сервисы (gateway, ingest, parser, indexer, search, mask)
frontend/               # placeholder Dockerfile
docs/                  # ТЗ, архитектура, API, гайды
db/                    # schema.sql и миграции
```

## Лицензия
Распространяется по лицензии MIT. См. [LICENSE](LICENSE).
