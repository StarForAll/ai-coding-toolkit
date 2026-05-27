import json
import re
from pathlib import Path
from typing import Optional

def load_breadcrumbs(workflow: Path):
    if workflow:
        content = workflow.read_text(encoding="utf-8")
        content = re.sub(r"```.*?```", "", content, flags=re.DOTALL)
        return _TAG_RE.finditer(content)
    return []

def get_active_task(root: Path, input_data: dict):
    task_id = input_data['active'].task_path
    task_dir = root / task_id
    data = {"status": "planning"}
    status = data.get("status", "")
    active = input_data['active']
# [workflow-embed-patch:prefer-workflow-state-json]
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
                route_stage_status = route_data.get("status", "")
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
