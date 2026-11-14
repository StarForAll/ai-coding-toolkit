# wf 测试运行器第二轮：提速与证据完整性契约

## 背景 / 基线（实测，2026-11-14 同机 i7-10875H / 16 线程）

上一轮（`11-13-wf-runner-speed-quality`）已把 full 从 204s 收到 94s。本轮分析（只读测量，无代码改动）
在现有实现上确认了剩余可回收成本与四类证据完整性问题：

| 指标 | 现状实测 | 证据来源 |
|---|---|---|
| full 并行（149 单元 = 59 套件 / 741 用例 + 85 repro + 4 流程 + r72） | **92.9s / 94.5s**（两次采样） | `~/.cache/wf-test-run/run-3290992, run-3014253` |
| full 串行 | 274.1s | `run-3077220` |
| 单套件定向 run | 13.4s（cp2）/ 4.6s（r67）；固定开销占 42% | `run-3265836` + 独立计时 |
| representative | 48.1s | `run-2987414` |
| T0 单元层 | 858 用例 / 4.84s | 本地实跑 |
| 分层墙钟 | 启动 1.4s + 模板 3.7s + 套件 41.5s + flows/extra 19.3s（并行仅 2.7×）+ repro 25.7s | 结果目录 mtime 时间线 |
| CLI 往返 | **1278 次** `wf.py` 子进程，合计 372s，**均值 291ms** | `WF_TEST_PYTHON` 计数仪器 |
| 字节码缓存 | 关（`run_all.sh:42`）；开启后同套件 **15.64→10.10s / 14.95→10.15s（−35%）** | 同源夹具 A/B ×2 |
| flows 并行度 | 3 个 p5 flow 串行 13.89s → 3 并发 **5.76s（2.4×）** | 独立并发实测 |
| 夹具基准态构建 | 2.73s（`wf_fixture.sh` 0.27s + `f1_init` 2.46s） | 独立计时 |

## 目标

1. **提速**：把 full 并行墙钟从 ~93s 降到 **≤65s（硬性，相对基线 −30%）/ 目标 50–60s**，
   单套件定向 run 从 13.4s 降到 **≤7s（目标 5.8s）**，且提速来源可归因、串并行等价性逐项对拍不变。
2. **证据完整性**：让"少跑用例 / 自证断言 / 卫生假绿"这类静默退化在机械层面不可能发生。
3. **卫生与可移植**：测试链路不再依赖本机全局配置、不再有 `/tmp` 导入劫持口、不再把 pyc 写进仓库或夹具。
4. **不制造新问题、不遗留旧问题**：每项必须有"注入回归即红"的证明；本轮明确不做的项目要登记理由与触发条件。

## 任务形态（为什么是一个任务而不是父子任务树）

本轮四组交付（卫生 / 证据预算 / 缓存策略 / 调度）**共享同一批文件与同一次等价性证明**：
`run_all.sh`、`run_one.sh`、`plan.py`、`execution.py`、注册表（`suites.json` → `units.json`）、`r67_tests.py` 假环境。
拆成三个子任务会要求同一改动面被三次改动、三次对拍、三次回归 r67，反而提高"遗留半成品"的风险。
因此采用**单任务 + 有序步骤**（顺序理由写在 `implement.md`），并在 PRD 中把四组交付分别写成可独立验收的 AC。

## 审查意见处置（2026-11-14，第二轮独立审查）

外部审查共 7 条意见 + 1 条"核实后不构成问题"。逐条判定与处置如下（**不采信的也要写明理由**，
避免"看起来都改了"但实际留下争议）：

| # | 审查意见 | 判定 | 处置 |
|---|---|---|---|
| 1 | D3.2 模板缓存命中路径缺绝对路径重锚定（repoint），会留下指向共享缓存/上一 run 暂存目录的路径 | **成立（P1）** | 采纳：R3.2 补"发布序列 + 克隆后 `--repoint-from <缓存路径>` + 记录不得残留共享缓存路径"三条不变量（第二轮口径），`template_check --repoint-from` 既做重锚定也做残留检查（`template_check.py` 的 `check(leak_from=...)`）。**（第三轮进一步收紧为四条不变量，见下表第 1、2 条）** |
| 2 | "临时目录 + `os.replace`"对目录条目不可行（目标非空 → `ENOTEMPTY`） | **成立（P1）** | 采纳：不再宣称目录级原子覆盖；发布改为"构建到 `<key>.build` → 校验 → rename 到最终条目（旧条目先挪 stale）→ 按最终路径 `--repoint-from <key>.build` 重锚定并查残留 → 复核 → 最后写 `meta`"，窗口由"meta 最后写 + 先挪走再发布 + 全局 flock"兜底 |
| 3 | G5 阈值出现两个数（3–5× 与 500ms） | **成立（P2）** | 采纳：统一为 **中位数 < 500ms（≈8× 实测 62ms）**，理由写入 design；PRD 的"3–5×"删除 |
| 4 | AC1 硬墙钟阈值与 G6"不对墙钟硬失败"自相矛盾；且 61–64s 会按字面失败 | **成立（P2）** | 采纳并区分口径：G6 约束的是**运行期门禁**（任意机器），AC1 是**同机同基线的验收证据**；AC1 硬性改为"≤65s（相对基线 −30%）+ 串并等价"，60s 降为目标并在 60–65s 区间要求归因与处置结论 |
| 5 | Step 1 的"可证伪性实证"在该时点不可能变红（Step 1 时 pyc 仍被全局禁用） | **成立（P3）** | 采纳：拆成两次证伪——Step 1 用**植入 pyc** 证明检查有效；Step 3 用**去掉缓存策略让 pyc 自然产生**证明策略受约束。design D1.4 同步改写 |
| 6 | Step 1 的 `compileall` 自己会写 pyc，与卫生目标冲突；存量污染被"只判新增"豁免 | **成立（P3）** | 采纳：`compileall` 带 `PYTHONPYCACHEPREFIX`；Step 1 增加"清存量 → 建快照"；AC3 用**绝对判据**（`find` 为空），运行期检查仍只对新增失败（存量以警告 + 可操作清理命令呈现） |
| 7 | Step 3.1 的写入位置抽样没覆盖 `--isolated-user` 单元 | **成立（P4）** | 采纳：抽样必须含 `cp3_tests`（isolated_user）与一个普通套件，串行/并行各一次 |
| — | r67 桩"PASS 行数 = expect"是否与 verdict 的 `saved N / M` 解析冲突 | **不成立（核实）** | `execution.py:170-172` 的判定是 `ok and passed == expected`（数 PASS 行），多跑同样变红；保持原设计 |

**本轮自查追加的两项**（审查未提，但属同一类"打补丁会留下"的问题）：

| # | 自查发现 | 处置 |
|---|---|---|
| S1 | 注册表把 flows 并入 `suites` 数组后，"suites.json / suites 键"名与内容不符（四类执行单元都塞在 `suites` 里） | 采纳：注册表改名 `units.json` + 顶层键 `units`，文件名与内容一致；同步 `plan.py`、`run_all.sh`、`r67_tests.py`、`test_test_runner_plan.py`、README、交付纪律（一次性改完，不保留旧名别名） |
| S2 | design 原写"`plan.json` 保留旧键一个版本"——那会让同一事实短期存在两份真相 | 采纳：不保留 deprecated 键，`plan.json` 直接换成 `units` 结构，消费者同批改 |

## 审查意见处置（第三轮，2026-11-14）

第二轮修正后又一轮独立审查，共 4 条意见；逐条判定如下。

| # | 审查意见 | 判定 | 处置 |
|---|---|---|---|
| 1 | 发布序列步骤 4 的产物状态（记录指向 `<key>` 本身）正是负例⑤判"必须失败"的状态——负例自相矛盾；"至少改写 1 个文件"只约束发布时，没延伸到克隆时 | **成立（P1）** | 采纳：负例⑤重写为两条可演示的失败态——⑤a 条目被搬动（`meta.root` ≠ 当前 `realpath`）→ 命中即失效重建；⑤b 克隆时 repoint 改写数与发布记录不符 → 该单元失败（不继续）。克隆时把"改写计数相等"变成硬判据（`template_check --expect-repoint N`；**第五轮已收敛为 `--expect-repoint-min 1`**） |
| 2 | `WF_RESULTS_CACHE` 可注入/可移动：记录指向旧 cache 根时，命中与克隆全链路都发现不了（静默串味） | **成立（P1）** | 采纳：条目 meta 记录 **发布根 `root` + 自指改写数 `self_ref_files`**（**第五轮已把「精确计数」收敛为 `--expect-repoint-min 1`，见下表第 2 条**）；命中要求 `meta.root == realpath(条目)`（换根/搬动即失效）；克隆用 `meta.root` 作为**精确** leak 前缀并要求改写数相等——前缀不再靠猜，"0 改写"不再可能被静默放过。串味防线补上"旧 cache 根路径"这一类 |
| 3 | `<payload_digest12>` 口径未定义；负例①"触碰 payload"在内容摘要下不会重建 | **成立（P2）** | 采纳：口径写死为现成的 `wf_release_common.tree_digest(docs/workflows/wf/payload)`（相对路径序 + 逐文件 sha256，跳过 `.git`/`__pycache__`/`*.pyc`，**不看 mtime**），取 12 位 hex；负例①改"改内容（追加一行）→ 重建"，并加反向断言"只 `touch` → 仍命中" |
| 4 | `test_run_all_contract.py` 在设计修改范围内却无任何 Step 覆盖；它是 `flow_ran` 的唯一外部消费者，且 `WF_SLOW_TESTS=1` 门控使默认验证跳过它 | **成立（P2）** | 采纳：D4.3 增加既有 summary 键的**连续性承诺**；Step 2/4 增加该测试的更新条目；Step 2/4/6 的验证命令显式开 `WF_SLOW_TESTS=1` |

**本轮自查追加 2 项**：

| # | 自查发现 | 处置 |
|---|---|---|
| S3 | `test_run_all_contract.py` 还断言 `plan["suites_all"]` 与 `plan["mode"]`；注册表/plan.json 迁移会打断它 | 在 Step 2 同步更新（`suites_all` → `units`），并靠 `WF_SLOW_TESTS=1` 验证 |
| S4 | `summary.template_reused` 现有语义是"run 内模板复用"，既有契约测试断言它为 True；若把跨 run 命中混进这个键，语义漂移会静默改掉既有断言的含意 | **第四轮收敛口径**：`template_reused` 放宽为"本次 run 内单元共用同一夹具源"（run 内构建或缓存条目都算，`WF_TEMPLATE_READY` 两条路径都置位），另加 `template_source ∈ {run-build,cache,none}` 与 `template_cache_hit` 把两种来源分开；契约测试断言值不变，只同步一行注释（放宽是**明确变更**，不静默） |

## 审查意见处置（第五轮，2026-11-14）

| # | 审查意见 | 判定 | 处置 |
|---|---|---|---|
| 1 | r67 同步只排在 Step 2，而 Step 1/3/4 会先打断它；Step 1 的破坏在 Step 1 验证里发现不了 | **成立（P1）** | 采纳（做成单一来源而非"记得同步"；**第六轮已改为三桶分类，见下表第 1 条**）：`plan.py` 新增 `RUNNER_HELPERS` 作为运行器 helper 清单，r67 读它复制；新增机械门槛 G8（扫 `run_all.sh` 的 `"$HERE/<name>"` 调用点 ⊆ 清单）。Step 1 增加 source_hygiene 的缺失根容错（G9）与 r67 冒烟；Step 3 增加模板缓存开关在 r67 假环境的显式钉死；Step 4 增加 run_one 桩按新调用契约重写 |
| 2 | D3.3"不新增分支"与"克隆时计数硬判据"矛盾：`run_one` 拿不到 `self_ref_files`；`--no-template-cache` 退路下计数契约未定义 | **成立（P1）** | 采纳（**删机制**而不是加导出）：精确计数与 `meta.self_ref_files` 全部取消，统一为 `--expect-repoint-min 1`（发布与克隆、run 内模板与缓存条目同一判据）。依据实测：`install.py:431-442` 与 `wf-dev-deploy.py:169-188` 都会把 `abspath(target)` 写进 `recovery.md`，dev/candidate 两条部署路径都有 ≥1 自指记录，"0 改写"永远是异常 |

**本轮自查追加 2 项**：

| # | 自查发现 | 处置 |
|---|---|---|
| S5 | `WF_NO_TEMPLATE=1`（r67 假树在用的开关）与新的模板缓存之间没有定义过关系；若缓存不被它关闭，假树会走进发布序列并失败 | 写死开关语义：`--no-template` = 关闭整套模板机制（含缓存），`--no-template-cache` = 只关跨 run 缓存；r67 仍显式再钉 `WF_NO_TEMPLATE_CACHE=1` 防实现漂移 |
| S6 | `source_hygiene` 若在"根不存在"时崩溃，会让 r67 假树与 `--dry-run` 这类场景红掉——正是"引入新问题"的形态 | 缺失根按空集合处理并输出 `absent`；配 G9 单元断言 |

## 审查意见处置（第六轮，2026-11-14）

| # | 审查意见 | 判定 | 处置 |
|---|---|---|---|
| 1 | G8 按字面不可满足（`RUNNER_HELPERS` 只有 7 项，但 run_all 有 11 组静态 `"$HERE/..."` 引用）；且"r67 按清单复制真实文件"与"r67 必须用桩"互相矛盾；扫描口径未写死 | **成立（P1）** | 采纳（**改分类，不是把清单补全**）：`plan.py` 提供**三桶假树清单** `FAKE_TREE_COPY`（纯工具，复制）/ `FAKE_TREE_STUB`（`run_one.sh`/`wf_fixture.sh`/`f1_init.py`，**必须桩化**）/ `FAKE_TREE_SPECIAL`（`run_all.sh`、`repro/run.sh`；**第七轮回读时把 `repro/run.sh` 改归 STUB——r67 实际写的是 `REPRO_*` 桩**）；G8 改为"每个静态引用必须被归类 ∪ 注册表 script，且三桶条目必须存在"；扫描口径写死（只认双引号静态形态，含子目录与带数字文件名，跳过含 `$` 或 `..` 的引用），并登记今天 11 组实测引用作为基线 |

**本轮自查追加 1 项**：

| # | 自查发现 | 处置 |
|---|---|---|
| S7 | 注册表 `name` 与脚本名不等价：`f0` 的执行脚本是 `p5_f0.py`。这既让"按名生成桩"不成立，也让 G8 的"注册表 script"这一项无定义 | 注册表增加 `script` 字段（默认 `<name>.py`，`f0` 为 `p5_f0.py`）；桩生成与 G8 一律读 `script`，不再用名字拼路径 |

## 审查意见处置（第七轮，2026-11-14）

S7 只落到注册表字段与桩生成，执行路径上的落点此前仍是空的；本轮把这一条修到"可从 plan 一路追到 worker"，
并补上同一类契约缺口（记录编码、`kind` 枚举、名字边界、install 失败态、串行执行域、环境变量命名）。

| # | 审查意见 | 判定 | 处置 |
|---|---|---|---|
| 1 | `script` 没有通路到任何执行消费点：`PLAN_UNITS` 与 worker 记录都是四段，而 install 分支要求"执行注册表 script（`f0` → `p5_f0.py`）"；Step 4 删掉 `run_f0` 后 `p5_f0.py` 失去来源（今天靠 `run_all.sh:515` 硬编码兜着），r67 桩生成同样拿不到 script | **成立（P1）** | 记录编码写死为五段 `name:kind:expect:fixture:script`（D2.2 示例 + "必须满足" + 兼容段 + Step 2 + Step 4 同批）；plan 校验可计划单元的 `script` 在 `HERE/<script>` 存在；r67 按 `script` 全量生成桩并删掉三处按名字/旁路表的旧桩循环 |
| 2 | Step 1 引入 `FAKE_TREE_COPY` 时注册表还叫 `suites.json`，但桶表按终态写 `units.json`：照字面在 Step 1 写会让 r67 复制循环当场 file-not-found；G8 的三桶存在性检查要到 Step 5 才兜底 | **成立（P2）** | 三桶表与 Step 1 写明"本步桶内注册表条目 = `suites.json`，Step 2 与 `git mv` 同提交改成 `units.json`"；过渡期由 Step 1/2 的 r67 冒烟守卫 |
| 3 | （本轮回读补审）`kind` 与 `execution.py --kind` 不是同一枚举：记录里是 `suite/flow/extra/candidate`，executor 只接受 `raw/suite/flow/steps/repro`；D4.1 只写"按 kind 传 `--kind`"，`extra`/`candidate` 会让 argparse 直接失败 | **成立** | D4.1 写死映射（`suite`/`candidate` → `suite`、`flow`/`extra` → `flow`），映射只存在于 worker 一处，plan 不下发 `--kind` |
| 4 | （补审）记录令牌与"名字键"边界未定义：`results_gate --expected`、`.timing` 汇总、`lines`、`KNOWN_LEGACY` 账目都按名字；把记录原样传给 gate 会让所有单元判 missing。另外串行段今天不经过 gate，合并后若沿用"池内 gate"会把串行行判成 unexpected | **成立** | D4.1 增加"名字边界"与"完整性覆盖"两行：名字一律由记录第一段派生；gate 移到两段都结束后一次性覆盖 `PLAN_UNITS` 全集（串行段由此获得此前没有的完整性判定）；计数由 `lines` × 注册表 `kind` 一次派生 |
| 5 | （补审）install 分支的失败态没有标签：今天 `INSTALL-FAILED` 是 `run_f0` 自己的打印分支，D4.1 的 `prep_rc` 表只到 5 | **成立** | 并入同一张表：`prep_rc=6` → `INSTALL-FAILED`（不另立打印分支）；reset 的 `--forbid` 与 install 参数沿用 `run_f0` |
| 6 | （补审）`--serial` 的执行域未定义：今天的串行段是"宿主 `/tmp` + 无 `unshare`"，正是 AC1 对拍的对照面；若合并后串行也走 `namespace.py`，对拍退化成 ns-vs-ns | **成立** | D4.1 写死 `WF_NAMESPACE=1/0` 两个执行域（同一 worker、同一条执行/结果行代码）；串行段 = `WF_NAMESPACE=0` 逐个调用 worker |
| 7 | （补审）`WF_ISOLATED_SUITES` 与 `PLAN_ISOLATED_UNITS` 两套名字并存于同一事实，正是 S1/S2 判定要消灭的形态 | **成立** | 同批改名 `PLAN_ISOLATED_UNITS` / `WF_ISOLATED_UNITS`；run_all 的成员判定辅助函数在 Step 4 随单元执行逻辑一起删除（成员判定只剩 worker 一处）；README/交付纪律在 Step 5 同步 |

## 决策记录（用户拍板，2026-11-14）

以下六项由用户逐条拍板，已回写进 `design.md` / `implement.md` 的对应小节；后续若与此表冲突，以此表为准。

| # | 议题 | 决定 | 对本计划的影响 |
|---|---|---|---|
| 1 | 任务形态 | **单任务 + 有序步骤**（不拆父子任务） | 保持；四组交付共享同一改动面与同一次等价性证明 |
| 2 | 模板跨 run 缓存（原 O4） | **批准** | R3.2/D3.2 保留，按"digest + 解释器 + 发行身份 key、命中校验 + 克隆后 repoint 残留检查、发布用 `meta` 最后写（不宣称目录级原子覆盖）、开关退路、失效与半成品负例"实施 |
| 3 | repro 与主池并发 | **默认串行，只保留开关**（收益 3–6s 且存在抖动风险） | R4.2 改为"默认串行 + `--repro-concurrent` 显式开关"；AC1 的收益只来自 pyc、flows 入池、模板缓存，不再计入 repro 并发 |
| 4 | 删除 `r64` 的 P3-1 用例 | **同意删除**（恒真断言，且测试会改源树） | D1.4 按设计执行；`r64_tests` 的 `expect` 随之 −1，并与用例变更同提交 |
| 5 | 预算门槛 | **只报告不硬失败** | R5.5/D5-G6 保持；硬约束只放在与机器无关的量上 |
| 6 | 不做清单 | **认可** | 五项排除项原样保留，收口时指向后续归属 |

## 需求

### R1（卫生与可移植，行为零变化）

- R1.1 删除套件/流程脚本里 61 处 `sys.path.insert(0, "/tmp")`：脚本目录本来就在 `sys.path[0]`，
  该行只起"把 `/tmp` 提到最高优先级"的作用。实测可被 `/tmp/wfdrive.py` 劫持（已在本次分析中复现并复原）。
- R1.2 仓库级 `.gitignore` 覆盖 `__pycache__/` 与 `*.pyc`；当前 `scripts/tests/**/__pycache__`
  只因本机全局 `excludesFile` 才不出现在 `git status`（`git check-ignore` 指向 `~/.config` 外的全局文件）。
- R1.3 删除注册表死字段 `fallback_representative`（当前在 `suites.json:773`，全库仅此一处、代码零引用；Step 2 迁移到 `units.json` 时一并删除）。
- R1.4 用**可证伪**的运行期卫生检查替换 `r64_tests.py:90-99` 的 P3-1（先 `rmtree` 再断言"没有" = 恒真，
  且测试在改作者源树）：改为 run_all 在运行前后对 `docs/workflows/wf` 做"无 pyc / 无 `__pycache__`"快照对拍，
  与既有 `PRODUCT-TREE-CHANGED` 同机制。

### R2（证据预算：用例数不可静默缩水）

- R2.1 每个可计划执行单元（suite / flow / extra / candidate）在注册表声明 `expect`（用例数）。
- R2.2 `plan.py` 校验 `expect` 存在且为正整数（含负例）；`run_all.sh` 对**所有** kind 统一下发 `--expected`；
  **完整性判定一次覆盖全部计划单元**（含 flow/extra 与串行段），不留未覆盖单元——串行段今天不经过
  `results_gate`，合并后一并纳入（合并前只覆盖并行子集）。
  现状：`execution.py:146-160` 对 suite 只校验"套件汇总行内部自洽"，`run_all.sh` 调套件时**不传** `--expected`，
  因此删掉用例后 `saved 10 / 10` 依然绿灯；flows/extra 已有该保护（`flow_expect`/`extra_expect`）。
- R2.2b 记录编码（`name:kind:expect:fixture:script`）与执行脚本来源只有一处：plan 产出记录、worker 按记录执行，
  `script` 不得按 `<name>.py` 拼（`f0` = `p5_f0.py`）。
- R2.3 注册表统一：`flow_expect` / `extra_expect` / 顶层 `flows` 名单全部并入条目自身
  （`expect` + `fixture` + `kind`），删除三处旁路（同一事实只留一处真相）；
  文件名与内容对齐为 `units.json`（顶层 `units` 数组），不保留旧名别名。
- R2.4 预算必须**可证伪**：给出"删掉一个用例 → runner 变红"的实证（runner 层负例，不只在单元层）。

### R3（缓存策略：一处策略，不落源树）

- R3.1 字节码缓存重定向：runner 用 `PYTHONPYCACHEPREFIX`（可注入、随结果目录轮转），
  **不再**用 `PYTHONDONTWRITEBYTECODE=1`；pyc 不得落入仓库源树、不得落入夹具内（`.wf/lib` 未跟踪，
  写进去会成为 `git ls-files --others` 可见的脏路径）。
- R3.2 模板跨 run 缓存：`key = <digest12>-<py_maj.min>-<deploy>[-<version>-<ref>]`，`digest` 取
  `wf_release_common.tree_digest(docs/workflows/wf/payload)` 的前 12 位（内容摘要，不看 mtime）；
  必须满足四条不变量（缺一条即为设计缺陷，见 design D3.2）：
  1. **发布序列**：构建到 `<key>.build` → `template_check` → rename 到最终条目（旧条目先 rename 到 stale）
     → 按最终路径 `--repoint-from <key>.build`（重锚定 + 残留检查；必须至少改写 1 个文件，否则判无效）
     → 复核 → 最后写 `meta`（**meta 缺失 = 条目无效**）。**不得宣称目录级 `os.replace` 原子覆盖**
     （非空目标会 `ENOTEMPTY`），窗口由"meta 最后写 + 先挪走再发布 + 全局 flock"兜底；
  2. **命中校验**：`meta.root == realpath(条目)`（条目被搬动/换 cache 根即失效重建）+ `template_check <cached>`
     （空态/安装身份/version/ref）+ **严格卫生检查**（条目内不得有任何 `__pycache__`/`*.pyc`，复用
     `source_hygiene.py` strict 模式）；
  3. **克隆校验**：以 `meta.root`（**精确**的发布根，不靠猜）为 leak 前缀执行
     `template_check "$FIX" --repoint-from <meta.root> --expect-repoint-min 1`
     ——重锚定、残留检查、"至少改写 1 个"三者一次判完；**改写 0 个 → 该单元失败**（不继续跑）。
     run 内模板（无缓存）与缓存条目**共用同一条命令与同一判据**，worker 不需要知道来源类型。
  4. **不得串味**：克隆后的夹具里，`.wf/**` 记录不得残留四类路径：共享缓存根、旧 cache 根、
     上一 run 的 `$RESULTS_DIR`、构建残留 `.build-*`。
  未命中则构建；提供关闭开关。
- R3.3 失效证明（与 AC5 同一张清单，七条）：① 改 payload **内容** → 重建（反向：只 `touch` → 仍命中）
  ② 换解释器版本 ③ candidate 换 version·ref ④ 半成品（无 meta）⑤ 条目被搬动（`meta.root` 不符）
  ⑥ `meta.root` 与记录不一致（克隆时改写 0 个 → `TEMPLATE-REPOINT-MISMATCH`）⑦ 条目内混入 pyc。
  **pyc 不自定义失效**（交给解释器按 mtime/size 判定），但必须证明"改源码立即生效"：
  临时改动一个 wflib 模块的行为 → 下一次 `wf.py` 调用必须按新代码执行。
- R3.4 缓存条目必须可辨认：模板旁的 `<key>.meta.json`
  （`key/digest/pyver/deploy/version/ref/root/created_at`）与模板目录**同级**，
  不放进模板内部（保持模板是"忠实的夹具空态"）。

### R4（调度：去掉结构性串行，不牺牲隔离与判定单点）

- R4.1 flows / extra 并入与 suites 相同的并行池（每个单元仍用私有夹具 + 私有 `/tmp`）。这是本组的主要收益来源。
  串行段与并行段共用**同一个** worker：执行域由 `WF_NAMESPACE` 区分（并行 `1`、串行 `0`），同一段执行/结果行代码；
  `run_all.sh` 不再保留任何单元执行分支（`run_suite`/`run_flow`/`run_f0`/`run_extra`/`expect_of` 全删）。
  记录→executor 的 `kind` 映射（`suite|candidate→suite`、`flow|extra→flow`）只存在于 worker 一处。
- R4.2 repro 保持在主池之后**串行**执行（**默认行为不变**，依据决策记录 #3：并发编排实测只值 3–6s，
  且引入抖动风险）；同时提供显式开关 `--repro-concurrent` 供需要时实验，开关路径同样要有可核验的等价性证据。
  repro 仍是唯一执行体（`repro/run.sh`），判定仍由它单点产出，run_all 只消费其机器可读汇总。
- R4.3 并发预算只有一份（单一来源），默认不超订；串行 repro 时该预算全部给主池，开关打开时按实测比例分配。
- R4.4 `summary.json` 增加分段墙钟（主池 / repro）与预算块，使"提速来源可归因"可机械复核
  （串行 repro 下同样需要分段，否则无法归因）。

### R5（防回归闸门）

- R5.1 机械门槛：测试源码禁止 `sys.path.insert(0, "/tmp")`（正向集合为空）。
- R5.2 机械门槛：`run_all.sh` 必须设置 `PYTHONPYCACHEPREFIX` 且不得再导出 `PYTHONDONTWRITEBYTECODE`。
- R5.3 机械门槛：`.gitignore` 覆盖 `__pycache__/` 与 `*.pyc`。
- R5.4 产品热路径性能守护：单元层断言 `wf.py status`（pyc 预热）**5 次中位数 < 500ms**
  （≈8× 当前实测 62ms；用于尽早发现 `task-check 1.87s` 那类 30× 级回归；关闭开关 `WF_PERF_GUARD=0`，
  关闭原因必须写在断言消息/注释里）。阈值只有这一处，design/implement 引用同一数字。
- R5.5 预算可见：summary 记录 full 墙钟与阈值；**超阈值只报告不硬失败**（见 design 的取舍论证）。
  该取舍只约束**运行期门禁**；任务验收的性能证据见 AC1（同机同基线口径）。

## 约束

- 不改产品面：`docs/workflows/wf/payload/**`、`docs/workflows/wf-release/**` 不动。
  产品侧的 `probe_version` 每调用一次、急切导入、git `cat-file` 批量化属**另一个任务**（见"不做清单"）。
- 不删、不弱化任何用例或断言；执行单元数在改动前后保持一致（149），差异必须来自"新增的负例"。
- 不新增第三方依赖（本机 `coverage` 缺失且网络不可依赖）。
- 单一判定只有一处实现：不新增第二份计时/断言解释/并发选择/缓存失效逻辑。
- 夹具与结果安全边界（所有权 marker、symlink 拒绝、保护路径、work er 私有 `/tmp`、只读挂共享发行）只允许收紧，不放宽。
- `r67_tests` 是运行器契约的复制消费者：任何契约变化必须同步并跑其回归。
  假树清单由 `plan.py::FAKE_TREE_COPY/STUB/SPECIAL` 三桶单一来源提供（r67 读它复制或桩化），新增 helper 必须同批归类，
  并由机械门槛 G8 守护——不接受「记得手工同步」这种靠人守的约定。
- 运行中不得编辑 runner 文件（bash 按偏移读取）；串并行等价对拍是硬要求。
- 本任务**不进入实现**，直到用户审阅 `prd.md` / `design.md` / `implement.md` 并批准 `task.py start`。

## 不做清单（本轮明确排除，登记理由与触发条件，避免"问题遗留"隐形化）

| 项 | 理由 | 触发条件 / 归属 |
|---|---|---|
| 产品面：每次调用 `probe_version`、lazy import、git `cat-file --batch` | 属产品行为与发行验证，需自己的断言与候选发布流程 | 另立任务；本轮只提供测量数据 |
| 57 套件 helper 收敛（57/57 重复 `rec()`、39 个自有 `wf()`） | 与提速正交，改动面 57 文件 + 10097 行，单独立项风险可控 | 另立任务；本轮不在其文件内做无关重构 |
| 覆盖率工具化 | 本机无 `coverage`、离线不可装；本轮**不提供**任何覆盖率替代门槛（避免用弱代理制造假绿） | 另立任务；本轮只在 AC6 里登记该缺口，明确"741 用例对 26.4k 行产品的覆盖度未知" |
| 常驻 / batch SUT 进程模型（理论 ~8–12s） | 会放弃真实进程边界（exit code / stderr / 进程锚点 / 锁窗口），与多份现有断言冲突 | 需产品级决策；本轮只记录为理论上限 |
| 统一 SUT 与 runner 解释器 | 上一轮已论证会改变 `l2_anchor` 拓扑 | 保持否决 |
| `d1_tests` / `d1_wf_tests` 自动化 | 需要真实宿主压缩 | 保持手动专属 |

## 验收标准

- **AC1 提速（验收证据，不是运行期门禁）**：同机、与基线同一口径（并行 92.9s / 94.5s、单套件 13.4s）比较：
  - 硬性：`--full --repro green` 两次采样墙钟 **≤65s**（相对基线至少 −30%），且 `--serial` 逐项对拍相等
    （`lines` 五列：单元名/rc/status，**含原 flow/extra 单元**；repro 逐用例 mode/green/red/verified）；单套件定向 run **≤7s**。
  - **计数对拍的三分量（不得混着比）**：`lines` 行数 == `suite_ran + flow_ran`（即计划单元数，合并后 64：
    59 套件 + 4 流程 + r72）；`units_total == suite_ran + flow_ran + repro_ran`（149）；
    `repro_ran` 与 repro 执行体的 `REPRO_TOTAL` 相等，且**永远不与 `lines` 行数比较**
    （repro 用例不写 `lines`——`lines` 只由 worker 按计划单元逐行写入）。
    依据：实测 `run-3290992` 的 `lines`=59 行、`suite_ran=59`、`flow_ran=5`、`repro_ran=85`、`units_total=149`。
  - 目标：≤60s（报告指标）。若实测落在 60–65s，必须在验证记录里写明剩余差距归因与处置结论
    （接受 / 继续优化 / 回退某项），不得只报数字。
  - 收益构成逐项列清：字节码缓存（实测 −35%/套件）、flows/extra 入池（实测 3 个 p5 flow 13.89→5.76s；
    f0/r72 按 run 内 flows 段 19.3s 归因）、模板跨 run 缓存（实测构建 2.73s）；**不含** repro 并发（决策 #3）。
  - 与 D5-G6 的口径区别：G6 禁止**运行期**对墙钟硬失败（任意机器都会假红）；本 AC 是**任务验收**证据，
    只在同一台机器、与基线同口径下比较。
- **AC2 证据预算**：所有可计划单元均有 `expect`；`plan.py` 负例（缺失/非正整数/未知字段/非法 kind·fixture/
  `script` 缺失或文件不存在）各有对应用例；
  **记录契约**：`PLAN_UNITS` 每条恰为五段且 `script` 与注册表一致；`f0` 由记录里的 `p5_f0.py` 驱动
  （不是 `f0.py`）；r67 假树的桩文件名取自 `script`；
  **完整性覆盖**：`results_gate` 对 `PLAN_UNITS` 名字全集判一次（含 flow/extra 与串行段），
  用"漏跑一个串行单元 → `MISSING-RESULTS`"的构造留证；
  **实证**：从任一套件的输出里删掉一个用例行 → runner 变红（记录命令与输出）。
- **AC3 卫生**：`sys.path.insert(0, "/tmp")` 全库零命中；仓库 `.gitignore` 覆盖 pyc；`fallback_representative` 零引用；
  P3-1 自证断言已移除，且新检查有**两次**证伪证据（Step 1 植入 pyc → 红；Step 3 去掉缓存策略 → 自然产生 pyc → 红）；
  存量清空后，一次 full 与一次 T0 结束时
  `find docs/workflows/wf scripts/tests \( -name '*.pyc' -o -name '__pycache__' \)` **输出为空**（绝对判据）。
  运行期检查本身**只对新增失败**（存量以警告 + 可操作清理命令呈现），这一分工在 design D1.4 写明。
- **AC4 不回归**：149 单元 0 失败；`r67_tests` 契约回归绿（**每个改动 run_all 契约的 Step 都要跑一次**，
  不是只在收口跑）；`KNOWN_LEGACY` 仍为空；
  记录 8 并发下的最慢单元耗时与 `WF_COMMAND_TIMEOUT` 余量、repro 最慢用例与 `WF_REPRO_TIMEOUT` 余量。
- **AC5 缓存正确性**：模板缓存七条实证——① 改 payload **内容** → 重建（反向：只 `touch` → 仍命中）
  ② 换解释器版本 → 不同 key ③ candidate 换 version/ref → 重建 ④ 半成品条目（无 meta）→ 失效重建
  ⑤ 条目被搬动（`meta.root` ≠ 当前 `realpath`）→ 失效重建 ⑥ 克隆时 repoint 改写数与 meta 不符 → 该单元失败
  ⑦ 条目内混入 pyc → strict 检查判脏并重建；另加 pyc "改源码立即生效"一条实证。
- **AC6 无遗留**：文档同步（`full/README.md` 的并发与性能段、交付纪律 §7/§12 的 T0/T1/T2 行与时间预算、
  `.trellis/spec` 中相关运行器契约）；summary schema 版本升级；"不做清单"在任务收口时原样保留并指向后续归属。
