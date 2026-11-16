# 验证记录（2026-11-15）

范围：`scripts/tests/**`（authoring runner 与测试）＋两份 README ＋
`.trellis/spec/docs/wf-delivery-discipline.md`。产品 payload、正式发行树与产品发行清单未改
（`docs/workflows/wf/**`、`docs/workflows/wf-release/**` 的 `git diff` 为空）。

## 1. 需求 ↔ 证据

### R1 journal 恢复窗口完整

| 窗口 | 断言 | 结果 |
|---|---|---|
| journal 已落、旧代未移、staging 不可验证 | `test_release_lock.JournalTest.test_window_journal_written_before_old_moved_rolls_back_in_place`、`test_template_cache.RecoveryTest.test_window_journal_written_before_old_moved_rolls_back_in_place`：`rolled-back`、旧字节/ meta 原文不变、journal 清、staging 清（**不再要求 backup**） | PASS |
| 移旧未装新 | 既有 `test_verifiable_new_generation_rolls_forward`（前滚） | PASS |
| 装新未写 meta | `test_window_new_generation_installed_before_meta_is_completed`：前滚写出 journal 冻结的新 meta/owner | PASS |
| 写 meta 未清 journal | `test_window_meta_written_before_journal_cleared_is_finished`：复写冻结字节、清 backup/journal | PASS |
| staging 半移动/损坏 | `test_broken_new_generation_rolls_back_old_bytes`、`test_half_moved_staging...`（template）按冻结旧字节回滚 | PASS |
| 首次发布半安装 | `test_window_first_publication_partial_install_is_undone`（两模块）：只撤本事务的不完整新代，sibling/兄弟条目不动 | PASS |
| 两代都不可验证 | `test_both_generations_unverifiable_fails_closed`、`test_unverifiable_generations_fail_closed`：非零、journal 与备份现场保留 | PASS |

判定统一收进 `_recovery_action()`（两模块同形、各自持有 owner/validator），只用 journal 冻结的摘要与
归属，不比 mtime、不看当前输入新鲜度。**行为变化**：旧记录里「旧代原位 + staging 损坏」= fail closed
的断言已按新契约改写为「旧代原位完好 → 回滚完成」，并把 fail closed 用例改成两代都不可验证。

### R3 公共摘要 barrier 化

- `repro_select.public_inputs()` 是 source/helpers/executor/runner 的唯一产生点；`select()` 各自算一次
  并写进 bundle schema 2；worker 只重算 `local_inputs` 并比对 context；gate 零重算；writer 最终
  barrier 各重算一次 public/context 后逐 case 核局部输入。
- 断言：`ScanCountTest.test_public_scans_are_constant_in_case_count`（3 vs 30 case 计数相同：
  `{source:1, release:1, helpers:1}`）、`test_worker_consumes_frozen_public_inputs`（worker 后
  source/helpers=0、release=1）、`test_results_gate.GateTest.test_gate_does_not_rescan_public_inputs`
  （三项全 0）、`BundleSchemaTest.test_schema_one_bundle_is_refused`、`test_tampered_public_inputs_are_refused_at_the_writer_barrier`。

### R2 契约测试 scope 化与成本账目

- `test_run_all_contract.RunAllContractTest` 改为单 class owned scope + 空 pool；每 case 独立
  `WF_TEST_RUN_CACHE`，每次调用独立 `results`/`fixture`/`pycache`；env 缺一即失败；plan-only 零 warmup；
  每次调用前后对 `~/.cache/wf-test-{release,run,candidate-repo}` 与 `/tmp/wf-test-results-<uid>.lock`
  做存在性+inode/mtime 快照比对。
- 成本账目（`<scope>/evidence/class-cost.json` 与测试输出的 `class-cost:` 行）：
  `class_seconds=137.17`、`teardown_seconds=0.01`、`class_deadline_remaining=762.83`、
  `cancel_log_wait_seconds=2.51`、`cleanup_seconds=0.03`；每 case 记录 `cold/warm`、`release_build`、
  `template_build_sequences`、`stages`、`plan_calls`、`deadline_remaining`。
- **HOME 边界（如实登记）**：设计要求「每 case 独立 HOME」；A/B 实测（HEAD 代码 + 同一 owned scope）
  把 HOME 指到 scope 内会让候选流程的 `task-check` 退化成 `WF_CHECK_STALE`（f0 saved 9 里 3 项 FAIL），
  恢复宿主 HOME 后同一 run 全绿。被测 SUT 的 check/归档判据依赖用户级环境（git 身份、执行器确认），
  用假 HOME 会改变被测语义，因此契约运行保留宿主 `HOME`，隔离只施加在 runner 管理的写入口上，
  用户 cache 用快照断言证明未被触碰。该偏离已写进 README 与 spec §12。
- 生产侧账目：`summary.json` 新增 `release_build`（`built|reused|checked`）与
  `template_build_sequences`（命中=0/本次发布=1/模板关闭=0）；两份 cache meta 新增 additive `builds`
  （首建=1、命中不增），`wf_test_release --ensure --json` 的 `status` 为 `built|reused`。

### R4 证据与硬化补口

| 断言 | 位置 | 结果 |
|---|---|---|
| 内嵌 repro 不再 ensure/check（一次 run 只剩 controlled 一次） | `test_embedded_repro_does_not_rebuild_the_release` | PASS |
| 独立 repro 入口 ensure/check=1 | `test_candidate_auto...` 给独立 red 入口挂 release CLI 计数 shim，断言恰好 1 次 | PASS |
| candidate validator 起止各 1 次；坏候选只 1 次且不启动 worker | `test_candidate_representative...`、`test_candidate_dirty_worktree_fails_the_start_barrier_without_workers` | PASS |
| `--no-build`+并发仍走 inherited frame | `test_repro_concurrent_with_no_build_uses_the_inherited_frame` | PASS |
| 4 阶段/2 次计划 | `test_subset_runs_one_unit_and_reports_stages_plans_and_cost`（`stages`=4 行、`plan-calls`=2 行） | PASS |
| HEAD 不可读 → run-owned 模板且不碰跨 run 缓存 | `test_unreadable_head_falls_back_to_a_run_owned_template`（顺带修好 `build_template_tree` 缺失导致的 `TEMPLATE-BUILD-FAILED`） | PASS |
| 取消后立即重取 scope 结果锁 + fixture lease | `test_interrupting_root_runner_cleans_its_command_and_fixtures` | PASS |
| `scope:` 域必须过 marker 且等于当前 scope；unit 域不借宿主锁；namespace 无宿主 state locator；宿主锁 inode/持锁不变 | `test_fixture_scope` 三个新用例、`test_execution.NamespaceScrubTest` 两例（真实 `unshare -Urm`） | PASS |
| 双输入交替 miss | `test_template_cache.PublishCostTest.test_alternating_inputs_each_resolve_to_their_own_entry_and_a_third_misses` | PASS |
| AC18 资产落点越界 | `test_install_refuses_a_symlink_asset_target_outside_the_project`：资产落点是指向项目外的符号链接 → `WF_ASSET_DECISION`，outside 与 sentinel 未被改写 | PASS |
| AC18 技能根符号链接（known-gap） | `test_known_gap_install_writes_through_a_symlinked_skill_root`：产品当前 `WF_OK` 并写到项目外兄弟目录（仍在 `WF_FIX` owned scope 内）；已登记产品侧缺口 | 已登记（非通过项） |

## 2. 命令与结果

| 命令 | 结果 |
|---|---|
| `PYTHONPYCACHEPREFIX=/tmp/wf-unit-pycache python3 -m unittest discover -s scripts/tests -t .` | **997 tests OK (skipped 21)**，13.7s（基线 961 OK / skipped 13） |
| `python3 -m unittest scripts.tests.wf_runtime.test_release_lock test_template_cache test_repro_selection test_results_gate test_fixture_scope test_execution test_test_release` | **142 tests OK**，7.9s（R1/R3 定向面） |
| `WF_SLOW_TESTS=1 python3 -m unittest scripts.tests.wf_runtime.test_run_all_contract` | **20 tests OK**，135.8s（class 135.75s、teardown 0.02s、最长 case 22.61s、cancel 2.31s、cleanup 0.03s、剩余 deadline 764.25s） |
| `run_all.sh --full --repro green`（owned scope，并行 8 worker/unshare） | **149 项 0 失败**（套件 59 / 流程 5 / repro 85），墙钟 52.8s（total 50.79s），`release_build=built`、`template_build_sequences=1`、`stages=4`、`plan-calls=2`；全部补口后最终重跑 |
| `--serial` ×1（同冷建输入） | 268.2s（total 266.03s），149 项 0 失败，`reused`、序列 0、缓存命中 |
| 串并等价逐项对拍 | `lines` 64 vs 64（唯一差异是 `f1_ordinary` 的随机 `TASK_ID` 尾字段）；repro 记录 85 vs 85，**0 差异**（原始数据：`evidence/full-green-2026-11-16.json`） |
| `run_all.sh --subset`（r67 假树冒烟，串行/并行各一次） | GATE-OK，17/17，9s |
| `scripts/build-wf-release.py --verify --verify-token-parity` | OK 字节复现（0.1.2，74 assets） |
| `scripts/validate-wf-design.py` | OK（730 行 / 定义位点 51+7 / 消费点缺项 0） |
| `scripts/check-doc-refs.py` | 0 problem(s) |
| `./scripts/validate-skills.sh` | OK（25 skills + spec cross-check） |
| `trellis-library/cli.py validate --strict-warnings` | rc=0 |

## 2b. 2026-11-16 补口（按决策 1=A / 2=A+B / 3=A / 4=A）

### 机制修复

| # | 内容 | 位置 | 断言 |
|---|---|---|---|
| 1 | `prepare-results` 重置每 run 证据文件（`stages`/`plan-calls`），复用显式结果目录时从本轮计数 | `fixture_scope.py::prepare_results` | `test_subset_runs_one_unit_and_reports_stages_plans_and_cost`：同目录复用后仍是 4 行/2 行（修复前实测 8/4） |
| 2 | 契约 case 级共享 900 秒 deadline（原先每调用新建） | `test_run_all_contract.CaseWorkspace.budget` | 同用例断言后续调用 `deadline_remaining` 更小；`test_case_budget_shares_one_deadline_and_refuses_exhaustion` 断言耗尽即 `deadline exhausted` |
| 3 | 发布成功后回收 `<root>.staging-<txn>` **父目录**（原每次构建留一个空壳；只在事务收尾时按前缀回收，fail closed 路径保留现场） | `wf_test_release.py::_reap_staging_parent` | `test_test_release.test_build_leaves_no_staging_or_backup_litter`；README「精确清理」已同步（含 `.lock` 与 staging 口径） |

### 证据补口

| 断言 | 位置 |
|---|---|
| candidate 不建 dev 发行（release CLI 调用 0） | `test_candidate_representative...`（挂 `WF_TEST_RELEASE_CLI` 计数 shim） |
| 独立 repro 入口 ensure/check=1；candidate green 不再加建 | `test_candidate_auto...`（同一 shim，断言 1 → 仍 1） |
| writer barrier 只重算一次公共输入 | `test_repro_selection.CommitTest.test_writer_barrier_scans_public_inputs_once` |
| 单 scope marker 可验回、空 pool（构造性前置 + 启动断言）、每调用 results/fixture/pycache 互不复用、teardown 无进程/无指向 scope 的 FD | `RunAllContractTest.setUpClass/tearDownClass` + `test_subset...` |
| 残留进程检测器**自证**：只在 `environ` 里引用 scope 的子进程也必须被抓到（原实现只查 cmdline，unit worker 会漏检） | `test_scope_process_detector_sees_env_only_references`；`_scope_processes` 同时查 cmdline 与 environ |
| template cache 两个窗口：移旧未装新→前滚；装新未 repoint→按 backup 回滚 | `test_template_cache.RecoveryTest` 两个新用例 |

### 改签与登记

- **AC3 改签（决策 1=A）**：`每 case 独立 state`，`HOME` 保持宿主值；宿主前置条件（执行器确认
  `~/.wf/interpreters.json`、git 身份）写进 `full/README.md` 的「宿主前置条件」段。A/B 证据见 §1 R2 的 HOME 边界。
- **AC18 收窄 + known-gap（决策 2=A+B）**：正式断言只覆盖"资产落点越界"；"技能根符号链接"写穿登记为
  known-gap（注释写明：逃逸目标仍在 case 的 `WF_FIX` owned scope 内、不污染宿主；修复须同时覆盖
  `uninstall.py` 同判据）。产品侧修复列入 PRD Out of Scope 并另行立项。
- **AC5 口径（决策 4-10）**：不再宣称可观测的"build=2"，改为 `release_build=built` + `meta.builds=1`
  （双构建与字节复现是发布器内部步骤）。
- **11-14 审计（决策 3=A）**：结论写在本任务目录 `audit-11-14-2026-11-16.md`，归档原文未改、未新增文件。
- **README 清理口径**：按 cache 类型拆成 A) 测试发行根（`.owner` + 显式路径）与 B) 模板/夹具条目
  （`fixture_scope.py remove`），并说明 test-release 根会被 `remove` 拒绝；A) 的代码片段已实测：
  正常根 rc=0 删除成功，伪造 `.owner` 被 `REFUSED` 拦下（`0.1.0.lock` 需显式删、staging 空壳已不再产生）。

## 3. 成本（同机，owned scope，8 worker）

| 轮次 | 场景 | 墙钟 | units | 失败 | release_build | template 序列 |
|---|---|---|---|---|---|---|
| cold | full + repro green | 52.8s（total 50.79s） | 149 | 0 | built | 1 |
| serial（同冷建输入） | 同输入（`--serial`） | 268.2s（total 266.03s） | 149 | 0 | reused | 0 |

上一任务基线：并行 49.9/49.7s、串行 259s（见 README 的 2026-11-14 记录）。本轮 cold 并行 52.8s（+5.8%）、
串行 268.2s（+3.6%），均在 implement.md 的 ≤10% 目标内；cold 的额外部分来自首次测试发行构建
（`release_build=built`）与模板首建（`template_build_sequences=1`）。
纯 identity 成本预算由 `test_test_release.test_input_identity_stays_within_the_cost_budget` 守护（<3s）。

**串行面新发现并修复**：`--serial` 下 r67 假树套件会原样继承父进程的 scope 结果锁定位串，
内层 run_all 用自己的 scope 时被新硬化拒绝（`scope results domain does not match the active test
scope`）。修法是让假环境按 namespace 同口径清除「域内」locator（结果锁/发行锁/frame/pycache/scope），
但**保留** fixture 租约（嵌套运行器共享同一把全局 flock 是既有语义）。修后该单元 17/17，
串行 full green 149/149。

## 3b. 串并等价对拍（2026-11-16 补口后重跑）

同一 scope 下取 warm 并行与 `--serial` 两次 full green 的结果目录逐项对比：

| 面 | 数量 | 差异 |
|---|---|---|
| `lines`（套件/流程） | 64 vs 64 | 1 条：`f1_ordinary` 的尾字段是随机 `TASK_ID`（rc/status 相同） |
| repro `<case>.json`（case/mode/verified/green/red） | 85 vs 85 | 0 |

原始数据（T0/定向/契约/两轮 full 与差异集合）：`evidence/verification-2026-11-16.json`。

## 4. 未验证与边界

- `d1_tests`/`d1_wf_tests`（manual，需真实宿主压缩）不在自动分母，仍为手工项。
- 同 UID 恶意 TOCTOU、断电级 durability 不在威胁模型（PRD Out of Scope）。
- `HOME` 不 scope 化（见 §1 R2 的 A/B 证据）；如需真正做到 per-case HOME，必须先让 SUT 的
  check/归档判据不依赖用户级环境——那是产品语义改动，超出本任务范围。
- 模板「同槽位单条」仍是既有口径：不同 HEAD/dirty 输入交替会 miss/重建，本轮只补了
  「A/B 各自命中自己的条目、第三种输入 miss」的可复跑断言，没有引入 LRU（Out of Scope）。
