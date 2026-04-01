# 新项目开发工作流多CLI适配与MCP/Skills利用率提升

## Goal

对 `docs/workflows/新项目开发工作流/` 目录中的工作流文档进行分析，找出在多CLI原生适配（Claude Code/Codex/OpenCode）和MCP/Skills利用率方面的缺漏，提出改进方案。采用渐进性披露原则，不一次性占满上下文。

## What I already know

### 文档结构（已确认）
- `工作流总纲.md`（2875行）：权威规则层，已有MCP/Skills配置原则、能力路由基线、渐进性披露框架
- `命令映射.md`（440行）：路由层，已有阶段→命令→Skills映射、能力路由矩阵、配置层矩阵
- `多CLI通用新项目完整流程演练.md`（445行）：通用主链入口，已有CLI入口差异、推荐MCP/Skills、降级方式
- `完整流程演练.md`（454行）：双轨交付控制专项案例
- `commands/` 下有 claude/opencode/codex/gemini/codex-gemini/cursor/shell 平台适配层

### 已做的好的部分
1. 渐进性披露三层架构（主规则层→映射层→平台展开层）已建立
2. 能力路由基线 10 条规则已写入总纲
3. 能力路由矩阵（10 场景 × 默认能力 × 回退 × 配置落点）已写入命令映射
4. 配置分层原则（项目稳定→workflow阶段→CLI原生→复用资产）已明确
5. Skills 复用总表已有 21 个 skill 映射到各阶段
6. 每个阶段的"推荐MCP/Skills"和"典型降级方式"已在通用流程演练中覆盖
7. 三个平台展开层 README 已各自说明承载方式

## 初步分析：发现的缺漏

### 一、MCP 利用率缺漏

1. **MCP 在各阶段命令正文中的使用指导缺失**
   - 命令源文件（`commands/brainstorm.md`、`commands/design.md` 等）是否在正文中指导 AI 何时调用 MCP？
   - 目前只有映射表和通用流程演练提到 MCP，但命令正文本身可能没有嵌入调用时机

2. **MCP 降级链路不完整**
   - 能力路由矩阵列了"回退顺序"，但没有统一的降级判断标准（何时认为"不可用"？超时？无结果？错误？）
   - 缺少"MCP 不可用时的证据标记格式"统一规范

3. **MCP 组合调用模式未文档化**
   - 某些阶段需要多个 MCP 协同（如 design 阶段同时需要 ace.search_context + Context7 + deepwiki）
   - 缺少"推荐调用顺序"和"并行 vs 串行"建议

### 二、Skills 利用率缺漏

4. **Skills 触发时机不够精确**
   - 映射表只写了"阶段→可复用Skills"，但何时在阶段内触发、触发条件是什么不够具体
   - 例：`coding-standards` 在 §5 start 什么时候调用？开始编码前？还是编码后审查？

5. **Skills 与 MCP 的协作关系未明确**
   - 某些 skill 内部会调用 MCP（如 `demand-risk-assessment` 可能需要 `exa_create_research`）
   - 目前只单独列了 Skills 和 MCP，没有说明它们在同一阶段的协作模式

6. **缺少 Skill 可用性检测与回退方案**
   - 如果目标项目没有安装某个 skill，工作流应如何降级？
   - 目前只在 `§5.1.y check` 提到"先补齐 skill"，其他阶段无类似指导

### 三、多 CLI 适配缺漏

7. **命令正文的 CLI 适配深度不均**
   - 命令源文件（`commands/*.md`）是否已覆盖三个 CLI 的差异化执行路径？
   - 还是只写了 Claude Code 的逻辑，其他 CLI 靠平台 README 自行推断？

8. **Codex 的 skill 触发入口缺乏实例**
   - Codex 不支持 `/trellis:xxx`，需通过自然语言或 skill 触发
   - 但各阶段没有给出 Codex 推荐的自然语言触发示例

9. **子代理（subagent）在各 CLI 下的使用差异未明确**
   - 总纲提到 research/implement/check/debug 子代理
   - 但在多 CLI 上下文中，子代理的调用方式和权限模型是否一致？

### 四、渐进性披露实施缺漏

10. **"按需引用"的触发机制不明确**
    - 命令映射说"按阶段需要引用"，但没有定义什么信号触发引用
    - AI 何时应该主动去读平台展开层 README？

## Open Questions

1. **范围确认**：改进范围是只改文档内容，还是也包括命令源文件（`commands/*.md`）的正文更新？
2. **优先级**：10 个缺漏中，你认为哪些最关键需要先处理？

## Requirements (evolving)

- （待确认后填写）

## Acceptance Criteria (evolving)

- [ ] （待确认后填写）

## Definition of Done

- 改动遵循渐进性披露原则
- 文档更新后不破坏现有三层架构
- 验证方法已明确

## Out of Scope (explicit)

- 不修改 install/uninstall/upgrade 脚本
- 不新建命令文件
- 不改变渐进性披露三层架构本身

## Technical Notes

- 工作流总纲 2875 行，已经很重，新增内容应优先放到映射层或平台展开层
- 渐进性披露的核心约束：主规则层只保留最小必要原则
