# Verification

Check the following:

* branch exits, fallthrough behavior, and terminal paths are explicit enough to review
* `switch` cases terminate intentionally and visible fallthrough is justified
* external `String` values are normalized or checked before null-sensitive `switch` behavior
* braces are used consistently where omission would make edits unsafe
* nested conditionals stay shallow enough to review without losing the main path
* guard clauses are used where they materially clarify the happy path
* loop bodies do not hide expensive or correctness-sensitive work that should be hoisted or separated
* condition expressions stay readable and do not bury assignment or side-effectful logic
