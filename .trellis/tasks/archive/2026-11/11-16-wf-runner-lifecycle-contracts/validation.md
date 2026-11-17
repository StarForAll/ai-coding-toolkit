# 父任务验证总账（AC01–20）

> 实施会话 2026-11-17；基线 c0c3a167；解释器 `/softwares/python/bin/python3 -B`。
> 本文件只汇总可复核事实；逐项反例/正常/限制明细见三个子任务 validation：
> [C1](../11-17-wf-runner-cli-contracts/validation.md)、
> [C2](../11-17-wf-runner-controller-lifecycle/validation.md)、
> [C3](../11-17-wf-runner-cache-maintenance/validation.md)。
> 未运行/能力边界如实注明，不以测试总数销账。

## 最终组合验证（父实现 §2）

| 编号 | 命令 | 结果 |
|---|---|---|
| V-T0 | `/softwares/python/bin/python3 -B -m unittest discover -s scripts/tests -t .` | **1223 OK, 32 skipped**（最后一次编辑后重跑） |
| V-CONTRACT | `WF_SLOW_TESTS=1 ... -m unittest scripts.tests.wf_runtime.test_run_all_contract` | **31 OK**（含初始化真死亡、controller/finalize/摘要/metrics 故障矩阵、取消、模板事务真实入口、candidate barrier） |
| V-FULL green | `run_all.sh --full --repro green`（父任务 start 后重跑） | GATE-OK；59/5/85（149 units），cleanup=cleaned，evidence=complete；run_id=1794929758413-158671-c4b9a025142e |
| V-FULL serial | `run_all.sh --full --repro green --serial`（父任务 start 后重跑） | GATE-OK；59/5/85；run_id=1794929823789-222627-8d3f16059948 |
| V-FULL both | `run_all.sh --full --repro both`（父任务 start 后重跑） | GATE-OK；59/5/85；run_id=1794930135481-285405-50bcaad1ef67；repro green+red verified |
| V-CANDIDATE | prepare_candidate 0.1.0 + `run_all.sh --full --repro green --fixture-deploy candidate ...`（父任务 start 后重跑） | GATE-OK；56/5/3（64 units）；run_id=1794930220800-360520-5c285900c090；candidate-clean 过滤未改声明 |
| V-RELEASE | `scripts/build-wf-release.py --verify --verify-token-parity`（TMPDIR 在 scope 内） | OK token parity；byte reproduction 74 assets；first=ok/after=expired |
| V-DOC | `check-doc-refs.py`（任务工件+默认文档+实际改动的 README/spec）、`validate-wf-design.py`、`validate-skills.sh`、`trellis-library/cli.py validate --strict-warnings` | 任务工件/README/default/design/skills/lib 均 0；`wf-delivery-discipline.md` strict 有 **14 个既存**“§x 缺所有者前缀”（HEAD 基线同样 14，非本轮引入），default 检查通过 |
| 审计重生成 | `candidate_audit.py --tree docs/workflows/wf-release --version 0.1.0`（自建 workdir） | 59 suites，3 个 dev-only（p5_v1/r67_tests/r90_tests）与基线一致；audit 由生成器重写，未手填 |

对照口径：逐 ID 比较 `lines` 的 name/rc/status、repro case/mode/green/red/verified 与各 run 的
`.runner.json`/`run-state.json`/`summary.json` 归属（run_id 自洽），不以总数/耗时证明等价。
V-FULL 三次运行的 `units_total=149`、`fail=0` 与 cleanup/evidence 状态一致；repro both 的 85 用例
在两相位均 verified。

## AC 总账

| AC | 结论 | 反例/正常证据 | 限制 |
|---|---|---|---|
| 01 | 通过 | 结构缺失/矛盾→unknown、cleaned 终态证明、缺文件不默认 cleaned：`test_runner_cleanup.AssessExecutionTest/ChildrenTest` | 不覆盖内核不可回收对象 |
| 02 | 通过 | 真实 root 的 assess/finalize 异常变体均非零且无成功；`delete-after-first` 报告部分完成；`test_controller_and_finalize_faults_never_sign_success` | 需测试开关+scope 才注入 |
| 03 | 通过 | 每命令先写 receipt；standalone/managed/root 三域；写失败不启动目标；scope 越界拒绝：`test_execution.EvidenceTest` | 无 scope 的相对 log 固定调用者 cwd |
| 04 | 通过 | 模板 W1–W5 真 checkpoint→acquire 恢复；测试发行 W1–W5 ensure 恢复；`test_template_cache.CheckpointTest`、`test_release_maintenance` | 断电级持久性不承诺 |
| 05 | 通过 | 只读 lookup/check 遇 journal 返回 recovery-required 不写；无 journal 不按名字删：`LookupJournalTest`、`test_release_lock.test_pending_journal...` | 需要独占锁才能恢复 |
| 06 | 通过 | F1：材料清完前不删 journal；删除失败保留 journal；坏 key 完整 reset 后同 key 重建：`FinishFailureTest`、`test_inventory_flags_bad_journal...` | — |
| 07 | 通过 | normal/failed/cancel/exception/复用/轮转共用判定；未知不提前删除；`live_references`/receipts；`test_supervision.DeterministicFaultPointTest`、worker 相位 TMPDIR 测试 | 只覆盖同 UID 可见引用 |
| 08 | 通过 | 确定性 G/S 固定点（before-ready/after-started/guardian-after-started）+ ready 管道；目标环境剥离选择器；W 真实派生进程被回收 | G/S 同时消失仍 unknown |
| 09 | 通过 | 初始化三 checkpoint 真死亡→下次入口拒绝→锁释放；取消后 controller 仍 finalize；KEEP/未知不自动复用（prune/classify 测试） | — |
| 10 | 通过 | delete-after-first 精确 removed/failed/not-attempted；单根 rmtree 部分失败保 marker；teardown 证据写失败可见且保留 scope（`write_class_cost`/`should_keep_scope` 用例） | 首次失败即停、不重试 |
| 11 | 通过 | 旧 parser 缺值死循环（timeout 124）→ 新 parser rc=2；每有值选项 missing/empty/next-option/`=` 形态零副作用 | 见 C1 validation |
| 12 | 通过 | 内部 frame 仍由 runner_protocol 先剥离；单位/根 frame 字段核验；`--list` 与 `--mode` 冲突拒绝 | 未来新增选项须同批登记 |
| 13 | 通过 | lines×plan→gate；controller 发布前核 metrics/plan/context/lines/units/repro；缺/漂移不签成功：`test_results_summary`、metrics faults | 时间测量不是精度承诺 |
| 14 | 通过 | schema3 原子写→fsync→replace→全对象读回；发布/读回/清理失败非零且无 GATE-OK；metrics 旧/截断/错 ID 拒绝 | — |
| 15 | 通过 | 新 helper/字段进入登记/证明身份/fake tree；candidate-audit 重新生成；README/spec 与 owner/处置文案同步 | 容量未测量单列 |
| 16 | 通过 | 计划/per-case/内嵌零 observe；真实 root 恰一次（结果缓存/模板/测试发行根去重）；activation 分支未改平台配置 | — |
| 17 | 通过 | 历史盘点：legacy/unowned/active/unknown/JOURNAL/unproven 分类；safe-legacy 严格归属；manual 额外 TTY+摘要；重置后重建：各 inventory/retire 测试 | 非本 UID/不可读进程按拒绝 |
| 18 | 通过 | 整批预检失败零删除；报告先建；删除/报告部分失败停止并重盘点；新报告幂等重试；旧现场不因换新路径计处置 | unproven 风险按 R10 已确认范围 |
| 19 | 通过 | 模板 W1–W5 从 run_all 重入；发行 W1–W5 从 ensure 重入；F1/O1；开关关闭/越界拒绝；后代收口 | 断电/内核边界 |
| 20 | 通过 | owner2/state1/receipt1/unit_execution1/metrics1/summary3/审计字段的 producer→reader；registry 供 prepare/prune/bootstrap/inventory/retire；无主新协议不绕 bootstrap | 逐步消费者清单见 C3 validation |

## 交付前复核

- `git status` 只含本任务路径（5 个新文件：`full/repro/cli.py`、`full/resource_lifecycle.py`、
  `test_repro_cli.py`、`test_resource_lifecycle.py`、`test_release_maintenance.py`，以及修改的
  实现/测试/README/spec/audit）与四个任务目录；
  无 `.relative.log*` 等测试残留（发现并修正后清理）。
- 真实存量：未删除用户 `~/.cache/wf-test-*`、生产结果锁、正式发行树；所有真实 root 调用使用独立 scope。
- 未授权提交：按要求停在“等待用户批准后提交收尾”。


## 激活与状态记录（2026-11-17）

- 实际实施会话：DSH **inline**；`.trellis/config.yaml` 的 `dsh.dispatch_mode: inline`，运行时加载
  `in_progress-inline` 横幅，主会话直接实现/检查、不派发子agent。四任务 8 份 JSONL 有意为空，
  符合 activation.md 的 inline 分支；未伪造 dispatch 清单，也未把审查者平台当作本会话平台。
- 分支均为 `main`；三个子任务与父任务均用 `task.py start --allow-empty-context` 在 DSH inline
  下激活。父任务此前停留在 planning；本轮修正先 `task.py start` 父任务（in_progress），随后在同一
  未改代码树上重跑 full green/serial/both 与 candidate，避免把“父任务 planning 下产出的集成结果”
  当成最终证据；提交与 finish-work 仍未执行，等待用户批准。
- 复审中确认另一份审查把 DSH 一概当作“dispatch 平台”是不准确的：本仓库显式配置为 inline，
  dispatch 分支只在 `dsh.dispatch_mode: auto` 或 ZCode 等 dispatch 会话成立；activation.md 已补
  DSH inline 行并保留 dispatch 条件，避免未来把 inline 事实写成 dispatch 豁免。

## 复审补记（2026-11-17 第二遍）

在按最新文件逐条复核设计文档第 4.3、5、5.1、5.2、6 节后补正了实现缺口并重跑相关检查：

- 模板成功事务的 staging/backup **兄弟 marker** 之前未随树回收；现在 `_finish/_undo_first_publication`
  按“树确认不存在后再移除 marker”处理，并删除首次发布撤销时的新代 meta。新增反例断言保证
  重发布后无 `.staging-*/.backup-*` 残留。
- 有效模板 entry 之前可被 `safe-legacy` 选中；现已拒绝，只允许 `manual-retained`/正常替换；
  entry 退役同时移除正式 `.meta.json`，测试断言重建前 meta 已消失。
- 坏 journal 的 cache-key reset 现在要求同 key 的 entry/材料/journal 整组选中；新增测试拒绝
  “只删 journal 留下 staging”的半组选择。
- 结果 selection/report 也加上 scope 内约束，与模板/发行维护入口一致。
- `run_all` 之前只依据 records/assess 诊断，**repro 入口自身 rc（如唯一 state writer 失败）**
  未阻断内层成功出口；现在 `repro_rc != 0`（含并发 counters 缺失）计入 `STRUCTURAL_FAIL`。
  新增真实 root 测试：把 state 目录设为只读，断言 `REPRO-INNER-FAILED` 且无 GATE-OK。
- 观察适配器之前调用深层 inventory（算树摘要），且未输出 `observed_at`；现在模板/发行 observe
  改为真正浅层（直接子项、控制 JSON ≤1 MiB、不跟链接、不递归），`--no-template-cache` 不扫描
  未使用模板根，单根读取失败只作诊断；新增“mock tree_digest 抛错仍成功”和坏 journal/孤儿
  只读计数测试。
- 测试发行恢复前的 journal 内部 `staging/backup` 路径校验补齐（canonical root/名字前缀/父目录），
  防止 journal 指向根外。
- `candidate-audit` 生成环境显式清除全部事务/初始化/执行故障选择器。

最终命令与结果：T0 **1223 OK/32 skipped**；V-CONTRACT **31 OK**；full green/serial/both 均
GATE-OK（59/5/85，149 units）；candidate full green GATE-OK（56/5/3，64 units）；V-RELEASE OK；
V-DOC 任务/README/default/design/skills/lib 0（spec strict 14 条与 HEAD 基线相同）。
