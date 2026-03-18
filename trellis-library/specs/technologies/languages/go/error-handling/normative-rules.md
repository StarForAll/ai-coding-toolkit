# Normative Rules

* Errors should remain explicit in function contracts rather than hidden behind ambiguous side channels.
* Wrapping should preserve causality and add meaning, not merely increase string noise.
* Callers should be able to distinguish meaningful failure categories without depending on brittle string matching.
* Error handling must not normalize ignored returns or shallow pass-throughs where boundary translation is needed.
* Conventions for wrapping, comparison, and propagation should remain predictable across packages.
