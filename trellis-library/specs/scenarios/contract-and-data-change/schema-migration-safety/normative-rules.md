# Normative Rules

* Schema changes must identify compatibility impact before implementation is treated as safe.
* Migration steps should be decomposed so validation and rollback risk remain visible.
* Backfill, repair, or data-shape transition work must not be hidden inside an ordinary feature change.
* If rollback is not practical, the workflow must state that explicitly.
* Schema migration claims must not ignore dependent contracts, consumers, or data integrity constraints.
