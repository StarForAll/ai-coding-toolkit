# Normative Rules

* React state should live where ownership is clear and propagation remains understandable.
* Shared state must not become a silent escape hatch for unresolved component-boundary problems.
* Remote, derived, transient, and persisted state should remain distinguishable where their update and failure behavior differ.
* Side-effect coordination must not introduce hidden state transitions that are difficult to reason about from the component tree.
* Dataflow conventions should remain consistent enough that readers can follow update paths without reconstructing implicit framework behavior.
