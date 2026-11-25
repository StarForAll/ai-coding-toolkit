---
name: wf-review-action
description: action 侧：读指定轮次已导入报告，先汇总各轴发现再做逐条处置建议。
disable-model-invocation: false
---

# wf-review-action

主会话（持有写权者）在 `review-import` 之后使用。它汇总报告、准备处置；本轮之后的**范围内修复仍由本会话完成**——reviewer 不修代码，写处置记录也不等于修好。

## 步骤（任务 id 已知；主会话复核文件按下面命令生成/填写）

本会话知道当前任务与审查轮次；`--main-review` 是必填的复核文件：

```bash
# 1) 导入：按文件名发现本轮已完成（status=done）的报告，重复调用幂等
# 轮次必须显式给：缺省取**最大发起轮**，恢复较早一轮时会导到另一轮去
# 自动模式（默认）不传信封；只有本会话确实有显式信封文件时才追加 --envelope <本会话信封>
<python> <项目根>/.wf/bin/wf.py review-import --task <任务 id> --round <n> --json

# 2) 生成主会话复核骨架（不产生结论；放 .wf/.runtime/，该目录不入库）
<python> <项目根>/.wf/bin/wf.py review-decide --task <任务 id> --round <n> \
  --main-review-draft .wf/.runtime/main-review.json --json

# 3) 填写后判定：**必须显式传 --round 与 --main-review**
<python> <项目根>/.wf/bin/wf.py review-decide --task <任务 id> --round <n> \
  --main-review .wf/.runtime/main-review.json --plan <处置.json> --json
```

1. 导入后读 `facts.imported_agents`（本轮报告来自哪些 agent）；报告正文在任务目录 `review/` 下。若本轮 launch 的 `scope.narrowed` 为真，报告只覆盖交付集合的声明子集；这是实施侧对审查输入面的判断：在受影响轴的 `basis` 写清未选路径是否相关、能否补证、还剩什么风险，`review-decide` 的 `scope.unselected` 会随判定记录；只有确实留下需要人接受的残余风险时才登记 judgment，不要为每次收窄机械补一条规模判断。不要把它当作全交付面审查。
2. **主会话复核（不是可选步骤）**：逐份报告质疑其覆盖、证据与矛盾（`report_review.reliance` 取 `primary|partial|none`，写清为什么）；逐条 finding 本地核实（`finding_review.check` 取 `verified|disputed|unable`）；对五个轴给出**你自己的** `pass|fail|uncovered` 与依据（`basis`），来源写 `main` 或具体报告槽位（与某采信报告一致的轴，`basis` 一句指向即可——如"与 r1 一致"——不必逐轴重述完整依据；有分歧或你补核实的轴才写完整依据，把判断力集中在差异处）。判 `fail` 必须指回本轮未关闭的 blocking finding；判 `pass` 不能覆盖未关闭 blocking。**覆盖按你的采信计算**：`reliance=none` 的报告不贡献覆盖，`partial` 只贡献你在该轴 `sources` 列出的槽位，`primary` 贡献它全部 `pass/fail` 轴；不要把不采信的报告当覆盖来源。材料收窄时若你把某轴留 `uncovered`，就不要把覆盖该轴的报告标 `primary`；入口会把这对矛盾拒掉，改成 `partial/none` 或把轴改判 `pass/fail`。
3. 先汇总：按轴列出共识、分歧与互相矛盾的事实，标明来源 agent 与 finding id。**reviewer 报告是辅助证据**：报告未覆盖的轴，你能核实就自己补（写 `pass/fail` + 依据），补不了才留 `uncovered` 交人；不要为补一个 reviewer 的未覆盖轴自动再发一轮。
   - **只有 blocking finding 必须逐条核实**（`finding_review`）；非阻塞建议填不填由你判断，未填会记进 `deferred_suggestions`，不影响本轮成立；草稿骨架只给 blocking 留占位，建议的空占位直接删掉即可视为延后。修正复核只需提交新增/改动的 `main_findings`，入口按 id 并集保留旧的，并沿用它们上次的核实状态（重交草稿也一样；要改状态就显式写 `finding_review`）。
   - 主会话复核 `fail` 轴必须指回一条**未关闭**的 blocking finding；修好后重跑 Check、发**新一轮**，不要改已判轮次的复核。
   - 主会话自己核实、reviewer 未提出的 blocking：写进 `main_findings[]`（id/severity/statement/assertion_ref/basis），`fail` 轴的 `finding_refs` 用 `{finding_id, slot:"main"}` 引用，关闭时 dispositions 写 `slot:"main"`；这不是伪造 reviewer finding。`finding_review` 可省（默认 verified），要写 `disputed/unable` 时才补；`finding_id` 唯一时 `slot` 可省，入口会写回。
   - `finding_review.check=unable` 的 finding 不能靠 accepted 关闭；先补核实，或保持 open 让判定 fail。blocking main finding 的 severity 降级/关闭必须先走 dispositions；`broken-reference` 只有所引规则确实被本任务改过才要求人复核。
   - 缺陷落在已批准验收项/验证/spec 条款之外时，先判断是否仍在原触碰面内、能否直接修：能修就继续修，并把 `assertion_ref` 写成 `t:<触碰面内路径>`、**finding 同时补 location 字段**（入口核验：路径在批准触碰面内且覆盖 location，2026-11-21 起 blocking 可用）；不要为凑 `assertion_ref` 降成 suggestion 或先停下请批。只有要改验收/承诺/授权，或需要人确认残余风险时，才登记 `judgment`（kind=缺口/未核实, outcome=escalated）请人扩判据。
   - 报告未到齐时，可先用 `review-decide --register-only --main-review <file>` 登记已核实 main_findings（不产生 verdict）；最小文件只需 `task`/`round`/`main_findings`，入口补 discovery 并标未就绪。正式判否仍要完整审查。已判 `pass/unavailable` 后不能用登记入口改写复核；先关闭、后核实为 verified 的 finding，核实那次必须补可解析的 evidence_refs。
   - 你认为某条 finding 是误报/重分类时，主会话复核对应轴写 `pass`、`finding_review.check=disputed`，按处置规则写 `accepted`；同一轮重判可在 finding 关闭后通过。判定为 `pass`/`unavailable` 后不可替换复核；判定为 `fail` 或尚未判定时，可提交修正复核（旧复核保留并标 `supersedes`）。若复核仍有 `fail` 轴，不能据此产 `pass`。
4. 逐条给出处置：关闭 / 误报 / 重分类 / 不处置（见下节）。`finding_id` 命中多轮/多槽位时，在自己的 `--plan` 元素里补 `round`+`slot` 重交即可，不需要请人裁。
5. 把处置写成 `--plan` 文件的元素数组，再交 `review-decide`。
6. 驳回必须本地核实；「作者不认可」不是证据。

## 报告还能不能沿用（内容或标准变了之后）

- 三条路：① **沿用**（说明为什么变更不影响该结论）② **重发**（说明为什么影响）③ **`escalated` 交人**（判不了时的默认出口）。
- 判"沿用"必须点名漂移差异里的**具体位置**（`d:` + hunk/字段/行号）；框架只校验位置存在，**相关性与粒度是你的判断**——写进 `kind=沿用` 的 judgment（依据写实），判不了才 `outcome=escalated` 交人，不默认请示。
- **纠错型漂移**（`broken-reference`，旧验证从未成功执行）不给"沿用"这条路：锚点指向被纠错 check 的报告只能重发。
- 框架不判决后果，只保证"带 `standard_drift` 且没有对应 judgment 的报告不能产出 pass"。
- **材料身份**（报告里的 `materials.identity`）是硬绑定：材料被重出后旧报告对不上，判定会拒；
  能放回原字节就放回（原报告继续有效），放不回就按新材料重写并开新一轮。
- 关闭证据要指回问题本身：见 `wf-repair-loop`「这条 blocking 真的修了吗」。

## 处置形状（只有 `accepted` 清零）

`--plan` 的每个元素：

```json
{"finding_id": "f1", "decision": "accepted", "reason": "已修复并重查通过 / 经复核认定误报 / 已重分类",
 "recheck_by": "human:xzc"}
```

- **只有 `decision == "accepted"` 会关闭**（`open_blocking` 里消失）。
  `rejected` / `amended` 只记录、**不关闭**：写入后 `open_blocking` 仍在，
  `facts.not_closing` 会如实回报"未关闭"，别把"已答复"当成"已了结"。
- **误报也写 `accepted`**，并在 `reason` 里写明性质（"经复核认定误报，无需改代码"）。
  不要用 `rejected` 表达"我不同意"——那不会关闭，机制也不追溯翻转历史。
- `recheck_by` 必填且**不得等于提出者**——后果是"同一份报告不能自证"（校验细节见机制稿，本 skill 只写后果）。
- `accepted` 只能表示「**处置结果已成立**」：① 已修复且已重查通过 ② 经复核认定误报 ③ 已重分类。
  **「同意某种修法但还没做」不得写 `accepted`**——finding 会立刻从 `open_blocking` 消失，
  light 任务又没有 C4 兜底；此时保持 open，或写 `amended` + 理由（不关闭）。

## 处置时机与类型的对应

`review-decide` 按**当前工作区内容**重算锚点；代码改过之后旧轮报告就失配，在旧轮补处置必被拒。
两条合法路径各自对应不同处置类型：

| 路径 | 只适用于 | 为什么 |
|---|---|---|
| 随 **fail 轮**那次 `review-decide` 一并写 | 误报 / 重分类（处置结果无需改代码即成立） | 内容未变，锚点仍匹配 |
| 随**修好 + 重查之后的新一轮** `review-decide` 捎带 | 「已修复」 | 内容必然已变，必须在新锚点下判 |

> 人数与异种由**报告文件名**判定（`review-<agent>.md`）；两个报告同名即视为同一 CLI，会被拒。

## fail 之后：谁修、怎么算收敛

`review-decide` 判 fail 不是终点，也不是"把建议登记完"就结束。收敛由本会话按下面三步完成：

1. 在**当前批准触碰面内**修（要碰面外路径：单点且人同意直接改时走轻量通道——`authorize record` 一条 `choice=expand` 后按 `wf-continue` 扩面段处理；批量扩面/改验收口径才回 Plan 扩范围）；
2. 重跑 `task-check`（旧 Check 与旧锚点一律失效，不能沿用旧 pass）；
3. 外发确认**同任务、同材料类集合持续有效**（见 `wf-continue`「复杂任务审查」——仅换任务或新增材料类才需人重签，不逐轮重取），新锚点上直接 `review-launch` 重新判。

- 轮次不设上限；"这轮算过"的唯一依据是 `review-decide` 的 pass 加上既有 disposition 关闭事实，
  不是"报告读完了"或"建议都登记了"。
- 本轮有**主会话复核与主会话采信的报告都未覆盖的轴**时 `review-decide` 输出需人裁决（`WF_SEMANTIC_DECISION`）：主会话能补就补，补不了才由人写接受文件（`by/at/quote/source` + `task` + `round` + `axes`）后用 `--gap-acceptance` 重判；缺口既不判 fail，也不等于审查通过。
- 关闭证据与处置类型见 `wf-repair-loop`「这条 blocking 真的修了吗」；定位与写权事实见 `wf-continue`。

## pass 之后：建议取舍与主动收敛

- `review-decide` 判 pass 后，纯建议**不阻塞收工**。逐条判断本轮是否采纳：明显值得且不改验收/范围才改。
  采纳后按**锚点重算结果**判断后果（机制事实，不按改动类型的文字分类推断）：
  改动进交付面 ⇒ 内容指纹变化 ⇒ 重跑 Check + 发新轮；改动落在框架自有资产（`.wf/` vendor 面，
  `control_plane_digest` 入锚点）⇒ 锚点失效 ⇒ 重跑 Check + 发新轮；只改任务内非判定叙述或
  审查处置记录 ⇒ 锚点不变 ⇒ 报告继续有效——拿不准就重算锚点比对，以工具输出为准
  （完整判定口径见 `wf-continue`「复杂任务审查」与 `wf-repair-loop`，此处不重复论述）。不要拿旧 pass 掩盖实质变更。
- **多条采纳合成一批**：把本轮要采纳的建议一次改完，再重跑一次 Check、发一轮审查即可；
  逐条判断的是"是否采纳"，不是"每条各走一遍门禁"（同一批改动落在同一份新锚点下被审）。
- 不采纳的留档并写明理由（影响面、为什么不值得本轮做、是否留作后续）；不要为了“把所有建议都做完”无限加轮。
- 没有未关闭 blocking、缺口已接受或无需缺口时，准备收工材料（Check 结果、未核实项、待提交路径），交人调用 `wf-finish`；不要停在“报告读完了”。

## 判定边界

`review-decide` 的 pass/fail 由入口按已落盘事实与 AI 声明推导（人数、CLI 差异、锚点、主会话复核与采信报告的覆盖、未关闭 blocking；声明本身不被机制验证）；本 skill 不给 verdict。
单 reviewer 默认不产生判定；人签残余风险接受（`--single-reviewer-acceptance`）时留痕降级可判定——
完整口径见 `wf-review` 适用面，此处不重复论述。

## 纪律

- 运行纪律见 `.wf/workflows/session-flow.md`「运行约定」：身份只经信封或宿主映射通道；不代人作答；入口输出是唯一判定源；解释器整会话固定、失效即停。

## 来源与差异

| 项 | 值 |
|---|---|
| 来源 | 本仓库全局 `skills/multi-cli-review-action`（一次性适配源） |
| 许可 | 跟随本仓库（内部私有源，无第三方 NOTICE 义务；上游为同作者资产） |
| 基线 | 适配基线＝本仓库上述源文件；本副本为唯一发行件，上游改动不自动流入 |
| 差异 | 只读指定轮次并先汇总后决策，写回 dispositions 而非直接改记录 |
| 最近正例 | 任务记录 `validation.md` §19：两异种 reviewer 的两份报告按轴汇总、主会话写五轴复核后，把处置写成 `--plan` 的 dispositions 元素，`review-decide` 据此判 pass |
| 最近反例 | 同节：同一 CLI 占两个槽位时 `review-decide` **拒绝输入、不产生 verdict**（旧版曾记为 fail，已按设计稿 §6.5 修订）；把汇总与决策混写会让判定无法回溯到具体报告 |
