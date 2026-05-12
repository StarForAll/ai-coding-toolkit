# Verification

Check the following:

* important runtime behavior is observable
* user-impacting failures and state transitions are visible
* diagnostic signals carry enough context for correlation
* noise is not replacing actionable telemetry
* remaining observability gaps are explicit
* structured signals include stable identifiers needed for cross-step causality
* logs use structured or parameterized fields where runtime values must stay queryable and safe
* operation-level logging covers ingress, dependency calls, state-changing writes, and failure exits where diagnosis depends on them
* sensitive values are redacted or excluded from diagnostic output
* key execution checkpoints are observable where missing them would block diagnosis
* failure logs preserve both business-scene context and underlying failure evidence where diagnosis needs both
* retention and classification match the audit and operational value of the emitted signals
