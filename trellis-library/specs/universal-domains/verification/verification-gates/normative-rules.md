# Normative Rules

* Verification gates must be defined before claiming completion on meaningful code changes.
* Gate results must be tied to concrete commands, checks, or review activities.
* Failed gates must block completion until resolved or explicitly downgraded by policy.
* Missing gates must be reported as an evidence gap, not silently ignored.
* Manual verification must be treated as a first-class gate when automation is insufficient.
* If a workflow installation defines a mandatory quality-platform project id, workflow stage entry and state-changing operations must block when that id is missing or invalid.
* When `sonar verify -p <project-id>` is the declared quality-platform gate, it must run before completion claims; failures must be fixed with similar-issue review and the same gate rerun until it passes.
