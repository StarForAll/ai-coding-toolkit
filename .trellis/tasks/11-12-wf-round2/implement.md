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
| B2-1 | P2-3 `ready` 分实例 | `lib/wflib/cli.py::cmd_ready`：增 `runs[]` 归组与 `run_in_flight` blocker（**不做子仓库归组**：charter T3 B2 硬边界） | `scripts/tests/wf_runtime/test_ready_runs.py`（新） | 单测 | [ ] |
| B2-2 | P2-4 自检解析 SKILL frontmatter | `payload/install.py::self_check`：投放后逐 `SKILL.md` 解析 frontmatter，问题入 `problems` | `repro/skill-frontmatter-selfcheck.py`（新，双模） | `bash scripts/tests/wf_runtime/full/repro/run.sh` 含该条 | [ ] |
| B2-3 | P2-8 键值语义解析 | `payload/bin/wf.py::project_key_approved`：逐行解析键值成对；`wflib/config.py::project_python_key` 只登记为无调用方 | 追加断言到 `repro/executor-approval-chain.py` 或新单测 | 单测 + repro | [ ] |
| B2-4 | P2-10 start 期验证证据入 action | `lib/wflib/tasks.py::cmd_task_start`（`_run_start_verifications` 调用点）与 `_finish_task_action` 的后置核验 | `scripts/tests/wf_runtime/test_start_verification_action.py`（新） | 单测 | [ ] |
| B2-5 | P2-11 D08 依赖/实例目标碰撞 | `lib/wflib/tasks.py::cmd_dep`、`lib/wflib/runs.py::create/advance` 的 `new_action(targets=…)` | `scripts/tests/wf_runtime/test_targets_dependency_run.py`（新） | 单测 | [ ] |
| B2-6 | P2-12 R93 注入式双模反例 | 新增 `scripts/tests/wf_runtime/full/repro/identity-platform-fact.py` | 双模 | `WF_REPRO_INJECT=0/1` 分别绿/红 | [ ] |
| B2-7 | P2-6 `task-check` 执行移出锁（**结构改动，单独一批**） | `lib/wflib/check.py::run_check` 拆三段 + `lib/wflib/tasks.py::cmd_task_check` 的锁段重排 | `scripts/tests/wf_runtime/test_check_lock_window.py`（新） | 单测 + 既有 `test_changes_persisted` 等全绿 | [ ] |

**批末门禁**：同 B1 + `run_all.sh`（本轮首次全量）。
**回滚点**：按文件回滚本批改动；P2-6 单独提交，失败只回滚该提交。

---

## 4. 批 B3：P1 小件（dep / task-reassess / out-of-scope / inspect 治理输出）

| # | 能力 | 改哪里 | 用例 | 验证 | 状态 |
|---|---|---|---|---|---|
| B3-1 | `dep add\|rm` | `lib/wflib/tasks.py::cmd_dep`（新）、`cli.COMMANDS["dep"]` 换真实处理器 | `scripts/tests/wf_runtime/test_dep_edges.py`（新） | 单测 + repro | [ ] |
| B3-2 | `task-reassess` 完整路径 | `lib/wflib/tasks.py::cmd_task_reassess` + `_reassess_empty_set` 改造为条件核验 | `scripts/tests/wf_runtime/test_task_reassess.py`（新） | 单测 | [ ] |
| B3-3 | `inspect` 两项治理输出 | `lib/wflib/tasks.py::_governance_summary` 增 `manual_compare`（§8.5 三步）与 `author_order`；`inspect()` 的 `governance_omitted` 删两条 | `scripts/tests/wf_runtime/test_inspect_governance.py`（新，含「未声明未输出」断言） | 单测 + `inspect-declares-omitted.py` 更新 | [ ] |
| B3-4 | `.wf/out-of-scope/` 四项前置 | `paths.WRITE_TARGET_PREFIXES`、`protocol/project_data.json`、`lib/wflib/spec.py`（`modify-append` 与 schema 校验）、`tasks.py::_governance_summary`（重复登记） | `scripts/tests/wf_runtime/test_out_of_scope.py`（新，正反 5 例：建文件/重提追加/空 reason 拒/concept 与文件名不符拒/多文件报重复） | 单测 | [ ] |

**前置依赖**：B3-1 与 B2-5 共用 targets 判定；B3-3 与 B3-4 的重复登记核对同批（同一遍历）。

---

## 5. 批 B4/B5：P1 大件（definition / run + rework + replace）

| # | 能力 | 改哪里 | 用例 | 状态 |
|---|---|---|---|---|
| B4-1 | `definition prepare/validate` | `lib/wflib/runs.py::prepare/validate/load_definition`（新实现，复用 `records`/`paths`/`templates`） | `scripts/tests/wf_runtime/test_definition.py` + `repro/definition-static-check.py` | [ ] |
| B4-2 | 准备记录 | `runs.py::prepare` 写准备记录（机制稿 §1.4 字段） | 同上 | [ ] |
| B5-1 | `run create/locate/pause` | `runs.py::create/locate/pause` + `cli.COMMANDS["run"]` 子动作分派 | `repro/run-create-advance.py`（双模） | [ ] |
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
