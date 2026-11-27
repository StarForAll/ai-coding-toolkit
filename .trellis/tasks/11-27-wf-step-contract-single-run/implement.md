# 实施计划

1. `runs.advance`：建任务分支写 `execution` 契约（`step/actions/human_points/verifications`）。
2. `decisions.DOMAINS`：新增 `action_result` 域（done/完成/waived/不适用）。
3. `check`：新增 `_step_contract_problems(...)` 与动作结果回写（准备段），接到 `run_check_scope`。
4. `check`：`task-check --run-verification` 的执行与记录（复用 `_run_argv`）。
5. `check.tdd_evidence_problem`：调用方并入 `execution.verification_runs` 作为红证据来源。
6. 用例：单元（契约生成/三类阻断/动作回写/单次运行记录/TDD 消费）+ 一条 CLI repro（单次运行）。
7. 文档：`payload/workflows/instance-flow.md`（任务生成段补契约）、`task-flow.md`（Check 出口）、
   `wf-tdd`、`wf-continue`（Check 行）、`wf help task-check`。

## 验证

- `python3 -m unittest discover -s scripts/tests -t .`
- `scripts/tests/wf_runtime/full/run_all.sh --full`
- `run.sh --mode red`（含新增 repro 的注入）
- `scripts/validate-wf-design.py`、`./scripts/validate-skills.sh`、`build_required_steps`


## 实施结果（2026-11-27）

1. `runs.step_contract(...)` + `run advance` 建任务分支写入 `execution.step/actions/human_points/verifications/verification_runs`。
2. `decisions`：新增 `action_result` 域；**修正 `canonical` 语义**（只归一同义写法——此前 `failed→passed`、`keep→commit`）。
3. `check.check_step_contract` / `apply_action_results` / `apply_decisions_to_actions`：契约三类事实核验 + 动作结果派生；
   应用点前移到**门禁求值之前**（否则 `task.work-satisfied` 先把待办报出来）。
4. `check.run_single_verification` + `tasks._single_verification`：`task-check --run-verification <id>`（互斥已登记）。
5. `check.verification_run_commands` → `tdd_evidence_problem` 的红证据池并入单次运行。
6. 文档：`instance-flow`（建任务写契约）、`task-flow`（Check 契约与单次运行出口）、`wf-tdd`（红证据走单次运行）、
   `wf-continue`（Check 行）、`wf help task-check`；机制稿与 round-history 同批登记。
7. 用例：`test_step_contract`（7）、`test_single_verification`（4）、`test_decision_canonical`（4）、
   repro `single-verification-run`（双模）；`instance-task-phases` 补契约执行与回显断言；覆盖率基线更新（92/62/30）。

验证：单测 **2152 OK**；`--full` 156 单元 fail=0 GATE-OK；`--mode red` **92/92**；设计稿/skills/required_steps 机检通过。

## 未做（明确边界）

- 定义里 `source=project` 的验证不被解析成命令：落地方式是"批准 plan 必须声明同一 id"（避免两处命令漂移）。
- 动作的业务完成度不由机制判：机制只记"谁在何时给出 done/waived"。
