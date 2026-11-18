# wf 运行证据修正设计

本文描述待审查的实现。其中 C 指现有 `execution.py --runner-control` 的整次运行外层进程。保留现有进程监督、结果目录所有权、缓存事务和唯一成功出口。

## 1. 事实归属

| 事实 | 产生与核验 | 消费方 |
| --- | --- | --- |
| 执行请求 | full 的 `plan.py` 与独立 repro 的 `repro/cli.py` 分别生成同代 `plan.json`。内嵌 repro 读取父计划 | C、受监督 shell、repro bundle、摘要。环境变量仅提供公开入口默认值或进程定位 |
| 发行消费租约 | 每个整次运行的 C 取得发行根固定 inode 的独占锁，`release_lock.verify_lease` 核验实际持有者和锁 | 发行准备、宿主 execute、内嵌与独立 repro、proof writer |
| 候选来源 | `prepare_candidate_repo.verify_candidate` 给出 canonical root、version、ref、tag commit 和实际树摘要；`release_context.py` 将候选事实绑定本代并交接 | 候选起止核验、模板、实际安装后检查、repro context、报告 |
| 相位命令与清理 | `execution.run` 写同代命令 receipt，`runner_cleanup` 解释监督与资源清理事实 | repro gate 和 proof writer 按同一个相位核验读取，整个 run 的清理仍由 C 汇总 |
| 取消与最后判定 | C 的 `CancellationScope` 及本代取消文件，C 使用同一锁存值判定本次终态 | 调度、监督、证明发布和最终退出 |
| 摘要 | `results_summary.py` 从已核计划、发行 context、执行证据和 C 的结果构造。实际相位由 bundle/records 核验报告提供 | CLI 与 CI。跨文件终态以同代、完成且一致的收口记录为准 |

### 1.1 冻结执行请求及交接

1. 每次执行复用结果根的 `plan.json`。两个入口都在 fixture/results 租约内且 `begin-run` 完成旧代 prepare 后写一次。已有 full preflight 继续只作预查，只有 lease 内的 final plan 是执行依据。公开 repro 由 `repro/cli.py` 一次解析参数、应用 CLI 优先于环境的规则并输出规范对象。help/list 在这里无写入退出。执行时用 `runner_protocol.py` 的保留 lease frame 在原有 `lease-results` 的同 PID exec 链中携带解析后的 JSON 对象，lease 入口核对 entry PID、有效租约、对象结构和路径，再冻结到 `plan.json`。取消当前基于 `WF_REPRO_LEASE_READY` 和重传公开 argv 的重入，内层只解析已核计划。见 [当前解析入口](../../../scripts/tests/wf_runtime/full/repro/run.sh#L61)、[fixture/results lease](../../../scripts/tests/wf_runtime/full/fixture_scope.py#L494)、[生命周期初始化](../../../scripts/tests/wf_runtime/full/resource_lifecycle.py#L489)。
2. 执行计划绑定 `schema_version`、`role`、`run_id`、canonical `results_dir` 和 `scope_root`（无显式 scope 为 null）。沿用现有计划字段表达 `fixture_deploy`、候选 `release_root`、`release_ref`、`release_version`、`release_meta`、dev 的 `test_release_root`、`test_release_version`、`test_release_ref`，以及 `no_build`、`repro_enabled`、`repro_mode`、`repro_groups`、`repro_jobs`。独立 repro 加 `repro_only`（full 为 null）、`mode=repro`、`full_mode=0` 和空 `units`。根、版本和其他前置默认值先按已有规则解析。未适用的发行字段沿用现有空值语义。实际发行 commit 与树摘要由后续已核 context 提供。
3. lease 阶段把完整计划原子写到固定路径，复用 `runner_protocol.py` 的 path/SHA-256/size token，以现有 `--plan-file`、`--plan-sha256`、`--plan-size` argv 交给 C。C 校验 fixture/results 租约与 owner/active run-state，随后对固定路径普通文件有界读取，核验同一份字节的 token、结构及本代 `role/run_id/results_dir/scope_root`。路径不同、文件缺失、摘要或长度不符、旧代或字段不完整，在取发行锁和启动 worker 前归因失败并保留现场。两个 role 都走此判定，删除独立 repro 由环境合成计划的分支。见 [当前 token](../../../scripts/tests/wf_runtime/full/runner_protocol.py#L180)、[controller 入口校验](../../../scripts/tests/wf_runtime/full/execution.py#L1456)。
4. C 写的发行 context 绑定本代与 plan token。独立内层和内嵌 repro 通过同一 `runner_protocol.py` 交接 plan/context token，核验父 C、租约、两文件的本代与摘要关联后，从已核数据派生部署与执行参数。独立结果写本地 `results_dir`，内嵌固定写父结果根的 `repro/`。每次消费均核对实际用于解析的字节。repro bundle 绑定本代 plan token，gate、writer、summary 输入证据核对这项对应关系。token 和代次只用于证据归属，不改变跨 run 的 proof 身份。full 计划展示与老结果目录仍可读，旧格式只供历史展示。将 `plan.json` 等控制产物从独立 repro 的 case 枚举排除，摘要单列 plan/context 的哈希。

## 2. 发行消费期与候选模板

### 2.1 整次运行的锁与持有者核验

- full 在 lease 后已 `exec ... --runner-role full`，独立 repro 也在 fixture/results lease 与 `begin-run` 后 `exec ... --runner-role repro`。选定 dev/candidate 后，这两个现有分支各自的 C 是整次运行唯一的发行锁持有者。full 内嵌 repro 复用父 C 的租约和 context。见 [full 入口](../../../scripts/tests/wf_runtime/full/run_all.sh#L202)、[独立 repro 入口](../../../scripts/tests/wf_runtime/full/repro/run.sh#L144)。
- 锁序 fixture → results → release。C 依据冻结请求一次确定发行根、version、ref 和准备动作。dev 保持现有版本及 scoped cache 的来源规则，候选保持已选 root/ref/version。用各发行入口已有的路径及 scope 验证检查根与派生文件后，C 调用现有 `release_lock.acquire(..., exclusive=True)` 取得 canonical root 的固定 sidecar inode。此锁与该根上的测试发行 ensure/check 或候选发布共用。竞争返回既有 busy/非零，准备命令和 worker 均不启动。
- C 用自身 PID 发布现有 `WF_TEST_RELEASE_LEASE_*`/root 定位值，盖过继承的旧定位值。准备和宿主执行的 `pass_fds` 在现有白名单中加入这一个 FD，经 C→G→S→W 传递同一打开文件描述。消费者只从冻结 context 确定待验 root，并用同一 `verify_lease` 核对由本代 controller 交接的预期持有者。持有者在后代是祖先，在 C 内核验时是当前进程。保持现有 `/proc` 祖先链、canonical inode、内核独占 FLOCK 和 mount 域检查。CLI `--verify` 继续委托这个判定。PID/FD 只作本代定位，发行内容主体、模板键和 proof 身份均不包含这些进程字段。见 [当前验锁函数](../../../scripts/release_lock.py#L77)。
- 核验发生在发行准备、full 的 execute、独立/内嵌 repro 的宿主入口和 C 提交 proof 之前。租约缺失或错持有者、错根、错 mount 域时拒绝继续。私有 mount 的单元按现有规则只关闭自己继承的宿主 FD 副本并清除 locator，通过只读挂载消费发行。C 持锁贯穿各 case 及其间隔、收尾、proof 和终态发布。有确认的退出由 C 释放。若监督丢失，C 只关闭本端 FD，保留继承者可能仍持有的锁，按 unknown 保留现场。

### 2.2 两类发行的准备、消费与结束

- **dev**。在同一变更中删除 full 的 `release_context.py` 子链 acquire/write_env，删除独立 repro 的 `release_lock.py --lease` 再次 exec 及 `WF_REPRO_RELEASE_READY` 分支。C 通过现有监督器调用一次共用的发行准备。准备 helper 核验 C 的租约后，调用 `wf_test_release.py --ensure --no-lock`，或在 `--no-build` 时调用 `--check --no-lock`。CLI 的 `--no-lock` 路径也先用现有 `verify_lease` 证明同根独占租约，随后才进入 locked 实现。full controlled/execute、独立内层和内嵌 repro 只验证和消费 C 交接的冻结 context。保留公开 `--ensure`、`--check`、`--lease` 的既有自行取锁路径。见 [full 旧取锁点](../../../scripts/tests/wf_runtime/full/release_context.py#L188)、[独立 repro 旧取锁点](../../../scripts/tests/wf_runtime/full/repro/run.sh#L196)、[测试发行 CLI](../../../scripts/tests/wf_test_release.py#L744)。
- **candidate**。C 监督同一只读 validator 的初核和终核，显式登记本代证据并使用本次的 deadline 和取消机制。初核认定 owner 与真实 root、version、ref、commit、树摘要后冻结 context。取值需与冻结请求对应后方可启动 worker。终核在 worker 退出后、发布前对照这份身份，覆盖无 repro 或无可提交用例的正常消费路径。结束比对可以发现绕过发布锁的持久变化，两次观测之间的临时修改与恢复超出现有观测能力。
- **候选 meta**。full 与独立 repro 共用参数判定。`--release-meta` 优先于 `WF_RELEASE_META`，未给有效值时派生 canonical 候选根的 `.meta.json`。给定有效值时按现有路径/scope 规则解析并比对 canonical sidecar 路径。另一文件即使内容相同也在启动 worker 前非零拒绝并报告 meta 路径冲突。validator 只读取原 canonical sidecar。计划入口与公开候选 `--check` 仍是只读调用。

### 2.3 候选模板的身份

- 保留 `release_subject` 的跨 dev/candidate 字节语义。候选模板键在内容主体基础上加已核 commit，同一提交与同样输入仍可复用。真实安装和克隆统一经 `template_check.py` 核 `version`、`release_ref`、`source_commit`，并保留原有安装规则摘要、只读库来源和重锚定检查。覆盖 template 缓存/本次构建/禁用，以及直接安装、`wf_fixture.sh`、`candidate_audit.py` 的已有消费者。缺 commit 或身份不匹配，缓存读为 miss，已消费夹具或明确提供的模板按准备失败处理。
- 新身份只改变候选模板输入键。旧候选模板自然不命中。旧目录仍可盘点，处置沿用原有恢复/退役规则。候选审计输出在 owned workdir 内用同一身份核验，记录本次 commit。

## 3. repro 相位、证明与重验

- Worker 写 case 结果和每相位的 receipt 引用。核验以本次 `run_id`、case、phase、`command_id`、预期日志路径和规范 `commands/` 目录绑定终态 receipt。命令身份、`rc/status` 与 phase 专属 PASS/FAIL 需要一致，同时验监督清理与相位临时目录清理。缺收据、未完成、坏 JSON、错代、路径或相位错配都属于证据异常，理由进入报告。已有 `execution.verdict` 的日志判定与 `runner_cleanup.assess_execution` 的监督判定各自保持唯一。
- 目标断言失败、设施/清理失败、显式保留单列。修正同链上的 `WF_REPRO_KEEP=1`：托管相位的回收决定交给现有 cleanup 所有者，已请求保留的实际路径按 `retained-keep` 登记并保留。保留的相位可展示日志与断言事实，但不能签清理完成或进入 proof；有保留路径的结果不能自动复用/轮转，仍走既有盘点与精确退役。
- C 持 fixture/results/release 租约，等 worker 及其监督退出。结束发行校验、清理事实和取消状态有结论后，调用一次现有 `repro_select.commit_state`。Shell 只产出 bundle/records 和诊断。移除 shell 唯一使用的内部 `commit-state` 命令入口，防止绕开结束判定。该 writer 在写前对同一 bundle、公共输入、每个合格 case 的局部输入重验，使用与 gate 共用的相位/receipt 判定。内嵌 repro 使用父根的 receipt 和 `run_id`。独立入口没有 full metrics 依赖。
- `both` 仍要求该 case 的两相位都成立。其他 case 只有业务断言失败、结构完整且清理已确认时，已通过 case 仍可独立合并；设施错误、候选漂移、清理未确认或写入前已取消，整次不提交。已完成证明的原子写是每个合格 case 的独立事实；后续取消或摘要写入失败会改变整次 run 的结论，已经提交的完整 case 事实保留。失败或取消的相位不能出现在更新集合。
- `repro-state.json` 升到 v5，读 v1–v4 时将其保留为 legacy，首次成功写入才转格式。旧 red 缺少本规则下的清理证明，`auto` 不命中。dev 重新跑 `both` 或 `red` 后恢复，candidate auto 仍先要求同主体有效 dev red。已经过 v5 验证的其他条目保留，损坏/未知版本或读取失败时拒绝覆盖。旧 bundle/结果目录保持历史可读；新 bundle、context 的 writer/reader 同批更新，旧数据不冒充本代证据。
- Proof writer 在目标同目录准备临时文件，完整写入并完成 flush、fsync、关闭后，用一次 `os.replace` 提交。读旧状态、写临时文件、落盘、关闭或 replace 失败时，旧文件字节保持原样，原先没有状态文件时仍不创建，报告运行失败。只清理本次临时文件，临时文件无法清理时报告路径，`auto` 始终只读正式路径。replace 成功后 proof 已提交，后续 run 终态失败仍按已提交事实处理。

## 4. 取消和最终发布

- `begin-run` 的 prepare 清理允许复用的旧代取消标记。C 在观察管理路径和发行准备前指定本代根下的 `cancel-request` 并建立作用域，以本代定位覆盖外来 `WF_CANCEL_FILE`。移除 full 与 repro 内层自行派生、重设或删除标记的代码及原 trap。新 trap 只在收到 INT/TERM/HUP 时，在 C 交接的路径用排他创建发布标记，并保留原信号退出码。标记只表达请求存在，已锁存的真实信号及目标退出码优先用于归因。已有标记视为请求已发布。其他创建错误输出明确诊断，保留信号对应的非零退出及监督收口。内层和内嵌启动都不能清除或改写已有请求。C 的信号 handler 仍只锁存，主循环和收尾读本代标记。保留 C→G→S→W 和 G/S 接管路径。见 [生命周期登记](../../../scripts/tests/wf_runtime/full/resource_lifecycle.py#L99)、[full 旧逻辑](../../../scripts/tests/wf_runtime/full/run_all.sh#L287)、[repro 旧逻辑](../../../scripts/tests/wf_runtime/full/repro/run.sh#L256)。
- 通用监督退出时归并信号、取消文件及真实进程退出事实。关闭新调度，等待已有 worker 收口。C 在外层清理、结束候选检查、证据复核和发布准备期间持续接受取消，并在 proof 写入前与最终成功决策前消费锁存值。保留原目标失败事实与真实清理结论；没有先前失败的取消使用既有非零退出语义。未清理的路径保留。
- 最终成功决策边界固定在 C 完成核验和摘要材料准备、正式发布终态之前。在现有 `CancellationScope` 的 install/restore 和首次锁存上新增最终决策接口。新增接口阻塞 INT/TERM/HUP，最后观测已结束调度的本代标记，读取锁存和内核待处理信号，以该次观测固定最终结果。已观测到的取消阻断成功，目标已有非零 rc 与其归因照实保留。决定后在本代 handler 仍有效时恢复原屏蔽状态，按已定结果完成发布与读回；控制器退出时恢复入场 handler。此后只渲染终态字段、发布和读回。见 [当前作用域](../../../scripts/tests/wf_runtime/full/execution.py#L853)。
- 每个终态文件保持一次原子发布与必要读回，`run-state.json` 最后提交。先前终态发布失败时，只能写失败或取消终态，并登记证据不完整；run-state 自身提交前失败时保留 active。任一写入/读回故障均非零且无 GATE-OK。报告文档说明以 CLI rc 或同代 `run-state`、`.runner.json`、`summary.json` 一致的终态作为整次成功证据，并保留既有 active/unknown 的诊断与退役出口。

## 5. 清单、摘要与业务断言

- 从 repro 现有用例选择器抽出纯选择部分复用，列表只读组/用例登记，展示 case ID 和默认可跑相位两列（dev `both`、candidate `green`）。保持组、only、candidate-clean 过滤和未知组/无匹配的非零返回；不计算 release subject 或读 proof/state，也不要求候选缓存存在。选择失败不再把空 stdout 交给二级 JSON 解析。
- `fixture_deploy` 与 `repro_mode` 从 1.1 的已核计划投影。`repro_mode` 保留请求的 `auto`，未启用时为 `none`。保留既有键值类型、五列结果和 stdout 汇总接口。每份新发出的 `summary.json` 都增列以下字段，内嵌结果归入 full 摘要。
  - `candidate_commit` 为已核候选提交的完整值，dev 或在候选初核前失败时为 JSON null。候选运行要签成功必须有非空值，且与冻结 context 和终核相同。候选 commit 继续进入执行 fingerprint，跨部署 red subject 保持发行内容语义。
  - `repro_phase_counts` 包含 `green` 和 `red`，各有 `planned`、`passed`、`failed`、`unverified` 四个非负整数。`planned` 取本代已核 bundle 的逐 case 实际相位选择；其余三项取同一相位核验报告，合计等于 `planned`。断言已核通过或失败且终态证据齐备时进入对应项，缺失、错代或清理未获确认时计 `unverified`。禁用 repro 时全为 0；启用但尚无合法 bundle 时字段取 null。旧摘要缺字段只按历史展示。
- 核对 full 已注册用例里的 `rec(..., True)`、恒等条件、宽泛异常通过和只检查源码字符串的「行为」断言。只修改能证明当前断言为空、或覆盖宣称与实际不一致的场景。D1-3 核实际只读结果，业务推进拒绝由原 D1-3b 断言；R84 核无绑定恢复结果与对象/动作关联；R67 核恢复后存在预期声明义务。必要时用实际入口替换静态或样本自证，如已由同一个真实行为用例覆盖且无新增意义，删去误计并同步 expect。测试用例以已有业务契约为准，出现真实产品缺陷时保留失败和证据供用户判断，不放宽测试来维持全绿。

## 6. 方案自查记录

按十项清单回查了执行计划到发行、相位到证明、取消到终态三条链。本轮补齐 `plan.json` 从生成到摘要的代次及摘要绑定、取消请求所有者与旧入口的迁移，并对证据定位和定向测试作对应检查。候选竞争以同根发布锁为边界，多文件发布以同代终态为准。验证步骤及负对照见 [验收和执行顺序](implement.md)。
