# 第四十七轮：第四轮独立复审 + 其他 agent 反例的复核与修正

- 处置编号 R82；实跑见 `validation.md` §74
- 结论：**14 条成立并已修**（复审 7 条 + 其他 agent 7 条）；本轮最重的一条又是"校验端修了、写入端没修"。

## 一、第四轮独立复审

| 编号 | 结论 | 复核 | 处置 |
|---|---|---|---|
| D-1（高） | 解除依赖写入端丢人判与替代路径 | **成立** | 写回改取 `released.decision / released.replacement` |
| D-2（中） | 归档终态巡检取错目录名，全量误报 | **成立** | `basename(path)` |
| D-3（中） | `review-decide` 重读报告不核摘要 | **成立** | 先核 `file_digest` 与 `report_digest`，失配入 `problems` |
| D-4（中） | 带引号 JSON 多词值漏遮 | **成立** | 带引号值允许空格/逗号；无引号值单独一条 |
| D-5（低） | `token_type_ids` 被误遮 | **成立** | 豁免集合补 `token_type_ids/token_ids/input_ids` |
| D-6（低） | install 对非对象资产抛裸 AttributeError | **成立** | `verify_assets/compute_rules_digest/plan_writes` 三处结构化拒绝 |
| D-7（低） | `repair --dispose` 预览只显示一条、写入改全部 | **成立** | 同 operation 多回执一律 `WF_SEMANTIC_DECISION`，预览与写入面同一集合 |

**D-1 是最该记的**：上一轮我只改了校验端（`_require_release_decision`），写回仍取外层 `entry.decision`——按正确输入形态写进策展的是一具空壳：`released.decision=null`，机制稿要求的"保留历史选用事实"完全不成立。R81 的用例只测了校验函数，没测写入结果，所以漏检。这一轮补了端到端断言（写入后 `released.decision` 非空、`replacement` 保留、`old_digest` 保留）。

## 二、其他 agent 的 7 条

| # | 问题 | 复核 | 处置 |
|---|---|---|---|
| 1 | spec 续做不核前像，会覆盖中断后产生的新内容 | **成立** | `_resume_decision()` 三态：符合前像→应用；已是本动作后像→跳过；都不符→`WF_SEMANTIC_DECISION` 并保留现场 |
| 2 | task-new 有意图但没有恢复路径 | **成立** | 新增 `_pending_task_create()` + `_resume_task_create()`：重入 `task-new` 续做同一任务，补绑定/运行态并结案 |
| 3 | 解除依赖写入丢失 + `choice=reject` 也算解除 | **成立** | 同 D-1；新增 `RELEASE_CHOICES`（解除依赖/release/released） |
| 4 | 批准证据不绑当前 PRD 内容 | **成立** | `_task_prd_is_approved()` 比对 `approval.object_digest` 与当前 PRD 摘要；批准后改 PRD 即失效 |
| 5 | skill 仍把 wf 签发路径当可用出口 | **成立** | `wf-start` 写明该路径**尚未交付**，不引导人走；`enable` 新增可缓存 `activation` 模板与 `cache_hint` |
| 6 | 归档恢复把多路径 subject 当单文件名 | **成立** | 复用 `_subject_paths()` |
| 7 | 能力声明 `transport=unsupported`、只有声明人无观察依据仍通过 | **成立** | `SUPPORTED_TRANSPORTS` 白名单 + 每条证据须带 `kind`/`ref` |

## 三、期间新发现（都是我改出来的或既有 fixture 暴露的）

- **N-R79**：能力结构收紧后，`wf-dev-deploy` 与 `install.py` 的"installer preview"证据没有 `kind/ref`，**所有夹具的 task-new 全部 `WF_IDENTITY_UNRESOLVED`**。两处都补上 `kind=declared-verification` 与 `ref`，与 `session.check_profile` 的判据对齐。
- **N-R80**：`verify_assets` 的非对象检查第一次插错了位置（锚点文本不匹配，静默未生效），靠 r82 用例才暴露；第二次改成按函数体插入并短路后续摘要计算（否则同一件事报两遍）。
- **N-R81**：`r81` 的 A5 用例给的是"批准但摘要不匹配"，判据收紧后必然失败——补成摘要匹配，并新增"批准后改 PRD 即失效"的正例。

## 四、口径

四轮独立复审 + 其他 agent 反例累计处置 34 条行为缺陷。未覆盖轴不变（上位文件授权链、历史实跑原始记录）；`issued_id` 签发命令仍是第二轮事项，本轮把 skill 的误导性引导改掉了。
