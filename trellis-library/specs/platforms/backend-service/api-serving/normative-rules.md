# Normative Rules

* Service-exposed APIs should behave predictably under load, partial dependency failure, timeout pressure, and retry conditions where those factors affect clients.
* Request-serving behavior must preserve clear boundary handling for validation, authorization, execution, and failure response.
* APIs must not assume ideal dependency conditions when service runtime reality includes latency, overload, or partial outages.
* Platform-level serving concerns such as concurrency pressure, timeout semantics, and backpressure should remain visible in design assumptions.
* Operational serving behavior should remain understandable enough that client and operator expectations can be aligned.
