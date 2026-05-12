# Normative Rules

* Test strategy must be chosen based on risk, change scope, and the behaviors most likely to regress.
* The smallest sufficient test layer should be preferred, but not at the cost of leaving critical behaviors unverified.
* Work that changes cross-layer behavior must not rely on a single narrow unit-level check.
* Manual checks may complement automation, but must not be used to hide missing high-value automated coverage.
* When no practical automated test exists, the limitation and compensating verification must be made explicit.
* Test suites should preserve automatic, repeatable, and execution-order-independent behavior so confidence does not depend on manual orchestration.
* High-risk or core behaviors should define stronger coverage expectations than incidental utility code, especially where branch behavior drives user or financial outcomes.
* Test design should cover correct cases, boundaries, design-critical invariants, and error paths intentionally rather than sampling only obvious success cases.
