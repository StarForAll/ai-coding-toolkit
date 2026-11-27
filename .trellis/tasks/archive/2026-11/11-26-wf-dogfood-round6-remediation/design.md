# 设计：wf dogfood 六轮复核后的机制化修正

> 本文件只写技术设计与取舍；需求与验收见 [prd.md](./prd.md)，执行顺序见 [implement.md](./implement.md)。
> 设计原则承接设计稿 §1.1（判据句：先答资格、再答后置条件）与 charter T4/T5/T6：不新增层级、不新增 skill、不扩张机械面。

## 1. 复核方法与结论强度

- 复核对象：报告 a（7 条 P0/P1 + 场景 + §1.1）、报告 b（分工评估 + 时序缺陷 + 问题清单 + §1.1）。
- 复核手段：逐条读当前源码定位真实实现；不采信报告的行号与描述，以代码事实为准。报告 b 引用的行号可与当前树相差数十行（例：`_complexity_proposal` 实际在 `tasks.py:1648`，`expansion_condition` 在 `scope.py:296`），因此**按函数名与行为复核，不按行号**。
- 结论强度：本文件第 3 节的每条「真实」项都可反向定位到函数与判定分支；「误判」项写明反驳依据；「不在本轮」项写明原因与去向。

## 2. 主张判定表

| # | 主张（来源） | 判定 | 依据（当前源码事实） |
|---|---|---|---|
| 1 | 实例能建子任务，但子任务进不了四阶段（a.1） | **真实·P0** | `tasks._require_binding`（`tasks.py:1231`）只接受 `binding.object.id == task_id`；实例会话绑定的是 run。17 个日常写入口（`tasks.py:1888/2449/2677/2758/2786/2997/3316/3450/3487/3521/3610/4020/4321/4761/5008/5579`）用它，且锁内再用 `ctx.require_held(task=task_id)` 比 holder scope；实例 holder scope 是 run ⇒ 双重拒绝。`bind_task_for_write`（`tasks.py:5092`）已能正确判（run_id + cursor），但只被决策类入口与 review 用。另：`_release_after_archive`（`tasks.py:4195`）在子任务归档后释放整份写权，会破坏在途实例。 |
| 2 | 人判/略过成功后 `run advance` 报 `WF_HISTORY_UNRESOLVED`（a.2） | **真实·P0** | `runs.advance` 的①段（`runs.py:1514` 起）只要 `cursor.step_id` 存在就要求 `task_map[step_id].task_id` 且任务记录存在，否则抛 `WF_HISTORY_UNRESOLVED`；人判（`runs.py:1566`）与略过（`runs.py:1546` 区段）都写 `cursor={step_id, task_id:None}` 且 `step_results[step_id].kind=satisfied/skipped`。用例 `procedures` 只覆盖「人判→run finish」，未覆盖「人判→advance」。 |
| 3 | 长 Check 覆盖同会话刚写入的暂停（a.3） | **真实·P1** | `cmd_task_check`（`tasks.py:3316`）③段注释明写「不重读记录」（`tasks.py:3342` 附近）并沿用②段内存态 `task` 回写；暂停字段不在 `check.anchor_parts`（`check.py:183`）里 ⇒ 锁外期间同一会话的 `task-pause`/`run pause`（`tasks.py:2758`、`runs.py:1726` 会写任务 `paused`）被静默覆盖。窗口窄但确定可达（后台跑 Check + 同时暂停）。 |
| 4 | 复杂度判据既误升也漏判（a.4） | **真实·P1** | ①漏判：`scope.expansion_condition`（`scope.py:296`）用「新条目与旧条目可证不相交」判扩张，`src/a.py`→`src/**` 二者不 disjoint ⇒ 返回 `within-previous`（实测路径：`provably_disjoint("src/**","src/a.py")=False`；`subsumes("src/**","src/a.py")=False`，方向判据本可正确）。②漏判：`tasks._complexity_proposal`（`tasks.py:1648`）③只比验收 **id 集合**；同 id 改判据文本不变。③误升：`scope.contract_surface_condition`（`scope.py:265`）对 `AGENTS.md` 只判"路径命中 + 文件里有 `TRELLIS:START`"，块外文字改动也算契约面。 |
| 5 | TDD 红绿可拼凑、且缺文档/调查适用性分支（a.5） | **真实·P1** | `check.tdd_evidence_problem`（`check.py:1075`）只要求「红引用历史失败、绿引用本次通过、两引用串不同」，不要求两者属同一 `verification_id`；用例 `r17r24_tests.py` 的 R22 正例即以 `v1`（文件内容不是 ok 则退出 1）为红、`v2`（`print(2)`）为绿。`task-flow.md`「task.tdd-verified」已承诺「文档类对象以已批准的适用性与独立可观察验证代替」，但 `check.py:1274-1281` 与 `gates.py:782` 都没有任何适用性分支。 |
| 6 | 纯调查任务被首轮 Check 前置卡住（a.6） | **真实·P1** | `tasks.work_satisfied_fact`（`tasks.py:1039`）零触碰面要求「已有复盘 / 非空 curation / 历史 check pass」，出口写「先通过 Check」；而 `cmd_task_check` 先跑 `gates.evaluate(before_check)`（含 `task.work-satisfied`）⇒ 循环。仅交一份根因结论、无可沉淀 spec 的调查任务无法进 Check。 |
| 7 | 准备授权顺序与实现不符（a.7） | **真实·P1** | `runs.prepare`（`runs.py:800` 区段）直接写 `authorization={"source":"human","at":…,"session_key":…}`，无任何授权输入；`create` 的 `_preparation_problems`（`runs.py:1000` 区段）只核 session_key/范围/digest/validation，不核授权。设计稿 §5.7 要求「先取得限定路径的准备权限再起草」，而 skill 现文本让 AI 先写文件再 prepare。 |
| 8 | `gate --due after_archive` help 与实现不一致（b.1） | **真实·P1** | `cli.py` 的 `COMMAND_HELP["gate"].args` 允许四值；`cmd_gate` 只接受三值。`gates.DUE_ORDER` 与 `TASK_STEP_SPECS` 都有 `after_archive`（`task.archived`），实现侧只差入口白名单。 |
| 9 | 快照读取顺序/缺失处理（b.2） | **真实·P1** | `run terminate` 在逐任务处置（④）**之后**再 `open(...definition.md)`（`runs.py:2292`）解析未执行步骤；`run finish`（`runs.py:1891`）与 `_terminate_preview`（`runs.py:2058`）直接 `open`，快照缺失抛裸 `FileNotFoundError`（非框架原因码）；`advance` 已有正确形态（`runs.py:1483-1493` 判 `os.path.isfile` + digest）。 |
| 10 | 参数解析把未注册 flag 吞成值（b.3） | **真实·P1** | `validate_usage` 在值是 `--x` 且 `x not in allowed` 时只 `index += 1` 当值消费（`cli.py:4265` 区段），随后可能以「未知任务/路径非法」等下游误导码失败；该分支与「入口对不成立的输入不再沉默」的既有口径矛盾。 |
| 11 | 人判答复按子串匹配步骤 id（b.4） | **真实·P1** | `runs._human_answer`（`runs.py:1425`）用 `step["id"] not in text`；定义同时有 `api`/`api-docs` 时答复互串。同类可优化但风险不成立：`run resume` 的 `paused_reason.at` 匹配是时间戳，无前缀碰撞。 |
| 12 | 并发 `review-context` 假失败（b.5） | **真实·P2** | `_publish_materials`（`review.py:3179`）对「目录非空」直接报 `WF_PATH_INVALID`；两位 reviewer 同时取材料时后到者路径为「锁外读到 unmaterialized → 发布时已非空」。材料物化本身幂等（同轮 manifest 相同），应复用而非报错。 |
| 13 | register-only 与正式判定的复核保留规则两套（b.6） | **真实·P1** | register-only 分支（`review.py:4975` 区段）对缺 finding/降级一律拒；正式判定分支（`review.py:5352` 区段）在 `dispositions` 有 accepted 时放行。同一意图两套判据。 |
| 14 | `projection._adjudicated` 前缀匹配（b.7） | **真实·P2** | `projection.py:92` 用 `str(entry.get("commit","")).startswith(sha[:7])`：短前缀在长串上永远不匹配（记录短、查询长时失效），且 7 位前缀可误命中另一提交。 |
| 15 | sid 型身份只凭字段判存活（b.8） | **真实·P1** | `session.state_of_root`（`session.py:420`）`kind=="sid"` 时 `sid_start is not None → ALIVE`，不查 `/proc`；`state_of_l1`（`session.py:396`）已有正确形态（stat + state Z + start 比对 + 读不到→UNVERIFIED）。该值被 `identity_store.maintain_roots`/`boundary_alive` 消费 ⇒ 同 boot 内死亡会话被判存活，可能永久占住写权/触发 C2 阻断。 |
| 16 | 死代码与 docstring 谎言（b.9） | **真实·P3** | `review.py:1998` `if True:`；`runs.py:1318` `... and False`；`runs._next_step` docstring 说「`step_results` 已有结果的跳过」而实现只取游标下一格，且 `creation` 形参未用；`scope.vendor_assets` 重复 `task_id/installed` 赋值与注释；`check.run_check` 无生产调用方；`judgments.py` 重复导入 `review`。 |
| 17 | 异常归档后实例层无出口（a.2 附带） | **真实·P1** | `runs.advance` 对「步骤任务异常归档」给 `next_="按机制稿 §6.4/§7.4 处置该任务后重试"`（`runs.py:1538`）；但该任务已归档，`task-abandon` 对已归档对象无合法入口，重跑 advance 仍报同错 ⇒ 指向不存在的动作。实例层合法动作只有 `run terminate`（§7.4/§5.9）或替换。 |
| 18 | `run pause` 回显与实现矛盾（a.3 场景） | **真实·P2** | `runs.pause` 回显 `next_="解除路径未定义…当前出口是 run terminate"`（`runs.py:1823`），docstring 同；而 `run resume` 已实现（`runs.py:2379`），`finish` 也按「paused 先 resume」引导（`runs.py:1888`）。 |
| 19 | §1.1 表述：默认规则缺「已授权调查/可逆准备」分界（a/b 三节） | **真实·文档** | §1.1「默认规则」只写「在已批准的目标与范围内」，未写批准前调查/准备的合法性与边界；与 §1.2「作决定与转录」、§4.2 的规划起草链不闭合。 |
| 20 | §1.1 人签封闭清单不完整（a 三节） | **真实·文档** | 清单缺 §4.2 基线/项目配置提案、`task-replan` 的 `choice=replan`、§5.7 的工作流定义准备授权与实例创建授权；这些入口确实消费人的语义输入（`cmd_baseline_apply`、`_mechanical/replan` 分支、`run create` 的 creation 文件）。 |
| 21 | 指令分工在「命令用法面」有三个描述源（b 五-1） | **真实·结构** | `wf help`（`COMMAND_HELP`）、`states.json`/`next_by_position`、`wf-continue` 路由表都在描述「下一步怎么调」；第 8 条漂移即其结果。设计对「机制论述」有唯一定位纪律，对「入口用法」没有等价护栏。 |
| 22 | 发行 skills 与用户可见文案指向 authoring 文档（b 五-2） | **真实·文档** | skills 正文 13 处（`wf-code-review:41`、`wf-continue:96/157`、`wf-diagnosing-bugs:11/36`、`wf-grilling:37`、`wf-review-action:68/130`、`wf-review:14`、`wf-spec-update:26`、`wf-start:37/82`、`wf-tdd:34`）；用户可见出口 5 处（`check.py:1131`、`gates.py:803`、`gates.py:1136`、`runs.py:1538`、`tasks.py:4614`）。目标项目只有 `.wf/workflows/` 流程文档，`wf-framework-design.md`/`机制稿` 不可达。 |
| 23 | `run create` 缺 creation 骨架（b 二-2.3） | **真实·P3** | `definition validate` 已在 facts 给 `digest`（`runs.py:772` 区段），但 creation 文件四字段仍要手抄；其余 15+ 入口都有 `--draft`。 |
| 24 | 轻量模式收尾摩擦、跨任务插单、外发接收边界、`review.decide` 体量（a 场景表、b 二/三） | **误判为「本轮缺陷」/设计候选** | 轻量与插单是 §8.2 明确挂观察程序的**已知成本**，改它等于改承诺（charter T4）；外发「接收边界」在机制里无客观可观测事实（reviewer 进程是否上传内容不可观测），只能改由人声明的契约——属需人裁的设计问题；`review.decide` ~890 行是维护性风险，不是行为缺陷，重构超出本轮且无行为收益。 |
| 25 | 报告 b 声称「没有结构性欠账」 | **部分误判** | 第 1 条即结构性欠账：实例内任务的写入口从设计（§5.8）到实现断层，`bind_task_for_write` 存在但未被日常入口接入。报告 b 只核了「机制/指引分工」，没核「机制之间是否接上」。 |

## 3. 修正设计（按簇）

### F1 任务写入口归属解析唯一化（对应 D1）

- **唯一实现**：`tasks.write_scope(task_id)`，返回 `("task", None)` 或 `("run", run_id)`。判据依次：
  1. 会话绑定：`binding.object.kind=="task" and id==task_id` ⇒ 任务面；`kind=="run"` ⇒ 候选实例面；否则 `WF_BINDING_MISMATCH`（保留既有 `_require_instance_match` 核验）。
  2. 实例面：任务记录 `run_id == binding.object.id`，实例记录存在、未终态，且 `run.cursor.task_id == task_id`；任一不符给对应事实（`cursor`、`terminal`、`run_id`）与出口「换任务先 run advance / 实例已结束按 §5.9 处置」。
- **写权核验**：`tasks.require_held_for(ctx, task_id)` 在锁内调用 `ctx.require_held()`（不指定 target，先核身份与代次），再按 holder scope 复核：task scope 必须就是该任务；run scope 必须满足上条第 2 项。返回 `(record, holder, scope_kind, run_id)`。
- **接入面**：把 17 处「`_require_binding` + `require_held(task=task_id)`」改为「锁外 `write_scope` 快检（保留原有提前报错位置）+ 锁内 `require_held_for`」。`bind_task_for_write`（决策类入口）改为 `write_scope` + `require_held()` 的组合，一处实现两种消费。`stop_work` 保持拒绝实例面，但出口改为「实例内任务用 `task-pause`，实例用 `run pause`/`run terminate`」。
- **归档语义**：`_release_after_archive` 在 run scope 下**不释放**写权，回 `{"released": True, "kept": "run"}` 并给 facts；`archive` 的 `next_` 依 scope 分叉：任务面「下一对象需在新会话选择」，实例面「回到实例：`run advance` 记 satisfied」。
- **取舍**：不改 writer 记录结构（holder scope 已是 run），不改 binding 结构（实例绑定仍指 run），因此不需要数据迁移；旧实例记录天然适用。风险点是「同一任务同时被 task 绑定与 run 绑定」——`write_scope` 以 binding 为唯一入口，不出现双绑（`session.bind` 保证单绑定）。

### F2 游标推进按步骤事实（对应 D2、D17）

- `runs.advance` ①段改为**按步骤类型与已落盘结果**推进：
  - `task_map[step].task_id` 存在 ⇒ 沿用现有「未归档则等、正常归档则 satisfied」；
  - 无映射：`step_results[step].kind ∈ {satisfied, skipped}` ⇒ 记 `settled=step` 并继续；`step` 是 task 类型且无结果 ⇒ 仍报 `WF_HISTORY_UNRESOLVED`（这是真损坏，不是合法中间态）。
- 异常归档出口改为实例层动作：`next_="该步骤任务已异常归档：实例不再推进本步骤；按 §7.4 用 run terminate 逐任务处置（放弃/保留），或由人裁定替换后重建"`，并给 `facts.exits` 列表。
- `_next_step` 改为真正的「下一个无结果步骤」：跳过 `step_results` 已有记录的 id（含略过），删除未用的 `creation` 形参，docstring 与实现对齐。这一改动同时使「返工返回定位后重入」不必依赖游标刚好停在原步。

### F3 Check 定稿合并（对应 D3）

- ③段锁内**重读** `task.json`，并对准备段的内存态做**身份二等分**：
  - `_apply_debug_inputs` 在重读后重放（输入来自 decisions，确定性）；
  - 比对 `identity = (status, phase, paused, suspended, normalized_plan_version, entry_snapshot_digest, acceptance_digest, check.id 上一版)`；
  - 与准备段取值不一致 ⇒ `WF_CHECK_STALE`（facts 给前后值与出口：「按当前状态重新 Check / 先解除暂停」）。
- 一致 ⇒ 用重读记录回写 check（不覆盖新写入的暂停/挂起/阶段字段）。
- **取舍**：新增一次读文件（毫秒级）换取「锁外窗口不会被内存态覆盖」；保留原有「锚点重算 + 内容扫描比对」两道判据。

### F4 复杂度条件事实化（对应 D4）

- `expansion_condition`：改判据为「存在新条目不被任一旧条目可证包含」即 `subsumes(touch, old)`（`paths.subsumes` 已有唯一实现），否则 `within-previous`；facts 附 `covering` 旧条目。
- `acceptance` 条件：新增**验收口径摘要**比较——`fingerprint.acceptance_digest(block["acceptance"])`（已有唯一实现，`tasks.py:2085` 已在批准时存 `plan.acceptance_digest`）与上一版不同即 `acceptance-changed`，并在 facts 里同时给 id 集合差异与摘要差异；首次批准无上一版时按现有路径面判定。
- `contract_surface_condition` 的 `AGENTS.md` 分支：改为**托管块内容比较**——从 `git.show HEAD:AGENTS.md`（无 HEAD/文件不在库内 ⇒ 保守判 true）与当前文件分别截取 `TRELLIS:START`…`TRELLIS:END` 之间文本，块内容不变 ⇒ 返回 `false` 并给 `fact="agents-outside-block"`（路径命中仍需在 facts 里明列，供 AI 判断）。块内容变了或一端缺失 ⇒ `true`。
- **取舍**：三项都是「可证事实 + 可执行出口」，语义判断（改动是否实质改变契约）仍留给 AI/人的批准决定；不新增门禁，只改条件的准确性。

### F5 TDD 证据身份与适用性（对应 D5）

- `tdd_evidence_problem` 增加身份核验：由 `green_command_ref` 定位本次命令条目，取其 `verification_id`；红运行必须存在**同 `verification_id`** 的历史失败命令（`history_commands` 现按 `verification_id`/`evidence_ref` 双向索引，已足够）；跨验证项拼凑 ⇒ `{"reason": "red and green must cover the same verification", ...}`。
- 适用性分支（接上 `task-flow.md` 已承诺的口径）：plan 机读块新增可选字段 `tdd_applicability ∈ {"code","docs","investigation"}`（默认 `code`，进 `plan_block` ⇒ 进 `plan_version`，即由人的批准绑定）。取值 `docs|investigation` 时：
  - 不要求红绿五段；改为要求该对象的每条验收项都有可消费证据（命令通过或人判决定，`_acceptance_results` 已判）；
  - `check` 记录 `tdd_applicability` 与 `tdd_evidence=null`，门禁 `task.tdd-verified` 按批准声明放行并在 facts 里给「适用性=docs，按独立可观察验证」；取值 `code` 时行为不变；
  - `--draft` 与 `task-approve` 的事实里回显该字段，避免人盲签。
- **取舍**：这是机制核**形制**（声明是批准对象的一部分）+ AI 判语义（这个对象算不算文档类）的正确分工；不新增门禁，只把已承诺的适用性做成可核声明。

### F6 纯调查出口（对应 D6）

- `work_satisfied_fact` 零触碰面分支：已批准规划声明了非空 `acceptance` ⇒ 返回 `(True, None, {"mode":"investigation","acceptance_ids":[…]})`；无验收项 ⇒ `WF_CHECK_FAILED` + 出口「回 Plan 补验收项并重新批准」。移除「先通过 Check」的自循环出口；保留复盘/curation 事实作为附加信息（不替代验收项）。
- 语义仍由 Check 的验收结论与双轴审查承担——机制只保证「可进入 Check」。

### F7 定义准备授权（对应 D7）

- `definition prepare` 新增 `--authorization <decision>`（`--authorization-draft` 只读骨架）：决定必须 `choice ∈ {"准备定义","prepare_definition"}`（登记进 `decisions` 域）、`scope_paths` 覆盖本次定义路径、六键齐全（沿用 `_load_decision` 的 TODO/字段校验）。
- 准备记录 `authorization = {"source":"decision","by","at","quote_digest","scope_paths":[…],"scope_digest":H(...)}`；不再写 `source="human"`。
- 幂等：同一 `workflow_id` + 同一 `scope_paths` 的既有授权可复用（第二次 prepare 只更新校验结果与代次，不要求重复签）；范围变化必须新授权。
- `_preparation_problems` 增加「authorization 存在且范围覆盖」一条；`create` 因此核到可核授权。skill 顺序改为「人授权准备范围 → prepare（可先无草稿）→ 起草 → prepare 复跑校验 → run create」。

### F8 快照单读（对应 D9）

- `run finish`/`_terminate_preview`/`terminate` 统一走 `runs._fixed_snapshot(ctx, run)`：存在性 + digest 复核 + 解析一次，失败给 `WF_HISTORY_UNRESOLVED`（与 `advance` 同口径）；`terminate` 在**任何业务写入之前**取 `doc` 并复用（不再在④之后重读）。
- **取舍**：快照内容在实例生命周期内不可变（digest 绑定），单读与重读等价，单读消除「写入后才发现快照缺失」的半写状态。

### F9 参数/匹配/身份小修（对应 D8、D10、D11、D14、D15）

- `cmd_gate` 接受 `after_archive`（与 `DUE_ORDER` 一致）。
- `validate_usage`：值位后紧跟 `--x` 且 `x ∉ allowed` ⇒ 直接报 `unknown flag`（带近似提示），不再吞成值；合法值以 `--flag=value` 传入。
- `_human_answer`：步骤 id 按整词匹配（`(?<![A-Za-z0-9_-])<id>(?![A-Za-z0-9_-])`），沿用 `plan-q` 已有的整词口径。
- `projection._adjudicated`：比对完整提交号（记录值即 `task-attribute --commit` 的输入；短号在记录时 `git rev-parse --verify` 归一为全长，读时精确相等）。
- `session.state_of_root` sid 分支：改为复用 `state_of_l1` 的同一套 stat/Z/start 判定（把「读不到」保留为 `UNVERIFIED`，不折成 ALIVE）。

### F10 review 侧一致性（对应 D12、D13）

- `_publish_materials`：目标目录非空时，若其 manifest 与本轮 staging 的身份一致 ⇒ 删除 staging 并**复用**既有材料（返回同一 facts，标 `reused: true`）；不一致 ⇒ 仍报 `WF_PATH_INVALID`（真冲突）。
- 复核保留规则抽成 `_main_review_revision_problems(previous, current, resolved_accepted)`，register-only 与正式判定两处共同消费；register-only 额外保留「不得在 pass/unavailable 后改写」的既有判据。

### F11 死代码清理（对应 D16）

- 删除 `if True:` 包裹、`and False` 分支、`scope.vendor_assets` 重复赋值与重复注释、`judgments.py` 重复导入；删除无调用方的 `check.run_check`（docstring 声称的兼容入口无消费者，保留即第二个「三段顺序」实现）；`_next_step` 按 F2 修改。清理只删不增，不改变判定。

### F12 出口、指引与文档同步（对应 D18、D19、D20、D21、D22）

- `runs.pause` 回显与 docstring：指向 `run resume`（解除实例暂停）与 `task-resume`（是否恢复任务）两件事，`run terminate` 作异常出口。
- 用户可见文案的 5 处 authoring 引用改为可达出口（`wf help <命令>` / `.wf/workflows/task-flow.md` 的对应小节）。
- 发行 skills 13 处 authoring 指针：改为目标项目可达的定位（`wf help`、流程文档小节）或删除括号引用；「基线」行保留摘要与口径，去掉不可达章节号。
- 设计稿 §1.1 三处更新（默认规则、人签清单、指令分工的「入口用法单一来源」纪律），并在 `wf-continue` 路由表加一句「命令形态以 `wf help` 为准」（不复制字段清单）。
- `run create` 增 `--creation-draft --id <workflow-id>`：从 `definition validate` 同一事实源生成 `{definition_id, definition_digest, inputs, steps}` 骨架（只打印，不落盘），`wf-start` 的「定义与实例」节改用它。

## 4. 不新增层级/不新增 skill 的核对

- 全部改动落在既有模块（`tasks/runs/check/scope/session/projection/review/authorize/cli`）与既有 skill 正文的判据位；新增字段仅 `plan.tdd_applicability`（进批准对象）与准备记录的 `authorization.*`（替换自报值），新增入口仅 `prepare --authorization[-draft]`、`run create --creation-draft`，均属既有命令的参数面。
- 判据自检（§1.1）：每条机制化项都能说出消费点——F1→日常写入口可达与实例不被打断；F2→合法中间态不误判为损坏；F3→暂停不被覆盖；F4→分级提议准确；F5→红绿覆盖同一行为、文档类不被迫造假；F6→调查任务可交付；F7→授权可核；F8→无半写；F9→入口不再误导；F10→复核规则单一；F11→无第二实现。
- 语义判断保留原位：扩面是否实质、红绿是否同一行为、调查结论是否成立、审查结论与残余风险，全部仍在 skill 判据位或人签。

## 5. 不在本轮（含原因与去向）

| 项 | 原因 | 去向 |
|---|---|---|
| 轻量模式收尾摩擦（a 场景 1） | §8.2 明确挂观察程序；改它等于改承诺（charter T4） | 保留为 §8.2 观察项，需真实切换耗时数据后由人裁 |
| 跨任务插单的 WIP 限制（a 场景 2） | 「共享工作区串行写入」是 charter 边界，不是实现缺陷；预览文案已给去向要求 | 观察项；若人要求，另开任务改 stop 预览首屏措辞 |
| 外发授权绑定「接收边界」（a 场景 4） | reviewer 进程是否上传内容**机器不可观测**，只能改由人声明的契约 ⇒ 属授权边界变更，需人裁 | 待裁项：若人裁「接收者集合进摘要」，另开任务实现 `export_scope` 扩展 |
| 步骤 `actions` 与任务记录的接缝（八轮审查 b-2） | 定义里的步骤 `actions` 是"该做什么"的声明，Check 侧已有待做动作核对，但实例建任务时没有把声明写进任务记录 `execution.actions` | 本轮只补了**可核事实**：产物 `exists` 与"上游产物缺失不建下游任务"。剩余是把 actions/inputs 绑定写进任务记录并让 Check 消费（属记录 schema 变更，需单独立项） |
| TDD 红证据的运行身份（八轮审查 c-2） | 现在只能拿整轮 Check 的失败当红证据；单次验证运行没有记录入口 | 需新增"一次验证运行"的记录形态并被 `tdd_evidence_problem` 消费（改动 TDD 证据链，单独立项） |
| 异步/长时验证的承载（a 报告第五节） | 验证命令=触发远端流水线时，"命令结束"≠"验证结束" | 属格式能力缺口（charter T3 三问），先登记不实现 |
| 准备通道「持有写权」 | 三轮审查指出准备期编辑与其他写入并发 | **已按写者模型实现**：`definition prepare` 取得 `scope.object=preparation` 的准备写权（写者记录里早有 `preparation` 槽），`prepare --end` 处置未提交编辑后释放，`run create` 作为天然收口自动释放；已结束的记录仍可用于创建。代价：未处置的定义编辑不能直接结束准备（`WF_WORKSPACE_UNRESOLVED`），需先提交或给逐路径去向 |
| `review.decide` 体量/三处出口瀑布（b 4.3） | 维护性重构，无行为收益且风险高于收益 | 记入 `analysis/round-history.md` 的观察，不在本轮动 |
| `run create` 的 creation 语义（人确认版本/输入/展开） | 现行 creation 文件即「人的选择」的转录，符合 §1.2；只补骨架 | 本轮只加 `--creation-draft` |

## 6. 风险与回退

- 风险 1（F1）：写入口放宽后误放行非本实例任务。缓解：`write_scope` 只有一个实现，且对 run 面强制三条件（run_id、未终态、cursor 指向）；新增负例用例（错任务/游标不指向/实例已终态/他人持权）。
- 风险 2（F3）：重读后 `_apply_debug_inputs` 重放差异导致 debug 声明丢失。缓解：重放后再做身份比对；用例覆盖「带调试声明的 Check + 期间暂停」两条路径。
- 风险 3（F4）：`subsumes` 对通配写法处理不当导致误判扩面/漏判。缓解：以 `paths` 现有单测 + 新用例覆盖 `a.py→**`、`**→a.py`、`src/*→src/**` 三组。
- 风险 4（F5）：`plan.tdd_applicability` 使既有 PRD 块的 `plan_version` 变化。缓解：字段可选、缺省 `code` 且不参与哈希以外的判定；旧任务重算版本时缺省值与批准时一致（缺省即默认文档语义），不影响既有批准。
- 回退：全部改动在单个提交面内（人同意后才提交），按簇可独立回退；每簇有用例，回退不牵动其他簇。