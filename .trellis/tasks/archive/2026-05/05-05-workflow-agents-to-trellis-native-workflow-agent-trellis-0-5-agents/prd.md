# workflow-agents-to-trellis-native: 删除 workflow 自定义 agent 层，改依赖 Trellis 0.5 原生 agents

## Goal

Workflow 当前在 `docs/workflows/新项目开发工作流/commands/` 下维护了自定义的 3 角色 × 多平台 agent 源资产（shared-agents/ + claude/agents/ + opencode/agents/ + codex/agents/）。Trellis 0.5 已原生提供同名同角色 agents，且 Claude/OpenCode 平台内容完全一致、原生反而更全面。删除 workflow 自定义层可消除重复维护、防止漂移、自动获得 9 平台覆盖（vs 当前 3 平台）。

## What I already know

### 版本门控

- 工作流声明 COMPATIBLE_TRELLIS_VERSION = "0.4.0"
- 当前实际 trellis -v = "0.5.0-rc.3"
- 0.5.0 > 0.4.0，审计继续

### 部署层 vs 原生层 diff 证据

| 平台 | 部署 (repo .claude/agents 等) vs 原生 (dist/templates/) | 结论 |
|---|---|---|
| Claude | 0 diff — 完全一致 | 原生已覆盖 |
| OpenCode | 0 diff — 完全一致 | 原生已覆盖 |
| Codex | 部署版多了 Context Self-Loading 段落 | 需处理差距 |
| Kiro | 仅 {{PYTHON_CMD}} 占位符差异 | 原生已覆盖 |
| Cursor/Gemini/Qoder/Pi/Codebuddy | 工作流从未管理 | 原生免费获得 |

### Workflow 源层 vs 原生层 diff 证据

- shared-agents/ SYSTEM.md 是精简版，原生 agents 是完整版
- research: 原生有 persist-to-file 工作流 + TASK_DIR 解析 + scope limits + 文件格式模板 + guidelines；workflow 源缺失这些
- implement: 原生有完整 context + 工作流步骤 + code standards；workflow 源仅 5 条 responsibilities
- check: 原生有完整 context + self-fix 工作流 + verification；workflow 源仅 4 条 responsibilities

### 上下文注入机制

- Trellis 0.5 有 `inject-subagent-context.py` hook，class-1 平台（Claude/Cursor/OpenCode/Kiro）自动推送上下文
- class-2 平台（Codex/Copilot/Gemini/Qoder）无 per-sub-agent hook，agent 需自加载上下文
- 当前部署的 Codex agents 有 Context Self-Loading 段落，原生 Codex agents 没有

### MCP 路由差距

- Workflow research agent 有具体 MCP 路由优先级（ace→Context7→grok-search→exa→deepwiki）
- 原生 research agent 使用通用工具列表（Glob/Grep/Bash/web），不含 MCP 路由优先级
- 此差距属于项目级配置，不属于 agent 定义层

### model: opus 差距

- Workflow Claude adapter 设 `model: opus`，原生不设
- 此差距属于项目级配置（.claude/settings.json）

## Requirements

### R1: 删除 workflow 自定义 agent 源资产层

删除以下目录：
- `commands/shared-agents/` （3 roles × 3 files = 9 文件）
- `commands/claude/agents/` （3 .md adapter files）
- `commands/opencode/agents/` （3 .md adapter files）
- `commands/codex/agents/` （3 .toml adapter files）— 需先解决 R3

### R2: 更新 workflow_assets.py

- 移除 `MANAGED_IMPLEMENTATION_AGENTS` 常量
- 移除 `render_workflow_managed_agent()` 及其辅助函数
- 移除 `build_managed_asset_specs()` 中 `kind="agent"` 的行
- 移除 `workflow_managed_agent_*` 路径函数
- 移除 `AGENT_SUFFIXES`, `SHARED_AGENTS_DIR` 相关定义

### R3: 处理 Codex context self-loading 差距

Codex 是 class-2 平台，原生 agents 缺少 context self-loading 段落。需选择方案：
- Option A: 保留 `commands/codex/agents/` 作为补丁目录，install 时覆盖原生 Codex agents
- Option B: 删除全部 codex/agents/，依赖 Trellis 后续版本增加 Codex per-agent hook 支持
- Option C: 通过 trellis update 机制后置补丁（不修改 workflow 源）

### R4: 更新安装脚本逻辑

安装脚本中涉及 managed agent overlay 的逻辑需要移除或调整：
- `install-workflow.py` 不再 overlay agent 文件
- `upgrade-compat.py` 不再检查 managed agent 差异
- `detect-embed-state.py` 不再检查 managed agent 状态

### R5: 升级 COMPATIBLE_TRELLIS_VERSION

- 从 "0.4.0" 升级到 "0.5.0"
- 此变更在所有其他变更完成后执行，确保全链路验证通过后再提升锚点

### R6: 处理遗留部署产物

已安装的项目中可能存在旧名称 agent 文件（legacy `research.md` vs 新 `trellis-research.md`）：
- `upgrade-compat.py` 已有 legacy agent 迁移逻辑，保留此逻辑用于升级场景
- 确认迁移逻辑不依赖 `MANAGED_IMPLEMENTATION_AGENTS` 常量

### R7: 处理 MCP 路由和 model 偏好

这些差距不属于 agent 定义层，但需确保有替代方案：
- MCP 路由：通过项目级 rules 文件或 CLAUDE.md 注入
- model 偏好：通过 .claude/settings.json 配置

## Acceptance Criteria

- [ ] `commands/shared-agents/` 目录已删除
- [ ] `commands/claude/agents/` 目录已删除
- [ ] `commands/opencode/agents/` 目录已删除
- [ ] `commands/codex/agents/` 目录已删除（或 Codex 差距方案已实施）
- [ ] `workflow_assets.py` 不再包含 `MANAGED_IMPLEMENTATION_AGENTS`、`render_workflow_managed_agent`、agent 相关路径函数
- [ ] `build_managed_asset_specs()` 不再生成 `kind="agent"` 行
- [ ] 安装脚本不再 overlay managed agent 文件
- [ ] `COMPATIBLE_TRELLIS_VERSION` 已升级到 "0.5.0"
- [ ] 升级场景中 legacy agent 迁移逻辑仍可用
- [ ] 在 /tmp 纯净项目中 `trellis init` → 安装 workflow → 验证 agents 来源正确（原生提供，非 workflow overlay）
- [ ] 已有项目 upgrade 后 agents 状态正确

## Definition of Done

- 所有 AC 检查项通过
- 相关 Python 测试通过（workflow_assets.py, install-workflow.py, upgrade-compat.py）
- /tmp 纯净项目端到端验证通过
- Lint/typecheck 通过

## Decision (ADR-lite)

**Context**: Trellis 0.5 原生提供 trellis-{research,implement,check} agents，覆盖 9 个平台。Workflow 自定义 agent 源层是 0.4 时代遗留，内容比原生更少，维护成本高，且造成漂移风险。唯一差距是 Codex class-2 平台的 context self-loading。

**Decision**: 删除全部 workflow 自定义 agent 源层和适配器目录。Codex 差距通过保留 upgrade-compat.py 中的 legacy agent 迁移逻辑 + 依赖 Trellis 后续版本解决（不在 workflow 源中保留 codex/agents/ 补丁）。

**Consequences**:
- Pro: 消除重复维护、防止漂移、自动获得 9 平台覆盖
- Pro: workflow_assets.py 和安装脚本更简洁
- Con: Codex agent 暂时缺少 context self-loading（class-2 平台已知限制）
- Con: MCP 路由优先级需通过项目级配置注入，不再嵌入 agent 定义

## Out of Scope

- 修改 Trellis 0.5 原生 agent 模板（属于 Trellis 上游）
- 为 Codex 添加 per-agent hook 机制（属于 Trellis 上游）
- 修改项目级 rules/settings 来注入 MCP 路由和 model 偏好（独立任务）
- 实现 agents/ 源资产层（03-19-implement-agents-source 任务，本任务与它独立）

## Technical Notes

### 涉及文件

- `docs/workflows/新项目开发工作流/commands/shared-agents/` — 删除
- `docs/workflows/新项目开发工作流/commands/claude/agents/` — 删除
- `docs/workflows/新项目开发工作流/commands/opencode/agents/` — 删除
- `docs/workflows/新项目开发工作流/commands/codex/agents/` — 删除
- `docs/workflows/新项目开发工作流/commands/workflow_assets.py` — 修改
- `docs/workflows/新项目开发工作流/commands/install-workflow.py` — 修改
- `docs/workflows/新项目开发工作流/commands/upgrade-compat.py` — 修改
- `docs/workflows/新项目开发工作流/commands/detect-embed-state.py` — 修改

### 关键约束

- COMPATIBLE_TRELLIS_VERSION 锚点提升在最后执行
- legacy agent 迁移逻辑（upgrade-compat.py 中的 `workflow_legacy_managed_agent_target_name`）需保留
- Codex skill candidates 函数（`codex_phase_router_skill_candidates` 等）不涉及 agents，不受影响

### 已验证的 Trellis 0.5 原生覆盖

- dist/templates/claude/agents/ — trellis-{research,implement,check}.md
- dist/templates/opencode/agents/ — trellis-{research,implement,check}.md
- dist/templates/codex/agents/ — trellis-{research,implement,check}.toml
- dist/templates/cursor/agents/ — trellis-{research,implement,check}.md
- dist/templates/gemini/agents/ — trellis-{research,implement,check}.md
- dist/templates/kiro/agents/ — trellis-{research,implement,check}.json
- dist/templates/qoder/agents/ — trellis-{research,implement,check}.md
- dist/templates/codebuddy/agents/ — trellis-{research,implement,check}.md
- dist/templates/pi/agents/ — trellis-{research,implement,check}.md
