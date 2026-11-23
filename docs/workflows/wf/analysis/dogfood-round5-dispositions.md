# dogfood 五轮：a/b 报告核验与处置台账（2026-11-23）

> 输入：`/tmp/traffic_monitor_1..4.md`（traffic_monitor 实测四会话）、`/tmp/wf-find-a.md`、
> `/tmp/wf-find-b.md`；参考（上一轮收口、部分已陈旧）`/tmp/wf-find-c.md`、`/tmp/wf-find-d.md`。
> 判据：**每条指控由主会话对照 `docs/workflows/wf/payload/**` 源码与 `git tag -l` 独立核验**，
> 不采信报告结论。本文件按轮次收口惯例逐项留痕，不留未标注条目。

## 1. 成立并已收口

| 编号 | 事实（决定性证据） | 处置 |
|---|---|---|
| a-1 | 三方匹配内部键 `(base, rel)`，但 `--keep/--restore`、升级预览、`--export-deviations` 清单、安装记录 `decisions` 全部退化为 `rel`；`claudecode`（`reads_shared=False`）与任一共享平台并存时两副本同 rel ⇒ 一处处置会同时命中两份，`--restore` 可能覆盖另一根有意保留的本地改动。帮助还写"相对项目根"，与真实匹配口径不符 | 人面路径统一为**项目相对路径** token（内部身份不变）；预览 `selected_paths`/`before_states`/`risks`、导出 `target_path`、安装记录 `path`+`root_ref` 同批；旧形态 `rel` 不再静默套用。回归 `test_w1_upgrade_path_identity.py`（11 断言，含多根分别处置与拒绝旧形态） |
| a-2 | `task-retrospect` 帮助把 `--evidence` 标"可选"、`--decision` 标"必填"，handler 恰好相反；另有 `--commit` 从未被读取 | 帮助与 handler 对齐；删幽灵旗标。新增 `test_help_contract.py`：①帮助登的旗标必须被真实实现读取（含委托型命令解析、动态读取须登记理由）；②"可选"缺省不得点名报错、"必填"缺省不得成功；③回归注入证明断言不空跑 |
| a-2 同类（自行发现） | `task-knowledge --evidence`、`task-curate --kind/--reason/--compensation/--evidence/--check` 均为幽灵旗标（写进去被静默丢弃） | 同批删除帮助与注册表条目；既有 `RegistryCompletenessTest` 改为真实解析委托型命令并加覆盖下限（此前对 20 余命令空跑） |
| b-P0 | `git tag -l` 仅 `wf-v0.1.0`，README 却记载 0.1.5→0.1.6 可用 upgrade 升级；安装器只认真实 tag ⇒ 文档承诺的升级通道在字段上不可执行。"三者同批"义务只活在散文里 | 新增 `scripts/verify-wf-release.py`（六项只读核对：tag 存在/源码重建一致/tag 树逐字节/清单版本/README 版本/rules_digest）；tracked `pre-push` 只对 `refs/tags/wf-v*` 推送跑同一脚本；README §3 补机械核对与**现有 tag 事实**（0.1.1–0.1.6 是未打 tag 的开发版，不作升级来源/目标）。回归 `test_verify_wf_release.py`（15 断言，含 ref 名与 `git tag --list` 语义） |
| b-P1 | `merge_hooks_json` 只在首装与 `add_platforms` 调用；升级只替换脚本字节，`self_check` 只核脚本 digest ⇒ 改落点/命令串的发行会让已升级项目带着失效 `hooks.json` 条目运行而自检报绿（退化方向＝会话身份错配） | `plan_hooks_json`/`apply_hooks_json` 成为唯一判定（`merge_hooks_json` 退化为首装包装）：absent/appended/unchanged/updated（等于安装记录 `host_hook_entries` 的上一版命令串）/conflict/unreadable；冲突在**写入资产之前**整批拒绝；应用段落地并把新串写回记录；`self_check` 核条目存在与命令串；命令串由落点派生（`host_hook_command`）。回归 `test_w3_hooks_sync.py`（17 断言） |
| b-P2#1 | dsh 部署表声明 `env:DSH_SESSION_ID` 但全仓无消费者（宿主映射唯一写者是 codex hook）⇒ 声明值读起来像"已可用"，实际运行期等同不可区分 | **只收口口径**，不新建适配层（实现稿已声明边界）：部署表注释写明 `env:` 前缀只表示"适配层/显式信封可见"、未交付适配层的宿主等同 `unknown`，可区分性由 `enable --new-session` 覆盖 |
| b-P3 | `task-knowledge --changes`（action/path/reason/summary）与 `spec-update --changes`（operation/new_paths/old_paths/content）同名异构 | 两侧帮助互加显式提示"形状不同、不可互填"；不改 schema（b 自评"登记即可"，改名会动已发行帮助面） |

## 2. 驳回或不成立

| 编号 | 判定 | 理由 |
|---|---|---|
| b-P2#3「review-context 不能在 launch 前预取材料」 | **驳回** | 材料面与"允许自主读取"由 launch 声明并绑定本轮锚点；launch 前的材料外发没有人的本次范围授权（§6.5 外发确认），预取会绕开 `authorize record export`。这是设计正确性，不是缺陷 |
| b 的 F13「未跟踪文件内容不进 diff」 | **已不成立** | `materialize_delivery` 对未跟踪文件用 `git diff --no-index /dev/null <path>`，且以任务基线提交为 base（中途提交也能取差异） |
| b 的 F18 后半「`workflow_snapshot_digest` 恒 None」 | **已不成立** | `check.py` 已实现该键并入锚点 |
| c 的 `AGENTS.md:25` 陈旧表述、README skills「11 个」 | **已不成立** | 现为 13 个且 AGENTS.md 已更新 |
| d 的 F03「generation 需手拼」 | **已不成立** | `resolve_generation` 缺省回退会话运行态记录的代次 |
| d 的 F20「工作区无关改动无排除通道」 | **已不成立** | `workspace_exclusions` + `--workspace-exclusion` 已实现 |
| b-P2#2「审批决定代笔」 | **维持已声明边界** | §1.5 明确"模型伪造人判不可辨、不建立验证证据链"；`--draft` 骨架已消除"靠报错试错"，不再新增防伪字段 |
| 同轮报告"判定前可重述" | **维持 11-21 裁决（导入后不可覆盖）** | 本轮把成本证据补在 §3，重开需人重新裁决，不自行实施 |

## 3. 需人重新裁决的候选（本轮只记证据，不实施）

**同轮报告"判定前可重述"**：按时间序列复述实测（不压缩）：

1. 第 1 轮导入时，`s1/report.md` 没有可核身份（槽位名不是 CLI 名）→ 只识别到 `dsh`，
   `review-decide` 报 `single-provider`；
2. 评审者改名 `review-zcode.md` 后，`status=done` 标在正文末尾 → 自动发现只扫文件头，仍只识别到
   `dsh`；同时五轴写成 `"pass：说明"` 不符合结构；
3. 状态行移到头部、五轴改成结构后两份都导入成功；接着 `zcode` 的 `excluded-scope` 是自然语言、
   没覆盖敏感面模式 → `review-decide` 再拒；
4. 修正 `excluded-scope` 后**再导入**才被"导入后不可覆盖"（`report digest differs`）挡住，
   只能开第 2 轮。

即：摘要锁是**迫使开新一轮**的那一步，不是唯一原因；前 3 步属报告协议问题，现在由
"骨架内嵌契约 + `wf lint report` 一次性全量预检 + 导入/判定同源校验 + 状态行窗口写清"承接，
第 4 步才是"判定前可重述"这一条待裁的口径（11-21 人裁维持"导入后不可覆盖"，本轮只补证据）。

## 4. §1.1「核心原则」AI 指导要点复核结论

| 要点 | 结论 |
|---|---|
| 判据句（可计算且同一结论 → 机制；其余留指引/交人） | **准确**，且与实现一致：本轮收的都满足"明确输入 → 唯一结果"，留下的（措辞、取舍、采纳建议）都确实是语境判断 |
| 护栏①「可计算 ≠ 同一结论」 | **准确**：机制只核形制，语义结论必须由 AI/人给（本轮无一处把"输入出现某词"当结论） |
| 护栏②「指引必须写到收敛动作」 | **准确且已在正例中生效**：`wf-review-action` 的"fail 之后：谁修、怎么算收敛"三步是本轮无需改动的正面样本 |
| 指引就地、不成层 | **准确**：本轮未新增 skill/层级，判断指引只落既有判据位 |
| 强度如实声明 | **准确**：本轮新增的 `--draft`/断言/核对脚本都只核形制与可计算事实，不宣称防伪 |
| 人签封闭清单 | **不完整 → 已补**：漏「机械修订的等价性签认」（`task-approve` 的 `choice=机械修订` 一直要求人签） |
| 「机制侧只提供它需要的事实（`facts`/`next`）」 | **偏窄 → 已补**：实际还产 `exits` 令牌表与 `--draft` 只读骨架；补句写明两者仍是机制产物、不构成新层级 |
| 「固定流转程序化」清单 | **陈旧 → 已改**：三方升级匹配的"未交付期间该条为登记缺口"与 0.1.5/0.1.6 实况矛盾 |
| 四段机制契约唯一定义置于 §1.1 | **不变式可读性代价**（候选，未改）：已有"读法标注"指向 `session-flow.md` 的收敛版；整体搬迁会牵动索引/引用面（charter T7 同批义务），本轮不动，登记为整理候选 |

## 5. 仍未关闭的边界（如实登记，未宣称已解决）

- **存量红灯 `r89_tests`**（上一轮遗留、非本轮回归）：断言仍在找 argparse 的 "unrecognized"
  措辞，而入口已改为自有文案 + `WF_USAGE_INVALID` 结构化输出。修断言会改变脚本字节并让
  `candidate-audit.json` 的登记摘要失效；重生成审计需要已提交候选，故本轮只登记、不动，
  下一轮随提交后的 candidate 审计同批修。

- **hook 落点改名**：`target_relative` 变化会被当作"新脚本"追加，旧条目按同名规则留在用户文件里；
  升级预览会显示 `appended`，自检只核当前落点的条目。清理旧条目仍需人做。
- **旧安装记录缺 `host_hook_entries`**：升级不阻断，但条目非当前值一律按冲突交人（不猜"那是我们的旧串"），
  应用后补登当前值。
- **`--keep/--restore` 是破坏性口径变更**：旧形态（资产相对路径）不再接受，报 `WF_ASSET_DECISION`
  并列出可用 token。理由：该旗标自交付起从未在字段上被真实使用（无对应 tag），双口径正是本轮要消除的缺陷。
- zcode/pi/dsh 仍无会话标识适配层（实现稿已声明边界）；`prefs`、`judgments` 等偏好仍只在本机。

## 6. 验证实况

- `python3 -m unittest discover -s scripts/tests -t .`：1671 用例，**5 failures + 9 errors 全为存量**
  （干净 worktree 复核同红：`test_template_cache` 9、`test_wfdrive_constants` 2、
  `test_python_runtime_identity` 1），本轮新增/改动用例全绿。
- `bash scripts/tests/wf_runtime/full/run_all.sh --full`：149 单元（59 套件 + 5 流程 + 85 repro），
  **148 绿 + 1 处存量红**（`r89_tests` 的 `[FAIL] R92 --skill-root 已移除`）：上一轮把未知参数
  从 argparse 的 "unrecognized" 换成入口自有文案时未同批更新该断言，**干净 worktree 复核同红**，
  与本轮改动无关。**本轮不动它的理由**：改该脚本字节会使 `full/candidate-audit.json` 里 r89 的
  `script_sha256` 失效，而重生成审计需要"已提交候选 + 重跑 candidate 模式"；为了一个措辞断言
  手改审计记录等于伪造审计证据。登记为下一轮收口项（先提交候选→重跑 candidate 审计→同批改断言）。
- `build-wf-release.py --verify --verify-token-parity` 绿（0.1.7，74 资产）；`validate-wf-design.py`
  （定义/消费 100%/100%、二值 92/92、三档 14/14、输入摘要 4/4）、`check-doc-refs.py`、
  `validate-skills.sh` 全绿。
- `verify-wf-release.py --version 0.1.7 --ref refs/tags/wf-v0.1.7`：**预期失败**（tag 尚未创建，
  由人执行）；这正是本轮要杜绝的"文档声称可升级、字段上不可执行"的自检入口。
## 7. 第二份审查输入（同日）的逐项处置

| 编号 | 判定 | 处置 |
|---|---|---|
| a-P1「hooks 冲突留下半安装态」 | **成立**：两条路径都先置 `held`、先写资产，之后才判 hooks；冲突直接 return ⇒ 首装留下「`.wf/` 已建 + 资产已投 + 无安装记录 + 写权 held」，追加平台留下「新资产已写 + 平台/记录未更新 + 写权 held」，后续入口被 `WF_WRITER_BUSY` 挡住 | 判定（只读）移到**任何写入之前**；写入后才可能失败的三处（投放写冲突、hooks 落地失败、维护应用失败）统一走 `maintenance_abort`（与既有"投放后自检失败"同语义：写 recovering 检查点 + 递增代次 + 两个出口，不留 held）。**同类一并收口**：首装的 `FileExistsError` 早退原本也留 held；`add_platforms` 的幂等条件并入"待落地 hook 动作"，使"安装后 hooks.json 丢条目"能用**重跑同一条安装命令**补齐。回归 `test_w3_hooks_sync.py::HalfInstallStateTest`（3 断言），并做回退注入（把判定挪回写后 ⇒ `.wf/` 已建/资产已写/writer=held 全部现形） |
| a-P2 / b-P0「README 把不存在的 tag 当可用升级来源」 | **成立（文档口径）** | README §1 的 0.1.6→0.1.7 句加前提"人已按 §5 创建 `wf-v0.1.7` tag；未建 tag 时该命令在 `REF_RE`/`rev-parse` 层面即不可执行"；§3 补"忘记打 tag 也有提醒"的机制说明 |
| b-P0 追加点「忘记打 tag 无提醒」 | **成立** | `pre-push` 增非阻断 WARN：本次推送改动发行树、且清单声明的版本没有对应 `wf-v*` tag ⇒ 打印 WARN 与两条修复命令。只提示不阻断（先推分支再打 tag 是合法顺序；阻断会把正常流程拦死） |
| b-P1「dev-deploy 安装走 upgrade 通道未端到端实跑」 | **成立（待实测，非代码缺陷）** | 机制上不矛盾（新引用由 `--release-ref` 校验；安装记录只作 O 侧事实）。登记为**下一轮 dogfood 必测项**：dev-deploy 形态（`release_ref` 非真实 tag）作为 O 侧 → 升级到已打 tag 的 0.1.7 |
| b-P2「hook 落点改名边界」 | **已在实现稿 §2.3.11 声明**，维持 | 不改 |
| b-P3「机制稿 §0.1 历史段顺序失真」 | **成立** | 把"五轮修正"句移到"四轮修正"句之后（同日先四轮提交、后五轮），历史账本恢复时间顺序 |

**这一轮复审同时确认了上一份审查的三项 P2 维持未动**（zcode 宿主会话标识 unknown、审批决定 AI 代笔、review-context 需已发起轮），均属声明边界，非回归。

## 8. 第三份审查输入（同日）的逐项处置

| 编号 | 判定 | 处置 |
|---|---|---|
| a-P2「`.codex/hooks.json` 在预览与维护回执里不可见」 | **成立（并比报告更宽）**：安装预览只列发行资产与 `.wf/`；首装回执只记 `deployed`；追加平台回执只记 `deployed + 安装记录`——三条都漏掉这次操作改到的**用户共享文件**。同类还有 `.gitignore` 托管段：首装既不预览其动作、也不进回执，且**冲突被静默忽略**（升级路径有拦截，首装没有） | ① 安装预览在 `--confirm` 前列出宿主 hook 配置的逐路径动作与托管段动作，冲突在**确认前**即 `needs_decision`（未写任何文件）；② 回执逐路径记 `.codex/hooks.json` 与 `.gitignore` 的前后摘要（`before` 新建时为 `None`，与既有 `deployed` 条目同口径）；③ `.gitignore` 判定拆成 `plan_gitignore`（只读）+ `apply_gitignore`（落地），与 hooks.json 同一形状；首装在锁内重核冲突、写入前拦。回归 `test_w3_hooks_sync.py::PreviewAndReceiptTest`（5 断言），两条关键断言做过回退注入（`plan_host_hooks` 返回空 ⇒ 预览与回执断言同时变红） |
| b-P0「wf-v0.1.7 tag 仍未创建」 | **成立（收尾纪律，非代码缺陷）** | 三条守卫已齐（tag 推送核对 / 推发行树的 WARN / 六项核对脚本）；本轮代码侧不再加东西，等提交后由人建 tag |
| b-P1「dev-deploy 形态走 upgrade 未实跑」 | **维持（待实测）** | 与第二份审查同一项：登记为下一轮 dogfood 必测，仍不宣称已实跑 |
| b-P2 四项残余边界 | **维持** | 均为已声明边界，无回归 |

**本轮之后`.codex/hooks.json` 的完整可见链**：预览（确认前）→ 落地（写入前判定/锁内重核）→ 回执（逐路径前后摘要）→ 自检（条目存在与命令串）→ 升级（`previous_command` 判定 + 同上回执）。任一处缺失都能由后面的环节报出，不再有"改了用户文件却没人知道"的环节。

## 9. 第四份审查输入（同日，含两份报告）的逐项处置

| 编号 | 判定 | 处置 |
|---|---|---|
| a「F09 残余：主会话仍要手写 `launch.json`」 | **不成立（陈旧）** | 现实现里 `review-launch` 的请求由入口 `default_launch_request(...)` 按当前对象生成，`--launch-request` 在帮助里明确是"可选：覆盖/补充"（`cli.py` 的 `review-launch` 条目、`review.py::launch_preview`/`launch` 均按 request_path=None 走生成路径）。a 的建议（`--draft` 化）**已经是现状**，不需要再做。复查 b 的同一处结论与代码一致 |
| a「`review-context` 需已发起轮」 | **维持（设计正确）** | 材料面与外发授权由 launch 声明并绑定本轮锚点；launch 前取材料会绕开人对外发的本次授权 |
| a/b「状态行契约两说」 | **成立** | 判定只读开头 `STATUS_HEAD_CHARS`(400) 字符，而三处出口写"报告第一行"。按"机制不收紧、口径说准"处理：出口改为"放在报告开头（骨架写在第一行；判定只读开头前 400 字符）"，`wf-review` skill 补同一句；新增 `test_guidance_contracts.py` 锁住**渲染后的出口字符串**（拿源码文本比数字会假绿） |
| b「§1.1 长段落难读，建议前置默认规则」 | **成立（指引结构）** | 在 §1.1 前置一句「默认规则（先读这一句，其余为细则）」——在已批准目标与范围内 AI 自主诊断/择优/实现/补测/收敛，仅人签封闭清单与无法消解的冲突才交人；它是对既有判据句/正面授权/负向禁令的**摘要与阅读顺序**，不新增规则、不复述清单（避免第二份判据） |
| b「决定文件：谁作决定 vs 谁录入不一致」 | **成立** | 在设计稿 §1.2「不得代人作答」处补「作决定与转录是两个动作」：决定内容必须是人已明确给出的选择，模型可按它填写文件（`--draft` 即为此），不得推测/补全/替人选择；`wf-continue` 证据文件纪律补同一句+指针；`_decision_draft_result` 的 `next_` 改为"按人的明确答复填写（不得推测或替人选择）"。新增断言锁这三处 |
| a/b「同轮报告判定前重述」 | **维持 11-21 裁决（待裁）** | 台账 §3 已列证据，默认不动 |
| a「审批代笔 / 会话2 绕过 / 身份适配」 | **维持声明边界** | 与既有登记一致；b 指出"不能仅凭文件由 agent 代笔判越权"与我们的口径相同（决定权在人、录制权可委托） |
| b「台账对第 1→2 轮过程有压缩」 | **成立（表述精度）** | 台账 §3 已改写为按时间序列陈述：先命名/状态行/轴格式，再 `excluded-scope`，最后才是摘要锁；摘要锁是**迫使开新一轮**的那一步，不是唯一原因 |
| 证据缺口：`~/.zcode/cli/log/zcode-2026-11-08.jsonl` | **成立** | 该文件不存在（日志目录最早 11-17）；reviewer 侧行为只有会话导出单一来源，结论按此边界表述，不据其宣称 reviewer 侧已核 |

**本轮确认无回归**：a 列的"已解决"项（轮次无上限、`task-rework` 真实现、`repair_scope` 取代现场状态机、`workspace_exclusions`、`materialize_delivery`、锚点并入控制面摘要、`--draft` 骨架、完整验证日志）经抽查与源码一致。

## 10. 第五份审查输入（同日）的逐项处置

| 编号 | 判定 | 处置 |
|---|---|---|
| a-1「`task-retrospect --decision` 读入即丢弃」 | **成立（我上一轮修 a-2 时新引入）** | 删除该旗标（帮助、注册表、handler）；`wf-continue` 的复盘命令行同步改为 `--task --evidence`（结论取自 `evidence.conclusion`）。**盲区同时收口**：`test_help_contract` 只保证"被读取"，新增 `DeadValueTest`——对每个命令的真实实现做赋值-未使用扫描，扫出并清掉 4 处同类死值（`cmd_baseline_apply.root_real`、`run_check_scope.task_dir`、`decide.gaps_out` ×2、`runs.create.snapshot_rel`） |
| a-2「指引契约测试锁措辞」 | **部分成立（保留）** | 只对**有行为对应物的契约**锁字面（状态行窗口→出口字符串、决定/转录→判据位与出口文案）；测试文件头已写明"不要推广到纯指引措辞"。这是刻意取舍，不是遗漏 |
| b-1「升级确认未绑定最终执行内容」 | **成立** | 锁内重核由"路径集合相等"改为 `_plan_fingerprint(plan)`（逐路径动作 + 本地/上游/新版摘要）。行为测试：预览后在**锁内重核那一次**改动文件 ⇒ `WF_PREVIEW_STALE` 且不写入；回退注入（改回路径集合）⇒ 断言变红 |
| b-2「首装中途失败后无法接续」 | **成立（我把故障变可恢复却漏了接续路径）** | 路由判据由"`writer.json` 是否存在"改为"**安装记录**是否存在"：无安装记录但 writer 在 ⇒ 按首装**重试**处理，沿用既有 writer（代次/修订递增、`maintenance_results` 追加不清空）。回归：模拟 `writer=recovering` + 无安装记录 ⇒ 重跑成功且代次 > 7；已有安装记录仍走追加平台 |
| b-3「manual 开工验证必然失败」 | **成立** | `_run_start_verifications` 对 `kind=manual` 不再执行：记 `{verification_id, kind: manual, status: human_required, criterion}`，真正的人判证据仍由 Check 的 manual 规则（要求 `decision`）强制。机制稿 §7.1 的 start 段同批登记证据形状；回归 2 条 |
| b-4「hook 自检把命令存在当成适配有效」 | **成立** | `plan_hooks_json` 增 `event`（默认 `SessionStart`）：命令挂在其它事件下 ⇒ `conflict`（附 `observed_events`），不再报 `unchanged`；`apply` 也只在目标事件内追加/更新。回归 4 条（含自检对错位条目的 problem） |
| b 其余「身份适配/过早宣称/taakku」 | 维持 | 与既有声明边界一致，不加机制 |

**本轮之后的一处口径变化**：`task-retrospect` 不再收决定文件——复盘是"证据 + 结论"的留痕，
不构成人签动作；若将来需要人签复盘结论，应在 §1.1 人签清单里新增一行，而不是留一个读了就丢的旗标。

## 11. 第六份审查输入（同日）的逐项处置

| 编号 | 判定 | 处置 |
|---|---|---|
| a-1「首装重入会覆盖既有会话写权」 | **成立（我上一轮把"可恢复"做过头，越过了持有边界）** | 新增 `_first_install_takeover()`：只有**无持有者**（`holder is None`）或**本框架安装维护检查点**（`phase` ∈ install*/deploy-assets/hooks-json-apply/self-check-failed）才允许按首装重试；`holder.kind=session`、交接中间态、其它维护阶段一律 `WF_WRITER_BUSY` 并原样保留 writer（不改 holder/代次）。回归 4 条（会话持有/其它维护阶段/交接态/崩溃的安装维护态）+ 回退注入（去掉守卫 ⇒ 3 条同时红） |
| a-2「开工验证失败输出绕过脱敏」 | **成立** | `_run_start_verifications` 的失败事实改为 `check.redact_text(...)`（遮罩唯一实现仍在 `check.py`）。修改前实测：`task-start` 事实里带出明文 `Bearer sk-live-…`；修改后同一条命令的输出被遮成 `***`。回归 `StartVerificationRedactionTest` |
| b「§1.1「随 0.1.5/0.1.6 发行」与 README「0.1.1–0.1.6 未打 tag」口径张力」 | **成立（措辞）** | 改为「随 0.1.5/0.1.6 的**源码树交付**」，并点明 0.1.1–0.1.6 未打 tag、不是升级来源/目标，tag 事实以 README §3 为准；机制稿修订说明与设计稿输入摘要同批更新 |
| b 其余（摘要锁待人裁 / tag 待建 / dev-deploy 升级待实测 / 声明边界 / control_plane_digest 一次性失效） | **维持** | 与既有登记一致；另外 b 独立复跑本轮 6 个新增测试文件 83 例全绿，与本台账声明一致 |

**这轮之后的收口边界**：`install.py` 的写权边界在"首装重入"这条路上恢复成与其它维护入口一致
（不把别人的持有当空闲）；遮罩在开工与 Check 两个执行路径上同源。

## 12. 第七份审查输入（同日）的逐项处置

| 编号 | 判定 | 处置 |
|---|---|---|
| a-1「脱敏仍泄露较长凭据」 | **成立（两处叠加）** | ① `redact_text` 的窗口右边界原本固定 `MASK_WINDOW`(512)，超过它的值只遮前半段——改为 `_value_extent()`：跳过键名收尾引号与分隔符后**覆盖整个值**（含引号包裹/中文键），扫描量以该值为界，长单行仍是线性（原注释里的 O(n²) 风险来自无界键名正则，那条早已收紧）；② `_run_start_verifications` 原本"先取末尾 800 字符再遮罩"，长值前缀被截掉后找不到触发词——改为**先遮罩、后截断**。改前实测：1100 字符虚构 Bearer 残留 579（全量遮罩）/799（先截断）；改后均为 0。回归 `LongCredentialMaskTest`（4 形态 + 顺序断言） |
| a-2「首装分支缺锁内重判」 | **成立** | 在首装锁内**第一步**重判 `installation.json`：存在即抛 `_InstalledMeanwhile`，退出 `with`（释放锁）后交回 `add_platforms`（它自己取锁，不能嵌套）。既有安装身份、平台、根一律不被覆盖。回归 `ConcurrentInstallTest`（伪造"进入锁的瞬间另一个进程写完记录"）+ 回退注入（去掉锁内重判 ⇒ 变红） |
| b-P1「摘要锁是最后一个僵硬限制」 | **维持 11-21 人裁（待人裁）** | 台账 §3 证据在案；b 的"成本惩罚诚实修正"判断与我们的口径一致。**不自行放开**：这是审查新鲜度 vs 修正成本的取舍，属人签范围 |
| b-P2「tag / dev-deploy 升级待实测」 | **维持** | tag 由人建；dev-deploy→tag 的 upgrade 端到端仍是下一轮 dogfood 必测项（本轮不宣称已跑） |
| b-P3「维护面只加不减，减法纪律未行使」 | **记录为观察项（本轮不做结构删减）** | 结论与 charter T6 的张力成立；但本轮每项新增都有登记的消费点，且都在人执行的安装/升级路径上、不约束 AI 日常使用。**不做"为凑减法而删结构"**——那会把风险换成没测过的改动。登记为下一轮测量项：把"一次安装/升级的实际操作轮次与失败重试次数"作为 dogfood 观测量，用数据判断这套守卫是否已越过盈亏平衡 |

**本轮之后**：`.codex/hooks.json` 的可见链（预览→判定→落地→回执→自检→升级）与 `install.py` 的
写权边界（首装重入、并发安装）都已闭合到"不把别人的持有当空闲、不覆盖既有安装身份"；
遮罩在开工/Check 两条执行路径上同源且不再被截断顺序破坏。

## 13. 第八份审查输入（同日）的逐项处置

| 编号 | 判定 | 处置 |
|---|---|---|
| b-1「脱敏未覆盖承诺保护的形态」 | **成立（两类）** | ① 键名带后缀（`access_token_value`、`api_key_primary`）时值起点错位，1100 字符值完整残留——新增 `_value_start()`：跳过键名剩余字符与收尾引号，找分隔符后才取值；② `scheme://user:password@host` 的 userinfo 无触发词，永远进不了窗口——新增 `STANDALONE_PATTERNS`（不依赖触发词，全文线性一遍），只遮 password、保留 user/host；无触发词的文本也要跑它。回归 `UrlCredentialMaskTest`（4 断言）+ 键名后缀两形态并入 `LongCredentialMaskTest` |
| b-2「首装自检失败的恢复链未闭合」 | **成立**（第一次修法过刚，回退为"可见但不阻断"） | 自检失败会先落安装记录；repair 清写权后重跑落进"无任何变化"幂等分支，旧实现直接回 OK——既不重跑自检也不报状态。改为该分支**按同一 `self_check` 复核**并把结论摆进事实与输出：`self_check: clean|problems` + `self_check_problems`，问题逐条列在人的可见输出里；仍按"无变化"返回、不取写权、不增代次（第一次把它做成硬阻断，被 `r83_tests` 的幂等用例证明会误伤——那是"项目本就不一致"的合成夹具，不是幂等分支该拦的东西）。回归 `NoopSelfCheckTest`（3 断言） |
| b-3「长凭据修复引入重复扫描」 | **成立** | 每个触发词都重算值边界 ⇒ 长值内反复出现触发词时平方（实测 100KB 43.7s、1MB 未在 60s 内完成）。改为「已落在当前窗口内的触发词跳过」（窗口右边界已覆盖整值），1MB 降到 0.13s。回归 `RedactionLinearCostTest`（1MB < 5s） |
| a-P1「摘要锁」 | **维持 11-21 人裁（待人裁）** | 第三次登记同一项，不自行放开 |
| a-P2「tag / dev-deploy 升级待实测」 | **维持** | tag 由人建；端到端升级仍是下一轮必测 |
| a-P3「连续七轮只加守卫」 | **记录为观察项** | 与 b-P3 同项；本轮**不做为凑减法的结构删减**，下一轮用"安装/升级轮次与重试次数"作测量项 |
| a-P4「安全路径修复批次自带回归，靠下一轮复审发现」 | **成立（批次纪律）** | 接受该批评：六轮接遮罩时用了"先截断后遮罩"、七轮才修正顺序；七轮的窗口半宽又引入截尾。**本批补的对抗性用例覆盖该模式**：长值、前缀切断（顺序断言）、键名后缀、引号包裹、URL userinfo、跨行、重复触发词成本——并在 `.trellis/spec/docs/wf-delivery-discipline.md` §8 增一条批次纪律：「凡触及脱敏/遮罩/摘要/身份类安全路径，同批必须带对抗性用例（长值、前缀切断、引号跨行、成本上界）」 |

## 14. 第九份审查输入（同日，含两份报告）的逐项处置

| 编号 | 判定 | 处置 |
|---|---|---|
| a-P0「掩码模式集与窗口扩展不同步：引号形态明文残留」 | **成立** | `Authorization: Bearer "…"` 与 `--token "多词值"` 两类实测原样/半段残留。**不再逐形态补洞**：按协议 `secret-mask` 的承诺把形态**一次性规格化**为有序规则表（Authorization/Bearer 含引号值、flag 与键值含引号多词值、厂商令牌 sk-/gh[pousr]_/AKIA/xox、PEM 私钥块、URL userinfo、中文键名），并**删除窗口机制**（`TRIGGER`/`MASK_WINDOW`/`_value_extent`/`_value_start`/`_standalone_masked` 全部移除）——窗口曾兼作"值的可见范围"，是连续四轮漏遮的根因；改为全文逐条应用 + 字面预筛 |
| b-1「跳过窗口内触发词是错误假设 + 相邻字段/引号/多行块」 | **成立** | 同上：去掉窗口后"跳过"这个假设本身消失；相邻字段、`password: "FIRST SECOND THIRD"`、PEM 块均已覆盖。成本实测：256KB 最坏 31ms（旧窗口实现 1.3s，且旧实现 100KB 对抗输入 43s） |
| b-2「审查材料未脱敏」 | **成立（外发面）** | `write_materials` 对 `diff.patch`/`prd.md` 同批脱敏，`status.json` 标 `redacted: true`；`wf-review` skill 告知 reviewer "看到 `***` 是预期，别判材料缺失"。材料字节没有参与任何锚点/摘要绑定（已核），因此脱敏不改判定 |
| b-3「卸载可能删掉同组用户 hook」 | **成立** | `uninstall.remove_hooks_json_entry` 改为只摘**本脚本成员**，同组用户命令保留；摘空才丢弃 entry。回归 2 条 |
| b-4「hook 自检忽略 matcher」 | **成立** | `matcher` 纳入触发条件：条目带非空 matcher ⇒ `conflict`（附 matcher 值），自检同判。回归 2 条 |
| b-5「只能写五类证据文件」与实际输入契约冲突 | **成立** | `wf-continue` 该段改写为按"谁生成"分类：入口生成的事实不要手写；人/模型填写的输入**以 `wf help <命令>` 的 `inputs` 为准**（决定/主会话复核/双轴结论/changes/plan/judgments/复盘证据/排除声明），并列出各自 `--draft` 骨架 |
| b-6「发行核对提示的 tag 命令多一层 refs/tags」 | **成立** | 改为 `git tag wf-v0.1.7 <提交>`；回归 1 条 |
| b「人签封闭清单漏 manual 验证与工作流 human_points」 | **成立** | §1.1 清单补「手工验证结论（`kind=manual` 只接受人的 `decision`）」「工作流 `human_points`」；同时写明机械修订通道以"已有同触碰面批准"为前提、首次批准失败只能重批、结构等价由机制核而"只是排版/转义"的判断仍由人签 |
| b「原则正确≠已证明 AI 发挥更好」 | **成立（证据边界）** | 台账 §15 登记：本轮只证明机制与指引落点，**没有**新版会话证明用户不再反复提醒、不再因格式换轮；列为下一轮 dogfood 观测量 |
| a-P1/P2/P3（摘要锁、tag、只加不减） | **维持/登记** | 摘要锁第三次登记待人裁；tag 由人建；减法：本轮**实际删掉**了窗口机制与 4 个辅助函数（净减），并把脱敏按协议规格化——这是对"只加不减"的第一次实质回应 |

## 15. 第十份审查输入（同日，含两份报告）的逐项处置

| 编号 | 判定 | 处置 |
|---|---|---|
| a-P0「裸前缀规则吞掉分隔符，键值对真值明文残留」 | **成立（我这轮重写引入的回归）** | 复现 `token = abc`→`token *** abc`、`Bearer = jwt`、`--token = abc`。三处结构修正：① **顺序**改为"具体形态（PEM/厂商令牌/URL/Authorization/Bearer-分隔符）→ 键值与 flag → 裸前缀"；② `_VALUE` 的裸值**不得以 `=`/`:` 起始**（否则分隔符被当值）；③ `_QUOTED` 整体分组——未分组的 `|` 会让右半支脱离 head，变成"任意位置裸引号串都被遮"（新矩阵用例当场抓到）。关键词预筛不再掺空白形态（`"token "` → `"token"`），tab 形态不再靠巧合 |
| a-P1「验证方法：手挑样例，补洞批次自带洞」 | **成立** | 遮罩测试改为**由规则集派生的性质矩阵**：`FORMS × 分隔符/引号变体 × 值长(12/40/1200)`，断言"文档化值形态绝不出现在输出里"；材料级、散文不误遮、转义引号、分隔符不被当值、成本上界各有专项。新增规则只需进 `FORMS` 即被覆盖 |
| a-P3（只加不减） | **本轮实际净减** | 删窗口机制（`TRIGGER`/`MASK_WINDOW`/`_value_start`/`_value_extent`/`_standalone_masked`），规则表 + 字面预筛取代；256KB 最坏 31ms（旧 1.3s；旧版 100KB 对抗 43s） |
| b-1「人的确认可被沿用到未确认内容」 | **成立（两处）** | ① 手工验证决定新增 `content_digest` 绑定，`status` 暴露 `delivery.content_digest`；不匹配/缺失即 `not_run` 并给出 `stale_decision` 事实；② 机械修订入口核对决定的 `object_digest` 与当前 PRD 摘要（不一致 ⇒ `WF_SEMANTIC_DECISION`；PRD 不可读也拒）。`object_digest` 未被复用为内容摘要（它已是"批准对象摘要"），避免一义二用 |
| b-2「材料纳入未登记/失配日志」 | **成立** | 日志改为**先核身份再物化**：未被命令引用或摘要不符的日志不进材料包，只进 `status.json.problems`；转义引号形态并入遮罩（`"(?:[^"\\\n]\|\\\\.)*"`）+ 矩阵用例 |
| b-3「脱敏抹掉 reviewer 需要的代码行为」 | **成立（我上一轮的过度收紧）** | 遮罩分两级（同一张规则表）：`redact_text` 全量（日志/错误回显），`redact_material` 只遮**字面凭据**（引号值、Bearer/Authorization、厂商令牌、PEM、URL userinfo）；`password = read_from_store()`、`token = request.headers.get(...)`、散文保持可读。材料 `status.json` 标 `redacted: true` |
| b-4「重复调试计数强制交人」 | **登记待人裁（不改机制）** | 属 §11.2 既有语义；改它等于改人裁过的判定。台账登记证据与 §1.1 的张力，等裁决 |
| b-5「重跑 Check 迫使复杂任务重审」 | **成立** | `review_binding`：`check_id` 不同但 `result.anchor.check_anchor == check.check_anchor`（同内容/同规划/同控制面）时仍算绑定；锚点不同才拒。回归 2 条 |
| b「§1.1 判据」 | 维持既有结论 | 无新反例；本轮只改机制面，未动判据句 |

**验证口径的两处修正（本轮教训）**：① 运行器的 `run-*` 目录按**字典序**取"最新"会读到旧 run（今天因此误判了两次），改为读 runner-control 打出的 run_id；② 全量套件用的是**已提交的** harness 脚本 + 工作树 payload，所以"改了 harness 却没生效"是预期现象，harness 改动必须在提交后才会作用于运行器。

## 16. 第十一份审查输入（同日，含两份报告）的逐项处置

| 编号 | 判定 | 处置 |
|---|---|---|
| a-P0 / b-3「`redact_material` 零生产消费点；按意图接线又带洞」 | **成立（我上一轮的死代码 + 设计洞）** | 两处同批修：① `write_materials` 改调 `redact_material`（diff/PRD 都换），并加**接线断言**（`redact_material(diff_text)` 在源码里，`redact_text(diff_text)` 不在）；② 材料档的值域改为「引号值，或不含 `.`/括号/下标的裸串」——`.env`/ini 的 `API_KEY=abcdefgh123456`、短值 `hunter2` 都遮，`read_from_store()`、`self.secret`、`os.environ['X']` 保留可读。判据是"这串本身像不像字面凭据"，不是"有没有引号" |
| b-1「直接人判验收仍只绑 ID + 规划版本」 | **成立** | `_acceptance_results` 对无 `verification_ids` 的验收项同批核 `content_digest`；不匹配即不得判 passed。回归 2 条 |
| b-2「tests.json 原样写入命令记录；重生成材料时旧日志留在包里」 | **成立（两处）** | ① `tests.json` 的 `commands` 先 `redact_material` 再落盘（人工验证 decision 的 reason/quote 属外发面）；② 物化前**清空** `materials/check-logs/`，上一轮复制进来、这次不再合格的文件不留 |
| b-4「复用分支读错锚点位置」 | **成立（我的实现 bug + 夹具放错形状）** | 真实 Check 记在 `check.anchor.check_anchor`；判定改读嵌套（顶层回落）。夹具同步改成真实形状（本轮教训：夹具形状必须取自真实记录） |
| b-6「纯人判验收卡在 commands 空」 | **成立（且我第一版改法引入新 bug）** | 空命令仅在"规划声明了验证项"时才判缺失。第一版实现时新起了同名变量 `declared`，覆盖了上面按 id 建的字典，导致**每条命令都被判 `unknown verification_id`**、模板夹具 archive 失败、运行器整轮起不来——已按"用既有 `declared`"修正，并在注释里写明这个坑 |
| b-5「重复调试计数强制交人」 | **维持·登记待人裁** | 属 §11.2 既有语义，改它等于改人裁过的判定。第三次登记 |
| a-P1/P2/P3 | 维持 | 摘要锁人裁、tag 人建、减法观察项不变 |

**本轮运行器故障的根因不是工具本身**：`template.out` 里 `[archive] exit=1 WF_CHECK_FAILED` 暴露了我 b-6 修法里的变量遮蔽，
运行器在模板阶段就中止（表现为 `metrics unreadable`、`commands/` 空）。修正后全量恢复 148/149。

## 17. 第十二份审查输入（同日，含两份报告）的逐项处置

| 编号 | 判定 | 处置 |
|---|---|---|
| a-P0「中文键与 `Bearer =`/`Basic =` 在材料级明文外发；矩阵子集手挑掩盖了它」 | **成立（同一语义类内的不一致）** | ① 中文键与裸赋值规则各补一条 `_LITERAL`+`code_safe=True`（同时保留 `_VALUE` 全量档——全量仍遮任意值，材料只遮字面量）；② 材料档矩阵断言改为**按形态名 + 规则档位派生**，并把"材料档不遮"的白名单显式列出（只余调用/常量引用类），不再手挑子集 |
| a-P0 次要「`api_key_version = 2` 被过掩」 | **成立（可读性方向）** | 字面量判据加"含至少一个数字、长度 ≥4"：`DEFAULT_PASSWORD`/`api_key_version = 2`/`some_identifier` 保留可读，`hunter2`/`abc123456`/`.env` 值仍遮 |
| a-P1「`current_check_anchor` 诊断字段恒空」 | **成立** | 阻断事实改用同一处算出的 `current_anchor`（读 `check.anchor.check_anchor`） |
| b-1「材料先写原文、后覆写脱敏」 | **成立（外发面）** | `write_materials` 改为**一次性写脱敏结果**：新增 `redact_object()` 递归处理结构化数据，不经 JSON 往返；`tests.json` 直接写脱敏后的 commands。回归含引号理由的用例（断言结构仍是合法 JSON 且无明文） |
| b-2「材料判据既漏又误」 | **成立（判据重定）** | 见上：带点号的 `.env` 值（`API_KEY=abc.def123`）遮；常量引用/版本号不遮。判据从"有没有引号"改为"像不像字面凭据（含数字、无调用/下标语法）" |
| b-3「同内容复验仍触发重审」 | **成立（指引与身份核验未跟上门禁）** | ① `anchor_identity_problems` 在 `check_id` 不同但锚点相同时不再拒（附两侧锚点事实）；② `check_next_hint` 对"已有 pass 且锚点相同"给出"可请人直接 finish"的下一跳，不再要求 review-launch。回归各 2 条 |
| b-4「可选验证把已通过任务卡在归档前」 | **成立** | 空命令判据改为按**必须执行的验证项**（`required is not False` 或被验收项引用）计算，可选且未被引用的验证项缺失不再阻断。回归 2 条 |
| b-5 / a-P2 / a-P3 / a-P4 | 维持 | 调试计数待人裁（第四次登记）；摘要锁待人裁；tag 由人建；减法观察项不变（本轮矩阵改为派生式，属于"减手工判断"方向） |

## 18. 第十三份审查输入（同日，含两份报告）的逐项处置

| 编号 | 判定 | 处置 |
|---|---|---|
| a-1「材料仍先写原文再覆写」 | **成立（我上一轮只挪了最后那份写，漏了前面那份）** | 删掉 `write_materials` 里第一次 `{"commands": commands}` 原文写入；`tests.json` 只在末尾写一次（脱敏后）。回归用 `write_json` 监视器断言**写入次数 = 1** 且内容无明文（上一版只查最终文件） |
| a-2「结构化脱敏丢字段名语义」 | **成立** | `redact_object` 增 `_structured_secret_key()`：字段名属凭据类（password/token/secret/中文键等）时值整体遮（含数字型），`token_count`/`*_version`/`*_name` 等保留。回归 2 条 |
| a-2 后半「纯字母裸值不遮」 | **成立（声明取舍）** | 按 b-P1 处理：在 `protocol/redaction.json` 增 `material-literal-heuristic` 条目，写明"引号值/含数字裸值/凭据类字段名/厂商令牌/PEM/URL userinfo 遮；**纯字母无数字裸值不遮**"与理由（保表达式可读），并注明"日志与回显走全量档"。边界测试固定两档行为 |
| a-3「同内容复验入口不一致 + 过早请人收工」 | **成立（两处方向相反）** | ① `submitted_scope.test_results` 的 Check 身份改为锚点感知（同锚点不再要求重开一轮）；② `check_next_hint` 的"可请人 finish"改为**先问门禁**（`gates.review_binding`），报告摘要失配时改说"重新导入同一份报告或换一轮"，不再把 AI 送进必然失败的归档 |
| a-4「重复调试计数强制交人」 | **维持·登记待人裁**（第五次） | 属 §11.2 既有语义；四次登记均未改，等裁决 |
| b-P0「派生测试白名单分支恒真 + 死条目」 | **成立（我自己写的空转断言）** | 重写：字面量形态断言"两档都遮"，表达式形态单列断言"材料保留、全量遮"；删除恒真三元与死条目。**并机械化**：新增 `test_assertion_hygiene.py`——AST 扫描 `assertEqual(x, x)`/`assertTrue(True)` 类恒真断言（含"纯表达式"判据，避开稳定性断言），扫描器自身也带反例测试 |
| b-P1「纯字母凭据泄漏面未登记」 | **成立** | 见 a-2 后半：协议条目 + 边界测试 |
| b-P2/P3/P4 | 维持 | 摘要锁人裁；tag 人建；减法观察项不变（本轮新增的是扫描器，属"防复发"而非新守卫层） |

## 19. 第十四份审查输入（同日，含两份报告）的逐项处置

| 编号 | 判定 | 处置 |
|---|---|---|
| a-1「配置文件的裸凭据随材料外发，且只标 `redacted: true` 不说哪部分」 | **成立（我上一轮的取舍把配置类当成代码类）** | 材料 diff 改为**按 `diff --git` 分片选档**：配置类文件（`.env*`/yaml/ini/toml/properties/json/tfvars/pem…，`is_config_path`）用**全量**规则，代码文件用材料档（调用可审）；PRD 由组件级改全量。`status.json` 增 `redaction` 说明策略（不再有"标了 redacted 却不说哪部分是原文"的盲区）。回归：同一份 patch 里 `config.yaml`/`.env` 的裸值被遮、`src/app.py` 的 `read_from_store()` 保持可读 |
| a-2「默认请求不带 `check_anchor`，同锚点复用永不生效」 | **成立（我上一轮只改了消费端）** | `default_launch_request` 的 `test_results` 增 `check_anchor`（与 `check`、`commands` 同批生成）；回归断言默认请求里带锚点 |
| a-3「开工验证在项目锁内可能无限期占锁」 | **成立** | 抽出 `check.verification_timeout(root)`（Check 与开工验证**共用一处**：同配置键、同非法值归因），`_run_start_verifications` 传入 `timeout=` 并把 `TimeoutExpired` 归为 `WF_CHECK_FAILED` + `timed out after Ns`（不再抛裸栈）。回归 2 条 |
| a-4「重复调试计数强制交人」 | **维持·登记待人裁**（第六次） | 属 §11.2 既有语义 |
| b-P1「恒真断言扫描范围不全」 | **成立** | `ROOTS` 扩到整个 `scripts/tests/`（含发行链/构建链与 `wf_review/`），排除 fixtures 目录；顺手关掉扫描器自己打开的未关闭文件句柄 |
| b-P2「`_VALUE` 连续重复定义」 | **成立** | 删除重复行（死值同型）；并确认 `DeadValueTest` 只覆盖函数体，模块级重复赋值由这次人工清掉 |
| b-P3/P4/P5 | 维持 | 摘要锁人裁；tag 人建；减法观察项——本轮把"材料遮罩"从单一档位重构为按文件分片，属于结构简化而非叠加 |

## 20. 第十五份审查输入（同日，含两份报告）的逐项处置

| 编号 | 判定 | 处置 |
|---|---|---|
| b-P0「tests.json 的 argv 走材料档，比入库记录暴露更宽」 | **成立（档位选错，顺序倒置）** | 复核实测：入库 `redact_argv` → `--password ***`；材料 `redact_object` → 明文。新增 `redact_commands()`：**argv 用位置语义**（`--password <值>` 分离写法也遮），其余字段走**全量**档；`tests.json` 改用它。回归 2 条（分离写法 + 纯字母裸值） |
| a-1「开工验证吞掉超时配置错误」 | **成立** | 去掉 `except Exception: None` 兜底：配置非法就按 `WF_RECORD_INVALID` 抛出，且**不执行命令**（回归断言 `subprocess.run` 未被调用）。只有"未配置"才是合法无界 |
| a-2「材料仍外发纯字母裸值」 | **残余面已收窄，并且这次是真的收窄** | 十四轮把配置类/PRD 改全量后，残余只剩"代码类文件里的纯字母裸值"；十五轮再把命令记录改 argv 语义，残余面进一步收窄。协议条目同步改写（不再声称 `.env`/PRD 会外发） |
| a-3「源日志目录缺失时旧副本仍留在材料包」 | **成立** | 旧副本清理移到 `if os.path.isdir(_log_root)` **之外**：每次生成材料先清空 `materials/check-logs/`。回归（源目录不存在的场景） |
| a-4「重复失败计数强制交人」 | **维持·登记待人裁**（第七次） | 属 §11.2 既有语义 |
| b-P1「residual_risk 文本落后于实现」 | **成立** | 协议条目重写：残余面 = "仅代码类文件、含纯字母且无数字的裸值"，并点名配置类/PRD/命令记录/日志都不受影响 |
| b-P4「三个外发面各自选档、无处登记理由」 | **成立** | `redaction.json` 的该条目增 `surfaces` 表：`diff.patch`(per-file) / `prd.md`(full) / `tests.json`(argv-aware + full)，各带 `why`；档位选择成为协议的一部分而非散在调用点 |

## 21. 第十六份审查输入（同日，含两份报告）的逐项处置

| 编号 | 判定 | 处置 |
|---|---|---|
| b-1「中文/引号路径的配置差异漏遮」 | **成立** | Git 的 `"a/\350\256\276\347\275\256.yaml"` 形态解析不出路径 → 落到代码档。新增 `_patch_path()`（切引号分段、还原八进制转义）+ **fail-closed**：路径解析不出时分片按配置类全量遮。回归 3 条（转义路径被遮、无法解析的头 fail-closed、代码路径仍可读） |
| b-2「命令记录改 argv 语义后漏了字段名遮罩」 | **成立（我上一轮修的副作用）** | `redact_commands` 的 dict 递归重新接上 `_structured_secret_key`：`decision.password` 之类字段整体遮，`token_count`/`verification_id` 保留。回归 2 条 |
| b-3「原轮未判定却让 AI 重开一轮」 | **成立** | `check_next_hint` 先识别"**未判定且锚点=当前**"的进行中轮次，提示"继续这一轮（取材料→reviewer→导入→判定），不要重新 review-launch"；只有无进行中轮次时才走重开提示。回归 1 条 |
| b-4「开工命令先跑、前置后核」 | **成立** | `_run_start_verifications` 移到门禁/工作区/唯一性/PRD 解析**之后**、写入口快照之前；回归用源码顺序断言（门禁 < 验证 < 快照）固定该不变量 |
| b-5 / a-P1 | **维持·已按"维持原判"登记** | 重复失败计数：第八次登记，属 §11.2 既有语义。摘要锁：按本份建议在台账写明"**维持 11-21 人裁**（非待办；重开须人显式提出）"，不再悬置为待办 |
| a-P2「升级链一行未动、守卫零真实运行」 | **如实登记** | 今天十四轮全部落在脱敏/材料链；`install.py` 的守卫仍只有单元证据，`dev-deploy→upgrade` 端到端仍是下一轮必测项（台账 §7/§8 已有登记，本轮不重复宣称） |
| a-P3「只加不减」 | 登记 | 本轮在材料链是"修档位/修路径解析"，方向正确；累计 diff 规模与"零 dogfood 实测"如实记录 |
