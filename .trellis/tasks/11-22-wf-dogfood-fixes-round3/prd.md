# wf dogfood 三轮修正——traffic_monitor 实测问题收口

## Goal

以质疑角度核验两份 agent 分析报告（wf-find-a / wf-find-b）与
`docs/workflows/wf/analysis/backlog-dogfood-round2.md` 的「下一任务待办」，
对 `docs/workflows/wf`（模块源码）与三份上位稿做**非补丁式**修正，
并交付两个已裁决纳入的既有声明边界特性：会话身份轮换（P0-1）与
upgrade --apply / 回传闭环（P0-2）。

核心约束（用户 2026-11-22 裁决）：wf 在指导 AI 使用的前提下发挥 AI 自身最大性能——
**明显需要机械逻辑的转化成机制实现，其余保持最大指导 AI 使用**；不为修正新增
独立层级或 skill（判断指引落进既有 skill 的判据位点）。修正不引入新问题、不留问题遗留。

## 输入与证据边界

- 两份报告的每条指控已经主会话逐条对照源码独立核验（非采信报告结论）：
  - a 组 4 项 P0 全部成立（backlog「已核验成立、未实施」复核一致）；
  - b 组 P1-3/P1-6/P2-9/P2-11 成立；P0-1/P0-2 成立（backlog 登记为既有声明边界）。
- 用户裁决（2026-11-22）：
  1. **P0-1（会话身份退化为进程锚、Codex 无适配层映射）与 P0-2（upgrade --apply 仍是桩、
     dogfood 修复无法回源）一并纳入本轮**；
  2. K6 commit 双轨：**删 authorize 的 commit 类，声明 finish 决定 commit_grants 为唯一通道**；
  3. 控制面锚点：**Check 锚点增加 control_plane_digest 非交付维度**（旧 pass 不能静默复用，
     不新增阻断）；
  4. 单 reviewer：**允许"单 reviewer + 人明确接受残余风险"的有记录降级路径**（不默认、留痕）。
- 事实基础（本轮研究核验）：Codex hook 载荷携带 session_id（本仓库
  `.codex/hooks/inject-spec-context.py` 已在消费）；部署表
  `install.py PLATFORMS["codex"]` 已声明 `host-hook:SessionStart`（user-declared，
  /clear 变化已实测）但无任何消费者；DSH 已有 `env:DSH_SESSION_ID` 声明与
  d1 实跑测试。设计稿/机制稿中「回传」（框架修复回源）无既有机制概念，属新增设计。

## Requirements

### W1 a 组 4 项 P0（机制对齐，全部为"能稳定计算但没接通"）

- **W1-a1 content_bound_patterns 合并遗漏**：`record_authorization` 的同动作累计
  合并段并入 `content_bound_patterns`（与 paths/digests/materials 同型并集）。
- **W1-a2 机械修订路由收口**：路由句与草稿指向真实入口 `task-approve`
  （choice=机械修订，等价链核验后不重复人批）；`task-replan --draft` 移除会被
  正式执行拒绝的 `choice=机械修订` 骨架；`task-approve --draft` 补机械修订骨架
  （人按实际类型留一条；机械修订条目必须在占位文案写明前置——**仅本任务已有
  批准后使用**，未批准阶段删除该条，否则照抄骨架必被
  `WF_APPROVAL_MISSING` 拒）。**口径审视结论（设计稿记录）**：机械修订仍需人签
  choice=机械修订 决定——机制能核机读块等价，但无法替人判 PRD 散文的"只改排版/转义"；
  "不重复问人"由"不重复批准"承载，不由"零人签"承载。
- **W1-a3 验证日志物化接通**：`write_materials` 读 Check 记录真实字段
  `started_at`（与 `check-logs/<started 去冒号点>` 目录命名同源），使日志复制
  分支在真实数据上执行；补端到端断言（真实 Check 记录 → materials/check-logs/
  存在 + tests.json 带 logs 清单）。
- **W1-a4 OSError≠删除**：`covers()` 的当前内容读取改用
  `records.file_digest_state` 三态归因：`missing` 才走删除例外（确认时存在、
  当前已删 ⇒ 覆盖）；`unreadable` 按未覆盖处理（无法核对即未覆盖）。
  删除既有"except OSError 折成 None"的内联解读。

### W2 b 组收口（指引补强 + 三项已裁决设计变更 + §1.1 偏差收口）

- **W2-1（裁决②）K6 commit 通道统一**：authorize `ACTIONS` 删 `commit` 类
  （record/show/help/守卫清单同批）；K6 五类不可逆动作**不变**，第①类（提交）
  的确认通道声明为 finish 决定 `commit_grants`（唯一通道）；cli.py 守卫清单
  文案修正（`vendor` 不是动作类——真实守卫面为 delete/expand/repo_rules/export）；
  机制稿 K6 登记段与设计稿 §6.5 K6 通道句同批改。
- **W2-2（裁决③）control_plane_digest 进锚点**：`fingerprint.check_anchor` 的
  键白名单（现十键）增第 11 键 `control_plane_digest`（vendor 脏路径集合的
  内容指纹，单一来源取分类 v 桶）——**常开键**：v 桶空时为常量摘要、非空时随
  vendor 内容变化。既有 Check 因新增锚点输入**一次性全量失效**（升级后需重跑
  Check，`WF_CHECK_STALE` 既有语义，不新增阻断码）；不引入"条件键"新语义
  （条件性并入哈希是新增机制概念，违背避免新问题约束）。分类失败的归因
  **不改写既有错误码**：`classify_candidates` 对入口快照问题本就抛
  `WF_RECORD_INVALID`（scope.py 既有口径）——原样传播；仅**非契约异常**
  单独归因 `WF_SCOPE_UNRESOLVED`（不折成缺锚点输入的
  `WF_APPROVAL_MISSING` 误归因）。`anchor_parts` 增可选 `classified` 参数
  （与 `delivery_set` 同型：Check 流程传入已算分类，只读面（judgments
  show/archive --draft/stop --preview 经由的锚点计算）自行计算——性能与
  降级口径同批登记）。锚点输入登记进机制稿 §3.2（键集合十→十一键 +
  一次性失效声明）/§3.5。
- **W2-3（裁决④）单 reviewer 降级留痕**：`review-decide` 单 reviewer 分支从硬拒
  改为"有人签残余风险接受记录（quote/by/at + 声明）才允许产出 verdict，默认仍拒"；
  接受记录落任务记录、降级事实（degraded: single-provider + acceptance 引用）进
  判定 facts 与 review-status 投影；两位异种 reviewer 仍是复杂任务默认要求。
  机制稿 §9.2 + 设计稿 §6.5 + wf-review 适用面同批改。
- **W2-4（指引）审查序列补外发确认步**：wf-continue「复杂任务审查」、
  wf-review-action、wf-finish 在 review-launch 之前补"先取人外发范围确认：
  `authorize record` 一条 choice=export（task+materials+quote/by/source）"，
  与入口既有门禁/exits 对齐（机制不改）。
- **W2-5（机械）review-notes 帮助路径**：`--review-notes` 帮助文案改为指向
  `status` 回显的真实任务目录（`<id>-<slug>` 形态），不再给会被当成外来改动的
  `<id>/notes.json` 示例。
- **W2-6（机械）archived 绑定的 next 文案**：`task-new` 对已绑定旧对象报
  WF_BINDING_MISMATCH 时，绑定对象已终态的 next_ 改为与 enable 终态出口同口径
  （开新对象需新执行边界/新会话/换新会话标识），不再给出对 archived 无效的
  "continue/bind" 指引。
- **W2-7（指引+记录点）vendor_dirty 确认留痕**：vendor 改动归属确认
  （回源仓库立项/另开任务/保持现场）从"口头不可核"升级为可审计记录：
  `judgments` kind 域（机制稿 §9.4，既有八中文类）增中文类 `框架改动`。
  **落点定死一种形态**（judgments add 只有 `--task/--file/--attestation`，
  无 --kind 旗标）：判断文件条目 `{kind: "框架改动", decision: <归属去向>,
  basis: <依据>, outcome: "applied", by: "human"}` 经 `judgments add --task
  <id> --file <文件>` 入库（decision 是判断内容字段、框架不判决其内容——
  judgments §5.4 分工；**不引入 quote、不用 --attestation**，人在场留痕由
  by: "human" 承载）；task-check/archive 的 vendor_dirty facts 消费该确认；
  不阻断、不参与判定（纯事实投影）。`cli.py` 判断偏好（prefs --kind）与
  judgments 帮助里的 kind 枚举同批同步（help/域表一致性断言覆盖）。
- **W2-8（维持现状，理由留档）repo_rules 逐文件内容绑定确认维持**：
  K6 第⑤类保护值恰在"每次环境级规则内容变化都重新确认"；dogfood 摩擦源是
  任务中途手工改规则文件（被正确拦截），非误伤。不做任务级合并、不降档。
- **W2-9 §1.1 三处内容偏差收口**：
  - 「本地完整路径」行补环境边界说明（复杂任务审查需两个异种审查 CLI，
    或单 reviewer + 人接受残余风险，见 §6.5）；
  - 「固定流转程序化」清单的"三方升级匹配"随 W4 交付落地（不再指向能力桩）；
  - 工作习惯/自动信封三处复述收敛为单一完整定义位（wf-continue）+ 其余一处
    判断句 + 指针（与「指引就地、不成层」一致；含 wf-review-action 复述收口）。

### W3 P0-1 会话身份（既有声明边界交付）

- **W3-1 换新会话标识命令**（宿主无关）：`wf enable --new-session`——人在
  当前执行边界显式开新会话身份；前置为旧会话绑定对象已到终态（或已释放），
  否则给出处置出口；新身份注册路由并使自动解析优先命中新会话（旧会话路由/
  附件保留为历史，不删除）；旧对象在途时不得轮换（WF_BINDING_MISMATCH 语义）。
  wf-start 的"尚未交付"句同批改为真实指引。
- **W3-2 Codex SessionStart 适配层**（部署表声明的落地）：
  - **宿主身份会话的建立语义（四态解析次序）**：`_auto_resolve`/`auto_session`/
    `cmd_enable` 三处定死——① 映射命中且 host 身份**有**附件：按既有解析
    续用；② 映射命中、host 身份无附件、但**锚点路由上有在途会话**（有附件
    且绑定对象未终态）：**续用该既有会话，不改写、不接管**（在途会话的身份
    不因 hook 上线/换聊天被夺走——否则在途任务只能靠 bind --task/显式信封
    接续，正是 P0-1 要消除的摩擦；与宿主不可区分时的现行"同边界=同执行会话"
    语义一致，并发由写权互斥保护）；③ 映射命中、host 身份无附件、路由无
    在途会话（全部终态/无附件）：以 host 身份建立会话（session_key =
    H({provider: host, identity:{host_id, session_id}})，host_id 按安装记录
    platforms 清单校验）并**接管路由**（建立前对同锚点既有其他 owner 先
    `replace_owner` 组更新——否则 sid 锚点撞 L1 单主 StoreError）；这是
    P0-1 的目标场景；④ 无映射：现行路径不变。
  - **并存与迁移**：既有 wf 身份会话（hook 部署前建立）在途 ⇒ 按②续用，
    映射出现不改写其绑定（MECH §1.4"更换 provider/host 不重命名或
    不改写旧绑定"）；其对象终态后下一次映射命中走③接管。
  - **identity facts 修正（拆两字段，不覆盖 source）**：`_identity_facts` 增
    `host_identity_present`（显式信封**或**映射命中即 true——"宿主是否提供
    会话标识"的客观事实）与 `session_provider`（**实际解析到的会话身份的
    provider**——②续用时是 wf，不得报 host）；`source` 保持实际来源语义；
    "本会话身份只能由进程锚派生、无法区分 /clear"警告只在
    host_identity_present=false 时出现；②续用时 facts 如实报"宿主标识已
    变化 + 按边界既有在途会话续用"。
  - **②③边界输入定义**：②适用条件 = 路由命中会话有附件、**绑定文件存在且
    可读、实例标识匹配**（与 `sync_attachment_instance` 既有写回语义同源：
    instance_expected ∈ {None, "", binding.instance_id} 即匹配——**None/空时
    以 binding.instance_id 回填附件**（既有唯一写回实现），否则
    `auto_session` 会把 None 原样作会话 instance_id、写入口因 carried 缺失
    拒绝；附件已有不同值 ⇒ sync 不覆盖 ⇒ `state=unresolved` 人裁档）、且
    绑定对象未终态（task 非 archived、run 非 terminal；**paused/suspended
    都算在途**——"在途"口径定死写进 MECH，facts 输出 task status /
    run terminal / binding id 证据字段；②态轮换出口 = 完成/暂停/放弃对象后
    重试 `enable --new-session`，不给 bind 之类不成立指引；`_auto_resolve`
    返回单一结构 {state, key, attachment, evidence, host_identity_present}，
    三处消费不重判——单实现纪律）；
    **绑定文件缺失 ⇒ 不算在途 ⇒ 走③**（"有附件、无绑定文件"是启用未绑定的
    正常状态，该会话没有要保护的对象——按人裁档处理会把 hook 上线后最常见的
    首次流程卡死）；**绑定文件存在但不可读 / 实例标识与附件不符**才是需人
    裁决档——解析结构返回 `state=unresolved` + evidence，**只在写/推进入口
    阻断；status/gate/help 等只读面降级为 facts 里可见的不可读事实继续
    运行**（`_auto_resolve` 是所有命令的必经解析路径，直接抛错会让 status
    自己打不出来——违反 MECH §1.4"只读诊断与独立维护仍可运行"既有承诺；
    出口：按 §5.4/repair 修复后重试、或人核实对象终态后走 W3-1 轮换）。
    ③接管启用未绑定的会话时，enable facts 点明
    "旧会话路由已让出，后续要重新 enable"，不静默丢弃。
  - **MECH §1.4 取用次序改写登记（人裁改写）**：四态②把次序实际改为
    「**边界在途会话续用 → 宿主会话标识（映射/信封）→ 进程锚派生**」——
    这是对 2026-11-09 人裁"宿主会话标识优先、进程锚回落"的**显式改写**
    （理由：在途会话的身份不因宿主标识出现/变化被夺走，/clear 后按在途
    会话续用直至对象终态），不是"补一句"能覆盖的；§1.4 该句同批改写并
    记改写理由，避免同节自相矛盾。
  - hook 脚本（**新资产类 host-hook，登记链八处**：DSGN §7.1 资产边界、
    MECH §10.1/§10.2（清单 schema + 落点表）、`wf_release_common.target_of`
    映射（payload/hooks/* → .codex/hooks/，未映射即 ReleaseError）、
    install.py `ASSET_CLASSES` + `plan_writes`/`self_check` 的类分发（非
    project_wf 不再一律发 skill 根；**self_check 增平台集入参**——取安装记录
    platforms，per-asset 平台条件可判）、**add_platforms 同批增 host_hook
    分发**（现只分发 skill_root，追加平台时投放 hook 文件 + hooks.json
    条目）、uninstall.py 三处类分支、dev-manifest）；
    **清单 assets[] 增 per-asset 平台条件**（host-hook 只投放声明平台；dsh
    项目不出现 .codex/hooks/——进 rules_digest，MECH §10.2 schema 登记；
    可选附加键**不递增 schema 版本**——决策登记进 MECH §10.2）；
    落点 `.codex/hooks/wf-session-identity.py`；hook **先定位项目根并核
    `.wf/`**（根取脚本自身落点上两级，部署落点确定；无 `.wf/` ⇒ exit 0
    不写任何文件），再从载荷取 session_id、从自身 /proc 祖先链解析执行边界
    锚点（复用 wflib.session 单一实现），写
    `.wf/.runtime/host-session-map/<anchor-key>.json`；
  - **失败可见**：hook import wflib 失败 ⇒ exit 0 但写
    `.wf/.runtime/host-session-map/import-error` 时间戳标记（不留静默黑洞），
    `status` facts 投影映射状态（hit/absent/import-error）；
  - `.codex/hooks.json` **合并登记**：已存在时保序追加本条目（所有权按
    命令串引用本脚本文件名判定；只增删自己的条目，不动用户其他条目）；
    不存在时创建；同名脚本冲突报人裁决；uninstall 对称移除（只删自己的
    条目与文件）；
  - 部署表 `session_identity` 声明获得真实消费者；**DSH 维持显式信封通道**
    （env 只有适配层可读、入口不读环境变量——d1 既有实跑覆盖，不为本轮
    新增机制；指引记实现稿）；zcode/pi 维持 unknown（不猜），由 W3-1 覆盖。
  - **不变量改写登记**：MECH §1.4"身份只在请求信封"口径补句——宿主映射文件
    是适配层持久化的宿主标识通道（读它的入口逻辑等价于读信封的宿主会话
    标识，不得用作其他身份来源）；session.py 模块头注释同批。
- 落点、写者、消费点、失败出口登记进机制稿 §1.4 与 §10.1/§10.2；实现稿登记
  适配层细节；dev-manifest 增资产。

### W4 P0-2 upgrade --apply 与回传闭环（既有声明边界交付）

- **W4-1 `wf upgrade --apply`**：按设计稿 §7.2/§10.3/§10.4 既有契约实现——
  - **调用形态对齐既有必填参数**：`install.py --upgrade --target <项目>
    --release-ref refs/tags/wf-vX.Y.Z --source <发行检出根> [--apply]`
    ——**--source 写死为发行检出根**（其下直接有 install.py、wf-release.json
    与 wf-release/ 子树；`load_manifest` 要求 wf-release.json 直在 source 下，
    写成 `<检出>/wf-release` 会直接 WF_PATH_INVALID）；--target/
    --release-ref/--source 三必填不变，发行身份核验复用既有实现不改
    argparse 面（`--token-parity-check` 例外分支在 argparse 之前处理，
    见下）；`wf upgrade`（wf.py 引导层）同型转交，`--release <检出根>` +
    `--release-ref` 缺一即报三要素；
  - 三方逐路径匹配（O=安装记录/L=本地/N=新发行）；**偏离记录落
    installation.json 的 assets 条目**（既有 schema："旧模板 O 的哈希与可重取
    来源 + 接受偏离决定"）——**写入侧同批补齐**（MECH §10.2 声明的
    O 哈希/可重取来源/接受偏离决定字段在 installation.json 从未落盘：
    首次安装与 `add_platforms` 的 assets 写入同批扩展，否则升级的"偏离保持"
    行无从判定）；字段名按机制稿 §10.4 既有登记
    `{local_fingerprint, upstream_version, upstream_fingerprint, decision}`，
    不另立 deviations.json、不改字段名；
  - **预览与应用**：预览含 MECH §10.3 全字段（operation/target_root/
    release_identity/selected_paths/before_states/intended_after/
    writer_observation/wip_observation/risks/backup_ref）；**预览→令牌→应用
    在同一交互入口进程完成**（PreviewToken 短指纹模式**逐字复制 repair.py
    的 PreviewToken 类**并纳入 `--verify-token-parity` 比对集——比对路径集
    由 payload/bin/{repair,uninstall}.py 扩为含 payload/install.py，且
    install.py 的 `--token-parity-check` 分支必须在 argparse 三必填之前
    处理，否则 parity 调用先被必填校验拒掉）；重跑预览即销毁、
    进程退出不恢复；
  - **升级前置**（DSGN §7.2:530；**机器判据写死**——install.py 内纯读取
    函数、不导入运行时，判据字段集登记 MECH §10.4 升级前置段）：
    `.wf/tasks/*/task.json` 每条非 archived 记录须 `status=="not_started"` 或
    **`paused==true 且 suspended==false`**（paused/suspended 独立字段，rework
    置 suspended 不清 paused——只判 paused 会放行"挂起未暂停"）；
    **收工保留 WIP 判据读任务记录的 `handoff.wip`**（writer.json 的
    handover **没有** wip 字段——按 writer.json 判恒通过，恰漏掉该前置要防的
    唯一情形；`wip_paths` 是唯一语义实现：wip 存在且 `resolved` 为空即未
    处置 ⇒ 阻断并列出路径）；
    `.wf/workflow-runs/*.json` 每条 terminal=null 记录须 paused=true；
    记录不可读 ⇒ 阻断（含路径与原因）；分支来源复用
    branch_source_findings、writer 观察复用 _writer_problem（要求 idle）；
    **出口固定三步**：`task-pause` → `writer release` → 重跑 upgrade 预览
    （task-pause 只置 paused 不释放写权；writer release 自身在保留 WIP 未
    处置时被 WF_WORKSPACE_UNRESOLVED 拦——先处置 WIP（提交/反向修正/承接）
    再释放，同出口说清）——预览前完成，不符即阻并给出口；
  - 维护写者（§4.4 互斥 + maintenance_results 登记精确路径与前后指纹）、
    应用后安装自检（§10.4 全量）、无提交授权时 applied_pending_commit
    报告后释放；
  - `wf.py` 引导层转交后，cli.py 的 `COMMANDS["upgrade"]` **保留注册**
    （help/flag 注册表断言 48/48 不动），桩体改为"转交引导层：
    .wf/bin/wf.py upgrade --release <检出> --release-ref <ref>"的明确报错；
    COMMAND_FLAGS 条目注明为 help 一致性保留（upgrade 不经本层用法校验）。
- **W4-2 回传闭环（新增设计，搭载偏离记录）**：`install.py --upgrade
  --export-deviations --out <dir>` 只读导出——对每个接受偏离的资产生成
  O→L 偏离补丁（O 字节按安装记录登记的**可重取来源**取回——
  `_committed_bytes(source_commit)` 自发行检出；取不回时如实产出
  摘要+说明，不伪造空补丁）+ 偏离清单到人给定输出目录；dogfood 修复回源 =
  人/agent 在源仓库按补丁立项（归属与取舍仍是人判，机制只做可审计导出）。
  wf-continue 的 vendor_dirty 段补回源动作句；设计稿 §7.2 登记该只读出口。
- **W4-3 版本与文档**：发行版本升 0.1.5（版本唯一源 = README + builder
  `--version`，dev-manifest 维持占位符不动）；wf/README 的"无升级路径"声明
  改为 upgrade 通道说明（0.1.4→0.1.5 可用 upgrade 升级）。

## Constraints

- **判据句分工**：能由明确输入稳定计算的进机制（W1 全部、W2-1/2/3/5/6、
  W3-2 映射、W4-1）；需要理解语境的保持指引（W2-4、W2-9 复述收敛、回传取舍）；
  改变目标/承诺/授权边界的交人（K6 各类确认、单 reviewer 残余风险、偏离裁决）。
- **不新增 skill/层级**：所有判断指引落进既有 skill 判据位；hook 与 upgrade
  模块是机制资产（非 skill），登记进安装清单。
- **登记链四件套**：新增资产/字段同批完成 dev-manifest 登记、机制稿登记、
  断言、发行树重建（0.1.5，单独 chore 提交）。
- **设计修订闸门**：上位稿修订走 validate-wf-design.py 绿 + 索引反扫；
  稿内矛盾按闸门三档处置记录。
- **提交收尾只在用户同意后执行**（用户 2026-11-22 指示）。
- 修复不回退既有承诺：两位异种 reviewer 默认要求、K6 各类确认、锚点失效
  语义、单实现纪律（同一判定只有一处实现）均不放宽。

## Acceptance Criteria

- [ ] W1-a1：先 record `.gitignore` 再 record `requirements-*.txt`，随后新增
      `requirements-prod.txt` ⇒ `covers` 判未覆盖（须重新 record）——组合场景
      断言入库，回退注入变红。
- [ ] W1-a2：按 wf-continue 路由句操作 `task-approve --decision`（choice=机械修订）
      真实可通；`task-replan --decision`（choice=机械修订）被拒且错误给出正确
      出口；`task-approve --draft` 含机械修订骨架且占位写明"仅已有批准后使用"、
      `task-replan --draft` 不再含。
- [ ] W1-a3：真实 Check 记录（含日志）→ `review-context` 物化后
      `materials/check-logs/` 非空且 tests.json 带 logs 清单；端到端断言入库
      （落 scripts/tests/wf_runtime/）。
- [ ] W1-a4：路径替换成目录/不可读 ⇒ `covers` 判未覆盖（不再按"已删除"放行）；
      真实删除仍按删除例外覆盖——三态断言入库；记录侧（record_authorization）
      同批统一走 `file_digest_state`（同一判定一处实现）。
- [ ] W2-1：`authorize record` choice=commit 被拒并列出真实四类；归档提交授权
      仍走 finish commit_grants（既有断言不回退）；机制稿/设计稿 K6 通道声明
      与实现一致（validate-wf-design 绿）。
- [ ] W2-2：键白名单十→十一键；vendor 路径内容变化 ⇒ 重算锚点 ≠ 旧
      check_anchor（旧 pass 失效）；新增键使既有 Check **一次性全量失效**
      （断言：用例自带**冻结的旧十键列表**对同一 parts 重算旧口径，与
      新十一键结果断言不等——不是同函数自比较）；分类失败归因：classify 的
      `WF_RECORD_INVALID` 原样传播（不改写），非契约异常 ⇒
      `WF_SCOPE_UNRESOLVED`（不折成 missing_anchor_inputs/
      WF_APPROVAL_MISSING 误归因）；只读面（judgments show 等）带 classified
      参数复用/自算的口径断言。
- [ ] W2-3：单 reviewer 无接受记录仍拒；有人签接受记录可产出 verdict 且
      facts/review-status 可见降级与接受引用；双 reviewer 路径断言不回退。
- [ ] W2-4/5/6/7/9：逐项对照文案/记录点/投影修正后的实际行为与投影断言；
      judgments kind 域含中文类"框架改动"（经 `--file` 条目落库、真实 CLI
      形态可通）、prefs/judgments 帮助枚举同步。
- [ ] W3-1：旧对象终态后 `wf enable --new-session` ⇒ 同边界内 `task-new`
      成功绑定新对象；旧对象在途时轮换被拒并给出口——断言入库。
- [ ] W3-2：hook 以载荷 session_id 写映射后按**四态次序**解析——映射命中且
      host 有附件 ⇒ 续用；映射命中但锚点路由有**在途会话**（绑定文件存在且
      可读、实例标识匹配、对象未终态——paused/suspended 算在途）⇒ 续用该
      会话、不接管不改写（facts 报宿主标识变化 + 证据字段 task status/
      run terminal/binding id + 出口）；**启用未绑定（有附件、无绑定文件）
      ⇒ 不算在途 ⇒ 走③**（task-new 不被卡进人裁档）；绑定不可读/实例不符
      ⇒ 需人裁决档；映射命中且路由无在途会话 ⇒ 以 host 身份建立并接管
      路由（`replace_owner`，不撞 L1 单主 StoreError；接管启用未绑定会话时
      facts 点明"旧会话路由已让出，需重新 enable"）；无映射 ⇒ 现行路径
      ——四态+边界断言入库；/clear 新 session_id 覆盖映射（建立不报错）；
      映射缺失回落锚点路由；`_identity_facts` 拆 host_identity_present/
      session_provider（②续用时 session_provider=wf 不误报 host）；
      import 失败写 import-error 标记且 status facts 可见、**成功写映射后
      标记消失且映射命中（恢复断言）**；**instance_expected=None 回填**
      （binding.instance_id 写回附件后写操作可通；已有不同值 ⇒ unresolved）
      ——断言入库
      （真实 Codex 宿主核验按 d1 同型手动记录，不进 run_all 分母）；
      hooks.json 合并/只删自己条目断言；**host-hook 资产链**断言：
      `--platform codex` 投放 `.codex/hooks/`、`--platform dsh` 不投放
      （per-asset 平台条件）、**dsh 装完后 add_platforms 追加 codex 能拿到
      hook**、uninstall 对称移除。
- [ ] W4-1：按 §7.2 场景表逐行断言（L=N、L=O、偏离保持、冲突交人、删除分支、
      新增碰撞、分支来源核对）；预览含 §10.3 全字段；令牌按 PreviewToken
      同一实现（`--verify-token-parity` 路径集含 payload/install.py、
      `--token-parity-check` 在 argparse 之前分支）且重跑预览即销毁；
      升级前置（**机器判据**：task.json {status, paused, suspended,
      handoff.wip} / workflow-runs {terminal, paused} 固定字段，不可读即
      阻断；**挂起未暂停、handoff.wip 未 resolved 均阻断**——含这两条的
      负例断言）不符即阻；无提交授权
      applied_pending_commit；应用后自检覆盖 §10.4 项；三必填参数缺一即报、
      `--source` 指发行检出根（写错子路径即 WF_PATH_INVALID 断言）；
      **installation.json assets 写入侧**含 O 哈希/可重取来源/偏离决定字段
      （首次安装与 add_platforms 同批写，偏离保持行可判定）。
- [ ] W4-2：偏离导出产物含 O→L 补丁（O 字节按可重取来源取回）与清单；
      O 不可取回时如实产出说明不伪造空补丁；无偏离时导出为空并如实报告；
      **导出写面负例**：--out 已存在且非空 ⇒ 拒并列冲突、目标含符号链接 ⇒
      拒、部分写入失败 ⇒ 停止+非零+如实报告已写清单（不自动删已写内容）。
- [ ] 分层验证：T0 全绿；T1 定向套件（authorize/review/identity 标签）绿；
      T2 `run_all --full --repro green` + `build-wf-release --verify
      --verify-token-parity` + `validate-wf-design.py` + `check-doc-refs.py` +
      `validate-skills.sh` 全绿；发行树 0.1.5 重建后与源树核对一致。
- [ ] backlog-dogfood-round2.md「下一任务待办」逐项标注处置（含维持项理由），
      不留未标注条目。

## Out of Scope（本轮不做，防范围漂移）

- traffic_monitor 目标项目的实际升级操作（0.1.4→0.1.5 真实 dogfood 升级）：
  本轮交付能力并自测；真实升级作为下一轮 dogfood 输入（如用户届时要求可另批）。
- repo_rules 确认粒度放宽（W2-8 维持现状）。
- 其他宿主（zcode/pi）的会话标识来源核实——维持部署表 unknown。
- 同轮报告条件重导入（11-21 已裁决不做）。
