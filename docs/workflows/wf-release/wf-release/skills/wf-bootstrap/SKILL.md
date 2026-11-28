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
3. 规划经人批准后 `task-start`；把基线/配置/spec 内容写进工作树，先用 `baseline-apply` 的
   只读预览取 `proposal_digest`，请人对该摘要批准（决定文件的 `object_digest` 写 `proposal_digest`），
   再用同一批文件与人的批准决定成组落盘——提案由入口生成，不手写 proposal JSON。
   旗标拼写与示例见 `wf help baseline-apply`。
4. 从代码推断的技术事实标 `verified_at: extracted`，不伪造核实日期。
5. `task-check` → 人调用 `wf-finish` → `archive`。

## 证据文件纪律

论述见 `wf-continue` 的「证据文件纪律」（唯一完整定义位，不在本文件另留清单）：按"谁生成"判断——入口产的结构不自建文件；人/模型填写的输入以 `wf help <命令>` 的 `inputs` 与 `--draft` 骨架为准。

## 不做

- 不读取、不改写其他框架（含 Trellis）的资产；Trellis 有效指令存在时先按 `wf-start` 的互斥出口处理。
  这不算违反：只读核对本项目自身的代码、提交与工作区状态是建立基线的份内事。
- 不把既有业务提交追认成本任务改动。
  这不算违反：在基线提案里如实登记既有提交的存在与归属（那是证据，不是追认）。

## 纪律

- 运行纪律见 `.wf/workflows/session-flow.md`「运行约定」：身份只经信封或宿主映射通道；不代人作答；入口输出是唯一判定源；解释器整会话固定、失效即停。
