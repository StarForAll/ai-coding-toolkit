# Research: check-quality.py false green exit code bug

- **Query**: Verify if check-quality.py has a "false green" exit code bug
- **Scope**: Internal
- **Date**: 2026-05-16

## Verdict: REAL

The bug is confirmed. The script always exits with code 0 regardless of whether checks pass or fail.

## Findings

### Files Found

| File Path | Description |
|---|---|
| `docs/workflows/新项目开发工作流/commands/shell/check-quality.py` | Main quality check script |
| `docs/workflows/新项目开发工作流/commands/shell/test_check_quality.py` | Existing test file (only tests happy path) |

### Bug Analysis

**Root cause**: `main()` at line 56 returns a hardcoded `0` on line 96. The return values from `run_optional_check()` (bool or None) are discarded at lines 65-71. No aggregation of failure status occurs.

**Exit code flow trace**:

1. Line 56: `def main() -> int:` declares it returns int
2. Lines 65-71: Calls `run_optional_check()` three times but **discards all return values**:
   ```python
   run_optional_check(args.test_cmd, "测试状态")    # line 65, return value ignored
   run_optional_check(args.lint_cmd, "Lint 状态")   # line 68, return value ignored
   run_optional_check(args.typecheck_cmd, "Type Check 状态")  # line 71, return value ignored
   ```
3. Line 96: `return 0` -- hardcoded, always returns success
4. Line 100: `raise SystemExit(main())` -- passes the always-0 to SystemExit

**`run_check()` return semantics (lines 28-45)**:
- Returns `True` when `result.returncode == 0` (check passed)
- Returns `False` on check failure or timeout
- Returns `None` when command not found

**`run_optional_check()` return semantics (lines 48-53)**:
- Returns `None` when no command provided
- Delegates to `run_check()` otherwise, forwarding True/False/None

**No call to `sys.exit(1)` exists anywhere in the file.**

### Existing Test Coverage Gaps

The test file `test_check_quality.py` only tests:
- `test_runs_explicit_commands_from_arguments`: Stub commands all `exit 0`, asserts `returncode == 0`
- `test_skips_checks_when_commands_are_not_provided`: No commands, asserts `returncode == 0`

**Missing**: No test case where a command returns non-zero exit code. No test asserts `returncode != 0`. The existing tests would pass even with the bug present.

### Proposed Fix

In `main()`, collect the return values from the three `run_optional_check()` calls, then evaluate the aggregate:

```python
def main() -> int:
    args = parse_args(sys.argv[1:])
    task_dir = Path(args.task_dir)

    print("=== 质量检查 ===")
    print("说明：...")

    results = []
    results.append(run_optional_check(args.test_cmd, "测试状态"))
    results.append(run_optional_check(args.lint_cmd, "Lint 状态"))
    results.append(run_optional_check(args.typecheck_cmd, "Type Check 状态"))

    # ... git status and history checks unchanged ...

    print()
    print("=== 质量检查完成 ===")
    print("下一步：根据以上结果生成 check.md 检查结果")

    # Any explicit False means a check failed
    if any(r is False for r in results):
        return 1
    return 0
```

Key semantics: `None` (skipped or command not found) should NOT cause failure. Only explicit `False` (check ran and failed, or timed out) should produce exit code 1.

## Caveats

- The Git status section (lines 74-83) and history check section (lines 86-91) are informational only and should not affect exit code.
- The `--test-cmd 'false'` reproduction mentioned in the issue is accurate: `false` returns exit code 1, `run_check` would return `False`, but `main()` still returns 0.
