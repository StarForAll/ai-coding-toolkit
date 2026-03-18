# Normative Rules

* Miniapp behavior must account for host-controlled lifecycle, visibility, and
  execution constraints instead of assuming a full standalone application
  runtime.
* Important state must not depend solely on fragile in-memory assumptions when
  host-managed suspension, page replacement, or limited persistence can occur.
* Miniapp features should remain predictable under host-imposed capability,
  navigation, and resource limitations.
* Host-runtime transitions must not silently duplicate, abandon, or partially
  replay meaningful work without explicit handling.
* Platform capability assumptions should remain visible enough that container
  restrictions and degraded behavior can be reasoned about explicitly.
