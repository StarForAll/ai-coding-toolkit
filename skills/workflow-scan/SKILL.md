---
name: workflow-scan
description: Generate a `WORKFLOW_QUESTIONS.md` report for an embedded Trellis temp project. Use when scanning the temp project workflow for problems, gaps, residual issues, or new issues before source-side repair.
compatibility: Requires `trellis` on PATH, access to the workflow source repo and temp project fixture, and inline CLI execution with local filesystem access.
---

# workflow-scan

## Version History

- **v1.3**: Aligned frontmatter with the latest public skill spec by making the description explicitly cover both purpose and trigger, and by adding compatibility requirements
- **v1.2**: Replaced misleading fixed example paths and version literals with runtime-sensitive placeholders
- **v1.1**: Clarified temp-project provenance, no-agent execution, analysis-summary output, and evidence classification rules
- **v1.0**: Initial release

## Purpose

Scan the embedded workflow in a freshly created Trellis temp project for problems, gaps, residual issues, and new issues. Produce a structured `WORKFLOW_QUESTIONS.md` report for `workflow-repair` to consume in the source project.

This skill is the **analyzer/producer** half of the `workflow-scan` / `workflow-repair` coupled pair.

Its target of judgment is the embedded workflow result inside the temp project, not the current source repository runtime. It does not edit workflow source files, installed artifacts, or task state.

## When to Use

Use this skill when any of the following is true:

- you are working in a trellis temp project and need to analyze the embedded workflow for issues
- the temp project was created from the source repo's `commands/shell/init-trellis-temp-project.sh` and now needs a source-repair report
- the user asks to "scan the temp project workflow" or "check the embedded workflow for issues"
- the user asks to "produce workflow questions" or "generate a workflow scan report"
- the user asks to "run workflow-scan"
- a workflow analysis cycle starts and a structured report is needed before repair

## When Not to Use

- you need to fix issues: use `workflow-repair` in the source project
- you need a comprehensive audit with version gates and runtime validation: use `workflow-audit`
- you need version-drift analysis: use `workflow-capability-audit`
- you are doing a normal implementation task without workflow analysis

## Core Rules

1. **Scan only**: this skill produces a question/evidence document; it never edits workflow source files or any code.
2. **Main CLI only**: do not use agents, sub-agents, or task orchestration. Run the scan directly in the current CLI session.
3. **Temp project only**: this skill runs in or targets a Trellis temp project, never the source project as the analysis target.
4. **Embedded-workflow truth target**: judge whether issues exist from the installed result under `/tmp/trellis-{VERSION}-2`, not from the source repo alone.
5. **Bootstrap provenance matters**: treat `commands/shell/init-trellis-temp-project.sh` as the canonical fixture-creation path when it is available. If the temp project was created some other way, note reduced confidence.
6. **Evidence carries source-layer tags**: every finding must include an `Evidence Layer` value (`generated-target-baseline`, `generated-target-installed`, or `source-repo-reference`).
7. **Conservative severity**: severity estimates are preliminary, set by the scan running in isolation without source-side repair context. Mark explicitly as estimates.
8. **Complete catalog**: every anomaly discovered must be recorded. Do not filter by severity during the scan phase.
9. **Origin classification is mandatory**: every finding must classify as either `trellis-native` (produced by `trellis init`) or `workflow-source` (from the workflow's own install step).
10. **Contract format**: the output must use the `WORKFLOW_QUESTIONS.md` format exactly as defined in `references/scan-output-template.md`.

## Inputs

| Input | Required | Default | Meaning |
|-------|----------|---------|---------|
| `temp_project_path` | No | auto-detect | Absolute path to temp project root |
| `source_project_root` | No | auto-detect | Absolute path to the workflow source repository |
| `candidate_focus` | No | empty | Supplementary focus areas to prioritize |

### Temp Project Path Resolution

1. If `temp_project_path` is explicitly provided, use it.
2. Otherwise: run `trellis -v` to get VERSION, construct path `/tmp/trellis-{VERSION}-2/`.
3. Validate: the directory must exist and contain `.trellis/`.
4. If not found: stop as **Blocked / Temp Project Not Found**.

### Source Project Root

The source project root is the repository where the workflow source files live (for example `<SOURCE_PROJECT_ROOT>`). It is used to:
- read `workflow_assets.py` for version and asset declarations
- read `commands/shell/init-trellis-temp-project.sh` for the canonical fixture-creation flow
- compare source declarations against installed artifacts
- record the source-project-root in the report frontmatter

Resolve the source project root from:
1. The explicit `source_project_root` input, if provided
2. The current workspace root, if it contains both `commands/shell/init-trellis-temp-project.sh` and `docs/workflows/新项目开发工作流/`
3. A source-project root explicitly stated in the current conversation
4. Otherwise stop and ask the user for the absolute source-project root

## Output

Single file: `WORKFLOW_QUESTIONS.md` at the temp project root.

Format specification: see `references/scan-output-template.md`.

## Workflow

### Step 0: Environment Preflight

1. Resolve the source project root and read:
   - `commands/shell/init-trellis-temp-project.sh`
   - `docs/workflows/新项目开发工作流/commands/workflow_assets.py`
   If you are currently inside the temp project and `source_project_root` is still unknown, stop and ask. Do not guess from unrelated filesystem paths.
2. Resolve the temp project path (see Path Resolution above).
3. Verify the temp project is a valid Trellis-initialized project:
   - `.trellis/` directory exists
   - `.trellis/.version` exists and is readable
4. Verify the temp project also looks workflow-embedded:
   - `.trellis/workflow-installed.json` exists, or
   - `.trellis/scripts/workflow/` exists, or
   - another workflow-installed marker declared by `workflow_assets.py` exists
5. Read versions:
   - `trellis -v` → trellis version
   - `.trellis/.version` → temp project's trellis version
   - `workflow_assets.py` in the source project → `WORKFLOW_VERSION` and `COMPATIBLE_TRELLIS_VERSION`
6. If the temp project is not fully initialized (no `.trellis/` or no `.version`): stop as **Blocked / Invalid Temp Project**.
7. If the temp project is not workflow-embedded: stop as **Blocked / Workflow Not Embedded**.
8. If `WORKFLOW_QUESTIONS.md` already exists at the temp project root: stop and ask whether to overwrite or append.

### Step 1: Provenance and Artifact Inventory

1. Use the init script and `workflow_assets.py` to establish the canonical fixture-creation and install surfaces.
2. Catalog every file in the temp project that was created or modified by the workflow install:
   - `.trellis/scripts/workflow/` — helper scripts
   - `.claude/commands/trellis/` — Claude commands
   - `.opencode/commands/trellis/` — OpenCode commands
   - `.agents/skills/` — Codex/Agent shared skills
   - `.codex/` — Codex surfaces (agents, hooks, skills)
   - `.trellis/workflow.md` — workflow document
   - `.trellis/workflow-installed.json` — install record
   - `.trellis/workflow-docs/` — execution cards
3. For each artifact, classify the strongest supported provenance:
   - Trellis-native carrier or baseline surface not declared as a workflow overlay → `generated-target-baseline`
   - path or content declared as workflow-installed / overlay / patch output → `generated-target-installed`
   - source-side declaration or document used only as comparison context → `source-repo-reference`
4. If provenance is inferred rather than directly observable, state that inference explicitly inside the finding evidence.
5. Build the artifact inventory that later steps reference.

### Step 2: Script and Command Verification

For every installed script and command from the workflow:

1. **Existence**: verify the file exists at the expected path.
2. **Executability**: for shell/Python scripts, verify the file is executable or has a valid shebang.
3. **Content shape**: check that the script/command content matches what the source project declares (use `workflow_assets.py` `HELPER_SCRIPTS`, `DISTRIBUTED_COMMANDS`, `PATCH_BASELINE_COMMANDS` as the expected set).
4. **Exit-code contracts**: where documented, check if the script would produce the expected exit code for basic inputs.
5. **Init-path consistency**: if the init script hardcodes or derives a path relevant to the installed artifact, verify the installed artifact still matches that expected path.
6. Note any missing files, wrong paths, or content mismatches.

### Step 3: CLI Adaptation Surface Scan

For each CLI carrier (Claude Code, OpenCode, Codex) in the temp project:

1. **Skills**: catalog all installed skills per CLI. Check for:
   - missing skills that `workflow_assets.py` declares should be installed
   - skills present but with inconsistent content
   - skills that conflict with trellis-native equivalents
2. **Commands**: catalog all installed commands. Check for:
   - missing commands from the distributed/overlay/patch-baseline sets
   - commands with stale references or broken paths
3. **Agents**: catalog installed agents. Check for:
   - legacy agent names that should have been migrated
   - missing NL-routing blocks
4. **Hooks**: catalog hook configurations. Check for:
   - missing critical runtime patches (from `CRITICAL_RUNTIME_PATCHES`)
   - hook scripts that reference wrong paths
   - missing marker verification in patch scripts

### Step 4: Document Reference Integrity

For every installed workflow document:

1. Check that internal cross-references resolve to existing files.
2. Check that references to helper scripts use the installed path (`.trellis/scripts/workflow/`), not the source path.
3. Check that execution card references resolve.
4. Flag any broken or stale references.

### Step 5: Residual and New Issue Detection

1. **Retired artifacts**: compare against `RETIRED_HELPER_SCRIPTS` in `workflow_assets.py`. If any retired script still exists in the install, flag it.
2. **Install set gaps**: compare the actual installed files against the declared sets in `workflow_assets.py` (`HELPER_SCRIPTS`, `DISTRIBUTED_COMMANDS`, `ADDED_COMMANDS`, etc.). Flag any missing or extra files.
3. **Configuration drift**: check `.trellis/workflow-installed.json` against the actual installed state. Flag inconsistencies.
4. **New issues**: check for any anomalies not covered by the above categories — unexpected files, wrong permissions, encoding issues, broken assumptions, or install-script mismatches.

### Step 6: Compile WORKFLOW_QUESTIONS.md

1. Assign unique IDs to each finding: `WS-001`, `WS-002`, etc. (sequential, zero-padded to 3 digits).
2. For each finding, include all required fields per the finding entry schema:
   - Category (from the 6 allowed values)
   - Severity Estimate (P0/P1/P2, preliminary)
   - Origin (trellis-native or workflow-source)
   - Evidence Layer (generated-target-baseline, generated-target-installed, or source-repo-reference)
   - Evidence (list of observations)
   - Temp Project Location (relative path within temp project)
   - Suspected Source Location (relative path within docs/workflows/新项目开发工作流/)
   - Description (what is wrong and why)
   - Suggested Investigation (what workflow-repair should check)
3. Write the required `Analysis Summary` section so the report explicitly includes:
   - overall problem analysis
   - gap / missing-surface analysis
   - residual issue summary
   - new issue summary
4. Set frontmatter `protocol: workflow-scan-repair-v1` (must match the contract version).
5. Write the document using the format from `references/scan-output-template.md`.
6. Write to the temp project root as `WORKFLOW_QUESTIONS.md`.

### Step 7: Echo and Stop

1. Echo the output summary:
   - source project path
   - temp project path
   - output file path
   - total findings, P0/P1/P2 counts
2. Suggest the next step: run `workflow-repair` in the source project to consume the report.
3. Do not attempt any fixes, aggregation, or workflow state changes.

## Error Handling

| Case | Behavior |
|------|----------|
| Temp project not found | Stop as **Blocked / Temp Project Not Found**. Suggest running `init-trellis-temp-project.sh` first. |
| Temp project not fully initialized | Stop as **Blocked / Invalid Temp Project**. Verify `.trellis/` and `.version` exist. |
| Temp project not workflow-embedded | Stop as **Blocked / Workflow Not Embedded**. Verify the project was created via `commands/shell/init-trellis-temp-project.sh` and the workflow install actually completed. |
| WORKFLOW_QUESTIONS.md already exists | Stop and ask whether to overwrite or append. |
| workflow_assets.py not found in source | Stop as **Blocked / Source Project Not Found**. Ask for the source project root. |
| No findings | Write WORKFLOW_QUESTIONS.md with `total-findings: 0` and all counts at 0. |
| Ambiguous source project root | Stop and ask the user to provide the absolute path. |

## Related Skills

- `workflow-repair`: consumer/fixer pair — consumes the WORKFLOW_QUESTIONS.md this skill produces
- `workflow-audit`: comprehensive audit with version gates, evidence mainline, and runtime validation (complementary, not replacement)
- `workflow-capability-audit`: version-drift audit

## Examples

### Example 1: Standard Scan in Temp Project

```text
User: /workflow-scan

AI:
1. Resolve source repo and read `commands/shell/init-trellis-temp-project.sh`
2. Auto-detect temp project: run `trellis -v`, read the live version, then resolve `/tmp/trellis-{LIVE_VERSION}-2/`
3. Validate: `.trellis/` exists, `.version` matches, workflow embed markers exist
4. Execute Steps 1-5 (provenance inventory, script check, CLI scan, references, residuals)
5. Compile findings and analysis summary into `WORKFLOW_QUESTIONS.md`
6. Echo:
   ✅ Workflow scan complete
   📁 Source Project: <SOURCE_PROJECT_ROOT>
   📁 Temp Project: /tmp/trellis-{LIVE_VERSION}-2
   📄 Report: /tmp/trellis-{LIVE_VERSION}-2/WORKFLOW_QUESTIONS.md
   📊 Findings: 5 total (P0: 1, P1: 2, P2: 2)
   ➡️ Next: run /workflow-repair in the source project
```

### Example 2: Temp Project Not Found

```text
User: /workflow-scan

AI:
❌ Blocked / Temp Project Not Found
   Expected: /tmp/trellis-{LIVE_VERSION}-2/
   The directory does not exist or is not a valid trellis project.
   Suggestion: run `commands/shell/init-trellis-temp-project.sh` from the source repo first to create the temp project.
```

### Example 3: Clean Install With No Issues

```text
User: /workflow-scan

AI:
1. Auto-detect temp project from the current `trellis -v` result
2. Execute all scan steps
3. No anomalies found
4. Write WORKFLOW_QUESTIONS.md with total-findings: 0

   ✅ Workflow scan complete — no issues found
   📁 Source Project: <SOURCE_PROJECT_ROOT>
   📁 Temp Project: /tmp/trellis-{LIVE_VERSION}-2
   📄 Report: /tmp/trellis-{LIVE_VERSION}-2/WORKFLOW_QUESTIONS.md
   📊 Findings: 0 total (P0: 0, P1: 0, P2: 0)
```
