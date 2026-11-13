# 执行计划：wf 控制流结构性修正

执行顺序按"低耦合 → 高耦合 → 文档/发行物"。每批 = 代码 + 同批测试；任何一批未过定向用例，不进入下一批。

## S0 基线（只读）

- [x] 记录基线：`git status` 干净；`/softwares/python/bin/python3 -m unittest discover -s scripts/tests -t .` 全绿（622 例）。
- [x] 读机制稿 §3.2/§3.5/§4.1/§9.1/§9.2/§12.2/§12.3 与实现稿 §2.3，确认落点编号；不读则不动笔。

## S1 运行态合并写（D1）

- [x] `payload/lib/wflib/session.py`：`write_runtime` → `_replace_runtime`；`update_runtime` 成为唯一公开写入 API（读取失败时建新记录）。
- [x] 改 5 处整份写：`runs.py`（bind、advance）、`tasks.py::_run_creation_steps`、`cli.py`（两处 bind/routing）。
- [x] 测试 `scripts/tests/wf_runtime/test_runtime_merge.py`：① 先写代次、后写游标，代次仍在；② 反向顺序同样；③ 结构守卫——`wflib/` 内 `write_runtime(` 只出现在 `session.py`。
- [x] 验证：`python3 -m unittest scripts.tests.wf_runtime.test_runtime_merge scripts.tests.wf_runtime.test_generation_carry -v`

## S2 报告输入校验单源（D6）

- [x] `review.py`：抽 `report_input_problems(payload, task=None)`（字段/非空/敏感面/axes/verdict 一致/状态头）。
- [x] `lint_report` 换用它并加 `status-head`（前 400 字符、`status=done`）；`import` 的字段核验换用它；`review_report_problems` 去掉重复实现、保留锚点与摘要比对。
- [x] 测试 `scripts/tests/wf_review/test_report_input_single_source.py`：空 `read-scope`、缺敏感面、状态头缺失/在末尾/非 done、申报 verdict 不一致 → lint 与 import 同结论（正例：合规报告两处都过）。
- [x] 验证：`python3 -m unittest scripts.tests.wf_review.test_report_input_single_source scripts.tests.wf_runtime.test_round_decisions -v`

## S3 审查覆盖判定（D2）

- [x] `review.py`：`coverage_state` + `coverage_acceptance`（`judgments` 的 `kind=缺口` + `waived_by=human:`，按 round 绑定）；`decide` 在输入成立后消费；删除 §4.8/§4.9 悬空引用。
- [x] 测试 `scripts/tests/wf_review/test_review_coverage.py`：全未覆盖 → `WF_REVIEW_INVALID`；部分未覆盖无接受 → `WF_SEMANTIC_DECISION` 且 facts 列轴；有接受 → verdict 可 pass 且 facts 带缺口；有 blocking + 接受缺口 → 仍 fail。
- [x] 验证：`python3 -m unittest scripts.tests.wf_review.test_review_coverage scripts.tests.wf_runtime.test_four_class_verdicts -v`

## S4 锚点纳入实例快照（D9）

- [x] `check.py::anchor_parts`：`run_id` 任务取 `run.definition.digest` + 快照文件摘要；缺失 → `WF_RECORD_INVALID`；无 `run_id` 仍 None。
- [x] 测试 `scripts/tests/wf_runtime/test_anchor_workflow_snapshot.py`：快照变 → 锚点变；快照缺失 → 报错；普通任务 → None 且不报缺。
- [x] 验证：`python3 -m unittest scripts.tests.wf_runtime.test_anchor_workflow_snapshot scripts.tests.wf_runtime.test_ready_runs -v`

## S5 材料差异源（D7）

- [x] `review.py::materialize_delivery(root, paths, base=None)` + `write_materials` 传 `task.baseline_head`，`status.json` 记 `diff_base`。
- [x] 测试 `scripts/tests/wf_review/test_material_baseline.py`：临时 git 仓库，中途提交修改/删除 + 未跟踪新增，三者都在 `diff.patch`；基线不可达 → `[wf-material-missing]`。
- [x] 验证：`python3 -m unittest scripts.tests.wf_review.test_material_baseline -v`

## S6 验证日志完整落盘（D8）

- [x] `check.py::_run_argv`：写完整遮罩输出 + 头尾截断标记；记录增 `log_digest/log_bytes/truncated`。
- [x] 测试 `scripts/tests/wf_runtime/test_verification_log.py`：大输出 → 头尾保留 + 截断标记；记录无全文；`--token` 值被遮罩。
- [x] 验证：`python3 -m unittest scripts.tests.wf_runtime.test_verification_log -v`

## S7 授权范围绑定（D4）

- [x] `authorize.py`：`export_scope`/`export_scope_problems`（task + 材料类 + 暂存根）；`review.py::launch` 消费。
- [x] `tasks.py` 提交守卫：`repo_rules` 改用 `covers(paths)`；未覆盖路径逐个列出。
- [x] 测试 `scripts/tests/wf_review/test_export_scope.py`：授权缺类/换任务/换暂存根 → 拒绝；同类同任务 → 放行；`repo_rules` 未覆盖路径 → 拒绝。
- [x] 验证：`python3 -m unittest scripts.tests.wf_review.test_export_scope scripts.tests.wf_runtime.test_register_close -v`

## S8 脱敏白名单（D5）

- [x] `authorize.py::redact`：按协议 keep 标签白名单 + 递归丢弃 + `redact_text` + quote 截断与 digest。
- [x] 测试 `scripts/tests/wf_review/test_redaction_allowlist.py`：嵌套 token、Bearer quote、未知键明文 → committed 无原文；`original_digest` 仍按原文。
- [x] 验证：`python3 -m unittest scripts.tests.wf_review.test_redaction_allowlist -v`

## S9 `review-launch` 机械化（D10）

- [x] `review.py`：`resolve_launch_request(ctx, task, impl, request)` 生成三类材料/只读范围/排除面；`--request` 可覆盖；`export_decision` 可省略。
- [x] 测试 `scripts/tests/wf_review/test_launch_mechanized.py`：无 request 可发起、记录三类齐全、exclusions 覆盖四类；手写 request 缺类仍拒绝。
- [x] 验证：`python3 -m unittest scripts.tests.wf_review.test_launch_mechanized scripts.tests.wf_runtime.test_launch_blocked_facts -v`

## S10 外来未提交改动排除（D3）

- [x] `decisions.py` 增域；`scope.py`：`exclusion_entries(decisions)`、`apply_exclusions(...)`（只吃 c 桶、摘要不符即失效）、`x` 桶事实。
- [x] `tasks.py::cmd_task_start` 与 `check.py::run_check_scope/run_check_finish` 消费；`task.execution.workspace_exclusions` 追加；`judgments.skeleton` 增 `workspace_exclusions` 事实。
- [x] 输出：`WF_WORKSPACE_UNRESOLVED` facts 增 `excluded` 与两条出口。
- [x] 测试 `scripts/tests/wf_runtime/test_workspace_exclusion.py`：① 无排除 → 阻断；② 排除匹配 → 放行且交付/指纹不变；③ 内容改动 → 失效复现；④ 排除路径不在 c 桶 → 拒绝（不静默）；⑤ Check 期间排除路径变化 → `WF_CHECK_STALE`。
- [x] 验证：`python3 -m unittest scripts.tests.wf_runtime.test_workspace_exclusion scripts.tests.wf_runtime.test_scope_d_bucket -v`

## S11 skill 与错误出口（D11）

- [x] `skills/wf-review-action/SKILL.md`：收敛责任段 + 指针；保留"不改 reviewer 报告/不代判"。
- [x] `skills/wf-start/SKILL.md`：启用无法建立时的事实与三条出口；明确不得自称 wf 流程。
- [x] `tasks.py::cmd_task_start` 版本失配 facts 增 `exits`（机械修订）。
- [x] 验证：`./scripts/validate-skills.sh`；`python3 scripts/validate-wf-design.py`（skill 文本不被机检，但改动需人读一遍）。

## S12 文档同步（D12）

- [x] 设计稿 §4.2 澄清句、§6.5 覆盖规则句、§8.2 两行（二值"外来未提交改动排除"、三档"审查覆盖缺口"）。
- [x] 机制稿：§0.1 变更说明 + 四份输入摘要；§3.2、§3.5、§4.1、§9.1、§9.2、§12.2、§12.3。
- [x] 实现稿 §2.3：决策域 9→10（`workspace_exclusion`）。
- [x] `docs/workflows/wf-variant.md` 首行历史标注。
- [x] 验证：`python3 scripts/validate-wf-design.py` 全绿（含定义/消费命中率、§8.2↔§12.2/12.3 映射、§0.1 摘要）。

## S13 回归与发行物

- [x] 全量：`/softwares/python/bin/python3 -m unittest discover -s scripts/tests -t .`
- [x] 文档：`python3 scripts/check-doc-refs.py`、`python3 scripts/check-wf-analysis.py`（若有）、`./scripts/validate-skills.sh`。
- [x] 发行树：`python3 scripts/build-wf-release.py --version 0.1.1` → `--verify` → `--verify-token-parity`。
- [x] 复核 diff：`git diff --stat` + 逐文件复核；确认未触碰 `~/projects/personal/traffic_monitor`。

## 回滚点

- S1–S10 每批一个提交批次（代码+测试同批）；失败按批回退，不回退其他批。
- S12 文档与 S13 发行树最后提交；`wf-v0.1.0` tag 不动，新增 `0.1.1` 的 tag 由人执行。

## 已知不在本任务范围

- A5（同进程新会话）、B7（报告独立修订通道）、B4 的"重装覆盖"主张：按 PRD 拒绝，只在文档/任务记录留结论。
- `upgrade --apply`（第三轮能力）不因本任务解封。

## 执行记录（2026-11-13）

- **代码**：D1/D6/D2/D9/D7/D8/D4/D5/D10/D3 全部落地；新增用例 11 个文件（51 例）。
- **全量**：`python3 -m unittest discover -s scripts/tests -t .` → 673 例 OK（基线 622）。
- **全量夹具**：`bash scripts/tests/wf_runtime/full/run_all.sh` → 149 项 0 失败、repro 85/85。
  过程中先出现 12 项失败，逐项归因后**全部是夹具未跟上接口**（报告缺首行 `status=done`、外发确认缺
  `task`+`materials`），不是实现回归；同步更新了 `full/` 与 `repro/` 夹具（r68/r69/r70/r71/r75/cp3 与 4 个 repro）。
- **文档**：设计稿 §4.2/§6.5 澄清、§8.2 两行（二值+三档）；机制稿 §0.1/§1.3/§3.2/§3.5/§9.1/§9.2/§12.2/§12.3；
  实现稿 §2.3 域表 9→10 与两条登记条目；`wf-variant.md` 历史标注；`docs/README.md` 同步。
- **校验**：`validate-wf-design.py` 七项+覆盖率通过（定义 100%/消费 100%、场景 92/92、14/14、摘要 4/4）；
  `check-doc-refs.py`、`check-wf-analysis.py`、`validate-skills.sh` 通过。
- **发行树**：`0.1.1` 重建并 `--verify` 字节复现、`--verify-token-parity` 通过；tag 由人创建。
- **未做的取舍**：A5/B7/B4-覆盖/B9-无豁免按 PRD 拒绝，证据写在机制稿 §0.1 与任务记录；
  `run_all.sh` 会用 `0.1.0` 重建发行树，收尾已再按 `0.1.1` 重建一次。

## 复审补齐（2026-11-13，逐项自查后）

第二轮以"接口改动是否处处跟上"为主线复核，补了 7 处**遗留/漏洞**（均含用例）：

1. `wf help review-launch` 仍写 `--launch-request`/`export_decision` 必填——与机械化后的入口矛盾；已改为"可选/覆盖入口"。
2. `wf help review-decide` 缺 `--gap-acceptance`——人拿到需人裁决档却不知道出口；已补，并加 `test_cli_flag_reaches_the_decide_entry`（接线测试，防"帮助有字、入口没接"）。
3. `review-status` 不投影覆盖状态——A3 修好后 AI 仍可能盲循环；已在 `status_of_round` 增 `coverage`（covered/uncovered/accepted）并让 next 提示缺口与接受出口。
4. 任务记录模板未声明 `workspace_exclusions`——机制稿写"初值空数组"而代码缺键；已补模板，并加断言。
5. 排除声明的 `quote` 原样入 committed——与脱敏协议"quote 摘要"不符；改为遮罩+截断 + `attestation_digest` 固定原文。
6. 中文凭据词（口令/密码/密钥/令牌/私钥）不被遮罩——中文文档与人写 quote 的主要形态；已加触发词与两条保守模式（不误伤"密码错误"这类散文），并加断言。
7. `--gap-acceptance` 可与 `--register-only`/`--unavailable` 同批（被静默忽略）、同一路径重复声明会写重复记录、非对象声明元素被静默跳过——三处已改为一律显式拒绝/按路径收敛。

复审后：`685 tests OK`；`validate-wf-design.py`、`check-doc-refs.py`、`check-wf-analysis.py`、`validate-skills.sh` 全绿；全量夹具再跑一遍（见下）。

### 无断言清单（按交付纪律 §6 登记）

- `cmd_task_start` 的"非普通任务 + `--workspace-exclusion`"拒绝分支：需要完整安装/写权/绑定夹具
  （`full/` 层）才能走到；当前以 helper 层用例覆盖排除语义，该分支只是参数拒绝。下一轮随完整夹具补断言。
- `review.launch` 的 `export_decision` 缺省改用"已入库确认摘要"这一行：由 `test_launch_mechanized.py`
  的"默认生成"用例间接覆盖（导入的记录里能看到该标签）；未单独断言其取值来源。
