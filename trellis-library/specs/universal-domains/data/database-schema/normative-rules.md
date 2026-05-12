# Normative Rules

* Schema structures must reflect domain meaning rather than temporary implementation convenience.
* Names for entities, fields, keys, and status values should be consistent, explicit, and durable.
* Ambiguous multi-purpose fields must not replace clearer structural modeling without justification.
* Constraints and defaults should reinforce intended semantics rather than hide uncertain modeling decisions.
* Schema shape should remain understandable to readers who are not carrying hidden project context.
* Common lifecycle metadata such as identifiers, creation timestamps, update timestamps, soft-delete markers, and version fields should be modeled consistently when they are part of the project’s persistence conventions.
* Table, column, and index naming should follow one durable convention so operational review, query writing, and migration diffing do not depend on local guesswork.
* Index definitions should reflect actual lookup, uniqueness, and ordering requirements rather than accumulating speculative or unnamed structures.
* Boolean or flag-style columns should use explicit storage semantics and naming that communicate both allowed values and intent.
* Decimal, text, and identifier field types should be chosen to preserve precision, indexing behavior, and growth expectations rather than relying on permissive defaults.
* Foreign-key-like relationships, cascades, and denormalized copies must reflect an intentional consistency strategy rather than hidden database coupling.
* Table and column naming should remain compatible with case-sensitive operational environments and migration tooling, avoiding patterns whose portability depends on local filesystem or server defaults.
* Common lifecycle fields such as identifiers and create/update timestamps should remain mandatory and consistently named wherever the project relies on them as baseline persistence metadata.
* String-column sizing should preserve indexing and row-shape expectations intentionally, separating oversized or document-style payloads from ordinary indexed attributes when the storage engine would otherwise pay the cost globally.
