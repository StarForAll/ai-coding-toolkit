---
name: delivery
description: 开发完成？准备交付 — 验收测试、交付物生成、变更日志、经验沉淀。触发词：准备交付、跑验收、整理交付物、项目收尾、上线、发布、部署
---

# /trellis:delivery — 项目测试、交付与沉淀

> **Workflow Position**: §6+§7 → 前: `/trellis:finish-work` → 后: `/trellis:record-session`
> **Cross-CLI**: ✅ Claude Code（项目命令：`/trellis:delivery`） · ✅ OpenCode（TUI: `/trellis:delivery`；CLI: `trellis/delivery`；见 `opencode/README.md`） · ⚠️ Codex（通过 AGENTS.md NL 路由触发，不提供项目级 `/trellis:delivery` 命令；见 `codex/README.md`）

> **Strong Gate**: 本阶段受 [阶段状态机与强门禁协议](../阶段状态机与强门禁协议.md) 约束。delivery 完成后，必须等待用户明确确认，不能自动进入 `record-session`。

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
| 依赖安全漏洞检查 | `exa_search` | 当存在依赖升级或上线前风险确认需求时 | 搜索已知漏洞信息 |

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

### Step 4: 外部项目交付控制门禁（如适用）

> **📋 前置依赖**
>
> 本项目应已在 `/trellis:feasibility` 阶段确定交付控制轨道，在 `/trellis:plan` 阶段已将移交任务拆分为独立任务。
> 若 `assessment.md` 中缺少 `delivery_control_track` 或 `delivery_control_handover_trigger` 字段，请先回到 `/trellis:feasibility` 补齐基线。

若项目属于外包、定制开发或新客户项目，进入正式交付前先检查 `assessment.md` / 合同中约定的交付控制轨道：

- **首选轨：托管部署**
  - 尾款未到账：只交付演示地址、试运行环境访问、验收材料、用户手册、运维说明
  - 尾款未到账：不交付源码仓库权限、生产环境密钥、管理员账号、最终部署权限
  - 每次交付事件都要明确：本次是“继续由开发者保留控制权”还是“进入最终控制权移交”
- **备选轨：试运行授权**
  - 必须已明确披露：授权有效期、续期方式、到期行为、永久授权触发条件
  - 到期行为应限制为“演示模式”或“只读模式”，不得破坏已有数据
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

### Step 4.5: 源码水印与归属证明门禁（如适用）

若 `assessment.md` 中 `ownership_proof_required = yes`，进入正式交付前还必须确认：

- `$TASK_DIR/design/source-watermark-plan.md` 已冻结
- 可见源码水印已落地
- 零宽字符水印（若启用）已按“仅注释 / 文档字符串 / Markdown”边界落地
- 不起眼代码标识（若启用）已落地且未污染业务关键逻辑
- `ownership-proof.md` 与 `source-watermark-verification.md` 已生成

按当前 workflow 口径：

- `visible` 通道是启用归属证明门禁时的最低要求
- `zero-width` / `subtle-markers` / `zero-watermark` 是否必须验证，以 `source_watermark_channels` 的实际声明为准
- `basic` / `hybrid` / `forensic` 本身不会直接切换 validator 代码路径；当前 workflow 仍按 `source_watermark_channels` 的实际声明决定本阶段要验证哪些通道

验证命令：

```bash
python3 <WORKFLOW_DIR>/commands/shell/ownership-proof-validate.py --phase delivery --task-dir <task-dir>
```

若需要一次性检查冻结字段、设计计划、任务拆分和交付证明，可执行：

```bash
python3 <WORKFLOW_DIR>/commands/shell/ownership-proof-validate.py --all --task-dir <task-dir>
```

失败时不允许进入正式交付，也不应把“已交付源码 / 已完成归属证明”写入交付清单。

### Step 5: 交付物生成

**调用 Skill**：`doc-coauthoring` — 协同撰写交付文档。降级：手动按“客户交付物 / 开发交付物 / 验收证据”三段结构整理。

客户交付物：代码 + PRD + 用户手册 + 运维文档
开发交付物：代码 + 技术文档 + 评估集

### Step 6: 交付事件 checklist（如适用）

对外部项目，每次正式交付事件都应执行 `transfer-checklist`；若事件属于“最终控制权移交”，则必须在开发者明确确认尾款到账后再完成所有最终移交项：

交付事件判定可先按下面速查：

| 当前事件 | 是否允许移交源码/永久授权/生产控制权 | 必须额外确认 |
|---|---|---|
| retained-control delivery | 否 | 交付材料中必须写清哪些控制权仍由开发者保留 |
| final control transfer | 是 | `delivery_control_handover_trigger` 已满足，通常为 `final_payment_received` |

### 交付事件执行门禁表

| 交付事件 | 允许交付的内容 | 不得标记为已完成的内容 | 必须附带的证据/说明 |
|---|---|---|---|
| retained-control delivery | 演示地址、试运行环境访问、验收材料、用户手册、运维说明 | 源码仓库权限、永久授权、生产密钥、管理员账号、最终部署权限 | 当前保留控制范围、当前事件类型、后续最终移交触发条件 |
| trial delivery under authorization | 试运行包、授权文件、限制说明、到期行为说明、验收材料 | 永久授权、完整源码、最终控制权 | `trial_authorization_terms.*`、到期行为验证、永久授权触发条件 |
| final control transfer | 源码、永久授权、构建/部署材料、密钥/配置、平台管理员权限、最终交接记录 | 无，但必须与 `transfer-checklist` 一致 | 尾款到账或其他触发条件证据、完整交接记录、回滚说明 |

- [ ] 源码仓库权限或源码包
- [ ] 永久授权文件，或移除试运行限制的正式版本
- [ ] 构建脚本、部署脚本、CI/CD 配置
- [ ] 生产环境变量、密钥、证书、第三方平台配置
- [ ] 服务器、域名、数据库、对象存储等管理员权限
- [ ] 最终运维文档、回滚说明、交接记录

若尾款尚未到账，上述条目不得在交付清单中标记为“已完成移交”。

### Step 7: 变更日志

**调用 Skill**：`changelog-generator` — 从 git commits 自动生成变更日志。降级：手动按功能、修复、风险、迁移说明四类整理。

### Step 8: 代码审查

**调用 Skill**：`requesting-code-review` — 完成提交前审查清单。降级：手动列出审查范围、验证证据和剩余风险。

### Step 9: 经验沉淀

本步骤包含两件事，**先分清再动手**：

| 产出物 | 面向 | 写什么 | 在哪 |
|-------|------|--------|------|
| `retrospective.md` | 当前项目 | 功能验收结果、Bug 清单、效率指标、改进建议 | `$TASK_DIR/delivery/retrospective.md` |
| `learn/*.md` | 工作流本身 | 流程踩坑、命令歧义、阶段路由错误、可复用经验 | `docs/workflows/新项目开发工作流/learn/` |

简单判断：如果问题是"这个功能没做好"，写 `retrospective.md`；如果问题是"这个流程/命令/文档本身有坑"，写 `learn/`。两者可以同时写，但不要混在一起。

---

**项目复盘**（→ `retrospective.md`）：效率指标 + Bug 知识沉淀 + 改进项

不要写成周报或制度材料，按真实开发过程复盘就够。优先记这些实际会拖慢你的点：

- 哪一步让你来回切换上下文
- 哪个命令说明看完还是容易误解
- 哪个门禁缺了，导致你返工或漏检
- 哪次人工介入其实暴露的是流程问题，不只是当前任务问题

#### Step 9a: 检查 tmp/ 中的待处理反馈文件

在正式复盘前，先检查 `tmp/` 目录下是否有 AI 起草但尚未处理的反馈文件：

```bash
ls tmp/workflow-feedback-*.md 2>/dev/null
```

如果存在未处理的反馈文件：

1. 逐一展示给用户，确认是否保留
2. 确认保留的，移动到 `docs/workflows/新项目开发工作流/learn/` 目录
3. 确认不需要的，直接删除
4. 移动完成后，删除 `tmp/` 中的原文件

> 这一步确保开发过程中 AI 起草的流程反馈不会遗漏。

#### Step 9b: 项目复盘

若在本次真实执行中发现了**流程问题、命令歧义、阶段路由错误、记录闭环缺口、人工介入触发原因、可复用提示词模式或明显反模式**，不要只停留在 `retrospective.md`。

请额外在以下目录沉淀一份经验反馈记录：

```text
docs/workflows/新项目开发工作流/learn/
```

记录方式：

- 新建 `YYYY-MM-DD-主题短名.md`
- 按 `learn/TEMPLATE.md` 填写（快速捕获或完整记录均可）
- 明确标注"是否值得学习优化"
- 若结论涉及修改工作流规则、命令门禁或阶段默认路径，必须等待人工确认后再回流修改

建议写法：

- 先写"哪里卡住了、你当时怎么判断错了、后来怎么发现的"
- 再写"这个坑是一次性失误，还是工作流本身容易让人踩"
- 最后再决定要不要升级成工作流优化候选

### Step 10: 收尾记录校验

进入 `/trellis:record-session` 前，先确认：

- 已完成内容已由人工测试并提交
- `/trellis:record-session` 在此只用于**当前任务完成后的最终收尾记录**
- 当前执行任务已完成，且本轮收尾只围绕**当前任务**
- 未完成任务不要误归档；非当前任务不要借本轮收尾顺手自动提交
- 不为了补齐新规则或整理台账而批量回写旧任务、旧会话记录或已归档目录
- staged 区不得混入非目标变更；若存在 staged 污染，必须先中断处理

收尾顺序：**先 record-session，再 archive**。record-session 需要当前任务上下文来生成会话记录；archive 会清除 `.current-task`，所以必须在 record-session 完成后再执行。

```bash
python3 <WORKFLOW_DIR>/commands/shell/record-session-helper.py \
  --title "Session Title" \
  --commit "hash1,hash2" \
  --summary "Brief summary of what was done"

python3 ./.trellis/scripts/task.py archive <current-task>

# 注意：archive 仍直接复用目标项目 Trellis 基线里的 task.py；若目标项目不是当前最新 Trellis 基线，
# 可能仍缺少 archive metadata auto-commit 的 pathspec 修复，需先升级 Trellis 再继续收尾。

git status --short .trellis/tasks .trellis/.current-task
```

判定规则：

- helper 返回 0：会话记录与元数据闭环完成，可以继续 archive
- helper 返回非 0：`/trellis:record-session` 不算完成，先处理 metadata closure 失败原因，不要 archive
- archive 后 `git status --short .trellis/tasks .trellis/.current-task` 输出应为空

---

## 输出

```
$TASK_DIR/delivery/
├── test-report.md
├── acceptance.md
├── deliverables.md
├── transfer-checklist.md
├── ownership-proof.md
├── source-watermark-verification.md
└── retrospective.md
```

## 下一步推荐

**当前状态**: 验收测试完成，交付物已生成；在用户明确确认前，仍停留在 delivery 阶段。

> 本节定义的是阶段完成后的推荐输出口径，用于帮助当前 CLI 或协作者说明下一步；它不是框架层自动跳转保证。

根据验收结果：

| 验收结果 | Claude / OpenCode 推荐入口 | Codex 推荐入口 | 说明 |
|---------|---------------------------|----------------|------|
| 全部通过，准备收尾 | `/trellis:record-session` | 进入会话收尾，或显式触发 `record-session` skill | **默认推荐**。仅在用户明确确认后才允许进入会话收尾；先通过 helper 完成记录与元数据闭环，再 archive |
| 有 P0/P1 缺陷 | `/trellis:break-loop` | 进入深度排障，或显式触发 `break-loop` skill | 深度分析 Bug 根因 |
| 有 P2/P3 缺陷 | `/trellis:start` | 回到实施阶段，或显式触发 `start` skill | 回到实施阶段修复 |
| 验收中出现冻结后新增 / 修改 / 删除需求 | [需求变更管理执行卡](../../需求变更管理执行卡.md) | 同上 | 先完成变更评估与确认；不要直接混入当前交付 |
| 需要更新规范文档 | `/trellis:update-spec` | 记录并更新规范，或显式触发 `update-spec` skill | 沉淀新发现的模式到 spec |
| 需要请求代码审查 | `requesting-code-review` 能力 | `requesting-code-review` skill | 提交前外部审查 |
| 需要归档任务 | `python3 ./.trellis/scripts/task.py archive <name>` | 同左 | 仅在 record-session 完成后使用；archive 会清除 `.current-task` |
| 不确定下一步 | `/trellis:delivery` | 描述当前收尾意图，或显式触发 `delivery` skill | 先停留在 delivery 阶段澄清，而不是自动进入会话收尾 |
