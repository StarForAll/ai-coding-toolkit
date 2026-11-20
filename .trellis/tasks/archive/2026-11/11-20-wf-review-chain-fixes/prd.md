# wf 审查链路与发行身份修正

## Goal

以两份 dogfood 分析报告为输入，按当前 HEAD 的源码事实重新核实，修正 wf 审查闭环中会让判定失真的机制缺陷、版本身份漂移与文档口径冲突；保持「机制算可稳定计算的事实、AI 判断授权内事项、人承担承诺与风险」的边界，不新增 skill 或层级。

## Background

- 输入 A：`/home/xzc/.codex/sessions/2026/11/08/rollout-2026-11-08T16-12-24-01a1ba37-3e19-7141-bcbf-a51e3001ceb2.jsonl` 等四份会话，导出为 `/tmp/traffic_monitor_1.md` 至 `/tmp/traffic_monitor_4.md`（存在，已抽查第 4 份）。
- 输入 B：`/tmp/wf-find-a.md`、`/tmp/wf-find-b.md` 当前不存在；两份新的首轮分析报告（本任务输入）已逐条对照当前源码复核。历史 wf-find 结论经归档任务 `11-12-wf-dogfood-round3` 消费，不作为本任务的直接事实源。
- 输入 C：`/home/xzc/.zcode/cli/log/zcode-2026-11-08.jsonl` 当前不存在；不依赖该日志，证据缺口已在任务记录声明。
- 当前基线：`HEAD=f7370d8a`，工作区干净；`docs/workflows/wf-release/wf-release.json` 版本 `0.1.0`、74 个资产；tag `wf-v0.1.0` 指向 `20e3ae88`（55 个资产）；`traffic_monitor/.wf/install/release-manifest.json` 版本 `0.1.0`、57 个资产；`docs/workflows/wf/README.md:18` 写目标版本 `0.1.2`。
- 基线验证：`python3 -m unittest discover -s scripts/tests -t .` 1323 项通过（42 skip）；`python3 scripts/validate-wf-design.py` 七项检查与覆盖率通过；`python3 scripts/build-wf-release.py --verify` 字节复现通过（0.1.0，74 assets）。

## Verified Findings

| ID | 事实（代码/数据证据） | 严重度 | 判定 |
|---|---|---|---|
| F1 | `review.launch` 在锁内只核 `check.result == "pass"`（`review.py:1521`），未调用已有的 `gates.check_validity`（`gates.py:584`）；`review-context` 在 `review.py:1767` 重新计算当前锚点并物化材料。内容在 Check 后变化时，旧 Check 可发起新轮，请求写旧 `check_id` + 新 `check_anchor`。 | 高 | 成立。设计稿 §6.5 要求 Check pass 后发起；§3.5 的有效性判据已存在，属实现未复用。 |
| F2 | `review.merged_coverage(main_axes, axis_reports)` 只合并两源 `pass/fail`（`review.py:702`）；`report_review[].reliance` 只校验取值（`review.py:864`），不参与覆盖。主会话五轴全 `uncovered`、两份报告 `reliance=none` 时，报告自身 `pass` 仍可贡献覆盖并产出 `pass`。 | 高 | 成立。`reliance` 成为只登记不消费的字段；与「报告是辅助证据、主会话复核」的契约冲突。 |
| F3 | `review.decide` 的 `failures` 来自报告原始 blocking findings，不看当前轮 dispositions（`review.py:2754` 起，失败在报告问题阶段累计）；隔离探针中主会话把 finding 判 `disputed`、处置写 `accepted`（误报）后仍返回 `fail`。而 `wf-review-action:32` 写「同一轮重判可在 finding 关闭后通过」，`wf-repair-loop:82` 写「fail 轮重判仍是 fail」。 | 高 | 成立，且是两份报告未点出的实现缺陷。设计稿说主会话 `pass` 不能覆盖**未关闭** blocking；已关闭的误报不应继续阻断本轮。 |
| F4 | `review-decide` 缺少 `--main-review` 时抛 `WF_SEMANTIC_DECISION`（`review.py:2970`）；主会话 `fail` 无 finding 时也抛 `WF_SEMANTIC_DECISION`。两者都可由 AI 生成骨架/修复/登记判断解决，不是人必须承担的决定。 | 中 | 成立。错误码把 AI 可补齐的输入误标成需人裁决，dogfood P12 的「停等」风险会复现。 |
| F5 | `review-decide` 的 `next` 对 `fail` 统一写「补真实审查或按异常退出处置」（`review.py:3160`），未指向范围内修复、重跑 Check、重新发起或关闭误报后重判。 | 中 | 成立。判定已经知道 verdict，回显应路由到可执行出口。 |
| F6 | `default_launch_request` 把 `submitted_scope.diff.paths` 声明为交付集合（`review.py:1401`），但 `write_materials` 固定重新取 `scope.delivery_set`（`review.py:1728`）；`context` 不回读 launch 的 `submitted_scope`（`review.py:1767`）。报告 `read-scope` 只与报告自己的 `excluded-scope` 比对，未与 launch 的 `exclusions` 比对。 | 中 | 部分成立。声明的缩小不生效、外发面与声明面可脱节；修复应把声明变成物化输入，并对越界读取声明做机械矛盾检查。 |
| F7 | 同一 `0.1.0` 对应三份不同内容：本地发行树 74 资产、tag 55 资产、traffic_monitor 安装 57 资产；README 却称目标 `0.1.2` 且「0.1.0/0.1.1 已由 tag 固定」（`README.md:18`）。`--verify` 只用现有清单版本重建，复现通过掩盖了版本复用。 | 高 | 成立。版本号不再是内容身份，违反 README §3 的版本同步义务与 §7.2 的三方升级匹配前提。 |
| F8 | `wf-review-action:32` 与 `wf-repair-loop:82` 对同一轮重判的结论相反。 | 中 | 成立，但根因是 F3 的代码缺陷；修 F3 后需同步修正 `wf-repair-loop` 的表述，保留 `wf-review-action` 的「误报关闭后可重判」。 |
| F9 | 设计稿 §1.1「判据句」把「可由明确输入稳定计算」直接连到「机制且进代码」，未区分「机制计算事实」与「是否设成硬门禁」；「交人」条件只列目标/承诺/授权边界，未列承担明确残余风险（覆盖缺口、不可用、降级）。 | 中 | 部分成立。核心判据准确，但两处表述不完整；修正应只补判据，不新增层级/skill。 |
| F10 | `upgrade --apply` 仍为 `WF_CAPABILITY_UNAVAILABLE`（`cli.py:2913`），traffic_monitor 无法机械升级到当前版。 | 已知 | 成立但属第三轮已声明未交付能力，不在本任务伪装为缺陷修复。 |
| F11 | `task-attribute` 只收 `--commit`（`tasks.py:2821`）。 | 低 | 不成立。批准触碰面内的未提交路径由 `touch_paths` 归入 e 桶；面外路径应回 Plan 扩范围，不应由归属命令收编。 |
| F12 | PRD 机读块缺审批前只读预检。 | 低 | 不构成正确性缺陷。`task-approve` 在写前完成同源校验，失败零写入；dry-run 属体验优化。 |
| F13 | 报告状态头只在首 400 字符内识别。 | 低 | 属既定协议；`lint report` 已给可执行提示。可在错误文案上改善，但不改变判定。 |
| F14 | 当前 0.1.x 修复没有一次新版真实 dogfood。 | 验证义务 | 成立但不在作者仓库内完成；本任务只交付可验证的机制修正，并在收尾声明未做新版 dogfood。 |

## Second-round Audit (2026-11-20)

| ID | 新审查意见 | 复核判定 | 处置 |
|---|---|---|---|
| S1 | 旧报告可绑定到新 Check（同 `check_anchor`、不同 `check_id`） | 成立 | 发起/取材料/导入/判定统一核 `check_id`；旧报告失效 |
| S2 | 发起阶段不核范围；缺 `diff.paths` 回退全量；读取声明超出 readable_scope/包含排除子目录 | 成立 | launch 同源校验；缺 paths 拒绝；导入/判定核 read-scope 与 exclusions/readable_scope |
| S3 | 主会话把 `reliance=none` 的报告当来源，仍记成 main 独立覆盖 | 成立 | `sources` 归属；引用槽位必须被采信且报告确实覆盖该轴 |
| S4 | fail 后同轮修正复核被摘要拒绝；保留旧 fail 复核却可 pass | 成立 | fail/未判定允许追加修正复核（旧记录标 `supersedes`）；仍有 fail 轴不得产 pass |
| S5 | 主会话独立发现 blocking 时无正式表达出口，`judgments add` 不在 finding 引用集合 | 部分成立 | 修正出口文案：修复重查，或登记 judgment 交人；不伪造 reviewer finding；不新增主会话 finding 模型 |
| S6 | `submitted_scope` 收窄无留痕、reviewer 与收工预览不可见 | 成立 | launch `scope.selected/total/narrowed`；context facts；`review-status` 与 `status --short` 的 launch_scope；skill 指引 |
| S7 | pass 的 `next_` 直接让人 finish，他轮 blocking 会撞 C2 | 成立 | pass next 补 `status --short` 提示 |
| S8 | `paths.match_path` docstring 与返回值不符 | 成立 | 修正 docstring |
| S9 | 全量单测偶发共享夹具租约争用/模板缓存失败 | 环境/运行器瞬态，未归因到本轮审查代码 | 干净重跑 T0 全绿；作为测试基础设施边界记录，不在本任务扩围 |
| S10 | `upgrade` 未交付、tag 未创建、traffic_monitor 仍 0.1.0、无新版真实 dogfood | 已声明能力/验证义务 | 不在本轮伪装为已修；收尾如实声明 |

## Third-round Audit (2026-11-20)

| ID | 新审查意见 | 复核判定 | 处置 |
|---|---|---|---|
| T1 | 收窄留痕指引指向 `judgments` 无法引用的 scoped 事实 | **不成立**：`judgments.validate` 不要求 `evidence_refs`；空引用合法 | 澄清 skill 最小形状（kind/outcome/basis），说明 `evidence_refs` 可省；未改机制 |
| T2 | 新 launch 强制 `diff.paths` 让旧请求无升级通道 | 部分成立（旧布尔形状已兼容；dict 缺 paths 会被拒） | 拒绝文案补「去掉 --launch-request 让入口重建」；upgrade 仍属第三轮边界 |
| T3 | 三类材料按字段存在而非形状判，错误分两跳 | 成立（体验） | 发起阶段 scope 校验已把形状/越界/排除面放在同一入口；不再留到 context |
| T4 | 同一路径同时在 diff.paths 与 exclusions 仍进入材料 | **成立（严重）** | `scope_binding_problems` 核 diff.paths 与 exclusions 交叠；`null`/非数组直接拒绝；重复路径去重后计 selected |
| T5 | 已确认 blocking 被无关覆盖缺口拦在正式 fail 前 | 成立 | dispositions/未关闭 blocking 前置；有 blocking 直接 fail，缺口接受只在可能 pass 时要求 |
| T6 | 主会话独立 blocking 无正式判否入口 | 边界（设计取舍） | 保留「修复重查或登记 judgment 交人」；不新增主会话 finding 模型，避免以补丁扩大机制 |
| T7 | 同轮关闭可产出证据自相矛盾 pass | 成立 | `pass` 不得引用该轴判 `fail` 的报告；`verified` finding 的 `accepted` 关闭须带 `evidence_refs` |
| T8 | 材料包含实施侧 `internal_review` 自评 | **成立（信息边界）** | `check.json` 只写 `id/result/anchor`；新增测试 |
| T9 | 会话身份/upgrade/tag/真实 dogfood 未验收 | 已声明能力/验证义务 | 不在本轮伪装为已修；收尾如实声明 |

## Fourth-round Audit (2026-11-20)

| ID | 新审查意见 | 复核判定 | 处置 |
|---|---|---|---|
| D1 | 旧布尔 `diff` 形状 + exclusions 仍把排除目录写入材料；`status.json` buckets 列全量；glob 读声明用字面匹配放宽 | **成立（高）** | 旧形状回退先扣 `exclusions`；buckets 只列本轮物化路径；`read-scope-readable` 改用 `subsumes` 可证包含 |
| D2 | 收窄事实未进入判定，只看 verdict 的调用方不知道证据面 | **成立（高）** | `review-decide` 的 `result.scope` 记录 selected/unselected/total/narrowed；skill 要求主会话在受影响轴 `basis` 说明未选路径处理；判断仍归 AI |
| D3 | 主会话独立 blocking 无正式表达；五轴全 uncovered + 已知 blocking 仍先拒绝 | **部分成立** | 全 uncovered + 已知 blocking 允许记录 fail；主会话独立 finding 仍保留「修复重查或 judgment 交人」边界，不新增自证 finding 模型 |
| D4 | `pass` 引用失败报告的出口写 `report_review.disputed`（非法值）；§8.2 把补覆盖写成必须重发一轮 | **成立** | 出口改为 `reliance=partial/none` + 具体 finding 的 `finding_review.check=disputed`；§8.2 改为“能同轮补证就同轮重判” |
| D5 | dogfood 历史项的会话身份/审批前置/报告 400 字符头/任务记录 | 多数已修；剩余为协议/能力边界 | 不在本轮扩围；会话身份、upgrade、真实 dogfood 仍如实声明 |

## Fifth-round Audit (2026-11-20)

| ID | 新审查意见 | 复核判定 | 处置 |
|---|---|---|---|
| E1 | 请求 `exclusions` 可整体替换必排面；显式空 `readable_scope` 跳过读取核对 | **成立（高）** | `mandatory_exclusions` 把必排面与请求追加项合并；请求只能加不能减；未声明 `readable_scope` 用入口默认，显式空表示不授权额外读取 |
| E2 | 收窄材料后 `reliance=primary` 仍整体消掉缺口 | **成立（高）** | 收窄时 primary 也只在该轴 `sources` 明确列出槽位时贡献覆盖；未列出的轴保持 `uncovered`，由主会话判断补读/证据 |
| E3 | 主会话独立 blocking 无正式判否入口 | 边界（设计取舍） | 保留「修复重查或 judgment 交人」；不新增主会话自证 finding 模型。D3 的“全 uncovered + 已复核 blocking 可 fail”已修 |
| E4 | §1.1 仍把“可稳定计算”写成充分条件；收窄要求额外规模判断 | 部分成立（指引密度） | §1.1 已写“可计算≠硬门禁”；收窄 judgment 仍是建议，不做强制；真实 dogfood 统计重试次数再决定是否降档 |
| E5 | 同进程新聊天仍沿用旧绑定；0.1.3 无真实 dogfood | 已声明能力/验证义务 | 不在本轮改身份机制；如实保留 |
| E6 | `read-scope-readable` 惩罚诚实申报 | **不采纳（安全边界）** | `readable_scope` 是 launch 声明的授权读取面；读过范围外应停止回报，不把读取声明删掉。保留硬拒绝，出口已写明“停止并回报” |
| E7 | `gap_decision` 在有 blocking 时被静默忽略 | 成立（小） | 增加 `gap_acceptance_ignored` 事实，明确该文件本轮不影响 fail |
| E8 | 设计稿 writer.json “整体提交”与 gitignore 矛盾 | 成立（文档） | 改为“运行态不整体提交；维护回执随维护组路径按 §5.3 处理” |

## Sixth-round Audit (2026-11-20)

| ID | 新审查意见 | 复核判定 | 处置 |
|---|---|---|---|
| F1 | `--main-review-draft` 预填 sources，主会话填 uncovered 仍被 primary 报告覆盖；旧 launch 判定端 narrowed=None | **成立（高）** | 骨架不再预填 sources；旧布尔/缺省 launch 在 `review_scope_facts` 按交付集合减排除面重算 selected/narrowed；收窄时 `uncovered` + 报告 `primary` 作为矛盾拒绝 |
| F2 | 默认 `business_code:["**"]` 接受 `.wf` 运行态与 `.git` 私有配置读取 | **成立（高）** | `read-scope-readable` 把 `.wf/`、`.git/` 作为控制面拒绝，spec/PRD 显式放行除外 |
| F3 | 只读材料包的合法审查无法提交报告 | **成立** | `read-scope` 可写 `materials`；显式空 `readable_scope` 下空数组表示未补读，不再强制非空 |
| F4 | 主会话独立阻塞仍难正式判否 | 边界（设计取舍） | 保留「修复重查或 judgment 交人」；不新增自证 finding 模型 |
| F5 | 收窄指引要求重复登记规模判断 | 成立（负担） | 改为在受影响轴 `basis` 说明未选路径处理；只有确有残余风险才登记 judgment |
| F6 | `merged_coverage` 收窄时要求 primary 逐轴 sources（N1） | **不采纳原修法** | 撤销该机械枚举；改为拒绝 `uncovered`+`primary` 的矛盾组合，保留 `reliance` 的 AI 判断语义 |
| F7 | 主会话复核表单继续增密（N2） | 部分成立 | 骨架减少预填、收窄指引减法；不降级现有语义校验，留真实 dogfood 统计重试次数 |
| F8 | 同进程身份/框架 vendor 锚点/报告同轮修订/archive preview | 已声明能力/产品边界 | 不在本轮扩围；`wf-finish` 增 vendor 单列指引 |

## Seventh-round Audit (2026-11-20)

| ID | 新审查意见 | 复核判定 | 处置 |
|---|---|---|---|
| G1 | 无关覆盖缺口挡住已核实缺陷的正式 fail | **成立（高）** | 收窄时 `uncovered`+`primary` 矛盾检查移到判定后：本来要产 pass 才拒绝；已有 blocking 先记录 fail，冲突写 `coverage_conflicts` |
| G2 | 本任务 PRD 虽在 readable_scope 放行，仍先被 `.wf/tasks/**` 判为越界 | **成立** | `read-scope-launch`/`read-scope-excluded` 对 `readable_scope.prd` 精确路径跳过排除冲突 |
| G3 | 默认 launch 丢失实际核验的外发授权引用 | **成立** | 轮次 `decision`/`export_decision` 写入口实际核验的确认摘要，不再读请求原字段 |
| G4 | 主会话独立核实的阻塞仍被迫走未核实 | **成立** | 新增 `main_findings[]`：可正式 fail、走 `slot:"main"` 关闭、参与 open_blocking/C2；修正复核不得静默丢弃 |
| G5 | 主会话复核表单持续增密 | 部分成立 | 本轮做骨架减法、收窄指引减法、main finding 提供正式出口；不降级现有语义校验，留 dogfood 统计 |
| G6 | 旧 launch 范围重算失败静默回落 | 成立（小） | `review_scope_facts` 返回 `scope_recompute_failed`，判定事实可见 |
| G7 | 框架 vendor 锚点/未启用绕过/reviewer 同轮修订/archive preview | 已声明产品边界 | 不在本轮扩围；保持如实声明 |

## Eighth-round Audit (2026-11-20)

| ID | 新审查意见 | 复核判定 | 处置 |
|---|---|---|---|
| H1 | 主会话 blocking 可通过把 severity 改成 suggestion 静默消失 | **成立（高）** | 修正复核对上一份 blocking main finding 的 severity 降级要求 accepted disposition；只改 severity 即拒绝 |
| H2 | 自定义 `readable_scope.prd` 可放行其他任务 PRD | **成立（高）** | launch 强制 `readable_scope.prd == task_prd_path(ctx, task)`；其他任务 PRD 拒绝 |
| H3 | 自定义请求 `export_decision` 可覆盖实际核验的授权摘要 | **成立** | 轮次记录优先写 `authorize.require` 的 `original_digest`；请求字段只作旧标签 |
| H4 | `main_findings` 还要重复填 `finding_review` | **成立（负担）** | `main_findings` 的 `finding_review` 可省，入口按 `verified` 记；要 `disputed/unable` 才写 |
| H5/b.N1 | main_findings 逃离 reviewer finding 的 K4c 校验 | **成立** | main blocking 与 reviewer finding 同核 `assertion_ref` 批准集合与规则不得自证 |
| H6/b.N2 | `recheck_by=human:` 无凭据载体，main finding 可被 AI 自产自销关闭 | 边界（§1.5 不防伪） | 保持现有 `recheck_by` 标签语义；不把它升级为 attestation，避免新增一层人工凭据机制；如需同级凭据应单独设计 |
| H7 | 主会话复核表单继续增厚 | 观察 | 本轮 main finding 自动补 finding_review、减少重复；不降级语义校验，留 dogfood 统计 |
| H8/b.P1-P3 | 框架 vendor 锚点/未启用绕过/reviewer 同轮修订 | 已声明产品边界 | 不在本轮扩围 |

## Ninth-round Audit (2026-11-20)

| ID | 新审查意见 | 复核判定 | 处置 |
|---|---|---|---|
| I1 | 跨轮关闭 verified main finding 只读当前轮复核，缺 evidence_refs 仍 pass | **成立（高）** | `verified_closure_problems` 接受全部 `main_reviews` 的 finding_review check；跨轮关闭按提出轮 check 核证据 |
| I2 | main finding 的 broken-reference 豁免未进人复核清单 | **成立（高）** | `main_findings` 中 `check_fix_kind=broken-reference` 加入 `lifted`，与 reviewer finding 同要求 `recheck_by=human:` |
| I3 | main finding 不在 `all_findings`/复核草稿/`f:` 判断引用 | **成立** | `all_findings` 纳入每轮最新 main_findings；草稿与 judgments 引用可见 |
| I4 | 单 reviewer 人数检查先于 main_findings 读取，已核实缺陷无法登记 | 边界（复杂审查输入） | 正式 verdict 仍需两份独立报告；单报告时按 `--unavailable`/修复重查/暂停处置，不在无效轮里写正式 fail |
| I5 | `recheck_by=human:` 无 attestation 载体 | 边界（§1.5 不防伪） | 保持标签语义；不新增人工凭据层，main finding 关闭仍要求 evidence_refs |
| I6/P1-P3 | 框架 vendor 锚点/未启用绕过/reviewer 同轮修订 | 已声明产品边界 | 不在本轮扩围 |

## Internal Audit (2026-11-20)

> 外部审查已到第九轮；按用户要求先做一次内部对照审查，重点判断实现是否偏离设计/PRD，而不是继续等外部指出。

| 项 | 复核结论 | 处置 |
|---|---|---|
| 实现与文档一致 | `all_uncovered` + 已复核 blocking 允许 fail，但设计/机制/实现稿仍写“输入不成立” | 三处文档同步为“无 blocking 才输入不成立，有 blocking 可 fail” |
| 旧 launch 兼容边界 | `scope_binding_problems` 只在 launch 调用时用合并排除面；旧 dict launch 仍可能绕过必排面 | 统一改为 `mandatory_exclusions`；旧布尔/缺省回退也扣面 |
| 主会话 finding 同批关闭 | `proposers` 在本轮 main review 读入前计算，同批 plan 关闭会误报 unknown | 当前 main findings 补入 `proposers`；新增同批关闭回归 |
| 复核草稿 | `all_findings` 已含 main finding，但草稿 `main_findings` 仍为空 | 草稿从本轮最新 main review 预填 `main_findings` |
| 请求形状 | 自定义请求可把 `diff` 写成字符串、`exclusions` 写成字符串、`readable_scope` 字段写成非数组 | launch 统一形状校验；仅旧布尔形状兼容 |
| 材料目录干净 | context 先建 materials 目录再核 PRD/范围，失败会留空目录 | PRD/范围校验先于目录创建 |
| 控制面读取 | `.wf`/`.git` 目录本身（不带斜杠）未被控制面分支拒绝 | 控制面精确目录也拒绝 |
| 跨轮关证据 | 已修；内部补 helper 测试 | 保留 |
| 文档/实现 | 实现稿 §2.3.10 未同步 main_findings/范围/授权摘要 | 已补 |

## Tenth-round Audit (2026-11-20)

| ID | 新审查意见 | 复核判定 | 处置 |
|---|---|---|---|
| J1 | 不存在/未通过的 evidence_refs 仍能关闭 verified finding | **成立（高）** | `evidence_ref_problems` 核 `v/a/f/p/j` 是否存在、`v:` 是否 passed；证据是否足够仍归 AI |
| J2 | 已登记的人复核在同轮重判失效；broken-reference 标记未改规则也触发 | **成立** | `broken_reference_problems` 消费现有+本次 dispositions；main broken-reference 仅对所引规则确实改过才要求人复核 |
| J3 | 草稿仍给 main finding 插入空 check/basis 记录 | **成立** | 草稿不再把 main finding 放进 `finding_review`，由入口按 verified 自动补 |
| J4 | 报告未到齐时已核实 main finding 无法登记 | **成立** | 新增 `--register-only --main-review`：只登记主会话 finding，不产生 verdict；正式判否仍要完整审查 |
| J5/a.1 | 降级与 broken-reference 规则只在代码/退出口，机制稿/skill 未登记 | 成立（文档） | 机制稿、action skill、实现稿、交付纪律同步 |
| J6/N2 | `recheck_by=human:` 无 attestation | 边界（§1.5 不防伪） | 保持标签语义；本轮已把 evidence_refs 可解析性收紧，但不新增人工凭据层 |
| J7/P1-P3 | vendor 锚点、未启用绕过、reviewer 同轮修订 | 已声明产品边界 | 不在本轮扩围 |

## Eleventh-round Audit (2026-11-20)

| ID | 新审查意见 | 复核判定 | 处置 |
|---|---|---|---|
| K1 | 计划 passed 盖过 Check 实际 failed/缺失；计划只声明、Check 通过却被拒 | **成立（高）** | 验证项定义取计划，通过状态只取 Check 记录；计划状态不再作为证据 |
| K2 | 不存在 `d:` 等证据仍能关闭 verified finding | **成立（高）** | `evidence_refs` 只接受可解析的 `v/a/f/p/j` 或当前锚点差异中的 `d:`；`s/g/h` 不作关闭证据 |
| K3 | 新一轮用当前 Check 重验历史已结案证据 | **成立** | `verified_closure_problems` 只核本次提交的 dispositions；历史关闭不被新计划重验 |
| K4 | `register-only` 不能保留原 finding 追加第二条 | **成立** | 允许 superset 追加（保留原 id、不降 severity），旧记录标 `supersedes`；丢 finding/降级拒绝 |
| K5 | evidence/register 规则只在代码与出口 | 成立（文档） | 机制稿、实现稿、交付纪律、repair/action skill 同步 |
| K6/N2 | `recheck_by=human:` 无 attestation | 边界（§1.5 不防伪） | 保持标签语义；本轮已收紧证据可解析性，不新增人工凭据层 |
| K7/P1-P3 | vendor 锚点、未启用绕过、reviewer 同轮修订 | 已声明产品边界 | 不在本轮扩围 |

## Twelfth-round Audit (2026-11-20)

| ID | 新审查意见 | 复核判定 | 处置 |
|---|---|---|---|
| L1 | `--register-only` 可改写已判 pass/unavailable 轮次的主会话复核 | **成立（高）** | 登记入口检查 `latest_decision`；已判 pass/unavailable 时拒绝改写，只允许开新一轮 |
| L2 | 先登记关闭、后核实为 verified，仍可无证据 pass | **成立（高）** | 全量判定对**已落盘**关闭只核非空证据、不按新 Check 重解；当前复核把该 finding 标 verified 时，缺证据即拒绝 |
| L3 | 只登记一条 main finding 仍要填正式审查整份表单 | **成立** | `--register-only --main-review` 支持最小 `task/round/main_findings`，入口补 discovery 复核（axes 全 uncovered，status 标未就绪） |
| L4/N2 | `recheck_by=human:` 无 attestation | 边界（§1.5 不防伪） | 保持标签语义；不新增人工凭据层 |
| L5/P1-P3 | vendor 锚点、未启用绕过、reviewer 同轮修订 | 已声明产品边界 | 不在本轮扩围 |

## Thirteenth-round Audit (2026-11-20)

| ID | 新审查意见 | 复核判定 | 处置 |
|---|---|---|---|
| M1 | 先登记关闭、后核实，不存在的证据仍能通过 | **成立（高）** | 已落盘关闭在本次复核标 verified 时也走证据解析；历史证据回退 `check_history`，不存在的 `v:` 仍拒绝 |
| M2 | 补齐证据后，旧空证据记录仍阻断判定 | **成立（高）** | 同一 finding 按**最新处置**计算；旧空记录被后续有效处置覆盖后不再阻断 |
| M3 | 省略可唯一推断的 slot，漏掉关闭证据校验 | **成立（高）** | `finding_review` 唯一推断出的 slot 写回记录；证据索引按 slot 精确核 |
| M4/N2 | `recheck_by=human:` 无 attestation | 边界（§1.5 不防伪） | 保持标签语义 |
| M5/P1-P3 | vendor 锚点、未启用绕过、reviewer 同轮修订 | 已声明产品边界 | 不在本轮扩围 |

## Fourteenth-round Audit (2026-11-20)

| ID | 新审查意见 | 复核判定 | 处置 |
|---|---|---|---|
| N1 | 关闭证据未绑定实际结案 Check：本次失败可借旧 passed，或旧关闭被后来同名失败卡住 | **成立（高）** | 关闭处置记 `check_id`；本次关闭只认本次 Check；历史关闭只认绑定那次，旧记录无绑定才回退历史 |
| N2 | 撤回无效关闭（amended）后旧 accepted 仍要求补证 | **成立（中）** | 同一 finding 取最新处置**含 amended**；最新不是 accepted 就不做关闭证据校验 |
| N3 | `vendor_dirty` 无路由指引 | 成立（指引） | `wf-continue` 明写：框架自有改动不当业务交付/审查，回源仓库维护任务处理 |
| N4 | main_finding 判据外缺陷无出口 | 成立（指引） | `wf-review-action` 明写：不要降成 suggestion，登记 judgment 请人扩判据 |
| N5 | 复核面复杂度累积 | 成立（认知负担） | 不靠再加机制解决；留真实 dogfood 重试率裁决，已做骨架/最小登记减负 |
| N6/P1-P3 | vendor 锚点、未启用绕过、reviewer 同轮修订 | 已声明产品边界 | 不在本轮扩围 |

## Fifteenth-round Audit (2026-11-20)

| ID | 新审查意见 | 复核判定 | 处置 |
|---|---|---|---|
| O1 | `finding_review.check=unable` + accepted 可关闭 blocking 并 pass | **成立（高）** | `open_findings` 只把 verified/disputed 的 accepted 算关闭；unable/未复核标 unverified，blocking 保留，判定 fail |
| O2 | Check 已 invalidated，review-decide 仍 pass | **成立（高）** | 正式判定与发起共用 `gates.check_validity`；失效即 `WF_CHECK_STALE`，register-only/unavailable 仍按各自职责 |
| O3 | 机械修订接纳验证项命令/cwd/required/consume_at 变化 | **成立（高）** | `_mechanical_revision` 对验证项定义做摘要比对；变化即 `WF_SEMANTIC_DECISION` 回 Plan |
| O4 | in-progress 占位被算 arrived/material_ready；格式错误抛 TypeError；lint 要求先 done | **成立（中）** | status 单列 writing，arrived/material_ready 只认 imported/done；非数组/非对象形状逐项报错且不产 verdict；skill 改为先 lint 后 done |
| O5 | `task-attribute` 路由与审查身份两处口径 | **成立（中）** | wf-continue 明确 `--commit` 只处理已提交历史；设计稿表改为发起声明实施 CLI、审查身份判定时事后核验 |
| O6 | `readable_scope.spec` 默认过窄 | **成立** | 默认 spec 覆盖 `.wf/spec/**` 与策展条目 |
| O7 | read-scope 诚实申报无出口 | 设计矛盾（§1.5） | 设计稿改为“不拦截读取、声明矛盾按输入不成立；诚实越界停止回报/修正/换轮”，不新增放行层 |
| O8/P1-P3 | 同进程身份轮换、reviewer 同轮修订、文档重复/复杂度 | 已声明边界 | 不在本轮扩围；复杂度留真实 dogfood |

## Sixteenth-round Audit (2026-11-20)

| ID | 新审查意见 | 复核判定 | 处置 |
|---|---|---|---|
| P1 | 规划批准失效，旧 Check 仍可发起/判定 | **成立（高）** | 审查入口先核 `_is_approved_plan`；失效 `WF_APPROVAL_MISSING` |
| P2 | blocking finding 缺 id 被跳过并 pass | **成立（高）** | 报告输入逐条要求 finding id/对象；缺 id 输入不成立 |
| P3 | 新处置显式历史 `check_id` 可借历史 passed | **成立（高）** | 新 dispositions 强制覆盖为当前 `check_id` |
| P4 | read-scope 绝对/项目外路径仍可 pass | **成立（高）** | 读声明必须是仓库相对路径；绝对/`..`/盘符拒 |
| P5 | status 先提示重发/缺口，晚于主会话补证 | **成立（中）** | 先提示 `--main-review-draft` 与同轮补证，再提示 gap |
| P6 | §1.1/§1.5 与 wf-start 首次写入边界 | **成立（中）** | §1.5 先 AI 判断再交人；wf-start 禁写时不得先 enable |
| Q1/P1 | 同进程身份轮换 | 已声明边界 | 不在本轮扩围 |
| Q2/P2 | 复核面复杂度、设计/机制重复、机械修订粗粒度、read-scope 激励 | 已声明/保留边界 | 不再叠机制；留 dogfood/后续 |

## Seventeenth-round Audit (2026-11-20)

| ID | 新审查意见 | 复核判定 | 处置 |
|---|---|---|---|
| R1 | 发起后 PRD/Check 失效，review-context 仍取材料 | **成立（高）** | 物化前复查批准版本与 Check 有效性；失效即阻断 |
| R2 | `pkg/.env` 未被子目录必排面覆盖 | **成立（高）** | 默认必排面增 `**/.env` 等同名敏感文件 |
| R3 | 同一报告两条 blocking 共用 id，可被一条处置关闭 | **成立（高）** | findings id 在单份报告内必须唯一 |
| R4 | gap acceptance 未绑定 task，可跨任务复用 | **成立（中）** | 接受文件须含 `task`，校验与摘要纳入 |
| R5 | 报告已写完未导入、fail 后误报被导向新轮 | **成立（中）** | status 先提示 review-import；fail 轮提示同轮 plan+main-review 重判 |
| R6 | 缺正式引用被误导向先请人扩授权 | **成立（中）** | 原触碰面内能修就继续修并说明缺判据；只有改验收/承诺/授权才请人扩判据 |
| S1/P2 | 验收轴无法读基线 | **成立** | 默认 spec 增 `.wf/baseline.md` |
| S2/P1-P5 | 身份轮换、复杂度、机制重复、机械粒度、越界激励 | 已声明边界 | 不在本轮扩围 |

## Eighteenth-round Audit (2026-11-20)

| ID | 新审查意见 | 复核判定 | 处置 |
|---|---|---|---|
| T1 | 两份 reviewer 全 uncovered，主会话自查五轴后仍 pass | **成立（高）** | 至少一份 reviewer 报告实际覆盖某轴；否则不构成复杂任务异种审查 |
| T2 | task-replan 清空 approval 后 `review-context` 仍取材料 | **成立（高）** | 对 `approval` 键（含 null）复查；失效即阻断物化 |
| T3 | `./.wf/tasks/...` 等价路径绕过读取面比较 | **成立（高）** | 读/排除声明比较前统一 `paths.normalize` |
| T4 | 默认请求把必排敏感文件放进 diff.paths，随后被自己拒绝 | **成立（中）** | 默认 diff.paths 先扣必排面 |
| T5 | 一份报告 done、一份在写时 status 先让等待；失效 Check 仍提示先重判 | **成立（中）** | status 先提示已 done 的 review-import；repair skill 改为必须先重查 |
| U1/P1-P5 | 身份轮换、复杂度/重复、机械粒度、越界激励 | 已声明边界 | 不在本轮扩围 |

## Nineteenth-round Audit (2026-11-20)

| ID | 新审查意见 | 复核判定 | 处置 |
|---|---|---|---|
| V1 | 一位 reviewer 全 uncovered/unavailable，另一位+主会话仍 pass | **成立（高）** | 每份 reviewer 报告至少实际覆盖一轴；不能互相代偿 |
| V2 | 标准漂移先于 unavailable/register-only 检查，阻塞事实登记 | **成立（中）** | standard-drift 只阻断正式判定；unavailable/register-only 不受阻 |
| V3 | 中断后 review-context 不能恢复 in-progress 草稿 | **成立（中）** | 同 agent/轮次重入返回同一 materials/report_path，不覆盖草稿 |
| V4 | lint 遇 findings 非数组/round 非数字崩溃或漏报 | **成立（中）** | 形状检查覆盖数组/整数字段；lint 用归一列表不遍历原值 |
| V5 | disposition 歧义误标人裁；reviewer skill 缺 finding id 唯一说明 | **成立（指引）** | 改为 AI 补 round+slot 重交；wf-review 明写单份唯一 |
| V6 | register-only 在失效 Check/批准下仍可登记关闭，借旧 passed | **成立（高）** | register-only --plan 同核批准/Check；失效拒绝 |
| V7 | 失效 Check 出口提示用 unavailable 规避 | **成立** | 删除该出口；Check 失效不属审查不可用声明 |
| W1/P1-P6 | 身份轮换、统计埋点、机械粒度、文档重复、越界激励 | 已声明边界 | 不在本轮扩围 |

## Twentieth-round Audit (2026-11-20)

| ID | 新审查意见 | 复核判定 | 处置 |
|---|---|---|---|
| X1 | 交付集合按 `.wf/` 前缀误排除项目自己的 spec | **成立（高）** | 新增 `is_vendor_asset = is_vendor ∧ ¬is_project_data`，交付集合/策展路径/提交面统一口径 |
| X2 | 非法 `severity` 被静默当作非阻塞 | **成立（高）** | findings-shape 核 `blocking|suggestion`；非法值输入不成立且不产 verdict |
| X3 | `rule.md#不存在的子句` 借基础路径通过 | **成立（中）** | spec-rule 的子句引用须精确存在（broken-reference 仍走人复核） |
| X4 | 草稿 lint 与 skill 矛盾（in-progress 被判错） | **成立（中）** | `report_input_problems(require_done=)`；lint 视 in-progress 为预期并给 notes，import/decide 仍只认 done |
| X5 | 导入先解析 round，非数字抛裸 ValueError | **成立（中）** | 导入先做形状检查再比身份；round 解析容错 |
| Y1 | 机制复杂度斜率、证据日志、wf-start 冲突指引 | 部分已修/已声明 | `check.py` 已有完整验证日志；wf-start 第 1 步已有禁写判断；`judgments`/`sampling` 标注为待独立审点 |

## Twenty-first Audit (2026-11-20)

| ID | 新审查意见 | 复核判定 | 处置 |
|---|---|---|---|
| Z1 | `wf-review` 存在孤立代码围栏，后半篇被包进代码块 | **成立（高）** | 删多余围栏；协议块与后续步骤恢复为正文 |
| Z2 | 出口文案仍指向 `task-attribute` 处理未提交路径 | **成立** | tasks/check/scope 五处出口改为「未提交按批准触碰面归属；已提交才 `--commit`」 |
| Z3 | `unable` 跨轮锁死：后续轮带证据 accepted 仍不关闭 | **成立（高）** | 处置记 `submitted_round`；`unable` 只在同轮阻断，后续轮 accepted 需可解析证据 |
| Z4 | `all_findings` 与 `open_findings` 的 closed 口径不一致 | **成立** | `all_findings` 直接用 `open_findings` 的关闭集合 |
| Z5 | 非阻塞建议也必须逐条核实 | **成立（中）** | 只有 blocking 必填 `finding_review`；建议未核实记 `deferred_suggestions` |
| Z6 | 修正复核要 AI 重抄全部 `main_findings` | **成立（中）** | 入口按 id 并集合并（`merge_main_findings`），撤项仍只能走 dispositions |
| Z7 | 绑定 `check_id` 缺失时静默借用当前 Check | **成立（中）** | 绑定不存在 → 不可核实，不回退 |
| Z8 | 锚点漂移时草稿不可达且无去向 | **成立（中）** | stale facts 列 `stale_round_drafts` 与出口 |
| Z9 | 改规则/基线缺合法证据前缀 | **成立（中）** | 用 `p:<交付面内路径>`（X1 修复后 spec 进交付面），出口文案写明 |
| Z10 | 判定路径组合复杂度、补测试需 replan | 部分成立 | 回 Plan 边界写进 wf-continue：新增/改验证项＝改验收证据；补测试文件仍属 AI |

## Twenty-second Audit (2026-11-20)

| ID | 新审查意见 | 复核判定 | 处置 |
|---|---|---|---|
| AA1 | 追加 finding 时旧 `unable` 被缺省规则自动改成 `verified` | **成立（高）** | `merge_main_findings` 同时沿用被并入项的 `finding_review` 状态 |
| AA2 | `--main-review-draft` 给建议也生成空占位，延后仍撞格式门禁 | **成立（中）** | 骨架只给 blocking 留占位 |
| AA3 | 跨轮 `unable→accepted` 关闭无证据强制 | **不成立（已实现）** | Z3 已让该路径按 `verified` 处理并要求 `verified_closure_problems` 证据；本轮补两条锁定用例 |
| AA4 | 判定拒绝循环无收敛保障 | 观察项 | 不加机制；留真实 dogfood 实测拒绝次数 |

## Twenty-third Audit (2026-11-20)

| ID | 新审查意见 | 复核判定 | 处置 |
|---|---|---|---|
| AB1 | 用默认草稿重交复核仍会把旧 `unable` 变成 `verified`（合并提前返回） | **成立（高）** | `main_findings` 与 `finding_review` 分开继承，不再依赖“有待补回项”才继承核实状态 |
| AB2 | 增量登记时继承的 reviewer 核实条目被判 unknown finding | **成立（中）** | 登记入口已知集合取任务全量；discovery 不再要求逐条核实 reviewer blocking |

## Requirements

### R1 审查发起必须复用 Check 有效性

- `review.launch` 在锁内重读任务后调用 `gates.check_validity`；非有效即按其 code/facts 阻断，不再只核 `result`。
- `review-context` 在物化材料前核对 launch 记录的 `anchor.check_anchor` 与当前锚点；不一致即 `WF_CHECK_STALE`，不重写材料、不生成新骨架。
- 两处共用同一判据，不复制有效性逻辑。

### R2 覆盖必须消费主会话采信

- `merged_coverage` 改为消费完整主会话复核记录（axes + report_review）：
  - `reliance=none` 的报告不贡献覆盖；
  - `reliance=primary` 的报告贡献其 `pass/fail` 轴；
  - `reliance=partial` 的报告只贡献主会话在该轴 `sources` 中明确列出的槽位；
  - 主会话自己的 `pass/fail` 仍直接覆盖。
- 无主会话复核时（status 投影）保留报告原始覆盖并标注 `main_review_ready=false`；产生 verdict 时主会话复核必填。
- 更新设计稿 §6.5、机制稿 §9.2、`.trellis/spec/docs/wf-delivery-discipline.md` §11、`review-status` 投影与测试；索引语义消费点回写。

### R3 本轮 verdict 只由未关闭 blocking 触发

- `review.decide` 在写入本轮 dispositions 后，以「本轮 imports + 既有 dispositions + 本次 dispositions」重算未关闭 blocking；只有当前轮仍有未关闭 blocking 才 fail。
- 误报/重分类且无内容变化的 finding 经 `accepted` 关闭后，同一轮可重判 pass；已修复的 finding 仍须新 Check + 新轮（锚点变化）。
- 更新 `wf-repair-loop` 的 fail 轮重判表述；保留 `wf-review-action` 的误报关闭后可重判。

### R4 判定回显与错误码按可执行出口路由

- 缺 `--main-review`、主会话 `fail` 无 finding 改为 `WF_REVIEW_INVALID`，给出生成骨架/修复/登记判断的出口。
- `review-decide` 的 `next` 按 verdict 分流：pass → finish；fail → 范围内修复/重跑 Check/重新发起，或误报关闭后重判；unavailable → 暂停或经人重新分级。
- 不在错误码或文案里把 AI 可补齐的输入写成人判信号。

### R5 外发声明与物化绑定

- `write_materials` / `context` 以 launch 的 `submitted_scope` 为物化输入；`diff.paths` 必须是 `delivery_set` 的子集，`requirement` 必须是本任务 PRD，`test_results.check` 必须是当前 Check id；越界或脱节即拒绝。
- 报告导入/判定时，把报告 `read-scope` 与 launch `exclusions` 做机械矛盾检查：读声明命中排除面即 `WF_REVIEW_INVALID`。
- 不改变「授权摘要不证明具体路径」的既有边界；只让已声明的范围与已物化的材料一致。

### R6 版本身份与发行树

- 目标版本升为 `0.1.3`；同步 `docs/workflows/wf/README.md` 的目标版本说明，删除「0.1.0/0.1.1 已由 tag 固定」的失实句。
- `scripts/build-wf-release.py --version 0.1.3` 重建发行树；`--verify` 字节复现。
- 打包入口增加两项机械守卫：① 已存在 `wf-v<version>` tag 时拒绝重建同版（防止同号异内容）；② `--version` 必须与 README 目标版本一致。
- tag 只在用户同意提交后由人创建；本任务不建 tag、不推送、不提交。

### R7 §1.1 判据补全（设计稿修订闸门）

- 在 §1.1 判据句补两句：可计算是进入机制的条件，不等于设成硬门禁；是否阻断取决于它保护的明确承诺，结构事实可以只作 facts/next。承担明确残余风险（覆盖缺口、不可用、降级）也属交人。
- 同步更新设计稿 §8.2 的覆盖缺口行、索引语义消费点、机制稿 §0.1 修订摘要；运行 `validate-wf-design.py` 至绿。
- 不新增 skill、不新增层级；不在 skill 正文复制判据。

### R8 验证与回归

- 为 F1-F6 各加能区分的断言；至少对 F1、F2、F3、F6 做回退注入验证（临时恢复旧实现时新断言变红）。
- 运行 T0 单元层、`WF_TAGS=review` 或相关套件、`validate-wf-design.py`、`build-wf-release.py --verify --verify-token-parity`。
- 不改 traffic_monitor 项目；新版真实 dogfood 作为后续验证义务记录，不在本任务宣称完成。

## Acceptance Criteria

- [x] 内容在 Check 后变化、未重查时，`review-launch` 返回 `WF_CHECK_STALE`，不写新 launch；`review-context` 对漂移轮返回 `WF_CHECK_STALE`，不重写材料。
- [x] 主会话五轴全 `uncovered`、两份报告 `reliance=none` 时，`review-decide` 以全未覆盖拒绝，不产生 `pass`。
- [x] `reliance=partial` 只在主会话该轴 `sources` 列出该槽位时贡献覆盖；未列出时不贡献。
- [x] 主会话 `disputed` + 处置 `accepted`（误报、无内容变化）时，同一轮 `review-decide` 可返回 `pass`；仍有未关闭 blocking 时返回 `fail`。
- [x] 缺 `--main-review` 返回 `WF_REVIEW_INVALID`，`next`/exits 指向 `--main-review-draft`；`fail` 的 `next` 指向修复/重跑 Check/重新发起或误报关闭后重判。
- [x] launch 的 `submitted_scope` 缩小生效：`review-context` 物化只含声明路径；放大会被拒绝；报告 `read-scope` 命中 launch `exclusions` 时被拒绝。
- [x] `docs/workflows/wf-release/wf-release.json` 为 `0.1.3` 且与 README 一致；`build-wf-release.py --verify` 字节复现；同版 tag 已存在时 `--version` 拒绝。
- [x] 设计稿 §1.1/§6.5、机制稿 §9.2、交付纪律 §11、`wf-repair-loop` 文案与代码一致；`validate-wf-design.py` 绿。
- [x] T0 单元层全绿；相关 review 套件全绿；新增断言做过回退注入验证。
- [x] 不提交、不建 tag、不推送；收尾前报告未做新版真实 dogfood 的边界。
- [x] 报告/launch 的 `check_id` 与当前 Check 不同即拒绝，即使 `check_anchor` 相同。
- [x] launch 阶段拒绝 `diff.paths` 缺失/越界；报告 `read-scope` 命中 launch exclusions 或超出 readable_scope 即拒绝。
- [x] 主会话 `sources` 引用 `reliance=none` 或未覆盖该轴的报告即拒绝；覆盖来源不再一律记成 main。
- [x] fail 后允许追加修正复核；pass/unavailable 后拒绝替换；仍有 fail 轴不得产 pass。
- [x] 收窄事实在 launch facts、context facts、review-status 与 `status --short` 的 `launch_scope` 可见。
- [x] `diff.paths` 与本轮 `exclusions` 交叠、为 `null` 或非数组时拒绝；重复路径去重后计 selected。
- [x] 已确认 blocking 直接记录 fail，不被其他轴的覆盖缺口拦住。
- [x] 主会话 `pass` 引用该轴判 `fail` 的报告即拒绝；`verified` finding 的 accepted 关闭无 `evidence_refs` 即拒绝。
- [x] `check.json` 不含 `internal_review` 等实施侧自评。
- [x] 旧布尔 `diff` 形状材料先扣 `exclusions`；`status.json` buckets 只列物化路径。
- [x] 报告 `read-scope` 使用可证包含判断，不能用字面 glob 放宽 `readable_scope`。
- [x] 判定 `result.scope` 记录 selected/unselected/total/narrowed。
- [x] 五轴全未覆盖但已有经复核 blocking 时允许记录 fail。
- [x] 请求 `exclusions` 不能删掉必排敏感面；显式空 `readable_scope` 拒绝读取声明。
- [x] 收窄材料时 `reliance=primary` 不再自动覆盖全部轴，需该轴 `sources` 显式列出槽位。
- [x] 有 blocking 时提交的缺口接受文件记入 `gap_acceptance_ignored` 事实。
- [x] 骨架不预填 sources；旧 launch 判定端能重算 selected/narrowed；收窄时 `uncovered`+`primary` 矛盾拒绝。
- [x] `.wf/`/`.git/` 控制面读取默认拒绝；只读材料包可写 `materials`，显式空 readable_scope 允许空 read-scope。
- [x] 已核实 blocking 不被无关覆盖冲突挡住；本任务 PRD 放行后不再被判排除冲突。
- [x] 轮次记录写实际核验的外发确认摘要；旧 launch 范围重算失败在 facts 标记。
- [x] 主会话 `main_findings` 可正式 fail，关闭走 `slot:"main"`，修正复核不能静默丢弃或只改 severity。
- [x] `evidence_refs` 可解析且 `v:` 验证 passed；跨轮关闭按提出轮 check 核。
- [x] 已登记人复核在同轮重判生效；broken-reference 仅对确实改过的规则要求人复核。
- [x] 报告未到齐时可用 `--register-only --main-review` 登记 main findings，不产生 verdict。
- [x] `v:` 通过状态只取 Check 记录；不存在/未通过的证据不能关闭。
- [x] `d:` 必须有当前漂移位置；`s/g/h` 不作关闭证据；历史关闭不按新 Check 重验。
- [x] register-only 可保留原 finding 追加第二条，旧记录标 supersedes。
- [x] 已判 pass/unavailable 的轮次不能被 register-only 改写主会话复核。
- [x] 先关闭、后核实为 verified 时，核实那次必须补可解析证据。
- [x] register-only 最小主会话 finding 文件只需 task/round/main_findings。
- [x] 已落盘关闭在首次 verified 时也核证据；历史证据回退历史 Check。
- [x] 同一 finding 按最新处置，旧空证据不阻断补齐后的有效关闭。
- [x] 唯一推断的 finding slot 写回，证据索引不漏核。
- [x] 关闭处置绑定 `check_id`；本次关闭不借同名旧 passed，历史关闭只认绑定那次。
- [x] 同一 finding 按最新处置（含 amended）；撤回关闭后不再要求旧 accepted 补证。
- [x] vendor_dirty 与判据外 main finding 有明确指引出口。
- [x] unable 的 accepted 不关闭；失效 Check 不产 verdict；机械修订核验证项定义。
- [x] status 区分 writing/arrived，格式错误不抛 TypeError，lint 可在 done 前跑。
- [x] 默认 spec 覆盖 `.wf/spec/**`；task-attribute/审查身份口径对齐。
- [x] 规划批准失效阻断审查；blocking 缺 id 输入不成立；新处置强制当前 check_id。
- [x] read-scope 拒绝绝对/项目外路径；status 先提示主会话补证。
- [x] review-context 物化前复查批准/Check；子目录敏感文件必排。
- [x] finding id 单份唯一；gap acceptance 绑定 task。
- [x] 报告写完先 review-import；fail 误报提示同轮重判；缺正式判据不强制先请批。
- [x] 至少一份 reviewer 报告实际覆盖某轴；两份全 uncovered 不构成 pass。
- [x] replan 后 context 阻断；`./` 等价路径归一；默认 diff.paths 先扣必排面。
- [x] 每份 reviewer 报告至少覆盖一轴；unavailable/register-only 不被漂移阻断。
- [x] 项目数据（`.wf/spec/**`）归本任务时进交付集合；框架资产判定复用 `is_project_data`。
- [x] severity 枚举、spec 子句存在性、草稿 lint、导入形状优先均已机械化。
- [x] `unable` 只在同轮阻断；`all_findings` 与 `open_findings` 同口径。
- [x] 只有 blocking 必填核实；`main_findings` 由入口并集合并。
- [x] 绑定 Check 缺失不回退；锚点漂移列出草稿；规则修复用 `p:` 表达。
- [x] 增量追加 finding 沿用原核实状态；复核骨架只给 blocking 留占位。
- [x] 草稿重交也继承核实状态；增量登记的继承条目不再判未知。
- [x] 跨轮 unable 关闭必须有可解析证据（用例锁定）。
- [x] in-progress 草稿可续写；lint 对 findings/round 形状不崩溃。
- [x] register-only 关闭同核批准/Check；失效 Check 不以 unavailable 规避。
- [x] blocking main finding 同核 `assertion_ref` 批准集合与规则不得自证；`finding_review` 可省。
- [x] `readable_scope.prd` 只能是本任务 PRD；轮次 `export_decision` 写已核验摘要。
- [x] 跨轮关闭 verified main finding 仍按提出轮复核 check 核 evidence_refs。
- [x] main finding 的 broken-reference 豁免进入人复核清单；main finding 进入 `all_findings`/草稿/`f:` 引用。

## Out of Scope

- `upgrade --apply` 的完整交付（第三轮能力，README 已声明；本任务不伪装为已修）。
- 在 traffic_monitor 上重跑真实 dogfood（作者仓库外；作为后续验证义务）。
- `task-attribute` 接管未提交面外文件（当前设计由 touch_paths/扩范围处理）。
- PRD 机读块的 dry-run 预检与报告状态头 400 字符外的识别（体验优化，不改变判定）。

## Resolved Decisions

- 2026-11-20 用户确认按 R1-R8 全量实施；F2/F3/F6/F9 与 F1/F4/F5/F7 同批修正。
- 版本号取 `0.1.3`；`0.1.2` 曾在 `da1d9605` 生成过不同内容的树，不复用。tag 由人在提交后创建。
- `upgrade --apply` 与新版真实 dogfood 不在本轮交付；收尾只如实声明。