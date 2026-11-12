#!/usr/bin/env python3
"""A5 + P1-7：`inspect` 的治理面既不得隐瞒未输出的类别，也不得把已交付的类别继续声明为缺失。

缺陷形态（两条都要挡）：
① facts 只有已实现的治理输出、没有 `governance_omitted` → 读者把子集当全量覆盖；
② 交付了 `manual_compare`/`author_order` 却仍把它们写在 `governance_omitted` 里（或反过来：
   把声明删了但输出没有）→ 声明与事实脱节。

2026-11-12 口径：两类已交付，声明里只允许留尚未交付的类别（当前是 `out_of_scope_duplicates`）。
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
        # 注入：把已交付的类别继续声明成「未输出」（声明与事实脱节），
        # 而不是把清单删掉——删掉会被 require_success/SyntaxError 之类的前置问题掩盖。
        H.patch(os.path.join(lib, "wflib", "tasks.py"),
                '"governance_omitted": [],',
                '"governance_omitted": [{"category": "manual_compare", "note": "注入"}],')
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
    governance = facts.get("governance") or {}
    problems = []
    # ① 声明面仍是列表、每条都有 note（A5 纪律不变）
    if not isinstance(omitted, list):
        problems.append(f"未声明未输出类别：{omitted}")
    else:
        categories = {item.get("category") for item in omitted if isinstance(item, dict)}
        if not all(item.get("note") for item in omitted if isinstance(item, dict)):
            problems.append("缺少说明 note")
        # ② 2026-11-12 交付后：已交付的两类**不得**再出现在声明里
        delivered = {"manual_compare", "author_order"}
        if categories & delivered:
            problems.append(f"已交付的类别仍在 governance_omitted：{sorted(categories & delivered)}")
        # ③ 反过来：输出里必须真的有两类，否则"移出声明"就只是删了一句话
        missing = delivered - set(governance)
        if missing:
            problems.append(f"governance 缺输出：{sorted(missing)}")
        # ④ 除声明之外，不得有"未声明且未输出"的类别
        expected = {"archive_terminals", "archive_references", "spec_usage", "inspection"}
        absent = expected - set(governance)
        if absent:
            problems.append(f"既有治理输出缺失：{sorted(absent)}")
        if categories - set(expected) - delivered - {"out_of_scope_duplicates"}:
            problems.append(f"声明了未知类别：{sorted(categories)}")
    if problems:
        raise H.TargetFailure("；".join(problems))
    return None


if __name__ == "__main__":
    sys.exit(H.main(check))
