# Normative Rules

* Spring-based security behavior should preserve clear boundaries between authentication, authorization, transport handling, and business logic.
* Security decisions must not rely on hidden framework defaults that reviewers cannot easily inspect.
* Request protection flow should remain explicit enough that failure behavior and access decisions are predictable.
* Controllers and service methods must not duplicate or contradict framework-level security boundaries without explicit justification.
* Security conventions should remain consistent enough that new endpoints inherit protection expectations predictably.
* Request-facing output encoding, binding, and rendering paths must not assume client input is safe simply because framework annotations are present.
* Sensitive or privileged operations should produce auditable security-relevant signals without exposing secrets or raw sensitive payloads.
* State-changing browser-facing flows must preserve request-forgery protections explicitly rather than assuming same-origin UI usage is sufficient.
* User-facing responses should mask or redact sensitive personal data wherever full disclosure is not required for the interaction.
* HTML, template, or browser-consumed output paths must apply context-appropriate escaping or encoding rather than trusting stored or user-supplied content to be display-safe.
* Sensitive platform actions such as messaging, email, payment, ordering, or similar cost-bearing operations must define replay resistance, rate limiting, or abuse controls explicitly.
* User-generated content paths should preserve moderation, anti-spam, or abuse-handling expectations where uncontrolled publication can create operational or trust risk.
