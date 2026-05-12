# Normative Rules

* Spring Boot controllers should preserve a clear boundary between transport concerns, validation, authorization, orchestration, and domain execution.
* Web-layer behavior must not hide contract drift behind implicit framework defaults or annotation convenience.
* Request handling should remain explicit enough that failure translation and client-visible behavior are predictable.
* Controllers must not absorb domain logic merely because the framework makes it easy to do so.
* Web-layer conventions should remain consistent enough that request flow is reviewable across endpoints.
* HTTP method choice, route semantics, and response shape should reflect operation intent consistently enough that clients can infer safe versus mutating behavior.
* Boundary validation should reject malformed requests early, while business-rule validation that depends on domain state must remain visible as a deeper concern rather than annotation folklore.
* Public request and response models must not expose persistence entities directly.
* Mapping boundaries should remain explicit enough that storage-only fields or nested objects are not leaked by shallow-copy convenience.
* Endpoint documentation or equivalent contract description should be maintained at the boundary where client-facing behavior is defined, rather than relying on unstated endpoint conventions.
* Controller handlers should keep conditional branching and incidental business decisions shallow enough that orchestration remains reviewable, pushing deeper flow decisions into service-level collaborators.
* Batch, pagination, export, or query-shaping request parameters must be validated against operational limits before they can amplify backend load.
