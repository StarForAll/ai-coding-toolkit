# Normative Rules

* Spring Boot controllers should preserve a clear boundary between transport concerns, validation, authorization, orchestration, and domain execution.
* Web-layer behavior must not hide contract drift behind implicit framework defaults or annotation convenience.
* Request handling should remain explicit enough that failure translation and client-visible behavior are predictable.
* Controllers must not absorb domain logic merely because the framework makes it easy to do so.
* Web-layer conventions should remain consistent enough that request flow is reviewable across endpoints.
