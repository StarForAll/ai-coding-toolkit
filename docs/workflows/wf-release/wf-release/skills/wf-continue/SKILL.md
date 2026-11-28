---
name: wf-continue
description: 推进 当前绑定对象（继续/开工/Check/暂停/收工）：批准规划、开工、Check、暂停/恢复、收工、策展、知识处置、复盘、归属裁决、审查记录。
disable-model-invocation: false
---

# wf-continue

> **判断指引**：实施期的归属与扩面判断见下节「实施期要自己判的几件事」；关闭证据见 `wf-repair-loop`；收工四项见 `wf-finish`。

已启用会话内的推进入口。先确认本会话已 `wf-start` 启用且绑定一致，再按当前状态路由。
门禁规则在 `.wf/workflows/task-flow.md` 与 `session-flow.md`，本 skill 只做路由。

**持续推进**：在现有授权与批准目标内，持续完成调查、实现、必要修复、验证与下一步准备，直到完成条件满足或出现需要人新增授权/改变承诺/明确人判的事项。不因一个 skill 段落结束、一条命令返回或一份报告读完而停下；也不要为“把所有建议做完”无限加轮。

## 路由

| 当前状态 | 动作 |
|---|---|
| 未开工 / plan，未批准 | 呈现 PRD 机读块、复杂度与 TDD（取值与理由取批准入口只读骨架里的 `complexity_proposal`/`tdd`，不要自己猜分级），请人批准 → `task-approve`（决定文件形状见 `wf help task-approve`） |
| 已批准，未开工 | 先看批准结果的 warnings：TDD 提示「未由人确认」时，把缺省值告诉人即可（设计允许按缺省执行，记录已记 `tdd_source`；要记成人的选择或改值，补 `plan.tdd` 重批），然后 `task-start`；复杂分级缺决定在批准时已被拒，不会再出现在本步 |
| in_progress/execute | 在批准触碰面内实施（开工前已存在的未提交路径若出现在 `preexisting_in_scope` 事实里：先按快照、提交和 WIP 证据判它是本任务交付还是外来——外来走排除声明，是本任务交付就继续；只有证据冲突、或必须决定接管/排除/提交时才问人，判断口径见下节「实施期要自己判的几件事」）；读规则用 `spec --file <path>`；需要时 `task-curate`。**单点面外扩展**：触碰面外一个具体路径、人又同意直接改时，走轻量通道——`authorize record` 一条 `choice=expand` + paths=该路径，`delivery_set` 会把它纳入本次交付；只有改验收口径/批量扩面才回 Plan 重批，不为单点走完整 replan。
**改仓库级规则文件（.gitignore/依赖清单/锁文件/CI 配置等——提交时按 K6 第 5 类确认拦截）**：改动前先取得人的同意；**改动完成后立即** `wf authorize record`（choice=repo_rules + paths + quote/by/source）落档——入口按内容摘要绑定确认，**确认之后再改内容即失效**，需按新内容重新 record。record 必须发生在改动之后（绑定的是实际生效的内容）；人先口头同意、改动、record 落档是认可顺序 |
| in_progress/check | `task-check`；实例任务的**步骤契约**（必做动作/步骤内人判点/声明验证）也在这里兑现——动作结果用 `--decision` 的 `choice=done|waived`（subject 含动作 id）记录；要留一次针对性红测用 `--run-verification`（不产生 Check 结论）。双轴结论与决定输入的字段形状见 `wf help task-check`（拿不准先取只读骨架）。**你要判的是**：双轴结论与依据够不够；人工验收/直接验收的结论是否绑定"人当时看到的交付内容"（内容变了旧结论不沿用——入口会用 `content_digest` 核它，缺该值就按未通过处理）；重复调试的「同一问题/不同问题」是你在授权内的裁定，不要套用验收字段 |
| 需要记录知识处置（Check/归档前） | `task-knowledge`（取值域见 `wf help task-knowledge`）；spec 变更走 `wf-spec-update` skill（`spec-update`），先看后改 |
| 复盘触发（入口 facts 的触发集合非空） | `task-retrospect`（结论写在 evidence 的 `conclusion`，形状见 `wf help task-retrospect`）；触发项与证据缺口由入口 facts 给出，不自行缩减 |
| 需要返工或替换 | **先取人签决定**（`choice=返工/rework` 或 `替换`；返工/替换是 §1.1 封闭清单，不由 AI 代作）→ `task-rework`（建 R、挂起 T、继承前置）/ `task-replace`（先可取只读预览）。**R 是 T 的交接承接方**：T 的保留 WIP 不挡 R 的绑定/取写权；但**普通任务** T 已暂停仍绑定本会话，本会话不能 `bind R`——由人**新开终端/新执行边界**后 `bind --task R`（即使不并行也必须换执行边界）；实例内任务按 `run advance` 的游标定位。R 完成后由 `task-reassess` 清挂起并核销 T 的旧登记（机制稿 §6.2 是定义位，`wf help task-rework` 给形状） |
| 任务挂起需要复评 | `task-reassess`（单任务复评；未挂起时幂等返回、不写记录） |
| 建/删依赖边 | `dep`（建/删边形态见 `wf help dep`）；前置状态与顺序由入口校验，不手改记录 |
| 基线/项目配置变更 | `baseline-apply`（先只读预览，再由人的批准决定承载）→ 只在已批准任务内，spec 变更走 `wf-spec-update` |
| 用户工作流定义编辑/校验 | **未绑定会话**才走准备通道：`definition prepare`（先取人的准备范围授权，见 `wf-start`）/ `definition validate`。**已绑定任务或实例的会话不要走它**——入口会报 `WF_BINDING_MISMATCH`；改定义回当前任务的 Plan 重新批准（触碰面覆盖该路径即可），实例推进用 `run advance` |
| 开工/Check/取写权报 `WF_WORKSPACE_UNRESOLVED` | **先把来源分清**：写权前置报的是“其他对象的未处置 WIP”，入口给 `facts.blocked` 与 `exits`——由各持有方实际处置（提交/移走/具名承接）或人 `repair`，排除声明与回 Plan 对该变体无效；开工/Check 的 c 档外来改动才走排除声明。然后：已批准触碰面内的未提交路径按归属规则记录；已提交的历史改动才用 `task-attribute` 裁决归属。人确认"不属于本任务、保持原样"时，写一份排除声明（`choice=排除外来改动` + `paths` + `by/at/quote/source`），用该入口的排除声明输入重跑。面外路径不猜，回 Plan 或请人确认；排除按记录时摘要绑定，内容一变即失效，且不构成提交授权 |
| in_progress/finish | **先读修复态**（见下节），把 Check 结果、未核实项、待提交路径准备好，再请人核对后由人调用 `wf-finish`；准备完成前不停止。决定文件结构拿不准时先跑 `archive` 的只读草稿（只打印不落盘）。试点期可跑一次 `sampling pick`（先冻结再落盘；不跑不阻断，入口会在 Check next_ 里提示） |
| 人**明确要求**改方案 | 先取人签的 `choice=replan` 决定文件 → `task-replan` → 重新 `task-approve` → `task-start`（缺决定即 `WF_SEMANTIC_DECISION`） |
| PRD 只改排版/转义等、验收与触碰面不变（机械修订） | 取人签的 `choice=机械修订` 决定 → `task-approve`：入口经等价链核验后**不重复人批**，回到执行继续。该签认是对散文等价性（只改排版/转义）的人签，"不重复问人"由"不重复批准"承载；前置是本任务已有批准（改语义仍走上一行的 replan，不经 task-replan） |
| 写权被占用 / 交接中间态 | 读 `status --short` 的 `writer{state,checkpoint,handover}`：接收方（`handover.receiver_session_key` 是本会话）运行 `writer-handover accept`；发起方/第三方等其接收或 `repair`；`checkpoint` 是最后核实点，按它核对占据者是否仍在动作 |
| 暂停 / 恢复（任务） | `task-pause` / `task-resume` |
| 绑定对象是**实例**（`run locate` 显示 `terminal=null`） | `run advance` 推进；`run pause` 受控暂停；只读回读用 `run locate` |
| 实例处于暂停态（`paused=true`） | 先读 `paused_reason`（原因/时间/停在哪一步）；解除与继续的判读见下节「实例暂停之后」 |
| 收工 | `stop`（一个去向，取值域见 `wf help stop`）；先看后定用它的只读预览 |
| 放弃 | `task-abandon`（**有未提交改动时必须逐项给去向**，覆盖 `preview.uncommitted`；形状见 `wf help task-abandon`）。提交范围含删除时另需 K6 第 2 类确认：**删除前** `authorize record` 一条 `choice=delete`（paths 覆盖被删路径——摘要绑定被删时的内容；先删后 record 绑不上、会被拒） |
| `status=archived` 但记录仍在活动区（归档中断：终态已写、目录未移） | 若写权已被释放，先 `writer acquire`（对象来自会话绑定）；再**重入 `archive`（同一决定）续做**。该入口会补做目录移动，不另开恢复命令 |
| 归档成功但回显 `write_release.released=false` | 按回显事实重跑 `writer release`（对象已终态，`ensure_releasable` 放行）；正常归档成功时入口已自动释放 |

## 修复态先读什么（⑥）

进入 finish、或收到 `fail` / `unavailable` / 报告损坏 / 换实施宿主的信号时，先读事实再动作：

命令与对象：`status`（短视图：四条件 + exits + 确定阻断，旗标见 `wf help status`）与 `gate`
（到期时点为归档前，取值与旗标见 `wf help gate`）。

- `repair_scope` 的四组事实与 `exits` 怎么读：见 `wf-repair-loop`。
- **不要用 `archive` 试归档探路**：为什么不行、还差什么该从哪里读，完整论述见
  `wf-repair-loop`「不要试归档探路」，此处不重复。
- 要人裁放行不可核实证据时，用 `wf-review-accept-unknown`（先按 `wf-review-accept-unknown`
  skill 呈现事实与采集 quote）。

## 实施期要自己判的几件事（这些不是机制结论）

- **交付面**：逐路径判"这是我改的 / 不确定 / 别人的"。框架给信号（开工快照、提交 trailer、他人 WIP 声明），
  **信号是输入不是判决**；"不确定"必须给理由。多算＝把别人的活提交了；少算＝漏审自己的交付。
  依据写进 `judgments add`（kind=归属）。人的挑战：「这几条为什么算你的？我不认会不会漏掉你的交付？」
- **扩面**：要碰批准面之外的文件时，先判每条新路径对应哪个问题、为什么非改不可、总量是否该回 Plan 重批；
  **判断 → 提出 → 人确认 → 才修改**（先改后补授权属越界修改，机制按 K6 第 4 类拦）。
  人的挑战：「这些新文件是哪条问题逼出来的？总量是不是该回计划？」
- **补测试 vs 改验证定义**：为已批准的验证项补测试文件是你的事，不需要回 Plan；若要在 PRD 里
  **新增/改一条验证项**（新的必需证据），那是改验收证据、不是等价实现，属规划变化，走回 Plan 重批。
- **vendor_dirty / 框架自有改动**：`status`/`task-check`/归档回显的 `vendor_dirty` 非空即说明工作区有
  `.wf/**` 框架自有改动——它不阻断推进，但**去向**要人裁一次（回源仓库立项/另开任务/保持现场），
  属「偏离裁决」的那一类；一直不裁，就会把框架缺陷悄悄并入业务任务。
  这条只在**真要定去向**时才成为停点。先自己核实是哪些路径、影响了什么：去向还没被后续动作
  逼定时，可先继续未受影响的活（Check 失效要重跑这件事照做），不要读成"停下等答复"。
  确认留痕走判断记录（可审计）：按 `wf help judgments` 的 inputs 写一条判断条目——判断类取
  「框架改动」一类、内容写归属去向（回源仓库立项/另开任务/保持现场）、依据与 `by=human`，
  经 `judgments add` 入库（判断类写在条目里而不是旗标上；task-check/归档回显的
  `vendor_judgments` 可见）。回源仓库立项的修复在源仓库按补丁/记录立项，归属与取舍仍是人判。
  不要把它当业务交付或审查材料：现场改 vendor 升级会丢、也不进提交。改 `.wf/**`
  会使当前 Check 失效（`WF_CHECK_STALE`——锚点的 `control_plane_digest` 随 vendor 内容
  变化），这是预期后果、不是误报；drift 的 `d:control_plane_paths` 会列出变化的框架
  文件清单。当前任务只记录“发现框架缺陷”的归属与边界。回源仓库立项的修复在源仓库
  按补丁/记录立项：运行系统级 `wf upgrade` 的只读导出子操作 `--export-deviations`（在项目内或
  `wf --project <绝对路径> upgrade` 的同一子操作）只读导出本地偏离补丁与
  `manifest.json`；导出基线是登记源的最新发行，**不取写权、不暂停任务、不改安装记录**，未接受项标
  `status=pending`。导出后仍由人把补丁带入源仓库、按作者仓库流程修复并发版；源仓库修复
  发版后再 `wf upgrade`（应用）升级回目标项目并重跑 Check——现场改 `.wf` 的旧
  Check 失效是预期。手工 `git diff` 只在导出不可用情形作兜底。
  不要把导出当成“已接受偏离”或“已回源”。这不算违反：只读 `.wf` 状态、读取/导出安装记录；
  改 `.wf/**` 才需要归属确认与回源。
- **本机判断偏好**：本机可把某类判断设为"必须交人"或"自定"（`wf prefs show` 查看；取值与旗标见
  `wf help prefs`）。设为必须交人时，该类只能写 `escalated` 交人，写 `applied` 会被 `judgments add` 拒；
  设为自定时的越界升级要在条目里写清为什么判断不了。偏好是本地用户设置，不是项目契约，不要改写它。
- **与人的限制冲突**（"别动 `.wf/`""不要提交""先别装依赖"）：停下并报告冲突点、你选的做法与影响；
  不自行取舍、不隐瞒、不改限制本身。冲突无法调和时停下报告是合法终态。

## 实例推进怎么读（`run advance`）

`run advance` 每次只做一件确定的事，并把**判断留给你**。先读 `facts`，再决定下一步：

| `facts` | 含义 | 你该做什么 |
|---|---|---|
| 有 `task`、无 `waiting` | 首达该任务步骤，已建任务（`run_id`=本实例、顺序前置=上一个未略过 task 步骤的任务），游标指向它 | 在那个任务上走四阶段（Plan→批准→开工→Check→Finish→由人归档）。**实例不代批准、不代归档** |
| `waiting: true` | 当前步骤的任务还没正常归档（含"还在做"与"异常归档"两种，异常归档会另报 `WF_SEMANTIC_DECISION`） | 回到那个任务推进；**任务还没归档时**异常处置是确认放弃范围与逐项去向（保留/反向修正/具名承接），写 `choice=放弃` 停止决定 + `--disposition`，交 `task-abandon`；**任务已异常归档后**实例层只剩两条路：`run terminate` 逐任务处置（放弃/保留），或由人裁定 `task-replace` 后继后重建推进——不要再对已归档任务跑 `task-abandon`，也不要靠再 advance 一次绕过 |
| `skipped: true` | 该步骤按 `creation.steps` 声明略过，决定已记录 | 继续 `advance`；若你认为这个决定此时不成立（条件变了），回人确认，不要自己改记录 |
| `answer: <choice>` | human 步骤的答复已记录 | 继续 `advance`；答复内容由人给，不要代答 |
| `settled: <step>` | 上一任务已正常归档且持久化可核，该步骤记 `satisfied` | 继续 `advance` 推进下一步 |
| `WF_DEPENDENCY_UNMET` | 顺序前置（上一个未略过 task 步骤的任务）尚未正常归档 | 先把那个任务做完并归档；不要删边绕过，也不要把异常归档当满足 |
| 所有步骤都有结果 | 实例的业务步骤都记了结果 | 正常结束走 `run finish`，异常终止走 `run terminate`（均已交付）；不要用 `advance` 反复试探 |

**你负责的判断**：某步骤的产物够不够用、能不能记"复用"（机制目前不生成复用事实，需要你自己在任务里核）、
某个可略步骤此时是否还成立、当前任务的缺口是否该回 Plan。

## 实例暂停之后

`run pause` 会把实例标 `paused` **并暂停当前步骤的任务**（否则那个任务还是执行候选，别人能接着干），
**不动游标**。所以解除时有两件事，它们是**两个决定**：

1. **解除实例暂停**：`run resume`（可选决定文件，见下）。机制只清 `paused` 并记录谁/何时/依据，
   **不恢复任务、不动游标、不推进**。
2. **是否恢复当前任务**：另跑 `task-resume`（它会核真实 WIP 指纹、身份与前置）。**不要顺手替人做第二个决定**：
   人可能只想先解除实例暂停、让任务继续停着。

恢复后从 `cursor` 继续 `advance`，**不要跳到下一步**（跳过该步的合法路径只有 `creation.steps` 声明 + 决定）。
**命令形态以 `wf help <命令>` 为准**：本表只说"这一步该读什么事实、该做什么判断"，不复述旗标与字段清单
（两处各写一份就会漂移——`gate --due` 曾在帮助里支持 `after_archive`、实现却拒绝，六轮复核已修）。

决定文件是**可选**的：单纯解除不必写；当人有附加约束（"先恢复但 task X 别动"）或这次恢复需要留痕时，
用决定文件记录——机制会把它存进 `resumed.decision`，并核 `subject` 与本实例当前暂停时点匹配（拿旧决定清新暂停会被拒）。

## 复杂任务审查

发起前**先取人外发范围确认**：`authorize record` 一条 choice=export（task + materials
["diff","requirement","test_results"] + quote/by/source；结构拿不准先跑
`authorize record` 的只读骨架（`--draft`）取）——没有它 review-launch 会报
`WF_EXPORT_NOT_AUTHORIZED`（外发确认绑任务与材料类集合）。**同一任务、同一材料类集合的
确认持续有效**：只有换任务或新增材料类才需要人重签，后续轮次直接发起即可，不要每轮
机械重签。外发属 K6 第③类不可逆动作，这个一次性范围确认是安全底线。
**授权的边界（显式声明）**：确认覆盖的是材料**类**集合，不覆盖每轮的具体内容——
每轮材料内容由批准触碰面、交付集合与排除面约束并随 Check 重跑重新生成；
人签字前可用 `review-launch` 的只读预览核对本轮路径清单与日志文件摘要，
但不必每轮重看（内容变化的约束是范围规则，不是这份签字）。
然后：`review-launch`（实施 CLI 由人声明，请求文件可选，入口按当前对象生成） → 人按回显文本在 reviewer CLI 里调用 `wf-review`
→ `review-import`（**一次调用导入本轮全部已完成报告**，轮次显式给：`--round <n>`；有失败槽位按回显 `import_errors` 逐个处置） → `review-decide` 的主会话复核骨架 → 主会话填写五轴复核 → `review-decide` 正式判定（轮次显式给：缺省取最大发起轮，恢复较早一轮会导错——见 `wf-review-action` 第 1 步）。
报告是辅助证据，主会话必须在判定前完成自己的逐轴复核；报告未覆盖的轴，主会话能核实就自己补，补不了才交人接受缺口。
单 reviewer 判定需人签残余风险接受（`review-decide` 的留痕降级，不默认；
骨架用它的只读草稿生成）；完整口径见 `wf-review` 适用面。

## 证据文件纪律（按"谁生成"分类）

真实 dogfood 发现：把"入口该生成的结构"写成文件，会让任务目录膨胀、并迫使模型读源码猜字段。因此：

- **入口生成、不要手写**：验证结果（`task-check` 记）、门禁预览（`gate`）、提交清单与摘要（`archive` 记）、
  审查材料与轮次记录（`review-*` 记）、安装/维护回执。这些一旦由模型自述，就会和真实事实分叉。
- **人/模型按命令契约填写的输入**：决定文件、主会话复核、双轴审查结论、spec/知识变更、
  处置数组、判断条目、复盘证据、外来改动排除声明。它们不是"五类白名单"能穷举的：**命令名与字段形状
  以 `wf help <命令>` 的 `inputs` 为准**；多数命令另有只读骨架，先用骨架再填（骨架只打印、不落盘、不消费输入）。
- 决定内容必须是人已明确给出的选择，模型只负责按它转录（作决定与转录是两件事）。
- 需要知道输入结构：`<python> <项目根>/.wf/bin/wf.py help <命令>`（有最小示例，不必读源码）。
- "决定文件只能转录人的答复"**不覆盖诊断裁定**：重复调试的「同一问题/不同问题」由你在授权内判（见
  `wf-diagnosing-bugs`），`task-check` 的决定输入记录的是你的裁定与依据，不是等人的签字；证据不足以
  区分根因时才交人。

## 不做

- 不调用 `wf-finish`、不发起正常收工归档、不自行提交（`archive` 的 commit 授权与 `stop` 的
  commit 去向都只在拿到精确路径授权时由对应入口执行）。
  这不算违反：归档中断（`status=archived` 未移目录）按上面路由表重入 `archive` 续做；在批准触碰面内
  改业务文件；按精确路径授权由归档/`stop` 入口执行提交。
- 不替人回答 `plan-q`、不伪造 review 结论。

## 工作习惯（唯一完整定义位）

- **同一终端同时只推进一个任务**；并行请另开终端/窗口。
  同一终端里的第二个 agent 会被 `WF_IDENTITY_UNRESOLVED(concurrent_unregistered_caller)` 阻断，
  须人显式 `wf.py enable` 登记后才放行，且此后与前者共享同一执行会话。
- **自动模式下不需要手写信封**：直接跑 `wf.py <子命令>`；身份由执行边界派生，
  写权代次由本会话运行态携带（显式 `inputs.generation` 可覆盖，不填不报错）。

## 纪律

- 运行纪律见 `.wf/workflows/session-flow.md`「运行约定」：身份只经信封或宿主映射通道；不代人作答；入口输出是唯一判定源；解释器整会话固定、失效即停。
- **机制已经判过的事不要重新论证，也不要找路绕过**：归属分类、范围核对、锚点失效、写权代次、实例游标、
  输入必填与类型 —— 这些是事实与阻断，不是"建议"。按 `facts` 修正或按 `next` 换路；判不了就交人，不编依据。
