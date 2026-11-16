# 技术设计：wf 证据与边界一致性

> 待用户审查，未实施。基线 `b74d60101bf874f7940af1e20dd1aa73eb8a6ee3`。
> 需求及验收以 [prd.md](./prd.md) 为准，实施顺序见 [implement.md](./implement.md)。

## 1. 边界与整体结构

本任务维护作者仓库中的测试工具，并修正两份产品自包含脚本的既有项目边界实现。保持 Linux、标准库、现有锁序 fixture → results → release、真实 HOME、独立 SUT 解释器、单一计划及发行缓存复用。

不新增任务工作流、自动授权、额外用户确认、网络服务或通用沙箱；不将耗时优化重开为本任务目标。无法合成真实宿主压缩事件，不把人工 D1 验证登记为自动通过。

修正围绕以下所有者进行，调用点只传输入和消费结果：

| 契约 | 唯一所有者 | 消费者与边界 |
|---|---|---|
| 测试路径、scope marker 校验与管理路径布局 | 新的作者侧 `scripts/wf_test_paths.py` | `fixture_scope` 保留委托接口；plan、两个 shell 入口、发行/候选准备、release 锁入口在首次写入前调用；模块不反向导入 runner |
| repro 请求相位与相位日志证据 | `execution.verdict(..., phase=...)` | worker 执行后、gate 与 writer 的 `validate_repro` 复核统一调用 |
| tool/SUT 完整身份 | 既有 `python_runtime_identity.Resolver` | release context 与 repro context 引用相同 role 身份投影；不另造路径摘要算法 |
| 结果完整性 | 既有 `results_gate` / `repro_select.validate_repro` | summary 生成器消费其结构报告，shell 不复制 PASS 判定 |
| 最终摘要发布 | 新的 `full/results_summary.py` | 从冻结 plan/context 与已校验结果派生；shell 负责调用与准确传播返回码 |
| 命令后代管理 | `execution.run` 的专用 guardian G 与执行 supervisor S | G 保持命令归属和故障接管，S 做正常执行/清理；共用后代回收实现，调用方与 shell 不另扫树 |
| 候选身份一致性 | `prepare_candidate_repo` 的统一验证函数 | ensure 命中、check、发布后验证复用，不保留简化命中判据 |
| 测试库来源 | `full` 下小型共享 resolver（具体名称由实施确定） | `wfdrive` 与 repro harness 委托；candidate 禁止源码回退 |
| 产品/开发部署资产包含关系 | install/uninstall 各自自包含的边界判定；`scripts/wf-dev-deploy.py` 的完整部署计划判定 | 三个入口均落实项目→基址→资产；dev-deploy 的首装/追加平台共用其本地唯一判定，三方用同一反例矩阵对拍；自包含产品脚本不导入 wflib |

新 helper 必须纳入 build/proof 输入身份与 r67 假树的登记复制契约；新增注册单元必须有 expect、模块映射与行为断言。不得通过“缺 helper 就跳过校验”兼容假树。

## 2. R1：统一管理路径与写前边界

### 2.1 解析规则

- 原始路径先按实际 cwd 变绝对路径，再解析 `..`、现有祖先符号链接及尚不存在的末段；不能以目标是否 exists 决定是否采用解析结果。
- 用路径组件包含关系判断 scope，不能以字符串前缀判断；相似前缀、文件父目录、坏链和无法确定归属分别拒绝并给出原因。
- 统一 helper 校验 scope marker/root/UID；`fixture_scope` 的 reset/remove/move 所有权与 protected-root 规则继续生效，不被 scope 内包含关系替代。
- 管理清单覆盖 results、state、test-release、template、candidate、fixture、pycache，以及 bootstrap/plan 计数文件、锁/meta/owner/journal/staging/backup 派生路径。HOME 与 fixture 全局锁是已有宿主语义，不伪称 scope 私有。

### 2.2 默认布局与最早写入

设置 scope 后，未显式给出的发行缓存等管理路径都派生到 scope；显式域外路径在 mkdir、open(O_CREAT)、取锁、pyc 生成和 prune 前拒绝。无 scope 时保持现有默认布局。

public 初始协议剥离/路径 preflight 一律禁止 pyc；完成路径验证后才启用批准的 pycache prefix。计划调用计数先在内存汇总，真实 run claim 结果目录后落盘，避免 list/dry-run 创建后再删除 bootstrap 文件来冒充零写入。显式结果镜像仍只允许其现有 owner/plan 与域结果锁写入。

低层可独立执行的 test-release/candidate/release-lock CLI 也消费同一 scope 检查；内部继承发行 frame 继续核真实锁和输入 token，不能以“父进程已经检查”跳过本入口将创建的派生路径。

### 2.3 执行域

namespace 内只校验该域的委派结果与本地 scope；不重建宿主 sidecar 锁。串行路径与并行路径保持相同可观察判定。来源在 `/tmp` 的输入仍按现有 capability 规则处理，不放宽保护规则。

## 3. R2 / R6：相位证据与校验错误统一

`verdict` 的 repro 模式必须显式接收 `green|red`；遗漏或未知相位是调用错误，不能保留旧的“任一 PASS 都算”分支。日志必须有匹配相位的合法 PASS，并拒绝相反相位、矛盾 PASS/FAIL、空日志与非零退出。多行 detail 保持支持。

worker 根据冻结 bundle 中的相位执行并记录 phase；gate 与 writer 从同一 bundle 推导必需相位，重读相位记录与日志，调用同一个 verdict。只修改 worker 不算完成。green 进程清除继承的 `WF_REPRO_INJECT`，red 由 harness 按显式相位设置；外部环境不能使 green 静默走注入分支。

输入读取/JSON/字段结构校验按先后分层，使用稳定的预期异常类型；`results_gate` 在模块级导入依赖，默认 bundle 路径与显式路径用同一解析过程。缺文件、无权限、目录代替文件、坏 JSON、非对象 JSON、未知 schema、缺字段、错误类型分别给出可归因的非零结果，不把程序错误包装成通过，不用 `except Exception: return []`。

所有验证器拒绝非有限/负数计数或耗时等畸形数据，避免结构报告通过后在汇总阶段再次崩溃。报告格式错误与断言失败分开，二者都阻断成功。

## 4. R3：运行身份与旧证明

每个 barrier 建一个 Resolver；tool/SUT 身份包含调用文件、解释器二进制字节摘要、路径身份、实现名与完整版本。原始定位只在进程内参与解析，对外保存规范身份摘要及必要 role/version 诊断，不转存环境值。实际调用的解释器必须与被签名的解释器一致。

execution context 绑定 deploy/root/candidate commit；red subject 继续排除 deploy 标签和根位置，以支持同内容 dev red → candidate green，但绑定完整 runtime、release 内容与 version/ref、断言/注入脚本及其 helper。路径相同但二进制或 SUT 版本变化必须使证明失效。不得 walk site-packages 或缓存整个 Python 安装树。

协议成组升级：repro bundle `2 → 3`、state `3 → 4`、repro execution context `1 → 2`、release-context `1 → 2`。release-context 的 runtime 投影由新公共解析产生；frame/execute/inherited、worker/gate/writer 消费者同批更新，不容忍混读。冻结 frame 自身仅携带 context token，语法不因 context schema 变化而改版。

| 输入 | 读取 | 可签发/复用证明 | 写入与恢复出口 |
|---|---|---|---|
| 新 bundle/context | 严格校验 | 相位、输入、运行身份全部匹配才可 | 唯一 writer 原子发布 state |
| 旧 bundle/context | 明确拒绝本次运行 | 不可 | 使用新 runner 重新运行，不改历史结果 |
| 旧 schema 1/2/3 state | 可解析时仅作 legacy 保留 | 旧 green/red 均不能当新协议证明 | dev auto 需 both；candidate auto 缺匹配证明时给 dev red/both 出口；显式 green 保持既有含义 |
| state 损坏或不可读 | 归因后拒绝 | 不可 | 保留原文件，由用户处理输入；不自动清空 |

旧 state 不因只读 list/plan 而回写；新结果成功提交时可在 schema 4 中保留 legacy 原记录，不推断其缺失身份。不得用“版本号相同”恢复旧 red 资格。

## 5. R4：一次成功必须完成结果交付

最终顺序固定为：主池/repro 结束 → 结构与断言 gate → 输入终审 barrier → 已拥有资源清理并确认 → 原子发布 summary 并读回 → 唯一成功出口。取消/异常走同一清理归属，失败不打印 GATE-OK。

`results_summary.py` 消费冻结 plan/context 与结果报告，复用现有判定函数；计数从实际结果集与注册 kind 派生，不以环境里的汇总数字代替事实。summary 保留既有 schema 2 可兼容字段，新增必要状态字段为 additive；字段语义变化必须升级 schema 并更改所有 consumer。

写入为同目录临时文件 → flush/fsync → replace → 按必需字段读回校验。创建、写、同步、替换、读回任一失败均非零，保留原始日志。现有 summary 在本轮 prepare 时移除，发布失败不得借上轮 summary。若受限目录已无法写入失败摘要，只保证 stderr/退出码正确，不声称生成了不存在的文件。

清理只操作 owned fixture/template/本次临时文件；输出结果和失败证据保留。撤销 trap 中的静默成功约定，清理失败独立归因且阻断成功。调用方失联由控制 EOF 触发清理，执行 supervisor 死亡由存活 guardian 接管；整个监督边界的最后有效责任方不可用时不得声称已清理，保留归属证据和明确恢复步骤，见下文故障域。

## 6. R5：候选复用与发布

统一验证“输入树实际摘要 + 版本 + 候选实际摘要 + meta + tag/commit/HEAD 对应关系”，ensure 命中/check/发布后共用。干净工作树只证明与当前 HEAD 一致，不能代替候选内容与 tag 的核对。只读 check 还核 owner/root/schema，读取缺失或损坏分别归因。

- 首次：在 sibling staging 建候选并完整验证，发布后再验证一致性。
- 同输入重复：只在所有观测一致时 REUSED，不改文件或刷新证明。
- 陈旧/被改动：ensure 只重建确认为本工具拥有的候选；check 非零且不修复。
- 无主目录：拒绝覆盖，即使形状像合法候选也不直接认领。

发布锁和回滚围绕 canonical candidate root：不能在新代验证/发布完成前删除唯一有效旧代。利用现有作者侧锁和有界事务模式，不再增加一套不受监督的 rmtree+move。scope 中 sidecar 同受 R1 约束。旧 candidate meta 不能通过新完整校验时作为 miss/拒绝处理，不用手填摘要升级。

## 7. R7：宿主保护证据

把“目录顶层 inode/mtime 未变”缩窄为辅助定位；真正的前后状态比较由只读树清单承载。清单含相对路径、类型、regular 文件字节摘要、权限及符号链接目标；不跟随链接到树外、不把敏感内容复制进报告，不比较读取引起的 atime。

类级入口/出口对现有三个宿主缓存和生产结果锁做完整状态比对；每次调用保留路径/域写前门与轻量定位证据。完整清单不可读取时记未验证并失败，不折空集合。缺失、空目录、正常目录是不同状态；已存在缓存的子文件变化必须被检测。

反向自证只改 scope 内合成树：修改深层已有文件而顶层 mtime 不变、改权限、链接换目标、文件增删、无法读取，都必须得到区别结果。前后快照只能证明终态相同，不能证明中途写后恢复；不把它宣传为 syscall 审计，越界写前拒绝由 R1/R10 的机制承担。

## 8. R8：所有命令采用专用后代监督

首先在受控临时 scope 中建立真实反例：命令另建 session 后留下子进程并正常退出，当前执行器是否漏清理。若反例推翻前序静态推断，在任务证据中撤回结论；仍验证同一“无遗留”契约，不为得到失败而制造无关条件。

### 8.1 角色与归属

拓扑固定为 `调用方 C → 专用 guardian G → 执行 supervisor S → 目标 W`。每个命令一个 G/S，不建设常驻服务。增加 G 是为了在 S 已退出时仍有存活的内核归属接管方，不把 S 普通崩溃降格为“不支持”。G/S 均用标准库 ctypes 设置并核验 `PR_SET_CHILD_SUBREAPER`；G 必须在派生 S 前就绪，S 必须在派生 W 前就绪。C 不改全局 subreaper 状态，不会因库调用回收其他 sibling 命令。

正常时 S 执行、终止和 wait/reap W；G 只转发控制、监测 S、核验无遗留与最终收口。S 退出后，G 通过 Linux 的最近存活祖先 subreaper 规则接管孤儿后代，停止该命令，不重启 S/W；G 与 S 调用同一后代回收函数。接管权限来自真实父子关系及 `/proc` 进程启动身份，不来自环境变量、进程名或历史 PID。C 仍不扫全机进程树。

| 故障域 | 责任与结果 |
|---|---|
| C 退出，G 存活 | C↔G EOF，G 取消 S，必要时接管清理；C 已死不强求它发布结果 |
| S 普通异常、os._exit、异常信号或 SIGKILL，G 存活 | G wait S 后进入 TAKEOVER，枚举并回收其真实接管的所有后代；最终 infrastructure failure，即使 W 曾 rc=0 也不能改判 passed |
| S 存活但失联/卡住 | G 先请求清理；有界宽限后可终止 S，使后代归属转交 G，再做同一接管清理。不能先假定 S 已死；身份核验和 wait 是接管前提 |
| G 的可捕获运行异常，S 存活 | G 的最外层失败收口仍取消/等待 S，必要时接管；不能异常退出跳过回收 |
| G 被不可接管地终止，S 仍存活 | G↔S EOF 仍要求 S 清理；C 返回监督设施失败，不能仅凭 S 预期会清理声称已释放锁 |
| 最后有效监督责任方已丢失或宿主断电 | 无存活祖先或宿主收容能力就无法保证自动回收；这是整个 G/S 监督边界失效，不是普通 S 崩溃。C 仍存活时报告 cleanup=unknown、最后观测身份和恢复步骤，不签成功 |

不无限增加互相监督层：G 是本命令最后的可信回收边界。普通可捕获 G 异常必须收口；G 猝死且 S 不能完成回收是残余能力边界，不能凭“非零退出”把泄漏判据销账。对可回收进程，S 失败恢复属于本任务强制验收；内核不可中断的进程等外部条件如实列未知。

### 8.2 启动与信号隔离

- C 用 `start_new_session=True` 启动 G，G 同样启动独立 session 的 S；两者不在调用终端的前台进程组中。G/S 在各自启动窗口屏蔽 INT/TERM/HUP，安装忽略设置及控制 FD、核验 subreaper 后再解除临时屏蔽；正常取消只走私有控制通道。
- C 在 spawn 前保存 mask 并临时阻塞这三个信号，创建 G 后在 finally 恢复；G 派生 S 的窗口同样受保护。C 的 handler 只锁存首次取消，不在未登记 G 时抛异常跳过接管。对 C 的重复信号不得绕过 G 强杀整棵树。
- W 不继承 G/S 的忽略设置、临时 mask 或任一控制 FD。目标策略由 C 修改 handler/mask 之前采集，随 START 交到 S：原 mask 与 INT/TERM/HUP 的 exec 后 disposition（原本显式忽略则保留 IGN，其余为 DFL，不传 Python handler 对象）。W 在 exec 前恢复，同时保留普通 Popen 的其他信号恢复语义；`restore_signals=True` 不能被当作会撤销自设 INT/TERM/HUP 忽略的保证。
- 信号恢复在独立的 exec 启动路径完成，不使用多线程不安全的 `preexec_fn`。最终 exec 保持原 argv/解释器/cwd/env/stdio 与批准的 pass_fds，不能额外套 shell。恢复失败不得执行目标正文。

### 8.3 唯一双向控制协议

分别建立 C↔G 和 G↔S 两条匿名 `socketpair`。每端只传给直接对端，建立后关闭冗余副本，默认 CLOEXEC；W 不继承任何端点，S 不持 C↔G 端点。这样 C 或 G 退出能由下一责任方看见 EOF，而不会被无关继承 FD 阻止。

两跳共用一种有界长度帧与版本/command_id 规则，处理部分收发；不把业务 stdout/stderr、文件或 env 当控制通道。消息为 READY、START、STARTED（W 的启动身份与已登记监督边界）、CANCEL(reason,signum)、CANCELLED_ACK、DONE。G 向 C 转交身份是诊断证据，不是凭该 PID 扫描/杀进程的许可。ACK 只表示进入清理，最终 DONE 只能由 G 发给 C。

| 状态/事件 | C/G 的动作 | 执行与清理出口 |
|---|---|---|
| BOOT → READY | G 核验自身与 S 初始化，S READY 后才对 C 发 READY | 未收到 START 时不得启动 W；G/S 初始化失败先收其已派生对象 |
| READY → START | C 没有已锁存取消才发 START；G 同样确认未取消后转发 | S 只接受一次 START；G 监测从此刻起的执行归属，包括 STARTED 尚未送达的崩溃窗口 |
| 启动前或 RUNNING 中取消 | C 将 INT/TERM/HUP/超时/异常统一发 CANCEL；G 幂等转交 S | S 清理；S 不响应则 G 终止/wait S 后 TAKEOVER，取消先于 START 生效则不启动 W |
| S 退出、坏消息或无结果 | G 标记设施失败，wait S/停止执行后接管，不能仅报错就退出 | G 从真实接管的子进程反复清理/wait，直至 ECHILD；S 故障结果永久非 passed |
| C EOF | G 保持存活并向 S 取消；S 死亡/失联按 TAKEOVER | 命令 deadline/清理 deadline 不因 C 死亡重置；完成后 G 关闭资源退出 |
| G EOF/死亡 | S 的最外层失联收口清理；C 若存活报告设施失败 | 没有 G 的最终核验就不声称已完整清理；最后责任方丢失适用故障边界与恢复程序 |
| 正常或接管清理完成 | S 发内部 DONE 后退出；G wait S 并核验自己的后代归属已清空 | G 发最终 DONE（目标结果、设施失败、cleanup 结论），退出；C 收完整帧且 wait G 才结束调用 |

C/G/S 的事件循环同时监测各自控制通道、子进程退出与 deadline，不能阻塞单次 send/read/wait 丢失取消或上游 EOF。命令 deadline 和首次取消/设施故障确定的清理 deadline 都只建立一次，重复请求不续期；清理超限不能签 cleaned 或 GATE-OK。完整记录 target_rc/信号、termination_reason、infrastructure_error、cleanup_state；S 故障优先决定失败，取消原因和原目标结果保留。C 在最终 DONE+wait G 完成前已锁存取消时，不能因为目标 rc=0 返回 passed。

启动握手超时也由 G 收其已派生的 S；C 从未发 START 时，协议保证无 W，但不能据此假定没有 S 而直接杀 G。G 无法收口时，C 只把尚存 G/S 标为设施失败，不伪报“没有工作进程就没有遗留”。

### 8.4 清理、嵌套与 shell 入口

正常清理由 S 先按目标信号策略终止 W，再强制结束可回收的残留工作后代；S 不可用时同一算法由 G 执行。扫描以当前实际拥有的后代和 PID 启动身份为范围，反复核验/终止/wait，防止 fork/重新托管窗口漏项；不能把单次静态 PID 快照当清空。G 能 wait S 和它接管的孤儿，因此不依赖 C 猜 W 的 PID，也不因 W 换 session 而失去归属。G/S 的业务 pass_fds 副本不超期保留，最终锁释放须在存活责任方回收和 FD 关闭后实测。

嵌套执行也是 C→G→S→W。正常取消先由内层 C 转发给内层 G；内层 C 先死由 EOF 清理。外层正常路径等待内层完成，不先递归杀内层监督进程。若宽限耗尽或外层 S 死亡，则存活的外层 G 明确进入整个 owned 子树的强制接管：先按真实亲缘/启动身份暂停派生并稳定枚举，再终止并 wait/reap 全部可回收后代，包含内层 G/S；此时回收责任在外层 G，不能再期待被终止的内层 S 自行清理。接管不依据进程名或跨代控制 FD，不新增“W 必须继承监督通道”的冲突。不能暂停或回收的对象使 cleanup 保持 unknown/failed，禁止成功。

`run_all.sh`、`repro/run.sh` 的 INT/TERM/HUP trap 与 `--cancel-parent-children` 调用点同批改为：停止调度，取消其 owned 执行调用，等待对应 G 的最终收口；不得保留递归强杀监督进程的旁路。shell 的 owned 夹具清理在命令清理完成后执行；清理 unknown 时保留现场而不是删除仍被使用的夹具。root controller、单元 CLI、repro 库调用共用同一实现和故障结果格式。

最后监督边界失效的恢复：C 存活时以 stderr/可用结果通道记录 command_id、G/S/W 的最后已观测 PID+启动身份、缺失确认及可能仍占用的 fixture/results/release；不得声称这是完整残留名单。重跑如遇 busy 保留锁 inode/owner，不删锁、不强接管。恢复先由人或已授权维护入口逐个核实现场进程身份、停止确认为本次命令的进程，待确认无存活持有者后再用 owned 清理入口回收夹具并重新运行；不能以历史 PID 或通配 kill/rm 自动消除未知。该边界不免除普通 S 崩溃在 G 存活时的强制接管测试。

### 8.5 验收与 API 依据

AC16 覆盖自建 PTY Ctrl-C、C 定向 TERM/HUP、进程组信号、BOOT/READY/START/STARTED 前/清理各窗口、重复取消、C EOF、坏帧/部分传输，以及 S 的普通异常/os._exit/SIGKILL/卡住。S 故障用例必须让 W 含独立 session、双 fork 和真实测试锁/FD，断言 G 接管后后代全回收、锁可重取，结果仍是设施失败；不能只断言 rc 非零。另测 G 可捕获异常收口、G 突失时不虚报 cleaned 的边界报告，W 不继承保护设置/控制 FD、sibling 不误收、嵌套正常取消与强制接管的责任切换。所有故障只作用于测试创建且明确拥有的 PID/进程组/PTY，测试外层自身保留可靠清理，避免故障用例污染宿主。

API 核对：本机工具 Python 为 3.14.7；[Python 3.14 subprocess 文档](https://docs.python.org/3.14/library/subprocess.html)说明 start_new_session 和 restore_signals 的范围；[Linux signal(7)](https://man7.org/linux/man-pages/man7/signal.7.html)（man-pages 6.19，2026-02-08）说明 exec 的信号继承；[PR_SET_CHILD_SUBREAPER](https://man7.org/linux/man-pages/man2/PR_SET_CHILD_SUBREAPER.2const.html)（同版手册）明确孤儿归最近存活祖先 subreaper，不保证 S 死后必然归 init。2026-11-16 只读查阅；来源支持设计语义，不证明本机监督能力与真实回收已经通过，以上全部执行验收待实施。

## 9. R9：测试来源与候选证据

`candidate_clean=false` 是当前声明，不能据此认定全部 suite 仍直接导入源码。现有多处已用 `wfdrive.LIB`，而该值优先消费 `WF_TEST_LIB`。清点消费注册全集与运行器的可发现 repro 全集，基线集合和复算证据统一见 [inventory.md](./inventory.md)：67 个注册单元及 85 个可发现 repro；54 个分组成员、10 个显式元数据条目和 3 个候选声明是不同子集，31 个未分组 repro 仍在来源核对范围。注册表中 62 项显式 false、1 项 true、4 个 flow 未声明，字段缺失与显式 false 分别保留。

实施中从 `units` 和 `all_cases()` 的实际 ID 生成逐项覆盖表：单元 → kind/分组成员关系/显式元数据状态 → 真实对象来源 → 是否可在安装项目执行 → 不能迁移的具体技术理由 → 对应产品行为的已安装断言。逐 ID 对账而非只核数量；相对固定基线的新增/删除/改名分别说明，不能通过漏掉未分组或无元数据用例维持表面总数。分组表仅解释选择范围，不改变全量发现规则。不得只依据字符串扫描批量标为 candidate_clean。

共享 resolver 在 candidate 下只接受本次安装项目的 `.wf/lib` 或该证明明确声明的发行输入；缺失/漂移非零，禁止自动退回作者 payload。可迁移的行为套件本任务内迁移并真实 candidate 实跑；必须操作作者脚本/注入源码的白盒检查保留在原层，其必要性明确登记，不冒充候选覆盖。R10 的正反安全行为必须有安装产物级验证，不能仅由源码单测覆盖。

覆盖表与 summary 分别报告实际执行/排除/人工/不适用，不把排除计 passed；出现可迁移但尚未验证的行为项，则本任务尚未完成。保留原测试的 expect 与反例语义；新增用例更新注册预算而不是削减旧预算。

## 10. R10：产品技能根的两层包含关系

既有产品规则是“项目内 skill 根，不能通过链接写出项目”，本任务修实现，不另改政策。install、追加平台/重装升级、dev-deploy、uninstall 预览与 apply 的落点都满足：

1. 登记基址的实际位置在真实项目根内；
2. 资产实际位置既在该基址内，也在项目根内。

尚不存在路径采用同一最近现有祖先解析语义；不因 realpath(base) 已在外部，就把外部当新的授权基址。历史绝对 root_ref 若仍在当前项目内则允许，项目外记录明确拒绝且不改历史安装记录、不尝试删除外部资产；出口是修复项目内落点/重新预览，不自动跟随旧外部路径清理。

三条实现入口明确负责修正，不能把 dev-deploy 仅列为验证对象：

| 实现所有者 | 修改与调用范围 | 既有保护的关系 |
|---|---|---|
| `payload/install.py` 的资产计划边界 | 根解析、plan_writes、首装/追加平台/重装升级的全批预检与锁内复核 | 自包含本地唯一判定，仍核相对路径/资产类别/内容冲突 |
| `payload/bin/uninstall.py` 的 collect_targets 边界 | root_ref 解析、预览与 apply 前全批重算，所有待删目标先校验 | 自包含同构判定，保留预览令牌/内容漂移/旧记录保护 |
| `scripts/wf-dev-deploy.py` 的完整部署计划边界 | resolve_skill_roots/plan_deployment、deploy 首装与 add_platforms 在锁内的唯一规范落点生成；root_record 只序列化通过校验的根 | 现有 `safe_write_target(base, rel)` 只守 base，保留作第二层目标保护，新增并强制先核 project→base；add_platforms 不得直接 join 绕过计划 |

两份产品脚本保持单文件标准库自包含；dev-deploy 可调用已有作者侧/wflib 基础路径函数，但其“项目→基址→资产”的组合判定只能有一个本地所有者。三方共享参数化输入矩阵和行为对拍，不增通用代码生成系统，也不为了去重改动所有无关产品路径消费者。

预览时校验全部根与落点，apply 在同一项目锁内重新解析根并核对本次计划中的规范根身份/选中集合，再读取/写入/删除。install/uninstall 的现有预览确认链继续绑定其预览；dev-deploy 的跨命令 `--confirm` 保持原授权语义，不凭这次修正新增跨进程预览令牌，但本次进程锁外预检与锁内全批复核间的漂移必须被拦截。根在确认期间变域外链接，无论是首次还是追加平台均拒绝；合法项目内路径照常通过，不扩大为禁止所有符号链接。

dev-deploy 首装必须在 `.wf` 创建、writer 初始记录、skill 根 mkdir 和资产写入前完成完整计划复核；追加平台在冲突内容读取、pending 筛选、维护写权保存及文件 open 前复核全部涉及根与资产，不能先写一部分再遇另一根报错。历史安装 roots 参与新根差集或 root_record 序列化前按同一规则校验；域外引用不能被序列化成“合法绝对根”。现有无变化幂等、来源/代次/内容冲突、nested-repo 保护仍保留。除既有互斥协议必要的锁对象外，拒绝路径的项目业务文件/记录/回执与域外哨兵都保持原状。

将 known-gap 测试改为拒绝写穿的正式负断言，同批补三方首装/追加平台（支持时）/卸载/预检到锁内根改变的向量；dev-deploy 至少显式记录 preview、首次 confirm、追加 confirm、合法 no-op 四条路径，不能只借候选 install 覆盖。产品脚本修改后通过构建器重建正式发行树；dev-deploy 作者侧变化纳入现有 build/template 输入身份，不进入产品部署清单；不手改 generated release，不自动改版本号或生成 tag。

## 11. 防止重复修补的横向约束

- 每个拒绝分支有明确的原因与可执行恢复出口；恢复不等于豁免校验。
- 所有协议变化一次修改 producer、worker、gate、writer、summary、fake tree 与测试，不能留“暂时接受旧证明”。
- 每个新 helper 在唯一输入清单登记；扫描计数保持公共工作在 barrier 发生，不能重新变成逐用例全树计算。
- 每项 R 必须有目标反例和正常/重复输入断言；不以 skip、放宽超时、假 HOME、真人缓存或降低 expect 作为修复。
- 新故障注入只在 owned 临时树内；测试不把现有源码/宿主缓存改坏再恢复。回退验证优先作用于临时副本。
- 验证过程中不编辑 runner；实现批次结束且相关测试通过后才执行串并全量与发行证明。

## 12. 回滚与剩余风险

路径/监督公共 helper 与其调用方、repro schema 消费链、summary 发布与 shell 退出、产品源脚本与生成发行物分别作为完整回滚单元；未经用户授权不执行 Git 回退或丢弃工作区。

不回写已归档任务或旧验证记录；本任务建立新的验证矩阵逐项销账。host HOME 依赖、真实宿主 D1、同 UID 恶意 TOCTOU、最后有效监督边界丢失/宿主断电/内核不可回收对象仍是明确边界；普通 S 崩溃/SIGKILL 且 G 存活不在排除项。具体未知状态与恢复手段已在故障域规定，不以报告代替回收。完整回归结果、监督能力与真实 candidate 覆盖只能在获批实施后取得，本设计不预先宣称通过。
