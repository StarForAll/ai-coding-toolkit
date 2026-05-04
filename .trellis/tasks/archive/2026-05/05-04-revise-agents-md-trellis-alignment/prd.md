# 修订 AGENTS.md 对齐当前 Trellis 实现

## Goal

把项目根 `AGENTS.md` 修订为符合当前仓库实际状态的项目级长期规则入口。

## Problems

- 文件开头把规则错误地写成 Qoder 专用，而当前仓库实际面向多 CLI。
- 非托管区段混入了部分低价值或易漂移内容，例如统一化的 slash command 叙述和独立的 commit convention。
- 架构描述把 `agents/`、`commands/` 写成了已经全面落地的 source-of-truth，但当前仓库现实仍是“部分骨架 + 部分隐藏目录部署层并存”。
- 文档没有明确区分长期规则层与运行时上下文注入层，容易把 `AGENTS.md` 和 `.trellis`/hooks 的职责混淆。

## Scope

- 重写 `AGENTS.md` 的非托管区段。
- 保留 `<!-- TRELLIS:START --> ... <!-- TRELLIS:END -->` 托管区段不动。
- 保留合理的项目级规则：meta-project 定位、spec 先读、验证要求、禁止 `git commit`、journal 上限、README 双语同步。

## Success Criteria

- `AGENTS.md` 明确这是多 CLI 共用的项目级长期规则入口。
- 文档反映当前仓库现实，而不是把目标项目安装态或未来源资产层直接当成当前事实。
- Codex / Claude / OpenCode 的高层入口边界表述正确，不再误导为统一的 `/trellis:xxx` 目录模型。
- 删除或压缩低价值、易冲突的段落，同时保留真正需要长期稳定存在的项目规则。
