# wf 测试运行器提速与质量修正（第二轮）

## Goal

在归档任务 `11-13-wf-test-runner-reliability-performance`（full 并行 174–179s）之后的第二轮运行器修正：
解除 13 个保守串行套件的串行约束、提高默认并发、补全 `--changed` 模块映射、**单点化并显式
契约化** SUT 驱动解释器（默认保持异解释器——`wflib/session.py` 的进程锚点规则使"统一解释器"
成为 SUT 可见的行为变更，结构性论证见 design D4.3，本任务不消灭该耦合而是把它变成显式契约）、
消除工具侧解释器与绝对路径硬编码、结果缓存轮转（含存量收敛）、断言解释收敛与死代码清理。

目标：full green 并行墙钟从 ~174s 降到 **≤120s**（套件段与 repro 段分开计量），
且并行/串行等价性对拍保持逐项一致（交付纪律 §7 的既有要求）。

## Background / Baseline（证据）

- 基线口径：同机同模式可比基线是 `~/.cache/wf-test-run/run-1964465/summary.json`（并行 204s、
  串行 run-2034392 301s、149 单元）；上一任务收口实测 174.99s（`/tmp/wf-runner-audit/delivery-full/`，
  **易失路径**，仅作参考不作为核对锚）。13 个强制串行套件合计 ~109s，占并行墙钟一半以上。
- 串行原因考古：`11-03-wf-round1-min-loop` 的 N-R112 记录了两个原始原因——"root 使 chmod 失效、
  跨套件 /tmp 状态"。后者已被 worker 私有 /tmp + 套件自带夹具（2026-11-06 W1）消除；
  前者实际只有 `r1r2_tests`/`r68_tests` 两处 `chmod 0o555` 注入。其余 11 个套件是保守遗留。
- 环境耦合（**分三类，不可混改**）：
  - **SUT 驱动侧**（套件/harness 启动被测 `wf.py` 的解释器）：`wfdrive.py`/
    `repro/_harness.py` 等约 26 处 `subprocess` 驱动写死 `/usr/bin/python3`（3.13.5），与运行器的
    `/softwares/python/bin/python3`（3.14.7）分裂。**结构性事实**：`wflib/session.py::l2_anchor`
    跳过与自身同解释器的祖先——SUT 与驱动异解释器时锚点落在套件进程，同解释器时套件层被跳过、
    锚点上移甚至落空（自动会话入口将抛 `WF_IDENTITY_UNRESOLVED`）；且 full 层**没有任何断言
    消费真实进程锚点**（`anchor_conflict`/`host_identity_absent` 仅在单元层以合成 facts 消费）。
    因此"统一解释器"是**无断言覆盖的 SUT 可见行为变更**，本任务的正确形态是单点化 + 显式契约，
    不是消灭。
  - **工具侧**（套件启动 `install.py`/`scripts/wf-dev-deploy.py` 的解释器）：21 处
    `/softwares/...` 写死在 shell 入口与套件启动点（r69/r70/r72/r89 启动 `install.py`，
    p5_v1/r90 启动 `wf-dev-deploy.py`）；`install.py::runtime_support`（:479）用
    `sys.executable` 起子进程自检——安装器解释器变化会改变自检所跑的解释器。
  - **数据侧**（断言本体）：约 66 处 `"argv": ["/usr/bin/python3", ...]` 是用例断言数据；
    `repro/d21-executor-set-multi-clone.py` 的 `PY_A`/`PY_B` 双解释器并存就是断言主体；
    `repro/_executor_set.py` 复制系统解释器伪造 venv 探测对象。**这些不得机械替换**。
  - **路径字面量**：56 个文件共 86 处硬编码本机绝对仓库路径 `/home/xzc/...`。
- 结果缓存：`~/.cache/wf-test-run` 现有 **489 个**目录（`run-*` 485 + `repro-*` 4，~312MB），
  **其中仅 3 个带 `.wf-results-owner.json` 所有权 marker**——历史目录多数产生于 marker 机制
  建立之前；且 `plan.py` 的 `list_only` 分支在目录不存在时 `makedirs` 并写 `plan.json`
  （直接 `--list` 每次泄漏一个无主 `run-<pid>` 目录）。只约束增量的轮转对存量无效；
  存量目录里包含本任务引用的基线证据（run-1964465/run-2034392，均无 marker）。
- `--changed` 建议：63 个套件条目中 **18 个可计划套件无模块映射**（另 2 个是 manual，不参与计划）；
  `plan.py::_validate_modules` 只校验"模块→套件存在"单方向，文件命中已映射键但漏列实际覆盖
  套件时静默漏建议。
- 断言解释：`execution.py::verdict` 是唯一实现，但 `run_all.sh` 有 **3 处**本地 `grep -Ec` PASS
  计数副本（run_flow/run_f0/run_extra，行 479/497/508）。
- 死代码/脆弱点：`suites.json` 的 `expected_seconds` 字段零使用；usage 文本靠 `sed -n '2,14/18/24/26p'`
  行号提取（**5 个调用点 / 4 个区间**，run_all.sh、wf_fixture.sh、repro/run.sh）；`now_ms` 计时在
  run_all.sh 与 run_one.sh 双份实现。

## Requirements

- **R1（O1）解除串行约束**：提供共享的只读注入助手（**三探针等价语义**：既阻断目录内新建/删除
  条目、也阻断改写已存在文件；chmod 层 + ro bind mount 层，两环境行为一致，fail-closed），
  转换 `r1r2_tests`/`r68_tests` 的注入点；逐套件审计其余 11 个保守串行套件并给出并行化结论；
  串行标记改为 suites.json `parallel: false` 字段（单一来源，删除 plan.py 的 `PARALLEL_SERIAL`
  常量）；`cp3/r1r2` 的 `--isolated-user` 特判同样进注册表。
- **R2（O2）默认并发**：`DEFAULT_JOBS`/`DEFAULT_REPRO_JOBS` 从 4 提到 `min(8, cpu_count)`，
  `--serial`/`WF_JOBS=1` 退路保留；summary 继续分开记录 requested/effective；同批复核
  `WF_COMMAND_TIMEOUT`/`WF_REPRO_TIMEOUT` 在 8 并发下的余量（记录最慢单元耗时）。
- **R3（P1）映射补全与双向校验**：为 18 个可计划未映射套件补齐 modules 映射（依据 full/README.md
  覆盖表与套件 docstring，逐条给出依据；manual 套件不映射）；`_validate_modules` 增加三条校验：
  ① 每个可计划套件（kind ∈ suite/extra/candidate）被 ≥1 模块覆盖；② 每个 modules key 在仓库中
  真实存在（防"永不命中的假 key"绕过门槛）；③ 命中 modules key 时该条目的 suites 不得为空。
- **R4（P2）解释器与路径的显式契约化**（行为敏感，见 design D4）：
  - **SUT 驱动解释器**：单点化为 `wfdrive.PYTHON = os.environ.get("WF_TEST_PYTHON")
    or <异解释器默认>`（`repro/_harness.py::WF_PYTHON` 同式同默认，两处字面量均登记白名单）。
    **默认保持异解释器是既定决策**（D4.3 结构性论证：统一即无断言覆盖的锚点拓扑变更），
    `WF_TEST_PYTHON` 提供可钉住的覆盖口；该耦合契约写入交付纪律；
    **SUT 驱动面覆盖全部三层**：full 套件、repro harness、单元层驱动点
    （`test_fixture_template.py:145`）与 manual 套件（`d1_tests.py:7`）一律改引
    `wfdrive.PYTHON`——不新增第三处默认字面量；
  - **工具侧解释器**：套件启动 `install.py`/`wf-dev-deploy.py` 的写死 `/softwares/...`
    （r69/r70/r72/r89/p5_v1/r90）归一到 `wfdrive.TOOL_PYTHON = sys.executable`——与今天
    实际所跑（3.14.7）一致，无行为变化，且与 SUT 驱动解释器**不共用默认**（安装器自检
    走 `sys.executable`，不受锚点耦合影响）；shell 入口的 `PY=/softwares/...` 保留并注释为
    项目声明解释器（AGENTS.md §4）；
  - **数据侧字面量不动**（两类都登记白名单）：`/usr/bin/python3` 的断言数据（d21 的
    PY_A/PY_B、argv 断言数据、`_executor_set` 复制源、r1r2:176/181 夹具数据）与
    `/softwares/...` 的断言数据（`executor-project-key-unusable.py` 的 GLOBAL_PY 与注入
    补丁源码串、d21 docstring/PY_B、`full/README.md:9` 文档字样）；
  - **新增三条最小单元断言**（交付纪律 §6"有实现、无断言 = 未验证"）：`WF_TEST_PYTHON`
    设置后 `wfdrive.PYTHON` 生效；`wfdrive.PYTHON` 默认 == `_harness.WF_PYTHON` 默认
    （防两处字面量漂移）；`TOOL_PYTHON == sys.executable`；
  - 86 处硬编码绝对仓库路径改为 `wfdrive.REPO`/`wfdrive.LIB` 派生路径；直接操作 wflib
    的套件优先取 `WF_TEST_LIB`（发行副本）。
- **R5（P3）结果缓存轮转（含存量与泄漏源）**：
  - 修泄漏：`plan.py` `list_only` 分支的判据是"**`WF_RESULTS_DIR` 未显式给出**且目录不存在 →
    不建不写"（run_all 全路径含 `--dry-run`/契约测试都显式给出目录且已 claim，plan.json 行为
    不变；直接 `--list` 不再泄漏。比"目录是否已存在"更可解释——后者会把"恰好存在的默认
    目录"误当显式目录）；
  - `fixture_scope.py` 新增 `prune-results`：只删除带有效所有权 marker 的目录，保留最近 N=20，
    跳过当前 run 与无主目录（fail-safe）；**root 可注入**（`WF_RESULTS_CACHE`，默认标准缓存根
    `~/.cache/wf-test-run`）——r67 假环境与契约测试指向临时根，**测试与假运行器绝不触碰
    真实用户缓存**；run_all 只回收 `run-*` 前缀、独立 repro 入口只回收 `repro-*` 前缀
    （**bootstrap 同样受 scope 约束，且 bootstrap 无自动调用点、仅手工执行**）；
  - **存量收敛**：一次性 bootstrap——仅删除目录名匹配 `run-<纯数字>` /
    `repro-<mode>-<纯数字>`、**顶层**内容全部属于运行器已知产物（文件白名单 + **已知子目录名**
    `logs/`（空目录、无 marker）、`repro/`（repro 结果）、`template/`（夹具模板副本）；
    子树内容不再逐项审查，这是**有意的**并在实现注释中写明）且无所有权冲突的无主历史目录；
    bootstrap **尊重 `--exclude`**（当前 run、r67 假运行器目录等活跃目录不删）、不看 keep-N；
    **执行前先把本任务引用的基线证据（run-1964465/run-2034392 的 summary.json 与 lines）
    归档进任务目录**；清理量逐条记录（实测预判：488 个名字匹配目录中 **476 个合格**
    （run 侧 473 + repro 侧 3）、**12 个跳过**——全部因顶层含 `flows` 文件，其中 1 个
    另有 `home-*` 残留目录；**scope 拆分需两次调用**（`--scope run` 与 `--scope repro`），
    单次调用会留存另一前缀的合格目录）；
  - 安全前提写入设计：prune 的 liveness 保障隐式依赖"全局 flock 只允许一个根运行器"。
- **R6（P4）断言解释收敛**：run_all.sh 的 flow/f0/extra 的 **3 处**本地 grep 计数全部改为消费
  execution.py 的结果 JSON；套件输出契约（三种汇总行格式 + PASS/FAIL 行文法）集中文档化在
  execution.py 一处。
- **R7（P5）小项清理**：移除 `expected_seconds` 死字段（schema 与全部数据行）；usage 改为
  heredoc 单一来源并删除头注释中的重复正文（5 个调用点 / 4 个区间一次清完）；run_one.sh 的
  套件耗时改读 execution.py 结果 JSON（init 计时保留本地 now_ms）；full/README.md 与交付纪律
  §7/§12 同步更新。~~`WF_RESULTS_DIR` export 位置~~：**撤销**——`exec` 不改变 PID，
  原判断不成立（实测验证），该目录名含租约进程 PID 是稳定行为，不改。

## Constraints

- 不改产品面：`docs/workflows/wf/payload/**` 与 `docs/workflows/wf-release/**` 不动；
  O4（模板跨 run 缓存）与 O5（lazy import）经用户决策明确不做。
- 遵守 `wf-delivery-discipline.md` §7/§12：运行中不编辑 runner 文件；改 runner 后必须做
  并行/串行全量对拍；验证顺序 T0 → 契约 → 冒烟 → representative → full。
- 同一判定只有一处实现：不新增第二份计时/断言解释/套件特判；串行标记与 isolated-user 标记
  都进 suites.json 注册表，bash 分支不藏特判。
- 不删除任何套件、用例或断言；执行单元数保持 149；KNOWN_LEGACY 机制不动。
- 数据侧断言字面量不受 AC4 grep 门槛约束（白名单制，门槛只管驱动侧）。
- 夹具/结果安全边界（fixture_scope 所有权 marker、symlink 拒绝、保护路径）不放宽；
  prune 对无主目录的默认行为仍是"不删"（bootstrap 例外见 R5，且内容白名单 + 无冲突双重条件）。
- **r67_tests 是运行器契约的消费者**（它复制 run_all.sh/plan.py/suites.json 等构造假环境），
  运行器内部契约变化（新 export、prune 调用、JSON 判定、usage）必须同步核对 r67 并跑其回归。

## Acceptance Criteria

- [ ] AC1：`--full --repro green` 并行墙钟 ≤120s（**套件段与 repro 段分开记录**，提速来源可
      归因），且与 `--full --repro green --serial` 对拍逐项相等（套件名/rc/status、repro 逐用例
      mode/green/red/verified、流程 rc/PASS；运行期 id 除外）。
- [ ] AC2：串行集合以 suites.json `parallel: false` 为唯一来源（plan.py 无平行常量）；为空或
      余留条目在 `notes` 登记具体不可并行理由；原 13 个串行套件在并行模式下结论与串行一致。
- [ ] AC3：modules 映射覆盖全部可计划套件；三条校验各有负例验证（假套件名、假 key、命中但
      suites 为空，均 PlanError）。
- [ ] AC4：**驱动侧**门槛机械可核验且**守恒**——反向正则（只扫代码文件 `*.py`/`*.sh`，
      不扫 `*.md`）在白名单之外零命中，且**守恒校验**：全库命中数 − 白名单登记数 = 0。
      白名单按**文件 + 命中数 + 命中行内容摘要**登记（不用行号——Step 6 同批编辑会使
      行号位移；复核前按当前树重生成快照再比对），覆盖两类数据侧：`/usr/bin/python3`
      断言数据（d21 PY_A/PY_B、argv 数据、`_executor_set` 复制源、r1r2:176/181 夹具数据）
      与 `/softwares/...` 断言数据（executor-project-key-unusable 的 GLOBAL_PY 与注入串、
      d21 docstring/PY_B）；驱动侧默认两行（`wfdrive.PYTHON`、`_harness.WF_PYTHON`）注明
      锚点耦合理由；SUT 驱动面（full/repro/单元层/manual）归一后除两处默认外零残留；
      工具侧 `/softwares/...` 启动点归一后零残留（shell 入口与数据侧白名单除外）；
      `grep -rn "/home/xzc/projects"` 在 `scripts/tests/wf_runtime/` 下零命中；
      锚点探针证据（差异存在性）与三条新单元断言在案。
- [ ] AC5：泄漏修复后直接 `--list` 不再产生无主目录，而 `--dry-run`/契约测试的 plan.json 行为
      不变（`test_dry_run_only_prints_plan` 仍绿）；prune/bootstrap 只删符合各自前缀与白名单的
      目录且保留最近 20，root 经 `WF_RESULTS_CACHE` 可注入（**r67 假环境与契约测试指向
      临时根，不触碰真实用户缓存**——负例验证），run_all/repro 前缀互不越界（**bootstrap
      同受 scope 与 `--exclude` 约束、无自动调用点**）；bootstrap 执行前基线证据已归档进
      任务目录，**两次调用**（`--scope run` 与 `--scope repro`）后 `~/.cache/wf-test-run`
      目录数收敛到 ≈ keep + 12（476 = run 473 + repro 3 合格清理；12 个跳过项全部含
      `flows`、其中 1 个另有 `home-*` 残留；记录前后数量对账）；无主目录（白名单外）、
      `repro-state.json`、当前 run 目录不受影响（负例验证）。
- [ ] AC6：run_all.sh 中无本地 PASS 计数 grep（3 处全消）；flow/f0/extra 的判定与展示均来自
      execution.py 结果 JSON；full green 149 单元零失败；r67 回归通过。
- [ ] AC7：`expected_seconds` 在 suites.json 中消失；三个脚本的 `--help` 输出与头注释一致且
      不依赖行号（5 个调用点全部走同一 usage 来源）；run_one.sh 不再自算套件耗时。
- [ ] AC8：单元层全绿（含 `WF_SLOW_TESTS=1` 契约测试）；`validate-wf-design.py`、
      `check-doc-refs.py`、`validate-skills.sh` 通过；交付纪律 §7/§12 与 full/README.md 的默认
      并发、串行清单、解释器口径、轮转策略描述同步；最终 diff 复核无计划外改动。

## Notes

- 复杂任务：`design.md`（技术设计）与 `implement.md`（执行计划）随本 PRD 一并审阅。
- 本任务不建父/子树：七个工作项共享同一验证闭环（等价性对拍 + full green），拆分会重复
  付出全量验证成本。
- 本 PRD 经三轮独立审查修正（修正记录见 design.md 末尾"审查修正记录"）。第三轮的关键
  重新定性：SUT 驱动解释器**不做统一**（结构性论证见 D4.3），任务交付改为"单点默认 +
  可覆盖 + 契约登记"；Goal 已按此改写。
- **用户已批准 Goal 级决策 A**（2026-11-14）：SUT 驱动解释器保持异解释器默认，本任务
  对该子项交付"单点化 + 显式契约化"，不消灭耦合；方案 B（统一解释器 + 锚点断言开发）
  不在本任务范围。
