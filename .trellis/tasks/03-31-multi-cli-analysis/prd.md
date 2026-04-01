# brainstorm: 分析新项目开发工作流的多AI CLI支持

## Goal

对 `./docs/workflows/新项目开发工作流/` 中的工作流进行多 AI CLI 支持分析，结合各 CLI 官方文档和实际使用经验，评估当前实现是否满足要求。

**关键澄清**：install/uninstall 脚本是**同时**为所有检测到的 CLI 配置/卸载原生工作流，而非根据不同 CLI 做差异化配置。

---

## 多 CLI 支持现状分析

### 1. Claude Code ✅ 完整支持

**部署状态**:
- `.claude/commands/trellis/` 包含 14 个命令文件
- 8 个新命令全部部署: `feasibility`, `brainstorm`, `design`, `plan`, `test-first`, `self-review`, `check`, `delivery`
- `Phase Router` 已注入 `start.md`
- `Metadata Closure` 已注入 `record-session.md`
- 辅助脚本部署到 `.trellis/scripts/workflow/`

**结论**: 原生命令平台，完整支持。

---

### 2. OpenCode ⚠️ 部分支持（存在问题）

**官方能力**（来自 OpenCode 源码分析）:
- 自定义命令目录: `.opencode/commands/`
- 调用方式: TUI 中 `Ctrl+K` 打开命令对话框选择，或 `opencode run --command project:xxx`
- 命令格式: **纯 Markdown**（无 frontmatter）
- 子目录创建层级命令 ID，目录分隔符用冒号 `:`，如 `trellis/start.md` → 调用 `project:trellis:start`

**实际部署状态**:
```
.opencode/commands/trellis/
├── brainstorm.md ✅
├── check.md ✅
├── before-dev.md     ❌ (旧文件，非本次新命令)
├── break-loop.md     ❌ (旧文件)
├── ... 等旧文件
└── (缺失) feasibility.md, design.md, plan.md, test-first.md, self-review.md, delivery.md
```

**当前实现问题**:

| 问题 | 严重度 | 说明 |
|------|--------|------|
| **缺失 6 个新命令** | 🔴 高 | 源文件存在于 `commands/*.md`，但未部署到 `.opencode/commands/trellis/` |
| 命令格式未处理 | 🟡 中 | install script 直接复制 Claude 格式（带 frontmatter），OpenCode 应为纯 Markdown |
| `opencode.json.instructions` 未配置 | 🟡 中 | OpenCode README 说要用 `instructions` 加载工作流文档，但 install script 未处理 |

**Gap**: `install-workflow.py` 的 `deploy_opencode()` **未能成功部署全部 8 个新命令**到 OpenCode 目录。

---

### 3. Codex ⚠️ 有限支持（存在问题）

**官方能力**（来自 Codex 官方文档）:
- `AGENTS.md`: 项目级长期规则，作用域为所在目录树
- `hooks.json` + `.codex/hooks/*.py`: SessionStart hook 注入上下文
- `.codex/skills/` 或 `.agents/skills/`: skills 目录
- Skills 格式: `SKILL.md` + YAML frontmatter (`name:`, `description:`)
- `.codex/agents/*.toml`: 子代理定义
- 内建 slash commands: `/agent`, `/plan`, `/review` 等（平台级控制）

**实际部署状态**:
```
.codex/
├── agents/     ✅ research.toml, implement.toml, check.toml
├── skills/
│   └── parallel/  ✅ (旧 skill)
└── hooks/      ❌ hooks.json 和 session-start.py 未部署
```

**当前实现问题**:

| 问题 | 严重度 | 说明 |
|------|--------|------|
| `hooks.json` 未创建 | 🔴 高 | install script 不创建 `hooks.json` |
| `session-start.py` hook 未部署 | 🔴 高 | 只检查 hook 是否存在，不部署 |
| Skills 格式未处理 | 🟡 中 | 直接复制 markdown 为 SKILL.md，缺少 frontmatter |
| Phase Router 未通过 hook 注入 | 🟡 中 | 8 个命令未转为 skills，Phase Router 未部署 |

**Gap**: `install-workflow.py` 的 `deploy_codex()` **未部署 Codex 的 hooks 机制**，导致上下文注入不可用。

---

### 4. Gemini ❌ 不支持

**当前状态**:
- 只有占位 README
- 无命令、rules、agents、skills 实现
- 仅靠 `instructions` 注入 + shell 脚本降级

**结论**: 按文档说明为"兼容层"，但无实际实现。

---

## 核心问题根因

### 1. OpenCode 缺失 6 个新命令

**问题**：`install-workflow.py` 的 dry-run 显示"将部署 8/8 命令"，但实际 `.opencode/commands/trellis/` 只包含部分文件。

**可能原因**：
- 上次安装未成功完成（非 dry-run 模式）
- 目录结构或权限问题导致部分文件写入失败

### 2. install/uninstall 脚本对所有 CLI 使用相同的文件复制逻辑

**问题**：脚本假设所有 CLI 都能直接使用相同的文件格式，没有区分：

| CLI | 原生格式要求 | install script 实际行为 |
|-----|------------|----------------------|
| Claude Code | Markdown + frontmatter | ✅ 直接复制 |
| OpenCode | 纯 Markdown（无 frontmatter） | ❌ 直接复制 Claude 格式 |
| Codex | SKILL.md + frontmatter + hooks | ❌ 仅复制 markdown，hooks 未部署 |

### 3. Codex hooks 机制完全未部署

**问题**：
- `hooks.json` 未创建
- `session-start.py` 未部署
- 导致 Codex 的 SessionStart 上下文注入不可用

---

## 建议修复方向

### 立即修复

1. **补充 OpenCode 缺失的 6 个命令**：
   - 运行 `install-workflow.py --cli opencode` 确保全部 8 个命令部署成功
   - 或手动验证缺失原因

2. **为 Codex 部署 hooks 机制**：
   - 创建 `hooks.json`
   - 部署 `session-start.py`

### 格式适配修复

3. **区分 OpenCode 命令格式**：
   - OpenCode 命令应为纯 Markdown
   - 移除 YAML frontmatter

4. **补充 Codex skills 格式**：
   - 为每个 skill 添加 `name:` 和 `description:` frontmatter

### 架构优化

5. **分离源格式与部署格式**：
   - 源命令保持 Trellis 内部格式
   - `install-workflow.py` 根据目标 CLI 转换为原生格式

---

## Open Questions

1. OpenCode 的 `opencode.json.instructions` 是否由 install script 配置？
2. Codex 的 `session-start.py` hook 内容是什么？谁负责提供？
3. Phase Router（Phase Router）是 Claude 特有的还是通用的？

---

## Technical Notes

**已读取文件**:
- `docs/workflows/新项目开发工作流/完整流程演练.md`
- `docs/workflows/新项目开发工作流/命令映射.md`
- `docs/workflows/新项目开发工作流/commands/opencode/README.md`
- `docs/workflows/新项目开发工作流/commands/codex/README.md`
- `docs/workflows/新项目开发工作流/commands/cursor/README.md`
- `docs/workflows/新项目开发工作流/commands/gemini/README.md`
- `docs/workflows/新项目开发工作流/commands/install-workflow.py`
- `.claude/commands/trellis/`（实际部署）
- `.opencode/commands/trellis/`（实际部署）
- `.codex/agents/`, `.codex/skills/`（实际部署）

**已研究 CLI 官方能力**:
- OpenCode: 源码分析（DeepWiki）
- Codex: 官方文档（DeepWiki）

**CLI 官方文档结论**:
- OpenCode: 命令用纯 Markdown，调用 `Ctrl+K` 或 `project:command` 前缀
- Codex: skills 用 SKILL.md + frontmatter，hooks 用 `hooks.json` + Python 文件
- Claude Code: 命令用 Markdown + frontmatter，支持 `/` 触发
