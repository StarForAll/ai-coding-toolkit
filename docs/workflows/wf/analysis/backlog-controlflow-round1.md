# backlog：控制流修复轮（2026-11-27，Round 1）

> 本轮（Goal 控制流卡点修复）调查中确认成立、但**不属本轮交付面**的项。
> 登记格式：结论 / 证据 / 归属轮次或待裁事项。清单不静默丢弃，也不作为本轮完成条件。

## 1. 已落地（2026-11-27 方案①）：普通任务返工交接的 WIP 承接（F1，成立·高危）

**结论**：普通任务绑定分支的 `task-rework` 之后，新会话**绑不上 R**。

**证据**：
- `wflib/tasks.py::cmd_task_rework` 的普通任务分支：写 `paused=true` + `handoff.wip{paths=未提交交付, resolved=None}`，
  在入口内 `writer release`，`next_` 写"在新会话绑定 R"。
- `wflib/cli.py::wip_blockers`（经 `assert_no_foreign_wip`，bind/acquire/task-new 三处调用）把**其他活动任务**的
  未处置 retained WIP 一律视为外来 → 新会话绑定 R 时命中 `WF_WORKSPACE_UNRESOLVED`。
- 框架自己的 `repro/task-rework-handover.py` 在 bind R 前先 `git add -A && git commit -m "dispose wip"`——
  即"唯一能走通的处置"是把审查 fail 的未提交实现提交入库（绕过提交授权）。
- 契约冲突：机制稿 §6.2「普通任务绑定则 T 显式暂停、保存交接/工作区并 release，新会话绑定 R」；
  §4.3/§4.4 的 WIP 判定把"其他对象的未处置保留 WIP"与请求范围重叠即阻断。R 与 T 不同对象 → 按字面必挡。

**为何不属本轮**：这是两份契约条款的**互相冲突**（`wf-design-revision-gate.md` B 档：稿内矛盾必须人裁选一侧），
改实现即等于单方面选边；本轮已把事实、三条候选方案与推荐整理在此，等裁。

**候选方案（需人裁一条）**：
1. **让 `wip_blockers` 认返工谱系为合法承接方**（推荐）：绑定对象 R 的 `rework_of == T` 时，T 的 retained WIP
   不挡 R 的 bind/acquire（R 是 T 的交接承接收方，处置权来自谱系而非会话）。机制稿 §6.2 补一句
   「R 是 T 的交接承接方，T 的保留 WIP 不构成 R 的授予写权阻断；R 处置后按 WIP 记录核销」。
2. **返工改走独立承接记录**：`task-rework` 把 T 的 WIP 登记成"承接给 R"的具名记录，`wip_blockers` 按记录放行。
3. **明确"返工前先处置 T 的 WIP"**：在 `task-rework` 入口要求 T 的 WIP 先提交/反向修正/具名承接，
   把出口写进 `next_`（但这与"被否实现不应入库"的直觉冲突，需要人确认哪种语义）。

**补充事实**：同 anchor 下 `enable --new-session` 在对象非终态时被 `WF_BINDING_MISMATCH` 拒绝，
所以"新会话"只能是真正的新执行边界；这一点与机制稿 §1.3/§3.4 一致，不是缺陷。

**更正（第二轮独立复审）**：`cli.wip_blockers` 对"其他活动对象的保留 WIP"是**无条件阻断**，
不按"与请求范围是否重叠"筛（`cli.py` 的 `wip_blockers` 遍历全部活动任务，不做重叠判定）。
本节原写"与请求范围重叠即阻断"不准确——存在重叠豁免的错觉会让人去找一条不存在的路。
另：本项与 backlog 之外已修的 d 档出口同属「机制算出事实却没有本步可执行出口」家族；
本轮只修了 d 档（check 的 `facts.exits`），返工交接这条因涉及契约冲突留待裁决。

## 2. 候选改进：repro 注入片段的静态自检

`repro/*.py` 的 `FROM` 是写死的源码片段；实现改动后脚本只会报 `repro stale`（前置失败），
而 `run_all.sh` 的 green 面不执行 `patch`，默认只跑 green 时漂移不会被发现
（本轮 `stale-writer-facts` 由 `--repro both` 抓到）。建议在 T0 层加一条自检：
对可静态解析的 `H.patch(os.path.join(..., ".wf/lib/wflib/<f>.py"), FROM, TO)` 调用，
断言 FROM 仍存在于 `payload/lib/wflib/<f>.py`（无法静态解析的跳过并计数）。
理由：`wf-delivery-discipline.md` §3 要求注入可达；这是该义务的机械守卫。

## 3. 文档同步（A 档，纯过时）

- `docs/workflows/wf-framework-implementation.md` §6.2 的 D03/D07/D11 行仍写"未交付：`WF_CAPABILITY_UNAVAILABLE`"、
  §5.4 的「轮次串行门禁」段仍写 `task-rework`/`task-replace` 返回不可用；同文 §4 的实现表已写"2026-11-12 已交付"。
- `docs/workflows/wf-framework-design.index.md` 第 52/76/97/100 行的语义消费列仍写"两轮失败/两轮后返工"，
  而设计稿 §4.3 与机制稿 §9.2 已明确"不设轮次上限"（2026-11-09 人裁）。
- 处置建议：按 revision gate 的 A 档同批同步正文与索引，跑 `validate-wf-design.py`；不改变任何判定。

## 4. 已核实不成立（不登记为缺陷，留作证据）

- 单 reviewer 拒绝（`WF_REVIEW_INVALID` + 人签降级通道）、`scope-exceptions` 不再一义多用（只由 `axes: uncovered` 承载）、
  `task-new` 返回旧任务重试结果、`enable` 无轮换、`task-rework` 能力桩、归档后写权自动释放与 persist_pending 期间拒绝释放、
  `--generation` 必填 —— 均在历史会话中成立，当前源码已修并有断言或复现覆盖。
- dsh 部署表 `env:DSH_SESSION_ID` 的声明与实际可见性差异：已知边界，处置记录在 `dogfood-round5-dispositions.md` b-P2#1。
## 5. `review-decide` 的 anchor_stale 出口分档（已补断言，2026-11-27 第四轮复审后）

出口分档收敛为 `review.review_input_exits(blockers)` 一处实现（消费 `anchor_stale`
token，不按 `problems[].reason` 措辞反推），并由 `test_review_input_exits.py` 两条用例覆盖（anchor_stale 在/不在）；第三例（同输入重复断言）
已按第七轮复审删除。

## 6. 已处置但值得记录的判据（R3 发现 1/2）

- d 档 `facts.exits` 已分档：报告方先交还写权（普通任务 `task-pause`→`writer release`、实例任务
  `run pause`→`writer release`），再由**持有方**（`handoff.wip` 只由普通任务的 `stop`/rework 普通分支写入，
  所以持有方必然是普通任务）用 `stop` 的 `commit`/`transfer`/`reverse` 处置，`wf repair` 只兜底写权记录残留。
  `keep` 会登记保留 WIP、反过来挡住承接方。实例报告方重取写权的问题已由 `wip_blockers` 按实例归属排除修复。
- 码表 `WF_SCOPE_UNRESOLVED` 的出口与 `facts.exits` 对齐为「人裁决只决定由谁处置、不解除 d」，
  机制稿 §11.1 该行与 §0.1 修订摘要同批同步（描述级，不改判定）。

## 7. 待裁：d 档出口的"本任务先交还写权"前提（R4 发现 5）

d 报错发生在 `task-check`（本会话持有唯一写权），持有方当刻拿不到写权；可走通的完整序是
「本任务 pause→release → 持有方 bind/acquire→stop(commit/reverse/transfer) → 本任务重新
bind/acquire → 重跑 check」。出口已写明第一步（交还写权并处置自身未提交交付），但若本任务还有
**其它**未提交的批准面内路径，持有方 bind 仍会被 `wip_blockers` 的 `owned_dirty` 无条件挡住——
这正是本文 §1 待裁的同一契约冲突。是否要求 d 档出口把 4 步全序列写全、或先裁 §1 的承接规则，
需人定。
## 8. 已落地（2026-11-27 人裁）：keep 判据收紧到本任务 e 桶（R5 发现 3）

`tasks.stop_work` 的 `keep` 只核批准面覆盖（`covered(item, touch)`），不排除 d/c 路径；同一路径
出现两份保留登记时，`wip_blockers` 的 `explicit` 先到先得，谁挡住谁取决于 `.wf/tasks` 排序。
机制稿 §4.3 已写禁令，实现未落实（C 档：收紧到稿子）。修它会改变 `stop --keep` 的拒绝面，
需要同批核存量记录与出口，登记为下一轮候选。

## 9. 相邻未修（R5 发现 6）

同一原因码的其他 raise 仍无 `facts.exits`：`check.governance`（`WF_SCOPE_UNRESOLVED`）、
`baseline-apply` 的目标类/触碰面（`WF_SCOPE_VIOLATION`）、`spec` 目标未覆盖。码表通用出口可接受，
但"拒绝必须给可执行出口"的原则未覆盖它们；登记为下一轮候选。

装配面仍未断言：`review-decide` 把 `report_facts["blockers"]` 传入 `review_input_exits` 的这一行
没有端到端用例（纯函数测试在 `test_review_input_exits.py`，signature 已去掉死参 `problems`）。
建议下一轮用 `review-report-boundary` 型夹具造"导入后 Check 重跑换锚点"再断 `exits[0]`。

## 10. 已落地（2026-11-27 口径乙）：实例写权作用域是否等同"同对象"（R7 发现 3）

`wip_blockers` 现按绑定对象排除（2026-11-27 人裁后为聚焦＋谱系，不再用 `tasks._task_in_run`）：`kind=run` 时把实例的**当前任务与返工谱系**
（步骤任务、受控返工 R、R 已归档后的恢复目标 T）视为"自己"。这收窄了"其他对象的未处置保留 WIP"
的阻断面，与机制稿 §4.3/§4.4 字面（"其他对象、实例下一任务…先要求实际处置"）方向相反。
需人裁一句口径：作用域内任务是否等同同对象（并同批改 §4.3/§4.4），或收窄到仅 `cursor.task_id`。
与 §1（返工交接 WIP 承接）耦合。

## 11. 相邻未修：`assert_no_foreign_wip` 无 `facts.exits`（R7 发现 5）

`WF_WORKSPACE_UNRESOLVED` 只给 `blocked` + 一句 `next_`，`wf-continue` 对该码的指引
（排除声明 / 回 Plan）对"他任务未处置 WIP"变体无效。建议给 exits（指名 `blocked[].task` 的处置序）。

## 12. 已收口：空转断言与端到端缺口（R7 发现 4）

`test_review_input_exits.py` 的第三例（与第 1/2 例同输入再断言）已删除；`review-decide` 装配面的
端到端断言（导入后重跑 Check 换锚点 → `exits[0]` 指向新一轮）仍缺，见 §5 末段。

## 13. 待裁：`stop --transfer` 之后该路径在写权前置面没有归属（R8/R9 发现）

`stop --transfer` 只写 `resolved`，`transferred_to` 全仓无消费点；`cross_task_conflicts` 跳过 resolved。
第九轮复审内存模拟：A transfer 后，**承接方**取写权（S1）与**任何覆盖该路径的第三方**取写权（S2）
都 `blocked == []`——即不存在"承接方被原持有方挡住"，真实残余方向是"路径在写权前置面无归属"。
第三方可把该路径算进自己交付并在授权提交时一并入库；缓解是 `preexisting_in_scope` 会把开工前
已脏的面内路径作为非阻断事实列出（设计稿 §4.2 九轮 b-1），但开工后才变脏时无事实。
需人裁：①`transfer` 记录承接方并由写权前置按它精确豁免/阻断；②或规定 transfer 后该路径的
交付归属与提交责任（当前由承接方/第三方按检查面处理）。
另：把"已处置登记"写进全局 `explicit` 会掩盖第三方未登记脏改动（第八轮 F1），已回退。

## 14. 已收口：非 anchor 输入问题的首条出口（R8 发现 3）

`review-decide` 的 `WF_REVIEW_INVALID` 非 anchor 分支首条已改为 `review-launch` 开新一轮
（已导入槽位的报告摘要不可替换，同轮补报告对它们不可执行）；"补齐报告"降为"槽位尚未导入"的次选。
`test_review_input_exits.py` 断言随之改为首条含 `review-launch`。

## 15. 口径观察（R9 发现 7）

run 记录缺失报 `WF_HISTORY_UNRESOLVED`（`cli.wip_blockers`），而机制稿 §11.1 的 `WF_TARGET_MISSING`
行写"绑定的对象不存在（任务/实例记录缺失）"；`tasks.write_scope` 早有同款选择。是否统一为
`WF_TARGET_MISSING` 待下一轮口径整理（不影响放行，只影响归因与出口）。

## 16. 登记：`WF_WORKSPACE_UNRESOLVED` 的三面不一致（R10 发现 3）

- `protocol/codes.json` 的 exit 只描述 c 档（外来未提交改动 + `--workspace-exclusion` 重跑 task-check），
  但同一码现在也被 `assert_no_foreign_wip`（写权前置）用于"他任务未处置 WIP"变体——排除声明/重跑
  Check 对该变体不可执行；
- 机制稿 §12.3「WIP 保留」验收行（`wf-framework-mechanism.md` 的 WIP 行）把该场景写成
  `WF_WIP_UNRESOLVED`（blocked），与运行期的码（`WF_WORKSPACE_UNRESOLVED`）与档位（needs_decision）都不符；
- backlog §11 只登记了"缺 exits/wf-continue 指引"。

需人裁/下一轮：统一码与档位（或分开两码），并同批改码表、§11.1、§12.3 与三处出口文案。

## 17. 已按人裁落地与残留（2026-11-27）

四项裁决已落地：返工谱系豁免（§1 方案①，含 `task-reassess` 核销点）、实例作用域聚焦＋谱系（§10 口径乙）、
`stop --keep` 归属收紧（§8）、d 档出口按对象形态条件化（§7）。残留：
- 核销点（`task-reassess` 把 T 的 wip 记为 `rework-completed`）**无独立断言**——复用 reassess 需要
  完整写权/锁桩，登记为下一轮补；
- `stop --keep` 双登记的先到先得仍是既有行为（人裁只要求不据此放行）；
- `§16`（`WF_WORKSPACE_UNRESOLVED` 三面一致）与 `§13`（transfer 后归属）仍待裁/未修。

## 18. 待裁：实例任务没有"提交自身交付"的入口（R11 发现 1）

实例形态 d 档出口要求报告方处置自身未提交交付，但实例任务不能 `stop`（`WF_BINDING_MISMATCH`），
`archive` 需要有效 Check（d 正挡住），`keep` 被收紧禁掉 → 实例步骤任务若还有其它面内未提交交付，
唯一可走的是 `run pause`→`writer release`，而持有方 `bind`/`acquire` 仍被该任务 `e∩dirty` 挡住
（`owned_dirty` 无条件计入）。需人裁：①允许实例任务调用与 `stop --commit` 等价的提交入口（人签 grant）；
②或明确"实例任务的自身交付由人在 Git 层处置后重新取权"；③或把实例步骤任务的 `e∩dirty` 从
"阻断持有方 bind"里豁免（与 §13 的归属窗口同族）。

## 19. 待裁：`task-reassess` 核销点不核实际处置（R11 发现 5）

清挂起时无条件把 T 的 wip 记为 `rework-completed`，不核这些路径是否已 dirty/已被 R 覆盖；
同族 `task-resume` 要"确已处置（still == []）"才写解除。若 R 的触碰面未覆盖 T 的全部遗留路径，
核销后这些改动失去唯一登记（可被面覆盖它的任务捎带）。需人裁：核 dirty 交叠再核销，或转人处置。

## 20. 待裁：`stop --commit` 未收窄 subject（R11 发现 9）

只收紧了 keep。人签 grant（可含 glob）可把 d/c 档路径一并提交，从而"用提交绕过 d 档"。
机制稿 §4.3 只禁了 keep 例外；是否把"无归属、跨任务混杂、外来改动"同口径扩到 commit 需人裁。

## 21. 已补断言（test_stop_ownership.py 两例）：keep/commit 归属拒绝面

`stop --keep` 的 e 桶归属收紧目前无断言（现有 keep 夹具路径都在 e 档，回退注入仍绿）。
补法：构造 d/c 路径写进 keep subject → 断言 `WF_WORKSPACE_UNRESOLVED` + `facts.foreign`。
构造 `stop_work` 的完整写权/锁桩成本高于本轮收口，登记下一轮。

## 22. 待裁：keep 的"面内但归属不明"残留（R12 发现 1，本轮先按事实处理）

`stop --keep` 已把 subject 收窄到本任务 e 桶（拒绝 d/c/面外）。但 e 桶**不含归属证明**：
开工前就在工作区、归属未确认的路径（`preexisting_in_scope`）仍在 e 桶里。
本轮曾试图机械拒绝这类路径，实测会打断既有合法收工（`stop-preview-readonly`、`stop-under-lock`、
`snapshot-missing-stop`、`reinstall-preserves-data` 四个 repro 与三个 keep 套件），且与设计稿 §4.2
九轮 b-1"这类路径只证明允许改、仍进交付并事实上抛，不是门禁"冲突——已回退为**不落任何字段**：事实由 Check/status 的 `preexisting_in_scope` 上抛。是否对它们设门禁（要求先出排除声明）需人裁；
若设，须同批改设计稿 §4.2/§4.4 与四个 repro 的夹具，并核存量记录。

## 23. 已补断言（test_startup_probe.py）：startup ⑩ 的 exclude_scope

`tasks.startup_check` 的 WIP 项改按 `exclude_scope` 后，全仓无测试引用 `startup_check`。
放行风险低（bind/acquire 前端仍拦），但事实面会静默少报一条阻断；与 §21 同批补。

## 24. 已同步：设计稿的返工谱系例外（R12 发现 2）

设计稿 §4.2/§4.4/§5.4 已补"返工谱系例外见 §5.6"，§5.6 补承接方与核销点；机制稿 §0.1 的
design.md 输入摘要同批更新（validate-wf-design 输入摘要 4/4、覆盖率 100%/100%）。

## 25. 待补断言：核销"全或不动"（下一轮独立小轮）

`stop --keep` 的 e 桶拒绝、`startup_check` 的 `exclude_scope`、`task-reassess` 的核销三处均无区分力断言
（删掉实现仍全绿）。构造 stop 的完整写权/锁桩成本高；`startup_check` 可直接构造 task + mock `cli.wip_blockers`
断言调用参数；核销可 mock 写权与 action。与 §21/§23 同批补。

## 26. 已修：Check 面的谱系例外（R13 发现 1）

`scope.cross_task_conflicts` 现跳过"当前任务 R 的 `rework_of` 来源 T"的登记，机制稿 §3.5/§6.2 同批注明；
否则写权前置放行、R 的 `task-check` 仍被 T 挡回 d 档。

## 27. 已修：settled 豁免绑内容（R13 发现 2）

`wip_blockers` 的已处置豁免改按 `wip.paths[].digest` 与当前指纹比对，失配即恢复阻断（此前按路径永久豁免，
已 resolved 后再变脏不阻断，第三方可捎带）。

## 28. 第二轮人裁落地（2026-11-27，8 项）

按用户裁决表落地：§22 keep 不设门禁（设计稿 §4.4 补 b-1 延伸）、§18 实例 d 出口改写（Git 层 + `task-attribute`，
实例内提交入口登记为后续能力）、§20 commit/reverse 同口径收窄（归属检查在授权覆盖之后，保既有码序）、
§19 核销"全或不动"（仍有工作区差异时不核销，facts 报 `unresolved_after_rework`）、§13 消费 `transferred_to`
（承接方名下归属；第三方被承接方挡，承接方自取不被挡）、§16 三面统一（码表 exit 补写权前置变体、§12.3 行改
`WF_WORKSPACE_UNRESOLVED`/needs_decision、§11.1 措辞）、§11 `assert_no_foreign_wip` 补 `facts.exits`、
§3 文档同步（实现稿 D03/D07/D11 与轮次串行门禁、索引四行"两轮"）。
验证：T0 2186 OK；全量 157 GATE-OK（run_id …38670d7a8992）；validate-wf-design 100%/100%、doc-refs 0、analysis 0。
仍缺断言：keep/commit/reverse 拒绝面、startup ⑩、核销条件（§21/§23/§25）。

## 29. 待裁：`stop --commit` 的 e 桶面窄于 `delivery_set` 待提交面（R14 发现 3）

`stop --draft` 用 `pending_delivery_paths`（`delivery_set ∩ uncommitted`，含未释放策展路径与
`.wf/baseline.md`/`.wf/project-config.json`）预填 subject，而 `stop --commit` 的归属门禁只认 e 桶——
按 draft 原样执行必被拒（这些路径落在 c 桶）。同一路径在 `archive` 提交通道是允许的。
需人裁：①改 draft 预填为 e∩dirty；②或在 §4.3 声明 stop 提交面窄于交付面并同步帮助；
③或让 commit 接受 delivery_set 口径（但需先定义这些路径的归属）。

## 30. 已补断言（test_wip_blockers_scope.py 匹配/失配对照）：settled 摘要失配

`test_wip_blockers_scope.py` 把 `fingerprint.item` 恒定 patch 为同一摘要，因此"已 resolved 路径
再变脏即恢复阻断"（第十三轮 F2 的修复）没有区分力断言。补法：两组用例（摘要匹配 / 失配）+ 可变 mock。

## 31. 已修：R14 的 6 项（2026-11-28）

run 绑定的 transfer 承接方匹配按写权作用域（实例内承接任务不再被自己挡）、`stop --reverse` 去掉
不可达的 e 桶归属门禁（保留 dirty 判据）、`assert_no_foreign_wip` 的 exits 去掉对写权前置无效的排除声明、
d 档形态判据改为"在途实例"（异常终止实例的保留任务走普通任务出口）、索引第 100 行"两轮"清理、
backlog §22 的 `unconfirmed_ownership` 声称与实现对齐（不落字段，事实由 `preexisting_in_scope` 上抛）。

## 32. 待裁：transfer 承接方归档后的阻断出口（R15 发现 5）

`wip_blockers` 的 `transfers` 阻断不核承接任务活性：承接方 S 已归档而路径仍 dirty 时，
`blocked[].task` 指向不可执行的持有方，三条 exits 都走不通；实际可走的是让原持有方 A 重新登记
（`stop --keep` 覆盖 wip，transfers 随之消失）。需人裁：是否核承接任务活性并给"原持有方重新登记"出口。

## 33. 待裁：§12.3/§4.4 ⑩ 的 WIP 变体仍给两个码（R15 发现 6）

运行期该路径只出 `WF_WORKSPACE_UNRESOLVED`（`assert_no_foreign_wip` 唯一 raise），但机制稿 §12.3 另一行
与 §4.4 ⑩ 仍写 `WF_WIP_UNRESOLVED`（维护组面才用）。需人裁：统一为一码并同批改 §12.3 两行、§4.4 ⑩ 与码表；
或声明"两码分工"并改 §12.3 的 WIP 行。

## 34. 已修：R15 的 2 条文档不一致（F1/F2）与 2 条断言缺口（F3/F4）

`wf-finish` 的出口表与码表/运行期对齐；机制稿 §4.3 的 reverse 归属口径回改；新增
`test_requester_matches_run_scope`（实例 cursor 承接任务不被自己挡）与
`test_abnormal_instance_task_uses_plain_exits`（异常终止实例的保留任务走普通出口）。

## 35. 已修：挂起复评触发面把合法 suspended 当未知残留（R16 发现 1，高危）

`_reassess_empty_set` 原对任何 `suspended` 记录抛 `WF_HISTORY_UNRESOLVED`——而挂起是 `task-rework`
写入的合法状态，导致**每次返工闭环收尾的 archive** 在终态落盘+提交后报错且不释放写权，
`status`/`status --short` 在挂起期间也不可用，出口还要求手改判定字段（跳过 §6.2 核销）。
现改为：返回 `suspended_tasks/conditions/waiting` 事实（清挂起仍走持写权会话的 `task-reassess`）；
`startup_check` 把该事实并入 findings（`step=reassess,status=waiting`）；归档 facts 带 `reassessment`。
新增 `test_reassess_trigger.py`（3 例：合法挂起报告不抛、空集合、条件求值失败降级）。
F2（实现稿 D12/D13「未交付」）同批同步为「2026-11-12 已交付」。

## 36. 观察：d 档实例用例靠"run 记录缺失"回落取支（R16 观察）

`test_instance_reporter_uses_run_pause_and_run_resume` 未 mock `load_run`，钉住的是"记录缺失视为在途"
这一子句；建议补一例 `{"terminal": None}` 正例，避免将来按 `wip_blockers` 口径改判为
`WF_HISTORY_UNRESOLVED` 时该断言阻碍修正。

## 37. 已补断言（test_startup_probe.py）：复评投影在固定顺序之后

`test_reassess_trigger.py` 只测纯函数；全仓无测试引用 `startup_check`；唯一消费 startup facts 的
repro 夹具无挂起任务；没有"兄弟任务挂起时 archive"的用例。以下注入全绿：删 startup finding、
删 archive `reassessment`、让 archive 在 waiting 时 raise。与 §23 同族，下一批用 repro 补。

## 38. 待裁：文档要求"执行复评"，实现恒只报告（R17 发现 4）

设计稿 §5.4 与机制稿 §5.3 写"归档后/启动后**执行**复评，持写权且目标可写时执行"；实现（R16 修复）
两条路径都只报告事实（清挂起由持写权会话的 `task-reassess` 做）。同实例 R 归档时可满足文档前提，
故文档与实现方向相反。需人选边：改稿（触发面只给事实）或补实现（触发面在可写时自动清挂起）。
R17 亦确认：两分支的 `task-reassess` 入口都可达，无新死路。

## 39. 已落地（2026-11-28 人裁）：subject 字面化（stop 预检拒 glob）

`stop --keep|--commit` 的归属门禁按**字面成员**比 e 桶，而同函数其余判据（`covered`/`unlisted`/
`out_of_scope`）把 subject 当**模式**（`pkg/**` 能过覆盖核却被判 foreign）。帮助只写"路径或承接对象"，
机制稿未声明必须字面。需人裁：统一到字面并写进帮助/§4.3，或先按 `covered` 归一后比较。
（旧形态本身不严谨：`pkg/**` 会被指纹记成 deleted；与 §29 同族。）

## 40. 已修：启动顺序与复评投影（R18 发现 1）

`STARTUP_STEPS` 恢复七步；复评事实改为**固定顺序之后**的第 8 项投影（`waiting|unknown`），不占序位、
不改首报项；实现稿的覆盖面声明与机制稿 §5.2/§5.3 同批登记；陈旧注释删除。

## 41. 已落地（2026-11-28 人裁：补齐实例三探针；⑧⑨在 run 绑定分支仍缺，见 §60）

`STARTUP_OUT_OF_SCOPE` 与实现稿 514 仍以"实例属于第二轮"排除 ⑥（未结束实例的快照/游标/任务归属/结束中断），
但 run advance/pause/terminate 已交付（同文 536 与 D11–D13 已改）。`status` 的实例分支走 `startup_check(ctx)`
（无 task）→ 无任何实例项，并非"由别处核"。需人裁：补实现（实例侧启动事实）或改稿并登记新的排除理由。

## 42. 已修：R19 的 3 项（2026-11-28）

F1（过时口径三处：help purpose / session-flow / wf-continue——`task-reassess` 现已单任务语义）；
F2（`wip_blockers` 的 transfer/settled 归属从**含归档记录**构建：转移方归档后第三方仍被承接方挡）；
F3（`assert_no_foreign_wip` 第 2 条出口改为"人裁决只决定由谁处置、处置走第一条"——原"judgments 落账"无消费点且需写权）。

## 43. 已修：R20 的 3 项（2026-11-28）

F1（链式 transfer 归属按 `resolved.at` 收敛到最近一次，不再按目录名顺序；归档记录不会覆盖较新承接方；
新增 `test_chained_transfer_owner_is_latest`）；F2（写权前置 exits 覆盖 `blocked[].preparation` 变体，
码表同批）；F3（wf-finish 与 wf-continue 对齐："人裁决只决定由谁处置、不解除阻断"）。

## 44. 待裁补充：§32 的"原持有方重新登记"出口不可执行（R20 证据）

R20 复核：被 transfers 挡住的 A 若要 `stop --keep` 重新登记，必须先取写权，而取写权会再次被同一条
transfers 条目挡住 → A 无法自救；§32 的候选出口应改为 `repair` 或由承接方处置。

## 45. 已落地（2026-11-28 人裁）：谱系闭包（附断言 test_nested_rework_lineage_is_transitive 含对照）

`cli.wip_blockers` 的 task 支只比 `bound_record.rework_of` 一层，`scope.cross_task_conflicts` 的 d 档也只跳一层；
run 支按 `sequence_changes` 可跨层。对返工任务再返工（入口允许）时：普通任务支 `bind R2` 被祖父 T 挡回
`WF_WORKSPACE_UNRESOLVED`（方案①的卡点复现），实例支 bind 放行但 Check 回 d 档（§26 的不一致复现）。
需人裁：①把谱系做成传递闭包并同步 §4.3/§4.4；②或明确"只承接一层"、把 run 支对齐并在 §6.2 写明。

## 46. 待裁：实例记录缺失的两种解释与出口不可执行（R21 发现 5）

`check.py` 把"run 记录缺失"当在途实例（选实例出口），而 `cli.wip_blockers` 对同一事实报
`WF_HISTORY_UNRESOLVED`。d 档首条出口（`run pause`→`writer release`）在该状态下必报
`WF_HISTORY_UNRESOLVED`（runs.py），"拒绝必须给可执行出口"落空。需人裁：是否让 check 与
`wip_blockers` 同口径报 history 问题（或改出口）。

## 47. 待裁：run 族代次面未实现（R23 发现 2；R22 曾声称登记但未落盘）

实现稿 240 行称 `run advance/pause/terminate` 必须携带代次且不符判 `WF_GENERATION_STALE`，但 runs 的
advance/pause/finish/terminate/resume 只手工核 state/held/holder.id，从不 `resolve_generation`；
唯独 `_return_from_rework` 调 `ctx.require_held(run=…)`——同一 `run advance` 的普通路径与返工返回路径
态度相反。`run finish`/`run resume` 不在 must-carry 清单。需人裁：补实现（`require_held(run=)` + 补表）
或在 §2.2 如实声明"实例族只核 holder/scope"。无任何 run 族的 `WF_GENERATION_STALE` 用例。

## 48. 已落地（2026-11-28 人裁）：R 不允许 task 绑定；锚点补实例快照（断言 test_rework_bind_scope.py）

`binding_state` 只看 `task.run_id`（R 为 BINDING_NONE），`_eligible_task_bind` 放行，`ready` 把 R 当普通任务，
task 绑定不经 run 的 paused/terminal 守卫。若判定"不允许"：实例 paused 后另一会话仍可 bind R 写它，
绕开"暂停冻结其任务写入"；若判定"允许"：需按 task 口径重写守卫与 Check 锚点（R 的锚点缺 workflow_snapshot）。
反证材料：`repro/task-rework.py` 断言 R 不自动加入实例；设计 §5.6 又写"R 同属该实例"。

## 49. 已修：R23 的 F1/F3/F4（2026-11-28）

F1（d 档形态判据：受控返工 R 无 run_id 但经 `sequence_changes` 属于在途实例 → 实例支出口，
不再给 run 绑定会话必失败的 stop 出口）；F3（审查锚点"同锚点换 check_id 继续有效"的旧口径订正 4 处：
实现稿、review.py docstring/注释、delivery-discipline spec）；F4（`task-rework-handover` 断言交接 WIP
每项为 `fingerprint.item`，含 path+digest）。

## 50. 已落地：§1/§10 的 2026-11-27 裁决

§1（返工承接 WIP）按方案①谱系豁免落地；§10（实例作用域）按口径乙聚焦＋谱系落地。两节正文保留作证据链，
状态以本条与 §17 为准。

## 51. 已修：R24 的 F24-1/F24-2/F24-3/F24-4（2026-11-28）

F24-3（新死路）：d 档出口改由**会话绑定形态**决定（run 绑定→实例支；task 绑定→普通支；任务形态只作关联
事实，`bound_kind is None` 时才回落任务/实例事实）。两个新用例钉住两向：run 绑定的受控返工 R 走实例出口、
task 绑定的实例任务走普通出口。
F24-1：上述两例即该分支的区分力断言（删掉绑定判据、回退到只看 `task.run_id` 都会红）。
F24-2：锚点"同锚点换 check_id 继续有效"的口径补订 6 处（delivery-discipline §14 两处、实现稿 436、
wf-review skill、`check_next_hint` 两处、`cli` 两处）。
F24-4：码表 `WF_SCOPE_UNRESOLVED.exit` 补形态分档与恢复序（与 §11.1 对齐）。

## 52. 已修：R25 的 2 项文档/验收口径（2026-11-28）

F1：delivery-discipline §14 残留半句"导入/判定同时核报告 `check-anchor.check_id`"改为"核 `check_anchor`；
`check_id` 只在锚点也不同时判失效"；实现稿 439 同族表述补"（同锚点换 `check_id` 有效）"。
F2：设计稿 §8.2「日常收工」验收行的 positive 补"（返工谱系例外见 §5.6）"、negative 限定为
"非返工谱系的换对象/进实例下一任务/普通升级"；机制稿 §0.1 的 design 摘要同批更新。

## 53. 复审收敛记录（R19–R25）

| 轮次 | 新增成立 | 其中 runtime/行为面 | 处置 |
|---|---|---|---|
| R19 | 4 | 3（transfer 跨归档、过时口径、出口） | 全修 |
| R20 | 3 | 3（链式 transfer、preparation 出口、finish 口径） | 全修 |
| R21 | 5 | 1（rework 交接 WIP 形状） | 修 4、登记 2 |
| R22 | 5 | 2（run resume 段、锚点口径 4 处） | 修 4、登记 1 |
| R23 | 5+1 | 1（d 档形态，产品级） | 修 4、登记 2 |
| R24 | 4 | 1（d 档按绑定形态，新死路） | 全修 |
| R25 | 2 | **0**（仅文档/验收口径） | 全修 |

R25 首次出现"runtime 侧无新成立项"。剩余全部为已登记待裁（§29/§32+§44/§33/§38/§39/§41/§45/§46/§47/§48）
与断言缺口（§21/§23/§25/§30/§37）。

## 54. 已修：R26 的 2 项码值/文案（2026-11-28）

F-1：`archive_precheck` 的"完全无提交授权"改报 `WF_COMMIT_NOT_AUTHORIZED`（与 `changes_persisted_fact`
同条件同码）；"有授权但未覆盖"仍报 `WF_WIP_UNRESOLVED`。cp3 套件 19/19 通过。
F-2：删 `codes.json` 的 `WF_SCOPE_UNRESOLVED.exit` 编辑残留「原句：…」；机制稿 §11.1 同行补
"stop 可用（choice 取 commit/transfer/reverse，keep 不适用）"与治理面变体说明，两处对齐。

## 55. 复审收敛终局（R25–R26）

R25：runtime 侧 0 新成立项（2 项文档/验收口径，已修）。
R26：runtime 侧 0 新成立项、0 新死路（2 项码值/文案，已修）；抽查的 7 条高风险相邻路径全部落在
已登记 backlog 或"不成立"。
剩余：待裁项 §29/§32+§44/§33/§38/§39/§41/§45/§46/§47/§48；
断言缺口 §21/§23/§25/§30/§37。二者均已在册，按 Goal 不作为完成条件，需人裁/授权推进。

## 56. 第三轮人裁落地（2026-11-28，9/10 项）

§48：`_eligible_task_bind` 拒绝"在途实例的受控返工 R"的 task 绑定（出口绑实例）；`workflow_snapshot_digest`
对 R 解析所属在途实例、锚点含实例快照。
§47：**已实施**（见 §59）。
§45：谱系闭包——`wip_blockers._mine` 与 `scope.cross_task_conflicts` 沿 `rework_of` 上溯全部祖先。
§46：`check` 在 d 档前对"实例记录缺失"同口径报 `WF_HISTORY_UNRESOLVED`（出口 repair/§5.5）。
§38：设计稿 §5.4 与机制稿 §5.3 改为"触发面只报告事实，清挂起由持写权 `task-reassess` 执行"。
§39：`stop` 预检拒绝 glob/通配 subject（只收字面路径，出口改写/排除声明）。
§41：`startup_check` 新增 `_instance_startup_probe`（快照/游标/结束中断三探针），`STARTUP_STEPS` 加 `instances`，
`STARTUP_OUT_OF_SCOPE` 删除"实例属第二轮"，实现稿 514 同步。
§29：`stop --draft` 预填改为 e 桶 ∩ 未提交（与 `--commit` 归口同口径）。
§32+§44：`transfers` 承接方失效（归档/不存在）时回落原持有方。
§33：§12.3 行声明两码分工（写权前置=WORKSPACE；归档/维护门禁=WIP）。

## 57. 未实施：§47 run 族代次面（R22 起登记，第三轮裁决要求补实现）

`runs` 五入口加 `ctx.require_held(run=…)` 要求代次三处一致；但 `resolve_generation` 缺代次即
`WF_GENERATION_STALE`，会连带要求**全部 run 夹具**携带代次并同步 must-carry 表（实现稿 240）与
`finish/resume` 入清单。本轮余量不足以完成该批夹具改造与契约同步；已完成的部分是：缺口事实、
修法方向（两选一）与 `WF_GENERATION_STALE` 的 run 族用例清单已在 §47 记录。下一轮独立实施。

## 58. 待补断言：§45 闭包与 §48 绑定拦截（2026-11-28）

§45 的二层嵌套（R2 的祖父 T 不再阻断、d 档不判争抢）与 §48 的"R 的 task 绑定被拒/锚点含实例快照"
均无区分力断言；§46 的 history 出口分支由既有 d 桶用例的 mock 改造间接覆盖（在途 run 记录）。
下轮补 §45/§48 各 1–2 例。

## 59. 已实施：§47 run 族代次面（2026-11-28）

五个写入口统一 `ctx.require_held(run=…)`：`advance`/`pause`/`resume` 在锁内入口核；`finish` 在
"已结束"只读诊断之后、真实写路径之前核；`terminate` 在"写权不可核→只读收停止请求"分支之后、
非预览时核（保留 §7.4 的窄例外与 §5.2 的重入诊断）。must-carry 表补 `run resume`/`run finish`。
新增 `test_run_generation.py`（四入口断言 STALE、terminate 断言只读收请求优先）与
`test_rework_bind_scope.py`（§48 两例）、`test_nested_rework_lineage_is_transitive`（§45 闭包）。
回归中修掉两处顺序副作用：`instance-task-phases`（终态诊断须先于代次核）与
`terminate-stop-request`（只读收请求须先于代次核）。

## 60. 已落地（2026-11-28）：启动面 ⑧⑨ 统一到两支；② 登记为入口自查

`startup_check` 的 marker/assets 两项只在 `task is not None` 分支内；run 绑定与未绑定会话的启动报告
缺 ⑧（写者标记锚点）与 ⑨（框架资产）。机制稿 §5.2 把二者列为固定顺序的无条件项；
② 会话写者与绑定的对应由各入口自查、启动报告面未列。`_instance_startup_probe` 的 blocked 项只有
英文自由文本 `problems`、无原因码与出口。修法：把 marker/assets 移出 task 分支（或 else 分支补发），
或把 ②⑧⑨ 的排除理由写进 `STARTUP_OUT_OF_SCOPE` 并同步实现稿 514 的计数句。

## 61. 已修：R27 的 F1/F2/F4/F5（2026-11-28）

F1：§45 闭包测试的夹具 id 撞车（child 与 grandparent 同 id → id 相等先行豁免，闭包从未被走），
改为独立 id 并加"链未相连必须阻断"的对照；
F2：`test_run_generation` 对五入口断言 `require_held` 的实参 `run=`，并补 terminate 写路径的
`WF_GENERATION_STALE` 用例（holder 本会话 + scope 正确）；
F4：本账本各节标题按实际证据更新（§21/§23/§30/§37 已补断言，§25 留待下一轮，§39/§41/§45/§48 已落地）；
F5：`ready` 对 §48 拒绝的 R 补 `run_in_flight` 细分（与实例内任务同形）。

## 62. 已修：R27 后续（2026-11-28）

§25：`test_reassess_consumption.py` 两例（残留→不核销并报路径、干净→核销）；`unresolved_after_rework`
归一为路径字符串（fact 面稳定）。
§60：marker/assets 移到 task/非 task 两支之后（⑧⑨ 对 run 绑定与未绑定会话也执行）；
`STARTUP_OUT_OF_SCOPE` 增 `writer-binding`（② 由入口自查），实现稿 514 同步。

## 63. 待补：侧车 `stop_request` 的清除点（R28 F4 后半）

`stop_request` 只在写权不可核时写入（runs.py 的 `_record_stop_request`），全仓无清除点：请求被真正
执行后仍留在侧车，下一次预览会再带出（现在已按 `run_id` 过滤，不再跨实例误导）。需人裁是否在
terminate 成功后清 `stop_request`（以及 preview 时是否提示"请求已被执行/作废"）。

## 64. 待裁：启动面 ① 的「代次」子项未核（R28 F5）

机制稿 §5.2 ① 明列代次；`startup_check` 只核 state/holder.id 并回显 generation，从不产出
`WF_GENERATION_STALE`。本批给 ② 的处理是"各入口自查、启动报告面不列"，同样理由适用于 ①。
需人裁：补一次比对（startup 里核会话代次）或把 ① 的代次子项登记进启动排除面。

## 65. 已修：R28 的 F1/F2/F3/F4/F6（2026-11-28）

F1（回归）：`ready` 的 `run_in_flight` 细分收窄到 §48 分支（BINDING_NONE + 谱系 reason），
正常结束/异常无许可/记录缺失不再被标成在途；
F2：`test_startup_probe` 断言 run 绑定会话也出 marker/assets，且 tempdir 下 assets 必 blocked；
F3：五入口的 `require_held` 断言具体 `run=` 值（不再 `mock.ANY`）；
F4：预览的 `pending_stop_request` 只带本实例（清除点登记 §63）；
F6：实现稿 514 计数句改为"④与②两项显式不在启动面"。

## 66. 已修：2026-11-28 独立复审的描述面与交接缺陷（F1.1/F3.4/F1.4/F3.1/F2.1/F2.2）

**触发与证据**（干净子代理只读复审 HEAD 3c090797，未改工作树）：
- F1.1/F3.4 **TDD 证据不在任何描述面**：`check._parse_review_notes` 从 review-notes 顶层读
  `tdd_evidence`，而 `wf help task-check` 的 `inputs.--review-notes` 只登记两轴、
  `--review-notes-draft` 骨架也只有两轴 → TDD 开启时按骨架填写必报 `WF_CHECK_FAILED`，只能读源码猜字段。
- F1.4 **交接两段的旗标漂移**：help 把 `--decision` 标成 accept 必填、`--to` 标成 begin 必填；
  实现是 begin 要求 `--to` **和** `--decision`，accept 不收任何参数（`--decision` 是死旗标，
  `COMMAND_SUB_FLAGS` 缺 writer-handover 条目，命令级并集放行）。
- F2.1/F2.2 **交接中间态不可发现、拒绝不可行动**：recovering 时 holder 已清空，
  `writer acquire` 与通用 `require_held` 都只回 `WF_WRITER_BUSY`，不点名
  `writer-handover accept`，也没有 exits/next。
- F3.1 **accept 抹掉检查点**：`writer.handover_accept` 被调用时不传 checkpoint，
  `status` 的 checkpoint 变 null，与 session-flow「补检查点」相反。

**处置（已落实现）**：
- help `task-check` 的 `--review-notes` 增 `tdd_evidence` 形状；`--review-notes-draft` 在
  `plan.tdd` 且 `tdd_applicability=code` 时生成该块并回显 `tdd_required`；`wf-tdd` 指明显式位置。
- help `writer-handover` 改为 begin 必填 `--to/--decision`、accept 不收 `--decision`；
  新增 `COMMAND_SUB_FLAGS["writer-handover"]`（begin 两旗标、accept 空集），accept 带
  `--decision` 现在按 `WF_USAGE_INVALID` 拒绝；示例改为 begin。
- 交接中间态的 `WF_WRITER_BUSY`（通用 `require_held`、`writer acquire`、`handover accept`）
  补齐 `writer_state/handover/exits/next`，recovering 时点名 `writer-handover accept`。
- `_handover_accept` 传 `checkpoint={step: handover-accepted, at, from, object}`；
  `session-flow` 的 accept 段同步「不收 --decision」。
- 断言：`test_task_check_draft` 新增 TDD 骨架两例；`test_help_contract` 新增
  DescriptionSurfaceTest 三例（inputs 登记、accept 拒收死旗标、`wf.py` 简写定义）；
  `repro/handover-two-stage.py` 新增两条目标断言（中间态点名 accept、accept 后检查点为
  handover-accepted）与第二个注入面（接受时抹掉检查点）。

**验证**：定向单测 20/20；`repro/run.sh --only handover-two-stage --mode both` GATE-OK
（run_id 1795834766152-2986444-c6395a19fae4）。

## 67. 已核实不成立 / 只做定义的最小修（2026-11-28 复审 F1.2、F2.3、F2.4、F2.5）

- F1.2（示例里的 `wf.py` 无定义）：成立的是"没有定义位"，不是"示例要全改"。本批在
  `session-flow` 运行约定里定义一次（`wf.py <子命令>` = `<解释器> .wf/bin/wf.py <子命令>`，
  项目根也可直接写 `.wf/bin/wf.py`），help 的 `hint/envelope` 同批改为可照抄形态；
  47 条示例保留简写，不再另造 PATH shim 或软链（新安装/卸载面，charter T5.5）。
- F2.3（首任务规模确认"无消费点"）：**不成立为无消费点**——`cumulative.confirmed_net`
  是 `scale.history_max` 的唯一输入，后者进入 `wf-finish` 预览的 `[规模]` 行；它是给人判断的事实，
  机制明令不设阈值。命令名（`sampling confirm`）与措辞摩擦登记为观察项，不升格门禁。
- F2.4（验证通过后无路可走）与 F2.5（已授权再确认）：复审逐条核对出口后**未发现真实实例**；
  与本账本 §53 的收敛结论一致。

## 68. 登记（不属本轮）：复审的其余相邻项

- F1.3 **repo_rules 改前同意与改后摘要的绑定缺口**：`authorize record` 在改动后按路径算摘要，
  人同意时被绑定内容尚不存在；record 只防"再改"，不证明人看过规模。属授权语义变更
  （设计稿 §4.2/K6 的确认对象），登记待裁，不在本轮改实现。
- F3.3 **旗标消费断言按命令级并集**：`command_introspection` 的消费集合是全部子动作并集，
  子命令级死旗标会漏（本批 F1.4 即由此躲过）。修法（真子命令级消费提取）影响全部帮助断言，
  成本高，登记下一轮。
- **交接发现面投影**：`status`/`enable` 目前不报"有交接给你"（只靠 begin 的 next_ 与人工转抄
  `session-key`）。新增投影是可选改进（新增字段与消费点），登记候选。
- **plan-q 行格式的静默不识别**：`PLAN_Q_RE` 只认行首 `plan-q-<n>：`，列表符号/编号会让
  `pending_plan_questions=[]`，冷启动实例为此读源码确认格式。模板注释已写"起始行"，机制可加
  "发现疑似 plan-q 行但不在行首"的可行动提示；登记候选。
- §63 侧车 `stop_request` 的清除点：**无消费者可见面**——`_terminate_preview` 对终态实例直接
  拒绝（`WF_BINDING_MISMATCH`），成功终止后预览不再带出该请求；清除只影响侧车字节，登记观察，不新增机制。
- §64 启动 ① 的代次子项：见 §69（需人裁契约方向）。

## 69. 待裁（契约级，2026-11-28 复审 F3.2 与 §1.1 三处）

- **设计稿未登记同边界轮换**：`enable --new-session` 已交付且机制稿 §1.4 有登记，
  设计稿 §1.3 仍写"同一执行边界内的下一个普通任务需要新的执行边界"，设计稿与索引无"轮换"。
  可选方向：①在设计稿 §1.3/§3 与索引登记同边界轮换（推荐，事实同步 + 回扫）；②保持设计稿，
  把 `--new-session` 降为机制实现细节并删 skill 指引。需具体修订授权。
- **§1.1 三处措辞**（复审第 5 项）：①「主动触发」——机制只核 activation 存在，不核调用者，
  建议写明"调用者由纪律约束、机制不核"；②「本地完整路径」——"外部服务不是前置"与"复杂任务
  审查需两个异种审查 CLI"同格易读成审查可省，建议把审查环境前提单列；③「强度如实声明」——
  建议补一句"review-decide 的 pass/fail 来自主会话五轴声明，机制只核人数/异名/锚点/未关闭 blocking"。
  均属设计稿修订（revision gate），未获授权前只登记。
- **§64 启动 ① 代次**：机制稿 §5.2 ① 明列代次与 `WF_GENERATION_STALE`，实现只回显
  `holder.generation`、从不判定（写入口已由 `require_held` 拦）。方向：①补一次只读比对
  （与 `require_held` 共用实现）；②把 ① 的代次子项登记为"入口自查、启动报告面不列"。
  两向都改契约文本，需人裁。

## 70. 已修：终审第二轮（交接发现面、唯一实现、checkpoint 消费者、TDD 谓词）

**输入**：2026-11-28 终审（干净子代理，只读 HEAD 3c090797 + 候选改动）指出上一批交接修复
"打在了错误的调用者上"：新增 `exits/next` 只在有绑定的会话可达，接收方真实路径
（enable/ready/bind/task-new/run create/definition prepare）没接上；`checkpoint` 只写不读；
TDD 谓词三处实现；`--review-notes` 的"复杂任务必填"与 Check 消费不符；begin 的 decision 内容
要求无机制。

**已修**：
- **单一交接出口**：`cli.writer_handover_projection` + `cli.writer_busy_error` 唯一实现；
  `require_held`、`writer acquire`、`bind`、`task-new`、`run create`、`definition prepare` 统一使用；
  recovering 点名 `writer-handover accept`，facts 带 `checkpoint` 与 `handover{from,receiver,object,invalidated_generation}`。
- **发现面**：`status` facts 增 `checkpoint` 与 `handover`（设计稿 §4.4 的消费者）；`ready` 对
  被交接对象标 `handover_pending`（不再当"就绪"）；`enable` 增 `facts.writer` 与
  `handover_for_me`，接收方 `next` 直接指向 accept。
- **拒绝可行动**：`handover accept` 的"非声明接收者/已绑另一对象"补 `next_`；begin 的 `next_`
  补"key 打错先按 `wf repair` 恢复"；不做接收者附件存在性校验——显式信封模式不落附件，
  校验会拒绝合法接收方（证据边界，登记 §71）。
- **checkpoint 消费**：`status`/`enable`/busy facts 输出；repro 断言从直读 `writer.json` 改为
  同时经 `status` 消费（订正 §66 F3.1 中"status 的 checkpoint 变 null"的表述——status 此前不输出该字段）。
- **TDD 谓词唯一**：`check.tdd_scope(plan, check=None)` 返回 `(required, applicability)`，
  Check 定稿/归档门禁/draft 骨架共用；`wf-tdd` 删除字段形状副本，改为指向
  `wf help task-check` inputs；`--review-notes-draft` 帮助说明 TDD 块与 `tdd_required`。
- **描述面订正**：`--review-notes` 改为"所有任务必填"（Check 双轴是固定步骤，轻量任务也消费）；
  `acceptance-fixtures.md` 的 begin 示例补 `--decision`；`wf-start` 增"接收写权交接"步骤
  （新执行边界 + enable 取 key + accept，不先 task-new/bind）。
- **断言**：新增 `test_handover_discovery.py`（busy 投影 recovering/held/maintenance、`tdd_scope`）；
  `handover-two-stage` 增接收方真实路径断言（ready 的 handover_pending、bind 点名 accept、
  enable `handover_for_me`、status 的 handover/checkpoint）与第三个注入面（删掉 accept 出口文案）。
- **验证**：定向单测通过；`repro --only handover-two-stage --mode both` GATE-OK
  （run_id 1795836572898-3442292-b6d59e12c55f）；T0 与全量见 §72。

## 71. 登记/证据边界（终审剩余，不属本轮）

- **begin 的 `--to` 存在性不可核实**：显式信封模式没有附件，auto 模式才有；本轮不做校验，
  只在 begin facts 回显 key、在 accept 拒绝时给出口。打错 key 的恢复仍是 `wf repair`
  （登记候选：auto 模式可核附件，混合模式不可靠）。
- **无 handover cancel**：交接中间态只能 accept 或 repair；新增取消入口须过 T5.5 缺口三问，
  本轮不做（终审明确不建议）。
- **`--to` 的跨会话转抄**：属跨会话外部通道，机制不替；`wf-start` 已写明取 key 与接收步骤。
- **`checkpoint` 的决定内容**：只投影交接元数据（from/receiver/object/invalidated_generation），
  `writer.handover.decision` 留审计面；终审建议不扩大投影。
- **`run create`/`definition prepare` recovering 路径**：已用统一 helper 补出口，但未写专项断言
  （前置重，repro 不覆盖）；登记下一轮补。

## 72. 已修：终审第三轮（准备范围交接、调用者角色、写后拒绝、谓词顺序等）

**输入**：2026-11-28 更新快照终审（干净子代理，只读 16 改 1 增）。结论摘录与处置：

**已修（本轮）**：
- **准备范围交接（高）**：`_handover_begin` 原无条件 `_require_instance_match`，未绑定会话的 preparation
  永远拿不到 begin；`accept` 又无条件给 preparation 写会话绑定（违反 §1.3/§4.4）。修法：
  `handover_begin_scope_problem`（未绑定只能交 preparation）+ `handover_accept_creates_binding`
  （preparation 不建绑定、不套工作区门禁）；accept 的 writer scope 仍为 preparation，接收方直接
  `definition prepare` 接续。纯决策有单测；**完整 preparation 交接的端到端断言仍缺（登记 §73）**。
- **`invalidated_generation` 消费（中）**：新增 `handover_generation_problem`，accept 前核
  `generation == invalidated + 1`；不符报 `WF_GENERATION_STALE` 并指 repair/重发 begin。单测覆盖。
- **TDD 谓词顺序（中）**：`tdd_scope` 改为 plan 优先、check 仅缺键回退；补冲突用例（旧 check docs +
  新 plan code 等）。
- **写权状态先于 WIP（中）**：`task-new`/`run create` 的 busy 判定移到 `assert_no_foreign_wip` 之前，
  接收方在发送方登记 WIP 时也能看到 accept 入口（WIP 门禁对普通路径不变）。
- **调用者角色（中）**：`writer_busy_error` 增 `you_are`（receiver/initiator/other，按 caller 与
  handover 的 from/receiver 判），next 改为"接收方 accept；发起方/第三方等其接收或 repair"；
  repro 断言 mid=initiator、bind=receiver。
- **`enable` 写后拒绝（中）**：writer 读改为容错 `writer_mod.load`（缺失按空闲），不再在写附件后抛
  `WF_CAPABILITY_UNAVAILABLE`；recovering 且本会话绑定已终态时，next 追加"之后轮换"。
- **status --short 投影（中）**：`--short` 现带 `writer{state,checkpoint,handover}`（skills 默认路由可见）；
  repro 增断言。
- **accept activation 单一判定（低）**：`_needs_activation` 覆盖 begin/accept，handler 不再重复调用。
- **轮换入口文案（低）**：recovering 下 `enable --new-session` 的 busy 出口改为"接收方先 accept 或 repair"。
- **描述面回扫（低）**：实现稿 begin 示例补 `--decision`；acceptance-fixtures 的 TDD 行证据改列
  `test_sixth_round_guards.py`/`test_single_verification.py`；repro 注释改为"begin 不核附件"。
- **ready 消费（低）**：`wf-start` 增"可先 `wf ready` 看候选与 `handover_pending`"；run 候选也标
  `handover_pending`。
- **TDD 形状一致性（低）**：单测改为从 `check.TDD_EVIDENCE_FIELDS` 派生（help inputs 与 draft 骨架
  各一条），加字段会同步变红；字面副本仍 3 处（常量/help 描述/骨架），由派生断言锁一致。
- **本地完整路径与强度声明的措辞**：本地完整路径补"经人重新评估后降级并留理由"（charter T4 的第三
  条，终审指出）；强度声明补"主会话复核存在、覆盖缺口的人签接受、材料身份 drift"的机制核对面；
  索引 138 行回扫并更新输入摘要。

**验证**：定向单测（含新 8 例）通过；handover repro both GATE-OK；T0/全量见 §74。

## 73. 登记（终审第三轮剩余，不属本轮）

- **preparation 交接端到端断言**：纯决策（begin 资格/accept 是否建绑定）已有单测，但"begin→accept→
  definition prepare 接续"的集成路径无夹具；登记下一轮补（需要 preparation 授权与未绑定会话夹具）。
- **TDD 字段形状仍 3 处字面**（常量/help 描述/骨架）：由 `TDD_EVIDENCE_FIELDS` 派生断言锁一致，
  但未把 help 描述表/骨架改为运行时派生；登记候选（避免为省一处字面引入 import 环）。
- **`ready` 的 preparation 对象无候选行**：ready 只列 task/run；准备范围交接的接收方靠 enable 的
  `handover_for_me` 与 wf-start 步骤，登记观察。
- **`activation.start_source="human:enable"` 由入口自写、无读取者**：字段名容易被读成"人调用证明"；
  改字段/删除属 schema 变更，登记候选（与本轮 §1.1 的"机制不核调用者"一致，但字段命名仍需单独裁）。
- **begin 的 `--to` 存在性**：显式信封不落附件，无法核；auto 模式可核但会误拒混合模式，维持 §71 的边界。

## 74. 终审第三轮后的验证记录

- T0：见 `tmp/wf-goal-round-new/t0-final4.log`（预期 2222 例，OK）。
- 全量：见 `tmp/wf-goal-round-new/run-full-final3.log`（预期 GATE-OK）。
- 设计/文本：`validate-wf-design` 100%/100%（输入摘要 4/4）、doc-refs 0、analysis 0、skills 25。

## 75. 已修：终审第四轮（准备交接出口/位置、status 短路、bind 顺序、key 形态）

**输入**：2026-11-28 终局定向复审（只读，18 M + 1 ??）。

- **准备范围交接（高）**：accept 成功后 `next_` 只写"按原对象记录继续"，`run create` 会被
  `_preparation_problems` 以"preparation belongs to another session"拒，而其出口（原会话创建/换会话）
  在交接后都不可执行。修法：accept 对 preparation 返回
  "在本会话重跑 `definition prepare --id <id>` 接续准备（记录转属本会话后 run create 才可用）"，
  `position` 用 `scope=maintenance`；`_preparation_problems` 的 exit 同批改为这条真出口。
- **`status --short` 的 writer 投影（中）**：原实现只在已绑定 task 分支；未绑定接收方与 run 绑定看不到。
  修法：`status` 顶层统一 `facts.writer{state,generation,holder,checkpoint,handover}`，`--short` 直接复制；
  repro 增"accept 前未绑定会话的 --short 投影"断言。
- **bind 顺序（中）**：`assert_no_foreign_wip` 仍在写权状态之前；recovering+第三方 WIP 会挡住 accept 指针。
  修法：`_resume_bind` 后先判写权状态，再核工作区。
- **`enable` 的写后拒绝（中）**：`writer_mod.load` 对损坏记录抛错、缺失返回空且 state=None。修法：
  函数入口用 `writer_snapshot`（缺失→空、损坏→`(空, True)`）读一次（写盘前）；损坏只加 warning 并
  投影 `writer{state:unknown,corrupt:true}`；缺失按空闲、不输出 `state:null`。
- **`--to` 形态校验（中）**：begin 之前不核 key 形态，粘贴错就进 recovering 无法重发。修法：
  `--to` 必须 64 位小写十六进制，否则 `WF_USAGE_INVALID` + 转抄出口（存在性仍受显式信封限制）。
- **描述面回扫（低）**：`session-flow` 删除"accept 不收 --decision"的参数复述（help 是唯一入口用法面）；
  设计稿 §1.1 本地完整路径补"满足轻量判据 + 重跑受影响检查"、强度声明把"才是"改"例如"、指令分工补
  "运行期命令形态（含 `wf.py` 简写）由 session-flow 定义一次"；索引/机制稿输入摘要同步。

**验证**：定向单测 28/28；handover repro both GATE-OK；T0/全量/设计校验见 §76。

## 76. 终审第四轮后的验证与剩余边界

- T0、全量、validate/doc-refs/analysis/skills 结果见 `tmp/wf-goal/worklog.md` 与 `tmp/wf-goal-round-new/`。
- 剩余边界：preparation 交接的**端到端**断言仍缺（begin→accept→definition prepare→run create 的顺序只由
  纯决策单测与静态走查覆盖）；`ready` 的 `handover_pending` 仍无专门出口文案；`activation.start_source`
  命名/消费者未核；TDD 形状仍有常量/help/骨架三处字面（派生断言锁一致）；`status --short` 的写入
  等价性未跑完整冷启动（H 是第三轮快照，未覆盖第四轮 incremental 改动）。

## 77. 已修与登记：终审第五轮（摘要范围、失效代次空判定、帮助内部矛盾、时序指引）

**输入**：2026-11-28 最终定向复核（只读）。

- **H1 机制稿摘要越界**：2026-11-28 段末"未改任何判定、字段、门禁或原因码"与本批代码差异相反。修法：
  改成"本段只改契约文本；同批代码侧变更（用法校验、facts 键、错误顺序等）见实现稿与各入口，
  不能按纯文案同步审阅"。
- **H2 失效代次空判定**：`handover_generation_problem` 在工具内无可达触发点（begin 后恒等、
  repair 清空 handover 后 accept 先报 busy），是"只有形式没有消费点"。修法：删除该函数/调用/单测；
  机制稿 §? "handover 消费 invalidated_generation"改为"保存失效代次供核对，交接中断由 repair 清空
  交接并恢复空闲（不另设工具内 stale 分支）"。
- **M2 时序不可达的发现事实**：`enable` 的 `handover_for_me` 只在 begin 之后为真，而接收方必须先
  enable 取 key；首次 enable 看到 `writer:null` 是正常。修法：`wf-start` 的接收段改成四步不可换序
  （① enable 取 key 并说明 writer 为空正常 → ② begin → ③ status --short/再次 enable 确认 receiver →
  ④ accept），并写明 key 打错只能 repair。
- **M3 task-check 帮助内部矛盾**：purpose 仍写"复杂任务还需双轴"，与 `--review-notes 所有任务必填`
  相反。修法：purpose 改"所有任务都要双轴内部审查"。
- **L1/L2/L4/ready 双读**：`writer_busy_error` docstring 收窄为"主要入口共用，run 族自有兜底保留"；
  `writer_snapshot` 非 dict 返回 `(空, True)`（损坏）；`enable.writer` 补 `holder`；`ready` 改用一次
  `writer_snapshot`（不再 per-task `ctx.writer()` + 另一次 load）。
- **登记（不属本轮）**：
  - **M1 `--to` 只核 64-hex 形态、不核接收方存在**：自动模式有附件可核，显式信封模式不落附件；
    混合模式无法安全区分，维持"形状校验 + 转抄核对 + 打错走 repair"的边界（§71 同族）。
  - **L3** `gates` 机械修订等价性另有一处 `or "code"` 默认（语义不同，登记候选）；
  - **L5** `begin --decision` 的审计消费面（人/审计）未单独登记，防止下轮误删（backlog 记录）；
  - **preparation 交接端到端断言**仍缺（纯决策单测 + 静态走查）；**最终快照冷启动未再复跑**
    （第五轮为文档/工具/时序改动，start 路径未变；以 H 的快照为最近冷启动证据，边界如实写）。

**验证**：定向单测 27/27；handover repro both GATE-OK；T0/全量/校验见 §78。

## 78. 终审第五轮后的验证

- T0、全量、validate/doc-refs/analysis/skills 结果见 `tmp/wf-goal/worklog.md` 与 `tmp/wf-goal-round-new/`。

## 79. 撤回：`--to` 的 64-hex 形态校验（终审第五轮后的成本判定）

终审建议对 `writer-handover begin --to` 做 64 位十六进制形态校验（零成本拦截转抄错）。实现后
`cp1_tests`/`r71_tests` 的短占位 key 被新拒绝面挡住，必须改这两个脚本的字节；而它们属于
candidate audit 的登记面，改字节会把 T0 的 `test_source_coverage` 打红（`script_sha256` 与
`declared-candidate-unverified`），需要重跑候选审计才恢复。按"范围收敛/成本不扩大本轮"判定：
**撤回形态校验**，`cp1_tests`/`r71_tests` 恢复 HEAD 字节；`--to` 仍只做转抄核对，打错由 accept
按 key 拒绝并给 `wf repair` 出口（§71 的边界不变）。登记为下一轮与 candidate audit 同批处理。
