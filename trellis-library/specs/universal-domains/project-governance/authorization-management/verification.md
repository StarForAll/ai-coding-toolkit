# Verification

Check the following:

* `authorization-management` is used only when `delivery_control_track` is `trial_authorization`
* `trial_authorization_terms` are recorded with validity, time or usage basis, expiration behavior, renewal policy, and permanent-authorization trigger
* expired-trial behavior preserves data and permits read access or export of existing data
* restricted behavior and upgrade conditions are disclosed in client-facing records
* authorization status and upgrade path are visible to authorized operators
* permanent authorization transition preserves existing data and configuration
* time-based or usage-based enforcement edge cases are documented when relevant
