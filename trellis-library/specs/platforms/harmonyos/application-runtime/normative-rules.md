# Normative Rules

* HarmonyOS application behavior must account for platform-managed lifecycle
  transitions where ability activation, backgrounding, or restoration affects
  correctness.
* Important state must not depend solely on volatile runtime assumptions when
  platform-managed transitions can interrupt or recreate execution.
* Lifecycle-sensitive work should remain predictable across activation,
  deactivation, and restored paths.
* HarmonyOS runtime transitions must not silently duplicate, abandon, or
  partially replay meaningful work without explicit handling.
* Platform-specific lifecycle and state-continuity assumptions should remain
  visible rather than being hidden behind framework abstraction confidence.
