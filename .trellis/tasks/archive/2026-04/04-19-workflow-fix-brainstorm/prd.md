# brainstorm: 新项目开发工作流修复完善

## Goal

分析并提出 `docs/workflows/新项目开发工作流` 的修复与完善方案，重点覆盖 Trellis 联动行为、Exa / Grok / Context7 / ACE 的路由一致性、多 CLI 原生适配边界，以及 workflow 安装后目标项目状态修复问题；当前阶段只输出分析、原因判断与建议修改方案，不直接修改 workflow 源文件。

## What I already know

* 用户明确限定分析与后续修改范围为 `docs/workflows/新项目开发工作流/`
* 涉及 Trellis 联动的判断需要先在 `/tmp` 新建临时项目并执行 `trellis init` 后再下结论
* 需要优先保证 Trellis 框架核心，再分别对齐 Claude Code / Codex / OpenCode 的官方原生适配方式
* 待分析点包括：
* A. `design` / `plan` / `feasibility` 中与 Exa 相关的使用配置需按当前系统提示词修正
* B. workflow 安装到 `trellis init` 后的目标项目时，`.trellis/.current-task` 仍指向已删除的 `00-bootstrap-guidelines`
* C. 若目标项目没有两个远程端点，需要在 workflow 中补充明确的 `git remote` 配置步骤
* D. 需要判断 research agent 搜索路由是否应从旧的 Exa-first / Context7-first 调整为与当前全局提示词一致的分层策略
* 已定位的关键文件包括：`commands/feasibility.md`、`commands/design.md`、`commands/plan.md`、`命令映射.md`、`多CLI通用新项目完整流程演练.md`、`.claude/agents/research.md`、`.opencode/agents/research.md`、`.codex/agents/research.toml`、`commands/install-workflow.py`、`commands/uninstall-workflow.py`、`commands/upgrade-compat.py`

## Assumptions (temporary)

* `.current-task` 残留问题大概率发生在安装器清理 bootstrap task 时没有同步修正当前任务指针或阶段状态
* 远程仓库双 push URL 目前更偏向“安装前置校验”，文档与报错提示可能不足，而不是缺少底层校验
* research agent 的实际改动范围可能不止 agent 文件本身，还会扩散到 walkthrough、命令映射、CLI 适配边界矩阵和安装文档

## Open Questions

* `trellis init` 后基线项目里 `00-bootstrap-guidelines` 的真实创建与 `.current-task` 写入路径是什么
* 安装当前 workflow 时，哪个具体步骤删除了 bootstrap task，但没有同步修正 `.current-task`
* Exa / Grok / Context7 / ACE 的现行全局路由与 workflow 文档中已有表述有哪些冲突点
* research agent 的路由修改是只调整文案与工具声明，还是要同步修改实际安装器分发内容与文档传播面

## Requirements (evolving)

* 先通过代码与文档调研列出 A-D 四项问题的现状与受影响文件
* 对涉及 Trellis 联动的问题，必须基于 `/tmp` 临时项目 + `trellis init` 的真实结果分析
* 给出兼容 Claude Code / Codex / OpenCode 原生格式、且以 Trellis 为主链的修正方案
* 当前阶段不修改 workflow 源文件，只形成可执行修改方案与影响面说明

## Acceptance Criteria (evolving)

* [ ] 列出 A-D 四项问题的现状、根因假设与证据来源
* [ ] 通过临时项目验证 Trellis init 与 workflow 安装相关的关键行为
* [ ] 给出每项问题的建议修正方式、涉及文件范围和跨 CLI 影响
* [ ] 在用户确认前不对 `docs/workflows/新项目开发工作流/` 做实现性修改

## Definition of Done (team quality bar)

* 分析结论有对应代码 / 文档 / 实证依据
* 明确区分“已验证事实”与“基于现有证据的推断”
* 对修改方案给出最小改动原则与传播范围
* 标注需要用户确认的决策点

## Out of Scope (explicit)

* 当前阶段不直接改 workflow 文件
* 当前阶段不处理 `docs/workflows/新项目开发工作流/` 之外的无关资产重构
* 当前阶段不做提交、发布或 task 执行阶段切换

## Technical Notes

* 已读关键源码：`docs/workflows/新项目开发工作流/commands/install-workflow.py`、`docs/workflows/新项目开发工作流/commands/uninstall-workflow.py`、`docs/workflows/新项目开发工作流/commands/upgrade-compat.py`
* 已定位关键文档：`commands/feasibility.md`、`commands/design.md`、`commands/plan.md`、`命令映射.md`、`多CLI通用新项目完整流程演练.md`、`CLI原生适配边界矩阵.md`
* 已定位研究代理定义：`.claude/agents/research.md`、`.opencode/agents/research.md`、`.codex/agents/research.toml`

## Research Notes

### `/tmp` 实证结果

* 纯净 `trellis init --claude --opencode --codex -y -u xzc` 之后，目标项目默认不会生成 `.trellis/.current-task`，也不会生成 `workflow-installed.json`
* 运行 `.trellis/scripts/create_bootstrap.py fullstack` 后，会创建 `.trellis/tasks/00-bootstrap-guidelines/`，并把 `.trellis/.current-task` 写成 `.trellis/tasks/00-bootstrap-guidelines`
* 满足 Git 前置条件后运行当前 workflow 的 `install-workflow.py`，会：
* 正常导入 `pack.requirements-discovery-foundation`
* 删除 `.trellis/tasks/00-bootstrap-guidelines/`
* 但不会清理 `.trellis/.current-task`
* 因此安装完成后会留下指向已删除 bootstrap task 的悬空指针

### 已确认问题

* `install-workflow.py` 的 `remove_bootstrap_task()` 只删除任务目录，不处理 `.trellis/.current-task`
* Claude / Codex 的 session-start hook 都会把这种状态识别为 `STALE POINTER`
* 当前 workflow 的高层路由文档已基本按 `ace / Context7 / grok / exa / deepwiki` 分层，但 workflow-local research agent 与 CLI README 仍保留“外部技术搜索优先 exa”的旧表述
* `design.md` 与 `feasibility.md` 已使用 `exa_web_search_advanced_exa(type=deep-reasoning)`，但仍缺少对“实时最新信息优先 grok-search、官方文档先 Context7、Exa 只用于深度研究”的更细边界说明
* `plan.md` 本体没有 Exa-first 问题；其当前重点仍是 `project-planner` / `writing-plans` / `sequential-thinking` / `ace.search_context`
