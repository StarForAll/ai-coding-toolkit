# brainstorm: 审查新项目开发工作流文档一致性

## Goal

对 `docs/workflows/新项目开发工作流/` 做一轮轻量一致性审查，重点检查工作流主文档、平台适配文档与阶段命令文档之间是否存在历史数据漂移、重复表述、术语不统一或入口协议口径不一致的问题，并收敛到“当前只原生适配 Claude Code / OpenCode / Codex，其他 CLI 有则使用、没有则忽略”的统一叙事。

## What I already know

- 用户明确要求：
  - 检查 `./docs/workflows/新项目开发工作流/` 下对应工作流文档实现是否统一
  - 重点关注历史数据漂移、重复表述、术语不统一
  - 当前嵌入工作流只解决 ClaudeCode / Codex / OpenCode 原生适配问题
  - 其他 CLI 有就使用，没有则忽略
  - 不需要太过精细
- 当前目录下的核心文档包括：
  - `工作流总纲.md`
  - `命令映射.md`
  - `多CLI通用新项目完整流程演练.md`
  - `完整流程演练.md`
  - `commands/claude/README.md`
  - `commands/opencode/README.md`
  - `commands/codex/README.md`
  - 多个阶段命令文档，如 `commands/brainstorm.md`、`commands/plan.md`
- 已观测到一条主叙事已经在多份文档中出现：
  - 原生适配范围是 Claude Code / OpenCode / Codex
  - Codex 不提供项目级 `/trellis:xxx` 命令目录，而是以 `AGENTS.md + hooks + skills + subagents` 为主
  - 多 CLI 同装不等于同一入口协议
- 已观测到一些可能需要统一的点：
  - “Claude Code / OpenCode / Codex” 与 “ClaudeCode / Codex / OpenCode” 存在写法差异风险
  - “原生适配范围”“多 CLI 同装”“嵌入 workflow”“Trellis 原生基线 / workflow 补丁增强”在多份文档反复出现，可能存在重复或细微漂移
  - 阶段命令文档里的 Cross-CLI 说明、下一步推荐口径，可能与总纲/映射层的统一说法存在局部偏差

## Assumptions (temporary)

- 本轮先做“轻量一致性审查 + 最小必要修订方案”，不做大规模重写
- 优先保证主链叙事统一，而不是逐字逐句消灭所有重复
- 若脚本实现与文档存在明显冲突，可以记为发现，但本轮不默认扩展为脚本层深挖

## Open Questions

- 本轮范围是否按“主文档 + 三个平台 README + 若干关键阶段命令的 Cross-CLI 口径”做轻量收敛，而不是遍历所有命令文档做细粒度逐段清洗？

## Requirements (evolving)

- 识别当前 workflow 文档中的统一主叙事
- 识别高价值不一致点：
  - 历史数据漂移
  - 重复表述
  - 术语不统一
  - CLI 入口协议口径不一致
- 输出轻量范围下的修订建议或后续实现计划
- 明确本轮应纳入和不纳入的文档范围

## Research Notes

### 当前已经稳定的一致主叙事

- `工作流总纲.md`、`命令映射.md`、`多CLI通用新项目完整流程演练.md`、`commands/claude/README.md`、`commands/opencode/README.md`、`commands/codex/README.md` 基本都已经对齐以下几点：
  - 原生适配范围是 `Claude Code / OpenCode / Codex`
  - 多 CLI 同装不等于同一入口协议
  - Claude / OpenCode 以项目命令为主
  - Codex 以 `AGENTS.md + hooks + skills + subagents` 为主，不提供项目级 `/trellis:xxx`
  - `start` / `finish-work` / `record-session` 默认属于 Trellis 基线能力，当前 workflow 只做增强或补丁

### 明确漂移 / 明确错误

**1. `命令映射.md` 保留了不存在的 `codex-gemini/README.md` 引用**

- 证据：
  - `docs/workflows/新项目开发工作流/命令映射.md:470`
  - 当前目录实际仅存在 `commands/cursor/README.md`、`commands/gemini/README.md`、`commands/codex/README.md`
- 判断：
  - 这是典型历史残留引用，属于明确的数据漂移
- 建议：
  - 删除 `codex-gemini/README.md` 引用，或补充真实文件；当前更适合直接删除

**2. `commands/codex/README.md` 顶部 skill 路径写法与实际结构不一致**

- 证据：
  - `docs/workflows/新项目开发工作流/commands/codex/README.md:8` 写的是 `.agents/skills/*.md` 或 `.codex/skills/*.md`
  - 同文件后文与仓库实际结构写的是 `.agents/skills/<phase>/SKILL.md`
- 判断：
  - 这是路径级术语漂移，容易误导读者理解 Codex skill 的真实承载方式
- 建议：
  - 统一改成目录式表达，如 `.agents/skills/*/SKILL.md` 或 `.codex/skills/*/SKILL.md`

### 建议统一的高价值表述

**3. 主文档里对非目标 CLI 的存在方式需要降权，而不是继续结构化展开**

- 证据：
  - `工作流总纲.md` 与 `命令映射.md` 开头都已明确“原生适配范围只含 Claude Code / OpenCode / Codex”
  - 但 `命令映射.md:464-487` 仍为 Cursor / Gemini 保留了独立“扩展适配”章节和 README 引导
- 判断：
  - 这不算错误，但会弱化“当前只维护三种原生适配”的主叙事
- 建议：
  - 如果本轮目标是收敛主叙事，保留一句“其他 CLI 有则用、没有则忽略”即可
  - 可把 Cursor / Gemini 从主链说明正文降到附录或“历史/可选参考”一句话说明

**4. “Claude Code 仍是原生命令基线平台”这类说法带有历史中心化色彩**

- 证据：
  - `commands/claude/README.md`
  - `命令映射.md:484`
- 判断：
  - 从实现历史角度可能成立，但从“当前只维护三种原生适配”的读者视角，容易被理解为 Claude 是唯一主平台，OpenCode/Codex 是次级兼容层
- 建议：
  - 若本轮想统一对外口径，可改成更中性的表述：
    - “当前 workflow 维护 Claude Code / OpenCode / Codex 三种原生适配”
    - 如需保留历史事实，可放到平台 README 内部，不放在主映射层高位位置

### 可保留但无需本轮细抠

**5. 阶段命令中的 Cross-CLI 头部基本一致**

- 已抽查：
  - `commands/feasibility.md`
  - `commands/brainstorm.md`
  - `commands/design.md`
  - `commands/plan.md`
  - `commands/delivery.md`
- 结果：
  - 头部对 Claude/OpenCode/Codex 的入口协议描述基本统一
  - “下一步推荐”中也大体遵守 Claude/OpenCode 给命令入口、Codex 给自然语言/skill 入口的规则
- 判断：
  - 这一层目前没有看到需要大改的系统性漂移

**6. `start/finish-work/record-session` 的 Trellis 基线关系目前已较统一**

- 证据来源：
  - `多CLI通用新项目完整流程演练.md`
  - `commands/claude/README.md`
  - `commands/opencode/README.md`
  - `commands/codex/README.md`
  - `start-patch-phase-router.md`
  - `record-session-patch-metadata-closure.md`
- 结果：
  - 这些文档基本都在重复同一个结论：`start` 是基线 + Phase Router，`finish-work` 是 Trellis 基线，`record-session` 是基线 + metadata closure patch
- 判断：
  - 当前更像“重复较多”而不是“口径冲突”
- 建议：
  - 若后续要继续压缩文档体积，可以把定义集中到主文档，再让平台 README / 阶段命令引用，不必多处重写

## Acceptance Criteria (evolving)

- [ ] 已明确本轮审查范围
- [ ] 已列出主要统一口径
- [ ] 已列出需要修订的高价值不一致点
- [ ] 已明确哪些内容属于本轮 out of scope
- [ ] 已按优先级整理成可执行的轻量修订建议

## Definition of Done (team quality bar)

- 审查结论能直接指导下一轮最小修订
- 不把单轮轻量审查膨胀成全目录逐字清洗
- 若进入实现，优先改高价值漂移点并保持文档角色边界清晰

## Out of Scope (explicit)

- 不做所有文档的逐句风格统一
- 不默认深挖所有 shell/python 脚本实现
- 不处理 Claude/OpenCode/Codex 之外 CLI 的完整适配设计
- 不因为新规则而回写历史任务或历史演练样例台账

## Technical Notes

- 已读取：
  - `.trellis/spec/docs/index.md`
  - `.trellis/spec/guides/index.md`
  - `docs/workflows/新项目开发工作流/工作流总纲.md`
  - `docs/workflows/新项目开发工作流/命令映射.md`
  - `docs/workflows/新项目开发工作流/多CLI通用新项目完整流程演练.md`
  - `docs/workflows/新项目开发工作流/完整流程演练.md`
  - `docs/workflows/新项目开发工作流/commands/claude/README.md`
  - `docs/workflows/新项目开发工作流/commands/opencode/README.md`
  - `docs/workflows/新项目开发工作流/commands/codex/README.md`
  - `docs/workflows/新项目开发工作流/commands/brainstorm.md`
  - `docs/workflows/新项目开发工作流/commands/plan.md`
- 初步关注的统一锚点：
  - 原生适配范围
  - 多 CLI 同装但入口协议不同
  - Codex 不是 `/trellis:*` 项目命令入口
  - `start` / `finish-work` / `record-session` 属于 Trellis 基线能力，workflow 只做增强或补丁
