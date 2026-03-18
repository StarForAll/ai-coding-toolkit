# Normative Rules

* Browser-side behavior must account for client execution constraints such as asynchronous loading, partial capability support, and user-controlled runtime conditions.
* Runtime assumptions about storage, network availability, document lifecycle, and client state must remain explicit where they affect correctness.
* Browser-only behavior must not be treated as universally reliable across all environments without qualification.
* Client runtime failures should degrade predictably rather than collapsing silently into undefined behavior.
* Platform-specific browser constraints should remain visible instead of being hidden behind framework abstraction confidence.
