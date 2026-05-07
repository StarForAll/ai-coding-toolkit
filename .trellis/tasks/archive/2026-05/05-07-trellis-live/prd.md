# 修正当前项目 Trellis live 升级漂移

## Goal

基于当前仓库实际正在使用的 live Trellis 运行面，收敛本轮小版本升级引入的流程漂移。保持当前 `.trellis/workflow.md` 作为唯一 Phase 真源，保留 implement/check 子代理递归保护、hook 注入标记、Windows 路径归一化等健壮性修复，同时回退所有未在当前 live workflow 中落地的新 Phase 编号和新 close-out 模型，并显式处理遗留 `.new` 文件。

## What I already know

- 当前项目 live Trellis 真源是 `.trellis/workflow.md`、`AGENTS.md`、以及各平台部署目录中的 agent / command / hook / skill 文件。
- 当前 `.trellis/workflow.md` 的 Phase Index 仍是 `1.1 / 1.2 / 1.3 / 2.1 / 2.2 / 2.3 / 3.1 / 3.2`。
- 当前工作树中混入了 `1.3 / 1.4 / 3.4 / 3.5` 等编号漂移，以及 `finish-work -> add_session.py` 的新 close-out 口径。
- 当前部分健壮性修复方向正确：implement/check recursion guard、hook-injected marker、Windows shell path normalize。
- 仓库中存在可见 `.new` 文件，也存在被 `.trellis/.gitignore` 隐藏的 `.trellis/*.new` 文件。

## Assumptions (temporary)

- 当前目标不是把整个项目切换到新的 `3.4 / 3.5` 模型，而是让所有 live 文件重新与当前 `.trellis/workflow.md` 自洽。
- `.new` 文件属于候选模板，不应长期保留；每个文件都需要明确落位、部分吸收或丢弃。

## Open Questions

- 无阻塞问题；处理策略已由本轮用户确认。

## Requirements (evolving)

- 只以当前 live Trellis 面为依据修正漂移，不以 `docs/workflows/新项目开发工作流/` 作为当前运行时真源。
- 保留 recursion guard、hook marker、Windows path normalize 等健壮性修复。
- 回退所有与当前 `.trellis/workflow.md` 不一致的 Phase 编号与 close-out 契约。
- 清理 `.new` 文件：能部分吸收的吸收后删除，不能采纳的直接删除。
- 保持跨平台 live 部署面的一致性，避免只修一个平台。

## Acceptance Criteria (evolving)

- [ ] `.trellis/workflow.md` 仍为 `1.1 / 1.2 / 1.3 / 2.1 / 2.2 / 2.3 / 3.1 / 3.2`，相关 live 文件引用与之对齐。
- [ ] `finish-work` live 契约仍指向 `Phase 3.1` 和 `record-session-helper.py`。
- [ ] recursion guard / hook marker / Windows path normalize 在对应 live 文件中保留。
- [ ] 当前可见 `.new` 文件与 `.trellis/*.new` 文件都得到显式处置。
- [ ] 相关校验命令完成，结果可陈述为 pass / fail / not run。

## Definition of Done (team quality bar)

- 相关 live 文件已收敛
- 相关 jsonl 已整理
- 必要验证已执行
- `.new` 处置结果明确

## Out of Scope (explicit)

- 不修改 `docs/workflows/新项目开发工作流/` 的产品源资产
- 不切换整个项目到新的 `3.4 / 3.5` workflow 模型
- 不处理与本轮 live Trellis 漂移无关的其他工作树改动

## Technical Notes

- 关键真源：`.trellis/workflow.md`、`.claude/commands/trellis/finish-work.md`
- 关键漂移面：`.agents/skills/trellis-continue/SKILL.md`、`.agents/skills/trellis-brainstorm/SKILL.md`、`.agents/skills/trellis-finish-work/SKILL.md`、`.opencode/lib/session-utils.js`、`.qoder/hooks/session-start.py`、`.kiro/hooks/inject-subagent-context.py`
- 健壮性修复来源：`.claude/.codex/.kiro/.opencode/.qoder` 的 implement/check agent 与 hook 文件
