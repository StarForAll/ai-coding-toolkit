def get_step(step):
    """Return the legacy step body."""
    # strong-gate-phase-patch-applied

    # --- strong-gate phase patch ---
    # When a workflow-state.json with a valid strong-gate stage exists,
    # keep the step-level compatibility layer available for baseline
    # get_context.py --mode phase --step lookups.
    try:
        import json as _json
        import subprocess as _sp
        from pathlib import Path as _Path
        import sys as _sys
        _ws_path = None
        # Walk up to find trellis root
        for _p in _Path(__file__).resolve().parents:
            _trellis = _p / ".trellis"
            if _trellis.is_dir():
                _task_script = _trellis / "scripts" / "task.py"
                if _task_script.is_file():
                    _r = _sp.run(
                        [_sys.executable, str(_task_script), "current"],
                        capture_output=True, text=True, encoding="utf-8", errors="replace",
                        timeout=10,
                    )
                    if _r.returncode == 0 and _r.stdout.strip():
                        _active_task_dir = _Path(_r.stdout.strip())
                        if _active_task_dir.is_dir() and (_active_task_dir / "workflow-state.json").is_file():
                            _ws_path = _active_task_dir / "workflow-state.json"
                break
        if _ws_path is not None and _ws_path.is_file():
            _ws_data = _json.loads(_ws_path.read_text(encoding="utf-8"))
            _stage = _ws_data.get("stage", "")
            _STRONG_GATE_STAGES = {
                "feasibility", "brainstorm", "design", "plan",
                "implementation", "check", "review-gate",
                "project-audit", "delivery",
            }
            if _stage in _STRONG_GATE_STAGES:
                pass
    except Exception:
        pass
    # --- end strong-gate phase patch ---

    return f'legacy step {step}'
