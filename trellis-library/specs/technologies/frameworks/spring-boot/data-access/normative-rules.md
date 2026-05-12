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
