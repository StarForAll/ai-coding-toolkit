# Normative Rules

* Modules should have explicit responsibilities rather than acting as generic dumping grounds.
* Dependency direction should support maintainability and reduce unnecessary coupling.
* Shared logic should move into intentional modules rather than being duplicated across unrelated areas.
* Structural decomposition should follow behavior and ownership, not only file-count convenience.
* A new module should be justified by responsibility clarity, not by arbitrary fragmentation.
* Modules and classes should preserve single responsibility strongly enough that one change reason does not routinely force unrelated edits through the same unit.
