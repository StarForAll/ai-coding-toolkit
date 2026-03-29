# 分析 .new 文件合并策略

## Goal

分析当前仓库中 10 组 `.new` 后缀文件与对应原文件的差异，在 Trellis 框架（source/deploy 分层）内判断每组应"直接择一"还是"合并优化"。

## What I already know

- 仓库中有 10 个 `.new` 文件，分布在 scripts、skills、commands、config 四层
- `.new` 文件均为未追踪状态（??）
- 原文件多数已修改（M）但未提交
- Trellis 框架中 skills/commands 存在 source → deploy 同步关系

## Analysis

### Group A: Python Scripts（3 组）

| # | 文件 | 变化 | 建议 |
|---|------|------|------|
| 1 | `git.py` | .new 新增 `auto_commit_paths()` 共享工具函数 | 择一：选 .new |
| 2 | `task_store.py` | .new 使用 `auto_commit_paths`，改进错误处理和返回值 | 择一：选 .new（与 git.py.new 配套） |
| 3 | `add_session.py` | .new 新增 `--branch` 功能，但用原始 subprocess 而非 `auto_commit_paths` | **合并**：保留当前版本的 `auto_commit_paths` 模式 + 加入 .new 的 branch 功能 |

### Group B: Skills（4 组）

| # | 文件 | 变化 | 建议 |
|---|------|------|------|
| 4 | `.agents/skills/finish-work/` | .new 通用化 Code Quality、新增 trellis-library 校验、移除 Test Coverage | 择一：选 .new（可能需合并 Test Coverage） |
| 5 | `.agents/skills/record-session/` | .new 新增 branch 文档、移除 postcondition 校验步骤 | **合并**：保留 postcondition 校验 + 加入 branch 文档 |
| 6 | `.agents/skills/update-spec/` | 仅 frontmatter description 增强 | 择一：选 .new |
| 7 | `.kiro/skills/update-spec/` | 仅 frontmatter description 增强 | 择一：选 .new |

### Group C: Commands（2 组）

| # | 文件 | 变化 | 建议 |
|---|------|------|------|
| 8 | `.claude/commands/trellis/finish-work.md` | .new 新增 trellis-library 校验 Section 7、更新 Block Rule | 择一：选 .new |
| 9 | `.iflow/commands/trellis/finish-work.md` | 同上 | 择一：选 .new |

### Group D: Config（1 组）

| # | 文件 | 变化 | 建议 |
|---|------|------|------|
| 10 | `.trellis/worktree.yaml` | verify 注释改为 trellis-library 验证命令 | 择一：选 .new |

## Summary

- **直接择一（选 .new）**: 8 组 (#1, #2, #4, #6, #7, #8, #9, #10)
- **需合并优化**: 2 组 (#3 add_session.py, #5 record-session)

## Open Questions

- add_session.py 合并策略确认
- record-session postcondition 校验是否保留

## Requirements (evolving)

- 清理 .new 文件，消除仓库中的未追踪文件
- 确保代码一致性（import、函数调用、文档引用）
- 保持跨工具部署同步（skills/commands 各目录）

## Acceptance Criteria (evolving)

- [ ] 10 组 .new 文件全部处理完毕
- [ ] 无 `.new` 后缀文件残留在仓库中
- [ ] Python 脚本 import 链正确（git.py → task_store.py → add_session.py）
- [ ] Skills 和 Commands 内容在工具部署层保持一致

## Out of Scope (explicit)

- 不涉及 `agents/` source 源资产层的创建（那是独立任务 03-19-implement-agents-source）
- 不涉及 `commands/` source 源资产层的创建（那是独立任务 03-19-implement-commands-source）
- 不涉及 `.kiro/skills/finish-work/` 的同步（已在工作树中直接修改）

## Technical Notes

- `.agents/skills/` 是 agents 工具部署目录，非 source 层
- `.kiro/skills/finish-work/` 已在工作树中修改但无 .new，需单独检查
- 当前 `add_session.py` 引用了 `auto_commit_paths`（来自 `git.py`），但当前 `git.py` 中该函数不存在——说明工作树状态不一致，需要统一
