# 审计并修复新项目开发工作流嵌入问题

## Goal

基于 `/tmp/trellis-0.5.17-2` 这个已经执行过 `trellis init` 并嵌入当前 workflow 的目标项目，审计 `docs/workflows/新项目开发工作流/` 的源资产、安装器补丁、装后校验与运行时指引，判断用户列出的候选问题是否真实存在；若确认存在，则仅在 `docs/workflows/新项目开发工作流/` 内实施修复，确保后续嵌入目标项目时行为正确且不引入新的状态漂移或半迁移问题。

## What I already know

- 本仓库是 workflow 作者仓库，不是目标项目；`docs/workflows/新项目开发工作流/` 是产品源资产层。
- 用户要求的证据面是 `/tmp/trellis-0.5.17-2`，而不是当前仓库自用的 `.trellis/` 运行态。
- 修复边界是 `docs/workflows/新项目开发工作流/`；其他目录不能修改。
- 当前 workflow 相容 Trellis 版本来自 `docs/workflows/新项目开发工作流/commands/workflow_assets.py`，值为 `0.5.17`。
- 本机 `trellis -v` 返回 `0.5.17`，版本门禁允许继续，不存在需要切到 capability audit 的版本漂移阻断。
- 用户给出了一组候选问题，重点涉及：plan 创建 child task 的 active task 切换、parent/child 与 leaf-only runtime 冲突、旧 phase step API 失效、session-start 与 inject-workflow-state 语义不一致、task.py start 双真相、安装完整性校验过弱、personal profile 首次路由错误、spec 模板占位、trellis-meta 残留旧模型。

## Assumptions (temporary)

- `/tmp/trellis-0.5.17-2` 的当前状态足以代表“用户按当前 workflow 嵌入后的典型目标项目”。
- 若某个问题根因在 Trellis 原生基线，而 workflow 通过安装器补丁即可安全修复，则应优先在该 workflow 的安装/补丁层处理，而不是修改当前仓库自用基线。
- 若候选问题经核验为假警报，不应制造“顺手优化”；只修真实缺陷和同类真实缺陷。

## Open Questions

- 哪些候选问题能在 `/tmp/trellis-0.5.17-2` 中直接复现，哪些只是源层静态漂移或文档残留？
- 同类问题是否还存在于其它工作流源文件、补丁清单、安装记录或装后验证路径中？
- 是否需要补充新的安装后健康检查或安装记录字段，才能避免以后再次出现“半迁移但被判健康”？

## Requirements (evolving)

- 逐条核验用户列出的候选问题，区分真实缺陷、假警报、未证实项。
- 核验时必须以目标项目 `/tmp/trellis-0.5.17-2` 的实际嵌入结果为主证据，并回溯到 `docs/workflows/新项目开发工作流/` 源资产定位根因。
- 若确认缺陷存在，只能修改 `docs/workflows/新项目开发工作流/` 内文件。
- 修复时必须一并处理同类真实问题，避免只补单点导致继续半迁移或多真相。
- 修复方案应优先选择 workflow 源资产、安装器补丁、装后校验、文档契约这些可随嵌入传播到目标项目的层。
- 需要保留或增强安装器/补丁的幂等性，避免重复嵌入产生破坏。

## Acceptance Criteria (evolving)

- [ ] 每个候选问题都有证据结论：真实存在 / 假警报 / 未证实，并注明检测动作。
- [ ] 所有确认存在的问题都在 `docs/workflows/新项目开发工作流/` 内获得修复。
- [ ] 已发现的同类真实问题被一并修复，而不是只处理用户列出的单点。
- [ ] 相关补丁、安装校验、文档指引之间保持一致，不再出现明显双真相或半迁移缺口。
- [ ] 运行相关验证命令后，至少能证明修改后的源资产在静态层面自洽；若可行，再用 `/tmp/trellis-0.5.17-2` 或新的临时项目做针对性验证。

## Definition of Done (team quality bar)

- 真实问题有证据、有修复、有验证结果。
- 修改只发生在允许范围内。
- 相关文档或校验逻辑同步更新，不留下已知漂移。
- 运行与本次改动直接相关的验证命令，并如实记录 pass / fail / not run。

## Out of Scope (explicit)

- 修改当前仓库自用 `.trellis/`、`.codex/`、`.claude/` 等非 `docs/workflows/新项目开发工作流/` 路径下的文件。
- 顺手优化与本次候选问题无关的 workflow 设计。
- 把 source 仓库当前运行机制重构成与目标项目完全一致。

## Technical Notes

- Workflow source root: `docs/workflows/新项目开发工作流/`
- Evidence target project: `/tmp/trellis-0.5.17-2`
- 版本锚点：`docs/workflows/新项目开发工作流/commands/workflow_assets.py`
- 审计技能边界：`workflow-audit`
- 代码定位已通过 `ace.search_context` 完成一轮初筛，后续需要补充静态读文件与目标项目行为验证。
