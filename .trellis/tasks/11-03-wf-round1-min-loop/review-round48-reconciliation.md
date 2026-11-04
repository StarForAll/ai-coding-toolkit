# 第四十八轮：第五轮独立复审（A1/A2/A3/A5、B1/B2/B3）+ 其他 agent（1/2/3）

- 处置编号 R83；实跑见 `validation.md` §75
- 结论：**10 条成立并已修**；A4 判通过。
- 这轮的性质变了：不再是我漏写功能，而是**我自己发明了规范里没有的判定**（A1/A2），以及**声称修好却没验**（A5/B2）。

## 一、「新增判定」类（本轮最严重的一类）

### A1 `RELEASE_CHOICES`（中）——已删除
我为"reject 不能解除"自造了三词白名单。机制稿 §1.3 只登记 `curation.released` 的四键，`decision` 复用 §1.1 的 Decision 结构，**choice 的取值域四份规范都没有登记**——收窄成三个词等于替人判语义（charter T3 边界、实现稿 §2.3 的封闭枚举纪律）。

处置：删掉词表，退回**纯结构核验**（decision 是对象、choice 非空、reason 非空、old_path/old_digest 可核对）。"这句 choice 是否表达解除"留给人在记录里承担——脚本只保证"人确实写了决定、且这条决定可定位"。

### A2 `SUPPORTED_TRANSPORTS`（中）——收回一个词
我写了三个词，机制稿 §1.4 明说「transport 首版只取 request_json」，`stdio_json`/`mcp_tool` 在四份规范里零出现，且框架没有任何对应通道——等于向人宣称两条不存在的能力。

处置：白名单只留 `request_json`，将来扩通道必须先改机制稿。

### A3 声明式证据自证（高）——最严重
`--verify-capability` 会生成一条 `kind=declared-verification` 的证据，而我又把"证据须带 kind/ref"当放行判据——于是**安装器自己写的声明满足了自己的核验**。实现稿 §2.3.7 早就写了「只有声明而无观察时应按『声明式 verified』报告，不得宣称已核实」，我的实现与这句话直接冲突。这也是 N-R79 的教训走反了：判据收紧后夹具被拒，我选择"给自证证据补字段"，而不是"让判据拒绝自证"。

处置：
- `OBSERVATION_KINDS = (compaction, reentry, new-session, transport)`（机制稿 §1.4 列举的观察类别）；
- 只有**人给出的、kind 属上表、且带 ref** 的证据才算 observation；`declared-verification` 明确排除在放行集合外；
- `install.py` 与 `wf-dev-deploy.py` 同判据：只勾 `--verify-capability` → `status=unknown`（声明记录仍留），人给了真实观察才转 `verified`。

### A4 `NON_SECRET_KEYS`（通过）
复审判通过并给了两个方向的反例：白名单键承载真实密钥形态仍被形态规则遮住；白名单外的计数键会被多遮，但只损失可读性、不泄漏。予以保留，并把实现稿里"只认形态、不判语义"的措辞改成"形态优先 + 已知非凭据键豁免"，消除文档与实现的张力。

### A5 续做三态只覆盖 add/modify（高）
`_resume_decision()` 只在写 content 的分支调用，delete/disable/rename 三个分支**完全没保护**：外部改动后仍会照删、照停用、照改名。

处置：新增 `_resume_decision_removal()`（delete/disable）与 `_resume_decision_rename()`，与 add/modify 同一套三态语义；四处共用同一错误出口 `WF_SEMANTIC_DECISION` 并保留现场。

## 二、B 组：修复落地质量

| 编号 | 结论 | 处置 |
|---|---|---|
| B1（低） | 只给外层 `decision` 的输入被**静默跳过**（无错、无写、上层报成功） | 外层形态一律 `WF_SEMANTIC_DECISION` 并要求 `released.{decision,replacement}` |
| B2（高） | `_pending_task_create` 恒返回 None（action 记录里没有 owner 字段），恢复逻辑是**死代码** | 改按 **action.id 派生**定位：用 `writer.owner_ref(session, key, task_scope)` + `action.base_revision` 重算与记录比对；`task-new` 里把恢复判定提到"已绑定"与 WIP 检查之前 |
| B3（低） | `report_path` 缺失或文件被删时抛裸异常 → exit 70 | 两处补出口：缺失与不可读都入 `problems`，统一 `WF_REVIEW_INVALID` |

## 三、其他 agent 的 3 条

1. **task-new 恢复找不到动作**——与 B2 同一根因；另外指出"意图写在 task 而机制稿 §5.1 规定由 writer 承载"。处置：保留 task 侧意图（机制稿 §5.2 的四态重入以动作记录为锚），并在实现稿登记"意图锚点 = task.action，writer 只承载写权"；恢复路径与"已绑定"判定、写权核验、结案后置一并覆盖。
2. **删除/改名续做缺口**——与 A5 同一根因，已修并各自加用例。
3. **正文已写、索引未同步的续做漏补索引**（新发现）：`skip` 分支直接 `continue`，把"后置条件"整体跳过了。处置：`skip` 时仍执行 `_sync_index()`；delete/disable 的 skip 同样补索引。

## 四、期间新发现（都是我改出来的）

- **N-R82**：`base_revision` 用 `or` 兜底，`0` 被当成缺省 → 派生 id 用 1 重算，恢复永远匹配不上。改为显式 `is not None`。
- **N-R83**：`holder_hint` 没带 scope，导致 action.id 的 owner_ref 与恢复端的推导不同源；补齐 scope。
- **N-R84**：install 的 `--capability-evidence` 只按"kind 字符串"存储，未解析 `kind=…;ref=…`，观察证据永远不被识别 → f0 全挂。改为与 dev-deploy 同一解析。
- **N-R85**：夹具与脚本全部只有 `--verify-capability`，A3 收紧后一律 `unknown`；给所有夹具补 `kind=reentry;ref=…` 的真实观察证据。

## 五、口径

五轮独立复审 + 其他 agent 累计处置 44 条。这一轮的教训写进实现稿 §2.3.11：**「补结构」不等于「补词表」**——规范没登记取值域时，实现只能核结构，不能自造白名单；反过来，规范登记了的观察类别（压缩/重入/新会话/传递）必须真被消费，否则"verified"就是声明自证。
