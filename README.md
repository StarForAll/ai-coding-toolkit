# AI 编程工具箱（ai-coding-toolkit）

这个仓库用于沉淀我在 AI 辅助编程过程中的可复用资产：自定义 agent、命令/脚本、以及可安装的 skills 等。

## 目录结构

- `agents/`：自定义 agent（系统提示词、工具约束、工作流等）
- `commands/`：自定义 command 集合（Codex/Claude/通用 Shell 等）
- `specs/`：具体编码规范文件（可作为团队/个人的可执行约定基线）
- `skills/`：可被 **Skills CLI**（`npx skills`）发现与安装的技能
- `marketplace/`：基于 trellis 框架的模板集合（个人自适应，不同场景可复用）
- `scripts/`：仓库维护脚本（例如 skills 校验）
- `docs/`：笔记、规范、设计文档等

## Skills（用于 `npx skills add`）

本仓库的 `skills/` 保持符合 Skills CLI 的可发现结构，可直接从 git 仓库安装。

### 快速安装（来自 git 托管）

将仓库推送到 GitHub/GitLab 后：

```bash
# 安装本仓库内的全部 skills
npx skills add <owner>/<repo>

# 或者使用完整 URL
npx skills add https://github.com/<owner>/<repo>
```

### 本地测试

```bash
# 仅列出 CLI 能发现的 skills（不安装）
npx skills add . --list

# 从本地路径安装（示例：全局范围）
npx skills add . -g -y
```

### 当前 skills

- `skills/demand-risk-assessment`
- `skills/example-skill`（最小模板）

### skills 目录约定

Skills 放在 `skills/<skill-id>/SKILL.md` 下：

- `skills/`
  - `<skill-id>/`
    - `SKILL.md`（必需）
    - `scripts/`（可选）
    - `references/`（可选）

`SKILL.md` 必须以 `---` 开头的 YAML frontmatter 起始块，并包含 `name`、`description` 字段（参考 `skills/example-skill/SKILL.md`）。

### 新增一个 skill

1. 新建目录：`skills/<new-skill-id>/`
2. 添加 `skills/<new-skill-id>/SKILL.md`（包含 YAML frontmatter，至少含 `name`、`description`）
3. （可选）添加 `scripts/` 与/或 `references/`
4. 运行校验脚本：

```bash
./scripts/validate-skills.sh
```

## Agents / Commands

这两块内容目前以“可读、可检索、可复用”为目标：

- `agents/README.md`：约定 agent 的组织方式与落盘格式建议
- `commands/README.md`：约定 command 的组织方式（按工具/平台归类）

## Specs / Marketplace

- `specs/README.md`：编码规范的组织方式与编写约定
- `marketplace/README.md`：基于 trellis 的模板集合组织方式与使用约定
