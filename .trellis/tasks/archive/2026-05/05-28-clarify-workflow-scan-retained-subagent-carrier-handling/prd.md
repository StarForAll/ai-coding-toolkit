# clarify workflow-scan retained subagent carrier handling

## Goal

修正 `workflow-scan` 的 skill 合同与配套示例/测试，使其在临时项目扫描中不再把“已明确说明为暂时关闭、仅保留兼容/占位用途的 subagent carrier”当成问题输出到 `WORKFLOW_QUESTIONS.md`。

## What I already know

- 用户明确要求补充 `workflow-scan` 说明，删除把保留的 subagent carrier 当成问题的行为。
- `skills/workflow-scan/SKILL.md` 已有“intentional gated-carrier observations stay conservative”规则，但当前仍允许把这类情况最多记为 `design-debt`。
- `skills/workflow-scan/references/scan-output-template.md` 的完整示例里，`WS-002` 仍把 `.codex/skills/` 空目录与 `.agents/skills/` 有效载体并存描述为 `design-debt`。
- `skills/workflow-scan/tests/08-classifies-repair-eligibility-before-emitting-findings.md` 当前也把“intentionally gated-but-present carrier”作为一种 finding 类型进行约束。
- `workflow-scan` / `workflow-repair` 是耦合 skill 对；即使这次不改共享 schema，也需要检查 repair 侧 intake 说明是否要同步收紧。

## Assumptions (temporary)

- 这里的 “retained subagent carrier” 指 temp project 中仍保留在磁盘上，但安装态文档或运行时规则已经明确声明当前不可用/关闭的 carrier。
- 只要 temp project 各表面之间没有出现自相矛盾，这类 carrier 应从 actionable finding 集合中直接省略，而不是降级为 `design-debt`。
- 本次修改聚焦 skill/spec/template/test 资产，不涉及运行时代码或安装脚本逻辑变更。

## Open Questions

- 无阻塞问题；若后续发现 repair 侧已依赖旧示例语义，再补充对称说明。

## Requirements

- 明确 `workflow-scan` 对“已声明暂时关闭的 retained carrier”的处理规则：
  - 仅因其被保留在磁盘上，不得生成 finding。
  - 只有当 temp project 其他安装态表面与“当前关闭”声明发生实际矛盾时，才可升级为 finding。
- 更新扫描输出模板或完整示例，删除把这类情况写成 `design-debt` 的示例。
- 更新场景测试，使测试期望与新的“默认不输出 finding”行为一致。
- 检查 `workflow-repair` 与 `.trellis/spec/skills/` 的配套说明，避免 scan/repair 侧语义漂移。

## Acceptance Criteria

- [ ] `skills/workflow-scan/SKILL.md` 明确说明：已声明暂时关闭且无矛盾的 retained carrier 不应作为 finding 输出。
- [ ] `skills/workflow-scan/references/scan-output-template.md` 不再示范把此类 carrier 记为 `design-debt`。
- [ ] 至少一个 `skills/workflow-scan/tests/*.md` 场景改为覆盖“默认不输出 finding”的预期。
- [ ] 若 `workflow-repair` 或 `.trellis/spec/skills/*.md` 需要同步说明，相关文件在同一变更中更新。
- [ ] `./scripts/validate-skills.sh` 通过。

## Definition of Done (team quality bar)

- 相关 skill/spec/template/test 已同步
- 仓库级 skill 校验已运行并记录真实结果
- 如无共享协议变更，明确说明 repair 侧仅做语义对齐或无需 schema 变更

## Out of Scope (explicit)

- 修改 temp project 安装产物或运行时 carrier 布局
- 扩展 `workflow-scan-repair-v4` 共享 schema
- 处理与本次 retained carrier 误报无关的其他 workflow-scan 发现

## Technical Notes

- 主要目标文件：
  - `skills/workflow-scan/SKILL.md`
  - `skills/workflow-scan/references/scan-output-template.md`
  - `skills/workflow-scan/tests/08-classifies-repair-eligibility-before-emitting-findings.md`
  - `.trellis/spec/skills/workflow-scan.md`
  - 视需要检查 `skills/workflow-repair/SKILL.md` 与 `.trellis/spec/skills/workflow-repair.md`
- 现有误导性示例位于 `scan-output-template.md` 的 `WS-002`。
