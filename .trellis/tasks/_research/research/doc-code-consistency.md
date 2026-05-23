# Research: 新项目开发工作流 -- 文档与代码一致性分析

- **Query**: 文档描述的步骤、路径、示例命令是否与实际代码/脚本实现一致
- **Scope**: Internal (文档 vs 代码/脚本交叉验证)
- **Date**: 2026-05-23

## Findings

### H-01: implementation 阶段无专属命令文件

| 字段 | 内容 |
|------|------|
| 严重程度 | **HIGH** |
| 文件 | `commands/` 目录 |
| 问题描述 | `workflow-state.py` STAGES 包含 9 个阶段（含 implementation），`workflow_assets.py` DISTRIBUTED_COMMANDS 只含 8 个命令（不含 implementation）。`commands/implementation.md` 文件不存在。implementation 是唯一没有专属命令文件的活跃阶段。当前通过 Trellis baseline `continue.md` + Phase Router 补丁进入，但其他 8 个阶段都有独立 `.md` 命令文件。这种不一致可能导致用户/维护者对"implementation 是否需要独立命令文件"产生困惑。 |
| 建议处理 | 在总纲和命令映射中显式标注 implementation 入口机制（continue + Phase Router），使其差异可被查阅而非隐含。若确认 continue 作为 implementation 入口是长期设计决策，应在 `workflow_assets.py` 中增加注释说明为何 DISTRIBUTED_COMMANDS 不含 implementation。 |

### H-02: 工作流嵌入执行规范.md 中补丁引用格式错误

| 字段 | 内容 |
|------|------|
| 严重程度 | **HIGH** |
| 文件 | `工作流嵌入执行规范.md` 第 105、107 行 |
| 问题描述 | 第 105 行: `Codex trellis-continue / trellis-Trellis 原生 /finish-work patch` -- 出现双重 "Trellis 原生" 标签嵌套，疑似搜索替换操作残留。第 107 行: `legacy start / Trellis 原生 /finish-work patch 残留` -- 同样出现格式混乱。正确表述应为 Codex `trellis-continue` / `trellis-finish-work` patch。 |
| 建议处理 | 修复第 105 行为: `Codex trellis-continue / trellis-finish-work patch`；修复第 107 行为: `legacy start / finish-work patch 残留`。并排查是否有全局搜索替换误伤其他文件。 |

### M-01: cursor/README.md 保留已废弃 test-first 命令映射和部署脚本

| 字段 | 内容 |
|------|------|
| 严重程度 | **MEDIUM** |
| 文件 | `commands/cursor/README.md` 第 9、24 行 |
| 问题描述 | 部署脚本 for 循环仍包含 `test-first`：`for cmd in feasibility brainstorm design plan test-first check review-gate delivery`。命令映射表仍列出 `/trellis:test-first` -> `/test-first`。但 `test-first` 已合并到 implementation 作为可选入口，不再作为独立阶段，也不在 DISTRIBUTED_COMMANDS 中。 |
| 建议处理 | 从部署脚本循环中移除 `test-first`；从命令映射表中移除 `/trellis:test-first` 行；若仍需提供测试驱动入口提示，改为注释说明 implementation 阶段可选测试驱动模式。 |

### M-02: plan.md 中多处引用 test-first 作为 implementation 的并行入口

| 字段 | 内容 |
|------|------|
| 严重程度 | **MEDIUM** |
| 文件 | `commands/plan.md` 第 51、81、281、369、504、505、556、570 行 |
| 问题描述 | plan.md 中 8 处将 `implementation / test-first` 并列描述为两个可选分支，例如"把执行态切到具体叶子 task 的 implementation / test-first 分支"、"是否允许进入 implementation / test-first"。但按阶段状态机协议，test-first 已合并到 implementation 作为可选入口模式，不是独立分支。 |
| 建议处理 | 将 `implementation / test-first` 统一改为 `implementation（可选测试驱动模式）`，与阶段状态机协议保持一致。第 570 行的 `/trellis:test-first` 路由入口应改为通过 `/trellis:continue` + 选择测试驱动模式进入。 |

### M-03: check.md 引用已废弃的 /trellis:test-first 作为回退入口

| 字段 | 内容 |
|------|------|
| 严重程度 | **MEDIUM** |
| 文件 | `commands/check.md` 第 202 行 |
| 问题描述 | 测试或验证证据不足时的推荐入口为 `/trellis:test-first`，但该命令已不在 DISTRIBUTED_COMMANDS 中。 |
| 建议处理 | 改为 `/trellis:continue`（选择测试驱动模式）或显式说明通过 implementation 阶段的可选测试驱动入口进入。 |

### M-04: opencode/README.md 和 codex/README.md 引用 test-first 作为并行入口

| 字段 | 内容 |
|------|------|
| 严重程度 | **MEDIUM** |
| 文件 | `commands/opencode/README.md` 第 168 行；`commands/codex/README.md` 第 266 行 |
| 问题描述 | 两处均写"只有用户明确确认进入 implementation / test-first 后，才允许显式设为 true"，将 test-first 作为与 implementation 并列的入口。 |
| 建议处理 | 改为"只有用户明确确认进入 implementation 后，才允许显式设为 true"。测试驱动模式应在 implementation 内部选择，而非独立入口。 |

### M-05: 命令映射.md 文件结构列表缺少 project-audit.md

| 字段 | 内容 |
|------|------|
| 严重程度 | **MEDIUM** |
| 文件 | `命令映射.md` 第 546-583 行（文件结构部分） |
| 问题描述 | 文件结构的 `commands/` 目录树没有列出 `project-audit.md`，但 project-audit 在 DISTRIBUTED_COMMANDS 中、且有独立命令文件 `commands/project-audit.md`。同时，自然语言路由表（第 497 行）有 project-audit 的路由条目。文件结构列表遗漏会导致维护者误以为 project-audit 不属于命令源文件。 |
| 建议处理 | 在文件结构 `commands/` 目录树中添加 `project-audit.md # §5.1 项目级全局审查`，位于 `plan.md` 和 `check.md` 之间。 |

### M-06: 命令映射.md Skills 表使用过时标签 "§5 start"

| 字段 | 内容 |
|------|------|
| 严重程度 | **MEDIUM** |
| 文件 | `命令映射.md` 第 427-429 行 |
| 问题描述 | Skills 映射表中 `coding-standards`、`simplify`、`karpathy-guidelines` 三个 skill 标注为 `§5 start`，但 `start` 是 legacy 命令，当前 fresh baseline 入口应为 `continue`（含 Phase Router 增强）。应标注为 `§5 implementation` 或 `§5 continue`。 |
| 建议处理 | 将 `§5 start` 统一改为 `§5 implementation` 或 `§5 continue（implementation 入口）`。 |

### M-07: 命令映射.md 下一步推荐仍引用 "start" 兜底

| 字段 | 内容 |
|------|------|
| 严重程度 | **MEDIUM** |
| 文件 | `命令映射.md` 第 468 行 |
| 问题描述 | 下一步推荐输出规范中写"始终包含「不确定 -> start」兜底"，但 `start` 是 legacy 命令，fresh baseline 应为 `continue`。 |
| 建议处理 | 改为"始终包含「不确定 -> continue」兜底"。 |

### L-01: 完整流程演练.md 使用 python3 而非完整路径

| 字段 | 内容 |
|------|------|
| 严重程度 | **LOW** |
| 文件 | `完整流程演练.md` |
| 问题描述 | 使用裸 `python3` 而非 `/ops/softwares/python/bin/python3`，与工作流嵌入执行规范和其他文档的路径规范不一致。 |
| 建议处理 | 统一使用 `/ops/softwares/python/bin/python3`，或在文档开头声明 Python 执行器约定。 |

## Caveats / Not Found

- `commands/implementation.md` 确认不存在；implementation 入口通过 `start-patch-phase-router.md` 补丁到 Trellis baseline `continue.md` 实现
- 未逐一比对每个命令文件中的脚本路径与 `commands/shell/` 实际文件名的一致性（已从 workflow_assets.py HELPER_SCRIPTS 确认列表一致）
