# Normative Rules

* Python package layout should make import boundaries and ownership easy to understand.
* Importable code must not depend on ad hoc path tricks or ambiguous execution context to work reliably.
* Distribution-facing structure should support predictable installation, testing, and reuse rather than local-machine convenience only.
* Top-level package organization should help readers identify domain code, entry points, and support modules quickly.
* Packaging conventions should remain stable enough that moving between modules does not require hidden environment assumptions.
