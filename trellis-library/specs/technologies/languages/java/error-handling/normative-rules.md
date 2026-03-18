# Normative Rules

* Exception flow should preserve meaningful failure categories instead of collapsing everything into generic runtime failure.
* Checked and unchecked exceptions should be chosen intentionally based on caller expectations and recovery responsibility.
* Boundary layers should translate low-level implementation failures into higher-level failure meaning where consumers need stability.
* Exceptions must not be swallowed, over-wrapped, or logged redundantly in ways that destroy causality.
* Error-handling conventions should remain consistent enough that readers can predict where failures are surfaced and transformed.
