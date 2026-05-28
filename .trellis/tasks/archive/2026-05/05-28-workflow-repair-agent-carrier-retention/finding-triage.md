# Finding Triage

## Context

- Source report: `/tmp/trellis-0.5.17-2/WORKFLOW_QUESTIONS.md`
- Temp project: `/tmp/trellis-0.5.17-2`
- Workflow version: `0.1.2803`
- Trellis version: `0.5.17`
- Mode: read-only truth judgment after `workflow-repair` stopped on the cross-task lineage gate.

This file records whether the reported problems are real current workflow
defects. It is not a source repair log and does not authorize ordinary repair
execution for the same lineage.

## Summary

| WS-NNN | Report Classification | Truth Judgment | Source Repair Needed |
|--------|-----------------------|----------------|----------------------|
| WS-001 | design-debt | not a current defect | no |
| WS-002 | design-debt | mostly already documented; no functional defect | no |
| WS-003 | evidence-gap | false problem for fresh install; template/runtime split is expected | no |

## WS-001: Agent/subagent carrier retention

### Judgment

Not a current workflow defect.

### Evidence

- Temp project `.codex/agents/` contains `trellis-research.toml`,
  `trellis-implement.toml`, and `trellis-check.toml`.
- Temp project `.codex/config.toml` has
  `[workflow-embed-patch:codex-main-session-only]` and
  `features.multi_agent_v2.enabled = false`.
- Temp project `AGENTS.md` states that the embedded workflow explicitly
  disables `agent / subagent` execution and requires research / implement /
  check to stay in the current main session.
- Source `commands/codex/README.md` explicitly says `.codex/agents/*.toml`
  are subagent carriers and not the current embedded workflow's recommended
  execution path.
- Source `工作流总纲.md` explicitly states that retained Trellis-native carriers
  do not become formal workflow entrypoints, and that carrier presence with a
  disabled contract should be treated as a known gated state unless another
  installed surface routes into it.

### Reason

The carrier files exist, but the installed and source contracts both state
that they are disabled/gated. No inspected installed surface contradicts that
by routing users into those agents as an allowed workflow path.

## WS-002: Shared skill carrier ownership ambiguity

### Judgment

Mostly already documented; no functional defect.

### Evidence

- Temp project `.agents/skills/` contains shared workflow skills, including
  `trellis-start`, `trellis-continue`, and `trellis-finish-work`.
- Temp project `.codex/skills/` contains no files.
- Temp project `.trellis/workflow-installed.json` records
  `patched_codex_skills` for `trellis-continue`, `trellis-finish-work`, and
  `trellis-start`.
- Source `commands/codex/README.md` states that `.agents/skills/` is the shared
  workflow skills primary carrier and `.codex/skills/` is a secondary carrier
  for Codex-specific or project-local extra skills.
- Source `工作流总纲.md` and `装后隐藏目录与托管边界核对清单.md` both state that
  Codex carrier completeness should check `.agents/skills/` first and should
  not treat an empty `.codex/skills/` as shared workflow skill loss.

### Reason

The current source documentation already describes the carrier role split. The
temp project behavior matches that contract: shared and patched workflow skills
are in `.agents/skills/`, while `.codex/skills/` has no required Codex-local
content. This is not a current functional defect.

## WS-003: Finish-work checklist template vs runtime file

### Judgment

False problem for a fresh install before any task reaches delivery or
finish-work readiness.

### Evidence

- Temp project contains
  `.trellis/workflow-docs/finish-work-checklist-template.md`.
- Temp project contains no task-local `finish-work-checklist.md`; no task in
  the temp project has reached the gate where that runtime file is required.
- Temp project `trellis-finish-work` skill says that if the current task lacks
  `finish-work-checklist.md`, it should first use
  `.trellis/workflow-docs/finish-work-checklist-template.md` as the skeleton
  and then fill real results.
- Temp project `delivery` skill lists `$TASK_DIR/finish-work-checklist.md` as
  delivery/close-out output.
- Source `workflow_assets.py` lists `finish-work-checklist-template.md` under
  `WORKFLOW_SHARED_DOCS`, making the template the installer-managed shared
  document.

### Reason

The report conflates two different artifacts:

- `.trellis/workflow-docs/finish-work-checklist-template.md`: installed shared
  template, expected immediately after workflow install.
- `$TASK_DIR/finish-work-checklist.md`: task-local runtime evidence file,
  generated later when a task reaches delivery / finish-work readiness.

The absence of the runtime file in a fresh temp project is expected.

## Overall Decision

No source workflow repair is justified from these three findings. The better
next step for the recurring lineage is audit / break-loop, focused on why the
scan keeps surfacing already-documented gated or template/runtime states as
new report items.
