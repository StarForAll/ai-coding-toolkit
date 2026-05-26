# workflow-validate-matrix

Matrix validation for workflow installation across multiple scenarios.

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
python3 validate-matrix.py
```

## Options

- `--keep-temp`: Keep temporary directories after validation (for debugging)
- `--output PATH`: Specify output report path (default: `./WORKFLOW_QUESTIONS.md`)

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

1. **Pre-flight checks**: Verifies disk space, trellis availability, workflow source location
2. **Creates 3 temp projects**: One for each scenario (clean, existing-trellis, existing-workflow)
3. **Runs full validation** in each:
   - Setup scenario (git init, trellis init, etc.)
   - Install workflow
   - Run detect-embed-state
   - Run upgrade-compat
   - Run workflow-state (if exists)
4. **Generates consolidated report**: `WORKFLOW_QUESTIONS.md` compatible with `workflow-repair`
5. **Cleans up**: Removes temp directories (unless `--keep-temp`)

## Output

Generates `WORKFLOW_QUESTIONS.md` with:
- Matrix-specific metadata (`matrix-validation: true`, `scenarios-tested: 3`)
- Findings from all successful scenarios
- Failure reports for failed scenarios
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

1. **clean**: Empty directory with git init only
2. **existing-trellis**: After trellis init
3. **existing-workflow**: With old workflow installed (upgrade scenario)

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

- v1.1: Configuration file support (`scenarios.yaml`)
- v1.2: Command-line scenario selection (`--scenarios clean,existing-trellis`)
- v2.0: Full matrix (2 profiles × 4 states × 3 CLI combinations)
- v2.1: Parallel execution
