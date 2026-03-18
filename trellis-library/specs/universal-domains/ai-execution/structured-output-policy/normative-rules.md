# Normative Rules

* Structured outputs must conform to their declared schema or shape contract.
* Undeclared fields must not appear when strict output is required.
* Partial or truncated structured output must be treated as invalid unless explicitly supported.
* Structured outputs used for automation must remain deterministic enough for downstream parsing.
* When structure cannot be guaranteed, the workflow must downgrade the claim and avoid pretending the output is safely consumable.
