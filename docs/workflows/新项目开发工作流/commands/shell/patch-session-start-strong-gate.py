#!/usr/bin/env python3
"""Patch session-start.py to use strong-gate workflow-state routing.

When installed into a target project, this patch replaces the legacy
task-status tail logic after `task_status = task_data.get(...)` with a
route-first strong-gate branch, so old PLANNING/READY/COMPLETED status routing
does not remain as unreachable dead code.

The patched session-start carrier delegates to `workflow-state.py route`
whenever the helper script exists, even if `workflow-state.json` is missing or
invalid. That lets the authoritative router surface `repair_needed`,
`context_needed`, `awaiting_confirmation_with_blockers`, or other formal strong-
gate actions instead of collapsing them into a misleading `ACTIVE` fallback.

It also removes the legacy startup instruction that told the AI to auto-continue
whenever a task looked `READY`; under the strong-gate workflow, startup carriers
must follow `workflow-state.py route` and stop at blockers or confirmation gates.
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

PATCH_MARKER = "# strong-gate-session-start-patch-applied"
ROUTE_FIRST_MARKER = "# [workflow-embed-patch:session-start-route-first]"
LEGACY_READY_AUTOCONTINUE_LINE = "If a task is READY, execute its Next required action without asking whether to continue."
STRONG_GATE_READY_GUIDANCE_LINES = (
    "Treat `workflow-state.py route` / <task-status> as the only authority for the next action.\n"
    "Do NOT auto-continue across blockers or confirmation gates; when routing asks for confirmation, repair, or task selection, surface that requirement first."
)
TAIL_START_RE = re.compile(
    r'task_status\s*=\s*task_data\.get\(\s*["\']status["\']\s*,\s*["\']unknown["\']\s*\)\s*\n'
)
LEGACY_TAIL_END_PATTERNS = (
    re.compile(r"\n\s*def _extract_range\("),
    re.compile(r"\n\s*def _load_trellis_config\("),
    re.compile(r"\n\s*def main\("),
)

PATCH_BLOCK = '''
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
                _r_stage_status = _route_data.get("stage_status", "")
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
                return "\\n".join(_lines)
        return f"Status: ACTIVE\\nTask: {task_title}\\nSource: {active.source}"
    except Exception:
        return f"Status: ACTIVE\\nTask: {task_title}\\nSource: {active.source}"
    # --- end strong-gate session-start patch ---
'''


def _build_replacement(status_assignment_line: str) -> str:
    return (
        status_assignment_line
        + f"    {PATCH_MARKER}\n"
        + f"    {ROUTE_FIRST_MARKER}\n"
        + PATCH_BLOCK
        + "\n"
    )


def _replace_legacy_tail(content: str) -> str | None:
    match = TAIL_START_RE.search(content)
    if not match:
        return None
    tail_end = None
    for pattern in LEGACY_TAIL_END_PATTERNS:
        candidate = pattern.search(content, match.end())
        if candidate and (tail_end is None or candidate.start() < tail_end.start()):
            tail_end = candidate
    replacement = _build_replacement(match.group(0))
    if tail_end is None:
        return content[:match.start()] + replacement
    return content[:match.start()] + replacement + content[tail_end.start():]


def _replace_legacy_ready_autocontinue(content: str) -> tuple[str, bool]:
    if LEGACY_READY_AUTOCONTINUE_LINE not in content:
        return content, False
    return content.replace(LEGACY_READY_AUTOCONTINUE_LINE, STRONG_GATE_READY_GUIDANCE_LINES), True


def patch_session_start(target_path: Path) -> bool:
    """Apply the strong-gate patch to session-start.py's _get_task_status().

    Returns True if the patch was applied or was already present.
    """
    if not target_path.is_file():
        print(f"Warning: {target_path} does not exist, skipping patch")
        return False

    content = target_path.read_text(encoding="utf-8")
    patched = content
    route_patch_present = PATCH_MARKER in content and ROUTE_FIRST_MARKER in content
    route_applied = False
    ready_guidance_applied = False

    if not route_patch_present:
        replaced = _replace_legacy_tail(patched)
        if replaced is None:
            print(f"Warning: {target_path} does not contain expected _get_task_status structure, skipping patch")
            return False
        patched = replaced
        route_applied = True

    patched, ready_guidance_applied = _replace_legacy_ready_autocontinue(patched)
    if not route_applied and not ready_guidance_applied:
        print(f"OK: {target_path} already contains full strong-gate patch, skipping")
        return True

    target_path.write_text(patched, encoding="utf-8")
    if route_applied and ready_guidance_applied:
        print(f"OK: Upgraded strong-gate session-start patch in {target_path} (route + startup guidance)")
    elif route_applied:
        print(f"OK: Applied strong-gate session-start patch to {target_path}")
    else:
        print(f"OK: Upgraded strong-gate startup guidance in {target_path}")
    return True


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Apply the strong-gate session-start patch to a target session-start.py file."
    )
    parser.add_argument("target_path", help="Path to the target session-start.py file")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    target_path = Path(args.target_path).resolve()
    if patch_session_start(target_path):
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
