# 验证总账（A1–A6）

> 实施会话 2026-11-18；基线 `b84b1a56`；解释器 `/softwares/python/bin/python3 -B`。
> 本文件只汇总可复核事实；未运行项与能力边界如实注明，不以用例总数销账。
> 运行环境：作者仓库 + 自建 owned scope（`fixture_scope.py create-scope`），宿主 HOME/Git 语义保持；
> 生产结果锁与用户 cache 由契约快照断言未被触碰。

## 汇总

| 编号 | 命令/入口 | 结果 |
|---|---|---|
| V-T0 | `/softwares/python/bin/python3 -B -m unittest discover -s scripts/tests -t .` | **1272 OK, 34 skipped**（最后一次代码编辑后重跑） |
| V-CONTRACT | `WF_SLOW_TESTS=1 ... -m unittest scripts.tests.wf_runtime.test_run_all_contract` | **33 OK**（含取消、锁竞争、候选 barrier、metrics/摘要故障矩阵、模板/CES 真实入口） |
| V-FULL green（并行） | `run_all.sh --full --repro green` | GATE-OK；59 套件/5 流程/85 repro = 149 units，fail=0；63s；run_id=`1795002121280-1654803-dae0989337e1` |
| V-FULL serial | `run_all.sh --full --repro green --serial` | GATE-OK；同 149 units；305s；run_id=`1795002202142-1720414-1c8ce30251b4`；与并行逐 ID 对拍一致（1 条随机 task_id 尾部差异） |
| V-FULL both | `run_all.sh --full --repro both` | GATE-OK；149 units；73s；run_id=`1795002552114-1783980-39a41bcfde2b`；85 用例 green+red 均 verified |
| V-REPRO standalone | `repro/run.sh --mode green --group install --no-build` | GATE-OK；9/9；run_id=`1795002657224-1859034-e8b22525844c`；`summary.role=repro`、`repro_phase_counts.green=9/9` |
| V-KEEP | 同上 + `WF_REPRO_KEEP=1` | 非零 + GATE-FAIL；`REPRO_ELIGIBLE=` 空、9 个相位 `unverified`、无 proof 文件；相位记录 `retained-keep` + 真实保留路径 |
| V-CAND no-repro | candidate 0.1.0 + `run_all.sh --representative ... --repro none --serial` | GATE-OK；8 units；`candidate_commit=852c0620…`（= tag commit）；`repro_phase_counts` 全零 |
| V-CAND A/B | 同内容不同提交的候选 A/B 共用空模板缓存 | A 发布条目（install=`source_commit`=A）；B 首跑冷建（hit=0/sequences=1，install=B）；B 重跑命中（hit=1/sequences=0）；两条目 meta commit 各自正确 |
| V-META | full 与独立 repro 的 `--release-meta` 指向另一文件 | 两入口均 rc=2、指向 canonical sidecar、零结果目录；CLI canonical 覆盖冲突 env 正常（plan 期判定） |
| V-LIST | 干净 env（`env -i`，空 HOME/TMPDIR）`--list --fixture-deploy candidate` | rc=0，4 行输出，临时 HOME 零新增文件（零写入） |
| V-AUDIT | `candidate_audit.py --tree docs/workflows/wf-release --version 0.1.0`（自建 workdir） | 59 suites，3 个 dev-only（p5_v1/r67_tests/r90_tests）与覆盖基线一致；`candidate-audit.json` 由生成器重写，未手填 |
| V-RELEASE | `scripts/build-wf-release.py --verify --verify-token-parity` | OK token parity；byte reproduction 0.1.0（74 assets）；产品发行树与 HEAD 无差异 |
| V-DOC | `check-doc-refs.py`（任务工件/READMEs/`.trellis/spec/docs/wf-delivery-discipline.md`）、`validate-skills.sh`、`validate-wf-design.py`、`trellis-library/cli.py validate --strict-warnings` | 任务工件与 README 0 问题；`wf-delivery-discipline.md` strict 有 **14 个既存**“§x 缺所有者前缀”（HEAD 基线同样 14，非本轮引入）；skills 25 + spec cross-check OK；design 七项检查通过；library rc=0（仅 5 条既存 mtime 漂移 INFO） |

定向单元（新增/改动行为）：
`test_runner_protocol`（repro frame/validate_plan）、`test_repro_cli`（公开解析一次、read-plan token/scope）、
`test_repro_selection`（相位 receipt/清理/KEEP/部分通过/状态原子写/v4 legacy）、`test_results_gate`
（相位计数与 receipt 域）、`test_results_summary`（candidate_commit/repro_phase_counts 投影）、
`test_execution`（最终决策边界、C 拒绝先于取锁、候选终核漂移）、`test_test_release`（`--no-lock` 须有租约）、
`test_template_cache`（候选 commit 身份/缺 commit miss/旧条目不改名）、`test_execute_gate`（计划身份）、
`test_source_coverage`（审计重生成后字节一致）、`test_runner_hygiene`/`test_test_runner_plan`。

## A 总账

| 验收 | 结论 | 反例/正常证据 | 限制 |
|---|---|---|---|
| A1（R1） | 通过 | 锁：`test_controller_holds_the_release_lease_for_the_whole_run`（运行中同根 acquire=75，正常结束后可重获）；准备一次：契约计数（dev 1 次、内嵌 0 次、独立 1 次）；`--no-lock` 先 `verify_lease`（`test_test_release.NoLockLeaseTest`）；A/B 模板 + 终核：V-CAND A/B、`test_template_cache.CandidateCommitIdentityTest`、`test_execution.CandidateFinalCheckTest`；meta 冲突：V-META | 候选在一个 run *期间*被持久改写的注入点不存在（初核/终核之间无同步窗口）；跨 run 漂移由初核拒绝，运行期临时改写后恢复超出观测能力（设计稿 §2.2 已声明）。 |
| A2（R2） | 通过 | `test_repro_selection.ProofGateTest`（清理失败/KEEP/缺收据/错代/部分通过→不进 proof；成功用例写入 v5）；`test_state_write_failure…`（replace/临时文件/fsync 失败保持旧字节、无临时残留）；v4 legacy 不命中 auto、首次成功写入才转格式；KEEP 运行态 V-KEEP | 只覆盖已测的 I/O 故障点；断电级持久性不承诺。 |
| A3（R3） | 通过 | 取消标记由 C 交接、shell 只排他发布：`test_pre_published_cancel_request_is_kept_and_cancels_the_run`（字节+inode 不变、status=cancelled、无 proof）；干净启动不建标记（V-CONTRACT 子集用例）；最终决策边界：`test_execution.FinalDecisionTest`（屏蔽期间待处理信号、决策后改写不影响结论、已发布标记阻断成功）；`test_interrupting_root_runner…` 覆盖 C 收尾（cleanup=cleaned、evidence=incomplete、GATE-OK 不出现） | 内层 trap 的模态行为由 shell 代码与标记保全测试覆盖，未做进程组信号级单测；取消在准备阶段（早于 worker）由 C 以 `cancelled` 终态收口（代码路径，未单独注入）。 |
| A4（R4） | 通过 | 清单纯选择：V-LIST + `list_selection` 单测；计划身份反向：`test_execution.ControllerRefusalTest`（token/路径/role/run_id/结果根/schema/units 不符均在取锁前拒绝，`_prepare_release` 未调用）、`test_repro_cli.PlanHandoffTest`（read-plan token/scope/run_id 拒绝）、`test_execute_gate`（inner 身份不符拒绝）；摘要四字段：V-FULL/V-CAND/V-REPRO 逐字段核对（dev null、候选=tag commit、相位统计 planned=实际 bundle） | “内层拒绝启动 worker”的证明是 inner 入口在 mkdir/worker 前退出（代码顺序 + execute_gate/read-plan 拒绝用例），没有对 worker 启动计数做单独插桩。 |
| A5（R5） | 通过 | D1-3、R84 无绑定恢复、R67 3d、R65 R5、R62 P1-3、R76 1f、R82 A7c、P5 f0 均改为核实际返回值/记录/命令结果；新增/替换断言不改变 `units.json` expect；审计生成器重跑，3 个 dev-only 与基线一致 | R65/R62 的 schema 守卫核的是产品 `new_task_record`/`verify_step` 实际值；源码字符串类断言中未证明为空的保持原样（本轮只处理 A5 所列）。 |
| A6（R1–R5） | 通过 | V-T0、V-CONTRACT、V-FULL ×3、V-REPRO、V-CAND（含 A/B）、V-AUDIT、V-RELEASE、V-DOC；逐 ID 对拍：64 个单元行 rc/status 全同、85 个 repro 记录的 case/mode/verified/相位全同 | 未运行：宿主无 Git HEAD 的独立全量（契约 `test_unreadable_head…` 覆盖 dev 模板回退）；`check-doc-refs` 的 14 个既存问题未在本任务修复（非本轮引入）。 |

## 关键不变式（逐项核对）

1. 每个整次 run：`summary.run_id == .runner.json.run_id == run-state.run_id`（V-FULL ×3、V-REPRO、V-CAND 均成立）。
2. `units_total == suite_ran + flow_ran + repro_ran`；V-FULL `59/5/85=149`。
3. repro 相位统计：`planned` 来自冻结 bundle，`passed+failed+unverified == planned`；未报告相位为 0（V-FULL green 的 red=0/0）。
4. 候选成功摘要必须有 `candidate_commit`，且等于 validator 核实的 tag commit（V-CAND）。
5. 失败/取消 run 不写 proof、不出现 GATE-OK；真实清理事实保留在 `.runner.json.cleanup`，失败 run 的 run-state 不写 finished-cleaned（故障矩阵）。
6. 取消标记：干净启动不存在；已存在时字节与 inode 不变，且由 C 消费为终态（V-CONTRACT）。