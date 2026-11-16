# 实施计划与验证矩阵

## 0. 前置与边界

- 开始前记录 `git status`/`git diff`/未跟踪文件；本任务只改 runner/测试/文档，不碰 `docs/workflows/wf/**`、产品发行树与用户 cache 内容（测试只读/快照用户 cache）。
- 解释器用项目声明 `/softwares/python/bin/python3`；T0 带 `PYTHONPYCACHEPREFIX=/tmp/wf-unit-pycache`，pyc 不落源树。
- inline 模式：不派 implement/check 子代理，`implement.jsonl`/`check.jsonl` 保持空并由 `task.py start --allow-empty-context` 放行。
- 顺序：R1 修复 → R3 barrier 化 → R2 契约 scope/账目（依赖前两者稳定）→ R4 证据/文档 → 全量验证。

## 1. R1 恢复窗口（先建立会失败的行为测试）

| 步骤 | 文件 | 内容 |
|---|---|---|
| 1.1 | `scripts/tests/wf_runtime/test_release_lock.py` | 新增 6 个窗口：journal 后未移旧（旧代原位）、移旧未装新、装新未写 meta、meta 后未清 journal、staging 半移动、首次发布各步。先跑旧实现确认「旧代原位」窗口失败 |
| 1.2 | `scripts/tests/wf_test_release.py`（`tests/wf_runtime/`） | 抽 `_recovery_action` 纯判定；旧代原位→清 staging/journal；首次发布→只撤新代；其余保持 fail closed |
| 1.3 | `scripts/tests/wf_runtime/full/template_cache.py` | 同一状态机（owner/validator 各自），覆盖 repoint 前/后窗口 |
| 1.4 | `scripts/tests/wf_runtime/test_template_cache.py` | 同上 6 窗口 + sibling 不被误删 |

## 2. R3 公共摘要 barrier 化

| 步骤 | 文件 | 内容 |
|---|---|---|
| 2.1 | `repro/repro_select.py` | 新增 `public_inputs()`/`scan_counts`；bundle 升 schema 2（`public_inputs` + 局部 `local_inputs`）；`red_subject/input_fingerprint` 改签名 |
| 2.2 | `repro/_worker.py` | 只重算 local_inputs + context 比对；删除 source/helpers 重算 |
| 2.3 | `repro/repro_select.py::commit_state` | barrier 只重算一次 public/context，随后逐 case 局部核验；candidate 终审保持 |
| 2.4 | `full/results_gate.py` | 读 schema 2，不重算公共摘要 |
| 2.5 | `test_repro_selection.py`、`test_results_gate.py` | schema 1 拒绝；3 vs 30 case 扫描计数相同；worker 后计数不增 |

## 3. R2 契约 scope/账目

| 步骤 | 文件 | 内容 |
|---|---|---|
| 3.1 | `test_run_all_contract.py` | `setUpClass` owned scope + 空 pool；`CaseBudget`（900s 分摊）；每 case state/HOME、每调用 results/fixture/pycache；env 注入断言 |
| 3.2 | `full/run_all.sh`、`plan.py`、`wf_test_release.py` | `--ensure --json` 增 `status: built|reused`；summary 增 `release_build`/`template_build_sequences`；两 cache meta 增累计 `builds`（additive） |
| 3.3 | `test_run_all_contract.py` | 生产隔离快照断言；plan-only 零 warmup；取消 probe 显式 warmup；故障/冷建 private pool；`evidence/class-cost.json` 账目 |
| 3.4 | `full/repro/run.sh` | 独立入口 cache 在 scope 时同样受 `check-scope`；state/HOME 写入 scope 校验 |

## 4. R4 证据与硬化

| 步骤 | 文件 | 内容 |
|---|---|---|
| 4.1 | `full/run_all.sh`、`full/repro/run.sh` | `WF_TEST_RELEASE_CLI`/`WF_CANDIDATE_VALIDATOR` 注入点（默认值不变）；调用计数 shim 契约测试（内嵌 0/独立 1/候选起止各 1） |
| 4.2 | `full/run_all.sh`、`full/plan.py` | stages/plan-calls 计数文件；断言 4 阶段/2 次计划 |
| 4.3 | `full/fixture_scope.py::verify_results_lock` | `scope:` 域必须过 `read_scope` 且与当前 scope 一致；无 scope 时拒绝 scope 域 |
| 4.4 | `full/namespace.py` | 清理 `WF_TEST_RUN_CACHE`/state locator；新增真实 `unshare` 硬化测试（能力缺失显式 skip+记录） |
| 4.5 | `scripts/wf_release_common.py` | `git_head/git_describe` 支持 `WF_GIT_BIN`；HEAD 失败走 run-owned 契约测试 |
| 4.6 | `test_template_cache.py` | A/B 输入交替 miss 与单槽回滚 |
| 4.7 | `test_run_all_contract.py` | `--repro-concurrent --no-build`、candidate red/both 拒绝、取消后立即重取锁、AC18 SUT escape（scope 内 outside 兄弟目录） |
| 4.8 | 两份 README、`.trellis/spec/docs/wf-delivery-discipline.md` | 列出/清理口径；scope/pool/账目/barrier/计数注入点；更正上轮失实声明（新记录） |

## 5. 验证矩阵

| ID | 行为证据 | 目标测试面 |
|---|---|---|
| V1 | 6 个 journal 窗口自动恢复；旧代原位不再 fail closed；两代不可验证保留现场 | `test_release_lock`、`test_template_cache` |
| V2 | 恢复不改 sibling；meta/owner 字节与 journal 冻结值一致；首次发布只撤新代 | 同上 |
| V3 | 契约单 scope/空 pool/每 case state/每调用 results；plan-only 零 warmup；teardown 无遗留 | `test_run_all_contract` |
| V4 | 契约运行前后生产结果锁 inode/mtime、用户 cache 快照不变 | 同上 |
| V5 | 首次 build=2/模板首建=1，后续同输入 build=0；candidate 不建 dev；private 不污染 | 同上 + summary 字段 |
| V6 | 900s deadline 递减；15s/5s 单列；超时归因明确 | 同上 |
| V7 | freeze 1 次/commit 1 次；worker/gate 0 次；公共输入篡改被拒 | `test_repro_selection`、`test_results_gate` |
| V8 | 3 与 30 case 公共扫描计数相同；schema 1 bundle 拒绝 | `test_repro_selection` |
| V9 | 内嵌 ensure/check=0、独立=1；candidate validator 起止各 1；坏候选无 worker | 契约 + shim 计数 |
| V10 | 伪造 scope 域/生产锁拒绝；unit 域无宿主 state locator；宿主锁不变 | `test_fixture_scope`、namespace 硬化测试 |
| V11 | 4 stage/3 重入/2 计划；HEAD 失败 run-owned；A/B miss；`--no-build`+并发；取消重取；SUT escape | 契约 + 定向单测 |
| V12 | README 口径可执行；文档校验通过；T0/定向/契约/full green 全绿 | 文档 + 全量命令 |

## 6. 命令与成本协议

```bash
# T0
PYTHONPYCACHEPREFIX=/tmp/wf-unit-pycache /softwares/python/bin/python3 -m unittest discover -s scripts/tests -t .
# 定向
/softwares/python/bin/python3 -m unittest scripts.tests.wf_runtime.test_release_lock
/softwares/python/bin/python3 -m unittest scripts.tests.wf_runtime.test_template_cache
WF_SLOW_TESTS=1 /softwares/python/bin/python3 -m unittest scripts.tests.wf_runtime.test_run_all_contract
# 阶段收口（隔离后）
R=$(mktemp -d /tmp/wf-full-XXXX); C=$(mktemp -d /tmp/wf-fullcache-XXXX)
WF_RESULTS_DIR=$R WF_RESULTS_CACHE=$C WF_TEST_RUN_CACHE=$R/state \
  bash scripts/tests/wf_runtime/full/run_all.sh --full --repro green
# 成本：同机 ≥3 次 warm full green 中位数 + 1 次 cold；记录 release/template build 次数、
# 公共扫描计数、identity 墙钟；目标新增 identity 墙钟 ≤3s、full 中位增幅 ≤10%（不达标先查重复计算）
# 文档/发行校验
/softwares/python/bin/python3 scripts/build-wf-release.py --verify --verify-token-parity
/softwares/python/bin/python3 scripts/validate-wf-design.py
/softwares/python/bin/python3 scripts/check-doc-refs.py
./scripts/validate-skills.sh
```

## 7. 复审与回退点

- R1 完成后先跑 `test_release_lock`/`test_template_cache` 与 r67 冒烟，再动 R3；R1 可单独回退。
- R3 的 bundle schema 与 worker/gate/writer 同批改；中途失败按「整批回退」处理，不做兼容层。
- R2 契约 helper 改动后再跑一次 r67/r70 子集与 repro install 组，确认 scope 化没有改变被测语义。
- 任一失败先归因（实现缺陷/输入失效/环境能力），不通过 skip、加 timeout、改 expect 或借真人 cache 变绿。
- 收口前复核最终 diff/untracked，确认只含本任务路径；未授权不 commit/push/归档。
