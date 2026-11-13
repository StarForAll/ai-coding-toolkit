# Phase 1 执行计划

> 顺序执行；每步给出验证命令与回滚点。回滚点 = 该步只动列出的文件，失败时按文件回退。

## 1. 运行器骨架（plan.py + suites.json）

- [ ] 新建 `scripts/tests/wf_runtime/full/suites.json`：59 个 `kind=suite` + `r72_tests`(extra) +
      `d1_tests`/`d1_wf_tests`(manual) + `f1_candidate_smoke`(candidate)；flow 列表 4 项；
      代表集 6 个；`candidate_clean` 只给 `f1_candidate_smoke`。
- [ ] 新建 `scripts/tests/wf_runtime/full/plan.py`：`plan()` + `--format json|sh` + `--list`/`--dry-run`
      + 全部冲突规则（design §2）。
- [ ] 验证：`python3 plan.py --dry-run --format json` / 冲突用例 / `python3 -m unittest ...`（尚未加测试则先手跑）。

回滚点：只新增 2 个文件，`git checkout` 不涉及已跟踪文件。

## 2. run_all.sh 改为消费计划

- [ ] 参数解析整体交给 `plan.py`（`eval "$(python3 plan.py --format sh -- "$@")"`），失败透传退出码。
- [ ] gating：`run_extra` 仅 full 或选中 r72；flows 仅 full/representative；`run_repro` 按 plan。
- [ ] 测试发行（dev）：启动时 `wf_test_release.py` 构建/校验；`RELEASE_REPO` 指向测试发行缓存，
      `run_f0`/repro 用解析出的 ref/version。
- [ ] candidate：`wf_fixture.sh`/`run_f0`/`p5_*`/`repro` 全部带候选参数；不构建测试发行。
- [ ] 产品树摘要前后比对（`docs/workflows/wf-release`）。
- [ ] 计时/计数拆分 + `summary.json` + `plan.json`。
- [ ] 保留结果完整性检查（malformed/missing/dup/unexpected/xargs）。
- [ ] 验证：`WF_SUITES=r70_tests bash run_all.sh`（=1 单元）；`--full --repro both --dry-run`；
      `--full --subset`（非零）；`--subset` 无选择（非零）。

回滚点：`run_all.sh` 单文件。

## 3. repro/run.sh + select.py + groups.json

- [ ] `groups.json`：`review/archive/identity/writer/install` + `candidate_representative=["install"]`；
      组用显式用例名；`cases` 标注 install 组成员的 `assertion_target`/`stage_role`/`targets`。
- [ ] `select.py`：组/only 交集、candidate 过滤与复核、`auto` 新鲜度与状态、meta 校验、零匹配报错。
- [ ] `run.sh`：`--mode/--group/--only/--jobs/--fixture-deploy/--release-*/--no-build/--list`；
      worker 只写 `results/<case>.json` + 日志；父进程汇总后原子写 state；超时 kill 进程组；
      red 前置失败/注入后仍绿分别报错；输出 `REPRO_GREEN_SECONDS`/`REPRO_RED_SECONDS`/`SKIPPED_NON_CANDIDATE`。
- [ ] 验证：`--group review --mode green --no-build`；`--mode red`；`--group nope`（非零）；
      `--jobs 4` vs `--jobs 1` 结果一致。

回滚点：`repro/run.sh`、`groups.json`、`select.py`。

## 4. 测试发行隔离

- [ ] `scripts/wf_release_common.py`：`source_tree_digest()` / `manifest_digest()`。
- [ ] `scripts/tests/wf_test_release.py`：版本解析、安全输出根、原子替换、meta、`--verify-meta`、`--no-build`。
- [ ] `.gitignore`：忽略 `docs/workflows/.wf-release-meta.json`（T3 用）。
- [ ] 验证：首次构建 → 复用重建 → `--verify-meta`；改一个 payload 字节后 `--verify-meta` 失败；
      产品树摘要不变。

回滚点：3 个文件（`wf_release_common.py` 只加函数）。

## 5. 候选仓库 + 候选安装

- [ ] `prepare_candidate_repo.py`：复制/tag/校验/缓存/meta（仓库根外）。
- [ ] `wf_fixture.sh`：`--deploy`/`--release-*`/`--profile`；candidate 安装后核对 `installation.json`。
- [ ] `run_all.sh` candidate 透传。
- [ ] 验证：`build-wf-release.py --version 0.1.2` → `prepare_candidate_repo.py` →
      `wf_fixture.sh /tmp/x --deploy candidate --release-root ... --release-ref ... --release-version 0.1.2`，
      核对 `installation.json`；脏树/错 tag/错版本各跑一次负例。

回滚点：2 个文件 + run_all 参数段。

## 6. wflib 解析 + candidate_clean

- [ ] `f1_init.py`：`WF_TEST_LIB`/`$F/.wf/lib` → 源码回退；删除 `/tmp` 与源码绝对路径插入。
- [ ] `repro/_harness.py`：codes 表同源解析；`RELEASE`/`RELEASE_REF`/`RELEASE_VERSION` 环境化。
- [ ] `repro/_release.py`：去掉独立 `TAG` 常量来源，改由环境解析。
- [ ] `f1_candidate_smoke.py`：候选安装 → 初始化/普通任务 → 复杂审查（夹具两份协议报告 + 主会话复核）→ 归档。
- [ ] 验证：候选项目跑 `f1_init`；`f1_candidate_smoke`；grep 确认无源码 `payload/lib` 读取。

回滚点：4 个文件。

## 7. 测试与清单

- [ ] `scripts/tests/wf_runtime/test_test_runner_plan.py`：计划冲突/选择/gating/退出码。
- [ ] `scripts/tests/wf_runtime/test_repro_selection.py`：组/only/candidate_clean/auto 状态/零匹配。
- [ ] `scripts/tests/wf_runtime/test_test_release.py`：版本解析、meta 过期、安全输出根、所有权标记不在树内。
- [ ] `scripts/tests/wf_runtime/test_prepare_candidate_repo.py`：tag/干净/版本一致/缓存/meta 位置。
- [ ] `scripts/tests/wf_runtime/test_run_all_contract.py`：`--dry-run`/`--list` 计划形状（快）；
      失败传播（夹具失败、结果缺失/重复）用小规模假套件；
      `WF_SUITES=r70_tests` 真实跑用 `WF_SLOW_TESTS=1` 门控。
- [ ] 验证：`python3 -m unittest discover -s scripts/tests -t .`

## 8. 规范同步

- [ ] `.trellis/spec/docs/wf-delivery-discipline.md`：§8 四层命令 + 真子集 + repro 默认 green +
      `--mode auto`/`--jobs` + candidate/test 发行边界；§7 并行纪律补 repro `--jobs`。
- [ ] 验证：`python3 scripts/check-doc-refs.py`。

## 9. 收口

- [ ] `run_all.sh --full --repro green`（149 单元，GATE-OK）。
- [ ] `build-wf-release.py --verify` / `--verify-token-parity` / `validate-wf-design.py` / 技能校验。
- [ ] `IMPLEMENTATION_NOTES.md`（任务目录）：章节映射、未验证假设、skipped 清单。

## 门禁

- 任一步失败先归因，不改判据迁就绿灯。
- 不新增 `KNOWN_LEGACY` 豁免。
- 提交前复核 `git diff --stat`，只暂存本任务路径。
