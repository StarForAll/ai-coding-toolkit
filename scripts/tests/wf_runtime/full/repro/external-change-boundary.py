#!/usr/bin/env python3
"""632 紧急变更边界：外部提交「是否触及批准面」决定它要不要人判。

obligation（设计稿 §8.2「紧急变更边界」、实现稿 §2.3.11 P1-1）：
- 与批准面**不相交**的外部提交：只记事实，不阻断；
- 与批准面**相交**的外部提交：必须人判「已核对无影响」，否则 `WF_SEMANTIC_DECISION`；
- 有了人判（choice 属「已核对无影响」且 subject 含该提交 OID）才放行。

注入形态：把「是否触及」判成恒假——相交的提交被当成无关，静默放行。
"""
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _harness as H
import _snapshot as S

SID = "sess-C632"
FROM = '    touch = tasks_module.approved_touch_paths(task)\n'
TO = ('    return False  # 注入：一律当作未触及\n'
      '    touch = tasks_module.approved_touch_paths(task)\n')


def git(project, *args):
    return subprocess.run(["git", *args], cwd=project, capture_output=True, text=True,
                          check=False).stdout.strip()


def check():
    root, _lib, _payload = H.stage()
    project = H.deploy(root)
    H.ensure_project_config(project)
    os.makedirs(os.path.join(project, "pkg"), exist_ok=True)
    open(os.path.join(project, "pkg/a.py"), "w").write("a\n")
    git(project, "add", "-A")
    git(project, "commit", "-qm", "基线")
    if os.environ.get("WF_REPRO_INJECT") == "1":
        H.patch(os.path.join(project, ".wf/lib/wflib/check.py"), FROM, TO)
    task_id, _task_dir = S.started_task(project, root, sid=SID)
    notes = os.path.join(root, "notes-632.json")
    json.dump({"standard": {"conclusion": "pass", "basis": "单函数"},
               "requirement": {"conclusion": "pass", "basis": "a1 覆盖"}},
              open(notes, "w", encoding="utf-8"), ensure_ascii=False)
    decision = os.path.join(root, "ext-632.json")
    problems = []

    def run_check(extra=()):
        return H.cli(project, ["task-check", "--task", task_id, "--review-notes", notes,
                               "--json", *extra], sid=SID,
                     inputs={"generation": H.generation(project)})

    # ① 面外外部提交：不阻断
    os.makedirs(os.path.join(project, "docs"), exist_ok=True)
    open(os.path.join(project, "docs/x.md"), "w").write("x\n")
    git(project, "add", "docs/x.md")
    git(project, "commit", "-qm", "外部：文档更新")
    rc, payload = run_check()
    if rc != 0 or (payload or {}).get("code") != "WF_OK":
        problems.append(f"面外外部提交被阻断：{(payload or {}).get('code')}")

    # ② 面内外部提交：必须人判
    open(os.path.join(project, "pkg/a.py"), "w").write("a-changed\n")
    git(project, "add", "pkg/a.py")
    git(project, "commit", "-qm", "外部：紧急改了任务文件")
    touched = git(project, "rev-parse", "HEAD")
    rc, payload = run_check()
    H.require_business_code(payload, rc)
    H.only_two_outcomes((payload or {}).get("code") if rc != 0 else "WF_OK",
                        "WF_SEMANTIC_DECISION", "632 面内外部提交")
    if rc == 0:
        problems.append("面内外部提交被静默放行")

    # ③ 补人判后放行
    if not problems:
        json.dump([{"source": "human (test)", "at": "2026-11-06T00:00:00.000000Z",
                    "subject": [f"已核对无影响 {touched}"], "object_digest": "sha256:" + "0" * 64,
                    "choice": "checked", "reason": "632"}],
                  open(decision, "w", encoding="utf-8"), ensure_ascii=False)
        rc, payload = run_check(("--decision", decision))
        if rc != 0 or (payload or {}).get("code") != "WF_OK":
            problems.append(f"补人判后仍未放行：{(payload or {}).get('code')}")
    if problems:
        raise H.TargetFailure("；".join(problems))
    return None


if __name__ == "__main__":
    sys.exit(H.main(check))
