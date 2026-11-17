# C2 验证记录：命令证据、controller 生命周期与最终发布

> 实施会话 2026-11-17；解释器 `/softwares/python/bin/python3 -B`。

## 激活记录（2026-11-17）

- 实际会话：DSH **inline**（`dsh.dispatch_mode: inline`，`in_progress-inline` 横幅；主会话直接
  实现/检查，不派发 implement/check 子agent）。本任务 `implement.jsonl`/`check.jsonl` 有意为空，
  按 activation.md 的 inline 分支以 `task.py start --allow-empty-context` 激活；分支 `main`。
- 未使用 ZCode/其他 dispatch 分支；若未来切到 `dispatch_mode: auto`，必须先为该子任务填写
  真实 spec/research 清单并 `task.py validate`，不能沿用本次 inline 记录。

## AC01–03（清理证据与 finalize）

| 项 | 反例 | 正常 | 证据 |
|---|---|---|---|
| 结构缺失/矛盾 | 非对象、缺 supervision、cleanup 非法、`infrastructure_error` 缺失、干净但无 target rc 均判 unknown | cleaned/failed 原样保留 | `test_runner_cleanup.AssessExecutionTest` |
| receipt ledger | 错 run_id/域、started、local pending/failed、坏 JSON、未知子文件均计问题 | finished+cleaned 的 managed child 通过 | `ChildrenTest` |
| 删除许可 | unknown/矛盾 assessment 零删除；单根 rmtree 部分失败保 marker/残余 | 按 FIX→LEGACY_FIXTURE_ROOT→RUN_TEMPLATE；delete-after-first 精确报告 | `FinalizeTest`、`FaultSeamTest` |
| 现场保留 | 真实 root 收到 `WF_UNIT_FAULT=kill`：summary cleanup=unknown、fixture 保留、无 GATE-OK | — | `test_run_all_contract.test_cleanup_unknown_preserves_the_fixture_site` |

## AC07–10（生命周期/信号/清理）

- 每命令先写 receipt 再启动：standalone 隐藏 sibling、managed `commands/<id>.json`、root `.runner.json`；写失败不启动目标；相对 log 固定调用者 cwd；scope 越界在启动前拒绝（`test_execution.EvidenceTest`）。
- 隔离 HOME 每 command_id 唯一，cleaned 后回收、unknown 保留并写 `retained_paths`；repro 相位 TMPDIR 同规则；harness `_STAGED` 在托管 worker 下 defer。
- 确定性 G/S 点：`supervisor-before-ready` / `supervisor-after-started` / `guardian-after-started` × `exception|exit|kill|hang`，故障 spec 随 G/S 启动参数传递、W 环境剥离选择器；after-started 用 ready 管道确认目标已初始化（`test_supervision.DeterministicFaultPointTest`）。
- 取消：真实入口 SIGTERM 后 controller 记录 `status=cancelled`、cleanup=cleaned、evidence=incomplete，并删除 owned 夹具；scope 锁可立即重取（`test_interrupting_root_runner_cleans_its_command_and_fixtures`）。
- 初始化真死亡：首次/计划转执行/cleaned 重用 × 3 checkpoint，helper `os._exit(97)`、shell 原样退出、不启动 controller、下次入口拒绝并保留现场、锁释放（`test_init_checkpoint_death_leaves_identity_and_blocks_reuse`）。

## AC13–14（摘要、metrics 与发布）

- schema1 `summary-metrics.json` 绑定 run_id/canonical root/role 与 plan/context/lines/每个 unit/repro 输入摘要；reader 重算并逐项比对；缺失/截断/旧 run/输入漂移/写失败均由真实入口注入验证，且不得写 finished-cleaned / GATE-OK（`test_metrics_handoff_faults_are_rejected_by_the_reader`）。
- schema3 `summary.json` 一次原子发布并全对象读回；`status=ok` 同时要求 gate、cleanup=cleaned、evidence=complete；发布/读回失败非零（`test_results_summary`）。
- controller 故障矩阵：assess-exception/none/empty/malformed/contradictory、delete-oserror、delete-after-first、control-write-oserror、summary-exception/malformed、state-finish-oserror 均非零、无 GATE-OK，且不产生可复用 cleaned 组合（`test_controller_and_finalize_faults_never_sign_success`、`test_state_finish_failure_keeps_the_run_active`）。

## 命令

```bash
/softwares/python/bin/python3 -B -m unittest scripts.tests.wf_runtime.test_resource_lifecycle \
  scripts.tests.wf_runtime.test_runner_cleanup scripts.tests.wf_runtime.test_results_summary \
  scripts.tests.wf_runtime.test_results_gate scripts.tests.wf_runtime.test_execution \
  scripts.tests.wf_runtime.test_supervision scripts.tests.wf_runtime.test_fixture_scope \
  scripts.tests.wf_runtime.test_evidence_protocol scripts.tests.wf_runtime.test_candidate_audit
WF_SLOW_TESTS=1 /softwares/python/bin/python3 -B -m unittest scripts.tests.wf_runtime.test_run_all_contract  # 30 OK
/softwares/python/bin/python3 -B -m unittest discover -s scripts/tests -t .                              # 1223 OK
```

## 限制

- G/S 同时消失时仍只能报告 unknown 并保留现场；不承诺内核级不可回收对象或断电持久性。
- 独立 repro 的 candidate validator 只在独立入口调用一次（父 barrier 负责起始/结束），内嵌不重复。


## 复审补记

- `run_all` 内嵌 repro 的入口 rc 现计入 `STRUCTURAL_FAIL`（含并发 counters 缺失）；新增只读
  state 目录的真实 root 反例，确认无 GATE-OK。
- `candidate-audit` 生成环境清除了事务/初始化/执行故障选择器，避免无关运行继承。
