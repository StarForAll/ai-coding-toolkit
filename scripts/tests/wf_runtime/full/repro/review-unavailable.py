#!/usr/bin/env python3
"""692 审查不可用：留痕成立，且复杂任务不得因此正常归档。

obligation（设计稿 §6.5「不可用处置」）：`review-decide --unavailable` 只能记录
「本轮未审查」，必须留下声明来源与证据；它不是审查 pass，复杂任务仍不得正常归档。

注入形态：把「不可用」当作 pass（`verdict = "pass"`）。
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _harness as H
import _review_flow as F
import _review_launch as L

SID = "sess-692"
FROM = '            verdict = "unavailable"\n'
TO = '            verdict = "pass"  # 注入：不可用当通过\n'


def check():
    root, _lib, _payload = H.stage()
    project = H.deploy(root)
    H.ensure_project_config(project)
    if os.environ.get("WF_REPRO_INJECT") == "1":
        H.patch(os.path.join(project, ".wf/lib/wflib/review.py"), FROM, TO)
    task_id, task_dir = L.prepare(project, root, SID)
    rc, payload = L.launch(project, root, SID, task_id)
    if rc != 0:
        raise H.Precondition(f"review-launch 失败：{payload}")
    round_no = (payload or {}).get("facts", {}).get("round") or 1

    problems = []
    # ① 无证据的不可用声明必须拒绝
    empty = os.path.join(root, "unavailable-empty.json")
    json.dump({"reason": "没有可用的 reviewer CLI"}, open(empty, "w", encoding="utf-8"), ensure_ascii=False)
    rc, payload = H.cli(project, ["review-decide", "--task", task_id, "--round", str(round_no),
                                  "--unavailable", empty, "--json"], sid=SID,
                        inputs={"generation": H.generation(project)})
    H.require_business_code(payload, rc)
    H.only_two_outcomes((payload or {}).get("code") if rc != 0 else "WF_OK",
                        "WF_SEMANTIC_DECISION", "692 无证据声明")
    if rc == 0:
        problems.append("无证据的不可用声明被接受")

    # ② 带证据的不可用声明：留痕为 unavailable，不是 pass
    decl = os.path.join(root, "unavailable.json")
    json.dump({"reason": "两个 reviewer CLI 均无法启动",
               "evidence": {"attempts": [{"cli": "pi", "result": "start failed"},
                                         {"cli": "claude", "result": "missing credentials"}]}},
              open(decl, "w", encoding="utf-8"), ensure_ascii=False)
    rc, payload = H.cli(project, ["review-decide", "--task", task_id, "--round", str(round_no),
                                  "--unavailable", decl, "--json"], sid=SID,
                        inputs={"generation": H.generation(project)})
    if not problems:
        if (payload or {}).get("code") != "WF_REVIEW_UNAVAILABLE":
            problems.append(f"不可用未按 WF_REVIEW_UNAVAILABLE 留痕：{(payload or {}).get('code')}")
        record = json.load(open(os.path.join(task_dir, "task.json"), encoding="utf-8"))
        outcome = ((record.get("reviews") or {}).get("result") or {}).get("verdict")
        attempts = [item.get("outcome") for item in (record.get("reviews") or {}).get("attempts") or []]
        if outcome != "unavailable":
            problems.append(f"reviews.result.verdict 不是 unavailable：{outcome}")
        if "unavailable" not in attempts:
            problems.append(f"尝试级 outcome 未记录 unavailable：{attempts}")

    # ③ 复杂任务不得因此归档
    if not problems:
        finish = os.path.join(root, "archive-692.json")
        json.dump([F.decision(["pkg/a.py"], "finish")], open(finish, "w", encoding="utf-8"), ensure_ascii=False)
        rc, payload = H.cli(project, ["archive", "--task", task_id, "--decision", finish, "--json"], sid=SID,
                            inputs={"generation": H.generation(project)})
        if rc == 0:
            problems.append("复杂任务在「审查不可用」后仍被正常归档")
        record = json.load(open(os.path.join(task_dir, "task.json"), encoding="utf-8"))
        if record.get("status") == "archived":
            problems.append("任务记录已变为 archived")
    if problems:
        raise H.TargetFailure("；".join(problems))
    return None


if __name__ == "__main__":
    sys.exit(H.main(check))
