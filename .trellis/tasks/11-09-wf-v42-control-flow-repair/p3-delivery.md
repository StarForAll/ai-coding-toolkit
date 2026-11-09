# P3 交付记录（第一片：S3 判定句 + S9 `review-status`）

## 1. 本轮改动

| 文件 | 动机 | 编号 |
|---|---|---|
| `review.py::derive_verdict` | **S3 判定句**：`verdict=fail` **仅当**存在 blocking finding；`uncovered` 轴产**缺口**不产缺陷（不再是 fail）；轴判 `fail` 却无 blocking finding → 输入不成立（例外字段不得一义三用）；申报 verdict 与推导不一致 → 输入不成立 | S3、B1 |
| `review.py::decide` | 改用上述三态推导；`uncovered` 汇总进 `facts.gaps`（走 4.8/4.9） | S3/D1 |
| `review.py::status_of_round` | **S9 到位状态**：本轮已到 n/2、缺哪份、每份状态 `missing|staged|imported|stale`、`ready_to_decide`；锚点算不出时标 `anchor_checked=false`（不假装新鲜也不假装失效） | S9、D3 |
| `cli.py` | 注册 `review-status` 命令与 help 条目（只读） | S9 |
| `scripts/tests/wf_review/test_review_status.py` | 8 条：缺份/到位/改写后 stale/锚点核不了、以及三态推导 5 条 | S3/S9 |

## 2. 验证

| 命令 | 结果 |
|---|---|
| `unittest discover` | **126 tests OK**（118 → 126） |
| `build-wf-release.py --verify` | **OK** byte reproduction（63 assets） |
| `wf-protocol-docs.py --check` | **OK** 35 码 / 16 配置键 / 11 转移 |
| `validate-wf-design.py` | **OK** 定义 100% / 消费 100% / 输入摘要 4/4 |
| `check-doc-refs.py` | **0 problem(s)** |

## 2.5 第二片：`lint report` 一次列全（S3/C2/C3）

| 位点 | 改动 |
|---|---|
| `review.py::read_report` | 宽松解析（返回 `(payload, problems)`）；**门禁 `parse_report` 与 lint 共用同一份解析**，避免"严格版/容忍版"两写 |
| `review.py::lint_report` | 一次列出：协议标记/JSON、必填字段、轴完整性与枚举、**轴 fail 无 blocking（一义三用）**、申报 verdict 与推导不一致、引用属当前集合、`d:` 引用 deprecated、recheck 形状；未给 `--task` 时**显式标 skipped**（不静默当通过）；输出 `not_checked` 声明 lint 不核什么 |
| `cli.py` | 注册 `lint report --file [--task]` 与 help 条目 |
| `scripts/tests/wf_review/test_lint_report.py` | 5 条：干净报告、一次列全、缺标记、`uncovered` 是缺口、缺 `--task` 时显式 skipped |

**一次列全的证据**：旧行为是 `parse_report` 遇到第一个问题就抛（缺字段只报缺字段），现在同一份样例能同时列出"缺字段 + 轴 fail 无 blocking"——这正是 dogfood 四轮格式返工的成因。

验证：`unittest discover` **131 tests OK**；`build-wf-release.py --verify` **OK**；`wf-protocol-docs.py --check` / `validate-wf-design.py` / `check-doc-refs.py` 全绿。

## 2.6 第三片：判断骨架 + `judgments[]` + 收工预览（v42 §5）

| 位点 | 改动 |
|---|---|
| `payload/lib/wflib/judgments.py`（新） | `skeleton(ctx, task)` 事实骨架（变更/排除路径、findings、closures、unaddressed、verifications、rejected_unresolved、waived_count；`scope_available` 如实标注分类是否可用）；`ref_ids` = `v:`/`f:`/`p:`；`validate`（kind 枚举、basis 必填、outcome、escalated 必须写清问题、`by` 枚举、**引用只认骨架派生 id**）；`append`（**append-only**：不删不改，更正只能新增 + `supersedes`）；`render_preview`（一屏，计数显式，含"不确定 0"、`[补]` 标记、升级项逐条） |
| `cli.py` | 注册 `judgments add --file` / `judgments show`（show 直接渲染预览）；add 走 `task.judge` 动作（锁内重核 + 写标记） |
| `dev-manifest.json` | 登记 `judgments.py`（64 assets） |
| `scripts/tests/wf_review/test_judgments.py` | 9 条：骨架引用、append-only 不改历史、`supersedes` 必须存在、自由文本引用被拒、escalated 必须带问题、kind 枚举、预览含"不确定 0"、`[补]`/升级可见 |

**这一片直接对着 dogfood 的两个病灶**：12 条"人决定"全是模型转录的 human:chat（现在 `by=human` 只是字段、不新增类别，且判断必须带骨架引用）；唯一那条 blocking 的 evidence 只写自由文本（现在自由路径一律拒绝）。

验证：`unittest discover` **140 tests OK**；`build-wf-release.py --verify` **OK**（64 assets）；`wf-protocol-docs.py --check` / `validate-wf-design.py` / `check-doc-refs.py` 全绿。

## 2.7 第四片：`WF_UNRESOLVED_BLOCKING` + 归档门禁接 S6 第 3/4 项

| 位点 | 改动 |
|---|---|
| `payload/protocol/codes.json` | 新增 `WF_UNRESOLVED_BLOCKING`（blocked；出口 = K4b 非提出者复核关闭 / 人确认重分类 / 设计稿 §5.6 异常归档）→ **36 码** |
| 机制稿 §11.1 | 同批加该码行（含"不把不处置当关闭、不靠自由文本理由关 blocking"） |
| `review.py::open_findings` | K8 投影：**重解析已导入报告**（报告有 digest、导入后不可改）派生未处置 findings；报告被改写 → `unavailable`，**不静默当已关闭** |
| `gates.py::final_gate` | S6 第 3/4 项：存在未处置 blocking → `WF_UNRESOLVED_BLOCKING`，facts 带条目与三条出口 |
| `judgments.py::skeleton` | `findings` / `unaddressed_findings` 改用同一投影（与门禁同源，不再两处各算） |
| `scripts/tests/wf_review/test_open_findings.py` | 5 条：未处置即阻断、accepted 关闭、rejected 不关闭、报告改写标 unavailable、新码已登记且带出口 |
| `scripts/tests/test_build_wf_release.py` | 2 条：打包预检早于删树、检查不得搬回 `build()` |

验证：`unittest discover` **147 tests OK**；`build-wf-release.py --verify` **OK**（64 assets）；`wf-protocol-docs.py --check` **OK（36 码）**；`validate-wf-design.py` / `check-doc-refs.py` 全绿。

## 2.8 第五片：§0.2 试点期抽样（按原文实现）

| 位点 | 改动 |
|---|---|
| `payload/lib/wflib/sampling.py`（新） | 事件池**只从事实骨架**取（`EVENT_SOURCES` 8 类）；`select` 按原文：**预算固定 2 条不叠加**、**首任务只抽 1 条（关闭优先→无则归属）**、open blocking 时关闭类第一、默认风险序 标准变更>扩面>关闭>其余（同级按历史失败、强化期优先）、第 2 条**不排除同类**且按 `sha256(seed+"class-2")` 选类后序号 1 取事件、与第 1 条同事件则**序号 +1 顺延**；强化义务无可履行事件 → 标"顺延到下一个任务、不重复抽、不阻塞归档" |
| 同上 | `freeze`（种子 + 事件集写**任务记录**，committed，可复算）、`select_for`（冻结后 AI 改 judgments 不影响选样）、`record_result`（漏报/结论错标 `failed`）、`history_from_tasks`（按类累计样本/失败/连续无失败；首次失败进**强化抽样期**；连续 5 任务且样本 ≥10 才降为"可选"）、`report`（一屏 + **样本 N<10 门槛未激活**显式提示） |
| `cli.py` | `sampling pick --task [--freeze]`（冻结走 `task.sampling.freeze` 动作）、`sampling report`（只读统计）；`judgments show` 的预览**先声明"本次抽哪两类、为什么"**（未冻结时显式提示去冻结） |
| `dev-manifest.json` | 登记 `sampling.py`（65 assets） |
| `scripts/tests/wf_review/test_sampling.py` | 12 条：可复算、预算不叠加、首任务 1 条与归属回落、open blocking 优先、强化义务承接、单一事件顺延、未覆盖类命名、事件池不受 judgments 影响、冻结后可复算、首次失败进强化期、报告样本不足提示 |

**实现降级路径未启用**：一次性强制占位按原文实现（模块 docstring 里写明了"若后续发现事件池与强化期状态耦合出歧义，允许按原文删去占位"）。

验证：`unittest discover` **159 tests OK**；`build-wf-release.py --verify` **OK**（65 assets）；`wf-protocol-docs.py --check` / `validate-wf-design.py` / `check-doc-refs.py` 全绿。

## 2.9 第六片：漏报补写、期满前置、4.6 规模托底（P3 收口）

| 位点 | 改动 |
|---|---|
| `sampling.py::judgment_for / backfill_status` | 抽到的事件有没有对应判断（按 kind + `evidence_refs` 命中）；缺则记**漏报失败**并要求**补写两条**（`kind=漏报说明` + `kind=<该类>`，带 `backfill`、不用 `supersedes`）；**每任务 ≤2 条**，超出标"二次失败：由人裁，不自动升内核" |
| `sampling.py::mark_reviewed` + `history_from_tasks` | 人以"已看过预览"声明后，已进入强化期的类恢复常规抽样（`strengthened_ended`），报告里显式写"该类强化抽样期已结束"；**框架不机械检测人是否真看了** |
| `payload/lib/wflib/scale.py`（新） | 4.6 事实托底：`changes_since` 从 `baseline_head` 数净增删行/文件（含未跟踪新文件），读不到 git 时 `available=false` + 原因（**不猜 0**）；`history_max` 从归档记录的 `cumulative.confirmed_net` 取历史最大；`describe` 出预览行并在**超出历史最大值时高亮**（不阻断、不设绝对阈值） |
| `judgments.py` | 骨架 `cumulative` 改为真实事实；预览新增 `[规模]` 行 |
| `cli.py` | `sampling pick` 带 `backfill` 事实；`judgments show` 预览在漏报时追加 `[补写]` / `[二次失败]` 行 |
| `dev-manifest.json` | 登记 `scale.py`（66 assets） |
| `scripts/tests/wf_review/test_scale_and_backfill.py` | 10 条：相对线而非绝对阈值、超历史只高亮、不可得不猜 0、历史最大值来自记录、确认写回、漏报判定、引用即不算漏报、两条补写闭合、超额=二次失败、人声明结束强化期 |

验证：`unittest discover` **169 tests OK**；`build-wf-release.py --verify` **OK**（66 assets）；`wf-protocol-docs.py --check` / `validate-wf-design.py` / `check-doc-refs.py` 全绿。

## 3. 观察（不阻塞）

- `review-status` 是**新命令**：命令面目前有两处手写（`cli.COMMANDS` + `COMMAND_HELP`），protocol 的 commands 表在 P5 才建。已登记为 P5 的迁移项（届时两处从 protocol 生成）。
- `uncovered` 轴的缺口目前只进 `facts.gaps`；把它接进判断清单与预览（4.8/4.9 的可见面）属下一片。

## 4. 未完成（下一片）

1. ~~报告协议 lint 一次列全~~ → 已落地（`wf lint report`，见 §2.5）。
2. ~~`d:` 只认 active 条目~~ → 已在 lint 里实现（引用 deprecated 报"位置不存在"）；`d:` 的**漂移位置**核对（必须存在于本次 `drift_diffs`）随预览一起做。
3. **判断骨架 + `judgments[]`**（K8 投影、append-only、`evidence_refs` 只认骨架 id）。
4. **收工预览一屏**（含"不确定 0"、被驳回未处置计数、判断质量对照）。
5. **漏报补写的闭环**：抽到"无对应判断" → 记失败 + 要求补写两条（`kind=漏报说明` + `kind=<该类>`，都带 `backfill: true`、不用 `supersedes`、预览标 `[补]`）；补写复核每任务 ≤2 条。`judgments.append` 已支持 `backfill` 字段与 `[补]` 渲染，缺"抽样结果 → 要求补写"的驱动。
6. **强化抽样期的期满前置**：以"人声明已看过预览"为结束，框架不机械检测；当前 `history_from_tasks` 只按失败重置，未接人的声明。
7. **S6 第 5 项「累积变更已确认」（4.6 事实托底）**：需要"上次人确认以来的累计量"与"本项目历史最大规模"两个事实的落点（建议 `task.cumulative` + 归档记录派生），未做。
