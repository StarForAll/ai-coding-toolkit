# 实施计划与验证矩阵

## 0. 授权、边界与前置

当前只完成规划。本任务为一个 runner/proof 闭环，cache、进程阶段、candidate 证明和 bundle 不能独立交付，因此保持一个任务、分步骤实现；Codex inline，不派子代理、不要求 implement/check JSONL。用户批准最新版规划后才 task.py start，读取 trellis-before-dev、scripts/doc specs，再写实现。

进入实施前记录 git status/diff/untracked，保护既有工作。解释器使用项目指定 `/softwares/python/bin/python3`，Python 验证设仓库外 pycache。不得修改产品 payload/正式 release tree、真实用户 wf 配置或无主数据；无用户授权不 commit/push/PR。

## 1. 先建立可失败的边界测试

每个行为先在旧实现观察目标失败，再实现并转绿。使用临时 owner/cache/source 副本，测试自身不改被验证源文件，不用跳过、降 expect 或静默重试掩盖失败。

| ID / 对应 AC | 行为证据 | 目标测试面 |
|---|---|---|
| V1 / AC1、AC10 | 资产、manifest、builder/helper、dirty/HEAD 改动各影响正确摘要；纯 touch 不变；不同 invocation/prefix 字符串可区分同 binary venv，路径身份只读固定字段、从不 walk prefix；binary 字节单独核验 | test_test_release、template/cache 定向测试、test_python_runtime_identity |
| V2 / AC1 | HEAD 不可读固定用 run-owned 模板，不读写 cross-run 槽；模板初始化失败仍失败 | template/runtime 契约 |
| V3 / AC2 | 初次/命中/旧 meta/损坏 meta/无主/搬动 root；发布每个 tree/meta/owner/journal 窗口注入失败/终止；恢复依据旧字节而非当前 freshness | cache 发布/fixture_scope/test_test_release |
| V4 / AC3 | ensure×ensure、ensure×check、外部 ensure/check×持有消费期独占锁的 runner 都明确 busy；两个独立共享 check 可共存；释放后重试成功，取消不泄漏 | 多进程 barrier 测试，不靠 sleep 猜先后 |
| V5 / AC4 | 共用 cache 的 dev 双 checkout/worktree 在不同 HEAD/dirty 输入下交替切同槽正确 miss；candidate 同 ref A/B 亦正确重建；legacy 只清可确认同槽，其他版本/缺字段保留 | template cache 契约与容量文档核对 |
| V6 / AC5 | run_all 无显式结果 list/dry-run/changed 零写、零 lease/build/state/prune；显式目录仅 plan/marker 与当前域固定结果锁，非空无主写前拒绝；现有 owned 日志哨兵不变 | test_run_all_contract；直接 shell，无默认自动注入 results 的旧 helper |
| V7 / AC5 | run_all 摘要 stderr/stdout 空；直接 plan JSON 单对象；sh channel；repro list stdout 列表且无 lease/pycache/runtime/cache/state | test_test_runner_plan、repro CLI 契约 |
| V8 / AC6、AC12、AC16 | 固定 internal frame 在 public parser 前剥离；含空格/中文 user argv 保真；未知/重复/漏字段/缺 --/注入保留选项拒绝；真实三次脚本重入只两次 plan，execute 核一次已冻字节并拒绝替换/缺失 | runner_protocol 单测 + 真实 lease/controller/wrapper exec 链 |
| V9 / AC7 | dev red 成功→同 release subject 的 candidate auto 实际 candidate green；缺 red、内容/版本/ref/helper/runtime 变化与非 clean case 拒绝；candidate green 不改 red | test_repro_selection、candidate auto 慢契约、真实安装 repro |
| V10 / AC8 | jobs=1/并行 xargs 只读同一 inputs 文件；删/坏/漏 case/模式冲突/替换文件/伪造第二 env JSON 均拒绝；初始文件 digest 与 gate 不同不提交 | test_results_gate、worker/runner 契约 |
| V11 / AC8、AC9 | 执行中改解释器/release/source、缺失/重复/畸形结果、old state 1/2/unknown/corrupt；相位独立、green 不续 red、原 state 保护 | test_repro_selection/test_results_gate/test_execution |
| V12 / AC10 | 公共输入只在两个 barrier 完整扫描，不随 case 数增长；单列 prefix 字符串哈希、binary 读字节/probe 次数、同机成本、full 计数及串并等价 | 新摘要计数/开销报告 + full/repro/candidate |
| V13 / AC11 | 内嵌 repro 在默认 build/--no-build、顺序/并发编排、jobs=1/>1 时 ensure/check/check-json 调用数严格为零，实际 locator 与父 context 一致；文件缺失/篡改/冲突/伪造 lease 非零且不走独立 fallback；独立 repro 仍正常初始化 | run_all→repro 真实链 + 公开 CLI 调用计数桩 + 身份哨兵 |
| V14 / AC12 | 同生产 UID 域或同测试 scope 多 run/不同输出目录只复用一个结果锁，无 per-run sidecar；同域活跃 run 阻止显式镜像，默认 list 不取锁；嵌套继承不自锁 | fixture_scope/results-lock 生命周期与并发契约 |
| V15 / AC13、AC18 | 生产路径拒访/busy 桩下，owned scope 的 runner 管理结果操作成功；实际管理写入不碰生产锁/cache，scope 外 locator、假/损 marker、跨域继承拒绝。suite 任意 scratch 不属于此保证；真实 fixture 慢测仍独占 | scope resolver/真实 CLI 的管理写目标探针，不以整进程 syscall 无越界作断言 |
| V16 / AC14 | 真实 user/mount namespace 覆盖 /tmp 后，生产 acquire/verify/commit 在 open 前拒绝，不创建私有同名锁；宿主锁保持；r67 fake runner 在自建本地测试 scope 内通过，不触真人 state/context | namespace.py 边界与 lock helper 端到端；能力不可用明确记未覆盖 |
| V17 / AC9、AC15 | 无 lease 的 gate 可诊断但从不调用 commit_state/写 state；R→G→S 合法子进程显式继承 FD 提交；S/直接 CLI/库调用无、伪造、关闭或不同 mount 域 lease 一律写前拒绝；普通 failed case 不妨碍结构合法的其他 eligible case | test_results_gate / test_repro_selection + real subprocess writer topology |
| V18 / AC11、AC15 | 根 handoff 前、candidate repro freeze、S 最终 barrier 各走完整 candidate check；坏 tag/dirty/坏 meta/tree 初始不启动 W，执行期改动使 S 拒绝；内嵌零 ensure/check CLI 不等于零 candidate validator | candidate validator 调用计数 + 初始/结束故障注入 |
| V19 / AC17 | setUpClass 只建空 scope/layout；正常同输入 dev 首次一次双构建序列/模板首建、后续 build=0；candidate 不建 dev；计划零 warmup；cold/stale/故障 private pool 不污染共享池。记录每调用/每 case/整类 wall clock、cold/warm/build count/teardown 与 900s 剩余；取消日志 15s 从 cache ready 起计 | test_run_all_contract helper 生命周期、cache builder 调用计数与明确失败归因 |
| V20 / AC18 | runner-managed 越界 locator 写前拒绝；唯一 owned fixture/outside 为 scope 内兄弟目录，项目外 symlink 目标仍 WF_PATH_INVALID 且无输出。并行私有 /tmp 与原宿主串行 scratch 边界保持；不改旧 suite 字面量、不按文件名认领清理 | scope 单测 + 复用 r7 语义的目标路径回归、已有并行/串行域测试 |

### 测试 helper 的缓存与时间账目（先落实）

- `RunAllContractTest.setUpClass()` 创建单个 owned scope 和正常 cache pool 布局，不急切构建；每 case 分 state/HOME 子目录并支持该 case 的多调用共享 proof，每次真实调用独立 results/fixture/pycache；不跨 case 共享 state。tearDownClass 只在所有调用与 FD 结束后回收类 scope；不使用用户 HOME 中发行或模板的副本作为种子。
- 正常 dev 调用复用 scope 内 pool/test-release 与 pool/results-cache/template，仍每次校验新鲜度/ownership。取消测试显式用同一池先 warmup 一次，再开始等日志窗口；warmup 失败报阶段错误。正常 candidate 使用类内 owned 候选输入/对应槽，不为了 setup 建 dev 发行。r67 继续短生命周期假树/假发行桩，不支付真实 build。
- 计划/非法参数测试不 warmup；强制 cold、stale、旧 schema、发布故障、中断、候选篡改等用 private cache/候选或空目录，helper 不覆盖测试显式配置，不把 --no-build 缺失面提前建好，不改共享池。WF_NO_TEMPLATE 测试即使池已有 template 仍真实绕过。
- 首次冷建、后续相同输入实际 builder.build 次数（dev cold=2、warm=0）、template fixture/init 次数（首次=1、warm=0）和 source identity 一并记账；输入变化后的必要重建单独报告，不为满足计数使用陈旧缓存。
- 一个逻辑 case 的 prepare/warmup/主请求共用 900 秒单调 deadline，子进程使用剩余时间而不是重置900；取消探针在 cache ready 后才计15秒日志等待，已有5秒 cleanup 另记。helper、warmup 和 teardown 必须有显式 timeout/错误归因，无盲重试/加时/skip/真人缓存 fallback。记录整类时间、最长case与剩余量、private 故障冷成本；超时先修共享范围或输入失效原因，不靠改timeout通过。
- scratch 处理只修边界文案与目标回归：新用例分配唯一 owned fixture/outside 兄弟目录，清理仅限自身拥有对象；现有固定 /tmp scratch 维持 namespace/宿主串行语义，不新增 scratch manifest、全局 TMPDIR 改写或 basename/glob 清理。

## 2. 实现身份与 cache 发布闭环

- 引入共享 runtime identity resolver；明确 tool/SUT role，路径身份严格哈希规范 JSON 中 normalized absolute invocation（保留 venv 启动位置）、realpath(sys.executable)、realpath(sys.prefix)、realpath(sys.base_prefix) 的 UTF-8 字符串；调用文件/实际 Python binary 按文件字节另哈希，禁止递归 prefix/site-packages。身份包含 implementation/version，避免同 binary 不同路径 venv 被当同环境；不改变执行解释器默认值。
- 在 common 中统一 release/template 输入清单、release subject 和稳定槽编码；新 helper 自身进摘要，dev 完整 HEAD 不删，HEAD 不可读固定走 run-owned 模板。candidate 不依赖 authoring HEAD，但绑定真实 release 内容/version/ref。
- 为 test release 公共 CLI/库建立 canonical-root 固定 inode 非阻塞 flock，内部 locked 实现不重入开锁。ensure 的发布/恢复全程独占，check 共享只读，runner 在同一独占 fd 完成 ensure/check 并保持至消费结束，不降级/重取；宿主嵌套 repro 验证祖先 lease 后只读消费，namespace worker 由父 lease 与只读挂载保护，不执行 ensure 自锁。
- 两 cache 共用一套有界 journal 发布协议：完整 staging→journal→backup/安装→验证→commit→清理；恢复先于任何 stale/prune。支持首次 old-absent、旧 schema 恢复、sidecar 部分移动、当前输入已变化、取消中断。journal 越界/owner 不符保持现场非零。
- test release schema 2、template meta schema 1；meta/output digest 均验证，只有过期/旧 meta 归入 miss，owner 不明或 inputs 不可读拒绝。check 发现 pending journal 返回 recovery-required，不能执行恢复写入。
- 稳定槽只清可证明归属的同槽 legacy；缺 deploy/version/ref 的旧 meta 不从 key 猜测；真实用户 cache 不在本任务手工清理。共用 cache 的 dev 多 worktree 与 candidate 同 ref A/B 交替重建、跨版本增长均按设计明示，不新增 LRU。

## 3. 实现公开入口、锁域与继承协议

- 先实现 create_test_scope 与统一 resolver：只对 runner 管理 results/cache/meta/lock/journal/state、分配 fixture 根、pycache/HOME 等入口强制 scope containment，越界/坏 marker 拒绝不 fallback。真实结果锁测试不取真人锁；完整 fixture 慢测保持既有独占。任意 suite open/mkdir 不由此 resolver 拦截，禁止以此检查未纳管固定 /tmp scratch。
- 在 `full/runner_protocol.py` 实现 design §4.1 的唯一 frame encoder/decoder。run_all 最顶层先剥离 `--_wf-internal <lease|controlled|execute> <fixed fields> -- <user argv>`，repro 先剥离 inherited-release frame；内部字段不进公开 parser。按表验证字段/类型/分隔符/真实 lease，非法不 fallback。只用 argv 数组，无 eval 拼参数；新 helper 纳入输入/假树清单。
- public 记录原始 results 显式性、设置稳定进程环境默认路径、禁写 pyc 做一次 preflight；list/dry-run 此时结束。lease-run helper 取 fixture→当前域结果锁再 exec lease frame，生成一次 final plan，claim/prepare 后写 plan bytes/token；exec execution controller，由它新 session 启动 controlled frame。
- controlled shell 在同 PID exec release wrapper；dev 取并保持独占 release FD、ensure/核验，candidate 调用同一完整 candidate check；主 results 写 release-context 后 exec execute frame。execute 是第三次同脚本重入、最终 consumer，无额外未声明阶段或重算计划。frame token 在执行首个单元前核验；路径/digest/长度经 argv，consumer 从读取的一份 bytes 核验并解析。controller 显式 pass_fds allowlist，取消等待全部后代后释放生命周期。
- 新结果锁 helper 同时供显式镜像、真实 runner/standalone repro 使用；同域显式镜像 busy、无显式 list 零锁/写。scope/domain 是继承校验的一部分；父仍持锁时内嵌 repro 不再次 open/加锁。plan-only 返回与下一次真实 prepare 分开取样。
- `namespace.py` 挂 tmpfs 前记录宿主 mount identity，之后关闭本 worker 继承的宿主结果/release FD 副本并清除 locator/host test scope；保留 unit-domain 与原宿主 mount ID 供 helper 先于 path open 做 kernel 校验。生产宿主锁/全局 writer 在域不符时拒绝，不能拿私有 /tmp 同名 inode 替代。suite 对共享结果的管理写入仅限父委派 per-unit 文件，仍按原执行域运行自己的 fixture/scratch；r67 可建立全新的本地 test scope，其 scope/context/state 不能指向宿主真实用户内容。
- `run_all::run_repro` 一律使用 inherited-release frame，不靠 --no-build 躲自锁。内嵌 R 校验父 release-context digest/schema/请求身份与真实 fixture/result（dev 再 release）lease，派生 TEST_ROOT/TEST_VERSION/TEST_REF、WF_RELEASE_TREE/WF_TEST_LIB，不调用 wf_test_release.py ensure/check/check-json；坏 context 不 fallback。独立 repro 才持锁初始化一次；list 在全部租约/runtime/pycache 之前纯选择退出。
- candidate handoff 根 wrapper、内嵌/独立 R 的 freeze 和 writer S 的最终 barrier 均复用 `prepare_candidate_repo.check(tree, version, out)` 全语义（含 meta/tree/commit、tag、clean、version/结构），用同一批观测构造 release subject，不能用较窄 verify_repo 取代；V18 验证调用归属与起止失败，不因禁 dev ensure/check 而删除候选校验。

## 4. 实现 repro 两种身份与唯一 bundle

- 将 red_subject 与 execution_fingerprint 分开，并按 design 的字段唯一生成；保留 candidate auto，不把完整 deploy context 当 red 的匹配 key。
- dev red proof 记录 subject 和真实 dev execution provenance；candidate auto 必须证明同 case/source/helper/runtime 和相同 release bytes/manifest/version/ref，仅排除 deploy/root/各自 Git commit。candidate actual execution 仍绑定 candidate 自己的部署/root/tag commit；任何变化出口是 dev 同主体 red/both，不能静默转 green。
- inputs bundle schema 1，case mode 和输入在其中唯一冻结；原子写 inputs.json，env 只传 WF_REPRO_INPUTS_FILE，去掉 REPRO_INPUTS_JSON。串行和 xargs 都读同一文件；TSV 只作派生兼容面，不能改变 bundle 权威。
- R 保存最初 bundle digest/长度；worker 返回 bundle digest、相位和 execution fingerprint；抽取纯 validate_repro 复用于 G/S，results_gate 移除当前 commit_state 调用，只输出结构报告/机器汇总，不做完整末次 barrier、不需要写租约。缺 bundle/context/case/schema 一律拒绝。
- R 在 G 报告结构合法且有 eligible case 时，仅启动并等待一个 commit-state writer S；不能只看 gate rc=0，因为普通部分 case 失败原来也允许其他有效 case 更新。R 经 shell argv 启动的 S 继承已标记 inheritable 的真实 fixture/result/release FD，所有 Python Popen 边界显式 allowlist pass_fds；S 核 ancestor/mount/scope，再重读 bundle/结果/日志，用同一 validate_repro 核验；gate report 文本不是写许可。
- S 负责唯一最终完整输入/runtime/release barrier（candidate 跑完整 validator）；G 不重复，W 只快检。全局 context/bundle 变化整批不提交，结构/畸形结果非零，普通 failed case 仅不更新自身。state schema 2→3，old 1/2 仅 legacy，未知/损坏不覆盖；commit_state 库函数和直接 CLI 均统一 verify_write_leases，不能只在 main 校验；writer 错误必须传播到最终非零汇总。

## 5. 跨层收口与最终验证

- 同步 r67 的 COPY/STUB/SPECIAL、runtime helper、cache/meta 签名、final plan/bundle schema、results_gate 测试，避免假环境缺依赖或引用真人 cache。
- 文档同步 full README、repro README、wf-delivery-discipline：独占消费锁的外部 busy、生产 UID/测试 scope 固定锁与 namespace 边界、原有 fixture 独占前提、runner-managed 与 suite scratch/escape 的边界、类缓存冷暖和超时账目、显式镜像串行代价、prefix 只哈希路径字符串、嵌套 release-context 交接与坏输入拒绝、final plan token、candidate auto red 主体、prepare 时点/list 无锁、dev 双工作区/candidate 同 ref A/B miss 及跨版本清理边界、G/S 的真实进程与锁继承。产品设计稿不改。
- 确认新/变更 shell bash -n、git diff --check；定向测试用项目解释器，新增失败证据和通过证据逐条对应 V1-V20。
- T0：PYTHONPYCACHEPREFIX=/tmp/wf-unit-pycache /softwares/python/bin/python3 -m unittest discover -s scripts/tests -t .；慢契约显式 WF_SLOW_TESTS=1，通过 owned test scope 隔离 runner 管理的 HOME/results/release/state/cache/fixture/pycache，真实 fixture 慢测先满足既有独占前提；不让默认 fixture helper 伪装“无显式 results”测试。
- 实施前 baseline 与实施后各三次 warm full green 同机中位数，另一次 cold rebuild；记录 identity 分段/完整扫描次数，目标 ≤3s 新核验且 full 增幅 ≤10%。未实测不写“满足”；超预算定位重复计算后解决，不能关核验过门。
- full green、--serial、representative、candidate green、dev red→candidate auto 真实正反例；串并 lines 名称/rc/status、repro phase/mode/proof identity 逐项对拍，runtime ID 与日志时间例外逐项注明。
- 项目只读发行/文档校验：/softwares/python/bin/python3 scripts/build-wf-release.py --verify --verify-token-parity；/softwares/python/bin/python3 scripts/validate-wf-design.py；/softwares/python/bin/python3 scripts/check-doc-refs.py；./scripts/validate-skills.sh。不能重建正式 release 来抹掉不一致。
- 审阅最终 diff/untracked/staged，对照实施前状态确认仅任务路径；记录 pass/fail/skipped/未跑、cache 迁移和手动覆盖。D1 真宿主压缩不自动化，不称为 full 自动覆盖。

## 6. 回退与交付

实现未获批准前不执行本计划的实现级检查。用户批准后按 1→2→3→4→5 顺序，失败只定位修复，不重复整套测试掩盖不确定性。事务在锁内恢复完整代，不能用删除 state/cache 来过测试；出现无法恢复的 journal 保留现场，报告精确安全下一步。

交付时对应 AC1-AC18 写 validation 证据；所有新 schema 旧读取口、direct CLI、nested runner 和 candidate auto 都要有闭环，不只报告默认 green。用户未授权不提交、不归档。
