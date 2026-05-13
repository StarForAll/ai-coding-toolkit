# fix workflow-capability-audit skill cli-native-adaptation requirements

## Goal

修复 `workflow-capability-audit` skill，使其按当前项目的 skill 实现规范补齐“原生适配 ClaudeCode/Codex/OpenCode 时必须结合对应 CLI 官方最新文档与本仓库实际使用经验分析”的要求，并保证该要求只在缺失处补充、不重复堆叠、不引入新的契约漂移。

## What I already know

* 当前行为源头是 `.trellis/spec/skills/workflow-capability-audit.md`，执行入口同步在 `.agents/skills/workflow-capability-audit/SKILL.md` 与 `.claude/skills/workflow-capability-audit/SKILL.md`。
* 该 skill 已覆盖 Claude/OpenCode/Codex 的 carrier 差异、Codex runtime boundary、shared skills carrier 等规则。
* 现有文本尚未把“必须结合各 CLI 官方最新文档和实际使用经验分析”明确写成契约要求。
* 该 skill 自带 references 与 scenario tests，适合把新增要求同步到 reference/test 层，避免只改主文档。

## Assumptions

* 本次修复以文档/skill/spec/test 为主，不需要改动 `workflow-capability-audit.py` 运行时代码，除非验证中发现该要求已经在 runtime 侧硬编码且与文本冲突。
* “实际使用经验”应限定为本仓库已验证、可指向具体 carrier/path/行为证据的经验，而不是无来源主观判断。
* “官方最新文档”需要基于当前日期重新核对，而不是依赖历史记忆。

## Requirements

* 按 skill 实现规范修复 `workflow-capability-audit` 的行为契约。
* 若现有文档已完整包含同等要求，不重复添加同义规则。
* 新增要求必须明确：
  * 原生适配分析面向 ClaudeCode、Codex、OpenCode 三个 CLI。
  * 分析必须同时参考对应 CLI 官方最新文档与本仓库实际使用经验证据。
  * 文档证据与本地经验冲突时，需要显式标注边界与判断依据，不能凭记忆下结论。
* spec、skill、reference、tests 需要按影响面同步，避免协议漂移。

## Acceptance Criteria

* [ ] `.trellis/spec/skills/workflow-capability-audit.md` 明确要求对 ClaudeCode/Codex/OpenCode 的原生适配分析同时依赖官方最新文档与本仓库经验证据。
* [ ] `.agents/skills/workflow-capability-audit/SKILL.md` 与 `.claude/skills/workflow-capability-audit/SKILL.md` 同步体现该要求，且无明显重复段落。
* [ ] 至少一个 reference 或 test 文件补充对该要求的可执行约束，证明不是只写在主说明里。
* [ ] 通过 repo 现有 skill 校验命令，且改动后未发现新的同步遗漏。

## Definition of Done

* 相关 spec / skill / references / tests 已同步
* 相关验证命令已运行并记录真实结果
* 最终说明中明确哪些要求原本已存在、哪些是本次新增补齐

## Out of Scope

* 重写 `workflow-capability-audit` 的整体流程
* 扩展到 `workflow-audit` 或其他 skill，除非本次改动直接暴露必须同步的同源契约
* 变更三方 CLI 的实际运行配置或 repo 平台接线实现

## Technical Notes

* 关键文件：
  * `.trellis/spec/skills/workflow-capability-audit.md`
  * `.agents/skills/workflow-capability-audit/SKILL.md`
  * `.claude/skills/workflow-capability-audit/SKILL.md`
  * `.agents/skills/workflow-capability-audit/references/execution-runbook.md`
  * `.agents/skills/workflow-capability-audit/tests/*.md`
* 验证命令预期：
  * `./scripts/validate-skills.sh`
  * `rg -n` 检查新增要求的同步分布与重复情况
