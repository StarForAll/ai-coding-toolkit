# dogfood 第二轮独立复审台账（2026-11-24）

> 输入：四份 traffic_monitor 实测会话（`/tmp/traffic_monitor_1..4.md`）、上一轮台账
> `dogfood-round5-dispositions.md`、归档任务 `11-24-wf-dogfood-residual-fixes` 的 prd/design/implement、
> 当前源码树（基线 `cf09db12` + 0.0.1 重建）。
> **证据缺口（如实声明）**：`/tmp/wf-find-a.md`、`/tmp/wf-find-b.md`、
> `~/.zcode/cli/log/zcode-2026-11-08.jsonl` 在本机已不存在（日志目录最早 11-17）；上一轮对它们的
> 采信只能经上一轮台账转述，本任务不复核原件。
> 判据：每条发现由主会话对照源码独立核实（file:line），不采信报告结论；裁定不改的写明理由。

## 1. 第一轮独立复审（两个干净子代理，只读、不用 MCP/网络）

- **机制面**：F1a–F8 十六项逐条核实**全部成立**（材料原子发布/身份绑定/启用前置/批准绑定/裁定覆盖/
  混合基线单一实现/§1.1 两处表述），42 项新增测试实跑全绿；另报 4 条新发现（下表 A-1…A-4）。
- **指引面**：设计稿 §1.1 二十个要点逐条对照实现，**19 项准确**（判据句两问、消费点定义、人签清单
  性质、正面授权、强度如实声明等均与实现一致）；唯「指令分工」存在实现面违例（skill/help 侧残留
  与定义位矛盾的旧口径），即下表 B 组发现。dogfood 历史卡点对照：新会话旧绑定、禁写 `.wf/` 径自
  普通开发、报告格式返工链、摘要锁重写链、"只登记不修"、两轮上限死锁、pass 后修订无路径、vendor
  混入提交——当前指引均封死；归档提交含未生成目录一条部分收敛（B-F10 后收口）。安装面向全部
  平台无残留漂移（`--platform`/`add_platforms` 在指引面零命中）。

## 2. 处置台账

| 编号 | 来源 | 判定（决定性证据） | 处置 |
|---|---|---|---|
| A-1 | P2 | 台账 implement.md:9-12 声称新增 `test_materials_atomic.py`（三条断言），实际该文件从未进入仓库（`ls`/`git log --follow` 零命中）——A1「中断不留半包」无回归防线 | **成立**。新增 `scripts/tests/wf_review/test_materials_atomic.py`：①正常物化无 staging 残留、发布后判据态 fixed；②`write_materials` 注入异常后无半包、空目录等同 unmaterialized、崩溃遗留 staging 由起手清理、重跑完整出版；③fixed 重入不重写 manifest 字节。台账声称自此为真 |
| A-2 | P3 | `cmd_task_rework` 的说明串落在 `--draft` 分支之后（tasks.py:5314），非首语句 ⇒ `__doc__` 为 None，是全仓唯一死字符串 | **成立**。docstring 移回函数首语句（无功能影响，纯维护面） |
| A-3 | P3 | review-status 逐槽位 restored 提示"可直接判定"，同页轮级 next_ 在混合基线时说"直接判定会撞混合基线"（review.py:1671 vs cli.py:3817-3820）——同一输出两处文案分叉 | **成立**。`status_of_round` 改读 `round_materials_basis`（与 decide/check_next_hint 同一实现）：混合轮的 restored 槽位提示改为"直接判定会撞混合基线，处置见轮级 next_"；非混合轮原提示不变。不加新机制 |
| A-4 | P3 | 弱身份（`legacy_adopted`/restored）的审查 pass 在 finish 处无消费指引：archive 门禁不消费 `materials_state`（gates.py 零命中），机制侧已如实产出事实（review-status facts `materials.state`、判定 facts `materials_state`） | **成立（指引面收口）**。wf-finish 步骤 1 补"呈现材料身份状态；非 `fixed` 的 pass 按弱证据对待——结论有效、证据强度如实报"。不新增机制：事实已由机制产出，缺的是判据位指引（符合 §1.1 后置条件：阻断无已观察失败） |
| B-F1 | P2 | wf-finish「证据文件纪律」仍写"可写的只有…五类"，与它自己指向的唯一定义位（wf-continue:154"不是五类白名单能穷举"）直接矛盾——上一轮删 wf-bootstrap 清单时漏了 finish | **成立**。改成与 wf-bootstrap 同构的纯指针（按"谁生成"判断 + inputs 为准），不再复述任何类清单 |
| B-F2 | P2 | help `task-approve` 称 plan-q 答复"要 choice=plan-q（旧夹具 choice=是 已不再接受）"，实现相反：识别靠 subject 编号、答复项 choice 任写（tasks.py `_answers_plan_q` 豁免未知 choice 校验） | **成立**。help 改为"识别靠 subject 编号，答复项的 choice 任写（未知 choice 校验不作用于 plan-q 答复项）" |
| B-F3 | P2 | help `review-accept-unknown` purpose 写"审查环境不可用时的接受/撤销"，skill 与实现均为"不可核实证据（unverifiable）的人裁放行"（skill 纪律行明说不接受不可用声明文件；handler 只消费 unverifiable） | **成立**。purpose 改"不可核实证据（unverifiable）的人裁放行/撤销"；`--file` 描述"不可用声明"改"放行决定文件" |
| B-F4 | P2 | wf-continue「不做」"不归档"与同文件路由表"归档中断重入 archive 续做"矛盾，正例未覆盖续做 | **成立**。改"不发起正常收工归档"，正例补"归档中断（status=archived 未移目录）按路由表重入 archive 续做" |
| B-F5 | P2 | wf-spec-update"语义是否冲突、该不该改，由人判"与同 skill 步骤 2（AI 判准入）、设计稿 §6.3（仅语义冲突/删除/合并/降级交人）、prefs（标准变更可 ai_decides）冲突，且无收敛动作 | **成立**。改三段分工：§6.3 人裁面照旧；普通准入与"改的是哪一类"AI 判；改尺子补 `judgments add`（kind=标准变更，prefs 两态，未补被 `WF_SEMANTIC_DECISION` 拦） |
| B-F6 | P2 | `release_allowed` 完整论述在 wf-repair-loop 与 wf-review-accept-unknown 双写（§1.1 明文"完整论述只在各自 skill 出现一次"） | **成立**。wf-repair-loop 降为一句判断 + 指针（取值公式留在 accept-unknown §3） |
| B-F7 | P3 | wf-start / wf-code-review / wf-tdd / wf-grilling / wf-diagnosing-bugs 的「不做」权限边界禁令缺"这不算违反"正例（§1.1 写作规则） | **成立**。各补一句正例，内容均取自该 skill 既有的份内事，不虚构行为 |
| B-F8 | P3 | wf-review"前 400 字符"、accept-unknown 入口规则清单属"skill 复制脚本可查事实" | **部分裁定不改**：wf-review 的窗口数字是 2026-11-24 上一轮刻意锁定的契约镜像——`test_guidance_contracts.StatusWindowTest` 同时断言出口文案与 skill 含同一数字，删除反而拆掉防漂移机制；accept-unknown 规则块是"报错前就知道"的采集契约（错一次成本是一次人裁轮次）。登记为 observation |
| B-F9 | P3 | wf-finish 未核实项给了四项依据判据但未指向收敛命令 `wf verify resolve`（13 个 skill 中 verify 零出现） | **成立**。补"收窄经 `wf verify resolve --kind narrow` 落档，人工核验证据走 `--kind inspection`" |
| B-F10 | P3 | wf-finish 的 `archive --draft` 触发条件"拿不准结构时"过弱——dogfood _4:1089-1094 实录：AI 自认拿得准、手写含未生成目录的提交清单翻车 | **成立**。改为规定动作：先跑 `--draft` 取草稿、按草稿写决定文件、不手写路径清单 |
| B-F11 | P3 | help `spec-update --changes[]` inputs 缺 `before_digests`/`after_digests`/`reference_dispositions`（spec.py:739/670 真实消费；wf-continue:156 说"以 help inputs 为准"——权威承载位自身不全） | **成立**。inputs 补齐三字段及各自语义（前像核对方向、入口回填、解除依赖条目形状） |
| B-F12 | P3 | session-flow「运行约定」第 2 条"人的决定只经 --decision/--plan/--disposition 文件承载"枚举不全（judgments/authorize/accept-unknown 等 `--file` 类人裁通道被排除在外），自称唯一论述位即漂移源 | **成立**。改"人的决定只经命令契约声明的人类输入通道承载（形状以 `wf help <命令>` 的 inputs 为准）" |
| B-F13 | P3 | 机制稿 §9.4"载体规则（2026-11-12 人裁，仅此一处定义）"与设计稿 §1.1 同日同规则构成双定义位，其中一处自称唯一 | **成立**。机制稿改"定义位在设计稿 §1.1「指引就地、不成层」，此处只登记实现侧落点" |

## 3. 设计稿 §1.1 AI 指导要点准确性结论（本轮）

20 个要点中 19 项经实现对照**准确**：判据句的两问结构（资格→后置条件）与"只被打印不算消费点"
消除了自证循环；"默认规则"前置与正面授权/负向禁令三处分工清晰；人签封闭清单及清单性质段（入口
动作不进清单、转录不降效力）与 §1.2 一致；"指引就地、不成层"与 13 skill/9+4 调用权登记一致。
唯一失准在**实现面**（skill/help 侧旧口径残留，即 B 组发现），设计文本本身无需修改；本轮修正后
该违例已清除。修正全程未新增 skill、未新增层级、未新增判断步骤。

## 4. 验证实况

- T0：`python3 -m unittest discover -s scripts/tests -t .` —— **1890 用例全绿**（43 skipped；较上一轮
  +3，即 test_materials_atomic 三断言）。
- 设计闸门：`validate-wf-design.py` 定义/消费点 100%/100%、二值 93/93、三档 14/14、输入摘要 4/4；
  `check-doc-refs.py` 0 problems；`validate-skills.sh` 25 skills 全过。
- 发行树：`build-wf-release.py --version 0.0.1` 重建后 `--verify` 字节复现通过（74 assets）。
- 全量 runner：见 §5。

## 5. 全量 runner 结果

第一轮修正后：`bash scripts/tests/wf_runtime/full/run_all.sh --full`：执行单元 144（套件 59 + 流程/extra 5 + repro 80），
**fail=0 / bad=0 / repro_fail=0**，GATE-OK（run_id=1795532381163-3596757-ccec9c60957a，清理/证据/摘要一致）。
GREEN 段含材料身份相关 repro（review-identity-c6、review-count-reject、review-copies-installed 等）全绿。

第二轮修正后：T0 **1892 全绿**（43 skipped；较第一轮 +2 = 混合轮槽位提示回归锁 + rename 前像回归锁）；
设计闸门/doc-refs/skills 全绿；发行树重建后 `--verify` 字节复现通过。全量 runner 复跑结果见 §7。

## 6. 第二轮独立复审（2026-11-25）：台账 17 条全部核实为"落盘且正确修复"

两个全新干净子代理（机制面/指引面，只读）逐条核实：A-1…A-4、B-F1…B-F13 全部成立且修复正确；
A-1 由机制面代理另做**对抗变体实跑**（带内容的 staging 注入后抛错——清理与重跑语义仍成立，超出仓库
测试直接覆盖面）；A-2 全仓 AST 死字符串扫描归零；A-3 三方一致（status/decide/check_next_hint 同构）
且非混合轮文案逐字不变；A-4 指向的两个 facts 字段实存。B-F8 裁定经测试正文核实成立
（`StatusWindowTest` 确断言 skill 含窗口数字）。第一轮 F1a–F8 五个关键判据位抽查完好。
§1.1 四要点独立抽查全部准确，"19/20、唯一失准在实现面且已清除"结论成立。

**第二轮新发现（7 条，已全部处置）**：

| 编号 | 判定 | 处置 |
|---|---|---|
| M-N1（低，本轮引入） | review.py:1622 `except Exception:` 下的 `anchor = None` 被本轮 A-3 编辑改出 12 空格缩进（可编译、行为不变，但埋混层隐患） | dedent 回 8 空格 |
| M-N2（低中，本轮引入） | A-3 的新文案（混合轮 restored 槽位 reason）无任何测试锁定——同页分叉的回归无防线 | 新增 `test_mixed_round_slot_hint_matches_round_exit`：混合轮 status_of_round 断言 restored 槽 reason 含"混合基线"、不含"可直接判定" |
| M-N3（低，既有实现面） | rename 的 `before_digests` 语义分叉：首跑前像核对取 new_paths（target，改名前不存在 ⇒ 填了必误拒），续做分支 `_resume_decision_rename` 取 source——两侧矛盾 | **统一到 source 侧**（与续做分支一致，protect 的是"批准→改名之间源文件被改"的真实风险面）：`validate_changes` 首跑核对 rename 改核 old_paths；help 同步"rename 与续做分支同核 source"；新增 rename 前像回归锁（匹配放行/失配拒）。r84 直调 `_apply_change` 不经此段，不受影响 |
| M-N4（信息） | `after_digests` 输入值被静默忽略（无消费点） | help 补"输入值不参与校验" |
| M-N5（信息） | status_of_round 每次调用算两遍材料身份（本轮提亮 + 返回点各一次） | 返回点复用 `current_materials_identity`（单次计算） |
| G-N1（P3，残缺口） | wf-bootstrap 与 wf-spec-update 的「不做」段同样缺"这不算违反"正例（B-F7 残留面） | 两个 skill 各补两句正例（内容取自各 skill 份内事） |
| G-N2（P3，本批引入） | session-flow「运行约定」第 6 条仍指"finish/continue 的清单"——B-F1 删 finish 清单后指针半失效 | 改指 `wf-continue`「证据文件纪律」 |
| G-N3（P3，本批暴露） | help `spec-update --changes` 的 args 行仍写四字段，与补齐后的七字段 inputs 形成同条目第二个不全清单 | args 行改"字段形状见下方 inputs" |
| G-N4（P3，观察项） | 标准变更段未写明人裁面（删除/合并/降级）结论按人答复转录（by=human；ask_always 不拦人的答复，judgments.py:277-281） | 句内补"人裁面的结论由人给，条目按人的答复转录（by=human）" |

## 7. 第二轮修正后的全量 runner

`bash scripts/tests/wf_runtime/full/run_all.sh --full` 复跑：执行单元 144（套件 59 + 流程/extra 5 + repro 80），
**fail=0 / bad=0 / repro_fail=0**，GATE-OK（run_id=1795536240032-3788666-a99cfdb0df44）。rename 前像语义
统一后 r84（直调 `_apply_change`，不经首跑前像段）不受影响、全绿。

## 8. 第三轮收敛审查（2026-11-25）：零新发现，循环 break

两个全新干净子代理（机制面/指引面，只读）对第二轮 9 条修复逐条核实**全部落盘且正确**：

- 机制面：`except` 缩进经 `cat -A` 核实恢复 8 空格（四模块 AST 编译全过）；混合轮槽位提示回归锁真实锁定新文案
  （断言含"混合基线"、不含"可直接判定"）；rename 前像与 `_resume_decision_rename` 同核 source，help 同步，
  回归锁实跑通过，r84 单跑 9 PASS（直调 `_apply_change` 不经首跑前像段，`validate_changes` 仅 2 调用方、
  测试面无旧 target 侧语义依赖）；`current_materials_identity` 复用判定为**纯等价变换且语义更强**（函数只读，
  单次调用内 manifest 不可能变化）；两个 skill 新正例与禁令无矛盾；发行树 15 个 payload 文件与源码字节一致。
  T0 1892 实跑全绿。
- 指引面：G-N1…G-N4 落盘正确且与实现互证（by=human 豁免与 judgments.py 注释逐字对应）；八个语义轴
  （证据纪律/决定转录/交人触发点/报告契约/--round/材料身份/标准变更/release_allowed）跨 13 skill + 6 流程文档
  全部口径一致；残留旧口径 rg 扫描零命中（"五类清单"仅剩否定句与 K6 分类学、"审查环境不可用"误指零残留、
  "先确认一下"零命中、平台区分零命中）；指针句逐条可解析（judgments 8 条 guidance 指针、facts 字段、
  错误码抽查全实存）；六个 help 命令与实现抽查一致；traffic_monitor 四会话历史卡点最后一遍核对全部封死。
- **两条信息级观察（自我证伪后判非缺陷，登记不处置）**：
  ① `--round` 缺省行为的 help 措辞三分叉（"当前轮"/"最大发起轮"/"最新已发起轮"）——四处实现完全同构
  （均 max(launches)），无行为差异，skill 已统一要求显式传 `--round`；
  ② wf-spec-update 描述行含"拆分"而 operation 枚举无 split——"拆分"是能力级描述（update+add 成组可实现），
  误写会得到明确拒绝，不构成静默错写面。

**收敛判定（break 条件）**：独立审查不再发现新问题 ✓；前两轮全部发现（A-1…A-4、B-F1…B-F13、
M-N1…M-N5、G-N1…G-N4）修复完整且经第三轮复核无回归 ✓；不偏移核心要点（§1.1 判据最终符合性结论
"符合"：进机制/留指引分工、收敛动作、单定义位、否定句带正例、未新增 skill/层级/判断步骤、全平台安装
无平台区分残留）✓。

## 9. 第四轮独立复审（2026-11-25，本轮）

> 输入：三个**全新干净子代理**（机制面 / 指引面 / dogfood 会话复演；只读、不用 MCP/网络），
> 加主会话机械核对。证据边界：`/tmp/wf-find-a.md`、`/tmp/wf-find-b.md`、
> `~/.zcode/cli/log/zcode-2026-11-08.jsonl` 仍不存在；复演只依据 `/tmp/traffic_monitor_1..4.md`
> （未读原始 JSONL）。三份报告的结论均先按 file:line 复核再采信。

### 9.1 对既有台账的复核

A-1…A-4、M-N1…M-N5、B-F1…B-F13、G-N1…G-N4 共 26 条：三份独立报告逐条核实**全部落盘且正确**
（A-1 另做"真实 write_materials 写满 staging 后抛错"的对抗复验；A-3 三方实跑一致；rename 前像
双向锁实跑通过；发行树 74 资产字节一致）。§1.1 八要点：6 项准确，2 项局部偏差（G-1/G-2）。

### 9.2 本轮新发现与处置（均已修正）

| 编号 | 判定（决定性证据） | 处置 |
|---|---|---|
| M-1 | **P2 成立（本批引入）**：`_session_like` 把入参来源无条件写成 `source=auto`，`cmd_enable` 的显式 `provider=wf` 信封由此在启用前置里被当成自动身份模式放行（HEAD `WF_OK`；cf09db12^ 同输入为 `WF_IDENTITY_UNRESOLVED`），fail-open 且 facts 自述面也错 | `_session_like` 增 `source` 参数；新增 `_enable_guard_session(explicit, base)` 唯一构造（显式=explicit、附件/派生=auto）；`test_enable_guards_source.py` 3 断言锁显式 wf 拒/auto 放行/显式 host 来源 |
| M-2 | **P2 成立**：`gates.debug_pending` 把任意 `choice`（如 plan-q 答复）和尚未到场的倍数都当裁定，一条 `debug-ruling-<vid>-99` 即可静音归档门禁；通用 `task-approve` 入账原样 append 保留 subject | 门禁只认 `decisions.domain("debug_ruling")` 且只按**已到场倍数**取覆盖上界；`task-approve` 对 `debug-ruling-`/`debug-declaration:` 前缀整批拒绝（改走 `task-check --decision`）；新增 4 条回归（门禁 3 + 入账 1） |
| M-3 | **P2 成立**：`materials_identity_state.present` 用 `os.listdir` 把 `check-logs/` 等子目录也算"有材料"；按官方出口②删内容文件+manifest 后重跑会落进 legacy 采纳，产出缺 diff/prd/check/tests 的半包并报成功；缺件旧包也会被 legacy 采纳 | `present` 只数文件；无 manifest 的旧包按 `MATERIAL_FILES` 必需集核完整性，缺件按未物化处理并在 review-context 给"删全部内容重建/放回完整备份"两个出口（不静默删证据）；只剩子目录时清掉重建；新增 3 条回归并同步旧的 legacy 夹具为完整包 |
| M-4 | **P3 成立**：混合轮 + 另一槽位有 done 待导入报告时，槽位 reason 说"处置见轮级 next_"，轮级 next_ 却只报"先 review-import"（A-3 要消的"同一页两句话"在该分支重现） | 轮级 next_ 先判"无材料身份/混合/材料失配"，待导入只作附加说明（"导入不改变上述基线问题"）；无材料身份时槽位 reason 改"先按轮级 next_ 恢复材料"；新增 `test_review_status_next.py` 2 断言 |
| M-5 | **P3 成立**：材料目录整体消失而报告已导入时，`round_materials_basis` 因 `current_identity is None` 跳过全部条目，status 回落"材料未齐，等 reviewer 产出"（永远等不到；decide 侧按 round has none 拒绝） | `round_materials_basis` 把"有绑定身份、当前无身份"计为 live/restored 不匹配；status 单列"材料目录已不在"出口（放回原字节/开新一轮）；basis 回归 2 条 + next_ 回归 2 条 |
| M-6 | **P3 成立**：实现稿仍写"删除/停用取 old_paths，其余取 new_paths"，与 M-N3 后的实现/help 相反 | 实现稿该句改为"删除/停用/rename 取 old_paths" |
| G-1 | **P2 成立**：设计稿人签清单的 manual 项（`kind=manual` 须人判 `content_digest`）在 13 skill/6 流程/PRD 模板零落点，AI 只能从 check.py 注释猜；wf-finish 把"本机验不了"只导向 `verify resolve --kind narrow`（改变承诺） | `wf-continue` 的 Check 行补整句（choice/subject/content_digest 来源与 `not_run` 后果）；`wf-finish` 补一句判断 + 指针；`task-check` help 的 args 与 inputs 补 manual 形状；`test_guidance_contracts` 4 断言锁落点 |
| G-2 | **P3 成立**：wf-finish"首任务收工必确认一次"是规定动作，但 `sampling confirm` 是唯一写入路径且 13 skill/6 流程零命中（不写则 `history_max` 永远为空、预览持续提示） | wf-finish 规模条补 `wf sampling confirm --task <id>` 与其作用 |
| G-3 | **P3 成立**：wf-continue 的审查链 `review-import`/`review-decide` 均未写 `--round`，与 wf-review-action"轮次必须显式给"相反（恢复较早一轮会导错） | wf-continue 三条命令补 `--round <n>` 并加一句指针 |
| G-4 | **P3 成立**：help 把 `task-abandon --disposition` 标"可选"，实现在 `preview.uncommitted` 非空时强制；该命令无 inputs/无 draft，而 session-flow 声明"形状以 help 的 inputs 为准" | help 改为"有未提交改动时必填"并补 `inputs.changes[{object, decision_ref, reason}]`；wf-continue 放弃行同批标注 |
| N-1 | **P3 成立**：`wf.py --help`/`-h` 落进 `unknown subcommand`（dogfood 会话 4 第一条命令即此），AI 先吃一次失败再改用 `wf.py help` | `dispatch` 把 `--help`/`-h` 别名到 `help`（带命令名仍可用）；`test_help_contract` 新增 1 条 |
| N-3 | **P3 成立**：wf-finish 出口把 `WF_SEMANTIC_DECISION` 单义化为"缺审查/复核不合规"，同码还来自知识处置缺失、复盘未覆盖（dogfood 会话 4 因此先往审查方向排查） | wf-finish 出口改为"按 facts 判断来源（审查/复核、知识处置、复盘等），先按 facts 补齐" |
| N-4 | **P3 成立（措辞）**：wf-finish 只写"本任务声称修框架时按独立维护任务处理"，未列"保持现场/回源"两条合法去向（人明确不许新开任务时 AI 找不到出口） | 改为"按 `wf-continue` 的 vendor 段定去向（回源仓库立项/另开任务/保持现场），不混入业务提交" |
| N-5 | **P3 成立（体验）**：wf-review-action 对采纳建议只写"逐条判断 → 重跑 Check + 发新轮"，没有"多条合成一批"的收敛句；dogfood 8 轮中 3 轮是单条"修完再审" | pass 之后补一句：多条采纳合成一批，一次重查、一轮审查；逐条判断的是"是否采纳" |
| D-baseline | **P2 成立（本轮主会话发现）**：`wf-bootstrap` 步骤 3 仍让 AI 用 `baseline-apply --proposal <path>`，而实现要求提案自带 `approval.object_digest=提案摘要`、且注释明说"提案是机械结构，不该由人/模型手写"；`wf help baseline-apply` 的示例同样指向旧路径（会话 1 的 `task-approve` 摘要失败同类） | 步骤 3 改为"规划批准 → 写工作树 → `--files --preview` 取 `proposal_digest` → 人批准该摘要 → `--files --decision` 成组落盘"；help 示例改为 `--files ... --preview`，`--proposal` 标注"必须自带 approval 且 object_digest=提案摘要" |

### 9.3 驳回与观察（不处置）

- **N-2（archive --draft 的 object_digest 留空）**：`_load_decision` 明写"archive/stop 可留空"，
  草稿已含该键；会话 1 的失败是"字段缺失"，不是"值为空"。不判缺陷。
- **§1.1 人签清单的生命周期项**：返工/替换/异常归档由 §5.6 定义为"人明确决定"，归属裁决在 §4.2；
  §1.1 清单未逐项列出。判为**边界观察**：baseline 批准在 `decisions.DOMAINS` 归入 `plan_approval`
  （被"规划批准"覆盖），其余由 §1.2 转录纪律与 skill 路由要求人给决定。本轮不改，登记待人裁是否补入清单。
- **`--main-review-draft` 落盘**：旗标不在 `--draft` 名下、文档未称只读；沿用第三轮观察。
- **`review-context` 的 `materials_check.state/fixed` 报进入态**：由测试注释固化（有意），
  且无机制消费者（指引指向 `review-status` 的 `materials.state`）；不列缺陷。
- **`_enable_guards` 返回的 `platforms` 无消费者**、`materials.staging-*` 只在未物化分支清理：
  死返回/垃圾目录，无机制后果；登记不处置。

### 9.4 §1.1 准确性结论（本轮）

- 判据句两问、可计算≠同一结论、指引就地、正面授权/负向禁令+正例、作决定与转录、
  `facts`/`next`/`exits`/`--draft`：**准确**。
- "指引必须写到收敛动作"：G-2 已补 `wf sampling confirm`；**准确**。
- "人签封闭清单"：manual 项落点 G-1 已补；baseline 批准归 `plan_approval`；生命周期项见观察。
  结论：**准确（含一处边界观察）**。
- 不新增 skill/层级/判断步骤；全平台安装零残留（`--platform`/`add_platforms` 在 skills/流程/cli 零命中）。

### 9.5 验证实况

- T0：`python3 -m unittest discover -s scripts/tests -t .`：**1914 用例 OK**（43 skipped；较上轮 +22）。
- 全量 runner：144 单元（59 套件 + 5 流程 + 80 repro），**fail=0 / bad=0 / repro_fail=0**，GATE-OK
  （run_id=1795577354459-144023-f2379bc55681，第五轮修正后复跑）。
- 设计闸门：`validate-wf-design.py` 定义/消费 100%/100%、二值 93/93、三档 14/14、输入摘要 4/4；
  `check-doc-refs.py` 0 problems；`validate-skills.sh` 25 skills 全过。
- 发行树：`build-wf-release.py --version 0.0.1` 重建后 `--verify` 字节复现（74 assets）；
  `--verify-token-parity` OK。
- 工作树：本轮改动未提交（用户未要求提交）。

### 9.6 第五轮独立复审与修正

两个全新干净子代理（机制面/指引面，只读）复核 §9.2 的 15 条修正：
- 机制面：14/15 落盘正确；**R5-M-1（P2）** restored-only + 材料目录消失时槽位仍说"可直接判定"，
  与轮级 next_ 相反且 decide 必拒；**R5-M-2（P3）** `task-check` 的 `check_next_hint` 在
  "材料目录不在 + mixed"时给出的 `--restore` 首选动作同轮不可执行。
- 指引面：9 项中 7 项正确；**R5-G-1（P2）** 发行树在最后一次文案修改后未重建（`--verify` 失败）；
  **R5-G-2（P2）** `wf help task-check` 仍写"subject 含 id"且 `inputs.manual` 缺
  `object_digest`/`plan_version`（照 help 写会静默 `not_run`）；**R5-G-3（P3）** `cli.py` 一处注释
  把 `content_digest` 写成 `object_digest`；**R5-G-4（P3）** `sampling confirm` 缺"人给原话 `--quote`"
  的指引；**R5-G-5（P3）** abandon `decision_ref` 与 runs 同名两义且无门禁消费者。

修正（同批，均未新增机制层级/字段）：
| 编号 | 处置 |
|---|---|
| R5-M-1 | `status_of_round` 的 restored 非 mixed 分支与"材料身份已变"措辞都按 `current_materials_identity is None` 分流：统一说"材料目录已不在/同轮无法恢复，按轮级 next_ 恢复材料或开新一轮"；新增回归 2 条（restored-only 无材料、restored+缺槽位） |
| R5-M-2 | `check_next_hint` 在 `_materials_current_missing and (stale or mixed)` 时先给"重跑 review-context 重建材料/开新一轮"，不再把 `--restore` 作为首选；定向 `test_check_next_route` 13 例全绿 |
| R5-G-1 | 重建发行树，`--verify` 74 assets 字节复现 |
| R5-G-2 | help args/inputs 的 manual 形状补 `object_digest`（或 `plan_version`）、"以整词"；`baseline-apply` inputs 补 `--decision`（object_digest=proposal_digest）；`GuidanceLandingTest` 锁落点 |
| R5-G-3 | status 的 delivery 注释改为 `content_digest` |
| R5-G-4 | wf-finish 规模条补"人给原话写入 `--quote`"；help `sampling --quote` 覆盖 confirm |
| R5-G-5 | abandon inputs 的 `decision_ref` 标注"字符串引用（不是 Decision 对象）；随处置留痕，不参与门禁" |
| 观察项同批收口 | 无 launch（round 0）→ 先 `review-launch`（不再"等 reviewer"）；restored + 槽位未到 → 等齐后再判定（不再"可直接判定"）；机制稿 §1.3 的覆盖上界补"已到场"；`_enable_guard_session` docstring 去掉"唯一构造"的过强表述 |

### 9.7 第六轮独立复审与修正

两个全新干净子代理（机制面/指引面）复核 §9.2 + §9.6：

- **机制面**：R5-M-1 / R5-M-2 / 观察项落盘正确；新发现 **R6-M-1（P2）+ R6-M-2…M-5（P3）**，全部是
  `review-status` 的"承诺了 decide 必拒的动作"或分支顺序问题（非本轮引入）：
  | 编号 | 事实 | 处置 |
  |---|---|---|
  | R6-M-1 | 材料 drift + live 报告：status 说"下一步 review-decide"，真 `review.decide` 先撞 drift 门禁（`review.py:4873`）；同态 `check_next_hint` 有 drift 分支 | status 补 drift 一档（restored-only 放行；live 给"放回原字节/重建后重写/开新一轮"），与 `check_next_hint` 同源 |
  | R6-M-2 | restored + 槽位未到：槽位 reason 仍"可直接判定"，decide 按 single reviewer 必拒 | 槽位改"该记录可直接判定；若无其他槽位未到，可直接 review-decide，否则等齐后再判定" |
  | R6-M-3 | restored-only + 材料目录不在：status 只给"开新一轮"，漏了"重建材料后直接 review-decide"（`materials_restored=True` 实测放行、drift 门禁因 history_round 放行） | restored-only 分支改"重建材料后直接 review-decide（还原记录仍有效）；有原字节也可放回" |
  | R6-M-4 | 已判定轮被资格/材料分支遮蔽：acceptance 已签且 verdict=pass 仍报"人数不合格"；已判定 + 材料不在只劝"开新一轮" | 已判定判定移到材料/资格分支之前；已判轮直接报 verdict 与"改结论开新一轮" |
  | R6-M-5 | `required=0` 混同"未发起"与"旧 launch 没有 slots"：status 让先 launch，hint 说不要重新 launch | 判据改 `facts["round"] < 1`；旧 launch 无 slots 单列"已发起但未声明槽位" |
- **指引面**：R5-G-1…G-5 与观察项落盘正确；新发现 **R6-G-1…G-3（P3）**：
  | 编号 | 事实 | 处置 |
  |---|---|---|
  | R6-G-1 | `wf help sampling` 把 `--attestation` 标"evaluate 可选"，实际 evaluate/reviewed 必填；`--quote` 归属 reviewed 但该分支不读 | help 改"evaluate/reviewed：人确认文件（必填）"、"confirm：人的确认原文"；`sampling pick` 的 next_ 改指 `sampling evaluate --file --attestation` |
  | R6-G-2 | `plan_version` 是未登记的决定字段，正确值是等价链归一后的版本，只读入口不暴露；填错时被报成"人没给决定" | `status --json` 增 `facts.task.plan_version`（`normalized_plan_version`）；help 与 `wf-continue` 指明来源；`check.py` 的 manual 失配摘要改 `content_digest mismatch` |
  | R6-G-3 | `--disposition` 形态错误的回显示例用 `path/action`，门禁只读 `object` | 示例改为 `{"changes": [{"object": "<路径或 glob>", "reason": "…"}]}` |
- 新增回归：`test_review_status_next` 扩到 9 例（无 launch、旧 launch 无 slots、drift+live、restored-only 无材料、
  已判定+材料不在、restored+缺槽位、mixed+待导入等）；`test_guidance_contracts` 扩到 12 例（sampling 两旗标、
  manual `plan_version` 来源）。
- 验证：T0 **1920 用例 OK**（43 skipped）；全量 runner 144 单元 fail=0/GATE-OK（run_id=1795579272801-283022-fb83baf66fe1）；发行树 `--verify` 74 assets 字节复现；
  设计闸门 100%/100%、93/93、14/14、4/4；doc-refs 0；skills 25。

### 9.8 第七轮独立复审与修正

两个全新干净子代理（机制面/指引面）复核第六轮修正：

- **机制面**：R6-M-1…M-5 落盘正确；新发现 **R7-M-5（P2）+ R7-M-1…M-4（P3）**：
  | 编号 | 事实 | 处置 |
  |---|---|---|
  | R7-M-5 / R7-G-1 | `check._decision_covers` 传 raw `plan.version`，而 `status`/help/`wf-continue` 给等价链归一版本：机械修订后照文档填 `plan_version` 的 manual 决定被拒且报成"人没给决定" | `check.py` 的 manual/直接验收调用点改用 `tasks.normalized_plan_version(task)`；新增"机械修订后仍覆盖"回归（`test_review5_mechanisms`） |
  | R7-M-1 | drift 豁免用"有 restored 条目"代理 decide 的 `history_round`（全部 restored 或无身份）：drift+restored+live 被误豁免、drift+restored 无身份被误拒；`check_next_hint` 不判 | 抽 `review.round_is_history()` 唯一实现；decide/status/`check_next_hint` 共用；status 的 drift 分支按"有 pending 或非 history"分流，history+waiting 追加"等齐再判定" |
  | R7-M-2 | result-first 后 fail 轮"同轮重判"未提材料前置：drift/材料不在时同轮 decide 必拒 | fail 分支按 `materials_state`/`current_identity` 追加"先放回原字节/恢复材料，否则只能开新一轮" |
  | R7-M-3 | restored-only + 材料不在：文案"重建后直接 decide"忽略未到槽位/待导入，decide 必拒；新测试只断言文案 | 该分支按 `pending_import`/`waiting` 追加"先导入/等齐，再 review-decide"；测试改为断言"重建材料 + review-decide"且不推"开新一轮" |
  | R7-M-4 | 只丢 manifest、材料文件仍在：状态是 legacy，文案却说"目录已不在"并推"开新一轮" | 按 `materials.state` 分流：legacy/legacy_adopted 说"采纳现场字节（内容未变则身份不变，原报告继续有效）"；`unmaterialized` 但 `present` 非空说"材料包不完整，删全部重建"；status facts 增 `materials.present` |
- **指引面**：R6-G-1/G-3 正确；R6-G-2 取值方向错（同 R7-M-5）；新发现 **R7-G-2（P3）+ R7-G-3（P3）**：
  | 编号 | 事实 | 处置 |
  |---|---|---|
  | R7-G-2 | `review-context`/`review-decide` help 写"`--round` 缺省＝当前轮"，实现与另两处 help/skill 都是"最大已发起轮" | 两处 help 改"缺省取最大已发起轮（恢复较早一轮时显式给）" |
  | R7-G-3 | `sampling confirm`/`reviewed` 的人原话原样入库，help 却写"遮罩摘要入库"；`authorize` 对同类 quote 有 mask+截断 | `authorize.mask_quote()` 成为唯一实现（mask+500 截断）；`scale.record`/`sampling.mark_reviewed` 写入前调用；`test_acceptance_sampling.QuoteMaskTest` 3 断言 |
- 新增回归：`test_review_status_next` 10 例（+ legacy 只丢 manifest）、`test_materials_identity.round_is_history`、`test_review5_mechanisms` 机械修订归一、`test_acceptance_sampling` quote mask 3 例。
- 验证：T0 **1926 用例 OK**（43 skipped）；全量 runner 144 单元 fail=0/GATE-OK（run_id=1795581205050-437568-585bc12f4136）；发行树 `--verify` 74 assets；设计闸门 100%/100%、93/93、14/14、4/4；doc-refs 0；skills 25。

### 9.9 第八轮独立复审与修正

两个全新干净子代理（机制面/指引面）复核第七轮修正：

- **机制面**：R7-M-1…M-5 落盘正确；新发现 **R8-M-1（P2）+ R8-M-2…M-7（P3）**：
  | 编号 | 事实（决定性证据） | 处置 |
  |---|---|---|
  | R8-M-1 | "材料字节不可还原、必须重写报告/开新一轮"被实测证伪：删 `materials/` 或删内容+manifest 后重跑 `review-context`，身份**逐字节复现**（`write_materials` 无时间戳/随机，Check 未重跑），`review-decide` 仍 pass；只有同锚点重跑 Check 换 id 才会变 | 统一修正 status/hint/槽位文案：重建即恢复同一身份、原报告继续有效；"重写/开新一轮"限定为 Check 换 id 或交付面/规格已变；新增"重建复现身份"回归 |
  | R8-M-2 | `status_of_round` 槽位仍用 `identity is None`/`mixed` 代理，restored+无材料说"同轮无法恢复"、drift+restored+live 说"可直接 review-decide"，均与轮级相反 | 槽位按 `materials_state` + `round_is_history` 分流（与轮级同源）；测试同步 |
  | R8-M-3 | `check_next_hint` 的 drift+history 分支不判槽位：drift+restored+槽位未到/待导入仍说"可直接 review-decide"（decide 按 single reviewer 拒） | 该分支按 `missing|writing|staged_unknown` 追加"等齐后再判定" |
  | R8-M-4 | drift+非 history 在零导入时说"且有 live 报告"（前提为假），并推"开新一轮"（重建后同轮可继续） | 区分有无导入记录：零导入只说"重建后让 reviewer 继续/写报告" |
  | R8-M-5 | legacy（只丢 manifest、五文件齐）槽位/hint 仍说"目录已不在/同轮无法恢复"，与轮级"采纳现场字节、原报告有效"相反 | 槽位/hint 读 `materials.state`：legacy/legacy_adopted 说采纳；只有真无文件才算不在 |
  | R8-M-6 | legacy 采纳时 manifest 用 `current_check_id`；同锚点重跑 Check（新 id）会把旧报告身份改掉，与"同内容重验报告仍有效"冲突 | 采纳优先沿用导入记录的 `anchor.check_id`（唯一时），否则 current |
  | R8-M-7 | 资格不足（实施 CLI 重叠）时 hint 仍把 AI 送进"导入→判定"（decide 同因拒） | hint 先算 implementation/reviewers 重叠并给"换异种 reviewer/补报告" |
- **指引面**：R7-G-1/G-2 正确；R7-G-3 只完成顶层 quote，`attestation` 子对象仍存原文；新发现 **R8-G-1（P2）+ R8-G-2/G-3（P3）**：
  | 编号 | 事实 | 处置 |
  |---|---|---|
  | R8-G-1 | 空 `verification_ids` 的直接验收决定要求"归一规划版本 + `content_digest`"两者同时满足，但机制稿 §3.5、实现稿 §2.3、设计稿 §1.1 清单、13 skill/6 流程都没有定义；照唯一来源写必 `pending` 且无字段归因 | 机制稿 §3.5/实现稿 §2.3 补归一版本 + `content_digest`；设计稿 §1.1 人签清单把"空 verification_ids 的验收结论"并入 manual 同类；`wf-continue` Check 行、`wf-finish`、`task-check` help（args + `acceptance-direct` inputs）补落点；`test_guidance_contracts` 锁 |
  | R8-G-2 | `attestation.stamp` 的 `quote` 原样入库，绕过 R7-G-3 的遮罩（同一 task.json 顶层已遮、attestation 子对象明文） | `stamp` 改 `authorize.mask_quote`；`test_acceptance_sampling` 断言整条记录无明文 |
  | R8-G-3 | `sampling evaluate` 把 `attestation` 放进 `evaluations["__attestation__"]` 后被 `record_result` 丢弃，人确认摘要未入库 | `record_result` 写 `state["evaluate_attestation"]`；新增回归 |
- 新增回归：`test_review_status_next` 11 例、`test_materials_atomic` 重建身份、`test_review5_mechanisms` 机械修订、`test_acceptance_sampling` 8 例（quote/attestation/evaluate）、`test_guidance_contracts` 13 例。
- 验证：T0 **1930 用例 OK**（43 skipped，干净一次）；全量 runner 144 单元 fail=0/GATE-OK（run_id=1795584145380-682724-77ce52296be5）；发行树 `--verify` 74 assets；设计闸门 100%/100%、93/93、14/14、4/4（输入摘要已随设计稿更新）；doc-refs 0；skills 25。
- 已知测试脆弱点：全量 T0 偶发 `test_template_cache.CheckpointTest` 失败（并行/资源，单跑 36 例 OK，与本轮改动无交集），登记为既有测试隔离问题。

### 9.10 第九轮独立复审与修正

两个全新干净子代理复核第八轮修正：

- **机制面**：R8-M-1/M-3/M-4/M-6 机制正确；R8-M-2/M-5/M-7 只部分落盘；新发现
  **R9-M-1（P2）** drift+restored+live 时槽位仍说"可直接 review-decide"（轮级说会被拒）；
  **R9-M-3（P2）** legacy 采纳文案"原报告继续有效"未限定"现场字节未改过"（改过时 decide 必拒）；
  以及 R9-M-2/M-4/M-5/M-6/M-7/M-8/M-9（P3，槽位/hint 的边缘态）。
- **指引面**：R8-G-1/G-2/G-3 方向正确；新发现 **R9-G-1（P2 档）** review 三类人确认记录与
  `acceptance_echo` 仍存/回显原话；R9-G-2/G-3/G-4/G-5（P3）：`evaluate_attestation` 未登记、
  wf-continue 把验收与重复调试的 choice 合并、manual/direct 版本绑定表述不对称、
  直接验收缺 `content_digest` 的文档写 `not_run` 而实现是 `pending` 且无归因。

修正（同批）：
| 编号 | 处置 |
|---|---|
| R9-M-1 / R9-M-2 | `status_of_round` 在槽位循环前算 `material_state` + `round_is_history`；restored 槽在 drift+非历史轮改"drift 阻断整轮，处置见轮级 next_"；legacy/partial 槽位改"采纳现场字节/包不完整"；新增 drift+restored+live、legacy 槽位回归 |
| R9-M-3 / R9-M-8 | legacy/采纳文案加"现场字节未改过时身份会复现；采纳沿用导入记录的被审 check_id；字节改过才需重写/新轮"；slot/status/hint 同批 |
| R9-M-4 | drift+history+waiting 首句改"还不能判定——等齐后再 review-decide" |
| R9-M-7 | hint 增 current-missing + history（仅 restored）分支：重建→（待导入先导入/等齐）→直接 decide |
| R9-M-9 | restored 分支在 `main_review_ready=false` 时先说"先生成主会话复核"，不再直接判 |
| R9-G-1 | `single_reviewer_acceptance`/`gap_acceptance`/`merge_acceptances`/`acceptance_echo`/`quote_summary` 全部走 `authorize.mask_quote`；新增回归 |
| R9-G-2 | 机制稿抽样字段闭集与 `frozen()` docstring 登记 `evaluate_attestation` |
| R9-G-3 | wf-continue 拆句：验收 `choice=passed|failed`；重复调试声明无 choice、裁定 `同一问题|不同问题` |
| R9-G-4 | 设计稿 manual/direct 两项统一"归一 `plan_version` 或批准对象摘要之一"；机制稿 §3.5 同批 |
| R9-G-5 | 文档改"直接验收缺 digest → `pending`"；`_acceptance_results` 的 pending 分支补 `stale_decision` 字段级事实 |
- 登记未修（P3 边缘态，非核心流程）：R9-M-5（drift/mixed 分支未先报资格重叠/人数）、R9-M-6（旧 launch 无 slots 时 status 用派生槽位、decide 用声明槽位，资格提示不一致）。两项均为既定边界态的文案精度，不改变门禁与判定，登记待人裁。
- 验证：T0 **1934 用例 OK**（43 skipped）；全量 runner 144 单元 fail=0/GATE-OK（run_id=1795586446322-835424-f2f20e46615f）；发行树 `--verify` 74 assets；设计闸门 100%/100%、93/93、14/14、4/4；doc-refs 0；skills 25。

### 9.11 第十轮独立复审与收敛判定

两个全新干净子代理（机制面/指引面）做最终收敛复核，范围限定 P2 修复 + 是否引入新的 P0–P2：

- **机制面**：R9-M-1（drift+restored+live 槽位说"drift 阻断"）、R9-M-3（legacy 采纳限定"现场字节未改过"）、R8-M-1（重建复现身份）、R8-M-2/M-5（槽位/轮级/hint 同源）全部成立，且在真实发行树部署的项目上端到端复现；`scripts/tests/wf_review` 545 OK、定向 162 OK、发行树 74 assets 字节复现。**无新的 P0–P2**，结论"可 break"。
- **指引面**：R9-G-1（review 人确认记录与回显遮罩）、R8-G-1（直接验收归一版本 + content_digest 六处同源、照文档可 passed、缺 digest 带 stale_decision）、R9-G-3/G-4（choice 拆分、版本绑定对称）、R8-G-2/G-3（attestation 遮罩、evaluate_attestation 入库并登记）全部成立；§1.1 八要点**全部仍成立、无新偏移**。**无新的 P0–P2**，结论"可 break"。
- **终审后补的两处 P3**（不改门禁）：① `wf-continue` 句末"缺该值该项 `pending`"按 manual/direct 拆开（manual `not_run`、直接验收 `pending`）；② 机制稿 §3.5 manual 句补"决定须绑定归一规划版本（或批准对象摘要）与当前 `content_digest`"（唯一来源完备性）。
- **登记不修的 P3/边界**（终审列出，均不改变门禁/判定，不阻塞收敛）：legacy 槽位缺"槽位未到先等齐"一句；drift 全 live 时 `material_ready` 仍表"到达"；换 Check id + 删材料后重建的 material_stale 未提示"删 manifest 采纳"恢复；review-status drift 零导入仍说"原报告继续有效"；既有明文记录不回写；验收字段形状 7 处重复的漂移风险；`wf-review` 重建复现未含"check 日志仍在"前提；`wf-continue` 裸否定微项。
- **收敛判定**：break 条件按本任务的可操作口径成立——**无新的 P0–P2 + 已有 P2 修复完整 + 不偏移核心要点**；P3 边缘态已逐条登记，不属于核心流程/门禁/安全缺陷。工作树未提交（HEAD `042b9051` + 未提交修正），按用户要求不提交。
- 最终验证：T0 **1934 用例 OK**（43 skipped）；全量 runner 144 单元 fail=0/GATE-OK（run_id=1795586446322-835424-f2f20e46615f）；发行树 `--verify` 74 assets；设计闸门 100%/100%、93/93、14/14、4/4（输入摘要 4/4）；doc-refs 0；skills 25。
