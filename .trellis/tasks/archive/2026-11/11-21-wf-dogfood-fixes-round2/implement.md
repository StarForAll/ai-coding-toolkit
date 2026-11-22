# 执行计划：wf 第二轮 dogfood 复审修正（修订版 r10）

> r10：第十轮审查 4 条全部成立。变更：PRD 提示发射点 ① 补"仅无 picks 时"；
> DECISION_FIELDS 统一（design 2.1/2.3 与 implement 2.3 消除 _load_decision
> 残留；2.5 的"在 _load_decision 之前返回"是代码路径、保留原样）；
> design §5 影响面补模板资产行；严格相等断言落点定为
> wf_protocol/test_invariants.py；design 头同步 r10。

## 顺序原则

R1（降档+登记）→ R2（机械项）→ R3（3.4 执行器顺序 → 3.1 措辞 → 3.2 去重 → 3.3 文案）
→ 发行版本化 → 全量验证 → 重建发行树。
理由：3.4 与 3.2 同改 session-flow"运行约定"段，3.4 先行避免中间态矛盾；
repo_rules 文案放最后（digest 联动面最大）。

## Checklist

### Stage 1 — R1 task.sampled 降档 + 登记
- [ ] 1.1 `gates.py`：TASK_STEP_SPECS 删 required 条目、移除阻断分支
- [ ] 1.2 `tasks.py`：`check_next_hint` 试点建议语（`stop --preview` 与
      `archive --draft` 的 facts 附 `pilot_sampling_pending`，无 picks 时）；
      **提示常驻、无开关**（用户裁决：不加 pilot_sampling 键，不动
      thresholds.json/机制稿 §8.1/发行模板）；试点结束=一次代码改动删提示
      发版，语义作为登记文字写进机制稿抽样段；
      archive 成功输出不加提示；status 不新增 sampling 投影
- [ ] 1.3 `task-flow.md:65` **整段改写**（删 required 标记与阻断出口，改可选/试点小节——发行自检双向核对，不能只改文案）
- [ ] 1.4 `wf-finish` / `wf-continue` 各加一句试点抽样指引（不跑不阻断）
- [ ] 1.5 设计稿/机制稿/索引登记 + **机制稿 §0.1 输入摘要四份 sha256 回写**
- [ ] 1.6 测试迁移（**全清单**）：
      `wf_review/test_gate_timing.py:25/:30/:41/:53/:70/:78`（**6 处** task.sampled
      调用，含 test_frozen_selection_satisfies_the_step——移除步骤后仍调
      已不存在的判定，T0 必红 → 改"无步骤 + 提示投影"）、
      `gates.py` RULE_CLASS_STEPS 清理（:32-37 定义；消费点 508/541/860，
      :475 是 task.sampled 的 facts 分支、同批清理但归属不同，不留死代码）、
      `wf_runtime/test_repair_scope.py:440/:616`（旧 blocking stub 改语义或
      删并登记）、f1_ordinary.py:138、r17r24_tests.py:370、
      r58_tests.py:105、wfdrive.py:278 `freeze_sampling`（调用点改可选、注释
      同步；f1_init.py 是 f1_ordinary 的模块、无独立 unit）；
      `test_check_next_route.py` 扩断言（无 picks 建议语出现/有 picks 不出现），
      逐条映射旧断言；新增正反断言 + 回退注入
- 验证：T0 + `WF_SUITES="f1_ordinary r17r24_tests r58_tests" bash scripts/tests/wf_runtime/full/run_all.sh`
      （**空格分隔**，plan.py:400 按 `.split()` 解析，逗号选不到套件）

### Stage 2 — R2 机械项入口化
- [ ] 2.1 object_digest 分档回显：task-approve **两个分支**（not cover 分支
      补 expected_prd_digest + 未绑定分支已有，next_ 补语义句）、
      replan（双候选进 exits）、baseline-apply/验收（既有 expected_digest 进 next_）、
      archive/stop（格式示例 + **各自 example_file**，不回显摘要值）；
      **提取模块常量 `DECISION_FIELDS`**（cli.py:1758 的六键局部元组上升为
      模块常量，预检与测试共用——`_load_decision` 必填键的唯一事实源，
      测试不再 import 私有函数或抄清单）
- [ ] 2.2 `at`：help 明写语义；预检错误 next_ 附 `records.now_str()` 当前值
- [ ] 2.3 `COMMAND_HELP`：archive/stop 补 example_file；task-knowledge 补
      `--changes` 数组示例（无决定文件，不补 example_file）；
      `test_help_domains.py` **新增**断言（example_file 存在且字段 ⊆
      `DECISION_FIELDS`——原 _load_decision 六键的模块常量，现状无此覆盖）
- [ ] 2.4 `review.py` 骨架预填 excluded-scope（mandatory_exclusions 口径）与
      read-scope=["materials"]；校验不动
- [ ] 2.5 `archive --draft`：免决定草稿输出（archive 决定域形状：
      archive_finish + commit_grant 条目骨架，每条含必填六键
      source/at/subject/object_digest/choice/reason 占位（取 `DECISION_FIELDS`
      生成，不手抄）；
      **只有 commit 条目预填 subject 路径**，finish 条目 subject/quote 留占位），
      只打印不落盘；**只读性质写死：在 `_load_decision`、action 启动与取锁
      之前返回；不要求写权与绑定**（按 archive 正式路径实现的人会先
      `_require_binding` + 取 lock，须在实现处显式排除）；
      `--draft` 与 `--decision` 同给报错；
      archive help next_ 指向；**不挂 stop**（决定域不同，不可互替）
- [ ] 2.6 `load_task` RecordInvalid 附 `carries_id` 属性；cli 兜底分支按属性加
      actual_id facts + "改用记录 id <X>" exits；其余 RecordInvalid 原因不扩权
- [ ] 2.7 新断言：骨架原样过材料包口径；--draft 的 commit 条目 subject 集合 ==
      pending_delivery_paths（不用 commit_grant_paths 做恒真断言）、草稿含
      finish+commit 两类 choice、--draft 后直接归档仍被拒（负例）、
      --draft 与 --decision 同给报错；id 提示出现；
      test_help_domains 新增 example_file 断言（含 archive 双 choice 形状、
      字段 ⊆ DECISION_FIELDS）；
      --draft **只读性质断言**（无写权/无绑定/不取锁时仍可出草稿）；
      逐项回退注入
- 验证：T0 + `WF_TAGS=review` 定向 + repro review 组

### Stage 3 — R3 措辞与重复收敛（顺序：3.4 → 3.1 → 3.2 → 3.3）
- [ ] 3.4 `session-flow.md` 执行器顺序收敛（删第②档与"能跑就复用"）
- [ ] 3.1 四处措辞收窄：`review-flow.md:4`、`wf-review-action/SKILL.md:103`、
      `wf-framework-implementation.md:266` 与 `:284`；上位稿索引消费行回扫；
      无"设计稿 :544"例外（该句为发行恢复语义、不含此措辞）
- [ ] 3.2 纪律论述收进 session-flow 定义位；13 个 skill 纪律段收敛一行+指针；
      单任务推进/证据文件纪律同收敛；wf-review/SKILL.md 删内嵌协议与材料清单；
      wf-review-action/SKILL.md 删判定复述、留后果句
- [ ] 3.3 `repo_rules.json` 只改 why + 显示名（键/patterns/classification 不动）；
      测试夹具 rules_digest 断言同批；发行清单 digest 随 0.1.4 重建自动重算
- [ ] 3.5 grep 校验（全树，排除 wf-release/）：实体论述 ≤2 处；指针句允许 13 处；
      "按事实推导"清零；无"你自身运行时的 Python"残留
- 验证：T0 + validate-skills.sh + check-doc-refs.py

### Stage 4 — 上位稿收口、版本化与全量
- [ ] 4.1 机制稿 §0.1 输入摘要最终核对；`validate-wf-design.py` 绿（含覆盖率阈值）；
      `wf-protocol-docs.py --check` 纳入并保持绿（**核对范围是 §2.2/§8.1/§11.1**，
      是 thresholds/配置表漂移保护网；机制稿抽样段登记**不靠它**，靠
      validate-wf-design.py 的索引/定义位覆盖）；
      **模板键集修复 + 严格相等断言**：`payload/templates/
      project-config.skeleton.json` 先补 `identity_path`（P1，当前树实测
      skeleton 14 键/模板 13 键、差 identity_path，属既有漂移——本任务修复，
      缺省与模板值相同行为不变，模板属发行资产随 0.1.4 重建），然后加
      "模板键集 == `config.skeleton()` 键集"严格相等断言（**落点：
      `scripts/tests/wf_protocol/test_invariants.py`**，该文件已有
      config/protocol 键不变量，天然落点；防未来漂移）；
      枚举回扫清单（本轮新增 §引用/索引消费行逐条核对回写）记录于本文件末尾
- [ ] 4.2 `wf/README.md` 目标版本 → 0.1.4；dev-manifest version 同批核对
- [ ] 4.3 T2 全量：`run_all.sh --full --repro green`
- [ ] 4.4 `build-wf-release.py --version 0.1.4` 重建（单独 chore 提交）→
      `--verify --verify-token-parity`
- [ ] 4.4b 发行说明与 README 核对：**如实声明"本轮不提供 0.1.3 → 0.1.4 升级路径"**
      （upgrade 第三轮未交付、install 仅同引用追加）；已装项目复验需卸载重装
      （保留数据）或手工投放整树；警告"只替换 payload/lib 保留旧清单 →
      WF_ASSET_DECISION 混装拒绝"
- [ ] 4.5 spec 更新（trellis-update-spec）：本轮新契约（骨架预填口径、试点抽样
      降档、--draft 草稿语义）如需进 spec 走此步
- [ ] 4.6 复核最终全量 diff，向用户报告；**提交/收尾/tag 等用户同意后执行**

## 激活与闸门

- `task.py start --allow-empty-context`（inline 模式、jsonl 为空，用户已确认此流程）
- 审查门一：Stage 1 完成后向用户简报归档行为变化（无 picks 可归档 + 提示），
  确认再继续
- 审查门二：Stage 4.6 提交前向用户提交完整 diff 摘要，等同意

## 回滚点

- Stage 1 后（门禁降档、测试迁移完成）第一稳定点
- Stage 3 后（文本收敛完成）第二稳定点
- 任一 Stage 验证红且无法归因 → 停在该 Stage、保留现场、报告失败命令与关键错误

## 枚举回扫记录（4.1 完成时填写）

本轮新增/修改的跨文件引用与登记（逐条核对已回写）：
1. 设计稿 §6.5 新增"试点期抽样（非门禁）"段 → 索引第 139 行 → 机制稿 §0.1 design/index 摘要回写 → validate-wf-design 100%/100% 绿。
2. 机制稿"试点期抽样"段与 9.2 表降档改写 → gates.py/task-flow.md/wf-finish/wf-continue 四处口径一致。
3. session-flow.md"运行约定"纪律唯一定义位 → 13 skill 指针；执行器三处一致。
4. README 0.1.4 + 无升级路径声明 → 版本断言同步 → 发行树重建 --verify --verify-token-parity 通过。
5. 模板补 identity_path → test_invariants 严格相等断言。
6. cp3 夹具既有漂移修复（prd 数组→字符串+真实目录）+ candidate-audit.json 经 candidate_audit.py 完整重跑后替换（cp3 升 passed，p5_v1/r90 维持 dev-only failed 处置）。
7. 回退注入验证（AC10）三处注入变红、还原绿。

## 第三轮审查补充（11-21 收口前追加，用户裁决"收 N1/N2/N3 + §1.1 补正纳入本轮；help 进 backlog"）

- [x] N1 `stop --preview` 免决定：cmd_stop 重构（preview 分支前置，choice 可选；--decision 仅正式执行必填）；help 文本同步。
- [x] N2 `--draft` 指引接上：wf-finish 第 2 步、wf-continue finish 行/收工行各一句指针；stop 收工行同时标注 --preview 免决定。
- [x] N3 enable 终态绑定出口：binding facts 附 `terminal`，next_ 对已归档绑定明示"本会话不能推进、开新任务需新边界"。
- [x] §1.1 三处措辞补正：主动触发补"人已调用入口而启用未成立"；指令分工改"判断指引+一句纪律+指针、机制论述只写一处"；判据句补两条护栏（可计算≠同一结论；指引必须写到收敛动作）。索引行 4 词法/语义列回写、机制稿输入摘要回写。
- [ ] **登记 backlog（下一轮）**：help 覆盖 21→48 + 注册表断言；vendor_dirty 消费点（facts+人确认一次、不阻断）；主会话五轴复核粒度（分歧轴+sources 表达）；§1.1"执行器解析/命令启动"段内容归位（机制契约不宜在核心原则表）——见 wf/analysis/ 登记。
- [x] **不做**：同轮报告条件重导入（N5）——与用户 11-21 裁决（维持不可覆盖边界）矛盾，不采纳；upgrade --apply（第三轮能力桩）维持声明边界。
