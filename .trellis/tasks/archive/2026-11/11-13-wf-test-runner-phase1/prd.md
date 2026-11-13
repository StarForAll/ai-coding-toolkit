# wf 测试体系 Phase 1：运行器与候选发行闭环

## Goal

按方案稿 `/tmp/scripts_wf_imporve.md` 的 **Phase 1A / 1B / 1C** 改造 wf 执行测试体系：
单一执行计划、真子集、green/red 分离、测试发行与产品发行隔离、候选仓库引导与候选安装、
wflib 来源解析、最小清单（`suites.json` / `repro/groups.json`）、交付纪律最小同步。

**不降低阶段收口覆盖，不按文件名删除历史测试。**

## 基线

- 仓库：`/home/xzc/projects/personal/ai-coding-toolkit`，基线提交 `93a30e09`（工作树 clean）。
- 现场核对的事实（不改假设）：
  - `run_all.sh` 的 `SUITES` 恰为 59 项；`WF_SUITES` 只改套件列表 + `SKIP_FLOWS=1`，
    但 `run_extra r72_tests` 与 `run_repro` 在 `SKIP_FLOWS` 判断之外无条件执行 → 子集实测 87 项。
  - `repro/run.sh` 对每个用例固定跑 `green` + `red`；固定 `build-wf-release.py --version 0.1.0`（写产品树）。
  - `repro/_harness.py`：`RELEASE` = 产品树 `docs/workflows/wf-release`；`release_source()`/`deploy()`
    固定 tag `wf-v0.1.0`；`install_fixture()` 固定 version `0.1.0`；`require_business_code`/`code_problem`
    从源码 `payload/lib` 读 `wflib.codes`。
  - `repro/_release.py`：`TAG = "wf-v0.1.0"`（与 `_harness` 两套身份来源）。
  - `wf_fixture.sh`：固定调 `scripts/wf-dev-deploy.py` → 安装记录 `0.0.0-dev`。
  - `f1_init.py`：`sys.path.insert(0, "/tmp")`；`sys.path.insert(0, "<repo>/docs/workflows/wf/payload/lib")`
    用于 `wflib.records.plain_digest`。
  - `docs/workflows/wf-release/wf-release.json` 的 version 是 `0.1.2`；`dev-manifest.json` version 是占位符
    `0.0.0-dev`（76 个 asset）。
  - `install.py`：`resolve_tag()` 在 `--source` 内解析 `refs/tags/wf-vX.Y.Z^{commit}`；`_worktree_clean()`
    看 `git status --porcelain -- <source 相对仓库根>`；`_committed_bytes()` 按 tag 提交取字节。
    因此候选 `--source` 必须是**带 tag 的干净仓库根**，不能是作者仓库内的 `docs/workflows/wf-release`。
  - repro 用例 85 个（`repro/*.py` 去掉 6 个 `_*.py` helper）；执行单元 149 = 59 套件 + 4 流程
    (`f0`/`p5_spec`/`p5_v2v3`/`p5_v5`) + `r72_tests` + 85 repro。

## Requirements

### Phase 1A：运行器与测试发行隔离

1. `run_all.sh` 建立**单一执行计划**（`plan()`）：`--full`/`--subset`/`--representative` 互斥；
   `WF_SUITES` 非空且未显式模式时隐含 `--subset`；`--full`/`--representative` + `WF_SUITES` 拒绝；
   `--repro green|red|both|none|auto` 只表示模式（不是组名）；新增 `--repro-group NAME`；
   `--fixture-deploy dev|candidate`（candidate 必须同时给 `--release-root/--release-ref/--release-version`）；
   `--release-root` 是**带 tag 的候选仓库根**；`--list`/`--dry-run` 与实际执行消费同一份计划（可输出 `plan.json`）。
2. repro gating：full/representative 允许 repro（representative 默认 `green`）；subset 需 `WF_WITH_REPRO=1`；
   `--repro none` 显式关闭。`FULL_MODE` 仅 `--full` 或无显式模式且无 `WF_SUITES` 时为 1。
   `f0`/`p5_*` 由 full 或 representative 控制（representative 默认 `f0` + `p5_spec`），subset 跳过。
3. 真子集：`WF_SUITES="r70_tests"` 只跑 1 个套件，不得隐式跑 85 个 repro 或 `r72`；
   `run_extra r72_tests` 只在 full 或 `r72_tests` 被选中时执行。
4. `repro/run.sh` 增加 `--mode green|red|both|auto`：`auto` 在首次运行/新用例/helper 变化/被测 payload
   目标变化时对相关用例强制 `both`，未变化只跑 `green`；candidate 模式只允许 `green|auto`，
   `auto` 检测到需要 both 时报错并提示在 dev 模式跑 red；`red`/`both` 在 candidate 下拒绝。
   red 前置失败不算 red 成功；注入后仍绿必须失败并输出目标断言。
5. `repro/run.sh` 增加 `--group NAME`、`--only SUBSTR`、`--jobs N`、`--fixture-deploy`、
   `--release-root/--release-ref/--release-version/--release-meta`、`--no-build`。
   每 worker 只写 `results/<case>.json` 与独立日志；父进程在汇总校验通过后原子更新 `repro-state.json`；
   失败/超时/未完成用例不得标记为“已验证”。`--jobs` 默认 1，先验证 `--jobs 4` 与 `--jobs 1` 结果一致。
6. 测试发行隔离：新增测试专用构建入口 `scripts/tests/wf_test_release.py`，构建到缓存根，
   不写 `docs/workflows/wf-release`；写 `test-release-meta.json`
   （version/ref/source_tree_digest/manifest_digest/built_at）；`--no-build` 必须核对 meta 与当前源树摘要，
   缺失或不一致就拒绝。T1/T2 不修改产品发行树；运行前后校验产品树摘要不变。
7. 失败传播：套件退出码非零、夹具/`f1_init` 失败、结果行缺失/重复/格式错误、子进程崩溃/超时、
   repro 前置失败、分组零匹配、汇总数字不一致，都必须让 `run_all` 非零退出；保留既有并行结果完整性检查。
8. 计时与计数：输出 `build_seconds`、`init_seconds`、`suite_seconds`、`green_seconds`、`red_seconds`、
   `total_seconds`；计数拆分 `suite_ran`/`flow_ran`/`repro_ran`（不再用单一 `ran`）。

### Phase 1B：候选仓库与 wflib 解析

9. 新增 `prepare_candidate_repo.py`：复制候选树 → `git init`/`add`/`commit`/`tag wf-v<version>`，
   产出干净、带 tag 的候选仓库根；校验 tag 可解析、`git status --porcelain` 干净、
   `wf-release.json` version 与 tag 一致；`candidate-repo.meta.json` 写在仓库根**外**（`<out>.meta.json`）；
   按 `tree_digest + version` 缓存，树/版本变化即重建。
10. 候选安装：`wf_fixture.sh` 增加 `--deploy dev|candidate`；candidate 调用候选仓库根的 `install.py`，
    `--source` 指向候选根；安装后核对 `.wf/install/installation.json` 的 version/ref/rules_digest，
    不是 `0.0.0-dev`；`run_all` candidate 模式下 `RELEASE_REPO`/`--source`/`run_f0`/`p5_*`/repro 全部消费候选。
11. 修 wflib 解析：`f1_init.py` 从 `$F/.wf/lib` 或 `WF_TEST_LIB` 导入 `wflib.records`，删除源码绝对路径
    与 `/tmp` 插入；`repro/_harness.py` 的 codes 表同样从 `$F/.wf/lib`/`WF_TEST_LIB` 解析，
    dev 回退源码仅用于 stage red；至少 T3 代表集涉及的套件改为 candidate-clean，其余保留
    `candidate_clean=false`（不得为“全绿”放宽候选证明）。
12. repro candidate 语义：`cases` 记录 `assertion_target`（source/installed/both）与
    `stage_role`（scaffold/target/both）；`candidate_clean=true` 仅当 `assertion_target=installed` 且
    `stage_role=scaffold` 且不读源码 `payload/lib`/codes 表；candidate 模式只跑 `candidate_clean=true` 用例，
    其余列入 `skipped_non_candidate`（不算通过）；整组没有 candidate_clean 时拒绝，或 `f1_candidate_smoke` 兜底。
13. 兜底候选闭环：若没有代表套件达到 candidate_clean，新增 CLI-only `f1_candidate_smoke`
    （候选安装 → 初始化/普通任务 → 复杂审查 → 归档）；不得用 dev 套件冒充候选证明。

### Phase 1C：最小清单与规范

14. 只新增 runner 所需最小清单：`suites.json`、`repro/groups.json`（够 `--representative`/`--group` 使用）；
    **不做**完整覆盖矩阵、不删除/合并历史套件。
15. `.trellis/spec/docs/wf-delivery-discipline.md` 只做 Phase 1 最小同步：四层命令、真子集、
    repro 默认 green、`--mode auto`/`--jobs`、candidate/test 发行边界；完整规范留后续。
16. 为新增运行器行为写测试（至少覆盖）：`WF_SUITES=r70_tests` 只跑 1 个套件；full 仍 149 个执行单元；
    representative 未设 `WF_WITH_REPRO` 也能跑 repro、subset 同参数被拒绝；green/red/auto/candidate
    的允许与拒绝；`--jobs 4` 与 `--jobs 1` 结果一致且 state 只由父进程写；测试发行/候选 meta 过期时
    `--no-build` 拒绝；候选仓库 tag/工作树/版本校验；套件失败、夹具失败、超时、结果缺失/重复、
    group 零匹配都非零退出。

## Constraints

- 不按文件名删除/合并历史套件；不做覆盖矩阵裁剪（Phase 2/4）。
- 不实现跨版本升级；`upgrade --apply` 未交付时只记录“升级未覆盖”。
- 不放宽安装器的 tag/摘要/身份校验。
- 不修改 `/tmp/scripts_wf_imporve.md`；发现事实错误单独报告。
- 不做与 Phase 1 无关的重构、文档润色或测试重命名。
- 不使用 `git checkout --`、`git reset --hard`、`git clean` 等丢弃用户工作的操作。
- 不提交、不推送，除非项目流程要求；如提交，只暂存本任务路径。
- `docs/workflows/wf-release` 是产品发行树，T1/T2 不得改写它。

## Acceptance Criteria

- [ ] `python3 -m unittest discover -s scripts/tests -t .` 全绿（含新增运行器测试）。
- [ ] `WF_SUITES="r70_tests" run_all.sh` 只执行 1 个执行单元（无 repro、无 r72、无 f0/p5）。
- [ ] `repro/run.sh --group review --mode green --no-build` 只跑 green；`--mode red` 只跑 red。
- [ ] `run_all.sh --full --repro green` 仍 149 个执行单元且 `GATE-OK`。
- [ ] `run_all.sh` 执行前后 `docs/workflows/wf-release` 树摘要不变（测试不写产品树）。
- [ ] `--representative` 不设 `WF_WITH_REPRO` 也能跑 repro；`--subset` 同参数被拒绝（非零退出）。
- [ ] `prepare_candidate_repo.py` 产物 tag 可解析、`git status --porcelain` 干净、version 与 tag 一致；
      candidate 安装后 `installation.json` 的 version/ref/rules_digest 与候选一致（非 `0.0.0-dev`）。
- [ ] 候选项目上 `f1_init`/`f1_candidate_smoke` 通过 `.wf/bin/wf.py` 跑通，且不读源码 `payload/lib`。
- [ ] 反向用例：套件失败、夹具失败、结果缺失/重复、group 零匹配、`--full`+`--subset`、
      subset 未开 `WF_WITH_REPRO`、meta 过期全部非零退出。
- [ ] 交付 `IMPLEMENTATION_NOTES`（方案稿章节 → 实际改动）与未验证假设清单、skipped 清单。
