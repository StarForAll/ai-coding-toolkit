# Normative Rules

* Secrets must be kept separate from ordinary configuration wherever possible.
* Sensitive values must not be committed, echoed, or exposed in reusable library assets.
* Missing required secrets must fail closed for protected operations.
* Environment-specific overrides must be explicit and reviewable.
* Debug or local convenience settings must not silently weaken production security expectations.
