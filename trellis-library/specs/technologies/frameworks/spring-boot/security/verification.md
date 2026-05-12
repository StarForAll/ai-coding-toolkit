# Verification

Check the following:

* authentication, authorization, and business-logic boundaries are clear
* hidden framework defaults are not carrying unreviewed security decisions
* access decisions and failure behavior are predictable
* controller or service checks do not silently contradict framework security
* new endpoints inherit protection expectations consistently
* request rendering or output paths do not trust raw client input by default
* privileged or sensitive operations produce auditable signals without leaking secrets
