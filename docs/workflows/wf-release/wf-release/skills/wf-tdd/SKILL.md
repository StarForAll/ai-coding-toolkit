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
- 命令形如 `<python> <项目根>/.wf/bin/wf.py <子命令>`。`<python>` 按此顺序取，**取到能跑的就整会话固定复用**：
  ① `.wf/project-config.json` 的 `python_executable`（未设置再读 `~/.wf/config.json` 同名键，可直接读文件取值，不必先执行）；
  ② 你自身运行时的 Python 可执行文件；
  ③ 系统 `python3`。
  若宿主执行策略要求审批或不在白名单（`WF_EXECUTOR_UNCONFIRMED` / 审批拒绝），改用策略允许的已核实 Python 绝对路径并固定下来；
  **不要每条命令换解释器**，也不要因为被拒就改成手写信封或换路径重试同一效果。不装 PATH、不做 shell shim。

## 来源与差异

| 项 | 值 |
|---|---|
| 来源 | 同作者的通用 skill `test-driven-development`（**非本仓库资产**，位于用户全局 skill 库；路径随机器而异，不以路径作基线） |
| 许可 | 跟随本仓库（内部私有源；同作者资产，无第三方 NOTICE 义务） |
| 基线 | 适配基线＝该上游 `SKILL.md` 的内容摘要 `sha256:dee1ce863c7c9ac61406e587b31f1f6650346f610e17f1ca468cb54eecf02da0`；本副本为唯一发行件，上游改动不自动流入。换机或上游更新时先按摘要核对差异，再决定是否吸收（设计稿 §7.4、§7.5） |
| 差异 | 红/绿压缩成 Check 间可核的运行引用（§3.5 的 tdd_evidence 结构），不引入上游的自动提交句 |
| 最近正例 | 红运行失败进 check_history、绿运行在本次通过，两引用不同才判 tdd 满足 |
| 最近反例 | 把「已写测试」当通过；缺失时 tdd 开关形同虚设 |
