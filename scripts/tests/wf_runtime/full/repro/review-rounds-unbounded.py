#!/usr/bin/env python3
"""轮次不设上限：审查 fail、范围内修复并重跑 Check 后，同一任务可继续发起下一轮。

obligation（设计稿 §6.5、机制稿 §9.2 的 2026-11-09 人裁）：删除两轮额度后，"轮次用尽"
不再是合法阻断理由；fail 后在范围内修复 → 重跑 Check → 发新轮次是唯一正路。
2026-11-08 dogfood 的卡点正是这里：第 2 轮 fail 后改进度已新 Check，却因"同一实施尝试最多
两轮"无入口可走（当时 task-rework 未交付），用户只能要求"让当前任务的审查继续下去"。

缺陷形态（red）：在 launch 分配新一轮时重新引入"两轮额度"——第二轮起直接拒绝。
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _harness as H
import _review_flow as F

SLOTS = ["codex", "zcode"]


def check():
    root, _lib, _payload = H.stage()
    project = H.deploy(root)
    if os.environ.get("WF_REPRO_INJECT") == "1":
        # 注入：恢复"两轮额度"（launch 分配第二轮时拒绝）
        H.patch(os.path.join(project, ".wf/lib/wflib/review.py"),
                '        round_no = int(reviews.get("last_round") or 0) + 1\n',
                '        round_no = int(reviews.get("last_round") or 0) + 1\n'
                '        if round_no > 1:  # 注入：两轮额度（历史死路）\n'
                '            raise ReviewError("WF_SEMANTIC_DECISION",\n'
                '                              {"reason": "round budget exhausted", "round": round_no})\n')
    task_id, task_dir = F.build_task(project, root, complexity="complex")
    findings = [{"id": "f1", "severity": "blocking",
                 "statement": "pkg/a.py 的分支未处理输入", "assertion_ref": "a1",
                 "basis": "repro：第 1 轮未关闭 blocking"}]
    rc, payload, record = F.run_review(project, root, task_id, task_dir, SLOTS, findings=findings)
    problems = []
    verdict = ((record.get("reviews") or {}).get("result") or {}).get("verdict")
    if verdict != "fail":
        problems.append(f"第 1 轮未按未关闭 blocking 判 fail：{verdict}（rc={rc}）")
    # 范围内修复：改动交付面文件，使旧锚点失效
    open(os.path.join(project, "pkg/a.py"), "w").write("fixed\n")
    try:
        rc2, payload2, record2 = F.run_review(project, root, task_id, task_dir, SLOTS,
                                              round_no=2, launch_only=True)
    except H.Precondition as exc:
        # 只有注入的"两轮额度"（WF_SEMANTIC_DECISION）才算目标红；其它前置失败原样保留，
        # 不包装成目标断言（wf-delivery-discipline §8.7：前置失败不算 red 成功）。
        if "WF_SEMANTIC_DECISION" in str(exc) or "round budget" in str(exc):
            raise H.TargetFailure(f"修复并重跑 Check 后无法发起第 2 轮（轮次上限回归）：{exc}")
        raise
    facts = (payload2 or {}).get("facts") or {}
    if rc2 != 0:
        problems.append(f"第 2 轮 review-launch 未成功：{payload2.get('code')}")
    if facts.get("round") != 2:
        problems.append(f"第 2 轮 round 不是 2：{facts.get('round')}")
    launches = ((record2.get("reviews") or {}).get("launches") or [])
    if len(launches) != 2:
        problems.append(f"launches 未记录两轮：{[item.get('round') for item in launches]}")
    if problems:
        raise H.TargetFailure("；".join(problems))
    return None


if __name__ == "__main__":
    sys.exit(H.main(check))