# Phase 1 实施记录：方案稿章节 → 实际改动

> 方案稿：`/tmp/scripts_wf_imporve.md`（未修改）。基线 `93a30e09`。
> 本文件只记录**实际做了什么、验证到哪一步、哪些还没验证**。

## 1. 文件清单

新增（9）：

| 文件 | 作用 |
|---|---|
| `scripts/tests/wf_test_release.py` | 测试专用发行构建入口（缓存根、meta、`--check`、`--no-build` 校验） |
| `scripts/tests/wf_runtime/full/plan.py` | 运行器**唯一**执行计划（模式/gating/冲突/`--list`/`--dry-run`） |
| `scripts/tests/wf_runtime/full/suites.json` | 套件清单（59 suite + r72 extra + 2 manual + candidate）+ 流程/extra 期望 PASS 数 |
| `scripts/tests/wf_runtime/full/results_gate.py` | 结果行完整性判定（缺行/重行/畸形/计划外/坏结果）唯一实现 |
| `scripts/tests/wf_runtime/full/repro/repro_select.py` | repro 组选择、candidate 过滤、`--mode auto` 新鲜度、状态提交 |
| `scripts/tests/wf_runtime/full/repro/groups.json` | repro 组与用例元数据（assertion_target / stage_role / targets / candidate_clean） |
| `scripts/tests/wf_runtime/full/repro/_worker.py` | 单用例 worker（只写自己的结果与日志、超时杀进程组） |
| `scripts/tests/wf_runtime/full/prepare_candidate_repo.py` | 候选仓库引导（复制→commit→tag→校验→meta 仓库根外） |
| `scripts/tests/wf_runtime/full/f1_candidate_smoke.py` | 兜底候选闭环（候选安装→初始化/普通任务→复杂审查→归档） |

修改（9）：

| 文件 | 改动 |
|---|---|
| `scripts/tests/wf_runtime/full/run_all.sh` | 参数/选择交给 `plan.py`；gating（extra/flows/repro）；测试发行 vs 候选；计数拆分 + 分段计时 + `summary.json`；结果完整性走 `results_gate.py`；产品树摘要前后比对 |
| `scripts/tests/wf_runtime/full/run_one.sh` | 部署参数走环境；写 `.timing`（init/suite 毫秒） |
| `scripts/tests/wf_runtime/full/wf_fixture.sh` | `--deploy dev\|candidate`、`--release-*`、`--profile`；候选安装后核对 `installation.json`；去掉硬编码仓库路径 |
| `scripts/tests/wf_runtime/full/f1_init.py` | wflib 从 `$F/.wf/lib` → `WF_TEST_LIB` → 源码回退；删除 `/tmp` 插入与源码绝对路径 |
| `scripts/tests/wf_runtime/full/repro/_harness.py` | `RELEASE`/`RELEASE_REF`/`RELEASE_VERSION` 环境化；`test_lib()` 解析 codes 表；`release_source`/`deploy` 用解析出的 ref |
| `scripts/tests/wf_runtime/full/repro/_release.py` | 去掉独立 `TAG` 常量，改由 `_harness` 解析 |
| `scripts/tests/wf_runtime/full/repro/branch-source-preview.py` | 去掉硬编码 `refs/tags/wf-v0.1.0` |
| `scripts/tests/wf_runtime/full/r67_tests.py` | 假运行器环境按新契约重建（plan/suites/groups/results_gate/发行桩） |
| `scripts/wf_release_common.py` | 新增 `tree_digest` / `source_tree_digest` / `manifest_digest` |
| `.trellis/spec/docs/wf-delivery-discipline.md` | §7 并行两层 + 测试发行路径；§8 四层收口证据集 + 8 条硬边界 |

新增测试（5）：`test_test_runner_plan.py`、`test_repro_selection.py`、`test_test_release.py`、
`test_prepare_candidate_repo.py`、`test_results_gate.py`、`test_run_all_contract.py`（慢，`WF_SLOW_TESTS=1` 才跑）。

## 2. 方案稿章节映射

| 方案稿 | 落地 |
|---|---|
| §4.1 单一 plan / 冲突规则 / 选项语义表 | `plan.py`（`plan()` + `--format sh/json`）；`run_all.sh` 只 `eval` 计划 |
| §4.2 `run_all.sh`（1–11） | gating 1/2/3/4；计量 5/6；`--list/--dry-run`；representative 独立模式；candidate 透传；并行分层；测试发行只在 dev 构建 |
| §4.3 `repro/run.sh` | `--mode green/red/both/auto`、`--group`、`--only`、`--jobs`、`--fixture-deploy`、`--release-*`、`--no-build`、`--results-dir`；red 语义分类；每用例超时 |
| §4.4 测试发行隔离 | `wf_test_release.py`：版本解析、输出边界、原子替换、所有权标记与 meta 在输出根外、`--check` |
| §4.5 失败传播 | `results_gate.py` + repro 汇总校验（缺/重/畸形/计划外/超时）+ 产品树摘要比对 |
| §5.1 `suites.json` | 只做 runner 需要的最小清单（无覆盖矩阵字段填充） |
| §5.2 `repro/groups.json` | 组用显式用例名；`cases` 标注 install 组；`candidate_clean` 由 runner 复核 |
| §5.3 模块映射 | **未做**（Phase 2） |
| §3.5 候选仓库引导 | `prepare_candidate_repo.py`（tag/干净/版本/缓存/meta 位置） |
| §3.5 候选安装 | `wf_fixture.sh --deploy candidate` + `installation.json` 三元核对 |
| §3.5 wflib 解析 | `f1_init.py`、`_harness.test_lib()`；T3 代表集 = `f1_candidate_smoke`（兜底） |
| §7.5 兜底候选闭环 | `f1_candidate_smoke` |
| §8 交付纪律最小同步 | `.trellis/spec/docs/wf-delivery-discipline.md` §7/§8 |
| §12 运行器正反例 | 见 §4 验证矩阵 |

## 3. 与方案稿的偏差

1. **编排语言**：`plan()` 落在 `plan.py`、repro 选择落在 `repro_select.py`，`run_all.sh`/`run_all.sh` 仍是入口与门禁。
   接口与语义按 §4.1.1；只是把解析/冲突判定从 bash 抽到 Python（避免两份计划）。
2. **`select.py` 改名 `repro_select.py`**：`select.py` 会遮蔽标准库 `select`，任何把 `repro/` 放进
   `sys.path[0]` 的用例都会炸（实测 `TypeError: 'SelectSelector' object is not iterable`）。
3. **产品侧 `wf-release.meta.json` 未实现**：Phase 1 的候选 meta 由 `prepare_candidate_repo.py` 写
   `<out>.meta.json`（仓库根外）。`build-wf-release.py` 未改（生产语义不动）。`.gitignore` 也无需新增。
4. **流程/extra 的期望 PASS 数**移入 `suites.json`（`flow_expect`/`extra_expect`），不再硬编码在 `run_all.sh`
   ——原 `r67` 用正则从 `run_all.sh` 抓这些数字，改造后清单是唯一来源。
5. **repro 默认模式**：独立 `repro/run.sh` 默认仍是 `both`（兼容）；`run_all` 显式传 `green`。
6. **`candidate_clean` 只有 `f1_candidate_smoke` 为 true**：其余 59 个套件里 52 个仍硬编码源码
   `payload/lib`，按方案稿保留 `candidate_clean=false`，不为了“全绿”放宽候选证明。
   兜底闭环已实现并通过，因此没有“T3 无候选证据”的空档。
7. **`--list`/`--dry-run` 的输出分流**：人类可读摘要写 stderr，stdout 只保留可 `eval` 的 `PLAN_*` 赋值，
   这样 `run_all.sh` 能用同一份 `plan()` 输出执行计划（而不是再解析一遍）。
8. **计数口径**：`suite_ran`（套件）/`flow_ran`（流程+extra）/`repro_ran`（用例）三者独立，
   `units_total = 三者之和`，full 模式打印 `运行 149 项（套件 59，流程/extra 5，repro 85）`。
9. **`repro/_harness.test_lib()` 顺序**：`$F/.wf/lib` → `WF_TEST_LIB` → 源码回退（方案稿未定顺序；
   这样“已安装项目”优先，候选断言不会被发行副本的 lib 顶掉）。

## 4. 已验证 / 未验证

已验证（实际执行，2026-11-13）：

| 命令 | 结果 |
|---|---|
| `python3 -m unittest discover -s scripts/tests -t .` | 781 tests OK（6 skipped = `WF_SLOW_TESTS` 门控的端到端用例） |
| `WF_SLOW_TESTS=1 python3 -m unittest ...test_run_all_contract` | 6/6 OK（真子集/失败传播/meta 过期/候选无效/dry-run） |
| `WF_SUITES="r70_tests" run_all.sh` | rc=0，`运行 1 项`，GATE-OK，8s，无 repro/r72 |
| `repro/run.sh --group review --mode green --no-build` | 12/12，green 19s，red 0s |
| `repro/run.sh --group review --mode red --no-build` | 12/12，green 0s，red 17s |
| `repro --group install --fixture-deploy candidate ...` | 3/3 candidate_clean，`skipped_non_candidate` 6 个 |
| `repro --only review-count-reject --mode auto`（首次→再次→改 targets） | both → green → both |
| `repro --jobs 1` vs `--jobs 4`（review 组） | 结果文件逐项相等（12/12），state 只由父进程写 |
| `run_all.sh --full --repro green` | rc=0，**运行 149 项（套件 59，流程/extra 5，repro 85）**，GATE-OK，557s |
| `run_all.sh --representative --repro green` | 62 项 GATE-OK，181s |
| `run_all.sh --representative --repro green --repro-group install --fixture-deploy candidate ...` | 6 项 GATE-OK，22s；`f1_candidate_smoke` 17/17 |
| 候选安装记录 | `.wf/install/installation.json` = `0.1.2` / `refs/tags/wf-v0.1.2` / rules_digest 与候选一致 |
| `build-wf-release.py --verify --verify-token-parity` | OK byte reproduction (0.1.2, 74 assets)；token parity OK |
| `build-wf-release.py --version 0.1.2` 后 `git status docs/workflows/wf-release` | 空（字节相同，测试/重建未改写产品树） |
| `prepare_candidate_repo.py --tree ... --version 0.1.2 --out ~/.cache/wf-candidate-repo/0.1.2` | BUILT；tag 可解析、`git status --porcelain` 空、meta 在仓库根外 |
| `check-doc-refs.py` / `validate-wf-design.py` / `validate-skills.sh` | 全部 OK |

未验证 / 已知边界：
- **`--representative --fixture-deploy candidate` 的完整跑**只做了单点验证（`f1_candidate_smoke` 单独跑通），
  `run_all` 层的 representative+candidate 组合见交付报告的命令结果。
- **跨版本升级未覆盖**（`upgrade --apply` 仍是能力桩），T3 只能声称候选 install + 同版本 reinstall。
- **`--mode auto` 的“payload 目标未映射 → both”**：`groups.json` 只为 install/review 少量用例登记了
  `targets`，其余用例 `targets_digest=None` → 永远 both（安全默认，但会让 auto 退化成 both）。
- **并行套件层（`--parallel`）**未在 Phase 1 重测；默认串行。新增的 `results_gate.py` 由单测覆盖，
  未跑一次 `--parallel` 全量。
- **53→54 个硬编码源码路径**：`grep -l 'docs/workflows/wf/payload' full/*.py` 当前 54 个
  （含 `p5_f0.py`、`d1_tests.py` 两个非默认套件；默认 59 套件里 52 个）。未逐个迁移。
- `f1_candidate_smoke` 的复杂审查用夹具两份协议报告 + 主会话复核，不接外部 reviewer CLI。
