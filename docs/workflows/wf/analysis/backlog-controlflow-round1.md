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

## 21. 待补断言（R11 发现 3）

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

## 23. 待补断言：startup check ⑩ 的收窄（R12 发现 3）

`tasks.startup_check` 的 WIP 项改按 `exclude_scope` 后，全仓无测试引用 `startup_check`。
放行风险低（bind/acquire 前端仍拦），但事实面会静默少报一条阻断；与 §21 同批补。

## 24. 已同步：设计稿的返工谱系例外（R12 发现 2）

设计稿 §4.2/§4.4/§5.4 已补"返工谱系例外见 §5.6"，§5.6 补承接方与核销点；机制稿 §0.1 的
design.md 输入摘要同批更新（validate-wf-design 输入摘要 4/4、覆盖率 100%/100%）。

## 25. 待补断言：keep 归属/startup ⑩/reassess 核销（R13 发现 6）

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

## 30. 待补断言：settled 的摘要失配分支（R14 发现 8）

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

## 37. 待补断言：挂起复评的接缝（R17 发现 3）

`test_reassess_trigger.py` 只测纯函数；全仓无测试引用 `startup_check`；唯一消费 startup facts 的
repro 夹具无挂起任务；没有"兄弟任务挂起时 archive"的用例。以下注入全绿：删 startup finding、
删 archive `reassessment`、让 archive 在 waiting 时 raise。与 §23 同族，下一批用 repro 补。

## 38. 待裁：文档要求"执行复评"，实现恒只报告（R17 发现 4）

设计稿 §5.4 与机制稿 §5.3 写"归档后/启动后**执行**复评，持写权且目标可写时执行"；实现（R16 修复）
两条路径都只报告事实（清挂起由持写权会话的 `task-reassess` 做）。同实例 R 归档时可满足文档前提，
故文档与实现方向相反。需人选边：改稿（触发面只给事实）或补实现（触发面在可写时自动清挂起）。
R17 亦确认：两分支的 `task-reassess` 入口都可达，无新死路。

## 39. 待裁：`stop` subject 的字面 vs 模式两套语义（R18 发现 2）

`stop --keep|--commit` 的归属门禁按**字面成员**比 e 桶，而同函数其余判据（`covered`/`unlisted`/
`out_of_scope`）把 subject 当**模式**（`pkg/**` 能过覆盖核却被判 foreign）。帮助只写"路径或承接对象"，
机制稿未声明必须字面。需人裁：统一到字面并写进帮助/§4.3，或先按 `covered` 归一后比较。
（旧形态本身不严谨：`pkg/**` 会被指纹记成 deleted；与 §29 同族。）

## 40. 已修：启动顺序与复评投影（R18 发现 1）

`STARTUP_STEPS` 恢复七步；复评事实改为**固定顺序之后**的第 8 项投影（`waiting|unknown`），不占序位、
不改首报项；实现稿的覆盖面声明与机制稿 §5.2/§5.3 同批登记；陈旧注释删除。

## 41. 待裁：启动项 ⑥ 的排除理由失效（R19 发现 4）

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

## 45. 待裁：返工谱系豁免只有一层（R21 发现 4）

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

## 48. 待裁：在途实例的受控返工 R 能否被"任务绑定"独立接续（R23 发现 6）

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
§47：**未实施**（见 §57）。
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
