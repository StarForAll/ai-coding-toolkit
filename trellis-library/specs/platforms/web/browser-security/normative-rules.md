# Normative Rules

* Browser-exposed trust boundaries must remain explicit wherever user-controlled, origin-controlled, or script-controlled data enters the client runtime.
* Security-sensitive client behavior should account for origin rules, script execution surfaces, and storage exposure rather than assuming a trusted browser environment.
* Client-side checks must not be treated as substitutes for server-side enforcement when the browser can be influenced by the user or hostile content.
* Cross-origin, embedded-content, and token-handling assumptions should remain visible enough to review.
* When web-platform security guarantees are partial or environment-dependent, the remaining exposure must be made explicit.
