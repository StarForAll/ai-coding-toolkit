# Normative Rules

* Type hints should clarify important interfaces and data flow rather than serving as decorative noise.
* Public or cross-module interfaces should use annotations that help readers and tools detect misuse early.
* Type annotations must not imply runtime guarantees that the code does not actually enforce.
* Broad escape hatches such as unbounded dynamic typing should remain visible and deliberate where used.
* Typing style should stay consistent enough that missing or misleading annotations are easy to spot.
