# Normative Rules

* Changes with meaningful blast radius must define whether and how they can be rolled back.
* Rollback assumptions must be verified against real dependencies, state changes, and irreversible side effects where relevant.
* When rollback is not practical, release decisions must compensate with stronger gating, containment, or staged exposure.
* Rollback triggers must be based on observable conditions rather than vague operator intuition.
* Temporary hesitation to roll back must not be treated as evidence that rollback is unnecessary.
