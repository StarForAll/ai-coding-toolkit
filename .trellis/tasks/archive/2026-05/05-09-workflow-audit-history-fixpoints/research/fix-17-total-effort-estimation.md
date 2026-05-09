# Research: 修复点 #17 项目总工时估算

- **Query**: 审计修复点 #17，检查工作流是否支持项目总工时估算
- **Scope**: internal
- **Date**: 2026-05-09

## Findings

### 安装后产物

| File Path | Description |
|---|---|
| `/tmp/trellis-0.5.9-2/.claude/commands/trellis/brainstorm.md` | brainstorm 命令，包含项目级粗估门禁 |
| `/tmp/trellis-0.5.9-2/.claude/commands/trellis/feasibility.md` | feasibility 命令，包含工作量评估 |
| `/tmp/trellis-0.5.9-2/.trellis/workflow.md` | 工作流总纲，包含工时估算相关段落 |
| `/tmp/trellis-0.5.9-2/.trellis/scripts/workflow/feasibility-check.py` | 可行性验证脚本 |

### 源码文件

| File Path | Description |
|---|---|
| `docs/workflows/新项目开发工作流/commands/feasibility.md` | 源码版可行性评估命令 |
| `docs/workflows/新项目开发工作流/工作流总纲.md` | 源码版工作流总纲 |

### 工时估算的证据链

1. **工作流总纲.md 行 216-217**: "工作量评估：功能开发工时 + 评审工时 + 测试工时 + 文档工时"，"时间成本分析：按里程碑拆分，给出最早/最晚交付窗口"
2. **工作流总纲.md 行 218-223**: 资源成本核算、AI 相关成本核算、风险预判
3. **工作流总纲.md 行 228**: "本阶段的时间/报价输出默认是商务预判与区间策略，不替代需求澄清后的正式项目级粗估；正式粗估必须在阶段二 brainstorm 收口前落盘"
4. **brainstorm.md 行 304-315**: "项目级正式需求文档门禁"中明确要求：
   - "在进入 design、plan 或任何执行阶段前，必须先产出不可跳过的项目级粗估"
   - "若暂时无法给出单点值，也必须给出区间估算与适用前提；'后面再说''先不估'都不算通过"
   - "由 workflow-state.py validate 强制检查项目级粗估门禁"
5. **brainstorm.md 行 42**: "需求已准确并准备离开 brainstorm 时，必须先产出项目级粗估；该粗估不能跳过，也不能只停留在口头描述里"
6. **brainstorm.md 行 281**: "当前项目级粗估相对 feasibility 是否已经刷新；若没有变化，也必须写清'为什么不变'"
7. **feasibility.md 行 128-131**: 评估阶段允许输出商务预判和预算区间策略，但"不承担需求澄清后的正式项目级工期承诺"
8. **feasibility-check.py 行 147**: assessment.md 模板中包含 `付款结构` 和 `工期/里程碑` 两个关键字段快照行
9. **工作流总纲.md 行 928**: 变更影响评估中包含"预计增加多少工时？是否影响当前里程碑、费用或交付节奏？"
10. **工作流总纲.md 行 1911**: 任务规格模板包含 `预估工时: X小时或X人天`

### 分层工时估算体系

| 阶段 | 估算性质 | 精度 | 强制程度 |
|---|---|---|---|
| feasibility (§1.3) | 商务预判/区间策略 | 粗 | 允许给出区间，不要求精确值 |
| brainstorm (§2.1.1) | 项目级正式粗估 | 中 | 硬门禁：未落盘不得进入 design |
| plan (§4) | 任务级预估 | 细 | 每个任务有 `预估工时` 字段 |
| 变更管理 (§2.5) | 变更影响估算 | 按需 | 重大变更必须评估 |

### 机器强制执行

- `workflow-state.py validate` 在 design/plan 入口强制检查项目级粗估是否落盘
- brainstorm.md 明确"由 workflow-state.py validate 强制检查项目级粗估门禁"
- feasibility-check.py 验证 assessment.md 中 `工期/里程碑` 字段存在性

### 项目总工时字段的覆盖情况

- feasibility 阶段：assessment.md 模板中有 `工期/里程碑` 字段（feasibility-check.py 行 148）
- brainstorm 阶段：要求产出 `项目级粗估`（brainstorm.md 行 304），并要求写入 `task_dir/prd.md` 的 `## 项目级粗估` 和 `customer-facing-prd.md` 的 `## 项目级粗估摘要`
- plan 阶段：每个任务规格模板有 `预估工时` 字段
- 但**没有**单独的 `total_effort` / `总工时` 机器字段在 assessment.md 或 prd.md 模板中被显式定义

## 审计判定

- **是否满足**: ⚠️ 部分满足
- **证据**: 工作流总纲.md 行 216-228; brainstorm.md 行 42, 281, 304-315; feasibility-check.py 行 147-148; 工作流总纲.md 行 1911
- **缺口描述**: 工时估算在各阶段有明确要求（feasibility 商务预判 -> brainstorm 项目级粗估 -> plan 任务级预估），且 brainstorm 阶段有硬门禁强制落盘。但**缺少独立的 `total_effort` / `总工时` 机器字段**，工时估算目前分散在多个自然语言描述中：
  - assessment.md 模板只有 `工期/里程碑` 快照行，没有显式的总工时数值字段
  - prd.md 的 `## 项目级粗估` 是自由格式描述，没有标准化的总工时字段契约
  - plan 阶段的任务级 `预估工时` 是单任务维度，没有汇总到项目总工时的机制
- **与上次对比变化**: 当前版本增加了 brainstorm 阶段的项目级粗估硬门禁，比之前更强；但仍缺少标准化的总工时机器字段

## Caveats / Not Found

- `workflow-state.py validate` 具体如何检查"项目级粗估"门禁未在本轮审计中读取到源码验证（该脚本不在 workflow scripts 目录列表中）
- 项目级粗估的内容格式由 brainstorm 命令定义但未在 feasibility-check.py 中做字段级校验
