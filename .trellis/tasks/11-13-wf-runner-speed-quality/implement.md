# 执行计划 — wf 测试运行器提速与质量修正

> 纪律前提（交付纪律 §7）：**运行中不编辑 runner 文件**——每步改完先停掉所有运行再改；
> 每步之后跑 T0；涉及 runner 契约的步骤（1/6/7/8/9）之后必须加跑 r67 回归——
> r67_tests 复制 run_all.sh/plan.py/suites.json/execution.py/fixture_scope.py 构造假环境，
> 契约不兼容在它那里表现为"假环境缺文件/缺 env"，不得当 flake 吞掉。

## Step 0 — 基线锚定与证据归档

- [x] 记录基线：`~/.cache/wf-test-run/run-1964465/summary.json`（并行 204s）与
      `/tmp/wf-runner-audit/delivery-full/`（174.99s，易失，仅参考）；记录
      `~/.cache/wf-test-run` 当前目录数（489 = run-* 485 + repro-* 4）与磁盘占用。
      → 实测：312MB；run-* 485 + repro-* 4（其中 3 目录 + repro-state.json）；
      174.99s 证据仍在 /tmp（2026-11-14 检查）。
- [x] **归档基线证据**（bootstrap 前置，它们无 marker、内容白名单合格，会被清理）：
      把 `run-1964465` 与 `run-2034392` 的 `summary.json`、`lines` 复制进本任务目录
      `evidence/` 子目录。→ 已归档 4 个文件。
- [x] **锚点探针（D4.3 证据固化，非决策门——决策已预定：SUT 驱动解释器保持异解释器）**：
      任务目录内写双配置探针脚本，在 `unshare -Urm bash -c` + 两级 python 祖先的最小复刻链
      下运行：分别以 `/usr/bin/python3`（现状）与 `sys.executable`（假设统一）spawn 子进程，
      子进程 `sys.path` 注入 payload lib 后调用 `session.l2_anchor()` 并打印锚点事实；
      两配置输出存 `evidence/anchor-probe.txt`。**证据效力限定为"差异存在性"**——配置②
      的具体锚点值随调用方环境而变，不作为具体值证据。
      → 见下方"锚点探针记录"。

## Step 1 — isolated-user 注册表（D1.3，其余步骤的前置）

- [ ] `suites.json`：`cp3_tests`/`r1r2_tests` 增加 `"isolated_user": true`。
- [ ] `plan.py`：sh 输出增加 `PLAN_ISOLATED_SUITES`（来源 suites.json，名字存在性校验）。
- [ ] `run_all.sh`：删除 `run_command` 内 `case cp3_tests|r1r2_tests` 特判；串行 `run_suite`
      路径按 `WF_ISOLATED_SUITES` 成员关系追加 `--isolated-user`；export
      `WF_ISOLATED_SUITES="$PLAN_ISOLATED_SUITES"`。
- [ ] `run_one.sh`：同样按 `WF_ISOLATED_SUITES` 给 execution.py 追加 `--isolated-user`
      （修复并行路径缺失该参数的隐患）。
- 验证（**本步只覆盖串行路径**——cp3/r1r2 此刻仍在串行集合，并行路径零触发，其验证
      属 Step 3）：T0 + r67 回归 + 契约测试；`WF_SUITES="cp3_tests" bash .../run_all.sh`
      串行一次，确认 isolated HOME 生效、结束无残留。

## Step 2 — 只读注入助手与注入点转换（D1.1，三探针等价契约）

- [x] `wfdrive.py`：实现 `deny_writes`/`allow_writes`——契约是"目录内新建条目、改写/删除
      已存在文件都必须失败"；**空目录时先创建助手哨兵文件**保证探针有目标（r1r2 的
      blocked-dir 恰是空目录）；chmod 层（目录 0555 + 文件 0444）→ 三探针（创建/改写/unlink）
      → 不成立再 mount 层（bind + remount,ro）→ 仍不成立抛异常；探测文件在 mount 层之前
      删除；令牌记录原模式表、哨兵名与挂载状态，allow 时 umount → 恢复模式 → 删哨兵。
- [x] `r68_tests.py:286/299`、`r1r2_tests.py:92/122`：chmod 对改为助手调用（try/finally）。
- [x] 单元测试 `scripts/tests/wf_runtime/test_wfdrive_readonly.py`：
      - 非 root 路径：deny 后新建/改写/删除**都**失败（含空目录分支），allow 后恢复原状
        （模式与内容逐项一致）；
      - `unshare -Urm` 内（可用时）：deny 走 mount 分支且三探针都失败，allow 后 umount；
      - fail-closed：契约建立不了必须抛异常；
      - 探测文件与哨兵无残留。
- 验证（**本步冒烟只覆盖 chmod 层**——r68/r1r2 此刻仍串行，mount 层端到端属 Step 3，
      本步不构成 D1.1 的收口证据）：T0 + 新测试 + r67 回归；
      `WF_SUITES="r68_tests r1r2_tests" bash .../run_all.sh`（chmod 层行为锚点：r68 用例 11
      的 `WF_PERSISTENCE_FAILED` 与 r1r2 的 R1 用例）。

## Step 3 — 保守串行套件审计与串行标记单一来源（D1.2/D1.4）

- [x] 逐套件审计 11 个无 chmod 的串行套件（cp3/cp4_a8/cp5_b12/r7r15/r35/r67/r69/r70/r71/
      r89/r90），五项核对：夹具来源 / 共享路径（`WF_LEGACY_FIXTURE_ROOT` 是否 worker 私有）/
      用户状态 / pty·sleep 在 ns 内的可用性 / **嵌套运行器**（r67 在 worker 私有 tmpfs +
      私有租约下跑嵌套 run_all，结论须能归因到这一列）。结论写入本文件"审计记录"。
- [x] `suites.json`：审计通过者标记 `"parallel": false` 删除（默认并行）；余留者保留并登记
      `notes` 理由。
- [x] `plan.py`：删除 `PARALLEL_SERIAL` 常量，串行集合改从 suites.json `parallel` 字段推导，
      输出 `PLAN_SUITES_SERIAL` 语义不变。
- 验证（**并行路径与 mount 层的端到端证据在此补齐**）：
      `WF_SUITES="cp3_tests r1r2_tests r68_tests" bash .../run_all.sh`——此刻三套件已入
      并行池，覆盖：run_one.sh 的 `--isolated-user`（Step 1 修复）、deny_writes 的 mount 层
      （Step 2 实现）、worker 内 pty/sleep 可用性；**另跑 `WF_SUITES="r67_tests"
      bash .../run_all.sh`**——r67 首次进并行池（worker 私有 tmpfs + 私有租约下跑嵌套
      run_all），该路径从未被跑过；全部绿再进 Step 4。

## Step 4 — 默认并发（D2）

- [x] `plan.py`：`DEFAULT_JOBS`/`DEFAULT_REPRO_JOBS` → `min(8, os.cpu_count() or 4)`；注释更新。
- [x] 记录：subset 冒烟下最慢单元耗时与 `WF_COMMAND_TIMEOUT`(180s)/`WF_REPRO_TIMEOUT`(120s)
      的实测余量（不沿用旧值）。
- 验证：T0（`test_test_runner_plan.py` 是符号断言）；确认 summary 的 requested/effective
  仍分开记录。

## Step 5 — 映射补全与双向校验（D3）

- [x] 依 full/README.md 覆盖行 + 套件 docstring 为 **18 个**可计划未映射套件补 modules 条目
      （r80–r88、r62、r64、r65、r55、r25r30、cp5_b12、cp5_b345、p5_v1、f1_candidate_smoke），
      逐条依据写入"映射依据"；`d1_*`（manual）不映射。
- [x] `plan.py::_validate_modules` 三条校验：① 可计划套件全覆盖；② 每个 key 在仓库中真实
      存在（**解析基准与 `_normalize_change` 同构**：`REPO/docs/workflows/wf/<key>`，不按
      仓库根裸解析）；③ `map_changes` 命中 key 时 suites 非空。
- 验证：T0；三条负例各验一次（假套件名 / 假 key / 命中但空条目 → PlanError 后恢复）；
  `--list --changed --changed-files` 抽查 3 个此前漏建议的模块路径。

## Step 6 — 解释器与路径的显式契约化（D4，SUT 驱动侧为既定决策）

- [x] `wfdrive.py`：`PYTHON = os.environ.get("WF_TEST_PYTHON") or <异解释器默认>`（**决策
      已定：默认保持异解释器**，D4.3 结构性论证；不改为 `sys.executable`）；新增
      `TOOL_PYTHON = sys.executable`、`REPO`、`LIB`（`WF_TEST_LIB` 优先）。
      `repro/_harness.py`：`WF_PYTHON` 同式同默认（独立字面量，不 import wfdrive）。
- [x] 套件 SUT 驱动点 `/usr/bin/python3`（subprocess 驱动，含 r1r2:187 的列表后置 spawn
      形态）→ `wfdrive.PYTHON`；**单元层驱动点**（`test_fixture_template.py:145`，经
      sys.path 引 wfdrive）与 **manual 套件**（`d1_tests.py:7`）同批改引 `wfdrive.PYTHON`
      ——不新增第三处默认字面量。**数据侧不动**（两类）：`/usr/bin/python3` 断言数据
      （d21 PY_A/PY_B、argv 断言数据、`_executor_set` 复制源、r1r2:176/181 夹具数据）与
      `/softwares/...` 断言数据（executor-project-key-unusable 的 GLOBAL_PY 与注入串、
      d21 docstring/PY_B）。
- [x] 工具侧启动点（r69/r70/r72/r89 启动 `install.py`；p5_v1/r90 启动
      `wf-dev-deploy.py`）的 `/softwares/...` → `wfdrive.TOOL_PYTHON`（与今天 3.14.7 一致，
      无行为变化；不与 SUT 默认共用——`install.py::runtime_support` 用 `sys.executable`
      自检）。shell 入口 `PY=/softwares/...` 保留，加注释声明为项目解释器约定（AGENTS.md §4）。
- [x] 86 处 `/home/xzc/...` 字面量 → `wfdrive.REPO`/`wfdrive.LIB` 拼接，逐文件复核。
- [x] **探针执行**：跑 Step 0 的双配置探针，输出存档（差异存在性证据，供交付纪律登记
      引用；不是决策门）。
- [x] **三条最小单元断言**（交付纪律 §6）：① `WF_TEST_PYTHON` 设置后 `wfdrive.PYTHON`
      取该值；② `wfdrive.PYTHON` 默认 == `_harness.WF_PYTHON` 默认；③
      `TOOL_PYTHON == sys.executable`。
- [x] **白名单清单固化（文件 + 命中数 + 命中行内容摘要，不用行号**——本步同批编辑 86 处
      路径字面量会使行号位移；门槛复核前按当前树重生成快照再比对）：全库
      `/usr/bin/python3` 与 `/softwares/...` 命中逐条清点，数据侧各行 + 驱动侧默认两行
      （wfdrive.PYTHON、_harness.WF_PYTHON）写入本文件白名单节，注明各行理由；
      **守恒校验**：全库命中数 − 白名单登记数 = 0；门槛只扫 `*.py`/`*.sh`（不扫 `*.md`）。
- 验证：T0 + r67 回归；grep 门槛（反向正则在白名单行外零命中 + 守恒校验 + `/home/xzc`
  零命中）；`WF_SUITES="r67_tests r68_tests" bash .../run_all.sh`（直接操作 wflib 的代表，
  验证 `WF_TEST_LIB` 生效）；`WF_SUITES="r69_tests r89_tests p5_v1 r90_tests"
  bash .../run_all.sh`（install.py 与 wf-dev-deploy.py 两类工具启动点的代表）。

## Step 7 — 结果缓存轮转（D5）

- [x] `plan.py`：`list_only` 分支判据改为"**`WF_RESULTS_DIR` 未显式给出**且目录不存在 →
      不建不写"——run_all 全路径（含 `--dry-run`/契约测试）显式给出目录且已 claim，行为
      不变；直接 `--list` 不再泄漏。
- [x] `fixture_scope.py`：`prune-results <root> --scope run|repro --keep N --exclude DIR`
      （**root 经 `WF_RESULTS_CACHE` 可注入，默认标准缓存根；root 不在 `/tmp` 或标准缓存根
      之下时拒绝**；marker 门控、前缀隔离、keep-N、fail-safe 跳过、`PRUNED=/KEPT=` 输出）
      + `--bootstrap`（目录名 `run-<纯数字>` / `repro-<mode>-<纯数字>`；**顶层**内容白名单
      = 已知文件类型 + **已知子目录名** `logs/`/`repro/`/`template/`（不要求 marker；子树
      不逐项审查是有意的，实现注释写明）；**bootstrap 同受 `--scope` 与 `--exclude` 约束**、
      不看 keep-N、**无自动调用点（仅手工执行）**；未知内容跳过并列出）。
- [x] `run_all.sh`/`repro/run.sh`：`prepare-results` 之后接入，root 取
      `${WF_RESULTS_CACHE:-<标准缓存根>}`，scope 各取 `run`/`repro`，exclude 各自当前目录；
      **r67 假环境（r67_tests.py 的假树构造）与 `test_run_all_contract.py` 的 env 同批把
      `WF_RESULTS_CACHE` 指向各自临时根**——测试与假运行器绝不触碰真实用户缓存。
- [x] `test_fixture_scope.py`：最旧先删 / keep-N / 前缀隔离（含 bootstrap）/ 无主不动 /
      exclude 不动 / marker 损坏跳过 / 非法 root 拒绝 / bootstrap 白名单外与空 `logs/`
      目录的区分。
- [x] **手工执行两次 bootstrap**（`--scope run` 与 `--scope repro`——单次只清一个前缀；
      **前置已满足**：Step 0 已归档基线证据），按 **实测 479 清理（run 476 + repro 3）/ 12 跳过
      （全部含 `flows`，其中 1 个另有 `home-*` 残留）** 的实测口径对账，记录清理前后目录数
      与释放空间；对不上账即停下归因，不把跳过项当"没删干净"。
- 验证：T0 + r67 回归 + 契约测试（`test_dry_run_only_prints_plan` 必须仍绿）；直接
  执行记录（2026-11-14）：泄漏判据验证通过（直接 --list 两次目录数不变；显式目录仍镜像
  写 plan.json）；prune 输出改 stderr（dry-run 契约要求 stdout 纯净）；set -u 陷阱修复
  （RESULTS_CACHE 先本地展开再传环境）；bootstrap 两次调用：run 侧 PRUNED=476 KEPT=20
  （12 个含 flows 跳过）、repro 侧 PRUNED=3；缓存 512 项 → 33 项（12 跳过 + 20 有主 +
  repro-state.json，对账吻合），312MB → 189MB；r67 15/15、契约 9/9、fixture_scope 14/14。

  `plan.py --list` 两次后确认无新 `run-<pid>` 目录；连续两次 subset 后确认
  `~/.cache/wf-test-run` 目录数收敛在 keep + 活跃余量内。

## Step 8 — 断言解释收敛（D6）

- [x] `run_all.sh`：`run_flow`/`run_f0`/`run_extra` 的 **3 处**（行 479/497/508）grep 计数
      删除，改读 `$log.json` 的 `assertion_result.passed`（`$PY -c` 解析，失败计基础设施失败）。
- [x] `execution.py`：模块 docstring 增加"套件输出契约"一节（三汇总行格式 + PASS/FAIL 行文法
      + steps 终态），声明 verdict 为唯一解释点。
- 验证：T0 + r67 回归 + `WF_SLOW_TESTS=1` 契约测试；representative 确认流程行 PASS 计数
  与改前一致。

## Step 9 — 小项清理（D7）

- [x] suites.json 删除全部 `expected_seconds` 键。
- [x] usage：三脚本的 `usage()` 改 heredoc 唯一来源（wf_fixture.sh 两处调用点、repro/run.sh
      两处、run_all.sh 一处），头注释压缩为一行指向 `--help`，删除全部 `sed -n '2,Np'`。
- [x] `run_one.sh`：`suite_millis` 读 `$suite.test.log.json` 的 `seconds`（缺失计 0，由
      results_gate 兜底）；`init_millis` 保留 now_ms。
- 验证：T0 + r67 回归；三脚本 `-h` 输出完整、与实现一致（逐项核对选项仍在）。

## Step 10 — 文档同步

- [x] `full/README.md`：并发默认、串行集合（或空集结论）、解释器口径（驱动侧统一 +
      数据侧白名单）、prune/bootstrap 策略、性能数字（Step 11 实测后填）。
- [x] `.trellis/spec/docs/wf-delivery-discipline.md` §7：默认并行数字、对拍记录追加本次；
      §12：prune-results/bootstrap 签名、套件耗时来源、**session 锚点与驱动解释器选择的
      耦合契约**（D4.3 的结论）。
- 验证：`check-doc-refs.py`、`validate-skills.sh`、`validate-wf-design.py`。

## Step 11 — 收口验证（AC1/AC6/AC8）

- [x] representative 预收口：`bash .../run_all.sh --representative --repro green`。
- [x] full 并行：`bash .../run_all.sh --full --repro green`（**分段记录**：套件段/repro 段
      墙钟，对照 AC1 ≤120s 且提速来源可归因）。
- [x] full 串行：`bash .../run_all.sh --full --repro green --serial`。
- [x] 对拍：两份 RESULTS_DIR 的 lines（套件名/rc/status）、repro/*.json（逐用例
      mode/green/red/verified）、流程行 rc/PASS 逐项相等（运行期 id 除外）；差异即停下归因。
- [x] grep 门槛复核（AC4 全项）；`~/.cache/wf-test-run` 目录数终值（AC5）。
- [x] 最终 diff 复核（含 untracked/staged），确认无计划外改动、无遗留 TODO。
  收口验证记录（2026-11-14）：
  - full 并行（run-3014253）：**total=94s**（基线 run-1964465 的 204s，-54%）；套件段
    累计 289s@8 worker、repro 段 26.33s、149 单元 0 失败；分段可归因（AC1 ≤120s 达成）。
  - full 串行（run-3077220）：274s，149 单元 0 失败。
  - 对拍：59 套件行（rc/status）、85 repro（mode/green/red/verified）、6 流程行
    （rc/PASS：f0=9、p5_spec=19、p5_v1=12、p5_v2v3=12、p5_v5=12、r72=7）逐项相等（AC1）。
  - grep 门槛：`/home/xzc` 零命中；驱动语境反向正则白名单外零命中；守恒校验经
    **内容级集合比对**复核（0 新增 0 消失；快照已按当前树重生成，行号漂移不影响身份）。
  - 文档校验：check-doc-refs / validate-wf-design / validate-skills 全过。
  - 最终 diff：87 文件（840+/359-），全部位于 scripts/tests/wf_runtime/**、交付纪律、
    任务目录；抽查 execution.py（docstring+isolated_user 字段）与 f1_init（仅 import
    顺序）无计划外改动；产品树 digest 自检经 run_all 内置 GATE-OK 通过。

## 回滚点

- 每个 Step 一个可独立 revert 的提交边界；Step 3 之前任一步失败可单独回退。
- Step 6 的既定形态即"保底"：wfdrive/_harness 单点默认保留异解释器（两处字面量、
  `WF_TEST_PYTHON` 可覆盖、三入口一致、AC4 白名单登记两行）——若实施中发现默认值选择
  有误（如该机器无 `/usr/bin/python3`），改默认值并同步白名单，不引入第三处字面量。
- Step 11 对拍失败：先归因（实现缺陷→修实现；审计结论错误→该套件回 `parallel: false` 并
  登记），不改判据迁就绿灯；最坏情况整体 `git revert` 本任务提交序列，无状态迁移需清理。

## 审计记录（Step 3 已执行，2026-11-14）

五项核对（夹具来源 / 共享路径 / 用户状态 / pty·sleep / 嵌套运行器），11 个无 chmod 的
保守串行套件 + 2 个 chmod 注入套件全部结论：**并行安全**。

| 套件 | 夹具来源 | 共享路径 | 用户状态 | pty·sleep | 嵌套运行器 | 结论 |
|---|---|---|---|---|---|---|
| cp3_tests | 模板克隆 | 无（F=WF_FIX） | isolated-user（注册表下发，并行路径已验证 isolated_user=True） | 无 | 无 | 并行安全 |
| cp4_a8 | 自带（wf_fixture.sh，LEGACY 根=worker 私有） | /tmp/cp4_a8_* 自名 scratch | 无 | 无 | 无 | 并行安全 |
| cp5_b12 | 自带（wf_fixture.sh+f2_setup+f1_init） | /tmp/cp5_* 自名 scratch | 无 | 无 | 无 | 并行安全 |
| r7r15_tests | 模板克隆 | /tmp/outside-target 等（worker 私有 tmpfs） | 无 | 无 | 无 | 并行安全 |
| r35_tests | 自带（f5/f3，LEGACY 根私有） | release-repo 只读 bind 回退 | 无 | 无 | 无 | 并行安全 |
| r67_tests | 假树 mkdtemp（TMPDIR=worker 私有） | /tmp/r67_* 自名 | 无 | 无 | **嵌套 run_all**：worker 内 namespace.py 弹出宿主 lease env，嵌套入口在私有 /tmp 取自己的锁——私有租约闭合 | 并行安全（实跑 15/15） |
| r69_tests | LEGACY 根私有（r69-uninstall） | install.py 启动（只读发行） | 无 | 无 | 无 | 并行安全 |
| r70_tests | LEGACY 根私有（r70-*） | 只读发行；"run_all" 仅出现在帮助文本 | 无 | 无 | 无 | 并行安全 |
| r71_tests | 模板克隆 | /tmp/r71_* 自名 | 无 | 无 | 无 | 并行安全 |
| r89_tests | 模板克隆 | 只读发行 bind（/tmp/wf-fixtures/release-repo） | 无 | 无 | 无 | 并行安全 |
| r90_tests | 模板克隆 | install/dev-deploy 启动 | 无 | 无 | 无 | 并行安全 |
| r1r2_tests | 模板克隆 | /tmp/r12_* 自名 | isolated-user（注册表） | **pty + sleep(0.6)**：worker 内实跑通过 | 无 | 并行安全（chmod 注入已转 deny_writes） |
| r68_tests | 模板克隆 | /tmp/r68_* 自名 | 无 | 无 | 无 | 并行安全（chmod 注入已转 deny_writes） |

实跑证据（全部并行模式，串行段 0）：
- `WF_SUITES="cp3_tests r1r2_tests r68_tests"` → 19/19、14/14、11/11（cp3/r1r2 的
  isolated_user=True 在并行路径生效；r1r2 的 pty 与 r68/r1r2 的 mount 层在 worker 内通过）；
- `WF_SUITES="r67_tests"` → 15/15（嵌套 run_all 在 worker 私有租约下首次跑通）；
- `WF_SUITES="cp4_a8 cp5_b12 r7r15_tests r35_tests r69_tests r70_tests r71_tests r89_tests r90_tests"`
  → 9+9+10+9+5+16+37+12+13 全过。
- suites.json 无任何 `parallel: false` 条目；plan.py 的 `PARALLEL_SERIAL` 常量已删除，
  `load_suites` 校验 parallel:false 必须携带 notes 理由。

## 锚点探针记录（Step 0 已执行）

- 输出：`evidence/anchor-probe.txt`（2026-11-14，unshare -Urm bash + 两级 python 祖先链）。
- 配置①（异解释器，现状）：锚点 = harness 内 level1 python（`exe=python3.14`）——稳定、
  可复现，等价于今天"锚点落在套件进程"的拓扑。
- 配置②（同解释器，假设统一）：锚点 = **zcode-cli 进程**（探针调用方环境，即运行本次
  任务的 agent 进程）——锚点逃逸出 harness，随调用方环境漂移、不可跨终端复现；在无
  host 标识/信封的入口上若落空则 `WF_IDENTITY_UNRESOLVED`。
- 结论：结构性论证获实证；既定决策 A（保持异解释器默认）成立。具体锚点值仅作差异
  存在性证据，不写入任何断言期望。

## 映射依据（Step 5 已执行，2026-11-14）

依据 = 套件实际调用的 wf 命令面 + 直接 import 的 wflib 模块（不凭名字猜）；18 个套件
并入**既有键**的 suites 列表（不新建键——records/session/gates 等无键文件在 --changed
下显式列为"未映射改动（需人工判断）"，fail-visible 不静默）：

| 套件 | 并入键 | 依据 |
|---|---|---|
| r25r30_tests | spec.py, tasks.py, writer.py | spec-update/task-approve/curate/pause 命令 + import records,spec |
| r55_tests | tasks.py, writer.py | task-approve 语义（批准必须被消费）+ writer |
| r62_tests | tasks.py, review.py | task-approve/knowledge + 审查 outcome/调查成果（import gates） |
| r64_tests | cli.py, spec.py | bind/spec/task-new + import cli,gates |
| r65_tests | review.py, tasks.py, sampling.py | review-passed 恢复 + sampling 命令（import gates） |
| r80_tests | check.py | Check 结构/处置事实/脱敏/计数（import check） |
| r81_tests | check.py, install.py | install 边界/manual 证据/归档恢复（import check） |
| r82_tests | check.py, maintenance.py, tasks.py | 巡检误报/续做三态（import check,records） |
| r83_tests | review.py, cli.py | transport 收窄/自证证据拒绝（import session, wflib.review） |
| r84_tests | identity_store.py, cli.py, tasks.py | 恢复期身份核验/bind 意图先行（import records） |
| r85_tests | check.py, cli.py, install.py | 创建/绑定意图协议/安装预览（import check） |
| r86_tests | check.py, scope.py, tasks.py | d 桶/活冲突/异常归档（import check） |
| r87_tests | tasks.py, writer.py | writer 单一父动作/Finish→Check（import tasks, wflib.gates） |
| r88_tests | tasks.py, runs.py | 早期中断可恢复/实例固定（import tasks） |
| cp5_b12 | cli.py, tasks.py | enable/任务闭环（F2 两分支） |
| cp5_b345 | spec.py, tasks.py, sampling.py | B5 spec 拆分 + sampling/归档命令 |
| p5_v1 | cli.py, identity_store.py | bind/enable/宿主会话身份能力 |
| f1_candidate_smoke | install.py, review.py, tasks.py | 候选安装→复杂审查→归档闭环 |

覆盖核对：61 个可计划套件全部被 ≥1 模块覆盖；三条校验负例（假套件/假键/空条目）
均 PlanError；--changed 抽查：check.py 建议已含 r80/r81/r82/r85/r86，
gates/records/session 显式列"未映射改动"。

## `/usr/bin/python3` 与 `/softwares/...` 白名单（Step 6 已固化，2026-11-14）

完整清单（文件:行号 + 行内容摘要哈希）存 `evidence/whitelist-interpreters.txt`
（99 命中 / 63 文件，复核时按同法重生成比对）。分类与守恒：

| 分类 | 数量 | 说明 |
|---|---|---|
| 驱动侧默认（SUT） | 2 | `wfdrive.py:10`、`repro/_harness.py:282`——D4.3 既定决策：默认保持异解释器（锚点拓扑耦合），`WF_TEST_PYTHON` 可覆盖；`test_wfdrive_constants.py` 五断言守卫 |
| argv/verification 断言数据 | ~66 | 各套件 `"kind": "argv", "argv": ["/usr/bin/python3", "-c", ...]`（任务记录里的验证命令）+ f1_init 模板 + p5_f0/p5_spec 的 verification-commands |
| 夹具/断言数据（解释器作为值） | 13 | r1r2:178/183（config/baseline）、r81:156–183（project_key_approved）、r79:109（redact_argv）、test_inspection_hint.py:38、test_project_key_semantic.py:46、test_wfdrive_constants.py:34（本任务断言默认值） |
| 数据侧解释器引用（repro） | 9 | d21-multi-clone:5/6/20/21（PY_A/PY_B/docstring）、d21-purge-reconfirm:17（PY=确认记录值）、executor-project-key-unusable:19/24/25（GLOBAL_PY/注入串）、_executor_set.py:50（复制系统解释器） |
| shell 入口 `PY=` | 5 | run_all.sh/wf_fixture.sh/repro/run.sh/f2_setup.sh/d1_rebuild.sh——项目声明解释器（已加 AGENTS.md §4 注释），属约定不是硬编码事故 |

守恒校验：全库命中 99 − 白名单登记 99 = **0** ✓。工具侧启动点
（r69/r70/r72/r89 的 install.py、p5_v1/r90 的 wf-dev-deploy.py）已归一
`wfdrive.TOOL_PYTHON`（=sys.executable，与今天一致）；SUT 驱动面四层
（full/repro/单元层/manual）一律引 `wfdrive.PYTHON`。
实施期间修复的两个自伤缺陷（均已过套件回归）：
`wfdrive.REPO` 上溯差一层（r67/r90/p5_v1 命中，已修 + REPO 断言守卫）；
r67 假树缺 modules 键桩路径（键存在性新校验所致，假环境依清单生成桩路径跟上契约面）。


## 独立检查（trellis-check）处置记录（2026-11-14）

检查结论：AC1–AC4、AC6–AC8 PASS；AC5 一处隔离缺口（Medium）+ 两处路径残留（Low）。
全部已修复并复验：

| 发现 | 严重度 | 处置 | 复验 |
|---|---|---|---|
| test_interrupting_root_runner 直启 Popen 绕过 run() 的 WF_RESULTS_CACHE 注入，对真实缓存执行了 prune（实测删 run-2840398） | Medium | 该测试 env 补 WF_RESULTS_CACHE 临时根（design D5.2 同一注入） | 契约测试 9/9 绿，前后真实缓存目录数 34→34 不变 |
| r76_tests.py:116 hold_lock 子进程 code 串内残留单引号绝对路径（落在带引号 grep 门槛之外） | Low | 改 `f"sys.path.insert(0, {wfdrive.LIB!r});"` 派生 | r76 11/11；严格 grep `/home/xzc`（不带引号前缀）全库 0 命中 |
| d1_rebuild.sh:4 ROOT= 硬编码（无调用点，手工维护入口，本任务只加过 PY 注释） | Low | 改脚本位置派生 `ROOT=$(cd ... && pwd)` | bash -n 过 |
| run_all 的 prune `|| true` 不因 root 校验失败而失败 | Info | 维持（轮转属维护操作非正确性门，单目录失败已打 PRUNE-SKIPPED） | — |
| "run 侧 PRUNED=476" 与 PRD 口径 473 的表述差 | Info | 总数 479 一致（476 run 含 3 个混入 run 前缀判断的 repro 期产物由 --scope run 一并清理）；不影响对账 | — |

AC4 的 grep 门槛在检查后升级为**不带引号前缀**的严格形态（`/home/xzc` 全形态零命中），
比 PRD 定义的字面门槛更严——按"不放宽"原则收口。
