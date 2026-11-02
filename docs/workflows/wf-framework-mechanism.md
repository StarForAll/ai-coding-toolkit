---
doc: wf 独立框架机制设计
scope: 记录 schema、判定编码、状态机、持久化与恢复算法、交付及验收映射
audience: 框架实现者与机制审查者
status: 首版机制设计已人工审查通过（2026-11-02）；不构成实现验收
baseline: 2026-11-01 人工确认的框架设计及 charter
---

# wf 独立框架机制设计

## 0. 效力与阅读方式

本文件遵循 [wf 框架基调与边界](./wf-framework-charter.md)（charter）及 [wf 框架设计](./wf-framework-design.md)（设计稿）。charter 定义目标与边界，设计稿定义行为与验收，本文件将这些行为编码为记录、状态机和算法。冲突按 charter T1 与设计稿 §1.5 交人裁决，本文件不自行改变上位规则。本文是 authoring 文档，不进入目标项目发行清单。

下文“设计稿 §x.y”与“本文 §x.y”分别指两份文档；charter 使用 T 编号。上位规则的定义位置由 [定义索引](./wf-framework-design.index.md) 定位，借鉴边界见 [来源说明](./wf-framework-design.sources.md)。旧 `workflow-design.md`、`workflow-implementation.md` 与旧依赖机制说明属于 Trellis 内嵌模块，不是本框架的存储或命令规范。

本文给出 schema 与算法的唯一编码位置；实现方案负责模块拆分、完整目录布局、CLI 参数和发行物组装。设计稿已确定的路径和委托本文确定的发行清单定位保留在本文。文中“操作名”是机制标识，不自动新增公开子命令或 skill。

### 0.1 输入版本与验证边界

输入为 2026-11-01 的工作树定稿版本及 2026-11-02 用户明确批准的首次基线语义修订；本日同批人裁“必要验证由各任务步骤 verifications 承载”并同步设计稿 §5.7 措辞。基础提交为 `15318f56a9e1a2eba9772b887755449aeb7abb88`，其后存在人工确认状态与上述获批规则的未提交更新，故以文件内容摘要固定本稿输入。

| 文件 | SHA-256 |
|---|---|
| wf-framework-design.md | f41173d9c174ab787bf65504c9d97bade41c00d07109eec7e5323650acaa9b7a |
| wf-framework-charter.md | 8b816ee4cb1fad0341ad7b3806748622c6c66f26040ec894da49d43d2ba33c16 |
| wf-framework-design.index.md | 1473942770bc336c0b592324b495622ce10208fcde6184bcb8cd2f9e80f1bdb2 |
| wf-framework-design.sources.md | 47484498fc23c6292c394fa1b4a7fa0b9eac5a9ca5c9aeb739916b1c16e4a25b |

这些摘要只绑定审查输入，不是目标项目字段，也不要求把文档自身哈希写回自身。上位文件变化后按改变的句子及其中每个义务子句，分别核对输入、写入时点、记录载体、消费者与失败出口，并在任务修订记录列出对应关系，再评估本稿有效性；不以同一主题的一处说明代替整句义务落实。

本文的算法、格式和缺省值已于 2026-11-02 经人工审查通过，作为后续实现方案的机制基线。结构检查和原语探针不替代设计稿 §8.2 的三夹具、故障注入、宿主核实及 dogfood；实际运行结果由实现阶段记录。

### 0.2 机制登记约定

本文各 schema 表是字段定义登记，各状态/算法节登记写者、消费者和失败出口，本文 §12 将其映射到设计稿验收场景与交付轮次。每个枚举及结构只在所属 schema 一处定义合法域，其他章节引用其定义，不另设同名取值表；新增字段必须同时出现在所属 schema 与一个真实消费算法中；仅为展示方便的派生值不落成第二事实源。只读摘要不成为新的生命周期记录。

authoring 机检统一使用 `scripts/validate-wf-design.py`：保留上位七项检查和阈值，同时检查本稿带所有者的章节引用、本文 §12.2 与本文 §12.3 和设计稿 §8.2 的场景名双向对应，以及本文 §0.1 四份输入的实际字节摘要。摘要不符时先核条款影响，再更新本稿及摘要；机检不自动刷新摘要来消除失败，也不以场景名全覆盖证明语义正确。

下表只是修订重点追踪表，列出已确认易漏的判定域，不是全量字段清单，也不证明表外没有遗漏。字段合法域、写者与消费关系以所属 schema 和算法为准；本次变更的字段和上位义务须在任务修订记录逐项列出并反查，机检只核其中可机械判断的关系。上位修改按句/义务子句核对，范围内复审还须从“至少包含/全部/必须”逐项展开，不能仅沿表中主题阅读。修订与复审的固定反查动作：对每个 schema 表的键名核对「该键有消费者与失败出口」，新增键须同批出现在所属 schema 与一个真实消费算法中（登记纪律的既有条款），逐键反查作为复审的固定步骤而非依赖发现驱动追加。authoring 机检的扩展项按本仓库复审记录（findings R2/R6/R7/R7a：字段登记生成、档位一致性、表间引用、断言同源，含字段名级匹配键的逐键定义检查）逐项落地；落地前，同类「一处已改另一处未同步」缺陷由上述固定反查动作与人工复审兜底，不降低本稿对自身的登记纪律要求。

| 判定域或上位完整性义务 | 定义/生产 | 必须反查的消费与失败出口 |
|---|---|---|
| required id/mode/applies/due、P、回执 | 本文 §11.2、§11.3 的固定分派/投影；发行声明、入口结果 | 开工/Check/Finish 按声明算缺项；未知键或缺证据拒绝 |
| PRD 验收/验证 id 与人判 | 本文 §2.3 的批准块 | 本文 §3.5 按规划全集核 commands/acceptance_results，缺项不 pass |
| independent_resume | 本文 §1.3、§7.4 的实例终止写者 | 本文 §6.1、§4.2、§2.3 的候选/取得/开工/启动核验，非法直接 task 绑定拒绝 |
| 规则版本、支持版本、模板使用位点 | 本文 §10.2 的发行 schema/摘要/模板登记 | 安装/升级自检和本文 §11.2、§3.5，未知/悬空/失配阻断相关判断 |
| 路由输出四要素（设计稿 §4.1） | 本文 §11.1 的 position/next/tier/exit | 所有路由出口含实际位置、下一步、结论、出口；未知位置明示，不省字段 |
| 巡检四类对象（设计稿 §5.4） | 本文 §8.5 的一次遍历与四类断言 | 归档引用/终态/id/知识各出结果，不能以知识报告替代全巡检 |
| 首次基线与上位裁决 | 设计稿 §4.2（2026-11-02 人裁）；本文 §2.3 | 外部变更核对从首次基线，锚点失效交人，不以工程理由覆盖上位 |
| Plan 期人判问答（execution.human_decisions 的 plan-q id） | 本文 §1.3、§2.3 | 固定格式（`plan-q-<n>：` 起始行+推荐答案）提取问题全集并由批准声明承载；开工核验（全集均有对应 Decision 且当前有效批准存在，仅按 plan-q id 判定、不含 debug-ruling 裁定条目）、task.plan-approved 证据（含 human_decisions 覆盖核对）、WF_SEMANTIC_DECISION |
| 复盘触发事实（rework/review_fail/debug_repeat）与检查历史（check_history） | 本文 §8.1（debug_repeat 机械检测口径）、本文 §11.2（触发集合派生重建、强制裁定与 Execute 期兜底）、本文 §1.3（check_history 字段、debug-ruling 裁定条目、debug_declarations 声明条目 schema 与双源合并口径定义）、本文 §3.5（check_history 保存协议） | 归档前 retrospective-done 证据核对：机械检测已产生的各整数倍均有对应 debug-ruling 裁定条目（无裁定的新倍数 → WF_SEMANTIC_DECISION 阻断归档），debug_repeat 触发核 debug-ruling 条目及其证据引用的调试证据（不限定 check_history 条目），重复调试计数按本文 §1.3 双源合并口径重建、触发集合为按本文 §11.2 派生的视图；触发事实不可重建时给待核对出口，不倒推为无触发 |
| 检查锚点（check_anchor）与回执内容/规则分类 | 本文 §3.2（唯一编码：`check_anchor=H("wf-check-anchor-v1", C({plan_version, entry_snapshot_digest, touch_paths_digest, content_digest, acceptance_digest, spec_versions, baseline_digest, config_digest, workflow_snapshot_digest}))`，plan_version/acceptance_digest 经本文 §1.3 的等价链归一；`paths_digest=H("wf-check-paths-v1", C(paths))`）、本文 §11.2（内容/规则两类回执的可核判据分类、匹配键与锚点公式） | 本文 §3.5 检查记录 anchor、本文 §9.1 审查 check-anchor、本文 §11.2 回执 P 按本文 §3.2 取值；回执选择规则类按 id/rule_version/occurrence、内容类按 id/occurrence（不因规则字节变化失配）；机械修订经等价链归一不重复批准（本文 §1.3）；键值缺失即未满足，不以 null 摘要补齐 |

## 1. 通用编码与记录结构

### 1.1 基本类型

目标脚本最低 Python 版本拟定为 3.11；只使用标准库。首版锁支持范围为 Linux、本机普通文件系统、单仓库工作树，需通过本文 §4 的能力检查。其他系统或远程/同步文件系统未列为支持，不以无锁退化补位。后续扩展支持范围须给出等效锁与恢复验收，不改变单机边界。

| 类型 | 编码与合法性 | 消费方式 |
|---|---|---|
| `Id` | 小写 UUID4 的 32 位十六进制；任务 id 为 `YYYY-<uuid>`，年份取创建时 UTC 年；其他 id 不加年份 | 创建/改名的目录防撞按本文 §5.2；id 不因改名/移动改变 |
| `SessionKey` | `SHA256(C({provider, identity}))`，provider/identity 取值与传递协议唯一见本文 §1.4 | 稳定绑定文件名；身份原值与实例标识另作比对，不当凭据 |
| `Time` | UTC 的 `YYYY-MM-DDTHH:MM:SS.ffffffZ`；核实日期单用 `YYYY-MM-DD` | 展示、归档排序、周期计算；不据时间接管写权 |
| `Digest` | `sha256:` 加 64 位小写十六进制 | 内容等同性检测，不作批准或身份认证 |
| `GitOid` | Git 实际返回的完整对象 id；不固定为 40 位 | 只读可达性与归属检查；缺 HEAD 的安装标记可为 null |
| `RepoPath` | 仓库相对、以 `/` 分段的 Unicode 路径，区分大小写，保留 Unicode 原码点 | 本文 §3 统一安全判定；不作 shell 字符串插值 |
| `Decision` | `{source, at, subject, object_digest, choice, reason}`；source 记实际人答复来源的可核对定位 | 入口记录人的决定；脚本核对象/版本，不判断答复真伪 |
| `ObjectRef` | `{kind, id}`；kind 为 task/run/preparation/writer/installation/config/spec | 定位唯一记录；不是授权可写范围 |

`C(x)` 为 UTF-8 编码的规范 JSON：键按 Unicode 顺序排序，分隔符为 `,`、`:`，不转义非 ASCII，不加末尾换行。已知数字字段均为整数（布尔不算整数）；哈希输入中无浮点数。集合型数组先按元素规范 JSON 的 UTF-8 字节序排序去重（另在所属 schema 声明排序键的从其声明，如本文 §10.2），顺序步骤数组保留顺序。文件字节哈希直接取原始字节，不规范化换行。`H(domain, payload)` 返回 `sha256:` 加 `SHA256(UTF8(domain) + 零字节 + payload)` 的十六进制值；SessionKey 单独取表中哈希的无前缀十六进制，适合作文件名。

**结构逐键定义硬规则**：任何作为哈希输入、匹配键或清单成员的结构，必须在所属 schema 处逐键给出名称与取值域（本表 C/H、本文 §11.2 的 P 与本文 §3.2 的 check_anchor 均为该规则的实例）；新增 `H("wf-…"` 哈希域时，域名必须同时有对应的逐键定义段，authoring 机检核对该对应关系。散文式列举（“某某等组成某结构”）不构成定义。

记录以 UTF-8 JSON 对象存储，读取拒绝重复键、NaN/Infinity 和语法损坏。未知字段保留原值，整记录写回只修改本操作拥有的键。未知 schema 版本或未知枚举值仅阻断依赖其语义的操作；诊断与保留数据卸载仍可达。缺字段不自动补批准、pass、空引用或终态。第一版新建记录显式写必需的空数组和 null；旧记录的兼容缺省由对应 schema 版本表解释，不能用新建缺省伪造旧事实。

### 1.2 公共字段与写入标记

任务、绑定、实例、准备、writer 和安装登记的可变 JSON 记录均有下列包络；项目配置与 spec 使用各自 schema，不强加任务状态字段。

| 字段 | 类型/初值 | 写者、消费与失败 |
|---|---|---|
| `schema_version` | 正整数，首版 1 | 入口创建；读取按本类型版本解释，未知按局部不可用 |
| `id` | Id 或固定对象键（writer 为 `writer`） | 创建后稳定；引用/幂等定位，碰撞拒绝 |
| `revision` | 非负整数，初值 0 | 每次有效记录更新加一；并发候选使用旧 revision 比较 |
| `created_at`、`updated_at` | Time | 入口写；排序与诊断，不承担授权 |
| `write_mark` | null 或 `{operation, owner, generation, before_head, changed_fields, action_id}` | 入口在同次写入登记；恢复核对实际字段/Git，null 只用于尚未完成创建的受控窗口 |
| `action` | null 或本文 §5.1 的动作描述 | 只保存当前/最近控制动作；恢复读取，完成后的业务状态仍由所属记录负责 |

每个动作的 `owner` 为 `{kind: session/maintenance, id, scope_ref}`：kind 与 id 同源于本文 §1.4 的 writer.holder（会话取 session key、维护取维护操作标识），scope_ref 为该动作的授权范围引用——会话类为绑定对象 id 或已授权准备范围的引用，维护类为本次维护操作标识或预览摘要定位；例如会话类 owner 取值 `{kind: session, id: <session-key>, scope_ref: <task-id>}`，维护类取值 `{kind: maintenance, id: <维护操作标识>, scope_ref: <预览登记的维护操作标识>}`。首次安装还没有 HEAD 或项目标识时，使用 writer 固定对象与安装操作 id；不提前伪造初始化任务的 `project_id`。更新未知字段时必须原样保留；例如仅暂停任务仍保存未知的附加元数据，这不算依赖该元数据作判定。

### 1.3 任务记录

每任务唯一记录加其 PRD/design/implement 内容文件构成任务产物；目标目录布局交实现方案，稳定 id 查找覆盖活动与 `archive/{YYYY-MM}/`。引用不会绑定可变目录名。

| 字段组 | 类型与约束 | 写者/主要消费者 |
|---|---|---|
| `title`、`kind` | 非空名称；kind 为 ordinary/initialize/bootstrap | 创建入口；路由、自举；名称可变而 id 不变 |
| `status`、`phase` | not_started/in_progress/archived；plan/execute/check/finish | 通用状态入口；本文 §2 |
| `paused`、`suspended` | 布尔，初值 false | 暂停/复评入口；执行候选与正常完成 |
| `terminal`、`archived_at` | null 或 normal/abnormal；null 或 Time | 归档入口；依赖、统计、恢复 |
| `prerequisites` | 去重 task id 数组，显式空允许 | 建任务/建删边/返工入口；唯一前置集合 |
| `rework_of`、`successor_id` | task id 或 null | 返工/替换入口；反向集合及继承检查 |
| `run_id`、`independent_resume` | run id 或 null；null 或 `{decision, termination_action}` | 实例创建/终止入口；归属与保留任务恢复 |
| `plan` | `{version, artifacts, touch_paths, acceptance_digest, verifications, complexity, complexity_reasons, tdd, approval, equivalences}` | continue 从本文 §2.3 的 PRD 块提取并记录批准快照；开工、范围、检查/审查 |
| `entry_snapshot` | null 或本文 §2.3 的开工核对快照 | 首次开工/再入 Execute 由入口保存；范围/检查/Finish 消费，批准时不写 |
| `baseline_head` | GitOid 或 null | 首次开工固定，按 2026-11-02 人裁同步的设计稿 §4.2；恢复与外部提交扫描 |
| `attribution` | `{decisions: [{commit, decision}], inherited: [{source_task, commits, paths, decision}]}` | 归属/替换入口；本文 §3.3 |
| `check` | null 或本文 §3.5 的当前检查记录 | Check 入口；Finish、审查锚点等当前锚点核对 |
| `check_history` | 按 check.id 保存的历次检查记录数组，显式空与缺失不同 | Check 入口在写入新结果前移入旧记录（含 failed/not_run/中断及带 invalidation 的失效 pass 的完整历史）；复盘触发计数、检查历史消费从该字段读取 |
| `execution` | `{required_steps, actions, human_decisions, debug_declarations}`，四者初值为空数组 | 通用入口记录任务内实际步骤/动作结果、人答复与重复调试声明；required 门禁、实例推进与复盘计数/机械检测消费 |
| `reviews` | `{last_round, attempts, launches, imported, dispositions, result}` | 审查发起/导入/决策入口；本文 §9 |
| `curation` | `[{path, digest, purpose, selected_at, released}]`；显式空与缺失不同 | 策展入口；加载/统计/依赖解除 |
| `knowledge`、`retrospective` | null 或 `{decision, changes, evidence}`；null 或 `{required, evidence, conclusion}` | 知识处置/复盘入口；最终门禁 |
| `handoff` | `{goal, decisions, progress, next, pending, ruled_out, verification_refs, wip}` | 进度内容可由 AI 起草；WIP 判定字段由入口写，接续消费 |
| `disposition` | null 或 `{kind, decision, changes, targets, pending}` | 替换/放弃入口；异常退出与后继引用 |
| `commit_grants`、`finish_decision` | Decision 数组（subject 包含明确路径/目的）；null 或 Decision | 人授权后入口记载；提交/正常归档 |

`plan.version` 的取值与提取顺序统一在本文 §2.3 定义。`artifacts` 保存路径、摘要和任务内可读快照引用；仅存哈希不能恢复批准内容。`complexity` 取 light/complex，`complexity_reasons` 逐项保存设计稿 §4.3 四个分级条件的 true/false/unknown 和事实；任一 true 或 unknown 提出 complex，由人确认；降级时该字段追加降级条目 `{downgrade: true, reason, evidence}`——reason 为人给的降级理由，evidence 为缩范围/拆分/降低契约影响的事实依据，与重新分级同批人批（对齐设计稿 §4.3“降级由人留理由，且只在任务本身确实变轻时成立”）。文件数/行数只作提醒。`tdd` 为布尔，取任务覆盖值或项目缺省并与分级同批批准。`approval` 初值 null，记录 Decision。`equivalences` 保存 `{old_version, new_version, reason, source}` 的机械修订衔接，每条衔接以 Decision 承载（subject 记新旧版本与两端摘要，choice 固定为“机械修订”，reason 记依据、source 记来源），构成**等价链**：入口核当前 plan.version 可沿链回溯到既有批准版本、每条衔接有有效 Decision 且两端规范化 touch_paths 与验收摘要相等，即机械同义成立；锚点归一与回执复用核该 Decision 当前有效（未被后续修订作废），脚本仍不判语义、只核“有 Decision 且链完整”。等价链同时被 check_anchor（本文 §3.2 的 plan_version/acceptance_digest 经链归一）与本文 §11.2 的内容类回执 P（plan_version 归一，见该节）消费——经等价链归一的旧 completed 回执仍可复用，语义变化仍须重新人批准，脚本只能核衔接留痕（对齐设计稿 §4.2“只修排版……不重复问人”）。复杂任务三件套均参与版本，轻量只需 PRD。

`curation.released` 为 null 或 `{decision, old_path, old_digest, replacement}`。解除保留历史选用事实，但从当前依赖集合排除；它不是把引用条目删除。已归档任务不常规更新。`reviews` 的初始值为轮号 0、空数组及 null 结果；其 schema 在本文 §9 细化。

execution.required_steps 保存本文 §11.2 定义的执行回执，字段为 `{id, rule_version, mode, occurrence, result, anchor, completed_at, checked_at, evidence_refs, skip_basis}`；它只记录执行事实，不决定应执行的步骤集合。execution.actions 每项为 `{id, result, output_refs, verification_refs, decision_refs}`，result 为 satisfied/skipped/pending/failed；execution.debug_declarations 为 Execute 期重复调试声明的具名条目数组（初值显式空数组），每项为 `{verification_id, counted, evidence_refs, dedupe_refs}`：verification_id 为其声明的失败验证声明 id；counted 为入口核定的计入次数（正整数）；evidence_refs 为支撑证据引用（check_history 条目、execution.actions 的 failed 结果及其 output_refs/verification_refs、handoff 材料的稳定引用）；dedupe_refs 为 `[{check_id}]` 数组，列出该声明中判定为与已入 check_history 的失败为同一事件所对应的历史检查条目（check_id 即 check_history 的唯一条目定位，足以唯一标识一条历史失败，不再另设命令摘要键；命令级溯源由该 check_id 对应 check_history 条目 command 项的 invocation 查得）。写者为处理 Execute 期声明/裁定的入口（continue/finish）；消费者为本文 §8.1 的机械检测与本文 §11.2 的复盘门禁（合并累计按本字段的 counted 与 dedupe_refs 求和）；失败出口为约束违反时的 WF_SEMANTIC_DECISION（dedupe 重复/超限）与 WF_RECORD_INVALID（求和越界）。debug-ruling 裁定条目与其对应的 debug_declarations 声明条目在裁定动作内同批写入，前者记结论、后者记计数事实。human_decisions 为带人判点 id 的 Decision 数组，人判点 id 来源为三类：工作流定义的 human_points id、普通任务 Plan 期自编号 `plan-q-<n>`、复盘待决项裁定自编号 `debug-ruling-<verification_id>-<multiple>`。普通任务的待决问题在 PRD 正文以 `plan-q-<n>：` 起始行的固定格式编号（n 为任务内正整数，从 1 递增、不重复不跳跃），同行或紧邻行附推荐答案；批准/开工入口按该固定模式提取问题全集——排除面与本文 §2.3、§10.2 的模板标记纪律同类：代码围栏内与 Markdown 引用块（`>` 起始行）内的 plan-q 行不计入提取，对 plan-q 格式本身的讨论、示例同样不计入（讨论这些标记的普通正文不是模板使用位点），人在一轮内批量作答后逐项写入对应 Decision，结构复用本文 §1.1；plan-q 不设 pending 记录态，未答的问题不存在对应 Decision。写者为批准/开工入口；消费者为开工核对（按固定格式提取的问题全集每项均有对应 Decision）与本文 §11.2 的 task.plan-approved 证据核对，编号重复、跳跃等格式不可靠提取的失败出口为 WF_SEMANTIC_DECISION；debug-ruling 条目不参与该问题全集判定（两者 id 前缀不同，防止把裁定条目计入问题全集）。debug-ruling 的 multiple 为该 verification_id 双源合并 failed 累计所跨过的 debug_repeat_threshold 整数倍序号（从 1 起）。双源合并累计是同一 verification_id failed 事实的唯一累计口径：合并累计为 check_history 中该 id 的 failed 最终结果条目数与 Execute 期声明条目经入口核定的次数之和；同一失败事件只在一个源计数——验证运行的 failed 最终结果已入 check_history 后不再计入任何声明次数。判重分工对齐设计稿 §1.5 的强制力模型（脚本核结构、人判语义）：脚本只核声明条目的证据引用真实存在、且与 check_history 条目的可比对字段（verification_id、check.id、命令行、输出摘要）机械比对一致；“同一失败事件”的判定结论属语义判断，由人/主会话在同一轮裁定中给出并结构化保存为 execution.debug_declarations 声明条目的 `dedupe_refs`（`[{check_id}]` 数组，见本段上文该字段的定义）；合并累计按“check_history 中该 id 的 failed 最终结果条目数 + 各 debug_declarations 声明条目 counted 之和 − 各声明条目 dedupe_refs 条目数”从结构化字段求和，不依赖自由文本即可重建；入口核 dedupe_refs 的两项约束：同一 check_id 在全任务各声明条目的 dedupe_refs 中全局唯一（重复出现即 WF_SEMANTIC_DECISION，两声明指向同一已计失败不重复扣减），且单条声明的 dedupe_refs 条目数不超过其 counted；求和结果不得小于 check_history 条目数——违反任一约束（含求和越界为负）按记录非法处理（WF_RECORD_INVALID），不据此判定倍数；入口只按结构化字段求和并核 dedupe_refs 引用的证据真实存在，不自行判定事件同一性；剔除结论的依据文本并入裁定 Decision 的 reason。Execute 期漏计兜底的声明条目复用同一 id 形式，multiple 取双源合并累计跨过的整数倍序号；其 counted 与 evidence_refs 随 debug_declarations 条目留痕，证据不限定 check_history 条目类型（check_history 条目、execution.actions 的 failed 结果及其 output_refs/verification_refs、handoff 材料均可支撑），不因证据不在 check_history 而无法重建。Decision 结构复用本文 §1.1，subject 记待决事实（verification_id、合并累计数、对应 debug_declarations 条目的 counted、阈值、所跨倍数），choice 记“同一问题”/“不同问题”，reason 记依据及证据引用。写者为处理待决项的入口（Check/continue/finish 裁定时）；消费判据：从 check_history 的 failed 最终结果条目与已留痕 debug_declarations 条目的 counted 重建双源合并累计，已跨倍数取合并累计数除以阈值的整数部分，每个已跨倍数须有对应 id 的裁定 Decision——“同一问题”则该倍数构成 debug_repeat 触发事实（按本文 §11.2 转正、复盘 required），“不同问题”则留痕、该倍数不再追问；无裁定的新倍数即未裁定待决项。跨会话接续按同一判据定位已裁定范围：旧裁定只对应其倍数、不外溢到新倍数，不重复询问。人批准规划的 Decision 即“问题集为空或已全部作答”的人判声明：该声明覆盖 PRD 实际存在的问题（含固定格式提取的遗漏面），机器不把“提取结果为空”倒推为无疑问，语义保证在人批准声明，尾部漏提的残余风险由该声明承载。它们是脚本写的判定记录，handoff.progress 仍是 AI 可起草的叙述，不能用进度勾选替代此记录。用户动作所需字段由当前批准规划/固定工作流快照解释；普通任务没有用户动作时 actions 为空。用户动作的 skipped 与框架 once 步骤的有效成果复用是两种语义，不能互换。

### 1.4 会话、准备与 writer

| 记录 | 关键字段 | 生命周期与写者 |
|---|---|---|
| `.wf/session-bindings/<session-key>.json` | 包络 + `identity: {provider, value}`、`instance_id`、`object: {kind: task/run, id}`、`bound_at` | start 在首次绑定时生成 instance_id 并固定 object；后续只核验，不换 object |
| 准备记录 | 包络 + `session_key`、`scope_paths`、`authorization`、`definition_refs`、`validation`、`progress`、`wip`、`ended_at` | 未绑定 start 准备子路由；准备记录的字段 schema 由本文固定，文件名/落点按本文 §10.1 归实现方案；数据随定义保留；结束不建立绑定 |
| `.wf/writer.json` | 包络 + `state`、`generation`、`holder`、`handover`、`checkpoint`、`maintenance_results` | 全部写权动作只由通用入口/独立维护入口在互斥内更新 |
| `.wf/.runtime/sessions/<session-key>.json` | `binding_digest`、`instance_id`、`object`、`current_task`、`cursor` | 当前会话定位缓存；丢失从绑定与实例重建 |

**会话请求协议**：所有会话入口从同一结构化请求信封的 session 对象取得 `{provider, identity, instance_id, activation}`。provider 仅取 host/wf；host 的 identity 为 `{host_id, session_id}`，host_id 是安装时人确认的宿主标识（`[a-z][a-z0-9-]{0,63}`），session_id 是经验证稳定的原始非空字符串；wf 的 identity 为 `{issued_id}`，issued_id 是入口显式签发的 UUID4。哈希对该结构作 C 编码，不 trim/改大小写/临时拼接 CLI 名。binding.identity 按表中 `{provider, value}` 保存，provider 取请求 provider，value 原样取请求 identity；SessionKey 只用 `{provider, identity: value}` 计算。首次绑定前请求 instance_id 可为 null，绑定入口首次生成后返回给当前会话携带；既有绑定后的入口先按当前 provider/identity 定位持久绑定，读取其中 instance_id 与请求比对，定位缓存不参与身份证明。两者一致则继续既有检查，缓存缺失仅重建定位，不视为未绑定。请求 instance_id 缺失时只读返回“待核对携带标识”及人调用 start 的出口：start 在实际会话身份已可靠核实、人的同一会话恢复事实明确后，可读回原持久标识返回当前会话携带，不改绑定/对象/实例标识，不要求为重取缓存执行 repair。证据不足时保留 WF_IDENTITY_UNRESOLVED；持久绑定已知应有却缺失、不可解析或两侧实例标识不同，则保留事实并转本文 §5.4 的出口。provider 未知、身份缺失或宿主映射不符时阻断绑定与推进，不猜环境变量。

身份来源声明作为安装记录的 session_profile 保存 `{host_id, provider, transport, capability}`；transport 首版只取 request_json，capability 为 `{status, verified_version, evidence_refs}`，status 只取 verified/unknown，verified_version 为核实的宿主版本字符串或 null，evidence_refs 指向压缩/重入/新会话的实际观察依据，未核实时 status=unknown；该声明由安装/维护预览的人确认后随本地安装记录写入，运行时不让模型自行修改。宿主/skill 适配层把实际上下文中的身份按此映射放入请求 JSON，由入口从标准输入解析；具体 CLI 外壳交实现方案，不另接受环境变量或命令行覆写身份。宿主无法保证稳定来源时由人选择 wf 签发路径，唯一 issued_id 由当前会话携带；丢失、复制到新会话或 provider 变化走明确恢复/新会话出口，不能自动签发新 id 绕过既有绑定。维护入口无需伪造 session。

**能力状态消费**：身份核验入口读取 session_profile.capability，而不是只核 provider 字面合法。status=unknown、证据缺失或当前宿主/传递方式与 verified_version/evidence_refs 不适用时，首次绑定与已有对象的恢复/推进均停止相关写入，输出 WF_IDENTITY_UNRESOLVED（需人裁决），列出未核实的稳定性/传递事实及出口；不允许“先绑定、压缩后再补核验”。只读诊断、能力核验和独立维护仍可运行，不把未知判成永久不支持。

核验出口为：人在不推进业务绑定的环境中检查宿主的同会话重入/压缩稳定性、新会话区别与结构化请求传递，确认实际证据后通过已有安装/维护预览更新 session_profile；或显式选择并核实可可靠携带的 wf 签发路径。wf 路径同样要验证携带/恢复方式，不能因 provider=wf 自动当 verified。status=verified 只说明对应来源能力已核实，每次请求仍须核实际 provider/identity、instance_id 与持久绑定一致。已经确认当前实现不支持该传递能力且无可用路径时用 WF_CAPABILITY_UNAVAILABLE（阻断），而“尚未核实/证据不适用”仍是前一需人裁决档。更换 provider/host 不重命名或改写旧绑定；既有对象经原写权释放/受控恢复后由新会话显式接续，不能用新签发标识绕过旧会话绑定。

activation 是当前会话由宿主/skill 携带的可丢弃缓存，取 null 或 `{enabled: true, start_source, enabled_at}`，start_source 为人的实际调用来源定位。人显式调用 start 时允许 activation=null，不以已有启用缓存为前置；start 核互斥/身份并返回允许启用的结果后，由当前宿主/skill 根据这次实际调用更新缓存。检查不通过则不生成有效 activation；仅绑定、重建定位缓存、读取旧 writer 均不得生成它。缓存保存在宿主当前会话上下文，经请求信封传给独立 CLI 进程，不写进项目 Git、本机解释器确认记录或他人会话文件；无需项目写权即可保持“启用未绑定”。项目内定位缓存仍只缓存绑定/游标，不因新增此传输字段放宽无写权项目写入例外。

continue/spec-update/bootstrap/finish 先由 skill 核实际调用上下文，再由入口核 activation 的结构、当前 session 对应关系；丢失/null/明确未启用时输出 WF_NOT_ENABLED 并提示人重新调用 start，不从持久绑定补 enabled。压缩可携带同一缓存，无法可靠携带就重新提示；重新 start 只恢复原对象，不产生改绑许可。该字段是可实现的会话间请求前置，不是人调用的机器证明；宿主或模型伪报缓存仍属设计稿 §1.5 的纪律边界，不宣称认证。纯只读诊断可在无 activation 下运行，不能借此推进业务。

writer.state 编码为 idle/held/recovering；generation 初值 0，每次授予、撤销或恢复所有权严格递增。holder 为 null 或 `{kind: session/maintenance, id, scope, generation}`。会话 scope 仅为绑定对象或已授权准备范围；维护 scope 为操作、预览摘要与精确路径。维护操作标识取 maintenance_results 的 operation id；无结果登记的维护动作由 `H("wf-maintenance-op-v1", C({operation, generation}))` 派生。handover 为 null 或 `{from, receiver_session_key, object_or_preparation, decision, invalidated_generation}`。checkpoint 保存最近完成控制步骤、执行进程 pid/启动标识（可核实时）及时间；进程字段仅作存活线索。

`maintenance_results` 是按操作 id 保存的未结结果集合，单项字段为 `{operation, preview_digest, head_before, changes, receipt_git_state, result, disposition}`：head_before 固定为本次维护第一次写入前的 HEAD，changes 包含精确路径、前后指纹、索引/HEAD 差异；result 为 applied_pending_commit/persisted/disposed；disposition 保存人的处置、承接对象及核验事实。完整结案的确认与移出当前集合按本文 §4.5 执行，历史由 Git 保留；新操作不能覆盖未结项。writer 自身回执的路径不放入 changes 的递归哈希；公共字段与回执字段分别核写权和整文件提交授权。

未绑定会话的准备授权不复用任务批准；首次绑定才建立 instance_id，此后该标识随会话携带。没有稳定身份或实例标识恢复证据时输出需人裁决，不从唯一活动任务猜绑定；仅定位缓存丢失而持久绑定与请求身份一致时，直接重建缓存，不触发记录 repair。身份冲突的修复保存原文及依据，不能通过删除绑定重新选对象。

### 1.5 实例与终止数据

`.wf/workflow-runs/<run-id>.json` 保存包络及下列字段；完整快照固定在设计稿规定的 `definition.md`，解析结构可从快照重建。

| 字段 | 内容 | 消费 |
|---|---|---|
| `definition` | `{workflow_id, content_version, format_version, snapshot_path, digest}` | 每次推进验证固定版本，源定义修改不改它 |
| `inputs`、`creation_decision` | 实际输入值或引用、人的版本/输入/展开规则确认 | 静态/消费时校验；输入引用不存秘密值 |
| `cursor`、`step_results` | cursor 为 null 或 `{step_id, task_id}`（人判步骤 task_id=null）；按步骤 id 保存决策、产物引用、略过/满足/未执行结果 | 通用推进；不复制任务 status/Check |
| `task_map` | 步骤 id → `{task_id, predecessors, superseded_ids}` | 幂等创建与继任者定位，最终状态查 task |
| `sequence_changes` | `[{kind, step_id, source_task, task_id, resume_task, decision}]`；kind 为 rework/replace | 定义步骤内的受控任务插入/继任路由，不修改原定义快照 |
| `pending`、`paused` | 当前失败/待决事实或 null；布尔 | 停在当前步骤，不自动终止 |
| `closing` | null 或 `{mode, decision, task_dispositions, next_step}` | 批量退出检查点，不是另一任务生命周期 |
| `terminal`、`ended_at` | null 或 normal/abnormal；null 或 Time | 终态摘要、历史读取与释放 |

step_results 的 kind 只取 satisfied/skipped/not_executed；尚未完成的步骤没有这类结果，pending 记录等待。任务步骤只存 task 引用和本次消费摘要，不抄 task 的批准/检查。返工时 cursor.step_id 保留原定义步骤，cursor.task_id 可定位 sequence_changes 明确登记的 R；task_map 仍保存该步骤的正式任务/继任者，不被临时 R 覆盖。实例异常终止时的任务处置为历史快照；保留任务后续状态仍查 task。

## 2. 入口与单任务状态机

### 2.1 调用与操作归属

| skill/入口 | 机制操作 | 共同校验之外的前置 |
|---|---|---|
| 人调用 start | 只读启用、准备定义、创建任务/实例、首次绑定、取得/接收写权 | Trellis 互斥事实、稳定身份；已绑定只恢复同对象 |
| 人调用 bootstrap | 存量项目接入规划与基线初建 | 已启用、当前接入任务；开工仍核批准 |
| continue | 批准、开工、Check、暂停/恢复/收工、基线提案、边/返工/替换/放弃、实例推进/终止、审查记录 | 已启用、绑定正确；项目写入核 holder/代次/范围 |
| spec-update | 知识编辑/索引同步与处置记录 | 当前批准范围；删除/合并等按既有人工裁决 |
| 人调用 finish | 最终门禁、正常归档、必要实例同步 | 人了解结果与未核实项，且本文 §9.3 前置通过 |
| 人直调维护 | 安装、upgrade、repair、uninstall | 预览/确认及本文 §4、§10；不以会话绑定授权维护 |
| 只读查询 | 状态/视图、`wf spec --file <path>` | 无项目写权前置；按本文 §8.3 仅可写本会话读取侧车，身份不可核时只读且不给完整读取回执 |

启用是当前会话中的人调用事实，记录和缓存不能机器证明；入口通过本文 §1.4 的请求 activation 核结构化前置，skill 核实际人调用上下文；两者均不把绑定当启用，缺事实或缓存则给调用提示。已结束绑定对象只返回结果；为下一对象创建新会话不改变历史绑定。只读查询可在无写权下运行；当前会话读取侧车是设计稿 §4.4 的窄例外，不能写他人侧车或判定字段。

start 先直接读当前 SessionKey 的绑定路径及当前 writer，并核本文 §6.1 的实例/独立接续资格；只加载当前对象、相关活动记录和判定需要的历史引用。首次绑定前核该身份路径是否已存在，已知应有而缺失时结合该路径的 Git 历史和引用诊断，不重当未绑定。活动区仍需扫描候选、DAG 和未处置 WIP；历史绑定只在当前 writer/对象引用或周期巡检时解析，不每次遍历全部旧会话。已结束实例只读终态摘要及本次需要的来源，保留任务独立接续不重跑旧实例步骤。

Trellis 核对依次收集已存在的数据/hook/项目指令入口线索、当前宿主适用的配置/托管指令以及本会话实际加载事实。已确认有效流程指令输出 WF_FLOW_CONFLICT；适用性未知输出 WF_SEMANTIC_DECISION；只有经人核实纯残留且无有效指令时继续。删除文件不能清除已加载上下文，冲突会话需换清理后的新会话。检查不安装 CLI、不调用 update、不自动改其他框架文件；非 Trellis 的其他流程按设计稿共存边界处理。

### 2.2 合法状态与迁移

status 的编码对应未开工、执行中、已归档；phase 对应 Plan/Execute/Check/Finish。初始为 not_started/plan，terminal=null。暂停与挂起可并存；执行候选精确等于 `status=in_progress AND NOT paused AND NOT suspended`。每次可能改变候选的动作在同一互斥中验证全活动区候选数不超过 1。

| 动作 | 源状态 | 前置与目标 | 失败出口 |
|---|---|---|---|
| 批准规划 | not_started/plan 或 in_progress/plan | 人批准当前版本、复杂度/TDD；Plan 期人判问题全集按本文 §1.3 由人一轮内作答，只写 plan 与对应 execution.human_decisions，不改变开工事实 | 版本不符重新呈现规划 |
| 首次开工 | not_started/plan | 本文 §2.3 → in_progress/execute，固定 baseline_head 并保存 entry_snapshot | 留在 Plan，指出缺前置 |
| 再入 Execute | in_progress/plan | 重新批准与开工条件成立；保存当前批准对应的新 entry_snapshot，保留原 baseline_head/提交归属 | 原批准不适用则待人确认 |
| Check | in_progress/execute 或 check | 对象稳定、范围合法；写结果，pass 后进入 finish | fail 留 check，修复回 execute |
| Finish 中变更 | in_progress/finish | 对象/规范变化使旧结果失效，回 check 或 execute | 不沿用旧 pass |
| 实质规划变更 | 未归档任务 | phase=plan；原批准/检查留历史但当前无效，status 不回未开工 | 人澄清并重批 |
| 暂停/恢复 | 未归档任务 | 人决定；恢复核身份、写权、真实 WIP、候选和前置 | 不清挂起，待决则不推进 |
| 挂起/清除 | 未归档任务 | 返工/复评按本文 §6；不重写 phase/status | 保留阻塞事实 |
| 正常归档 | in_progress/finish | 本文 §9.3 及授权提交成立 → archived、normal | 未获 finish 调用/提交许可则等待 |
| 异常归档 | 任一未归档任务 | 放弃/替换决定与图/改动处置成立 → archived、abnormal | 只阻断结案，业务停止决定仍有效 |

archived 必须有 terminal/archived_at，且无未决暂停/挂起；异常退出将取消等待作为历史处置后清标记，不假称等待已满足。归档记录通常只读；repair 是记录修复，不是重开旧业务任务。T 挂起而 R 执行不构成多个执行候选。

### 2.3 规划输入、批准与开工

PRD 是规划内容来源：正文写目标、范围、方案说明与不做项；唯一 `<!-- wf-plan:v1 -->` 标记后的紧邻 `json` 围栏保存下表机读块。该块按本文 §1.1 的 JSON 规则解析，不同时接受另一套 frontmatter 字段。任务记录 plan 是入口保存的版本快照，不是供人另行编辑的第二份规划。块缺失、重复、非法或与正文意图有已知冲突时，批准/开工均停止；前者报结构错误，意图未决交人裁决。

| PRD 块字段 | 类型与来源 | 批准时写入 |
|---|---|---|
| `schema_version` | 正整数 1 | 记录格式版本随 artifacts 快照保留 |
| `touch_paths` | 仓库相对 glob 数组；调查可显式为空，缺字段不等于空 | 全部通过本文 §3.1 后保存 plan.touch_paths |
| `acceptance` | 非空 `{id, statement, verification_ids}` 数组；id 唯一，statement 非空，引用已声明验证 id | `acceptance_digest=H("wf-acceptance-v1", C(acceptance))` |
| `verifications` | `{id, invocation, cwd, input_refs, required, consume_at}` 数组；id 唯一，required 为布尔，consume_at 为 start/check/finish | 原样形成 plan.verifications；检查结果另存 check.commands |

invocation 取 `{kind: argv, argv: [字符串…]}` 或 `{kind: manual, criterion: 非空验收说明}`。前者是固定参数数组，不作输入插值或 shell 求值；项目既有脚本可作为获批 argv 调用。cwd 为 `.` 或项目内安全路径；input_refs 的全部引用类型、允许场景及秘密引用规则统一见本文 §7.1，普通任务只使用其中标明适用普通任务的类型。manual 供文档等人工可观察验收，其实际人判进入检查证据，不伪造 exit_code。开工时必须立即可运行的检查由 consume_at=start 指定；新测试设施可在规划中给出确定的未来路径/调用并标 check，消费前仍须核实。验收项允许 verification_ids 为空，但须由本任务 check.acceptance_results 中的实际人判证据覆盖，不能从空数组推出验收通过。

批准入口先读取 PRD 块和所需规划文件，核 schema、唯一 id、全部 glob、验收引用与验证声明，再提出复杂度/TDD 并交人同批确认。`plan.version=H("wf-plan-v1", C({artifact_digests, plan_block, complexity, complexity_reasons, tdd}))`，artifact_digests 包含 PRD 整文件及适用的 design/implement，且不包含带有本 version 的控制记录。确认时重读输入；发生变化就返回重新核对，不保存过时批准。批准成功保存可读快照、提取值和 Decision。普通任务 Plan 期的 grilling 类待决问题由规划材料按本文 §1.3 的固定格式承载：每个待决问题编号 `plan-q-<n>` 并附推荐答案，措辞使“是”即接受推荐项；人一轮内批量作答后，由批准/开工入口将答复写入 execution.human_decisions（对齐设计稿 §4.3 grilling 行的完成信号），未答的问题不写入 Decision。首次开工和回 Plan 后再入 Execute 都重新提取当前 PRD，与当前有效批准逐项核对后保存 entry_snapshot，再迁移阶段；只有首次开工同时固定 baseline_head。批准入口不能提前替代开工时点的这次核对。

PRD 改动不会自动扩充 plan.touch_paths；plan 被手改也不能反向授权 PRD。两侧不一致时，机械修订可经 equivalences 衔接并由入口重取同义快照；影响范围、验收、调用或取舍的变化回 Plan 重批。在此之前执行以最近有效批准为边界，但不允许带失配继续开工、Check 或 Finish。

开工按顺序核对：启用/绑定/写权及本文 §6.1 接续资格 → 记录可解释及无未恢复动作 → 工作区归属与候选唯一 → 本节规划提取/批准与模板标记 → touch_paths 安全及语义未决 → 无未决范围问题（按本文 §1.3 固定格式提取的问题全集均有对应 Decision 且当前有效批准存在；提取不可靠或存在未答项 → WF_SEMANTIC_DECISION）→ 依赖、暂停/挂起 → 基线/配置 → Git HEAD → 本节 verification.resolve(start) 及立即基本核验 → 本文 §11.2 的适用开工前步骤全部满足。每项失败返回本文 §11 的局部原因和出口，不先写业务文件。

**验证分时消费（verification.resolve）**：输入为当前批准 plan.verifications、工作流的具名来源声明（若有）和时点 point，point 唯一取 start/check/finish。先按 verification_id 关联、核来源结构/版本与当前批准调用一致，再解析 cwd、输入及真实脚本/文件/设施，输出逐项 ready/blocked/needs_decision、具体缺失事实和来源哈希。它是只读固定处理器，不写检查结果、不执行业务验证；不以“定义可解析”替代真实就绪。

- start：首次/再入 Execute 的 task.transition 必须对 consume_at=start 项调用处理器，缺失任一前置不得迁移；批准 PRD 指定的立即基本核验也须实际执行并取证，证据引用纳入本次迁移 action 的步骤后置及 control_assertion。check/finish 项可保持待解析而不阻断自举自身；依赖参数仍取既有发行缺省。
- check：task.check 对全部批准必要验证及被验收引用的项核实际就绪，再实际执行并写 check.commands/acceptance_results。consume_at=finish 只延后最后重核的时点，不豁免必要业务验证在 Check 中通过；缺就绪/结果不明就不能 pass。只有与验收无关、明确非必需的声明可留 not_run 并显示原因。
- finish：task.archive 在改归档终态前，对 consume_at=finish 及当前 Check 依赖的来源/输入再核版本与就绪，比较检查锚点。缺失、变化或此时新增必要检查就回 Check（涉及规划实质变化先回 Plan），不得在归档提交后补必要验证或把此处理器的 ready 当测试 pass。

调用结果由承载动作的 steps 后置和 evidence_refs 引用，重入重核真实来源，不建第二份命令注册库；普通只读查询可调用该处理器作诊断，不能写 action 或伪造检查通过。该算法只管理验证来源/就绪，实际执行的命令结果继续唯一保存在对应 Check 与任务验证证据中。

entry_snapshot 结构为 `{plan_version, approval_ref, prd_digest, touch_paths, head_at_entry, entered_at}`：plan_version 是本次有效规划版本，approval_ref 定位实际人批准或已登记的机械修订衔接，prd_digest 为开工时重读 PRD 的字节摘要；touch_paths 从该批准版本的 PRD 重提取并规范化，顺序去重后保存；head_at_entry/entered_at 记录本次观察的 HEAD/Time；本次迁移动作由 task.action 与 write_mark.action_id 对应，不在快照内嵌自身 action.id，避免幂等键输入自指。入口在同一 action 内完成快照写入与 Execute 迁移，中断按原前后像恢复，不出现进入 Execute 却无对应快照的合法态。再入以新快照替换当前 entry_snapshot，旧快照由原规划快照、动作与 Git 保留，不改变首次 baseline_head。

在 Execute/Check/Finish，批准范围取 entry_snapshot.touch_paths，不能只取后来可变的 plan.touch_paths；同时必须核当前规划有效性。若只是机械修订衔接，原 entry_snapshot 保持开工事实，核 equivalences 的完整版本链及两端规范化 touch_paths 相等后可继续；范围变化或无法核同义时回 Plan 重批并再入，不能自动改开工快照。本文 §3.2 和本文 §3.5 的检查锚点包括 entry_snapshot 的规范 JSON 摘要与当前有效 plan.version，门禁 1 核二者对应关系。未开工时 entry_snapshot=null；已开工而缺失/冲突时走恢复，不从当前规划倒填过去的开工事实。

baseline_head 仅首次从 not_started 进入 Execute 时固定；in_progress 回 Plan 后再次进入 Execute 保留原值。这避免遗漏重新规划期间的外部变化。扫描区间始终从首次基线到当前 HEAD，先用 Git 路径过滤仅呈现与当前范围/触碰集合相关的未归属提交；任务归属仍只取 trailer/人裁和继承记录，区间增长不追认授权。缺失/不可达的原基线走锚点核对，不用当前 HEAD 静默替换。

初始化/接入只豁免活基线/项目配置已经存在；参数取同版发行骨架，已批准 PRD 给可立即执行的基本检查。自行建立的测试设施在建成后参加 Check，不作为自身事前前置。工作流实例可先创建规划，但无基线时首个任务步骤必须 initialize/bootstrap；前置人判步骤不能改交付。接入仍需人实际调用 bootstrap。

模板占位集合首版为 `{{WF_REQUIRED:<field>}}` 和 JSON 已知必填字段中的字符串 `__WF_REQUIRED__`；每份模板登记哪些字段/段落必填。校验只检查模板声明的待填位置，不因业务说明讨论 TODO 或字符串示例而误拒；新版本模板标记随发行一起版本化。规划必填还核非空和类型，删除标记留下空值不能通过。

## 3. 路径、归属与检查对象

### 3.1 路径安全与 glob

仓库相对的交付、spec、工作流引用与 touch_paths 先按设计稿 §6.1 的拒绝条件检查：绝对路径、`..` 段、反斜杠、控制字符非法；空路径不是可写文件。执行器配置和显式投放根使用各自的路径规则，不套此相对路径限制。分隔符规范为 `/`，消去 `.` 与重复分隔符，不改大小写或 Unicode 正规形。glob 按路径段匹配：`*`、`?`、`[...]` 使用标准库 fnmatch 的段内语义；整段 `**` 匹配零或多段；其他字符按字面，不因作用域标记或非 ASCII 被拒。普通 `*` 不跨 `/`，不隐式排除点文件。未闭合 `[` 按字面匹配，不临时新增形状 allow-list。

匹配前解析字面前缀，命中后解析现有路径各段；不存在目标取最近存在祖先的真实位置加剩余字面段。自仓库根向下核涉及祖先的 `.git` 目录或 gitfile，根自身 `.git` 合法，遇嵌套根停止，不读取其中内容。符号链接的目录目标须仍在同一仓库边界；文件内容指纹使用链接本身的目标字符串，不跟随读外部内容。坏链/无法确定边界只阻断相关操作，删除旧路径可用原提交的文件类型/路径事实核范围，但不把历史内容作为当前指纹。

项目控制面 `.wf/` 内写入落点须能确定为本项目数据/资产，不通过符号链接把写入引出项目边界。明确授权的项目外宿主 skill 根按本文 §10.1 作为独立投放根核验，不允许借其内部符号链接转写未授权位置；这是声明根的投放，不等于允许从项目内符号链接越界。

touch_paths 任一非法条目拒绝批准/开工；spec.paths 非法项逐条失效并可见报告，整个 metadata 解析不可靠时该文件不可路由。无合法 paths 的 spec 仍可由索引/策展显式加载。语法命中而范围意图存疑输出需人裁决，不自动扩大 glob。

### 3.2 内容指纹

单项为 `{path, exists, kind, executable, digest}`：kind 为 file/symlink/deleted；file.digest 是文件原始字节哈希，symlink.digest 是链接目标字节哈希，deleted 的 exists=false、digest=null、executable=false。可执行位按任一执行位存在编码为 true；目录不是交付文件项，展开其实际文件，涉及未支持类型（设备、套接字等）报告不能核验。

task.check 在记录结果前消费本文 §2.3 的 verification.resolve(check)。Check 对象为设计稿 §4.2 的触碰路径与规则输入并集；每项标用途 delivery/spec/baseline/config/workflow_snapshot，集合按路径去重排序。保存 `paths_digest=H("wf-check-paths-v1", C(paths))`（paths 为去重排序后的触碰路径数组）与 `content_digest=H("wf-content-v1", C(items))`（items 为本节指纹项）；检查锚点是本节唯一编码的独立哈希域 `check_anchor=H("wf-check-anchor-v1", C({plan_version, entry_snapshot_digest, touch_paths_digest, content_digest, acceptance_digest, spec_versions, baseline_digest, config_digest, workflow_snapshot_digest}))`，键集合逐键对应检查事实来源：plan_version 为当前有效批准的 plan.version（经等价链归一：当前 plan.version 可沿本文 §1.3 的 equivalences 完整版本链归一到既有批准版本时，取归一后的 plan_version——机械修订不改变锚点，语义变化回 Plan 重批后版本链断开、锚点随之变化）；entry_snapshot_digest 为本文 §2.3 entry_snapshot 的规范 JSON 摘要；touch_paths_digest 与 content_digest 即上述路径集合哈希与指纹哈希（touch_paths_digest 取等价链两端规范化后相等的路径集合哈希）；acceptance_digest 为本文 §2.3 定义的验收摘要（经同一等价链归一）；spec_versions 为当前命中/策展 spec 的 {path, digest} 排序集合；baseline_digest 与 config_digest 为当前项目基线、有效项目配置的指纹；workflow_snapshot_digest 为影响本次执行的工作流定义快照哈希（无实例上下文时为 null）。路径用途标注是呈现标注，不进入锚点输入。当前存在状态一律来自工作树，HEAD/暂存区状态另列，不代替内容。

扫描开始/结束比较路径集合和指纹，文件读取前后比较可观测元数据；检测到变化重取或报对象变化。相同元数据下的对抗替换不在防护承诺内；测试期间已知环境/依赖变化即使未体现路径差异仍使相关检查失效。

### 3.3 提交归属与未提交路径

读取本任务 baseline_head 至当前 HEAD 的可达提交和明确登记的继承提交；提交 trailer `wf-task: <id>` 或人的归属裁决是任务归属依据。一个提交同时出现冲突 id/裁决即交人核对。按 Git 路径差异读取增删和改名两端；不依赖 rename 相似度把旧端漏掉。归属裁决仅指向未归档任务，继承路径保存原来源引用，不给原提交改 trailer。

当前未提交路径从工作树与索引相对 HEAD 的并集取得，包括未跟踪的拟交付文件；明确忽略的缓存不计，已批准交付被 ignore 遮住则报告需处理，而非强制暂存。每条先核是否为固定职责控制记录或未结维护组，再核当前 entry_snapshot.touch_paths，并按本文 §2.3 核当前规划与开工快照的对应关系；交叉认领或语义存疑需人裁决。未开工任务只能按批准规划预览拟触碰范围，不能凭预览取得交付写入权限。命中宽 glob 不能覆盖原有外来改动归属，开工时的逐路径边界事实优先保留。

最终触碰集合＝本任务标记提交路径 ∪ 归属裁决路径 ∪ 替换继承路径 ∪ 当前明确归属路径。未归属提交与范围无交集则不阻断；有交集按外部变化核对影响，确属遗漏才由人裁决归属。baseline 不可达时按历史锚点核对处理，不改为扫描全部历史追认。

### 3.4 规划与基线变更

规划的机械修订建立版本衔接记录；实质变更清当前批准适用性并回 Plan。基线/项目配置提案包含旧指纹、目标内容及批准引用，入口核绑定/写权/范围后以 baseline.apply 在当前 task.action 固定活文件的前后像和批准引用，按本文 §5 成组应用/记录中断；更新内容后重新检查。人已批准的基线变更不再被旧基线的同一条规则反向否决；其他权限与安全边界照常核验。

初始化的 `python_executable` 首次写入须在批准 PRD/基线提案逐项列键和值；骨架不提供该键的示例值作为实际配置。原项目键失效或删除走原配置通道/repair，不通过换低优先级执行器掩盖配置失效。

### 3.5 Check 记录与有效性

check 结构为 `{id, anchor, started_at, ended_at, result, commands, acceptance_results, internal_review, tdd_evidence, invalidation}`。anchor 为 `{check_anchor, rule_version}`：check_anchor 按本文 §3.2 的定义计算（哈希域名与键集合见该处，覆盖批准/entry_snapshot/触碰面/验收、触碰路径集合与指纹、相关 spec/基线/有效配置及影响执行的定义快照），rule_version 为本次检查所用的框架规则兼容标识、取本文 §10.2 的 effective_rule_version；本文 §11.2 回执 P 中的 check_anchor 指 anchor 的内容哈希部分。commands 每项包含 `{verification_id, invocation, cwd, input_refs, required, started_at, ended_at, exit_code, status, summary, evidence_ref}`；输入引用不复制凭据，日志摘要按秘密边界脱敏。

status 取 passed/failed/not_run/not_applicable，未结束的命令 ended_at=null。必要项只有实际结束且成功才可判 passed；not_applicable 要有与批准验收对应的理由，不作为用无关测试补位的通道。internal_review 分别记录标准轴、需求轴的结论与依据；两轴均完成才可 pass。result 取 pass/fail，尚无完整结果则 null。

commands.verification_id 必须命中本次 plan.verifications 的唯一 id，invocation/cwd/input_refs/required 与批准项一致；每次 Check 对每个声明至多保存一个最终结果，调试重试过程用 evidence_ref 引用，不能用其他命令同名顶替；单次 Check 内的调试重试不产生多条 check_history failed 条目（每声明只存最终结果，重试到绿的形态不进入本文 §8.1 的机械检测口径，由 Execute 期声明兜底承载）。必要集合从批准规划计算，不能从实际结果里标 required 的子集反推。缺失必要结果、未知 id、重复最终结果或调用失配均不能 pass。argv 项 passed 须 ended_at 非空且 exit_code=0；manual 项 exit_code=null，须有同对象的人决定证据；批准的不适用项以理由与适用依据记录，不伪装执行成功。

acceptance_results 每项为 `{acceptance_id, verification_ids, decision, conclusion, evidence_refs}`，逐项覆盖当前批准 acceptance，不能遗漏或添加未知 id。verification_ids 与规划声明一致且其必要结果通过；列表为空时 decision 必须是针对该 acceptance_id、plan.version 和当前 check.anchor 的实际人判 Decision，证据直接存于本项，不借内部自审结论补位。conclusion 取 passed/failed/pending；任一 failed/pending 或所需证据缺失使 Check 非 pass。该验收人判不替代最后人调用 finish，未改变业务验收也不凭空增加独立 reviewer。

plan.tdd=true 且对象为可执行行为变更时，tdd_evidence 保存 `{assertion, red_command_ref, red_reason, green_command_ref, properties}`，核确有针对同一行为的红/绿运行，红不是环境启动失败，properties 分别说明可红、确定性、快速、可无人执行的依据。关闭时为 null；文档/调查按设计稿 §4.3 以独立可观察产物验证，记录适用性，不人为造失败命令。它不替代必要验证或内部双轴审查。

保存协议与计算有效性：Check 入口在同一次原子动作内、写入新 check 结果前，将旧 check 记录移入 task.check_history（按 check.id 定位，不删不改历史条目），failed/not_run/中断的记录与带 invalidation 的失效 pass 一并完整保留。当前锚点核对仍用 check；复盘触发计数与触发重建从 check_history 读取 failed 最终结果条目，并按本文 §1.3 的双源合并口径并入 execution.debug_declarations 条目 counted。计算有效性为：当前 anchor 与检查保存值一致，逐项必要检查通过，两轴通过，且无已知外部影响或未决项。失效的旧 pass 保留原结果并给 invalidation 的事实，派生有效性为 false，历史证据留在 check_history；不删除历史结果或把文件还在当有效。框架规则集改变须核兼容声明，影响门禁的项重跑。修复后的验证形成新 check.id，旧记录已按上述协议入 check_history，旧审查不自动沿用。check_history 是任务记录自身字段，不新增独立生命周期账本，周期巡检/统计不单独消费它。

## 4. 写入权、互斥与工作区

### 4.1 锁原语与存活线索

短时互斥使用标准库 `fcntl.flock(fd, LOCK_EX | LOCK_NB)`，锁对象固定为项目根 `.wf-lock`。已存在文件只在完整内容等于 `wf-lock-v1\n`、普通文件且真实落点属于项目根时复用，持锁全过程保留同一个 fd，释放用 `LOCK_UN`/关闭 fd；不删除或原子替换锁文件。锁对象不是持久所有权记录。

首次创建以排他创建方式打开锁文件，在该 fd 上获取排他锁后写固定标记并 flush/fsync；并发观察到空/不完整标记者退出报告初始化未完成，输出 WF_CAPABILITY_UNAVAILABLE，facts 记锁标记不完整及路径，不将它当空闲锁、不覆写未知内容。创建进程中断留下不完整标记时，人核实后处置同名文件；普通入口不自动认领。标记写入不是对该路径所有权的密码学证明。

锁等待采用 monotonic 计时，首版固定上限 5 秒，每 50 毫秒非阻塞重试；超时返回锁占用原因及可取得的 holder/checkpoint，读不到时显示未知，不写项目数据或抢锁。持锁后再次核 pathname 与 fd 的设备/inode 一致及标记可识别；不一致停止本次写入，给人核对锁文件被替换/删除的出口。运行期不支持网络文件系统、外部同步复制或不具备本地锁语义的挂载；安装/能力自检声明实际文件系统，无法确认时需人核实，不默认为支持。

锁内事务限定为控制记录读改写、预检及维护受控应用；业务编写、长时间测试与等人答复不长期持 OS 锁。长操作由持久 writer 授权，开始/每个写入检查点/结束均核 generation；失去代次立即停止。直接工具写入仍受纪律限制，文件锁不会拦截所有编辑器。

holder 的 pid 与进程启动线索来自实际执行入口。Linux 可读取 `/proc/<pid>/stat` 的 starttime 和本次系统启动标识来区分 PID 复用；信息不可读则标 unknown。它们只说明入口进程可观测状态，不等于长期 AI 会话活跃或停止；一次子命令正常退出也不释放会话写权。异常恢复一律结合持久持有事实、已落盘动作与人的旧写者停止确认。拿到 OS 锁但 writer=held/recovering 时，仍需原所有者或已授权恢复，不能直接授给新对象。

### 4.2 写权状态转换

| 操作 | 锁内前置 | 持久结果 | 失败/重入 |
|---|---|---|---|
| acquire | idle、身份/首次绑定及本文 §6.1 接续资格成立、工作区允许该对象、无未恢复动作 | generation+1，held、holder；首次绑定按本文 §5 成组写入 | 原范围不一致或 WIP 属其他对象则拒绝 |
| checkpoint | held 且类别/id/generation/范围匹配 | 更新检查点，代次不变，保留维护回执 | 旧代次拒绝所有业务写 |
| release | 原 holder 匹配、对象暂停/终态或准备结束、交接/WIP 已核 | generation+1，idle，holder=null，保留历史绑定/回执 | 工作区未处置则不称释放 |
| handover.begin | 旧会话持有、人确认接收者与同对象/准备范围、进度/暂停/WIP 处置已保存但尚未普通 release | generation+1，recovering；保存 handover，旧代次失效 | 中间态双方无业务权 |
| handover.accept | 指定接收者、首次绑定或原绑定一致、本文 §6.1 接续资格成立、真实 WIP/范围未变 | generation+1，held 新 holder；完成接收检查点 | 接收者绑定其他对象即拒绝 |
| maintenance.acquire | 人预览确认、旧写者已停止、工作区符合维护前置 | generation+1，held、maintenance holder | 未结维护组同路径冲突先处置 |
| recover | 人确认旧写者停止与可恢复事实，代次/范围可证明 | 在原代次上递增，保持恢复中直到动作补齐/授予 | 无法证明则保留诊断和独立卸载出口 |

generation 在每次撤销和授予时变化，handover 消费保存的 invalidated_generation；正常释放后再 acquire 是新路径，不复用显式接收许可。缓存中的 generation 只能用于比对，不能反写 writer。缺 writer 或缺锁且有既有记录不视为首次安装。

准备定义的权限是 session holder 的 preparation scope，只能改已预览定义/准备记录。创建任务/实例时先完成准备释放与工作区处置，再在 acquire 动作中建立首次绑定；直接把准备权限扩成任务权限不合法。

### 4.3 同对象 WIP 与收工

wip 记录 `{decision, object, task_id, step_id, paths, risks, pending, resolved}`。paths 每项含本文 §3.2 指纹、索引状态、相对 HEAD 的差异及归属依据；不保存文件内容副本。普通任务的 object 为自身，实例另必须绑定当前 task/step；准备者记 preparation id 和范围。人选择保留后由入口记录、暂停/保存准备进度，再 release。

acquire/接收/start 读取活动任务和准备记录中 unresolved WIP：同对象且同实例当前任务可核真实指纹后恢复，变化时重新核对归属/范围；其他对象、实例下一任务和普通升级先要求实际处置。原 WIP 已提交或反向修正完成后，由入口核对并写 resolved 依据；仅删说明或给一句“已处理”不解除限制。

收工决定为 commit/keep/reverse/transfer，Decision 只表示选择；commit 还需提交授权且成功，reverse 需实际完成且在授权内，transfer 需具名对象与实际承接。无归属、跨任务混杂或外来改动不能纳入 keep 例外。直接关闭 CLI 未完成这些动作时，写权记录仍占用，原会话核身份/代次恢复，新会话先经 repair 核旧写者停止。

### 4.4 工作区分类算法

每次开工、换任务、获取/交接/释放写权及维护前，将当前路径差异分为：当前交付组、当前固定职责控制组、已登记关联控制组、未结维护组、同对象保留 WIP、运行态、外来/未知。分类依据为批准范围、write_mark、动作目标、维护回执与 WIP 记录；不按 `.wf/` 前缀一概豁免。

运行态忽略仅适用于本文 §10.1、§10.2 登记的 `.gitignore` 精确托管段，控制组可待提交但必须可解释。换对象/实例下一任务/普通升级要求业务改动已授权提交或实际处置；同对象 WIP 例外仅用于本文 §4.3。任何路径多组冲突先输出需人裁决，保留全部内容，不自动 stash、清理或捎带。已知删除路径也是差异，不从分类中消失。

### 4.5 维护变更与 writer 整文件提交

**可达提交查证**：给定区间下界（该次操作登记的写入前 HEAD）与该次操作登记的结构，历史查找覆盖下界..当前 HEAD 中触及该操作登记精确路径组的提交，候选按拓扑逆序逐个核对完整树状态；某个可达提交同时包含登记的回执/终态与完整路径组登记状态，即证明该次操作已持久化。之后的差异按当前任务/外部变更归属处理，不倒算为该次操作未持久化；不扫描操作之前的历史，也不以“近 N 次”截断后推断已完成。下界不可达、旧格式缺该界限、历史查询失败或没有完整依据时标待核对，走本文 §5.4 的锚点核对出口，不扩大为全库猜测。

maintenance_results 承载尚需核实或处置的维护结果；Git 保存已结历史。upgrade/repair 完整应用后登记精确变化及 head_before。结果可核但无提交授权时记 applied_pending_commit，报告并释放；提交失败但结果可核也走待提交，结果不明保持 recovering。每次读取先比较 HEAD 中的该操作回执和完整路径组终态，再核工作树/索引差异：全部一致即可派生 persisted，读取本身不为了更新结果再次写 writer。

若路径已被后续合法工作修改，按本节开头的可达提交查证派生：区间下界取该操作登记的 head_before，登记结构为该操作回执（maintenance_results 单项）与完整路径组登记终态；查证成立即证明该次维护已持久化，后续同组路径差异按当前归属处理，不要求工作树当前与登记终态完全一致。

已完成反向修正或具名承接时，原回执保存 disposition 及实际路径状态；其结案证明须包含该处置决定、核验事实和必要承接引用，不能仅凭文件内容碰巧相等。未结、冲突或仍被未完成 action 使用的回执始终完整保留。

已结回执在下一次实际维护操作的预览中可列为收敛对象：逐项核对上述可达提交、完整处置事实，且相关路径当前无未处理工作树/索引差异，然后由维护入口移出当前集合；不在 writer 内永久累加一行摘要。该维护 action 记操作 id、原回执摘要与证据提交，移除前像已经在 Git 中，历史仍可追溯。收敛与 writer 整文件提交须各在原有授权范围内，不能为清理回执单独滥用 repair 或新增入口。没有收敛授权时保留回执并报告，不限制未结项数量来换取性能；因长期未提交而积累的真实待处理项仍须人处置。

writer 的 state/generation/holder/handover/checkpoint/write_mark/action 是公共协调字段；maintenance_results 为维护回执。后续写者更新公共字段时必须保留全部未结回执。未结期间公共字段合法变化可待提交，不阻断无交集任务开工；但暂存/提交 writer 整文件会同时带入回执，故其提交授权必须明确覆盖维护组。未授权时从该任务提交路径中排除 writer，不能用部分字段“已属于本任务”推导整文件许可。

回执不包含 writer 自身哈希，receipt_git_state 只记录观察到的 HEAD/索引存在性等事实；比较历史回执只取本操作的字段，不要求 writer 公共字段也保持旧值。移除已结回执的维护提交不把自身 SHA 写回自身；提交后只读核验，中断按本文 §5 重入。关联任务正常归档只要求本任务交付及归档组已持久化，合法待提交的共享控制记录按设计稿 §4.2 单列；这不授权提交维护组。

维护路径与新任务计划重叠时，先核人选择的独立提交、已完成反向修正或具名任务承接；入口将实际去向写回原回执。承接记录包括新任务批准版本及路径归属，完成后才能从旧维护待处理组解除；仅新建任务或给路径改标签不算承接。操作后实际状态与回执不符输出需人裁决。

## 5. 持久化与恢复协议

### 5.1 内嵌动作描述与幂等键

本文 §11.3 中会写控制状态的具名动作，不论单记录还是跨记录，都在现有主记录的 action 字段先登记意图，不另建事务账本。单记录 task.transition 同样有 action.id；若阶段迁移只是已登记 task.archive/run.advance 等动作的内部步骤，则纳入该父 action 的 targets/steps 和后置核验，不递归建立第二个 action。纯查询/只读断言按本文 §11.3 直接返回结果，不写 action。主记录选择：写权/首次绑定/维护和实例首次创建用 writer，普通任务动作和归档用 task，已有实例推进/批量终止用 run，准备动作使用准备记录（准备记录首次创建同样由 writer 承载）。主记录在动作中途保持不变，不把进度复制/迁移到新记录；关联目标只记录 action.id 作为写入来源。一个未完成动作占有其目标控制字段，后续冲突动作先恢复，不并行覆盖意图。

主记录的具体归属：baseline.apply、spec.update、task.curate、task.knowledge-dispose、task.check、review.launch、review.import、review.decide 与 task.attribute 均使用发起且获批的当前 task；spec.update 的其他任务引用同步是该主动作的窄目标，不在目标任务另开嵌套动作。初始化配置生成也走 baseline.apply，由同一初始化 task 负责；首次任务创建由 writer 承载 task.create，实例内创建由原 run.advance 的固定步骤承载。挂起复评使用当前写者有权触及的任务作为 task.reassess 主记录；维护修复/安装/退出均用 writer 的维护动作，损坏 writer 独立卸载仅按本文 §10.5 的既定例外，不为该例外伪造记录。

所有单记录控制写入也采用意图、原子替换、write_mark 和后置核验，不另造较弱协议。多个动作组合时由一个父 action 固定全部 targets/steps，内部操作按对应固定处理器核后置，不覆盖尚未结束的主 action；不得为了完成同一动作在同一记录递归另开 action。spec/基线的编辑仍可由 AI 在授权内起草，实际已编辑内容作为当前前像/候选，入口的原子恢复承诺覆盖其正式成组应用和关联控制记录，不伪称拦截编辑器的每次键入。

| action 字段 | 类型/用途 |
|---|---|
| `id` | `H("wf-action-v1", C({owner_ref, base_revision, kind, normalized_inputs, approval_ref}))`；owner_ref 为本文 §1.2 所定义 owner 结构的规范 JSON；相同请求重入复用该值 |
| `kind`、`scope`、`decision_refs` | 固定机制操作名、精确对象/路径、人的有效授权引用 |
| `base_revision`、`head_before` | 意图写入前主记录 revision 与可核对 HEAD |
| `inputs_digest`、`targets` | 输入摘要；每目标的定位、预期 revision/受控字段前像、目标字段后像、创建/移动的源目的地 |
| `steps`、`next_step` | 固定有序步骤标识及已核实进度；每步有后置断言 |
| `state` | prepared/applying/persist_pending/done；字段全名为 `action.state`，与 task.phase 无关；done 表示目标后置成立、与 Git 提交无关，persist_pending 仅限含固定提交步骤的动作（终态语义见本节下文） |
| `result` | null 或 `{summary, failure, control_assertion}`；状态动作的 control_assertion 按本文 §11.3 定义，失败时为 null，恢复保留先前已成立事实 |

哈希输入中的 normalized_inputs 包括预先生成并已保存的所有新 id、路径、版本和决策；首次失败重入从意图取这些值，不另生成 id。动作完成后相同参数的新操作使用新的 base_revision，得到新 id；重试必须明确引用旧 action.id。重复消费任务步骤以 run/step 的既有 task_map 为首要定位，不拿新动作 id 建第二任务。

targets 的前后像仅包含本操作拥有的控制字段及必要创建内容；写时从当前原始记录合并，保留未知与非本操作字段。自身 action/revision/write_mark 不放入自身循环哈希；是否为本次写由 action.id 与确定的目标 revision/受控字段联合核验。该数据只是恢复当前动作所需意图，不复制另一个对象长期生命周期。

**action 终态语义**：done 表示该动作的目标后置成立，与 Git 提交无关——未提交状态不构成后续冲突动作的前置，也不使已完成动作回到未完成，门禁核记录内容而非提交状态（对齐设计稿 §4.2 工作区边界）。persist_pending 仅用于提交本身是该动作固定步骤的动作：task.archive 与 run.terminate；此类动作在授权提交完成前保持 persist_pending，其整体后置含该提交步骤，提交后按本文 §5.3、§7.4 的持久化后置派生完成。维护动作不用 action.state 表达待提交：其结果由 maintenance_results 的 result（applied_pending_commit）承载，按本文 §4.5 的可达提交查证派生 persisted。

### 5.2 候选校验、落盘与重入四态

1. 持锁核所有者代次，读取所有涉及记录及路径真实状态；构造完整候选图/终态/映射。
2. 按下述目录核对规则检查所有新 id、目标文件、归档目录、实例快照位置和改名目的地无碰撞；校验候选 DAG、来源、批准范围及写入权限。任一不成立则尚不写意图或状态。
3. 将意图写入主记录后，按固定步骤逐个更新目标；每步先验证前像或识别同动作后像，再原子写与读回，最后推进 next_step。外部文件被改变而不再匹配前后像时停下，不覆盖。
4. 全部业务/控制后置成立后按授权持久化；恢复只补未完步骤，不撤销已提交事实。完成动作保留摘要，再允许下一动作替换当前 action。

| 重入观察 | 处理 |
|---|---|
| 意图存在，目标仍为预期前像 | 执行该步骤 |
| 目标为同 action.id 的预期后像，游标尚未推进 | 只补游标/后置核验 |
| 整体后置成立 | 返回已完成（done），不再产生任务/归档/提交；含固定提交步骤的动作（task.archive、run.terminate）在提交完成前保持 persist_pending，其整体后置含该提交步骤 |
| 意图、目标或提交事实不明/冲突 | recovering，报告待核对事实；经 repair/人裁，不盲重放 |

任务目录名固定以完整 task id 起首，后面可接名称 slug；这是定位约束，活动根的具体布局仍由实现方案确定。创建/改名在锁内枚举活动任务目录和 archive/{YYYY-MM}/ 的直接任务目录名，核本次候选中的 id 重复及目的地占用；不递归读无关归档正文。改名只豁免明确的同 id 源目录，归档移动另核目标精确路径。非规范目录名或无法枚举的目录报告无法完成防撞，由人/repair 核实，不当作空目录。完整记录中的重复 id、目录名与记录 id 不符由周期巡检及被引用时校验发现；发现已知冲突后阻断相关创建/定位。目录枚举仍随历史目录数增长，但不等于全库反序列化，也不增加权威 id 索引。

创建目标原子发布用同文件系统的临时文件与排他目标检查，合法入口在共同锁内避免互相碰撞；外部写入不可完全防护，发布前最后核对占用并在有冲突时停止。单记录使用同目录临时文件、flush/fsync、原子替换，成功后核实际内容；目录移动在同文件系统完成并核源/目的地。必要时同步父目录；实际持久化错误必须报错，不能以原子可见性宣称断电不丢数据。

只读启动遇 action 未完成，只展示恢复事实/候选出口；有写权且该动作授权仍适用时才能补写。启动校验按本节末尾的固定顺序执行，先解决相关未完动作，再计算就绪、挂起复评和可见成功；无关历史不重复执行。

**启动校验固定顺序**：启动时的结构校验按下述顺序逐项执行，每项失败输出对应既有原因码并停止依赖该事实的后续判断，不先写业务文件：① 当前会话绑定与写者类别/标识/代次/准备或维护范围/恢复状态（WF_GENERATION_STALE/WF_IDENTITY_UNRESOLVED）；② 会话写者与绑定的对应（WF_BINDING_MISMATCH）；③ 执行候选唯一性——判定前先对活动任务记录做轻量可读性检查（仅要求能取出 status/phase/paused/suspended 各键，完整 schema/取值解释仍归⑤）：可读则核候选唯一性，多个候选或候选不属写者绑定为记录集不变量破坏（WF_RECORD_INVALID——多候选是非法组合事实而非写权占用事实，出口是按事实恢复或 repair，不是等待写者；候选不属当前写者绑定时另报 WF_BINDING_MISMATCH）；任一活动记录不可读时以“候选未知”上报并在报告中先列该不可读事实（未知优先于判定，不把损坏记录当无任务或零候选；未知态取 WF_HISTORY_UNRESOLVED 并在 facts 写明不可读对象，可确证记录损坏时并用 WF_RECORD_INVALID），完整诊断与出口随⑤的 WF_RECORD_INVALID 给出；④ 维护写者与本次预览范围/操作的对应（WF_WRITER_BUSY/WF_PREVIEW_STALE）；⑤ 本次判定所需记录的 schema/取值可解释，不可解析保留原文（WF_RECORD_INVALID）；⑥ 未结束实例的快照/游标/任务归属及结束中断（WF_HISTORY_UNRESOLVED/WF_ACTION_INCOMPLETE）；⑦ DAG 与被引用归档任务的终态（WF_DEPENDENCY_UNMET/WF_RECORD_INVALID）；⑧ 写者标记，按记录锚点核对（WF_HISTORY_UNRESOLVED）；⑨ 框架资产可用性——installed 入口核 `.wf/bin` 布局与必需资产存在，缺必需资产输出对应入口不可用（WF_CAPABILITY_UNAVAILABLE）；⑩ 未处置保留 WIP 及维护待持久化组：存在按记录登记的未处置组 → WF_WIP_UNRESOLVED；其去向或归属未明 → WF_WORKSPACE_UNRESOLVED（档位由本文 §11.1 码表单一来源，按事实性质选码）。顺序固定使失败报告稳定可复现；判定使用记录事实的步骤在其数据源通过可解释校验或轻量可读检查之前，只允许输出“未知”并列出该事实（未知优先于判定；未知态取 WF_HISTORY_UNRESOLVED 并在 facts 写明不可读对象，可确证损坏时并用 WF_RECORD_INVALID，不据未知出放行或阻断结论）；本段与本文 §2.3 的开工核对序列同源于设计稿 §5.4 的校验项，两者同为“身份/绑定/写权 → 记录结构 → 依赖/资产 → 工作区”的顺序骨架、启动段含启动特有项——同一故障在两个入口的首报项一致（身份与记录问题并存时，两序列都先报身份/绑定类、后报记录类）。各项的判定算法在所属章节（本文 §1.4、§2.2、§4、§6.1、§8.2、§10），本段只固定顺序、覆盖项与出口，与设计稿 §5.4 的启动校验清单逐项对应。

### 5.3 提交、归档与自指消除

Git 操作只在已有明确授权内按精确路径执行。暂存前核工作树/索引差异及所选组，提交前复核索引内容对应已检查对象；其他路径的预暂存变更保持原状，不能让普通 commit 捎带它们。若不能保证提交范围，输出待人处理，不重置用户索引。

归档动作固定步骤：预检终态和目标碰撞 → 保存归档意图 → 写归档终态/时间及已处置等待 → 移动任务目录 → 同步必要实例步骤/相关控制引用 → 写 `task.action.state=persist_pending` 及精确待提交组 → 授权暂存提交 → 只读核对提交与工作树。task.phase 仍为 finish；异常退出保留停止时的合法阶段，不写入动作状态值。最后一步不把该提交 SHA 再写回同一归档记录。

task.action.state=persist_pending 的记录已进入归档提交后，持久化完成按本文 §4.5 的可达提交查证派生：区间下界为该归档动作的 `action.head_before`（本文 §5.1 定义的动作字段：意图写入前的可核对 HEAD；归档动作以 task 为主记录），登记结构为该归档动作登记的终态、目录移动结果与精确路径组登记状态——某个可达提交同时包含这三者即证明该次归档已持久化，保留该检查点不意味着还需再提交一遍。归档组可能含实例记录等共享文件，后续对同组路径的合法推进（游标/任务映射更新等）产生的差异按当前任务/外部变更归属处理，不倒算为该归档未持久化。工作树/索引对该组的额外差异只作“该组当前是否有待处理变化”的独立事实报告，不参与已持久化判定。提交成功但进程未报告时，下次读回相同事实返回完成。任务归档后 write_mark 仍引用写入前 HEAD，不要求它指向包含自身的提交。

每次正常或异常归档的持久化被核实成功后、以及本文 §5.2 的启动校验固定顺序通过后，都触发本文 §6.2 的挂起复评。归档入口先以只读事实确认原归档 action 已结束，再调用 task.reassess；不在已归档任务内追加复评结果，关联未归档 T 的变更由其记录承载并核当前写权范围。复评失败/无写权/无关联写入权限时输出“待复评”及重入出口，不撤销已成立归档，也不伪称清挂起；启动时按原条件补做。复评与归档本身两个结果分别报告，避免为重试复评重复归档或重复提交。

正常/异常归档未完成持久化时，依赖与流程推进保持等待，避免只见 archived 就消费未完成动作。绑定仍保留。归档成功后处理写权释放，其合法待提交公共控制差异按本文 §4.5 单列，不以反复写“已提交”制造无限提交链。

### 5.4 repair 与不可解析记录

repair 先只读汇总对象原文的安全片段、Git 锚点、引用图、写权和已落盘步骤，再给具体候选修复与影响。预览令牌只授权该方案；应用时同锁重核，先确认旧写者停止，恢复能证明的代次/范围，再按 action 受控写入，验证全图/引用及结果。原文保存在预览确认的恢复材料中，敏感内容不进入报告；恢复材料不是新的任务事实源。

代次不可证明时不给常规推进伪造新起点；保留诊断与独立卸载。单记录删除前核活动/归档前置、来源、继任、实例和绑定引用；不能通过删坏记录获得可继续状态。记录原文无法解析时允许人指定可证明事实重建，不要求先能解析才 repair。项目标识重建由 repair 入口在同一动作内生成新 UUID4，并与预览登记的旧值比对，相同则重新生成直至不同，落实设计稿 §3“重建不复用旧值”；同时对旧标识的本机解释器确认记录执行明确失效并保留依据；只有模型代填确认的路径不允许。

完整修复后回执、提交/待提交和释放按本文 §4.5；失败保持恢复检查点。锚点修复只恢复定位，不恢复已失效的批准/Check。repair 不能代替合法日常删边、内容修改或范围批准；例如正常删掉冗余依赖走建删边入口，不算结构修复。

## 6. 依赖、返工、替换与放弃

### 6.1 依赖计算与局部图校验

就绪以任务唯一 prerequisites 为准，查活动成员及被引用归档成员；满足条件为正常归档且其归档持久化已完成（按本文 §4.5 定义的可达提交查证、以本文 §5.3 的归档登记结构派生）。图遍历按稳定 id，DFS 三色或等价拓扑算法检测自环/环；候选图校验在全部写入前完成。无法解析的被引用对象阻断相关子图，不把“未知”当依赖满足。

独立建边由人发起，两端都在活动区且前置未归档；新任务定义可引用已正常归档历史前置。执行中新增前置允许继续当前执行，只挡收尾；首次开工、暂停后恢复和重新 Plan 入 Execute 仍核各自前置。删边仅改未归档持有侧，目标可在归档区，死引用走 repair。

无绑定新会话先按下述独立接续资格过滤，再按 created_at、id 排序给就绪建议，人选择后才 acquire/绑定；有绑定只恢复同对象。就绪是可选择性，不等于已有开工批准。阶段尾任务只是普通任务的人约定，不引入另一项目状态机。

**独立接续资格（所有入口共用）**：task.run_id=null 时可作为普通任务候选；非空时先读取该实例的终态和必要任务映射。在途实例的任务只可由绑定该实例且 cursor.task_id 正确的会话推进，不得直接以 task 绑定选取。实例已异常结束时，只有 task.independent_resume 非空、其 decision 明确保留本任务、termination_action 对应实例已持久化的终止动作，且实例处置摘要与任务许可一致，才可在新会话独立接续；正常结束实例没有未完任务可借此恢复。未知、缺失、冲突或 closing 未完成只诊断/恢复，不当作独立任务。历史 run_id 保留，不因独立接续置空。

首次绑定候选过滤、writer.acquire/handover.accept、开工/恢复、本文 §5.2 的启动校验和 Check/Finish 都调用同一资格判断；它只授予选择当前对象的资格，仍须核暂停、依赖、批准与写权。合法保留任务后续完成不重开原实例；无许可直接选择在途任务输出 WF_BINDING_MISMATCH，记录事实未明输出 WF_HISTORY_UNRESOLVED。周期巡检按本文 §8.5 检查“非保留任务绕过实例独立执行”的历史非法组合。

### 6.2 返工与挂起复评

人确认 T 缺陷与 R 范围后，在 T.action 登记完整候选：R 继承 T 的原前置与 rework_of=T，T.prerequisites 增 R 且 suspended=true；先预检 R 目标碰撞和候选图，再固定 R id。落盘顺序为创建 R 规划记录 → 更新 T 挂起及前置 → 同实例时更新 task_map/sequence_changes → 验证后置。未完成动作阻止 R 提前执行或 T 清挂起。

同实例在 sequence_changes 保存 R 的原步骤、source_task=T、resume_task=T，cursor.task_id 临时定位 R，T 不自动 paused；R 完成并复评后，按已登记返回目标恢复 T，T 仍等待其他返工时仅报告等待。嵌套返工按这些来源引用恢复最近尚未完成的返回目标，不成为用户可编程的嵌套工作流。普通任务绑定则 T 显式暂停、保存交接/工作区并 release，新会话绑定 R。R 仍须独立批准与开工，不能消费 T 的批准。

返工集合由所有 rework_of=T 的活动和归档记录重建。复评条件为 T 未归档且挂起、集合非空、集合无未归档成员、T 前置全部满足，且相关跨记录动作已恢复（上位依据：设计稿 §5.4 失败/中断先恢复，不先清挂起掩盖残留）。清 suspended 保留 paused；若会新产生第二候选则同时 paused=true、记等待人恢复。多个 T 按 created_at、id 排序逐个应用，后续使用更新后的候选集。

复评仅在当前持写权且目标属于必要关联控制写入范围时执行；未持权只报告待复评，原 T 会话取得写权后可补做。它不是让 R 会话修改 T 业务内容的权限。R 异常归档不会自动满足 T 的前置；按已确认删边/重连后才可能清挂起。

### 6.3 替换

输入为未归档、暂停已处置且未挂起的 T，继任者 S 的规划/继承路径与人的替换决定。预览固定 S id、原前置、来源提交/路径、返工来源、下游重连和仍执行实例映射；人确认 S.touch_paths 覆盖继承路径，不覆盖则保留原态并回规划。

T.action 内先验证完整候选图和所有位置，再创建 S 的规划记录、登记继承、修改必要下游前置、更新在途实例映射，最后按异常归档处置 T。各中断窗用同动作前后像恢复；T 已异常归档后不回退正常。S 开工仍须自己当前版本批准，继承历史触碰面不是开工许可。

已结束实例留下的保留任务替换时，S 是独立普通任务，只引用来源，不重新加入原实例。普通会话绑定仍是 T，T 结束后新会话绑定 S。

### 6.4 放弃与改动去向

对任一未归档 T，人可先决定停止；该决定立即冻结业务，不依赖原规划批准、Check、前置或返工成功。预览列未完返工、下游、尾任务职责、已有提交与未提交改动；每项给保留现状/反向修正/具名承接的实际去向，无改动显式记载。

disposition.pending 记录未落实项；待决时不继续业务，也不提前归档。未提交改动须已授权提交或由人实际处置；同对象收工 WIP 的例外不扩张为放弃后遗留无主 WIP。停止决定可先保存，结案等实际处置；人仍可暂停释放，但工作区限制继续生效。

候选图允许下游/返工保留合法阻塞边；只有另有人确认才删边、重连或放弃这些对象。阶段目标保留则指向具名承接任务；明确撤回目标可不造替代任务，但不能宣称阶段已完成。归档时暂停/挂起以“放弃取消”历史处置，terminal=abnormal；只报告退出完成与保留风险，不报告业务验收通过。

## 7. 用户工作流与实例

### 7.1 有限定义格式

`.wf/user-workflows/<workflow-id>.md` 使用唯一 `<!-- wf-definition:v1 -->` 标记，其后紧邻一个 `json` 代码围栏承载机读定义，余下 Markdown 为说明。通用入口只解析该块，不求值 Markdown/输入。workflow-id 与 step/action/output 的局部 id 使用 `[a-z][a-z0-9-]{0,63}`；这是引用标识编码，不限制业务路径的字符集。

| 字段 | 类型与语义 |
|---|---|
| `format_version` | 整数 1；未知版本不可实例化 |
| `workflow_id`、`content_version` | 稳定局部 id；正整数，每次源内容改变递增；快照哈希同时覆盖完整文件 |
| `purpose`、`applicability` | 非空文本；人的用途/适用性判断，不作表达式求值 |
| `inputs` | 名称 → `{type, required, description}`，type 为 text/path/artifact_ref/secret_ref |
| `steps` | 有序非空数组；每步为下述 task 或 human；id 全局唯一 |
| `completion` | 非空完成条件说明数组；结案核已满足的事实/人判，不从自然语言自动判真 |

设计稿要求的定义级“必要验证”由各任务步骤的 verifications 共同承载，completion 引用这些步骤的实际满足结果，不另在定义根复制一份验证清单。跨步骤整体验证须在末尾适用任务步骤明确声明其来源与所需前序产物，进入该任务批准规划并执行；只写 completion 自然语言不能替代必要验证。未明确承载步骤的必要验证使静态校验不完整，先完善定义，不让解释器猜测放到哪个任务。

共同步骤字段：`id`、`type`、`title`、`inputs`、`outputs`、`required`、`skip`、`human_points`。required 默认 true；skip 在必需项为 null，可略项为 `{condition, decision_point, downstream: [{consumer, output, mode, replacement}]}`，mode 为 unused/replacement，replacement 必须有合法来源。condition 是待人判的自然语言条件，不是代码或隐藏条件跳转。human_points 为 `{id, question}` 数组，id 在本步骤内唯一且禁止以 `plan-q-`、`debug-ruling-` 起始（保留前缀约束使本文 §1.3 的人判点 id 来源仅凭前缀即可区分，静态校验拒绝违例 id）；task 级问题在 Plan 完成、开工前处理，action 级问题在该动作完成前处理。可与同对象的规划批准等已有确认合并记录，不增加内容相同的重复问答。

task 步骤另有 `task_kind`（ordinary/initialize/bootstrap）、`goal`、`acceptance`、`actions`、`verifications`。actions 为有限有序 `{id, text, inputs, outputs, required, skip, human_points}` 数组；它只是单任务内的工作说明，不能产生新步骤类型或绕过四阶段。human 步骤有 `question`、`choices` 和答复记录要求，允许输出人的文本决定，不修改交付物、不承载业务命令。skip.decision_point 引用相应步骤/动作声明的人判点；答复保存实际决定及适用快照哈希，任务内部人判进 task.execution，独立人判步骤进实例结果。

输出声明为 `{id, kind, path, description, required}`，kind 取 delivery/step_artifact：delivery 路径相对项目根，step_artifact 相对本实例/步骤专属产物根（布局由实现方案固定并记录解析后的真实路径）。path 是具体安全路径，或 `{input: name}` 指向 path 类型输入，不拼接任意模板表达式；解析结果均核本文 §3.1 边界。不同实例的 step_artifact 不能解析到同一路径，delivery 的共享路径仍逐任务批准并纳入 Check，不因放在 `.wf/` 而排除交付。输入引用的唯一取值域如下；工作流 inputs[].type 表示输入值类型，from 表示该值的来源，两者不互相充当枚举。所有消费者只接受本表结构，不在 PRD/检查记录另扩 from 值。

| from | 结构 | 可用场景与解析 |
|---|---|---|
| input | `{from: input, name}` | 工作流任务/动作引用本实例已声明输入，按其 type 校验 |
| project | `{from: project, path}` | 普通任务及工作流，path 是已授权的项目相对路径，核真实文件和边界 |
| secret_ref | `{from: secret_ref, provider, name}` | 普通任务及工作流，provider 只取 env/host_store，name 是已配置秘密入口名；只保存引用，宿主传递值不进入 argv/日志/记录 |
| step | `{from: step, step, output}` | 工作流引用严格早于当前步骤的已声明产物，来源身份为前序步骤产物；消费按本节统一消费规则解析 |
| action | `{from: action, action, output}` | 同一工作流任务内部引用前序动作的已声明产物，来源身份为同任务前序动作产物；消费按本节统一消费规则解析 |

**统一消费规则**：上表 from 引用的消费方分三类——步骤输入（from: step）、动作输入（from: action）与验证来源（source: prior_step 的 stored_in: step_output），三类同用一条替代语义。解析时先核来源实际结果：来源正常完成则核验被引用产物本身；来源为合法略过且略过决定中已确认对该输出的替代映射（skip.downstream 的 replacement）时，改为核验替代来源声明的真实产物就绪并固定到当前任务批准验证材料；来源既未正常完成、也无已确认替代映射才阻断。“来源实际结果”按消费方身份取值：步骤输入取来源步骤在实例 step_results（本文 §1.5）的结果，动作输入取该动作在 task.execution.actions 的结果；验证来源按 established_by.action_id 定位来源身份——action_id 非空时定位到该具名动作，同时核前序任务的合法完成事实（由 task_map 解析）与该动作在前序任务 task.execution.actions 中该动作 id 的结果、其略过决定及已确认替代映射（略过决定的人判答复保存于前序任务 task.execution、动作结果行记 skipped，替代映射为该动作 skip.downstream 的 replacement），合法略过与替代分支按上述统一规则执行；action_id 为空时使用步骤级结果，即前序任务的实际完成事实（由 task_map 解析实际产物）。替代产物核验等同原产物，验证强度不降；验证来源走替代时的具体强度要求见下文验证声明段。

普通任务仅接受 project/secret_ref，因其没有实例 inputs/步骤/动作引用上下文；工作流按顺序边界使用全表。工作流创建时 type=secret_ref 的输入值采用本表 secret_ref 对象，type=artifact_ref 的值采用可解析的 project/step 引用；type=path/text 分别为安全路径/文本。通过 from=input 取得秘密引用后仍按 secret_ref 对象处理，不解析为要落盘的明文。秘密不可用仅报告引用名与缺失事实，不要求抄入定义/快照/实例输入；具体秘密通道由宿主能力及当前授权确认，不提供秘密通道的调用不能改用 argv。

验证声明保存 `id`、`source`、`established_by`、`stored_in`、`consume_at`（start/check/finish）。建立者与落点采用下表带类型引用，禁止把步骤名、任务 id 和自由文本混用；静态校验核类型和来源顺序，消费前解析为具体任务/文件/验证声明并固定版本。

| source | established_by | stored_in 与解析 |
|---|---|---|
| existing_project | `{kind: project}` | `{kind: project_file, path, verification_id}`；path 是已有基线或已有验证说明文件的项目相对路径 |
| current_plan | `{kind: current_task}` | `{kind: task_plan, verification_id}`；在该步骤生成任务后，取其已批准 PRD 块的 verifications 项；不是源定义的步骤 id |
| prior_step | `{kind: step, step_id, action_id}`；action_id 可为 null | `{kind: step_output, step_id, output_id, verification_id}`；建立者必须是更早的任务步骤，action_id 非空时须命中该步骤声明的动作；落点必须是同一步骤声明的产物 |

project_file/step_output 的验证说明在对应文件内使用唯一 `<!-- wf-verifications:v1 -->` 标记与紧邻 JSON 块，内容为 `{verifications: [...]}`，各项复用本文 §2.3 的验证项格式；该块附着既有基线/声明产物，不另建命令注册库。prior_step 可在创建时尚无实际文件，但必须有建立者和产物声明；消费按本节统一消费规则解析——前序正常完成时由 task_map 解析其实际产物，前序为合法略过且已确认对该产出的替代映射时按替代来源核验，替代文件本身仍须带 `<!-- wf-verifications:v1 -->` 块、来源合法，其调用纳入当前任务批准并实际通过必要验证，验证强度不降；两者皆无才阻断。current_plan 的条目可以在任务 Plan 中补齐，但开工前必须落入批准版本。缺项、重复验证 id 或引用错位即阻断，不能用同名其他任务的声明补位。

消费任务把解析后的来源定位、版本/哈希和实际 invocation/cwd/input_refs 固定在本任务批准验证材料中；源声明只说明调用从何而来，不授予执行权。consume_at 指核对声明与就绪事实的时点，必要业务验证仍纳入 Check；到 Finish 才发现新增必要检查时回 Check 完成，不用待执行的 Finish 命令证明先前 Check 已通过。人调用 finish 的决定另存 finish_decision，不作为一个预先必需的 manual 检查制造循环。项目既有脚本仍以批准的固定调用执行，不把流程输入拼入 shell 正文。

下例是一个完整的定义文件，由 `<!-- wf-definition:v1 -->` 标记与其紧邻机读块构成，可直接复制到 `.wf/user-workflows/` 按本节规则解析校验；示例为存量项目的单任务定义，实际任务仍需批准验收与命令，示例不声称项目测试已存在：

<!-- wf-definition:v1 -->
```json
{
  "format_version": 1,
  "workflow_id": "bounded-change",
  "content_version": 1,
  "purpose": "完成一个已限定范围的变更",
  "applicability": "已有项目基线与配置",
  "inputs": {"request": {"type": "text", "required": true, "description": "人的变更要求"}},
  "steps": [{
    "id": "change", "type": "task", "title": "实施变更", "task_kind": "ordinary",
    "inputs": [{"from": "input", "name": "request"}], "outputs": [],
    "required": true, "skip": null, "human_points": [{"id": "approve-plan", "question": "是否批准当前规划与复杂度？"}],
    "goal": "按输入形成规划并完成获批变更", "acceptance": ["当前批准的验收项实际通过"],
    "actions": [{"id": "work", "text": "在当前任务批准范围内实现并验证", "inputs": [], "outputs": [], "required": true, "skip": null, "human_points": []}],
    "verifications": [{"id": "task-check", "source": "current_plan", "established_by": {"kind": "current_task"}, "stored_in": {"kind": "task_plan", "verification_id": "task-check"}, "consume_at": "check"}]
  }],
  "completion": ["change 对应任务正常归档"]
}
```

### 7.2 准备、静态校验与创建

未绑定 start 在人批准精确定义路径后取得 preparation scope，创建/编辑定义并保存校验结果、版本和待决项。静态校验依次检查格式/schema → id 唯一（含 human_points id 的保留前缀约束：禁止以 `plan-q-`、`debug-ruling-` 起始，见本文 §7.1）→ 引用来源与顺序 → 路径 → 必需/可略及替代 → 完成/验证/人判声明。必需/可略及替代环节同时核替代映射的下游一致性：可略项声明的 downstream.consumer 须指向定义中实际存在的下游消费方（消费方所属步骤/动作的 id 或验证声明的 id），replacement 须为合法来源引用且静态可核；步骤输入、动作输入与验证来源三类消费方均适用本文 §7.1 的统一消费规则，不设某类默认不允许替代的暗规则——未来若要禁止某类消费方使用替代，须在静态校验显式拒绝，避免定义通过静态校验后才在消费时被另一套规则阻断。静态校验不要求未来产物已经存在；但待解析验证必须声明建立者、持久落点与首个消费时点，不能用无来源自由文本占位。

准备结束或取消可以保留未通过草稿，记录真实 WIP 并按设计稿 §4.4 释放；未通过草稿不能创建实例。要由该会话接着创建实例，先完成准备工作区处置；保留未提交草稿不自动满足换对象边界。

创建输入为所选定义确切版本/哈希、绑定后的实际输入、人确认的步骤适用性与展开规则。锁内重核定义未变、身份未绑定、写权/工作区合法，以及无基线时首任务自举约束；预检 run/快照/绑定目标碰撞。先在 writer.action 保存固定 run id/快照摘要及全部目标，再落完整快照、run 记录、绑定和 holder 范围，验证后置；成功仅取得规划权限，不自动批准业务。

静态有效的定义仍可能在消费时阻断；例如前序应产命令声明但实际缺失，应停在相关步骤而非用备用命令替换。未知来源、输入缺失与类型不支持是阻断；授权/语义不明为需人裁决。

### 7.3 推进与任务映射

每次推进先核绑定、本文 §6.1 的实例/独立接续资格、writer、固定快照/格式、未完 action 与 cursor，再核真实输入、前序完成事实和验证就绪。首次到达 task 步骤时：读取 task_map → 若无映射，预生成 task id/规划目录 → 校验上一未略过 task 步骤的正常归档继任者 → 在 run.action 固定新任务和顺序边 → 创建 task(run_id=本实例) → 写 task_map → 定位新任务 Plan。重入从固定 id 与映射找回，不新建第二份。

顺序前置只直接引用上一未略过 task 步骤的正常归档任务；human 步骤不生成任务边。额外前置、返工、替换按本文 §6 的人发起动作处理。整个任务四阶段完成且归档持久化可核后，才记录该步骤 satisfied 并推进 cursor。已有产物核条件通过可记复用，但任务 Check/finish 仍执行。

actions 的判定进度与人判保存在所属 task.execution，叙述与证据引用保存在 handoff/检查材料中，实例只引用任务事实；脚本核必须动作的结果/必要验证留痕，AI 在批准范围执行工作说明。cursor.task_id 为受控返工 R 时只执行 R 及既定返回定位，不把 R 归档当作原定义步骤完成。结果不明的业务命令先查真实产物与结果，控制动作幂等不授权重放业务副作用。

可略步骤在生成任务前先处理 skip.decision_point，人确认条件与下游替代成立后在实例 step_results 保存决定并记 skipped，不为保存答复强建任务。已生成 task 则先明确放弃/替换及改动去向，未完对象不能被游标绕过。必需步骤变更必须按定义版本迁移/退出路径处理；口头略过不放宽框架 required 门禁。可略 action 同样要核其下游使用，不能把必要测试编码成可略业务动作。下游引用解析按本文 §7.1 的统一消费规则执行（来源正常完成核原产物；合法略过且已确认替代映射则核替代来源声明的真实产物就绪并固定到当前任务批准验证材料；两者皆无才阻断；三类消费方同用该规则），替代产物核验等同前序产物，不降低验证要求。

### 7.4 正常结束、异常终止与迁移

正常结束核所有必需步骤满足、可略项合法、关联任务终态一致及人判齐全；保存 closing.mode=normal，核真实工作区后写 terminal=normal、ended_at 与 `run.action.state=persist_pending`，再按授权提交并只读确认持久化完成，最后释放。任一提交中断按本文 §5.3 的同一完成判据恢复，不在提交后追加尚未持久化的终态。任务 finish 调用由人实际完成，实例结束入口不代调。

异常终止可从任意未结束实例发起。锁内核身份/写权后保存人停止请求与 closing.mode=abnormal，逐个列出已生成任务、返工/继任者、未生成步骤、已有改动、外部依赖。人一次确认批量计划：放弃者走本文 §6.4，保留者在其任务记录写 independent_resume；执行中保留者先 paused，未开工者保持原 status，挂起/前置如实保留；未生成步骤记 not_executed，不创建空壳任务。

先校完整候选终态/图/改动处置，再按固定顺序逐 task 应用、保存实例终态及处置摘要、授权持久化、释放。若改动未落实，保持 closing 与待决，不恢复业务；写权无法核实时只读接收停止请求，待恢复后再写。中断后已归档的 task 不再次放弃，保留任务后续在新会话独立接续，不更新旧实例终止快照。

编辑定义只改变下一次选择，不改既有快照。采用新执行语义时，先终止旧实例并处置未完任务，再由新会话新建实例；可只读引用旧产物并重新核验，不能认领旧 task 或直接套旧 cursor。纯文字修订仍生成源内容版本/哈希，实例无需迁移。

## 8. 配置、执行器与本地知识

### 8.1 项目配置与缺省

`.wf/project-config.json` 的首版 schema 为下表。发行骨架包含缺省而不是占位；初始化/接入由批准提案生成实际配置。后续通过 baseline 子操作成组应用变化文件，升级保留项目数据。

| 键 | 类型/缺省 | 消费与非法出口 |
|---|---|---|
| `schema_version` | 正整数 1 | 配置解释版本 |
| `project_id` | UUID4；初始化随机生成，不在骨架给值 | 本机解释器确认匹配；repair 重建生成新值后与旧值比对、相同则重新生成；缺失只阻断依赖身份的判断 |
| `python_executable` | 可选路径，无缺省值 | 本文 §8.2；设置但失效不得向下回退 |
| `tdd_default` | 布尔 false | Plan 按项目缺省提出任务取值，人批准 |
| `review_file_hint`、`review_line_hint` | 正整数 3、80 | 提醒复评复杂度，不自动分类 |
| `split_file_hint`、`split_line_hint`、`merge_line_hint` | 正整数 8、400、10 | 体积提示，不自动拆合任务 |
| `debug_repeat_threshold` | 正整数 3 | 机械检测的累计口径：同一 verification_id 的双源合并 failed 累计（check_history 中该 id 的 failed 最终结果条目数与 execution.debug_declarations 条目 counted 之和，合并与判重规则唯一见本文 §1.3，触发集合重建按本文 §11.2）达到阈值时，产生一项 WF_SEMANTIC_DECISION 待决项（待决事实：该合并累计是否属同一问题重复调试），不直接触发复盘；返工、审查失败两类机械触发的语义本就机械可判，维持直接触发。每次 Check 每声明只存最终结果、修复重跑形成新 check.id；裁定留痕按本文 §11.2 的 debug-ruling 条目（execution.human_decisions），再触发节奏按本文 §11.2 整数倍口径，事实全部从既有判定记录重建，不新增计数账本 |
| `spec_verify_days` | 正整数 90 | 到期与 extracted 分流 |
| `spec_reclaim_tasks` | 正整数 5 | 回收统计窗口 N |
| `inspection_every_tasks` | 正整数 10 | 正常归档累计数整数倍触发巡检 |
| `spec_output_codepoints` | 正整数 12000 | 每次 spec 加载/输出响应的软预算 |

无完整配置的自举仅使用对应版本骨架的非身份参数；project_id 在初始化落盘时生成。旧 schema 缺失非授权类新增键可按版本表取发行缺省并可见报告；未知/非法键不静默当无限或 false。项目标识 clone/复制沿用，目录移动不重建；purge 后新初始化产生新标识，repair 重建按设计稿 §5.5 显式失效旧确认。

### 8.2 执行器选择与确认

用户层配置目录固定为当前操作用户主目录下的 `.wf/`，全局配置固定 `~/.wf/config.json`；解析用主目录 API，不把字符串中的 `~`/变量当作可执行展开。首版配置为 `{schema_version: 1, python_executable?: 绝对路径}`，无文件等于未设置该键，未知字段保留但不赋予能力，已设置非法值按配置错误处理。解释器确认集合的具体文件名仍由实现方案确定，但必须独立于 config.json 且同属该用户目录，保持人写入和多元组并存约束；不为每项目复制一份用户配置。

解析顺序固定为项目键 → `~/.wf/config.json` 全局键 → 系统 python3，按“已设置”选唯一候选。全局值仅绝对路径，项目值可相对项目根，拒绝变量/命令片段；相对路径经真实路径解析后仍按设计稿身份规则记录。缺失键与空串不同：空串是非法配置，不能退回系统。

普通引导仅定位目标、读配置、取候选存在/可执行/大小/mtime_ns 与路径身份，查本机确认集合；不自动执行未知候选探测。已确认候选按完整元组匹配，项目相对路径取解析后相对项目根位置，解析落在外部时取真实路径；绝对路径取真实路径。项目键的确认还核 Git 侧批准中的键名与原配置值。

本机确认集合的单项为 `{scope, project_id, key, config_value, path_identity, size, mtime_ns, python_version, confirmed_at}`：scope=project/global/system，global/system 不按项目保存，project 必须带项目标识；system 的 config_value 记系统查找出的可执行定位。系统候选首次解析使用前若没有匹配确认记录，或后续解析发现元组失配，均输出 WF_EXECUTOR_UNCONFIRMED，阻断依赖它的常规操作并提示人执行确认子命令；不因它来自系统 PATH 就自动确认。确认动作为人显式调用的执行器确认子命令，属引导层例外（与独立 repair/uninstall 的启动例外同构）：仅写用户层 `~/.wf/` 的确认集合、只读项目配置，不写项目数据、不进项目锁；首次解析输出 WF_EXECUTOR_UNCONFIRMED 时，出口提示人执行该确认子命令，确认后重入原操作。该子命令自身由引导解释器（系统或人显式选择的可用 Python）拉起，不算引导越权。确认时由人在终端显式执行动作，启动候选 `--version` 并核 Python 3 及最低小版本，写集合中的新元组，不覆盖其他 clone 的条目。集合持久化于用户层标准 wf 配置目录的独立确认记录，具体文件名由实现方案固定；模型不写或代填。

日常可观测匹配不重新探测版本；确认记录的版本作已知值。二进制大小/时间/解析身份变化即失配，需人再次确认。相同大小/时间戳的替换可能无法发现，属于设计稿已声明的非防伪边界；venv 包变化而解释器元数据未变不影响只用标准库的框架。系统 Python 被替换同样需要重新核对，不能把 PATH 名称当永久身份。

已设置候选失效输出确认为当前/改为已批准候选/合法回到未设置的出口，项目键变更走原批准通道。系统 Python 缺失且两级键未设时，由人配置已有全局键后重入。独立 repair/uninstall 可用系统或人已核实的绝对 Python 直接启动；引导解释器仅负责转交，不继续普通业务判定。

installed 入口从自身真实位置核 `.wf/bin` 与项目根；源码/重取恢复入口使用人给的目标绝对路径。未知目标或布局先诊断。最低版本与锁平台不支持时停止依赖操作，独立恢复仍需满足其可运行解释器与最小互斥条件，不宣称任意系统都可恢复。

### 8.3 spec 元数据、策展与读取

spec frontmatter 使用 `---` 分隔，内部采用标准库可解析的受限形式：每行 `key: <JSON值>`，key 为固定 ASCII 名称，字符串双引号、数组为 JSON 数组、整数为十进制；没有多行 YAML、alias、tag 或隐式类型。未知键保存原行，重复键/不支持结构可见标不可解析。只对本框架 spec 使用此格式，不要求改写其他流程规范。正文 Markdown 不作程序执行。

首版字段：`paths` 为字符串数组；`status` 为 template/active/disabled；`verified_at` 为合法日期或 extracted（template 可为 null）；`schema_version=1`；`author` 为 human/ai；`counterexample` 为非空字符串或明确模板标记。active 才参与规则加载，模板不是已核实知识；extracted 永久待核实直至人实际核验转日期。

合法组合：active 的 verified_at 必须为日期/extracted，counterexample 必须有实际内容；template 可用 null/模板标记，disabled 保留停用前的证据值而不参与当前路由。只有人实际核实的动作可将 extracted 变日期；单纯编辑/改名只改内容版本，不自动刷新核实时间。

`author` 只影响复核排序，不改变真伪或门禁结果：同一检查周期内，若多个命中规则都到期或存在冲突，复核队列先列 `author=ai`，再把 extracted 列在日期项之前、日期项按 verified_at 升序，最后按路径字典序排序；human 条目仍必须按同一到期和冲突规则处理。排序结果只写当前巡检报告/读取顺序，不写可变优先级到账本，也不允许用 human 身份跳过核实。

task.curate 由当前任务入口在同记录 action 中把选择的 path/digest/purpose/time 写 task.curation；Plan 从索引选，Execute/Check 新发现时补充。运行读取只写当前会话侧车 `{spec_path, digest, read_at, complete}`；侧车完整读取以输出全文为前提，不把提醒/摘要标为 complete。侧车写失败可当次重读并可见报告，由当前入口核全文已交付；不因缓存不可写永久阻断。但未获得完整正文仍保持相关门禁未满足，新会话必须重读。

当前依赖以未解除条目的逻辑路径去重，digest 表示选用时的内容而非锁定旧规则；正文变化时读取当前文件并由策展入口刷新已选版本，原事实由写入标记/Git 追溯。已选路径不会因自动匹配结果减少而被删除，解除条目也保留历史引用。无写权会话只能读新版并写本会话侧车，持久策展更新等取得写权后再执行。

按真实路径匹配后，排序键为：精确匹配优先；字面段数降序；通配符数升序；模式长度降序；spec 路径字典序。窄规则不推翻宽规则的禁止项；语义冲突需人裁决。无合法 paths 的策展项仍需读，不因自动匹配不到而消失。

### 8.4 预算、变更与统计

`spec_output_codepoints` 是同一个“spec 加载/输出软预算”，同时约束一次响应中为本次加载形成的正文装载和对用户/执行器输出的总量，不是只限制展示。它计标题、路径/版本标签、正文、索引、提醒与汇总的 Unicode 码点数（换行也计数）；运行诊断单独输出，不借诊断通道隐藏被截断内容。流程/基线/配置/skill 正文不受该预算裁剪。多文件超预算先减少本批、分文件输出，单个必需文件超预算则整文件超额输出并明示；正文未完整时 complete=false，依赖前再读全。预算计数不改变文件内容，也不把一次分批读取拼成未经记录的完整读取。

spec 变更前取现有文件、索引、活动策展与本地证据，批准范围内编辑；改名同步活动引用路径/哈希，旧归档按历史解释；删除前每个活动引用须有人的 released 决定。同步是固定职责窄写入，仅修改引用路径/哈希/解除标记，其他任务批准与目标保持不变。成组动作统一为当前发起 task.action 的 spec.update，按本文 §5 预检目标文件、索引和全部关联任务策展字段并恢复；关联任务仅合并许可的引用字段、不覆盖其已有 action，若目标有未完冲突动作则先恢复，不并行叠写；读取缓存保守失效；涉及本任务检查输入的变化回 Check，不能为保持 pass 排除整个 `.wf/`。

| 知识操作 | 候选结果与关联写入 | 通过/拒绝的决定性条件 |
|---|---|---|
| 新增/更新 | 准入依据、正文/metadata 与索引三段一致；当前任务知识处置保存前后路径/哈希 | 有真实约定及消费者可准入；模板/空泛建议不作 active |
| 拆分 | 人审各新规则族及旧文件保留/停用/删除决定，逐项 paths/index；需要删除旧文件则先解除旧活动依赖 | 只改结构且引用处置明确可应用；不能自动把其他任务改依赖全部新文件 |
| 合并 | 人裁冲突与目标规则，索引单一入口；每个旧文件按实际保留/删除处理 | 决策与引用齐全才应用；同路径冲突未裁决不覆盖 |
| 改名 | 先检查目标碰撞，再更新文件、索引与活动策展路径/哈希 | 旧归档按历史路径解释；不因改名强改历史任务 |
| 删除/停用 | 人决定去留；仍需当前规则的活动任务须明确解除或指定替代；替代策展由所属任务按其权限维护 | 未解除的活动依赖阻断删除；停用不能绕过必要规则的读取/依赖判断 |

index 与 metadata 同步是这些操作的后置，不单靠文件写成功判完成。知识变更记录的 changes 每项为 `{operation, old_paths, new_paths, before_digests, after_digests, reference_dispositions}`，其中改名/合并映射供本文统计回扫；不另造可变引用计数。

核实到期计算为 UTC 当日距 verified_at 的天数达到 spec_verify_days；未来日期或非法日期报需核对，不能用未来日期绕过。extracted 单列依赖未核实，经 finish 人接受才完成诚实处置，必要业务验证仍不可豁免。人的长期约定可作为准入证据，不要求先发生失败。准入/合并/删除决定及最近正反例由 task.knowledge-dispose 写入 task.knowledge 的处置记录并引用实际证据，人判语义不由 metadata 合法性代替。

周期清点是本文 §8.5 巡检中的知识治理部分，报告名称固定为“策展引用统计”；共享同一次记录遍历，从活动与归档 task.curation 重建引用，连同过期/extracted、路径漂移和需人工比对项输出。它统计任务选用/引用，不称“实际加载次数”，读取侧车清理/丢失不改变结果。历史曾选用但当前已解除仍计为该次任务引用，活动依赖阻止删除只看未解除项。计数与触发统一由巡检定义，不在知识清点另维护一份节奏或累计数。

回收看该 spec 存在期间最近连续 N 个正常归档任务的完整清单且无当前活动依赖；窗口中任何一次引用即不列回收候选。存在起点、改名/合并映射从 Git 与知识变更记录核对；缺清单、样本不足或映射不明报告未知。候选只供人决策，删除仍走引用解除与准入/去留判断。`.wf/out-of-scope/` 一概念一文件，重提追加旧记录；临时困难放 task.handoff.pending，不伪装持久拒绝。

### 8.5 周期巡检

触发为人发起，或正常归档累计数达到 inspection_every_tasks 的整数倍；阶段收尾伴随人的主动意图，由“人发起”承载，不设“阶段尾任务归档”触发。累计数按 archived_at、id 排序，从归档记录重建，异常归档不计也不重置，人工巡检不改计数；无持久计数标记。普通 start 仍按需读归档，只有本巡检可执行全库一致性遍历。只读巡检无项目写权前置；若要持久报告、更新知识或 repair，分别取得对应写权和授权。

一次遍历建立仅存内存的 task/run/binding 引用视图，包含活动与归档记录，按下表检查；相同记录只解析一次，知识统计复用此视图。非法记录保留并报告相应检查未知，不当作零引用或无任务。报告含对象、记录版本、事实和出口，不自动修复。

| 检查类 | 必查对象与断言 | 失败处置 |
|---|---|---|
| 归档引用 | prerequisites/rework_of/successor_id、实例映射、历史绑定和 independent_resume 的被引用对象及可用历史锚点 | 缺失/冲突交本文 §5.4；正常历史路径移动按稳定 id 定位 |
| 终态 | archived 的 normal/abnormal、时间及归档持久化、暂停/挂起处置；实例 terminal/closing 与任务许可的一致性 | 非法组合或未完成动作给恢复/repair，不重开旧任务 |
| 重复 id | 全活动/归档记录 id、目录 id 对应、同 id 多位置与实例/绑定冲突 | 列全部冲突位置，拒绝相关定位；不删记录取巧 |
| 知识治理 | 当前 spec/index/metadata、过期/extracted、策展引用/路径漂移/改名映射、按 paths 交集生成的“需人工比对”清单、缺链/孤儿页/已知被新证据替代的断言、回收候选及 author 复核顺序 | 按本文 §8.3 核结构/加载，按本文 §8.4 在授权内修正缺链、维护索引及处置孤儿/被替代断言；结构损坏交本文 §5.4，语义去留交人裁决 |

“需人工比对”按稳定 spec 路径对去重，每项含双方文件/哈希、参与比较的合法 paths、分类及依据；比较使用本次有效 active spec 的合法模式和同一次巡检的项目路径范围。分类只取 witnessed/potential，显示名分别为“已证实交集”“待核实的潜在交集”，算法顺序固定如下：

1. 按本文 §3.1 匹配本次巡检可读的合法仓库路径，记录路径→命中 spec 的关系；任一同路径同时命中两份规则即生成 witnessed，列出见证路径及对应模式。它证明当前适用范围相交，不证明内容矛盾。
2. 对没有当前见证的 spec 对，逐对比较模式的**完整字面前缀段**：从根起只取遇首个含 `*`、`?`、`[` 段之前的普通字面段，整个 `**` 段也在此前停止；`[` 未闭合时亦保守停止，不据其特殊解析得出不相交。若两个前缀在共有位置出现不同字面段，这一模式对可证明不相交；否则只记“不能排除重叠”，不宣称精确求交成功。仅当两份 spec 的全部合法模式组合均已按此前缀规则证明不相交时，才可从比对候选中排除该 spec 对。
3. 其余无当前见证的 spec 对均生成 potential，附未排除的模式组合及“前缀检查不能排除、无当前路径见证”的依据；将来可能命中的组合不会因目前没有文件而被静默忽略。没有合法模式、非法项、不可读/边界外路径或未完成的扫描单列未核实对象，不当作模式不相交；无 paths 的显式策展知识不凭空推断路径适用范围，仍参与既有准入/引用检查。

报告同时列扫描范围、候选总数与 witnessed/potential 数量，宽 glob 产生大量 potential 时可按稳定文件路径对分页展示，但须显示尚未展开的数量及完整清单出口，不按预算默默删候选。它不实现任意 glob 的精确语言求交，potential 可能为保守多报；例如无现存文件的 `src/**` 与 `**/*.md` 列 potential，现有 `src/a.md` 同时命中则列 witnessed；`src/**` 与 `tests/**` 的首段不同可排除。两类都不判定语义矛盾，也不以“疑似冲突”替代人工正文判断；两份互补规则命中同一路径仍可同时成立，只有对照正文和真实证据后才按既有语义冲突出口交人裁决。

缺链、孤儿页及被新证据替代的断言均作为明确处置项记录对象、依据和出口；被替代判断须能指向新证据及旧断言位置，依据未核实则保留待核对，不自动停用。按本文 §8.4 同步完成获批的正文/索引/metadata 与活动引用维护；合并、删除、降级仍由人裁决，活动依赖未解除则阻断相应删除。只读巡检或当前范围不足时明确报告待处置及所需授权，不把列入清单称为已清理，也不借“同步清理”擅改历史任务或用户文件。

报告四类各自 passed/failed/unknown 及未覆盖对象，不能只给知识统计就称巡检通过。归档正常/异常不自动免于引用核对，历史绑定在此按全库巡检范围读取；这是周期操作，不把相同全扫搬进每次任务创建/start。

## 9. 审查协议与最终门禁

### 9.1 发起、材料与报告 schema

复杂任务 Check 有效后，由人声明实施 CLI 集合、两个异种 reviewer CLI 与槽位，并授权本次材料范围。入口在 task.reviews.launches 保存 `{round, attempt, decision, implementation_clis, slots, anchor, submitted_scope, readable_scope, exclusions, export_decision, temp_paths}`。round 从 last_round+1 分配，跨返工保持递增；attempt 引用当前实施尝试号，每个尝试内最多两轮，返工后新尝试的轮数从零计但全局 round 不归零，旧报告路径不复用。

submitted_scope 只有 diff、需求、测试结果；readable_scope 分列允许只读的业务代码、spec 与需求 PRD。exclusions 明列凭据、私密配置、项目外非报告路径、其他任务目录；暂存报告目录是单独授权的输出位置，不开放它的父目录。项目配置/基线哈希属于对象锚点元数据，不因它在指纹里就授权 reviewer 读取私密配置。材料不够覆盖检查面时 reviewer 回报，不自行扩大；与检查有关的公开需求事实可在原授权范围内整理，新增外发范围仍需人确认。

两份自有审查适配资产共同实现以下协议：

| 字段 | 必需语义 |
|---|---|
| `protocol` | `wf-review-v1`，不支持版本拒绝导入 |
| `task-id`、`round`、`reviewer-id` | 本次任务、正整数轮次、已声明槽位；不从目录名猜 |
| `source-cli`、`review-time`、`review-focus` | 自报 CLI、Time、固定检查轴及本次重点 |
| `check-anchor` | check.id 与本文 §3.2 定义的 check_anchor 键集合取值（paths/content 摘要、批准版本、验收摘要、spec/基线/配置/定义快照哈希） |
| `read-scope`、`excluded-scope`、`scope-exceptions` | 实际读取声明、排除声明、越界/缺材料事实 |
| `axes` | 范围、验收、契约/spec、跨层回归、可测性各自结果与未覆盖项 |
| `findings`、`verdict` | 具名发现、位置/证据/影响；pass/fail/unavailable，仅建议可 pass |

报告 Markdown 内用唯一带协议标记的 JSON 块承载字段，正文保存具体分析；机器检查字段，主会话核对事实。CLI 参数 `--task-id`、`--round`、`--reviewer-id` 两侧必备，wf 总提供 `--review-focus`；参数拼写沿用设计稿，其完整调用语法由实现方案负责。主会话不传作者会话/自评充当需求。

### 9.2 导入、判定与轮次

reviewer 只在已给的项目树外暂存路径写报告。导入主会话持自己的 writer，在当前 task.action 以 review.import 固定报告原始摘要、目标槽位、round/slot、人工身份声明与 anchor；先读完整报告并核元数据及当前锚点一致，再预检目标碰撞。以同目录临时文件写完整内容、读回哈希后原子发布最终报告，最后更新 reviews.imported 并核两侧一致；不把“目标路径存在”当作已导入。最终文件已发布而 imported 未写时，按同 action 意图核哈希补字段；临时文件未发布时只恢复该动作登记的临时目标，不认领其他文件；截断或来源报告变化就停在恢复诊断。两侧已一致的同路径同摘要重入返回已导入，不同摘要报冲突。导入不改变交付指纹、不转移写权，reviewer 不取得项目写权。

暂存目录按 task/round/slot 隔离并由主会话输出其确切范围；源报告在导入成功、目标摘要/元数据均核对且 reviewer 已结束写入后才成为可清理项。主会话报告这些精确目录的导入/待决状态，由人确认后清理；默认保留尚未导入、冲突或恢复中的轮次，不静默删旧轮或全局临时根。项目卸载/purge 的清单不覆盖这些项目外目录，只列残留位置及人工清理出口，不授予删除权限；导入的项目内报告按任务归档/保留策略处理。正文和摘要均避凭据，需求/测试内容的外发和保留仍在原授权范围内。

人工声明至少两个 reviewer CLI，彼此不同且不在任一实施 CLI 中。主会话对照实际调用、自报字段与声明来源核验；文件不能证明身份真实性，缺失/冲突不能 pass。同 CLI 换模型仍同 provider。单 reviewer 可作为 degraded 参考，不能满足复杂完成门禁。

task.reviews.imported 保存 `{round, slot, report_path, report_digest, anchor}`；dispositions 保存逐条接受/驳回理由、证据与后续动作，result 保存当前对象的 pass/fail/unavailable 和引用。存在阻塞项、未决人判、必要验证 fail/未跑、范围核对失败、报告/身份/人数不合格即 fail。驳回须本地核实，不把“作者不认可”当证据。审查 pass 后采纳纯建议（不影响 verdict 的建议项）按是否影响检查对象分流：先核受影响路径——不在当前 check 对象（本文 §3.2 的触碰路径与规则输入并集）内的采纳改动，按机械修订口径处置，dispositions 记采纳依据并与新指纹核对，报告继续有效、不消耗轮次；命中 check 对象的采纳改动使锚点变化，重跑 Check 并按既有轮次规则发起新轮次。该分流与设计稿 §4.2 检查有效性“无关路径改变不自动失效”同构：无关路径的采纳不使旧 pass 失效，对象内变化按内容指纹重检。

实际 fail 后在范围内修复、重跑 Check，再发新轮次；同一实施尝试最多两轮仍 fail，由人发起返工。unavailable 只用于实际缺 CLI/适配/启动能力，不把两轮 fail 改成不可用；当前任务仍复杂时暂停或异常退出，只有事实范围变轻并获重新分级后才走轻量 Check。失效锚点一律重审，不能因旧文件仍在而复用。

attempts 每项为 `{number, rework_ref, round_ids, outcome}`；原 T 经返工 R 恢复后只增加尝试号，T.last_round 不归零。R 自己作为普通任务有自己的 task-id 与审查序列，两者不能互借报告；同一任务的旧轮次路径永不覆写。任务替换后新任务采用自己的 task-id，旧任务报告只作来源参考。

### 9.3 最终门禁算法

按设计稿 §6.5 的八项定义实现一次最终核验，前七项为动作前置，第八项中人调用是发起条件、归档完成是后置。下表的编号与上位相同，不另立一套完成标准。

| 项 | 读入事实与算法 | 未满足的出口 |
|---|---|---|
| 1 | 当前 plan.version/批准、entry_snapshot 对应的触碰面、实际路径与复杂度有效；按本文 §11.2 计算所有适用的归档前 required 步骤，逐项 completed，或 once 且 reused 的 skip_basis 和当前 gate 均可核 | 列出缺失/过期步骤并回对应阶段；不能以“已有回执均一致”代替全完成 |
| 2 | 当前 check.result=pass 且本文 §3.5 有效，所有批准必要验证及逐项验收结果实际通过 | 回 Check；未跑不得视同成功 |
| 3 | complex 时本文 §9.2 当前对象审查 pass；light 时两轴内部审查完成；由 complex 降级为 light 的任务另核 plan.complexity_reasons 的降级条目（reason/evidence 齐全且与轻量判据相符），按轻量任务的审查要求执行 | 重新审查/暂停/异常退出或合法重新规划 |
| 4 | 当前命中及策展 spec 全文已读，过期/extracted 已核实或有人接受的未核实留痕 | 重读/核实/人判；缺必要验证仍拒绝 |
| 5 | knowledge 有处置记录，curation 显式存在，最终知识变更已入 Check，所需复盘完成 | 补真实处置；新变更回 Check |
| 6 | prerequisites 均满足，无未决暂停/挂起/动作残留，write_mark 与归属可核 | 依赖/恢复/人裁；不自动删边 |
| 7 | 本任务交付/记录按授权提交，业务 WIP 无未处理项；外来/维护组未捎带 | 待提交授权或实际处置，保留合法独立控制组 |
| 8 | 实际人调用 finish；按本文 §5.3 归档移动、关联记录与归档提交均可核 | 中断恢复，成功前不报告完成 |

task.archive 在本节前置中消费本文 §2.3 的 verification.resolve(finish)；finish 中更新 spec/配置后重新计算 anchor，发现变化回 Check；不会因 knowledge 字段写了“已更新”而排除实际文件。规则兼容语义对齐设计稿 §4.2 检查有效性“规则变化影响门禁/检查项时重跑对应步骤”：本表门禁仍核发行兼容声明，规则类回执因规则字节变化失配并重跑对应步骤；内容类回执（本文 §11.2 的分类）不因规则字节变化失配，仍按其内容主键核验。正常归档后实例继续步骤或结束，最后按 writer 协议释放；异常归档只核本文 §6.4 的退出条件，不套上表。

## 10. 发行、维护与退出

### 10.1 资产落点与所有权

本表是类型到既定落点/所有者的约束，细分文件名由实现方案给出；不据目录名自动认领未登记文件。

| 资产/记录类 | 落点约束 | 所有者与升级/卸载覆盖 |
|---|---|---|
| 入口 skill、原语、审查成对副本 | 人声明且宿主确认可读的 skill 根，缺省候选 `.agents/skills/` | 发行资产，精确清单、三方升级、默认卸载移除；本地偏离先裁决 |
| 常规脚本、独立恢复 | `.wf/bin/wf.py`、`repair.py`、`uninstall.py` 及实现方案声明的资产 | 发行资产；恢复脚本单文件标准库、不导入运行时 |
| 框架流程 | `.wf/workflows/` | 发行资产；本地修改作为偏离保护 |
| 配置/spec/任务模板 | 发行资产区，具体子路径由实现方案定 | 模板随发行升级，已生成实例属项目数据 |
| 任务、准备、基线、spec/index、拒绝项 | `.wf/` 内项目数据区；拒绝项 `.wf/out-of-scope/` | 任务/相应入口写；升级/默认卸载保留 |
| 用户定义、实例、快照、绑定、writer、项目配置 | 设计稿明确的 `.wf/` 路径 | 项目数据，升级不 O/L/N 替换；writer 只经维护协调修改 |
| 安装清单、偏离/删除裁决、恢复说明 | `.wf/` 的独立安装恢复数据区 | 本机投放事实，默认卸载保留；purge 单独确认 |
| 活动缓存与读取侧车 | `.wf/.runtime/`，按会话隔离 | 可丢弃运行态，忽略后不进任务提交 |
| 最小互斥文件 | 项目根 `.wf-lock` | 运行态、只创建不删除，卸载/purge 保留忽略行 |
| `.gitignore` 托管段 | 首行 `# wf-managed-v1` 至尾行 `# wf-managed-end` 界定的连续段，段内为框架运行态忽略行（含 `/.wf-lock` 保留行） | 发行资产约定：追加/升级/卸载按标记串定位整段处理，重复运行核对已有标记串、不重复追加；段外内容属用户，见本文 §10.2 的清单登记 |
| 用户层配置和解释器确认集合 | `~/.wf/` | 人维护、非项目 Git、非发行资产，卸载项目不复制/删除 |
| 本稿、设计稿与 charter | authoring 文档族 | 不投放目标项目 |

宿主根可发现性、调用权声明支持与已有同名文件均在安装预览核实；共享根只是候选，不假定每个 CLI 可用。不同根的自有副本共享同一逻辑来源和版本，不能发展不同平台门禁规则。

### 10.2 发行身份与清单 schema

专用发行引用定为 `refs/tags/wf-v<major>.<minor>.<patch>`，版本按三段非负整数解释，预正式发行使用 0.x.y。目标提交根的清单定位定为 `wf-release.json`；这是发行协议定位，authoring 的打包源码布局另由实现方案定义。清单不写包含自身的 Git SHA；源提交从人给的专用引用解析到 commit 获得。

清单 schema：`{schema_version, version, compatibility, assets, required_steps, template_markers, gitignore_managed}`。compatibility 为 `{python_min, systems, filesystems, record_versions, workflow_versions, rules_digest}`；assets 为 `{source_path, target_class, target_relative, kind, required, file_kind, executable, digest}` 数组，kind 是资产类型，file_kind/executable/digest 采用本文 §3.2 的文件状态定义，required 缺失按 true。required_steps 的唯一字段定义与适用性算法在本文 §11.2，清单保存其实际条目；清单不复制 skill description。gitignore_managed 为 `{begin_marker, end_marker, lines}`：登记托管段标记串（首行 `# wf-managed-v1`、尾行 `# wf-managed-end`，见本文 §10.1 落点表）与首版段内容（框架运行态忽略行，含 `/.wf-lock` 保留行）；标记串与段内容属于判定物，随发行版本化、计入 rules_digest 输入，升级/卸载按其定位整段处理，不以散行匹配替代。

compatibility 的取值域：python_min 为 `{major: 3, minor: 11}`；systems 为 `["linux"]`；filesystems 为 `{local_only: true, advisory_flock_required: true, network_or_sync_supported: false}`。record_versions 是对象类型到 `{read: [正整数], write: 正整数}` 的映射，首版键为 task/binding/preparation/run/writer/installation/config/spec，全部 read=[1]、write=1；未知版本仅阻断依赖判断。workflow_versions 为 `{read: [1], write: 1}`。这些字段表示发行支持声明，不替代安装机的实际能力验证。

template_markers 为 `{formats: [{id, pattern}], uses: [{template_path, selector, format_id, required}]}`，首版 formats 的 id/pattern 固定为 required-field/`{{WF_REQUIRED:<field>}}` 与 required-value/`__WF_REQUIRED__`；前者 field 为非空 ASCII 字段名，后者为完整 JSON 字符串值。selector 用 `{kind: json_pointer, value}`（标准逐段对象/数组路径）或 `{kind: markdown_marker, value}`（模板中唯一标记），仅定位模板已声明的待填位置。uses 引用的模板须在 assets，format_id 须命中 formats，selector 须唯一可解析；自检双向枚举模板的实际占位标记与 uses，漏登记/悬空/重复位置使模板不可用。讨论这些标记的普通正文不是模板使用位点，不能据关键字整文件拒绝。判断必填还核类型/非空，不把删除标记视为填完。

`rules_digest` 是整个发行规则集的内容标识，不是人工填写的兼容结论：`H("wf-rules-v1", C({schema_version, compatibility_without_rules_digest, assets, required_steps, template_markers, gitignore_managed}))`。assets 按 source_path/target_class/target_relative 排序，required_steps 按 id 排序，集合按本文 §1.1 规范化。`wf-release.json` 清单自身不作为 assets 成员，也不把清单自身哈希或规则摘要写入规则摘要输入；版本号、Git SHA 和 rules_digest 自身同样不入输入，避免自指；校验时重算并与声明值比较。首版将清单之外的全部发行资产计入，宁可在无语义影响的资产变化后重新核验，也不由脚本猜测某文件是否影响门禁；版本号单独变化不改变该标识。

运行期 `effective_rule_version=H("wf-effective-rules-v1", C({rules_digest, installed_assets}))`，installed_assets 按安装登记的逻辑根标识和相对路径排序，记录每份实际投放资产的类型、执行位、存在状态及内容摘要，不包含机器绝对目录。原样副本和已接受本地偏离都按实际内容计算；未解决的缺失/不兼容先阻断相关入口。Check.anchor.rule_version 与规则类 required 回执的 rule_version 均取此值；内容类回执不按 rule_version 匹配（分类与匹配键见本文 §11.2）。规则内容变化会失配，重新核对适用清单和对应 gate，不自动把旧回执改写成新版；真正需重新运行的步骤补跑，再形成当前版本 Check。规则字节未变时标识相同，但这仍不证明未记录的环境变化不存在。

安装从设计稿 §7.5 固定私有源获得已检出的发行源码，入口本地解析指定 tag → commit → 清单/资产，不查询发布服务。校验 tag 版本与清单一致、每源路径处于发行根内且无越界/嵌套引用、资产实际哈希一致，记录解析出的 commit 与清单摘要。同一 version 已见不同 commit/清单视为冲突，即便引用名相同；首次没有既往观察时只能核当前身份一致，不声称证明远端 tag 从未移动。

本地安装记录含 `{release_ref, source_commit, version, manifest_digest, roots, assets, decisions, session_profile}`，session_profile 按本文 §1.4 定义。roots 为安装时人确认的实际投放根，项目内根用相对路径、明确项目外根用绝对路径；assets 每项保存 target、旧模板 O 的哈希与可重取来源、必要本地模板副本、所见 N、接受偏离/删除决定。只从已登记目标判所有权，远端通用清单不证明本机曾安装到哪里。

### 10.3 预览令牌与应用

所有维护先形成 `{operation, target_root, release_identity, selected_paths, before_states, intended_after, writer_observation, wip_observation, risks, backup_ref}` 的完整预览。终端生成随机 128 位 nonce，令牌显示为 nonce 的十六进制，校验对象绑定预览摘要和本次过程；token 不作为跨会话授权凭据、不保存秘密。首版预览/确认/应用在同一交互入口进程完成，重新预览即销毁旧 nonce；进程退出后重新预览，不从旧输出恢复许可。

upgrade 应用、repair、purge 要求人在交互终端输入本次令牌；模型仅可准备/解释预览。安装与默认卸载按其预览确认要求取得明确人决定。确认后在同一项目锁内重新比对目标/范围/前像/writer/WIP，再 acquire maintenance；任何差异使预览失效，不自动扩大路径。确认只授权维护，Git 提交另有明确精确路径授权。

长期维护可持锁完成其预览确认后的实际应用，但等待人输入在锁外；旧写者已停止仍须人的事实确认，不以 OS 锁已可取得代替。首次安装还没有 writer 时，先在同一锁内核不存在既有项目数据，创建 `.wf/` 与初始维护 writer，全部纳入预览，完成后释放。

### 10.4 安装、三方升级与分支来源

安装投放前仅对预览登记路径作只读 Git 历史/引用核对：当前分支缺失但其他本地分支存在时列具体分支与推荐出口，待人确认再继续。未获取的远端引用不假装已扫描，证据不足可见报告。该观察不保存 branch 字段或管理分支；切换/合并仍由人执行。

每路径读取 O/L/N，先处理上游删除；其余按设计稿 §7.2 的顺序表匹配：本地缺失曾安装 → 新增无占用 → 新增撞用户文件 → L=N → L=O 且有上游变化 → 同一已接受偏离 → 其他冲突。缺失时先核分支来源并确认删除，不自动恢复；必需资产缺失即相关入口不可用。偏离保存 `{local_fingerprint, upstream_version, upstream_fingerprint, decision}`，只对两边指纹均相同的状态免重复询问。

上游删路径只有 L=O 且无用户新增内容时成为可删候选，仍列入预览；偏离或未知内容人裁。移动按旧所有权、新目标碰撞和目录自深到浅顺序执行。O 正文不可得但哈希可靠时，只做哈希可支持的判定；需要内容合并则请人提供原发行副本，或放弃该路径恢复，不猜模板。

完整应用后检查目标资产哈希/已接受偏离、skill 路由、required 步骤与脚本接口属于同一兼容发行集，核 gitignore 托管段（按本文 §10.1、§10.2 的标记串定位：已有标记串不重复追加，段内容与发行登记不符按偏离处理）、基础引导与坏配置下恢复。未解冲突/部分投放保持明确维护检查点，不启用依赖缺失步骤。自检成功才记录安装/升级结果；无提交授权时按本文 §4.5 待持久化释放。

普通升级前所有活动任务暂停或未开工，挂起任务亦暂停，WIP 已实际处置；数据格式不兼容只阻断相关对象，保留原文并由获批数据任务迁移。项目配置不作为发行替换对象。Git 初始化/首个 HEAD 按单独授权，只暂存清单骨架，不卷入已有 README/LICENSE；无许可或身份缺失就报告待就绪。

### 10.5 独立卸载、purge 与重装

独立卸载只读独立安装清单、精确资产状态和最小协调材料，不解析任务/spec，不导入框架运行时。清单缺失只诊断，不从目录形状猜删宿主根。writer 合法时正常 acquire maintenance；writer 损坏则保留原文、人确认其他写者停止、持同一最小锁，仅在已确认退出范围内处理，不造假代次。

默认卸载移除精确登记且已确认的发行资产及 gitignore 托管段（按本文 §10.1 的标记串定位整段处理，保留 `/.wf-lock` 保留行），保留数据/安装偏离/恢复材料、`.wf-lock` 及 `/.wf-lock` 忽略行；本地偏离和未知文件逐项由人选择保留/移走/删除。报告锁保留与人在确认无 wf 进程后清理锁和对应忽略行的顺序；框架不代删锁。

purge 另由人直调并确认数据丢失、备份位置和全部目标。应用先完成其他资产退出，再删除 `.wf/` 数据，writer 等协调材料最后删除，仍持锁核目标已移除后释放 fd；不重建空 writer。部分删除的中断用仍存清单/恢复入口与实际状态诊断，不能因数据目录消失就报告全部完成；锁对象保持同一 inode。

保留数据重装先验证原清单、偏离和数据存在，不覆盖；投放后核 records/schema/定义快照/绑定/writer，与 WIP 和卸载期外部提交对应。新会话显式接续原对象，损坏先 repair。卸载期业务提交不要求补建 wf 任务。恢复入口可从对应发行重取并给显式目标，不能把源码目录误当项目。

## 11. 输出与固定执行面

### 11.1 结果结构与原因码

每次路由/判定返回 `{tier, code, object, position, next, facts, exit, prohibited_repairs, warnings}`。position 为 `{scope, phase, step_id, task_id, action_id, action_state}`：scope 取 session/task/run/preparation/maintenance；无适用值写 null，未知记录的事实写入 facts，不猜阶段。任务 phase 取 task.phase，实例 step_id/task_id 取当前 cursor，维护位置取 action.id/state；查询也返回实际定位。next 是具名下一操作及所需人工动作，exit 是失败/待决时可走的出口；通过时 next 给合法后续入口。tier 为 pass/blocked/needs_decision；object 显示名称与稳定 id。blocked 的 facts 至少含决定性事实，exit 给下一步；needs_decision 列待决事实和人可选出口。执行失败还含命令、关键错误、影响；输出不携带秘密。warnings 用于截断/未核实等降级事实，不自动将 blocked 转 pass。

以下码值首版固定，发布后只能新增、不改义；具体对象/路径/缺失项放 facts，不为每个文件新增原因码。同次多个问题可返回有序 issues，先列权限/结构问题，相关判断停止，无关只读诊断继续。

| 原因码 | 档位 | 适用事实 | 出口与禁止的错误修复 |
|---|---|---|---|
| `WF_OK` | pass | 当前操作所有适用前后置成立 | 继续当前绑定步骤；不推断其他对象已完成 |
| `WF_NOT_ENABLED` | blocked | 当前会话未声明有效 start 启用或 activation 缓存缺失/非法 | 提示人调用；不靠绑定文件伪造启用 |
| `WF_FLOW_CONFLICT` | blocked | 当前有效 Trellis 指令已确认 | 清理来源后新会话核对；不以人工豁免继续混跑 |
| `WF_IDENTITY_UNRESOLVED` | needs_decision | 身份/实例标识不可核或冲突，或宿主会话稳定性/身份传递能力及其证据尚未核实 | 核受支持身份与会话连续性能力/显式恢复；不猜全局指针 |
| `WF_BINDING_MISMATCH` | blocked | 目标与持久绑定不一致 | 原对象保存退出后新会话选择；不改绑 |
| `WF_WRITER_BUSY` | blocked | 锁占用或 writer 属他者 | 等待/已确认交接；不超时抢占或删锁 |
| `WF_GENERATION_STALE` | blocked | 请求代次不是当前 holder 代次 | 停止写并重新核对；不自行递增获取权限 |
| `WF_RECORD_INVALID` | blocked | 依赖记录语法/已知 schema 非法 | 保留原文并 repair；不覆盖同名任务 |
| `WF_CAPABILITY_UNAVAILABLE` | blocked | 所需系统/格式/资产能力未支持 | 列支持路径或恢复出口；不退无锁/猜兼容 |
| `WF_PATH_INVALID` | blocked | 非法路径/嵌套/越界 | 修正授权输入；不跳过非法 touch_paths |
| `WF_SCOPE_UNRESOLVED` | needs_decision | 命中但归属/范围意图不明 | 人核对或回 Plan；不自动扩 glob |
| `WF_APPROVAL_MISSING` | blocked | 批准缺失或与版本不符 | 当前规划人批准；不补写伪批准 |
| `WF_DEPENDENCY_UNMET` | blocked | 必要前置未正常完成 | 等待/人确认返工或重连；不把异常当成功 |
| `WF_WORKSPACE_UNRESOLVED` | needs_decision | WIP/维护组去向或归属未明 | 逐路径核实并落实处置；不 stash/捎带 |
| `WF_WIP_UNRESOLVED` | blocked | 存在按记录登记的未处置保留 WIP 或待持久化维护组（确定边界事实，非去向未明） | 按登记限制执行：同对象恢复/实际处置后重入；不当空闲放行、不捎带 |
| `WF_ACTION_INCOMPLETE` | blocked | 相关动作未完成且事实可定位 | 按原意图恢复；不另生成重复对象 |
| `WF_HISTORY_UNRESOLVED` | needs_decision | 锚点/旧写者/记录来源待核 | 只读核 Git/原文，人确认后 repair；不改历史猜锚点 |
| `WF_TARGET_COLLISION` | blocked | 创建/归档/移动目标已占用 | 保留双方并确认目标；不先改状态后覆盖 |
| `WF_CHECK_FAILED` | blocked | 必要命令失败/未运行/未结束或内部审查未通过 | 修复并重跑相关项；不称基本通过 |
| `WF_CHECK_STALE` | blocked | 当前路径/内容/规范/环境与检查不同 | 重新 Check/审查；不按归属豁免变化 |
| `WF_SPEC_INCOMPLETE` | blocked | 必要正文未完整读取/版本不符 | 分批全文读取；不以摘要当已读 |
| `WF_SEMANTIC_DECISION` | needs_decision | 知识/工作流/规划等语义未决 | 列具体冲突与人选项；不由脚本臆造判据 |
| `WF_REVIEW_INVALID` | blocked | 报告、人数、声明、范围或锚点不合格 | 补真实审查/重新发起；不伪造异种身份 |
| `WF_REVIEW_UNAVAILABLE` | blocked | 实际审查环境不足且任务仍复杂 | 暂停或异常退出；不把不可用当 pass |
| `WF_EXECUTOR_UNCONFIRMED` | blocked | 候选不可用或确认元组失配 | 人确认/合法配置修复；不自动回退 |
| `WF_PREVIEW_STALE` | blocked | 令牌/范围/前像不匹配 | 重新预览确认；不扩大旧许可 |
| `WF_RELEASE_CONFLICT` | blocked | 发行引用/清单/同版内容不一致 | 核正确发行；不信名称替代内容 |
| `WF_ASSET_DECISION` | needs_decision | 本地偏离/未知文件/分支来源待定 | 预览保留/恢复/合并等具体选择；不认领未知文件 |
| `WF_COMMIT_NOT_AUTHORIZED` | blocked | 本次提交范围无授权 | 等人处理；不借维护确认执行提交 |
| `WF_PERSISTENCE_FAILED` | blocked | 写入/移动/提交失败或结果不明 | 报命令、影响及读回/恢复出口；不盲重试 |
| `WF_VERIFICATION_UNREADY` | blocked | 验证的来源/输入/命令不就绪 | 补真实来源/设施后重新解析；不以“定义可解析”替代就绪 |
| `WF_DEFINITION_INVALID` | blocked | 工作流定义静态校验非法 | 按本文 §7.1、§7.2 修正定义；不猜测承载步骤或自由文本占位 |
| `WF_TEMPLATE_INCOMPLETE` | blocked | 批准用模板的必填位未填 | 填写模板声明的待填位置并重新核验；不以删除标记充当填完 |

等待人的缺口是 needs_decision；事实已确定违反前置则 blocked。比如审查不可用但复杂度是否已实质降低尚未裁定，先输出 `WF_SEMANTIC_DECISION`；裁定仍复杂且只有一个 reviewer 时输出 `WF_REVIEW_UNAVAILABLE`。一次控制记录合法更新不表示业务内容验收通过。

固定处理器的失败输出与原因码固定映射如下；只读断言与状态动作的处理器在无专用码时按该表取值，具体对象/缺失事实放 facts：

| 固定处理器 | 失败情形 | 码（档位由本文 §11.1 码表单一来源） | 决定性事实 |
|---|---|---|---|
| `verification.resolve` | 验证来源/文件/设施不就绪 | `WF_VERIFICATION_UNREADY` | 来源/输入/命令缺失或不就绪的具体项（与 `WF_CHECK_STALE` 分工：后者为检查对象已变化，前者为验证设施本身不就绪） |
| `definition.validate` | 定义静态校验失败 | `WF_DEFINITION_INVALID` | 首个非法项及规则（id 重复、引用错位、替代不合法、根级字段缺失等）；新增专用码而非复用 `WF_RECORD_INVALID`：后者语义是“依赖记录语法/已知 schema 非法”，指运行态持久记录不可解释，定义文件校验失败属输入文档不合法、记录尚不存在，语义不贴切 |
| `definition.prepare` / 批准入口模板核验 | 模板必填位未填 | `WF_TEMPLATE_INCOMPLETE` | 批准用模板中声明必填的待填位置及模板标识 |
| `run.advance` / 实例步骤 pending | 待决人判未完成 | `WF_SEMANTIC_DECISION` | 既有码语义本贴合（语义未决），直接映射，不新增 |
| `gate.evaluate` | required 步骤缺项/过期 | 二维分派：先按未满足的原因事实选码，再以缺失步骤 id 列清单；每分支一码一档，档位由本文 §11.1 码表单一来源、本表不另标——必需人判/批准未答（待决面）→ `WF_SEMANTIC_DECISION`（plan-approved/knowledge-disposed/retrospective-done 的批准或声明待答、work-satisfied 的必需用户动作未答）；批准缺失或与版本不符（已确定违反）→ `WF_APPROVAL_MISSING`（plan-approved 的批准缺失/失配面）；产物未做或验证 fail/未跑 → `WF_CHECK_FAILED`（work-satisfied/check-passed/tdd-verified 的交付/检查事实不合格）；审查报告/人数/锚点不合格 → `WF_REVIEW_INVALID`（review-passed，出口补真实审查）；提交未获授权 → `WF_COMMIT_NOT_AUTHORIZED`（changes-persisted 的授权缺失面）；提交失败/结果不明 → `WF_PERSISTENCE_FAILED`（changes-persisted 的持久化失败面）；WIP 未处置 → `WF_WIP_UNRESOLVED`（changes-persisted 的未处置组面）；正文未完整读取 → `WF_SPEC_INCOMPLETE`（spec-loaded） | 缺失/过期步骤的 id、未满足的具体原因事实（清单逐项带原因与码） |
| `run.locate` | 实例内定位失败 | 按原因事实选码（档位由码表单一来源）：目标与持久绑定不一致 → `WF_BINDING_MISMATCH`；快照/游标/映射记录待核 → `WF_HISTORY_UNRESOLVED` | cursor/task_map 与实际任务的差异事实 |
| `asset.compare` | 三方比较冲突/缺失登记 | 按原因事实选码：本地偏离/未知文件/分支来源待定、新增撞用户文件、上游冲突 → `WF_ASSET_DECISION`（各面共用一枚码，冲突类型写 facts；码的适用事实见本文 §11.1 码表行） | O/L/N 三态与冲突类别 |

### 11.2 required 步骤清单与完成判定

发行清单的 `required_steps` 是应执行步骤的唯一机读来源，首轮开发态部署也须带同结构清单。流程 Markdown 以稳定 `id` 引用声明并写 `[required · once]` 或 `[required · repeatable]`；安装/升级自检双向核对 id、mode 和 enforcement，缺声明、重复 id、模式不符或找不到执行面均使相关流程不可用。任务中的执行回执不是步骤清单，不能用“已记录的步骤都成功”代替“应有步骤全部满足”。

每项声明为 `{id, scope, workflow_ref, mode, applies, due}`：id 为发行集内唯一的稳定 ASCII 名称；scope 取 task/control；workflow_ref 定位发行流程文件及该 id 的步骤标记；mode 取 once/repeatable。task 的 applies 是 `{task_kinds, condition}`，task_kinds 为 ordinary/initialize/bootstrap 的非空子集，condition 只取 all/complex/tdd/retrospective，由当前批准分级、TDD 取值与实际复盘触发事实判定，不接受自然语言或可执行表达式。事实未知就给待核对出口，不能按不适用删除步骤。control 声明只应用于具名操作的本次 action，不加入每个普通任务的收尾清单。

task.due 取 before_execute/before_check/before_archive/after_archive，表示最迟满足时点，不是 task.phase 的新值；control.due 为 operation_end。id 同时是框架实现中的固定分派键，下表与本文 §11.3 给出每个键的核验算法和证据类型；不再让清单自由填写 gate/anchor_kind/evidence_kind 或函数名。实现须为每个声明 id 提供对应固定处理器，自检比较支持键集合与清单声明，未知 id 拒绝，不动态加载任意代码。新增阶段内细分步骤要同批增加固定键、投影和断言，不能只在 Markdown 增一句 required。

首版任务声明至少包含以下固定行。前三类任务共用四阶段，差异只由明确条件确定。表中“当前检查”指本次 check.id 及其对象锚点，“当前规划”指 plan.version；这些取值均从已有记录派生，不新增步骤计数账本。

| id | mode / 条件 | due / 期次 occurrence | gate 与证据 |
|---|---|---|---|
| `task.plan-approved` | once / all | before_execute / 当前规划 | 当前规划文件/机读块与批准一致；Decision 及快照 |
| `task.spec-loaded` | repeatable / all | before_execute / 会话身份 + 当前所需 spec 集合及哈希 | 全文已读；当前侧车或本次完整读取事实，不能借旧会话回执放行 |
| `task.work-satisfied` | once / all | before_check / 当前规划 + 当前交付指纹 | 规划要求及必需用户动作满足；实际产物、动作结果/人判引用；纯调查也须有可观察成果 |
| `task.check-passed` | repeatable / all | before_archive / 当前检查 | 必要验证与内部双轴均通过，检查对象有效；check 记录 |
| `task.tdd-verified` | repeatable / tdd | before_archive / 当前检查 | 开关开启时核红绿证据；文档等对象核已批准的适用性与独立可观察验证，不人为造红命令 |
| `task.review-passed` | repeatable / complex | before_archive / 当前检查 | 当前对象的两个异种审查通过；身份声明、导入报告和处置记录 |
| `task.knowledge-disposed` | once / all | before_archive / 当前规划 + 当前知识处置及相关规范指纹 | knowledge 非空、curation 显式存在；无更新也是实际处置 |
| `task.retrospective-done` | once / retrospective | before_archive / 当前触发事实集合 | 适用由触发事实集合决定，触发集合是 gate 时的派生视图、不落第二持久清单：从 rework_of 反向集合本轮新增、reviews 历史 result=fail 与 debug-ruling“同一问题”裁定条目及其 subject/证据引用的调试证据重建（调试证据不限定 check_history 条目类型：check_history 的 failed 最终结果条目、execution.actions 的 failed 结果及其 output_refs/verification_refs、handoff 材料均可承载，核对所引证据仍真实存在即可，Execute 期裁定凭原证据可重建）。返工（本任务 rework_of 反向集合本轮新增）与审查失败（reviews 历史 result=fail）语义机械可判，任一成立即适用且复盘 required。重复调试经两层判定：机械检测（本文 §8.1：同一 verification_id 的双源合并 failed 累计达到 debug_repeat_threshold，合并与判重规则唯一见本文 §1.3）只产生 WF_SEMANTIC_DECISION 待决项，不独自决定“同一问题”；裁定留痕位置为 execution.human_decisions 的 debug-ruling 条目（id 形式、结构、写者与消费判据见本文 §1.3）——人确认属同一问题重复调试后该待决项转正为触发事实、复盘 required；人裁定为不同问题时裁定条目留痕，该倍数不再追问，该 verification_id 的双源合并 failed 累计保留；合并累计每新跨过 debug_repeat_threshold 的整数倍（即合并累计数首次达到阈值，及其后每再增加 debug_repeat_threshold 次达到新的整数倍）时重新产生待决项，已裁定倍数留痕不重复追问，仅新跨过整数倍的累计待裁定。归档门禁核对 retrospective 适用条件时，要求机械检测已产生的各整数倍均有对应 debug-ruling 裁定条目，无裁定的新倍数即未裁定待决项、阻断归档（出口 WF_SEMANTIC_DECISION），不倒推为无触发。Execute 期漏计兜底：check_history 之外的重复调试由人/主会话在 continue/finish 声明，入口核其引用的调试证据（execution.actions 的 failed 结果及其 output_refs/verification_refs、handoff 材料）真实存在，逐项核对 counted 由证据引用支撑并写入 debug_declarations 条目，判重按本文 §1.3 的分工执行——脚本核证据引用与可比对字段一致，同一事件的剔除结果结构化保存为声明条目的 dedupe_refs，合并累计从结构化字段求和（判定结论属人判语义、依据文本入裁定 reason），核定次数并入双源合并累计、达到新整数倍后按同一 debug-ruling 条目形式留痕；verification_id 只作证据关联辅助。retrospective.evidence（本文 §1.3 既有字段）保存复盘所覆盖触发事实的引用（含对应裁定条目 id）；“历史复盘不能覆盖新增触发事实”按整数倍与触发事实重建核对——复盘之后新跨过的倍数、新增的返工或审查失败事实不属于已覆盖范围，须另行满足。未产生任何触发事实时人仍可要求复盘（对齐设计稿 §4.4“其余任务可选”），由人在 continue/finish 提出、入口记录 retrospective，不新增独立声明字段 |
| `task.changes-persisted` | repeatable / all | before_archive / 当前交付指纹及待提交组 | 本任务改动按许可持久化、无未处理业务 WIP；只读核 Git 与授权 |
| `task.archived` | once / all | after_archive / 归档 action.id | 正常终态、移动及归档提交可核；本文 §5.3 的提交后只读后置 |

下表定义 task 分派键的唯一投影 P；字段名是规范 JSON 键，值从已有记录读取。通用 `occurrence=H("wf-step-occurrence-v1", C({task_id, step_id, P}))`；回执按**可核判据**分两类——gate 处理器是否读取 rule_version 或规则正文：读取者为规则类，不读者为内容类。规则类（task.check-passed、task.tdd-verified、task.review-passed、task.changes-persisted——changes-persisted 的门禁核查 rules_digest 与发行规则兼容，属规则行为）为 `anchor=H("wf-step-anchor-v1", C({rule_version, P}))`，内容类（task.plan-approved、task.knowledge-disposed、task.retrospective-done、task.spec-loaded、task.work-satisfied——后两者的 gate 分别只读会话侧车/全文读取事实与批准目标/实际交付/execution.actions，不读规则内容）为 `anchor=H("wf-step-anchor-v1", C(P))`：内容类 P 只含内容键（plan_version、内容摘要、读取事实、触发事实集合等），不含规则输入，规则字节变化不改变其期次与锚点。P 不包含本回执自身、临时路径、渲染文本或时钟。items/refs/paths 按稳定 id/路径排序；缺所需值即未满足，不以 null 摘要补齐。check_anchor 按本文 §3.2 的定义取值（哈希域名与键集合见该处），输出摘要不包含 check.result/该步骤回执。

| step_id | P 的精确对象形状 | 固定处理器读取的证据 |
|---|---|---|
| `task.plan-approved` | `{plan_version}` | plan.approval、可读快照、当前 PRD 提取值与 execution.human_decisions 的覆盖核对（本文 §1.3 的问题全集均有对应 Decision）；当前 plan.version 经本文 §1.3 的等价链归一到批准版本时，原 completed 回执可复用（skip_basis 记等价链核对事实） |
| `task.spec-loaded` | `{session_key, instance_id, specs: [{path, digest}]}` | 当前会话完整读取侧车/本次全文读取事实 |
| `task.work-satisfied` | `{plan_version, content_digest}` | 批准目标、实际交付与 execution.actions |
| `task.check-passed` | `{check_id, check_anchor}` | commands、acceptance_results、internal_review |
| `task.tdd-verified` | `{check_id, check_anchor}` | plan.tdd、check.tdd_evidence 或文档适用依据 |
| `task.review-passed` | `{check_id, check_anchor}` | 当前 reviews.result、CLI 声明与报告锚点 |
| `task.knowledge-disposed` | `{plan_version, knowledge_digest, specs: [{path, digest}]}` | knowledge、curation 和实际规范；knowledge_digest 取 knowledge 的规范 JSON 哈希 |
| `task.retrospective-done` | `{triggers: [{kind, ref}]}` | retrospective 与派生的触发集合（按本文 §11.2 gate 格从既有判定记录重建，不落第二持久清单）：kind 为 rework/review_fail/debug_repeat，ref 为任务/轮次/check 历史（check_history）条目或裁定条目证据引用（execution.actions 的 failed 结果及其 output_refs/verification_refs、handoff 材料）；debug_repeat 触发核 execution.human_decisions 的 debug-ruling 裁定条目（本文 §1.3）及其证据引用的调试证据（不限定 check_history 条目类型，核对所引证据仍真实存在即可），机械检测已产生的各整数倍均有对应裁定条目 |
| `task.changes-persisted` | `{content_digest, paths: [RepoPath]}` | 本任务精确路径组的 Git 持久化与授权，不把本回执写入列为自身前置 |
| `task.archived` | `{archive_action_id}` | 归档记录、移动目标和提交后只读断言；只派生后置，不追加任务回执 |

spec-loaded 只表示当前会话/内容的完整装载，不为每次 Check 创建新期次。每次接续/编辑前/Check/Finish 都重新核当前读取事实：同会话同内容可沿用完整装载事实，换会话或哈希变化必须重读；侧车缺失则重读或当次核全文交付。门禁 4 直接复用这一读取判据，不另建“Check 必须再读一次”的步骤。因而期次不含 check.id，调用该核验多次不等于伪造重复阅读。

`execution.required_steps` 只保存适用 task 声明的归档前回执，其 id/mode 与相应声明逐项对应；after_archive 的 task.archived 只从本文 §5.3 的持久化后置派生，不要求也不追加 execution.required_steps 行。回执选择规则按上文分类执行：规则类回执的 rule_version 取本文 §10.2 的 `effective_rule_version`；内容类回执不按 rule_version 匹配、按其 P 主键（plan_version/内容摘要/触发事实集合）匹配，rule_version 字段记 null、不作为匹配键，不因规则字节变化失配。occurrence/anchor 按上表唯一公式生成，固定处理器核验对应证据。result 只取 completed/reused；尚未满足不写成功行。completed 由执行入口在后置成立时记录 completed_at、checked_at、evidence_refs，skip_basis=null。repeatable 每个新期次必须实际执行，已完成同一期次的中断重入只读核后置，不伪造第二次执行；输入或会话改变会产生新的期次或失效锚点。

回执数组保留原 completed 条目，reused 是后续核验条目，不覆盖其 completed_ref 指向的原记录；查询按类选择本次可核的结果——规则类按 id/rule_version/occurrence，内容类按 id/occurrence，不能用最后一条未知 id 挤掉缺失项。P 中 plan_version 一律取经本文 §1.3 等价链归一后的批准版本（当前 plan.version 可沿链回溯到既有批准版本时取归一值，机械修订不改变 P/occurrence；链断开即语义变化、P 随之变化）——该规则适用于 P 含 plan_version 的全部内容类回执（task.plan-approved、task.work-satisfied、task.knowledge-disposed），不逐 id 另述；content_digest=本次按本文 §3.2 重算的交付/规则对象摘要、check_id/check_anchor=当前 check.id 与其 anchor 的 check_anchor 部分（本文 §3.2 的定义）；知识摘要排除 required 回执。反例：原完成条目还未提交即被原位改成 reused，使其引用落空，属于非法回执，不允许用 Git 中尚不存在的版本解释。

once 的“跳过”仅省略重复执行已满足的工作，不省略条件核验。gate.evaluate 重核实际产物、版本与完成判据，只有找到可核的原 completed 回执才返回“可复用”及候选 skip_basis；查询无论是否持权都只返回结论，不追加或修改 execution.required_steps。只读查询没有写 reused 不使原 completed 失效，也不要求重新实施已满足的工作。

承载本次推进的状态动作是 reused 的唯一写者，例如开工/再入的 task.transition、实例推进的 run.advance、归档前的 task.archive。该动作取得并核对写权后，在自己的 action 内按当前规则、期次和真实产物重验候选；重验通过后，将 reused 作为本次目标记录变化写入并核后置，再完成相应推进。gate 计算适用步骤时可使用当前原 completed 及当次重核的候选复用结论，不把“reused 必须已写入”当作开始状态动作的前置，避免先有回执才能写回执的循环。归档需要的复用回执须在归档提交前与本次记录变化同批持久化，提交成功后不为更新 checked_at 再写归档记录。

skip_basis 为 `{completed_ref, checked_outputs, gate_result}`，completed_ref 用原 id/occurrence/completed_at 及规则类回执的 rule_version 定位实际执行，checked_outputs 含本次路径/哈希等核验事实，gate_result 为本次通过的结构结果；task.plan-approved 的复用另须记录等价链核对事实（链完整、两端规范化 touch_paths 与验收摘要相等；归一发生时 skip_basis 的 checked_outputs 另列「本次 plan.version → 归一后批准版本」的映射事实供核对）。reused 保留原 completed_at，checked_at 记录状态动作实际重核时间；不能引用另一个 reused 形成循环。相同 action.id 重入且目标已有该动作写入的预期回执后像时，按本文 §5.2 只补未完步骤，不追加第二条或刷新时间；事实变化时保留原记录并报告失效，不从查询缓存复制过时结论。无原成果、产物变化、规则类回执的规则版本失配、内容类回执的 P 主键失配（plan-approved 含等价链归一后的主键失配，即语义变化使链断开）或条件不成立就重新执行/补齐，内容类回执不因规则字节变化重跑，不接受一句“无需执行”。

门禁按以下顺序算缺项：加载并核验发行声明 → 从当前任务事实计算适用集合 → 按所到达 due 选择需核的声明，并且仅按每项 P 的唯一公式构造期次 → 逐 id 查对应回执并重核 gate → 输出缺失/过期/不适用待决清单。进入 Execute 要满足开工前集合；开始 Check 先满足 before_check 集合，Check 成功后才写 check-passed；归档前第 1 项必须满足所有适用的归档前声明。after_archive 不参与归档前集合，归档提交后由只读事实派生 task.archived 已满足，不为写回其成功再次提交归档文件。异常退出只消费自身控制动作的退出条件，不要求正常流程的任务步骤全部完成。

正例：同一 once 步骤的原产物未变且 gate 重核通过，可记 reused；反例：删掉任务回执就使 required 消失、repeatable 新检查借旧期次放行、once 仅凭理由跳过，均拒绝。归档前不要求 task.archived 回执，这是前置/后置分工，不是跳过 required。规则版本变化时按本文 §10.2 重新核适用步骤及证据，不从旧回执自动补出新步骤。

### 11.3 固定控制流的执行面

执行面分为下表两类，读写效果由固定操作定义，不能由是否拿到写权临场改变。同一操作的预览只读阶段不属于 apply 动作。发行 required_steps 的 scope=control 只登记下表“状态动作”，每项由 `id=control.<operation>`、mode=repeatable、due=operation_end、applies={operation: action.kind} 定义；纯断言通过固定查询分派表提供，不伪造 required 回执。两类均须有实现支持，自检分别核对固定操作集合和状态动作的清单条目。

| 类别 | operation 集合（逐个展开，独立固定名称） | 处理器核验与证据落点 |
|---|---|---|
| 只读断言 | `gate.evaluate`、`run.locate`、`definition.validate`、`asset.compare`、`verification.resolve` | 本文 §2、§6.1、§7、§9.3、§10；返回当前 gate/建议定位/结构/三方比较/验证就绪事实，不更新阶段、游标、验证记录或所有权 |
| 状态动作 | `task.create`、`task.transition`、`task.attribute` | 本文 §2、§3；创建规划/归属裁决及包含 entry_snapshot 的迁移后置 |
| 状态动作 | `baseline.apply`、`spec.update`、`task.curate`、`task.knowledge-dispose` | 本文 §3.4、§8.3、§8.4；当前发起任务主记录，成组活文件/索引/窄引用更新或单任务策展/知识处置 |
| 状态动作 | `task.check`、`review.launch`、`review.import`、`review.decide`、`task.reassess` | 本文 §3.5、§9、§6.2；检查结果/审查记录与导入槽位/归档或启动后的挂起复评 |
| 状态动作 | `session.bind` | 本文 §1.4、§6.1；唯一绑定、资格及必要首次所有权事实 |
| 状态动作 | `task.pause`、`session.stop` | 本文 §4.3；实际 WIP、暂停与释放 |
| 状态动作 | `writer.acquire`、`writer.release`、`writer.handover.begin`、`writer.handover.accept` | 本文 §4.2；代次、所有者、两段前后像 |
| 状态动作 | `definition.prepare` | 本文 §7.2；限定准备授权、准备记录与定义落盘结果 |
| 状态动作 | `run.advance`、`run.terminate` | 本文 §7.3、§7.4；人判、任务终态、处置和游标 |
| 状态动作 | `task.archive` | 本文 §5.3；碰撞预检、移动及提交后只读事实 |
| 状态动作 | `dependency.change`、`task.rework`、`task.replace`、`task.abandon` | 本文 §6；完整候选图、来源和改动处置 |
| 状态动作 | `asset.apply`、`repair.apply`、`uninstall.apply` | 本文 §5.4、§10；安装/升级投放或受控修复/退出；损坏 writer 卸载仅适用既有例外 |

状态动作统一 P 为 `{owner_ref, action_id, operation, inputs_digest, targets_digest}`，operation=action.kind，owner_ref 为本文 §1.2 所定义 owner 结构的规范 JSON（同 action.id 的输入取值），targets_digest 是 action.targets 去除回执/写入标记递归字段后的规范 JSON 哈希。`occurrence=H("wf-control-occurrence-v1", C(P))`；`anchor=H("wf-step-anchor-v1", C({rule_version, P}))`。纯断言不使用该公式，没有 action_id/occurrence/持久回执，无论调用会话是否持权都如此；下次查询重新读实际事实。需要写校验结论/改变游标时由对应状态动作消费断言结果并落盘，不能借查询接口写状态。

action.result 中的 control_assertion 为 `{step_id, rule_version, occurrence, anchor, evidence_refs}`，step_id=control.<operation>；这是本动作后置证据，不复制 task.execution。固定处理器逐个核 targets/steps/next_step 与实际后置后才生成该证据。消费点有三处：本动作结案前核证据和真实后置才允许 action.state=done；恢复入口先校验同 action.id 的后置决定补执行还是返回已完成；后续推进/释放所有权先拒绝相关未结动作，不能以回执存在掩盖内容变化。失败不生成成功证据，保留未完检查点及失败事实。

归档/终止的提交后置是特例：从原 action 的固定意图、实际移动/终态和可达提交派生 control_assertion，不把它写回已归档对象，也不为它再提交；恢复/成功报告/后继消费同一派生断言。其他状态动作在原 action.result 写 control_assertion。内部单记录迁移只核父动作的后置，不要求独立的 task.transition 回执；直接调用的 task.transition 必须有自身 action。结构检查不能定夺 glob 是否符合人的意图，这些输出需人裁决；这是固定处理器的语义边界，不是漏执行状态动作的出口。

## 12. 交付与验收追踪

### 12.1 设计稿 §8.1 逐项承接

本表将上位机制交付清单拆为可逐行核对的义务；同一行内列出的子项共用所指机制，不代表可省略其中一项。“跨轮基础项”从首轮起持续成立；“该轮交付·第二/三轮”在未交付阶段只允许报告相应能力不可用，不将缺实现记为已通过。每轮对象若已需要某项前置，就必须先交付该前置，分轮不是绕过门禁的许可。

| 登记 | 上位交付义务 | 本文定义/消费 | 交付归属 |
|---|---|---|---|
| D01 | 任务 schema、状态/阶段、判定字段写者 | 本文 §1.2、§1.3、§2.2 | 跨轮基础项 |
| D02 | skill/机制操作归属、只启用未绑定路由 | 本文 §2.1 | 跨轮基础项 |
| D03 | 准备定义/创建实例路由、静态与消费校验 | 本文 §7.1、§7.2、§7.3 | 该轮交付·第二轮 |
| D04 | 批准触碰面、规划版本、复杂度/TDD | 本文 §1.3、§2.3、§3.4 | 跨轮基础项 |
| D05 | 路径集合与内容指纹、检查有效性 | 本文 §3.1、§3.2、§3.5 | 跨轮基础项 |
| D06 | 未提交路径归属、外部变更与提交边界 | 本文 §3.3、§4.4、§5.3 | 跨轮基础项 |
| D07 | 依赖建删边、返工/替换/放弃 | 本文 §6 | 该轮交付·第二轮；首轮异常退出使用本文 §6.4 的单任务路径 |
| D08 | 跨任务目标碰撞预检、记录级幂等指纹 | 本文 §5.1、§5.2 | 跨轮基础项；第二轮加入全部依赖/实例目标 |
| D09 | repair 预览/确认/验证/留痕、关闭残留、历史锚点、不可解析记录 | 本文 §4.1、§5.4、§10.3 | 跨轮基础项；第三轮完成全部资产修复验收 |
| D10 | 读未知字段保留、写回不丢未知字段 | 本文 §1.1、§5.1 | 跨轮基础项 |
| D11 | 工作流格式、准备/自举、动作与验证边界、固定快照及版本维护 | 本文 §7.1、§7.2、§7.4 | 该轮交付·第二轮 |
| D12 | 步骤人判/略过、动作消费、自动任务/边与幂等映射 | 本文 §7.3 | 该轮交付·第二轮 |
| D13 | 实例正常结束、批量异常终止、保留任务独立接续 | 本文 §1.5、§7.4 | 该轮交付·第二轮 |
| D14 | 稳定会话身份、持久绑定、历史按需读取 | 本文 §1.4、§2.1、§5.2 | 跨轮基础项 |
| D15 | 会话/维护写者、原子获取/释放、两段交接与旧代次失效 | 本文 §4.1、§4.2 | 跨轮基础项 |
| D16 | 同对象 WIP 收工/恢复限制 | 本文 §4.3、§4.4 | 跨轮基础项 |
| D17 | 项目配置类型/范围/缺省、自举骨架 | 本文 §8.1 | 跨轮基础项 |
| D18 | spec 预算键、计数范围、数值缺省及降级 | 本文 §8.1、§8.4 | 跨轮基础项 |
| D19 | 命令引导、installed/源码目标、坏配置独立恢复 | 本文 §8.2、§10.5 | 跨轮基础项 |
| D20 | Python 三级解析、缺系统 Python 的已有配置出口 | 本文 §8.2 | 跨轮基础项 |
| D21 | 执行器探测/确认、首次写入批准、项目标识匹配 | 本文 §3.4、§8.1、§8.2 | 跨轮基础项 |
| D22 | 发行引用与本地清单解析 | 本文 §10.2 | 该轮交付·第三轮；首轮开发态也固定所用资产/模板版本 |
| D23 | spec 三时点加载、策展/读取侧车、排序/预算 | 本文 §8.3、§8.4 | 跨轮基础项 |
| D24 | 本地 spec 全部变更、持久引用统计/治理 | 本文 §8.4、§8.5 | 跨轮基础项 |
| D25 | 审查身份声明、报告核对及新鲜度 | 本文 §9.1、§9.2 | 跨轮基础项：首轮允许初始化/治理面任务，可能属复杂，故成对适配须首轮就绪 |
| D26 | 审查读取/外发范围、报告写权与导入 | 本文 §9.1、§9.2 | 跨轮基础项，与 D25 同批 |
| D27 | writer 公共字段与维护回执隔离、整文件提交 | 本文 §1.4、§4.5 | 跨轮基础项 |
| D28 | 预览令牌签发/校验 | 本文 §10.3 | 跨轮基础项；第三轮补全升级/purge 路径 |
| D29 | 固定原因码及输出三档 | 本文 §11.1 | 跨轮基础项 |
| D30 | 模板占位标记集 | 本文 §2.3、§10.2 | 跨轮基础项 |
| D31 | 审查适配副本投放、三方升级和卸载覆盖 | 本文 §9.1、§10.1、§10.4、§10.5 | 首轮投放为跨轮基础项；完整发行生命周期为第三轮交付 |
| D32 | 锁原语、落点、支持范围与存活探测 | 本文 §4.1 | 跨轮基础项 |
| D33 | 资产类型/落点/所有者/升级卸载覆盖表 | 本文 §10.1 | 跨轮基础项；第三轮验收全部适用分支 |
| D34 | 最终门禁与正常/异常完成边界 | 本文 §9.3、§6.4 | 跨轮基础项 |
| D35 | 每条门禁到验收场景的映射 | 本文 §12.2、§12.3 | 跨轮基础项 |
| D36 | 每个固定 required 步骤的执行/检查面 | 本文 §11.2、§11.3 | 跨轮基础项，步骤随交付增加 |
| D37 | 最小安装/自检、完整安装/升级/退出 | 本文 §10 | 首轮最小安装/独立恢复为跨轮基础项；完整发行入口为第三轮交付 |
| D38 | 机制/实现分工、使用速查与后续验证责任 | 本文 §0、§12.4 | 跨轮基础项；实现方案产出实际布局/命令和速查 |

首轮复杂审查按真实对象执行，D25 的提前交付选择来自初始化/治理面可能命中的既有判据；这不把所有任务预先判为复杂。若首轮实际范围只含已初始化项目的轻任务，可以在实现规划中明确缩小验收对象，但不能以审查未实现让复杂任务正常完成。

### 12.1.1 设计稿委托句反查表

设计稿正文散落的「由机制设计固定/确定/声明/交付」委托句按下表反查本稿落点；新增修订时按句对照，出现委托句无落点或落点失效即缺口。本表承接设计稿正文明文委托（含隐性委托中已落位的典型项），与上表 D 行并列、不互相替代；表外隐性委托以所属 schema 与算法的逐键定义为准。

| 设计稿委托句（章节） | 委托内容 | 本稿落点 |
|---|---|---|
| 设计稿 §1.1 执行器解析（轻量指纹算法） | 确认记录元组的大小与修改时间算法 | 本文 §8.2（确认集合单项 size/mtime_ns 元组） |
| 设计稿 §1.1 执行器解析（最低小版本） | 脚本使用的最低 Python 小版本 | 本文 §1.1（3.11）与发行说明 |
| 设计稿 §8.2 判定物（预览令牌） | 令牌的生成/校验/绑定 | 本文 §10.3（nonce 128 位、绑定预览摘要、同进程失效） |
| 设计稿 §8.2 判定物（占位标记集） | 模板占位标记与使用位点 | 本文 §2.3、本文 §10.2（template_markers 的 formats/uses） |
| 设计稿 §8.2 判定物（归属判定） | 提交归属的判定编码 | 本文 §3.3（trailer/裁决/继承）、本文 §5.1（action 的归属核验） |
| 设计稿 §8.2 判定物（原因码） | 固定码表，只增不改义 | 本文 §11.1（首版 33 枚）与处理器映射表 |
| 设计稿 §3 项目配置（project_id 格式与生成） | 随机生成、实际不重复、重建不复用旧值 | 本文 §1.1（UUID4）、本文 §5.4（重建比对）、本文 §8.1（project_id 行） |
| 设计稿 §3 项目配置（预算键/计数范围/数值缺省） | 具体键与缺省值 | 本文 §8.1（全键表）与发行骨架 |
| 设计稿 §4.4 项目写入权（维护标识派生） | 由操作和代次派生的具体编码 | 本文 §1.4（wf-maintenance-op-v1 公式） |
| 设计稿 §4.4 项目写入权（互斥支持范围） | 支持的系统与退化行为声明 | 本文 §1.1、§4.1（flock、Linux 本地 FS、未声明即不支持） |
| 设计稿 §5.2（任务 id 与 schema 编码） | 具体 id 与 schema 编码 | 本文 §1.1（Id）、本文 §1.3（任务记录表） |
| 设计稿 §5.7 准备定义通道（文件编码） | 准备记录的具体文件编码 | 本文 §1.4（字段 schema；文件名/落点归本文 §10.1 实现方案） |
| 设计稿 §6.2 预算降级（计数范围） | 具体键和每次输出的计数范围 | 本文 §8.4（码点计数口径） |
| 设计稿 §7.2 发行身份（引用命名与清单路径） | 引用命名与清单路径 | 本文 §10.2（refs/tags/wf-v…、wf-release.json） |
| 设计稿 §8.1 交付清单（分轮标注） | 逐项机制设计编码 | 本文 §12.1 D01–D38 |


### 12.2 机制到设计稿场景的映射

场景名逐字引用设计稿 §8.2。G 编号只作为本文门禁/检查面定位，不是新的业务状态或第二原因码表。每行的正例与反例以设计稿相应行作为上位断言，本文给出其记录与算法落点；charter 人判项保持人审，不伪装脚本可判断意图。

| 门禁/检查面 | 本文落点 | 设计稿 §8.2 场景 |
|---|---|---|
| G01 目标、边界、演进与停止的人审 | 本文 §0、§12.1 | `扩展与取舍（charter T2、charter T5）`；`边界与边界外出口（charter T3）`；`减法与停止（charter T6）`；`使用负担与缺口（charter T5）`；`演进判断顺序（charter T5）`；`保留机制必答（charter T6）` |
| G02 效力、同批修订与闭环责任 | 本文 §0、§12.4 | `效力与冲突（charter T1）`；`修订同批义务（charter T7）`；`等效替换（charter T4）`；`闭环四条件（charter T4）` |
| G03 仓库/分支观察边界 | 本文 §3.1、§10.4 | `多分支与嵌套仓库（charter T3）`；`分支来源核对` |
| G04 用户定义结构与边界 | 本文 §7.1、§7.2 | `用户定义零框架改造`；`定义有界校验`；`定义与实例固定`；`工作流兼容与迁移` |
| G05 分时消费与展开 | 本文 §7.2、§7.3 | `单任务与多任务流程`；`准备定义与自举`；`验证分时解析`；`接续与任务归属`；`顺序依赖授权`；`人判与略过` |
| G06 实例终态与隔离 | 本文 §1.5、§7.4 | `实例正常与异常终态`；`规划实例直接终止`；`实例放弃与保留`；`终止中断与历史校验`；`实例与产物隔离` |
| G07 身份与固定绑定 | 本文 §1.4、§2.1 | `会话固定绑定`；`压缩与新会话`；`无稳定会话身份`；`会话实例标识`；`绑定历史按需读取` |
| G08 写权、交接与收工 | 本文 §4.1、§4.2、§4.3 | `单工作区串行写入`；`释放与显式交接`；`日常收工`；`所有权中断恢复`；`无 hook 强度`；`暂停插单恢复` |
| G09 维护组与持久化 | 本文 §4.4、§4.5 | `维护写者`；`未提交记录存在性` |
| G10 恢复与锚点 | 本文 §5、§10.5 | `普通任务持久恢复`；`历史锚点不可达`；`数据与恢复`；`受控修复` |
| G11 规划、自举与 Git 就绪 | 本文 §2.3、§3.4、§10.4 | `入口与基线子路由`；`规划授权`；`初始化自举`；`Git 就绪`；`执行器首次写入` |
| G12 范围与检查有效性 | 本文 §2.3、§3 | `机读触碰面`；`同路径交替`；`指纹内容源`；`最终知识变更` |
| G13 共存与启动互斥 | 本文 §2.1、§3.3、§10.5 | `共存与重装`；`Trellis 互斥`；`紧急变更边界` |
| G14 依赖和异常退出 | 本文 §6 | `返工接续`；`异常归档边界`；`放弃改动处置` |
| G15 本地知识与真实复用 | 本文 §8.3、§8.4、§8.5、§9.3 | `extracted 生命周期`；`spec 正向积累`；`spec 跨任务复用`；`知识删除与依赖解除`；`策展引用统计`；`读取留痕完整性`；`无 MCP 全流程` |
| G16 配置、升级与发行 | 本文 §8.1、§10.2、§10.4 | `升级三方判断`；`流程与配置`；`发行身份` |
| G17 执行器、身份与引导 | 本文 §8.1、§8.2、§5.4 | `Python 执行器`；`本地命令引导`；`执行器配置可信`；`执行器确认绑定`；`确认记录身份`；`项目标识生命周期` |
| G18 预算与固定执行面 | 本文 §8.4、§11 | `spec 预算`；`固定流转程序化`；`判定物与原因码` |
| G19 审查身份、人数及适配 | 本文 §9、§10.1 | `审查与正常完成（charter T4）`；`审查 CLI 身份确认`；`审查适配副本` |
| G20 审查读取、外发、写权及锚点 | 本文 §9.1、§9.2 | `审查材料外发`；`审查读取范围`；`审查报告写权`；`审查回执锚定` |
| G21 资产与锁生命周期 | 本文 §4.1、§10 | `资产落点`；`互斥与锁生命周期`；`锁删除与人工清理`；`锁文件归属` |
| G22 复杂度与 TDD | 本文 §1.3、§2.3、§8.1、§9.3 | `复杂度分级一致性`；`TDD 开关` |

### 12.3 需人裁决档与恢复窗口

本表反向覆盖设计稿 §8.2 三档场景；实际输出包含待决事实与出口，不能只给 generic needs_decision。

| 上位三档场景 | 相关门禁 | 待决事实/出口在本文的落点 |
|---|---|---|
| `设计稿与 charter 冲突` | G02 | 本文 §0：列两侧条款与输入版本，人裁后同步 |
| `需求是否属边界外` | G01 | 本文 §0：交 charter T3 判定，不在机制层开新通道 |
| `承诺或证据是否成立` | G01 | 本文 §12.4：按上位证据和观察判断，不以实现估算替代 |
| `删除会破坏什么承诺` | G01、G15 | 本文 §8.4：指出现存引用/承诺，保留或人判去留 |
| `语义分叉识别` | G18 | 本文 §11.3：结构算法与人判面分开，未定前不自动执行 |
| `分支来源未确认` | G03 | 本文 §10.4：具体分支与当前缺失路径，去原分支或确认新安装 |
| `历史锚点或旧写者事实待核对` | G08、G10 | 本文 §4.1、§5.4：核原文/Git/进程线索和旧写者停止，不抢占 |
| `WIP 去向或维护范围未明` | G08、G09、G14 | 本文 §4.3、§4.5、§6.4：保留现状，待实际处置而非仅人选项 |
| `Trellis 线索与指令状态未明` | G13 | 本文 §2.1：核当前宿主配置/适用指令和会话事实；已加载冲突换新会话 |
| `glob 命中但范围语义存疑` | G12 | 本文 §3.1、§3.3：核归属和意图，确认原范围或回 Plan |
| `审查不可用` | G19 | 本文 §9.2、§11.1：核缺哪一 CLI 和实际分级，仍复杂暂停/异常退出 |
| `知识准入冲突` | G15 | 本文 §8.3、§8.4：核真实依据与重复/冲突，人裁合并/拒绝/另立 |
| `工作流动作/验证语义存疑` | G04、G05 | 本文 §7.2、§7.3：核来源/范围/恢复事实，澄清或回 Plan |

三个运行夹具分别为 F0（空目录、无 Git/基线）、F1（有代码与本地测试、无流程/基线）、F2（有其他流程与普通外部提交）。F2 的其他流程资产保持不变；另构造适用 Trellis 托管指令激活/纯残留两个分支。每个夹具各跑普通正常闭环与必要拒绝，另用下表的初态/触发/输出区分特有边界。下列全为待实现运行的断言，不记为已运行。

| 夹具/窗口 | 初始事实与触发 | 预期输出与恢复 |
|---|---|---|
| F0 自举 | 无 HEAD/基线，安装后直接请求开工 | 缺 Git/批准时 blocked；授权建立 HEAD、批准初始化后可开工；后续命令待建立不阻止规划 |
| F1 接入 | 无 wf 基线，人调用 bootstrap，代码萃取 spec | extracted 而非伪核实日期；必要检查实际通过后人 finish；缺命令报告缺失 |
| F2 共存 | 其他流程提交无交集，wf 恢复；再制造相关路径变化 | 无交集可继续，相关变化失效并重检；不追认所有外部提交 |
| F2 Trellis | 已确认当前有效指令；对照仅残留数据无有效指令 | 前者保持未启用，后者人核实后可启用；未知输出需人裁决 |
| 两段交接中断 | begin 后旧代次已失效，accept 未运行 | recovering；双方无业务写权，指定接收者核事实后 accept |
| WIP 保留 | A 暂停保留未提交业务，writer idle，B 请求 acquire | B 被工作区边界挡住；A 同对象核 WIP 后可恢复 |
| 维护无提交许可 | upgrade 完整应用并有回执，新任务路径无交集 | 维护释放、保留独立待提交组；新任务可开工，writer 整文件未经维护提交许可不能捎带 |
| 目标碰撞 | 归档目的地已有不匹配对象 | 第一次状态写前拒绝；原任务状态/位置不变 |
| 落盘后游标未写 | 目标是同 action 后像，next_step 落后 | 只补后置和游标；不重复创建 R/实例任务 |
| 归档提交后崩溃 | persist_pending 已入 HEAD，进程未输出成功 | 只读核持久化完成；不再归档或提交自身“成功”字段 |
| 实例规划直接停止 | 无任务或只有未开工任务，人终止 | 未生成记未执行；已生成逐项放弃/保留，无需 Check pass |
| spec 后变更 | Check pass 后 spec 内容或路径变化 | 当前 anchor 不同，旧 pass 不用于 Finish；重读/重检 |
| 坏执行器/坏 writer | 项目解释器失效、writer 原文损坏，人卸载 | 独立脚本用可用解释器及最小锁，人确认旧写者停止后仅退出；不造可业务推进代次 |
| purge 删除尾窗 | 数据已删但还持锁，另一安装进程启动 | 同一锁阻止并发；卸载释放后新安装才可自举，锁路径不删除 |
| debug 双源合并 | 同一 verification_id 的 failed 事实分处 check_history 与 Execute 期声明证据两处（阈值 4：两源各 2 次互不重复、合并累计 4 = 阈值；两源各 1 次、合并累计 2 < 阈值——两种互斥情形；另设同一失败事件已入 check_history 又被声明计入的判重情形、及两条声明 dedupe_refs 指向同一 check_id 的双扣情形） | 倍数判定与 debug-ruling id 归属按本文 §1.3 的合并与判重规则：两源各 2 次、合并累计 4 = 阈值时须判为已跨倍数并产生待决项（multiple 为 1，与合并累计跨过的倍数一致）；两源各 1 次、合并累计 2 < 阈值时不得判为已跨倍数；判重情形下入口剔除已计数失败、合并累计按真实失败事件数计；双扣情形（两声明 dedupe_refs 指向同一 check_id）按 WF_SEMANTIC_DECISION 拒绝（check_id 全任务唯一），求和越界（累计 < check_history 条目数或为负）按 WF_RECORD_INVALID 拒绝 |
| 单 Check 内多次重试 | 同一 verification 在一次 Check 内重试多次后 passed | check_history 中该 Check 只有一条 passed 最终结果、不产生 failed 条目；机械检测不计该重试形态，重试期间的真实失败由 Execute 期声明兜底承载（本文 §3.5、§1.3） |
| 机械修订不重复批准 | 任务已批准开工后，PRD 只修排版/措辞并登记 equivalences（每条衔接有 Decision），随后 Check/Finish | 等价链核对通过：check_anchor 的 plan_version/acceptance_digest 与内容类回执 P 的 plan_version 均经链归一不变（occurrence 不变、原 completed 回执可查得），旧 Check pass 与 task.plan-approved/work-satisfied/knowledge-disposed 的 completed 回执不失效、无重复人批准；改验收口径或范围时链断开 → P/occurrence 变化、回 Plan 重批（对齐设计稿 §4.2“只修排版……不重复问人”） |
| 规则类失配与内容类稳定 | 发行资产字节变化（如流程文档错字修正）后，既有任务恢复推进 | 规则类回执（check-passed/changes-persisted 等）因 effective_rule_version 失配须重核，内容类回执（plan-approved/spec-loaded/work-satisfied/knowledge-disposed/retrospective-done）不因规则字节变化失配、不重复人批准或重读未变 spec；changes-persisted 重核 rules_digest 兼容性 |
| 启动校验顺序与首报项 | 构造同时含身份冲突与记录不可解析的故障态，分别经启动与开工入口进入 | 两个入口首报项一致（先身份/绑定类、后记录类——启动序列①-④为身份/绑定/写权、⑤起为记录类）；启动十步按固定顺序执行，③多候选报 WF_RECORD_INVALID（恢复出口）而非 WF_WRITER_BUSY，⑩存在未处置组报 WF_WIP_UNRESOLVED、去向未明报 WF_WORKSPACE_UNRESOLVED（档位由码表派生）；活动记录不可读时③报 WF_HISTORY_UNRESOLVED（未知态）并先列该事实 |
| 缺项分派与未知优先 | 构造 changes-persisted 的三种缺项原因（未授权/提交失败/WIP 未处置）、work-satisfied 的必需用户动作未答、批准与版本不符，及活动记录不可读的启动态 | gate.evaluate 逐项按原因事实选码：未授权 → WF_COMMIT_NOT_AUTHORIZED、提交失败 → WF_PERSISTENCE_FAILED、WIP 未处置 → WF_WIP_UNRESOLVED、用户动作未答 → WF_SEMANTIC_DECISION、批准失配 → WF_APPROVAL_MISSING（各码档位与本文 §11.1 码表一致，出口按码分派不混淆）；记录不可读 → 未知态 WF_HISTORY_UNRESOLVED、先列事实，可确证损坏并用 WF_RECORD_INVALID，不据未知出放行/阻断 |

夹具与设计稿场景的绑定固定如下；通用场景仍可在三个夹具重复运行，绑定只指定必须出现的专属覆盖，避免实现阶段把同一套样本复制三遍而漏掉存量/共存边界：

| 夹具 | 必须覆盖的设计稿 §8.2 场景 | 额外要求 |
|---|---|---|
| F0 全新项目 | `准备定义与自举`、`验证分时解析`、`初始化自举`、`Git 就绪` | 从无 HEAD/基线开始；验证“未来建立的命令”不阻止规划，但消费前必须真实就绪；无 MCP 全流程至少跑一次 |
| F1 存量无流程 | `extracted 生命周期`、`无 MCP 全流程` | 先 bootstrap 再进入普通任务；初始代码/测试/文档作为本地证据，extracted 不得伪造日期；spec 新增/更新/拆分/合并/改名/删除及 index/metadata 同步至少各有一次正反断言 |
| F2 存量有其他流程 | `共存与重装` | 保留其他流程资产和无交集外部提交；另跑 `Trellis 互斥` 的有效指令与纯残留分支、卸载期提交以及相关路径外部变更 |

三夹具都必须覆盖普通正常闭环、至少一条范围/授权拒绝和一次暂停/接续；实现阶段把每个场景记录为 F0/F1/F2、入口、初态、输出和实际结果。缺少夹具专属场景的正反样本时，该夹具不算完成，即使另外两个夹具通过。

实现夹具必须覆盖每个 action 步骤前/后中断、读回不明、提交失败和真实目标碰撞。单进程模拟不证明跨进程互斥；本文文本推演不证明宿主新会话身份或人判真实性。全部适用场景、三夹具与独立复核完成后才可声明实现可用。

### 12.4 后续交付与本稿收口

实现方案以本文编码为输入，给出文件布局、实际脚本/子命令参数、版本化发行物、自有审查适配和单页使用速查；速查消费设计稿 §8.1，不复制另一套规则。实现阶段还须验证 Python 最低版本、支持文件系统、锁中断/恢复、host 身份持久性、可发现入口及成对审查协议。未核实能力明确报告，不从本稿的字段可解析推出可用。

设计稿 §8.2 的真实使用观察记录由当前任务/实例的交接、审查声明和本地观察承载：样本版本/环境、对象类型、确认/调用/加载次数、耗时、写权交接/恢复结果、CLI 可用或不足、身份不可用、关闭未收工、连续短对象换会话成本。汇总可重建自原记录，不增跨项目采集或常驻观察器。未运行/放弃必须给原因分类和依据；缺样本为未知，不计零。只有符合 charter T5 的实际场景放弃证据才支持候选重议；操作成本不撤回 charter T4 承诺。

本稿验收分两轴：上位承接/内部语义轴检查定义、写者、消费、前后置与恢复出口；机械轴检查引用、schema 示例、执行面及场景映射。作者自检与独立会话复审分开记录；未参与编写的会话须绑定本稿内容版本、声明覆盖轴与未覆盖项，人工确认后才称机制设计定稿。设计阶段不以未运行的框架夹具阻止交付待审稿，也不以文本通过宣称框架已实现。
