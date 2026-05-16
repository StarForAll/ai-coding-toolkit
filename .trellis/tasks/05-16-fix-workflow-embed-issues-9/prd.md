# 修复工作流嵌入后 9 个一致性问题

## Goal

修复 `docs/workflows/新项目开发工作流` 中的 9 个问题，使 `install-workflow.py` 嵌入后的目标项目不再出现 breadcrumb 状态不一致、文档引用缺失、流程冲突等缺陷。修复范围仅限源资产目录，不影响其他目录。

## What I already know

### 嵌入后目标项目实际状态 (`/tmp/trellis-0.5.16-2`)

- `inject-workflow-state.py` 第 181 行读取 `task.json.status` 决定 breadcrumb key
- `workflow-state.py` 第 1157 行附近管理 `workflow-state.json` 中的强门禁 stage
- 嵌入后 `workflow.md` 同时保留了原生三阶段 Phase Index 和强门禁 Phase Index
- `workflow.md` 第 658 行在代码块内有 `[workflow-state:my-status]` 示例
- `workflow.md` 第 688 行引用不存在的 `workflow-state-contract.md`
- `workflow-state.py` STAGES 包含 `record-session` 但无对应 breadcrumb 块
- `feasibility/SKILL.md` Step 0.5 已创建任务 + 初始化 workflow-state.json
- `trellis-continue/SKILL.md` 第 131 行写明 `codex.dispatch_mode=inline` 时主会话 inline 执行
- `implementation` breadcrumb 写 "Dispatch sub-agent or inline with explicit user override"

### 修复入口

所有修复必须作用于 `docs/workflows/新项目开发工作流/` 目录下的源资产文件，嵌入器会读取这些源资产写入目标项目。关键源文件：

- `commands/workflow-patch-projectization.md` — Phase Index / breadcrumb / no_task 补丁模板
- `commands/install-workflow.py` — 嵌入执行器（含注入逻辑）
- `learn/` 目录下的工作流文档（嵌入后追加到 workflow.md）

## Issues & Fix Plan

### Issue 1 (高风险): hook 用 task.json.status 决定 breadcrumb，但强门禁状态在 workflow-state.json

**现象**: `inject-workflow-state.py` 第 181 行读取 `task.json.status`，返回 `(task_id, status, source)`。对于强门禁项目，实际 stage 存储在 `$TASK_DIR/workflow-state.json` 的 `stage` 字段。task.json.status 仍为 `planning` / `in_progress` 的旧三阶段值，而 workflow-state.json.stage 可能为 `feasibility` / `brainstorm` / `design` / `plan` / `implementation` 等细粒度值。结果是 hook 发出的 breadcrumb key 与实际阶段不匹配。

**修复方案**: 在 `install-workflow.py` 嵌入器中，嵌入完成后对已部署的 `inject-workflow-state.py` 进行补丁：在 `get_active_task()` 返回结果后，检查 `workflow-state.json` 并优先使用其 `stage` 字段。具体做法：新增 `patch_inject_workflow_state_hook()` 函数，在 hook 文件中 `get_active_task()` 返回 task 信息后插入一段逻辑：读取同目录下 `workflow-state.json`，若存在且含有效 `stage` 字段，则用 `stage` 替换 `status`。

**修复位置**: `docs/workflows/新项目开发工作流/commands/install-workflow.py` — 新增 `patch_inject_workflow_state_hook()` 函数 + 在嵌入流程末尾调用。

**证据**: `/tmp/trellis-0.5.16-2/.codex/hooks/inject-workflow-state.py:181` vs `/tmp/trellis-0.5.16-2/.trellis/scripts/workflow/workflow-state.py` STAGES 定义。

---

### Issue 2 (高风险): workflow.md 同时保留原生 Phase Index 和强门禁 Phase Index

**现象**: 嵌入后 workflow.md 包含两个 `## Phase Index` 区块：
1. 原生三阶段：Phase 1: Plan → Phase 2: Execute → Phase 3: Finish（含 `no_task` / `planning` / `in_progress` / `completed` 四个 breadcrumb）
2. 强门禁：feasibility → brainstorm → ... → delivery → record-session（含 12 个细粒度 breadcrumb）

`inject-workflow-state.py` 的 `load_breadcrumbs()` 用正则扫描整个文件，两个区块的 `no_task` 块都会被匹配。由于 `finditer` 返回所有匹配，后出现的 `no_task` 会覆盖先出现的，导致强门禁版本的 no_task 被旧三阶段版本覆盖（或反之，取决于匹配顺序）。

**修复方案**: 在 `inject_workflow_phase_index_patch()` 执行时，不仅替换 Phase Index 段，还必须删除原生三阶段区块中的旧 `[workflow-state:no_task]` / `[workflow-state:planning]` / `[workflow-state:in_progress]` / `[workflow-state:completed]` 及其 `-inline` 变体块，避免同一个 status 有多个 breadcrumb 定义。

具体修改 `install-workflow.py`：在 Phase Index 补丁注入成功后，扫描并移除旧三阶段 breadcrumb 块。

**修复位置**: `docs/workflows/新项目开发工作流/commands/install-workflow.py` — `inject_workflow_phase_index_patch()` 或新增清理函数。

**证据**: `/tmp/trellis-0.5.16-2/.trellis/workflow.md` 同时存在 line 152 `[workflow-state:no_task]`（旧）和 line 895 `[workflow-state:no_task]`（新）。

---

### Issue 3 (高风险): no_task 引导 feasibility 后再 task.py create，但 feasibility 自己已创建任务

**现象**: 强门禁 `no_task` B 规则写明：outsourcing 流程为 route → feasibility → task.py create → brainstorm → task.py start。但 `feasibility/SKILL.md` Step 0.5 已执行 `task.py create` + `workflow-state.py init`。用户按 no_task 引导先 feasibility 再手动 create，会重复建任务；且第二个任务不会自动初始化 `workflow-state.json`（因为 `task.py create` 不写此文件）。

**修复方案**: 修改强门禁 `no_task` B 规则文案，将 outsourcing 路径改为：route → feasibility（feasibility 内部自动创建任务和初始化 workflow-state）→ brainstorm → task.py start。去掉显式的 `task.py create` 步骤，改为提示"feasibility skill 会自动创建任务目录"。

**修复位置**: `docs/workflows/新项目开发工作流/commands/workflow-patch-projectization.md` 的 `<!-- workflow-projectization-no-task-patch -->` 区块。

**证据**: `/tmp/trellis-0.5.16-2/.trellis/workflow.md:895-908` no_task B 规则 vs `/tmp/trellis-0.5.16-2/.agents/skills/feasibility/SKILL.md:49` Step 0.5。

---

### Issue 4 (高风险): 强门禁状态机有严格校验但缺少阶段切换命令模板

**现象**: `workflow-state.py set` 要求合法组合，例如进入 implementation 必须 `stage_status=awaiting_user_confirmation` 且 `execution_authorized=true`。但嵌入后 workflow.md 只笼统说 "set stage"，没有提供完整的命令模板。用户/AI 在实操中容易卡在 `repair/blocked`，或被迫使用 `--force` 绕过。

**修复方案**: 在强门禁 Phase Index 区块（或相邻位置）增加一个"阶段切换命令速查"小节，列出每个阶段切换所需的最小命令集合。例如：
- brainstorm → design: `workflow-state.py set <dir> --stage design --stage-status awaiting_user_confirmation`
- plan → implementation: `workflow-state.py set <dir> --stage implementation --execution-authorized true`（前提：stage_status 已为 awaiting_user_confirmation）

**修复位置**: `docs/workflows/新项目开发工作流/commands/workflow-patch-projectization.md` 的 Phase Index 补丁区块末尾。

**证据**: `/tmp/trellis-0.5.16-2/.trellis/scripts/workflow/workflow-state.py:920` 的校验逻辑 vs 嵌入后 workflow.md 缺少命令模板。

---

### Issue 5 (中风险): record-session 存在于 STAGES 和 Phase Index 但无对应 breadcrumb 块

**现象**: `workflow-state.py` STAGES 集合包含 `record-session`，Phase Index 也列出 `record-session` 作为最终阶段，但 `workflow-patch-projectization.md` 和嵌入后的 workflow.md 都没有 `[workflow-state:record-session]` 块。如果状态真的进入此 stage，breadcrumb 会降级为 "Refer to workflow.md for current step." 的通用文案。

**修复方案**: 在 breadcrumb 补丁中增加 `[workflow-state:record-session]` 块，内容指向 `/trellis:record-session`（legacy 兼容）或说明此阶段由 `add_session.py` 完成。

**修复位置**: `docs/workflows/新项目开发工作流/commands/workflow-patch-projectization.md` 的 `<!-- workflow-projectization-breadcrumb-patch -->` 区块，在 `[workflow-state:delivery]` 之后、`---` 之前。

**证据**: `/tmp/trellis-0.5.16-2/.trellis/scripts/workflow/workflow-state.py:60` STAGES 含 `record-session`，但 `/tmp/trellis-0.5.16-2/.trellis/workflow.md` 中无 `[workflow-state:record-session]`。

---

### Issue 6 (中风险): 文档引用不存在的 workflow-state-contract.md

**现象**: 嵌入后 workflow.md 第 688 行引用 `.trellis/spec/cli/backend/workflow-state-contract.md`，但该文件在嵌入后的目标项目中不存在（`/tmp/trellis-0.5.16-2/.trellis/spec/cli/` 目录为空或无 backend 子目录）。

**修复方案**: 将引用改为指向实际存在的文件：`workflow-state.py --help` 或 `workflow-state.py show`，或直接在 workflow.md 中内联关键契约要点，而非指向一个不存在的文件。

**修复位置**: 这段文本来自 Trellis 基线 workflow.md（不属于强门禁补丁），需要在嵌入过程中清理此引用。具体修改点取决于这段文本出现在哪个注入阶段 — 它在原生 workflow.md 的 "Customizing Trellis" 区块，嵌入器未修改此区块。需在 `install-workflow.py` 中增加对这段引用的清理/替换逻辑。

**证据**: `/tmp/trellis-0.5.16-2/.trellis/workflow.md:688` 引用 vs `/tmp/trellis-0.5.16-2/.trellis/spec/cli/backend/` 不存在。

---

### Issue 7 (中风险): [workflow-state:my-status] 示例在代码块中被 hook regex 解析

**现象**: 嵌入后 workflow.md "Customizing Trellis" 区块中，`[workflow-state:my-status]` 示例写在 markdown 代码块内，但 `inject-workflow-state.py` 的 `_TAG_RE` 正则不排除代码块，会把它当作真实 breadcrumb 模板解析。结果是 `templates` dict 中出现 `my-status` 键，虽然没有 lifecycle hook 写入此 status，但它在模板中占据空间且可能造成混淆。

**修复方案**: 同 Issue 1，在 `patch_inject_workflow_state_hook()` 中对 `load_breadcrumbs()` 函数进行补丁：在 `_TAG_RE.finditer(content)` 之前，先用正则移除 markdown fenced code blocks（` ```...``` `）中的内容，避免示例块被当作真实 breadcrumb 解析。具体做法：在 `load_breadcrumbs()` 的 `content = workflow.read_text(...)` 之后插入一行 `content = re.sub(r"```.*?```", "", content, flags=re.DOTALL)`。

**修复位置**: `docs/workflows/新项目开发工作流/commands/install-workflow.py` — 与 Issue 1 共用 `patch_inject_workflow_state_hook()` 函数。

**证据**: `/tmp/trellis-0.5.16-2/.trellis/workflow.md:658` 代码块内示例 vs `/tmp/trellis-0.5.16-2/.codex/hooks/inject-workflow-state.py:202` `_TAG_RE` 正则。

---

### Issue 8 (中风险): implementation breadcrumb 与 codex inline 模式冲突

**现象**: 强门禁 `[workflow-state:implementation]` 写 "Dispatch `trellis-implement` sub-agent or implement inline (with explicit user override)"，但 `trellis-continue/SKILL.md` 第 131 行写明 `codex.dispatch_mode=inline` 时主会话默认 inline 执行。两者对默认行为的描述不一致：breadcrumb 暗示默认是 dispatch sub-agent（inline 需显式 override），而 trellis-continue 说 inline 是默认。

**修复方案**: 修改 `[workflow-state:implementation]` breadcrumb 文案，增加条件分支：对于 codex.dispatch_mode=inline，默认 inline 执行；对于其他平台或 sub-agent 模式，默认 dispatch sub-agent。这与已有的 `-inline` breadcrumb 后缀机制保持一致。

具体修改：将 implementation breadcrumb 中 "Dispatch `trellis-implement` sub-agent or implement inline (with explicit user override)" 改为 "For sub-agent dispatch mode: dispatch `trellis-implement` sub-agent. For inline dispatch mode: implement directly (load `trellis-before-dev` first)."

**修复位置**: `docs/workflows/新项目开发工作流/commands/workflow-patch-projectization.md` 的 `[workflow-state:implementation]` 区块。

**证据**: `/tmp/trellis-0.5.16-2/.trellis/workflow.md:848` vs `/tmp/trellis-0.5.16-2/.agents/skills/trellis-continue/SKILL.md:131`。

---

### Issue 9 (中风险): no_task A/B/C 没覆盖深度只读审计请求

**现象**: A 类限定一行回答 + 读取 ≤2 文件；B 类是建任务做实现/改代码；C 类是显式 inline escape hatch。深度只读审计（如"分析这个项目的架构问题""审计这个工作流的一致性"）既需要读多文件、写分析报告，又不涉及代码修改，在 A/B/C 中无明确归属。

**修复方案**: 在 no_task A/B 规则之间增加一个 **A+** 类（或扩展 A 类）："深度只读分析" — 允许多文件读取和写入分析文档（如写入 research/ 或临时文件），但不允许修改项目源代码/配置。路由条件：用户请求涉及跨文件分析、审计、诊断，但不要求修改代码。

具体措辞：在 A 和 B 之间插入 `**A+ Deep analysis** — multi-file read-only audit / architecture review / diagnostic report; file writes limited to analysis docs (research/, temp files); no source code / config / project file modification allowed. Creates task only if the user explicitly asks to act on findings.`

**修复位置**: `docs/workflows/新项目开发工作流/commands/workflow-patch-projectization.md` 的 `[workflow-state:no_task]` 区块。

**证据**: `/tmp/trellis-0.5.16-2/.trellis/workflow.md:895-908` no_task A/B/C 定义。

---

## Requirements

1. Issue 1+7: `patch_inject_workflow_state_hook()` 补丁 hook — 优先读 workflow-state.json.stage + 移除代码块中的示例
2. Issue 2: 嵌入时删除旧三阶段 breadcrumb 块（no_task/planning/in_progress/completed 及 -inline 变体）
3. Issue 3: no_task B 规则不引导重复建任务，feasibility skill 内部已创建
4. Issue 4: Phase Index 补丁增加阶段切换命令速查
5. Issue 5: 增加 `[workflow-state:record-session]` breadcrumb 块
6. Issue 6: 嵌入时清理对不存在文件的引用（workflow-state-contract.md）
7. Issue 8: implementation breadcrumb 区分 dispatch/inline 模式
8. Issue 9: no_task 增加 A+ 深度只读分析类别

## Acceptance Criteria

- [ ] 在 `/tmp/trellis-0.5.16-2` 等效的干净目标项目上重新嵌入后，9 个问题全部消失
- [ ] 嵌入后 `inject-workflow-state.py` 正确读取 `workflow-state.json.stage` 且不解析代码块示例- [ ] 嵌入后 `workflow.md` 中每个 status 只有一个 `[workflow-state:STATUS]` 块
- [ ] 嵌入后 `workflow.md` 的 `no_task` B 规则不引导重复建任务
- [ ] 嵌入后 `workflow.md` 包含阶段切换命令速查
- [ ] 嵌入后 `workflow.md` 包含 `[workflow-state:record-session]` 块
- [ ] 嵌入后 `workflow.md` 不引用不存在的 `workflow-state-contract.md`（引用改为 workflow-state.py --help）
- [ ] 嵌入后 `load_breadcrumbs()` 不解析代码块中的示例（已在 Issue 1 补丁中一并处理）
- [ ] 嵌入后 `implementation` breadcrumb 与 codex inline 模式一致
- [ ] 嵌入后 `no_task` 覆盖深度只读审计场景
- [ ] `install-workflow.py --dry-run` 通过且不引入新问题
- [ ] 修改范围仅限 `docs/workflows/新项目开发工作流/` 目录

## Definition of Done

- 所有 Acceptance Criteria 满足
- `install-workflow.py --dry-run` 在 `/tmp/trellis-0.5.16-2` 上通过
- 现有嵌入测试（如有）通过
- 不引入新的一致性问题

## Out of Scope

- 修改 Trellis 基线文件（.trellis/scripts/ 下的脚本不在修改范围内，除非是嵌入器复制模板）
- 修改 workflow-state.py 本身（属于 Trellis 基线）
- 修改 feasibility SKILL.md 本身（属于 skill 基线）
- 修改 trellis-continue SKILL.md 本身（属于 skill 基线）
- 不在 `docs/workflows/新项目开发工作流/` 之外的目录做任何修改

## Technical Notes

### 关键源文件

1. `commands/workflow-patch-projectization.md` — Phase Index / breadcrumb / no_task 补丁模板（Issue 3,4,5,8,9）
2. `commands/install-workflow.py` — 嵌入执行器（Issue 1+7 via hook patch, Issue 2, Issue 6）

### inject-workflow-state.py 来源确认

`inject-workflow-state.py` 由 Trellis 基线 (`trellis init`) 部署到各 CLI hooks 目录，不属于工作流源资产。嵌入器 (`install-workflow.py`) 不复制此文件，只检查它是否存在（见 line 1494-1499）。因此 Issue 1 和 Issue 7 的修复需要通过嵌入器对已部署的 hook 文件进行补丁，而非修改源模板。具体做法：新增 `patch_inject_workflow_state_hook()` 函数，在嵌入流程末尾对 hook 文件做文本替换/插入。

### 嵌入器补丁标记

- `<!-- workflow-projectization-patch -->` — Development Process 区块
- `<!-- workflow-projectization-phase-index-patch -->` — Phase Index 区块
- `<!-- workflow-projectization-breadcrumb-patch -->` — Strong-Gate Breadcrumb 区块
- `<!-- workflow-projectization-no-task-patch -->` — No-Task Entry Point 区块
