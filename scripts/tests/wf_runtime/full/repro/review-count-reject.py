#!/usr/bin/env python3
"""N2：审查人数不成立（同一 CLI 双槽位）必须拒绝输入、不产生 verdict、不落 fail 历史。

缺陷形态：把"人数不合格"当审查结论，写 result.verdict=fail 并进 attempts.outcome，
于是输入无效被记成正式审查失败，还会触发复盘语义。
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _harness as H
import _review_flow as F


def check():
    root, _lib, _payload = H.stage()
    project = H.deploy(root)
    if os.environ.get("WF_REPRO_INJECT") == "1":
        # 注入：把"人数不足"退回成写 verdict=fail 的旧口径
        # 只保留可观测的注入点；"把人数不足写回 reasons"这一半在提前拒绝存在时被遮蔽，
        # 不能算作可证伪（第九轮复审 N9-3）
        H.patch(os.path.join(project, ".wf/lib/wflib/review.py"),
                "if input_problems:",
                "if False:  # 注入：不提前拒绝")
    task_id, task_dir = F.build_task(project, root)
    rc, payload, record = F.run_review(project, root, task_id, task_dir, ["codex", "codex"])

    problems = []
    H.require_business_code(payload, rc)
    H.only_two_outcomes((payload or {}).get("code") if rc != 0 else "WF_OK",
                        "WF_REVIEW_INVALID", "review-count-reject")
    code = (payload or {}).get("code")
    if code != "WF_REVIEW_INVALID":
        problems.append(f"原因码不是 WF_REVIEW_INVALID：{code}")
    reviews = record.get("reviews") or {}
    if reviews.get("result") is not None:
        problems.append(f"仍写了判定：{(reviews.get('result') or {}).get('verdict')}")
    if any((a.get("outcome") == "fail") for a in (reviews.get("attempts") or [])):
        problems.append("attempts 落了 fail 历史")
    facts = (payload or {}).get("facts") or {}
    if not facts.get("exits"):
        problems.append("拒绝时未给出口")
    if problems:
        raise H.TargetFailure("；".join(problems))
    return None


if __name__ == "__main__":
    sys.exit(H.main(check))
