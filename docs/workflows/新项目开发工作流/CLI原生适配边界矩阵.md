# CLI 原生适配边界矩阵

> 本文档聚焦"安装器管理什么 / 项目自己维护什么 / 运行前需满足什么"的边界说明。
> 目标项目若要判断“是否允许执行首次嵌入”或“当前是否已完整有效嵌入”，先看《[工作流嵌入执行规范](./工作流嵌入执行规范.md)》。
> 装后必检项统一见《[装后隐藏目录与托管边界核对清单](./装后隐藏目录与托管边界核对清单.md)》；各平台 README、命令映射.md、多CLI通用新项目完整流程演练.md 应引用本文档或该清单，不再各自扩写。

## 当前真实边界

在当前 `docs/workflows/新项目开发工作流` 版本里，需要先区分两层概念：

1. **Trellis 原生管理（当前真实）**
   - Trellis 0.5+ 通过 `trellis init` 原生提供 `trellis-research` / `trellis-implement` / `trellis-check` agents，覆盖 9 个平台
   - workflow 不再 overlay 这些 agent 定义，也不再维护 `commands/{claude,opencode,codex}/agents/` 源资产
   - 安装器仅做 legacy bare-name → trellis-* 迁移（rename），不写入 agent 内容
2. **workflow-managed subset（当前真实）**
   - Claude / OpenCode / Codex 的阶段命令（feasibility / brainstorm / design / plan / test-first / project-audit / check / review-gate / delivery）
   - Trellis 基线命令补丁（continue / finish-work / record-session）
   - 这是当前 workflow 安装器、升级分析、卸载、回归测试共同覆盖的子集

补充说明：

- `.iflow/agents/` 当前属于仓库级 live deployment 范围，但**不在**本 workflow 安装器的 managed subset 内
- 因此，若当前问题与 `trellis-research / trellis-implement / trellis-check` 的部署有关，应通过 Trellis 上游解决，而非在 workflow 安装器内 overlay

## 已完成的 agent 托管策略变更

Trellis 0.5 已原生提供 `trellis-research` / `trellis-implement` / `trellis-check` agents，覆盖 9 个平台（Claude / OpenCode / Codex / Cursor / Gemini / Kiro / Qoder / CodeBuddy / Pi）。workflow 已从"自维护 agent overlay"切换为"依赖 Trellis 原生 agents"。

### 变更后的实际链路

```text
Trellis 0.5 原生模板（trellis init 产物）
  -> target project .claude/.opencode/.codex trellis-* agents
```

workflow 不再维护 `commands/{claude,opencode,codex}/agents/` 源资产，也不再 overlay 这些文件。安装器仅做 legacy bare-name → trellis-* 迁移（rename）。

关键约束：

- `trellis-research` / `trellis-implement` / `trellis-check` 的主体语义由 Trellis 上游维护，workflow 不修改
- 若某平台确有行为差距（如 Codex class-2 缺 context self-loading），应通过 Trellis 上游机制或项目级配置解决，不在 workflow 源中补丁
- 安装器 / 升级分析 / 卸载脚本不再读写 agent 内容，仅检测和迁移 legacy bare-name 文件

### 已完成的原子更新集合

切换到 Trellis 原生 agent 时，以下文件已作为原子集合一起更新：

- `commands/install-workflow.py` — 移除 agent overlay，仅保留 legacy 迁移
- `commands/upgrade-compat.py` — 移除 agent overlay，仅保留 legacy 迁移
- `commands/uninstall-workflow.py` — 不再删除原生 trellis-* agents
- `commands/workflow_assets.py` — 移除 agent 相关定义，新增 `LEGACY_AGENT_NAMES`
- `commands/test_workflow_installers.py` — 更新为验证”不再管理 agents”
- `commands/claude/README.md` — 更新 agent 章节为”Trellis 原生管理”
- `commands/opencode/README.md` — 同上
- `commands/codex/README.md` — 同上
- 本文档 `CLI原生适配边界矩阵.md`
- `目标项目兼容升级方案指导.md`
- `commands/shared-agents/` — 已删除
- `commands/claude/agents/` — 已删除
- `commands/opencode/agents/` — 已删除
- `commands/codex/agents/` — 已删除

### `/tmp` 验证基线

基于 `/tmp` 临时项目的实际安装验证，当前 workflow 的正确检验口径应是：

1. 先在 `/tmp` 创建纯净 Trellis 目标项目
2. 满足安装前置条件：
   - Git 仓库
   - 新建仓库为 `main`
   - `origin` 至少 2 个 push URL
   - 已执行 `trellis init`
3. 用 `install-workflow.py` 生成真实 target layout
4. 比较的是：
   - workflow adapter 层
   - 与目标项目安装结果

而不是把“workflow 内部共享 source 的定义”和“目标项目安装结果验证”混成一层，否则会导致新的分析漂移。

## 分类定义

| 分类 | 含义 | 谁负责 |
|------|------|--------|
| **安装器管理** | `install-workflow.py` 负责部署、升级、一致性校验 | 安装器 |
| **手动维护** | 项目创建者或开发者按平台要求自行创建/维护 | 项目开发者 |
| **运行前置/仅校验** | 安装器会检查是否存在或满足条件，但不负责创建 | 项目开发者 + 安装器校验 |

---

## Claude Code

| 资产 | 目标位置 | 分类 | 说明 |
|------|---------|------|------|
| 阶段命令（feasibility / brainstorm / design / plan / test-first / project-audit / check / review-gate / delivery） | `.claude/commands/trellis/*.md` | 安装器管理 | 同源 Markdown + 路径改写 |
| Trellis 基线命令补丁（start / finish-work / record-session） | `.claude/commands/trellis/start.md` 等 | 安装器管理 | 保留基线 → 注入补丁 |
| 通用辅助脚本 | `.trellis/scripts/workflow/` | 安装器管理 | shell helper 脚本 |
| Trellis 基线 workflow 指南补丁 | `.trellis/workflow.md` | 安装器管理 | 保留 Trellis 基线文档 → 注入 workflow 项目化补丁（当前只增强 Development Process / Session End 区块） |
| 项目长期规则 | `AGENTS.md` | 半托管（手动维护为主） | 稳定执行规则、证据门禁由人工维护；`<!-- TRELLIS:START ... TRELLIS:END -->` 由 `trellis init` 托管，`<!-- workflow-nl-routing-start ... workflow-nl-routing-end -->` 由 workflow 安装器托管 |
| AGENTS.md NL 路由块 | `AGENTS.md` 内 `workflow-nl-routing` 区段 | 安装器管理 | 由 `install-workflow.py` 注入/更新，不要手工覆盖 |
| 共享运行时基线 | `.claude/settings.json` | 手动维护 | hooks 接线、默认 deny |
| 本机权限扩展 | `.claude/settings.local.json` | 手动维护 | MCP allowlist、本地调试 |
| 会话与子代理 hooks | `.claude/hooks/*.py` | 手动维护 | session-start / inject-subagent-context |
| 子代理定义 | `.claude/agents/*.md` | Trellis 原生管理 | Trellis 0.5+ 原生提供 `trellis-research` / `trellis-implement` / `trellis-check`；workflow 不再 overlay，仅做 legacy bare-name → trellis-* 迁移 |
| 项目 Git 前置条件 | `origin ≥ 2 push URL` | 运行前置/仅校验 | 安装器校验，不负责配置 |
| Trellis init 产物 | `.trellis/.version` | 运行前置/仅校验 | 安装器校验，由 `trellis init` 负责 |

---

## OpenCode

| 资产 | 目标位置 | 分类 | 说明 |
|------|---------|------|------|
| 阶段命令（feasibility / brainstorm / design / plan / test-first / project-audit / check / review-gate / delivery） | `.opencode/commands/trellis/*.md` | 安装器管理 | 与 Claude 同源 Markdown + 路径改写 |
| Trellis 基线命令补丁（start / finish-work / record-session） | `.opencode/commands/trellis/start.md` 等 | 安装器管理 | 保留基线 → 注入补丁 |
| 通用辅助脚本 | `.trellis/scripts/workflow/` | 安装器管理 | 与 Claude 共用，不重复部署 |
| Trellis 基线 workflow 指南补丁 | `.trellis/workflow.md` | 安装器管理 | 与 Claude / Codex 共用同一份目标项目 workflow 指南，保持 close-out 与 child-task 规则一致 |
| 阶段 skills（跨 CLI 可发现） | `.agents/skills/*/SKILL.md` | 安装器管理（与 Codex 共用单份落盘） | OpenCode 官方 skills 扫描链路会命中 `.agents/skills/`，因此同一份 skills 会被 OpenCode 与 Codex 同时发现；但当前 workflow 对 OpenCode 的**正式主入口**仍是 `.opencode/commands/trellis/`，不是 `.agents/skills/` |
| 子代理定义 | `.opencode/agents/*.md` | Trellis 原生管理 | Trellis 0.5+ 原生提供 `trellis-research` / `trellis-implement` / `trellis-check`；workflow 不再 overlay，仅做 legacy bare-name → trellis-* 迁移 |
| 项目长期规则 | `AGENTS.md` | 半托管（手动维护为主） | 与 Claude/Codex 共用同一文件；`TRELLIS` managed block 与 `workflow-nl-routing` 区段由 `trellis init` / `install-workflow.py` 分别托管 |
| workflow 文档注入 | `opencode.json.instructions` | 手动维护 | 只挂主入口与必要补充 |
| 项目 Git 前置条件 | `origin ≥ 2 push URL` | 运行前置/仅校验 | 安装器校验 |
| Trellis init 产物 | `.trellis/.version` | 运行前置/仅校验 | 安装器校验 |

**安装器不负责的 OpenCode 原生资产**（需手动维护）：

- `.opencode/agents/debug.md` 或其他非 `trellis-research / trellis-implement / trellis-check` 子代理
- `opencode.json` — instructions / provider / MCP 配置
- `AGENTS.md` 的手动段（workflow 不托管的章节）
- `.opencode/plugins/*.js` + `.opencode/package.json` — plugin 层（`trellis init` 产物，workflow 不重复分发）

---

## Codex

| 资产 | 目标位置 | 分类 | 说明 |
|------|---------|------|------|
| workflow 阶段 skills（feasibility / brainstorm / design / plan / test-first / project-audit / check / review-gate / delivery） | `.agents/skills/<phase>/SKILL.md` | 安装器管理（共享 skills 单点落盘） | 共享 skills 只落在 `.agents/skills/`；Codex 会直接读取这一路径；OpenCode 官方也会发现这一路径，但对当前 workflow 来说它不是 OpenCode 的正式主入口 |
| Trellis 基线 skill 补丁（start / finish-work） | 活动 skills 目录下的 `start/SKILL.md`、`finish-work/SKILL.md` | 安装器管理（活动目录增强） | **只在 `resolve_codex_skills_dir(root)` 解析出的活动 skills 目录**追加 workflow patch；当前 `trellis init` 下通常是 `.agents/skills/` |
| Trellis 基线 `record-session` skill | 活动 skills 目录下的 `record-session/SKILL.md` | 运行前置/仅校验 | 由 `trellis init` 提供；当前 workflow 不对其追加 Codex 专属 patch，但最终收尾仍依赖它与共享 helper 正常协同 |
| parallel skill 入口移除 | 各 skills 目录下的 `parallel/SKILL.md` | 安装器管理（条件移除） | **只在存在 parallel 的目录**执行：先备份，再把 `parallel` 从嵌入面移除；若不存在则跳过 |
| 通用辅助脚本 | `.trellis/scripts/workflow/` | 安装器管理 | 与 Claude/OpenCode 共用 |
| Trellis 基线 workflow 指南补丁 | `.trellis/workflow.md` | 安装器管理 | 与 Claude/OpenCode 共用；Codex hooks 注入的 `.trellis/workflow.md` 应与安装器增强后的文档保持一致 |
| 项目长期规则 | `AGENTS.md` | 半托管（手动维护为主） | 与 Claude/OpenCode 共用；`TRELLIS` managed block 与 `workflow-nl-routing` 区段由 `trellis init` / `install-workflow.py` 分别托管 |
| Codex 项目配置 | `.codex/config.toml` | 手动维护 | `AGENTS.md` fallback 等项目配置 |
| 会话启动注入 | `.codex/hooks.json` + `.codex/hooks/*.py` | 手动维护 | SessionStart hook 注入 Trellis 上下文 |
| 子代理定义 | `.codex/agents/*.toml` | Trellis 原生管理 | Trellis 0.5+ 原生提供 `trellis-research` / `trellis-implement` / `trellis-check`；workflow 不再 overlay，仅做 legacy bare-name → trellis-* 迁移 |
| 项目 Git 前置条件 | `origin ≥ 2 push URL` | 运行前置/仅校验 | 安装器校验 |
| Trellis init 产物 | `.trellis/.version` | 运行前置/仅校验 | 安装器校验 |

**安装器不负责的 Codex 原生资产**（需手动维护）：

- `.codex/config.toml` — Codex 项目级配置
- `.codex/hooks.json` + `.codex/hooks/*.py` — 会话启动 hooks
- 其他非 `research / implement / check` 的 `.codex/agents/*.toml`
- `AGENTS.md` 的手动段（workflow 不托管的章节）

### 多 skills 目录同步边界

`trellis init` 可能同时落盘 `.agents/skills/` 与 `.codex/skills/` 两个目录（例如本仓库实际观察到：主体 skills 落在 `.agents/skills/`，`parallel` 落在 `.codex/skills/`）。当前安装器对这两类目录采用分层策略：

- `install-workflow.py` 只向 `.agents/skills/` 写入共享阶段 skills
- `start` / `finish-work` baseline patch 只增强**活动 skills 目录**
- `parallel` 入口按"存在才移除，不存在就跳过"处理
- `upgrade-compat.py --check` 只在 `.agents/skills/` 检查共享分发 skills；若 `.codex/skills/` 中出现重复 shared skills，则视为重复副本

补充说明：

- 非活动目录中的 `start` / `finish-work` 同名文件**不在** `upgrade-compat.py --check` 的 baseline patch 检测范围内
- 这是设计边界，不是漏检：当前 workflow 安装器不会向非活动目录写入这两类 patch，因此这些文件不属于 workflow 托管漂移面

这意味着目录边界应理解为：

- `.agents/skills/` 承载共享 / 通用 workflow skills
- `.codex/skills/` 承载 Codex 特有或本地侧 skills
- 因此 `.codex/skills/` 不应被默认视为 `start` / `finish-work` 这类共享 baseline skill 的补丁目标
- Claude Code 官方技能目录仍是 `.claude/skills/`；当前没有官方证据表明 Claude Code 会读取 `.agents/skills/`

装后/升级后核对仍建议显式检查两条路径，确认两边已同步为一致状态：

```bash
# 所有 skills 目录
ls -d .agents/skills/ .codex/skills/ 2>/dev/null

# 核对 parallel 是否已从嵌入面移除，但备份仍在
ls .agents/skills/parallel/SKILL.md 2>/dev/null
ls .codex/skills/parallel/SKILL.md 2>/dev/null
ls .agents/skills/.backup-original/parallel/SKILL.md 2>/dev/null
ls .codex/skills/.backup-original/parallel/SKILL.md 2>/dev/null
```

---

## 跨平台对比速查

| 资产类型 | Claude | OpenCode | Codex |
|---------|--------|----------|-------|
| 阶段命令入口 | `.claude/commands/trellis/*.md` ✅ 安装器 | `.opencode/commands/trellis/*.md` ✅ 安装器 | `.agents/skills/*/SKILL.md` ✅ 安装器（`.codex/skills/*` 仅保留 Codex 独有或项目自定义 skills） |
| 基线补丁 | start / finish-work / record-session ✅ | start / finish-work / record-session ✅ | start / finish-work ✅（仅活动 skills 目录） |
| 收尾入口 | `record-session.md` + `.trellis/scripts/workflow/record-session-helper.py` | `record-session.md` + `.trellis/scripts/workflow/record-session-helper.py` | Trellis baseline `record-session` skill + `.trellis/scripts/workflow/record-session-helper.py` |
| 辅助脚本 | `.trellis/scripts/workflow/` ✅ | 共用 ✅ | 共用 ✅ |
| 嵌入尝试记录 | `.trellis/workflow-embed-attempt.json` ✅ 安装器（开始写入，成功后清理） | 共用 ✅ | 共用 ✅ |
| 项目规则 | `AGENTS.md` ⚠️ 半托管 | `AGENTS.md` ⚠️ 半托管 | `AGENTS.md` ⚠️ 半托管 |
| 平台配置 | `.claude/settings*.json` ❌ 手动 | `opencode.json` ❌ 手动 | `.codex/config.toml` ❌ 手动 |
| Hooks | `.claude/hooks/*.py` ❌ 手动 | `.opencode/plugins/*.js` ❌ 手动（trellis init 分发） | `.codex/hooks.json` + `.codex/hooks/*.py` ❌ 手动 |
| 子代理 | `research / implement / check` ✅ 部分安装器（由 workflow 部署）；其他手动 | `research / implement / check` ✅ 部分安装器（由 workflow 部署）；其他手动 | `research / implement / check` ✅ 部分安装器（由 workflow 部署）；其他手动 |

> 注意：上表描述的是**当前 workflow-managed subset**；`iFlow` 当前不在本 workflow 的 installer / upgrade / uninstall 合同内。
>
> 对 Codex 还要额外记住一条：`.codex/skills/` 是 `trellis init` 之后可能出现的额外影响面，而不是本文档要宣称的 Codex 官方唯一主目录；本文只是把它纳入当前 workflow 的实际核对边界。

---

## 收尾基线依赖

| 资产/行为 | 实际位置 | 分类 | 说明 |
|-----------|----------|------|------|
| `record-session` 元数据闭环增强 | `record-session` 基线入口 + workflow patch | 安装器管理 | 当前 workflow 会对 Trellis 基线 `record-session` 注入补丁增强 |
| `record-session` 自动提交失败恢复 | `.trellis/scripts/workflow/record-session-helper.py` + `metadata-autocommit-guard.py` | 安装器管理 | 三个平台共用同一套 `record-session-helper.py`，内置只读失败检测、pending 状态管理和 `--resume` 恢复；失败时输出 `TRELLIS_AUTO_ESCALATE_COMMAND=...`，支持提权重试。该增强对所有平台生效，但 Codex（沙箱环境）最容易触发 |
| `archive` 任务归档行为 | `.trellis/scripts/task.py` / `.trellis/scripts/common/task_store.py` | 运行前置/仅校验 | 仍由目标项目 Trellis 基线提供，当前 workflow **不分发** 这段基线代码 |
| archive metadata auto-commit pathspec 修复 | Trellis 基线 close-out 实现 | 运行前置/仅校验 | 若目标项目不是当前最新 Trellis 基线，收尾链路仍可能继承旧基线中的 archive bug；建议先升级 Trellis，再使用当前 workflow 的 `record-session -> archive` 收尾链路 |
| 源码水印与归属证明校验脚本 | `.trellis/scripts/workflow/ownership-proof-validate.py` | 安装器管理 | 校验 assessment / design / plan / delivery 各阶段的源码水印与归属证明产物 |
| 源码水印设计与交付产物 | `$TASK_DIR/design/source-watermark-plan.md`、`$TASK_DIR/delivery/ownership-proof.md`、`$TASK_DIR/delivery/source-watermark-verification.md` | 运行前置/人工维护 | 属于目标项目或任务产物，不由安装器直接生成 |

补充约束：

- `record-session` 虽然会被当前 workflow 注入元数据闭环补丁，但最终的 `archive` 仍直接调用目标项目 Trellis 基线里的 `python3 ./.trellis/scripts/task.py archive`
- 因此，这类 close-out 行为是否稳定，取决于目标项目当前 Trellis 基线是否已包含相应修复，而不是取决于 workflow 是否额外分发了 helper
- 若要验证该前提，优先检查目标项目 `.trellis/.version` 是否已升级到当前最新 Trellis 版本

---

## 前端视觉落地补充边界

| 子阶段 | Claude | OpenCode | Codex |
|--------|--------|----------|-------|
| UI 原型生成（`uiprompt.site -> Stitch -> Figma`） | ✅ 允许作为主执行器 | ✅ 允许作为主执行器 | ❌ 禁止作为主执行器 |
| UI -> 首版代码界面 | ✅ 允许作为主执行器 | ✅ 允许作为主执行器 | ❌ 禁止作为主执行器 |
| 后续前端视觉微调 / 样式修复 | ✅ | ✅ | ✅（但需遵循 `design/frontend-ui-spec.md`） |

补充约束：

- 若项目存在前端视觉落地链路，`UI -> 首版代码界面` 任务完成时必须产出 `design/frontend-ui-spec.md`
- 后续任意 CLI 再改前端时，默认都要以 `design/frontend-ui-spec.md` 作为统一约束来源
- `design/STITCH-PROMPT.md` 同时承担 Stitch `DESIGN.md` 的设计系统语义；UI 界面默认中文，给 Stitch 的执行 prompt 默认英文
- Figma 只承担整体视觉风格参考与校正职责，不作为具体内容布局照抄依据
- UI 原型文件、原型导出代码、临时网页源码都只属于参考资产，不能直接作为正式实现输入

## plan 阶段执行边界

| 子阶段 | Claude | OpenCode | Codex |
|--------|--------|----------|-------|
| 任务拆分 / lane 规划 / `task_plan.md` 摘要 | ✅ | ✅ | ✅ |
| 生成项目基础代码 / 具体实现代码 | ❌ 禁止 | ❌ 禁止 | ❌ 禁止 |
| 未确认前直接切到 `implementation` / `test-first` | ❌ 禁止 | ❌ 禁止 | ❌ 禁止 |

补充约束：

- `plan` 阶段只做任务划分与规划，不做具体任务执行
- 只有用户明确确认后，才允许进入某个叶子 task 的 `implementation` / `test-first`

---

## 静态验证分组

验证安装结果时，应分两组检查：

### 安装器产物验证

以下文件/目录由 `install-workflow.py` 负责部署，缺失表示安装未完成：

```bash
# Claude
test -f .claude/commands/trellis/brainstorm.md
test -f .claude/commands/trellis/check.md
test -f .claude/commands/trellis/delivery.md
test -d .trellis/scripts/workflow/
test -f .trellis/scripts/workflow/workflow-state.py
test -f .trellis/scripts/workflow/ownership-proof-validate.py

# OpenCode
test -f .opencode/commands/trellis/brainstorm.md
test -f .opencode/commands/trellis/check.md
test -f .opencode/commands/trellis/delivery.md

# Codex
test -f .agents/skills/brainstorm/SKILL.md
test -f .agents/skills/check/SKILL.md
```

### 平台前置资产验证

以下文件/目录由项目开发者手动维护，缺失不表示安装失败，但会导致平台无法正常运行：

```bash
# Claude
test -f AGENTS.md
test -f .claude/settings.json
test -f .claude/hooks/session-start.py

# OpenCode
test -f AGENTS.md
test -f opencode.json
test -f .opencode/plugins/session-start.js
test -f .opencode/plugins/inject-subagent-context.js

# Codex
test -f AGENTS.md
test -f .codex/config.toml
test -f .codex/hooks.json
test -f .codex/hooks/session-start.py
```

---

## 相关文档

| 文档 | 说明 |
|------|------|
| `装后隐藏目录与托管边界核对清单.md` | 安装后 / 升级后的隐藏目录与托管边界必检项 |
| `commands/claude/README.md` | Claude Code 原生适配详情 |
| `commands/opencode/README.md` | OpenCode 原生适配详情 |
| `commands/codex/README.md` | Codex 原生适配详情 |
| `命令映射.md` | 阶段 × 命令 × Skills 映射 |
| `多CLI通用新项目完整流程演练.md` | 通用主链 walkthrough |
