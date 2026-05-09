# backfill-workflow-audit-optimization-task-info

## Goal

Capture, as task context only, the optimization directions that were proposed
earlier in this conversation for `workflow-audit` / `workflow-capability-audit`
 and related workflow-maintainer contracts. This task is for backfilling the
conversation-derived repair plan into Trellis task materials without executing
the implementation itself.

This backfill now also includes a deeper current-state analysis of how Trellis
is actually implemented in this repository, recorded in task-local `info.md`,
so later implementation work can distinguish:

- already-correct `workflow-audit` boundaries that should be preserved
- real same-version audit contract adjustments
- separate workflow-product changes that should not be silently folded into the
  same task

## Source Of This Task

This task is based on the **current conversation's initial analysis**, not on
historical archived task documents.

The relevant conversation-derived conclusions were:

* the current issue should be framed as workflow compatibility-governance
  cleanup rather than a simple `workflow-audit` wording tweak
* `workflow-audit` must remain the same-version maintenance audit entry point
* `workflow-capability-audit` must remain the version-upgrade compatibility
  audit entry point
* `workflow_assets.py` should continue to act as the single concrete source of
  truth for:
  * compatibility anchor version
  * managed surface definitions
  * Codex shared-vs-secondary skills carrier boundary
  * legacy migration assumptions
* maintainer docs and skill/spec surfaces should consistently reinforce the
  three-layer evidence model:
  * source repo carrier state
  * fresh `/tmp + trellis init` baseline
  * workflow-installed target-project state

## What I already know

From the earlier conversation analysis:

* current local Trellis version and workflow compatibility anchor were aligned
  at the time of analysis, so the immediate problem was **not** an anchor
  mismatch
* the real recommendation was to keep responsibility boundaries sharp instead
  of letting `workflow-audit` absorb upgrade-compatibility concerns
* `.trellis/` is the runtime truth surface, while hidden CLI directories such
  as `.claude/`, `.opencode/`, `.codex/`, `.agents/`, `.kiro/`, `.qoder/`
  are carrier layers with different ownership boundaries
* `workflow_assets.py` already acts as the central contract authority and
  future compatibility work should continue to route through it

From the current deeper repository read:

* current live versions still align at `0.5.9`:
  * `.trellis/.version = 0.5.9`
  * `trellis -v = 0.5.9`
  * `COMPATIBLE_TRELLIS_VERSION = "0.5.9"`
* current repo active-task behavior is session-scoped under
  `.trellis/.runtime/sessions/`, not old repo-global `.current-task`
* current `workflow-audit` already correctly preserves several important
  boundaries:
  * exact same-version gate
  * fixed workflow root
  * supported surface limited to Claude/OpenCode/Codex
  * `.kiro/` / `.qoder/` excluded unless `workflow_assets.py` expands first
* the remaining work is therefore mainly **mechanism-fidelity and
  evidence-model alignment**, not redoing solved version-gate work

## Assumptions

* this task is informational and preparatory only
* no workflow source files, skills, specs, scripts, tests, or docs should be
  modified as part of this task
* the output of this task should make later implementation easier by preserving
  the intended scope and sequencing of follow-up work

## Current Recommendation About Task Shape

Based on the current deeper analysis:

* use **one main implementation task** for `workflow-audit` contract alignment:
  * `.trellis/spec/skills/workflow-audit.md`
  * `.agents/skills/workflow-audit/`
  * `.claude/skills/workflow-audit/`
  * matching references/tests
* create a **separate follow-up task only if needed** for workflow-product
  surface changes such as:
  * OpenCode duplicate-entry carrier cleanup
  * explicit managed-surface expansion in `workflow_assets.py`
  * downstream workflow-doc propagation outside the audit contract itself

## Recommended Follow-Up Directions

These are the conversation-derived recommendations to preserve for later work:

1. Keep dual entry-point responsibilities strict.
   * `workflow-audit` = same-version workflow maintenance audit only
   * `workflow-capability-audit` = Trellis version-upgrade compatibility audit

2. Preserve `workflow_assets.py` as the only literal compatibility anchor and
   managed-surface truth source.
   * other docs/specs/skills/tests may reference the rule
   * they should not become competing value sources

3. Continue reinforcing the three-layer evidence boundary in maintainer-facing
   docs and audit output:
   * source repo carrier
   * fresh target baseline
   * workflow-installed target state

4. Make the current Trellis mechanism map explicit in future
   `workflow-audit` alignment work.
   * `.trellis/` = runtime truth layer
   * hidden platform directories = carrier layers with different loading models
   * `.agents/skills/` has dual role and must be described carefully
   * session-scoped active task under `.trellis/.runtime/sessions/` must remain
     the assumed runtime model

5. Treat future Trellis upgrades as a `workflow-capability-audit`-first flow.
   * run capability audit first
   * inspect A/B fixtures
   * adapt workflow source only after evidence is collected
   * write back the compatibility anchor only after the compatibility round is
     confirmed complete

6. Keep the “native Trellis agents are no longer workflow-overlaid” contract
   synchronized across installer/upgrade scripts, maintainer docs, and tests.

7. Keep `.kiro/` / `.qoder/` outside the workflow managed subset unless
   `workflow_assets.py` is intentionally expanded first.

8. Treat current Codex/OpenCode secondary surfaces as conditional audit topics,
   not unconditional baseline assumptions.
   * `.codex/skills/` is conditional secondary carrier, not current default
   * OpenCode `.agents/skills/` visibility is a same-version audit concern,
     not proof that workflow surface should widen automatically

## Requirements

* Preserve the above optimization plan in Trellis task materials.
* Persist the deeper current-state mechanism analysis in task-local `info.md`.
* Make it explicit that this task does **not** execute those changes.
* Point later work back to the relevant spec/skill source-of-truth surfaces.
* Distinguish "must-fix audit contract alignment" from "separate workflow
  product surface changes" so later implementation does not collapse them into
  one vague cleanup.

## Acceptance Criteria

* [x] `prd.md` records the conversation-derived optimization directions
* [x] `info.md` captures the current Trellis mechanism map and concrete repair
      sequencing
* [x] task materials clearly state that this task is informational only
* [x] at least the relevant current spec surfaces are referenced for future
      implementation

## Verification Notes

* Reviewed task-local `prd.md`, `info.md`, `task.json`, `check.jsonl`, and
  `implement.jsonl` together.
* Confirmed the task remains informational-only and points future work back to
  the current source-of-truth skill/spec surfaces.
* Confirmed the preserved follow-up plan separates:
  * correct existing `workflow-audit` boundaries to keep
  * required same-version audit contract alignment work
  * optional later workflow-product surface changes
* Confirmed current working-tree changes for this task are limited to the
  task-local backfill materials.

## Definition of Done

* The task captures the intended follow-up plan clearly enough that a later
  implementation task can reuse it directly.
* The task clearly separates:
  * preserved correct boundaries
  * real `workflow-audit` contract alignment work
  * optional later workflow-product changes
* No implementation files are changed.

## Out of Scope

* editing `.trellis/spec/skills/workflow-audit.md`
* editing `.trellis/spec/skills/workflow-capability-audit.md`
* editing `.agents/skills/workflow-audit/` or
  `.agents/skills/workflow-capability-audit/`
* editing workflow scripts, docs, references, or tests
* running any compatibility audit implementation flow

## Technical Notes

Likely future implementation surfaces:

* `.trellis/spec/skills/workflow-audit.md`
* `.trellis/spec/skills/workflow-capability-audit.md`
* `.agents/skills/workflow-audit/SKILL.md`
* `.agents/skills/workflow-capability-audit/SKILL.md`
* `.claude/skills/workflow-audit/SKILL.md`
* `docs/workflows/新项目开发工作流/commands/workflow_assets.py`
* maintainer-facing docs under `docs/workflows/新项目开发工作流/`

Task-local analysis output:

* `.trellis/tasks/05-09-backfill-workflow-audit-optimization-task-info/info.md`
