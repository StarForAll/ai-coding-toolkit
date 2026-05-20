# workflow-scan Skill Specification

> Behavioral contract for the installable skill `skills/workflow-scan/`.

---

## Purpose

`workflow-scan` is the scan-side half of the installable `workflow-scan` /
`workflow-repair` pair.

It exists to inspect the embedded workflow result inside a Trellis temp project
and produce one report file:

- `WORKFLOW_QUESTIONS.md`

It does not fix source files.

---

## Scope Boundary

`workflow-scan` must preserve all of the following:

1. The analysis target is the temp project created for workflow checking, not
   the source repository runtime.
2. The canonical fixture path is `/tmp/trellis-{VERSION}-2`, where `VERSION`
   comes from `trellis -v`, unless an explicit override is provided.
3. The canonical fixture-creation flow is the source repo script
   `commands/shell/init-trellis-temp-project.sh`.
4. The skill runs inline in the current CLI session. Do not route through
   agents or sub-agents.
5. The skill never edits workflow source files, temp-project files, or task
   state. It only writes `WORKFLOW_QUESTIONS.md`.

---

## Required Behaviors

### 1. Temp Project Resolution

The skill must:

- resolve the temp-project path dynamically from `trellis -v` when the user did
  not supply a path
- stop instead of guessing when the path or source-project root is ambiguous
- verify `.trellis/` and `.trellis/.version`
- verify that workflow-embed markers exist, not just Trellis baseline markers

### 2. Source Context Resolution

The skill must read source-side workflow declarations from:

- `docs/workflows/新项目开发工作流/commands/workflow_assets.py`
- `commands/shell/init-trellis-temp-project.sh` when available

The init script is part of the evidence chain because it defines the canonical
fixture construction path that later repair work depends on.

### 3. Coupled Report Contract

The skill must emit `WORKFLOW_QUESTIONS.md` in the shared
`workflow-scan-repair-v1` format and keep the following aligned with
`workflow-repair`:

- frontmatter fields
- finding ID format `WS-NNN`
- category/origin/evidence-layer vocabularies
- analysis-summary semantics

### 4. Evidence Discipline

The skill must:

- classify each finding as `trellis-native` or `workflow-source`
- tag each finding with the strongest supported evidence layer
- state inference explicitly when direct before/after proof is unavailable
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
- the skill still treats `init-trellis-temp-project.sh` as the canonical
  fixture-creation path
- the skill still emits `WORKFLOW_QUESTIONS.md` only
- any protocol change is mirrored in `skills/workflow-repair/` and the shared
  template in the same change

---

## Validation Notes

Minimum expected validation:

- `./scripts/validate-skills.sh`
- paired diff review across:
  - `skills/workflow-scan/SKILL.md`
  - `skills/workflow-repair/SKILL.md`
  - `skills/workflow-scan/references/scan-output-template.md`
