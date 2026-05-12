# Verification

Check the following:

* service classes coordinate use cases without turning into unbounded catch-all helpers
* orchestration is distinguishable from transport handling, persistence detail, and framework configuration
* transaction ownership is explicit for multi-step consistency
* complex branching or side effects are decomposed enough to review for correctness
* proxy-driven framework behavior is not relied on through self-invocation or bypassed call paths
* Spring-managed async dispatch uses an explicit executor policy where concurrency behavior matters
* transaction, context, and proxy assumptions are not silently carried across async dispatch boundaries
* asynchronous or integration side effects have explicit ordering, retry, and failure expectations
