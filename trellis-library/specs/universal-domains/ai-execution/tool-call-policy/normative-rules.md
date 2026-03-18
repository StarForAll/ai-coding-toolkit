# Normative Rules

* Tool calls must be chosen based on evidence needs and execution safety, not convenience alone.
* Write actions with side effects must not be parallelized when state conflicts are possible.
* High-risk or destructive actions must be gated by explicit policy or human approval.
* Tool outputs used as evidence must be observed directly rather than inferred.
* When a required tool is unavailable, the workflow must report an evidence gap instead of fabricating a result.
