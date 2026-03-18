# Normative Rules

* Protected actions must require explicit authentication and appropriate authorization.
* Privileged operations must not rely on implicit trust or hidden defaults.
* Permission checks must be aligned with the actual resource or action boundary, not only the UI boundary.
* Escalated actions must be visible, intentional, and auditable.
* Missing or uncertain authorization state must fail safely rather than silently granting access.
