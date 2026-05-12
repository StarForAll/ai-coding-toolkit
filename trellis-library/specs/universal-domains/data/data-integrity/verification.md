# Verification

Check the following:

* critical invariants are explicitly identified
* invalid states are prevented or surfaced rather than silently tolerated
* retry and replay behavior has integrity safeguards where needed
* concurrency and partial-failure risks are considered where relevant
* residual integrity exposure is documented when full enforcement is not practical
* concurrent update control strategy is explicit for race-prone operations
* lock or replay defenses have bounded scope and clear release behavior
