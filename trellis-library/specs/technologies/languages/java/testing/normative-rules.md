# Normative Rules

* Java tests must remain automatic, independent, and repeatable so confidence does not depend on manual orchestration or execution order.
* Tests should use executable assertions rather than console output or human inspection as the primary proof of correctness.
* Test sources and supporting fixtures must live in the test-only structure expected by the build and tooling, rather than mixing with production sources.
* Test-case design should cover correct behavior, boundary conditions, and error behavior intentionally rather than sampling only the happy path.
* Coverage expectations should scale with risk and criticality, using stronger statement and branch coverage expectations for core or failure-sensitive logic than for incidental glue code.
* Test setup must create its own required state or fixtures rather than assuming ambient database, filesystem, or remote environment contents.
* Tests should avoid constructor-heavy, global-state-heavy, or externally entangled designs that make the code effectively untestable without structural refactoring.
* Test design should preserve AIR-style behavior: automatic execution, independence between cases, and repeatability across runs and environments.
* Java test cases should intentionally cover BCDE-style dimensions where relevant: boundary conditions, correct flow, design-critical invariants, and error behavior.
* Coverage targets should remain explicit enough that teams can distinguish baseline statement coverage expectations from stronger branch-coverage expectations for core modules.
