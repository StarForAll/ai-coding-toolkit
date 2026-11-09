#!/usr/bin/env python3
"""673 残余缺口：项目键的批准证据必须覆盖归档区。

obligation（§2.3.11 ③）：初始化任务归档后，其 PRD 仍是「键名+取值」的批准证据；
`project_key_approved` 只扫活动区会让执行器项目键的批准链在归档后断档。

夹具：造一个已归档任务（task.json 带批准 + prd.md 含键值），基线里**不**写该键，
确认动作必须仍能找到证据并通过；注入形态 = 只扫活动区。
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _harness as H
import _executor_set as E

VALUE = ".venv/bin/python"
FROM = '    archive = os.path.join(tasks_dir, "archive")\n'
TO = '    archive = os.path.join(tasks_dir, "__no_such__")  # 注入：只扫活动区\n'


def seed_archived_task(project, root):
    """造一条已归档、带批准、PRD 含键值的任务记录。"""
    task_id = "2026-" + "a" * 32
    directory = os.path.join(project, ".wf/tasks/archive/2026-11", f"{task_id}-初始化基线")
    os.makedirs(directory, exist_ok=True)
    prd = (f"# 初始化基线\n\n<!-- wf-plan:v1 -->\n```json\n"
           f"{json.dumps({'schema_version': 1, 'touch_paths': ['pkg/**']}, ensure_ascii=False)}\n```\n\n"
           f"python_executable = {VALUE}\n")
    open(os.path.join(directory, "prd.md"), "w", encoding="utf-8").write(prd)
    import hashlib

    prd_digest = "sha256:" + hashlib.sha256(open(os.path.join(directory, "prd.md"), "rb").read()).hexdigest()
    record = {
        "schema_version": 1, "id": task_id, "kind": "initialize", "status": "archived",
        "phase": "finish", "title": "初始化基线", "terminal": "normal",
        "plan": {"version": prd_digest,
                 "approval": {"choice": "approve", "source": "human",
                              "at": "2026-11-06T00:00:00.000000Z",
                              "subject": ["approve"], "object_digest": prd_digest},
                 "approved_version": prd_digest,
                 "touch_paths": ["pkg/**"]},
        "entry_snapshot": None, "archived_at": "2026-11-06T00:00:00.000000Z",
    }
    json.dump(record, open(os.path.join(directory, "task.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
    return directory


def check():
    root, _lib, _payload = H.stage()
    with E.isolated_home(root):
        project = H.deploy(root)
        H.ensure_project_config(project)
        E.make_venv_python(project)
        seed_archived_task(project, root)
        if os.environ.get("WF_REPRO_INJECT") == "1":
            H.patch(os.path.join(project, ".wf/bin/wf.py"), FROM, TO)
        module = E.launcher(project)
        config_path = os.path.join(project, ".wf/project-config.json")
        config = json.load(open(config_path, encoding="utf-8"))
        config["python_executable"] = VALUE
        json.dump(config, open(config_path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
        # 基线里没有该键：证据只在归档 PRD 中
        baseline = open(os.path.join(project, ".wf/baseline.md"), encoding="utf-8").read()
        if "python_executable" in baseline:
            raise H.Precondition("基线里已含该键，夹具不成立")
        import contextlib
        import io

        old_stdin = sys.stdin
        sys.stdin = E._Terminal("yes\n")
        buffer = io.StringIO()
        try:
            with contextlib.redirect_stdout(buffer):
                rc = module.cmd_confirm_executor(project, ["--scope", "project"])
        finally:
            sys.stdin = old_stdin
        if rc != 0:
            raise H.TargetFailure(f"归档 PRD 未被当作批准证据：{buffer.getvalue().strip()[-120:]}")
        if not E.ready(module, project):
            raise H.TargetFailure("确认后并不 ready")
        return None


if __name__ == "__main__":
    sys.exit(H.main(check))
