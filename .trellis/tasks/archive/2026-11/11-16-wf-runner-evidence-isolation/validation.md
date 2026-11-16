# 实施验证记录（逐 AC）

> 2026-11-16；基线 `b74d60101bf874f7940af1e20dd1aa73eb8a6ee3`。
> 本文件记录实际执行过的命令与结果；未运行/无法测量的条目单列，不写成通过。

## 1. 代码与测试落点

| AC | 实现 | 测试 / 证据 |
|---|---|---|
| AC01–02 | 新 `scripts/wf_test_paths.py`（scope marker/layout/组件包含）；`fixture_scope`/`plan.py`/`run_all.sh`/`repro/run.sh`/`wf_test_release.py`/`prepare_candidate_repo.py`/`release_lock.py` 委托或消费；public 在校验前禁写 pyc，`--list`/`--dry-run` 零 pycache/零结果写入 | `test_wf_test_paths.py`（含真实 `run_all --list`、显式 dry-run、域外 WF_PYCACHE 零写入）；`test_fixture_scope.py`；contract `test_plan_only_*`/`test_dry_run_only_mirrors_the_plan` |
| AC03–04 | `execution.verdict(phase=...)`；worker 清/设 `WF_REPRO_INJECT`；gate/writer 经 `validate_repro` 同判定 | `test_evidence_protocol.py::VerdictTest/WriterPhaseTest`；`test_repro_selection.py` |
| AC05–06 | `_runtime_identity()` 完整投影；`helper_set=core-v2` 把库来源/scope/候选/上下文/摘要/主 shell helper 纳入公共输入；bundle 3/state 4/context 2/release-context 2；旧 state 只作 legacy | `test_evidence_protocol.py::RuntimeIdentityTest`；`test_repro_selection.py::PublicHelperIdentityTest/AutoModeTest`；contract `test_candidate_auto_*` |
| AC07 | 新 `full/results_summary.py`：冻结 plan/context 绑定、实际 lines 派生、原子发布+读回；shell 只传播 rc | `test_results_summary.py`；contract `test_subset_*`/`test_template_can_be_disabled_*` |
| AC08 | `execution.py` C→G→S→W；G/S subreaper；清理先于摘要；`runner_cleanup.py` 聚合命令级 cleanup，unknown 时保留夹具现场；`prepare_results` 重置旧 `.runner.json` | `test_supervision.py`；`test_runner_cleanup.py`；`test_fixture_scope.py`（stale `.runner.json`）；contract `test_cleanup_unknown_preserves_the_fixture_site`、取消用例 |
| AC09–10 | `prepare_candidate_repo.py` 统一 `verify_candidate`、sidecar 锁（ensure 独占、check 只读无写）；`git` 统一 `GIT_OPTIONAL_LOCKS=0`，check 不刷新 `.git/index`；staging 发布并保留旧代 | `test_prepare_candidate_repo.py`（A/B、tag/HEAD/meta 漂移、无主拒绝、失败重建保留旧代、只读复用、index 不变） |
| AC11–12 | `results_gate.py` 模块级依赖、默认 bundle 路径、稳定归因；`validate_repro` 有限值/相位/结构 | `test_results_gate.py`（默认/显式成功等价 + 失败归因）；`test_evidence_protocol.py::GateAttributionTest` |
| AC13–14 | 新 `full/host_snapshot.py`：只读树清单、缺失/空区分、不跟随树外链接、不可读即未验证 | `test_host_snapshot.py`；contract 类入口/出口 manifest 对拍 + `host_protection` 证据 |
| AC15–16 | 监督/取消/信号隔离/目标信号恢复/控制 FD 不继承；控制帧带 `id`；故障注入仅在 `WF_TEST_FAULT_INJECTION=1`；kill 前核对 PID 启动身份；取消先只向目标发信号 | `test_supervision.py`（含 READY 前取消、重复取消、C 失联、S 故障/接管、FD/信号）；`test_execution.py` |
| AC17–18 | 新 `full/source_coverage.py` + `coverage-baseline.json` + `candidate-audit.json`；`library_source.py` 唯一 resolver（candidate 禁止源码回退）；`wfdrive`/`_harness` 委托 | `test_source_coverage.py`（67/85/54/31/10/3、逐 ID 脚本摘要/来源层/可安装执行性/不可迁移理由、audit 字节一致、未分组 31 ID、candidate resolver） |
| AC19–20 | `payload/install.py`/`bin/uninstall.py`/`scripts/wf-dev-deploy.py` 项目→基址→资产两层判定、锁内重算、历史 root_ref 拒绝；发行树重建 | `test_asset_boundaries.py`；contract `test_install_refuses_*` |
| AC21 | 全量 runner 串并等价、full both、candidate 证明 | 见 §2 |
| AC22 | 构建器重建 + 字节复现 + token parity；README/spec 同步 | `build-wf-release.py --verify`、`--verify-token-parity`；静态校验 |

## 2. 执行记录（本轮修复后）

| # | 命令 | 结果 |
|---|---|---|
| 1 | `python3 -m unittest discover -s scripts/tests -t .` | **1106 tests, OK (skipped=22), 32.1s** |
| 2 | `WF_SLOW_TESTS=1 python3 -m unittest scripts.tests.wf_runtime.test_run_all_contract` | **21 tests, OK, 197.6s**（含 cleanup-unknown 现场保留、candidate 代表、取消、三方边界、宿主终态清单） |
| 3 | `run_all.sh --full --repro green`（ext4 scope，证据留存） | **149 项，fail=0，72.74s，jobs=8，unshare，cleanup=cleaned**；证据 `evidence/final-ext4-green/summary.json` |
| 4 | `run_all.sh --full --repro green --serial`（ext4 scope，证据留存） | **149 项，fail=0，417.25s，jobs=1，cleanup=cleaned**；证据 `evidence/final-ext4-serial/summary.json` |
| 5 | 并行 vs 串行逐项对拍 | 64 个主池单元名称集合/rc/status 全同；85 个 repro 选择/模式/green/red/verified 全同；state schema=4；证据 `evidence/final-parity.json` |
| 6 | `run_all.sh --full --repro both`（ext4 scope，bind-run 修复后，证据留存） | **149 项，repro 85/85，fail=0，102.17s；state schema=4，85 case 同时有 green 与 red 证明；bind-run `[both]` 通过**；证据 `evidence/final-ext4-both/summary.json` |
| 7 | `run_all.sh --full --fixture-deploy candidate --repro green`（candidate 0.1.0） | **64 项（56 suite + 5 flow/extra + 3 repro），fail=0，41.73s，cleanup=cleaned**；证据 `evidence/final-candidate/summary.json` |
| 8 | candidate 逐 suite 审计（生成器：`python3 scripts/tests/wf_runtime/full/candidate_audit.py --tree docs/workflows/wf-release --version 0.1.0 --workdir <dir> --out scripts/tests/wf_runtime/full/candidate-audit.json`） | 59 suite 真实运行：**56 通过并提升 `candidate_clean=true`**。r67 是 fake-tree runner 技术审计（其 candidate 运行在模拟环境返回 plan/scope 错误，不作为断言失败）；r90（R93 追加平台资产）与 p5_v1（`[V1] 追加平台…: FAIL — False`）保留 dev-only，`candidate-audit.json` 记录 `rc`（命令退出）、`suite_rc`（目标进程退出）、`expected/observed` 与具体 `failures`。 |
| 9 | AC02 探针（真实 `run_all --list`） | 全新 scope 无新增文件；域外 `WF_PYCACHE` 返回 PATH-REFUSED 且域外目录不存在 |
| 10 | `build-wf-release.py --verify` | **OK  byte reproduction (0.1.0, 74 assets)** |
| 11 | `build-wf-release.py --verify-token-parity` | OK token parity（first=ok / after=expired） |
| 12 | `check-doc-refs.py` / `validate-wf-design.py` | 0 problem(s) / 七项检查 + 覆盖率断言通过（引用残差 2 行为既有口径） |
| 13 | `validate-skills.sh` / `trellis-library/cli.py validate --strict-warnings` | OK 25 skill(s) + spec cross-check / 退出码 0（仅既有 informational 警告） |

关键证据目录：本节所有计时/相位结论均复制到任务内小证据：

- `evidence/final-ext4-green/`、`final-ext4-both/`、`final-ext4-serial/`：`summary.json`、`lines`、
  `selection.tsv`、`repro-state.json`、`summary-metrics.json`；不再依赖会被 keep 轮转清掉的 scope。
- `evidence/final-candidate/summary.json`；`evidence/historical-tmp-green/summary.json`（66.28s）。
- candidate 审计文件 `scripts/tests/wf_runtime/full/candidate-audit.json`；覆盖基线
  `scripts/tests/wf_runtime/full/coverage-baseline.json`。

本轮收口已清理 34 个 `/tmp/wf-test-scope-*` owned scope（约 2019MB）；scope 是临时运行资源，
不随任务归档提交；可复核证据已复制到上述任务目录。

## 2.1 性能对照（有源）

> 更正（2026-11-16）：此前口头对照使用的 **61.3s** 是本会话临时测量、仓库内无可溯来源，已撤回，不作为基线。
> 基线改用上一任务（11-15）的存档冷并行墙钟 **52.8s**（total 50.79s）。

来源：
`.trellis/tasks/archive/2026-11/11-15-wf-runner-boundaries-followup/validation-2026-11-15.md:77`
（同机 owned scope、8 worker、cold、suite 59 / flow 5 / repro 85、149 项 0 失败）以及
`.../evidence/verification-2026-11-16.json:30` 的 `elapsed=52.8`。

本轮保留的 cold 并行证据是 ext4 **72.74s**，相对上一任务存档 **52.8s** 为 **+37.8%**；历史 tmpfs
scope 的 66.28s（+25.5%）也有 summary 留存，但两者存储/负载未做同轮 A/B，只作量级参考。
差异来源包括：每个命令新增 C→G→S→W 监督（进程/协议/最终核验）、公共 helper 身份摘要、
命令级 cleanup 聚合与更完整的审计/测试。ext4 串行 417.25s 是全新冷 scope，不能与存档 reused
release/template 的 268.2s 直接比较。该偏差已在 [prd.md](./prd.md) 的“实施结果与已登记偏差”
按本轮审查口径登记接受；若要求恢复原速，另立优化项，不能用跳过校验/降低覆盖换取。

## 2.2 P0 复核：bind-run red 的 readdir 顺序（已修复并复跑）

外部审查的 P0 成立：在 ext4 结果目录上复跑 `--subset --repro both` 时，`bind-run [both]` 的 red
相位失败（`注入缺陷后目标断言仍未变红`）。根因是 `bind-run.py` 的断言 ② 用未排序
`os.listdir()` 取任意 `object.id` 匹配的 runtime 侧车；旧会话 `sess-BR1` 的 `current_task` 正常，
readdir 顺序靠前时会掩盖 `sess-BR2` 的注入缺陷。

修复不是排序目录，而是**按会话 key 精确读取**：`bind-run.py` 新增 `session_key()`/`runtime_record()`，
断言只读 `sess-BR2` 的侧车；`test_repro_case_helpers.py` 构造“旧文件字典序更小且 current_task 正确”
的反例，证明不再依赖 readdir 顺序。修复后在 ext4 scope 复跑：

- `--subset --repro both`：85/85，bind-run `[both]` 通过；
- `--full --repro both`：149 项、85/85、fail=0、102.17s、cleanup=cleaned；
- `--full --repro green`：ext4 72.74s、full serial 417.25s，均 149/0。

## 3. 本轮修复的阻断/偏差

- **AC02**：`run_all.sh`/`repro/run.sh` 在校验前统一禁写 pyc 并丢弃外部 pycache 前缀；layout/scope
  通过后才启用批准的 pycache。修复了“域外 WF_PYCACHE 先被写入再拒绝”和“list 生成 pycache-bootstrap”。
  新测试真实调用 `run_all --list`，不再用域外 `PYTHONPYCACHEPREFIX` 掩盖问题。
- **R9 / AC17–18**：新增逐 ID 脚本摘要/来源层/可安装执行性/不可迁移理由/已安装断言；
  59 suite 真实 candidate 审计（`candidate_audit.py` 可复现生成），56 个提升；r67 按 fake-tree
  技术理由保留，r90/p5_v1 按具体失败断言保留；candidate full 实跑通过。
  注册单元仍 67，candidate_clean 分布更新为 57 true / 6 false / 4 未声明（详见 inventory 更新）。
- **证据身份**：`HELPERS` 纳入 `library_source.py`、`prepare_candidate_repo.py`、`release_context.py`、
  `results_gate.py`、`results_summary.py`、`fixture_scope.py`、`execute_gate.py`、`run_all.sh`、
  `wf_test_paths.py`；`helper_set=core-v2` 使旧公共输入集合的 bundle 被拒绝。
- **AC08**：新增 `runner_cleanup.py` 聚合命令级 cleanup；run_all 在 unknown 时保留夹具现场、summary
  记 unknown 并 GATE-FAIL；新增真实故障注入契约用例。
- **P1**：故障注入只在显式测试开关下生效；`inherit_output` 恢复控制台继承；kill 前核对 PID 启动
  时间；控制帧带 `id`；candidate `check` 恢复只读（不创建锁 sidecar）；取消先只向目标发信号。
- **P1 测试补口**：`test_supervision.py` 新增 READY 前取消（`WF_SUPERVISOR_READY_DELAY` 测试窗口）、
  重复取消、C 失联（SIGKILL C 后 G 经 EOF 回收）三个断言，覆盖 AC16 的协议窗口；C 收口预算
  默认从 12s 调整为 14s，覆盖 G 的 8s 取消宽限 + 5s 清理宽限，避免 C 先杀 G 得到 unknown。
- **P2**：candidate `check` 的 `git status` 统一带 `GIT_OPTIONAL_LOCKS=0`；新增测试核对
  `.git/index` inode/mtime/size 在 check 前后不变（只读声明与实际行为一致）。
- **P3**：`fixture_scope.prepare_results` 重置每 run 的 `.runner.json`，新增测试证明上一轮
  `cleanup_state=unknown` 不会跨轮污染本轮 cleanup 聚合（`.runner.json` 每轮重建）。
- **P4**：`implement.md` AC03 责任测试改为 `test_evidence_protocol::VerdictTest` + gate/writer；
  `test_results_gate` 增加“默认 bundle 路径与显式路径在成功场景同样可用”的直接断言；AC11 覆盖面补齐。
- **证据追溯/清理**：此前 72.67/414.66/103.74 的 ext4 scope 已被轮转/手动清理，数字无法复核；
  本轮重新跑并留存小证据，数值更新为 72.74/417.25/102.17；同时删除 34 个 owned `/tmp` scope（约 2019MB）。
- **卫生**：删除 `run_all.sh` 重复的 `TEMPLATE_BUILD_SEQUENCES` 计算块；`results_summary.publish`
  的 open/fsync/replace `OSError` 统一收敛为 `SummaryError`，main 不再裸 traceback。

## 4. 未直接执行 / 剩余边界

- 真实宿主压缩与 D1 人工验收：无法在脚本内合成，未运行，不登记为通过。
- 同 UID 恶意 TOCTOU、最后有效监督方丢失后的自动回收、宿主断电/内核不可回收对象仍是能力边界；
  `test_supervision` 覆盖 G 存活时 S 故障接管与 G 猝死时 S 侧清理，C 在 G 猝死时报告
  `cleanup=unknown` 与恢复步骤。
- candidate 的 3 个 dev-only suite 均有可复核记录：r67 的保留理由是 fake-tree runner 技术审计
  （`units.json` notes + `candidate-audit.json` 的运行记录），r90/p5_v1 是具体断言失败
  （`candidate-audit.json` 的 `failures`）。若未来要求它们进入 candidate，需要单独修断言/环境
  并用同一生成器更新审计文件；不能只改 `candidate_clean`。
