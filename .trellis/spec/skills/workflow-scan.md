# workflow-scan Skill Specification

> Behavioral contract for the installable skill `skills/workflow-scan/`.

---

## Purpose

`workflow-scan` is the scan-side half of the installable `workflow-scan` /
`workflow-repair` pair.

It exists to inspect the full workflow content currently present inside a
Trellis temp project and produce one report file:

- `WORKFLOW_QUESTIONS.md`

It does not fix source files.

---

## Scope Boundary

`workflow-scan` must preserve all of the following:

1. The analysis target is the temp project's currently used workflow content,
   not the source repository runtime.
2. The canonical fixture path is `/tmp/trellis-{VERSION}-2`, where `VERSION`
   comes from `trellis -v`, unless an explicit override is provided.
3. The skill runs inline in the current CLI session. Do not route through
   agents or sub-agents.
4. The skill never edits workflow source files, temp-project files, or task
   state. It only writes `WORKFLOW_QUESTIONS.md`.
5. The scan must not require or depend on the source repository as an evidence
   input.

---

## Required Behaviors

### 1. Temp Project Resolution

The skill must:

- resolve the temp-project path dynamically from `trellis -v` when the user did
  not supply a path
- stop instead of guessing when the path is ambiguous
- verify `.trellis/` and `.trellis/.version`
- verify that workflow-embed markers exist, not just Trellis baseline markers

### 2. Temp-Project-Only Evidence Model

The skill must analyze the temp project's currently used workflow surfaces from
the temp project itself.

Expected surfaces include, when present:

- `.trellis/workflow.md`
- `.trellis/workflow-installed.json`
- `.trellis/scripts/workflow/`
- `.trellis/workflow-docs/`
- `.agents/skills/`
- `.codex/`
- `.claude/commands/trellis/`
- `.opencode/commands/trellis/`
- installed runtime control files such as `AGENTS.md`, hooks, and related
  config surfaces whose current content shapes workflow behavior

The skill must not require:

- `commands/shell/init-trellis-temp-project.sh`
- `docs/workflows/新项目开发工作流/commands/workflow_assets.py`
- any other source-repo file as a prerequisite for the scan

### 3. Coupled Report Contract

The skill must emit `WORKFLOW_QUESTIONS.md` in the shared
`workflow-scan-repair-v2` format and keep the following aligned with
`workflow-repair`:

- frontmatter fields
- finding ID format `WS-NNN`
- category/origin/evidence-layer vocabularies
- analysis-summary semantics

This coupling is **bidirectional and mandatory**:

- whenever `skills/workflow-scan/SKILL.md` changes any shared protocol,
  contract field, role boundary, or scan-side assumption, the paired
  `skills/workflow-repair/SKILL.md` surface must be updated in the same change
- the adaptation is not optional or deferrable; do not leave repair-side intake
  or examples on the previous contract

### 4. Evidence Discipline

The skill must:

- classify each finding as `trellis-native` or `workflow-source`
- tag each finding with the strongest supported temp-project evidence layer
- state inference explicitly when direct proof is unavailable
- record residual and new issues, not only user-supplied suspicions

### 5. Output Discipline

The report must remain directly usable as a handoff artifact for source-side
repair. It must therefore contain:

- scan summary counts
- analysis summary covering problem themes, gap/missing-surface themes,
  residual issues, and new issues
- concrete per-finding suggested investigation guidance

---

## Review Checklist

When editing `skills/workflow-scan/`, confirm all of the following:

- the skill still forbids agent/sub-agent execution
- the skill still targets `/tmp/trellis-{VERSION}-2` by default
- the skill still emits `WORKFLOW_QUESTIONS.md` only
- the skill no longer requires source-project-root or source-repo evidence
- any protocol, field, role-boundary, example, or behavior change is mirrored
  by a matching `skills/workflow-repair/` adaptation and shared-template update
  in the same change

---

## Validation Notes

Minimum expected validation:

- `./scripts/validate-skills.sh`
- paired diff review across:
  - `skills/workflow-scan/SKILL.md`
  - `skills/workflow-repair/SKILL.md`
  - `skills/workflow-scan/references/scan-output-template.md`
- when the repair-side memory/auxiliary surfaces change, confirm whether the
  scan-side report wording or investigation guidance must be updated for
  compatibility with `tmp/workflow-issues/` consumption
- verify the paired `workflow-repair` diff is an actual compatibility
  adaptation when the scan-side contract changed, not just an unchanged carryover
