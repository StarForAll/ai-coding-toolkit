#!/usr/bin/env python3
"""六轮-B1：报告还没导入齐时，`review-decide` 必须先说"材料未到齐"，不能逼人签不可逆的单 reviewer 接受。

obligation（设计稿 §6.5、review-flow）：discovered 模式下人数取自已导入报告，第二份只是没写完时
会被误判成"单个 reviewer"，先要求人签残余风险接受；出口又写"重发一轮"——同轮仍开着，
第二份导入即可判。正确的先后是：**材料是否到齐 → 人数/异种 → 结论**。

红模：去掉"材料未到齐"的前置判定 → 一次只导入一份时直接进单 reviewer 分支（要求接受记录），
目标断言变红。
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _harness as H
import _review_flow as F

SID = "sess-MATPEND"

FROM = '''            if (declared_slots_count and len(imported) < declared_slots_count
                    and pending_acceptance is None):
'''
TO = '''            if False:  # 注入：不先判"材料未到齐"
'''


def _launch_and_import(project, root, task_id, task_dir, slot_clis, sid):
    """check → launch（两个槽位）→ 只导入**第一份**报告。返回 (anchors, temp_paths, check_id)。"""
    import subprocess

    subprocess.run(["git", "add", ".wf"], cwd=project, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-qm", "task state", "--allow-empty"],
                   cwd=project, check=True, capture_output=True)
    notes = os.path.join(root, "notes.json")
    json.dump(F.NOTE, open(notes, "w"), ensure_ascii=False)
    ack = os.path.join(root, "ack.json")
    json.dump([F.decision("external-checked", "external-checked")], open(ack, "w"), ensure_ascii=False)
    rc, payload = H.cli(project, ["task-check", "--task", task_id, "--review-notes", notes,
                                  "--decision", ack, "--json"],
                        sid=sid, inputs={"generation": H.generation(project)})
    if rc != 0:
        raise H.Precondition(f"task-check failed: {payload}")
    record = json.load(open(os.path.join(task_dir, "task.json"), encoding="utf-8"))
    check = record.get("check") or {}
    anchor = (check.get("anchor") or {}).get("check_anchor")
    request = {"implementation_clis": ["dsh"],
               "slots": [{"slot": f"slot-{i}", "reviewer_cli": cli} for i, cli in enumerate(slot_clis)],
               "export_decision": F.decision("export", "approve"),
               "submitted_scope": {"diff": "git diff", "requirement": ["prd"], "test_results": ["v1"]},
               "readable_scope": {"paths": ["pkg/**"]}, "exclusions": []}
    launch_path = os.path.join(root, "launch.json")
    json.dump(request, open(launch_path, "w"), ensure_ascii=False)
    auth = os.path.join(root, "export.json")
    json.dump([{"choice": "export", "task": task_id,
                "materials": ["diff", "requirement", "test_results"], "paths": ["pkg/**"],
                "quote": "人同意把材料外发给审查 CLI", "by": "human:test",
                "at": "2026-11-10T00:00:00.000000Z", "source": "user-declared"}],
              open(auth, "w"), ensure_ascii=False)
    rc, payload = H.cli(project, ["authorize", "record", "--task", task_id, "--file", auth, "--json"],
                        sid=sid, inputs={"generation": H.generation(project)})
    if rc != 0:
        raise H.Precondition(f"authorize record(export) failed: {payload}")
    rc, payload = H.cli(project, ["review-launch", "--task", task_id,
                                  "--launch-request", launch_path, "--json"],
                        sid=sid, inputs={"generation": H.generation(project)})
    if rc != 0:
        raise H.Precondition(f"review-launch failed: {payload}")
    facts = (payload or {}).get("facts") or {}
    temp_paths = facts.get("temp_paths") or []
    if len(temp_paths) != len(slot_clis):
        raise H.Precondition(f"review-launch 未给出逐槽位暂存目录：{list(facts)}")
    body = {"protocol": "wf-review-v1", "task-id": task_id, "round": 1,
            "reviewer-id": "slot-0", "source-cli": slot_clis[0], "review-time": F.AT,
            "review-focus": "x",
            "check-anchor": {"check_id": check.get("id"), "check_anchor": anchor},
            "read-scope": ["pkg/**"],
            "excluded-scope": ["node_modules/**", ".env", "*.pem", ".codex/**", "../**", ".wf/tasks/**"],
            "axes": {axis: {"conclusion": "pass", "basis": "b"} for axis in F.AXES},
            "findings": [], "verdict": "pass"}
    slot_dir = temp_paths[0]
    os.makedirs(slot_dir, exist_ok=True)
    report = os.path.join(slot_dir, "report.md")
    open(report, "w", encoding="utf-8").write(
        F.REPORT.format(slot="slot-0", body=json.dumps(body, ensure_ascii=False, indent=2)))
    rc, payload = H.cli(project, ["review-import", "--task", task_id, "--round", "1",
                                  "--slot", "slot-0", "--report", report, "--json"],
                        sid=sid, inputs={"generation": H.generation(project)})
    if rc != 0:
        raise H.Precondition(f"review-import failed: {payload}")
    return temp_paths, slot_clis, check


def _import_second(project, task_id, temp_paths, slot_clis, check_record):
    body = {"protocol": "wf-review-v1", "task-id": task_id, "round": 1,
            "reviewer-id": "slot-1", "source-cli": slot_clis[1], "review-time": F.AT,
            "review-focus": "x",
            "check-anchor": {"check_id": check_record.get("id"),
                             "check_anchor": (check_record.get("anchor") or {}).get("check_anchor")},
            "read-scope": ["pkg/**"],
            "excluded-scope": ["node_modules/**", ".env", "*.pem", ".codex/**", "../**", ".wf/tasks/**"],
            "axes": {axis: {"conclusion": "pass", "basis": "b"} for axis in F.AXES},
            "findings": [], "verdict": "pass"}
    slot_dir = temp_paths[1]
    os.makedirs(slot_dir, exist_ok=True)
    report = os.path.join(slot_dir, "report.md")
    open(report, "w", encoding="utf-8").write(
        F.REPORT.format(slot="slot-1", body=json.dumps(body, ensure_ascii=False, indent=2)))
    rc, payload = H.cli(project, ["review-import", "--task", task_id, "--round", "1",
                                  "--slot", "slot-1", "--report", report, "--json"],
                        sid=SID, inputs={"generation": H.generation(project)})
    if rc != 0:
        raise H.Precondition(f"第二份导入失败：{(payload or {}).get('code')} {(payload or {}).get('facts')}")


def _single_acceptance(root, task_id):
    path = os.path.join(root, "single-acceptance.json")
    json.dump({"by": "human:test", "at": "2026-11-10T00:00:00.000000Z",
               "quote": "只审一遍可接受", "source": "user-declared",
               "residual_risk": "漏检风险由我承担", "round": 1, "task": task_id},
              open(path, "w"), ensure_ascii=False)
    return path


def check():
    problems = []
    # ---- 项目 1：材料未到齐 → 拒绝；补齐第二份 → 同一轮可判 ----
    root, _lib, _payload = H.stage()
    project = H.deploy(root)
    H.ensure_project_config(project)
    if os.environ.get("WF_REPRO_INJECT") == "1":
        H.patch(os.path.join(project, ".wf/lib/wflib/review.py"), FROM, TO)
    task_id, task_dir = F.build_task(project, root, "材料未到齐", sid=SID, complexity="complex")
    temp_paths, slot_clis, check_record = _launch_and_import(
        project, root, task_id, task_dir, ["codex", "gemini"], SID)

    review_path = os.path.join(root, "main-review.json")
    json.dump(F.main_review(task_id, ["slot-0"]), open(review_path, "w"), ensure_ascii=False)
    rc, payload = H.cli(project, ["review-decide", "--task", task_id, "--round", "1",
                                  "--main-review", review_path, "--json"],
                        sid=SID, inputs={"generation": H.generation(project)})
    code = (payload or {}).get("code")
    facts = (payload or {}).get("facts") or {}
    if code != "WF_REVIEW_INVALID":
        problems.append(f"未按输入不成立拒绝：code={code}")
    if "还没导入齐" not in str(facts.get("reason") or ""):
        problems.append(f"拒绝原因不是「材料未到齐」：{facts.get('reason')}")
    if (facts.get("declared_slots"), facts.get("imported")) != (2, 1):
        problems.append(f"槽位事实不对：declared={facts.get('declared_slots')} imported={facts.get('imported')}")
    if "degraded" in facts:
        problems.append("仍走单 reviewer 降级分支（逼人签不可逆接受）")
    exits = " ".join(str(item) for item in facts.get("exits") or [])
    if "同一轮" not in exits:
        problems.append(f"出口没有指向同轮补导入：{facts.get('exits')}")

    if problems:
        raise H.TargetFailure("；".join(problems))

    _import_second(project, task_id, temp_paths, slot_clis, check_record)
    json.dump(F.main_review(task_id, ["slot-0", "slot-1"]), open(review_path, "w"), ensure_ascii=False)
    rc, payload = H.cli(project, ["review-decide", "--task", task_id, "--round", "1",
                                  "--main-review", review_path, "--json"],
                        sid=SID, inputs={"generation": H.generation(project)})
    if (payload or {}).get("code") != "WF_OK":
        raise H.TargetFailure(f"补齐第二份后同一轮仍判不了：code={(payload or {}).get('code')} "
                              f"facts={(payload or {}).get('facts')}")

    # ---- 项目 2：人已签单 reviewer 残余风险接受 → 缺的槽位按"确实不可用"处理 ----
    root2, _lib2, _payload2 = H.stage()
    project2 = H.deploy(root2)
    H.ensure_project_config(project2)
    if os.environ.get("WF_REPRO_INJECT") == "1":
        H.patch(os.path.join(project2, ".wf/lib/wflib/review.py"), FROM, TO)
    task2, task_dir2 = F.build_task(project2, root2, "槽位确实不可用", sid=SID, complexity="complex")
    _launch_and_import(project2, root2, task2, task_dir2, ["codex", "gemini"], SID)
    review2 = os.path.join(root2, "main-review.json")
    json.dump(F.main_review(task2, ["slot-0"]), open(review2, "w"), ensure_ascii=False)
    acceptance = _single_acceptance(root2, task2)
    rc, payload = H.cli(project2, ["review-decide", "--task", task2, "--round", "1",
                                   "--main-review", review2,
                                   "--single-reviewer-acceptance", acceptance, "--json"],
                        sid=SID, inputs={"generation": H.generation(project2)})
    code = (payload or {}).get("code")
    facts = (payload or {}).get("facts") or {}
    degraded = ((facts.get("result") or {}).get("degraded"))
    if code == "WF_REVIEW_INVALID" and "还没导入齐" in str(facts.get("reason") or ""):
        raise H.TargetFailure("人签残余风险接受后仍被'材料未到齐'挡住（该槽位确实不可用）")
    if degraded != "single-provider":
        raise H.TargetFailure(f"人签接受后未按单 reviewer 降级：code={code} degraded={degraded} "
                              f"facts={str(facts)[:300]}")
    return None

if __name__ == "__main__":
    sys.exit(H.main(check))