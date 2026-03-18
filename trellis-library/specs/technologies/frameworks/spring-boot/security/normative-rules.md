# Normative Rules

* Spring-based security behavior should preserve clear boundaries between authentication, authorization, transport handling, and business logic.
* Security decisions must not rely on hidden framework defaults that reviewers cannot easily inspect.
* Request protection flow should remain explicit enough that failure behavior and access decisions are predictable.
* Controllers and service methods must not duplicate or contradict framework-level security boundaries without explicit justification.
* Security conventions should remain consistent enough that new endpoints inherit protection expectations predictably.
