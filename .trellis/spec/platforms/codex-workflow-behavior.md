# Codex Workflow Behavior

> Project-level Codex operating rules for this repository.

---

## Purpose

Define how Codex should behave when working inside this repository's Trellis
setup, especially where Codex runtime behavior differs from other platforms.

This document is about the **current repository's own operating rules**, not
about workflow product behavior in installed target projects.

---

## Core Rule: Inline Means No Manual Subagents

When `.trellis/config.yaml` keeps `codex.dispatch_mode` at `inline`, the main
Codex session must stay inline.

Normative meaning:

- do not manually spawn subagents for implementation, checking, research, or
  convenience parallelization
- do not bypass inline mode by using platform-level agent spawning as an
  ad hoc substitute for Trellis dispatch
- if work genuinely requires subagent orchestration, change the operating path
  explicitly first rather than silently mixing models inside an inline session

This rule applies even to read-only analysis tasks. “It is only research” is
not an exception.

---

## Why This Rule Exists

In this repository, `inline` is not just a performance preference.

It is the coordination model documented in `.trellis/config.yaml`: Codex
subagents with isolated turns do not inherit the main session's task context
reliably enough to be the default path here.

Because of that:

- the session should follow one consistent execution model
- the user should not have to guess whether a Codex session is still operating
  under inline assumptions
- repo-local process rules should be discoverable in spec form rather than
  remembered as oral convention

---

## Allowed / Not Allowed

### Allowed

- reading files inline
- running shell commands inline
- doing multi-step analysis in the main Codex session
- using normal non-agent tools in the current session

### Codex-Specific Close-Out Helper

In this repository, `record-session-helper.py` is a Codex-specific close-out
helper, not a cross-platform default.

Normative meaning:

- Codex-focused fallback / recovery guidance may reference
  `.trellis/scripts/workflow/record-session-helper.py`
- shared non-Codex `finish-work` entrypoints should continue to describe the
  default `add_session.py` path unless their own platform contract explicitly
  adopts the helper
- do not rewrite Claude / OpenCode / Qoder / Kiro `finish-work` entrypoints to
  use the Codex-specific helper merely for cross-platform wording symmetry

Why this matters:

- `record-session-helper.py` was added here to support Codex-specific recovery
  and operator ergonomics
- other platform surfaces in this repository are not required to treat that
  helper as their default session-recording path
- cross-platform wording should reflect actual platform ownership rather than
  collapsing everything into the Codex path

### Not Allowed While Inline

- manually calling platform-level agent spawning to parallelize analysis
- manually dispatching work to Codex subagents while still claiming inline mode
- mixing inline execution with ad hoc subagent execution in one continuous Codex
  path unless the operating mode has been intentionally changed first

---

## Escalation Path

If inline execution is no longer sufficient:

1. stop and recognize that the current constraint is real
2. decide whether the project should explicitly use a non-inline Codex path for
   this work
3. update the relevant configuration or workflow contract first
4. only then use subagent-based execution

Do not treat manual subagent spawning as an invisible local optimization.

---

## Verification Notes

When reviewing Codex behavior in this repository, verify:

- the session honored `codex.dispatch_mode: inline` as an execution constraint
- no manual subagent spawning was used inside an inline Codex path
- any deviation was made explicit as a rule/config change rather than an
  unrecorded exception

---

**Language**: English
