# Архитектура (Stage 1)

```mermaid
graph TB
  user[Публичный/Админ UI (Next.js / позже)]
  gateway[API Gateway (FastAPI)]
  ingest[Ingest]
  parser[Parser (Tika/Unstructured/OCR)]
  indexer[Indexers (Embeddings/Qdrant)]
  graphdb[(Neo4j)]
  pg[(PostgreSQL)]
  obj[(MinIO)]
  qdr[(Qdrant)]

  user --> gateway
  gateway --> ingest --> parser
  parser --> obj
  parser --> pg
  parser --> graphdb
  parser --> indexer --> qdr
  gateway --> pg
  gateway --> graphdb
  gateway --> qdr
  gateway --> obj
```

```
