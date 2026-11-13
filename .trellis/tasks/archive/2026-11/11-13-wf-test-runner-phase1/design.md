# Phase 1 技术设计

## 0. 边界

- 只做 Phase 1A/1B/1C。不删除/合并套件、不做覆盖矩阵裁剪、不实现跨版本升级。
- 产品发行树 `docs/workflows/wf-release` 只由人（或 T3 显式命令）构建；测试路径一律写缓存根。
- 安装器的 tag / 提交树摘要 / 工作树干净 / identity 校验**不放宽**；测试只是换来源，不改判据。

## 1. 分层与数据流

```
run_all.sh  ──(argv/env)──>  plan.py ──> Plan(dict) ──(sh/json)──> run_all.sh 执行
                                 │                                   ├─ wf_test_release.py  (dev: 测试发行缓存)
                                 │                                   ├─ prepare_candidate_repo.py (candidate 前置)
                                 │                                   ├─ wf_fixture.sh → wf-dev-deploy.py | 候选 install.py
                                 │                                   ├─ f1_init.py → .wf/bin/wf.py
                                 │                                   ├─ suites (*.py)
                                 │                                   ├─ flows (f0/p5_*)
                                 │                                   └─ repro/run.sh ──> select.py ──> groups.json
                                 └─ suites.json / groups.json
```

单一权威：
- **执行计划**：`plan.py`（唯一 `plan()`）。`--list` / `--dry-run` / 真实执行消费同一输出对象。
- **套件清单**：`full/suites.json`（不是文件 glob）。
- **repro 组**：`full/repro/groups.json`（组与用例元数据唯一来源）。
- **发行身份**：`scripts/wf_release_common.py` 的摘要函数 + `wf_test_release.py` / `prepare_candidate_repo.py` 写出的 meta。
  测试侧不再有第二套 `TAG`/`RELEASE` 常量（`_release.py` 从环境读，`_harness.py` 从环境读）。

## 2. `plan.py`

### 输入
`argv`（run_all 的全量参数）+ 环境：`WF_SUITES`、`WF_WITH_REPRO`、`WF_REPRO_JOBS`、`WF_JOBS`、
`WF_FIXTURE_DEPLOY`、`WF_RELEASE_ROOT/REF/VERSION/META`、`WF_RESULTS_DIR`。

### 输出
`Plan` 字典（`--format json` 打印，`--format sh` 输出 `PLAN_*` 赋值供 bash `eval`）：
`mode`、`full_mode`、`suites_parallel`、`suites_serial`、`flows`、`extra`、`repro_enabled`、
`repro_mode`、`repro_groups`、`fixture_deploy`、`release_root/ref/version/meta`、
`test_release_root/version/ref`、`results_dir`、`jobs`、`repro_jobs`、`list_only`、`dry_run`、`no_build`、`candidate_smoke`。

### 规则（唯一实现，plan.py 内）

| 条件 | 结果 |
|---|---|
| `--full` + `--subset` / `--full` + `--representative` / `--subset` + `--representative` | 非零退出，列出冲突 |
| `WF_SUITES` 非空且无显式模式 | `mode=subset` |
| `--full`/`--representative` + `WF_SUITES` 非空 | 拒绝（提示清空 `WF_SUITES` 或用 `--subset`） |
| 无显式模式且 `WF_SUITES` 为空 | `mode=full`（保持现状） |
| `--subset` 且选择为空 | 拒绝并列出可用套件 |
| subset + 任何 repro 参数/组 且 `WF_WITH_REPRO != 1` | 拒绝 |
| repro 启用 | full / representative 恒开；subset 需 `WF_WITH_REPRO=1`；`--repro none` 关闭 |
| `--repro-mode` 缺省 | dev: `green`；candidate: `green`；独立 `repro/run.sh` 缺省仍是 `both`（保持兼容） |
| `--repro none` + `--repro-group` | 拒绝 |
| `--fixture-deploy candidate` | 必须同时给 release-root/ref/version；repro 模式 ∈ {green,auto}；否则拒绝 |
| `--fixture-deploy dev` + 任一 release 参数 | 拒绝 |
| 未知套件名 / 未知组名 | 非零退出并列出可选值 |
| `--representative` | suites = `representative=true && kind=suite`；flows = `f0` + `representative_flow`（默认 `p5_spec`）；repro 组 = `groups.representative`（candidate: `groups.candidate_representative`，再按 candidate_clean 过滤） |
| representative + candidate 且过滤后无组 | `candidate_smoke=true`，不静默拒绝 |
| candidate 模式 suites | 只保留 `candidate_clean=true` 的套件；一个都没有 → 用 `f1_candidate_smoke`（`fallback_representative=true`） |
| `FULL_MODE` | 仅 `mode=full` 为 1；subset/representative 强制 0 |

`--list` / `--dry-run` 只输出计划（`plan.json` 落到 `results_dir/plan.json`），不执行任何子进程。

### 为什么 bash 里还要 `eval`
`run_all.sh` 保留 bash 负责执行与门禁（最小 diff），但选项解析与选择逻辑全部移到 `plan.py`，
避免“两份计划”。`--format sh` 只输出我们自己生成的 `PLAN_*=单引号值`，不含外部输入回显。

## 3. `suites.json`

```json
{"schema_version": 1, "flows": ["f0","p5_spec","p5_v2v3","p5_v5"],
 "suites": [{"name":"r70_tests","kind":"suite","tags":["review"],
             "representative":true,"candidate_clean":false,
             "representative_flow":null,"expected_seconds":24,"notes":"..."}]}
```

- `kind`: `suite`（默认全量 59 个）/ `extra`（`r72_tests`）/ `manual`（`d1_tests`、`d1_wf_tests`，不进默认全量）/
  `candidate`（`f1_candidate_smoke`，只在 candidate 代表集使用）。
- `candidate_clean` 默认 `false`；只有“断言只经 `.wf/bin/wf.py` 与 `$F/.wf/lib`，不读源码 `payload/lib`”
  的套件才可标 `true`。Phase 1 只有 `f1_candidate_smoke` 标 `true`（其余 59 个保留 `false`，
  其中 53 个仍硬编码源码 `payload/lib`，列在 `IMPLEMENTATION_NOTES` 的待迁移清单）。
- `representative=true` 的 6 个套件：`f1_ordinary`、`cp1_tests`、`r31r34_tests`、`r70_tests`、`r71_tests`、`r7r15_tests`。
  它们只在 dev 模式参与代表集；candidate 模式被 `candidate_clean` 过滤掉。

## 4. `repro/groups.json` + `select.py`

```json
{"schema_version": 1,
 "representative": ["review","archive","identity","writer","install"],
 "candidate_representative": ["install"],
 "groups": {"review": ["review-count-reject", ...]},
 "cases": {"reinstall-preserves-data": {"group":"install","assertion_target":"installed",
           "stage_role":"scaffold","module":"install.py","targets":["payload/install.py"],
           "candidate_clean":true}}}
```

- 组定义只用**显式用例名列表**（不支持通配），保证“零匹配”是可检测错误。
- `cases` 只补充元数据；缺省 `candidate_clean=false`、`assertion_target=source`、`stage_role=target`。
- `candidate_clean` 由 runner **复核**：`assertion_target=installed && stage_role=scaffold` 才允许为 `true`，
  否则直接拒绝 manifest（防止手滑把 stage 用例标成候选）。
- `select.py` 职责：`--group/--only` 交集解析、candidate 过滤、`skipped_non_candidate` 列表、
  `auto` 的新鲜度判定（用例脚本 + helper 摘要 + `targets` 摘要 + 状态文件）、meta 校验。
  输出 `CASES`（要跑的用例）、`MODES`（每用例 green/both）、`SKIPPED`。

自动新鲜度（`--mode auto`）：
- 状态文件 `<cache>/repro-state.json`，schema 版本常量在 `select.py`；schema 变化 → 全部 both。
- 每个用例记 `script_digest`、`helpers_digest`、`targets_digest`（目标文件字节 sha256）。
- helper 集合：`_harness.py`、`_release.py`、`_review_flow.py`、`_review_launch.py`、`_snapshot.py`、`_executor_set.py`。
- 任一摘要缺失/变化/用例是新的 → 该用例 both；否则 green。
- candidate 模式：auto 只允许 green；若判定出任何 both → 非零退出并提示“先在 dev 模式跑 red”。
- 状态只由父进程在汇总校验通过后原子写（`os.replace`）；失败/超时/未完成用例不写状态。

## 5. 测试发行隔离（`scripts/tests/wf_test_release.py`）

- 版本解析：`--version` > `WF_TEST_RELEASE_VERSION` > `dev-manifest.version`（非占位符时）> 常量 `0.1.0`。
  `dev-manifest.version` 是真实版本且与请求版本不一致 → 明确失败（不绕过 `_assert_version_consistency`）。
- 输出根默认 `~/.cache/wf-test-release/<version>`；`--root` 可覆盖，但必须遵守：
  - `realpath(out)` 不得是 `/`、仓库根、`docs/workflows`、`docs/workflows/wf-release`、源码根；
  - 不得是符号链接；不得与源码/产品树重叠；
  - 空目录，或带**输出根之外**的 `.owner` 兄弟文件（`<out>.owner`）且内容匹配；
  - 先在同级临时目录构建 + `verify`（manifest/digest）成功，再原子替换；失败保留旧产物。
- meta：`<out>.meta.json`（输出根外，字节复现不受影响）：
  `{"schema_version":1,"version","release_ref","source_tree_digest","manifest_digest","built_at"}`。
- `wf_release_common` 新增 `source_tree_digest()`（按 `source_tree_files()` 枚举 + 逐文件 sha256 + 路径排序，
  算法与 `build_manifest` 同源，不看 mtime）与 `manifest_digest()`（canonical json）。
- `--verify-meta <out>`：核对 version/ref 与解析结果、`source_tree_digest` 与当前源树；
  失败 → 非零 + 提示“测试发行副本过期”。
- `--no-build` 在 `run_all.sh`(dev) / `repro/run.sh`(dev) 都走这套校验。

## 6. 候选仓库（`prepare_candidate_repo.py`）

- 输入 `--tree`（默认 `docs/workflows/wf-release`）、`--version`、`--out`。
- 复制 `tree` → `out`（排除 `.git`、`__pycache__`），`git init`/`add`/`commit`/`tag wf-v<version>`。
- 校验：`git rev-parse refs/tags/wf-v<version>^{commit}` 成功；`git status --porcelain` 空；
  `wf-release.json.version == version`；`install.py` / `wf-release.json` / `wf-release/` 存在。
- meta 写 `<out>.meta.json`（仓库根**外**）：`{version, tag, commit, tree_digest, source_tree_digest, built_at}`。
- 缓存：`<out>.meta.json` 的 `tree_digest + version` 与当前一致且校验通过 → 直接复用；否则重建。
- `--check`：只校验不复建（供 `--no-build` 使用）。

## 7. 夹具部署（`wf_fixture.sh`）

- 兼容旧位置参数：`wf_fixture.sh <F> [nocap]`。
- 新增 `--deploy dev|candidate`、`--release-root/--release-ref/--release-version`、`--profile`（Phase 1 只接受 `install`）。
- `dev`：现行为（`wf-dev-deploy.py`），安装记录 `0.0.0-dev`。
- `candidate`：
  ``python3 <release-root>/install.py --target F --release-ref <ref> --source <release-root> --platform dsh --confirm``
  之后用 python 校验 `.wf/install/installation.json`：`version == release_version`、
  `release_ref == release_ref`、`rules_digest == <release-root>/wf-release.json` 的 `compatibility.rules_digest`、
  且 version 不是 `0.0.0-dev`。任一不符 → 非零退出（不回退 dev）。
- `run_all.sh` candidate 模式把同一组参数传给 `run_suite`/`run_flow`/`run_f0`/`repro/run.sh`。

## 8. wflib 来源解析契约

```
resolve_test_lib():
  1. $WF_TEST_LIB（目录，含 wflib/…）        # runner 显式指定（测试发行/候选的 lib）
  2. $WF_FIX/.wf/lib（安装产物）              # 夹具项目自己的 lib
  3. <repo>/docs/workflows/wf/payload/lib     # 仅 dev 回退（stage red 用）
```

- `f1_init.py` 用它导入 `wflib.records.plain_digest`；删除 `/tmp` 插入与源码绝对路径。
- `repro/_harness.py` 的 `require_business_code` / `code_problem` 用它读 `wflib.codes`。
  runner 在 dev 模式设 `WF_TEST_LIB=<test-release>/wf-release/lib`，candidate 模式设
  `WF_TEST_LIB=<candidate-root>/wf-release/lib` → 断言侧不再读源码树。
- 仍硬编码源码 `payload/lib` 的 53 个套件保留 `candidate_clean=false`（清单见 notes），不阻塞 Phase 1。

## 9. repro 身份参数化

- `_harness.py`：`RELEASE` ← `WF_RELEASE_TREE`（默认产品树，仅 dev 兼容），
  `RELEASE_REF` ← `WF_RELEASE_REF`（默认 `refs/tags/wf-v0.1.0`），`RELEASE_VERSION` ← `WF_RELEASE_VERSION`（默认 `0.1.0`）。
- `_harness.release_source(root)`：复制 `RELEASE`（排除 `.git`/`__pycache__`）→ 以 `RELEASE_REF` 的 tag 名提交打 tag。
- `_harness.deploy(root)`：用 `RELEASE_REF` 安装。
- `_release.py`：`TAG` / `TAG_REF` 由环境解析；`source_repo()` 同上；`installer()` 用 `TAG_REF`。
- `install_fixture()` 默认值改由环境解析（合成记录里显式给旧版本的用例不受影响）。

## 10. 计时与计数

`run_all.sh`：
- `build_seconds`：测试发行构建 + 候选校验；`init_seconds`：`wf_fixture.sh` + `f1_init.py` 累计；
  `suite_seconds`：套件/流程/extra 累计；`green_seconds` / `red_seconds`：从 `repro/run.sh` 的
  `REPRO_GREEN_SECONDS` / `REPRO_RED_SECONDS` 读；`total_seconds`：整脚本。
- 计数：`suite_ran`（套件+流程+extra）、`flow_ran`（流程/extra 单列，不重复计入总数）、`repro_ran`（用例数）。
  汇总行保留 `运行 N 项`，其中 N = `suite_ran` + `repro_ran`，`flow_ran` 单列打印以保持 149 口径可核对。
- 写 `RESULTS_DIR/summary.json`。

## 11. 失败传播（保留 + 补齐）

- 并行/串行结果行：保留现有 5 段格式、malformed/missing/duplicate/unexpected/xargs 检查。
- repro：缺 `REPRO_TOTAL` 或数字不一致 → fail+1；`REPRO_FAILED>0` → 记失败；
  `SKIPPED_NON_CANDIDATE>0` 单列打印，不计通过。
- 组/用例零匹配 → `repro/run.sh` 非零（沿用 `--only` 的 0 匹配语义）。
- 超时：`repro` 每用例 `timeout`（默认 120s，`WF_REPRO_TIMEOUT` 覆盖），超时 kill 进程组并记失败。
- `plan.py` 的任何拒绝 → `run_all.sh` 原样透传非零退出码（`2`）。

## 12. 兼容与回滚

- 旧调用 `bash run_all.sh`（无参数、无 `WF_SUITES`）仍是 full，`--repro` 默认 `green`（比旧的 both 少一半，
  是方案稿明确的行为变更；T3 用 `--repro both`）。
- 旧调用 `bash repro/run.sh` 默认仍是 `both`（保持兼容）。
- `wf_fixture.sh <F> [nocap]` 位置参数保持可用。
- 回滚：本任务只改测试/工具/文档；单文件 `git checkout` 即可回退（提交前）。

## 13. 与方案稿的偏差（记录）

1. **编排语言**：方案稿把 `plan()` 描述在 `run_all.sh` 内；这里把解析/选择抽到 `plan.py`，
   `run_all.sh` 仍负责执行与门禁（避免 bash 里做 JSON/冲突校验产生两份计划）。接口不变。
2. **repro 编排**：同理新增 `repro/select.py`；`repro/run.sh` 仍是入口。
3. **候选 meta 位置**：方案稿说候选构建 meta 写 `docs/workflows/.wf-release-meta.json`；
   Phase 1 的候选由 `prepare_candidate_repo.py` 产出，meta 写 `<out>.meta.json`（仓库根外）。
   `build-wf-release.py` 是否额外写产品侧 meta 留待 T3 实施时再定（Phase 1 不改产品构建产物语义）。
4. **`f1_candidate_smoke`**：Phase 1 没有现成套件达到 candidate_clean，按方案稿 §7.5 兜底实现该 CLI-only 闭环。
5. **repro 默认模式**：独立 `repro/run.sh` 保持 `both` 默认（方案稿 §0 建议兼容），`run_all` 显式传模式。
