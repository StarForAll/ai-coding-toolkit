# Normative Rules

* Cached or replicated data must have explicit freshness and invalidation expectations.
* Systems should not silently assume strong consistency where cache lag, replica lag, or asynchronous propagation can violate that assumption.
* Invalidation responsibility must be clear enough that stale behavior can be reasoned about and debugged.
* Read optimization must not hide correctness risk when user-visible or business-critical behavior depends on freshness.
* When consistency is probabilistic or delayed, that behavior must remain explicit at the affected boundary.
