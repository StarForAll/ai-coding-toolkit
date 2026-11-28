import contextlib, sys, tempfile
from pathlib import Path
from unittest import mock
REPO = Path("/home/xzc/projects/personal/ai-coding-toolkit")
sys.path.insert(0, str(REPO / "docs/workflows/wf/payload/lib"))
from wflib import tasks
TASK = "2026-" + "a"*32
root = tempfile.mkdtemp(); (Path(root)/".wf").mkdir(exist_ok=True)
ctx = mock.Mock(root=root); ctx.key = lambda required=True: "s-k"
def go(paths_in_subject, uncommitted, a_paths=None, e_paths=None):
    decision = {"source":"human:x","at":"t","subject":",".join(paths_in_subject),
                "object_digest":"","choice":"keep","reason":"r"}
    classified = {"buckets":{"a":a_paths or [],"b":[],"c":[],"d":[],"e":e_paths or [],"f":[]},
                  "candidates":[],"touch_paths":["pkg/**"]}
    task = {"id":TASK,"status":"in_progress","phase":"execute","handoff":{},
            "execution":{"actions":[]},"plan":{}}
    with mock.patch.object(tasks.session_mod,"load_binding",return_value={"object":{"kind":"task","id":TASK}}), \
         mock.patch("wflib.lock.acquire",return_value=contextlib.nullcontext()), \
         mock.patch.object(tasks,"require_held_for",return_value=({"holder":{}},{"holder":{}})), \
         mock.patch.object(tasks,"task_dir",return_value=root), \
         mock.patch.object(tasks.records,"load_json",return_value=task), \
         mock.patch.object(tasks,"approved_touch_paths",return_value=["pkg/**"]), \
         mock.patch.object(tasks.scope,"classify_candidates",return_value=classified), \
         mock.patch.object(tasks.scope,"uncommitted_paths",return_value=list(uncommitted)), \
         mock.patch.object(tasks.scope,"git",return_value=(0,"","")), \
         mock.patch.object(tasks.fingerprint,"item",side_effect=lambda root,path:{"path":path,"digest":"sha256:x","exists":True,"kind":"file"}):
        try:
            tasks.stop_work(ctx,[decision],"keep")
        except tasks.TaskError as exc:
            return exc.code, exc.facts
    return None,None
print("empty-subject, only own control records dirty:", go([], [".wf/tasks/%s/task.json"%TASK]))
print("baseline a-bucket listed, e empty:", go([".wf/baseline.md"], [".wf/baseline.md"], a_paths=[".wf/baseline.md"], e_paths=[]))

def go2(paths_in_subject, a_paths, touch):
    decision = {"source":"human:x","at":"t","subject":",".join(paths_in_subject),
                "object_digest":"","choice":"keep","reason":"r"}
    classified = {"buckets":{"a":a_paths,"b":[],"c":[],"d":[],"e":[],"f":[]},"candidates":[],"touch_paths":touch}
    task = {"id":TASK,"status":"in_progress","phase":"execute","handoff":{},"execution":{"actions":[]},"plan":{}}
    with mock.patch.object(tasks.session_mod,"load_binding",return_value={"object":{"kind":"task","id":TASK}}), \
         mock.patch("wflib.lock.acquire",return_value=contextlib.nullcontext()), \
         mock.patch.object(tasks,"require_held_for",return_value=({"holder":{}},{"holder":{}})), \
         mock.patch.object(tasks,"task_dir",return_value=root), \
         mock.patch.object(tasks.records,"load_json",return_value=task), \
         mock.patch.object(tasks,"approved_touch_paths",return_value=touch), \
         mock.patch.object(tasks.scope,"classify_candidates",return_value=classified), \
         mock.patch.object(tasks.scope,"uncommitted_paths",return_value=list(a_paths)), \
         mock.patch.object(tasks.scope,"git",return_value=(0,"","")), \
         mock.patch.object(tasks.fingerprint,"item",side_effect=lambda root,path:{"path":path,"digest":"sha256:x","exists":True,"kind":"file"}):
        try:
            tasks.stop_work(ctx,[decision],"keep")
        except tasks.TaskError as exc:
            return exc.code, exc.facts
    return None,None
print("baseline a-bucket in approved touch:", go2([".wf/baseline.md"],[".wf/baseline.md"],["pkg/**",".wf/baseline.md"]))
