# settle trellis 0.5.12 upgrade residue and restore research agent contract

## Goal

收敛当前仓库因 Trellis 0.5.12 小版本升级产生的 live/runtime 变更与 `.new` 候选，恢复当前项目真实运行面下的 Trellis 合同：保留有效升级项，回退错误的 `trellis-research` 能力简化和 Phase 编号漂移，补齐或撤回未完整落地的升级项，并让 `.template-hashes.json` 与最终 live 文件一致。

## What I already know

- 当前项目真实生效的 Trellis 运行面是 `.trellis/`、平台 live agent/skill/command 文件和各平台 hook/config，不是 `docs/workflows/新项目开发工作流/`。
- 当前 live workflow 的原始 Phase 编号为 `1.1 / 1.3 / 1.4 / 2.1 / 2.2 / 2.3 / 3.4 / 3.5`。
- `trellis-research` 在当前 worktree 的 Claude/OpenCode/Qoder live 文件中被错误简化，丢失 `ace.search_context`、`Context7`、`deepwiki`、`grok-search` 和搜索路由表。
- 一批 `.new` 文件把 continue / finish-work / brainstorm / codex agent 合同回退到了不适配当前仓库的模板状态。
- `session_auto_commit` 目前只改到了 `.trellis/config.yaml` 和 `common/config.py`，尚未接入 `add_session.py` / `task_store.py` 实际调用链。
- `.trellis/.template-hashes.json` 已记录当前未最终裁决的 live 文件哈希，必须在最终内容稳定后刷新。

## Assumptions (temporary)

- 本轮应以“恢复当前仓库实际 Trellis 合同”为准，而不是盲跟 Trellis 0.5.12 模板候选。
- 对 `.new` 文件采用逐个裁决策略，不存在必须整体采用的候选集。
- `session_auto_commit` 若保留，就应该在本轮补完整条调用链；否则会留下半升级状态。

## Open Questions

- 无阻塞性开放问题；按已审计出的处置矩阵执行。

## Requirements (evolving)

- 恢复 Claude/OpenCode/Qoder 的增强版 `trellis-research` 合同，与当前仓库对 `ace`/额外研究工具的要求一致。
- 保持 Codex live 文件中的 inline/non-inline 边界说明，不被 `.new` 弱化。
- 回退 live 文档中错误的 Phase 编号漂移，继续使用当前仓库原本的编号。
- 补齐 `session_auto_commit` 到 `add_session.py` / `task_store.py` 的实际行为接线。
- 删除本轮已明确拒收的 `.new` 文件。
- 在最终 live 内容确定后刷新 `.trellis/.template-hashes.json`。

## Acceptance Criteria (evolving)

- [ ] `.claude/.opencode/.qoder` 的 `trellis-research` 恢复增强工具能力和搜索路由说明
- [ ] `trellis-meta` 相关 live 文档恢复到当前仓库真实 Phase 编号
- [ ] `session_auto_commit` 配置真实影响 `add_session.py` 与 `task.py archive` 的 auto-commit 行为
- [ ] 全部 `.new` 文件按本轮方案清理完毕
- [ ] `.trellis/.template-hashes.json` 与最终保留的 live 文件一致
- [ ] 相关验证命令通过

## Definition of Done (team quality bar)

- Tests added/updated where behavior changed
- Lint / typecheck / targeted validation green
- Docs/notes updated if behavior changes
- Hash baseline updated only after final live content stabilizes

## Out of Scope (explicit)

- 改造 `docs/workflows/新项目开发工作流/` 产品源资产
- 提交 git commit
- 处理与本轮升级残留无关的并行工作树修改

## Technical Notes

- 关键运行面：`.trellis/workflow.md`、`.trellis/scripts/common/active_task.py`、`.trellis/scripts/common/session_context.py`、`.codex/config.toml`、各平台 `trellis-research` live 文件。
- 关键回归面：`trellis-research` 能力简化、Phase 漂移、`.new` 模板误收、`session_auto_commit` 半升级、`.template-hashes.json` 提前刷新。
