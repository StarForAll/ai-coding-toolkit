# 优化 workflow-audit 小版本差异跳过规则

## Goal

优化当前项目中的 `workflow-audit` skill，使其在 Trellis 版本存在“小版本差异”时，允许用户通过显式要求跳过该版本差异检测；同时保留对非小版本差异、预发布版本差异的严格门禁。

## What I already know

* 当前 `workflow-audit` 在 `.agents/skills/workflow-audit/SKILL.md`、`.claude/skills/workflow-audit/SKILL.md` 与 `.trellis/spec/skills/workflow-audit.md` 中都要求将 `COMPATIBLE_TRELLIS_VERSION` 与 `trellis -v` 做“完全相等”比较。
* `workflow-audit` 的输入模板当前没有“跳过小版本差异检测”的显式字段。
* `docs/workflows/新项目开发工作流/commands/workflow_assets.py` 已有 Trellis 版本解析与比较能力，支持识别 `beta` 与 `rc` 预发布标签。
* 用户已明确给出示例：`0.5.0` 和 `0.5.5` 属于小版本差异；`rc` 与正式版不是小版本差异；`beta` 与正式版不是小版本差异。
* 用户要求：必须在用户确认之后再进行实际修改。

## Assumptions (confirmed)

* “小版本差异”按“相同 `major.minor` 的正式版，仅 `patch` 不同”处理。
* 只要任一侧带有 `beta` 或 `rc` 预发布标签，就不属于可跳过的小版本差异；预发布版本之间也不允许按该规则跳过。
* 跳过机制通过显式字段 `allow_minor_version_mismatch: yes|no` 落地，同时接受等价的明确自然语言表达。
* 本次修改范围以 `workflow-audit` skill 合同及其 repo-local spec / 模板为主，并同步更新受影响的场景测试。

## Open Questions

* 无。用户已确认输入合同与预发布版本处理规则。

## Requirements (evolving)

* 定义 `workflow-audit` 中“小版本差异”的判定规则。
* 仅当用户显式要求时，才允许跳过“小版本差异”的版本门禁。
* 非小版本差异仍必须阻断，并引导到 `workflow-capability-audit`。
* `rc` 与正式版、`beta` 与正式版不能被视为“小版本差异”。
* 为显式跳过机制新增 `allow_minor_version_mismatch` 输入字段，并保持与自然语言入口语义一致。
* 修改完成后需要保持 skill、本地 spec、输入模板之间的一致性。

## Acceptance Criteria (evolving)

* [ ] `workflow-audit` skill 文档明确区分完全匹配、小版本差异、非小版本差异。
* [ ] 用户显式要求跳过时，小版本差异可继续审计流程；未显式要求时仍阻断。
* [ ] 任何涉及 `beta` / `rc` 与正式版差异的场景仍阻断并路由到 `workflow-capability-audit`。
* [ ] 输入模板暴露 `allow_minor_version_mismatch` 字段，并精确定义其适用边界。
* [ ] 相关 spec / 模板 / 场景测试同步更新，无规则漂移。

## Definition of Done (team quality bar)

* 相关 skill/spec/template 已同步更新
* 相关验证命令已运行并如实记录结果
* 如产生新的 repo 维护知识，已评估是否需要更新 `.trellis/spec/`

## Out of Scope (explicit)

* 全面改造 `workflow-capability-audit`
* 修改与当前需求无关的 Trellis 版本比较策略
* 扩展到 `workflow-audit` 之外的普通业务 skill

## Technical Notes

* 相关主文件：
  * `.agents/skills/workflow-audit/SKILL.md`
  * `.claude/skills/workflow-audit/SKILL.md`
  * `.trellis/spec/skills/workflow-audit.md`
  * `.agents/skills/workflow-audit/references/input-template.md`
  * `.claude/skills/workflow-audit/references/input-template.md`
  * `docs/workflows/新项目开发工作流/commands/workflow_assets.py`
* 当前精确相等规则已在 skill/spec/template 多处重复声明，修改时需要先全局搜索后统一收敛。
