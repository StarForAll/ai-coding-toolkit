# workflow-audit: 修复新项目开发工作流 project-audit / 状态展示 / check 证据缺陷

## Goal

基于 `docs/workflows/新项目开发工作流/` 的源资产，结合 `/tmp/trellis-0.5.17-2` 这个已执行 `trellis init` 并嵌入该工作流的目标项目样本，逐项核实并修复用户列出的工作流缺陷。修复必须只落在 `docs/workflows/新项目开发工作流/` 内，并保证安装后目标项目的 project-audit 编排、任务状态展示、check 证据链和 strong-gate 语义更加一致，不引入新的明显回归。

## What I already know

* 审计与修复目标固定为 `docs/workflows/新项目开发工作流/`，不是当前仓库自用的 `.trellis/` 工作流。
* 用户要求以 `/tmp/trellis-0.5.17-2` 的实际嵌入结果判断问题是否真实存在；该目录可作为 `generated target project` 证据层。
* 修复范围限定为 `docs/workflows/新项目开发工作流/` 和当前任务目录；其他仓库目录不能修改。
* `docs/workflows/新项目开发工作流/commands/workflow_assets.py` 中 `COMPATIBLE_TRELLIS_VERSION = "0.5.17"`，当前 `trellis -v` 也是 `0.5.17`，`workflow-audit` 版本门禁通过。
* `/tmp/trellis-0.5.17-2` 当前已能复现多项问题：`project-audit` 只允许从 `implementation` / `test-first` 进入，任务列表只显示裸 `stage`，`check-quality.py` 仍只支持 test/lint/typecheck 且 `not run` 语义不标准，`task.py` 仍残留“status flip”旧注释和旧示例。

## Assumptions (temporary)

* `/tmp/trellis-0.5.17-2` 保留了足够的嵌入产物，可用于确认问题是否真实存在，而无需重新执行一次正式 embed。
* 若问题根因落在 Trellis 原生基线文件，但该工作流已经通过安装器或补丁脚本接管对应面，则应优先在该工作流的补丁链里修复。
* 与用户列出的四类问题相邻的同类缺陷，可能还分布在 `workflow-state.py` 的 transition graph、task-status view patch、安装器内联补丁、帮助文案与回归测试中，需要一并修正。

## Open Questions

* 当前无需向用户追加阻塞问题，先按 source repo 与 `/tmp` 样本取证；仅当证据出现分叉且无法静态归因时再询问。

## Requirements (evolving)

* 不能把候选问题直接当成结论，必须逐项给出 confirmed / false alarm / blocked 判断。
* 若问题真实存在，修复只能发生在 `docs/workflows/新项目开发工作流/` 内。
* 需要主动排查同类缺口，而不是只修用户点名行号。
* `project-audit` 修复需要同时覆盖阶段图、命令文档、安装后补丁和测试，避免只改一层。
* 任务状态展示修复需要让目标项目任务列表能体现 strong-gate 语义，而不是继续伪装成普通 `stage`。
* `check-quality.py` 修复需要提升项目化验证证据表达能力，至少统一 `pass / fail / not run`，保留 stderr 证据，并支持超出 test/lint/typecheck 的附加检查。
* 需要维护任务内 `audit-report.md`，保留 `source repo`、`generated target project`、`runtime command output` 三层证据。
* 最终需要运行与本次修改对应的测试或验证命令，并真实记录 `pass / fail / not run`。

## Acceptance Criteria (evolving)

* [ ] `audit-report.md` 中对用户列出的四类问题给出基于证据的结论，并记录必要的同类问题。
* [ ] `project-audit` 的正式进入链与 leaf/transition 语义在工作流源资产内闭环，不再要求操作者回退阶段或强制 `--force` 才能进入。
* [ ] 目标项目任务列表状态展示不再只显示裸 `stage`，能体现关键 strong-gate 动作或阻塞语义。
* [ ] `check-quality.py` 输出对跳过项标准化为 `not run`，保留失败 stderr，并支持附加验证项。
* [ ] `task.py` 的强门禁补丁不再遗留“仍会 flip status”的旧注释和旧示例。
* [ ] 至少一组相关 installer / workflow-state / helper 测试实际通过。

## Definition of Done (team quality bar)

* 相关测试或校验已运行并记录结果
* 文档、安装器内联补丁、helper 脚本和测试保持一致
* 不修改 `docs/workflows/新项目开发工作流/` 之外的非任务文件
* 若发现新的强约束或维护规则，记录到 `audit-report.md` 并在总结中说明

## Out of Scope (explicit)

* 不直接修改当前仓库根层 `.trellis/`、`.codex/`、`.claude/`、`.opencode/` 的运行时代码
* 不把本次 same-version 维护扩展成跨版本兼容性审计
* 不直接在 `/tmp/trellis-0.5.17-2` 上打补丁作为最终交付

## Technical Notes

* 固定工作流根：`docs/workflows/新项目开发工作流/`
* 版本锚点：`docs/workflows/新项目开发工作流/commands/workflow_assets.py`
* 目标项目样本：`/tmp/trellis-0.5.17-2`
* 重点排查文件：
  * `commands/shell/workflow-state.py`
  * `commands/shell/check-quality.py`
  * `commands/project-audit.md`
  * `commands/workflow-patch-projectization.md`
  * `commands/install-workflow.py`
  * `commands/shell/patch-task-start-strong-gate.py`
  * `commands/test_workflow_installers.py`
  * `commands/shell/test_workflow_state.py`
