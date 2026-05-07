# 为 Codex 平台实现自动提交失败恢复增强

## Goal

根据《Trellis自动提交失败恢复与提权修复指南》，为 Codex 平台添加自动提交失败恢复能力，使其能够在只读/权限受限环境下识别失败、生成机器可读恢复命令，并支持提权重试。

## What I already know

* **适用范围**：仅 Codex 平台需要此增强；Claude Code 和 OpenCode 使用原生 Trellis，由基线负责自动提交行为
* **恢复指南已明确定义**：
  - 需要修改的脚本：`record-session-helper.py`、`metadata-autocommit-guard.py`
  - 需要修改的入口文档：Codex 的 finish-work patch（`finish-work-patch-projectization.md`）
  - 核心机制：只读失败检测、pending 状态文件、`TRELLIS_AUTO_ESCALATE_COMMAND` 输出、`--resume` 支持
* **两条链路**：
  - archive 链：`task.py archive` 自动提交 `.trellis/tasks`（**属于 Trellis 基线，workflow 不分发**）
  - record-session 链：`record-session-helper.py`（由 finish-work 内部调用）自动提交 `.trellis/workspace` + `.trellis/tasks`（**属于 workflow 托管**）
* **当前 workflow 托管边界**：
  - ✅ 分发：`record-session-helper.py`、`metadata-autocommit-guard.py`（在 HELPER_SCRIPTS 中）
  - ✅ Patch 机制：Codex finish-work 通过 patch 增强基线 skill（`CODEX_PATCH_BASELINE_SKILLS`）
  - ❌ 不分发：`task.py`、`task_store.py`、`add_session.py`（属于 Trellis 基线）
* **Patch 文件位置**：
  - Codex finish-work patch 源：`docs/workflows/新项目开发工作流/commands/finish-work-patch-projectization.md`
  - 安装器通过 `inject_codex_finish_work_skill_patch` 函数注入到基线 skill
* **现有文档状态**：
  - `工作流总纲.md` 第 3028 行有通用的失败处理指导："若自动提交失败，应视为 `record-session` 未完成，先处理 git 写入失败原因，再结束本轮工作"
  - 该指导是**通用的**，未区分平台
  - 各平台 README 都强调 archive 调用基线，建议升级 Trellis
  - **未发现**已有的自动提交恢复机制代码实现

## Assumptions (temporary)

* Codex 的 finish-work 入口文档位于 `docs/workflows/新项目开发工作流/commands/codex/` 或通过 patch 机制注入
* `record-session-helper.py` 和 `metadata-autocommit-guard.py` 是 workflow 托管的共享脚本
* `task.py` 相关脚本可能属于 Trellis 基线，需要判断是否应在 workflow 层面增强还是仅增强调用方

## Open Questions

* [Blocking] **archive 链如何处理？**
  - `task.py` / `task_store.py` 属于 Trellis 基线，workflow 不分发这些脚本
  - 恢复指南建议添加 `archive-commit-only` 子命令，但这需要修改基线
  - 选项：
    1. **仅增强 record-session 链**：只增强 `record-session-helper.py` 和 `metadata-autocommit-guard.py`，不处理 archive 链的恢复
    2. **在 helper 层绕过**：在 finish-work 入口层面提供完整的收尾恢复路径（包括 record-session 和 archive）
    3. **分发增强版基线脚本**：在 workflow 中分发增强版的 `task.py` / `task_store.py`（违反当前托管边界原则）
  - **推荐选项 1**：保持当前边界清晰，仅增强 workflow 托管的 record-session 链；archive 链依赖用户升级 Trellis 基线

* [Preference] **pending 状态文件的存储位置？**
  - 恢复指南建议：`.trellis/.pending-record-session/<slug>.pending.json`
  - 是否需要考虑与 Trellis 基线的兼容性？

## Decision (ADR-lite)

**Context**: archive 链（`task.py` / `task_store.py`）属于 Trellis 基线，workflow 不分发这些脚本。恢复指南建议添加 `archive-commit-only` 子命令，但修改基线会违反当前托管边界。

**Decision**: 采用选项 1，仅增强 record-session 链。修改工作流源资产（`docs/workflows/新项目开发工作流/commands/shell/` 下的托管脚本），增强 `record-session-helper.py` 和 `metadata-autocommit-guard.py`，添加只读失败检测、pending 状态、`TRELLIS_AUTO_ESCALATE_COMMAND` 输出和 `--resume` 支持。

**Consequences**:
- ✅ 保持托管边界清晰，不与 Trellis 基线升级冲突
- ✅ record-session 链是 Codex finish-work 的主要收尾路径，覆盖核心场景
- ⚠️ archive 链仍可能失败，依赖用户升级 Trellis 基线
- 需要在 Codex finish-work patch 文档中说明 archive 链的基线依赖

## Expansion Sweep (Diverge → Converge)

**未来演进**：
* 可能需要支持其他 CLI（如 Qoder）的自动提交恢复，但当前仅针对 Codex
* pending 文件可能需要支持跨 CLI 恢复（如 Codex 失败后由 Claude Code 接手）

**相关场景**：
* finish-work 的完整收尾流程：record-session → archive
* 其他可能触发 git commit 的 workflow 命令（如 design 阶段的产物提交）
* 与 `.gitignore` 的交互：pending 文件是否应该被忽略

**失败与边缘情况**：
* pending 文件本身写入失败（磁盘满、权限问题）
* 多个 pending 文件同时存在（多次失败累积）
* `--resume` 时原始参数丢失或环境变化
* 并发执行时的竞态条件（多个 finish-work 同时运行）
* 网络隔离环境下的 git 操作失败

**MVP 边界决定**：
- **包含**：Codex record-session 链的只读失败检测与恢复
- **包含**：pending 文件的基本管理（创建、读取、清理）
- **排除**：跨 CLI 恢复支持（未来可能）
- **排除**：并发执行的高级处理（当前按单任务串行假设）

## Requirements (final)

**1. 只读失败检测**：
* 在 `metadata-autocommit-guard.py` 中定义只读失败关键词：
  ```python
  READONLY_HINTS = (
      "Read-only file system",
      "只读文件系统",
      "Permission denied",
      "Operation not permitted",
      ".git/index.lock",
      "cannot create",
      "不能创建",
  )
  ```
* 在 git 操作失败时检查 stderr，区分只读失败和其他失败

**2. Pending 状态管理**：
* 创建目录：`.trellis/.pending-record-session/`
* 生成 pending 文件：`<timestamp>-<slug>.pending.json`
* 文件内容：
  ```json
  {
    "timestamp": "ISO8601",
    "title": "会话标题",
    "commit": "hash1,hash2",
    "summary": "会话摘要",
    "branch": "分支名",
    "package": "包名",
    "repo_root": "项目根路径",
    "failed_step": "pre-check | add_session | post-check"
  }
  ```
* 提供 `--resume <pending-file>` 参数恢复执行

**3. 恢复命令输出**：
* 失败时输出：
  ```
  ⚠️  record-session metadata auto-commit 失败，检测到可能的只读/受限写入环境。
  如果当前 CLI 支持提权重试，请立即用提权方式执行：
  python3 ./.trellis/scripts/workflow/record-session-helper.py --resume <pending-file>
  TRELLIS_AUTO_ESCALATE_COMMAND=python3 ./.trellis/scripts/workflow/record-session-helper.py --resume <pending-file>
  ```

**4. Exit Code 规范**：
* 成功：`0`
* record-session 失败（含只读失败）：`1`
* 不改变现有的 exit code 语义

**5. 文档更新**：
* 在 `finish-work-patch-projectization.md` 中添加：
  - 自动提交失败恢复流程说明（**仅针对 Codex**）
  - `--resume` 使用方法
  - archive 链的基线依赖说明（依赖用户升级 Trellis）
* 在 `工作流总纲.md` 中明确说明：
  - 第 3028 行的"自动提交失败"指导仅适用于 **Codex 平台**
  - Claude Code / OpenCode 使用原生 Trellis，由基线负责自动提交行为
  - 或将该段指导改为平台特定的分情况说明
* 在 `CLI原生适配边界矩阵.md` 的"收尾基线依赖"部分明确：
  - Codex 的 record-session 链需要 workflow 增强的恢复机制
  - Claude Code / OpenCode 完全依赖原生 Trellis

**文件修改清单**：
* `docs/workflows/新项目开发工作流/commands/shell/record-session-helper.py`
  - 添加 `--resume` 参数
  - 添加失败检测和 pending 文件生成
  - 添加 `TRELLIS_AUTO_ESCALATE_COMMAND` 输出
* `docs/workflows/新项目开发工作流/commands/shell/metadata-autocommit-guard.py`
  - 添加 `READONLY_HINTS` 定义
  - 添加只读失败检测函数
* `docs/workflows/新项目开发工作流/commands/finish-work-patch-projectization.md`
  - 添加恢复流程说明（仅针对 Codex）
  - 添加 archive 链基线依赖说明
* `docs/workflows/新项目开发工作流/工作流总纲.md`
  - 更新第 3028 行附近的自动提交失败指导，明确仅针对 Codex
  - 或改为平台特定分情况说明
* `docs/workflows/新项目开发工作流/CLI原生适配边界矩阵.md`
  - 在"收尾基线依赖"部分明确 Codex 的恢复机制需求

## Acceptance Criteria (final)

**功能验证**：
* [ ] `metadata-autocommit-guard.py` 能够识别只读失败（通过 stderr 关键词）
* [ ] `record-session-helper.py` 失败时生成 pending 文件到 `.trellis/.pending-record-session/`
* [ ] pending 文件包含完整的恢复上下文（title, commit, summary, branch, repo_root, failed_step）
* [ ] 失败输出包含 `TRELLIS_AUTO_ESCALATE_COMMAND=...`
* [ ] `--resume <pending-file>` 能够正确恢复中断的会话记录
* [ ] `--resume` 执行成功后清理对应的 pending 文件

**文档验证**：
* [ ] `finish-work-patch-projectization.md` 包含恢复流程说明（仅针对 Codex）
* [ ] 包含 archive 链的基线依赖说明
* [ ] 包含 `--resume` 使用示例
* [ ] `工作流总纲.md` 明确说明自动提交失败指导仅适用于 Codex
* [ ] `CLI原生适配边界矩阵.md` 明确 Codex 的恢复机制需求
* [ ] 文档中不存在针对 Claude Code / OpenCode 的自动提交增强说明

**测试覆盖**：
* [ ] 正常闭环：record-session 成功，无 pending 文件残留
* [ ] 无变更跳过：git 操作无变更时正确处理
* [ ] 只读失败恢复：模拟只读失败，验证 pending 文件生成和恢复
* [ ] 普通失败：非只读失败不生成 pending 文件（按原有行为报错）

**代码质量**：
* [ ] 脚本语法验证通过：`python3 -m py_compile record-session-helper.py metadata-autocommit-guard.py`
* [ ] 不影响 Claude Code / OpenCode 的现有行为（修改的是共享脚本，但行为向后兼容）

## Definition of Done (team quality bar)

* [ ] 所有 Acceptance Criteria 通过
* [ ] 测试用例已编写并通过
* [ ] 脚本语法验证通过
* [ ] 文档已更新
* [ ] 不影响其他平台的现有行为
* [ ] 符合恢复指南的核心要求（仅 record-session 链部分）

## Out of Scope (explicit)

* **archive 链增强**：`task.py` / `task_store.py` 属于 Trellis 基线，不在 workflow 托管范围
* **Claude Code / OpenCode 平台**：它们使用原生 Trellis，由基线负责自动提交行为
* **跨 CLI 恢复支持**：pending 文件仅供当前 CLI 恢复使用
* **并发执行处理**：假设单任务串行执行，不处理竞态条件
* **网络隔离环境**：网络问题导致的 git 失败不属于只读失败范畴
* **跨项目恢复**：pending 文件绑定到特定项目的 repo_root

## Technical Notes

**相关文件**：
* 恢复指南：`docs/Trellis自动提交失败恢复与提权修复指南.md`
* 共享脚本位置：`docs/workflows/新项目开发工作流/commands/shell/`
* Codex README：`docs/workflows/新项目开发工作流/commands/codex/README.md`
* CLI 边界矩阵：`docs/workflows/新项目开发工作流/CLI原生适配边界矩阵.md`
* workflow_assets.py：`docs/workflows/新项目开发工作流/commands/workflow_assets.py`

**托管边界约束**：
* `record-session-helper.py` 和 `metadata-autocommit-guard.py` 在 `HELPER_SCRIPTS` 中定义，由安装器分发到 `.trellis/scripts/workflow/`
* `finish-work-patch-projectization.md` 通过 `inject_codex_finish_work_skill_patch` 注入到 Codex 基线 skill
* `task.py` / `task_store.py` / `add_session.py` 属于 Trellis 基线，workflow 不分发

**实现约束**：
* 向后兼容：新参数 `--resume` 是可选的，不影响现有调用方式
* Exit code 保持语义：`0` 表示成功，`1` 表示失败（细化失败类型但不改变 exit code）
* pending 文件命名：使用时间戳前缀保证唯一性
* `.gitignore` 建议：pending 目录应被忽略（临时状态文件）

**依赖的外部能力**：
* `add_session.py`（Trellis 基线）：被 `record-session-helper.py` 调用
* git 命令：`git add` / `git commit` / `git status`

## Phase 1.2 Status

✅ **implement.jsonl 已 curate**：包含 8 个 spec/research 文件，覆盖恢复指南、托管边界、平台特点、待增强脚本等上下文
✅ **check.jsonl 已 curate**：包含 5 个验证相关文件，覆盖验证标准、边界一致性、文档一致性、测试基础等上下文

## Implementation Plan (small PRs)

**PR1：文档审查与清理**
- 审查 `工作流总纲.md`，更新第 3028 行自动提交失败指导为平台特定说明
- 更新 `CLI原生适配边界矩阵.md`，明确 Codex 恢复机制需求
- 确保文档中不存在针对 Claude Code / OpenCode 的自动提交增强说明

**PR2：增强 `metadata-autocommit-guard.py`**
- 添加 `READONLY_HINTS` 定义
- 添加 `detect_readonly_failure()` 函数
- 添加单元测试

**PR3：增强 `record-session-helper.py`**
- 添加 `--resume` 参数支持
- 添加 pending 文件管理（创建、读取、清理）
- 添加恢复命令输出（`TRELLIS_AUTO_ESCALATE_COMMAND`）
- 添加集成测试

**PR4：更新 `finish-work-patch-projectization.md` + 验证**
- 添加 Codex 平台的恢复流程说明
- 添加 archive 链基线依赖说明
- 添加 `--resume` 使用示例
- 验证完整流程（正常、失败恢复、边界情况）

