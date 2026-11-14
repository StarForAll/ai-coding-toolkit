# wf 测试运行器第二轮：实施计划

> 执行模式：本仓 `.trellis/config.yaml` 为 inline（DSH），主会话直接实施与自检，不派子代理。
> 规划产物齐备后由用户审阅批准，再 `task.py start --allow-empty-context`（`implement.jsonl`/`check.jsonl` 有意留空）。

## 执行纪律（每一步都适用）

1. **运行中不得编辑 runner 文件**（bash 按偏移读取）：`run_all.sh` / `run_one.sh` / `plan.py` / `execution.py` /
   `fixture_scope.py` 的编辑必须在两次运行之间完成。
2. **同一判定只有一处实现**：如果某个改动只能以"再加一个分支/再复制一张表"的方式落地，停下来回到 `design.md` 修设计。
3. **每个 Step 结束即验证**（下表）；不做"全部改完再验"。
4. **用例只增不删**（`r64` 的 P3-1 例外，已在 design D1.4 论证）；`expect` 的变更必须与用例变更同一次提交。
5. 每个 Step 一次提交，提交信息写清"改了什么契约、验证了什么"。

## Step 0 — 基线与数据采集（改动前，只读）

- [ ] 采集基线两次 full 并行：`bash scripts/tests/wf_runtime/full/run_all.sh --full --repro green`（记录
      `summary.json` 的 `total_seconds` 与分段；目标基线 ~92–94s）。
- [ ] 单套件基线 2 个：`WF_SUITES=cp2_tests`（~13s）与 `WF_SUITES=r67_tests`（~4.6s），记录整次墙钟。
- [ ] 生成 `expect` 数据源：从上一步全绿结果目录的 `*.test.log.json` 读取每个单元的
      `assertion_result.passed`，落盘成 `expect` 草表（进入任务目录作为证据，不进仓库）。
- [ ] 记录每单元耗时（`*.timing`）与最慢单元，用于 Step 6 的超时余量结论。

**验证**：基线数字与设计中的测量值一致（±5%）；不一致先解释差异再继续。
**回滚点**：无改动。

## Step 1 — D1 卫生（机械、零行为变化）

> 顺序要点：**先清存量、再建快照**。当前树上已有 222 个 pyc / 10 个 `__pycache__`（`scripts/tests` 7 个、
> `payload` 3 个），只判"新增"会让 AC3 绿着通过而源树仍然脏。

- [ ] 清理存量：删除 `docs/workflows/wf` 与 `scripts/tests` 下所有 `__pycache__`/`*.pyc`
      （均为未跟踪构建产物；清理前后各跑一次 `git status` 确认无跟踪文件受影响）。
- [ ] 删除 61 个文件里的 `sys.path.insert(0, "/tmp")` 行（只删该行）。
- [ ] `.gitignore`：加入仓库级 `__pycache__/` 与 `*.pyc`，删除原 payload 专用行（一条规则）。
- [ ] 新增 `full/source_hygiene.py`（`snapshot` / `check` / `check --strict`）：`check` 对**新增**非零退出，
      对**存量**只打警告 + 打印可执行的清理命令；**扫描根不存在时按空集合处理并在输出里标 `absent`**（不崩溃）。
- [ ] `plan.py` 新增三桶假树清单：`FAKE_TREE_COPY`（含 `repro/groups.json`；**本步桶内的注册表条目必须写
      `suites.json`——它此刻还叫这个名字，Step 2 与 `git mv` 同提交改成 `units.json`**；先含
      `source_hygiene.py`，`template_check.py` 在 Step 3 加入）、
      `FAKE_TREE_STUB`（`run_one.sh`/`wf_fixture.sh`/`f1_init.py`/**`repro/run.sh`**——它由 r67 写 `REPRO_*` 桩）、
      `FAKE_TREE_SPECIAL`（仅 `run_all.sh` 自身）；
      `r67_tests.py` 改为 importlib 载入真实 `plan.py`，按 COPY 复制、按 STUB 写桩（**不得复制 STUB 条目**）。
- [ ] `run_all.sh`：构建前 `snapshot`、结束时 `check`；新增失败标签 `SOURCE-TREE-POLLUTED`。
- [ ] `r64_tests.py`：删除 P3-1 用例与相关 import（`shutil` 若不再使用一并删除）。
- [ ] 注册表本步**不动**（`units.json` 改名与 `expect` 在 Step 2 统一迁移）。

**验证**
```bash
# 语法自检也必须带 pycache 前缀，否则它自己就把 pyc 写进源树
PYTHONPYCACHEPREFIX=/tmp/wf-compile-check /softwares/python/bin/python3 -m compileall -q scripts/tests/wf_runtime/full
PYTHONPYCACHEPREFIX=/tmp/wf-unit-pycache /softwares/python/bin/python3 -m unittest discover -s scripts/tests -t .
grep -rn 'sys.path.insert(0, "/tmp")' scripts/tests | wc -l        # 必须为 0
git check-ignore -v scripts/tests/wf_runtime/__pycache__/x.pyc     # 必须命中仓库 .gitignore
find docs/workflows/wf scripts/tests \( -name '*.pyc' -o -name '__pycache__' \) | wc -l  # 必须为 0
# r67 假树是这份 run_all 的第一个外部消费者：本步就必须冒烟，不能等到 Step 2 才发现假树缺文件
WF_SUITES=r67_tests bash scripts/tests/wf_runtime/full/run_all.sh
# 缺失根容错（G9 的实现前置）：空目录 snapshot 必须退出 0 并标 absent
PYTHONPYCACHEPREFIX=/tmp/wf-unit-pycache /softwares/python/bin/python3 -c \
  "import importlib.util,tempfile; s=importlib.util.spec_from_file_location('sh','scripts/tests/wf_runtime/full/source_hygiene.py'); m=importlib.util.module_from_spec(s); s.loader.exec_module(m); print(m.snapshot(tempfile.mkdtemp()))"
```
- [ ] **可证伪性实证（检查本身）**：手动在 `docs/workflows/wf/payload/lib/wflib/__pycache__/x.pyc`
      放一个空文件 → `source_hygiene.py check` 必须非零退出并列出该路径；删掉后恢复零（记录命令与输出）。
      （**不要**在此步用"去掉 `PYTHONPYCACHEPREFIX`"来演示——本步 pyc 仍被全局禁用，那样不可能变红；
      策略级证伪在 Step 3 做。）
- [ ] 记录 `r64_tests` 删除 P3-1 后的用例数（作为 Step 2 的 `expect` 输入）。

**回滚点**：本 Step 单独可 revert（不改任何判定语义）。

## Step 2 — D2 证据预算（注册表统一）

> 顺序固定：`git mv suites.json units.json` → `plan.py` → `run_all.sh` → `r67_tests.py` → 单元层负例 → 文档。
> 中间态不允许提交（schema 与消费者必须同提交）；**不保留旧名别名/旧键**（同一事实两份真相是遗留源头）。

- [ ] `git mv suites.json units.json`（保留历史）：schema_version +1；顶层 `units` 数组；
      `kind:flow` 的 4 个单元并入；删除顶层 `flows` / `flow_expect` / `extra_expect` / `fallback_representative`；
      每个可计划单元补 `expect`（来自 Step 0/1 实测）与 `fixture`（默认 `template`，`f0` 为 `install`）。
- [ ] `plan.py`：`SUITES_JSON`→`UNITS_JSON`、`load_suites`→`load_units`；字段白名单、`expect` 正整数、
      `kind`/`fixture` 枚举、`manual` 必须带 `notes`、`parallel:false` 必须有 `notes`（沿用）；
      新增 `script` 字段（默认 `<name>.py`；`f0` 显式 `p5_f0.py`），并校验**可计划单元**的 `script`
      在 `HERE/<script>` 存在（`manual` 不校验）；桩生成与 G8 一律读它。
- [ ] `plan.py` 输出契约：`PLAN_UNITS`（**五段** `name:kind:expect:fixture:script`）+ `PLAN_UNITS_PARALLEL` +
      `PLAN_UNITS_SERIAL`（两者互斥且并集为全量）+ `PLAN_ISOLATED_UNITS`（名字列表）；
      删除 `PLAN_FLOWS` / `PLAN_EXTRA` / `PLAN_FLOW_EXPECT` / `PLAN_EXTRA_EXPECT`；
      `plan.json` 直接换成 `units` 结构（条目含 `name/kind/expect/fixture/script`，**不加 deprecated 旧键**）；
      `describe()` 的三行摘要（suites/flows/extra）改为 units 汇总，保留 `计划执行单元: N` 这一行（契约测试依赖它）。
- [ ] `run_all.sh`（Step 2 范围内**只做数据与判定对齐，不改调度**）：删除 `expect_of` 与两张旁路期望表的使用，
      改为按 `kind` 从 `PLAN_UNITS` **派发**到既有的三段执行形状（suite 池 / flow 顺序 / extra），
      每段都用 `--expected <expect>`；`f0` 仍走它自己的 install 前置（本步不动其语义）。
      调度合并留给 Step 4。`isolated_suites`→`isolated_units`，`export WF_ISOLATED_UNITS`
      （`run_one.sh` 的成员判定同步改 env 名；run_all 侧的成员判定辅助函数在 Step 4 随执行逻辑一起删除）。
- [ ] `r67_tests.py`：复制清单与 `FAKE_TREE_COPY` 条目**同提交改名为 `units.json`**，`_manifest["units"]` 同步；
      桩生成改为**按注册表逐可计划单元、以该单元的 `script` 为文件名**（PASS 行数 = `expect`；
      已核实 `verdict` 用 `passed == expected`，多跑同样变红），并删除三处按名字/旁路表生成的旧桩循环
      （`suite|candidate` 名字循环、`extra_expect` 循环、`flow_expect`/`p5_f0.py` 专用写入）。
- [ ] `test_test_runner_plan.py`：同步 `plan.load_units` 的 monkeypatch 与 `PLAN_*` 断言；新增断言
      "每条记录恰为五段、`script` 与注册表一致"（记录格式与 `script` 通路各有一处断言）。
- [ ] `plan.json`：`suites_all` / `flows` / `extra` 三键合并为 `units`（`name/kind/expect/fixture/script`）。
- [ ] `test_run_all_contract.py`：同步 `plan["suites_all"]` → `plan["units"]`，并把 `flow_ran == 2`
      （`--representative`：`f0` + `p5_spec`）与 `suite_ran == 1` 的断言按新注册表复核（值不变是目标，不是假设）。

**验证**
```bash
WF_SUITES="r67_tests r64_tests cp1_tests" bash scripts/tests/wf_runtime/full/run_all.sh   # 子集冒烟
bash scripts/tests/wf_runtime/full/run_all.sh --full --repro green                        # 全量
PYTHONPYCACHEPREFIX=/tmp/wf-unit-pycache /softwares/python/bin/python3 -m unittest \
  discover -s scripts/tests/wf_runtime -t scripts/tests -p 'test_test_runner_plan.py' -v 2>&1 | tail -20
# 慢契约测试（默认被 WF_SLOW_TESTS 跳过，必须显式开，否则 plan/summary 的键漂移无人发现）
WF_SLOW_TESTS=1 PYTHONPYCACHEPREFIX=/tmp/wf-unit-pycache /softwares/python/bin/python3 -m unittest \
  discover -s scripts/tests/wf_runtime -t scripts/tests -p 'test_run_all_contract.py' -v 2>&1 | tail -20
```
- [ ] **负例 1（单元层）**：`execution.verdict()` 给出"`expect` 大于实际用例数 → `ok=False`"。
- [ ] **负例 2（运行器层）**：在 r67 假环境里让某桩少输出一行 `[PASS]` → run_all 整体非零退出，
      错误行指出该单元名与期望/实际计数（记录命令与输出）。
- [ ] **负例 3（plan 层）**：缺 `expect` / `expect: 0` / 未知字段 / `script` 缺失或指向不存在的文件
      → `PlanError` 退出码 2；`manual` 单元缺 `script` **不**报错（不在执行面）。

**回滚点**：本 Step 一个提交；回滚即回到旧 schema（旧 `run_all.sh` 同批回滚）。

## Step 3 — D3 缓存策略（先 pyc，再模板）

### 3.1 字节码缓存

- [ ] `run_all.sh` / `run_one.sh` / `repro/run.sh`：`export PYTHONPYCACHEPREFIX=${WF_PYCACHE:-$RESULTS_DIR/pycache}`，
      删除 `PYTHONDONTWRITEBYTECODE=1`；`summary.json` 记录 `pycache_root`。
- [ ] 交付纪律 T0 命令同步加前缀（`PYTHONPYCACHEPREFIX=... python3 -m unittest discover ...`）。

**验证**
```bash
WF_SUITES=cp1_tests bash scripts/tests/wf_runtime/full/run_all.sh          # 单套件前后对比（预期 13.4→~9）
bash scripts/tests/wf_runtime/full/run_all.sh --full --repro green         # 全量（预期 ~64s）
find docs/workflows/wf/payload scripts/tests -name '__pycache__' | wc -l   # 无新增
```
- [ ] 记录 `pycache_root` 下的文件数与位置；确认 worker 私有 `/tmp` 内也有写入（并行路径可用）。
- [ ] **"改源码立即生效"实证**：临时让某个 wflib 函数抛错 → 下一次 `wf.py` 调用必须按新代码失败
      （证明 pyc 不提供陈旧答案）；复原后转回正常（记录两次输出）。
- [ ] **抽样必须含 isolated-user 路径**：`WF_SUITES=cp3_tests`（`--isolated-user`，HOME 重定向）与
      `WF_SUITES=cp1_tests`（普通）各一次，串行/并行各一次，确认 pyc 落在 `$RESULTS_DIR/pycache`，
      没有落到合成 HOME 或夹具内。
- [ ] **可证伪性实证（策略级）**：临时去掉 `PYTHONPYCACHEPREFIX`（保留其余不变）跑一次 full →
      `SOURCE-TREE-POLLUTED` 必须出现；恢复后重跑必须转绿（记录两次输出）。

### 3.2 模板跨 run 缓存

- [ ] `run_all.sh`：`TEMPLATE_KEY=<digest12>-<pyver>-<deploy>[-<version>-<ref>]`，其中
      `digest12 = wf_release_common.tree_digest(<repo>/docs/workflows/wf/payload)[:12]`
      （内容摘要：相对路径序 + 逐文件 sha256，跳过 `.git`/`__pycache__`/`*.pyc`，**不看 mtime**）。
- [ ] `template_check.py`：新增 `--expect-repoint-min N`（发布与克隆共用）并输出结构化改写计数
      （判定留在该文件一处；bash 只传参与读退出码）；把 `template_check.py` 归入 `FAKE_TREE_COPY`。
- [ ] 发布序列（按 design D3.2，一步不许省）：构建到 `<key>.build` → `template_check <key>.build`
      → `rename(<key>.build → <key>)`（旧条目先挪 `<key>.stale-<pid>`）→
      `template_check <key> --repoint-from <key>.build --expect-repoint-min 1`（重锚定 + 残留 + 改写数）
      → 最后写 `<key>.meta.json`（`root=realpath(<key>)`）。
      **meta 缺失 = 条目无效**（命中时挪 stale 重建）。
- [ ] 命中序列：`meta.root == realpath(条目)`（否则 `TEMPLATE-CACHE-MOVED`）→ `template_check <cached>`
      → `source_hygiene.py check --strict <cached>` → 克隆到 `$FIX` →
      `template_check "$FIX" --repoint-from <meta.root> --expect-repoint-min 1`
      （重锚定 + 残留 + **至少改写 1 个**；0 改写即该单元失败，不继续跑）。
      run 内模板路径同样传 `--expect-repoint-min 1`——两条来源共用一条克隆命令，worker 不新增分支。
- [ ] 失败标签：新增 `prep_rc=5` → `TEMPLATE-REPOINT-MISMATCH`，并入既有 fixture 准备失败标签表
      （Step 4 合并后只剩 run_one 一处；合并前后都要能报出该名字）。
- [ ] 路径规范化：缓存根/`<key>.build` 一律 `realpath`；所有前缀来源只用 `meta.root`，不从当前路径推断。
- [ ] 开关：`--no-template-cache` / `WF_NO_TEMPLATE_CACHE=1`（只关跨 run 缓存）；
      `--no-template` / `WF_NO_TEMPLATE=1` 关闭**整套模板机制**（含缓存，`template_source=none`）。
- [ ] r67 假环境：在既有 `WF_NO_TEMPLATE=1` 之外**显式再钉 `WF_NO_TEMPLATE_CACHE=1`**（防实现漂移把蕴含关系丢掉）。
- [ ] summary 记录夹具来源三键：`template_source`（`run-build`/`cache`/`none`）、`template_cache_hit`、
      `template_cache_key`（无命中时 `null`）；`template_reused` 仍由 `WF_TEMPLATE_READY` 派生
      （命中路径同样置 1，worker 走同一条 clone + `--repoint-from "$WF_TEMPLATE_SOURCE"` 路径，不新增分支）。

**验证**
```bash
bash scripts/tests/wf_runtime/full/run_all.sh --full --repro green   # 第一次：构建；第二次：命中
WF_SUITES=cp2_tests bash scripts/tests/wf_runtime/full/run_all.sh    # 预期 13.4→~6s
```
- [ ] **失效负例（七条，全部要演示）**：① 改 payload **内容**（追加一行）→ 重建；反向：只 `touch` → **仍命中**；
      ② `WF_TEST_PYTHON` 换成另一版本 → 不同 key；③ candidate 换 `--release-version/--release-ref` → 不同 key；
      ④ 删 `<key>.meta.json` → 判无效并重建；⑤ 把条目 `cp -a` 到另一 cache 根（或改 `meta.root`）→
      `TEMPLATE-CACHE-MOVED` → 重建；⑥ 把 `meta.root` 改成另一个存在的绝对路径 → 克隆时改写 0 个 →
      `TEMPLATE-REPOINT-MISMATCH`（该单元失败）；⑦ 往条目里塞一个 pyc → `source_hygiene.py check --strict` 判脏 → 重建
      （strict 是同一实现的第二种模式：绝对判据 0 个 pyc / 0 个 `__pycache__`，不新增扫描器）。
      说明：**"记录指向 `<key>` 自身"不是失败态**——那是正常发布态，克隆时会被正确改写到 `$FIX`；
      要演示"repoint 失效"请用 ⑤（条目搬动 → `meta.root` 与 `realpath(条目)` 不符）与 ⑥（`meta.root` 与记录不一致 →
      克隆时改写 0 个 → `TEMPLATE-REPOINT-MISMATCH`）两个形态。

**回滚点**：两个开关都在；单独回退 3.2 不影响 3.1。

## Step 4 — D4 调度（去掉结构性串行；repro 保持默认串行）

- [ ] `run_one.sh` 成为**唯一**单元执行器，入参是**单参数五段记录** `name:kind:expect:fixture:script`：
      - 一次解析成 `name/kind/expect/fixture/script`，此后**一切路径与键只用 `name`**
        （`.out` / `.timing` / `.test.log(.json)` / `lines` / `NAMESPACE_ERROR_LOG`；夹具路径的私有后缀
        `FIX-<name>-<pid>` **只在进入 ns 时追加**，`WF_NAMESPACE=0` 的宿主域沿用共享 `$FIX`，与今天串行一致）；
      - `script` 只从记录取（`f0` → `p5_f0.py`），**不得拼 `<name>.py`**；
      - `kind` → `execution.py --kind`：`suite|candidate→suite`、`flow|extra→flow`（executor 没有 `extra`/`candidate`，
        映射只在此一处）；`--expected` 一律取记录的 `expect`；
      - `fixture` 分派：`template` 走既有克隆路径；`install` 沿用 `run_f0` 的 reset/`--forbid` 与 install 参数，
        装到 `$LEGACY_FIXTURE_ROOT/<name>` 后执行 `script`；
      - 失败标签并入**同一张** `prep_rc` 表（新增 `5`=`TEMPLATE-REPOINT-MISMATCH`、`6`=`INSTALL-FAILED`），不另立打印分支；
      - 执行域由 `WF_NAMESPACE` 决定：`1`（默认，首段照旧 `exec namespace.py`）/ `0`（串行段：同一 worker，不 exec
        namespace，保持宿主 `/tmp` + 无 `unshare` 的既有语义）；
      - 只写自己的 `<name>.timing`，**不累加** `init_millis`/`suite_millis`；
      - 结果行保持**五列** `name\trc\telapsed_s\tstatus\ttail`（`results_gate.py` 只认五列）。
- [ ] `run_all.sh`：删除 `run_suite` / `run_flow` / `run_f0` / `run_extra` 与它们的计数递增——
      并行段 `xargs` 调用 worker（默认域），串行段 `for rec in $PLAN_UNITS_SERIAL` 逐个调用 worker（`WF_NAMESPACE=0`）；
      `results_gate` **移到两段都结束后执行一次**，`--expected` 传 `PLAN_UNITS` 的**名字全集**（并行 ∪ 串行，含 flow/extra）——
      名字列表由记录第一段派生，不新增第二份名单；`init_millis`/`suite_millis` 在 gate 之后统一读全部 `.timing` 累加；
      `suite_ran` / `flow_ran` 由 `lines` × 注册表 `kind` **一次派生**（`suite|candidate`→`suite_ran`，`flow|extra`→`flow_ran`），
      不再在任何执行分支里递增；`KNOWN_LEGACY` 账目遍历同一名字全集。
      **repro 默认仍在主池之后顺序执行**（决策 #3），新增显式开关 `--repro-concurrent`（不进默认路径）。
- [ ] `r67_tests.py` 的 `run_one.sh` 桩**按新入参契约重写**（旧桩假设 `$1`=套件名）：解析五段记录、按 `script` 找桩文件、
      按 `kind` 映射 `--kind`、按 `fixture` 分派（假环境的 `f0` 走 install 桩）、保持五列输出；
      同时把假环境的模板开关按 Step 3.2 钉死（`WF_NO_TEMPLATE=1` + `WF_NO_TEMPLATE_CACHE=1`）。
      桩文件全集在 Step 2 已按 `script` 生成，本步只改调用契约。
- [ ] `plan.py`：`WF_TOTAL_JOBS` → 默认串行时全部给主池；`--repro-concurrent` 时按 5/3 推导
      `PLAN_JOBS` / `PLAN_REPRO_JOBS`（公式只存在 plan.py 一处；`--serial` 为 1/1）。
- [ ] `summary.json`：新增 `pool_seconds` / `repro_seconds` / `startup_seconds` / `template_source` /
      `template_cache_hit` / `template_cache_key` / `pycache_root` / `budget` 块，
      并记录 `repro_concurrent: false|true`，schema_version +1。
- [ ] **既有键连续性（flows 入池后不得改义）**：`suite_ran` = `kind=suite` 数、`flow_ran` = `kind=flow/extra` 数
      （`--representative` 仍为 2：`f0` + `p5_spec`）、`repro_ran` 不变、`units_total` = 三者之和；
      `template_reused` 表示"本次 run 内共用同一夹具源"（run 内构建或缓存条目都算，命中路径同样为 true），
      跨 run 命中由 `template_cache_hit` / `template_source` 单独表达；
      `init_seconds` / `suite_seconds` 的口径同批由"套件累计"扩为"**全部执行单元**累计"（flow/extra 现在也写
      `.timing`），`timing_note` 措辞同步——登记为明确变更，不静默漂移。
- [ ] `test_run_all_contract.py`：复核 `flow_ran == 2` / `suite_ran == 1` / `flow_ran == 0` 与
      `template_reused is True` 四处断言在新记账下仍成立（**断言值不变**；只允许同步
      `template_reused` 那一处注释说明"共享夹具源"的新口径。若值不得不变，先停下改设计，不擅改断言）。

**验证**
```bash
bash scripts/tests/wf_runtime/full/run_all.sh --full --repro green              # 默认（串行 repro）两次采样
bash scripts/tests/wf_runtime/full/run_all.sh --full --repro green --serial     # 对拍基线
bash scripts/tests/wf_runtime/full/run_all.sh --representative --repro green     # 预收口
bash scripts/tests/wf_runtime/full/run_all.sh --full --repro green --repro-concurrent  # 开关抽样 1 次（仅记录，不入默认）
WF_SUITES=r67_tests bash scripts/tests/wf_runtime/full/run_all.sh   # 派发契约变了：假环境的 run_one 桩必须仍绿
WF_SLOW_TESTS=1 PYTHONPYCACHEPREFIX=/tmp/wf-unit-pycache /softwares/python/bin/python3 -m unittest \
  discover -s scripts/tests/wf_runtime -t scripts/tests -p 'test_run_all_contract.py' -v 2>&1 | tail -20
```
- [ ] **等价性对拍**：默认路径两份结果目录的 `lines`（单元名/rc/status，**含原 flow/extra 单元**）、
      `repro/*.json`（mode/green/red/verified）逐项相等（运行期 id 除外）；
      **计数三分量分开核对**（flow/extra 已无独立"流程行"，但对拍对象不是"四键都等于行数"）：
      `lines` 行数 == `suite_ran + flow_ran`；`units_total == suite_ran + flow_ran + repro_ran`；
      `repro_ran` == repro 汇总的 `REPRO_TOTAL`（repro 用例不写 `lines`，**不得**与行数比较）。
- [ ] **记录/名字边界实证**：`lines` 里 flow/extra 单元以 `name` 出现（不是记录串）；`results_gate` 的
      `--expected` 覆盖 `PLAN_UNITS` 全集——用一个"故意漏跑串行单元"的构造（临时把某串行单元从 gate 名单外运行）
      确认 gate 会报 `MISSING-RESULTS`，证明串行段确实被覆盖。
- [ ] **串行域实证**：`--serial` 下确认 worker 是 `WF_NAMESPACE=0`（无 `unshare`，宿主 `/tmp`），
      与默认并行路径的夹具路径形态各留一条日志证据；两域结果逐项相等即 AC1 的对拍。
- [ ] `f0` 迁入 worker 后 representative 与 full 各跑一次，确认安装+自举闭环绿
      （这是 f0 从宿主迁入私有 tmpfs 的唯一验收面）。
- [ ] 开关路径同样跑一次等价性对拍（结论与默认路径一致），并把分段的 `pool_seconds`/`repro_seconds`
      与总墙钟记录进验证记录；**默认配置不因开关实验而改变**。

**回滚点**：`--repro-concurrent` 是新增开关，默认不启用；主池改动与 Step 2 的注册表一并回退。

## Step 5 — D5 闸门与文档

- [ ] 新增 `test_runner_hygiene.py`：G1（`/tmp` 注入零命中）、G2（pyc 策略）、G3（`.gitignore`）、
      G8（按 design 写死的扫描口径解析 `run_all.sh` 的静态引用：每个命中 ∈ COPY∪STUB∪SPECIAL∪注册表 script，
      且三桶条目必须存在；基线 = 实测 11 组）、
      G9（`source_hygiene` 对缺失根退出 0 且输出含 `absent`）。
- [ ] 新增 `test_runner_budgets.py`：G5（`wf.py status` **5 次中位数 < 500ms**，`setUpClass` 建一次夹具，
      `WF_PERF_GUARD=0` 可关并在断言消息里报实测值）。阈值只在 PRD R5.4 定义一次，此处与 design D5-G5 同值，
      实现时不得再引入第二个数字。
- [ ] `full/README.md`：并发与子集、缓存轮转、性能、解释器契约四段同步；明确四件事：
      模板缓存与 pyc 策略、注册表 `expect` 契约、**repro 默认串行且并发仅经 `--repro-concurrent`**、
      记录与名字的边界（`PLAN_UNITS` 五段记录 / 其它消费点只用名字）+ `WF_ISOLATED_UNITS` 的改名。
- [ ] `wf-delivery-discipline.md` §7/§12：T0 命令加 pycache 前缀；T1/T2 表格与时间预算；超时余量口径；
      `PLAN_ISOLATED_SUITES` → `PLAN_ISOLATED_UNITS` / `WF_ISOLATED_UNITS` 的引用同步（§7 现有那一句要改）。
- [ ] `AGENTS.md` 的常用命令若受影响同步（只改确需改的行）。

> **闸门 → 落点索引**（避免"设计里有、计划里没落点"）：G1/G2/G3/G8/G9 在本步新增的两个测试文件；
> G4（注册表完整性）在 Step 2 的 `load_units` 校验；G6（预算可见）在 Step 4 的 summary `budget` 块；
> G7（源树卫生）在 Step 1 的 snapshot/check。三处都不是"另加机制"，是同一实现的消费点。

**验证**
```bash
PYTHONPYCACHEPREFIX=/tmp/wf-unit-pycache /softwares/python/bin/python3 -m unittest discover -s scripts/tests -t .
/softwares/python/bin/python3 scripts/validate-wf-design.py
/softwares/python/bin/python3 scripts/check-doc-refs.py
./scripts/validate-skills.sh
```

## Step 6 — 收口验证与报告

- [ ] full 并行两次采样（AC1：硬性 ≤65s = 相对基线 −30%，目标 ≤60s；**默认串行 repro**）、
      full 串行一次、representative 一次；三份 summary 存档进任务目录；
      另存一份 `--repro-concurrent` 抽样 summary 作为对照（不改默认）。
- [ ] 若并行落在 60–65s：写出剩余差距归因（模板命中/未命中、flows 段实测、repro 段实测）与处置结论，
      不允许只贴一个数字。
- [ ] 串并行等价性逐项对拍；`KNOWN_LEGACY` 仍为空（不是"有债但没报"）。
- [ ] 8 并发下最慢单元耗时与 `WF_COMMAND_TIMEOUT`(180s) 余量、repro 最慢用例与 `WF_REPRO_TIMEOUT`(120s) 余量。
- [ ] `WF_SLOW_TESTS=1` 契约回归跑一次并留证（`test_run_all_contract.py` 全绿：plan 键、summary 键、
      取消清理、模板禁用/复用四条）。
- [ ] **证据归档（逐项核对"命令 + 关键输出片段"是否齐全，缺一即视为未收口）**：
      AC2 证据：plan 层五类负例（`expect` 缺失/非正整数、`script` 缺失、`script` 文件不存在、未知字段、
      非法 `kind`/`fixture`）+ 单元层"用例数少 1 → 红" + 运行器层"少一行 `[PASS]` → 红" +
      "漏跑一个串行段单元 → `MISSING-RESULTS`" + 记录五段断言 + r67 桩按 `script` 命名的证据；
      AC5 七条失效实证（① 内容变更 + `touch` 反向 ② 解释器 ③ candidate 身份 ④ 无 meta ⑤ 搬动
      ⑥ `meta.root` 与记录不一致（0 改写）⑦ 脏条目）与 pyc"改源码立即生效"实证；
      AC3 双重证伪（Step 1 植入 pyc → 红；Step 3 去掉缓存策略 → 自然产生 pyc → 红）；
      AC1 两次并行 summary + 串行对拍文件。
- [ ] AC3 绝对判据复核：
      `find docs/workflows/wf scripts/tests \( -name '*.pyc' -o -name '__pycache__' \) | wc -l` = 0。
- [ ] 用 `trellis-update-spec` 把"运行器三份契约（注册表/pyc 策略/并发预算）+ 预算口径"写进
      `.trellis/spec/docs/wf-delivery-discipline.md` 与相关 spec 索引。
- [ ] 复核最终 diff（含 untracked/staged），确认无计划外改动、无遗留 TODO；按 Step 提交。
- [ ] 向用户报告：提速幅度归因、被替换的证据机制、仍不做的事项（指向"不做清单"）。

## 完成定义（与 PRD 的 AC 一一对应）

| AC | 由哪个 Step 产出 | 证据形态 |
|---|---|---|
| AC1 提速 | Step 3 / Step 4 / Step 6 | 两次 summary + 串并对拍文件 |
| AC2 证据预算 | Step 2 | plan 层五类负例 + 单元层/运行器层负例 + 串行段 `MISSING-RESULTS` 实证 + 五段记录断言 |
| AC3 卫生 | Step 1 / Step 5 | grep 计数、check-ignore、source_hygiene 快照、G1–G3/G8/G9 测试（G4/G6/G7 见落点索引） |
| AC4 不回归 | Step 6 | full 149 单元 0 失败、r67 绿、`WF_SLOW_TESTS=1` 契约回归绿、对拍相等、超时余量 |
| AC5 缓存失效 | Step 3 | 七条失效实证（内容/解释器/候选身份/无 meta/搬动/`meta.root` 与记录不一致/脏条目）+ `touch` 不失效反向 + pyc 生效实证 |
| AC6 无遗留 | Step 5 / Step 6 | 文档 diff、schema 版本、任务目录里的"不做清单" |
