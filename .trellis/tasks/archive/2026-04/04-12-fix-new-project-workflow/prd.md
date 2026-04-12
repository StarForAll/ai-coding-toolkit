# brainstorm: 修复新项目开发工作流

## Goal

在不立即改动实现的前提下，先分析并收敛 `docs/workflows/新项目开发工作流` 中与新项目初始化分支策略、`brainstorm`→`design` 之间的质量门禁、以及 Claude Code / OpenCode / Codex 原生适配边界相关的问题，形成一套最小充分、可验证的修正方案，待用户确认后再实施。

## What I Already Know

- 当前分析范围限定在 `docs/workflows/新项目开发工作流/` 目录及其关联安装/升级脚本、补丁文档、平台适配 README。
- 当前 workflow 明确要求三类 CLI 原生适配：Claude Code、OpenCode、Codex；并强调多 CLI 同装，但入口协议不同。
- `brainstorm` 已被定义为“保留 Trellis 原生需求发现主链 + workflow 门禁扩展”的合并命令。
- `design` 已把“自动化检查矩阵”“finish-work 项目化适配”“record-session 基线适配”定义为进入 `plan` 前的硬门禁。
- 当前文档与脚本里几乎没有“新项目默认主分支必须为 main”的明确规则或自动校验。
- 当前文档已把 SonarQube / SonarQube-like 质量平台作为检查矩阵示例，但没有把 `sonar-scanner` 提升为用户这次要求的固定门禁。
- `install-workflow.py` 当前负责多 CLI 分发、导入 `pack.requirements-discovery-foundation`、注入 `start` / `finish-work` / `record-session` 补丁，但没有分支名规范相关逻辑。
- `finish-work` 项目化补丁目前仍是占位式提醒，要求“由当前项目在 design 阶段补充真实命令”，尚未写死任何必须存在的扫描命令。

## Assumptions (Temporary)

- “新建目标项目本地的主分支和初始分支必须使用 main”应在使用该 workflow 的最开始阶段就进行检查与约束，而不是等到 `brainstorm` 阶段。
- 该规则主要针对 workflow 安装/初始化指导、阶段一前置校验与文档规范，不一定要求当前安装器强制改写一个已有内容的非 `main` 仓库。
- “如果该项目已经有了一定量的内容就不需要强制修改成 main 分支”可通过“已有提交历史/已有业务文件/非空仓库”之类的非破坏性判定来承载，优先做文档和校验提示，避免默认自动改分支。
- `sonar-scanner` 需要被定义为跨语言统一质量门禁的一部分，但实际项目 key/token/sources 等参数仍应由目标项目在 design 阶段项目化填写，而不是在 workflow 源资产里写死。
- 用户当前需要的是“分析 + 修改方案”，不是立刻改文档/脚本。

## Open Questions

- 是否只做最小范围修复（A/B 两项及必要联动文档/测试），还是顺手补一轮围绕 `main` 与 `sonar-scanner` 的升级兼容检测与安装器提示一致性。

## Requirements (Evolving)

- 明确新项目 workflow 对目标项目默认主分支/初始分支使用 `main` 的规则，并将该规则前移到 workflow 最开始阶段。
- 对已有一定内容的目标项目，不默认强制切换或改写为 `main`。
- 在 `brainstorm` 完成后进入 `design` 前，把 `sonar-scanner` 纳入全局测试/质量门禁要求。
- 该 Sonar 门禁适用于任意语言实现的目标项目。
- 修正必须保持 Trellis 核心工作流优先，并分别遵守 Claude Code / OpenCode / Codex 的原生承载格式。
- 输出只包含分析和修改方案，实施需要再次获得用户确认。

## Acceptance Criteria (Evolving)

- [ ] 能指出当前 workflow 中承载 A/B 两项规则的主定义文件、补充说明文件、安装/升级脚本和测试触点。
- [ ] 能给出不破坏 Trellis 基线命令合并策略的最小充分修正方案。
- [ ] 能说明 Claude Code / OpenCode / Codex 三类适配层为何不应被同一种命令协议硬套。
- [ ] 能说明 `main` 分支规则应如何区分“workflow 最开始阶段校验”“新仓库默认值”和“已有内容仓库不强改”。
- [ ] 能说明 `sonar-scanner` 应在哪个阶段冻结为项目门禁、在哪些资产中同步。

## Definition of Done (team quality bar)

- 输出结论、证据、风险和下一步建议。
- 给出明确的待改文件集合与修改策略。
- 不做未经确认的代码或文档实现改动。

## Out of Scope (explicit)

- 不在本轮直接修改 workflow 源资产、安装脚本或测试。
- 不替用户决定目标项目的 SonarQube `projectKey`、`SONAR_TOKEN` 或具体扫描参数值。
- 不把 Codex 强行改造成 `/trellis:xxx` 项目级命令目录模型。
- 不回填历史任务、历史 session 记录或已安装目标项目的既有业务分支结构。

## Technical Notes

- 重点文件：
  - `docs/workflows/新项目开发工作流/工作流总纲.md`
  - `docs/workflows/新项目开发工作流/命令映射.md`
  - `docs/workflows/新项目开发工作流/多CLI通用新项目完整流程演练.md`
  - `docs/workflows/新项目开发工作流/commands/brainstorm.md`
  - `docs/workflows/新项目开发工作流/commands/design.md`
  - `docs/workflows/新项目开发工作流/commands/finish-work-patch-projectization.md`
  - `docs/workflows/新项目开发工作流/commands/install-workflow.py`
  - `docs/workflows/新项目开发工作流/commands/upgrade-compat.py`
  - `docs/workflows/新项目开发工作流/commands/test_workflow_installers.py`
- 官方格式验证要点：
  - Claude Code 官方当前把 skills 作为主推荐形态，但保留 `.claude/commands/` 兼容；项目级 `.claude/agents/` 仍使用 Markdown + YAML frontmatter。
  - OpenCode 官方支持项目级 `.opencode/commands/*.md` 和 Markdown agent 文件，frontmatter 中可声明 `description`、`agent`、`model`、`mode`、`permission` 等字段。
  - Codex 官方当前仍以 `AGENTS.md`、`.agents/skills/`、`.codex/hooks.json` 为项目承载主线，skills 必须有 `SKILL.md` 且包含 `name` / `description`。

## Research Notes

### What similar / official tool docs confirm

- Claude Code：
  - `.claude/commands/` 仍兼容，但官方更推荐 skills。
  - `.claude/agents/` 使用 Markdown + YAML frontmatter 承载子代理。
- OpenCode：
  - 项目命令可以原生放在 `.opencode/commands/*.md`。
  - agent 也可用 Markdown 文件配置，并支持 `mode: subagent` 与权限声明。
- Codex：
  - `AGENTS.md` 是项目级长期规则入口。
  - 仓库级 skills 应放在 `.agents/skills/`。
  - hooks 通过 `<repo>/.codex/hooks.json` 发现。

### Constraints from our repo/project

- 当前 workflow 已明确采用“Claude/OpenCode 以项目命令为主，Codex 以 AGENTS + hooks + skills 为主”的分层模型。
- `start` / `finish-work` / `record-session` 采用 Trellis 基线 + workflow 注入补丁，不宜在本轮需求中破坏该继承关系。
- `brainstorm` 和 `check` 是合并命令，`design` / `plan` / `delivery` 等是 workflow 分发命令，修正时要避免把所有阶段都当作同一种资产。

### Feasible approaches here

**Approach A: 文档主定义收口 + 补丁占位升级 + 安装/测试轻校验**（Recommended）

- How it works:
  - 在 `工作流总纲` / `命令映射` / `feasibility.md` / `design.md` / walkthrough 中把“workflow 最开始阶段检查 `main` 分支”和 Sonar 门禁收口成一致规则。
  - 把 `finish-work` 项目化补丁从泛化提示升级为“必须显式包含 sonar-scanner”的项目化门禁模板。
  - 在安装器/升级兼容测试层补最小校验或提示，确保后续不会被升级覆盖或漂移。
- Pros:
  - 变更集中，风险可控。
  - 兼容 Trellis 基线和三类 CLI 当前承载模型。
  - 能把文档规则、命令门禁、补丁模板、测试覆盖串起来。
- Cons:
  - 需要同步多个说明文档和测试，文件面较广。

**Approach B: 只改主文档，不碰安装器/补丁**

- How it works:
  - 仅修改总纲、命令映射、walkthrough 和阶段命令说明。
- Pros:
  - 实施快。
- Cons:
  - `finish-work` 补丁、升级兼容和目标项目实际落地之间会继续断层，后续容易漂移。

**Approach C: 直接在安装器里做强制分支切换与 Sonar 注入**

- How it works:
  - 安装器在目标项目检测并尝试自动修分支、强写 Sonar 门禁占位。
- Pros:
  - 强执行。
- Cons:
  - 对已有项目过于侵入，且容易违反“已有一定内容不强改 main”的要求；不适合作为默认方案。

## Workflow Decisions

- Accuracy Status: 已可进入方案确认
- Complexity: L1
- Need More Divergence: 否
- Need Sub Tasks: 否
- Next Step: 向用户汇报分析与推荐方案，待确认后实施
