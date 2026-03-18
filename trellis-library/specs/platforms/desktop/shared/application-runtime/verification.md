# Verification

Check the following:

* launch, ready, background, and shutdown states are reflected where they affect behavior
* filesystem, permissions, and local-resource assumptions are explicit
* missing or unavailable local dependencies degrade predictably
* desktop-owned local state has clear storage and recovery expectations
* framework abstractions are not hiding cross-platform desktop runtime constraints
