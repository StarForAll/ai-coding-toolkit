# WORKFLOW_QUESTIONS.md Format Specification

This document defines the contract format for the bridge document between `workflow-scan` (producer) and `workflow-repair` (consumer).

---

## File Location

Always at the root of the temp project resolved from the live `trellis -v` result: `/tmp/trellis-{VERSION}-2/WORKFLOW_QUESTIONS.md`

---

## Document Structure

### YAML Frontmatter (Required)

```yaml
---
document-type: workflow-questions
protocol: workflow-scan-repair-v1
trellis-version: <from the current `trellis -v` output, for example <LIVE_TRELLIS_VERSION>>
workflow-version: <from workflow_assets.py WORKFLOW_VERSION, for example <WORKFLOW_VERSION>>
compatible-trellis-version: <from workflow_assets.py COMPATIBLE_TRELLIS_VERSION>
scan-timestamp: <ISO 8601, e.g. 2026-05-20T14:30:00+08:00>
temp-project-root: <absolute path derived from the live trellis version, e.g. /tmp/trellis-<LIVE_TRELLIS_VERSION>-2>
source-project-root: <absolute path to the source repo, e.g. /abs/path/to/source-repo>
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
| `protocol` | Yes | Fixed value: `workflow-scan-repair-v1` |
| `trellis-version` | Yes | Output of the current `trellis -v` command at runtime |
| `workflow-version` | Yes | `workflow_assets.py` `WORKFLOW_VERSION` |
| `compatible-trellis-version` | Yes | `workflow_assets.py` `COMPATIBLE_TRELLIS_VERSION` |
| `scan-timestamp` | Yes | ISO 8601, local timezone |
| `temp-project-root` | Yes | Absolute path to temp project root |
| `source-project-root` | Yes | Absolute path to the source repo (where the workflow source lives) |
| `total-findings` | Yes | Count of all findings in this document |
| `p0-count` | Yes | Count of P0 findings |
| `p1-count` | Yes | Count of P1 findings |
| `p2-count` | Yes | Count of P2 findings |

### Scan Summary Section (Required)

After frontmatter, include a brief summary:

```markdown
# Workflow Scan Report

## Scan Summary

- Trellis Version: {trellis-version}
- Workflow Version: {workflow-version}
- Compatible Trellis Version: {compatible-trellis-version}
- Scan Time: {scan-timestamp}
- Temp Project Root: {temp-project-root}
- Source Project Root: {source-project-root}
- Total Findings: {total-findings} (P0: {p0-count}, P1: {p1-count}, P2: {p2-count})
```

### Analysis Summary Section (Required)

After `## Scan Summary`, include an analysis summary that makes the report directly usable as a "problem analysis + gap analysis + residual issues + new issues" handoff:

```markdown
## Analysis Summary

- Problem Analysis: <short synthesis of the main issue themes; use `none` if there are no findings>
- Gap / Missing-Surface Analysis: <short synthesis of missing or incomplete workflow surfaces; use `none` if not present>
- Residual Issues: <WS-ID list or `none`>
- New Issues: <WS-ID list or `none`>
```

Rules:

- `Problem Analysis` is the broadest summary and may reference any finding category.
- `Gap / Missing-Surface Analysis` focuses on missing, incomplete, stale, or inconsistent workflow surfaces.
- `Residual Issues` should list findings whose main classification is retired/stale leftovers.
- `New Issues` should list findings whose main classification is `new`.

### Findings Section (Required)

Each finding is a level-3 heading with structured fields:

```markdown
### WS-NNN: <concise title>

- **Category**: script-behavior | cli-adaptation | post-install-artifact | document-reference | residual | new
- **Severity Estimate**: P0 | P1 | P2
- **Origin**: trellis-native | workflow-source
- **Evidence Layer**: generated-target-baseline | generated-target-installed | source-repo-reference
- **Evidence**:
  - <observation 1>
  - <observation 2>
- **Temp Project Location**: <relative path within temp project>
- **Suspected Source Location**: <relative path within docs/workflows/新项目开发工作流/>
- **Description**: <what is wrong and why it is a candidate issue>
- **Suggested Investigation**: <what workflow-repair should check in the temp project and source project>
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
| `trellis-native` | The issue is in a file that `trellis init` produced (not from workflow install) | Patch must live within the workflow so the installer can apply it |
| `workflow-source` | The issue originated from the workflow's own install step | Direct fix in `docs/workflows/新项目开发工作流/` |

### Evidence Layer Values

| Layer | Meaning |
|-------|---------|
| `generated-target-baseline` | Observed in the clean `trellis init` baseline before workflow install |
| `generated-target-installed` | Observed in the state after `install-workflow.py` ran |
| `source-repo-reference` | Observed by comparing against the source repo's workflow files |

### Severity Estimate

| Level | Meaning |
|-------|---------|
| `P0` | Broken functionality: scripts fail, commands produce wrong output, critical path is blocked |
| `P1` | Significant degradation: missing surfaces, inconsistent behavior, but core path still works |
| `P2` | Minor issue: cosmetic, documentation drift, non-blocking inconsistency |

**Note**: Severity is **preliminary** — set by the scan running in isolation without access to the source project. `workflow-repair` re-verifies and may reclassify.

### Finding IDs

- Prefix: `WS-` (workflow-scan)
- Format: `WS-NNN` where NNN is zero-padded sequential number starting from `001`
- Sequential within the document, not per-category
- Unique within a single WORKFLOW_QUESTIONS.md file

---

## Complete Example

```markdown
---
document-type: workflow-questions
protocol: workflow-scan-repair-v1
trellis-version: <LIVE_TRELLIS_VERSION>
workflow-version: <WORKFLOW_VERSION>
compatible-trellis-version: <COMPATIBLE_TRELLIS_VERSION>
scan-timestamp: 2026-05-20T14:30:00+08:00
temp-project-root: /tmp/trellis-<LIVE_TRELLIS_VERSION>-2
source-project-root: <SOURCE_PROJECT_ROOT>
total-findings: 3
p0-count: 1
p1-count: 1
p2-count: 1
---

# Workflow Scan Report

## Scan Summary

- Trellis Version: <LIVE_TRELLIS_VERSION>
- Workflow Version: <WORKFLOW_VERSION>
- Compatible Trellis Version: <COMPATIBLE_TRELLIS_VERSION>
- Scan Time: 2026-05-20T14:30:00+08:00
- Temp Project Root: /tmp/trellis-<LIVE_TRELLIS_VERSION>-2
- Source Project Root: <SOURCE_PROJECT_ROOT>
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
  - `workflow_assets.py` declares `session-start-strong-gate` in `CRITICAL_RUNTIME_PATCHES` with marker `SESSION_START_STRONG_GATE_PATCH_MARKER`
  - The patch script does not verify the marker after applying
- **Temp Project Location**: .trellis/scripts/workflow/patch-session-start-strong-gate.py
- **Suspected Source Location**: commands/shell/patch-session-start-strong-gate.py
- **Description**: The patch script uses legacy READY/NOT READY semantics instead of the strong-gate marker protocol defined in workflow_assets.py. This means the gate check may pass when it should block.
- **Suggested Investigation**: Compare the installed patch script against the source version in commands/shell/patch-session-start-strong-gate.py and confirm the temp-project script still reproduces the mismatch.

### WS-002: Codex .codex/skills/ directory is empty but .agents/skills/ has workflow skills

- **Category**: cli-adaptation
- **Severity Estimate**: P1
- **Origin**: trellis-native
- **Evidence Layer**: generated-target-baseline
- **Evidence**:
  - `.codex/skills/` exists but contains no SKILL.md files
  - `.agents/skills/` contains all distributed command skills (brainstorm, check, delivery, etc.)
  - `workflow_assets.py` defines `resolve_codex_skills_dir` with fallback logic from `.agents/skills/` to `.codex/skills/`
- **Temp Project Location**: .codex/skills/ and .agents/skills/
- **Suspected Source Location**: N/A (trellis-native)
- **Description**: The empty `.codex/skills/` directory is a trellis init artifact. The workflow correctly routes to `.agents/skills/` but the empty directory may confuse tools that scan `.codex/skills/` first. This is a cosmetic issue if the fallback works correctly.
- **Suggested Investigation**: Verify in the temp project that Codex tool resolution actually follows the fallback path, then confirm whether the source workflow intentionally relies on that behavior.

### WS-003: Stale reference to record-session-helper.py in workflow.md

- **Category**: residual
- **Severity Estimate**: P2
- **Origin**: workflow-source
- **Evidence Layer**: generated-target-installed
- **Evidence**:
  - `.trellis/workflow.md` section "Helper Scripts" lists `record-session-helper.py`
  - `workflow_assets.py` RETIRED_HELPER_SCRIPTS includes `record-session-helper.py`
  - The script is not installed in `.trellis/scripts/workflow/`
- **Temp Project Location**: .trellis/workflow.md
- **Suspected Source Location**: workflow.md (source document)
- **Description**: The workflow document still references a retired helper script. The script was correctly retired from the install set but the document reference was not updated.
- **Suggested Investigation**: Check that the temp-project document still exposes the stale reference, then remove the matching source-side reference if it still exists.
```

---

## Protocol Version

Current protocol version: `workflow-scan-repair-v1`

Runtime-value rule:

- Example placeholders such as `<LIVE_TRELLIS_VERSION>`, `<WORKFLOW_VERSION>`, `<COMPATIBLE_TRELLIS_VERSION>`, and `<SOURCE_PROJECT_ROOT>` are illustrative only.
- The real temp-project path must always be derived from the live `trellis -v` result at execution time.

If the format changes in a way that breaks backward compatibility, increment the version. `workflow-repair` must validate the protocol field and stop if it encounters an unknown version.
