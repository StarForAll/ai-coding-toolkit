# Normative Rules

* Configuration changes must be treated as behavior changes when they can alter runtime outcomes, not as low-risk metadata by default.
* The affected environments, defaults, and dependency assumptions must be visible before rollout.
* Config changes should preserve a clear path to revert or disable unsafe behavior when impact is meaningful.
* Hidden coupling between configuration and code behavior must not be ignored just because no code diff exists.
* When configuration state cannot be observed confidently after rollout, the change must be treated as carrying elevated operational risk.
