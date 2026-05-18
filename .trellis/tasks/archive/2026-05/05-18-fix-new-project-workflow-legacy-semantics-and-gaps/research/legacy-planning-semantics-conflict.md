# Research: Legacy "planning" Status Semantics Conflict in Strong-Gate Workflow

- **Query**: Investigate legacy planning/status semantics in embedded workflow vs strong-gate model, map to source files
- **Scope**: Internal (embedded target + source workflow)
- **Date**: 2026-05-18

## Findings

### Summary of the Conflict

The strong-gate workflow model uses `workflow-state.json.stage` (values: feasibility, brainstorm, design, plan, implementation, test-first, project-audit, check, review-gate, finish-work, delivery, record-session) as the single source of truth for stage routing. However, multiple files across the embedded installation and the source workflow still reference the legacy three-phase model where `task.json.status` values (`planning`, `in_progress`, `completed`) drove routing via `[workflow-state:planning]`, `[workflow-state:in_progress]`, and `[workflow-state:completed]` breadcrumb blocks. These legacy references create a dual-truth conflict: an AI reading these files may route based on `status=planning` instead of using `workflow-state.py route`.

---

### Category 1: Legacy `[workflow-state:planning]` Breadcrumb Block References

These files explicitly reference `[workflow-state:planning]` as a live breadcrumb that would fire after `task.py create`. In the strong-gate model, this block does not exist in the installed `workflow.md` (it was removed by `cleanup_legacy_breadcrumb_blocks`), so any reference to it is describing a dead/unreachable state.

#### Embedded (Installed) Files

| File | Line | Exact Text | Conflict Type |
|---|---|---|---|
| `.agents/skills/trellis-meta/references/customize-local/change-task-lifecycle.md` | 71 | `The task's \`status=planning\` and \`[workflow-state:planning]\` fires on the very next \`UserPromptSubmit\`.` | Claims `[workflow-state:planning]` fires, but strong-gate has no such block |
| `.agents/skills/trellis-meta/references/customize-local/change-task-lifecycle.md` | 72 | `the task directory is still created and \`status=planning\` is still written` | Reinforces `planning` as a meaningful status |
| `.agents/skills/trellis-meta/references/customize-local/change-task-lifecycle.md` | 74 | `This makes \`[workflow-state:planning]\` the live breadcrumb during the brainstorm and JSONL curation work that follows \`task.py create\`.` | Claims `[workflow-state:planning]` is live, contradicts strong-gate |
| `.claude/skills/trellis-meta/references/customize-local/change-task-lifecycle.md` | 71-74 | (Same text as above, duplicated across Claude skill directory) | Same conflict |
| `.opencode/skills/trellis-meta/references/customize-local/change-task-lifecycle.md` | 71-74 | (Same text as above, duplicated across OpenCode skill directory) | Same conflict |

#### Source Files

| File | Line | Exact Text | Notes |
|---|---|---|---|
| `.agents/skills/trellis-meta/references/customize-local/change-task-lifecycle.md` | 71 | `The task's \`status=planning\` and \`[workflow-state:planning]\` fires on the very next \`UserPromptSubmit\`.` | SOURCE: this is the baseline Trellis reference, NOT patched by install |
| `.agents/skills/trellis-meta/references/customize-local/change-task-lifecycle.md` | 72 | `\`status=planning\` is still written` | Same |
| `.agents/skills/trellis-meta/references/customize-local/change-task-lifecycle.md` | 74 | `This makes \`[workflow-state:planning]\` the live breadcrumb...` | Same |

**Key finding**: The `install-workflow.py` function `patch_trellis_meta_references` only patches 4 files (workflow.md, context-injection.md, change-workflow.md, hooks-and-settings.md) from `trellis-meta-strong-gate/`. It does NOT patch `change-task-lifecycle.md`, `task-system.md`, or other reference docs. Therefore, the baseline `change-task-lifecycle.md` is copied verbatim into the target project with its legacy `planning` references intact.

---

### Category 2: Legacy `status=planning` Routing Logic in trellis-continue SKILL.md

#### Embedded (Installed) Files -- PATCHED (conflict resolved)

| File | Line | Exact Text | Conflict Type |
|---|---|---|---|
| `.agents/skills/trellis-continue/SKILL.md` | 16 | `**WARNING: Old status routing is deprecated**: Do not use \`status=planning\` / \`status=in_progress\` for Step 3 routing.` | Patched: deprecation warning present |
| `.agents/skills/trellis-start/SKILL.md` | 71 | `**WARNING: Old status routing is deprecated**: Do not use \`status=planning\` / \`status=in_progress\` for Step 3 routing.` | Patched: deprecation warning present |

The embedded (patched) versions have the Phase Router patch applied, which replaces the old Step 1-4 routing with strong-gate `workflow-state.py route` logic. The backup originals retain the legacy routing.

#### Embedded (Installed) Files -- BACKUP ORIGINALS (conflict preserved)

| File | Line | Exact Text | Conflict Type |
|---|---|---|---|
| `.agents/skills/.backup-original/trellis-continue/SKILL.md` | 32 | `\`status=planning\` + no \`prd.md\` -> **1.1** (load \`trellis-brainstorm\`)` | Legacy routing by status |
| `.agents/skills/.backup-original/trellis-continue/SKILL.md` | 33 | `\`status=planning\` + \`prd.md\` exists + \`implement.jsonl\` not curated...` | Legacy routing by status |
| `.agents/skills/.backup-original/trellis-continue/SKILL.md` | 34 | `\`status=planning\` + \`prd.md\` + curated \`implement.jsonl\` -> **1.4**` | Legacy routing by status |

#### Source Files (BASELINE, unpatched)

| File | Line | Exact Text | Notes |
|---|---|---|---|
| `.agents/skills/trellis-continue/SKILL.md` | 32 | `\`status=planning\` + no \`prd.md\` -> **1.1** (load \`trellis-brainstorm\`)` | SOURCE baseline: routes by status=planning |
| `.agents/skills/trellis-continue/SKILL.md` | 33 | `\`status=planning\` + \`prd.md\` exists + \`implement.jsonl\` not curated...` | Same |
| `.agents/skills/trellis-continue/SKILL.md` | 34 | `\`status=planning\` + \`prd.md\` + curated \`implement.jsonl\` -> **1.4**` | Same |
| `.agents/skills/trellis-start/SKILL.md` | -- | (no planning references in source baseline) | Clean |

**Key finding**: The source baseline `trellis-continue/SKILL.md` contains the legacy `status=planning` routing table. The install workflow patches this in the embedded target, but the source file remains unpatched, meaning any future re-install or the source itself serves as a reference that contradicts the strong-gate model.

---

### Category 3: Legacy `task.json.status = "planning"` in Code (task.py, task_store.py)

#### Embedded (Installed) Files

| File | Line | Exact Text | Conflict Type |
|---|---|---|---|
| `.trellis/scripts/task.py` | 123 | `# Still flip task.json status: planning -> in_progress so downstream phases proceed.` | Comment claims flip is needed; strong-gate patch skips it |
| `.trellis/scripts/task.py` | 127 | `if data and data.get("status") == "planning":` | Checks for `planning` status to flip |
| `.trellis/scripts/task.py` | 133 | `print(colored("OK Status: planning -> in_progress (degraded)", Colors.GREEN))` | Reports legacy flip |
| `.trellis/scripts/task.py` | 145 | `if data and data.get("status") == "planning":` | Same check in non-degraded branch |
| `.trellis/scripts/task.py` | 151 | `print(colored("OK Status: planning -> in_progress", Colors.GREEN))` | Reports legacy flip |
| `.trellis/scripts/task.py` | 368 | `--status, -s <s>     Filter by status (planning, in_progress, review, completed)` | Help text lists `planning` as a valid filter |
| `.trellis/scripts/common/task_store.py` | 212 | `"status": "planning",` | New tasks are created with `status=planning` |
| `.trellis/scripts/common/task_store.py` | 270 | `# Auto-activate the new task so the per-turn breadcrumb fires planning` | Comment references planning breadcrumb |
| `.trellis/scripts/common/task_queue.py` | 83 | `return list_tasks_by_status("planning", repo_root)` | `list_pending_tasks()` queries by `planning` status |
| `.trellis/scripts/add_session.py` | 164 | `commit_table = "(No commits - planning session)"` | UI label uses "planning" |

#### Source Files

| File | Line | Exact Text | Notes |
|---|---|---|---|
| `.trellis/scripts/task.py` | 111 | `# Still flip task.json status: planning -> in_progress so downstream phases proceed.` | SOURCE: baseline unpatched, ALWAYS flips |
| `.trellis/scripts/task.py` | 114 | `if data and data.get("status") == "planning":` | SOURCE: unconditional flip (no strong-gate guard) |
| `.trellis/scripts/task.py` | 117 | `print(colored("OK Status: planning -> in_progress (degraded)", Colors.GREEN))` | Same |
| `.trellis/scripts/task.py` | 128 | `if data and data.get("status") == "planning":` | SOURCE: unconditional flip (no strong-gate guard) |
| `.trellis/scripts/task.py` | 131 | `print(colored("OK Status: planning -> in_progress", Colors.GREEN))` | Same |
| `.trellis/scripts/task.py` | 330 | `--status, -s <s>     Filter by status (planning, in_progress, review, completed)` | Same |
| `.trellis/scripts/common/task_store.py` | 212 | `"status": "planning",` | SOURCE: same |
| `.trellis/scripts/common/task_store.py` | 270 | `# Auto-activate the new task so the per-turn breadcrumb fires planning` | SOURCE: same |
| `.trellis/scripts/common/task_queue.py` | 83 | `return list_tasks_by_status("planning", repo_root)` | SOURCE: same |
| `.trellis/scripts/add_session.py` | 164 | `commit_table = "(No commits - planning session)"` | SOURCE: same |

**Key finding**: The source baseline `task.py` ALWAYS flips `planning -> in_progress` on `task.py start`. The install workflow applies `patch-task-start-strong-gate.py` to add a guard that skips the flip when `workflow-state.json` exists. However, the source file itself still has the unconditional flip. The `task_store.py` still creates tasks with `status=planning`, and `task_queue.py` still queries by `planning` status. These are not patched at all.

---

### Category 4: Legacy `planning` References in trellis-meta Reference Docs (NOT patched by install)

The `install-workflow.py` function `patch_trellis_meta_references` only copies 4 strong-gate replacement files from `trellis-meta-strong-gate/`. The following reference files are NOT patched and retain legacy `planning` semantics:

#### Embedded + Source (identical, not patched)

| File | Line | Exact Text | Conflict Type |
|---|---|---|---|
| `.agents/skills/trellis-meta/references/local-architecture/task-system.md` | 36 | `\| \`status\` \| Status such as \`planning\`, \`in_progress\`, \`review\`, or \`completed\`.\|` | Lists `planning` as a primary status |
| `.agents/skills/trellis-meta/references/local-architecture/context-injection.md` | 29 | `...it selects a block from \`.trellis/workflow.md\`, such as \`no_task\`, \`planning\`, \`in_progress\`, or \`completed\`.` | Lists `planning` as a valid workflow-state block (embedded version patched to use stage-based) |
| `.agents/skills/trellis-meta/references/customize-local/change-workflow.md` | 17 | `\| Change the next step during planning \| Phase 1 and \`[workflow-state:planning]\`.\|` | References `[workflow-state:planning]` block (embedded version patched to use stage) |
| `.agents/skills/trellis-meta/references/customize-local/change-workflow.md` | 52-54 | Route table rows with `planning` status | Embedded version patched to use action-based routing |
| `.agents/skills/trellis-meta/references/local-architecture/workspace-memory.md` | 46 | `Planning or review work without a commit can also be recorded...` | Benign: uses "planning" in natural language, not as status |
| `.agents/skills/record-session/SKILL.md` | 36 | `Don't skip archiving just because \`status\` still says \`planning\` or \`in_progress\`` | Acknowledges `planning` as a status that may not reflect reality |

---

### Category 5: Backup Original workflow.md (Preserved Legacy Blocks)

| File | Line | Exact Text | Conflict Type |
|---|---|---|---|
| `.trellis/.backup-original/workflow.md` | 76 | `...auto-sets the per-session active-task pointer so the planning breadcrumb fires immediately. \`task.py start\` writes...and flips \`task.json.status\` from \`planning\` to \`in_progress\`.` | Baseline 3-phase description |
| `.trellis/.backup-original/workflow.md` | 122 | `[workflow-state:planning] -> all of Phase 1 (status='planning')` | Legacy tag-to-phase mapping |
| `.trellis/.backup-original/workflow.md` | 154 | `...(1) \`task.py create\` to create the task (status=planning, breadcrumb switches to [workflow-state:planning]...` | Legacy no_task entry flow |
| `.trellis/.backup-original/workflow.md` | 159 | `1.0 Create task [required . once] (just task.py create; status enters planning)` | Legacy Phase 1 step |
| `.trellis/.backup-original/workflow.md` | 168-172 | Full `[workflow-state:planning]...[/workflow-state:planning]` block | Legacy breadcrumb block |
| `.trellis/.backup-original/workflow.md` | 180-184 | Full `[workflow-state:planning-inline]...[/workflow-state:planning-inline]` block | Legacy breadcrumb block (codex inline variant) |
| `.trellis/.backup-original/workflow.md` | 315 | `Create the task directory (status enters \`planning\`...` | Legacy Phase 1 step description |
| `.trellis/.backup-original/workflow.md` | 323 | `...the per-turn breadcrumb auto-switches to \`[workflow-state:planning]\`` | Legacy breadcrumb switch claim |
| `.trellis/.backup-original/workflow.md` | 645 | `All of Phase 1 (task created -> ready for implementation) \| \`[workflow-state:planning]\`` | Legacy route table |

Note: The backup original is preserved for rollback purposes. It is not active in routing, but if an AI reads it, the legacy semantics could cause confusion.

---

### Category 6: install-workflow.py Source -- Legacy String Constants

| File | Line | Exact Text | Notes |
|---|---|---|---|
| `docs/workflows/.../commands/install-workflow.py` | 190-202 | `_BASELINE_WORKFLOW_TASK_MECHANISM` constant | Describes baseline `planning -> in_progress` flip |
| `docs/workflows/.../commands/install-workflow.py` | 204-222 | `_STRONG_GATE_WORKFLOW_TASK_MECHANISM` constant | Describes patched behavior that skips flip; mentions `planning` in context of explaining the legacy |
| `docs/workflows/.../commands/install-workflow.py` | 956 | `status=planning/in_progress routing` | Comment in `build_codex_phase_router_skill_content` |
| `docs/workflows/.../commands/install-workflow.py` | 1790-1791 | `"planning", "planning-inline",` | `_LEGACY_BREADCRUMB_TAGS` list for cleanup |
| `docs/workflows/.../commands/install-workflow.py` | 1876 | `"[workflow-state:planning]"` | Signal for legacy section detection |
| `docs/workflows/.../commands/install-workflow.py` | 2002 | `anchor = '        # Still flip task.json status: planning -> in_progress...'` | Anchor for degraded patch |

These are intentionally present in the installer -- they describe what the installer transforms. They are not a conflict in the target project but document the migration path.

---

### Category 7: patch-task-start-strong-gate.py Source

| File | Line | Exact Text | Notes |
|---|---|---|---|
| `docs/workflows/.../commands/shell/patch-task-start-strong-gate.py` | 6 | `NOT flip task.json status from planning -> in_progress.` | Patch description |
| `docs/workflows/.../commands/shell/patch-task-start-strong-gate.py` | 36 | `r'(?P<indent>\s*)if (?P<var>...) and (?P=var)\.get\("status"\) == "planning":\n'` | Regex pattern to find and patch |

This is the installer patch tool itself, not a conflict in the target.

---

## Mapping: Source to Embedded (Install Flow)

| Embedded Target File | Source File / Install Mechanism | Patched? |
|---|---|---|
| `.trellis/workflow.md` | Baseline Trellis `workflow.md` + install-workflow.py patches | YES: Phase Index, breadcrumb blocks, no_task block all replaced |
| `.trellis/scripts/task.py` | Baseline Trellis `task.py` + `patch-task-start-strong-gate.py` | PARTIAL: strong-gate no-flip guard added, but `planning` status still set on create, still referenced in help text |
| `.trellis/scripts/common/task_store.py` | Baseline Trellis `task_store.py` | NO: `status=planning` on create, `fires planning` comment unchanged |
| `.trellis/scripts/common/task_queue.py` | Baseline Trellis `task_queue.py` | NO: `list_tasks_by_status("planning")` unchanged |
| `.agents/skills/trellis-start/SKILL.md` | Baseline Trellis `trellis-start/SKILL.md` + Phase Router patch | YES: Phase Router appended |
| `.agents/skills/trellis-continue/SKILL.md` | Baseline Trellis `trellis-continue/SKILL.md` + Phase Router patch | YES: Steps 1-4 replaced with Phase Router |
| `.agents/skills/trellis-meta/references/local-architecture/workflow.md` | `trellis-meta-strong-gate/local-architecture/workflow.md` | YES: strong-gate version installed |
| `.agents/skills/trellis-meta/references/local-architecture/context-injection.md` | `trellis-meta-strong-gate/local-architecture/context-injection.md` | YES: strong-gate version installed |
| `.agents/skills/trellis-meta/references/customize-local/change-workflow.md` | `trellis-meta-strong-gate/customize-local/change-workflow.md` | YES: strong-gate version installed |
| `.agents/skills/trellis-meta/references/platform-files/hooks-and-settings.md` | `trellis-meta-strong-gate/platform-files/hooks-and-settings.md` | YES: strong-gate version installed |
| `.agents/skills/trellis-meta/references/customize-local/change-task-lifecycle.md` | Baseline Trellis reference (NOT patched) | NO: still references `[workflow-state:planning]` as live breadcrumb |
| `.agents/skills/trellis-meta/references/local-architecture/task-system.md` | Baseline Trellis reference (NOT patched) | NO: still lists `planning` as primary status |
| `.agents/skills/trellis-meta/references/local-architecture/workspace-memory.md` | Baseline Trellis reference (NOT patched) | NO (benign: natural language use) |
| `.agents/skills/record-session/SKILL.md` | Baseline Trellis skill (NOT patched) | NO: references `planning` as status that may lag reality |

## Caveats / Not Found

1. **No `[workflow-state:planning]` block exists in the installed `.trellis/workflow.md`** -- it was correctly removed by `cleanup_legacy_breadcrumb_blocks`. The conflict is that reference docs and code still mention it as if it exists.

2. **`task_store.py` status=planning is architectural, not just legacy text** -- new tasks are genuinely created with `status=planning` in `task.json`. This field persists even in strong-gate installs. The patch only prevents `task.py start` from flipping it to `in_progress` when `workflow-state.json` exists. The field itself is not removed; it remains as a "legacy lifecycle field for task bookkeeping only" (as the strong-gate workflow.md states). Whether `task_store.py` should set a different initial status (or whether the field should be kept as-is but documented as non-authoritative) is a design decision beyond research scope.

3. **`task_queue.py:list_pending_tasks()` queries by `planning` status** -- this function is used by `task.py list --status planning`. In strong-gate, tasks may stay in `status=planning` forever (since the flip is skipped), so this query may actually return all non-archived tasks that were never started via the legacy path. This is potentially a functional issue, not just a semantic one.

4. **The `trellis-spec-bootstarp` reference to "task planning"** (line 23 of its SKILL.md) is benign -- it refers to planning as a general activity ("decomposition and task planning"), not as the `status=planning` workflow state.

5. **`add_session.py` line 164** ("planning session") is a UI label for sessions without commits, not a workflow status reference. Low conflict risk.
