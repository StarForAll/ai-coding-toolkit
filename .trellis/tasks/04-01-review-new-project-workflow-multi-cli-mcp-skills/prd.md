# brainstorm: 审查新项目工作流多 CLI 与 MCP/Skills 适配

## Goal

在不修改文件的前提下，分析 `./docs/workflows/新项目开发工作流/` 当前文档体系是否已经满足以下目标：一是原生适配 Claude Code / Codex / OpenCode；二是命令易于触发，支持自然语言触发，并在每次对话输出中明确推荐下一个 Trellis 命令；三是提升已有 MCP 与 skills 的使用率。基于现状给出“已满足 / 部分满足 / 不满足”的判断、证据和后续修复建议，待用户确认后再进入修改阶段。

## What I already know

* 分析范围限定为 `./docs/workflows/新项目开发工作流/`
* 用户明确要求先分析，未确认前不得修改
* `命令映射.md` 已声明多 CLI 同装原则，并区分 Claude Code / OpenCode / Codex 的入口模型
* `工作流总纲.md` 已有 MCP / skills 的渐进性披露与配置分层原则
* `commands/claude/README.md`、`commands/opencode/README.md`、`commands/codex/README.md` 已分别描述三类 CLI 的原生承载方式
* 当前尚未确认“自然语言触发词”“每轮推荐下一条 Trellis 命令”“更强 MCP / skills 使用率”是否在主文档链路中形成完整闭环

## Assumptions (temporary)

* 本轮主要输出诊断结论与修复建议，不执行文档改写
* “满足”不仅看是否单点提到，还要看是否在主阅读路径中清晰、可执行、低歧义
* “加强 MCP / skills 使用率”需要体现为文档中的显式路由、阶段建议、触发规则或默认优先级，而不仅是原则性提及

## Open Questions

* 用户对“每次对话都输出下一个推荐执行的 Trellis 命令”期望的是主 workflow 文档要求，还是各 CLI 适配文档/命令模板都必须硬性规定？

## Requirements (evolving)

* 审查 `新项目开发工作流` 主文档与 CLI 适配文档的实际覆盖情况
* 对三类目标分别给出满足度判断和证据
* 识别主链路中的缺口、歧义、信息分散点和可能的修复位点
* 在用户确认前不修改任何范围内文件

## Acceptance Criteria (evolving)

* [ ] 给出三类目标的现状判断：已满足 / 部分满足 / 不满足
* [ ] 每项判断都能指向具体文档证据
* [ ] 明确指出若要修复，优先应改哪些文档、改什么内容
* [ ] 在用户确认前保持仓库文件不变

## Definition of Done (team quality bar)

* 结论基于仓库实际文件而非记忆
* 结论中区分“已有原则”与“可执行落地”
* 明确说明未做修改、未运行验证类命令
* 若后续进入修改，能直接基于本 PRD 收敛为实现任务

## Out of Scope (explicit)

* 本轮不修改 `./docs/workflows/新项目开发工作流/` 下的任何文件
* 本轮不扩展到其他 workflow 目录做重构
* 本轮不调整运行时配置、hooks、skills 本体或 CLI 安装脚本行为，除非仅作为分析证据引用

## Technical Notes

* 已读取/定位：
  * `docs/workflows/新项目开发工作流/工作流总纲.md`
  * `docs/workflows/新项目开发工作流/命令映射.md`
  * `docs/workflows/新项目开发工作流/多CLI通用新项目完整流程演练.md`
  * `docs/workflows/新项目开发工作流/commands/claude/README.md`
  * `docs/workflows/新项目开发工作流/commands/opencode/README.md`
  * `docs/workflows/新项目开发工作流/commands/codex/README.md`
  * `docs/workflows/新项目开发工作流/commands/install-workflow.py`
  * `docs/workflows/自定义工作流制作规范.md`
* 初步关注点：
  * 主链文档是否把三 CLI 原生承载差异讲清楚
  * 主链文档是否显式提供自然语言触发词与下一步推荐命令约束
  * MCP / skills 是停留在原则层，还是已进入阶段执行建议与默认路由

## Research Notes

### What the current workflow already does

* `多CLI通用新项目完整流程演练.md` 已作为第一入口，明确三类 CLI 入口差异，并为每个阶段列出推荐 MCP / skills 与降级方式
* `工作流总纲.md` 与 `命令映射.md` 已建立多 CLI 原生适配、能力路由优先级、渐进性披露、`[Evidence Gap]` 边界
* 各阶段命令文档已普遍包含：
  * 自然语言触发词
  * Cross-CLI 说明
  * MCP 能力路由
  * `下一步推荐` 区块
* `start-patch-phase-router.md` 已显式规定：
  * 触发词路由表
  * 歧义消解规则
  * 每个命令结束后必须输出 `下一步推荐`

### Constraints from the current docs structure

* 第一入口文档与命令正文、平台 README、patch 文档分层明显，能力存在但分散
* Codex 已被定义为 skills / AGENTS / hooks / subagents 模型，而非 `/trellis:xxx` 命令目录
* 不少“下一步推荐”示例仍以 `/trellis:xxx` 为统一写法，和 Codex 的原生 skill 入口存在表达层不完全对齐

### Preliminary assessment

**Approach A: 仅做结论性审查**（本轮执行）

* How it works:
  * 给出满足度判断、证据、缺口、修复位点
* Pros:
  * 符合“未确认前不修改”
  * 可直接作为下一轮修复输入
* Cons:
  * 不能立即消除文档中的表达不一致

**Approach B: 审查后进入最小修复**

* How it works:
  * 先确认修复方向，再最小改动主入口文档、命令映射和 Codex 相关表达
* Pros:
  * 能把“已有但分散”的规则前移到主阅读路径
* Cons:
  * 需要先明确你希望强化“主文档规范”还是“各阶段命令模板”
