#!/usr/bin/env python3
"""审查身份由文件名承载：reviewer 只给 task id + 轮次；同一 agent 同一轮不得二次审查。

obligation（2026-11-07 人裁）：
- reviewer 侧只调 `review-context --task <id> [--round n]`，其余信息（锚点/材料/报告路径）由它提供；
- 报告文件名 `review-<agent>.md` 就是身份，正文不必声明；
- 同一 agent 同一轮的 in-progress 草稿可续写；status=done 后不能再起一份，只能导入；
- 判定按文件名 token 判人数与异种，实施 CLI 取 action 会话身份。

注入形态：不拦"同一 agent 二次审查"（占位检查失效）。
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _harness as H
import _review_flow as F
import _review_launch as L

SID = "sess-main"
FROM = '    if status == "done":\n'
TO = '    if False:  # 注入：不拦已完成报告的二次审查\n'
COVERED = ["node_modules/**", ".env", "*.pem", ".codex/**", "../**", ".wf/tasks/**"]


def report_body(task_id, round_no, anchor, agent, materials_identity=None):
    axes = {name: {"conclusion": "pass", "basis": "夹具"}
            for name in ("range", "acceptance", "contract", "regression", "testability")}
    body = {"protocol": "wf-review-v1", "task-id": task_id, "round": round_no,
            "review-time": "2026-11-07T00:00:00.000000Z", "review-focus": "范围/验收",
            "check-anchor": anchor, "read-scope": ["pkg/**"], "excluded-scope": COVERED,
            "scope-exceptions": [], "axes": axes, "findings": [], "verdict": "pass"}
    if materials_identity:
        body["materials"] = {"identity": materials_identity}
    return ("<!-- wf-review-agent:v1 status=done -->\n<!-- wf-review-report:v1 -->\n```json\n"
            + json.dumps(body, ensure_ascii=False, indent=2) + "\n```\n")


def context(project, task_id, round_no, agent):
    return H.cli(project, ["review-context", "--task", task_id, "--round", str(round_no), "--json"],
                 sid=f"sess-{agent}", host_id=agent)


def check():
    root, _lib, _payload = H.stage()
    project = H.deploy(root)
    H.ensure_project_config(project)
    if os.environ.get("WF_REPRO_INJECT") == "1":
        H.patch(os.path.join(project, ".wf/lib/wflib/review.py"), FROM, TO)
    task_id, _dir = L.prepare(project, root, SID)
    # launch 要求声明**实施 CLI**（C6：异种审查的判定输入）；审查 CLI 仍由报告文件名承载
    request = os.path.join(root, "launch.json")
    json.dump({"export_decision": {"source": "human", "at": "2026-11-07T00:00:00.000000Z",
                                   "subject": ["授权外发"], "choice": "export"},
               "submitted_scope": {"diff": True, "requirement": True, "test_results": True}},
              open(request, "w", encoding="utf-8"), ensure_ascii=False)
    _auth = os.path.join(root, "export.json")
    json.dump([{"choice": "export", "task": task_id, "materials": ["diff", "requirement", "test_results"], "paths": ["pkg/**"], "quote": "人同意外发审查材料",
                "by": "human:test", "at": "2026-11-10T00:00:00.000000Z",
                "source": "user-declared"}],
              open(_auth, "w"), ensure_ascii=False)
    _rc_auth, _payload_auth = H.cli(project, ["authorize", "record", "--task", task_id,
                                               "--file", _auth, "--json"],
                                     sid=SID, inputs={"generation": H.generation(project)})
    if _rc_auth != 0:
        raise H.Precondition(f"authorize record(export) 失败：{_payload_auth}")
    rc, payload = H.cli(project, ["review-launch", "--task", task_id, "--launch-request", request,
                                  "--implementation-cli", "dsh", "--json"],
                        sid=SID, inputs={"generation": H.generation(project)})
    if rc != 0:
        raise H.Precondition(f"review-launch 失败：{payload}")
    facts = (payload or {}).get("facts") or {}
    round_no = facts.get("round") or 1
    anchor = facts.get("anchor") or {}
    problems = []

    # ① reviewer 只给 task id + 轮次：路径/材料/锚点都由 context 给
    rc, payload = context(project, task_id, round_no, "pi")
    if rc != 0:
        raise H.Precondition(f"review-context(pi) 失败：{payload}")
    pi_facts = (payload or {}).get("facts") or {}
    report = pi_facts.get("report_path") or ""
    if os.path.basename(report) != "review-pi.md":
        problems.append(f"报告路径不是按 agent 命名：{report}")
    for key in ("diff", "prd", "check", "tests"):
        if not os.path.isfile((pi_facts.get("materials") or {}).get(key) or ""):
            problems.append(f"材料未物化：{key}")

    # ② 同一 agent 的 in-progress 草稿可续写：返回同一材料/路径，不另起一份
    rc2, payload2 = context(project, task_id, round_no, "pi")
    if rc2 != 0:
        problems.append("同一 agent 的 in-progress 草稿无法续写")
    else:
        facts2 = (payload2 or {}).get("facts") or {}
        if not facts2.get("resumed") or facts2.get("report_path") != report:
            problems.append("续写没有返回同一 report_path/resumed")

    # ③ 写完 status=done 后同一 agent 不能再起一份，只能导入
    open(report, "w", encoding="utf-8").write(report_body(task_id, round_no, anchor, "pi",
                                                     (pi_facts.get("materials_check") or {}).get("identity")))
    rc_done, _payload_done = context(project, task_id, round_no, "pi")
    if rc_done == 0:
        problems.append("同一 agent 的已完成报告未被阻止")

    # ④ 第二个 agent → 导入 → 判定
    rc, payload = context(project, task_id, round_no, "zcode")
    if rc != 0:
        raise H.Precondition(f"review-context(zcode) 失败：{payload}")
    open((payload or {})["facts"]["report_path"], "w", encoding="utf-8").write(
        report_body(task_id, round_no, anchor, "zcode",
                    ((payload or {}).get("facts") or {}).get("materials_check", {}).get("identity")))
    rc, payload = H.cli(project, ["review-import", "--task", task_id, "--json"], sid=SID,
                        inputs={"generation": H.generation(project)})
    if rc != 0:
        raise H.Precondition(f"review-import 失败：{payload}")
    main_path = os.path.join(root, "main-review.json")
    json.dump(F.main_review(task_id, ["s1", "s2"]), open(main_path, "w"), ensure_ascii=False)
    rc, payload = H.cli(project, ["review-decide", "--task", task_id,
                                  "--main-review", main_path, "--json"], sid=SID,
                        inputs={"generation": H.generation(project)})
    if rc != 0 or (payload or {}).get("code") != "WF_OK":
        problems.append(f"判定失败：{(payload or {}).get('code')}")
    else:
        clis = ((payload or {}).get("facts") or {}).get("reviewer_clis")
        if sorted(clis or []) != ["pi", "zcode"]:
            problems.append(f"身份不是取文件名：{clis}")
    if problems:
        raise H.TargetFailure("；".join(problems))
    return None


if __name__ == "__main__":
    sys.exit(H.main(check))
