# Normative Rules

* Backend services must treat startup, readiness, steady-state operation, degradation, and shutdown as distinct runtime states where they affect correctness.
* Runtime assumptions about external dependencies, retry behavior, and process restarts must remain explicit.
* Service behavior should fail predictably when dependencies are unavailable rather than hanging in ambiguous half-ready states.
* Lifecycle-sensitive work must account for restart, replay, and shutdown conditions rather than assuming uninterrupted execution.
* Platform runtime constraints should remain visible even when hidden behind framework startup abstractions.
