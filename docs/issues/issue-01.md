# Issue #1 — Infra: базовый Docker-стек и деплой

**Labels:** stage1, infra

* Развернуть Docker Compose стек: Postgres, MinIO, Qdrant, Neo4j, Redis, Tika, Piper, Nginx.
* Подготовить `.env.example` и секреты.
* Включить health-checks, логи, бэкапы.
* Настроить reverse-proxy и TLS (Let’s Encrypt).

DoD:
* `docker-compose up -d` поднимает все сервисы без ошибок.
* Health endpoints зелёные; доступ к UI по HTTPS.
* Ежедневные бэкапы Postgres/MinIO/Neo4j/Qdrant (manual restore проверен).
