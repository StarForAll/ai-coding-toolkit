# repro/：修复的可证伪用例

每条已声明的修复配一个脚本，契约由 `_harness.py` 固定：

| 模式 | 做什么 | 期望 |
|---|---|---|
| `--expect green` | 在当前树上跑 check | 成立（退出 0） |
| `--expect red` | 把 payload 复制到临时目录，**注入"退回修复前"的那一处**，再跑同一 check | check 必须变红（退出 0 表示"如预期变红"） |

两者都过才说明：这条断言能区分"修好了"和"没修"——但只有 `TargetFailure` 能在 red 模式算通过，内部错误、前置失败、未归类字符串都不行（第十/十一轮复审）。只跑 green 的用例等于没有证据——
空断言、`expected == actual`、候选与规则不相交的空匹配、只记目录的快照，都会在 red 模式下原形毕露。

## 新增一条

1. 命名 `<批次>-<编号>-<短名>.py`，如 `f5-4-generation-bool.py`。
2. 用 `_harness.stage()` 拿临时 payload 副本；`WF_REPRO_INJECT=1` 时 `_harness.patch()` 注入缺陷。
3. `check()` 成立时返回 `None`；**目标断言被击中**时 `raise H.TargetFailure(原因)`；**夹具/环境/内部错误**时 `raise H.Precondition(原因)`。返回字符串已被视为未归类失败（两种模式都不通过）。
4. 跑 `--expect green` 与 `--expect red` 都要退出 0；`run_all.sh` 会自动汇总。

## 已知边界

- 只能证明"已声明的修复被验证过"，不能证明"没有未被发现的缺陷"。
- 注入点写死源码片段：实现改动后脚本会报 `repro stale`，必须同批更新，否则等于失效证据。
- 锁对象（`.wf-lock`）不属于写入产物，目录快照需显式排除。

## 一键运行（CI 可用）

```bash
bash scripts/tests/wf_runtime/full/repro/run.sh              # 默认 both、单并发，构建/复用测试发行缓存
bash scripts/tests/wf_runtime/full/repro/run.sh --no-build   # 已有新鲜缓存时校验并复用
bash scripts/tests/wf_runtime/full/repro/run.sh --only bind  # 只跑名字含子串的
bash scripts/tests/wf_runtime/full/repro/run.sh --list       # 列出用例
```

默认 both 模式退出码 0 只由 root controller 的最终投影给出（bundle/records/receipts/cleanup 全部核验后），
内层 `INNER-TARGET-OK` 不是成功出口；机器可读汇总为
`REPRO_TOTAL= / REPRO_PASSED= / REPRO_FAILED= / REPRO_GREEN_SECONDS= / REPRO_RED_SECONDS=`，
另有结构性事实 `REPRO_STRUCTURAL_OK= / REPRO_ELIGIBLE= / REPRO_BUNDLE_SHA256=`。`run_all.sh`
委托本脚本，并**一律**用 `--_wf-inherited-release` frame 交接已核发行身份（默认构建与
`--no-build` 都一样），内层不再 `ensure`/`check`/`check --json`。

CLI 级用例由运行器传入测试发行缓存或候选仓库；T1/T2 不重建产品发行树。通过本入口运行，避免直接执行单条脚本时借用旧发行。

## 双身份、冻结 bundle 与唯一 writer

- 身份分成两件：`execution_fingerprint`（case 输入 + 本次 tool/SUT、平台、部署、真实 release 根身份与
  candidate tag commit）与 `red_subject`（断言/注入脚本、helper、协议、source/targets/build 输入、tool/SUT、
  平台与 release **内容主体**；不含 deploy 标签与根路径）。green 只记前者，red proof 两者都记。
- `--mode auto`：dev 找同名主体的有效 dev red，否则 both；candidate 只对 candidate-clean 用例要求同主体
  **且**同 release 内容/version/ref/runtime 的 dev red，缺失即拒绝（出口是先在 dev 用同一内容跑 red/both）。
  candidate green 从不续签 red。未知 targets、旧 schema 1/2 状态都只算 both/legacy，不推导、不复用。
- 冻结来源只有一个 `inputs.json`（schema 2：execution_context + public_inputs + cases{mode,fingerprint,
  subject,local_inputs}），原子写一次；env 只传 `WF_REPRO_INPUTS_FILE`。worker/gate/writer 都读这一份并核摘要与长度。
  **公共输入只算一次**：source/helpers/executor/runner 在 freeze 由 `repro_select.public_inputs()` 一次算齐并
  冻结进 bundle；worker 只重算 case 局部输入（script/targets/case_meta）并比对 context；只读 gate 不重算任何
  公共摘要；唯一 writer 在最终 barrier 各重算一次 `public_inputs()` 与 `execution_context()` 并与冻结值比对，
  随后逐 case 只核局部输入与 subject。旧 schema 1 bundle 一律拒绝（每 run 产物，不迁移）。
- 拓扑（独立入口）：R 取租约/layout → `resource_lifecycle.begin-run(role=repro)` 写 schema2 owner +
  active run-state → root controller（同 C 进程，`execution.py --runner-control --runner-role repro`）
  监督发行准备与 worker/gate/writer → finalize → schema3 repro 投影 + run-state 终态，最后才输出
  `GATE-OK`。内嵌入口复用父 run_id/receipts/release context，不另起 controller、不发布父摘要。
- 命令证据：每个 phase `execution.run` 先写 receipt（managed→父/本 run `commands/<command_id>.json`；
  独立 API→log 同目录隐藏 sibling），相位 TMPDIR 在 supervision=cleaned 后回收，否则保留并在
  `retained_paths` 报告。只读 gate 不写 state；唯一 state writer 仍是 `commit-state` 子进程。
- candidate 最终 barrier 与直接 CLI/库调用的租约核验不变；candidate 的独立入口只调用 validator 一次
  （起始/结束由父 run 负责），内嵌入口不再重复校验。
- 状态 schema 3：`green` 与 `red` 相位独立；旧 1/2 只作 legacy 保留，未知/损坏不覆盖。

## 租约、测试域与 namespace

- R 先取 fixture → 当前域结果锁 → dev release 独占锁（均同 PID exec 持有）；独立入口才初始化发行，
  继承入口只 verify 并派生 locator。结果锁是**域**锁：生产 `/tmp/wf-test-results-<uid>.lock`，
  测试域 `<scope>/locks/results-<uid>.lock`，不为每 run 建 sidecar。
- 设 `WF_TEST_SCOPE_ROOT` 时，repro 的结果/pycache/state/cache 必须在 scope 内（独立入口对
  `WF_RESULTS_CACHE`/`WF_TEST_RUN_CACHE` 也过 `check-scope`；未注入时默认落在 `<scope>/cache`、
  `<scope>/state`）；`--list` 在一切租约、pycache 与状态读取之前纯选择退出。
- 测试专用注入点（默认值不变，不劫持 PATH）：`WF_TEST_RELEASE_CLI` 覆盖独立入口的测试发行 CLI、
  `WF_CANDIDATE_VALIDATOR` 覆盖候选校验（独立入口与 writer 最终 barrier 同一入口）。
- namespace 单元会关掉本 worker 的宿主 FD 副本并标 `WF_UNIT_DOMAIN=unit`：伪造的私有 `/tmp` 同名锁不会被
  当宿主锁；只有显式 scope 单元可以在自己 scope 内建测试锁。结果目录无主或符号链接时拒绝清理；
  日志、模式、退出状态与冻结 bundle 不一致都计失败。
