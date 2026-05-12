# Normative Rules

* Shared objects, singletons, and utility state accessed across threads must define thread-safety expectations explicitly rather than relying on incidental usage patterns.
* Thread creation and executor policy must remain explicit enough that queueing, sizing, rejection, and naming behavior are reviewable.
* Thread-pool configuration must not rely on convenience factories whose hidden defaults can create unbounded queues or thread growth under load.
* Locking strategy must make scope, ordering, and ownership explicit enough to review deadlock, contention, and lost-update risk.
* Lock acquisition and release paths must be structured so exceptions cannot silently leave ownership unreleased or unlock a lock the thread never acquired.
* Thread-local state must be bounded to the intended execution scope and cleaned up reliably when threads are reused.
* Concurrency primitives should match the correctness problem being solved, rather than using `volatile`, shared mutable collections, or ad hoc synchronization where they do not provide the required safety.
* Time, random, and formatter helpers used across threads must preserve the concurrency guarantees required by the execution model.
* Modern JDK concurrency features such as virtual threads should be adopted only when blocking behavior, thread-local assumptions, and scheduler impact remain explicit rather than hidden behind a mechanical migration.
