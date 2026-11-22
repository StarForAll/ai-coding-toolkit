# wf 修正：基于 dogfood 复审报告的结构性修正（第二轮）

## Goal

以质疑态度复核两份外部分析报告（wf-find-a / wf-find-b）与一轮规划审查意见，
对 `docs/workflows/wf`（及三份上位稿）做**非补丁式**结构性修正：把明显该机械的收进入口、
把越档的硬门禁降档并补齐登记、把自我矛盾的措辞与重复论述收敛回唯一定义位。

## 输入与证据边界

- 报告结论经三路只读核查代理逐条对照源码验证（关键出入：设计稿 §6.5 单段实测
  2662 字符；"按事实推导"句实际共四处——review-flow.md:4、
  wf-review-action/SKILL.md:103、wf-framework-implementation.md:266 与 :284）。
- 规划审查（14 条）逐条核验：13 条成立、1 条部分成立，已吸收进本 PRD 与
  design/implement。关键修正：发行版本升 0.1.4、`stop --preview` 前置 `_load_decision`
  不可作为草稿入口、object_digest 各命令语义不同须分档回显、
  RecordInvalid 无结构化字段、task-knowledge 无决定文件。
- 用户已裁决（2026-11-21）：
  1. task.sampled 降档为可选提示 + 登记试点语义；
  2. 决定文件 object_digest/at 维持"入口校验 + 错误回显"（按命令语义分档回显，不代填）；
  3. 报告导入后不可覆盖维持为声明边界；
  4. 措辞/去重/分类名/执行器顺序四项全做；
  5. 发行版本升 0.1.4；
  6. repo_rules 只改 why 文案与显示名，不动 action 键/patterns/classification；
  7. 提交清单草稿为"草稿 → 人写决定文件即授权"，预览不替代决定。

## Requirements

### R1 task.sampled 档位修正（P0-1）

- 归档硬门禁（gates required 步骤 + 阻断分支）**降档为非阻断提示**。
- **提示发射点定为两处**（archive 后提示无意义且恒真，去除）：
  ① `task-check` 通过后 `check_next_hint` 的 next_ 试点建议语——**仅无 picks 时**
  （有 picks 不提示，与 ② 同条件）；
  ② `stop --preview` / `archive --draft` 的 facts 附
  `pilot_sampling_pending`（无 picks 时）。`status` **不新增** sampling 投影（现状没有）。
- **试点期结束口径（用户裁决：提示常驻、不加键）**：不新增配置键、
  不动 thresholds.json/机制稿 §8.1/发行模板——提示无条件发射（仅以
  "无 picks"为条件），试点结束时由**一次代码改动删除提示并发版**收口。
  试点结束语义作为登记文字写进机制稿抽样段（"试点结束由人决定，届时
  删除提示代码并发版"），不固化为长期产品配置面。
- **同步补登记**：抽样作为"试点期自验证手段"登记进设计稿/机制稿/索引
  （定义、写者、消费点=上述提示、失败出口=无、试点结论由 sampling evaluate/reviewed 驱动）。
- `task-flow.md:65` 的 `[required · repeatable]` 标题**整段改写**（不能只改出口文案：
  发行自检 `build_required_steps` 双向核对 required 标记，残留即预检失败）。
- skill 侧同步：`wf-finish` / `wf-continue` 各一句"试点期可跑 sampling pick，
  不跑不阻断"（不新增 skill）。

### R2 机械项入口化（P0-2）

- **object_digest / at 错误回显按命令语义分档**：
  - `task-approve`：**两个错误分支都要回显** `expected_prd_digest`——
    "not cover"分支（tasks.py:1693-1695，dogfood 实际撞的就是它）现状只有
    decision_digest/current_digest，须补；"未绑定任务"分支（:1700-1704）已有；
  - `replan`：回显 `current_plan_version` 与 `current_prd_digest`（既有 facts 已含，
    补进 exits/next_ 文案）；
  - `baseline-apply` / 人工验收：各自错误分支已有 `expected_digest`，
    统一确保出现在 next_/exits（不新造统一口径）；
  - `archive` / `stop`：仅要求字段存在——预检错误给格式示例，
    指向**各自命令**（archive/stop）补齐后的 example_file，
    **不回显摘要值**（回显会引向错误语义；不指向 task-approve——决定格式不同）。
- `at`：帮助文本明写"人答复时刻（ISO8601）；无法确知时写入口回显的当前时刻"，
  预检错误 next_ 附 `records.now_str()` 当前值。
- `example_file` 补齐：`archive` / `stop` 两个决定文件命令补；
  `task-knowledge` **不补**（它收 `--decision no-update|updated` 值参数，
  无决定文件——该补的是 `--changes` 的数组示例说明，写入 help）。
- 报告骨架：`excluded-scope` 预填 `mandatory_exclusions()` launch 口径、
  `read-scope` 预填 `["materials"]`；导入/判定校验不动。
- 提交清单草稿：**新入口挂在 `archive --draft`**（archive 的决定域才是
  finish+commit_grants 形状；stop 的决定域是 stop_choice，两者不可互替）——
  与 `--decision` 平行、免决定的草稿输出，由 `pending_delivery_paths` /
  `commit_grant_paths` 生成决定文件草稿文本（archive_finish + commit_grant
  条目骨架；每条给全 `_load_decision` 必填六键 source/at/subject/object_digest/
  choice/reason 的**占位**；**只有 commit 条目预填 subject 路径清单**，
  finish 条目的 subject/quote 留占位——框架不替人写"已了解结果与未核实项"）；
  **草稿只打印不落盘**；人把草稿内容写成决定文件即授权；
  `--draft` 与 `--decision` 同时给出时报错（草稿模式互斥）。
  `archive` help next_ 指向它。
- `WF_RECORD_INVALID`（目录名被当 id）：`RecordInvalid` 为裸 message 异常，
  **在 `load_task` 抛错点通过异常属性 `carries_id` 携带结构化信息**（不解析
  消息文本），cli 全局兜底分支按属性存在与否决定是否加 facts `actual_id`、
  exits 给"改用记录 id <X>"；其余 RecordInvalid 原因（duplicate/unreadable 等）
  保持现状不扩权。

### R3 措辞与重复收敛（P0-3 / P1-1 / P1-2 / P1-3）

- "按事实推导"四处（review-flow.md:4、wf-review-action/SKILL.md:103、
  wf-framework-implementation.md:266 与 :284）改为
  "按已落盘事实与 AI 声明推导；声明本身不被机制验证"；上位稿同批回扫，
  不设"设计稿 :544"例外（该句是"按已落盘事实恢复"、发行恢复语义，本就不含
  审查判定措辞，无需例外条目）。
- 技能去重：完整纪律论述收进 `session-flow.md` 定义位（含执行器顺序段），
  13 个 skill 的纪律段收敛为一行判断句 + 指针；
  `wf-review/SKILL.md` 删内嵌协议 JSON 与材料文件名清单；
  `wf-review-action/SKILL.md` 删判定逻辑复述、只留后果句。
- `repo_rules.json`：只改 `why` 与显示名（"环境级规则变更确认"），
  **不动** action 键、patterns、classification；rules_digest 变化属预期，
  同批处理发行清单 `compatibility.rules_digest` 重算与测试夹具同步
  （含"0.1.4 无升级路径，已装项目按卸载重装或整树手工投放复验"的如实声明，
  见 R4；**不写"正常升级/预期路径"**）。
- `session-flow.md` 执行器解析顺序收敛到设计稿 §1.1 唯一定义，
  删第②档与"能跑就复用"表述。

### R4 明确不做（边界声明）

- 报告同轮不可修订（review.py:2847 证据身份模型）：登记 backlog，不动。
- `.wf/**` vendor 边界、B5 attestation 强度边界：现状正确，不动。
- repo_rules 授权模型与 action 键：不动（只改文案）。
- 不新增 skill / 层级 / 必填工件。
- **本轮不提供 0.1.3 → 0.1.4 的升级路径**：`wf.py upgrade` 仍为第三轮
  `_unavailable`、install.py 追加平台仅限同发行引用。已装 0.1.3 的项目
  复验 0.1.4 需卸载重装（保留数据）或手工投放；**严禁只替换 payload/lib
  而保留旧清单**（旧清单 task.sampled 与新 lib 的 declared_step_specs 比对
  会 WF_ASSET_DECISION 拒绝）。此项作为如实声明写进发行说明。

## Acceptance Criteria

- [ ] AC1：无 picks 归档成功；task-check 通过后的 next_ 含试点抽样建议；
      `stop --preview` 与 `archive --draft` 的 facts 含 pilot_sampling_pending
      （有 picks 则两处不提示；提示无条件发射、无开关）。
      **测试前置**：`stop --preview` **免决定**（11-21 三轮审查 N1 修正：预览分支在
      `_load_decision` 之前返回，choice 可选）；`archive --draft` 同为只读免决定；
      task-flow.md 无残留 required 标记、发行自检（build_required_steps）无 problem。
- [ ] AC2：task-approve 两个摘要错误分支（not cover / 未绑定）都回显
      expected_prd_digest；replan 错误回显
      plan.version/prd 双候选；archive/stop 预检错误给格式示例不回显摘要；
      at 预检错误附当前时刻；archive/stop 有 example_file、task-knowledge help 含
      --changes 数组示例；WF_RECORD_INVALID（carries id）含 actual_id 与改用出口。
      **test_help_domains.py 新增断言**：archive/stop 的 example_file 存在、
      字段 ⊆ **`DECISION_FIELDS`**（模块常量，六键唯一事实源）；archive 的
      example_file 同时含 finish 与 commit 两类 choice（决定域形状，help 测试
      只读 COMMAND_HELP；**草稿的双 choice 断言归 AC4**，不在此重复）。
- [ ] AC3：review-context 骨架 excluded-scope 预填必排敏感面、read-scope 预填
      ["materials"]；骨架原样通过材料包口径导入校验；reviewer 自行改写仍受同一校验。
- [ ] AC4：`archive --draft` 草稿的 commit 条目 subject 集合 ==
      `pending_delivery_paths` 结果（首次归档前无 grant，
      不用 commit_grant_paths 做恒真断言）；条目为 archive 决定域形状
      （archive_finish + commit_grant 骨架、每条含必填六键占位、
      **同时含 finish 与 commit 两类 choice**）；
      finish 条目 subject/quote 为占位不预填；
      **只读性质：无绑定、无写权、不取锁时仍可出草稿**（实现在
      `_load_decision`/action 启动/取锁之前返回的唯一验收证据）；
      `--draft` 与 `--decision` 同给报错；
      草稿不落盘（负例：草稿后直接归档仍被拒，因无决定文件）。
- [ ] AC5：review-flow.md:4、wf-review-action/SKILL.md:103、
      wf-framework-implementation.md:266 与 :284 四处措辞收窄完成；
      全树（排除 wf-release/）无"按事实推导"残留。
- [ ] AC6：每句收敛的**实体论述**在源树（排除 wf-release/）出现 ≤2 处
      （定义处 + 至多一处必要判断句）；指针句（含 skill 内一行纪律）允许 13 处。
- [ ] AC7：repo_rules.json why 与显示名自洽、action 键/patterns/classification 不变；
      发行清单 rules_digest 重算一致；夹具断言同步。
- [ ] AC8：session-flow.md 执行器顺序与设计稿 §1.1、bin/wf.py 三处一致；
      源树无"你自身运行时的 Python"残留。
- [ ] AC9：validate-wf-design.py 绿（含机制稿 §0.1 输入摘要回写 + 覆盖率阈值）；
      `wf-protocol-docs.py --check` 绿（核对 §2.2/§8.1/§11.1——它是
      thresholds/配置表漂移保护网；抽样段登记靠 validate-wf-design.py，不靠它）；
      project-config 模板**先补 `identity_path`（P1）**后断言
      模板键集 == `config.skeleton()` 键集（严格相等；当前树实测 14 vs 13、
      差 identity_path，属既有漂移，本任务修复）；模板属发行资产，随 0.1.4 重建；
      check-doc-refs.py、validate-skills.sh、T0 单元层全过；发行树以
      `--version 0.1.4` 重建后 `--verify --verify-token-parity` 通过。
- [ ] AC10：抽样降档、骨架预填、错误回显、草稿命令逐项回退注入：
      临时恢复旧实现时对应断言变红。

## Notes

- 复杂任务：`design.md` 与 `implement.md` 在 `task.py start` 前完成。
- 上位稿修订遵循 `.trellis/spec/docs/wf-design-revision-gate.md` 全部闸门；
  机制稿 §0.1 输入摘要（design/charter/index/sources 四份 sha256）在改动后同批回写。
- 实现遵循 `.trellis/spec/docs/wf-delivery-discipline.md`。
- `task.py start` 需 `--allow-empty-context`（inline 模式、jsonl 为空）。
- 验证命令解释器统一绝对路径 `/softwares/python/bin/python3`。
- 提交收尾只在用户同意后执行；tag `wf-v0.1.4` 由人创建。
