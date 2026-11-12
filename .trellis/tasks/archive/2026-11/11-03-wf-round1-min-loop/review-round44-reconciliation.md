# 第四十四轮：E 独立复审（codex CLI）的复核与修正

- 复审主体：`codex exec`（未参与任何修订的异构 CLI），只读模式，材料与判据见 `e-review-packet.md`
- 处置编号 R79；实跑见 `validation.md` §70
- 结论：**10 条判据 → 6 条缺陷成立并已修、2 条判为未覆盖（如实登记）、2 条为通过/低危已处理**

## 0. 逐条判定

| 判据 | 复审结论 | 我的复核 | 处置 |
|---|---|---|---|
| 1 上位文件遵守 | 未覆盖（历史授权链材料不足） | **同意** | 登记为未覆盖轴，state 不整体称定稿 |
| 2 内容类回执哈希 | 缺陷 D01 | **成立** | R79-a |
| 3 Check 门禁只核 pass+锚点 | 缺陷 D02 | **成立** | R79-b |
| 4 维护回执"字段齐就结案" | 缺陷 D03 | **成立** | R79-c |
| 5 调试裁定前缀匹配 | 缺陷 D04 | **成立** | R79-d |
| 6 覆盖声明超出实际执行 | 缺陷 D05 | **成立** | R79-e |
| 7 §6.2 落点函数不存在 | 缺陷 D06 | **成立** | R79-f |
| 8 历史实跑声明真实性 | 未覆盖 | **同意** | 登记为未覆盖轴 |
| 9 Bearer/分离参数未脱敏 | 缺陷 D07 | **成立** | R79-g |
| 10 遗留无消费者函数 | 缺陷 D08（低） | **成立** | R79-h |

## 1. D01 内容类回执哈希输入形状

`step_anchor` 对内容类步骤算的是 `H(domain, {"P": projection})`，机制稿 §11.2 要求 `H(domain, C(P))`——多包了一层对象。用同一投影对两种公式实测不等（`52eb59…` vs 另值），已改为直接哈希投影；固定向量比对见 §70.1。

**兼容说明**：锚点公式变了，改动前产生的回执在重算后失配，会判 `WF_CHECK_STALE`（要求重跑 Check）。当前未发布任何版本，属实现期修正；若已在外部使用需按"重跑 Check"处理，不做回执迁移。

## 2. D02 Check 门禁缺结构复核

`task.check-passed` 原来只核 `result=pass` 与当前锚点一致，没有核 `commands`/`acceptance_results`/`internal_review`/`anchor.rule_version`——只要记录里写上 pass 就能过。

新增 `gates.check_result_problems()`：`result` 必须 pass、`anchor.rule_version` 必须存在、`commands` 必须覆盖批准声明的全部 verification 且状态为 passed、`acceptance_results` 非空、内部双轴（`standard`/`requirement`）各有 `pass` 与依据。缺一即 `WF_CHECK_FAILED`。

## 3. D03 维护回执"字段齐就结案"

`_disposition_complete()` 只看非空 `choice`/`evidence`/类型/承接引用，随后**在探测之前**就派 `disposed`；`choice=reject` + 任意证据也照样结案，且该状态被排除出重叠阻断集合——等于用一个空壳处置解除了维护组阻断。

改为：`receipt_state(record, probe=…, disposition_probe=…)`，`disposed` 需**字段齐 + 事实可核**；无探测或探测失败一律 `pending_check`。新增 `tasks.maintenance_disposition_probe()`：

| 类型 | 事实核验 |
|---|---|
| commit | 证据提交可达且各路径在该提交里等于登记终态；未给提交或提交被拆分时，要求「当前内容等于登记终态且无未提交差异」 |
| reverse | 各路径**当前指纹等于登记前像** |
| transfer | 承接任务存在、**已批准**（`plan.approval` 非空）、其 `touch_paths` 覆盖全部登记路径 |

## 4. D04 调试裁定前缀误配

`subject.startswith(f"debug-ruling-{vid}-{multiple}")` 让「第 1 倍」被「第 10 倍」覆盖：累计 30、阈值 3 时只剩 2–9 待裁定，第 1 倍被误判已裁定。

改为精确解析：`parse_debug_ruling()` 取「最后一个连字符后的正整数」为倍数（verification_id 本身可含连字符），`rulings` 的键改为 `(verification_id, multiple)` 元组；写入口也校验标识结构，非法即 `WF_RECORD_INVALID`。

## 5. D05 覆盖声明与执行不符

`run_all.sh` 没有调用 `p5_f0.py`；`prepare_release_repo()` 在已有仓库时直接返回，因此"45 项 + F0 + 从零重建"无法由该命令复现。

改为：**默认每次重建发行仓库**（`WF_REBUILD_RELEASE=0` 才复用），并把 `run_f0`（安装 → 自举闭环 → 9 条断言）接入入口。当前实际执行 **46 项**（42 套件 + r72 + f0 + 3 专项），文档按实际执行集合改写。

## 6. D06 与 D07/D08

- §6.2 与 G11/G22 里 8 组函数名按真实定义改写（`cmd_task_approve`、`load_task/save_task`、`cmd_archive`、`cmd_task_retrospect`、`cmd_stop` 在 `cli.py` 等），并写了一个 AST 校验脚本对全稿 `wflib/<mod>.py::sym` 逐个核对，当前 **missing: none**。
- 脱敏补 `Authorization: Bearer <值>` 与 `--token <值>` 分离写法（`redact_argv()`），用虚构值验证日志/facts/命令记录均被遮罩。
- 删除无消费者的 `check._decision_index()`。

## 7. 未覆盖轴（如实登记）

1. **上位文件历次授权的批准链**：本轮只能证明四份摘要匹配、相对 HEAD 无差异；"每次语义修改都在批准范围内"需要逐次批准记录，材料不在本轮范围。
2. **历史实跑声明的原始记录**：强杀恢复、宿主身份、异种 reviewer 等声明的原始日志未随本轮材料提供；不以本轮回归通过追认，维持原有登记。

因此 frontmatter 状态写「**按已覆盖轴定稿**」，并在其中列明未覆盖轴，不整体称验收完成。

## 8. 期间新发现

- **N-R66**：删 `_decision_index` 时把紧随其后的 `SECRET_PATTERNS` 一起删了，导致 `task-check` 内部错误 70（exit 70）。全量回归暴露后恢复并复验脱敏。教训：批量删除函数要按 AST/边界而非下一个 `def` 定位。
- **N-R67**：`disposed` 加强后 V3 的"按登记终态原样提交"被误判——dev-deploy 回执含 `.gitignore`，而证据提交只覆盖安装组。改为「提交内匹配 **或** 当前态匹配且无未提交差异」，兼容拆分提交。
- **N-R68**：r67 的假套件环境未跟上新入口（缺 `p5_f0.py`、缺发行仓库桩），补桩后通过。
