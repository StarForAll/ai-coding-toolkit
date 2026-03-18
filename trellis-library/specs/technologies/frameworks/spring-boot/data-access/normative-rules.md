# Normative Rules

* Data-access code should preserve a clear boundary between persistence concerns and domain or orchestration logic.
* Repository or persistence abstractions must not silently absorb workflow logic that belongs elsewhere.
* Persistence-facing models, query behavior, and transactional assumptions should remain understandable enough to review for correctness and performance risk.
* Framework convenience must not normalize cross-layer reach-through from controllers or unrelated services into persistence details.
* Data-access conventions should stay consistent enough that storage behavior is predictable across modules.
