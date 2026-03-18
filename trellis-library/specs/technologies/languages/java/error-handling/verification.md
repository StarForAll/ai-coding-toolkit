# Verification

Check the following:

* failure categories remain meaningful across exception flow
* checked and unchecked exceptions are used intentionally
* boundary translation preserves stable failure meaning
* causality is not destroyed by swallowing, over-wrapping, or redundant logging
* exception-handling conventions are predictable across the codebase
