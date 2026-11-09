#!/usr/bin/env python3
"""F7-3：scope.classify_candidates 与写入口共用同一批准面判定。

缺陷形态：scope 自己写一套 `entry.get("touch_paths") or plan...` 回退口径，
于是"已开工但快照缺键"在分类器里被当成空面继续分类，而不是报记录非法。
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _harness as H


def check():
    root, lib, _payload = H.stage()
    H.load(lib)
    if os.environ.get("WF_REPRO_INJECT") == "1":
        H.patch(os.path.join(lib, "wflib", "scope.py"),
                "touch_paths = tasks_mod.approved_touch_paths(task)",
                'touch_paths = ((task.get("entry_snapshot") or {}).get("touch_paths")\n'
                '                   or (task.get("plan") or {}).get("touch_paths") or [])')
    from wflib import scope as wf_scope

    project = H.git_repo(os.path.join(root, "proj"))
    open(os.path.join(project, "a.txt"), "w").write("a\n")
    H.commit_all(project)
    open(os.path.join(project, "a.txt"), "w").write("b\n")

    task = {"id": "2026-" + "a" * 32, "phase": "execute", "baseline_head": "deadbeef",
            "entry_snapshot": {"baseline_head": "deadbeef"},  # 缺 touch_paths 键
            "plan": {"touch_paths": ["a.txt"]}}
    try:
        wf_scope.classify_candidates(project, task)
    except Exception as exc:  # noqa: BLE001
        code = getattr(exc, "code", None)
        H.only_two_outcomes(code, "WF_RECORD_INVALID", "classify_candidates")
        return None
    raise H.TargetFailure("已开工但快照缺键，分类器仍按 plan 继续分类（未报记录非法）")


if __name__ == "__main__":
    sys.exit(H.main(check))
