# 恢复当前项目 Trellis 0.5.10 升级漂移

## Goal

按当前仓库真实生效的 Trellis live 合同恢复本轮 0.5.10 小版本升级后的工作树：

1. 修正错误的 Phase 编号引用，统一回当前 `.trellis/workflow.md`
2. 恢复 `trellis-research` 的证据优先工具链与 active-task 解析协议
3. 删除不应保留的 `.new` 升级残留
4. 保留 `safe_commit` 主修复，并收紧其 staged 范围，避免误纳入并行 active task
5. 让 `.trellis/.template-hashes.json` 与最终 live 文件一致

## Scope

- 当前仓库 live `.trellis/`、`.agents/skills/`、`.codex/`、`.claude/`、`.opencode/`、`.qoder/`、`.kiro/`
- 本仓库实际使用的 Trellis runtime / hooks / skills / agents / close-out 行为

## Non-Goals

- 不改 `docs/workflows/新项目开发工作流/` 产品资产
- 不切换当前仓库的 Codex `inline` 运行模型
- 不把当前仓库迁移到另一套 Phase 编号体系

## Acceptance Criteria

1. 所有 live Phase 引用与 `.trellis/workflow.md` 一致
2. `trellis-research` 在支持的平台恢复 `ace` / `Context7` / `deepwiki` / `grok-search` / `exa` 路径说明
3. 应丢弃的 `.new` 文件全部移除
4. `safe_commit` 不再扫描全部 active task 目录，只处理本次 auto-commit 需要的明确路径
5. 相关验证命令通过
