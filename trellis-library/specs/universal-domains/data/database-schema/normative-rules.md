# Normative Rules

* Schema structures must reflect domain meaning rather than temporary implementation convenience.
* Names for entities, fields, keys, and status values should be consistent, explicit, and durable.
* Ambiguous multi-purpose fields must not replace clearer structural modeling without justification.
* Constraints and defaults should reinforce intended semantics rather than hide uncertain modeling decisions.
* Schema shape should remain understandable to readers who are not carrying hidden project context.
* Common lifecycle metadata such as identifiers, creation timestamps, update timestamps, soft-delete markers, and version fields should be modeled consistently when they are part of the project’s persistence conventions.
* Table, column, and index naming should follow one durable convention so operational review, query writing, and migration diffing do not depend on local guesswork.
* Index definitions should reflect actual lookup, uniqueness, and ordering requirements rather than accumulating speculative or unnamed structures.
