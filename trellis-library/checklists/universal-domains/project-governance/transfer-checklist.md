# Transfer Checklist

* the agreed handover trigger for this delivery event is confirmed and recorded
* `assessment.md` records the chosen `delivery_control_track` and the delivery event matches that track
* this delivery event is labeled as either retained-control delivery or final control transfer
* the delivery contact, acknowledgment path, and artifact index for this event are recorded
* if this event includes source transfer, the repository or archive identity and commit or checksum are recorded
* if this event includes source transfer, build and deployment materials are included and verified from scratch
* if this event includes credential or secret transfer, those items are transferred through a secure channel and receipt is confirmed
* if this event includes infrastructure transfer, ownership boundaries, deployment steps, and rollback or runbook materials are included
* if the developer retains control after this event, the retained responsibilities, support window, environment access scope, and escalation path are documented
* if the delivery path uses `trial_authorization`, the disclosed `trial_authorization_terms` are attached or referenced
* if the delivery path uses `trial_authorization`, expired-trial behavior has been checked to preserve data and allow read or export access
* client-facing documentation matches what was actually handed over in this delivery event
* known limitations, remaining responsibilities, and post-delivery support terms are documented
* client acknowledgment or equivalent recorded handover evidence exists before the event is marked complete
