# Normative Rules

* Static TypeScript types must not be treated as proof that untrusted runtime data is valid.
* Data crossing process, network, storage, or user-input boundaries should have explicit runtime trust assumptions.
* Narrowing, parsing, and validation should occur close enough to runtime boundaries that later code can rely on clearer invariants.
* Unsound casting must remain exceptional and visible rather than normalized as the default boundary strategy.
* Runtime-boundary handling should stay consistent enough that trusted and untrusted data paths are distinguishable.
