# Windows Filesystem Readiness Checklist

* Path handling does not assume Unix-style separators or shell behavior.
* Writable state is not stored in protected install locations by default.
* File locking and rename or delete contention are handled predictably.
* Windows-specific path and permission assumptions are explicit.
* Failure logs or support output can identify the real file location involved.
