# 实施与验收计划

已获用户批准并于 2026-11-19 启动；本会话 inline 实施，提交/收尾等待用户再次同意。

## 顺序

1. 复核实际发行调用、每个固定 `/tmp` 读写及仓库内消费者。在现有契约测试中为 A1–A4 落下正负对照。
2. 收口发行来源及次级夹具。逐条确认测试断言对象是发行资产、作者工具或合成参数，明确该断言归属的候选或 dev 分母及唯一验证位置。
3. 收口增量审计身份和运行。验证未知选择在运行套件前拒绝、拒绝后原报告字节不变。起始与结束核对候选身份和公共 helper/source 摘要。待代码稳定后，当前正式发行执行全量候选审计，输出到新的 owned scope，核齐所有 ID 和状态后更新受跟踪报告。仅在套件集合元数据实际变化时更新 coverage baseline。
4. 扩展 `execution.py` 命令接口，由 `run_one.sh` 为 fixture/init/suite 提供收据绑定的 `--local-tmp-root`。命令 ID 派生真实 TMPDIR。先确认本次 results 路径在 namespace remount 后仍可达。迁移套件自造决策、日志、报告和暂存发现路径，逐项说明保留字面路径的断言对象。
5. 分开 assertion、证据结构和 cleanup 三个字段。按完整、失败、结构不足、监督/本地回收失败及早期准备失败检查 full、独立 repro、摘要、历史读取和 prune。

## 核验矩阵

| 对应验收 | 入口与对照 |
| --- | --- |
| A1 | 在新的慢契约中用 build(version, destination_root) 于 owned scope 生成临时 0.1.1 树及候选仓库。WF_CANDIDATE_VALIDATOR 包装器追加 --tree <scope 临时发行树>。CP5 F2 的 dev/candidate 安装使用同一 legacy scaffold，比较 .trellis/README.md、NOTES.md、原始 Git commit、候选 installation.json 及 .wf/lib 来源等 B1/B2 前置，不比较预期不同的 release metadata。核 f1_init.py 与 CP5 断言在 candidate F2 上通过。再跑真实 candidate 代表集和全量、当前发行 candidate 代表集及 dev full。候选安装若破坏原始项目数据或目标断言前置，保留 candidate failure，不自动降级资格。 |
| A2 | test_candidate_audit、test_source_coverage 覆盖同身份增量、版本与同版本异树、helper/runtime/tree 输入变化、保留行过期、旧格式、--only 空字符串、argparse 缺值、未知/混合 ID 和拒绝后的原字节不变。无 --only 的正常全量入口仍运行全部单元。candidate-clean ID 全部 ok；non-candidate bad 有具体验证依据并处于排除项。 |
| A3 | 将仓库根通过 owned scope 下的路径 alias 暴露为 /tmp/<scope>/repo，以 WF_TOTAL_JOBS=2、WF_SUITES=r70_tests 真实运行 alias 下的 run_all.sh，触发现有 repository-under-tmp 自动串行分支。核 summary.fallback_reason、execution_mode、unit 记录和 local-tmp 收据，再用真实仓库路径、同输入及 --serial 对拍。不 mock can_unshare、不劫持 PATH。对 R70 伪确认/notes/main review、f1 init 决策、CP5 的 cp5_a/cp5_notes/cp5_ext、R69/R72/R35/R89 release-repo fallback、R47 外部目标建立旧值对照。test_unit_temp_paths.py 扫描可计划脚本与登记 helpers 的绝对 /tmp literal，未分类项失败。候选/发行/template cache 仍只读复用，锁身份正确且字节不变。 |
| A4 | test_results_gate、test_runner_cleanup、test_results_summary、test_repro_selection 和真实入口契约分别构造 prep-failed、target_rc 非零但无完整断言、完整 PASS+FAIL 计数、无 FAIL 的短输出、缺失/错代/冲突 receipt。每种来源覆盖 cleanup=cleaned/unknown/failed。目标断言失败要求 execution.verdict 认可的显式 FAIL 和完整断言计数。核查 bad aggregate 与 assertion/preparation/execution/unverified 分类互不混淆，summary.unit_outcomes 和 failure_owner typed counts 与旧聚合字段一致。repro unverified 不写 proof。旧摘要读取及 inventory/retire 合同保持有效。 |

### 全量审计命令

在任务创建的 owned scope 中，将 `WF_TEST_SCOPE_ROOT` 指向该 scope，再以同一发行树准备并核验候选根。以下命令用于真实逐 ID 审计，不由单元测试的合成 fixture 代替。

```bash
WF_TEST_SCOPE_ROOT=<scope> /softwares/python/bin/python3 -B scripts/tests/wf_runtime/full/prepare_candidate_repo.py \
  --tree docs/workflows/wf-release \
  --version <当前 wf-release.json version> \
  --out <scope>/candidate/<version>
WF_TEST_SCOPE_ROOT=<scope> /softwares/python/bin/python3 -B scripts/tests/wf_runtime/full/candidate_audit.py \
  --tree docs/workflows/wf-release \
  --version <当前 wf-release.json version> \
  --candidate-root <scope>/candidate/<version> \
  --workdir <scope>/candidate-audit-work \
  --out <scope>/candidate-audit.json
```

临时 `0.1.1` 树只由 A1 慢契约通过 `build(version, destination_root)` 在 scope 中产生。正式审计的 `--tree` 与候选根必须是同一输入及版本。只有全量命令涵盖全部登记的可计划 ID、所有 candidate-clean ID 都为 ok、dev-only bad 均有具体断言且不进入候选分母，才将 scope 输出复制到受跟踪的 `candidate-audit.json`。CLI 的 `bad>0` 本身不代表失败，因为已知 dev-only ID 预期会 red。缺行、未解释 bad 或身份不一致保全旧工件并报告失败。

```bash
/softwares/python/bin/python3 -B -m unittest scripts.tests.wf_runtime.test_candidate_audit
/softwares/python/bin/python3 -B -m unittest scripts.tests.wf_runtime.test_source_coverage
```

批准后执行公共检查。完整候选审计使用上方的隔离命令。现有开发全量入口明确验证 dev 模式，不能由候选运行替代。结果使用本次 scope 证据。

```bash
/softwares/python/bin/python3 -B -m unittest discover -s scripts/tests -t .
WF_SLOW_TESTS=1 /softwares/python/bin/python3 -B -m unittest scripts.tests.wf_runtime.test_run_all_contract
/softwares/python/bin/python3 -B -m unittest scripts.tests.wf_runtime.test_unit_temp_paths
bash scripts/tests/wf_runtime/full/run_all.sh --full --repro green
bash scripts/tests/wf_runtime/full/run_all.sh --full --repro green --serial
bash scripts/tests/wf_runtime/full/run_all.sh --full --repro none
bash scripts/tests/wf_runtime/full/run_all.sh --representative --repro green --repro-group install --fixture-deploy candidate --release-root <verified-candidate-root> --release-ref <verified-ref> --release-version <verified-version>
bash scripts/tests/wf_runtime/full/repro/run.sh --group install --mode green
/softwares/python/bin/python3 -B scripts/build-wf-release.py --verify --verify-token-parity
git diff --check
```

固定路径盘点以这些命令为起点，人工核对结果中的每个匹配项，并检查经 `tempfile.gettempdir()`、shell helper 和动态拼接产生的路径：

```bash
rg -n '(/tmp/|tempfile\.(mkdtemp|NamedTemporaryFile|gettempdir)|mktemp)' scripts/tests/wf_runtime/full
```

对自动回退使用可复算的现有分支，不注入 can_unshare 结果：

```bash
ln -s <repository-root> <scope>/repo
WF_TEST_SCOPE_ROOT=<scope> WF_TOTAL_JOBS=2 WF_SUITES=r70_tests \
  bash <scope>/repo/scripts/tests/wf_runtime/full/run_all.sh --repro none
WF_TEST_SCOPE_ROOT=<scope> WF_TOTAL_JOBS=2 WF_SUITES=r70_tests \
  bash scripts/tests/wf_runtime/full/run_all.sh --serial --repro none
```

第一条通过逻辑路径 `HERE=/tmp/<scope>/repo/...` 触发 runner 已有的 `repository-under-tmp` 分支。核 summary 中的 `fallback_reason` 和 `execution_mode`，再按相同 suite 对照显式串行执行的 unit outcome。测试在自己的 owned scope 中创建和移除 symlink。

## 收口

按 A1–A4 一次复查真实入口证据、断言映射、所有固定路径分类及任务 diff。完整候选审计必须有真实逐 ID 输出，不以合成单元测试替代。若某环境能力无法实跑，注明对应验收未完成，不把其余绿灯推导为通过。后续问题须有具体调用和可观察后果，并改变本轮结论、证据来源、数据安全或受支持调用，才纳入本任务。显式候选仓库/cache 是已核输入，除非另有用户授权，不纳入 runner 回收。prune 与退役资格遵守现有契约，不从 `summary.status=failed` 推导新的删除策略。提交和发行仍按项目规则授权。

## 执行记录（2026-11-19）

### 结果

- A1：候选 0.1.1 慢契约通过——临时发行树 + 候选仓库 → 代表入口（f0/R70/CP5 等）与 install repro，
  `summary.status=ok`、`candidate_commit` 一致、f0 安装身份 `version=0.1.1`、R70 次级项目
  “安装来源为本次发行” PASS；同一 legacy scaffold 的 dev 部署与候选安装在 `.trellis/README.md`、
  `NOTES.md`、两次原始提交上字节一致；CP5 B1/B2 在候选 F2 上 `11/11` 通过。
  安装身份核验的缺记录/错 version/ref/commit/rules/`.wf/lib` 反例由
  `test_verify_install_identity.py` 覆盖。
- A2：正式发行全量审计 `65/65` 可计划 ID，`candidate-clean` 63 项全部 `ok`，`p5_v1`/`r90_tests`
  保留具体失败断言并处于候选排除；同身份增量 `--only cp1_tests` 成功并保留其余行；空值/未知/混合
  `--only`、身份不一致均在启动套件前拒绝且原报告 sha256 不变。
- A3：`/tmp` 仓库路径真实触发 `repository-under-tmp` 串行回退，与显式 `--serial` 的
  `suite_ran/flow_ran/fail/status` 对拍一致；每个受监督单元 receipt `local_tmp_created=true`、
  `local_cleanup=removed`、无 retained path；旧 `/tmp` 伪确认/审批/notes/release-repo 诱饵存在时
  连续两次串行运行仍全绿，诱饵未被消费或改写；静态扫描全部可计划脚本与 fixture/init helper 后
  无未登记 `/tmp` 字面量（仅手工 D1 工具与运行器自身契约保留）。
- A4：`assertion_failed/execution_failed/preparation_failed/cancelled/unverified` 与清理三态
  组合测试通过；`summary.unit_outcomes` 与 `failure_owner` typed 计数在真实 `run_all` 输出中生成；
  结构缺失的单元记 `unverified`、`evidence_state=incomplete`，失败运行仍发布 `summary.json`
  记录清理事实。完整 dev full green 与串行 full green 均 `GATE-OK`。

### 命令与结果

| 命令 | 结果 |
| --- | --- |
| `python3 -B -m unittest discover -s scripts/tests -t .` | 1323 tests OK（42 skipped） |
| `WF_SLOW_TESTS=1 python3 -B -m unittest scripts.tests.wf_runtime.test_run_all_contract` | 41 tests OK（732s，最终代码） |
| `bash scripts/tests/wf_runtime/full/run_all.sh --full --repro green` | 149 units，fail=0，GATE-OK（68s） |
| `bash scripts/tests/wf_runtime/full/run_all.sh --full --repro green --serial` | 149 units，fail=0，GATE-OK（359s） |
| `bash scripts/tests/wf_runtime/full/run_all.sh --full --repro none` | 64 units，fail=0，GATE-OK |
| `candidate_audit.py --tree docs/workflows/wf-release --version 0.1.0`（scope 输出） | 65/65，bad=p5_v1,r90_tests，`AUDIT-STATUS=failed`（含预期 dev-only 断言失败） |
| `python3 -B scripts/build-wf-release.py --verify --verify-token-parity` | 字节复现 OK（0.1.0，74 assets） |
| `/tmp` 盘点（`rg -n '(/tmp/|tempfile\.(mkdtemp|NamedTemporaryFile|gettempdir)|mktemp)'`） | 套件材料全部按次；仅 runner 契约（namespace `/tmp` tmpfs、fixture lease 锁、仓库回退判定）与手工 D1 保留 |

### 审查复核修正（2026-11-19）

对外部审查意见逐条质疑后，确认并修正了四处未覆盖问题（运行时契约均在正确层修正并补测试）：

1. `classify_unit` 未核对 test receipt 的 `rc/status` 与单元结果是否一致；现不一致记 `unverified`。
2. `preflight_failed` 在缺 `failure_reason` 时仍被判 `preparation_failed`；现无记录原因记 `unverified`。
3. `fixture_scope` 的 `WF_HOST_TMPDIR` 桥接接受任意存在目录（含 `/`、HOME/仓库及内部路径），
   会放宽 fixture 删除域；现统一经 `_temporary_roots()` 有界校验（存在目录、拒绝根/受保护路径
   及其祖先/内部），并补 `HostTempBridgeTest`。
4. `candidate_audit` 对结构损坏的旧报告行会抛未分类异常；现明确 `AUDIT-REFUSED`，原子发布失败
   会清理临时文件并按 0644 发布。对应测试覆盖旧报告非 dict/非对象行与发布失败保全原字节。

另修正 A1 慢契约的比较口径：跨两个独立 scaffold 不应比较含时间戳的 commit id，改为比较
content-addressed 提交树（tree id），并保留 `.trellis/README.md`/`NOTES.md` 字节一致断言。

审查意见中“rg 全局零命中 `wf-v0.1.0`”“116 个目标测试”等表述不准确：合成安装记录/repro
扰动夹具仍保留固定 ref 字符串（非发行来源），静态守卫是 9 个测试覆盖 68 个扫描目标；
`outcome_counts` 是报告内部校验字段，`summary.json` 对外是 `unit_outcomes` + typed
`failure_owner`。这些按实际契约理解，不据此改代码。

### 未完成/边界

- 提交与 Trellis 收尾（archive/journal）未执行，等待用户明确同意。
- 正式 `candidate-audit.json` 已用 scope 输出覆盖并复核身份/安装；后续 helper 变更需完整重跑审计。
