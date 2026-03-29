# 验证 Trellis 升级兼容性并修复问题

## Goal

对当前仓库中所有与 Trellis 升级直接相关的脚本、工作流、规范和命令入口进行一次兼容性检查与执行验证，定位升级后产生的 API、行为、路径或流程不兼容问题，并尽可能在本次任务中完成修复。

## What I already know

- 项目中的 Trellis 已经升级。
- 用户希望测试升级后的关联内容是否仍然适用，并尽可能直接修复问题。
- 当前仓库是 Trellis 管理项目，包含 `.trellis/`、`agents/`、`commands/`、`scripts/`、`trellis-library/` 等多层资产和脚本。

## Assumptions (temporary)

- 升级影响可能集中在 `.trellis/scripts/`、任务工作流、spec 说明、以及与 Trellis 命令/上下文注入相关的实现。
- 现有验证命令和单元测试可以覆盖一部分兼容性问题，但仍需要额外的定向检查。
- 当前工作区已有未提交改动，与本任务可能无关，默认不回退。

## Open Questions

- Trellis 本次升级的具体破坏性变化落在哪些接口或工作流约定上。
- 哪些验证链路最能直接暴露升级后的不兼容问题。

## Requirements (evolving)

- 识别仓库内所有与 Trellis 升级直接相关的实现与文档边界。
- 检查升级后是否存在 API、命令、路径、数据格式或行为兼容性问题。
- 运行现有验证命令，尽量覆盖关键 Trellis 工作流。
- 对发现的问题完成根因定位，并在可控范围内修复。
- 输出剩余风险和未覆盖区域。

## Acceptance Criteria (evolving)

- [ ] 已定位 Trellis 相关的核心实现和验证入口。
- [ ] 已执行至少一组能证明兼容性的关键验证命令。
- [ ] 已修复本次验证中发现的可复现问题，或明确记录无法在本轮修复的原因。
- [ ] 已说明验证结果：通过 / 失败 / 未运行。

## Definition of Done

- 相关验证命令已实际执行并记录结果。
- 涉及的代码修改已通过对应检查。
- 若行为或维护方式发生变化，相关文档或 spec 已同步更新。

## Out of Scope (explicit)

- 与 Trellis 升级无关的广泛重构。
- 无法通过当前仓库环境复现的外部平台问题。

## Technical Notes

- 任务创建路径：`.trellis/tasks/03-29-trellis-upgrade-compat-check/`
- 需要优先检查 `.trellis/scripts/`、`.trellis/spec/`、`agents/`、`commands/`、`trellis-library/` 与工具部署目录之间的衔接。

## Relevant Specs

- `.trellis/spec/scripts/python-conventions.md`: 约束 Trellis Python 脚本的实现与 CLI 形式。
- `.trellis/spec/guides/cross-layer-thinking-guide.md`: 约束脚本、hook、文档三层之间的同步与边界检查。
- `.trellis/spec/docs/index.md`: 用于校正文档中的旧路径示例，避免继续传播过期约定。

## Code Patterns Found

- `session-start` hook 通过读取 `.trellis/` 内容构造注入上下文：`.codex/hooks/session-start.py`、`.claude/hooks/session-start.py`、`.iflow/hooks/session-start.py`
- 任务上下文由 `task.py` 分发到 `common/task_context.py` 统一生成与校验。
- 命令文档当前仍以工具部署目录为 live source，需要同步修复 `.claude/`、`.opencode/`、`.iflow/` 三处。

## Files to Modify

- `.trellis/scripts/common/task_context.py`: 修复 `init-context` 对旧 `backend/frontend` spec 路径的硬编码。
- `.claude/commands/trellis/create-command.md`: 替换失效的 spec 路径示例。
- `.opencode/commands/trellis/create-command.md`: 替换失效的 spec 路径示例。
- `.iflow/commands/trellis/create-command.md`: 替换失效的 spec 路径示例。

## Confirmed Issues

- `task.py init-context <task> backend` 在当前仓库会生成不存在的 `.trellis/spec/backend/index.md`，导致 `task.py validate` 失败。
- 三套 `create-command` 文档仍引用 `.trellis/spec/backend/index.md` / `.trellis/spec/frontend/index.md`，与当前仓库的 layer-based spec 结构不一致。
