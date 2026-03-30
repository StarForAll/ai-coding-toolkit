# Normative Rules

* This concern must be imported only when `delivery_control_track` is `trial_authorization`.
* Trial authorization must define `trial_authorization_terms` in `assessment.md` or a linked contract artifact, including validity, clock source or usage basis, expiration behavior, renewal policy, and permanent-authorization trigger.
* Trial expiration must preserve user data and must allow read access or export of previously created data.
* Trial expiration must not delete data, irreversibly encrypt data, or hide the existence of restrictions from the client.
* Trial authorization should expose current status, remaining entitlement, and upgrade path to the authorized client or operator.
* Permanent authorization transition must preserve data and configuration and must not require reinstallation unless that exception is disclosed in advance.
* If the trial model depends on time or usage counting, the implementation should document how rollback, offline operation, or counter resets are handled.
