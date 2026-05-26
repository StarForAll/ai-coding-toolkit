---
name: delivery
description: 开发完成？准备交付 — 验收测试、交付物生成、变更日志、项目复盘。适用场景提示：准备交付、跑验收、整理交付物、项目收尾、上线、发布、部署
---

# /trellis:delivery — 项目测试、交付与沉淀

> **Workflow Position**: §6 → 前: `/trellis:project-audit` / `/trellis:check` / `/trellis:review-gate` → 后: 视当前项目是否存在项目级交付事件，决定是否还需要单任务级 Trellis 原生 `/trellis:finish-work` 收尾
> **Cross-CLI**: ✅ Claude Code（项目命令：`/trellis:delivery`） · ✅ OpenCode（TUI: `/trellis:delivery`；CLI: `trellis/delivery`；见 `opencode/README.md`） · ⚠️ Codex（通过 AGENTS.md NL 路由触发，不提供项目级 `/trellis:delivery` 命令；见 `codex/README.md`）

> **Strong Gate**: 本阶段受 [阶段状态机与强门禁协议](../阶段状态机与强门禁协议.md) 约束。`delivery` 是项目级/交付级验收与交付阶段，不等同于单任务级 `finish-work`。若当前轮还需要对**当前活动任务**做原生 Trellis 收尾，再进入 `/trellis:finish-work`。

补充边界：

- 当上游来自任务级 `check` 时，`delivery` 直接消费当前 active task 的 `check.md`
- 当上游来自任务级 `review-gate` 时，`delivery` 消费当前 active task 的 `check.md` 与最新 `review-gate/review-gate-round-<N>.md`
- 当上游来自项目级 `project-audit` 时，`delivery` 同时消费：
  - 当前 active task 的 `check.md`
  - 正式 `project-audit` 载体中的项目级总复核结论；若 `task_plan.md` 已声明独立 `PROJECT-AUDIT` task，则应以该 task 内的 `project-audit.md` 为准
- `delivery` 消费任务级 `check` 与项目级 `project-audit` 时，二者是**并列双门禁**，不是互相替代：
  - `check` 证明当前 active task 的任务级质量闭环
  - `project-audit` 证明项目整体代码面的项目级总复核闭环
- 因此，只要 `task_plan.md` 已把 `PROJECT-AUDIT` 写成正式终局任务，进入 `delivery` 前就必须同时满足这两类证据；不能把“formal PROJECT-AUDIT 已完成”误解成可跳过当前 active task 的 `check.md`
- 若 formal `PROJECT-AUDIT` 是独立 carrier task，则 `project-audit.md` 必须显式写出 `task_level_check_task`，用于绑定当前任务级 `check.md` 的真实 owner；不能只靠 parent/self 猜测
- 若 `project-audit.md` 标记本轮存在代码修改，则不得直接进入 `delivery`，必须先回到 `/trellis:check`

---

## When to Use (自然触发)

- "准备交付了"
- "跑一下验收测试"
- "整理一下交付物"
- "项目收尾"
- "生成 changelog"
- 已进入收尾链路后："做个项目复盘" / "复盘一下这次流程哪里别扭" / "把这次踩坑记录下来" / "这套工作流有几个地方得记一下"

> 若验收或交付阶段命中需求讨论，按 [需求变更管理执行卡](../需求变更管理执行卡.md) 分流：纯澄清留在当前阶段；新增 / 修改 / 删除进入变更管理，不直接混入本轮交付。

---

## 流程

### Step 1: 自动化测试

**MCP 能力路由**

| 场景 | 调用能力 | 触发条件 | 说明 |
|------|---------|---------|------|
| 项目依赖/版本确认 | `Context7` | 当需要查询框架或依赖官方文档、版本信息时 | 获取最新框架文档。若无法获取，标记 `[Evidence Gap]`，仅引用项目内已有版本与用法证据 |
| 依赖安全漏洞检查 | `exa_web_search_exa` | 当存在依赖升级或上线前风险确认需求时 | 搜索已知漏洞信息 |

**调用 Skill**：`verification-before-completion` — 汇总测试、类型检查和 lint 证据。降级：手动记录实际命令、输出摘要与结论。

```bash
<user-confirmed verification commands for current project>
```

这里执行的必须是目标项目在技术架构确认后已由用户明确的真实验证命令，不在本阶段猜默认包管理器或默认脚本名。

### Step 2: 可用性与性能验证

按 PRD 验收标准逐项检查

### Step 3: 验收门禁

- [ ] 核心场景 100% 通过
- [ ] P0/P1 缺陷为 0
- [ ] 安全扫描无高危

<!-- if:outsourcing -->
### Step 4: 外部项目交付控制门禁（如适用）

> **📋 前置依赖**
>
> 本项目应已在 `/trellis:feasibility` 阶段完成项目类别判断；若判定为外部项目，还应已确定启动款门禁与交付控制轨道，并在 `/trellis:plan` 阶段将开工授权与移交任务拆分为独立任务。
> 若外部项目的 `assessment.md` 中缺少 `project_engagement_type`、`kickoff_payment_*`、`delivery_control_track` 或 `delivery_control_handover_trigger` 字段，请先回到 `/trellis:feasibility` 补齐基线。

若项目属于外包、定制开发或新客户项目，进入正式交付前先检查 `assessment.md` / 合同中约定的交付控制轨道。外包控制字段由 `workflow-state.py validate` 校验；交付专属门禁由 `delivery-control-validate.py` 校验。

- **首选轨：托管部署**
  - 尾款未到账：只交付演示地址、试运行环境访问、验收材料、用户手册、运维说明
  - 尾款未到账：不交付源码仓库权限、生产环境密钥、管理员账号、最终部署权限
  - 每次交付事件都要明确：本次是”继续由开发者保留控制权”还是”进入最终控制权移交”
- **备选轨：试运行授权**
  - 必须已明确披露：授权有效期、续期方式、到期行为、永久授权触发条件
  - 到期行为应限制为”演示模式”或”只读模式”，不得破坏已有数据
  - 尾款未到账：不交付永久授权、不交付完整源码与最终控制权

禁止项：

- 未披露的授权失效机制
- 远程关停、隐藏后门、不可恢复锁定
- 用不可解码文件伪装源码交付

**双轨交付控制验证**：

```bash
python3 <WORKFLOW_DIR>/commands/shell/delivery-control-validate.py --phase delivery --task-dir <task-dir>
```

此验证覆盖 `assessment.md` 双轨字段完整性、`task_plan.md` 中的交付控制 task 图摘要结构、以及 `delivery/` 交付事件文档。若验证失败，不得进入正式交付。
此处的 `task_plan.md` 仅作为交付控制 task 图摘要；真实执行完成情况仍以对应 Trellis task 为准。
<!-- endif:outsourcing -->

### Step 4.5: 源码水印与归属证明门禁（如适用）

若 `assessment.md` 中 `ownership_proof_required = yes`，进入正式交付前还必须确认：

- `$TASK_DIR/design/source-watermark-plan.md` 已冻结
- 可见源码水印已落地
- 零宽字符水印（若启用）已按”仅注释 / 文档字符串 / Markdown”边界落地
- 不起眼代码标识（若启用）已落地且未污染业务关键逻辑
- 若设计中声明了 `Protected Watermark Snippets`，这些受保护片段在当前源码中仍然存在；若先前发生可恢复漂移，已通过自动修复或人工修复恢复
- `ownership-proof.md` 与 `source-watermark-verification.md` 已生成

按当前 workflow 口径：

- `visible` 通道是启用归属证明门禁时的最低要求
- `zero-width` / `subtle-markers` / `zero-watermark` 是否必须验证，以 `source_watermark_channels` 的实际声明为准
- `basic` / `hybrid` / `forensic` 本身不会直接切换 validator 代码路径；当前 workflow 仍按 `source_watermark_channels` 的实际声明决定本阶段要验证哪些通道

验证命令：

```bash
python3 <WORKFLOW_DIR>/commands/shell/ownership-proof-validate.py --phase delivery --task-dir <task-dir>
python3 <WORKFLOW_DIR>/commands/shell/source-watermark-guard.py --task-dir <task-dir> --mode check
```

若需要一次性检查冻结字段、设计计划、任务拆分和交付证明，可执行：

```bash
python3 <WORKFLOW_DIR>/commands/shell/ownership-proof-validate.py --all --task-dir <task-dir>
```

若 guard 发现的是已声明为可自动恢复的低风险片段漂移，可先执行：

```bash
python3 <WORKFLOW_DIR>/commands/shell/source-watermark-guard.py --task-dir <task-dir> --mode repair
python3 <WORKFLOW_DIR>/commands/shell/source-watermark-guard.py --task-dir <task-dir> --mode check
```

设计边界、术语与证据链口径以 [源码水印与归属证据链执行卡](../源码水印与归属证据链执行卡.md) 为准。

失败时不允许进入正式交付，也不应把”已交付源码 / 已完成归属证明”写入交付清单。

### Step 5: 交付物生成

**调用 Skill**：`doc-coauthoring` — 协同撰写交付文档。降级：手动按”客户交付物 / 开发交付物 / 验收证据”三段结构整理。

客户交付物：代码 + PRD + 用户手册 + 运维文档
开发交付物：代码 + 技术文档 + 评估集

面向用户或非技术读者的文档，默认增加一条文字收口要求：

- 对目标项目 `docs/` 目录下的**非技术性文档**，初稿完成后默认执行一次 `humanizer-zh`
- 正式交付前，再执行一次 `humanizer-zh`
- 项目整体完成后，对仍需交给人阅读的非技术性文档再复核一次
- 若用户明确要求某个额外文件做人性化处理，即使它不在默认范围内，也应执行 `humanizer-zh`

默认不强制纳入 `humanizer-zh` 的文件：

- `docs/requirements/developer-facing-prd.md`
- `delivery/transfer-checklist.md`
- `delivery/retrospective.md`

最小交付文档契约：

- `delivery/acceptance.md`
  - 验收标准逐条状态
  - Blocking Findings
  - Acceptance Gate
  - 当前交付状态
  - `delivery_gate_status`
- `delivery/deliverables.md`
  - Closeout Assets
  - Verification Evidence
  - Current Status
  - Residual Risks
- `delivery/transfer-checklist.md`
  - 当前事件允许移交什么
  - 当前事件禁止标记为已移交什么
  - 触发条件 / 付款 / 权限 / 证明材料是否齐备
  - `milestone_payment_schedule` / `non_payment_remedy_path` / `dispute_escalation_path` 是否与 `assessment.md`、`task_plan.md` 对齐
- `delivery/retrospective.md`
  - 本轮验收、返工、摩擦点，以及需要人工说明的缺陷或待优化点

<!-- if:outsourcing -->
### Step 6: 交付事件 checklist（如适用）

对外部项目，每次正式交付事件都应执行 `transfer-checklist`；若事件属于”最终控制权移交”，则必须在开发者明确确认尾款到账后再完成所有最终移交项：

交付事件判定可先按下面速查：

| 当前事件 | 是否允许移交源码/永久授权/生产控制权 | 必须额外确认 |
|---|---|---|
| retained-control delivery | 否 | 交付材料中必须写清哪些控制权仍由开发者保留 |
| final control transfer | 是 | `delivery_control_handover_trigger` 已满足，通常为 `final_payment_received` |

每次交付事件都应额外核对：

- `milestone_payment_schedule` 是否已达到当前事件允许的付款里程碑
- `non_payment_remedy_path` 是否已在交付材料中明确
- `dispute_escalation_path` 是否已在验收/付款争议场景中明确

### 交付事件执行门禁表

| 交付事件 | 允许交付的内容 | 不得标记为已完成的内容 | 必须附带的证据/说明 |
|---|---|---|---|
| retained-control delivery | 演示地址、试运行环境访问、验收材料、用户手册、运维说明 | 源码仓库权限、永久授权、生产密钥、管理员账号、最终部署权限 | 当前保留控制范围、当前事件类型、后续最终移交触发条件、`milestone_payment_schedule`、`non_payment_remedy_path`、`dispute_escalation_path` |
| trial delivery under authorization | 试运行包、授权文件、限制说明、到期行为说明、验收材料 | 永久授权、完整源码、最终控制权 | `trial_authorization_terms.*`、到期行为验证、永久授权触发条件、`milestone_payment_schedule`、`non_payment_remedy_path`、`dispute_escalation_path` |
| final control transfer | 源码、永久授权、构建/部署材料、密钥/配置、平台管理员权限、最终交接记录 | 无，但必须与 `transfer-checklist` 一致 | 尾款到账或其他触发条件证据、完整交接记录、回滚说明、`milestone_payment_schedule`、`non_payment_remedy_path`、`dispute_escalation_path` |

- [ ] 源码仓库权限或源码包
- [ ] 永久授权文件，或移除试运行限制的正式版本
- [ ] 构建脚本、部署脚本、CI/CD 配置
- [ ] 生产环境变量、密钥、证书、第三方平台配置
- [ ] 服务器、域名、数据库、对象存储等管理员权限
- [ ] 最终运维文档、回滚说明、交接记录

若尾款尚未到账，上述条目不得在交付清单中标记为”已完成移交”。
<!-- endif:outsourcing -->

### Step 7: 变更日志

**可选 Skill**：`doc-coauthoring` — 协助把变更日志整理成对外可读版本。当前 workflow 不依赖专用 changelog skill；默认做法是基于实际提交记录，按功能、修复、风险、迁移说明四类手动整理。

### Step 8: 代码审查

**优先 Skill**：`verification-before-completion` — 先收口当前 CLI 的验证证据与剩余风险。  
**如需额外外部审查**：使用 `multi-cli-review` 发起 reviewer 审查，并在报告返回后用 `multi-cli-review-action` 汇总、确认与执行低回归修复。降级：手动列出审查范围、验证证据和剩余风险。

### Step 9: 项目复盘

本步骤只保留当前项目的复盘与人工说明，不再要求单独的 workflow 缺陷反馈机制闭环。

### Step 10: 写入等待确认状态

当 `delivery/*` 交付产物、`finish-work-checklist.md` 与本轮验收结论都已经完成后，必须显式写入等待确认状态：

```bash
python3 <WORKFLOW_DIR>/commands/shell/workflow-state.py set <task-dir> \
  --stage-status awaiting_user_confirmation \
  --awaiting-user-confirmation true
```

只有在用户明确确认后，才允许把当前轮视为项目级主链完成，并决定是否继续进入原生 `/trellis:finish-work`。

`retrospective.md` 重点记录：

- 功能验收结果
- 返工与摩擦点
- 哪些地方仍需要人工补充说明

若本次真实执行暴露出**workflow 本身**的缺陷或待优化点，人工手动说明即可；当前 workflow 不再要求：

- AI 先在 `tmp/` 目录起草 `workflow-feedback-*.md`
- 再移动到 `learn/`
- 再按固定交接闭环回流

换句话说：

- 项目问题，继续写在 `retrospective.md`
- workflow 问题，人工手动说明缺陷和待优化点即可

### Step 10: 收尾记录校验

进入最终 close-out 前，先确认：

- 已完成内容已由人工测试并提交
- 当前 workflow 里，`delivery` 与 Trellis 原生 `/finish-work` 是**不同层级**的动作：
  - `delivery` 负责项目级/交付级验收与交付物
  - Trellis 原生 `/finish-work` 负责**当前活动任务**的单任务收尾冻结，并执行 `task.py archive` + `add_session.py`
  - 不要把 `delivery` 写成“原生 `finish-work` 的定义组成部分”，也不要把原生 `finish-work` 改写成项目级交付阶段
- 当前执行任务已完成，且本轮收尾只围绕**当前任务**
- 未完成任务不要误归档；非当前任务不要借本轮收尾顺手自动提交
- 不为了补齐新规则或整理台账而批量回写旧任务、旧会话记录或已归档目录
- staged 区不得混入非目标变更；若存在 staged 污染，必须先中断处理

若当前轮还需要关闭当前活动任务，则 `archive` 与 session 记录在 Trellis 原生 `/finish-work` 中完成，不在 `delivery` 阶段执行。具体操作步骤参见 `Trellis 原生 /finish-work.md`。

判定规则：

- 在 `Trellis 原生 /finish-work` 阶段：`archive` 与 `add_session.py` 都返回 0 则会话记录与元数据闭环完成
- 任一步返回非 0：close-out 不算完成，先处理 Trellis 基线写入失败原因
- `git status --short .trellis/workspace .trellis/tasks` 输出应为空

---

## 输出

```
$TASK_DIR/
├── finish-work-checklist.md
└── delivery/
    ├── acceptance.md
    ├── deliverables.md
    ├── transfer-checklist.md
    ├── ownership-proof.md
    ├── source-watermark-verification.md
    └── retrospective.md
```

最小内容要求：

- `finish-work-checklist.md`
  - 冻结验证矩阵
  - 人工验证状态
  - spec / 文档同步结论
  - child-task parent record sync（如适用）
  - `finish_work_gate_status`
- `delivery/acceptance.md`
  - `Acceptance Criteria Status`
  - `Blocking Findings`
  - `Acceptance Gate`
  - `当前交付状态`
  - `delivery_gate_status`
- `delivery/deliverables.md`
  - `Closeout Assets`
  - `Verification Evidence`
  - `Current Status`
  - `Residual Risks`
- `delivery/transfer-checklist.md`
  - 对外项目：必填
  - 内部项目：若无真实移交事件，可标注 `not applicable`
- `delivery/retrospective.md`
  - 本轮验收
  - 返工
  - 摩擦点
- 这些文件都必须如实记录实际状态；没有证据时写 `not run` / `not applicable`，不要伪造通过

## 下一步推荐

**当前状态**: 验收测试完成，交付物已生成；在用户明确确认前，仍停留在 delivery 阶段。

> 本节定义的是阶段完成后的推荐输出口径，用于帮助当前 CLI 或协作者说明下一步；它不是框架层自动跳转保证。

根据验收结果：

| 验收结果 | Claude / OpenCode 推荐入口 | Codex 推荐入口 | 说明 |
|---------|---------------------------|----------------|------|
| 全部通过，且当前活动任务也准备关闭 | `/finish-work` | 进入会话收尾，或显式触发 `Trellis 原生 /finish-work` skill | **默认推荐**。前提：如果当前轮需要收尾当前活动任务，再进入 Trellis 原生 `finish-work`；它按 Trellis 原生顺序先 archive，再通过 `add_session.py` 完成记录与元数据闭环 |
| 有 P0/P1 缺陷 | 描述排障意图，或显式触发 `trellis-break-loop` skill | 进入深度排障，或显式触发 `trellis-break-loop` skill | 深度分析 Bug 根因 |
| 有 P2/P3 缺陷 | `/trellis:continue` | 回到实施阶段，或显式触发 `trellis-continue` skill | 回到实施阶段修复 |
| 验收中出现冻结后新增 / 修改 / 删除需求 | [需求变更管理执行卡](../../需求变更管理执行卡.md) | 同上 | 先完成变更评估与确认；不要直接混入当前交付 |
| 需要更新规范文档 | 描述规范更新意图，或显式触发 `trellis-update-spec` skill | 记录并更新规范，或显式触发 `trellis-update-spec` skill | 沉淀新发现的模式到 spec |
| 需要请求代码审查 | `multi-cli-review` / `multi-cli-review-action` 能力 | `multi-cli-review` / `multi-cli-review-action` skill | 提交前外部审查与报告汇总 |
| 需要归档任务 | `python3 ./.trellis/scripts/task.py archive <name>` | 同左 | 归档在 `/finish-work` 阶段执行，不在 `delivery` 阶段单独执行 |
| 不确定下一步 | `/trellis:delivery` | 描述当前交付/收尾意图，或显式触发 `delivery` skill | 先判断现在需要的是项目级交付动作，还是当前活动任务的单任务 finish-work 收尾 |
