import sys
from unittest import mock
sys.path.insert(0,"/home/xzc/projects/personal/ai-coding-toolkit/docs/workflows/wf/payload/lib")
from wflib import cli, runs
ctx = mock.Mock(root="/tmp/x")
run = {"paused": True, "terminal": None, "cursor": {"task_id": "T1"}}
task = {"id":"T1","status":"in_progress","phase":"execute","handoff":{},"plan":{"touch_paths":["src/**"]},"execution":{}}
with mock.patch.object(runs,"load_run",return_value=run), \
     mock.patch.object(runs,"_run_persist_pending",return_value=False), \
     mock.patch("wflib.tasks.load_task",return_value=task), \
     mock.patch("wflib.scope.uncommitted_paths",return_value=["src/a.py"]), \
     mock.patch("wflib.tasks.wip_paths",return_value=[]):
    try:
        cli._ensure_run_releasable(ctx,"r1")
        print("release allowed with unregistered src/a.py WIP")
    except Exception as exc:
        print("rejected:", getattr(exc,"code",type(exc).__name__), getattr(exc,"facts",None))
