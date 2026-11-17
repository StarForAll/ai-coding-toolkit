# wf 运行器资源生命周期与恢复契约收口

> 状态：实施与验证已完成，等待用户批准提交/收尾；AC01–20 的证据与限制见 [validation.md](./validation.md)。未提交、未推送、未归档。
> 基线：`c0c3a167`，创建任务前工作树干净。用户授权创建任务、规划与实施；提交/归档仍需单独批准。
> 当前为父任务（P1）：共享需求/设计与最终集成由本目录负责；三个子任务已完成各自实现与验证记录（任务状态仍为 in_progress，待提交/归档），责任、依赖和分批验收见 [delivery-map.md](./delivery-map.md)。父任务已于 2026-11-17 在 DSH inline 模式下 start，最终集成证据由本目录汇总。

## Goal

修正 wf 运行器已确认的五类非耗时问题，使资源释放、缓存恢复、错误传播和持久化证据在完整调用链上成立；用真实入口的异常组合验证阻断同类回归，避免只给被点名的位置加条件。

## 范围与约束

- 实现范围：`scripts/tests/wf_runtime/**`、`scripts/tests/wf_test_release.py` 及直接相关作者侧 helper、测试、`full/README.md`、`repro/README.md`、`.trellis/spec/docs/wf-delivery-discipline.md`；包括生命周期收紧带来的历史缓存/结果材料盘点、明确退役出口和确定性故障测试。仅在身份登记/假树依赖确实需要时调整 `scripts/wf_release_common.py` 等直接依赖。
- 规划阶段只写任务文档和任务元数据；用户批准最新方案后，在 DSH inline 主会话实施并记录验证。`prd.md`、`design.md`、`implement.md` 的规划口径不因实施而改变；实施/验证事实统一写 `validation.md`。
- 耗时不作优化/验收目标；保留命令有界终止、取消和锁竞争语义。保留现有公开模式、默认并发、模板缓存、SUT 异解释器、scope/锁/namespace 和已声明覆盖，不能用删功能、降覆盖或自动重试掩盖失败。
- 不改产品工作流/安装政策，不手改正式发行树，不改官方 Trellis 上游，不提交/推送/开 PR。激活与JSONL按 [activation.md](./activation.md) 在实际实施会话重新门控；不能把本次审查会话的平台写成长期事实，也不能用inline豁免绕过dispatch平台的上下文要求。
- 不保证宿主断电级持久性、内核不可回收对象、所有监督方同时消失后的自动回收、同 UID 恶意篡改防护；脚本仍须报告 unknown、保留现场，不得宣称已验证。真实宿主压缩维持既有 manual 范围。

## Background / 证据口径

前序分析在同一基线检查实现，并执行了 shell 语法检查、154 个定向测试及受控反例。154 tests OK 只说明已有用例通过；不是本任务修复证据。下面区分真实入口、持久化文件和内存模拟，禁止把模拟扩大为历史事故。完整出口清单见 [inventory.md](./inventory.md)。

| ID / 严重度 | 已确认事实与基线锚点 | 要求 | AC |
|---|---|---|---|
| R1 / P1 | `FULL/run_all.sh:825` 忽略 helper 失败，缺计数默认为 0；`FULL/runner_cleanup.py:37` 对空对象/缺字段返回空清单，错误类型可抛 AttributeError。内存模拟确认 helper 无输出失败后仍删除、记 cleaned | 清理证明只有完整且明确的 cleaned 才允许删除；缺失/损坏/崩溃统一 unknown，缺文件不能因 glob 没发现而消失 | AC01–03 |
| R2 / P1 | `FULL/run_all.sh:405,464` 在 `FULL/template_cache.py:382` 恢复前删 staging/backup；lookup 可绕过 journal。恢复判定模拟从 roll-backup 变为 fail-closed，未在真实缓存破坏性复现 | 事务恢复与遗留清理由缓存所有者统一编排；未完成 journal 先于命中/迁移/残留回收，失败保留恢复材料 | AC04–06 |
| R3 / P1 | `REPRO/_worker.py:58`、`FULL/execution.py:1149` 的 finally 不看 cleanup_state；unknown 模拟仍删除。`FULL/run_all.sh:289` EXIT trap、`FULL/execution.py:1104` 取消清理、`FULL/fixture_scope.py:91,249` 重用/轮转及 `scripts/tests/wf_runtime/test_run_all_contract.py:160` teardown 也是同类责任链 | 同一资源生命周期规则覆盖正常/失败/取消/异常/复用/轮转；未知时不提前删除、不抹证据；最终成功由外层监督完成后统一发布 | AC07–10 |
| R4 / P2 | `REPRO/run.sh:65` 缺值后 shift 2 不前进；真实 `timeout 0.2s bash .../repro/run.sh --mode` 返回 124 | 所有公开有值选项先完整解析/校验；缺值/空值/未知选项非零且不取锁、不建缓存、不启动 worker | AC11–12 |
| R5 / P2 | `FULL/results_summary.py:210` 先写 pending 再只改内存；前任务 `evidence/final-ext4-green/summary.json:48` 等四份成功文件均 pending | 最终落盘摘要、返回值、stdout/退出码一致；发布/读回/清理失败不能出现成功结论 | AC13–14 |

`FULL` = `scripts/tests/wf_runtime/full/`；`REPRO` = `FULL/repro/`；前任务 = `.trellis/tasks/archive/2026-11/11-16-wf-runner-evidence-isolation/`。相邻出口仅表示必须核验的影响面，不凭源码模式直接声称每个已发生事故。

## Requirements / 跨层收口

- R6：先建立“资源—创建者—实际消费者—清理责任方—证明—再进入行为”清单，覆盖主 runner、独立/内嵌 repro、install/fixture/init/test、isolated HOME、run-owned 模板、缓存事务与契约 teardown。无调用方可以自行用 rc=0 或路径存在代替 cleaned。
- R7：清理失败、目标失败、取消、证据缺失分别归因。资源已安全清理不等于目标通过；执行 rc=0 也不等于资源可删。正常失败且已 cleaned 可复用；unknown/failed/未完成保留记录不得自动清除后重跑。结果协议身份须在首次 owner 发布及每次执行意图发布时原子可识别；初始化中断、缺 run-state 或新旧记录不匹配不得降格为 legacy/plan-only。
- R8：采用最小的共用判定与单一最终收口者；不新增后台服务、通用工作流引擎、第二套进程监督/缓存恢复算法。每处新增状态都必须有生产者、消费者、缺失规则与终止出口。
- R9：现有测试保护和覆盖保持；新增断言必须击中旧缺陷，并同时覆盖正常对照与真实入口。范围内同类问题必须在本任务闭环，不能改名为 known-gap。不同类别的新需求另行审查，不无限扩张任务。
- R10：保守保留必须有可执行处置出口，不能把换新路径当旧现场已解除。历史归属与本次人工授权分开：可验marker的无journal材料可safe-legacy，新协议保留结果/owned fixture可TTY manual-retained。缓存坏/不可恢复journal可明确确认完整key reset，不要求手修损坏证据。**用户于2026-11-17确认**：历史wf归属无法证实的缓存材料仍标unproven，允许在路径、UID、锁、活引用等硬检查全部通过后，通过额外TTY与所选集合摘要确认显式放弃；确认含unproven-cache，不把名字/UID/位置改称历史归属。该规划决策不授权当前清理真实存量，实际处置每次仍须精确确认；自动/safe-legacy路径继续拒绝unproven材料。活锁/活进程、必要检查能力不足、非本UID/越界/受保护路径仍硬拒绝；人工确认不补cleaned、不授下次自动删除权。

## Acceptance Criteria

- [ ] AC01 / R1：有效 cleaned、unknown/failed、缺字段/空对象/数组/错误类型、缺文件/不可读/坏 JSON 各有行为断言；没有崩溃后二次异常或默认 cleaned。
- [ ] AC02 / R1：实际 root 的 Python 直接调用收口边界遇 cleanup/finalizer 异常、None/空对象、畸形类型/字段或 cleaned 与 pending 矛盾均非零，无 `GATE-OK`，现场未删；正常 cleaned 仍安全释放并成功。故障用受限确定注入，不能复建已移除的 shell stdout 协议来测试非零/空输出。
- [ ] AC03 / R1/R6：命令启动前登记；managed install/fixture/init/test/repro与root分别有证据，pending/缺终态不消失。无collector的direct API/CLI必写standalone receipt，只证明command；有scope核scope，无scope以显式log真实父目录为输出锚点，保留安全创建缺失父目录的能力；坏scope/managed不降级。原参数/rc/status/seconds及库异常语义保持，普通TemporaryDirectory、用户可写路径、相对log与目标cwd不同均有对照；权限/链接/类型错误及scope越界明确前置拒绝。run_one五列lines不扩列，receipt/invocation引用走同路径unit结果JSON；candidate_audit逐阶段精确核本次ID，prep失败/无test、unit JSON发布失败、旧JSON/旧绿行均不误通过。
- [ ] AC04 / R2：从真实 run_all 入口重入“journal 后未移旧、移旧未装新、装新未 repoint/meta、写 meta 未清 journal、首次发布半安装”状态，可验证旧/新代恢复成功；对原始字节与身份断言，非仅检查状态标签。
- [ ] AC05 / R2：lookup 可命中但 journal 未收尾时先恢复；无有效 journal 不按名字删未知目录；坏 journal、两代不可验证或恢复失败保留原材料并非零。独立只读 lookup 遇 journal 拒绝，不偷偷写。
- [ ] AC06 / R2：模板与测试发行缓存恢复后 marker/root/meta/tree 一致，重复恢复幂等；事务清理失败不删除恢复索引或假报收尾；sibling/无主/不相关输入条目不受影响。
- [ ] AC07 / R3/R6：repro 临时目录、isolated HOME、run-owned fixture/template 在 unknown/failed/执行异常时保留并报告原因；cleaned 的正常成功/目标失败可安全清理，保留原目标 rc/原因。
- [ ] AC08 / R3：根收口在execution.runner_control同C进程，正常/失败/取消/确定点G/S故障/helper异常/早退共用原run监督与单一finalize。lease持锁后一次调用Python begin_run写owner/state/prepare，controller只接管；三个初始化checkpoint归同一helper，不在controller重演许可。内层EXIT不提前删，不聚合未终态root；children-only诊断与最终root结论分域，root started正常不误报，真正缺失/unknown最终仍拒绝。G退出前无成功发布，信号/rc/FD及handler/mask恢复恰一次有行为对拍。
- [ ] AC09 / R3/R7：unknown/failed/未完成目录的自动复用/轮转/teardown在删旧证据前拒绝，KEEP不自动清，cleaned失败run可复用、纯计划可首次执行。首次/计划转执行/cleaned重用×三个初始化点由begin_run helper os._exit(97)确定死亡，不用raise；lease shell非零退出不启动controller/删现场。等待最外public退出后验证磁盘身份和实际FD/lease释放，不删锁；新入口不得降级legacy/plan-only，旧格式身份与生命周期分开。
- [ ] AC10 / R3/R7：最终清理/写结果/发布失败非零且可归因，进程cleaned与文件删除failed分开。真实finalize覆盖首删前失败和已删首项、第二项失败的部分完成：removed/failed/not-attempted、retained_paths与实际marker/剩余字节一致，停止后续删除、不重建已删项、不重试、不签成功；单根rmtree内部部分失败另有定向I/O反例。慢契约teardown的class-cost写失败不得吞掉：先完成进程/FD/宿主保护断言，再决定scope回收；证据写失败非零且保留scope/错误归因。原非零目标rc保留，原0转非零；正常/取消探针核owned进程/FD/锁，故障探针只清自建对象。
- [ ] AC11 / R4：每个 repro 有值选项的缺值、空值、后跟选项都确定非零终止；短 deadline 只作“不得卡住”的断言，不作性能考核；scope/缓存/锁/worker 无副作用。
- [ ] AC12 / R4：合法公开参数、重复 group、带空格路径、模式与内部 frame 原样保真；非法内部 frame 仍拒绝，正常独立/内嵌、dev/candidate 选择与租约语义保持。
- [ ] AC13 / R5：execution.runner_control唯一发布实际summary.json，summary_publish/path与返回对象一致，全对象读回；cleanup非cleaned或必需证据缺失不可status=ok。full metrics以schema1绑定本run_id/root/role及当前plan/context/lines/unit/repro输入摘要，原子交接并由唯一reader验证；controller按当前结果/策略派生gate和cleanup，不采shell旧计数签成功。summary含实际输入证据引用；full/repro投影固定，控制/摘要/最后finished同ID，旧无IDmetrics只作历史展示。
- [ ] AC14 / R5：publisher的write/fsync/replace/readback、真实root异常/非法返回，以及metrics旧代重放/缺失/截断/坏schema类型/错root或role/摘要错配/写失败均非零、无GATE-OK、不写finished-cleaned；原非零rc保留。metrics真实入口用有限scope故障点，不靠外部竞态；同plan同路径复用仍拒绝旧ID。陈旧unit/repro证据也拒绝；正常首跑/cleaned复用/目标失败/repro开关均有对照，保留债务及卫生门禁。完整失败可发布failed摘要，证据不全只写控制失败，不造完整成功摘要。
- [ ] AC15 / R6/R8/R9：inventory 每个出口有“已修或已有机制验证”的结论、对应测试与证据；同类失败在真实入口可被捕获；helper身份/fake-tree/schema/legacy/standalone隐藏receipt与所有枚举消费者和文档同步，无无主状态/未分类出口。
- [ ] AC16 / R9：T0、慢契约、full green 串并逐项等价、full both、candidate、发行只读复现/token parity、相关文档/资产校验通过；skip/未运行据实报告。耗时不计成败；范围内未关闭缺陷或证据缺口不得声明完成。
- [ ] AC17 / R2/R10：三材料inventory零写，覆盖journal前/后staging/backup、stale/build、marker-only壳、坏journal及unproven归属。模板按现有fixture marker判归属，新发行material-owner在build前发布；meta不作为staging必需证据，旧无marker不补owned。按已确认R10验证：safe-legacy只收可验对象；unproven缓存自动/safe路径拒绝，硬检查通过且本次额外TTY+集合摘要确认后才可manual-retained；缺确认/非TTY/坏摘要/漂移/忙锁/活引用/检查能力不足均零删除，不补owner。坏key完整reset后真实入口重建，部分失败保留journal，其他key/sibling不动。root维护前一次按实际根浅层observe给快照计数/容量未测/准确inventory命令，所有计划与per-case/内嵌零观察。
- [ ] AC18 / R7/R10：严格旧格式有主且无新协议痕迹的结果可safe-legacy退役；不把“没有 run-state”单独当资格、不改历史/制造state、不误用fixture owner。plan-only、新协议缺失/损坏状态、run_id不匹配、早期中断、死active、cleanup unknown/failed与KEEP不得自动退役；owner可验且必要检查通过后须有manual-retained TTY流程。默认缓存外的显式结果与逐项owned fixture也能盘点/选定；预览集合/容量/锁与liveness证据，输入路径+digest确认。漂移/非TTY/忙锁/已知活持有者/检查能力不足拒绝，不写cleaned；删除前安全创建外部报告，逐项记retired-manual。覆盖整批预检失败零删除、报告/删除I/O阶段部分失败停止并重盘点、同清单换新报告幂等重试；真实用户存量不自动迁移。保留并用新路径不能被计为旧现场已处置。unproven缓存按R10/AC17的已确认范围处置，不能扩展成无主结果或fixture的删除许可。
- [ ] AC19 / R2/R9：按 design 的 W1–W5（AC04五个恢复场景）+O1（AC17 journal前孤儿）+F1（AC06材料清完journal未删）七行，用六个不同checkpoint确定中断；首次/重建共享点但各有独立证据。模板W1–W5真从run_all重入，发行对应场景从ensure重入；保持各自恢复算法与摘要时机。总开关关闭不生效、越界拒绝，后代/锁收口，不外部kill猜时序；全部点与输入/fake-tree/审计条件影响列全。
- [ ] AC20 / R6/R9/R10：所有新产物有唯一登记及 prepare/prune/bootstrap/盘点/退役消费者规则，包含standalone隐藏receipt、metrics和unit_execution；`.json`已知不代表可删，receipt不冒充结果/fixture owner，commands pending/KEEP/错误仍阻断，无主含新协议产物不绕bootstrap。observe交接C2=disabled/零调用、C3=enabled/实际根一次，计划/per-case/内嵌始终零；原CLI不安全用法非零，激活按activation实际平台分支。

## 完成与审查标准

实施后单独编写validation.md，逐AC列反例/正常/命令/证据/限制；测试总数或机制存在不算销账。交付前核diff/untracked/staged，历史证据不改。R10的unproven缓存人工放弃范围已由用户于2026-11-17明确确认，原悬置的产品/风险取舍已解决。当前实现与验证记录见 validation.md；未执行提交/归档，策略确认仍不构成真实缓存的一次性或批量删除授权。
