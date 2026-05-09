# Deep Analysis: workflow-audit vs Current Trellis Mechanism

## Why This Document Lives Here

This task is a **task-context backfill**, not an implementation task.

The goal is to preserve the current conversation's deeper analysis in the
active Trellis task so a later implementation task can reuse it directly.

For this repository, the right place for that analysis is the task-local
`info.md`, not repo-global docs or immediate edits to `workflow-audit`.

---

## Current Snapshot

- Current repo Trellis version file: `.trellis/.version = 0.5.9`
- Current executable Trellis version: `trellis -v = 0.5.9`
- Current workflow compatibility anchor:
  `docs/workflows/新项目开发工作流/commands/workflow_assets.py`
  `COMPATIBLE_TRELLIS_VERSION = "0.5.9"`

Conclusion:

- the current `workflow-audit` version gate **passes today**
- the current problem is therefore **not** "same-version gate missing" or
  "anchor mismatch"
- the current problem is keeping `workflow-audit` aligned with the **actual
  Trellis operating model now used in this repository**

That means the follow-up should be framed as:

- Trellis mechanism alignment
- audit boundary clarification
- carrier wording and evidence-model correction

not as:

- version-anchor remediation
- merging `workflow-capability-audit` logic back into `workflow-audit`

---

## Trellis Mechanism Map In This Repository

## 1. `.trellis/` is the runtime truth layer

The current repository uses `.trellis/` as the authoritative runtime and
maintenance layer.

Key roles:

- `.trellis/workflow.md`
  - workflow source of truth
  - owns `[workflow-state:*]` prompt blocks
- `.trellis/config.yaml`
  - project-level Trellis configuration
  - includes task hook configuration entrypoint
  - carries the Codex `dispatch_mode` contract
- `.trellis/tasks/`
  - task-local PRD, `info.md`, JSONL context, research
- `.trellis/workspace/`
  - developer journal and cross-session memory
- `.trellis/scripts/`
  - runtime helpers used by hooks, agents, and task tooling
- `.trellis/.runtime/sessions/`
  - session-scoped active-task state
- `.trellis/.template-hashes.json`
  - Trellis-managed template hash tracking

Important implication:

- active task is no longer modeled as a repo-global `.trellis/.current-task`
- any maintainer-side skill or audit logic that drifts back toward that old
  assumption will misread current Trellis behavior

## 2. Hidden platform directories are carrier layers, not equal authorities

The hidden directories in repo root are not peers of `.trellis/` in authority.
They are platform-specific carrier/integration layers attached to the same
runtime truth.

### Claude Code

- main files:
  - `.claude/settings.json`
  - `.claude/hooks/session-start.py`
  - `.claude/hooks/inject-workflow-state.py`
  - `.claude/hooks/inject-subagent-context.py`
  - `.claude/skills/`
  - `.claude/agents/`
- model:
  - hook-push for session-start
  - hook-push for per-turn workflow-state
  - hook-push for sub-agent task/spec context

### Codex

- main files:
  - `.codex/config.toml`
  - `.codex/hooks.json`
  - `.codex/hooks/inject-workflow-state.py`
  - `.codex/agents/`
  - `.agents/skills/`
- model:
  - per-turn breadcrumb hook only
  - main session defaults to inline mode in this repo
  - sub-agents self-load context from task files when explicitly used
  - shared skills live in `.agents/skills/`
  - `.codex/skills/` is a conditional secondary carrier, not today's default

Important Codex nuance:

- even when `.codex/hooks.json` exists, hook execution is still gated by
  user-level feature enablement and hook approval
- `workflow-audit` should therefore reason about **installed carrier shape**
  separately from **runtime activation**

### OpenCode

- main files:
  - `.opencode/plugins/*`
  - `.opencode/lib/trellis-context.js`
  - `.opencode/commands/trellis/`
  - `.opencode/agents/`
- model:
  - plugin-driven context loading
  - command carrier under `.opencode/commands/trellis/`
  - may also observe shared `.agents/skills/`

Important OpenCode nuance:

- `.agents/skills/` is not only a Codex concern
- when workflow product assets write phase skills into `.agents/skills/`,
  OpenCode can perceive them alongside its own command carrier
- this creates a real same-version audit topic: duplicate or confusing
  multi-entry exposure

### Kiro

- current repo has:
  - `.kiro/hooks/inject-subagent-context.py`
  - `.kiro/skills/`
  - `.kiro/agents/`
- this proves Kiro is part of the current repo's Trellis integration surface
- it does **not** mean the current workflow product has adopted Kiro as a
  workflow-managed target-project surface

### Qoder

- current repo has:
  - `.qoder/settings.json`
  - `.qoder/hooks/inject-workflow-state.py`
  - `.qoder/agents/`
  - `.qoder/skills/`
- Qoder currently uses a mixed model:
  - workflow-state hook exists
  - implement/check agents self-load task context
  - there is no dedicated sub-agent context hook like Claude/Kiro

Important implication for `workflow-audit`:

- `.kiro/` and `.qoder/` are valid **repo-local Trellis integration**
  directories
- they are still **out of scope by design** for the current workflow product
  unless `workflow_assets.py` expands the managed surface first

## 3. Current task/context loading is session-scoped and platform-specific

The current repository's task model is not "one repo-wide active task file."

It is:

- one logical active task per session/window
- session identity resolved from platform input, env vars, transcript path, or
  explicit context id
- persisted in `.trellis/.runtime/sessions/`

This affects all audit/task wording:

- task-based audit mode should be described as operating inside current
  session-scoped Trellis runtime
- active task is runtime context, not a workflow-root inference source
- `prd.md` + `info.md` + JSONL files are the current task-local evidence and
  instruction container

## 4. Backup and residual directories are context, not live contract

The repository currently contains historical Trellis snapshots under
`.trellis/.backup-*`.

These should not be treated as:

- current Trellis runtime contract
- workflow-managed target-project evidence
- justification to reintroduce removed legacy assumptions

They are useful for forensic comparison only.

---

## What The Current workflow-audit Already Gets Right

The current `workflow-audit` contract is not starting from zero.
Several important corrections are already present and should be preserved.

## 1. Exact same-version gate

Current `workflow-audit` already requires:

1. read `COMPATIBLE_TRELLIS_VERSION`
2. run `trellis -v`
3. require exact equality

This is correct and should remain unchanged.

## 2. Fixed audit target

Current `workflow-audit` already treats:

- `docs/workflows/新项目开发工作流/`

as the only supported workflow root.

This is also correct and should remain unchanged.

## 3. Supported workflow-managed surface stays limited

Current `workflow-audit` already limits same-version workflow audit coverage to:

- Claude Code
- OpenCode
- Codex

and already excludes:

- `.kiro/`
- `.qoder/`

unless `workflow_assets.py` changes first.

This is correct.

## 4. It already distinguishes workflow target from runtime context

Current `workflow-audit` already says:

- do not infer workflow root from current repo root
- do not infer workflow root from active task
- do not infer workflow root from temporary target-project root

That rule must stay.

## 5. Codex handoff boundary already exists

Current `workflow-audit` already preserves:

- Codex stops at formal embed boundary
- non-Codex executor is required for that step

This still matches the current repo's Codex operating constraints.

Net conclusion:

- the follow-up work should **not** reopen already-solved version-gate or
  fixed-target questions unless new evidence appears
- the follow-up work should focus on **mechanism fidelity and evidence-model
  precision**

---

## Compatibility Risks Still Worth Correcting

## 1. Step 2a mechanism description is still too coarse

Current `workflow-audit` wording already lists a simplified Trellis init
artifact model:

- `.trellis/`
- `.claude/`
- `.opencode/`
- `.agents/skills/`
- `.codex/`

That is directionally correct, but too coarse for current Trellis `0.5.9`.

What it misses:

- session-scoped active task runtime under `.trellis/.runtime/sessions/`
- `.agents/skills/` as both repo-local shared deployment layer and shared
  target-project skill carrier
- Codex hook/config carrier being present-but-runtime-gated
- OpenCode plugin-based context loading and formal command carrier split
- platform differences between hook-push and agent-pull task context models

Repair direction:

- expand `workflow-audit` Step 2a into a real mechanism map
- keep it bounded to what same-version audit actually needs

Likely files:

- `.trellis/spec/skills/workflow-audit.md`
- `.agents/skills/workflow-audit/SKILL.md`
- `.claude/skills/workflow-audit/SKILL.md`

## 2. The three-layer evidence model should be made more explicit

Current task analysis confirms that workflow maintenance in this repo should
always separate three evidence layers:

1. source repo carrier state
2. fresh `/tmp + trellis init` baseline
3. workflow-installed target-project state

Current `workflow-audit` already requires source-layer tags, which is good.
But the deeper three-layer model is important enough to become a more explicit
first-class rule in the maintainer contract.

Why this matters:

- this repository's own hidden directories are customized authoring/runtime
  carriers, not clean baseline fixtures
- a fresh `/tmp` project is the right baseline for "what current Trellis
  really installs"
- workflow-installed target state is the right evidence for "what this
  workflow adds or changes"

Repair direction:

- keep source-layer tags
- additionally make the three-layer comparison model explicit in Step 2a/2c
  wording and report/template language

Likely files:

- `.trellis/spec/skills/workflow-audit.md`
- `.agents/skills/workflow-audit/references/audit-report-template.md`
- `.agents/skills/workflow-audit/references/lightweight-output-template.md`
- matching `.claude/skills/workflow-audit/` copies

## 3. `.agents/skills/` needs dual-role wording

Current repo evidence shows `.agents/skills/` has dual meaning:

- in this repo: shared deployment layer for compatible skill loaders
- in workflow-installed target projects: shared workflow skill carrier,
  especially relevant to Codex and discoverability on OpenCode

If `workflow-audit` describes `.agents/skills/` too narrowly, it risks:

- underexplaining OpenCode duplicate exposure
- overexplaining it as a workflow defect in contexts where it is just the
  repo-local shared deployment layer

Repair direction:

- explicitly describe dual-role semantics
- make OpenCode duplicate exposure a same-version audit topic
- do not treat `.agents/skills/` presence alone as a defect

Likely files:

- `.trellis/spec/skills/workflow-audit.md`
- `.agents/skills/workflow-audit/SKILL.md`
- `.claude/skills/workflow-audit/SKILL.md`
- possibly workflow docs if their current wording still implies one single role

## 4. Codex conditional carriers should stay conditional

Current repo evidence does not support modeling `.codex/skills/` as today's
default baseline output.

Current evidence supports:

- `.agents/skills/` as current shared skill carrier
- `.codex/skills/` as optional secondary carrier
- `.codex/hooks.json` and `.codex/config.toml` as carrier/config surfaces
- runtime hook behavior still gated by user-level Codex settings and approval

Repair direction:

- do not require `.codex/skills/` as a default expected artifact in
  `workflow-audit`
- treat it as conditional/secondary
- keep the workflow's Codex audit logic focused on carrier shape, not
  unconditional runtime activation claims

Likely files:

- `.trellis/spec/skills/workflow-audit.md`
- `.agents/skills/workflow-audit/tests/*`
- matching `.claude/skills/workflow-audit/` copies
- possibly `docs/workflows/新项目开发工作流/commands/codex/README.md`
  if old examples still imply default `.codex/skills/` presence

## 5. Task-based audit wording should stay aligned with session-scoped Trellis

Current `workflow-audit` does not appear to contain the older
`.current-task` mistake, but the task-based wording should still explicitly
stay aligned with current Trellis runtime shape:

- active task is session-scoped
- task context lives in task-local files
- `prd.md`, `info.md`, and report artifacts are task-local truth surfaces

Repair direction:

- add explicit wording so future edits/tests do not regress into old
  repository-global active-task assumptions

Likely files:

- `.trellis/spec/skills/workflow-audit.md`
- `.agents/skills/workflow-audit/tests/07-child-audit-task.md`
- `.agents/skills/workflow-audit/tests/24-active-task-not-audit-target.md`
- matching `.claude/skills/workflow-audit/` copies

## 6. `workflow_assets.py` must remain the literal managed-surface authority

Current analysis does **not** justify silently widening workflow-managed
surface to match all hidden directories that now exist in this repo.

Therefore:

- do not expand `workflow-audit` support surface just because `.kiro/` or
  `.qoder/` exist locally
- do not change managed-surface assumptions outside `workflow_assets.py`
- if a future compatibility round intentionally widens managed surface, that
  decision must start in `workflow_assets.py`

This is partly already understood in current docs, but it should be preserved
as an explicit guardrail for future work.

---

## Concrete Repair Plan

## Phase A: contract alignment first

Primary goal:

- update `workflow-audit` behavioral contract to describe current Trellis
  mechanism accurately without changing its role boundary

Primary files:

- `.trellis/spec/skills/workflow-audit.md`

Required changes:

- expand Step 2a mechanism map
- strengthen the three-layer evidence model
- clarify `.agents/skills/` dual-role semantics
- clarify Codex conditional carrier wording
- add explicit session-scoped task/runtime wording where useful

## Phase B: executable skill surface sync

Primary files:

- `.agents/skills/workflow-audit/SKILL.md`
- `.claude/skills/workflow-audit/SKILL.md`

Required changes:

- mirror Phase A contract changes
- avoid platform-private semantic drift

Companion files likely needing same-change sync:

- `.agents/skills/workflow-audit/references/*`
- `.agents/skills/workflow-audit/tests/*`
- matching `.claude/skills/workflow-audit/` copies

## Phase C: workflow product docs only if evidence still shows wording drift

Do **not** default to editing workflow product docs in the same change unless
the Phase A/B correction reveals actual wording drift there.

Possible follow-up files if needed:

- `docs/workflows/新项目开发工作流/CLI原生适配边界矩阵.md`
- `docs/workflows/新项目开发工作流/装后隐藏目录与托管边界核对清单.md`
- `docs/workflows/新项目开发工作流/commands/opencode/README.md`
- `docs/workflows/新项目开发工作流/commands/codex/README.md`

Important boundary:

- `workflow_assets.py` should be edited only if the managed-surface contract
  itself changes, not just because wording becomes more precise elsewhere

## Phase D: verification

Minimum verification for the future implementation task:

- `./scripts/validate-skills.sh`
- targeted grep or diff review to ensure `.agents/skills/` and
  `.claude/skills/` stay synchronized
- any workflow-audit scenario-file checks relevant to changed wording

If future implementation touches workflow product docs too, add the relevant
workflow validation commands from that task's scope.

---

## Task-Shaping Recommendation

Current recommendation:

- use **one implementation task** for `workflow-audit` contract alignment
  itself:
  - spec
  - executable skill copies
  - references
  - tests

Only create a second follow-up task if Phase A/B proves there is still a
separate product-surface change, such as:

- OpenCode duplicate entry exposure that requires workflow product carrier
  redesign
- managed-surface expansion that would require `workflow_assets.py` change

This means the current PRD open question can be narrowed to:

- one main implementation task for audit-contract alignment
- optional second task only if workflow product surfaces must change

---

## Non-Goals To Preserve

- do not merge `workflow-capability-audit` logic back into `workflow-audit`
- do not change `COMPATIBLE_TRELLIS_VERSION` as part of this backfill
- do not treat repo-local `.kiro/` or `.qoder/` presence as automatic workflow
  adoption
- do not use this repo's customized hidden directories as a substitute for a
  fresh `/tmp + trellis init` baseline
- do not silently widen workflow-managed surface outside `workflow_assets.py`

---

## Evidence Pointers Used For This Analysis

Current repo runtime and rules:

- `.trellis/workflow.md`
- `.trellis/config.yaml`
- `.trellis/.version`
- `.trellis/scripts/common/active_task.py`
- `AGENTS.md`

Platform carriers:

- `.claude/settings.json`
- `.claude/hooks/inject-subagent-context.py`
- `.codex/config.toml`
- `.codex/hooks.json`
- `.codex/hooks/inject-workflow-state.py`
- `.codex/agents/trellis-implement.toml`
- `.opencode/package.json`
- `.opencode/plugins/*`
- `.opencode/lib/trellis-context.js`
- `.qoder/settings.json`
- `.qoder/agents/*`
- `.kiro/hooks/inject-subagent-context.py`

Current workflow-audit contract surfaces:

- `.trellis/spec/skills/workflow-audit.md`
- `.agents/skills/workflow-audit/SKILL.md`
- `.claude/skills/workflow-audit/SKILL.md`

Workflow product authority:

- `docs/workflows/新项目开发工作流/commands/workflow_assets.py`

Relevant prior task context:

- `.trellis/tasks/archive/2026-05/05-07-workflow-audit/audit-report.md`
- `.trellis/tasks/archive/2026-05/05-08-fix-workflow-capability-audit-trellis-alignment/prd.md`
- `.trellis/tasks/archive/2026-05/05-05-audit-trellis-surfaces-outside-workflow/research/trellis-residual-surfaces.md`
