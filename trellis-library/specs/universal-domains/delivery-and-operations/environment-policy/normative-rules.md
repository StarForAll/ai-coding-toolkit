# Normative Rules

* Environments must have explicit roles rather than being treated as interchangeable runtime copies.
* Promotion between environments should follow a defined path with verification expectations at each meaningful boundary.
* Production assumptions must not be inferred from local or lower-environment behavior without explicit evidence.
* Environment-specific configuration differences must be visible and controlled rather than hidden in tribal knowledge.
* Work that cannot state which environment assumptions it relies on must be treated as carrying operational uncertainty.
