# Input Validation Checklist

* Every externally supplied field has an explicit validation boundary.
* Validation happens before the value crosses a trust boundary.
* Reject behavior is explicit instead of silently tolerated.
* Error signaling does not leak unsafe internal detail.
* Validation gaps and deferred hardening work remain visible.
