# 设计：恢复窗口、隔离账目与 barrier 化

## 1. 边界与不变量

- 只改 authoring runner 与测试/文档：`scripts/tests/wf_test_release.py`、`scripts/tests/wf_runtime/full/**`、`scripts/tests/wf_runtime/test_*.py`、两份 README、`.trellis/spec/docs/wf-delivery-discipline.md`。
- 不变量沿用上一任务：产品语义/发行树不变；锁序 fixture → results → release；内部 frame 唯一编解码；state 唯一 writer；scope 不是 syscall 沙箱；不新增 LRU/通用事务框架。
- 本任务的「完成」由行为断言与账目证据定义，不由「命令能跑」定义。

## 2. R1：恢复状态机（两 cache 各自实现，判定形状一致）

journal 的 `new.digest = None` 表示新代尚未确认（repoint/meta 之前写入），见 [`template_cache.py`](../../../scripts/tests/wf_runtime/full/template_cache.py) 与 [`wf_test_release.py`](../../../scripts/tests/wf_test_release.py) 的发布序列。

恢复时按**固定顺序**判定，任一命中即执行并结束：

| 优先级 | 条件 | 动作 |
|---|---|---|
| 1 | `new.digest` 非空，且 `staging` 或 `entry/root` 的 tree digest == `new.digest` | 前滚：必要时备份旧代→安装新代→写 meta/owner→核验→清 journal |
| 2 | `old.present` 且 `entry/root` 的 tree digest == `old.digest` | 旧代原位完好：删 staging，删 journal，回滚完成（**不要求 backup**） |
| 3 | `old.present` 且 `backup` digest == `old.digest` | 按 journal 冻结的 meta/owner 字节回滚 |
| 4 | `old.present == false` 且 entry/root 不存在或不完整 | 首次发布撤销：删 staging/backup/journal |
| 5 | 其余（两代都不可验证、backup 缺失且原代已变、journal schema/root 不符） | fail closed：保留现场、非零、给出路径 |

- 判定 2 是本任务修复的核心：此前 `_restore_old` 直接要求 backup，导致「journal 已写、旧代未移」窗口被误判不可恢复。
- 判定 4 也必须覆盖「entry 已存在但不完整」：只删本事务可确认的新代，不碰 sibling/unrelated 路径。
- 比较一律用冻结摘要与归属，不用 mtime/当前输入新鲜度；meta/owner 恢复用 journal 里的原文，不重新序列化。
- 代码落点：抽出模块内 `_recovery_action(entry_or_root, journal)` 纯函数供恢复与测试共用；发布路径不变（仍先写 journal 再移旧），只修恢复。两模块各自持有 owner/validator，不合并。

## 3. R2：契约测试的 scope、pool 与账目

### 3.1 结构与注入

`RunAllContractTest`（[`test_run_all_contract.py`](../../../scripts/tests/wf_runtime/test_run_all_contract.py)）改为类级夹具：

- `setUpClass`：`fixture_scope.create_test_scope()` 建 owned scope；只建空布局 `pool/results-cache/template`、`pool/test-release`、`cases/`、`private/`；不 import 时构建。
- 每个测试 case：`cases/<case>/{state,home}`；该 case 的多次调用共用 `state`（dev red→candidate auto），不跨 case 共享。
- 每次 runner 调用：`cases/<case>/calls/<n>/{results,fixture,pycache}`；fixture 根由 `WF_FIX` 指定，默认也在 scope。
- env 注入（缺一即失败，helper 断言）：`WF_TEST_SCOPE_ROOT`、`WF_TEST_RELEASE_CACHE=<scope>/pool/test-release`、`WF_RESULTS_CACHE=<scope>/pool/results-cache`、`WF_TEST_RUN_CACHE=<case>/state`、`HOME=<case>/home`、`WF_PYCACHE=<call>/pycache`、`WF_RESULTS_DIR=<call>/results`。
- `tearDownClass`：先等 class 下所有 Popen/FD 结束，再 `fixture_scope.remove(scope)`；残留子进程即失败。
- 生产隔离断言：调用前后对 `~/.cache/wf-test-release`、`~/.cache/wf-test-run`、`~/.cache/wf-candidate-repo` 做快照（存在性+inode/mtime），并记录 `/tmp/wf-test-results-<uid>.lock` 的 inode/mtime；不变即通过。生产路径「禁止访问/busy 桩」保留在单测层（现有 `TestScopeTest` 的 stub 方式）。
- 需要真实 git 仓库的用例（candidate）物料放 `private/<case>`，不进共享 pool。

### 3.2 warmup / 故障 / 计划

- plan-only、非法参数、拒绝路径：只建 scope 与必要目录，**不 warmup**、不预建 test-release/template。
- 取消探针：同一 case 先显式 warmup 一次（走真实 ensure/模板命中并断言退出 0），失败按阶段报错；随后才开 15 秒日志窗口。
- 冷建、stale、旧 schema、发布故障、候选篡改：`private/<case>/<call>` 独立 cache/candidate。

### 3.3 成本账目与 deadline

- `CaseBudget`：`deadline = monotonic()+900`；每个子进程 `timeout = min(剩余, 既有上限)`；剩余为 0 直接失败并归因「case deadline exhausted」，不重置。
- 记录到 `evidence/class-cost.json`（contract 测试可读）：`class_seconds`、每 case `seconds`、每调用 `cold/warm`、`release_build_sequences`、`template_build_sequences`、`teardown_seconds`、`deadline_remaining`、`cancel_log_wait_seconds`、`cleanup_seconds`。
- 生产侧账目：`run_all` summary 增 `release_build`（`built|reused`，来源：`wf_test_release --ensure --json` 的 `status`）与 `template_build_sequences`（cache 命中=0，否则=1）；两 cache meta 增累计 `builds` 供诊断（additive 字段，读取方不依赖）。

## 4. R3：公共摘要 barrier 化

### 4.1 bundle schema 2

```text
{ "schema_version": 2,
  "execution_context": {deploy, release_subject, release_root_identity,
                        candidate_commit, runtime, platform},
  "public_inputs": {source, helpers, executor, runner{...}},
  "cases": { "<case>": { mode, execution_fingerprint, red_subject_digest,
                         local_inputs{script, targets, case_meta} } } }
```

- `schema_version != 2` 一律拒绝（bundle 是每 run 产物，不做迁移）。
- 公共输入唯一产生点：`repro_select.public_inputs()`；`execution_context()` 保持现有字段；`red_subject/input_fingerprint` 改为 `(case_local, public_inputs, context)`。
- freeze barrier：`select()` 调一次 `public_inputs()` 与一次 `execution_context()`，写 bundle。
- worker：读 bundle；只重算 `local_inputs`（script/targets/meta）与 context 摘要比对；不重算 source/helpers/executor/runner。
- gate：只读 bundle 与结果，不重算任何公共摘要。
- writer barrier：重算**一次** `public_inputs()` + `execution_context()` 并与 bundle 比较；随后逐 case 只核 `local_inputs` 与 subject 派生值。

### 4.2 计数与验证

- 模块级 `scan_counts = {"source":0, "release":0, "helpers":0}`，`reset_scans()/scans()`；`source_digest/release_context/helpers_digest` 自增。仅测试读取，不进 bundle/状态。
- 断言：3 与 30 个 case 的 select+commit 流程中 `source/release` 计数相同（各 1/1）；worker 直跑后计数不变。

## 5. R4：证据注入点与硬化

### 5.1 调用计数（测试专用、默认不变）

- `run_all`/`repro` 通过 env 可覆盖外部 CLI 路径：`WF_TEST_RELEASE_CLI`、`WF_CANDIDATE_VALIDATOR`（默认取现有绝对路径）。契约测试把它们指向计数 shim（记录调用后 exec 真实脚本），断言内嵌=0、独立=1、candidate validator 起止各 1。
- 不用 PATH 劫持（会改变被测语义）；shim 只包一层 argv 记录。

### 5.2 阶段/计划计数

- `run_all` 在每个 stage 入口向 `$RESULTS_DIR/stages` 追加一行 stage 名；`plan.py` 真正计算计划时（非 `--plan-file`）向 `$RESULTS_DIR/plan-calls` 追加一行。仅当 `WF_RESULTS_DIR` 可写时写，失败不阻断。
- 契约断言：一次真实 run 的 stages = `public,lease,controlled,execute`（4 条 = 3 次脚本重入），plan-calls = 2（preflight + final）。

### 5.3 scope 与 namespace 硬化

- `verify_results_lock`：`scope:` 域必须 `read_scope(scope_path)` 成功，且该 scope 等于当前 `WF_TEST_SCOPE_ROOT`（无 scope 时拒绝 scope 域，除非显式继承生产域）。
- `namespace.py` 增加清理 `WF_TEST_RUN_CACHE`、`HOME` 派生状态 locator 与任何 state 路径变量；保留 per-unit 委派输出。
- 测试：unit 域伪造 `scope:/tmp/x` 锁被拒；真实 `unshare` 下宿主结果/发行锁 acquire/verify 拒绝，宿主锁 inode/持锁状态不变（无 `unshare` 能力时显式 skip 并记录原因）。

### 5.4 其余补口

- HEAD 不可读：`common.git_head/git_describe` 支持 `WF_GIT_BIN`（默认 `git`）；契约用失败 shim 断言走 run-owned、且模板缓存目录无新增。
- 双输入交替 miss：template_cache 单测以 patched inputs 交替 A/B，断言两次 lookup 都 miss、同 slot 只保留最新一次发布、其他槽保留。
- `--no-build`+并发：契约跑 `--repro-concurrent --no-build`（预置新鲜 release）断言仍走 inherited frame 且成功；candidate `--repro red|both` 在 plan 层拒绝。
- 取消后可立即重取锁：契约中断根 runner 后在 scope 内立即 `<scope>/locks/results-<uid>.lock` + fixture lease 获取成功。
- AC18 SUT escape：scope 内 fixture + outside 兄弟目录，`install.py` 对 outside symlink 目标返回 `WF_PATH_INVALID` 且 outside 无输出。
- README：给出只读列举（`find <cache> -maxdepth 2` + meta/marker 身份/大小）与清理（`fixture_scope.py remove <精确 owned 路径>`，先核 marker/meta.root，无 glob/rm -rf）两段可执行口径。

## 6. 兼容性、风险与回滚

- bundle schema 2 与 worker/gate/writer/selector 同批切换；旧 bundle 属每 run 产物，拒绝即可。meta 新增字段 additive，旧读取方忽略。
- 契约 class 化会让慢测试首次变慢（cold 构建）并把状态显式化；不得用 skip/加时/真人 cache 换取速度。
- 新增 env 注入点（CLI 路径、`WF_GIT_BIN`、stage 日志）默认值保持现有行为；它们只在测试中使用。
- 回滚点：R1 修复独立可回退；R2 contract helper 与 R3 bundle 改动需同批回退（否则 worker 与 selector 版本不一致）。
- 明确不承诺：同 UID 恶意伪造、断电 durability；`unshare` 不可用时 namespace 行为记未覆盖而非跳过不提。
