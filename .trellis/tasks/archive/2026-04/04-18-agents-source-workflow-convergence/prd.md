# workflow agents 源定义：收敛 implementation 子代理链为工作流内单一 source-of-truth

## Goal

将当前散落在 `docs/workflows/新项目开发工作流/commands/{claude,opencode,codex}/agents/` 下的 workflow agent 定义，收敛为**工作流目录内**的单一 source-of-truth，建立统一的部署映射和同步规则，避免同一 workflow 内部出现多份 agent 定义长期双轨。

## What I already know

* 仓库当前已有一个上层任务：`.trellis/tasks/03-19-implement-agents-source/`，本任务已作为其子任务创建。
* 当前仓库的 `.claude/agents/`、`.opencode/agents/` 是 live deployment，不是当前 workflow 在目标项目里的真正 source-of-truth。
* 刚完成的 workflow 兼容修复，已经在 `docs/workflows/新项目开发工作流/commands/{claude,opencode,codex}/agents/` 下建立了 workflow 管理的 `research / implement / check` agent 源文件。
* 当前 workflow 已将 `research -> implement -> check-agent` 定义为 implementation 内部链；`plan / dispatch agent` 明确不采用。
* research agent 已确定统一规则：
  * 外部技术搜索优先 `exa`
  * 第三方库 / 框架 / SDK 官方文档必须先 `Context7`
  * 未经过 `Context7` 不得输出 API / 配置 / 版本结论
* Codex 的 `check.toml` 已确定需要按官方 `subagents` / `hooks` 边界对齐为可修复 check-agent 语义。

## Problem

当前仓库存在至少两层“agent 源定义”：

1. workflow 当前按 CLI 分散维护的 `docs/workflows/.../commands/*/agents/`
2. workflow 文档、安装器、升级脚本之间对这些 agents 的 source / adapter / target 边界

如果不继续收敛：

* agent 定义会继续双轨
* workflow 内部不同 CLI 目录下的 agent 定义会继续漂移
* 安装器 / 升级分析脚本与未来工作流内 source-of-truth 收敛方案会冲突

## Scope

本任务未来应覆盖：

* 设计 workflow agents 如何在 `docs/workflows/新项目开发工作流/commands/` 内收敛为单一 source-of-truth
* 明确 source-of-truth 与 deploy target 的边界
* 明确 `research / implement / check` 这组 agents 是否以仓库通用能力存在，还是以 workflow 变体存在
* 明确 Claude / OpenCode / Codex 三端 deployment adapter 的字段映射
* 明确从“按 CLI 分散 source”迁移到“工作流内单一 source”时的步骤和防漂移策略

## Out of Scope

* 当前 turn 不执行任何实现
* 当前任务不把 agent source 上收为仓库根 `agents/`
* 当前 turn 不回滚或删除 `docs/workflows/新项目开发工作流/commands/*/agents/`

## Key Inputs From Previous Task

来自 `.trellis/tasks/04-18-trellis-native-workflow-compat/` 的已确认结论：

* workflow 不采用 `plan / dispatch agent`
* `research / implement / check-agent` 是 implementation 内部角色链
* `.codex/agents/*.toml` 需要纳入 workflow 兼容治理
* Codex 不能照搬 Claude 的 hook 注入机制，但应对齐 agent 角色语义
* 三端 managed agents 目前已在 workflow 层形成 install / analyze-upgrade / upgrade-compat / uninstall / test 的闭环

## Expected Deliverables

* 一份清晰的收敛方案：
  * workflow 内部 source-of-truth 目录结构
  * workflow agents 与 per-CLI adapter 的关系
  * 迁移顺序
  * 部署与同步策略
  * 风险与回滚思路
* 必要时，再拆成后续实现子任务

## Decision Gates

在进入实现前，本任务需要把下列问题从“待讨论”收敛成明确决定：

1. `research / implement / check` 的唯一 source-of-truth 应放在 workflow 命令目录的哪一层：
   * 继续保留在各 CLI 子目录
   * 收敛到 `docs/workflows/新项目开发工作流/commands/` 下的共享 agent source 目录
   * 或“工作流内主体 + 各 CLI 薄适配层”
2. workflow 子目录中的 agent 文件在收敛后保留什么角色：
   * 可编辑源文件
   * 由 workflow 内共享主体派生的 deploy adapter
   * 仅作为 installer 打包输入的镜像副本
3. Codex `.toml` agent 与 Claude/OpenCode `.md` agent 的差异：
   * 只是 deploy 格式差异
   * 还是语义合同也需要单独维护
4. `workflow_assets.py`、安装器、升级分析脚本应如何识别新的 source-of-truth，避免再出现双轨维护。

## Acceptance Criteria

* [ ] PRD 明确写出 `research / implement / check` 的唯一 source-of-truth 归属，不再保留双义描述。
* [ ] PRD 明确写出 workflow source、workflow adapter、target-project deployment 三层之间的边界与职责。
* [ ] PRD 给出 Claude / OpenCode / Codex 的部署映射规则，并显式说明 Codex `.toml` 的特殊点。
* [ ] PRD 给出迁移顺序，至少覆盖：工作流内 source 落位、workflow adapter 调整、installer / analyze-upgrade / upgrade-compat 对齐、文档与测试更新。
* [ ] PRD 列出防漂移机制，至少说明哪些文件或脚本必须一起更新、由什么验证命令证明一致性。
* [ ] 若无法在单任务内完成实现，PRD 要给出可拆分的后续子任务边界。
* [ ] `docs/workflows/新项目开发工作流` 目录内新增或修改的 agent 相关内容，必须保证目标项目在先执行 `trellis init`，再嵌入当前 workflow 后，`research -> implement -> check` 子代理链仍可正常安装、恢复、升级与使用。

## Definition of Done

* 任务元数据已补齐：`description`、`dev_type`、`scope`、`relatedFiles` 不再为空壳。
* 任务 context 文件已初始化并补充关键参考路径，可直接支撑 brainstorm / research。
* 当前 PRD 已把“目标、边界、决策点、验收条件、迁移面”写成可讨论、可验证的文本，而不是仅有方向性描述。

## Technical Notes

关键参考路径：

* 当前 workflow agents：
  * `docs/workflows/新项目开发工作流/commands/claude/agents/`
  * `docs/workflows/新项目开发工作流/commands/opencode/agents/`
  * `docs/workflows/新项目开发工作流/commands/codex/agents/`
* 当前 live deployments：
  * `.claude/agents/`
  * `.opencode/agents/`
* 兼容治理脚本：
  * `docs/workflows/新项目开发工作流/commands/install-workflow.py`
  * `docs/workflows/新项目开发工作流/commands/workflow_assets.py`
  * `docs/workflows/新项目开发工作流/commands/analyze-upgrade.py`
  * `docs/workflows/新项目开发工作流/commands/upgrade-compat.py`

## Primary Impact Surface

后续 research / design 至少需要覆盖这些影响面：

* workflow agent 托管清单：`docs/workflows/新项目开发工作流/commands/workflow_assets.py`
* 三端 workflow agent 实例：
  * `docs/workflows/新项目开发工作流/commands/claude/agents/`
  * `docs/workflows/新项目开发工作流/commands/opencode/agents/`
  * `docs/workflows/新项目开发工作流/commands/codex/agents/`
* 与部署/升级强相关的脚本：
  * `docs/workflows/新项目开发工作流/commands/install-workflow.py`
  * `docs/workflows/新项目开发工作流/commands/analyze-upgrade.py`
  * `docs/workflows/新项目开发工作流/commands/upgrade-compat.py`
* 上层 blocked 任务与前置分析结论：
  * `.trellis/tasks/03-19-implement-agents-source/prd.md`
  * `.trellis/tasks/archive/2026-04/04-18-trellis-native-workflow-compat/prd.md`

## Research Findings

### Current Source-of-Truth Chain

当前 `research / implement / check` 的真实 source-of-truth 在 workflow 子目录：

```text
docs/workflows/新项目开发工作流/commands/{claude,opencode,codex}/agents/*
  -> install-workflow.py / upgrade-compat.py 直接读取这些文件
  -> 目标项目 .claude/agents / .opencode/agents / .codex/agents
```

关键事实：

* `install-workflow.py` 的 `src` 就是 `commands/` 目录本身，`source_agent_path()` 直接拼 `src / cli_type / "agents"` 读取源 agent。
* `upgrade-compat.py --check/--merge` 也把 workflow 子目录中的 agent 文件当作 expected content / redeploy source。
* `uninstall-workflow.py` 按 `MANAGED_IMPLEMENTATION_AGENTS = ["research", "implement", "check"]` 恢复或删除目标项目中的 managed agents。

### Real Managed Surface Today

当前 workflow-managed implementation agents 只覆盖三端：

* Claude: `research.md` / `implement.md` / `check.md`
* OpenCode: `research.md` / `implement.md` / `check.md`
* Codex: `research.toml` / `implement.toml` / `check.toml`

`iFlow` 不在当前 workflow-managed 合同面内。

### Semantic Reuse Already Exists

三端的 `research / implement / check` 主体语义已经高度一致：

* 都明确是 implementation 内部角色链，不等于正式 `/trellis:check`
* `implement` 都要求按 `.trellis/spec/`、PRD、设计约束落地
* `check` 都要求 scoped self-fix + rerun verification
* 新 workflow source 中的 `research` 已统一证据门禁：
  * 外部技术搜索优先 `Exa`
  * 第三方库 / 框架 / SDK 文档必须先 `Context7`
  * 无法确认时必须标记 `[Evidence Gap]`

真正的差异主要在：

* frontmatter / `.toml` 包装格式
* 权限字段表达
* 少量 context self-loading 文案

这说明它们更像“同一主体 + 平台适配层”，而不是三套独立源资产。

### Drift Reality In This Repo

仓库当前已经存在明显漂移：

* `.claude/agents/research.md`、`.opencode/agents/research.md`、`.codex/agents/research.toml` 仍保留较旧语义
* workflow 子目录中的 research agent 已升级到 `Exa + Context7 + [Evidence Gap]` 合同
* `.iflow/agents/*` 仍是另一套未纳入本次 workflow 兼容治理的老副本

因此当前至少同时存在：

1. 仓库 live deployments
2. workflow source copies
3. workflow 文档与脚本对 source / adapter / target 的不同抽象层

## Constraints

### Contract Constraints

若 source-of-truth 发生迁移，以下合同必须一起更新：

* `docs/workflows/新项目开发工作流/commands/install-workflow.py`
* `docs/workflows/新项目开发工作流/commands/upgrade-compat.py`
* `docs/workflows/新项目开发工作流/commands/uninstall-workflow.py`
* `docs/workflows/新项目开发工作流/commands/workflow_assets.py`
* `docs/workflows/新项目开发工作流/commands/test_workflow_installers.py`
* workflow 文档中的 CLI 边界矩阵与 Codex / OpenCode / Claude 说明

### Non-Negotiable Semantic Contracts

无论最终 source-of-truth 放在哪一层，至少要保留：

* `research` 的 `Exa-first` / `Context7-first` / `[Evidence Gap]` 证据门禁
* `check-agent` 与正式 `/trellis:check` 的显式边界
* installer / upgrade / uninstall 对 managed agents 的备份、漂移检测、恢复或删除合同
* 目标项目在 `trellis init` 后执行 `install-workflow.py`，必须仍能得到可用的 `research -> implement -> check` implementation 子代理链

## Feasible Approaches

### Approach A: Keep Workflow Directories As Canonical Source

做法：

* 继续把 `docs/workflows/.../commands/{cli}/agents/*` 视为唯一 source-of-truth
* 仓库级 `agents/` 继续空置或只做文档占位

优点：

* 对现有 installer / upgrade / uninstall / tests 冲击最小
* 不需要立刻设计新的 adapter 生成机制

缺点：

* 无法完成父任务“实现 `agents/` 源资产层”的目标
* workflow source 与仓库级 source-of-truth 永远无法合并
* 继续保留“workflow 子目录才是真正源层”的反直觉结构

结论：

* 仅适合作为短期维持现状，不满足本任务目标

### Approach B: Move Source To Workflow-Local Shared Agent Directory And Let Scripts Read It

做法：

* 将 `research / implement / check` 迁入 `docs/workflows/新项目开发工作流/commands/` 下的共享 agent source 目录
* installer / upgrade 从这层共享 source 读取并生成目标项目 agent 文件
* 各 CLI 子目录只保留 adapter 或镜像输入

优点：

* source-of-truth 最纯粹
* 不需要跨出 workflow 目录边界

缺点：

* 需要 installer / upgrade / tests 同时改成“从 tool-agnostic 源资产生成 tool-specific deploy content”
* 对当前 workflow 打包目录结构和回归测试冲击最大

结论：

* 架构最干净，但不适合作为第一步迁移

### Approach C: Workflow-Local Canonical Source + Per-CLI Adapter Copies

做法：

* 在 `docs/workflows/新项目开发工作流/commands/` 下建立 workflow-local canonical source
* `SYSTEM.md` / `README.md` / `TOOLS.md` 成为唯一主体语义来源
* workflow 子目录中的 `commands/{claude,opencode,codex}/agents/*` 改为派生 adapter：
  * 保留当前 installer / upgrade 读取路径
  * 但不再手工维护主体内容

优点：

* 满足“只在 workflow 目录内收敛 source-of-truth”的约束
* 保留 workflow 现有安装/升级合同的目录边界，降低第一阶段改造风险
* 将平台差异压缩到 adapter 层，而不是复制整份主体语义

缺点：

* 会暂时保留一层 workflow adapter 文件
* 需要明确“workflow-managed target subset”和“workflow-local shared source”的区别

结论：

* 这是当前最稳妥的推荐路径

## Recommended Direction

推荐采用 **Approach C: workflow-local canonical source + per-CLI adapter copies**。

推荐理由：

* 它同时满足两个目标：
  * 不越出 `docs/workflows/新项目开发工作流` 目录边界
  * 不破坏 workflow 当前已经跑通的 install / upgrade / uninstall / drift-check 闭环
* 它最符合现有证据：
  * 三端主体语义已经接近统一
  * 差异集中在平台包装层
  * workflow 现在已经有一套围绕 per-CLI agent 文件的稳定治理链，直接删除这层风险太高

### Recommended Boundary Model

建议收敛成下面这条链：

```text
docs/workflows/新项目开发工作流/commands/<shared-agent-source>/
  -> workflow adapter files under docs/workflows/.../commands/{claude,opencode,codex}/agents/
  -> target project managed agents (.claude/.opencode/.codex)
```

其中要明确：

* workflow 目录内共享 agent source 是唯一主体语义 source-of-truth
* workflow 子目录是 installer / upgrade 需要的打包适配层，不再手工写主体
* workflow 当前 managed subset 是 Claude / OpenCode / Codex
* `iFlow` 不属于当前 workflow-managed subset

## Proposed Migration Sequence

### Phase 1: Spec Alignment

* 明确 workflow-local source、per-CLI adapter、target deployment 三层边界
* 明确当前 managed subset 仍是 Claude / OpenCode / Codex

### Phase 2: Define Workflow-Local Shared Agent Source

在 `docs/workflows/新项目开发工作流/commands/` 下定义第一批共享 agent source 结构与字段契约。

### Phase 3: Define Adapter Generation Rules

明确如何从 `agents/<id>/` 生成：

* `docs/workflows/.../commands/{claude,opencode,codex}/agents/*`
* 目标项目 `.claude/agents/*`
* 目标项目 `.opencode/agents/*`
* 目标项目 `.codex/agents/*`

第一阶段可以先采用“手工同步 + 明确规则”，后续再补自动化脚本。

### Phase 4: Retarget Workflow Governance

让以下脚本和测试围绕新的 canonical source 工作：

* `workflow_assets.py`
* `install-workflow.py`
* `upgrade-compat.py`
* `uninstall-workflow.py`
* `test_workflow_installers.py`

策略上可分两步：

1. 先保留 workflow adapter 路径不变，只改变其来源
2. 再决定是否让 installer 直接从 workflow-local shared source 生成目标文件

### Phase 5: Clean Up Legacy Drift

* 对比并收敛 workflow 当前按 CLI 分散维护的 agent 正文
* 明确 `plan / dispatch / debug` 是否继续留在 workflow 外层手动维护状态

## Suggested Follow-Up Tasks

如果拆分实现，建议至少拆成：

1. **定义 workflow-local shared agent source**
2. **定义并执行 workflow adapter 同步**
3. **调整 installer / upgrade / uninstall / tests 到新 source-of-truth**
4. **评估 `debug / plan / dispatch` 的后续收敛策略**

## Current Status

* 任务已创建
* 已完成 brainstorm / research / 迁移前置合同收口
* workflow 目录内的 install / upgrade / uninstall agent 路径合同已集中到 `workflow_assets.py`
* 已验证当前修改满足一个关键要求：
  * 目标项目在 `trellis init` 后，补齐 workflow 前置条件并嵌入当前 workflow，仍可成功安装并使用 `research -> implement -> check` 子代理链
* 已完成 workflow-local shared source 落位：
  * `docs/workflows/新项目开发工作流/commands/shared-agents/research/`
  * `docs/workflows/新项目开发工作流/commands/shared-agents/implement/`
  * `docs/workflows/新项目开发工作流/commands/shared-agents/check/`
* workflow adapter 已切到从 workflow-local shared source 派生并部署到目标项目
* 本任务目标内的收敛已完成：
  * `research / implement / check` 已收敛为 workflow-local shared source
  * 三端 adapter 已由 shared source 派生
  * install / upgrade / uninstall / tests 已围绕这条 workflow-local source-of-truth 工作
* 不在本任务范围内的剩余事项：
  * 非 `research / implement / check` 的其他 agent（如 `debug`）仍未纳入本次收敛范围

## Current Judgment

针对“`docs/workflows/新项目开发工作流` 目录范围内补充的 agent 内容，需要保证目标项目使用 `trellis init` 初始化之后嵌入该 workflow 能够使用 `research -> implement -> check` 子代理链”这一要求，当前修改**满足要求**，且本任务范围内的收敛目标已完成。

判断依据：

* `commands/shared-agents/{research,implement,check}/` 已成为 workflow-local shared source。
* `workflow_assets.py` 已把 managed agent 的 source / target 路径合同集中化，并从 shared source 渲染三端 adapter。
* `install-workflow.py`、`upgrade-compat.py`、`uninstall-workflow.py` 已围绕这条 workflow-local source-of-truth 工作，没有引入对 workflow 目录之外路径的依赖。
* 关键 installer tests 已通过，完整 `test_workflow_installers.py` 回归也已通过。
* fresh `/tmp` 目标项目已实际验证：
  * `trellis init --claude --opencode --codex -y -u xzc`
  * 补齐 Git / `main` / `origin` 双 push URL 前置条件
  * 执行 `install-workflow.py`
  * 三端 `research / implement / check` managed agents 成功备份并部署
