# 第二轮实现核对底稿（只读审计，2026-11-12）

**用途**：给独立复核者一张"机制义务 → 实现位置 → 用例"的对照表。本文档**不**声称第二轮已完全实现；
它只陈述"每条义务落在哪、被什么证据覆盖、哪些没有证据"。判断留给复核者。

**证据边界**（必须先读）：
- 用例分两类：`repro/*.py`（双模：`--expect green` 在正确实现上过、`--expect red` 在注入缺陷后必须变红）与
  `test_*.py`（单元/集成断言）。**双模 repro 只证明"这条断言能区分对错"，不证明实现语义正确**。
- 断言是**结构级**：脚本核结构（字段、引用、门禁、终态），语义是否恰当仍由人判（设计稿 §1.5）。
- 以下"覆盖"= 有实现 + 至少一条能区分的断言；"部分"= 有实现但用例只覆盖一个分支；"未覆盖"= 有实现无用例；
  "登记不做"= 有意不实现并在实现稿登记理由。

## 一、机制稿 §1.5（实例与终止数据）

| 义务 | 实现位置 | 用例 | 状态 |
|---|---|---|---|
| run 记录字段集（definition/inputs/creation_decision/cursor/step_results/task_map/sequence_changes/pending/paused/closing/terminal/ended_at + 只读信息字段） | `runs.py:1053 create`、`runs.py:1842 finish`、`runs.py:2096 terminate`、`runs.py:1723 pause`、`runs.py:2378 resume` | `test_run_create`(10)、`test_run_pause`(2)、`repro/run-resume`、`repro/run-terminate` | 覆盖 |
| `step_results` 的 kind 只取 satisfied/skipped/not_executed | `runs.py:1438 advance`、`runs.py:2096 terminate` | `test_run_advance`(6)、`repro/run-terminate` | 覆盖 |
| `step_results` 保存产物引用 | `runs.py:1275 _step_outputs` | `test_run_outputs`(4) | 覆盖 |
| 返工时 `cursor.step_id` 保留、`cursor.task_id` 定位 R、`task_map` 不被 R 覆盖 | `runs.py:1356 _return_from_rework`、`tasks.py:4514 cmd_task_rework` | `test_rework_cursor`(4)、`repro/task-rework` | 覆盖 |
| 异常终止时任务处置为历史快照；保留任务后续查 task | `runs.py:2096 terminate`、`tasks.py:2859 _apply_abandon` | `repro/run-terminate` | 覆盖 |

## 二、机制稿 §6.1–§6.4（依赖、返工、替换、放弃）

| 义务 | 实现位置 | 用例 | 状态 |
|---|---|---|---|
| 建边：两端活动区、前置未归档；删边只改未归档持有侧 | `tasks.py cmd_task_dep`、`_prerequisite_graph`/`_find_cycle` | `test_dep_edges`(4)、`repro/dep-edges` | 覆盖 |
| 实例内任务只能由「绑该实例 + 游标正确」的会话推进 | `tasks.py:4175 bind_task_for_write`、`runs.py:1438`（writer/scope 核） | `repro/bind-run`（绑定侧）；**写入口的游标不匹配拒绝无用例** | 部分 |
| 返工：R 继承原前置 + `rework_of`；T 前置增 R 且 suspended | `tasks.py:4514 cmd_task_rework` | `repro/task-rework` | 覆盖 |
| 返工：**先预检候选图**（成环即拒） | `tasks.py cmd_task_rework`（`_find_cycle`） | `test_dep_edges` 覆盖 `_find_cycle` 本身；**rework 入口的环拒绝无用例** | 部分 |
| 返工（同实例）：`sequence_changes` + cursor 临时定位 + T 不 paused | `tasks.py:4514`、`runs.py:1356` | `repro/task-rework` | 覆盖 |
| 返工（普通任务）：T 显式暂停 + **保存交接/工作区** + 入口内 release | `tasks.py:4514` 尾部 | `repro/task-rework-handover`（双模） | 覆盖 |
| 复评：五条件、清挂起保留 paused、第二候选则 paused+等待 | `tasks.py:4223 reassess_problems`、`tasks.py:4245 cmd_task_reassess` | `test_rework_reassess`(5) | 覆盖（第二候选分支无用例） |
| 复评：**未持权只报告待复评**（不是阻断） | `tasks.py reassess_write_right` | `test_rework_reassess::ReassessWriteRightTest`(3) | 覆盖 |
| 复评后按登记返回 T | `runs.py:1356 _return_from_rework` | `test_rework_cursor`(4) | 覆盖 |
| 替换：预览（S 前置/继承路径/未覆盖项/下游/实例映射） | `tasks.py cmd_task_replace` → `_replace_preview` | `repro/task-replace-preview` | 覆盖 |
| 替换：`touch_paths` 未覆盖继承路径 → 拒且零写入 | `tasks.py:4373 cmd_task_replace` | `repro/task-replace` | 覆盖 |
| 替换：登记继承（`attribution.inherited`）+ T 异常归档 + `successor_id` | `tasks.py:4373` | `repro/task-replace` | 覆盖 |
| 替换：下游重连；在途实例 `task_map`/`superseded_ids`/cursor 改指 S | `tasks.py:4373` | `repro/task-replace`（下游重连已断言）；**实例映射仍无用例** | 部分 |

## 三、机制稿 §7.1（有限定义格式）

| 义务 | 实现位置 | 用例 | 状态 |
|---|---|---|---|
| 唯一标记 + json 围栏；只解析该块 | `runs.py:139 parse_definition` | `test_definition`(20) | 覆盖 |
| 局部 id 字符集（含 `human_points`/`verifications`） | `runs.py _local_id_problems` | `test_definition` | 覆盖 |
| `format_version=1`；`content_version` 正整数；`purpose`/`applicability` 非空；`steps` 有序非空且 id 全局唯一；`completion` 非空 | `runs.py:731 validate_definition`（六阶段） | `test_definition` | 覆盖 |
| `inputs[].type` 枚举 + `description`；`from` 取值域 | `runs.py _reference_problems`/`_from_problems` | `test_definition` | 覆盖 |
| 必需项 `skip=null`；**可略项必须声明 skip 且 `condition` 非空** | `runs.py _skip_problems` | `test_definition_closed_set`(8) | 覆盖 |
| `skip.downstream.consumer` 必须存在于定义；`replacement` 合法 | `runs.py _skip_problems` | `test_definition` | 覆盖 |
| `human_points` id 步骤内唯一 + 保留前缀（`plan-q-`/`debug-ruling-`） | `runs.py _local_id_problems` | `test_definition` | 覆盖 |
| task 步骤字段（`task_kind`/`goal`/`acceptance`/`actions`/`verifications`）+ **acceptance 引用本步骤验证** | `runs.py:731` | `test_definition_closed_set`、`test_definition` | 覆盖 |
| human 步骤 `question`/`choices` | 同上 | `test_definition` | 覆盖 |
| `outputs`：kind 枚举、path 安全、`{input:name}` 解析、`step_artifact` 越界拒绝 | `runs.py _path_problems` | `test_definition`（探针实测越界被拒） | 覆盖 |
| **未登记键拒绝**（七处闭集） | `runs.py:426 _unknown_key_problems` | `test_definition_closed_set` | 覆盖 |
| 答复保存「实际决定 + 适用快照哈希」 | `runs.py:1438`（`definition_digest`） | `repro/run-finish`、`repro/run-advance-creates-task` | 覆盖 |

## 四、机制稿 §7.2（准备、静态校验与创建）

| 义务 | 实现位置 | 用例 | 状态 |
|---|---|---|---|
| 静态校验六阶段顺序 + 逐阶段问题清单 | `runs.py:731 validate_definition` | `test_definition`、`repro/definition-static-check` | 覆盖 |
| 准备动作在**主记录（准备记录）**登记意图并结案 | `runs.py:800 prepare`、`runs.py:788 _prepare_action_done` | `test_definition::PrepareActionTest`、`repro/definition-static-check` | 覆盖 |
| 未通过草稿保留；未通过不能创建实例 | `runs.py:800`、`runs.py:1053 create`（核 validation） | `repro/definition-static-check` | 覆盖 |
| 创建输入：版本/哈希/输入值/步骤适用性/展开 | `runs.py:886 creation_problems`、`runs.py:934 input_value_problems` | `test_run_create`(10) | 覆盖 |
| **步骤适用性逐步骤声明**（不推断） | `runs.py:886` | `test_creation_steps`(3) | 覆盖 |
| 锁内重核：定义未变/身份未绑定/写权/目标碰撞 | `runs.py:1053 create` | `test_run_create` 部分；**碰撞与锁内重核无用例** | 部分 |
| 先在 `writer.action` 固定 run id/快照摘要/全部目标 | `runs.py:1053` | `repro/run-create-once`（中断续做） | 覆盖 |
| 成功仅取得规划权限，不自动批准 | `runs.py:1053` | `repro/run-create-once` | 覆盖 |

## 五、机制稿 §7.3（推进）

| 义务 | 实现位置 | 用例 | 状态 |
|---|---|---|---|
| 每次推进核绑定/资格/writer/快照/未完动作/cursor | `runs.py:1438 advance` | `repro/run-advance-creates-task`、`repro/bind-run` | 覆盖 |
| 首达 task 步骤：task_map → 建任务 → 写 map → 定位 Plan；重入不建第二份 | `runs.py:1438` | `repro/run-advance-creates-task` | 覆盖 |
| **顺序边只引用上一未略过 task 步骤**（human 不生成边、略过要跳过） | `runs.py:1334 _previous_task_step` | `test_order_edges`(5) | 覆盖 |
| human 步骤：答复是声明 choices 之一 → satisfied | `runs.py:1438`、`_human_answer` | `repro/run-finish`、`repro/run-advance-creates-task` | 覆盖 |
| 可略步骤：先处理 skip、不建任务、记 skipped + 决定 + 快照哈希 | `runs.py:1438` | `test_run_advance` 只核 `_applicability`；**端到端 skipped 路径无用例** | 部分 |
| 已生成 task 时先明确放弃/替换及去向，未完对象不能被游标绕过 | `runs.py:1438` | `repro/run-advance-creates-task` | 覆盖 |
| 完成判据：任务正常归档且持久化可核才 satisfied | `runs.py:1438` | `repro/run-advance-creates-task`、`repro/run-finish` | 覆盖 |
| 受控返工 R：只执行 R 与返回定位，R 归档不算步骤完成 | `runs.py:1356` | `test_rework_cursor`、`repro/task-rework` | 覆盖 |
| 下游引用解析：三类消费方同一规则（来源完成/合法略过的替代/皆无则阻断） | `runs.py _from_problems`/`_skip_problems` | `test_definition` | 覆盖 |
| 实例门禁：只读断言（不写游标/step_results、不建任务） | `gates.py:881 evaluate_instance`、`gates.py:952 evaluate_instance_cli` | `repro/gate-run` | 覆盖 |
| 实例记录挂 `run.advance` 动作（目标含新任务/顺序边/游标） | `runs.py:1438` | `repro/run-advance-creates-task` | 覆盖 |

## 六、机制稿 §7.4（正常结束、异常终止、迁移）

| 义务 | 实现位置 | 用例 | 状态 |
|---|---|---|---|
| 正常结束前置：必需步骤 satisfied、可略合法、任务终态一致、人判齐全 | `runs.py:1842 finish` | `repro/run-finish` | 覆盖 |
| `closing.mode=normal` → `terminal=normal` + `ended_at` + 动作 `persist_pending` | `runs.py:1842` | `repro/run-finish` | 覆盖 |
| 授权提交 + 只读复核；无授权停在 `persist_pending` 并如实说明 | `runs.py:1842` | `repro/run-finish` | 覆盖 |
| 不代调任务的 `finish` | `runs.py:1842`（facts 明示） | `repro/run-finish` | 覆盖 |
| 异常终止：任意未结束实例 + `closing.mode=abnormal` | `runs.py:2096 terminate` | `repro/run-terminate` | 覆盖 |
| **逐个列出**（已生成任务/未生成步骤/改动/外部依赖） | `runs.py:2044 _terminate_preview` | `repro/run-terminate` | 覆盖 |
| 批量计划：放弃走 §6.4、保留写 `independent_resume`、执行中 paused | `runs.py:2096`、`tasks.py:2859` | `repro/run-terminate` | 覆盖 |
| 未生成步骤记 `not_executed`，不建空壳任务 | `runs.py:2096` | `repro/run-terminate` | 覆盖 |
| 固定提交步骤（`persist_record`）+ 双核 | `runs.py:2096` | `repro/run-terminate` | 覆盖 |
| **写权不可核时只读接收停止请求**（侧车，非终止事实） | `runs.py:2024 _record_stop_request` | `repro/terminate-stop-request` | 覆盖 |
| 中断后已归档任务不再次放弃 | `runs.py:2096`（`already_archived` 分支） | **无用例** | 未覆盖 |
| 定义版本迁移/退出路径 | —— | —— | **登记不做**（实现稿 §2.3.11：快照固定、版本不兼容静态拒绝、退出走 terminate） |

## 七、机制稿 §8.4/§8.5（第二轮子项）与 §11.x（动作）

| 义务 | 实现位置 | 用例 | 状态 |
|---|---|---|---|
| `.wf/out-of-scope/`：一概念一文件、只追加、写者 spec-update | `spec.py`、`tasks.py`（拒绝项） | `test_out_of_scope`(10) | 覆盖 |
| 巡检「需人工比对」清单（witnessed/potential/unknown 不当零） | `tasks.py:5015 _manual_compare` | `test_inspect_governance`(6) | 覆盖 |
| `author` 复核顺序（extracted 前置、author=ai 优先） | `tasks.py:5096 _author_order` | `test_inspect_governance` | 覆盖 |
| 巡检报告四类各自 passed/failed/unknown + 未覆盖对象 | `tasks.py:5334 _four_class_verdicts` | `test_four_class_verdicts`(6) | 覆盖 |
| 具名动作先在主记录登记意图（prepare/create/advance/pause/resume/finish/terminate/rework/replace/reassess） | 各入口 `*.action` | 分散于各 repro；**无"每个入口都登记 action"的统一断言** | 部分 |
| `persist_pending` 仅用于 task.archive / run.terminate / run.finish | `tasks.py`/`runs.py` | `repro/run-terminate`、`repro/run-finish` | 覆盖 |
| 只读断言不写 action（gate/locate/validate/preview） | `gates.py`、`runs.py` | `repro/gate-run`（断言零写入） | 覆盖 |

## 八、诚实清单：有实现但**没有能区分的断言**（复核者应重点看这些）

2026-11-12 补过一轮，已从 8 项降到 5 项（下面的编号即当前状态）：

1. ~~替换的下游重连~~ → **已补**（`repro/task-replace` 加了以 T 为前置的下游任务并断言改挂 S）；
   **实例映射改指 S（`task_map`/`superseded_ids`/cursor）仍未覆盖**。
2. ~~返工普通任务分支的入口内 release~~ → **已补**（`repro/task-rework-handover`，双模）。
   **连带补齐一个真缺口**：该分支此前只 `paused`，没按机制稿 §6.2 的「保存交接/工作区」写 `handoff.wip`。
3. 返工/替换的**候选图成环拒绝**（入口层）——只有 `_find_cycle` 本身的单元测试。
4. 可略步骤的**端到端**路径（记 `skipped` + 决定 + 快照哈希、不建任务）——只有 `_applicability` 单测。
5. 终止的「**已归档任务不再次放弃**」分支。
6. ~~复评未持权只报告待复评~~ → **已补**（抽 `reassess_write_right()` + 3 条判定用例）；
   **「第二候选则 paused + 等待人恢复」仍未覆盖**。
7. 创建时的**目标碰撞**与**锁内重核**。
8. 「每个具名入口都登记 action 意图」——靠分散的 repro 间接覆盖，没有统一断言。

## 九、复核者可直接跑的命令

```bash
/softwares/python/bin/python3 -m unittest discover -s scripts/tests            # 534 项
/softwares/python/bin/python3 -m unittest discover -s scripts/tests/wf_runtime  # 287 项
bash scripts/tests/wf_runtime/full/run_all.sh                                   # 148 项 + 84 条双模 repro
/softwares/python/bin/python3 scripts/build-wf-release.py --verify
/softwares/python/bin/python3 scripts/build-wf-release.py --verify-token-parity
/softwares/python/bin/python3 scripts/validate-wf-design.py
/softwares/python/bin/python3 scripts/check-doc-refs.py
./scripts/validate-skills.sh
# 单条双模 repro 的两面（示例）
/softwares/python/bin/python3 scripts/tests/wf_runtime/full/repro/terminate-stop-request.py --expect green
WF_REPRO_INJECT=1 /softwares/python/bin/python3 scripts/tests/wf_runtime/full/repro/terminate-stop-request.py --expect red
```

**并发纪律**：`run_all.sh` 独占 `/tmp/wf-fixtures/*` 与发行仓库副本；同时跑两个会让双方挂起（本任务遇到过一次 SIGTERM）。
