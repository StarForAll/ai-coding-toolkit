# ⑥ 修复态的表达：不新增阶段，用「事实 + 出口」吸收 `fixing` 的收益（v26）

> 状态：**待审 v26**。阶段：**方案审查阶段，实现零改动**（规则见 `.trellis/spec/guides/review-phase-discipline.md`）。
> **本文只回答 ⑥**：`fixing` 阶段的收益如何在四阶段内表达。范围边界见 §8，超出范围不作为通过条件。

---

## 1. ⑥ 的问题

v42 要求"审查失败进入修复态"，三处原文：

| v42 | 要点 |
|---|---|
| K10（L107） | 阶段只有 `plan/execute/**fixing**/finish`；`escalated` 只阻断最终结论与归档 |
| S4（L122） | `decide` 三态：`fail → **fixing**`、`pass → finish`、`unavailable`（异常归档） |
| S5（L123） | `plan → execute → **fixing** → finish`；**内容变化或 review 判 fail 进入 `fixing`**，由下一次 `task-check` 退出；**审查失败不再需要 replan/approve** |

人裁：**保留四阶段、`fixing` 不落盘**（2026-11-09）；在该前提下**吸收收益**、人裁通道用于"人不在场"（2026-11-11 乙）。

`fixing` 作为阶段实际提供三样东西：

| `fixing` 提供 | 本方案用什么替代 |
|---|---|
| ① 明确的"在修"位置 | `findings` 事实（要修哪些项）+ `conclusion` 事实（结论是否仍成立） |
| ② "fail 不强制 replan"的默认 | **指引**（不是机制常量）：`fail` 不触发 replan；**根因在规划时 `task-replan` 仍可用**（协议已有 `check/finish → plan` 的 `replan` 迁移） |
| ③ 修完由下一次 `task-check` 退出 | 事实：`conclusion.bound_to_current` 与 `check` 的现状；是否重查由 AI 判断（见 §4 出口表） |

**S5 的另一个触发（内容变化）** 一并纳入：它使旧结论不再绑定当前 check，体现为 `conclusion.bound_to_current=false`（判据与既有 `review-passed` 门禁一致，不新写条件）。

---

## 2. 机制给什么：三组事实 + 一条人裁记录

### 2.1 `repair_scope`（派生，不落盘；**没有单一状态枚举**）

```json
"repair_scope": {
  "findings": [{"round": 1, "slot": "codex", "finding_id": "f1", "severity": "blocker"}],
  "unverifiable": [{"round": 1, "slot": "codex", "path": "…", "report_digest": "sha256:…",
                    "cause": "changed|missing|unreadable",
                    "cited": false,        // 是否为当前结论所引用的报告
                    "released": false}],   // 是否已有人裁放行（且 cited=false）
  "conclusion": {"verdict": "fail", "round": 2, "check_id": "C2",
                 "bound_to_current": false,
                 "bind_problems": ["check_id_changed", "cited_report_digest_mismatch"]}
}
```

**计算规则（一个函数实现；三组事实彼此独立，不用单值枚举互相遮蔽）**

| 事实 | 公式 | 与既有代码的关系 |
|---|---|---|
| `findings` | 直接取门禁用的同一份 `open_findings(...)["blocking"]`（**全轮次、不做 check 过滤**），并补 `round/slot` | **与 `final_gate` 同源**：两处口径必须逐项一致（上一版另立"针对当前 check"的过滤，导致 `repair_scope` 说无项可修而归档被拒） |
| `unverifiable` | 已导入报告中**当前核对不上**的：`cause` 取 `changed/missing/unreadable`；`report_digest` 取**登记摘要**（不是现场摘要）；`cited` = 该 `(round, slot)` 是否出现在 `reviews.result.imported` 中；`released` = 存在 `(round, slot, report_digest)` 全等且未撤销的放行记录 **且** `cited == false` | 只读既有记录；不新增身份 |
| `conclusion` | `verdict/round/check_id` 来自 `reviews.result`；`bound_to_current` **≡ 既有 `review-passed` 门禁的判据**（`check_id` 相等 **且** 结论引用报告的 `result_digest == recorded == 文件当前摘要`）；不满足时 `bind_problems` 逐项给原因 | **不复制条件**：直接复用该判定 |

**为什么不用 `reason` 单值**：`fail` 与"某份报告损坏"可以同时成立；单值只能隐藏其中一个（上一版的 `reason` 优先序会遮住另一条事实）。

**不放进 JSON 的东西**（避免把指引伪装成事实）：`replan_not_needed`、`phase_unchanged`、`recheck_required`、`active`。
这些要么是常量（零信息），要么是 AI 的判断（是否重查、是否 replan），应写在 §4 的指引里。

### 2.2 人裁记录（乙通道，只在"无法恢复的可核实性"时使用）

**记录**（新增，落盘）：`reviews.unknown_acceptances[]`

```json
{"batch": "b-1", "round": 1, "slot": "codex", "report_digest": "sha256:…",
 "path": "…", "cause": "changed", "quote": "这份报告丢失的风险我认",
 "by": "human:xzc", "at": "…", "source": "user-declared", "attestation_digest": "sha256:…",
 "revoked": false}
```

| 规则 | 语义 |
|---|---|
| 匹配 | `(round, slot, report_digest)` **三者全等**；摘要不同不匹配 |
| **只对非引用证据有效** | `cited == true` 的报告（当前结论引用的）**不接受放行**：归档依据必须是可核实证据 → 只能重发新一轮（见 §3 B2） |
| 批次 | 一次一批、**全有或全无**；任一项不匹配 → 整批拒绝、零写入，返回 `bad_items` |
| 不做预放行 | 指向当前不存在的不可核实项 → 拒绝（避免将来自动生效） |
| 幂等 | 同一键重复放行 → 不新增，回报 `already_accepted` |
| 撤销 | `--revoke --batch <id>`；或 `--revoke --round --slot --digest`（**必须带 digest**，否则同槽多条时不唯一，报错列出候选） |
| 信任模型（**定案：不引入签名**） | 沿用既有 attestation：`by/at/quote/source` + 摘要入库。**机制不引入任何密钥/签名步骤**——全仓没有任何签名/验签设施（`grep signature|gpg|hmac|keyring` 于 `payload/` 为空），`authorize`（删除/外发/提交授权）与 `attestation` 都是这个级别。机制只保证：绑定到具体证据、留痕可审计、撤销留痕。**不宣称"AI 无法自签"** |

**命令**：`wf review-accept-unknown --task <id> --file <决定.json>`（含 `--revoke`）。

---

## 3. 四条语义边界（上一版写错的三处已纠正）

| # | 边界 | 说明 |
|---|---|---|
| **B1** | **可核实性是"当前状态"，不是历史事件** | 报告短暂不可读后恢复、或找回了与登记摘要完全相同的字节 → 它**不再**是不可核实 → 阻断**自然消失**。这不是"解除阻断"，是事实变化。人裁只用于**无法恢复**的情形（如原字节已不可得）。上一版 B1 写"恢复也不能解除"，会逼出"客观已恢复仍要人签字"的无谓流程 |
| **B2** | **当前结论所引用的证据必须可核实** | `cited == true` 的损坏报告**不能靠人裁解除**：既有 `review-passed` 门禁会先做三重摘要核对并拒绝。出口是**重发新一轮**（新结论 + 新证据）；人裁放行只消化"非引用"的历史证据 |
| **B3** | **`fail` 不强制 replan，但不是禁止 replan** | 机制只表达"fail 不自动回到 plan"这一默认；若根因是规划缺陷（验收标准不成立、路线不可行），`task-replan` 仍是合法出口（协议已有 `check/finish → plan` 迁移，代价：原批准失效）。**不由机制断言"不需要 replan"** |
| **B4** | **`unavailable` ≠ 异常归档** | `--unavailable` 只表示"这次审查做不成"；`task-abandon` 是不跑最终门禁的**终局**出口，不解除任何阻断事实 |

---

## 4. 出口表（**指引**，不是机制；给事实与可选动作，不排顺序）

| 事实组合 | 可做的事（AI 自行选序） | 不该被理解成 |
|---|---|---|
| `findings` 非空 | 按项修复 →（需要时）重跑 `task-check` → 重发审查 | "必须先 replan" |
| `findings` 为空，但 `conclusion.bound_to_current == false` | 重发审查（结论已不适用）；若根因在规划，可用 `task-replan` | "已经结清" |
| `unverifiable` 有 `cited == false` 且 `released == false` | 找回原字节（恢复即可核实）/ 人裁放行 / 放弃任务 | "重发新一轮就已解除" |
| `unverifiable` 有 `cited == true` | **重发新一轮**（新报告 + 新结论）；人裁放行不适用 | "放行后即可归档" |
| `verdict == "invalidated"` | **完成已在途的那一轮**（`invalidated` 只在新 `review-launch` 时写入，此时新一轮已发起） | "再发一次审查" |
| `phase == "finish"` 且存在上述任一未结事实 | 以事实为准，先把未结项处理完再归档（`next` 是位置驱动、不感知失败事实） | "位置说归档就可以归档" |

**唯一硬约束**：不要用"试归档"探路（`tasks.py:3233` 会先做业务提交）。需要"能不能归档"的只读答案时，并读 `gate`（步骤面）与 `repair_scope`。

---

## 5. 与既有机制的关系（**不改的东西 + 依赖声明**）

| 机制 | 关系 |
|---|---|
| `phase` 枚举（`plan/execute/check/finish`） | **不改**，不新增 `fixing` |
| `protocol/states.json`（36 码 / 16 配置键 / 11 迁移 / `next_by_position`） | **不改**；`repair_scope` 不参与 `next` |
| `review-decide` 的判定资格 | **不改**，`repair_scope` 只读它的结论 |
| `task-check` 的 fail 语义与 revision | **不改** |
| `final_gate` 结构 | **只加一条**：存在 `unverifiable` 中 `released == false` **且 `cited == false`** 的条目时阻断归档（`WF_REVIEW_INVALID` + `facts.reason = "unverifiable_evidence"`）；`cited == true` 的情形由既有 `review-passed` 拒绝，不新增分支 |
| `task-abandon` | **不改**：终局、不解除 |

**已知限制（登记，不解决）**：人裁放行是**人的声明**，由持写权的 AI 会话转录；机制无法证明"人真的说过"。
不引入签名的理由：① 全仓无签名设施，`authorize`/`attestation` 都是声明式；② 要求人持密钥/硬件是反人性的流程负担，
人不一定在终端；③ 真要升级属"整体信任模型"议题，不应在 ⑥ 里点状加码。

**依赖声明（必须写清，否则 ⑥ 的落地会踩另案的坑）**

| 依赖 | 影响 | 未就绪时的行为 |
|---|---|---|
| 读取归因（`OSError` 归类，另案） | `cause` 能否正确区分 `missing` 与 `unreadable` | 退化为"不可读"，仍可阻断；`cause` 精度不足 |
| `slot` 身份稳定（另案） | 人裁键 `(round, slot, digest)` 是否稳定 | 现状下若 `slot` 与 `agent` 混用，放行可能匹配不上；此时出口是"重发新一轮"（不依赖放行） |

---

## 6. 实现落点（批准后执行；本轮不动代码）

| 文件 | 改动 |
|---|---|
| `review.py` | 新增 `repair_scope(ctx, task)`（纯派生，单一实现）；复用 `open_findings` 的 blocking 集与 `review-passed` 的绑定判据；`unknown_acceptances` 读写与撤销 |
| `gates.py` | `final_gate` 末尾追加一条：未放行的**非引用**不可核实项 → 阻断（附三条出口） |
| `cli.py` | `wf status`（含 `--short`）输出 `repair_scope`；新增 `wf review-accept-unknown`（`--revoke` 需 `--batch` 或 `--digest`） |
| `templates/` | 不改（`repair_scope` 派生；`unknown_acceptances` 可选） |

**迁移影响**：无历史改写（全派生）。

---

## 7. 验收（12 项，全部属于 ⑥）

| # | 断言 |
|---|---|
| 1 | `findings` 与 `final_gate` 的 `unaddressed_blocking` **逐项一致**（同一函数产出；不做 check 过滤） |
| 2 | 审查判 `fail` 且绑定当前 check → `conclusion.verdict == "fail"`、`bound_to_current == true`、`findings` 列出未关闭 blocking |
| 3 | 修复后重跑 `task-check` 产生新 check（**不改 `reviews.result`**）→ `conclusion.bound_to_current == false`、`bind_problems` 含 `check_id_changed`；**不得**因为"verdict 仍是 fail"而让 `findings` 消失 |
| 4 | 内容变化使旧结论失效 → `bound_to_current == false`（S5 的第二触发可见） |
| 5 | `verdict == "invalidated"` → 出口指引为"完成已在途那一轮"，**不是**"再发一次" |
| 6 | 非引用报告损坏 → `unverifiable[].cited == false`；人裁放行（摘要全等）后 `released == true`，归档不再因此阻断 |
| 7 | **引用**报告损坏 → `cited == true`；人裁放行**不**解除（`released` 保持 false），归档被既有 `review-passed` 拒绝，出口是重发 |
| 8 | 报告恢复（原字节找回，摘要与登记一致）→ 该项**不再出现在** `unverifiable`（B1：事实变化，不是解除） |
| 9 | 撤销放行 → `released` 回到 false 并恢复阻断；同槽多条放行时 `--revoke` 必须带 `--digest`，否则报错列候选 |
| 10 | `fail` 之外的路径不改 phase：无论 fail 发生在 `check` 还是 `finish`（`task-check` 通过后会置 `finish`），phase 都不由本方案改写 |
| 11 | 协议零改动：`phase.enum`、迁移数、`next_by_position` 逐字节一致；`repair_scope` 不参与 `next` 计算 |
| 12 | `task-abandon` 仍可终止任务，且不把任何 `unverifiable` 标为 `released`（B4） |

---

## 8. 范围边界（防跑偏，硬约束）

> 被排除的条目已登记在 `analysis/backlog-excluded-from-item6.md`（含证据位置、与 ⑥ 的依赖关系、建议顺序），
> **⑥ 解决前不处理**。本文只保留边界说明，不复述条目细节。

**本文只回答 ⑥。以下均不在本文范围**，不作为通过条件：

| 不属 ⑥ | 归属 |
|---|---|
| `slot`/`agent` 身份域、finding 跨轮同名 | 另案（本文只声明依赖） |
| 导入端证据身份、`--restore`、幂等重入三态 | 另案 |
| `review-status` 的 `reports_ready`/`material_blockers` 等语义 | 另案 |
| 六处读取健壮、`file_digest_or_raise` | 另案（本文只声明依赖） |
| `gate` 的 `fulfilled_by`、`changes-persisted` 语义 | 另案 |
| `--short` 字段派生、展示分组 | 另案 |

---

## 9. 本文的历史（只留与 ⑥ 相关的关键否决）

| 版本 | 形态 | 为什么被否 |
|---|---|---|
| v3 | 新增 `fixing` 阶段 | 与 v42 枚举冲突；牵动协议与迁移 |
| v4 | 事件写入 `repair` 标记 | 主路径清不掉；两失败源共用槽位互相覆盖 |
| v20–v24 | 大 schema 表达"全部未结事实" | 偏题（装进其它组件缺陷）；事实过载 |
| v25 | 单值 `reason` + 常量字段 | fail 与损坏并存时互相遮蔽；`replan_not_needed`/`phase_unchanged` 是指引伪装成事实；cited 损坏时人裁出口是死路 |
| **v26** | **三组独立事实 + 一条人裁记录 + 出口表（指引）** | 只回答 ⑥；不新增阶段、不改协议、不改 `next`、不把判断写成常量 |

---

## 10. 已定项（原 D1/D2，2026-11-11 人裁）

| # | 问题 | 裁定 | 落点 |
|---|---|---|---|
| D1 | 非引用不可核实证据的阻断：复用 `WF_REVIEW_INVALID` 还是新增协议码？ | **复用 `WF_REVIEW_INVALID` + `facts.reason = "unverifiable_evidence"`**（协议零改动） | §5 `final_gate` 那一条分支、验收 6/7 |
| D2 | 人裁信任模型：是否引入签名？ | **不引入签名**——沿用既有声明式信任（`by/at/quote/source` + 摘要），如实登记为已知限制 | §2.2 信任模型行、§5 已知限制 |

> 早期 **Q1=乙**（放行批次形状）与 **Q2=甲**（两类阻断分列）同样已定，见 §2。
> 本文现已无待决项。
