# Audit Report: 新项目开发工作流

## Audit Boundary

* Workflow Root: `docs/workflows/新项目开发工作流/`
* Temporary Target Project: `/tmp/trellis-0.5.17-2`
* Compatible Anchor Version: `0.5.17`
* Current Trellis Version: `0.5.17`
* Version Gate: `passed`

## Candidate Issues

* `workflow-state.py` 单文件过度膨胀，职责可能过多，维护成本过高
* 需要顺带排查同类结构问题，避免只修单点

## Status

* 当前处于证据采集阶段，尚未进入源资产修改

## Findings

### Confirmed

#### 1. `workflow-state.py` 过度膨胀且职责混杂

* Source layer: `docs/workflows/新项目开发工作流/commands/shell/workflow-state.py`
* Generated target project: `/tmp/trellis-0.5.17-2/.trellis/scripts/workflow/workflow-state.py`
* Validation action:
  * `wc -l` 显示源文件与临时项目文件均为 `2872` 行
  * `sha256sum` 显示两者内容完全一致
  * `rg '^def '` 显示该文件包含 `70+` 个函数，覆盖 state schema、阶段门禁、route、repair、安装态校验、CLI 补丁完整性检查、分发命令漂移检查等多类职责
* Evidence summary:
  * 文件前半段负责 `workflow-state.json` 结构、阶段转换、外包/归属/PRD/交付门禁
  * 文件后半段额外负责 `.trellis/workflow-installed.json`、runtime patch 标记、patched Codex skills、distributed command 漂移检查，并由 `route` 在任务解析前先执行
  * 这已经超出“状态 helper”单一职责，是真实的结构复杂度问题，而非单纯行数大

#### 2. `route` 入口与嵌入完整性检查强耦合，维护点分散

* Source layer: `docs/workflows/新项目开发工作流/commands/shell/workflow-state.py`
* Runtime command output: `/tmp/trellis-0.5.17-2` 上执行 `workflow-state.py route --project-root /tmp/trellis-0.5.17-2`
* Validation action:
  * 运行命令得到 `action=entry_choice_required`
  * 结合 `cmd_route()` 代码可见：`route` 在解析 active task 前先调用 `detect_embed_invalid()`
* Evidence summary:
  * `route` 既承担阶段路由，又承担嵌入安装态完整性守卫
  * 任何 install-record / patch / distributed command 契约变化都会直接影响主路由入口
  * 这是导致脚本持续膨胀的直接原因之一

#### 3. 同类问题已蔓延到配套测试，现有基线测试已出现漂移

* Source layer: `docs/workflows/新项目开发工作流/commands/shell/test_workflow_state.py`
* Runtime command output: `python3 -m unittest docs/workflows/新项目开发工作流/commands/shell/test_workflow_state.py`
* Validation action:
  * 单测结果：`Ran 127 tests ... FAILED (failures=1)`
  * 失败用例：`test_cmd_route_embed_invalid_when_distributed_command_content_drifts_across_platforms`
* Evidence summary:
  * 该失败 fixture 的 `critical_runtime_patches` 缺失 `claude-inject-subagent-context`，因此 `route` 返回 `embed_invalid` 是合理的；测试期望仍写成 `entry_choice_required`
  * 说明测试文件也已经难以维护，且与脚本契约不同步

### Similar Issues Observed But Not Yet Recommended For This Round

* `install-workflow.py` 为 `3503` 行，`upgrade-compat.py` 为 `1962` 行，也存在体量偏大问题
* 但这两者 blast radius 明显更大，且不属于本次 `workflow-state` 直接相邻修复面；若本轮同时大拆，新增风险很高
