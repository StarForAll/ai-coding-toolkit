# 提案：check 阶段多 agent 辅助审查（skill 内部化）

> 状态：**待审**（本轮不写入 `docs/workflows/workflow-implementation.md`）
> 上游决定（2026-10-29）：
> 1. check 阶段的多 agent 辅助审查**只用** `multi-cli-review-action` / `multi-cli-review`；
> 2. 这两个 skill 要从**仓库全局通用 skill** 改造为**工作流内部 skill**；
> 3. 它只是**基础默认实现**，后续允许新增别的实现；
> 4. 新方案须先经人审，通过后才落到实现方案文档。

---

## 0. 结论摘要

| 项 | 结论 |
|---|---|
| 归属 | 两个 skill 从 `skills/` 的通用资产迁为 wf 模块资产（`<MODULE_SRC>/templates/skills/`），随安装器落到目标项目 |
| 命名 | `wf-review`（reviewer 侧）+ `wf-review-action`（fixer 侧），与 `wf` / `wf-repair` 同前缀 |
| 编排契约 | 单独一份 `templates/review-protocol.md`，是唯一源；两个 skill 与 `wf` skill 只引用不重写 |
| 触发点 | 任务 check（`trellis-check`）之后、人判之前 |
| 状态影响 | **零**：不改 `task.json.status`、不写账本、不构成 `wf close` 的完成判据 |
| 产物 | `$TASK_DIR/review/round-{N}/…`，随任务进库 |
| 扩展位 | 契约里把"审查实现"抽成可替换位，默认指向 `wf-review*`；新增实现只加实现，不改契约 |

一句话：**把"谁来审、审什么、审到哪、结果放哪"写进工作流契约，把"怎么写一份合格报告"留给内部 skill，且不把审查塞进状态机。**

---

## 1. 为什么通用版不适配（证据）

| # | 现状（通用协议） | 与本工作流的冲突 |
|---|---|---|
| 1 | 两个 skill 的 Core Rules 明确"保持 workflow-agnostic"，人数/轮次/命令封装归上游 coordinator（`skills/multi-cli-review/SKILL.md` Rule 3；`.trellis/spec/skills/index.md` 的 paired-contract 段） | 本工作流需要**唯一答案**的身份规则、轮次上限、失败语义；通用协议把它们留空 |
| 2 | 报告落点固定 `tmp/multi-cli-review/<task-id>/`，而 `.gitignore:2` 忽略 `tmp/` | 本工作流要求任务产物随任务进库；报告放 `tmp/` 则跨机、换会话、事后审计都拿不到 |
| 3 | `task-id` 同时充当 review 根目录名与 Trellis 任务名 | 本工作流有三种身份（依赖标识 / slug / 目录，§3.3），`task-id` 指哪个未定义 |
| 4 | reviewer 身份只靠人给 `--reviewer-id`，`source-cli` 由 reviewer 自填 | 缺少"实施者 CLI 不得给自己当 reviewer"这一条硬规则，也没有来源核验点 |
| 5 | 协议不定义"报告缺失/不合格"的后果（只说 `0` 报告是 error） | 本工作流要求"审查失败不得视为通过"，需要明确的结论态与出口 |
| 6 | 两个 skill 在 `skills/`，未登记进 `trellis-library/manifest.yaml`，也未部署到 `.agents/skills/`、`.claude/skills/` | 装进目标项目后，目标项目里**根本没有这两个 skill**，审查无法执行 |

第 6 条是决定性的：不内部化，"检查阶段用它们"在目标项目里不成立。

---

## 2. 目标形态

### 2.1 资产与命名

| 现状 | 目标 |
|---|---|
| `skills/multi-cli-review/SKILL.md` | `<MODULE_SRC>/templates/skills/wf-review/SKILL.md` |
| `skills/multi-cli-review-action/SKILL.md` | `<MODULE_SRC>/templates/skills/wf-review-action/SKILL.md` |
| 无 | `<MODULE_SRC>/templates/review-protocol.md`（编排契约，唯一源） |

改名理由：`wf-` 前缀先于加载顺序说明归属，避免与将来任何通用版同名互遮；同时让 `wf` / `wf-repair` / `wf-review*` 在 skill 列表里连成一组。

### 2.2 落点与分发（沿用 §4.1 平台矩阵，不新增平台）

- 投放根：`.agents/skills/`（codex / zcode / pi / dsh 共用）+ `.claude/skills/`（Claude Code）。
- 不投 `.dsh/skills/`、`.zcode/skills/`、`.pi/prompts/`（与 §4.1 既有决策一致）。
- frontmatter 按 §4.3 渲染，正文同一份，占位符沿用 `{{PYTHON_CMD}}` 等。
- `§1.5 module_owned_paths` 增 4 条（两个 skill × 两个根）；`§7.5` 卸载随模块删除；`skill_roots.py` 的平台白名单从 2 个 skill 扩到 4 个。
- **不是**可选资产：随 `wf install` 分发，`wf doctor` 检查四个 skill 根是否齐全（缺则报告，不自动修复）。

### 2.3 契约单一源

`review-protocol.md` 只写编排（触发点、身份、轮次、落点、结论态、失败出口、降级）；`wf-review` 只写"怎么产出一份合格报告"，`wf-review-action` 只写"怎么安全采纳报告"。三者冲突时以 `review-protocol.md` 为准。

`.trellis/spec/skills/index.md` 的 coupled-pair 段同步改述：paired 关系保留（仍是同一协议的两半），但"保持 workflow-agnostic"改为"由 `review-protocol.md` 提供编排侧答案"。

### 2.4 与现有 skill 的边界

| skill | 职责 | 变化 |
|---|---|---|
| `wf` | 路由与生命周期入口；check 阶段提示"该跑审查了"并给出派发模板 | 正文加 3–5 行指引，不接管审查 |
| `wf-repair` | 账本对账与异常处分 | **不变** |
| `wf-review` | reviewer 侧：只读、只写自己的报告 | 由通用版改造 |
| `wf-review-action` | fixer 侧：汇总、本地复核、人确认后修 | 由通用版改造 |

---

## 3. 编排契约（工作流内专用）

### 3.1 时序

```
实施 → trellis-check（本 CLI 自查） → 多 agent 辅助审查 → 人判 → wf close
```

- 审查在**人判之前**：人判要看的正是"另一个 CLI 怎么看这份改动"。
- 审查可以与 check 失败重跑交替，但审查本身不重跑 check 的判据。

### 3.2 派发者与审查者

- 派发者是**当前任务所在 CLI**（也是唯一的 fixer）。
- 审查者必须是**另一个 CLI 会话**：人手工切 CLI 派单，或由派发者用该 CLI 的 headless 方式起一次性会话。派发者在派单里给出完整命令，审查者不改路径、不改轮次、不改 reviewer-id。
- 审查者**不 commit、不推送**，报告留在工作区由 fixer 收口。

### 3.3 身份

- `source-cli` 必须 ≠ 派发者 CLI；同一 CLI 不能既实施又审自己。
- reviewer-id 是槽位字母（`a` / `b` / `c` / `d`），真实 CLU 身份只进 `source-cli`。
- 报告 frontmatter 的身份字段拆成 `dep-id` + `slug`（取代含糊的 `task-id`），目录校验改为比对 `$TASK_DIR` 名的 slug 段。

### 3.4 人数与轮次

| 项 | 默认 | 说明 |
|---|---|---|
| reviewer 数 | **2 个不同 CLI** | 少于 2 家可用 provider 时降级为 1 个，报告里记 `degraded: single-provider` |
| 轮次上限 | **2 轮** | 达上限仍有未决项 → 结论记为不通过，交人判 |
| 0 个可用 provider | 不通过（记 `degraded: none`） | 不得静默跳过 |

### 3.5 产物

```
$TASK_DIR/review/
  round-1/{a.md,b.md}          # reviewer 只写自己那一个
  round-1/summary-round-1.md   # 只有 fixer 写
  action.md                    # 只有 fixer 写
```

- 进库，随任务归档一起移动。
- 目录由**派发者**预建（reviewer 不建目录，保留通用协议这条）。
- 定位是**任务产物**，不是新记录类型：不参与 `§6.1` 的记录表，也不改完成判据。

### 3.6 写边界（单写者）

| 对象 | 谁写 |
|---|---|
| `$TASK_DIR/review/**/{reviewer-id}.md` | 各 reviewer 只写自己的 |
| `summary-round-{N}.md`、`action.md` | fixer |
| 源码、`task.json`、`ledger.json` | 只有 fixer（reviewer 一律不写） |

### 3.7 审查焦点

派发者从 `prd.md` / `design.md` / `implement.md`、相关 `.trellis/spec/**` 与 `wf dag --check` 输出里取焦点；同一轮各 reviewer 的焦点文本**逐字相同**，只有 reviewer-id 不同。审查者不得自行扩焦到旁边的问题。

### 3.8 结论态与失败出口

| 结论 | 含义 | 出口 |
|---|---|---|
| `pass` | 无阻塞问题 | 进人判 |
| `pass-with-notes` | 只有低风险建议 | 进人判，建议列表随报告留档 |
| `fail` | 存在阻塞问题 | 就地修 → 重跑 check → 下一轮；或改走 `wf rework` |

- 报告缺失、frontmatter 不合法、reviewer 与派发者同 CLI → 结论按 `fail` 处理。
- `wf rework` 仍按 §3.12 的五步序列，审查不新增返工登记字段。

### 3.9 与门禁的关系

- 不阻断 `wf close`（约定层，与不变量 5 的强度一致）。
- `wf doctor` 报告"某任务有归档但 `review/` 缺失"一行；`wf dag` 不变。

---

## 4. 适配清单（逐条带验收）

| # | 现状 | 改法 | 验收 |
|---|---|---|---|
| A1 | 落点 `tmp/multi-cli-review/<task-id>/` | 改为 `$TASK_DIR/review/round-{N}/` | 装好后跑一轮，报告出现在任务目录且 `git status` 可见 |
| A2 | `task-id` 语义含糊 | frontmatter 改用 `dep-id` + `slug`，并校验与 `$TASK_DIR` 一致 | 故意写错 slug，action 侧拒绝消费 |
| A3 | 目录由 reviewer 之外的"coordinator"预建，未说明是谁 | 明确由派发者（fixer）预建 | reviewer 在缺目录时停下并回话，不建目录 |
| A4 | 轮次无上限 | 上限 2 轮 | 第 3 轮派单被 action 侧拒绝（`--round` 超限） |
| A5 | 无身份规则 | `source-cli` ≠ 派发者；校验落在 action 侧 | 用同一 CLI 填 `a` 槽，action 报"同源 reviewer" |
| A6 | 无降级 | 1 provider 降级 + 标记；0 provider 不通过 | 只挂一个 reviewer 跑完，`summary` 含 `degraded` 标记 |
| A7 | 焦点可各自发挥 | 焦点逐字一致 + 来源限定 | 派单模板里两端 `--review-focus` 字符串完全相同 |
| A8 | 无语言/篇幅 | 报告用中文，单条 finding ≤ 8 行，只留可核证据 | 抽查一份报告结构合规 |
| A9 | 无单写者条款 | 两个 skill 各加"不得写源码/`task.json`/账本/不改 commit" | reviewer 说"顺手改了"时以 `git status` 复核 |
| A10 | 与 `trellis-check` 分工未写 | `wf-review` 明写"check 由本 CLI 做，本 skill 不重跑 check 判据" | 派单模板里先出现 check 步骤 |
| A11 | 未分发 | 纳入模块资产与卸载面 | `wf doctor` 报缺；`uninstall --module` 后两 skill 目录消失 |
| A12 | 无探针 | 新增 R1–R5（见 §8） | 探针全绿 |

---

## 5. 文档落点（通过后执行）

| 位置 | 动作 |
|---|---|
| §8.3 | 末段改写：编排已定，`trellis channel` 不再作并列候选 |
| 新 §8.5 | 正文落地：触发点、角色、产物、结论态、降级、适配清单、探针 R 系列 |
| §2.2 / §4.3 | skill 表从 2 扩到 4，补分工行 |
| §1.5 / 附录 B | 增加两个 skill 的写入与路径 |
| §8.1 / §8.4 | 新增 R1–R5 与夹具验收项 |
| §9.6 G7 | 状态改为"编排已定，适配待办"，保留五条边界并注明第③条放宽 |
| §9.5 | 加一行 2026-10-29 裁决（编排只用 `wf-review*`；`trellis channel` 不采用） |

---

## 6. 与不变量 / G7 边界的关系

| 约束 | 影响 | 处置 |
|---|---|---|
| 不变量 3（不新增记录类型） | 报告是过程产物 | 不入 `§6.1` 记录表、不写 `meta`、不写账本 |
| 不变量 5（图内只走机制入口） | 审查不改状态 | 只留痕，`wf doctor` 报告 |
| 不变量 6（完成 = 人判 + 归档） | 审查只是人判的输入 | 不构成完成判据 |
| 不变量 9（不依赖单一 CLI） | 审查者本身要跨 CLI | 恰好加固该条 |
| G7 边界 ① | 不得成门禁 | 满足 |
| G7 边界 ② | 判据须可观察 | "复杂/简单"由派发判据表给出；未定项见 §9 |
| G7 边界 ③ | 原写"变体与 §4.3 skill 面不动" | **放宽**：§4.3 扩到 4 个 skill；变体仍不动（审查提示放 `wf` skill 正文） |
| G7 边界 ④ | reviewer 必须异 CLI | 落为 A5 |
| G7 边界 ⑤ | 审查失败不得视为通过 | 落为 §3.8 |

---

## 7. 为什么不采用 `trellis channel`

| 项 | channel（Pattern C） | 本方案 |
|---|---|---|
| worker 平台覆盖 | 仅 claude / codex | 五平台同构（skill 通道） |
| 产物 | 频道日志，需另定报告格式 | 已有成对的报告/行动契约 |
| 状态耦合 | 频道运行时是额外进程 | 纯文件 + 人派单，无守护进程 |
| 代价 | 平台不对等（pi / dsh / zcode 无法派 worker） | 不依赖任何编排运行时 |

保留为"后续可能实现"（用户已说明允许新增实现），但一期不做。

---

## 8. 实施拆分与探针

| 段 | 内容 | 完成判据 |
|---|---|---|
| S1 | 契约 `review-protocol.md` + 两个内部 skill 正文 + 放置位与 frontmatter | 渲染幂等；四份 frontmatter 字段齐 |
| S2 | 安装/卸载/`wf doctor` 检查 | `install` 后四根齐；`uninstall --module` 后归零 |
| S3 | `wf` skill 的 check 段派发模板 | 模板里 reviewer 焦点逐字相同 |
| S4 | 夹具实测一轮（两份报告 → summary → 采纳 → 复核） | R1–R5 全绿 |

**探针（写入 §8.1，全部必需）**

| # | 断言 |
|---|---|
| R1 | 审查后 `task.json.status` 与 `ledger.json` 字节未变 |
| R2 | 报告落在 `$TASK_DIR/review/round-1/` 且四份文件齐全、frontmatter 合法 |
| R3 | 同 CLI 充当 reviewer 时 action 侧拒绝 |
| R4 | 只有 1 个 provider 时 `summary` 含 `degraded: single-provider`；0 个时结论 `fail` |
| R5 | `uninstall --module` 后四份 skill 目录消失、`trellis update --dry-run` 无新增漂移 |

---

## 9. 待裁决项

| # | 项 | 选项 | 建议 |
|---|---|---|---|
| D1 | 命名 | ① `wf-review*` ② 保留原名 | ①（归属清楚，避免同名互遮） |
| D2 | 报告进库 | ① 进库 ② 留 `tmp/` | ①（跨机可审计） |
| D3 | 全局版 skill | ① 退役 ② 保留为通用协议参考 | ①（两处维护必然漂移）；若保留需写明谁是权威 |
| D4 | 同 CLI 不同模型可否补位 | ① 可以（记 `source-cli` + 模型名） ② 不可以 | ② 严格；① 作为 provider 不足时的第二级降级 |
| D5 | 默认人数 / 轮次 | 2 / 2（见 §3.4） | 照此 |
| D6 | `fail` 是否强制 `wf rework` | ① 允许就地修 ② 一律返工 | ① 就地修，连续 2 轮仍 fail 才要求返工 |
| D7 | 审查缺失是否阻断 `wf close` | ① 不阻断（只在 doctor 报告） ② 阻断 | ① 与"约定层"一致 |
| D8 | 是否随安装器默认分发 | ① 是 ② 可选安装 | ①（否则目标项目不可用） |
| D9 | 复杂度判据（哪些任务要审） | 可观察信号：新建/删除文件数、跨目录、碰 spec/契约、碰安装器或 CLI | 待与人对齐后写表 |

---

## 10. 风险

| 风险 | 影响 | 缓解 |
|---|---|---|
| 审查变成第二套判据 | 与"人判 + 归档"冲突 | 只留痕；R1 断言零状态写入 |
| 报告质量不稳 | 采纳成本高 | 焦点限定 + 条数上限 + action 侧本地复核 |
| provider 只有一家 | 无法异 CLI 审查 | 降级标记 + 人判兜底 |
| 四份 skill 增加维护面 | 漂移 | 契约单源；`wf doctor` 查根；D3 退役全局版 |
