# Normative Rules

* Windows desktop applications must not assume Unix-style path behavior where
  path separators, drive letters, or shell quoting affect correctness.
* Code that reads or writes local files should use explicit path construction and
  not depend on development-machine working directories or install-location luck.
* Writable state, caches, and user-owned data should not be placed in protected
  install locations when Windows user-permission or UAC behavior can block them.
* File access behavior must account for Windows-specific realities such as locked
  files, rename or delete contention, and user-visible path differences across
  environments.
* Filesystem assumptions should remain diagnosable enough that Windows-only
  failures can be reproduced without guessing at hidden path or permission state.
