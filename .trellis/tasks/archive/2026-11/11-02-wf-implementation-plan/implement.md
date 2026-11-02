# 执行计划（implement）

## 顺序清单

1. [x] 复核 git 状态与机检基线（HEAD `13965ad`；`输入摘要 4/4`；check-doc-refs 0 problem）。
2. [x] 读必读输入：charter 全文、设计稿全文、机制稿全文、索引表、来源说明、`.trellis/spec/docs/` 的 gate 与实现约束。
3. [x] 起草文档骨架（§0–§9），先写 §0 的 charter 遵循声明与分工句。
4. [x] 写 §1 资产/数据布局表（逐项到文件名，四列：类型/路径/所有者/升级卸载覆盖）。
5. [x] 写 §2 命令面（引导层 + 语义层；命令→§11.3 操作→§2.2 状态机→§3 路径判定四列表）。
6. [x] 写 §3 引导与执行器解析、§4 发行物组装（含 `wf-release.json` 键表与摘要公式落点、gitignore 段）。
7. [x] 写 §5 审查适配、§6 首轮清单（D01–D38 逐行 + 轮次）。
8. [x] 写 §7 验证映射（五条顺序 + 门禁→场景矩阵）、§8 速查、§9 未落地项。
9. [x] 复核：上游四文件未被改动（`git status` / `git diff --stat`）；本文不新增哈希域；本文无第二套门禁规则。
10. [x] 跑自检并把实际输出写进交付报告。

## 验证命令

```bash
/softwares/python/bin/python3 scripts/validate-wf-design.py     # 期望输入摘要 4/4 且全绿
/softwares/python/bin/python3 scripts/check-doc-refs.py         # 期望 0 problem(s)
/softwares/python/bin/python3 -m unittest scripts.tests.test_validate_wf_design
git status --short && git diff --stat
```

## 风险文件与回退点

- 风险文件：无源文件改动；唯一写操作是新增 `docs/workflows/wf-framework-implementation.md` 与任务目录三件套。
- 回退点：§9 登记未落地项；若复核发现越界（复制判定/schema），删除该段而不动上游文件。
- 禁止：修改四份上游文件、`skills/`、`.trellis/spec/`、`scripts/`；提交/归档/finish（未获授权）。

## 开工前检查

- [x] 任务创建并获人同意（本会话第一步）。
- [x] 四项范围决策已由人确认（落点/速查位置/机检四项去留/是否写代码）。
- [x] 规划产物经人复核后 `task.py start --allow-empty-context`（inline 模式，jsonl 不策展）。

## 执行记录（2026-11-02）

- 产物：`docs/workflows/wf-framework-implementation.md`，578 行，10 章（§0–§9）。
- 自检实测：`机制稿：引用 555；二值场景 91/91；三档场景 13/13；输入摘要 4/4`；`OK：设计 720 行 / charter 129 行；定义位点 51+7；索引表 143 行；消费点缺项 0；三率 100%`；`check-doc-refs.py` 0 problem(s)；`unittest` 19 tests OK。
- 四份上游文件 SHA-256 与机制稿 §0.1 登记值逐一相同；`git diff --stat` 为空（无受版本控制文件被改）。
- 交叉核对：文中 `机制稿 §x.y` / `设计稿 §x.y` / `charter Tn` 引用全部可解析；设计稿 §8.2 场景名 90 个逐字命中；只使用机制稿 §11.1 的 34 枚原因码。
- 未运行：三夹具、五条最小验证顺序、审查链路、宿主身份能力、reviewer CLI 可用性（原因分类见文档 §9.1）。
- 未提交：按人指示不提交/不归档/不 finish。

## 第二轮执行记录（2026-11-02，按人裁落地 5 项）

- 机制稿 3 处受控改动（`git diff` 6 行）：§12.4 加实现方案指针；§11.3 状态动作集合登记 `task.retrospect`；§5.1 主记录归属同步。`validate-wf-design.py` 仍全绿，`引用 555 → 557`、`输入摘要 4/4`。
- `scripts/check-doc-refs.py` 扩展：新增 `机制稿 ` 前缀、列举继承规则、多文件参数（单文件输出格式不变）。用 /tmp 夹具实测四条规则：裸 `§9.9` 被报、`机制稿 §9.9` 豁免、`机制稿 §1.3、§8.1` 继承、`机制稿 §1.3 的定义与 §8.1` 不继承仍被报；多文件输出逐文件计数 + 总数。
- 实现方案文档同步：§0 引用约定、§1.5 发行说明要求、§2.3 `task.retrospect` 行与登记说明、§6.2 D36 处理器、§9.2 改为「已裁定事项与剩余待办」。文档自检：`check-doc-refs.py docs/workflows/wf-framework-implementation.md` 0 problem(s)。
- 复核：`validate-wf-design.py` 全绿；`unittest` 19 tests OK；四份保护文件 SHA-256 未变；未提交。

## 第二轮复审后补记（2026-11-02，按设计稿 §0 维护协议登记新增机制入口）

复审报告：`review-mechanism-batch.md`（独立上下文复审 + 编写方逐条核实）。机制稿本次共 7 处改动，均为登记完整性修正，未新增判定、未改原因码、未改门禁顺序。

- **定义**：`task.retrospect` 为状态动作，`control.task.retrospect` 按机制稿 §11.3 的 `id=control.<operation>` 公式派生；归属 continue 路由（机制稿 §2.1）。
- **写者**：当前任务入口（`wflib/tasks.py::retrospect`），在同一 action 内写 `task.retrospective`（required/evidence/conclusion）与 `task.retrospective-done` 的 completed 回执（机制稿 §11.2 回执写者句；人裁 ①）。
- **消费点**：机制稿 §11.2 的 `task.retrospective-done` gate；实现方案 §2.3 命令映射、§6.2 D36 执行面、§9.2 已裁定事项。
- **失败出口**：不新增原因码。复盘证据缺失/未覆盖 P 时由 §11.2 的 gate 阻断归档，按 §11.1 码表取码（语义未决面 `WF_SEMANTIC_DECISION`）；可选复盘 `required=false` 不进 applies，不产生门禁。
- **正例**：无触发事实时人主动要求复盘 → 记录 `required=false`、结论照记、归档不受影响。**反例**：存在 `debug-ruling`「同一问题」裁定或返工/审查失败事实而未复盘就归档 → gate 缺项，归档被挡（报缺失步骤与原因事实）。
- **索引同步**：`wf-framework-design.index.md` 无操作名行——索引只登记设计稿/charter 的定义位点，机制操作名不是设计稿定义，故本变更在索引中无对应行；不新增操作行以保持索引口径（「同步索引」在此为空操作，非遗漏）。
- **机检**：`validate-wf-design.py` 全绿（引用 559；二值 91/91；三档 13/13；输入摘要 4/4）；`check-doc-refs.py` 机制稿与实现方案均 0 problem(s)；`unittest` 19 tests OK。
- **复审独立性边界**：同一操作者会话下的独立上下文子代理（冷启动、未参与编写），不是另一 CLI/另一台机器；结论不宣称防伪。

## 第三轮：批次全文同批复审（2026-11-02，人裁「只执行①」）

- 复审报告：`review-batch-round2.md`（独立上下文复审 + 编写方逐条核实）。被审绑定：机制稿 `7cef366c…`（1141 行，7 处）、实现方案 `1f3469ef…`（590 行，修正前）、`check-doc-refs.py` `deb02612…`。
- 覆盖：A 遵循/分工、B 与机制稿一致性（D01–D38、G01–G22、34 枚码、命令→操作名脚本比对）、C 资产与发行物事实、D 首轮下限/轮次、E 速查与档位。未覆盖：门禁与夹具未运行、脚本实现质量、索引登记判定、charter T2/T3 逐条闭合、机制稿 §8.4/§8.5 逐行。
- 结论：15 条发现（阻断 2 / 需人裁决 4 / 建议 9），全部已在实现方案内处置：F1 档位拆分、F2 引导层 `confirm-executor` 分支、F3 人裁「映射到已登记操作名」（`run.create`/`run.pause`/`enable` 不再充当操作名）、F4 `definition validate` 统一为公开只读子命令、F5 两棵树补 `install.py`、F6 解析落点改为「引导层唯一实现，`wflib/config.py` 只读结果」、F7 `§5.5` 悬空改指、F8 两处章节号、F9 G01 补边界场景行、F10 skill 计数、F11/F12 名称级引用与信封措辞、F13 D08/D33 附注、F14 速查档位说明、F15 前缀枚举。
- 未发现自造 schema、原因码改义或第二套门禁顺序；90 个场景名逐字命中，G/D 编号一致。
- 机检（修正后实跑）：`check-doc-refs.py` 七份文档 0 problem(s)（实现方案 strict）；`validate-wf-design.py` 全绿（引用 559；输入摘要 4/4）；`unittest` 19 tests OK；操作名脚本比对无未知操作。
- 残余边界：V1–V5、F0–F2 与全部门禁**未运行**；文档层面可交付，运行层面未验证。未提交。

## 第四轮：按外部审查 F1–F8 重构（2026-11-02）

外部审查提出 8 条，逐条在现行文档上核实，全部成立（无一条属旧版本残留的误报），按「改结构而非补句」处置：

| # | 事实 | 重构方式 |
|---|---|---|
| F1 | §2.2 把 `spec --file` 列为「不需要信封」，但 §2.3 要它写本会话读取侧车；机制稿 §11.2 的 `task.spec-loaded` P 含 `session_key`，身份只经信封 | §2.2 不再逐条列命令，改为**三条规则**：信封必需（写侧车或判定字段的命令，含 `spec --file`）／信封可选（`status`/`gate`/`inspect`/`version`，纯只读且 `position.session` 置 null）／引导层与独立脚本例外；§2.3 `spec` 行同步 |
| F2 | `review-launch` 参数面表达不了机制稿 §9.1 的 `launches`（slots 复数、结构化材料范围、round 由入口分配）；slot 与 reviewer-id 两套命名 | 参数改为 `--launch-request <path>`，给出 JSON 骨架（`implementation_clis`、`slots[{slot, reviewer_cli}]`、`submitted_scope`、`readable_scope`、`exclusions`、`export_decision`），round/attempt/anchor/temp_paths 由入口生成回显；**统一槽位 id = `--reviewer-id`**，§1.4、§5.1、§5.2 的报告/暂存命名全部改为 `<slot>` |
| F3 | `task-new` 与 `bind` 都不承载「acquire + 首次绑定 + task.create」父 action，按字面顺序两步都会违反设计稿 §4.4 | `task-new` 明定为**单一父 action**（`writer.acquire` + `session.bind` + `task.create`，主记录 writer）；`bind` 降为「绑定既有就绪对象或交接第二段，不承担首次创建」；§7.1 V1 的触发路径随之改写 |
| F4 | §3.4 的 git 只读子查询枚举读不出 trailer（需 `log --format`）也做不了拓扑逆序树核对（需 `diff-tree`/`ls-tree`） | 改为原则句「只读、不改状态、不写引用」+ 四类示例（解析/可达、提交内容与归属、树与差异、忽略判定），并显式列出仍被禁止的写类子命令 |
| F5 | D20 说引导层是唯一实现，D21 又把确认/匹配放在 `wflib/config.py` | D20/D21 统一：第 3 步 `confirm-executor`（探测+写元组）与第 4 步匹配都在引导层；`wflib/config.py` 只读取用于展示/诊断 |
| F6 | §4.6 开发态部署没落设计稿 §4.4 的首装契约（初始维护持有 + `.wf/writer.json`/`.wf/`/锁） | §4.6 增加「首装契约（与正式安装同构）」：同一最小互斥内创建 `.wf-lock`、`.wf/`、`.wf/writer.json`（维护持有、gen 从 0 递增）、列入预览、投放后释放为空闲；无 `writer.json` 不算已安装 |
| F7 | 机制稿 §7.1 委托的 `step_artifact` 产物根无落点；`run` 族参数以省略号带过 | §1.1 树与 §1.3 数据表补 `.wf/workflow-runs/<run-id>/artifacts/<step-id>/`；§2.3 给出 `run` 五个子动作的参数骨架与 `run create --request` 的语义 |
| F8 | §6.1/§6.4 第三轮汇总句漏 D28（升级/purge 令牌）与 D33（落点表全分支） | 两处第三轮表述补齐六个条目并标 D 号 |

连带一致性修正（避免新问题）：D20 的「第 3–4 步」改为与新引导层编号一致；V1 触发改为 `task-new`；无残留 `--implemented-by`/`--reviewer-cli`/`reviewer-id>`/「非会话」。

机检（实跑）：`check-doc-refs.py` 实现方案 0 problem(s)（strict）与默认路径 0；`validate-wf-design.py` 全绿（引用 559；输入摘要 4/4）；`unittest` 19 tests OK；表格列数检查 0 异常；文档 622 行。未提交。

## 第五轮：外部审查 R1–R4 修正（2026-11-02）

四条全部在现行文档上核实成立，按「一次改判定、不留第二写法」处置：

| # | 事实 | 修正 |
|---|---|---|
| R1 | §2.3 骨架写「slots 至少两项」，与 §5.3 的 degraded 单 reviewer 路径互斥 | 骨架改为「slots 至少一项」：两项且 CLI 两两不同且都不在 `implementation_clis` 时满足复杂任务完成条件；只有一项时**同一命令放行**，入口在 `launches` 与 `result` 标 `degraded: single-provider`，判定仍归机制稿 §9.2；§5.3 同步写明单 reviewer 走同一 `review-launch` |
| R2 | 信封清单漏 `dep`（写前置集合）与 `upgrade`（维护类、人直调无 stdin 信封） | 必需清单补 `dep`；第三条改为「引导层、独立脚本与维护入口」，补 `upgrade --apply` 并注明维护不以会话绑定授权（机制稿 §2.1） |
| R3 | `position.session` 不是机制稿 §11.1 的 position 键 | 改为「`position.scope` 为 null」，并注明 position 的六个键 |
| R4 | 首轮归档/启动的复评触发与「第二轮交付」冲突，可能被实现成 `WF_CAPABILITY_UNAVAILABLE` 而永留待复评 | §6.4 后加一段：首轮触发按**空挂起集合**直接通过、不写记录、不产生待决、不得报能力不可用；有挂起任务时的复评与 `task-reassess` 完整路径属第二轮 |

机检（实跑）：实现方案 strict 0 problem(s)；七份文档 0 problem(s)；`validate-wf-design.py` 全绿（引用 559；输入摘要 4/4）；`unittest` 19 tests OK；表格列数 0 异常；`position.session` 残留 0；文档 624 行。未提交。

## 第六轮：外部审查 N1–N2 修正（2026-11-02）

两条均核实成立，按「立一条约定、三处命令统一」处置：

| # | 事实 | 修正 |
|---|---|---|
| N1 | `stop`/`archive` 无承载「逐路径处置」「提交授权 `commit_grants`」「具名承接」的参数；单值 `--choice` 表达不了逐路径差异，且与 §8.2 速查的自述冲突 | 新增「结构化人工输入（约定）」小节：`--decision <path>`（单条 Decision 或数组，照机制稿 §1.1）与 `--plan <path>`（逐路径/批量处置计划，元素 `{path|object, choice, decision_ref, reason}`；`transfer` 须带具名对象、`commit` 须引用覆盖精确路径的授权）。`stop` 改 `--plan [--decision]`、`archive` 改 `--task --decision`、`review-decide` 的 `--dispositions` 统一为 `--plan`，§8.2 两行同步 |
| N2 | degraded 标注写进 `reviews.result` 越出该字段写者与取值（机制稿 §9.2：result 由 review.decide 写 pass/fail/unavailable） | 改为：`review-launch` 只在 `launches` 记 `degraded: single-provider`；`review-decide` 按机制稿 §9.2 判 fail（单 reviewer 属人数不合格），degraded 事实由 result 引用的 launches 条目呈现，不写 result 字段。§2.3 与 §5.3 两处同步 |

机检（实跑）：实现方案 strict 0 problem(s)；七份文档 0 problem(s)；`validate-wf-design.py` 全绿（引用 559；输入摘要 4/4）；`unittest` 19 tests OK；表格列数 0 异常；`--choice` 与 `dispositions` 残留 0。未提交。

## 第七轮：外部审查 M1/L1/L2 修正（2026-11-02）

三条均核实成立，其中 M1 是对第六轮 N1 建议的自我纠正（逐路径混合去向超出上位模型）：

| # | 事实 | 修正 |
|---|---|---|
| M1 | `stop` 承诺「逐路径去向」，但设计稿 §4.4 的收工是**单一选择**、机制稿 §4.3 的 `decision` 只有四值且 wip 记录的 `paths` 只存逐路径状态、无 per-path choice → 下位越权 | 收工改回单一选择：`stop --decision <path>`（数组含**一条**收工选择 + 提交/反向修正授权），`subject` 列覆盖路径或承接对象；`--plan` 不再服务 stop；§8.2 速查与 §8.3 叙述同步，并写明「混合处理要拆成多轮或先改机制稿 §4.3 的 wip schema」 |
| L1 | `--plan` 元素 `{path\|object, …}` 对不上 `dispositions` 的具名 finding | 元素改为 `{object\|finding, decision_ref, reason}`；`review-decide` 行注明元素是 finding，`run terminate` 注明元素是任务 |
| L2 | 约定首句「凡需要人的判断都用 JSON 文件」与 `task-knowledge --decision`、`review-decide --verdict` 的内联枚举自相矛盾 | 约定改为二分：**封闭枚举（≤3 值、取值由机制稿固定）可留命令行**；其余（含对象/路径/证据/理由）走 `--decision`/`--plan` 文件 |

机检（实跑）：实现方案 strict 0 problem(s)；`validate-wf-design.py` 全绿（引用 559；输入摘要 4/4）；`unittest` 19 tests OK；表格列数 0 异常；`逐路径去向` 残留 0；文档 635 行。未提交。

## 第八轮：外部审查 1–6 修正（2026-11-02）

六条全部核实成立（含两条对上位的误读：Git 禁令扩权、install.py 归属），按「回上位 + 补接口」处置：

| # | 事实 | 修正 |
|---|---|---|
| 1 高 | §3.4 把 `commit`/`add` 列入禁令，与设计稿 §1.1「授权范围内的暂存、提交与初始化不属本条限制」冲突，归档无法实现 | 禁令恢复为**分支状态变更与历史改写**（checkout/switch/branch/merge/rebase/worktree/reset/push）；明确授权内按精确路径 `git add -- <path…>`、`git commit` 可执行且不得捎带（机制稿 §5.3），`git init`/首个 HEAD 属另行授权 |
| 2 高 | 信封无代次与重试载体，`WF_GENERATION_STALE` 与「重试必须引用旧 action.id」无参数落点 | 信封 `inputs` 增两个保留键：`generation`（只比对不授权；不等即 `WF_GENERATION_STALE`）、`retry_of_action`（按旧意图走重入四态；缺省按当前 revision 建新 action）；每个写类命令回显当前 generation 与 action_id |
| 3 高 | Check 的人判/双轴/调试裁定无输入通道，`task.work-satisfied` 的 completed 回执无落点 | 新增「证据与裁定的输入通道」表：argv 自行取证；`--decision` 承载 manual 验证与空 verification_ids 的验收决定（subject 带 plan.version 与 check.anchor）；`--review-notes` 承载双轴材料→`check.internal_review`；`task-check --decision` 承载 Execute 期调试声明与 debug-ruling；`task.work-satisfied` 的 completed 由 `task-check` 写（本文指定承载动作，机制稿只要求「执行入口」） |
| 4 高 | install.py 属发行资产却无清单归属，`rules_digest` 覆盖不到安装判定代码 | `target_class` 定义三值并新增 `release_only`（随发行交付、不投放、不参与 O/L/N 与卸载，仅入 `rules_digest`）；install.py 按该值登记；§9.2 第 5 项改为「打包脚本不入清单 / 安装器入清单」并说明取值域由本文定义（机制稿未定域） |
| 5 高 | `--request` 一名两用、安装与升级缺完整语法、reviewer 调用缺传递方式 | 信封文件改 `--envelope`、实例创建改 `--creation`；新增 §4.1.1 安装与升级完整语法（`--target/--release-ref/--source/--skill-root/--confirm`）；`review-launch` 为每槽位写 `<staging>/request.json` 并打印可直接执行的 `wf-review` 调用模板 |
| 6 中 | 审查导入路径缺 slug，按字面会写错目录 | 改为 `<task-dir>/review/review-round-<N>/<slot>.md`，并写明 `<task-dir>` 是由稳定 id 解析出的真实目录 `<task-id>-<slug>` |

机检（实跑）：实现方案 strict 0 problem(s) 与默认路径 0；`validate-wf-design.py` 全绿（引用 559；输入摘要 4/4）；`unittest` 19 tests OK；表格列数 0 异常；`<task-id>/review/`、`--request <path>`、`install.py <目标` 残留均为 0；文档 674 行。未提交。

## 第九轮：外部审查 1–3 修正（2026-11-02）

三条均成立（第 1 条是「已有权威输入没有长期可读落点」，不是新机制）：

| # | 事实 | 修正 |
|---|---|---|
| 1 高 | 运行期要读的 `required_steps`/兼容声明/模板位点/`rules_digest` 输入只存在于发行源码根；安装记录只存摘要，源码清理后无来源 | 新增 `.wf/install/release-manifest.json`（所选发行的完整清单原样副本）+ §4.2.1：落点、`manifest_digest` 一致性、**唯一读取入口** `wflib/assets.py::load_installed_manifest()`、缺失/不符的出口（`WF_ASSET_DECISION`）、首轮开发态同路径（来源 `dev-manifest.json`）；D22 落点同步 |
| 2 高 | `generation` 缺省语义未定：首次 acquire 与已持权业务写被混为一谈，漏传时「拒绝」或「补用当前代次」两读都通 | §2.2 拆成两类：**允许省略**（建立代次的动作与纯只读）／**必须携带**（其余持权业务写）；未携带与不匹配同判 `WF_GENERATION_STALE`（facts 区分两者，出口均为重新读取代次后重试）；并写明释放后重新 acquire 时旧材料被拒，不会被套进新授权期 |
| 3 高 | 文档承诺「可直接执行的调用模板」，但发行只投放 `SKILL.md`、且明确不做 PATH/shim，`wf-review` 可执行入口不存在 | 交接改为**人可粘贴到 reviewer CLI 会话的 skill 调用文本**（`/wf-review … --request <staging>/request.json`），并明确：不是 shell 命令、投放物只有 `SKILL.md`、宿主不支持文本调用时由人打开 skill 并给 request.json |

机检（实跑）：实现方案 strict 0 problem(s) 与默认路径 0；`validate-wf-design.py` 全绿（引用 559；输入摘要 4/4）；`unittest` 19 tests OK；表格列数 0 异常；`可直接执行`、`wf-review --request` 残留 0；文档 686 行。未提交。

## 第十轮：外部审查（代次分类）修正（2026-11-02）

一条成立：代次规则按命令族分类，把「建立写权」与「消费已有写权」混在一起，`definition prepare` 与 `run create` 被整族列进「必须携带」侧，而它们本就无前置代次。

| 事实 | 修正 |
|---|---|
| 首次准备定义要建立 preparation scope；准备释放后 `run create` 另建立实例写权与首次绑定——两者都没有可携带的前置代次，按原分类会被误拒或被迫复用准备代次 | §2.2 改为**按子动作分类**：允许省略＝①建立新代次（`writer acquire`、`handover accept`、`task-new`、**`definition prepare`**、**`run create`**、维护入口）＋②不写项目判定字段（纯只读、`definition validate`/`run locate` 只读断言、`spec --file` 侧车）；必须携带＝其余持权业务写（逐个子动作列出，含 `run advance/pause/terminate`）。新增一条：**不同写权期不共享代次**——准备代次不得用于创建实例，创建前先完成准备释放与工作区处置（机制稿 §4.2 末段）。`definition`/`run` 两行参数内标注哪个子动作建立代次、哪个只读 |

机检（实跑）：实现方案 strict 0 problem(s)；`validate-wf-design.py` 全绿（引用 559；输入摘要 4/4）；`unittest` 19 tests OK；表格列数 0 异常；文档 689 行。未提交。

## 第十一轮：外部审查 高1–高3 / 中1–中5 / 低1 修正（2026-11-02）

九条全部核实成立（其中高-1 是我把 repair 的应用逻辑错放进 `wflib`，会让坏运行时下的独立恢复不可达）：

| # | 事实 | 修正 |
|---|---|---|
| 高-1 | A3/A4 与 §3.3 禁止 repair/uninstall 导入 `wflib`，D09/D28 又把修复与令牌逻辑放在 `wflib/maintenance.py`，首轮无调用方 | D09 改为「全部逻辑自含于 `repair.py`」；D28 改为首轮两份入口各自自含；新增 **§4.5.1 预览令牌实现约定**（nonce 128 位、绑定预览摘要、同进程失效、两份实现必须一致并由发行自检用固定向量比对）；D27 与 G10 同步；`wflib/maintenance.py` 只服务第三轮 `upgrade` |
| 高-2 | `review-decide --verdict pass\|fail\|unavailable` 让人直接选结论，与设计稿 §6.5/机制稿 §9.2 的事实推导冲突，可绕过最终门禁第 3 项 | 改为 `review-decide --task --round [--plan] [--unavailable <path>]`：pass/fail **由入口按 §9.2 推导**，人只声明「环境不可用」；封闭枚举段的示例同步（审查结论不属封闭枚举） |
| 高-3 | dev-deploy 无 `--skill-root`、无预览确认，`installation.json.roots`、`session_profile`、Trellis 风险提示无落点 | 签名改为 `--target … --skill-root … [--skill-root …] [--preview] [--confirm]`；不带 `--confirm` 只出预览（含 `.wf/`、`writer.json`、`.wf-lock`、托管段、skill 根、Trellis 线索与风险）；速查行同步 |
| 中-1 | `task-knowledge --decision deferred` 在上位零依据，值域未登记 | 改为 `no-update\|updated`，具体操作由 `changes` 按机制稿 §8.4 记录；值域扩展须先回机制稿 §1.3 登记 |
| 中-2 | `--decision` 要求预含 `check.anchor`，但锚点只在 Check 内部算出 | 改为：文件侧只带 `plan.version` 与 `acceptance_id`/`verification_id`，**锚点由入口在写 `acceptance_results` 时核绑并补记** |
| 中-3 | `run locate` 在命令行、§2.2、末段三处两票对一票 | 定为**公开只读子动作**，从「没有公开子命令」列表移除（该列表只剩 `verification.resolve`、`asset.compare`） |
| 中-4 | 交接接收方走 `bind` 还是 `writer-handover accept` 不明 | 写明：`bind` 只用于空闲态新会话对既有对象的首次绑定（成组于写权获取），**交接接收一律走 `writer-handover accept`**（原子完成绑定核验＋代次授予）；`begin` 由旧写者发起 |
| 中-5 | `dev-manifest.json` 标称与正式清单同 schema，但哈希/rules_digest 的算法与时机未定 | `dev-manifest.json` 改为「登记资产清单/版本/标记，不含手填哈希」；`wf-dev-deploy.py` 按源树字节现算全部 digest 与 `rules_digest` 生成部署副本，算法与 `build-wf-release.py` 同一份，首轮锚点可复现 |
| 低-1 | upgrade 语法行的 `[--envelope]` 与「升级不需要信封」互斥 | 删除该可选项 |

机检（实跑）：实现方案 strict 0 problem(s) 与默认路径 0；`validate-wf-design.py` 全绿（引用 559；输入摘要 4/4）；`unittest` 19 tests OK；表格列数 0 异常；`deferred`/`--verdict` 残留 0；文档 699 行。未提交。

## 第十二轮：外部审查 中-1 / 低-1 / 低-2 / 低-3 修正（2026-11-02）

| # | 事实 | 修正 |
|---|---|---|
| 中-1 | D27 把回执读取/派生推到「引入维护语义入口的那一轮」（两读），而首轮 repair 就写回执、启动校验第⑩项与 V3 都要读；「人确认处置后写回原回执」在命令面无入口 | 拆开三层：**读**——`wflib/writer.py::receipt_state()` 首轮即落，按机制稿 §4.5 派生 persisted/applied_pending_commit/recovering，供启动校验⑩与 Check 的 a 类；**写**——`repair.py`/`uninstall.py` 自含；**应用与收敛**——`wflib/maintenance.py` 仅第三轮 upgrade。新增「维护组处置回写」段：`.wf/bin/repair.py --dispose <plan>`（机制稿 §5.4 已把「维护残留」列入 repair 对象）；并写明若人选「按登记终态原样提交」，启动时直接派生 persisted、无需回写。G10 实现面同步 |
| 低-1 | 「发行自检用固定向量」的落点与 nonce 注入方式未定，「拒绝发布」指向 authoring 侧 | 明确为 **authoring 发布前检查** `scripts/build-wf-release.py --verify-token-parity`，用显式 `--nonce`（仅测试形态）比对两份实现四步输出；不属于安装期自检，也不是运行期能力 |
| 低-2 | `task-knowledge` 取值仍称「由机制稿固定」，机制稿 §1.3 未登记值域 | 改为「由本文定义、语义取设计稿 §6.3；机制稿只登记字段未登记值域，扩展须先回机制稿登记」 |
| 低-3 | §4.6 断句错字「后退出。，按」；`--preview` 与「缺省即预览」重复；§2.2 代次清单漏 `bind`/`enable` | 修断句；删 `--preview`（缺省即预览、`--confirm` 才应用，三处签名一致）；代次「允许省略」侧补 `bind`（在其写权获取动作内成组）与 `enable`（只做启用检查） |

机检（实跑）：实现方案 strict 0 problem(s) 与默认路径 0；`validate-wf-design.py` 全绿（引用 559；输入摘要 4/4）；`unittest` 19 tests OK；表格列数 0 异常；`--preview`、`后退出。，` 残留 0；文档 700 行。未提交。

## 第十三轮：外部审查 低-1 + 两个提示项修正（2026-11-02）

| # | 事实 | 修正 |
|---|---|---|
| 低-1 | 「维护残留」的对象列举在设计稿 §5.5，机制稿 §5.4 只有算法与边界句——原引用的章节号去机制稿查不到依据 | 依据改为「设计稿 §5.5 的对象列举 + 机制稿 §4.5 的去向回写（该条未指定入口）」，并写明不越机制稿 §5.4 的边界（repair 不代替日常删边/内容修改/范围批准），处置回写只记人已确认的去向 |
| 提示-1 | `--dispose` 只出现在 §4.6，§2.3 的 repair 行与 §8.2 的速度表都看不出它有第二形态 | §2.3 repair 行补「第二形态 `--dispose <plan>` 做维护组处置回写（见 §4.6）」；§8.2 受控修复行补同名标注 |
| 提示-2 | D27 的派生三态把回执 `result` 与 `writer.state` 两个枚举混写 | 改为「每一项回执派生为『已持久化 / 已应用待提交 / 待核对』」，并显式注明这与 `writer.state` 的 idle/held/recovering 不是同一枚举 |

机检（实跑）：实现方案 strict 0 problem(s) 与默认路径 0；`validate-wf-design.py` 全绿（引用 559；输入摘要 4/4）；`unittest` 19 tests OK；文档 700 行。未提交。

## 第十四轮：外部审查（维护回执四态）修正（2026-11-02）

一条成立：上一轮把回执派生写成三态，漏了机制稿 §1.4 的合法 `disposed`，且「已处置后如何解除阻断」没有接到读取侧。

| 事实 | 修正 |
|---|---|
| 机制稿 §1.4 的 `maintenance_results.result` 合法值为 `applied_pending_commit`/`persisted`/`disposed`；§4.5 规定完成反向修正或具名承接后解除旧待处理组，回执保留到下一次维护收敛。三态写法会把「已处置但未收敛」的回执误判成待提交或待核对 | D27 改为**四态**：已持久化 / 已应用待提交 / **已处置**（`disposed`，含 disposition 的处置决定、核验事实与承接引用）/ 待核对；并写清消费口径——只有「已应用待提交且与请求范围重叠」才挡（`WF_WIP_UNRESOLVED`），「已处置」不挡但报告「已处置未收敛」，「待核对」报 `WF_HISTORY_UNRESOLVED`；解除看 `disposition` 的实质内容（不看字段存在），把回执移出 `maintenance_results` 是维护预览里的收敛动作，读取侧不做。§4.6 的处置回写段同步说明写回后的状态与保留期 |

机检（实跑）：实现方案 strict 0 problem(s)；`validate-wf-design.py` 全绿（引用 559；输入摘要 4/4）；`unittest` 19 tests OK。未提交。

## 第十五轮：外部审查（「保留现状」被误当结案）修正（2026-11-02）

一条成立，且是明文条件冲突：设计稿 §4.4（维护变更持久化）与机制稿 §4.5 只承认三条解除条件——该组路径已被独立提交、已完成反向修正、或已由具名任务承接（承接任务已批准、路径归属明确）；「保留现状」不在其中。

| 事实 | 修正 |
|---|---|
| 上一轮把「保留现状」与反向修正/承接并列为 `disposed` 的成立情形，于是 `repair --dispose` 记一条「保留现状」就能让重叠任务开工，跳过上位要求的归属处置 | D27 的「已处置」限定为**三条之一落实**且 `disposition` 齐全；**「保留现状」只留痕，回执仍按「已应用待提交」挡住重叠路径**。§4.6 的处置回写段同步：去向四选一可记录，但解除只认三条；`disposition` 缺决定/缺核验/缺承接引用或只记「保留现状」时按「已应用待提交 / 待核对」处理。引用同步修正为「设计稿 §4.4（维护变更持久化）与机制稿 §4.5」——设计稿 §5.5 只提供 repair 的对象列举 |

机检（实跑）：实现方案 strict 0 problem(s)；`validate-wf-design.py` 全绿（引用 559；输入摘要 4/4）；`unittest` 19 tests OK。未提交。

## 收口检查（2026-11-02，人工审查结束后）

- 机检：`validate-wf-design.py` 全绿（引用 559；二值 91/91；三档 13/13；**输入摘要 4/4**；七项检查 + 覆盖率断言通过）；`check-doc-refs.py` 七份文档各 0 problem(s)（实现方案/机制稿/charter strict，设计稿/旧计划 local，索引/来源 cross）；`unittest` 19 tests OK。
- 验收审计（脚本逐项）：A–I 共 27 项全部 PASS——含 D01–D38 齐 38 行、G01–G22 齐 22 行、charter 遵循声明、九键输出契约、清单键、tag 命名、gitignore 段、两副本、锚点、首轮就绪理由、首轮下限、二三轮单列、五条验证、速查四类行、「未运行」声明。
- 范围：受控文件 `wf-framework-mechanism.md`（8+/6−，SHA `7cef366c…` 仍等于第 2 轮复审绑定值）与 `scripts/check-doc-refs.py`（三模式，新增 98 行级改动）；新增 `docs/workflows/wf-framework-implementation.md`（700 行）；任务目录含 3 份产物 + 2 份复审报告。四份保护文件 `git diff` 为空、SHA 与机制稿 §0.1 登记值逐一相同。
- 未做（原因）：`.trellis/spec/` 未改（任务硬约束要求人明确批准）；运行层未验证（V1–V5、F0–F2 与全部门禁仍「未运行」）。
- 提交与归档：待人授权（本任务未自行提交）。
