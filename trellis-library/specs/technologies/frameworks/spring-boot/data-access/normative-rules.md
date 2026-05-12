# Normative Rules

* Data-access code should preserve a clear boundary between persistence concerns and domain or orchestration logic.
* Repository or persistence abstractions must not silently absorb workflow logic that belongs elsewhere.
* Persistence-facing models, query behavior, and transactional assumptions should remain understandable enough to review for correctness and performance risk.
* Framework convenience must not normalize cross-layer reach-through from controllers or unrelated services into persistence details.
* Data-access conventions should stay consistent enough that storage behavior is predictable across modules.
* Query construction must use parameter binding or equivalent safe composition rather than string interpolation that can reintroduce injection risk through convenience APIs.
* Complex query behavior should remain reviewable in a dedicated persistence boundary rather than hidden inside controller or service-side string assembly.
* Batch writes, pagination strategy, and related-data fetching should make scale assumptions explicit instead of assuming small datasets forever.
* Persistence-local transaction assumptions should stay reviewable, especially when mixed data sources, repository side effects, or hidden write coupling would make one apparent boundary non-atomic.
* Persistence queries must select explicit fields and mappings where wildcard fetching would hide contract drift, inflate payload cost, or couple storage shape to callers.
* ORM mapping between database fields and Java properties should remain explicit enough that boolean naming, partial updates, and generated mappings do not silently corrupt state.
* Persistence updates should avoid rewriting unchanged fields or issuing correction SQL without an explicit verification step when the blast radius is hard to review.
* Database-specific features such as stored procedures, cascades, or ORM pagination shortcuts must not hide portability, performance, or correctness risk behind convenience.
* Join shape, count strategy, and index usage assumptions must remain explicit enough that multi-table queries and aggregate reads can be reviewed for cost and correctness.
* Index naming, uniqueness intent, and prefix strategy should stay consistent enough that reviewers can infer lookup purpose without reverse engineering every migration.
* Query semantics for `count`, `NULL`, pagination, and correction writes must stay explicit enough that aggregate accuracy, empty-result behavior, and deep-page cost are reviewable.
* Multi-table joins should remain bounded and indexed strongly enough that relationship traversal does not silently become the default read strategy for growing data shapes.
* ORM parameter binding must preserve safe prepared-statement semantics, and mapping style should prefer explicit result contracts over convenience shortcuts that blur field-to-type correspondence.
* Transaction annotations and persistence-side transactions should remain bounded to the consistency need, rather than becoming a default wrapper that hides rollback, cache, or side-effect coupling.
