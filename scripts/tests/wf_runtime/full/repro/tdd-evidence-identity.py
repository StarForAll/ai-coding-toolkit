#!/usr/bin/env python3
"""六轮-5：TDD 红绿必须覆盖同一验证项；文档/调查对象按已批准适用性免红绿。

obligation（设计稿 §4.3、task-flow「task.tdd-verified」）：
① 只核"一次历史失败 + 一次本次通过"会被两条互不相关的命令拼凑（R22 正例曾以文件内容检查为红、
   `print(2)` 为绿），红绿必须同 `verification_id`；
② 文档/调查类对象以**已批准**的适用性 + 独立可观察验证代替红绿，不再逼 AI 造假。

红模：把"同一验证项"判定关掉 → 跨验证项的拼凑被放行，目标断言变红。
"""
import hashlib
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _harness as H
import _review_flow as F

SID = "sess-TDD"

FROM = '''    if not green_ids or not red_ids or not (green_ids & red_ids):
'''
TO = '''    if False:
'''


def _block(applicability=None):
    block = {
        "schema_version": 1,
        "touch_paths": ["area/x.txt"],
        "acceptance": [{"id": "a1", "statement": "v1 通过", "verification_ids": ["v1"]}],
        "verifications": [
            {"id": "v1", "invocation": {"kind": "argv", "argv": [
                "/usr/bin/python3", "-c",
                "import sys;sys.exit(0 if open('area/x.txt').read().strip()=='ok' else 1)"]},
             "cwd": ".", "input_refs": [], "required": True, "consume_at": "check"},
            {"id": "v2", "invocation": {"kind": "argv", "argv": ["/usr/bin/python3", "-c", "print(2)"]},
             "cwd": ".", "input_refs": [], "required": True, "consume_at": "check"},
        ],
    }
    if applicability:
        block["tdd_applicability"] = applicability
    return block


def _make_task(project, root, sid, block, title):
    rc, payload = H.cli(project, ["task-new", "--kind", "ordinary", "--title", title,
                                  "--template", os.path.join(project, ".wf/templates/task"), "--json"],
                        sid=sid)
    if rc != 0:
        raise H.Precondition(f"task-new 失败：{payload}")
    task_id = payload["facts"]["task_id"]
    task_dir = os.path.join(project, payload["facts"]["directory"])
    prd = ("# " + title + "\n\n<!-- wf-plan:v1 -->\n```json\n"
           + json.dumps(block, ensure_ascii=False, indent=2) + "\n```\n")
    open(os.path.join(task_dir, "prd.md"), "w", encoding="utf-8").write(prd)
    for name in ("design.md", "implement.md"):
        open(os.path.join(task_dir, name), "w", encoding="utf-8").write(f"# {name}\n")
    path = os.path.join(root, f"approve-{task_id}.json")
    json.dump([dict(F.decision(f"approve {task_id}", "approve",
                               "sha256:" + hashlib.sha256(prd.encode()).hexdigest()),
                    artifacts=H.plan_artifacts(project, f"approve {task_id}"),
                    plan={"tdd": True})],
              open(path, "w", encoding="utf-8"), ensure_ascii=False)
    rc, payload = H.cli(project, ["task-approve", "--task", task_id, "--decision", path, "--json"],
                        sid=sid, inputs={"generation": H.generation(project)})
    if rc != 0:
        raise H.Precondition(f"task-approve 失败：{(payload or {}).get('code')} {(payload or {}).get('facts')}")
    rc, payload = H.cli(project, ["task-start", "--task", task_id, "--json"], sid=sid,
                        inputs={"generation": H.generation(project)})
    if rc != 0:
        raise H.Precondition(f"task-start 失败：{(payload or {}).get('code')} {(payload or {}).get('facts')}")
    return task_id, task_dir


def _notes(root, name, evidence):
    notes = {"standard": {"conclusion": "pass", "basis": "仅新增文件"},
             "requirement": {"conclusion": "pass", "basis": "a1 由 v1 覆盖"}}
    if evidence is not None:
        notes["tdd_evidence"] = evidence
    path = os.path.join(root, name)
    json.dump(notes, open(path, "w"), ensure_ascii=False)
    return path


def check():
    root, _lib, _payload = H.stage()
    project = H.deploy(root)
    H.ensure_project_config(project)
    if os.environ.get("WF_REPRO_INJECT") == "1":
        H.patch(os.path.join(project, ".wf/lib/wflib/check.py"), FROM, TO)
    os.makedirs(os.path.join(project, "area"), exist_ok=True)

    problems = []
    # ---- 场景 A/B：同一任务先红后绿 ----
    task_id, _task_dir = _make_task(project, root, SID, _block(), "TDD 身份")
    open(os.path.join(project, "area/x.txt"), "w").write("bad\n")
    evidence = {"assertion": "x 的内容是 ok", "red_reason": "旧实现写坏内容",
                "red_command_ref": "v1", "green_command_ref": "v2",
                "properties": "可红、确定性、快速、可无人执行"}
    rc, payload = H.cli(project, ["task-check", "--task", task_id, "--review-notes",
                                  _notes(root, "n1.json", evidence), "--json"],
                        sid=SID, inputs={"generation": H.generation(project)})
    # 第一次：v1 失败（红运行入历史），整体 Check 失败
    if rc == 0:
        raise H.Precondition("第一次 Check 本应因 v1 失败而失败")

    open(os.path.join(project, "area/x.txt"), "w").write("ok\n")
    # 跨验证项拼凑：红=v1（历史失败），绿=v2（本次通过）→ 必须拒
    rc, payload = H.cli(project, ["task-check", "--task", task_id, "--review-notes",
                                  _notes(root, "n2.json", evidence), "--json"],
                        sid=SID, inputs={"generation": H.generation(project)})
    code = (payload or {}).get("code")
    facts = (payload or {}).get("facts") or {}
    tdd = facts.get("tdd") or {}
    if code == "WF_OK":
        problems.append("跨验证项的红绿被放行（未核同一验证项）")
    elif "same verification" not in str(tdd.get("reason") or ""):
        problems.append(f"拒绝原因未指向同一验证项：tdd={tdd}")

    # 同验证项：红=v1（历史失败），绿=v1（本次通过）→ 被接受
    same = dict(evidence, green_command_ref="v1")
    rc, payload = H.cli(project, ["task-check", "--task", task_id, "--review-notes",
                                  _notes(root, "n3.json", same), "--json"],
                        sid=SID, inputs={"generation": H.generation(project)})
    if (payload or {}).get("code") != "WF_OK":
        problems.append(f"同一验证项的红绿未被接受：{(payload or {}).get('code')} {(payload or {}).get('facts')}")

    # ---- 场景 C：文档类适用性（另一项目/会话，避免同会话多任务）----
    doc_root, _doc_lib, _doc_payload = H.stage()
    doc_project = H.deploy(doc_root)
    H.ensure_project_config(doc_project)
    if os.environ.get("WF_REPRO_INJECT") == "1":
        H.patch(os.path.join(doc_project, ".wf/lib/wflib/check.py"), FROM, TO)
    os.makedirs(os.path.join(doc_project, "area"), exist_ok=True)
    os.makedirs(os.path.join(doc_project, "docs"), exist_ok=True)
    block = {"schema_version": 1, "touch_paths": ["docs/guide.md"],
             "tdd_applicability": "docs",
             "acceptance": [{"id": "a1", "statement": "guide 含安装步骤", "verification_ids": ["v1"]}],
             "verifications": [{"id": "v1", "invocation": {"kind": "argv", "argv": [
                 "/usr/bin/python3", "-c",
                 "import sys;sys.exit(0 if 'install' in open('docs/guide.md').read() else 1)"]},
                 "cwd": ".", "input_refs": [], "required": True, "consume_at": "check"}]}
    doc_task, _dir = _make_task(doc_project, doc_root, "sess-TDD2", block, "文档类 TDD")
    open(os.path.join(doc_project, "docs/guide.md"), "w").write("# guide\n\ninstall: wf install\n")
    rc, payload = H.cli(doc_project, ["task-check", "--task", doc_task, "--review-notes",
                                      _notes(doc_root, "d1.json", None), "--json"],
                        sid="sess-TDD2", inputs={"generation": H.generation(doc_project)})
    code = (payload or {}).get("code")
    if code != "WF_OK":
        problems.append(f"已批准适用性=docs 仍被要求红绿：code={code} facts={(payload or {}).get('facts')}")

    if problems:
        raise H.TargetFailure("；".join(problems))
    return None


if __name__ == "__main__":
    sys.exit(H.main(check))