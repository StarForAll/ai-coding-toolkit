#!/usr/bin/env python3
"""666 审查报告写权：暂存目录必须在项目树之外，导入由持写权的主会话完成。

obligation（设计稿 §6.5「审查文件协议」）：
- reviewer 只写**项目树外**的暂存目录，报告不进项目树；
- 导入由持有写权的主会话做，写权在导入期间不转移、不释放；
- 锚点失配的报告不得导入为有效结论。

注入形态：把暂存根改到项目树内（`.wf/review`）。
"""
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _harness as H
import _review_launch as L

SID = "sess-666"
FROM = '    return os.path.join(tempfile.gettempdir(), "wf-review", str(project_id), task_id)\n'
TO = '    return os.path.join(ctx.root, ".wf", "review", str(project_id), task_id)  # 注入：暂存写进项目树\n'


def git(project, *args):
    return subprocess.run(["git", *args], cwd=project, capture_output=True, text=True,
                          check=False).stdout.strip()


def writer_state(project):
    record = json.load(open(os.path.join(project, ".wf/writer.json"), encoding="utf-8"))
    return record.get("state"), record.get("generation"), record.get("holder")


def check():
    root, _lib, _payload = H.stage()
    project = H.deploy(root)
    H.ensure_project_config(project)
    if os.environ.get("WF_REPRO_INJECT") == "1":
        H.patch(os.path.join(project, ".wf/lib/wflib/review.py"), FROM, TO)
    task_id, task_dir = L.prepare(project, root, SID)
    before = writer_state(project)
    rc, payload = L.launch(project, root, SID, task_id)
    if rc != 0:
        raise H.Precondition(f"review-launch 失败：{payload}")
    facts = (payload or {}).get("facts") or {}
    staging = [str(item) for item in (facts.get("temp_paths") or [])]
    problems = []
    project_real = os.path.realpath(project)
    if not staging:
        problems.append("launch 未给出暂存路径")
    for path in staging:
        real = os.path.realpath(path)
        if real == project_real or real.startswith(project_real + os.sep):
            problems.append(f"暂存目录落在项目树内：{path}")

    # 导入由持写权的主会话完成：写权不转移
    round_no = facts.get("round") or 1
    slot = (facts.get("slots") or [{}])[0]
    slot_id = slot.get("slot") or "s1"
    if not problems:
        report_dir = staging[0] if staging else os.path.join(root, "reports")
        os.makedirs(report_dir, exist_ok=True)
        report = os.path.join(report_dir, "s1.md")
        anchor = (facts.get("anchor") or {})
        axes = {name: {"conclusion": "pass", "basis": "夹具"}
                for name in ("range", "acceptance", "contract", "regression", "testability")}
        body = {"task-id": task_id, "round": round_no, "reviewer-id": slot_id,
                "source-cli": slot.get("reviewer_cli") or "pi",
                "review-time": "2026-11-06T00:00:00.000000Z",
                "review-focus": "range/acceptance", "protocol": "wf-review-v1",
                "check-anchor": anchor, "read-scope": ["pkg/**"], "excluded-scope": [".wf/**", ".env", "*.pem", ".codex/**", "../**"],
                "scope-exceptions": [], "axes": axes, "findings": [], "verdict": "pass"}
        open(report, "w", encoding="utf-8").write(
            "<!-- wf-review-agent:v1 status=done -->\n<!-- wf-review-report:v1 -->\n```json\n" + json.dumps(body, ensure_ascii=False, indent=2) + "\n```\n")
        rc, payload = H.cli(project, ["review-import", "--task", task_id, "--round", str(round_no),
                                      "--slot", slot_id, "--report", report, "--json"], sid=SID,
                            inputs={"generation": H.generation(project)})
        if rc != 0:
            problems.append(f"导入失败：{(payload or {}).get('code')}")
        after = writer_state(project)
        if after[0] != before[0] or after[2] != before[2]:
            problems.append(f"导入期间写权被转移：{before} → {after}")
    if problems:
        raise H.TargetFailure("；".join(problems))
    return None


if __name__ == "__main__":
    sys.exit(H.main(check))
