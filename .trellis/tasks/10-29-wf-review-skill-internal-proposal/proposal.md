# 提案：check 阶段多 agent 辅助审查（skill 内部化）

> 状态：**待审**（本轮不写入 `docs/workflows/workflow-implementation.md`）
> 上游决定：
> - 2026-10-29：check 阶段的多 agent 辅助审查**只用**这两个 skill；二者要从仓库全局通用 skill 改为**工作流内部 skill**；它是**基础默认实现**（后续允许新增）；新方案须先人审再落文档。
> - 2026-10-29 补充：命名定为 **`wf-task-review` / `wf-task-review-action`**；审查者只需拿到**任务标识**，任务信息自己从任务里取；主 agent 只调用 action skill 就能拿到对应轮次信息；主 agent 对报告持怀疑态度，报告只辅助不指挥；两个 skill **一律人工主动调用，不自动化**；二者**只在具体任务的 check 阶段使用**。

---

## 0. 结论摘要

| 项 | 结论 |
|---|---|
| 归属 | 从 `skills/` 的通用资产迁为 wf 模块资产（`<MODULE_SRC>/templates/skills/`），随安装器落目标项目 |
| 命名 | `wf-task-review`（reviewer 侧）+ `wf-task-review-action`（主 agent 侧） |
| 契约 | 单源 `templates/review-protocol.md`；两个 skill 只写各自角色动作，`wf` skill 只加"该跑了"的提示 |
| 唯一适用面 | 具体任务的 **check（`trellis-check`）之后、人判之前**，别处不用 |
| 调用方式 | **人工主动调用**；不挂 hook、不等自动触发、`wf doctor` 只报告不代跑 |
| 入参 | 任务标识（依赖标识或 slug）——**只此一项**；轮次可省，由 skill 自行解析 |
| 产物 | `$TASK_DIR/review/round-{N}/…`，随任务进库 |
| 权威关系 | 报告是**辅助证据**，不是指令；主 agent 逐条复核，可采纳、可改法、可驳回，并记录偏离 |
| 状态影响 | 零：不改 `task.json.status`、不写账本、不构成 `wf close` 判据 |
| 扩展位 | 契约把"审查实现"留成可替换位，默认指向这两个 skill；新增实现不改契约 |

一句话：**审查被钉在 check 阶段、由人手动发起、只传任务标识；报告进任务目录，是否照做由主 agent 复核后决定。**

---

## 1. 为什么通用版不适配（证据）

| # | 现状（通用协议） | 冲突 |
|---|---|---|
| 1 | Core Rules 明确"保持 workflow-agnostic"，人数/轮次/封装归上游 coordinator（`skills/multi-cli-review/SKILL.md` Rule 3；`.trellis/spec/skills/index.md` paired-contract 段） | 本工作流要唯一答案的身份、轮次、失败语义 |
| 2 | 落点固定 `tmp/multi-cli-review/<task-id>/`，而 `.gitignore:2` 忽略 `tmp/` | 任务产物要随任务进库、跨机可读 |
| 3 | `task-id` 语义含糊，兼作目录名 | 本工作流有三种身份（§3.3），需明确只传依赖标识或 slug |
| 4 | reviewer 身份靠人给槽位、`source-cli` 自填 | 缺"实施者 CLI 不得审自己"，也无核验点 |
| 5 | 不定义报告缺失/不合格的后果 | 要求"审查失败不得视为通过" |
| 6 | 协议默认由 coordinator 编排，隐含"协调者可以自动派单" | 本工作流确定**只人工发起**，自动派单不是必需能力 |
| 7 | 两 skill 在 `skills/`，未进 `trellis-library/manifest.yaml`，未部署到 `.agents/skills/`、`.claude/skills/` | 目标项目里没有这两个 skill，审查无法执行 |

第 7 条是决定性的：不内部化，"check 阶段用它们"在目标项目里不成立。

---

## 2. 目标形态

### 2.1 资产与命名

| 现状 | 目标 |
|---|---|
| `skills/multi-cli-review/SKILL.md` | `<MODULE_SRC>/templates/skills/wf-task-review/SKILL.md` |
| `skills/multi-cli-review-action/SKILL.md` | `<MODULE_SRC>/templates/skills/wf-task-review-action/SKILL.md` |
| 无 | `<MODULE_SRC>/templates/review-protocol.md`（编排契约，唯一源） |

`wf-task-review*` 同时说明**作用对象（task）**与**归属（wf 模块）**，并与 `wf` / `wf-repair` 的入口型命名区分开：前三者是入口，后两者是任务内的辅助动作。

### 2.2 落点与分发（沿用 §4.1 平台矩阵，不新增平台）

- 投放根：`.agents/skills/` + `.claude/skills/`；不投 `.dsh/skills/`、`.zcode/skills/`、`.pi/prompts/`。
- frontmatter 按 §4.3 渲染，正文同一份，占位符沿用 `{{PYTHON_CMD}}` 等。
- §1.5 `module_owned_paths` 增 4 条；`§7.5` 随模块删除；`skill_roots.py` 白名单从 2 扩到 4。
- 随 `wf install` 分发（不是可选件）：否则目标项目不可用。`wf doctor` 只检查四个 skill 根齐全，不代跑审查。

### 2.3 契约单源

`review-protocol.md` 只写编排（阶段、任务标识解析、轮次、落点、结论态、权威关系、降级）；`wf-task-review` 写"如何在 check 阶段整改一份报告"，`wf-task-review-action` 写"如何不盲信地复核与采纳"。冲突以契约文本为准。

`.trellis/spec/skills/index.md` 的 coupled-pair 段同步改述：paired 关系保留，"保持 workflow-agnostic"改为"编排答案由 `review-protocol.md` 提供"。

### 2.4 与现有 skill 的边界

| skill | 职责 | 变化 |
|---|---|---|
| `wf` | 路由与生命周期；check 阶段提示"该跑审查了"并给一行示例调用 | 正文加 3–5 行，不代跑 |
| `wf-repair` | 账本对账与异常处分 | **不变** |
| `wf-task-review` | 只读任务、只写自己那份报告 | 由通用版改造 |
| `wf-task-review-action` | 逐条复核、人确认后修、写 summary/action | 由通用版改造 |

---

## 3. 编排契约（工作流内专用）

### 3.1 阶段

```
实施 → trellis-check（本 CLI 自查） → 人工在两个以上 CLI 里各调一次 wf-task-review → 主 agent 调 wf-task-review-action → 人判 → wf close
```

- 只在此阶段使用：`wf-task-review` 在非 check 阶段（如刚开工、返工登记中）也允许跑，但结论一律按"check 未通过"解读。
- 与 check 失败重跑交替：重跑 check 不重开轮次；改动大到要重审才开新轮。

### 3.2 调用方式：只人工，不自动

| 项 | 规定 |
|---|---|
| 谁发起 | **人**。reviewer 侧：人在另一个 CLI 会话里说"审 `<任务标识>`"；action 侧：人在主会话里说"按 `wf-task-review-action` 处理 `<任务标识>`" |
| 是否自动 | 否：没有 hook、没有自动派单、没有后台进程。两个 skill 都靠人开口才加载 |
| 主 agent 的角色 | reviewer 侧不代发起，只能把调用串打给人；action 侧在被点名后执行复核与修复 |
| 是否要求 headless | 不要求：交互式会话即可，降低平台不对等 |

### 3.3 入参与任务解析

- 唯一必填入参：**任务标识**——依赖标识（`meta.wf.deps.id`）或 slug，二者取一。
- 任务信息（`prd.md` / `design.md` / `implement.md`、工作区改动、相关 spec）由 skill **自己从任务目录读**，调用方不传。
- 解析规则：按标识扫活动区与归档区；命中 1 个 → 用它；命中 0 个 → 停；命中多个 → 停下要更精确的标识。
- 只接受单个任务：批量审查属后续扩展，不在一期。

### 3.4 轮次

- 调用方**可省**。
- reviewer 侧：轮次 = 现存最大轮次；该任务尚无 `review/` 时 = 1。**同一轮的多个 reviewer 各自算出同一轮次**，因此不靠传参也一致。
- action 侧：默认消费**当前最大轮次**；可用显式 `--round` 覆盖（补判旧轮）。
- 超过上限（默认 2 轮）仍要开新轮 → action 报"轮次上限已到"，由人决定是否放宽。

### 3.5 身份

- `source-cli` 必须 ≠ 实施该任务的 CLI；同一 CLI 不得既实施又补位。
- reviewer-id 是槽位字母（`a` / `b` / `c` / `d`），真实 CLI 身份只进 `source-cli`。
- frontmatter 身份字段拆为 `dep-id` + `slug`，目录校验比对 `$TASK_DIR` 名的 slug 段。

### 3.6 人数与降级

| 项 | 默认 | 说明 |
|---|---|---|
| reviewer 数 | **2 个不同 CLI** | 只有一家可用 → 1 个，报告记 `degraded: single-provider` |
| 0 个 | 结论 `fail`（记 `degraded: none`） | 不得静默跳过 |
| 可用性判定 | 由人判断（手动调用的天然结果） | 不做自动探测 |

### 3.7 产物与写边界

```
$TASK_DIR/review/
  round-1/{a.md,b.md}          # reviewer 只写自己那一个
  round-1/summary-round-1.md   # 只有主 agent 写
  action.md                    # 只有主 agent 写
```

- 进库，随任务归档移动；目录由**主 agent 预建**（reviewer 不建目录）。
- 定位是任务产物，不是新记录类型：不入 §6.1 记录表、不写 `meta`、不写账本。
- reviewer 不写源码、不写 `task.json`、不写账本、不 commit；主 agent 是唯一写者。

### 3.8 审查焦点

调用方不传焦点。焦点由 reviewer 从任务产物派生，检查面固定为：范围是否被超出、验收口径是否被满足、契约/规格是否被违反、跨层影响与回归风险、可测性。允许 reviewer 只报其中命中项，不得自行扩焦到相邻问题。

### 3.9 权威关系：辅助而非指挥

- 报告是**证据**：主 agent 必须逐条对代码、spec、任务边界复核后才能采纳。
- 主 agent 可以：采纳原方案、采纳但改法、降级为备注、驳回（写理由）。
- 驳回与改法必须写进 `action.md`，理由要具体到下一轮不会重炒。
- reviewer 的建议不构成"已批准"，也不产生任何门禁效果。

### 3.10 结论态与失败出口

| 结论 | 含义 | 出口 |
|---|---|---|
| `pass` | 无阻塞项 | 进人判 |
| `pass-with-notes` | 只有低风险建议 | 进人判，建议留档 |
| `fail` | 有阻塞项 | 就地修 → 重跑 check → 下一轮；或走 `wf rework` |

- 报告缺失、frontmatter 不合法、reviewer 与实施者同 CLI、该轮 reviewer 不足（非降级）→ 一律按 `fail`。
- `wf rework` 仍按 §3.12 五步序列，审查不新增返工字段。

### 3.11 与门禁的关系

- 不阻断 `wf close`（约定层，与不变量 5 的强度一致）。
- `wf doctor` 报"任务已归档但 `review/` 缺失"一行；`wf dag` 不变。

---

## 4. 适配清单（逐条带验收）

| # | 现状 | 改法 | 验收 |
|---|---|---|---|
| A1 | 落点 `tmp/multi-cli-review/<task-id>/` | 改 `$TASK_DIR/review/round-{N}/` | 跑一轮后报告在任务目录且 `git status` 可见 |
| A2 | `task-id` 含糊 | frontmatter 改 `dep-id` + `slug`，校验与目录一致 | 故意写错 slug，action 拒绝消费 |
| A3 | 目录归属不明 | 明确主 agent 预建 | 缺目录时 reviewer 停下回话，不建目录 |
| A4 | 轮次无上限、需传参 | 上限 2 轮；轮次可省，按 §3.4 规则自解 | 不传轮次跑一轮，两份报告落在同一 `round-1/` |
| A5 | 无身份规则 | `source-cli` ≠ 实施者，校验在 action 侧 | 同 CLI 补位被拒 |
| A6 | 无降级 | 单 provider 降级标记；0 个 `fail` | 单 reviewer 跑完，summary 含 `degraded` |
| A7 | 焦点由调用方传且要求逐字一致 | 改为 reviewer 自派生固定检查面（§3.8） | 调用只给任务标识，报告检查面齐全 |
| A8 | 无语言/篇幅 | 中文，单条 finding ≤ 8 行，只留可核证据 | 抽查结构合规 |
| A9 | 无单写者条款 | 两 skill 各加"不写源码/`task.json`/账本/不 commit" | reviewer 称改动时以 `git status` 复核 |
| A10 | 与 `trellis-check` 分工未写 | `wf-task-review` 明写"check 由主 CLI 做，本 skill 不重跑其判据" | 调用记录里先有 check |
| A11 | 未分发 | 纳入模块资产与卸载面 | `wf doctor` 报缺；`uninstall --module` 后目录消失 |
| A12 | 无探针 | 新增 R1–R6（§8） | 探针全绿 |
| **A13** | 描述语未限定阶段 | 两份 description 写死"具体任务的 check 阶段、人工调用" | 在非 check 阶段调用时 skill 提示阶段错位 |
| **A14** | 入参是 `<issue-description>` + `[target-path]` | 改为单一任务标识；任务信息内部读 | 只传 slug 即可产出报告 |
| **A15** | action 需人给 `--task-dir` / `--round` | 只给任务标识；轮次自解，`--round` 仅覆盖 | 不传轮次也能消费当前轮 |
| **A16** | 报告被当结论 | 加"辅助而非指挥"条款与偏离记录 | `action.md` 必含驳回/改法理由 |
| **A17** | 隐含自动派单 | 明写"无 hook、无后台、人工发起" | `wf doctor` 只报不跑 |

---

## 5. 文档落点（通过后执行）

| 位置 | 动作 |
|---|---|
| §8.3 | 末段改写：编排已定，`trellis channel` 不再作并列候选 |
| 新 §8.5 | 正文落地：阶段、人工调用、任务标识入参、轮次、权威关系、产物、降级、适配清单、探针 |
| §2.2 / §4.3 | skill 表 2 → 4，补分工与描述语要点 |
| §1.5 / 附录 B | 加两个 skill 的写入与路径 |
| §8.1 / §8.4 | 新增 R1–R6 与夹具验收 |
| §9.6 G7 | 状态改"编排已定，适配待办"，保留五条边界并注明第③条放宽 |
| §9.5 | 加 2026-10-29 裁决行（编排只用 `wf-task-review*`；不采用 channel；人工调用） |

---

## 6. 与不变量 / G7 边界的关系

| 约束 | 影响 | 处置 |
|---|---|---|
| 不变量 3 | 报告是过程产物 | 不入记录表、不写 `meta`、不写账本 |
| 不变量 5 | 审查不改状态 | 只留痕，`wf doctor` 报告 |
| 不变量 6 | 审查只是人判的输入 | 不构成完成判据 |
| 不变量 9 | 审查者本身跨 CLI | 加固该条 |
| G7 ① | 不得成门禁 | 满足 |
| G7 ② | 判据须可观察 | 阶段（check）+ 人工调用即信号；D9 另定清单 |
| G7 ③ | 原写"变体与 §4.3 skill 面不动" | **放宽**：§4.3 扩到 4 个 skill；变体仍不动 |
| G7 ④ | reviewer 必须异 CLI | 落为 A5 |
| G7 ⑤ | 审查失败不得视为通过 | 落为 §3.10 |

---

## 7. 为什么不采用 `trellis channel`

| 项 | channel（Pattern C） | 本方案 |
|---|---|---|
| worker 平台 | 仅 claude / codex | 五平台同构 |
| 产物 | 频道日志，需另定格式 | 已有成对报告/行动契约 |
| 运行时 | 额外进程 | 纯文件 + 人工调用 |
| 与"不自动化" | 派 worker 即自动编排 | 人工调用天然符合 |

保留为后续可实现项，一期不做。

---

## 8. 实施拆分与探针

| 段 | 内容 | 完成判据 |
|---|---|---|
| S1 | 契约 + 两个内部 skill 正文 + 放置位/frontmatter | 渲染幂等；描述语含阶段与人工调用 |
| S2 | 安装/卸载/`wf doctor` 检查 | 安装后四根齐；卸载后归零 |
| S3 | `wf` skill 的 check 段提示 | 提示含一行示例调用与"人工执行"字样 |
| S4 | 夹具实测一轮（两份报告 → 复核驳回一条 → 采纳一条 → summary/action 落盘） | R1–R6 全绿 |

**探针（全部必需）**

| # | 断言 |
|---|---|
| R1 | 审查前后 `task.json.status`、`ledger.json` 字节不变 |
| R2 | 只传任务标识即可产出报告，落在匹配 `round-1/`，frontmatter 合法 |
| R3 | 同 CLI 补位时 action 拒绝 |
| R4 | 单 provider → summary 含 `degraded: single-provider`；0 个 → `fail` |
| R5 | `uninstall --module` 后四份 skill 目录消失、`trellis update --dry-run` 无新增漂移 |
| R6 | 主 agent 驳回某条并改法后，`action.md` 有理由且该条不被下一轮重炒 |

---

## 9. 裁决状态

| # | 项 | 状态 |
|---|---|---|
| D1 | 命名 | **已定**：`wf-task-review` / `wf-task-review-action` |
| D2 | 报告进库 | 待定（建议进库；与 A1 绑定） |
| D3 | 全局版 `multi-cli-review*` 处置 | 待定（建议退役，避免两处维护） |
| D4 | 同 CLI 不同模型可否补位 | 待定 |
| D5 | 默认人数 / 轮次 | 待定（暂写 2 / 2） |
| D6 | `fail` 是否强制 `wf rework` | 待定（暂写：先就地修，连续 2 轮 fail 才返工） |
| D7 | 审查缺失是否阻断 `wf close` | 待定（暂写：不阻断） |
| D8 | 是否随安装器默认分发 | 待定（暂写：是，随装） |
| D9 | 复杂度判据 | 待定（阶段已由"check 阶段"限定，是否再按规模分流仍待定） |
| D10 | 轮次自解规则 | 待定（暂写 §3.4；替代方案：调用必须显式给轮次） |
| D11 | 批量审查（一次多个任务）是否一期做 | 待定（暂写：不做） |
| D12 | 审查产物是否要求随任务归档一起提交 | 待定（依赖 D2） |
| D13 | 阶段错位时（非 check 阶段调用）硬停还是继续并标注 | 待定（暂写：继续并标注） |

---

## 10. 风险

| 风险 | 影响 | 缓解 |
|---|---|---|
| 审查被当成判据 | 与"人判 + 归档"冲突 | R1 零写入 + §3.9 |
| 主 agent 盲信报告 | 修出新问题 | 逐条复核、允许改法、R6 |
| 人工调用易漏 | 该审未审 | `wf doctor` 报告 + `wf` skill 提示 |
| provider 只有一家 | 无法异 CLI | 降级标记 + 人判兜底 |
| 四份 skill 增加维护面 | 漂移 | 契约单源 + D3 退役全局版 |
