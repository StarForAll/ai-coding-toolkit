---
name: wf-finish
description: 人显式调用：核对结果与未核实项后执行最终门禁与正常归档。
disable-model-invocation: true
user-invoked: true
---

# wf-finish

> **判断指引**：收工四项判断（影响面 / 规模 / 缺口 / 未核实）见下节「收工前要自己判的四件事」；关闭证据见 `wf-repair-loop`。

仅由人调用。它是正常归档的唯一入口；未调用时任务不能正常归档。

试点期可跑一次 `wf sampling pick --task <id> --freeze`（不跑不阻断归档；入口会在 Check next_ 与预览里提示）。

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
1. 呈现给人：Check 结果与锚点、验收逐项结论、未核实项、复杂任务的审查结论（含每轮 `launch_scope` 的
   `selected/total/narrowed` 与判定 `scope.unselected`）、知识处置状态、待提交路径，以及当前生效的放行清单
   （`unknown_acceptances`，归档回显会再列一次）、**K6 不可逆确认项**（`stop --preview`/`archive --draft` 的 `irreversible`：命中的规则文件、删除路径与缺的 `authorize record`——缺确认直接归档会被 `WF_COMMIT_NOT_AUTHORIZED` 拦）。若 `judgments show` 有 `[vendor]` 框架自有改动，
   单列说明它不计交付/审查/业务提交；本任务声称修框架时按独立维护任务处理，不在收尾里吞掉。
2. 人确认后，把「finish 调用证据 + 按精确路径的提交授权」写入决定文件数组
   （拿不准结构时先跑 `archive --task <id> --draft`：入口按待提交路径生成决定文件草稿、
   只打印不落盘，人把内容写成决定文件即授权）：
   - 一条 `choice=finish` 的 Decision（subject 记本任务与“已了解结果与未核实项”）；
   - 若干 `choice=commit` 的 Decision，`subject` 列出本次授权提交的精确路径。
3. `archive --task <id> --decision <decision.json>`。
4. 正常归档持久化成功后，入口自动释放写权（对象已到合法终态）；若回显 `write_release.released=false`，按事实重跑 `writer release`，不要把归档结果说成失败。

## 出口

- `WF_COMMIT_NOT_AUTHORIZED`：等人处理，不自行提交。
- `WF_WORKSPACE_UNRESOLVED` / `WF_SCOPE_UNRESOLVED`：逐路径处置或回 Plan 重批。
- `WF_REVIEW_INVALID` / `WF_SEMANTIC_DECISION`：复杂任务缺真实审查、或主会话复核缺失/不合规；先补复核/补审，确无审查环境则按异常退出处置（不降级归档）。

## 工作习惯（2026-11-08 起）

- **同一终端同时只推进一个任务**（阻断机制见 `wf-continue`「工作习惯」）；并行请另开终端/窗口。
  同一终端里的第二个 agent 会被 `WF_IDENTITY_UNRESOLVED(concurrent_unregistered_caller)` 阻断，
  须人显式 `wf.py enable` 登记后才放行，且此后与前者共享同一执行会话。
- **自动模式下不手写 session 信封**：直接跑 `wf.py <子命令>`；身份由执行边界派生，
  写权代次由本会话运行态携带（显式 `inputs.generation` 可覆盖，不填不报错）。

## 纪律

- 运行纪律见 `.wf/workflows/session-flow.md`「运行约定」：身份只在请求信封里；不代人作答；入口输出是唯一判定源；解释器整会话固定、失效即停。

## 证据文件纪律

论述见 `wf-continue` 的「证据文件纪律」（唯一完整定义位）：可写的只有决定/`--review-notes`/`--changes`/基线提案/主会话复核五类；入口自产的结构不自建文件；命令输入结构问 `help <命令>`。
