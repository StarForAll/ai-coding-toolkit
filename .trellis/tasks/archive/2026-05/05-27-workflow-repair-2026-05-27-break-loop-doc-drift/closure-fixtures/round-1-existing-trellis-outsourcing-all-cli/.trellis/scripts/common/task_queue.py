from .tasks import iter_active_tasks

def list_tasks_by_status(filter_status=None, repo_root=None):
    return []

def list_pending_tasks(repo_root=None):
    # [workflow-embed-patch:strong-gate-task-status-view]
    # Under strong-gate installs, active task views are stage-based.
    # "Pending" therefore means every non-archived active task rather than
    # the legacy raw task.json status=planning subset.
    return list_tasks_by_status(None, repo_root)
