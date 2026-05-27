---
name: workflow-validate-matrix
description: Run matrix validation across multiple temp project scenarios to discover workflow installation issues. Tests 5 state/profile/CLI scenarios and generates workflow-repair compatible reports.
compatibility: Requires `trellis` on PATH, Python 3.8+, and execution from the workflow authoring repository. Uses a synced runtime bundle inside the skill payload and fails closed if that bundle drifts from the repo source.
---

# workflow-validate-matrix

## Version History

- **v1.1**: Expanded to 5 state/profile/CLI scenarios, added post-install integrity checks, exact embed-state parsing, and strict report read-back validation
- **v1.0**: Initial release - MVP with 2 scenarios (clean, existing-trellis)

## Purpose

Run comprehensive matrix validation across multiple temporary project scenarios to discover workflow installation and compatibility issues in a single run, breaking the incremental discovery loop.

This skill creates multiple temporary projects, installs the workflow in each, runs validation checks, and generates a consolidated report compatible with `workflow-repair`.

**Scope**: This skill validates workflow installation mechanics (detect-embed-state, install-workflow, upgrade-compat, workflow-state, embed_integrity, installed-surface contract checks). It does NOT perform deep workflow-scan level audits of all workflow surfaces, does NOT validate `uninstall-workflow.py`, and does NOT perform full semantic review of `.trellis/workflow.md` beyond install/runtime contract checks that already surface through `upgrade-compat --check` and `embed_integrity.py`. For uninstall coverage, rely on installer regression tests. For comprehensive workflow-surface audits, use `workflow-scan` on each scenario separately.

## When to Use

Use this skill when:
- You need to validate workflow changes before committing
- You want to avoid the incremental discovery loop (fix → test → find new issue → repeat)
- You're preparing for a workflow release
- You suspect issues might only appear in specific scenarios
- You want to verify that fixes don't introduce new problems

## When Not to Use

- Quick iteration on a single scenario: use `workflow-scan` instead (5-10 seconds vs 6-9 minutes)
- You only have one specific scenario to test
- You need uninstall-path validation: use the installer/uninstall regression suite, not this matrix
- You need full `.trellis/workflow.md` semantic auditing beyond install/runtime contract validation: use `workflow-scan` or workflow audit tooling
- You're working on non-workflow code

## Core Rules

1. **Source project only**: Run this skill in the workflow source project, not in temp projects
2. **Comprehensive validation**: Tests multiple scenarios in one run
3. **Continue on error**: One scenario failure doesn't block others
4. **Compatible output**: Generates `WORKFLOW_QUESTIONS.md` compatible with `workflow-repair`
5. **Clean temp dirs**: Creates unique temp directories to avoid conflicts
6. **Environment variables**: Automatically sets `WORKFLOW_EMBED_EXECUTOR_CONFIRMED=1` for Codex compatibility
7. **Exit code**: Returns non-zero if any scenario fails (suitable for CI/release gates)
8. **Runtime drift guard**: If the workflow runtime bundle is stale relative to the repo source, stop immediately and instruct the user to sync the payload and reinstall the global skill

## Inputs

| Input | Required | Default | Meaning |
|-------|----------|---------|---------|
| `--keep-temp` | No | false | Keep temporary directories after validation (for debugging) |
| `--output` | No | `./WORKFLOW_QUESTIONS.md` | Output report path |

## Output

Single file: `WORKFLOW_QUESTIONS.md` at the specified output path (default: current directory).

Format: Compatible with `workflow-scan-repair-v3` protocol, with additional matrix-specific fields.

## Workflow

### Step 1: Pre-flight Checks

1. Verify running in workflow source project
2. Verify the embedded runtime bundle is in sync with the repo source; otherwise stop with sync + reinstall instructions
3. Check disk space (need ~500MB in `/tmp`)
4. Verify `trellis` command available
5. Verify Python interpreter available

### Step 2: Create Scenarios

For each scenario:

1. Create unique temp directory under `/tmp/trellis-matrix-{timestamp-with-microseconds}/{scenario}`
2. Initialize scenario-specific state
3. Record scenario metadata

Default scenarios:
- `clean-outsourcing-all-cli`: fresh Trellis baseline, outsourcing profile, Claude + OpenCode + Codex
- `clean-personal-claude`: fresh Trellis baseline, personal profile, Claude only
- `existing-customized-all-cli`: existing Trellis task history plus CLI customizations, all CLI adapters
- `partial-failed-attempt`: failed embed-attempt record that must be blocked before install
- `preinstalled-upgrade-check`: already embedded workflow with legacy version metadata, used for upgrade compatibility validation

### Step 3: Run Validations

For each scenario:

1. Run scenario-specific validation chain:
   - Setup scenario (git init, initial commit, trellis init, and scenario fixtures)
   - Run `detect-embed-state.py --json` before install and match the exact expected status
   - Install workflow when the scenario is a fresh-install scenario
   - For blocked / already-installed scenarios, attempt install once and verify that it is explicitly rejected
   - Run post-install integrity checks using the bundled `workflow_assets.py` contract to validate installed assets, audit surfaces, and `workflow-installed.json`
   - Run `detect-embed-state.py --json` after install and expect `ALREADY_VALID_EMBEDDED`
   - Run `embed_integrity.py` and expect success for valid installs
   - Run `workflow-state.py route` and fail on blocking actions such as `embed_invalid`
   - Run `upgrade-compat.py --check` only for installed/upgrade scenarios
2. Collect structured findings from both failed steps and successful commands that emit warnings
3. On error: record error details, continue to next scenario

### Step 4: Generate Report

1. Aggregate all structured findings from every scenario
2. Assign `WS-NNN` IDs exactly once in render order
3. Write `WORKFLOW_QUESTIONS.md` with matrix-specific metadata and one matrix root
4. Read the report back and verify frontmatter counts, severity counts, required fields, sequential IDs, and Analysis Summary classification IDs
5. Clean up temp directories without deleting scenario dirs referenced by findings or failures (unless `--keep-temp`); if nothing is preserved, remove the matrix root too

### Step 5: Summary

Echo summary:
- Total scenarios tested
- Success/failure count
- Total findings
- Output file path
- Next steps (run `workflow-repair`)

## Error Handling

| Case | Behavior |
|------|----------|
| Not in source project | Stop with error message |
| Insufficient disk space | Stop with error message |
| `trellis` not found | Stop with error message |
| Runtime bundle drift | Stop with explicit sync + reinstall instructions |
| Scenario setup fails | Record error, continue other scenarios |
| Validation command fails | Record error, continue other scenarios |
| All scenarios fail | Generate report with failure details only |

## Related Skills

- `workflow-scan`: Quick single-scenario scan
- `workflow-repair`: Consume the generated report and fix issues
- `workflow-audit`: Comprehensive audit with version gates

## Examples

### Example 1: Standard Matrix Validation

```text
User: /workflow-validate-matrix

AI:
1. Pre-flight checks pass
2. Create 5 temp projects under one matrix root
3. Run validations across fresh install, profile/CLI, customized, blocked-state, and upgrade-check scenarios
4. Generate and read-back validate WORKFLOW_QUESTIONS.md
5. Clean scenario directories that are not referenced by findings or failures

Matrix validation complete
Scenarios: 5 tested, 5 succeeded, 0 failed
Findings: 0 total
Report: ./WORKFLOW_QUESTIONS.md
```

### Example 2: Partial Failure

```text
User: /workflow-validate-matrix

AI:
1. Pre-flight checks pass
2. Create 5 temp projects under one matrix root
3. Continue after one scenario reports a post-install integrity finding
4. Generate WORKFLOW_QUESTIONS.md with the failed scenario's structured finding
5. Preserve only scenario directories referenced by findings or failures

Matrix validation completed with failures
Scenarios: 5 tested, 4 succeeded, 1 failed
Findings: 1 total
Report: ./WORKFLOW_QUESTIONS.md
Next: review failure details in report, then run /workflow-repair
```

### Example 3: Keep Temp Directories

```text
User: /workflow-validate-matrix --keep-temp

AI:
1. Pre-flight checks pass
2. Create 5 temp projects
3. Run validations
4. Generate WORKFLOW_QUESTIONS.md
5. Keep all temp directories for debugging

Matrix validation complete
Scenarios: 5 tested
Report: ./WORKFLOW_QUESTIONS.md
Temp root preserved: /tmp/trellis-matrix-20260526-183045
```
