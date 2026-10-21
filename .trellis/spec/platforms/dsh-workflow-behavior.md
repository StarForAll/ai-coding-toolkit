# DSH Workflow Behavior

> Project-level DeepSeek Harness (DSH) operating rules for this repository.

---

## Purpose

Define how the main DSH session should behave in this repository's Trellis
setup, and how the local `dsh-trellis` carrier realizes Trellis behavior.
This is about the **current repository**, not about installed target projects.

The carrier lives at `dsh-plugins/dsh-trellis` and is symlinked into the `web`
profile (`~/.dsh/profiles/web/node_modules/dsh-trellis`). Editing `lib/**`
requires a DSH restart before the running session sees it.

---

## Core Rule: DSH Owns Its Dispatch Mode

DSH reads `.trellis/config.yaml` `dsh.dispatch_mode`; it must not read or reuse
`codex.dispatch_mode` (Trellis marks `*-inline` blocks Codex-only and its
carrier selects them only for `platform == "codex"`).

| `dsh.dispatch_mode` | Main-session behavior | Breadcrumb |
| --- | --- | --- |
| `auto` (default) | dispatch `trellis-agent-implement` / `trellis-agent-check` role sub-agents | base `planning` / `in_progress` blocks |
| `inline` | implement and check directly in the main session; do not dispatch role sub-agents; `trellis_wait` is unnecessary; verify with the `trellis-check` skill | `*-inline` block plus the `<dsh-mode>` banner |

Unknown values fall back to `auto`. A missing `*-inline` block also keeps the
base block rather than inventing inline guidance.

This repository pins `inline` to match its standing main-session rule; Codex
pins its own `codex.dispatch_mode: inline` independently.

---

## Normative Meaning of Inline

While `dsh.dispatch_mode: inline`:

- do not dispatch `trellis-agent-implement` / `trellis-agent-check` manually
  or by any other name; the main session does the work
- `trellis-agent-*` skills are child-only and must not be loaded by the main
  session
- verification uses the main-session `trellis-check` skill; spec capture uses
  `trellis-update-spec`
- the close-out path is unchanged: commit in Phase 3.4, then
  `/trellis-finish-work` (archive + journal)

While `auto`:

- dispatch prompts start with `Active task: <task path>`; the plugin pushes the
  role contract and curated context on the child's first step
- the dispatch guard refuses a task-less implement/check dispatch (fail-closed,
  stricter than Codex by design)

---

## Workflow-State Contract

- Blocks are parsed only when the opening tag ends its line. Inline mentions
  inside workflow.md comments must never open a block; this mirrors the Python
  carriers' `\s*\n` constraint.
- Task statuses pass through by value (`completed`, custom statuses included);
  only a missing/unreadable status degrades to `no_task`.
- A session pointer is normalized like `common/active_task.py`
  (`tasks/<slug>`, `./`, absolute paths); a missing or non-directory target is
  `stale`, a readable directory with an unreadable `task.json` is `task_error`.
- Workflow selection follows Trellis precedence: task `workflow` pin →
  `.trellis/.developer` → `config.yaml default_workflow` → global
  `.trellis/workflow.md`.
- Project `prompt_injection.skip_keyword` takes precedence over the plugin's
  `skipKeyword`; boundaries match Trellis's `prompt_has_skip_keyword`.

---

## Verification Notes

When reviewing DSH behavior in this repository, verify:

- `dsh.dispatch_mode` is the only dispatch switch consulted by the plugin
- inline sessions do not dispatch role sub-agents and still run the check skill
- `codex.dispatch_mode` changes do not alter DSH breadcrumbs
- plugin changes are verified with `node --test "test/*.test.js"` in
  `dsh-plugins/dsh-trellis`, plus a real `.trellis/workflow.md` parse
- a DSH restart is called out whenever `lib/**` changed during the session

---

**Language**: English
