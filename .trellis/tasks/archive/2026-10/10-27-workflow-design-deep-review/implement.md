# 执行计划：workflow-design.md 深度审查

## 0. Current gate

- [x] 仅创建一个 Trellis 任务。
- [x] 读取主设计 §0.1、关联 docs/guides spec、配套文档版本与已确定口径。
- [x] 写入 `prd.md`、`design.md`、`implement.md`。
- [ ] 向人工提交最终规划摘要并等待明确批准。
- [ ] 未获批准前不得运行 `task.py start`，不得开始完整审查。

## 1. Activate after explicit planning approval

- [ ] 复核 `prd.md`、`design.md`、`implement.md` 未发生实质变化。
- [ ] 运行 `task.py validate 10-27-workflow-design-deep-review`。
- [ ] 运行 `task.py start 10-27-workflow-design-deep-review`，使任务进入 `in_progress`。
- [ ] 确认仍只有这一个任务承载本请求。

## 2. Establish the evidence baseline

- [ ] 完整读取 `docs/workflows/workflow-design.md` 当前 1104 行内容，不只读取命中片段。
- [ ] 完整读取 `docs/workflows/依赖机制设计说明.md` 当前 476 行内容，限定为镜像、引用、版本和反驳证据。
- [ ] 读取任务规划产物与注入的两个关联 spec。
- [ ] 明确记录 `1.2-零补丁嵌入方案.md` 不在读取与证据范围内。
- [ ] 建立当前版本、规范区、附录区、有意取舍和历史决策日志。

## 3. Run three review surfaces inside the same task

所有研究提示必须以 `Active task: .trellis/tasks/10-27-workflow-design-deep-review` 开头；研究者只能写指定的任务研究文件，禁止修改产品文档。

### 3.1 Surface A — acceptance paths

- [ ] 枚举全文人判点并核对“由人决定”。
- [ ] 枚举 P 的正常完成、返工、替换、放弃、类型 1 补建、异常未完成及归档前后路径。
- [ ] 复核类型 1–5 的输入、动作、产出态和组合表合法性。
- [ ] 将证据、候选和排除项写入 `research/sweep-a.md`。

### 3.2 Surface B — rule and recovery integrity

- [ ] 构建重叠规则情形矩阵，覆盖承重字段、角色、归档态、继任者存在性和修复入口。
- [ ] 枚举封闭断言并追踪全部产生路径。
- [ ] 构建识别字段 × 角色 × 修复入口的权限交叉表。
- [ ] 建立判定/动作序列/状态清单的唯一源与副本清单。
- [ ] 回放 `§N` 引用输入域和多步动作窗口。
- [ ] 运行 `.trellis/spec/docs/index.md` 的注册探针，逐条核对命中上下文与期望值。
- [ ] 将证据、候选和排除项写入 `research/sweep-b.md`。

### 3.3 Surface C — adversarial rebuttal

- [ ] 对照 §0 有意取舍、A/B 验收表、配套 §13 和 v25–v45 决策记录。
- [ ] 对每个候选执行承载层、决策日志、留白/冲突、正常使用/篡改四层过滤。
- [ ] 执行全文反驳搜索、端到端场景模拟、最简合规实现测试和带 § 的作者反驳。
- [ ] 对同一对象重复动作和中断快照做可区分性检查。
- [ ] 将证据、候选和排除项写入 `research/sweep-c.md`。

## 4. Synthesize the review report

- [ ] 综合三份 sweep，按根因去重，不按表面出现次数拆分发现。
- [ ] 对每条幸存主发现补齐：约束编号、精确证据、触发场景、四类来源、必然影响、最小改善方向、反驳为何失败。
- [ ] 将仅措辞/精度问题、版本漂移和证据边界独立成节。
- [ ] 将所有低于缺陷门槛但值得说明的候选写入“Excluded”，说明排除原因。
- [ ] 把口径 10 六项扫描、口径 11 副本清单、口径 12 引用回放、口径 13/14 窗口与残留态、注册探针结果写入 `research/review-report.md`。
- [ ] 检查报告没有引用或依赖 `1.2-零补丁嵌入方案.md`。
- [ ] 检查工作区：产品文档、spec、测试和实现资产均未因审查被修改。

## 5. Mandatory review stop

- [ ] 向人工汇报 `research/review-report.md` 的结论与文件位置。
- [ ] 明确任务仍保持开启。
- [ ] 停止；不修复、不更新 spec、不提交、不归档、不执行 finish-work。

## 6. Conditional future root-cause phase — only after human accepts findings and asks for repair

- [ ] 记录人工对每条发现的接受/驳回/降级/补证据决定。
- [ ] 对获准修复的发现追踪：产生路径 → 冲突/无出口点 → 唯一源 → 全部消费者 → 现有探针为何漏检。
- [ ] 分类根因：源规则缺失、重复定义漂移、调用输入域错误、例外孤儿化、路径/窗口漏枚举、权限交叉冲突、探针覆盖/期望失真或其他有证据类别。
- [ ] 枚举同类载体和角色六面，判断是否为问题族而非单点。
- [ ] 将根因、证据、影响面、最小源级修复策略和验证矩阵写入 `research/root-cause-analysis.md`。
- [ ] 向人工提交根因分析并停止；未获确认不得编辑产品文档。

## 7. Conditional future repair phase — only after root-cause approval

- [ ] 按“源 first → projections → probes → revision note last”修改。
- [ ] 主设计与配套镜像同版同步；不建立补丁层，不复制新的判定定义。
- [ ] 更新所有受影响副本、引用、窗口、探针预期和同类载体。
- [ ] 运行口径 10–14 全量复核和 docs spec 注册探针。
- [ ] 运行与变更范围对应的仓库验证。
- [ ] 复核最终 diff，并写 `research/fix-notes.md`。

## 8. Mandatory post-fix stop

- [ ] 向人工提供 diff、验证结果、根因到修复的映射和剩余风险。
- [ ] 停止；不提交、不归档、不执行 finish-work。
- [ ] 仅在人工明确表示审查通过并要求收尾后，才进入 Trellis Phase 3 的 spec 判断、提交计划与最终收尾。

## Validation commands

规划阶段：

```bash
/softwares/python/bin/python3 ./.trellis/scripts/task.py validate 10-27-workflow-design-deep-review
git diff --check
```

审查阶段按 `.trellis/spec/docs/index.md` 当前注册表逐条执行 `rg` 探针，并保存实际结果；不能只复制注释中的期望数。审查报告完成后至少运行：

```bash
git status --short
git diff -- docs/workflows/workflow-design.md 'docs/workflows/依赖机制设计说明.md' .trellis/spec
```

预期：审查阶段上述产品/规范路径无 diff；只允许当前 Trellis 任务目录新增或更新研究产物。

## Rollback points

- 任何研究者误改产品资产：立即停止，不继续综合；先隔离并报告误改，不用覆盖式操作掩盖。
- 发现证据不足：将候选标为待补证据或排除，不通过推测抬升为主发现。
- 规划边界发生实质变化：退回 Phase 1 更新三份产物并重新请求人工批准。
- 人工驳回根因或修复边界：保持任务开启，停止编辑，不转入收尾。
