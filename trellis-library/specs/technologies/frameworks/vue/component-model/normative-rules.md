# Normative Rules

* Vue components should express clear responsibility boundaries rather than mixing presentation, orchestration, and unrelated domain behavior.
* Props, emits, and exposed interfaces must remain understandable enough that component usage does not depend on hidden conventions.
* Local component state should stay close to the behavior it owns and not become a silent replacement for broader state boundaries.
* Reusable components must not overfit one screen's implementation detail while pretending to be generic primitives.
* Component patterns should remain consistent enough that similar UI behaviors are modeled in comparable ways.
