# Normative Rules

* Browser networking behavior must account for latency, interruption, retry ambiguity, and partial connectivity instead of assuming stable ideal transport.
* Client requests should preserve clear ownership of loading, cancellation, timeout, and stale-response handling where those behaviors affect correctness.
* Network-driven UI state must not silently conflate "not yet loaded", "failed", "stale", and "empty" when those states require different user handling.
* Client retry or refresh behavior should not amplify server load or user confusion without explicit control.
* Web-network assumptions should remain visible enough that offline, degraded, or reordered responses can be reasoned about.
