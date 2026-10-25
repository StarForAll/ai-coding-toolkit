# 执行计划

## 步骤

1. **读源 + 建决策日志（只读）**
   - 通读 `docs/workflows/workflow-design.md` 全文、§0.1 A/B 表、§0 写作约定与事实边界、附录 C 全部版本条目（当作已定决策，不翻案）。
   - 读配套文档 §13 实现口径与 §22 v34 记录，确认哪些是设计决定、哪些只是引用。
   - 读上一轮报告与 remediation-plan 的排除候选表，把已定过的误报族列为不再翻案项。

2. **探针基线**
   - 逐条跑 `.trellis/spec/docs/index.md` 的 8 条探针，记录实数值与期望值比对结果。

3. **候选收集（不判）**
   - 按 `design.md` 的六个高风险面 + §0.1 A/B 逐条扫描，记录 §/行、规则、场景、期望 vs 实际。

4. **过滤与反驳**
   - 对每个候选依次过 F1–F4 与四步反驳；存活项定级，写不出反驳句的留作主发现，能写出反驳句的降为措辞或进排除表。

5. **写报告**
   - 按 `design.md` 的输出契约落 `review-report.md`，含结论计数、主发现、措辞项、排除表、探针结果、版本核对。

6. **自检**
   - 每条引用回原文件核行号；核每条主发现都写了影响阶段与最小修复；核排除表覆盖误报族；`rg` 复核报告里没有悬空引用。

7. **交付 + 等结论**
   - 向用户汇报主发现数量与摘要，问是否在本任务继续修复；修复阶段再按“判定源唯一”协议执行（源 → 引用 → 探针 → 附录 C），主稿与配套同提交。

## 验证命令

```bash
# 探针（期望值以 .trellis/spec/docs/index.md 为准）
rg -n "按 §3 有效（" docs/workflows/workflow-design.md
rg -n "有当前任务，且该任务未归档、账本为|有当前任务，但该任务未归档、账本为|有当前任务，但该任务已归档" docs/workflows/workflow-design.md
rg -n "按 §3 有效|按 §3 无效" docs/workflows/workflow-design.md
rg -n "依赖满足 =|就绪.*前置集合全部为" docs/workflows/workflow-design.md docs/workflows/依赖机制设计说明.md
rg -n "满足判定按 §4.3|按主设计 §4.3" docs/workflows/workflow-design.md docs/workflows/依赖机制设计说明.md
rg -n "指向已归档、规划中且前置未满足" docs/workflows/依赖机制设计说明.md
rg -n "或为“正常但未归档”的任务|前置未完工（或为" docs/workflows/workflow-design.md docs/workflows/依赖机制设计说明.md
rg -n "视为无当前任务" docs/workflows/workflow-design.md

# 引用核验
git status --short
```

## 风险与回滚点

- 风险：把留白 / 取舍写成缺陷 → 回滚点：每写入一条主发现前必须先写作者反驳句。
- 风险：重复上一轮已否掉的候选 → 回滚点：先读排除表。
- 审查阶段不动产品文件，回滚成本≈0。
