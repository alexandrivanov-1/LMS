# Issue #4 — Graph: Neo4j модель и построение связей

**Labels:** stage1, backend, data

* Узлы: `Source`, `NormUnit`, `Chunk`, `KnowledgeAtom`, `Artifact`.
* Рёбра: `HAS_UNIT`, `HAS_CHUNK`, `EVIDENCED_BY`, `PREREQUISITE_OF`, `AFFECTS`, `VALID_DURING(from,to)`.
* Cypher-скрипты построения из Postgres.

DoD:
* Выборка `NormUnit -> Chunk <- KnowledgeAtom` работает.
* Фильтр «на дату» по `VALID_DURING` отрабатывает.
