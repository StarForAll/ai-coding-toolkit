# wf 测试运行器第二轮：提速与证据完整性契约 — 技术设计

## Boundary

**修改范围**

- `scripts/tests/wf_runtime/full/run_all.sh`、`run_one.sh`、`plan.py`、注册表 `suites.json` → `units.json`（改名，见 D2.1）
- `scripts/tests/wf_runtime/full/execution.py`（只改"如何被消费"，不改断言解释规则）
- 新增 `scripts/tests/wf_runtime/full/source_hygiene.py`（P3-1 的替代机制，唯一实现）
- `scripts/tests/wf_runtime/full/template_check.py`：新增 `--expect-repoint-min N`（发布与克隆共用）
  与结构化改写计数输出（判定留在本文件一处，bash 只传参与读退出码）；其余空态判据不变
- `scripts/tests/wf_runtime/full/*_tests.py` / `*.py`：**只做**删除 `sys.path.insert(0, "/tmp")` 与
  `r64_tests.py` 移除 P3-1 自证用例；不做任何其他改动
- `scripts/tests/wf_runtime/full/r67_tests.py`（消费注册表与 plan 契约的假环境，必须同步）
- `scripts/tests/wf_runtime/test_test_runner_plan.py`、`test_run_all_contract.py`、新增
  `test_runner_hygiene.py`、新增 `test_runner_budgets.py`
- `scripts/tests/wf_runtime/full/README.md`、`.trellis/spec/docs/wf-delivery-discipline.md`
- `.gitignore`

**不修改**

- `docs/workflows/wf/payload/**`（产品）、`docs/workflows/wf-release/**`（发行树）
- repro 用例脚本的业务断言；`repro/run.sh` 的对外入口与机器可读汇总契约（D4.2 只改"何时启动"）
- 任何用例的断言内容（`r64` 的 P3-1 是唯一例外：它被判定为自证断言，替换而非删除覆盖）

**保留的单一来源（不得出现第二份）**

| 关注点 | 唯一实现 |
|---|---|
| 执行单元与期望用例数 | `units.json`（本轮由 `suites.json` 改名并扩展为统一注册表）+ `plan.py::load_units` 校验 |
| 选择/冲突/gating | `plan.py::plan()` |
| 执行与断言解释 | `execution.py::verdict` |
| 结果完整性 | `results_gate.py` |
| 夹具与结果目录所有权 | `fixture_scope.py` |
| 源树卫生 | 新增 `source_hygiene.py` |
| repro 选择与状态 | `repro/repro_select.py` + `repro/run.sh` |
| 并发预算 | `plan.py`（一处推导，两处消费） |

**特殊消费者**：`r67_tests.py` 构造假运行器树——它今天**按写死的文件名清单**复制 6 个文件
（`run_all.sh` / `plan.py` / `suites.json`（Step 2 改名 `units.json`）/ `results_gate.py` / `execution.py` /
`fixture_scope.py`），
并按注册表生成桩。本轮 run_all 新增了对 `source_hygiene.py`（必然调用）与 `template_check.py`（缓存路径）的依赖，
**写死清单必然失配**。因此本轮把"假树需要哪些文件"变成**单一来源的三类清单**：

- `plan.py` 新增**假树清单（三桶，单一来源）**——一个"helper 清单"无法同时表达"复制真实文件"与"必须桩化"：

  | 桶 | 内容 | r67 的处理 |
  |---|---|---|
  | `FAKE_TREE_COPY` | `plan.py` / `suites.json`（**Step 2 `git mv` 后为 `units.json`，桶条目随改名同提交**）/ `repro/groups.json` / `results_gate.py` / `execution.py` / `fixture_scope.py` / `template_check.py` / `source_hygiene.py` / `prepare_candidate_repo.py` | 原样复制（纯工具 + `plan.py` 无条件依赖的数据；假树语义不变） |
  | `FAKE_TREE_STUB` | `run_one.sh` / `wf_fixture.sh` / `f1_init.py` / `repro/run.sh` | **由 r67 自己写桩**——复制真实文件会改变假环境语义（假树没有真夹具、没有真 worker 契约；`repro/run.sh` 的桩负责吐 `REPRO_*` 汇总行，`r67_tests.py:271` 已有先例） |
  | `FAKE_TREE_SPECIAL` | `run_all.sh`（自身，复制） | 不做桩化、不做归类推导 |

  **过渡状态（写死，避免"照终态表在 Step 1 写 `units.json`"当场 file-not-found）**：三桶机制在 Step 1 引入，
  注册表改名在 Step 2。因此 Step 1 的桶内条目必须是**当前文件名 `suites.json`**；Step 2 与 `git mv` 同提交把它
  改成 `units.json`。G8 的"三桶条目必须存在"反向检查到 Step 5 才生效，过渡期由 Step 1/2 的 r67 冒烟守卫。

- **G8 判据（可满足、可机械化）**：扫描 `run_all.sh` 的**静态** `"$HERE/<相对路径>"` 引用，每个命中必须属于
  `FAKE_TREE_COPY ∪ FAKE_TREE_STUB ∪ FAKE_TREE_SPECIAL ∪ {注册表每个可计划单元的 script}`；
  并反向检查三桶里每个条目真实存在（防陈旧条目）。
- 注意 `repro/groups.json` 只能靠这张清单兜住：它由 `plan.py` 的常量引用（`plan.py:245` 无条件 `load_groups()`），
  不出现在 `run_all.sh` 的 `"$HERE/..."` 里，G8 扫不到——因此它的正确性由 r67 冒烟（Step 1/2/4）保证，并在清单注释里写明。
- **扫描口径写死**（否则 G8 的测试各有各的解析）：匹配双引号形态 `"$HERE/<相对路径>"`（含 `f1_init.py` 这类
  带数字的文件名、`repro/run.sh` 这类子目录路径），命中串 `normpath` 归一；**跳过**含 `$`（变量展开，
  如 `"$HERE/$suite.py"`）与含 `..`（纯路径运算，如 `"$HERE/../../../.."`）的引用。
  实测今天共 11 组静态引用：`fixture_scope.py`、`execution.py`、`plan.py`、`template_check.py`、
  `wf_fixture.sh`、`f1_init.py`、`run_one.sh`、`results_gate.py`、`repro/run.sh`、
  `prepare_candidate_repo.py`、`p5_f0.py`（最后一个在 Step 4 后消失，之前由注册表 `script` 值覆盖）。

r67 的桩生成必须按注册表逐**可计划**单元产出：**桩文件名取该单元的 `script`**（不是 `<name>.py`），输出行数等于
`expect`（`[PASS]` 行数；`verdict` 用 `passed == expected` 判，多一行同样变红）。这同时是 `script` 字段的
正确性证据——名字拼错会在假树里缺文件，当场由 run_all 的"文件不存在"失败暴露，而不是静默假绿。

---

## D1 卫生：把"导入优先级"和"源树卫生"从巧合变成契约

### D1.1 删除 `sys.path.insert(0, "/tmp")`（61 个文件）

- 事实：脚本以 `$PY $HERE/<unit>.py` 启动，`sys.path[0]` 已是 `full/` 目录；该行唯一效果是让 `/tmp`
  **优先于** harness 目录。实测（本次分析，已复原）：在 `/tmp` 放一个 `wfdrive.py`，`cp1_tests.py`
  直接导入伪造 harness 并 `SHADOW-HIT`。并行 worker 的 `/tmp` 是私有空 tmpfs，所以现状"恰好安全"；
  `--serial`、无 `unshare` 的机器、以及 README 允许的直接手跑都共享宿主 `/tmp`。
- 做法：机械删除该行（保留 `import wfdrive`）。**不做**任何路径注入替代方案（不需要）。
- 验证：全套 T0 + 3 个代表单元（`cp1_tests` / `r83_tests` / `r64_tests`）绿灯；新增机械门槛（D5.1）。

### D1.2 仓库级 pyc 忽略

- 现状：`.gitignore` 只有 `docs/workflows/wf/**/__pycache__/`；`scripts/tests/**/__pycache__` 仅因本机
  全局 `excludesFile`（`git check-ignore` 指向仓库外的全局文件）才不出现在 `git status`。
- 做法：加入仓库级 `__pycache__/` 与 `*.pyc`，并把原 payload 专用行删掉（一条规则覆盖，不留两条）。
- 验证：`git check-ignore -v` 对 `scripts/tests/**/__pycache__`、`docs/workflows/wf/payload/**` 均命中**仓库**
  `.gitignore`；`git status` 干净。

### D1.3 删除死字段

`units.json` 的 `fallback_representative`（全库仅一处、代码零引用）随注册表重构一并删除；
`load_units` 增加"未知字段"校验（白名单），防止下一个死字段悄无声息地长回来。

### D1.4 P3-1 自证断言的替代（唯一实现：`source_hygiene.py`）

- 现状问题：`r64_tests.py:90-99` 先 `rmtree` 所有 `__pycache__` 再断言"没有 `__pycache__`" → **恒真**，
  且测试在改作者源树。
- 替代设计：**由运行器承载"运行期不污染源树"这条不变量**，而不是由某个套件自证：

  ```
  source_hygiene.py snapshot <root>                     # {"pyc":[...], "pycache_dirs":[...]} 排序后落盘
  source_hygiene.py check <root> --expect <snapshot>    # delta 模式：新增 → 非零；存量 → 警告（不失败）
  source_hygiene.py check --strict <root>               # 绝对模式：有任何 pyc/__pycache__ 即非零
  ```

  两种模式同一实现：run_all 用 delta（本地存量不算本次回归），模板缓存条目用 strict（缓存必须绝对干净）。

  - 扫描面：`docs/workflows/wf`（含 payload；不含 `wf-release`，后者已有 `PRODUCT-TREE-CHANGED` 同族检查）；
    `scripts/tests` 作为第二面（T0 现场）。
  - **根不存在时按"空集合"处理并在输出里注明 `absent`**（r67 的假树只有 `scripts/tests/wf_runtime/full`，
    没有 `docs/workflows/wf`；若在此崩溃，等于让一个本不该失败的假环境变红——这是"引入新问题"的典型形态）。
    该行为配一条单元断言（临时空目录 → 退出 0、输出含 `absent`）。
  - **判据分工（防"绿着但脏"）**：运行期 `check` 只对**新增**失败（本地存量不属于本次运行的回归信号，
    否则一台本来就脏的机器会把 run 判红）；**存量**写进 summary 并在 stdout 打一行警告，
    附可直接执行的清理命令。AC3 的验收则用**绝对判据**（`find` 输出为空），且 Step 1 先把存量清空。
  - 可证伪性要分两次（原设计只有一句话，实际在 Step 1 时点做不到——那时 pyc 仍被全局禁用）：
    1. **检查本身可证伪**（Step 1）：手动在 payload 里放一个 `__pycache__/x.pyc` → `check` 必须非零；
    2. **策略可证伪**（Step 3，缓存策略落地后）：临时去掉 `PYTHONPYCACHEPREFIX` 跑一次 full →
       自然产生 pyc → `SOURCE-TREE-POLLUTED` 必须出现。
  - 两次演示的命令与输出写进 `implement.md` 的验证记录。
- `r64_tests.py` 删除 P3-1 用例（该套件的 `expect` 随之 −1，属于 R2 数据生成的输入）。

---

## D2 证据预算：注册表统一 + 期望值下发 + 不可静默缩水

### D2.1 注册表统一（消灭三个旁路：`flows` / `flow_expect` / `extra_expect`；并改名）

`suites.json` 升级 schema_version，并把文件名/键名与内容对齐为 **`units.json` / 顶层 `units`**
（四类执行单元都在里面，继续叫 `suites` 会让后来者误读；不保留旧名别名，避免两套名字长期并存）：

- `flows` 名单并入 `units` 数组（`kind: "flow"`），`flow_expect` / `extra_expect` 删除，期望值进入条目自身；
- `fallback_representative`（死字段）删除；
- 改名波及面（同批一次改完）：`plan.py`（`SUITES_JSON`→`UNITS_JSON`、`load_suites`→`load_units`、
  `describe()` 的 suites/flows/extra 三行摘要改为 units 汇总、`isolated_suites`→`isolated_units`）、
  `run_all.sh`（注释、变量、`export WF_ISOLATED_UNITS`）、`run_one.sh`（成员判定的 env 名）、
  `r67_tests.py`（复制清单 + `_manifest["suites"]`→`["units"]` + 桩生成按 `script`）、
  `test_test_runner_plan.py`（`plan.load_suites` 的 monkeypatch 与 PLAN_* 断言）、`full/README.md`、
  `.trellis/spec/docs/wf-delivery-discipline.md`。文件系统层面用 `git mv` 保留历史。

条目字段（白名单，`load_units` 校验）：

| 字段 | 适用 kind | 含义 |
|---|---|---|
| `name` | 全部 | 单元名；**执行脚本由 `script` 给出**（默认 `<name>.py`），两者不等价的例子见 `f0` |
| `script` | 全部 | 执行脚本文件名（默认 `<name>.py`；`f0` = `p5_f0.py`）；桩生成与 G8 一律读它，不按名字拼路径 |
| `kind` | 全部 | `suite` / `flow` / `extra` / `candidate` / `manual` |
| `expect` | `suite`/`flow`/`extra`/`candidate` | **期望用例数**（正整数，必填；`manual` 不需要） |
| `fixture` | `suite`/`flow`/`extra`/`candidate` | `template`（默认，模板克隆）或 `install`（安装器产生的项目，当前只有 `f0`） |
| `tags` / `representative` / `candidate_clean` / `isolated_user` / `parallel` / `notes` / `modules` | 可选 | 沿用现有语义 |
| `representative_flow` | 仅顶层一个 | 顶层字段保留 |

- `kind: manual` 的两个单元（`d1_tests` / `d1_wf_tests`）保留在注册表但不参与计划（不要求 `expect`），
  `load_units` 校验它们必须带 `notes` 说明"为何手动"。
- 顶层 `flows` 列表删除；`plan.py` 按 `kind` 选择，代表集逻辑不再为 flow 单开分支。
- 说明：`fixture` 目前只取 `template`/`install` 两值（`install` 仅 `f0`）。`cp4_a8`/`cp5_b12`/`cp5_b345`
  这类"自带夹具"的套件本轮**不改语义**（仍由 runner 提供模板夹具），扩展第三种值属另一件事，登记在"不做清单"外。

### D2.2 plan 输出契约变化

`--format sh` 输出从"套件列表 + 流程列表 + extra 列表 + 两张期望表"改为（**编码写死，不留实现自由度**）：

```
PLAN_UNITS='cp1_tests:suite:20:template:cp1_tests.py cp2_tests:suite:15:template:cp2_tests.py ... f0:flow:9:install:p5_f0.py ... r72_tests:extra:7:template:r72_tests.py'
PLAN_UNITS_PARALLEL='...'        # 并行子集（同一记录编码）
PLAN_UNITS_SERIAL='...'          # parallel:false 的子集（与上面互斥、并集=PLAN_UNITS）
PLAN_ISOLATED_UNITS='cp3_tests r1r2_tests'          # 名字列表（不是记录）
PLAN_JOBS / PLAN_REPRO_JOBS / PLAN_REPRO_*（保持现状）
```

记录编码：`name:kind:expect:fixture:script` **五段固定顺序**，冒号分隔、无空格。必须满足：

1. **单一列表**：四类可计划单元同池同编码，无第二份期望表（`flow_expect`/`extra_expect` 已删）；
2. **`script` 必须随记录下发**：`f0` 的执行脚本是 `p5_f0.py`，不等于 `<name>.py`；执行器只从记录取值，
   **不得按名字拼脚本路径**（拼出来的 `f0.py` 不存在）。这是 S7 在执行路径上的落点：
   记录之外的任何地方都没有 `script` 的第二个来源；
3. `plan.json` 的 `units` 条目与记录同源（`name/kind/expect/fixture/script`），不另存一份字段表；
4. `PLAN_ISOLATED_UNITS` 仍是名字列表——它只做成员判定，不参与分派。

记录的字段全部来自注册表（`plan()` 读取后逐单元转发），**注册表仍是唯一来源，记录只是执行期的传输格式**；
worker 因此**不读** `units.json`（它只消费一条记录），避免"worker 侧第二次数据解析"与假树/真树两套读取逻辑。
这不是第二份真相：任何字段变更只改注册表，记录随 plan 自动跟随。

校验（各自配负例）：`expect` 缺失 / 非正整数；`kind` 非法；`fixture` 非法；`script` 缺失，
或对**可计划单元**而言 `script` 在 `plan.py` 所在目录（`HERE/<script>`，r67 假树同样成立）不存在；
`parallel:false` 无 `notes`；每个可计划单元被 `modules` 覆盖（沿用上一轮双向校验）。
`manual` 单元不校验 `script` 存在性（不在任何执行面内）。

### D2.3 消费点

- 终态（Step 4 之后）：所有单元由**同一个 worker** 执行，`--expected <expect>` 在 worker 里从记录取值；
  `run_all.sh` 只做段编排与 `results_gate`/summary，不含任何按 kind 的执行分支。
- 过渡态（Step 2，调度未合并）：`run_all.sh` 按记录里的 `kind` 把单元派发到既有三段执行形状，
  每段仍经 `run_command ... --expected <expect>`；这段派发在 Step 4 被 worker 取代，**不长期保留**。
- `execution.py::verdict`：`expected` 语义不变（`passed == expected`），不新增判定路径。
- **不做**：不引入"断言内容指纹"之类的新机制（超出本轮收益）。

### D2.4 可证伪性（硬要求）

- 单元层（`execution.verdict`）：断言"用例数少 1 → `ok=False`"（负例）。
- plan 层（`load_units`）：`expect` 缺失/非正整数、`script` 缺失或文件不存在、未知字段、非法 `kind`/`fixture`、
  记录不是五段——各有一条 `PlanError` 负例。
- 运行器层（r67 假环境）：让某个桩少输出一行 `[PASS]` → 整体变红；再构造"漏跑一个**串行段**单元" →
  `MISSING-RESULTS` 必须出现（证明 gate 覆盖串行段，而不是只覆盖并行子集）。两条实证写入验证记录。

---

## D3 缓存策略：一处策略，两个载体

### D3.1 字节码缓存（本轮最大单项收益，实测 −35%）

- 现状：`run_all.sh:42 export PYTHONDONTWRITEBYTECODE=1` → 每次 `wf.py` 调用（1278 次/run，两次 python
  启动）都重编译 wflib；单次 `wf.py status` 118ms，其中 86ms 是编译。
- 新策略：**pyc 一律落在仓库与夹具之外**，由运行器统一下发 `PYTHONPYCACHEPREFIX`：

  ```
  WF_PYCACHE=${WF_PYCACHE:-$RESULTS_DIR/pycache}      # 随结果目录轮转，可注入
  export PYTHONPYCACHEPREFIX=$WF_PYCACHE
  unset PYTHONDONTWRITEBYTECODE                        # 不再使用该开关
  ```

  理由与约束（都已在分析中实测）：
  1. `PYTHONPYCACHEPREFIX` 按**源码绝对路径**分桶：每个 worker 的夹具路径不同 → 每套件一次性编译
     （~40–80ms）后全部命中；净收益仍是每套件 −4.8s。
  2. 不写进夹具 `.wf/lib/`：该目录在夹具仓库里是**未跟踪**的，pyc 会进入
     `git ls-files --others --exclude-standard`（`authorize.py:200`），有污染"未登记脏改动"类断言的现实风险。
  3. 不写进 `docs/workflows/wf/**`：源树卫生不变量（D1.4）。
  4. 必须可写且位于 worker 可见路径：`$RESULTS_DIR` 由 run_all 导出给 worker（串行/并行两条路径都已如此）。
- 文档化的 T0 命令同步带上前缀（否则 `unittest discover` 仍会往 payload 写 pyc；这在本次分析中已实测发生）。
- 度量：`summary.json` 增加 `pycache_root` 与"编译一次成本"无关的统计（不新增计时维度，只记路径与命中策略）。

### D3.2 模板跨 run 缓存（单套件 run 的最大固定开销，实测 2.73s）

**先摆清现有不变量**（跨 run 缓存必须原样继承）：
`template_check.py` 的 `--repoint-from <模板源>` 同时做两件事——把 `.wf/**/*.json|.md` 里指向模板源的
绝对前缀改写为当前项目路径，并断言**没有残留**该前缀（`check(leak_from=...)`）。
`run_all.sh` 的注释写明"复制不会搬走记录里的绝对路径与外部暂存目录，所以复制后必须机械核对"。
跨 run 缓存只是把"模板源"从每 run 的 `$RESULTS_DIR/template` 换成持久路径，**克隆后 repoint 这一步不能少**。

**实测依据（本轮核对）**：`wf_fixture.sh + f1_init.py` 之后，夹具 `.wf/**` 中指向自身根的记录只有 **1 个文件**
（`.wf/install/recovery.md:13` 的 `python3 <root>/.wf/bin/wf.py status`）；其余绝对路径只有 11 处 `/usr/bin`
（解释器确认记录，属合法的外部引用）。因此"自指记录数"是一个可测量、可断言的量，但它**不能靠假设**——
必须发布时量一次、命中时按量出的数复核（见下）。

- **载体**：`${WF_RESULTS_CACHE}/template/<key>/` + 同级 `<key>.meta.json`，字段：
  `key / digest / pyver / deploy / version / ref / root / created_at`。
  - `root` = 发布时的 `realpath(条目)`；**它是克隆时 repoint 的精确前缀来源**（不靠猜、不靠当前路径推断）。
  - metadata 放**同级**，不进模板内部（模板克隆出去必须仍是忠实空态）。
- **"改写数"这件事只留一个判据：`--expect-repoint-min 1`**（发布与克隆都用它）。理由：
  夹具必然留下 ≥1 处指向自身根的记录——`install.py:431-442` 与 `wf-dev-deploy.py:169-188` 都会把
  `abspath(target)` 写进 `.wf/install/recovery.md`，dev 与 candidate 两条部署路径都成立（本轮实测 dev：
  恰好 1 处）。因此"0 改写"永远是异常，`min 1` 就足以消灭静默 no-op；
  之前设计的"精确计数 + `meta.self_ref_files`"需要 worker 拿到计数（`run_one` 是唯一克隆点），
  要么新增导出变量、要么让 worker 读 meta——两者都是为一丁点额外强度换来的额外耦合。
  **改为 `min 1` 后：不需要新导出、`run_one` 不需要分支、run 内模板与缓存条目共用同一条克隆命令。**
- **key 的口径（写死，不留解释空间）**：
  `key = <digest12>-<py_maj.min>-<deploy>[-<version>-<ref>]`，其中
  `digest = wf_release_common.tree_digest(<repo>/docs/workflows/wf/payload)` 取前 12 位 hex。
  `tree_digest` 的语义是既成事实：**相对路径序遍历 + 逐文件 sha256，跳过 `.git`/`__pycache__`/`*.pyc`，
  不看 mtime**。推论必须显式写进负例：**改内容才失效；只 `touch` 不失效**（这是"内容摘要"应有的行为，
  否则 git checkout/clone 造成的 mtime 变化会让缓存全量失效）。
- **发布序列（唯一实现，写在 run_all 的一个函数里；`meta` 是"条目有效"的唯一标志）**：
  1. 在 `${WF_RESULTS_CACHE}/template/<key>.build/` 构建（`wf_fixture.sh` + `f1_init.py`）；
  2. `template_check <key>.build`（candidate 模式加 `--version/--ref`）——基本空态与安装身份；
  3. `rename(<key>.build → <key>)`；若 `<key>` 已存在，先把旧条目 `rename` 到 `<key>.stale-<pid>`；
  4. `template_check <key> --repoint-from <key>.build --expect-repoint-min 1` —— 一步完成重锚定、
     残留检查与"改写数 ≥1"判定（0 改写 = 发布失败，来源为路径形态不一致）；
  5. 写 `<key>.meta.json`（`.tmp` + rename），其中 `root=realpath(<key>)`。
     **这是最后一步**：没有 meta 的条目一律无效，命中时被挪 stale 并重建。
  **不宣称目录级 `os.replace` 原子覆盖**（非空目标会 `ENOTEMPTY`）：安全边界是"meta 最后写 + 先挪走再发布 + 全局 flock"。
  注意步骤 4 时 `<key>.build` 已被 rename（不存在），`realpath` 对缺失路径仍返回同一字符串，所以这一步本身不报错——
  **正因如此才需要 `--expect-repoint-min` 兜底，防静默 no-op**。
- **命中序列**（任一步失败 → 记 `TEMPLATE-CACHE-INVALID`、把条目挪 `.stale-<pid>`、回到构建路径，不静默复用）：
  1. `meta.root == realpath(<key>)` —— 否则 `TEMPLATE-CACHE-MOVED`（cache 根被移动/换了根/条目被拷贝过；
     这类条目内部记录仍指向旧根，克隆时 repoint 必然 0 命中）；
  2. `template_check <cached>`（空态/安装身份/version/ref）；
  3. `source_hygiene.py check --strict <cached>`（条目内不得有任何 `__pycache__`/`*.pyc`；与运行期 delta 同实现）；
  4. 克隆到 `$FIX`，然后 `template_check "$FIX" --repoint-from <meta.root> --expect-repoint-min 1`
     ——以**精确**发布根为前缀重锚定 + 残留检查 + "至少改写 1 个文件"；**0 改写即判该单元失败**
     （不是"继续跑"），因为这说明记录与 `meta.root` 不一致（条目被搬动/被改写/路径形态不符）。
     失败标签：夹具准备阶段新增 `prep_rc=5` → `TEMPLATE-REPOINT-MISMATCH`（与既有
     `FIXTURE-FAILED/INIT-FAILED/TEMPLATE-COPY-FAILED/TEMPLATE-COPY-INVALID` 同一张表；
     Step 4 合并后这张表只剩 run_one 一处）。
     **run 内模板路径同样传 `--expect-repoint-min 1`**（来源是 `$RESULTS_DIR/template`，本 run 刚由安装器写出，
     同样必有自指记录）——两条来源因此共用一条克隆命令，worker 无需知道来源类型。
- **缓存条目只读**：任何步骤都不得在条目内写文件（重锚定只发生在克隆产物上）。若有人误把条目 repoint 到自身，
  克隆阶段的 `--expect-repoint-min 1`（实际改写 0 个）会立即把它变成 `TEMPLATE-REPOINT-MISMATCH`——
  这条不变量由既有机制自检，不需要额外扫描器。
- **串味防线的四类残留源**（全部由上面 4 步覆盖，不新增第三套扫描器）：
  ① 共享缓存根（当前条目路径）→ 克隆后残留检查；
  ② **旧 cache 根** → `meta.root` 不一致在命中阶段就被拦（这正是第三轮审查指出的缺口）；
  ③ 上一 run 的 `$RESULTS_DIR` → 发布时 repoint 把记录改到条目自身，残留检查兜底；
  ④ 构建残留 `.build-*` → 发布后记录里不应出现该前缀；`source_hygiene`/`template_check` 的扫描面覆盖 `.wf/**`，
     另外每次运行开始按 mtime 清理 `.build-*`/`.stale-*`（保留当次自己的）。
- **开关语义（单一来源，写在此处）**：
  - `--no-template` / `WF_NO_TEMPLATE=1`：**关闭整套模板机制**——不构建 run 内模板、也不读/写跨 run 缓存，
    `template_source=none`、每单元重建夹具（今天的 `WF_NO_TEMPLATE` 语义 + 新增的"缓存一并关闭"）；
  - `--no-template-cache` / `WF_NO_TEMPLATE_CACHE=1`：**只关跨 run 缓存**，run 内模板照旧构建并复用
    （`template_source=run-build`）；
  - `--no-build` 语义不变（只管测试发行副本）。
  理由：`WF_NO_TEMPLATE=1` 的既有消费者是 r67 的假树（它没有 `template_check.py`、夹具是空 `.wf`），
  若缓存不随它关闭，假树会走进发布序列并失败；两者合成一个"模板机制总开关"才是可解释的。
  另外 r67 仍显式再钉一次 `WF_NO_TEMPLATE_CACHE=1`（防止将来实现漂移把这条蕴含关系丢掉）。
- **失效实证（AC5，七条，全部要可演示）**：
  ① 改 payload **内容** → digest 变 → 重建；**反向**：只 `touch` → 仍命中；
  ② 换解释器版本 → key 变；
  ③ candidate 换 version/ref → key 变；
  ④ 删掉 `<key>.meta.json`（模拟发布中途崩溃）→ 命中判无效并重建；
  ⑤ 把条目 `cp -a` 到另一个 cache 根（或改 `meta.root`）→ `TEMPLATE-CACHE-MOVED` → 重建
     （**不再声称"记录指向缓存目录"是失败态**：那是正常发布态，克隆时会被正确改写到 `$FIX`）；
  ⑥ 把 `meta.root` 改成另一个真实存在的绝对路径（模拟"记录与 root 不一致"）→ 克隆时改写 0 个 →
     `--expect-repoint-min 1` 失败 → `TEMPLATE-REPOINT-MISMATCH`（该单元失败，不继续跑）；
  ⑦ 往条目里塞一个 pyc → strict 判脏 → 重建。

### D3.3 缓存"不得静默生效"的判据（防新问题）

- summary 必须能区分三种夹具来源；**键的唯一定义在 D4.3 连续性表**，此处只写不得静默的判据：
  命中必须同时体现在 `template_source=cache`、`template_cache_hit=true`、`template_cache_key=<key>` 三处，
  且 `template_reused` 按 D4.3 的口径由 `WF_TEMPLATE_READY` 派生（命中路径同样置位）。
- **命中路径与 run-build 路径共用同一段 worker 代码**：run_all 命中时导出
  `WF_TEMPLATE=<缓存条目>`、`WF_TEMPLATE_READY=1`、`WF_TEMPLATE_SOURCE=<meta.root>`；
  run_one 的克隆分支照旧用 `--repoint-from "$WF_TEMPLATE_SOURCE"`（今天就有这个变量），
  **不新增分支**。因此 `template_reused` 的派生变量 `WF_TEMPLATE_READY` 在两条共享源路径上都是 1，
  只有 `--no-template` / 逐单元重建才是 0——"默认复用"的承诺与既有契约断言都保持成立。
- 复用后仍跑 `template_check`，不通过即失败而非"继续用"；
- 缓存条目内的任何非模板产物（`__pycache__`/`*.pyc`、结果文件、`.build-*` 残留）都视为脏 →
  由 `source_hygiene.py check --strict` 判定（唯一实现），命中即挪 stale 重建。

---

## D4 调度：一个池、一份预算、两条并发流水线

### D4.1 flows/extra 并入主池（实测 3 单元串行 13.89s → 并发 5.76s）

- worker 仍是一个入口 `run_one.sh`，按记录里的 `fixture` 字段分派：
  - `template` → 现有"克隆模板 + 空态复核"路径（缓存命中与 run 内模板共用这条命令，靠导出的
    `WF_TEMPLATE` / `WF_TEMPLATE_READY` / `WF_TEMPLATE_SOURCE` 三个变量区分来源；**不需要新导出**）；
  - `install` → 沿用现 `run_f0` 的 reset/`--forbid` 与 install 参数，把 `install.py` 装到
    `$LEGACY_FIXTURE_ROOT/<name>`，再执行**记录里的 `script`**（`f0` → `p5_f0.py`，不是 `<name>.py`），
    改成数据驱动。
- **worker 调用契约（必须在本步钉死，r67 的桩按它重写）**：

  | 项 | 契约 |
  |---|---|
  | 入参 | `run_one.sh <unit-record>`，**单参数**，即 plan 产出的 `name:kind:expect:fixture:script`（五段、冒号分隔、无空格）；worker 一次解析后，后续一切路径与键只用 `name` |
  | 环境 | `FIX HERE PY SHARED_RELEASE RESULTS_DIR SOURCE_HOME` + 全部 `WF_*`（沿用现有 export 面，含 `WF_ISOLATED_UNITS`） |
  | 执行域 | `WF_NAMESPACE=1`（默认，并行池：worker 首段照旧 `exec namespace.py`）；`WF_NAMESPACE=0`（串行段：**同一 worker**，不 exec namespace，保持宿主 `/tmp` + 无 `unshare` 的既有语义——它是 AC1 对拍的对照面）。两域共用同一条克隆/执行/结果行代码，只有隔离层不同；**夹具路径后缀 `-<unit>-<pid>` 只在 `WF_NAMESPACE=1` 域内加**（与今天 `run_one.sh` 的既有行为一致），串行域仍用共享 `$FIX`——否则串行对拍面会退化成"每个单元一套夹具" |
  | `kind` → `execution.py --kind` | `suite`/`candidate` → `suite`；`flow`/`extra` → `flow`（`execution.py` 的枚举只有 `raw/suite/flow/steps/repro`，没有 `extra`/`candidate`）。映射**只在 worker 一处**，plan 不下发 `--kind` |
  | `--expected` | 除 `manual` 外全部 kind 都传记录里的 `expect`（与 R2.2 一致） |
  | 结果行 | `name\trc\telapsed_s\tstatus\ttail` **五列，格式不变**（`results_gate.py` 只认五列） |
  | 夹具失败 | 复用 `prep_rc` 标签表（新增 `5` = `TEMPLATE-REPOINT-MISMATCH`、`6` = `INSTALL-FAILED`；install 分支失败并入同一张表，不另立打印分支） |
  | 计时 | worker 只写自己的 `<name>.timing`；`init_millis`/`suite_millis` 由父进程在**两段都结束后**统一读全部单元的 `.timing` 累加，worker 不累加，`run_suite` 的本地累加删除 |
  | 名字边界 | 以名字为键的消费点一律由记录的**第一段**派生，不新增第二份名单：`lines`、`<name>.timing`、`<name>.out/.test.log/.json`、`NAMESPACE_ERROR_LOG`、`results_gate --expected`、`KNOWN_LEGACY` 账目、summary 计数（夹具路径后缀的域边界见「执行域」行） |
  | 完整性覆盖 | `results_gate` 移到两段都完成之后，一次性对 `PLAN_UNITS` 全集（含串行段与 flow/extra 行）判定；**不再只覆盖并行子集**（今天串行段没有完整性判定，合并后若沿用"池内 gate"会把串行行判成 unexpected） |

- `run_all.sh` 不再保留任何单元执行逻辑：`run_suite` / `run_flow` / `run_f0` / `run_extra` / `expect_of` 全部删除，
  只留夹具模板构建、段编排（并行 `xargs` + 串行逐个调用 worker）、`results_gate` 一次性判定与 summary。
- 每个 worker 仍保持：私有 `/tmp` 与私有夹具路径（`WF_NAMESPACE=1` 并行域）、宿主共享 `/tmp`（`WF_NAMESPACE=0`
  串行域，与今天 `--serial` 一致）、只读挂共享发行、结果行唯一写入点；两域用同一条克隆/执行/结果行代码。

### D4.2 repro：默认串行，只提供显式开关（决策 #3）

- 事实：主池与 repro 是**两个独立的执行体**（`run_all.sh` 池 vs `repro/run.sh`），今天按 `主池 → flows → repro`
  串行。主池 CPU 298s、repro 190s，机器在 ~7 有效并行上饱和，所以"并发编排"只消屏障与尾部空转，
  实测预估 **3–6s**，且会引入资源竞争与抖动。
- **决定（用户拍板）**：默认 **保持串行**，行为与今天一致；并发只作为显式开关 `--repro-concurrent`
  存在的实验通道，不进默认路径，也不作为 AC1 的收益来源。
- 开关实现（放在 `run_all.sh` 的编排层，不动 `repro/run.sh` 的内部契约）：
  - 默认：主池跑完 → flows 已在池内 → 再顺序执行 `repro/run.sh`（参数仍全部来自 plan）；
  - `--repro-concurrent`：主池启动后后台启动 `repro/run.sh`，结束 join；失败传播与结果完整性判定与默认路径完全一致
    （结果缺失/畸形一律失败，不静默重跑）；
  - 两条路径都只在 summary 里记录 `pool_seconds` / `repro_seconds`，用于归因，不改变判定。
- 并发预算：串行路径下 `WF_TOTAL_JOBS` 全部给主池；开关打开时按工作比（主池 298s : repro 190s）分 5/3，
  换算公式写在 `plan.py` 一处，不在 bash 里重算。

### D4.3 summary 归因

`summary.json` 增加：`pool_seconds`、`repro_seconds`、`startup_seconds`、`template_source`、
`template_cache_hit`、`template_cache_key`、`pycache_root`、`budget` 块（阈值 + 实测 + 是否超阈值）。
`total_seconds` 仍是墙钟，schema_version +1。

**既有键的连续性承诺（flows 入池后不得改义）**——这是 `test_run_all_contract.py` 的对外契约：

| 键 | 语义（保持） | flows 入池后的实现 |
|---|---|---|
| `suite_ran` | `kind=suite` 的成功执行单元数 | 池内按 kind 计数，不受调度合并影响 |
| `flow_ran` | `kind=flow/extra` 的单元数（`--representative` 下为 2：`f0` + `p5_spec`） | 池内按 kind 计数（**不并入 `suite_ran`**，否则既有断言与运维口径一起漂移） |
| `repro_ran` | repro 用例数 | 不变 |
| `units_total` | 三者之和 | 不变（`suite_ran + flow_ran + repro_ran`） |
| `template_reused` | 本次 run 内单元**共用同一夹具源**（不逐单元重建）；默认 true | 由 `WF_TEMPLATE_READY` 派生，两条共享源路径（run 内构建 / 缓存条目）都置位；**语义由"run 内构建"放宽为"共享源"，属明确变更，同批改契约测试那一行注释** |
| `template_source` | 新增：`run-build` / `cache` / `none` | 三态取代布尔猜测 |
| `template_cache_hit` | 新增：`source == cache` | 跨 run 命中用这一键表达，不与 `template_reused` 混用 |
| `template_cache_key` | 新增：命中时的 key，否则 `null` | 与 meta 的 key 同源 |
| `init_seconds` / `suite_seconds` | 累计计时（**口径明确变更**） | 由"套件累计"扩为"**全部执行单元**累计"：flow/extra 现在也在池内并写 `.timing`；`timing_note` 措辞同批改为"全部单元的跨单元累计"，既有断言只检查 `> 0`，不受影响（口径变化登记在此，不静默漂移） |

理由（第四轮收敛）：原计划让 `template_reused` 严格保持"run 内构建"，但缓存命中路径不构建 run 内模板
（`WF_TEMPLATE_READY` 会是 0），那会让常见路径上该键变成 false、直接打挂它承诺要保护的契约断言；
因此**明确放宽**该键的含义为"共享源复用"，并用 `template_source` / `template_cache_hit` 把两种来源分开，
契约测试的断言值不变、只同步一行注释（本轮自查 S4 的最终口径）。同样地，
把 flow 单元折进 `suite_ran` 会让"流程跑了几条"这个运维口径消失。

**计数的唯一来源（合并后）**：`suite_ran` / `flow_ran` 由"`lines` 结果集 × 注册表 `kind`"在 gate 之后**一次派生**
（`suite`/`candidate` → `suite_ran`，`flow`/`extra` → `flow_ran`），不再在执行分支里递增
（今天 `suite_ran`/`flow_ran` 由 `run_suite`/`run_flow`/`run_f0`/`run_extra` 各自 `+=1`，合并后这些分支消失；
保留两套递增会让并行/串行段的计数口径分叉）。

**计数不变式（唯一写法，AC1/对拍都引用这一条）**：
`lines 行数 == suite_ran + flow_ran`（repro 用例不写 `lines`）；
`units_total == suite_ran + flow_ran + repro_ran`；`repro_ran == repro 执行体的 REPRO_TOTAL`。
实测基线（`run-3290992`）：`lines`=59、`suite_ran`=59、`flow_ran`=5、`repro_ran`=85、`units_total`=149
——"四个计数都等于行数"从来不是事实，也不该被写成判据。

---

## D5 防回归闸门（把"这次修好"变成"以后不能坏"）

| 闸门 | 形式 | 判据 |
|---|---|---|
| G1 `/tmp` 导入注入 | 新增单元测试扫描 `scripts/tests/**/*.py` | 命中集合为空，否则失败 |
| G2 pyc 策略 | 新增单元测试读 `run_all.sh` | 必须含 `PYTHONPYCACHEPREFIX`，不得含 `PYTHONDONTWRITEBYTECODE` 导出 |
| G3 `.gitignore` | 单元测试读 `.gitignore` | 含 `__pycache__/` 与 `*.pyc` |
| G4 注册表完整性 | `plan.py::load_units` | 未知字段、缺 `expect`、非法 `kind`/`fixture`、无理由 `parallel:false` 全部拒绝 |
| G5 产品热路径 | 新增 `test_runner_budgets.py` | `wf.py status`（pyc 预热）**5 次中位数 < 500ms**（≈8× 现状 62ms；用于尽早抓 `task-check 1.87s` 那类 30× 回归）。**阈值只有这一个数**，PRD R5.4 同值；允许 `WF_PERF_GUARD=0` 关闭并在断言消息里报实测值 |
| G6 预算可见 | summary `budget` 块 | 只报告不硬失败（理由见下） |
| G7 源树卫生 | run_all 前后快照 | 新增 pyc → 失败（D1.4） |
| G8 假树清单完整性 | 新增单元测试按固定口径解析 `run_all.sh` 的静态 `"$HERE/<相对路径>"` 引用 | 每个命中 ∈ COPY∪STUB∪SPECIAL∪注册表 script；三桶条目必须存在；缺登记即失败 |
| G9 假树缺根容错 | 新增单元测试（临时空目录） | `source_hygiene snapshot/check` 退出 0 且输出含 `absent` |

**G6 不硬失败的论证**：运行期墙钟受机器负载、文件系统缓存、并行分配影响，硬阈值在**任意机器**上都会假红；
"静默变慢"的正确处置是**可见 + 可追溯**（summary 的分段与阈值偏离），由人在收口时对比基线。
运行期硬约束只放在**与机器无关的量**上：单元数（`expect`）、并发预算、超时余量、串并等价性。

**与 AC1 的口径区别（回应审查意见 #4）**：AC1 是**任务验收证据**，只在同一台机器、与基线同口径下比较
（硬性 ≤65s = 相对基线 −30%，60s 为目标并要求超目标时给出归因与处置）；G6 约束的是**运行期门禁**，
不允许在任意机器上对墙钟硬失败。两者不矛盾，且都在 PRD 里写明。

---

## 兼容性 / 迁移

- 注册表迁移（`suites.json` → `units.json`）：`+expect`、`+fixture`、顶层 `units`、`-flows`、
  `-flow_expect`、`-extra_expect`、`-fallback_representative`。`plan.py` 升级后**旧文件必须被拒绝并给出迁移提示**
  （不静默兼容，避免两套 schema 并存）；用 `git mv` 改名保留历史。
- `plan.py --format sh` 输出改为 `PLAN_UNITS`（逐单元 `name:kind:expect:fixture:script`）：`run_all.sh` 与
  `r67_tests.py` 是仅有的两个消费者，必须同批改。`plan.json` **直接换成 `units` 结构，不保留 deprecated 旧键**
  ——保留旧键会让同一事实短期存在两份真相（本轮自查 S2）。
- `plan.json` 的 `suites_all` / `flows` / `extra` 三个键一并改为 `units`（含 `name/kind/expect/fixture/script`）：
  `test_run_all_contract.py` 断言了 `plan["suites_all"]`，必须同批改（本轮自查 S3），
  且该改动只能靠 `WF_SLOW_TESTS=1` 的慢测试发现——因此三处验证命令都必须显式开它。
- `PLAN_ISOLATED_SUITES` → `PLAN_ISOLATED_UNITS`，连带环境变量 `WF_ISOLATED_SUITES` → `WF_ISOLATED_UNITS`
  （`run_all.sh` 的 export 与 `run_one.sh` 的成员判定同批改；README/交付纪律的引用在 Step 5 同步）。
  不保留旧名：同一事实两个名字正是 S1/S2 要消灭的形态。
- `execution.py` 的 `--expected` 语义不变，因此 r67 的桩只需产出与 `expect` 一致的用例数
  （已核实：`verdict` 用 `passed == expected` 判，多跑一行同样变红，两个方向都被覆盖）。
- 文档：`full/README.md` 的"并行与子集/结果缓存轮转/性能/解释器契约"四段与
  `wf-delivery-discipline.md` §7（T0/T1/T2 表）、§12（超时与计时）同步更新，并写明
  **repro 默认串行**、**模板缓存与 pyc 策略**、**`expect` 契约**三件事。

## 回滚

- 每个 Step 独立提交；Step 3（缓存）与 Step 4（调度）各自带开关（`--no-template-cache`、`--repro-concurrent`），
  出问题可只回退单个开关而不回退整轮。
- 数据迁移（`units.json`）与代码（`plan.py` / `run_all.sh` / `r67_tests.py`）**必须同提交**，避免中间态；
  回滚该提交即回到旧 schema（旧文件仍在 `git mv` 之前的历史里）。

## 风险与对策

| 风险 | 对策 |
|---|---|
| `PYTHONPYCACHEPREFIX` 在 worker/只读挂载/isolated-user（HOME 重定向）下行为异常 | Step 3 抽样必须含 `cp3_tests`（isolated_user）与一个普通套件，串行/并行各一次，确认 pyc 落在 `$RESULTS_DIR/pycache`；失败即回退该 Step |
| 模板缓存复用陈旧夹具 | digest+版本 key；命中即跑 `template_check`；克隆后 `--repoint-from <缓存路径>`；`meta` 最后写、无 meta 即无效；summary 记录命中/重建 |
| 存量 pyc 让 AC3“绿着但脏” | Step 1 先清存量再建快照；运行期只对新增失败（存量警告+清理命令）；AC3 用绝对判据（`find` 为空） |
| `expect` 数据与真实用例数漂移 | 由一次全绿结果机械生成；负例证明"少一行即红"；`expect` 变更必须与用例变更同提交 |
| 统一注册表改动面波及 r67/plan/run_all | Step 2 以"改 schema → 改 plan → 改 run_all → 改 r67 → 文档"固定顺序，每步跑 r67 回归 |
| 跨 run 缓存条目被搬动/换 cache 根 | `meta.root` 与 `realpath(条目)` 不等即失效重建；克隆用 `meta.root` 作精确前缀 |
| 克隆时 repoint 静默 no-op | `--expect-repoint-min 1`：改写 0 个即 `TEMPLATE-REPOINT-MISMATCH`，该单元失败（不继续） |
| 运行器新增 helper 后 r67 假树失配 | 假树清单改为单一来源三桶（`plan.py::FAKE_TREE_*`）+ G8 机械门槛（静态引用必须被归类） |
| `source_hygiene` 在假树缺扫描根时崩溃 | 根缺失按空集合处理并输出 `absent`，配单元断言；r67 与 `--dry-run` 路径都覆盖 |
| 契约测试（`WF_SLOW_TESTS=1`）在默认验证里被跳过 | Step 2/4/6 的验证命令显式开该开关；summary/plan 键的连续性写进 D4.3 作为验收项 |
| repro 并发的实验通道引入抖动 | 默认串行（决策 #3），开关不进默认路径；开关打开时按 5/3 分配并记录分段耗时；出问题直接停用该开关，不影响默认路径 |
| 61 文件机械删除引入语法/行为差异 | 只删一行；删除后 `python -m compileall -q` + 3 个代表单元 + 全量对拍 |
| 记录编码（五段）与 `kind→--kind` 映射在 bash 里被重新拼装而漂移 | 编码/映射各只有一处（plan 产出记录、worker 解析记录）；`test_test_runner_plan.py` 断言记录恰为五段且 `script` 与注册表一致；r67 的桩文件名取 `script`（名字拼错即缺文件） |
| f0 / 三个 p5 flow 从宿主 `/tmp` 迁入 worker 私有 tmpfs 后行为变化 | Step 4 的 representative 与 full 覆盖安装+自举闭环；若出现"宿主 `/tmp` 假设"，按 R4.1 修 worker 的夹具路径而不是给 flow 单开宿主分支 |
| 合并后串行段首次纳入 `results_gate`，可能暴露此前被吞掉的串行失败 | 这正是证据完整性的收益；若变红，按"该单元的既有缺陷"处理并记录，**不得**把 gate 退回只覆盖并行子集 |
