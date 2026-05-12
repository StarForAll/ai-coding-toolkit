# Normative Rules

* Control flow must make ordinary, exceptional, and terminal paths explicit enough that readers can predict which branch exits, continues, or falls through.
* `switch` statements should terminate each case explicitly, and any intentional fallthrough must remain visible and justified rather than accidental.
* `switch` handling over external `String` input must not assume non-null values without an explicit precondition or earlier normalization step.
* Branching constructs must use braces consistently where omission would make later edits unsafe or visually ambiguous.
* Conditional nesting should remain shallow enough that reviewers can reason about the decision tree, preferring guard clauses or extracted decisions once nesting obscures intent.
* Guard-clause structure should be used when early rejection, early return, or fail-fast branching makes the main success path clearer than a deep `if/else` ladder.
* Loop bodies must avoid hidden high-cost work or side effects whose placement inside the iteration materially changes performance or correctness assumptions.
* Conditional expressions should remain readable enough that assignment, negation, and multi-step side effects are not hiding the real decision boundary.
