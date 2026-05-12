# Verification

Check the following:

* schema naming is explicit and internally consistent
* fields and keys communicate stable domain meaning
* ambiguous catch-all structures are not hiding weak modeling
* defaults and constraints support intended semantics
* the schema remains understandable without project-private assumptions
* common lifecycle metadata is modeled consistently where the project relies on it
* table, column, and index naming follow one durable convention
* indexes have an explicit lookup, uniqueness, or ordering purpose
* flag-style columns communicate explicit value semantics through naming and type choice
* field types preserve precision, indexing, and growth expectations intentionally
* relationship and redundancy choices reflect an explicit consistency strategy
* naming remains compatible with case-sensitive operational environments and migration tooling
* lifecycle baseline fields such as identifiers and create/update timestamps are present where the persistence model relies on them
* oversized text payloads are separated from ordinary indexed attributes when row shape or indexing would otherwise degrade
