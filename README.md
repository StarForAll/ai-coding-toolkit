# AI 编程工具箱（ai-coding-toolkit）

沉淀我在 AI 辅助编程过程中的可复用资产：规范、模板、agent、命令、skills、以及多工具配置。

## 目录结构

### 核心资产

| 目录 | 说明 |
|------|------|
| `trellis-library/` | **核心资产库**：specs、templates、checklists、examples、schemas、scripts，通过 `manifest.yaml` 注册管理 |
| `.trellis/spec/` | **项目本地开发规范**：定义如何编写和维护本仓库的所有资产 |
| `skills/` | 可被 **Skills CLI**（`npx skills`）发现与安装的技能 |

### 源资产层（Source Assets）

| 目录 | 说明 |
|------|------|
| `agents/` | Agent 源资产：tool-agnostic 的系统提示词、权限边界、工作流定义 |
| `commands/claude/` | Claude Code 命令源资产 |
| `commands/codex/` | Codex CLI 命令源资产 |
| `commands/shell/` | 通用 shell 脚本 |

### 工具部署层（Tool Deployments）

| 目录 | 说明 |
|------|------|
| `.claude/` | Claude Code 配置：agents、commands、hooks、settings |
| `.opencode/` | OpenCode 配置：agents、commands、plugins |
| `.iflow/` | iFlow 配置：agents、commands、hooks、settings |

### 其他

| 目录 | 说明 |
|------|------|
| `scripts/` | 仓库维护脚本（例如 skills 校验） |
| `docs/` | 笔记、设计文档 |
| `.trellis/` | Trellis 工作空间：workflow、tasks、workspace |

## 架构：源资产 → 工具部署

```
源资产层（source of truth）          工具部署层（派生实例）
────────────────────────           ──────────────────────────
agents/<id>/SYSTEM.md       ──→    .claude/agents/<role>.md
                             ──→    .opencode/agents/<role>.md
                             ──→    .iflow/agents/<role>.md

commands/<tool>/            ──→    .<tool>/commands/<ns>/<name>.md

trellis-library/specs/      ──→    .trellis/spec/universal-domains/（导入）
```

修改源资产后需要同步到对应的工具部署层。详见 `.trellis/spec/agents/index.md` 和 `.trellis/spec/commands/index.md`。

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

- `skills/demand-risk-assessment` — 需求风险评估

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

详见 `trellis-library/taxonomy.md` 和 `.trellis/spec/library-assets/`。

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
