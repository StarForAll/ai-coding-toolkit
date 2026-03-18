# Normative Rules

* Linux desktop applications must not assume a single runtime environment where
  display stack, session variables, and writable-user paths behave identically
  across all machines.
* Behavior that depends on environment variables or session context should keep
  those assumptions explicit rather than burying them in startup defaults or
  developer-shell state.
* Application-owned local state should respect Linux user-environment
  conventions such as XDG-style writable locations instead of relying on
  arbitrary working-directory behavior.
* Missing or incompatible runtime conditions such as absent display variables,
  unavailable desktop session capabilities, or restricted writable locations
  should degrade predictably.
* Linux-only failures should remain diagnosable enough that support and testing
  can recover the relevant environment state instead of guessing at hidden
  process context.
