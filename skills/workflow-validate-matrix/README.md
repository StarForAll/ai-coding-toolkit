# workflow-validate-matrix

Matrix validation for workflow installation across multiple scenarios.

This skill is intended to run from the workflow authoring repository, but it
ships its own synced runtime bundle so the global skill install does not depend
on live `docs/workflows/.../commands/` paths at execution time.

## Purpose

Breaks the incremental discovery loop by testing workflow installation across multiple scenarios in a single run.

## Quick Start

### As a Skill (Recommended)

```bash
# In the workflow source project
/workflow-validate-matrix
```

### As a Standalone Script

```bash
# In the workflow source project
cd skills/workflow-validate-matrix
/ops/softwares/python/bin/python3 validate-matrix.py
```

## Options

- `--keep-temp`: Keep temporary directories after validation (for debugging)
- `--output PATH`: Specify output report path (default: `./WORKFLOW_QUESTIONS.md`)

## Runtime Sync

If the skill detects that the repo's shared workflow runtime changed after the
global skill was installed, it fails closed and tells you to:

```bash
/ops/softwares/python/bin/python3 scripts/sync-workflow-validate-matrix-runtime.py
npx skills add . -g -y
```

Run these from the workflow authoring repository root.

## Example Usage

```bash
# Standard validation
/workflow-validate-matrix

# Keep temp directories for debugging
/workflow-validate-matrix --keep-temp

# Custom output path
/workflow-validate-matrix --output /tmp/matrix-report.md
```

## What It Does

1. **Pre-flight checks**: Verifies runtime bundle sync, disk space, trellis availability, and authoring-repo context
2. **Creates 5 temp projects** under one matrix root (`/tmp/trellis-matrix-{timestamp}/`)
3. **Runs full validation** in each:
   - Setup scenario (git init, initial commit, trellis init, scenario-specific fixtures)
   - Run pre-install `detect-embed-state.py --json` with exact status matching
   - Install workflow for fresh-install scenarios
   - Verify required installed files and `workflow-installed.json`
   - Run post-install `detect-embed-state.py --json`
   - Run `workflow-state.py route` and flag blocking actions such as `embed_invalid`
   - Run `upgrade-compat.py --check` for installed/upgrade scenarios
4. **Generates consolidated report**: `WORKFLOW_QUESTIONS.md` compatible with `workflow-repair`
5. **Cleans up**: Removes scenario directories not referenced by findings/failures; keeps the matrix root for report context

## Output

Generates `WORKFLOW_QUESTIONS.md` with:
- Matrix-specific metadata (`matrix-validation: true`, `scenarios-tested: 5`)
- Findings from successful and failed scenarios
- Failure reports as structured `WS-NNN` findings
- Scenario tags on each finding

## Next Steps

After running matrix validation:

```bash
# Fix issues
/workflow-repair

# Verify fixes (should show 0 issues)
/workflow-validate-matrix
```

## Scenarios (MVP)

1. **clean-outsourcing-all-cli**: Fresh Trellis baseline, outsourcing profile, Claude + OpenCode + Codex
2. **clean-personal-claude**: Fresh Trellis baseline, personal profile, Claude only
3. **existing-customized-all-cli**: Existing task history plus pre-existing CLI customizations, all CLI adapters
4. **partial-failed-attempt**: Failed embed-attempt record, expected to be blocked before install
5. **preinstalled-upgrade-check**: Already embedded workflow with legacy version metadata, validating upgrade compatibility

## Environment Variables

- `PYTHON_BIN`: Python interpreter path (default: `/ops/softwares/python/bin/python3`)
- `TRELLIS_USER`: Trellis user name (default: `xzc`)
- `WORKFLOW_EMBED_EXECUTOR_CONFIRMED`: Automatically set to `1` by the skill (required for Codex execution)

## Requirements

- Python 3.8+
- `trellis` command in PATH
- At least 500MB free disk space in `/tmp`
- Running from workflow source project

## Troubleshooting

### "Could not find workflow source"

Make sure you're running from the workflow source project (the repo containing `docs/workflows/新项目开发工作流/`).

### "Insufficient disk space"

Free up at least 500MB in `/tmp`.

### "'trellis' command not found"

Install trellis or add it to your PATH.

### Scenario fails with timeout

Increase `STEP_TIMEOUT` in `constants.py` (default: 300 seconds).

## Architecture

```
validate-matrix.py       # Main entry point
constants.py             # Configuration
scenario_setup.py        # Scenario initialization
validation_runner.py     # Validation execution
report_generator.py      # Report generation
```

## Future Enhancements

- v1.2: Configuration file support (`scenarios.yaml`)
- v1.3: Command-line scenario selection (`--scenarios clean-outsourcing-all-cli,preinstalled-upgrade-check`)
- v2.0: Full matrix (2 profiles × 4 states × 3 CLI combinations)
- v2.1: Parallel execution
