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
| 项目长期规则 | `AGENTS.md` | 手动维护 | 稳定执行规则、证据门禁 |
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
| 子代理定义 | `.opencode/agents/*.md` | 手动维护 | research / implement / check / debug |
| 项目长期规则 | `AGENTS.md` | 手动维护 | 与 Claude/Codex 共用同一文件 |
| workflow 文档注入 | `opencode.json.instructions` | 手动维护 | 只挂主入口与必要补充 |
| 项目 Git 前置条件 | `origin ≥ 2 push URL` | 运行前置/仅校验 | 安装器校验 |
| Trellis init 产物 | `.trellis/.version` | 运行前置/仅校验 | 安装器校验 |

**安装器不负责的 OpenCode 原生资产**（需手动维护）：

- `.opencode/agents/*.md` — 子代理定义
- `opencode.json` — instructions / provider / MCP 配置
- `AGENTS.md` — 项目级长期规则

---

## Codex

| 资产 | 目标位置 | 分类 | 说明 |
|------|---------|------|------|
| workflow 阶段 skills（feasibility / brainstorm / design / plan / test-first / project-audit / check / review-gate / delivery） | `.agents/skills/<phase>/SKILL.md` 或 `.codex/skills/<phase>/SKILL.md` | 安装器管理 | 同源 Markdown 转换为 skill 格式 |
| Trellis 基线 skill 补丁（finish-work） | `.agents/skills/finish-work/SKILL.md` | 安装器管理 | 已有基线时追加项目化补丁 |
| 通用辅助脚本 | `.trellis/scripts/workflow/` | 安装器管理 | 与 Claude/OpenCode 共用 |
| 项目长期规则 | `AGENTS.md` | 手动维护 | 与 Claude/OpenCode 共用 |
| Codex 项目配置 | `.codex/config.toml` | 手动维护 | `AGENTS.md` fallback 等项目配置 |
| 会话启动注入 | `.codex/hooks.json` + `.codex/hooks/*.py` | 手动维护 | SessionStart hook 注入 Trellis 上下文 |
| 子代理定义 | `.codex/agents/*.toml` | 手动维护 | research / implement / check |
| 项目 Git 前置条件 | `origin ≥ 2 push URL` | 运行前置/仅校验 | 安装器校验 |
| Trellis init 产物 | `.trellis/.version` | 运行前置/仅校验 | 安装器校验 |

**安装器不负责的 Codex 原生资产**（需手动维护）：

- `.codex/config.toml` — Codex 项目级配置
- `.codex/hooks.json` + `.codex/hooks/*.py` — 会话启动 hooks
- `.codex/agents/*.toml` — 子代理定义
- `AGENTS.md` — 项目级长期规则

---

## 跨平台对比速查

| 资产类型 | Claude | OpenCode | Codex |
|---------|--------|----------|-------|
| 阶段命令入口 | `.claude/commands/trellis/*.md` ✅ 安装器 | `.opencode/commands/trellis/*.md` ✅ 安装器 | `.agents/skills/*/SKILL.md` ✅ 安装器 |
| 基线补丁 | start / finish-work / record-session ✅ | start / finish-work / record-session ✅ | finish-work ✅ |
| 辅助脚本 | `.trellis/scripts/workflow/` ✅ | 共用 ✅ | 共用 ✅ |
| 项目规则 | `AGENTS.md` ❌ 手动 | `AGENTS.md` ❌ 手动 | `AGENTS.md` ❌ 手动 |
| 平台配置 | `.claude/settings*.json` ❌ 手动 | `opencode.json` ❌ 手动 | `.codex/config.toml` ❌ 手动 |
| Hooks | `.claude/hooks/*.py` ❌ 手动 | plugin 层 ❌ 手动 | `.codex/hooks.json` + `.codex/hooks/*.py` ❌ 手动 |
| 子代理 | `.claude/agents/*.md` ❌ 手动 | `.opencode/agents/*.md` ❌ 手动 | `.codex/agents/*.toml` ❌ 手动 |

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
