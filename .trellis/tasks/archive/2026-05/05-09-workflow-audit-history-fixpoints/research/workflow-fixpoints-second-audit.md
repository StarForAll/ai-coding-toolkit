# Research: 工作流修复点二次审计

- **Query**: 对 /tmp/trellis-0.5.9-2 安装后产物做修复点 19/21/22/23/24/25 的完整复查
- **Scope**: internal
- **Date**: 2026-05-09

## Findings

### Files Found

| File Path | Description |
|---|---|
| `/tmp/trellis-0.5.9-2/.claude/agents/trellis-research.md` | Claude 平台 research 代理（含完整搜索路由表） |
| `/tmp/trellis-0.5.9-2/.claude/agents/trellis-implement.md` | Claude 平台 implement 代理 |
| `/tmp/trellis-0.5.9-2/.claude/agents/trellis-check.md` | Claude 平台 check 代理 |
| `/tmp/trellis-0.5.9-2/.opencode/agents/trellis-research.md` | OpenCode 平台 research 代理（含完整搜索路由表） |
| `/tmp/trellis-0.5.9-2/.opencode/agents/trellis-implement.md` | OpenCode 平台 implement 代理 |
| `/tmp/trellis-0.5.9-2/.opencode/agents/trellis-check.md` | OpenCode 平台 check 代理 |
| `/tmp/trellis-0.5.9-2/.codex/agents/trellis-research.toml` | Codex 平台 research 代理（简化版，无搜索路由表） |
| `/tmp/trellis-0.5.9-2/.codex/agents/trellis-implement.toml` | Codex 平台 implement 代理 |
| `/tmp/trellis-0.5.9-2/.codex/agents/trellis-check.toml` | Codex 平台 check 代理 |
| `/tmp/trellis-0.5.9-2/.trellis/workflow.md` | 项目工作流指南（含子代理 dispatch 协议） |
| `/tmp/trellis-0.5.9-2/.trellis/workflow-installed.json` | 安装记录 |
| `/tmp/trellis-0.5.9-2/.trellis/workflow-docs/需求变更管理执行卡.md` | 嵌入执行卡 1 |
| `/tmp/trellis-0.5.9-2/.trellis/workflow-docs/源码水印与归属证据链执行卡.md` | 嵌入执行卡 2 |
| `/tmp/trellis-0.5.9-2/.claude/commands/trellis/plan.md` | plan 阶段命令（含性能优化子任务要求） |
| `/tmp/trellis-0.5.9-2/.claude/commands/trellis/design.md` | design 阶段命令（含 README.en.md 要求） |
| `/tmp/trellis-0.5.9-2/AGENTS.md` | 项目规则（含 NL 路由块） |
| `/tmp/trellis-0.5.9-2/.trellis/spec/universal-domains/project-governance/readme-governance/normative-rules.md` | README 双语治理规范规则 |
| `/tmp/trellis-0.5.9-2/.trellis/spec/universal-domains/project-governance/readme-governance/verification.md` | README 双语验证规则 |
| `/ops/.../commands/workflow_assets.py` | 安装器资产常量（MANAGED_ENHANCED_AGENT_NAMES 等） |
| `/ops/.../commands/install-workflow.py` | 安装器主脚本 |
| `/ops/.../CLI原生适配边界矩阵.md` | CLI 适配边界说明 |

### 修复点逐项审计

---

#### #19: research -> implement -> check 子代理链调用能力

**是否满足**: ✅ 已满足

**证据**:

1. workflow.md 行 198: "trellis-implement → trellis-check → trellis-update-spec → commit" 完整链路定义
2. workflow.md 行 201: 统一 dispatch 协议，所有子代理 dispatch 必须以 `Active task: <path>` 开头
3. workflow.md 行 459-505: implement 子代理 dispatch 细节（三种 CLI 分列说明）
4. workflow.md 行 511-556: check 子代理 dispatch 细节（含 inline 和 sub-agent 两条路径）
5. workflow.md 行 347-357: research 子代理 dispatch 说明（含 inline override）
6. 三个平台的代理文件全部就位：
   - Claude: `.claude/agents/trellis-{research,implement,check}.md`
   - OpenCode: `.opencode/agents/trellis-{research,implement,check}.md`
   - Codex: `.codex/agents/trellis-{research,implement,check}.toml`
7. 所有代理含 Recursion Guard（trellis-implement.md 行 15-17, trellis-check.md 行 16-18）
8. Codex 代理设 `multi_agent = false` 防止 wait_agent 自死锁（trellis-implement.toml 行 86-90）
9. AGENTS.md 行 24-72: NL 路由块含 "设计→/trellis:design" 映射，间接引导进入 design 阶段后可通过 plan 进入子代理链

**与上次对比变化**: 无变化，维持已满足状态

---

#### #21: trellis-research 增强搜索能力对齐（ace.search_context / exa / grok-search / deepwiki / Context7）

**是否满足**: ⚠️ 部分满足（Codex 版本缺少搜索路由表）

**证据**:

Claude 版本（完整）:
- trellis-research.md 行 5: tools 列表含 mcp__ace__search_context, mcp__exa__web_search_exa, mcp__exa__web_fetch_exa, mcp__exa__get_code_context_exa, mcp__exa__web_search_advanced_exa, mcp__Context7__resolve-library-id, mcp__Context7__query-docs, mcp__deepwiki__read_wiki_structure, mcp__deepwiki__read_wiki_contents, mcp__deepwiki__ask_question, mcp__grok-search__web_search, mcp__grok-search__web_fetch
- 行 48-56: 6 类搜索路由表（Internal code → ace.search_context; Library docs → Context7; GitHub repos → deepwiki; Real-time → grok; General web → exa; Advanced → exa_advanced）

OpenCode 版本（完整）:
- trellis-research.md 行 6-17: permissions 含 mcp__ace__search_context:allow, mcp__exa__*:allow, mcp__Context7__*:allow, mcp__deepwiki__*:allow, mcp__grok-search__*:allow
- 行 60-67: 与 Claude 版本相同的搜索路由表

Codex 版本（简化）:
- trellis-research.toml: developer_instructions 仅包含通用研究流程（resolve task → mkdir → read → write → report）
- **缺失**: 无搜索路由表，无 MCP 工具优先级指引，无 fallback 链说明
- **缺失**: 无 ace.search_context、Context7、deepwiki、grok-search、exa 等工具路由指导

**缺口描述**: Codex 的 trellis-research.toml 代理定义未包含搜索能力路由表和 MCP 工具优先级指引。Codex 代理通过 developer_instructions 文本指导行为，而非 tools frontmatter 权限过滤，因此缺少路由表意味着 Codex research 子代理无法获得"何时用 Context7、何时用 deepwiki、何时用 grok"的搜索策略指引。

**根因**: `source_agent_path()` 对 codex 指向 `.codex/agents/trellis-research.toml`，该 TOML 源文件不含搜索路由表内容。Claude/OpenCode 版本则从各自的 `.md` 源文件继承完整路由表。

**与上次对比变化**: 较上次审计新增发现。上次审计未区分三个平台的 research 代理内容差异。Claude 和 OpenCode 已完整对齐，Codex 存在缺失。

---

#### #22: AI CLI 工作流嵌入规范指导文档

**是否满足**: ✅ 已满足

**证据**:

1. `.trellis/workflow-docs/` 目录存在，包含 2 份执行卡：
   - `需求变更管理执行卡.md`（3237 bytes, 4月17日）
   - `源码水印与归属证据链执行卡.md`（6834 bytes, 4月28日）
2. workflow-installed.json 行 61-63: `execution_cards` 字段正确记录两份执行卡
3. design.md 行 377: 引用 `源码水印与归属证据链执行卡`
4. design.md 行 495: 引用 `需求变更管理执行卡`（需求变更分流）
5. workflow_assets.py 行 105: `EXECUTION_CARDS = ["需求变更管理执行卡.md", "源码水印与归属证据链执行卡.md"]`
6. install-workflow.py 行 1319-1320: `deploy_execution_cards()` 函数实现分发
7. install-workflow.py 行 1635-1638: 安装流程中调用 `deploy_execution_cards`

**嵌入规范文档功能完整性**:
- 需求变更管理执行卡：4 步闭环（变更识别 → 影响评估 → 用户确认 → 回到受影响最早阶段），含触发条件、不触发条件、口语示例
- 源码水印与归属证据链执行卡：4 层分层模型（W0 可见 → W1 零宽 → W2 不起眼标识 → W3 零水印记录），覆盖 feasibility/design/plan/delivery 各阶段动作

**与上次对比变化**: 无变化，维持已满足状态

---

#### #23: 双语言版本 README

**是否满足**: 📈 较上次改善

**证据**:

规范约束层（完整）:
1. `.trellis/spec/universal-domains/project-governance/readme-governance/` 目录存在，含 4 个文件：
   - `normative-rules.md`: 完整双语 README 规范（README.md + README.en.md 配对、交叉链接、同步更新、漂移防护）
   - `verification.md`: 验证项（paired set、双语言同变更、交叉链接、不漂移）
   - `overview.md`: 目的与适用范围
   - `scope-boundary.md`: 边界说明

design 命令层（完整）:
2. design.md 行 335-336: Block C 明确列出 `项目根 README.md（默认中文版，最低可用版）` + `项目根 README.en.md（与 README.md 对齐的英文补充版）`
3. design.md 行 439: 退出条件要求 `项目根 README.md 与 README.en.md 已生成或确认可复用`
4. design.md 行 479: 输出文件列表包含 `README.en.md`
5. design.md 行 402: 块 C/D 顺序约束中提及 README.md / README.en.md 依赖块 D 确认的标注要求
6. design.md 行 69: 技术架构确认前必须留在工作底稿的内容包含 `README 中的技术架构部分`

安装后提示层（仍有缺口）:
7. install-workflow.py 行 1736: 仅提到 "在目标项目根 README.md 中说明 todo.txt 的存在与用途"，**未**显式提及 README.en.md 或 design 阶段需产出英文版 README

AGENTS.md NL 路由层（隐式引导）:
8. AGENTS.md 行 42: `设计...→/trellis:design` 映射，间接引导进入 design 阶段（design 命令内含完整 README.en.md 要求）

**缺口描述**: 安装后打印的"项目级协作提醒"仅提及 README.md，未显式提醒 design 阶段需产出 README.en.md。不过，这一缺口的影响已被以下机制充分缓解：
- readme-governance spec 提供了规范性约束
- design 命令 Block C 和退出条件明确要求 README.en.md
- 用户进入 design 阶段时一定会看到 README.en.md 的产出要求

**与上次对比变化**: 较上次审计显著改善。上次审计标记为"⚠️ 部分满足"，当时问题是"规范约束完整但安装后提示未显式提醒"。本次复查发现：
- 新增: readme-governance spec 已完整安装（含 normative-rules + verification）
- 新增: design.md Block C 和退出条件已显式要求 README.en.md
- 仍存: 安装后提示缺 README.en.md 提及（但影响面已被上述机制覆盖，属于低优先级缺口）

---

#### #24: 目标项目必须包含性能优化子任务

**是否满足**: ✅ 已满足

**证据**:

1. plan.md 行 210: `post_mainline_performance_task: yes` 作为阶段出口字段
2. plan.md 行 227: `性能回归与优化任务：主干任务完成后的固定后置任务（必选）`
3. plan.md 行 232: 依赖关系含 `性能回归与优化任务`
4. plan.md 行 239: 确认清单含 `已确认 性能回归与优化任务 为主干后的固定必选任务`
5. plan.md 行 246: `post_mainline_performance_task: yes` 在确认结果模板中
6. plan.md 行 311: `performance probe` 早期探针要求
7. plan.md 行 312: **强制要求** "无论项目是否启用源码水印，都**必须**额外拆出一个独立的后置 task：性能回归与优化任务"
8. plan.md 行 384: 任务列表示例含 `.trellis/tasks/04-14-performance-opt`
9. plan.md 行 402-403: 依赖规则（性能任务依赖全部主干完成，project-audit 不得早于性能任务）
10. plan.md 行 409: `performance_probe` 出口快照字段
11. plan.md 行 433-434: 主链末尾包含性能回归与优化任务
12. plan.md 行 497: 校验项 "性能回归与优化任务 是否已作为真实 Trellis task 出现，并位于主干之后"
13. plan.md 行 515: 目录树示例含性能任务

**完整性**: 从强制要求、确认门禁、依赖排序、模板示例、出口校验、快照字段共 6 层覆盖，确保性能优化子任务不会被遗漏。

**与上次对比变化**: 无变化，维持已满足状态

---

#### #25: 使用原生 trellis agents

**是否满足**: ✅ 已满足

**证据**:

1. CLI原生适配边界矩阵.md: "Trellis 0.5 已原生提供 trellis-research / trellis-implement / trellis-check agents，覆盖 9 个平台"
2. workflow-installed.json: `managed_enhanced_agents: ["research"]` -- 仅 research 为托管增强代理
3. workflow_assets.py 行 109: `MANAGED_ENHANCED_AGENT_NAMES = ["research"]` -- implement/check 不在增强列表
4. workflow_assets.py 行 108: `LEGACY_AGENT_NAMES = ["research", "implement", "check"]` -- legacy 迁移覆盖三者
5. 三个平台代理文件全部使用 `trellis-*` 前缀（Trellis 0.5 命名规范）:
   - Claude: trellis-research.md / trellis-implement.md / trellis-check.md
   - OpenCode: trellis-research.md / trellis-implement.md / trellis-check.md
   - Codex: trellis-research.toml / trellis-implement.toml / trellis-check.toml
6. 三个平台的 agents/ 目录均含 `.backup-original/` 子目录（代理备份）
7. install-workflow.py 行 901-938: `_migrate_legacy_agents()` 处理 bare-name → trellis-* 迁移
8. install-workflow.py 行 941-963: `_deploy_enhanced_research_agent()` 仅部署增强版 research
9. implement 和 check 代理的主体语义来自 Trellis 原生，workflow 不做 overlay:
   - trellis-implement.md: 标准实现代理（含 Recursion Guard、Context Loading Protocol）
   - trellis-check.md: 标准检查代理（含 Self-fix 工作流）
10. 边界矩阵明确说明："trellis-implement / trellis-check 的主体语义由 Trellis 上游维护，workflow 不修改"

**与上次对比变化**: 无变化，维持已满足状态

---

## Caveats / Not Found

1. **Codex trellis-research.toml 缺少搜索路由表**: Codex 版本的 developer_instructions 未包含 6 类搜索路由表和 MCP 工具优先级指引。这是 #21 的唯一缺口，但 Codex 子代理的工具可用性取决于父会话配置而非代理定义内的工具声明，因此该缺口影响的是行为引导而非功能可达性。

2. **install-workflow.py 安装后提示缺 README.en.md 提及**: 这是 #23 的残留低优先级缺口。design 命令内已有完整覆盖，实际进入 design 阶段的用户不会被遗漏，但安装时刻的即时提示缺失。
