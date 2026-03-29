# Normative Rules

* Model choice must match task risk, complexity, and output requirements.
* Fallback behavior must preserve correctness expectations even when capability is downgraded.
* A degraded model path must be reported when it materially changes confidence or output quality.
* Workflows must not silently substitute a weaker model when doing so would invalidate prior assumptions.
* If no acceptable model path exists, the workflow must stop or escalate rather than fabricate confidence.
