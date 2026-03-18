# Normative Rules

* Page behavior must account for load, refresh, visibility change, resume, and teardown transitions where those states affect correctness.
* Client state that must survive navigation or refresh should not depend on fragile in-memory assumptions alone.
* Side effects tied to page lifecycle should remain predictable across repeated visits, interrupted sessions, and backgrounding behavior.
* Page lifecycle transitions must not silently duplicate, abandon, or partially replay meaningful work without explicit handling.
* When lifecycle behavior differs across browsers or runtime modes, the remaining uncertainty should remain visible.
