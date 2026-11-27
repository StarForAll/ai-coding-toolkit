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
  vs 本项目历史最大"的事实，**不设阈值**；首任务收工必确认一次（人看过 `[规模]` 行并给出原话，
  跑 `wf sampling confirm --task <id> --quote "<人的原话>"` 写入本次确认值，成为后续 `history_max`
  的输入；不确认则预览会持续提示）。人的挑战：「这次一共动了多少？为什么不需要我看？」
- **计划没覆盖的缺口**：检索了哪些验收项与 spec 规则、为什么认为没覆盖、影响多大、建议补计划还是接受。
  人的挑战：「你查了哪些标准就说没有？影响有多大？」
- **未核实项**：哪些本机验不了、影响多大、能否收窄。收窄必须同时给**四项依据**：被收窄/去除的验收项 id、
  不可验证的客观原因、影响与被放弃的保障、补偿措施——缺一不予接受；`required` 只能收窄或异常归档。
  收窄经 `wf verify resolve --kind narrow` 落档，人工核验证据走 `--kind inspection`。
  **手工验证与直接验收都不是收窄**：它们要的是人给的验收结论，且该结论必须绑定"人当时看到的交付内容"
  （入口按 `content_digest` 核这个绑定）——缺它该项按未运行/待定处理，不能当成通过。决定文件的字段形状见
  `wf help task-check`。

## 步骤

0. **先读修复态，不要试归档探路**：
   ```bash
   <python> <项目根>/.wf/bin/wf.py status --short --json              # 四条件 + exits + 确定阻断
   <python> <项目根>/.wf/bin/wf.py gate --due before_archive --json   # 步骤面缺口
   ```
   `repair_scope` 的读法见 `wf-repair-loop`；`unverifiable` 未放行时按 `wf-review-accept-unknown`
   找人裁（先呈现事实、再由人写 quote）。不要用 `archive` 试探（完整理由见 `wf-repair-loop`「不要试归档探路」）；
   本 skill 只呈现事实，不宣告结论。
1. 呈现给人：Check 结果与锚点、验收逐项结论、未核实项、复杂任务的审查结论（含每轮 `launch_scope` 的
   `selected/total/narrowed` 与判定 `scope.unselected`；发起前的人外发确认——choice=export——见
   `wf-continue`「复杂任务审查」）、材料身份状态（`review-status` facts 的 `materials.state`
   与判定 facts 的 `materials_state`：非 `fixed` 的 pass 按弱证据对待——结论有效、证据强度如实报）、
   知识处置状态、待提交路径，以及当前生效的放行清单
   （`unknown_acceptances`，归档回显会再列一次）、**K6 不可逆确认项**（收工/归档的只读预览里 `irreversible`：命中的规则文件、删除路径与缺的 `authorize record`——缺删除/规则确认会被 `WF_DELETE_NOT_AUTHORIZED`/`WF_REPO_RULES_NOT_AUTHORIZED` 拦；确认文件结构拿不准先取 `authorize record` 的只读骨架（`--draft`））、**审查降级事实**（同投影的 `review_degraded`：本轮若是人签接受的单 reviewer 留痕降级，单列说明并附接受记录摘要，人基于降级事实决定是否收工）。若 `judgments show` 有 `[vendor]` 框架自有改动，
   单列说明它不计交付/审查/业务提交；归属确认记录（kind=框架改动）按 `wf-continue` 的 vendor 段；
   本任务声称修框架时按 `wf-continue` 的 vendor 段定去向（回源仓库立项/另开任务/保持现场），
   不在收尾里吞掉，也不混入业务提交。
2. 人确认后，先跑 `archive --task <id> --draft` 取决定文件草稿（入口按当前待提交路径生成、只打印不落盘），
   按草稿把「finish 调用证据 + 按精确路径的提交授权」写成决定文件（不手写路径清单，人把内容写成决定文件即授权）：
   - 一条 `choice=finish` 的 Decision（subject 记本任务与“已了解结果与未核实项”）；
   - 若干 `choice=commit` 的 Decision，`subject` 列出本次授权提交的精确路径。
3. `archive --task <id> --decision <decision.json>`。
4. 正常归档持久化成功后，入口自动释放写权（对象已到合法终态）；若回显 `write_release.released=false`，按事实重跑 `writer release`，不要把归档结果说成失败。

## 出口

- `WF_COMMIT_NOT_AUTHORIZED`：等人处理，不自行提交。
- `WF_WORKSPACE_UNRESOLVED` / `WF_SCOPE_UNRESOLVED`：逐路径处置或回 Plan 重批。
- `WF_REVIEW_INVALID` / `WF_SEMANTIC_DECISION`：按 `facts` 判断来源——复杂任务缺真实审查/主会话复核不合规、
  知识处置缺失、复盘未覆盖触发事实等都会用这两个码；先按 facts 补齐对应项，审查环境确不可用才按异常退出
  处置（不降级归档）。

## 工作习惯

- 同一终端只推进一个任务、自动模式不手写信封（含 generation 口径）——完整定义见
  `wf-continue`「工作习惯」（唯一完整定义位），此处不重复论述。

## 纪律

- 运行纪律见 `.wf/workflows/session-flow.md`「运行约定」：身份只经信封或宿主映射通道；不代人作答；入口输出是唯一判定源；解释器整会话固定、失效即停。

## 证据文件纪律

论述见 `wf-continue` 的「证据文件纪律」（唯一完整定义位，不在本文件另留清单）：按"谁生成"判断——入口产的结构不自建文件；人/模型填写的输入以 `wf help <命令>` 的 `inputs` 与 `--draft` 骨架为准。
