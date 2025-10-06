# KPK Stage 1 — Обновляемые курсы по закупкам (44-ФЗ/223-ФЗ)

![CI](https://github.com/alexandrivanov-1/LMS/actions/workflows/ci.yml/badge.svg)
![Integration](https://github.com/alexandrivanov-1/LMS/actions/workflows/integration.yml/badge.svg)

Stage 1 создаёт фундамент платформы обучения госзакупкам: ingest источников, нормализация норм до подпункта, гибридный поиск с цитатами «на дату» и базовые активности (маска знаний, банк вопросов, карточки, аудио-брифинг).

## Быстрый старт

### GitHub Codespaces (рекомендуется)
1. Открой репозиторий → **Code → Create codespace on main**.
2. После запуска devcontainer автоматически поднимет Docker Compose (см. `.devcontainer/devcontainer.json`).
3. В панели **Ports** доступны ключевые сервисы:
   - 80 — Nginx/gateway + демо-страница `http://<host>/`
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

## Сквозной сценарий (демо-страница)
1. Откройте `http://<host>/` — HTML-страница `infra/nginx/www/index.html`.
2. Загрузите тестовый документ (PDF/DOCX/TXT).
3. Нажмите «Сканировать» → Tika разберёт файл и сохранит чанки в Postgres.
4. Нажмите «Индексировать» → данные отправятся в Qdrant (детерминированный псевдо-эмбеддер).
5. Выполните поиск и получите список чанков с идентификаторами источников.

## Компоненты
- **gateway** — FastAPI, проксирующий внешние запросы к внутренним сервисам.
- **ingest** — загрузка файлов в MinIO и запись метаданных в Postgres.
- **parser** — интеграция с Apache Tika, разбивка текста на чанки.
- **indexer** — отправка чанков в Qdrant (pseudo-эмбеддер, поддержка ONNX в планах).
- **search** — гибридный поиск (детерминированный вектор).
- **mask** — заготовка сервиса «маски знаний».
- **frontend** — placeholder контейнер.
- **infra** — Docker Compose, Nginx, вспомогательные скрипты.

## Документация
- [docs/TZ_Stage1.md](docs/TZ_Stage1.md) — техническое задание.
- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) — обзор архитектуры.
- [docs/api/openapi-stage1.yaml](docs/api/openapi-stage1.yaml) — API Stage 1.
- [docs/HOWTO_DEV_ON_GITHUB.md](docs/HOWTO_DEV_ON_GITHUB.md) — руководство по GitHub-only разработке.
- [docs/HOWTO_PUSH_TO_GITHUB.md](docs/HOWTO_PUSH_TO_GITHUB.md) — инструкция по публикации из окружения с доступом к GitHub.

## Stage 1 в релизе
- Финальная ветка: `main`.
- Тег релиза: `v0.1.0-stage1-bootstrap`.
- CI: `CI` и `Integration` проходят на каждом pull request.
- Защита `main`: обязательный review, запрет прямых push, только squash-merge.

## CI/CD
- `CI` — линтеры/тесты для Python-сервисов и фронтенда, сборка Docker-образов.
- `Integration (Compose)` — поднимает весь стек, выполняет health-check и базовый сценарий (upload → parser → index → search).
- `Deploy` — SSH-деплой по тэгу `v*.*.*`.

## Дальнейшие шаги
- Подключение ONNX-эмбеддингов.
- CRUD «маски знаний» с цитатами и контекстами.
- Импорт MCQ из Excel и генерация карточек.
- Подготовка Delta-Engine (Stage 2).

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
