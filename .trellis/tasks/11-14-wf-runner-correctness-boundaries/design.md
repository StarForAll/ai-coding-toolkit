# wf 运行器正确性设计

## 1. 范围与设计原则

本任务只维护 authoring runner、cache、proof state 及对应测试/文档。保留 full/subset/representative、candidate green/auto、串并执行域、人工 D1 和慢契约边界；不改 wf 产品 payload、正式发行物或宿主锚点。

拟修改面：`scripts/wf_release_common.py`、`scripts/tests/wf_test_release.py`、`scripts/tests/wf_runtime/full/`、相应 `scripts/tests/` 测试、`full/README.md`、`full/repro/README.md` 和 `.trellis/spec/docs/wf-delivery-discipline.md`。拟增加 `scripts/python_runtime_identity.py` 作为工具/SUT 身份的单一解析点。下文函数名和新字段均为提案，不宣称当前实现已存在。

把三个根因作为同一链处理：输入身份由单一函数产生，计划与运行有明确进程阶段，proof 的主体与实际执行来源分别记录；cache 发布有单写者和故障恢复。

## 2. 身份与摘要的唯一来源

| 字段/对象 | 唯一产生点 | 输入域与用途 |
|---|---|---|
| interpreter identity | `python_runtime_identity.resolve()` | role=tool/sut；调用文件/Python binary 的字节摘要、实现/完整版本，以及下文定义的路径字符串摘要；不序列化原始用户目录 |
| release build inputs | `wf_release_common.test_release_inputs_digest()` | 登记资产、dev-manifest、builder/common/test-release/runtime helper 内容、tool identity、版本和协议 schema |
| template build inputs | `wf_release_common.fixture_template_inputs_digest()` | release build inputs、受控 full runner 子树、dev-deploy/runtime helper、tool/SUT identity；dev 另含完整 HEAD，candidate 另含实际 release identity |
| release subject | `wf_release_common.release_subject()` | 实际 tree 内容摘要、manifest 摘要、version、ref；排除 .git/pyc，路径排序及完整 SHA-256 |
| template slot | `wf_release_common.template_cache_slot()` | Python major.minor + deploy；candidate 加 version/ref，无内容/HEAD/dirty 摘要 |
| final plan | `plan.plan()` | 参数/选择器/当前 registry，只有 lease 内生成的 final plan 才能执行 |
| repro execution context | `repro_select.runtime_context()` | tool/SUT identity、平台、deploy、release subject、被测 release root 的身份摘要、candidate 已核 tag commit |
| red subject | `repro_select.red_subject()` | case/source/targets/helpers/runner/executor/build 输入、tool/SUT/平台、release subject；特意排除 deploy 和 root 定位 |
| case execution fingerprint | `repro_select.input_fingerprint()` | case 输入 + 本次完整 execution context，不用于跨 deploy 匹配 red |

内容摘要按规范路径排序、读取实际字节；必要文件缺失/不可读报错，不签发 None/unknown 身份，不把 mtime 当内容证明。`source_tree_files()` 枚举之外还需显式纳入 dev-manifest 与 build 工具；模板覆盖 full 子树是保守失效策略，测试脚本变化也可能重建模板，代价有意接受。新 runtime helper 自身进入摘要。

保留工具与 SUT 默认异解释器；共享 identity resolver 只负责解析/核验，不偷偷统一二者执行路径。模板初始化通过 f1_init → wfdrive.run 使用 SUT，所以两种 role 都进入模板身份；运行期间直接 import SUT lib 的 Python 代码也由 tool identity 覆盖。路径身份按以下固定对象计算，不能解释为 prefix 目录树内容：

`path_identity = SHA256(UTF8(canonical_JSON({invocation: normalized_absolute_invocation, executable_realpath: realpath(sys.executable), prefix: realpath(sys.prefix), base_prefix: realpath(sys.base_prefix)})))`。

JSON 固定键排序、ensure_ascii=False 和紧凑分隔符；invocation 从实际使用的单个 executable 定位，规范化为绝对路径但保留 venv 启动路径，不把它先 realpath 成基础解释器。sys.* 字段由实际启动的解释器探针返回；原始路径只在本地进程内参与计算，不写到 proof/cache/context。调用文件与实际 Python binary 的字节摘要另算，相同文件/同 role 在一次 barrier 内去重。禁止 walk sys.prefix、sys.base_prefix、site-packages、/usr 或 /softwares/python 来建立该身份；不宣称它是整个 Python 安装/依赖环境的完整指纹。同 binary、不同 prefix 路径仍得到不同 path_identity。

dev 模板安装记录内嵌 `source_commit`，完整 HEAD 与内容摘要同时必要；不能用 dirty bit 替代任一事实。HEAD 不可读时固定关闭 dev cross-run 模板 cache，退回 run-owned 模板；若初始化本身失败则照常失败。该判断在执行阶段构建模板前计算，preflight 不探测 HEAD，也没有需要跨 exec 携带的 HEAD 可用性决定。

## 3. Cache 发布、锁与生命周期

### 3.1 Release 的并发契约

为每个 canonical release root 使用固定 sidecar lock inode（root 外、不随 tree 替换、不 unlink；拒绝符号链接）。所有公开 CLI 和库调用都经过同一锁包装，内部 `_..._locked` 实现不再次开 fd 自锁。

| 操作 | 锁与行为 |
|---|---|
| `--ensure`/恢复/发布 | 非阻塞独占 flock；从恢复、输入核验、build、切换到 journal 提交都在锁内。竞争返回明确 busy，不改 cache，不无限等候 |
| `--check` | 非阻塞共享 flock；只读核验。发现未完成 journal 返回 recovery-required，提示在可获独占锁时 ensure；check 不恢复、不 build；runner 消费期的独占 lease 下明确返回 busy |
| runner 消费 release | 同一独占 lease 内完成 ensure/核验，随后保持该独占 fd 到全部 worker/repro 结束；不做锁降级、释放后重取或独立 ensure→lease 接力。外部 `--check` 因此可能暂时 busy |
| 嵌套 repro | 宿主侧验证祖先持有该 canonical root 的真实 lease 后只读消费，不再次 ensure/自锁 |
| namespace worker | 父 runner 始终持有 release lease，worker 只读挂载该树，不要求 user namespace 内读取宿主不可见 fd；不得从 worker 调用共享 cache ensure |
| 手工 ensure 与活跃 runner 竞争 | 独占锁失败，返回 busy；runner 不读被替换的一半 tree |

集成方式：在 `wf_test_release.py` 提供持锁的 runner lease wrapper。wrapper 在受外层 controller 监督的同一消费 PID 中取得并保持锁，然后用 exec 进入最终消费阶段；所有后代退出后由 controller 生命周期保证 FD 释放；只有 scope 内 PID/root/fd 的内核锁验证成立才接受 inherited lease。环境标记只定位验证对象，不是授权证据。进程取消使用现有 execution 清理协议，wrapper 不能先放锁再让孙进程继续读 tree。root fixture lease → 当前域结果状态锁 → release lock 是唯一锁顺序；公开 ensure/check 不反向申请 fixture/results lease。消费期保持独占是明确的正确性取舍：避免释放到重取之间被 ensure 替换；代价是外部 check 在 runner 整个消费期间 busy。

模板发布、恢复和同槽清理继续在 root fixture lease 下进行。candidate 校验统一使用 `prepare_candidate_repo.check(tree, version, out)` 的既有语义：结构/manifest/version、tag commit、clean 工作树、candidate meta 的 tree/commit 与可用 source tree 等价核对；不只调用较窄的 verify_repo。根 wrapper 在生成 release-context 前先核验一次；内嵌 repro 的 freeze 与有 eligible proof 时的 writer 最终 barrier 分别重新调用同一 Python validator，比较父已核 tree/tag/meta 摘要，起始失败不启动 worker，结束失败不提交 proof。独立 candidate repro 同样在 freeze/需要提交 proof 的最终 barrier 两处核验。无 eligible case 时不启动 writer、不更新 proof，本轮保持失败，不为一次已无证明可提交的运行单独增加 writer。此处替代重复 shell CLI 启动，不删校验，也不将 `wf_test_release.py` ensure/check 禁令误套到候选 validator。candidate 外部输入不写锁或 journal。

嵌套 repro 的发行身份交接采用一个明确内部入口，不把已有 WF_RELEASE_* 当作已验证身份：

1. 根消费 wrapper 在 dev 持有 release 独占 lease 并完成发行核验、或 candidate 完成候选核验后，在主 results prepare 之后原子写主目录 `release-context.json`；schema 1 记录 deploy、canonical release root、version/ref、manifest/output tree digest、已观测 runtime/build 身份，candidate 另记已核 tag commit、meta 摘要与这次 candidate check 使用的 tree/out/version 输入。该文件是身份字段唯一来源。文件路径与初始字节 digest 作为内部 handoff 令牌传给 `run_repro`，不写入内层会被 prepare 的 repro 结果目录。
2. `run_all.sh::run_repro()` 无论默认 build 或 --no-build、顺序或 --repro-concurrent，都显式走继承入口；不再靠 --no-build 使内层“只 check 一下”。`repro/run.sh` 首先调用同一 lease/context verifier 核对祖先 fixture/当前域结果锁，dev 还核对 canonical root 的 release 独占 lease；校验文件 digest/schema、请求的 deploy/root/version/ref 与文件一致。
3. 校验成功后直接从 context 派生 TEST_ROOT/TEST_VERSION/TEST_REF 与 WF_RELEASE_TREE/WF_TEST_LIB 等现有 harness locator，覆盖先前未验证的 locator；显式参数冲突在覆盖前报错。这个内部入口在旧 dev 分支的 --release-* 拒绝与发行初始化之前分流，不将父已核版本/ref 误判成独立 dev 请求。内层不调用 wf_test_release.py 的 ensure、check 或 check --json。祖先 fd 验证由内部 helper 完成，不调用尝试重新获取锁的公开 CLI。candidate 沿父 context 消费，起止 barrier 仍重核实际 tree/tag；不伪造 release flock。
4. 传递内部入口但文件缺失/损坏、digest 不符、root/version/ref 冲突或真实 lease 不成立，一律拒绝；不能回退独立 ensure/check，也不能悄悄按新 env 选择另一 cache。独立 repro 未请求内部入口时按自己的参数获取 fixture→当前域结果→release 锁并执行一次 ensure 或内部只读 check，复用 wrapper 的核验返回身份，亦不再第二次 check --json。
5. 根 runner 与内层 repro 的 freeze/state-writer 完整内容 barrier 仍按第 6 节执行；worker 只做快检，gate 只读校验；这个 handoff 消除重新拿锁和重复发行初始化，不允许省掉输入完整性校验。release-context.json 与 inputs.json 分工不同：前者交接已核发行和 lease scope，后者冻结本次 case/mode/证明输入，不形成同一事实两份可修改权威。


### 3.2 发布协议与恢复边界

测试发行 meta 从 schema 1 升 2；模板旧 meta 未版本化，作为 legacy，新增 schema 1。两种 cache meta 都记录完整 build inputs 和实际 output tree digest，旧字段保留有用的诊断信息，但旧 meta 不能命中。

所有输入先冻结，staging 构建完成后再重核输入相等，避免把变化过程中产物写成一个稳定输入的结果。release 完成双构建字节比较、tag 仓库生成、新 meta/owner；template 完成 fixture/init、repoint、身份/空态和 strict hygiene。只有全部成立后才开始替换。

tree 与 sidecar 不能视为单个原子对象。两种 cache 使用同一发布协议，适配各自 owner/validator，不开发通用事务引擎：

1. 锁内先处理已存在 journal。journal 限定在已校验 cache root 的同级路径，包含 transaction id、旧/新 tree/sidecar 的完整性摘要和归属；首次发布记录 old-absent，不伪造旧代。
2. 在独立 staging 准备新 bundle；旧 tree/meta/owner 在此期间不动。原子写 journal 后才把旧 bundle 移到该事务唯一 backup，安装新 bundle，完成最终路径 repoint/owner/meta/root 核验。
3. 新 bundle 全部核验成功才写提交状态并回收该事务 backup/journal。函数失败尽力立即恢复旧 bundle；无法验证时保留现场并非零，不吞错。
4. 被中断后 ensure/template 入口先恢复：新 bundle 与 journal 中预期新代完全一致则前滚；否则按 journal 逐组件恢复完整旧 bundle。旧代允许是旧 schema 或旧输入，恢复验证比对冻结的旧字节/归属，不误用“当前输入新鲜度”拒绝回滚。首次发布没有旧代时，只撤销本事务不完整新代，不误删 unrelated 路径。
5. 两代都无法完整验证、journal 越界或 owner 不符时 fail closed，保留现场。不能把 backup 当普通 stale 先清理；read-only check 只报告 recovery-required。

普通异常可清理本次 staging；SIGKILL 等中断不承诺立即无临时文件，承诺下一次合法 ensure/模板入口恢复后无可确认本事务残留。没有断电级 fsync durability 或同用户恶意篡改防护承诺。

### 3.3 模板槽位、迁移及容量边界

同一 results-cache 根内，dev 每个 Python major.minor/deploy 保留一个最新槽；candidate 每个 Python major.minor/version/ref 一个最新槽。槽名按 canonical tuple 的稳定编码产生，避免简单 sanitize 导致不同 ref 名碰撞。build_inputs 改变只使同槽 meta 失效。

这是容量与命中率的取舍：两个 dev checkout/worktree 共用 results-cache、Python major.minor 和 dev 槽时，若 HEAD 或 dirty/build 内容不同，交替使用同样每次 miss、重建和切槽；相同 version/ref 的 candidate A/B 内容不同时也是如此。既不能复用 A 证明 B，也不为此增加多内容变体/LRU；dev 可显式选择独立的 WF_RESULTS_CACHE 分开模板槽，但宿主 fixture/结果锁域仍按既有规则，不能因此并发修改共享用户状态。将该行为写入两份 README/spec。不同 version/ref 和 Python 版本的槽数量仍随用户测试集合增长，没有全 cache 容量上限；新规则防止同槽按每次 commit 无界增长，不宣称整个 cache 恒定大小。

成功发布后，只迁移同 Python/deploy/release 槽位且 owner.root、meta.root、身份字段完整匹配的 legacy key 及其 sidecar。旧 meta 缺 deploy/version/ref 等证据时不从目录名猜归属，保留并报告；无主/畸形/其他候选版本不自动清理。

README 提供只读列出路径、marker/meta 身份和大小的检查口径；用户明确选择某个旧槽后，持有 fixture lease 使用现有 fixture_scope.remove 对精确 owned 路径清理，sidecar 仅在身份一致时一并移除。无 glob/rm-rf 清全根的默认建议。开发本任务不手工清用户 cache。

## 4. 入口协议、锁域与真实进程拓扑

### 4.1 阶段与参数 carrier

`controller` 是监督进程，`consumer` 是最终执行阶段，不再混用名称。`run_all.sh` 内部 frame 只在参数最前面识别，语法固定：

```text
bash run_all.sh --_wf-internal <lease|controlled|execute> [该阶段的固定键值对] -- <原始用户参数...>
```

public 调用没有该前缀；用户原始参数中的保留 `--_wf-*` 选项被拒绝，不能传给 plan.py。入口首先剥离并校验整个内部 frame：stage、固定字段、字段类型、重复/未知字段、必需的 `--` 分隔符及祖先/lease 归属都验证完，才处理后面的 user argv。内部字段不会进入 `plan.parse_args()` 或 repro 的公开解析器；无 eval/字符串拼接生成 argv。拟用 `full/runner_protocol.py` 同一 encoder/decoder 定义 frame。frame 只能由统一 encoder 组装 argv 数组，各阶段用对应 decoder，不能由多个 shell 分支各自拼格式。

carrier 的固定字段如下，解析完成后只把分隔符后的原 user argv 交公开 parser：

| stage | 必需键（类型） | 其他阶段规则 |
|---|---|---|
| lease | --entry-pid（正 PID）、--results-root（规范绝对路径）、--results-explicit（0/1）、--scope-root（生产用 -，测试用规范绝对路径） | lease FD/PID 另由现有 lease helper 导出 locator，必须验证；不含 plan/context token |
| controlled | lease 字段 + --plan-file（路径）、--plan-sha256（64 hex）、--plan-size（正字节数） | 不接受 release-context token，不重新 plan |
| execute | controlled 字段 + --context-file（路径）、--context-sha256（64 hex）、--context-size（正字节数） | token 由持锁 wrapper 在写 handoff 后追加；不得再进入 lease/controlled |

非秘密字段可通过内部 argv 传递，但参数本身不代表授权；每次内部入口均验证相应祖先、scope 和实际持锁 FD。新内部 repro frame 形式为 `--_wf-inherited-release --context <path> --sha256 <digest> --size <N> -- <公开 repro argv...>`，同样先剥离并验证，再进入 repro 公开解析器。无内部入口则按独立调用处理；非法或验证失败不能 fallback。

具体进程链如下。PID 名称仅作说明，不写死数字：

| 位置 | 进程/阶段 | 锁与计划动作 |
|---|---|---|
| 0 | public bash A | 原始 argv/env → 一次禁写 pyc 的 no-write preflight；list/dry-run 在此结束。实际执行才 `exec fixture_scope lease-run -- bash run_all.sh <lease frame>` |
| 1 | lease-owned bash A（第一次脚本重入，exec 保持 PID） | `lease-run` 已按顺序取得 fixture lease 与当前结果锁域；shell 验证它们，再生成唯一 final plan。claim/prepare 后原子写 plan.json 并计算 token；然后 exec `execution.py --runner-control ... -- bash run_all.sh <controlled frame>` |
| 2 | Python controller A → controlled bash B（第二次脚本重入，新 session 子进程） | controller 持有并显式传递允许的 fixture/result FD，监督 B 及其后代的超时/取消；B 不再 preflight/plan。dev 时 B exec release lease wrapper；wrapper 在同一 PID B 取得并保持 release 独占 FD、核验发行、写 release-context，再 exec execute frame。candidate wrapper 不取 dev release 锁，按第 3.1 节核候选后同样 exec |
| 3 | execute bash B（第三次脚本重入，exec 保持 PID） | 验证 controller A、fixture/result/domain、dev release FD 和 handoff token；读取一次 final plan 字节核验、解析后执行单元与 repro；不计算 plan、不再次 ensure/check，不再 reexec 同脚本 |

同一公开 run 有三次脚本重入，但只有两次计划计算：public 一次 preflight、lease-owned 一次 final。release wrapper 采用持 FD 的 exec，而不是再建立未声明的等待父/子进程；外层 execution controller A 继续监督 PID B 的整个生命周期。controller 在 Python Popen 启动 controlled B 时显式 allowlist pass_fds 所需 fixture/result FD；lease-run、release wrapper 及 shell 的 exec 保留已标记 inheritable 的所需 FD。普通探针不传全局 lease FD，不继承任意 FD；取消时杀掉并等待全部后代后才结束监督。consumer 的 release FD 不通过 worker env 宣称可用；host/domain 验证见第 4.2 节。

list/dry-run 摘要由 plan.describe 渲染到 stderr，stdout 空；直接 plan JSON stdout 恰为一个对象。public 在给默认 results 赋值前记录原始显式性，内部 carrier 原样传递该事实，重入不重新猜测；默认路径采用原入口 PID。preflight 不探测 HEAD/runtime，dev HEAD 可用性在 execute 构建模板时决定，无需跨 exec 传播预判。

final plan 只落在主 results/plan.json：prepare 完成后写规范 UTF-8 JSON，产生 SHA-256 和字节长度，并冻结 user argv/registry 摘要。execute consumer 使用 O_NOFOLLOW 读取普通文件的同一份字节，先比内部 token、schema、args/registry，再由这份已验证字节解析并执行；缺失、内容替换或不匹配拒绝，不再算 plan，也不使用 preflight 补位。controller/wrapper 可为定位和安全 setup 读取并核同 token，但不能重新生成或替换计划；执行所用计划只来自 consumer 核验的字节。summary 中的 digest 只用于诊断，不产生额外 digest sidecar。

### 4.2 结果锁域与测试隔离

生产默认域仍使用 `/tmp/wf-test-results-<uid>.lock` 固定 inode；所有 cache roots/results 目录共用一个，避免每 run 永久 sidecar。锁采用 O_NOFOLLOW、regular file/UID 校验，不 unlink，不进结果 prune；同域竞争返回 busy。root run/独立 repro 在结果 claim/prepare 前取得并保持到消费结束；显式 plan 镜像在目标只读预检后短期持锁、锁内复验，只写 plan/必要 marker。不同目录显式镜像也会被同域活跃 run 拦住，普通无显式结果的 list/dry-run 不触锁、不创建文件。锁顺序为 fixture → results domain → release；plan mirror 只取 results domain，不能反向申请 fixture。

新增显式测试域 `WF_TEST_SCOPE_ROOT`，由 `fixture_scope.create_test_scope()` 建立 owned 临时根并传入真实 CLI。scope 是 runner 管理对象的所有权边界，**不是拦截测试脚本任意 open/mkdir 的文件系统沙箱**。

#### 管理对象与生命周期

- root 必须是当前 UID 拥有的规范绝对临时目录、无 symlink；marker 固定 `{schema_version:1, owner:"wf-runner-test-scope-v1", root:<canonical scope>, uid:<actual uid>}`。唯一测试结果锁为 `<scope>/locks/results-<uid>.lock`，不以任意 lock-path 或 WF_RESULTS_CACHE 代替域验证。
- scope resolver 只检查 runner 管理写入口：结果目录、cache/template/test-release 的 tree/meta/owner/journal/lock、proof state、由 runner 分配的主/legacy fixture 根、pycache 和合成 HOME。其解析后的目标必须在该 scope 内；越界/坏 marker 写前拒绝，不回退真人目录或生产结果锁。源仓库、只读候选输入可以在外部，不因 scope 获得修改权。这个保证不扩大成“所有 suite scratch 都在 scope 内”。
- `RunAllContractTest.setUpClass()` 只创建一个空 owned scope 和缓存池布局，不在 import/default T0、类 setup 或 plan-only 之前急切 build。相同测试进程内该慢契约类复用 pool，tearDownClass 先等待/关闭全部子进程和 FD 再回收；进程异常中断的 owned scope 不由别的测试猜测删除。
- 正常不变输入的真实 dev 调用共用 `pool/test-release/<version>` 和 `pool/results-cache/template/<slot>`；每个测试 case 分配独立 `cases/<case>/state` 和合成 HOME，同一 case 的多次调用显式共用该 state（例如 dev red→candidate auto）；每次 runner 调用再分配独立 `cases/<case>/calls/<id>/results`、主 fixture 根和 pycache。state 不跨 case 共享，需要 fresh-state 的调用另用私有子目录。正常 candidate 可以复用类内只读候选与其对应 template 槽，但不因此构建 dev test-release。锁/租约仍逐 run 获取和释放，不跨测试继承 FD 或 handoff token；只复用经过新鲜度/所有权验证的磁盘 cache。
- 故障注入、旧 schema、stale、fresh-empty、取消发布以及候选篡改测试使用 `private/<case>/<call>` 下独立 cache/candidate 副本或空根，不改共享 pool；辅助 warmup 不得把预期 stale/--no-build 缺失路径提前建好。`--no-template` 仍真正绕过已有 template，不能为省成本改变被测模式。
- plan-only/非法参数/拒绝路径使用仅建 owned scope 的 helper，调用前后快照，不跑 warmup；取消用例显式先完成一次共享 cache warmup，再开始等待测试日志的 15 秒窗口。warmup 走与正常 runner 相同的构建/命中检查并断言退出成功，不导入真实用户发行、不跳过失败。
- r67 fake harness 仍按自己的短生命周期在私有 tmpfs 创建本地 scope；保持假发行/夹具桩，不为假树测试引入真实双构建。正常真实调用只在 cache 输入身份变化时重建；更改源码必须失效，不能以“共享”跳过核验。
- 新测试域不取消现有 fixture lease：真实 full fixture 契约测试仍要求该旧全局资源独占。scope 结果锁测试通过拒访/busy 桩而非获取真人生产锁建立前置。每 scope 只有一个结果锁，默认无显式结果的 plan-only 只读 scope 校验且不创建锁。

#### 套件 scratch 与逃逸探针的边界

| 写入种类 | 约束及验证 | 本任务不承诺的事 |
|---|---|---|
| runner 管理对象 | 上述 resolver/owner/路径/lease 规则；测试域的写目标必须在 scope 内 | 不允许以 scratch 名义把 cache/state/root locator 指向真人目录 |
| suite 自己生成的固定名/临时 scratch | 维持既有执行域：并行单元的 `/tmp` 是私有 tmpfs，随 namespace 生命周期销毁；宿主串行仍是宿主 `/tmp`，由既有 fixture lease 排除 harness 间竞争 | resolver 不截获普通 open/mkdir；不宣称宿主串行没有临时残留、没有与其他非 harness 同名文件冲突的可能 |
| 项目外 symlink-escape 目标 | 必须在 fixture/project 之外，检查 SUT 拒绝并未产生目标文件；scope 内的兄弟目录也可以是合法项目外目标 | 不能把“project 外”误等同“test scope 外”，不能放宽 SUT 的路径校验来让用例通过 |
| 新增边界回归的 scratch/probe | 由测试创建可证明所有权的唯一临时目录，设 fixture 和 outside 为 scope 内兄弟目录；仅回收本次创建的目录。验证 scope 外 runner locator 拒绝与项目外 escape 拒绝是两个独立断言 | 不去真实宿主 `/tmp/outside-target` 创建、删改 sentinel 以证明隔离 |

`r65/r79/r90/r53/r7r15` 等既有 suite 的固定 `/tmp` 写法及 r7 的 outside-target 保留语义，不批量迁移、不新增 suite scratch manifest，也不以 basename/glob 或“新增文件快照”自动认领/清理宿主文件。需要复核固定路径用例时，正常并行使用现有私有 tmpfs；串行对拍继续忠实报告宿主 scratch 的既有限制，不改成另一个 namespace 而仍称原串行域。`TMPDIR` 注入不被当成覆盖字面量写入的办法，也不在本轮全局改变它以免改动 fixture_scope 的临时根判定。测试只清理它能证明自己创建的管理对象，固定旧路径若已存在则不凭名字删除。

### 4.3 Mount namespace 边界

宿主结果锁只限宿主编排、plan mirror、gate 后 state-writer 使用。取锁时记录当前 `/proc/self/ns/mnt` 的 kernel identity 以及锁 FD 的 device/inode/UID；host descendant 的继承核验必须在路径 open 之前确认当前 mount namespace 与锁 holder 的域一致，并核真实 ancestor/FD/kernel flock。namespace.py 保留只用于边界判定的原宿主 mount identity 与 unit-domain 标记；它们不提供锁权，但 helper 必须以当前 kernel namespace 比对。读不到继承域或锁事实就拒绝，不能按同名路径再建一把锁。该规则约束本 runner 管理的 namespace，不能据此声称能识别任意外部独立启动的 unshare 域。

`namespace.py` 在覆盖 /tmp 前记录宿主 mount 域，覆盖后关闭当前 worker 继承的宿主 results/release FD 副本（不 unlock、不影响父仍持有的 open-file-description），显式清除相应 FD/PID/domain/context locator、宿主 WF_TEST_SCOPE_ROOT 与 final-plan 内部 frame 变量（挂载给该单元的结果输出路径是委派写入范围，不据此重取任何宿主锁），设定 unit execution domain；worker 对共享结果的管理写权限仅限父分配的 per-unit 文件；它仍可按第 4.2 节运行自己的 fixture/scratch，不能调用生产 results-lock acquire/verify、全局 proof commit 或共享 release ensure。生产锁 helper 在 unit domain 或 mount namespace 不一致时先拒绝，**不能创建或验证私有 `/tmp/wf-test-results-<uid>.lock` 并把它当宿主锁**。宿主保留原 lease 到 worker 全部退出，隔离域靠 parent scope 与只读挂载保护。

显式 test scope 的 namespace 内 fake runner 是不同测试域：可以只在自己的 scope 内创建测试锁，但要报告 `domain=test` 且不能声称继承宿主锁，也不能产生生产 proof。现有 namespace 私有 fixture lease 保留，不把它混同宿主结果状态锁。不能只信 WF_NAMESPACE_READY 的 env 文本，kernel namespace/FD 校验也是继承入口的必需条件；同 UID 恶意伪造仍不在本任务威胁模型内。

### 4.4 镜像与 list 的验证时点

镜像契约在 plan-only 返回时采样。之后真实执行 prepare 删除旧 plan 再写 final 是允许行为，需另测其来源与 token；不要求旧镜像字节跨 prepare 不变。独立 repro --list 先纯 select_cases/describe，保持 stdout case+mode 列表，在 fixture/results/release lease、pycache、state/runtime 之前返回。

## 5. Repro 的主体、实际执行与单一冻结文件

### 5.1 保留 candidate auto

不能用单个完整 fingerprint 同时表达 red 可迁移主体与 green 实际执行来源。拆成两个有域的身份，来源都由第 2 节函数唯一生成：

- `execution_fingerprint` 包含 deploy、真实 release root identity、candidate tag commit、release subject 和 runtime。每次 worker 的结果及 green proof 都记录它。
- `red_subject_digest` 包含 case/script/meta、完整 source/targets、helper/protocol/executor、构建输入、tool/SUT/平台和 release subject。它只排除 deployment 标签、绝对 release 根及各自生成仓库的 Git commit；这些不是安装 repro 注入内容本身。release subject 的文件字节、manifest、version/ref 仍必须完全相同。
- red proof 记录 red_subject_digest + 产生它的 dev execution_fingerprint + verified phase；只有 dev red 目标断言确实变红且整个验证链成功才产生。candidate green 从不更新 red。

| 请求 | red proof 判据 | 实际执行 |
|---|---|---|
| dev auto | 同 red_subject 的有效 dev red | 有则 dev green，无则 dev both |
| candidate auto（candidate-clean） | 同 red_subject 的有效 dev red，且 candidate 已核 release subject 与该 proof 完全一致 | 有则 candidate green；无则拒绝并列出需在 dev 用同内容/version/ref 验证的 cases |
| candidate green | 无 red prerequisite | 正常 candidate green，不签发 red |
| candidate red/both | 不允许 | 在 plan/selector 都拒绝 |

这保留了 dev red → candidate auto 的已有用途，但缩小到内容和运行身份严格相同的证明；任意 candidate A 不能因版本名相同继承 B 的 red。tag commit 不跨仓库匹配，但 candidate 自己的 commit 仍进 execution 身份且起止复核。改变 deploy 不必使 red 主体变化；改变 release 内容/version/ref、解释器或 case 输入必须使 red 主体变化。

如果源树或候选内容不同，出口是用同一内容/version/ref 的 dev 测试发行重新验证 red/both，或显式 candidate green；不能把报错改成自动降级 green，也不让 candidate 上注入。未知 targets 不签发可复用 red，维持原有保守行为。

### 5.2 单一冻结文件与明确的提交进程

bundle schema 1：`inputs.json = {schema_version, execution_context, cases}`。cases 包含 mode、execution_fingerprint、red_subject_digest、输入分项摘要和 auto 所消费的 red proof 摘要。selector 的 select_cases/mode/digest 为唯一产生实现。文件只有一个权威来源，TSV 只是兼容派生物。

进程拓扑明确区分父编排 shell、worker、只读 gate 和 state writer：

```text
run_all execute B
└─ repro/run.sh R（宿主内嵌）或 standalone repro parent R
   ├─ serial / xargs -P → _worker.py W（每 case 独立结果，不写全局 state）
   ├─ results_gate.py G（只读校验与摘要，绝不调用 commit_state）
   └─ repro_select.py commit-state S（一次 writer 子进程，唯一全局 state 写入口）
```

R 只编排提交，不能把“parent 单写者”理解为所有写入必须在 shell PID 内。S 是 R 串行启动并等待结束的唯一 writer，逻辑父写者包括这一个指定命令，不包括 G 或 W。直接 commit-state CLI 与 S 执行同一个安全入口：必须验证真实祖先 fixture lease、当前域结果独占锁、mount/domain 一致，dev 验证 release 消费 lease，candidate 则走其 validator；没有这些事实一律拒绝。库函数 `commit_state()` 本身也走这些检查，不能只在 main 包一层。

冻结到提交的顺序：

1. R 完成 results prepare 后，在启动任何 W 前冻结初始观测。candidate 此时重跑第 3.1 节的完整 validator；dev 复用已核 release context 并核真实父锁。原子写 inputs.json 一次，R 在内存保留初始 byte digest/长度；外层 release-context 在主结果目录，不会被内层 prepare 删除。
2. env 只传 `WF_REPRO_INPUTS_FILE` 的绝对路径，不传第二份 JSON；串行和 xargs W 继承同一路径。W 读 bundle，核 schema/case/mode/context、按第 6 节快检，结果记所读 bundle digest 和相位。缺项拒绝，不使用 current fallback。
3. R 等全部 W 退出后启动只读 G。G 可在无 lease 下用于诊断，因为它不修改 state、不恢复缓存；它读同一 bundle/结果/日志，与 R 传入的初始 digest/长度比对，输出结构化报告和既有机器汇总。`results_gate.repro_gate()` 移除当前 `repro_select.commit_state()` 调用，抽取 `validate_repro()` 作为可供 G 与 S 复用的纯校验函数；不复制另一套 PASS/phase 规则。
4. `structural_ok=false`、bundle 被换、缺失/畸形/重复结果均禁止提交。普通 case 断言失败与结构失败分开：前者仍可按现有行为提交其他 eligible pass case，不能简单写成“gate rc!=0 一律不提交”；全部失败则不写 state。R 只有看到结构有效且存在 eligible case 才启动 S，并传 inputs 路径、初始 digest/长度及本轮 results 范围；不能只凭 report.json 文案获得写授权。
5. R 用 argv 直接启动 Python writer S，已核 fixture/result/release FD 必须仍标记 inheritable 并经 shell exec 继承；如途中经过 Python subprocess 边界，那个创建点必须显式 allowlist pass_fds，不能依赖 Popen 默认行为，也不新增未声明的 launcher 常驻进程。env 只给 holder PID/FD/path/domain 定位，不是凭据。`verify_write_leases()` 用 `/proc` 祖先链、fd device/inode、holder fdinfo 的 kernel flock 和 mount/domain 逐项核对；不存在、伪造、已关闭或 namespace 不同均在写前拒绝。非继承 FD 或 parent 退出不能静默自己拿新锁代替。
6. S 在持有这些同一 lease 的范围内重新读取初始 token 指向的 bundle，复用 `validate_repro()` 核实际结果/日志，并执行唯一的最终完整输入 barrier（包括 candidate validator）。全局 context/bundle 改变则整批拒绝；个别普通 failed case 不更新其 proof。S 原子读合并写 state，给 R 返回结果；writer 出错必须使本轮非零，R 最终汇总不能再报 GATE-OK。G 不做最终完整 barrier，避免重复全树哈希。

初始 digest 是完整性令牌，不是第二份 context 真相。检查读取同一文件后解析同一字节，不以 mutable gate report 当提交许可；同 UID 恶意 TOCTOU 不在威胁模型内，正常外部内容变化由最终 barrier 拒绝。

### 5.3 State 迁移与锁继承

proof state schema 2 → 3；green execution proof 与 dev red subject proof 独立，green 不能续 red。schema 1/2 只保留 legacy，不推导 context/subject、不重复套娃迁移；未知/损坏 schema 原文件保持且非零。唯一写入函数是经第 5.2 节 lease 验证的 commit_state，由指定 S 调用；直接命令也必须同样验证，G/W 无写入权。

host R/G/S 的 FD 继承由各自 subprocess 创建点显式控制，不依赖 Python Popen 默认继承 FD。G 不需要 FD 作为写权；S 需要已验证 holder 仍存活的 FD 和 ancestor 信息，控制进程持锁直到 S 与其后代退出。namespace 单元内禁止调用生产 writer；测试 scope 只能提交到 scope 内合成 state，不能凭私有 fixture lease为宿主 state 背书。worker 普通失败可保留旧 proof，但任何新 proof 都必须有本轮通过相位、执行来源和输入核验；legacy 不计本次通过、不改变分母。

## 6. 内容核验成本与可信边界

不能把当前 check_meta 的成功当实际 tree 完整性的证明：manifest 自身自洽并不证明其声明文件未被改动。meta 保存 output_tree_digest 作为预期值，必须在明确 barrier 与实际读取摘要比较。

按 run 共享的观测边界如下：

| 边界 | 完整观测 | 复用范围 |
|---|---|---|
| release/template 发布 | build 开始冻结 inputs；发布前重算 inputs/output，重新比对 | cache 当前事务，不跨 run 无条件复用 |
| repro freeze | 各 tool/SUT role 一次解析/哈希；release tree 一次；source/helper/full 子树公共摘要一次；case 脚本/target 按 case | 本次 bundle 的全部 cases/worker，禁止每 case 重跑公共全树扫描 |
| worker 前后 | 严格读 bundle，比较调用 locator/角色与 case 文件身份；文件集合/stat 索引变化只用于提前拒绝或触发重算 | 索引不是内容证明，不能据此跳过最终 barrier |
| proof commit 前 | 指定 state-writer S 新进程重算全套公共内容/runtime/release，candidate 调用同一完整 validator 一次，核开始观测；只读 G 不重复完整扫描 | 同一 fixture/results/release scope、同一 bundle 的这次提交；不跨 run 持久缓存 |

完整重算分摊到 parent 的两个 barrier；worker 不各自重算 release/binary/source 全摘要。传入冻结 context 后再次计算相同旧值不算重核，最终必须重新观察实际输入。source/tag/tree 若被其他进程改变且维持到 barrier 会拒绝证据；不保证观察到两屏障间被修改再原样恢复的瞬态。合作 ensure 发布由 release lease 阻止，不能用屏障替代该锁。

记录 `identity_seconds`、完整公共扫描次数、路径字符串哈希数、binary 文件读取数/字节数和 tool/SUT probe 次数，不混淆 CPU 累加与墙钟。实施期先采同机旧实现 baseline，再做三次 warm full green 新旧中位数对比，另记录一次 cold rebuild 与串行；目标新增 warm identity 墙钟 ≤3s、full 中位增幅 ≤10%。这是本任务验收证据，不新增任意机器上的硬 wall-clock gate。release subject digest 在 run 的 freeze barrier 计算一次并供所有 cases/worker 使用，proof commit barrier 再完整重算一次；不得每个 case 重扫。超标先排除 N×case 重复计算/多次 preflight；不能复用未经实际 tree 核验的 meta 来过预算。规划阶段没有实测新增成本，不写估测为事实。


### 6.1 慢契约隔离成本（与 full 身份核验分开记账）

旧 `run()` 只注入 WF_RESULTS_CACHE，未普遍重定向 dev test-release；可能命中真人 cache，但不是可保留的性能前提。类内 owned cache pool 用于避免**相同不变输入每个测试都冷建**，不是跨用户 cache 复用。

| 场景 | 构建预期与观察项 |
|---|---|
| 首个正常 dev 真实调用或取消用例的显式 warmup | scope 内缺发行时一次双构建校验序列（两个 builder.build），缺模板时一次 fixture/init；记录各段墙钟、cache identity、build 次数与总准备时间 |
| 同输入后续正常 dev 调用 | ensure/check 仍校验，发行实际 build 次数 0、模板实际 build 次数 0；每调用仍有独立 fixture clone/执行/清理，不把它们算成“免成本” |
| candidate 真实调用 | 只记录候选准备/check、candidate template 首建与命中；不要求或计入 dev test-release 双构建 |
| plan-only/非法计划 | 自己的调用窗口 release/template 实际 build 次数均 0；不能因 class/setup warmup 隐藏副作用 |
| 冷建、损坏、stale、迁移/发布中断专测 | 用 private cache 故意支付冷成本并单列，不以共享正常池稀释故障证明；私有失败不能污染下一条正常测试 |
| teardown | 每调用 results/fixture 与每 case state/HOME 的回收时间、类 pool 的最终回收、终止子进程/关闭 FD 成本都纳入 class 总墙钟；能确认归属才删 |

测试 helper 的同一逻辑 case deadline 仍是现有 900 秒：该 case 的 warmup/prepare/测试调用共用剩余时间，不能每次子调用重新获得 900 秒；进程取消后的有限清理按既有 cleanup timeout 另行报告。取消探针的 15 秒只用于 cache ready 后等目标执行日志，5 秒清理等待保留并单列。warmup 失败按阶段报错，不自动反复重建、不 skip、不增大 timeout，不允许退回用户 cache。

实施验收分别记录：旧 helper 的缓存命中背景、新隔离类首次 cold 总时间、相同输入 warm 调用中位数/最大值、整类总墙钟、故障专测冷成本、每 case 900 秒剩余量与取消窗口余量。旧实测与新实测必须说明 cold/warm 和隔离口径，不拿真人 warm 与隔离 cold 的差直接称身份算法回归。新增 full identity 的 ≤3s/10% 目标继续适用其原范围，不能代替这个慢契约账目。相同输入第二条正常测试再次出现发行双构建或模板首建、任何 case/cleanup 超时、共享池被前一故障污染，都不满足验收；先查 pool 生命周期/输入失效/准备阶段归属，不以改 timeout 或放松隔离解决。规划阶段尚无新实现的 cold/warm 测量，不能推断现有 900 秒一定够或必然超时。

## 7. 兼容性、风险和验证归属

- 旧 cache 正常 miss 并安全重建；初次新 schema 会冷启动。journal 不完整先恢复；只读 check 返回 recovery-required，恢复入口是 ensure。
- 共用 cache 的 dev 多工作区与同 ref 异内容 candidate 会抖动，其他版本槽随集合增长；只做明示容量说明与精确 owned 清理，不增加后台/LRU。
- 旧 proof 首次 auto 要重建 dev red；candidate auto 保留，但必须实际 release 内容/version/ref/runtime 一致。
- 显式 plan 镜像增加必要 owner marker，保留旧数据；真实执行 prepare 仍能删除旧计划并写 final。stderr/stdout 兼容性单独断言。
- identity/helper、slot/schema、阶段重构和 bundle 变更一起同步 r67 假树 COPY/STUB/SPECIAL、hygiene 引用测试、results_gate、README/spec；假树不引用真实用户 cache。
- 既有 suite 宿主串行 scratch 不由 scope resolver 全局约束或自动清理；本轮不批量改脚本字面量，不声称 OS 级 sandbox。D1 真宿主压缩仍未自动覆盖；WF_SLOW_TESTS 明确启用。验证矩阵与执行次序以 implement.md 为准。
