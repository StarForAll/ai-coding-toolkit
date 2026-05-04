# PRD: workflow/source 层历史漂移收敛

## Problem Statement

本项目是一个 meta-project，维护跨多个 AI CLI 工具（Claude Code、OpenCode、Codex CLI）的可复用工作流资产。系统设计了"source → deploy"的分层架构：`agents/` 和 `commands/` 为源资产层（source of truth），`.claude/`、`.opencode/`、`.codex/` 为工具部署层（derived instances）。

**当前状态：源资产层为空壳，部署层直接编辑，三层之间存在历史漂移。**

具体表现为：

1. **agents/ 源层为空**：`agents/` 目录只有 `README.md`，无任何实际 agent 源定义。三个工具部署目录（`.claude/agents/`、`.opencode/agents/`、`.codex/agents/`）各自独立维护，内容不同步。

2. **commands/ 源层为空**：`commands/claude/`、`commands/codex/`、`commands/shell/` 均只有 `README.md`，无实际脚本。Trellis 工作流命令（`finish-work.md`、`continue.md`、`record-session.md`）直接在各工具命令目录中维护。

3. **部署层不对称**：
   - OpenCode 有 5 个命令（含 `create-command.md`、`migrate-specs.md`），Claude 只有 3 个
   - OpenCode agents 有 self-loading context 机制，Claude agents 依赖 hook 注入，Codex 用 TOML 格式 + `developer_instructions` 字段
   - Claude 有 `workflow-audit` 和 `workflow-capability-audit` 两个 skill，OpenCode 没有
   - `record-session.md` 在 Claude 版本有更详细的 close-out 顺序说明

4. **备份文件残留**：每个工具目录都有 `.backup` 文件（agents 和 skills），表明过去有手动更新但未清理。

5. **library-lock.yaml 漂移**：最后一次 library sync 在 2026-03-29，距今超过一个月。`diff-library-assets.py` 因 `_internal` 模块导入问题无法运行。

6. **trellis-library sync 脚本不可用**：脚本引用 `from _internal.asset_state import ...`，但本地没有 `_internal` 包。

7. **5 个历史备份目录**：`.trellis/.backup-*` 共 5 个（含 phase1），未清理。

## Decisions (from brainstorm)

1. **Library sync 工具**：修复 `_internal` 模块导入问题，恢复 drift 检测能力
2. **备份清理**：暂不清理 `.backup` 文件和 `.trellis/.backup-*` 目录
3. **跨平台内容差异**：仅文档标注，不做内容同步。内容统一留给 `03-19-implement-agents-source` / `03-19-implement-commands-source` 任务在建立源层时处理

## Scope

### In Scope

- 识别并记录所有 source/deploy 层之间的漂移
- 修复 library sync 工具（`diff-library-assets.py` 的 `_internal` 导入问题）
- 运行 library drift 检测并记录结果
- 将跨平台差异分类标注到 spec 文档（合理差异 vs 需收敛的漂移）
- 清理空残留文件（`migrate-specs.md` 0 字节文件）
- 更新 spec 文档以反映当前实际状态

### Out of Scope

- 实现 `agents/` 源层（已有任务 `03-19-implement-agents-source`）
- 实现 `commands/` 源层（已有任务 `03-19-implement-commands-source`）
- 新增 agent 或 command 资产
- 修改 agent/system prompt 内容
- 跨平台内容同步（由源层任务统一处理）
- 清理 `.backup` 文件和 `.trellis/.backup-*` 目录（后续统一处理）

## Drift Inventory

### D1: Agent 部署层不对称

| Agent | Claude | OpenCode | Codex | 漂移类型 |
|-------|--------|----------|-------|----------|
| trellis-implement | basic frontmatter + body | self-loading context section | TOML + developer_instructions | **结构性**：内容模型不同 |
| trellis-check | basic frontmatter + body | self-loading context section | TOML format | **结构性** |
| trellis-research | basic frontmatter + body | self-loading context section | TOML format | **结构性** + `.opencode` 列举了更多平台配置路径 |

**判定**：部分漂移是**合理的平台差异**（frontmatter 格式、context 加载机制），但核心指令体（responsibilities、boundaries、workflow）应该保持一致。

### D2: Command 部署层不对称

| Command | Claude | OpenCode | 漂移 |
|---------|--------|----------|------|
| finish-work | identical | identical | 无 |
| continue | `--platform claude` | `--platform opencode` | **合理差异** |
| record-session | 有 close-out 顺序说明 + branch context | 无这些内容 | **需要同步** |
| create-command | 不存在 | 存在（154 行） | **OpenCode-only** |
| migrate-specs | 不存在 | 存在（0 字节空文件） | **残留** |

### D3: Skill 部署层不对称

| Skill | Claude | OpenCode | 漂移 |
|-------|--------|----------|------|
| trellis-check | identical | identical | 无 |
| trellis-before-dev | identical | identical | 无 |
| trellis-brainstorm | identical | identical | 无 |
| trellis-update-spec | identical | identical | 无 |
| trellis-break-loop | identical | identical | 无 |
| trellis-meta | identical | identical | 无 |
| workflow-audit | 存在 | 不存在 | **Claude-only** |
| workflow-capability-audit | 存在 | 不存在 | **Claude-only** |

### D4: Library Sync 工具不可用

`diff-library-assets.py` 导入 `_internal.asset_state` 失败，该包不存在于本地。这阻止了 library drift 检测。

### D5: 备份残留

- `.claude/agents/*.backup` × 3
- `.claude/skills/*.backup` × 5
- `.opencode/agents/*.backup` × 3
- `.opencode/skills/*.backup` × 5
- `.codex/agents/*.backup` × 3
- `.trellis/.backup-*` × 5 个目录

### D6: library-lock.yaml 过期

最后同步时间 2026-03-29，`last_diff_status: warn`，但无法重新验证。

## Proposed Actions

### A1: 修复 Library Sync 工具 [Required]

修复 `diff-library-assets.py` 的导入问题，使 library drift 检测恢复可用。

**方案**：
- 检查 `trellis-library/scripts/` 下是否有 `_internal` 包
- 如果存在，调整 Python path 或创建符号链接
- 如果不存在，评估是否需要从 trellis-library 上游同步该模块

### A2: 运行 Library Drift 检测 [Required]

A1 完成后，运行完整的 library diff 并记录结果到 `research/library-drift-report.md`。

### A3: 标注跨平台差异到 Spec 文档 [Required]

在 `.trellis/spec/agents/index.md` 和 `.trellis/spec/commands/index.md` 中新增"Platform Drift Status"章节：
- 明确标注哪些差异是**合理的平台适配**（frontmatter 格式、context-loading 机制、`--platform` 参数）
- 标注哪些是**需要收敛的漂移**（核心指令体不一致、单平台功能缺失）
- 对需要收敛的项注明：由 `03-19-implement-agents-source` / `03-19-implement-commands-source` 统一处理

### A4: 清理空残留文件 [Recommended]

删除 `.opencode/commands/trellis/migrate-specs.md`（0 字节空文件）。

### A5: 评估 workflow-audit / workflow-capability-audit 分发范围 [Optional]

这两个 skill 当前只在 Claude 部署，需决定是否也部署到 OpenCode/Codex。

## Success Criteria

1. Library sync 工具可用，能成功运行 `diff-library-assets.py`
2. Library drift 报告已记录到 `research/library-drift-report.md`
3. 所有跨平台漂移项已被分类为"合理差异"或"需收敛"，并标注到 spec 文档
4. 空残留文件（`migrate-specs.md`）已清理
5. Spec 文档（agents/index.md、commands/index.md）反映了当前实际漂移状态

## Risks

- 修复 library sync 工具可能涉及对 `trellis-library` 内部结构的理解
- 平台差异的分类有主观性，标注已基于 brainstorm 确认的策略

## Dependencies

- `03-19-implement-agents-source`（本任务的漂移标注为该任务提供输入）
- `03-19-implement-commands-source`（同上）
