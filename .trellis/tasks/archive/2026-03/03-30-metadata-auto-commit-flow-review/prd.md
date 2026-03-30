# brainstorm: 评估元数据自动提交辅助流程

## Goal

从实际开发实践角度，重新扫描 `./docs/workflows/新项目开发工作流/` 中“元数据自动提交辅助流程”及其关联实现与文档，判断该流程是否完整、是否存在不闭环、误导、遗漏或落地成本过高的问题，并收敛出后续应补强的范围。

## What I already know

* 用户要求重新扫描相关内容，而不是只看单一文档做静态判断。
* 主文档位于 `docs/workflows/新项目开发工作流/commands/metadata-auto-commit.md`。
* 当前流程围绕两个场景展开：`task.py archive` 与 `add_session.py`。
* 当前辅助方案由 1 个 guard 脚本和 2 个 wrapper 脚本组成：
  * `docs/workflows/新项目开发工作流/commands/shell/metadata-autocommit-guard.py`
  * `docs/workflows/新项目开发工作流/commands/shell/metadata-archive-wrapper.py`
  * `docs/workflows/新项目开发工作流/commands/shell/metadata-record-session-wrapper.py`
* `delivery.md` 与 `命令映射.md` 已引用该流程，并把它视作收尾阶段门禁。
* 主文档明确宣称：
  * 自动 commit 只服务于当前任务完成后的收尾
  * staged 污染必须硬阻断
  * 不能只看脚本输出，必须用 git 状态验证闭环
* 主文档同时承认现状并不完全统一：
  * `add_session.py` 已使用共享自动提交 helper
  * `task.py archive` 仍有独立自动提交逻辑，失败语义未完全统一

## Assumptions (temporary)

* 这次工作先以“评估完整性与完善度”为主，不默认直接改代码。
* “相关联内容”至少包括工作流文档、wrapper / guard 脚本、`.trellis/scripts/task.py`、`.trellis/scripts/add_session.py`、命令部署/安装链路。
* 评估标准不仅是文档自洽，还包括：开发者是否容易正确执行、是否容易误用、脚本与文档是否一致、工具部署后是否真的可达。
* 后续若进入方案设计或修订，范围仅限 `docs/workflows/新项目开发工作流/` 这一套工作流源资产；不把修改当前项目现有 `.trellis/`、`.claude/`、`.agents/skills/` 作为前提。

## Open Questions

* `record-session` 是否仍需要一个轻量 helper 脚本来串联 guard + `add_session.py` + post-check，还是只保留文档规则与手动命令？

## Requirements (evolving)

* 重新扫描元数据自动提交辅助流程的所有关键关联内容。
* 从实际开发实践角度评估流程是否完整、是否完善。
* 识别文档与实现之间的偏差、缺口、误导点和执行摩擦点。
* 输出可操作的补强方向，区分 P0 / P1。
* 方案必须限定在 `docs/workflows/新项目开发工作流/` 可修改范围内。

## Acceptance Criteria (evolving)

* [ ] 已覆盖主流程文档、引用点、guard / wrapper、底层项目脚本与安装/部署链。
* [ ] 已明确“文档是否完整”和“落地是否顺手”两个维度的判断。
* [ ] 已列出关键缺口，并说明为什么它们会在真实开发中造成问题。
* [ ] 已形成后续修订方向或决策问题。

## Definition of Done (team quality bar)

* 结论有明确证据来源（文件路径/实现位置）
* 风险按严重性区分，而不是笼统说“可以优化”
* 若需要后续实施，能直接作为下一轮任务输入

## Out of Scope (explicit)

* 先不默认修改 `.trellis/scripts/` 或工作流命令
* 先不讨论所有其它工作流命令，只关注与元数据自动提交收尾闭环直接相关的部分

## Technical Notes

* 初步定位文件：
  * `docs/workflows/新项目开发工作流/commands/metadata-auto-commit.md`
  * `docs/workflows/新项目开发工作流/commands/delivery.md`
  * `docs/workflows/新项目开发工作流/命令映射.md`
  * `docs/workflows/新项目开发工作流/commands/shell/metadata-autocommit-guard.py`
  * `docs/workflows/新项目开发工作流/commands/shell/metadata-archive-wrapper.py`
  * `docs/workflows/新项目开发工作流/commands/shell/metadata-record-session-wrapper.py`
* 待继续核对：
  * `.trellis/scripts/task.py`
  * `.trellis/scripts/add_session.py`
  * `docs/workflows/新项目开发工作流/commands/install-workflow.py`

## Research Notes

### 已核对的实现与入口

* `add_session.py` 通过共享 helper `auto_commit_paths()` 做自动提交：
  * `./.trellis/scripts/add_session.py`
  * `./.trellis/scripts/common/git.py`
* `task.py archive` 仍使用独立 `_auto_commit_archive()` 路径：
  * `./.trellis/scripts/common/task_store.py`
* 工作流安装/升级脚本只部署：
  * `feasibility / design / plan / test-first / self-review / check / delivery`
  * helper 仅包含 `metadata-autocommit-guard.py`
* 当前仓库内现有 `record-session` 入口仍主要指向直接执行：
  * `.claude/commands/trellis/record-session.md`
  * `.agents/skills/record-session/SKILL.md`

### 当前已确认问题

* **安装态不可达**：
  * `metadata-auto-commit.md` 本身不会被安装到 `.claude/commands/trellis/`
  * 两个 wrapper 也不会被安装到 `.trellis/scripts/workflow/`
  * 但 `delivery.md` 与 `工作流总纲.md` 又把该流程当成主链规则/详细说明引用
* **命令入口不统一**：
  * 新工作流文档推荐 wrapper
  * 现有 `record-session` skill / command 仍要求直接跑 `task.py archive` 与 `add_session.py`
* **脚本守门能力不足**：
  * `metadata-autocommit-guard.py` pre-check 只检查：
    * `current-task` 是否存在
    * `archive` 目标是否等于当前任务
    * staged 区是否有 scope 外变更
  * 它**不会检查当前任务是否真的已完成**
  * 它**不会阻止 scope 内但与当前任务无关的未 staged 元数据改动**被后续 `git add -A` 一并提交
* **测试覆盖偏窄**：
  * 已有测试覆盖 guard 本身、以及 installer 是否部署 guard
  * 未覆盖 wrapper 部署、wrapper 执行链、安装后文档链接完整性

### 轻量验证结果

* 单元测试通过：
  * `docs.workflows.新项目开发工作流.commands.shell.test_metadata_autocommit_guard`
  * `docs.workflows.新项目开发工作流.commands.test_workflow_installers`
* 但安装到临时目录后，以下文件确实不存在：
  * `.claude/commands/trellis/metadata-auto-commit.md`
  * `.trellis/scripts/workflow/metadata-archive-wrapper.py`
  * `.trellis/scripts/workflow/metadata-record-session-wrapper.py`
* 最小复现显示：
  * 若其他任务的未 staged 改动位于 `.trellis/tasks/`，`record-session` 的 guard pre-check 仍会通过
  * 即使当前任务状态为 `in_progress`，guard pre-check 仍会通过

## Decision (ADR-lite)

**Context**:
用户已明确：`metadata-auto-commit` 只是 `record-session` 的一部分，而不是单独需要执行的命令，不应引入过于复杂的机制。

**Decision**:
后续新方案收敛为“`record-session` 的内建收尾子流程”，不再把 `metadata-auto-commit` 设计为独立工作流命令。

**Consequences**:
* 不再建议单独推广 `metadata-auto-commit` 为独立入口
* 优先解决：
  * 文档定位去歧义
  * `record-session` 链路内的最小 guard / wrapper
  * 安装器只部署真正会被 `record-session` 使用的辅助脚本
* `archive` 保持显式步骤，不由 `record-session` 隐式接管
* `metadata-auto-commit` 的说明不再保留为独立命令页，应合并进 `delivery` / `工作流总纲` 的收尾章节
