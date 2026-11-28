# 设计：wf 控制流修复与跨会话接续

> 基线：`1f60bb25b4892b61c887999ae3947139692bbf86`（`0.0.22`）。
> 本文行号均指该基线；实现后行号会漂移，验收以行为断言与命令输出为准。
> 上位判据：设计稿 §1.1/§1.3/§4.3/§5.7/§5.9/§6.5、机制稿 §1.3/§2.2/§3.5/§4.3/§4.4/§7.2/§7.3/§9.1/§9.2/§11.3。
> 任务级证据只保留在本文与 `verification-ledger.md`，不回写产品规则之外的历史叙述。

## 1. 外审逐条裁定

| 编号 | 意见 | 裁定 | 处置 / 依据 |
|---|---|---|---|
| A1-1 | 实例的人判、必做动作、验证声明未完整兑现 | **成立（P1）** | I1；基线复现见 §3.1，四条缺口全部命中 |
| A1-2 | `verify resolve` 提供走不通的收尾出口 | **成立（P1）** | I2；`resolve` 只写 `unverified_resolutions`，不改变 `check.result`；基线接受不存在的验收 id |
| A1-3 | Check 发布条件与后续消费不一致 | **成立（P1）** | I3；`_parse_review_notes` 不核 `basis`，`run_check_finish` 仍可产 `pass`，Finish 端 `validate_check_result` 再拒 |
| A1-4 | 实例暂停与普通任务收工的 WIP 保障不一致 | **成立（P2）** | I4；`_ensure_run_releasable` 只查已登记 `handoff.wip` |
| A1-5 | 小修被治理面路径误升 | **部分成立，登记 backlog** | `paths.provably_disjoint` 只按字面前缀判；`src/*utils.py` 与 `src/*-schema.py` 落入 `prefix-unexcluded` 后按 `true` 提复杂。设计稿 §4.3 允许「分不清按复杂（宁高不低）」，故不是门禁缺陷；事实标签把保守策略写成 `true` 可改，但改它要动复杂度提议与既有断言，不属 S1–S4，登记 `backlog-controlflow-round1` 后续项 |
| A1-6 | 批准后改 PRD 错字也产生人签 | **不成立（属用法/判断）** | `choice=机械修订` 的人签是设计稿 §1.1 明文封闭清单项；进度/调查所得可写交接与判断记录而不动已批准正文。本轮不改机制，登记为摩擦项 |
| A1-7 | 长验证/审查环境摩擦晚暴露 | **部分成立，超范围** | 开工验证已有 `verification_timeout_seconds` 共用键（`tasks.py` 注释与实现），非「无超时」；复杂任务审查不可用已有 §6.5 出口（单 reviewer + 人签，或暂停/异常归档）。异步长验证承载已登记边界；本轮不扩 |
| A2-1 | C2 登记通道没有「人调」闸门 | **成立，但修法为纠正表述** | 设计稿 §1.1「主动触发」已明确：机制只核 activation、不核调用者身份、不提供「人调用过」的机器证明。§1.3 与 `identity_store`/`cli` 的「仅人调启用入口可登记」与此冲突。本轮 I6 改文本，不新增人证闸门（加闸门会改变新终端并行的既有出口，属另一变更） |
| A2-2 | `stop` 空 subject 死路 | **成立（P2）** | I5；基线复现见 §3.5，A/B 两条死路均可复算 |
| A2-3 | 单 reviewer 残余风险逐轮重签 | **不成立（按现行契约）** | 机制稿 §9.2 明确接受 `round` 精确等于本轮；这是「本轮只审一遍」的残余风险接受，不是长期能力授权。跨轮复用属设计变更，登记 backlog |
| A2-4 | reviewer 报告状态行靠手工翻转 | **成立（P4），登记 backlog** | `lint report` 只能发现不能消除；自动翻转需新的入口/语义，不属本轮承诺 |
| A2-5 | `_commit_gate_problems` 覆盖不全 | **成立（声明漂移）** | I8；`runs.py::_run_persist` 直接 `_commit_paths`。但实例记录组路径不含规则文件/删除，实际绕过面窄；本轮只把 docstring 改准，接线登记 backlog |
| A2-6 | `states.json` 迁移登记与实现漂移 | **成立（P2）** | I7；`spec.update` 同触 `finish→check`，`check` 的 `from` 不含 `finish`，而 `finish_check_stale_next` 明确推荐 Finish 中重跑 `task-check` |
| §1.1 | AI 指导是否准确 | **核心准确，不改 §1.1** | §1.1 的判据句、后置条件、人签封闭清单与「入口用法一个描述面」已覆盖 reviewer 三条建议；问题在 §1.3 的 C2 表述。不改 §1.1 以免扩范围 |

## 2. 历史故障复核（11-08 四份会话）

输入：`/tmp/traffic_monitor_1..4.md`（可读）、`~/.codex/sessions/2026/11/08/rollout-*.jsonl`
（四份可读）。`/tmp/wf-find-a.md`、`/tmp/wf-find-b.md` 缺失；ZCode 原日志未取得文本。
下表「证据」标注为 `会话导出` 或 `当前源码/用例`；只依赖台账转述的条目已注明。

| 历史故障 | 当前基线复核 | 结论 |
|---|---|---|
| H1 `enable` 后仍绑定已归档任务，`wf-start` 只让「恢复原对象」 | `enable` 回报 `binding.terminal`；`wf-start` 步骤 2 已给 `enable --new-session` 出口；`tests/test_terminal_release.py` 锁轮换出口 | **已闭合**（源码 + 用例） |
| H2 `task-new` 返回旧 bootstrap 任务的重试结果 | `tasks.py::cmd_task_new` 先按 writer 上的 `task.create` 意图续做；已绑定且对象终态时抛 `WF_BINDING_MISMATCH` 并给 `--new-session`，不再把旧任务当成功 | **已闭合**（源码） |
| H3 单 reviewer 判定被 `WF_REVIEW_INVALID / single-provider` 拒 | `review.py` 支持 `--single-reviewer-acceptance`（`by/at/quote/source` + `residual_risk` + `round`），只降级人数，其余门槛照旧 | **已闭合**（源码；跨轮复用仍为摩擦项，见 A2-3） |
| H4 `scope-exceptions` 被计为未覆盖例外 | `review.py` 只保留注释，`scope-exceptions`/`material-gaps` 不再进入缺口/失败消费；缺口只由 `axes: uncovered` 承载 | **已闭合**（源码） |
| H5 两轮审查额度用尽且 `task-rework` 不可用 | 两轮额度 2026-11-09 人裁删除（`review.py` 注释：轮次不设上限）；`task-rework` 已实现并接线（`cli.py` 命令表、`tasks.cmd_task_rework`） | **已闭合**（源码） |
| H6 `task-check` 被 `WF_WORKSPACE_UNRESOLVED` 拦在自身任务目录/`.gitignore` | `scope._is_control_record` 把 `.wf/tasks/<本任务>`、session/writer/runtime 等归 b 桶；`.gitignore` 仅在框架托管时归控制面 | **已闭合**（源码；I5 修的是 `stop` 的另一处原始未提交查询） |
| H7 review-notes 放错任务目录被误归「其他任务」 | `_parse_review_notes` 对缺失给「路径按进程 CWD 解析」与 `--review-notes-draft` 回显路径的 hint；`status.facts.task.directory` 已补 | **已闭合**（源码 + `test_terminal_release`） |

结论：历史故障本身不再构成本轮阻断；本轮阻断来自 §1 的 I1–I5 与表述漂移 I6–I8。

## 3. 根因与基线复现

基线复现脚本与输出保存在 `research/baseline-probes/`（实现阶段补齐断言版）。
关键输出（`/tmp/wf_baseline_probe.py`、`/tmp/wf_stop_probe.py`、`/tmp/wf_release_probe.py`）：

### 3.1 实例步骤契约（I1）

- `runs.step_contract`（`runs.py:1987`）只搬运 `{id, source, consume_at}`，丢掉定义里的
  `established_by` 与 `stored_in`。
- `check.check_step_contract`（`check.py:1409`）只比 `id ∈ plan.verifications`；
  步骤级人判只查 `subject` 是否含 id，不查 `choice` 是否命中 `choices`；
  动作级 `human_points` 完全不消费；`required` 动作的 `waived` 不要求 `skip` 声明。

基线输出：

```
contract.verifications: [{"id":"v1","source":"current_plan","consume_at":"finish"}]
waived-on-required-no-skip            problems= []   results=[write=waived]
invalid-human-choice                  problems= []   (confirm=maybe 被接受)
unanswered-action-human-point         problems= []   (approve-write 未答被接受)
verification-consume-at-mismatch      problems= []   (声明 finish / plan check 被接受)
```

### 3.2 `verify resolve`（I2）

- `projection.resolve`（`projection.py:203`）不核验收 id 是否存在、不区分
  `unverified` 与 `failed`，只写 `task.unverified_resolutions`。
- `projection.required_unverified`（`projection.py:197`）把有 resolution 的项当作已结案，
  但 `gates.final_gate`（`gates.py:1131`）第一项仍要求 `check.result == pass`；
  Check 的 `acceptance_results` 未变，重跑仍失败。故 `verify resolve → 重入` 不改变门禁。
- 基线输出：`verify-resolve-nonexistent: accepted []`（不存在的 id 也返回成功）。

### 3.3 Check 发布/消费（I3）

- `_parse_review_notes`（`check.py:974`）只核 `conclusion ∈ pass|fail|undecided`，不核 `basis`。
- `run_check_finish`（`check.py:1597`）的 `passed` 只看双轴 `conclusion`，不核 `basis`；
  `_parse_review_notes` 又在验证命令执行完之后才调用（`cmd_task_check` ② 段之后）。
- `check.validate_check_result`（`check.py:582`）在 Finish 门禁要求 `basis`，于是同一记录
  「发布 pass / 消费缺证据」两套结论。

基线输出：`parse-pass-without-basis: accepted None`；
`validate_check_result` 对该记录报 `internal_review.{standard,requirement} lacks basis`。

### 3.4 实例暂停/释放（I4）

- `run pause` 只标实例与当前任务暂停，不登记当前任务未提交 WIP。
- `cli._ensure_run_releasable`（`cli.py:2545`）只读 `tasks.wip_paths(task)`；未登记时
  直接返回，不查工作区。基线输出：`release allowed with unregistered src/a.py WIP`。

### 3.5 `stop` 空 subject / a 桶（I5）

- `tasks.stop_work`（`tasks.py:6188`）的空 subject 守卫在分类之前，直接调
  `scope.uncommitted_paths(root)`；该函数返回工作树与索引相对 HEAD 的全部差异，
  包含 `.wf/tasks/<本任务>/**` 这类归档前恒脏的控制记录。
- 把控制记录列进 subject：`_is_control_record` 归 b 桶；`keep`/`commit` 的归属核只认
  e 桶，b 桶被判 foreign。`reverse` 要求路径已无差异，控制记录仍有差异；`transfer`
  要求承接任务已批准且触碰面覆盖这些路径。四选一全灭。
- `baseline-apply` 后的 `.wf/baseline.md`/`.wf/project-config.json` 因回执归 a 桶，
  `keep`/`commit` 同样只认 e 桶 → foreign；不列则被空 subject 守卫以「工作区有未提交差异」拒。

基线输出：

```
empty-subject, only own control records dirty:
  WF_SEMANTIC_DECISION 工作区有未提交差异，收工决定须在 subject 列出覆盖路径
baseline a-bucket in approved touch:
  WF_WORKSPACE_UNRESOLVED foreign=[".wf/baseline.md"], owned=[]
```

### 3.6 表述/登记漂移（I6–I8）

- `identity_store.maintain_roots` docstring/`cli._enforce_roots` 出口/`_roots_registration_facts`
  说「仅人调启用入口可登记」，但 `enable` 的 `allow_concurrent=True` 对任何调用者放行；
  `session` 不提供调用者身份。设计稿 §1.1 已声明机制不核调用者身份 → §1.3 的「仅人调」是错误承诺。
- `tasks._commit_gate_problems` docstring 说「所有提交入口共用」，`runs.py::_run_persist`
  直接 `tasks_mod._commit_paths`。
- `states.json`：`finish-invalidate.action` 只有 `baseline-apply`，实际 `spec.update` 也调用
  `_reenter_check_from_finish`；`check.from` 不含 `finish`，但 `cli.finish_check_stale_next`
  推荐 Finish 中重跑 `task-check`，`cmd_task_check` 也不核 phase。

## 4. 修复设计

### F1 实例步骤契约（I1）

**写者**：`runs.step_contract`（唯一产生函数）。

- `verifications[]` 保留 `id/source/established_by/stored_in/consume_at`；缺字段只在
  旧契约出现，按 legacy 处理，不回写历史。
- 新增 `contract_schema` 版本事实？**不新增字段**：以 `stored_in` 是否存在区分新旧，
  避免记录 schema 变更与迁移。

**消费者**：`check.check_step_contract`（唯一判定）。

1. 验证项：
   - 落点必须命中已批准 `plan.verifications`：含 `stored_in` 时取
     `stored_in.verification_id` 解析 plan 项（声明 `id` 只是本地引用标识，可与 plan 项 id 不同）；
     `project_file` 还须 `path` 是项目内真实存在的文件；旧契约无 `stored_in` 时取声明 `id`；
   - `consume_at` 必须等于该 plan 项的 `consume_at`；
   - 若声明无 `stored_in`（旧契约）：只按 id 消费，并在返回 `legacy_verifications` 事实，
     不阻断。
2. 动作结果：
   - `choice=waived` 且 `entry.required` 为真、`entry.skip` 为空/假 →
     `pending_actions` 增加 `reason="waived_requires_skip_declaration"`；
   - `choice` 不在 `action_result` 域仍按现有 `pending_actions` 报；
   - 已存在的 `entry.result == "waived"` 不追溯重判（历史事实），只核本次决定。
3. 人判点：
   - 步骤级 `execution.human_points` 与动作级 `actions[].human_points` 合并消费（按 id 去重）；
   - 必须存在 `subject` 整词命中 id 且 `choice` 非空的决定；
   - 若声明有非空 `choices`，`choice` 必须精确命中其一；
   - 缺答复/选项不合法 → `missing_human_points`，条目带 `reason` 与 `accepted`。

**兼容**：旧任务（`execution.step` 存在、`stored_in` 缺失）不新增阻断；动作级人判点若旧记录
从未答复，会在下次 Check 报 `missing_human_points`，出口明确「请人回答」，属可执行迁移成本。
`test_step_contract` 的合成 plan 补 `consume_at`。

### F2 验收处置出口（I2）

**写者**：`projection.resolve`。

- 从 `task.plan.acceptance` 与 `task.check.acceptance_results` 建索引；两者都没有该 id →
  返回 problems（`acceptance id not found`），不写记录。
- `kind=narrow` 时：
  - `conclusion == "passed"` → 拒绝（无需收窄）；
  - `conclusion == "failed"` → 拒绝（失败是缺陷，不是不可验证；出口：修复后重检/异常归档）；
  - 其余（`unverified`/`not_run`/`pending`/缺失）→ 接受四要素记录。
- `kind=inspection`：只要求验收项存在、`evidence` 非空；仍可对 `failed` 记录人工核验证据，
  但不改变 Check。
- 记录形状不变（`unverified_resolutions`），不新增字段。

**出口**：`cmd_verify` 的 `next_` 与 `gates.final_gate` 的 `pending_required` exits 改为：

1. 按 `task-replan` 修改 PRD 验收口径（收窄/移出 required）→ 重新 `task-approve` → `task-check`；
2. 修复该项后重检；
3. 按设计稿 §5.6 异常归档。

`wf-finish` skill 的未核实段同步：`verify resolve` 只落档，不改变 Check；实质收窄走规划变更。

**不复制判定**：是否收窄、收窄哪些项仍由人/规划决定；机制只核 id 存在与记录四要素。

### F3 Check 发布与消费同条件（I3）

- `_parse_review_notes` 在 `conclusion == "pass"` 时要求 `basis` 非空；`fail/undecided`
  保持现状（不会产 pass）。
- `run_check_scope` 预解析 notes 并把 `internal_review`、`review_notes_digest` 放入 state；
  解析失败在锁内准备段抛 `WF_SEMANTIC_DECISION`，**不进入锁外执行**。
- `run_check_finish` 重读 notes 并比 digest；变化 → `WF_CHECK_STALE`（对象在锁外窗口被改）。
- 组装 `check` 后，若 `result == "pass"`，调用 `check.validate_check_result(task, check)`；
  有问题 → 抛 `WF_CHECK_FAILED`（facts 带 `problems`，exit 指向修 notes/验证记录后重跑），
  **不写一个会被 Finish 拒绝的 pass**。
- 单次验证运行 / TDD 证据路径不变。

### F4 实例暂停与释放 WIP（I4）

**消费者**：`cli._ensure_run_releasable`。

- 已有 `retained = wip_paths(task)` 检查保留；
- 新增：任务非终态时，`scope.classify_candidates(root, task, receipts=task_receipts(root))`，
  取 `e∪a` 桶 ∩ `uncommitted_paths(root)`（a 是本任务回执路径）；非空 → `WF_WORKSPACE_UNRESOLVED`，
  facts 列 `paths`、`task`、`registered_wip` 事实；exits：
  1. 保持写权、不释放，先在该任务处置这些路径（提交/反向修正/具名承接）；
  2. 处置后重跑 `writer release`；
  3. 需要对象交接用 `writer-handover`（不释放写权）。
- 分类/读取失败 fail-closed：不让「读不到工作区」变成「可以释放」。
- `run pause` 不新增 WIP 登记（只暂停、继续持有写权是合法用法）；本修复只防释放时丢事实。

### F5 收工空 subject 与 a 桶（I5）

**写者/消费者**：`tasks.stop_work`。

- 把 `touch/receipts/classified/pending` 的计算前移到空 subject 守卫之前（无副作用）。
- 空 subject 守卫改判 `pending`（`e ∩ 未提交`），不再看全局 `uncommitted_paths`；
  b 桶控制记录、a 桶回执路径不再误触。
- `keep`/`commit` 的归属核改为 `owned = set(e) | set(a)`：
  - a 桶是本任务回执路径（`task_receipts` 只含本任务），可提交/保留；
  - b/c/d 仍拒绝；`keep` 仍要求 `covered(path, approved_touch_paths)`。
- `reverse`/`transfer` 分支不变。
- 空 subject 的错误文案改为「本任务仍有未提交改动」并列出 `pending`。

### F6 表述/登记（I6–I8）

- `identity_store.maintain_roots` docstring、`cli._enforce_roots` 的 C2 exit、
  `cli._roots_registration_facts` warning：改为「启用入口是唯一登记通道；机制不核调用者身份，
  登记不构成人批准证明（§1.1）」。
- 设计稿 §1.3 的「仅人调启用入口可登记」改为同口径；机制稿 §1.4 若同句一并订正
  （只改表述，不改判定）。
- `tasks._commit_gate_problems` docstring：改为「任务提交入口（stop/abandon/archive）共用；
  实例记录组提交不在此列，其路径不含规则/删除」。
- `states.json`：
  - `check.from` 增 `{status: in_progress, phase: finish}`；
  - `finish-invalidate.action` 改为 `["baseline-apply", "spec-update"]`，notes 点明两者；
  - `next_by_position["in_progress/finish"]` 改为「门禁成立用 wf archive；C1 失效先 wf task-check」。
  - `protocol.py` 只要求 `action` 非空，数组合法。

## 5. 不变量与唯一判定

| 事实 | 唯一实现 | 本轮消费者 |
|---|---|---|
| 步骤契约生产 | `runs.step_contract` | `check.check_step_contract` |
| 动作结果派生 | `check.check_step_contract` → `apply_action_results` | `task-check` 门禁前 |
| Check 结构发布/消费 | `check.validate_check_result` | `run_check_finish` + `gates.check_structure` |
| 未核实处置 | `projection.resolve` / `required_unverified` | `verify resolve` + `final_gate` |
| 实例释放前置 | `cli._ensure_run_releasable` | `writer release` |
| 收工归属 | `tasks.stop_work` + `scope.classify_candidates` | `stop` |
| 迁移登记 | `protocol/states.json` | `protocol.py` 自检 + 入口回显 |

## 6. 迁移与兼容

- 旧实例契约无 `stored_in`：按 id 消费并报 legacy 事实，不阻断。
- 旧 `unverified_resolutions` 记录保留；新 `verify resolve` 只增不改。
- `states.json` 只增 `from` 项与 `action` 数组，schema 版本不变；`protocol.py` 兼容。
- Check notes 预解析：缺失/路径错在准备段失败，旧任务重跑 Check 时更早得到同一错误，
  不是新拒绝。
- `stop` 归属放宽只对 a∪e，不放宽 b/c/d；不放宽提交授权。
- `writer release` 对未登记 WIP 的拒绝是**新增拒绝**：只影响「暂停实例 + 当前任务有未提交
  业务改动」这一形态；出口是保持写权/处置/交接，不改变已登记 WIP 的既有行为。

## 7. 验收与断言设计

| 断言 | 位置 | 基线（红） | 修复后（绿） |
|---|---|---|---|
| A1 waived 需要有 skip 声明 | `test_step_contract` | `problems=[]` | `pending_actions` + reason |
| A2 人判选项必须命中 | 同上 | 接受 `maybe` | `missing_human_points` + accepted |
| A3 动作级人判未答 | 同上 | 接受 | `missing_human_points` |
| A4 `consume_at`/`stored_in` 失配 | 同上 | 接受 | `declared_verification_not_in_plan`（带 mismatch 事实） |
| A5 旧契约无 stored_in | 同上 | —（新断言） | 通过 + legacy 事实 |
| A6 `verify resolve` 未知 id | 新 `test_verify_resolve` | 接受 | 拒绝 |
| A7 `verify resolve` 对 failed 收窄 | 同上 | 接受 | 拒绝 |
| A8 notes 缺 basis 预检 | 新 `test_check_publish` | 接受 | 准备段拒绝 |
| A9 pass 结构复用 | 同上 | 可产 pass | `validate_check_result` 先拦 |
| A10 暂停实例未登记 WIP 释放 | 新 `test_run_release_wip` | 放行 | 拒绝并列路径 |
| A11 stop 空 subject 只有控制记录 | 扩展 `test_stop_ownership` | 拒绝 | 放行 |
| A12 stop a 桶 baseline 路径 | 同上 | foreign | keep/commit 接受 |
| A13 states 登记 | 新 `test_states_contract` | 缺项 | 通过 |
| A14 历史故障 H1–H7 | 现有 `test_terminal_release`/`test_step_contract`/源码 | 已绿 | 复核不回退 |

E2E：
- `f1_ordinary.py`（普通任务闭环，含 enable）与 `instance-task-phases`（实例内任务四阶段）
  必须保持绿；如受影响，先跑 `WF_SUITES="<name>" bash scripts/tests/wf_runtime/full/run_all.sh`。
- 隔离目标项目产品接续脚本（见 §8）。

## 8. 两种新会话验收

### 8.1 维护接续

- 产物：`prd.md`（范围/验收）、`design.md`（裁定/根因/修法）、`implement.md`（顺序/命令/
  回滚）、`verification-ledger.md`（候选身份、逐项证据、已跑命令与结果、未覆盖项、下一步）。
- 只读这些文件 + `git log`/`git diff` 应能重建：基线 HEAD、候选改动范围、每条根因的
  复现/反证、断言位置、未跑项与下一条可执行验证。
- 验证强度：当前会话内由同一主 agent 写入与重读；另用一次干净子代理只读任务产物与 Git
  复述状态（不共享当前上下文），记录其复述与产物的差异。若只做同会话重读，明标「弱验证」。

### 8.2 产品接续

隔离目标：`/tmp/wf-continuation-<random>/`（新目录，非真实 dogfood 项目）。

部署：`scripts/wf-dev-deploy.py --target <abs> --confirm`（源码候选；记录源树文件摘要/
manifest 身份）。发行 `install.py`、`wf upgrade` 预览/应用按「未跑（无新发行版本；版本推进
与发布需人授权）」记录，不冒充候选验证。

场景：
1. **同会话续用**：enable → task-new → PRD → approve → start → check → archive；
   断言写权随归档释放、`status` 到终态。
2. **旧对象终态后新会话**：同一目标再 `enable`（旧绑定终态）→ 出口 `enable --new-session`
   → task-new 第二对象 → 走完闭环；断言旧绑定保留、新对象与写权归属正确。
3. **暂停/交接接续**：普通任务 `stop --keep` 或有 WIP 的 task-pause + writer release；
   新会话 enable → `writer acquire`/`bind` → `task-resume` 核 WIP 指纹；断言下一条命令可执行。
   实例：`run pause` → 同会话保持写权；若有未提交 WIP，`writer release` 必须拒绝并给出口。
4. **无宿主标识**：用显式/自动模式下不提供宿主 id 的调用（或测试夹具的 `provider=wf`
   派生路径）走 enable → 绑定 → 推进；断言回显 `host_identity_present=false` 与受支持出口。

结果分栏记录：夹具模拟 / 真实宿主（DSH）/ 升级预览 / 实际升级。未跑项写原因与影响。

## 9. 回滚与风险

- 每个修复点独立、按文件分组；失败时可按 `git diff` 逐文件回退（保留用户未提交工作）。
- 新拒绝（release 未登记 WIP）可能挡住既有暂停实例的释放；出口「保持写权/处置/交接」
  已给出，不自动放行。
- 动作级人判点的新消费可能让旧实例任务下次 Check 需人回答；记录为迁移成本。
- 发布树不重建：源码候选与发行树 `0.0.22` 不一致，属已知边界；下次人工版本 bump 时重建。
## 10. 实现结果（2026-11-28）

### 10.1 落点

| 修复 | 实现位置 | 测试 |
|---|---|---|
| F1 步骤契约 | `runs.py::step_contract` 保留 `established_by/stored_in`；`check.py::check_step_contract` 核 plan 对齐、waived 的 skip 声明、动作级人判、选项命中 | `test_step_contract.py`（17 例） |
| F2 验收处置 | `projection.resolve` 核 id 存在与 failed/passed 收窄；`cmd_verify.next_` 与 `gates.final_gate` 出口改为重规划/重检/异常归档；wf-finish skill 同步 | `test_verify_resolve.py`（7 例） |
| F3 Check 发布 | `check._parse_review_notes` 要求 pass 带 basis；`run_check_scope` 预解析并带 digest；`run_check_finish` 比 digest + 复用 `validate_check_result` | `test_check_publish.py`（5 例） |
| F4 释放 WIP | `cli._ensure_run_releasable` 核 e∪a∩未提交；分类失败 fail-closed | `test_run_release_wip.py`（5 例） |
| F5 stop 归属 | `tasks.stop_work` 前移分类、空 subject 只看 e 桶、keep/commit 用 e∪a | `test_stop_ownership.py`（6 例） |
| F6 表述/登记 | `identity_store`/`cli` C2 口径；`_commit_gate_problems` docstring；`states.json` check.from/finish-invalidate/next | `test_states_contract.py`（3 例） |

### 10.2 验证

- 定向单测：`test_step_contract` 17、`test_verify_resolve` 7、`test_check_publish` 5、
  `test_run_release_wip` 5、`test_stop_ownership` 6、`test_states_contract` 3，
  以及 `test_terminal_release` 16、`test_check_lock_window` 3、`test_scope_d_bucket` 7、
  `test_workspace_exclusion` 11、`test_w3_session_identity` 26，全部通过。
- 全 `scripts/tests/wf_runtime/test_*.py` 循环：除 `test_template_cache.py` 直接执行的
  `NameError: run_template_cli`（该文件把 `unittest.main()` 放在辅助函数定义之前，属基线文件
  布局问题，不在本 diff）外，其余全部通过。
- 设计门禁：`validate-wf-design.py` 通过（4/4 输入摘要、定义/消费点 100%）；
  `check-doc-refs.py`、`wf-protocol-docs.py --check`、`validate-skills.sh`、
  `trellis-library/cli.py validate --strict-warnings` 均通过。
- 受影响 full runner：`WF_SUITES="f1_ordinary r7r15_tests r35r37_tests" ... --subset --serial`
  通过（`f1_ordinary` rc=0、`r35r37_tests` 15/15、`r7r15_tests` 38/38，`GATE-OK`）。
- 全量 runner：`bash scripts/tests/wf_runtime/full/run_all.sh --full --serial` 通过——
  59 套件 / 5 流程 / 93 repro 全绿，`fail=0`、`bad=0`、`GATE-OK`、`HYGIENE-OK`，
  run_id `1795874618914-3924681-7b88e5bb863b`（514s）。首次 92/93 的
  `uninstall-records-maintenance` 为运行期源码编辑导致的 `inputs changed before execution`，
  清理并冻结源码后重跑通过；两次运行之间只修正了 `projection.resolve` 的「plan 有项但
  Check 无结果」分支并补测试。
- 产品接续（`dev` 隔离目标 `/tmp/wf-product-probe-oOSfRm`）：同会话闭环、
  旧对象终态后 `enable --new-session` 绑定第二对象、`task-pause`→`writer release`→
  `stop --decision keep` 保留 `wip.txt`、无宿主标识按 anchor 派生且回显
  `host_identity_absent=true` 均通过；实例 `run pause` + WIP 由既有
  `repro/run-pause-and-advance` 与 `repro/instance-task-phases` 覆盖，未另建产品套件。

### 10.3 未覆盖 / 边界

- 未重建发行树（版本推进需人授权）；`payload/` 源码树与 `0.0.22` 发行树的差异只在源码。
  产品目标为 `dev` 部署，非正式发行；真实 DSH 宿主 dogfood 未跑，无宿主标识路径只验证了
  anchor 降级。
- 新增/修改的测试文件未重生成 `candidate-audit.json`（需发行批次与 tag 同批），
  台账已如实登记为未覆盖项。
- `test_template_cache.py` 的直接执行失败为基线文件布局问题，未在本任务修改；如需修复应
  单独立项（把 `unittest.main()` 移到文件末尾），不夹带进控制流修复。
