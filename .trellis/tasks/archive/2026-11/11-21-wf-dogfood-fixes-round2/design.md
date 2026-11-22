# 技术设计：wf 第二轮 dogfood 复审修正（修订版 r10）

> r2（首轮 14 条审查吸收）→ r10（第十轮 4 条全部成立）。
> r10 变更：PRD AC1/提示发射点 ① 补"仅无 picks 时"；DECISION_FIELDS 统一
> 进 design 2.1/2.3（消除三处 _load_decision 残留，代码路径引用保留）；
> §5 影响面表补模板资产行（identity_path 修复 + 随 0.1.4 重建 +
> test_invariants.py 断言落点）。
> 此前各轮要点见 implement.md 的 r2–r9 变更记录（三稿同批维护）。

## 0. 设计立场（防打补丁）

- **能由明确输入稳定算出同一结果 → 机制**（R2 全部）；**语义判断、纪律论述 → 指引**
  且**只写一处**（R3 去重）。每处修正同批改**定义位 + 全部消费位 + 登记位**。
- 三档差异处置：task.sampled = C 档（回退实现到登记承诺）；session-flow 执行器第②档
  = B 档（稿内矛盾，收敛到唯一定义）；"按事实推导"措辞 = 收紧到稿子（如实声明强度）。
- 不新增 skill / 层级 / 必填工件。

## 1. R1 task.sampled 降档 + 登记

| 位 | 文件 | 改法 |
|---|---|---|
| 门禁 | `gates.py` | TASK_STEP_SPECS 删 required 条目与阻断分支；`sampling.pick` 的 freeze/picks 事实记录**不动** |
| 提示 | ① `check_next_hint`：task-check 通过分支追加试点抽样建议语（不阻断，无配置开关）；② `stop --preview` / `archive --draft` 等收工预览类 facts 附 `pilot_sampling_pending`（无 picks 时）。archive 成功输出**不加**（事后提示无意义且恒真）；`status` 不新增 sampling 投影（现状没有）。**试点结束口径（用户裁决：提示常驻、不加键）**：不新增 pilot_sampling 配置键、不动 thresholds.json/机制稿 §8.1 配置表/发行模板——提示无条件发射（仅以"无 picks"为条件）；试点结束时一次代码改动删除提示并发版；试点结束语义作为登记文字写进机制稿抽样段 | 不阻断、不新增任务记录字段（`pilot_sampling_pending` 是命令输出 facts 键，不落任务记录） |
| 流程文 | `task-flow.md:65` 整段改写：删 `[required · repeatable]` 标记与"无冻结选样 → WF_SEMANTIC_DECISION"出口，改为可选/试点期小节（`build_required_steps` 双向核对：spec 删后文档残留 required 标记即预检失败，必须同批删） |
| skill | `wf-finish` / `wf-continue` 各一句"试点期可跑 sampling pick，不跑不阻断" |
| 登记 | 设计稿（试点期抽样小节：定义、写者=sampling 命令族、消费点=归档/检查提示、失败出口=无、来源 v42 §0.2、试点结论由 evaluate/reviewed 驱动、样本不足门槛不激活）+ 机制稿 777/783/960/975 处档位同步 + 索引新行 |
| 摘要 | 设计稿/机制稿/索引任一改动后，**机制稿 §0.1 输入摘要四份 sha256 同批回写**（validate-wf-design.py:459-479 强校验） |

测试：无 picks 归档成功；task-check next_ 含建议、预览 facts 含 pilot_sampling_pending、有 picks 不提示（提示常驻、无开关）；回退注入（恢复阻断→红）；
受影响套件/断言逐条映射旧断言（**全部清单**）：
- `wf_review/test_gate_timing.py:25/:30/:41/:53/:70/:78`——**6 处** task.sampled 调用（含 `test_frozen_selection_satisfies_the_step`），移除步骤后仍调已不存在的判定，T0 必红，须改写为"无步骤 + 提示投影"断言；
- `gates.py` 的 `RULE_CLASS_STEPS`（:32-37 含 task.sampled，消费点 **508/541/860**——:475 是 task.sampled 的 facts 分支、非 RULE_CLASS_STEPS 消费，须一并清理但归属不同）——task.sampled 从步骤体系移除后，元组与各消费分支同批清理，不留死代码；
- `wf_runtime/test_repair_scope.py:440/:616`——stub 伪造 task.sampled blocking 的旧断言，改为新提示语义或删除并登记；
- `full/`：f1_ordinary.py:138、r17r24_tests.py:370、r58_tests.py:105、wfdrive.py:278 `freeze_sampling`（调用点改可选、注释同步；f1_init.py 是 f1_ordinary 的模块、无独立 unit）。
不允许只比数量。

## 2. R2 机械项入口化

### 2.1 决定文件错误回显（按命令分档）

| 命令 | object_digest 语义 | 回显改法 |
|---|---|---|
| task-approve | PRD sha256（tasks.py:1690） | **两个分支都回显** `expected_prd_digest`：摘要 not cover 分支（:1693-1695，现状只有 decision_digest/current_digest，dogfood 实际撞的分支，须补该键）与未绑定分支（:1700-1704，已有该键）；next_ 补"应为 <expected>；入口不代填，人批准留痕不可替代" |
| replan | plan.version 或 PRD 摘要双候选（tasks.py:2290-2313） | 既有 facts 含双候选，exits/next_ 文案补齐 |
| baseline-apply / 人工验收 | 提案摘要 / 批准对象摘要（tasks.py:4017、check.py:741） | 各自分支已有 expected_digest，确保出现在 next_/exits，**不造统一口径** |
| archive / stop | 仅要求字段存在（tasks.py:3537-3542） | 预检错误只给**格式示例**（archive/stop 各自的 example_file 补齐后指向自己的示例），**不回显摘要值**（回显会引向错误语义） |

- `at`：帮助写"人答复时刻（ISO8601）；无法确知时写入口回显的当前时刻"；缺字段时预检错误 next_ 附 `records.now_str()` 当前值。
- `COMMAND_HELP`：`archive`/`stop` 补 `example_file`；`task-knowledge` **不补**（收 `--decision no-update|updated` 值参数、无决定文件），改为 help 中补 `--changes` 数组示例。帮助从登记表生成（交付纪律 §9）；`test_help_domains.py` **新增**断言：archive/stop 的 example_file 存在且字段 ⊆ **`DECISION_FIELDS`**（新增模块常量——cli.py:1758 的六键局部元组上升为模块常量，预检/草稿生成/测试共用的唯一事实源；现状无 example_file 断言）。

### 2.2 报告骨架预填

- `review.py` 骨架写入处（已持有 launch 记录）：`excluded-scope` 预填 `mandatory_exclusions()` 口径结果；`read-scope` 预填 `["materials"]`。
- 校验（`report_input_problems`）不动：预填让骨架默认可过，reviewer 自行申报仍受同一校验约束。
- 测试：骨架原样过材料包口径导入；改写越界仍拒（既有断言不回退）。

### 2.3 提交清单草稿（挂 archive，免决定）

- 草稿的决定域形状与 archive 一致（`archive_finish` + `commit_grant` 条目骨架，
  decisions.py:30-34）；stop 的决定域是 `stop_choice`，两者不可互替，**草稿挂
  `archive --draft`**（与 `--decision` 平行、免决定），不挂 stop——否则 archive help
  指向的草稿会被人拿去写 stop 决定。
- 由 `pending_delivery_paths` / `commit_grant_paths` 生成决定文件草稿文本：
  每条含必填六键占位（**取 `DECISION_FIELDS` 生成，不手抄**——原 `_load_decision`
  局部元组的模块常量化）；**只有 commit 条目预填 subject 路径清单**；finish 条目的
  subject/quote 留占位——框架不替人写"已了解结果与未核实项"。
  只打印不落盘。
- `--draft` 与 `--decision` 同时给出时报错（草稿模式互斥）。
- 授权语义：**人把草稿内容写成决定文件即授权**；草稿本身不构成任何决定
  （负例断言：跑 `--draft` 后直接归档仍被预检拒）。
- `archive` help 的 next_ 指向 `archive --draft`。
- 不新增顶层命令；`decisions.DOMAINS` 取值域不变。

### 2.4 WF_RECORD_INVALID 结构化分支

- `RecordInvalid` 是裸 message 异常（records.py:19-21）。**在 `load_task` 抛错点携带结构化信息**：改为 raise 时附 `expected`（记录内 id）——通过异常属性（`exc.carries_id`）携带，cli 全局兜底分支（cli.py:2996-2998）按属性存在与否决定是否加 `actual_id` facts 与 "改用记录 id <X>" exits；**其余 RecordInvalid 原因保持现状**（无属性即不加），不扩权、不影响 duplicate/unreadable。
- `locate_task_dirs` 宽松匹配不动（目录名容错非缺陷）。
- 测试：传目录名 → 错误含 actual_id 与出口；传正确 id → 正常。

## 3. R3 措辞与重复收敛

### 3.1 强度措辞

- 改四处：`review-flow.md:4`、`wf-review-action/SKILL.md:103`、
  `wf-framework-implementation.md:266` 与 `:284`（review-decide 表格行与
  封闭枚举段）→ "按已落盘事实与 AI 声明推导；声明本身不被机制验证"。
- 全树（排除 wf-release/）grep "按事实推导" 清零；无"设计稿 :544"例外
  （该句是"按已落盘事实恢复"、发行恢复语义，不含审查判定措辞）。
- 索引中相关消费行同批回扫（闸门 gate 8 枚举回扫）。

### 3.2 技能去重

- 定义位：`session-flow.md`（含 3.4 执行器顺序段，同文件一次改齐）。完整论述收进"运行约定"：身份信封 / tier·code·facts·next 唯一判定源 / 解释器选择 / 不代人作答。
- 13 个 skill 的"## 纪律"段 → 一行："运行纪律见 `.wf/workflows/session-flow.md`『运行约定』：身份只在请求信封里；入口输出是唯一判定源；不代人作答。"
- 单任务推进（×3）、证据文件纪律（×3）：同理收敛到各自流程文定义处 + skill 一行指针。
- `wf-review/SKILL.md:29` 材料文件名清单、`:50-58` 内嵌协议 JSON：删除，指向"骨架由 review-context 生成，字段以骨架为准"。
- `wf-review-action/SKILL.md:50-68`：删判定逻辑推导复述，只留后果句（"rejected/amended 只记录不关闭，open_blocking 仍在"等是后果+反例的允许形态）。

### 3.3 repo_rules 文案自洽

- 只改 `why`（"因此属 K6 第 5 类不可逆动作" → "属环境级规则变更，需一次显式确认"）与**显示名**；action 键、patterns、classification、K6 引用不动。
- 联动：发行清单 `compatibility.rules_digest` 重算（安装器比对，不一致 WF_RELEASE_CONFLICT）；测试夹具 digest 断言同批；安装/升级文档段核对。**0.1.4 无升级路径，已装项目只按卸载重装或整树手工投放复验（见 §4），不存在"正常升级"表述**。

### 3.4 session-flow 执行器顺序（先行）

- `session-flow.md:52-57` 删第②档"你自身运行时的 Python 可执行文件"与"取到能跑的就整会话固定复用"；收敛到设计稿 §1.1 唯一定义；已设置项失效停下人确认、不降级续试。
- **执行顺序**：本项先于 3.2 去重（两者同改 session-flow"运行约定"段，避免中间态自相矛盾）。

## 4. 发行与版本（0.1.4）

- 版本链：`wf/README.md` 目标版本 0.1.3 → **0.1.4**；dev-manifest `version` 若非占位符同批改；`build-wf-release.py --version 0.1.4` 重建；`--verify --verify-token-parity` 复现核对。
- rules_digest 重算随重建自动发生；`assert_version_not_tagged`（0.1.4 未 tag）通过。
- **升级路径如实声明**：`wf.py upgrade` 仍为第三轮 `_unavailable`（cli.py:2927）、
  install.py 追加平台仅限同发行引用（:743-747）——本轮**不提供** 0.1.3 → 0.1.4
  升级路径。已装 0.1.3 项目复验 0.1.4 需卸载重装（保留项目数据）或手工投放整树；
  **严禁只替换 payload/lib 保留旧清单**（旧清单 task.sampled 与新 lib 的
  declared_step_specs 比对 → WF_ASSET_DECISION）。此边界写进发行说明与 README。
- 发行树重建为**单独** `chore(wf): 重建发行树` 提交（交付纪律 §5）；tag `wf-v0.1.4` 由人确认后创建。

## 5. 影响面与兼容

| 对象 | 影响 | 处置 |
|---|---|---|
| 机制稿 §0.1 输入摘要 | design/charter/index/sources 改动后必失配 | 同批回写四份 sha256（validate 强校验） |
| 发行树 wf-release/ | 源改动后旧树过时 | 0.1.4 重建；源树 grep 校验一律排除 wf-release/ |
| `payload/templates/project-config.skeleton.json` | **发行资产改动**：补 `identity_path`（P1）修既有漂移（当前树 skeleton 14 键/模板 13 键）；随后在 `scripts/tests/wf_protocol/test_invariants.py`（已有 config/protocol 键不变量）加"模板键集 == `config.skeleton()` 键集"严格相等断言 | 模板随 0.1.4 重建；缺省与模板值相同、初始化行为不变 |
| 既有测试套件 | task.sampled 门禁断言（f1_ordinary/r17r24/r58/wfdrive——f1_init 是 f1_ordinary 的模块）、rules_digest 夹具、review 骨架断言、help 取值域断言 | T0 → 定向 → 全量，逐条映射旧断言 |
| 决定文件 schema | 无变化（仍含 at/object_digest） | 无迁移义务 |
| decisions.DOMAINS / 授权模型 | 不变 | repo_rules 只改文案 |
| task.py start | jsonl 空 | `--allow-empty-context`（inline 模式） |

## 6. 回滚

逐文件独立可回滚；注入断言锚行为，回滚即红。发行树由构建器字节复现保证可验证。

## 7. 验证命令（统一绝对路径解释器）

```bash
PYTHONPYCACHEPREFIX=/tmp/wf-unit-pycache /softwares/python/bin/python3 -m unittest discover -s scripts/tests -t .   # T0
/softwares/python/bin/python3 scripts/validate-wf-design.py
/softwares/python/bin/python3 scripts/check-doc-refs.py
./scripts/validate-skills.sh
bash scripts/tests/wf_runtime/full/run_all.sh --full --repro green      # T2
/softwares/python/bin/python3 scripts/build-wf-release.py --version 0.1.4   # 先重建
/softwares/python/bin/python3 scripts/build-wf-release.py --verify --verify-token-parity
```
