---
name: wf-finish
description: 人显式调用：核对结果与未核实项后执行最终门禁与正常归档。
disable-model-invocation: true
user-invoked: true
---

# wf-finish

> **判断指引**：收工四项判断（影响面 / 规模 / 缺口 / 未核实）见下节「收工前要自己判的四件事」；关闭证据见 `wf-repair-loop`。

仅由人调用。它是正常归档的唯一入口；未调用时任务不能正常归档。

## 收工前要自己判的四件事

- **影响面**：缺口影响谁、什么后果、能否回退；建议（补计划 / 接受 / 异常归档）。
  **`required` 验收项不得以"接受风险"结案**——只能按下面"收窄"或异常归档。人的挑战：「这个缺口影响谁？接受之后出问题谁负责？」
- **规模**：这次改了多少（新增/删除/移动、净增删、扩面条目、与批准面偏离）。框架给"自上次人确认以来的累计量
  vs 本项目历史最大"的事实，**不设阈值**；首任务收工必确认一次。人的挑战：「这次一共动了多少？为什么不需要我看？」
- **计划没覆盖的缺口**：检索了哪些验收项与 spec 规则、为什么认为没覆盖、影响多大、建议补计划还是接受。
  人的挑战：「你查了哪些标准就说没有？影响有多大？」
- **未核实项**：哪些本机验不了、影响多大、能否收窄。收窄必须同时给**四项依据**：被收窄/去除的验收项 id、
  不可验证的客观原因、影响与被放弃的保障、补偿措施——缺一不予接受；`required` 只能收窄或异常归档。

## 步骤

0. **先读修复态，不要试归档探路**：
   ```bash
   <python> <项目根>/.wf/bin/wf.py status --short --json              # 四条件 + exits + 确定阻断
   <python> <项目根>/.wf/bin/wf.py gate --due before_archive --json   # 步骤面缺口
   ```
   `repair_scope` 的读法见 `wf-repair-loop`；`unverifiable` 未放行时按 `wf-review-accept-unknown`
   找人裁（先呈现事实、再由人写 quote）。预检通过不等于可以归档：本 skill 只呈现事实，不宣告结论。
1. 呈现给人：Check 结果与锚点、验收逐项结论、未核实项、复杂任务的审查结论、知识处置状态、待提交路径，
   以及当前生效的放行清单（`unknown_acceptances`，归档回显会再列一次）。
2. 人确认后，把「finish 调用证据 + 按精确路径的提交授权」写入决定文件数组：
   - 一条 `choice=finish` 的 Decision（subject 记本任务与“已了解结果与未核实项”）；
   - 若干 `choice=commit` 的 Decision，`subject` 列出本次授权提交的精确路径。
3. `archive --task <id> --decision <decision.json>`。
4. 归档成功后按需 `writer release`（对象已到合法终态）。

## 出口

- `WF_COMMIT_NOT_AUTHORIZED`：等人处理，不自行提交。
- `WF_WORKSPACE_UNRESOLVED` / `WF_SCOPE_UNRESOLVED`：逐路径处置或回 Plan 重批。
- `WF_REVIEW_INVALID`：复杂任务缺真实审查，补审或按异常退出处置（不降级归档）。

## 工作习惯（2026-11-08 起）

- **同一终端同时只推进一个任务**；并行请另开终端/窗口。
  同一终端里的第二个 agent 会被 `WF_IDENTITY_UNRESOLVED(concurrent_unregistered_caller)` 阻断，
  须人显式 `wf.py enable` 登记后才放行，且此后与前者共享同一执行会话。
- **自动模式下不需要手写信封**：直接跑 `wf.py <子命令>`；身份由执行边界派生。

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


## 证据文件纪律（2026-11-07 起）

真实 dogfood 发现：把"入口该生成的结构"写成文件，会让任务目录膨胀、并迫使模型读源码猜字段。因此：

- **可以人/模型写的只有四类**：决定文件（批准/收工/知识处置的选择）、`--review-notes`（双轴结论）、`--changes`（spec 变更）、基线提案（**推荐** `baseline-apply --files a,b,c --decision <批准文件>`，由入口生成提案）。
- **不要自建**：验证结果（`task-check` 会记）、门禁预览（`gate --due before_archive`）、提交清单与摘要（`archive` 记录）、`plan-approval`/`finish-commit-manifest` 之类"自述性"文件。
- 需要知道某命令的输入结构：`<python> <项目根>/.wf/bin/wf.py help <命令>`（有最小示例，不必读源码）。
