# 设计：资源生命周期、事务恢复与最终发布

> planning / 未实现。需求与边界以 [prd.md](./prd.md) 为准；出口清单见 [inventory.md](./inventory.md)。

`FULL` = `scripts/tests/wf_runtime/full/`，`REPRO` = `FULL/repro/`。

## 1. 根因与最小结构调整

根因是清理权限、执行证明、最终发布由多个调用方独立推断。修复不重写 C→G→S→W、锁算法或两套缓存恢复状态机；收拢以下责任：

| 责任 | 唯一实现/拟落点 | 调用方职责 |
|---|---|---|
| 外层 controller、信号与最终出口 | `FULL/execution.py::runner_control()`，由现有 `main --runner-control` 分支进入 | 同一 C 进程调用原 run 监督 controlled/execute，再直接调用 runner_cleanup.finalize、results_summary；不新增进程/通用执行命令入口 |
| 执行清理证据、run 生命周期与产物分类 | `FULL/resource_lifecycle.py`（新增） | 纯判定 + 有限记录；共用产物登记，不 kill、不猜归属、不实现新监督器 |
| run 最终收口 | 扩展 `FULL/runner_cleanup.py` | 聚合 receipts、执行允许的 owned 删除、形成清理报告；由最外层 controller 调用 |
| 模板事务维护 | `FULL/template_cache.py` | shell 只调用维护/获取入口，不扫描 staging/backup |
| repro 公开 argv | `REPRO/cli.py`（新增 argparse helper） | shell 消费 shlex.quote 赋值/数组；内部 frame 仍由 runner_protocol 单点处理 |
| 摘要输入交接与最终发布 | `FULL/results_summary.py` | write_metrics唯一序列化内层测量，read_metrics核本run输入；build/publish只由controller完成最终对象一次原子发布+全对象读回 |

仅增加上述两个有独立责任的 helper，不新增后台服务、通用资源框架或重复清理算法。最终 GATE-OK 的发布从 execute shell 移至外层 controller，消除“内层先宣布成功、外层后发现监督异常”的窗口。

## 2. 共用判定与字段域

### 2.1 清理证据

`assess_execution(payload)` 是唯一解释 execution supervision 的函数。输入不是对象、缺 supervision、字段类型不符、cleanup_state 非 cleaned/unknown/failed、缺终态证明均返回 unknown 和明确 reason；只有结构完整且 cleanup_state=cleaned 才允许回收该命令所消费的资源。rc/status 另属目标结果，不推导清理许可。

- `cleaned`：监督方完成真实后代核验；目标可以成功、失败或取消。
- `unknown`：缺证明/未完成/损坏/监督失联/执行抛异常，禁止自动删除现场。
- `failed`：已经确认的资源回收错误，禁止签成功；保留尚未删除部分。

execution 的原始 supervision 与“本地资源删除”分开记录。文件删除失败不能把进程证明改成成功，也不能覆盖原目标 rc/原因；最终 rc 原已非零则保留，原为零则转非零，并附加 cleanup_error。

### 2.2 run 与 command 身份

新增 `run-state.json`（schema 1）：`run_id` 为每次运行随机 ID，`root` 是 canonical results，`role` 为 full/repro，`state` 为 active/finished，`cleanup_state` 为 unknown/cleaned/failed，附 reasons/retained_paths。active 不表示仍有活进程，只表示没有完整终态；缺/坏/active 一律不能自动删。

结果 owner 使用原路径 `.wf-results-owner.json`，新写采用 schema 2，完整字段为 `schema_version:2`、既有 `owner` 值、canonical `root`、`lifecycle_protocol:1`、`intent:plan-only|execution`、`run_id:null|本次ID`。plan-only 的 run_id 必须为 null；execution 必须有 run_id。它只证明协议归属和已登记执行意图，不证明清理完成；不得将缺 run-state 推导为旧格式。fixture 兄弟 marker 和测试发行 owner 不升级为此结构。

owner 的协议字段与意图在同一 JSON 原子发布，避免“先有旧 owner 后补新状态”的窗口；新代码的 claim/计划镜像/重用一律不得再写 schema 缺失的旧 owner。字段按明确类型/枚举核验，bool 不代替整数协议号。owner 临时文件完整写入前后、rename 前中断均按“没有完整 owner 的未知目录”保留，临时文件不作为 legacy 证明。schema 2 owner 在 run-state 缺失/损坏或 run_id 不匹配时判 incomplete-new/unknown；旧 owner **精确等于**基线 `{'owner': OWNER, 'root': canonical_root}` 且没有 run-state、commands/、新协议初始化临时文件、control/summary 中的新 run_id/schema 痕迹，才归 legacy-owned。legacy 仍没有进程已清理证明，只能在明确维护确认下退役，不能自动复用/轮转。未知/未来 schema、额外非法字段、被降级的旧 owner 混有新痕迹均 unknown，不猜版本。

字段唯一写者：resource_lifecycle.begin_run在lease bootstrap原子登记owner执行意图和active state并prepare；controller接管本ID并最终化state。execution.run写receipts，local责任方串行补local_cleanup/retained_paths；runner_cleanup派生清理报告，results_gate派生唯一目标gate报告，results_summary.write_metrics只做测量交接、build/publish消费已验证报告发布摘要。计划owner由同一lifecycle入口生成，不覆盖执行intent。retained_paths含explicit-keep或cleanup-unconfirmed；auto_remove_allowed只由生命周期判定导出，不持久化第二份许可。

每次 `execution.run()` 先确定下表证据域与规范写入点，在派生 G 之前原子写 started receipt，完成后同一记录更新 finished + execution 结果。`command_id` 每调用唯一，不按 command 名覆盖；managed记录带run_id，standalone明确无父代。写 started 失败则目标不得启动；写 finished 失败保留 started、非零归因。注册与完成由 execution 单点负责，CLI/直接库调用同一路径；不存在静默 collector-less 启动。

| 证据域 | 判定/归宿 | 对账与调用方 |
|---|---|---|
| managed-child | 有完整且可验证的 run_id、approved commands 根与 owner/state；写 run collector | run_one prep/install/fixture/init/test、repro worker 直接 execution.run、嵌套受控命令。缺项、不可写、错 run_id/域外均启动前拒绝，绝不 fallback standalone |
| root-control | 仅 runner_control 内部显式调用，已核 begin_run 与租约；started/终态在本 run 的 `.runner.json` | 原外层 C 监督 controlled shell；不把自己注册为待自己结束的 child。root started 也是“启动前登记”，不是豁免。collector 内孩子与 root 事实显式分域 |
| standalone-command | 完全没有 managed locator 且不是 runner-control；在 log 同目录写唯一隐藏 sibling `.<log_basename>.execution-<command_id>.json`，原子记录started/finished，`evidence_scope=standalone`、run_id=null | execution CLI不带--runner-control、test_execution/test_supervision直接run、candidate_audit单次run_one的各prep/test命令。`run()`返回evidence_path；CLI给定`--result`时写入引用，省略时在stderr给精确quote路径。hidden文件不匹配repro `*.json` case glob；cleaned result目录复用时，通过所有权与生命周期复验后由prepare清理已知隐藏receipt |

standalone路径与枚举兼容表：`repro_select.validate_repro()`只读取repro结果根的`*.json`，隐藏sibling不在该glob且日志通常位于logs子目录；`results_summary._result_lines()`只读lines；`source_hygiene`只扫描源码pyc；`candidate_audit.record_suite()`只读精确结果/output并由run_one显式带回本次receipt引用；`fixture_scope.prepare_results()`虽按JSON扩展名清理顶层文件，但只能在已核验previous run finished+cleaned后清理；prune删除的是已核验owned完整结果目录。实施需在该表逐项加行为测试，不假定“点号文件一定被每种未来枚举器忽略”。standalone receipt失败路径显式非零、日志可诊断；无权限目录由调用者可见拒绝，不能静默略写。

默认 API 的既有位置参数/返回 rc/status/seconds 保持；允许增加 evidence_path 返回字段、可选 metadata/context 关键字。standalone receipt只允许log同目录唯一隐藏单文件，不另建receipt目录、不扫历史同名记录。日志与receipt的路径准入由execution同一入口完成，先确定证据域，再按下表确定边界；任何已声明但无效/不完整的scope或managed上下文均拒绝，不能清除定位后降级无scope。

| 调用上下文 | 日志/receipt的路径边界 | 正常与拒绝行为 |
|---|---|---|
| 有有效WF_TEST_SCOPE_ROOT的standalone | 既有scope marker验证后的canonical scope；log与receipt必须在其中 | scope内正常临时路径继续成功，越界/坏scope启动前拒绝 |
| 无WF_TEST_SCOPE_ROOT、无managed定位的standalone | 调用者显式log路径的真实父目录是本次输出锚点，不要求wf owner/结果scope | unittest TemporaryDirectory及用户可写目录均合法；不推导HOME/cache为默认证据根，不声称该锚点是沙箱或删除授权 |
| managed-child | 经owner/run_id/租约核验的collector与批准日志路径；有测试scope时另核scope，namespace按既有合法bind验证 | 不因namespace剥离scope而误降级standalone，也不把collector授权扩大到任意宿主路径 |

无scope的相对log路径在进入目标cwd前相对调用者cwd固定；无论有无scope，逐组件拒绝symlink/非目录父路径、最终symlink/非普通日志和跨锚点替换。保留原run()可创建缺失日志父目录的能力：先固定最近已存在的真实祖先dirfd，再只创建所请求的缺失目录链；有scope时祖先/新目录均在scope内，创建后固定最终父dirfd，log/receipt以相对文件名及O_NOFOLLOW操作。receipt以排他首次创建与同目录原子替换完成，不覆盖别的记录；并发同log的日志本身仍由调用方避免，receipt各自唯一。`--result`若给定也按对应输出域核验，不能因receipt安全而继续跟随result链接。写started失败不启动，写finished失败保留started并非零。库保持现有参数校验/路径OSError异常语义，不为“结构化非零”吞异常或伪造成功结果；CLI将异常转有归因的非零。

这套边界区分有scope的测试隔离与无scope的显式输出授权：先盘点direct/API/CLI、audit、假树全部调用方，普通test_execution/test_supervision的无scope绿路径不能靠迁到scope逃避兼容验收；仅需故障注入的用例按本文5.2另建有效scope。两种正常路径、缺失父目录、relative log/目标cwd不同均有成功对照；不可写、坏scope、scope越界、symlink父/日志/result、目录类型错误均前置拒绝。AC03/15核行为兼容，签名/字段兼容不能代替。

run_one的`lines`继续严格五列`name/rc/elapsed/status/tail`，不加列、不把receipt藏进tail。结构化传递只使用既有`<unit>.test.log.json`：成功执行时保留execution原字段，run_one结束后经lifecycle的单一unit-result写入口原子附加`unit_execution`（schema1，unit、invocation_id、run_id（standalone为null）、state、result_row、command_evidence）；prep失败也在同路径写`state=prep-failed`与实际失败阶段，不伪造test的supervision/断言。result_row保存实际五列投影，供audit与当前lines互核，不能单独证明命令执行。

run_one入口固定一次invocation_id：candidate_audit在启动前生成并作为metadata交入，普通runner由lifecycle生成；managed还绑定本run_id。run_one为实际路径的install或fixture/init以及test每次调用显式传`--result`，prep结果用既有logs目录内含unit/phase/invocation_id的唯一JSON路径，test仍用原结果路径；command_evidence按执行顺序列phase、command_id、evidence_path及对应CLI result路径，不靠glob。跳过的阶段不造receipt，启动登记失败要在unit结果中记明确preflight-failed且无虚假command_id；任何必需阶段无合法证据不得审计通过。test CLI退出、原结果读回后才由run_one写unit_execution，无并发写者；unit发布失败使run_one非零且不能回用旧结果。五列行可报告bad，但不足以替代JSON证据。

candidate_audit.record_suite显式接收预期invocation_id，读取精确unit结果/各阶段引用并核schema、unit/phase、命令身份和实际五列行，不能从陈旧JSON或最后一条同名绿行猜本次身份。run_one实际runner_rc非零同样不许签通过，即使已有unit JSON和旧行看似正常。完整非零的prep/test结果允许报告失败，但pending/local unknown或缺阶段不能签审计通过。standalone preparation（生成candidate/template）仍用已有同步步骤与锁，失败原样退出；若audit位于父run内则继承有效managed collector，不清除它。增加的unit_execution只升级此JSON命名空间，不升级lines协议；candidate审计记录注明所消费的unit evidence协议，历史记录只读展示不可冒充本次证据。T0 mocks须模拟receipt与unit JSON写失败/完成。

- managed命令继承 `WF_COMMAND_EVIDENCE_ROOT` 和 run_id，standalone按表独立定位。run_one prep/install/init/test、repro phase 都自动有记录，不再依赖 `*.test.log.json` glob 作为全集。
- lifecycle只枚举本run的commands/作为managed-child集合，按receipt域/ID逐项核验，不追加`.runner.json`，也不吸入standalone隐藏文件；未知/错域子记录报错，不静默忽略。外层controller的终态由finalize显式参数接收，避免读取未来自身结果；execute前构建/安装仍受外层监督，不能凭“没有receipts”确认成功。
- 内层execute移除原runner_cleanup聚合/cleanup计数分支，不再把`.runner.json`的正常started当unknown写入metrics或影响目标rc。若需要命令诊断，只调用同一children读取投影，标children-only/nonfinal，不能命名run cleanup、签cleaned或等待root；最终root缺失/unknown仍由外层终态判定拒绝。离线CLI复用同一分域，active根只能报告in-progress/nonfinal，不能因为排除了root而返回完整run成功。
- receipts 目录是 runner 管理写入口，必须 scope 校验；namespace 使用既有 results bind，不借宿主 FD；嵌套假 runner 清 locator 后建立自己的 run 身份。
- 同一文件的 started→finished 原子替换可重复读取；缺终态默认 unknown。主池 plan/lines 完整性继续核缺单元，repro bundle/records 继续核缺 case；ledger 负责已启动命令的清理完整性，三者不能互相替代。

本地资源有第二步完成条件：HOME/TMPDIR 的责任方在启动前声明到该 command receipt，`local_cleanup` 初值 pending；execution.run 只完成 supervision 部分，随后由调用方通过同一 lifecycle helper 把 local_cleanup 写为 removed/retained-keep/retained-unknown/failed。父聚合遇 local pending/unknown/failed 必须保留，不能仅看 supervision.cleaned。每个 receipt 一次只由该命令调用方进程写，其他进程只读；在 supervision 与 local 完成之间死亡仍留下 pending。资源创建后、登记前失败由本调用方保守保留并归因，不启动目标；root 在父监督完成后聚合，不与活 writer 竞争。

## 3. 谁在何时清理

### 3.1 root 收口

```text
lease / begin_run: 检查旧 run 或 plan-only 许可
     → 原子发布 schema2 owner（execution + 新 run_id）
     → 原子写同 run_id 的 active run-state → prepare 旧产物（保留本代 owner/state）
outer execution controller: 核验并接管已登记的 run_id → 只读 observe 本次配置缓存根
     → 持既有锁/监督 controlled→execute
execute: 构建/单元/repro → 当前结果gate与原子metrics交接（本文6.1），输出中间诊断，返回目标结果
outer: 收 G 最终结果并等待退出 → 聚合本 run receipts
     → 未确认则保留；确认则 owned 删除 → 写控制/清理结果（run-state 仍 active）
     → 完整证据时发布并读回 summary → run-state 最后写 finished
     → 只在全部成功时 GATE-OK
```

内层不发布最终摘要/成功，也不在 EXIT trap 删除；trap 只请求取消并退出。外层正常、目标失败、取消/timeout、可捕获异常共用 finalize。若 controller 被 SIGKILL，active 记录留下，下一次不会自动删除现场；这是保守失效，不许靠 PID 猜测重新放行。

begin_run 在任何旧产物删除、结果目录内 pycache/日志/计划计数、fixture 创建和目标进程启动前登记 execution 意图；结果目录 mkdir 后的首个正式记录就是 schema2 owner，不能先写旧格式 owner。旧代是否可删除在同一持锁函数中先验证并保留原事实；写新 owner 后即使旧 run-state 尚在，run_id 不匹配也必须 unknown。`prepare_results` 不得把本代 owner/state 当普通 JSON 清掉，也不提供“传一个 run_id 即可继续清理 active 目录”的公共恢复入口；只有本次 begin_run 不中断的执行可按刚核验的旧代事实清产物。中断后重入不能重演该删除许可，须改用新路径保留旧现场。

public/lease 的 Python helper 在 begin_run 返回前继续禁写 pyc（-B/PYTHONDONTWRITEBYTECODE），不能因 layout 已通过就提前启用用户指定的结果内 WF_PYCACHE；批准的 pycache 只在 owner/state 已完整后启用。目录检查/lease/版本解析都不能先产生结果日志或调用原 claim 的旧格式写法；测试要覆盖这些真实 shell 调用点，而非只单测 begin_run。

begin_run 死在 owner 前只留下空/无主/临时文件目录，不存在新 active 执行；死在 owner 后/run-state 前留下可识别 execution 意图，inventory/retire 必须拒绝 legacy 分类。plan-only 转执行和 finished+cleaned 旧代复用同样先换 execution owner，再写 state/prepare，避免死亡后又被视为计划目录或上一代 cleaned。bootstrap 尚未交接 controller 时的可捕获失败非零并保留意图/状态；不会为补全记录猜 cleaned。这是单份 owner 与 state 的有序失效，无新增 sidecar。

取消请求只由 root 初始化一次；内嵌 repro 不得 rm 父 cancel-request，也不得重置已 latched 的取消。finalize 阶段重复 INT/TERM/HUP 仍走既有信号保护，不允许在删除与最终证据写入间触发第二条收尾路径。

外层先保留原始控制结果，再最终化资源状态；写任一必需证明失败非零。root 自身 cleanup=cleaned 与所有子 receipt cleaned 都满足，才执行 run 级自动删除。任何 child unknown 不因外层 rc=0 而被覆盖。早期 release/plan/prep 失败没有完整结果时，写控制失败/保留记录，不填造完整 summary；原错误必须可见。

最终化失败时 active 记录继续阻断复用/轮转；若能写出明确 finished+unknown/failed，也同样保留。证据完整的目标失败可写 finished+cleaned（目标仍 failed），允许下一轮安全复用。可捕获的收口异常只报告一次、不自动重跑删除；controller 直接使用已有 plan 与 owner 校验，不接受任意清理路径参数。

controller 直接消费 `runner_cleanup.assess_run()` 的结构化结果，抛异常、None/空对象、错误类型/字段或“cleaned 但仍有 pending/unknown”矛盾一律 unknown；先完整核验再删除。full shell 不再 eval helper 输出作为删除授权。独立 runner_cleanup CLI 仍可读报告并以 rc 区分失败，但根入口不依赖 CLI stdout，因而不为 AC02 重建非零/空输出子进程边界。

### 3.2 controller 的实现和进程边界

选择**扩展现有 execution.py --runner-control**。该分支在 `main()` 的通用 command CLI 逻辑之前进入 `runner_control(args)`；保留 C→G→S→W 拓扑，C 仍是 lease shell exec 出来的同一个 PID。不新增 Python controller 文件，不选择 bash 串调 helpers，不将收口放入被监督的 W。`runner_cleanup` 和 `results_summary` 仅在 root 分支内延迟导入；通过参数传入执行结果/取消事实，避免 execution↔runner_cleanup 顶层循环导入。

| 组件 | 输入、职责和固定调用点 |
|---|---|
| run_all/repro root lease 分支 | 已持fixture→results lease后，仅一次调用lifecycle.begin_run入口，唯一执行者是该Python helper：核旧代、写owner/state并按刚核旧代许可prepare；shell只消费成功返回的run_id，失败立即退出。其后冻结plan/args并传`--runner-role`（full/repro）、规范根、run_id、摘要及原FD白名单，exec同C的execution --runner-control。此阶段允许上述初始化/准备写入，但不执行run终态finalize/删除或发布成功；不是“全程只读” |
| execution.runner_control | 验祖先/fixture+results lease、owner/run_id、冻结输入和 FD 集合；安装共享取消作用域 → root started → observe（维护子任务完成后启用）→ run 监督 controlled → wait G/DONE → 原始控制事实 → 调用 finalize → 摘要读回 → run-state 最终化 → 输出最终结果/返回码 |
| runner_cleanup.assess_run / finalize | assess_run 是纯聚合（root + child + local + plan/bundle完整性），finalize 先核结果再按已有 fixture_scope 入口删除 owned 资源；返回严格报告，禁止自行打印 GATE-OK/调用 exec 或 kill |
| results_summary.read_metrics / build / publish | controller传预期run_id/role/root和冻结输入；full验证本文6.1的metrics交接并独立核当前结果，给最终cleanup/gate/control后发布schema3。独立repro按其本代bundle/records投影，不强造full metrics/units；不从shell指标采纳cleanup/成功结论 |

`runner-role` 仅 full/repro，无任意扩展 role；candidate_audit 用 standalone receipt，不新增 audit controller。full plan 校验继续使用 execute_gate 的冻结契约；独立 repro 在既有 runner_protocol 的类型化 frame 中冻结公开解析后的 args，controller 按相同摘要与真实租约核验。root 自动删除的路径只从已核 plan/role 的固定位派生，不从 shell env 的任意删除列表读取。

信号由 execution 内部 `CancellationScope` 唯一管理：普通 run 自建作用域；runner_control 在整个 observe/run/finalize/publish 外建立作用域并让 run 复用同一对象，内部 run 不提前恢复 controller 的 mask/handler。进入任何监督前先保存目标原始 signal policy；传给 W 的仍是该原始策略，不能把 controller 的 latch handler 当目标策略。INT/TERM/HUP 只锁存首次取消；run 阶段走现有 CANCEL 协议；最终化阶段重复信号只记录不重入 finalize。恢复外部 handler/mask 在 controller 完整出口之后，所有分支恰一次。

C 本身保留 fixture/results FD 直到输出/退出；传给 G/S/W 只沿既有白名单和 namespace scrub，不把 control socket 或 root collector 锁借给 standalone。release 独占 FD 由 controlled 的 release_context 持有到其退出，C 最终删除仅 run-owned 资源，不改 release/template cache；不因最后发布再取 release 锁打乱锁序。

返回码规则：原目标/取消 rc 非零时保留，清理/发布错误另记；原 rc=0 遇取消/不完整证据/清理/发布失败转非零。只在 root/control、全部 child/local、计划/结果和发布/readback/finished 一致时输出唯一 GATE-OK（full）或最终 repro 成功。shell 的汇总行仅诊断，不再有成功承诺。repro state writer 只有真实相位与 cleanup=cleaned 才可写 proof；最终发布失败不补签整个 run 成功。

这不是多文件事务原子性保证：控制结果→summary→run-state 有序发布，任何中断仍 active/unknown 阻断成功和复用；不为失败重写已经发布的历史 payload。不完整 early failure 可只写控制失败并保留资源，不制造完整 summary。实现中的每个步骤与异常出口由本节固定，不能在执行期改选另一种 controller 架构。

### 3.3 独立与内嵌 repro

- 内嵌 repro 使用父 run_id、receipts 根、release context；不另起 root controller，不发布父 summary。相位资源由 worker 按同一证据判定清理，run 累计结论交父 controller。
- 独立 repro 按 public 解析/layout → fixture/results lease → begin_run 先登记新协议执行意图/state 再 prepare → controller 接管并 observe 配置缓存根 → controlled 取 release lease/准备发行 → execute 选择/worker/gate/writer。与 full 同序，发行构建失败也在已有 controller 边界内。复用 runner_protocol 的严格内部 frame，增加独立 repro 的阶段字段（entry PID/results/run_id/发行定位；产生 context 后再加摘要），验证真实祖先和租约；不再加环境 ready 位作授权。阶段输入均用类型化 argv，不新增任意命令执行入口。
- 锁顺序 fixture→results→release、模式选择、父 context 零 ensure/check 约束保持。CLI parser 不处理内部 frame，frame 先由 runner_protocol 剥离；新保留标记仍为 `--_wf-*`，公开 argv 拒绝。
- root 之外的独立 execution API 不创建 full/repro run 目录，但必须按本文 2.2 写 standalone receipts；同一判定保护自己的 HOME 等资源，返回证据引用与保留位置，只证明该 command。managed 上下文不完整不是 standalone 条件。

### 3.4 local 临时目录与 teardown

- isolated HOME：先保留执行结果，再按 assess_execution 决定删除；执行抛异常也保留，删除异常附加诊断，不覆盖原失败。沿用既有fixture owner，但每次采用本command_id的唯一新HOME，不再reset前次同log的保留HOME；ID由execution单点预分配，初始化owner后才写内容/登记local pending/启动目标。
- worker 相位目录：只有 cleaned 才删除；unknown/failed/异常保留，record 写 retained_paths。`WF_REPRO_KEEP=1` 保持用户显式保留，不能把 KEEP 写成清理 unknown。
- harness `_STAGED`：由 worker 在相位环境下发 defer-cleanup；`H.main` 不在目标退出前删这些目录；所有 stage 在 worker 的相位 TMPDIR 内，由 worker 在监督核验后统一处理。手工直接 case 无 worker 清理许可时保留并报告 staged 目录（仍执行原断言，不伪造清理成功），推荐公开 repro runner 负责自动回收；不在 harness 内复制进程监督/后代扫描。stage开始复制前用既有fixture_scope入口建立唯一新owned根；显式 KEEP 始终保留。
- 慢契约 teardown：先检查本测试 owned 进程/FD 与生命周期证据，异常或 retained 就保留 scope 并报路径；测试外边界按自建 PID/启动身份回收故障探针对象，禁止杀宿主对象。正常无遗留 scope 可回收。

每个新保留local目录必须归入“owned结果树内的后代”或“有独立fixture marker的精确根”，retained_paths同时给出此归属锚点；worker TMPDIR/_STAGED可随被明确选定的结果树处置，独立HOME/direct stage可单独选择fixture-only维护。local生产者先验证已继承fixture lease；standalone CLI/direct harness没有祖先lease时沿用既有fixture锁取得并持有到本调用退出，忙则创建内容前拒绝，不能在results锁后反向新取fixture锁。不新增每目录锁算法/owner schema；marker前中断只留空壳，marker后中断仍可精确盘点。旧无主非空临时树不追认owner。C2交付归属/唯一性/租约，C3按4.2提供相同manual-retained出口，不能只给结果目录退出而遗漏local现场。

## 4. 复用与轮转：保留必须跨下一次运行成立

| 上一代 | 自动 prepare/reuse | prune / teardown |
|---|---|---|
| 无主非空 | 原有 owner 拒绝 | 不删除 |
| 新空目录 | 允许 claim/初始化 | 不作为历史 run 处理 |
| 新协议纯计划目录（schema2 intent=plan-only，顶层仅 owner 或 owner/plan.json，无临时残留/执行产物） | 允许首次实际运行；先原子改execution owner，不用plan-only覆盖执行意图 | 不自动prune；操作者不再需要计划时可用本文4.2的manual-retained显式放弃 |
| finished + cleaned（目标可 failed；schema2 execution owner 与 state/control/summary 同 run_id） | 先核旧代，再登记新意图/state 后清旧产物 | 保持正常 owned 轮转 |
| active / unknown / failed / 坏状态记录，但结果owner可验 | 不恢复旧执行；保留证据并改新results路径 | 自动prune/teardown拒绝；停止消费者并通过完整复验后可manual-retained显式放弃 |
| schema2 execution owner，state缺失/损坏/不匹配（含初始化早死） | incomplete-new/unknown，不降级plan-only/legacy | 自动清理和safe-legacy退役拒绝；经本文4.2独立人工授权流程可退役，不补签cleaned |
| 严格旧 owner、无任何新协议痕迹 | legacy-owned 仅为格式归属；不自动采纳 cleaned，旧 owner+plan 也不视为新纯计划 | 普通 prune 跳过并提示；本文 4.2 确认退役，不回写历史 |

用户explicit-keep即使进程cleaned也不得由普通复用/轮转/teardown删除；run-state保留reason并提示新路径。KEEP可由操作者在manual-retained模式明确放弃，绝不由脚本静默清标记。无KEEP的finished+cleaned维持普通回收。

局部目录曾保留时，不允许下次 `prepare_results` 删除 logs/JSON 抹证据，再把新代冒充旧代已安全。新运行可选择新结果目录；旧资源按本文 4.2 的处置流程核验，本任务不提供“强制视为 cleaned”的开关。

显式 `--list/--dry-run` 的 plan 镜像只能写新空目录/上述新协议纯计划目录；任何 execution 意图（包括缺 state）、旧格式或不明目录都拒绝镜像，不以改成 plan-only 覆盖恢复定位。普通无显式 results 仍零锁零写。plan-only 可写范围保持 schema2 owner+plan，不为计划创建 run-state/commands；计划文件未落而 owner 已落时，仍是 plan-only，不假称执行过。

### 4.1 产物登记和 bootstrap

`resource_lifecycle` 持有结果产物的唯一结构登记（文件/目录、所属阶段、是否含生命周期证明），供 prepare、prune、bootstrap 和 inventory/retire 共用；不再各自加一份名称白名单。

| 产物 | 生产者 | prepare/reuse | prune/bootstrap/存量盘点 |
|---|---|---|---|
| schema2 owner + plan.json | lifecycle claim/plan/begin_run | owner 意图与协议同时写；仅精确新 plan-only 可首次执行，execution 缺 state 不可降级 | 协议/意图先判，不将 owner 推导为已清理；严格旧格式只可确认退役 |
| run-state.json | begin_run 初始化、controller 接管最终化 | 完整 finished+cleaned 且无 KEEP，才可开始新代 | 登记为已知 JSON，必须解析身份/状态，不能只凭扩展名 |
| commands/ | execution/lifecycle | 完整终态且 local 无 pending/unknown/failed/KEEP；清旧代前对账 | 逐 receipt 验 run_id/类型/阶段/清理证据；无主/坏子记录禁止自动删 |
| summary-metrics.json及同目录临时写入 | results_summary.write_metrics（内层调用）、read_metrics（controller读） | begin_run在许可prepare时移除旧代文件/临时写；新写schema1绑定run_id与输入，未知版本/缺坏文件不得默认值放行 | 登记为测量交接，不是cleanup/目标成功证明；旧无ID文件只读展示，manual处置随结果根 |
| `<unit>.test.log.json`的unit_execution及logs内prep CLI结果 | execution写命令result；run_one串行调用lifecycle追加unit终态 | 许可prepare清旧结果/logs；新命令从当前invocation精确引用，不glob历史；prep失败也覆盖为本代明确失败对象 | unit_execution schema1单独登记，消费者含audit/controller/summary/fixture_scope/fake-tree；lines仍五列 |
| standalone execution receipt（隐藏同目录JSON） | `execution.run`唯一写started/finished；无collector时由调用者显式log父目录定位，managed不降级；command_id唯一 | 有scope按scope、无scope按显式log真实父目录；prepare只在已核验结果许可时清本代已知receipt，普通目录/历史receipt不按文件名前缀扫删；repro/summary/coverage/candidate audit均按精确引用或既有glob规则排除 | lifecycle登记`evidence_scope=standalone`、run_id=null、command_id/路径/状态；inventory只读展示，retire不把receipt单独当结果/fixture owner；缺/坏/未终态阻断对应command，不伪造root/cleaned；结构登记含路径域/生产者/reader/清理/缺失规则，C2按本行成组更新 |
| .runner.json、summary、lines、logs/repro/template 等原产物 | 对应既有 writer | 经同一 run 许可再按各自角色重置；内嵌 repro 属父代，不新造许可 | 原有命名兼容，数据只作本来角色的证据；不能扩大成删除授权 |

当前 `_bootstrap_eligible` 的 `.json` 分支已认识 run-state.json；实际缺口是 commands/、阶段语义和跨消费者对齐，不能误写成所有新增产物均不识别。`prune-results --bootstrap` 保留解析兼容，但不再凭“顶层看似已知”删除无主目录：无主项只报告 `needs-retirement-review`，提示本文 4.2 的盘点入口；有此类未处置对象时返回非零，不把“只盘点未删除”报成 bootstrap 已成功完成。即使新协议 run-state/commands 看似正常，也不能替代 owner。历史确认只在明确的维护操作中发生，不让 bootstrap 绕过 active/KEEP。

### 4.2 统一的盘点—分类—处置契约

本节区分两种事实：**历史归属证据**决定能否把材料称为wf产物，**本次明确授权**决定操作者是否放弃精确选中的现场。UID、前缀、位置或mtime不能冒充历史wf归属；manual-retained不补造owner/cleaned，不授予普通runner删除许可。维护CLI与README须同批交付，以下均为拟实现。

**规划决策已于2026-11-17获用户确认**：允许对历史wf归属无法证实的缓存材料，在路径、UID、锁、活引用等硬检查全部通过后，通过额外真实TTY与所选集合摘要确认显式放弃。本节unproven-cache分支据此进入C3实施/验收范围；每次实际删除仍需其自身确认，规划确认不能替代该步骤，也不授权当前清理真实存量。历史归属始终保留unproven，不因此转成safe-legacy/自动清理对象；结果/fixture的owner要求不变。

| 材料 | 只读盘点入口（拟） | 精确处置入口（拟） |
|---|---|---|
| 结果/独立fixture | `fixture_scope.py inventory-results <cache-root> --format json`；精确模式 `inventory-results [--results-root <root>] [--fixture <path> ...] --format json` 至少一项 | `fixture_scope.py retire-results --selection <selection.json> --retirement-mode <safe-legacy或manual-retained> --confirm-retirement` |
| 模板缓存 | `template_cache.py inventory --cache-root <root> --format json` | `template_cache.py retire --cache-root <root> --selection <selection.json> --retirement-mode <safe-legacy或manual-retained> --confirm-retirement` |
| 测试发行缓存 | `wf_test_release.py --inventory --cache-root <root> --json` | `wf_test_release.py --retire --cache-root <root> --selection <selection.json> --retirement-mode <safe-legacy或manual-retained> --confirm-retirement` |

所有manual-retained另必填`--report <outside-report.json>`。三个材料所有者各自执行归属/锁/事务检查，lifecycle只共享结果分类与选择格式，不新增helper或通用事务框架。

#### 4.2.1 盘点与归属等级

inventory纯读，不恢复、不取修改锁、不写pyc/sidecar，只输出JSON。每项列canonical根/路径、材料域/类型、owner证据或`provenance=unproven`、UID/文件身份、有效journal引用或坏journal原始摘要、当前状态、容量/快照摘要及允许动作/阻断原因。未知归属不填owned，不可读/变化是unverified，不填0或授处置权；大小/摘要不跟随symlink。shallow观察仍按4.3不求完整容量。

| 无有效journal材料 | 可验证归属的机械判据 | 允许动作 |
|---|---|---|
| 模板staging/backup | 既有fixture_scope兄弟marker是普通文件，精确匹配OWNER与该材料canonical root，材料/marker属当前UID；无有效journal引用 | 可safe-legacy。meta不是材料归属的必要条件；模板_build已有reset(staging)，不能误称journal前没有marker |
| 新发行staging父目录/backup | 本文5的独立material-owner匹配owner tag/schema、material root、entry root、version/txn/kind/UID及命名位置；原entry.owner的root不能当backup归属 | 可safe-legacy；只证明材料归属，不证明完整发行 |
| 历史发行staging/backup或stale/build | 没有上述marker则unproven；仅名字/位置、缺journal或有payload不补足证明 | 不可safe-legacy/自动删；仅缓存manual-retained可明确选择放弃，预览直说归属未证实 |
| 空真实构建壳 | 当前UID、无引用、确实为空，不把链接当空目录 | 确认后仅rmdir，非空拒绝，不退回rmtree |
| 严格旧owner结果 | owner/root精确旧对象，无任何新协议痕迹 | safe-legacy；无state本身不是旧格式证明 |

safe-legacy拒绝新协议保留结果、有效或坏/未知journal阻断的缓存key和unproven非空材料，不修改历史身份。有效可恢复journal优先所属acquire/ensure；inventory/retire不隐式恢复。

selection由操作者显式从inventory选择，无通配/年龄/任意代码字段。JSON给entries与可选取的selection projection，包含domain/root/path/kind、provenance、文件身份/快照摘要及需要时的key/group；README给完整结构/命令。cache扫直接子项；结果精确模式与cache模式互斥，允许fixture-only，逐项核marker，不跟旧plan推任意删除集合。selection/report在删除集外，有scope时也须在scope内；输入字段不是权限凭证。

#### 4.2.2 共同硬门禁与人工授权

所有修改型维护按fixture→results domain→release（仅发行需要）取既有非阻塞锁；一个材料域一批，发行多key锁按canonical key排序，固定锁永不删除。整批复验canonical路径、UID、可验owner或明确unproven分类、文件身份/快照、有效引用、协议生产者与当前UID进程的FD/cwd引用。记录PID连同启动身份核验，不读环境/原始argv，不因无关跨UID不可见进程无条件阻断。本UID必要检查不可完成仍拒绝；不承诺证明不守锁的外部消费者或恶意同UID竞争不存在。

引用核验仅排除维护进程自身为本次安全遍历/取锁而打开的已登记只读FD，不把这些FD误当活消费者；调用者shell、其他进程及其cwd引用不在排除范围。确认前后同一集合/文件身份复验；若目录含挂载点、跨UID内容或无法稳定枚举的对象则拒绝，不因缓存reset扩大递归边界。

忙锁、已知活持有者、非本UID节点、不可读/不稳定快照、受保护根、固定.lock、跨域/链接或挂载逃逸、重复/祖先子项重叠均硬拒绝，不按坏journal字段扩选择。结果/fixture仍须可验wf owner；唯有下述**缓存unproven的人工放弃**是独立授权，不是坏owner兼容成合法owner。确认不覆盖硬门禁，任一预检失败整批零删除。

manual-retained必须真实TTY：展示完整canonical集合、归属缺口、容量/摘要、锁/FD结论、将丢失的证据；确认短语含所选根、集合digest与`abandon`，unproven缓存另含`unproven-cache`以明确承认归属未证实。非TTY/EOF/空错答案/漂移均零删除，无yes/环境/--force替代。这是本次对精确材料的处置授权，不能被自动prune或下一run继承，不保证历史执行cleaned。

| manual-retained范围 | 必需证据/人工选择 | 完成出口 |
|---|---|---|
| schema2 plan-only/incomplete-new/死active/cleanup unknown或failed/KEEP结果 | owner可验；逐项owned fixture可附或单独选，无run_id明确N/A，不伪造结果owner | 明确放弃，不续旧run/补cleaned；换新路径只允许继续工作，不计旧现场已处置 |
| 坏/未知schema/两代不可验证journal的缓存key | 显式cache-root内一个key的完整reset集合：entry、原owner/meta、可识别材料及marker、坏journal原件；节点当前UID/快照稳定，归属不足逐项unproven并额外确认 | 不修journal，不从坏字段执行路径；全组材料成功删除后才删journal，解除该key阻断，下次真实入口重建 |
| 无journal历史unproven缓存材料 | 仅inventory识别的staging/backup/stale/build精确项，由操作者主动选择；名称仅缩候选面，不证明归属 | 放弃所选材料，报告保留unproven事实，不改标safe-legacy/owned后自动删 |

缓存reset集合由所属模块按key固定路径规则与实际根内索引产生，坏journal不能指定根外对象。其他有效journal引用所选材料则拒绝；同key可识别残留须全列入确认，不能只删坏journal留下隐含可命中的残代。无关key/sibling不动；无法归key的stale/build可单独选择，不虚构entry/txn。整个cache根永不可删，此模式不是自动整根清空。

#### 4.2.3 写序、部分失败与README操作流程

首删前安全排他创建外部report，保存selection/授权等级/坏journal摘要；需留原件由操作者先存集外。创建失败零删除，不覆盖旧报告/跟链接。逐项记removed/already-absent/failed，人工终态retired-manual，不回写旧state/summary/owner。缓存reset先材料、再marker、最后journal；任何删除或后续报告写失败即停下/非零，尽力stderr报已完成集合；仍在的journal继续阻断，缺终态须重盘点，不承诺原子回滚或预知未来I/O。

重试用新报告：已不存在幂等，残留摘要/集合变动须重盘点重新确认，不凭原授权扩删。owner/material-marker只在对应树确认不存在后移除；journal最后删失败可经完整重盘点销账。retire不自动杀进程，不移动活引用路径，不造历史证据、不把放弃当目标通过。

README须给结果保留、缓存不可恢复、历史unproven三份完整示例：新路径继续工作→inventory审集合/归属缺口→证据存集外→按PID+启动身份停止自有消费者并重验→本机TTY确认→报告/重盘点→缓存reset后真实入口重建。检查能力不足先修访问；原证据损坏不要求手修可信journal，改走明确放弃。普通runner只提示盘点命令，不替用户选真实存量或调用manual-retained。本任务仅在自建scope与PTY验证，未获真实用户缓存删除授权。

### 4.3 自动维护的残留观察与提示归属

`runner_cleanup.observe_roots()` 是一次实际 root 运行的唯一观察编排者，由 root controller 核验 begin_run 的 run_id 后、进入 controlled 的 release/模板维护之前调用一次。它调用三个材料所属模块的只读 `observe(root)` 适配器，复用 inventory 的**条目分类**，不调用带恢复/取锁/写盘副作用的 acquire/ensure/CLI。适配器扫描根，编排者负责去重、汇总和向 stderr 输出；`resource_lifecycle` 不另扫目录。**交接状态明确为二态**：C2完成而C3尚未交付时，调用位存在但`observe_roots`能力标记为`disabled`，root不调用适配器、不输出残留计数（计数=0仅表示未启用，不表示根为空）；C3接线完成并通过自身定向验证后，才切换为`enabled`并按本节一次浅扫。C2的V-CONTRACT预期为0次调用，C3/父最终预期为启用配置根各一次；不能用no-op读取或“有warnings字符串”伪装两种状态。

| 本次配置根 | 实际 root 消费者/生产者 | 扫描范围 | 排除与下一步 |
|---|---|---|---|
| WF_RESULTS_CACHE | full 或独立 repro controller → fixture_scope.observe_results | 只遍历根的直接子项，识别 run-/repro- 及对应 owner/state 顶层记录 | 排除当前 results 和明确所属父 run 的内嵌结果；报 legacy/incomplete/KEEP/unverified，给该 canonical root 的 inventory-results 命令 |
| WF_RESULTS_CACHE/template | 启用跨 run 模板的 full controller → template_cache.observe | 只读直接目录/marker/meta/journal，不进入模板树或恢复 | 只按观测事实计 orphan-like/recovery-required/unknown，不据名称确认可退役；给 template inventory 命令 |
| WF_TEST_RELEASE_CACHE | dev full/独立 repro controller → wf_test_release.observe | 只读直接目录和 owner/meta/journal，不扫发行树/git | 不使用该缓存的 candidate 运行不扫描；给 test-release inventory 命令 |

full 扫本次实际使用的根；--no-template/--no-template-cache 不扫描未使用模板根，独立 repro 不扫描模板根。canonical 相同的根只枚举一次并按材料分类；嵌套根不递归进入，因此 results 根不会顺便深扫 template。内嵌 repro/每单元/per-case 不调用 observe；特殊候选审计工具只用本来显式盘点，不伪装成 root 自动观察。

同根多材料适配器共享本次顶层索引，不各自重列；该快照只用于提示，不作为后续 prune/retire 的安全复验输入。分类器显式接收 shallow/deep 证据完整度：浅层只报告可见 owner/状态声明与 unknown，不能因没有展开 commands/ 就称完整 cleaned；`complete` 仅表示本次浅层遍历未遇错误，不是完整生命周期已验证。安全复用/删除仍走既有完整证明判定，且可为该目的独立重读，不把“一次观察”误写为整次 run 只有一次目录读取。

只读浅层观察不递归计算目录大小、不生成内容摘要、不读取环境/凭据；子项/owner/meta/journal 链接不跟随，跳过并标 unverified，避免读到配置根外 sentinel。可识别的顶层控制 JSON 按协议读取（单文件最多 1 MiB，过大视 unverified）。目录数计为本次观察快照，扫描中缺失/不可读/变化写入 unverified；不存在根给 absent，不创建根。日志给 `observed_at`、每根分类计数、`complete|partial|absent`、容量 `not-measured` 和 shlex 正确引用的完整盘点命令；不能把未求容量填 0，也不能承诺列举后仍精确或“已无残留”。完整字节数与确认用摘要由用户显式 inventory 的深层只读扫描产生。

observe 在已验证的 controller/租约边界中执行；不额外 acquire release 锁或修改其他 key。无关根读失败只产生明确诊断，不能扩大为当前 key 的恢复失败，也不能被当作退役许可。记录只输出 stderr，不新增需要销账的结果 sidecar；输出失败须给出可用错误通道的归因，不伪造观察完成。随后真正运行遇到自己的事务/执行故障仍由原门禁决定成败。

public 的所有 --list/--dry-run/WF_NO_RUN 及纯 plan.py/repro --list，包含显式 results 镜像，都在此调用前返回，observe 计数为 0。独立只读 cache lookup 也不隐式扫描全根。真实 run 的契约测试要计 observe 调用次数/根集合，并用根外 sentinel、坏无关 journal、已配置缺失根、内嵌 repro、候选模式及计划模式做正反对照；不能用“warnings 字符串存在”代替证明生产者与扫描范围。

## 5. 模板事务：先恢复，再命中，再清理

删除 run_all 的 staging/backup 扫描。template_cache 新增一个修改型 acquire/prepare 入口：在既有 fixture lease 内，按当前 key 检查 journal→恢复/验证→迁移/lookup→必要时 publish。shell 一次调用取得 root/key/source/hit，不分别猜顺序。

事务材料归属也须在生产时闭合，不能等正式entry meta落盘才考虑清理。模板继续复用_build的fixture_scope.reset(staging)兄弟marker及move的重新锚定，盘点验实际marker而非要求不存在的staging meta。测试发行新增**材料专用**owner：`owner_path(material)`（staging父目录/backup的同级.owner），schema1、owner=`wf-test-release-material`、canonical root/entry_root、version、transaction、kind=staging或backup、uid；由wf_test_release本模块唯一读写，不改正式发行owner的原schema/tag。持锁后先排他原子写材料marker，再mkdir staging/写build内容；backup marker在已验旧代后、rename前写。marker是归属而非第二journal，不记恢复状态/代摘要，不参与build树摘要，不被_complete_generation当正式代。

两发布器分配新txn材料路径时必须同时确认树/marker均未存在（含链接），碰撞即拒绝，不先rmtree旧同名树或复用旧marker。新marker前不得有非空build内容。旧有效journal仍按既有冻结路径/摘要/owner恢复与finish，缺新材料marker不单独变成失败，也不补写marker；此兼容只限有效journal，不把无journal旧材料追认为owned。新生成事务的material-owner则必须完整匹配，丢失/矛盾保留，转4.2明确处置。

材料树确认不存在后才删其marker，异常/部分删除保留marker，journal仍最后删；无journal的异常清理也走相同精确材料校验，不再ignore_errors吞证据。回滚把backup移回entry时按既有journal恢复正式owner，材料marker不搬成正式owner。marker已写但树未建的所有权壳由inventory识别，可确认后只移该marker；marker原子写前失败无build内容，临时文件归unproven盘点。旧发行材料不补写该marker伪迁移，按4.2分别safe-legacy或明确人工放弃。相关marker/空壳的publisher、finish/recover/inventory/retire、测试/fake-tree/输入身份同批登记；不增加后台回收器。

- 独立只读 lookup 不恢复、不清理；发现当前 key journal 返回 recovery-required，不能伪命中。
- 普通acquire/ensure只维护当前key及明确legacy迁移，先核journal schema/key/路径再按既有recovery_action处理；坏记录保留并拒绝该key自动维护，不删其材料。无关key原地不动、不中断当前有效key。无journal不按名字猜删；可验marker走4.2安全退役，不可恢复/历史unproven由独立TTY manual-retained明确放弃，不能从普通入口自动调用。
- 恢复与迁移使用 fixture_scope 的 move/marker 规则，使 root/meta/owner 与真实落点一致；不在 raw os.rename 后遗留旧 marker。
- 只有完成新/旧代完整验证后，按 journal 明确引用的路径回收事务材料；失败保留 journal 或明确未收尾记录。不得 ignore_errors 后删唯一恢复索引。新代完整但垃圾回收失败仍可据实说明新代已完整，本次维护非零，不声明事务已收尾。
- journal 路径在任何 rename/remove 前验证 canonical root、key/transaction 前缀、staging/backup 父目录及 owner；错误 schema/错误类型/越界/坏链 fail closed。恢复成功但清垃圾失败时，下一次可以从已经完整的新/旧代继续收尾，不要求已删除的 backup 再出现。旧 journal 兼容现有字段；新字段缺失不能被猜成合法路径。
- test-release 缓存已有先 recover 后 stale cleanup 的顺序；保留恢复算法，但 `_cleanup_stale` 不再仅凭前缀删除无 journal 旧材料，改入同一盘点/退役契约。`_finish_transaction`、`_reap_staging_parent` 和模板 `_finish` 必须确认引用材料删除成功/确已不存在，最后才删 journal；失败仍能再次收尾。两种缓存的产物/marker 差异保持各自所有权，不强行抽通用事务框架。
- 事务首次/重复/中断后重入都核原始字节、tree digest、meta、root 与 sibling 不变。对声明为不可验证的两代不自动重建覆盖，避免丢唯一可排障材料。

在检查范围（full/ 的 Python/Shell、wf_test_release.py、wf_release_common.py）内，`*.stale-*`/`*.build` 仅找到 run_all 的删除引用，未找到当前生产者；作为一次性历史材料分类，不能声称它们仍由本轮发布器生成。它们的存量按本文 4.2 处理。新代码清理失败保持 journal 的设计防止继续制造同类 orphan，但首次构建在 journal 落盘前中断仍可能留下 staging，必须能被同一盘点发现；不为这一个窗口增加第二套事务日志。

### 5.1 确定性事务中断测试

当前 template_cache/wf_test_release 没有可精确定位事务窗口的 failpoint；现有 RecoveryTest 多数手工构造目录后直调 recover，不足以证明 run_all 顺序。实施明确增加模块内有限 checkpoint 函数和测试，不依赖外部 sleep/kill 竞争。

- 入口由 `WF_TEST_FAULT_INJECTION=1`、有效 owned test scope 和专用点名变量三项共同约束（模板 `WF_TEMPLATE_TXN_STOP_AFTER`，测试发行 `WF_TEST_RELEASE_TXN_STOP_AFTER`）；root/staging/backup/journal/测试日志均须 scope 内。不开测试开关时忽略点名变量；开测试开关但点名非法或路径越界，首次事务写前拒绝。故障变量不进入公开 CLI，也不能携带任意代码/路径。
- 枚举 checkpoint：`after-staging-before-journal`、`after-journal`、`after-old-moved`、`after-new-installed`、`after-meta`、`after-material-cleanup-before-journal-remove`。模板 after-new-installed 位于 repoint 前；测试发行位于 meta/owner 发布前。首次发布用 after-new-installed，同阶段但 old.present=false。只有点名匹配的 cache 发布器进程 `os._exit(97)`，绕过 except 的即时恢复，真实控制层仍负责收子进程/锁；不是杀主会话或伪造监督结果。
- 结果初始化用相同总开关/scope准入：lease中同一begin_run helper依次设after-owner-intent、after-run-state-before-prepare、after-prepare-before-controller（WF_RESULTS_INIT_STOP_AFTER）。命中时先将点名/路径/本ID日志写stderr并flush，然后仅该helper `os._exit(97)`，不raise、不走except/finally、不在stdout提前给成功run_id；最后一点在prepare完成但helper返回前。lease shell读helper非零后原样exit 97，不eval部分输出、不启动controller/重跑prepare/EXIT清理。helper退出只关闭它自己的FD副本，lease shell仍持锁直至其退出，不能以helper死亡立即宣称锁已释放。
- 初始化测试从最外public子进程启动，首次/plan-only转执行/cleaned重用×三个点逐项等待public/lease退出，核到达日志/磁盘owner-state-旧产物、controller未启动、对应FD/lease已真实释放，再从新public/inventory/reuse/prune/retire入口验证保留与不降级；探针只尝试既有锁，绝不删锁文件。开关关/非法点/越界对照，owner原子替换前异常另测，不用可捕获raise冒充死亡窗口。controller仅接管，初始化许可不跨失败重演；这些用例归C2 AC08/09，不计入AC19七缓存场景。
- 必须使用真实发布代码生成旧/新材料。对缓存命中导致窗口不可达的测试，在同样 scope/开关保护下提供仅测试用的 `WF_TEMPLATE_TXN_REBUILD=1`，只跳过本次命中、仍走真实 build/journal/move/repoint；不改变稳定输入身份、不跳过验证，重入时清掉该变量。测试发行复用真实 ensure 的构建失效条件或同样受限的重建注入，不加生产 force 开关。
- 覆盖集合固定为**五个恢复场景 W1–W5，加两个补充场景 O1/F1，共七个场景、六个不同 checkpoint**；after-new-installed 分 old.present=true/false 两个场景。数字不含结果初始化的三个独立 checkpoint，也不含本地删除 I/O 故障。AC04 对应 W1–W5，AC17 对应 O1，AC06 对应 F1，AC19 要求这七个场景及开关隔离全部验证。不能把一个 checkpoint 命中同时算成首次/重建两种前提。

| 场景 | checkpoint / 前提 | 模板期望及入口 | 测试发行对应期望 |
|---|---|---|---|
| W1 journal 已落旧未移 | after-journal / old=true | journal新摘要尚未确认，旧原位回滚；run_all重入 | 新代摘要已确认且staging完整可前滚；ensure重入核已冻结字节 |
| W2 旧移走新未安装 | after-old-moved / old=true | backup回滚；run_all重入 | 新代可验证优先前滚；原backup保持到验证通过 |
| W3 新已安装未repoint/meta | after-new-installed / old=true | 新摘要未确认，按backup回滚；run_all重入 | 新代摘要已确认，补meta/owner前滚 |
| W4 meta已写journal未清 | after-meta / old=true | 前滚收尾；run_all重入 | 前滚收尾，不重复构建 |
| W5 首次发布半安装 | after-new-installed / old=false | 未确认新代撤销，再由真实入口正常发布 | 新代完整可确认则前滚；不可确认则撤销，禁止填造旧代 |
| O1 journal前孤儿 | after-staging-before-journal | 真实_build完成已有fixture marker；inventory验证marker，safe-legacy可退役，不假恢复 | 新material-owner先于build，验证后可退役；旧无marker材料另测unproven手动放弃，不伪owned |
| F1 材料已清journal未删 | after-material-cleanup-before-journal-remove | 已完整entry可重复finish，不要求已删backup | 已完整根可重复finish，journal最后删 |

恢复算法不改成两种缓存完全同结果；它们记录新摘要的时机不同，按各自 journal 可验证代选择。每行必须有“精确到达日志+实际磁盘状态+真实入口重入/盘点”的证据；异常没到点不算覆盖。另以清理I/O失败验证F1相邻的部分材料已删场景，不能吞错后直接删journal。
- 清理 I/O 故障使用受开关/scope 保护的确定点，仅使指定材料一次删除失败，不伪造 finished；正常环境相同变量不得生效。所有测试外边界只回收自身创建对象，保留现场先留证，不给普通 runner 增加自动重跑。
- checkpoint 与测试强制命中开关必须从 candidate audit、r67 假树/嵌套无关运行和 namespace 的无关命令中清除，只显式传给被测发布器；完整 CLI 支持矩阵验证未继承污染。静态 helper 已在 fake-tree COPY 与模板 full_runner inputs，wf_test_release 已在 build inputs；须核这些边而非一律重造审计。新增生命周期/CLI helper 登记、suite 字节变化才触发 candidate-audit 重生成/coverage 复核的条件仍保留。

### 5.2 controller 与监督的确定性故障验收

不引入通用故障注入框架/任意回调脚本；在对应实现模块内保留有限点，统一复用既有总开关 `WF_TEST_FAULT_INJECTION=1` 与有效 owned scope 的准入。新 root 控制输入在任何命令启动/删除前校验；非法点名或scope不符拒绝，未开总开关全部忽略。点名变量只影响被选定的本次 run/command，不进入稳定输入身份、公开产品配置或普通子进程环境。

| 边界 | 受限选择/实际注入位置（拟） | 真实入口的可区分断言 |
|---|---|---|
| 聚合函数失败 | `WF_RUNNER_FINALIZE_FAULT` 取 `assess-exception`、`assess-none`、`assess-empty`、`assess-malformed`、`assess-contradictory`；runner_control在调用assess_run的固定seam注入异常/返回值，仍走真实校验/finalize | run_all/独立repro正常执行到命令终态后拒绝删除、summary非成功，run-state保留；不是伪造lines或绕过helper。正常无开关相同变量不改变行为 |
| owned删除失败/部分完成 | 同变量`delete-oserror`保持第一次remove前故障；另加`delete-after-first`：finalize按固定角色序FIX→LEGACY_FIXTURE_ROOT→RUN_TEMPLATE过滤实际存在的owned资源，在第一项确已完整删除后、第二项remove前抛OSError，只生效一次，不接受N/任意路径 | 真实root用正常setup产生至少两项实际资源，否则用例失败而非跳过；核第一项/marker确失、第二项及后项/marker保留，报告removed/failed/not-attempted与retained_paths一致，cleanup failed；目标原非零rc不被改，原0转非零，无GATE-OK/finished-cleaned，重复信号不重试/重建已删项 |
| 控制/摘要发布失败 | 同变量取 `control-write-oserror`、`summary-exception`、`summary-malformed`、`state-finish-oserror`；在runner_control的固定writer/publisher seam | 写失败无GATE-OK，不写finished-cleaned；纯publisher单测另外验证fsync/replace/readback各OS失败，真实root不依赖用户权限/磁盘满注入 |
| metrics交接失败/重放 | 同变量取`metrics-write-oserror`、`metrics-missing`、`metrics-truncated`、`metrics-old-run`、`metrics-input-mismatch`；先通过真实scope准入再将有限spec显式交给本run的write_metrics，在其固定提交点分别抛错/不提交/提交截断字节/用确定的非本代ID/改一个固定输入摘要，不接受文件或任意payload参数 | 从真实run_all运行正常单元后触发，reader必须拒绝具体原因，内层或controller非零，无GATE-OK/finished-cleaned；正常同输入成功。旧文件原样重放另用reader定向测试，真实入口变体不靠外部写文件竞速 |
| S/G故障 | `WF_EXECUTION_FAULT_TARGET`取root、unit:<注册名>或repro:<case>:<phase>；`WF_EXECUTION_FAULT_POINT`取supervisor-before-ready、supervisor-after-started、guardian-after-started；`WF_EXECUTION_FAULT_ACTION`取exception/exit/kill/hang。C按已验元数据选择，在spawn G/S时传内部有限FaultSpec | S在READY前、目标Popen并发STARTED后或G收到STARTED固定点故障；不依赖delay/sleep或外部kill；核命令真实PID/started receipt、故障日志、最终cleanup、下游保留/无成功 |

selector语法与角色枚举由execution解析，不将环境字符串直接eval。run_one传注册unit名、worker传case/phase的metadata，root传保留root角色；无法定位唯一目标拒绝。FaultSpec必须在内部G/S启动参数中先传递，不能等START帧才送达，否则before-ready点不可达；G/S只接收严格点名/action，复验本命令绑定，不执行任意代码。G在转发STARTED的固定分支注入，S在自身实际状态分支注入；测试仅向所属G/S自身发信号或os._exit/hang，C始终保留控制面，目标策略不改。hang使用已有取消/清理deadline结束，不加无限等待。原 `WF_UNIT_FAULT` 可在测试中映射同一内部spec，不再向所有后代export裸G故障；旧supervision单测同样迁移到确定点，保留原信号/PTY/后代覆盖。

不要求G/S一故障就全部unknown：G存活并接管S成功时进程cleanup可cleaned，但设施失败仍非零；G丢失时C不能替S猜cleaned，必须保留unknown。两者分别配正常对照/receipt/保留现场断言。被测目标需有真实派生进程的用例，用测试专用ready管道/固定事件确认其就绪后在对应scope控制路径触发故障；无跨进程sleep时序猜测，不发信号到宿主同名对象。

finalize删除报告由唯一执行循环逐项产生，首次失败即停，后项记not-attempted，不因finally重复删。delete-after-first覆盖跨资源部分完成；单一rmtree内部的部分删除另做定向I/O反例，真实删除一个自建后代后失败，保留owner marker和剩余内容，禁止ignore_errors或把该根记removed。不承诺恢复已删文件，复用/轮转仍阻断；后续人工处置按4.2，而非自动重跑finalize。

真实G/S故障集成优先使用owned scope内WF_JOBS=1路径，namespace中不为注入重新暴露宿主scope/FD。仅test_supervision里使用故障注入的用例改用有效scope，普通无scope TemporaryDirectory调用继续作为兼容对照；故障准入失败不能记为设施故障已覆盖。unshare正常回归仍独立验证。root集成按目标Popen/STARTED固定事件注入，只证明实际已创建的后代被处理；需要证明双fork子代时，低层监督测试让自建目标经**独立测试ready管道**报告派生完成，S再按既有控制通道转发状态。测试pipe显式通过pass_fds、仅测试开关有效，W仍不继承C↔G/G↔S控制FD；不让生产命令按任意文件触发控制动作。

故障事件只写本run既有日志（精确点名/run_id/command_id），不新增任意路径写入能力。发射fault spec后从G/S/W环境剥离root测试选择变量；metrics专用有限spec只经已核root→execute的内部frame交给本次write_metrics，writer复验scope/run_id后一次消费，不export给unit/repro。namespace/candidate_audit/r67无关运行显式清除，repro父异常不得污染相位执行。root不存在CLI helper stdout协议，空stdout/非零子进程仅在原独立CLI测试；核心R1失效不放行由真实异常/非法返回覆盖，不删异常测试。

## 6. CLI 与最终证据

`REPRO/cli.py` 用 argparse 定义所有公开选项，列表项/路径用 shlex.quote 数组输出；值不能为空，后继选项不能充当值。公开解析先于任何租约和发行初始化；--list 仍零写；合法重复 group 与现有最后值规则用兼容用例固定。wf_fixture.sh 使用 set -e，不存在同一 shift 死循环，但仍核缺参稳定报错，不为统一外观重写它。

summary 构造时已是最终 payload：`summary_publish=published`、canonical summary_path、最终 gate/cleanup/status。临时文件不作为已发布文件；replace 后读回完整规范对象等于拟发布对象，成功才返回同一对象。无需“发布后再写一次”标记成功。

- status=ok 的必要条件包含目标/结构 gate、全部 cleanup=cleaned、必需控制结果与最终摘要验证；不能只凭 fail 计数为零。
- summary_publish 表示本次文件已被原子放到目标；CLI 返回成功还要求 fsync/读回完成。若 replace 后读回失败，命令非零且无 GATE-OK，失败原因写外层控制记录，run-state 不写 cleaned 的 finished；单独一个 summary 文件不得被下游当作完整 run 成功证明。同 run_id 的 run-state.finished、控制结果和摘要三者共同验证。run-state 最终写失败同样非零，不改回已发布摘要或重试成功。
- 新写 summary 增 run_id，字段修正采用 schema 3；旧 schema 2/pending 只读历史保留，不批量改写。内部 reader/test 同步接受历史用于展示，但不可给本次成功背书。
- receipts/run-state 新协议 schema 1；原 execution supervision 结构不随意换代，若新增 required 字段则成组升级对应 writer/reader/tests。repro bundle/state 协议只有所需输入集合/结构变化才按现有规则升级，不能为沿用旧 red proof 留后门。
- 结果 owner schema2 必须在 claim-results、plan 镜像、begin_run、prepare、_valid_results_owner/prune/bootstrap、inventory/retire、controller/fake-tree/tests 等所有 reader/writer 成组更新；fixture/test-release 的其他 owner 域不受影响。repro validator 跳过的结果 owner 文件仍按既有文件角色处理，不能把新增 run-state/观察输出误当 case 结果；observe 无新文件，不增加此歧义。

### 6.1 发布输入的本代身份与事实归属

full的`summary-metrics.json`继续位于原路径，但采用schema1交接对象：`schema_version`、`run_id`、canonical `results_root`、`role=full`、`state=complete`、`inputs`和`measurements`均必需。run_id由lease本代身份经已核内部frame传入，不能从磁盘旧metrics取值；不把随机ID纳入稳定plan/proof摘要。shell只采测量，调用同一个results_summary.write_metrics入口（有限`--write-metrics`模式）做结构校验、同目录临时写/flush/fsync/replace；写失败内层非零，绝不沿用旧文件。

`inputs`记录本次已完成的plan、release-context、五列lines、每个unit结构化结果，以及启用repro时的bundle/records的sha256和长度；文件路径按已核角色固定或来自验证后的本代清单，不接受metrics提供任意可读路径。每个unit_execution必须是本run_id与当前unit/实际阶段，结果行投影与lines相符。controller等内层/所有写者结束后，以自己持有的预期run_id/root/role和冻结plan/args核验；metrics按普通非链接文件受限读取一次（1 MiB），解析、摘要与build共用同一字节快照，inputs逐项核实际字节。不用mtime、仅“文件存在”或计时戳证明新鲜度；未运行repro时显式not-applicable，运行但缺bundle/records不可当0。

| 摘要事实 | 唯一来源与交叉核验 |
|---|---|
| 目标rc/取消/监督与run cleanup | controller收到的root终态、当前child/local receipts及finalize；metrics不得携cleanup_state/最终status并覆盖它们 |
| suite/flow/extra数、结构gate与失败 | 当前冻结plan×五列lines×本代unit结果；controller复用results_gate及既有债务判定输入，不接受metrics里的gate_*或extra_failures当成功依据，不再保留两个最终fail计数器 |
| repro相位/数量/失败 | 已验证的本代bundle/records与原repro gate；metrics只提供时间等测量，不决定repro_ran/repro_fail或proof有效性 |
| 配置/来源 | frozen plan/context提供mode/deploy/jobs/release来源；测得effective jobs/fallback/template构建事实必须类型正确且与实际选择/记录不矛盾，非适用值显式null/0 |
| 时间及其他测量 | measurements按现有字段登记类型、有限非负和启用条件；启用项缺失拒绝，禁用项显式0/null；不以缺字段默认0掩盖截断。耗时数值不作本任务成败目标 |

最终目标计数/gate/债务投影固定收拢到`results_gate.assess_run_results()`纯函数，沿用现有gate/repro_gate与shell已确定的债务规则；controller调用一次并把验证后的同一报告交build，publisher不再算另一份fail。内层可调用该函数打印非最终目标诊断，但不能掺root cleanup，shell中的旧fail/debt计算在迁移后移除，行为回归证明等价而非改变规则。

`read_metrics`是唯一输入身份/结构验证入口，build不得自己重开文件或兜底旧无schema数据。summary schema3携`input_evidence`记录实际消费的metrics/plan/context/lines/结果清单摘要；完整成功仍要求同代owner/state/control/summary与全部必需证据一致。summary输入失败不逆写进程清理事实，但本次发布必须非零、无GATE-OK、不签finished-cleaned；可保存控制失败与已知实际清理事实，不能造完整成功摘要。独立repro不消费full metrics，改为验证其本代bundle/records/receipts后构造对应投影；内嵌repro的记录绑定父run_id及case/phase身份。

repro的本代绑定沿用已冻bundle sha/size加新record.run_id与phase receipt的run_id/command_id；validator/writer/controller共用该检查。随机run_id仅在运行记录和控制交接，不进入execution_fingerprint/red_subject_digest/public_inputs，bundle的稳定身份算法不为本次运行重算另一套。旧record缺ID可历史展示，不给本run签成功；需要升级的只是必需record读取契约及对应测试，不靠升级bundle/state掩盖陈旧proof。

WF_KNOWN_LEGACY继续保持既有债务/转绿/缺项语义；controller在启动W前将经过注册名校验的清单快照记入现有root-control输入，由同一gate判定消费，shell不能在metrics里另传debt减免数字。源树卫生/产品树变化等现有必过检查仍执行，失败经内层非零控制结果和明确原因保留；controller不得用metrics覆盖内层非零。最终计数投影与门禁规则逐项回归，不能在搬发布位置时顺手取消债务或卫生检查。

旧无身份metrics、旧无unit_execution结果可按历史展示读取，不自动迁移/补本代ID。本批成组更新write/read、shell交接、controller、summary、candidate audit、产物登记、fake-tree与测试；lines及其五列消费者保持格式。反例覆盖旧metrics重放（相同plan/路径但不同run_id）、缺失/截断/畸形/错类型/未来schema、错root/role/输入摘要、陈旧unit/repro记录及写入失败；正常首跑、cleaned复用、非零目标、repro禁用/启用均有对照。

## 7. 真实入口验收和收敛

测试分两层：纯判定枚举结构/字段错误；真实 run_all、独立 repro、内嵌 repro 入口覆盖顺序/失败传播/跨 run 保留。不得仅 mock 最终 bool 或只测 recover 函数。

核心反例矩阵：聚合正常/抛错/非法返回/矛盾报告×资源可删/必须保留；内层正常root started不误报child unknown，外层root真正缺失仍拒绝；确定点G/S完成/丢失×本地删除成功/失败；事务W1–W5/O1/F1逐行；公开有值选项×缺/空/后继选项；summary正常/写/同步/替换/读回失败；本文6.1的旧/缺/半写输入全矩阵。receipt三域分别覆盖有scope与无scope边界，unit JSON引用与原五列lines分开验证，不用standalone绿证明managed全集。

受控故障仍只在 WF_TEST_FAULT_INJECTION=1 下生效；优先测试自己的进程/临时目录，不触碰真实用户确认、宿主缓存或历史证据。为每个原缺陷证明“旧机制会错、新机制阻断”，用行为反例或受控 mutation 核断言有效性，不以文本布局测试取代。

结构调整后全跑既有 T0、慢契约、full 串并/green/both、candidate 并比较 ID/rc/status/相位，不只数目。helper 注册、fake-tree、源码/发行来源、字节复现以及 AGENTS 非托管摘要与 workflow/config/skills 的一致性手工核对。

## 8. 风险、兼容与回退

- 最终输出改由外层发布，stdout 顺序、取消 rc 与继承 FD 是主要风险；真实 root 取消和嵌套 repro 验证为必过项，不增加新进程监督层。
- 历史orphan/legacy/无主材料在人工处置前占空间；归属不明不自动删、不伪owned。用户于2026-11-17已确认4.2的unproven缓存精确人工放弃范围，操作者每次仍要在硬门禁通过后额外TTY+摘要确认；这接受了明确放弃可能损失非wf材料的风险，不表示脚本还原了历史归属，结果/fixture仍须owner。活持有者/权限能力不足/越界不可确认覆盖。新协议unknown/KEEP不自动删、不补legacy；本任务不处理真实存量。容量上限重构不在本轮，可执行收敛流程在范围内。
- schema/旧目录自动复用收紧是有意行为：提示新路径并给盘点/退役流程，不破坏旧证据；原正常已完成 run 在新协议下仍可复用。
- 确定性 checkpoint 增加发布器异常分支和 helper 输入影响；测试开关隔离、点名可达性、稳定输入不自失效、fake-tree 正常对照及必要审计重生成是必过项。若某窗口没有到达日志+磁盘状态+真实入口恢复三份证据，不可声称 AC04/AC19 完成。
- owner 协议升级与 begin_run 初始化顺序会影响所有结果所有权消费者；“先检查后删除”之外还必须覆盖“意图已写、状态未写”以及复用过程旧 state 遗留的中断窗口。observe 仅提供维护前快照提示，容量未测/部分扫描显式标明；不承诺观测到每个外部并发写入或恢复后的实时库存，这些由显式盘点负责。
- 回退按本任务实际修改路径逐项进行；不使用 reset/clean、通配删除、stash 遗忘，不回退用户其他工作。任务未获准 commit；任何提交另需用户授权。
- 发现设计不闭合或需新增产品行为/跨边界依赖时，先修方案重新审查；范围内普通实现细节由执行阶段解决，不能拿“待下轮审查”代替自查。
