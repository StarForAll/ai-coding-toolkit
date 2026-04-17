# CLI 原生适配边界矩阵

> 本文档是"安装器管理什么 / 项目自己维护什么 / 运行前需满足什么"的**单一事实源**。
> 各平台 README、命令映射.md、多CLI通用新项目完整流程演练.md 应引用本文档，不再各自扩写。

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
| 项目长期规则 | `AGENTS.md` | 半托管（手动维护为主） | 稳定执行规则、证据门禁由人工维护；`<!-- TRELLIS:START ... TRELLIS:END -->` 由 `trellis init` 托管，`<!-- workflow-nl-routing-start ... workflow-nl-routing-end -->` 由 workflow 安装器托管 |
| AGENTS.md NL 路由块 | `AGENTS.md` 内 `workflow-nl-routing` 区段 | 安装器管理 | 由 `install-workflow.py` 注入/更新，不要手工覆盖 |
| 共享运行时基线 | `.claude/settings.json` | 手动维护 | hooks 接线、默认 deny |
| 本机权限扩展 | `.claude/settings.local.json` | 手动维护 | MCP allowlist、本地调试 |
| 会话与子代理 hooks | `.claude/hooks/*.py` | 手动维护 | session-start / inject-subagent-context |
| 子代理定义 | `.claude/agents/*.md` | 手动维护 | research / implement / check / debug |
| 项目 Git 前置条件 | `origin ≥ 2 push URL` | 运行前置/仅校验 | 安装器校验，不负责配置 |
| Trellis init 产物 | `.trellis/.version` | 运行前置/仅校验 | 安装器校验，由 `trellis init` 负责 |

---

## OpenCode

| 资产 | 目标位置 | 分类 | 说明 |
|------|---------|------|------|
| 阶段命令（feasibility / brainstorm / design / plan / test-first / project-audit / check / review-gate / delivery） | `.opencode/commands/trellis/*.md` | 安装器管理 | 与 Claude 同源 Markdown + 路径改写 |
| Trellis 基线命令补丁（start / finish-work / record-session） | `.opencode/commands/trellis/start.md` 等 | 安装器管理 | 保留基线 → 注入补丁 |
| 通用辅助脚本 | `.trellis/scripts/workflow/` | 安装器管理 | 与 Claude 共用，不重复部署 |
| 阶段 skills（跨 CLI 共享） | `.agents/skills/*/SKILL.md` | 安装器管理（与 Codex 共享单份落盘） | OpenCode 官方 skills 扫描链路会命中 `.agents/skills/`，因此同一份 skills 同时影响 OpenCode 与 Codex；升级/核对时必须把该路径算在 OpenCode 影响面内 |
| 子代理定义 | `.opencode/agents/*.md` | 手动维护 | research / implement / check / debug |
| 项目长期规则 | `AGENTS.md` | 半托管（手动维护为主） | 与 Claude/Codex 共用同一文件；`TRELLIS` managed block 与 `workflow-nl-routing` 区段由 `trellis init` / `install-workflow.py` 分别托管 |
| workflow 文档注入 | `opencode.json.instructions` | 手动维护 | 只挂主入口与必要补充 |
| 项目 Git 前置条件 | `origin ≥ 2 push URL` | 运行前置/仅校验 | 安装器校验 |
| Trellis init 产物 | `.trellis/.version` | 运行前置/仅校验 | 安装器校验 |

**安装器不负责的 OpenCode 原生资产**（需手动维护）：

- `.opencode/agents/*.md` — 子代理定义
- `opencode.json` — instructions / provider / MCP 配置
- `AGENTS.md` 的手动段（workflow 不托管的章节）
- `.opencode/plugins/*.js` + `.opencode/package.json` — plugin 层（`trellis init` 产物，workflow 不重复分发）

---

## Codex

| 资产 | 目标位置 | 分类 | 说明 |
|------|---------|------|------|
| workflow 阶段 skills（feasibility / brainstorm / design / plan / test-first / project-audit / check / review-gate / delivery） | `.agents/skills/<phase>/SKILL.md` + `.codex/skills/<phase>/SKILL.md` | 安装器管理（同步写入所有存在的目录） | 同源 Markdown 转换为 skill 格式；安装器通过 `list_all_codex_skills_dirs` 获取全部目录，向每个目录同步写入阶段 skills |
| Trellis 基线 skill 补丁（finish-work） | 各 skills 目录下的 `finish-work/SKILL.md` | 安装器管理（条件注入） | **只在存在 finish-work 基线的目录**追加项目化补丁；若某目录缺少该基线（如 trellis init 未写入），则 info 跳过，不报错 |
| parallel skill 禁用覆盖 | 各 skills 目录下的 `parallel/SKILL.md` | 安装器管理（条件覆盖） | **只在存在 parallel 的目录**执行禁用覆盖；若不存在则跳过 |
| 通用辅助脚本 | `.trellis/scripts/workflow/` | 安装器管理 | 与 Claude/OpenCode 共用 |
| 项目长期规则 | `AGENTS.md` | 半托管（手动维护为主） | 与 Claude/OpenCode 共用；`TRELLIS` managed block 与 `workflow-nl-routing` 区段由 `trellis init` / `install-workflow.py` 分别托管 |
| Codex 项目配置 | `.codex/config.toml` | 手动维护 | `AGENTS.md` fallback 等项目配置 |
| 会话启动注入 | `.codex/hooks.json` + `.codex/hooks/*.py` | 手动维护 | SessionStart hook 注入 Trellis 上下文 |
| 子代理定义 | `.codex/agents/*.toml` | 手动维护 | research / implement / check |
| 项目 Git 前置条件 | `origin ≥ 2 push URL` | 运行前置/仅校验 | 安装器校验 |
| Trellis init 产物 | `.trellis/.version` | 运行前置/仅校验 | 安装器校验 |

**安装器不负责的 Codex 原生资产**（需手动维护）：

- `.codex/config.toml` — Codex 项目级配置
- `.codex/hooks.json` + `.codex/hooks/*.py` — 会话启动 hooks
- `.codex/agents/*.toml` — 子代理定义
- `AGENTS.md` 的手动段（workflow 不托管的章节）

### 多 skills 目录同步边界

`trellis init` 可能同时落盘 `.agents/skills/` 与 `.codex/skills/` 两个目录（例如本仓库实际观察到：主体 skills 落在 `.agents/skills/`，`parallel` 落在 `.codex/skills/`）。当前安装器不再区分"活动目录"与"影子目录"，而是对所有存在的 skills 目录一视同仁：

- `install-workflow.py` 向**所有 skills 目录**同步写入阶段 skills
- `finish-work` 补丁按"有基线就打补丁，没有就跳过"处理，**不要求所有目录都必须有 finish-work**
- `parallel` 禁用覆盖按"存在才覆盖，不存在就跳过"处理
- `upgrade-compat.py --check` 对**所有 skills 目录**分别检查内容、补丁与禁用覆盖状态

这意味着"漏掉影子目录"的问题已被修复，但引入了新的边界：

- `trellis init` 未必在每个 skills 目录都写入相同的基线集合（例如 `.codex/skills/` 可能没有 `finish-work`）
- 因此安装器不会强制"补齐缺失基线"，而是接受"某些目录有、某些目录没有"的现实

装后/升级后核对仍建议显式检查两条路径，确认两边已同步为一致状态：

```bash
# 所有 skills 目录
ls -d .agents/skills/ .codex/skills/ 2>/dev/null

# 核对 parallel 是否已在所有目录被禁用
ls .agents/skills/parallel/SKILL.md 2>/dev/null
ls .codex/skills/parallel/SKILL.md 2>/dev/null
```

---

## 跨平台对比速查

| 资产类型 | Claude | OpenCode | Codex |
|---------|--------|----------|-------|
| 阶段命令入口 | `.claude/commands/trellis/*.md` ✅ 安装器 | `.opencode/commands/trellis/*.md` ✅ 安装器 | `.agents/skills/*/SKILL.md` ✅ 安装器（同一份也被 OpenCode 原生 skills 扫描命中） |
| 基线补丁 | start / finish-work / record-session ✅ | start / finish-work / record-session ✅ | finish-work ✅ |
| 辅助脚本 | `.trellis/scripts/workflow/` ✅ | 共用 ✅ | 共用 ✅ |
| 项目规则 | `AGENTS.md` ⚠️ 半托管 | `AGENTS.md` ⚠️ 半托管 | `AGENTS.md` ⚠️ 半托管 |
| 平台配置 | `.claude/settings*.json` ❌ 手动 | `opencode.json` ❌ 手动 | `.codex/config.toml` ❌ 手动 |
| Hooks | `.claude/hooks/*.py` ❌ 手动 | `.opencode/plugins/*.js` ❌ 手动（trellis init 分发） | `.codex/hooks.json` + `.codex/hooks/*.py` ❌ 手动 |
| 子代理 | `.claude/agents/*.md` ❌ 手动 | `.opencode/agents/*.md` ❌ 手动 | `.codex/agents/*.toml` ❌ 手动 |

---

## 收尾基线依赖

| 资产/行为 | 实际位置 | 分类 | 说明 |
|-----------|----------|------|------|
| `record-session` 元数据闭环增强 | `record-session` 基线入口 + workflow patch | 安装器管理 | 当前 workflow 会对 Trellis 基线 `record-session` 注入补丁增强 |
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
| UI 原型生成（`uiprompt.site -> Stitch`） | ✅ 允许作为主执行器 | ✅ 允许作为主执行器 | ❌ 禁止作为主执行器 |
| UI -> 首版代码界面 | ✅ 允许作为主执行器 | ✅ 允许作为主执行器 | ❌ 禁止作为主执行器 |
| 后续前端视觉微调 / 样式修复 | ✅ | ✅ | ✅（但需遵循 `design/frontend-ui-spec.md`） |

补充约束：

- 若项目存在前端视觉落地链路，`UI -> 首版代码界面` 任务完成时必须产出 `design/frontend-ui-spec.md`
- 后续任意 CLI 再改前端时，默认都要以 `design/frontend-ui-spec.md` 作为统一约束来源
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
test -f .agents/skills/brainstorm/SKILL.md 2>/dev/null || test -f .codex/skills/brainstorm/SKILL.md
test -f .agents/skills/check/SKILL.md 2>/dev/null || test -f .codex/skills/check/SKILL.md
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
test -f .opencode/agents/implement.md  # 如使用子代理

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
| `commands/claude/README.md` | Claude Code 原生适配详情 |
| `commands/opencode/README.md` | OpenCode 原生适配详情 |
| `commands/codex/README.md` | Codex 原生适配详情 |
| `命令映射.md` | 阶段 × 命令 × Skills 映射 |
| `多CLI通用新项目完整流程演练.md` | 通用主链 walkthrough |
