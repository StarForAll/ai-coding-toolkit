# fix workflow installer profile contract and bootstrap cleanup

## Goal

修正 `docs/workflows/新项目开发工作流/commands/install-workflow.py` 的安装契约，避免 workflow 在目标项目首次嵌入时把未声明项目类型默认视为 `outsourcing`，并确保 `trellis init` 生成的 `00-bootstrap-guidelines` 在正式安装过程中被彻底清理，不再污染后续 `workflow-state.py route` 的首次入口判断。

## What I already know

* 当前安装器把 `--profile` 设为可选参数，默认值为 `outsourcing`。
* `workflow-state.py route` 在没有 active task 时，会先检查 `.trellis/tasks/` 下是否存在任意任务目录；只要存在，就会返回 `recovery_needed`，而不是进入首次入口的 profile 路由。
* 在真实样本 `/tmp/trellis-0.5.17-2` 中，`route` 返回：
  * `action = recovery_needed`
  * `reason = 当前 session 未解析到 active task。已有任务: 00-bootstrap-guidelines。请执行 task.py start <task-dir> 切换到目标任务`
* 工作流文档和安装记录都宣称 `00-bootstrap-guidelines` 已在安装时清理，但真实样本又表现出该任务仍被路由器识别。
* 用户已确认两项产品决策：
  * `--profile` 不能有默认值；必须显式传入，或在交互环境中强制用户选择。
  * `00-bootstrap-guidelines` 这类初始化遗留项应在安装时彻底清理。

## Assumptions

* 当前任务只修复安装契约与 bootstrap 清理，不扩展或重构整个强门禁状态机。
* 非交互环境下，如果未显式传入 `--profile`，安装器应直接失败，而不是静默选择默认值。
* `--dry-run` 与正式安装应共享同一套 profile 决策逻辑，避免预览结果与正式安装结果不一致。

## Open Questions

* 无。当前需求已足够明确，可以直接进入实现。

## Requirements

* `install-workflow.py` 的 `--profile` 不得再使用默认值。
* 当调用方未提供 `--profile` 时：
  * 若当前为交互式终端，安装器必须要求用户从 `personal` / `outsourcing` 中显式选择。
  * 若当前不是交互式终端，安装器必须退出并提示显式传入 `--profile`。
* 上述规则必须同时作用于 `--dry-run` 和正式安装。
* profile 决策结果必须继续正确传播到：
  * 安装记录 `workflow-installed.json`
  * profile 条件化内容裁剪
  * helper scripts / execution cards 分发
  * AGENTS / workflow / commands 补丁注入
* 正式安装时必须彻底清理 `00-bootstrap-guidelines` 及其相关遗留引用，至少不能让它继续作为 `.trellis/tasks/` 下的可见任务污染首次 `route`。
* 若 bootstrap 清理未实际发生，安装记录不得继续写出误导性的 `bootstrap_task_removed = true` 或 `bootstrap_cleanup_status = removed`。
* 需要补充或更新验证，覆盖：
  * 未传 `--profile` 的交互 / 非交互行为
  * `--dry-run` 与正式安装的 profile 一致性
  * bootstrap task 清理后的 `route` 首次入口行为

## Acceptance Criteria

* [ ] 不带 `--profile` 在非交互环境运行安装器时，命令失败并给出明确错误提示。
* [ ] 不带 `--profile` 在交互环境运行安装器时，必须要求用户明确选择 `personal` 或 `outsourcing`。
* [ ] `--dry-run` 与正式安装在同一 profile 下生成一致的 profile-sensitive 结果。
* [ ] 在 fresh `trellis init` 基线上正式嵌入后，`.trellis/tasks/00-bootstrap-guidelines` 不再残留。
* [ ] 真实或测试夹具中的 `workflow-state.py route` 不再因 `00-bootstrap-guidelines` 残留而返回 `recovery_needed`。
* [ ] 安装记录中的 bootstrap 清理字段与实际结果一致。
* [ ] 相关测试 / 验证命令通过，或新增覆盖能证明本次修复有效。

## Definition of Done

* 代码修改完成并自检通过
* 相关测试或验证覆盖更新
* 文档 / 命令示例更新到位
* 不引入新的 source/deploy 漂移

## Out of Scope

* 不重做整个 `workflow-state.py route` 体系
* 不处理所有潜在的 `embed_invalid` / skill 语义漂移问题
* 不调整外包项目逻辑本身的业务规则

## Technical Notes

* 关键源文件：
  * `docs/workflows/新项目开发工作流/commands/install-workflow.py`
  * `docs/workflows/新项目开发工作流/commands/workflow_assets.py`
  * `docs/workflows/新项目开发工作流/commands/detect-embed-state.py`
  * `docs/workflows/新项目开发工作流/commands/shell/workflow-state.py`
  * `docs/workflows/新项目开发工作流/工作流总纲.md`
  * `docs/workflows/新项目开发工作流/命令映射.md`
* 已确认的运行证据：
  * `/tmp/trellis-0.5.17-2/.trellis/scripts/workflow/workflow-state.py route`
  * 输出 `recovery_needed`
  * 原因包含 `已有任务: 00-bootstrap-guidelines`
* 本任务属于跨层修改：安装器、运行时路由、安装记录、文档示例、验证都可能需要同步。
