# check阶段补充sonar验证闭环

## Goal

在 `docs/workflows/新项目开发工作流` 的新项目首次嵌入与 `check` 阶段强制加入 `project-id` 与 `sonar verify -p <project-id>` 验证闭环，并同步目标项目嵌入时的 project id 输入、安装记录、目标项目 spec 基线和相关旧说明，避免 check 流程、安装流程、文档与测试之间产生漂移。

## What I Already Know

* 用户要求新增的 check 步骤是强制步骤，不能作为可选门禁。
* `project-id` 必须在执行 workflow 嵌入命令时传入，例如 `--project-id python_project`。
* 本任务不考虑旧项目中已嵌入 workflow 的升级问题，只考虑新项目首次嵌入该 workflow。
* `project-id` 是后续任何 workflow 操作的硬前置条件；如果没有该值，后续任何操作都必须禁止执行。
* 已确认阻断边界：安装阶段缺 `--project-id` 直接失败且不写安装记录；安装完成后，所有 workflow 阶段入口、路由、状态推进、check / delivery / finish-work 相关命令若读不到有效 `project_id` 都 hard stop；`detect-embed-state.py`、`--help`、只读诊断类命令可保留，因为它们不推进 workflow。
* 用户确认 `project-id` 的个人强制校验要求：`strip()` 后非空、不包含空白字符；首尾必须是英文字符，非首尾字符允许英文字符、数字和常见符号，例如 `:`、`-`、`_`。
* `check` 阶段必须先执行 `sonar verify -p <project-id>`。
* 如果 sonar 分析发现问题，必须按实际情况修复；修复时需要避免引入新问题，并检查是否存在类似问题，若存在需一起修复。
* 如果 sonar 存在问题且执行了修复，必须重新执行 `sonar verify -p <project-id>`，直到无问题。
* 当前 `commands/check.md` 已有项目化验证步骤和 `check-quality.py` 示例，但没有强制 `sonar verify -p <project-id>` 闭环。
* 当前安装命令文档和 `install-workflow.py` 已要求 `--profile`，但初步检索未发现正式 `--project-id` 参数。
* 当前目标项目初始导入包包含 `.trellis/spec/universal-domains/verification/evidence-requirements`，但未包含 `verification-gates`。
* 现有 docs spec 把 `sonar-scanner conditionalization` 标记为易漂移规则，相关旧说明需要同步。

## Requirements

* 在 workflow 的 check 阶段加入强制 sonar 验证闭环。
* 新项目首次嵌入时，安装器必须要求并记录目标项目 `project-id`，供后续所有阶段使用。
* 安装后任意阶段或命令若无法读取有效 `project-id`，必须 hard stop，不能降级为警告、询问或跳过。
* Hard stop 范围限定为 installed workflow 的阶段入口、路由、状态推进、check / delivery / finish-work 相关执行面；不阻断 `--help`、`detect-embed-state.py` 和只读诊断。
* `project-id` 必须执行个人强制校验：`strip()` 后非空、不包含空白字符；首尾必须是英文字符，非首尾字符允许英文字符、数字和常见符号，例如 `:`、`-`、`_`。
* 安装命令示例和执行规范必须同步显示 `--project-id <id>`。
* 嵌入到目标项目的 spec 必须包含该强制 check 规则，不能只存在于源仓库命令文档。
* 与旧 `sonar-scanner` 条件化说明相关的文档和测试必须同步，避免新旧规则冲突。
* 改动不得破坏现有 check-quality、review-gate、delivery、finish-work 和新项目首次安装流程。

## Acceptance Criteria

* [ ] `check` 阶段文档明确强制执行 `sonar verify -p <project-id>`。
* [ ] check 流程明确 sonar fail -> 修复 -> 类似问题排查 -> 重跑 sonar，直到通过。
* [ ] `install-workflow.py` 接收并强制校验 `--project-id`，并写入 `.trellis/workflow-installed.json`。
* [ ] 新项目安装时缺失 `--project-id` 必须失败，不能写入半完成安装状态。
* [ ] 安装后的阶段命令若 `.trellis/workflow-installed.json` 缺失有效 `project-id`，必须禁止继续执行。
* [ ] 只读诊断和帮助命令在缺失 `project-id` 时仍可用于定位安装状态。
* [ ] `project-id` 校验覆盖空字符串、前后空格、内部空白、首尾非英文字符、非法符号。
* [ ] `project-id` 校验覆盖允许数字作为非首尾字符的合法案例。
* [ ] 目标项目安装后的 spec 基线包含强制 sonar verify 闭环规则。
* [ ] 安装示例、嵌入执行规范、命令映射、平台 README、walkthrough 等引用旧安装命令的位置同步加入 `--project-id`。
* [ ] 旧 `sonar-scanner` 条件化说明被同步改为与新强制 `sonar verify` 规则不冲突。
* [ ] 相关测试覆盖安装记录、缺失 `--project-id` 的阻断、安装产物和关键文档内容。
* [ ] 仓库验证命令通过，或明确记录未能运行的原因。

## Definition of Done

* 更新源 workflow 资产、安装器、目标项目 spec 基线和相关说明。
* 更新或新增回归测试。
* 运行与本改动相关的验证命令。
* 按 Trellis 流程完成 spec update 判断和收尾。

## Out of Scope

* 不实现 `sonar` CLI 本身。
* 不处理旧项目已嵌入 workflow 后的升级迁移。
* 不改变 review-gate、delivery 或 finish-work 的阶段跳转语义。
* 不把 Codex 改造成正式项目级 slash command 入口。

## Technical Notes

* 初步定位的核心文件：
  * `docs/workflows/新项目开发工作流/commands/check.md`
  * `docs/workflows/新项目开发工作流/commands/install-workflow.py`
  * `docs/workflows/新项目开发工作流/commands/workflow_assets.py`
  * `docs/workflows/新项目开发工作流/commands/test_workflow_installers.py`
  * `trellis-library/specs/universal-domains/verification/*`
  * `.trellis/spec/docs/index.md`
* 已确认范围收窄为新项目首次嵌入，不需要设计旧项目升级迁移路径。
* `project-id` 在运行时读取方式建议为从 `.trellis/workflow-installed.json` 读取安装时写入值，避免要求 check 阶段重复输入。
* 当前建议方案：新增安装器必填 `--project-id`，写入安装记录；`check.md` 指导从安装记录读取，执行 `sonar verify -p <project-id>`；目标项目 spec 初始包加入或更新验证门禁规则。

## Open Questions

* 最终需求是否确认完成，可以进入实现？
