# Normative Rules

* Browser-visible routes should preserve stable URL meaning for refresh, direct entry, share, and navigation history where those behaviors matter.
* Navigation state must not depend solely on ephemeral client memory when the URL is expected to represent user-visible state.
* URL changes should remain understandable and consistent with the behavior they trigger.
* Routing behavior must account for back, forward, reload, and direct-entry scenarios rather than assuming single-path navigation.
* When route meaning cannot be represented cleanly in the URL, the limitation should be explicit rather than hidden.
