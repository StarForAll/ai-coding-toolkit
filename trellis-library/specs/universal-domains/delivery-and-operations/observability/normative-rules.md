# Normative Rules

* Meaningful operational behavior must produce inspectable signals that support verification and diagnosis.
* Observability should capture user-impacting failures and important state transitions, not only low-level noise.
* Signals must preserve enough context to support correlation between events, actions, and outcomes.
* Logging or metrics volume must not substitute for clarity, relevance, or ownership.
* When observability gaps remain, the reduced operating confidence must be made explicit.
* Structured logs and equivalent signals should include stable business or request identifiers when those identifiers are required to reconstruct causality across service boundaries.
* Runtime logs should prefer structured or parameterized fields over ad-hoc string concatenation when variable values must remain queryable, safely escaped, or redactable.
* Business-relevant execution logs should identify the operation consistently and cover ingress, dependency calls, state-changing writes, and failure exits where those checkpoints are required for diagnosis.
* Sensitive values should be redacted, omitted, or transformed before they enter logs, traces, or metrics payloads.
* Key execution checkpoints should be observable at the start, critical branch, failure, and completion boundaries when missing them would block diagnosis.
