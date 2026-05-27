import sys
import subprocess
from common.log import Colors, colored
from common.io import read_json, write_json

def cmd_create(args):
    repo_root = get_repo_root()
    task_dir = repo_root / '.trellis' / 'tasks' / 'sample'
    dir_name = task_dir.name
    # Auto-activate the new task so the per-turn breadcrumb fires planning
    try:
        from .active_task import resolve_context_key, set_active_task
        # [workflow-embed-patch:preserve-parent-active-task]
        _preserve_active = bool(getattr(args, "parent", None)) and __import__("os").environ.get(
            "TRELLIS_PRESERVE_ACTIVE_TASK"
        ) == "1"
        if _preserve_active:
            print(
                colored(
                    "⏭ Preserving current active task while creating child task "
                    "(TRELLIS_PRESERVE_ACTIVE_TASK=1)",
                    Colors.YELLOW,
                ),
                file=sys.stderr,
            )
        elif resolve_context_key():
            try:
                rel_dir = task_dir.relative_to(repo_root).as_posix()
            except ValueError:
                rel_dir = str(task_dir)
            set_active_task(rel_dir, repo_root)
    except Exception:
        pass
    print(colored(f'Created task: {dir_name}', Colors.GREEN))
    return 0

def cmd_archive(args):
    repo_root = get_repo_root()
    task_dir = repo_root / '.trellis' / 'tasks' / 'sample'
    dir_name = task_dir.name
    task_json_path = task_dir / FILE_TASK_JSON

    # [workflow-embed-patch:archive-closeout-gate]
    workflow_state_path = task_dir / "workflow-state.json"
    finish_work_checklist = task_dir / "finish-work-checklist.md"
    if workflow_state_path.is_file():
        workflow_state = read_json(workflow_state_path)
        if isinstance(workflow_state, dict):
            stage = workflow_state.get("stage")
            if stage not in {None, "", "delivery"}:
                print(
                    colored(
                        f"Error: archive only after workflow close-out gate validation "
                        f"(current workflow-state stage={stage!r})",
                        Colors.RED,
                    ),
                    file=sys.stderr,
                )
                return 1
    if not finish_work_checklist.is_file():
        print(
            colored(
                "Error: archive only after workflow close-out gate validation "
                "(missing finish-work-checklist.md)",
                Colors.RED,
            ),
            file=sys.stderr,
        )
        return 1
    workflow_validate_path = repo_root / ".trellis" / "scripts" / "workflow" / "workflow-state.py"
    if workflow_validate_path.is_file():
        validate_result = subprocess.run(
            [
                sys.executable,
                str(workflow_validate_path),
                "validate",
                str(task_dir),
                "--project-root",
                str(repo_root),
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        if validate_result.returncode != 0:
            validate_output = (validate_result.stdout + validate_result.stderr).strip()
            print(
                colored(
                    "Error: archive only after workflow close-out gate validation "
                    + (f"({validate_output})" if validate_output else "(workflow-state.py validate failed)"),
                    Colors.RED,
                ),
                file=sys.stderr,
            )
            return 1
    if task_json_path.is_file():
        data = read_json(task_json_path)
        if data:
            data['status'] = 'completed'
            write_json(task_json_path, data)
    return 0
