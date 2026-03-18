# Normative Rules

* Risky release work should identify rollback expectations before release handoff.
* If rollback is not practical or not equivalent to restore, that limitation must be stated explicitly.
* Rollback assumptions must align with the real change shape, not only code deployment mechanics.
* Release-readiness claims must not ignore rollback uncertainty.
* If runtime observability is required to judge rollback success, that dependency should be stated before release.
