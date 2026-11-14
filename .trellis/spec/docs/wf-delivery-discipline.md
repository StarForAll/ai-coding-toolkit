# wf 模块交付纪律（轮次收口的可执行契约）

> 适用范围：`docs/workflows/wf/**`（模块源码）、`docs/workflows/wf-framework-*.md`（三份上位稿）、
> `scripts/tests/wf_runtime/**`（用例）。来源：2026-11-12 的 `11-12-wf-round2` 任务——该任务的三轮审计
> 各漏一批义务，本文把"为什么漏"和"怎么核"固定下来，避免下次重新推导。

---

## 1. 轮次收口核对（Scope / Trigger）

**Trigger**：声称为某一轮（首轮/第二轮/第三轮）"已交付"之前。

**Contract**：以下三份清单**逐行**核过才算收口，缺一张都不算：

| 清单 | 位置 | 核什么 |
|---|---|---|
| 义务表 | 机制稿 §12.1（D 编号 → 机制节 → 轮次标签） | 该轮每一行的机制节是否都有实现 |
| 轮次表 | 实现稿 §6.4（第二轮/第三轮单列） | 该轮列出的能力是否逐项可用 |
| 实现面矩阵 | 实现稿 §7.2（G 编号 → 文件/命令 → 场景行） | 矩阵点名的**文件与函数**是否真有实现与用例 |

**反例（真实发生）**：第二轮曾按"命令从 `WF_CAPABILITY_UNAVAILABLE` 变可跑"验收，于是漏掉 G05 点名的
`wflib/gates.py`（实例绑定时 `gate` 仍抛能力不可用）与 G04 点名的 `runs.py::load_definition`（抛桩、零调用者）。
两张表绿、契约没落实。

**Rule**：验收判据写成"**文档点名的实现面 → 有实现 + 有能区分的断言**"，不写成"命令名可跑"。

---

## 2. 机制义务逐句核（不只核主流程）

**Contract**：每条机制义务按**句子**核对，尤其这段里容易被当成"叙述"的过程义务：
- "**预览**/逐个列出"（§6.3 替换、§7.4 异常终止）
- "**授权提交**并只读确认持久化"（§5.1、§7.4）
- "**并 release**""保存交接/工作区"（§6.2 返工普通分支）
- "未持权只报告待复评"（§6.2）
- "报告四类各自 passed/failed/unknown 及未覆盖对象"（§8.5）

**Wrong**：`run terminate` 只写终态、直接 `done`，把"固定提交步骤"当成可选。
**Correct**：动作 steps 增 `persist_record`，无授权停在 `persist_pending` 并如实说明（§5.1 的终态语义）。

**Rule**：句子里的动词（预览/列出/保存/释放/提交/报告）都是义务；主流程跑通不等于义务落实。

---

## 3. 双模 repro 的契约

**Contract**：`scripts/tests/wf_runtime/full/repro/<name>.py` 必须同时过两面：

| 面 | 命令 | 含义 |
|---|---|---|
| green | `python3 repro/x.py --expect green` | 正确实现上断言成立 |
| red | `WF_REPRO_INJECT=1 python3 repro/x.py --expect red` | 注入缺陷后**目标断言**变红 |

**注入必须可达**：注入后用 `patch()` / `_harness` 改的代码必须真的在目标路径上执行。三层守卫（绑定 + 写权 + 幂等）
会让"重入/二次调用"类缺陷注入不可达——此时**改注入单层可观察事实**（如 `run_id` 取值、快照字节、记录字段），
不要伪造一个到不了的缺陷。
**反例**：三次注入落在守卫外（`dep` 自环双锁、`run create` / `run advance` 的三重守卫），red 面形同虚设。

---

## 4. 同一判定只有一处实现

**Contract**：同一判据被多个入口需要时，抽一处实现并参数化输入，调用点不各自复制：

| 判据 | 唯一实现 | 消费者 |
|---|---|---|
| 放弃一个任务 | `tasks._apply_abandon()` | `task-abandon`、`run terminate`、`task-replace` |
| 定义加载 | `runs.load_definition()` | `definition validate/prepare`、`run create` |
| 归属存疑（d 档） | `scope.cross_task_conflicts(root, task, touch_paths)` | `check`、`inspect` |
| 实例可绑定资格 | `cli._eligible_run_bind()` | `bind --run`、`ready` |
| 复评写权事实 | `tasks.reassess_write_right()` | `task-reassess` |

**Wrong**：`check` 自己再算一遍 `cross_task_conflicts` → 两处判定、一次注入改不动全部（red 面失效）。
**Correct**：`touch_paths` 作为参数传入，只推导一次。

---

## 5. 新增资产 / 字段的登记链

**Contract**：新增 payload 文件或记录字段，同批完成四项：

1. `docs/workflows/wf/dev-manifest.json` 增 asset 条目（否则发行预检的清单/源码树不一致会失败）；
2. `scripts/build-wf-release.py --version 0.1.0` 重建发行树（单独一笔 `chore(wf): 重建发行树` 提交）；
3. 机制稿的字段表登记（判定字段）或"只读信息字段"登记（如 `paused_reason`/`resumed`/`closing.pending`）；
4. 写者、消费者与失败出口各写清（机制稿 §1.1 的登记纪律）。

**反例**：`wf-judging` 删除时只改源码不动 manifest → 预检失败；`handoff.wip` 在返工分支漏写 → 新会话看不到未提交改动。

---

## 6. "有实现、无断言" = 未验证，必须登记或补断言

**Contract**：任何分支若只有实现、没有能区分的断言，收口时二选一：补断言，或写进任务的"无断言清单"并说明为什么现在补不了。

**为什么**：本任务两次因此抓到真缺陷——`_previous_task_step` 不过滤被略过的任务步骤（会报 `WF_DEPENDENCY_UNMET`）、
返工普通分支不写 `handoff.wip`。两处都是"读代码像对、跑起来才不对"。

**Tests Required（断言点）**：每条分支至少一条断言锚在**行为**上（记录字段/返回码/下游重连/写权状态），不锚排版或文案。

---

## 7. 并行纪律：`run_all.sh` 独占夹具

`run_all.sh` 使用 `/tmp/wf-fixtures/*` 与**测试发行副本**（默认 `~/.cache/wf-test-release/<version>`，
不重建产品树 `docs/workflows/wf-release`）。入口持全局 `flock`：第二个根运行器在写夹具前拒绝；
嵌套运行器校验祖先进程仍持有内核锁。worker 在私有 `/tmp` 持局部锁，只共享结果和只读输入。
单跑某套件用 `WF_SUITES="<name>" bash scripts/tests/wf_runtime/full/run_all.sh`
（它会自己重建夹具），不要直接 `python3 rXX_tests.py`。

两层并行是**分开**的开关，互不继承：

| 层 | 开关 | 默认 | 说明 |
|---|---|---|---|
| 单元层（suite/flow/extra 同池） | `--serial` / `WF_TOTAL_JOBS`（兼容 `WF_JOBS`） | 并行（min(8, cpu_count)） | `unshare` + bind mount；`--serial` 或 `WF_JOBS=1` 退回宿主 `/tmp` + 无 `unshare` 的串行域（确定性、排障、AC1 对拍面） |
| repro 用例层 | `WF_REPRO_JOBS` / `repro/run.sh --jobs` | run_all 为 min(8, cpu_count)，独立入口为 1 | 每用例独立 `mkdtemp`，父进程独占写 `repro-state.json`；`--jobs 4` 与 `--jobs 1` 结果逐项一致 |

**串行集合（2026-11-14 清空，任务 11-13-wf-runner-speed-quality）**：原 13 个强制串行
套件全部转入并行池——chmod 写入失败注入改由 `wfdrive.deny_writes` 三探针等价契约承担
（chmod 层 + ro bind mount 层按探针结果选择，fail-closed；空目录注入由助手哨兵统一）；
其余 11 个保守遗留项经五项审计（夹具来源/共享路径/用户状态/pty·sleep/嵌套运行器）确认
并行安全。今后确需串行的单元：`units.json` 置 `"parallel": false` 并在 `notes` 登记
具体理由（`load_units` 校验 notes 非空，防无理由串行回潮）。`--isolated-user` 特判
（cp3/r1r2）由 `units.json` 的 `isolated_user` 字段经 `PLAN_ISOLATED_UNITS` 下发为
`WF_ISOLATED_UNITS`，run_all/run_one 同一成员判定——套件特判不进 bash 分支。

**注册表与记录（2026-11-14 起）**：注册表是 `units.json`（顶层 `units`，schema 2），
四类可计划单元（suite/flow/extra/candidate）同池，每条声明 `expect`/`fixture`/`script`；
`plan.py` 是唯一计划源，输出五段记录 `name:kind:expect:fixture:script`（`PLAN_UNITS` /
`PLAN_UNITS_PARALLEL` / `PLAN_UNITS_SERIAL`）。worker 只消费记录：`kind` 到
`execution.py --kind` 的映射（suite|candidate→suite、flow|extra→flow）、`script` 来源、
夹具分派（template/install）都只在 `run_one.sh` 一处。**不要按 `<name>.py` 拼脚本**
（`f0` 的执行脚本是 `p5_f0.py`）。`--expected` 与 `execution.verdict` 的 observed 比较：
少跑/多跑用例都会让整次运行变红。

**结果缓存轮转（2026-11-14 起）**：run_all（`--scope run`）与独立 repro 入口
（`--scope repro`）在 `prepare-results` 之后各自回收本前缀的带 marker 结果目录，保留
最近 20；root 经 `WF_RESULTS_CACHE` 注入（默认 `~/.cache/wf-test-run`）——r67 假环境与
契约测试必须指向临时根，不触碰真实用户缓存。`--bootstrap`（仅手工执行）额外回收无主
但顶层内容全部为已知产物的历史目录；liveness 保障隐式依赖全局 flock 单运行器。
直接 `plan.py --list` 不再创建结果目录；显式 `WF_RESULTS_DIR` 时 plan.json 仍镜像写入
（`test_dry_run_only_prints_plan` 消费该行为）。

**SUT 驱动解释器契约（2026-11-14 起，不得当纯清理）**：被测 `wf.py` 的驱动解释器
默认保持**异于运行器的解释器**（`wfdrive.PYTHON` / `_harness.WF_PYTHON` 两处单点默认，
`WF_TEST_PYTHON` 可覆盖）——`wflib/session.py::l2_anchor` 跳过与自身同解释器的祖先，
统一解释器会把进程锚点推出 harness 之外（随调用方环境漂移、不可复现，自动会话入口
`WF_IDENTITY_UNRESOLVED`）；full 层没有任何断言消费真实进程锚点，所以"统一"是无断言
覆盖的 SUT 可见行为变更。工具侧（install.py/wf-dev-deploy.py 启动）用
`wfdrive.TOOL_PYTHON = sys.executable`，与 SUT 驱动面不共用默认。数据侧
`/usr/bin/python3` 断言字面量不动（白名单 + 守恒校验）。

并行/串行的等价性要**定期对拍**（改 runner 后至少一次）：跑一次 `--full --repro green` 和一次
`--full --repro green --serial`，比对两份 `RESULTS_DIR/lines`（套件名/rc/status）、`repro/*.json`
（逐用例 mode/green/red/verified）与流程行的 `rc/PASS=`。除运行期 id（task id 等）外必须逐项相等。
2026-11-13 实测：59 套件 + 85 repro + 5 流程全部相等，并行 204s / 串行 301s。

**选择器**：`WF_SUITES`（套件名）、`WF_TAGS`（tag，多值取并集）都隐含 `--subset`；两者同时给出取**交集**，
为空即报错。未知套件/tag 一律非零并列出可选值。`--changed`/`--changed-files` 只产出建议
（`units.json` 的 `modules`：精确文件键优先，其次最长目录前缀；未映射的改动单列，不猜），
必须配合 `--list`，不自动执行。

**夹具模板（run 内构建 + 跨 run 缓存，2026-11-14 起）**：`run_all` 构建一次
`wf_fixture.sh + f1_init.py` 的产物当**只读模板**，每个单元通过 `fixture_scope.clone` 复制到独立目录。
复制不会搬走记录里的绝对路径与外部暂存目录，所以复制后必须
`template_check.py <dir> --repoint-from <源> --expect-repoint-min 1`：`.wf/bin/wf.py` 与安装记录都在、
candidate 模式下 version/ref 仍等于本次候选、记录里的旧前缀被改写成当前项目、且**至少改写 1 个文件**。
**安装记录会按安装时的绝对路径登记技能根（`installation.json` 的 `assets[].root_ref`）**，
`recovery.md` 里也有 `python3 <项目>/.wf/bin/wf.py` 的绝对路径——不迁移的后果不是报错，而是后续
uninstall/reinstall 类入口去操作**模板目录**（共享可变状态、静默串味）；改写 0 个说明记录与
`meta.root` 不一致，该单元直接失败（`TEMPLATE-REPOINT-MISMATCH`）。

跨 run 缓存载体是 `<WF_RESULTS_CACHE>/template/<key>/` + 同级 `<key>.meta.json`
（`key = <payload_digest12>-<pyver>-<deploy>[-<version>-<ref>]`；dev 的 ref 是 `dev:<git describe>`，
与安装记录登记的 `source_commit`/`release_ref` 同源——提交变化即换 key，不能只按 payload 摘要复用）。
发布序列：构建 `<key>.build` → 校验 → 挪旧条目 → move 到 `<key>` → `--repoint-from <key>.build
--expect-repoint-min 1` → **最后**写 meta（`root=realpath(<key>)`）。**没有 meta 的条目一律无效**；
命中要求 `meta.root == realpath(条目)`、空态/身份校验通过、条目内**零 pyc/`__pycache__`**
（`source_hygiene.py check --strict`）。任一步失败 → 挪陈旧 + 重建，不静默复用。
排障用 `--no-template`（整套模板机制，含缓存）或 `--no-template-cache`（只关跨 run 缓存）。
模板缓存条目只读：任何重锚定都发生在克隆产物上。

**pyc 策略（2026-11-14 起）**：运行器统一下发 `PYTHONPYCACHEPREFIX`（默认 `$RESULTS_DIR/pycache`，
`WF_PYCACHE` 可注入），**不再** `PYTHONDONTWRITEBYTECODE`。pyc 不落源树、不落夹具；`source_hygiene.py`
在 run 前后做 delta 对拍（新增即 `SOURCE-TREE-POLLUTED`，存量只警告 + 给清理命令），模板缓存条目用
strict 绝对判据。手工跑单元层也要带前缀（见 §8 T0）。

**运行中不要编辑 runner 文件**：`bash` 按偏移增量读取脚本，运行期间改 `run_all.sh`/`run_one.sh`/
`repro/run.sh`/`plan.py` 会让运行中的实例读到错位内容，结果不可信（2026-11-13 实测：
一次全量因此作废重跑）。要改就先停掉运行，改完按下面的顺序重验。

**验证顺序（省墙钟，别一上来就全量）**：

```bash
python3 -m unittest discover -s scripts/tests -t .            # T0  ~4s
WF_SLOW_TESTS=1 python3 -m unittest scripts.tests.wf_runtime.test_run_all_contract  # 契约 ~25s
WF_SUITES="r67_tests r70_tests" bash .../run_all.sh           # 冒烟 ~20s（r67 是唯一复制 run_all 的套件）
bash .../run_all.sh --representative --repro green            # 预收口 ~3min
bash .../run_all.sh --full --repro green                      # T2 收口，一次
```

---

## 8. 收口前的最小证据集（四层）

**只在对应层付出对应成本**：全量入口不承担“每次编辑后的快速反馈”。

| 层 | 何时 | 命令 |
|---|---|---|
| T0 快速 | 每次编辑后（<10s） | `PYTHONPYCACHEPREFIX=/tmp/wf-unit-pycache /softwares/python/bin/python3 -m unittest discover -s scripts/tests -t .`（已包含 `wf_runtime`/`wf_review`，**不再重复跑子目录**；前缀保证 pyc 不落源树） |
| T1 定向 | 改动命中模块时（<2min） | `bash scripts/tests/wf_runtime/full/run_all.sh --list --changed`（看建议，不执行）<br>`WF_TAGS=review bash .../run_all.sh` 或 `WF_SUITES="r68_tests r70_tests" bash .../run_all.sh`<br>`bash .../repro/run.sh --group review --mode green --no-build` |
| T2 阶段收口 | 任务收口/合并前 | `bash scripts/tests/wf_runtime/full/run_all.sh --full --repro green`（59 套件 + 4 流程 + r72 + green repro）+ 单元层<br>`python3 scripts/build-wf-release.py --verify --verify-token-parity`<br>`python3 scripts/validate-wf-design.py`、`python3 scripts/check-doc-refs.py`、`./scripts/validate-skills.sh` |
| T3 发行 | 发行前 | `bash .../run_all.sh --full --repro both`（red 只在这一层全量）<br>`python3 scripts/build-wf-release.py --version <X.Y.Z>`<br>`python3 scripts/tests/wf_runtime/full/prepare_candidate_repo.py --tree docs/workflows/wf-release --version <X.Y.Z> --out ~/.cache/wf-candidate-repo/<X.Y.Z>`<br>`bash .../run_all.sh --representative --repro green --repro-group install --fixture-deploy candidate --release-root <候选仓库根> --release-ref refs/tags/wf-v<X.Y.Z> --release-version <X.Y.Z>`<br>+ `build-wf-release.py --verify --verify-token-parity` |

边界（Phase 1 起的硬约束）：

1. **子集是真子集**：`WF_SUITES=...` 只跑选中的套件；`r72`/`repro`/`f0`/`p5_*` 不再隐式执行。
   子集要跑 repro 必须显式 `WF_WITH_REPRO=1`（`--full`/`--representative` 不需要）。
2. **repro 默认 green**：`run_all` 的全量/代表集默认 `--repro green`；red 只在 T3 或断言变更时跑。
   独立 `repro/run.sh` 的默认仍是 `both`（兼容旧调用）。
3. **`--mode auto` 是 red 闸门**：首次运行、新用例、helper/脚本/被测 payload 目标变化 → 该用例 both；
   未变化 → green；candidate 模式遇到“需要 both”直接报错，要求先在 dev 模式跑 red。
4. **发行边界**：T1/T2 只用测试发行副本（`~/.cache/wf-test-release/<version>` + `test-release-meta.json`），
   绝不改写产品发行树；T3 用**带 tag 的候选仓库根**（`prepare_candidate_repo.py` 产物），
   candidate 夹具必须由候选 `install.py` 部署并核对 `installation.json` 的 version/ref/rules_digest。
5. **`--no-build` 必须校验新鲜度**：测试发行 meta 或 `<候选根>.meta.json` 与当前源树/树摘要不一致 →
   拒绝运行，不静默使用旧副本。
6. **candidate 只认 candidate-clean**：repro 用例须同时满足 `assertion_target=installed` 与
   `stage_role=scaffold`；其余列入 `skipped_non_candidate`，**不算通过**；套件侧 `candidate_clean=false`
   的不得用于候选证明（大量历史套件仍硬编码源码 `payload/lib`）。
7. **red 的语义**：前置失败不算 red 成功；注入后仍绿必须失败并输出目标断言。
8. **失败传播不降级**：套件退出码、夹具/`f1_init` 失败、结果行缺失/重复/畸形、子进程崩溃/超时、
   repro 前置失败、分组零匹配、汇总数字不一致——任一都让 `run_all` 非零退出。

任一失败先归因（实现缺陷 → 修实现；实现正确但事实不足 → 才回修机制稿），不改判据迁就绿灯。

---

## 9. 审查材料与交付集合（2026-11-12 第二轮 dogfood）

**Trigger**：改动 `review.context` 的材料生成、`check.object_paths`、`pending_delivery_paths`、
写权代次读取、或 `task-approve` 帮助文本时。

**Contract**：

| 判据 | 唯一实现 | 调用点只消费 | 断言锚点（`scripts/tests/wf_runtime/`） |
|---|---|---|---|
| 本任务交付集合 | `scope.delivery_set()` | `check.object_paths`、`review.context`、`tasks.pending_delivery_paths` | `test_delivery_set.py` |
| 材料片段生成 | `review.materialize_delivery()` | `review.context` | `test_material_diff.py` |
| 写权代次来源 | `cli.resolve_generation()` + `writer.sync_session_generation()` | `Context.require_held` | `test_generation_carry.py` |
| Check 下一跳 | `tasks.check_next_hint()` | `cmd_task_check` | `test_check_next_route.py` |
| 帮助取值域 | `decisions.DOMAINS` | `cli.COMMAND_HELP` | `test_help_domains.py` |

**反例（真实发生，dogfood F13/A#4）**：`_material_diff` 注释写着"必须含未跟踪新文件"，
实现却只跑 `git diff [HEAD] -- path`——未跟踪文件两种调用都是 0 字节，异常还被吞成
`owned=[]`，最后写成 `# 无工作树差异`。注释引用了历史反例、实现复现了历史反例。

**Wrong**：
```python
diff = _material_diff(ctx, record)
records.atomic_write(..., diff or "# 无工作树差异\n")
```

**Correct**：
```python
delivery = scope.delivery_set(ctx.root, record)          # 唯一交付集合
material = review.materialize_delivery(ctx.root, delivery["paths"])
# 未跟踪 → git diff --no-index /dev/null <path>；失败 → problems + [wf-material-missing]
```

**Rule**：
- "无差异"只能由**交付集合为空**推出；生成失败必须写进 `materials/status.json.problems`
  并在正文留 `[wf-material-missing]`，不得与"无差异"共用一句文案。
- 写权代次取"本会话取得写权时的值"（会话运行态侧车），**不得**改读 writer 当前代次；
  侧车陈旧必须仍被 `WF_GENERATION_STALE` 拦下。
- 帮助/示例里的取值域从登记表生成，不在第二处手写（`approve-light` 残留就是这么来的）。
- 文档与实现的忽略集合冲突时，以发行清单 `gitignore_managed` 为唯一枚举，安装器缺该字段即拒绝。
- 新增断言必须做过回退注入验证：临时改回旧实现时用例变红，恢复后字节一致
  （本轮对 R1/R2/R3/R5 各做了一次，见任务 `implement.md` 的收口自检）。

---

## 10. 审查输入面、外发授权与夹具的联动（2026-11-13）

**Trigger**：改动 `review.report_input_problems` / `drop`-allowlist 脱敏 / `review-launch` 的
材料与范围校验 / `check.anchor_parts` / 验证日志落盘 / 任何"新增判定字段或决策域"时。

**Contract**：

| 判据 | 唯一实现 | 同批必须核 |
|---|---|---|
| 报告输入面（状态头/必需字段/读取与排除范围/轴与 verdict） | `review.report_input_problems` | `lint`、导入、判定三处调用同一实现；`test_report_input_single_source.py` 断言同名 check 三处一致 |
| 未覆盖轴与缺口接受 | `review.coverage_state` + `review.gap_acceptance` | 全未覆盖=输入不成立；部分未覆盖须人接受（`--gap-acceptance`）；`test_review_coverage.py` |
| 外发确认范围 | `authorize.export_scope`（`scope_digest` = task + materials） | 旧确认无 `scope_digest` 一律要求补录；夹具里的 export 决定必须带 `task` + `materials` |
| 脱敏入库 | `authorize.redact`（保留白名单） | 未知字段/嵌套结构一律丢弃；`quote` 只留遮罩摘要 |
| 材料差异源 | `review.materialize_delivery(base=task.baseline_head)` | 已提交的中途改动必须出现在 `diff.patch`；基线不可达要如实报 |
| 验证日志 | `check._log_payload`（头 64 KiB + 尾 192 KiB） | 截断必须可见；记录只留 summary+digest |
| 实例定义快照 | `check.workflow_snapshot_digest` | 实例任务缺快照报 `WF_RECORD_INVALID`，不折 null |

**夹具联动（本次实测）**：把外发确认加成"task + materials"、把报告加首行 `status=done` 之后，
`full/run_all.sh` 从 12 项失败回到 149 项全过。原因是 **12 个失败全部来自夹具没有跟上接口**，
不是实现回归。**Rule**：改输入面/外发守卫的同一批，先跑
`WF_SUITES="<受影响的套件>" bash scripts/tests/wf_runtime/full/run_all.sh` 与
`bash scripts/tests/wf_runtime/full/repro/run.sh --no-build`，再跑全量；
`run_all.sh` 只构建/校验测试发行缓存；收尾核对产品树摘要不变，不再用历史版本覆盖产品树。

**新增字段/域的登记实例（照此四件套）**：`workspace_exclusion` 决策域 →
`execution.workspace_exclusions` 字段 → 机制稿 §1.1/§1.3/§3.5 登记 + 实现稿 §2.3 域表 →
`test_workspace_exclusion.py`（含幂等与失效两负例）。

**复审补充（2026-11-13）**：改入口参数或新增判定事实时，同批核四件**自述面**，缺一件即算遗留——
`COMMAND_HELP`（`wf help` 是唯一自述来源，必填/可选必须与实现一致）、`status`/`review-status` 的事实投影
（新事实必须在状态页可见，否则 AI 拿到需人裁决档却不知道怎么走）、任务记录模板（机制稿写"初值空数组"
就必须在 `new_task_record` 里真的建这个键）、脱敏规则（中文凭据词 `口令/密码/密钥/令牌/私钥` 也属遮罩范围；
人写的 quote 只入遮罩摘要 + digest，不入原文）。

## 11. 审查判定：主会话复核与两源覆盖（2026-11-13）

**Trigger**：改动 `review.decide`、`review.validate_main_review`、`review.merged_coverage`、
报告输入面、`review-context` facts、归档收尾或 `writer release` 时。

**Contract**：

| 判据 | 唯一实现 | 同批必须核 |
|---|---|---|
| 主会话五轴复核 | `review.validate_main_review` | `review-decide --main-review` 产生 verdict 时必填；`--main-review-draft` 只生成骨架、不写记录；`reviews.main_reviews[]` 按 `(round, file_digest)` 幂等，判定后不可替换 |
| 本轮覆盖 | `review.merged_coverage` | 轴由主会话复核或任一报告 `pass/fail` 覆盖；两者都未覆盖才是缺口；全未覆盖 = 输入不成立；`review-status` 同源投影 `main_review_ready`/`sources` |
| 报告边界 | `review.report_input_problems` | `read-scope` 与 `excluded-scope` 不得交叠（lint/import/decide 同源）；`scope-exceptions`/`material-gaps` 不再消费；全轴 uncovered 的报告自报 `unavailable` |
| reviewer 入口范围 | `review.context` | facts 返回 `submitted_scope`/`readable_scope`/`exclusions`；`readable_scope.business_code=["**"]`、`focus_paths` 是审查重点不是读取上限 |
| 归档收尾 | `tasks._release_after_archive` + `cli._release_writer_locked` | 正常归档持久化成功后锁内释放；释放失败只写 `write_release` facts，不反转归档结果；`writer release` 空闲时幂等成功 |
| 旧口径 | skill/README/注释 | `bind --run`、`run create/advance/pause/resume/locate/terminate/finish` 已交付；`upgrade --apply` 仍第三轮；自动模式 `generation` 不必填；diff 比任务基线；报告名 `review-<agent>.md` |

**夹具联动**：`wfdrive.write_main_review` / `_review_flow.main_review` 生成夹具复核；
`r68/r69/r70/r71/r75` 的 `imported` 槽位必须与复核 `report_review` 一致，finding 必须带 `slot`
（同 id 多槽位时 `finding_refs` 也要带 `slot`）。`f1_init` 直接断言 `archive.facts.write_release.released`，
不再单独调 `writer release`；`r31` 模拟归档中断时先重新 `writer acquire` 再续做。

**反例（本轮修复的失败）**：`scope-exceptions` 自述越界只进 gaps、`read-scope: [".env"]` 与排除面并存仍 pass；
A 全 pass、B 全 uncovered 仍算全覆盖；归档后 `writer release` 返回 `WF_SEMANTIC_DECISION` 把 fixture 初始化打断；
`review-decide` 缺主会话复核时直接按报告 pass。

**Tests Required**：
- `scripts/tests/wf_review/test_review_coverage.py`：无主会话复核 → `WF_SEMANTIC_DECISION`；主会话覆盖 reviewer 缺口 → pass；两源都未覆盖 → 缺口；`fail` 无 finding → 需人裁决；`pass` 不能覆盖未关闭 blocking；复核判定后不可替换。
- `scripts/tests/wf_review/test_report_boundary.py`：`read-scope` 与 `excluded-scope` 矛盾在 lint/input 同源；`scope-exceptions`/`material-gaps` 不再产生缺口/失败；全 uncovered 报告自报 `unavailable`；`review-context` 返回授权范围。
- `scripts/tests/wf_runtime/test_archive_writer_release.py`：归档释放成功、失败只报告、空闲幂等。
- `scripts/tests/wf_runtime/test_envelope_cache.py`：按 `session_id`/`issued_id` 分文件，缺标识不缓存。
- 全量：`python3 -m unittest discover -s scripts/tests`；`WF_JOBS=1 bash scripts/tests/wf_runtime/full/run_all.sh`。

**Wrong vs Correct**：
- Wrong：`review-decide` 只按两份报告算覆盖，A 全 pass、B 全 uncovered 仍 pass。
- Correct：先 `--main-review-draft` 生成五轴复核，主会话填自己的结论与逐报告/逐 finding 复核，再用 `--main-review` 判定；报告未覆盖的轴由主会话补足，两者都未覆盖才交人。


## 12. wf 测试运行器的执行与证据契约

### 1. Scope / Trigger

修改 `scripts/tests/wf_runtime/full` 的执行、选择、夹具、计量与缓存时遵守本节。完整验证是单元层加集成层；字段变体迁移必须逐条映射旧断言，不能只比较 suite 数量。

### 2. Signatures

- `execution.run(argv, log_path, *, timeout, cwd=None, env=None)`：完整 stdout/stderr 日志、单调时间、退出原因、进程清理。
- `execution.verdict(log_path, rc, kind, expected=None)`：集中适配 suite/flow/steps/repro；任意 PASS 子串不算断言。**PASS 计数的唯一消费来源是结果 JSON 的 `assertion_result`**（run_all.sh 不在 shell 里复制行文法判定）；套件输出契约（三汇总行格式 + PASS/FAIL 行文法 + steps 终态）文档化在 execution.py 模块 docstring。
- `fixture_scope reset|clone|move|remove|claim-results|prepare-results|lease|check-lease|prune-results`：临时目录归属、运行互斥与结果缓存轮转（prune-results：marker 门控 + `--scope run|repro` 前缀隔离 + `--keep N` + `--exclude` + `--bootstrap` 仅手工；root 经 `WF_RESULTS_CACHE` 注入）。`move` 只用于模板缓存发布/失效：要求 marker 存在且 owner 匹配，搬动后重写 marker（`remove` 仍严格比对 `root`）。
- `repro_select.input_fingerprint(case)`、`auto_modes(cases, groups_doc)`、`commit_state(results_dir)`：repro 新鲜度与唯一状态写者。

### 3. Contracts

`WF_COMMAND_TIMEOUT` 默认 180 秒，`WF_REPRO_TIMEOUT` 默认 120 秒，根运行器的 `WF_RUN_TIMEOUT` 默认 1800 秒。超时、中断、非零退出和断言不成立分别记原因，均不能成功。所有阶段保留日志与结果；初始化失败不继续构造半成品套件。缺 worker 结果直接失败，禁止自动串行重跑覆盖原尝试。

夹具只能是安全临时路径或专用测试缓存内目录。非空目录须有匹配其规范路径的所有权标记；符号链接、与项目/发行/结果重叠的夹具拒绝。结束清理自身夹具和模板，保留日志；不自动接管历史目录。`cp3/r1r2` 使用合成执行器确认集合和临时 HOME，不复制真人确认记录；夹具 Git 忽略测试生成的 check-logs，不依赖全局 Git 配置。

`summary`（schema 2）的 `requested_jobs/effective_jobs`、`execution_mode/fallback_reason` 分别描述请求和实际；
`pool_seconds`/`repro_seconds`/`startup_seconds` 是分段墙钟，`budget` 只报告（60s 目标 / 65s 硬阈值，任意机器硬失败会假红）。
`suite_ran/flow_ran` 由 `lines` × 注册表 `kind` 一次派生（`suite|candidate`→suite_ran，`flow|extra`→flow_ran），
计数不变式：`lines == suite_ran + flow_ran`、`units_total == suite_ran + flow_ran + repro_ran`、
`repro_ran == repro 执行体的 REPRO_TOTAL`（repro 用例不写 `lines`，不与行数比较）。
`template_reused` 的口径是“本次 run 内共用同一夹具源”（run 内构建或缓存条目都算），跨 run 命中看
`template_cache_hit`/`template_source`。`init_seconds/suite_seconds` 是**全部执行单元**累计，`total_seconds` 是墙钟。shell 阶段时间用 `/proc/uptime`（10ms 粒度），单命令与**套件耗时**用 `time.monotonic`（run_one 的套件段读 execution 结果 JSON 的 `seconds`，init 段不经 execution 保留本地计时）；不要以伪毫秒整数宣称测量精度。

repro schema 2 每个用例分别记录 green/red 的 `fingerprint/verified_at`。输入包含完整源树、脚本、helper、目标、清单和执行协议摘要。green 不能更新 red；局部执行不能刷新其他 case。旧 schema 1 只作 legacy 留存并要求 both；损坏或未知 schema 明确拒绝覆盖。未知/不存在目标不得生成可复用的 red 证据。运行前冻结、运行后与状态提交前重核摘要。

### 4. Validation & Error Matrix

| 输入/故障 | 结果 |
|---|---|
| rc 非零却 status=ok；缺失/重复/畸形/计划外结果 | 非零，保留原始结果 |
| 字段级失败/零断言/不完整 suite 汇总 | 非零；步骤型输出需全部 WF_OK 和终态 TASK_ID |
| 用例模式/身份/阶段与计划矛盾 | repro 汇总失败，不写可信状态 |
| 测试输入运行中变化；旧 red 摘要不符 | 拒绝证据；auto 要求 both |
| 无主非空目录/符号链接/保护路径 | FIXTURE-REFUSED，哨兵字节不变 |
| 第二个根运行器重叠 | 租约拒绝，不删除对方夹具 |
| unshare 不可用 | 整次按计划回到串行，记录原因；worker 已启动后挂载失败则计失败 |
| 超时/取消/状态写入失败 | 明确非零，保存日志和原因 |

### 5. Good / Base / Bad Cases

Good：同一输入完成 both 后 auto 仅 green；目标变化后先 green 再 auto，仍要 both。
Base：无旧缓存时 both；无主旧夹具时选择新临时路径。
Bad：沿用旧 `verified_both_at` 给新摘要背书；把宿主夹具父目录挂回 worker `/tmp`；自动重跑后覆盖失败证据。

### 6. Tests Required

- `test_repro_selection`：green 不续签 red、helper 子集不刷新旁例、旧状态失效、损坏不覆盖。
- `test_execution`：非零退出和双流日志、阻塞读取/子孙进程超时、真实只读挂载与结果回传、文本适配拒绝假绿。
- `test_fixture_scope`：哨兵不变、符号链接/重叠拒绝、根运行互斥、归属后重建及结果清理。
- `test_results_gate`：矛盾 rc/status、无效时间、缺行/重行、shell 列表引用和 repro 模式一致性。
- `test_runner_hygiene`：G1 `/tmp` 导入注入零命中、G2 pyc 策略、G3 `.gitignore`、G8 假树静态引用全部归类、G9 缺根容错。
- `test_runner_budgets`：`wf.py status`（pyc 预热）5 次中位数 < 500ms（唯一阈值；`WF_PERF_GUARD=0` 显式关闭）。
- `WF_SLOW_TESTS=1` 的运行器/模板契约；候选代表闭环；full green 并行和串行逐项对拍。
- `/proc` 会话 leader 不可见时，用 `setsid --wait /softwares/python/bin/python3 -B -m unittest discover -s scripts/tests -t .` 建立可验证会话，不改产品锚点规则。

### 7. Wrong vs Correct

Wrong：`green` 成功时刷新旧 `verified_both_at`，随后 auto 跳过新代码的 red。
Correct：只写本次成功面的输入指纹；auto 比较当前指纹和 red 证据，缺失/不符即 both。
