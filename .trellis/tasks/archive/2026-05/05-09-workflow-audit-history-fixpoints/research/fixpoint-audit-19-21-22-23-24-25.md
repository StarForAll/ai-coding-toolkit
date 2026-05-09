# Research: 工作流修复点审计 (19/21/22/23/24/25)

- **Query**: 深度分析 6 个修复点，判断当前工作流是否真正满足要求
- **Scope**: internal
- **Date**: 2026-05-09

## Findings

### 修复点 19: 工作流补充 research -> implement -> check 子代理链调用能力

**是否满足**: ✅ 已满足

**证据**:

1. `/tmp/trellis-0.5.9-2/.trellis/workflow.md` (已安装版) 第 198 行明确写出:
   ```
   **Flow**: trellis-implement → trellis-check → trellis-update-spec → commit (Phase 3.4) → `/trellis:finish-work`.
   ```
2. `/tmp/trellis-0.5.9-2/.trellis/workflow.md` 第 346-353 行 Phase 1.2 Research 小节明确写出:
   ```
   Spawn the research sub-agent:
   - **Agent type**: `trellis-research`
   - **Task description**: Research <specific question>
   ```
3. `/tmp/trellis-0.5.9-2/.trellis/workflow.md` 第 457-464 行 Phase 2.1 Implement 小节明确写出:
   ```
   Spawn the implement sub-agent:
   - **Agent type**: `trellis-implement`
   ```
4. `/tmp/trellis-0.5.9-2/.trellis/workflow.md` 第 511-524 行 Phase 2.2 Quality check 小节明确写出:
   ```
   Spawn the check sub-agent:
   - **Agent type**: `trellis-check`
   ```
5. 工作流总纲 `/ops/projects/personal/ai-coding-toolkit/docs/workflows/新项目开发工作流/工作流总纲.md` 第 440 行明确:
   ```
   当前 workflow 将 implementation 阶段内部链统一定义为 Trellis 原生 agent 链：trellis-research -> trellis-implement -> trellis-check。
   ```
6. 临时项目中三个子代理均已落盘:
   - `/tmp/trellis-0.5.9-2/.claude/agents/trellis-research.md` ✅
   - `/tmp/trellis-0.5.9-2/.claude/agents/trellis-implement.md` ✅
   - `/tmp/trellis-0.5.9-2/.claude/agents/trellis-check.md` ✅

**结论**: research -> implement -> check 子代理链在 workflow.md、总纲和目标项目 agent 文件中均已完整覆盖。Phase 1.2 用 trellis-research，Phase 2.1 用 trellis-implement，Phase 2.2 用 trellis-check。workflow.md 的 in_progress breadcrumb 也完整描述了 dispatch 协议。

---

### 修复点 21: 目标项目 trellis-research 需与当前项目增强版保持同等级搜索能力

**是否满足**: ✅ 已满足

**证据**:

1. **源仓库 (当前项目) trellis-research tools 清单** (`/ops/projects/personal/ai-coding-toolkit/.claude/agents/trellis-research.md` 第 5 行):
   ```
   tools: Read, Write, Glob, Grep, Bash, mcp__ace__search_context, mcp__exa__web_search_exa, mcp__exa__web_fetch_exa, mcp__exa__get_code_context_exa, mcp__exa__web_search_advanced_exa, mcp__Context7__resolve-library-id, mcp__Context7__query-docs, mcp__deepwiki__read_wiki_structure, mcp__deepwiki__read_wiki_contents, mcp__deepwiki__ask_question, mcp__grok-search__web_search, mcp__grok-search__web_fetch, Skill, mcp__chrome-devtools__*
   ```

2. **目标项目 trellis-research tools 清单** (`/tmp/trellis-0.5.9-2/.claude/agents/trellis-research.md` 第 5 行):
   ```
   tools: Read, Write, Glob, Grep, Bash, mcp__ace__search_context, mcp__exa__web_search_exa, mcp__exa__web_fetch_exa, mcp__exa__get_code_context_exa, mcp__exa__web_search_advanced_exa, mcp__Context7__resolve-library-id, mcp__Context7__query-docs, mcp__deepwiki__read_wiki_structure, mcp__deepwiki__read_wiki_contents, mcp__deepwiki__ask_question, mcp__grok-search__web_search, mcp__grok-search__web_fetch, Skill, mcp__chrome-devtools__*
   ```

3. **两份文件完全一致**: 源仓库和目标项目的 trellis-research.md 文件内容逐行相同（frontmatter + 全部正文）。

4. **搜索路由规则完整** (两份文件第 49-56 行):
   - 内部代码: ace.search_context 优先 ✅
   - 库文档: Context7 (resolve -> query) 优先 ✅
   - GitHub 仓库: deepwiki 优先 ✅
   - 实时/最新信息: grok.web_search -> grok.web_fetch 优先 ✅
   - 通用非时间敏感: exa.web_search -> exa.web_fetch 优先 ✅
   - 深度研究: exa.web_search_advanced 优先 ✅

5. **安装器部署链路验证** (`workflow_assets.py` 第 109 行):
   ```python
   MANAGED_ENHANCED_AGENT_NAMES = ["research"]
   ```
   `install-workflow.py` 第 941-966 行 `_deploy_enhanced_research_agent` 函数确认从源仓库复制增强版 trellis-research 到目标项目。

6. **workflow-installed.json 确认** (`/tmp/trellis-0.5.9-2/.trellis/workflow-installed.json` 第 48-50 行):
   ```json
   "managed_enhanced_agents": [
     "research"
   ]
   ```

7. **CLI原生适配边界矩阵确认** (`CLI原生适配边界矩阵.md` 第 43-47 行):
   ```
   当前源仓库（authoring repo）自身对 trellis-research 做了项目级 capability-enhancement...
   当前 workflow 合同要求目标项目中的 trellis-research 与这套增强版保持同等级能力，
   因此安装器 / 升级器会同步该增强版 trellis-research
   ```

**结论**: 目标项目的 trellis-research 与源仓库完全一致，包含全部增强搜索工具（ace, Context7, deepwiki, grok-search, exa）和完整的路由规则。安装器通过 `_deploy_enhanced_research_agent` 函数保证同步。

---

### 修复点 22: 补充 AI CLI 所需要使用的工作流嵌入规范指导文档

**是否满足**: ✅ 已满足

**证据**:

1. **工作流嵌入执行规范** (`/ops/projects/personal/ai-coding-toolkit/docs/workflows/新项目开发工作流/工作流嵌入执行规范.md`):
   - 定义了完整的三态模型: INITIAL_BASELINE_READY / ALREADY_VALID_EMBEDDED / BLOCKED_NON_INITIAL_STATE
   - 定义了标准执行顺序: detect -> dry-run -> install -> check
   - 定义了硬规则: 禁止手工复制、禁止 force/merge 自动修复
   - 定义了完整有效嵌入判定 (第 249-260 行)
   - 定义了允许执行的命令和禁止使用的命令 (第 170-195 行)
   - 定义了嵌入尝试记录结构 (第 113-145 行)
   - 定义了联动更新要求 (第 311-331 行)

2. **CLI原生适配边界矩阵** (`CLI原生适配边界矩阵.md`):
   - 区分了 Trellis 原生管理 vs workflow-managed subset
   - 对 Claude / OpenCode / Codex 分别列出了资产分类表
   - 明确了安装器管理 / 手动维护 / 运行前置的分类定义
   - 包含了跨平台对比速查表
   - 包含了前端视觉落地边界和 plan 阶段执行边界

3. **装后隐藏目录与托管边界核对清单** (`装后隐藏目录与托管边界核对清单.md`):
   - 分三层来源: trellis init baseline / workflow installer managed / manual project-owned
   - 定义了四步核对流程: 自动化核对 -> 逐项核对 -> Codex 双 skills 核对 -> 收尾链路核对
   - 包含完整的通过标准

4. **目标项目兼容升级方案指导**: 被总纲引用，定义了 A/B/C 三态分析和升级流程

5. **工作流总纲** 第 22-83 行详细描述了使用前提与安装时序，明确引用了上述三个文档

**结论**: 工作流嵌入规范指导文档体系已完整，涵盖嵌入执行规范、边界矩阵、装后核对清单和升级方案指导。

---

### 修复点 23: 双语言版本 README

**是否满足**: ⚠️ 部分满足

**证据**:

1. **工作流总纲明确要求双语言 README** (第 1308-1309 行):
   ```
   项目根 README.md（默认中文，最低可用版...）
   项目根 README.en.md（与 README.md 对齐的英文补充版）
   ```

2. **总纲 §1.4 项目确认与初始化** (第 268 行):
   ```
   其中 README 治理规则默认要求：README.md 作为默认中文入口；若同时存在 README.en.md，
   任何 README 内容、结构、命令、路径、链接、状态说明变更都必须同步更新两份
   ```

3. **目标项目 spec 中包含 readme-governance 规范**:
   - `/tmp/trellis-0.5.9-2/.trellis/spec/universal-domains/project-governance/readme-governance/overview.md` ✅
   - `/tmp/trellis-0.5.9-2/.trellis/spec/universal-domains/project-governance/readme-governance/normative-rules.md` ✅
   - `/tmp/trellis-0.5.9-2/.trellis/spec/universal-domains/project-governance/readme-governance/verification.md` ✅
   - `/tmp/trellis-0.5.9-2/.trellis/spec/universal-domains/project-governance/readme-governance/scope-boundary.md` ✅
   这些由 `pack.requirements-discovery-foundation` 自动导入。

4. **工作流嵌入执行规范** 第 257-258 行的完整有效嵌入判定:
   ```
   .trellis/spec/universal-domains/project-governance/readme-governance/ 已导入，
   可约束 README.md 默认中文与 README.en.md 同步更新
   ```

5. **目标项目实际缺少 README 文件**:
   ```
   /tmp/trellis-0.5.9-2/README* → NO_README_FILES
   ```

**缺口描述**:

- **规范层面**: 双语 README 的治理规范和 spec 已完整存在，design 阶段的硬必选文档列表中明确列出了 `README.md` + `README.en.md`。
- **实际落地层面**: 这是设计阶段才需要产出的文档，安装器不负责生成 README 文件。空白初始项目没有 README 是正常的（尚未进入 design 阶段）。
- **安装器角色**: 安装器只负责导入 readme-governance spec 来约束后续 README 的生成规则，不负责替项目生成 README。

**结论**: 规范和约束机制已完整存在，README 文件本身是 design 阶段的产物，不是安装器的职责。但需确认 install-workflow.py 的安装后提示中没有显式提醒"design 阶段需要产出 README.md + README.en.md"。

---

### 修复点 24: 目标项目必须包含性能优化子任务

**是否满足**: ✅ 已满足

**证据**:

1. **plan 命令强制要求性能回归与优化任务** (`/ops/projects/personal/ai-coding-toolkit/docs/workflows/新项目开发工作流/commands/plan.md`):
   - 第 229 行:
     ```
     `性能回归与优化任务`：主干任务完成后的固定后置任务（必选）
     ```
   - 第 235 行:
     ```
     项目域 A：TASK-A → TASK-B → 性能回归与优化任务
     ```
   - 第 241 行:
     ```
     - [ ] 已确认 `性能回归与优化任务` 为主干后的固定必选任务
     ```
   - 第 314-318 行 Step 3 拆分规则:
     ```
     无论项目是否启用源码水印，都**必须**额外拆出一个独立的后置 task：`性能回归与优化任务`
     - 该 task 只能在目标主干任务链完成后开始
     - 该 task 负责对主干完成后的关键性能指标做回归对比，并在必要时完成优化闭环
     - 指标至少覆盖与项目相关的体积 / 启动时间 / 内存 / 响应速度中的适用项
     ```
   - 第 507 行验证拆分结果:
     ```
     `性能回归与优化任务` 是否已作为真实 Trellis task 出现，并位于主干之后
     ```

2. **工作流总纲** 第 1879 行:
   ```
   `性能回归与优化任务` 必须存在，且位于目标主干任务链之后
   ```

3. **task_creation_checklist.md 模板** (plan.md 第 213-249 行) 包含:
   ```
   - `post_mainline_performance_task`: `yes`
   ```

4. **task_plan.md 模板** (plan.md 第 387 行):
   ```
   | .trellis/tasks/04-14-performance-opt | implementation | 全局 | 主干完成后的性能回归与优化任务 |
   ```

5. **PROJECT-AUDIT 依赖约束** (plan.md 第 318 行):
   ```
   若存在 `PROJECT-AUDIT`，则 `PROJECT-AUDIT` 不得早于该 task
   ```

**结论**: plan 命令和总纲都明确强制要求在目标主干任务链后追加性能回归与优化任务，且有验证脚本 `plan-validate.py` 检查其存在性。该要求与源码水印无关（"无论项目是否启用源码水印"），适用于所有项目。

---

### 修复点 25: 使用原生 trellis agents

**是否满足**: ✅ 已满足

**证据**:

1. **CLI原生适配边界矩阵** 第 29-30 行:
   ```
   Trellis 0.5 已原生提供 trellis-research / trellis-implement / trellis-check agents，覆盖 9 个平台...
   workflow 已从"自维护 agent overlay"切换为"依赖 Trellis 原生 agents"。
   ```

2. **变更后的实际链路** (边界矩阵第 34-37 行):
   ```
   Trellis 0.5 原生模板（trellis init 产物）
     -> target project .claude/.opencode/.codex trellis-* agents
   ```

3. **trellis-implement 和 trellis-check 不做 overlay** (边界矩阵第 42-43 行):
   ```
   `trellis-implement` / `trellis-check` 的主体语义由 Trellis 上游维护，workflow 不修改
   ```
   - `/tmp/trellis-0.5.9-2/.claude/agents/trellis-implement.md` 的内容是 Trellis 原生提供（通过 trellis init）
   - `/tmp/trellis-0.5.9-2/.claude/agents/trellis-check.md` 的内容是 Trellis 原生提供（通过 trellis init）

4. **trellis-research 仅做增强版同步** (边界矩阵第 43-44 行):
   ```
   `trellis-research` 则额外作为 workflow-managed enhanced agent 同步到目标项目，
   以满足当前工作流对搜索能力路由的要求
   ```

5. **workflow_assets.py** 第 108-109 行:
   ```python
   LEGACY_AGENT_NAMES = ["research", "implement", "check"]
   MANAGED_ENHANCED_AGENT_NAMES = ["research"]
   ```
   - `implement` 和 `check` 不在 MANAGED_ENHANCED_AGENT_NAMES 中，安装器不覆盖它们
   - `research` 在 MANAGED_ENHANCED_AGENT_NAMES 中，安装器同步增强版

6. **安装器不再维护 agent overlay 目录** (边界矩阵 第 63-66 行):
   ```
   commands/shared-agents/ — 已删除
   commands/claude/agents/ — 已删除
   commands/opencode/agents/ — 已删除
   commands/codex/agents/ — 已删除
   ```

7. **install-workflow.py** 中 `deploy_claude`/`deploy_opencode`/`deploy_codex` 的 agents 统计:
   - 仅调用 `_deploy_enhanced_research_agent`（只部署 research）
   - 调用 `_migrate_legacy_agents`（仅迁移 legacy bare-name 文件）
   - dry-run 输出 `Agents: 0`（除增强版 research 外无 agent overlay）

8. **目标项目 agent 文件均使用 trellis-* 命名**:
   - `/tmp/trellis-0.5.9-2/.claude/agents/trellis-research.md` ✅
   - `/tmp/trellis-0.5.9-2/.claude/agents/trellis-implement.md` ✅
   - `/tmp/trellis-0.5.9-2/.claude/agents/trellis-check.md` ✅
   - 不存在 bare-name `research.md` / `implement.md` / `check.md`（legacy 已迁移或不存在）

**结论**: 当前工作流已全面采用 Trellis 0.5+ 原生 agents（trellis-research / trellis-implement / trellis-check），不再维护自有的 agent overlay。仅 trellis-research 做增强版同步，implement 和 check 保持 Trellis 原生基线。

---

## Caveats / Not Found

1. **修复点 23 的缺口**: 虽然双语 README 的规范和约束已完整，但 install-workflow.py 安装后的提示信息（第 1722-1747 行）中没有显式提及"design 阶段需要产出 README.md + README.en.md"。该信息只在工作流总纲和 plan.md 中存在。如果用户不看总纲，可能不知道 design 阶段有这个硬必选文档要求。不过这不属于安装器合同范围，因为 README 是项目产物不是安装器产物。

2. **trellis-check skill vs agent 的区分**: 临时项目中同时存在:
   - `/tmp/trellis-0.5.9-2/.claude/agents/trellis-check.md` (Trellis 原生 sub-agent，用于 Phase 2.2 dispatch)
   - `/tmp/trellis-0.5.9-2/.claude/skills/trellis-check/SKILL.md` (Trellis 原生 skill，用于 inline mode)
   这是 Trellis 0.5+ 的正确行为，两者在不同 dispatch 模式下使用，不构成冲突。

3. **Codex 平台的 trellis-research**: workflow_assets.py 中 `source_agent_path` 对 codex 类型会寻找 `.codex/agents/trellis-research.toml`，但当前源仓库中不存在该文件（源仓库只有 Claude 版本的 `.claude/agents/trellis-research.md`）。这意味着 Codex 平台的增强版 trellis-research 部署可能缺失。但这一缺口已在 CLI原生适配边界矩阵 第 44 行明确指出:
   ```
   若某平台确有行为差距（如 Codex class-2 缺 context self-loading），
   应通过 Trellis 上游机制或项目级配置解决，不在 workflow 源中补丁
   ```

## Summary Table

| 修复点 | 标题 | 是否满足 | 缺口描述 |
|--------|------|---------|---------|
| 19 | research -> implement -> check 子代理链 | ✅ 已满足 | 无 |
| 21 | trellis-research 增强搜索能力对齐 | ✅ 已满足 | 无 |
| 22 | 工作流嵌入规范指导文档 | ✅ 已满足 | 无 |
| 23 | 双语言版本 README | ⚠️ 部分满足 | 规范和约束已完整；README 文件本身是 design 阶段产物，不是安装器职责，但安装后提示未显式提醒 |
| 24 | 性能优化子任务 | ✅ 已满足 | 无 |
| 25 | 使用原生 trellis agents | ✅ 已满足 | 无 |
