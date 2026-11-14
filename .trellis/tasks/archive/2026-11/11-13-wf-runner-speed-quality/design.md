# wf 测试运行器提速与质量修正 — 技术设计

## Boundary

修改范围：`scripts/tests/wf_runtime/full/**`（运行器、wfdrive、套件的注入点与路径字面量）、
`scripts/tests/wf_runtime/full/repro/_harness.py`、`scripts/tests/wf_runtime/` 下相关单元测试、
`scripts/tests/wf_runtime/full/suites.json`、`full/README.md`、`.trellis/spec/docs/wf-delivery-discipline.md`。

不修改：`docs/workflows/wf/payload/**`（产品）、`docs/workflows/wf-release/**`（发行树）、
repro 用例脚本的业务断言（含其断言数据字面量）、KNOWN_LEGACY 机制、fixture_scope 既有的
安全判定（只新增操作，不放宽）。

保留的单一来源：plan.py（选择）、execution.py（执行与断言解释）、results_gate.py（结果完整性）、
repro_select.py（repro 选择/状态）、fixture_scope.py（夹具与结果目录所有权）。

**特殊消费者**：`r67_tests.py` 复制 `run_all.sh`/`plan.py`/`suites.json`/`results_gate.py`/
`execution.py`/`fixture_scope.py` 构造假环境并自带 `run_one.sh` 桩（内含独立 `grep -c [FAIL]`
判定）。任何运行器内部契约变化（新 export、prune 调用、结果 JSON 判定、usage）都会被它复制
走——本任务所有 runner 契约步骤之后必须跑 `WF_SUITES="r67_tests"` 回归，其失败要归因到
契约不兼容而不是当 flake 吞掉。

## D1 解除串行约束（R1）

### D1.1 只读注入助手（唯一实现：wfdrive.py，三探针等价契约）

现状：`r1r2_tests.py:92/122`、`r68_tests.py:286/299` 用 `os.chmod(path, 0o555)` 模拟目录不可写。
user namespace 内 worker 是 root，chmod 不生效——这是 13 套件串行的原始硬原因之一。

**机制等价问题（必须解决，不能靠巧合）**：chmod 0555 只阻断"目录内新建/删除条目"，已存在
文件仍可写；ro bind mount 连改写已存在文件也 EROFS。今天两者结果碰巧一致，是因为产品持久化
统一走 `records.atomic_write`（`records.py:159`，同目录 mkstemp + os.replace）——两种机制都
断在 mkstemp 的"目录内创建"上。这是产品的实现巧合，不是助手的契约。契约必须按行为定义：

> deny 后，对 path 内**新建条目**、**改写已存在文件**与**删除已存在条目**都必须失败。

实现（wfdrive.py）：

```python
def deny_writes(path):
    """让 path 暂时满足 deny 契约，返回恢复令牌；契约建立不了即抛异常（fail-closed）。"""
    # 0) 若 path 内没有已存在文件（r1r2 的 blocked-dir 恰是空目录）：先在 path 内创建
    #    助手自己的哨兵文件——保证后续探针 b/c 始终有目标，契约不因目录为空而退化
    #    或抛异常（空目录分支由此与一般分支统一）
    # 1) 记录原模式：path 目录 + 其内一层已存在文件（注入目录都很小；递归遇到
    #    子目录则按目录处理）
    # 2) chmod 层：目录 0o555、文件 0o444
    # 3) 探针×3：
    #    a) 在 path 内 O_CREAT|O_EXCL 创建探测文件 —— 必须失败（探测文件用后即删，
    #       且必须在进入 mount 层之前删除干净，否则 ro 下删不掉、残留会污染后续
    #       fixture 空态/模板校验）
    #    b) 对哨兵文件尝试 r+/追加打开 —— 必须失败
    #    c) 对哨兵文件尝试 os.unlink —— 必须失败
    #    三探针都失败 → 契约成立（非 root 宿主路径）
    #    任一探针通过（root 场景 chmod 不约束）→ mount 层：
    #    mount --bind path path && mount -o remount,bind,ro path，再跑三探针，
    #    仍不成立 → 抛异常：注入未建立，测试不得继续
    # 4) 令牌记录 (path, 原模式表, 哨兵文件名, 是否挂载)

def allow_writes(token):
    """按令牌恢复：先 umount（若挂载），再逐项恢复原模式，最后删除哨兵文件。任一步失败抛异常。"""
```

- 双机制按**探针结果**选择，不按环境猜测；两环境最终契约一致（这正是 AC1 对拍可比的前提——
  对拍比的是同一实验，不是两个实验）。
- fail-closed：契约建立不了抛异常，杜绝"注入失效但套件绿灯"。
- 显式令牌恢复（不用上下文管理器魔法），套件用 try/finally 包住断言段。
- ro bind mount 在 user namespace 内可用性已有先例：`namespace.py:14` 同机制挂只读发行，
  `test_execution.py` 有真实 unshare+mount 测试。

转换点（仅两处注入；`r67:273`/`r61:59-69` 的 chmod 是 0o755/0o644 模式翻转，root 下行为
一致，不动）：`r1r2_tests.py:92→122`、`r68_tests.py:286→299`。

### D1.2 保守串行套件逐套件审计

11 个无 chmod 注入的串行套件，逐个核对四项：夹具来源（模板克隆/自带）、共享路径
（`WF_LEGACY_FIXTURE_ROOT` 在 worker 内是 `$FIX.legacy`，私有）、用户状态（isolated-user）、
pty/sleep 在 ns 内可用性：`cp3`、`cp4_a8`、`cp5_b12`、`r7r15`、`r35`、`r67`、`r69`、`r70`、
`r71`、`r89`、`r90`。审计结论逐条写入 implement.md 审计记录；发现真实共享状态依赖的，
保持 `parallel: false` 并在 `notes` 登记理由（预期为空或极少）。

### D1.3 isolated-user 特判进注册表

现状：`run_all.sh:84` 的 `case cp3_tests|r1r2_tests` 特判，且 **run_one.sh（并行路径）没有
这个特判**——套件进并行池就会写真用户状态。

- `suites.json`：`cp3_tests`/`r1r2_tests` 增加 `"isolated_user": true`；
- `plan.py`：sh 输出增加 `PLAN_ISOLATED_SUITES`（来源仅 suites.json，名字存在性校验）；
- `run_all.sh`/`run_one.sh`：删 bash case，改查 `WF_ISOLATED_SUITES` 成员关系。
  数据单一来源在注册表；两个消费点只做成员判断（判定一处、消费两处，符合"同一判定
  只有一处实现"）。

### D1.4 串行标记单一来源

删除 `plan.py::PARALLEL_SERIAL` 常量；串行集合改由 `suites.json` 的 `"parallel": false`
字段推导（plan.py 读取并输出 `PLAN_SUITES_SERIAL`）。串行理由写同一条目的 `notes`——
**同一事实不再有两处真相**。`--serial` 全串行模式保留（确定性/排障用途不变）。

## D2 默认并发（R2）

`plan.py`：`DEFAULT_JOBS = min(8, os.cpu_count() or 4)`，`DEFAULT_REPRO_JOBS` 同式。
理由：固定 8 在少核机器上会超订。独立 `repro/run.sh` 的默认 `JOBS=1` 不变（交付纪律 §7
表格的兼容承诺）。summary 的 requested/effective/fallback 语义不变；等价性对拍在 jobs=8
下重做。**同批记录**：8 并发下最慢单元耗时与 `WF_COMMAND_TIMEOUT`(180s)/`WF_REPRO_TIMEOUT`
(120s) 的余量（当前最慢单元 ~26s，余量充足，但需实测确认而非沿用旧值）。

## D3 映射补全与双向校验（R3）

- 补齐 **18 个**可计划未映射套件的 modules 条目（r80–r88、r62、r64、r65、r55、r25r30、
  cp5_b12、cp5_b345、p5_v1、f1_candidate_smoke）。映射依据 = full/README.md 覆盖行 +
  套件 docstring 点名的 wflib 模块/入口，逐条依据写入 implement.md 映射记录，不凭名字猜。
- `d1_tests`/`d1_wf_tests`（kind=manual）不参与映射与校验——不在任何计划模式内，建议会误导。
- `_validate_modules` 三条校验（各自有负例）：
  1. kind ∈ {suite, extra, candidate} 的每个套件被 ≥1 模块覆盖，否则 PlanError 列出名单；
  2. 每个 modules key 在仓库中真实存在——**解析基准与 `_normalize_change` 同构**：
     key 按 `docs/workflows/wf/` 前缀剥除后的相对路径解析（`REPO/docs/workflows/wf/<key>`），
     不按仓库根裸解析（`_normalize_change` 对前缀外路径原样透传，若将来出现 `scripts/...` 类
     key，须同批扩展解析基准并在校验中显式声明，不静默换基准）；已核对现有 20 个 key 在
     该基准下全部存在；
  3. `map_changes` 命中 key 时该条目 suites 不得为空（空条目 = 建议静默缺失）。
- 校验只读 suites.json，不引入第二份数据。

## D4 解释器与路径的显式契约化（R4）——**SUT 驱动侧是行为决策，不是清理**

### D4.1 三个解释器面必须分开

- **SUT 驱动面**（启动被测 `wf.py`）：`wfdrive.py::PYTHON` 与 `repro/_harness.py::WF_PYTHON`
  （后者不 import 前者，是两份字面量——AC4 白名单登记**两行**）统一为：

  ```python
  PYTHON = os.environ.get("WF_TEST_PYTHON") or "<异解释器默认>"
  ```

  **默认保持异解释器（如 `/usr/bin/python3`）是既定决策，不是待验证的假设**——理由见
  D4.3 的结构性论证。`WF_TEST_PYTHON` 是可覆盖口。**SUT 驱动面覆盖全部三层**：full 套件
  驱动点（含 r1r2:187 的"先拼列表再 spawn"形态）、repro harness、单元层驱动点
  （`test_fixture_template.py:145` 经 sys.path 引 `wfdrive.PYTHON`）与 manual 套件
  （`d1_tests.py:7` 改引 `wfdrive.PYTHON`）——一律同一常量，**不新增第三处默认字面量**。

- **工具面（启动 `install.py` / `scripts/wf-dev-deploy.py`）**：r69/r70/r72/r89（install.py）、
  p5_v1/r90（wf-dev-deploy.py）的写死 `/softwares/...` 归一到
  `wfdrive.TOOL_PYTHON = sys.executable`——与今天实际所跑（3.14.7）一致，**无行为变化**；
  与 SUT 驱动面**不共用默认**：`install.py::runtime_support`（:479）用 `sys.executable`
  起子进程自检，安装器解释器若随 SUT 默认漂移到 3.13.5，自检跑的就不是同一个解释器，
  且无等价证据。shell 入口（run_all.sh/wf_fixture.sh/repro/run.sh/f2_setup.sh/d1_rebuild.sh
  的 `PY=`）**保留** `/softwares/...` 并注释为项目声明解释器（AGENTS.md §4）。

- **数据面（不动，行级白名单，两类字面量）**：`/usr/bin/python3` 侧——d21 的 PY_A/PY_B
  （双解释器并存就是断言主体）、~66 处 argv 断言数据、`_executor_set` 的
  `shutil.copy2("/usr/bin/python3", path)`（复制系统解释器伪造 venv 探测对象）、r1r2 的
  config/baseline 夹具数据（:176/:181）；`/softwares/...` 侧——
  `executor-project-key-unusable.py` 的 `GLOBAL_PY` 与注入补丁源码串（:19/:24/:25）、
  d21 的 docstring（:6）与 `PY_B`（:21）、`full/README.md:9` 文档字样。白名单按
  **文件 + 命中数 + 命中行内容摘要**登记——不用行号（Step 6 同批编辑 86 处路径字面量
  会使行号位移，行号快照在步骤内自我失效）；门槛复核前按当前树重生成快照再比对；
  反向正则只扫代码文件（`*.py`/`*.sh`），不扫 `*.md`。守恒校验：全库命中数 −
  白名单登记数 = 0（反向正则匹配不到列表后置 spawn 的形态，守恒校验兜住这类两头漏）。

- **三条最小单元断言**（交付纪律 §6"有实现、无断言 = 未验证"；每条一行，成本远低于
  事后排查）：① `WF_TEST_PYTHON` 设置后 `wfdrive.PYTHON` 取该值；② `wfdrive.PYTHON`
  的默认 == `_harness.WF_PYTHON` 的默认（两处字面量的防漂移守卫——设计承认它们必须
  一致，就必须有断言强制）；③ `TOOL_PYTHON == sys.executable`。

### D4.2 路径字面量

`wfdrive.py` 增加 `REPO`（`__file__` 上溯派生）与
`LIB = os.environ.get("WF_TEST_LIB") or REPO/docs/workflows/wf/payload/lib`。
86 处 `/home/xzc/...` 按语义替换：payload/lib 语义 → `wfdrive.LIB`（run_all 环境下自动落
发行副本）；仓库其他资产 → `wfdrive.REPO` 拼接。逐文件复核，不盲式 sed。

### D4.3 进程锚点拓扑：为什么 SUT 驱动解释器**不做统一**（本项是 D4 的核心）

`wflib/session.py::l2_anchor` 会**跳过与自身 `sys.executable` 相同的祖先**（session.py:297，
按解释器可执行文件跳过，不按名字）。

**结构性论证（无需测量即成立）**：

- 现状（SUT=3.13.5，驱动链=3.14.7）：SUT 向上走，套件层解释器不同 → 不跳过 → 锚点落在
  套件进程；
- 统一后（SUT == 驱动链解释器）：套件层被跳过 → execution.py 层也被跳过 → 锚点被推出
  harness 之外（落到终端/agent 进程，**随调用环境而变、不可复现**），甚至落空返回 `None`——
  在无 host 会话标识、无信封的入口上，`_establish_auto_session` 将抛
  `WF_IDENTITY_UNRESOLVED`（"锚点消失"是比"锚点上移"更硬的失败形态）。

即：**两配置的锚点必然不同，"等价"分支结构性不存在**；而 full 层没有任何断言消费真实
进程锚点（`anchor_conflict`/`host_identity_absent` 仅在单元层以合成 facts 消费，全层套件
不跑真实锚点路径）——统一等于引入**无断言覆盖的 SUT 可见行为变更**，正是本任务
"不引入新问题"所禁止的。

**决策（既定，非矩阵悬念）**：SUT 驱动解释器保持异解释器默认，交付形态为
"单点默认 + `WF_TEST_PYTHON` 可覆盖 + 契约登记"：

- `wfdrive.PYTHON` 与 `_harness.WF_PYTHON` 两处默认字面量（后者不 import 前者），
  AC4 白名单登记**两行**并注明锚点耦合理由；
- run_all / 独立 repro / 手工单套件三入口经同一常量取值，行为一致；
- 交付纪律登记："SUT 驱动解释器 ≠ 运行器解释器是 session 锚点拓扑的既定前提，
  不得当纯清理"。

**探针（证据固化，非决策依据）**：任务目录内的双配置探针脚本在
`unshare -Urm bash -c` + 两级 python 祖先的最小复刻链下运行（贴近 worker 真实链
`bash → xargs → unshare → execution.py → suite → SUT` 的层级深度），分别以异解释器与
同解释器 spawn 子进程调用 `session.l2_anchor()`。**其证据效力限定为"差异存在性"**——
配置②的具体锚点值取决于探针调用方环境、不可跨终端复现，不作为"具体锚点值"证据。
输出存任务目录 `evidence/`，供交付纪律的登记引用。

## D5 结果缓存轮转（R5）——存量与泄漏源必须一起解决

### D5.1 泄漏源修复（不修则轮转永远追不上；但不能打红契约）

`plan.py` `list_only` 分支的判据改为"**`WF_RESULTS_DIR` 未显式给出**且目录不存在 → 不建不写"：

- `run_all.sh` 全路径（含 `--dry-run`/`--list`）：run_all 总是显式设置 `WF_RESULTS_DIR`
  （用户给定或默认，line 40-41 export）且 `claim-results`（:48）先于 plan 调用（:58）→
  plan.py 看到"显式给出" → plan.json 照写，
  `test_run_all_contract.py::test_dry_run_only_prints_plan`（读该文件）行为**不变**；
- 直接 `plan.py --list`（无 run_all）：`WF_RESULTS_DIR` 未设置 → 不建不写，泄漏消失；
  stdout 的 sh/json emit 输出完整，无信息损失。

比"目录是否已存在"判据更可解释：后者会把"恰好存在的默认目录"（如 PID 碰撞复现的旧
无主目录）误当显式目录写入。

### D5.2 prune-results（fixture_scope.py 新子命令）

`prune-results <root> --scope run|repro --keep N --exclude DIR`：

- **root 可注入**（`WF_RESULTS_CACHE`，默认标准缓存根 `~/.cache/wf-test-run`）：run_all.sh
  与 repro/run.sh 调 prune 时读该环境变量。**为什么必须可注入**：r67 复制 run_all.sh 构造
  假环境、契约测试真跑 run_all——若 root 是硬编码常量，这两类测试会对**真实用户缓存**
  执行 prune；今天只有 3 个有主目录"看起来无害"，一旦有主目录超过 keep-N，r67 回归就会
  删掉用户的真实结果目录，且测试结果随缓存状态漂移。**r67 假环境与契约测试必须把
  `WF_RESULTS_CACHE` 指向各自临时根**（r67 的假树构造与 `test_run_all_contract` 的 env
  各自补上）。root 不在 `/tmp` 或标准缓存根之下时拒绝（沿用 `fixture_scope.validate`
  的边界）。
- 只枚举 root 下 `run-*`/`repro-*` 中**与 --scope 前缀匹配**的目录：run_all 只回收
  `run-*`，独立 repro 入口只回收 `repro-*`——独立跑 repro 不会越界回收套件 run 目录。
- 每个候选读 `.wf-results-owner.json`，仅当记录等于 `{'owner': OWNER, 'root': <绝对路径>}`
  才可删；marker 不可读/记录不匹配/符号链接 → 跳过（fail-safe：宁可留着）。
- 按 marker mtime 排序保留最新 N（默认 20）；`--exclude` 永不删（当前 run、r67 假运行器
  目录等活跃目录由此保护）。
- `repro-state.json` 是文件且不匹配目录模式，实现里再显式跳过非目录项，双保险。
- 删除失败跳过并计数，不中断运行；输出 `PRUNED=<n> KEPT=<m>`。
- **安全前提（写进设计，不留推理）**：prune 不做 liveness 探测，其安全性隐式依赖
  "全局 flock 只允许一个根运行器持有 lease"（`fixture_scope.lock_run`）——正在运行的
  run 目录必然属于 lease 持有者，其他运行器无法创建 marker，故不存在"删到活目录"的
  窗口。该前提若被破坏（绕过 lease 的调用），prune 只会漏删不会误删（marker 校验兜底）。
- 单元测试进 `test_fixture_scope.py`：最旧先删 / keep-N / 前缀隔离 / 无主不动 / exclude
  不动 / marker 损坏跳过 / 非标准 root 拒绝。

### D5.3 存量收敛（bootstrap，一次性，受 scope 约束）

`prune-results --bootstrap`：对无主候选目录增加保守判定，**且与 D5.2 共用 `--scope` 前缀
隔离**（run_all 入口只 bootstrap `run-*`，独立 repro 入口只 bootstrap `repro-*`——
AC5 的"前缀互不越界"对 bootstrap 同样成立）：

- 目录名匹配 `run-<纯数字>` 或 `repro-<mode>-<纯数字>`（实测命名如 `repro-green-962923`）；
- **顶层**内容全部属于运行器已知产物（**顶层判定是有意的**：`logs/`、`template/`、`repro/`
  子树内容不再逐项审查——它们全部是运行器自产副本，整树删除是预期行为；实现注释写明，
  不让"content whitelist"承诺与实际口径不一致）：
  - 文件白名单：`*.json`/`*.out`/`*.log`/`*.timing`/`lines`/`plan.err`/`selection.tsv`
    （复用 prepare-results 的白名单）；
  - **已知子目录名**（不要求 marker——实测它们没有 results marker）：`logs/`（空目录，
    `prepare_results` 无条件 mkdir 的产物）、`repro/`（repro 结果子树）、`template/`
    （夹具模板副本，含 `.agents` 等夹具内容）；
  - 顶层含任何未知文件名或未知目录 → 跳过并列出。
- **尊重 `--exclude`**（当前 run、r67 假运行器目录、marker 损坏的活跃目录由此保护），
  **不看 keep-N**（bootstrap 是存量收敛，与增量保留策略正交）。
- **前置**：bootstrap 之前先把本任务引用的基线证据（`run-1964465`/`run-2034392` 的
  `summary.json` 与 `lines`）归档进任务目录——它们无 marker、内容全合格，正是删除对象，
  不先归档则 Background 的数字失去可复核性。
- 本次任务执行**两次手工调用**（`--scope run` 与 `--scope repro`——bootstrap 受 scope
  约束，单次只清一个前缀，另侧合格目录会留存；**bootstrap 无自动调用点**，不接入
  run_all/repro 的常规路径），**对账口径（实测）**：488 个名字匹配目录中 **476 个合格**
  （run 侧 473 + repro 侧 3，后者内容 = `*.json` + `logs/` + `selection.tsv` 全在白名单内）、
  **12 个跳过**——全部因顶层含 `flows` 文件（旧运行器产物），其中 1 个（run-1747855）
  另有 45 个 `home-*` 残留目录（旧 isolated HOME 残留，白名单正确拒绝未知目录）；
  执行后 `~/.cache/wf-test-run` 目录数预期 ≈ keep(20) + 12。此后靠 D5.1 的泄漏修复维持
  收敛。AC5 按此对账，不把 12 个跳过项当"没删干净"。

## D6 断言解释收敛（R6）

- `run_all.sh::run_flow/run_f0/run_extra` 的 **3 处**（行 479/497/508）`grep -Ec` 计数全部
  删除，改读 `run_command` 已写出的结果 JSON（`$log.json` 的 `assertion_result.passed`）；
  `--expected` 判定本就由 `execution.py::verdict`（`ok = ... and passed == expected`）执行
  并反映在 rc 上，shell 侧不再重复判定，只负责展示与计数入账。JSON 解析用 `$PY -c`，
  解析失败按基础设施失败计（不静默）。
- 套件输出契约（`saved N / N`、`saved N cases; N passed`、`saved N cases` 三汇总行 +
  `[PASS]`/`PASS`/`[标签]: PASS` 行文法 + steps/TASK_ID 终态）集中写成 execution.py 模块
  docstring 的"输出契约"一节——适配器仍只有 verdict 一处实现，三格式是上一轮刻意保留的
  适配层，不新增解释点也不强改 59 个套件的输出。

## D7 小项清理（R7）

- `expected_seconds`：从 suites.json 全部条目删除（grep 证实零读者）。不加替代实现——
  性能门禁将来要做须带实现一起进。
- usage：`usage() { cat <<'EOF' ... EOF; }` 成为**唯一文本来源**，头注释压缩为一行指向
  `--help` 的说明——不保留两份手写文本（那是新的 drift 源）。5 个调用点（wf_fixture.sh
  两处、repro/run.sh 两处、run_all.sh 一处）全部走该函数。
- `run_one.sh`：`suite_millis` 改读 `$suite.test.log.json` 的 `seconds`（execution.py 单调钟；
  交付纪律 §12"单命令用 time.monotonic"口径不变）；`init_millis` 保留本地 now_ms（clone/
  template_check 不经 execution.py）。run_all.sh 的 now_ms 保留（阶段计时包裹多条命令）。
- ~~`WF_RESULTS_DIR` export 位置~~ **撤销**：`exec` 不改变 PID（实测验证），原"目录名含
  pre-exec PID"的判断不成立；目录名含租约进程 PID 是稳定且一致的命名，不改。
- 文档同步：full/README.md（并发默认、串行集合、解释器口径、prune/bootstrap 策略、性能
  数字）、交付纪律 §7（默认并行、对拍记录追加本次）、§12（prune-results 签名、套件耗时
  来源、D4.3 的锚点-解释器耦合契约）。

## Compatibility / Rollout / Rollback

- suites.json 变更：删 `expected_seconds`、增 `isolated_user`/`parallel`——向后兼容的增删
  字段，plan.py 同批消费，无中间态。
- 行为变化点：默认并发 4→min(8,cpu)、13 套件转并行、结果目录开始被轮转、历史无主目录被
  bootstrap 清理。**SUT 驱动解释器不变**（默认保持异解释器，D4.3 既定决策）；工具侧
  `TOOL_PYTHON=sys.executable` 与今天实际一致。前三者由等价性对拍覆盖；轮转由
  prune/bootstrap 单测 + 负例覆盖。
- 回滚：每 Step 独立提交可单独 revert；bootstrap 只删缓存（回滚无数据迁移）；无 schema
  迁移。

## Verification Strategy（按交付纪律 §7 顺序；步骤间有覆盖依赖，见下）

**覆盖依赖（防"验证了没修的那条路径"）**：Step 1 修的 `run_one.sh` 并行路径、Step 2 的
mount 层端到端，在 cp3/r1r2/r68/r1r2 仍处串行集合时**不可能被触发**——这两步的验证只覆盖
各自可达面（Step 1：串行路径 + 单元；Step 2：chmod 层 + 单测内 unshare 分支），**不构成
收口证据**；并行路径与 mount 层的端到端证据统一在 Step 3（套件移入并行池之后）补齐。

1. T0：`/softwares/python/bin/python3 -m unittest discover -s scripts/tests -t .`（每步之后）。
2. 契约：`WF_SLOW_TESTS=1 ... -m unittest scripts.tests.wf_runtime.test_run_all_contract`
   （含 `test_dry_run_only_prints_plan`——D5.1 的直接消费者）。
3. **r67 回归**：任何 runner 契约步骤（Step 1/6/7/8/9）之后
   `WF_SUITES="r67_tests" bash .../run_all.sh`——它是 run_all 契约的复制消费者。
4. 负例探针：`_validate_modules` 三条校验各一负例；prune 对无主目录/白名单外目录零动作；
   `deny_writes` 三探针在 ns 内与宿主上各验证一次成立（r68 用例 11 的 `WF_PERSISTENCE_FAILED`
   与 r1r2 的 R1 用例是行为锚点）。
5. 锚点探针（Step 6 专属）：D4.3 双配置探针在 unshare + 两级 python 祖先链下运行，输出
   作为"差异存在性"证据存档（不宣称具体锚点值）；决策已预定（保持异解释器默认），
   探针不是决策门。
6. 冒烟：`WF_SUITES="r68_tests r1r2_tests cp3_tests" bash .../run_all.sh`（Step 3 之后，
   此时走并行路径 + mount 层 + isolated-user）；工具侧归一后另跑
   `WF_SUITES="r69_tests r89_tests p5_v1 r90_tests" bash .../run_all.sh`（install.py 与
   wf-dev-deploy.py 两类启动点的代表）。
7. representative 预收口 → `--full --repro green`（并行，分段计时对照 AC1）→
   `--full --repro green --serial` → 逐项对拍。
8. grep 门槛（AC4：反向正则 + 白名单清单，机械可核验）+ `validate-wf-design.py`、
   `check-doc-refs.py`、`validate-skills.sh`。
9. 最终 diff 复核（含 untracked）。

## Tradeoffs（已决策项）

- **不做** O4 模板跨 run 缓存：与交付纪律 §7"不要跨 run 缓存模板"冲突，用户已确认。
- **不做** O5 lazy import：为测试提速改产品代码，收益不抵边界破坏。
- **不强制** 59 套件统一输出格式：verdict 适配层是上一轮刻意保留的设计，收敛到
  "解释唯一 + 契约文档化"即止。
- **不动** 数据侧 `/usr/bin/python3` 断言字面量与 shell 入口 `PY=/softwares/...`：前者是
  断言本体（替换即毁用例），后者是项目声明解释器约定（AGENTS.md §4）。
- **接受** SUT 驱动解释器**不统一**的结论（第三轮结构性论证）：换来的不是"消灭耦合"，
  而是"解释器选择"从 26 处散落硬编码变成两处单点默认 + `WF_TEST_PYTHON` 可覆盖 +
  交付纪律登记的显式契约——这是该耦合的正确形态；工具侧与路径字面量则真正归一。

## 审查修正记录
### 第一轮（2026-11-13，外部审查 → 核实 → 采纳）

| 审查发现 | 核实结果 | 处置 |
|---|---|---|
| 存量 488 目录仅 3 个有主，prune 对存量无效；`--list` 每次泄漏无主目录 | **属实**（实测 488/3；plan.py list_only makedirs 确认） | D5 重写：泄漏修复 + bootstrap 存量收敛 + AC5 存量判据 |
| AC4 全局 grep 归零会毁 d21 双解释器断言、_executor_set 复制源、66 处 argv 数据 | **属实**（逐一读取确认） | R4/D4 拆分驱动侧与数据侧，数据侧白名单制 |
| 漏了 /softwares 21 处（含 install.py 启动点） | **属实** | D4.1 收编：python 侧归一 wfdrive.PYTHON，shell 侧保留并注明约定 |
| D4 改变 session 锚点祖先跳过拓扑，full green 不能证明等价 | **属实**（session.py 机制确认） | D4.3：WF_TEST_PYTHON 口子 + 锚点前后对比 + 显式决策规则 |
| R3 反向校验不覆盖"命中 key 漏列套件"原始缺陷、假 key 可绕过 | **属实** | D3 三条校验 + 各自负例 |
| chmod 与 ro mount 机制不等价，对拍比的是两个实验 | **属实**（r68 注入目录含已存在文件；现靠 atomic_write 巧合等价） | D1.1 双探针等价契约（文件层也 deny） |
| 串行理由两处真相（plan 常量 + suites.json notes） | **属实** | D1.4：suites.json `parallel: false` 单一来源 |
| usage 改 heredoc 后变两份手写文本 | **属实**（5 调用点/4 区间，非 3 处） | D7：heredoc 唯一来源 + 头注释压缩为指向 |
| `WF_RESULTS_DIR` "pre-exec PID" 项是 no-op（exec 不改 PID） | **审查正确，原设计错误**（复核确认） | 撤销该项并留痕 |
| "20 个未映射"应为 18 可计划 + 2 manual；基线引用错位；grep 副本 3 处非 2 | **属实**（逐一复核） | 数字与口径全部修正 |
| r67 复制 run_all 契约，影响面漏登记 | **属实**（:216-220 确认） | Boundary 增列 + 每个契约步骤后 r67 回归 |
| prune 前缀越界（repro 回收 run 目录）；liveness 前提未写明 | **属实** | D5.2 scope 前缀隔离 + flock 前提显式化 |
| deny_writes 探测文件须在 mount 前删除 | **属实** | D1.1 步骤顺序明确 |
| AC1 分段计量；超时余量 8 并发下重估 | 采纳 | AC1 分段；D2 记录最慢单元余量 |

### 第二轮（2026-11-13，外部审查 → 核实 → 采纳）

| 审查发现 | 核实结果 | 处置 |
|---|---|---|
| D5.1 初稿删 list_only 的 plan.json 会打红 `test_dry_run_only_prints_plan`（该文件只由 list_only 写出，run_all dry-run 在 :67 早退到不了 :111） | **属实**（测试与早退路径逐行确认） | D5.1 改为"目录已存在才镜像写入"：契约测试与显式目录行为不变，直接 `--list` 泄漏消失 |
| bootstrap 白名单漏 `logs/`（空目录无 marker）、`template/`、`repro/`，存量收敛将为 0 | **属实**（实测 run-2759397 含空 logs/；run-1964465 含 repro/、template/） | D5.3 白名单显式枚举已知子目录名（不要求 marker） |
| bootstrap 会删掉任务自引用的基线证据（run-1964465/run-2034392 无 marker 且内容合格） | **属实**（两者均在无主名单） | Step 0 前置归档基线证据进任务目录；D5.3 写明前置 |
| D4.3"从会话记录提取锚点"不可执行：锚点无可观测面、夹具即删 | **属实**（全库无 l2_anchor 引用确认） | D4.3 重写：任务内双配置探针脚本（l2_anchor 只依赖进程谱系，无需夹具） |
| 保底"run_all 钉 WF_TEST_PYTHON"与 AC4 矛盾、且只钉一条入口 | **属实** | 保底分支改为"wfdrive 单点默认 + 同源常量贯通三入口 + AC4 白名单注明理由" |
| Step 1 验证覆盖不到并行路径（cp3 仍串行）；Step 2 mount 层同理 | **属实**（plan 按串行集合分区） | Verification Strategy 写明覆盖依赖；并行/mount 端到端证据统一在 Step 3 补齐 |
| 双探针契约在空注入目录无定义（r1r2 恰为空目录）；删除无探针 | **属实**（r1r2:91-92 确认） | D1.1 哨兵文件前置创建（空目录分支统一）+ 第三探针（unlink） |
| D3 校验②的 key 解析基准未定义（`_normalize_change` 对前缀外透传） | **属实**（函数确认） | D3：解析基准与 `_normalize_change` 同构（`REPO/docs/workflows/wf/<key>`），前缀外 key 须显式扩展声明 |
| bootstrap 与 D5.2 scope 打架；repro 命名是 `repro-<mode>-<pid>` | **属实**（实测 repro-green-962923 等） | bootstrap 受 scope 约束；匹配串按真实命名写死 |
| AC4 无机械判据 | 采纳 | AC4 改反向正则 + "文件 × 期望命中数"白名单清单 |
| 数字：489 目录（485+4）；路径 56 文件 86 行 | **属实** | PRD 修正 |

### 第三轮（2026-11-13，外部审查 → 核实 → 采纳；含一次对审查建议的改进）

| 审查发现 | 核实结果 | 处置 |
|---|---|---|
| D4.3 决策矩阵第 1 行结构性不可能（异解释器→锚点必落套件层；同解释器→套件层必被跳过），第 2 行无可观测断言（full 层零锚点消费），矩阵退化为必然保底，与 PRD Goal"消除耦合"矛盾 | **属实**（结构性论证复认；`anchor_conflict`/`host_identity_absent` 仅单元层合成 facts 消费） | **重新定性而非修补矩阵**：SUT 驱动解释器不做统一（既定决策），交付改为"单点默认 + 可覆盖 + 契约登记"；PRD Goal/R4/AC4 同批改写 |
| 矩阵漏"锚点消失"形态（配置②锚点推出 harness 外或 None → `WF_IDENTITY_UNRESOLVED`） | **属实**（逻辑成立） | 并入 D4.3 结构性论证（"锚点消失"是统一不可行的核心理由之一） |
| 保底会把安装器解释器从 3.14.7 降成 3.13.5（r69/r70/r72/r89/r90/p5_v1 归一到 wfdrive.PYTHON）且 `install.py::runtime_support:479` 用 `sys.executable` 自检 | **属实**（install.py:479 确认） | 工具面独立常量 `TOOL_PYTHON = sys.executable`（与今天一致、无行为变化、不与 SUT 默认共用）；启动点描述修正为 install.py/wf-dev-deploy.py 两类 |
| 文件×计数白名单会遮蔽 r1r2:187 真驱动点（同文件混数据侧与驱动侧；反向正则漏"先拼列表再 spawn"形态） | **属实**（:176/:181 数据、:187 驱动，逐一确认） | 白名单改**文件:行号**登记 + **守恒校验**（全库命中数 − 白名单行数 = 0） |
| "同源常量贯通三入口"不准确：`_harness` 不 import `wfdrive`，是两份字面量 | **属实** | D4.1/AC4 明确登记**两行**白名单（wfdrive 与 _harness 各一） |
| prune root 未定义（从 `WF_RESULTS_DIR` 反推可扫到任意父目录） | **属实** | root 固定标准缓存根、显式传入、非标准根拒绝 |
| bootstrap 与 `--exclude`/keep-N 关系未写；"内容白名单"实为顶层判定 | **属实** | bootstrap 尊重 `--exclude`、不看 keep-N；顶层判定**写明是有意的**（子树是运行器自产副本） |
| D5.1 判据应为"是否显式给出 WF_RESULTS_DIR"而非"目录是否已存在" | **属实**（后者有 PID 碰撞误写风险） | D5.1 判据改为环境变量显式性 |
| p5_v1/r90 实际启动 `wf-dev-deploy.py` 非 `install.py` | **属实**（:35/:75 确认） | 全部改写为"安装/部署工具启动点（install.py 或 wf-dev-deploy.py）" |
| 探针父链与真实 worker 链不同，配置②锚点值不可跨终端复现 | **属实** | 探针改在 `unshare -Urm bash -c` + 两级 python 祖先下运行；**证据效力限定为"差异存在性"**，不宣称具体锚点值 |
| Step 3 缺 r67 回归（r67 首次进并行池，"worker 私有 tmpfs + 私有租约下嵌套 run_all"从未跑过） | **属实** | Step 3 验证清单加入 r67 |
| 存量对账：476 合格 / 12 跳过（含 `flows` 文件），非"~485 合格" | **属实**（实测 488 目录：476/12，12 个均为顶层含 `flows`） | PRD/AC5/D5.3 按 476/12 对账，预期收敛 ≈ keep + 12 |

### 第四轮（2026-11-14，外部审查 → 核实 → 部分采纳；两处审查数字经实测驳回）

| 审查发现 | 核实结果 | 处置 |
|---|---|---|
| AC4 白名单分类漏三类：单元层真驱动点（test_fixture_template.py:145）、manual 套件驱动点（d1_tests.py:7）、`/softwares` 数据侧字面量（executor-project-key-unusable 的 GLOBAL_PY 与注入串、d21 docstring/PY_B、README:9） | **属实**（逐行确认） | D4.1：SUT 驱动面明确覆盖"full/repro/单元层/manual"四层、一律引 `wfdrive.PYTHON` 不新增第三处默认；`/softwares` 数据侧入白名单；门槛只扫代码文件 |
| prune root 硬编码标准根 → r67 假环境与契约测试会删真实用户缓存（有主目录超 keep-N 后必然发生，测试结果随缓存状态漂移） | **属实**（r67 复制 run_all.sh 的执行路径推演成立） | D5.2：root 改 `WF_RESULTS_CACHE` 可注入（默认标准根）；r67 假环境与契约测试指向临时根；bootstrap 无自动调用点 |
| 新增开关无断言（WF_TEST_PYTHON 覆盖、TOOL_PYTHON、两处默认一致性），违反交付纪律 §6 | **属实** | D4.1 增三条最小单元断言（覆盖生效 / 两默认相等 / TOOL_PYTHON==sys.executable） |
| scope 拆分使"执行一次 bootstrap"漏掉 repro 侧合格目录 | **要点属实，数字有误**：实测 repro 侧是 **3 个目录**（审查称 4；第 4 个是 `repro-state.json` 文件），run 侧合格 **473**（审查称 472）；总数 476 一致 | Step 7 明写两次调用（`--scope run` + `--scope repro`）；对账按 473+3=476 |
| 12 个跳过项里只有 11 个是 `flows`，第 12 个是 `home-r58_tests/` | **审查拆分错误，实测驳回**：12 个**全部**含 `flows`；其中 run-1747855 **额外**含 45 个 `home-*` 残留（它因 `flows` 已被跳过，`home-*` 是第二重不合格项，白名单拒绝未知目录的行为正确） | 对账口径保留"12 个含 `flows`"并补记 `home-*` 残留细节；审查的 11+1 拆分不采信 |
| 文件:行号白名单在 Step 6 内自我失效（同批编辑使行号位移） | **属实** | 白名单改"文件 + 命中数 + 命中行内容摘要"；复核前按当前树重生成快照 |
| `/softwares` 零残留门槛会因 README.md:9 文档字样永远无法归零 | **属实** | 门槛只扫 `*.py`/`*.sh` |
| Step 3 审计四项缺"嵌套运行器"列（r67 在 worker 私有 tmpfs + 私有租约下跑嵌套 run_all） | **属实** | 审计模板加第五项"嵌套运行器" |

