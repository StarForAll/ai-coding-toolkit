# P2 勘察：K3a/K3b/K4a/K4b/K4c 的现状与阻断

## 1. 现状（读代码 + 读机制稿核实）

| 项 | 现状 | 结论 |
|---|---|---|
| K3a 内容锚点 | `check.anchor_parts` 含 `content_digest`（`fingerprint.items` 逐路径内容）、`paths_digest`、`plan_version`、`entry_snapshot_digest`、`acceptance_digest` 等；`import_report` 核 `report.check-anchor == 当前 anchor`，不符即 `WF_REVIEW_INVALID` | **已实现** |
| K3b 标准锚点 | 锚点有 `spec_versions`（**整文件摘要**），无 `assertions_digest` | **未实现**，且整文件摘要与「排版不计」相反 |
| K3b 引用属当前集合 | 报告 `findings[].assertion_ref` **完全没有校验** | **未实现** |
| K4a 报告不可覆盖 | `import_report`：同路径不同摘要 → `WF_REVIEW_INVALID`，不覆盖；同摘要重入幂等；机制稿 §9.2 同步写明"旧轮次路径永不覆写" | **已实现**（缺自动化用例） |
| K4b 关闭复核不得自证 | `reviews.dispositions` 是**自由格式列表**，逐条原样追加，无字段校验、无复核人、无"提出者"比对 | **未实现** |
| K4c 本轮新规则不得当判据 | 无 rule id、无"本任务新增/修改"的判定，`broken-reference` 豁免机制不存在 | **未实现** |

## 2. 三条阻断（需要人裁定，均属上位文档语义）

### 阻断 003：spec 规则没有 `check` / `clauses` / 稳定 rule id
- **原因码**：`WF_SEMANTIC_DECISION`
- **决定性事实**：机制稿 §8.3 的字段清单只有 `paths` / `status` / `verified_at` / `schema_version` / `author` / `counterexample`（`payload/templates/spec/rule.md` 同）；v42 K3b 却以「spec 规则 `check`」为 digest 实质字段、以 `clauses[]`（只增不改、`deprecated_summary ≤80`、只算 active）为判定条件；K4c 还需要"规则身份"来判"本轮新增"。
- **出口**：(a) 机制稿 §8.3 增 `check` 与 `clauses[]`（含 active/deprecated 语义与 `deprecated_summary` 校验）；(b) 把 K3b/K4c 的 spec 侧改成基于现有字段（例如以"路径 + `counterexample` + `status`"为实质字段）——但这与 v42 的"命令/参数变了标准就变了"意图不符；(c) 登记为 P2 只覆盖验收项与验证定义，spec 侧留空。
- **禁止的错误修复**：不得给 spec 规则偷偷加字段而不改机制稿；不得把整文件摘要继续当"实质摘要"。

### 阻断 004：check 记录不存锚点 parts，"列出差异"没有第二端
- **原因码**：`WF_SEMANTIC_DECISION`
- **决定性事实**：`check.py` 只存 `anchor: {check_anchor, rule_version}`（哈希），`anchor_parts` 未落盘；v42 K3b 要求"不符 → 列出差异（只算实质字段）"。没有第二端就无法算 diff。
- **出口**：(a) 给 `check.anchor` 增 `parts`（机制稿 §3.5 的 check schema 同步加字段，旧记录缺省为 null → 差异不可得时如实标 `diff_unavailable`）；(b) 另开一个"锚点快照"记录文件（违反"同一事实两处存"）；(c) 不改记录，只在 import 时报"锚点失配，差异不可得"。
- **禁止的错误修复**：不得在失配时按当前内容反推旧值。

### 阻断 005：机制稿 §9.2 明文"同一实施尝试最多两轮"，与 v42「删除轮次额度」冲突
- **原因码**：`WF_SEMANTIC_DECISION`
- **决定性事实**：机制稿 §9.2 写「同一实施尝试最多两轮（含审查通过后因采纳建议发起的重审），两轮用尽仍未 pass 由人发起返工，不再发起第三轮」；v42 §4「必须删除的旧机制」首条即「轮次额度（两轮上限）」，K10 说"阶段只有…+ 终态"，§7.1 的覆盖者是「收敛谓词 S6 + 判断清单」；dogfood 的两次死路（两轮用尽）正是这条。
- **出口**：(a) 删机制稿的两轮上限，改由收敛谓词判定（v42 方向）；(b) 保留两轮上限，v42 的 S6/K10 记偏差；(c) 折中：保留"尝试/轮次"计数字段用于观察，但不再阻断。
- **禁止的错误修复**：不得既留额度又声称已删；不得把额度藏在 `attempts` 计数里隐性生效。

## 3. 可立即做的（不依赖裁定）

- 给 K4a 补一条自动化用例（行为已存在，无覆盖）。
- 为 `dispositions` 定义最小字段（finding id / decision / reason / evidence / follow-up）并做 **结构性** 校验——但"提出者不得自证"需要"复核人"字段，属阻断 003/004 之外的第三处 schema 缺口（机制稿 §9.2 只写"逐条接受/驳回理由、证据与后续动作"），若要加字段需同批改 §9.2。
