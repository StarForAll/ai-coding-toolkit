# Normative Rules

* Dependency direction must be explicit for meaningful architectural layers or modules.
* Dependencies should point toward more stable, lower-volatility abstractions rather than toward volatile implementation details.
* Cross-layer shortcuts must not be introduced as convenience fixes without updating the architectural model.
* Shared code must not become an uncontrolled dumping ground for bypassing dependency rules.
* When a dependency exception is necessary, its scope and containment must be explicit.
* Substitutability expectations should remain preserved so callers depending on an abstraction are not broken by a concrete subtype that narrows or violates the contract.
* Composition or aggregation should be preferred over inheritance where reuse does not require a stable behavioral subtype relationship.
* Dependencies should favor abstractions and contracts where volatility, extension, or cross-module collaboration would otherwise couple callers directly to concrete implementation details.
