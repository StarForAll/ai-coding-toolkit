# Research: 新项目开发工作流 -- 文档过时与废弃引用分析

- **Query**: 文档中是否存在对已不存在的文件/命令/配置的引用，阶段定义跨文档是否一致，Trellis API 兼容性
- **Scope**: Internal (跨文档一致性验证)
- **Date**: 2026-05-23

## Findings

### H-01: test-first 作为独立阶段的僵尸引用广泛存在

| 字段 | 内容 |
|------|------|
| 严重程度 | **HIGH** |
| 文件 | 多文件（6+ 处） |
| 问题描述 | `阶段状态机与强门禁协议.md` 第 57 行明确声明"test-first 已合并到 implementation 阶段作为可选入口，不再作为独立阶段"。但以下文档仍将 test-first 描绘为独立阶段或独立入口：1) `通俗版.md` mermaid 图（第 70-71 行）显示 "4.3 Test-First" 为独立节点；2) `通俗版.md` 第 354-368 行有 "4.3 Test-First" 独立章节；3) `cursor/README.md` 命令映射表含 `/trellis:test-first`；4) `cursor/README.md` 部署脚本循环含 test-first；5) `plan.md` 8 处将 implementation / test-first 并列；6) `check.md` 第 202 行引用 `/trellis:test-first`；7) `opencode/README.md` 第 168 行和 `codex/README.md` 第 266 行引用 implementation / test-first 并列入口。 |
| 建议处理 | 全局搜索替换，将 test-first 独立入口引用清除：mermaid 图中删除 4.3 Test-First 节点及连线；cursor/README.md 删除 test-first 行和部署循环项；plan.md 中 implementation / test-first 统一改为 implementation（可选测试驱动模式）；check.md 入口改为 continue；opencode/codex README.md 删除 test-first 并列。 |

### M-01: 通俗版.md 多处使用 legacy "start" 替代当前 "continue"

| 字段 | 内容 |
|------|------|
| 严重程度 | **MEDIUM** |
| 文件 | `工作流全局流转说明（通俗版）.md` 第 234、358、544、576 行 |
| 问题描述 | 1) 第 234 行: `L0：很小...可以直接进 start` -- 应为 continue；2) 第 358 行: `进入某个 task 实现前会由 start 自动执行 before-dev` -- 应为 continue；3) 第 544 行: `回到 start 修复` -- 应为 continue（implementation）；4) 第 576 行: `进入 start，自动补当前 task 的门禁` -- 应为 continue。通俗版是用户第一接触面，legacy 术语会导致新用户困惑。 |
| 建议处理 | 将所有 `start` 引用改为 `continue`，并在首次出现时注明 `continue` 含 Phase Router 增强，替代了旧版 `start`。 |

### M-02: 通俗版.md mermaid 图阶段编号与实际状态机不一致

| 字段 | 内容 |
|------|------|
| 严重程度 | **MEDIUM** |
| 文件 | `工作流全局流转说明（通俗版）.md` 第 64-87 行 |
| 问题描述 | mermaid 流程图中：1) Project-Audit 标为 "5.1" 但在总纲阶段编号中是独立阶段（§5.1）；2) Check 标为 "5.1.x" 而非独立编号；3) Review-Gate 标为 "5.1.y"；4) Delivery 标为 "6+7" 而非 "6"；5) Test-First 标为 "4.3" 作为独立节点（已废弃）。workflow-state.py STAGES 列表为: feasibility, brainstorm, design, plan, implementation, check, review-gate, project-audit, delivery。流程图的编号体系与实际 9 阶段状态机不一致。 |
| 建议处理 | 重绘 mermaid 图，使用实际 9 阶段名称和顺序，移除 Test-First 独立节点。编号应与阶段状态机协议保持一致。 |

### M-03: 外包项目扩展.md 阶段编号跳跃

| 字段 | 内容 |
|------|------|
| 严重程度 | **MEDIUM** |
| 文件 | `外包项目扩展.md` |
| 问题描述 | 使用"阶段一、阶段三、阶段四、阶段六"编号，跳过阶段二和阶段五，缺乏一致性。读者无法确认是刻意的阶段跳跃还是笔误。 |
| 建议处理 | 统一为与阶段状态机协议一致的编号（§1 feasibility, §2 brainstorm, §3 design, §4 plan, §5 implementation, §5.1 project-audit, §5.1.x check, §5.1.y review-gate, §6+§7 delivery），或改为直接使用阶段名而非编号。 |

### M-04: 多CLI通用新项目完整流程演练.md 阶段编号跳过 9

| 字段 | 内容 |
|------|------|
| 严重程度 | **MEDIUM** |
| 文件 | `多CLI通用新项目完整流程演练.md` |
| 问题描述 | 阶段编号从 8（Delivery）直接跳到 10（Finish-Work），跳过 9。若是有意为之（如 9 曾预留给某个已废弃阶段），应加注释说明；否则是编号错误。 |
| 建议处理 | 若 Finish-Work 不是 workflow 阶段而是 Trellis 原生收尾，建议改为"终态：Finish-Work"而不参与阶段编号序列；或补齐 9 并注释。 |

### L-01: 附录：评估安全与意图机制.md 使用 emoji 标题格式

| 字段 | 内容 |
|------|------|
| 严重程度 | **LOW** |
| 文件 | `附录：评估安全与意图机制.md` 第 6、95、115 行 |
| 问题描述 | 使用 emoji 标题（🧪 附录一、🔒 附录二、📑 附录三），与工作流其他文档的纯 markdown 标题格式不一致。 |
| 建议处理 | 移除 emoji 前缀，改为纯文本标题以保持格式一致。 |

### L-02: 附录 Intent.md / 意图文档维护机制未被任何工作流阶段引用

| 字段 | 内容 |
|------|------|
| 严重程度 | **LOW** |
| 文件 | `附录：评估安全与意图机制.md` 附录三；`工作流总纲.md` 第 2531-2538 行 |
| 问题描述 | Intent.md 意图文档维护机制在总纲和附录中有定义，但没有任何阶段命令文件（feasibility/brainstorm/design/plan/implementation/check/delivery）引用它，也没有任何 CLI README 引用它。命令映射.md 和通俗版.md 同样未引用。这像是一个孤立的附录概念，未集成到实际工作流执行路径中。 |
| 建议处理 | 若 Intent.md 机制已废弃或暂缓，在总纲和附录中标注为"规划中/未集成"状态；若仍计划集成，至少在 design 或 delivery 阶段命令中添加引用。 |

### L-03: 总纲附录内容重复 -- 同时保留内联摘要和外部文件引用

| 字段 | 内容 |
|------|------|
| 严重程度 | **LOW** |
| 文件 | `工作流总纲.md` 第 2504-2538 行 |
| 问题描述 | 总纲在"附录一/二/三"标题下既保留了简短摘要，又引用外部 `附录：评估安全与意图机制.md`。如果外部文件已是完整版，总纲的内联摘要和标题应大幅缩减为仅引用链接，避免两处维护同一内容。 |
| 建议处理 | 将总纲附录段改为仅保留标题 + 外部文件链接 + 一句话说明，删除内联摘要内容。 |

## Caveats / Not Found

- 未发现总纲中引用了完全不存在的文件路径（所有 `[xxx](./xxx.md)` 引用的文件均存在）
- 未发现 workflow_assets.py COMPATIBLE_TRELLIS_VERSION (0.5.17) 与实际 Trellis 版本的不兼容问题（需要实际运行验证）
