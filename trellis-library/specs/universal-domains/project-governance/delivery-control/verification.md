# Verification

Check the following:

* `assessment.md` records `delivery_control_track` with one of the canonical values `hosted_deployment`, `trial_authorization`, or `undecided`
* `assessment.md` or a linked negotiation record states the human-readable track, payment trigger, and control-handover timing
* `authorization-management` is imported only when `delivery_control_track` is `trial_authorization`
* planning artifacts separate payment-gated handover tasks from ordinary implementation work
* no source code, secrets, admin credentials, deployment control, or permanent authorization were transferred before the documented trigger
* delivery records clearly state whether the event is retained-control delivery or final control transfer
* no undisclosed backdoors, hidden switches, destructive expiration behavior, or obfuscated pseudo-source are part of the delivery approach
* any mid-project delivery-track change is traceable in change records and reflected in planning and delivery artifacts
