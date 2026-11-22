# design.md — wf dogfood 三轮修正（第 2 版，吸收外部审查 6+9 项）

> 路径缩写：`LIB` = `docs/workflows/wf/payload/lib/wflib`，
> `SK` = `docs/workflows/wf/skills`，`BIN` = `docs/workflows/wf/payload/bin`，
> `MECH` = `docs/workflows/wf-framework-mechanism.md`，
> `DSGN` = `docs/workflows/wf-framework-design.md`，
> `IMPL` = `docs/workflows/wf-framework-implementation.md`。
> 引用行号为 2026-11-22 HEAD 核验值；第 2 版修订处标（审 N）。

## 0. 分工判据（本设计的总纲）

按 DSGN §1.1 判据句逐项定档（用户裁决的核心约束）：

| 项 | 档 | 依据 |
|---|---|---|
| W1 全部、W2-1/2/3/5/6、W3-2 映射与轮换、W4-1 全部 | **机制** | 可由明确输入稳定计算（合并/字段对齐/三态归因/通道判定/三方匹配） |
| W2-4、W2-7 指引面、W2-9、W4-2 的回传取舍 | **指引（就地）** | 需理解语境；写入用得上它的既有 skill 判据位 |
| K6 各类确认、单 reviewer 残余风险、偏离裁决、回传取舍 | **交人** | 改变承诺/授权边界、需人承担残余风险 |

**禁止形态**：不新增 skill、不新增"层"；指引只落既有 skill 判据位；hook 与
upgrade 是机制资产（安装清单登记），不是 skill。

## 1. W1 a 组 4 项 P0

### W1-a1 content_bound_patterns 合并

- 位置：`LIB/authorize.py` `record_authorization` 合并段（:226-269）。
- 修法：与 `content_digests` 同型——`merged` 段并入
  `content_bound_patterns` 列表并集去重（`_as_list_value` 归一，两侧 legacy
  无键时从新记录起档，与 digests 兼容口径一致）。
- 不变量：`covers()` 的缺摘要三档（authorize.py:402-414）不改——修复只让
  "追加确认的绑定模式"不再丢，语义（命中绑定模式 ⇒ 须重新 record）已有定义。

### W1-a2 机械修订路由收口

- 事实链：`cmd_task_replan` 正式执行只认 `choice=replan`
  （tasks.py:2315 + decisions.py:28 域）；机械修订真实处理在
  `cmd_task_approve`（tasks.py:1670-1673 → `_mechanical_revision`
  :1987-2068，等价链 + 不改阶段 + 不重复人批）；`_mechanical_revision`
  在**无既有批准时抛 WF_APPROVAL_MISSING**（tasks.py:1994-1995）（审 6）。
  草稿与指引双指错：tasks.py:2294-2296、SK/wf-continue:28。
- 修法：
  1. `cmd_task_approve --draft`：批准骨架外补一条 choice=机械修订 骨架；
     **该条占位文案必须写明前置**——"仅本任务已有批准、只改排版/转义时保留
     本条，否则删除"（否则 plan 阶段照抄骨架必被 WF_APPROVAL_MISSING 拒——
     复刻 a-2 要消灭的"指引指向不成立动作"）（审 6）；
  2. `cmd_task_replan --draft`：删除机械修订骨架；
  3. SK/wf-continue:28 路由句改指 `task-approve --task <id> --decision <文件>`；
  4. decisions.py:26 注释、tasks.py 机械修订注释的入口指向同步。
- **人签决定口径（审视结论，记入 MECH §2.2 登记与 SK/wf-continue 路由句）**：
  机械修订保留人签 choice=机械修订 决定。理由：等价链可机械核机读块，但 PRD
  散文"只改排版/转义"无法由明确输入稳定计算——人签是对散文等价性的**签认**；
  "不重复问人"由"不重复批准"承载（等价链后锚点与回执期次保持），不指零留痕。
  该签认是 Decision 六字段最轻形态，无附加结构。
- 回退防护：`cmd_task_replan` 对 choice=机械修订 的拒绝错误补 next_/exits
  指向 `task-approve`。

### W1-a3 验证日志物化接通

- 位置：`LIB/review.py` `write_materials`（:2704）。
- 修法：`check.started` → `check.started_at`（与 check.py:983-984 的日志目录
  命名同源；Check 记录字段 `started_at`，check.py:1069/:558/:581 一致）。
- 断言（端到端）：跑一次真实 Check（含至少一条验证命令落 check-logs/）→
  `review.context` 取材料 → 断言 `round-N/materials/check-logs/` 非空、
  `tests.json["logs"]` 清单含该文件与摘要。断言落
  **`scripts/tests/wf_runtime/`**（材料面既有用例族所在目录）（审·小错 3）。

### W1-a4 covers 三态归因（双侧统一）

- 位置：`LIB/authorize.py` `covers()`（:396-403 内联 try/except OSError）。
- 修法：改用 `records.file_digest_state`（records.py:74-90，C1 契约唯一归因）：
  - `missing` → 删除例外判定（"确认时存在、当前已删 ⇒ 覆盖"）；
  - `unreadable` → `uncovered`（无法核对即未覆盖，七轮 b-2 既有承诺）；
  - 正常读到 → 摘要比对（既有逻辑）。
- **记录侧同批统一（审·小错 2）**：`record_authorization` 内容留档段
  （:196-203）的内联 `except OSError → None` 同改 `file_digest_state`
  （missing/unreadable 均 → `digests[rel]=None`＝未绑内容——记录侧本就
  不区分两态，统一归因实现后行为不变，但不再第二处解释 OSError）。
- 测试向量（不依赖 root）：路径替换为目录（IsADirectoryError →
  unreadable）⇒ uncovered；真实删除 ⇒ 覆盖（既有断言）；正常内容变化 ⇒
  uncovered（既有断言）。

## 2. W2 b 组收口

### W2-1 K6 commit 通道统一（裁决②）

- 事实：`authorize_mod.ACTIONS` 含 `commit` 但守卫只消费
  expand/repo_rules/delete/export 四类——`authorization-commit.json` 零消费方；
  真实提交授权 = finish 决定 `commit_grants`（tasks.py:1023-1041 唯一口径）。
- 修法（单一事实源）：
  1. `ACTIONS` 删 `commit`（→ 四类）；`authorize record` choice=commit →
     拒绝并列四类（cli.py:2713-2717 既有分支覆盖）；`authorize show`
     自动跟随 ACTIONS。
  2. authorize.py 模块 docstring、cli.py:2660-2664 docstring：守卫清单改为
     真实四类（顺带修 `vendor` 笔误），写明"提交授权唯一通道 = finish 决定
     commit_grants"。
  3. MECH K6 登记段（:788 起）：五类**不变**；第①类（提交/推送）确认通道
     改记为 finish 决定 commit_grants；authorize record 覆盖②③④⑤。
  4. DSGN §6.5「K6 不可逆确认通道」句（:507-508）同步。
  5. 测试：test_authorization.py ACTIONS 遍历改四类；新增 choice=commit
     拒绝断言；既有 commit_grants 归档断言不回退。
- 历史文件不迁移（`require()` 按 ACTIONS 投影自然不再展示；升级说明注明
  可手工清理，机制不删用户文件）。

### W2-2 control_plane_digest 进 Check 锚点（裁决③；审 2 重设计）

- 事实：`fingerprint.check_anchor`（fingerprint.py:64-79）是**十键白名单**
  （键名与顺序取 MECH §3.2，C 排序后逐键进哈希）；`anchor_parts` 加键不进
  白名单 = 不进哈希；`current_anchor`（check.py:154-159）把取不到值的键折成
  `missing_anchor_inputs` → `WF_APPROVAL_MISSING`（可选键例外清单现仅
  entry_snapshot_digest/workflow_snapshot_digest 两键）。
- **决策（审 2 二选一）**：**常开第 11 键 + 一次性全量失效**，不引入"条件键"
  新语义（条件性并入哈希是新增机制概念，新增问题面）。理由：条件键要在
  fingerprint 键序、current_anchor 可选键、MECH §3.2 三处引入"条件并入"语义；
  常开键零新语义；一次性失效是锚点扩展的诚实代价（重跑 Check 是既有
  WF_CHECK_STALE 出口的正确动作；现实影响面：traffic_monitor 全部任务已
  归档，真实影响≈0）。
- 修法：
  1. `fingerprint.check_anchor` keys 增 `control_plane_digest`（十→十一键，
     键序登记 MECH §3.2 同批）；
  2. `anchor_parts` 增该键与可选 `classified=None` 参数（与
     `delivery_set(receipts=None, classified=None)` 同型）：Check 流程传入
     已算分类；只读调用面（judgments show / archive --draft /
     stop --preview 经 judgments.py:129-170 触发的锚点计算）缺省自算——
     性能与降级口径同批登记（审 8-2：只读面每次多一轮分类扫描的成本
     如实登记，不静默省略）；
  3. 键值 = `records.H("wf-control-plane-v1",
     {path: {digest, cause, reason} for path in sorted(v桶)})`，v 桶取
     `scope.classify_candidates(...)["buckets"]["v"]`（与 vendor_dirty
     facts 同源唯一实现）；逐路径 `file_digest_state`，cause/reason 原样入
     摘要（读取归因是锚点事实，不折 None）；v 桶空 ⇒ 常量摘要；
  4. **分类失败归因不改写既有错误码（审 8-1）**：
     `classify_candidates` 对入口快照问题本就抛 `WF_RECORD_INVALID`
     （scope.py:617-623 明文"不在本函数里另写一套回退口径"）——
     `CheckError` 原样传播；仅**非 CheckError 异常**包装为
     `CheckError("WF_SCOPE_UNRESOLVED", {"reason": "control-plane
     classification failed", ...})`（不折 None——否则 current_anchor 折成
     missing_anchor_inputs → WF_APPROVAL_MISSING 误归因）；
  5. 键值恒非 None ⇒ 不进 current_anchor 可选键例外清单，无缺项路径。
- 登记：MECH §3.2（键集合十一键 + 新增输入 + **一次性失效声明**：新增锚点
  输入使既有 Check 一次性失效，升级后需重跑 Check）、§3.5（check.parts
  与 check_anchor 覆盖面句 + anchor.parts 字段行）、DSGN §3.2 Check 内容
  指纹句补指针。
- 断言：vendor 内容变化 ⇒ 重算锚点 ≠ 旧 check_anchor；**一次性失效断言**：
  用例**自带冻结的旧十键列表**（旧口径锚点计算的逐字快照——改完后
  `check_anchor` 只有一份键表，同函数自比较恒真，审3-7），按旧十键对同一
  parts 重算并与新十一键结果断言不等；v 桶空 ⇒ 常量；分类失败 ⇒
  CheckError 原样传播（WF_RECORD_INVALID）/ 非 CheckError ⇒
  WF_SCOPE_UNRESOLVED（非 WF_APPROVAL_MISSING）。

### W2-3 单 reviewer 降级留痕（裁决④）

- 位置：`LIB/review.py` 单 reviewer 分支（:4279-4292）。
- 修法：
  1. `review-decide --single-reviewer-acceptance <文件>`：人签决定
     （quote/by/at/source + `residual_risk` 声明），gap-acceptance 同型校验
     后落 `task.reviews.single_reviewer_acceptance`（按轮绑定，判定后
     不可替换——main_reviews 幂等同型）；**记录作者归属是声明边界**（审6-b6）：
     普通文件记录无法可靠辨别人写/模型代笔（DSGN §1.5 既有边界，与全部
     决定文件同口径——批准/finish/K6 同样不宣称防伪）；接受记录沿用乙口径
     来源声明（source/by/quote），不新增防伪声明；
  2. 判定分支：单 reviewer **有**当轮接受记录 → 允许产出 verdict，facts 带
     `degraded: "single-provider"` + acceptance 引用（digest + quote 摘要）；
     无 → 维持拒绝（exits 增"人接受残余风险：先 record
     single-reviewer-acceptance 再判定"）；
  3. `review-status` 投影：`single_reviewer_accepted` + 降级事实；
  4. 双 reviewer 零改动（断言不回退）。
- 登记：MECH §9.2（决定文件族 + 接受记录字段 + 与 unavailable 互斥：接受
  只降级"人数"，不豁免主会话复核/未关闭 blocking）、DSGN §6.5（"两个…
  审查 CLI"句补"或单 reviewer + 人签残余风险接受（留痕降级，不默认）"）、
  SK/wf-review 适用面句。
- CLI help（review-decide）补 flag 与 example_file；help 注册表双向断言覆盖。

### W2-4 审查序列补外发确认步（指引）

- `SK/wf-continue`「复杂任务审查」（:100-103）开头补：发起前先取人外发范围
  确认——`authorize record` 一条 choice=export（task+materials+quote/by/
  source），否则 review-launch 报 `WF_COMMIT_NOT_AUTHORIZED`。
- `SK/wf-review-action`（:87 附近）与 `SK/wf-finish`（步骤 1 审查结论项）各
  补判断句 + 指针（论述不跨文件复制）。
- 机制不改（review.py:2379-2390 门禁与 authorize.py:118-126 出口已存在）。

### W2-5 review-notes 帮助路径（机械）

- cli.py:2342 帮助：改"放当前任务目录内（用 `wf.py status` 回显的
  `directory`，形如 `<id>-<slug>`；放错目录会被当成外来改动）"。

### W2-6 archived 绑定 next 文案（机械）

- tasks.py:1250：绑定对象已终态时改用 enable 终态出口同口径文案（随 W3-1
  补"或 `wf enable --new-session` 换新会话标识"）。按 bound 对象状态分档
  组 next_（机械判定：status==archived or terminal）。

### W2-7 vendor_dirty 确认留痕（指引 + 记录点；审·小错 1 + 审2-7 修正）

- kind 域唯一定义在 **MECH §9.4**（judgment 记录字段行）：既有八中文类
  （归属/关闭/沿用/扩面/标准变更/缺口/未核实/规模）。
- 修法：judgments `KINDS` 增中文类 **`框架改动`**（与既有类命名形态一致，
  非英文 "vendor"；MECH §9.4 kind 列表同批登记）；`cli.py` 判断偏好
  （prefs --kind）与 judgments 帮助枚举同批同步（help/域表一致性断言覆盖）；
  **不参与判定、纯事实投影**（域登记注明）。
- **落点定死一种形态（审3-6，不留实施时再判）**：`judgments add` 只接受
  `--task/--file/--attestation`（cli.py COMMAND_FLAGS），无 `--kind` 旗标——
  kind 在**判断文件条目**里：`{kind: "框架改动", decision: <归属去向：
  回源仓库立项/另开任务/保持现场>, basis: <依据>, outcome: "applied",
  by: "human"}`，**不引入 quote、不用 --attestation**（decision 是判断内容
  字段，框架不判决其内容——judgments.py 模块头 §5.4 分工；outcome/basis/
  by 按 `validate` 既有校验面即可，无需新校验）。人在场的归属确认由
  `by: "human"` 承载留痕。
- SK/wf-continue「vendor_dirty」段（:62-65）补收敛动作句（按上述真实
  CLI 形态写指引，不造不存在的旗标）。
- 消费点：task-check/archive 的 facts 投影 `vendor_judgments`（与
  vendor_dirty 并列，仍不阻断）。

### W2-8 repo_rules 粒度维持（留档理由）

- 不改机制。理由：K6 ⑤ 确认对象是"环境级规则变更对后续任务的影响"，逐次
  内容变化逐次确认正是该类承诺本体；dogfood 摩擦实例（手工改 .gitignore 后
  被拦）是门禁正确工作。任务级合并引入"确认后内容再变仍放行"窗口，与内容
  绑定不变量直接冲突。
- SK/wf-continue:23 指引不动。

### W2-9 §1.1 三处收口 + 复述收敛

- DSGN §1.1「本地完整路径」行（:37）补环境边界说明（复杂任务审查需两个
  异种审查 CLI，或单 reviewer + 人接受残余风险，见 §6.5）。
- 「固定流转程序化」清单"三方升级匹配"随 W4-1 落地。
- 工作习惯收敛：**唯一完整定义位 = SK/wf-continue「工作习惯」**，内容合并
  三处中信息最全的版本——含 wf-finish 版独有的"显式 inputs.generation 可
  覆盖"一句（审·小错 9：先确认 wf-start 步骤 5 已有，仍以合并进完整定义位
  为准，不丢信息）；SK/wf-start:85-89、SK/wf-finish:54-60 各留判断句 +
  指针；显式模式启用事实记录（wf-start:37-42）是步骤指引，保留在 wf-start。
- SK/wf-review-action 覆盖/关闭后果复述收敛为判断句 + 指针。
- 索引反扫：DSGN/MECH 改动逐条过 `validate-wf-design.py` + 手工反扫。

## 3. W3 会话身份（P0-1）

### W3-1 `wf enable --new-session`（宿主无关轮换）

- 命令形态：`enable --new-session`（enable 子命令面加 flag）。
- 语义（MECH §1.4 登记）：
  1. 前置：当前执行边界已有会话身份（路由命中）；其绑定对象已终态
     （task archived / run terminal）**或**绑定为空。对象在途 ⇒
     `WF_BINDING_MISMATCH` + 出口（先 finish/abandon/release，或新开终端）。
  2. 动作：签发新 `issued_id`，登记当前边界锚点路由指向新 session_key，
     旧 session 在 anchors.json 的 owners 以 `identity_store.replace_owner
     (old, new)` 组更新（既有"轮换=组更新"实现）；旧 attachment 与绑定
     文件保留为历史（"结束不解除绑定"）。
  3. 幂等与并发：同边界重复轮换 = 再签发（人显式动作）；锚点无路由 ⇒ 走
     普通 enable（等价首次启用）。
  4. writer 语义：轮换不触碰写权；对象终态但写权未释放 ⇒ 拒绝轮换并给
     release 出口（防把在途写权带进新会话）。
- 自动解析衔接：replace_owner 保证唯一 owner ⇒ 走既有 L1 单主/L2 命中
  路径，adjudicate 不改。
- 文档：SK/wf-start:18-19"尚未交付"句改真实指引；cli.py enable help 补
  flag + example；MECH §1.4 登记（写者/消费点/失败出口）。
- 断言：终态后轮换 → 同边界 `task-new` 成功；在途对象轮换被拒 + 出口；
  轮换后旧 attachment/绑定文件仍在。

### W3-2 Codex SessionStart 适配层（审 3/4 重设计）

#### 3.2.1 建立语义（审 3/审2-3/审3-1——四态解析次序，在途会话续用优先）

- **四态解析次序**（`_auto_resolve` / `auto_session` / `cmd_enable` 三处一致）：
  - ① **映射命中 + host 身份有附件**：按既有解析续用该 host 会话（不变）。
  - ② **映射命中 + host 身份无附件 + 锚点路由上有在途会话**（路由命中的
    会话有附件、且其绑定对象未终态：task 未 archived / run 未 terminal）：
    **续用该既有会话，不改写、不接管**（审3-1：hook 上线/换聊天不能把
    在途会话的身份夺走——否则在途任务只能靠 bind --task/显式信封接续，
    正是 P0-1 要消除的摩擦）。这与宿主不可区分时的现行语义一致（同边界
    = 同执行会话），并发仍由写权互斥保护。facts 报告"宿主会话标识已变化，
    当前边界按既有在途会话续用"+ 出口（继续当前对象；或按受控路径完成/
    暂停/放弃对象后 `enable --new-session` 换新会话）。
  - ③ **映射命中 + host 身份无附件 + 路由无在途会话**（全部终态/无附件）：
    **建立 host 身份会话并接管路由**——`cmd_enable` 的建立条件从
    `if key is None`（cli.py:1027-1030）扩为"key 为 None **或** 映射命中
    且路由无在途会话"；`_establish_auto_session` 扩展分支以 host 身份建立
    （session_key = H({provider:"host", identity:{host_id, session_id}})，
    session.py:35-40 既有校验，host_id 按安装记录 platforms 清单核），
    附件/activation/绑定全落 host session_key；建立时对同锚点键的既有其他
    owner 先 `identity_store.replace_owner(old, new)` 组更新（审2-4：否则
    sid 锚点撞 register 的 L1 单主 StoreError）；旧绑定文件保留为历史
    不改写。这是 P0-1 的目标场景：旧对象终态后，同边界新聊天正常开新任务。
  - ④ **无映射**：现行路径不变（锚点路由 → wf 身份；无路由 → 签发）。
- **并存与迁移**：既有 wf 身份会话（hook 部署前建立）在途 ⇒ 按②续用，映射
  出现不改写其绑定（MECH §1.4"更换 provider/host 不重命名或改写旧绑定"）；
  其对象终态后 ⇒ 下一次映射命中走③接管（换身份开新对象）。在途对象由
  写权互斥保护（新会话 enable 撞已持写权 ⇒ 既有阻断），不靠身份劫持。
- **解析结果单一结构（审6-2：单实现纪律）**：`_auto_resolve` 的返回从
  `(session_key, attachment)` 扩为**一处实现**的结构
  `{state, key, attachment, evidence, host_identity_present}`——`state` 取
  host_resume(①)/inflight_reuse(②)/host_establish(③)/无映射(④)；
  `evidence` 含②的 task status / run terminal / binding id / 旧会话 key 与
  ③的"旧会话路由已让出"事实；`host_identity_present` 供 `_identity_facts`
  消费。`auto_session`/`cmd_enable`/`_identity_facts` **只消费该结构**，
  不在各处重判四态（同一判定只有一处实现）；ctx 缓存该结构（一次解析、
  多处消费——与既有 `_auto_key/_auto_attachment` 缓存同型）。
- **实例标识匹配口径（审6-4 + 审8 修正）**：②的"实例标识匹配"比对
  attachment.instance_expected ↔ binding.instance_id，**与
  `sync_attachment_instance` 既有写回语义同源**（current ∈ (None, "", id)
  即接受）：**历史会话 instance_expected 为 None/空 ⇒ 以
  binding.instance_id 回填附件**（`sync_attachment_instance` 既有唯一写回
  实现——否则 `auto_session` 会把 None 原样作会话 instance_id（cli.py:229），
  写入口 `_require_instance_match` 随即因 carried 缺失拒绝（cli.py:1526））；
  回填后 `session.instance_id = binding.instance_id`，写入口验收补
  "回填后写操作可通"断言；附件已有**不同**值 ⇒ `sync_attachment_instance`
  不覆盖 ⇒ `state=unresolved` 人裁档。**②态的轮换出口显式写**：②态下
  `enable --new-session` 会被 W3-1 前置（对象终态）拒——出口是
  完成/暂停/放弃对象后重试轮换（或继续当前对象），不给出 bind 之类
  不成立指引。
- **identity facts 修正（审2-5 + 审4-4：拆两字段，不覆盖 source）**：
  `_identity_facts` 增 `host_identity_present`（显式信封**或**映射命中即
  true——宿主是否提供了会话标识的客观事实）与 `session_provider`（实际
  解析到的会话身份的 provider——②续用时是 wf，**不得报 host**）；
  `source` 保持实际来源语义；"本会话身份只能由进程锚派生、无法区分
  /clear"警告只在 host_identity_present=false 时出现；②续用时 facts 如实
  报告"宿主标识已变化 + 按边界既有在途会话续用"。
- **②③边界输入定义（审4-5 + 审5 修正）**：
  - **②"在途"口径定死（写进 MECH §1.4）**：路由命中会话有附件、**绑定
    文件存在且可读、实例标识匹配**、且绑定对象未终态（task 非 archived、
    run 非 terminal；**paused/suspended 都算在途**）；②续用的 enable/status
    facts 输出证据字段（task status / run terminal / binding id）+ 出口
    （继续当前对象 / 完成·暂停·放弃对象后 `enable --new-session`）。
  - **绑定文件缺失 ⇒ 不算在途 ⇒ 走③**（审5："有附件、无绑定文件"是
    **启用未绑定**的正常状态——hook 上线时项目已有启用未绑定的 wf 会话，
    下一次 SessionStart 写映射后若按人裁档处理，任何命令（含 task-new）
    都被卡进需人裁决，最常见的首次流程直接卡死）；③接管该会话时 enable
    facts 点明"旧会话路由已让出，后续要重新 enable"，不静默丢弃。
  - **绑定文件存在但不可读 / 实例标识与附件不符** ⇒ 解析结构返回
    **`state=unresolved` + evidence（binding_unreadable / instance_mismatch）**，
    **只在写/推进入口阻断**；`status`/`gate`/`help` 等只读面降级为 facts 里的
    不可读事实继续运行（审7-1：`_auto_resolve` 是所有命令会话解析的必经路径
    （ctx.session → auto_session → _auto_resolve），把人裁档直接抛错会让
    status 自己打不出来——违反 MECH §1.4「只读诊断与独立维护仍可运行」
    既有承诺）；写入口的阻断出口：按 §5.4/repair 修复后重试、或人核实对象
    终态后走 W3-1 轮换（与 enable 对 binding_terminal_unknown 现行口径一致）。
- **DSGN §1.3 已知限制句补登（审5 落地条件②）**：在途期内 /clear 仍不可
  区分（声明边界、非回归，覆盖到对象终态为止——终态后新映射命中即换 host
  身份），与 MECH §1.4 三阶次序句互指；登记进 §5 文档总表。
- **MECH §1.4 取用次序改写登记（审4-3 + 审8 同意：人裁改写，非补句）**：
  四态②把次序实际改为「**边界在途会话续用 → 宿主会话标识（映射/信封）→
  进程锚派生**」——这是对 2026-11-09 人裁"宿主会话标识优先、进程锚回落"的
  **显式改写**（理由：在途会话的身份不因宿主标识出现/变化被夺走，/clear
  后按在途会话续用直至对象终态，之后新映射命中即换新 host 身份）；§1.4
  该句**整体改写并保留限定语**——「第 1 档（在途续用）仅在存在未终态
  在途对象时生效，其余情况宿主会话标识优先」（审8：不写限定语会被读成
  "进程锚优先"，与既有裁决整体相反），并记改写理由，避免同节自相矛盾。
  **明示接受的残余**（审8）：在途期 /clear 仍不可区分（P0-1 收益延后到
  空闲边界）；"宿主会话标识优先"由绝对优先降为**有条件优先**（只在无
  在途对象时）——两残余与 DSGN §1.3 已知限制句互指，记入 design §8 与
  MECH §1.4 改写段。该改写已随本设计报用户确认（B 档）。
- **降级链**：映射文件丢失（.wf/.runtime 清理）→ 回落锚点路由 → 仍可解析
  （③建立时登记了 host session_key 路由）；路由也丢 → 显式信封/
  `bind --task` 既有恢复出口（与现行 wf 身份运行态丢失同边界，非回归）。

#### 3.2.2 hook 资产与资产边界（审 4 + 审2-2：登记链完整）

- 新资产类 **host-hook**，登记链**八处同批**（审2-2/审3-2：只写一处其余会直接
  报错或静默跳过——`wf_release_common.target_of` 对 payload/hooks/* 抛
  `ReleaseError: unmapped source path`；`plan_writes`/`self_check` 把非
  project_wf 资产一律发每个 skill 根；`add_platforms` 只分发 skill_root——
  "dsh 装完再追加 codex"时 host_hook 会被静默跳过；uninstall 三处独立类分支）：
  1. `wf_release_common.py` `target_of`：`payload/hooks/<name>` →
     （"host_hook", `.codex/hooks/<name>`, "hook", False）映射行；
  2. install.py `ASSET_CLASSES` 增 `"host_hook"`；`plan_writes` 与
     `self_check` 的类分发：host_hook 按**声明平台**的 hook 落点投放/核对
     （不再走 skill 根分支）；**`self_check` 增平台集入参**（审3-3：现签名
     `(target, manifest, skill_roots)` 无平台集——dsh 项目会把缺失的
     `.codex/hooks/` 误报 digest mismatch 或漏核；入参取安装记录 platforms）；
  3. **`add_platforms` 同批增 host_hook 分发**（install.py:761-764 只处理
     skill_root，追加平台时投放 hook 文件 + 登记 hooks.json 条目）（审3-2）；
  4. uninstall.py 三处类分支（297-307、411-414、528-531 一带）对称增
     host_hook 处置（只删自己文件与 hooks.json 自己条目）；
  5. **清单 schema 增 per-asset 平台条件**（MECH §10.2 assets[] 增可选
     `platform` 键，仅 host_hook 类合法、须属 --platform 声明集；进
     rules_digest）——否则 `--platform dsh` 项目也会被投放
     `.codex/hooks/`（资产模型现无"只投放给 codex"的表达）。**"仅
     host_hook 类合法"的校验落点三处**（审4-6：schema 声明之外，
     `verify_assets`/`self_check`/`plan_writes` 都拒非法组合——platform
     键出现在非 host_hook 资产、或 host_hook 资产缺/错 platform 即拒）。
     **schema 版本不递增**（可选附加键；**兼容声明只覆盖 platform 键对已知
     类的旧读取方不破坏**——新资产类 host_hook 本身需要新安装器处理，旧安装器
     的 `plan_writes` 对未知类报 unknown target_class（install.py:1270-1276
     既有行为）；**安装器与清单同属一个发行单元**（§7.2 发行身份），安装/
     升级都用发行检出自带的安装器，不存在"旧安装器读新清单"的正常路径；
     旧安装的发行集一致性自检读自己的 installation 记录（无 host_hook），
     不受影响；审6-b2 的兼容口径按此收窄登记进 MECH §10.2）；
  6. DSGN §7.1 资产边界句 + MECH §10.1 落点表 + §10.2 schema；
  7. dev-manifest 资产条目（platform=codex）；
  8. 落点 `.codex/hooks/wf-session-identity.py`（进用户 Git，与 skill 根
     同类——已投放资产、提交属用户仓库）。
- hook 职责（单文件标准库；import wflib 见下）：
  1. **定位项目根并核 `.wf/`**（审3-5）：项目根取 hook 脚本自身落点
     （`<project>/.codex/hooks/` 的上两级——部署落点确定，不依赖载荷 cwd）；
     根下无 `.wf/` ⇒ exit 0（非 wf 项目，不写任何文件）；
  2. 读 stdin 载荷取 `session_id`（大小写键兼容，与 .codex 既有 hook 同型）；
  3. `sys.path` 注入 `<project>/.wf/lib` → `from wflib import session` →
     以自身 /proc 祖先链调 `session.candidates()` 取锚点键（**单一实现**）；
  4. 对每个锚点键写 `.wf/.runtime/host-session-map/<key>.json`
     （{provider:"host", host_id:"codex", session_id, mapped_at, boot}）；
  5. `/clear` ⇒ SessionStart 再触发，新 session_id 覆盖同键映射；**成功写映射
     时同批删除 `import-error` 标记**（审7-b3：恢复即自愈——新映射本身就是
     恢复证据；`status` facts 报告 import-error 仅当标记仍存在）。
- **失败可见（审·小错 6）**：import wflib 失败 ⇒ exit 0 **但**写
  `.wf/.runtime/host-session-map/import-error`（时间戳 + 异常摘要，last-wins）
  ——不留静默黑洞；`status` facts 投影 `host_mapping` 状态
  （hit/absent/import-error），映射缺失不再不可见；**恢复路径有断言**
  （失败→标记→成功→标记消失且映射命中）。
- **hooks.json 合并（审 4-②）**：install.py 对 codex 平台——无 hooks.json
  ⇒ 创建（仅本条目）；已有 ⇒ 保序解析、追加本条目（幂等：命令串引用本
  脚本文件名即视为已登记）、按 dict 插入序原样 dump；**所有权按命令串引用
  本脚本文件名判定**（无标记段机制可借，命令串含唯一脚本路径是确定性归属）；
  同名脚本已被用户占用 ⇒ 报人裁决（§7.1 同名未知文件口径）。uninstall
  对称：只删命令串引用本脚本的条目与本文件，空列表/空 hooks 保留文件结构
  （用户文件不删）。
- **不变量改写登记（审 3-②）**：MECH §1.4 补句——宿主映射文件
  （`.wf/.runtime/host-session-map/`）是适配层持久化的宿主标识通道：入口
  读它的逻辑等价于读信封的宿主会话标识，仅作宿主身份来源，不得用作其他
  身份通道；session.py 模块头注释同批。入口**不读环境变量、不读命令行
  覆写身份**的禁令不变（映射文件不是环境变量/命令行）。
- **DSH 维持显式信封（审·小错 7）**：env 只有适配层（模型/脚本）能读、
  入口不读环境变量——DSH 不新增 hook/映射机制；指引记 IMPL（d1 既有实跑
  覆盖显式信封路径）。
- zcode/pi 维持 unknown；由 W3-1 覆盖。
- **gitignore 不动**（审·小错 5）：`.wf/.runtime/` 已在托管段整目录忽略，
  不加行（避免无谓 rules_digest 变更）。
- 断言：hook 样本载荷（含 session_id）临时项目实跑 → 映射落位 → `enable`
  建立 host 会话（四态次序断言）→ 后续命令解析为该会话；路由接管
  （replace_owner，/clear 场景建立不报 StoreError）；既有 wf 会话有附件
  时不被映射改写（并存断言）；映射删除 → 回落路由；import 失败 →
  import-error 标记 + status facts 可见 + identity facts 报 host 源；
  hooks.json 合并/幂等/冲突/只删自己；**资产链**：`--platform codex`
  投放 `.codex/hooks/`、`--platform dsh` 不投放、uninstall 对称
  （test_asset_boundaries.py 同族）。真实 Codex 宿主核验按 d1 同型手动
  记录（full README 登记，不进 run_all 分母）。

## 4. W4 upgrade --apply 与回传闭环（P0-2；审 5 重设计）

### 4.1 实现形态

- `install.py` 增 `--upgrade` 模式；**调用形态对齐既有必填参数**（审 5-1）：
  `python3 <发行检出根>/install.py --upgrade --target <项目> --release-ref
  refs/tags/wf-vX.Y.Z --source <发行检出根> [--apply]`——**--source 写死为
  发行检出根**（其下直接有 install.py、wf-release.json 与 wf-release/ 子树；
  `load_manifest`（install.py:184-189）要求 wf-release.json 直在 source 下，
  写成 `<检出>/wf-release` 会直接 WF_PATH_INVALID）（审2-1）；三必填不变，
  发行身份核验 `resolve_tag/verify_assets` 复用零复制；同版已装 ⇒ 拒
  （同版非升级）。**`--token-parity-check` 在 argparse 之前分支**（见 4.2）。
- `wf upgrade` 入口：`BIN/wf.py` 引导层在 repair/uninstall 转交位
  （:521-532）同型增 `upgrade`——`--release <检出根>` 与 `--release-ref`
  由引导层透传，execve `<检出根>/install.py --upgrade --target
  <WF_PROJECT_ROOT> --release-ref <ref> --source <检出根> [--apply]`；
  缺参由 install.py 报三要素（引导层只转交不判定）。
- **cli.py 注册表不动（审 1）**：`COMMANDS["upgrade"]` 保留（48/48 与双向
  断言不动）；桩体 `_unavailable(3, ...)` 改为明确报错——"upgrade 经引导层
  转交：终端直接 `python3 .wf/bin/wf.py upgrade --release <检出根>
  --release-ref <ref>` 或 `python3 <检出根>/install.py --upgrade ...`"；
  `COMMAND_FLAGS["upgrade"]` 更新为真实 flag 集，**条目注释注明为 help
  一致性保留**（upgrade 不经本层用法校验——引导层先转交）。
- 运行时无关性：升级路径不经 wflib（与 repair/uninstall 同理：坏运行时
  也要能升级）；writer 协调用 install.py 既有 Lock/_writer_problem 面。

### 4.2 三方升级核心（严格按 DSGN §7.2/MECH §10.2/§10.4 既有契约）

- 输入身份：O = 目标 `.wf/install/installation.json` 的 assets；L = 目标当前
  字节；N = 新发行清单。**写入侧同批补齐（审2-6）**：MECH §10.2:860 声明的
  assets 字段（"旧模板 O 的哈希与可重取来源、必要本地模板副本、所见 N、
  接受偏离/删除决定"）在 installation.json **从未落盘**（现仅
  {target, root_ref, digest, source_path}，install.py:1090-1093 与
  add_platforms:857-861）——首次安装与 add_platforms 的 assets 写入同批扩展
  （O 哈希 = digest 既有；补 upstream_version=安装版本、可重取来源引用安装
  记录的 release_ref/source_commit），偏离决定字段 `{local_fingerprint,
  upstream_version, upstream_fingerprint, decision}`（MECH §10.4:875 既有
  登记名）由 upgrade 写入——不另立 deviations.json、不改契约字段名；
  否则"偏离保持"行无从判定。
- 逐路径动作 = MECH §10.4:875 顺序表逐行（本地缺失曾安装 → 分支来源核对
  复用 `branch_source_findings` → 新增无占用 → 新增撞用户文件 → L=N →
  L=O 且上游变化 → 同一已接受偏离（两边指纹均同）免重复询问 → 其他冲突
  预览人选保留/恢复/合并）。上游删除：L==O 且无用户新增 ⇒ 可删候选；
  偏离或目录含未知 ⇒ 人裁决。目录先深后浅；符号链接越界拒绝（既有
  boundary/inside 工具）。
- **预览与令牌（审 5-2，对齐 MECH §10.3 既实现）**：
  - 预览含 §10.3 全字段：`{operation, target_root, release_identity,
    selected_paths, before_states, intended_after, writer_observation,
    wip_observation, risks, backup_ref}`；
  - **预览 → 令牌 → 应用在同一交互入口进程完成**：`--apply` 为无参形态时
    交互 TTY 确认（`sys.stdin.isatty()`），`PreviewToken` 类**逐字复制
    repair.py 的 `PreviewToken` 类实现**（短指纹模式：指纹 = 预览摘要前 8 位
    十六进制；符号定位，不按行号——审2-9）并纳入
    `build-wf-release.py --verify-token-parity` 比对集——**比对路径集由
    `payload/bin/{repair,uninstall}.py` 扩为含 `payload/install.py`**
    （build-wf-release.py:217-222 一带），且 install.py 的
    `--token-parity-check` 分支**必须在 argparse 三必填解析之前处理**
    （否则 parity 调用先被必填校验拒掉）（审2-6 连带）；重跑预览即销毁；
    进程退出不恢复；非 TTY ⇒ 拒并给出口；
  - **MECH §10.3 令牌句与既实现偏差同批收口**（C 档收紧到稿子）：现文
    "终端生成随机 128 位 nonce"与 repair.py 已实现的短指纹（E1/E2 有意
    设计，类 docstring 记录）不一致——本次改 MECH §10.3 该句为既实现的
    短指纹口径（预览摘要前 8 位十六进制、绑定预览摘要与本次过程、重跑
    即销毁），消除文实分叉。
- **升级前置（审 5-3 + 审3-4 + 审4-1/4-2：机器判据写死）**（DSGN §7.2:530
  既有契约，install.py 现无任务面读取——判据不写死则验收无法断言）：
  - **活动任务**：读 `.wf/tasks/*/task.json`（活跃目录，归档目录不读）——
    每条 `status != "archived"` 的记录必须满足 `status == "not_started"` 或
    **`paused == true 且 suspended == false`**（审4-2：paused/suspended 是
    独立字段、rework 置 suspended 不清 paused——只判 paused 会放行
    "挂起未暂停"）；记录不可读/缺 status ⇒ 阻断（reason=unreadable-record，
    含路径）；无活跃任务目录 ⇒ 通过；
  - **实例**：读 `.wf/workflow-runs/*.json`——`terminal == null` 的每条
    必须 `paused == true`；不可读 ⇒ 阻断同上；
  - **收工保留 WIP**（审4-1：读**任务记录的 `handoff.wip`**，不是
    writer.json——writer.py 的 handover 只有 {from, receiver_session_key,
    object_or_preparation, decision, invalidated_generation}，**没有 wip
    字段**，按 writer.json 判恒通过、恰漏掉该前置要防的唯一情形）：对每条
    活跃任务记录，`handoff.wip` 存在且 `resolved` 为空 ⇒ 未处置 ⇒ 阻断
    （列出 WIP 路径与出口：按 §4.4 处置后重跑）；`wip_paths` 的语义口径
    （wip 存在且未 resolved 即未处置）为机制稿 §3.5 既有登记，升级前置
    只读 {handoff.wip.resolved, handoff.wip.paths} 两个固定字段、不复制
    归因逻辑；
  - **分支来源**：复用 `branch_source_findings`；**writer 观察**：复用
    `_writer_problem`（要求 `state == "idle"`——审7-2：**前置是两步**，
    `task-pause` 只置 paused **不释放写权**（tasks.py:2409-2417），释放后
    才 idle（`ensure_releasable` 允许 paused 释放，tasks.py:4956 起）；
    **出口固定写成三步：`task-pause` → `writer release` → 重跑 upgrade
    预览**；且 `writer release` 自身在保留 WIP 未处置时被
    `WF_WORKSPACE_UNRESOLVED` 拦（`ensure_releasable` 既有判定：先处置
    保留 WIP（提交/反向修正/承接）再释放）——这条也在同一出口里说清，
    不让用户走完 pause 又撞下一道门）；
  - 判定实现为 install.py 内**纯读取函数**（只读上述固定字段，不导入
    运行时、不解析 PRD/spec/任务正文）；判据字段集登记进 MECH §10.4
    （升级前置段：task.json {status, paused, suspended, handoff.wip.resolved,
    handoff.wip.paths}、workflow-runs {terminal, paused}、writer
    {state}、**两步处置出口**）。
  - 不符即阻并给出口（处置路径写进预览 facts）。
- 维护写者与持久化：取得 maintenance 持有（maintenance_results：operation=
  H("wf-maintenance-op-v1", C({operation:"upgrade:<version>", generation}))、
  preview_digest、head_before、changes=精确路径+前后指纹）；无提交授权 ⇒
  result=applied_pending_commit、报告待持久化路径并释放。
- 应用后自检：复用 `self_check` 全量（发行集一致性、required steps 可达、
  gitignore 托管段、运行态忽略实际生效、坏配置恢复可达）；失败保留现场
  （§5.4 恢复语义）。
- **不做**：patch/merge 引擎（冲突行出口 = 预览差异 + 人选保留/恢复/合并，
  人合并后重跑按表重判）；跨大版本 schema 迁移（§7.2 既定：旧 schema 按
  §5.3 解释保留原文）。

### 4.3 回传闭环：`--export-deviations`

- `install.py --upgrade --export-deviations --out <dir>`（只读，不需令牌/
  写者）：对每个接受偏离资产生成 `<dir>/deviations/<n>-<basename>.patch`
  ——**O 字节按安装记录登记的可重取来源取回**（MECH §10.2:860 既有字段；
  `_committed_bytes(source_commit)` 自发行检出，检出须含该提交）+
  `<dir>/manifest.json`（路径、upstream_version、local_fingerprint、
  decision、导出时间）；O 不可取回 ⇒ 如实产出摘要+说明行，不伪造空补丁
  （审 5-5）。
- **导出写面规则（审6-b3）**：`--out` 目录**不存在则创建、已存在则必须为
  空目录**（非空 ⇒ 拒绝并列冲突内容——不覆盖、不并入用户文件）；逐文件
  原子写（install.py 既有 `write_bytes` 复用）；目标路径含符号链接 ⇒
  拒绝（既有 boundary/inside 工具）；**部分写入失败 ⇒ 停止、非零退出、
  如实报告已写清单与失败原因**——导出是可重跑的只读派生物，失败不自动
  删除已写内容（人决定处置），验收补这些负例（已存在非空/符号链接/
  部分失败）。
- 消费：人/agent 在源仓库按补丁立项（归属与取舍人判——W2-7 的
  judgments kind=框架改动 记录"回源仓库立项"去向，与本出口闭环）。
- 登记：DSGN §7.2 偏离管理段补只读导出句；SK/wf-continue vendor_dirty 段
  补回源动作句；README 补 upgrade 通道说明。

### 4.4 版本与发行

- 版本升 0.1.5：**版本唯一源 = wf/README（+英文对应段）与 builder
  `--version`**；dev-manifest 维持占位符不动（builder :88-93 显式豁免，
  审·小错 4）；发行树重建 `build-wf-release.py --version 0.1.5`（单独
  chore 提交）。
- 升级自举验证：0.1.4 安装的夹具项目 ← 0.1.5 发行跑 `--upgrade --apply`
  （夹具内不真提交）：三方主路径（L=O 更新、新增资产投放、偏离保持）+
  `--export-deviations` 断言；candidate-clean 评估，不足则 dev-only 登记。

## 5. 文档/登记改动总表（设计修订闸门）

| 文件 | 改动 | 闸门 |
|---|---|---|
| DSGN §1.1 | 本地完整路径补环境前置句 | validate 绿 + 反扫 |
| **DSGN §1.3** | 已知限制句补"在途期内 /clear 仍不可区分（声明边界、非回归，覆盖到对象终态为止）"，与 MECH §1.4 互指（审5 落地条件②） | validate 绿 + 反扫 |
| DSGN §6.5 | K6 通道句（②③④⑤ authorize record / ① finish）；单 reviewer 降级句 | 同上 |
| **DSGN §7.1** | 资产边界增 host-hook 类（审 4 补） | 同上 |
| DSGN §7.2 | 偏离导出只读出口句；升级前置指针已存在（核对） | 同上 |
| MECH K6 段 | 五类通道登记改写（①=finish commit_grants） | 同上 |
| MECH §3.2/§3.5 | 键集合十→十一键 + 一次性失效声明 + parts 字段 | 同上 |
| MECH §1.4 | host-session-map（落点/写者/消费点/失败出口 + 不变量补句 + 建立语义 + 四态/②③边界与"在途"口径 + **取用次序三阶改写·人裁改写及理由**）+ enable --new-session 登记 | 同上 |
| MECH §9.2 | single_reviewer_acceptance 记录 | 同上 |
| **MECH §9.4** | judgments kind 域增"框架改动"（审·小错 1 修正落点） | 同上 |
| MECH §10.1/§10.2 | host-hook 资产类/落点；installation.json assets 偏离字段核对；token parity 集 | 同上 |
| MECH §10.3 | 令牌句对齐既实现（短指纹口径，消文实分叉） | 同上 |
| **MECH §10.4** | 升级前置段判据字段集（task.json {status, paused, suspended, handoff.wip.resolved, handoff.wip.paths}、workflow-runs {terminal, paused}）——与 4.2 正文逐条对上（审6-3） | 同上 |
| IMPL | 部署表 session_identity 消费、upgrade 转交形态、DSH 显式信封指引 | 文档核对 |
| SK/wf-continue | 机械修订路由、审查外发确认步、vendor 判断句+记录、工作习惯唯一完整定义位 | validate-skills |
| SK/wf-start | 换新会话标识真实指引、工作习惯收敛 | 同上 |
| SK/wf-finish / wf-review-action | 工作习惯/复述收敛、外发确认指针 | 同上 |
| SK/wf-review | 单 reviewer 适用面句 | 同上 |
| wf/README(+en 对应段) | 0.1.5、upgrade 通道、Codex hook 前置说明 | 双语同批 |
| backlog-dogfood-round2.md | 「下一任务待办」逐项处置标注 | 收尾项 |

## 6. 测试计划（分层）

- **新增/改动单测**（scripts/tests/wf_review、**wf_runtime**）：
  - authorize：a-1 组合、a-4 三态（含记录侧统一）、commit 类拒绝；
  - review：a-3 端到端（wf_runtime 材料面用例族）、单 reviewer 接受/拒绝、
    review-status 投影；
  - check：control_plane_digest 锚点（变化/常量/一次性失效/分类失败归因）；
  - identity：enable --new-session、host-session-map（建立/并存/回落/
    import-error 可见）、hooks.json 合并（test_asset_boundaries.py 同族）；
  - tasks/judgments：kind=框架改动（**经 --file 条目、真实 CLI 形态可通**——
    judgments add 无 --kind 旗标，审2-7）、archived next 分档、机械修订草稿
    双骨架（含占位前置文案断言）；
  - install.py upgrade：三方表逐行、三必填缺参报错、**--source 指发行检出根**
    （子路径即 WF_PATH_INVALID）、预览全字段、令牌（重跑销毁/非 TTY/
    **parity 路径集含 install.py 且 --token-parity-check 先于 argparse**）、
    升级前置、applied_pending_commit、**installation.json assets 写入侧
    字段**（首次安装/add_platforms/upgrade 三写者）、自检、export-deviations
    （O 可取回/不可取回/无偏离）；
  - W3-2 资产链：`--platform codex` 投放 `.codex/hooks/`、`--platform dsh`
    不投放（per-asset 平台条件）、target_of 映射、uninstall 对称
    （test_asset_boundaries.py 同族 + 发行面断言）。
- **回归不回退面**：既有 authorize/review/check/identity/install 套件全绿
  （run_all --full）；help 注册表 48/48 双向断言不动。
- **回退注入**：a-1/a-3/a-4、control_plane、new-session、host 建立优先级、
  upgrade L=O 行、令牌重跑销毁各一次（临时恢复旧实现变红 → 恢复 → 字节一致）。
- **T2/T3**：`run_all --full --repro green`；`build-wf-release --verify
  --verify-token-parity`；`validate-wf-design.py`；`check-doc-refs.py`；
  `validate-skills.sh`；发行树 0.1.5 重建后 diff 核对。
- **真实宿主手动项**（不进 run_all 分母，full README 登记）：Codex hook 实跑
  （真会话 SessionStart→映射→enable 建立→status 解析→/clear 覆盖）；dsh
  既有 d1 不回退。

## 7. 回滚点

- 阶段 1/2/3 各自独立成组：每阶段完成即 T0 绿（可独立回退到阶段边界）。
- 上位稿与源码同批原则：DSGN/MECH 改动与实现断言同 commit 语义分组；
  发行树重建独立 chore 提交（可单独 revert）。
- 用户同意提交前全部改动留在工作树；**回退 = 只撤销本任务产生的差异**
  （审6-b4：按 implement.md 各阶段分组文件清单，先 `git status`/`git diff`
  核对该组内无本任务之外的未提交改动混入，再对本任务差异应用反向补丁
  （`git diff -- <本任务文件> | git apply -R`）；**本任务新建的未跟踪文件**
  （审7-b1：普通 `git diff` 不含未跟踪文件——如
  `payload/hooks/codex-session-identity.py`）按各阶段"新建文件"清单逐一
  核对 `git status --porcelain` 的 untracked 集合**只含本任务新建文件**才
  删除；发现无关未提交改动混在同一文件 ⇒ 停下交人处置，不用
  `git checkout --`/`git reset --hard` 类会丢弃未提交工作的操作）。

## 8. 已知边界与本设计不做的事

- **明示接受的残余（审8，三阶改写随附）**：
  - 在途期 /clear 仍不可区分（P0-1 的"同终端换聊天"收益延后到空闲/对象
    终态边界生效；DSGN §1.3 已知限制句与 MECH §1.4 改写段互指）；
  - "宿主会话标识优先"由绝对优先降为**有条件优先**（只在无在途对象时）。
- 不改 K6 五类语义/不放宽任何既有拒绝（只改第①类通道声明）。
- 不为 zcode/pi 猜会话标识（部署表 unknown 维持）。
- DSH 不新增 hook/映射机制（显式信封通道已可用；指引记 IMPL）。
- upgrade 不做 patch 合并引擎/跨版本迁移（§7.2 既定边界）。
- 真实 dogfood 升级 traffic_monitor（0.1.4→0.1.5）属下一轮 dogfood 输入。
