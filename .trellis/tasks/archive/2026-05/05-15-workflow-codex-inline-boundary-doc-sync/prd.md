# workflow-codex-inline-boundary-doc-sync

## Goal

将当前仓库里已经验证有效的 Codex inline 边界说明，最小化补充到 `docs/workflows/新项目开发工作流/` 对应的产品文档中，并修复同类传播缺口：`codex.dispatch_mode = inline` 时主会话不得手工派发 sub-agent，`.codex/agents/*` 与通用平台 multi-agent / sub-agent 能力都不构成该规则的例外；同时把相关跨文档表述统一到同一口径。

## What I already know

- 用户已明确收敛范围：只吸收“优点 2”，不吸收其他优点。
- 当前仓库 `AGENTS.md` 与 `.codex/config.toml` 已有更明确的 inline 边界口径。
- workflow 的 `commands/codex/README.md` 与 `CLI原生适配边界矩阵.md` 已覆盖 Codex hooks / skills / trusted gating / secondary carrier，但尚未把该 inline 边界说得同样直接。

## Assumptions (temporary)

- 这次改动只需要修改 `commands/codex/README.md` 与一处轻量交叉说明，不需要扩散到 `工作流总纲.md`、`AGENTS.md` 或安装器合同。
- 当前 wording 属于文档澄清，不改变安装器行为或 runtime contract。

## Open Questions

- 无阻塞问题；按用户已确认的收敛范围直接实现。

## Requirements (evolving)

- 在 Codex 定向文档中补充 inline 模式边界。
- 说明 `.codex/agents/*` 仅服务显式 delegated / non-inline 路径，不是 inline 主会话的逃生口。
- 说明 multi-agent / 通用平台 sub-agent 能力存在不意味着可绕过 inline 规则。
- 修复其他文档中同类入口描述和 implementation 内部链描述的传播缺口。
- 保持 source repo / target project / manual-maintained boundary 不被混淆。

## Acceptance Criteria (evolving)

- [ ] `commands/codex/README.md` 明确写出 inline 边界与非例外说明
- [ ] `CLI原生适配边界矩阵.md` 与相关 cross-doc 入口描述口径一致
- [ ] implementation 内部链相关文档对 Codex inline 例外有明确说明
- [ ] 未引入更大范围的合同变更
- [ ] 通过针对性搜索确认新规则在目标文档中可定位

## Definition of Done (team quality bar)

- Docs updated and internally consistent
- Relevant targeted validation/searches run
- No unrelated contract expansion

## Out of Scope (explicit)

- 不把当前仓库完整 `AGENTS.md` 规则并入 workflow 装后 `AGENTS.md`
- 不修改安装器、hooks、agents 或 runtime 脚本
- 不做 broader capability audit 或官方文档全面复核

## Technical Notes

- Candidate files:
  - `docs/workflows/新项目开发工作流/commands/codex/README.md`
  - `docs/workflows/新项目开发工作流/CLI原生适配边界矩阵.md`
  - `docs/workflows/新项目开发工作流/命令映射.md`
  - `docs/workflows/新项目开发工作流/工作流全局流转说明（通俗版）.md`
  - `docs/workflows/新项目开发工作流/工作流总纲.md`
  - `docs/workflows/新项目开发工作流/多CLI通用新项目完整流程演练.md`
  - `docs/workflows/新项目开发工作流/工作流嵌入执行规范.md`
  - `docs/workflows/新项目开发工作流/commands/check.md`
  - `docs/workflows/新项目开发工作流/commands/start-skill-patch-phase-router.md`
- Supporting repo-local evidence:
  - `AGENTS.md`
  - `.codex/config.toml`
