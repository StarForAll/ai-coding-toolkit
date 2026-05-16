# Research: Issue 1 - Workflow fact source splits

- **Query**: Does workflow.md three-phase model contradict AGENTS.md gate chain?
- **Scope**: Internal
- **Date**: 2026-05-16

## Findings

### Files Found

| File Path | Description |
|---|---|
| `/tmp/trellis-0.5.16-2/.trellis/workflow.md` | Embedded workflow guide with Plan/Execute/Finish three-phase model |
| `/tmp/trellis-0.5.16-2/AGENTS.md` | Trellis instructions with feasibility/brainstorm/design/plan gate chain |
| `/ops/.../工作流总纲.md` | Source workflow definition with 7-phase model (feasibility through delivery) |
| `/ops/.../阶段状态机与强门禁协议.md` | Strong gate protocol and stage state machine |

### Analysis

#### workflow.md three-phase model (lines 142-244 of embedded workflow.md)

The embedded `workflow.md` organizes work into 3 native phases:
- **Phase 1: Plan** (lines 164-456) -- covers task creation, brainstorm, research, context curation, activation
- **Phase 2: Execute** (lines 194-551) -- covers implementation, quality check, rollback
- **Phase 3: Finish** (lines 224-244) -- covers verification, debug retrospective, spec update, commit, wrap-up

However, the Phase Index block (line 144-152) lists 7 stages:
```
Phase 1: Feasibility → 项目可行性评估
Phase 2: Brainstorm  → 需求明确与确认
Phase 3: Design      → 技术架构与设计
Phase 4: Plan        → 任务拆解与规划
Phase 5: Implement   → 代码实现与自检
Phase 6: Check       → 质量检查与验证
Phase 7: Delivery    → 交付与收尾
```

And the `no_task` breadcrumb (lines 158-162) does reference feasibility first:
> Entry sequence: (1) load `feasibility` skill ... (2) if assessment allows, load `trellis-brainstorm` skill ...

The `planning` breadcrumb (line 175) also requires feasibility precondition:
> **前置条件**：已完成feasibility阶段，且`assessment.md`明确允许进入brainstorm。

#### AGENTS.md gate chain (lines 36-51)

The AGENTS.md natural language routing table maps intents to a gate chain:
- feasibility -> brainstorm -> design -> plan -> test-first -> check -> review-gate -> finish-work -> delivery

This is consistent with the 7-phase model in workflow.md's Phase Index.

#### 工作流总纲.md (source)

The source workflow defines the full 7-phase chain explicitly in sections:
- 阶段一：项目可行性评估 (feasibility)
- 阶段二：需求明确与确认 (brainstorm)
- 阶段三：设计阶段 (design)
- 阶段四：任务分解与准备 (plan)
- 阶段五：开发实施循环 (implementation)
- 阶段六：项目整体测试 (check)
- 阶段七：交付与沉淀 (delivery)

### Verdict: PARTIAL

**Evidence of consistency:**
1. The `workflow.md` Phase Index (line 144-152) and breadcrumb blocks DO reference the 7-phase chain with feasibility first
2. The `no_task` breadcrumb correctly routes through feasibility -> brainstorm
3. The `planning` breadcrumb correctly enforces feasibility precondition
4. AGENTS.md routing table is consistent with the 7-phase model

**Evidence of residual inconsistency:**
1. The section HEADINGS in workflow.md still use the old 3-phase naming: "Phase 1: Plan", "Phase 2: Execute", "Phase 3: Finish" (lines 164, 194, 224). These headings do NOT align with the 7-phase Phase Index or the gate chain.
2. The Phase 1 section (titled "Plan") actually contains both feasibility and brainstorm content, collapsing two distinct gates into one native phase.
3. The Phase 2 section (titled "Execute") collapses design/plan/implementation into one phase.
4. A model reading the HEADINGS would see "Plan -> Execute -> Finish" which is the old model; a model reading the Phase Index or breadcrumb blocks would see the 7-phase gate chain.

**The core tension:** workflow.md's structural sections (Phase 1/2/3 with their detailed walkthroughs) use the old 3-phase framing, while the Phase Index, breadcrumb blocks, AGENTS.md routing table, and 工作流总纲.md all use the new 7-phase gate chain. These are NOT outright contradictory in behavior (the breadcrumbs enforce the right gates), but the heading-level framing creates conflicting mental models depending on which part the AI reads.

### Source files involved

- `docs/workflows/新项目开发工作流/工作流总纲.md` -- defines the 7-phase model; this is the source of truth
- The workflow.md template (generated during install) -- its Phase 1/2/3 section headings were never updated to match the 7-phase model; the Phase Index and breadcrumbs were updated but the section structure was not

### Proposed fix scope

1. **workflow.md source template**: Update Phase 1/2/3 section headings and structure to align with the 7-phase gate chain, or remove the misleading 3-phase section structure entirely
2. **No change needed** to: AGENTS.md, breadcrumb blocks, Phase Index -- these already reflect the correct gate chain
3. **No change needed** to: 工作流总纲.md or 阶段状态机与强门禁协议.md -- these are consistent

## Caveats / Not Found

- The contradiction is in naming/framing, not in actual gate enforcement -- the breadcrumb blocks correctly enforce the 7-phase gates
- The old 3-phase section structure may be intentionally preserved for backward compatibility or simplicity -- needs confirmation from workflow maintainers
