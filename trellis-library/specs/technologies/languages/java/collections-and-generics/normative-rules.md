# Normative Rules

* Collection mutability must remain explicit, and code must not assume a view, singleton, empty collection, or adapter-backed list is freely mutable.
* Code that creates collection views or slices should account for the coupling between the derived view and the original collection rather than treating them as independent copies.
* Iteration and mutation must use collection APIs whose concurrent-modification semantics are safe for the intended access pattern.
* Generic bounds should preserve readable producer-versus-consumer intent rather than relying on wildcard signatures whose operational limits are unclear to callers.
* Raw collections and unchecked generic handoffs must not hide type uncertainty where a later cast can fail far from the source boundary.
* Collection-to-array and array-to-collection conversions should use APIs whose runtime type, mutability, and backing-storage behavior remain explicit.
* Collection sizing and lookup strategy should reflect expected cardinality and access patterns instead of assuming repeated resizing or linear scans are harmless.
* Comparator behavior must satisfy ordering contracts strongly enough that sorting and ordered collections remain stable under runtime use.
* Pattern matching, regular-expression use, and other reusable parsing helpers should avoid per-call recompilation or equivalent hidden cost when the pattern is stable and reused across ordinary execution paths.
