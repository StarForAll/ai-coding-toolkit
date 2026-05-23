# Research: 新项目开发工作流 -- 文档偏移与过时问题综合汇总

- **Query**: 深度分析新项目开发工作流文档的内容偏移和过时问题
- **Scope**: Internal + Mixed (4 维度全面分析)
- **Date**: 2026-05-23

## 分析范围

本次分析覆盖 `docs/workflows/新项目开发工作流/` 下的所有主要文档，按 4 个维度组织：

1. **文档与代码一致性** -- 详见 [doc-code-consistency.md](./doc-code-consistency.md)
2. **文档过时与废弃引用** -- 详见 [doc-staleness-obsolete-refs.md](./doc-staleness-obsolete-refs.md)
3. **源文档与嵌入文档偏移** -- 详见 [doc-embed-drift.md](./doc-embed-drift.md)
4. **文档冗余与跨文档矛盾** -- 详见 [doc-redundancy-contradictions.md](./doc-redundancy-contradictions.md)

## 问题统计

| 严重程度 | 数量 | 分布 |
|----------|------|------|
| HIGH | 3 | test-first 僵尸引用（跨 6+ 文档）、implementation 无专属命令文件、嵌入执行规范格式错误 |
| MEDIUM | 12 | 通俗版 legacy start 引用、mermaid 图过时、阶段编号不一致、plan.md 8 处 test-first 并列、命令映射文件结构遗漏、Skills 表过时标签、路径前缀差异、重复描述等 |
| LOW | 5 | Python 执行器路径不一致、附录 emoji 格式、Intent.md 孤立概念、总纲内联重复、双轨交付重复 |

## 按优先级的全局修复建议

### P0: 必须立即修复（造成新用户困惑或功能误导）

1. **全面清除 test-first 独立阶段/入口引用**：以 `阶段状态机与强门禁协议.md` 第 57 行声明为权威，清理通俗版 mermaid 图、cursor/README.md、plan.md（8 处）、check.md、opencode/README.md、codex/README.md 中的 test-first 独立入口描述。统一为 "implementation（可选测试驱动模式）"。

2. **修复工作流嵌入执行规范.md 第 105、107 行格式错误**：`trellis-Trellis 原生 /finish-work` 是搜索替换误伤，需改为 `trellis-finish-work`。

3. **通俗版.md 中 start -> continue 术语更新**：4 处使用 legacy "start" 的地方全部改为 "continue"，首次出现时加注说明。

### P1: 应尽快修复（影响文档可维护性和完整性）

4. **命令映射.md 文件结构补充 project-audit.md**。

5. **命令映射.md Skills 表 "§5 start" -> "§5 implementation"**。

6. **命令映射.md 下一步推荐 "start" 兜底 -> "continue" 兜底**。

7. **通俗版 mermaid 图重绘**：移除 Test-First 独立节点，对齐 9 阶段状态机。

8. **阶段编号统一**：外包项目扩展.md 和多CLI通用演练.md 的阶段编号需对齐状态机协议。

### P2: 后续优化（减少维护负担）

9. **总纲内联内容瘦身**：变更管理、源码水印、附录一/二/三内容已拆出为执行卡/专项文档，总纲应仅保留声明 + 引用链接。

10. **CLI 入口差异描述集中化**：非 CLI原生适配边界矩阵 的文档应引用该矩阵而非独立重写。

11. **Intent.md 意图文档机制标注状态**：若未集成到任何阶段，标注为"规划中/未集成"。

12. **附录 emoji 标题格式统一为纯 markdown**。

## 关键发现摘要

1. **test-first 是最大的僵尸引用源**：它已合并到 implementation 但在 6+ 文档中仍作为独立入口出现，是新用户最容易产生困惑的点。

2. **start -> continue 迁移在面向用户文档中不完整**：CLI边界矩阵和嵌入执行规范已正确使用 continue，但通俗版（用户第一接触面）仍广泛使用 start。

3. **implementation 是唯一无专属命令文件的活跃阶段**：这与 8 个有专属文件的阶段形成不对称，虽然设计上通过 continue + Phase Router 实现，但缺乏显式说明。

4. **文档冗余是长期维护风险**：总纲、命令映射、通俗版、CLI README 之间存在大量重复描述，每处修改需同步多处，增加了不同步概率。

## 相关 Specs

- `.trellis/spec/agents/index.md` -- agent 托管策略定义
- `docs/workflows/新项目开发工作流/commands/workflow_assets.py` -- 托管资产常量单一事实源
