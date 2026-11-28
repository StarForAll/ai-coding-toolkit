# 基线复现探针（HEAD 1f60bb25）

这些脚本在修复前运行，记录 I1/I2/I3、I5、I4 的红证据；修复后旧行为不再成立，
脚本保留为"修复前基线"证据，不作为当前行为断言。当前行为的断言在
`scripts/tests/wf_runtime/test_step_contract.py`、`test_verify_resolve.py`、
`test_check_publish.py`、`test_stop_ownership.py`、`test_run_release_wip.py`。

## wf_baseline_probe.py 输出（修复前）

```
contract.verifications: [{"id": "v1", "source": "current_plan", "consume_at": "finish"}]
waived-on-required-no-skip problems= [] results= [{'id': 'write', 'result': 'waived'}]
invalid-human-choice problems= [] results= [{'id': 'write', 'result': 'done'}]
unanswered-action-human-point problems= [] results= [{'id': 'write', 'result': 'done'}]
verification-consume-at-mismatch problems= [] results= [{'id': 'write', 'result': 'done'}]
verify-resolve-nonexistent: accepted []
parse-pass-without-basis: accepted None
validate_check_result problems: [acceptance_results empty, internal_review.standard lacks basis, internal_review.requirement lacks basis]
```

## wf_stop_probe.py 输出（修复前）

```
empty-subject, only own control records dirty:
  WF_SEMANTIC_DECISION 工作区有未提交差异，收工决定须在 subject 列出覆盖路径
baseline a-bucket in approved touch:
  WF_WORKSPACE_UNRESOLVED foreign=[".wf/baseline.md"], owned=[]
```

## wf_release_probe.py 输出（修复前）

```
release allowed with unregistered src/a.py WIP
```

## 复算

```bash
/softwares/python/bin/python3 research/baseline-probes/wf_baseline_probe.py
/softwares/python/bin/python3 research/baseline-probes/wf_stop_probe.py
/softwares/python/bin/python3 research/baseline-probes/wf_release_probe.py
```

注意：这些脚本导入当前源码，修复后输出会与上面的"修复前"不同；要复现基线需
`git worktree` 检出 `1f60bb25` 后运行。
