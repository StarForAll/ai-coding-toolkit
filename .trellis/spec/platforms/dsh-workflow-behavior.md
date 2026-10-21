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
| `inline` (bootstrapped default) | implement and check directly in the main session; do not dispatch role sub-agents; `trellis_wait` is unnecessary; verify with the `trellis-check` skill | `*-inline` block when defined, plus the `<dsh-mode>` banner on every status |
| `auto` (library fallback / explicit opt-out) | dispatch `trellis-agent-implement` / `trellis-agent-check` role sub-agents | base `planning` / `in_progress` blocks |

Unknown values fall back to `auto`. A missing `*-inline` block keeps the base
block as phase wording; the `<dsh-mode>` banner is still emitted, because the
banner — not the block choice — declares the mode.

This repository pins `inline` to match its standing main-session rule; Codex
pins its own `codex.dispatch_mode: inline` independently.

## Project Bootstrap: `dsh.dispatch_mode`

Installing and enabling the plugin bootstraps the project instead of asking the
user to add the key by hand. Before the first state resolution of a project, the
plugin ensures `.trellis/config.yaml` contains `dsh.dispatch_mode: inline`.

Rules:

- add the key only when it is absent; an explicit `auto` (or any value) is
  authoritative and is never overwritten;
- preserve comments, ordering, and line endings; never rewrite the file when the
  key is already present;
- never create a missing `.trellis/config.yaml` — the plugin supplements a
  Trellis project, it does not invent one;
- write atomically (temp + rename) under a directory lock, and re-read the
  file while holding the lock before merging, so two sessions starting together
  cannot append the section twice or overwrite each other's edits;
- a read-only project or a failed write degrades to the library fallback
  `auto` for that run and logs one warning.

Because the bootstrap runs before state resolution, the first turn already sees
`inline`; the read cache is invalidated as part of the write.

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

---

## Versioning Policy for the Local `dsh-trellis` Carrier

The carrier's version numbering restarted at **0.1.0** on 2026-10-21. Pre-reset
versions (upstream `0.1.12` through the local `0.3.10`) remain only as history
in `LOCAL_CHANGES.md` and the `validation-0.3.*` records.

- Normal fixes, features, and documentation changes bump the **patch**:
  `0.1.0` → `0.1.1` → `0.1.2`.
- A **minor** or **major** bump is reserved for significant changes: a breaking
  runtime or configuration contract, a manifest/settings-surface break, or a
  rewrite large enough that projects must re-verify integration.
- Do not jump to `0.2.0` or higher for ordinary work; "it is a feature" is not a
  reason to change the major/minor component.
- Keep `package.json`, `README.md`, `LOCAL_CHANGES.md`, and the release record
  (`docs/validation-<version>-local.md`) in agreement. The client bundle's
  `PLUGIN_VERSION` is stamped from `package.json` at build time (`pnpm run
  build:client`), so rebuild it as part of a version change.
