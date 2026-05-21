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
3. The default execution mode is inline in the current CLI session.
4. Helper agents are allowed only when the user explicitly provides
   `--agent`; this is an opt-in execution mode, not the default behavior.
5. In `--agent` mode, the current CLI session remains the coordinator and owns
   overwrite decisions, final finding judgment, report writing, and read-back
   validation.
6. `--agent` is a bounded evidence-gathering mode, not a general orchestration
   license; helper count and scope must stay intentionally small.
7. The skill never edits workflow source files, temp-project files, or task
   state. It only writes `WORKFLOW_QUESTIONS.md`.
8. The scan must not require or depend on the source repository as an evidence
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

### 1A. Execution Mode Resolution

The skill must:

- treat `--agent` as the only valid trigger for agent-assisted execution
- accept explicit natural-language equivalents to `--agent` only when they
  clearly request helper-agent use rather than merely asking for speed or depth
- keep inline execution as the default when `--agent` is absent
- keep "speed/depth only" requests inline unless they also explicitly ask for
  helper-agent use
- stop as **Blocked / Agent Mode Unsupported** when `--agent` is requested but
  the current platform/session cannot safely support helper agents
- use explicit capability criteria rather than vague product-family labels when
  deciding whether the current session is truly agent-capable
- keep helper scopes read-only and bounded to concrete evidence-gathering
  slices
- keep helper count intentionally small; a recommended ceiling of 3 should be
  the default, with 4 requiring an explicit concrete scope justification
- require the coordinator to resolve conflicting helper output before report
  generation
- keep the output file path and report schema identical across inline and
  `--agent` runs
- treat helper-dispatch mechanics as platform-specific implementation detail
  rather than as a single universal tool-binding promised by this skill

Agent-capable means all of the following are true at runtime:

- helper invocation is actually available in the current session
- helper agents can receive bounded ownership and return a distinct handoff
- no stronger repo-local/platform-local rule forbids helper use in this session
  (for example Codex inline main-session constraints)

If any of the above is unknown, the skill must treat the mode as unsupported.

The blocking rule for unsupported `--agent` mode applies at mode-selection
time. After helper dispatch has legitimately started, coordinator-side local
compensation for helper failure is allowed and is not considered an invalid
silent fallback.

Repair-side `--auto` follow-through remains outside scan execution mode. The
paired `workflow-repair` skill already broadened its current-task commit
confirmation detection, and this scan skill should document that compatibility
note only to the extent needed to keep it explicit that scan output and the
shared `WORKFLOW_QUESTIONS.md` schema remain unchanged.
Repair-side close-out also already tightened its rejection rules for mixed-
scope or misleading current-task commit confirmations, and this scan skill
should still document that only as a repair-side compatibility note rather
than implying any scan-side schema or overwrite-flow change.

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
- the required read-back validation step before the scan may report success

This coupling is **bidirectional and mandatory**:

- whenever `skills/workflow-scan/SKILL.md` changes any shared protocol,
  contract field, role boundary, or scan-side assumption, the paired
  `skills/workflow-repair/SKILL.md` surface must be updated in the same change
- the adaptation is not optional or deferrable; do not leave repair-side intake
  or examples on the previous contract
- scan-side execution-mode changes must state whether they do or do not affect
  repair-side intake assumptions; if they do not, that compatibility statement
  still belongs in the paired repair-side update

### 4. Evidence Discipline

The skill must:

- classify each finding as `trellis-native` or `workflow-source`
- tag each finding with the strongest supported temp-project evidence layer
- state inference explicitly when direct proof is unavailable
- record residual and new issues, not only user-supplied suspicions
- keep helper-agent handoffs separate from final findings; helper evidence is
  input to the coordinator, not a substitute for the coordinator's judgment
- require helper handoffs to follow a concrete reusable template when
  `--agent` is used
- verify source ownership boundary before escalating a temp-project observation
  into an actionable repair-side finding
- avoid reporting a `workflow-source` defect when the observed surface is a
  newly introduced shared or external baseline carrier that is not authored
  from `docs/workflows/新项目开发工作流/`
- avoid reporting a workflow defect when the temp project merely preserves a
  Trellis-native hook/runtime convention that the current workflow embed did
  not change
- emit such observations only when the current workflow explicitly claims
  ownership of that entry surface or changed that runtime behavior; otherwise
  omit them from the actionable finding set

### 5. Output Discipline

The report must remain directly usable as a handoff artifact for source-side
repair. It must therefore contain:

- scan summary counts
- analysis summary covering problem themes, gap/missing-surface themes,
  residual issues, and new issues
- concrete per-finding suggested investigation guidance

Before the skill reports success, it must read the generated
`WORKFLOW_QUESTIONS.md` back and verify the exact shared contract surface:

- frontmatter includes `document-type`, `protocol`, `trellis-version`,
  `workflow-version`, `workflow-schema-version`, `scan-timestamp`,
  `temp-project-root`, `total-findings`, `p0-count`, `p1-count`, and
  `p2-count`
- the report contains `## Scan Summary`
- the report contains `## Analysis Summary`
- finding sections use `### WS-NNN`
- the count fields match the actual number of findings and their P0/P1/P2
  severity split in the document body

If the generated file drifts into snake_case or omits a required section, the
skill must treat that as a failed scan output and correct it before stopping.

In `--agent` mode, the coordinator alone must perform this read-back
validation. Helper agents must not be treated as having completed the scan.

If helper execution fails, times out, returns malformed output, or conflicts
with sibling helper evidence, the coordinator must resolve or compensate in the
main session rather than treating the helper state itself as authoritative.

---

## Review Checklist

When editing `skills/workflow-scan/`, confirm all of the following:

- inline execution is still the default when `--agent` is absent
- `--agent` is the only explicit trigger for helper-agent execution
- helper-agent execution still leaves the current CLI session as coordinator
- the skill still blocks instead of silently falling back when `--agent` is
  requested but unsupported
- the agent-capable decision criteria are explicit enough to distinguish real
  runtime availability from product-family assumptions
- helper failure/conflict handling still routes final authority back to the
  coordinator
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
- scenario coverage for:
  - inline default without agents
  - successful `--agent` use in a supported session
  - `Blocked / Agent Mode Unsupported`
  - helper failure compensated locally by the coordinator
  - unresolved helper conflicts dropped conservatively instead of guessed through
  - partial helper output used only as a lead for local coordinator follow-up
  - speed/depth-only requests staying inline
- verify the scan-side `--agent` mode still leaves the shared output contract
  unchanged and that repair-side intake remains execution-mode agnostic
- verify any paired repair-side `--auto` close-out change is documented here as
  a compatibility note only, without implying any scan-side schema or overwrite
  behavior change
- verify the scan-side instructions now require a read-back validation step and
  explicitly guard against snake_case contract drift
- when the repair-side memory/auxiliary surfaces change, confirm whether the
  scan-side report wording or investigation guidance must be updated for
  compatibility with `tmp/workflow-issues/` consumption
- verify the paired `workflow-repair` diff is an actual compatibility
  adaptation when the scan-side contract changed, not just an unchanged carryover

## References

- `skills/workflow-scan/references/scan-output-template.md`
- `skills/workflow-scan/references/helper-handoff-template.md`

## Validation

`workflow-scan` should now carry persisted scenario tests in the same contract
style used by the repository's more complex workflow skills.

Each test file must use:

1. `Purpose`
2. `Input`
3. `Expected Mode`
4. `Expected Key Behaviors`
5. `Must Not`

First-version scenario set should cover at least:

- inline default with no helper agents
- supported `--agent` execution with coordinator-owned finalization
- explicit `Blocked / Agent Mode Unsupported`
- helper failure/timeout/malformed-handoff compensated locally by the
  coordinator
- unresolved helper conflicts dropped conservatively instead of guessed through
- partial helper output does not bypass coordinator confirmation
- speed/depth wording alone does not enable helper-agent mode
