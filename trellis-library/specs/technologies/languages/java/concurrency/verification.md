# Verification

Check the following:

* shared objects and singletons expose explicit thread-safety assumptions
* executor configuration makes queueing, sizing, rejection, and thread naming reviewable
* thread pools do not rely on hidden unbounded defaults where load can exhaust resources
* lock scope, ordering, and ownership are explicit enough to review deadlock and contention risk
* lock release paths stay safe under failure and cannot unlock unowned locks or leak ownership
* thread-local values are cleared when their execution scope ends
* chosen concurrency primitives actually provide the required safety and visibility guarantees
* shared helpers for time, randomness, or formatting remain safe under concurrent use
* virtual-thread adoption, if present, keeps blocking, thread-local, and scheduler assumptions explicit
