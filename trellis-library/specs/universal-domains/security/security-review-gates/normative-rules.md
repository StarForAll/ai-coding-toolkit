# Normative Rules

* Changes affecting auth, secrets, trust boundaries, or sensitive data paths must be evaluated for elevated security review.
* Security-sensitive changes must not be treated as routine low-risk edits by default.
* Security review gates must be explicit enough to trigger before release, not after incident discovery.
* When security review cannot be completed, the gap must be reported rather than hidden behind ordinary verification success.
* Reusable workflows must preserve a path for escalation when security uncertainty remains.
