# PRD: 审计并修复可嵌入新项目工作流的强门禁残留缺口

## Goal

基于目标项目样本 `/tmp/trellis-0.5.17-2` 的实际嵌入结果，审计并修复 `docs/workflows/新项目开发工作流/` 中仍会导致安装后运行异常、提示冲突、入口歧义或回归缺口的真实问题。修复范围仅限该工作流源码目录及当前任务目录，确保后续嵌入到目标项目时行为更一致、更可验证。

## What I Already Know

- 当前仓库 `trellis -v` 为 `0.5.17`，与 `commands/workflow_assets.py` 中 `COMPATIBLE_TRELLIS_VERSION = "0.5.17"` 一致，版本门禁通过。
- 用户给出的 6 类问题中，至少已有两类在 `/tmp/trellis-0.5.17-2` 中仍真实存在：
  - per-turn hook 仍优先把 `route.stage` 作为 breadcrumb body key，导致 `blocked` / `awaiting_confirmation_with_blockers` / `repair_needed` 等动作态继续复用普通 stage 正文，只在 header 补 Action/Blockers。
  - per-turn hook 在读取 `task.json.status` 为空时会直接放弃后续 `workflow-state.py route` 解析，`task.json.status` 仍是隐性前置条件。
- “完全没有自动化测试”这一判断已不成立。源码内已有：
  - `docs/workflows/新项目开发工作流/commands/test_workflow_installers.py`
  - `docs/workflows/新项目开发工作流/commands/shell/test_workflow_state.py`
- `implementation` 作为正式 stage 已存在于状态机、目标项目 `.trellis/workflow.md` 和路由产物中，但当前公开入口存在契约歧义：
  - 路由补丁文案写着 “use the skill matching the target field”
  - 实际并无 `implementation` 同名用户入口
  - 当前设计更像是通过 `trellis-continue` 自身的 `Implementation Entry` 小节重入 implementation

## Scope

- 只修改 `docs/workflows/新项目开发工作流/` 下源码与测试
- 可在当前任务目录写 `prd.md`、`audit-report.md`、研究记录
- 不修改仓库其他目录
- 不直接修改 `/tmp/trellis-0.5.17-2`，仅将其作为证据源与回归对照样本

## Non-Goals

- 不重构当前仓库自身 `.trellis/` 的运行时实现
- 不修改 Trellis 原生上游仓库
- 不做与本次真实缺陷无关的美化式“优化”

## Candidate Issues To Verify

1. `implementation` stage 是否存在真实的入口契约断裂，还是仅文案/映射歧义
2. 阻塞态与修复态是否缺少一等 breadcrumb 模板，导致 hook 注入信号冲突
3. `task.json.status` 是否仍被 hook / 任务视图 / 启动链路作为不必要的硬依赖
4. 分布式契约是否已通过测试/文档固化，若未固化应补哪类回归测试
5. `workflow-state.py route` 的子进程调用路径是否存在可低风险消减的重复开销
6. 是否存在与上述问题同类的相邻缺口，应一并修复

## Acceptance Criteria

- [ ] 对每个候选问题给出“真实缺陷 / 非缺陷 / 已被现有设计覆盖”的证据化结论
- [ ] 对真实缺陷在 `docs/workflows/新项目开发工作流/` 内完成修复
- [ ] 修复后的源码不会引入新的入口冲突或回退到 legacy `task.json.status` 主导模型
- [ ] 至少补充覆盖本次真实缺陷的自动化回归测试
- [ ] 运行相关测试并记录真实结果

## Technical Notes

- 重点文件：
  - `commands/install-workflow.py`
  - `commands/workflow-patch-projectization.md`
  - `commands/start-skill-patch-phase-router.md`
  - `commands/shell/patch-inject-workflow-state.py`
  - `commands/test_workflow_installers.py`
  - `commands/shell/test_workflow_state.py`
- 目标项目证据源：
  - `/tmp/trellis-0.5.17-2/.trellis/workflow.md`
  - `/tmp/trellis-0.5.17-2/.codex/hooks/inject-workflow-state.py`
  - `/tmp/trellis-0.5.17-2/.opencode/plugins/inject-workflow-state.js`
  - `/tmp/trellis-0.5.17-2/.agents/skills/trellis-start/SKILL.md`
  - `/tmp/trellis-0.5.17-2/.agents/skills/trellis-continue/SKILL.md`
