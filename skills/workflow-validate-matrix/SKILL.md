---
name: workflow-validate-matrix
description: Run matrix validation across multiple temp project scenarios to discover all workflow issues at once. Use when you need comprehensive validation before repair, or to verify fixes don't introduce new issues.
compatibility: Requires `trellis` on PATH, Python 3.8+, and access to workflow source at known location. Creates temporary projects under /tmp for testing.
---

# workflow-validate-matrix

## Version History

- **v1.0**: Initial release - MVP with 3 scenarios (clean, existing-trellis, existing-workflow)

## Purpose

Run comprehensive matrix validation across multiple temporary project scenarios to discover all workflow installation and compatibility issues in a single run, breaking the incremental discovery loop.

This skill creates multiple temporary projects, installs the workflow in each, runs full validation, and generates a consolidated report compatible with `workflow-repair`.

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
- You're working on non-workflow code

## Core Rules

1. **Source project only**: Run this skill in the workflow source project, not in temp projects
2. **Comprehensive validation**: Tests multiple scenarios in one run
3. **Continue on error**: One scenario failure doesn't block others
4. **Compatible output**: Generates `WORKFLOW_QUESTIONS.md` compatible with `workflow-repair`
5. **Clean temp dirs**: Creates unique temp directories to avoid conflicts

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
2. Check disk space (need ~500MB for 3 temp projects)
3. Verify `trellis` command available
4. Verify Python interpreter available
5. Locate workflow source directory

### Step 2: Create Scenarios

For each scenario (clean, existing-trellis, existing-workflow):

1. Create unique temp directory: `/tmp/trellis-matrix-{timestamp}-{scenario}`
2. Initialize scenario-specific state
3. Record scenario metadata

### Step 3: Run Validations

For each scenario:

1. Try to run full validation chain:
   - Setup scenario (git init, trellis init, etc.)
   - Install workflow
   - Run detect-embed-state
   - Run upgrade-compat
   - Run workflow-state (if exists)
2. Collect findings
3. On error: record error details, continue to next scenario

### Step 4: Generate Report

1. Aggregate all findings from successful scenarios
2. Add scenario tags to each finding
3. Include failure reports for failed scenarios
4. Write `WORKFLOW_QUESTIONS.md` with matrix-specific metadata
5. Clean up temp directories (unless `--keep-temp`)

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
2. Create 3 temp projects
3. Run validations:
   - Scenario 1 (clean): ✅ 5 findings
   - Scenario 2 (existing-trellis): ✅ 3 findings
   - Scenario 3 (existing-workflow): ✅ 8 findings
4. Generate WORKFLOW_QUESTIONS.md
5. Clean up temp directories

✅ Matrix validation complete
📊 Scenarios: 3 tested, 3 succeeded, 0 failed
📄 Findings: 16 total (P0: 2, P1: 8, P2: 6)
📝 Report: ./WORKFLOW_QUESTIONS.md
➡️ Next: run /workflow-repair to fix issues
```

### Example 2: Partial Failure

```text
User: /workflow-validate-matrix

AI:
1. Pre-flight checks pass
2. Create 3 temp projects
3. Run validations:
   - Scenario 1 (clean): ✅ 5 findings
   - Scenario 2 (existing-trellis): ❌ Failed (install-workflow.py error)
   - Scenario 3 (existing-workflow): ✅ 8 findings
4. Generate WORKFLOW_QUESTIONS.md (includes failure report)
5. Clean up temp directories

⚠️ Matrix validation completed with failures
📊 Scenarios: 3 tested, 2 succeeded, 1 failed
📄 Findings: 13 total from successful scenarios
📝 Report: ./WORKFLOW_QUESTIONS.md
➡️ Next: review failure details in report, then run /workflow-repair
```

### Example 3: Keep Temp Directories

```text
User: /workflow-validate-matrix --keep-temp

AI:
1. Pre-flight checks pass
2. Create 3 temp projects
3. Run validations (all succeed)
4. Generate WORKFLOW_QUESTIONS.md
5. Keep temp directories for debugging

✅ Matrix validation complete
📊 Scenarios: 3 tested, 3 succeeded, 0 failed
📄 Findings: 16 total
📝 Report: ./WORKFLOW_QUESTIONS.md
🗂️ Temp dirs preserved:
   - /tmp/trellis-matrix-20260526-183045-clean
   - /tmp/trellis-matrix-20260526-183045-existing-trellis
   - /tmp/trellis-matrix-20260526-183045-existing-workflow
➡️ Next: run /workflow-repair to fix issues
```
