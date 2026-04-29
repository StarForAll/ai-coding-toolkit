# 修复新项目开发工作流分析

## Goal

分析 `docs/workflows/新项目开发工作流` 在真实目标项目中的当前行为，判断用户提出的 README、性能优化子任务、plan 阶段强门禁等问题是否真实存在，并给出符合 Trellis 核心约束且原生适配 Claude Code / Codex / OpenCode 的修改方案。

## What I already know

- 分析范围限定在 `docs/workflows/新项目开发工作流/`
- 需要先在 `/tmp` 创建临时项目，执行 `trellis init`，再嵌入当前 workflow 做实际验证
- 本轮只做分析和修改方案，不直接修改工作流文件
- 用户关注的候选优化点包括：
- README 需要中英双语，默认 `README.md` 为中文
- 是否存在“项目水印子任务之后补充性能优化子任务”的缺口
- `plan` 阶段必须只做规划与 Trellis task 创建准备，不能进入任何实现；真实创建任务前必须有人工确认清单
- 用户已明确新增约束：无论是否启用项目水印，`性能回归与优化任务` 都必须存在，且必须在目标主干任务完成之后执行
- 已按工作流嵌入协议在 `/tmp/trellis-workflow-probe.pIZ5iM` 完成 `git init`、`trellis init --claude --opencode --codex`、`detect-embed-state.py`、`install-workflow.py`、`upgrade-compat.py --check` 全链路验证
- 临时项目在安装前状态为 `INITIAL_BASELINE_READY`，安装后状态为 `ALREADY_VALID_EMBEDDED`
- 安装层已实际分发 Claude / OpenCode 命令、Codex skills、workflow helper scripts 与 AGENTS 路由块，说明三 CLI 原生适配链当前可落盘

## Assumptions (temporary)

- 当前 workflow 已具备安装脚本，可嵌入到纯净 Trellis 项目中
- 相关行为可能分散在总纲、阶段命令、校验脚本、平台 README 与安装器中，需要交叉核对

## Open Questions

- README 双语要求需要作为所有目标项目的默认硬约束，还是只在特定类型项目启用

## Requirements (evolving)

- 基于 workflow 源文档、安装器、校验脚本和临时目标项目实际嵌入结果做判断
- 逐项说明问题是否存在、证据位置、影响范围
- 对真实存在的问题给出修改思路，并说明需要同步更新的文档/脚本/平台适配面
- 保持 Claude Code / OpenCode / Codex 原生适配承载方式不被破坏，优先遵守 Trellis 核心阶段机与安装协议

## Acceptance Criteria (evolving)

- [ ] 给出 README / 性能优化子任务 / plan 阶段门禁 三项的存在性判断
- [ ] 每项判断都有对应文件或临时项目行为作为证据
- [ ] 给出不直接落地修改的修正方案草案，等待用户确认

## Definition of Done (team quality bar)

- 结论基于实际源文件与临时项目验证，不凭记忆推断
- 明确列出已完成、未完成、风险和后续修改面
- 若本轮未运行某些验证，需明确写出原因与建议命令

## Out of Scope (explicit)

- 本轮不直接修改 workflow 源文件、安装器或校验脚本
- 本轮不提交 commit，不做最终实现

## Technical Notes

- 目标目录：`docs/workflows/新项目开发工作流/`
- 重点入口预计包括：`工作流总纲.md`、`命令映射.md`、`commands/*.md`、`commands/install-workflow.py`、`commands/shell/plan-validate.py`、平台 README
- 当前已确认事实：
- A. 当前 design 阶段只要求生成项目根 `README.md`，未要求 `README.en.md` 或中英双版本；`workflow-state.py` 也只校验根 README 是否存在
- B. 当前 workflow 已强制 `performance_probe` 早期探针，并在 brainstorm 中关注体积/启动时间/内存/性能；但未找到“无条件存在、且位于主干任务之后的独立性能回归与优化 task”规则
- C1. 当前 `plan.md`、`workflow-state.py`、`start.md` 已共同阻止 plan 自动进入 implementation / test-first，并强制 `execution_authorized = false`
- C2. 当前 `plan.md` 明确要求在 plan 阶段直接“创建 / 补齐真实 Trellis task”，且 `plan-validate.py` 要求这些 task 目录真实存在；尚未发现“任务创建前人工确认清单”的产物契约或校验
