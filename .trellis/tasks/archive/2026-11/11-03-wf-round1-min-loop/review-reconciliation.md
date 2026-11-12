# 首轮实现外部评审的复核与修正

- 复核对象：外部评审报告「二、较重要的发现 F1–F12 / 三、次要发现 N1–N12 / 五、改进建议」
- 复核方法：逐条对照**源树代码**（`docs/workflows/新项目开发工作流/payload/**`，与已打包发行树字节一致）与四份契约（charter、设计稿、机制稿、实现稿）；没有引用的论断不采信
- 判定口径：**成立** / **部分成立（需改写）** / **不成立**；处置归属：**首轮收口前修** / **登记为未运行或延后（注明轮次）** / **需人裁决**
- 本次复核只改文档（本文件 + 任务记录 `validation.md` 的登记节），**未改代码、未改发行树、未改四份契约**

## 0. 复核结论摘要

| 类别 | 条数 | 说明 |
|---|---|---|
| 成立 | 21 | F2/F3/F5/F7/F8/F9/F10/F11/F12；N1–N12 全部（N8 另属需人裁） |
| 部分成立（含需改写的子论断） | 3 | F1（缺口成立、可达性判断不成立）、F4（矛盾成立、死代码判断不成立）、F6（提交范围成立、顺序判断不成立） |
| 不成立 | 3 条子论断 | F4「未闭合不报」、F6「提交顺序与 §5.3 不符」、F1「首轮 task-abandon 可造成」 |
| 原报告事实性混淆 | 1 | 把 F1 夹具的 spec 生命周期 13/13 记成「V1」 |
| 处置：首轮收口前必修 | A1–A23（23 项） | 22 项实现件（门禁/核验/接线/工具/模板）+ 1 项记录补登（A20） |
| 处置：登记未运行/延后 | 4 项 | N1、N4 的 transfer/reverse、N5 的持久化查证、N10 |
| 处置：需人裁决 | 2 项 | N8 令牌范围；F6 归档顺序（结论倾向不改） |

**对首轮验收的直接影响**：F12 成立 ⇒ 按机制稿 §12.3「缺正反样本该夹具不算完成」，**F2 夹具未完成、P5 未收口**；F2/F3/F11 属「已交付但未接线且未登记」⇒ 违反 P5 判据「未运行必须写原因分类」。三项均已在 `validation.md` 新增的登记节逐条补记（见 §6）。

---

## 1. 逐条判读（保留原编号以便对照）

| # | 原判 | 复核 | 修正要点 | 处置 |
|---|---|---|---|---|
| F1 | 最终门禁不核前置依赖 | 部分成立 | 门禁确实不核（`gates.py:525` 是空分支）；但**首轮无法产生前置**：`dep`/`task-rework`/`task-replace` 均返回 `WF_CAPABILITY_UNAVAILABLE`，`prerequisites` 恒为空，故「task-abandon 可造成」不成立。属**真实缺口 + 当前不可达** | 首轮修（成本 6 行）+ 用手工构造记录验证 |
| F2 | equivalences 只有字段无消费 | 成立 | `tasks.py:143` 初始化后再无引用；`compute_plan_version`/`verify_step`/`compute_P` 均不归一 | 首轮修 |
| F3 | activation 核验缺失、`WF_NOT_ENABLED` 零消费 | 成立 | `WF_NOT_ENABLED` 仅存在于 `codes.py`；`cli.activation()` 只在 `enable` 的 facts 里出现 | 首轮修 |
| F4 | frontmatter 解析器与模板不兼容 | 部分成立 | 矛盾成立：模板 `templates/spec/rule.md` 写裸词 `status: template`、`author: ai`，解析器要求 JSON 值 ⇒ `problems` 恒非空 ⇒ `spec.match` 判不可路由。**但「`problems.append("frontmatter not closed")` 是死代码、未闭合反而不报」不成立**：该行在 `for` 循环之后，未闭合时正常返回该 problem（`spec.py:24-53`） | 首轮修（改模板，不改解析器） |
| F5 | 开工把 fresh satisfied 写成 `reused` | 成立 | `tasks.py:927-931`：`reused_from={"completed_at": None}` ⇒ 产生 `result=reused`、`completed_at=null`、`skip_basis.completed_ref=null` 的非法回执 | 首轮修 |
| F6 | 归档顺序与提交范围 | 部分成立 | **顺序论断不成立**：设计稿 §4.2「业务/spec/基线/配置变更……提交，**随后**核对最终门禁，归档记录最后单独成组」明确要求业务提交先于门禁；机制稿 §5.3 的步骤表约束的是**归档动作自身**（记录组）的顺序。实现与设计稿一致。**成立的是**：`_commit_paths`（`tasks.py:1371`）用 `git commit -m` 提交**整个索引**，预暂存的无关改动会被捎带；不核对暂存集合与授权组一致；`grant.subject` 用逗号拆分路径（含逗号的路径直接坏） | 顺序不改（交人确认）；提交范围首轮修 |
| F7 | attempt 额度管理失效 | 成立 | `review.py:116` 每次 launch 都 `len(attempts)+1`。**本轮 V4 实跑即证据**：同一实施尝试的 round 1/2 被记成 `attempts=[1,2]`（`round_ids` 分别为 `[1]`、`[2]`） | 首轮修 |
| F8 | 默认卸载不核本地偏离 | 成立 | `uninstall.py:269-281` 按清单逐个 `os.remove`，`expected` 只记录不参与判断，预览不列偏离 | 首轮修（预览列偏离 + 需明确决定才删改过的资产） |
| F9 | 执行器解析三处偏离 | 成立 | ① 全局键不校验绝对路径（`bin/wf.py:166`；`config.py::load_global_config` 的校验在运行路径上不被使用）；② 项目键 `..` 越界不拒（`:348` 只 join+realpath）；③ 项目配置 JSON 损坏 → `{"__invalid__": True}` → `.get()` 得 None → **静默回退**全局/系统；④ `confirm-executor --scope project` 不核 Git 侧批准键名/值 | 首轮修 |
| F10 | check.py 三处弱化 | 成立 | ① `_acceptance_results`/`_manual_command` 收 `anchor` 不用（`check.py:215`、`:359`），且**任何未枚举的 `choice` 都被记成 `passed`**（`:247`），偏差比原报告更严重；② 无开始/结束两次扫描比对；③ `consume_at=finish` 在 `cmd_archive` 无 `verification.resolve(finish)` | 首轮修 |
| F11 | `debug_repeat_threshold` 未接线 | 成立 | `gates.py:79` 硬编码 3，不读项目配置 | 首轮修 |
| F12 | 验证记录与夹具绑定缺口 | 成立 | `validation.md` 的 F2 段只有 V4；Trellis 两分支、共存与外部提交分支未跑也未登记 | 首轮修（补跑或补登记；本次已在 `validation.md` 补登记） |
| N1 | 三个配置键零消费 + `inspect` 弱化 | 成立 | `spec_verify_days`/`spec_reclaim_tasks`/`inspection_every_tasks` 未消费；`inspect` 仅四类弱断言 | 登记为未运行（第二轮/巡检轮），见 §4 |
| N2 | Trellis 互斥比契约更严 | 成立 | `cli.py:470-521`：任何 `TRELLIS:START` 一律 `WF_FLOW_CONFLICT`，缺「适用性未知 → needs_decision」档；含本仓库自身（AGENTS.md 有托管块） | 首轮修 |
| N3 | handover.begin 不核已存进度/暂停/WIP | 成立 | `cli.py:766-787` 只核 held，begin 后任务可仍 `in_progress` | 首轮修（S） |
| N4 | stop 三分支与 commit 授权判定过弱 | 成立 | keep 不核同对象范围；transfer 不核具名承接；reverse 不核实际完成；commit 只数 decision 条数 | 首轮修 keep/commit；transfer/reverse 承接核验延后（依赖建边轮） |
| N5 | abandon 无预览、异常归档无持久化查证 | 成立 | `tasks.py:1299-1353` 直接写终态并移动；`task.archived` 只判 `terminal==normal` | 首轮修预览面；持久化查证延后 |
| N6 | 两份 `compute_rules_digest` 排序键不一致 | 成立 | `assets.py:61` 按 UTF-8 字节序；`install.py:59` 按 str 序（ASCII 下等价） | 首轮修（两处统一 UTF-8 字节序） |
| N7 | install 自检是字符串包含；`gates.HANDLERS` 不存在 | 成立 | `install.py:292-305`；全仓无 `HANDLERS` | 首轮修（补 id→处理器表，自检双向核对） |
| N8 | `repair --dispose` 无令牌 | 成立 | `repair.py:233-238`；机制稿 §10.3 的令牌覆盖「repair」 | **已裁定（2026-11-03）：纳入令牌**，实现与实测见 `validation.md` §17 |
| N9 | plan-q 覆盖只在 approve 核 | 成立 | `gates.py:360` 调 `unanswered_plan_questions(task)`，`_questions` 只由 `_attach_questions`（`tasks.py:669`）在 approve 注入 ⇒ gate/start 恒为空 | 首轮修 |
| N10 | `_enumerate_tree` 排除 `.wf` 等前缀 | 成立 | `scope.py:189-196`；只会保守取 complex，不会放行 | 登记（不修） |
| N11 | `cmd_spec` 非 JSON 模式双份输出 | 成立 | `cli.py` 先写正文再 `emit(render)` | 首轮修 |
| N12 | 降级复核缺链 | 成立 | `gates.py:387-397`：light 直接返回 True，不核 `complexity_reasons` 的降级条目 | 首轮修 |

---

## 2. 不成立或需改写的论断（避免把错误结论带进修复清单）

1. **F4「未闭合 frontmatter 反而不报」——不成立。** `spec.py` 的 `problems.append("frontmatter not closed")` 位于 `for` 之后，未闭合时执行；`return` 只在遇到结尾 `---` 时提前返回。正确结论是「解析器与模板不一致」，不是「闭合检测缺失」。
2. **F6「提交发生在 final_gate 之前与机制稿 §5.3 不符」——不成立。** 设计稿 §4.2 的提交顺序为「业务组提交 → 最终门禁 → 归档记录单独成组」；机制稿 §5.3 的固定步骤是归档动作自身（终态/移动/记录组提交）的顺序。实现与上位一致。若坚持按 §5.3 字面重排，会造成「门禁失败也先提交业务」的更差结果，属需人裁决而非实现缺陷。
3. **F1「首轮 task-abandon 可造成」——不成立。** 首轮没有建边/返工入口（`dep`、`task-rework` 均 blocked），`prerequisites` 恒空；缺口真实但不可达，因此它是「前瞻缺口」而非「已验证逃逸」。
4. **原报告把「F1 夹具 spec 生命周期 13/13」写成「V1 spec 生命周期」——事实混淆。** V1 是会话身份与绑定（11/11）；spec 生命周期属 F1 夹具的专属场景（13/13）。
5. **F10① 的成因描述需要改写。** 原报告说「写个 decision 文件即可让 manual 验证通过」——结论成立，但成因更严重：`_acceptance_results` 对空 `verification_ids` 的验收项接受**任意** `choice`（未命中 `passed/failed/pending` 即记为 `passed`，`check.py:247`），`_manual_command` 只判 `verification_id` 是否出现在 `subject` 里；机制稿 §3.5 要求的「Decision 绑定该 acceptance_id、`plan.version` 与当前 `check.anchor`」完全没有实现。因此修复不是「加一个枚举判断」，而是补齐锚点绑定（A10）。

---

## 3. 首轮收口前必修（A 类）

排序按「先结构核验、后接线、再一致性」，对应 charter T6.3；全部不涉及二/三轮能力。

| 序 | 项 | 位置 | 处置 | 验收判据 |
|---|---|---|---|---|
| A1 | 前置依赖核验 | `gates.py:525` | 抽 `tasks.dependency_blockers()`：前置须正常归档且归档持久化可核；开工与归档门禁共用 | 构造带前置的任务记录：前置异常归档 → 开工与归档均 `WF_DEPENDENCY_UNMET` |
| A2 | equivalences 归一 | `tasks.py` plan 计算链 | 新增 `normalized_plan_version(task)`：沿 `equivalences` 回溯到 `approved_version`（链断/缺 Decision/成环即不归一）；`task-approve` 收到 `choice=机械修订` 时校验两端同义（`touch_paths` 集合相等 + 验收摘要相等）后接链，**且该分支不受 plan 阶段限制**（开工后修错字是常态）；`compute_plan_version` 比对、`compute_P` 的 `plan_version`、`check_anchor` 的 `plan_version` 一律走归一值 | PRD 只改错字 + 一条等价链 Decision → `task-start`/`task-check` 不重批、锚点不变；改验收或范围 → `WF_SEMANTIC_DECISION` 回 Plan |
| A3 | activation 核验 | `cli.py` 会话类入口 | `task-*`/`spec --file`/`writer`/`stop`/`review-*`/`archive`/`baseline-apply`/`spec-update` 在写前核 activation；缺失 → `WF_NOT_ENABLED`；纯只读（`status`/`gate`/`inspect`/`version`）不受限 | activation=null 时 `task-start` → `WF_NOT_ENABLED`（exit 1） |
| A4 | spec 模板与解析器一致 | `templates/spec/rule.md` | 模板值改为 JSON 字面（`"template"`/`"ai"`/`null`），解析器不动（机制稿 §8.3 是唯一定义） | 用模板生成的文件 `parse_frontmatter` 的 `problems` 为空，`spec.match` 可命中 |
| A5 | 回执类型 | `tasks.py:927-931` | 无既有回执的 satisfied 步骤写 `completed`（`completed_at`/`checked_at` 为本次、`evidence_refs` 记核验结果）；只有确有原 completed 时才写 `reused` 并填真实 `completed_ref` | 开工后 `required_steps` 中不存在 `result=reused ∧ skip_basis.completed_ref=null` 的条目 |
| A6 | 提交范围 | `tasks.py:1371` | 业务组与记录组分开提交；`git commit -m <msg> -- <paths>` 路径限定；授权可写 glob，提交前展开为精确路径；提交后回读 `git show --name-only` 并要求 ⊆ 授权集合；`subject` 接受数组或 `,;/换行` 分隔；非 ASCII 路径 `core.quotePath=false` | 预暂存无关文件 → 不入本次提交；授权组缺项 → `WF_COMMIT_NOT_AUTHORIZED`；残留差异 → `WF_PERSISTENCE_FAILED` |
| A7 | 审查 attempt | `review.py:116` | attempt 取当前实施尝试号（仅返工开启新尝试时 +1），round 只递增；同一尝试轮数达 2 即拒绝再发起 | round 2 落在 `attempts[0].round_ids=[1,2]`；第 3 轮 → `WF_SEMANTIC_DECISION` 并提示人发起返工 |
| A8 | 卸载偏离 | `uninstall.py:269-281` | 逐项比对发行摘要：偏离默认**保留**并列入预览与结果（不给用户新增开关，避免误删）；同目录未知文件只列不删；预览与确认在同一进程内完成 | 改过的 skill/项目资产不被删除且出现在报告里；未修改的资产正常移除 |
| A9 | 执行器解析 | `bin/wf.py:166,348` | 全局键强制绝对路径；项目键解析后必须仍在项目根内（越界 → `WF_PATH_INVALID`）；项目配置非法 JSON → 阻断（`WF_EXECUTOR_UNCONFIRMED` 并给出口），不回退；`confirm-executor --scope project` 核 Git 侧批准键名/值（在基线或已批准 PRD 中可查） | 三条反例各返回对应码且不静默回退；确认时缺批准记录 → 拒绝写入确认集合 |
| A10 | 检查锚点绑定 | `check.py:215,247,359` | `_acceptance_results` 用 `anchor`：空 `verification_ids` 的 Decision 必须 `subject` 含 acceptance_id、`choice ∈ {passed,failed,pending}` 且记录中补记 `plan.version` 与本次 `check_anchor`；`_manual_command` 同规则 | 缺 Decision → `pending`；choice 不在枚举 → 不通过；Decision 与当前锚点不符 → 不通过 |
| A11 | 扫描前后比对 | `check.py::run_check` | ②之前取一次对象路径+指纹，⑤写结果前再取一次；不一致 → 重取或 `WF_CHECK_STALE`（不写 pass） | 检查期间改交付 → 本次 Check 不判 pass |
| A12 | finish 时点解析 | `tasks.py::cmd_archive` | 改终态前对 `consume_at=finish` 与当前检查依赖的输入调 `verification.resolve(finish)`，不就绪 → `WF_VERIFICATION_UNREADY` / 回 Check | 构造 finish 项缺来源 → 归档被拒 |
| A13 | 阈值接线 | `gates.py:79,108` | `debug_pending` 由调用方传入项目配置 `debug_repeat_threshold`（读不到时用发行缺省并可见报告） | 配置 threshold=2 时累计 2 即产生待决项 |
| A14 | Trellis 档位 | `cli.py:470-521` | 分档：仅数据线索 → 通过并提示；当前宿主可适用的 hook/配置存在 → `WF_FLOW_CONFLICT`；托管指令块存在但宿主适用性未知 → `WF_SEMANTIC_DECISION`（exit 2），出口为「核实并清理后换新会话」或「确认仅残留」 | 带 `TRELLIS:START` 的项目 `enable` 返回 exit 2 而非硬阻断；仅 `.trellis/` 数据返回 pass |
| A15 | plan-q 覆盖 | `tasks.py`/`gates.py:360` | 问题提取改为纯函数 `plan_questions(root, task)`（不写记录、不产生临时键）；`evaluate` 一律先 `verify_step` 再采信回执，避免回执短路活事实 | 删掉一条 plan-q 答复后 `task-start` → `WF_SEMANTIC_DECISION` |
| A16 | 处理器表 | `gates.py` | 补 `HANDLERS`（task id → `verify_step`；control id → 承接子命令）与 `support_report()`；dev-deploy 在进程内、install 在部署后的运行时里双向核对「声明 ↔ 分派表 ↔ 命令面」，不再用字符串包含 | 删除任一处理器 → 自检失败；两处自检结论一致 |
| A17 | rules_digest 单源 | `assets.py:61`、`install.py:59` | 两处排序键统一为 `str.encode("utf-8")`；`build-wf-release.py` 加 `verify_rules_digest_parity()`，对同一清单比对两处实现 | 含非 ASCII `source_path` 时两处 digest 相同（已实测） |
| A18 | 降级复核 | `gates.py:387-397` | light 且 `plan.complexity_reasons` 含降级条目时核 `reason`/`evidence` 非空；complex 时核无降级条目 | 降级任务缺 evidence → 归档门禁阻断 |
| A19 | `cmd_spec` 输出 | `cli.py` | 非 JSON 模式只把正文写到 stdout，摘要（路径/摘要/字数/超预算）写 stderr；`--json` 仍返回完整结果结构 | stdout 只有正文；`--json` 结构完整 |
| A20 | 验证记录补登 | `validation.md` | 补 F2 缺失分支与三项未接线项的「未运行/部分交付 + 原因分类」 | 记录与本文 §6 一致 |
| A21 | 交接前置 | `cli.py:766-787` | `handover.begin` 前核「进度/暂停/WIP 处置已保存」：任务须 `paused` 或已有 `handoff.wip`，否则 `WF_SEMANTIC_DECISION` | begin 后任务不得仍为可推进的 `in_progress`；缺处置 → 拒绝 begin |
| A22 | 收工判定 | `tasks.py::stop_work` | `keep` 核路径均在当前批准触碰面且归属本任务；`commit` 的授权取 `decisions[1:]`（收工选择本身不算授权）并核其 `subject` 覆盖全部待提交路径；`transfer` 核承接任务存在；`reverse` 核路径已不差异 | 保留外来改动 → `WF_WORKSPACE_UNRESOLVED`；授权不全 → `WF_COMMIT_NOT_AUTHORIZED` |
| A23 | 放弃预览 | `tasks.py:1299-1353` | `task-abandon` 先输出预览（未提交改动、下游/未完返工引用、既有提交），预览项与处置项同名可比对；无处置决定不结案 | 缺预览直接结案 → 拒绝；预览项未覆盖实际未提交路径 → `WF_WORKSPACE_UNRESOLVED` |

> 除 A4（模板一致性，用模板自身判定）、A16/A17（工具自检，用构造清单）、A19（输出形态）、A20（记录）外，其余 A 项的验收都需要**新增用例**，不能只靠既有 V1–V5 回归；新增用例写入 `validation.md` 时须记版本与环境。

---

> **CP1 实跑补充（2026-11-03）**：A15/A22 的实跑另外暴露三处实现漏判——任务记录被写入临时键 `_prd_text`/`_questions`、收工把自身选择计作提交授权、门禁找到回执即跳过事实核验。三者已在同一批修正，记录见 `validation.md` §12.3，判据未变、不改机制稿。

## 4. 登记为未运行或延后（B 类）

| 项 | 归属轮次 | 登记理由与出口 |
|---|---|---|
| N1 核期（`spec_verify_days`）/ 回收（`spec_reclaim_tasks`）/ 巡检节奏（`inspection_every_tasks`）+ `inspect` 四类断言 | 第一轮末（`inspect` 弱化版）→ 完整巡检与知识治理归第二轮 | 三项均属 D23/D24 的跨轮基础项；本轮只交付 `inspect` 的四类弱断言。登记为「部分交付」，出口：第二轮补全并补断言（归档引用、终态、重复 id、知识治理） |
| N4 的 transfer/reverse 承接核验 | 第二轮（依赖建边/替换） | 首轮无具名承接入口；先修 keep/commit 两侧 |
| N5 的异常归档持久化查证 | 第二轮（`task.archived` 派生） | 首轮异常归档只写终态并移动；持久化查证需与 `run.terminate` 的派生规则同批 |
| N10 治理面见证排除前缀 | 不修 | 排除 `.wf/node_modules` 只会让条件①偏保守（取 complex），不会放行；登记为已知偏差 |

---

## 5. 需人裁决（C 类）

1. **N8：`repair --dispose` 是否纳入令牌（已裁定：纳入；实现见 `validation.md` §17）。** 机制稿 §10.3 的令牌覆盖「repair」，实现稿 §4.6 把它描述成维护组处置回写。两种读法都可成立：按机制稿应加令牌（改动小、更严）；按实现稿可视为「回写处置不是修复应用」。**请人裁定一次并写回实现稿对应段落**，不要两边各留一句。
2. **F6 归档顺序。** 本复核结论是「按设计稿 §4.2 保持现状」；若人认为应按机制稿 §5.3 字面重排，则属上位之间冲突，须按 charter T1 / 设计稿 §1.5 出「需人裁决」并同批改机制稿，而不是只改实现。

---

## 6. 已完成的登记动作（本轮）

- `validation.md` §11 新增「评审复核后的未运行/部分交付登记」：三项未接线（F2 equivalences / F3 activation / F11 threshold）、F2 夹具缺的两条专属分支（Trellis 二分支、共存与外部提交）、N1 的三项配置键消费，以及异常归档持久化查证、transfer/reverse 承接、治理面见证偏差等，均按「未运行/部分交付 + 原因分类 + 归属轮次」逐条补记。
- 未改实现稿：实现稿的对应表述与 §7.3 的更新，与 A 类修复同批做**一次**重绑与复审，避免两次重绑。

---

## 7. 执行顺序与回归清单

1. **A20**（先补记录）→ 2. **A5/A10/A11/A12/A15/A18/A21/A22/A23**（结构核验与交接/收工/放弃前置）→ 3. **A2/A3/A13/A14**（接线）→ 4. **A1/A6/A7/A9/A16/A17**（门禁与工具）→ 5. **A8**（卸载偏离）→ 6. **A4/A19**（模板与输出）

每批完成后：`build-wf-release.py --version` + `--verify` + `--verify-token-parity`；重跑 V1–V5、F0/F1/F2（含本轮新增用例）；三条机检（`validate-wf-design.py` 4/4、`check-doc-refs.py` 0 problem、`unittest` 19 tests）。

全部收口后再做一次实现稿重绑（§7.1/§7.3 + 本文 A/B 类的最终状态），并交未参与修订的会话复审。

## 8. 本次复核未做

- 未改代码、未改发行树、未改 charter/设计稿/机制稿/索引/来源说明（代码修复属下一批，见 §3）；
- 未做二轮（实例/依赖/返工/复评完整路径）与三轮（upgrade/发行引用/purge）能力；
- 未新增原因码、状态值或判定字段；F6 顺序、N8 令牌两处留待人裁。
