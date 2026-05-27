from pathlib import Path
import json

def _resolve_active_task(trellis_dir: Path, hook_input: dict):
    return hook_input['active']

def _resolve_task_dir(trellis_dir: Path, task_ref: str) -> Path:
    return trellis_dir / 'tasks' / task_ref

def _get_task_status(trellis_dir: Path, hook_input: dict) -> str:
    active = _resolve_active_task(trellis_dir, hook_input)
    if not active.task_path:
        # [workflow-embed-patch:session-start-nl-routing]
        return 'Status: NO ACTIVE TASK\nSource: none\nNext-Action: Consult the AGENTS.md NL routing table for profile-specific entry routing. For outsourcing profile: run `python3 ./.trellis/scripts/workflow/workflow-state.py route` to detect whether this is a read-only analysis turn or a real first-entry task turn; only load `/trellis:feasibility` when the route result and the current intent both indicate task creation. For personal profile: also run `python3 ./.trellis/scripts/workflow/workflow-state.py route` first; new implementation work still enters `/trellis:feasibility` first unless route explicitly reuses an existing valid assessment and keeps `target=brainstorm`.\n\n'
    task_ref = active.task_path
    task_dir = _resolve_task_dir(trellis_dir, task_ref)
    if active.stale or not task_dir.is_dir():
        return 'Status: STALE POINTER'
    task_json_path = task_dir / 'task.json'
    task_data = {}
    if task_json_path.is_file():
        task_data = json.loads(task_json_path.read_text(encoding='utf-8'))
    task_title = task_data.get('title', task_ref)
    task_status = task_data.get('status', 'unknown')
    # strong-gate-session-start-patch-applied
    # [workflow-embed-patch:session-start-route-first]

    # --- strong-gate session-start patch ---
    # Route through workflow-state.py even when workflow-state.json is missing;
    # the router itself decides repair_needed vs reenter vs blocked.
    try:
        _ws_script = trellis_dir / "scripts" / "workflow" / "workflow-state.py"
        if not _ws_script.is_file():
            _ws_script = trellis_dir / "scripts" / "workflow-state.py"
        if _ws_script.is_file():
            import subprocess as _sp
            import json as _json
            _route_result = _sp.run(
                [
                    sys.executable,
                    str(_ws_script),
                    "route",
                    str(task_dir),
                    "--project-root",
                    str(trellis_dir.parent),
                ],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=10,
            )
            if _route_result.returncode == 0 and _route_result.stdout.strip():
                _route_data = _json.loads(_route_result.stdout.strip())
                _action = _route_data.get("action", "")
                _r_stage = _route_data.get("stage", "")
                _r_stage_status = _route_data.get("status", "")
                _r_blockers = _route_data.get("blockers", [])
                _r_reason = _route_data.get("reason", "")
                _r_target = _route_data.get("target", "")
                _r_warnings = _route_data.get("warnings", [])
                _status_label = _r_stage or _action or "active"
                _lines = [
                    f"Status: STRONG-GATE ({_status_label})",
                    f"Task: {task_title}",
                    "Source: workflow-state.route",
                ]
                if _r_stage_status:
                    _lines.append(f"Stage-Status: {_r_stage_status}")
                if _action:
                    _lines.append(f"Action: {_action}")
                if _r_target:
                    _lines.append(f"Target-Stage: {_r_target}")
                if _r_reason:
                    _lines.append(f"Reason: {_r_reason}")
                if isinstance(_r_blockers, list) and _r_blockers:
                    _lines.append(f"Blockers: {'; '.join(str(item) for item in _r_blockers)}")
                if isinstance(_r_warnings, list) and _r_warnings:
                    _lines.append(f"Warnings: {'; '.join(str(item) for item in _r_warnings)}")
                _lines.append(
                    "Next-Action: Follow the action above. Use `workflow-state.py route` "
                    "to re-check routing at any time. Use `workflow-state.py set --stage <stage>` "
                    "to transition stages when gate conditions are met."
                )
                return "\n".join(_lines)
        return (
            f"Status: ACTIVE (route unavailable)\nTask: {task_title}\nSource: {active.source}"
            "\nNext-Action: Re-run `workflow-state.py route` after restoring the helper or its runtime dependency."
        )
    except Exception:
        return (
            f"Status: ACTIVE (route failed)\nTask: {task_title}\nSource: {active.source}"
            "\nNext-Action: Inspect workflow-state.py route failure and retry before continuing stage work."
        )
    # --- end strong-gate session-start patch ---

