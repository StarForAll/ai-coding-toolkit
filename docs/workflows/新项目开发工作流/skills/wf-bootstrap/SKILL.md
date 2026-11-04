---
name: wf-bootstrap
description: 人显式调用：存量项目首次建立基线、项目配置与初始 spec。
disable-model-invocation: true
user-invoked: true
---

# wf-bootstrap

在已启用的会话内做存量接入。产出是项目基线、项目配置与 spec 骨架；不接管既有开发流程。

## 步骤

1. 清点本地事实：代码、测试、已有文档、本地命令。命令缺失就写“缺失 + 核验出口”，不猜。
2. 起草接入 PRD（`task-new --kind bootstrap`），机读块列出触碰面（`.wf/baseline.md`、`.wf/project-config.json`、`.wf/spec/**`）与可立即运行的基本核验。
3. 经人批准 → `task-start` → `baseline-apply --task <id> --proposal <path>` 成组落盘。
4. 从代码推断的技术事实标 `verified_at: extracted`，不伪造核实日期。
5. `task-check` → 人调用 `wf-finish` → `archive`。

## 不做

- 不读取、不改写其他框架（含 Trellis）的资产；Trellis 有效指令存在时先按 `wf-start` 的互斥出口处理。
- 不把既有业务提交追认成本任务改动。

## 纪律

- 身份只在请求信封里：不读环境变量、不从命令行或文件猜身份；信封缺失就报 `WF_IDENTITY_UNRESOLVED`。
- 不代人作答、不代跑终端确认与令牌；人的决定只经 `--decision` / `--plan` / `--disposition` 文件承载。
- 入口输出的 `tier` / `code` / `facts` / `next` 是唯一判定源；不自行改写状态或补写门禁结论。
- 命令一律形如 `python3 <项目根>/.wf/bin/wf.py <子命令>`；不装 PATH、不做 shell shim。
