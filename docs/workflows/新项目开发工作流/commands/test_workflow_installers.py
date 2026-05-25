from __future__ import annotations

import argparse
import contextlib
import importlib.util
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from workflow_assets import HELPER_SCRIPTS, build_managed_audit_extra_specs


REPO_ROOT = Path(__file__).resolve().parents[4]
PYTHON = (
    "/ops/softwares/python/bin/python3"
    if Path("/ops/softwares/python/bin/python3").exists()
    else shutil.which("python3") or shutil.which("python")
)
COMMANDS_DIR = REPO_ROOT / "docs" / "workflows" / "新项目开发工作流" / "commands"
INSTALL_SCRIPT = COMMANDS_DIR / "install-workflow.py"
DETECT_EMBED_STATE_SCRIPT = COMMANDS_DIR / "detect-embed-state.py"
UPGRADE_SCRIPT = COMMANDS_DIR / "upgrade-compat.py"
UNINSTALL_SCRIPT = COMMANDS_DIR / "uninstall-workflow.py"
PATCH_TASK_CREATE_SCRIPT = COMMANDS_DIR / "shell" / "patch-task-create-preserve-active.py"
PATCH_WORKFLOW_PHASE_SCRIPT = COMMANDS_DIR / "shell" / "patch-workflow-phase.py"
PATCH_WORKFLOW_PHASE_STRONG_GATE_SCRIPT = COMMANDS_DIR / "shell" / "patch-workflow-phase-strong-gate.py"
PATCH_TASK_STATUS_VIEW_STRONG_GATE_SCRIPT = COMMANDS_DIR / "shell" / "patch-task-status-view-strong-gate.py"
TRELLIS_LIBRARY_CLI = (REPO_ROOT / "trellis-library" / "cli.py").as_posix()
TRELLIS_LIBRARY_DIR = (REPO_ROOT / "trellis-library").as_posix()
EMBED_CONFIRM_ENV = "WORKFLOW_EMBED_EXECUTOR_CONFIRMED"
ATTEMPT_RECORD_NAME = "workflow-embed-attempt.json"
PHASE_ROUTER_MARKER = "## Phase Router `[AI]`"
FINISH_WORK_MARKER = "<!-- finish-work-projectization-patch -->"
PARALLEL_DISABLED_MARKER = "<!-- workflow-parallel-disabled -->"
WORKFLOW_PATCH_MARKER = "<!-- workflow-projectization-patch -->"
TRELLIS_META_PATCH_MARKER = "<!-- workflow-embed-patch:trellis-meta-strong-gate -->"
OPENCODE_SESSION_UTILS_PATCH_MARKER = "// [workflow-embed-patch:strong-gate-session-utils]"
SESSION_START_STRONG_GATE_PATCH_MARKER = "# strong-gate-session-start-patch-applied"
TASK_NO_STATUS_FLIP_PATCH_MARKER = "# [workflow-embed-patch:strong-gate-no-status-flip]"
TASK_CREATE_PRESERVE_ACTIVE_PATCH_MARKER = "# [workflow-embed-patch:preserve-parent-active-task]"
LEGACY_READY_AUTOCONTINUE_LINE = "If a task is READY, execute its Next required action without asking whether to continue."
STRONG_GATE_READY_GUIDANCE_LINE = "Treat `workflow-state.py route` / <task-status> as the only authority for the next action."
DEFAULT_PROJECT_TODO = "文档内容需要和实际当前的代码同步\n"
BASELINE_START_CONTENT = (
    "# /trellis:start\n\n"
    "Original baseline start command for fixture testing.\n\n"
    "## Operation Types\n\n"
    "| Marker | Meaning |\n"
    "|--------|---------|\n"
    "| `[AI]` | tool calls |\n"
    "| `[USER]` | user actions |\n"
)
BASELINE_CONTINUE_CONTENT = (
    "# Continue Current Task\n\n"
    "Original baseline continue command for fixture testing.\n"
)
BASELINE_RECORD_SESSION_CONTENT = (
    "# /trellis:record-session\n\n"
    "## Record Work Progress\n\n"
    "### Step 1: Get Context & Check Tasks\n\n"
    "```bash\n"
    "python3 ./.trellis/scripts/get_context.py --mode record\n"
    "```\n\n"
    "### Step 2: One-Click Add Session\n\n"
    "```bash\n"
    "python3 ./.trellis/scripts/add_session.py --title \"Title\" --commit \"hash\"\n"
    "```\n"
)
BASELINE_OPENCODE_RECORD_SESSION_CONTENT = (
    "# /trellis:record-session\n\n"
    "### Step 2: One-Click Add Session\n\n"
    "```bash\n"
    "python3 ./.trellis/scripts/add_session.py --title \"Title\" --commit \"hash\"\n"
    "```\n"
)
BASELINE_CHECK_CONTENT = (
    "# /trellis:check\n\n"
    "Check if the code you just wrote follows the development guidelines.\n\n"
    "1. Identify changed files.\n"
)
BASELINE_BRAINSTORM_CONTENT = (
    "# /trellis:brainstorm\n\n"
    "Clarify requirements before implementation.\n"
)
BASELINE_PARALLEL_CONTENT = (
    "# /trellis:parallel\n\n"
    "Run a worktree-based parallel pipeline and finish with a PR.\n"
)
BASELINE_START_SKILL_CONTENT = (
    "---\n"
    "name: trellis-start\n"
    "description: Baseline start skill\n"
    "---\n\n"
    "# Start Session\n\n"
    "## Step 1: Current state\n\n"
    "```bash\n"
    "python3 ./.trellis/scripts/get_context.py\n"
    "```\n\n"
    "## Step 2: Workflow overview\n\n"
    "```bash\n"
    "python3 ./.trellis/scripts/get_context.py --mode phase\n"
    "```\n\n"
    "## Step 3: Guideline indexes\n\n"
    "```bash\n"
    "python3 ./.trellis/scripts/get_context.py --mode packages\n"
    "```\n\n"
    "## Step 4: Decide next action\n\n"
    "```bash\n"
    "python3 ./.trellis/scripts/get_context.py --mode phase --step 2.1 --platform codex\n"
    "```\n"
)
BASELINE_FINISH_WORK_CONTENT = (
    "# Finish Work - Pre-Commit Checklist\n\n"
    "Before submitting or committing, use this checklist to ensure work completeness.\n\n"
    "**Timing**: After code is written and tested, before commit\n\n"
    "---\n\n"
    "## Checklist\n\n"
    "### 1. Code Quality\n\n"
    "```bash\n"
    "# Must pass\n"
    "pnpm lint\n"
    "pnpm type-check\n"
    "pnpm test\n"
    "```\n\n"
    "- [ ] `pnpm lint` passes with 0 errors?\n"
    "- [ ] `pnpm type-check` passes with no type errors?\n"
    "- [ ] Tests pass?\n\n"
    "### 1.5. Test Coverage\n\n"
    "Check if your change needs new or updated tests.\n"
)
BASELINE_FINISH_WORK_WITHOUT_TEST_COVERAGE_CONTENT = (
    "# Finish Work - Pre-Commit Checklist\n\n"
    "Before submitting or committing, use this checklist to ensure work completeness.\n\n"
    "**Timing**: After code is written and tested, before commit\n\n"
    "---\n\n"
    "## Checklist\n\n"
    "### 1. Code Quality\n\n"
    "```bash\n"
    "# Must pass\n"
    "pnpm lint\n"
    "pnpm type-check\n"
    "pnpm test\n"
    "```\n\n"
    "- [ ] `pnpm lint` passes with 0 errors?\n"
    "- [ ] `pnpm type-check` passes with no type errors?\n"
    "- [ ] Tests pass?\n\n"
    "### 2. Code-Spec Sync\n\n"
    "Check code-spec updates.\n"
)
BASELINE_WORKFLOW_CONTENT = (
    "### Task System\n\n"
    "**Current-task mechanism**: `task.py create` creates the task directory and "
    "(when session identity is available) auto-sets the per-session active-task "
    "pointer so the planning breadcrumb fires immediately. `task.py start` writes "
    "the same pointer (idempotent if already set) and flips `task.json.status` "
    "from `planning` to `in_progress`. State is stored under "
    "`.trellis/.runtime/sessions/`. If no context key is available from hook "
    "input, `TRELLIS_CONTEXT_ID`, or a platform-native session environment "
    "variable, there is no active task and `task.py start` fails with a session "
    "identity hint. `task.py finish` deletes the current session file (status "
    "unchanged). `task.py archive <task>` writes `status=completed`, moves the "
    "directory to `archive/`, and deletes any runtime session files that still "
    "point at the archived task.\n\n"
    "## Development Process\n\n"
    "### Task Development Flow\n\n"
    "```\n"
    "1. Create or select task\n"
    "2. Start task\n"
    "3. Write code\n"
    "4. Self-test\n"
    "5. Commit code\n"
    "6. Record session\n"
    "7. Finish task\n"
    "```\n\n"
    "## Session End\n\n"
    "### One-Click Session Recording\n\n"
    "Use add_session.py directly.\n\n"
    "## File Descriptions\n\n"
    "### 1. workspace/ - Developer Workspaces\n"
)
LATEST_BASELINE_WORKFLOW_CONTENT = (
    "# Development Workflow\n\n"
    "---\n\n"
    "## Trellis System\n\n"
    "### Task System\n\n"
    "**Current-task mechanism**: `task.py create` creates the task directory and "
    "(when session identity is available) auto-sets the per-session active-task "
    "pointer so the planning breadcrumb fires immediately. `task.py start` writes "
    "the same pointer (idempotent if already set) and flips `task.json.status` "
    "from `planning` to `in_progress`. State is stored under "
    "`.trellis/.runtime/sessions/`. If no context key is available from hook "
    "input, `TRELLIS_CONTEXT_ID`, or a platform-native session environment "
    "variable, there is no active task and `task.py start` fails with a session "
    "identity hint. `task.py finish` deletes the current session file (status "
    "unchanged). `task.py archive <task>` writes `status=completed`, moves the "
    "directory to `archive/`, and deletes any runtime session files that still "
    "point at the archived task.\n\n"
    "### Workspace System\n\n"
    "Records every AI session.\n\n"
    "### Context Script\n\n"
    "```bash\n"
    "python3 ./.trellis/scripts/get_context.py --mode phase --step <X.Y>\n"
    "```\n\n"
    "---\n"
)
LEGACY_PHASE_WORKFLOW_CONTENT = (
    "## Context Script\n\n"
    "```bash\n"
    "python3 ./.trellis/scripts/get_context.py --mode phase --step <X.Y>\n"
    "```\n\n"
    "<!--\n"
    "  WORKFLOW-STATE BREADCRUMB CONTRACT (read this before editing the tag blocks below)\n"
    "-->\n\n"
    "## Phase Index\n\n"
    "```\n"
    "Phase 1: Plan    → figure out what to do (brainstorm + research → prd.md)\n"
    "Phase 2: Execute → write code and pass quality checks\n"
    "Phase 3: Finish  → distill lessons + wrap-up\n"
    "```\n\n"
    "[workflow-state:planning]\nold planning block\n[/workflow-state:planning]\n\n"
    "## Customizing Trellis (for forks)\n\n"
    "Legacy customization notes.\n"
)
BASELINE_TASK_PY_CONTENT = (
    "from common.log import Colors, colored\n"
    "from common.io import read_json, write_json\n\n"
    "def cmd_start(args):\n"
    "    repo_root = get_repo_root()\n"
    "    full_path = repo_root / '.trellis' / 'tasks' / 'sample'\n"
    "    task_dir = full_path.relative_to(repo_root).as_posix()\n"
    "    task_json_path = full_path / FILE_TASK_JSON\n"
    "    if not resolve_context_key():\n"
    "        # Still flip task.json status: planning → in_progress so downstream phases proceed.\n"
    "        if task_json_path.is_file():\n"
    "            data = read_json(task_json_path)\n"
    "            if data and data.get(\"status\") == \"planning\":\n"
    "                data[\"status\"] = \"in_progress\"\n"
    "                if write_json(task_json_path, data):\n"
    "                    print(colored(\"✓ Status: planning → in_progress (degraded)\", Colors.GREEN))\n"
    "        return 0\n"
    "    active = set_active_task(task_dir, repo_root)\n"
    "    if active:\n"
    "        if task_json_path.is_file():\n"
    "            data = read_json(task_json_path)\n"
    "            if data and data.get(\"status\") == \"planning\":\n"
    "                data[\"status\"] = \"in_progress\"\n"
    "                if write_json(task_json_path, data):\n"
    "                    print(colored(\"✓ Status: planning → in_progress\", Colors.GREEN))\n"
    "        return 0\n"
    "    return 0\n\n"
    "def cmd_finish(args):\n"
    "    repo_root = get_repo_root()\n"
    "    current = active.task_path\n"
    "    task_json_path = repo_root / current / FILE_TASK_JSON\n"
    "    if task_json_path.is_file():\n"
    "        run_task_hooks(\"after_finish\", task_json_path, repo_root)\n"
    "    return 0\n\n"
    "def cmd_current(args):\n"
    "    repo_root = get_repo_root()\n"
    "    active = resolve_active_task(repo_root)\n"
    "    if args.source:\n"
    "        print(f\"Current task: {active.task_path or '(none)'}\")\n"
    "        print(f\"Source: {active.source}\")\n"
    "        if active.stale:\n"
    "            print(\"State: stale\")\n"
    "        return 0 if active.task_path else 1\n\n"
    "    if active.task_path:\n"
    "        print(active.task_path)\n"
    "        return 0\n\n"
    "    return 1\n\n"
    "def show_usage():\n"
    "    print(\"  python3 task.py start <dir>                        Set active task\\n\")\n\n"
    "def build_parser():\n"
    "    p_start = subparsers.add_parser(\"start\", help=\"Set active task\")\n"
)
BASELINE_TASK_STORE_CONTENT = (
    "import sys\n"
    "from common.log import Colors, colored\n"
    "from common.io import read_json, write_json\n\n"
    "def cmd_create(args):\n"
    "    repo_root = get_repo_root()\n"
    "    task_dir = repo_root / '.trellis' / 'tasks' / 'sample'\n"
    "    dir_name = task_dir.name\n"
    "    # Auto-activate the new task so the per-turn breadcrumb fires planning\n"
    "    try:\n"
    "        from .active_task import resolve_context_key, set_active_task\n"
    "        if resolve_context_key():\n"
    "            try:\n"
    "                rel_dir = task_dir.relative_to(repo_root).as_posix()\n"
    "            except ValueError:\n"
    "                rel_dir = str(task_dir)\n"
    "            set_active_task(rel_dir, repo_root)\n"
    "    except Exception:\n"
    "        pass\n"
    "    print(colored(f'Created task: {dir_name}', Colors.GREEN))\n"
    "    return 0\n\n"
    "def cmd_archive(args):\n"
    "    repo_root = get_repo_root()\n"
    "    task_dir = repo_root / '.trellis' / 'tasks' / 'sample'\n"
    "    dir_name = task_dir.name\n"
    "    task_json_path = task_dir / FILE_TASK_JSON\n"
    "    if task_json_path.is_file():\n"
    "        data = read_json(task_json_path)\n"
    "        if data:\n"
    "            data['status'] = 'completed'\n"
    "            write_json(task_json_path, data)\n"
    "    return 0\n"
)
BASELINE_COMMON_TASKS_CONTENT = (
    "from collections.abc import Iterator\n"
    "from pathlib import Path\n\n"
    "from .io import read_json\n"
    "from .paths import FILE_TASK_JSON\n"
    "from .types import TaskInfo\n\n"
    "def load_task(task_dir: Path) -> TaskInfo | None:\n"
    "    task_json = task_dir / FILE_TASK_JSON\n"
    "    if not task_json.is_file():\n"
    "        return None\n"
    "    data = read_json(task_json)\n"
    "    if not data:\n"
    "        return None\n"
    "    return TaskInfo(\n"
    "        dir_name=task_dir.name,\n"
    "        directory=task_dir,\n"
    "        title=data.get(\"title\") or data.get(\"name\") or \"unknown\",\n"
    "        status=data.get(\"status\", \"unknown\"),\n"
    "        assignee=data.get(\"assignee\", \"\"),\n"
    "        priority=data.get(\"priority\", \"P2\"),\n"
    "        children=tuple(data.get(\"children\", [])),\n"
    "        parent=data.get(\"parent\"),\n"
    "        package=data.get(\"package\"),\n"
    "        raw=data,\n"
    "    )\n\n"
    "def iter_active_tasks(tasks_dir: Path) -> Iterator[TaskInfo]:\n"
    "    return iter(())\n\n"
    "def get_all_statuses(tasks_dir: Path) -> dict[str, str]:\n"
    "    return {t.dir_name: t.status for t in iter_active_tasks(tasks_dir)}\n\n"
    "def children_progress(children, all_statuses) -> str:\n"
    "    return \"\"\n"
)
BASELINE_TASK_QUEUE_CONTENT = (
    "from .tasks import iter_active_tasks\n\n"
    "def list_tasks_by_status(filter_status=None, repo_root=None):\n"
    "    return []\n\n"
    "def list_pending_tasks(repo_root=None):\n"
    "    return list_tasks_by_status(\"planning\", repo_root)\n"
)
BASELINE_WORKFLOW_PHASE_CONTENT = (
    "def get_step(step):\n"
    "    \"\"\"Return the legacy step body.\"\"\"\n"
    "    return f'legacy step {step}'\n"
)
BASELINE_INJECT_WORKFLOW_STATE_HOOK_CONTENT = (
    "import re\n"
    "from pathlib import Path\n\n"
    "def load_breadcrumbs(workflow: Path):\n"
    "    if workflow:\n"
    "        content = workflow.read_text(encoding=\"utf-8\")\n"
    "        return _TAG_RE.finditer(content)\n"
    "    return []\n\n"
    "def get_active_task(root: Path, input_data: dict):\n"
    "    task_id = input_data['active'].task_path\n"
    "    task_dir = root / task_id\n"
    "    data = {\"status\": \"planning\"}\n"
    "    status = data.get(\"status\", \"\")\n"
    "    active = input_data['active']\n"
    "    return task_id, status, active.source\n"
)
BASELINE_SESSION_START_CONTENT = (
    "from pathlib import Path\n"
    "import json\n\n"
    "def _resolve_active_task(trellis_dir: Path, hook_input: dict):\n"
    "    return hook_input['active']\n\n"
    "def _resolve_task_dir(trellis_dir: Path, task_ref: str) -> Path:\n"
    "    return trellis_dir / 'tasks' / task_ref\n\n"
    "def _get_task_status(trellis_dir: Path, hook_input: dict) -> str:\n"
    "    active = _resolve_active_task(trellis_dir, hook_input)\n"
    "    if not active.task_path:\n"
    "        return 'Status: NO ACTIVE TASK\\nSource: none\\nNext-Action: After the user describes their intent, load skill `trellis-brainstorm` to clarify requirements and create a task via `python3 ./.trellis/scripts/task.py create`.\\n'\n"
    "    task_ref = active.task_path\n"
    "    task_dir = _resolve_task_dir(trellis_dir, task_ref)\n"
    "    if active.stale or not task_dir.is_dir():\n"
    "        return 'Status: STALE POINTER'\n"
    "    task_json_path = task_dir / 'task.json'\n"
    "    task_data = {}\n"
    "    if task_json_path.is_file():\n"
    "        task_data = json.loads(task_json_path.read_text(encoding='utf-8'))\n"
    "    task_title = task_data.get('title', task_ref)\n"
    "    task_status = task_data.get('status', 'unknown')\n"
    "    if task_status == 'completed':\n"
    "        return f'Status: COMPLETED\\nTask: {task_title}'\n"
    "    return f'Status: READY\\nTask: {task_title}'\n"
)
BASELINE_OPENCODE_SESSION_UTILS_CONTENT = (
    "import { existsSync, readFileSync } from \"fs\"\n"
    "import { basename, join } from \"path\"\n"
    "import { execFileSync } from \"child_process\"\n"
    "const PYTHON_CMD = process.env.TRELLIS_PYTHON || \"python3\"\n\n"
    "function hasCuratedJsonlEntry(jsonlPath) {\n"
    "  return existsSync(jsonlPath)\n"
    "}\n\n"
    "function getTaskStatus(ctx, platformInput = null) {\n"
    "  const active = ctx.getActiveTask(platformInput)\n"
    "  const taskRef = active.taskPath\n"
    "  if (!taskRef) {\n"
    "    return `Status: NO ACTIVE TASK\\nSource: ${active.source}\\nNext: Describe what you want to work on`\n"
    "  }\n\n"
    "  const taskDir = ctx.resolveTaskDir(taskRef)\n\n"
    "  if (active.stale || !taskDir || !existsSync(taskDir)) {\n"
    "    return `Status: STALE POINTER\\nTask: ${taskRef}\\nSource: ${active.source}\\nNext: Task directory not found. Run: python3 ./.trellis/scripts/task.py finish`\n"
    "  }\n\n"
    "  let taskData = {}\n"
    "  const taskJsonPath = join(taskDir, \"task.json\")\n"
    "  if (existsSync(taskJsonPath)) {\n"
    "    try {\n"
    "      taskData = JSON.parse(readFileSync(taskJsonPath, \"utf-8\"))\n"
    "    } catch {\n"
    "      // Ignore parse errors\n"
    "    }\n"
    "  }\n\n"
    "  const taskTitle = taskData.title || taskRef\n"
    "  const taskStatus = taskData.status || \"unknown\"\n\n"
    "  if (taskStatus === \"completed\") {\n"
    "    const dirName = basename(taskDir)\n"
    "    return `Status: COMPLETED\\nTask: ${taskTitle}\\nSource: ${active.source}\\nNext: Archive with \\`python3 ./.trellis/scripts/task.py archive ${dirName}\\` or start a new task`\n"
    "  }\n\n"
    "  let hasContext = false\n"
    "  for (const jsonlName of [\"implement.jsonl\", \"check.jsonl\"]) {\n"
    "    const jsonlPath = join(taskDir, jsonlName)\n"
    "    if (existsSync(jsonlPath) && hasCuratedJsonlEntry(jsonlPath)) {\n"
    "      hasContext = true\n"
    "      break\n"
    "    }\n"
    "  }\n\n"
    "  const hasPrd = existsSync(join(taskDir, \"prd.md\"))\n\n"
    "  if (!hasPrd) {\n"
    "    return `Status: NOT READY\\nTask: ${taskTitle}\\nSource: ${active.source}\\nMissing: prd.md not created\\nNext: Write PRD (see workflow.md Phase 1.1) then curate implement.jsonl per Phase 1.3`\n"
    "  }\n\n"
    "  if (!hasContext) {\n"
    "    return `Status: NOT READY\\nTask: ${taskTitle}\\nSource: ${active.source}\\nMissing: implement.jsonl / check.jsonl missing or empty\\nNext: Curate entries per workflow.md Phase 1.3 (spec + research files only), then \\`task.py start\\``\n"
    "  }\n\n"
    "  return (\n"
    "    `Status: READY\\nTask: ${taskTitle}\\n` +\n"
    "    `Source: ${active.source}\\n` +\n"
    "    \"Next required action: dispatch `trellis-implement` per Phase 2.1. \" +\n"
    "    \"For agent-capable platforms, the default is to NOT edit code in the main session. \" +\n"
    "    \"After implementation, dispatch `trellis-check` per Phase 2.2 before reporting completion.\\n\" +\n"
    "    \"User override (per-turn escape hatch): if the user's CURRENT message explicitly tells the \" +\n"
    "    \"main session to handle it directly (\\\"你直接改\\\" / \\\"别派 sub-agent\\\" / \\\"main session 写就行\\\" / \" +\n"
    "    \"\\\"do it inline\\\" / \\\"不用 sub-agent\\\"), honor it for this turn and edit code directly. \" +\n"
    "    \"Per-turn only; do NOT invent an override the user did not say.\"\n"
    "  )\n"
    "}\n"
    "\n"
    "function loadTrellisConfig() {\n"
    "  return null\n"
    "}\n"
    "\n"
    "export function buildSessionContext(ctx, platformInput = null) {\n"
    "  const workflowContent = ctx.readProjectFile(\".trellis/workflow.md\")\n"
    "  if (!workflowContent) return \"\"\n"
    "  const allLines = workflowContent.split(\"\\n\")\n"
    "  const overviewLines = []\n"
    "  let rangeStart = -1\n"
    "  let rangeEnd = allLines.length\n"
    "  for (let i = 0; i < allLines.length; i++) {\n"
    "    const stripped = allLines[i].trim()\n"
    "    if (rangeStart === -1 && stripped === \"## Phase Index\") {\n"
    "      rangeStart = i\n"
    "    } else if (rangeStart !== -1 && stripped === \"## Workflow State Breadcrumbs\") {\n"
    "      rangeEnd = i\n"
    "      break\n"
    "    }\n"
    "  }\n"
    "  if (rangeStart !== -1) {\n"
    "    overviewLines.push(...allLines.slice(rangeStart, rangeEnd))\n"
    "  }\n"
    "  return overviewLines.join(\"\\n\")\n"
    "}\n"
)
BASELINE_OPENCODE_SESSION_START_PLUGIN = (
    "import { buildSessionContext } from \"../lib/session-utils.js\"\n"
    "export default async () => ({\"chat.message\": async () => buildSessionContext})\n"
)
BASELINE_OPENCODE_INJECT_WORKFLOW_STATE_PLUGIN = (
    "/* global process */\n"
    "import { existsSync, readFileSync } from \"fs\"\n"
    "import { join } from \"path\"\n"
    "import { TrellisContext } from \"../lib/trellis-context.js\"\n\n"
    "function getActiveTask(ctx, platformInput = null) {\n"
    "  const active = ctx.getActiveTask(platformInput)\n"
    "  const taskRef = active.taskPath\n"
    "  if (!taskRef) return null\n"
    "  const taskDir = ctx.resolveTaskDir(taskRef)\n"
    "  if (active.stale || !taskDir || !existsSync(taskDir)) {\n"
    "    return { id: taskRef.split(\"/\").pop(), status: \"stale\", source: active.source }\n"
    "  }\n"
    "  const taskJsonPath = join(taskDir, \"task.json\")\n"
    "  if (!existsSync(taskJsonPath)) return null\n"
    "  const data = JSON.parse(readFileSync(taskJsonPath, \"utf-8\"))\n"
    "  const status = typeof data.status === \"string\" ? data.status : \"\"\n"
    "  if (!status) return null\n"
    "  return { id: data.id || taskRef.split(\"/\").pop(), status, source: active.source }\n"
    "}\n\n"
    "function buildBreadcrumb(id, status, templates, source = null) {\n"
    "  return `<workflow-state>\\n${id}:${status}:${source}\\n</workflow-state>`\n"
    "}\n\n"
    "export default async ({ directory }) => {\n"
    "  const ctx = new TrellisContext(directory)\n"
    "  return {\n"
    "    \"chat.message\": async (input, output) => {\n"
    "      const templates = {}\n"
    "      const task = getActiveTask(ctx, input)\n"
    "      const breadcrumb = task\n"
    "        ? buildBreadcrumb(task.id, task.status, templates, task.source)\n"
    "        : buildBreadcrumb(null, \"no_task\", templates)\n"
    "      const parts = output?.parts || []\n"
    "      parts.unshift({ type: \"text\", text: breadcrumb })\n"
    "    },\n"
    "  }\n"
    "}\n"
)
BASELINE_TRELLIS_CONTINUE_SKILL_CONTENT = (
    "---\n"
    "name: trellis-continue\n"
    "description: Baseline continue skill\n"
    "---\n\n"
    "# Continue Current Task\n\n"
    "Original baseline Codex continue skill.\n"
)
BASELINE_TRELLIS_FINISH_WORK_SKILL_CONTENT = (
    "---\n"
    "name: trellis-finish-work\n"
    "description: Baseline finish-work skill\n"
    "---\n\n"
    + BASELINE_FINISH_WORK_CONTENT
)
BASELINE_TRELLIS_BRAINSTORM_SKILL_CONTENT = (
    "---\n"
    "name: trellis-brainstorm\n"
    "description: Baseline brainstorm skill\n"
    "---\n\n"
    + BASELINE_BRAINSTORM_CONTENT
)
BASELINE_TRELLIS_CHECK_SKILL_CONTENT = (
    "---\n"
    "name: trellis-check\n"
    "description: Baseline check skill\n"
    "---\n\n"
    + BASELINE_CHECK_CONTENT
)
BASELINE_AGENT_RESEARCH_MD = (
    "---\n"
    "name: trellis-research\n"
    "description: baseline research\n"
    "---\n\n"
    "# Research Agent\n"
)
BASELINE_AGENT_IMPLEMENT_MD = (
    "---\n"
    "name: trellis-implement\n"
    "description: baseline implement\n"
    "---\n\n"
    "# Implement Agent\n"
)
BASELINE_AGENT_CHECK_MD = (
    "---\n"
    "name: trellis-check\n"
    "description: baseline check\n"
    "---\n\n"
    "# Check Agent\n"
)
BASELINE_CODEX_RESEARCH_TOML = (
    'name = "trellis-research"\n'
    'description = "baseline research"\n'
    'sandbox_mode = "read-only"\n'
)
BASELINE_CODEX_IMPLEMENT_TOML = (
    'name = "trellis-implement"\n'
    'description = "baseline implement"\n'
    'sandbox_mode = "workspace-write"\n'
)
BASELINE_CODEX_CHECK_TOML = (
    'name = "trellis-check"\n'
    'description = "baseline check"\n'
    'sandbox_mode = "read-only"\n'
)


class WorkflowInstallerTests(unittest.TestCase):
    def run_script(
        self,
        script: Path,
        *args: str,
        env: dict[str, str] | None = None,
        input_text: str | None = None,
    ) -> subprocess.CompletedProcess[str]:
        merged_env = os.environ.copy()
        if env:
            merged_env.update(env)
        return subprocess.run(
            [PYTHON, str(script), *args],
            cwd=REPO_ROOT,
            text=True,
            capture_output=True,
            check=False,
            env=merged_env,
            input=input_text,
        )

    def create_fixture(
        self,
        *,
        include_opencode: bool = False,
        include_codex: bool = False,
        include_agents_md: bool = False,
        include_git: bool = True,
        include_multi_origin_push_urls: bool = True,
        include_trellis: bool = True,
        include_trellis_version: bool = True,
        include_bootstrap_task: bool = True,
        bootstrap_as_current_task: bool = False,
        current_branch: str = "main",
        has_local_history: bool = False,
        use_latest_trellis_baseline: bool = True,
    ) -> Path:
        root = Path(tempfile.mkdtemp(prefix="workflow-installers-"))
        if include_git:
            (root / ".git").mkdir(parents=True)
            push_urls = [
                "git@github.com:example/project.git",
                "git@gitee.com:example/project.git",
            ]
            if not include_multi_origin_push_urls:
                push_urls = push_urls[:1]
            config_lines = [
                "[core]",
                "\trepositoryformatversion = 0",
                "\tfilemode = true",
                "\tbare = false",
                "\tlogallrefupdates = true",
                '[remote "origin"]',
                "\turl = git@github.com:example/project.git",
                "\tfetch = +refs/heads/*:refs/remotes/origin/*",
            ]
            config_lines.extend(f"\tpushurl = {url}" for url in push_urls)
            (root / ".git" / "config").write_text("\n".join(config_lines) + "\n", encoding="utf-8")
            (root / ".git" / "HEAD").write_text(f"ref: refs/heads/{current_branch}\n", encoding="utf-8")
            if has_local_history:
                ref_path = root / ".git" / "refs" / "heads" / current_branch
                ref_path.parent.mkdir(parents=True, exist_ok=True)
                ref_path.write_text("0123456789abcdef0123456789abcdef01234567\n", encoding="utf-8")
        (root / ".claude" / "commands" / "trellis").mkdir(parents=True)
        if include_trellis:
            (root / ".trellis").mkdir(parents=True)
            (root / ".trellis" / ".runtime" / "sessions").mkdir(parents=True, exist_ok=True)
            (root / ".trellis" / "scripts").mkdir(parents=True, exist_ok=True)
            (root / ".trellis" / "scripts" / "common").mkdir(parents=True, exist_ok=True)
            (root / ".trellis" / "workflow.md").write_text(
                BASELINE_WORKFLOW_CONTENT,
                encoding="utf-8",
            )
            (root / ".trellis" / "scripts" / "task.py").write_text(
                BASELINE_TASK_PY_CONTENT,
                encoding="utf-8",
            )
            (root / ".trellis" / "scripts" / "common" / "__init__.py").write_text(
                "",
                encoding="utf-8",
            )
            (root / ".trellis" / "scripts" / "common" / "task_store.py").write_text(
                BASELINE_TASK_STORE_CONTENT,
                encoding="utf-8",
            )
            (root / ".trellis" / "scripts" / "common" / "tasks.py").write_text(
                BASELINE_COMMON_TASKS_CONTENT,
                encoding="utf-8",
            )
            (root / ".trellis" / "scripts" / "common" / "task_queue.py").write_text(
                BASELINE_TASK_QUEUE_CONTENT,
                encoding="utf-8",
            )
            (root / ".trellis" / "scripts" / "common" / "workflow_phase.py").write_text(
                BASELINE_WORKFLOW_PHASE_CONTENT,
                encoding="utf-8",
            )
            if include_bootstrap_task:
                (root / ".trellis" / "tasks" / "00-bootstrap-guidelines").mkdir(parents=True)
                (root / ".trellis" / "tasks" / "00-bootstrap-guidelines" / "task.json").write_text(
                    '{"id":"00-bootstrap-guidelines"}\n',
                    encoding="utf-8",
                )
                if bootstrap_as_current_task:
                    (root / ".trellis" / ".current-task").write_text(
                        ".trellis/tasks/00-bootstrap-guidelines\n",
                        encoding="utf-8",
                    )
                    (root / ".trellis" / ".runtime" / "sessions" / "test-context.json").write_text(
                        json.dumps({"current_task": ".trellis/tasks/00-bootstrap-guidelines"}, ensure_ascii=False) + "\n",
                        encoding="utf-8",
                    )
        claude_entry_name = "continue.md" if use_latest_trellis_baseline else "start.md"
        claude_entry_content = BASELINE_CONTINUE_CONTENT if use_latest_trellis_baseline else BASELINE_START_CONTENT
        (root / ".claude" / "commands" / "trellis" / claude_entry_name).write_text(
            claude_entry_content,
            encoding="utf-8",
        )
        (root / ".claude" / "commands" / "trellis" / "brainstorm.md").write_text(
            BASELINE_BRAINSTORM_CONTENT,
            encoding="utf-8",
        )
        (root / ".claude" / "commands" / "trellis" / "check.md").write_text(
            BASELINE_CHECK_CONTENT,
            encoding="utf-8",
        )
        (root / ".claude" / "commands" / "trellis" / "parallel.md").write_text(
            BASELINE_PARALLEL_CONTENT,
            encoding="utf-8",
        )
        (root / ".claude" / "commands" / "trellis" / "finish-work.md").write_text(
            BASELINE_FINISH_WORK_CONTENT,
            encoding="utf-8",
        )
        (root / ".claude" / "commands" / "trellis" / "record-session.md").write_text(
            BASELINE_RECORD_SESSION_CONTENT,
            encoding="utf-8",
        )
        (root / ".claude" / "hooks").mkdir(parents=True, exist_ok=True)
        (root / ".claude" / "hooks" / "session-start.py").write_text(
            BASELINE_SESSION_START_CONTENT,
            encoding="utf-8",
        )
        (root / ".claude" / "hooks" / "inject-workflow-state.py").write_text(
            BASELINE_INJECT_WORKFLOW_STATE_HOOK_CONTENT,
            encoding="utf-8",
        )
        (root / ".claude" / "agents").mkdir(parents=True, exist_ok=True)
        claude_agent_prefix = "trellis-" if use_latest_trellis_baseline else ""
        (root / ".claude" / "agents" / f"{claude_agent_prefix}research.md").write_text(BASELINE_AGENT_RESEARCH_MD, encoding="utf-8")
        (root / ".claude" / "agents" / f"{claude_agent_prefix}implement.md").write_text(BASELINE_AGENT_IMPLEMENT_MD, encoding="utf-8")
        (root / ".claude" / "agents" / f"{claude_agent_prefix}check.md").write_text(BASELINE_AGENT_CHECK_MD, encoding="utf-8")
        if include_trellis and include_trellis_version:
            version = "0.5.0-rc.3" if use_latest_trellis_baseline else "2.0.0"
            (root / ".trellis" / ".version").write_text(f"{version}\n", encoding="utf-8")
        if include_opencode:
            (root / ".opencode" / "commands" / "trellis").mkdir(parents=True)
            (root / ".opencode" / "lib").mkdir(parents=True, exist_ok=True)
            (root / ".opencode" / "plugins").mkdir(parents=True, exist_ok=True)
            opencode_entry_name = "continue.md" if use_latest_trellis_baseline else "start.md"
            opencode_entry_content = (
                BASELINE_CONTINUE_CONTENT.replace("Original baseline", "Original OpenCode baseline")
                if use_latest_trellis_baseline
                else BASELINE_START_CONTENT.replace("Original baseline", "Original OpenCode baseline")
            )
            (root / ".opencode" / "commands" / "trellis" / opencode_entry_name).write_text(
                opencode_entry_content,
                encoding="utf-8",
            )
            (root / ".opencode" / "commands" / "trellis" / "brainstorm.md").write_text(
                BASELINE_BRAINSTORM_CONTENT,
                encoding="utf-8",
            )
            (root / ".opencode" / "commands" / "trellis" / "check.md").write_text(
                BASELINE_CHECK_CONTENT,
                encoding="utf-8",
            )
            (root / ".opencode" / "commands" / "trellis" / "parallel.md").write_text(
                BASELINE_PARALLEL_CONTENT,
                encoding="utf-8",
            )
            (root / ".opencode" / "commands" / "trellis" / "finish-work.md").write_text(
                BASELINE_FINISH_WORK_CONTENT,
                encoding="utf-8",
            )
            (root / ".opencode" / "commands" / "trellis" / "record-session.md").write_text(
                BASELINE_OPENCODE_RECORD_SESSION_CONTENT,
                encoding="utf-8",
            )
            (root / ".opencode" / "agents").mkdir(parents=True)
            (root / ".opencode" / "lib" / "session-utils.js").write_text(
                BASELINE_OPENCODE_SESSION_UTILS_CONTENT,
                encoding="utf-8",
            )
            (root / ".opencode" / "plugins" / "session-start.js").write_text(
                BASELINE_OPENCODE_SESSION_START_PLUGIN,
                encoding="utf-8",
            )
            (root / ".opencode" / "plugins" / "inject-workflow-state.js").write_text(
                BASELINE_OPENCODE_INJECT_WORKFLOW_STATE_PLUGIN,
                encoding="utf-8",
            )
            opencode_agent_prefix = "trellis-" if use_latest_trellis_baseline else ""
            (root / ".opencode" / "agents" / f"{opencode_agent_prefix}research.md").write_text(BASELINE_AGENT_RESEARCH_MD, encoding="utf-8")
            (root / ".opencode" / "agents" / f"{opencode_agent_prefix}implement.md").write_text(BASELINE_AGENT_IMPLEMENT_MD, encoding="utf-8")
            (root / ".opencode" / "agents" / f"{opencode_agent_prefix}check.md").write_text(BASELINE_AGENT_CHECK_MD, encoding="utf-8")
        if include_codex:
            (root / ".agents" / "skills").mkdir(parents=True)
            (root / ".agents" / "skills" / "trellis-start").mkdir(parents=True)
            (root / ".agents" / "skills" / "trellis-start" / "SKILL.md").write_text(
                BASELINE_START_SKILL_CONTENT,
                encoding="utf-8",
            )
            (root / ".agents" / "skills" / "trellis-continue").mkdir(parents=True)
            (root / ".agents" / "skills" / "trellis-continue" / "SKILL.md").write_text(
                BASELINE_TRELLIS_CONTINUE_SKILL_CONTENT,
                encoding="utf-8",
            )
            (root / ".agents" / "skills" / "trellis-finish-work").mkdir(parents=True)
            (root / ".agents" / "skills" / "trellis-finish-work" / "SKILL.md").write_text(
                BASELINE_TRELLIS_FINISH_WORK_SKILL_CONTENT,
                encoding="utf-8",
            )
            (root / ".agents" / "skills" / "trellis-brainstorm").mkdir(parents=True)
            (root / ".agents" / "skills" / "trellis-brainstorm" / "SKILL.md").write_text(
                BASELINE_TRELLIS_BRAINSTORM_SKILL_CONTENT,
                encoding="utf-8",
            )
            (root / ".agents" / "skills" / "trellis-check").mkdir(parents=True)
            (root / ".agents" / "skills" / "trellis-check" / "SKILL.md").write_text(
                BASELINE_TRELLIS_CHECK_SKILL_CONTENT,
                encoding="utf-8",
            )
            (root / ".agents" / "skills" / "parallel").mkdir(parents=True)
            (root / ".agents" / "skills" / "parallel" / "SKILL.md").write_text(
                BASELINE_PARALLEL_CONTENT,
                encoding="utf-8",
            )
            (root / ".codex" / "hooks").mkdir(parents=True)
            (root / ".codex" / "agents").mkdir(parents=True)
            (root / ".codex" / "hooks.json").write_text("{}", encoding="utf-8")
            (root / ".codex" / "hooks" / "inject-workflow-state.py").write_text(
                BASELINE_INJECT_WORKFLOW_STATE_HOOK_CONTENT,
                encoding="utf-8",
            )
            (root / ".codex" / "hooks" / "session-start.py").write_text(
                BASELINE_SESSION_START_CONTENT,
                encoding="utf-8",
            )
            codex_agent_prefix = "trellis-" if use_latest_trellis_baseline else ""
            (root / ".codex" / "agents" / f"{codex_agent_prefix}research.toml").write_text(BASELINE_CODEX_RESEARCH_TOML, encoding="utf-8")
            (root / ".codex" / "agents" / f"{codex_agent_prefix}implement.toml").write_text(BASELINE_CODEX_IMPLEMENT_TOML, encoding="utf-8")
            (root / ".codex" / "agents" / f"{codex_agent_prefix}check.toml").write_text(BASELINE_CODEX_CHECK_TOML, encoding="utf-8")
        if include_agents_md:
            (root / "AGENTS.md").write_text("# Project Rules\n", encoding="utf-8")
        return root

    def install_workflow(self, fixture_root: Path, *args: str) -> subprocess.CompletedProcess[str]:
        forwarded_args = list(args)
        if "--profile" not in forwarded_args:
            forwarded_args = ["--profile", "outsourcing", *forwarded_args]
        return self.run_script(
            INSTALL_SCRIPT,
            "--project-root",
            str(fixture_root),
            *forwarded_args,
            env={EMBED_CONFIRM_ENV: "1"},
        )

    def test_install_requires_explicit_profile_in_non_interactive_mode(self) -> None:
        fixture = self.create_fixture()
        self.addCleanup(shutil.rmtree, fixture)

        result = self.run_script(
            INSTALL_SCRIPT,
            "--project-root",
            str(fixture),
            env={EMBED_CONFIRM_ENV: "1"},
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("--profile", result.stdout + result.stderr)
        self.assertIn("非交互", result.stdout + result.stderr)
        self.assertFalse((fixture / ".trellis" / "workflow-installed.json").exists())

    def test_install_prompts_for_profile_in_interactive_mode(self) -> None:
        fixture = self.create_fixture()
        self.addCleanup(shutil.rmtree, fixture)

        result = self.run_script(
            INSTALL_SCRIPT,
            "--project-root",
            str(fixture),
            env={EMBED_CONFIRM_ENV: "1", "FORCE_INTERACTIVE_PROFILE_PROMPT": "1"},
            input_text="personal\n",
        )

        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        self.assertIn("请选择安装 profile", result.stdout)
        record = json.loads((fixture / ".trellis" / "workflow-installed.json").read_text(encoding="utf-8"))
        self.assertEqual(record["profile"], "personal")

    def test_install_prompt_accepts_profile_initial(self) -> None:
        fixture = self.create_fixture()
        self.addCleanup(shutil.rmtree, fixture)

        result = self.run_script(
            INSTALL_SCRIPT,
            "--project-root",
            str(fixture),
            env={EMBED_CONFIRM_ENV: "1", "FORCE_INTERACTIVE_PROFILE_PROMPT": "1"},
            input_text="p\n",
        )

        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        record = json.loads((fixture / ".trellis" / "workflow-installed.json").read_text(encoding="utf-8"))
        self.assertEqual(record["profile"], "personal")

    def test_install_dry_run_prompts_for_profile_in_interactive_mode(self) -> None:
        fixture = self.create_fixture()
        self.addCleanup(shutil.rmtree, fixture)

        result = self.run_script(
            INSTALL_SCRIPT,
            "--project-root",
            str(fixture),
            "--dry-run",
            env={"FORCE_INTERACTIVE_PROFILE_PROMPT": "1"},
            input_text="outsourcing\n",
        )

        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        self.assertIn("请选择安装 profile", result.stdout)
        self.assertIn("Profile: outsourcing", result.stdout)
        self.assertFalse((fixture / ".trellis" / "workflow-installed.json").exists())

    def test_install_dry_run_prompt_accepts_profile_initial(self) -> None:
        fixture = self.create_fixture()
        self.addCleanup(shutil.rmtree, fixture)

        result = self.run_script(
            INSTALL_SCRIPT,
            "--project-root",
            str(fixture),
            "--dry-run",
            env={"FORCE_INTERACTIVE_PROFILE_PROMPT": "1"},
            input_text="o\n",
        )

        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        self.assertIn("Profile: outsourcing", result.stdout)
        self.assertFalse((fixture / ".trellis" / "workflow-installed.json").exists())

    def test_install_removes_bootstrap_task_before_first_route(self) -> None:
        fixture = self.create_fixture(bootstrap_as_current_task=True)
        self.addCleanup(shutil.rmtree, fixture)

        install = self.install_workflow(fixture, "--profile", "outsourcing")
        self.assertEqual(install.returncode, 0, msg=install.stdout + install.stderr)
        self.assertFalse((fixture / ".trellis" / "tasks" / "00-bootstrap-guidelines").exists())
        self.assertFalse((fixture / ".trellis" / ".current-task").exists())
        self.assertFalse((fixture / ".trellis" / ".runtime" / "sessions" / "test-context.json").exists())

    def test_embed_entry_scripts_and_docs_pass_explicit_outsourcing_profile(self) -> None:
        temp_project_script = (REPO_ROOT / "commands" / "shell" / "init-trellis-temp-project.sh").read_text(
            encoding="utf-8"
        )
        quick_commands = (REPO_ROOT / "trellis常用提示语句.txt").read_text(encoding="utf-8")

        self.assertIn("--profile \"$INSTALL_PROFILE\" --dry-run", temp_project_script)
        self.assertIn("--profile \"$INSTALL_PROFILE\"", temp_project_script)
        self.assertIn("prompt_profile()", temp_project_script)
        self.assertIn("--profile outsourcing --dry-run", quick_commands)
        self.assertIn("--profile outsourcing", quick_commands)

    def test_install_entry_docs_state_profile_must_be_explicit(self) -> None:
        workflow_overview = (REPO_ROOT / "docs" / "workflows" / "新项目开发工作流" / "工作流总纲.md").read_text(
            encoding="utf-8"
        )
        command_mapping = (REPO_ROOT / "docs" / "workflows" / "新项目开发工作流" / "命令映射.md").read_text(
            encoding="utf-8"
        )
        embed_spec = (REPO_ROOT / "docs" / "workflows" / "新项目开发工作流" / "工作流嵌入执行规范.md").read_text(
            encoding="utf-8"
        )

        self.assertIn("必须显式传入 `--profile`", workflow_overview)
        self.assertIn("显式传入 `--profile`", command_mapping)
        self.assertIn("`--profile` 必须显式传入", embed_spec)

    def test_finish_work_skill_matches_current_codex_validation_contract(self) -> None:
        embed_integrity = (COMMANDS_DIR / "shell" / "embed_integrity.py").read_text(encoding="utf-8")
        finish_work_patch = (COMMANDS_DIR / "finish-work-patch-projectization.md").read_text(
            encoding="utf-8"
        )

        self.assertIn("complete native Trellis close-out after delivery", embed_integrity)
        self.assertIn("archive + session-record steps after delivery", embed_integrity)
        self.assertIn("Trellis 原生 `finish-work` 是**当前活动任务**的正常终态入口", finish_work_patch)
        self.assertIn("使用 Trellis 原生 `finish-work` 完成最终 `archive + add_session`", finish_work_patch)

    def test_patch_task_create_preserve_active_produces_compilable_python(self) -> None:
        root = Path(tempfile.mkdtemp(prefix="workflow-task-store-patch-"))
        self.addCleanup(shutil.rmtree, root)
        target = root / "task_store.py"
        target.write_text(BASELINE_TASK_STORE_CONTENT, encoding="utf-8")

        spec = importlib.util.spec_from_file_location("patch_task_store", PATCH_TASK_CREATE_SCRIPT)
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        applied = module.patch_task_store(target)
        self.assertTrue(applied, "patch_task_store should patch the baseline fixture")

        result = subprocess.run(
            [PYTHON, "-m", "py_compile", str(target)],
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)

    def test_patch_workflow_phase_blocks_legacy_step_lookup_when_strong_gate_state_exists(self) -> None:
        root = Path(tempfile.mkdtemp(prefix="workflow-phase-patch-"))
        self.addCleanup(shutil.rmtree, root)
        target = root / ".trellis" / "scripts" / "common" / "workflow_phase.py"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(BASELINE_WORKFLOW_PHASE_CONTENT, encoding="utf-8")

        task_script = root / ".trellis" / "scripts" / "task.py"
        task_script.write_text(
            "from pathlib import Path\n"
            "import sys\n\n"
            "if len(sys.argv) >= 2 and sys.argv[1] == 'current':\n"
            "    print(str(Path(__file__).resolve().parents[1] / 'tasks' / '04-15-sample-task'))\n"
            "    raise SystemExit(0)\n"
            "raise SystemExit(1)\n",
            encoding="utf-8",
        )

        task_dir = root / ".trellis" / "tasks" / "04-15-sample-task"
        task_dir.mkdir(parents=True, exist_ok=True)
        (task_dir / "workflow-state.json").write_text('{"stage":"design"}\n', encoding="utf-8")

        spec = importlib.util.spec_from_file_location("patch_workflow_phase", PATCH_WORKFLOW_PHASE_SCRIPT)
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        patch_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(patch_module)

        applied = patch_module.patch_workflow_phase(target)
        self.assertTrue(applied, "patch_workflow_phase should patch the baseline fixture")

        module_spec = importlib.util.spec_from_file_location("patched_workflow_phase", target)
        self.assertIsNotNone(module_spec)
        self.assertIsNotNone(module_spec.loader)
        runtime_module = importlib.util.module_from_spec(module_spec)
        module_spec.loader.exec_module(runtime_module)

        self.assertEqual(runtime_module.get_step.__doc__, "Return the legacy step body.")
        self.assertEqual(runtime_module.get_step("1.0"), "legacy step 1.0")

    def test_build_workflow_content_replaces_task_mechanism_without_legacy_headings(self) -> None:
        import importlib.util

        module_path = COMMANDS_DIR / "install-workflow.py"
        spec = importlib.util.spec_from_file_location("workflow_install_workflow_test", module_path)
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        patch_text = module.prepare_command_content(COMMANDS_DIR / "workflow-patch-projectization.md")
        patched = module.build_workflow_content(LATEST_BASELINE_WORKFLOW_CONTENT, patch_text)

        self.assertIsNotNone(patched)
        assert patched is not None
        self.assertIn(WORKFLOW_PATCH_MARKER, patched)
        self.assertIn(module._STRONG_GATE_WORKFLOW_TASK_MECHANISM, patched)
        self.assertIn("#### 1.1 Requirement exploration", patched)
        self.assertIn("#### 3.5 Wrap-up reminder", patched)
        self.assertNotIn("flips `task.json.status` from `planning` to `in_progress`", patched)

    def test_upgrade_build_workflow_content_replaces_task_mechanism_without_legacy_headings(self) -> None:
        import importlib.util

        module_path = COMMANDS_DIR / "upgrade-compat.py"
        spec = importlib.util.spec_from_file_location("workflow_upgrade_compat_test", module_path)
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        patch_text = module.prepare_command_content(COMMANDS_DIR / "workflow-patch-projectization.md")
        patched = module.build_workflow_content(LATEST_BASELINE_WORKFLOW_CONTENT, patch_text)

        self.assertIsNotNone(patched)
        assert patched is not None
        self.assertIn(WORKFLOW_PATCH_MARKER, patched)
        self.assertIn(module._INSTALL_WORKFLOW._STRONG_GATE_WORKFLOW_TASK_MECHANISM, patched)
        self.assertIn("#### 1.1 Requirement exploration", patched)
        self.assertIn("#### 3.5 Wrap-up reminder", patched)
        self.assertNotIn("flips `task.json.status` from `planning` to `in_progress`", patched)

    def detect_embed_state(self, fixture_root: Path, *args: str, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
        return self.run_script(DETECT_EMBED_STATE_SCRIPT, "--project-root", str(fixture_root), *args, env=env)

    def latest_env_for(self, fixture_root: Path) -> dict[str, str]:
        version_path = fixture_root / ".trellis" / ".version"
        return {"TRELLIS_LATEST_VERSION": version_path.read_text(encoding="utf-8").strip()}

    def assert_install_result_usable(self, result: subprocess.CompletedProcess[str]) -> None:
        """Fixture-level workflow.md drift is tolerated; runtime patch failures are not."""
        if result.returncode == 0:
            return
        combined = result.stdout + result.stderr
        self.assertIn(".trellis/workflow.md: 项目化补丁内容漂移", combined)
        self.assertNotIn("session-start.py: 强门禁补丁缺失", combined)
        self.assertNotIn("task.py: strong-gate no-status-flip 补丁缺失", combined)
        self.assertNotIn("common/task_store.py: preserve-active 补丁缺失", combined)
        self.assertNotIn("common/tasks.py: strong-gate task status view 补丁缺失", combined)
        self.assertNotIn("common/task_queue.py: strong-gate pending-task 视图补丁缺失", combined)
        self.assertNotIn("common/workflow_phase.py: 强门禁补丁缺失", combined)

    def mark_legacy_codex_installed(self, fixture_root: Path) -> None:
        record_path = fixture_root / ".trellis" / "workflow-installed.json"
        record_data = json.loads(record_path.read_text(encoding="utf-8"))
        cli_types = list(record_data.get("cli_types", []))
        if "codex" not in cli_types:
            cli_types.append("codex")
        record_data["cli_types"] = cli_types
        record_data["patched_codex_skills"] = ["start", "finish-work"]
        record_path.write_text(json.dumps(record_data, ensure_ascii=False, indent=2), encoding="utf-8")

    def apply_legacy_codex_workflow_state(self, fixture_root: Path) -> None:
        self.mark_legacy_codex_installed(fixture_root)
        commands_root = COMMANDS_DIR
        start_skill = fixture_root / ".agents" / "skills" / "start" / "SKILL.md"
        finish_work_skill = fixture_root / ".agents" / "skills" / "finish-work" / "SKILL.md"
        start_backup = fixture_root / ".agents" / "skills" / ".backup-original" / "start" / "SKILL.md"
        finish_backup = fixture_root / ".agents" / "skills" / ".backup-original" / "finish-work" / "SKILL.md"
        start_backup.parent.mkdir(parents=True, exist_ok=True)
        finish_backup.parent.mkdir(parents=True, exist_ok=True)
        start_backup.write_text(BASELINE_START_SKILL_CONTENT, encoding="utf-8")
        finish_backup.write_text(BASELINE_FINISH_WORK_CONTENT, encoding="utf-8")

        install_module = self.run_script  # suppress linter-like unused concerns by local aliasing? no
        _ = install_module
        import importlib.util
        module_path = COMMANDS_DIR / "install-workflow.py"
        spec = importlib.util.spec_from_file_location("workflow_install_workflow_test", module_path)
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        patched_start = module.build_codex_start_skill_content(
            BASELINE_START_SKILL_CONTENT,
            module.prepare_command_content(commands_root / "start-skill-patch-phase-router.md"),
        )
        assert patched_start is not None
        start_skill.parent.mkdir(parents=True, exist_ok=True)
        start_skill.write_text(patched_start, encoding="utf-8")

        patched_finish = module.build_finish_work_content(
            BASELINE_FINISH_WORK_CONTENT,
            module.prepare_command_content(commands_root / "finish-work-patch-projectization.md"),
        )
        assert patched_finish is not None
        finish_work_skill.parent.mkdir(parents=True, exist_ok=True)
        finish_work_skill.write_text(patched_finish, encoding="utf-8")

        agents_backup_dir = fixture_root / ".trellis" / ".backup-original" / "codex-agents"
        agents_backup_dir.mkdir(parents=True, exist_ok=True)
        (agents_backup_dir / "trellis-research.toml").write_text(BASELINE_CODEX_RESEARCH_TOML, encoding="utf-8")
        (agents_backup_dir / "trellis-implement.toml").write_text(BASELINE_CODEX_IMPLEMENT_TOML, encoding="utf-8")
        (agents_backup_dir / "trellis-check.toml").write_text(BASELINE_CODEX_CHECK_TOML, encoding="utf-8")

    def test_install_deploys_record_session_closure_helper_and_patch(self) -> None:
        fixture = self.create_fixture(include_opencode=True, include_codex=True)
        self.addCleanup(shutil.rmtree, fixture)

        install = self.install_workflow(fixture)

        self.assert_install_result_usable(install)
        brainstorm = fixture / ".claude" / "commands" / "trellis" / "brainstorm.md"
        self.assertTrue(brainstorm.exists(), "brainstorm.md should be deployed")
        project_audit = fixture / ".claude" / "commands" / "trellis" / "project-audit.md"
        self.assertTrue(project_audit.exists(), "project-audit.md should be deployed")
        project_audit_text = project_audit.read_text(encoding="utf-8")
        self.assertIn("代码漏洞检测与代码质量总检", project_audit_text)
        self.assertIn("项目级统一代码漏洞检测命令", project_audit_text)
        self.assertIn("项目级统一代码质量总检命令", project_audit_text)
        workflow_state_helper = fixture / ".trellis" / "scripts" / "workflow" / "workflow-state.py"
        self.assertTrue(workflow_state_helper.exists(), "workflow-state.py should be deployed")
        ownership_helper = fixture / ".trellis" / "scripts" / "workflow" / "ownership-proof-validate.py"
        self.assertTrue(ownership_helper.exists(), "ownership-proof-validate.py should be deployed")
        watermark_guard = fixture / ".trellis" / "scripts" / "workflow" / "source-watermark-guard.py"
        self.assertTrue(watermark_guard.exists(), "source-watermark-guard.py should be deployed")
        workflow_doc = fixture / ".trellis" / "workflow.md"
        workflow_doc_text = workflow_doc.read_text(encoding="utf-8")
        self.assertIn(WORKFLOW_PATCH_MARKER, workflow_doc_text)
        self.assertIn("task.py start <task-dir>", workflow_doc_text)
        self.assertIn("does **not** advance `workflow-state.json.stage`", workflow_doc_text)
        self.assertIn("load `/trellis:brainstorm` for prd iteration", workflow_doc_text)
        self.assertNotIn("no_task → brainstorm", workflow_doc_text)
        self.assertNotIn("personal first entry", workflow_doc_text)
        self.assertIn("no_task → feasibility", workflow_doc_text)
        self.assertIn("需求变更管理执行卡", workflow_doc_text)
        self.assertIn("源码水印与归属证据链执行卡", workflow_doc_text)
        self.assertNotIn("flips `task.json.status` from `planning` to `in_progress`", workflow_doc_text)
        self.assertIn("python3 ./.trellis/scripts/add_session.py", workflow_doc_text)
        self.assertIn("finish-work-checklist.md", workflow_doc_text)
        self.assertIn("child task", workflow_doc_text)
        self.assertIn("parent coordinator records", workflow_doc_text)
        self.assertIn("does not automatically authorize", workflow_doc_text)
        self.assertIn("[workflow-state:blocked]", workflow_doc_text)
        self.assertIn("[workflow-state:repair_needed]", workflow_doc_text)
        self.assertIn("[workflow-state:stale]", workflow_doc_text)
        self.assertNotIn("[workflow-state:needs-init]", workflow_doc_text)
        self.assertIn("[workflow-state:awaiting_confirmation_with_blockers]", workflow_doc_text)
        self.assertIn("do **not** expect a public `/trellis:implementation` command", workflow_doc_text)
        self.assertIn("Global execution rule", workflow_doc_text)
        self.assertIn("Do not dispatch `trellis-research`, `trellis-implement`, `trellis-check`", workflow_doc_text)
        self.assertNotIn("Phase 1: Plan    → figure out what to do", workflow_doc_text)
        start_text = (fixture / ".claude" / "commands" / "trellis" / "continue.md").read_text(encoding="utf-8")
        self.assertIn(
            ".trellis/scripts/workflow/workflow-state.py route <task-dir> --project-root <project-root>",
            start_text,
        )
        self.assertIn("不要期待存在公开的 `/trellis:implementation` 入口", start_text)
        self.assertIn("awaiting_confirmation_with_blockers", start_text)
        self.assertNotIn("Steps 1-4 替换说明", start_text)
        self.assertNotIn("Load Current Context", start_text)
        self.assertNotIn("docs/workflows/新项目开发工作流/commands/shell", start_text)
        trellis_start_text = (fixture / ".agents" / "skills" / "trellis-start" / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("## Workflow Phase Router Patch `[AI]`", trellis_start_text)
        self.assertIn("Route initial user intent through the installed workflow router", trellis_start_text)
        self.assertIn("every project starts at `feasibility`", trellis_start_text)
        self.assertNotIn("personal-profile first entry may enter `brainstorm` directly", trellis_start_text)
        self.assertNotIn("bootstrap the minimum assessment baseline", trellis_start_text)
        self.assertNotIn("--step 2.1 --platform codex", trellis_start_text)
        self.assertNotIn("## Step 4: Decide next action", trellis_start_text)
        finish_work = fixture / ".claude" / "commands" / "trellis" / "finish-work.md"
        finish_work_text = finish_work.read_text(encoding="utf-8")
        self.assertIn(FINISH_WORK_MARKER, finish_work_text)
        self.assertNotIn("pnpm lint", finish_work_text)
        self.assertNotIn("archive the active task", finish_work_text)
        self.assertNotIn("Step 3/4 替换说明", finish_work_text)
        self.assertIn("当前活动任务", finish_work_text)
        self.assertIn("不是同一层级的阶段定义", finish_work_text)
        # 补丁已条件化：验证质量平台门禁口径，不再硬断言特定 sonar 内容
        self.assertIn("质量平台门禁", finish_work_text)
        codex_finish_work_text = (
            fixture / ".agents" / "skills" / "trellis-finish-work" / "SKILL.md"
        ).read_text(encoding="utf-8")
        self.assertIn("archive + session-record steps after delivery", codex_finish_work_text)
        self.assertIn("使用 Trellis 原生 `finish-work` 完成最终 `archive + add_session`", codex_finish_work_text)
        self.assertNotIn("hand off to `delivery`", codex_finish_work_text)
        self.assertNotIn("hand off to delivery", codex_finish_work_text)
        task_py_text = (fixture / ".trellis" / "scripts" / "task.py").read_text(encoding="utf-8")
        self.assertIn(TASK_NO_STATUS_FLIP_PATCH_MARKER, task_py_text)
        self.assertIn(
            'help="Set active task (strong-gate: refresh pointer only; does not flip task.json status or advance workflow stage)"',
            task_py_text,
        )
        self.assertIn(
            "Set active task (strong-gate: pointer only; stage changes still go through workflow-state.py)",
            task_py_text,
        )
        task_store_text = (fixture / ".trellis" / "scripts" / "common" / "task_store.py").read_text(encoding="utf-8")
        self.assertIn(TASK_CREATE_PRESERVE_ACTIVE_PATCH_MARKER, task_store_text)
        self.assertIn("archive only after workflow close-out gate validation", task_store_text)
        claude_session_start = (fixture / ".claude" / "hooks" / "session-start.py").read_text(encoding="utf-8")
        self.assertIn(SESSION_START_STRONG_GATE_PATCH_MARKER, claude_session_start)
        self.assertNotIn(LEGACY_READY_AUTOCONTINUE_LINE, claude_session_start)
        self.assertIn("new implementation work still enters `/trellis:feasibility` first", claude_session_start)
        self.assertIn('_r_stage_status = _route_data.get("status", "")', claude_session_start)
        claude_subagent_hook_path = fixture / ".claude" / "hooks" / "inject-subagent-context.py"
        if claude_subagent_hook_path.exists():
            claude_subagent_hook = claude_subagent_hook_path.read_text(encoding="utf-8")
            self.assertIn("# [workflow-embed-patch:claude-subagent-gates]", claude_subagent_hook)
            self.assertIn("Strong-gate blocked this subagent dispatch.", claude_subagent_hook)
            self.assertIn("current embedded workflow disables agent/subagent execution paths", claude_subagent_hook)
        codex_session_start = (fixture / ".codex" / "hooks" / "session-start.py").read_text(encoding="utf-8")
        self.assertIn(SESSION_START_STRONG_GATE_PATCH_MARKER, codex_session_start)
        self.assertNotIn(LEGACY_READY_AUTOCONTINUE_LINE, codex_session_start)
        claude_inject = (fixture / ".claude" / "hooks" / "inject-workflow-state.py").read_text(encoding="utf-8")
        self.assertIn("use_action_status =", claude_inject)
        self.assertIn('extra_lines.append(f"Stage: {route_stage}")', claude_inject)
        self.assertIn('route_stage_status = route_data.get("status", "")', claude_inject)
        self.assertIn("workflow-state.route_failed", claude_inject)
        self.assertNotIn("fall back to task.json status", claude_inject)
        codex_inject = (fixture / ".codex" / "hooks" / "inject-workflow-state.py").read_text(encoding="utf-8")
        self.assertIn("workflow-state.route_failed", codex_inject)
        self.assertNotIn("fall back to task.json status", codex_inject)
        opencode_session_utils = (fixture / ".opencode" / "lib" / "session-utils.js").read_text(encoding="utf-8")
        self.assertIn(OPENCODE_SESSION_UTILS_PATCH_MARKER, opencode_session_utils)
        self.assertNotIn(LEGACY_READY_AUTOCONTINUE_LINE, opencode_session_utils)
        self.assertIn('stripped === "## Customizing Trellis (for forks)"', opencode_session_utils)
        self.assertNotIn('stripped === "## Workflow State Breadcrumbs"', opencode_session_utils)
        self.assertIn("function stripBreadcrumbTagBlocks(content)", opencode_session_utils)
        opencode_subagent_path = fixture / ".opencode" / "plugins" / "inject-subagent-context.js"
        if opencode_subagent_path.exists():
            opencode_subagent = opencode_subagent_path.read_text(encoding="utf-8")
            self.assertIn("buildBlockedSubagentPrompt(routeData, subagentType, originalPrompt)", opencode_subagent)
            self.assertIn("Strong-gate blocked this subagent dispatch.", opencode_subagent)
            self.assertIn("current embedded workflow disables agent/subagent execution paths", opencode_subagent)
            self.assertIn("return false", opencode_subagent)
        opencode_inject_path = fixture / ".opencode" / "plugins" / "inject-workflow-state.js"
        if opencode_inject_path.exists():
            opencode_inject = opencode_inject_path.read_text(encoding="utf-8")
            self.assertIn("ACTION_BREADCRUMB_KEYS", opencode_inject)
            self.assertIn('const PYTHON_CMD = process.env.TRELLIS_PYTHON || "python3"', opencode_inject)
            self.assertNotIn("if (!rawStatus) return null", opencode_inject)
            self.assertIn("workflow-state.route_failed", opencode_inject)
            self.assertNotIn("fall back to task.json status", opencode_inject)
        record = fixture / ".trellis" / "workflow-installed.json"
        self.assertTrue(record.exists(), "workflow-installed.json should be created")
        record_data = json.loads(record.read_text(encoding="utf-8"))
        self.assertIn("brainstorm", record_data["commands"])
        self.assertIn("project-audit", record_data["commands"])
        self.assertEqual(record_data["overlay_commands"], ["brainstorm", "check"])
        self.assertEqual(record_data["disabled_commands"], ["parallel"])
        self.assertEqual(
            record_data["patched_baseline_commands"],
            ["continue", "finish-work"],
        )
        self.assertNotIn("record-session", record_data["patched_baseline_commands"])
        self.assertEqual(record_data["patched_shared_docs"], ["workflow.md"])
        self.assertEqual(
            record_data["critical_runtime_patches"],
            [
                "inject-workflow-state",
                "session-start-strong-gate",
                "claude-inject-subagent-context",
                "opencode-inject-subagent-context",
                "task-start-strong-gate",
                "task-create-preserve-active",
                "task-status-view-strong-gate",
                "workflow-phase-strong-gate",
            ],
        )
        self.assertEqual(record_data["profile"], "outsourcing")
        self.assertEqual(record_data["scripts"], HELPER_SCRIPTS)
        self.assertEqual(
            record_data["execution_cards"],
            ["需求变更管理执行卡.md", "源码水印与归属证据链执行卡.md"],
        )
        for helper_name in HELPER_SCRIPTS:
            helper_path = fixture / ".trellis" / "scripts" / "workflow" / helper_name
            self.assertTrue(helper_path.exists(), f"{helper_name} should be deployed")
        self.assertTrue(PATCH_WORKFLOW_PHASE_STRONG_GATE_SCRIPT.exists())
        self.assertTrue(PATCH_TASK_STATUS_VIEW_STRONG_GATE_SCRIPT.exists())
        change_card = fixture / ".trellis" / "workflow-docs" / "需求变更管理执行卡.md"
        ownership_card = fixture / ".trellis" / "workflow-docs" / "源码水印与归属证据链执行卡.md"
        self.assertTrue(change_card.exists(), "需求变更管理执行卡.md should be deployed")
        self.assertTrue(ownership_card.exists(), "源码水印与归属证据链执行卡.md should be deployed")
        change_card_text = change_card.read_text(encoding="utf-8")
        self.assertIn(".trellis/workflow.md", change_card_text)
        self.assertIn("continue` / `trellis-continue", change_card_text)
        self.assertIn("运行期创建或补齐 `docs/requirements/customer-facing-prd.md`", change_card_text)
        self.assertNotIn("§2.5", change_card_text)
        self.assertNotIn("§2.4", change_card_text)
        self.assertNotIn("commands/delivery.md", change_card_text)
        self.assertNotIn("CLI原生适配边界矩阵.md", change_card_text)
        ownership_card_text = ownership_card.read_text(encoding="utf-8")
        self.assertIn("./.trellis/scripts/workflow/ownership-proof-validate.py", ownership_card_text)
        self.assertIn("./.trellis/scripts/workflow/source-watermark-guard.py", ownership_card_text)
        self.assertNotIn("docs/workflows/新项目开发工作流/commands/shell", ownership_card_text)
        self.assertNotIn("<WORKFLOW_DIR>/commands/shell", ownership_card_text)
        self.assertEqual(record_data["workflow_version"], "0.1.28")
        self.assertEqual(record_data["workflow_schema_version"], "3")
        self.assertEqual(record_data["initial_pack"], "pack.requirements-discovery-foundation")
        self.assertIn(
            "spec.universal-domains.product-and-requirements.problem-definition",
            record_data["initial_pack_assets"],
        )
        self.assertIn(
            ".trellis/library-assets/examples/assembled-packs/requirements-discovery-foundation.md",
            record_data["initial_pack_target_paths"],
        )
        self.assertEqual(record_data["initial_pack_cleanup_policy"], "retain-imported-assets")
        self.assertEqual(record_data["workflow_doc_cleanup_policy"], "remove-on-uninstall")
        self.assertIn("finish-work-checklist-template.md", record_data["workflow_shared_docs"])
        self.assertIn("workflow-phase-index-strong-gate", record_data["workflow_doc_patch_components"])
        parallel = fixture / ".claude" / "commands" / "trellis" / "parallel.md"
        self.assertFalse(parallel.exists())
        self.assertTrue((fixture / ".claude" / "commands" / "trellis" / ".backup-original" / "parallel.md").exists())
        deployed_feasibility = (fixture / ".claude" / "commands" / "trellis" / "feasibility.md").read_text(
            encoding="utf-8"
        )
        self.assertIn(".trellis/scripts/workflow/feasibility-check.py", deployed_feasibility)
        self.assertNotIn("docs/workflows/新项目开发工作流/commands/shell", deployed_feasibility)
        self.assertIn("OpenCode 入口见目标项目 AGENTS.md 路由表", deployed_feasibility)
        self.assertNotIn("personal profile 首次入口例外", deployed_feasibility)
        self.assertIn("不存在按 profile 跳过 feasibility 的首次入口例外", deployed_feasibility)
        self.assertNotIn("[阶段状态机与强门禁协议](", deployed_feasibility)
        self.assertNotIn("../源码水印与归属证据链执行卡.md", deployed_feasibility)
        self.assertIn(
            "[源码水印与归属证据链执行卡](../../../.trellis/workflow-docs/源码水印与归属证据链执行卡.md)",
            deployed_feasibility,
        )
        shared_feasibility_skill = (fixture / ".agents" / "skills" / "feasibility" / "SKILL.md").read_text(
            encoding="utf-8"
        )
        self.assertNotIn("personal profile 首次入口例外", shared_feasibility_skill)
        self.assertIn("不存在按 profile 跳过 feasibility 的首次入口例外", shared_feasibility_skill)
        design_skill = (fixture / ".agents" / "skills" / "design" / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn(
            "[需求变更管理执行卡](../../../.trellis/workflow-docs/需求变更管理执行卡.md)",
            design_skill,
        )
        self.assertNotIn(
            "[需求变更管理执行卡](.trellis/workflow-docs/需求变更管理执行卡.md)",
            design_skill,
        )
        finish_work_template = fixture / ".trellis" / "workflow-docs" / "finish-work-checklist-template.md"
        self.assertTrue(finish_work_template.exists(), "finish-work-checklist-template.md should be deployed")
        finish_work_template_text = finish_work_template.read_text(encoding="utf-8")
        self.assertIn("## 冻结验证矩阵", finish_work_template_text)
        self.assertIn("## 人工验证", finish_work_template_text)
        self.assertIn("## 同步结论", finish_work_template_text)

    def test_install_deployed_runtime_helpers_compile(self) -> None:
        fixture = self.create_fixture(include_opencode=True, include_codex=True)
        self.addCleanup(shutil.rmtree, fixture)

        install = self.install_workflow(fixture)
        self.assert_install_result_usable(install)

        python_targets = [
            fixture / ".trellis" / "scripts" / "task.py",
            fixture / ".trellis" / "scripts" / "common" / "tasks.py",
            fixture / ".trellis" / "scripts" / "common" / "task_queue.py",
            fixture / ".trellis" / "scripts" / "common" / "task_store.py",
            fixture / ".trellis" / "scripts" / "common" / "workflow_phase.py",
            fixture / ".claude" / "hooks" / "inject-workflow-state.py",
            fixture / ".claude" / "hooks" / "session-start.py",
            fixture / ".codex" / "hooks" / "inject-workflow-state.py",
            fixture / ".codex" / "hooks" / "session-start.py",
        ]
        python_targets.extend(fixture / ".trellis" / "scripts" / "workflow" / name for name in HELPER_SCRIPTS)

        result = subprocess.run(
            [PYTHON, "-m", "py_compile", *(str(path) for path in python_targets)],
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)

    def test_install_deployed_route_helper_survives_file_based_hook_import(self) -> None:
        fixture = self.create_fixture()
        self.addCleanup(shutil.rmtree, fixture)

        install = self.install_workflow(fixture)
        self.assert_install_result_usable(install)

        workflow_scripts = fixture / ".trellis" / "scripts" / "workflow"
        for helper_name in (
            "state_utils.py",
            "validators_core.py",
            "validators_gates.py",
            "embed_integrity.py",
        ):
            self.assertTrue(
                (workflow_scripts / helper_name).exists(),
                f"{helper_name} should be deployed with workflow-state.py",
            )

        task_dir = fixture / ".trellis" / "tasks" / "05-24-route-import-check"
        task_dir.mkdir(parents=True, exist_ok=True)
        (task_dir / "task.json").write_text(
            json.dumps(
                {
                    "id": "05-24-route-import-check",
                    "title": "route import check",
                    "status": "planning",
                    "children": [],
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        (task_dir / "workflow-state.json").write_text(
            json.dumps(
                {
                    "version": 1,
                    "stage": "feasibility",
                    "status": "in_progress",
                    "current_block": None,
                    "completed_blocks": [],
                    "checkpoints": {
                        "architecture_confirmed": False,
                        "context7_review_completed": False,
                        "execution_authorized": False,
                    },
                    "updated_at": "2026-05-24T00:00:00+00:00",
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        install_record_path = fixture / ".trellis" / "workflow-installed.json"
        install_record = json.loads(install_record_path.read_text(encoding="utf-8"))
        install_record.pop("patched_codex_skills", None)
        install_record_path.write_text(
            json.dumps(install_record, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        (fixture / ".trellis" / "scripts" / "common" / "active_task.py").write_text(
            "from pathlib import Path\n"
            "from types import SimpleNamespace\n\n"
            "def resolve_active_task(_repo_root):\n"
            "    return SimpleNamespace(task_path=None, stale=False, source='fixture')\n\n"
            "def resolve_task_ref(task_path, _repo_root):\n"
            "    return Path(task_path) if task_path else None\n",
            encoding="utf-8",
        )
        (fixture / ".claude" / "hooks" / "inject-subagent-context.py").write_text(
            "# [workflow-embed-patch:claude-subagent-gates]\n"
            "def _emit_blocked_subagent_output(*args, **kwargs):\n"
            "    return None\n"
            "# Strong-gate blocked this subagent dispatch.\n"
            "# current embedded workflow disables agent/subagent execution paths\n"
            "_emit_blocked_subagent_output(subagent_type, original_prompt, tool_input)\n",
            encoding="utf-8",
        )

        workflow_state_path = workflow_scripts / "workflow-state.py"
        spec = importlib.util.spec_from_file_location("embedded_workflow_state", workflow_state_path)
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            exit_code = module.cmd_route(
                argparse.Namespace(project_root=str(fixture), task_dir=str(task_dir))
            )
        self.assertEqual(exit_code, 0)
        route_data = json.loads(buffer.getvalue())
        self.assertEqual(route_data["action"], "reenter")
        self.assertEqual(route_data["stage"], "feasibility")

    def test_install_patches_opencode_inject_workflow_state_with_runtime_contract(self) -> None:
        fixture = self.create_fixture(include_opencode=True)
        self.addCleanup(shutil.rmtree, fixture)

        install = self.install_workflow(fixture)
        self.assert_install_result_usable(install)

        opencode_inject = (fixture / ".opencode" / "plugins" / "inject-workflow-state.js").read_text(encoding="utf-8")
        self.assertIn('import { execFileSync } from "child_process"', opencode_inject)
        self.assertIn('const PYTHON_CMD = process.env.TRELLIS_PYTHON || "python3"', opencode_inject)
        self.assertIn("ACTION_BREADCRUMB_KEYS", opencode_inject)
        self.assertIn("Stage: ${routeStage}", opencode_inject)
        self.assertNotIn("if (!rawStatus) return null", opencode_inject)
        self.assertIn("task.extraLines", opencode_inject)

    def test_install_session_start_patch_removes_legacy_tail_logic(self) -> None:
        fixture = self.create_fixture(include_opencode=True, include_codex=True)
        self.addCleanup(shutil.rmtree, fixture)

        install = self.install_workflow(fixture)
        self.assert_install_result_usable(install)

        for target in (
            fixture / ".claude" / "hooks" / "session-start.py",
            fixture / ".codex" / "hooks" / "session-start.py",
        ):
            content = target.read_text(encoding="utf-8")
            self.assertIn(SESSION_START_STRONG_GATE_PATCH_MARKER, content)
            self.assertIn("workflow-state.route", content)
            self.assertNotIn("Case 3: Task completed", content)
            self.assertNotIn("Status: READY", content)
            self.assertNotIn("Status: PLANNING", content)

    def test_nl_routing_maps_record_progress_to_finish_work(self) -> None:
        content = (COMMANDS_DIR / "install-workflow.py").read_text(encoding="utf-8")
        self.assertIn("| 记录、保存进度 | `/trellis:finish-work` |", content)
        self.assertNotIn("| 记录、保存进度 | `/trellis:record-session` |", content)

    def test_nl_routing_maps_implementation_entry_to_continue(self) -> None:
        content = (COMMANDS_DIR / "install-workflow.py").read_text(encoding="utf-8")
        self.assertIn("| 开始写代码、实现、开发、编码、动手、修这个功能、开始改代码 | `/trellis:continue` |", content)
        self.assertIn("没有对称的 `/trellis:implementation` 命令", content)

    def test_upgrade_merge_removes_ready_autocontinue_prompt_residue(self) -> None:
        fixture = self.create_fixture(include_opencode=True, include_codex=True)
        self.addCleanup(shutil.rmtree, fixture)

        install = self.install_workflow(fixture)
        self.assertEqual(install.returncode, 0, msg=install.stdout + install.stderr)

        for target in (
            fixture / ".claude" / "hooks" / "session-start.py",
            fixture / ".codex" / "hooks" / "session-start.py",
            fixture / ".opencode" / "lib" / "session-utils.js",
        ):
            content = target.read_text(encoding="utf-8")
            target.write_text(content + "\n" + LEGACY_READY_AUTOCONTINUE_LINE + "\n", encoding="utf-8")

        (fixture / ".trellis" / ".version").write_text("2.1.0\n", encoding="utf-8")

        check = self.run_script(
            UPGRADE_SCRIPT,
            "--check",
            "--project-root",
            str(fixture),
            env=self.latest_env_for(fixture),
        )
        self.assertNotEqual(check.returncode, 0)
        self.assertIn("READY 自动续跑提示", check.stdout + check.stderr)

        merge = self.run_script(
            UPGRADE_SCRIPT,
            "--merge",
            "--project-root",
            str(fixture),
            env=self.latest_env_for(fixture),
        )
        self.assertEqual(merge.returncode, 0, msg=merge.stdout + merge.stderr)

        for target in (
            fixture / ".claude" / "hooks" / "session-start.py",
            fixture / ".codex" / "hooks" / "session-start.py",
            fixture / ".opencode" / "lib" / "session-utils.js",
        ):
            content = target.read_text(encoding="utf-8")
            self.assertNotIn(LEGACY_READY_AUTOCONTINUE_LINE, content)
            self.assertIn(STRONG_GATE_READY_GUIDANCE_LINE, content)

    def test_cli_matrix_treats_record_session_as_legacy_only(self) -> None:
        matrix = (COMMANDS_DIR.parent / "CLI原生适配边界矩阵.md").read_text(encoding="utf-8")
        self.assertNotIn("continue / finish-work / record-session ✅", matrix)
        self.assertNotIn("workflow 分发的 `record-session` 终态命令/skill", matrix)
        self.assertNotIn("`record-session` 基线入口 + workflow patch", matrix)

    def test_full_walkthrough_closeout_example_keeps_delivery_before_native_finish_work(self) -> None:
        walkthrough = (COMMANDS_DIR.parent / "完整流程演练.md").read_text(encoding="utf-8")
        self.assertIn("delivery → Trellis 原生 `/finish-work`", walkthrough)
        self.assertIn("再通过 `/trellis:delivery` 确认验收结论和交付物", walkthrough)
        self.assertIn("最后进入 Trellis 原生 `/finish-work` 执行终态归档与会话记录", walkthrough)

    def test_delivery_docs_do_not_reference_missing_skills(self) -> None:
        docs_to_check = [
            COMMANDS_DIR / "delivery.md",
            COMMANDS_DIR.parent / "命令映射.md",
            COMMANDS_DIR.parent / "多CLI通用新项目完整流程演练.md",
        ]
        forbidden = ("requesting-code-review", "changelog-generator")
        for path in docs_to_check:
            content = path.read_text(encoding="utf-8")
            for skill_name in forbidden:
                self.assertNotIn(skill_name, content, msg=f"{path} still references missing skill {skill_name}")

    def test_design_and_research_docs_do_not_reference_invalid_exa_type_or_missing_skills(self) -> None:
        docs_to_check = [
            COMMANDS_DIR / "design.md",
            COMMANDS_DIR / "plan.md",
            COMMANDS_DIR / "feasibility.md",
            COMMANDS_DIR.parent / "工作流总纲.md",
        ]
        forbidden_snippets = (
            "exa_web_search_advanced_exa(type=deep-reasoning)",
            "api-design-principles",
            "postgresql-table-design",
        )
        for path in docs_to_check:
            content = path.read_text(encoding="utf-8")
            for snippet in forbidden_snippets:
                self.assertNotIn(snippet, content, msg=f"{path} still references invalid routing snippet {snippet}")

    def test_install_removes_legacy_three_phase_workflow_contract(self) -> None:
        fixture = self.create_fixture()
        self.addCleanup(shutil.rmtree, fixture)
        (fixture / ".trellis" / "workflow.md").write_text(LEGACY_PHASE_WORKFLOW_CONTENT, encoding="utf-8")

        install = self.install_workflow(fixture)
        self.assertEqual(install.returncode, 0, msg=install.stdout + install.stderr)

        workflow_doc_text = (fixture / ".trellis" / "workflow.md").read_text(encoding="utf-8")
        self.assertNotIn("Phase 1: Plan    → figure out what to do", workflow_doc_text)
        self.assertNotIn("[workflow-state:planning]", workflow_doc_text)
        self.assertIn("feasibility → brainstorm → design", workflow_doc_text)
        self.assertIn("## Customizing Trellis (for forks)", workflow_doc_text)
        deployed_design = (fixture / ".claude" / "commands" / "trellis" / "design.md").read_text(encoding="utf-8")
        self.assertIn("context7-review.md", deployed_design)
        self.assertIn("Context7", deployed_design)
        self.assertIn("context7_review_completed", deployed_design)
        self.assertIn(f"`{TRELLIS_LIBRARY_CLI} assemble`", deployed_design)
        self.assertNotIn("`trellis-library/cli.py assemble`", deployed_design)
        deployed_plan = (fixture / ".claude" / "commands" / "trellis" / "plan.md").read_text(encoding="utf-8")
        self.assertIn("## 任务粒度判断", deployed_plan)
        self.assertIn("granularity_decision", deployed_plan)
        self.assertIn(f"从宿主仓库中的 `{TRELLIS_LIBRARY_DIR}` 选择并导入", deployed_plan)
        self.assertNotIn("从 `trellis-library` 选择并导入", deployed_plan)

    def test_install_patches_task_views_to_use_stage_based_status(self) -> None:
        fixture = self.create_fixture(include_codex=True)
        self.addCleanup(shutil.rmtree, fixture)

        install = self.install_workflow(fixture)

        self.assertEqual(install.returncode, 0, msg=install.stdout + install.stderr)
        tasks_py = (fixture / ".trellis" / "scripts" / "common" / "tasks.py").read_text(encoding="utf-8")
        task_queue_py = (fixture / ".trellis" / "scripts" / "common" / "task_queue.py").read_text(encoding="utf-8")
        task_py = (fixture / ".trellis" / "scripts" / "task.py").read_text(encoding="utf-8")
        self.assertIn("# [workflow-embed-patch:strong-gate-task-status-view]", tasks_py)
        self.assertIn('display_status, display_extra = _display_status(task_dir, data)', tasks_py)
        self.assertIn("_workflow_state_summary(state)", tasks_py)
        self.assertIn('stage_status = state.get("status") or state.get("stage_status")', tasks_py)
        self.assertIn('if raw_status in TERMINAL_TASK_STATUSES:', tasks_py)
        self.assertIn('return "completed", None', tasks_py)
        self.assertNotIn("needs-init", tasks_py)
        self.assertNotIn("_route_status_summary(task_dir)", tasks_py)
        self.assertNotIn("_module_cache", tasks_py)
        self.assertNotIn("cmd_route(", tasks_py)
        self.assertNotIn("subprocess.run(", tasks_py)
        self.assertIn('data["_workflow_display_extra"] = display_extra', tasks_py)
        self.assertIn("# [workflow-embed-patch:strong-gate-task-status-view]", task_queue_py)
        self.assertIn('return list_tasks_by_status(None, repo_root)', task_queue_py)
        self.assertNotIn("Still flip task.json status: planning → in_progress", task_py)
        self.assertIn("Strong-gate mode keeps workflow-state.py route as the only stage authority.", task_py)

    def test_install_task_view_keeps_completed_status_when_workflow_state_file_remains(self) -> None:
        fixture = self.create_fixture(include_codex=True)
        self.addCleanup(shutil.rmtree, fixture)

        install = self.install_workflow(fixture)
        self.assertEqual(install.returncode, 0, msg=install.stdout + install.stderr)

        task_dir = fixture / ".trellis" / "tasks" / "05-23-completed-task"
        task_dir.mkdir(parents=True, exist_ok=True)
        (task_dir / "task.json").write_text(
            json.dumps(
                {
                    "id": "completed-task",
                    "name": "completed-task",
                    "title": "Completed Task",
                    "status": "completed",
                    "assignee": "xzc",
                    "priority": "P2",
                    "children": [],
                    "parent": None,
                    "package": None,
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        (task_dir / "workflow-state.json").write_text(
            json.dumps(
                {
                    "version": 1,
                    "stage": "check",
                    "status": "in_progress",
                    "current_block": None,
                    "completed_blocks": [],
                    "checkpoints": {},
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

        scripts_dir = fixture / ".trellis" / "scripts"
        common_dir = scripts_dir / "common"
        shutil.copy(REPO_ROOT / ".trellis" / "scripts" / "common" / "io.py", common_dir / "io.py")
        shutil.copy(REPO_ROOT / ".trellis" / "scripts" / "common" / "paths.py", common_dir / "paths.py")
        shutil.copy(REPO_ROOT / ".trellis" / "scripts" / "common" / "types.py", common_dir / "types.py")
        sys.path.insert(0, str(scripts_dir))
        self.addCleanup(lambda: sys.path.remove(str(scripts_dir)) if str(scripts_dir) in sys.path else None)
        sys.modules.pop("common", None)
        sys.modules.pop("common.io", None)
        sys.modules.pop("common.paths", None)
        sys.modules.pop("common.tasks", None)
        sys.modules.pop("common.types", None)

        import common.tasks as tasks_module

        loaded = tasks_module.load_task(task_dir)
        self.assertIsNotNone(loaded)
        self.assertEqual(loaded.status, "completed")
        self.assertIsNone(loaded.raw.get("_workflow_display_extra"))

    def test_install_personal_profile_keeps_ownership_cards_and_helpers(self) -> None:
        fixture = self.create_fixture()
        self.addCleanup(shutil.rmtree, fixture)

        install = self.install_workflow(fixture, "--profile", "personal")

        self.assertEqual(install.returncode, 0, msg=install.stdout + install.stderr)
        record_data = json.loads((fixture / ".trellis" / "workflow-installed.json").read_text(encoding="utf-8"))
        self.assertEqual(record_data["profile"], "personal")
        self.assertEqual(
            record_data["scripts"],
            [name for name in HELPER_SCRIPTS if name not in {"delivery-control-validate.py"}],
        )
        self.assertEqual(
            record_data["execution_cards"],
            ["需求变更管理执行卡.md", "源码水印与归属证据链执行卡.md"],
        )

        workflow_scripts = fixture / ".trellis" / "scripts" / "workflow"
        self.assertTrue((workflow_scripts / "workflow-state.py").exists())
        self.assertFalse((workflow_scripts / "delivery-control-validate.py").exists())
        self.assertTrue((workflow_scripts / "ownership-proof-validate.py").exists())
        self.assertTrue((workflow_scripts / "source-watermark-guard.py").exists())

        workflow_docs = fixture / ".trellis" / "workflow-docs"
        self.assertTrue((workflow_docs / "需求变更管理执行卡.md").exists())
        self.assertTrue((workflow_docs / "源码水印与归属证据链执行卡.md").exists())

        deployed_delivery = (fixture / ".claude" / "commands" / "trellis" / "delivery.md").read_text(encoding="utf-8")
        self.assertIn("源码水印与归属证据链执行卡", deployed_delivery)
        self.assertIn("ownership-proof-validate.py", deployed_delivery)
        self.assertIn("source-watermark-guard.py", deployed_delivery)

    def test_upgrade_merge_respects_personal_profile_for_commands_and_codex_skills(self) -> None:
        fixture = self.create_fixture(include_codex=True)
        self.addCleanup(shutil.rmtree, fixture)

        install = self.install_workflow(fixture, "--profile", "personal")
        self.assertEqual(install.returncode, 0, msg=install.stdout + install.stderr)
        (fixture / ".trellis" / ".version").write_text("2.1.0\n", encoding="utf-8")

        merge = self.run_script(
            UPGRADE_SCRIPT,
            "--merge",
            "--project-root",
            str(fixture),
            env=self.latest_env_for(fixture),
        )

        self.assertEqual(merge.returncode, 0, msg=merge.stdout + merge.stderr)
        delivery_cmd = (fixture / ".claude" / "commands" / "trellis" / "delivery.md").read_text(encoding="utf-8")
        delivery_skill = (fixture / ".agents" / "skills" / "delivery" / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("源码水印与归属证据链执行卡", delivery_cmd)
        self.assertIn("ownership-proof-validate.py", delivery_cmd)
        self.assertIn("source-watermark-guard.py", delivery_cmd)
        self.assertIn("源码水印与归属证据链执行卡", delivery_skill)
        self.assertIn("ownership-proof-validate.py", delivery_skill)
        self.assertIn("source-watermark-guard.py", delivery_skill)

    def test_install_patches_finish_work_for_opencode_and_codex(self) -> None:
        fixture = self.create_fixture(include_opencode=True, include_codex=True)
        self.addCleanup(shutil.rmtree, fixture)

        install = self.install_workflow(fixture)

        self.assertEqual(install.returncode, 0, msg=install.stdout + install.stderr)
        opencode_finish_work = fixture / ".opencode" / "commands" / "trellis" / "finish-work.md"
        codex_finish_work = fixture / ".agents" / "skills" / "trellis-finish-work" / "SKILL.md"
        opencode_parallel = fixture / ".opencode" / "commands" / "trellis" / "parallel.md"
        codex_parallel = fixture / ".agents" / "skills" / "parallel" / "SKILL.md"
        opencode_text = opencode_finish_work.read_text(encoding="utf-8")
        codex_text = codex_finish_work.read_text(encoding="utf-8")
        self.assertIn(FINISH_WORK_MARKER, opencode_text)
        self.assertIn(FINISH_WORK_MARKER, codex_text)
        self.assertNotIn("pnpm test", opencode_text)
        self.assertNotIn("pnpm test", codex_text)
        # 补丁已条件化：验证质量平台门禁口径，不再硬断言特定 sonar 内容
        self.assertIn("质量平台门禁", opencode_text)
        self.assertIn("质量平台门禁", codex_text)
        self.assertFalse(opencode_parallel.exists())
        self.assertFalse(codex_parallel.exists())

    def test_install_patches_codex_continue_skill_phase_router(self) -> None:
        fixture = self.create_fixture(include_codex=True)
        self.addCleanup(shutil.rmtree, fixture)

        install = self.install_workflow(fixture)

        self.assertEqual(install.returncode, 0, msg=install.stdout + install.stderr)
        start_skill = fixture / ".agents" / "skills" / "trellis-continue" / "SKILL.md"
        start_text = start_skill.read_text(encoding="utf-8")
        self.assertIn("## Workflow Phase Router Patch `[AI]`", start_text)
        self.assertIn("Re-enter the current workflow stage through the workflow router", start_text)
        self.assertIn("stay in the current phase-router entry", start_text)
        self.assertIn("Do not assume a public `implementation` skill exists.", start_text)
        self.assertIn("source-watermark-guard.py", start_text)
        self.assertIn("If `target=finish-work`, use `trellis-finish-work`.", start_text)
        self.assertNotIn("Steps 1-4 替换说明", start_text)
        self.assertNotIn("docs/workflows/新项目开发工作流/commands/shell", start_text)
        self.assertNotIn("<WORKFLOW_DIR>/commands/shell", start_text)
        self.assertNotIn("figures out which phase/step to pick up at", start_text)
        self.assertEqual(
            (fixture / ".agents" / "skills" / ".backup-original" / "trellis-continue" / "SKILL.md").read_text(
                encoding="utf-8"
            ),
            BASELINE_TRELLIS_CONTINUE_SKILL_CONTENT,
        )

    def test_install_deploys_check_command_with_review_gate_decision_and_delivery_default(self) -> None:
        fixture = self.create_fixture(include_opencode=True, include_codex=True)
        self.addCleanup(shutil.rmtree, fixture)

        install = self.install_workflow(fixture)

        self.assertEqual(install.returncode, 0, msg=install.stdout + install.stderr)
        opencode_check = (fixture / ".opencode" / "commands" / "trellis" / "check.md").read_text(encoding="utf-8")
        codex_check = (fixture / ".agents" / "skills" / "check" / "SKILL.md").read_text(encoding="utf-8")
        for content in (opencode_check, codex_check):
            self.assertIn("## Review-Gate Decision", content)
            self.assertIn("`review_gate_decision`", content)
            self.assertIn("`explicit_user_review_gate_request`", content)
            self.assertIn("| 基本合规，可直接进入交付收口 | `/trellis:delivery` |", content)

    def test_install_patches_codex_session_start_to_remove_legacy_startup_semantics(self) -> None:
        fixture = self.create_fixture(include_codex=True)
        self.addCleanup(shutil.rmtree, fixture)

        install = self.install_workflow(fixture, "--cli", "codex")

        self.assertEqual(install.returncode, 0, msg=install.stdout + install.stderr)
        combined = install.stdout + install.stderr
        self.assertIn(
            "[Codex] session-start.py 强门禁补丁已应用",
            combined,
        )
        codex_session_start = (fixture / ".codex" / "hooks" / "session-start.py").read_text(encoding="utf-8")
        self.assertIn(SESSION_START_STRONG_GATE_PATCH_MARKER, codex_session_start)
        self.assertIn("workflow-state.route", codex_session_start)
        record = json.loads((fixture / ".trellis" / "workflow-installed.json").read_text(encoding="utf-8"))
        self.assertEqual(
            record["critical_runtime_patches"],
            [
                "inject-workflow-state",
                "task-start-strong-gate",
                "task-create-preserve-active",
                "task-status-view-strong-gate",
                "workflow-phase-strong-gate",
            ],
        )

    def test_patch_session_start_no_task_guidance_removes_research_subagent_hint(self) -> None:
        fixture = Path(tempfile.mkdtemp(prefix="session-start-no-task-guidance-"))
        self.addCleanup(shutil.rmtree, fixture)
        session_start = fixture / ".claude" / "hooks" / "session-start.py"
        session_start.parent.mkdir(parents=True, exist_ok=True)
        session_start.write_text(
            "def _get_task_status():\n"
            "    active = type('Active', (), {'source': 'none', 'task_path': None})()\n"
            "    if not active.task_path:\n"
            "        return (\n"
            "            \"Status: NO ACTIVE TASK\\n\"\n"
            "            f\"Source: {active.source}\\n\"\n"
            "            \"Next-Action: After the user describes their intent, load skill `trellis-brainstorm` \"\n"
            "            \"to clarify requirements and create a task via `python3 ./.trellis/scripts/task.py create`.\\n\"\n"
            "            \"Research reminder: for research-heavy tasks (comparing tools, reading external docs, \"\n"
            "            \"cross-platform surveys), spawn `trellis-research` sub-agents via the Task tool — \"\n"
            "            \"they persist findings to `{TASK_DIR}/research/*.md` and keep main context clean. \"\n"
            "            \"Do NOT do 10+ inline WebFetch/WebSearch in the main conversation.\\n\"\n"
            "        )\n",
            encoding="utf-8",
        )

        install_spec = importlib.util.spec_from_file_location("install_workflow", INSTALL_SCRIPT)
        self.assertIsNotNone(install_spec)
        self.assertIsNotNone(install_spec.loader)
        install_module = importlib.util.module_from_spec(install_spec)
        install_spec.loader.exec_module(install_module)

        patched = install_module.patch_session_start_no_task_guidance(fixture, dry_run=False)
        self.assertTrue(patched)
        claude_session_start = session_start.read_text(encoding="utf-8")
        self.assertNotIn("spawn `trellis-research` sub-agents via the Task tool", claude_session_start)
        self.assertIn("keep research in the main session for this embedded workflow", claude_session_start)
        self.assertIn("persist durable findings directly to `{TASK_DIR}/research/*.md`", claude_session_start)

    def test_patch_claude_inject_subagent_context_blocks_dispatch(self) -> None:
        fixture = Path(tempfile.mkdtemp(prefix="claude-inject-subagent-context-"))
        self.addCleanup(shutil.rmtree, fixture)
        hook_path = fixture / ".claude" / "hooks" / "inject-subagent-context.py"
        hook_path.parent.mkdir(parents=True, exist_ok=True)
        hook_path.write_text(
            "import json\n"
            "import sys\n"
            "AGENT_IMPLEMENT = \"trellis-implement\"\n"
            "AGENT_CHECK = \"trellis-check\"\n"
            "AGENT_RESEARCH = \"trellis-research\"\n"
            "AGENTS_ALL = (AGENT_IMPLEMENT, AGENT_CHECK, AGENT_RESEARCH)\n"
            "\n"
            "def main():\n"
            "    subagent_type = \"trellis-research\"\n"
            "    original_prompt = \"research\"\n"
            "    tool_input = {\"prompt\": original_prompt}\n"
            "    # Only handle subagent types we care about\n"
            "    if subagent_type not in AGENTS_ALL:\n"
            "        sys.exit(0)\n"
            "\n"
            "    # Find repo root\n"
            "    repo_root = \"/tmp\"\n"
            "\n"
            "if __name__ == \"__main__\":\n"
            "    main()\n",
            encoding="utf-8",
        )

        install_spec = importlib.util.spec_from_file_location("install_workflow", INSTALL_SCRIPT)
        self.assertIsNotNone(install_spec)
        self.assertIsNotNone(install_spec.loader)
        install_module = importlib.util.module_from_spec(install_spec)
        install_spec.loader.exec_module(install_module)

        patched = install_module.patch_claude_inject_subagent_context(fixture, dry_run=False)
        self.assertTrue(patched)
        patched_text = hook_path.read_text(encoding="utf-8")
        self.assertIn("# [workflow-embed-patch:claude-subagent-gates]", patched_text)
        self.assertIn("Strong-gate blocked this subagent dispatch.", patched_text)
        self.assertIn("current embedded workflow disables agent/subagent execution paths", patched_text)

    def test_upgrade_check_allows_missing_unwired_codex_session_start(self) -> None:
        fixture = self.create_fixture(include_codex=True)
        self.addCleanup(shutil.rmtree, fixture)

        install = self.install_workflow(fixture, "--cli", "codex")
        self.assertEqual(install.returncode, 0, msg=install.stdout + install.stderr)

        (fixture / ".codex" / "hooks" / "session-start.py").unlink()

        result = self.run_script(
            UPGRADE_SCRIPT,
            "--check",
            "--project-root",
            str(fixture),
            "--cli",
            "codex",
            env=self.latest_env_for(fixture),
        )

        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        self.assertIn("session-start.py 未接线", result.stdout)
        self.assertNotIn("session-start.py 缺失", result.stdout)

    def test_install_patches_trellis_meta_references_with_strong_gate_guidance(self) -> None:
        fixture = self.create_fixture(include_opencode=True, include_codex=True)
        self.addCleanup(shutil.rmtree, fixture)

        stale_files = [
            fixture / ".agents" / "skills" / "trellis-meta" / "references" / "local-architecture" / "workflow.md",
            fixture / ".agents" / "skills" / "trellis-meta" / "references" / "local-architecture" / "context-injection.md",
            fixture / ".agents" / "skills" / "trellis-meta" / "references" / "platform-files" / "hooks-and-settings.md",
            fixture / ".agents" / "skills" / "trellis-meta" / "references" / "customize-local" / "change-hooks.md",
            fixture / ".agents" / "skills" / "trellis-meta" / "references" / "customize-local" / "change-workflow.md",
            fixture / ".claude" / "skills" / "trellis-meta" / "references" / "local-architecture" / "workflow.md",
            fixture / ".claude" / "skills" / "trellis-meta" / "references" / "local-architecture" / "context-injection.md",
            fixture / ".claude" / "skills" / "trellis-meta" / "references" / "platform-files" / "hooks-and-settings.md",
            fixture / ".claude" / "skills" / "trellis-meta" / "references" / "customize-local" / "change-hooks.md",
            fixture / ".claude" / "skills" / "trellis-meta" / "references" / "customize-local" / "change-workflow.md",
            fixture / ".opencode" / "skills" / "trellis-meta" / "references" / "local-architecture" / "workflow.md",
            fixture / ".opencode" / "skills" / "trellis-meta" / "references" / "local-architecture" / "context-injection.md",
            fixture / ".opencode" / "skills" / "trellis-meta" / "references" / "platform-files" / "hooks-and-settings.md",
            fixture / ".opencode" / "skills" / "trellis-meta" / "references" / "customize-local" / "change-hooks.md",
            fixture / ".opencode" / "skills" / "trellis-meta" / "references" / "customize-local" / "change-workflow.md",
        ]
        for path in stale_files:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("# stale\nlegacy status routing\n", encoding="utf-8")

        install = self.install_workflow(fixture)

        self.assertEqual(install.returncode, 0, msg=install.stdout + install.stderr)
        for path in stale_files:
            content = path.read_text(encoding="utf-8")
            self.assertIn(TRELLIS_META_PATCH_MARKER, content, msg=str(path))
            self.assertNotIn("legacy status routing", content, msg=str(path))
        shared_workflow_ref = (
            fixture / ".agents" / "skills" / "trellis-meta" / "references" / "local-architecture" / "workflow.md"
        ).read_text(encoding="utf-8")
        self.assertIn("workflow-state.py route", shared_workflow_ref)
        self.assertIn("route metadata", shared_workflow_ref)
        self.assertIn("delivery -> native finish-work", shared_workflow_ref)
        opencode_change_hooks = (
            fixture / ".opencode" / "skills" / "trellis-meta" / "references" / "customize-local" / "change-hooks.md"
        ).read_text(encoding="utf-8")
        self.assertIn(".opencode/package.json", opencode_change_hooks)
        self.assertIn(".opencode/plugins/", opencode_change_hooks)
        codex_change_hooks = (
            fixture / ".agents" / "skills" / "trellis-meta" / "references" / "customize-local" / "change-hooks.md"
        ).read_text(encoding="utf-8")
        self.assertIn(".codex/hooks.json -> .codex/hooks/inject-workflow-state.py", codex_change_hooks)

    def test_install_patches_platform_brainstorm_skills_away_from_trellis_start(self) -> None:
        fixture = self.create_fixture(include_opencode=True, include_codex=True)
        self.addCleanup(shutil.rmtree, fixture)

        stale_skill = """---
name: trellis-brainstorm
description: stale brainstorm
---

## When to Use

Triggered from /trellis:start when the user describes a development task, especially when:

## Related Commands

| Command | When to Use |
|---------|-------------|
| `/trellis:start` | Entry point that triggers brainstorm |
| `/trellis:finish-work` | After implementation is complete |
| `trellis-update-spec` skill | If new patterns emerge during work |
"""
        shared_stale_skill = """---
name: trellis-brainstorm
description: stale brainstorm
---

## When to Use

Triggered from `start` (Trellis command) when the user describes a development task, especially when:

## Related Commands

| Command | When to Use |
|---------|-------------|
| ``start` (Trellis command)` | Entry point that triggers brainstorm |
| ``finish-work` (Trellis command)` | After implementation is complete |
| ``update-spec` (Trellis command)` | If new patterns emerge during work |
"""
        for path in [
            fixture / ".claude" / "skills" / "trellis-brainstorm" / "SKILL.md",
            fixture / ".opencode" / "skills" / "trellis-brainstorm" / "SKILL.md",
        ]:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(stale_skill, encoding="utf-8")
        shared_path = fixture / ".agents" / "skills" / "trellis-brainstorm" / "SKILL.md"
        shared_path.parent.mkdir(parents=True, exist_ok=True)
        shared_path.write_text(shared_stale_skill, encoding="utf-8")

        install = self.install_workflow(fixture)

        self.assertEqual(install.returncode, 0, msg=install.stdout + install.stderr)
        for path in [
            fixture / ".claude" / "skills" / "trellis-brainstorm" / "SKILL.md",
            fixture / ".opencode" / "skills" / "trellis-brainstorm" / "SKILL.md",
        ]:
            content = path.read_text(encoding="utf-8")
            self.assertIn("/trellis:brainstorm", content)
            self.assertIn("/trellis:continue", content)
            self.assertIn("All new implementation work must still pass `/trellis:feasibility` first", content)
            self.assertIn("assessment.md", content)
            self.assertIn("assessment.md", content)
            self.assertNotIn("Triggered from /trellis:start", content)
            self.assertNotIn("| `/trellis:start` | Entry point that triggers brainstorm |", content)
        shared_content = shared_path.read_text(encoding="utf-8")
        self.assertIn("Triggered when the installed workflow routes into brainstorm", shared_content)
        self.assertIn("All new implementation work must still pass `/trellis:feasibility` first", shared_content)
        self.assertIn("assessment.md", shared_content)
        self.assertIn("trellis-continue", shared_content)
        self.assertNotIn("Triggered from `start` (Trellis command)", shared_content)
        self.assertNotIn("| ``start` (Trellis command)` | Entry point that triggers brainstorm |", shared_content)

    def test_install_patches_cross_layer_guide_check_entry(self) -> None:
        fixture = self.create_fixture()
        self.addCleanup(shutil.rmtree, fixture)

        guide_path = fixture / ".trellis" / "spec" / "guides" / "cross-layer-thinking-guide.md"
        guide_path.parent.mkdir(parents=True, exist_ok=True)
        guide_path.write_text(
            "# Cross-Layer Thinking Guide\n\n"
            "## Cross-Platform Template Consistency\n\n"
            "- [ ] Run `/trellis:check-cross-layer` to verify nothing was missed\n",
            encoding="utf-8",
        )

        install = self.install_workflow(fixture)

        self.assertEqual(install.returncode, 0, msg=install.stdout + install.stderr)
        patched = guide_path.read_text(encoding="utf-8")
        self.assertIn("/trellis:check` and specify the cross-layer scope manually", patched)
        self.assertNotIn("/trellis:check-cross-layer", patched)

    def test_install_migrates_legacy_agents_to_trellis_naming(self) -> None:
        fixture = self.create_fixture(include_opencode=True, include_codex=True, use_latest_trellis_baseline=False)
        self.addCleanup(shutil.rmtree, fixture)

        install = self.install_workflow(fixture)

        self.assertEqual(install.returncode, 0, msg=install.stdout + install.stderr)
        self.assertTrue((fixture / ".claude" / "agents" / "trellis-research.md").exists())
        self.assertFalse((fixture / ".claude" / "agents" / "research.md").exists())
        self.assertTrue((fixture / ".opencode" / "agents" / "trellis-research.md").exists())
        self.assertFalse((fixture / ".opencode" / "agents" / "research.md").exists())
        self.assertTrue((fixture / ".codex" / "agents" / "trellis-research.toml").exists())
        self.assertFalse((fixture / ".codex" / "agents" / "research.toml").exists())

    def test_install_keeps_codex_native_agents_unchanged(self) -> None:
        fixture = self.create_fixture(include_codex=True)
        self.addCleanup(shutil.rmtree, fixture)

        install = self.install_workflow(fixture)

        self.assertEqual(install.returncode, 0, msg=install.stdout + install.stderr)
        codex_trellis_agents = fixture / ".codex" / "agents"
        self.assertEqual(
            (codex_trellis_agents / "trellis-research.toml").read_text(encoding="utf-8"),
            BASELINE_CODEX_RESEARCH_TOML,
        )
        self.assertEqual(
            (codex_trellis_agents / "trellis-implement.toml").read_text(encoding="utf-8"),
            BASELINE_CODEX_IMPLEMENT_TOML,
        )
        self.assertEqual(
            (codex_trellis_agents / "trellis-check.toml").read_text(encoding="utf-8"),
            BASELINE_CODEX_CHECK_TOML,
        )
        self.assertFalse((codex_trellis_agents / ".backup-original").exists())
        self.assertFalse((fixture / ".trellis" / ".backup-original" / "codex-agents").exists())

    def test_install_keeps_native_research_agents_in_target_project(self) -> None:
        fixture = self.create_fixture(include_opencode=True, include_codex=True)
        self.addCleanup(shutil.rmtree, fixture)

        install = self.install_workflow(fixture)

        self.assertEqual(install.returncode, 0, msg=install.stdout + install.stderr)
        claude_research = (fixture / ".claude" / "agents" / "trellis-research.md").read_text(encoding="utf-8")
        opencode_research = (fixture / ".opencode" / "agents" / "trellis-research.md").read_text(encoding="utf-8")
        codex_research = (fixture / ".codex" / "agents" / "trellis-research.toml").read_text(encoding="utf-8")

        self.assertEqual(claude_research, BASELINE_AGENT_RESEARCH_MD)
        self.assertEqual(opencode_research, BASELINE_AGENT_RESEARCH_MD)
        self.assertEqual(codex_research, BASELINE_CODEX_RESEARCH_TOML)

    def test_upgrade_check_ignores_native_research_agent_content_drift(self) -> None:
        fixture = self.create_fixture(include_opencode=True, include_codex=True)
        self.addCleanup(shutil.rmtree, fixture)

        install = self.install_workflow(fixture)
        self.assertEqual(install.returncode, 0, msg=install.stdout + install.stderr)

        claude_research = fixture / ".claude" / "agents" / "trellis-research.md"
        claude_research.write_text("# drifted research\n", encoding="utf-8")
        (fixture / ".trellis" / ".version").write_text("2.1.0\n", encoding="utf-8")

        result = self.run_script(
            UPGRADE_SCRIPT,
            "--check",
            "--project-root",
            str(fixture),
            env=self.latest_env_for(fixture),
        )

        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        self.assertNotIn("agent 内容漂移", result.stdout)

    def test_upgrade_merge_does_not_rewrite_native_research_agent(self) -> None:
        fixture = self.create_fixture(include_opencode=True, include_codex=True)
        self.addCleanup(shutil.rmtree, fixture)

        install = self.install_workflow(fixture)
        self.assertEqual(install.returncode, 0, msg=install.stdout + install.stderr)

        claude_research = fixture / ".claude" / "agents" / "trellis-research.md"
        claude_research.write_text("# drifted research\n", encoding="utf-8")
        (fixture / ".trellis" / ".version").write_text("2.1.0\n", encoding="utf-8")

        result = self.run_script(
            UPGRADE_SCRIPT,
            "--merge",
            "--project-root",
            str(fixture),
            env=self.latest_env_for(fixture),
        )

        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        updated = claude_research.read_text(encoding="utf-8")
        self.assertEqual(updated, "# drifted research\n")

    def test_install_patches_finish_work_when_test_coverage_heading_is_missing(self) -> None:
        fixture = self.create_fixture()
        self.addCleanup(shutil.rmtree, fixture)
        finish_work = fixture / ".claude" / "commands" / "trellis" / "finish-work.md"
        finish_work.write_text(BASELINE_FINISH_WORK_WITHOUT_TEST_COVERAGE_CONTENT, encoding="utf-8")

        install = self.install_workflow(fixture)

        self.assertEqual(install.returncode, 0, msg=install.stdout + install.stderr)
        patched_text = finish_work.read_text(encoding="utf-8")
        self.assertIn(FINISH_WORK_MARKER, patched_text)
        self.assertIn("### 2. close-out 基线路径", patched_text)
        self.assertNotIn("pnpm lint", patched_text)

    def test_install_imports_requirements_foundation_and_removes_bootstrap_task(self) -> None:
        fixture = self.create_fixture()
        self.addCleanup(shutil.rmtree, fixture)

        install = self.install_workflow(fixture)

        self.assertEqual(install.returncode, 0, msg=install.stdout + install.stderr)
        lock_path = fixture / ".trellis" / "library-lock.yaml"
        self.assertTrue(lock_path.exists(), "library-lock.yaml should be created during installation")
        lock_text = lock_path.read_text(encoding="utf-8")
        self.assertIn("pack.requirements-discovery-foundation", lock_text)
        self.assertIn("spec.universal-domains.product-and-requirements.problem-definition", lock_text)
        self.assertIn("spec.universal-domains.project-governance.readme-governance", lock_text)
        readme_governance = (
            fixture
            / ".trellis"
            / "spec"
            / "universal-domains"
            / "project-governance"
            / "readme-governance"
            / "normative-rules.md"
        )
        self.assertTrue(readme_governance.exists(), "README governance spec should be imported during installation")
        readme_governance_text = readme_governance.read_text(encoding="utf-8")
        self.assertIn("README.md", readme_governance_text)
        examples_dir = (
            fixture
            / ".trellis"
            / "library-assets"
            / "examples"
            / "universal-domains"
            / "product-and-requirements"
        )
        self.assertTrue(examples_dir.exists(), "requirements foundation example directory should be imported")
        assembled_example = (
            fixture
            / ".trellis"
            / "library-assets"
            / "examples"
            / "assembled-packs"
            / "requirements-discovery-foundation.md"
        )
        self.assertTrue(assembled_example.exists(), "assembled-pack example should be imported")
        self.assertIn("README.en.md", readme_governance_text)
        self.assertIn("default Simplified Chinese entry", readme_governance_text)
        self.assertFalse((fixture / ".trellis" / "tasks" / "00-bootstrap-guidelines").exists())
        self.assertIn("初始 spec 基线已导入", install.stdout)
        self.assertIn(f"{TRELLIS_LIBRARY_CLI} assemble", install.stdout)
        self.assertNotIn("再使用 trellis-library/cli.py assemble 为当前项目补充真实 spec 集合", install.stdout)
        self.assertIn("Trellis bootstrap 任务已删除", install.stdout)
        self.assertIn("README.en.md", install.stdout)

    def test_managed_audit_extra_specs_include_requirements_example_assets(self) -> None:
        extras = build_managed_audit_extra_specs(["claude", "opencode", "codex"])
        requirements_spec = next(item for item in extras if item.capability == "shared-pack:requirements-discovery-foundation-import")

        self.assertIn(
            ".trellis/library-assets/examples/universal-domains/product-and-requirements",
            requirements_spec.claude_paths,
        )
        self.assertIn(
            ".trellis/library-assets/examples/assembled-packs/requirements-discovery-foundation.md",
            requirements_spec.codex_paths,
        )

    def test_install_clears_stale_current_task_when_bootstrap_task_is_removed(self) -> None:
        fixture = self.create_fixture(bootstrap_as_current_task=True)
        self.addCleanup(shutil.rmtree, fixture)

        install = self.install_workflow(fixture)

        self.assertEqual(install.returncode, 0, msg=install.stdout + install.stderr)
        current_task_file = fixture / ".trellis" / ".current-task"
        self.assertFalse(current_task_file.exists())
        self.assertFalse((fixture / ".trellis" / ".runtime" / "sessions" / "test-context.json").exists())
        self.assertFalse((fixture / ".trellis" / "tasks" / "00-bootstrap-guidelines").exists())
        self.assertIn("已清理 bootstrap current-task 引用", install.stdout)
        self.assertIn("已清理 bootstrap session active-task 引用", install.stdout)

    def test_install_clears_bootstrap_current_task_when_reference_uses_short_name(self) -> None:
        fixture = self.create_fixture(bootstrap_as_current_task=True)
        self.addCleanup(shutil.rmtree, fixture)
        (fixture / ".trellis" / ".current-task").write_text("00-bootstrap-guidelines\n", encoding="utf-8")

        install = self.install_workflow(fixture)

        self.assertEqual(install.returncode, 0, msg=install.stdout + install.stderr)
        current_task_file = fixture / ".trellis" / ".current-task"
        self.assertFalse(current_task_file.exists())
        self.assertFalse((fixture / ".trellis" / ".runtime" / "sessions" / "test-context.json").exists())
        self.assertIn("已清理 bootstrap current-task 引用", install.stdout)
        self.assertIn("已清理 bootstrap session active-task 引用", install.stdout)

    def test_install_dry_run_previews_bootstrap_current_task_cleanup(self) -> None:
        fixture = self.create_fixture(bootstrap_as_current_task=True)
        self.addCleanup(shutil.rmtree, fixture)

        result = self.run_script(
            INSTALL_SCRIPT,
            "--project-root",
            str(fixture),
            "--dry-run",
            "--profile",
            "outsourcing",
        )

        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        self.assertIn("将清理 bootstrap current-task 引用", result.stdout)
        self.assertIn("将清理 bootstrap session active-task 引用", result.stdout)
        self.assertEqual(
            (fixture / ".trellis" / ".current-task").read_text(encoding="utf-8").strip(),
            ".trellis/tasks/00-bootstrap-guidelines",
        )

    def test_install_does_not_clear_special_current_task_values(self) -> None:
        fixture = self.create_fixture(bootstrap_as_current_task=True)
        self.addCleanup(shutil.rmtree, fixture)
        (fixture / ".trellis" / ".current-task").write_text(".\n", encoding="utf-8")

        install = self.install_workflow(fixture)

        self.assertEqual(install.returncode, 0, msg=install.stdout + install.stderr)
        self.assertEqual((fixture / ".trellis" / ".current-task").read_text(encoding="utf-8").strip(), ".")
        self.assertNotIn("已清理 bootstrap current-task 引用", install.stdout)
        self.assertFalse((fixture / ".trellis" / ".runtime" / "sessions" / "test-context.json").exists())
        self.assertIn("已清理 bootstrap session active-task 引用", install.stdout)

    def test_uninstall_restores_workflow_doc(self) -> None:
        fixture = self.create_fixture()
        self.addCleanup(shutil.rmtree, fixture)

        install = self.install_workflow(fixture)
        self.assertEqual(install.returncode, 0, msg=install.stdout + install.stderr)
        workflow_doc = fixture / ".trellis" / "workflow.md"
        self.assertIn(WORKFLOW_PATCH_MARKER, workflow_doc.read_text(encoding="utf-8"))

        result = self.run_script(UNINSTALL_SCRIPT, "--project-root", str(fixture))

        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        self.assertEqual(workflow_doc.read_text(encoding="utf-8"), BASELINE_WORKFLOW_CONTENT)

    def test_install_agents_routing_warns_against_manual_agent_subagent_path(self) -> None:
        fixture = self.create_fixture(include_opencode=True, include_codex=True, include_agents_md=True)
        self.addCleanup(shutil.rmtree, fixture)

        install = self.install_workflow(fixture)
        self.assertEqual(install.returncode, 0, msg=install.stdout + install.stderr)

        agents_text = (fixture / "AGENTS.md").read_text(encoding="utf-8")
        self.assertIn("显式禁用** `agent / subagent` 路径", agents_text)
        self.assertIn("禁止派发 `trellis-research` 或其他 agent/subagent", agents_text)
        self.assertNotIn("trellis-research` skill / agent", agents_text)

    def test_patch_opencode_session_utils_rewrites_subagent_guidance(self) -> None:
        fixture = Path(tempfile.mkdtemp(prefix="opencode-session-utils-"))
        self.addCleanup(shutil.rmtree, fixture)
        session_utils = fixture / ".opencode" / "lib" / "session-utils.js"
        session_utils.parent.mkdir(parents=True, exist_ok=True)
        session_utils.write_text(
            "function getTaskStatus(ctx, platformInput = null) {\n"
            "  return \"READY\"\n"
            "}\n"
            "\n"
            "function loadTrellisConfig() {\n"
            "  return null\n"
            "}\n"
            "\n"
            "export function buildSessionContext(ctx, platformInput = null) {\n"
            "  parts.push(\n"
            "    \"Project spec indexes are listed by path below. Each index contains a \" +\n"
            "    \"**Pre-Development Checklist** listing the specific guideline files to \" +\n"
            "    \"read before coding.\\n\\n\" +\n"
            "    \"- If you're spawning an implement/check sub-agent, context is injected \" +\n"
            "    \"automatically via `{task}/implement.jsonl` / `check.jsonl`. You do NOT \" +\n"
            "    \"need to read these indexes yourself.\\n\" +\n"
            "    \"- For agent-capable platforms, do NOT edit code directly in the main \" +\n"
            "    \"session; dispatch `trellis-implement` and `trellis-check` so JSONL \" +\n"
            "    \"context is loaded by the sub-agents.\\n\"\n"
            "  )\n"
            "}\n",
            encoding="utf-8",
        )

        install_spec = importlib.util.spec_from_file_location("install_workflow", INSTALL_SCRIPT)
        self.assertIsNotNone(install_spec)
        self.assertIsNotNone(install_spec.loader)
        install_module = importlib.util.module_from_spec(install_spec)
        install_spec.loader.exec_module(install_module)

        patched = install_module.patch_opencode_session_utils(fixture, dry_run=False)
        self.assertTrue(patched)
        patched_text = session_utils.read_text(encoding="utf-8")
        self.assertIn("explicitly disables `agent / subagent` execution paths", patched_text)
        self.assertNotIn("dispatch `trellis-implement` and `trellis-check`", patched_text)

    def test_uninstall_removes_workflow_shared_docs_but_retains_library_import_assets(self) -> None:
        fixture = self.create_fixture()
        self.addCleanup(shutil.rmtree, fixture)

        install = self.install_workflow(fixture)
        self.assertEqual(install.returncode, 0, msg=install.stdout + install.stderr)
        workflow_docs_dir = fixture / ".trellis" / "workflow-docs"
        self.assertTrue((workflow_docs_dir / "需求变更管理执行卡.md").exists())
        self.assertTrue((workflow_docs_dir / "finish-work-checklist-template.md").exists())
        library_lock = fixture / ".trellis" / "library-lock.yaml"
        self.assertTrue(library_lock.exists())

        result = self.run_script(UNINSTALL_SCRIPT, "--project-root", str(fixture))

        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        self.assertFalse(workflow_docs_dir.exists(), "workflow-docs should be removed on uninstall")
        self.assertTrue(library_lock.exists(), "library-lock.yaml should be retained by policy")
        self.assertIn("保留 requirements-foundation 导入资产与 library-lock.yaml", result.stdout)
        self.assertNotIn("Trellis 已恢复原始状态", result.stdout)

    def test_upgrade_check_detects_workflow_doc_patch_drift(self) -> None:
        fixture = self.create_fixture()
        self.addCleanup(shutil.rmtree, fixture)

        install = self.install_workflow(fixture)
        self.assertEqual(install.returncode, 0, msg=install.stdout + install.stderr)

        workflow_doc = fixture / ".trellis" / "workflow.md"
        workflow_doc.write_text(
            workflow_doc.read_text(encoding="utf-8").replace(WORKFLOW_PATCH_MARKER, "<!-- missing -->"),
            encoding="utf-8",
        )
        (fixture / ".trellis" / ".version").write_text("2.1.0\n", encoding="utf-8")

        result = self.run_script(
            UPGRADE_SCRIPT,
            "--check",
            "--project-root",
            str(fixture),
            env=self.latest_env_for(fixture),
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("workflow.md", result.stdout + result.stderr)

    def test_upgrade_check_detects_workflow_doc_content_drift_while_marker_intact(self) -> None:
        fixture = self.create_fixture()
        self.addCleanup(shutil.rmtree, fixture)

        install = self.install_workflow(fixture)
        self.assertEqual(install.returncode, 0, msg=install.stdout + install.stderr)

        workflow_doc = fixture / ".trellis" / "workflow.md"
        workflow_doc.write_text(
            workflow_doc.read_text(encoding="utf-8").replace(
                "workflow-state.py set <dir> --stage brainstorm --stage-status in_progress --awaiting-user-confirmation false --allowed-next design,plan,implementation --transition-from feasibility",
                "workflow-state.py set <dir> --stage brainstorm --stage-status blocked --awaiting-user-confirmation false --allowed-next design,plan,implementation --transition-from feasibility",
            ),
            encoding="utf-8",
        )
        (fixture / ".trellis" / ".version").write_text("2.1.0\n", encoding="utf-8")

        result = self.run_script(
            UPGRADE_SCRIPT,
            "--check",
            "--project-root",
            str(fixture),
            env=self.latest_env_for(fixture),
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("workflow.md", result.stdout + result.stderr)
        self.assertIn("内容漂移", result.stdout + result.stderr)

    def test_upgrade_check_detects_embed_attempt_record_conflict(self) -> None:
        fixture = self.create_fixture()
        self.addCleanup(shutil.rmtree, fixture)

        install = self.install_workflow(fixture)
        self.assertEqual(install.returncode, 0, msg=install.stdout + install.stderr)
        (fixture / ".trellis" / ATTEMPT_RECORD_NAME).write_text(
            json.dumps({"status": "failed"}, ensure_ascii=False),
            encoding="utf-8",
        )
        (fixture / ".trellis" / ".version").write_text("2.1.0\n", encoding="utf-8")

        result = self.run_script(
            UPGRADE_SCRIPT,
            "--check",
            "--project-root",
            str(fixture),
            env=self.latest_env_for(fixture),
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn(ATTEMPT_RECORD_NAME, result.stdout + result.stderr)
        self.assertIn("status=failed", result.stdout + result.stderr)

    def test_upgrade_check_allows_attempt_record_during_installer_self_check_env(self) -> None:
        fixture = self.create_fixture()
        self.addCleanup(shutil.rmtree, fixture)

        install = self.install_workflow(fixture)
        self.assertEqual(install.returncode, 0, msg=install.stdout + install.stderr)
        (fixture / ".trellis" / ATTEMPT_RECORD_NAME).write_text(
            json.dumps({"status": "failed", "last_step": "post-install-check"}, ensure_ascii=False),
            encoding="utf-8",
        )
        (fixture / ".trellis" / ".version").write_text("2.1.0\n", encoding="utf-8")

        env = self.latest_env_for(fixture)
        env["WORKFLOW_IGNORE_EMBED_ATTEMPT"] = "1"
        result = self.run_script(
            UPGRADE_SCRIPT,
            "--check",
            "--project-root",
            str(fixture),
            env=env,
        )

        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)

    def test_upgrade_check_detects_agents_md_routing_drift(self) -> None:
        fixture = self.create_fixture(include_opencode=True, include_codex=True, include_agents_md=True)
        self.addCleanup(shutil.rmtree, fixture)

        install = self.install_workflow(fixture)
        self.assertEqual(install.returncode, 0, msg=install.stdout + install.stderr)

        agents_md = fixture / "AGENTS.md"
        content = agents_md.read_text(encoding="utf-8")
        start_idx = content.index("<!-- workflow-nl-routing-start -->")
        end_idx = content.index("<!-- workflow-nl-routing-end -->") + len("<!-- workflow-nl-routing-end -->")
        agents_md.write_text(content[:start_idx] + content[end_idx:], encoding="utf-8")
        (fixture / ".trellis" / ".version").write_text("2.1.0\n", encoding="utf-8")

        result = self.run_script(
            UPGRADE_SCRIPT,
            "--check",
            "--project-root",
            str(fixture),
            env=self.latest_env_for(fixture),
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("AGENTS.md: NL 路由表缺失", result.stdout + result.stderr)

    def test_install_initializes_project_todo_file(self) -> None:
        fixture = self.create_fixture()
        self.addCleanup(shutil.rmtree, fixture)

        install = self.install_workflow(fixture)

        self.assertEqual(install.returncode, 0, msg=install.stdout + install.stderr)
        todo_path = fixture / "todo.txt"
        self.assertTrue(todo_path.exists(), "todo.txt should be created during installation")
        self.assertEqual(todo_path.read_text(encoding="utf-8"), DEFAULT_PROJECT_TODO)

    def test_install_preserves_existing_project_todo_file(self) -> None:
        fixture = self.create_fixture()
        self.addCleanup(shutil.rmtree, fixture)
        todo_path = fixture / "todo.txt"
        todo_path.write_text("已有内容\n", encoding="utf-8")

        install = self.install_workflow(fixture)

        self.assertEqual(install.returncode, 0, msg=install.stdout + install.stderr)
        self.assertEqual(todo_path.read_text(encoding="utf-8"), "已有内容\n")
        self.assertIn("todo.txt 已存在", install.stdout)

    def test_codex_secondary_skills_docs_do_not_claim_parallel_as_fresh_baseline_default(self) -> None:
        cli_matrix = (REPO_ROOT / "docs" / "workflows" / "新项目开发工作流" / "CLI原生适配边界矩阵.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("不应再把 `.codex/skills/parallel` 当作必然出现的默认现象", cli_matrix)
        self.assertIn("test -d .agents/skills", cli_matrix)
        self.assertIn("test -d .codex/skills || true", cli_matrix)
        self.assertIn("secondary carrier，不是 fresh baseline 默认必然存在", cli_matrix)
        self.assertIn("唯一主承载面", cli_matrix)
        self.assertIn("repo-scoped skills 主入口", cli_matrix)
        self.assertNotIn(
            "本仓库实际观察到的例子是：主体 skills 落在 `.agents/skills/`，`parallel` 落在 `.codex/skills/`。",
            cli_matrix,
        )

        opencode_readme = (
            REPO_ROOT / "docs" / "workflows" / "新项目开发工作流" / "commands" / "opencode" / "README.md"
        ).read_text(encoding="utf-8")
        self.assertIn("共享承载面与漂移核对范围", opencode_readme)
        self.assertIn("不应被描述成与 `.opencode/commands/trellis/*` 等价的正式入口", opencode_readme)
        self.assertIn("这一定位与本轮官方文档核对和 A/B fixture 审计结论一致", opencode_readme)

        codex_readme = (
            REPO_ROOT / "docs" / "workflows" / "新项目开发工作流" / "commands" / "codex" / "README.md"
        ).read_text(encoding="utf-8")
        self.assertIn("当前 fresh `0.5.15` 基线默认可稳定观察到的是 `.agents/skills/`", codex_readme)
        self.assertIn("唯一主承载面", codex_readme)
        self.assertIn("repo-scoped skills 主入口", codex_readme)
        self.assertIn("secondary carrier", codex_readme)
        self.assertIn("不是共享 workflow 主入口", codex_readme)
        self.assertIn(".codex/skills/ 是条件出现的 secondary carrier", codex_readme)
        self.assertNotIn(
            "本仓库实际观察到的例子是：主体 skills 落在 `.agents/skills/`，而 `parallel` 落在 `.codex/skills/`。",
            codex_readme,
        )

        hidden_boundary = (
            REPO_ROOT / "docs" / "workflows" / "新项目开发工作流" / "装后隐藏目录与托管边界核对清单.md"
        ).read_text(encoding="utf-8")
        self.assertIn("当前 fresh baseline 不应默认假定它存在", hidden_boundary)
        self.assertIn("仅在 `.codex/skills/` 实际存在时才纳入核对", hidden_boundary)
        self.assertIn("仅在该目录真实存在时才继续检查其条件性影响面", hidden_boundary)
        self.assertIn("唯一主承载面", hidden_boundary)
        self.assertIn("secondary carrier", hidden_boundary)

        command_map = (REPO_ROOT / "docs" / "workflows" / "新项目开发工作流" / "命令映射.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("只应视为共享承载面与漂移核对范围", command_map)
        self.assertIn("repo-scoped skills 主入口", command_map)
        self.assertIn("secondary carrier", command_map)

        plain_overview = (
            REPO_ROOT / "docs" / "workflows" / "新项目开发工作流" / "工作流全局流转说明（通俗版）.md"
        ).read_text(encoding="utf-8")
        self.assertIn("repo-scoped skills 主入口", plain_overview)
        self.assertIn("secondary carrier", plain_overview)

        workflow_overview = (
            REPO_ROOT / "docs" / "workflows" / "新项目开发工作流" / "工作流总纲.md"
        ).read_text(encoding="utf-8")
        self.assertIn("共享 skills 唯一主承载面", workflow_overview)
        self.assertIn("secondary carrier", workflow_overview)
        self.assertIn("install-only 的协作提醒产物", workflow_overview)
        self.assertIn("不是卸载时必须恢复/清理的目标", workflow_overview)

        walkthrough = (
            REPO_ROOT / "docs" / "workflows" / "新项目开发工作流" / "多CLI通用新项目完整流程演练.md"
        ).read_text(encoding="utf-8")
        self.assertIn("repo-scoped skills 主入口", walkthrough)
        self.assertIn("secondary-carrier skills", walkthrough)

    def test_session_start_patch_doc_tracks_current_stage_chain(self) -> None:
        doc = (
            REPO_ROOT / "docs" / "workflows" / "新项目开发工作流" / "commands" / "session-start-patch-strong-gate.md"
        ).read_text(encoding="utf-8")

        self.assertIn("正式阶段链（例如", doc)
        self.assertIn("project-audit", doc)
        self.assertNotIn(
            "feasibility/brainstorm/design/plan/implementation/check/review-gate/finish-work/delivery/record-session",
            doc,
        )

    def test_workflow_overview_extracts_large_inline_templates(self) -> None:
        workflow_root = REPO_ROOT / "docs" / "workflows" / "新项目开发工作流"
        overview = (workflow_root / "工作流总纲.md").read_text(encoding="utf-8")
        phase2_templates = (workflow_root / "阶段二：需求文档与变更模板.md").read_text(encoding="utf-8")
        phase34_templates = (workflow_root / "阶段三四：设计与任务模板.md").read_text(encoding="utf-8")
        appendix_doc = (workflow_root / "附录：评估安全与意图机制.md").read_text(encoding="utf-8")

        self.assertIn("阶段二：需求文档与变更模板", overview)
        self.assertIn("阶段三四：设计与任务模板", overview)
        self.assertIn("附录：评估安全与意图机制", overview)

        self.assertNotIn("# 变更单 CHANGE-XXX", overview)
        self.assertNotIn("# Task Creation Checklist: [任务名称]", overview)
        self.assertNotIn("# AI 设计粗稿", overview)
        self.assertNotIn("# Intent.md - [项目名称]", overview)

        self.assertIn("# 变更单 CHANGE-XXX", phase2_templates)
        self.assertIn("# Task Creation Checklist: [任务名称]", phase34_templates)
        self.assertIn("# AI 设计粗稿", phase34_templates)
        self.assertIn("# Intent.md - [项目名称]", appendix_doc)

    def test_install_creates_and_clears_attempt_record_on_success(self) -> None:
        fixture = self.create_fixture(include_opencode=True, include_codex=True, include_agents_md=True)
        self.addCleanup(shutil.rmtree, fixture)

        install = self.install_workflow(fixture)

        self.assertEqual(install.returncode, 0, msg=install.stdout + install.stderr)
        self.assertFalse((fixture / ".trellis" / ATTEMPT_RECORD_NAME).exists())
        self.assertIn("装后自检通过", install.stdout)

    def test_install_leaves_failed_attempt_record_when_cli_deployment_fails(self) -> None:
        fixture = self.create_fixture(include_codex=True)
        self.addCleanup(shutil.rmtree, fixture)
        (fixture / ".agents" / "skills" / "trellis-finish-work" / "SKILL.md").unlink()

        install = self.install_workflow(fixture)

        self.assertNotEqual(install.returncode, 0)
        attempt_record = fixture / ".trellis" / ATTEMPT_RECORD_NAME
        self.assertTrue(attempt_record.exists(), "workflow-embed-attempt.json should remain after failed install")
        attempt_data = json.loads(attempt_record.read_text(encoding="utf-8"))
        self.assertEqual(attempt_data["status"], "failed")
        self.assertEqual(attempt_data["last_step"], "deploy-cli-assets")
        self.assertFalse((fixture / ".trellis" / "workflow-installed.json").exists())

    def test_install_blocks_when_target_is_not_initial_baseline(self) -> None:
        fixture = self.create_fixture(include_opencode=True, include_codex=True, include_agents_md=True)
        self.addCleanup(shutil.rmtree, fixture)

        first_install = self.install_workflow(fixture)
        self.assertEqual(first_install.returncode, 0, msg=first_install.stdout + first_install.stderr)

        second_install = self.install_workflow(fixture)

        self.assertNotEqual(second_install.returncode, 0)
        self.assertIn("不是可执行首次嵌入的初始态", second_install.stderr)
        self.assertIn("workflow-installed.json", second_install.stderr)

    def test_detect_embed_state_reports_initial_baseline_ready(self) -> None:
        fixture = self.create_fixture(include_opencode=True, include_codex=True, include_agents_md=True)
        self.addCleanup(shutil.rmtree, fixture)

        result = self.detect_embed_state(fixture, "--json")

        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["status"], "INITIAL_BASELINE_READY")
        self.assertEqual(payload["traces"], [])

    def test_detect_embed_state_reports_already_valid_embedded(self) -> None:
        fixture = self.create_fixture(include_opencode=True, include_codex=True, include_agents_md=True)
        self.addCleanup(shutil.rmtree, fixture)

        install = self.install_workflow(fixture)
        self.assertEqual(install.returncode, 0, msg=install.stdout + install.stderr)

        result = self.detect_embed_state(fixture, "--json", env=self.latest_env_for(fixture))

        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["status"], "ALREADY_VALID_EMBEDDED")
        self.assertTrue(payload["upgrade_check_passed"])

    def test_detect_embed_state_blocks_failed_attempt_record(self) -> None:
        fixture = self.create_fixture(include_opencode=True, include_codex=True, include_agents_md=True)
        self.addCleanup(shutil.rmtree, fixture)
        attempt_record = fixture / ".trellis" / ATTEMPT_RECORD_NAME
        attempt_record.write_text(
            json.dumps(
                {
                    "status": "failed",
                    "workflow_version": "0.1.28",
                    "workflow_root": "/tmp/workflow",
                    "workflow_spec_path": "/tmp/workflow/工作流嵌入执行规范.md",
                    "target_project_root": str(fixture),
                    "last_step": "deploy-cli-assets",
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

        result = self.detect_embed_state(fixture, "--json", env=self.latest_env_for(fixture))

        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["status"], "BLOCKED_NON_INITIAL_STATE")
        self.assertIn("embed-attempt-record", "\n".join(payload["traces"]))
        self.assertEqual(payload["attempt_details"]["status"], "failed")
        self.assertEqual(payload["attempt_details"]["last_step"], "deploy-cli-assets")

    def test_install_requires_git_repository(self) -> None:
        fixture = self.create_fixture(include_git=False)
        self.addCleanup(shutil.rmtree, fixture)

        install = self.install_workflow(fixture)

        self.assertNotEqual(install.returncode, 0)
        self.assertIn("目标项目不是 Git 仓库", install.stderr)

    def test_install_requires_multiple_origin_push_urls(self) -> None:
        fixture = self.create_fixture(include_multi_origin_push_urls=False)
        self.addCleanup(shutil.rmtree, fixture)

        install = self.install_workflow(fixture)

        self.assertNotEqual(install.returncode, 0)
        self.assertIn("origin", install.stderr)
        self.assertIn("至少需要 2 个 push URL", install.stderr)
        self.assertIn("git remote add origin <你的第一个远程仓库URL>", install.stderr)
        self.assertIn("git remote set-url --add --push origin <第一个仓库URL>", install.stderr)
        self.assertIn("git remote set-url --add --push origin <第二个仓库URL>", install.stderr)

    def test_install_requires_main_branch_for_new_project(self) -> None:
        fixture = self.create_fixture(current_branch="master", has_local_history=False)
        self.addCleanup(shutil.rmtree, fixture)

        install = self.install_workflow(fixture)

        self.assertNotEqual(install.returncode, 0)
        self.assertIn("主分支和初始分支必须使用 `main`", install.stderr)
        self.assertIn("git branch -M main", install.stderr)

    def test_install_allows_existing_project_to_keep_non_main_branch(self) -> None:
        fixture = self.create_fixture(current_branch="release/1.x", has_local_history=True)
        self.addCleanup(shutil.rmtree, fixture)

        install = self.install_workflow(fixture)

        self.assertEqual(install.returncode, 0, msg=install.stdout + install.stderr)
        self.assertIn("不强制改为 `main`", install.stdout)

    def test_install_requires_codex_baseline_finish_work_skill(self) -> None:
        fixture = self.create_fixture(include_codex=True)
        self.addCleanup(shutil.rmtree, fixture)
        (fixture / ".agents" / "skills" / "trellis-finish-work" / "SKILL.md").unlink()

        install = self.install_workflow(fixture)

        self.assertNotEqual(install.returncode, 0)
        self.assertIn(
            "活动 skills 目录缺少 trellis-finish-work 基线", install.stdout + install.stderr
        )
        self.assertFalse((fixture / ".trellis" / "workflow-installed.json").exists())

    def test_install_codex_uses_agents_skills_for_shared_assets_only(self) -> None:
        fixture = self.create_fixture(include_codex=True)
        self.addCleanup(shutil.rmtree, fixture)
        codex_parallel = fixture / ".codex" / "skills" / "parallel" / "SKILL.md"
        codex_parallel.parent.mkdir(parents=True, exist_ok=True)
        codex_parallel.write_text(BASELINE_PARALLEL_CONTENT, encoding="utf-8")

        install = self.install_workflow(fixture)

        self.assertEqual(install.returncode, 0, msg=install.stdout + install.stderr)
        self.assertTrue((fixture / ".agents" / "skills" / "delivery" / "SKILL.md").exists())
        self.assertFalse((fixture / ".codex" / "skills" / "delivery" / "SKILL.md").exists())
        self.assertFalse((fixture / ".codex" / "skills" / "trellis-finish-work" / "SKILL.md").exists())
        self.assertFalse((fixture / ".codex" / "skills" / "trellis-continue" / "SKILL.md").exists())
        self.assertFalse((fixture / ".codex" / "skills" / "parallel" / "SKILL.md").exists())
        self.assertTrue((fixture / ".codex" / "skills" / ".backup-original" / "parallel" / "SKILL.md").exists())

    def test_install_requires_trellis_init(self) -> None:
        fixture = self.create_fixture(include_trellis=False)
        self.addCleanup(shutil.rmtree, fixture)

        install = self.install_workflow(fixture)

        self.assertNotEqual(install.returncode, 0)
        self.assertIn("目标项目未执行 trellis init", install.stderr)

    def test_install_requires_trellis_version_marker(self) -> None:
        fixture = self.create_fixture(include_trellis=True, include_trellis_version=False)
        self.addCleanup(shutil.rmtree, fixture)

        install = self.install_workflow(fixture)

        self.assertNotEqual(install.returncode, 0)
        self.assertIn("缺少 .trellis/.version", install.stderr)

    def test_install_injects_agents_md_routing_and_multi_cli_assets(self) -> None:
        fixture = self.create_fixture(include_opencode=True, include_codex=True, include_agents_md=True)
        self.addCleanup(shutil.rmtree, fixture)

        install = self.install_workflow(fixture)

        self.assertEqual(install.returncode, 0, msg=install.stdout + install.stderr)
        self.assertTrue((fixture / ".opencode" / "commands" / "trellis" / "brainstorm.md").exists())
        self.assertTrue((fixture / ".agents" / "skills" / "brainstorm" / "SKILL.md").exists())

        agents_md = (fixture / "AGENTS.md").read_text(encoding="utf-8")
        self.assertIn("Claude / OpenCode 入口 | Codex 入口", agents_md)
        self.assertIn("Codex：通过 `AGENTS.md` 自然语言路由或显式触发对应 skill", agents_md)
        self.assertIn("所有新实现任务默认先走这里", agents_md)
        self.assertNotIn("personal profile 首次入口可直接 `brainstorm`", agents_md)
        self.assertNotIn("personal profile 首次入口例外，可在本阶段内补齐 assessment 基线", agents_md)
        self.assertIn("调研、研究、查资料", agents_md)
        self.assertIn("trellis-research", agents_md)
        self.assertIn("当前 workflow 默认由 continue 自动执行 before-dev", agents_md)
        self.assertNotIn("| 读规范、开发前准备、看看有什么规范 | `/trellis:before-dev` |", agents_md)
        self.assertNotIn("legacy `/trellis:start`", agents_md)
        self.assertNotIn("legacy start", agents_md)

    def test_install_dry_run_reports_preview_without_writing_files(self) -> None:
        fixture = self.create_fixture(include_opencode=True, include_codex=True, include_agents_md=True)
        self.addCleanup(shutil.rmtree, fixture)

        result = self.run_script(
            INSTALL_SCRIPT,
            "--project-root",
            str(fixture),
            "--dry-run",
            "--profile",
            "outsourcing",
        )

        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        self.assertIn("将写入安装记录", result.stdout)
        self.assertIn("将注入 AGENTS.md NL 路由表", result.stdout)
        self.assertIn("将执行装后自检", result.stdout)
        self.assertNotIn("✅ 安装记录 → workflow-installed.json", result.stdout)
        self.assertNotIn("✅ AGENTS.md NL 路由表已注入", result.stdout)
        self.assertFalse((fixture / ".trellis" / "workflow-installed.json").exists())
        self.assertFalse((fixture / ".trellis" / ATTEMPT_RECORD_NAME).exists())
        self.assertFalse((fixture / ".agents" / "skills" / "review-gate").exists())
        self.assertNotIn("workflow-nl-routing-start", (fixture / "AGENTS.md").read_text(encoding="utf-8"))
        self.assertIn("[codex] 命令: 8/8, 补丁: 4, agents: 0, 脚本: 0, 手动基线校验: 2".lower(), result.stdout.lower())

    def test_install_dry_run_does_not_migrate_legacy_agents(self) -> None:
        """--dry-run must NOT perform actual file renames on disk."""
        fixture = self.create_fixture(use_latest_trellis_baseline=False)
        self.addCleanup(shutil.rmtree, fixture)

        legacy_research = fixture / ".claude" / "agents" / "research.md"
        trellis_research = fixture / ".claude" / "agents" / "trellis-research.md"
        self.assertTrue(legacy_research.exists())
        self.assertFalse(trellis_research.exists())

        result = self.run_script(
            INSTALL_SCRIPT,
            "--project-root",
            str(fixture),
            "--dry-run",
            "--profile",
            "outsourcing",
            env={EMBED_CONFIRM_ENV: "1"},
        )

        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        # Legacy file must still exist (no actual rename)
        self.assertTrue(legacy_research.exists(), "dry-run must not rename legacy agents on disk")
        # trellis-* must NOT exist (no actual creation)
        self.assertFalse(trellis_research.exists(), "dry-run must not create trellis-* agents on disk")

    def test_install_requires_embed_executor_confirmation(self) -> None:
        fixture = self.create_fixture()
        self.addCleanup(shutil.rmtree, fixture)

        result = self.run_script(INSTALL_SCRIPT, "--project-root", str(fixture))

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("无法在 Codex 中嵌入成功", result.stderr)
        self.assertIn(EMBED_CONFIRM_ENV, result.stderr)

    def test_install_proceeds_after_embed_executor_confirmation(self) -> None:
        fixture = self.create_fixture()
        self.addCleanup(shutil.rmtree, fixture)

        result = self.run_script(
            INSTALL_SCRIPT,
            "--project-root",
            str(fixture),
            "--profile",
            "outsourcing",
            env={EMBED_CONFIRM_ENV: "1"},
        )

        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)

    def test_install_filters_supported_clis_when_codex_is_requested_with_others(self) -> None:
        fixture = self.create_fixture(include_opencode=True, include_codex=True, include_agents_md=True)
        self.addCleanup(shutil.rmtree, fixture)

        result = self.run_script(
            INSTALL_SCRIPT,
            "--project-root",
            str(fixture),
            "--cli",
            "claude,opencode",
            "--profile",
            "outsourcing",
            env={EMBED_CONFIRM_ENV: "1"},
        )

        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        record_data = json.loads((fixture / ".trellis" / "workflow-installed.json").read_text(encoding="utf-8"))
        self.assertEqual(record_data["cli_types"], ["claude", "opencode"])
        self.assertIn("patched_codex_skills", record_data)

    def test_upgrade_check_detects_phase_router_drift_even_when_versions_match(self) -> None:
        fixture = self.create_fixture()
        self.addCleanup(shutil.rmtree, fixture)

        install = self.install_workflow(fixture)
        self.assertEqual(install.returncode, 0, msg=install.stdout + install.stderr)

        backup_start = fixture / ".claude" / "commands" / "trellis" / ".backup-original" / "continue.md"
        target_start = fixture / ".claude" / "commands" / "trellis" / "continue.md"
        shutil.copy2(backup_start, target_start)

        result = self.run_script(
            UPGRADE_SCRIPT,
            "--check",
            "--project-root",
            str(fixture),
            env=self.latest_env_for(fixture),
        )

        self.assertNotEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        self.assertIn("Phase Router 丢失", result.stdout)

    def test_upgrade_check_detects_missing_helper_scripts(self) -> None:
        fixture = self.create_fixture()
        self.addCleanup(shutil.rmtree, fixture)

        install = self.install_workflow(fixture)
        self.assertEqual(install.returncode, 0, msg=install.stdout + install.stderr)

        helper = fixture / ".trellis" / "scripts" / "workflow" / "workflow-state.py"
        helper.unlink()
        (fixture / ".trellis" / ".version").write_text("2.1.0\n", encoding="utf-8")

        result = self.run_script(
            UPGRADE_SCRIPT,
            "--check",
            "--project-root",
            str(fixture),
            env=self.latest_env_for(fixture),
        )

        self.assertNotEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        self.assertIn("辅助脚本缺失", result.stdout)
        self.assertIn("workflow-state.py", result.stdout)

    def test_upgrade_check_blocks_when_target_is_not_latest_trellis(self) -> None:
        fixture = self.create_fixture()
        self.addCleanup(shutil.rmtree, fixture)

        install = self.install_workflow(fixture)
        self.assertEqual(install.returncode, 0, msg=install.stdout + install.stderr)

        result = self.run_script(
            UPGRADE_SCRIPT,
            "--check",
            "--project-root",
            str(fixture),
            env={"TRELLIS_LATEST_VERSION": "2.1.0"},
        )

        self.assertNotEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        self.assertIn("尚未升级到当前最新 Trellis", result.stdout)
        self.assertIn("禁止执行当前步骤", result.stdout)

    def test_upgrade_check_detects_helper_script_drift_for_opencode_only(self) -> None:
        fixture = self.create_fixture(include_opencode=True)
        self.addCleanup(shutil.rmtree, fixture)

        install = self.install_workflow(fixture)
        self.assertEqual(install.returncode, 0, msg=install.stdout + install.stderr)

        helper = fixture / ".trellis" / "scripts" / "workflow" / "check-quality.py"
        helper.write_text(helper.read_text(encoding="utf-8") + "\n# drift\n", encoding="utf-8")
        (fixture / ".trellis" / ".version").write_text("2.1.0\n", encoding="utf-8")

        result = self.run_script(
            UPGRADE_SCRIPT,
            "--check",
            "--cli",
            "opencode",
            "--project-root",
            str(fixture),
            env=self.latest_env_for(fixture),
        )

        self.assertNotEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        self.assertIn("辅助脚本内容漂移", result.stdout)
        self.assertIn("check-quality.py", result.stdout)

    def test_upgrade_check_detects_obsolete_helper_script_residue(self) -> None:
        fixture = self.create_fixture()
        self.addCleanup(shutil.rmtree, fixture)

        install = self.install_workflow(fixture)
        self.assertEqual(install.returncode, 0, msg=install.stdout + install.stderr)

        stale_helper = fixture / ".trellis" / "scripts" / "workflow" / "record-session-helper.py"
        stale_helper.write_text("# obsolete helper residue\n", encoding="utf-8")
        (fixture / ".trellis" / ".version").write_text("2.1.0\n", encoding="utf-8")

        result = self.run_script(
            UPGRADE_SCRIPT,
            "--check",
            "--project-root",
            str(fixture),
            env=self.latest_env_for(fixture),
        )

        self.assertNotEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        self.assertIn("废弃辅助脚本残留", result.stdout)
        self.assertIn("record-session-helper.py", result.stdout)

    def test_upgrade_merge_removes_obsolete_helper_script_residue(self) -> None:
        fixture = self.create_fixture()
        self.addCleanup(shutil.rmtree, fixture)

        install = self.install_workflow(fixture)
        self.assertEqual(install.returncode, 0, msg=install.stdout + install.stderr)

        stale_helper = fixture / ".trellis" / "scripts" / "workflow" / "record-session-helper.py"
        stale_helper.write_text("# obsolete helper residue\n", encoding="utf-8")
        (fixture / ".trellis" / ".version").write_text("2.1.0\n", encoding="utf-8")

        result = self.run_script(
            UPGRADE_SCRIPT,
            "--merge",
            "--project-root",
            str(fixture),
            env=self.latest_env_for(fixture),
        )

        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        self.assertFalse(stale_helper.exists())

    def test_upgrade_check_detects_install_record_schema_drift(self) -> None:
        fixture = self.create_fixture()
        self.addCleanup(shutil.rmtree, fixture)

        install = self.install_workflow(fixture)
        self.assertEqual(install.returncode, 0, msg=install.stdout + install.stderr)

        record_path = fixture / ".trellis" / "workflow-installed.json"
        record_data = json.loads(record_path.read_text(encoding="utf-8"))
        record_data.pop("patched_baseline_commands", None)
        record_data.pop("initial_pack", None)
        record_data.pop("bootstrap_task_removed", None)
        record_data.pop("workflow_shared_docs", None)
        record_data.pop("patched_codex_skills", None)
        record_path.write_text(json.dumps(record_data, ensure_ascii=False, indent=2), encoding="utf-8")
        (fixture / ".trellis" / ".version").write_text("2.1.0\n", encoding="utf-8")

        result = self.run_script(
            UPGRADE_SCRIPT,
            "--check",
            "--project-root",
            str(fixture),
            env=self.latest_env_for(fixture),
        )

        self.assertNotEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        self.assertIn("workflow-installed.json 缺少字段", result.stdout)
        self.assertIn("patched_baseline_commands", result.stdout)
        self.assertIn("initial_pack", result.stdout)
        self.assertIn("bootstrap_task_removed", result.stdout)
        self.assertIn("workflow_shared_docs", result.stdout)
        self.assertNotIn("patched_codex_skills", result.stdout)

    def test_upgrade_check_detects_missing_critical_runtime_patches(self) -> None:
        fixture = self.create_fixture(include_codex=True)
        self.addCleanup(shutil.rmtree, fixture)

        install = self.install_workflow(fixture)
        self.assert_install_result_usable(install)

        (fixture / ".claude" / "hooks" / "session-start.py").write_text(
            BASELINE_SESSION_START_CONTENT,
            encoding="utf-8",
        )
        (fixture / ".trellis" / "scripts" / "task.py").write_text(
            BASELINE_TASK_PY_CONTENT,
            encoding="utf-8",
        )
        (fixture / ".trellis" / "scripts" / "common" / "task_store.py").write_text(
            BASELINE_TASK_STORE_CONTENT,
            encoding="utf-8",
        )
        (fixture / ".trellis" / ".version").write_text("2.1.0\n", encoding="utf-8")

        result = self.run_script(
            UPGRADE_SCRIPT,
            "--check",
            "--project-root",
            str(fixture),
            env=self.latest_env_for(fixture),
        )

        self.assertNotEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        self.assertIn("session-start.py", result.stdout)
        self.assertIn("task_store.py", result.stdout)

    def test_upgrade_check_detects_incomplete_runtime_patch_contracts(self) -> None:
        fixture = self.create_fixture(include_opencode=True)
        self.addCleanup(shutil.rmtree, fixture)

        install = self.install_workflow(fixture)
        self.assertEqual(install.returncode, 0, msg=install.stdout + install.stderr)

        opencode_inject = fixture / ".opencode" / "plugins" / "inject-workflow-state.js"
        opencode_inject.write_text(
            opencode_inject.read_text(encoding="utf-8")
            .replace('import { execFileSync } from "child_process"\n', "")
            .replace('const PYTHON_CMD = process.env.TRELLIS_PYTHON || "python3"\n\n', ""),
            encoding="utf-8",
        )
        (fixture / ".trellis" / ".version").write_text("2.1.0\n", encoding="utf-8")

        result = self.run_script(
            UPGRADE_SCRIPT,
            "--check",
            "--project-root",
            str(fixture),
            env=self.latest_env_for(fixture),
        )

        self.assertNotEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        self.assertIn("inject-workflow-state.js", result.stdout)

    def test_upgrade_check_allows_legacy_missing_version_keys(self) -> None:
        fixture = self.create_fixture()
        self.addCleanup(shutil.rmtree, fixture)

        install = self.install_workflow(fixture)
        self.assertEqual(install.returncode, 0, msg=install.stdout + install.stderr)

        record_path = fixture / ".trellis" / "workflow-installed.json"
        record_data = json.loads(record_path.read_text(encoding="utf-8"))
        record_data.pop("workflow_version", None)
        record_data.pop("workflow_schema_version", None)
        record_data.pop("patched_codex_skills", None)
        record_data.pop("bootstrap_cleanup_status", None)
        record_path.write_text(json.dumps(record_data, ensure_ascii=False, indent=2), encoding="utf-8")
        (fixture / ".trellis" / ".version").write_text("2.1.0\n", encoding="utf-8")

        result = self.run_script(
            UPGRADE_SCRIPT,
            "--check",
            "--project-root",
            str(fixture),
            env=self.latest_env_for(fixture),
        )

        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        self.assertNotIn("workflow-installed.json 缺少字段", result.stdout)
        self.assertIn("legacy/unknown", result.stdout)

    def test_upgrade_merge_backfills_legacy_missing_version_keys_even_without_conflicts(self) -> None:
        fixture = self.create_fixture()
        self.addCleanup(shutil.rmtree, fixture)

        install = self.install_workflow(fixture)
        self.assertEqual(install.returncode, 0, msg=install.stdout + install.stderr)

        record_path = fixture / ".trellis" / "workflow-installed.json"
        record_data = json.loads(record_path.read_text(encoding="utf-8"))
        record_data.pop("workflow_version", None)
        record_data.pop("workflow_schema_version", None)
        record_path.write_text(json.dumps(record_data, ensure_ascii=False, indent=2), encoding="utf-8")
        (fixture / ".trellis" / ".version").write_text("2.1.0\n", encoding="utf-8")

        result = self.run_script(
            UPGRADE_SCRIPT,
            "--merge",
            "--project-root",
            str(fixture),
            env=self.latest_env_for(fixture),
        )

        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        updated = json.loads(record_path.read_text(encoding="utf-8"))
        self.assertEqual(updated["workflow_version"], "0.1.28")
        self.assertEqual(updated["workflow_schema_version"], "3")
        self.assertIn("finish-work-checklist-template.md", updated["workflow_shared_docs"])
        self.assertIn("example.assembled-packs.requirements-discovery-foundation", updated["initial_pack_assets"])
        self.assertEqual(updated["initial_pack_cleanup_policy"], "retain-imported-assets")

    def test_upgrade_check_warns_when_bootstrap_cleanup_record_conflicts_with_filesystem(self) -> None:
        fixture = self.create_fixture()
        self.addCleanup(shutil.rmtree, fixture)

        install = self.install_workflow(fixture)
        self.assertEqual(install.returncode, 0, msg=install.stdout + install.stderr)

        bootstrap_dir = fixture / ".trellis" / "tasks" / "00-bootstrap-guidelines"
        bootstrap_dir.mkdir(parents=True, exist_ok=True)
        (bootstrap_dir / "task.json").write_text('{"id":"00-bootstrap-guidelines"}\n', encoding="utf-8")
        (fixture / ".trellis" / ".version").write_text("2.1.0\n", encoding="utf-8")

        result = self.run_script(
            UPGRADE_SCRIPT,
            "--check",
            "--project-root",
            str(fixture),
            env=self.latest_env_for(fixture),
        )

        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        self.assertIn("bootstrap_cleanup_status=removed", result.stdout + result.stderr)

    def test_upgrade_check_warns_when_bootstrap_dry_run_removed_conflicts_with_filesystem(self) -> None:
        fixture = self.create_fixture()
        self.addCleanup(shutil.rmtree, fixture)

        install = self.install_workflow(fixture)
        self.assertEqual(install.returncode, 0, msg=install.stdout + install.stderr)

        record_path = fixture / ".trellis" / "workflow-installed.json"
        record_data = json.loads(record_path.read_text(encoding="utf-8"))
        record_data["bootstrap_cleanup_status"] = "dry-run-removed"
        record_path.write_text(json.dumps(record_data, ensure_ascii=False, indent=2), encoding="utf-8")

        bootstrap_dir = fixture / ".trellis" / "tasks" / "00-bootstrap-guidelines"
        bootstrap_dir.mkdir(parents=True, exist_ok=True)
        (bootstrap_dir / "task.json").write_text('{"id":"00-bootstrap-guidelines"}\n', encoding="utf-8")
        (fixture / ".trellis" / ".version").write_text("2.1.0\n", encoding="utf-8")

        result = self.run_script(
            UPGRADE_SCRIPT,
            "--check",
            "--project-root",
            str(fixture),
            env=self.latest_env_for(fixture),
        )

        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        self.assertIn("bootstrap_cleanup_status=dry-run-removed", result.stdout + result.stderr)

    def test_upgrade_force_backfills_legacy_missing_codex_patch_record(self) -> None:
        fixture = self.create_fixture(include_codex=True)
        self.addCleanup(shutil.rmtree, fixture)

        install = self.install_workflow(fixture)
        self.assertEqual(install.returncode, 0, msg=install.stdout + install.stderr)

        self.apply_legacy_codex_workflow_state(fixture)
        record_path = fixture / ".trellis" / "workflow-installed.json"
        record_data = json.loads(record_path.read_text(encoding="utf-8"))
        record_data.pop("patched_codex_skills", None)
        record_path.write_text(json.dumps(record_data, ensure_ascii=False, indent=2), encoding="utf-8")
        (fixture / ".trellis" / ".version").write_text("2.1.0\n", encoding="utf-8")

        result = self.run_script(
            UPGRADE_SCRIPT,
            "--force",
            "--project-root",
            str(fixture),
            env=self.latest_env_for(fixture),
        )

        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        updated_record = json.loads(record_path.read_text(encoding="utf-8"))
        self.assertEqual(
            updated_record["patched_codex_skills"],
            ["trellis-continue", "trellis-finish-work", "trellis-start"],
        )

    def test_upgrade_merge_rewrites_patched_baseline_commands_without_record_session(self) -> None:
        fixture = self.create_fixture()
        self.addCleanup(shutil.rmtree, fixture)

        install = self.install_workflow(fixture)
        self.assertEqual(install.returncode, 0, msg=install.stdout + install.stderr)

        record_path = fixture / ".trellis" / "workflow-installed.json"
        record_data = json.loads(record_path.read_text(encoding="utf-8"))
        record_data["patched_baseline_commands"] = ["continue", "finish-work", "record-session"]
        record_path.write_text(json.dumps(record_data, ensure_ascii=False, indent=2), encoding="utf-8")
        (fixture / ".trellis" / ".version").write_text("2.1.0\n", encoding="utf-8")

        result = self.run_script(
            UPGRADE_SCRIPT,
            "--merge",
            "--project-root",
            str(fixture),
            env=self.latest_env_for(fixture),
        )

        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        updated = json.loads(record_path.read_text(encoding="utf-8"))
        self.assertEqual(updated["patched_baseline_commands"], ["continue", "finish-work"])

    def test_upgrade_merge_clears_residual_attempt_record_after_success(self) -> None:
        fixture = self.create_fixture()
        self.addCleanup(shutil.rmtree, fixture)

        install = self.install_workflow(fixture)
        self.assertEqual(install.returncode, 0, msg=install.stdout + install.stderr)

        attempt_record = fixture / ".trellis" / ATTEMPT_RECORD_NAME
        attempt_record.write_text(json.dumps({"status": "failed"}, ensure_ascii=False), encoding="utf-8")
        (fixture / ".trellis" / ".version").write_text("2.1.0\n", encoding="utf-8")

        result = self.run_script(
            UPGRADE_SCRIPT,
            "--merge",
            "--project-root",
            str(fixture),
            env={**self.latest_env_for(fixture), "WORKFLOW_IGNORE_EMBED_ATTEMPT": "1"},
        )

        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        self.assertFalse(attempt_record.exists(), "successful merge should clear residual attempt record")

    def test_upgrade_check_detects_codex_start_skill_patch_drift(self) -> None:
        fixture = self.create_fixture(include_codex=True)
        self.addCleanup(shutil.rmtree, fixture)

        install = self.install_workflow(fixture)
        self.assertEqual(install.returncode, 0, msg=install.stdout + install.stderr)
        self.apply_legacy_codex_workflow_state(fixture)

        start_skill = fixture / ".agents" / "skills" / "start" / "SKILL.md"
        start_skill.write_text(BASELINE_START_SKILL_CONTENT, encoding="utf-8")
        (fixture / ".trellis" / ".version").write_text("2.1.0\n", encoding="utf-8")

        result = self.run_script(
            UPGRADE_SCRIPT,
            "--check",
            "--project-root",
            str(fixture),
            env=self.latest_env_for(fixture),
        )

        self.assertNotEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        self.assertIn("start skill (.agents/skills): Phase Router 补丁缺失", result.stdout)

    def test_upgrade_check_detects_codex_secondary_skills_dir_parallel_drift(self) -> None:
        fixture = self.create_fixture(include_codex=True)
        self.addCleanup(shutil.rmtree, fixture)
        codex_parallel = fixture / ".codex" / "skills" / "parallel" / "SKILL.md"
        codex_parallel.parent.mkdir(parents=True, exist_ok=True)
        codex_parallel.write_text(BASELINE_PARALLEL_CONTENT, encoding="utf-8")

        install = self.install_workflow(fixture)
        self.assertEqual(install.returncode, 0, msg=install.stdout + install.stderr)
        self.apply_legacy_codex_workflow_state(fixture)

        codex_parallel.parent.mkdir(parents=True, exist_ok=True)
        codex_parallel.write_text("# drifted parallel\n", encoding="utf-8")
        (fixture / ".trellis" / ".version").write_text("2.1.0\n", encoding="utf-8")

        result = self.run_script(
            UPGRADE_SCRIPT,
            "--check",
            "--project-root",
            str(fixture),
            env=self.latest_env_for(fixture),
        )

        self.assertNotEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        self.assertIn(".codex/skills", result.stdout)
        self.assertIn("parallel skill (.codex/skills): 应已从嵌入面移除", result.stdout)

    def test_upgrade_check_no_longer_checks_agent_drift(self) -> None:
        fixture = self.create_fixture(include_codex=True)
        self.addCleanup(shutil.rmtree, fixture)

        install = self.install_workflow(fixture)
        self.assertEqual(install.returncode, 0, msg=install.stdout + install.stderr)
        self.mark_legacy_codex_installed(fixture)

        codex_check = fixture / ".codex" / "agents" / "trellis-check.toml"
        codex_check.write_text('name = "trellis-check"\nsandbox_mode = "read-only"\n', encoding="utf-8")
        (fixture / ".trellis" / ".version").write_text("2.1.0\n", encoding="utf-8")

        result = self.run_script(
            UPGRADE_SCRIPT,
            "--check",
            "--project-root",
            str(fixture),
            env=self.latest_env_for(fixture),
        )

        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)

    def test_upgrade_check_still_ignores_non_research_claude_agent_drift(self) -> None:
        fixture = self.create_fixture()
        self.addCleanup(shutil.rmtree, fixture)

        install = self.install_workflow(fixture)
        self.assertEqual(install.returncode, 0, msg=install.stdout + install.stderr)

        claude_check = fixture / ".claude" / "agents" / "trellis-check.md"
        claude_check.write_text("# drifted check\n", encoding="utf-8")
        (fixture / ".trellis" / ".version").write_text("2.1.0\n", encoding="utf-8")

        result = self.run_script(
            UPGRADE_SCRIPT,
            "--check",
            "--project-root",
            str(fixture),
            env=self.latest_env_for(fixture),
        )

        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)

    def test_upgrade_check_still_ignores_non_research_opencode_agent_drift(self) -> None:
        fixture = self.create_fixture(include_opencode=True)
        self.addCleanup(shutil.rmtree, fixture)

        install = self.install_workflow(fixture)
        self.assertEqual(install.returncode, 0, msg=install.stdout + install.stderr)

        opencode_check = fixture / ".opencode" / "agents" / "trellis-check.md"
        opencode_check.write_text("# drifted check\n", encoding="utf-8")
        (fixture / ".trellis" / ".version").write_text("2.1.0\n", encoding="utf-8")

        result = self.run_script(
            UPGRADE_SCRIPT,
            "--check",
            "--project-root",
            str(fixture),
            env=self.latest_env_for(fixture),
        )

        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)

    def test_upgrade_merge_no_longer_restores_codex_managed_agent(self) -> None:
        fixture = self.create_fixture(include_codex=True)
        self.addCleanup(shutil.rmtree, fixture)

        install = self.install_workflow(fixture)
        self.assertEqual(install.returncode, 0, msg=install.stdout + install.stderr)
        self.mark_legacy_codex_installed(fixture)

        codex_check = fixture / ".codex" / "agents" / "trellis-check.toml"
        codex_check.write_text('name = "trellis-check"\nsandbox_mode = "read-only"\n', encoding="utf-8")
        (fixture / ".trellis" / ".version").write_text("2.1.0\n", encoding="utf-8")

        result = self.run_script(
            UPGRADE_SCRIPT,
            "--merge",
            "--project-root",
            str(fixture),
            env=self.latest_env_for(fixture),
        )

        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        updated = codex_check.read_text(encoding="utf-8")
        self.assertIn('sandbox_mode = "read-only"', updated)

    def test_upgrade_merge_still_ignores_non_research_claude_agent_drift(self) -> None:
        fixture = self.create_fixture()
        self.addCleanup(shutil.rmtree, fixture)

        install = self.install_workflow(fixture)
        self.assertEqual(install.returncode, 0, msg=install.stdout + install.stderr)

        claude_check = fixture / ".claude" / "agents" / "trellis-check.md"
        claude_check.write_text("# drifted check\n", encoding="utf-8")
        (fixture / ".trellis" / ".version").write_text("2.1.0\n", encoding="utf-8")

        result = self.run_script(
            UPGRADE_SCRIPT,
            "--merge",
            "--project-root",
            str(fixture),
            env=self.latest_env_for(fixture),
        )

        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        updated = claude_check.read_text(encoding="utf-8")
        self.assertEqual(updated, "# drifted check\n")

    def test_upgrade_merge_still_ignores_non_research_opencode_agent_drift(self) -> None:
        fixture = self.create_fixture(include_opencode=True)
        self.addCleanup(shutil.rmtree, fixture)

        install = self.install_workflow(fixture)
        self.assertEqual(install.returncode, 0, msg=install.stdout + install.stderr)

        opencode_check = fixture / ".opencode" / "agents" / "trellis-check.md"
        opencode_check.write_text("# drifted check\n", encoding="utf-8")
        (fixture / ".trellis" / ".version").write_text("2.1.0\n", encoding="utf-8")

        result = self.run_script(
            UPGRADE_SCRIPT,
            "--merge",
            "--project-root",
            str(fixture),
            env=self.latest_env_for(fixture),
        )

        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        updated = opencode_check.read_text(encoding="utf-8")
        self.assertEqual(updated, "# drifted check\n")

    def test_uninstall_migrates_legacy_agents_and_restores_backups(self) -> None:
        fixture = self.create_fixture(include_codex=True)
        self.addCleanup(shutil.rmtree, fixture)

        install = self.install_workflow(fixture)
        self.assertEqual(install.returncode, 0, msg=install.stdout + install.stderr)
        self.mark_legacy_codex_installed(fixture)

        merge = self.run_script(
            UPGRADE_SCRIPT,
            "--merge",
            "--project-root",
            str(fixture),
            env=self.latest_env_for(fixture),
        )
        self.assertEqual(merge.returncode, 0, msg=merge.stdout + merge.stderr)

        codex_check = fixture / ".codex" / "agents" / "trellis-check.toml"

        result = self.run_script(UNINSTALL_SCRIPT, "--project-root", str(fixture))

        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        self.assertIn("[Codex]", result.stdout)
        if codex_check.exists():
            restored = codex_check.read_text(encoding="utf-8")
            self.assertIn('sandbox_mode = "read-only"', restored)

    def test_uninstall_preserves_native_trellis_agents_no_backup(self) -> None:
        """Post-0.5: workflow no longer overlays agents; uninstall must NOT
        delete Trellis-native trellis-*.md files when no backup exists."""
        fixture = self.create_fixture()
        self.addCleanup(shutil.rmtree, fixture)

        install = self.install_workflow(fixture)
        self.assertEqual(install.returncode, 0, msg=install.stdout + install.stderr)

        claude_research = fixture / ".claude" / "agents" / "trellis-research.md"
        self.assertTrue(claude_research.exists(), "trellis-research.md should exist before uninstall")

        result = self.run_script(UNINSTALL_SCRIPT, "--project-root", str(fixture))

        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        # Native agents must survive uninstall
        self.assertTrue(claude_research.exists(), "native trellis-research.md must NOT be deleted by uninstall")

    def test_uninstall_removes_legacy_bare_name_agents(self) -> None:
        """Legacy bare-name agent files (research.md) are leftovers from
        pre-0.5 installs and should be cleaned up by uninstall."""
        fixture = self.create_fixture(use_latest_trellis_baseline=False)
        self.addCleanup(shutil.rmtree, fixture)

        install = self.install_workflow(fixture)
        self.assertEqual(install.returncode, 0, msg=install.stdout + install.stderr)

        # After install, legacy bare-name should be migrated to trellis-*
        legacy_research = fixture / ".claude" / "agents" / "research.md"
        trellis_research = fixture / ".claude" / "agents" / "trellis-research.md"
        self.assertFalse(legacy_research.exists(), "legacy research.md should be migrated by install")
        self.assertTrue(trellis_research.exists(), "trellis-research.md should exist after migration")

        result = self.run_script(UNINSTALL_SCRIPT, "--project-root", str(fixture))
        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)

        # trellis-* is native, must survive uninstall even without backup
        self.assertTrue(trellis_research.exists(), "native trellis-research.md must survive uninstall")

    def test_uninstall_restores_agents_from_backup(self) -> None:
        """When a workflow backup exists, uninstall restores the backup
        content for both Claude and OpenCode agents."""
        fixture = self.create_fixture(include_opencode=True)
        self.addCleanup(shutil.rmtree, fixture)

        install = self.install_workflow(fixture)
        self.assertEqual(install.returncode, 0, msg=install.stdout + install.stderr)

        claude_research = fixture / ".claude" / "agents" / "trellis-research.md"
        opencode_check = fixture / ".opencode" / "agents" / "trellis-check.md"

        result = self.run_script(UNINSTALL_SCRIPT, "--project-root", str(fixture))

        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        if claude_research.exists():
            restored = claude_research.read_text(encoding="utf-8")
            self.assertEqual(restored, BASELINE_AGENT_RESEARCH_MD)
        if opencode_check.exists():
            restored = opencode_check.read_text(encoding="utf-8")
            self.assertEqual(restored, BASELINE_AGENT_CHECK_MD)

    def test_uninstall_removes_agents_created_by_legacy_migration(self) -> None:
        fixture = self.create_fixture(include_codex=True, use_latest_trellis_baseline=False)
        self.addCleanup(shutil.rmtree, fixture)

        install = self.install_workflow(fixture)
        self.assertEqual(install.returncode, 0, msg=install.stdout + install.stderr)

        result = self.run_script(UNINSTALL_SCRIPT, "--project-root", str(fixture))

        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)

    def test_upgrade_check_detects_brainstorm_command_drift(self) -> None:
        fixture = self.create_fixture()
        self.addCleanup(shutil.rmtree, fixture)

        install = self.install_workflow(fixture)
        self.assertEqual(install.returncode, 0, msg=install.stdout + install.stderr)

        brainstorm = fixture / ".claude" / "commands" / "trellis" / "brainstorm.md"
        brainstorm.write_text("# drifted brainstorm\n", encoding="utf-8")
        (fixture / ".trellis" / ".version").write_text("2.1.0\n", encoding="utf-8")

        result = self.run_script(
            UPGRADE_SCRIPT,
            "--check",
            "--project-root",
            str(fixture),
            env=self.latest_env_for(fixture),
        )

        self.assertNotEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        self.assertIn("命令内容漂移: /trellis:brainstorm", result.stdout)

    def test_upgrade_check_detects_check_command_drift(self) -> None:
        fixture = self.create_fixture()
        self.addCleanup(shutil.rmtree, fixture)

        install = self.install_workflow(fixture)
        self.assertEqual(install.returncode, 0, msg=install.stdout + install.stderr)

        check = fixture / ".claude" / "commands" / "trellis" / "check.md"
        check.write_text("# drifted check\n", encoding="utf-8")
        (fixture / ".trellis" / ".version").write_text("2.1.0\n", encoding="utf-8")

        result = self.run_script(
            UPGRADE_SCRIPT,
            "--check",
            "--project-root",
            str(fixture),
            env=self.latest_env_for(fixture),
        )

        self.assertNotEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        self.assertIn("命令内容漂移: /trellis:check", result.stdout)

    def test_upgrade_check_detects_finish_work_patch_drift(self) -> None:
        fixture = self.create_fixture()
        self.addCleanup(shutil.rmtree, fixture)

        install = self.install_workflow(fixture)
        self.assertEqual(install.returncode, 0, msg=install.stdout + install.stderr)

        finish_work = fixture / ".claude" / "commands" / "trellis" / "finish-work.md"
        content = finish_work.read_text(encoding="utf-8").replace(FINISH_WORK_MARKER, "<!-- missing -->")
        finish_work.write_text(content, encoding="utf-8")
        (fixture / ".trellis" / ".version").write_text("2.1.0\n", encoding="utf-8")

        result = self.run_script(
            UPGRADE_SCRIPT,
            "--check",
            "--project-root",
            str(fixture),
            env=self.latest_env_for(fixture),
        )

        self.assertNotEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        self.assertIn("finish-work.md: 项目化补丁缺失", result.stdout)

    def test_force_recovers_start_from_backup_when_injection_marker_is_missing(self) -> None:
        fixture = self.create_fixture()
        self.addCleanup(shutil.rmtree, fixture)

        install = self.install_workflow(fixture)
        self.assertEqual(install.returncode, 0, msg=install.stdout + install.stderr)

        broken_start = fixture / ".claude" / "commands" / "trellis" / "continue.md"
        broken_start.write_text(
            "# broken start\n\n"
            "This file intentionally lacks the expected injection marker.\n",
            encoding="utf-8",
        )
        (fixture / ".trellis" / ".version").write_text("2.1.0\n", encoding="utf-8")

        result = self.run_script(
            UPGRADE_SCRIPT,
            "--force",
            "--project-root",
            str(fixture),
            env=self.latest_env_for(fixture),
        )

        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        self.assertIn(PHASE_ROUTER_MARKER, broken_start.read_text(encoding="utf-8"))
        self.assertNotIn("无法自动注入", result.stdout)

    def test_upgrade_check_tolerates_missing_legacy_record_session_file(self) -> None:
        fixture = self.create_fixture()
        self.addCleanup(shutil.rmtree, fixture)

        install = self.install_workflow(fixture)
        self.assertEqual(install.returncode, 0, msg=install.stdout + install.stderr)

        (fixture / ".claude" / "commands" / "trellis" / "record-session.md").unlink()
        (fixture / ".trellis" / ".version").write_text("2.1.0\n", encoding="utf-8")

        result = self.run_script(
            UPGRADE_SCRIPT,
            "--check",
            "--project-root",
            str(fixture),
            env=self.latest_env_for(fixture),
        )

        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)

    def test_upgrade_merge_restores_drift_and_followup_check_passes(self) -> None:
        fixture = self.create_fixture()
        self.addCleanup(shutil.rmtree, fixture)

        install = self.install_workflow(fixture)
        self.assertEqual(install.returncode, 0, msg=install.stdout + install.stderr)

        start = fixture / ".claude" / "commands" / "trellis" / "continue.md"
        finish_work = fixture / ".claude" / "commands" / "trellis" / "finish-work.md"
        record_session = fixture / ".claude" / "commands" / "trellis" / "record-session.md"
        start.write_text(BASELINE_CONTINUE_CONTENT, encoding="utf-8")
        finish_work.write_text(BASELINE_FINISH_WORK_CONTENT, encoding="utf-8")
        record_session.write_text(BASELINE_RECORD_SESSION_CONTENT, encoding="utf-8")
        (fixture / ".trellis" / ".version").write_text("2.1.0\n", encoding="utf-8")

        merge = self.run_script(
            UPGRADE_SCRIPT,
            "--merge",
            "--project-root",
            str(fixture),
            env=self.latest_env_for(fixture),
        )

        self.assertEqual(merge.returncode, 0, msg=merge.stdout + merge.stderr)
        self.assertIn(PHASE_ROUTER_MARKER, start.read_text(encoding="utf-8"))
        self.assertIn(FINISH_WORK_MARKER, finish_work.read_text(encoding="utf-8"))
        record_data = json.loads((fixture / ".trellis" / "workflow-installed.json").read_text(encoding="utf-8"))
        self.assertEqual(record_data["workflow_version"], "0.1.28")
        self.assertEqual(record_data["previous_version"], "0.5.0-rc.3")

        followup_check = self.run_script(
            UPGRADE_SCRIPT,
            "--check",
            "--project-root",
            str(fixture),
            env=self.latest_env_for(fixture),
        )
        self.assertEqual(followup_check.returncode, 0, msg=followup_check.stdout + followup_check.stderr)

    def test_upgrade_check_detects_needs_init_residue_in_installed_artifacts(self) -> None:
        fixture = self.create_fixture(include_codex=True)
        self.addCleanup(shutil.rmtree, fixture)

        install = self.install_workflow(fixture)
        self.assertEqual(install.returncode, 0, msg=install.stdout + install.stderr)

        workflow_md = fixture / ".trellis" / "workflow.md"
        workflow_text = workflow_md.read_text(encoding="utf-8")
        workflow_text = workflow_text.replace(
            "If `workflow-state.json` is missing or not yet initialized, strong-gate task views surface `repair_needed` instead of ",
            "If `workflow-state.json` is missing, strong-gate task views surface a `needs-init` / repair-oriented status instead of ",
        )
        workflow_text = workflow_text.replace(
            "[workflow-state:repair_needed]\n"
            "Route action: **repair_needed** — workflow state is missing, uninitialized, stale, or structurally invalid.\n",
            "[workflow-state:needs-init]\n"
            "Route action: **needs-init** — the current task exists, but `workflow-state.json` has not been initialized yet.\n"
            "Do **not** fall back to legacy `planning` semantics. Initialize or repair the task's workflow state first, then rerun `workflow-state.py route`.\n"
            "If this is a freshly created task, enter the correct first stage instead of jumping straight into implementation.\n"
            "[/workflow-state:needs-init]\n\n"
            "[workflow-state:repair_needed]\n"
            "Route action: **repair_needed** — workflow state is missing, stale, or structurally invalid.\n",
        )
        workflow_md.write_text(workflow_text, encoding="utf-8")

        tasks_py = fixture / ".trellis" / "scripts" / "common" / "tasks.py"
        tasks_text = tasks_py.read_text(encoding="utf-8").replace(
            '        return "repair_needed", "workflow-state.json missing"\n',
            '        return "needs-init", None\n',
        )
        tasks_py.write_text(tasks_text, encoding="utf-8")

        task_py = fixture / ".trellis" / "scripts" / "task.py"
        task_text = task_py.read_text(encoding="utf-8") + (
            "\n  --status, -s <s>     Filter by workflow display status / stage "
            "(e.g. needs-init, feasibility, design, completed)\n"
        )
        task_py.write_text(task_text, encoding="utf-8")

        patch_script = fixture / ".trellis" / "scripts" / "workflow" / "patch-task-status-view-strong-gate.py"
        patch_text = patch_script.read_text(encoding="utf-8").replace(
            '        return "repair_needed", "workflow-state.json missing"\n',
            '        return "needs-init", None\n',
        ).replace(
            '        return "repair_needed"\n',
            '        return "needs-init"\n',
            1,
        ).replace(
            "  --status, -s <s>     Filter by workflow display status / stage (e.g. repair_needed, feasibility, design, completed)\n",
            "  --status, -s <s>     Filter by workflow display status / stage (e.g. needs-init, feasibility, design, completed)\n",
        )
        patch_script.write_text(patch_text, encoding="utf-8")

        workflow_state_helper = fixture / ".trellis" / "scripts" / "workflow" / "workflow-state.py"
        helper_text = workflow_state_helper.read_text(encoding="utf-8").replace(
            "缺少 workflow-state.json（可能因任务创建于工作流安装之前，或当前任务尚未初始化阶段状态）。",
            "缺少 workflow-state.json（可能因任务创建于工作流安装之前）。",
        )
        workflow_state_helper.write_text(helper_text, encoding="utf-8")

        check = self.run_script(
            UPGRADE_SCRIPT,
            "--check",
            "--project-root",
            str(fixture),
            env=self.latest_env_for(fixture),
        )

        self.assertNotEqual(check.returncode, 0)
        combined = check.stdout + check.stderr
        self.assertIn(".trellis/workflow.md: needs-init 状态块残留", combined)
        self.assertIn(".trellis/workflow.md: task system 文案仍将未初始化状态写成 needs-init", combined)
        self.assertIn("common/tasks.py: 仍将缺失 workflow-state.json 显示为 needs-init", combined)
        self.assertIn("task.py: --status 示例仍使用 needs-init", combined)
        self.assertIn("辅助脚本内容漂移: workflow-state.py", combined)
        self.assertIn("辅助脚本内容漂移: patch-task-status-view-strong-gate.py", combined)

    def test_upgrade_merge_refreshes_needs_init_residue_from_installed_artifacts(self) -> None:
        fixture = self.create_fixture(include_codex=True)
        self.addCleanup(shutil.rmtree, fixture)

        install = self.install_workflow(fixture)
        self.assertEqual(install.returncode, 0, msg=install.stdout + install.stderr)

        workflow_md = fixture / ".trellis" / "workflow.md"
        workflow_text = workflow_md.read_text(encoding="utf-8")
        workflow_text = workflow_text.replace(
            "If `workflow-state.json` is missing or not yet initialized, strong-gate task views surface `repair_needed` instead of ",
            "If `workflow-state.json` is missing, strong-gate task views surface a `needs-init` / repair-oriented status instead of ",
        )
        workflow_text = workflow_text.replace(
            "[workflow-state:repair_needed]\n"
            "Route action: **repair_needed** — workflow state is missing, uninitialized, stale, or structurally invalid.\n",
            "[workflow-state:needs-init]\n"
            "Route action: **needs-init** — the current task exists, but `workflow-state.json` has not been initialized yet.\n"
            "Do **not** fall back to legacy `planning` semantics. Initialize or repair the task's workflow state first, then rerun `workflow-state.py route`.\n"
            "If this is a freshly created task, enter the correct first stage instead of jumping straight into implementation.\n"
            "[/workflow-state:needs-init]\n\n"
            "[workflow-state:repair_needed]\n"
            "Route action: **repair_needed** — workflow state is missing, stale, or structurally invalid.\n",
        )
        workflow_md.write_text(workflow_text, encoding="utf-8")

        tasks_py = fixture / ".trellis" / "scripts" / "common" / "tasks.py"
        tasks_text = tasks_py.read_text(encoding="utf-8").replace(
            '        return "repair_needed", "workflow-state.json missing"\n',
            '        return "needs-init", None\n',
        )
        tasks_py.write_text(tasks_text, encoding="utf-8")

        task_py = fixture / ".trellis" / "scripts" / "task.py"
        task_text = task_py.read_text(encoding="utf-8") + (
            "\n  --status, -s <s>     Filter by workflow display status / stage "
            "(e.g. needs-init, feasibility, design, completed)\n"
        )
        task_py.write_text(task_text, encoding="utf-8")

        patch_script = fixture / ".trellis" / "scripts" / "workflow" / "patch-task-status-view-strong-gate.py"
        patch_text = patch_script.read_text(encoding="utf-8").replace(
            '        return "repair_needed", "workflow-state.json missing"\n',
            '        return "needs-init", None\n',
        ).replace(
            '        return "repair_needed"\n',
            '        return "needs-init"\n',
            1,
        ).replace(
            "  --status, -s <s>     Filter by workflow display status / stage (e.g. repair_needed, feasibility, design, completed)\n",
            "  --status, -s <s>     Filter by workflow display status / stage (e.g. needs-init, feasibility, design, completed)\n",
        )
        patch_script.write_text(patch_text, encoding="utf-8")

        workflow_state_helper = fixture / ".trellis" / "scripts" / "workflow" / "workflow-state.py"
        helper_text = workflow_state_helper.read_text(encoding="utf-8").replace(
            "缺少 workflow-state.json（可能因任务创建于工作流安装之前，或当前任务尚未初始化阶段状态）。",
            "缺少 workflow-state.json（可能因任务创建于工作流安装之前）。",
        )
        workflow_state_helper.write_text(helper_text, encoding="utf-8")

        merge = self.run_script(
            UPGRADE_SCRIPT,
            "--merge",
            "--project-root",
            str(fixture),
            env=self.latest_env_for(fixture),
        )
        self.assertEqual(merge.returncode, 0, msg=merge.stdout + merge.stderr)

        refreshed_workflow = workflow_md.read_text(encoding="utf-8")
        self.assertNotIn("needs-init / repair-oriented status", refreshed_workflow)
        self.assertNotIn("[workflow-state:needs-init]", refreshed_workflow)
        self.assertIn("missing or not yet initialized", refreshed_workflow)
        self.assertIn("missing, uninitialized, stale, or structurally invalid", refreshed_workflow)

        refreshed_tasks = tasks_py.read_text(encoding="utf-8")
        self.assertNotIn("needs-init", refreshed_tasks)
        self.assertIn('return "repair_needed", "workflow-state.json missing"', refreshed_tasks)

        refreshed_task = task_py.read_text(encoding="utf-8")
        self.assertNotIn("e.g. needs-init, feasibility", refreshed_task)
        self.assertIn("e.g. repair_needed, feasibility, design, completed", refreshed_task)

        refreshed_patch = patch_script.read_text(encoding="utf-8")
        self.assertIn('return "repair_needed", "workflow-state.json missing"', refreshed_patch)
        self.assertIn('patched = patched.replace(', refreshed_patch)
        self.assertIn('  --status, -s <s>     Filter by workflow display status / stage (e.g. repair_needed, feasibility, design, completed)', refreshed_patch)

        refreshed_helper = workflow_state_helper.read_text(encoding="utf-8")
        self.assertIn("或当前任务尚未初始化阶段状态", refreshed_helper)
        self.assertNotIn("缺少 workflow-state.json（可能因任务创建于工作流安装之前）。", refreshed_helper)

        followup_check = self.run_script(
            UPGRADE_SCRIPT,
            "--check",
            "--project-root",
            str(fixture),
            env=self.latest_env_for(fixture),
        )
        self.assertEqual(followup_check.returncode, 0, msg=followup_check.stdout + followup_check.stderr)

    def test_upgrade_merge_preserves_legacy_entry_command_while_migrating_agent_names(self) -> None:
        fixture = self.create_fixture(include_codex=True, use_latest_trellis_baseline=False)
        self.addCleanup(shutil.rmtree, fixture)

        install = self.install_workflow(fixture)
        self.assertEqual(install.returncode, 0, msg=install.stdout + install.stderr)

        legacy_start = fixture / ".claude" / "commands" / "trellis" / "start.md"
        self.assertTrue(legacy_start.exists())

        (fixture / ".trellis" / ".version").write_text("2.1.0\n", encoding="utf-8")

        merge = self.run_script(
            UPGRADE_SCRIPT,
            "--merge",
            "--project-root",
            str(fixture),
            env=self.latest_env_for(fixture),
        )

        self.assertEqual(merge.returncode, 0, msg=merge.stdout + merge.stderr)
        self.assertIn(
            PHASE_ROUTER_MARKER,
            (fixture / ".claude" / "commands" / "trellis" / "start.md").read_text(encoding="utf-8"),
        )
        self.assertTrue((fixture / ".claude" / "commands" / "trellis" / "start.md").exists())
        self.assertTrue((fixture / ".claude" / "agents" / "trellis-research.md").exists())
        self.assertFalse((fixture / ".claude" / "agents" / "research.md").exists())

    def test_upgrade_merge_restores_agents_md_routing(self) -> None:
        fixture = self.create_fixture(include_opencode=True, include_codex=True, include_agents_md=True)
        self.addCleanup(shutil.rmtree, fixture)

        install = self.install_workflow(fixture)
        self.assertEqual(install.returncode, 0, msg=install.stdout + install.stderr)

        agents_md = fixture / "AGENTS.md"
        content = agents_md.read_text(encoding="utf-8")
        start_idx = content.index("<!-- workflow-nl-routing-start -->")
        end_idx = content.index("<!-- workflow-nl-routing-end -->") + len("<!-- workflow-nl-routing-end -->")
        agents_md.write_text(content[:start_idx] + content[end_idx:], encoding="utf-8")
        (fixture / ".trellis" / ".version").write_text("2.1.0\n", encoding="utf-8")

        merge = self.run_script(
            UPGRADE_SCRIPT,
            "--merge",
            "--project-root",
            str(fixture),
            env=self.latest_env_for(fixture),
        )

        self.assertEqual(merge.returncode, 0, msg=merge.stdout + merge.stderr)
        updated_agents = agents_md.read_text(encoding="utf-8")
        self.assertIn("workflow-nl-routing-start", updated_agents)
        self.assertIn("自然语言命令路由", updated_agents)
        self.assertNotIn("legacy `/trellis:start`", updated_agents)
        self.assertNotIn("legacy start", updated_agents)

        followup_check = self.run_script(
            UPGRADE_SCRIPT,
            "--check",
            "--project-root",
            str(fixture),
            env=self.latest_env_for(fixture),
        )
        self.assertEqual(followup_check.returncode, 0, msg=followup_check.stdout + followup_check.stderr)

    def test_upgrade_merge_removes_codex_secondary_duplicate_shared_skills(self) -> None:
        fixture = self.create_fixture(include_codex=True)
        self.addCleanup(shutil.rmtree, fixture)
        codex_parallel = fixture / ".codex" / "skills" / "parallel" / "SKILL.md"
        codex_parallel.parent.mkdir(parents=True, exist_ok=True)
        codex_parallel.write_text(BASELINE_PARALLEL_CONTENT, encoding="utf-8")

        install = self.install_workflow(fixture)
        self.assertEqual(install.returncode, 0, msg=install.stdout + install.stderr)
        self.apply_legacy_codex_workflow_state(fixture)

        codex_delivery = fixture / ".codex" / "skills" / "delivery" / "SKILL.md"
        codex_delivery.parent.mkdir(parents=True, exist_ok=True)
        codex_delivery.write_text("# drifted delivery\n", encoding="utf-8")
        codex_parallel.parent.mkdir(parents=True, exist_ok=True)
        codex_parallel.write_text("# drifted parallel\n", encoding="utf-8")
        (fixture / ".trellis" / ".version").write_text("2.1.0\n", encoding="utf-8")

        merge = self.run_script(
            UPGRADE_SCRIPT,
            "--merge",
            "--project-root",
            str(fixture),
            env=self.latest_env_for(fixture),
        )

        self.assertEqual(merge.returncode, 0, msg=merge.stdout + merge.stderr)
        self.assertFalse(codex_delivery.exists())
        self.assertFalse(codex_parallel.exists())

    def test_upgrade_merge_preserves_bootstrap_cleanup_status(self) -> None:
        fixture = self.create_fixture()
        self.addCleanup(shutil.rmtree, fixture)

        install = self.install_workflow(fixture)
        self.assertEqual(install.returncode, 0, msg=install.stdout + install.stderr)

        record_path = fixture / ".trellis" / "workflow-installed.json"
        record_data = json.loads(record_path.read_text(encoding="utf-8"))
        self.assertEqual(record_data["bootstrap_cleanup_status"], "removed")
        (fixture / ".trellis" / ".version").write_text("2.1.0\n", encoding="utf-8")

        merge = self.run_script(
            UPGRADE_SCRIPT,
            "--merge",
            "--project-root",
            str(fixture),
            env=self.latest_env_for(fixture),
        )

        self.assertEqual(merge.returncode, 0, msg=merge.stdout + merge.stderr)
        updated_record = json.loads(record_path.read_text(encoding="utf-8"))
        self.assertEqual(updated_record["bootstrap_cleanup_status"], "removed")

    def test_force_restores_codex_secondary_parallel_backup_without_finish_work(self) -> None:
        fixture = self.create_fixture(include_codex=True)
        self.addCleanup(shutil.rmtree, fixture)
        codex_parallel = fixture / ".codex" / "skills" / "parallel" / "SKILL.md"
        codex_parallel.parent.mkdir(parents=True, exist_ok=True)
        codex_parallel.write_text(BASELINE_PARALLEL_CONTENT, encoding="utf-8")

        install = self.install_workflow(fixture)
        self.assertEqual(install.returncode, 0, msg=install.stdout + install.stderr)
        self.apply_legacy_codex_workflow_state(fixture)

        backup_parallel = fixture / ".codex" / "skills" / ".backup-original" / "parallel" / "SKILL.md"
        backup_parallel.parent.mkdir(parents=True, exist_ok=True)
        backup_parallel.write_text(BASELINE_PARALLEL_CONTENT, encoding="utf-8")
        self.assertTrue(backup_parallel.exists())
        codex_parallel.parent.mkdir(parents=True, exist_ok=True)
        codex_parallel.write_text("# drifted parallel\n", encoding="utf-8")
        (fixture / ".trellis" / ".version").write_text("2.1.0\n", encoding="utf-8")

        result = self.run_script(
            UPGRADE_SCRIPT,
            "--force",
            "--project-root",
            str(fixture),
            env=self.latest_env_for(fixture),
        )

        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        self.assertFalse(codex_parallel.exists())

    def test_force_restores_finish_work_from_backup_and_reapplies_patch(self) -> None:
        fixture = self.create_fixture()
        self.addCleanup(shutil.rmtree, fixture)

        install = self.install_workflow(fixture)
        self.assertEqual(install.returncode, 0, msg=install.stdout + install.stderr)

        finish_work = fixture / ".claude" / "commands" / "trellis" / "finish-work.md"
        finish_work.write_text("# broken finish-work\n\nmissing expected sections\n", encoding="utf-8")
        (fixture / ".trellis" / ".version").write_text("2.1.0\n", encoding="utf-8")

        result = self.run_script(
            UPGRADE_SCRIPT,
            "--force",
            "--project-root",
            str(fixture),
            env=self.latest_env_for(fixture),
        )

        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        restored_text = finish_work.read_text(encoding="utf-8")
        self.assertIn(FINISH_WORK_MARKER, restored_text)
        self.assertNotIn("pnpm lint", restored_text)

    def test_install_deploys_archive_closeout_patch_and_help_contract(self) -> None:
        fixture = self.create_fixture(include_opencode=True, include_codex=True)
        self.addCleanup(shutil.rmtree, fixture)

        install = self.install_workflow(fixture)
        self.assert_install_result_usable(install)

        task_store = fixture / ".trellis" / "scripts" / "common" / "task_store.py"
        task_store_text = task_store.read_text(encoding="utf-8")
        self.assertIn("workflow close-out gate validation", task_store_text)
        self.assertIn("finish-work-checklist.md", task_store_text)
        self.assertIn("workflow-state.json", task_store_text)

        workflow_state = fixture / ".trellis" / "scripts" / "workflow" / "workflow-state.py"
        workflow_state_text = workflow_state.read_text(encoding="utf-8")
        self.assertIn("Runtime contract", workflow_state_text)
        self.assertIn("Writer table", workflow_state_text)
        self.assertIn("Test invariants", workflow_state_text)

    def test_force_restores_codex_start_skill_from_backup_and_reapplies_patch(self) -> None:
        fixture = self.create_fixture(include_codex=True)
        self.addCleanup(shutil.rmtree, fixture)

        install = self.install_workflow(fixture)
        self.assertEqual(install.returncode, 0, msg=install.stdout + install.stderr)
        self.apply_legacy_codex_workflow_state(fixture)

        start_skill = fixture / ".agents" / "skills" / "start" / "SKILL.md"
        start_skill.write_text("# broken start skill\n", encoding="utf-8")
        (fixture / ".trellis" / ".version").write_text("2.1.0\n", encoding="utf-8")

        result = self.run_script(
            UPGRADE_SCRIPT,
            "--force",
            "--project-root",
            str(fixture),
            env=self.latest_env_for(fixture),
        )

        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        restored_text = start_skill.read_text(encoding="utf-8")
        self.assertNotIn("## Step 4: Decide next action", restored_text)
        self.assertIn("Workflow Phase Router Patch", restored_text)

    def test_force_fails_when_codex_active_baseline_backup_is_missing(self) -> None:
        fixture = self.create_fixture(include_codex=True)
        self.addCleanup(shutil.rmtree, fixture)

        install = self.install_workflow(fixture)
        self.assertEqual(install.returncode, 0, msg=install.stdout + install.stderr)
        self.apply_legacy_codex_workflow_state(fixture)

        start_backup = fixture / ".agents" / "skills" / ".backup-original" / "start" / "SKILL.md"
        if start_backup.exists():
            start_backup.unlink()
        current_backup = fixture / ".agents" / "skills" / ".backup-original" / "trellis-continue" / "SKILL.md"
        if current_backup.exists():
            current_backup.unlink()
        (fixture / ".trellis" / ".version").write_text("2.1.0\n", encoding="utf-8")

        result = self.run_script(
            UPGRADE_SCRIPT,
            "--force",
            "--project-root",
            str(fixture),
            env=self.latest_env_for(fixture),
        )

        self.assertNotEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        self.assertIn("缺少 .backup-original/trellis-continue 或 start", result.stdout + result.stderr)

    def test_uninstall_tolerates_corrupted_install_record(self) -> None:
        fixture = self.create_fixture()
        self.addCleanup(shutil.rmtree, fixture)

        install = self.install_workflow(fixture)
        self.assertEqual(install.returncode, 0, msg=install.stdout + install.stderr)

        record = fixture / ".trellis" / "workflow-installed.json"
        record.write_text("{ invalid json", encoding="utf-8")

        result = self.run_script(UNINSTALL_SCRIPT, "--project-root", str(fixture))

        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        self.assertIn("workflow-installed.json", result.stdout)
        self.assertFalse(record.exists())
        self.assertFalse((fixture / ".trellis" / "scripts" / "workflow").exists())
        self.assertTrue((fixture / ".claude" / "commands" / "trellis" / "continue.md").exists())
        finish_work = (fixture / ".claude" / "commands" / "trellis" / "finish-work.md").read_text(encoding="utf-8")
        self.assertNotIn(FINISH_WORK_MARKER, finish_work)
        self.assertIn("pnpm lint", finish_work)

    def test_uninstall_restores_codex_start_and_finish_work_skills(self) -> None:
        fixture = self.create_fixture(include_codex=True)
        self.addCleanup(shutil.rmtree, fixture)

        install = self.install_workflow(fixture)
        self.assertEqual(install.returncode, 0, msg=install.stdout + install.stderr)
        self.apply_legacy_codex_workflow_state(fixture)
        start_skill = fixture / ".agents" / "skills" / "start" / "SKILL.md"
        self.assertIn("Workflow Phase Router Patch", start_skill.read_text(encoding="utf-8"))
        patched_skill = fixture / ".agents" / "skills" / "finish-work" / "SKILL.md"
        self.assertIn(FINISH_WORK_MARKER, patched_skill.read_text(encoding="utf-8"))

        result = self.run_script(UNINSTALL_SCRIPT, "--project-root", str(fixture))

        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        start_text = start_skill.read_text(encoding="utf-8")
        self.assertNotIn("Workflow Phase Router Patch", start_text)
        self.assertIn("## Step 4: Decide next action", start_text)
        restored_text = patched_skill.read_text(encoding="utf-8")
        self.assertNotIn(FINISH_WORK_MARKER, restored_text)
        self.assertIn("pnpm lint", restored_text)

    def test_uninstall_restores_codex_skills_when_record_lacks_patched_codex_skills(self) -> None:
        fixture = self.create_fixture(include_codex=True)
        self.addCleanup(shutil.rmtree, fixture)

        install = self.install_workflow(fixture)
        self.assertEqual(install.returncode, 0, msg=install.stdout + install.stderr)
        self.apply_legacy_codex_workflow_state(fixture)
        record_path = fixture / ".trellis" / "workflow-installed.json"
        record_data = json.loads(record_path.read_text(encoding="utf-8"))
        record_data.pop("patched_codex_skills", None)
        record_path.write_text(json.dumps(record_data, ensure_ascii=False, indent=2), encoding="utf-8")

        start_skill = fixture / ".agents" / "skills" / "start" / "SKILL.md"
        patched_skill = fixture / ".agents" / "skills" / "finish-work" / "SKILL.md"
        self.assertIn("Workflow Phase Router Patch", start_skill.read_text(encoding="utf-8"))
        self.assertIn(FINISH_WORK_MARKER, patched_skill.read_text(encoding="utf-8"))

        result = self.run_script(UNINSTALL_SCRIPT, "--project-root", str(fixture))

        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        self.assertNotIn("Workflow Phase Router Patch", start_skill.read_text(encoding="utf-8"))
        self.assertNotIn(FINISH_WORK_MARKER, patched_skill.read_text(encoding="utf-8"))

    def test_uninstall_restores_overlapped_baseline_check_command(self) -> None:
        fixture = self.create_fixture()
        self.addCleanup(shutil.rmtree, fixture)

        install = self.install_workflow(fixture)
        self.assertEqual(install.returncode, 0, msg=install.stdout + install.stderr)
        patched_check = fixture / ".claude" / "commands" / "trellis" / "check.md"
        self.assertIn("/trellis:check", patched_check.read_text(encoding="utf-8"))
        self.assertEqual(
            (fixture / ".claude" / "commands" / "trellis" / ".backup-original" / "check.md").read_text(encoding="utf-8"),
            BASELINE_CHECK_CONTENT,
        )

        result = self.run_script(UNINSTALL_SCRIPT, "--project-root", str(fixture))

        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        restored_text = patched_check.read_text(encoding="utf-8")
        self.assertEqual(restored_text, BASELINE_CHECK_CONTENT)

    def test_uninstall_restores_overlapped_baseline_brainstorm_command(self) -> None:
        fixture = self.create_fixture()
        self.addCleanup(shutil.rmtree, fixture)

        install = self.install_workflow(fixture)
        self.assertEqual(install.returncode, 0, msg=install.stdout + install.stderr)
        patched_brainstorm = fixture / ".claude" / "commands" / "trellis" / "brainstorm.md"
        self.assertIn("/trellis:brainstorm", patched_brainstorm.read_text(encoding="utf-8"))
        self.assertEqual(
            (fixture / ".claude" / "commands" / "trellis" / ".backup-original" / "brainstorm.md").read_text(encoding="utf-8"),
            BASELINE_BRAINSTORM_CONTENT,
        )

        result = self.run_script(UNINSTALL_SCRIPT, "--project-root", str(fixture))

        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        restored_text = patched_brainstorm.read_text(encoding="utf-8")
        self.assertEqual(restored_text, BASELINE_BRAINSTORM_CONTENT)

    def test_uninstall_restores_disabled_parallel_command(self) -> None:
        fixture = self.create_fixture()
        self.addCleanup(shutil.rmtree, fixture)

        install = self.install_workflow(fixture)
        self.assertEqual(install.returncode, 0, msg=install.stdout + install.stderr)
        patched_parallel = fixture / ".claude" / "commands" / "trellis" / "parallel.md"
        self.assertFalse(patched_parallel.exists())
        self.assertEqual(
            (fixture / ".claude" / "commands" / "trellis" / ".backup-original" / "parallel.md").read_text(encoding="utf-8"),
            BASELINE_PARALLEL_CONTENT,
        )

        result = self.run_script(UNINSTALL_SCRIPT, "--project-root", str(fixture))

        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        restored_text = patched_parallel.read_text(encoding="utf-8")
        self.assertEqual(restored_text, BASELINE_PARALLEL_CONTENT)

    def test_uninstall_removes_agents_md_routing_section(self) -> None:
        fixture = self.create_fixture(include_opencode=True, include_codex=True, include_agents_md=True)
        self.addCleanup(shutil.rmtree, fixture)

        install = self.install_workflow(fixture)
        self.assertEqual(install.returncode, 0, msg=install.stdout + install.stderr)
        self.assertIn("workflow-nl-routing-start", (fixture / "AGENTS.md").read_text(encoding="utf-8"))

        result = self.run_script(UNINSTALL_SCRIPT, "--project-root", str(fixture))

        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        self.assertIn("AGENTS.md NL 路由表已删除", result.stdout)
        self.assertNotIn("workflow-nl-routing-start", (fixture / "AGENTS.md").read_text(encoding="utf-8"))

    def test_uninstall_leaves_default_todo_file_untouched(self) -> None:
        fixture = self.create_fixture()
        self.addCleanup(shutil.rmtree, fixture)

        install = self.install_workflow(fixture)
        self.assertEqual(install.returncode, 0, msg=install.stdout + install.stderr)
        self.assertTrue((fixture / "todo.txt").exists())

        result = self.run_script(UNINSTALL_SCRIPT, "--project-root", str(fixture))

        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        self.assertNotIn("todo.txt 已删除", result.stdout)
        self.assertEqual((fixture / "todo.txt").read_text(encoding="utf-8"), DEFAULT_PROJECT_TODO)

    def test_uninstall_leaves_modified_todo_file_untouched(self) -> None:
        fixture = self.create_fixture()
        self.addCleanup(shutil.rmtree, fixture)

        install = self.install_workflow(fixture)
        self.assertEqual(install.returncode, 0, msg=install.stdout + install.stderr)
        todo_path = fixture / "todo.txt"
        todo_path.write_text("自定义提醒\n", encoding="utf-8")

        result = self.run_script(UNINSTALL_SCRIPT, "--project-root", str(fixture))

        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        self.assertNotIn("todo.txt 已被修改，保留现有内容", result.stdout)
        self.assertEqual(todo_path.read_text(encoding="utf-8"), "自定义提醒\n")


if __name__ == "__main__":
    unittest.main()
