# wf 会话身份重设计（评审稿 v3，2026-11-07）

> v3.32 = v3.31 + **R1–R6 交付完成**：§8c 改为实测交付状态（3 个模块/接线、2 条 repro、7 处文档落账；41 项单测 + 131 项全量全绿）；未实现项收敛为 3 个且都有明确协议与验收。
> v3.31 = v3.30 + **R0 完成（2026-11-08）**：§2.5 补 A2（zcode 两聊天 L1 可分）、ssh 结果与"R0 完成"判定；§10 待裁项 2b 关闭（R0 已回答）。支持环境清单见 `r0-results.md` §九。
> v3.30 = v3.29 + **S1 收口（拆文档）**：审查参与者身份（C6 实现清单）、`--as` 三点一致性、`review-launch` 跨文件事务三节**拆到 `review-identity-protocol.md`**，本文只留契约引用与指针；本文回归单一议题（零输入身份）。拆分理由与议题边界见终局评估 §三 C 类。
> v3.29 = v3.28 + 第二十六轮评审修正：**§3.7g ① 重写为可机械执行的替换文本**——完整原文（去省略号）、**明确"仅替换前两句"**、新文补齐三要素（边界粒度 / **显式 legacy 模式分支** / **「路由标识而非凭据」限定**），核对清单加"后两句保持不变"一项。
> v3.28 = v3.27 + 第二十五轮评审修正：**写入边界表与三点一致性表统一**（a1/b1：暂存布局两表并存，第 4 次回扫遗漏）、**`verdict` 枚举补回既有 `unavailable`**（a2：机制稿 §10 的"审查不可用"出口不能被新枚举吞掉）、**§3.7g 补设计稿 §3 正文「使用环境」句**（b2：frontmatter 与正文是同一事实的两份表述）、小项：`status` 残留、reason 登记位置、§8c 验收错引、暂存清理双因判别、矩阵 leader 行 reason 归属、15g 覆盖 S3/S4。
> v3.27 = v3.26 + **人裁 C1 = ①（执行边界粒度）**：新增 §3.7g 给出 R5 的**逐字改写文本**（§1.3 身份句、environment 行、skills 工作习惯、连带核对清单）；C1 行与待裁清单同步（OD-9）。使用约定随之明确：**一个终端同时只干一个任务**。\n> v3.26 = v3.25 + 第二十四轮评审修正：**统一"文件名承载身份"**（a1/b1：暂存用 `review-<as>.md` + `.claim-<as>.json`，三点一致性表与 §3.7a 同步，不再有"树内占位/目录身份"两套）、**删除多余 `status` 字段**（a2/b2：只用 `verdict`，无需迁移）、**start 越过重建加三条前置**（a3/a4/b3/b4：候选唯一 + 确由附件缺失引起 + binding/写权核对；多候选不越过、其它 unverified 走 `mark-root-gone`）、判据 8c 与 C2 对齐（b5）、补验收 15f–15h、`concurrent_unregistered_caller` 进 reason 表、§8c 补四项、暂存清理归因（小项）。
> v3.25 = v3.24 + 第二十三轮评审修正：**C2 阻断进入 §3.4 执行伪码**（a1/b1：原规则写在 `adjudicate()` 里，而该场景走 #1 不进裁决；伪码还会 upsert 未登记调用者 ⇒ 阻断永不生效）、**reviewer 写入移出项目树**（a2：运行态也在项目内）、**start 的附件重建入口**（a3：缺附件时先 BLOCK 会自锁）、**审查失效改为可执行状态并被 final_gate 消费**（a4）、**「已登记」定义可机械核对**（b1c）、删无产生机制的 `single_root_multi_chat`、判据 4/8 同步、矩阵 l1-drift 补 P2、`mark-root-gone` 排除附件缺失、materials 不提交、**C1 升为待裁**。
> v3.24 = v3.23 + **人裁 C2 = C（分级）**：可检测的未登记第二调用者 ⇒ 阻断 `concurrent_unregistered_caller`（人调 `start` 登记后放行）；不可检测的（同 root 多聊天）⇒ 合并披露。落账：§3.7 C2、§2.3d 分级规则表、§5 矩阵、§9 判据 7/7a'、§6 强度④、`open-decisions.md` OD-8。
> v3.23 = v3.22 + 第二十二轮评审修正：**reviewer 全程不写项目树**（a1/b9：材料由 launch 物化；占位/报告落运行态；归档由 import 复制）、**实施 CLI 变更同批失效既有 pass**（a2）、**轮换前置加「无其它 alive/unverified 根」**（a3）、**一致性只核未完成 action**（a4）、**S0/S1 收敛**（a5）、7c 补 P2 限定（b1）、**§3.4 守卫收窄为 `!known ∧ 无存活兄弟根`**（b2）、**bind 链补 action 意图**（b3）、**reason 归因修正**（b4）、**P2 排除 l1 维度**（b5）、**新增 §3.7f 待裁与回扫补充**（b6）、R0 必测不可达出口（b7）、`{sid}` 断言收紧（b8）、`mark-root-gone` 幂等重跑（b10）、`state()` 补附件缺失行（b11）。
> v3.22 = v3.21 + 第二十一轮评审修正：**新增 §8c 交付状态表**（a1/a2：明确本文零实现、C6 是待办）、**§3.7e 补 action schema 映射**（a3：幂等键含 impl_cli、前像/后像、generation 拒绝旧重入）、**修幂等与补录的矛盾**（b1：按"意图值 vs 落盘值"判定，补录才可达）、**sid 根补 `root_state` 列**（b2）与**"同 sid 即同根"措辞修正**（b3：改按三元组）、**`review-context` 写入授权与占位改运行态**（b4）、小项 a/b/c。
> v3.21 = v3.20 + 第二十轮评审修正：**§3.7a 清单补报告文件名/import token/`--as` 校验/help** 并新增 **§3.7d `--as` 三点一致性**（b1：context/文件名/import 不一致即阻断）、**§3.7e `review-launch` 跨文件事务**（a3：复用 action 意图与四种重入）、附件 schema 补 **`declared_implementation_cli`**（a2：含兼容缺省/写者/轮换）、**`state()` 补 sid 型根两行**（b4：sid_start 不符 ⇒ gone）、预填值过期说明（b2）、**新装 vs 升级分行**（b3）。
> v3.20 = v3.19 + 第十九轮评审修正：**`mark-root-gone` 参数含 `boot`**（a1：否则跨重启删错根）并给出**跨文件事务与四种中断重入**（a3）、**新增 §3.7a C6 实现修改点清单**（a2：`review.py:281/:140/:601`、CLI 参数、launch schema、import 署名、help）、**§3.4b 补 `attached_l1` 的 unverified 行**（b1：#1/#2/#3 不调 `adjudicate`，故无效果）、**引写权链**（b2：`reviews.*` 属判定字段，仍走 `writer.json` 代次）、**`declared_implementation_cli` 的写者/预填/轮换**（b3）、I1 补 P2 引用、`status --issued` 空结果语义、表格闭合、矩阵列语义（小项 a/b/c）。
> v3.19 = v3.18 + 第二轮第十八批评审修正：**`unverified` 在伪码里也变成 `USE` 守卫**（b1：伪码与正文此前两处互斥）、**`repair --mark-root-gone` 定稿为"删除条目 + 留痕"**（a1/b2：不留状态字段，`state()` 无需新增行；参数面收窄为 pid 型）、**实施 CLI 声明时点改到 `review-launch`** 并给补录出口（a2/b6）、**`review-context` 单列为 reviewer 入口**（a3：不要求 activation、不参与 roots、不解析路由身份，与 `cli.py:1677` 一致）、删 §3.4 不可达子句（b3）、**重建 §8b 不变量表**（b4）、安装器不假装能判宿主（b5）、业务行去 `task-start` 重复、矩阵补"无关旧根 unverified 只披露"行（小项 b）。
> v3.18 = v3.17 + 第十八轮评审修正：**恢复审查参与者身份**（v3.17 称「没消费点」是错的：`review.py:281/:601` 读 host_id；改为 `--as` 显式声明 + launch 记录，缺失即拒绝出 pass，并进契约清单 C6，修 a1/b1）、**`state()` 补「ENOENT=gone/dead」「start 不符/zombie=dead」**（修 a2/b2：否则「leader 先死」整条链被误阻断）、**unverified 降为 USE 守卫**＋新增 `repair --mark-root-gone` 出口（修 b#18.1 毒丸）、**不变量限定适用入口**（修 a3/b7）、**适配层标记语义二分**（修 b3）、**C4 补裁决记录 OD-7 与 §8.1 同步**（修 b4）、删 macOS 幻影 ps 后端（b5）、明确 unverified 输出码（b6）、小项 a–f。
> v3.17 = v3.16 + 第十七轮评审修正：**`boot` 进入 roots 与 attached_l1**（跨 boot 撞车，修 b1）、**`state()` 输入映射**（null=gone、损坏=unverified，修 b2）、**未知分支阻断后不 upsert**（修 a1）、**P2 读法分区**（修 a2）、S1 出口改 repair（b3）、S3/S4 判据可核对化（b4）、`SHELLS_OR_UTILS` 匹配口径（b5）、**新增 §3.7 契约修订清单 C1–C5 + 适配层退场 + 轮次归属**（b6/b8/b12）、**R0 环境清单按 agent 宿主重排**（b9，含 A2 多聊天必测）、**删除 root_exe→host_id**（b10，无消费点）、**新增 §8b 组合穷举与 7 条不变量**（b11）、**旧对象只读入口**与 **§9b 使用观察项**（b13/b7）、macOS 行（b9）。\n> v3.16 = v3.15 + 第十六轮评审修正：**删除「普通调用幂等补齐」**（与 §3.5 冲突、且给伪造 binding 开通道）、**「附件有值 + binding 缺失」归 S1 而非 S0**（不清空证据，修 a1/b1）、**`other_roots()` 成为唯一根证据定义**（修 a2：v3.15 的 `USE`/`other_root_alive` 漏了排除当前 root，会拒绝合法续接）、**P2 差异写进 `adjudicate()` 函数内**（修 a3：调用处不得筛单元素、不得跳守卫）、**业务根维护三值化**（修 a4：`unverified` 不当作已死）、§2.4b 与新验收统一、路由条目加 `boot` 字段以支持 GC、存档 GC 规则、判据 7b 拆 A/B、删 `routes_shadowed`。
> v3.15 = v3.14 + 第十五轮评审修正：**`adjudicate()` 证据三值化**（`l1_state` / `root_state` 的 unverified ⇒ 阻断，不让「读不到」冒充「已消失」，修 a1）、**路径切换=路由重置**并删除 `path_at_attach`（修 a2）、**首次绑定写回与三种残态补齐**（§3.6，修 a3）、**验收 15/15b/15d 收窄为可识别范围**（修 a4）、**矩阵 leader 行拆子场景 A/B**（L2 在 ⇒ #5 续接、L2 缺 ⇒ 接管孤儿，修 b1）、清理 X 表引用（b2）、**#5 收紧明示为有意行为变化**（b3）、空 owners 走 `WF_HISTORY_UNRESOLVED`（小项 4）、#4-P2 改调 `adjudicate`（小项 5）。
> v3.14 = v3.13 + 第十四轮评审修正：**判据收敛为唯一函数 `adjudicate()`（§2.3d）**——#5 与 X 表都调用它，§2.3b 不再自带规则、矩阵与 R0-C 一律引用它；修 §3.4b/§3.4c 的 `M4` 残骸。
> v3.13 = v3.12 + 第十三轮评审修正：**`attached_l1` 不可解析 ≠ 旧边界已消失**（#5/X2 追加「该会话无其它 alive 根、无 liveness-unknown」双重条件，修 a1）、**X2 改为「接管孤儿」**（`C==U` ∧ 无 alive 根；新增 `O` 与 `alive_other` 判据，修 b1）、**`resolve()` 伪码与 §2.6 用途表改 owners**（修 b2，第三处单值残骸）、§2.3b 措辞同步「不可解析」（修 b3）、矩阵与判据 7b 去「可达」、轮换补 recovering 冲突、X5 标为 else。
> v3.12 = v3.11 + 第十二轮评审修正：**轮换改为 `replace_owner(S→N)` 组操作**（共享 L2 只换自己的 owner，B 不受影响，修 a1）、**§7 anchors schema 同步 owners**（修 b2）、**迁移并入 #5 同一判据 X1–X5**（废除 v3.3 可达性，修 b1）、**`attached_l1` 用可解析性而非存活三态**（修 b3）、**writer 的 preparation 范围不作曾绑定证据**且未绑定附件完整可直接 S0（修 a2）、`l2_owners_changed` 降噪、R0-C 更名「唯一裁决」（小项）。
> v3.11 = v3.10 + 第十一轮评审修正（**结构性重写，非补丁**）：**L1 单主 / L2 多主**的登记语义（`owners` 集合，第二终端追加不覆盖；取消 v3.10 的 #2「键冲突」——L2 多主是常态），**#5 用 owners + `attached_l1` 唯一裁决**、**S0 改为最严格一档**（无任何曾绑定痕迹才成立）、**§3.1 伪码落地 S1 人裁闸门**、路径切换的连带后果与 `orphan_sessions` 披露、清理重复注释与 schema 标注。
> v3.10 = v3.9 + 第十轮评审修正：**键资格改按 `path_at_attach`**（修 b1：P1 自己的 proc 键仍参与，#5 恢复可达、守卫不再是死代码）、**#4 补 else 与 P2 豁免**（修 b2/small）、**迁移守卫覆盖 M4**（修 a1）、**有效性以已提交路由为准**（修 a2：孤儿与轮换残留天然无效）、**轮换提交顺序写死**（路由为真相）、**S0/S1 判据重写**（修 a3：不再用 `--diff-filter=D`，证据不足保持待核实）、**判定顺序改分支表述**（修 b4）、**S0 新身份覆盖路由**（修 b3）。
> v3.9 = v3.8 + 第九轮评审修正：**`attached_l1` 守卫**（登记两键，但用「建立时 L1 是否仍可解析」判定共享 root 是否同一边界，既恢复 P1 的 #5 续接、又堵住 M4 合并，修 a1/b1）、**identity 结构与哈希输入统一**（`provider` 与 `identity:{issued_id}` 分开存，轮换/恢复同构，修 a2）、**身份不可恢复时走新会话**（修 a3）、**迁移候选集加有效性**（排除 `superseded_by` 与孤儿附件，修 a4）、**路径切换后旧键不参与判定**（修 a5）、**五态执行表与机械判据**（修 b2/b3）、**判定顺序写死**（修 b4）。
> v3.8 = v3.7 + 第八轮评审修正：**L2 不再无条件全局别名**（P1 下 L1 有决定权，修 a1）、**迁移候选集**（按当前 root 正向关联，空集不得迁移，修 a2）、**`identity` 原文入库**（首次绑定可闭合，修 a3）、**`identity-path` 授权链归维护类**（复用格式不借用会话授权，修 a4/b3）、**恢复五态**（S0–S4，修 a5）、**根两型 + unknown 单一语义**（修 a6/b2）、L2 归属检查改扫 `attachments`（修 b1）、命令清单补全（b4）、**消费码表列清**（b5）、矩阵补 M3u 行（b6）。
> v3.7 = v3.6 + 第七轮评审修正：**M 表收缩为 M3/M3u/M4/M5**（命中场景归还 §2.2b）、**新增 M3u**（旧根存在 unknown ⇒ 阻断迁移，堵住“证据不明即接管”）、决策表 #4 补 P2 前提、**`identity.path` 改值走维护类命令 + 基线提案通道**（消除直写项目配置与引导悖论）、§4.2b 去重、§3.4b 锁段去重、§3.5 ② 收窄 `WRITER_BUSY` 语义、§3.3 旧名清理。
> v3.6 = v3.5 + 第六轮评审修正：**`task-start` 归业务类**（`enable` 才是启用入口）、**锁规则统一**（附件锁/项目锁+固定顺序，删掉 §3.4 旧并发段与判据 8c 的矛盾表述）、**恢复表三支互斥重写**、**命名全面统一为 session_key**、**决策表 #7 拆 7a/7b**（候选存在未登记 ≠ 无锚）、**P2 引导例外**、**M2 拆 M2a/M2b 并定迁移优先级**、**`identity.path` 单字段 + 兼容缺省**。
> v3.5 = v3.4 + 第五轮评审修正：**生命周期伪码与新 schema 同步**(§3.1/§3.3)、**标识链** issued_id→identity→session_key(§2.6)、**迁移状态转移表**(§3.4c)、**存活三态与锁分离**(§3.4b)、**P2 默认关闭的部署事实**(§2.4d)、**命令四分类**（`repair` 归维护类）(§4.2b)、附件恢复三支互斥(§3.5)。
> v3.4 = v3.3 + 第四轮评审修正：**路由与状态分离**（`anchors.json` 单文件组原子 + 会话级 `attachments`，修多键分叉）、R0 改为**按支持路径 P1/P2/P3** 验证（修 R0 与降级自相矛盾）、失败形态**三分法**、空 roots **fail-safe**、附件恢复**三态**、命令**三分类**（`spec --file` 需 activation）、矩阵补两条不可检测通道披露。
> v3.3 = v3.2 + 第三轮评审修正：回查**决策表**(§2.2b)、roots 判定在维护前且降级**持久化**(§3.4)、L2 归属按**可达性**裁决(§2.3b)、去掉 ROOT_TTL(§3.4)、轮换前置持权检查(§3.3)、附件**显式恢复**流程(§3.5)、R0 可选条目与**经 agent 路径**要求(§2.4b)。
> v3.2 = v3.1 + **根进程由单字段改集合**（§3.4 重写，修掉「并存调用者互相覆盖」的缺陷）。
> v3.1 = v3 + **R0 升格为实现前的强制门禁**（2026-11-07 人裁）。
> **R0 未完成不得开始实现**；文档中任何"支持环境"声明都必须有 R0 证据。
> v3 = v2 + 第二轮两份评审的修正 + 我的实测复核。**被实测推翻的评审主张也记录在此（§0.3）。**
> 本文自包含；剩余争议见 §10。

---

## 0. 相对 v2 的变更

### 0.1 采纳并修正

| # | 问题（谁提的） | v3 处理 |
|---|---|---|
| 1 | **L1（sid）"一终端一身份"未经验证**，且 `sid>1 可读` ≠ "合适的执行边界"（A#1） | **新增 R0 强制门**（§2.4，2026-11-07 升格）：在 11 个环境（含 tmux / screen / VS Code 集成终端 / `docker exec -t` / `docker run` 一次性 / `systemd-run` / 嵌套 shell / nohup / CI）逐个跑锚点探针，四条判据全过才记为"支持"；**R0 未完成不得进 R1**，任一环境不过 ⇒ 列入不支持清单（fail loud + 出口），**范围收缩必须由 R0 数据支撑** |
| 2 | `last_root_pid` 没有定义"根进程"，且未定义刷新时机（A#4、B#1） | 定义 `root_ref` = **L2 解析出的 agent 祖先（pid+start）**；L2 不可用时退化记录 `{sid}`；**每次成功认证后刷新**；降级条件与并发标记见 §3.4 |
| 3 | "前者已死"堵不住**并存**（A 还活着，B 同终端启动）（B#2） | `roots[]` **集合 + TTL**（§3.4 重写）：并存 ⇒ `facts.concurrent_callers` 披露；旧根全死 ⇒ activation 降级；TTL 清空 ⇒ `activation_stale` 要求重新 start |
| 4 | §2.2 伪码 L1 命中即返回，**实现不了**"偏好与回查解耦"（B#3） | `resolve_anchor()` 改返回**候选列表** `[L1_key?, L2_key?]`；回查按 L1→L2，**两者皆 miss 才 fail loud** |
| 5 | "公共系统祖先"没有判定规则，CI 行为在两种解释间摇摆（A#2、B#4） | 定义 L2 候选的三条硬判据（§2.2）；**直接子于 pid 1 的候选视为服务进程、不接受** ⇒ CI 默认阻断（可用显式模式），不再留给实现者 |
| 6 | activation 的"变强"被高估（B#5） | 区分两面写清：跨会话冒充经输入通道**确被堵死**（真增益）；**同会话自我启用仍是纪律边界**（与伪造信封同级），不宣称防伪 |
| 7 | 轮换/建立的事务细节缺失（A#5、B#8） | §3.3 给出**提交顺序与失败语义**；轮换与启用**在同一次 start 内完成** |
| 8 | anchors 丢失后"新会话"不等于可直接拿写权（A#6） | §3.5 明确：新会话仍要过 `WF_WRITER_BUSY` / WIP / handover 三关，**不因注册表丢失而算干净会话** |
| 9 | attachments 缺失复用 `WF_BINDING_MISMATCH` 语义不准（B#7） | 新增**增量原因码** `WF_ATTACHMENT_MISSING`；`WF_BINDING_MISMATCH` 只保留"两侧不同"的原义 |
| 10 | 显式模式是完整 legacy 通道，不只是测试便利（A#7） | §4.1 写定位 + **退役条件**；仍是唯一允许 `host_id ∈ platforms` 校验的通道 |
| 11 | `root_exe → 宿主种类` 无归一规则（A#8、B#10） | MVP 采**保守**：自动模式**不产生 host_id、不做归一**；审查所需的参与者身份改由显式声明提供（§6，v3.18） |
| 12 | 矩阵缺行：leader 先死、`exec`、setsid 型 agent 重启（A#6、B#6） | §5 补齐；其中 `exec` 一条经实测**不成立**（见 0.3） |

### 0.2 新增

- **R0 验证门**（实现前必做，不通过则缩范围）；
- `root_ref` / `concurrent_callers` / `WF_ATTACHMENT_MISSING`；
- 轮换的提交顺序（attachment → 指针 swap → 失败保留旧指针）；
- 显式模式退役条件；
- ~~可选的本机宿主映射（人维护）~~：**已删除**（自动模式不产生 host_id；见 §6）。

### 0.3 被实测推翻的评审主张（质疑记录，第二轮新增）

| 主张 | 实测 | 结论 |
|---|---|---|
| B#6：「shell 原地 `exec zsh` ⇒ 同 pid、**新 starttime** ⇒ 新锚点键」 | `exec /usr/bin/python3` 前后：**pid 不变、starttime 不变**（5096225 → 5096225） | **不成立**。`execve` 不重建 task，`starttime` 是 fork 时刻常量 ⇒ L1 键在 `exec` 下稳定。该行从矩阵移除 |
| B#1：「若根 = 会话领导（shell），agent 重启时 shell 仍活 ⇒ 不触发降级，与判据 4 矛盾」 | 属实 | **采纳**：根必须定义为 L2 的 agent 祖先（见 #2） |
| A#1：「`sid>1 且 /proc 可读` 只说明有进程，不说明是合适边界」 | 属实（服务进程也有 sid） | **采纳**：加三条硬判据 + R0 验证门 |

---

## 1. 约束（不变）

①不为特定 agent 适配；②调用方尽量零输入；③写权互斥/会话区分/实例隔离/人启用不可破坏；④**Linux 必选**，其它可选；⑤不宣称防伪。

**不可消除的限制**：禁止宿主适配 + 禁止调用方携带标识 ⇒ 任意 agent 的聊天会话无法自动识别。
本方案的"会话"= **wf 执行会话**；锚点只做**路由**。

---

## 2. 锚点

### 2.1 信号事实（含实测）

| 信号 | 事实 | 用途 |
|---|---|---|
| `session`（`getsid(0)`，stat 第 6 字段） | 同终端多次调用稳定；`setsid` 每次新；新 shell 新 sid；**`exec` 不改变 leader 的 pid/starttime** | 主锚 L1 |
| `tty_nr`（stat 第 **7** 字段）+ 设备 inode | pty 编号与 **inode 都会复用**（实测 `/dev/pts/7`、`136:7`、`inode=10` 重复） | 仅审计 |
| 祖先 `(exe,pid,starttime)` | 稳定于同一 agent 进程；"最近非工具祖先"是启发式 | 次锚 L2 |

### 2.2 解析：返回**候选列表**，回查分两步

```text
candidates(anchor) -> [key_l1?, key_l2?]        # 不在这里决定命中
  boot = boot_id
  l1 = None
  sid = getsid(0)
  if sid > 1 and /proc/<sid> readable and not is_kernel_thread(sid):
        l1 = key(boot, "session", sid, starttime(sid))
  l2 = None
  for pid in ancestors(self):                   # self → … → 1
      if pid == 1 or is_kernel_thread(pid): break
      if pid in {self} ∪ interpreter_chain_pids(self): continue
      name = basename(readlink(/proc/<pid>/exe))   # 口径见 §2.2c；readlink 失败 ⇒ 该候选不成立
      if name in SHELLS_OR_UTILS: continue
      if starttime(pid) >= starttime(self): continue
      if parent_of(pid) == 1:                   # 直接子于 init ⇒ 服务进程，不接受
          break
      l2 = key(boot, "proc", name, pid, starttime(pid)); break
  return [k for k in (l1, l2) if k]

resolve(anchor):                                # 回查：候选先全算出来，再按下表判
  cands = candidates()                          # [l1?, l2?]（合格键见 §2.2c）
  l1    = 唯一 owner(cands.l1) 若该键存在且 owners 恰一个，否则 None
  l2    = set(anchors[cands.l2].owners) 若该键存在，否则 set()
  return decide(l1=l1, l2=l2, cands=cands)      # 见 §2.2b 决策表
```

### 2.2a 登记语义：L1 单主、L2 可多主（v3.11 重写，一次性修 a1/b1/a2 根因）

前几版的反复源于我把"登记"当成单一映射。**根因是 L1 与 L2 的所有权性质不同**：

| 键 | 所有权 | 说明 |
|---|---|---|
| **L1**（会话锚） | **单主** | 一个终端会话只属于一个执行会话。出现两个主即记录损坏 |
| **L2**（进程锚） | **可多主** | 同一 agent 进程可以被多个边界共享（两个终端、两 pane、执行服务） |

```json
// anchors.json 的 value（v3.11：owner 改为集合）
"<key>": {"owners": ["<session_key>", …], "attached_at": "…", "via": "session|proc"}
```

**登记（`start`）**：

- L1：`owners` 必须是空或只含本会话；否则 `WF_HISTORY_UNRESOLVED`（单主被破坏）。
- L2：**追加**本会话到 `owners`（去重），**不覆盖**已有主——两个终端共享同一 root 时 `owners=[S1,S2]`，双方都不丢路由。

**解析（`resolve`）**：

```text
hits = {key: owners(key)  ∈ 当前路径合格键见 §2.2c}
l1_hit = 唯一 owner（单主 ⇒ 至多一个）
l2_hit = owners 集合
```

### 2.2b 命中决策表（v3.11，唯一实现依据）

**参与判定的键**：`anchors.json` 中的全部键（路径切换即路由重置，见 §2.2c，故不存在「别的路径时代」的键）。

| # | L1 | L2（`owners`） | 判定 | 动作 |
|---|---|---|---|---|
| 1 | 命中 S | 空，或含 S | 同一会话 | 用 S（L2 的其它 owner 只是共享 root 的别的边界，忽略） |
| 2 | 命中 S | 非空且**不含 S** | L1 与 L2 指向不同会话 | 以 **L1 为准**，忽略 L2（L2 多主是常态，不构成冲突）；仅当该会话的 `owners` **数量发生变化**时记 `facts.l2_owners_changed`（避免常态噪声，评审 b 小项） |
| 3 | 命中 S | 不可用 | 同一会话 | 用 S |
| 4 | 可用但未命中 | owners 集合 | **当前 L1 与已登记不同** | **P1/P3：不复用**（当前 L1 可用 ⇒ 另一个边界；`start` 新建、业务命令阻断）。**P2**：调用 `adjudicate(owners, 当前 root, path)`（§2.3d），`USE` ⇒ 复用（`anchor_degraded="l1-drift"`），否则按 reason 阻断 |
| 5 | 不可用 | owners 集合 | L1 消失 | 调用 `adjudicate(owners, 当前 root, path)`（§2.3d，P1/P2 都在函数内处理）：`USE` ⇒ 续接（`l2-only`）；`BLOCK` ⇒ 按其 reason 阻断；**owners 为空数组（半写入/损坏）⇒ 不走裁决，直接 `WF_HISTORY_UNRESOLVED`** |
| 6 | 未命中/不可用 | 空 | 新边界 | 业务命令阻断；`start` ⇒ §3.4c（候选集非空才迁移，否则新建） |
| 7a | 未命中 | 不可用 | 候选集为空 | `WF_IDENTITY_UNRESOLVED`（R0 亦不支持的环境） |
| 7b | 可用但未登记 | 不可用 | 候选存在、路由未登记 | `start` 允许新建（P3 首次使用）；业务命令阻断 |

> **为什么取消 v3.10 的"#2 键冲突"**：L2 多主是**正常**状态（共享 root）。把"L1→S1、L2→{S1,S2}"判成历史损坏，
> 等于框架把合法用法变成 repair 事故。真正的冲突只剩 **L1 单主被破坏**（同一 L1 键出现两个 owner）。

### 2.2c 路径切换 = **路由重置**（v3.15，修 a2）

v3.13–v3.14 用条目级 `path_at_attach` 决定"哪些键参与"，但 L2 一句话可以有多个不同路径时代登记的 owner
（同一 root 在 P2 下登记 S、切 P1 后再登记 N）——**条目级字段无法表达 owner 级事实**：
更新条目会让旧 owner 重新获得资格，保留旧值又会让新 owner 失格。

v3.15 采取更简单且可验证的语义：**改 `identity.path` 就是一次路由重置**。

| 动作 | 结果 |
|---|---|
| `wf.py identity-path --set <P>`（维护类，见 §2.4d） | 维护事务内把**当前 `anchors.json` 整体置为失效**（重命名为 `anchors.invalidated-<ts>.json` 存档，之后从空表开始） |
| 旧会话（P2 时代建立的） | **不再可解析**：`status` 列 `facts.orphan_sessions=[…]`；其绑定、附件、历史**全部保留**（Git 不动） |
| 继续使用旧会话 | 走 §5.5 受控恢复（人确认旧写者停止 → 释放 → 新会话接续原对象） |
| 新会话 | 按新路径照常登记 |

因此**不再需要 `path_at_attach` 字段**：任何时刻 `anchors.json` 里的键都属于当前路径，全部参与解析与裁决。

**`SHELLS_OR_UTILS` 的匹配口径（v3.17，修 b#17.5）**：取 `basename(readlink(/proc/<pid>/exe))`，与常量集合**全等**匹配
（不按前缀、不比对 comm、不读配置）；常量随发行固定，名单变更属「锚点逻辑变更」⇒ 按 §2.4 必须重跑 R0。

**判据分离**（采纳 A#1/A#2）：`采集到进程信息` ≠ `确认了可接受边界`。
候选必须同时满足：存活、非 pid 1 / 非内核线程、**不是 init 的直接子进程（服务）**、starttime 早于调用者、名字不在工具表。任一不满足 ⇒ 该候选不成立。

### 2.3 键

`SHA256(C({boot, kind, sid, sid_start}))` / `SHA256(C({boot, kind, exe, pid, start}))`（**含 pid**）。

### 2.3b R0 首轮实测（2026-11-07，本机）

| 场景 | L1 | L2 | 结论 |
|---|---|---|---|
| 普通终端（同 shell 两次） | `c0ee9691…` 稳定 | `d14cb12e…`（node pid 5538） | 均可 |
| `setsid` 起新会话 | `f01a2063…`（**不同** ✓） | **同一个 `d14cb12e…`（相同 ✗）** | **L2 会把 L1 能区分的两个边界合并** |
| `systemd-run --user --scope` | 稳定 | 稳定 | 继承发起终端的 sid ⇒ 与发起终端**同一执行会话**（记为可接受行为） |
| `docker run … python3`（作为容器 pid 1） | **None** | **None** | 无锚 ⇒ 阻断（走显式模式），符合设计 |

**L2 归属：没有独立规则，一律调用 `adjudicate()`（v3.14）**

v3.3–v3.13 这里曾有两套并存的判据（"独占性阻断"→"owners + attached_l1"），
与 #5 及 miss 分支各自表述，导致同一事实在不同入口得到不同结论（评审 a#14 指出 §2.3b 与矩阵仍只写 `owners + attached_l1`，
漏掉 `alive_other` / liveness-unknown 两个条件 ⇒ 会重新允许"旧 agent 仍有其它存活根"时接管）。

**v3.14 起，全文只有一处裁决实现：§2.3d 的 `adjudicate()`。** 本处不再重复任何判据。

### 2.3d 唯一裁决函数 `adjudicate()`（v3.14 新增：全文唯一实现依据）

hit 分支（决策表 #5：L1 消失、L2 命中）与 miss 分支（候选全 miss 后的迁移）
**调用同一个函数**，只是结果解释不同（续接 vs 接管孤儿）。任何其它章节不得另行表述判据。

```text
adjudicate(C, current_root, path):
    # C：候选会话集合（hit = L2 键的 owners；miss = 有效会话 ∩ roots 含当前 root）
    # 统一定义：other_roots(S) = S.roots − {current_root}   ← 所有根证据判定都用它（v3.16，修 a2）
    # 三值：state(x) ∈ match/gone/unverified（L1）、alive/dead/unverified（根）

    l1   = { S : state(S.attached_l1) }
    rt   = { (S, r) : r ∈ other_roots(S), state(r) }
    any_unverified = (path == P2 ? false : ∃S: l1[S] == unverified)   # P2 下 L1 不作边界依据（v3.23 修 b#22.5）
                     ∨ ∃r ∈ other_roots(S): state(r) == unverified

    if C == ∅                                              → NEW
    G = { S ∈ C : l1[S] == gone }                          # path != P2 时才是"边界消失"证据
    if path == P2: G = C                                    # P2：L1 不作边界依据（部署前提），函数内显式放宽
    if |C| == 1 ∧ |G| == 1 ∧ ¬∃(S,r): state(r) == alive
       ∧ ¬any_unverified                                   → USE(C 的唯一成员)   # unverified 是 USE 的守卫（v3.19）
    if |C| == 1 ∧ |G| == 1 ∧ ¬∃(S,r): state(r) == alive
       ∧ any_unverified                                    → BLOCK(evidence_unknown)
    if |G| > 1                                              → BLOCK(ambiguous_shared_root)
    if |G| == 0 ∧ ∃S: l1[S] == unverified                  → BLOCK(evidence_unknown)   # 归因：不是"别处活着"，而是无法核实（v3.23 修 b#22.4）
    if |G| == 0                                             → BLOCK(other_boundary_alive)
    if |C| > |G|                                            → BLOCK(other_boundary_alive)
    if ∃(S,r): state(r) == alive                            → BLOCK(other_root_alive)
    else                                                    → BLOCK(ambiguous_shared_root)
```

**`state()` 的输入映射（v3.17，修 b#17.2）**：

| 输入 | `l1_state` | `root_state` |
|---|---|---|
| `null`（建立时即无 L1／该根从未记录） | **`gone`** | — |
| 字段完整、`boot` 与当前一致、**标识相符**（pid/sid 与 start 均一致）、进程存在 | `match` | `alive` |
| 字段完整、`boot` 一致，但 **`stat` 返回 ENOENT（对象确认不存在）** | **`gone`** | **`dead`** |
| 字段完整、`boot` 一致，但 **start 不一致（pid 复用）** 或 **`state == Z`（zombie）** | **`gone`** | **`dead`** |
| `boot` 与当前不同 | `gone` | `dead` |
| **sid 型根**、`boot` 一致、`sid_start` **相符** | `match` | **`alive`**（它就是当前根；无独立探测） |
| **sid 型根**、`boot` 一致、`sid_start` **不符**（sid 被新 leader 复用） | **`gone`** | **`dead`**（不同边界，v3.22 补 root 列） |
| 字段不可解析／半损坏 | **`unverified`** | **`unverified`** |
| `/proc` **不可读**（`EACCES`、权限、跨 namespace 但目录存在） | `unverified` | `unverified` |
| **该会话的附件文件整体缺失**（runtime 被清、anchors 尚在） | `unverified` | `unverified` |

**「确认不存在」与「读不到」必须分开（v3.18，修 a#18.2/b#18.2）**：`stat` 的 `ENOENT` ⇒ `gone/dead`；`EACCES`/其他错误 ⇒ `unverified`。
否则「leader 先死」——本方案最主要支持的续接路径——会落进 `unverified` 而被永久阻断。

`null = gone` 的依据：§2.4a 允许只凭 L2 建立会话，这类会话本来就没有 L1 边界可「消失」；
但**损坏 ≠ null**：损坏一律 `unverified`（阻断），不得落进 `gone`。

**`any_unverified` 只是 `USE` 的守卫，不是无条件前置（v3.18，修 b#18.1）**：
v3.17 把它写成"任何 unverified ⇒ 立刻 BLOCK"，会造成**毒丸**——一个与本次调用无关的旧根持续不可读
（hidepid、异用户、跨 namespace），就把**已知且存活**的当前调用者永久挡住，且没有任何恢复动作。
改法：① 当前 root `known ∧ alive` 时（不需要旧根证据），unverified **只披露**（`facts.roots_unverified`），不阻断；
② 只有当判定**依赖**"旧根是否已停"（`USE` 候选、迁移、轮换前提）时，unverified 才阻断。

**C2 分级：未登记的第二调用者必须阻断（v3.24，人裁 C）**

| 情形 | 判定 | 依据 |
|---|---|---|
| 当前 root ∈ `S.roots`（已登记） | 正常推进；`S` 另有存活 root 时披露 `concurrent_callers` | 人类已通过 `start` 认可过这个调用者 |
| 当前 root **∉** `S.roots`，且 `S` 中**无**其他存活 root | 视为同一边界的新进程（重启/续接）⇒ 走既有降级与 `adjudicate` 流程 | 旧调用者已停 |
| 当前 root **∉** `S.roots`，且 `S` 中**有**其他存活 root | **`BLOCK(concurrent_unregistered_caller)`**：`WF_IDENTITY_UNRESOLVED`，出口＝人调 `start` 显式登记（登记后按第一行处理）或结束另一调用者 | **可检测的第二调用者不得自动继承**（C2 分级①） |
| 同 root、多聊天（不可检测） | 合并，**无任何标记**（如实记为不可检测；不设「看起来有监控」的假事实位） | 无信号可分（矩阵已披露） |

> **「已登记」的可机械核对定义（v3.25，修 b#23.1c）**：`当前 root ∈ S.roots`。
> roots 由两处写入：`start`（人调）与降级分支的业务命令（此时其它根已全部确认 dead，不存在第二调用者）。
> 因此「已登记」不等于「人类认可过这个调用者」，但阻断判定**不需要**更强的语义——它只要求
> 「当前 root 不在 roots **且** 另有存活 root」，这在两种写入来源下都可机械核对；留痕由 `maintenance_results` 与 stale 历史承担，不新增字段。

**`other_roots()` 是唯一定义（v3.16，修 a2）**：v3.15 的伪码只在 `unverified` 检查里排除了当前 root，
`USE` 与 `other_root_alive` 分支漏了这个限定——按字面实现会把"候选只剩 S、S 的根就是当前 agent"这种
**文档明确支持**的续接判成阻断。现在所有根证据一律基于 `other_roots(S)`。

**P2 的差异写进函数（v3.16，修 a3）**：`path==P2` 时 `G = C`（L1 不作边界依据），
但 `|C|` 仍是**实际 owners 集合**——多个候选照样 `ambiguous` 阻断。调用处**不得**筛成单元素集合，
也不得跳过守卫；"单聊天假设"是部署前提，不能替代记录层面的唯一性核验。

**判据的三值要求（v3.15，修 a1）**：`attached_l1` 与每个根都必须给出
**match / gone / unverified** 三态——"读不到"与"确认不存在"**不等价**：
`unverified` 一律 `BLOCK(evidence_unknown)` 并在 facts 保留 `l1_unverified` / `roots_unverified`，
**只有 `gone` 才可以作为孤儿接管依据**。

> **行为变化（v3.14/v3.15，有意收紧）**：v3.13 的 #5 允许 `|C|>1 ∧ |U|==1` 即续接；现在要求 `|C|==1`。后果：**共享 agent 且仍有兄弟边界存活时，孤儿续接从"放行"变为"阻断"**（出口＝换终端 / 显式模式）。这是裁决而非笔误，列入 dogfood 观察项（合法续接被挡的频率）。

**读法（P1/P3）**：`USE` 的前提是「所有候选里只剩一个会话、它的 L1 边界已消失（`gone`）、且没有别的存活根」——即**接管孤儿**。
**P2 例外（读法不适用）**：P2 是"部署前提下的连续性复用"——`G = C`，即使旧 L1 仍 `match` 也允许 `USE`；
但 `|C|` 仍是真实 owners 集合，多候选照样 `ambiguous` 阻断。上一句「只有 gone 才能接管」**仅指 P1/P3**。

| 调用处 | C 的来源 | `USE` 的含义 | `NEW` 的含义 |
|---|---|---|---|
| 决策表 #5 | L2 键的 `owners`（合格键见 §2.2c） | 续接该会话（`anchor_degraded="l2-only"`） | — |
| §3.4c（miss 分支） | 有效会话 ∩ roots 含当前 root | 迁移：把当前候选键**追加**进该会话 owners（`anchor_migrated=true`） | 新建会话 |

### 2.4 **R0 验证门**（**实现前的强制门禁**，不可跳过、不可用"缩小范围"替代）

**目的**：方案的唯一支柱是"同一执行边界 ⇒ 同一稳定锚键；不同边界 ⇒ 不同键"。
这条假设只要在某个环境不成立，失败形态就是**静默合并**（两个会话共享启用与写权），且不会报错。
所以必须在使用任何实现代码之前，用探针把每个目标环境**实测一遍**，并把结论写成"支持 / 不支持"清单。

**判定标准（每个环境都必须同时满足）**

| 编号 | 判据 | 不满足的含义 |
|---|---|---|
| R0-A | 同一执行边界内，连续两次调用的 `L1 键`（可用时）与 `L2 键`（可用时）**完全相同** | 锚点抖动 ⇒ 每命令一个新会话 |
| R0-B | 两个不同执行边界（两个终端 / 两个 tmux pane / 两个 IDE 终端）**至少 L1 键不同** | 边界不可区分 ⇒ 静默合并风险 |
| R0-C（唯一裁决） | 若某环境 L1 不可用而只能靠 L2：**`adjudicate()`** 能唯一裁决出本边界（禁止出现多主且都不可裁决） | 多边界共享 root 时无法区分 ⇒ 会并会话 |
| R0-D | 关闭边界后重开（pty 编号可能复用）**不命中旧键** | 继承旧会话的激活与绑定 |

### 2.4a 先定"支持路径"，再逐路径验证（v3.4，修 a#3 的 R0/降级矛盾）

v3.3 的矛盾：R0-A 要求 L1、L2 **都**稳定，而决策表 #4 又允许"L1 每命令变化、L2 单根稳定"降级使用——
同一环境会同时被判"不支持"和"允许"。v3.4 改为**先声明支持哪几条解析路径，每条路径各自验证必要条件**。

| 路径 | 描述 | 支持级别 | 必要条件（R0 逐条验） | 已知限制 |
|---|---|---|---|---|
| **P1** | L1 稳定（同终端重启仍同键） | **完整支持** | R0-A1/A2（同边界同键、异边界异键）、R0-D（重开不命中旧键） | — |
| **P2** | L1 每命令变化，L2 单根稳定（如 agent 经执行服务逐命令新建会话） | **受限支持**（标注"**仅单聊天假设**"） | R0-A3（L2 在同边界稳定）、R0-C（`adjudicate()` 能唯一裁决） | 若该执行服务被多聊天共享 ⇒ **合并，不可检测**（见 §5 披露行） |
| **P3** | 只有 L1（L2 不可用） | **完整支持**（新增：允许 L1 单键建立） | R0-A1、R0-D | 无 L2 时"leader 先死"无法续接 ⇒ 走迁移/重附着 |
| — | 两者皆不稳定 / 皆不可用（容器 pid1、CI） | **不支持** | R0-E（记录为"无锚"） | 运行时 `WF_IDENTITY_UNRESOLVED` |

**首次建立规则（修 a#3 后半）**：`start` 允许只凭 L1 或只凭 L2 建立会话（决策表 #6/#7 不再把"L1 可用但未登记、L2 不可用"判成无锚）：
候选集非空即可建立；候选集为空才阻断。

**判据归属**：R0 只约束**锚点键与解析路径**；`roots`/`activation_stale`/迁移/轮换等**判定语义**由 R2 用例覆盖（§8）。

### 2.4d 支持路径是**部署事实**，P2 默认关闭（v3.5，修 a#5）

R0 只能证明"信号表现"，**不能证明"该部署满足单聊天前提"**。所以支持路径必须是**安装/本机配置里的显式事实**：

```json
// .wf/project-config.json（安装时写入；单字段，不设第二个开关）
"identity": {"path": "P1"}
```

- 取值 `P1 | P2 | P3`；**缺省（键不存在）= `P1`**（旧项目升级到新版时的兼容缺省，不阻断）；
- 按项目配置键契约登记：随发行骨架投放、写入时带 `schema_version`、读取时校验枚举值，非法值 ⇒ `WF_RECORD_INVALID`；
- **写入通道（v3.7，修 b#2）**：`identity.path` 是 **Git 跟踪的项目配置**，不得由会话命令直写。改为：
  1. 安装时由 `install.py --identity-path <P1|P2|P3>` 写入（缺省 P1）；
  2. 之后改值走**维护类命令** `wf.py identity-path --set P2 --accept-single-chat --decision <approve.json> [--preview]`：
     它复用提案文件格式、`object_digest` 摘要校验与成组应用逻辑，但**授权链是维护类**：人直调 + 终端确认，不经任务批准、不动用会话写权（`approve.json` 只批准改什么内容，不授予写权）；仍按维护命令契约走：预览 → 互斥内登记维护持有（新代次）→ 应用 → 维护结果留痕 → 中断出口；
  3. 该类命令**归维护类**（不读信封、不需 activation、不参与 roots）——因此**不存在引导悖论**：P2 未启用时也能改配置。

这样"R0 证据"与"运行期接受"之间才有绑定：**R0 通过 + 显式启用**，两者缺一不可。

### 2.4e R0 环境清单（v3.17 重排：**真实 dogfood 宿主为主轴**）

> 修 b#17.9：原清单（tmux/screen/VS Code/docker/systemd-run/nohup/CI）全是**终端形态**，
> 而方案要服务的是 **agent 宿主形态**。测终端会得出"支持范围很大"的错觉——那些场景显式模式本来就够用。
> 每项都要跑两次：**①人在终端直跑（对照）②经 agent 命令路径（判定依据）**。

| # | 环境 | 必测 | 关键判据 |
|---|---|---|---|
| **A1** | **单聊天 agent 宿主**（Claude Code / Codex 常规进程形态） | ✅ | R0-A/B/C；这是自动模式的主力形态 |
| **A2** | **同一守护进程 + 多个聊天**（IDE 扩展宿主、执行服务） | ✅ | **R0-B 必测边界对**：两聊天能否得到不同 L1 键。相同 ⇒ 归"仅显式模式"（直接回答 §10.2b） |
| **A3** | agent 逐命令新建会话（`setsid` 型执行服务） | ✅ | R0-A3（L2 是否稳定）+ R0-C（能否唯一裁决） |
| B1 | 普通终端 bash / zsh（同终端、两终端） | ✅ | R0-A / R0-B / R0-D |
| B2 | tmux / screen 多 pane | 可选 | R0-B |
| B3 | VS Code / JetBrains 集成终端 | 可选 | R0-A / R0-B |
| B4 | `docker exec -t`（常驻容器） | 可选 | R0-A（每命令是否新 sid） |
| B5 | `docker run …`（容器 pid 1） | 可选 | 记录"无锚"是否符合预期 |
| B6 | `systemd-run --user --scope` | 可选 | 记录是否与发起终端同键 |
| B7 | nohup / 后台化（leader 先死） | ✅ | 子场景 A/B（§5 矩阵） |
| B8 | CI runner | 可选 | 是否被判为"服务进程 ⇒ 阻断" |

**完成条件**：A1–A3 + B1 + B7 必须有结论；可选项不可达记"未验证"，**不得写入"支持环境"表**。

**必测项不可达时的出口（v3.23 修 b#22.7）**：某必测形态本机凑不齐（如没有 A2 多聊天宿主）⇒ **该形态按「仅显式模式」发布**，支持表写"未验证（本机不可达）"并记原因，**不阻塞其余环境结论**。R0 不能被必测项自锁。

### 2.4c 失败形态三分法：哪些能在运行时机械拒绝（修 a#4）

R0 通过 ≠ 运行时能识别一切未测环境。必须把"拒绝依据"分三层写清，否则"不支持环境 fail loud"是空话。

| 类别 | 例子 | 运行时依据 | 责任 |
|---|---|---|---|
| **机械可识别** | 候选集为空；L2 候选是 init 直接子进程；`(pid,start)` 读不到；**L1 单主被破坏**（同一 L1 键出现两个 owner）；roots 空/损坏；owners 裁决不唯一 | 解析器**直接**返回 `WF_IDENTITY_UNRESOLVED` / `WF_HISTORY_UNRESOLVED` | 实现保证 |
| **部署前提**（机制无法识别） | 同一执行服务被多聊天共享；容器内 reparent 到 init；CI runner 形态 | 运行时**无信号**；只能靠"受限支持 + 单聊天假设"声明，或人用显式模式 | 文档声明 + 使用约定 |
| **R0 证据** | P1/P2/P3 在具体环境的稳定性 | 不作为运行时判据；只用于**发布时**声明支持范围 | 发布记录 |

**两处必须先说死的适用面**：
- 「名字不在工具表」「不是 init 直接子进程」**只约束 L2**；L1 不做名字过滤（否则常见 shell session leader 会被误排除）；
- L1 只要求：`sid > 1`、`/proc/<sid>` 可读、**不是内核线程**。

### 2.4b 可选条目与"不可达"的处置（评审 b#6）

- 标"可选"的环境（如 CI runner）若不可达：记为 **`未验证`**，**不算 R0 未完成**；**不得写入"支持环境"表**；文档记"未验证（发布声明层面不支持）"。运行时**不要求识别该环境**——无法识别的部署前提按 §2.4c 的"部署前提"类处理（使用约定 + 文档声明），能机械识别的不合格才阻断。
- 因此 R0 的完成条件是：**必测项全有结论**（支持/不支持/仅显式），**可选类无结论时不得写成支持**。

**必须经 agent 命令路径验证（评审 a#3）**：同一环境要分别测
①「人在终端直接跑探针」与②「agent 通过其命令工具跑探针」——两者的 sid/父链可能不同（本方案已实测到 agent 逐命令新建会话的形态）。
**只有②的结论才决定该环境是否支持**；①仅作对照。

**执行时机与产出**

- **时机**：R1 之前；**R0 未完成不得开始写身份解析代码**。
- **产出**：`r0-results.md`（模板见 §2.5），逐环境记录 `L1 键 / L2 键 / 各判据结论 / 最终判定（支持 / 不支持 / 仅显式模式）`。
- **落地**：结论表**原样写进设计稿**，作为"支持环境"的唯一依据；文档不得出现无 R0 证据的支持声明。
- **回归**：任何锚点逻辑变更（分类表、判据、键构成）都必须**重跑 R0**，并在同批更新结论表。

**处置规则**

- 任一环境不满足 R0-A/B/C/D ⇒ 该环境**列入不支持清单**：行为是 `WF_IDENTITY_UNRESOLVED` + 出口（换终端 / 显式模式 / 未来领养码），**不静默降级、不用启发式去猜**；
- 允许"部分支持"：例如"支持终端类（1–6），不支持 CI（11）"，但**必须逐条有 R0 证据**；
- 不允许以"我们只保证普通终端"替代 R0——**范围收缩必须由 R0 数据支撑**，不能由实现者先验声明。

### 2.5 R0 记录模板（`r0-results.md`）

```text
| 环境 | 边界 A 两次是否同键 (R0-A) | 边界 A/B 是否不同键 (R0-B) | 唯一裁决 (R0-C) | 重开不命中旧键 (R0-D) | 判定 |
|------|---------------------------|---------------------------|------------------|----------------------|------|
| 1 bash 终端 | 是 | 是 | 不适用 | 待测 | 支持 |
| 7 docker exec -t | 待测 | 待测 | 待测 | 待测 | 待测 |
```

**R0 本机结果（2026-11-08 实跑，详见 `r0-results.md`）**

| 环境 | L1 | L2 | 结论 |
|---|---|---|---|
| **A1 单聊天 agent 宿主** | `a78cac38…` 稳定 | `d14cb12e…` | **支持（P1）** |
| B1 bash / zsh / 嵌套 shell | 同一 `a78cac38…` | 同一 | 支持 |
| **A3 setsid 每命令新建** | 每次不同 | 同一 | **仅 P2**（单聊天假设） |
| B6 `systemd-run --scope` | 继承发起终端 | 同一 | 同一执行会话（须声明） |
| B5 `docker run`（容器 pid 1） | 无 | 无 | 不支持（显式模式） |
| **B4 `docker exec -t` ×2** | `sid=7` → `sid=13` | 无 | **不支持**（L1 不稳且无 L2） |
| B7 leader 先死 | 无（reparent 到 systemd） | 无（`parent==init` 被拒） | 不支持（fail loud） |

**人工结果（2026-11-08 回收）**：tmux 两 pane ⇒ L1 不同（**P3：只有 L1**，`tmux` 在工具表内、其后直达 pid1）；IDEA / Zed 集成终端 ⇒ L1 稳定且互不相同（支持 P1），但 **L2 = 各自 IDE 进程**（同一 IDE 实例的所有终端共享同一 L2）；两个 IDE 的 `tty_nr` 相同（`/dev/pts/7` 复用）⇒ **再次印证 tty 不能作身份**。

**A2 结果（zcode，两个会话，2026-11-08）**：会话 1 L1 `3d4cb3fc…`、会话 2 L1 `a6683247…` ⇒ **不同**（各自稳定）；
两者 **L2 相同**（同一 `zcode` 进程）——正是 `owners` + `attached_l1` 要裁决的形态。**R0-B 通过 ⇒ 自动模式在 zcode 可用（P1）**。
前提（必须写成部署前提）：**宿主为每个聊天派生独立 shell/pty**；若宿主直接用自身 session 执行命令，两聊天会同 sid ⇒ 合并。

**ssh -t（单连接内）**：L1 `38219b5a…` 稳定、L2 = `sshd`（每连接一进程）。

**R0 = 完成**（必测 A1/A2/A3/B1/B7 均有结论）。支持环境清单见 `r0-results.md` §九；结论：**§10 待裁项 2b 不需要"共享宿主一律显式模式"**——L1 可分时 `owners` 裁决已足够。

---

## 2.6 三个标识的关系（v3.5 新增，修 a#2）

现有模型里 `session_key` 是对 `{provider, identity}` 做 C 编码后哈希得到的值；`provider=wf` 的 `identity` 是 `issued_id`。
必须把链条写死，否则实现者会把未哈希的 UUID 当路径键：

```text
issued_id            = uuid4()                         # 一次性签发
identity             = {provider: "wf", issued_id}     # 机制稿 §1.4 的 identity 结构
session_key          = SHA256(C({provider, identity})) # 既有哈希域，不变
```

| 用途 | 使用哪个值 |
|---|---|
| `anchors.json` 的 value | **`owners: [session_key…]`**（L1 单主、L2 可多主；见 §2.2a） |
| `.wf/session-bindings/<…>.json` 文件名 | **`session_key`** |
| `.wf/.runtime/attachments/<…>.json` 文件名 | **`session_key`** |
| `writer.holder.id` | **`session_key`** |
| 日志/输出里的可读标识 | `issued_id` 前 8 位（`facts.session_issued="ab12cd34"`） |

正文出现的 `session_id` 一律是**可读别名**。路径与键一律用 `session_key`；但 `identity` 原文（含 `issued_id`）必须存进 `attachments/<session_key>.json`，否则首次绑定（尤其「只启用未绑定」后重启）无法构造 `binding.identity`，也无法核 `SHA256(C(identity)) == session_key`（v3.8，修 a#3）。
轮换示例中的 `new_issued = uuid4()` → `new_key = SHA256(C({provider:"wf", identity:{issued_id:new_issued}}))`。

---

## 3. 生命周期

### 3.1 建立（人调 start）

```text
with 项目锁:
    hit = resolve()                                   # §2.2b：可能是 L1 命中，也可能是 L2 owners 中挑出的一个
    if hit is None:                                   # miss 分支
        session_key = new_session(provider="wf", issued_id=uuid4())   # 或按 §3.4c 迁移
    else:
        state = five_state(hit.session_key)           # §3.5：S0/S1/S2/S3/S4
        if state == S1:                               # 待核实：证据不足，绝不自动签发
            raise WF_HISTORY_UNRESOLVED(facts={reason:"binding history unknown", session:hit.session_key},
                  next_="按 §3.5 S1 走 repair（人确认后修复记录；证据不删，故不会「重跑 start 即变 S0」）")
        if state == S0 and identity_unrecoverable(hit.session_key):
            # §3.5：attachments 丢失且非本次签发的 S0 已在上面被拦成 S1；能到这里的 S0 必然可恢复身份
            session_key = new_session(...)            # 或复用记忆中身份（本次签发）
            rebind_routes(cand_keys → session_key)    # 同锁内改指，旧键记 stale_routes
        else:
            session_key = hit.session_key             # 复用（续接）
    maintain_attachments(session_key, current_root)   # upsert root；清/置 activation_stale
    commit anchors.json                               # 组原子：L1 单主校验、L2 owners 追加
```

注意：**状态只写 `attachments[session_key]` 一份**；`anchors.json` 里**没有** `roots`/`activation_stale` 字段。

### 3.2 一会话一对象（不变）

已绑定 session 只能恢复原对象；请求另一对象 ⇒ `WF_BINDING_MISMATCH`。

### 3.3 轮换（对象终态 → 新会话）：**owner 替换**，不是字段赋值

```text
with 项目锁:
    S = 本次命中的 session_key
    if object_state(S) terminal \
       and writer.holder ∉ {S, 其它会话的 recovering} \
       and other_roots(S) 中**无 alive、无 unverified**:        # v3.23 修 a#22.3：否则会把别的活跃调用者带进新对象
                                                                 # （不满足 ⇒ 阻断，要求那些调用者先结束或先 start）
                                                              # 别人的 recovering 交接也阻断（等它恢复完再轮换）
        N = new_session(issued_id=uuid4())                    # ① 写 attachments[N]：identity/activation/
        write_attachment(N, ..., roots = roots(S) ∪ 当前root) #    attached_l1/attached_root/roots；此刻它还没有路由 ⇒ 孤儿
        replace_owner(S → N)                                  # ② 组原子操作，见下
        commit anchors.json                                   # ③ 一次 rename 提交
        audit_superseded(S → N)                               # ④ 提交成功后写 superseded_by（仅审计）
```

**`replace_owner(S → N)` 的语义（唯一定义）**：遍历**所有**路由条目，把 `owners` 中的 `S` 换成 `N`，**保留其它 owner**。

| 路由条目 | 轮换前 | 轮换后 |
|---|---|---|
| A 的 L1（单主） | `{A}` | `{N}` |
| 共享 L2（A、B 两个终端共用同一 root） | `{A, B}` | `{N, B}` ← **B 不受影响** |
| B 的 L1 | `{B}` | `{B}` |

- 轮换是 **L1 单主规则的受控替换路径**：`{A}→{N}` 之后仍单主；
- 若某键的 `owners` 只含 `S`，替换后键指向 `N`（键本身不变，只有 owner 变）；
- 已无任何键指向 `S` ⇒ `S` 不再"有效"（§3.4c），其附件成为历史（可 GC）。

> v3.12 修正：v3.11 只把 §2.2a 改成 `owners`，§3.3/§7 仍按 `value.session_key == S` 的单值语义——共享 L2 时会把 B 一起改指或把 A 留在 owners 里。

### 3.4 根进程集合（`roots[]`）：判定在维护**之前**，降级必须**持久化**

> v3.3 修正两处（评审 a#1、b#1、b#4）：
> ①原顺序"先 upsert 再剪枝"让 TTL 分支**永不可达**，且"当前根在集合中"恒真 → 判定失效；
> ②"同锚新调用者"的降级是**推导态**，一次只读调用把它洗掉，从未经人 start。

**数据结构**（存于 `attachments/<session_key>`，**会话级单份**）：
`roots: [{kind, pid|sid, start|sid_start, exe, boot, first_seen, last_seen}]`

> **boot 必须进条目（v3.17，修 b#17.1）**：`starttime` 是「自本次 boot 起的 tick」，跨重启后 `(pid,start)` 会撞车。
> 一切存在性/存活/可解析判定都**先比 `boot`**：`boot ≠ 当前 boot_id` ⇒ 该条目**视为 dead**（不是 unknown），可直接剪枝。

**常量与淘汰**：`ROOTS_MAX = 8`；**只淘汰死条目**；全为存活且超上限时**不淘汰**，改为 `facts.roots_capped=true`（评审 b#8）。
**不再有 ROOT_TTL**（评审 b#4：Linux 上存活总可证；TTL 会把活着的 agent 在隔夜后剪掉 → 强迫重新 start，纯粹变差）。

**每次调用（仅"需要 activation 的业务命令"）的处理顺序——不可调换**。
**C2 检查位置（v3.25）**：`!known ∧ others_alive ≠ ∅` 的阻断**必须先于任何 upsert**；
否则未登记的调用者第一条命令就把自己写进 roots，第二条起 `known` 恒真，人裁的阻断永远失效。

```text
1. snapshot = 读 attachments[session_key].roots（维护前）
2. 用 other_roots 语义为每个旧根求状态（三值）：
     known        = 当前 root ∈ snapshot
     others       = snapshot − {当前 root}
     others_dead  = { r ∈ others : state(r) == dead }
     others_unk   = { r ∈ others : state(r) == unverified }
     others_alive = { r ∈ others : state(r) == alive }
3. 判定（只认 confirmed dead，"读不到"不算死）：
     if others_unk 非空 **且本次判定需要旧根证据**
        （判定需要旧根证据 ⇔ `!known ∧ others_alive == ∅`：既要不认识当前 root，又没有存活兄弟根；
          有存活兄弟根时"不降级"已由它自己决定，unverified 与本次判定无关——v3.23 修 b#22.2）
                               → 返回 `WF_HISTORY_UNRESOLVED`（`facts.reason="evidence_unknown"`，v3.18 明确码位），
                                 **不置 stale**、**并且立即结束本次调用**：
                                   **不得执行第 4 步的 upsert**（评审 a#17：否则新调用者被登记成"已知"，
                                   下一次旧根转为 dead 时就不再进入降级分支，等于绕过"须人重新 start"）；
                                   roots 与 activation 状态**原样保留**；不剪枝
     elif !known ∧ others_alive 非空
                                 → **C2 阻断（v3.25，修 a#23.1/b#23.1）**：返回 `WF_IDENTITY_UNRESOLVED`
                                   （`facts.reason="concurrent_unregistered_caller"`），**不 upsert、不剪枝、立即结束**；
                                   roots 与 activation 原样保留；出口＝人调 `start` 显式登记，或结束另一个调用者
     elif !known ∧ snapshot 非空 ∧ others_alive 为空 ∧ others_dead 覆盖 others
                                 → attachments[session_key].activation_stale = True   # 旧根全部确认已死
                                   （仍继续第 4 步登记，本次返回 WF_NOT_ENABLED）
4. 维护并写回：upsert 当前 root → 只剪掉 confirmed dead 条目（unverified 一律保留）→ 超 ROOTS_MAX 只淘汰 dead
5. 若 others_alive 非空 ⇒ facts.concurrent_callers = [当前 root] + others_alive（披露，不阻断）
```

**`WF_NOT_ENABLED` 的新判据**：`attachment.activation` 无效 **或** `attachment.activation_stale == true`。
**只有 `start` 能清除 `activation_stale`**——建立、**轮换、迁移、附件恢复**四种 start 内动作都要写 `false`（评审 b#8 的统一声明）。

**只读命令不参与**：只读诊断（`status/ready/inspect/help/...`）不解析 roots、不写、不刷新 `last_seen`
（避免"只读也要拿项目锁"，也顺带堵死"用只读调用把降级洗掉"的路径）。根条目由 `start` 与业务命令维护。

**措辞修正**：判定表的第三行准确表述是「当前 root **不在 snapshot 中** ∧ snapshot 中除当前外**无存活条目**」
（upsert 之前，当前根本来就不在集合里）。

**空/不可识别集合 = 未知态（fail-safe，评审 b#1）**：若 `snapshot` 为空、或条目字段不可解析（半损坏、手改、异常中断），
**不得落到"正常推进"**：视同"旧的调用者不可证明"⇒ 写 `activation_stale = true` 并返回 `WF_NOT_ENABLED`（业务命令），
出口"人重新 `/wf-start`"；`start` 则可重建附件（§3.5）。删掉 TTL 后这是"空集合"的**唯一**处置，不再有第二条规则。

**锁（v3.6 统一，修 a#2/b#1 的半截修复）**：

| 记录 | 保护它的锁 |
|---|---|
| `attachments/<session_key>.json`（含 roots / activation / stale） | **该会话的附件锁** `<session_key>.lock` |
| `anchors.json`（组更新）、`writer.json`、`session-bindings/*` | **项目锁** `.wf-lock` |

**锁顺序（唯一，防死锁）**：需要两把锁时**先项目锁、后附件锁**；**禁止持有附件锁时再取项目锁**。
因此业务命令维护 roots 只取附件锁（不与写权锁抢），`start` 按 项目锁 → 附件锁 顺序取。

### 3.4b 根的两种类型与三种存活状态（v3.8 统一，修 a#6 / b#2）

**根只有两种结构，禁止混用**：

```json
{"kind": "pid", "pid": 5538, "start": "16466", "exe": "node"}      // L2 根
{"kind": "sid", "sid": 4711, "sid_start": "16200", "leader": "bash"} // L1 根（L2 不可用时的退化形态）
```

| 类型 | 存活判定 | 相等条件 | 是否可能 unknown |
|---|---|---|---|
| **pid** | 读 `/proc/<pid>` 的 `starttime` 与 `state` | `(pid, start)` 完全相同 | **是** |
| **sid** | **不做存活判定**（sid 不是进程；`/proc/<sid>` 只是 leader，可能已死而会话仍存） | `(sid, sid_start)` 完全相同 | **否**（结构性无探测对象） |

**注**：`attached_l1` 用**可解析性**（leader 进程存在且 sid 相符）判断，属于存在性检查，**不走本表的存活三态**（评审 b3）。

**pid 根的三种状态**：alive（存在且 start 一致）/ **dead**（不存在、start 不一致、或 zombie）/ **liveness-unknown**（`/proc` 不可读：权限、跨 PID namespace、瞬时 IO 错误）。

**unknown 的唯一语义（三处统一）**：

| 场合 | 处置 |
|---|---|
| **需要旧根证据的放行判定**（`adjudicate()` 的 `USE` 候选、迁移、轮换前提） | 阻断（`evidence_unknown`）：`liveness-unknown` 使"旧调用者已停止"无法证明 |
| **不依赖旧根证据的续接**（当前 root `known ∧ alive`，例：决策表 #1） | **只披露**（`facts.roots_unverified`），不阻断（v3.19，修 b#18.1） |
| **决策表 #1/#2/#3 的 `attached_l1` 为 `unverified`** | **无效果**：这三行不调用 `adjudicate()`（动作列直接"用 S"），`attached_l1` 只在 #4/#5/miss 进入裁决（v3.20，修 b#19.1） |
| 仅作**披露**的场合（`facts`、`status`） | 报 `facts.roots_unknown=[…]`，不影响本次判定结果 |
| `sid` 型根 | **永远不算 unknown**（无探测对象）；同一性按 **`(boot, sid, sid_start)` 全等**判定——**同 sid 但 `sid_start` 不同 ⇒ 不同边界**（v3.22 修正旧措辞） |

**`{sid}` 退化形态的行为**（收回 v3.6 的含糊表述）：该形态下"同终端先后两个 agent"⇒ 同一执行会话、**不降级**（**仅当**该会话 root 为 `{sid}` 且该 sid 仍是当前调用者的 leader；人直跑终端属此形态，v3.23 收紧）；矩阵单列一行。

### 3.4c 迁移附着的确定性时序（v3.5，修 a#3 / b#2）

**边界（v3.6，修 b#5）**：§2.2b 决策表只管**每次调用的路由命中**；本表只接管**候选全部 miss 之后 `start` 的处置**。
`start` 的顺序：先判 `adjudicate()`（唯一裁决），都不适用（即候选集为空）才新建会话（迁移优先于新建，避免把可迁移的旧会话当新会话）。

> **"可达"概念已废除（v3.13）**：v3.3 的"可达 = 任一登记键命中候选 或 有除本根外 alive 根"在 owners 模型下两项都失效
> （miss 分支里键不可能命中；多主下"除本根外 alive 根"又是常态）。现在一律用 `adjudicate()` 内部的
> `l1_state`（match / gone / unverified）与 `root_state`（alive / dead / unverified）三值判据。

> **本表只管"候选全部 miss 之后 `start` 的处置"**。命中场景归 §2.2b（#1/#5/#4）。

**第一步：迁移候选集怎么来（v3.8 新增，修 a#2）**

> 旧根已死只能证明"它停止了"，**不能证明当前调用者就是它的后继**。

```text
有效会话 = S 满足：存在至少一个路由键（anchors.json，且键合格见 §2.2c）指向 S
           # ← 以「已提交的路由事实」为准，v3.10 修正：
           #   ① 轮换中断留下的新附件没有任何路由键 ⇒ 天然无效（孤儿）
           #   ② 被轮换替代的旧会话，其路由键已改指新会话 ⇒ 天然无效
           #   ③ 不再用 roots/`superseded_by` 判有效性（前者恒真、后者可能在崩溃时未写）
candidates_S = { S ∈ 有效会话 : S.roots 中包含"当前 root"（同 kind 且同标识） }
```

**额外前提（v3.9，修 a1）**：只有**当前 L1 不可用**时才允许进入迁移；
若当前 L1 **可用但未登记**，说明这是另一个边界（它有自己的 L1），即使 root 相同也**不得迁移**——
否则 P1 下「新终端共享同一 agent 进程」会被 `adjudicate()` 判成可迁移（接管）。

- 当前 root 是 **pid 型**：要求 `(boot, pid, start)` 完全相同（同一 agent 进程；boot 必需，跨重启会撞车）；
- 当前 root 是 **sid 型**：要求 `(boot, sid, sid_start)` 完全相同（同一终端 leader）；
- **`candidates_S` 为空 ⇒ 不得迁移**：与任何旧会话无正向关联 ⇒ 按 §2.2b #6/#7b **新建会话**（绝不"挑一个死掉的旧会话接上去"）。

**第二步：与决策表 #5 用**同一套**裁决（v3.12，修 b1）**

v3.3 时代的"可达性"在 owners 模型下已经失效：miss 分支里 S 的键不可能命中当前候选，
而"除本根外的 alive root"在多主场景下又是常态 —— 于是旧 M3 几乎不触发、旧 M4 几乎总触发，
**两个终端共享同一 agent 进程的合法形态会在 leader 死后被迁移合并**。
因此 v3.12 把迁移处置并入 **#5 的同一判据**（`attached_l1` 的可解析性），miss 与 hit 两个分支对同形数据给出同一结论：

```text
C = 有效会话 ∩ { S : S.roots 含当前 root }
verdict = adjudicate(C, 当前 root)      # §2.3d，唯一判据
```

| verdict | 动作 |
|---|---|
| `USE(S)` | **接管孤儿**：把当前候选键**追加**进 S 的 `owners`（L1 单主校验照旧）+ `upsert 当前 root` + `activation_stale=false`，同批；`facts.anchor_migrated=true` |
| `NEW` | 新建会话（§2.2b #7b）；业务命令阻断 |
| `BLOCK(reason)` | 阻断并给出该 reason 对应的出口（人核实 / 人指认 / 换终端 / 显式模式 / §5.5） |

**「人核实」必须有落点（v3.19 定稿编码，修 a#18.1 / b#18.2）**

`WF_HISTORY_UNRESOLVED(evidence_unknown)` 的出口除只读核对，还包括维护类动作：

```bash
wf.py repair --mark-root-gone --session <session_key> --root pid:<boot>:<pid>:<start> --decision <f> [--preview]
```

| 项 | 规定 |
|---|---|
| **后置动作** | **从 `attachments[<key>].roots` 中删除该条目**（不是加状态字段）——删除后 `others_dead` 自然覆盖 `others`，后续判定无需新增状态来源 |
| **留痕** | 原像（`kind/pid/start/exe/boot`）+ 人的决策摘要 + 时间写入 `writer.maintenance_results`；`state()` **不需要新增"人裁"行**（条目已不存在） |
| **参数面** | **附件整体缺失时本命令不适用**（无 `roots` 可改）⇒ 指向 §3.5 的附件重建；只接受 **`pid` 型根**且**必须带 `boot`**（`sid` 型无探测对象、永不 `unverified`；不带 boot 无法在跨重启复用下唯一定位 ⇒ 匹配到 0 条或多条时**阻断**并列候选，交人重新指定） |
| **最小验证** | 持续不可读的旧根 → 人确认停止并 repair → 再次 `start` 按剩余事实恢复（**不再报同一错误**） |

没有这一条，"人核实"是空出口。

**跨文件事务（v3.20，修 a#19.3）**——本动作同时改 `attachments` 与 `writer.json`，必须走既有 action 协议：

```text
with 项目锁:                                   # 锁顺序：项目锁 → 附件锁（§3.4）
    writer.action = {kind:"mark-root-gone", session, root:{boot,pid,start}, step:"intent"}     # ① 意图
    with 附件锁(session):
        roots.remove(root)                                                                     # ② 改数据
    writer.maintenance_results += {前像: root, 决策摘要, at}                                    # ③ 回执
    writer.action = null                                                                       # ④ 清意图
```

| 中断点 | 重入判定 |
|---|---|
| ①后、②前 | 意图在 ⇒ 重跑整个动作（幂等） |
| ②后、③前 | 意图在、条目已不在 ⇒ **只补写 ③**（回执缺前像时从意图里取） |
| ③后、④前 | 回执在、条目已不在 ⇒ 只清意图 |
| 无意图、条目消失、**且 `maintenance_results` 已有同根回执** | **幂等成功**：报「已处理」并退出（正常重跑不应被当成损坏，v3.23 修 b#22.10） |
| 无意图、条目消失、**且无回执** | 视为外部直改 ⇒ `WF_HISTORY_UNRESOLVED`（不猜） |

> **语义**：`USE` 只在「候选里只剩一个会话、它的 L1 边界已消失、且它没有别的存活根」时成立——
> 即**接管孤儿**，而不是**加入现存共享**。旧的 X1–X5 编号已作废，判据全部收敛到 `adjudicate()`。

**迁移优先于新建**：`start` 在候选全 miss 时调用 `adjudicate()`；返回 `USE` 则迁移，返回 `NEW`（即 `C` 为空）才新建会话。

旧路由键在迁移后**保留**（它们已不可命中，按 boot 前缀 GC 自然清理）；不修改历史绑定。

**孤儿附件 GC**：`attachments/<key>` 满足「无任何路由键指向 + 绑定对象已终态 + writer 不持有该 key」⇒ 可清理（与路由 GC 同时执行）。

**路由存档 GC**：路径切换产生的 `anchors.invalidated-<ts>.json` **仅保留最近 3 份**，更早的删除（它们是排障材料，不是判定依据）。

**附件整体缺失时的 start 入口（v3.25，修 a#23.3）**：附件缺失会让 `adjudicate()` 返回 `BLOCK(evidence_unknown)`，
若照字面执行，`start` 也进不了 §3.5 的 S2 重建——**恢复入口要求附件先完整**，形成死锁。

因此把"识别待恢复候选"与"批准继续推进"分开。**两条出口的优先级**：附件整体缺失 ⇒ 本条（start 重建）；根不可读（附件完好）⇒ `repair --mark-root-gone`。两者互不覆盖。

| 调用 | 行为 |
|---|---|
| 普通业务命令 | 仍按 `BLOCK(evidence_unknown)` 阻断（不得因缺附件就续接） |
| **`start`** | **仅在下列三条同时成立时**允许越过该阻断并进入 §3.5 的 **S2/S3/S4**：①**候选唯一**（`|C|==1`；多候选 ⇒ 不越过，走人指认/repair）②**该阻断确由候选附件整体缺失引起**（`facts` 指向 `state()` 表最后一行，而非 hidepid/跨 namespace 的 liveness-unknown）③`binding` 可校验 + 写权/WIP 核对通过 |
| 其它 unverified 来源 | **不越过**：仍走 `repair --mark-root-gone` / §5.5 人工核实（那才是它们的出口） |
| S0（从未绑定） | **不在本规则范围**（无 binding 可校验）；S0 只在"本次签发后立即丢失"的内存事实下可达 |

### 3.5 运行态丢失

- **anchors 丢失** ⇒ 下次调用 `WF_IDENTITY_UNRESOLVED` ⇒ 人调 start ⇒ **签发新 session**。
  但新会话**必须照常过三关**：`WF_WRITER_BUSY`（旧写者未释放）、WIP 处置、handover recovering。**注册表丢失不等于干净新会话**（A#6）。
- **attachments 丢失** ⇒ `activation`/`instance_expected` 缺失 ⇒ `WF_NOT_ENABLED` / **`WF_ATTACHMENT_MISSING`**；
  **普通调用不补齐**（否则独立对账与启用检查被绕过）。**恢复只能在 `start` 内，且五态互斥**（v3.9 统一，修 b3）：

  **先判五态**（v3.8，修 a#5；「无 binding」不能直接当首次使用）：

  | 态 | 判据 | 与轮换的顺序 |
  |---|---|---|
  | **S0 确未绑定** | 无 binding，**且该绑定路径在 Git 历史中从未出现**（机械判据见下） | — |
  | **S1 绑定缺失（原本应有）** | 无 binding，但有**曾绑定证据**（`instance_expected` 有值／任务范围写权引用／提交类维护回执／Git 任意历史）⇒ **不得当首次使用**（**仅有路由键不构成证据**，v3.23 修 a#22.5） | 先报 `WF_HISTORY_UNRESOLVED`，人确认后 repair |
  | **S2 在途** | binding 存在、对象未终态 | 先恢复，再谈轮换 |
  | **S3 终态已清理** | 对象终态**且 `writer.holder` 与 `recovering` 均不指向该 key**（可机械核对；v3.17 修 b#17.4） | 不需补释放：重建"仅用于接续/轮换"的附件（activation 由本次 start 形成），然后按 §3.3 轮换；不得进入 §5.4 |
  | **S4 终态未清理** | 对象终态**且 `writer.holder` 或 `recovering` 指向该 key** | 只恢复补释放所需，走 §5.4，不轮换 |


  | 分支 | 步骤（走完即结束） | identity 来源（v3.9，修 a3） |
  |---|---|---|
  | **S0 确未绑定** | 建附件（`instance_expected=null`, activation 由本次 start 形成, `attached_l1/attached_root` 取当前值, `roots:[当前 root]`）；不读 binding | **完整旧附件的 `identity` 可复用**（同 key ⇒ 同身份）；附件缺失才新建 `issued_id`（v3.23 修 a#22.5） |
  | **S1 绑定缺失（原本应有）** | **阻断** `WF_HISTORY_UNRESOLVED`（`reason="binding missing"`），出口=人确认后 repair；不重建 | 需人裁 |
  | **S2 在途** | 核对象未终态 → 核写权（`WRITER_BUSY`：holder 非本会话且非中断态 ⇒ 仅报告）→ 重建 `instance_expected := binding.instance_id` → 写 activation/stale=false/roots | **从 `binding.identity` 读回**，并核 `SHA256(C({provider,identity})) == session_key` |
  | **S3 终态已清理** | 重建"仅用于接续/轮换"的附件（不核释放、不进 §5.4）→ 按 §3.3 轮换 | 同 S2 |
  | **S4 终态未清理** | 只恢复补释放所需 → 走 §5.4 补释放 → 不轮换 | 同 S2 |

  **identity 不可恢复时（a3）**：若 S0 场景下附件已丢且从未绑定（原 `issued_id` 无法还原，`session_key` 不可逆）⇒
  **不得沿用旧 `session_key`**：走"新会话建立"出口（新 `issued_id` → 新 key），旧 key 仅作历史；若仍有路由键指向旧 key，报 `facts.stale_routes=[…]` 并清理。

  **S0/S1 的机械判据（v3.11 重写，修 a2）：先找"应有绑定"的证据，再看缺什么**

  | 证据（任一成立即"曾绑定过"） | 说明 |
  |---|---|
  | `attachment.instance_expected` **有值** | 已绑定会话一直有附件；绑定文件被删后附件仍带着对账值——**附件存在不能证明"从未绑定"** |
  | `writer.holder/handover` 的 **scope 是任务/实例**（`scope.object` 非空） | **绑定类写权**引用 ⇒ 应有绑定 |
  | `maintenance_results` 中登记过该 key 的**提交类**动作 | 同上 |
  | `git log -- <binding path>` 非空（**任意**历史，非 `--diff-filter=D`） | 绑定曾被提交 |
  | 当前 `session-bindings/<session_key>.json` 存在 | 当前绑定 |

  > **不构成证据**：`writer.holder.scope` 为 **preparation**（未绑定会话合法取得准备范围，机制稿 §5.3 允许），
  > 以及单纯的"有路由键"。评审 a2：把 preparation 引用当"曾绑定"会把**合法的未绑定准备流程**判成记录缺失。

  | 观测 | 判定 |
  |---|---|
  | 上述证据**任一成立**且当前绑定文件缺失 | **S1**（记录缺失，`WF_HISTORY_UNRESOLVED`，出口=人确认后 repair）——**不得当首次使用** |
  | 当前绑定文件**存在且可校验** | **S2 / S3 / S4**（按对象态与写权细分） |
  | 证据全部不成立 + **附件完整** + `instance_expected` 为空 | **S0**（正常的"只启用未绑定"，**不要求本次签发**——评审 a2）|
  | 证据全部不成立 + **附件丢失** + 该 key 是本次签发 | **S0**（内存事实） |
  | 证据全部不成立 + **附件丢失** + 非本次签发 | **S1 待核实**（不直接判 S0） |

  **原则**：`S0（确未绑定）` 是**最严格的一档**——必须"没有任何曾绑定的痕迹"且"身份可追"；缺证据即待核实。

- **附件存在但 `instance_id` 不符** ⇒ 先**呈现差异**（`facts.diff = {expected, current, binding}`），人确认后**同一次 start** 重建；
  不得因为进入 start 就无条件覆盖差异。

---

### 3.6 首次绑定的写回与中断补齐（v3.15 新增，修 a3）

`instance_id` 由 `bind` 生成。**自动模式下它是从附件读的**，所以第一次绑定必须把它写进附件，否则
"启用未绑定 → 首次绑定 → 下一条命令"会因附件仍为 null 而失败。

**写入链（顺序固定，锁顺序见 §3.4：项目锁 → 附件锁）**：

```text
bind / handover-accept（首次）:
  with 项目锁:                       # 写 binding + writer 代次
      writer.action = {kind:"bind", object, step:"intent", before:{instance_expected:null}}   # ⓪ 意图（v3.23 修 b#22.3）
      binding = {instance_id: <新生成>, object, …}      # ①
      writer.holder/handover 更新                        # ②
      with 附件锁(session_key):
          attachments[session_key].instance_expected = instance_id   # ③
      writer.action = null                                                        # ④ 清意图
  commit
```

**中断与重入（四类残态；共同规则：证据不可凭外观认定）**：

| 残留状态 | 判定 | 处置 |
|---|---|---|
| binding 已写、附件 `instance_expected == binding.instance_id` | 正常 | 无动作 |
| binding 已写、附件 `instance_expected` 为 null，且**本次锁内有该绑定的中断意图**（`writer.action` 指向同一对象、同一动作、步骤未完成） | **确认的前向半写入** | 在 **`start` 内**按 §3.5 的 S2 路径补齐（核对象未终态 + 核写权后写回）；**不在普通业务调用里补**（§3.5 总规则：普通调用不补齐） |
| binding 已写、附件非空但与 binding 不符 | **真实差异** | 保留差异：`WF_BINDING_MISMATCH` + `facts.diff`，只在 `start` 内经人确认后重建 |
| **附件有值、binding 缺失** | **不得清空**：这可能是"绑定被删"（S1）而不是反向半写入 | 按 **§3.5 的 S1** 处理（`WF_HISTORY_UNRESOLVED`，保留附件证据）；若 `writer.action` 证明是未完成的首次绑定意图，则由**既有动作恢复协议**补完 binding，**不清空 `instance_expected`** |

> **v3.16 修正（评审 a1/b1）**：①删掉"普通调用幂等补齐"——它与 §3.5 "普通调用不补齐"直接冲突，也给了伪造 binding 一条自动写回通道；
> ②"附件有值、binding 缺失"不再按 S0 重来，因为**从当前文件无法证明 binding 从未写入**，清空只会抹掉"绑定丢失"的证据。

**首次交接接收**（handover）同链：接收方写入 `instance_expected` 后方可推进；两把锁的顺序不变。

## 3.7 契约修订清单（v3.17 新增：这些不是"措辞同步"，是**语义变更**，必须同批落账）

> 设计稿 §0 的维护协议要求：唯一定义条目变更时必须同批登记「定义 / 写者 / 消费点 / 失败出口 / 正反例」并同步 index。
> 以下是本方案对既有契约的**实质改动**，R5 必须逐条改文并更新索引，不能只写"三稿 0 problem"。

| # | 被改动的契约 | 原文 | 本方案语义 | 必须同步的位置 |
|---|---|---|---|---|
| C1 | 设计稿 §1.3「压缩后保持不变且**新会话不同**的稳定标识」 | 以「会话」为粒度 | **以「执行边界」为粒度（人裁 2026-11-08 取 ①，见 OD-9）**：同一终端/同一 agent 进程 = 同一执行会话（矩阵有专行）。**使用约定随之改变：一个终端同时只干一个任务；要并行请另开终端/窗口** | 设计稿 §1.3 定义句、\*\*environment 行\*\*、index 条目、§8.2 场景行、skills 文案（工作习惯） |
| C2 | 设计稿 §1.3「复制到另一会话**不构成接管许可**」 | 复制不接管 | **分级（人裁 2026-11-08，选 C，见 OD-8）**：①**可检测**——同一执行边界内出现**未登记的第二个调用者**（当前 root ∉ `S.roots` 且 `S` 另有存活 root）⇒ **阻断**，人调 `start` 显式登记后才放行；②**不可检测**——同一宿主进程内的多个聊天（同 root）⇒ 合并并披露。复制标识本身仍不构成接管（自动模式身份由锚点派生，拷文件无效；显式模式保留原语义） | 设计稿定义句、机制稿 §1.4、§6 强度声明、§5 矩阵、§9 判据 7 |
| C3 | 机制稿 §1.4「activation 缓存保存在**宿主当前会话上下文**，经请求信封传给独立 CLI 进程，**不写进项目 Git / 本机记录 / 他人会话文件**」 | 由宿主携带 | 改为 **wf 自己写入 `attachments/<session_key>`（gitignore 运行态）** | 机制稿该段整体改写 + 失败出口 |
| C4 | 机制稿 D14「`provider=wf` 自签发属**第二轮**，未交付前一律 `WF_IDENTITY_UNRESOLVED`」 | 第二轮 | **提前到第一轮**。裁决记录：`open-decisions.md` OD-7（2026-11-07 会话原话「provider=wf 提前到首轮 这点同意」）；D14 需改为"第一轮交付" | 机制稿 D14、设计稿 **§8.1 首轮最小闭环清单**、§8.2 轮次映射、实现稿批次表 |
| C5 | 机制稿 §1.4「宿主/skill 适配层把身份放入请求 JSON」 | 适配层注入 | 自动模式下**适配层不再注入**；显式模式保留该通道 | 机制稿该段、skills 文案、安装器 |
| **C6** | 设计稿 §6.5「实施 CLI 取 action 会话的宿主身份；两名 reviewer 须与其不同」 | 从 `host_id` 取 | **参与者身份与会话路由身份分离**：reviewer 由 `review-context --as <cli>` 声明；实施 CLI **在 `review-launch` 时声明**并写入该轮 `reviews.launches[].implementation_cli`（会话级默认值仅预填）；**任一缺失 ⇒ 拒绝产生 pass**，补录＝重跑 launch 或 repair | 设计稿 §6.5、机制稿审查段、`review.py` 的 `normalize_agent` 调用点、skills（wf-review / wf-review-action）。**实现细节与验收见 `review-identity-protocol.md`** |

### 3.7a/3.7d/3.7e 已拆出（v3.30，S1 收口）

审查参与者身份（C6）、`--as` 三点一致性、`review-launch` 跨文件事务，**已拆到独立文档**：

→ **`review-identity-protocol.md`**（议题：审查身份与暂存）

理由（终局评估 §三 C 类）：这三节属于**审查子系统**，是"删掉自动模式 `host_id`"的连带依赖，
与"零输入身份"是两个议题；放在一起会让评审在两者之间来回串。
本方案只保留一行契约引用（§3.7 契约清单 C6），实现细节与验收在拆分文档内。

### 3.7b 适配层退场（C5 的迁移步骤，修 b#17.8）

**风险**：只要存量适配层继续注入 `session` 对象，模式判定就永远走显式模式 ⇒ **自动模式成死代码**。

| 阶段 | 适配层行为 | 说明 |
|---|---|---|
| **升级项目**首次 | 仍注入 `session` | `identity.path` 不存在 ⇒ 显式模式，行为与升级前一致（不破坏在途项目） |
| **新装项目** | **不注入** | 安装器写入 `identity.path` ⇒ 从一开始走自动模式（干净路径）；未验证宿主则由安装输出附显式模板兜底 |
| 人跑过 `wf.py identity-path --set <P>`（或新装时安装器写入） | **不再注入** | 标记语义 = **`identity.path` 键已写入**（见下） |
| 过渡期 | 两种 activation 来源并存 | 显式模式只读请求里的 activation；自动模式只读 `attachments`（模式由「是否含 session 对象」唯一决定，不存在混用） |

**一致性规则（v3.22 修正计数）**：表中前两行（升级/新装）由 **`identity.path` 键是否存在**决定，二者互斥；
"过渡期"行描述的是**同一项目内两种来源并存的时间窗口**（与键维度正交），不是第三种状态。

R3 必须交付"适配层如何停止注入"的具体点（skills 文案 + 安装器提示），不能只写"`--envelope-last` 退役"。

**「键缺省 = P1」与「键缺省 = 继续注入」必须分开说（v3.18，修 b#18.3）**：

| 事实 | 缺省（键不存在）时的语义 | 依据 |
|---|---|---|
| **解析路径** `identity.path` | 缺省 = **P1** | §2.4d |
| **适配层是否注入** | 缺省 = **仍注入**（等价显式模式） | 升级兼容：键不存在 ⇒ 不知道是否已迁移 |
| 两者关系 | **同一字段，两种用法**：字段**存在** ⇒ 走该路径且停止注入；字段**不存在** ⇒ 解析按 P1 兜底、但注入继续 | 这样升级当天行为不变，`identity-path --set` 才是显式切换点 |

**未验证宿主的平滑回退（b#18.3 后半，v3.19 修正措辞）**：框架**不做宿主探测**（约束①），安装器**无法**判定"当前宿主形态是否已验证"。
可达行为只有两条：① 安装输出**展示**支持环境结论表（供人自行对照，来源是发行内随附的 `r0-results.md` 副本或安装器内置摘要），
② **无条件附上显式调用模板**（`--envelope` 完整示例）。不假装安装器能做判定。

### 3.7c 轮次归属（C4 的落地，修 b#17.12）

| 批次 | 所属轮次 | 首轮身份通道 |
|---|---|---|
| R0 | 第一轮（前置门） | — |
| R1–R5 | **第一轮** | 自动模式（P1）+ 显式模式兼容 |
| 首轮 dogfood | 第一轮 | 先用**显式模式**跑通，再切 P1 验证零输入 |

§9 的验收判据需同时映射到设计稿 §8.2 的既有场景行（评审要求"每条门禁→场景行"），映射表在 R5 交付。

### 3.7g C1 定稿（人裁 ①：执行边界粒度）——R5 的**可机械改写文本**

裁决记录：`open-decisions.md` OD-9。以下三段是 R5 必须**逐字写入**的内容（不是"大意同步"）。

**① 设计稿 §1.3 会话身份句**（v3.29 重写：**完整原文 + 明确替换范围 + 三段新文**）

> **替换范围**：只替换该条的**第一句 + 第二句**（到"复制到另一会话不构成接管许可"为止）；
> 其后的「绑定记录同时保存……」「能力、传递与恢复方式……」两句**原样保留**。

**原文（完整，无省略）**

> **会话身份（唯一定义）**：采用经目标宿主核实、压缩后保持不变且新会话不同的稳定标识；宿主不能提供时，使用 wf 显式签发、由该会话携带的唯一会话标识。后者是路由标识而非凭据或人批准证明，复制到另一会话不构成接管许可。

**新文（替换上面两句；三个要素缺一不可）**

> **会话身份（唯一定义）**：**自动模式**下采用**以执行边界为粒度**的稳定标识——同一边界内压缩或 agent 重启保持不变，不同边界（终端/进程树）不同；边界由本地事实派生（会话 leader + 进程链），同一宿主进程内的多个聊天**无法区分**，视为同一执行会话（矩阵已声明该限制），可检测的"未登记第二调用者"按机制稿的 C2 分级阻断，仅人调启用入口可登记。**显式 legacy 模式**下仍采用宿主提供/请求携带的会话标识，语义见机制稿 §1.4，退役条件见本方案 §4.1。两种模式的身份**都是路由标识而非凭据或人批准证明**；自动模式的标识由锚点派生（拷文件无效），显式模式的标识复制到另一会话**不构成接管许可**。

**② 设计稿 frontmatter `environment:` 行 + §3 正文「使用环境」句**（两处是同一事实，必须同时改）：

> 原文：`environment: 单人 · 本机 · 单一共享工作区 · 多会话分别绑定、串行写入`

> 新文（frontmatter）：`environment: 单人 · 本机 · 单一共享工作区 · 多执行边界分别绑定、串行写入（同一边界内只有单一绑定）`
>
> 新文（§3 正文）：`**使用环境**：单人、本机、单一共享工作区，**多执行边界**分别绑定、串行写入；**同一边界内只有单一绑定**（一个终端同时只干一个任务，并行请另开终端/窗口）；推送由人执行。`

**③ skills 文案**（`wf-start` / `wf-continue` / `wf-finish` 的"工作习惯"段）加一句：

> 「同一终端同时只推进一个任务；需要并行时另开终端或窗口（同一终端内的第二个 agent 会被阻断，须人 `start` 显式登记后才放行，且此后与前者共享同一会话）。」

**④ 连带核对清单**（R5 交付时逐项打勾）：

- [ ] 设计稿 §1.3 定义句（**仅替换前两句**：边界粒度 + 显式模式分支 + 「路由标识而非凭据」限定，三者齐全）
- [ ] 设计稿 §1.3 后两句（绑定实例标识、能力/恢复出口）**保持不变**
- [ ] 设计稿 frontmatter `environment:` 行
- [ ] 设计稿 **§3 正文「使用环境」句**（与 frontmatter 是同一事实的两份表述，必须同批改）
- [ ] 设计稿 §8.2 场景行（"多会话分别绑定"相关表述）
- [ ] 索引表相关条目
- [ ] 机制稿 §1.4（会话身份与 activation 落点）
- [ ] 实现稿命令表与 §2.2 身份段
- [ ] 三份 skills 的"工作习惯"与"证据文件纪律"段

### 3.7f 待裁与回扫补充（v3.23，修 b#22.6）

**(a) 待裁清单**：C1–C6 中已有三条裁决记录（OD-7 C4、OD-8 C2、OD-9 C1）；其余按「落账 ≠ 已裁」处理。

| 条目 | 为什么需人裁 | 状态 |
|---|---|---|
| **C2**（"复制不构成接管许可"） | 安全承诺的调整方式 | **已裁 2026-11-08：选 C（分级）**，见 `open-decisions.md` OD-8；落账内容见上表 C2 行 |
| ~~C1~~ | 身份粒度（会话 / 执行边界 / 进程） | **已裁 2026-11-08：取 ① 执行边界粒度**，见 `open-decisions.md` OD-9；连带改动见 C1 行与 §3.7g |
| C3 / C5 / C6 | 语义变更但方向明确 | 立项，R5 同批落账 |

**(b) 回扫补充（设计稿侧，此前漏项）**

| 漏项 | 处理 |
|---|---|
| 设计稿 **§5.3 记录分类/写者纪律**：`anchors.json`、`attachments/` 是**新记录类 + 新判定字段**（`owners`/`roots`/`activation_stale`/`instance_expected`/`declared_implementation_cli`） | 按 §0 逐项登记「定义/写者/消费点/失败出口/正反例」——现有运行态清单（活动指针、读取留痕、互斥锁对象、临时缓存）**无一覆盖** |
| 设计稿 §1.3 的**活动指针**（`.wf/.runtime/sessions/<key>.json`）与**附件**（`.wf/.runtime/attachments/<key>.json`）是**两套逐会话运行态文件** | 必须写明**合并**（附件吸收定位缓存）还是**并存**（各司其职），否则实现者会造两套并行状态 |
| O1 对 §5.3「运行态不承载不可重建的唯一事实」的**解释性放宽**（未绑定会话的 `issued_id` 只在 runtime） | 设计稿侧同步该句（C3 只改了机制稿） |

## 4. 请求协议（两模式互斥）

### 4.1 模式

| 请求形态 | 模式 | 身份/启用/校验 |
|---|---|---|
| 含 `session` 对象 | **显式 legacy 模式** | 完全旧语义：身份取 `provider/identity`；`instance_id`、`activation` 从请求读；**`host_id ∈ platforms` 照旧校验**（保住 r90）；不查锚点 |
| 无 `session` 对象 | **自动模式** | 身份来自锚点；`instance_expected`/`activation` 来自 attachments；无 host_id 校验 |

- 同时存在 ⇒ 显式模式（**模式选择，不是字段拼接**；不查锚点、无回退）。
- **定位与退役**：显式模式是"完整 legacy 通道 + 诊断/测试"，**不是自动模式出错后的快捷恢复**。退役条件：`anchors` 成为唯一实际入口、且所有 `provider=host` 绑定的对象进入终态后，降为"仅诊断、不再新建绑定"。

### 4.2 自动模式最小请求

```bash
echo '{"inputs": {"generation": 7}}' | wf.py task-approve --task <id> --decision approve.json --json
```

### 4.2b 命令四分类（v3.5，修 a#6 / b#4）

| 类别 | 命令 | 需要 activation | 参与 roots | 身份解析 |
|---|---|---|---|---|
| **只读诊断** | `status`（含 `--issued <issued_id>`：查旧会话与旧对象；**找不到 ⇒ 空结果 + `facts.found=false`，不报错**） `ready` `inspect` `help` `gate` `definition validate` `version` `spec`（**无 `--file`**） | 否 | 否 | 可解析则记录，不可解析也可运行 |
| **写侧车推业务** | `spec --file`（写本会话读取留痕，参与最终门禁“已读”判定） | **是** | **是** | 必须成功 |
| **写业务** | `task-new` `task-approve` `task-check` `stop` `archive` `bind` `writer` `writer-handover` `dep` `spec-update` `definition` `run` `baseline-apply` `task-knowledge` `review-launch` `review-import` `review-decide`；**其余信封必需命令默认归此类** | 是 | 是 | 必须成功 |
| **reviewer 入口**（单列，v3.19 修 a#18.3） | **`review-context`** | **否** | **否** | **不解析路由身份**：只核任务/轮次/`--as`/材料与报告范围、遵守占位契约即可 |
| **维护/恢复** | `repair`、`install`、`upgrade --apply`、`uninstall`、**`identity-path --set`** | **否** | **否** | **不读信封、不以会话绑定授权**（既有契约：机制稿 §2.1；`bin/repair.py` 也不读信封） |
| **会话建立/启用**（人调入口，单列） | `enable`（`/wf-start` 的启用动作） | **非前置**（首次允许 `activation=null`；它本身就是产生激活的入口） | 是（维护根、清 `activation_stale`、建立会话） | 必须成功 |
| **业务（开工）** | **`task-start`** | **是**（v3.6 纠正：它不是启用入口） | 是 | 必须成功 |

**为什么 `repair` 不能归入业务类**（评审 a#6/b#4 正确）：`repair` 正是“附件/启用状态已损坏”时的恢复入口；
若要求它先有 activation 才能跑，就是自锁。它按机制稿的独立维护写者路径走。

**`spec --file` 身份解析失败时**：按机制稿既有规则处理——只读断言仍可做，但**不给完整读取回执**（侧车不写），
并在 facts 说明“身份未解析，留痕未记录”；不静默写、也不因此阻断只读部分。

**`WF_NOT_ENABLED` 的两种来源必须在 facts 里可区分**（否则统计与 dogfood 观察会混在一起）：

| `facts.reason` | 含义 | 出口 |
|---|---|---|
| `activation_missing` | 附件里没有激活事实（未启用/附件重建后未 start） | 人调 `/wf-start` |
| `activation_stale` | 根集合判定为"同锚新调用者"或 roots 未知 | 人调 `/wf-start`（并展示 `roots` 与 `concurrent_callers`） |

### 4.2c 本方案消费的原因码（v3.8，一次性列清）

| 码 | 状态 | 既有定义位置 |
|---|---|---|
| `WF_IDENTITY_UNRESOLVED` | 既有 | `codes.py`；机制稿 §11.1 |
| `WF_BINDING_MISMATCH` | 既有 | 同上 |
| `WF_GENERATION_STALE` | 既有 | 同上 |
| `WF_NOT_ENABLED` | 既有（本方案细化 `facts.reason`：`activation_missing` / `activation_stale`） | 同上 |
| `WF_HISTORY_UNRESOLVED` | **既有**（`needs_decision`：只读核对 Git/原文，人确认后 repair） | `codes.py:91`；机制稿 §11.1:855；实现方案 :374/:469/:673 已在消费 |
| `WF_ATTACHMENT_MISSING` | **新增**（本方案引入，需按增量码登记：只增不改义） | 本轮随 R3 加入 `codes.py` 与机制稿 §11.1 |
| `facts.reason="concurrent_unregistered_caller"` | 既有码 `WF_IDENTITY_UNRESOLVED` 下的**新 reason 值**（非新码） | **登记位置＝本节（§4.2c）**；另有既有 reason 值 `evidence_unknown`（同为 `WF_IDENTITY_UNRESOLVED`/`WF_HISTORY_UNRESOLVED` 下的值），见 §3.4 伪码 |
| `WF_RECORD_INVALID` / `WF_SEMANTIC_DECISION` / `WF_CAPABILITY_UNAVAILABLE` | 既有 | 同上 |

**唯一需要新增登记的是 `WF_ATTACHMENT_MISSING`**；`WF_HISTORY_UNRESOLVED` 早已在码表内，本方案只是复用。

### 4.3 `generation` 闭环

响应 `facts.generation` 回显（含 `status --short`）；`WF_GENERATION_STALE` 的出口固定为"跑一次只读命令重取代次后重试"。**不自动读最新代次替代请求值。**

---

## 5. 失效矩阵（v3）

| 场景 | 锚点 | 行为 | 静默？ |
|---|---|---|---|
| 终端里跑 agent；**agent 重启** | L1 稳定 | 同一 session，**但 activation 降级** ⇒ 须人重新 start（`root_ref` 已死） | 否 |
| 新终端 / tmux 新 pane | 不同 sid | 不同执行会话 | 否 |
| 终端关闭重开（pty 编号复用） | 新 shell ⇒ 新 sid | 新会话 ⇒ 轮换；**若旧会话仍持写权，须走 §5.5 受控恢复**（不是无条件接续） | 否 |
| **同终端先后两个 agent** | 同 sid | 同一 session；旧根已死 ⇒ activation 降级（须人重新 start） | 否 |
| **同终端并存两个 agent**（A 仍活、B 未登记） | 同 sid | **阻断**（`concurrent_unregistered_caller`）：人调 `start` 显式登记后才放行；登记后仅披露 | 否（**可检测**） |
| 共享宿主 + 两聊天**绑同一对象** | 同锚（**同一 root**） | 合并为同一执行会话，互斥只串行化命令，不区分意图 | **合并且不可检测**（同 root 无信号；`concurrent_callers` 只对**不同 root** 生效） |
| 共享宿主 + 绑不同对象 | 同锚 | 第二个 ⇒ `WF_BINDING_MISMATCH` | 否 |
| **会话 leader 先死**（nohup/后台化），**同一 agent 继续** | L1 不可读，L2 键仍在 | **子场景 A**：L2 路由存在 ⇒ 决策表 #5 命中 ⇒ `adjudicate` 返回 `USE` ⇒ **续接**（`anchor_degraded="l2-only"`，**不产生** `anchor_migrated`）。**子场景 B**：L2 路由丢失/失格 ⇒ miss ⇒ `adjudicate` 返回 `USE` ⇒ **接管孤儿**（`anchor_migrated`）。两者都不满足 ⇒ 阻断（R0 #10 裁决容器 reparent 情形） | 否；**若另有存活且已登记的其他根 ⇒ 按 C2 行 3 阻断**（不做降级）；该路径 reason=`other_root_alive`（`concurrent_unregistered_caller` 只在 hit #1 的 §3.4 分支产生） |
| 每命令新 L1（agent 经执行服务逐命令新建会话） | L1 漂移 | 决策表 #4：**仅 P2 启用时**降级使用（`anchor_degraded=l1-drift`） | **仅在单聊天假设下安全**：该执行服务若被多聊天共享，root 相同 ⇒ 守卫恒真 ⇒ **合并且不可检测**（与共享宿主同列披露） |
| shell 原地 `exec` | **同 sid、同 starttime**（实测） | 无变化 | 否 |
| **setsid 型 agent 重启** | L1、L2 同时漂移 | 新会话 ⇒ 走轮换/接续门禁 | 否 |
| 每命令新会话（`docker exec -t`、沙箱 setsid） | L1 不稳定 | 回查 L1→L2；L2 亦不成立 ⇒ fail loud | 否 |
| CI runner | L2 候选是 init 直子（服务） | 阻断；用显式模式 | 否 |
| **续接时有无关旧根 unverified**（hidepid／异用户／跨 namespace） | L1 命中（hit 场景，`known ∧ alive`） | 该判定**不依赖**旧根证据 ⇒ **只披露** `facts.roots_unverified`，**不阻断**（v3.19） | 否 |
| **旧根 liveness-unknown**（`/proc` 不可读、跨 namespace） | 候选全 miss（与上一行区分：此处**无 L1 命中**，判定必须依赖旧根证据） | `adjudicate()` 返回 `BLOCK(evidence_unknown)`：`WF_HISTORY_UNRESOLVED`，出口＝人核实或 §5.5 | 否 |
| **L2 独用**（leader 先死等） | L1 缺、L2 命中 | 调用 `adjudicate(owners)`（§2.3d）：`USE` ⇒ 续接；否则按其 reason 阻断 | 否 |
| 容器内作为 pid 1 的一次性命令（`docker run …`） | 无 | 阻断，走显式模式 | 否 |
| 沙箱 PID namespace | L1 可用则用 | 否则阻断 | 否 |
| **`{sid}` 退化根**（L2 不可用，root 记成 leader sid） | L1 稳定 | 同终端先后两个 agent ⇒ **同一会话、无降级、无标记**（**仅当**该会话 root 为 `{sid}` 且该 sid 仍是当前调用者的 leader；人直跑终端属此形态，v3.23 收紧） | **是：不可检测**（`{sid}` 条目不做存活判定） |
| macOS | **无 `/proc`**（本方案未实现 `ps` 后端） | 双锚皆不可用 ⇒ `WF_IDENTITY_UNRESOLVED`；首轮**不声明支持**，只能用显式模式 | 否 |
| Windows | 无 POSIX 会话 | **只支持显式模式**（不做半吊子 L2） | 否 |

---

## 6. 其它语义

- **`instance_id`**：漂移对账（附件 vs 绑定，同源写者），不符 ⇒ `WF_BINDING_MISMATCH` + 轻量出口"重附着"。
- **`checkout_id`**：移出 MVP（隔离由 per-root `.runtime` 结构保证）。
- **`host_id`（会话路由）**：**只在显式模式校验**（`host_id ∈ platforms`）；自动模式不使用、不归一（v3.17）。
- **审查参与者身份（v3.18 修正：v3.17 说"没有消费点"是错的）**：设计稿 §6.5 要求"两个与实施 CLI 不同的审查 CLI"，
  实现里 `review.py:281`（`review-context` 取 reviewer 身份）与 `:601`（`review-decide` 取实施 CLI）都读 `host_id`。
  **自动模式不产生 host_id ⇒ 必须给出替代来源，否则审查门禁失效**：

  | 参与者身份 | 来源 | 缺失时 |
  |---|---|---|
  | **reviewer 是谁** | `review-context --as <cli>` **显式声明**；`--as` 必须非空且经 `normalize_agent` 归一（`[a-z][a-z0-9-]*`） | **拒绝**（`WF_IDENTITY_UNRESOLVED`），不产生审查结论 |
  | **实施 CLI 是谁** | **在 `review-launch` 时声明**（写入该轮 `reviews.launches[].implementation_cli`）；显式模式下可由 `host_id` 归一填充；**会话级可选默认值**存 `attachments.declared_implementation_cli`（写者：`review-launch --implementation-cli` 在附件锁内顺带更新；预填：launch 缺少该参数时读它；归一不符 ⇒ 忽略默认值并要求显式声明；**随轮换复制到新会话**——但复制来的只是**预填值**，可能与新对象的实际实施 CLI 不同；若与实际不符，出口＝**重跑 `review-launch --implementation-cli` 覆盖**或 repair（预填值本身不可作为异种判定依据）） | **无实施 CLI ⇒ `review-decide` 拒绝给出 pass**（不得用空集合放行）；补录出口＝**重跑 `review-launch --implementation-cli <cli>`**（同轮次幂等）或 `repair` 补写该轮记录 |

  **两者与会话路由身份彻底分离**：路由身份（`session_key`）决定"谁在写"，参与者身份决定"谁参与了评审"，互不替代。

**写权链**：`review-launch/import/decide` 写 `reviews.*` 属**判定字段**，按机制稿 §5.3 由**入口脚本**在 `writer.json` 代次内写；
因此这三个命令仍是"写业务"类（需 activation + 有效代次），**不因参与者身份改为声明制而免除写权校验**。
- **activation 的强度（B#5，v3.3 收窄）**：
① **仅自动模式**：跨会话冒充经输入通道被堵死（模型无法为别的 session 注入身份）；
② **显式 legacy 模式仍完整接受请求里的身份与 activation**——这是保留兼容通道的既定选择，**不构成新漏洞，但也不能作全局保证**；
③ **同会话自我启用仍是纪律边界**（模型可直接跑 start 路由的同一命令）——与伪造信封同级，不宣称更强。
④ **C2 分级（人裁 C）**：可检测的「未登记第二调用者」**阻断**，只有人调 `start` 能登记；不可检测的（同 root 多聊天）合并并披露——这是本条唯一被明确弱化的部分，已写入矩阵与判据 7。

---

## 7. 数据结构（v3.4 重构：路由与状态分离）

> 第三/四轮评审共同指出：一个会话可对应多个锚点键，而 `roots`/`activation_stale` 存在**每个 anchor 条目**里，
> 于是同一会话有多份状态副本，且写操作只写"本次命中的那个键"——轮换会留下分叉别名，降级会跨键失效。
> v3.4 把**路由**与**状态**彻底分开：锚点只管"从哪个键找到会话"，所有会话状态只有一份。

```text
# 路由（一文件一世界，组原子：整文件 rename）
.wf/.runtime/anchors.json
  {"<anchor_key>": {"owners": ["<session_key>", …], "attached_at": "…",
                     "via": "session|proc", "boot": "<boot_id>"}, …}
  # boot 字段用于 GC：键是哈希、无法反推 boot，故必须在条目里存一份
  # owners：L1 键**必须单主**；L2 键**可多主**（共享同一 agent 进程的多个边界）
  # GC：条目自带 `boot` 字段；与当前 boot 不同的条目在启动时清理（键是哈希，无法从键反推 boot）

# 会话状态（权威、单份）
.wf/.runtime/attachments/<session_key>.json
  {provider, identity:{issued_id}, session_key,
   instance_expected, activation, activation_stale,   # activation = {enabled, start_source, enabled_at}（与显式模式同构）
   declared_implementation_cli: "<cli>" | null,      # 会话级预填；缺省=null（**不得解释成任意 CLI**）
   # 兼容：旧附件缺该字段 ⇒ 读作 null；写者＝review-launch（附件锁内）；轮换/恢复/repair 均保留
   attached_l1:{sid, sid_start, boot} | null, attached_root:{kind,pid,start,boot} | {kind,sid,sid_start,boot},
   roots: [...], session_created_at, rotation_id,
   superseded_by?: <new session_key>   # 可选、仅审计；缺失无害，不参与任何判定}

# Git（历史/绑定，不变）
.wf/session-bindings/<session_key>.json  {schema_version, provider:"wf", identity:{issued_id}, instance_id, object, bound_at}
.wf/writer.json                           （不变）
```

**为什么这样分**

| 关注点 | 归属 | 理由 |
|---|---|---|
| 键 → 会话 | `anchors.json` | 纯路由；组更新（轮换要把**该会话的全部键**一起改指）必须原子 ⇒ 单文件 rename |
| 谁在用过这个会话（`roots`） | `attachments/<key>` | "谁在用这个**执行会话**"是会话属性，不是锚点属性 |
| 是否需重新启用（`activation_stale`） | 同上 | 会话属性；否则跨键漂移后降级失效 |
| 对账值（`instance_expected`） | 同上 | 会话属性 |

**轮换的组更新（修 a#1）**：锁内 `new = uuid4()` → 写 `attachments[new]`（`roots` 沿用、`activation` 由本次 start 形成、`stale=false`）→
把 `anchors.json` 中**所有 `session_key == S` 的键**改为 `new_key` → 单次 rename 提交。
**失败**：rename 未发生 ⇒ 旧 `anchors.json` 原样（无分叉）；`attachments[new]` 成为孤儿（可 GC）。
**重复 start**：命中即复用 —— 只更新 `roots`（**合并**已有存活根，不重置），写 `last_seen`。

## 8. 实施批次

| 批 | 内容 | 门 |
|---|---|---|
| **R0**（强制门） | 11 个环境（**经 agent 命令路径**为主、终端直跑为对照）跑锚点探针 → `r0-results.md` → 结论表写进设计稿 | **R0 未完成不得进 R1**；可选类不可达记"未验证⇒阻断"；任一必测环境不满足 ⇒ 列入不支持清单 |
| R1 | `session.py`：`candidates()`/`resolve()` + 判据分离 + 单测 | R0 通过 |
| R2 | `anchors`/`attachments` + start 建立/轮换/重附着/迁移 + roots 判定与 `activation_stale` + 附件显式恢复 | **事务用例 + roots 行为用例**（判据 4/7/8/8b/8c + `adjudicate()` 的每个 verdict（USE / NEW / 各 BLOCK reason）+ 接管孤儿与加入现存共享的区分） |
| R3 | `cli` 两模式判定 + instance/activation/host_id 归位 + `--envelope-last` 退役 | 回归绿 |
| R4 | 新用例（§9）+ 既有 129 项按显式模式保留 | 全绿 |
| R5 | 三稿 + skills 文案 | 0 problem |
| R6 | 收口 + dogfood 重跑清单 | — |

---

## 8b. 判定覆盖：组合穷举 + 不变量（v3.17 新增，修 b#17.11）

用例驱动会漏分支。R2 之前必须交付**组合穷举表**或**不变量测试**（至少其一）。

| 维度 | 取值 |
|---|---|
| `C`（候选集合） | ∅ / 1 / 多个 |
| 每个候选 `l1_state` | match / gone / unverified / null(→gone) |
| 每个候选 `root_state`（other_roots） | 全 dead / 有 alive / 有 unverified / 混合 |
| `path` | P1 / P2 / P3 |
| 调用点 | hit(#1/#3/#4/#5) / miss(迁移) / 轮换 / 附件恢复 |

**不变量（属性测试，与实现无关）**

| # | 适用入口（**必须限定**） | 断言 |
|---|---|---|
| I1 | **仅** `adjudicate()` 的孤儿/接管裁决（P1/P3，P2 的放宽见 §2.3d 读法分区） | 无 `gone` 证据 ⇒ 永不 `USE` |
| I2 | `adjudicate()` 的 `USE` 候选（任何 path，含 P2） | 存在 `unverified`（且该裁决依赖旧根证据）⇒ 不得 `USE` |
| I3 | 全会话 | **经 L1 键可区分**的两个边界永不静默合并（同 L1 键两个 owner ⇒ 报损坏）；矩阵已披露的三类**不可检测**合并不在断言范围 |
| I4 | `adjudicate()` 返回 `BLOCK`，**以及 §3.4 的两个阻断分支**（`evidence_unknown` / `concurrent_unregistered_caller`） | 不改变 roots / activation；**例外**：`WF_NOT_ENABLED` 的 stale 分支必须持久化 `activation_stale` 并登记当前 root |
| I5 | 全会话（每次读附件） | `SHA256(C({provider, identity})) == session_key` 恒成立 |
| I6 | **锚点登记/轮换/迁移**（写 `anchors.json` 的动作） | 每个 L1 键的 `owners` 长度 ≤ 1；L2 键可多主且**只追加不覆盖** |
| I7 | **轮换提交后** | 不存在「旧会话仍被任何路由键指向」的条目；`superseded_by` 只作审计 |

## 8c. 交付状态（2026-11-08 R6 收口）

| 项 | 状态 | 交付点 | 验收 |
|---|---|---|---|
| `session.py` 锚点与 `adjudicate()` | **已实现** | R1 | 单测 32 项；`test_wflib_session.py` |
| `identity_store.py`（routes/attachments/roots/五态/迁移） | **已实现** | R2 | 单测 19 项；`test_identity_store.py` |
| CLI 自动模式（`explicit_session`/`_auto_resolve`/建立会话/roots 维护） | **已实现** | R3/R4 | `repro/auto-identity-zero-input.py`、`repro/auto-identity-gates.py` |
| 三稿与 skills 落账（C1/C3/C4/C5 文本） | **已同步** | R5 | `validate-wf-design.py` 通过 |
| `repair --mark-root-gone` | **未实现**（出口已在文档与错误码里声明） | 后续 | R6 未接线 |
| `identity-path --set`（维护类命令） | **未实现**（配置键与语义已定） | 后续 | — |
| C6 审查身份协议（`--as` / `--implementation-cli`） | **未实现** | 后续 | 见 `review-identity-protocol.md` |
| R0 结论表 | **已完成** | R0 | `r0-results.md` §九 |

> 统计：R1–R5 交付 3 个模块/接线 + 2 条 repro + 7 处文档/技能落账；**41 项单测 + 131 项全量全绿**。
> 仍未实现的三项（`mark-root-gone`、`identity-path --set`、C6）都已有明确的错误码/协议/验收，不阻塞 dogfood。

## 9. 验收判据

1. 安装后人不写任何 JSON；终端里 `/wf-start` 跑通；
2. 双终端两会话，仅一个持写权；
3. 同会话多次调用（中间夹 shell）同键；
4. **agent 重启 ⇒ 同会话但 activation 降级，须人重新 start**（例外：`root_ref` 退化为 `{sid}` 时根是 leader，agent 重启不换根 ⇒ 不触发降级；**该形态的归属由 R0-A2 结论表声明**：人直调终端、init 直子的单聊天守护都可能落此形态）；
5. 终端关闭重开（pty 编号复用）⇒ 新会话，**不继承 activation/绑定**；旧会话仍持写权时走 §5.5；
6. 每命令新会话 ⇒ L2 兜底或 fail loud，不误认连续；
7. **同锚同对象**：①**未登记的第二 root**（可检测）⇒ **阻断** `concurrent_unregistered_caller`，人调 `start` 登记后放行；②**已登记多 root** ⇒ 正常推进 + `facts.concurrent_callers`；③**同一 root 多聊天**（不可检测）⇒ 合并且无标记（如实披露）；同锚不同对象 ⇒ 阻断；
7a'. **C2 分级的死锁检查**：人调 `start` 登记第二 root 之后，两个调用者**都能**正常推进（不得再次阻断）；
7b. **同一 agent、leader 先死**：**子场景 A**（L2 路由仍在）⇒ 续接并 `anchor_degraded="l2-only"`，**不产生** `anchor_migrated`；**子场景 B**（L2 路由丢失/失格）⇒ 接管孤儿并 `facts.anchor_migrated=true`；两者都不满足 ⇒ 阻断；
7c. **每命令新 L1** ⇒ **仅在 `identity.path=P2` 已启用时**单根降级使用（`anchor_degraded=l1-drift`）；P1/P3 或 P2 未启用 ⇒ 阻断；多根 ⇒ 阻断；
7d. **降级不可被只读调用洗掉**：`WF_NOT_ENABLED` 之后先跑一次 `status`，再跑业务命令仍为 `WF_NOT_ENABLED`；
7e. **轮换前置**：归档已落盘但旧会话仍持写权时，start **不轮换**，先走 §5.4 释放；
8. **同终端并存**：未登记的第二个 root ⇒ **阻断**（判据 7①）；已登记的多 root ⇒ `facts.concurrent_callers` 标记（不阻断）；同 root 多聊天 ⇒ **无标记**（不可检测）；
8b. **`roots` 为空或条目损坏 ⇒ 视同未知态 ⇒ `activation_stale` ⇒ `WF_NOT_ENABLED`**（不得当作首调用者继承激活；无 TTL 机制）；
8c. `roots` 维护在**该会话附件锁**内完成（不取 `.wf-lock`）：**两个已登记的调用者**并发调用后集合同时含两个根（无一被覆盖），且与写权持锁互不阻塞；未登记的第二个调用者按 C2 阻断、**不产生 upsert**（判据 7①）；
9. 同终端完成 T 后 ⇒ start **一次**完成轮换 + 启用，旧绑定保留；轮换后仍可用 `wf.py status --issued <issued_id> --json` 只读查看旧会话与旧对象结果（v3.17 补）；
10. anchors 丢失 ⇒ 新会话仍过 writer/WIP/handover 三关；
11. attachments 丢失 ⇒ `WF_ATTACHMENT_MISSING` 或 `WF_NOT_ENABLED`，不自动补；
12. 自动模式带 `generation` 可全程跑通；显式模式旧语义回归绿；
13. 释放再取得后旧代次 ⇒ `WF_GENERATION_STALE`；
14. clone 只带历史，不继承 activation/锚点；
15. **机械可识别的不合格必须阻断**（候选集空、L1 单主破坏、owners 空/损坏、`unverified` 证据）；**未通过 R0 的环境不得被声明为支持**——这是发布声明纪律，不是运行时环境识别能力；无法识别的部署前提按 §2.4c 的"部署前提"类处理（文档声明 + 使用约定），**不要求运行时自动识别**。
15b. **P2 默认关闭**：未显式启用时，P2 形态**在能识别的前提下**报 `WF_IDENTITY_UNRESOLVED`（如 `identity.path` 为 P1 且出现 L1 漂移）；若某部署形态本身不可识别（共享执行服务），按"部署前提"类声明，不做运行时区分。
15c. **迁移后第一条业务命令不被降级打回**：迁移动作同批 upsert 新 root + 清 stale；
15d. **`/proc` 不可读 ⇒ unverified**：不剪枝、**不当作已死**；**所有放行判定（#4/#5 复用、迁移、轮换）一律阻断并报 `facts.evidence_unknown`**；仅披露类 facts（`concurrent_callers`）不因此产生误报。
15e. **`repair` 在附件损坏时仍可运行**（维护类，不需 activation、不参与 roots）；
15f. **实施 CLI 实质变更 ⇒ 同批 `verdict` 改 `invalidated`**，`final_gate` 拒绝该结论；重跑 `review-decide` 后才可恢复 pass；
15g. **附件整体缺失 + 候选唯一 ⇒ `start` 可越过并重建 S2**（S3/S4 的终态恢复同属该规则，R2 用例覆盖）；**多候选 ⇒ 不越过**（人指认）；**根不可读（附件完好）⇒ 不越过**（走 `mark-root-gone`）；
15h. **`status --issued` 对未知 `issued_id` 返回空结果**（`facts.found=false`），不报错。

---

## 9b. 使用观察项（v3.17 新增：这些是"已知代价"，不是缺陷，但必须被度量）

| # | 观察项 | 为什么 |
|---|---|---|
| O1 | **runtime 误清理的恢复成本**：`git clean -xdf` / 临时目录工具抹掉 `.wf/.runtime/` 后，所有在途会话需重新 `start` + 受控恢复 | `activation_stale` 存在 gitignore 运行态；设计稿 §5.3 要求"运行态不承载不可重建的唯一事实"——它能重建（逐会话人确认），但代价要记录 |
| O2 | **`identity-path --set` 的切换成本**：一次切换使 `anchors.json` 整体失效，全部在途会话孤儿化，逐个走 §5.5 | 单人用户一次配置变更的代价 |
| O3 | **#5 收紧的合法续接被挡频率** | `\|C\|>1 ∧ \|U\|==1` 不再放行（§2.3d 行为变化声明） |
| O4 | **A2 形态（多聊天同守护进程）落入"仅显式模式"的比例** | 直接决定自动模式的实际覆盖面（R0 主轴） |

## 10. 仍待定（需人裁或需 R0 数据）

1. ~~R0 是否要做~~（**已裁 2026-11-07：R0 是强制门**，实现前必须跑完 11 个环境并把结论写进设计稿；
   不允许以"只保证普通终端"替代；范围收缩必须由 R0 数据支撑）。
2. **CI 与共享服务的支持边界**：仍取"服务进程 = 阻断"（保守）；若接受"一个 CI job = 一个执行会话"，需可执行判定（暂无）。
2b. ~~共享守护进程是否只允许显式模式~~（**已由 R0 回答**：zcode 两聊天 L1 可分 ⇒ **不需要**；仅把"宿主须为每聊天派生独立 shell/pty"写成部署前提）。
3. **`systemd-run`**：继承发起终端 sid ⇒ 与发起者同锚，是否可接受？
4. ~~`root_ref` 单字段无法表达并存~~（**已修 2026-11-07：改 `roots[]` 集合 + TTL + `activation_stale`**，见 §3.4）；
4b. **显式模式的退役时点**（§4.1 给了条件，但需人裁）。
5. ~~本机 `host-map.json`~~（**已删除**：自动模式不产生 host_id，§6 明确不设该文件）。
6. ~~同锚同对象合并~~（**已裁 2026-11-07：取披露 + facts 标记**，不在保护范围，写入矩阵）。
