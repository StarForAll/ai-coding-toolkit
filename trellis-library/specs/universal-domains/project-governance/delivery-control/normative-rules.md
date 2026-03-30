# Normative Rules

* External projects must record `delivery_control_track` in `assessment.md` as `hosted_deployment`, `trial_authorization`, or `undecided` before implementation planning continues.
* External projects must keep a human-readable statement of the chosen track, payment trigger, and control-handover timing aligned with the canonical assessment fields.
* `hosted_deployment` must be treated as the default track unless a disclosed `trial_authorization` arrangement is explicitly agreed.
* `authorization-management` rules must be imported and applied only when `delivery_control_track` is `trial_authorization`.
* Planning artifacts must separate feature-delivery work from payment-gated handover work, and handover tasks must not become ready before their payment or approval condition is met.
* Final transfer of source code, secrets, admin credentials, deployment control, or unrestricted authorization must not occur before the agreed handover trigger is satisfied.
* Delivery records must distinguish retained-control delivery from final control transfer, including what the developer still operates and what the client has already received.
* Delivery control mechanisms must not rely on undisclosed backdoors, hidden kill switches, obfuscated pseudo-source, or destructive expiration behavior.
* Delivery-track changes after project start must follow change-management rules and must update assessment, planning, and delivery records together.
