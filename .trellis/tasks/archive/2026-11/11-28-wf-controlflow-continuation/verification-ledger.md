# 验证台账：wf 控制流修复与跨会话接续

> 基线 `1f60bb25b4892b61c887999ae3947139692bbf86`；候选为当前源码树（未重建发行树）。
> 每行记录命令、结果、证据边界。未跑项写原因与影响。

## 1. 定向单测

| 命令 | 结果 | 说明 |
|---|---|---|
| `/softwares/python/bin/python3 scripts/tests/wf_runtime/test_step_contract.py -v` | 17/17 通过 | F1 五类缺口 + 历史契约 |
| `... test_verify_resolve.py -v` | 7/7 通过 | 未知 id / failed 收窄 / 记录只落档 |
| `... test_check_publish.py -v` | 5/5 通过 | 缺 basis、notes 不可读、准备段拒绝、pass 结构复用 |
| `... test_run_release_wip.py -v` | 5/5 通过 | 未登记 e/a 路径拒绝、干净放行 |
| `... test_stop_ownership.py -v` | 6/6 通过 | 空 subject 控制记录、a 桶、foreign 保持拒绝 |
| `... test_states_contract.py -v` | 3/3 通过 | check.from / action 列表 / next 文案 |
| `... test_terminal_release.py -v` | 16/16 通过 | 历史释放/轮换回归 |
| `... test_check_lock_window.py -v` | 3/3 通过 | 两段锁与执行窗口 |
| `... test_scope_d_bucket.py -v` | 7/7 通过 | 分类单源 |
| `... test_workspace_exclusion.py -v` | 11/11 通过 | 排除声明 |
| `... test_w3_session_identity.py -v` | 26/26 通过 | C2 身份出口 |

## 2. 全单元文件循环

命令：`for f in scripts/tests/wf_runtime/test_*.py; do $PY "$f"; done`

结果：除 `test_template_cache.py` 直接执行报
`NameError: name 'run_template_cli' is not defined` 外全部通过。该文件把
`if __name__ == "__main__": unittest.main()` 放在辅助函数 `run_template_cli` 定义之前
（`test_template_cache.py:615` vs `:619`），直接执行时测试先于定义运行；不在本 diff，
属基线布局问题。用 `python -m unittest` 导入执行可绕过，但本次未改该文件。

## 3. 文档/资产门禁

| 命令 | 结果 |
|---|---|
| `/softwares/python/bin/python3 scripts/validate-wf-design.py` | 通过（745 引用、输入摘要 4/4、定义/消费点 100%） |
| `/softwares/python/bin/python3 scripts/check-doc-refs.py` | 通过（0 problem） |
| `/softwares/python/bin/python3 scripts/wf-protocol-docs.py --check` | 通过（41 码/16 配置键/11 转移） |
| `./scripts/validate-skills.sh` | 通过（25 skill + spec 交叉检查） |
| `/softwares/python/bin/python3 trellis-library/cli.py validate --strict-warnings` | 退出码 0（5 条 mtime INFO） |

## 4. 受影响 full runner

命令：`WF_SUITES="f1_ordinary r7r15_tests r35r37_tests" bash scripts/tests/wf_runtime/full/run_all.sh --subset --serial`

结果：**通过**。`f1_ordinary` rc=0（2s）、`r35r37_tests` 15/15（2s）、`r7r15_tests` 38/38（10s）；`ASSESS_OK=1`、`ASSESS_FAIL=0`、`GATE-OK`。runner 报告 85 个存量 pyc 产物（非本次新增），已按计划清理。

## 5. 全量 runner

命令：`bash scripts/tests/wf_runtime/full/run_all.sh --full --serial`

结果：**59 套件 / 5 流程 / 93 repro 全绿，fail=0、bad=0、GATE-OK**，`HYGIENE-OK`（pyc=0、pycache_dirs=0），耗时 514s。
run_id `1795874618914-3924681-7b88e5bb863b`。首次 92/93 的 `uninstall-records-maintenance`
为 `inputs changed before execution`（运行期源码编辑），清理并冻结源码后重跑通过；
两次运行之间只修正了 `projection.resolve` 的「plan 有项但 Check 无结果」分支并补测试。

## 6. 产品接续（隔离目标）

部署：`scripts/wf-dev-deploy.py --target /tmp/wf-product-probe-oOSfRm --confirm --json`，
版本 `0.0.0-dev`、引用 `dev:wf-v0.0.22-dirty`、86 文件、清单摘要
`sha256:39d77343486c1ae9b97af53784c76d80e048454f1df3a9ee9807c54eaf20f1b6`。

| 场景 | 命令/结果 |
|---|---|
| 同会话闭环 | `task-new --kind initialize` → `task-approve` → `task-start` → `task-check`（v1 通过）→ `task-knowledge --no-update` → `archive`：业务段提交 `c8c39f29`、记录段提交 `a4bba1bf`，`archive_persisted=true`，`terminal=normal` |
| 旧对象终态后换新会话 | `enable --new-session`：`old_binding_preserved=true`、`rotated=true`；随后 `task-new --kind ordinary` 绑定第二对象 `2026-59018421a0be449592150f4219523e83` |
| 暂停/收工 | 第二对象 `task-pause` → `writer release` 成功（普通任务暂停不触发实例 WIP 门禁）→ `writer acquire` → `stop --decision keep` 保留 `wip.txt`，写权释放 |
| 无宿主标识 | `enable` 回显 `host_identity_absent=true`、`identity.source=anchor`、`new_session_indistinguishable=true`；按 anchor 派生会话，未伪造宿主身份 |
| 实例 run pause + WIP | 本场景由 `repro/run-pause-and-advance` 与 `repro/instance-task-phases` 覆盖；产品目标未另建 workflow 定义，故不冒充手工验证 |

## 7. 未覆盖 / 边界

- 未重建发行树/版本推进（需人授权）；产品目标为 `dev` 部署，非正式发行。
- 真实 DSH 宿主 dogfood 未跑；无宿主标识路径只验证了 anchor 降级。
- `stop` 的 a 桶归属放宽只对 `task_receipts` 本任务路径；b/c/d 与 foreign 拒绝不变。
- `writer release` 新增拒绝只影响「暂停实例 + 当前任务有未提交业务改动」；普通任务暂停不触发，
  已登记 WIP 行为不变。

