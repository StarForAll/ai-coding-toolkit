# Refactoring Safety Checklist

* Refactor scope is bounded before implementation expands.
* Intended behavior preservation is explicit.
* Verification covers the behaviors most likely to regress.
* Structural cleanup is not being used to smuggle in unrelated feature changes.
* Stop or rollback conditions are defined for unsafe drift.
