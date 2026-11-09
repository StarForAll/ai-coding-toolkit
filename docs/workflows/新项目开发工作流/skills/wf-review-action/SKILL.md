---
name: wf-review-action
description: action 侧：读指定轮次已导入报告，先汇总各轴发现再做逐条处置建议。
disable-model-invocation: false
---

# wf-review-action

主会话（持有写权者）在 `review-import` 之后使用。它汇总报告、准备处置，不改源码。

## 步骤（**不需要任何路径或轮次参数**）

本会话已经知道当前任务与审查轮次，直接调即可：

```bash
# 1) 导入：按文件名发现本轮已完成（status=done）的报告，重复调用幂等
<python> <项目根>/.wf/bin/wf.py review-import --task <任务 id> --envelope <本会话信封> --json

# 2) 判定：轮次缺省＝当前打开的轮；实施 CLI 取本会话宿主身份
<python> <项目根>/.wf/bin/wf.py review-decide --task <任务 id> --envelope <本会话信封> --json
```

1. 导入后读 `facts.imported_agents`（本轮报告来自哪些 agent）；报告正文在任务目录 `review/` 下。
2. 先汇总：按轴列出共识、分歧与互相矛盾的事实，标明来源 agent 与 finding id。
3. 逐条给出处置建议：接受并修复 / 驳回（须给本地核实方式与证据）/ 转下轮。
4. 把处置计划写成 `--plan` 文件元素 `{finding, decision_ref, reason}`，再交 `review-decide`。
5. 驳回必须本地核实；「作者不认可」不是证据。

> 人数与异种由**报告文件名**判定（`review-<agent>.md`）；两个报告同名即视为同一 CLI，会被拒。

## 判定边界

`review-decide` 的 pass/fail 由入口按事实推导（人数、CLI 差异、锚点、阻塞项）；本 skill 不给 verdict。
单 reviewer 只是 degraded 参考，不满足复杂任务完成条件。

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

## 来源与差异

| 项 | 值 |
|---|---|
| 来源 | 本仓库全局 `skills/multi-cli-review-action`（一次性适配源） |
| 许可 | 跟随本仓库（内部私有源，无第三方 NOTICE 义务；上游为同作者资产） |
| 基线 | 适配基线＝本仓库上述源文件；本副本为唯一发行件，上游改动不自动流入 |
| 差异 | 只读指定轮次并先汇总后决策，写回 dispositions 而非直接改记录 |
| 最近正例 | 任务记录 `validation.md` §19：两异种 reviewer 的两份报告按轴汇总后写成 `--plan` 的 dispositions 元素，`review-decide` 据此判 pass |
| 最近反例 | 同节：同一 CLI 占两个槽位时 `review-decide` **拒绝输入、不产生 verdict**（旧版曾记为 fail，已按设计稿 §6.5 修订）；把汇总与决策混写会让判定无法回溯到具体报告 |
