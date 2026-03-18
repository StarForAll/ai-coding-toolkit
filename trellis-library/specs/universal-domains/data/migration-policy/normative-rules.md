# Normative Rules

* Persistent data changes should be decomposed into steps that can be validated and reasoned about.
* Compatibility impact must be identified before migration work is treated as safe.
* Rollback assumptions must be explicit, especially when data mutation is irreversible.
* Data backfill or repair work must not be hidden inside unrelated application changes.
* Migration policy should account for dependent readers, writers, and long-running consumers.
