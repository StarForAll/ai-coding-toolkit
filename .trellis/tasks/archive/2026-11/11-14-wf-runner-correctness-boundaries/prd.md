# 修正 wf 运行器非耗时问题

## Goal

修正 wf 测试运行器的缓存来源、计划入口和 repro 证明边界，使命中、执行和证据提交能对应实际输入；保留 candidate auto 等已有入口，不改变 wf 产品规则和人工覆盖边界。

## Background / Evidence

本节描述审查时的实现事实；下文是待实现要求。

- 模板 cache key 只有 payload 摘要、Python 主次版本和 deploy/version/ref；dev 使用 `git describe --dirty`，不能区分同 HEAD 下两次 dirty 工具内容变更。cache 命中不检查构建工具摘要。证据：[`run_all.sh:252-335`](../../../scripts/tests/wf_runtime/full/run_all.sh)。
- dev 部署把 `git_head()` 写入 `installation.source_commit`，追加平台时按 HEAD 和 rules_digest 判同源；`r90_tests.py` 使用模板派生夹具验证追加平台。dev 模板需要 HEAD 与内容身份共同成立。证据：[`wf-dev-deploy.py:339-365,465-483`](../../../scripts/wf-dev-deploy.py)、[`r90_tests.py:69-91`](../../../scripts/tests/wf_runtime/full/r90_tests.py)。
- 测试发行 meta 未绑定 build 工具；`check_meta()` 只验证 source、manifest 和版本，未逐文件核对实际发行树；公开 `--ensure` 无发布锁，先删旧 tree 再 move，和 CLI/runner 并发发布会交错。证据：[`wf_test_release.py:169-258`](../../../scripts/tests/wf_test_release.py)。
- `run_all.sh` 在两次自重入前设置默认 results，在 plan-only 判定前认领、清理和轮转结果；既有 dry-run 契约要求人类摘要在 stderr、stdout 为空，显式目录留下 plan。证据：[`run_all.sh:41-87`](../../../scripts/tests/wf_runtime/full/run_all.sh)、[`plan.py:678-705`](../../../scripts/tests/wf_runtime/full/plan.py)、[`test_run_all_contract.py:96-109`](../../../scripts/tests/wf_runtime/test_run_all_contract.py)。
- candidate 明确允许 green/auto，禁止 red/both；旧 auto 未区分部署，因此能用 dev red。若把 red 匹配也绑定完整部署 context，candidate auto 就永久无法满足。三个 candidate-clean 安装 repro 在两种部署下都复制所选 release 再注入，支持用相同内容主体关联 dev red 与 candidate green，而不是忽略任意发行差异。证据：[`plan.py:484-486`](../../../scripts/tests/wf_runtime/full/plan.py)、[`repro_select.py:108-121,175-184,247-258`](../../../scripts/tests/wf_runtime/full/repro/repro_select.py)、[`_release.py`](../../../scripts/tests/wf_runtime/full/repro/_release.py)、[`branch-source-preview.py`](../../../scripts/tests/wf_runtime/full/repro/branch-source-preview.py)、[`release-identity-commit.py`](../../../scripts/tests/wf_runtime/full/repro/release-identity-commit.py)、[`reinstall-preserves-data.py`](../../../scripts/tests/wf_runtime/full/repro/reinstall-preserves-data.py)。
- 冻结指纹同时存在 env 和 `inputs.json`；worker 读 env，缺 case 时回退到 current。独立 repro list 也先拿 lease、设置 pycache，再调用生成 fingerprint 的 plan。证据：[`_worker.py:59-67`](../../../scripts/tests/wf_runtime/full/repro/_worker.py)、[`repro/run.sh:27-90,143-170`](../../../scripts/tests/wf_runtime/full/repro/run.sh)、[`results_gate.py:68-123`](../../../scripts/tests/wf_runtime/full/results_gate.py)。
- `f1_init.py` 通过 `wfdrive.run()` 启动 SUT，故 SUT 解释器也影响模板初始化；D1 宿主压缩用例仍是手动覆盖，慢契约仍显式启用。证据：[`f1_init.py:28-35,47`](../../../scripts/tests/wf_runtime/full/f1_init.py)、[`wfdrive.py:6-13,191-200`](../../../scripts/tests/wf_runtime/full/wfdrive.py)、[`full/README.md:48-49`](../../../scripts/tests/wf_runtime/full/README.md)、[`test_run_all_contract.py:1-4,39`](../../../scripts/tests/wf_runtime/test_run_all_contract.py)。

## Requirements

### R1 — 完整、可恢复且受并发保护的 cache

- 用单一输入清单和完整内容摘要绑定资产、dev-manifest、build/初始化工具及 tool/SUT 身份。相同内容稳定，dirty 字节变化可区分；dev 模板另绑定完整 HEAD，candidate 模板绑定实际 candidate 内容、version/ref。
- dev HEAD 不可读取时，固定退回 run-owned 临时模板；不得读写跨 run dev 模板缓存或用 unknown 签发身份。夹具初始化本身失败仍报失败。
- 旧 schema/身份缺失或不符只产生 miss，不冒充命中。保护 owner/root 和无主数据；构建失败保留旧 tree/meta/owner，成功后才清理本次 staging/backup。进程中断后先恢复可验证完整代，再做失效或清理；无法恢复则保留现场并明确拒绝。
- release 的公开 ensure/recovery/读者使用同一 canonical-root 锁；并发发布不得交错，runner 消费发行树期间持有同一独占 lease，直接 ensure/check 竞争明确返回 busy，释放后可重试。模板继续由 fixture lease 串行保护。只读 check 不执行 journal 恢复写入。
- 嵌套 repro 通过父 release context 与真实祖先锁取得同一身份，内层不再调用 wf_test_release.py ensure/check/check-json 或另选 cache；缺失、冲突或验证失败拒绝。candidate 仍在根 handoff 前、内嵌/独立 repro 的 freeze 与提交 proof 前的 writer 最终 barrier 调用同一 prepare_candidate_repo.check 完整语义，不能删掉 tag/clean/meta/tree 核验。独立 dev repro 保留持锁初始化入口。
- 模板按 Python major.minor/deploy、candidate 再按 version/ref 使用最新单槽；完整身份在 meta。接受共用 cache 的 dev 多 checkout/worktree 不同 HEAD/dirty 输入、或 candidate 同 version/ref 异内容交替时反复 miss 的代价，并记录于 README/spec。只迁移可确认 owner/root/identity 的同槽 legacy key；其他版本、无主和归属不明目录不自动删除，说明增长边界与精确清理口径。

### R2 — 计划入口与执行阶段分离

- run_all list/dry-run/changed 和独立 repro list，在默认情况下不创建 lease、结果、日志、pycache，不 build、不读写 proof state、不 prune。慢契约类只在 setup 建立空 owned scope/共享缓存布局，不为计划测试预建发行或模板；正常真实调用可在该 pool 内复用已经核验的磁盘 cache，禁止借真人缓存走快路径。
- run_all 从原始调用环境记录显式 results，仅首次入口做无写入 preflight；plan-only 在 exec 前结束。实际执行在 lease 后重算 final；public→lease-owned→controlled→execute 的内部 frame 在顶层先剥离/校验，再交公开 argv 到 plan。controller 是监督进程，execute 是最终消费 shell，不重复 preflight 或重判显式性。
- 显式 WF_RESULTS_DIR 允许 plan.json、必要 owner marker，以及当前生产/测试域共用的固定结果锁；已 owned 目录其他字节保留，无主非空/不安全路径写前拒绝。该保护在 plan-only 退出时断言；后续实际执行仍允许 prepare 删除旧 plan 并重写最终 plan。
- 结果锁按“生产 UID 域或经过校验的临时测试 scope”各固定一个，不为每个 run/输出目录创建永久 sidecar。测试域内 runner 管理的结果/cache/state、分配的 fixture 根、pycache/HOME 等写入口必须在 owned scope；resolver 不是任意 syscall 沙箱。suite 自有 scratch 保留私有 tmpfs/宿主串行的既有语义，项目外 escape 目标可以是 scope 内兄弟目录，不因名称被自动认领或清理；不能以换锁规避生产互斥；namespace 内不得按私有 /tmp 重建宿主锁。宿主内嵌 repro 经 kernel/ancestor/scope 验证继承，不再次申请。既有真实 fixture lease 的独占约束不因测试域取消。
- run_all 人类摘要保持 stderr、stdout 为空；直接 plan JSON stdout 是单一 JSON，sh 输出保留现有通道。独立 repro list 保持 stdout 用例列表。

### R3 — 保留 candidate auto 的两种证明身份

- execution fingerprint 绑定本次完整 tool/SUT、平台、部署和实际 release 身份，green 结果始终使用该身份；不得把 candidate green 标成 dev 执行。
- red subject 单独绑定断言/注入脚本、helper、执行协议、source/targets/build inputs、tool/SUT、平台及 release 内容/version/ref，不含 deploy 标签和 release 根路径。red proof 只由 dev red 实际成功产生，并同时保留其 dev execution fingerprint。
- candidate auto 只对 candidate-clean 用例查找同 red subject 的有效 dev red：release 内容、version/ref、运行环境等必须匹配。匹配时执行 candidate green；缺失或变化时拒绝并给出在 dev 用同一内容/version/ref 运行 red/both 的出口。禁止 candidate 注入、禁止仅按版本名继承任意 red。dev auto 继续无匹配 red 则 both。
- 冻结 bundle 只有一个落盘来源 inputs.json；env 只传 bundle 路径，不传第二份 JSON。case/mode/context 缺失、损坏或不匹配均拒绝；worker、gate、state writer 消费同一 schema 和摘要。输入变化不能写入可信 proof，green 不刷新 red。
- 只读 results_gate 不再调用 commit_state；父 repro 编排 shell 按结构校验结果启动唯一 state-writer 子进程，writer 本身与直接 CLI/库调用都验证真实 fixture/result/release lease 和 mount/scope，再复用同一 gate 校验及最终 barrier 后提交。普通 case 失败与结构/全局 context 失败分开，保留可提交其他 eligible case 的原有语义。
- 旧 state 不推导新证明；保留 legacy 内容，只有新 schema 的实际成功相位能建立新 proof。部署变化只改变 execution 身份；red subject 的兼容匹配规则以上述条款为准。

### R4 — 验证完整性并守住已有成本

- 实际 release tree、source/tool 和解释器身份在运行开始、提交 proof/发布 cache 前核验；公共摘要按 run 共享，不按每 case 反复全树扫描；不能只信 meta 或用 mtime 代替内容证明。新核验成本必须记录并对比，不能靠关闭内容核验过预算。
- 解释器路径身份只哈希规范化 invocation、sys.prefix/sys.base_prefix 路径字符串的 UTF-8 规范 JSON；Python binary 另外按文件字节哈希，严禁递归扫描 prefix 安装目录。
- full 身份核验继续记录分段/调用次数并做同机 warm 对比，任务目标 ≤3 秒新增核验且 full 中位数增幅 ≤10%，非跨机器硬失败门。
- 慢契约成本另记：正常共享池首次 dev 冷建、后续 warm 命中、candidate 准备、故障专测 private 冷建、每调用与整类 teardown、整类墙钟及最长 case。相同输入后续正常测试不重复发行双构建/模板首建；private 故障/迁移测试不能污染正常池。每个逻辑 case 的准备/warmup/实际请求共用现有 900 秒 deadline；取消探针 cache ready 后再计 15 秒日志等待，5 秒清理单列。超时、重复冷建先修生命周期/失效/等待归属，不能借用户 cache、改 timeout 或关闭核验掩盖。
- 维持实际用例数、异常/取消/超时、串并等价、candidate 真实闭环；同步运行器 README、repro README 与交付规格，不用静态检查代替行为证据。

## Acceptance Criteria

- [ ] AC1/R1：资产、manifest、builder、runner 和 runtime dirty 变化均改变正确输入身份；dev HEAD 单独变化必 miss；HEAD 不可读固定走 run-owned 模板。
- [ ] AC2/R1：旧 meta 安全失效；构建/切换错误及各 journal 中断窗口能保留/恢复完整旧代或确认完整新代；不覆盖无主目录，不清掉唯一完整代。
- [ ] AC3/R1：两个公开 ensure 并发、ensure 与 check、ensure/check 与持有发行消费期独占 lease 的 runner 竞争均无交错发布或半成品读取；外部 ensure/check 均明确 busy，两个独立共享 check 仍可共存；锁释放后可重试，异常和取消不泄漏锁。
- [ ] AC4/R1：同槽输入变化只替换该槽；共用 cache 的 dev 双 checkout/worktree 不同 HEAD/dirty 输入以及 candidate 同 version/ref 异内容交替得到正确 miss，不误命中；旧槽清理与跨版本保留范围有测试和文档。
- [ ] AC5/R2：从公开 shell 入口验证无显式结果计划零写入、零 lease/build/state/prune；显式结果仅 plan/owner 与当前生产/测试域的固定结果锁，无主非空拒绝；摘要通道兼容，直接 JSON 可一次解析。
- [ ] AC6/R2：正常 run 仅一次 preflight、一次 lease 内 final plan；controller 子进程不再算计划。lease 前后输入改变按 final plan 执行；伪造阶段标记不能跳过真实 lease 验证。
- [ ] AC7/R3：dev red + 相同内容/version/ref/runtime 的 candidate auto 确实执行 candidate green；改变任一 red subject 输入、用非 candidate-clean case 或旧 proof 必须拒绝；显式 candidate red/both 仍拒绝。candidate green 不续签 dev red。
- [ ] AC8/R3：jobs=1 和 jobs>1 都只读 inputs.json；删除/损坏 bundle、漏 case、模式冲突、替换 bundle、执行中 runtime/release 变化等均非零且不提交受影响证明。
- [ ] AC9/R3：旧 state 安全迁移，不丢历史，不继承 proof；未知/损坏 schema 不覆盖；合法 green/red 相位更新和原有结果完整性检查保持。
- [ ] AC10/R4：定向、慢契约、full green 串并等价、candidate auto 正反例及文档校验通过；附同机开销数据和已知覆盖边界，不减少 expect 或关闭正确性门禁。
- [ ] AC11/R1、R3：嵌套 repro 从父 runner 的冻结 release context 取得已核身份并验证真实 lease，ensure/check CLI 调用数为零；jobs=1/jobs>1、默认构建/--no-build、顺序/并发编排均通过。文件缺失、摘要/根目录/版本/ref 不符或伪造 lease 必须拒绝，不回退独立发行初始化；独立 repro 仍按自身请求正常 ensure 或 check。
- [ ] AC12/R2、R4：同一生产 UID 域或测试 scope 多次 run/镜像共用一个固定结果锁，prune 后无每 run 残留；同域其他目录显式镜像与活跃 runner 竞争 busy，默认 list 不取锁；execute 入口校验 final plan 路径/digest/长度，篡改/缺失拒绝。
- [ ] AC13/R2、R4：真实 fixture 契约测试保持既有独占前提；新增结果锁单测使用 owned scope，用生产路径禁止访问/busy 桩模拟已有宿主锁，隔离结果操作仍成功；真实 CLI 的 runner 管理写对象只触测试 scope，不取得或改动生产结果锁与用户 cache。管理 locator 越界、损坏 scope、伪造继承拒绝，不 fallback；scope 完成后无子进程/FD 遗留。
- [ ] AC14/R2、R3：受控 namespace worker 在调用生产锁 acquire/verify/writer 前拒绝，不创建私有 /tmp 的伪宿主锁；宿主锁 inode/持锁状态不变；域内 r67 仅写测试 scope 合成状态，不接管真人 context。
- [ ] AC15/R1、R3：read-only gate 无锁时可诊断且不写 state；writer 无/伪造/过期/不同 mount 域 lease 写前拒绝；合法 shell→gate→writer 子进程链提交，candidate 起始与有 eligible proof 的提交前 barrier 分别验证 tag、clean、meta/tree，起始坏候选不启动 worker，结束变化不提交。
- [ ] AC16/R2：内部阶段 frame 经真实 exec/controller 链剥离，原 user argv（含空格/中文路径）保真；未知/重复/缺失内部字段、缺分隔符、保留选项注入拒绝；计数为三次脚本重入/两次计划，无未声明 consumer 层。

- [ ] AC17/R2、R4：慢契约类共享 owned cache pool、每 case 独立 state/HOME、每调用独立 results/fixture；同 case 多调用可共享证明但不得跨 case 泄漏；计划路径零构建，dev 首次仅一次双构建序列/一次模板首建，同输入正常后续实际 build 次数为零；故障/冷建专测使用 private cache，candidate 不被迫建 dev 发行。报告 cold/warm/class/teardown 账目、900 秒剩余与取消等待余量，无悄悄加 timeout、真人 cache 或 skip。
- [ ] AC18/R2、R4：scope resolver 拒绝 scope 外 runner-managed locator；不拦截任意 suite scratch，也不把项目外 escape 目标混同 scope 外。新回归用唯一 owned fixture/outside 兄弟目录证明 SUT 拒绝且 outside 无输出；并行私有 tmpfs 与宿主串行固定 scratch 的区别、归属/清理边界在文档明示，无 basename/glob 自动清理或批量套件迁移。

## Out of Scope

- 改 wf 产品语义、解释器祖先锚点、默认并发和候选 red 禁令；自动化真实宿主压缩；提交/push/PR。
- 为缓存增加多版本 LRU 服务、后台回收器或通用事务框架；自动清除其他 candidate 版本或无主目录。
- 把所有既有 suite scratch 改写到新根、增加 scratch manifest/全局 open 拦截或按固定 /tmp 名清理宿主；这些不属于 runner 管理写入口的 scope 保证。
- 防御同一用户恶意持续改写并恢复字节的文件系统攻击；承诺任意时刻无 TOCTOU 或断电级 durability。保护合作工具的并发发布，内容证据在明确起止屏障核验，已检测变化拒绝。

## Planning Status

阻塞问题为空。关键兼容性选择是保留 candidate auto：用受内容一致性约束的 dev red subject 证明，配合独立 candidate execution 身份。PRD/design/implement 均待用户审查；未开始实现。
