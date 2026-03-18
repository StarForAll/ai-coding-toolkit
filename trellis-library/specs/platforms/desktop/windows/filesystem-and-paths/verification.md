# Verification

Check the following:

* path construction does not assume Unix-style separators or shell behavior
* writable data is not stored in protected install locations by default
* file locking, rename, or delete contention is handled predictably
* Windows-specific path and permission assumptions are explicit
* support and debugging can recover the actual file location involved in failures
