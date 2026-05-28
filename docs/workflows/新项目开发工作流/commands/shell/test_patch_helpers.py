from __future__ import annotations

import importlib.util
import io
import json
import shutil
import subprocess
import tempfile
import unittest
from contextlib import redirect_stderr
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[5]
PYTHON = (
    "/ops/softwares/python/bin/python3"
    if Path("/ops/softwares/python/bin/python3").exists()
    else shutil.which("python3") or shutil.which("python")
)
SHELL_DIR = REPO_ROOT / "docs" / "workflows" / "新项目开发工作流" / "commands" / "shell"
PATCH_SCRIPTS = [
    SHELL_DIR / "patch-claude-inject-subagent-context.py",
    SHELL_DIR / "patch-inject-workflow-state.py",
    SHELL_DIR / "patch-session-start-strong-gate.py",
    SHELL_DIR / "patch-task-start-strong-gate.py",
    SHELL_DIR / "patch-task-create-preserve-active.py",
    SHELL_DIR / "patch-task-status-view-strong-gate.py",
    SHELL_DIR / "patch-workflow-phase.py",
    SHELL_DIR / "patch-workflow-phase-strong-gate.py",
]


class PatchHelperScriptTests(unittest.TestCase):
    def test_patch_helpers_support_help(self) -> None:
        for script in PATCH_SCRIPTS:
            with self.subTest(script=script.name):
                result = subprocess.run(
                    [PYTHON, str(script), "--help"],
                    cwd=REPO_ROOT,
                    text=True,
                    capture_output=True,
                    check=False,
                )

                self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
                self.assertIn("usage:", result.stdout.lower())
                self.assertNotIn("does not exist", result.stdout + result.stderr)
                self.assertNotIn("不存在", result.stdout + result.stderr)

    def test_patch_workflow_phase_preserves_docstring(self) -> None:
        root = Path(tempfile.mkdtemp(prefix="workflow-phase-docstring-"))
        self.addCleanup(shutil.rmtree, root)
        target = root / "workflow_phase.py"
        target.write_text(
            "def get_step(step_id):\n"
            "    \"\"\"Return the legacy step body.\"\"\"\n"
            "    return f'legacy step {step_id}'\n",
            encoding="utf-8",
        )

        spec = importlib.util.spec_from_file_location("patch_workflow_phase", SHELL_DIR / "patch-workflow-phase.py")
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        applied = module.patch_workflow_phase(target)
        self.assertTrue(applied, "patch_workflow_phase should patch the docstring fixture")

        runtime_spec = importlib.util.spec_from_file_location("patched_workflow_phase_docstring", target)
        self.assertIsNotNone(runtime_spec)
        self.assertIsNotNone(runtime_spec.loader)
        runtime_module = importlib.util.module_from_spec(runtime_spec)
        runtime_spec.loader.exec_module(runtime_module)

        self.assertEqual(runtime_module.get_step.__doc__, "Return the legacy step body.")

    def test_patch_task_start_refreshes_help_and_usage_text(self) -> None:
        root = Path(tempfile.mkdtemp(prefix="task-start-help-"))
        self.addCleanup(shutil.rmtree, root)
        target = root / "task.py"
        target.write_text(
            "from common.log import Colors, colored\n"
            "from common.io import read_json, write_json\n\n"
            "def cmd_start(args):\n"
            "    if task_json_path.is_file():\n"
            "        data = read_json(task_json_path)\n"
            "        if data and data.get(\"status\") == \"planning\":\n"
            "            data[\"status\"] = \"in_progress\"\n"
            "            if write_json(task_json_path, data):\n"
            "                print(colored(\"✓ Status: planning → in_progress\", Colors.GREEN))\n"
            "    return 0\n\n"
            "def show_usage():\n"
            "    print(\"  python3 task.py start <dir>                        Set active task\\n\")\n\n"
            "def build_parser():\n"
            "    p_start = subparsers.add_parser(\"start\", help=\"Set active task\")\n",
            encoding="utf-8",
        )

        spec = importlib.util.spec_from_file_location("patch_task_start", SHELL_DIR / "patch-task-start-strong-gate.py")
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        applied = module.patch_task_start(target)
        self.assertTrue(applied, "patch_task_start should patch the task.py fixture")

        patched = target.read_text(encoding="utf-8")
        self.assertIn("strong-gate: refresh pointer only", patched)
        self.assertIn("stage changes still go through workflow-state.py", patched)

    def test_patch_task_store_archive_guard_blocks_without_finish_work_checklist(self) -> None:
        root = Path(tempfile.mkdtemp(prefix="task-store-archive-guard-"))
        self.addCleanup(shutil.rmtree, root)
        package_dir = root / "pkg"
        package_dir.mkdir(parents=True, exist_ok=True)
        (package_dir / "__init__.py").write_text("", encoding="utf-8")
        (package_dir / "active_task.py").write_text(
            "def resolve_context_key():\n"
            "    return None\n\n"
            "def set_active_task(task_dir, repo_root):\n"
            "    return None\n",
            encoding="utf-8",
        )
        target = package_dir / "task_store.py"
        target.write_text(
            "import json\n"
            "import sys\n"
            "from pathlib import Path\n\n"
            "class Colors:\n"
            "    RED = 'red'\n\n"
            "def colored(message, _color):\n"
            "    return message\n\n"
            "FILE_TASK_JSON = 'task.json'\n\n"
            "def get_repo_root():\n"
            "    return Path(__file__).resolve().parents[1]\n\n"
            "def read_json(path):\n"
            "    return json.loads(path.read_text(encoding='utf-8')) if path.is_file() else None\n\n"
            "def write_json(path, data):\n"
            "    path.write_text(json.dumps(data), encoding='utf-8')\n"
            "    return True\n\n"
            "def cmd_create(args):\n"
            "    repo_root = get_repo_root()\n"
            "    task_dir = repo_root / '.trellis' / 'tasks' / 'sample'\n"
            "    try:\n"
            "        from .active_task import resolve_context_key, set_active_task\n"
            "        if resolve_context_key():\n"
            "            set_active_task('sample', repo_root)\n"
            "    except Exception:\n"
            "        pass\n"
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
            "    return 0\n",
            encoding="utf-8",
        )
        task_dir = root / ".trellis" / "tasks" / "sample"
        task_dir.mkdir(parents=True, exist_ok=True)
        (task_dir / "task.json").write_text('{"status": "in_progress"}\n', encoding="utf-8")
        (task_dir / "workflow-state.json").write_text('{"stage": "delivery"}\n', encoding="utf-8")

        spec = importlib.util.spec_from_file_location("patch_task_store", SHELL_DIR / "patch-task-create-preserve-active.py")
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        self.assertTrue(module.patch_task_store(target))

        import sys as _sys
        if str(root) not in _sys.path:
            _sys.path.insert(0, str(root))
        runtime_spec = importlib.util.spec_from_file_location("pkg.task_store", target)
        self.assertIsNotNone(runtime_spec)
        self.assertIsNotNone(runtime_spec.loader)
        runtime_module = importlib.util.module_from_spec(runtime_spec)
        runtime_spec.loader.exec_module(runtime_module)

        stderr = io.StringIO()
        with redirect_stderr(stderr):
            result = runtime_module.cmd_archive(object())
        self.assertEqual(result, 1)
        self.assertIn("finish-work-checklist.md", stderr.getvalue())

    def test_patch_task_store_archive_guard_allows_archive_after_validate_passes(self) -> None:
        root = Path(tempfile.mkdtemp(prefix="task-store-archive-allow-"))
        self.addCleanup(shutil.rmtree, root)
        package_dir = root / "pkg"
        package_dir.mkdir(parents=True, exist_ok=True)
        (package_dir / "__init__.py").write_text("", encoding="utf-8")
        (package_dir / "active_task.py").write_text(
            "def resolve_context_key():\n"
            "    return None\n\n"
            "def set_active_task(task_dir, repo_root):\n"
            "    return None\n",
            encoding="utf-8",
        )
        target = package_dir / "task_store.py"
        target.write_text(
            "import json\n"
            "import sys\n"
            "from pathlib import Path\n\n"
            "class Colors:\n"
            "    RED = 'red'\n\n"
            "def colored(message, _color):\n"
            "    return message\n\n"
            "FILE_TASK_JSON = 'task.json'\n\n"
            "def get_repo_root():\n"
            "    return Path(__file__).resolve().parents[1]\n\n"
            "def read_json(path):\n"
            "    return json.loads(path.read_text(encoding='utf-8')) if path.is_file() else None\n\n"
            "def write_json(path, data):\n"
            "    path.write_text(json.dumps(data), encoding='utf-8')\n"
            "    return True\n\n"
            "def cmd_create(args):\n"
            "    repo_root = get_repo_root()\n"
            "    task_dir = repo_root / '.trellis' / 'tasks' / 'sample'\n"
            "    try:\n"
            "        from .active_task import resolve_context_key, set_active_task\n"
            "        if resolve_context_key():\n"
            "            set_active_task('sample', repo_root)\n"
            "    except Exception:\n"
            "        pass\n"
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
            "    return 0\n",
            encoding="utf-8",
        )
        task_dir = root / ".trellis" / "tasks" / "sample"
        task_dir.mkdir(parents=True, exist_ok=True)
        (task_dir / "task.json").write_text('{"status": "in_progress"}\n', encoding="utf-8")
        (task_dir / "workflow-state.json").write_text('{"stage": "delivery"}\n', encoding="utf-8")
        (task_dir / "finish-work-checklist.md").write_text("ok\n", encoding="utf-8")
        workflow_dir = root / ".trellis" / "scripts" / "workflow"
        workflow_dir.mkdir(parents=True, exist_ok=True)
        (workflow_dir / "workflow-state.py").write_text(
            "#!/usr/bin/env python3\n"
            "from __future__ import annotations\n"
            "import sys\n"
            "print('ok')\n"
            "raise SystemExit(0)\n",
            encoding="utf-8",
        )

        spec = importlib.util.spec_from_file_location("patch_task_store", SHELL_DIR / "patch-task-create-preserve-active.py")
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        self.assertTrue(module.patch_task_store(target))

        import sys as _sys
        if str(root) not in _sys.path:
            _sys.path.insert(0, str(root))
        runtime_spec = importlib.util.spec_from_file_location("pkg.task_store", target)
        self.assertIsNotNone(runtime_spec)
        self.assertIsNotNone(runtime_spec.loader)
        runtime_module = importlib.util.module_from_spec(runtime_spec)
        runtime_spec.loader.exec_module(runtime_module)

        stderr = io.StringIO()
        with redirect_stderr(stderr):
            result = runtime_module.cmd_archive(object())
        self.assertEqual(result, 0)
        self.assertEqual(stderr.getvalue(), "")

    def test_patch_inject_workflow_state_maps_stale_suffixes_to_stale_block(self) -> None:
        root = Path(tempfile.mkdtemp(prefix="inject-workflow-state-stale-"))
        self.addCleanup(shutil.rmtree, root)
        target = root / "inject-workflow-state.py"
        target.write_text(
            "import re\n"
            "from pathlib import Path\n"
            "from typing import Optional\n\n"
            "def get_active_task(root: Path, input_data: dict):\n"
            "    active = input_data['active']\n"
            "    task_id = active.task_path\n"
            "    task_dir = root / task_id\n"
            "    if active.stale:\n"
            "        return task_dir.name, f\"stale_{active.source_type}\", active.source\n"
            "    data = {'status': 'planning'}\n"
            "    status = data.get('status', '')\n"
            "    if not status:\n"
            "        return None\n"
            "    return task_id, status, active.source\n\n"
            "# ---------------------------------------------------------------------------\n"
            "# Breadcrumb loading: parse workflow.md, fall back to hardcoded defaults\n"
            "# ---------------------------------------------------------------------------\n"
            "def load_breadcrumbs(root: Path) -> dict[str, str]:\n"
            "    workflow = root / \".trellis\" / \"workflow.md\"\n"
            "    if not workflow.is_file():\n"
            "        return {}\n"
            "    try:\n"
            "        content = workflow.read_text(encoding=\"utf-8\")\n"
            "    except OSError:\n"
            "        return {}\n"
            "    result: dict[str, str] = {}\n"
            "    return result\n\n"
            "def build_breadcrumb(\n"
            "    task_id: Optional[str],\n"
            "    status: str,\n"
            "    templates: dict[str, str],\n"
            "    source: str | None = None,\n"
            "    breadcrumb_key: str | None = None,\n"
            ") -> str:\n"
            "    lookup_key = breadcrumb_key or status\n"
            "    body = templates.get(lookup_key)\n"
            "    if body is None and lookup_key != status:\n"
            "        body = templates.get(status)\n"
            "    if body is None:\n"
            "        body = 'Refer to workflow.md for current step.'\n"
            "    header_lines = [f'Status: {status}' if task_id is None else f'Task: {task_id} ({status})']\n"
            "    if source:\n"
            "        header_lines.append(f'Source: {source}')\n"
            "    header = '\\n'.join(header_lines)\n"
            "    return f'<workflow-state>\\n{header}\\n{body}\\n</workflow-state>'\n\n"
            "# ---------------------------------------------------------------------------\n"
            "# Entry\n"
            "# ---------------------------------------------------------------------------\n"
            "def main() -> int:\n"
            "    templates = {}\n"
            "    task = ('task', 'stale_session', 'session:demo')\n"
            "    if task is None:\n"
            "        return 0\n"
            "    else:\n"
            "        task_id, status, source = task\n"
            "        status_key = status\n"
            "        breadcrumb = build_breadcrumb(\n"
            "            task_id, status, templates, source, breadcrumb_key=status_key\n"
            "        )\n"
            "    return 0\n",
            encoding="utf-8",
        )

        spec = importlib.util.spec_from_file_location("patch_inject_workflow_state", SHELL_DIR / "patch-inject-workflow-state.py")
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        applied = module.patch_python_hook(target)
        self.assertTrue(applied, "patch_python_hook should patch stale suffix handling")

        patched = target.read_text(encoding="utf-8")
        self.assertIn('status.startswith("stale_")', patched)
        self.assertIn('lookup_key.startswith("stale_")', patched)
        self.assertIn('lookup_key = "stale"', patched)
        self.assertIn('display_status = "stale"', patched)

    def test_patch_opencode_inject_subagent_context_adds_block_feedback(self) -> None:
        root = Path(tempfile.mkdtemp(prefix="opencode-subagent-guard-"))
        self.addCleanup(shutil.rmtree, root)
        node = shutil.which("node")
        if not node:
            self.skipTest("node is required for OpenCode plugin runtime verification")

        (root / "package.json").write_text('{"type":"module"}\n', encoding="utf-8")
        (root / "plugins").mkdir(parents=True, exist_ok=True)
        (root / "lib").mkdir(parents=True, exist_ok=True)
        (root / "lib" / "trellis-context.js").write_text(
            "export class TrellisContext {\n"
            "  constructor(directory) { this.directory = directory }\n"
            "  getContextKey() { return null }\n"
            "  readContext() { return null }\n"
            "  normalizeTaskRef(taskRef) { return taskRef }\n"
            "  resolveTaskDir(taskRef) { return taskRef }\n"
            "  _resolveSingleSessionFallback() { return null }\n"
            "}\n"
            "export function debugLog() {}\n",
            encoding="utf-8",
        )
        target = root / "plugins" / "inject-subagent-context.js"
        target.write_text(
            (REPO_ROOT / ".opencode" / "plugins" / "inject-subagent-context.js").read_text(encoding="utf-8"),
            encoding="utf-8",
        )

        spec = importlib.util.spec_from_file_location(
            "patch_opencode_inject_subagent_context",
            SHELL_DIR / "patch-opencode-inject-subagent-context.py",
        )
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        applied = module.patch_opencode_inject_subagent_context(target)
        self.assertTrue(applied, "OpenCode subagent patch should apply to the fixture")

        patched = target.read_text(encoding="utf-8")
        self.assertIn('const STRONG_GATE_BLOCKED_ERROR_NAME = "TrellisStrongGateBlockedError"', patched)
        self.assertIn("buildBlockedSubagentPrompt(routeData, subagentType, originalPrompt)", patched)
        self.assertIn("buildBlockedSubagentError(routeData, subagentType, originalPrompt)", patched)
        self.assertIn("Strong-gate blocked this subagent dispatch.", patched)
        self.assertIn("current embedded workflow disables agent/subagent execution paths", patched)
        self.assertIn("JSON.parse(raw)", patched)
        self.assertIn("Embedded workflow keeps all Task-based subagent execution disabled.", patched)
        self.assertIn("blockedError.name = STRONG_GATE_BLOCKED_ERROR_NAME", patched)
        self.assertIn("throw blockedError", patched)
        self.assertIn("error.name === STRONG_GATE_BLOCKED_ERROR_NAME", patched)
        self.assertIn("throw error", patched)
        self.assertNotIn(': "unknown"', patched)

        runner = root / "runner.mjs"
        runner.write_text(
            "import { pathToFileURL } from 'node:url'\n"
            "const [pluginPath, directory] = process.argv.slice(2)\n"
            "const mod = await import(pathToFileURL(pluginPath).href)\n"
            "const hooks = await mod.default({ directory, platform: process.platform, env: process.env })\n"
            "try {\n"
            "  await hooks['tool.execute.before'](\n"
            "    { tool: 'task' },\n"
            "    { args: { subagent_type: 'trellis-check', prompt: 'run checks' } },\n"
            "  )\n"
            "  console.log(JSON.stringify({ status: 'no-throw' }))\n"
            "} catch (error) {\n"
            "  console.log(JSON.stringify({ status: 'threw', name: error?.name || '', message: String(error?.message || '') }))\n"
            "}\n",
            encoding="utf-8",
        )
        runtime = subprocess.run(
            [node, str(runner), str(target), str(root)],
            cwd=root,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(runtime.returncode, 0, msg=runtime.stdout + runtime.stderr)
        payload = json.loads(runtime.stdout.strip())
        self.assertEqual(payload["status"], "threw")
        self.assertEqual(payload["name"], "TrellisStrongGateBlockedError")
        self.assertIn("Strong-gate blocked this subagent dispatch.", payload["message"])

    def test_patch_opencode_inject_subagent_context_upgrades_intermediate_route_guard(self) -> None:
        root = Path(tempfile.mkdtemp(prefix="opencode-subagent-intermediate-"))
        self.addCleanup(shutil.rmtree, root)
        target = root / "inject-subagent-context.js"
        target.write_text(
            'const ACTIVE_TASK_HINT_RE = /^\\s*Active task:\\s*(\\S+)\\s*$/m\n'
            'import { join } from "path"\n'
            'import { execFileSync } from "child_process"\n'
            "function injectTrellisContextIntoBash(ctx, input, output, hostPlatform, env) {\n"
            "  return true\n"
            "}\n"
            "async function before(ctx, input, output) {\n"
            "  const args = output?.args\n"
            "  const subagentType = 'check'\n"
            "  const originalPrompt = args.prompt || ''\n"
            "  let taskDir = null\n"
            "          if (!taskDir) {\n"
            "            const fallback = ctx._resolveSingleSessionFallback()\n"
            "            if (fallback?.taskPath) {\n"
            "              const fallbackDir = ctx.resolveTaskDir(fallback.taskPath)\n"
            "              if (fallbackDir && existsSync(fallbackDir)) {\n"
            "                taskDir = fallback.taskPath\n"
            "                taskSource = fallback.source\n"
            "                debugLog(\"inject\", \"Resolved task via single-session fallback:\", taskDir, \"source:\", taskSource)\n"
            "              }\n"
            "            }\n"
            "          }\n"
            "          const routeData = taskDir ? loadRouteData(ctx, ctx.resolveTaskDir(taskDir)) : null\n"
            "          if (!shouldAllowTaskInjection(routeData, subagentType)) {\n"
            "            const blockedMessage = buildBlockedSubagentPrompt(routeData, subagentType, originalPrompt)\n"
            "            debugLog(\"inject\", \"Skipping - strong-gate route does not allow subagent injection\", JSON.stringify(routeData))\n"
            "            throw new Error(blockedMessage)\n"
            "          }\n"
            "        } catch (error) {\n"
            "          debugLog(\"inject\", \"Error in tool.execute.before:\", error.message, error.stack)\n"
            "        }\n"
            "}\n",
            encoding="utf-8",
        )

        spec = importlib.util.spec_from_file_location(
            "patch_opencode_inject_subagent_context",
            SHELL_DIR / "patch-opencode-inject-subagent-context.py",
        )
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        applied = module.patch_opencode_inject_subagent_context(target)
        self.assertTrue(applied, "OpenCode subagent patch should upgrade intermediate guard")

        patched = target.read_text(encoding="utf-8")
        self.assertIn("buildBlockedSubagentError(routeData, subagentType, originalPrompt)", patched)
        self.assertIn("throw blockedError", patched)
        self.assertNotIn("throw new Error(blockedMessage)", patched)

    def test_patch_claude_inject_subagent_context_blocks_dispatch(self) -> None:
        root = Path(tempfile.mkdtemp(prefix="claude-subagent-guard-"))
        self.addCleanup(shutil.rmtree, root)
        target = root / "inject-subagent-context.py"
        target.write_text(
            "import json\n"
            "import sys\n"
            "AGENT_IMPLEMENT = \"trellis-implement\"\n"
            "AGENT_CHECK = \"trellis-check\"\n"
            "AGENT_RESEARCH = \"trellis-research\"\n"
            "AGENTS_ALL = (AGENT_IMPLEMENT, AGENT_CHECK, AGENT_RESEARCH)\n"
            "\n"
            "def main():\n"
            "    subagent_type = \"trellis-research\"\n"
            "    original_prompt = \"do work\"\n"
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

        spec = importlib.util.spec_from_file_location(
            "patch_claude_inject_subagent_context",
            SHELL_DIR / "patch-claude-inject-subagent-context.py",
        )
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        applied = module.patch_claude_inject_subagent_context(target)
        self.assertTrue(applied, "Claude subagent patch should apply to the fixture")

        patched = target.read_text(encoding="utf-8")
        self.assertIn("# [workflow-embed-patch:claude-subagent-gates]", patched)
        self.assertIn("def _emit_blocked_subagent_output(", patched)
        self.assertIn("Strong-gate blocked this subagent dispatch.", patched)
        self.assertIn("current embedded workflow disables agent/subagent execution paths", patched)
        self.assertIn('"permissionDecision": "deny"', patched)
        self.assertIn('"permission": "deny"', patched)
        self.assertIn("_emit_blocked_subagent_output(subagent_type, original_prompt, tool_input)", patched)
        self.assertNotIn("repo_root = \"/tmp\"", patched)

    def test_patch_session_start_replaces_subagent_guidance_with_main_session_only(self) -> None:
        root = Path(tempfile.mkdtemp(prefix="session-start-guidance-"))
        self.addCleanup(shutil.rmtree, root)
        target = root / "session-start.py"
        target.write_text(
            "def _get_task_status():\n"
            "    task_status = task_data.get(\"status\", \"unknown\")\n"
            "    return task_status\n"
            "\n"
            "def _load_trellis_config():\n"
            "    return {}\n"
            "\n"
            "def build_session_context(output):\n"
            "    output.write(\n"
            "        \"Project spec indexes are listed by path below. Each index contains a \"\n"
            "        \"**Pre-Development Checklist** listing the specific guideline files to \"\n"
            "        \"read before coding.\\n\\n\"\n"
            "        \"- If you're spawning an implement/check sub-agent, context is injected \"\n"
            "        \"or loaded by the sub-agent via `{task}/implement.jsonl` / `check.jsonl`. \"\n"
            "        \"You do NOT need to read these indexes yourself.\\n\"\n"
            "        \"- For agent-capable platforms, the default is to dispatch \"\n"
            "        \"`trellis-implement` and `trellis-check` (so JSONL context is loaded by \"\n"
            "        \"the sub-agents) rather than editing code in the main session. \"\n"
            "        \"Honor a per-turn user override only if the user's current message \"\n"
            "        \"explicitly opts out (see <task-status> below for override phrases).\\n\"\n"
            "        \"- Sub-agent self-exemption: if you are reading this as a `trellis-implement` \"\n"
            "        \"or `trellis-check` sub-agent, the \\\"dispatch trellis-implement / trellis-check\\\" \"\n"
            "        \"rule above does NOT apply to you — you are already the dispatched sub-agent. \"\n"
            "        \"Do NOT spawn another sub-agent of the same kind; implement / check directly.\\n\\n\"\n"
            "    )\n"
            "\n"
            "def main():\n"
            "    return 0\n",
            encoding="utf-8",
        )

        spec = importlib.util.spec_from_file_location(
            "patch_session_start_strong_gate",
            SHELL_DIR / "patch-session-start-strong-gate.py",
        )
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        applied = module.patch_session_start(target)
        self.assertTrue(applied, "session-start guidance patch should apply to the fixture")

        patched = target.read_text(encoding="utf-8")
        self.assertIn("explicitly disables `agent / sub-agent` execution paths", patched)
        self.assertIn("return control to the main session", patched)
        self.assertNotIn("the default is to dispatch", patched)

    def test_patch_session_start_replaces_codex_subagent_guidance_variant(self) -> None:
        root = Path(tempfile.mkdtemp(prefix="session-start-guidance-codex-"))
        self.addCleanup(shutil.rmtree, root)
        target = root / "session-start.py"
        target.write_text(
            "def _get_task_status():\n"
            "    task_status = task_data.get(\"status\", \"unknown\")\n"
            "    return task_status\n"
            "\n"
            "def _load_trellis_config():\n"
            "    return {}\n"
            "\n"
            "def build_session_context(output):\n"
            "    output.write(\n"
            "        \"Project spec indexes are listed by path below. Each index contains a \"\n"
            "        \"**Pre-Development Checklist** listing the specific guideline files to \"\n"
            "        \"read before coding.\\n\\n\"\n"
            "        \"- If you're spawning an implement/check sub-agent, context is injected \"\n"
            "        \"automatically via `{task}/implement.jsonl` / `check.jsonl`. You do NOT \"\n"
            "        \"need to read these indexes yourself.\\n\"\n"
            "        \"- For agent-capable platforms, the default is to dispatch \"\n"
            "        \"`trellis-implement` and `trellis-check` (so JSONL context is loaded by \"\n"
            "        \"the sub-agents) rather than editing code in the main session. \"\n"
            "        \"Honor a per-turn user override only if the user's current message \"\n"
            "        \"explicitly opts out (see <task-status> below for override phrases).\\n\"\n"
            "        \"- Sub-agent self-exemption: if you are reading this as a `trellis-implement` \"\n"
            "        \"or `trellis-check` sub-agent, the \\\"dispatch trellis-implement / trellis-check\\\" \"\n"
            "        \"rule above does NOT apply to you — you are already the dispatched sub-agent. \"\n"
            "        \"Do NOT spawn another sub-agent of the same kind; implement / check directly.\\n\\n\"\n"
            "    )\n"
            "\n"
            "def main():\n"
            "    return 0\n",
            encoding="utf-8",
        )

        spec = importlib.util.spec_from_file_location(
            "patch_session_start_strong_gate",
            SHELL_DIR / "patch-session-start-strong-gate.py",
        )
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        applied = module.patch_session_start(target)
        self.assertTrue(applied, "codex session-start guidance patch should apply to the fixture")

        patched = target.read_text(encoding="utf-8")
        self.assertIn("explicitly disables `agent / sub-agent` execution paths", patched)
        self.assertNotIn("the default is to dispatch", patched)

    def test_patch_python_hook_forces_codex_inline_mode(self) -> None:
        root = Path(tempfile.mkdtemp(prefix="codex-inline-hook-"))
        self.addCleanup(shutil.rmtree, root)
        target = root / "inject-workflow-state.py"
        target.write_text(
            "import re\n"
            "import sys\n"
            "from pathlib import Path\n"
            "\n"
            "def load_breadcrumbs(workflow: Path):\n"
            "    if workflow:\n"
            "        content = workflow.read_text(encoding=\"utf-8\")\n"
            "        return []\n"
            "    return []\n"
            "\n"
            "def get_active_task(root: Path, input_data: dict):\n"
            "    task_id = \"task-1\"\n"
            "    status = \"planning\"\n"
            "    active = type(\"Active\", (), {\"source\": \"session\"})()\n"
            "    return task_id, status, active.source\n"
            "\n"
            "def _codex_mode_banner(config: dict) -> str:\n"
            "    mode = \"inline\"\n"
            "    if isinstance(config, dict):\n"
            "        codex_cfg = config.get(\"codex\")\n"
            "        if isinstance(codex_cfg, dict):\n"
            "            cfg_mode = codex_cfg.get(\"dispatch_mode\")\n"
            "            if cfg_mode in (\"inline\", \"sub-agent\"):\n"
            "                mode = cfg_mode\n"
            "    return f\"<codex-mode>{mode}</codex-mode>\"\n"
            "\n"
            "def resolve_breadcrumb_key(status: str, platform: str | None, config: dict) -> str:\n"
            "    if platform == \"codex\":\n"
            "        mode = \"inline\"\n"
            "        if isinstance(config, dict):\n"
            "            codex_cfg = config.get(\"codex\")\n"
            "            if isinstance(codex_cfg, dict):\n"
            "                cfg_mode = codex_cfg.get(\"dispatch_mode\")\n"
            "                if cfg_mode in (\"inline\", \"sub-agent\"):\n"
            "                    mode = cfg_mode\n"
            "        return f\"{status}-inline\" if mode == \"inline\" else status\n"
            "    return status\n"
            "\n"
            "def build_breadcrumb(task_id, status, templates, source=None, breadcrumb_key=None, extra_lines=None):\n"
            "    return status\n"
            "\n",
            encoding="utf-8",
        )
        target.write_text(
            target.read_text(encoding="utf-8")
            + "task = get_active_task(root, input_data)\n"
            + "if task:\n"
            + "        task_id, status, source = task\n"
            + "        breadcrumb = build_breadcrumb(\n"
            + "            task_id, status, templates, source, breadcrumb_key=status_key\n"
            + "        )\n",
            encoding="utf-8",
        )

        spec = importlib.util.spec_from_file_location(
            "patch_inject_workflow_state",
            SHELL_DIR / "patch-inject-workflow-state.py",
        )
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        applied = module.patch_python_hook(target)
        self.assertTrue(applied, "python hook patch should apply to the fixture")

        patched = target.read_text(encoding="utf-8")
        self.assertIn('return "<codex-mode>inline</codex-mode>"', patched)
        self.assertNotIn('cfg_mode in ("inline", "sub-agent")', patched)


if __name__ == "__main__":
    unittest.main()
