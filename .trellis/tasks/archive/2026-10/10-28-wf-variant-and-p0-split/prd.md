# PRD：wf 变体正文与 P0 拆分裁决

## 1. 背景与目标

上一轮任务（`10-28-workflow-implementation-plan`，已归档）交付了实现方案
`docs/workflows/workflow-implementation.md`（1447 行，16 条冲突已裁决）。该方案 §9.6 遗留两项未定：

| 项 | 内容 |
|---|---|
| **G5** | 流程变体 `.trellis/workflows/wf.md` 的正文内容（Phase Index 与设计稿 §4.1 四段的映射、§9.1 三段入口提示词） |
| **G6** | 是否拆出 P0 实现任务、怎么拆 |

本任务交付这两项：G5 产出变体正文（核心交付物），G6 产出并落定拆分裁决（已选"三段 · 资产先行"）。

## 2. 范围

### 2.1 交付

1. **变体正文**：落 `docs/workflows/wf-variant.md`（位置交接尚未做，按用户指定走临时落点；T2 再迁入
   `<MODULE_SRC>/templates/wf.md.tmpl`）。
2. **G6 裁决记录**：在 `docs/workflows/workflow-implementation.md` 新增 §9.7（P0 实施拆分裁决），
   并把 §9.6 的 G5 / G6 两行状态从"待定"改为已裁决 + 指向新节。
3. **验收证据**：临时夹具内的 W1 / W2 断言结果 + 逐条对应表（§3.5 机制入口、§3.7 三段入口、§3.8 自检入口）。

### 2.2 明确不做

- 不实现 CLI（`wf ...`）、安装器、`render.py`、skill 正文（G5 只交变体文本）。
- 不做位置交接（旧模块移入 `tmp/`）、不建新模块源骨架 —— 这些是 T2。
- 不改 `docs/workflows/workflow-design.md`、`docs/workflows/依赖机制设计说明.md`（权威文档）。
- 不改本仓库平台目录（`.zcode/ .claude/ .codex/ .pi/ .dsh/ .agents/`）与 `.trellis/workflow.md`。
- 不在本仓库设 `default_workflow: wf`、不写 `.trellis/workflows/`。
- 不启动 P1–P5，不写 `.trellis/spec` 之外的规格改动（§3.3 例外见 implement.md）。

## 3. 需求（变体正文的硬约束，逐条可核）

| # | 约束 | 判据 |
|---|---|---|
| R1 | 含**哨兵串**，供 W1/W2 断言"读到的确实是本变体" | `get_context.py --mode phase` 输出含该串；串只在 Phase Index 区、纯文本行 |
| R2 | 含**三个** `[workflow-state:*]` 块，只对应 `planning` / `in_progress` / `completed` | 全文正则计数 = 3；不含任何 `wf-*` 或自定义状态值 |
| R3 | 含模块版本注释行 `<!-- wf:module_version=… -->` | 行存在，位于文件头部 |
| R4 | Phase Index 语义映射设计稿 §4.1 四段（项目层 / 任务层 / 收尾层 / 持续使用）与 §9.1 三段入口（全局旁路 / 挂起 / 非挂起） | 变体内有两张映射表，且每段/每行都指向机制入口命令 |
| R5 | **不另造判定、不重复定义状态机** | 判定一律引用设计稿与方案章节号；变体不出现新的判定公式或状态枚举 |
| R6 | **不出现平台分支** | 无 `[Claude Code, …]` 一类 marker 行、无平台名、无 frontmatter |
| R7 | **不写** declare / verify / 证据记录环节 | 无 `wf declare` / `wf verify` / `impl_sha` / 证据链字样 |
| R8 | 文案能让 AI 执行者判断"下一步做什么"，并指向机制入口命令名（`wf route` / `state` / `task new` / `start` / `close` / `repair` 等，即使尚不存在） | 三值块与入口表内均出现具体命令名 |

## 4. 验收判据

- **A1**：临时夹具（`.trellis/config.yaml` 设 `default_workflow: wf` + `.trellis/workflows/wf.md` 为变体）中，
  `get_context.py --mode phase` 输出含哨兵串（W1）；`--mode phase --step <X.Y>` 返回变体步骤正文（W2）；
  结果记录后**清理夹具**，本仓库配置零改动（`git status` 只含本任务改动）。
- **A2**：R2–R8 的静态断言全过（命令清单见 implement.md）。
- **A3**：交付说明给出"变体哪一段对应 §3.5 / §3.7 / §3.8 的哪一条"的逐条对应表。
- **A4**：`docs/workflows/workflow-implementation.md` 的 §9.6 / §9.7 与本任务裁决一致，且不出现"正文按 A 写、登记说 B"的漂移。

### 4.1 对用户原验收口的一处修正（已实测）

原表述"`get_context.py --mode phase` 返回哨兵串**与三值块**"按现实现不可能同时成立：
`get_phase_index()` 会主动剥离 `[workflow-state:*]` 块与 HTML 注释
（`common/workflow_phase.py`）。因此 A1 拆为两条：三值块用文件级正则断言（R2），
平台注入面属 W7 增强探针（DSH 记 N/A）。

## 5. 依赖与前置

- 权威文档：`docs/workflows/workflow-design.md`、`docs/workflows/依赖机制设计说明.md`、
  `docs/workflows/workflow-implementation.md`、`.trellis/spec/docs/workflow-implementation-constraints.md`（均已读）。
- 原生契约以 `.trellis/scripts/common/workflow_phase.py`、`workflow_selection.py` 的当前实现为准（`实测`）。

## 6. 遗留决策（本任务不裁决，转入后续任务）

| ID | 内容 | 承接方 |
|---|---|---|
| D4 | 最小账本读取与 `wf close` 是否前移进"最小闭环机制面" | T3（本任务只在 §9.7 记入提案） |
| N4 | 位置交接须处置的两个 audit skill 位于平台目录，与"不改平台目录"冲突 | T2 |
| D5 | 仓库内 18 处"模块源"指路的改写口径（不指向 gitignored 的 `tmp/`） | T2 |
