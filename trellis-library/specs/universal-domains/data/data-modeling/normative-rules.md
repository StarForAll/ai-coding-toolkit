# Normative Rules

* Data structures should reflect stable meaning, not only immediate implementation convenience.
* Identity, ownership, and lifecycle should be explicit where data persists or crosses boundaries.
* Fields with different meanings should not be collapsed into overloaded generic structures without strong justification.
* Data models should account for how state evolves over time, not only snapshot representation.
* Model changes with broad downstream impact should be treated as design changes rather than incidental edits.
