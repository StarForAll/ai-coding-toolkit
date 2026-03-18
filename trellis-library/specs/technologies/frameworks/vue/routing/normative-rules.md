# Normative Rules

* Vue route structure should preserve understandable boundaries between navigation state, page composition, and shared application state.
* Route parameters, query state, and route-driven side effects must remain explicit enough to review for correctness and reload behavior.
* Navigation guards and route-level loading behavior must not become hidden control flow that obscures user-visible transitions.
* Route reuse and nesting should support clarity of screen ownership rather than maximizing abstraction density.
* Routing conventions should remain consistent enough that new views inherit predictable navigation behavior.
