# Verification

Check the following:

* failure categories remain meaningful across exception flow
* checked and unchecked exceptions are used intentionally
* boundary translation preserves stable failure meaning
* causality is not destroyed by swallowing, over-wrapping, or redundant logging
* exception-handling conventions are predictable across the codebase
* validation, domain, dependency, and unexpected failures are not silently merged into one generic category
* transaction-affecting failures cannot return ambiguous partial-success outcomes
* exceptions are not being used as routine control flow where safer checks should exist
* `catch` scope is narrow enough to preserve differentiated handling
* resource cleanup paths remain safe and do not suppress the meaningful failure
* top-level failure boundaries preserve or translate actionable context instead of discarding it
