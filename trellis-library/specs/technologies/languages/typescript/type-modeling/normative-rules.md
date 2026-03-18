# Normative Rules

* Types should model real invariants and interface boundaries rather than merely mirroring current implementation shortcuts.
* Public types must balance precision and usability so consumers can understand constraints without excessive guesswork.
* Unsound escape hatches should be narrow, explicit, and not normalized as routine design.
* Type refinements should reduce ambiguity around nullable, optional, or stateful data where those distinctions matter.
* Type structure should evolve with contract meaning rather than drifting into misleading compatibility shells.
