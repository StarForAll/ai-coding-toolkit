# Normative Rules

* Background and scheduled work must define execution ownership, retry assumptions, and failure visibility explicitly.
* Async work should not rely on request-time assumptions that disappear once execution becomes deferred or decoupled.
* Jobs, retries, and schedulers must account for duplicate execution, partial failure, and restart behavior where relevant.
* Operational visibility for asynchronous work must be strong enough to detect stuck, repeated, or silently failing execution.
* When async execution semantics are uncertain, downstream correctness must not assume perfect single-run behavior.
