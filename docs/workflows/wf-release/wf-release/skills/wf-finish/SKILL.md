---
name: wf-finish
description: 人显式调用：核对结果与未核实项后执行最终门禁与正常归档。
disable-model-invocation: true
user-invoked: true
---

# wf-finish

仅由人调用。它是正常归档的唯一入口；未调用时任务不能正常归档。

## 步骤

1. 呈现给人：Check 结果与锚点、验收逐项结论、未核实项、复杂任务的审查结论、知识处置状态、待提交路径。
2. 人确认后，把「finish 调用证据 + 按精确路径的提交授权」写入决定文件数组：
   - 一条 `choice=finish` 的 Decision（subject 记本任务与“已了解结果与未核实项”）；
   - 若干 `choice=commit` 的 Decision，`subject` 列出本次授权提交的精确路径。
3. `archive --task <id> --decision <decision.json>`。
4. 归档成功后按需 `writer release`（对象已到合法终态）。

## 出口

- `WF_COMMIT_NOT_AUTHORIZED`：等人处理，不自行提交。
- `WF_WORKSPACE_UNRESOLVED` / `WF_SCOPE_UNRESOLVED`：逐路径处置或回 Plan 重批。
- `WF_REVIEW_INVALID`：复杂任务缺真实审查，补审或按异常退出处置（不降级归档）。

## 纪律

- 身份只在请求信封里：不读环境变量、不从命令行或文件猜身份；信封缺失就报 `WF_IDENTITY_UNRESOLVED`。
- 不代人作答、不代跑终端确认与令牌；人的决定只经 `--decision` / `--plan` / `--disposition` 文件承载。
- 入口输出的 `tier` / `code` / `facts` / `next` 是唯一判定源；不自行改写状态或补写门禁结论。
- 命令一律形如 `python3 <项目根>/.wf/bin/wf.py <子命令>`；不装 PATH、不做 shell shim。
