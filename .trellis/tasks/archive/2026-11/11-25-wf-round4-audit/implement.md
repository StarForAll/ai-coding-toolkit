# 执行计划：wf 第四轮复审的机制收口

## 顺序与检查点

1. **F1 实现**
   - 抽 `tasks._resolve_tdd(ctx, plan_decision, inputs)`，正式路径改调它（行为不变）。
   - 草稿分支：解析 block 后调用 `_complexity_proposal`，输出 `complexity_proposal`/`tdd`，
     approve 条目加 `plan`。
   - `confirmed_source` 三值 + `proposed` warning。
   - 改 `scripts/tests/wf_review/test_review_gates.py:139-142` 的源码字符串断言为行为断言。
   - 新增 `scripts/tests/wf_runtime/test_approve_draft_facts.py`。
   - 检查点：`python3 -m unittest scripts.tests.wf_runtime.test_approve_draft_facts scripts.tests.wf_review.test_review_gates -v`。

2. **F2 实现**
   - `review.round_entry_gate(task)` 单实现。
   - `cli.cmd_review_status`：`round < 1` 分支按 gate 分派，facts 增 `entry_gate`。
   - `review.launch`：锁前终态核验（终态 → `WF_SEMANTIC_DECISION` + 终态出口）。
   - 新增 `scripts/tests/wf_review/test_review_entry_gate.py`（三态 next + 归档 launch）。
   - 检查点：单文件跑绿；对既有 `test_review_status*`、`test_launch_mechanized` 无回归。

3. **F3 实现**
   - `wflib/codes.result`：pass 时 `exit=None`。
   - 新增 `scripts/tests/wf_runtime/test_result_exit.py`。
   - 检查点：单文件跑绿；`full/repro/record-missing-in-worktree.py` 场景属 blocked，不受影响。

4. **随批文档**
   - `docs/workflows/wf-framework-mechanism.md` §2.3 行（`confirmed_source` 三值、草稿事实）与 §11.1 段（pass 的 exit）。
   - `docs/workflows/wf/skills/wf-continue/SKILL.md:20` 补一句指针（不改判断句）。
   - `docs/workflows/wf/skills/wf-review-action/SKILL.md` 或 `wf-review` 若涉及终态审查文案，只在已被证伪处改。
   - 重建发行树：`python3 scripts/build-wf-release.py --version 0.0.1`（版本号不动；构建器按源树重建发行根）。

5. **验证（逐层）**
   - T0：`PYTHONPYCACHEPREFIX=/tmp/wf-unit-pycache /softwares/python/bin/python3 -m unittest discover -s scripts/tests -t .`
   - 设计闸门：`python3 scripts/validate-wf-design.py`、`python3 scripts/check-doc-refs.py`、`./scripts/validate-skills.sh`
   - 发行：`python3 scripts/build-wf-release.py --verify --verify-token-parity`
   - 全量：`bash scripts/tests/wf_runtime/full/run_all.sh --full --repro green`（要求 GATE-OK）
   - 手工：`scripts/wf-dev-deploy.py` 到临时项目，复跑草稿/批准/检查/归档，确认新事实。

6. **收尾（停在提交前）**
   - `trellis-check` 自查、`trellis-update-spec`（如产生可复用规则）。
   - 汇总 diff 与验证结果，**等待用户同意**后再提交/归档。

## 风险文件

- `docs/workflows/wf/payload/lib/wflib/tasks.py`（批准入口，多分支）
- `docs/workflows/wf/payload/lib/wflib/review.py`（launch 前缀）
- `docs/workflows/wf/payload/lib/wflib/cli.py`（review-status 投影）
- `docs/workflows/wf/payload/lib/wflib/codes.py`（全局结果结构）
- 发行树 `docs/workflows/wf-release/`（生成物，只由构建器重建）

## 回退

任一步失败：先归因（实现缺陷修实现；事实不足才回改文档）。三处改动互不依赖，可按提交粒度回退；
不触碰任务记录格式，无数据迁移。

## 执行结果（2026-11-25）

| 步骤 | 结果 |
|---|---|
| F1 | `tasks._resolve_tdd` 单实现；草稿输出 `complexity_proposal`/`tdd` 并在 approve 条目预填 `plan`；`confirmed_source` 三值 + `proposed` warning；新增 6 用例 |
| F2 | `review.round_entry_gate` 单实现；`review-status` 按终态/轻量/复杂分派 next 并输出 `entry_gate`；`review-launch` 锁前终态首报（`WF_SEMANTIC_DECISION`）；新增 6 用例 |
| F3 | `codes.result` 的 pass `exit=null`；新增 4 用例；文本渲染不变 |
| 文档 | 机制稿 §2.3 行/段、§11.1；`wf-continue` 一步；wf README 本轮内容；`.trellis/spec/docs/wf-delivery-discipline.md` 第 6 条 |
| 夹具 | `test_dogfood_round2/3` 的假 Ctx 补 `inputs()`（接口已含该方法，夹具未跟进） |
| 构造 | 发行树按源树重建，`--verify` 字节复现 |

验证：T0 1949 全绿；全量 runner GATE-OK；设计闸门/doc-refs/skills/发行核对全绿；手工 dogfood 通过。

## 第二轮冻结（同日）

| 项 | 结果 |
|---|---|
| 草稿健壮性 | TDD 解析失败降级为 facts，不阻断骨架 |
| 轻量审查 | 投影文案与 `wf-review` 同口径；不给"临时加轮"出口 |
| 复杂分级 | 非 decision 来源给「归档会被拒」警告（不提前阻断） |
| spec 结构文件 | 顶层 index/checklist 排除出规则集；机制稿 §8.3 登记 |
| 新增用例 | `test_spec_structure_files`(4)、approve 草稿新增 3 条（共 9）、materials 回显断言 1 条 |
| 草稿预检 | 复杂提议下同时报 `complex_artifacts`（design/implement 缺口） |
| 材料回显 | 物化后用同一判据重算 `materials_check`；更新 2 条锁定旧时点的用例 |

## 第四轮冻结（同日）

| 项 | 结果 |
|---|---|
| TDD | 缺省取值 + "未由人确认"警告（不硬拒：§4.4 允许缺省） |
| 复杂分级 | 警告 + 下一跳改为"先补决定重批再开工"；硬拒与夹具迁移留给 tag/候选审计同批 |
| 夹具审计 | 实测改套件脚本会打红 `candidate-audit`（64→58），已回退；该约束写入交付纪律 spec |
| 文档 | README「存量分级载体」、机制稿 §2.3、`wf-continue` 已批准行 |
