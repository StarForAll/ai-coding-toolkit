# 修复 workflow-audit skill 与当前 Trellis 机制的兼容漂移

## Goal

在不扩大职责边界、不引入新的行为漂移的前提下，修复当前项目中
`workflow-audit` repo-local maintainer skill 的兼容问题，使其与当前仓库
真实 Trellis 运行机制、`.trellis/spec/skills/workflow-audit.md` 行为源头、
以及 `.agents` / `.claude` 双执行载体保持一致。

## What I already know

- 当前仓库是 Trellis 管理的 workflow authoring source project，不是被安装后的 target project。
- `.trellis/` 是运行时真相层，负责 workflow、task、session、spec、workspace。
- `.claude/`、`.opencode/`、`.codex/`、`.agents/`、`.kiro/`、`.qoder/` 是不同平台的 carrier / integration layer，
  不是与 `.trellis/` 同级的运行时 authority。
- 当前仓库 `.trellis/config.yaml` 保持 Codex `dispatch_mode: inline` 约束，
  `.codex/config.toml` 也明确主会话不能把 inline 规则当成手动 sub-agent 豁免口。
- `workflow-audit` 的行为源头是 `.trellis/spec/skills/workflow-audit.md`；
  repo-local 可执行 skill surface 在 `.agents/skills/workflow-audit/` 与
  `.claude/skills/workflow-audit/`。
- 当前 `workflow-audit` skill 主体已经覆盖大部分 same-version 审计主线、
  fixed workflow root、Codex handoff、三层证据模型、CLI 适配证据要求。
- 当前 `workflow-audit` 可执行 skill surface 与 spec 仍存在维护层合同漂移，
  主要集中在：
  - 任务闭环后的 remediation splitting 说明
  - report contract / confirmed-issue schema / blocked-state rule 的显式维护段
  - CLI main-session-only policy 的集中说明
  - post-audit trusted routing whitelist
  - validation / sync rules / related files 这些 repo-local maintainer contract
- 当前本机 `trellis -v` 为 `0.5.15`；
  `docs/workflows/新项目开发工作流/commands/workflow_assets.py` 中
  `COMPATIBLE_TRELLIS_VERSION` 为 `0.5.14`，因此真实运行环境下
  `workflow-audit` 默认会遇到 patch-only stable mismatch 的 version gate 判断。

## Assumptions

- 本次修复以 `.trellis/spec/skills/workflow-audit.md` 为行为源头，不反向修改 spec 以迎合当前 skill drift。
- 本次不修改 `workflow-capability-audit` 的主合同，除非发现 `workflow-audit`
  当前文本对其引用已明确错误。
- `.agents/skills/workflow-audit/` 与 `.claude/skills/workflow-audit/`
  需要保持相同的行为语义；若无平台差异，不单独分叉。
- 由于当前仓库 Codex 处于 inline dispatch mode，本任务 Phase 1.3 的
  `implement.jsonl` / `check.jsonl` curation 可跳过，直接由主会话读取 spec。

## Requirements

- 深度分析当前仓库 Trellis 机制后，只修复经证据确认的 `workflow-audit` 合同漂移。
- 保持 `workflow-audit` 的 same-version maintainer audit 职责边界，不扩面到：
  - 普通业务代码评审
  - `workflow-capability-audit` 的升级兼容职责
  - workflow product source 逻辑本身
- 以最小改动补齐当前 skill surface 中缺失的维护层合同：
  - remediation splitting
  - report contracts
  - CLI and handoff rules
  - post-audit routing
  - validation
  - sync rules
  - related files
- 保持 `.agents` 与 `.claude` 两个 workflow-audit surface 同步。
- 如本次修复不改变行为语义，则不额外修改 references/tests；
  仅在当前 surface 无法正确表达既有 spec 合同时才联动更新。

## Acceptance Criteria

- `.trellis/tasks/05-15-workflow-audit-skill/research/` 中有本次 Trellis 机制与 drift 结论记录。
- `.agents/skills/workflow-audit/SKILL.md` 修复后能完整表达当前 repo-local maintainer contract。
- `.claude/skills/workflow-audit/SKILL.md` 与 `.agents` surface 保持零语义漂移。
- 不引入对 references/tests 的无必要改动；若有联动改动，需有明确合同原因。
- 运行并如实记录以下验证结果：
  - `./scripts/validate-skills.sh`
  - `diff -u .agents/skills/workflow-audit/SKILL.md .claude/skills/workflow-audit/SKILL.md`
  - `git diff --check`

## Definition of Done

- 当前 skill surface 与 spec 的维护层合同漂移已修复。
- 已明确记录：已修复项、未修复项、剩余风险、以及是否需要后续 workflow-level follow-up。
- 所有完成声明都有实际验证证据支撑。

## Out of Scope

- 修改 `docs/workflows/新项目开发工作流/commands/workflow_assets.py` 的版本锚点
- 将 `.kiro/` / `.qoder/` 纳入 `workflow-audit` 支持面
- 对 `workflow-audit` 做无证据的结构性重写
- 顺手优化其他 Trellis skill

## Technical Notes

- 关键证据面：
  - `.trellis/workflow.md`
  - `.trellis/config.yaml`
  - `.codex/config.toml`
  - `.codex/hooks.json`
  - `.claude/settings.json`
  - `.opencode/plugins/inject-workflow-state.js`
  - `.trellis/spec/skills/workflow-audit.md`
  - `.agents/skills/workflow-audit/SKILL.md`
  - `.claude/skills/workflow-audit/SKILL.md`
- 参考历史任务：
  - `.trellis/tasks/archive/2026-05/05-07-fix-workflow-audit-target-scoping-and-review/prd.md`
  - `.trellis/tasks/archive/2026-05/05-09-implement-workflow-audit-optimization/prd.md`
  - `.trellis/tasks/archive/2026-05/05-13-fix-workflow-audit-skill-requirements/prd.md`
