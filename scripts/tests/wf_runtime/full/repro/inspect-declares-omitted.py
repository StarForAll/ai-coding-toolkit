#!/usr/bin/env python3
"""A5：inspect 必须显式声明本轮**未输出**的两类治理输出。

缺陷形态：facts 只有已实现的四类治理输出，读者会把"四类"当成全量覆盖。
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _harness as H


class _Ctx:
    def __init__(self, root):
        self.root = root


def check():
    root, lib, _payload = H.stage()
    H.load(lib)
    if os.environ.get("WF_REPRO_INJECT") == "1":
        H.patch(os.path.join(lib, "wflib", "tasks.py"),
                '"governance_omitted": [',
                '"governance_omitted_disabled": [  # 注入：不再声明未输出类别')
    from wflib import tasks as wf_tasks

    project = H.git_repo(os.path.join(root, "proj"))
    for sub in (".wf/tasks", ".wf/spec", ".wf/session-bindings"):
        os.makedirs(os.path.join(project, sub), exist_ok=True)
    json.dump({"schema_version": 1, "state": "idle", "generation": 1,
               "created_at": "2026-11-05T00:00:00.000000Z",
               "updated_at": "2026-11-05T00:00:00.000000Z",
               "maintenance_results": []},
              open(os.path.join(project, ".wf/writer.json"), "w"), indent=2)
    H.commit_all(project)

    try:
        payload = wf_tasks.inspect(_Ctx(project))
    except Exception as exc:  # noqa: BLE001
        raise H.Precondition(f"inspect 抛异常：{exc!r}")
    H.require_success(payload, 0, "inspect")
    facts = (payload or {}).get("facts") or {}
    omitted = facts.get("governance_omitted")
    problems = []
    if not isinstance(omitted, list) or len(omitted) != 2:
        problems.append(f"未声明未输出类别：{omitted}")
    else:
        categories = {item.get("category") for item in omitted if isinstance(item, dict)}
        if categories != {"manual_compare", "author_order"}:
            problems.append(f"类别不符：{sorted(categories)}")
        if not all(item.get("note") for item in omitted if isinstance(item, dict)):
            problems.append("缺少说明 note")
    if problems:
        raise H.TargetFailure("；".join(problems))
    return None


if __name__ == "__main__":
    sys.exit(H.main(check))
