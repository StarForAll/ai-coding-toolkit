from common.log import Colors, colored
from common.io import read_json, write_json

def cmd_start(args):
    repo_root = get_repo_root()
    full_path = repo_root / '.trellis' / 'tasks' / 'sample'
    task_dir = full_path.relative_to(repo_root).as_posix()
    task_json_path = full_path / FILE_TASK_JSON
    if not resolve_context_key():
        # Strong-gate mode keeps workflow-state.py route as the only stage authority.
        if task_json_path.is_file():
            data = read_json(task_json_path)
            # [workflow-embed-patch:strong-gate-no-status-flip]
            if data and data.get("status") == "planning":
                print(colored("⏭ Strong-gate mode: skipping legacy task.json status flip (workflow-state.py route is authoritative)", Colors.YELLOW))
        return 0
    active = set_active_task(task_dir, repo_root)
    if active:
        if task_json_path.is_file():
            data = read_json(task_json_path)
            # [workflow-embed-patch:strong-gate-no-status-flip]
            if data and data.get("status") == "planning":
                print(colored("⏭ Strong-gate mode: skipping legacy task.json status flip (workflow-state.py route is authoritative)", Colors.YELLOW))
        return 0
    return 0

def cmd_finish(args):
    repo_root = get_repo_root()
    current = active.task_path
    task_json_path = repo_root / current / FILE_TASK_JSON
    if task_json_path.is_file():
        run_task_hooks("after_finish", task_json_path, repo_root)
    return 0

def cmd_current(args):
    repo_root = get_repo_root()
    active = resolve_active_task(repo_root)
    if args.source:
        print(f"Current task: {active.task_path or '(none)'}")
        print(f"Source: {active.source}")
        if active.stale:
            print("State: stale")
        return 0 if active.task_path else 1

    if active.task_path:
        print(active.task_path)
        return 0

    return 1

def show_usage():
    print("  python3 task.py start <dir>                        Set active task (strong-gate: pointer only; stage changes still go through workflow-state.py)\n")

def build_parser():
    p_start = subparsers.add_parser("start", help="Set active task (strong-gate: refresh pointer only; does not flip task.json status or advance workflow stage)")
