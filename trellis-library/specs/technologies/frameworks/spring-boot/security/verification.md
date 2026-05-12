# Verification

Check the following:

* authentication, authorization, and business-logic boundaries are clear
* hidden framework defaults are not carrying unreviewed security decisions
* access decisions and failure behavior are predictable
* controller or service checks do not silently contradict framework security
* new endpoints inherit protection expectations consistently
* request rendering or output paths do not trust raw client input by default
* privileged or sensitive operations produce auditable signals without leaking secrets
* browser-facing mutation flows have explicit request-forgery protection where applicable
* user-facing responses mask or redact sensitive personal data where full disclosure is unnecessary
* HTML or browser-consumed output uses context-appropriate escaping for untrusted content
* cost-bearing or sensitive platform actions have explicit replay and abuse controls
* UGC paths include moderation or anti-spam expectations where publication risk matters
