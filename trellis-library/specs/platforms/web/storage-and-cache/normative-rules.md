# Normative Rules

* Browser-side stored state must have clear ownership, lifecycle, and invalidation expectations.
* Cached client behavior must not silently outlive the assumptions that made the cached data safe or relevant.
* Sensitive or high-risk data should not be persisted in browser-accessible storage without explicit justification and containment.
* Reload, multi-tab, logout, and stale-session behavior should be considered when storage affects user-visible state.
* Storage and cache behavior must remain understandable enough that stale or conflicting client state can be diagnosed.
