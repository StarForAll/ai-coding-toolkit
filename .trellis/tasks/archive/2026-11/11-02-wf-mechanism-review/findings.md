# wf-framework-mechanism 机制设计深度审查发现（findings）

- 审查任务：11-02-wf-mechanism-review
- 审查日期：2026-11-02
- 审查输入版本（绑定机制稿 §0.1 声明的摘要，已逐一核验与工作树一致）：
  - wf-framework-design.md `4419b03a…fd61d`
  - wf-framework-charter.md `8b816ee4…3c16`
  - wf-framework-design.index.md `3513d1d5…c62e2`
  - wf-framework-design.sources.md `47484498…4a25b`
  - wf-framework-mechanism.md（审查对象，全文 1030 行通读）
- 机检证据：`scripts/validate-wf-design.py` 全绿（机制稿引用 321；二值场景 91/91；三档场景 13/13；输入摘要 4/4）。机检通过不证明语义正确，以下发现均以人工通读对照为据。

## 覆盖轴声明

- 已覆盖：① 跨文档一致性轴（机制稿行为契约 ↔ 设计稿/charter 条目逐项对照）；② 可实现性轴（schema 可机判性、算法确定性、枚举与委托链完整性）；③ 状态机与门禁完整性轴（开工门禁/最终门禁/required 步骤逐项核对）；④ 恢复与幂等路径轴（§5 重入四态、§11.2 回执复用、§4 写权恢复）。
- 未覆盖（不据本报告下结论）：三夹具实际运行、宿主会话身份真实传递、发行/升级/卸载矩阵的运行验收、skill 正文与流程文档实际写作质量——这些按设计稿 §8.2 属实现阶段验收。

## 总体结论

未发现 A 级（与 charter/设计稿正面冲突、颠覆初衷或核心承诺的矛盾）。机制稿整体质量高：四份输入哈希吻合、D01–D38 逐项承接、状态机与原因码表完整、自指消除（清单/回执/锚点不哈希自身）处理周密。发现集中在「上位已定但机制编码缺漏」与「跨文档解释差」两类，共 3 项 B 级、5 项 C 级。

## B 级发现（缺漏 / 不可机判，建议修复）

### B1 巡检触发条件「阶段尾任务归档」不可机判

- 定位：机制稿 §8.5（wf-framework-mechanism.md:627）；设计稿 §5.4（wf-framework-design.md:317）、§5.1（:270）。
- 证据：设计稿 §5.1「首尾角色是人的约定，不建立角色继任解析器」；任务 schema（机制稿 §1.3）无任何阶段尾/尾任务标记字段；机制稿 §8.5 原样把「阶段尾任务归档」列为巡检触发之一。
- 影响：实现者无法判定哪个归档任务属阶段尾，该触发条件不可实现；照字面实现只能靠任务标题猜测，违反「事实未知就给待核对出口」的自身纪律。
- 建议（择一，需人裁决）：① 机制稿将该触发并入「人发起」（阶段收尾本就伴随人的主动意图，语义无损）；② 在任务记录增加由人在创建/批准时声明的阶段尾标记字段（注意：设计稿 §5.1 说不建立「角色继任解析器」，静态标记不违反该条，但须按设计稿 §0 维护协议登记）。同步修改设计稿 §5.4/§6.4 的同一触发措辞。

### B2 设计稿开工门禁项「无未决范围问题」未进入机制稿开工核对序列，且 Plan 期人判问答无记录载体

- 定位：设计稿 §4.2 开工门禁（wf-framework-design.md:189，枚举含「无未决范围问题」）；机制稿 §2.3 开工核对序列（wf-framework-mechanism.md:220）。
- 证据：机制稿 §2.3 的开工顺序为「启用/绑定/写权 → 记录可解释 → 工作区/候选 → 规划提取/批准/模板标记 → touch_paths 安全及语义未决 → 依赖/暂停/挂起 → 基线/配置 → Git HEAD → verification.resolve(start) → required 步骤」，逐项比对设计稿开工门禁十项，唯缺「无未决范围问题」；全文检索无「未决范围」「待决问题」编码。关联缺口：设计稿 §4.3 grilling 原语要求「每个待决问题编号并附推荐答案、人在一轮内批量作答」，机制稿 execution.human_decisions 只承载工作流人判点（id 来自定义 human_points），普通任务 Plan 期的未决问题/人判答复没有任何 schema 落点，机器无从核对「已澄清」。
- 影响：门禁 1（开工前 required 集合）与设计稿 §4.2 存在覆盖缺口；grilling 完成信号不可留痕复核，属「判定字段无写者与消费点」的登记缺口。
- 建议：① 在机制稿 §2.3 开工核对序列补「无未决范围问题」一项（出口 WF_SCOPE_UNRESOLVED / WF_SEMANTIC_DECISION）；② 为 Plan 期人判问题补编码——最小方案是扩展 plan 或 execution.human_decisions 的人判点 id 来源（允许无工作流上下文的自编号，如 `plan-q-<n>`），Decision 结构可原样复用；③ 按 §0.2 登记该字段的写者/消费者/失败出口。

### B3 定义级「必要验证」的分布式解读与设计稿格式枚举存在解释差

- 定位：设计稿 §5.7（wf-framework-design.md:355）「统一格式含格式版本、稳定工作流 id、内容版本、用途/适用条件、输入、有限顺序步骤、完成条件和必要验证」；机制稿 §7.1（wf-framework-mechanism.md:467）「设计稿要求的定义级"必要验证"由各任务步骤的 verifications 共同承载……不另在定义根复制一份验证清单」。
- 证据：设计稿把「必要验证」列为定义格式根级组件（与 completion 并列）；机制稿将其解读为各 task 步骤 verifications 的汇总承载，定义根不设该字段，并自行给出「未明确承载步骤的必要验证使静态校验不完整」的补位规则。
- 影响：非行为矛盾（机制稿解读自洽且有减法依据，charter T6），但属机制稿单方面消解上位格式枚举的根级字段；按 charter T1「上位判据未给出答案时下位交人裁决」，该解读未像 baseline_head 那样登记为获批语义修订（§0.1 只登记了 2026-11-02 的首次基线人裁）。留此缺口，后续复审/实现可能重新质疑该字段归属。
- 建议：补一次轻量人裁留痕（在 §0.1 或任务修订记录登记「必要验证分布化承载」经人确认），或回写设计稿 §5.7 措辞为「完成条件和由各任务步骤 verifications 承载的必要验证」。

## C 级发现（改进建议，不阻断实现）

### C1 `C(x)` 规范化中「集合型数组先按其键排序去重」未指定排序键

- 定位：机制稿 §1.1（wf-framework-mechanism.md:69）。
- 证据：「按其键排序」语义不明（按元素的哪个键？多键时顺序？）。§10.2 对 assets/required_steps 明确了排序键，其余数组（specs、curation、prerequisites 等）进入 H() 输入时无排序规则。
- 影响：单实现内自洽，但哈希公式是跨版本承诺（回执 anchor/occurrence 长期比对），排序规则歧义会让不同实现或未来重构产生不同哈希，导致回执无谓失效。
- 建议：明确为「按元素规范 JSON 的 UTF-8 字节序排序」，或逐 schema 声明排序键（推广 §10.2 的做法）。

### C2 锁初始化未完成的退出未映射固定原因码

- 定位：机制稿 §4.1（wf-framework-mechanism.md:294）「并发观察到空/不完整标记者退出报告初始化未完成」。
- 证据：§11.1 码表自称首版固定完整；该出口未指明复用哪个码（WF_WRITER_BUSY 语义是占用，WF_RECORD_INVALID 语义是记录非法，均不贴切）。
- 建议：指明复用码（最接近 WF_CAPABILITY_UNAVAILABLE/ WF_WRITER_BUSY 之一并写明 facts 区分），或按「只增不改义」原则在首版内新增一枚。

### C3 准备记录「文件编码」的委托链存在落点差

- 定位：机制稿 §1.4（wf-framework-mechanism.md:125）「实际路径由实现方案给出」；设计稿 §5.7（wf-framework-design.md:359）「具体文件编码由机制设计确定」；机制稿 §10.1 又把「细分文件名」归实现方案。
- 影响：设计稿委托机制设计固定的「文件编码」，机制稿只交付了字段 schema，路径/文件名转推实现方案——两份文档对同一委托的归属表述不一致，复审时易被判「委托未履行」。
- 建议：在 §1.4 准备记录行补一句「文件编码（字段 schema）由本文固定，文件名/落点按 §10.1 归实现方案」，消除歧义。

### C4 维护写者「操作标识」的派生编码未交付

- 定位：设计稿 §4.4（wf-framework-design.md:232）「维护标识可由操作和代次派生，具体编码交机制设计」。
- 证据：机制稿 §1.4 holder 维护 scope 为「操作、预览摘要与精确路径」，§1.4 maintenance_results 按操作 id 保存，但均未给出「由操作和代次派生」的具体公式。
- 建议：补一句派生规则（如直接复用 maintenance_results 的 operation id，或 `H("wf-maintenance-op-v1", C({operation, generation}))`），闭合设计稿的显式委托。

### C5 机制稿挂起复评条件较设计稿「唯一定义」多一个合取项，未标注上位依据

- 定位：机制稿 §6.2（wf-framework-mechanism.md:432）「……T 前置全部满足，且相关跨记录动作已恢复」；设计稿 §5.6（wf-framework-design.md:337）唯一定义为五条件（无此项）。
- 影响：与设计稿 §5.4「失败/中断先恢复，不先清挂起掩盖残留」精神一致，属合理细化而非矛盾；但「唯一定义」条目被机制稿扩展而无引用注记，违反「每项判据只在一个位置定义，其余位置引用」的维护协议风格。
- 建议：在机制稿 §6.2 该句后标注上位依据（引用设计稿 §5.4 的恢复先行句），或回写设计稿把该合取项并入唯一定义。

## 未采纳的审查线索（核对后排除）

- 挂起清除/复杂度分级/体积阈值/巡检计数规则/审查轮次与人数/执行器三级解析与确认元组/两段交接/维护回执隔离/归档幂等/required 回执复用机制——逐项与设计稿对照后语义一致，不列为发现。
- spec frontmatter「extracted」取值按「字符串双引号」规则可解析，不构成歧义。
- 锁等待 5 秒、巡检 O(n²) 潜在比对等性能特征与单人本机定位相称，不列为发现。

## 修复建议的处置顺序（若用户批准修复）

1. B1、B2（补机制编码与门禁项，涉及机制稿正文与可能的设计稿同步，按 charter T7 同批义务）。
2. B3（人裁留痕或设计稿一句措辞同步）。
3. C1–C5（机制稿局部补句，均不改变行为语义）。

## 修复记录（2026-11-02，用户批准后执行）

处置方式均按上文各条的指定方案；行号为修复后工作树行号。

### B1（建议①：并入人发起）

- `docs/workflows/wf-framework-mechanism.md:628`（§8.5）：触发改为「人发起，或正常归档累计数达到 inspection_every_tasks 的整数倍」，并注明阶段收尾由"人发起"承载、不设"阶段尾任务归档"触发；累计数重建语义不变。
- `docs/workflows/wf-framework-design.md:317`（§5.4 周期巡检）：同步移除「阶段尾任务归档」触发，保留整数倍触发与计数重建语义，括注不设阶段尾触发的理由。
- `docs/workflows/wf-framework-design.md:471`（§6.4 周期清点）：移除「阶段收尾」触发，改为「巡检节奏触发或人发起时」，括注同上。
- 索引同步：`docs/workflows/wf-framework-design.index.md:62`（row 48 项目判定）删除语义消费列中「§5.4（尾任务巡检）」「§6.4（阶段收尾清点）」两条失效注记（两节不再消费阶段尾语义）；row 57 周期巡检的消费点不涉及该触发，未改。设计稿 §5.1「首尾角色是人的约定」未动。

### B2（补门禁项 + plan-q 编码）

- `docs/workflows/wf-framework-mechanism.md:221`（§2.3 开工核对序列）：在 touch_paths 之后、依赖之前补「无未决范围问题（execution.human_decisions 无 pending 项，失败出口 WF_SEMANTIC_DECISION）」，复用现有码，不新增。
- `docs/workflows/wf-framework-mechanism.md:119`（§1.3 execution 段落）：人判点 id 来源扩展为 human_points id 或普通任务 Plan 期自编号 `plan-q-<n>`（任务内正整数从 1 递增）；问题与推荐答案随规划材料留痕；Decision 结构复用 §1.1。写者=批准/开工入口（人一轮内批量作答后写入）；消费者=开工核对（无 pending 项，即已编号问题均有对应 Decision）与 task.plan-approved 证据核对；失败出口 WF_SEMANTIC_DECISION。
- `docs/workflows/wf-framework-mechanism.md:217`（§2.3 规划批准段落）：补 grilling 类待决问题逐项 plan-q 编号+推荐答案、人批量作答后由入口写入 execution.human_decisions（对齐设计稿 §4.3 grilling 行的完成信号），未答项保持 pending。
- `docs/workflows/wf-framework-mechanism.md:191`（§2.2 批准规划行）：「只写 plan」扩为「只写 plan 与 Plan 期人判答复（execution.human_decisions）」，消除批准入口新写者与该行的字面冲突（B2 引入写者后的必要一致性修正，见下「需人工复核」）。
- 登记：`docs/workflows/wf-framework-mechanism.md` §0.2 修订重点追踪表新增一行「Plan 期人判问答（execution.human_decisions 的 plan-q id）｜本文 §1.3、§2.3｜开工核验（无未决项）、task.plan-approved 证据、WF_SEMANTIC_DECISION」。

### B3（人裁留痕 + 设计稿措辞同步）

- `docs/workflows/wf-framework-design.md:355`（§5.7）：「完成条件和必要验证」改为「完成条件和由各任务步骤 verifications 承载的必要验证」，与机制稿 §7.1 的分布化解读一致。
- `docs/workflows/wf-framework-mechanism.md:21`（§0.1）：并列登记本日同批人裁「必要验证由各任务步骤 verifications 承载」并同步设计稿 §5.7 措辞。
- 摘要链：设计稿与索引内容变化后重算 SHA-256 并更新 §0.1 表格（`wf-framework-mechanism.md:25` 设计稿 f41173d9…、`:27` 索引 14739427…）；charter 与 sources 未改，摘要不变。

### C1–C5

- C1 `docs/workflows/wf-framework-mechanism.md:70`（§1.1）：「集合型数组先按其键排序去重」改为「先按元素规范 JSON 的 UTF-8 字节序排序去重（另在所属 schema 声明排序键的从其声明，如本文 §10.2）」。
- C2 `docs/workflows/wf-framework-mechanism.md:295`（§4.1）：锁初始化未完成退出补「输出 WF_CAPABILITY_UNAVAILABLE，facts 记锁标记不完整及路径」（在 WF_CAPABILITY_UNAVAILABLE 与 WF_RECORD_INVALID 中选用前者：锁对象是运行态互斥设施而非持久记录，"所需能力未支持/不可用"语义更贴切；未新增码）。
- C3 `docs/workflows/wf-framework-mechanism.md:126`（§1.4 准备记录行）：「实际路径由实现方案给出」改为「准备记录的字段 schema 由本文固定，文件名/落点按本文 §10.1 归实现方案」，闭合与设计稿 §5.7「具体文件编码由机制设计确定」的委托链落点差。
- C4 `docs/workflows/wf-framework-mechanism.md:142`（§1.4 writer 段）：补派生规则「维护操作标识取 maintenance_results 的 operation id；无结果登记的维护动作由 `H("wf-maintenance-op-v1", C({operation, generation}))` 派生」，闭合设计稿 §4.4 的显式委托。
- C5 `docs/workflows/wf-framework-mechanism.md:433`（§6.2）：复评条件句后补「（上位依据：设计稿 §5.4 失败/中断先恢复，不先清挂起掩盖残留）」，不改设计稿。

### 机检输出（修复后）

```
$ /softwares/python/bin/python3 scripts/validate-wf-design.py
机制稿：引用 330；二值场景 91/91；三档场景 13/13；输入摘要 4/4（仅机械关系，不证明语义正确）
OK：设计 720 行 / charter 129 行；定义位点 51+7 个；索引表 143 行；消费点缺项 0；三率：定义命中 100% / 消费点命中 100% / 引用检查残差 2 行（输出不设阈值）；七项检查 + 覆盖率断言通过
```

（引用数由修复前 321 增至 330，来自 B2/C1/C3/C5 新增的带所有者章节引用。）

### 需人工复核点

1. **§2.2 批准规划行的连带修正**（mechanism:191）：任务指令未明列该行，但 B2 指定「写者为批准/开工入口」与原「只写 plan」字面冲突，按最小改动扩为「只写 plan 与 Plan 期人判答复」。若认为批准入口不应写 execution.human_decisions，需回退该句并收窄 §1.3 写者。
2. **pending 语义的承载边界**（mechanism:119/217）：「无 pending 项」的核对以「规划材料中已编号的问题」为问题全集来源（问题+推荐答案随规划材料留痕），未新设机读问题清单 schema。若实现阶段需要更强机判（如 PRD 块内问题登记），须另行登记字段。
3. **C2 码值取舍**：选用 WF_CAPABILITY_UNAVAILABLE 而非 WF_RECORD_INVALID，理由见上；与 §11.1 码表「所需系统/格式/资产能力未支持」语义对齐，未改码表本身。
4. **索引 row 48 的消费点删除**（index:62）：删除的是语义消费列的人工注记（第 5 列），词面候选列（第 3 列）未动；机检不校验第 5 列内容，该同步正确性需人确认。

### 独立检查阶段修正（2026-11-02）

- `wf-framework-mechanism.md:21` 与 `:628`：新增句中的 4 处 ASCII 直双引号改为中文弯引号（“”），对齐全文正文仅用弯引号的既有文体；不改变语义，机检复跑全绿（引用 330；二值 91/91；三档 13/13；输入摘要 4/4）。机制稿自身不哈希回写，四份输入摘要不受影响。

### 独立检查遗留（留人工裁决，未替人定夺）

1. **pending 的承载措辞**（mechanism:119/217）：「无 pending 项」以「已编号问题均有对应 Decision」解释（缺席即待决），但 :217「未答项保持 pending」字面读作记录状态，而 Decision schema（§1.1）无 pending 字段——两处措辞对 pending 究竟是状态还是缺席，存在轻度歧义。
2. **§11.2 证据行的覆盖方式**（mechanism:843）：§1.3 声称消费者含「本文 §11.2 的 task.plan-approved 证据核对」，但 §11.2 固定处理器证据行（:843）只列「plan.approval、可读快照与当前 PRD 提取值」，未显式列 human_decisions；仅 :828 的「Decision 及快照」可泛指覆盖。是否在 :843 补列，交人裁决。

## 第二轮修复记录（2026-11-02，外部复审 4 项发现，用户已裁决方案后执行）

修复对象仅 `docs/workflows/wf-framework-mechanism.md` 与本文件；design/charter/sources/index 四文件未改（sha256 与 §0.1 登记一致：f41173d9…/8b816ee4…/14739427…/47484498…）。行号为修复后工作树行号。用户明确要求避免补丁式叠加：涉及上轮已改的 §1.3/:120、§2.3/:218/:222 段落均整段重写为语义连贯整体。用户两项裁决：debug_repeat 机械触发统一为「check 记录 failed 累计」口径（修正 2）；plan-q 采用「PRD 正文固定格式编号 + 批准声明承载全集、不设 pending 记录态」方案（修正 4）。

### 修正 1（§7.1 示例补定义标记）

- `wf-framework-mechanism.md:499-501`（§7.1）：示例引导句重写为「下例是一个完整的定义文件，由 `<!-- wf-definition:v1 -->` 标记与其紧邻机读块构成，可直接复制到 `.wf/user-workflows/` 按本节规则解析校验」，并在 ```json 围栏前补标记行。示例 JSON 内容不变。
- 自查：以脚本按「唯一标记 + 紧邻围栏」规则解析该块，JSON 解析通过、顶层键齐全；全文该标记出现 3 处（§7.1 规则句 :458、示例引导句 :499、示例标记 :501），示例自带标记不破坏「每份定义文件唯一标记」的规则表述（规则句约束的是定义文件，机制稿正文不是定义文件）。

### 修正 2（debug_repeat 触发事实：机械+人判双层，用户裁决）

- `wf-framework-mechanism.md:566`（§8.1 `debug_repeat_threshold` 消费列）：改为「同一 verification_id 在本任务历次 check 记录中的 failed 最终结果累计达到阈值提示复盘；每次 Check 每声明只存最终结果、修复重跑形成新 check.id，故按 check 记录个数累计，事实全部从既有判定记录重建，不新增计数账本」。
- `wf-framework-mechanism.md:837`（§11.2 task.retrospective-done gate 列）：整格重写为三类机械触发（返工 = rework_of 反向集合本轮新增；审查失败 = reviews 历史 result=fail；重复调试 = 同一 verification_id 跨本任务历次 check 的 failed 累计达阈值）+ 人判补充（未达阈值时人可在 continue/finish 要求，对齐设计稿 §4.4「其余任务可选」，不新增独立声明字段）+ 「不可重建给待核对出口，不倒推为无触发」。
- `wf-framework-mechanism.md:852`（§11.2 P 表证据列）：ref 措辞改为「任务/轮次/检查记录引用」。
- `wf-framework-mechanism.md:52`（§0.2 追踪表）：新增一行「复盘触发事实（rework/review_fail/debug_repeat）｜本文 §8.1、§11.2｜归档前 retrospective-done 证据核对；触发事实不可重建时给待核对出口，不倒推为无触发」。
- 依据：用户裁决的机械计数口径；三类事实均从既有判定记录（rework_of 边、reviews 历史、check 记录）重建，符合修订闸门「触发输入须可从持久记录重建」的规则。注意：任务指令写「对齐设计稿 §4.3」，但「其余任务可选」实际位于设计稿 §4.4 复盘段（design:258），:837 已按实际章节引用 §4.4。

### 修正 3（project_id 重建不复用旧值）

- `wf-framework-mechanism.md:410`（§5.4）：整句重写为「项目标识重建由 repair 入口在同一动作内生成新 UUID4，并与预览登记的旧值比对，相同则重新生成直至不同，落实设计稿 §3『重建不复用旧值』；同时对旧标识的本机解释器确认记录执行明确失效并保留依据；只有模型代填确认的路径不允许」。注意：「重建不复用旧值」实际位于设计稿 §3 项目配置（唯一定义）段（design:137），未按任务指令示例写 §5.5/§1.1；§5.5 是重建动作的入口章节、§1.1 是生成算法的委托出处，均不如 §3 的字面承诺贴切。
- `wf-framework-mechanism.md:561`（§8.1 `project_id` 消费列）：补「repair 重建生成新值后与旧值比对、相同则重新生成」。

### 修正 4（plan-q 全集载体：固定格式+批准声明，用户裁决）

- `wf-framework-mechanism.md:120`（§1.3 execution 段）：整段重写——人判点 id 来源两类（human_points id；普通任务 PRD 正文以 `plan-q-<n>：` 起始行固定格式编号、同行或紧邻行附推荐答案，n 从 1 递增不重复不跳跃）；入口按固定模式提取问题全集，人一轮批量作答后逐项写入 Decision；**不设 pending 记录态，未答即无对应 Decision**；消费者 = 开工核对（全集每项均有对应 Decision）与 §11.2 task.plan-approved 证据核对；编号重复/跳跃等格式不可靠提取 → WF_SEMANTIC_DECISION；人批准规划的 Decision 即「问题集为空或已全部作答」的人判声明，机器不把「无编号」倒推为无疑问。
- `wf-framework-mechanism.md:218`（§2.3 规划批准段）：grilling 句对齐重写（每个待决问题编号+推荐答案、措辞使「是」即接受推荐项、人一轮内批量作答；删除「未答项保持 pending」字样，改为「未答的问题不写入 Decision」），并指明固定格式定义在本文 §1.3。
- `wf-framework-mechanism.md:222`（§2.3 开工序列项）：「无未决范围问题」项重写为「按本文 §1.3 固定格式提取的问题全集均有对应 Decision 且当前有效批准存在；提取不可靠或存在未答项 → WF_SEMANTIC_DECISION」。
- `wf-framework-mechanism.md:192`（§2.2 批准规划行）：前置列改为「人批准当前版本、复杂度/TDD；Plan 期人判问题全集按本文 §1.3 由人一轮内作答，只写 plan 与对应 execution.human_decisions」，与新写者定义对齐（保留上轮消除字面冲突的修正语义）。
- `wf-framework-mechanism.md:845`（§11.2 task.plan-approved P 表证据列）：显式补「与 execution.human_decisions 的覆盖核对（本文 §1.3 的问题全集均有对应 Decision）」，闭合 §1.3 声称的消费点，同时解决上轮遗留 2。
- `wf-framework-mechanism.md:51`（§0.2 登记行）：按新规则整行重写（固定格式提取+批准声明承载；开工核验、task.plan-approved 证据含 human_decisions 覆盖核对、WF_SEMANTIC_DECISION），不叠加旧措辞。
- 附带解决上轮遗留 1：pending 歧义随「不设 pending 记录态」的整段重写消除。

### 机检输出（第二轮修复后）

```
$ /softwares/python/bin/python3 scripts/validate-wf-design.py
机制稿：引用 338；二值场景 91/91；三档场景 13/13；输入摘要 4/4（仅机械关系，不证明语义正确）
OK：设计 720 行 / charter 129 行；定义位点 51+7 个；索引表 143 行；消费点缺项 0；三率：定义命中 100% / 消费点命中 100% / 引用检查残差 2 行（输出不设阈值）；七项检查 + 覆盖率断言通过
```

引用数由 330 增至 338（新增的带所有者章节引用），设计稿 720 行不变，四份输入摘要与 §0.1 一致。

### 自查（第二轮）

- §7.1 示例含标记+围栏，按 §7.1 规则脚本解析通过。
- §1.3/§2.2/§2.3/§11.2 四处 plan-q 规则一致：写者均为批准/开工入口（§2.2 允许写、§2.3 :218 落笔、§1.3 定义、§11.2 :845 消费）；消费者均为开工核对 + task.plan-approved 证据；出口均为 WF_SEMANTIC_DECISION；全集来源均为 PRD 正文固定格式提取，无「pending 项」「无 pending」残留（grep 确认；§1.1 execution.actions 的 result=pending 枚举、handoff/disposition/wip/action.state 等既有 pending 均为合法字段，不在清除范围）。
- 新增正文无 ASCII 直引号（仅 §2.3 既有的 `H("wf-plan-v1",…)` 公式字面量含直引号，属代码样式，未改）。
- `git diff --stat`：本轮工作树相对 HEAD 含 design/index 的第一轮改动与本轮 mechanism 改动；本轮实际触碰仅 mechanism.md 与本文件，四输入文件 sha256 与 §0.1 表一致。

### 需人工复核点（第二轮）

1. **设计稿章节引用两处按实际位置修正**：任务指令给出的「设计稿 §4.3『其余任务可选』」实为 §4.4（design:258 复盘段）、「重建不复用旧值」实为 §3（design:137 项目配置段），机制稿 :837 与 :410 分别引用 §4.4 与 §3。若用户本意是指其他章节，需人工指认。
2. **§2.2 批准规划行的连带措辞**（mechanism:192）：前置列并入「Plan 期人判问题全集按本文 §1.3 由人一轮内作答」，语义为批准动作可携带人判答复写入；若认为该行应只保留最小语义（只写 plan 与 execution.human_decisions），可再收窄。
3. **「编号缺失以批准声明为准」的边界**（mechanism:120）：PRD 完全无 plan-q 编号时机器不阻断，由人的批准 Decision 声明「问题集为空或已全部作答」兜底；该声明是格式校验之外的纯人判面，实现阶段的固定处理器无法机判其真伪，属已声明的语义边界而非缺口，但值得在实现验收时给一条正反断言（有编号未答 → 阻断；无编号已批准 → 放行）。
4. **§0.2 新增复盘触发行的登记完备性**：复盘触发事实同时涉及 §11.2 :837 的 required 步骤条件与 §8.1 :566 的阈值口径，追踪表只登记这两处定义/生产位置；返工与审查失败两类触发无独立配置键（分别来自 rework_of 边与 reviews 历史），登记粒度按判定域合并，是否符合 §0.2 的登记习惯请人确认。

## 第三轮修复记录（2026-11-02，外部复审 4 项，两项经用户裁决）

修复对象仅 `docs/workflows/wf-framework-mechanism.md` 与本文件；design/charter/sources/index 四文件未改（sha256 复核与 §0.1 登记一致：f41173d9…/8b816ee4…/14739427…/47484498…）。行号为修复后工作树行号。涉及前两轮已改段落的（§0.2 追踪行、§8.1 阈值消费列、§11.2 gate/evidence 列、§3.5 计算有效性段）均整格/整段重写为语义连贯整体，未叠加补丁。用户两项裁决：debug_repeat 采用「机械检测 + 归档门禁强制裁定」方案（修正 1）；check 历史采用「记录内 check_history 字段」方案（修正 2）。设计稿 §4.4 复盘语义未改，机制稿编码就此收敛，不宣称改动上位语义。

### 修正 1（debug_repeat 判据语义不等价 → 机械检测 + 强制裁定，用户裁决）

- `wf-framework-mechanism.md:567`（§8.1 `debug_repeat_threshold` 消费列）：重写为机械检测口径——同一 verification_id 在本任务 check 历史（check_history）的 failed 最终结果累计达阈值只产生 WF_SEMANTIC_DECISION 待决项（待决事实：该累计是否属同一问题重复调试），不直接触发复盘；返工、审查失败两类机械触发语义本就机械可判，维持直接触发。
- `wf-framework-mechanism.md:838`（§11.2 `task.retrospective-done` gate 列，整格重写）：两层判定完整编码——人确认「同一问题」→ 待决项转正为触发事实、复盘 required，入口核其引用的调试证据真实存在且次数达阈值后写入 triggers；裁定「不同问题」→ 裁定 Decision 留痕、清除待决项，该 verification_id 累计保留，后续再达阈值重新产生待决项；归档门禁要求机械检测待决项均已被裁定，未裁定阻断归档（出口 WF_SEMANTIC_DECISION）。Execute 期漏计兜底：check 历史之外的重复调试由人/主会话在 continue/finish 声明触发，入口核调试证据（check 历史、execution.actions failed 结果及 evidence_refs、handoff 材料）真实存在且次数达阈值后写入 triggers；verification_id 只作证据关联辅助。
- `wf-framework-mechanism.md:853`（§11.2 P 表证据列）：ref 措辞改为「任务/轮次/check 历史（check_history）条目引用」，补「debug_repeat 触发另核对应裁定留痕（同一问题的确认裁定或不同问题的裁定 Decision），机械检测待决项均已裁定」。
- `wf-framework-mechanism.md:52`（§0.2 追踪行）：整行重写，登记机械检测口径（§8.1）与触发集合/强制裁定/Execute 期兜底（§11.2）两处定义位置及「未裁定 → WF_SEMANTIC_DECISION 阻断归档」消费出口（该行随后并入修正 2 的 check_history 登记再整行重写一次）。

### 修正 2（check 历史保存协议 → 记录内 check_history，用户裁决）

- `wf-framework-mechanism.md:107-108`（§1.3 任务 schema）：`check` 行改注「当前检查记录」（当前锚点核对），新增 `check_history` 行——按 check.id 保存的历次检查记录数组，显式空与缺失不同；写者为 Check 入口（写入新结果前移入旧记录，含 failed/not_run/中断及带 invalidation 的失效 pass 的完整历史），消费者为复盘触发计数与检查历史消费。
- `wf-framework-mechanism.md:289`（§3.5）：原「计算有效性」段整段重写为「保存协议与计算有效性」——Check 入口在同一原子动作内、写入新结果前将旧 check 移入 check_history（按 check.id 定位、不删不改历史条目）；当前锚点核对用 check、复盘计数与触发重建从 check_history 读取；失效旧 pass 的 invalidation 语义并入同一表述，不再两套说法；明确 check_history 是任务记录自身字段、不新增独立生命周期账本、周期巡检/统计不单独消费它。
- `wf-framework-mechanism.md:567`、`:838`：「历次 check 记录」措辞统一为「check 历史（check_history）」（首轮写定于修正 1 的两格重写中）。
- `wf-framework-mechanism.md:52`（§0.2）：追踪行登记 check_history 的定义/生产位置（本文 §1.3 与本文 §3.5）与消费（重复调试计数从 check_history 重建）。

### 修正 3（归档持久化判据与共享文件后续合法变化冲突 → 可达提交查证）

- `wf-framework-mechanism.md:401`（§5.3）：整段重写——持久化完成改为可达提交查证：历史查找覆盖该归档意图登记的写入前 HEAD..当前 HEAD 中触及该归档动作登记精确路径组的提交，按拓扑逆序逐个核对完整树状态，某个可达提交同时包含登记终态、目录移动结果与精确路径组登记状态即证明已持久化；后续对同组路径的合法推进（游标/任务映射更新等）按当前任务/外部变更归属处理，不倒算为该归档未持久化；工作树/索引额外差异只作「该组当前是否有待处理变化」的独立事实报告，不参与已持久化判定；写入前 HEAD 不可达/查询失败/无完整依据走锚点核对。与本文 §4.5 的关系在段内写明：查证思路同源（存在包含完整登记终态的可达提交即证明该次操作已持久化），两边各自引用各自对象的登记结构，不复制成第二份通用算法。
- `wf-framework-mechanism.md:419`（§6.1）：依赖满足条件「归档持久化已完成」补「（按本文 §5.3 的可达提交查证派生）」。

### 修正 4（skip.replacement 下游解析顺序未定义）

- `wf-framework-mechanism.md:483`（§7.1 from:step 行，消费语义定义处）：重写为三段顺序——先核来源步骤实际结果；来源正常完成则核验产物本身；来源为合法略过且略过决定中已确认对该输出的替代映射（skip.downstream 的 replacement）时，改为核验替代来源声明的真实产物就绪并固定到当前任务批准验证材料；来源既未正常完成、也无已确认替代映射才阻断。
- `wf-framework-mechanism.md:541`（§7.3 可略执行段，消费端引用处）：段末补一句「下游引用解析按本文 §7.1 的 from:step 消费顺序执行（……三分支简述……），替代产物核验等同前序产物，不降低验证要求」——一处定义（§7.1）一处引用（§7.3），未修改固定定义格式、未引入条件跳转。

### 机检输出（第三轮修复后）

```
$ /softwares/python/bin/python3 scripts/validate-wf-design.py
机制稿：引用 345；二值场景 91/91；三档场景 13/13；输入摘要 4/4（仅机械关系，不证明语义正确）
OK：设计 720 行 / charter 129 行；定义位点 51+7 个；索引表 143 行；消费点缺项 0；三率：定义命中 100% / 消费点命中 100% / 引用检查残差 2 行（输出不设阈值）；七项检查 + 覆盖率断言通过
```

引用数由 338 增至 345（新增带所有者的本文 § 引用）；中途一次 FAIL（§0.2 行三个引用缺「本文」前缀）已修复后复跑全绿。四份输入文件 sha256 与 §0.1 表一致（§0.1 无需更新）。`git diff --stat`：mechanism.md 56 行变更（含第二轮既有未提交改动）与 design/index 的前两轮既有改动；本轮实际触碰仅 mechanism.md 与本文件。新增正文无 ASCII 直引号（grep 复核；diff 中含 `"` 的两行为第二轮既有的 `H("wf-plan-v1",…)` 公式字面量，属代码样式例外）。

### 自查（第三轮）

- §8.1/§11.2/§0.2 三处 debug_repeat 口径一致：均为「机械检测产生待决项（不触发）→ 强制裁定（同一问题转正 / 不同问题留痕清项、累计保留）→ 未裁定阻断归档（WF_SEMANTIC_DECISION）」；返工/审查失败直接触发三处一致。
- check/check_history 四处一致：§1.3（:107-108 定义字段与写者）、§3.5（:289 原子保存协议）、§8.1（:567 按 check_history 条目计数）、§11.2（:838/:853 从 check_history 重建、ref 引用其条目）；「历次 check 记录」旧措辞在阈值消费与 gate 格中已清除（:108 行内「历次检查记录」为 check_history 自身描述，非旧口径残留）。
- §5.3 与 §4.5 无重复定义：§5.3 引用「查证思路与本文 §4.5 同源」并各自给出对象特定的核对内容（§5.3 = 归档动作登记终态/目录移动/精确路径组；§4.5 = 操作回执/路径组终态），无第二份通用算法。
- §7.1/§7.3 一处定义一处引用：三段消费顺序唯一定义在 §7.1 from:step 行，§7.3 仅引用并简述。

### 需人工复核点（第三轮）

1. **「同一问题」裁定的留痕载体**（mechanism:838）：确认裁定经 triggers（ref 引用调试证据）承载、不同问题裁定 Decision 留痕，均复用既有 Decision/triggers 结构，未新增独立 schema 字段。若实现阶段需要更强的机判载体（如 retrospective 内嵌 ruling 字段），须另行登记。
2. **「不同问题」裁定后累计保留的再触发节奏**（mechanism:838）：该 verification_id 的 failed 累计不清零，后续再达阈值会重新产生待决项；同一命令因多个不同问题反复失败时可能出现「频繁待决—频繁裁定」。语义上「不重复追问已裁定事实」只豁免已裁定的那一次累计，是否符合预期请人确认。
3. **§5.3 查证界限的字段级措辞**（mechanism:401）：「该归档意图登记的写入前 HEAD」对应 action.head_before/write_mark.before_head 的语义，段内未精确到字段名；是否需要点名字段，交人裁决（§4.5 原文同样用 head_before 字段名，措辞风格略有差异）。
4. **§7.3 引用处的简述幅度**（mechanism:541）：任务要求「§7.3 只引用不复述」，实际写法在引用本文 §7.1 后括注了三分支简述以保证该段自含可读；若认为复述过度，可收窄为纯引用句。

## 第三轮独立检查修正（2026-11-02）

- `wf-framework-mechanism.md:838`（§11.2 task.retrospective-done gate 格）：Execute 期兜底句中「execution.actions 的 failed 结果及 evidence_refs」的 evidence_refs 并非 execution.actions 的 schema 字段（其字段为 id/result/output_refs/verification_refs/decision_refs，见 §1.3），改为「及其 output_refs/verification_refs」（该 schema 真实自带的引用字段，判定语义不变）。第三轮修复记录 :212 原句同步以此为准。机检复跑全绿（引用 345；二值 91/91；三档 13/13；输入摘要 4/4）。

## 遗留决策项闭合记录（2026-11-02，三项均经用户裁决后执行）

修复对象仅 `docs/workflows/wf-framework-mechanism.md` 与本文件；design/charter/sources/index 四文件未改（sha256 复核与 §0.1 登记一致：f41173d9…/8b816ee4…/14739427…/47484498…）。行号为修复后工作树行号。三处均只做句内最小扩展/重写，不动所在格/段的其余句子，不顺手改其他任何句子。

### 修正 1（「再达阈值」机械口径 → 整数倍，闭合第三轮遗留 2）

- `wf-framework-mechanism.md:838`（§11.2 task.retrospective-done gate 格，「不同问题」裁定分支）：原「该 verification_id 的累计保留，后续再达阈值重新产生待决项，不重复追问已裁定事实」整句重写为整数倍口径——「该 verification_id 的 failed 累计保留；累计每新跨过 debug_repeat_threshold 的整数倍（即累计数首次达到阈值，及其后每再增加 debug_repeat_threshold 次达到新的整数倍）时重新产生待决项，已裁定事实留痕不重复追问，仅新跨过整数倍的累计待裁定」。
- §8.1 :567 核查：该消费列只有「累计达到阈值时产生待决项」的首次触发口径，无再触发措辞，未改动（与 :838 的「首次达到阈值」一致，无张力）。机器可判定性：整数倍比较（累计数 mod debug_repeat_threshold == 0 且本裁定周期内新增的 failed 计数非零），与「不重复追问已裁定事实」无张力（已裁定部分只留痕不再入待决）。

### 修正 2（§5.3 点名 head_before，闭合第三轮遗留 3）

- `wf-framework-mechanism.md:401`（§5.3 可达提交查证段）：区间下界由「该归档意图登记的写入前 HEAD」改为点名 schema 真实字段——「该归档动作的 `action.head_before`..当前 HEAD」，并括注「区间下界 `action.head_before` 为本文 §5.1 定义的动作字段：意图写入前的可核对 HEAD；归档动作以 task 为主记录」。
- 字段名核对：§5.1 action 字段表 :365 行为 `| `base_revision`、`head_before` | 意图写入前主记录 revision 与可核对 HEAD |`，引用与定义逐字一致；全限定写法 `action.head_before` 与全文 `action.state`、`action.id` 的限定风格一致，与 §4.5 的裸 `head_before` 用法写法风格对齐（§4.5 为主记录自身字段故裸写，§5.3 归档动作在 task 主记录上、以限定名消歧）。

### 修正 3（plan-q 批准声明「问题集」指代闭合）

- `wf-framework-mechanism.md:121`（§1.3 execution 段，原 :120 因第三轮 check_history 增行移至 :121）：批准声明句内最小扩展——「该声明覆盖 PRD 实际存在的问题（含固定格式提取的遗漏面），机器不把“提取结果为空”倒推为无疑问，语义保证在人批准声明，尾部漏提的残余风险由该声明承载」。语义与原句等价连续（原「编号缺失时以该批准声明为准」的兜底语义并入新表述），非补丁式叠加。
- 一致性核查：与 §2.3 :223 开工序列项「按本文 §1.3 固定格式提取的问题全集均有对应 Decision」（机判面：提取全集）分工明确、无冲突——提取全集由机器核对，提取遗漏面由人批准声明承载；与 §11.2 :846 task.plan-approved P 表证据列的覆盖核对（提取全集每项有 Decision）同样无冲突。

### 机检输出（本轮修复后）

```
$ /softwares/python/bin/python3 scripts/validate-wf-design.py
机制稿：引用 346；二值场景 91/91；三档 13/13；输入摘要 4/4（仅机械关系，不证明语义正确）
OK：设计 720 行 / charter 129 行；定义位点 51+7 个；索引表 143 行；消费点缺项 0；三率：定义命中 100% / 消费点命中 100% / 引用检查残差 2 行（输出不设阈值）；七项检查 + 覆盖率断言通过
```

引用数由 345 增至 346（:401 新增一处「本文 §5.1」带所有者引用）。四份输入文件 sha256 与 §0.1 表一致（§0.1 无需更新）。本轮 diff 核对（相对第三轮后快照）：mechanism.md 仅 :121、:401、:838 三行变更；`git diff --stat` 中 design/index 的变更为第一轮既有未提交改动，本轮实际触碰仅 mechanism.md 与本文件。新增正文无 ASCII 直引号（全文直引号计数 160→160 不变，均为代码字面量）。本轮后不提交，留人工审查。

## 第四轮修复记录（2026-11-02，外部复审 2 项，两项方案均经主会话判定后执行）

修复对象仅 `docs/workflows/wf-framework-mechanism.md` 与本文件；design/charter/sources/index 四文件未改（sha256 复核与 §0.1 登记一致：f41173d9…/8b816ee4…/14739427…/47484498…）。行号为修复后工作树行号。涉及第三轮已改的 §7.1 from 表、验证来源段与 §11.2 gate 格的，均整体重写为连贯语义，未叠加补丁；文体保持密集中文规范文风、弯引号（新增正文无 ASCII 直引号，diff 中含 `"` 的两行为第二轮既有的 `H("wf-plan-v1",…)` 等公式字面量，属代码样式例外）。两项方案判定（含主会话裁决）：修正 1 统一替代语义采用「一处定义、三类消费方同用」——承载位置定在 §7.1 from 表后紧邻段（一处定义），from 表两行/验证来源段/§7.3 三处只引用；修正 2 裁定事实持久化采用「execution.human_decisions 的 debug-ruling 条目」为唯一承载（主会话时序论证：triggers 若作为持久清单，写入发生在「同一问题」裁定之后，而裁定前机器只有待决项、无触发事实可写，「写入 triggers」指代悬空；改为 gate 时派生视图后，持久面只剩裁定条目与 check_history，全部在裁定/检查时点即已存在，重建无时序缺口），不新增独立账本/入口/状态机，retrospective schema 不扩字段。

### 修正 1（替代语义统一覆盖三类消费方）

- `wf-framework-mechanism.md:483`（§7.1 from:step 行）：行内三段解析顺序抽出，瘦身引用统一规则，来源身份注明「前序步骤产物」。
- `wf-framework-mechanism.md:484`（§7.1 from:action 行）：补「来源身份为同任务前序动作产物；消费按本节统一消费规则解析」，消除无替代分支的行内旧语义。
- `wf-framework-mechanism.md:486`（§7.1 from 表后新增「统一消费规则」段）：唯一定义——消费方三类（步骤输入 from: step、动作输入 from: action、验证来源 source: prior_step 的 stored_in: step_output）同用一条替代语义；三段顺序（核来源实际结果 → 合法略过且已确认替代映射时核替代来源真实产物就绪并固定到当前任务批准验证材料 → 皆无才阻断）；「来源实际结果」按消费方身份取值（步骤实际完成结果 / task.execution.actions 的结果 / 前序步骤/任务实际完成事实，由 task_map 解析）。
- `wf-framework-mechanism.md:498`（§7.1 验证来源段）：prior_step 消费句改为引用统一规则，替代文件仍须带 `<!-- wf-verifications:v1 -->` 块、来源合法、调用纳入当前批准并实际通过必要验证，验证强度不降。
- `wf-framework-mechanism.md:527`（§7.2 静态校验）：「必需/可略及替代」处补句——downstream.consumer 须指向定义中实际存在的下游消费方（步骤输入/动作输入/验证声明 id），replacement 须为合法来源引用且静态可核；三类消费方均适用统一替代语义，不设某类默认不允许的暗规则，未来要禁止某类须在静态校验显式拒绝。
- `wf-framework-mechanism.md:543`（§7.3 :541 引用处）：括注与新统一规则对齐（「from:step 消费顺序」措辞换为「统一消费规则」，三分支简述同步、补「三类消费方同用该规则」），定义地位不变（仍一处定义、此处引用）。

### 修正 2（复盘裁定事实的持久化协议）

- `wf-framework-mechanism.md:121`（§1.3 execution 段）：人判点 id 来源扩为三类，新增 `debug-ruling-<verification_id>-<multiple>`——multiple 为该 verification_id 的 failed 累计所跨过的 debug_repeat_threshold 整数倍序号（从 1 起；Execute 期漏计兜底声明条目复用同一 id 形式）；Decision 结构复用本文 §1.1（subject 记待决事实、choice 记「同一问题」/「不同问题」、reason 记依据）；写者为处理待决项的入口（Check/continue/finish 裁定时）；消费判据：从 check_history 重建累计 → 已跨倍数 = 累计数除以阈值的整数部分 → 每个已跨倍数须有对应 id 的裁定 Decision（「同一问题」→ 该倍数构成触发事实按本文 §11.2 转正、复盘 required；「不同问题」→ 留痕、该倍数不再追问；无裁定的新倍数即未裁定待决项）；跨会话接续按同一判据定位已裁定范围，旧裁定只对应其倍数、不外溢到新倍数；补隔离半句——debug-ruling 条目不参与开工核对的问题全集判定（id 前缀不同）。
- `wf-framework-mechanism.md:840`（§11.2 task.retrospective-done gate 格，整格重写）：裁定留痕位置明确为 execution.human_decisions 的 debug-ruling 条目；triggers 定性为 gate 时的派生视图、不落第二持久清单——从 rework_of 反向集合本轮新增、reviews 历史 result=fail 与 debug-ruling「同一问题」裁定及其引用的 check_history 条目重建；「同一问题」转正为触发事实、复盘 required，「不同问题」留痕该倍数不再追问、累计保留；整数倍再触发与归档门禁（无裁定的新倍数即未裁定待决项，出口 WF_SEMANTIC_DECISION）口径不变；Execute 期兜底按同一 debug-ruling 条目形式留痕；retrospective.evidence（本文 §1.3 既有字段）保存复盘所覆盖触发事实的引用（含对应裁定条目 id），「历史复盘不能覆盖新增触发事实」按整数倍与触发事实重建核对，retrospective schema 不变。
- `wf-framework-mechanism.md:855`（§11.2 P 表证据列）：对齐——triggers 为按 gate 格从既有判定记录重建的派生视图；debug_repeat 触发核 debug-ruling 裁定条目及其引用的 check_history 条目。
- `wf-framework-mechanism.md:569`（§8.1 debug_repeat_threshold 消费列）：对齐——裁定留痕按本文 §11.2 的 debug-ruling 条目；补「再触发节奏按本文 §11.2 整数倍口径」，闭合上轮最终检查建议项 1（该口径已经用户裁决，此处只是传播）。
- `wf-framework-mechanism.md:51-52`（§0.2 登记同步）：plan-q 登记行消费列补「仅按 plan-q id 判定、不含 debug-ruling 裁定条目」；复盘触发行整行重写为 debug-ruling 口径（定义登记本文 §1.3/§8.1/§11.2/§3.5 四处，消费登记按 §11.2 派生重建核对）。

### 机检输出（第四轮修复后）

```
$ /softwares/python/bin/python3 scripts/validate-wf-design.py
机制稿：引用 355；二值场景 91/91；三档场景 13/13；输入摘要 4/4（仅机械关系，不证明语义正确）
OK：设计 720 行 / charter 129 行；定义位点 51+7 个；索引表 143 行；消费点缺项 0；三率：定义命中 100% / 消费点命中 100% / 引用检查残差 2 行（输出不设阈值）；七项检查 + 覆盖率断言通过
```

引用数由 346 增至 355（新增的带所有者「本文 §」引用，含 :527/:543 的「本文 §7.1」、:121 的「本文 §11.2」、:840/:855 的「本文 §1.3/§8.1/§11.2」与 §0.2 登记行）。四份输入文件 sha256 与 §0.1 表逐字一致（§0.1 无需更新）。`git diff --stat`：design 6 行、index 2 行为既有未提交改动（第一轮），mechanism.md 64 行变更（含第二、三轮既有未提交改动）；本轮实际触碰仅 mechanism.md 与本文件。

### 自查与场景走查（第四轮）

- 替代语义一处定义三处引用：三段解析顺序唯一定义在 §7.1 :486「统一消费规则」段（含三类消费方枚举与「来源实际结果」身份取值）；:483/:484 表行、:498 验证来源段、:543 §7.3 均只引用该规则并各自说明来源身份/强度要求，grep 确认无第二处行内三段顺序定义（旧「from:step 消费顺序」措辞已清除）。
- debug-ruling 四处口径一致：§1.3 :121（id 形式 `debug-ruling-<verification_id>-<multiple>`、倍数判据=累计除以阈值整数部分、写者=Check/continue/finish 裁定入口、出口=未裁定阻断归档）、§8.1 :569（消费列引用 §11.2 条目与整数倍口径）、§11.2 :840/:855（gate 格定义条目承载与派生视图重建、P 表证据列核对条目及 check_history 引用）、§0.2 :51-52（登记与隔离半句）；「写入 triggers」悬空指代已消除（grep 无残留），triggers 仅作为 P 表投影形状 `{triggers: [{kind, ref}]}` 与派生视图出现。
- 「同一问题转正」（:840 转正为触发事实、复盘 required）与「不同问题留痕」（:121 该倍数不再追问）两分支同 triggers 派生重建无矛盾：重建输入恰为「同一问题」裁定 + rework_of + reviews fail，「不同问题」条目不进入触发集合、只作已裁定范围定位；retrospective schema 未扩（仍 {required, evidence, conclusion}，evidence 为既有字段）。
- :121 隔离半句与开工核对措辞无冲突：开工核对（§2.3 :223）以「固定格式提取的问题全集」为输入，其提取模式为 `plan-q-<n>：` 起始行，debug-ruling 前缀天然不命中；隔离半句在 §1.3 与 §0.2 :51 双处声明，防止实现者按「human_decisions 内全部条目」口径误把裁定条目计入问题全集。
- 场景走查①（动作 A 合法略过 + 动作 B from:action 引用 A 产物 + 已确认替代）：B 的输入消费走 :486 统一规则——A 在 task.execution.actions 的 result=skipped 且 skip.downstream 已确认对 A 该输出的 replacement → 核替代来源真实产物就绪并固定到 B 的批准验证材料，不阻断（旧语义下 :484 无替代分支会阻断，已消除）；静态校验 :527 先行核 consumer/replacement 合法性，定义期即报错，不留给消费期。
- 场景走查②（前序可略步骤提供验证声明 + 人确认替代文件）：验证来源 prior_step 的 stored_in: step_output 消费走 :498——前序合法略过且替代映射已确认 → 核替代文件（须带 `<!-- wf-verifications:v1 -->` 块、来源合法）、调用纳入当前任务批准并实际通过必要验证；强度不降（块格式、来源合法性、必要验证执行三层要求均在）。
- 场景走查③（累计 3 次失败 → 裁定不同问题 → 收工 → 新会话累计到 6）：阈值 3 下首次累计 3 = 倍数 1，人裁定「不同问题」→ debug-ruling 条目留痕；归档时门禁核「机械检测已产生的各整数倍均有对应裁定条目」→ 倍数 1 有裁定 → 无待决项、不重复询问（跨会话按 :121 同一判据定位：重建累计=3、已跨倍数=1、该倍数有对应 id 裁定）；其后累计到 6 → 已跨倍数=2、倍数 2 无对应裁定条目 → 新产生待决项（WF_SEMANTIC_DECISION），归档阻断直至裁定；旧裁定（倍数 1）不外溢到倍数 2。

### 需人工复核点（第四轮）

1. **统一消费规则的段位选择**（mechanism:486）：定义段放在 from 表后紧邻处以「本节统一消费规则」指称（未编号），三处引用均以此措辞定位；若认为应作为编号小节或前置（表前）以便更强的锚定引用，需调整段位与引用措辞。
2. **debug-ruling 的 multiple 取值证据**（mechanism:121）：Execute 期漏计兜底的声明条目复用同一 id 形式、multiple 取「入口所核证据次数跨过的整数倍序号」——该分支的证据次数来自 check_history 之外的动作/handoff 材料，其与 check_history 累计口径的合并关系（是否并入同一累计网格）实现时须给出确定算法；本稿只锁 id 形式与判据方向，网格合并算法留实现方案，属可接受的委托深度但值得验收断言。
3. **阈值中途变更的整数倍网格**：按任务指令保持开放（上轮最终检查建议项 2），本轮未在正文引入任何一侧语义；§1.3 与 §11.2 的「累计/倍数」措辞均以当前 debug_repeat_threshold 值隐含计算，变更重建规则留人工审查。
4. **§0.2 复盘触发行的登记粒度**（mechanism:52）：debug-ruling 条目定义登记在「本文 §1.3」、消费判据同时被 §8.1/§11.2 引用，登记按判定域合并为单行；是否需要为 debug-ruling 单独拆行登记，交人确认。

## 第四轮开放项闭合记录（2026-11-02，四项均按已定推荐执行）

修复对象仅 `docs/workflows/wf-framework-mechanism.md` 与本文件；design/charter/sources/index 四文件未改（sha256 复核与 §0.1 登记逐字一致：f41173d9…/8b816ee4…/14739427…/47484498…）。行号为修复后工作树行号。三处正文改动均为句内最小替换或单行追加，不动所在格/段的其余句子，不顺手改其他任何句子；新增正文无 ASCII 直引号。

### 项 1（:486 步骤输入分支点名载体字段）

- `wf-framework-mechanism.md:486`（§7.1 统一消费规则段）：「来源实际结果」三类取值中，步骤输入分支由「来源步骤的实际完成结果」收窄为「来源步骤在实例 step_results（本文 §1.5）的结果」，与另两类点名 `task.execution.actions`/`task_map` 对称。
- 自查：step_results 字段名与本文 §1.5 定义逐字一致（:158「按步骤 id 保存决策、产物引用、略过/满足/未执行结果」、:165「kind 只取 satisfied/skipped/not_executed」）；引用章节号经 grep 核实为 §1.5（实例与终止数据），无错引；该处为全文正文首个指向 §1.5 的带所有者消费引用（既有两处本文 §1.5 引用分别在 §12.1 承接表 :920 与 §12.2 映射表 :960；第四轮独立检查修正原记录将两处均归入 §12.2 的偏差），机检引用数 +1 与之对应。

### 项 2（:527 consumer id 归属收窄）

- `wf-framework-mechanism.md:527`（§7.2 静态校验句）：downstream.consumer 的 id 归属由「步骤输入、动作输入或验证声明的 id」收窄为「消费方所属步骤/动作的 id 或验证声明的 id」——消费方是步骤输入/动作输入/验证声明三类，其 id 分别按所属步骤/动作自身 id 或验证声明 id 指代，与 §7.1 步骤/动作以自身 id 指代的结构一致。
- 自查：与 :472 skip.downstream 结构（`{consumer, output, mode, replacement}`）无冲突——consumer 单字段语义不变，仅收窄其取值归属的表述；与 :486 三类消费方枚举口径一致。

### 项 3（§12.3 追加 debug 双源合并验收断言）

- `wf-framework-mechanism.md:1016`（§12.3 夹具/窗口表末行追加）：新增一行「debug 双源合并」——初始事实与触发为同一 verification_id 的 failed 事实分处 check_history 与 Execute 期声明证据两处（两源各达半阈值、两源合计跨过阈值两种情形）；预期输出与恢复为倍数判定与 debug-ruling id 归属按实现方案的合并算法一致执行，两源各达半阈值时不得判为已跨倍数，合计跨过阈值时对应倍数须产生待决项且 debug-ruling id 的 multiple 与合并后累计一致，跨源不重复计数。
- 自查：行文与该表既有行同构（夹具/窗口｜初始事实与触发｜预期输出与恢复三段式）；不修改 §1.3/§8.1/§11.2 的判定语义本身——合并算法仍归实现方案，本行只固定验收口径；「合计跨过阈值时对应倍数须产生待决项」「multiple 与合并后累计一致」与 §11.2 :840 整数倍口径（无裁定的新倍数即未裁定待决项）及 §1.3 :121 的 multiple 取值判据同向，无矛盾。

### 项 4（阈值中途变更：保持开放，零文本改动）

- 经用户确认按推荐保持开放：不在机制稿正文引入任何一侧语义（不写「按当前 debug_repeat_threshold 值计算」也不写「按各时点阈值分段计算」），留实现方案/人工审查阶段裁决；本稿 §1.3 与 §11.2 的「累计/倍数」措辞维持现状，本项正文零改动。对应第四轮遗留 3 的处置为「维持开放并留痕」，不新增任何待决项编码。

### 机检输出（本轮闭合后）

```
$ /softwares/python/bin/python3 scripts/validate-wf-design.py
机制稿：引用 356；二值场景 91/91；三档场景 13/13；输入摘要 4/4（仅机械关系，不证明语义正确）
OK：设计 720 行 / charter 129 行；定义位点 51+7 个；索引表 143 行；消费点缺项 0；三率：定义命中 100% / 消费点命中 100% / 引用检查残差 2 行（输出不设阈值）；七项检查 + 覆盖率断言通过
```

引用数由 355 增至 356（:486 新增一处「本文 §1.5」带所有者引用；项 2/项 3 未新增引用）。四份输入文件 sha256 与 §0.1 表逐字一致（§0.1 无需更新）。本轮 diff 核验（反向应用三处编辑构造基线副本比对）：mechanism.md 本轮实际变更仅 :486（句内替换）、:527（句内替换）、:1016（§12.3 表末追加一行）三处；`git diff --stat` 中 design/index 的变更为第一轮既有未提交改动、mechanism.md 的其余变更为第二至四轮既有未提交改动，本轮实际触碰仅 mechanism.md 与本文件。新增正文无 ASCII 直引号（全文直引号出现次数相对 HEAD 的 +2 为第二轮既有公式字面量，非本轮引入）。本轮后不提交，留人工审查。

## 第五轮修复记录（外部复审 2 项：双源证据模型、action_id 来源定位）

修复对象仅 `docs/workflows/wf-framework-mechanism.md` 与本文件；四份上位文件未改（sha256 复核与 §0.1 逐字一致）。两项发现均经主会话核实属实：判断 1（生产端允许 Execute 期证据留痕、消费端重建只认 check_history；:1016 验收行「各达半阈值不判已跨」与「合计跨阈值须产生待决项」在两源各半阈值且互不重复时自相矛盾）；判断 2（established_by.action_id 非空时统一规则只按任务级完成事实取来源结果，S 归档+S 内动作 A 略过+下游引用 S.A 场景进不了替代分支）。

### 修正 1：统一双源证据模型（:121/:840/:855/:569/:52/:289/:1016）

- `:121`（§1.3 debug-ruling 段）：消费判据重写为双源合并口径——合并累计 = check_history 中该 id 的 failed 最终结果条目数 + Execute 期声明条目经入口核定的次数；判重规则（同一失败事件只在一个源计数，已入 check_history 的 failed 不再计入声明次数，入口逐项核对并剔除）；Execute 期声明条目核定次数与证据引用随条目留痕、证据不限定 check_history 条目类型（actions failed 及 output_refs/verification_refs、handoff 材料均可支撑）；multiple 取双源合并累计跨过的整数倍序号；跨会话重建合并累计不外溢不重复询问。
- `:840`（§11.2 gate 格）：触发集合重建输入扩展为「check_history failed 条目 + debug-ruling 裁定条目及其 subject/证据引用的调试证据（不限定 check_history 类型）」——Execute 期裁定凭原证据可重建；机械检测句改双源合并口径；两层判定、整数倍节奏、retrospective.evidence 承载结构不变。
- `:855`（P 表）：ref 类型扩为「任务/轮次/check 历史条目或裁定条目证据引用（execution.actions 的 failed 结果及其 output_refs/verification_refs、handoff 材料）」。
- `:569`（§8.1 消费列）与 `:52`（§0.2 登记行）对齐合并口径（一处定义一处引用）。
- `:289`（§3.5 保存协议段）补「按本文 §1.3 的双源合并口径并入 Execute 期声明条目核定次数」。
- `:1016`（§12.3 验收行）：两个情形改为互斥（阈值 4、两源各 2 次互不重复、合并累计 4=阈值→须判已跨倍数并产生待决项；两源各 1 次、合并累计 2<阈值→不得判已跨倍数），另设同一失败事件已入 check_history 又被声明计入的判重情形（入口剔除、按真实事件数计）；「按实现方案的合并算法」委托改为「按本文 §1.3 的合并与判重规则」。

### 修正 2：action_id 非空时来源身份定位到具名动作（:486）

- `:486`（§7.1 统一消费规则段）验证来源分支重写：established_by.action_id 非空时定位到该具名动作——同时核前序任务的合法完成事实（task_map 解析）与该动作在前序任务 task.execution.actions 中该动作 id 的结果、其略过决定及已确认替代映射（略过决定的人判答复保存于前序任务 task.execution、动作结果行记 skipped、替代映射为该动作 skip.downstream 的 replacement），合法略过与替代分支按统一规则执行；action_id 为空时使用步骤级结果（前序任务实际完成事实，task_map 解析实际产物）。
- 引用的记录载体全部为既有真实结构（task_map、task.execution.actions、skip.downstream），未虚构字段。

### 机检输出

```
机制稿：引用 363；二值场景 91/91；三档场景 13/13；输入摘要 4/4（仅机械关系，不证明语义正确）
OK：设计 720 行 / charter 129 行；定义位点 51+7 个；索引表 143 行；消费点缺项 0；三率：定义命中 100% / 消费点命中 100% / 引用检查残差 2 行（输出不设阈值）；七项检查 + 覆盖率断言通过
```

引用数 356→363。四份输入文件 sha256 与 §0.1 表逐字一致，§0.1 无需更新。`git diff --cached` 为空（未暂存未提交）。

### 场景走查（主会话独立执行）

1. **Execute 期三次失败+首次 Check 通过（跨会话）**：声明条目核定 3、证据引用 actions failed/handoff；重建合并累计 = 0（check_history）+ 3（声明） = 3，阈值 3 → 倍数 1；有「同一问题」裁定 → 触发事实凭其证据引用重建（不要求 check_history 类型）→ 复盘 required；有「不同问题」裁定 → 留痕不追问。旧文本：重建只认 check_history（累计 0），触发漏失或裁定无法核验——已消除。
2. **判重**：Check failed 2 条 + 声明把其中 1 条再计入：入口按 §1.3 判重规则剔除，合并累计按真实事件数（2+声明去重后次数）计。
3. **action_id 场景**：S 正常归档、S 内动作 A 合法略过+已确认替代 Y、下游验证 established_by=S.A：核 S 完成（task_map）+ A 结果（execution.actions 记 skipped）+ A 的替代映射 → 核 Y 真实产物就绪并固定，强度不降。旧文本按任务级完成事实会核原产物 X——已消除。
4. **:1016 互斥**：两情形（累计 4=阈值 / 累计 2<阈值）事实互斥，断言不再自相矛盾；判重情形独立成句。

### 需人工复核点（第五轮）

1. 声明条目「核定次数」由入口核证据支撑——入口对人声明次数与证据的逐项核对属纪律+事后核对边界（§1.5 已声明），不是防伪；与既有不可防边界一致。
2. `:486` 动作级略过决定的承载表述（「略过决定的人判答复保存于前序任务 task.execution、动作结果行记 skipped」）复用了第四轮已有人判点/execution.actions 结构，未新增字段；静态校验消费方解析对跨任务动作 id 消歧仍依赖既有 id 唯一核验（第四轮建议项未变）。
3. 阈值中途变更的整数倍网格重建口径仍保持开放（第四轮项 4 确认），本轮未引入任何一侧语义。

## 第六轮修复记录（2026-11-02，外部复审 6 项 B 级 + 7 项 C 级，4 项经用户裁决）

修复对象仅 `docs/workflows/wf-framework-mechanism.md` 与本文件；design/charter/sources/index 四份上位文件未改（sha256 复核与 §0.1 登记逐字一致：f41173d9…/8b816ee4…/14739427…/47484498…）。行号为修复后工作树行号。用户四项裁决：B2（回执按内容/规则分两类）、C4（complexity_reasons 扩降级条目）、C6（确认子命令例外）、C7（采纳建议按影响分流）；其余 9 项按复审处方直接修。涉及前几轮已改段落的（§1.3 execution 段、§3.5 保存/命令段、§11.2 P 表与 gate 格、§5.3 查证段）均整句/整段重写为连贯语义，未叠加补丁；文体保持密集中文规范文风、弯引号（新增正文的 ASCII 直引号仅为哈希域名代码字面量，见机检自查）。

### 13 项落点汇总

| 项 | 落点（file:line） | 处置摘要 |
|---|---|---|
| B1 check_anchor/paths_digest 规范形状 | mechanism:260（§3.2 唯一编码定义）、:280（§3.5 anchor 改引用）、:864（§11.2 P 表改引用）、:678（§9.1 审查 check-anchor 对齐）、:53（§0.2 登记行） | :260 给出 `paths_digest=H("wf-check-paths-v1", C(paths))` 与 `check_anchor=H("wf-check-anchor-v1", C({九键}))`，逐键说明来源；:280 anchor 定为 `{check_anchor, rule_version}` 结构（rule_version 即原「所用框架规则兼容标识」，保住 §10.2 :751 的 Check.anchor.rule_version 取值语义）；:864/:678 直接引用定义；§0.2 登记域名与键集合 |
| B2 rule_version 匹配粒度（用户裁决：内容/规则两类） | mechanism:864（分类与锚点公式）、:881（回执选择规则按类）、:883（查询按类）、:889（completed_ref 与重跑触发按类）、:751（§10.2 对齐一句）、:714（§9.3 对齐说明）、:53（§0.2 登记行） | 内容类（plan-approved/knowledge-disposed/retrospective-done）锚点公式去 rule_version、匹配按 id/occurrence、rule_version 字段记 null，不因规则字节变化失配；规则类六 id 维持 rule_version 匹配；§9.3 补对齐句（引设计稿 §4.2 检查有效性「规则变化影响门禁/检查项时重跑对应步骤」）；effective_rule_version 定义未动 |
| B3 action 终态与未授权提交 | mechanism:371（state 行）、:378（新增「action 终态语义」段）、:391（§5.2 重入表第 3 行） | 明文 done=目标后置成立、与 Git 提交无关；persist_pending 仅限 task.archive/run.terminate；维护待提交走 maintenance_results 的 applied_pending_commit；补「未提交不构成后续冲突动作前置、不使已完成回到未完成；门禁核记录内容而非提交状态（对齐设计稿 §4.2）」；:391 删「授权提交事实可核」这一全类前置 |
| B4 固定处理器输出映射表 | mechanism:826-828（新码 3 枚入码表）、:832-839（映射表引导句与 4 行，行体 :836-839） | 新增 WF_VERIFICATION_UNREADY（blocked，来源/输入/命令不就绪）、WF_DEFINITION_INVALID（blocked，定义静态校验非法——不复用 WF_RECORD_INVALID，理由写入表内：后者语义是持久记录不可解释，定义文件属输入文档）、WF_TEMPLATE_INCOMPLETE（blocked，模板必填未填）；run.advance/实例步骤 pending 待决映射既有 WF_SEMANTIC_DECISION；三枚均给「出口与禁止的错误修复」列 |
| B5 plan-q 提取排除面 + 保留前缀 | mechanism:122（§1.3 提取排除规则）、:479（§7.1 human_points 保留前缀）、:534（§7.2 静态校验同步） | 代码围栏与引用块内 plan-q 行、对格式本身的讨论/示例不计入提取（与模板标记纪律同类，引「讨论这些标记的普通正文不是模板使用位点」）；human_points id 禁止以 `plan-q-`/`debug-ruling-` 起始，静态校验拒绝，使 §1.3 前缀隔离可校验 |
| B6 owner/owner_ref schema | mechanism:89（§1.2 owner 结构与两类取值示例）、:366（§5.1 id 公式 owner_ref 语义）、:914（§11.3 control P 同义引用） | owner=`{kind: session/maintenance, id, scope_ref}`，kind/id 与 writer.holder 同源，scope_ref 为授权范围引用（会话=绑定对象 id/准备范围，维护=维护操作标识）；owner_ref=该结构的规范 JSON |
| C1 单 Check 内重试边界 | mechanism:284（§3.5）、:1037（§12.3 夹具表新行） | 明文单 Check 内重试不产生多条 check_history failed 条目、不进机械检测口径、由 Execute 期声明兜底；夹具断言按此固定 |
| C2 启动校验固定顺序 | mechanism:400（§5.2 末尾新增「启动校验固定顺序」段）、:398/:410/:434（三处零散引用改指向） | 十项固定顺序逐项给既有原因码（复用为主），与设计稿 §5.4 启动校验清单逐项对应；⑨ 框架资产可用性按 installed 入口核 `.wf/bin` 布局与必需资产 |
| C3 判重的语义/结构分工 | mechanism:122（§1.3 判重分工）、:860（§11.2 gate 格 Execute 兜底句） | 脚本只核证据引用存在与可比对字段（verification_id、check.id、命令行、输出摘要）机械比对；「同一失败事件」结论并入裁定 Decision.reason 由人/主会话给出，入口据人判结论执行剔除（对齐设计稿 §1.5 强制力模型） |
| C4 降级理由落点（用户裁决：complexity_reasons 扩降级条目） | mechanism:118（§1.3 降级条目）、:707（§9.3 第 3 项） | 降级追加 `{downgrade: true, reason, evidence}`，与重新分级同批人批（引设计稿 §4.3「降级由人留理由，且只在任务本身确实变轻时成立」）；门禁第 3 项读该条目后按轻量审查要求执行 |
| C5 可达提交查证一处定义 | mechanism:338（§4.5 开头具名算法定义）、:342（§4.5 应用句）、:408（§5.3 改引用+登记结构差异）、:426（§6.1 引用对齐） | 算法（区间+拓扑逆序+完整树状态+不倒算+锚点核对出口）唯一编码在 §4.5 开头；:342 只述维护登记结构（操作回执+路径组终态），:408 只述归档登记结构（终态+目录移动+路径组）；删除「不复制成第二份通用算法」辩解句 |
| C6 确认动作执行载体（用户裁决：确认子命令例外） | mechanism:592（§8.2） | 确认动作=人显式调用的确认子命令，引导层例外（与独立 repair/uninstall 同构）：仅写用户层 `~/.wf/` 确认集合、只读项目配置、不写项目数据、不进项目锁；由引导解释器拉起不算越权；WF_EXECUTOR_UNCONFIRMED 出口提示执行该子命令后重入 |
| C7 审查 pass 后采纳建议（用户裁决：按影响分流） | mechanism:693（§9.2 dispositions 段后） | 不在 check 对象内的采纳按机械修订口径处置（dispositions 记依据+新指纹核对，报告继续有效、不消耗轮次）；命中对象使锚点变化，重跑 Check 并按既有轮次规则发新轮次；引设计稿 §4.2「无关路径改变不自动失效」同构 |
| C8 gitignore 托管段标识串 | mechanism:733（§10.1 落点表新行）、:743/:749（§10.2 gitignore_managed 字段并入清单 schema 与 rules_digest 输入）、:334（§4.4）、:773（§10.4）、:781（§10.5） | 固定标记串首行 `# wf-managed-v1`/尾行 `# wf-managed-end`，段内含 `/.wf-lock` 保留行；标记串与首版段内容随发行版本化并计入 rules_digest 输入（判定物表达选独立字段而非 assets 条目：托管段是用户文件内的段而非独立资产文件）；三处「托管段」引用对齐到登记处 |

### 机检输出（第六轮修复后）

```
$ /softwares/python/bin/python3 scripts/validate-wf-design.py
机制稿：引用 416；二值场景 91/91；三档场景 13/13；输入摘要 4/4（仅机械关系，不证明语义正确）
OK：设计 720 行 / charter 129 行；定义位点 51+7 个；索引表 143 行；消费点缺项 0；三率：定义命中 100% / 消费点命中 100% / 引用检查残差 2 行（输出不设阈值）；七项检查 + 覆盖率断言通过
```

引用数由第五轮 363 增至 416（本轮大量新增带所有者的「本文 §」引用）。中途一次 FAIL（5 处引用缺所有者：§0.2 行内裸 §3.2、四处「本文 §A/§B」斜杠连写不合机检的列表分隔符口径）改为「本文 §A、§B」后复跑全绿。四份输入文件 sha256 与 §0.1 表逐字一致（§0.1 无需更新）。`git diff --stat`：design 6 行、index 2 行为第一轮既有未提交改动；mechanism.md 144 行变更（含第二至五轮既有未提交改动）；本轮实际触碰仅 mechanism.md 与本文件。新增正文无 ASCII 直引号（diff 加号行中的直引号全部为 `H("wf-…-v1", …)` 哈希域名代码字面量，属既有代码样式例外）。

### 自查（第六轮，按任务指令七项）

1. **check_anchor 键集合逐键来源**：九键均对照 :259（修复前）/§3.5 :279（修复前）现有列举核实——plan_version←「批准版本/批准」、entry_snapshot_digest←「entry_snapshot」、touch_paths_digest←「触碰面/触碰路径集合」、content_digest←「指纹」、acceptance_digest←「验收摘要」、spec_versions←「相关 spec/规范」、baseline_digest←「基线」、config_digest←「有效配置/配置版本」、workflow_snapshot_digest←「影响执行的定义快照哈希」；「所用框架规则兼容标识」不进 check_anchor 哈希、由 anchor 结构的 rule_version 字段承载（§10.2 :751 的 Check.anchor.rule_version 取值语义因此保住）。**注意：content_digest 为任务草案八键之外增补的一键**，理由见需人工复核点 1。
2. **内容/规则两类口径一致**：:864（分类枚举+锚点公式）、:881（选择规则）、:883（查询）、:889（completed_ref/重跑触发）、:751（§10.2）、:714（§9.3）六处均为「规则类按 id/rule_version/occurrence、内容类按 id/occurrence、不因规则字节变化失配」；P 表三个内容类 id 的形状（{plan_version}/{plan_version, knowledge_digest, specs}/{triggers}）未改，本就不含规则输入，与分类一致。
3. **新增码枚举**：3 枚（WF_VERIFICATION_UNREADY/WF_DEFINITION_INVALID/WF_TEMPLATE_INCOMPLETE），均 blocked，均给「出口与禁止的错误修复」列，风格与既有码一致；映射表 4 行（第 4 行映射既有 WF_SEMANTIC_DECISION 不新增）。任务指令称「既有 31 枚」，实际修复前码表为 29 枚（WF_OK 至 WF_PERSISTENCE_FAILED 逐行清点），本轮后为 32 枚；任务中的计数与实际有出入，未按 31 回改任何内容。
4. **plan-q 排除规则与模板标记纪律同构**：:122 引「讨论这些标记的普通正文不是模板使用位点」——该字面短语在 §10.2（清单 template_markers 段），§2.3 为同义句（「不因业务说明讨论 TODO 或字符串示例而误拒」），故引用写为「本文 §2.3、§10.2 的模板标记纪律同类」；任务指令标注的 §2.3 单独引用不精确，已按实际位置修正。
5. **启动校验顺序与设计稿 §5.4 逐项对应**：十项 = 记录 schema/取值 → 候选唯一 → 会话写者/绑定 → 维护写者/预览范围操作 → 当前绑定与写者类别/标识/代次/范围/恢复 → 未结束实例快照/游标/归属/结束中断 → DAG 与被引用归档终态 → 写者标记（记录锚点核对）→ 框架资产可用性 → 未处置 WIP 及维护待持久化组；设计稿清单中「DAG」「被引用归档任务的终态」两项按任务指令合并为第⑦项、「未处置保留 WIP」「维护待持久化」合并为第⑩项，无遗漏。
6. **可达提交查证一处定义**：算法通用子句（拓扑逆序、不扫描操作之前历史、不「近 N 次」截断、不倒算、下界不可达走锚点核对）唯一编码在 :338；:342 与 :408 均只给各自登记结构（§4.5=操作回执+路径组终态；§5.3=归档终态+目录移动+路径组），grep 确认无第二处完整算法表述；:426 依赖满足改引「本文 §4.5 定义的可达提交查证、以本文 §5.3 的归档登记结构派生」。
7. **13 项落点汇总表**：见上表，全部为 mechanism.md 单文件加本文件；四上位文件 sha256 未变。

### 需人工复核点（第六轮）

1. **check_anchor 键集合在任务草案 8 键外增补 content_digest**（mechanism:260）：任务给出的公式草案不含 content_digest，但修复前 :279 anchor 段明确列有「指纹」，且设计稿 §4.2 检查有效性要求 Check pass 对应「内容指纹」——若按 8 键定稿，锚点对交付内容变化不敏感，:290「当前 anchor 与检查保存值一致」的有效性判定会漏检同路径内容变化。故按「键集合对照现有列举逐项核实后定稿」的授权增补该键。若用户本意是让内容绑定完全由 check.id 承载，需回退该键并同步改写 :290 的有效性表述。
2. **内容类回执的 rule_version 字段记 null**（mechanism:881）：回执 schema（§1.3 :122）的字段表未改，内容类以 null 占位而非删字段，保持 schema 统一；若认为应从 schema 层面区分两类回执形状（内容类无 rule_version 字段），需另行登记 schema 修订。
3. **§10.2 :751 的最小连带修正**：任务指令称「§10.2 :737-743 保持」，但「Check.anchor.rule_version 与 required 回执的 rule_version 均取此值」在 B2 分类后对内容类不再成立，已最小改为「与规则类 required 回执的 rule_version 均取此值；内容类回执不按 rule_version 匹配」；effective_rule_version 定义本身未动。若认为该句应整句保持原样，需回退并接受与 :881 的字面张力。
4. **§9.1 :678 审查 check-anchor 行的连带对齐**：任务 B1 未列该行，但其组件列举与 check_anchor 键集合同源，已改为引用 §3.2 定义（保留括注组件枚举便于报告可读）；若认为审查协议字段应独立列举，可回退为原句。
5. **B4 码表计数差异**：任务指令「与既有 31 枚风格一致」，实际修复前为 29 枚（见自查 3）；请确认任务计数是否另有所指（如把档位/出口列计入），本轮按实际行数执行。
6. **C8 的 gitignore_managed 计入 rules_digest 输入**：这改变了 rules_digest 公式的输入集合（首版未发布，按「首版可新增」处理）；若认为托管段内容不应影响规则兼容判定（例如纯注释行变化不应使规则失配），可将其移出 rules_digest 输入、仅随清单版本化。
7. **C2 顺序表的原因码配对**：十项与原因码的配对（如④维护写者对应配 WF_PREVIEW_STALE、⑤配 WF_GENERATION_STALE/WF_IDENTITY_UNRESOLVED）为按各码既有语义的择优，任务指令只点名了部分码（WF_RECORD_INVALID/WF_WRITER_BUSY/WF_BINDING_MISMATCH/WF_HISTORY_UNRESOLVED/WF_CAPABILITY_UNAVAILABLE）；未点名的配对请人工过目。

## 第七轮修复记录（外部复审 6 项 + 根因救济，主会话直接执行）

修复对象仅 `docs/workflows/wf-framework-mechanism.md` 与 `scripts/validate-wf-design.py`（R2 机检）及本文件；四份上位文件未改（sha256 复核与 §0.1 逐字一致）。用户要求不使用子代理，本轮全部由主会话直接执行。三项用户裁决：C2 按判据改判（spec-loaded/work-satisfied → 内容类）、R1/R2 最小落地、R4 建委托反查表。

### B1：机械修订等价链接入检查锚点与回执（:262/:120/:873/:894/:53）

- §3.2 :262：check_anchor 的 plan_version/acceptance_digest 经等价链归一（当前 plan.version 可沿 §1.3 equivalences 回溯到既有批准版本时取归一值）；touch_paths_digest 取链两端规范化后相等的路径集合哈希——机械修订不改变锚点，语义变化回 Plan 重批后链断开、锚点随之变化。
- §1.3 :120：equivalences 定义升格为**等价链**（链完整性 + 两端规范化 touch_paths/验收摘要相等的机械同义判据），声明其被 check_anchor 与 task.plan-approved 回执两处消费。
- §11.2 :873 P 表 plan-approved 证据列：补「经等价链归一到批准版本时，原 completed 回执可复用（skip_basis 记等价链核对事实）」分支。
- :894 skip_basis：补 plan-approved 复用须记等价链核对事实；重跑触发补「plan-approved 含等价链归一后的主键失配（语义变化使链断开）」——闭环「语义变了必须重批」。
- 修法效果：PRD 排版/措辞修订不再迫使重新批准 + 重跑 Check（对齐设计稿 §4.2「只修排版……不重复问人」）。

### B2：debug 判重结构化（:124/:865）

- §1.3 :124：剔除结论结构化为声明条目的 `dedupe_refs`（`[{check_id, command_digest}]` 数组，由人/主会话在同一轮裁定给出）；合并累计 =「check_history failed 条目数 + 声明核定次数 − dedupe_refs 条目数」从结构化字段求和，可机械重建；依据文本保留在 Decision.reason。
- §11.2 :865 gate 格：判重句同步（剔除结果结构化保存、合并累计从结构化字段求和）。
- 修法效果：「语义人判」与「计数可重建」同时成立（归档阻断不再依赖自然语言解读）。

### B3：启动校验码绑定与档位（:402）

- ② 多执行候选改报 WF_RECORD_INVALID（记录集不变量破坏，出口为恢复/repair 而非等待写者；候选不属写者绑定时另报 WF_BINDING_MISMATCH）——消除「人一直等一个不存在的写者」的误导。
- ⑩ 拆档位说明：存在未处置组=blocked（facts 写明为确定边界事实）；去向/归属未明=needs_decision——同一码 WF_WORKSPACE_UNRESOLVED 以 facts 区分档位与出口。
- 顺序关系注：启动十步与 §2.3 开工序列同源，开工序列为启动序列的开工时点子序列并前插身份/绑定核对——同一故障两入口首报项一致（先身份/绑定类、后记录类）。

### C1：映射表补齐（:840 附近）

- gate.evaluate 缺项 → 按缺失步骤 id 分派既有码（plan-approved 等内容声明缺失→WF_APPROVAL_MISSING；check/tdd/review 缺失→WF_CHECK_FAILED；spec-loaded→WF_SPEC_INCOMPLETE；changes-persisted→WF_PERSISTENCE_FAILED）——全部复用既有码，未新增。
- run.locate 定位失败 → WF_BINDING_MISMATCH/WF_HISTORY_UNRESOLVED。
- asset.compare 三方冲突 → WF_ASSET_DECISION（needs_decision，facts 写明冲突类型）。
- 5 个只读断言中缺映射的 3 个全部补齐（definition.validate 已有）。

### C2（用户裁决：按判据改判）：:869

- 分类判据改写为**可核判据**「gate 处理器是否读取 rule_version 或规则正文」。
- spec-loaded、work-satisfied 移入内容类（其 gate 分别只读会话侧车/全文读取事实与批准目标/实际交付/execution.actions）；changes-persisted 维持规则类（门禁核查 rules_digest 与发行规则兼容，判据在表内写明）。
- 效果：发行资产错字修正不再迫使重读未变 spec 正文/重核未变工作满足事实；自述标准与分派一致。

### C3：三处判定域补验收夹具行（:1061-1064）

- 「机械修订不重复批准」（排版修订→等价链核对→旧 pass 与 plan-approved 回执不失效）。
- 「规则类失配与内容类稳定」（资产字节变化→规则类重核、内容类不失配不重复人批准）。
- 「启动校验顺序与首报项」（双故障两入口首报一致；②报恢复出口、⑩档位按 facts 区分）。

### R2 最小落地：§1.1 硬规则 + 脚本域名机检

- §1.1 :74 后新增「结构逐键定义硬规则」段：哈希输入/匹配键/清单成员结构须逐键定义，散文式列举不构成定义。
- `scripts/validate-wf-design.py` 新增 `check_hash_domains()`：10 个 H("wf-…") 域名逐个核对有逐键定义段（C({...}) 形态或键集合说明），缺定义报 FAIL。
- R1：§0.2 表前导段补固定反查动作句（schema 键→消费者/出口反查是复审固定步骤，非发现驱动追加）。

### R4（用户裁决：建反查表）：§12.1.1

- 新增「设计稿委托句反查表」小节：12 行（设计稿明文 9 处委托句 + 隐性委托中已落位的 3 处典型项：预算键、原因码表内 §8.1 场景行引用、交付清单分轮），每行「委托句（章节）/委托内容/本稿落点」，落点全部经 grep 逐一核实（§8.2 确认元组、§1.1 3.11、§11.1 32 枚码、§1.1 UUID4、§5.4 重建比对、§8.1 全键表、§1.4 维护标识公式、§4.1 flock、§1.1 Id、§1.4 准备 schema、§8.4 码点口径、§10.2 引用与清单、§12.1 D01–D38）。

### 机检输出

```
机制稿：引用 457；二值场景 91/91；三档场景 13/13；输入摘要 4/4（仅机械关系，不证明语义正确）
OK：设计 720 行 / charter 129 行；定义位点 51+7 个；索引表 143 行；消费点缺项 0；三率：定义命中 100% / 消费点命中 100% / 引用检查残差 2 行（输出不设阈值）；七项检查 + 覆盖率断言通过
```

引用 416→457（等价链/反查表/映射表新增带所有者引用）；域名机检 10/10 通过。机制稿 1057→1085 行。四上位文件 sha256 未变，§0.1 无需更新。`git diff --cached` 为空（未暂存未提交）。

### 交叉一致性自查（主会话）

1. 等价链三处（§1.3 定义、§3.2 锚点归一、§11.2 复用分支）口径一致：链完整 + 两端规范化 touch_paths/验收摘要相等 = 机械同义；语义变化链断开。
2. dedupe_refs 双处（§1.3 定义、§11.2 gate 引用）公式一致。
3. 回执分类：新五内容类/四规则类在 :869 枚举、:888 选择规则（按类不点名 id）、§0.2 :53 登记行三处一致。
4. 启动⑩档位拆分与 WF_WORKSPACE_UNRESOLVED 码表定义（needs_decision）的关系：以 facts 区分档位，码义未改（码表语义「去向或归属未明」覆盖待决面；blocked 面由 facts 显式声明，出口仍为逐路径核实）。
5. C1 映射的 4 行档位/码与 §11.1 码表逐枚核对无冲突；asset.compare 用 WF_ASSET_DECISION 的 needs_decision 档与该码表行一致。

### 需人工复核点（第七轮）

1. **⑩ 档位拆分未新增码**：WF_WORKSPACE_UNRESOLVED 一码两档（blocked/needs_decision 以 facts 区分）。判断建议「拆成两码」或「改 blocked 并说明区分」，本稿选择共用一码 + facts 区分——理由是码表已有「同次多个问题可返回有序 issues」的多问题机制，码义「WIP/维护组去向或归属未明」对两档都不撒谎；但一码两档是否违反「码值语义一经发布不改」的精神，交人复核。
2. **gate.evaluate 分派码为映射表内新增行**：按 id 分派既有码的做法把「缺哪个步骤」的语义留在 facts——符合「具体对象放 facts，不为每个文件新增原因码」的既有纪律，但 4 个分派码的选择（尤其 WF_APPROVAL_MISSING 覆盖 knowledge-disposed/retrospective-done 的「声明缺失」）请复核。
3. **等价链归一的 touch_paths_digest 描述**（§3.2「取等价链两端规范化后相等的路径集合哈希」）：归一语义已定义，但「两端相等时取哪端」由链定义隐含（取归一到批准版本的一端），无歧义但表述较密。
4. C6 引导例外清单同步（第六轮遗留，本轮 R4 反查表中 §1.1 执行器解析行未涉及该委托）：设计稿是否补引导例外清单仍待人工裁决。

本轮后不提交，留人工审查。

## 第八轮修复记录（外部复审 5 项 + R6/R7 根因，主会话直接执行）

修复对象仅 `docs/workflows/wf-framework-mechanism.md` 与本文件；四上位文件未改（sha256 与 §0.1 一致）。一项用户裁决：B2 新增专用 blocked 码 WF_WIP_UNRESOLVED。5 项判断全部核实属实并修复：

### B1：归一进入 P/occurrence 定义层（:890/:895/:120）

- §11.2 :890（回执选择段）：P 中 plan_version **一律取经等价链归一后的批准版本**，规则明文适用于 P 含 plan_version 的全部内容类回执（plan-approved/work-satisfied/knowledge-disposed），不逐 id 另述——occurrence 随 P 归一，机械修订后原 completed 回执可查得、可写 reused，闭环了上轮「承诺在处理器层、公式没跟动」的缺口。
- :895 skip_basis：归一发生时 checked_outputs 另列「本次 plan.version → 归一后批准版本」映射事实供核对。
- §1.3 :120 等价链定义同步声明 P 消费（原只写 plan-approved 回执消费）。

### B2（用户裁决：新增专用码）：:813/:402/:984

- §11.1 新增 `WF_WIP_UNRESOLVED`（blocked；存在登记的未处置保留 WIP/待持久化维护组——确定边界事实；出口：按登记限制执行、不当空闲放行），`WF_WORKSPACE_UNRESOLVED` 维持 needs_decision 原义——一码一档纪律恢复。码表 32→33 枚，§12.1.1 反查表同步。
- 启动⑩改写：存在未处置组 → WF_WIP_UNRESOLVED（blocked）；去向/归属未明 → WF_WORKSPACE_UNRESOLVED（needs_decision）——两码各一档按事实性质分派。

### B3：启动序列重排消除自相矛盾（:402/:1066）

- 十步重排为「①当前会话绑定/写者 → ②会话写者与绑定 → ③执行候选唯一性 → ④维护写者 → ⑤记录 schema → ⑥实例快照/游标 → ⑦DAG/终态 → ⑧写者标记 → ⑨框架资产 → ⑩未处置组」——身份/绑定/写权（①-④）在前、记录类（⑤起）在后，与开工序列同构；「同一故障两入口首报项一致」断言现在与序列本身一致（上轮 ①记录在最前与断言直接矛盾）。
- 夹具 :1066 断言同步新编号（③多候选、①-④身份类）。

### C1：review-passed 映射改码（:843）

- gate.evaluate 映射中 review-passed 缺失/过期 → `WF_REVIEW_INVALID`（出口补真实审查/重新发起，不指向重跑测试）；work-satisfied/check-passed/tdd-verified 维持 WF_CHECK_FAILED。消除「同一事实两路径给相反下一步」的错配。

### C2：dedupe_refs 约束与下限（:124/:1062）

- §1.3 补两项约束：dedupe_refs 的 check_id/command_digest 对全任务全局唯一（重复 → WF_SEMANTIC_DECISION）；单条声明 dedupe 数 ≤ 核定次数；求和结果不得小于 check_history 条目数——越界（含负数）按 WF_RECORD_INVALID，不据此判倍数。
- 夹具 :1062 补「两条声明 dedupe 同一 check_id 的双扣情形」断言。

### C3：等价链条目改 Decision 承载（:120）

- equivalences 每条衔接以 Decision 承载（subject=新旧版本与两端摘要、choice 固定「机械修订」、reason+source）；锚点归一与回执复用核该 Decision 当前有效（未被后续修订作废）——脚本仍不判语义，只核「有 Decision 且链完整」。纪律写入不再能单方面保住旧 pass（charter T4 检查面不降）。

### R7 救济（部分落地）：映射表加「引用的码表行」列

- 映射表表头改为「档位与原因码（引用的码表行）」；gate.evaluate 行逐码对照码表行、run.locate/asset.compare 行补码义对照（含 asset.compare 明示其码法定档位为 needs_decision、冲突面不单独给 blocked 档——修正上轮误写「二值侧」的档位歧义）。
- R6（派生值目录）与 R7 剩余部分（夹具断言由序列表生成、目录机检）**未在本轮落地**——见下。

### 根因表更新（R1-R7 现状）

| 根因 | 本轮处置 |
|---|---|
| R1 判定域人工枚举 | 未变（§0.2 提示句维持） |
| R2 逐键定义 | 未变（存在性机检维持） |
| R3 等价维度 | B1+C3 贯通到 P/occurrence + Decision 载体——R3 救济完成 |
| R4 委托反查 | 未变（§12.1.1 维持） |
| R5 回执多重职责 | 未变 |
| R6 派生值/叙述层分离 | 本轮 5 项修复全部是「叙述层已写、公式层跟动」的补齐（B1/B2 即例）；「派生值目录」机制未建——属结构性新机制，建议登记设计稿 §8.3 候选而非本轮硬造 |
| R7 跨表一致性 | 映射表码表行列已加；夹具断言改为「由序列表/公式表生成」的机检未建——同上，属脚本工程，登记候选 |

### 机检输出

```
机制稿：引用 459；二值场景 91/91；三档场景 13/13；输入摘要 4/4（仅机械关系，不证明语义正确）
OK：设计 720 行 / charter 129 行；定义位点 51+7 个；索引表 143 行；消费点缺项 0；三率：定义命中 100% / 消费点命中 100% / 引用检查残差 2 行（输出不设阈值）；七项检查 + 覆盖率断言通过
```

`git diff --cached` 为空（未暂存未提交）。旧措辞（「同一码，needs_decision」「以 facts 区分档位与出口」「task.plan.version、content_digest=」）grep 零残留。

### 需人工复核点（第八轮）

1. **R6「派生值目录」与 R7「断言由表生成」未建**：属结构性新机制/脚本工程，按 charter T5.2 缺口三问应登记设计稿 §8.3 候选（依据：本轮 B1/B2/C1 三个跨层缺口均由 R6/R7 解释，已出现两次以上同类漏扫）——是否本轮顺带登记候选行，交人裁决（登记需改设计稿，涉及 §0.1 摘要更新）。
2. 启动序列重排后 ⑤记录项从 ①移位：依赖「先核身份才能安全读记录」的假设（身份未明时读到的绑定记录可能属他会话）——重排语义上更稳，但与设计稿 §5.4 启动校验列举顺序（记录项在前）的字面顺序不同；设计稿该段是清单非顺序规定，不构成冲突，提请知悉。

## 第九轮修复记录（外部复审 4 项，主会话直接执行）

修复对象仅 `docs/workflows/wf-framework-mechanism.md` 与本文件；四上位文件未改（sha256 与 §0.1 一致）。4 项判断全部核实属实并修复，无新增用户裁决（command_digest 处置采用判断给出的「删键、check_id 已足」方案，理由见 B1）。

### B1：debug 计数载体建 schema（:124/:578/:866/:292/:1065/:52）

- §1.3 :124：新增 `execution.debug_declarations` 具名条目数组（初值显式空），每项 `{verification_id, counted, evidence_refs, dedupe_refs}`——counted 为入口核定的计入次数（正整数）、dedupe_refs 为 `[{check_id}]` 数组；写者（continue/finish 裁定入口）、消费者（§8.1 检测、§11.2 复盘门禁）、失败出口（WF_SEMANTIC_DECISION/WF_RECORD_INVALID）三要素齐备；debug-ruling 裁定条目与对应声明条目同批写入（前者结论、后者计数事实）。
- **command_digest 处置**：按判断选项②删键——check_id 是 check_history 的唯一条目定位、足以唯一标识一条历史失败；命令级溯源由该 check_id 对应条目 command 项的 invocation 查得（不需要新哈希域，也不引入「匹配键非域名」的 R2 缝隙）。全局唯一约束相应简化为「同一 check_id 全任务唯一」。
- 判重段四处同步（dedupe 结构/counted 字段名/求和公式/subject 记录）、§8.1/:578、§11.2/:866、§3.5/:292、夹具 :1065、§0.2 登记行全部改引新字段名；grep「command_digest/声明条目核定/核定次数之和」全文清零。
- 机检缺口确认（判断分析正确）：check_hash_domains 只扫 H("wf-…" 域名，字段名级匹配键在其缝隙——R2 机检扩为「字段名级匹配键」属脚本工程，与 R6/R7 一并留候选登记。

### B2：gate.evaluate 映射改二维（:843）

- 映射从「按缺失 id 压平为单码」改为「先按未满足的**原因事实**选码/档位、再以缺失步骤 id 列清单」：批准/人判未答 → needs_decision WF_APPROVAL_MISSING；产物/验证 fail → WF_CHECK_FAILED；审查不合格 → WF_REVIEW_INVALID；提交未授权 → WF_COMMIT_NOT_AUTHORIZED；提交失败 → WF_PERSISTENCE_FAILED；WIP 未处置 → WF_WIP_UNRESOLVED；正文未读 → WF_SPEC_INCOMPLETE。
- changes-persisted 的三面（未授权/失败/未处置）显式分派——消除「把未授权说成持久化失败」的方向错误与「压掉待决档」的档位错误；决定性事实列同步为「清单逐项带原因与码，档位随码」。

### C1：启动③数据依赖倒置（:402）

- ③ 判定候选唯一性前先对活动任务记录做**轻量可读性检查**（仅要求能取出 status/phase/paused/suspended 各键，完整 schema 解释仍归⑤）；任一不可读时以「候选未知」上报并先列该事实——「未知优先于判定」成为序列的一部分（不把损坏记录当无任务或零候选，与 §8.5/§11.1 纪律一致），完整诊断随⑤ WF_RECORD_INVALID 给出。
- 序列尾补通用规则句：「判定使用记录事实的步骤在其数据源通过可解释校验或轻量可读检查之前，只允许输出"未知"并列出该事实」——该原则不限于③，覆盖⑥⑦对同类数据源的依赖。

### C2：反查表拆「判定物」四行（:983）

- 原「原因码表」单行拆为四行（预览令牌→§10.3、占位标记集→§2.3/§10.2、归属判定→§3.3/§5.1、原因码→§11.1 33 枚），完整承接设计稿 §8.2「判定物与原因码」委托行的四类对象——修复「只登记一项、改令牌时查不到」的 R4 复发面。

### 机检输出

```
机制稿：引用 469；二值场景 91/91；三档场景 13/13；输入摘要 4/4（仅机械关系，不证明语义正确）
OK：设计 720 行 / charter 129 行；定义位点 51+7 个；索引表 143 行；消费点缺项 0；三率：定义命中 100% / 消费点命中 100% / 引用检查残差 2 行（输出不设阈值）；七项检查 + 覆盖率断言通过
```

引用 459→469（B2 二维映射与 C2 四行新增引用）。`git diff --cached` 为空（未暂存未提交）。四上位文件哈希未变。

### 根因表更新

| 根因 | 本轮处置 |
|---|---|
| R1 人工枚举 | debug_declarations 已按「新增字段同时入 schema 与消费算法」登记（§0.2 :52 同步）；机检派生未建（维持） |
| R2 逐键定义机检过窄 | B1 确认缝隙属实（字段名级匹配键漏检）；扩展机检属脚本工程，与 R6/R7 一并留候选 |
| R3 等价维度 | 无新问题（正面样本维持） |
| R4 反查表 | C2 补全判定物四行 |
| R5 回执多职责 | debug_declarations 为新职责建了 schema（B1），职责分层未显式建模（维持） |
| R6/R7 | 未救济（登记候选待人工裁决，第八轮复核点 1 延续） |

### 需人工复核点（第九轮）

1. R6（派生值目录）/R7（断言由表生成）/R2 扩展（字段名级匹配键机检）三项结构性救济仍待裁决是否登记设计稿 §8.3 候选（连续三轮同类漏扫证据已足）——登记需改设计稿并更新 §0.1 摘要。
2. B2 二维映射的 7 个码/档位分派与 §11.1 码表逐枚对照过，但「work-satisfied 的必需人判未答归 WF_APPROVAL_MISSING（needs_decision）」的档位选择（该码原语义偏「批准缺失」blocked 面）请复核——另一选择是归 WF_SEMANTIC_DECISION。

## 第十轮修复记录（外部复审 4 项 + R7a 救济，主会话直接执行）

修复对象仅 `docs/workflows/wf-framework-mechanism.md` 与本文件；四上位文件未改（sha256 与 §0.1 一致）。两项用户裁决：B2 未答面复用 WF_SEMANTIC_DECISION；R7a 本轮落地「码表加列+档位单源」（机检留候选）。

### B1：登记表同步 debug_declarations（:112）

- §1.3 :112 execution 登记行改 `{required_steps, actions, human_decisions, debug_declarations}`、「四者初值为空数组」，消费列补「复盘计数/机械检测」——与 :124 新增段的「四个成员/初值显式空数组」硬矛盾消除，§1.1 初值契约统一。
- 顺手核对：curation（:114）、check_history（:111）均写「显式空与缺失不同」，check 为独立登记行——初值契约全表一致。

### B2（裁决）：未答面改码 + work-satisfied 人判面 + 每分支一码（:843）

- gate.evaluate 二维映射：「必需人判/批准未答（待决面）」→ `WF_SEMANTIC_DECISION`（按裁决复用，覆盖 plan-approved/knowledge-disposed/retrospective-done 待答面 **与 work-satisfied 的必需用户动作未答**——修复上轮压掉的人判面）；「批准缺失或与版本不符（已确定违反）」→ `WF_APPROVAL_MISSING`（blocked 原义不变，不再一码两档）。
- run.locate 同步修混档：行级「blocked」标注删除，只按原因写码（WF_BINDING_MISMATCH / WF_HISTORY_UNRESOLVED——后者法定 needs_decision，原行把它压在 blocked 行级下）。
- asset.compare 同样去档位、冲突类型归 facts。

### R7a（裁决）：档位单一来源（:797-:835/:837-:845/:402）

- §11.1 码表拆列：「档位与决定性事实」拆为「档位」+「适用事实」两列（33 枚逐枚拆，含 WF_OK 的 pass 档）——档位与适用事实自此各有单一来源；新增出口引用码时对照「适用事实」列。
- 处理器映射表表头改「码（档位由本文 §11.1 码表单一来源）」，全部行去行级档位（blocked；/needs_decision； 前缀删除）。
- 启动⑩去行级档位（按事实性质选码，档位由码表派生）。
- 档位一致性机检（表内档位 ↔ 码表比对）未建——脚本工程，与 R2 扩展/R6/R7 一并留候选登记。

### C1：未知态配码（:402）

- ③ 轻量可读检查的未知态与序列尾通则均补：未知态取 `WF_HISTORY_UNRESOLVED`（facts 写明不可读对象），可确证记录损坏时并用 `WF_RECORD_INVALID`，不据未知出放行或阻断结论——「未知优先于判定」不再是无码占位。

### C2：夹具断言（§12.3 新行）

- 新增「缺项分派与未知优先」行：覆盖 changes-persisted 三面（未授权/提交失败/WIP 未处置）、work-satisfied 用户动作未答 → WF_SEMANTIC_DECISION、批准失配 → WF_APPROVAL_MISSING、记录不可读 → 未知态先列事实——本轮 B2 类档位错配自此有验收断言兜底。
- 既有「启动校验顺序与首报项」行同步（⑩两码新写法、③未知态）。

### 机检输出

```
机制稿：引用 473；二值场景 91/91；三档场景 13/13；输入摘要 4/4（仅机械关系，不证明语义正确）
OK：设计 720 行 / charter 129 行；定义位点 51+7 个；索引表 143 行；消费点缺项 0；三率：定义命中 100% / 消费点命中 100% / 引用检查残差 2 行（输出不设阈值）；七项检查 + 覆盖率断言通过
```

引用 469→473。码表区域 33 枚全部 5 列结构一致；行级档位残留（blocked；`/needs_decision；` 前缀）grep 清零。`git diff --cached` 为空（未暂存未提交）。四上位文件哈希未变。

### 关于「问题性质演进」的采纳

判断指出 B 类已从「设计不可实现/自相矛盾」退化为「变更没同步到另一处」（登记表漏一行、出口表档位错一行）——本轮 B1 即典型例。采纳其结论：文本复审只能抽样，根治靠生成器/机检（字段登记生成、档位单源机检、表间引用机检、断言同源）。其中文档层可立即落地的「档位单源」本轮已做（R7a）；四项脚本工程（登记生成/档位机检/引用机检/断言同源）合并 R2 扩展为一份候选登记待人工裁决。

### 需人工复核点（第十轮）

1. **脚本工程候选登记**（R2 扩展 + R6 + R7 + R7a 机检四项合一）：是否登记设计稿 §8.3 候选行——登记需改设计稿并更新 §0.1 摘要；判断已给出「六轮 B 类退化为变更同步缺陷」的趋势证据，建议登记。
2. work-satisfied「必需用户动作未答」→ WF_SEMANTIC_DECISION 的裁决已执行；该码「语义未决」原义偏知识/工作流语义，用于「用户动作未答」是语义扩展（未改码义描述本身，仅在映射层引用）——若认为应为其单列码（如 WF_APPROVAL_PENDING）可在人工审查时改判。

## 第十轮复核点裁决记录（2026-11-02，用户裁决）

1. **脚本工程候选（R2 扩展 + R6 + R7 + R7a 机检四项）**：裁决为**方案 B**——不登记设计稿 §8.3（authoring 机检属本仓库工程工具，非产品级候选，登记越层）；改为在机制稿 §0.2 表前导段追加机检演进说明：四项扩展按 findings 根因记录逐项落地，落地前由固定反查动作与人工复审兜底。已执行（:40），不触发设计稿哈希链。
2. **work-satisfied「必需用户动作未答」码归属**：裁决为**维持复用 WF_SEMANTIC_DECISION**——映射层引用不变。注：码表该行「适用事实」列字面为「知识/工作流/规划等语义未决」，未含待答面字样；该引用属映射层语义扩展（码义描述未改），若后续复审对此再提出异议，最小修法是把码表适用事实列扩写为「……含必需人判/用户动作/批准声明的待答面」（一格文字，不动码义）。

机检复核：引用 473；场景 91/91 + 13/13；摘要 4/4 全绿。四上位文件哈希未变，暂存区为空，未提交。
