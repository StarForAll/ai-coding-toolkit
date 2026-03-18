# Normative Rules

* macOS permission-gated capabilities must treat permission state as a runtime
  dependency rather than assuming access will be granted when the feature is
  invoked.
* Permission checks should happen explicitly before high-impact feature use so
  denial, restriction, or not-determined states are visible in control flow.
* Applications must not rely on permission dialog behavior being identical
  between unsigned development builds and signed production builds.
* When macOS permission access is denied or unavailable, the application should
  guide the user toward a recoverable settings path instead of repeatedly
  prompting or failing silently.
* Platform-specific permission assumptions, entitlements, and consent recovery
  steps should remain diagnosable enough that support and testing workflows can
  reproduce failures intentionally.
