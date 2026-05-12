# Normative Rules

* Exception flow should preserve meaningful failure categories instead of collapsing everything into generic runtime failure.
* Checked and unchecked exceptions should be chosen intentionally based on caller expectations and recovery responsibility.
* Boundary layers should translate low-level implementation failures into higher-level failure meaning where consumers need stability.
* Exceptions must not be swallowed, over-wrapped, or logged redundantly in ways that destroy causality.
* Error-handling conventions should remain consistent enough that readers can predict where failures are surfaced and transformed.
* Exception handling should distinguish validation failure, domain rejection, dependency failure, and unexpected system error rather than flattening them into one response path.
* Transactional or multi-step write flows must propagate failure strongly enough to prevent partial-success behavior from being mistaken for completion.
* Exceptions must not be used as ordinary branch control where precondition checks or explicit result handling can express the behavior more safely.
* `catch` scope should stay narrow enough that stable code is not masked together with genuinely uncertain operations.
* Resource cleanup must remain reliable under failure, using language constructs that preserve the original failure when possible.
* Top-level failure boundaries should either translate failures for the consumer or rethrow them intact rather than discarding operationally important context.
