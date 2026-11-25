# wf 第四轮独立复审与机制收口

## Goal

以质疑视角独立复核两份 dogfood 分析输出（a/b）与 `dogfood-second-audit-dispositions.md` 的结论，核对
`docs/workflows/wf/` 当前源树是否真的收口，并把其中「机制本可算出、却未交付或交付错」的三处问题按
机制实现修正；同时回答设计稿 §1.1「核心原则」的 AI 指导要点是否准确。不新增 skill、不新增层级、
不做补丁式堆叠。

## 背景与已核实事实

### 对两份分析的独立核对（结论：大体成立，但有三处被漏掉的实现面缺陷）

已复核成立的部分（不重复修）：

- `task-rework` 真实现、三个临时入口（`review-restart`/`review-reauthorize`/`reopen-reviewed`）零命中。
- `scope-exceptions`/`material-gaps` 不再参与缺口判定；缺口只由 `axes: uncovered` 承载
  （`payload/lib/wflib/review.py:4332`）。
- 发行资产 74 项（`docs/workflows/wf/dev-manifest.json`），与两份分析一致。
- 当前源树自测健康：T0 单元面与全量 runner 均绿（本任务复跑：144 单元 = 59 套件 + 5 流程/extra +
  80 repro，fail=0，GATE-OK，run_id=1795590889329-1078517-ae7a5aa44ba6）。
- 两份分析共同的判断「§1.1 原则准确、失准在实现面」经本轮抽查**成立**：判据句两问、消费点定义、
  人签清单性质、正面授权、强度如实声明与 13 skill 的调用权登记一致；失准仍在实现面。

本轮**新发现**（两份分析未覆盖，均在本机复现，证据见各条）：

- **F1（人签面，P1）批准草稿不交复杂度/TDD 事实，且记录来源失真。**
  `task-approve --draft` 的 facts 只有 `pending_plan_questions`（`payload/lib/wflib/tasks.py:1775-1803`），
  不含机器算出的复杂度提议与四项条件理由，也不含生效 TDD；`wf-continue/SKILL.md:20` 却要求
  「呈现 PRD 机读块、复杂度与 TDD，请人批准」——指引承诺的输入机制不提供。决定文件未写 `plan` 时，
  正式批准把 `plan.confirmed_source` 记为 `inputs`、`human_inputs={}`（`tasks.py:1936-1939`），
  实际取值来自机器提议：记录宣称的确认来源不存在。
  复现：`task-approve --draft --json` 的 facts 无复杂度键；批准后 `task.json.plan.confirmed_source="inputs"`、
  `human_inputs={}`、`complexity="light"`。
- **F2（自我描述的机械事实，P2）终态对象与轻量任务的审查投影说错话。**
  `review-status` 在 `round < 1` 时无条件输出「复杂任务 Check pass 后先 review-launch」
  （`payload/lib/wflib/cli.py:3953`），既不核对象状态也不核复杂度：已归档任务与轻量任务都被劝去发起审查。
  对该已归档任务执行 `review-launch` 得到 `WF_APPROVAL_MISSING`「规划批准已失效」
  （真实原因是对象已归档、PRD 已移入归档目录），诊断与处置方向都错。
- **F3（结果协议，P2）通过结果的 `exit` 与自身 `next` 矛盾。**
  机制稿 §11.1 定义 `exit` 为「失败/待决时可走的出口」，实现却对每个 `WF_OK` 结果输出码表通用文案
  「继续当前绑定步骤；不推断其他对象已完成」（`payload/protocol/codes.json:99`、`wflib/codes.py:72`）；
  只读命令（`version`/`help`/`status`/`review-status`）的 `next` 与它直接冲突，文本渲染器又只在
  非 pass 时显示该字段（`cli.py:738`）。

### 不修但登记的观察

- **O1** `status.task.files.unexpected` 把人的决定文件（`approve.json`、`review-notes.json`）列为
  「非规范文件」（`wflib/taskfiles.py`），易被读成「该删掉」。只读投影、无门禁消费，本轮不改名。
- **O2** `task-start` 的工作区事实把未提交项目数据（`.wf/baseline.md`、`.wf/project-config.json`）
  归入 `other_tasks`（`tasks.py:2416`）。语义应为「未归属」，但改名牵动机制稿 §3.5 与 skill 引述，
  本轮只登记。
- **O3**「报告导入后不可覆盖」仍是人裁维持项（前台账 11-21 裁定），本轮不重开。
- **O4** 0.0.1 尚无完整复杂任务 dogfood；本轮只跑到轻量闭环 + 全量 runner，复杂链路仍由测试面覆盖。

## Requirements

- **R1** `task-approve --draft` 必须输出机器可算的批准事实：复杂度提议及四项条件理由、生效 TDD 与来源；
  approve 条目预填 `plan{complexity,tdd}`，人确认后写回决定即成为 `decision` 来源。
- **R2** 正式批准在决定与请求 inputs 都没有 complexity 时，`plan.confirmed_source` 记 `proposed`
  （不再记 `inputs`），并在结果里给出「分级未经人确认」的可见提示；复杂分级仍必须来自 `decision`。
- **R3** `review-status` 的轮级 `next` 必须按对象状态与复杂度给事实：已归档对象不再劝发起审查；
  轻量任务说明外部审查轮非必需；复杂未发起才给 `review-launch`。
- **R4** `review-launch` 在对象已归档时以终态事实阻断（先于规划批准核验），出口指向新对象/归档记录。
- **R5** pass 结果的 `exit` 为 null（与机制稿 §11.1 的定义一致）；blocked/needs_decision 的 `exit` 不变。
- **R6** 机制稿 §2.3、§11.1 与相关 skill 文案同批对齐；不新增 skill、不新增原因码、不改设计稿 §1.1 的原则文本。

## Acceptance Criteria

- [x] AC1 `task-approve --draft` 的 facts 含 `complexity_proposal{value,reasons}` 与
      `tdd{value,source}`；approve 条目的 `plan.complexity` 等于提议值（新增用例断言）。
- [x] AC2 复制草稿的 approve 条目正式批准后，`plan.confirmed_source == "decision"`、`human_inputs` 含该 plan 块。
- [x] AC3 决定与 inputs 都不含 complexity 时，`plan.confirmed_source == "proposed"` 且结果 warnings 明示；
      复杂分级仍需 `decision`（既有门禁不变，回归用例保留）。
- [x] AC4 对已归档任务与轻量任务跑 `review-status`，`next` 不含「先 review-launch」的劝告，且给出对应事实；
      复杂未发起任务仍给 `review-launch`（三条断言）。
- [x] AC5 对已归档任务跑 `review-launch`，返回终态事实（`status=archived`）与归档出口，不再报「规划批准已失效」。
- [x] AC6 pass 结果 `exit is None`；同一命令的 blocked 结果 `exit` 非空（改用例覆盖）。
- [x] AC7 机制稿 §2.3/§11.1 与 `wf-continue` 的对应句同批更新，定义只写一处、其余留判断句。
- [x] AC8 新增回归用例实跑通过；`python3 -m unittest discover -s scripts/tests -t .` 全绿。
- [x] AC9 `scripts/validate-wf-design.py`、`scripts/check-doc-refs.py`、`./scripts/validate-skills.sh`、
      `python3 scripts/build-wf-release.py --verify --verify-token-parity` 全绿。
- [x] AC10 变更后重跑全量 runner（144 单元）GATE-OK；无新增 skill/层级/原因码。

## Out of Scope

- 报告导入后覆盖、审查环境不可用的降级口径（人裁维持项）。
- `other_tasks`/`unexpected` 的事实改名与任务目录规范集调整（观察项，另立）。
- 版本号推进、tag 创建、0.1.0 → 0.0.1 升级通道（需人操作）。
- traffic_monitor 目标项目侧的收尾清理（运行态残留）。

## 验证记录（2026-11-25）

- T0：`python3 -m unittest discover -s scripts/tests -t .` —— **1949 用例全绿**（43 skipped）。
- 全量 runner：`run_all.sh --full --repro green` —— 144 单元（59 套件 + 5 流程/extra + 80 repro）
  **fail=0，GATE-OK**（run_id=1795591797507-1196011-27adeef88800）。
- 设计闸门：`validate-wf-design.py`（定义/消费 100%、二值 93/93、三档 14/14）、`check-doc-refs.py` 0 problems、
  `validate-skills.sh` 25 skills 全过；`build-wf-release.py --verify --verify-token-parity` 字节复现通过（74 assets）。
- 手工 dogfood（`/tmp/wf-audit-5`，dev 部署 86 文件）：草稿显示 `complexity_proposal{light}`/`tdd{false,project-default}`
  并预填 `plan`；复制草稿批准后记录 `confirmed_source=decision`、`human_inputs={complexity,tdd}`；
  轻量任务 plan→check→knowledge→archive 全通；归档后 `review-status` 报「审查轮次已关闭」，
  `review-launch` 报 `task is archived`（不再误报「规划批准已失效」）；`version --json` 的 `exit` 为 null。

## §1.1 结论（本轮）

设计稿 §1.1 的 AI 指导要点**准确**：判据句两问（资格 → 后置条件）、消费点定义「只被打印不算」、
人签清单性质（入口动作不进清单、可按人答复转录）、正面授权/负向禁令分工、「指引就地、不成层」
与 13 skill 调用权登记一致。三处缺陷都在**实现面**（事实未交付/来源失真/出口自相矛盾），
修的是实现与机制稿定义位，设计稿正文不改；本轮未新增 skill、层级与原因码。

## Notes

- 提交与收尾按用户要求：实现与验证完成后停在此处，等待人工同意再执行提交/归档。
- 所有发现均带 file:line 与实跑证据；不复用台账转述。
- 回归用例位置与 implement.md 的偏差：批准草稿用例落在 `scripts/tests/wf_runtime/test_approve_draft_facts.py`
  （与计划一致），审查入口用例落在 `scripts/tests/wf_review/test_review_entry_gate.py`（与既有 review 套件同层）。

## 第二轮：对"审查本轮改动"的两份分析的处理（2026-11-25）

### 采纳并修正

- **B-2 草稿硬失败（采纳）**：`--draft` 在 `tdd_default`/`inputs.tdd` 非法时会整体 raise，连骨架与
  复杂度提议都拿不到。改为：草稿把问题放进 `facts.tdd.problem`，不预填坏的 `plan.tdd`；正式批准
  仍严格拒（坏值就是拒绝理由）。用例 `test_draft_survives_broken_tdd_default`。
- **B-3 轻量审查口径分叉（采纳）**：`review-status` 曾写"确需外部审查再 review-launch"，与
  `wf-review`「轻量任务不发起审查」冲突。改为：轻量任务不设外部审查轮，实际需要异种审查说明
  分级不成立 → 回 Plan 由人提高复杂度。`review.round_entry_gate` docstring 同步。
- **A-1 复杂分级承载（部分采纳）**：请求 `inputs.complexity` 不是人的决定（机制稿 §2.3：inputs 只作
  提议），复杂分级最终由归档门禁拒。批准入口现在对「complex 且来源非 decision」给出**可执行警告**
  （明说归档会被拒、给出补 decision 的两条出口），不提前阻断——避免让集成夹具的既有 inputs 路径
  全部改形，也不把"分级值本身"替人决定。轻量提议在四项条件全 false 时机器可证，保留 `proposed`
  记录 + 提示；不改成硬门禁（否则每笔手写批准多一轮，且没有承诺被绕过）。
- **B-7 spec 结构文件与 schema（采纳）**：`all_specs` 曾把 `.wf/spec/` 顶层 `index.md` 与两份 checklist
  当规则加载，出厂模板因此自带 3 条「frontmatter missing」（dogfood 会话 1 收工前返工）。现在这三个
  框架定义的结构文件不进规则集、不参与元数据校验；子目录同名文件与缺 frontmatter 的真规则照常校验。
  用例 `test_spec_structure_files.py`（4 条）。

### 复核后不成立/不改

- **A-2 导入后修订报告**：属 11-21 人裁「维持」项。摘要是 reviewer 的证言边界：允许导入后改字节，
  等于让主会话改写 reviewer 的结论；成本是真实轮次，但替代方案的代价更大。不重开。
- **B-1「proposed 告警是死代码」**：不成立（部分）。规定路径复制草稿确实恒为 `decision`——那正是
  「人已看到并确认预填值」的转录；`proposed` 分支服务于手写决定且双缺的路径，并新增了
  「complex + inputs」的归档后果警告，二者都可达。删警告会让"机器提议"重新不可见。
- **B-9 单 reviewer 降级未实测**：测试面已有覆盖（`r71_tests` 走 `--single-reviewer-acceptance`
  并断言接受记录、`test_acceptance_sampling`/`test_dogfood_round3` 单测），缺的是人工环境实测；
  本轮不新增入口。
- **B-4 tag / B-5 dogfood / B-8 §1.1 搬迁 / B-10 目标项目偏离**：分别属人操作、证据面、文档整理
  候选与目标项目侧，均不在本轮代码范围；已在交付说明中如实登记。

## 第三轮：复杂链路实测与随之修正（2026-11-25）

- **复杂链路 dogfood（新增证据，关闭 A-3/B-5 的"无实测"）**：`/tmp/wf-audit-6` 从空项目走完
  `draft(complex, governance witnessed) → 人批准(decision) → start → 交付(pkg+tests+spec 规则) →
  Check → 授权外发 → review-launch → review-context×2 → lint×2 → import → main-review → decide pass →
  knowledge → archive`。审查链在 0.0.1 上可走通；两个 reviewer 为同机合成报告，非异种 CLI。
- **新发现并修正（两轮分析均未提）**：`review-context` 首次物化后回显 `materials_check.state=
  unmaterialized / fixed=false`（取的是写入**前**状态），reviewer 会读成"材料未物化"。改为发布后
  用同一 `materials_identity_state` 重算再回显；`review-identity-c6` 增首调用断言。
  交付纪律 spec 增第 7 条（回显快照时点）。既有两个用例原本断言"回显取进入时状态"
  （`test_materials_atomic` 的注释写着"记的是进入时状态"）——它们锁定的正是自相矛盾的一对
  事实（identity 取发布后 manifest、state 取发布前），已按新语义更新，不是放宽断言。
- **顺带验证**：`spec --file` 的 `exit` 为 null（F3）；新增规则在 Check 阶段要求 `task-curate` +
  `spec --file` 留痕（机制按事实报出，未额外加指引）。

## 第四轮：对"第二次审查本轮改动"的处理（2026-11-25）

### 采纳并修正

- **a-1 TDD 未由人确认（采纳，警告级）**：设计稿 §4.4 允许未设置时按项目默认/发行缺省，但批准记录要能看出
  "这个值不是人的选择"。`_approval_warnings` 增 TDD 分支（记录 `tdd_source` 已如实）；用例断言
  "缺 plan 时按缺省 + 有未确认提示"。
- **a-2 警告未接入开工路由（采纳，指引+next 级）**：批准结果在「complex 且来源非 decision」时不再只说
  "归档会被拒"，`next` 改为「先补 `plan.complexity` 的决定并重新批准，再 task-start」；`wf-continue`
  已批准行同步要求先看 warnings 再开工。**没有**改成批准时硬拒——见下方审计约束。

### 复核后不成立/不改

- **b-2 草稿预填洗白来源（再次不成立）**：设计稿 §1.2 明确"人答复后转录不降效力"，草稿展出的
  `complexity_proposal` 是人做决定的信息基础；把骨架改成 TODO 只会把"抄错值"的风险交给 AI。
  `proposed` 分支服务于手写决定路径，不是装饰；本轮又让它与 next/warning 连成一条收敛链。
- **b-3 存量兼容缺口**：核实 `wf-v0.1.7` 的 `gates.py:1109` 已有同一门禁、`tasks.py:1830` 已把缺省来源记
  `inputs`——不是 0.0.1 新增面。README 升级段补一条"存量分级载体"说明与两个出口，避免升级时才撞。
- **b-6 §1.1 第 46 段搬迁**：仍属文档整理候选（牵动唯一定义索引与修订闸门），本轮不动。

### 关键约束（本轮实测，给 b-1 定级）

改集成套件/repro 脚本字节会让 `full/candidate-audit.json` 的 `script_sha256` 失效，T0 直接红
（`units_candidate_verified` 64 → 58），而重生成审计需要"已提交候选 + tag"跑 candidate 模式——
`wf-v0.0.1` 未建时，任何"需要夹具跟改"的批准行为变更都被冻结。因此批准入口保持"可见警告 + 收敛 next"
而非硬拒；硬拒与夹具迁移应与 tag/候选审计同一批做。该结论已写进交付纪律 spec。

## 第五轮：0.0.2（人裁：把复杂分级人签改成硬门禁）

- **批准入口**：`complexity == "complex"` 且 `confirmed_source != decision` 时直接
  `WF_SEMANTIC_DECISION`（出口：`--draft` 骨架已预填 `plan.complexity`，或手写补该键）；
  请求 `inputs.complexity` 只作提议不再能承载人签。TDD 仍按设计稿 §4.4 允许缺省（保留"未由人确认"提示）。
- **夹具迁移**：r69/r75/r70/r68/r53/r51r52/r54/r71/p5_v2v3 与 `_review_launch` 的批准决定补
  `plan.complexity`；`test_approval_binding` 夹具补基线（使提议可判成 light）；`review-identity-c6`
  恢复"首物化后 state=fixed"断言。p5_v2v3 按任务分别声明（V2 轻量、V3 契约面 complex），不把 V2 连带判复杂。
- **发行**：README 目标版本 → 0.0.2，升级通道指向 `refs/tags/wf-v0.0.2`；发行树重建；
  `wf-v0.0.2` tag 已建，标签内容随夹具/审计同批前移到绿色提交（未推送，移动前仅有本机引用）。
- **候选审计**：按 0.0.2 tag 全量重跑（非手改），65/65 ok、bad=0、status=complete；
  首次审计暴露 p5_v2v3/r54_tests/r71_tests 三处夹具仍用 inputs 承载分级，已修后复跑至全绿。
- **复现用例**：首轮全量 runner 又暴露 3 个 repro（`baseline-apply-generated`、`complexity-bootstrap-exempt`、
  `complexity-human-carrier`）仍用 inputs 承载复杂分级；按"复杂提议 + 决定 plan"改写后，缺产物仍按
  `WF_TEMPLATE_INCOMPLETE` 被拒，用例意图不变。
- **验证**：T0 1956 绿；全量 runner 144 单元 fail=0 GATE-OK（run_id 1795599151571-2063390-48d6512e8ecd）；
  `verify-wf-release` 六项 OK；候选审计 65/65 ok。tag 在未推送前曾随夹具/复现修正前移，最终指向 f74ea6df。

## 第六轮：对"0.0.2 之后"的第三次审查处置（2026-11-25）

### 采纳并修正

- **a-1 AGENTS 版本漂移（采纳）**：`AGENTS.md` 不再复述版本号，改为"当前版本以 README 目标版本行为唯一事实"——
  消除"每次升版都要记得同批改 AGENTS"这一类漏项。
- **b-1 机制稿与实现相反（采纳）**：机制稿 §2.3 改为"复杂分级未写入决定时批准入口直接拒绝"，
  与 0.0.2 实现同向；此前文档仍写"警告不硬拒"。
- **b-2 inputs.tdd 绕过确认（采纳，提示级）**：`tdd_source=inputs` 现在也触发"TDD 未由人确认（请求 inputs 提议）"
  警告；取值仍保留（设计稿 §4.4 允许缺省/提议），不改夹具行为。
- **a-3 分级门禁两处实现（采纳，收敛实现）**：`tasks.complex_needs_human_decision()` + `COMPLEX_DECISION_REASON`
  成为批准入口与归档门禁的共同判据与文案；纵深防御保留，但不再各写一套措辞。
- **a-2 README 版本单元膨胀（采纳）**：历轮叙述迁出至 `analysis/round-history.md`，README 单元从 2288 字符
  收到 789 字符（当前版本 + 当前变化 + 升级口径 + 指针）。
- **a-4 升级链路可执行性（部分关闭，预览实测）**：0.0.1 候选安装 → 0.0.2 升级**预览**跑通
  （86 项路径、update/add/reinstall/register、0 偏离、预览指纹 `bbcc4802`）；`--apply` 需交互终端确认，
  按规则不由模型代跑。
- **发行收口**：因 payload 新增（TDD 提示、共享判据）先删本地 `wf-v0.0.2` 再重建（未推送，仅本机），
  候选审计按最终字节第三次重跑（65/65 ok），tag 六项核对仍全绿。

### 复核后不改

- **b-3 导入后改报告**：仍是 11-21 人裁维持项（摘要是 reviewer 证言边界）；不重开。
- **a-5 §1.1 第 46 段搬迁**：仍属修订闸门范围（牵动唯一定义索引与引用面），单开整理任务更合适。
- **a-6 目标项目偏离面**：traffic_monitor 侧收尾属目标项目操作，不在本仓库任务内。

## 第七轮：0.0.3（第四次审查处置）

### 采纳并修正

- **a-4 / 同型不对称（采纳）**：TDD 开关也只由人的决定承载——`inputs.tdd` 只作提议、**不生效**；
  缺省按项目配置/发行缺省并提示"未由人确认"。`r17r24_tests` 的 TDD 用例改为把 `tdd` 写进决定 `plan`。
  （设计稿 §4.3「模型不因任务类型自行开启」由此在机制上成立。）
- **b-1 轻量任务外部审查（采纳）**：设计稿只规定复杂任务**必需**外部审查、轻量用内部双轴审查，
  没有禁止轻量自愿额外审查。`wf-review`、`review-status`、`round_entry_gate` 三处同口径改为
  "轻量可选、不改变分级与完成条件"，不再把 AI 的判断写成分级错误。
- **b-2 TDD 警告与 next 冲突（采纳）**：`wf-continue` 改为"TDD 提示未确认时向人确认按缺省执行即可
  （要改值再重批）"，与批准结果的 `next=task-start` 一致；复杂分级缺决定已在批准时拒绝，不会出现在该步。
- **a-2 §1.1 超长段（采纳，拆分而非搬迁）**：该段现在 2793 字符（分析中的 6765 与当前文件不符），
  按主题拆成三段（指引就地 / 正面授权 / 人签清单），定义位与索引不变；机制稿登记的 design 输入摘要同批更新。
- **a-3 round-history 无护栏（采纳）**：新增 `test_readme_version_cell`——READM 目标版本单元 ≤1400 字符、
  必须链接 `analysis/round-history.md`、该文件保留迁出内容；下一轮再堆流水账会直接红。
- **a-1 升级证据（部分关闭）**：0.0.1→0.0.2、0.0.2→0.0.3 两次升级**预览**实测
  （86 项路径、0 偏离、指纹 `bbcc4802` / `5384dd6b`）；`--apply` 仍需人在 TTY 输入指纹，不由模型代跑。

### 复核后不改

- **b-3 导入后改报告**：11-21 人裁维持项，不重开。
- **a-5 traffic_monitor 偏离面**：目标项目侧操作，不在本仓库任务内。
- 设计稿整体搬迁（把清单移出 §1.1）仍属修订闸门范围；本轮只做同节拆分，未改定义位与索引。

## 第八轮：0.0.4（第五次审查处置）

### 采纳并修正

- **a-1 TDD 缺省无持久记录（采纳，口径级）**：设计稿 TDD 段明确"缺省值与来源写入任务记录（`tdd_source`），
  不要求额外人签；要记成人的选择就写批准决定的 `plan.tdd`"。`wf-continue` 同步：把缺省值告诉人即可，
  不制造"人已确认缺省"的假记录（这正是 0.0.2 修 `confirmed_source` 同类的"不要把没有的选择记成有"）。
- **b-1 轻量自愿审查的后果未写全（采纳）**：三处文案（`wf-review`、`review-status`、`round_entry_gate`）
  补上"发起后未关闭 blocking 进入归档门禁（与复杂任务同口径），fail 须逐条关闭/修复重查"。
  不加"轻量轮的 finding 不进归档门禁"的短路——已核实的缺陷不会因任务分级而消失。
- **b-3 help 示例预填 tdd（采纳）**：`task-approve` 帮助的 `plan` 说明改为"`tdd` 只在偏离缺省时写"，
  `example_file` 删除 `tdd` 键——照抄示例不再把项目缺省记成人的选择。

### 复核后不改

- **a-2 导入后改报告**：11-21 人裁维持项。
- **a-3 / b-2 新版使用证据**：真实新会话与 `--apply` 仍需人工环境；本轮只补了 0.0.3→0.0.4 升级预览
  （86 路径、0 偏离、指纹 `952d8407`）。
- **b-4 traffic_monitor 偏离面**：目标项目侧操作。
