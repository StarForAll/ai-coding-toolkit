---
name: wf-diagnosing-bugs
description: 同一问题重复失败时使用：建反馈、最小化、假设与定向探测、回归。
disable-model-invocation: false
---

# wf-diagnosing-bugs

用于 Execute 期的调试循环。重复失败达到 `debug_repeat_threshold` 时，入口会产生待决项，由人裁定「同一问题/不同问题」。

## 做法

1. 建立可重复的最小反馈（一条命令或一个断言）。
2. 最小化输入，直到失败可稳定复现且范围最小。
3. 提出假设 → 定向探测 → 记录被排除项（写进交接材料的 `ruled_out`）。
4. 修复后回归：同一反馈由红转绿，且不改变已批准范围。
5. 无法复现就如实报告环境与观察，不推测修复。

## 不做

- 不为了让计数好看而省略失败记录；不在未授权范围外改动代码。

## 纪律

- 身份只在请求信封里：不读环境变量、不从命令行或文件猜身份；信封缺失就报 `WF_IDENTITY_UNRESOLVED`。
- 不代人作答、不代跑终端确认与令牌；人的决定只经 `--decision` / `--plan` / `--disposition` 文件承载。
- 入口输出的 `tier` / `code` / `facts` / `next` 是唯一判定源；不自行改写状态或补写门禁结论。
- 命令一律形如 `python3 <项目根>/.wf/bin/wf.py <子命令>`；不装 PATH、不做 shell shim。

## 来源与差异

| 项 | 值 |
|---|---|
| 来源 | 全局 skill `diagnosing-bugs`（`~/.claude/skills/diagnosing-bugs`，含 agents/scripts） |
| 许可 | 跟随本仓库（内部私有源，无第三方 NOTICE 义务；上游为同作者资产） |
| 基线 | 适配基线＝本仓库上述源文件；本副本为唯一发行件，上游改动不自动流入 |
| 差异 | 只保留可被判据消费的复现-最小化-验证三段，脚本工具不随发行投放 |
| 最近正例 | 重复失败带 `dedupe_refs` 指向真实 check 失败，不重复计数 |
| 最近反例 | 反复猜修；缺失时 dedupe 声明容易拍脑袋 |
