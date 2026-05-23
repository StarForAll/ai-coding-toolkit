# Session Notes

## User-confirmed decisions

* `install-workflow.py` 的 `--profile` 不能设置默认值。
* 如果未显式传入 `--profile`：
  * 交互式场景必须要求用户选择
  * 非交互式场景必须失败
* `00-bootstrap-guidelines` 这类初始化遗留项必须在安装时彻底清理。

## Confirmed problem statements

* 真实样本 `/tmp/trellis-0.5.17-2` 中，`workflow-state.py route` 返回 `recovery_needed`，原因是发现已有任务 `00-bootstrap-guidelines`。
* 当前 `--profile` 默认值为 `outsourcing`，会把未声明项目类型错误固化到安装记录和后续首次路由。
* 这两个问题是独立但相关的：前者是 bootstrap 清理 / 首次路由问题，后者是安装契约问题。

## Expected implementation direction

* 优先修安装器契约与 bootstrap 清理。
* 若 bootstrap 清理逻辑已存在但记录字段与真实结果不一致，需要一并修正安装记录写入或校验逻辑。
* `--dry-run` 必须与正式安装共享 profile 决策，避免预览与正式安装分叉。
