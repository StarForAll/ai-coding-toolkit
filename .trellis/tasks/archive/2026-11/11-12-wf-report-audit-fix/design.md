# 技术设计：wf 控制流结构性修正

本设计只覆盖 PRD 中裁定为"采纳/部分采纳"的条目。每节写：要消除的失败模式、机制契约、落点、失效与兼容、验证。
编号 D1–D12 与 PRD 表一一对应；D13/D14 是文档与发行物。

## 0. 总体原则

1. **单一事实源**：同一判定只保留一处实现（运行态写入、报告输入校验、交付集合、脱敏口径），其他位置只消费。
2. **摘要绑定**：任何"人已确认/已排除/已授权"的事实都绑定可核对摘要（内容、提交、锚点、范围），内容变化即失效，不做永久豁免。
3. **失效可见**：新增的放行都不产生 pass，只解除特定阻断；不能核实的部分按设计稿 §1.5 输出三档之一。
4. **不新增定义体**：设计稿只做澄清与场景行；机制/字段/域登记放在机制稿与实现稿。

## D1 会话运行态：唯一合并写入口（A2）

- 失败模式：侧车同时承载"对象定位/游标"与"写权代次"，5 处调用用整份替换，后写者抹掉先写者的字段；`run advance`、`bind`、`task.create` 后 `resolve_generation` 取不到代次。
- 契约：侧车只有**合并写**一种写入口。`session.update_runtime(root,key,**fields)` 是唯一公开写入 API；整份替换下沉为 `_replace_runtime`（仅 `update_runtime` 内部使用，且只在读取失败时用于建新记录）。
- 落点：`session.py`；`runs.py:1205/1674`、`tasks.py:1490`、`cli.py:1216/1349` 改为 `update_runtime`；`runs.py:2038` 已用合并，保留。
- 失效/兼容：旧侧车缺 `writer_generation` 时行为不变（仍是"缺代次"出口）；不迁移、不猜值。
- 防回归：加结构测试——扫描 `wflib/` 源码，`write_runtime(` 只允许出现在 `session.py`（其他模块出现即失败）。

## D2 审查覆盖：`uncovered` 不推导通过（A3）

- 失败模式：五轴全 `uncovered` 仍 `pass`；"没有发现缺陷"被当成"完成必要审查"；注释引用的 §4.8/§4.9 不存在。
- 契约（写进设计稿 §6.5 与机制稿 §9.2）：
  - `uncovered` 不是缺陷，也不构成审查通过；**全部轴未覆盖** = 输入不成立，`review-decide` 拒绝、不写 verdict。
  - 部分轴未覆盖：需人接受覆盖缺口（`judgments` 追加 `{kind:"缺口", waived_by:"human:<来源>", …}` + `--attestation`）后才产生判定；接受记录按 `round` 与轴名绑定；缺口进 `facts.coverage_gaps` 与 `status` 事实面。
  - 有 blocking finding 仍 fail；覆盖缺口不改变 fail。
- 落点：`review.py` 新增 `coverage_state(axes)`、`coverage_acceptance(task, round_no)`；`decide` 在输入成立后、写 verdict 前消费；`derive_verdict` 保持"只按已覆盖轴给 pass/fail"；删除 §4.8/4.9 悬空引用。
- 兼容：旧记录里已写 `verdict=pass` 且轴全未覆盖的，门禁不追溯改写；只在 `status`/`repair_scope` 的 gaps 事实里如实列出（不静默）。
- 验证：全未覆盖→`WF_REVIEW_INVALID`；部分未覆盖无接受→`WF_SEMANTIC_DECISION`（带轴名与两条出口）；有接受→pass，facts 带缺口；有 blocking→仍 fail。

## D3 外来未提交改动：摘要绑定的排除留痕（A4/B1）

- 失败模式：c 桶（未归属未提交）在开工与 Check 无条件阻断，只有**已提交**外部变更才有"已核对无影响"的人判出口，dogfood 中 `.unipi/`、`.gitignore` 两次逼停。
- 契约：
  - 新增 Decision 域 `workspace_exclusion`（规范值 `排除外来改动`）。决定文件形状：`{choice, paths:[{path, digest}], reason, by?, at?}`；`path` 必须当前在 c 桶，`digest` 必须等于当前内容指纹。
  - 记录载体：`task.execution.workspace_exclusions`（追加，`{path, digest, reason, decision_digest, at}`）；同 path+digest 重入幂等。
  - 消费点：`task-start`（ordinary）与 `task-check` 的 c 桶判定；被排除路径进入新的 `x` 桶事实（不并入 e/f，不改变交付、指纹、材料、提交面）。
  - 失效：任一被排除路径内容变化 → 排除失效、c 桶重现；`run_check_finish` 的重分类比对把这种变化报成 `WF_CHECK_STALE`。排除**不**解除换对象/实例下一任务/升级的工作区边界（设计稿 §4.2 原约束不变），也**不**构成提交授权。
  - 输出：`WF_WORKSPACE_UNRESOLVED` 的 facts 增 `excluded` 与两条出口（记录排除 / 实际处置）。
- 落点：`decisions.py`（域）、`scope.py`（`exclusion_entries/apply_exclusions`）、`tasks.py`（start + 记录写入）、`check.py`（scope/finish）、`judgments.py`（骨架事实）。
- 文档：设计稿 §4.2 增一句澄清 + §8.2 增一行二值场景；机制稿 §3.5 增 x 桶与失效规则，§12.2 新增场景映射；实现稿 §2.3 域表 9→10。

## D4 授权范围绑定（A6）

- 失败模式：`review-launch` 只核 `authorization-export.json` 存在；`archive` 的 `repo_rules` 只核类别。
- 契约：
  - 外发授权必须声明并核对 **task id + 材料类集合（`diff/requirement/test_results` 子集）+ 暂存根**；`launch` 计算本次集合，缺项/超集/换任务即 `WF_COMMIT_NOT_AUTHORIZED`（给"补一条 export 确认"与"改为同机只读审阅"两条出口）。同一 task、同类材料、同暂存根的新轮次可复用（符合设计稿 §4.1"同范围授权持续有效"）。
  - 仓库规则提交：`repo_rules` 授权改为与 `delete` 同口径的路径覆盖核对（`authorize.covers`），未覆盖的路径逐个列出。
- 落点：`authorize.py`（`export_scope`/`export_scope_problems`）、`review.py::launch`、`tasks.py` 提交守卫。
- 兼容：旧授权无 `materials` 字段 → 视为"只覆盖当时未细分的类别"→ 需要补一条（给明确出口，不静默放行）。
- 不可观测面：reviewer 侧最终由哪个 CLI 读取属事后事实，按设计稿 §6.5 的"过程约束 + 事后核对"声明边界，不假装机制能拦截。

## D5 脱敏：协议驱动的保留白名单（A7）

- 失败模式：`redact()` 按顶层键黑名单；`quote`、嵌套字典、未知字段的敏感文本原样进 committed。
- 契约：保留项取自 `protocol/redaction.json` 的 `effect=keep` 条目（语义标签 → 字段映射在代码中显式登记）；其余一律丢弃并记 `<omitted>`；所有保留字符串过 `redact_text` 遮罩，`quote` 另截断到 500 字符并记 `quote_digest`；嵌套结构不再原样保留子键，只保留白名单标量。
- 落点：`authorize.py::redact`；`protocol/redaction.json` 不新增规则（只按既有标签落实现）。
- 验证：嵌套 `{"token": ...}`、`quote` 带 Bearer、未知键 `notes` 带明文路径/口令 → committed 副本无原文；`original_digest` 仍按原文计算。

## D6 报告输入校验单源（A8）

- 失败模式：lint 只核字段存在，导入/判定另核非空、敏感面、状态头；lint 通过 → 导入成功 → 判定失败 → 另开一轮。
- 契约：新增 `review.report_input_problems(payload, task=None)`，覆盖：必需字段、`read-scope`/`excluded-scope` 非空、敏感面覆盖、`axes` 结构与 conclusions、申报 verdict 与推导一致、状态头存在且 `status=done`。`lint`、`import`（字段与状态头）、`decide`/`review_report_problems`（除锚点与文件摘要外的输入面）都调用它；不再各写一套。
- 落点：`review.py`；`lint_report` 增 `status-head` 检查（只看前 400 字符，与 `read_agent_status` 同源）。
- 兼容：`lint --task` 可继续跳过批准集合核对（输出 skipped）；不改变 decide 的锚点/人数判定。
- 验证：空 `read-scope`、缺敏感面、状态头缺失、状态非 done 四类在 lint 与 import 处同结论。

## D7 材料差异源 = 任务基线（A9/B6）

- 失败模式：已跟踪路径只比 `HEAD`，任务中途提交后材料变成"no textual change (metadata-only?)"；已提交删除只留标注。
- 契约：`materialize_delivery(root, paths, base=None)`；`base` 取 `task.baseline_head`，回退 `HEAD` 仅当基线不可用并在 `problems` 里如实报（不静默）；已跟踪路径用 `git diff <base> -- <path>`（含已提交与未提交，删除给出删除 hunk）；未跟踪仍 `--no-index`。`status.json` 增 `diff_base`。
- 落点：`review.py::materialize_delivery` / `write_materials`。
- 兼容：基线不可达时输出 `[wf-material-missing]` + 原因；不改变材料集合与指纹。
- 验证：中途提交一处修改 + 一处删除 + 一处新增未跟踪，三者都出现在 `diff.patch`。

## D8 验证日志完整落盘（B5）

- 失败模式：日志只写最后一行 summary，复核只能靠人保留终端。
- 契约：日志写 `argv(遮罩)/cwd/exit_code` + 完整遮罩输出；超过上限时保留头尾并写 `[wf-log-truncated kept=<n> dropped=<n> total=<n>]`；上限为机制常量（头 64 KiB、尾 192 KiB），不引入项目配置键。记录内保留 `summary`、`log_digest`、`log_bytes`、`truncated`。
- 落点：`check.py::_run_argv`。
- 验证：输出 1 MiB → 日志有头尾与截断标记；记录无全文；遮罩规则仍生效。

## D9 锚点纳入实例定义快照（B4 实质项）

- 失败模式：`workflow_snapshot_digest` 恒 `None`；属于实例的任务，其定义快照变化不影响旧 Check。
- 契约：任务带 `run_id` 时，`anchor_parts.workflow_snapshot_digest = H("wf-workflow-snapshot-v1", {run, definition_digest, snapshot_digest})`；快照缺失/不可读 → `WF_RECORD_INVALID`（不静默为 None）。无 `run_id` 的任务保持 `None`（可选项身份不变）。
- 落点：`check.py::anchor_parts`；`fingerprint.check_anchor` 已含该键，不新增哈希域。
- 兼容：老实例任务的旧锚点会失配（需重跑 Check），这是"规则输入变化"的应有结果；在 facts 里指出差异键。
- 拒绝部分：报告"重装会覆盖就地修改的 `.wf/lib`"不成立——`install.py`/`wf-dev-deploy.py` 对内容不同的既有文件整批 `WF_ASSET_DECISION`，零写入；不为此新增机制。

## D10 `review-launch` 请求机械化（B3）

- 失败模式：`submitted_scope`/`readable_scope`/`exclusions` 由模型手写，易漏项且与事实脱节。
- 契约：`review-launch --task <id> --implementation-cli <cli>` 即可发起；入口按当前对象生成：
  - `submitted_scope.diff` ← 交付集合（D7 的基线差异摘要）；
  - `submitted_scope.requirement` ← 任务 PRD 路径与摘要；
  - `submitted_scope.test_results` ← 当前 Check 的验证条目摘要；
  - `readable_scope` ← 批准触碰面内的业务路径 + 相关 spec + PRD；
  - `exclusions` ← 四类敏感面 + 项目外 + 其他任务目录。
  `--request <path>` 仍接受，用于覆盖/补充；无论来源，都过 D4 的范围绑定与 D6 的最小材料检查。`export_decision` 改为可省略，缺省用已入库授权摘要。
- 落点：`review.py::launch` + `resolve_launch_request`。
- 验证：无 request 文件时可发起，记录内三类材料齐全、exclusions 覆盖四类；手写 request 缺一类时仍拒绝。

## D11 skill 口径（A1/B2/B9）

- `wf-review-action`：去掉"不改源码"的绝对口径，改成"本步只写报告与处置；fail 后的范围内修复、重跑 Check、重发下一轮由主会话承接"，并给收敛判据与指针（`wf-repair-loop`、`wf-continue`），保留"不改 reviewer 报告/不代判"。
- `wf-start`：新增"启用无法建立时"段：宿主拒绝写 `.wf/`、身份不可核实、`enable` 报错时，**报告未启用事实 + 出口**（解除写限制 / 换宿主或会话 / 由人明确选择按普通开发继续），并明确此时不得把结果称作 wf 流程产物。不提供"先写码后补流程"通道（与设计稿 §4.2 冲突，PRD 已拒绝）。
- `task-start` 版本失配：错误 facts 增 `exits`——若只是排版/说明变化，写 `choice=机械修订` 的决定文件后重跑 `task-approve`（与 `_mechanical_revision` 同源）。

## D12 文档与发行物（B8/D13）

- 设计稿：§4.2 澄清句、§6.5 覆盖规则句、§8.2 两行（二值 + 三档）。
- 机制稿：§0.1 变更说明与输入摘要同步；§3.2 锚点、§3.5 排除桶、§4.1 日志预算、§9.1 材料与发起、§9.2 覆盖判定、§12.2/§12.3 映射。
- 实现稿：§2.3 决策域 9→10。
- `docs/workflows/wf-variant.md`：首行加历史标注（旧版文档族，独立框架已取代），不改正文语义。
- 发行树：源树变更后按 `scripts/build-wf-release.py --version 0.1.1` 重建；`wf-v0.1.0` 已存在，同版改内容属身份冲突，故递增。

## 回滚与风险

- 每项独立成 commit 级批次（代码+测试同批），失败只回退该批次；文档与发行树最后一批。
- 最大风险点：D3（新增放行）与 D2（新增拒绝）。D3 用摘要绑定 + 只解除 Check/开工阻断 + 不改变交付与提交面把风险限制在"看得见的共存"；D2 只增加"未覆盖不能算通过"，不放宽任何既有拒绝。
- 兼容风险：D9 使老实例任务锚点失配 → 需重跑 Check，属规则输入变化；在 facts 明示。
