# DSH Workflow Behavior

> Project-level DeepSeek Harness (DSH) operating rules for this repository.

---

## Purpose

Define how the main DSH session should behave in this repository's Trellis
setup, and how the local `dsh-trellis` carrier realizes Trellis behavior.
This is about the **current repository**, not about installed target projects.

The carrier lives at `dsh-plugins/dsh-trellis`. The `web` profile currently
installs it as an ssh git dependency snapshot
(`~/.dsh/profiles/web/node_modules/dsh-trellis`), not a symlink. Editing
`lib/**` requires reinstalling/updating that dependency and restarting DSH
before the running session sees it; a `link:` install is a local-development
alternative, not the current profile shape.

---

## Upstream Trellis Is Read-Only

The official Trellis source checkout (for example `~/projects/other/Trellis`) is
a **read-only reference** in this environment. There is no permission to modify
it, and it must not become a repair target.

- Design, fix, and improve Trellis plugins/workflows only in this repository's
  assets (`dsh-plugins/`, `.trellis/spec/`, docs, workflow sources). Do not
  propose or apply patches to the upstream checkout.
- An upstream behavior difference is an **observation**, not a defect to fix
  here. Do not put it in an issue list, execution plan, or acceptance criteria;
  record it as a boundary/limitation and, only when needed, design a local
  workaround inside this repository's own surfaces.
- Concretely: the Codex-in-DSH identity precedence and the upstream DSH
  workflow/`DSH.md` staleness (`run_in_background`, "foreground" wording) are
  upstream observations. They are intentionally ignored as issues in this
  repository; do not reopen them as defects or propose upstream patches.

---

## Core Rule: DSH Owns Its Dispatch Mode

DSH reads `.trellis/config.yaml` `dsh.dispatch_mode`; it must not read or reuse
`codex.dispatch_mode` (Trellis marks `*-inline` blocks Codex-only and its
carrier selects them only for `platform == "codex"`).

| `dsh.dispatch_mode` | Main-session behavior | Breadcrumb |
| --- | --- | --- |
| `inline` (default when the key is absent) | implement and check directly in the main session; do not dispatch role sub-agents; `trellis_wait` is unnecessary; verify with the `trellis-check` skill | `*-inline` block when defined, plus the `<dsh-mode>` banner on every status |
| `auto` (explicit `auto` / legacy `sub-agent`) | dispatch `trellis-agent-implement` / `trellis-agent-check` role sub-agents | base `planning` / `in_progress` blocks |

Unknown values fall back to `inline` (fail-safe: a typo must not silently enable
dispatch). A missing `*-inline` block keeps the base block as phase wording; the
`<dsh-mode>` banner is still emitted, because the banner — not the block choice —
declares the mode. The banner also overrides Trellis phase detail that still
says "Spawn the implement sub-agent" (Trellis 0.7.0-beta.4 has no DSH-inline
variant).

This repository pins `inline` to match its standing main-session rule; Codex
pins its own `codex.dispatch_mode: inline` independently.

## Project Config Is Read-Only

The plugin reads `.trellis/config.yaml` and never writes it. A missing `dsh`
section or `dispatch_mode` key means `inline`; there is no first-session
migration, no appended key, and no backup/atomic-write path to maintain.

Consequences:

- a tracked `config.yaml` is never dirtied by a session and `trellis update`
  never sees a plugin-made edit;
- `trellis update -f` cannot remove a plugin-written section because there is
  none to remove;
- an explicit `auto` / `sub-agent` remains the only way to enable dispatch;
- a read-only project behaves identically to a writable one.

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
- the `<dsh-mode>` banner overrides any phase detail or skill text that still
  instructs the main session to spawn implement/check
- `task.py start` still needs `--allow-empty-context`: Trellis treats the
  presence of `.dsh` as sub-agent-capable (`_SUBAGENT_CONFIG_DIRS`) regardless of
  `dsh.dispatch_mode`, and inline mode does not curate jsonl

While `auto`:

- dispatch prompts start with `Active task: <task path>`; the plugin pushes the
  role contract and curated context on the child's first step
- the dispatch guard refuses a task-less implement/check dispatch (fail-closed,
  stricter than Codex by design)

### Mid-session mode switches (0.1.7, documented boundary)

Old `<dsh-mode>` banners in session history are not rewritten when
`dsh.dispatch_mode` changes; a model may keep quoting the stale banner (e.g.
refusing a legitimate dispatch after the switch to `auto`, or quietly
implementing inline instead of dispatching after that same switch). Guidance recorded in the plugin
README (0.1.7): avoid switching the mode mid-session; if a switch is
necessary, prefer a fresh session, or explicitly tell the model the old banner
is obsolete and the current config wins. A new breadcrumb for the new mode is
injected on the next turn (digest change), but the old banner stays in
history. Related caveat: `dsh.inline_allow_dispatch: true` changes only the
dispatch-guard decision, not the banner text — a model may still refuse to
dispatch while the inline banner is present. This is documentation guidance,
not new runtime behaviour.

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
- A stale pointer keeps its own diagnostic: when `workflow.md` has no
  `[workflow-state:stale]` block, the breadcrumb uses `STALE_BREADCRUMB`
  (names the pointer as the repair target) instead of the generic
  "no matching [workflow-state] block" line, and the one-time bootstrap is
  appended for `stale` exactly as for `no_task`. `stale` is never rewritten to
  `no_task`. Codex keeps the same state as `stale_session` and emits its generic
  fallback line without a bootstrap; the explicit repair text and the bootstrap
  are DSH enhancements, not parity with Codex.
- Workflow selection follows Trellis precedence: task `workflow` pin →
  `.trellis/.developer` → `config.yaml default_workflow` → global
  `.trellis/workflow.md`.
- Project `prompt_injection.skip_keyword` takes precedence over the plugin's
  `skipKeyword`; boundaries match Trellis's `prompt_has_skip_keyword`.
- The skip keyword is decided **once per turn**, not per step: `agent/pre-step`
  hands each step only the batch it claims from the inbox, so the prompt that
  carried the keyword is not visible at step 2. The composer remembers the
  skipped `turn` per agent and stays silent for its remaining steps; the next
  turn decides again. Skipping only affects message composition; the plugin
  never writes project configuration. A host that reports no `turn` degrades to
  step scope and must not be described as turn-scoped.

---

## Path-Scoped Spec Contract

- Tools pass a raw `file_path`. DSH resolves a relative path against the
  agent's current working directory, which may be a subdirectory of the
  Trellis project root. The plugin therefore resolves **both** interpretations
  (`normalizeRepoRelativeFrom(root, cwd, filePath)` first,
  `normalizeRepoRelative(root, filePath)` second) and unions the matches,
  deduplicating by spec path and keeping the most specific glob.
- The primary `editedRel` is the cwd-relative candidate when it matches; the
  `<spec-context file="…">` attribute must name a repo-relative path, never an
  absolute one.
- Over-injection is the deliberate fail-safe: a file path written
  repo-relative from a subdirectory (`src/x.ts` while cwd is `src/`) may match
  both interpretations. Missing a governing spec is worse than teaching it
  twice.
- Deny-once, ticket, refresh-window, persistence, and compaction reset are
  unchanged. The Codex hook has the same root-relative limitation; 0.1.6 fixes
  it on the DSH side only (upstream not changed).

### Command routing surface (0.1.7, documented boundary)

`/trellis-*` plugin commands execute only through the interactive command
input surface (Web/TUI etc.). A headless plain-text prompt containing
`/trellis-status` is an ordinary task for the model, not a command execution —
this holds even with the plugin installed, and adding `--json` only changes
the output format, not the input. Its answer is model-improvised and can be
factually wrong (the verification round observed a headless session claiming
the plugin was not installed while it was actively injecting). In headless
sessions use the shell equivalents (`task.py current --source`,
`get_context.py`, `task.py list`; `python3` or on Windows `py -3`/available
Python). Recorded in the plugin README (0.1.7) and
`docs/validation-0.1.7-local.md` as a host limitation; no runtime change.

---

## Verification Notes

When reviewing DSH behavior in this repository, verify:

- `dsh.dispatch_mode` is the only dispatch switch consulted by the plugin;
  missing/unknown values are `inline`, and a session never writes
  `.trellis/config.yaml`
- inline sessions do not dispatch role sub-agents (the banner overrides phase
  detail) and still run the check skill; `task.py start` needs
  `--allow-empty-context` because `.dsh` triggers the jsonl gate
- `codex.dispatch_mode` changes do not alter DSH breadcrumbs
- plugin changes are verified with `node --test "test/*.test.js"` in
  `dsh-plugins/dsh-trellis`, plus a real `.trellis/workflow.md` parse
- a role is selected only by a prompt declaration (first-line prefix, `Role:`
  line, or `You are the <role> sub-agent/role` sentence) or a strict
  `description` prefix; path/prose mentions
  (`.dsh/skills/trellis-agent-<role>/SKILL.md`, `Run the trellis-check skill`)
  stay generic: no guard decision and no role push
- a relative `edit`/`write` path from a subdirectory session still matches
  specs written against repo-relative paths (`src/**/*.ts`)
- a DSH restart is called out whenever `lib/**` changed during the session
- when comparing a hook against Codex, clear inherited DSH identity variables
  (`DSH_TRELLIS_CONTEXT_ID`, `DSH_SHELL`, `DSH_SESSION_ID`) before invoking
  `.codex/hooks/*.py`. `common/active_task.py#resolve_context_key` prefers those
  env-derived keys (the DSH override first, then the `DSH_SHELL=1` +
  `DSH_SESSION_ID` pair, then the generic `TRELLIS_CONTEXT_ID`) over the payload
  `session_id`. A temporary project without the matching pointer therefore
  yields a fabricated `no_task` + bootstrap baseline. `_detect_platform` does
  not recognise DSH, and the payload `session_id` is not turned into a
  `dsh_<id>` key.
- a version change updates `package.json`, `README.md`, `LOCAL_CHANGES.md`, and
  `docs/validation-<version>-local.md` together
- upstream Trellis findings (identity precedence, template/DSH.md staleness) are
  recorded as read-only observations only; never as actionable issues or
  upstream patches

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

---

## 0.1.1 Behavior Notes

- **Flow-style config** — `parseSection` accepts `section: {key: value}` for
  `dsh`, `spec_injection`, `prompt_injection`, and `context_injection`; an
  explicit `dsh: {dispatch_mode: inline}` therefore selects inline and remains
  subject to the inline dispatch guard.
- **Broken workflow visibility** — when a Trellis root has a missing,
  unreadable, or zero-state-block `workflow.md`, the plugin emits the generic
  fallback breadcrumb plus the normal `no_task` bootstrap. A plain Git
  repository without `.trellis` stays silent.
- **Command references** — injected state bodies normalize
  `/trellis:<name>` to the DSH skill/command surface before the digest is
  computed.
- **Research push** — research children receive the `.trellis/spec` directory
  overview plus `get_context.py --mode packages` and search tips; task
  artifacts are not inlined for that role. An empty `research.jsonl` is not
  reported as missing context.
- **Role contract push** — pull-only context-loading sections are removed from
  the pushed copy only; the on-disk `.dsh/skills/trellis-agent-*` contracts
  remain the pull path.
- **Version check** — GitHub Atom/npm timeouts are reported as partial results
  with a retry hint; the raw `This operation was aborted` text must not reach
  the settings page.

---

## 0.1.2–0.1.3 Behavior Notes

### Design Decision: role identity has two sources

**Context**: Role detection used to read only the dispatch prompt. DSH records
the `subagent` / `subagent_fork` `description` argument as the child's durable
`subagent/descriptor` label, so a role named only there was silently treated as
a generic child: no push, and no inline guard (the same parser feeds both).

**Decision** (0.1.6): role = a *declared* role in the dispatch prompt, then the
dispatch `description` (guard) / child descriptor `label` (push). Prompt wins
when both carry one. `Active task:` still comes from the prompt only.

**Prompt declaration rule** (0.1.6): the prompt selects a role only through one
of these shapes — a first-line role prefix (`trellis-agent-implement`,
`trellis-implement: …`, `trellis-implement (round 3)`), a dedicated line
(`Role: trellis-agent-implement` / `Agent: trellis-check`), or the Trellis
dispatch sentence (`You are the trellis-implement sub-agent/role`). A path
mention (`.dsh/skills/trellis-agent-<role>/SKILL.md`) or ordinary prose
(`Run the trellis-check skill …`) is **not** a declaration: no push and no guard
decision. This closes the 0.1.5 false positive where a generic child that only
read the role skill file received an implement push, and an unbound generic
dispatch could be refused. Intended dispatches must include the declaration
line; the workflow's own phase text already says to tell the child it is the
role sub-agent, and `description` remains the fallback.

**Role-label rule**: the label is display text, not an instruction channel. It
selects a role when it *starts* with `trellis-agent-<role>` / `trellis-<role>`
(case-insensitive; leading quotes/brackets ignored) and is followed by the end
of the label or an annotation separator: whitespace plus `:`/`：`, `(`/`（`,
`[`/`【`, `-`, `–`, `—` (e.g. `trellis-agent-implement (audit round 3)`).
A label that merely mentions the name — `研究 trellis-agent-implement 插件的
README`, `about trellis-agent-check plugin docs` — stays generic: no guard
decision and no role-contract push. So does a role name followed by plain words
(`trellis-agent-check plugin docs`). A bare substring match regressed 0.1.1
(topical descriptions were refused and generic children received a wrong role
contract); whole-label equality (0.1.2) dropped annotated role labels; the
0.1.1–0.1.5 prompt substring scan regressed the reverse case in 0.1.6 (path and
prose mentions selected a role). The declarative prompt rule above is the
current contract.

**Contracts**:

- guard — `parseDispatchRequest(prompt, description)`; `exec.arguments` carries
  both for `subagent` and `subagent_fork`.
- push — `parseDispatchPrompt(messages, label)`; the label is read through
  `sessionProjections` (`dsh-trellis.subagent-identity`, host-only state
  `{ inherited, label? }`), never via `eventAt` / `snapshotEvents` /
  `ownEvents`. An inherited descriptor (forked child) is ignored via
  `event.seq < inherited`.
- degradation — a profile without the projection service yields `labelOf() =>
  null`; detection falls back to the prompt with no error.

**Tests**: `test/subagent-identity.test.js`,
`test/native-subagent-push.test.js` (real AgentLoop + Session + descriptor),
`test/dispatch-guard.test.js` (description-only inline denial),
`test/role-contract.test.js` (role-prefix, declaration, topical labels, and
path/prose false positives).

### Push contract: one authoritative context statement

- Task source order is dispatch prompt `Active task:` first, the parent
  session pointer second; when neither resolves, nothing is pushed (Codex's
  `SubagentStart` hook also returns without a task directory). Research keeps
  its post-dispatch notice about where findings must be persisted.
- The preamble is the only place that says "the task context was prepared"; the
  `## Task Context` replacement section must not repeat it.
- When the role skill body is inlined, the push must say so and forbid a second
  load of `.dsh/skills/trellis-agent-<role>/SKILL.md`; when the skill is
  missing, the fallback may only ask for that one load.
- `subagentContextMessage` byte budget and task materialization are unchanged.

### Dispatch guard is a prompt-level gate

`inline` refuses `trellis-agent-implement` / `trellis-agent-check` dispatch,
but the project config is writable by the same agent that receives the denial.
The denial therefore names leaving inline as the **user's** decision and tells
the model not to edit `.trellis/config.yaml`; README and code must not claim the
guard enforces the contract or is a security boundary.

### README scope

`dsh-plugins/dsh-trellis/README.md` describes this plugin only. Upstream fork
lineage, release history, and npm-install instructions for the upstream package
must not be reintroduced; version notes stay in `docs/validation-*` and
`LOCAL_CHANGES.md`.
