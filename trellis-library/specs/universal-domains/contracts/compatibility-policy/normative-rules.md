# Normative Rules

* Contract changes must be evaluated for consumer impact before they are treated as routine implementation detail.
* Breaking changes should be explicit, justified, and paired with a migration or containment strategy when consumers exist.
* Additive changes must still be reviewed for hidden compatibility risk such as changed defaults, ordering, timing, or semantics.
* Compatibility guarantees must be stated at the same boundary where consumers depend on them.
* When compatibility status is unknown, the change must be treated as carrying integration risk rather than assumed safe.
