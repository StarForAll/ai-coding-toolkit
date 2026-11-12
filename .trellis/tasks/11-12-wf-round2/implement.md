# 执行清单：wf 第二轮（11-12-wf-round2）

> 配套 `design.md`（能力边界/签名/记录字段/机制 vs 指引）。本文件只管**顺序、改动段落、验证命令、回滚点、评审闸门**。
> 分批规则：**P2 先、P1 后**（人裁 2026-11-12）；每批必须自成一个可验证单元，批末跑 §4 的对应门禁。

---

## 0. 状态图例

`[ ]` 未开始 · `[~]` 进行中 · `[x]` 完成（含实跑证据）· `[!]` 阻塞/待裁 · `[-]` 确认不需要改（须写理由）

---

## 1. 批 B0：规划产物与激活

| # | 步骤 | 改哪里 | 验证 | 状态 |
|---|---|---|---|---|
| B0-1 | 写 `design.md`（含 §7 机制 vs 指引） | 本任务目录 | 人工审查 | [x] |
| B0-2 | 写 `implement.md`（本文件） | 本任务目录 | 人工审查 | [x] |
| B0-3 | P2 十二项落成逐项表 | `design.md` §5（13 行，含计数订正说明） | 逐项有「判据/现状/改哪里/验收」 | [x] |
| B0-4 | 激活 | — | `python3 ./.trellis/scripts/task.py start 11-12-wf-round2 --allow-empty-context` | [x] 已执行（planning → in_progress） |
| B0-5 | 轮次串行门禁前置确认（不重开讨论，只确认工作区未破坏） | — | `git status --porcelain` 仅 `.trellis/.gitignore`；`bash scripts/tests/wf_runtime/full/run_all.sh` 基线绿 | [x] 开工时工作区仅 `.trellis/.gitignore`；基线跑出 2 项失败（`p5_v5` INIT-FAILED、`f7-3` red 失效），逐项定位后**均已修**（见 §10 批次记录） |

**回滚点**：B0 无代码改动，无需回滚。

---

## 2. 批 B1：P2 低风险集（P2-1/2/5/7/9/13）

| # | 项 | 改哪些文件的哪一段 | 新增/改动用例 | 验证 | 状态 |
|---|---|---|---|---|---|
| B1-1 | P2-1 `d` 档判定 | `scope.classify_candidates` 增 `conflicts = cross_task_conflicts(root, task, touch_paths)`（复用既有判定、批准面只推导一次），命中即归 `d`；`check.run_check` 删除重复的争抢判定、改用 `classified["conflicts"]` | `scripts/tests/wf_runtime/test_scope_d_bucket.py`（新，3 例） | 单测 3/3 + 既有 `f7-3-scope-single-source` 双模仍绿 | [x] |
| B1-2 | P2-2 `spec-update` 首跑核前像 | `spec.validate_changes`（整批校验段）新增「首跑也核前像」，不符即 `WF_SEMANTIC_DECISION` 且零写入 | `scripts/tests/wf_runtime/test_spec_first_run_before.py`（新，3 例含还原注入） | 单测 3/3 | [x] |
| B1-3 | P2-5 巡检提示接配置 | `tasks._inspection_hint(ctx)` 改为复用 `_governance_summary` 的 `inspection`（唯一判定，无第二份算法）；**并修正** `due` 的未知压制范围：只由「归档记录不完整 / 配置键非法」决定，不再被知识回收窗口的样本不足压成 `None` | `scripts/tests/wf_runtime/test_inspection_hint.py`（新，3 例） | 单测 3/3 + `r76`/`r77` 既有断言不变 | [x] |
| B1-4 | P2-7 Decision 取值域统一 | **新增 `lib/wflib/decisions.py`**（不新增 `protocol/` 文件：`protocol/` 是发行清单资产，新增文件要同步 dev-manifest/资产表，收益不抵风险；取值域语义仍归机制稿 §1.1，本模块只登记实现稿 §2.3 已接受的写法）；`tasks.py`（`APPROVE_CHOICES`/`MECHANICAL_REVISION`/`replan`/`archive_finish`/`commit_grant`/`debug_ruling`）、`check.py`（`EXTERNAL_CHECKED_CHOICES`/验收结论三值）、`cli.py`（收工四值）全部改为引用登记表 | `scripts/tests/wf_runtime/test_decision_domains.py`（新，5 例） | 单测 5/5 | [x] |
| B1-5 | P2-9 `_apply_debug_inputs` 幂等键 | `tasks.py` 新增 `_debug_idempotency_key()`（声明与裁定各一套结构化键），`_apply_debug_inputs` 遇到同键即跳过 | `scripts/tests/wf_runtime/test_debug_declaration_idempotent.py`（新，4 例含还原注入） | 单测 4/4 | [x] |
| B1-6 | P2-13 无锚点出口文案 | `cli.py` 新增 `EXPLICIT_ENVELOPE_EXIT` 常量，替换 4 处出口（原「用显式信封」未点明 provider） | `scripts/tests/wf_runtime/test_identity_exit_text.py`（新，3 例） | 单测 3/3 | [x] |

**批末门禁**：`validate-wf-design.py`、`check-doc-refs.py`、`python3 -m unittest discover -s scripts/tests`、`discover -s scripts/tests/wf_runtime`。
**回滚点**：`git checkout -- docs/workflows/wf/payload scripts/tests`（回到 B0 结束时的状态；不动用户未提交内容）。

---

## 3. 批 B2：P2 中风险集（P2-3/4/8/10/11/12）

| # | 项 | 改哪些文件的哪一段 | 用例 | 验证 | 状态 |
|---|---|---|---|---|---|
| B2-1 | P2-3 `ready` 分实例 | `runs.py` 新增 `iter_runs`/`binding_state`（判定本体），`cli._eligible_task_bind` 改用它；`cmd_ready` 增 `runs[]` 归组、`run_in_flight` 细分阻断、悬空 run_id 标 unknown（**不做子仓库归组**：charter T3 B2 硬边界） | `test_ready_runs.py`（新，4 例） | 单测 4/4 + `ready-view` 双模仍绿 | [x] |
| B2-2 | P2-4 自检解析 SKILL frontmatter | `install.py` 新增自含的 `skill_frontmatter_problems()`（起止 `---`、`name`/`description` 非空、重复键），`self_check` 对 `kind=skill` 逐份核 | `repro/skill-frontmatter-selfcheck.py`（新，双模；把清单摘要改成与新内容一致，只留 frontmatter 检查能抓到） | green/red 均 PASS | [x] |
| B2-3 | P2-8 键值语义解析 | `bin/wf.py` 新增 `declared_values(text, key)`（行内键值成对，键前须为分隔符/行首），`project_key_approved` 改用它；`config.project_python_key` 零调用方 → 登记进 §2.3.11「运行时死代码」（不删） | `test_project_key_semantic.py`（新，5 例） | 单测 5/5 + `executor-approval-chain`、`project-key-archived-evidence` 双模均绿 | [x] |
| B2-4 | P2-10 start 期验证证据入 action | `tasks.py` 新增 `_start_verification_ids`/`_start_verification_evidence`/`_missing_start_verification_evidence`；结果并入 `action.inputs["start_verifications"]`，动作启动后与结案前各核一次真实后置 | `test_start_verification_action.py`（新，5 例） | 单测 5/5 + `task-start-surface` 双模绿 | [x] |
| B2-5 | P2-11 D08 依赖/实例目标碰撞 | `dep` 侧已交付：`cmd_dep` 的 `new_action(targets=[{task},{prereq}])` 覆盖两端；实例侧（`run create/advance`）随 B4/B5 | `repro/dep-edges.py` 断言动作含双端目标（经 facts/prerequisites 可见） | — | [~] 依赖侧完成、实例侧待 B4/B5 |
| B2-6 | P2-12 R93 注入式双模反例 | 新增 `repro/identity-platform-fact.py`：未安装宿主写操作被拒（facts 带 `installed_platforms` 与登记出口）+ 只读不受限；注入=去掉平台成员判定 | 双模 | `--expect green`/`--expect red` 均 PASS | [x] |
| B2-7 | P2-6 `task-check` 执行移出锁（**结构改动，单独一批**） | `check.py` 拆 `run_check_scope`/`run_check_execute`/`run_check_finish`（`run_check` 保留为兼容入口）；`tasks.py::cmd_task_check` 改两段锁 + 中间锁外执行，回锁后重核 holder/代次并**重算锚点**；新增 `_require_task_dir()` 复用记录缺失出口 | `test_check_lock_window.py`（新，3 例） | 单测 3/3 + 既有 28 个 `task-check` 套件全绿 + run_all 全绿 | [x] |

**批末门禁**：同 B1 + `run_all.sh`（本轮首次全量）。
**回滚点**：按文件回滚本批改动；P2-6 单独提交，失败只回滚该提交。

---

## 4. 批 B3：P1 小件（dep / task-reassess / out-of-scope / inspect 治理输出）

| # | 能力 | 改哪里 | 用例 | 验证 | 状态 |
|---|---|---|---|---|---|
| B3-1 | `dep add\|rm` | `tasks.py` 增 `_prerequisite_graph`/`_find_cycle`/`cmd_dep`；`cli.COMMANDS["dep"]` 换真实处理器并把 `dep` 纳入 `ACTIVATION_REQUIRED` | `test_dep_edges.py`（新，4 例）+ `repro/dep-edges.py`（新，双模，两层注入） | 单测 4/4 + repro green/red 均 PASS | [x] |
| B3-2 | `task-reassess` 完整路径 | `lib/wflib/tasks.py::cmd_task_reassess` + `_reassess_empty_set` 改造为条件核验 | `test_task_reassess.py`（新） | 单测 | [ ] 未开工（返工集合要有 `rework_of` 生产者才有意义 → 与 B5-4 同批） |
| B3-3 | `inspect` 两项治理输出 | `tasks.py` 增 `_scan_repo_paths`/`_manual_compare`/`_author_order`；`inspect()` 的 `governance_omitted` 清空（空列表＝断言） | `test_inspect_governance.py`（新，6 例）+ `inspect-declares-omitted.py` 断言改强（双模） | 单测 6/6 + repro 双模绿 | [x] |
| B3-4 | `.wf/out-of-scope/` 四项前置 | `paths.WRITE_TARGET_PREFIXES` += 该目录；`protocol/project_data.json` 前缀 += 该目录；`spec.py` 增 `parse_frontmatter_text`（与 `parse_frontmatter` 同源）+ `out_of_scope_problems`（schema、文件名一致、只增不改、追加行形态），在 `validate_changes` 整批校验段调用；`tasks.py` 增 `_out_of_scope_duplicates` 并接进 `governance`，`governance_omitted` 清空 | `test_out_of_scope.py`（新，10 例，覆盖 PRD 五项验收 + 「改写既往内容被拒」「未知不当零」「声明清空」） | 单测 10/10 | [x] |

**前置依赖**：B3-1 与 B2-5 共用 targets 判定；B3-3 与 B3-4 的重复登记核对同批（同一遍历）。

---

## 5. 批 B4/B5：P1 大件（definition / run + rework + replace）

| # | 能力 | 改哪里 | 用例 | 状态 |
|---|---|---|---|---|
| B4-1 | `definition prepare/validate` | `runs.py` 实装：`parse_definition`（标记唯一 + 紧邻 json 围栏）、`validate_definition`（六阶段：`_schema_problems`/`_local_id_problems`/`_reference_problems`/`_path_problems`/`_skip_problems`/`_completion_problems`）、`prepare`（准备记录 + 未通过草稿保留）、`validate`（只读）；`cli.COMMANDS["definition"]` 换 `_runs_command` | `test_definition.py`（新，18 例）+ `repro/definition-static-check.py`（新，双模） | 单测 18/18 + repro 双模绿 | [x] |
| B4-2 | 准备记录 | `runs.py::prepare` 写 `.wf/preparations/<id>.json`（`session_key`/`scope_paths`/`authorization`/`definition_refs`/`validation`/`progress`/`wip`/`ended_at`），该目录已是 `scope._is_control_record` 的固定职责控制记录；别的会话持写权 → `WF_WRITER_BUSY` | 同上（断言字段齐全与 drafts 保留） | repro 断言覆盖 | [x] |
| B5-1 | `run create` / `run locate` | `runs.py`：`creation_problems`/`input_value_problems`（纯判定）、`create`（writer 主记录 + 8 步 + 续做）、`locate`（只读）；`cli.COMMANDS["run"]` 换 `_runs_command`，`SUBACTIONS` 表登记子动作，`definition` 纳入 `ACTIVATION_REQUIRED` | `test_run_create.py`（10 例）、`test_run_locate.py`（4 例）、`repro/run-create-once.py`（双模） | 单测 14/14 + repro 双模绿 + run_all 全绿 | [x]（`pause` 未做，见 B5-3） |
| B5-2 | `run advance`（含人判/略过/自动建任务与顺序边） | `runs.py::advance` | 同上 + `scripts/tests/wf_runtime/test_run_advance.py` | [ ] |
| B5-3 | `run terminate` + `finish` | `runs.py::terminate/finish` | `repro/run-terminate.py` | [ ] |
| B5-4 | `task-rework` | `tasks.py::cmd_task_rework`（新；机制稿 §6.2 全段） | `repro/task-rework.py`（双模：图非法/未完成动作/批准不继承） | [ ] |
| B5-5 | `task-replace` | `tasks.py::cmd_task_replace` | `repro/task-replace.py`（双模） | [ ] |

**批末门禁**：全量 `run_all.sh` + 三夹具 F0/F1/F2 相关项 + `--verify` 字节复现。

---

## 6. 批 B6：文档同步与发行树

| # | 项 | 改哪里 | 验证 | 状态 |
|---|---|---|---|---|
| B6-1 | 实现稿 §6.4 轮次表：P1 各项状态从「第二轮交付」改为「已交付（本任务）」 | `docs/workflows/wf-framework-implementation.md` §6.4 | `validate-wf-design.py`、`check-doc-refs.py` | [ ] |
| B6-2 | 实现稿 §2.3.11：本节各条状态（P2-1/2/3/4/5/6/7/8/9/10/11/12/13 对应条目）逐条改为「已交付」并给用例名 | 同上 §2.3.11 | 同上 | [ ] |
| B6-3 | `governance_omitted` 声明同步（实现稿 + 代码 facts） | §2.3.11 巡检条 + `tasks.inspect` | 同上 | [ ] |
| B6-4 | `analysis/backlog-excluded-from-item6.md` 状态表订正（「只记录，不实现」→ 已按裁定实施） | 该文件 §2/§4 | `check-doc-refs.py` | [ ] |
| B6-5 | `analysis/proposal-repairing-state.md` §6 标题「工作树未提交」订正 | 该文件 §6 标题 + §8 | 同上 | [ ] |
| B6-6 | 机制稿：仅在本轮实现暴露判据缺陷时按人裁同批改；否则不动（charter T1） | — | 人工审查 | [ ] |
| B6-7 | 发行树重建 | `python3 scripts/build-wf-release.py --version 0.1.0` + 提交 `docs/workflows/wf-release/**` | `--verify` 与 `--verify-token-parity` | [ ] |

---

## 7. 门禁命令（每批必跑，最终全跑）

```bash
/softwares/python/bin/python3 scripts/validate-wf-design.py          # 输入摘要 4/4 + 七项检查
/softwares/python/bin/python3 scripts/check-doc-refs.py              # 0 problem(s)
./scripts/validate-skills.sh                                          # validated N + spec cross-check passed
/softwares/python/bin/python3 -m unittest discover -s scripts/tests
/softwares/python/bin/python3 -m unittest discover -s scripts/tests/wf_runtime
/softwares/python/bin/python3 scripts/build-wf-release.py --verify
/softwares/python/bin/python3 scripts/build-wf-release.py --verify-token-parity
bash scripts/tests/wf_runtime/full/run_all.sh
git status --porcelain docs/workflows/wf-release                     # 期望空
```

**纪律**：验证结论只能来自在待提交内容上的实跑；「未运行」必须写原因分类，不得写成通过。

---

## 8. 评审闸门

1. **G1（B0 后）**：`design.md` §7「机制 vs 指引」逐条能回答「这条为什么必须机械 / 为什么只能是指引」。不过即回 B0。
2. **G2（B1/B2 每批末）**：§7 门禁前四项全绿；新增用例逐条能红（注入验证）。
3. **G3（B3 后）**：`inspect` 与 `out-of-scope` 同批——不允许出现「目录已放行但无消费者」或「消费者存在但白名单未放行」。
4. **G4（B5 后）**：`run`/`definition` 端到端夹具通过；`task-rework`/`task-replace` 的「R 不得消费 T 的批准」「T 不自动 paused（同实例）」逐条有断言。
5. **G5（B6 后，交付前）**：§7 门禁全跑；`git status` 仅剩本任务预期改动；然后**停在「待人工审查」**（不归档、不写 journal、不跑 finish-work）。

---

## 9. 交付前必须如实报告的四类

1. 改了什么（逐批文件清单）；
2. 验证了什么（命令 + 实跑结论）；
3. **没验证什么**（原因分类：需真实事件 / 需外部 CLI / 夹具不具备 / 明确不做）；
4. 需裁决或待确认项（charter T1 冲突、机制 vs 指引拿不准的条目）。

---

## 10. 批次记录（实跑证据，逐批追加）

### B0 —— 规划产物与激活（2026-11-12）

- 写了 `design.md`（含 §7「机制 vs 指引」）与 `implement.md`；PRD 的 P2 从概述落成 §5 的 13 行逐项表（PRD 文字说「12 项」，枚举含末句「以及 `cli.py` 无锚点出口文案」实为 13 项，已订正计数、不改 PRD 判据）。
- `task.py start 11-12-wf-round2 --allow-empty-context`：`planning → in_progress`，branch=main。
- **`task-rework` 的「权威冲突」按事实订正为「不存在冲突」**（见 `design.md` §0）：`solution-review-v42.md` 与 `/tmp/wf-solution-review-2026-11-09.md` 字节相同，`task-rework` 出现 0 次、`必须删除` 0 次；实现稿 §2.3:260 把它列为第二轮交付项；归档任务 `11-09-wf-v42-control-flow-repair/rework-conflict.md` 已自我更正为「误判出处」。→ 本轮按机制稿 §6.2 交付，`cli.py` 注释同批订正。

### B1 —— P2 低风险集（P2-1/2/5/7/9/13，2026-11-12）

改动文件：

| 文件 | 改动 |
|---|---|
| `payload/lib/wflib/decisions.py`（新） | `Decision.choice` 取值域唯一登记表（9 个操作）+ `accepts`/`canonical`/`registered` |
| `payload/lib/wflib/tasks.py` | 取值域引用登记表（`APPROVE_CHOICES`/`MECHANICAL_REVISION`/`replan`/`archive_finish`/`commit_grant`/`debug_ruling`）；`_debug_idempotency_key` + 幂等跳过；`_inspection_hint` 复用 `_governance_summary`；`inspection.due` 压制范围收窄 |
| `payload/lib/wflib/check.py` | `EXTERNAL_CHECKED_CHOICES`/验收结论三值引用登记表；删除重复的 `cross_task_conflicts` 调用，改用 `classified["conflicts"]` |
| `payload/lib/wflib/scope.py` | `classify_candidates` 增 d 档（复用 `cross_task_conflicts`，`touch_paths` 由调用方传入、只推导一次） |
| `payload/lib/wflib/spec.py` | `validate_changes` 首跑核前像（零写入） |
| `payload/lib/wflib/cli.py` | `EXPLICIT_ENVELOPE_EXIT` 常量 + 4 处出口；收工四值引用登记表 |
| `payload/dev-manifest.json` | 登记 `lib/wflib/decisions.py`（`preflight` 要求源码树与清单一一对应） |
| 新增用例 | `test_scope_d_bucket.py`、`test_spec_first_run_before.py`、`test_inspection_hint.py`、`test_decision_domains.py`、`test_debug_declaration_idempotent.py`、`test_identity_exit_text.py`（共 21 例，含 3 处「还原缺陷即变红」的注入） |

**过程中定位并修掉的两个真实缺陷**（都不是本轮新引入，但被本轮改动暴露/加重）：

1. `check._spec_coverage` 的 `decisions_used` 在改引用登记表时误用了 `item.get("choice")`（`item` 是 `needs` 条目），导致 `spec_review.evidence` 恒空 —— 由 `r25r30_tests` 的「R28 spec_review 写入检查记录」抓到，已改回 `decision.get("choice")`。
2. `inspection.due` 被知识回收窗口的未知压成 `null`（见 B1-3），与机制稿 §8.5 的触发口径相反。

实跑结论（命令与输出摘录）：

```
python3 scripts/validate-wf-design.py     → 输入摘要 4/4；七项检查 + 覆盖率断言通过
python3 scripts/check-doc-refs.py         → 0 problem(s)
./scripts/validate-skills.sh              → OK: validated 25 skill(s) + spec cross-check passed
python3 -m unittest discover -s scripts/tests            → Ran 478 tests, OK
python3 -m unittest discover -s scripts/tests/wf_runtime → Ran 175 tests, OK
python3 scripts/build-wf-release.py --verify             → OK byte reproduction (0.1.0, 75 assets)
python3 scripts/build-wf-release.py --verify-token-parity→ first=ok / after=expired
bash scripts/tests/wf_runtime/full/run_all.sh            → 运行 132 项，失败 0 项；repro 68/68（green+red）；GATE-OK
```

**B1 末次全量门禁（2026-11-12 16:59，在待提交内容上实跑）**：`132 项 0 失败`、`repro 68/68`、
`GATE-OK（豁免中的债 0 项）`。三次全量跑分别暴露了 3 个问题，全部修完才转绿：
① `p5_v5` INIT-FAILED —— 首跑时我在 run_all 运行期间改源码，发行树被半途重建；
改用干净重建后 `f1_init` 通过（**不是代码缺陷**，是并行编辑污染，已记入教训）；
② `f7-3` red 失效 —— 新增的 `cross_task_conflicts` 二次推导批准面掩盖了注入点，
改为由调用方传入 `touch_paths`；
③ `r25r30` R28 `spec_review.evidence` 恒空 —— 改引用登记表时误用 `item` 变量；
④ `r84` B4-1 —— d 档从「已知边界」变成「已交付」，文档措辞与断言同批更新（断言改强，不是放宽）。

**仍未做（本会话到此为止）**：B2（`ready` 分实例、自检解析 SKILL frontmatter、`project_key` 语义键值、
start 期验证入 action、D08 目标碰撞、R93 注入式双模反例、`task-check` 执行移出锁）、
B3–B5（P1 七项能力）、B6 的发行树提交与其余文档同步。原因分类：**会话预算**，不是阻塞；
下一会话从 B2 的第一项续做，`implement.md` 的批次表已是可执行清单。

### B3（部分）——P1 两项自治能力（2026-11-12）

同批交付的两项（PRD §2.1 第 7 项与 §2.2 要求同批）：

1. **`inspect` 两项治理输出**：`manual_compare`（§8.5 三步：见证 → 前缀不可证不相交 → potential，含 `unverified` 与扫描范围）与 `author_order`（`extracted` 前置、`author=ai` 优先）。
2. **`.wf/out-of-scope/` 四项启用前置**：写入者（`spec-update` 的 add/update + schema 与只增不改校验）、重提追加（不新建文件）、路径放行（`paths`/`protocol` 两处唯一声明）、消费者（巡检重复登记）。
3. **同批声明变更**：`governance_omitted` 清空；机制稿两处**状态表述**事实订正（§8.4 末句与 D24 轮次列），只改状态、不改判据。

门禁（本批跑完后）：见 §9 的 `run_all` 结果与 `--verify`。

### B3-1 —— `dep` 建删边（2026-11-12）

- 落点：`tasks._prerequisite_graph`（只收活动记录）、`tasks._find_cycle`（DFS 三色）、`tasks.cmd_dep`；`cli.COMMANDS["dep"]` 由桩换成 `_task_command("cmd_dep")`，并把 `dep` 纳入 `ACTIVATION_REQUIRED`。
- 动作：`dependency.change`，steps `validate_graph` → `write_prerequisites`，**targets 覆盖两端任务**（D08 的依赖侧要求）。
- 判定：自环显式守卫 + 环检测（两层）；建边要求前置在活动区且未归档；删边只改未归档持有侧、目标可在归档区（死引用交 repair）；重复 add/rm 幂等返回。
- 用例：`test_dep_edges.py`（4 例）、`repro/dep-edges.py`（双模）。**注入教训**：首版只退回自环守卫，断言仍成立——因为环检测独立拦住了自环，于是「红不掉」。改成把**两层都**退回后才真正变红；这条写进用例注释，免得后人再写一个测不到东西的注入。

### B4 —— `definition` 准备与静态校验（2026-11-12）

- 落点：`runs.parse_definition` / `validate_definition`（六阶段 + 按 `stage` 排序）/ `prepare` / `validate`；`cli.COMMANDS["definition"]` 由桩换成 `_runs_command("definition")`（位置参数取子动作）。
- 分界：结构/id 唯一与保留前缀/引用存在与顺序/路径边界/跳过替代下游一致性/必要验证的步骤承载 → 机制；「定义写得清不清楚」「skip 条件该不该认」→ 人判；`completion` 自然语言不求值。
- **仍未交付并登记**：`run *`（实例创建/推进/暂停/终止）仍是桩；准备范围未登记到 `writer.holder.scope`（以准备记录承载，建实例时重核）；`prepare` 未写 `definition.prepare` 的动作意图（准备期只有记录级恢复）。
- 用例：`test_definition.py`（18 例：标记唯一/紧邻/非法 JSON/保留前缀/重复 id/引用前向/prior_step 落点/step_artifact 根/skip 与 required 冲突/未知 consumer/步骤无验证/问题按阶段排序），`repro/definition-static-check.py`（双模）。

### B2-7 —— `task-check` 验证执行移出锁（2026-11-12，口径 A）

- 结构：`check.run_check` 拆成 `run_check_scope`（锁内准备：范围/知识兜底/`resolve_verifications`/锚点与扫描快照）→ `run_check_execute`（**锁外**：跑命令取证）→ `run_check_finish`（锁内定稿：双轴审查、结束前重算范围、扫描前后比对、组装记录）；`run_check` 保留为三段顺序调用的兼容入口。
- `cmd_task_check`：两段 `lock.acquire`，回锁后 `require_held` 重核 holder 与代次，并**重算 `check_anchor`**（与准备段不等即 `WF_CHECK_STALE`，facts 并列 before/after）；记录缺失出口抽成 `_require_task_dir()` 供两段共用（不拼 None 路径）。
- **口径选择**：按 A 落地（不加 `writer.checkpoint` 摘要字段、不升格其为「对象稳定性判据」）。B 的价值（锁定窗口内改动的**差异清单**）由 `WF_CHECK_STALE` 的 before/after 摘要与既有的 `changed` 列表承载，已够定位；真要持久化摘要，须先回机制稿 §1.4 登记 `checkpoint` 字段，属另案。
- 用例：`test_check_lock_window.py` 3 例（含线程用例：执行段期间另一会话能取得项目锁——这是「不占锁」的直接证明）。

---

## 11. B5 拆解：`run create` + `run locate`（下一批的执行清单）

> 依据：机制稿 §1.5（实例记录字段）、§5.1（内嵌动作与幂等键）、§7.2（准备/创建校验）、
> §7.3（推进与任务映射）；实现稿 §2.3 的 `run` 行。代码基线：本文件 §10 的 B4（`definition`
> 已交付）+ `tasks.cmd_task_new`（**同一形状的 writer 主记录创建**，可直接照抄结构）。

### 11.1 为什么先只做 `create` + `locate`

- `create` 是实例能力的**唯一入口**：没有实例记录，`advance/pause/terminate` 无从测起。
- `create` 同时是 §2.3.11 登记的第 ② 项（**准备范围 -> writer scope**）必须落地的地方：机制稿 §1.4
  要求 writer 的 holder scope 是「绑定对象**或**已授权准备范围」，而 B4 只把准备记在
  `.wf/preparations/<id>.json`（`session_key` + `scope_paths`）。`run create` 必须在锁内**重核**
  「本会话确有该定义的准备记录且未结束」，再以 `scope={object:{kind:run,id}, preparation:{...}}`
  取得写权——这一步做完，第 ② 项登记才可关闭。
- `locate` 只读、零风险，用来给 `advance` 之后的人工核对与巡检一个稳定入口。

### 11.2 `run create --creation <path>` 的固定步骤（照 `cmd_task_new` 的形状）

| 步 | 做什么 | 判据 / 关键点 |
|---|---|---|
| 0 | 解析 creation 文件 | `{definition_id, definition_digest, inputs, steps:{<step-id>: applicable\|skipped}, expansion:{...}}`；缺项、未知 step id、类型不符 → `WF_SEMANTIC_DECISION`（列可选值） |
| 1 | 载入定义并复核静态校验 | `runs.parse_definition` + `runs.validate_definition`；任何问题 → `WF_DEFINITION_INVALID`（不建实例） |
| 2 | 版本一致性 | 文件当前 `sha256` 必须等于 `definition_digest`；不等 → `WF_SEMANTIC_DECISION`（facts 给两版摘要，出口：按当前内容重新确认） |
| 3 | 输入校验 | 按 `inputs` 声明：required 缺值 → `WF_SEMANTIC_DECISION`；`secret_ref` 只接受引用对象、**不得**出现明文；`path` 走 `paths.normalize` + 边界 |
| 4 | 准备范围重核（**关闭 §2.3.11 第 ② 项**） | 读 `.wf/preparations/<id>.json`：`session_key` 必须是本会话、`scope_paths` 含该定义、`validation.ok=true`、`ended_at` 为 null；任一不成立 → `WF_SEMANTIC_DECISION`/`WF_APPROVAL_MISSING` |
| 5 | 目标预检 | `.wf/workflow-runs/<run-id>.json`、`.wf/workflow-runs/<run-id>/`、绑定文件三者都不存在；碰撞 → `WF_TARGET_COLLISION` |
| 6 | **锁内**取写权 + 固定意图 | `writer.acquire(scope={object:{kind:run,id}, preparation:{id, scope_paths}})`，随后 `actions.new_action("run.create", targets=[writer, run, snapshot, binding, instance, definition-digest, inputs-digest])`，**同一次写入**（照 `cmd_task_new` 的「意图与写权授予同一次写入」） |
| 7 | 逐步推进 | steps = `write_snapshot`（原字节落 `definition.md`）→ `write_run`（§1.5 全字段）→ `acquire_writer`（已在上一步完成，这步只核后置）→ `bind`（`session.bind` 的首次绑定，`object={kind:run}`，写 `instance_id`）；每步先核真实后置、缺什么补什么 |
| 8 | 结案 | `_finish_writer_action` 前**重核每步后置**（快照摘要 = 定义摘要、run 记录可解析且 `terminal=null`、绑定指向该 run、holder scope 匹配） |

**不做什么**：不代批准业务（实例创建只取得「规划权限」，任务仍要自己批）、不创建任何任务、不推进 cursor。

### 11.3 `run locate --run <id>`（只读）

返回 `{run: {id, workflow_id, terminal, paused}, cursor, task_map, step_results, tasks: [{id, status, phase}], binding_state}`；
`tasks` 的状态一律**查 task**（不抄进实例记录）；未知/不可解析 → `WF_HISTORY_UNRESOLVED`，不当「没有」。

### 11.4 用例清单（每条都要能红）

1. `test_run_create.py`：creation 缺字段/未知 step → `WF_SEMANTIC_DECISION`；定义校验不过 → `WF_DEFINITION_INVALID`；digest 不符 → `WF_SEMANTIC_DECISION`。
2. `test_run_create.py`：**没有准备记录**（B4 的 prepare 未跑）→ 拒绝；准备记录属于别的会话 → 拒绝；`validation.ok=false` → 拒绝（这三条是 §2.3.11 第 ② 项的验收）。
3. `repro/run-create-once.py`（双模）：同一会话重入 `run create` → 按固定意图续做、**不建第二个实例**；注入=重入时按当前参数重建 → 红（出现两个 run 记录）。
4. `test_run_locate.py`：只读不改任何字段；悬空 run_id → `WF_HISTORY_UNRESOLVED`。
5. 快照固定：创建后改定义源文件 → `run locate` 仍报创建时的 digest；`advance`（下一批）据此判「定义已变」。

### 11.5 风险与回滚

- 风险：`writer.acquire` 的 preparation scope 是**首次**在运行期被真实使用，`writer.require_supported()` 只核结构不核语义；要另加一条断言「scope.object 与 scope.preparation 不能同时为空」。
- 回滚点：`run` 解封单独一次提交；失败只回滚该提交（`git checkout -- payload/lib/wflib/runs.py payload/lib/wflib/cli.py`）。

### B5-1 —— `run create` + `run locate`（2026-11-12）

- 落点：`runs.creation_problems` / `input_value_problems`（纯判定）/ `create` / `_advance_run_create` / `_resume_run_create` / `locate`；`cli` 的 `SUBACTIONS` 表登记 `run` 的子动作，`definition` 进 `ACTIVATION_REQUIRED`。
- **关闭 §2.3.11 第 ② 项**：`create` 锁内重核准备记录（`session_key` 属本会话、`scope_paths` 覆盖定义、`validation.ok`、未 `ended_at`），再以 `scope={object:{kind:run}, preparation:{...}}` 取写权。
- 快照 = **原字节**；摘要进实例记录；重入按原意图续做，定义字节变则拒（快照不可重建）。
- 三个过程中踩到的坑（都记进用例注释）：
  ① `locate` 的桩函数在文件后面覆盖了新实现（Python 后者生效）——已删桩；
  ② `_advance_run_create` 里 `actions`/`codes` 未导入（内部错误 70，被 repro 抓到）；
  ③ repro 的注入一度选「重入建第二个实例」，但那条路被**未结案意图/已绑定/writer 非 idle** 三层同时挡着，任何单点注入都不可达 → 改成「把快照写成非原字节」，目标断言落在**快照必须等于确认的原字节**（机制稿 §7.1）。
- 未做：`run advance/pause/terminate`（B5-2/B5-3）；`_resume_run_create` 在 creation 文件缺失时以空值续做（登记为后续项）。

### B5-2 —— `run advance` 最小闭环（2026-11-12）

- 落点：`runs.advance` + 纯函数 `_applicability`/`_next_step`/`_previous_task_step`/`_human_answer`/`_advance_step_done`；实例记录上落 `run.advance` 动作（`resolve_step` → `create_or_reuse_task` → `record_cursor`）。
- 判定顺序：结算（成功归档→satisfied；异常归档→`WF_SEMANTIC_DECISION`）→ **等待**（当前步骤任务未完成就停在原地，不跳步）→ 可略（须有决定，记 skipped，不建任务）→ human（答复须属声明选项）→ task（复用映射或按顺序前置建任务，前置须正常归档）。
- **分界**：「这一步算不算完成、产物够不够用」由人在任务上走四阶段判；实例只引用任务结果，不复制 status/Check。
- 用例：`test_run_advance.py`（6 例）、`repro/run-advance-creates-task.py`（双模）。
- 未做：`run pause`/`run terminate`（B5-3）；`step_results` 的产物引用（`outputs`）与「已有产物记复用」未实现——登记为后续项。
