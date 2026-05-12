# Normative Rules

* Exception flow should preserve meaningful failure categories instead of collapsing everything into generic runtime failure.
* Checked and unchecked exceptions should be chosen intentionally based on caller expectations and recovery responsibility.
* Boundary layers should translate low-level implementation failures into higher-level failure meaning where consumers need stability.
* Exceptions must not be swallowed, over-wrapped, or logged redundantly in ways that destroy causality.
* Error-handling conventions should remain consistent enough that readers can predict where failures are surfaced and transformed.
* Exception handling should distinguish validation failure, domain rejection, dependency failure, and unexpected system error rather than flattening them into one response path.
* Transactional or multi-step write flows must propagate failure strongly enough to prevent partial-success behavior from being mistaken for completion.
