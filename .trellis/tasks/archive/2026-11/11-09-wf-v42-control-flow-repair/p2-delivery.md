# P2 交付记录（第一片：K3a 核实 + K3b 锚点面 + 额度删除）

## 1. 本轮改动（文件 → 动机 → 编号）

| 文件 | 动机 | 编号 |
|---|---|---|
| `wf-framework-mechanism.md` §8.3 | 增 spec 规则字段 `check` 与 `clauses[]`（只增不改、active/deprecated、`deprecated_summary ≤80`、digest 只算 active） | K3b |
| `wf-framework-mechanism.md` §3.5 | check 记录增 `anchor.parts`（失配时列差异的第二端；旧记录 null → `diff_unavailable`，不得反推） | K3b |
| `wf-framework-mechanism.md` §9.1/§9.2 | 删除两轮额度；dispositions 定字段 `{finding_id, decision, reason, evidence_refs, follow_up, recheck_by, at}` 并要求 `recheck_by` 非提出者 | 阻断 005、K4b |
| `wf-framework-design.md` §4.3/§6.5 | 同步「不设轮次上限」 | 阻断 005 |
| `wf-framework-mechanism.md` §0.1 | 记录本次人裁并更新设计稿摘要 | T7.2 |
| `payload/lib/wflib/review.py` | 删 `len(used) >= 2` 的额度拒绝（`round_ids` 只作观察） | 阻断 005 |
| `payload/lib/wflib/check.py` | check 记录写 `anchor.parts`；新增 `assertions_digest` 并进锚点；`spec_versions` 的摘要改为「实质摘要优先、无实质字段退回整文件」 | K3b |
| `payload/lib/wflib/spec.py` | 校验 `check` / `clauses`（id 唯一、status 枚举、deprecated 必填摘要且 ≤80）；新增 `rule_digest` | K3b |
| `scripts/tests/wf_review/test_assertions_digest.py` | 4 条：排版不计、check/clause 变化必变、无实质字段无摘要、clause schema 负例 | K3b |

## 2. 验证

| 命令 | 结果 |
|---|---|
| `unittest discover` | **105 tests OK**（101 → 105） |
| `build-wf-release.py --verify` | **OK** byte reproduction（63 assets） |
| `validate-wf-design.py` | **OK** 定义 100% / 消费 100% / 输入摘要 4/4 / 二值 91/91 / 三档 13/13 |
| `check-doc-refs.py` | **0 problem(s)** |
| `wf-protocol-docs.py --check` | **OK** 35 码 / 16 配置键 / 11 转移 |

## 3. 勘察结论里已确认「本来就有」的

- K3a 内容锚点：`anchor_parts` 的 `content_digest`/`paths_digest`/`plan_version`/`entry_snapshot_digest`/`acceptance_digest`；`import` 核锚点，不符即 `WF_REVIEW_INVALID`。
- K4a 报告不可覆盖：同路径不同摘要 → `WF_REVIEW_INVALID`，同摘要幂等；机制稿 §9.2 亦写明"旧轮次路径永不覆写"。**缺自动化用例**（待补）。

## 3.5 第二片：引用校验 / 漂移差异 / 关闭不自证（本轮同批）

| 位点 | 改动 |
|---|---|
| `review.py::assertion_index` | 当前批准集合 = 验收项 id + 验证 id + 参与 spec 的路径与 `path#clause-id`；同时算出**本任务内被改过的规则**（策展记录里的摘要是"选用时"快照，与当前实质摘要不同即改过） |
| `review.py::assertion_ref_problem` | 单条引用判定：不属集合 → 拒；指向本任务改过的规则 → 拒（K4c）；声明 `check_fix_kind=broken-reference` 时解除该禁令 |
| `review.py::dispositions_problems` | disposition 结构（`decision` 枚举、`reason` 必填）+ **关闭不得自证**（`recheck_by` 必填且 ≠ 提出者；`human:<来源>` 允许） |
| `review.py::anchor_drift` | 锚点差异（只比实质字段，`d:<key>` 形式）；旧记录无 `parts` → `diff_unavailable`，不反推 |
| `import_report` | 锚点失配时**列出差异**；`findings[].assertion_ref` 逐条校验（blocking finding 必须带引用） |
| `decide` | dispositions 改用纯函数校验并拒绝；错误里带提出者映射与两条出口 |
| `scripts/tests/wf_review/test_review_gates.py` | 10 条：引用属集合/不属集合/规则自证/`broken-reference` 解除、关闭自证/他人复核/缺字段/人复核、锚点差异/差异不可得 |

验证：`unittest discover` **115 tests OK**；`build-wf-release.py --verify` **OK**（63 assets）。

## 3.6 第三片：`broken-reference` 豁免按裁定 B 落地

| 位点 | 改动 |
|---|---|
| 机制稿 §9.2 | 增「规则不得自证（K4c）」：引用必须属当前批准集合、本任务改过的规则不得当判据、blocking finding 必须带引用；豁免口径写明「声明 + 人复核」且**框架不验证声明真伪** |
| 机制稿 §0.1 | 记录本次人裁（⑤）并更新设计稿摘要 |
| `review.py` import | 声明 `broken-reference` 且指向改过的规则时放行，并把 `{declared, lifted:[{finding, assertion_ref, rule}]}` 写进 `imported` 记录 |
| `review.py::broken_reference_problems` | 纯函数：`lifted` 里每条 finding 必须有 `recheck_by=human:<来源>` 的处置，否则拒绝（两条出口） |
| `review.py` decide | 汇总本轮 `lifted` 并强制上条前置 |
| `scripts/tests/wf_review/test_review_gates.py` | +3 条（无声明不需人、有声明缺人复核被拒、人复核后通过） |
| 裁定记录 | `.trellis/tasks/11-09-.../decision-broken-reference.md` |

验证：`unittest discover` **118 tests OK**；`build-wf-release.py --verify` **OK**；`validate-wf-design.py` **OK**；`check-doc-refs.py` 0；`wf-protocol-docs.py --check` OK。

## 4. 未完成（下一轮）

1. ~~`broken-reference` 豁免口径~~ → 已按裁定 B 落地（声明 + 人复核 + 记录入 `imported`）。
2. **`d:` 只认 active 条目**：属 P3 的 `lint report`／位置校验，随报告协议一起做（`clauses` 已就位）。
3. **K4a 的自动化用例**：行为已在（同路径不同摘要拒绝），缺 CLI 夹具用例。
4. **`standard_drift` 的判定语义**（带 drift 的报告不得产出 pass、只能重发 / escalated 三条路）属 P3 的判断与预览，本轮只落了"差异可列出"。
