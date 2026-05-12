# Normative Rules

* External input must be validated at the boundary where trust changes.
* Shape validation alone is insufficient when semantic constraints matter.
* Invalid, malformed, or unsafe input must be rejected or handled safely before deeper processing.
* Validation responsibilities must be explicit rather than assumed to happen elsewhere.
* Reusable workflows must not treat unvalidated input as trustworthy by default.
* Nested structures, collections, and optional sub-objects must not bypass boundary validation merely because the top-level payload passed shape checks.
* Boundary validation and domain-state validation should remain distinguishable so reviewers can see which rules are enforced by schema and which depend on business context.
* Input validation must include operational guardrails where size, cardinality, sort fields, redirect targets, or pattern complexity can trigger abuse or resource exhaustion.
