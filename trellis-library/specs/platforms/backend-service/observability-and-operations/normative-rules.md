# Normative Rules

* Backend services must expose enough runtime evidence to support health assessment, failure diagnosis, and release confidence.
* Service health signals should distinguish readiness, liveness, degradation, and dependency failure where those states matter operationally.
* Operational intervention assumptions should remain visible rather than buried inside framework defaults or infrastructure folklore.
* Logs, metrics, and traces should support service-level causality instead of isolated technical fragments only.
* When operational visibility is incomplete, the remaining service risk must be explicit.
