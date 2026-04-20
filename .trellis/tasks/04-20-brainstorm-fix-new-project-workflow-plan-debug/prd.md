# brainstorm: 修复新项目开发工作流的 plan 与 debug agent 集成

## Goal

在不直接修改当前 workflow 的前提下，分析 `docs/workflows/新项目开发工作流` 与 Trellis 原生 `plan/debug` agent 的真实关系，给出一套以 Trellis 核心机制为前提、同时原生适配 Claude Code / OpenCode / Codex 的修正方案，待用户确认后再实施。

## What I already know

* 当前要分析和后续修改的范围限定在 `docs/workflows/新项目开发工作流/`
* 当前 workflow 已明确把 implementation 内部链定义为 `research -> implement -> check-agent`
* 当前 workflow 已明确把 `/trellis:plan` 定义为“真实 Trellis task 拆解 + 摘要型 `task_plan.md`”，并通过 `execution_authorized = false` 阻止未确认的执行态切换
* 当前 workflow 文档多处写明：`research / implement / check` 属于 workflow-managed subset，而 `debug` 仍是 Trellis / 项目侧手动维护能力
* 当前 workflow 历史分析曾明确写过“当前 workflow 不采用 Trellis 原生 `plan / dispatch agent`”，原因是其默认语义绑定 `dispatch` 自动执行链，与当前 workflow 的强门禁 + 用户确认模型冲突
* 在 `/tmp/trellis-workflow-plan-debug-analysis` 中用真实 `trellis init --claude --opencode --codex -y -u xzc` 初始化后，确认 Trellis 原生基线实际会落盘：
  * `.claude/agents/plan.md` / `.claude/agents/debug.md`
  * `.opencode/agents/trellis-plan.md` / `.opencode/agents/debug.md`
  * `.codex/hooks.json` + `.codex/hooks/session-start.py`
  * `.agents/skills/*` 与 `.codex/skills/parallel/SKILL.md`
  * `.trellis/scripts/task.py`、`.trellis/scripts/multi_agent/plan.py`、`.trellis/scripts/multi_agent/start.py`
* 原生 `plan agent` 的真实职责是：先评估需求，再生成任务目录、`prd.md`、`implement.jsonl`、`check.jsonl`、`debug.jsonl`，随后默认衔接 `dispatch`
* 原生 `debug agent` 的真实定位是：修复已发现问题；默认 `task.json.next_action` 不包含 `debug`，它属于 dispatch 失败/超时后的可选恢复分支，不是默认主链阶段
* `task.py init-context` 默认会创建 `implement.jsonl`、`check.jsonl`、`debug.jsonl`；其中默认 `debug.jsonl` 只注入 check 规范，说明 debug 的角色是“带着问题回修”，不是重新跑一遍完整研究

## Assumptions (temporary)

* 用户希望保留当前 workflow 的 task-first、强门禁、用户确认优先模型，不会回退到 Trellis 原生 `parallel/worktree/dispatch/create-pr` 自动流水线
* 用户希望“融入 Trellis Plan Agent 优点”，重点是复用其任务上下文装配能力，而不是引入其原生 dispatch 自动执行链
* 用户希望对 `debug agent` 做的是“是否纳入 workflow 明示模型”的判断，而不是简单把它加入默认链中

## Open Questions

* `plan` 阶段是否只吸收原生 plan agent 的“拒绝不清晰需求 + 预装配任务上下文”能力，而明确不吸收 `dispatch` 联动？
* `debug` 是否要在 workflow 中上升为“implementation 内部恢复分支”的显式能力，而不是保留为 README 里的手动维护说明？

## Requirements (evolving)

* 基于真实 `trellis init` 初始化结果与当前仓库现状做判断，不凭记忆猜测
* 方案必须优先维护 Trellis 核心机制，再做 Claude Code / OpenCode / Codex 原生格式适配
* 分析 A：提炼 Trellis 原生 plan agent 的有效优点，并设计如何吸收到当前 workflow 的 `/trellis:plan` 阶段
* 分析 B：判断 Trellis 原生 debug agent 是否值得纳入当前 workflow 使用模型，以及它应处于什么位置
* 在用户明确确认前，只输出分析与修改方案，不直接改 workflow 文件

## Acceptance Criteria (evolving)

* [ ] 给出基于 `/tmp` 真实初始化结果的 Trellis plan/debug 机制说明
* [ ] 说明当前 workflow 与 Trellis 原生 `plan / dispatch / debug` 的兼容与冲突点
* [ ] 给出 plan 阶段的推荐吸收方案，明确“保留什么 / 不引入什么 / 为什么”
* [ ] 给出 debug agent 的推荐定位，明确“默认主链 / 条件恢复分支 / 不纳入”的判断与理由
* [ ] 方案覆盖 Claude Code / OpenCode / Codex 三端原生适配边界

## Definition of Done (team quality bar)

* 仅完成分析与方案设计，不修改 workflow 正文
* 所有结论都能回溯到当前仓库文件或 `/tmp` 初始化实验
* 若涉及 Trellis 原生机制判断，必须明确是“当前 workflow 现状”还是“Trellis 基线行为”

## Out of Scope (explicit)

* 未经用户确认，不修改 `docs/workflows/新项目开发工作流/**`
* 不恢复 `parallel/worktree/dispatch/create-pr` 作为当前 workflow 默认主链
* 不把仓库根目录现有 Trellis live assets 直接重构成另一套 source 架构

## Technical Notes

* 当前关键文件：
  * `docs/workflows/新项目开发工作流/commands/plan.md`
  * `docs/workflows/新项目开发工作流/工作流总纲.md`
  * `docs/workflows/新项目开发工作流/CLI原生适配边界矩阵.md`
  * `docs/workflows/新项目开发工作流/commands/claude/README.md`
  * `docs/workflows/新项目开发工作流/commands/opencode/README.md`
  * `docs/workflows/新项目开发工作流/commands/codex/README.md`
* `/tmp` 验证项目：
  * `/tmp/trellis-workflow-plan-debug-analysis`
* 已验证的 Trellis 基线要点：
  * `trellis init` 会生成 plan/debug agent 与 hooks/skills/task 脚本
  * `task.py create` 默认 `next_action` 不含 `debug`
  * `task.py init-context` 默认创建 `debug.jsonl`
  * `multi_agent/plan.py` 的目标是为 dispatch 生产已配置好的 task directory
