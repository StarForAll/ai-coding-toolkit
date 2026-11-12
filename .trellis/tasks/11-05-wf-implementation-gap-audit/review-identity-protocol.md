# 审查参与者身份协议（review identity protocol）

> **拆分来源**：`identity-redesign.md` v3.30（S1 收口）。
> **拆分理由**：这三节是"删掉自动模式 `host_id`"的连带依赖，与"零输入身份"是两个议题；
> 它们改的是**审查子系统**（`review.py` 的 context/launch/decide、报告暂存、verdict 失效），
> 放在身份方案里会让评审在两个议题间来回串。
>
> **与身份方案的关系**：身份方案只保留契约引用 **C6**（§3.7 清单）；本文负责实现清单、协议与验收。
> **共同前提**：自动模式不产生 `host_id` ⇒ 会话路由身份与审查参与者身份必须分离。

---

## 0. 议题边界

| 属于本文 | 不属于本文（见 `identity-redesign.md`） |
|---|---|
| reviewer 如何声明身份（`--as`） | 会话身份如何派生（锚点、`session_key`） |
| 实施 CLI 如何声明与补录 | 写权、代次、activation |
| 报告与占位的落点与暂存 | 五态恢复、轮换、迁移 |
| `verdict` 失效与最终门禁消费 | 附件 / roots / anchors 的 GC |

---

## 1. 实现修改点（C6：这份清单必须写进 R5 交付，否则协议落空）

| 文件/位置 | 现状 | 必须改成 |
|---|---|---|
| `lib/wflib/cli.py` 参数解析 | 无 `--as` / `--implementation-cli` | ✅ 已新增并进 `COMMAND_HELP` |
| `lib/wflib/review.py:281`（`review-context`） | `normalize_agent(session.identity.host_id)` | ✅ 已改取 **`--as`**（显式模式回退 host_id 以兼容存量）；都没有 ⇒ `WF_IDENTITY_UNRESOLVED` |
| `lib/wflib/review.py:140`（`review-launch`） | 读 `implementation_clis` 数组 | ✅ 已改为单值 `--implementation-cli`（数组仅作兼容读，冲突即阻断；缺失即 `WF_REVIEW_INVALID`） |
| launch 记录 schema | `reviews.launches[]` 无实施 CLI 字段 | 增 `implementation_cli`（单值）+ `declared_at` + `declared_by` |
| `review-import` | 报告署名靠 host_id | 署名取 `--as` 的归一值；与 launch 记录比对 |
| `review-decide` | `:601` 取 host_id，缺失回退空集 | ✅ 已只读 launch 记录的 `implementation_cli`；为空 ⇒ **拒绝给出 pass**，并**删除**了判定期回写该字段的旧逻辑 |
| `capabilities`/`help` | — | 两个新参数进命令表（§4.2b 已列） |


| 文件/位置（续） | 现状 | 必须改成 |
|---|---|---|
| `review.context()` 的报告路径 | `review-<host_id>.md` | 改为 **`review-<as>.md`**（文件名 token = 身份，设计稿 §6.5 2026-11-07 修订） |
| `review-import` 的 reviewer token | 取自报告文件名 | 取**暂存报告**文件名 token（`review-<as>.md`），与**占位记录 `.claim-<as>.json`** 及 launch 声明交叉核对（见第 2 节） |
| `--as` 校验 | 无 | 非空 + `normalize_agent` 归一（`[a-z][a-z0-9-]*`）；缺失/非法 ⇒ `WF_IDENTITY_UNRESOLVED` |
| `help`/示例 | 无 `--as` | ✅ 已在 `COMMAND_HELP` 补 `--as` 与 `--implementation-cli` 示例 |

## 2. `--as` 的三点一致性

身份是自报（纪律边界），但**同一次审查里三处声明必须一致**，否则"两个不同审查 CLI"的门禁可被声明漂移绕过：

| 时点 | 声明 | 校验 |
|---|---|---|
| `review-context --as X` | 写入该轮**占位**：`<staging>/<project-hash>/<task>-<round>/review-<X>.md`，头部 `status=in-progress`（**项目树外**） | 同轮同 X 只允许一次（已有 in-progress/done ⇒ 拒绝）；`--reset` 由人清除 |
| 写报告 | 同一文件：把头部改成 `status=done` 并写正文（**文件名的 `<X>` 就是身份**，与归档后的名字一致） | 判定/导入都按文件名 token |
| `review-import` | 文件名 token + `--as` | **两者必须一致**；`--as` 指到从未调用过 context 的 CLI ⇒ `no_claim`；占位在但 `status` 不是 done ⇒ `staging_evicted`。出口相同（重跑 context），归因按此规则判定 |

> **实现对齐（2026-11-08 C6 交付）**：占位不是独立文件，而是 `review-context` 写下的**报告骨架本身**（`status=in-progress`），
> 文件名即身份。这样"占位/报告/导入"三处天然只有一个事实源，不需要额外的 `.claim-<X>.json`。

**验收**：`context --as codex` 后把报告命名成 `review-claude.md` ⇒ import 阻断；`import --as claude` 与占位 `codex` 不符 ⇒ 阻断。

**`review-context` 的写入边界（v3.23 重写，修 a#22.1 / b#22.9）**

v3.22 让它"以固定职责授权写项目树"，这是错的：设计稿 §4.4 的写者互斥**不会**被"固定职责授权"豁免
（后者只解决"是否必须列入 touch_paths"），而且 reviewer 没有 session_key，**根本无从取附件锁**。

| 写入物 | 谁写 | 落点 | 并发控制 |
|---|---|---|---|
| `materials/{diff.patch,prd.md,check.json,tests.json}` 快照 | **主会话在 `review-launch` 时一次性物化**（持写权） | 任务树 `review/round-N/materials/`；**不随任务记录提交**（`.gitignore` 托管段覆盖运行产物，R3 核对） | 项目锁 |
| reviewer 占位 | reviewer | **项目树外**：`<staging>/<project-hash>/<task>-<round>/.claim-<as>.json` | `O_EXCL` 原子创建（同轮同 agent 只能一次） |
| 审查报告 | reviewer | **项目树外**：`<staging>/<project-hash>/<task>-<round>/review-<as>.md`（**身份在文件名**） | 原子写 + rename |
| 报告归档进任务树 `review/round-N/review-<as>.md` | **主会话在 `review-import` 时复制**（持写权） | 任务树 | 项目锁 |

**暂存目录（v3.25 修 a#23.2）**：`<staging>` 由入口提供且**必须在项目树外**，默认 `${TMPDIR:-/tmp}/wf-review`；
项目内只留一行定位信息（`.wf/.runtime/review-staging.json` 指向该目录），由持写权的主会话在 `review-import` 时核验并导入。
暂存可能被系统清理：导入时若文件不在 ⇒ 拒绝并提示“重跑 context”（不猜、不复用旧报告）。

**结论**：reviewer **全程不写项目树**（运行态也是项目树内），项目树只由持写权的主会话写——不新增任何例外。

## 3. `review-launch` 的跨文件事务

`review-launch` 同时写三处：`writer.json`（代次/判定字段）、task 记录的 `reviews.launches[]`、附件的 `declared_implementation_cli`。
与 `mark-root-gone` 同类，**复用同一套 action 意图/前像/后像规则**：

```text
with 项目锁:                                   # 锁顺序：项目锁 → 附件锁
    writer.action = {kind:"review-launch", task, round, impl_cli, step:"intent",
                     id, base_revision, head_before, targets, before, after, generation, owner}
    reviews.launches[] += {round, implementation_cli, declared_at, declared_by}    # ① 任务记录（Git）
    with 附件锁(session):
        attachments[K].declared_implementation_cli = impl_cli                       # ② 会话默认值
    writer.action = null                                                            # ③ 清意图
```

| 中断点 | 重入判定 |
|---|---|
| ①后②前 | 意图在、launch 记录已含该 round **且其中 `implementation_cli` == 意图值** ⇒ **只补 ②**（真中断恢复） |
| ①后②前，且**记录值 ≠ 意图值** | 这是**补录**：按意图值**更新 ①**（写新的 `declared_at`/`declared_by`）再补 ②——否则 §6 的"重跑 launch 补录"永远不可达（v3.22 修 b#21.1） |
| ②后①前（顺序不会发生，①在②前） | — |
| ③前任意失败 | 意图在 ⇒ 按 `step` 补齐缺失的一侧 |
| 意图已清、两侧不一致 | **不视为损坏**（v3.23，修 a#22.4）：事务完成后附件默认值可独立变化；一致性只在**未完成 action** 的前像/后像范围内核验，不回看历史轮次 |

**实施 CLI 变更 ⇒ 既有审查结论同批失效（v3.23，修 a#22.2）**

`implementation_cli` 不是展示字段，而是"异种审查是否成立"的**判定输入**。因此：

| 情形 | 动作 |
|---|---|
| 同轮 `implementation_cli` **实质变化**（值不同） | ①更新 launch 记录；②**同批把 `reviews.result.verdict` 直接改写为 `invalidated`**（并写 `invalidated_reason`/`invalidated_at`）——**改现有字段，不新增旁路标记、不引入第二个状态字段**；③同批改写引用该结论的完成回执为 `invalidated`；④输出 `WF_REVIEW_INVALID(exit="实施 CLI 已变更，审查资格需重判")` |
| 仅补录为**相同值** | 幂等，无失效 |
| 报告能否复用 | **可复用**，但必须**重跑 `review-decide`** 重新判定异种门禁（报告是事实，资格不是） |

**理由**：最终门禁（`gates.py` 的 `final_gate`）核 verdict/Check id/报告摘要，**不重核实施 CLI**；不同批失效就会留下"已失去依据的 pass"。

**失效如何被消费（v3.28 定稿编码）**：**只保留 `verdict` 一个字段**，取值 **`pass | fail | unavailable | invalidated`**（`unavailable` 是机制稿 §10 既有的"审查不可用"出口——设计稿承诺的异常路径，**必须保留**，不得被新枚举吞掉）；`final_gate` 只认 `verdict == "pass"`。
**兼容缺省**：存量记录本就只有 `pass/fail/unavailable`，**无需迁移**；`invalidated` 是新增枚举值，只由本方案写入。不引入 `status` 之类第二字段。
**action 前像/后像必须覆盖**：`reviews.launches[]` 条目、`reviews.result.verdict`、引用它的完成回执、附件默认值。
**重入判定**：核验后像是否**完整**（四处都已改写），不能只看 `implementation_cli` 是否等于意图值。

**"同轮次幂等"的唯一含义（v3.22）**：同一 `(task, round)` 可重复调用；**是否写入取决于意图值与已落盘值是否相同**——
相同 ⇒ 不重复写；不同 ⇒ 视为补录并更新记录。§6 的补录出口即由此成立。

> **交付状态（2026-11-08）**：上面三处写入中，**① 任务记录（`reviews.launches[]`，含 `implementation_cli`/`declared_at`/`declared_by`）已实现**；
> **② 附件的 `declared_implementation_cli`（"下次预填"的会话默认值）尚未接线**——它只是预填来源，缺失不影响判定；
> ③ 清意图沿用既有 action 收尾。失效链（`verdict=invalidated`）已实现并在 launch 内同批判定。

**与既有 action schema 的映射（v3.22，修 a#21.3）**：

| 字段 | 取值 |
|---|---|
| `id`（幂等键） | `SHA256(C({kind:"review-launch", task, round, impl_cli, decision_digest}))`——**含 impl_cli**：补录时 CLI 变了就是新 id，不会与旧意图混淆 |
| `base_revision` / `head_before` | 进入事务时的 Git HEAD |
| `targets` | `[<task>/task.json（reviews.launches）]` + `[.wf/.runtime/attachments/<session_key>.json]` |
| `before` / `after` | ①`reviews.launches` 该 round 条目（前像可为空）②`declared_implementation_cli` 旧/新值 |
| `generation` / `owner` | 写入时的 `writer.generation` 与 `session_key`；**重入时 generation 已变 ⇒ 拒绝旧 launch 重入**（`WF_GENERATION_STALE`），由人重新发起 |

**一致性语义**：**launch 记录是本轮的事实**；附件默认值只是"下次预填"。因此
"launch 用了 X、默认值仍是旧 Y"**不构成不一致**（Y 是历史默认），只有"本轮记录缺失/两侧都无"才阻断。
