---
name: wf-tdd
description: 任务 TDD 开关为开启时使用：针对真实行为取得红→绿证据。
disable-model-invocation: false
---

# wf-tdd

开关由项目缺省 + 任务取值决定，Plan 末与人批准同批确认。文档/调查类任务用独立可观察产物验证，不人为造失败命令。

## 做法

1. 先写针对目标行为的断言，运行并确认**因行为缺失**而失败（不是环境启动失败）。
2. 最小实现使其通过；再补边界用例。
3. 把证据写成 `check.tdd_evidence`：`{assertion, red_command_ref, red_reason, green_command_ref, properties}`。
4. `properties` 逐项说明：可红、确定性、快速、可无人执行。

## 不做

- 不把开关当全局强制，也不按任务类型自行开启。
- 不用生成测试凑数；不伪造红/绿运行记录。

## 纪律

- 身份只在请求信封里：不读环境变量、不从命令行或文件猜身份；信封缺失就报 `WF_IDENTITY_UNRESOLVED`。
- 不代人作答、不代跑终端确认与令牌；人的决定只经 `--decision` / `--plan` / `--disposition` 文件承载。
- 入口输出的 `tier` / `code` / `facts` / `next` 是唯一判定源；不自行改写状态或补写门禁结论。
- 命令一律形如 `python3 <项目根>/.wf/bin/wf.py <子命令>`；不装 PATH、不做 shell shim。

## 来源与差异

| 项 | 值 |
|---|---|
| 来源 | 全局 skill `test-driven-development`（`~/.claude/skills/test-driven-development`） |
| 许可 | 跟随本仓库（内部私有源，无第三方 NOTICE 义务；上游为同作者资产） |
| 基线 | 适配基线＝本仓库上述源文件；本副本为唯一发行件，上游改动不自动流入 |
| 差异 | 红/绿压缩成 Check 间可核的运行引用（§3.5 的 tdd_evidence 结构），不引入上游的自动提交句 |
| 最近正例 | 红运行失败进 check_history、绿运行在本次通过，两引用不同才判 tdd 满足 |
| 最近反例 | 把「已写测试」当通过；缺失时 tdd 开关形同虚设 |
