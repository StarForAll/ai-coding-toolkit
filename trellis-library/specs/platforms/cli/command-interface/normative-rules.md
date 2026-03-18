# Normative Rules

* CLI commands must keep invocation contracts explicit enough that both humans and
  scripts can determine the required arguments, optional flags, and expected
  behavior.
* Help output should describe the supported command shape and main modes without
  requiring source inspection.
* Exit codes must distinguish success from misuse or failure; invalid invocation
  must not silently report success.
* Output intended for automation should stay stable enough to parse or assert
  against, while error messages remain visible on the appropriate output channel.
* Wrapper commands should preserve the behavioral contract of the underlying
  command rather than hiding failures or mutating exit semantics unexpectedly.
