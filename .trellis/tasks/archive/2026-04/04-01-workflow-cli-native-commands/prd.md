# 工作流命令原生适配多CLI + 自然语言触发 + 下一步推荐

## Goal

让 `docs/workflows/新项目开发工作流/` 中的工作流命令在 Claude Code、Codex、OpenCode 三个 CLI 中都能：
1. 容易被触发调用（降低记忆负担）
2. 支持自然语言触发（不需要记住精确命令名）
3. 每次对话输出时推荐下一个应执行的 trellis 命令（含工作流自定义命令和 trellis 官方命令）

## Requirements

### R1: NL 路由表（Phase Router 增强）

集中维护一份 NL→命令 路由表，覆盖：
- 8 个工作流阶段命令（feasibility, brainstorm, design, plan, test-first, self-review, check, delivery）
- 13 个框架命令（start, finish-work, record-session, break-loop, parallel, update-spec, check-cross-layer, integrate-skill, before-dev, onboard, create-command, check, brainstorm）

路由表格式：
```
| 触发短语模式 | 目标命令 | 优先级 |
|------------|----------|--------|
| 评估/能做吗/报价/新项目 | feasibility | 1 |
| 需求/PRD/明确需求 | brainstorm | 2 |
| 设计/架构图/选型/接口设计 | design | 3 |
| ...
```

### R2: 下一步推荐内嵌

每个命令 .md 末尾添加标准化的"下一步推荐输出"section：
- 基于 `命令映射.md` 中已有的分支路径速查表
- 包含：默认下一步、回退路径、跳过路径、特殊情况路径
- 始终包含 "不确定→/trellis:start" 兜底
- 使用已定义的输出格式规范

### R3: 无 hooks CLI 降级方案

- **Claude Code / iFlow**：通过 session-start hook 注入路由表到 session context
- **OpenCode**：路由表写入 `AGENTS.md` 或 `opencode.json.instructions`
- **Codex**：路由表写入 `AGENTS.md`；工作流命令通过 skills/agents 入口触发

### R4: 歧义消解逻辑

- NL 匹配多个命令时：按优先级排序，取最高优先级
- 优先级规则：当前阶段上下文 > 精确匹配 > 模糊匹配
- 兜底：匹配不到或不确定 → 路由到 `/trellis:start`（Phase Router 自动检测）
- AI 确认：当 top-2 优先级接近时，向用户确认意图

## Acceptance Criteria

- [ ] 用户说"帮我评估这个项目"→ 触发 feasibility 命令
- [ ] 用户说"开始设计"→ 触发 design 命令
- [ ] 用户说"提交前检查一下"→ 触发 finish-work 命令
- [ ] 每个工作流命令执行完毕后，输出标准化下一步推荐表
- [ ] 每个框架命令执行完毕后，输出标准化下一步推荐表
- [ ] Claude Code 通过 session context 注入路由表，NL 触发正常
- [ ] OpenCode 通过 AGENTS.md 获取路由表，NL 触发正常
- [ ] Codex 通过 AGENTS.md + skills 入口，NL 触发正常
- [ ] NL 歧义时有明确的消解策略

## Decision (ADR-lite)

**Context**: 工作流命令目前只能通过精确的 `/trellis:<name>` 触发，用户需要记住命令名；命令执行后无系统性的下一步推荐。

**Decision**:
1. NL 触发采用 **Phase Router 增强**方案 — 集中路由表 + session context/AGENTS.md 注入，而非为每个命令创建 Skill wrapper
2. 下一步推荐采用 **命令内嵌入**方案 — 每个命令末尾添加标准化推荐 section
3. 无 hooks 的 CLI 通过 AGENTS.md 降级注入路由信息

**Consequences**:
- 路由表集中维护，新增/修改命令只需更新一处
- 不创建额外 Skill 文件，减少维护层级
- OpenCode/Codex 的 NL 体验取决于 AGENTS.md 的 context 加载质量
- 框架命令的推荐 section 需要在三个 CLI 的部署目录都更新

## Definition of Done

- 路由表数据完整（覆盖所有 21 个命令）
- 每个命令有标准化下一步推荐 section
- install-workflow.py 更新，能部署新增内容
- 命令映射.md 同步更新
- 三个 CLI 实际测试 NL 触发正常

## Out of Scope

- Gemini CLI 深度适配（保持现有兼容层）
- Cursor 适配（当前已有 cursor/README.md）
- 工作流总纲.md 内容修改（只改命令文件和映射）
- 新增 SKILL.md wrapper 文件
- Hook 脚本逻辑变更（只改注入的数据内容）

## Technical Notes

### 关键文件变更清单

| 文件 | 变更类型 | 说明 |
|------|---------|------|
| `docs/workflows/.../命令映射.md` | 更新 | 新增完整 NL 路由表 section |
| `docs/workflows/.../commands/*.md` (×8) | 更新 | 每个命令末尾添加下一步推荐 section |
| `.claude/commands/trellis/*.md` (×13) | 更新 | 框架命令添加下一步推荐 section |
| `.opencode/commands/trellis/*.md` (×14) | 更新 | 同上 |
| `.iflow/commands/trellis/*.md` (×13) | 更新 | 同上 |
| `docs/workflows/.../commands/install-workflow.py` | 更新 | 部署路由表到 AGENTS.md |
| `docs/workflows/.../命令映射.md` 路由表 | 新增 section | NL 路由数据源 |

### 已有可复用资产
- `命令映射.md` 分支路径速查表 → 下一步推荐数据源
- `命令映射.md` 下一步推荐输出规范 → 输出格式模板
- 各命令 YAML frontmatter 中的 `description` + 触发词 → NL 路由数据源
- 各命令 "When to Use (自然触发)" section → NL 路由数据源

### 实现优先级
1. 创建集中 NL 路由表（数据整理）
2. 更新 8 个工作流命令（添加下一步推荐）
3. 更新 13 个框架命令（添加下一步推荐）
4. 更新 install-workflow.py（部署路由表）
5. 更新 AGENTS.md 模板（无 hooks 降级）
6. 更新命令映射.md（同步文档）
