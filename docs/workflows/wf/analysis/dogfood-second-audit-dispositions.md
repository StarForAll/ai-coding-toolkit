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
