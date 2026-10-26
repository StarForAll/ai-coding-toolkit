# 审查交付与待审批修正计划

## 当前阶段

`in_progress`。C1–C3 与 v42 修订及后续反馈已完成，用户明确“人工审查通过，继续后续操作”。已进入 Trellis Phase 3.4 提交准备；具体19路径提交计划已获用户“确认”，按工作提交、finish-work归档与会话记录顺序执行。

## 已完成的审查工作

- [x] 读取主稿、配套与相关 spec，核对版本、工作区和历史。
- [x] 按 §0.1 六项扫描并记录结果；执行已登记探针。
- [x] 筛选主发现、执行反驳检验，形成根因、排除项和修正方向。
- [x] 保存审查报告与证据，保持唯一任务，等待人工决定。
- [x] 补做修改前方案复核，记录简单修法反例与 42 项候选合同下的路径预期；不把人工推演记成实现测试。

## 人工批准后才能执行

- [x] F1–F3 已由用户确认。
- [x] D1 已确认：接受说明字段中的单个当前登记标记，PRD/design/implement 已收敛，不保留两套冲突方案。
- [x] 展示最终修复规划，获得后续明确实施批准；再按 Trellis 1.4 启动同一任务。不创建新任务或子任务。
- [x] 固定 `pre-change-review.md` 的窗口/角色/权限预期为验收基线；保留原 v41 反例、探针及哈希。若有需求变化，显式记录变化而不覆盖旧证据。
- [x] 先改 §7.8 的字段许可与当前登记标记规则，再改 §6.4 登记序列/取消/窗口，以及表 4-2 行 2/3/7 的触发和守卫；不要在摘要处再造动作顺序。
- [x] 同次修订更新 §7.7 类型 2、启动评估、§9.1 全局登记恢复和所有清挂起评估点；检查基底创建时当前指针残留仍被入口接管。
- [x] 按 C2 更新 §6.5 解析域与终点、§7.4 活动下游范围；类型 1/3/4/5 的优先处置与 §9.1 消费结果保持一致。
- [x] 按 C3 统一类型 4 权限、正常写入与受控恢复的边界；同步归档只读/返工来源例外，防止恢复预写未建指向或已归档来源时再次无出口。
- [x] 核对同类生产者：首次/重复/追加/嵌套返工；替换 R 与替代 R；P 的替换/放弃/类型 1 补建；正常完成与归档待修复。
- [x] 同步配套各镜像/引用；按 `design.md` 唯一源及消费者清单逐项填同步结果，而非仅查本次改动行。
- [x] 更新现有 spec 注册表、相关探针与审查指南的实际适用项；不得仅改探针预期使其通过。重跑后另存本版结果。
- [x] 主稿/配套同升 v42，最后写修订记录，只描述已核对的变更；不修改 `1.2-零补丁嵌入方案.md`。
- [x] 执行下述验证，交付 diff 和新证据；再停下等待人工复核。

## 批准后的文件清单

| 文件 | 允许的改动 |
|---|---|
| `docs/workflows/workflow-design.md` | C1–C3 的唯一源、直接消费者、相应验收与版本记录 |
| `docs/workflows/依赖机制设计说明.md` | 对应状态表、返工、恢复、身份的镜像/引用与版本 |
| `.trellis/spec/docs/index.md` | 直接相关谓词注册表、探针及其证据范围 |
| `.trellis/spec/guides/design-review-thinking-guide.md` | 直接补入快照可辨识性/引用输入域/权限交叉核对，现有扫描口径跟随主稿，不另堆同义门禁 |
| 本任务文件 | 人工决策、计划、同步清单、修后验证；原始 v41 证据保持可查 |

以上清单已获用户实施批准，实际产品/spec 改动未超出范围。扩大清单仍须返回人工审查。

## 验证计划

本轮：

```bash
git diff --check
/softwares/python/bin/python3 .trellis/scripts/task.py current --source
/softwares/python/bin/python3 .trellis/scripts/task.py list
git status --short --untracked-files=all
git diff -- docs/workflows/workflow-design.md docs/workflows/依赖机制设计说明.md
```

另对任务 JSON、链接、Markdown 围栏、主稿/配套 SHA-256 做定向检查；审查专用 `probe-results.json` 保存实际执行的命令、期望和命中。注册表中的目录级探针限定到主稿与配套，避免读取明确排除的实现方案，因此不声称覆盖整个 `docs/workflows/`。

未来修复（以已选定的 C1–C3 为合同）：

- F1：重跑 `pre-change-review.md` W01–W18，覆盖提交边界 × 历史集合，以及基底创建前后、重入、取消、存量无标记；快照不可对应互斥恢复动作。
- F2：重跑 R01–R11，保留正常下游边；活动下游处分完成和归档正常非法组合检查分别保持合法出口。
- F3：重跑 F01–F13，每个许可输出与禁止条件交叉核对；包含原合法空值、预写未创建指向、已归档来源修复及禁止消除未完成登记意图。
- 重新执行 §0.1 口径 10–14 与文本探针；不能仅调整期望值来消除反例。
- 对启用新口径前的存量挂起人工确认义务，只核对设计是否清楚交给实现方案；本轮不执行迁移或真实项目探针。
- 按 trellis-check 检查完整 diff、未跟踪文件和任务约束；不运行与文档变动无关的大型代码测试。

## 收尾门

人工复核已通过，用户明确授权继续后续操作；按 Phase 3.4 仍须对具体提交计划取得一次确认。具体计划已获确认，仅提交所列本任务文件，再依 trellis-finish-work 执行任务归档和会话记录；不推送。

## 最终规划摘要（实施批准对象）

- 目标：在同一任务内修复 F1–F3，保留既有正常使用能力，减少因状态不可辨识、引用输入域错误和修复权限冲突导致的反复修补。
- 关键方案：C1 用现有说明字段标记当前未完成返工登记；C2 分离 P 身份解析与正常/异常完成判定并统一活动下游范围；C3 类型 4 仅恢复当前仍合法的既有关系。
- 范围：上方文件清单的主稿、配套、两份相关 spec 和本任务材料；主稿/配套同升 v42。继续排除 `1.2-零补丁嵌入方案.md`、模块实现、迁移执行、上游修改与收尾。
- 执行：先唯一源，后消费者及镜像，再验收和探针，最后写修订记录；若扩大到新字段/状态/机制或需要不能满足的定位条件，返回规划。
- 验收：按原始预期对实际修订文本重跑 42 项、口径 10–14、关联探针；核对全部副本与差异；修复后交人工复核。文本计数和路径推演分别报告，不承诺未经验证的零回归。
- 材料：PRD 已完成收敛，design/implement 完备；inline 模式不使用子代理，不要求 JSONL 配置。
- 当前状态：人工审查与具体提交计划均已确认，按计划执行后续步骤，不再重复询问。

## 当前人工门

- [x] 根据用户同版反馈，核证并精修 P 完成行归档表述及嵌套返工候选范围；八项定向回放及34条探针结果见 fix-notes/verification。
- [x] 核证持久化枚举反馈，统一主稿 §3 与全部范围副本；类型3专行不加前置限制，普通选择行限定无记录；轻量路径引用既有就绪/挂起源，复核结果见 fix-notes/verification。
- [x] 澄清首次新记录必要载体与已有记录字段变更的提交边界；补齐两份事实表身份字段与 status 摘要，明确清单未入库和真实项目自检未运行的验收限制。
- [x] 人工审查 v42 的实际差异、42 项路径与副本清单。
- [x] 用户明确“人工审查通过，继续后续操作”，已授权继续提交及 finish-work 流程。
- [x] Phase 3.4 具体19路径提交计划已由用户明确“确认”；工作提交执行结果以Git历史为准。
- [ ] 工作提交完成后执行 task.py archive 与 add_session.py，核对提交顺序和最终工作区。

## Phase 3.4 提交计划（已确认）

一个工作提交：`workflow-design v42：返工登记恢复、P 解析分域与持久化范围收口`。下列19个路径构成一个完整变更单元：两份产品设计、两份相关spec及本任务的全部规划/审查/证据材料；没有不明来源脏文件。只暂存这些路径，不使用全仓库 git add。

- `.trellis/spec/docs/index.md`
- `.trellis/spec/guides/design-review-thinking-guide.md`
- `docs/workflows/workflow-design.md`
- `docs/workflows/依赖机制设计说明.md`
- `.trellis/tasks/10-26-review-workflow-design-v41/audit-checks.md`
- `.trellis/tasks/10-26-review-workflow-design-v41/audit-inventory-v42.json`
- `.trellis/tasks/10-26-review-workflow-design-v41/check.jsonl`
- `.trellis/tasks/10-26-review-workflow-design-v41/design.md`
- `.trellis/tasks/10-26-review-workflow-design-v41/fix-notes.md`
- `.trellis/tasks/10-26-review-workflow-design-v41/implement.jsonl`
- `.trellis/tasks/10-26-review-workflow-design-v41/implement.md`
- `.trellis/tasks/10-26-review-workflow-design-v41/prd.md`
- `.trellis/tasks/10-26-review-workflow-design-v41/pre-change-review.md`
- `.trellis/tasks/10-26-review-workflow-design-v41/probe-results-v42.json`
- `.trellis/tasks/10-26-review-workflow-design-v41/probe-results.json`
- `.trellis/tasks/10-26-review-workflow-design-v41/review-report.md`
- `.trellis/tasks/10-26-review-workflow-design-v41/structural-checks-v42.json`
- `.trellis/tasks/10-26-review-workflow-design-v41/task.json`
- `.trellis/tasks/10-26-review-workflow-design-v41/verification-v42.md`

工作提交之后按原生 finish-work：本任务从未有独立分支，真实记录为 main/main，归档使用技能明确规定的 `--skip-branch-validation`；不篡改分支元数据。归档自动提交之后，用工作提交哈希记录会话日志，日志不纳入归档提交哈希。不推送。本节保留获批计划，实际执行结果以工作提交、归档元数据与会话日志为准。
