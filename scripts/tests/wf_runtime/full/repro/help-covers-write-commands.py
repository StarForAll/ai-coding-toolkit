#!/usr/bin/env python3
"""B4：`wf.py help <命令>` 必须自报输入结构与最小示例（消除"读源码猜字段"）。

obligation（dogfood 2026-11-07：33 次 `sed -n tasks.py/review.py` 才凑出字段）：
每条写命令的输入形态要能被入口自己说清，尤其是决定文件里的 `plan` 块这种"人不写就卡住"的字段。

注入形态：help 注册表为空。
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _harness as H

SID = "sess-help"
FROM = "COMMAND_HELP = {\n"
TO = "COMMAND_HELP = {}\n_UNUSED_HELP = {\n"
REQUIRED = ("task-new", "task-approve", "task-start", "task-check", "task-knowledge",
            "stop", "archive", "spec-update", "baseline-apply",
            "review-launch", "review-context", "review-import", "review-decide")


def check():
    root, _lib, _payload = H.stage()
    project = H.deploy(root)
    H.ensure_project_config(project)
    if os.environ.get("WF_REPRO_INJECT") == "1":
        H.patch(os.path.join(project, ".wf/lib/wflib/cli.py"), FROM, TO)
    problems = []

    rc, payload = H.cli(project, ["help", "--json"], sid=SID)
    if rc != 0 or (payload or {}).get("code") != "WF_OK":
        raise H.Precondition(f"help 列表失败：{payload}")
    listed = ((payload or {}).get("facts") or {}).get("commands") or []
    missing = [name for name in REQUIRED if name not in listed]
    if missing:
        problems.append(f"help 未覆盖写命令：{missing}")

    rc, payload = H.cli(project, ["help", "task-approve", "--json"], sid=SID)
    facts = (payload or {}).get("facts") or {}
    if not facts.get("args") or "--decision" not in (facts.get("args") or {}):
        problems.append("task-approve 未给参数表")
    if "plan" not in json.dumps(facts, ensure_ascii=False):
        problems.append("task-approve 未给出决定文件的 plan 块（人确认分级的关键字段）")
    if not facts.get("example"):
        problems.append("task-approve 未给最小示例")

    rc, payload = H.cli(project, ["help", "task-check", "--json"], sid=SID)
    notes = ((payload or {}).get("facts") or {}).get("inputs") or {}
    if "standard" not in json.dumps(notes, ensure_ascii=False):
        problems.append("task-check 未给 review-notes 的双轴结构")

    rc, payload = H.cli(project, ["help", "not-a-command", "--json"], sid=SID)
    if rc == 0:
        problems.append("未知命令的 help 未被拒")
    if problems:
        raise H.TargetFailure("；".join(problems))
    return None


if __name__ == "__main__":
    sys.exit(H.main(check))
