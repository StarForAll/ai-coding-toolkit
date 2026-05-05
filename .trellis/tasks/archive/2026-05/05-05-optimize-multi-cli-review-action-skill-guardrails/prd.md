# 优化 multi-cli-review-action skill 防回归护栏并补齐缺漏

## Goal

强化 `skills/multi-cli-review-action/SKILL.md`，明确当前 CLI 在依据 reviewer 报告执行修复时，不能为了关闭已知问题而引入新的问题；同时对与其共享协议面的文档进行缺漏审查，并补齐必要的同步说明。

## What I already know

- 用户要求补充一条明确约束：使用 `multi-cli-review-action` 修复问题时不能引入新的问题。
- `.trellis/spec/skills/index.md` 已将 `skills/multi-cli-review/` 与 `skills/multi-cli-review-action/` 定义为必须共同维护的 coupled skill contract。
- 当前 `multi-cli-review-action` 只有“修复后必须验证”的约束，尚未把“不得引入新问题”提升为采纳/执行前的明确决策门槛。
- `review-gate.md` 与 `project-audit.md` 都把 `multi-cli-review-action` 作为聚合与修复环节的一部分，因此需要复核是否存在说明漂移。

## Assumptions

- 这次需求以文档/skill 约束增强为主，不涉及新增脚本或协议格式变更。
- 若共享协议、角色边界和路径契约未变化，则配对 skill 只需做最小必要同步或审查确认，不强制改动。

## Requirements

- [ ] 在 `skills/multi-cli-review-action/SKILL.md` 中新增明确规则：采纳或执行修复前必须判断不会引入新的问题、回归或更高风险副作用。
- [ ] 将该规则落实到 workflow / decision / stop conditions / common mistakes 等至少一个高约束位置，而不只是示例性提醒。
- [ ] 深度审查与该 skill 直接耦合的文档面，确认是否还有其他与“防回归修复”相关的缺漏。
- [ ] 若发现必要同步点，做最小一致性补充，避免 paired skill 或 workflow 文档继续只强调“验证”而不强调“采纳门槛”。

## Acceptance Criteria

- [ ] `multi-cli-review-action` 明确要求：任何 `adopted` 修复都必须先评估不会制造新的问题。
- [ ] skill 文档中至少有一处把“新问题/回归风险”定义为停止、忽略或人工决策条件之一。
- [ ] 审查 `multi-cli-review`、`review-gate.md`、`project-audit.md` 后，必要缺漏已同步处理或明确记录为无需修改。
- [ ] `./scripts/validate-skills.sh` 通过。

## Out of Scope

- 不重写 multi-review 协议。
- 不新增自动化校验脚本。
- 不扩展到与本次护栏无关的通用 skill 写作规范。

## Technical Notes

- 重点文件：`skills/multi-cli-review-action/SKILL.md`
- 需复核的耦合面：`skills/multi-cli-review/SKILL.md`、`docs/workflows/新项目开发工作流/commands/review-gate.md`、`docs/workflows/新项目开发工作流/commands/project-audit.md`
- 相关规范：`.trellis/spec/skills/index.md`、`.trellis/spec/docs/index.md`、`.trellis/spec/guides/cross-layer-thinking-guide.md`
