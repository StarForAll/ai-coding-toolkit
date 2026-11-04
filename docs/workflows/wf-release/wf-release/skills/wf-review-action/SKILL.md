---
name: wf-review-action
description: action 侧：读指定轮次已导入报告，先汇总各轴发现再做逐条处置建议。
disable-model-invocation: false
---

# wf-review-action

主会话（持有写权者）在 `review-import` 之后使用。它汇总报告、准备处置，不改源码。

## 步骤

1. 读 `<任务目录>/review/review-round-<N>/` 下已导入的报告（每槽位一个文件）。
2. 先汇总：按轴列出共识、分歧与互相矛盾的事实，标明来源槽位与 finding id。
3. 逐条给出处置建议：接受并修复 / 驳回（须给本地核实方式与证据）/ 转下轮。
4. 把处置计划写成 `--plan` 文件元素 `{finding, decision_ref, reason}`，交 `review-decide`。
5. 驳回必须本地核实；「作者不认可」不是证据。

## 判定边界

`review-decide` 的 pass/fail 由入口按事实推导（人数、CLI 差异、锚点、阻塞项）；本 skill 不给 verdict。
单 reviewer 只是 degraded 参考，不满足复杂任务完成条件。

## 纪律

- 身份只在请求信封里：不读环境变量、不从命令行或文件猜身份；信封缺失就报 `WF_IDENTITY_UNRESOLVED`。
- 不代人作答、不代跑终端确认与令牌；人的决定只经 `--decision` / `--plan` / `--disposition` 文件承载。
- 入口输出的 `tier` / `code` / `facts` / `next` 是唯一判定源；不自行改写状态或补写门禁结论。
- 命令一律形如 `python3 <项目根>/.wf/bin/wf.py <子命令>`；不装 PATH、不做 shell shim。

## 来源与差异

| 项 | 值 |
|---|---|
| 来源 | 本仓库全局 `skills/multi-cli-review-action`（一次性适配源） |
| 许可 | 跟随本仓库（内部私有源，无第三方 NOTICE 义务；上游为同作者资产） |
| 基线 | 适配基线＝本仓库上述源文件；本副本为唯一发行件，上游改动不自动流入 |
| 差异 | 只读指定轮次并先汇总后决策，写回 dispositions 而非直接改记录 |
| 最近正例 | 只读 round-2 两份报告，逐条折成 dispositions 后交人确认 |
| 最近反例 | 汇总与决策混写；缺失时判定无法回溯到报告 |
