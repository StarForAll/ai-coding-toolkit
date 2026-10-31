# Session Isolation Baseline

## Scope

Read-only inspection of this repository's existing Trellis task/session mechanism. This is a design reference only; the independent wf framework must not depend on Trellis runtime code or require changes to Trellis assets.

## Findings

- `.trellis/scripts/common/active_task.py:1-7` describes the active task as a session-scoped pointer stored below `.trellis/.runtime/sessions/` and requires a stable session key.
- `.trellis/scripts/common/active_task.py:514-577` resolves a key from explicit context, platform event fields, verified environment values, or shell tickets. It returns no key when none is available.
- `.trellis/scripts/common/active_task.py:676-700` resolves only the current session's file. It does not infer ownership from a sole project-wide pointer unless a caller explicitly enables a compatibility fallback.
- `.trellis/scripts/common/active_task.py:754-780` writes the task path to the current session's runtime file; it returns failure when session identity is unavailable.
- `.trellis/scripts/task.py:238-258` has a degraded path that advances task status without persisting a session pointer when identity is unavailable. This independent wf design must not copy that behavior where it would make session isolation ambiguous.
- The runtime pointer is a locator, not a durable task-state store. Task status and workflow/task artifacts remain in project records; the independent wf design must preserve that distinction.
- The inspected mechanism does not provide a project-wide single-writer lease. The independent wf design therefore needs its own generic writer-ownership contract if it is to serialize writes across concurrent sessions.

## Design Consequences

- Resolve a stable session identity or require an explicit session token; never silently fall back to a project-global active object.
- Persist per-session binding separately from task/workflow progress.
- Enforce at most one shared-workspace writer through a project-wide ownership record. A new session may inspect and prepare another object while the writer is held, but cannot mutate the project until it acquires ownership.
- Ownership transfer must fence the prior session from subsequent framework-mediated writes. Do not expire or steal a lease by elapsed time alone; unknown owner liveness requires explicit human recovery.
- Because the framework has no real-time tool interception, the design must distinguish script/entry validation from prevention of direct tool writes. Direct writes remain a declared discipline boundary and must be detected at the next workflow check where possible.

## Evidence Limits

This read establishes the current local Trellis mechanism shape only. It does not establish host identity availability across all supported AI CLIs, prove runtime enforcement, or authorize reusing/modifying Trellis code. Host session identity support must be verified during implementation; unsupported hosts need an explicit session-token path or a visible stop condition.
