# Normative Rules

* Dependency coordinates must remain explicit, stable, and semantically meaningful enough that module ownership and reuse boundaries are reviewable from the build graph.
* Version identifiers should communicate compatibility intent consistently enough that consumers can distinguish breaking change, additive evolution, and compatible fixes without private tribal knowledge.
* Release builds must not depend on mutable snapshot-like artifacts where reproducibility and rollback confidence require immutable dependency inputs.
* Shared dependency families should use centralized version management or an equivalent reviewable mechanism rather than drifting across modules by copy-pasted version strings.
* A build must not resolve multiple conflicting versions of the same logical dependency without an explicit arbitration strategy and impact review.
* Reusable library modules should expose only the minimum dependency surface necessary for their contract, avoiding hidden transitive coupling or bundled implementation choices that force consumers into accidental upgrades.
