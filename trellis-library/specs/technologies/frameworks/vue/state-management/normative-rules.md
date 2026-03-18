# Normative Rules

* State in Vue applications should live at the narrowest boundary that still preserves correctness and reuse.
* Shared state must have clear ownership and mutation expectations rather than being treated as an ambient convenience layer.
* Remote data, derived UI state, and user-editable local state should remain distinguishable where their lifecycle and failure modes differ.
* Framework-level reactivity should not hide ambiguous state transitions or stale data assumptions.
* State-management conventions should remain consistent enough that readers can predict where new state belongs.
