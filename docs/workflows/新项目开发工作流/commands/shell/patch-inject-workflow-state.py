#!/usr/bin/env python3
"""Patch inject-workflow-state hooks to prefer workflow-state.py route.

When installed into a target project, this patch updates Python and JS
inject-workflow-state carriers so their breadcrumb headers are derived from the
authoritative `workflow-state.py route` result instead of collapsing everything
to `workflow-state.json.stage` or `task.json.status`.

The patched carriers still use `.trellis/workflow.md` breadcrumb templates, but
they now treat blocking / repair / confirmation actions as first-class template
keys instead of silently reusing the current stage body. Python carriers also
load the route helper in-process when possible so the hot path does not need a
fresh subprocess on every turn.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

PY_PATCH_MARKER = "# [workflow-embed-patch:prefer-workflow-state-json]"
PY_ROUTE_PATCH_MARKER = "# [workflow-embed-patch:prefer-workflow-route]"
JS_PATCH_MARKER = "// [workflow-embed-patch:prefer-workflow-state-json]"
JS_ROUTE_PATCH_MARKER = "// [workflow-embed-patch:prefer-workflow-route]"

PY_GET_ACTIVE_TASK_BLOCK = """_ACTION_BREADCRUMB_KEYS = {
    "awaiting_confirmation",
    "awaiting_confirmation_with_blockers",
    "blocked",
    "context_needed",
    "repair_needed",
    "recovery_needed",
    "embed_invalid",
    "workflow-state.route_failed",
}


def _load_route_data(root: Path, task_dir: Path) -> tuple[dict | None, str | None]:
    route_script = root / ".trellis" / "scripts" / "workflow" / "workflow-state.py"
    if not route_script.is_file():
        route_script = root / ".trellis" / "scripts" / "workflow-state.py"
    if not route_script.is_file():
        return None, None

    try:
        import argparse as _argparse
        import contextlib as _contextlib
        import importlib.util as _importlib_util
        import io as _io

        cache = getattr(_load_route_data, "_module_cache", {})
        cache_key = str(route_script)
        module = cache.get(cache_key)
        if module is None:
            spec = _importlib_util.spec_from_file_location("_trellis_workflow_state_hook", str(route_script))
            if spec is None or spec.loader is None:
                return None, "workflow-state.py route helper unavailable"
            module = _importlib_util.module_from_spec(spec)
            spec.loader.exec_module(module)
            cache[cache_key] = module
            _load_route_data._module_cache = cache
        if not hasattr(module, "cmd_route"):
            return None, "workflow-state.py route helper unavailable"

        buffer = _io.StringIO()
        with _contextlib.redirect_stdout(buffer):
            exit_code = module.cmd_route(
                _argparse.Namespace(project_root=str(root), task_dir=str(task_dir))
            )
        output = buffer.getvalue().strip()
        if exit_code != 0:
            return None, output.splitlines()[-1] if output else "workflow-state.py route returned non-zero"
        if not output:
            return None, "workflow-state.py route returned empty output"
        return json.loads(output), None
    except Exception as exc:
        return None, f"{type(exc).__name__}: {exc}"


def get_active_task(root: Path, input_data: dict) -> Optional[tuple[str, str, str, list[str]]]:
    \"\"\"Return (task_id, status, source, extra_lines) from the current active task.\"\"\"
    active = _resolve_active_task(root, input_data)
    if not active.task_path:
        return None

    task_dir = Path(active.task_path)
    if not task_dir.is_absolute():
        task_dir = root / task_dir
    if active.stale:
        return task_dir.name, f\"stale_{active.source_type}\", active.source, []

    data: dict = {}
    task_json = task_dir / \"task.json\"
    if task_json.is_file():
        try:
            loaded = json.loads(task_json.read_text(encoding=\"utf-8\"))
            if isinstance(loaded, dict):
                data = loaded
        except (json.JSONDecodeError, OSError):
            data = {}

    task_id = data.get(\"id\") or task_dir.name
    raw_status = data.get(\"status\", \"\")
    status = raw_status if isinstance(raw_status, str) else \"\"

    # [workflow-embed-patch:prefer-workflow-state-json]
    # [workflow-embed-patch:prefer-workflow-route]
    # Prefer workflow-state.py route over task.json.status for strong-gate projects.
    route_source = active.source
    extra_lines: list[str] = []
    route_data, route_error = _load_route_data(root, task_dir)
    if route_data is not None:
        route_stage = route_data.get(\"stage\", \"\")
        route_action = route_data.get(\"action\", \"\")
        route_stage_status = route_data.get(\"stage_status\", \"\")
        route_target = route_data.get(\"target\", \"\")
        route_reason = route_data.get(\"reason\", \"\")
        route_blockers = route_data.get(\"blockers\", [])
        route_warnings = route_data.get(\"warnings\", [])
        uses_action_breadcrumb = isinstance(route_action, str) and route_action in _ACTION_BREADCRUMB_KEYS
        if uses_action_breadcrumb:
            status = route_action
            if isinstance(route_stage, str) and route_stage:
                extra_lines.append(f\"Stage: {route_stage}\")
        elif isinstance(route_stage, str) and route_stage:
            status = route_stage
        elif isinstance(route_action, str) and route_action:
            status = route_action
        if isinstance(route_stage_status, str) and route_stage_status:
            extra_lines.append(f\"Stage-Status: {route_stage_status}\")
        if isinstance(route_target, str) and route_target:
            extra_lines.append(f\"Target-Stage: {route_target}\")
        if isinstance(route_reason, str) and route_reason:
            extra_lines.append(f\"Reason: {route_reason}\")
        if isinstance(route_blockers, list) and route_blockers:
            extra_lines.append(
                \"Blockers: \" + \"; \".join(str(item) for item in route_blockers)
            )
        if isinstance(route_warnings, list) and route_warnings:
            extra_lines.append(
                \"Warnings: \" + \"; \".join(str(item) for item in route_warnings)
            )
        route_source = \"workflow-state.route\"
    elif route_error:
        status = \"workflow-state.route_failed\"
        route_source = \"workflow-state.route_failed\"
        extra_lines.append(f\"Reason: {route_error}\")
    if not status:
        return None
    return task_id, status, route_source, extra_lines
"""

PY_BUILD_BREADCRUMB_BLOCK = """def build_breadcrumb(
    task_id: Optional[str],
    status: str,
    templates: dict[str, str],
    source: str | None = None,
    breadcrumb_key: str | None = None,
    extra_lines: list[str] | None = None,
) -> str:
    \"\"\"Build the <workflow-state>...</workflow-state> block.

    - Known status (tag present in workflow.md) → detailed template body
    - Unknown status (no tag, or workflow.md missing) → generic
      \"Refer to workflow.md for current step.\" line
    - `no_task` pseudo-status (task_id is None) → header omits task info
    \"\"\"
    lookup_key = breadcrumb_key or status
    body = templates.get(lookup_key)
    if body is None and lookup_key != status:
        body = templates.get(status)
    if body is None:
        body = \"Refer to workflow.md for current step.\"

    header_lines = [f\"Status: {status}\" if task_id is None else f\"Task: {task_id} ({status})\"]
    if source:
        header_lines.append(f\"Source: {source}\")
    if extra_lines:
        header_lines.extend(extra_lines)
    header = \"\\n\".join(header_lines)
    return f\"<workflow-state>\\n{header}\\n{body}\\n</workflow-state>\"
"""

JS_GET_ACTIVE_TASK_BLOCK = """const ACTION_BREADCRUMB_KEYS = new Set([
  "awaiting_confirmation",
  "awaiting_confirmation_with_blockers",
  "blocked",
  "context_needed",
  "repair_needed",
  "recovery_needed",
  "embed_invalid",
  "workflow-state.route_failed",
])

function getActiveTask(ctx, platformInput = null) {
  const active = ctx.getActiveTask(platformInput)
  const taskRef = active.taskPath
  if (!taskRef) return null
  const taskDir = ctx.resolveTaskDir(taskRef)
  if (active.stale || !taskDir || !existsSync(taskDir)) {
    return { id: taskRef.split(\"/\").pop(), status: \"stale\", source: active.source, extraLines: [] }
  }
  const taskJsonPath = join(taskDir, \"task.json\")
  let data = {}
  if (existsSync(taskJsonPath)) {
    try {
      const parsed = JSON.parse(readFileSync(taskJsonPath, \"utf-8\"))
      if (parsed && typeof parsed === \"object\" && !Array.isArray(parsed)) {
        data = parsed
      }
    } catch {
      data = {}
    }
  }
  const rawStatus = typeof data.status === \"string\" ? data.status : \"\"
  const id = typeof data.id === \"string\" && data.id ? data.id : taskRef.split(\"/\").pop()

  // [workflow-embed-patch:prefer-workflow-state-json]
  // [workflow-embed-patch:prefer-workflow-route]
  // Prefer workflow-state.py route over task.json.status for strong-gate projects.
  let status = rawStatus
  let source = active.source
  const extraLines = []
  const routeScript = join(ctx.directory, \".trellis\", \"scripts\", \"workflow\", \"workflow-state.py\")
  if (existsSync(routeScript)) {
    try {
      const output = execFileSync(PYTHON_CMD, [
        routeScript,
        \"route\",
        taskDir,
        \"--project-root\",
        ctx.directory,
      ], {
        cwd: ctx.directory,
        timeout: 5000,
        encoding: \"utf-8\",
        stdio: [\"pipe\", \"pipe\", \"pipe\"],
      })
      const routeData = JSON.parse(output)
      const routeStage = typeof routeData.stage === \"string\" ? routeData.stage : \"\"
      const routeAction = typeof routeData.action === \"string\" ? routeData.action : \"\"
      const routeStageStatus = typeof routeData.stage_status === \"string\" ? routeData.stage_status : \"\"
      const routeTarget = typeof routeData.target === \"string\" ? routeData.target : \"\"
      const routeReason = typeof routeData.reason === \"string\" ? routeData.reason : \"\"
      const routeBlockers = Array.isArray(routeData.blockers) ? routeData.blockers : []
      const routeWarnings = Array.isArray(routeData.warnings) ? routeData.warnings : []
      const usesActionBreadcrumb = ACTION_BREADCRUMB_KEYS.has(routeAction)
      if (usesActionBreadcrumb) {
        status = routeAction
        if (routeStage) extraLines.push(`Stage: ${routeStage}`)
      } else if (routeStage) {
        status = routeStage
      } else if (routeAction) {
        status = routeAction
      }
      if (routeStageStatus) extraLines.push(`Stage-Status: ${routeStageStatus}`)
      if (routeTarget) extraLines.push(`Target-Stage: ${routeTarget}`)
      if (routeReason) extraLines.push(`Reason: ${routeReason}`)
      if (routeBlockers.length > 0) extraLines.push(`Blockers: ${routeBlockers.map(item => String(item)).join(\"; \")}`)
      if (routeWarnings.length > 0) extraLines.push(`Warnings: ${routeWarnings.map(item => String(item)).join(\"; \")}`)
      source = \"workflow-state.route\"
    } catch (error) {
      status = "workflow-state.route_failed"
      source = "workflow-state.route_failed"
      extraLines.push(`Reason: ${String(error).split("\\n").pop()}`)
    }
  }
  if (!status) return null
  return { id, status, source, extraLines }
}
"""

JS_BUILD_BREADCRUMB_BLOCK = """function buildBreadcrumb(id, status, templates, source = null, extraLines = []) {
  let body = templates[status]
  if (body === undefined) {
    body = \"Refer to workflow.md for current step.\"
  }
  const headerLines = [id === null ? `Status: ${status}` : `Task: ${id} (${status})`]
  if (source) {
    headerLines.push(`Source: ${source}`)
  }
  if (Array.isArray(extraLines) && extraLines.length > 0) {
    headerLines.push(...extraLines)
  }
  return `<workflow-state>\\n${headerLines.join(\"\\n\")}\\n${body}\\n</workflow-state>`
}
"""

PY_BASELINE_ROUTE_SNIPPET = """# [workflow-embed-patch:prefer-workflow-state-json]
    # [workflow-embed-patch:prefer-workflow-route]
    # Prefer workflow-state.py route over task.json.status for strong-gate projects.
    extra_lines = []
    route_source = active.source
    route_script = root / ".trellis" / "scripts" / "workflow" / "workflow-state.py"
    if not route_script.is_file():
        route_script = root / ".trellis" / "scripts" / "workflow-state.py"
    if route_script.is_file():
        try:
            import json as _json
            import subprocess as _sp
            route_result = _sp.run(
                [
                    sys.executable,
                    str(route_script),
                    "route",
                    str(task_dir),
                    "--project-root",
                    str(root),
                ],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=10,
            )
            if route_result.returncode == 0 and route_result.stdout.strip():
                route_data = _json.loads(route_result.stdout.strip())
                route_stage = route_data.get("stage", "")
                route_action = route_data.get("action", "")
                route_stage_status = route_data.get("stage_status", "")
                route_target = route_data.get("target", "")
                route_reason = route_data.get("reason", "")
                route_blockers = route_data.get("blockers", [])
                route_warnings = route_data.get("warnings", [])
                use_action_status = isinstance(route_action, str) and route_action in {
                    "awaiting_confirmation",
                    "awaiting_confirmation_with_blockers",
                    "blocked",
                    "context_needed",
                    "repair_needed",
                    "recovery_needed",
                    "embed_invalid",
                    "workflow-state.route_failed",
                }
                if use_action_status:
                    status = route_action
                    if isinstance(route_stage, str) and route_stage:
                        extra_lines.append(f"Stage: {route_stage}")
                elif isinstance(route_stage, str) and route_stage:
                    status = route_stage
                elif isinstance(route_action, str) and route_action:
                    status = route_action
                if isinstance(route_stage_status, str) and route_stage_status:
                    extra_lines.append(f"Stage-Status: {route_stage_status}")
                if isinstance(route_target, str) and route_target:
                    extra_lines.append(f"Target-Stage: {route_target}")
                if isinstance(route_reason, str) and route_reason:
                    extra_lines.append(f"Reason: {route_reason}")
                if isinstance(route_blockers, list) and route_blockers:
                    extra_lines.append("Blockers: " + "; ".join(str(item) for item in route_blockers))
                if isinstance(route_warnings, list) and route_warnings:
                    extra_lines.append("Warnings: " + "; ".join(str(item) for item in route_warnings))
                route_source = "workflow-state.route"
            elif route_result.returncode != 0:
                status = "workflow-state.route_failed"
                route_source = "workflow-state.route_failed"
                stderr_summary = route_result.stderr.strip() or route_result.stdout.strip() or "workflow-state.py route returned non-zero"
                extra_lines.append(f"Reason: {stderr_summary.splitlines()[-1]}")
        except Exception as exc:
            status = "workflow-state.route_failed"
            route_source = "workflow-state.route_failed"
            extra_lines.append(f"Reason: {type(exc).__name__}: {exc}")
    return task_id, status, route_source, extra_lines
"""

JS_BASELINE_ROUTE_SNIPPET = """  // [workflow-embed-patch:prefer-workflow-state-json]
  // [workflow-embed-patch:prefer-workflow-route]
  // Prefer workflow-state.py route over task.json.status for strong-gate projects.
  let status = rawStatus
  let source = active.source
  const extraLines = []
  const routeScript = join(ctx.directory, ".trellis", "scripts", "workflow", "workflow-state.py")
  if (existsSync(routeScript)) {
    try {
      const output = execFileSync(PYTHON_CMD, [
        routeScript,
        "route",
        taskDir,
        "--project-root",
        ctx.directory,
      ], {
        cwd: ctx.directory,
        timeout: 5000,
        encoding: "utf-8",
        stdio: ["pipe", "pipe", "pipe"],
      })
      const routeData = JSON.parse(output)
      const routeStage = typeof routeData.stage === "string" ? routeData.stage : ""
      const routeAction = typeof routeData.action === "string" ? routeData.action : ""
      const routeStageStatus = typeof routeData.stage_status === "string" ? routeData.stage_status : ""
      const routeTarget = typeof routeData.target === "string" ? routeData.target : ""
      const routeReason = typeof routeData.reason === "string" ? routeData.reason : ""
      const routeBlockers = Array.isArray(routeData.blockers) ? routeData.blockers : []
      const routeWarnings = Array.isArray(routeData.warnings) ? routeData.warnings : []
      const useActionStatus = new Set([
        "awaiting_confirmation",
        "awaiting_confirmation_with_blockers",
        "blocked",
        "context_needed",
        "repair_needed",
        "recovery_needed",
        "embed_invalid",
        "workflow-state.route_failed",
      ]).has(routeAction)
      if (useActionStatus) {
        status = routeAction
        if (routeStage) extraLines.push(`Stage: ${routeStage}`)
      } else if (routeStage) {
        status = routeStage
      } else if (routeAction) {
        status = routeAction
      }
      if (routeStageStatus) extraLines.push(`Stage-Status: ${routeStageStatus}`)
      if (routeTarget) extraLines.push(`Target-Stage: ${routeTarget}`)
      if (routeReason) extraLines.push(`Reason: ${routeReason}`)
      if (routeBlockers.length > 0) extraLines.push(`Blockers: ${routeBlockers.map(item => String(item)).join("; ")}`)
      if (routeWarnings.length > 0) extraLines.push(`Warnings: ${routeWarnings.map(item => String(item)).join("; ")}`)
      source = "workflow-state.route"
    } catch (error) {
      status = "workflow-state.route_failed"
      source = "workflow-state.route_failed"
      extraLines.push(`Reason: ${String(error).split("\\n").pop()}`)
    }
  }
  if (!status) return null
"""


def _replace_section(content: str, start_token: str, end_token: str, replacement: str) -> str:
    start = content.find(start_token)
    end = content.find(end_token, start)
    if start == -1 or end == -1:
        raise ValueError(f"missing section boundary: {start_token!r} .. {end_token!r}")
    return content[:start] + replacement.rstrip() + "\n\n" + content[end:]


def _ensure_python_code_block_strip(content: str) -> str:
    strip_line = '        content = re.sub(r"```.*?```", "", content, flags=re.DOTALL)\n'
    if strip_line in content:
        return content
    anchor = '        content = workflow.read_text(encoding="utf-8")\n'
    if anchor not in content:
        raise ValueError("python hook missing workflow.read_text anchor")
    return content.replace(anchor, anchor + strip_line, 1)


def _patch_python_baseline_fixture(content: str) -> str:
    patched = content
    if 'import json\n' not in patched:
        patched = patched.replace("import re\n", "import json\nimport re\n", 1)
    if 'from typing import Optional\n' not in patched:
        patched = patched.replace("from pathlib import Path\n\n", "from pathlib import Path\nfrom typing import Optional\n\n", 1)
    if "    return task_id, status, active.source\n" not in patched:
        raise ValueError("python baseline fixture missing active-source return")
    patched = patched.replace("    return task_id, status, active.source\n", PY_BASELINE_ROUTE_SNIPPET, 1)
    return patched


def _ensure_js_code_block_strip(content: str) -> str:
    strip_line = '    content = content.replace(/```[\\s\\S]*?```/g, "")\n'
    if strip_line in content:
        return content
    anchor = '    content = readFileSync(workflowPath, "utf-8")\n'
    if anchor not in content:
        return content
    return content.replace(anchor, anchor + strip_line, 1)


def _ensure_js_route_runtime_deps(content: str) -> str:
    patched = content
    if 'import { execFileSync } from "child_process"\n' not in patched:
        if 'import { TrellisContext, debugLog, isTrellisSubagent } from "../lib/trellis-context.js"\n' in patched:
            patched = patched.replace(
                'import { TrellisContext, debugLog, isTrellisSubagent } from "../lib/trellis-context.js"\n',
                'import { TrellisContext, debugLog, isTrellisSubagent } from "../lib/trellis-context.js"\nimport { execFileSync } from "child_process"\n',
                1,
            )
        elif 'import { TrellisContext } from "../lib/trellis-context.js"\n' in patched:
            patched = patched.replace(
                'import { TrellisContext } from "../lib/trellis-context.js"\n',
                'import { TrellisContext } from "../lib/trellis-context.js"\nimport { execFileSync } from "child_process"\n',
                1,
            )
        elif 'import { join } from "path"\n' in patched:
            patched = patched.replace(
                'import { join } from "path"\n',
                'import { join } from "path"\nimport { execFileSync } from "child_process"\n',
                1,
            )
        else:
            raise ValueError("js hook missing anchor for execFileSync import")
    if 'const PYTHON_CMD = process.env.TRELLIS_PYTHON || "python3"\n' not in patched:
        child_process_anchor = 'import { execFileSync } from "child_process"\n'
        if child_process_anchor not in patched:
            raise ValueError("js hook missing child_process import anchor for PYTHON_CMD")
        patched = patched.replace(
            child_process_anchor,
            child_process_anchor + 'const PYTHON_CMD = process.env.TRELLIS_PYTHON || "python3"\n\n',
            1,
        )
    return patched


def _replace_js_function(content: str, signature_prefix: str, replacement: str) -> str:
    start = content.find(signature_prefix)
    if start == -1:
        raise ValueError(f"missing JS function signature: {signature_prefix}")
    brace_start = content.find("{", start)
    if brace_start == -1:
        raise ValueError(f"missing opening brace for JS function: {signature_prefix}")

    depth = 0
    i = brace_start
    in_single = False
    in_double = False
    in_template = False
    in_line_comment = False
    in_block_comment = False
    escaped = False

    while i < len(content):
        ch = content[i]
        nxt = content[i + 1] if i + 1 < len(content) else ""

        if in_line_comment:
            if ch == "\n":
                in_line_comment = False
            i += 1
            continue
        if in_block_comment:
            if ch == "*" and nxt == "/":
                in_block_comment = False
                i += 2
                continue
            i += 1
            continue
        if in_single:
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == "'":
                in_single = False
            i += 1
            continue
        if in_double:
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == '"':
                in_double = False
            i += 1
            continue
        if in_template:
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == "`":
                in_template = False
            i += 1
            continue

        if ch == "/" and nxt == "/":
            in_line_comment = True
            i += 2
            continue
        if ch == "/" and nxt == "*":
            in_block_comment = True
            i += 2
            continue
        if ch == "'":
            in_single = True
            i += 1
            continue
        if ch == '"':
            in_double = True
            i += 1
            continue
        if ch == "`":
            in_template = True
            i += 1
            continue

        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                end = i + 1
                return content[:start] + replacement.rstrip() + "\n\n" + content[end:]
        i += 1

    raise ValueError(f"unterminated JS function body: {signature_prefix}")


def _patch_js_baseline_fixture(content: str) -> str:
    patched = content
    if 'import { execFileSync } from "child_process"\n' not in patched:
        if 'import { basename, join } from "path"\n' in patched:
            patched = patched.replace(
                'import { basename, join } from "path"\n',
                'import { basename, join } from "path"\nimport { execFileSync } from "child_process"\n',
                1,
            )
        elif 'import { join } from "path"\n' in patched:
            patched = patched.replace(
                'import { join } from "path"\n',
                'import { join } from "path"\nimport { execFileSync } from "child_process"\n',
                1,
            )
        else:
            raise ValueError("js baseline fixture missing path import anchor for execFileSync")
    if 'const PYTHON_CMD = process.env.TRELLIS_PYTHON || "python3"\n' not in patched:
        child_process_anchor = 'import { execFileSync } from "child_process"\n'
        if child_process_anchor not in patched:
            raise ValueError("js baseline fixture missing child_process import anchor for PYTHON_CMD")
        patched = patched.replace(
            child_process_anchor,
            child_process_anchor + 'const PYTHON_CMD = process.env.TRELLIS_PYTHON || "python3"\n\n',
            1,
        )
    if "  const rawStatus = typeof taskData.status === \"string\" ? taskData.status : \"\"\n" not in patched:
        task_status_anchor = "  const taskTitle = taskData.title || taskRef\n"
        if task_status_anchor not in patched:
            raise ValueError("js baseline fixture missing task status anchor")
        patched = patched.replace(
            task_status_anchor,
            task_status_anchor + "  const rawStatus = typeof taskData.status === \"string\" ? taskData.status : \"\"\n\n",
            1,
        )
    return patched


def patch_python_hook(target_path: Path) -> bool:
    """Patch a Python inject-workflow-state.py to prefer workflow-state.py route."""
    if not target_path.is_file():
        print(f"⚠️ {target_path} 不存在，跳过")
        return False

    content = target_path.read_text(encoding="utf-8")
    if (
        PY_ROUTE_PATCH_MARKER in content
        and "workflow-state.route" in content
        and "extra_lines=extra_lines" in content
        and "_ACTION_BREADCRUMB_KEYS" in content
    ):
        print(f"✅ {target_path} 已包含 route-centered workflow-state 补丁，跳过")
        return True

    try:
        patched = _ensure_python_code_block_strip(content)
        if "def build_breadcrumb(" in patched and "# ---------------------------------------------------------------------------\n# Breadcrumb loading: parse workflow.md, fall back to hardcoded defaults" in patched:
            patched = _replace_section(
                patched,
                "def get_active_task(root: Path, input_data: dict)",
                "# ---------------------------------------------------------------------------\n# Breadcrumb loading: parse workflow.md, fall back to hardcoded defaults",
                PY_GET_ACTIVE_TASK_BLOCK,
            )
            patched = _replace_section(
                patched,
                "def build_breadcrumb(",
                "# ---------------------------------------------------------------------------\n# Entry",
                PY_BUILD_BREADCRUMB_BLOCK,
            )
        else:
            patched = _patch_python_baseline_fixture(patched)
    except ValueError as exc:
        print(f"⚠️ {target_path} 缺少预期结构，跳过补丁: {exc}")
        return False

    old_unpack = "        task_id, status, source = task\n"
    new_unpack = "        task_id, status, source, extra_lines = task\n"
    if "def build_breadcrumb(" in patched and "extra_lines=extra_lines" not in patched:
        if old_unpack not in patched:
            print(f"⚠️ {target_path} 中未找到 task 解包逻辑，跳过补丁")
            return False
        patched = patched.replace(old_unpack, new_unpack, 1)

        old_call = (
            "        breadcrumb = build_breadcrumb(\n"
            "            task_id, status, templates, source, breadcrumb_key=status_key\n"
            "        )\n"
        )
        new_call = (
            "        breadcrumb = build_breadcrumb(\n"
            "            task_id,\n"
            "            status,\n"
            "            templates,\n"
            "            source,\n"
            "            breadcrumb_key=status_key,\n"
            "            extra_lines=extra_lines,\n"
            "        )\n"
        )
        if old_call not in patched:
            print(f"⚠️ {target_path} 中未找到 build_breadcrumb 调用，跳过补丁")
            return False
        patched = patched.replace(old_call, new_call, 1)

    target_path.write_text(patched, encoding="utf-8")
    print(f"✅ 已为 {target_path} 应用 route-centered workflow-state 补丁")
    return True


def patch_js_hook(target_path: Path) -> bool:
    """Patch a JS inject-workflow-state.js to prefer workflow-state.py route."""
    if not target_path.is_file():
        print(f"⚠️ {target_path} 不存在，跳过")
        return False

    content = target_path.read_text(encoding="utf-8")
    if (
        JS_ROUTE_PATCH_MARKER in content
        and "workflow-state.route" in content
        and "task.extraLines" in content
        and 'import { execFileSync } from "child_process"' in content
        and 'const PYTHON_CMD = process.env.TRELLIS_PYTHON || "python3"' in content
        and "ACTION_BREADCRUMB_KEYS" in content
    ):
        print(f"✅ {target_path} 已包含 route-centered workflow-state 补丁，跳过")
        return True

    try:
        patched = _ensure_js_code_block_strip(content)
        patched = _ensure_js_route_runtime_deps(patched)
        if "function getActiveTask(ctx, platformInput = null) {" in patched and "function buildBreadcrumb(" in patched:
            patched = _replace_js_function(
                patched,
                "function getActiveTask(ctx, platformInput = null) {",
                JS_GET_ACTIVE_TASK_BLOCK,
            )
            patched = _replace_js_function(
                patched,
                "function buildBreadcrumb(",
                JS_BUILD_BREADCRUMB_BLOCK,
            )
        else:
            patched = _patch_js_baseline_fixture(patched)
            if "  return (\n    `Status: READY\\nTask: ${taskTitle}\\n` +\n" not in patched:
                raise ValueError("js baseline fixture missing READY return block")
            patched = patched.replace(
                "  const taskTitle = taskData.title || taskRef\n"
                "  const taskStatus = taskData.status || \"unknown\"\n\n",
                "  const taskTitle = taskData.title || taskRef\n"
                "  const taskStatus = taskData.status || \"unknown\"\n\n"
                + JS_BASELINE_ROUTE_SNIPPET + "\n",
                1,
            )
            patched = patched.replace("Source: ${active.source}", "Source: ${source}")
            patched = patched.replace(
                "  return (\n"
                "    `Status: READY\\nTask: ${taskTitle}\\n` +\n"
                "    `Source: ${source}\\n` +\n",
                "  const routeHeader = extraLines.length > 0 ? `${extraLines.join(\"\\n\")}\\n` : \"\"\n\n"
                "  return (\n"
                "    `Status: READY\\nTask: ${taskTitle}\\n` +\n"
                "    `Source: ${source}\\n` +\n"
                "    routeHeader +\n",
                1,
            )
    except ValueError as exc:
        print(f"⚠️ {target_path} 缺少预期结构，跳过补丁: {exc}")
        return False

    if "task.extraLines" not in patched:
        call_pattern = re.compile(
            r"(?P<indent>\s*)\?\s*buildBreadcrumb\(task\.id,\s*task\.status,\s*templates,\s*task\.source\)\n"
        )
        patched, replacements = call_pattern.subn(
            lambda match: (
                f"{match.group('indent')}? buildBreadcrumb(task.id, task.status, templates, task.source, task.extraLines)\n"
            ),
            patched,
            count=1,
        )
        if replacements == 0:
            print(f"⚠️ {target_path} 中未找到 buildBreadcrumb 调用，跳过补丁")
            return False

    if (
        'import { execFileSync } from "child_process"' not in patched
        or 'const PYTHON_CMD = process.env.TRELLIS_PYTHON || "python3"' not in patched
    ):
        print(f"⚠️ {target_path} route-centered JS 补丁缺少 execFileSync/PYTHON_CMD 依赖注入")
        return False

    target_path.write_text(patched, encoding="utf-8")
    print(f"✅ 已为 {target_path} 应用 route-centered workflow-state 补丁 (JS)")
    return True


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Apply the route-centered inject-workflow-state patch to Python or JS hook carriers."
    )
    parser.add_argument(
        "target_paths",
        nargs="+",
        help="One or more target inject-workflow-state hook files (.py or .js).",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    success = True
    for path_str in args.target_paths:
        target_path = Path(path_str).resolve()
        if target_path.suffix == ".py":
            if not patch_python_hook(target_path):
                success = False
        elif target_path.suffix == ".js":
            if not patch_js_hook(target_path):
                success = False
        else:
            print(f"⚠️ 不支持的文件类型: {target_path.suffix}")
            success = False

    return 0 if success else 1


if __name__ == "__main__":
    raise SystemExit(main())
