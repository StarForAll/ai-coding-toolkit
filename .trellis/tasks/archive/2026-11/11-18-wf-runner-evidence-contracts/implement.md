# 实施顺序和验证

方案批准后执行。当前基线 `b84b1a56`，在任务处于 `planning` 时只修改任务工件和做文档检查。以一个任务承接相互依赖的证据链，各验收组分别出具可核结果。

本方案的激活命令以在当前 **Codex inline** 会话继续实施为前提。当前运行模式与仓库 [Codex 配置](../../config.yaml#L150) 一致。Phase 1.3 跳过 JSONL 配置，Phase 2 通过 `trellis-before-dev` 读取工件和规范。批准后按 1.4 使用 `/softwares/python/bin/python3 -B .trellis/scripts/task.py start --allow-empty-context .trellis/tasks/11-18-wf-runner-evidence-contracts`。若改由 ZCode 等项目流程列出的子代理派发环境实施，激活前按该平台的 [Phase 1.3](../../workflow.md#L407) 配置两份清单，使用常规 `task.py start`。

## 1. 工作顺序

1. **固定负对照。** 核对 HEAD 与工作区，沿用现有契约的 owned scope、计数 shim 和确定性故障握手。对 A1–A5 各建最小复现，观察旧实现的错误结果。取消场景按第 4 节建立触发点与可达性断言。当前已有的缺陷在同一观测条件下先复现再修，新增决策边界用正反对照验收。记清「预期复现失败」与「基础设施无法运行」。
2. **统一请求、租约与发行事实（R1、R4）。** 按设计 1.1 先接通独立 repro 的单次解析与 lease frame、full 与独立 repro 的同代 `plan.json` 原子写入和校验。移除独立外层通过 `WF_REPRO_LEASE_READY` 重传公开 argv、内层重新解析 argv、C 从环境合成计划三条旧路径。更新 `runner_protocol.py`、`execute_gate.py`、repro bundle/摘要的同代身份和 fake tree。接通后，把 `release_context.py` 的 dev acquire/write_env 及 repro shell 的 dev `--lease` 重入和哨兵一并移除，迁移至 C 的单次取锁与监督准备。接通 `wf_test_release.py --no-lock` 的租约核验与原 locked 分支。沿 C→G→S→W 白名单传 FD，验证宿主消费与 `namespace.py` 的副本关闭。按 dev 首次构建、候选真实安装/模板/终核、候选审计与独立摘要的顺序核验。
3. **统一取消处理和最终出口（R3）。** 保留 `begin-run` 的旧代清理。移除 `run_all.sh` 的 `CANCEL_REQUEST` 路径派生、`rm -f`、`WF_CANCEL_FILE` 重新导出和未定义函数 trap，移除 `repro/run.sh` 的本地 fallback、删除及覆盖写 trap。统一由 C 交接本代标记，shell 收到信号才调用共用发布逻辑。扩展 `CancellationScope` 支持最终决策观测，覆盖 INT/TERM/HUP、内嵌边界、收尾和发布。保留收尾异常归因，校验一代只清理/发布一次。
4. **收口相位证明（R2）。** 接入命令 receipt 的身份、相位、监督与实际清理；把全局 state writer 调用收归 C 的结束路径。验证坏/缺/错代证据、真实本地回收失败、显式 KEEP、v4 重验、完好对照和通过用例部分合并。同步新协议的字段登记、`NON_CASE_FILES`、资源登记与公共输入摘要。验证读坏、不存在、临时写入失败、落盘失败和 replace 失败，以及后续 `auto` 的选择。旧清理/恢复逻辑无需重写。
5. **修实业务断言（R5）。** 按下列已确认与需核覆盖口径逐项处理。只对实际改动登记 expect 的增减，与用例逻辑、注册表、候选审计和覆盖清单一起核。
   - **已确认无有效断言**。D1-3、R84 无绑定恢复、R67 3d、[R65 R5](../../../scripts/tests/wf_runtime/full/r65_tests.py#L99)、[R62 P1-3](../../../scripts/tests/wf_runtime/full/r62_tests.py#L74)、[R76 1f](../../../scripts/tests/wf_runtime/full/r76_tests.py#L81)、[R82 A7c](../../../scripts/tests/wf_runtime/full/r82_tests.py#L137) 都直接传 `True`。R76 还有空循环，样本不足也未建立受控前置。R82 A7/A7b 各有真实判断，应保留各自覆盖。为无效行补真实结果和拒绝对照，或在验证同一行为已有覆盖后删除重复的通过记录。
   - **核对覆盖口径**。[P5 f0](../../../scripts/tests/wf_runtime/full/p5_f0.py#L23) 的 `task-new` 后有非空 `task_id` 守卫，第 30 行的 `rec` 固定为真。先核守卫是否已证明该行所称的业务事实，再决定是否需要补断言或改为纯展示。同文件的 `enable` 已独立检查 `rc == 0`。
6. **整体验证和对账（A6）。** 更新 full/repro README 和本任务触达的现有 runner 契约说明。比较实际请求、用户可见摘要、已安装提交、所有 receipt 归属和下次执行选择。记录涉及的生产侧只读快照、清理结果及所有计划/源码差异。

## 2. 可执行验收矩阵

| 验收 | 需要复现的旧行为 | 修正后的对照与观察 |
| --- | --- | --- |
| A1 | A/B 同内容而不同提交可共用模板，候选复核依赖 repro，候选 meta 未统一拒绝冲突。dev 旧持有者在受监督链内，扫描两个旧取锁点以验证迁移完整性 | 在同一 owned scope 使用空模板缓存依次跑 A、B、B，核三次命中状态与 B 的安装记录。分别跑候选无 repro、内嵌和独立验结束提交漂移。候选 full 无 repro 和独立用真实同根发布命令验 busy，独立跑两个选定 case，在两 case 之间验证持有者与 inode 同起点。发布完核锁可重获。两个入口分别对照默认 meta、有效 CLI 或 env 指向 scope 内另一份有效 JSON 的拒绝、CLI canonical 覆盖冲突 env 的成功。确认拒绝在 worker 前且 sidecar 未改。dev 的迁移对照见下节。 |
| A2 | 目标 rc=0 且 PASS，局部目录回收失败仍写 red，下一次 auto 走 green | 分别注入局部清理、坏/缺/错代 receipt、状态读取、临时写入或 fsync、replace 失败。使用带旧 proof 与无状态文件的对照，核本次 rc、诊断、保留路径、state 原字节、有无临时残留及下一次相位。对照清理成功、KEEP、业务断言失败但其他 case 可合并、v4 首次成功转换。 |
| A3 | 内层 trap 不工作；full 和 repro 内层自行重置取消标记；finalize 时收到信号仍成功 | 第 4 节握手确认真实路径与触发点。检查干净启动不建标记，预先发布的本代请求未被删改或复制，随后验证真实 C 的清理中、决策前后信号。核停止调度、一次清理、原 rc、取消 rc、receipt、run-state、摘要和唯一成功输出。分别验证决策后正常发布和 I/O 失败。 |
| A4 | 候选 list 退出 1，独立 candidate 被写成 dev，已运行时模式仍标 none | 干净环境两种 list 零结果、锁、pyc、cache 写入。用计数记录证明独立入口只公开解析一次。分别注入缺文件、符号链接、SHA/长度错误及 token 正确但 role、run_id、根或字段结构错的计划，核 C 在取发行锁前拒绝。C 验证后、内层启动前替换 plan/context，核 worker 未启动。提交错代或 plan token 不符的 bundle 时，gate、writer、摘要均拒绝当成本代证据。对照真实 CLI 覆盖环境、dev `both`、混合 `auto`、candidate green、无 repro、未完成相位。以已核计划、bundle、tag、相位 receipt 对照四个摘要字段，另核分组/only、空格路径及无效参数。 |
| A5 | D1、R84、R67 在返回值破坏时仍 PASS | 注入目标返回值/记录的变化，逐条报告旧绿新红，配合正常入口真绿。重新生成受 suite 字节影响的候选审计项，核 candidate-clean 的分母、行和原先省略原因。 |

## 3. dev 锁迁移对照

- 在独立的 owned scope 用真实 full 与 `repro/run.sh` 验证冷构建、热复用、`--no-build` 的新鲜度校验和陈旧拒绝。正常入口要确认无自撞 busy。沿用计数 shim 指向真实发行 CLI，核每个整次运行恰有一次准备调用，`--no-lock` 只出现在持 C 租约的准备阶段。内嵌跑默认构建与 `--no-build`（含并发交接），仍只看到父端一次调用。
- 用同一 C 的 PID、`/proc` FD inode 和实际 FLOCK 取证。在准备、独立 repro 两 case 之间及 worker 结束后的收尾观察同一租约。同根的独立 `wf_test_release.py --ensure` 与 `--check` 必须真实 busy，整次正常退出后另一进程可重获同一 inode 的锁。反向用例覆盖无租约、错 root、错 PID 和错 mount，核 `--no-lock` 非零且零发行写入。父 lease 的 FD 在 unshare 中只关闭副本，宿主仍持锁。

## 4. 取消探针与可达性

现有 [G/S 故障点](../../../scripts/tests/wf_runtime/full/execution.py#L74) 只能在 supervisor/guardian 注入，现有 [收尾故障选择器](../../../scripts/tests/wf_runtime/full/runner_cleanup.py#L34) 覆盖异常、删除与写入失败；两者都没有 C 的决策前后信号触发点。

- 目标 shell 及并发内嵌路径用私有 scope 的 fake tree 与测试替身在现有交接点做双向就绪握手。初始化探针同时核对 full、独立 repro 干净启动没有标记，以及内嵌启动时已有标记字节、inode 均未变，自己的结果根也无替代标记。full 在 trap 之后调用的 source hygiene snapshot 可作为就绪点。内嵌 repro 在进入内层且尚未启动 worker 时暂停，先建立父请求，再放行并观察请求和调度。收到目标 PID 和阶段确认后，测试才向本次进程发信号。握手超时或目标提前退出按探针未达判失败。
- 新增收尾信号用例调用真实 `runner_control` 和 `CancellationScope`。在测试进程内包装实际 `finalize` 后段，以同进程真实信号复现旧实现的假成功。新实现另包裹取消信号待处理集合的读取和其后的摘要发布入口。前者在屏蔽已生效、读取前发信号，后者在决策已固定时发信号。保留被包装方法及信号处理器的原逻辑，校验触发点名称、进入次数及实际信号。发布失败可复用既有 I/O 故障注入。测试只依赖这些现有接口与新增的实际决策路径，无需生产测试开关或 sleep。
- 记录旧版探针证据和新版前后对照。捕获异常或日志缺失不得当作取消成功；与 CLI 的子进程测试共同核对 `130/143/129` 等既有信号码及终态证据。

## 5. 验证顺序和命令

实现验证继承 [上轮 scope 条件与调用包装](../archive/2026-11/11-16-wf-runner-lifecycle-contracts/verification-plan.md#L17)。保持宿主 HOME/Git 语义，净化外来 WF 定位与故障变量。每个 runner 调用使用自己的结果/夹具/pycache 根，允许同一逻辑 case 共享缓存和 state。使用项目指定的 `/softwares/python/bin/python3`。

- **语法及定向**：逐个执行 `bash -n`（`run_all.sh`、`run_one.sh`、`repro/run.sh`、`wf_fixture.sh`）。先定向复现新增场景的旧行为，修正后重跑同一用例，再逐组用现有 `scripts.tests.wf_runtime` 模块验证相邻契约：
  - 发行与夹具：`test_test_release`、`test_release_lock`、`test_prepare_candidate_repo`、`test_fixture_template`、`test_template_cache`、`test_candidate_audit`。
  - 请求和交接：`test_execute_gate`、`test_runner_protocol`、`test_resource_lifecycle`、`test_repro_cli`、`test_repro_list`、`test_repro_selection`。
  - 执行和证据：`test_execution`、`test_supervision`、`test_runner_cleanup`、`test_results_gate`、`test_results_summary`。
- **通用及真实入口契约**：`/softwares/python/bin/python3 -B -m unittest discover -s scripts/tests -t .`，随后 `WF_SLOW_TESTS=1 /softwares/python/bin/python3 -B -m unittest scripts.tests.wf_runtime.test_run_all_contract`。在 owned scope 内使用现有包裹，每次调用分别确认路径边界与宿主快照。
- **full**：按上轮 `scoped_run` 口径，依次跑 `run_all.sh --full --repro green`、同参数加 `--serial`、`run_all.sh --full --repro both`。真实并行能力不可用时记录 fallback 和未验证的并行分支，不能把两次串行视为并行对照。逐 ID 比较状态、rc、真实相位和 receipts。
- **候选和独立**：用产品清单的当前版本在 scope 内构建候选，跑 candidate full green、至少一次 `--repro none` 路径、独立 candidate green 和 dev red/both→candidate auto。以真实 tag/commit 对照；重新生成审计使用独立 workdir，沿用已有 candidate-clean 选择规则。生成物不得手填通过。
- **发行与文档**：按既有流程在临时区运行 `scripts/build-wf-release.py --verify --verify-token-parity`，核生成发行树与产品树。对实际改动的契约文档和本任务工件运行 `scripts/check-doc-refs.py`。最后核对 staged/untracked 和 `git diff --check`，逐项保存验收结果。

## 6. 回退和失败处理

- 先用私有 scope 验证候选发布竞争、缓存命中、旧 proof 和恢复窗口，避免改宿主缓存及锁。新旧 writer/reader 与相应测试需要同行，审查实现差异时检查三个执行入口是否仍有旁路。
- 出现异常先保持相关结果及旧 state，依据身份、证据或清理归因判别下一步。对旧 proof 使用重验出口；对旧模板使用新键自然重建；对 retained/unknown 使用既有精确处置。回退本任务的代码改动时，验证用 scope 可独立保留/回收。使用新代码写出的证明不向旧版本降级回填。
- 产品命令暴露出真实的行为缺陷、宿主前置不足或受监督能力不可达时，记录触发命令、错误、影响和可继续的验证面。完整验证按观测标记通过、失败或未执行。
