# Normative Rules

* A bug fix should target the proven defect path before expanding into unrelated cleanup.
* Fix scope should remain proportional to the defect unless broader change is justified explicitly.
* Temporary workaround logic must not be disguised as a stable fix.
* Regression prevention should be addressed even when the code change itself is small.
* If a minimal fix is impossible because the structure is unsound, the workflow must escalate rather than pretend the change is low-risk.
