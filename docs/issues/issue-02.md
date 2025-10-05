# Issue #2 — Ingest/Parser: загрузка и нормализация источников

**Labels:** stage1, backend

* Эндпоинты: `POST /ingest/upload`, `POST /ingest/url`, `GET /sources`.
* Парсинг PDF/DOCX/PPTX/XLSX/URL через Tika + unstructured + OCR (Tesseract).
* Модель `source` + реквизиты/лицензии + `valid_from/valid_to`.
* Разметка `norm_unit` до подпункта, извлечение `chunk` с координатами.
* Очереди Celery (batch).

DoD:
* Загруженные файлы парсятся в `source/norm_unit/chunk`.
* Дубликаты отфильтрованы; метаданные заполнены; статусы задач видны.
