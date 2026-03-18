# Normative Rules

* iOS application behavior must account for app and scene transitions between
  active, inactive, background, and restored states where those transitions
  affect correctness.
* Important user state must not rely only on volatile memory when suspension or
  restoration can interrupt normal control flow.
* Lifecycle-sensitive work should remain predictable across resume, interruption,
  and restoration instead of assuming uninterrupted execution.
* iOS lifecycle transitions must not silently duplicate, abandon, or partially
  replay meaningful work without explicit handling.
* Platform-specific restoration and background assumptions should remain visible
  rather than hidden behind framework lifecycle callbacks alone.
