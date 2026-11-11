#!/usr/bin/env python3
"""665 审查读取范围：`excluded-scope` 必须覆盖敏感面，不能只「非空」。

obligation（设计稿 §8.2「审查读取范围」）：提交材料与允许自主读取分列并留痕；
凭据、私密配置、项目外路径、其他任务目录排除；越界回报而非自行扩大。

2026-11-07 审计发现：机制只核 `excluded-scope` **非空**，写 `["node_modules/**"]` 也能过——
这条承诺此前没有任何机制兜底。本用例把它钉住。

注入形态：不核覆盖（只核非空）。
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _harness as H
import _review_launch as L

SID = "sess-665"
FROM = '        gaps = exclusion_gaps(payload)\n'
TO = '        gaps = []  # 注入：不核覆盖\n'
COVERED = ["node_modules/**", ".env", "*.pem", ".codex/**", "../**", ".wf/tasks/**"]
NARROW = ["node_modules/**"]


def import_report(project, root, task_id, round_no, slot, staging, excluded, tag):
    report = os.path.join(staging, f"{slot}-{tag}.md")
    body = {"protocol": "wf-review-v1", "task-id": task_id, "round": round_no,
            "reviewer-id": slot, "source-cli": dict((item["slot"], item["reviewer_cli"]) for item in L.SLOTS)[slot], "review-time": "2026-11-07T00:00:00.000000Z",
            "review-focus": "范围/验收", "check-anchor": None,
            "read-scope": ["pkg/**"], "excluded-scope": list(excluded), "scope-exceptions": [],
            "axes": {name: {"conclusion": "pass", "basis": "夹具"}
                     for name in ("range", "acceptance", "contract", "regression", "testability")},
            "findings": [], "verdict": "pass"}
    open(report, "w", encoding="utf-8").write(
        "<!-- wf-review-report:v1 -->\n```json\n" + json.dumps(body, ensure_ascii=False, indent=2) + "\n```\n")
    return report


def check():
    root, _lib, _payload = H.stage()
    project = H.deploy(root)
    H.ensure_project_config(project)
    if os.environ.get("WF_REPRO_INJECT") == "1":
        H.patch(os.path.join(project, ".wf/lib/wflib/review.py"), FROM, TO)
    task_id, _dir = L.prepare(project, root, SID)
    rc, payload = L.launch(project, root, SID, task_id)
    if rc != 0:
        raise H.Precondition(f"review-launch 失败：{payload}")
    facts = (payload or {}).get("facts") or {}
    round_no = facts.get("round") or 1
    staging = facts.get("temp_paths") or []
    anchor = facts.get("anchor") or {}
    problems = []

    # ① 窄排除（只写 node_modules）→ 缺覆盖，必须拒绝
    for slot, path in zip(("s1", "s2"), staging):
        os.makedirs(path, exist_ok=True)
        report = import_report(project, root, task_id, round_no, slot, path, NARROW, "narrow")
        body = json.loads(open(report, encoding="utf-8").read().split("```json")[1].split("```")[0])
        body["check-anchor"] = anchor
        open(report, "w", encoding="utf-8").write(
            "<!-- wf-review-report:v1 -->\n```json\n" + json.dumps(body, ensure_ascii=False, indent=2) + "\n```\n")
        rc, payload = H.cli(project, ["review-import", "--task", task_id, "--round", str(round_no),
                                      "--slot", slot, "--report", report, "--json"], sid=SID,
                            inputs={"generation": H.generation(project)})
        if rc != 0:
            raise H.Precondition(f"导入失败：{(payload or {}).get('code')}")
    rc, payload = H.cli(project, ["review-decide", "--task", task_id, "--round", str(round_no), "--json"],
                        sid=SID, inputs={"generation": H.generation(project)})
    if rc == 0:
        problems.append("窄排除范围仍被判通过（excluded-scope 只核了非空）")
    facts_out = json.dumps((payload or {}).get("facts") or {}, ensure_ascii=False)
    if "credentials" not in facts_out and (payload or {}).get("code") != "WF_OK":
        problems.append(f"拒绝但未点名缺哪类敏感面：{facts_out[:160]}")
    if problems:
        raise H.TargetFailure("；".join(problems))
    return None


if __name__ == "__main__":
    sys.exit(H.main(check))
