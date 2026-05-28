# AI 编程工具箱（ai-coding-toolkit）

> 默认版本：简体中文 | [English](./README.en.md)

沉淀我在 AI 辅助编程过程中的可复用资产：规范、模板、agent、命令、skills、多工具配置、以及工作流。

## 目录结构

### 核心资产

| 目录 | 说明 |
|------|------|
| `trellis-library/` | **核心资产库**：specs、templates、checklists、examples、schemas、scripts，通过 `manifest.yaml` 注册管理 |
| `.trellis/spec/` | **项目活规范工作区**：定义如何编写和维护本仓库资产，11 个规范层（agents、checklists、commands、docs、examples、guides、library-assets、platforms、scripts、skills、templates） |
| `skills/` | 可被 **Skills CLI**（`npx skills`）发现与安装的技能（6 个） |

### 源资产层（Source Assets）

> ⚠️ `agents/` 已开始承载真实 source agent 资产，但尚未成为所有工具部署文件的自动同步源。
> `commands/*` 源资产层仍以脚手架为主；其中 `commands/shell/` 已有共享脚本，Claude / OpenCode 的 live command 资产仍主要直接维护于对应工具部署层，Codex 也不是 `.commands/` 型承载模型。

| 目录 | 说明 |
|------|------|
| `agents/` | Agent 源资产（tool-agnostic 的系统提示词、权限边界、工作流定义），已部分填充，详见 `agents/README.md` |
| `commands/claude/` | Claude Code 命令源资产，当前仍以 README 骨架为主 |
| `commands/codex/` | Codex CLI 辅助资产源层，当前仍以 README 骨架为主；不等于 `.codex/commands/` |
| `commands/shell/` | 通用 shell 脚本与辅助入口；当前已包含 `init-trellis-temp-project.sh` |

### 工具部署层（Tool Deployments）

| 目录 | 说明 |
|------|------|
| `.claude/` | Claude Code 配置：agents、commands、hooks、settings |
| `.opencode/` | OpenCode 配置：agents、commands、plugins、lib、settings |
| `.codex/` | Codex CLI 配置：agents（TOML 格式）、hooks、config |
| `.agents/` | 工具侧 skills 部署（共享 trellis workflow skills） |
| `.kiro/` | 工具侧 skills 部署（Kiro skills 部署面） |

### 其他

| 目录 | 说明 |
|------|------|
| `scripts/` | 仓库维护脚本（`validate-skills.sh`） |
| `docs/` | 笔记、设计文档，含 3 套工作流（`docs/workflows/**/`） |
| `reference-data/` | 空目录，待用 |
| `tmp/` | 临时流程数据，已在 `.gitignore` 中忽略 |
| `.trellis/` | Trellis 工作空间：workflow、tasks、workspace、scripts、spec、library-lock |
| `.github/` | GitHub Actions CI 配置（`trellis-library-ci.yml`） |
| `.ace-tool/` | 工具缓存，已在 `.gitignore` 中忽略 |

## 架构：源资产 → 工具部署

```
源资产层（source of truth）          工具部署层（派生实例）
────────────────────────           ──────────────────────────
agents/<id>/SYSTEM.md       ──→    .claude/agents/<role>.md
                             ──→    .opencode/agents/<role>.md
                             ──→    .codex/agents/<role>.toml

commands/claude/<id>/       ──→    .claude/commands/<ns>/<name>.md
commands/shell/<id>.sh      ──→    直接引用 / 复制到辅助流程
commands/codex/<id>/        ──→    Codex config / hooks / skills / helper assets
```

> **当前状态**：`agents/` 源资产层已部分建立，但尚未自动同步到所有工具部署目录；
> `commands/` 源资产层仍未收口成统一同步模型：`commands/shell/` 已有共享脚本，Claude / OpenCode 的 live command 资产仍主要直接维护于部署目录，Codex 当前主承载面则是 `AGENTS.md`、`.codex/config.toml`、hooks、`.agents/skills/` 与 `.codex/agents/`。
> 详见 `.trellis/spec/agents/index.md` 和 `.trellis/spec/commands/index.md`。

### 关于自动化工作流的说明

**本项目不使用全自动化 AI 开发工作流。** 参考案例：

- [ralph-claude-code](https://github.com/frankbria/ralph-claude-code) — 夜间自动化工作流
- [loki-mode](https://github.com/asklokesh/loki-mode) — 全自动化工作流

**本项目不采用此类方案的原因：**

1. **自动化带来的不确定性**
   - 执行权限不足时会卡顿
   - 影响范围过大时可能导致误删其他文件

2. **当前模型性能限制**
   - 全自动化会持续积累技术负债
   - 必须有人工干预才能确保质量

如果能够解决以上问题，可以大幅降低中低级开发人员的工作复杂度。

## Skills（用于 `npx skills add`）

本仓库的 `skills/` 保持符合 Skills CLI 的可发现结构，可直接从 git 仓库安装。

### 快速安装

```bash
# 从 git 仓库安装全部 skills
npx skills add <owner>/<repo>

# 或使用完整 URL
npx skills add https://github.com/<owner>/<repo>
```

### 本地测试

```bash
# 仅列出可发现的 skills（不安装）
npx skills add . --list

# 从本地路径安装
npx skills add . -g -y
```

### 当前 skills

| Skill ID | 说明 |
|----------|------|
| `collaborating-with-claude` | 通过 Claude Code CLI 协作，委托原型/调试/代码审查，支持多轮会话 |
| `demand-risk-assessment` | 需求风险评估：外包/项目/需求的接/谈判/暂停/拒绝判断，含结构化评分与风险矩阵 |
| `multi-cli-review` | 多 CLI 协作问题审查，输出结构化缺陷报告（支持单 reviewer 与多 reviewer 两种协议） |
| `multi-cli-review-action` | 多 CLI 审查汇总：读取多份 reviewer 报告，聚合去重、检测冲突、统一执行修复 |

### skills 目录约定

```
skills/
  <skill-id>/
    SKILL.md       # 必需，含 YAML frontmatter（name, description）
    scripts/       # 可选
    references/    # 可选
```

### 新增一个 skill

1. 新建目录：`skills/<new-skill-id>/`
2. 添加 `SKILL.md`（含 YAML frontmatter，至少含 `name`、`description`）
3. （可选）添加 `scripts/` 与/或 `references/`
4. 运行校验：

```bash
./scripts/validate-skills.sh
```

## Trellis Library

核心资产库位于 `trellis-library/`，包含通过 `manifest.yaml` 注册的所有可复用资产。

### 验证

```bash
python3 trellis-library/cli.py validate --strict-warnings
```

### 文档

详见 `trellis-library/README.md`、`trellis-library/taxonomy.md` 和 `.trellis/spec/library-assets/`。

## Claude Code 配置说明

本项目通过 Trellis 的 session-start hook 和 PreToolUse hook 动态注入上下文（项目状态、规范索引、任务信息、子 agent 上下文），已覆盖 CLAUDE.md 和 Teammates 模式的核心功能：

- **不需要开启 Teammates 模式**：Trellis 已实现更成熟的多 agent 编排（dispatch agent + worktree 隔离 + hook 上下文注入 + Ralph Loop 质量门禁），开启 Teammates 会引入双重编排和 hook 冲突。
- **不需要初始化 CLAUDE.md**：session-start hook 动态注入的内容（git 状态、活跃任务、spec 索引、workflow 指引）比静态 CLAUDE.md 更准确且自动更新，同时添加会导致信息冗余。

## 开发规范

所有开发规范在 `.trellis/spec/` 下：

```bash
# 查看全部规范索引
cat .trellis/spec/index.md

# 按任务类型查阅
cat .trellis/spec/library-assets/spec-authoring.md   # 编写 spec
cat .trellis/spec/scripts/python-conventions.md      # 编写 Python 脚本
cat .trellis/spec/agents/index.md                    # 定义 agent
cat .trellis/spec/commands/index.md                  # 定义 command
cat .trellis/spec/skills/index.md                    # 定义 skill
```
