# Normative Rules

* Cached or replicated data must have explicit freshness and invalidation expectations.
* Systems should not silently assume strong consistency where cache lag, replica lag, or asynchronous propagation can violate that assumption.
* Invalidation responsibility must be clear enough that stale behavior can be reasoned about and debugged.
* Read optimization must not hide correctness risk when user-visible or business-critical behavior depends on freshness.
* When consistency is probabilistic or delayed, that behavior must remain explicit at the affected boundary.
* Cached entries should have a bounded lifetime or explicit refresh discipline rather than persisting indefinitely by neglect.
* Cache-miss fallback and null-result handling should prevent repeated penetration of the authoritative data source under abusive or high-volume miss patterns.
* Update flows should make the ordering between source-of-truth writes and cache invalidation or refresh explicit enough to reason about stale windows.
