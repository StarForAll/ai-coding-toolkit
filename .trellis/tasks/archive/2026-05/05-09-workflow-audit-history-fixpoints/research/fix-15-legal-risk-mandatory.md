# Research: 修复点 #15 项目初始化时必须强制分析法律风险

- **Query**: 审计修复点 #15，检查工作流是否在项目初始化时强制分析法律风险
- **Scope**: internal
- **Date**: 2026-05-09

## Findings

### 安装后产物

| File Path | Description |
|---|---|
| `/tmp/trellis-0.5.9-2/.claude/commands/trellis/feasibility.md` | 项目可行性评估命令，包含法律风险分析硬门禁 |
| `/tmp/trellis-0.5.9-2/.trellis/scripts/workflow/feasibility-check.py` | 可行性验证脚本，包含合规检查与法律风险验证 |
| `/tmp/trellis-0.5.9-2/.trellis/workflow.md` | 工作流总纲，包含 §1.1 合法性审查与 §1.3.1 门禁 |

### 源码文件

| File Path | Description |
|---|---|
| `docs/workflows/新项目开发工作流/commands/feasibility.md` | 源码版可行性评估命令 |
| `docs/workflows/新项目开发工作流/工作流总纲.md` | 源码版工作流总纲 |

### 强制法律风险分析的证据链

1. **feasibility.md Step 1 (行 60-69)**: "法律与合规风险初筛（必须先做）" -- 明确标注"必须先做"，不合规则立即终止
2. **feasibility.md Step 1.5 (行 73-102)**: "法律风险结构化分析（阶段起始硬门禁）" -- 硬门禁，未完成前不得继续 Step 2/3/4
3. **feasibility.md 行 71**: "Step 1 完成后，必须立刻进入法律风险结构化分析；在该分析完成前，不得继续需求粗估、报价、交付控制判断或正式 task 初始化"
4. **feasibility.md 行 99-100**: "硬门禁：Step 1.5 未完成前，Step 2 / Step 3 / Step 4 一律视为未开放"
5. **feasibility-check.py 行 94-102**: `step_compliance()` 函数输出法律合规初筛清单，并提示"如发现不合规，应立即终止项目"
6. **feasibility-check.py 行 263-272**: `step_validate()` 函数验证 `法律/合规风险结论` 字段，缺失则报错
7. **工作流总纲.md 行 207-209**: "法律合规性检查：确认项目在当地法律法规框架下是否合规...如果不符合法律法规，终止项目"
8. **工作流总纲.md 行 241-245**: "风险分析执行"使用 `demand-risk-assessment` skill 完成结构化风险评估

### 机器强制执行机制

- `feasibility-check.py --step validate` 验证 `法律/合规风险结论` 字段是否存在且取值有效
- `feasibility.md` 明确规定 Step 1.5 未完成前，后续步骤"一律视为未开放"
- `workflow-state.py` 与 `feasibility-check.py` 的联动通过 `assessment.md` 字段强制约束

### 与"项目初始化"的关联

- feasibility 是新项目进入 workflow 的**强制前置门禁**（feasibility.md 行 11: "对于新项目 / 新客户需求 / 首次立项，`/trellis:feasibility` 是进入 `/trellis:brainstorm` 前的强制前置门禁"）
- 法律风险分析在 feasibility 阶段 Step 1 + Step 1.5 即强制执行，早于需求粗估和报价
- 因此，法律风险分析在项目初始化时点确实是**强制且前置的**

## 审计判定

- **是否满足**: ✅ 已满足
- **证据**: feasibility.md 行 60-102; feasibility-check.py 行 94-102, 263-272; 工作流总纲.md 行 207-209, 241-245
- **与上次对比变化**: 上次审计未单独标记此项有问题；本次确认法律风险分析在可行性评估阶段作为硬门禁强制执行，且早于所有商业判断步骤

## Caveats / Not Found

- 法律风险结构化分析的深度依赖 `demand-risk-assessment` skill 的执行质量，而 skill 本身是 AI 辅助执行，存在主观判断空间
- `feasibility-check.py --step validate` 只验证字段存在性和取值有效性，不验证风险评估内容的实际质量
