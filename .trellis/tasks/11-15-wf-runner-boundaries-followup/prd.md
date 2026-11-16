# 收口 wf 运行器隔离、恢复窗口与成本证据

## Goal

让上一任务（`.trellis/tasks/archive/2026-11/11-14-wf-runner-correctness-boundaries/`）已交付的运行器机制在**恢复完整性、测试隔离与成本账目**三条上闭环：修复 journal 恢复窗口缺陷，把慢契约测试真正关进 owned scope 并记账，消除 per-case 公共摘要重扫，补齐调用计数与硬化断言。不改产品语义、运行器门禁阈值与产品发行树。

## Background / Evidence

上一任务的 `validation-2026-11-15.md:38` 声称「公共身份不在 per-case 循环内」，与代码不符；以下为当前代码事实（本轮复核）：

- **恢复窗口缺陷**：journal 在移走旧代**之前**写入，但恢复要求 backup 存在。崩在两步之间时旧代仍在原位、恢复却 fail closed（已实测复现 `REFUSED`）。证据：[`wf_test_release.py:378-393`](../../../scripts/tests/wf_test_release.py)、[`template_cache.py:253-263`](../../../scripts/tests/wf_runtime/full/template_cache.py)。
- **契约测试仍触生产资源**：helper 只注入 `WF_RESULTS_CACHE`，不设 scope 与 `WF_TEST_RELEASE_CACHE`；`plan.py` 的测试发行根缺省回落到 `~/.cache/wf-test-release`。实际运行创建了 `~/.cache/wf-test-release/{0.1.0,0.1.2}`、`~/.cache/wf-candidate-repo/0.1.2` 与 `/tmp/wf-test-results-1000.lock`。证据：[`test_run_all_contract.py:22-36`](../../../scripts/tests/wf_runtime/test_run_all_contract.py)、[`plan.py:551-556`](../../../scripts/tests/wf_runtime/full/plan.py)。
- **AC17 无实现**：契约 helper 没有 `setUpClass` owned scope/共享 pool、没有每 case state/HOME、没有 900 秒分摊与 cold/warm/build/teardown 账目；summary 只有 `build_seconds/template_seconds`。证据：[`run_all.sh:711-760`](../../../scripts/tests/wf_runtime/full/run_all.sh)。
- **per-case 公共扫描**：`_case_inputs` 每次重算 `source_digest()`；worker 每 case 调 `execution_context()` 与两次 `input_fingerprint()`；writer 每 case 重算 `red_subject`。实测 `source_tree_digest`≈4.5 ms、单次 fingerprint≈66 ms。证据：[`repro_select.py:90-105,183-190`](../../../scripts/tests/wf_runtime/full/repro/repro_select.py)、[`_worker.py:80-108`](../../../scripts/tests/wf_runtime/full/repro/_worker.py)、[`repro_select.py:428-451`](../../../scripts/tests/wf_runtime/full/repro/repro_select.py)。
- **scope/unit 域硬化缺口**：`verify_results_lock` 对 `scope:` 域只拼路径、不验 marker；`namespace.py` 未清 `WF_TEST_RUN_CACHE`，而 state 路径由它决定。证据：[`fixture_scope.py:428-455`](../../../scripts/tests/wf_runtime/full/fixture_scope.py)、[`namespace.py:20-30`](../../../scripts/tests/wf_runtime/full/namespace.py)、[`repro_select.py:300-303`](../../../scripts/tests/wf_runtime/full/repro/repro_select.py)。
- **证据缺口**：V13 ensure/check 调用数、V16 namespace 宿主锁不变、V18 candidate 结束 barrier、AC16 三次重入/两次计划、AC1 HEAD 不可读、AC4 双工作区交替 miss、AC11 `--no-build`/并发、AC3 取消不泄漏锁、AC18 SUT 级 escape、README 精确清理口径。
- **当前基线**：T0 `961 OK (skipped 13)`；契约 `12 OK`；`--full --repro green` 并行/串行各 149 项 0 失败且逐项对拍相等。

## Requirements

### R1 — journal 恢复窗口完整

- 两个 cache 的恢复都先判「当前代是否仍等于 journal 记录的可验证代」：新代可验证则前滚；旧代仍在原位完好则视为回滚完成（只清 staging/journal，不要求 backup）；旧代已移走但 backup 可验证则按冻结旧字节回滚。
- 首次发布（old-absent）只撤销本事务不完整新代；两代都不可验证时保持 fail closed、保留现场并非零。
- 恢复判定不再依赖「当前输入新鲜度」，不比 mtime；旧代/新代均按 journal 记录的摘要与归属核验。

### R2 — 契约测试 scope 化与成本账目

- `RunAllContractTest` 单 class 一个 owned scope（marker 可验回）与空 pool 布局；每 case 独立 `state`，每调用独立 `results/fixture/pycache`；`tearDownClass` 先等子进程/FD 结束再回收。
  **HOME 保持宿主值**（2026-11-16 改签）：被测 SUT 依赖用户级执行器确认（`~/.wf/interpreters.json`）与 git 身份，A/B 实测把 HOME 指到 scope 内会让候选流程 `task-check` 退化成 `WF_CHECK_STALE`；假 HOME 会改变被测语义，因此隔离只施加在 runner 管理的写入口，用户 cache/生产结果锁靠快照断言证明未被触碰。宿主前置条件写进 README「宿主前置条件」段。
- 契约运行必须注入 `WF_TEST_SCOPE_ROOT`、scope 内 `WF_TEST_RELEASE_CACHE`、`WF_TEST_RUN_CACHE`、`WF_RESULTS_CACHE`，不创建/不修改生产结果锁与用户 cache。
- 计划/非法参数/拒绝路径零 warmup；取消探针显式 warmup 后计时；故障、冷建、旧 schema、stale、候选篡改使用 private pool，不污染共享池。
- 成本可报告：首个 dev 调用 `release_build=built`（发布器内部仍做 staging 双构建 + 字节复现，但只暴露状态与累计 `builds=1`，不宣称可观测的"build=2"）+ 模板缓存发布一次（`template_build_sequences=1`），同输入后续为 `reused`/0；candidate 不建 dev 发行（用 release CLI 计数 shim 断言 0 次调用）；记录 class/case 墙钟、cold/warm、build/模板状态、teardown 与 900 秒剩余、取消窗口余量。
- 一个逻辑 case 的 prepare/warmup/主请求共享 900 秒单调 deadline；日志等待 15 秒从 cache ready 起算，5 秒清理单列；失败显式归因，无 skip/加时/真人 cache。

### R3 — 公共摘要 barrier 化

- 公共输入（source、release subject、helpers、executor、runner、runtime）在 freeze 计算一次并冻结进 bundle；worker 只做 case 局部快检（script/targets）与 context 比对；只读 gate 不重算；唯一 writer 在最终 barrier 重算**一次**并与冻结值比对。
- 公共扫描次数不随 case 数增长；bundle schema 升级，旧 schema bundle 明确拒绝（不迁移、不兼容）。

### R4 — 证据与硬化补口

- 内嵌 repro 的 `wf_test_release` ensure/check/check-json 调用计数为 0，独立入口为 1；candidate validator 在起始与结束 barrier 各 1 次，坏候选不启动 worker。
- `scope:` 域必须通过 marker 校验才可作为继承锁；unit 域伪造 scope/生产锁被拒绝；namespace 单元不携带宿主 state locator；宿主锁 inode/持锁状态不变。
- 补齐 AC16 重入/计划计数、AC1 HEAD 不可读、AC4 双输入交替 miss、AC11 `--no-build`+并发、AC3 取消后可立即重取锁，以及 AC18 的 **SUT 级 escape** 可复跑断言。
  2026-11-16 收窄口径：AC18 的正式断言只覆盖"资产落点本身是指向项目外的符号链接"（`WF_ASSET_DECISION`、整批零写入）；
  "技能根目录是指向项目外的符号链接"这条产品当前会写穿（`WF_OK`），以命名清楚的 known-gap 测试登记为可复跑证据，
  修复需同时覆盖 `uninstall.py` 的同判据并走发行重建，属产品侧另行立项。
- 文档：README 给出只读列出条目（路径/meta/marker/大小/身份）与精确 owned 清理命令；新任务记录更正上轮「无逐 case 重扫」的失实声明（不改写旧记录原文）。

## Acceptance Criteria

- [x] AC1/R1：两个 cache 在「journal 后未移旧 / 移旧未装新 / 装新未 repoint / 未写 meta / meta 后未清 journal / 首次发布」各窗口都能自动恢复到可验证代；旧代原位完好的窗口不再 fail closed；两代不可验证仍保留现场非零。
- [x] AC2/R1：每个窗口有断言（tree digest、meta/owner 字节、journal 清理），失败窗口不删除旧数据。
- [x] AC3/R2：契约 class 结构（单 scope marker 可验回/空 pool/每 case state/每调用 results/fixture）、plan-only 零 warmup、teardown 无子进程/FD 遗留均有断言；`HOME` 保持宿主值并写明理由。
- [x] AC4/R2：契约运行前后生产结果锁 inode/mtime 与用户 cache 快照不变；scope 内 create/delete 可证；真实 CLI 的管理写全在 scope。
- [x] AC5/R2：首次 dev `release_build=built` 且 `builds=1`、模板缓存发布一次，后续同输入 `reused`/0；candidate 不建 dev（release CLI 计数 0）；private 故障不污染共享池；账目字段可读。
- [x] AC6/R2：900 秒 deadline 在子调用间递减、15 秒/5 秒窗口单列、超时/失败归因明确且不吞。
- [x] AC7/R3：freeze 一次、writer barrier 一次；worker/gate 不重算公共摘要；篡改公共输入被 barrier 拒绝。
- [x] AC8/R3：3 与 30 个 case 的公共扫描次数相同；旧 schema bundle 被拒绝。
- [x] AC9/R4：内嵌 ensure/check 计数 0、独立 1；candidate validator 起止各 1 且起始失败无 worker。
- [x] AC10/R4：伪造 `scope:` 域/生产锁被拒；namespace 单元无宿主 state locator；宿主锁 inode/持锁不变。
- [x] AC11/R4：AC16 计数、AC1 HEAD 不可读、AC4 双输入 miss、AC11 `--no-build`+并发、AC3 取消重取均有可复跑断言；AC18 的"资产落点越界"有正式断言，"技能根符号链接"有 known-gap 证据并登记为产品侧缺口。
- [x] AC12/文档：README 列出/清理口径可执行；新记录更正失实声明；T0/契约/定向/full green 与发行/设计/文档校验通过。

## Out of Scope

- 改产品 payload、正式发行树、运行器门禁阈值或用例期望数；D1 真宿主压缩自动化。
- 通用事务框架、LRU/后台回收器、把所有 suite scratch 改写到 scope。
- 任意 syscall 沙箱、同 UID 恶意 TOCTOU、断电级 durability。
- 产品侧"技能根目录符号链接写穿"的修复（`install.py`/`uninstall.py` 同判据 + 发行重建）：本任务只登记 known-gap 证据，另行立项。

## Open Questions

无阻塞问题。恢复判定、scope 分层、bundle 版本与计数注入点均由现有设计与代码约束确定；实现顺序见 `implement.md`。
