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


## 证据文件纪律（2026-11-07 起）

真实 dogfood 发现：把"入口该生成的结构"写成文件，会让任务目录膨胀、并迫使模型读源码猜字段。因此：

- **可以人/模型写的只有四类**：决定文件（批准/收工/知识处置的选择）、`--review-notes`（双轴结论）、`--changes`（spec 变更）、基线提案（**推荐** `baseline-apply --files a,b,c --decision <批准文件>`，由入口生成提案）。
- **不要自建**：验证结果（`task-check` 会记）、门禁预览（`gate --due before_archive`）、提交清单与摘要（`archive` 记录）、`plan-approval`/`finish-commit-manifest` 之类"自述性"文件。
- 需要知道某命令的输入结构：`<python> <项目根>/.wf/bin/wf.py help <命令>`（有最小示例，不必读源码）。

## 不做

- 不读取、不改写其他框架（含 Trellis）的资产；Trellis 有效指令存在时先按 `wf-start` 的互斥出口处理。
- 不把既有业务提交追认成本任务改动。

## 纪律

- 身份只在请求信封里：不读环境变量、不从命令行或文件猜身份；信封缺失就报 `WF_IDENTITY_UNRESOLVED`。
- 不代人作答、不代跑终端确认与令牌；人的决定只经 `--decision` / `--plan` / `--disposition` 文件承载。
- 入口输出的 `tier` / `code` / `facts` / `next` 是唯一判定源；不自行改写状态或补写门禁结论。
- 命令形如 `<python> <项目根>/.wf/bin/wf.py <子命令>`。`<python>` 按此顺序取，**取到能跑的就整会话固定复用**：
  ① `.wf/project-config.json` 的 `python_executable`（未设置再读 `~/.wf/config.json` 同名键，可直接读文件取值，不必先执行）；
  ② 你自身运行时的 Python 可执行文件；
  ③ 系统 `python3`。
  若宿主执行策略要求审批或不在白名单（`WF_EXECUTOR_UNCONFIRMED` / 审批拒绝），改用策略允许的已核实 Python 绝对路径并固定下来；
  **不要每条命令换解释器**，也不要因为被拒就改成手写信封或换路径重试同一效果。不装 PATH、不做 shell shim。
