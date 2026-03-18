# Normative Rules

* React components should separate view composition, state ownership, and side-effect orchestration clearly enough to stay reviewable.
* Props and rendered composition boundaries must remain understandable without hidden coupling to distant component internals.
* State should live at the narrowest level that preserves correctness without forcing unstable prop drilling or silent global coupling.
* Reusable components must not mix framework convenience with accidental business logic in ways that make reuse misleading.
* Similar interaction patterns should be implemented with consistent component conventions rather than ad hoc local styles.
