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
protocol: workflow-scan-repair-v2
trellis-version: <from the current `trellis -v` output, for example <LIVE_TRELLIS_VERSION>>
workflow-version: <from the temp project's installed workflow surfaces, for example `.trellis/workflow-installed.json` `workflow_version`; use `unknown` when no reliable in-project value exists>
workflow-schema-version: <from `.trellis/workflow-installed.json` when available; otherwise `unknown`>
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
| `protocol` | Yes | Fixed value: `workflow-scan-repair-v2` |
| `trellis-version` | Yes | Output of the current `trellis -v` command at runtime |
| `workflow-version` | Yes | Best supported value from the temp project's installed workflow surfaces |
| `workflow-schema-version` | Yes | `.trellis/workflow-installed.json` `workflow_schema_version` when available, otherwise `unknown` |
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
```

Rules:

- `Problem Analysis` is the broadest summary and may reference any finding
  category.
- `Gap / Missing-Surface Analysis` focuses on missing, incomplete, stale, or
  inconsistent workflow surfaces inside the temp project.
- `Residual Issues` should list findings whose main classification is
  retired/stale leftovers.
- `New Issues` should list findings whose main classification is `new`.

### Findings Section (Required)

Each finding is a level-3 heading with structured fields:

```markdown
### WS-NNN: <concise title>

- **Category**: script-behavior | cli-adaptation | post-install-artifact | document-reference | residual | new
- **Severity Estimate**: P0 | P1 | P2
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
| `residual` | An artifact from a retired/removed feature still exists and should have been cleaned up |
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
protocol: workflow-scan-repair-v2
trellis-version: <LIVE_TRELLIS_VERSION>
workflow-version: 0.1.28
workflow-schema-version: 2
scan-timestamp: 2026-05-20T14:30:00+08:00
temp-project-root: /tmp/trellis-<LIVE_TRELLIS_VERSION>-2
total-findings: 3
p0-count: 1
p1-count: 1
p2-count: 1
---

# Workflow Scan Report

## Scan Summary

- Trellis Version: <LIVE_TRELLIS_VERSION>
- Workflow Version: 0.1.28
- Workflow Schema Version: 2
- Scan Time: 2026-05-20T14:30:00+08:00
- Temp Project Root: /tmp/trellis-<LIVE_TRELLIS_VERSION>-2
- Total Findings: 3 (P0: 1, P1: 1, P2: 1)

## Analysis Summary

- Problem Analysis: The main failure themes are one broken patch-script contract, one Codex adaptation ambiguity, and one stale document reference.
- Gap / Missing-Surface Analysis: Codex skill resolution needs confirmation because the temp project exposes an empty `.codex/skills/` directory while workflow skills live under `.agents/skills/`.
- Residual Issues: WS-003
- New Issues: none

### WS-001: patch-session-start-strong-gate.py uses legacy READY/NOT READY semantics

- **Category**: script-behavior
- **Severity Estimate**: P0
- **Origin**: workflow-source
- **Evidence Layer**: generated-target-installed
- **Evidence**:
  - `.trellis/scripts/workflow/patch-session-start-strong-gate.py` line 42 checks for `READY` string instead of checking the strong-gate marker
  - The installed patch script does not verify the marker after applying
  - The surrounding temp-project workflow surfaces describe a strong-gate behavior instead of READY/NOT READY semantics
- **Temp Project Location**: .trellis/scripts/workflow/patch-session-start-strong-gate.py
- **Description**: The patch script uses legacy READY/NOT READY semantics instead of the marker-based strong-gate behavior exposed by the temp project's current workflow surfaces. This means the gate check may pass when it should block.
- **Suggested Investigation**: Re-check the installed patch script and the temp project's other startup/runtime-control surfaces to confirm whether the embedded workflow still relies on the legacy check.

### WS-002: Codex .codex/skills/ directory is empty but .agents/skills/ has workflow skills

- **Category**: cli-adaptation
- **Severity Estimate**: P1
- **Origin**: trellis-native
- **Evidence Layer**: generated-target-runtime
- **Evidence**:
  - `.codex/skills/` exists but contains no SKILL.md files
  - `.agents/skills/` contains the workflow skills the temp project currently exposes
  - The temp project's installed workflow surfaces rely on `.agents/skills/` as the effective carrier
- **Temp Project Location**: .codex/skills/ and .agents/skills/
- **Description**: The empty `.codex/skills/` directory is a baseline/runtime surface that may confuse tools scanning the wrong carrier first, even though the temp project's active workflow currently lives under `.agents/skills/`.
- **Suggested Investigation**: Verify in the temp project which Codex carrier is actually authoritative, then decide whether the workflow should patch or document that behavior more clearly.

### WS-003: Stale reference to record-session-helper.py in workflow.md

- **Category**: residual
- **Severity Estimate**: P2
- **Origin**: workflow-source
- **Evidence Layer**: generated-target-installed
- **Evidence**:
  - `.trellis/workflow.md` section "Helper Scripts" lists `record-session-helper.py`
  - The script is not present in `.trellis/scripts/workflow/`
  - No other installed workflow surface in the temp project still exposes the helper as active
- **Temp Project Location**: .trellis/workflow.md
- **Description**: The installed workflow document still references a helper that is no longer part of the temp project's active workflow surfaces.
- **Suggested Investigation**: Check the installed workflow document and related runtime docs in the temp project, then remove or replace the stale source-side reference if the temp-project evidence confirms it is obsolete.
```

---

## Protocol Version

Current protocol version: `workflow-scan-repair-v2`

Runtime-value rule:

- Example placeholders such as `<LIVE_TRELLIS_VERSION>` are illustrative only.
- Real values must come from the temp project's current installed workflow
  surfaces and the live `trellis -v` result at execution time.

If the format changes in a way that breaks backward compatibility, increment
the version. `workflow-repair` must validate the protocol field and stop if it
encounters an unknown version.
