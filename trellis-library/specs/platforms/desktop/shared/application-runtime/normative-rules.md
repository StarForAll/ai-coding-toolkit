# Normative Rules

* Desktop applications must treat launch, readiness, steady-state operation,
  suspension or backgrounding, and shutdown as distinct runtime states where
  they affect correctness.
* Runtime assumptions about filesystem access, user-session context, local
  configuration, and device availability must remain explicit rather than hidden
  behind development-machine defaults.
* Local failures such as missing files, permission denial, locked resources, or
  unavailable desktop capabilities should degrade predictably instead of
  collapsing into ambiguous client state.
* Application-owned local state must have clear ownership, storage location, and
  recovery expectations when restarts, upgrades, or partial corruption occur.
* Shared desktop-platform constraints should remain visible even when framework
  or toolkit abstractions make the runtime appear uniform across operating
  systems.
