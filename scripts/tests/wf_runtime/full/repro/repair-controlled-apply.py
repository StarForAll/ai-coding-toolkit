#!/usr/bin/env python3
"""654 受控修复：预览 → 短指纹 → 重核 → 应用 → 回执，指纹错则零写入。

obligation（设计稿 §5.5 / 机制稿 §10.3）：repair 的每一次应用都必须由**本次预览**签发的
短指纹许可；指纹不符时不得改动任何记录（尤其不得把 writer 置 idle）。
成功路径必须留下可核事实：代次递增 + 维护回执。
"""
import json
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _harness as H
import _snapshot as S

PY = H.WF_PYTHON
FROM = '            if live and live.get("alive"):\n'
TO = '            if False and live and live.get("alive"):  # 注入：人工确认可以替代存活事实\n'


def writer(project):
    return json.load(open(os.path.join(project, ".wf/writer.json"), encoding="utf-8"))


def repair(project, *args, feed=""):
    return subprocess.run([PY, os.path.join(project, ".wf/bin/repair.py"), "--project", project, *args],
                          capture_output=True, text=True, input=feed)


def stale(project, task_id):
    path = os.path.join(project, ".wf/writer.json")
    record = json.load(open(path, encoding="utf-8"))
    record["state"] = "held"
    record["holder"] = {"kind": "session", "id": "sess-dead", "generation": record["generation"],
                        "scope": {"object": {"kind": "task", "id": task_id}}}
    json.dump(record, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    with open(os.path.join(project, ".wf-lock"), "w", encoding="utf-8") as handle:
        handle.write("wf-lock-v1\nholder pid=999999 start=0\n")


def check():
    root, _lib, _payload = H.stage()
    project = H.deploy(root)
    H.ensure_project_config(project)
    os.makedirs(os.path.join(project, "pkg"), exist_ok=True)
    open(os.path.join(project, "pkg/b.py"), "w").write("b\n")
    if os.environ.get("WF_REPRO_INJECT") == "1":
        H.patch(os.path.join(project, ".wf/bin/repair.py"), FROM, TO)
    task_id, _task_dir = S.started_task(project, root, sid="sess-R654")
    stale(project, task_id)
    before = writer(project)
    problems = []

    import re as _re

    live_pid = os.getpid()
    live_start = open(f"/proc/{live_pid}/stat", encoding="utf-8").read().split()[21]
    with open(os.path.join(project, ".wf-lock"), "w", encoding="utf-8") as handle:
        handle.write(f"wf-lock-v1\nholder pid={live_pid} start={live_start}\n")   # 旧写者「仍存活」
    await_token = repair(project)
    token = _re.search(r"预览指纹：([0-9a-f]{8})", await_token.stdout or "")
    if not token:
        raise H.Precondition(f"预览未给出指纹：{(await_token.stdout or '')[-200:]}")
    bad = repair(project, "--apply", "--nonce", token.group(1), feed=token.group(1) + "\n")
    if bad.returncode == 0:
        problems.append("旧写者仍存活时仍应用成功（人工确认替代了存活事实）")
    if writer(project) != before:
        problems.append("存活阻断路径改动了写权记录（应零写入）")

    # 旧写者已死 → 受控应用成立：代次递增 + 维护回执
    with open(os.path.join(project, ".wf-lock"), "w", encoding="utf-8") as handle:
        handle.write("wf-lock-v1\nholder pid=999999 start=0\n")
    ready = repair(project)
    token2 = _re.search(r"预览指纹：([0-9a-f]{8})", ready.stdout or "")
    if not token2:
        raise H.Precondition("第二次预览未给出指纹")
    good = repair(project, "--apply", "--nonce", token2.group(1), feed=token2.group(1) + "\n")
    after_good = writer(project)
    if good.returncode != 0:
        problems.append(f"旧写者停止后应用失败：{(good.stdout or good.stderr)[-160:]}")
    else:
        if after_good.get("state") != "idle":
            problems.append(f"应用后写权不是 idle：{after_good.get('state')}")
        if after_good.get("generation") != (before.get("generation") or 0) + 1:
            problems.append(f"代次未递增：{before.get('generation')} → {after_good.get('generation')}")
        if not after_good.get("maintenance_results"):
            problems.append("应用后没有维护回执")
    if problems:
        raise H.TargetFailure("；".join(problems))
    return None


if __name__ == "__main__":
    sys.exit(H.main(check))
