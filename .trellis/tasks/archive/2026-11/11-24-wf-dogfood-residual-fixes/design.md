# 技术设计：材料身份 / 启用前置 / 批准摘要

## 0. 约束与总体形状

三条机制共同的不变量是"**结论只对它实际核过的字节成立**"：材料、启用记录、批准决定都必须绑定
它们各自被判定时的那份内容，而不是"当前磁盘上的某个东西"。三条都只加一条判据 + 一个出口，
不新增命令、不新增 skill、不新增层级。

判据句自查（设计稿 §1.1）：三项都满足"可由明确输入稳定算出同一结果"+"有已观察失败（F1/F2/F3 的
dogfood 与源码事实）"+"有消费点（导入/判定门禁、启用前置、批准门禁）"；把它们留成指引都会
继续产生"核了 A、结论却记 B"的等价失败。

## 1. 材料是一个原子身份（F1）

### 1.1 发布原子化

`review.prepare_context` 的 `unmaterialized` 分支（今 `review.py:3315-3317`）改为：

```
staging = <round>/materials.staging-<uuid4().hex[:8]>
os.makedirs(staging)
material_facts = write_materials(..., materials_dir=staging)
manifest = write_materials_manifest(staging, current_check_id, anchor, material_facts)
if os.path.isdir(materials) and not os.listdir(materials): os.rmdir(materials)
os.replace(staging, materials)
```

- 开始时清理同轮的残留 `materials.staging-*`（崩溃遗留，最多一个目录）；`materials/` 本身不被
  `materials_identity_state` 之外的人读。
- 失败路径：`write_materials`/manifest 抛错时删掉本次 staging（`try/except` + `shutil.rmtree`），
  目标目录保持不存在 ⇒ 下次仍是 `unmaterialized`。不再产生"半包"。
- 沿用现有 `records.atomic_write`（单文件原子）与 `write_json`；`os.replace` 只搬一次目录名。
- 只在 `unmaterialized` 分支发布：`fixed`/`legacy_adopted` 仍复用、`drift` 仍拒绝。

### 1.2 身份的定义（唯一实现）

```python
def materials_identity(manifest):
    """轮次材料身份：manifest 的被审 check_id + 逐文件摘要（不含 generated_at/facts）。"""
    body = {"check_id": (manifest or {}).get("check_id"),
            "files": (manifest or {}).get("files") or {}}
    return "sha256:" + records.sha256_hex(records.canonical_bytes(body))
```

排除时间戳的理由：`generated_at`/`adopted_at` 每次物化都变；把时间戳算进身份会让"内容一模一样
的重出材料"也判失配，出口就只剩"开新一轮"。排除 `facts` 同理（`legacy_materials` 由 `state` 另报）。

### 1.3 报告携带身份（骨架 → 校验 → 导入 → 判定）

| 环节 | 改动 |
|---|---|
| 骨架 `report_skeleton` | 协议块增 `"materials": {"identity": <当前身份>}`（空材料时省略该键）；同时把 `facts.materials_check` 改成 `{state, fixed, identity, check_id, current_check_id}`，`fixed` 取 `state == "fixed"`（修 F2c） |
| `report_input_problems` | 新参数 `materials_identity=None`。字段可选（不给不报错，老报告继续通过）；给了必须是带合法 `identity` 的对象，且等于当前身份，否则 `WF_REVIEW_INVALID` + 出口（"恢复原字节 / 换一轮"）。判定复用同一实现（三处同源） |
| `import_report` | 校验通过后把 `payload["materials"]` 原样写进 `entry_record["materials"]`；报告没带时用当前身份补记，并在 facts 标 `materials_unbound: true`。`--restore` 分支保留 `previous["materials"]` |
| `decide` | 对本轮全部 `imported` 条目求 `materials.identity` 集合：任一与当前身份不等 ⇒ 拒绝，facts 给两侧身份 + drift/exit；集合内部不一致同样拒绝（同一轮两份报告必须看同一版材料）。`result.materials` 记**报告绑定**的身份（`{state, identity, check_id}`），当前身份另记 `current` 便于对账 |

`review-context` 的 facts 同时把 `identity` 放进 `materials_check`，让 reviewer 手改报告时有处可抄；
`review-status` 的轮次投影加 `materials_state`（新事实必须在状态页可见，交付纪律 §10 的四自述面）。

### 1.4 出口改造（F1c）

两处 `drift` 出口（`review.py:3288`、`4569`）与 `drift` 判据文档改成三段：

1. **材料改动可接受且报告已导入**：把 manifest 记录的原字节放回文件，再重跑 `review-context`
   （字节一致 ⇒ 身份一致 ⇒ 原报告仍有效）。
2. **要按当前内容重出**：删 `materials/` 下的内容文件**和** `materials-manifest.json`（只删内容不删
   manifest 会停在 `drift`，这是 F1c），重跑 `review-context`；报告须按新材料重写 —— 同轮已登记摘要
   不可覆盖，因此再导入要 `--restore`（身份字段保留）或直接开新一轮。
3. 弱身份（`legacy`/`legacy_adopted`）继续按现场字节采纳，但 facts 必须说"无身份"，不给"fixed"。

## 2. 一套启用前置，写盘之前跑（F2）

### 2.1 抽公共前置

```python
def _enable_guards(ctx, host_id):
    """Trellis 互斥 + 平台可用性（`enable` 与 `--new-session` 共用；只读、不写）。"""
```

内容就是把 `cmd_enable` 现有的 `_trellis_state` 两段判定（`WF_FLOW_CONFLICT` / `WF_SEMANTIC_DECISION`）
与 `session_mod.check_platforms` 搬进来，facts/next 原文不动；`host_id` 由调用方按身份来源给出
（显式信封 `session.identity.host_id`；`host_establish` 的 evidence；`no_session` 与自动模式为 `None`，
与今天的取值一致）。返回 `{"trellis": state, "platform": facts}` 供回显。

### 2.2 调用点与顺序

- `cmd_enable`：解析身份前移到 `_establish_auto_session` **之前**（`_auto_resolve` 只读，可重复调）。
- `_rotate_session`：`unresolved` 之后、绑定/终态/写权/路由写入**之前**；`no_session`/`host_establish`
  子分支（实为首次启用）也跑。
- 失败即命令失败，**不留** `enabled=true` 附件与路由 ⇒ 后续命令仍按 `WF_NOT_ENABLED`（A7）。
- `--identity host` 的钉住与 `identity_facts` 警告留在写后（它们需要 session_key，属事实不属门禁）；
  但 `_rotate_session` 也补同样的身份警告事实，两个入口的自述面一致。

### 2.3 不做的事

不把 Trellis 判定搬进 `require_activation`（那样每次命令都扫其他框架资产）；不做"启用事务回滚"
（前置已前移，正常路径不会再写后拒绝）。

## 3. 正式批准必须覆盖当前 PRD（F3）

- `cmd_task_approve`：`object_digest` 从"非空才比"改为**必填且必须等于当前 `prd_digest`**。
  两条错误分开：缺 → `WF_APPROVAL_MISSING`（带 `expected_prd_digest`）；不等 → 现有
  `does not cover the current PRD` 原文。`subject` 含任务 id 退回次级绑定（保留检查，不再是替代）。
- `_load_decision` 的 `field_notes.object_digest` 与 `COMMAND_HELP["task-approve"]` 同步为"批准必填、
  等于当前 PRD 摘要；`--draft` 预填"。
- 不改 `_mechanical_revision`（它已强制摘要）、不改 `replan`/`archive`/`stop`（各自的摘要口径不同）。

## 4. 指引与 §1.1 表述

| 位置 | 改法 |
|---|---|
| `skills/wf-review-action/SKILL.md:13` | 导入示例补 `--round <n>`，并加一句"恢复较早一轮时必须显式给轮次；缺省取最大发起轮" |
| `review.import_report` 的 "no finished report" 错误 | facts 增 `undecided_rounds`（launches 里未判定的轮次集合）；`next_` 带轮次 |
| `skills/wf-bootstrap/SKILL.md:20` | 删五类清单，只留一句判断 + 指向 `wf-continue`「证据文件纪律」的指针 |
| `skills/wf-continue/SKILL.md:22` | 改"先按快照/提交/WIP 证据判归属；外来走排除声明、本任务交付就继续；只有证据冲突或要决定接管/排除/提交时才问人" |
| 设计稿 §1.1 判据句 | "消费点"改成"改变哪个实际动作、保护哪项已承诺的结果（判定/门禁/留痕/交接）"，并加"只被打印（`facts`/`next`）不算消费点，除非它改变后续动作" |
| 设计稿 §1.1 交人句 | 交人触发点钉在真实决定上（证据冲突、接管/排除/提交他人改动、改承诺/授权、承担残余风险），并写"归属类事实先核后问" |

转写后按维护协议做双向回扫：本批只改措辞，不新增 § 引用，逐条确认索引第 3/5 列无需新增；
`python3 scripts/validate-wf-design.py` 必须全绿（含覆盖率阈值）。

## 5. 兼容与迁移

- 旧报告无 `materials`：可选字段 + `materials_unbound` 事实，不阻断（在途轮不受影响）。
- 旧 manifest 有 `files`：身份照算；`facts.legacy_materials` 已由 `state` 表达，`fixed` 修正只改回显。
- `review-context` 的 `materials_identity` 只作回显，不改材料写入顺序之外的任何判据。
- 不改 `dev-manifest.json`（无新文件）、不改版本号（本任务不发布）。
- 记录字段新增 `reviews.imported[].materials`：机制稿 §9.2 字段表 + §1.1 只读信息字段登记；
  `new_task_record` 的 `reviews` 键已存在，无需改模板。

## 6. 回滚

三项互不依赖，可单独回退；材料身份是唯一涉及记录形状的一项，回退后旧记录多一个 `materials` 键
（读取侧本来就忽略未知键）。回退后必须重跑 T0 + 受影响套件，因为报告协议校验面变了。

## 7. 风险

- **R-1 误报失配**：身份包含 `files` 全量摘要，任何一处日志字节不同都会让老报告失效。缓解：只在
  显式重物化时发生；正常流程同一轮的 manifest 不被重写。
- **R-2 半包清理删错**：`materials.staging-*` 前缀只在轮次目录内，`materials_identity_state` 不读它。
- **R-3 前置前移导致 enable 的 facts 缺失**：`trellis_data`/`platforms` 仍在 facts 里回显，只是
  判定提前；`established` 事实只在真的建立时出现。
- **R-4 批准必填打破夹具**：约 12 处 subject-only 夹具要补 `object_digest`，属机械补齐；补齐后
  `f1_ordinary` 等已有真实摘要的用例不受影响。
