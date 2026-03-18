# Normative Rules

* Externally visible failures must use stable and distinguishable error semantics rather than ad hoc messages alone.
* Error contracts should let consumers identify category, likely cause, and appropriate response without reverse engineering implementation details.
* Similar failure conditions should not produce incompatible error shapes across adjacent boundaries without justification.
* Error contracts must preserve enough detail for action while avoiding accidental leakage of sensitive internals.
* When failure meaning is uncertain or partial, the contract should represent that uncertainty explicitly rather than pretending precision.
