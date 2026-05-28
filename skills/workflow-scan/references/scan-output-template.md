# WORKFLOW_QUESTIONS.md Format Specification

This document defines the contract format for the bridge document between
`workflow-scan` (producer) and `workflow-repair` (consumer).

Execution-mode note:

- `workflow-scan` may gather evidence inline by default or via explicit
  `--agent` helper assistance.
- `workflow-repair` may later run with plain repair flow or explicit `--auto`
  close-out follow-through in the source project.
- This **MUST NOT** change the `WORKFLOW_QUESTIONS.md` schema.
- The final report is always coordinator-owned and must pass the same
  read-back validation before `workflow-repair` may consume it.
- Repair-side `--auto` changes only post-repair source-project close-out
  behavior. It does not add report fields or alter repair-side intake rules for
  this document.
- Helper handoff artifacts, if any, are internal scan-side working context only
  and are not part of the shared scan/repair protocol surface.

---

## File Location

Always at the root of the temp project resolved from the live `trellis -v`
result: `/tmp/trellis-{VERSION}-2/WORKFLOW_QUESTIONS.md`

---

## Document Structure

### YAML Frontmatter (Required)

```yaml
---
document-type: workflow-questions
protocol: workflow-scan-repair-v4
trellis-version: <from the current `trellis -v` output, for example <LIVE_TRELLIS_VERSION>>
workflow-version: <from the temp project's installed workflow surfaces, for example `.trellis/workflow-installed.json` `workflow_version`; successful reports must not use `unknown`>
workflow-schema-version: <from `.trellis/workflow-installed.json`; successful reports must not use `unknown`>
scan-timestamp: <ISO 8601, e.g. 2026-05-20T14:30:00+08:00>
temp-project-root: <absolute path derived from the live trellis version, e.g. /tmp/trellis-<LIVE_TRELLIS_VERSION>-2>
total-findings: <N>
p0-count: <N>
p1-count: <N>
p2-count: <N>
---
```

### Field Rules

| Field | Required | Source |
|-------|----------|--------|
| `document-type` | Yes | Fixed value: `workflow-questions` |
| `protocol` | Yes | Fixed value: `workflow-scan-repair-v4` |
| `trellis-version` | Yes | Output of the current `trellis -v` command at runtime |
| `workflow-version` | Yes | Value from the temp project's installed workflow surfaces; successful reports must not use `unknown` |
| `workflow-schema-version` | Yes | `.trellis/workflow-installed.json` `workflow_schema_version`; successful reports must not use `unknown` |
| `scan-timestamp` | Yes | ISO 8601, local timezone |
| `temp-project-root` | Yes | Absolute path to temp project root |
| `total-findings` | Yes | Count of all findings in this document |
| `p0-count` | Yes | Count of P0 findings |
| `p1-count` | Yes | Count of P1 findings |
| `p2-count` | Yes | Count of P2 findings |

Count consistency rule:

- `total-findings` must match the actual number of `### WS-NNN` finding blocks
  in the document body
- `p0-count`, `p1-count`, and `p2-count` must match the actual severity split
  declared in the finding blocks

### Scan Summary Section (Required)

After frontmatter, include a brief summary:

```markdown
# Workflow Scan Report

## Scan Summary

- Trellis Version: {trellis-version}
- Workflow Version: {workflow-version}
- Workflow Schema Version: {workflow-schema-version}
- Scan Time: {scan-timestamp}
- Temp Project Root: {temp-project-root}
- Total Findings: {total-findings} (P0: {p0-count}, P1: {p1-count}, P2: {p2-count})
```

### Analysis Summary Section (Required)

After `## Scan Summary`, include an analysis summary that makes the report
directly usable as a "problem analysis + gap analysis + residual issues + new
issues" handoff:

```markdown
## Analysis Summary

- Problem Analysis: <short synthesis of the main issue themes; use `none` if there are no findings>
- Gap / Missing-Surface Analysis: <short synthesis of missing or incomplete workflow surfaces; use `none` if not present>
- Residual Issues: <WS-ID list or `none`>
- New Issues: <WS-ID list or `none`>
- Confirmed Defects: <WS-ID list or `none`>
- Design-Debt Items: <WS-ID list or `none`>
- Evidence-Gap Items: <WS-ID list or `none`>
```

Rules:

- `Problem Analysis` is the broadest summary and may reference any finding
  category.
- `Gap / Missing-Surface Analysis` focuses on missing, incomplete, stale, or
  inconsistent workflow surfaces inside the temp project.
- `Residual Issues` should list findings whose main classification is
  retired/stale leftovers.
- `New Issues` should list findings whose main classification is `new`.
- `Confirmed Defects` should list findings whose repair classification is
  `confirmed-defect`.
- `Design-Debt Items` should list findings whose repair classification is
  `design-debt`.
- `Evidence-Gap Items` should list findings whose repair classification is
  `evidence-gap`.

### Findings Section (Required)

Each finding is a level-3 heading with structured fields:

```markdown
### WS-NNN: <concise title>

- **Category**: script-behavior | cli-adaptation | post-install-artifact | document-reference | residual | new
- **Severity Estimate**: P0 | P1 | P2
- **Repair Classification**: confirmed-defect | design-debt | evidence-gap
- **Origin**: trellis-native | workflow-source
- **Evidence Layer**: generated-target-baseline | generated-target-installed | generated-target-runtime
- **Evidence**:
  - <observation 1>
  - <observation 2>
- **Temp Project Location**: <relative path within temp project, or concise multi-path description>
- **Description**: <what is wrong and why it is a candidate issue>
- **Suggested Investigation**: <what workflow-repair should verify in the temp project before deciding the source-side repair>
```

---

## Field Semantics

### Category Values

| Category | Meaning |
|----------|---------|
| `script-behavior` | A helper script or command produces incorrect output or exit code |
| `cli-adaptation` | A CLI carrier surface (skill/command/agent/hook) is missing, inconsistent, or behaviorally drifted |
| `post-install-artifact` | An artifact that should exist after install is missing, malformed, or contains wrong content |
| `document-reference` | A cross-reference in an installed document is broken or stale |
| `residual` | An artifact from a retired/removed feature still exists and should have been cleaned up; intentionally preserved restore surfaces such as valid `.backup-original/` copies are not residual by default |
| `new` | An issue not previously cataloged, potentially from a recent change |

### Origin Values

| Origin | Meaning | Repair Routing |
|--------|---------|----------------|
| `trellis-native` | The issue is in a file that `trellis init` produced or left in its current baseline/runtime state inside the temp project | Patch must live within the workflow so the installer can apply it |
| `workflow-source` | The issue was introduced by the embedded workflow's own install, patch, or runtime-control layer | Direct fix in `docs/workflows/新项目开发工作流/` |

### Evidence Layer Values

| Layer | Meaning |
|-------|---------|
| `generated-target-baseline` | Observed in a Trellis baseline surface present in the temp project |
| `generated-target-installed` | Observed in a workflow-installed or workflow-patched surface in the temp project |
| `generated-target-runtime` | Observed in a temp-project runtime/control surface whose current behavior matters beyond the install record alone |

### Severity Estimate

| Level | Meaning |
|-------|---------|
| `P0` | Broken functionality: scripts fail, commands produce wrong output, critical path is blocked |
| `P1` | Significant degradation: missing surfaces, inconsistent behavior, but core path still works |
| `P2` | Minor issue: cosmetic, documentation drift, non-blocking inconsistency |

**Note**: Severity is **preliminary** — set by the scan running in isolation
before repair. `workflow-repair` re-verifies and may reclassify.

### Repair Classification

| Value | Meaning | Default Repair Posture |
|-------|---------|------------------------|
| `confirmed-defect` | Temp-project evidence shows a concrete contradiction, broken behavior, missing/stale managed artifact, or another real defect that is actionable as workflow repair work | eligible for normal repair verification |
| `design-debt` | The concern is about complexity, maintainability, ergonomics, or over-design, but the temp project does not yet show a concrete installed-workflow defect or contradiction | do not auto-repair; treat as manual scope decision |
| `evidence-gap` | The observation looks suspicious, but the temp-project evidence is still insufficient to confirm a real defect or source-owned root cause | do not auto-repair; gather more evidence first |

Additional classification rule:

- When a carrier is still present but the installed workflow explicitly says it
  is intentionally gated off for now, retained only as a compatibility surface,
  or kept in place for possible future re-enable after maturity improves, that
  observation is omitted from the finding set unless another installed surface
  contradicts the stated “present but intentionally disabled” contract.
- For Codex, `.agents/skills/` is the shared workflow primary carrier and
  `.codex/skills/` is a secondary carrier for Codex-specific or project-local
  extras. An empty `.codex/skills/` directory or the absence of shared
  workflow skills there is not a finding by itself.
- When installed workflow surfaces consistently use uppercase `SKILL.md`, that
  filename convention is not a finding by itself.
- When an installed workflow explicitly disables a surface such as `parallel`
  and removes it from the active embedded state, the absence of an active
  command/skill file is not a finding by itself unless another installed
  surface explicitly requires a retained marker or stub.
- If the temp project shows no concrete contradiction beyond that intentional
  gated state, omit it from the `### WS-NNN` finding set.
- Contradiction examples include installed workflow docs still teaching that
  carrier's usage, hooks/config/runtime controls still invoking it, or another
  installed command/skill/agent surface still routing through it.

`Repair Classification` is the anti-overrepair guardrail. It determines whether
`workflow-repair` may treat the finding as part of the default repair-ready set.
It does **not** replace `Severity Estimate`; the two axes answer different
questions.

### Finding IDs

- Prefix: `WS-` (workflow-scan)
- Format: `WS-NNN` where NNN is zero-padded sequential number starting from
  `001`
- Sequential within the document, not per-category
- Unique within a single WORKFLOW_QUESTIONS.md file

---

## Complete Example

```markdown
---
document-type: workflow-questions
protocol: workflow-scan-repair-v4
trellis-version: <LIVE_TRELLIS_VERSION>
workflow-version: 0.1.2800
workflow-schema-version: 2
scan-timestamp: 2026-05-20T14:30:00+08:00
temp-project-root: /tmp/trellis-<LIVE_TRELLIS_VERSION>-2
total-findings: 4
p0-count: 1
p1-count: 1
p2-count: 2
---

# Workflow Scan Report

## Scan Summary

- Trellis Version: <LIVE_TRELLIS_VERSION>
- Workflow Version: 0.1.2800
- Workflow Schema Version: 2
- Scan Time: 2026-05-20T14:30:00+08:00
- Temp Project Root: /tmp/trellis-<LIVE_TRELLIS_VERSION>-2
- Total Findings: 4 (P0: 1, P1: 1, P2: 2)

## Analysis Summary

- Problem Analysis: The main failure themes are one broken patch-script contract, one stale document reference, one documentation maintainability concern, and one unresolved carrier-resolution ambiguity.
- Gap / Missing-Surface Analysis: WS-004
- Residual Issues: WS-002
- New Issues: WS-003
- Confirmed Defects: WS-001, WS-002
- Design-Debt Items: WS-003
- Evidence-Gap Items: WS-004

### WS-001: patch-session-start-strong-gate.py uses legacy READY/NOT READY semantics

- **Category**: script-behavior
- **Severity Estimate**: P0
- **Repair Classification**: confirmed-defect
- **Origin**: workflow-source
- **Evidence Layer**: generated-target-installed
- **Evidence**:
  - `.trellis/scripts/workflow/patch-session-start-strong-gate.py` line 42 checks for `READY` string instead of checking the strong-gate marker
  - The installed patch script does not verify the marker after applying
  - The surrounding temp-project workflow surfaces describe a strong-gate behavior instead of READY/NOT READY semantics
- **Temp Project Location**: .trellis/scripts/workflow/patch-session-start-strong-gate.py
- **Description**: The patch script uses legacy READY/NOT READY semantics instead of the marker-based strong-gate behavior exposed by the temp project's current workflow surfaces. This means the gate check may pass when it should block.
- **Suggested Investigation**: Re-check the installed patch script and the temp project's other startup/runtime-control surfaces to confirm whether the embedded workflow still relies on the legacy check.

### WS-002: Stale reference to record-session-helper.py in workflow.md

- **Category**: residual
- **Severity Estimate**: P2
- **Repair Classification**: confirmed-defect
- **Origin**: workflow-source
- **Evidence Layer**: generated-target-installed
- **Evidence**:
  - `.trellis/workflow.md` section "Helper Scripts" lists `record-session-helper.py`
  - The script is not present in `.trellis/scripts/workflow/`
  - No other installed workflow surface in the temp project still exposes the helper as active
- **Temp Project Location**: .trellis/workflow.md
- **Description**: The installed workflow document still references a helper that is no longer part of the temp project's active workflow surfaces.
- **Suggested Investigation**: Check the installed workflow document and related runtime docs in the temp project, then remove or replace the stale source-side reference if the temp-project evidence confirms it is obsolete.

### WS-003: Duplicate carrier-explanation notes increase maintenance cost without contradicting runtime behavior

- **Category**: new
- **Severity Estimate**: P2
- **Repair Classification**: design-debt
- **Origin**: workflow-source
- **Evidence Layer**: generated-target-installed
- **Evidence**:
  - `.trellis/workflow.md` and `.trellis/workflow-docs/命令映射.md` both explain the same Codex carrier fallback path in slightly different wording
  - The temp project's actual installed carrier surfaces remain consistent with both descriptions
  - No installed runtime surface shows a broken route or contradictory behavior
- **Temp Project Location**: .trellis/workflow.md and .trellis/workflow-docs/命令映射.md
- **Description**: The duplicate explanation does not currently break the installed workflow, but it increases maintenance cost and the chance of future wording drift.
- **Suggested Investigation**: Confirm whether one installed document can become the single source of truth for this explanation without changing runtime behavior.

### WS-004: Codex hook carrier ownership remains ambiguous in the installed temp project

- **Category**: cli-adaptation
- **Severity Estimate**: P1
- **Repair Classification**: evidence-gap
- **Origin**: trellis-native
- **Evidence Layer**: generated-target-runtime
- **Evidence**:
  - `.codex/hooks.json` references a generic hook helper entry rather than naming the resolved installed carrier path directly
  - `.trellis/workflow.md` says the Codex workflow adaptation should be active in the temp project
  - The available temp-project evidence does not yet prove whether the active runtime resolves that helper through the workflow-managed carrier or a Trellis-native baseline surface
- **Temp Project Location**: .codex/hooks.json and .trellis/workflow.md
- **Description**: The installed carrier wiring looks suspicious, but the scan cannot yet prove a broken route or whether the root cause belongs to workflow-source or Trellis-native ownership.
- **Suggested Investigation**: Re-check the installed hook/config surfaces and, if needed, exercise the Codex hook resolution path in the temp project before deciding whether a workflow-source repair is warranted.
```

Intentionally disabled compatibility carriers are not shown in the example
above because they should be omitted from the finding set unless another
installed surface contradicts the disabled contract. The example still keeps
one `design-debt` item and one `evidence-gap` item so all three repair
classification classes remain visible.

---

## Protocol Version

Current protocol version: `workflow-scan-repair-v4`

Runtime-value rule:

- Example placeholders such as `<LIVE_TRELLIS_VERSION>` are illustrative only.
- Real values must come from the temp project's current installed workflow
  surfaces and the live `trellis -v` result at execution time.
- Successful reports must not emit `workflow-version: unknown` or
  `workflow-schema-version: unknown`. If the temp project cannot provide both
  fields reliably, the scan must stop as invalid embedded state instead of
  producing a repair-consumable report.

If the format changes in a way that breaks backward compatibility, increment
the version. `workflow-repair` must validate the protocol field and stop if it
encounters an unknown version.
