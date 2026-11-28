# 实施计划：wf 控制流修复与跨会话接续

> 基线 `1f60bb25`；只在 `task.py start` 激活后改实现。按顺序执行，每步先红后绿；
> 任一验证失败先定位，不跳步、不改无关文件。所有测试前清理 `__pycache__`。

## 0. 准备（激活后）

- [x] 保存基线探针：把 `/tmp/wf_baseline_probe.py`、`/tmp/wf_stop_probe.py`、
  `/tmp/wf_release_probe.py` 与输出保存到 `research/baseline-probes/`（作为红证据）。
- [x] `git status --porcelain` 复核只有本任务允许的改动。
- [x] 记录候选身份：源树路径、HEAD、涉及文件、测试发行/部署来源。
- [x] 清理 pyc：
  `find docs/workflows/wf scripts/tests \( -name "*.pyc" -o -name __pycache__ \) -prune -exec rm -rf {} +`

## 1. F1 实例步骤契约

文件：`docs/workflows/wf/payload/lib/wflib/runs.py`、`.../check.py`、
`scripts/tests/wf_runtime/test_step_contract.py`。

- [x] `runs.step_contract` 保留 `established_by`/`stored_in`（仅拷贝 dict 形状），其余不变。
- [x] `check.check_step_contract`：
  - [x] 验证项解析：`stored_in.kind == task_plan` 时比 `stored_in.verification_id`；
    `consume_at` 比 plan 项；无 `stored_in` 走 legacy（不阻断，返回 legacy 事实）。
  - [x] `waived` 且 required 且无 `skip` → `pending_actions`（reason 明确）。
  - [x] 合并步骤级 + 动作级人判点；`choice` 非空且命中 `choices`（非空时）。
  - [x] 新问题条目带 `reason`/`accepted`/`choices`，exits 写收敛动作。
- [x] 测试先红：新增 5 个用例（A1–A5）；跑
  `/softwares/python/bin/python3 scripts/tests/wf_runtime/test_step_contract.py -v`。
- [x] 实现后绿；同步 `design.md` §6 迁移说明与机制稿对应字段消费描述
  （只写实现实际做的，不扩判定）。

## 2. F2 验收处置出口

文件：`.../projection.py`、`.../cli.py`、`.../gates.py`、`skills/wf-finish/SKILL.md`、
新测试 `scripts/tests/wf_runtime/test_verify_resolve.py`。

- [x] `projection.resolve` 索引 plan.acceptance + check.acceptance_results：
  - [x] 未知 id 拒绝（problems）。
  - [x] `narrow` 对 `passed`/`failed` 拒绝，`inspection` 只要求存在 + evidence。
- [x] `cmd_verify` 的 `next_` 改为「记录只落档，不改 Check；实质收窄走 task-replan/重批/重检」。
- [x] `gates.final_gate` 的 `pending_required` exits 改为三条可执行路径（见 design §F2）。
- [x] `wf-finish` 未核实段同步，删掉「resolve 后重入」的暗示。
- [x] 测试 A6/A7 先红后绿；断言 `required_unverified` 不因记录而误判结案。

## 3. F3 Check 发布/消费同条件

文件：`.../check.py`、`.../tasks.py`、新测试 `scripts/tests/wf_runtime/test_check_publish.py`。

- [x] `_parse_review_notes`：`conclusion == pass` 时 `basis` 必填。
- [x] `run_check_scope` 预解析 notes，state 增加 `internal_review`/`review_notes_digest`；
  解析失败抛 `WF_SEMANTIC_DECISION`（`exits` 指向 `--review-notes-draft` 与正确路径）。
- [x] `run_check_finish` 重读 notes 比 digest；变化 → `WF_CHECK_STALE`；用 state 中的解析结果。
- [x] 组装 `check` 后 `result == pass` 时调 `validate_check_result`；问题 → `WF_CHECK_FAILED`
  （facts.problems，exit 修正后重跑），不写 pass。
- [x] 测试 A8/A9：缺 basis 在 scope 段拒绝（不执行命令）；执行后改 notes → stale；
  构造会被 validate 拒的 pass → finish 抛错。
- [x] 回归 `test_check_lock_window.py`、`test_check_next_route.py`、`r7r15_tests`（Check 段）。

## 4. F4 实例释放 WIP

文件：`.../cli.py`、新测试 `scripts/tests/wf_runtime/test_run_release_wip.py`。

- [x] `_ensure_run_releasable`：任务非终态时分类当前任务，e∩uncommitted 非空 → 拒绝；
  facts 列 paths/task；exits 三条（保持写权/处置后重试/writer-handover）。
- [x] 分类失败 fail-closed，不释放。
- [x] 测试 A10：未登记 `src/a.py` → 拒绝；无未提交 → 放行；已登记 wip 行为不变。
- [x] 回归 `test_terminal_release.py`（16 例）。

## 5. F5 收工空 subject / a 桶

文件：`.../tasks.py`、扩展 `scripts/tests/wf_runtime/test_stop_ownership.py`。

- [x] 前移 `touch/receipts/classified/pending` 计算；空 subject 守卫只看 `pending`。
- [x] `keep`/`commit` 的 `owned` 改为 `e ∪ a`；`keep` 仍核 approved touch。
- [x] 错误文案改为「本任务仍有未提交改动」并列 pending。
- [x] 测试 A11/A12 先红后绿；原有 foreign 拒绝用例保持绿。
- [x] 回归 `r35r37_tests`（真实 stop keep）、`test_stop_ownership`。

## 6. F6 表述/登记

文件：`.../identity_store.py`、`.../cli.py`、`.../tasks.py`、
`docs/workflows/wf-framework-design.md`、`docs/workflows/wf-framework-mechanism.md`、
`docs/workflows/wf/payload/protocol/states.json`、新测试 `test_states_contract.py`。

- [x] C2 表述统一：启用入口是唯一登记通道；机制不核调用者身份；登记不是人批准证明。
  删掉 §1.3/identity_store/cli 的「仅人调」与「人调」出口字样。
- [x] `_commit_gate_problems` docstring 改准（任务提交入口；实例记录组不在列）。
- [x] `states.json`：`check.from` 加 finish；`finish-invalidate.action` 列表；
  `next_by_position` finish 行改写。
- [x] `test_states_contract` 断言三项；`protocol.py` 自检仍绿。
- [x] `grep -rn "仅人调" docs/workflows/wf` 零命中（除非历史叙述明确标注为已废止）。

## 7. 文档与机制同步

- [x] 机制稿登记本轮的字段消费/迁移变化（§3.5 步骤契约、§7.3 验证声明、§9.2 复核/验收、
  §4.4 释放前置、§5.3 收工）；只写实现实际行为。
- [x] 设计稿 §1.3 C2 表述；§5.7/§5.9 若措辞受影响同批。
- [x] `docs/workflows/wf/analysis/round-history.md` 追加本轮叙述（源码树未发版、候选身份、
  验证结果、未覆盖项），不写流水账。
- [x] 不重建发行树（版本推进需人；记录源码树与 0.0.22 发行树的差异）。

## 8. 定向验证（每步后）

```bash
PY=/softwares/python/bin/python3
$PY scripts/tests/wf_runtime/test_step_contract.py -v
$PY scripts/tests/wf_runtime/test_verify_resolve.py -v
$PY scripts/tests/wf_runtime/test_check_publish.py -v
$PY scripts/tests/wf_runtime/test_run_release_wip.py -v
$PY scripts/tests/wf_runtime/test_stop_ownership.py -v
$PY scripts/tests/wf_runtime/test_states_contract.py -v
$PY scripts/tests/wf_runtime/test_terminal_release.py -v
$PY scripts/tests/wf_runtime/test_w3_session_identity.py -v
```

## 9. 全量/受影响 runner（子集已跑，见 verification-ledger.md）

- [x] 先跑受影响单元：
  `WF_SUITES="f1_ordinary instance-task-phases r7r15_tests r35r37_tests" bash scripts/tests/wf_runtime/full/run_all.sh`
  （名称以 `units.json` 为准；先 `--list`/`--dry-run` 确认）。
- [x] 跑全量：`bash scripts/tests/wf_runtime/full/run_all.sh`（后台 job，完成后再收口；
  失败按 failure_owner 分类，不盲目重跑）。最终 59 套件 / 5 流程 / 93 repro 全绿、
  fail=0、GATE-OK、HYGIENE-OK（run_id `1795874618914-3924681-7b88e5bb863b`）。
- [x] 文档/资产闸门：
  ```bash
  $PY scripts/validate-wf-design.py
  $PY scripts/check-doc-refs.py
  ./scripts/validate-skills.sh
  $PY trellis-library/cli.py validate --strict-warnings
  ```
- [ ] 若改了 `scripts/tests`，按 `wf-delivery-discipline` 登记候选审计状态。
  本轮新增/修改测试文件未重生成 `candidate-audit.json`（需发行批次与 tag 同批），
  台账已如实登记为未覆盖项。

## 10. 维护接续验证

- [x] 写 `verification-ledger.md`：候选身份、逐项「预期/基线复现/修法/区分断言/候选结果」、
  已跑命令与结果、未覆盖项、下一条可执行验证。
- [x] 干净子代理（不共享当前上下文）只读 `prd.md`/`design.md`/`implement.md`/
  `verification-ledger.md` + `git log`/`git diff`，复述本轮状态与下一验证；记录差异。
  复审发现测试计数漂移与 `_commit_gate_problems` docstring 不准，已修正并复跑定向测试。
- [x] 若只做同会话重读，在台账标注「弱验证」——本轮为独立子代理只读，不属弱验证。

## 11. 产品接续验证（隔离目标）

- [x] `D=$(mktemp -d /tmp/wf-continuation-XXXX)`；`wf-dev-deploy.py --target "$D" --confirm`
  部署候选；记录部署来源/摘要（`dev:wf-v0.0.22-dirty`、86 文件、清单 `39d77343…`）。
- [x] 场景 1 同会话闭环；场景 2 旧对象终态 → `enable --new-session` → 第二对象；
  场景 3 `stop --keep`/task-pause + release + 新会话 `writer acquire`/`bind`/`task-resume`；
  实例 `run pause` + 未提交 WIP 的 release 拒绝；场景 4 无宿主标识派生路径。
  其中实例 run pause + WIP 由既有 `run-pause-and-advance`/`instance-task-phases` repro 覆盖，
  未另建 workflow 定义，台账已注明不冒充手工验证。
- [x] 每场景断言：旧绑定保留、目标对象与写权归属、下一条命令可执行、终态/接续事实。
- [x] 分栏记录：夹具模拟 / 真实宿主（DSH）/ 升级预览 / 实际升级。升级两项注明
  「未跑：无新发行版本；版本推进/发布需人授权」，不冒充。

## 12. 收口

- [x] 复核最终 `git diff`：只含本任务文件；无用户未提交工作被覆盖。
- [x] 每条根因有证据链；失败/未跑项如实保留状态。
- [x] 独立复审：子代理只读候选 diff + 验收台账，绑定 `git diff` 摘要与范围；
  改动后复验受影响的结论。
- [ ] 报告待审结果与精确变更范围；提交与 `finish-work` 等用户明确同意后再做。

## 回滚点

| 步骤 | 回滚方式 |
|---|---|
| F1 | 还原 `runs.py`/`check.py` 两处与测试 |
| F2 | 还原 `projection.py`/`cli.py`/`gates.py`/skill |
| F3 | 还原 `check.py` 三段与测试 |
| F4 | 还原 `cli.py::_ensure_run_releasable` |
| F5 | 还原 `tasks.py::stop_work` |
| F6 | 还原表述/`states.json` |
| 任一 | 按文件 `git checkout -- <path>` 前先确认该文件只含本任务改动；不 `reset --hard`、不 `clean` |