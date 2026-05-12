# Verification

Check the following:

* trust boundaries are identified
* shape and semantic validation expectations are explicit
* unsafe input is rejected or contained early
* validation ownership is clear
* unvalidated input is not treated as trusted by default
* nested structures and collections are validated rather than bypassed through shallow top-level checks
* schema-level validation and business-context validation responsibilities are distinguishable
* operational guardrails exist for inputs that can trigger abuse or resource exhaustion
