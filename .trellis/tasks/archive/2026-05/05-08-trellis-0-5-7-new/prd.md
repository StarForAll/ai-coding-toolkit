# PRD: 清理 trellis 0.5.7 升级遗留的 .new 文件并修正配置一致性

## 问题背景

trellis 从 0.5.6 升级到 0.5.7 过程中，生成了 64 个 `.new` 文件。经分析发现存在以下问题：

1. **版本倒退冲突**：部分 `.new` 文件是在 commit `36a27cc`（回退 trellis-research 工具简化）之后生成的，内容与当前正确版本冲突
2. **工具配置被错误简化**：`trellis-research` agent 的 `.new` 版本丢失了 ace、Context7、deepwiki、grok-search 等关键 MCP 工具
3. **Phase 编号不一致**：`continue.md.new` 和 `finish-work.md.new` 使用错误的 Phase 编号（1.3/1.4 而非 1.2/1.3，3.4 而非 3.1）
4. **跨平台配置不一致**：不同平台（.kiro, .codex, .qoder 等）的 agent 配置需要保持工具列表一致性

## 验证结论

### ✅ 正确的修改（已提交）
- `.trellis/.version`: 0.5.6 → 0.5.7
- `.trellis/config.yaml`: 新增 codex dispatch_mode 配置
- `.trellis/scripts/common/workflow_phase.py`: 新增 workflow 步骤提取功能
- `.trellis/scripts/common/git_context.py`: 集成 workflow_phase 模块
- `.codex/agents/trellis-check.toml`: 新增 context 加载指引，禁用 multi_agent
- `.codex/agents/trellis-implement.toml`: 同上
- `.kiro/agents/trellis-research.json`: 字段重命名（需补充工具列表）

### ❌ 错误的 .new 文件（必须丢弃）
- `.claude/agents/trellis-research.md.new`: 工具列表被错误简化
- `.claude/commands/trellis/continue.md.new`: Phase 编号错误
- `.claude/commands/trellis/finish-work.md.new`: Phase 编号错误
- 其他平台对应的 trellis-research .new 文件

### ⚠️ 需要审查的 .new 文件
- skills、hooks、references 等其他 .new 文件需要逐个比对

## 验收标准

### AC1: 丢弃错误的 .new 文件
- 删除 trellis-research agent 相关的所有 .new 文件
- 删除 continue.md.new 和 finish-work.md.new
- 确保当前正确版本不受影响

### AC2: 修正跨平台 trellis-research 配置
- `.kiro/agents/trellis-research.json`: 补充完整的 allowedTools 列表
- 其他平台（.qoder, .opencode 等）如有类似问题一并修正

### AC3: 审查并合并其他 .new 文件
- 逐个比对剩余 .new 文件与原文件差异
- 确认 Phase 编号引用正确
- 确认工具配置完整
- 决定合并策略（保留原版本 / 合并变更 / 丢弃 .new）

### AC4: 提交正确的修改
- 提交已验证正确的文件修改
- 清理所有已处理的 .new 文件
- 确保工作区干净

### AC5: 验证一致性
- 运行 `.trellis/scripts/get_context.py` 验证 workflow phase 功能
- 确认所有平台的 agent 配置工具列表一致
- 确认 Phase 编号在各文件中引用一致

## 技术约束

1. **不修改 workflow.md**: 当前版本 Phase 编号正确（1.1, 1.2, 1.3, 2.1, 2.2, 2.3, 3.1, 3.2）
2. **保留完整工具列表**: trellis-research 必须包含 ace、Context7、deepwiki、grok-search、exa 全套工具
3. **遵循原有 Phase 编号**: 所有引用必须与 workflow.md 一致
4. **跨平台一致性**: 确保各平台 agent 配置功能对等

## 执行优先级

P0 - 立即处理：
- 删除错误版本的 trellis-research .new 文件
- 删除错误的 continue/finish-work .new 文件

P1 - 次要处理：
- 修正 kiro 的 trellis-research.json 工具列表
- 审查其他 .new 文件

P2 - 后续处理：
- 提交修改
- 验证功能

## 风险评估

- **影响范围**: trellis 多平台 agent 配置
- **回滚方案**: 所有修改前确认当前版本正确，.new 文件不影响已提交代码
- **测试方案**: 运行 get_context.py --mode phase 验证功能
