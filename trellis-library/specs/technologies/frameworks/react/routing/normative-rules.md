# Normative Rules

* React routing should preserve clear boundaries between navigation state, page ownership, and shared application concerns.
* Route params, search state, and route-driven data loading must remain explicit enough to reason about refresh, direct entry, and transition behavior.
* Route-level guards, redirects, and loading transitions must not become hidden orchestration that obscures user-visible flow.
* Nested route structure should improve clarity of screen composition rather than scattering state ownership across unrelated layers.
* Routing conventions should remain stable enough that new screens inherit understandable navigation behavior.
