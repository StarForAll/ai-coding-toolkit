# Design：变体正文结构 + G6 拆分裁决

## 0. 权威与证据边界

| 层 | 文档 | 本任务的用法 |
|---|---|---|
| 设计 | `docs/workflows/workflow-design.md` §4.1（四段）、§4.2（三值状态）、§9.1（三段入口）、§9.4（卸载） | 变体的语义来源，**不重写、不改动** |
| 机制细节 | `docs/workflows/依赖机制设计说明.md` | 术语一致（前置集合 / 账本 / 挂起 / 返工） |
| 实现 | `docs/workflows/workflow-implementation.md` §3.1 / §3.5 / §3.7 / §3.8 / §2.2 / §9.5 / §9.6 | 变体引用的命令面与状态口径；本任务只改 §9.6 + 新增 §9.7 |
| 硬约束 | `.trellis/spec/docs/workflow-implementation-constraints.md` | 三值状态、无证据链、平台中立、不依赖 hook |
| 原生契约 | `common/workflow_phase.py`、`common/workflow_selection.py` | `实测`（2026-10-28，本仓库 0.7.0-beta.4） |

## 1. 原生解析契约（变体必须满足的机械条件）

| 条件 | 实现事实 | 对变体的约束 |
|---|---|---|
| C1 变体解析 | `workflow_selection.resolve_workflow_md` 逐层取 `.trellis/workflows/<id>.md`，缺失即回落 `.trellis/workflow.md` | 夹具里只需 `.trellis/config.yaml` + `.trellis/workflows/wf.md`（已实测） |
| C2 Phase Index 起点 | 逐字等于 `## Phase Index` 的行 | 变体必须有该行，且哨兵在其后 |
| C3 Phase Index 终点 | 逐字等于 `## Phase 1: Plan` 的行；缺失则**到文件末尾** | 变体必须出现该行作分隔，否则整份变体被当索引注入 |
| C4 索引裁剪 | `get_phase_index` 先剥 `[workflow-state:*]` 块、再剥 `<!-- -->`、再压空行 | 哨兵**不能**写在注释或状态块内；三值块不会出现在 `--mode phase` 输出（已实测） |
| C5 步骤提取 | `#### X.Y …` 到下一个 `####` / `## ` / 列 0 的 `---` | 步骤用 `#### X.Y`；步骤体内不得出现列 0 的 `---` |
| C6 平台过滤 | 形如 `^\[…\]$` 且首字符为字母的行被当平台 marker，平台不匹配时**整段丢弃** | 变体不得出现 `[wf route]` 一类方括号独立行；不写 marker（R6） |

## 2. 变体结构骨架

```text
<!-- wf:module_version={{MODULE_VERSION}} -->      ← R3；由 render 替换（T2）
（前置说明：本文件是变体；判定权威是设计稿，本文件只提示顺序与入口）

## Phase Index                                     ← C2
  哨兵行（纯文本）                                 ← R1
  ### 四段结构与出口（映射设计稿 §4.1）             ← R4
  ### 入口：三段判定（映射设计稿 §9.1 / 方案 §3.7） ← R4
  ### 机制入口（方案 §3.5 的命令面）                ← R4/R8
  ### 自检与修复（方案 §3.8）                       ← R4
  [workflow-state:planning] … [/workflow-state:planning]        ← R2
  [workflow-state:in_progress] … [/workflow-state:in_progress]  ← R2
  [workflow-state:completed] … [/workflow-state:completed]      ← R2

## Phase 1: Plan        （= 设计稿 §4.1 项目层）    ← C3 分隔点
  #### 1.1 立项与基线
  #### 1.2 任务图与收尾任务定义
  #### 1.3 项目层收尾
  #### 1.4 按图建任务
## Phase 2: Execute     （= 任务层）
  #### 2.1 取就绪任务
  #### 2.2 开工
  #### 2.3 执行与人判
  #### 2.4 收尾
  #### 2.5 返工
## Phase 3: Finish      （= 收尾层）
  #### 3.1 收尾任务
  #### 3.2 验收、交付与发布
  #### 3.3 项目收尾判定
## 持续使用             （= 第四段）
  #### 4.1 迭代任务
  #### 4.2 建边与基线变更
```

**为什么沿用 `Phase 1/2/3` 标题与 `1.x–4.x` 步号**：C3 是唯一可用的索引截断点，且各平台 hook
与上游 `trellis-continue` 都以 `--step 2.1` 这类基底式编号取正文。变体保留**容器名**
（Phase 1/2/3 + 持续使用），**语义按设计稿四段重写**：每节首行显式标注"本节 = 设计稿 §4.1 的哪一段"，
避免读者把容器名当基底阶段语义。这不是"另造判定"（R5）：变体不新增任何判定，只做映射与入口提示。

## 3. 关键设计决定

| ID | 决定 | 理由 / 代价 |
|---|---|---|
| E1 | 变体落 `docs/workflows/wf-variant.md`，文件头注明"位置交接前的暂存落点，T2 迁入 `<MODULE_SRC>/templates/wf.md.tmpl`" | 交接未做，写进 `.trellis/workflows/` 或模块源路径会与本仓库现状不符；代价是 T2 多一次单文件迁移 |
| E2 | 哨兵串 = `WF-VARIANT-SENTINEL:1d9c4b7e`（纯 ASCII、无方括号、无中文、含半随机后缀） | 满足 R1；不会被 `filter_platform` 当 marker（C6），不会被正文偶然撞车；W1 断言精确串 |
| E3 | 两个占位符：`module_version` 用 `{{MODULE_VERSION}}`，步骤加载行的解释器用 `{{PYTHON_CMD}}`（方案 §4.3 的占位符表） | 本变体尚未成为模块源；写死假版本或 `python3` 会在 T2 变成"版本漂移 / Windows 不可执行"隐患。夹具断言不依赖占位符的字面值 |
| E4 | 三值块只含 planning / in_progress / completed，**不含** `no_task` / `stale` / `task_error` | R2；后三者是基底指针态而非任务状态，指向它们会把基底指针语义引回变体；缺失时 hook 降级为通用提示（可见即提示修），属 W7 增强面 |
| E5 | 变体**不写**状态转移表、不写就绪公式 | R5；判定归 `wf route` / `wf state`，变体只写"必须先跑这两条、再按输出行动" |
| E6 | 每个状态块与每张映射表都落到具体命令名（含尚不存在的 `wf …`） | R8；命令不存在时变体给出唯一合法动作：按设计稿 §9.4 卸载（只卸载、不绕过） |
| E7 | 章节顺序：四段 → 三段入口 → 机制入口 → 自检 → 状态块 | 与 §3.7 的"逐段判定、命中即停"同序，AI 从上往下读即可定位 |
| E8 | 文字语言 = 中文（命令/路径/标识原样） | 与设计稿、方案一致 |

## 4. 与三层判定的逐条映射（预期交付形态，实施时逐条落表）

| 方案 § | 条目 | 变体承载位置 |
|---|---|---|
| §3.5 | `task new` / `start` / `close` / `edge` / `rework` / `replace` / `abandon` / `baseline --light` / `repair` / 只读五命令 | "机制入口"表：入口 → 类别（只读/有副作用/人类专用）→ 前置一句话 |
| §3.5 | `--allow-empty-context`（start）、`--skip-branch-validation` + `pr_url is None`（close） | "机制入口"表脚注：这两条是机制入口的内部约定，AI 不直接调原生命令 |
| §3.7 | 第一段 全局旁路（模块不可用 / 完整性分流 / 改基线） | 入口表第 1 行：命中即停 → `wf repair` / 卸载 / 回设计稿 §5.5 |
| §3.7 | 第二段 挂起（四行） | 入口表第 2 行：交给 `wf route` 的 `matched_row`，AI 只按输出执行 |
| §3.7 | 第三段 非挂起（未收尾两表 + 已收尾三行） | 入口表第 3 行：`wf route` 输出 + 下沉规则一句话 |
| §3.8 | `wf check` 只读自检；类型 1–5 只经 `wf repair` | "自检与修复"段：AI 不许自行判定修复类型，必须 `wf check --json` 后交人 |
| §2.2 | skill 与变体的分工（日常流转 / 异常处分） | 文件头一行：`wf` skill 承载日常，`wf-repair` 承载异常 |

## 5. G6 裁决（用户已选：选项 1 三段 · 资产先行）

| 任务 | 边界 | 依赖 | 验收要点 | 产生的"半成品态" |
|---|---|---|---|---|
| **T1 = 本任务** | G6 裁决记录 + 变体正文（`wf-variant.md`） | — | 夹具 W1/W2 + R2–R8 静态断言 + 三层映射表 | 变体是未归属模块源的单文件：无渲染器、无安装器、无 CLI |
| **T2** | 位置交接 + 四 skill 处置 + 模块源骨架（`module.yaml` / `workflow.yaml` / `render.py`）+ 变体迁入 `templates/wf.md.tmpl` | T1 | 交接可核 + grep 归属 + render 幂等 + 夹具 W1/W2 复跑 | 有变体源与渲染器、无机制 |
| **T3** | 最小闭环机制面（账本读取 + 只读五命令 + `task new`/`start`/`close` + `install/uninstall` + ZCode + `wf` skill + 探针 + G0 + §7.6 往返） | T2 | 一条真闭环 + 探针全绿 + `trellis update --dry-run` 无新增漂移 | 内部"只读先绿、写后绿"，首个里程碑即"能装能收尾" |

### 5.1 对 §8.2 的两处修正提案（写入 §9.7，标注"待 D4 确认"）

1. **账本读取前移进 T3**：§8.2 把 `wf route/state/dag/check` 放 P0，却把"账本读写"放 P1；
   而 §3.7 的三段判定与 §3.8 的组合分类都读账本。缺账本读取的 P0 命令面只能报"未实现"。
2. **`wf close` 前移进 T3**：§8.2 的 P0 ⑫ 要求 §7.6 往返验收"走完开工/收尾"，而 `wf close` 在 P1。
   否则 P0 结束态是"装上却只能原生 archive 收尾"，直接踩不变量 5（图内收尾只走机制入口）。

### 5.2 传递项（本任务不裁决）

| ID | 内容 | 承接 |
|---|---|---|
| D4 | 上述两处修正是否采纳（改 §8.2 阶段表） | 用户裁决，T3 前 |
| N4 | 两个 audit skill 实体在 `.claude/`、`.agents/`，与"不改平台目录"冲突 | T2 开工前放行 |
| D5 | 仓库内 18 处"模块源"指路（`docs/` 5、`.trellis/spec/` 12、`AGENTS.md` 1）改写口径：建议"旧模块已退役，模块源见方案 §2.1"，**不**指向 gitignored 的 `tmp/` | T2 |

## 6. 验证设计

| 层 | 手段 | 判据 |
|---|---|---|
| 解析面 | 临时夹具（`tmp/…`，用完即删）：`.trellis/config.yaml` 设 `default_workflow: wf`，`.trellis/workflows/wf.md` = 变体 | `--mode phase` 含哨兵（W1）；`--step 1.1`/`2.4` 返回正文（W2）；`--platform dsh` 与不带平台输出一致 |
| 文本面 | 正则可核清单（见 implement.md §3） | R2/R3/R6/R7 计数为 0 或 3；R4 两张表齐全 |
| 仓库面 | `git status` 只含本任务预期路径；`.trellis/config.yaml` 的 `default_workflow` 仍为注释态 | 本仓库未被变体"启用" |

## 7. 风险与回退

| 风险 | 处理 |
|---|---|
| 变体被当成"新状态机" | 每张表只写"入口 + 交给谁判"，判定句一律引用设计稿/方案章节号；交付前 grep 不得出现转移表样式 |
| 哨兵与正文撞车 | 哨兵含半随机后缀；交付说明写明精确串，W1 用精确匹配 |
| 夹具污染仓库 | 夹具建在 `tmp/`（gitignored），验证后 `rm -rf`；本仓库 `.trellis/config.yaml`、`.trellis/workflows/` 零改动 |
| 改 §9.6 + 新增 §9.7 引起文档漂移 | 只改这两处；§9.5 的既有裁决行一字不动；交付前 diff 复核 |
| 回退 | 删除 `docs/workflows/wf-variant.md` + `git checkout` 恢复 `workflow-implementation.md` 两处改动即可，无其它副作用 |
