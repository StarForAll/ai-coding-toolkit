# reconcile trellis 0.5.6 upgrade drift

## Goal

在当前仓库内完成一次受控的 Trellis 0.5.6 小版本升级对账：保留有效的 runtime / hook / agent 增强，回退错误的 phase 编号漂移、finish-work 合同漂移、research agent 降级，以及不安全的 template hash 回写；逐个处置 `.new` 候选文件，并把工作树恢复到“当前仓库合同一致”的状态。

## What I already know

* 当前仓库的 canonical workflow 仍以 `.trellis/workflow.md` 为准，阶段编号口径仍是 `1.2 / 1.3 / 2.3 / 3.1 / 3.2`。
* `git diff` 中混入了两类升级内容：
  * 合法增强：如 Codex/Qoder 的 sub-agent notice、bootstrap 方向、active-task fallback 兼容、部分 hooks/runtime 注释增强。
  * 非法漂移：如 `1.2 -> 1.3`、`1.3 -> 1.4`、`3.1 -> 3.4`、`3.2 -> 3.5`，以及 `record-session-helper.py -> add_session.py` 的 finish-work 合同重写。
* 当前 `.trellis/.template-hashes.json` 已记录了部分当前工作树文件的实际 sha256，而不是干净 Trellis 基线 hash，这会掩盖本地定制。
* 仓库里不存在 `.agents/skills/trellis-start/SKILL.md`，但 `.codex/hooks/inject-workflow-state.py` 的新 bootstrap 文案要求读取它。

## Assumptions (temporary)

* 用户希望直接在当前工作树中落地修复，而不是仅输出审计报告。
* 这次修复以“当前仓库合同优先”为准，不盲目跟随上游小版本对 phase 编号和 close-out 文案的改写。
* 没有必要引入 subagent；全部工作在主会话完成。

## Open Questions

* 无阻塞问题。若在保留 bootstrap 方案时发现必须补建 `trellis-start` skill，按最小可用实现补齐。

## Requirements (evolving)

* 回退所有 live phase drift，恢复到当前仓库 canonical 编号。
* 保持 `finish-work` 仍依赖 `record-session-helper.py` 与恢复指导，不切换到 `add_session.py` 直调合同。
* 恢复 `trellis-research` 对当前仓库所需的任务定位与工具能力，不接受降级。
* 逐个处理 `.new` 文件：
  * 明确删除不应合并的候选。
  * 仅手工摘取确有价值的升级片段。
* 修复 `.template-hashes.json`，不得继续记录当前本地定制文件的实时内容 hash。
* 如果保留 Codex bootstrap 路线，则补齐缺失的 `trellis-start` skill；否则回退到当前可运行状态。

## Acceptance Criteria (evolving)

* [ ] `.trellis/workflow.md`、continue / brainstorm / finish-work / meta references / hook 提示中的 phase 编号与 canonical workflow 一致。
* [ ] `finish-work` 文案仍指向 `record-session-helper.py`，并保留只读失败恢复指导。
* [ ] `trellis-research` agent 合同恢复到当前仓库需要的任务定位与检索能力。
* [ ] `.new` 文件按逐文件策略完成：该删的删，该合的合，该保留的保留。
* [ ] `.trellis/.template-hashes.json` 不再使用当前定制工作树内容作为基线 hash。
* [ ] 如保留 bootstrap，则 `trellis-start` 实际存在且可被引用；如不保留 bootstrap，则相关引用已清理。

## Definition of Done (team quality bar)

* 相关修改完成后，至少运行受影响脚本/校验命令证明工作树处于自洽状态。
* 不引入新的 phase drift、路径漂移或托管边界误导。
* 不修改与本任务无关的业务内容。
* 变更说明中明确写出保留项、回退项、删除项和剩余风险。

## Out of Scope (explicit)

* 重构 Trellis 整体架构或改写上游版本策略。
* 为所有新平台（如 `iflow` / `pi`）全面接入支持。
* 修改 `docs/workflows/新项目开发工作流/` 产品资产本身。

## Technical Notes

* 关键合同来源：
  * `.trellis/workflow.md`
  * `.trellis/spec/guides/cross-layer-thinking-guide.md`
  * `.trellis/spec/scripts/index.md`
  * `.trellis/spec/scripts/python-conventions.md`
  * `.trellis/spec/scripts/workflow-installer-upgrade-contracts.md`
* 历史修复证据：
  * `.trellis/workspace/xzc/journal-4.md` 已明确记录过 phase drift / finish-work drift 的回退结论。
