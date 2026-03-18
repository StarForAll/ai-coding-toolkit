# Verification

Check the following:

* client-side stored state has clear ownership and lifecycle
* invalidation expectations are explicit
* sensitive data is not persisted casually in browser-accessible storage
* reload, multi-tab, logout, and stale-session behavior were considered
* stale or conflicting client state remains diagnosable
