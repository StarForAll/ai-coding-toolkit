# Research: 新项目开发工作流 -- 源文档与嵌入文档内容偏移分析

- **Query**: 源文档（docs/workflows/新项目开发工作流/）与嵌入目标项目后的文档之间是否存在非预期偏移或矛盾
- **Scope**: Internal (源资产 vs 目标项目安装产物比对)
- **Date**: 2026-05-23

## Findings

### 背景说明

源文档描述的是"维护者在当前仓库中管理的 workflow 源资产"，嵌入文档描述的是"install-workflow.py 部署到目标项目后的实际落盘产物"。两者之间的差异有些是有意设计（如路径改写、平台适配），有些可能是同步遗漏。

### M-01: 源命令文件中脚本路径前缀与目标项目安装路径不匹配

| 字段 | 内容 |
|------|------|
| 严重程度 | **MEDIUM** |
| 文件 | 所有阶段命令文件（feasibility.md, brainstorm.md, design.md, plan.md, check.md, review-gate.md, delivery.md, project-audit.md） |
| 问题描述 | 命令文件中辅助脚本路径使用 `<WORKFLOW_DIR>/commands/shell/` 前缀（如 `/ops/softwares/python/bin/python3 <WORKFLOW_DIR>/commands/shell/workflow-state.py`），但安装后目标项目中的实际路径为 `.trellis/scripts/workflow/`。install-workflow.py 在部署时会做路径改写（将 `<WORKFLOW_DIR>/commands/shell/` 替换为 `.trellis/scripts/workflow/`），但这种设计意味着：1) 直接在源仓库中阅读命令文件时看到的路径不可用；2) 若路径改写逻辑有遗漏或变更，会导致目标项目脚本调用失败；3) `<WORKFLOW_DIR>` 这个占位符在源文件中是字面值，需要阅读 install-workflow.py 才能理解其替换规则。 |
| 建议处理 | 在命令文件头部或工作流总纲中显式声明路径替换规则，让阅读源文件的人知道 `<WORKFLOW_DIR>/commands/shell/` 会在安装时被替换。 |

### M-02: 命令文件与 skills 文件的格式差异可能导致内容截断

| 字段 | 内容 |
|------|------|
| 严重程度 | **MEDIUM** |
| 文件 | Codex 相关的 .agents/skills/*/SKILL.md 产物 |
| 问题描述 | 源命令文件（如 feasibility.md）包含 YAML frontmatter + 长正文。转换为 Codex SKILL.md 时，install-workflow.py 会剥离 YAML frontmatter（`sed '1,/^---$/d'` 两次）。但部分命令文件的正文结构与 SKILL.md 的预期格式可能有差异：1) SKILL.md 通常需要精简描述以适配 Codex skill 发现机制；2) 源命令文件的长正文（如 plan.md 570+ 行）直接灌入 SKILL.md 可能导致上下文过长；3) 若后续修改源命令文件并增加段落，对应的 SKILL.md 产物也会同步增长，可能超出 Codex 的最佳上下文窗口。 |
| 建议处理 | 评估是否需要为 Codex skill 生成精简版本而非全量转换，或在 install-workflow.py 中增加 SKILL.md 正文长度上限警告。 |

### L-01: 目标项目 AGENTS.md 路由块内容与源命令触发词可能偏移

| 字段 | 内容 |
|------|------|
| 严重程度 | **LOW** |
| 文件 | AGENTS.md workflow-nl-routing 区段 |
| 问题描述 | AGENTS.md 中的自然语言路由块由 install-workflow.py 注入，其触发词与命令文件中的 `When to Use` 段应保持同步。但两处维护是独立的：1) 命令文件中的触发词可以随时修改；2) AGENTS.md 路由块只在安装/升级时更新。若中间修改了命令文件触发词但未重装，路由块就会过时。 |
| 建议处理 | 考虑在 upgrade-compat.py --check 中增加路由块与命令文件触发词的交叉校验。 |

## Caveats / Not Found

- 未发现源文档描述的安装步骤与 install-workflow.py 实际行为之间的重大矛盾
- CLI原生适配边界矩阵.md、装后核对清单.md、目标项目兼容升级方案指导.md 三份边界文档之间的口径基本一致，未发现自相矛盾
- 源仓库 carrier 增强（如 trellis-research 的工具路由扩展）与目标项目 baseline 的差异已在 CLI原生适配边界矩阵.md 中声明，属于有意设计
