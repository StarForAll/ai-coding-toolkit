#!/usr/bin/env python3
"""六轮-2：实例建出的任务必须能走完四阶段，且归档不夺走实例的写权。

obligation（设计稿 §5.8、§6.1、§7.3）：`run advance` 首达任务步骤时建出的任务属于该实例，
会话绑定的是实例。日常写入口必须按「实例归属 + 游标指向」核验，而不是只认 `binding.object.id == 任务 id`；
任务正常归档后实例仍持写权，`run advance` 才能记 satisfied 并推进。

红模：把锁内写权的实例分支关掉（退回修复前：只认任务作用域）→ `task-approve` 直接报
`WF_BINDING_MISMATCH`，目标断言变红。
"""
import hashlib
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _harness as H
import _review_flow as F

SID = "sess-INS"
MARKER = "<!-- wf-definition:v1 -->"

FROM = '''    if kind == "run":
        from . import runs as runs_mod

        run_id = scope.get("id")
'''
TO = '''    if kind == "run" and False:
        from . import runs as runs_mod

        run_id = scope.get("id")
'''


def _definition():
    doc = {
        "format_version": 1, "workflow_id": "one-task", "content_version": 1,
        "purpose": "单任务流程", "applicability": "已有基线",
        "inputs": {},
        "steps": [{
            "id": "build", "type": "task", "title": "实现功能", "task_kind": "ordinary",
            "inputs": [], "outputs": [], "required": True, "skip": None,
            "human_points": [], "goal": "实现功能", "acceptance": ["验收通过"],
            "actions": [{"id": "work", "text": "实现", "inputs": [], "outputs": [],
                         "required": True, "skip": None, "human_points": []}],
            "verifications": [{"id": "v1", "source": "current_plan",
                               "established_by": {"kind": "current_task"},
                               "stored_in": {"kind": "task_plan", "verification_id": "v1"},
                               "consume_at": "check"}]}],
        "completion": ["任务正常归档"],
    }
    body = json.dumps(doc, ensure_ascii=False, indent=2)
    return f"{MARKER}\n```json\n{body}\n```\n\n# 说明\n"


def _plan_block():
    return {
        "schema_version": 1,
        "touch_paths": ["area/a.txt"],
        "acceptance": [{"id": "a1", "statement": "文件内容为 ok", "verification_ids": ["v1"]}],
        "verifications": [{
            "id": "v1",
            "invocation": {"kind": "argv", "argv": [
                "/usr/bin/python3", "-c",
                "import sys;sys.exit(0 if open('area/a.txt').read().strip()=='ok' else 1)"]},
            "cwd": ".", "input_refs": [], "required": True, "consume_at": "check"}],
    }


def check():
    root, _lib, _payload = H.stage()
    project = H.deploy(root)
    H.ensure_project_config(project)
    if os.environ.get("WF_REPRO_INJECT") == "1":
        H.patch(os.path.join(project, ".wf/lib/wflib/tasks.py"), FROM, TO)

    text = _definition()
    os.makedirs(os.path.join(project, ".wf/user-workflows"), exist_ok=True)
    path = os.path.join(project, ".wf/user-workflows/one-task.md")
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(text)
    digest = "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()

    prepare_auth = H.prepare_authorization(project, root, "one-task", sid=SID)
    rc, payload = H.cli(project, ["definition", "prepare", "--id", "one-task",
                                  "--authorization", prepare_auth, "--json"],
                        sid=SID, inputs={"generation": H.generation(project)})
    if rc != 0:
        raise H.Precondition(f"prepare 失败：{(payload or {}).get('code')}")

    creation = {"definition_id": "one-task", "definition_digest": digest,
                "inputs": {}, "steps": {"build": "applicable"}}
    creation_path = os.path.join(root, "creation.json")
    json.dump(creation, open(creation_path, "w"), ensure_ascii=False)
    create_auth = H.creation_authorization(project, root, creation_path, sid=SID)
    rc, payload = H.cli(project, ["run", "create", "--creation", creation_path,
                                  "--authorization", create_auth, "--json"],
                        sid=SID, inputs={"generation": H.generation(project)})
    if rc != 0:
        raise H.Precondition(f"run create 失败：{(payload or {}).get('code')} {(payload or {}).get('facts')}")
    run_id = (payload.get("facts") or {})["run"]["id"]

    # 创建授权是人的输入：没有它、或它绑的不是这份创建输入，都必须停在需人决策（不自报 source=human）
    rc, payload = H.cli(project, ["run", "create", "--creation", creation_path, "--json"],
                        sid=SID, inputs={"generation": H.generation(project)})
    if (payload or {}).get("code") != "WF_SEMANTIC_DECISION":
        raise H.TargetFailure(f"无创建授权仍建实例：code={(payload or {}).get('code')}")
    wrong_auth = os.path.join(root, "wrong-creation-auth.json")
    json.dump([{"source": "human terminal (repro)", "at": "2026-11-26T08:00:00Z",
                "subject": "创建实例 one-task", "object_digest": "sha256:" + "0" * 64,
                "choice": "创建实例", "reason": "摘要不对"}],
              open(wrong_auth, "w"), ensure_ascii=False)
    rc, payload = H.cli(project, ["run", "create", "--creation", creation_path,
                                  "--authorization", wrong_auth, "--json"],
                        sid=SID, inputs={"generation": H.generation(project)})
    if (payload or {}).get("code") != "WF_SEMANTIC_DECISION":
        raise H.TargetFailure(f"创建授权摘要不符仍建实例：code={(payload or {}).get('code')}")

    # 定义是项目数据：按 §5.7 处置后再推进实例（未提交的项目数据会挡住 task-start 的外来改动核验）
    subprocess.run(["git", "add", "-A"], cwd=project, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-qm", "definition one-task"], cwd=project,
                   check=True, capture_output=True)

    rc, payload = H.cli(project, ["definition", "prepare", "--id", "one-task", "--json"],
                        sid=SID, inputs={"generation": H.generation(project)})
    if (payload or {}).get("code") != "WF_BINDING_MISMATCH":
        raise H.TargetFailure(f"已绑定实例的会话仍可用准备通道：code={(payload or {}).get('code')}")

    rc, payload = H.cli(project, ["run", "advance", "--run", run_id, "--json"],
                        sid=SID, inputs={"generation": H.generation(project)})
    facts = (payload or {}).get("facts") or {}
    task_id = facts.get("task")
    directory = facts.get("directory")
    if rc != 0 or not task_id:
        raise H.Precondition(f"advance 未建任务：{(payload or {}).get('code')} {facts}")

    # 写 PRD 机读块并请人批准（轻量：必须覆盖模板里已有的全部规划产物）
    block = _plan_block()
    prd = ("# 实现功能\n\n## 目标\n\n在 area/a.txt 写入 ok。\n\n<!-- wf-plan:v1 -->\n```json\n"
           + json.dumps(block, ensure_ascii=False, indent=2) + "\n```\n")
    with open(os.path.join(project, directory, "prd.md"), "w", encoding="utf-8") as handle:
        handle.write(prd)
    prd_digest = "sha256:" + hashlib.sha256(prd.encode("utf-8")).hexdigest()
    artifacts = {}
    for name in ("prd.md", "design.md", "implement.md"):
        candidate = os.path.join(project, directory, name)
        if os.path.isfile(candidate):
            artifacts[f"{directory}/{name}"] = "sha256:" + hashlib.sha256(
                open(candidate, "rb").read()).hexdigest()
    decision = os.path.join(root, "approve.json")
    json.dump([{"source": "human terminal (repro)", "at": "2026-11-26T02:00:00.000000Z",
                "subject": f"approve {task_id}", "object_digest": prd_digest,
                "artifacts": artifacts, "choice": "approve", "reason": "单文件"}],
              open(decision, "w"), ensure_ascii=False)

    rc, payload = H.cli(project, ["task-approve", "--task", task_id, "--decision", decision, "--json"],
                        sid=SID, inputs={"generation": H.generation(project)})
    code = (payload or {}).get("code")
    if rc != 0 or code != "WF_OK":
        raise H.TargetFailure(f"实例内任务无法批准：code={code} facts={(payload or {}).get('facts')}")

    problems = []
    # 实例绑定的状态页必须给出当前任务的事实与交付摘要（人工验收要 `content_digest`）
    rc, payload = H.cli(project, ["status", "--json"], sid=SID,
                        inputs={"generation": H.generation(project)})
    facts = (payload or {}).get("facts") or {}
    task_facts = facts.get("task") or {}
    if (payload or {}).get("code") != "WF_OK":
        problems.append(f"实例内 status 失败：{(payload or {}).get('code')}")
    elif not task_facts.get("plan_version"):
        problems.append(f"实例内 status 缺任务事实（plan_version）：{task_facts}")
    elif not (facts.get("delivery") or {}).get("content_digest"):
        problems.append(f"实例内 status 缺 delivery.content_digest：{facts.get('delivery')}")
    if not (facts.get("repair_scope") or {}).get("conclusion"):
        problems.append("实例内 status 缺 repair_scope")

    for label, args in (("task-start", ["task-start", "--task", task_id, "--json"]),):
        rc, payload = H.cli(project, args, sid=SID, inputs={"generation": H.generation(project)})
        if rc != 0 or (payload or {}).get("code") != "WF_OK":
            problems.append(f"{label} 失败：{(payload or {}).get('code')} {(payload or {}).get('facts')}")

    os.makedirs(os.path.join(project, "area"), exist_ok=True)
    with open(os.path.join(project, "area/a.txt"), "w", encoding="utf-8") as handle:
        handle.write("ok\n")
    notes = os.path.join(root, "notes.json")
    json.dump({"standard": {"conclusion": "pass", "basis": "新文件，风格一致"},
               "requirement": {"conclusion": "pass", "basis": "a1 由 v1 覆盖"}},
              open(notes, "w"), ensure_ascii=False)
    rc, payload = H.cli(project, ["task-check", "--task", task_id, "--review-notes", notes, "--json"],
                        sid=SID, inputs={"generation": H.generation(project)})
    if rc != 0 or (payload or {}).get("code") != "WF_OK":
        problems.append(f"task-check 失败：{(payload or {}).get('code')} {(payload or {}).get('facts')}")

    rc, payload = H.cli(project, ["task-knowledge", "--task", task_id, "--decision", "no-update", "--json"],
                        sid=SID, inputs={"generation": H.generation(project)})
    if rc != 0:
        problems.append(f"task-knowledge 失败：{(payload or {}).get('code')}")

    archive_decision = os.path.join(root, "archive.json")
    json.dump([
        {"source": "human terminal (repro)", "at": "2026-11-26T02:10:00.000000Z",
         "subject": f"finish {task_id}: 人已了解检查结果与未核实项", "object_digest": prd_digest,
         "choice": "finish", "reason": "验收 a1 通过"},
        {"source": "human terminal (repro)", "at": "2026-11-26T02:10:00.000000Z",
         "subject": "area/a.txt", "object_digest": prd_digest,
         "choice": "commit", "reason": "授权提交交付路径"}],
        open(archive_decision, "w"), ensure_ascii=False)
    rc, payload = H.cli(project, ["archive", "--task", task_id, "--decision", archive_decision, "--json"],
                        sid=SID, inputs={"generation": H.generation(project)})
    facts = (payload or {}).get("facts") or {}
    if rc != 0 or (payload or {}).get("code") != "WF_OK":
        problems.append(f"archive 失败：{(payload or {}).get('code')} {facts}")
    else:
        release = facts.get("write_release") or {}
        if release.get("kept") != "run":
            problems.append(f"归档把实例的写权一起释放了：write_release={release}")

    rc, payload = H.cli(project, ["run", "advance", "--run", run_id, "--json"],
                        sid=SID, inputs={"generation": H.generation(project)})
    code = (payload or {}).get("code")
    facts = (payload or {}).get("facts") or {}
    if code != "WF_OK" or facts.get("settled") != "build":
        problems.append(f"归档后实例未记 satisfied：code={code} facts={facts}")
    if (facts.get("step_results") or {}).get("build", {}).get("kind") != "satisfied":
        problems.append(f"step_results 未记 satisfied：{facts.get('step_results')}")

    # 落盘核对：末步结案必须写进实例记录——只回显 facts 会让 `run finish` 重读后仍判未完
    # （六轮审查 b-1：末步 advance 返回 WF_OK、写盘 0 次）
    run_path = os.path.join(project, ".wf/workflow-runs", f"{run_id}.json")
    on_disk = (json.load(open(run_path, encoding="utf-8")).get("step_results") or {}).get("build") or {}
    if on_disk.get("kind") != "satisfied":
        problems.append(f"末步结果没落盘：{on_disk}")

    # 单步实例：结案后直接正常结束；无提交授权 → 停 persist_pending 并给出口
    rc, payload = H.cli(project, ["run", "finish", "--run", run_id, "--json"],
                        sid=SID, inputs={"generation": H.generation(project)})
    facts = (payload or {}).get("facts") or {}
    if (payload or {}).get("code") != "WF_OK":
        problems.append(f"末步结案后 run finish 失败：{(payload or {}).get('code')} {facts}")
    elif facts.get("persisted") is not False:
        problems.append(f"无授权却报已持久化：{facts}")
    record = json.load(open(run_path, encoding="utf-8"))
    if (record.get("action") or {}).get("state") != "persist_pending":
        problems.append(f"待提交状态不对：{(record.get('action') or {}).get('state')}")

    # 补交授权后**重入必须能续做**（此前一律报 run already ended，出口是死的）
    record_rel = f".wf/workflow-runs/{run_id}.json"
    grant = os.path.join(root, "finish-grant.json")
    json.dump([{"source": "human terminal (repro)", "at": "2026-11-26T03:00:00.000000Z",
                "subject": [record_rel], "object_digest": prd_digest,
                "choice": "commit", "reason": "提交实例结束记录"}],
              open(grant, "w"), ensure_ascii=False)
    rc, payload = H.cli(project, ["run", "finish", "--run", run_id, "--decision", grant, "--json"],
                        sid=SID, inputs={"generation": H.generation(project)})
    facts = (payload or {}).get("facts") or {}
    if (payload or {}).get("code") != "WF_OK":
        problems.append(f"补授权后重入失败：{(payload or {}).get('code')} {facts}")
    elif facts.get("persisted") is not True or facts.get("resumed") is not True:
        problems.append(f"补授权后未续做提交：{facts}")
    record = json.load(open(run_path, encoding="utf-8"))
    if (record.get("action") or {}).get("state") != "done":
        problems.append(f"提交完成后动作应 done：{(record.get('action') or {}).get('state')}")
    # 已真正结束（不再 persist_pending）时重入仍被拒
    rc, payload = H.cli(project, ["run", "finish", "--run", run_id, "--json"],
                        sid=SID, inputs={"generation": H.generation(project)})
    if (payload or {}).get("code") != "WF_BINDING_MISMATCH":
        problems.append(f"已结束实例再次 finish 未被拒：{(payload or {}).get('code')}")

    if problems:
        raise H.TargetFailure("；".join(problems))
    return None


if __name__ == "__main__":
    sys.exit(H.main(check))