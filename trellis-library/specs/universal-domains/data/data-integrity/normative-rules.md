# Normative Rules

* Critical data invariants must be explicit rather than assumed.
* Invalid or contradictory states must be prevented, rejected, or made visible as exceptions.
* Operations that may be retried or replayed should define idempotency or equivalent integrity protections.
* Integrity guarantees must account for concurrent updates, partial failures, and cross-system boundaries where relevant.
* When integrity cannot be fully enforced, the remaining exposure and detection strategy must be explicit.
