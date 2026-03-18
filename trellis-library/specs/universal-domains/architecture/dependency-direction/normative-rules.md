# Normative Rules

* Dependency direction must be explicit for meaningful architectural layers or modules.
* Dependencies should point toward more stable, lower-volatility abstractions rather than toward volatile implementation details.
* Cross-layer shortcuts must not be introduced as convenience fixes without updating the architectural model.
* Shared code must not become an uncontrolled dumping ground for bypassing dependency rules.
* When a dependency exception is necessary, its scope and containment must be explicit.
