# Miniapp Host Runtime Readiness Checklist

* Host-controlled lifecycle states that affect correctness are identified.
* Important state does not rely only on fragile in-memory assumptions.
* Host capability and resource limits are explicit.
* Duplicate, abandoned, or partial replay risks were considered.
* Container restrictions remain visible where they affect behavior.
