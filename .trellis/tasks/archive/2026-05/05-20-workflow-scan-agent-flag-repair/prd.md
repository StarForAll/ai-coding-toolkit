# repair workflow-scan agent flag

## Goal

修复 `skills/workflow-scan/` 的 skill 合同，使其在默认情况下继续禁止 agent/sub-agent 协作，但在显式提供 `--agent` 参数时允许多 agent 协助扫描，以降低上下文压力，同时不改变 `WORKFLOW_QUESTIONS.md` 的既有共享协议，也不为 `workflow-repair` 引入新的兼容性问题。

## What I already know

- 用户明确要求为 `workflow-scan` 增加 `--agent` 输入参数，默认仍不能使用 agents。
- `skills/workflow-scan/SKILL.md` 与 `.trellis/spec/skills/workflow-scan.md` 当前都把“禁止 agents/sub-agents”写成硬约束。
- `workflow-scan` / `workflow-repair` 是强耦合 skill 对，`.trellis/spec/skills/index.md` 明确要求任一方的协议或角色边界变化都要在另一方同变更内适配。
- `scripts/validate-skills.sh` 已对这对 skill 的共享协议执行关键字校验，目前还没有覆盖 `--agent` 执行模式契约。
- 当前仓库 `codex.dispatch_mode=inline`，本会话不能实际调用 agents；因此本次修复只能定义 installable skill 的行为契约，而不是在当前会话里演示使用 agents。

## Assumptions

- `--agent` 作为布尔型执行模式开关即可满足当前需求，不需要在本次变更里扩展 agent 数量、命名或调度策略参数。
- 显式 `--agent` 只改变扫描过程的执行组织方式，不改变输出文件位置、frontmatter、finding schema 或 repair-side intake 协议。
- repair 侧无需获得新的输入参数，但需要明确：只要 scan 侧最终报告通过了既有 read-back validation，repair 就不应依赖 scan 是 inline 还是 `--agent` 模式。

## Open Questions

- 无阻塞问题；按现有约束直接实施。

## Requirements

- `workflow-scan` skill 必须新增 `--agent` 输入参数说明。
- 默认执行模式必须继续是当前 CLI 会话 inline 扫描，不允许 agents。
- 只有显式提供 `--agent` 时，skill 才允许使用多个 agents 协助扫描。
- `--agent` 模式必须定义清晰的角色边界：
  - 主协调者负责路径解析、是否覆盖、最终 finding 判断、报告写入、read-back validation、结果回显。
  - 协助 agents 只能做受限的证据采集/分类子任务，不能写报告、不能改文件、不能越权扩展范围。
- 若显式请求 `--agent` 但当前平台/会话不支持 agents，skill 必须阻塞而不是静默降级。
- `workflow-repair` 与共享 spec/验证层必须同步适配，明确 repair intake 与 scan 执行模式解耦。
- 变更不得破坏现有 `workflow-scan-repair-v2` 报告协议。

## Acceptance Criteria

- [ ] `skills/workflow-scan/SKILL.md` 明确新增 `--agent` 输入参数和默认 inline / 显式 agent 模式的执行规则。
- [ ] `.trellis/spec/skills/workflow-scan.md` 同步表达新的执行模式约束与 review checklist。
- [ ] `skills/workflow-repair/SKILL.md` 与 `.trellis/spec/skills/workflow-repair.md` 明确 repair intake 不依赖 scan 的执行模式。
- [ ] 如有必要，共享模板或 spec index 对“执行模式不改变报告协议”给出明确说明。
- [ ] `scripts/validate-skills.sh` 对新的 agent-mode 契约有防回归校验。
- [ ] 相关验证命令通过，且没有新增协议漂移。

## Definition of Done

- 相关 skill/spec/validation 改动已完成
- 运行并记录必要校验结果
- 明确说明未完成项与残余风险（若存在）

## Out of Scope

- 修改 `workflow-scan-repair-v2` frontmatter 或 finding schema
- 为 `workflow-repair` 增加 agent 模式
- 在当前 Codex inline 会话里实际启用/演示 agents
- 引入新的 CLI 参数族（如 `--agent-count`、`--agent-role`）

## Technical Notes

- 主要变更面：
  - `skills/workflow-scan/SKILL.md`
  - `.trellis/spec/skills/workflow-scan.md`
  - `skills/workflow-repair/SKILL.md`
  - `.trellis/spec/skills/workflow-repair.md`
  - `.trellis/spec/skills/index.md`
  - `skills/workflow-scan/references/scan-output-template.md`
  - `scripts/validate-skills.sh`
- 相关协作规范：
  - `.trellis/spec/universal-domains/agent-collaboration/agent-role-boundaries/normative-rules.md`
  - `.trellis/spec/universal-domains/agent-collaboration/delegation-policy/normative-rules.md`
  - `.trellis/spec/universal-domains/agent-collaboration/handoff-contracts/normative-rules.md`
