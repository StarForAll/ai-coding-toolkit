---
name: wf-code-review
description: Check 内使用：同会话顺序做标准轴与需求轴检查，分别给结论与依据。
disable-model-invocation: false
---

# wf-code-review

Check 的第 ④ 步（双轴内部审查）。结论写入 `check.internal_review`，作为 `--review-notes` 提交。

## 两轴

| 轴 | 看什么 | 结论要件 |
|---|---|---|
| 标准轴 | 契约/spec 一致性、错误处理、边界与可维护性、是否引入未批准依赖 | 结论 + 具体位置/证据 |
| 需求轴 | PRD 验收项逐条是否被实际覆盖、是否有未声明的行为变化 | 结论 + 逐条对应 |

## 做法

1. 逐条对照批准验收与当前 diff；指出未覆盖项，而不是泛泛评级。
2. 两轴分别给结论，不用一轴掩盖另一轴。
3. 发现的问题在范围内修复后重跑相关验证；旧结果不挪用。
4. 写成 `{"standard": {…}, "requirement": {…}}`。

## 不做

- 不替代异种 CLI 审查（复杂任务仍需 `wf-review` 两个独立 reviewer）。
- 不以「已审查」为由跳过必要验证。

## 纪律

- 身份只在请求信封里：不读环境变量、不从命令行或文件猜身份；信封缺失就报 `WF_IDENTITY_UNRESOLVED`。
- 不代人作答、不代跑终端确认与令牌；人的决定只经 `--decision` / `--plan` / `--disposition` 文件承载。
- 入口输出的 `tier` / `code` / `facts` / `next` 是唯一判定源；不自行改写状态或补写门禁结论。
- 命令一律形如 `python3 <项目根>/.wf/bin/wf.py <子命令>`；不装 PATH、不做 shell shim。

## 来源与差异

| 项 | 值 |
|---|---|
| 来源 | 全局 skill `code-review-expert`（`~/.claude/skills/code-review-expert`） |
| 许可 | 跟随本仓库（内部私有源，无第三方 NOTICE 义务；上游为同作者资产） |
| 基线 | 适配基线＝本仓库上述源文件；本副本为唯一发行件，上游改动不自动流入 |
| 差异 | 双轴拆成同会话顺序两步，结论结构对齐 check.internal_review |
| 最近正例 | 两轴各有依据且结论为 pass，Check 才允许 pass |
| 最近反例 | 两轴只写结论不写依据；缺失时 Check 的通过判据无从核对 |
