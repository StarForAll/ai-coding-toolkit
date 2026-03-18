# Normative Rules

* Test strategy must be chosen based on risk, change scope, and the behaviors most likely to regress.
* The smallest sufficient test layer should be preferred, but not at the cost of leaving critical behaviors unverified.
* Work that changes cross-layer behavior must not rely on a single narrow unit-level check.
* Manual checks may complement automation, but must not be used to hide missing high-value automated coverage.
* When no practical automated test exists, the limitation and compensating verification must be made explicit.
