# 设计：wf 第二轮能力与收口遗留（11-12-wf-round2）

> 判据源（只读）：`docs/workflows/wf-framework-{charter,design,mechanism,implementation}.md`。
> 本文件只写**本轮怎么做**：能力边界、签名、记录字段、错误码、落点与测试策略；
> 不重述状态机、不新增判据。与上位文件冲突按 charter T1 出「需人裁决」，不改上位。
> **核心约束**：指导 AI 而不是限制 AI（见 §7「机制 vs 指引」，本节是人工审查重点）。

---

## 0. 结论先行

| 项 | 结论 | 依据 |
|---|---|---|
| `task-rework` 的「权威冲突」 | **不存在冲突**，按机制稿 §6.2 交付实现 | v42（`solution-review-v42.md`，与 `/tmp/wf-solution-review-2026-11-09.md` 字节相同）全文 `task-rework` **0 次**、`必须删除` **0 次**；实现稿 §2.3:260 把它列为**第二轮交付项**；机制稿 §6.2/§6.3 有完整机制；设计稿 §5.6 承诺该能力；`payload/workflows/instance-flow.md:36` 声明 `control.task.rework [required]` 且部署自检要求 handler 存在（`install.py:520-522`、`gates.py:304`）。2026-11-09 的 A/B/C 裁定请求已在归档任务 `11-09-wf-v42-control-flow-repair/rework-conflict.md` 中自我更正为「误判出处、无需裁定」；`cli.py:2632-2634` 的注释是那次误判的残留，本轮**只订正注释出处**，不动任何判据 |
| P2 与 P1 的先后 | **P2 先、P1 后**（人裁，2026-11-12） | P2 每项都有现成登记位置与判据，小且可验证；P1 的 `definition`/`run` 需新增 schema 与新代码，放后更易保证已交付部分全绿 |
| 新增原因码 / 状态值 / 判定字段 / 开关 / 入口 | **零新增** | 36 码已覆盖本轮（`WF_DEFINITION_INVALID`、`WF_DEPENDENCY_UNMET`、`WF_SCOPE_UNRESOLVED`、`WF_CAPABILITY_UNAVAILABLE` 等均已登记）；`run_id`/`rework_of`/`successor_id`/`independent_resume` 已在机制稿 §1.3 与 `templates/task/task-record.json` 登记 |

---

## 1. 能力边界

### 1.1 P1：第二轮能力（七项）

| # | 能力 | 做什么 | **不做什么**（越界即停） |
|---|---|---|---|
| 1 | `definition prepare/validate` | 解析 `.wf/user-workflows/<id>.md` 的 `<!-- wf-definition:v1 -->` + 紧邻 `json` 块；按机制稿 §7.2 的固定顺序做静态校验；准备记录（`scope_paths`/`authorization`/`validation`/`progress`/`wip`/`ended_at`）落盘 | 不求值 Markdown/输入；不要求未来产物已存在；不把 `completion` 的自然语言判真；不新增定义字段 |
| 2 | `run create/advance/pause/locate/terminate` | 实例记录（机制稿 §1.5 全部字段）落盘、快照固定、`task_map`/`sequence_changes`/`step_results`/`cursor` 推进；首达 task 步骤时建任务并写顺序边 | 不代调任务阶段的批准/Check/归档（那是人的动作）；不复制 task 的 status/Check 进实例记录；不实现 migrate/upgrade |
| 3 | 步骤人判与略过 | 略过在生成任务**前**处理 `skip.decision_point`，答复与决定存 `step_results`（`kind=skipped`）；`human` 步骤只记文本决定 | 不为保存答复强建任务；口头略过不放宽框架 `required` 门禁；把必要测试编码成可略动作 |
| 4 | `dep add/rm` | 两端存在性、自环/环（DFS 三色）、两端活动区校验后落边；删边只改未归档持有侧 | 不新建依赖账本；不把未知当依赖满足；不做跨项目依赖（charter T3） |
| 5 | `task-rework` / `task-replace` | 按机制稿 §6.2/§6.3 在 `T.action` 内登记完整候选后落盘；返工集合与复评条件由记录重建 | 不让 R 消费 T 的批准；不把 R 归档当原步骤完成；不做嵌套工作流 |
| 6 | `task-reassess` | 复评条件逐条核（未归档 ∧ 挂起 ∧ 集合非空 ∧ 集合无未归档成员 ∧ 前置满足 ∧ 跨记录动作已恢复），满足则清 `suspended`（保留 `paused`） | 不夺权（未持写权只报「待复评」）；不把「读不出」当「没有」 |
| 7 | `inspect` 两项治理输出 | 「需人工比对」清单（`witnessed`/`potential`，机制稿 §8.5 三步算法）+ `author` 复核顺序；`governance_omitted` 同批删去这两类 | 不判定语义矛盾；不按预算静默删候选；不把「列入清单」说成「已清理」 |

### 1.2 P1 同批：`.wf/out-of-scope/` 知识拒绝项

四项启用前置一次打勾（设计稿 §6.3、机制稿 §8.4 末段）：

1. **写入者**：`spec-update` 的 `changes` 支持目标落 `.wf/out-of-scope/<concept>.md`，按 schema 建文件；
2. **重提追加**：同 concept 已存在则向 `## 既往请求` 追加一行，**不新建文件**；
3. **路径放行**：`.wf/out-of-scope/**` 进 `paths.WRITE_TARGET_PREFIXES` 与 `protocol/project_data.json` 的 `prefixes`（唯一声明处）；
4. **消费者**：`inspect` 的治理面增加「重复登记核对」（同 concept 多文件）；知识处置入口（`task-knowledge` 的 facts）能引用拒绝项。

**不做什么**：不新增命令（写入走既有 `spec-update`）；不新增原因码；不把「临时困难」写进拒绝项（那属 `task.handoff.pending`）。

### 1.3 P2：第一轮遗留债（13 项，非新能力）

**计数订正**：PRD §4 文字写「P2 的 12 项」，但其枚举（含末句「以及 `cli.py` 无锚点出口文案」）实际是 **13 项**；本文件以 13 项逐条落地，并在实现稿登记该计数差异（不改 PRD 判据）。

逐项表见 §5。

---

## 2. 命令与函数签名

### 2.1 新增/解封的命令面（全部沿用实现稿 §2.3 已登记形态）

| 命令 | argv | facts 关键字段 | 失败码 |
|---|---|---|---|
| `definition prepare` | `--id <workflow-id>`（信封必需） | `{definition: {workflow_id, path, digest, content_version}, validation, pending}` | `WF_PATH_INVALID`（id/路径非法）、`WF_DEFINITION_INVALID`（已有校验问题）、`WF_ACTION_INCOMPLETE`（未完成动作） |
| `definition validate` | `--id <workflow-id>` | `{problems: [{location, reason}], ok}` | `WF_DEFINITION_INVALID`（问题非空） |
| `run create` | `--creation <path>` | `{run: {id, workflow_id, digest}, task, binding}` | `WF_SEMANTIC_DECISION`（输入/展开未确认）、`WF_TARGET_COLLISION`（run/快照/绑定目标）、`WF_APPROVAL_MISSING`、`WF_DEFINITION_INVALID` |
| `run advance` | `--run <id> [--decision <path>]` | `{run, cursor, step_result, task, edges}` | `WF_BINDING_MISMATCH`、`WF_DEPENDENCY_UNMET`、`WF_VERIFICATION_UNREADY`、`WF_ACTION_INCOMPLETE` |
| `run pause` | `--run <id> --reason <text>` | `{run, paused: true, reason}` | `WF_SEMANTIC_DECISION`（已终态/已暂停） |
| `run locate` | `--run <id>`（只读） | `{run, cursor, tasks}` | `WF_TARGET_MISSING`（无此实例） |
| `run terminate` | `--run <id> --plan <path>`（信封） | `{run, closing, dispositions}` | `WF_SEMANTIC_DECISION`（计划不全）、`WF_WORKSPACE_UNRESOLVED`（改动未落实） |
| `dep add\|rm` | `--task <id> --prereq <id>` | `{edge: {task, prereq}, prerequisites}` | `WF_DEPENDENCY_UNMET`（环/自环/已归档端）、`WF_TARGET_MISSING`、`WF_HISTORY_UNRESOLVED` |
| `task-rework` | `--task <id> --decision <path>` | `{rework: R, suspended: T, candidates}` | `WF_SEMANTIC_DECISION`（决定不成立/图非法）、`WF_TARGET_COLLISION`、`WF_ACTION_INCOMPLETE` |
| `task-replace` | `--task <id> --decision <path>` | `{successor: S, inherited, terminal: T}` | 同上 + `WF_APPROVAL_MISSING`（S 未自批） |
| `task-reassess` | `--task <id>`（已存在，本轮改实现） | `{suspended_tasks, reassessed, waiting, applied}` | `WF_WRITER_BUSY`（未持写权时只报待复评，不算失败）、`WF_HISTORY_UNRESOLVED` |

### 2.2 模块落点

| 模块 | 现状 | 本轮 |
|---|---|---|
| `lib/wflib/runs.py` | 57 行，全部 `CapabilityUnavailable` | 实装 `load_definition/validate/prepare/create/advance/pause/locate/terminate/finish` |
| `lib/wflib/tasks.py` | 依赖只到「单任务放弃」 | 新增 `cmd_dep`、`cmd_task_rework`、`cmd_task_replace`；重写 `cmd_task_reassess`、`_inspection_hint`；`_governance_summary` 增两类输出与重复登记核对 |
| `lib/wflib/paths.py` | `WRITE_TARGET_PREFIXES = (".wf/spec/",)` | 追加 `.wf/out-of-scope/`（唯一声明处） |
| `payload/protocol/project_data.json` | 前缀三项目 | 追加 `.wf/out-of-scope/` |
| `lib/wflib/cli.py` | `dep`/`definition`/`run`/`task-rework`/`task-replace` 均 `_unavailable(2, …)` | 换成真实处理器；订正无锚点出口文案（P2-13） |
| `lib/wflib/spec.py` | `_resume_decision*` 只在续做分支调用 | 首跑也核前像（P2-2） |
| `install.py` | `self_check` 不解析 SKILL frontmatter | 增投放后 frontmatter 解析（P2-4） |

**复用纪律**（同一判定只允许一处实现）：

- 独立接续资格 → `cli._eligible_task_bind`（`ready`/`bind`/`run advance` 共用）；
- 门禁评估 → `gates.evaluate` / `gates.final_gate_nonstep`；
- 路径边界 → `paths.boundary_violation` / `paths.write_target_allowed`；
- glob 前缀不相交 → `paths.literal_prefix` / `paths.provably_disjoint`；
- 巡检到点 → `tasks._inspection_facts`（本轮提取，`inspect` 与归档提示共用）。

---

## 3. 记录字段

### 3.1 `.wf/workflow-runs/<run-id>.json`（机制稿 §1.5，字段不新增）

```json
{
  "schema_version": 1,
  "id": "<run-id>",
  "workflow_id": "<局部 id>",
  "definition": {"workflow_id": "…", "content_version": 1, "format_version": 1,
                  "snapshot_path": ".wf/workflow-runs/<run-id>/definition.md", "digest": "sha256:…"},
  "inputs": {"<name>": "<value 或引用对象>"},
  "creation_decision": {"source": "human", "at": "…", "steps": [...], "expansion": "…"},
  "cursor": {"step_id": "…", "task_id": "…|null"},
  "step_results": {"<step-id>": {"kind": "satisfied|skipped|not_executed", "at": "…", "task_id": "…",
                                  "outputs": [...], "decision": {...}}},
  "task_map": {"<step-id>": {"task_id": "…", "predecessors": ["…"], "superseded_ids": []}},
  "sequence_changes": [{"kind": "rework|replace", "step_id": "…", "source_task": "…",
                         "task_id": "…", "resume_task": "…", "decision": "…"}],
  "pending": null,
  "paused": false,
  "closing": null,
  "terminal": null,
  "ended_at": null
}
```

- 快照落 `.wf/workflow-runs/<run-id>/definition.md`（原字节），digest 覆盖完整文件；
- 未知字段读写保留（`records.merge_unknown` 同源口径）；
- `step_results` 的 `kind` 只取三值；任务步骤只存 task 引用与本次消费摘要。

### 3.2 任务记录：只用已登记字段

`rework_of`、`successor_id`、`prerequisites`、`suspended`、`paused`、`run_id`、`independent_resume`、`handoff`、`action` 均已在 `templates/task/task-record.json` 与机制稿 §1.3 登记；本轮**不新增**任何字段。

### 3.3 `.wf/out-of-scope/<concept>.md`

```markdown
---
concept: "<稳定概念名，与文件名一致>"
reason: "<非空：为什么拒绝>"
reconsider_when: "<非空：什么条件下可重议>"
status: "active|disabled"        # 复用 spec.py 受限 frontmatter 的 `key: <JSON值>` 形式
---

# <概念名>

## 既往请求
- 2026-11-12 ｜ <请求摘要> ｜ <结论或裁决引用>
```

**唯一写入路径**：`spec-update --changes` 的 `{operation: add|modify|modify-append, old_paths, new_paths, content}`：
新增走 `add`；重提追加走 `modify-append`（只允许该目录、只允许向 `## 既往请求` 追加一行，不重写正文）。
校验（写入前整批、零写入失败）：`concept` 与文件名一致、`reason`/`reconsider_when` 非空、`## 既往请求` 段存在、
同一 concept 在目录内只有一份文件（多份交 `inspect` 报重复登记并由人处置）。

---

## 4. `inspect` 治理输出形状

```json
"governance": {
  "manual_compare": {
    "witnessed": [{"pair": ["a.md", "b.md"], "paths": [".wf/spec/a.md", ".wf/spec/b.md"],
                    "patterns": [["src/**", "src/api/**"]], "witnesses": ["src/api/x.py"],
                    "class": "witnessed", "label": "已证实交集"}],
    "potential": [{"pair": ["c.md", "d.md"], "unexcluded": [["src/**", "**/*.md"]],
                    "basis": "前缀检查不能排除、无当前路径见证", "class": "potential",
                    "label": "待核实的潜在交集"}],
    "unverified": [{"reason": "spec 无可解析 paths|路径越界|读取失败", "path": "…"}],
    "counts": {"witnessed": 1, "potential": 1, "candidates": 2, "unexpanded": 0},
    "scan": {"root": "项目根", "spec_files": 12, "repo_paths_scanned": 340}
  },
  "author_order": [
    {"path": ".wf/spec/x.md", "author": "ai", "verified_at": "extracted", "reason": "extracted 且 author=ai"},
    {"path": ".wf/spec/y.md", "author": "human", "verified_at": "extracted", "reason": "extracted 且 author=human"}
  ],
  "out_of_scope_duplicates": [{"concept": "x", "files": [".wf/out-of-scope/x.md", ".wf/out-of-scope/x-2.md"]}]
}
```

- `governance_omitted` 本轮**删去** `manual_compare` 与 `author_order` 两条；若某项本轮仍无法给出结论
  （样本/读取问题），不写进 `governance_omitted`，而是写进该输出的 `unverified`/`unknown` 字段
  （未知不当零）——即交付后不存在「未声明且未输出」的类别。
- 排序固定：`author_order` 先 `verified_at=extracted` 再日期，其次 `author=ai` 先于 `human`，最后按路径稳定排序。
- `manual_compare` 不判语义矛盾（机制稿 §8.5 末段）：只给事实与分类。

---

## 5. P2 逐项表（判据 / 现状 / 改哪里 / 验收）

| # | 项 | 判据 | 现状（已核） | 改哪里 | 验收 |
|---|---|---|---|---|---|
| 1 | `d` 档判定 | 机制稿 §3.5 分类 d)「归属语义存疑 → `WF_SCOPE_UNRESOLVED`」；§3.5「首轮实现覆盖」要求第二轮引入「已提交但归属不可解析」 | `scope.classify_candidates` 的 `owned = attributed ∪ 命中触碰面`，故 `¬owned ∧ ¬uncommitted` 恒假，**d 恒空**；消费端 `check.run_check` 已判 `buckets["d"]` → `WF_SCOPE_UNRESOLVED` | `scope.classify_candidates`：`owned` 收敛为「有归属证据」，把「命中批准面但被另一任务 `handoff.wip` 显式登记 / 归属裁决冲突」的路径归 `d`（不改变 c/e/f 语义与顺序） | 新增单测：路径命中触碰面且被他任务 WIP 显式登记 → `d` 且 `check` 报 `WF_SCOPE_UNRESOLVED`；注入=恢复旧 `owned` → 红 |
| 2 | `spec-update` 首跑核前像 | 机制稿 §5.2 三态（前像→应用；本动作后像→跳过；都不符→冲突）对**所有**写入生效；实现稿 §2.3.11 未做项 | `_resume_decision*` 只在 `resume=True` 调用；首跑直接 `atomic_write` | `spec.apply_changes` 的整批校验段：首跑也逐条核 `before_digests`；不符即 `WF_SEMANTIC_DECISION` 且零写入 | 单测：首跑时目标内容已变 → `WF_SEMANTIC_DECISION` + 零写入；注入=跳过首跑前像核 → 红 |
| 3 | `ready` 分实例 | 机制稿 §6.1 独立接续资格「所有入口共用」；实现稿 §2.3.11「仍未做：`ready` 不区分…实例归组」 | `cmd_ready` 只列任务，无 `run_id` 归组；**子仓库归组属 charter T3 B2 硬边界，不做** | `cmd_ready`：facts 增 `runs: [{run_id, workflow_id, terminal, tasks: [...]}]`，`tasks[].blockers` 增 `run_in_flight`（在途实例且非保留） | 单测：在途实例任务不 ready、保留任务按许可 ready；注入=忽略 run 归组 → 红 |
| 4 | 自检解析 SKILL frontmatter | 设计稿 §1.2「frontmatter 可解析」；实现稿 §2.3.11「安装自检不核 skill frontmatter」 | `self_check` 只核摘要/运行时/步骤/桩轮次 | `install.py::self_check`：对每个投放的 `SKILL.md` 解析 frontmatter（`name`/`description` 非空、可解析），问题入 `problems` | `repro` 注入=去掉解析 → 红；绿=投放后自检通过 |
| 5 | 巡检提示接 `inspection_every_tasks` | 机制稿 §8.5：按**正常归档**的 `(archived_at, id)` 累计，异常归档不计也不重置，配置键非法即未知 | `_inspection_hint` 硬编码 `every = 10` 且数**全部**归档（含异常、含坏记录）；`_governance_summary` 已实现同一判定 | `_inspection_hint(ctx)` 改为直接复用 `_governance_summary` 的 `inspection`（不另提函数：不复制算法就不会漂移）。**同批修正**：`inspection.due` 原先被整张 `unknown` 列表压成 `null`，其中混着知识回收窗口的样本不足/路径失联 → 年轻项目永远不到点；改为只由「归档记录不完整 / `inspection_every_tasks` 非法」压制 | 单测：`every=2` + 2 正常 + 3 异常 → 到点；仅异常 → 不到点；键非法 → `unknown`（硬编码 10 会给出 False）；既有 `r76`/`r77` 断言不变 |
| 6 | `task-check` 验证执行移出锁 | 机制稿 §4.1「长操作不长期持 OS 锁」；实现稿 §2.3.11 未做项 | `cmd_task_check` 的 `lock.acquire` 覆盖 `run_check` 全程（含 `subprocess.run`） | `run_check` 拆三段：锁内 `scope+resolve+锚点` → **锁外执行命令** → 锁内重核 holder/代次 + **重算锚点**（不等即 `WF_CHECK_STALE`）+ 既有扫描前后比对 → 写 check。**不新增判定字段**（口径 A：不把 `writer.checkpoint` 升格为稳定性判据、不给 `writer.json` 加摘要字段——那需先回机制稿 §1.4 登记） | 单测 3 例：执行段期间别的会话可取得项目锁；锁外期间内容变化被既有比对挡住；`cmd_task_check` 恰好两段锁且调用顺序为 scope → execute → 二次取锁 → finish |
| 7 | Decision 取值域统一 | 机制稿 §1.1 只定 `Decision` 结构，取值域按操作登记在实现稿 §2.3；§2.3.11 ①「不得据同义词新增语义分支」 | `tasks.APPROVE_CHOICES`、`check.EXTERNAL_CHECKED_CHOICES` 四值、`cmd_archive` 的 `("finish","完成","pass")`、`debug-ruling` 两值、收工四值、提交授权、验收结论三值——七处各写字面量 | **`wflib/decisions.py::DOMAINS`（9 个操作）+ `accepts`/`canonical`**；七处调用点改为引用。**落地偏离原设计**：不新增 `protocol/decisions.json`——`protocol/` 是发行清单资产，新增文件要同批改 `dev-manifest.json` 与资产表，收益不抵风险；语义权属仍在机制稿/实现稿，本模块只放「已接受的写法」 | 单测：正名被接受、未登记同义词被拒、`accepts` 未登记域要抛错（不允许「域拼错就全放行」）；原七处与登记表**同源**（断言 `APPROVE_CHOICES`/`EXTERNAL_CHECKED_CHOICES`/`MECHANICAL_REVISION` 与登记表相等） |
| 8 | `project_key` 语义级键值解析 | 机制稿 §3.4 末段「首次写入须在批准 PRD/基线提案逐项列键和值」 | 判定在**引导层** `bin/wf.py::project_key_approved`：`"python_executable" in text and value in text`（键与值可各在一处） | `bin/wf.py::project_key_approved`：逐行解析 `key = value` / `"key": "value"` 形态，要求**同一条目**键值成对；`wflib/config.py::project_python_key` 无调用方（死代码），只登记不删 | 复用 `repro/executor-approval-chain.py` 语义 + 新增单测：PRD 里键与值分处两行 → 不通过；注入=退回子串匹配 → 红 |
| 9 | `_apply_debug_inputs` 幂等键 | 机制稿 §1.3「每声明只存最终结果」；实现稿 §2.3.11 ④ | 同一决定文件重入会重复 append 声明 | `_apply_debug_inputs`：以 `(verification_id, counted, evidence_refs, dedupe_refs)` 为幂等键，已存在则跳过（不新增字段） | 单测：同一决定文件连跑两次，`debug_declarations` 长度不变；注入=去掉幂等键 → 红 |
| 10 | start 期验证证据入 action | 机制稿 §5.1「动作内固定后置」；实现稿 §2.3.11 ⑥ | `_run_start_verifications` 结果只进命令 facts | `cmd_task_start` 把结果并入该动作 steps 的后置核验（`inputs["start_verifications"]`），结案前按真实后置复核 | 单测：`consume_at=start` 命令通过后 action 内含证据；注入=不入 action → 红 |
| 11 | D08 依赖/实例目标碰撞 | 机制稿 §5.1 幂等键、§6.1 候选图；实现稿 §6.2 D08「第二轮加入全部依赖/实例目标」 | 碰撞预检在 `task-new`/`archive`/`task-abandon`/`spec` 就地判定；`dep`/`run` 的动作 targets 不含依赖/实例目标 | `cmd_dep` 与 `run create/advance` 的 `new_action(targets=…)` 覆盖「两端任务记录 + 实例记录 + 快照路径」，并走既有 `WF_TARGET_COLLISION` 判定 | 单测：同一目标被两动作覆盖 → `WF_TARGET_COLLISION`；注入=targets 置空 → 红 |
| 12 | R93 注入式双模反例 | charter T4 等效替换「须有最近正反例」；`denominator.md:164` 登记「R93 身份入口替换只有 r90 套件 9/9，缺注入式双模反例」 | `r90_tests.py` 只有正向断言 | 新增 `repro/identity-platform-fact.py`：绿=未安装宿主写操作被拒、只读放行；红=注入「不看 platforms 直接放行」 | 双模跑：`WF_REPRO_INJECT=0` 绿、`=1` 红 |
| 13 | `cli.py` 无锚点出口文案 | 机制稿 §1.4：显式 `provider=wf` 信封一律 `WF_IDENTITY_UNRESOLVED`，只有 `provider=host`（宿主提供 `session_id`）可用 | 4 处出口写「用显式信封（--envelope/stdin）」，与 `session.check_platforms` 的拒绝矛盾（`cli.py:190/325/362/919`） | 4 处文案改为「换到能提供宿主会话标识的终端形态，或以 `provider=host` 的显式信封（`identity.host_id`+`session_id`）提交」 | 单测/文本断言：4 处不再出现无条件的「用显式信封」；注入=保留旧文案 → 红 |

---

## 6. 测试策略

- **双模约定**（沿用现有 `repro/_harness.py`）：`WF_REPRO_INJECT=0` 绿、`=1` 红；红必须是「注入缺陷后才失败」，
  不允许「本来就失败」。
- 层级选择：能用单元测试表达判定的用 `scripts/tests/wf_runtime/test_*.py`（快、无夹具）；
  需要真实 Git/部署/信封的（P2-4、P2-12、P1 的 `run`/`definition` 端到端）用 `repro/*.py`。
- 每条断言必须能回答「它防的失败真实存在吗」（v42 §6 元规则）；历史缺陷回归以条目标记。
- 全量门禁见 `implement.md` §4；**验证结论必须来自在待提交内容上的实跑**。

---

## 7. 机制 vs 指引（人工审查重点）

判据句式：一条规则若要求 AI「理解 / 判断 / 择优 / 表述」→ **只能是指引**，机制侧只提供它需要的事实；
若要求「阻止 / 校验 / 记录 / 失效」→ **才写成机制**。

### 7.1 P1 逐项

| 能力 | 机制（代码唯一实现） | 指引（skill/文档的判断口径 + 事实输入） | 载体 |
|---|---|---|---|
| `definition validate` | schema/`format_version`、id 唯一与保留前缀（`plan-q-`/`debug-ruling-`）、引用来源与顺序、路径合法性、required/skip 与 downstream 一致性、验证声明三要素（建立者/落点/首个消费时点） | **用途与适用性是否写清**、`completion` 的条件是否真的覆盖目标、某个 `skip.condition` 是否该被认可——都是人的文本判断，机制只核非空 | `skills/wf-bootstrap` + `workflows/definition-flow.md`；机制：`runs.validate` |
| `run advance` | cursor/`task_map`/`sequence_changes` 的读写、顺序边的直接前驱唯一性、同一步骤不建第二份任务、人判答复与 `skip` 决定落 `step_results` | **前序产物够不够用**、能否记「复用」、某动作是否算完成——AI 判断并留依据；机制只核「任务归档持久化可核」这个事实 | `skills/wf-continue`；机制：`runs.advance` |
| 步骤人判与略过 | `skip` 必须引用已声明的 `decision_point` 且答复已存；必需步骤不受 `skip` 影响；下游替代映射静态可核 | 人答复什么、替代是否真等价——人的判断；机制只核「有答复 + 引用成立」 | `skills/wf-continue`；机制：`runs.advance` |
| `dep` | 自环/环 DFS、两端存在且在活动区、前置未归档、删边只改持有侧 | **该不该加这条前置**（业务上的顺序是否真必要）——人的取舍 | `skills/wf-continue` |
| `task-rework` / `task-replace` | 候选图预检、`rework_of`/`successor_id` 记录、`suspended`/`paused` 标记、R 不得消费 T 的批准、异常归档 T 的终态 | **缺陷是否成立、范围该多大、值不值得返工/替换**——人裁（决定文件承载）；机制不判「该不该修」 | `skills/wf-repair-loop` + `skills/wf-continue` |
| `task-reassess` | 五条件逐条核（含「集合无未归档成员」「前置满足」「跨记录动作已恢复」）、清 `suspended` 保留 `paused`、未持写权只报待复评 | **其他前置是否仍必要**、是否该趁机重排——AI 解释、人决定 | `skills/wf-continue` |
| `inspect` 两项治理输出 | spec 路径对去重、`witnessed`/`potential` 分类（§8.5 三步算法）、`author` 顺序（`extracted` 前置、`ai` 优先）、`unverified` 单列、计数与扫描范围 | **两份 spec 的正文是否语义矛盾**——只交人对照正文；机制不产出「疑似冲突」结论 | `skills/wf-spec-update`（巡检解读段） |
| `.wf/out-of-scope/` | schema 校验（`concept`/`reason`/`reconsider_when` 非空、文件名一致）、`## 既往请求` 追加形态、路径白名单、重复登记检测 | **什么算「已拒绝」、何时可重议**——人裁；机制只保证写下来的拒绝项可被检索与核对 | `skills/wf-spec-update` |

### 7.2 P2 逐项（只列有判断成分的）

| 项 | 机制侧最小必要判定 | 指引侧 |
|---|---|---|
| P2-1 `d` 档 | 只判「有归属证据 / 无归属证据 / 归属证据冲突」——纯事实比对（trailer、裁决、他任务 WIP 登记） | 归属冲突由人裁决；机制给双方事实与出口 |
| P2-3 `ready` 归组 | 只出 `runs[]` 与 `run_in_flight` 事实 | 「先做哪个」由人/AI 选；机制不排序 |
| P2-5 巡检到点 | 只算「正常归档累计是否为 `every` 整数倍」 | 巡检该看什么、要不要现在做——人决定 |
| P2-6 执行移出锁 | 只把长操作移出临界区，并保留锁内锚点重核；**不新增字段、不升格 checkpoint** | —（纯实现结构；「锁外期间对象被改」沿用既有锚点与扫描比对判据，不由机制新造） |
| P2-8 键值解析 | 只核「同一条目内键值成对」 | 该值是「批准的解释器」还是「举例」——人的判断 |
| P2-9 幂等键 | 只按结构化字段去重 | 重复声明是否同一事件——人裁定（`dedupe_refs`） |

### 7.3 反例警戒（本轮不得回退的形态）

- 不得把「返工是否值得」「spec 是否语义矛盾」「归属该算谁的」编码成规则表（v42 §7.1 的「已删除机制」清单：归属优先级 10 行表、`covers` 形态表、`fix_scope` 上限数值等）；
- 每个新增机制必须回答：**它防的失败现在由谁覆盖、那个覆盖在什么场景失效**（v42 §7.1 使用方式）；答不出的不加；
- 机制只出现在「不可观察 / 不可逆 / 跨会话一致 / 可伪造的声明 / 需审计留痕」五类上。

---

## 8. 风险与回滚

| 风险 | 应对 |
|---|---|
| `definition`/`run` 引入大量新代码，可能与既有锁/动作模型冲突 | 全部复用 `_start_task_action`/`_finish_task_action`/`lock.acquire`/`actions.*`；不新起写入协议 |
| P2-6 拆 `run_check` 可能改变既有 Check 语义 | 拆前后对既有失败场景逐字段等价（沿用 `test_repair_scope` 的等价断言方式）；不等价即回滚该批 |
| P2-7 集中取值域可能拒绝历史决定文件 | 正名（现有实现接受的**全部**取值）保留为登记值；只拒绝「未登记」的新词，不拒绝历史上已被接受的词 |
| 发行树重建 | 每次改 payload/skills 后 `scripts/build-wf-release.py --version 0.1.0` 并提交发行树 diff；`--verify` 必须字节复现 |
| 回滚点 | 每批一次提交，批内失败用 `git checkout -- <本批路径>` 回到上一批（不 `reset --hard`、不 `stash` 遗留） |
