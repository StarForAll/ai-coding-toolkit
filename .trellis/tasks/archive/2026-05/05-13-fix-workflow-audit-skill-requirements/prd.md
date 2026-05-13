# 修复 workflow-audit skill 实现规范与审计闭环要求

## Goal

修复 repo-local maintainer skill `workflow-audit` 的行为合同，使其按现有 skill 实现规范补齐缺失要求，并保持与 `.trellis/spec/skills/workflow-audit.md`、`.agents/skills/workflow-audit/`、`.claude/skills/workflow-audit/`、相关 references/tests 的同步，不引入新的行为漂移。

## What I already know

- 该 skill 的行为源头是 `.trellis/spec/skills/workflow-audit.md`，入口副本位于 `.agents/skills/workflow-audit/` 和 `.claude/skills/workflow-audit/`
- 当前 skill 已覆盖 `incomplete closure`（流程层面有、执行闭环没做完）的识别要求，不需要重复新增同义规则
- 当前 skill 已覆盖基础的 CLI 适配结论与 `present-but-incompatible` / `missing-but-valuable` 分类
- 当前 skill 仍缺少对“结合各 CLI 官方最新文档 + 实际开发使用视角/使用证据”的明确审计合同
- 当前 skill 仍缺少“不能进行负面优化、非缺陷不优化、无必要不优化”的明确判断约束
- 相关最新官方资料已确认可用：
  - Claude Code: 官方文档覆盖 slash commands / subagents / hooks / settings
  - Codex: 官方文档覆盖 `AGENTS.md`、hooks、config/agents
  - OpenCode: 官方文档覆盖 commands / agents / plugins

## Assumptions

- `.agents/skills/workflow-audit/` 与 `.claude/skills/workflow-audit/` 现阶段保持相同的行为语义；如无平台差异，不单独分叉
- 本次不改 `workflow-capability-audit`，除非发现 `workflow-audit` 对其引用关系必须同步
- “实际使用经验/实际开发使用角度”在 skill 中应落成可审计的证据要求，例如 repo-local carrier、运行时观察、维护者实际操作路径，而不是主观感受

## Requirements

- 补齐 `workflow-audit` 对 Claude Code / OpenCode / Codex 原生适配判断时的证据要求：
  - 必须结合执行时可获得的最新官方文档
  - 必须结合 repo-local 已验证证据
  - 必须结合实际开发使用视角的证据，例如真实承载面、维护者日常调用路径、运行时/安装时行为
  - 禁止仅凭记忆或仅凭静态目录存在性下结论
- 补齐负面优化防护：
  - 不能把“不是缺陷的东西”包装成优化项
  - 不能做无必要优化
  - 不能把会损害现有可用路径、增加维护复杂度、或破坏托管边界的建议当作默认修复方向
- 保持已有 `incomplete closure` 规则，不重复添加同义要求；仅在必要处增强其与实际开发闭环视角的衔接
- 若行为合同变化影响输出结构或验证方式，同步更新 references 与 persisted tests
- 保持 `.trellis/spec`、`.agents`、`.claude` 三层行为一致

## Out of Scope

- 不重写 `workflow-audit` 的整体流程
- 不扩展支持新的 workflow root
- 不改 `workflow-capability-audit` 的主合同
- 不引入与本次缺口无关的“优化”

## Acceptance Criteria

- `.trellis/spec/skills/workflow-audit.md` 明确包含：
  - 最新官方 CLI 文档 + repo-local 证据 + 实际开发使用视角的适配分析要求
  - 负面优化防护和“非缺陷忽略”判断约束
- `.agents/skills/workflow-audit/SKILL.md` 与 `.claude/skills/workflow-audit/SKILL.md` 同步体现上述要求
- 受影响的 references/templates 能承载新增证据要求
- 至少新增或更新对应 persisted tests，覆盖：
  - 原生 CLI 适配需要结合最新官方文档与实际开发使用证据
  - 非缺陷/负面优化场景不得被误报为 change-worthy issue
- 相关校验命令执行并如实记录结果

## Technical Notes

- 重点文件：
  - `.trellis/spec/skills/workflow-audit.md`
  - `.agents/skills/workflow-audit/SKILL.md`
  - `.claude/skills/workflow-audit/SKILL.md`
  - `.agents/skills/workflow-audit/references/*.md`
  - `.claude/skills/workflow-audit/references/*.md`
  - `.agents/skills/workflow-audit/tests/*.md`
  - `.claude/skills/workflow-audit/tests/*.md`
- 参考外部官方资料：
  - Claude Code docs: slash commands / sub-agents / hooks / settings
  - OpenAI Codex docs: AGENTS.md / hooks / config basics
  - OpenCode docs: commands / agents / plugins
