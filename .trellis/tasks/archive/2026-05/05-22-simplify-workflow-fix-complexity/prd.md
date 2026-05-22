# 简化工作流：修复过度复杂化和边界模糊问题

## Goal

简化 `docs/workflows/新项目开发工作流` 对原生 Trellis 框架的修改，解决过度复杂化、边界模糊、过度补丁化等问题，同时保留核心价值（显式状态文件、阶段切换确认、外包项目门禁、技术架构确认）。

## What I already know

基于深度分析报告（Agent a03bcbda511336cbe），当前工作流存在以下问题：

### 核心问题
1. **过度复杂化**：10个阶段 + 强门禁协议 + 子块机制，学习成本高
2. **边界模糊**：Trellis 原生 vs. Workflow 托管、外包 vs. 通用、阶段 vs. Skill
3. **适用范围窄**：外包项目专用机制占据大量篇幅，但适用场景有限
4. **过度补丁化**：6个 patch 脚本依赖 Trellis 内部实现，维护成本高
5. **设计不稳定**：经验反馈机制反复调整，最终又移除

### 修改性质判断
- **补充性修改**：10个阶段命令 + 15个脚本（部分合理，但过度细分、边界模糊）
- **合并型修改**：workflow.md patch（合理，但文档冗长）
- **破坏性修改**：无
- **过度修改**：子块机制、经验反馈（不合理，增加复杂度、设计不稳定）

### 保留的核心价值
1. ✓ 显式状态文件（workflow-state.json）
2. ✓ 阶段切换需要用户确认
3. ✓ 外包项目的可行性评估和交付门禁
4. ✓ 技术架构确认后的 spec 对齐
5. ✓ "强制 2 个 push URL 的前置条件"（用户明确指出是正确的）

### 需要修复的问题
1. ❌ 过度细分的阶段（10 → 6）
2. ❌ 子块机制（移除）
3. ❌ 外包机制混在通用流程中（拆分）
4. ❌ 过度补丁化（6 → 2）
5. ❌ 经验反馈机制（移除或简化）

## Assumptions (temporary)

1. 用户希望保留工作流的核心价值，但简化过度复杂的部分
2. 修复后的工作流应该更易于理解和使用
3. 外包项目专用机制应该作为可选扩展，而非默认流程
4. 修复应该分阶段进行，优先处理高优先级问题

## Open Questions

### 高优先级修复范围
1. **阶段简化方案**：✓ 已确认 12 → 9（保留 feasibility、brainstorm、design 子块、plan、check、review-gate、project-audit）
2. **workflow-state.json 简化**：✓ 已确认 9个字段 → 7个核心字段
3. **阶段转换逻辑简化**：✓ 已确认，需要在实施过程中特别注意不引入新问题

### 中优先级修复范围
4. **外包项目扩展拆分**：✓ 已确认
5. **review-gate 触发条件优化**：✓ 已确认（不减少条件，优化描述）
6. **补丁脚本精简**：✓ 已确认

### 低优先级修复范围
7. **经验反馈机制移除**：✓ 已确认移除

## Requirements (evolving)

### 高优先级
- [ ] 简化阶段状态机（12 → 9）
  - 保留：feasibility（必需）、brainstorm（需求发现）、design、plan（必需）、implementation、check、review-gate、project-audit、delivery
  - 合并：test-first → 合并到 implementation（作为可选入口）
  - 删除：finish-work + record-session（Trellis 原生已合并，删除工作流中的单独操作）
  - 理由：brainstorm 提供结构化需求发现流程，保证需求质量，不可替代
  - **风险控制**：在实施过程中特别注意不引入新问题，保持现有功能完整性
- [ ] 保留 design 阶段子块机制（块 A/B/C/D）
  - 理由：子块提供强制等待点和顺序性保证，checklist 无法替代
  - 范围：仅 design 阶段使用 current_block / completed_blocks
- [ ] 简化 workflow-state.json（9个字段 → 7个核心字段）
  - 保留：version, stage, status, current_block, completed_blocks, checkpoints, updated_at
  - 移除：stage_status（与 status 语义重叠）、allowed_next_stages（可从阶段定义推导）
- [ ] 简化阶段转换逻辑（STAGE_TRANSITIONS）
  - 从 12个阶段的复杂转换关系简化为 9个阶段的清晰转换规则
  - 保持核心路径：feasibility → brainstorm → design → plan → implementation → check → project-audit → delivery
  - 保留快速路径：brainstorm → plan/implementation（跳过 design）
  - 保留迭代路径：implementation ↔ check、check → review-gate → implementation

### 中优先级
- [ ] 拆分外包项目扩展
  - 当前：外包机制混在工作流总纲中
  - 目标：拆分为独立文档（`工作流总纲.md` + `外包项目扩展.md`）
  - 理由：提高通用流程可读性，外包项目用户按需加载
- [ ] 优化 review-gate 触发条件描述
  - 当前：触发条件描述分散，判定标准不够突出
  - 目标：不减少条件数量，优化文档结构和判定示例
  - 理由：review-gate 在实际开发中一般都要被触发，但需要避免简单任务误触发
  - 重点：明确 "blast radius 明显" 和 "测试证据不足" 的判定标准，突出 anti-pattern
- [ ] 移除过度补丁化
  - 当前：6个 patch 脚本依赖 Trellis 内部实现
  - 目标：只保留 2个核心补丁（patch-inject-workflow-state.py + patch-workflow-phase-strong-gate.py）
  - 理由：减少对 Trellis 内部实现的依赖，降低维护成本，提高升级兼容性

### 低优先级
- [ ] 移除经验反馈机制（可选）
  - 当前：`learn/` 目录 + 反馈模板，反复调整后又移除
  - 目标：完全移除或简化为人工记录
  - 理由：设计不稳定，最终又移除了默认反馈机制

## Acceptance Criteria (evolving)

### 高优先级验收标准
- [ ] 阶段数量从 12个减少到 9个（减少 25%）
- [ ] workflow-state.json 字段从 9个减少到 7个（减少 22%）
- [ ] STAGE_TRANSITIONS 定义清晰，转换规则明确
- [ ] design 阶段子块机制保留且正常工作
- [ ] 移除的阶段（test-first、finish-work、record-session）功能已正确合并
- [ ] 所有现有功能保持完整，无破坏性变更

### 中优先级验收标准
- [ ] 外包项目扩展已拆分为独立文档
- [ ] 工作流总纲篇幅减少约 30%
- [ ] review-gate 触发条件描述清晰，判定标准明确
- [ ] 补丁脚本从 6个减少到 2个（减少 67%）
- [ ] 保留的补丁脚本正常工作

### 低优先级验收标准
- [ ] 经验反馈机制相关代码和文档已移除
- [ ] `learn/` 目录已清理

### 整体验收标准
- [ ] 修改后的工作流能够正常运行
- [ ] 所有阶段命令正常工作
- [ ] 状态转换逻辑正确
- [ ] 文档清晰易懂
- [ ] 无新引入的问题或回归

## Definition of Done (team quality bar)

- 修改后的工作流文档已更新
- 相关脚本已修改或移除
- 测试验证修改后的工作流能够正常运行
- 文档已更新，反映新的工作流结构
- 用户确认修改符合预期

## Out of Scope (explicit)

- 不修改 Trellis 原生框架本身
- 不改变"强制 2 个 push URL 的前置条件"（用户明确指出是正确的）
- 不移除外包项目专用机制，只是将其拆分为可选扩展
- 不修改 design 阶段的子块机制（保留块 A/B/C/D）
- 不减少 review-gate 的触发条件数量（只优化描述）
- 不合并 brainstorm 和 design 阶段（brainstorm 提供不可替代的需求发现价值）

## Technical Notes

### 关键文件位置
- 工作流文档：`docs/workflows/新项目开发工作流/`
- 工作流脚本：`docs/workflows/新项目开发工作流/commands/shell/workflow-state.py`（嵌入后：`.trellis/scripts/workflow/workflow-state.py`）
- 补丁脚本：`docs/workflows/新项目开发工作流/commands/shell/patch-*.py`
- 阶段命令文档：`docs/workflows/新项目开发工作流/commands/*.md`

### 对比项目
- `/tmp/trellis-0.5.17-1`：只进行了 trellis 框架嵌入（原生 trellis）
- `/tmp/trellis-0.5.17-2`：进行了 trellis init 和该工作流嵌入（修改后的 trellis）

### 分析报告
- Agent ID: a03bcbda511336cbe
- 报告包含详细的修改分析、问题识别、修复建议

### 预期效果

修复后可实现：
- 阶段数量减少 25%（12 → 9）
- 状态文件字段减少 22%（9 → 7）
- 补丁脚本减少 67%（6 → 2）
- 工作流总纲篇幅减少约 30%（通过拆分外包扩展）
- 学习成本降低，用户体验提升
- 保持现有功能完整性，无破坏性变更

## Technical Approach

### 实施策略

采用**分阶段、增量式修复**策略，确保每个阶段都可验证、可回退：

#### 阶段 1：高优先级修复（核心简化）
1. **简化阶段状态机**
   - 修改 `workflow-state.py` 中的 STAGES 定义（12 → 9）
   - 修改 STAGE_TRANSITIONS 定义
   - 更新阶段验证逻辑
   - 测试阶段转换是否正常

2. **简化 workflow-state.json**
   - 移除 `stage_status` 字段（与 status 语义重叠）
   - 移除 `allowed_next_stages` 字段（可从阶段定义推导）
   - 保留 design 阶段的 `current_block` / `completed_blocks`
   - 更新状态初始化和验证逻辑

3. **合并和删除阶段**
   - test-first → 合并到 implementation（更新文档和命令）
   - finish-work + record-session → 删除工作流中的单独操作（保留 Trellis 原生）
   - 更新所有引用这些阶段的文档和脚本

#### 阶段 2：中优先级修复（优化体验）
1. **拆分外包项目扩展**
   - 创建 `外包项目扩展.md`
   - 从 `工作流总纲.md` 中提取外包相关内容
   - 更新文档引用和链接

2. **优化 review-gate 触发条件描述**
   - 重组文档结构，突出判定标准
   - 添加判定示例和 anti-pattern
   - 明确 "blast radius 明显" 和 "测试证据不足" 的判定标准

3. **移除过度补丁化**
   - 识别 6个补丁脚本的功能
   - 保留 2个核心补丁（patch-inject-workflow-state.py + patch-workflow-phase-strong-gate.py）
   - 移除其他 4个补丁脚本
   - 验证保留的补丁正常工作

#### 阶段 3：低优先级修复（清理遗留）
1. **移除经验反馈机制**
   - 删除 `learn/` 目录
   - 删除反馈模板
   - 移除文档中的相关描述（§6.6.4、§7.3.1）

### 风险控制措施

1. **备份机制**
   - 修改前备份所有关键文件
   - 使用 git 分支进行修改
   - 每个阶段完成后创建 checkpoint

2. **验证机制**
   - 每个阶段完成后运行验证测试
   - 检查状态转换逻辑
   - 验证阶段命令正常工作
   - 确保无破坏性变更

3. **回退机制**
   - 如果发现问题，立即回退到上一个 checkpoint
   - 分析问题原因，调整方案后重试

### 关键文件清单

需要修改的关键文件：
- `docs/workflows/新项目开发工作流/工作流总纲.md`
- `docs/workflows/新项目开发工作流/commands/shell/workflow-state.py`（嵌入后位置：`.trellis/scripts/workflow/workflow-state.py`）
- `docs/workflows/新项目开发工作流/commands/*.md`（各阶段命令文档）
- `docs/workflows/新项目开发工作流/commands/shell/patch-*.py`（补丁脚本）

需要创建的新文件：
- `docs/workflows/新项目开发工作流/外包项目扩展.md`

需要删除的文件/目录：
- `learn/` 目录（如果存在）
- 4个非核心补丁脚本

## 当前进度与遗留问题

### 已完成（2026-05-22）

#### 1. ✅ 拆分外包项目扩展文档（中优先级任务 4）
- 从《工作流总纲.md》移除约 118 行外包专用内容
- 在文档开头和 5 个关键位置添加对《外包项目扩展.md》的引用
- 文档从 2620 行减少到 2553 行（净减少 67 行）
- 工作流总纲更加通用和简洁

#### 2. ✅ 优化 review-gate 触发条件描述（中优先级任务 5）
- 增加清晰的分隔线（`---`），将各部分明确区分
- 将"blast radius 明显"和"测试证据不足"提升为独立小节（`####` 标题）
- 使用 ✅/❌ 符号标记成立/不成立条件，视觉对比更清晰
- Anti-Pattern 独立成节，使用 ⚠️ 符号突出警示
- 判定结果改为表格形式，更易查阅
- 硬条件改为编号列表，便于引用

#### 3. ✅ 修复补丁脚本依赖问题
- **问题**：`patch-workflow-phase-strong-gate.py` 依赖于已被删除的 `patch-workflow-phase.py`
- **原因**：之前的简化工作误删了核心补丁文件，只保留了包装器
- **解决**：从 git 历史（commit 10a5a90）恢复 `patch-workflow-phase.py` 文件
- **验证**：工作流安装测试通过（/tmp/trellis-0.5.17-2）

### 遗留问题（需要在下次会话中处理）

#### 问题描述

工作流安装后自检发现 **28 个冲突**，主要问题：

1. **缺失的阶段命令**（❌ 高优先级）：
   - `test-first`：在 PRD 中已计划合并到 `implementation`，但安装脚本仍引用
   - `record-session`：在 PRD 中已计划删除（Trellis 原生已合并），但安装脚本仍引用
   - 影响：Claude、OpenCode、Codex 三个平台的命令/skill 都缺失

2. **缺失的补丁脚本**（❌ 高优先级）：
   - `patch-session-start-strong-gate.py`
   - `patch-task-start-strong-gate.py`
   - `patch-task-create-preserve-active.py`
   - `patch-task-status-view-strong-gate.py`
   - 影响：多个强门禁相关的补丁未应用

3. **项目化补丁缺失**（❌ 高优先级）：
   - `finish-work.md`：Claude、OpenCode、Codex 三个平台都缺失项目化补丁
   - `session-start.py`：Claude、Codex 强门禁补丁缺失
   - `task.py`：strong-gate no-status-flip 补丁缺失
   - `common/task_store.py`：preserve-active 补丁缺失
   - `common/tasks.py`：strong-gate task status view 补丁缺失
   - `common/task_queue.py`：strong-gate pending-task 视图补丁缺失

#### 根本原因分析

当前的工作流文档（`工作流总纲.md`、`阶段状态机与强门禁协议.md`）已经按照 PRD 简化为 9 个阶段，但：

1. **安装脚本未同步**：`install-workflow.py` 仍然引用 12 个阶段的旧配置
2. **补丁脚本策略不明确**：PRD 要求"保留 2 个核心补丁"，但实际需要的补丁脚本远超 2 个
3. **阶段合并未完成**：`test-first` 和 `record-session` 的合并/删除工作未完成

#### 下次会话的处理建议

**优先级 1：重新评估补丁脚本策略**
- 检查 PRD 中"保留 2 个核心补丁"的决策是否合理
- 列出所有必需的补丁脚本及其功能
- 决定是保留更多补丁，还是简化补丁逻辑

**优先级 2：完成阶段简化（高优先级任务 1）**
- 更新 `install-workflow.py` 中的阶段列表（12 → 9）
- 移除对 `test-first` 和 `record-session` 的所有引用
- 更新相关的元数据文件和配置

**优先级 3：补齐缺失的补丁脚本**
- 根据重新评估的策略，恢复或创建必需的补丁脚本
- 确保所有强门禁相关的补丁都能正常应用

**优先级 4：验证完整性**
- 重新运行工作流安装测试
- 确保自检通过，无冲突
- 验证所有阶段命令正常工作

#### 当前文件状态

```
M  docs/workflows/新项目开发工作流/commands/review-gate.md
M  docs/workflows/新项目开发工作流/工作流总纲.md
A  docs/workflows/新项目开发工作流/commands/shell/patch-workflow-phase.py
?? docs/workflows/新项目开发工作流/外包项目扩展.md
```

**注意**：这些文件尚未提交，建议在完成所有高优先级修复后一起提交。
