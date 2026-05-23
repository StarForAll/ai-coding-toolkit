# Workflow 审计报告

## Audit Boundary

- Workflow Path: `docs/workflows/新项目开发工作流/`
- Target Project Fixture: `/tmp/trellis-0.5.17-2`
- Compatible Anchor Version: `0.5.17`
- Current Trellis Version: `0.5.17`
- Version Gate: `passed`
- Current CLI: `codex`
- Need Runtime Validation: `yes`（用户明确要求基于 `/tmp/trellis-0.5.17-2` 实际嵌入内容判断）

## Comparison Model

- `source repo`
- `generated target project` baseline (`trellis init`)
- `generated target project` workflow-installed state (`install-workflow.py`)
- `runtime command output`

## Candidate Issues

- 用户提供的 5 组候选问题 + 同类问题扩展扫描
- 扩展关注：
  - 首屏文档是否仍把 `test-first` / `start` 当成独立正式入口
  - 首屏图示与通俗文档是否仍描述过时阶段链
  - 版本锚点是否只存在于代码、未进入对外文档
  - 命令/脚本清单是否与实际源树不一致

## Confirmed Issues

1. `命令映射.md` 的“文件结构”清单已经明显过时，属于真实漂移，而不是用户描述的“单一不存在文件”问题。
   - 结论：`confirmed`
   - 严重度：`high`
   - 证据：
     - `[source repo]` [命令映射.md](/ops/projects/personal/ai-coding-toolkit/docs/workflows/新项目开发工作流/命令映射.md:560) 只列出部分命令/脚本，遗漏 `detect-embed-state.py`、`finish-work-patch-projectization.md`、`session-start-patch-strong-gate.md`、`start-skill-patch-phase-router.md`、`parallel-disabled.md` 等真实存在文件。
     - `[source repo]` `find docs/workflows/新项目开发工作流/commands -maxdepth 1 -type f | sort`
   - validation action：对照源目录真实文件列表与文档清单。

2. `阶段状态机与强门禁协议.md` 自称“单一事实源”，但没有把 `project-audit / check / review-gate / delivery` 的完整阶段职责、切换边界和退出契约写成同等层级规则，存在单一事实源不完整问题。
   - 结论：`confirmed`
   - 严重度：`medium`
   - 证据：
     - `[source repo]` [阶段状态机与强门禁协议.md](/ops/projects/personal/ai-coding-toolkit/docs/workflows/新项目开发工作流/阶段状态机与强门禁协议.md:1) 宣称为单一事实源。
     - `[source repo]` 该文档完整描述了 `workflow-state.json`、`continue` 边界、`design`/`plan` 特殊约束，但未对后半段四个阶段逐一给出对等的阶段级协议。
   - validation action：按“文档标题承诺”反查是否覆盖全阶段链。

3. `工作流总纲.md` 缺少显式的最低/兼容 Trellis 版本锚点，和代码中的 `COMPATIBLE_TRELLIS_VERSION = "0.5.17"` 已产生文档漂移。
   - 结论：`confirmed`
   - 严重度：`medium`
   - 证据：
     - `[source repo]` [工作流总纲.md](/ops/projects/personal/ai-coding-toolkit/docs/workflows/新项目开发工作流/工作流总纲.md:23) 只写“目标项目应优先使用当前最新 Trellis 基线”，未写兼容锚点。
     - `[source repo]` [workflow_assets.py](/ops/projects/personal/ai-coding-toolkit/docs/workflows/新项目开发工作流/commands/workflow_assets.py:24) 明确锚定 `COMPATIBLE_TRELLIS_VERSION = "0.5.17"`。
   - validation action：全文检索 `0.5.17` / `COMPATIBLE_TRELLIS_VERSION` 在对外总纲中的缺失。

4. `工作流嵌入执行规范.md` 未声明当前 workflow 版本 `0.1.28`，且初始态判定段出现文本替换污染，属于真实文档缺陷。
   - 结论：`confirmed`
   - 严重度：`medium`
   - 证据：
     - `[source repo]` [工作流嵌入执行规范.md](/ops/projects/personal/ai-coding-toolkit/docs/workflows/新项目开发工作流/工作流嵌入执行规范.md:90) 只把 `workflow_version` 当记录字段示例，未说明当前工作流版本。
     - `[source repo]` [工作流嵌入执行规范.md](/ops/projects/personal/ai-coding-toolkit/docs/workflows/新项目开发工作流/工作流嵌入执行规范.md:105) 出现 `Trellis 原生 /finish-work`、`trellis-Trellis 原生 /finish-work` 这类替换污染文本。
     - `[source repo]` [workflow_assets.py](/ops/projects/personal/ai-coding-toolkit/docs/workflows/新项目开发工作流/commands/workflow_assets.py:22) 明确当前 `WORKFLOW_VERSION = "0.1.28"`。
   - validation action：对照源代码常量与嵌入执行规范正文。

5. `test-first` 作为独立阶段/命令的僵尸引用仍跨多个首屏资产和脚本保留，已与“并入 implementation、不是独立公开入口”的现行协议冲突。
   - 结论：`confirmed`
   - 严重度：`high`
   - 证据：
     - `[source repo]` [阶段状态机与强门禁协议.md](/ops/projects/personal/ai-coding-toolkit/docs/workflows/新项目开发工作流/阶段状态机与强门禁协议.md:57) 已明确 `test-first` 不再作为独立阶段。
     - `[source repo]` [plan.md](/ops/projects/personal/ai-coding-toolkit/docs/workflows/新项目开发工作流/commands/plan.md:570)、[check.md](/ops/projects/personal/ai-coding-toolkit/docs/workflows/新项目开发工作流/commands/check.md:202)、[工作流思维导图.html](/ops/projects/personal/ai-coding-toolkit/docs/workflows/新项目开发工作流/工作流思维导图.html:84) 仍把 `/trellis:test-first` 当独立入口展示。
     - `[source repo]` [workflow-state.py](/ops/projects/personal/ai-coding-toolkit/docs/workflows/新项目开发工作流/commands/shell/workflow-state.py:1404) 与测试 [test_workflow_state.py](/ops/projects/personal/ai-coding-toolkit/docs/workflows/新项目开发工作流/commands/shell/test_workflow_state.py:3734) 仍保留 `allowed_next ... test-first` 特判。
   - validation action：全文检索 `test-first` 并按“独立入口/阶段”与“implementation 内测试先行模式”两类语义区分。

6. `工作流全局流转说明（通俗版）.md` 仍使用 legacy `start` 作为实现回退/继续入口，并把收尾链拆成过时的 `Finish-Work -> Delivery -> Session Record` 叙事，和现行主链不一致。
   - 结论：`confirmed`
   - 严重度：`high`
   - 证据：
     - `[source repo]` [工作流全局流转说明（通俗版）.md](/ops/projects/personal/ai-coding-toolkit/docs/workflows/新项目开发工作流/工作流全局流转说明（通俗版）.md:542) 明确写“回到 Start 修复”。
     - `[source repo]` [工作流全局流转说明（通俗版）.md](/ops/projects/personal/ai-coding-toolkit/docs/workflows/新项目开发工作流/工作流全局流转说明（通俗版）.md:576) 口诀仍写“进入 start”。
     - `[source repo]` [工作流全局流转说明（通俗版）.md](/ops/projects/personal/ai-coding-toolkit/docs/workflows/新项目开发工作流/工作流全局流转说明（通俗版）.md:445) 把 `Finish-Work` 写成单独阶段，再在后文另起 `7. Finish-Work（Session Record）`。
   - validation action：核对通俗版与现行 `continue -> check -> [review-gate] -> delivery -> native finish-work` 链。

7. `工作流思维导图.html` 已过时，仍展示 `/trellis:test-first`、`check/review-gate/delivery -> start` 回退、`delivery -> record-session` 等旧链路。
   - 结论：`confirmed`
   - 严重度：`medium`
   - 证据：
     - `[source repo]` [工作流思维导图.html](/ops/projects/personal/ai-coding-toolkit/docs/workflows/新项目开发工作流/工作流思维导图.html:84) 仍存在 `/trellis:test-first` 节点。
     - `[source repo]` [工作流思维导图.html](/ops/projects/personal/ai-coding-toolkit/docs/workflows/新项目开发工作流/工作流思维导图.html:125) 仍写 `check/review-gate/delivery -> start 修复`。
     - `[source repo]` [工作流思维导图.html](/ops/projects/personal/ai-coding-toolkit/docs/workflows/新项目开发工作流/工作流思维导图.html:111) 仍把 `delivery → record-session` 作为独立主链。
   - validation action：对照通俗版/总纲/阶段协议的现行链路。

8. `workflow-state.py` 周边确实存在可收敛的重复实现：`extract_backticked_field`、`_find_assessment_in_lineage`、`PLACEHOLDER_MARKERS`、`MIN_KICKOFF_PAYMENT_RATIO` 分散在多个 helper 中，属于真实维护性问题。
   - 结论：`confirmed`
   - 严重度：`medium`
   - 证据：
     - `[source repo]` `rg -n "extract_backticked_field|_find_assessment_in_lineage|PLACEHOLDER_MARKERS|MIN_KICKOFF_PAYMENT_RATIO" docs/workflows/新项目开发工作流/commands`
   - validation action：按符号名全目录检索重复定义。

9. `workflow-state.py` 本体过大是事实，但更适合作为后续重构议题，不适合作为本轮“高置信、低回归”修复项直接拆分。
   - 结论：`confirmed but not recommended in this patch set`
   - 严重度：`low`
   - 证据：
     - `[source repo]` `wc -l docs/workflows/新项目开发工作流/commands/shell/workflow-state.py`
   - validation action：统计行数并结合当前职责分布评估风险。

## False Alarms / Non-Defects

1. “NL 路由表与原生 skill routing 重复”不是当前嵌入目标项目上的真实 defect。
   - 结论：`false alarm`
   - 证据：
     - `[generated target project] workflow-installed state` [AGENTS.md](/tmp/trellis-0.5.17-2/AGENTS.md:24) 确实注入了 `workflow-nl-routing`，承担跨 CLI 入口映射，尤其是 Codex 无项目级 `/trellis:xxx` 命令目录时的入口说明。
     - `[generated target project] workflow-installed state` [/tmp/trellis-0.5.17-2/.trellis/workflow.md](/tmp/trellis-0.5.17-2/.trellis/workflow.md:76) 已改写为强门禁 projectized workflow，不再保留“原生两张 skill routing 表 + DO NOT skip skills”那套与 NL 路由表同层竞争的结构。
     - `[source repo]` [workflow_assets.py](/ops/projects/personal/ai-coding-toolkit/docs/workflows/新项目开发工作流/commands/workflow_assets.py:507) 把 AGENTS 路由块定义为 non-hook command discovery 合同的一部分。
   - validation action：对照目标项目嵌入后的 `.trellis/workflow.md` 与 `AGENTS.md` 实际承载职责。

2. “`task.py start` 状态翻转补丁是自造问题再自修”不成立。
   - 结论：`false alarm`
   - 证据：
     - `[generated target project] workflow-installed state` [/tmp/trellis-0.5.17-2/.trellis/workflow.md](/tmp/trellis-0.5.17-2/.trellis/workflow.md:76) 明确声明 `task.json.status` 只作 bookkeeping。
     - `[source repo]` [patch-task-start-strong-gate.py](/ops/projects/personal/ai-coding-toolkit/docs/workflows/新项目开发工作流/commands/shell/patch-task-start-strong-gate.py:1)、[patch-session-start-strong-gate.py](/ops/projects/personal/ai-coding-toolkit/docs/workflows/新项目开发工作流/commands/shell/patch-session-start-strong-gate.py:1)、[patch-task-status-view-strong-gate.py](/ops/projects/personal/ai-coding-toolkit/docs/workflows/新项目开发工作流/commands/shell/patch-task-status-view-strong-gate.py:1) 形成完整补丁链，统一把路由 authority 收敛到 `workflow-state.py route`。
     - `[generated target project] workflow-installed state` [/tmp/trellis-0.5.17-2/.trellis/scripts/task.py](/tmp/trellis-0.5.17-2/.trellis/scripts/task.py:114) 实际已被 no-flip patch 改写并配套 task view 补丁。
   - validation action：核对目标项目 `task.py`、startup carrier、task view 和 route helper 的一致性。

3. “`recovery_needed` route action 从未被生成”不成立。
   - 结论：`false alarm`
   - 证据：
     - `[source repo]` [workflow-state.py](/ops/projects/personal/ai-coding-toolkit/docs/workflows/新项目开发工作流/commands/shell/workflow-state.py:2339) 明确会在“有任务但 session 无 active task”场景输出 `recovery_needed`。
     - `[source repo]` [test_workflow_state.py](/ops/projects/personal/ai-coding-toolkit/docs/workflows/新项目开发工作流/commands/shell/test_workflow_state.py:1997) 有对应测试。
   - validation action：查看 route 分支与测试覆盖。

4. “`check-quality.py` 与原生 `trellis-check` 完全重复，应删除”不成立。
   - 结论：`false alarm`
   - 证据：
     - `[source repo]` [check-quality.py](/ops/projects/personal/ai-coding-toolkit/docs/workflows/新项目开发工作流/commands/shell/check-quality.py:1) 是一个薄包装 helper，只负责执行用户确认过的验证命令并输出 `pass/fail/not run`。
     - `[source repo]` [check.md](/ops/projects/personal/ai-coding-toolkit/docs/workflows/新项目开发工作流/commands/check.md:92) 把它放在 formal check 阶段的“项目化验证”步骤中使用，职责与 implementation 内部的 `trellis-check` agent 不同。
   - validation action：对照 helper 脚本职责与阶段命令正文。

## Evidence Gaps / Blockers

- 无版本门禁阻塞。
- `workflow-scan` / `workflow-repair` 技能在当前会话可见列表中存在，但磁盘路径不可读；本轮未依赖这两个技能结论，已改用 source repo + target fixture 直接取证。
- `workflow-state.py` 大拆分的最佳边界尚未设计，不建议在本轮与文档纠偏一起做。

## Proposed Fix Scope

建议把本轮修复包控制在“高置信、可验证、低回归”的两组：

### 修复包 A：文档与图示对齐

- 修 `命令映射.md` 的文件结构段，按真实源树更新，补齐漏项，去掉误导性过时说明。
- 在 `工作流总纲.md` 明确写入兼容 Trellis 锚点 `0.5.17`。
- 在 `工作流嵌入执行规范.md` 明确写入当前 workflow 版本 `0.1.28`，并修正 `finish-work` 相关替换污染文本。
- 修 `工作流全局流转说明（通俗版）.md` 中的 legacy `start`、过时 `Finish-Work/Session Record` 分层和口诀。
- 修 `工作流思维导图.html` 的阶段链、回退链和 `test-first` 节点，使其与当前协议一致。
- 补 `阶段状态机与强门禁协议.md` 对 `project-audit / check / review-gate / delivery` 的阶段级契约摘要，使“单一事实源”名副其实。

### 修复包 B：脚本与测试收敛

- 收敛 `test-first` 作为独立入口/阶段的残留：
  - 文档改成“implementation 内测试先行模式”；
  - `workflow-state.py` 去掉对独立 `test-first` 入口的额外兼容分支；
  - 同步调整 `test_workflow_state.py`、相关 installer tests 和引用文案。
- 视风险可控程度，抽取 `commands/shell/common/` 共享模块，先处理四组重复常量/函数：
  - `extract_backticked_field`
  - `_find_assessment_in_lineage`
  - `PLACEHOLDER_MARKERS`
  - `MIN_KICKOFF_PAYMENT_RATIO`

### 本轮不建议纳入

- 直接拆分 `workflow-state.py` 主文件。
- 取消 AGENTS NL 路由表。
- 回退 `task.py start` 的 no-flip 强门禁补丁。
