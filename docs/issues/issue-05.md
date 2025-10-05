# Issue #5 — Mask: CRUD атомов и контекстов + админ-UI

**Labels:** stage1, backend, frontend, ux

* API: `POST/GET/PATCH /atoms`, `POST /contexts`.
* Поля: type, bloom, granularity, prerequisites, misconceptions, citations[], status, version.
* Админ-экран: список атомов, редактор с автоподсветкой цитат, статусы `draft/reviewed/approved`.
* Граф-виз (Cytoscape) локального подграфа; фильтр «на дату».

DoD:
* CRUD работает; цитаты обязательны.
* Граф рендерится < 1.5 с на 500 узлах локального подграфа.
