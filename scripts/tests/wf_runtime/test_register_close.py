"""A8：`review-decide --register-only` —— 只登记复核关闭，不产生结论。

历史缺陷：写 dispositions 的唯一入口是 `review-decide`，它先做人数/异种资格校验；light
任务想关掉一个 C2 也得凑齐整轮审查。裁定（甲）：在 `review-decide` 加"只登记"通道，
关掉的只是**结论产出**，关闭本身的硬条件（结构 / 复核不得自证 / finding 必须属已导入报告）
全部照旧。
"""

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "docs" / "workflows" / "wf" / "payload" / "lib"))

from wflib import records, review, tasks as tasks_mod  # noqa: E402

ANCHOR = "sha256:" + "a" * 64


class Ctx:
    def __init__(self, root):
        self.root = str(root)

    def require_held(self, task=None):
        return {"id": "sess-test"}, {"id": "human:test"}

    def rule_version(self):
        return "rules-v1"


def write_report(root, round_no, slot, findings):
    relative = f"review/round-{round_no}/review-{slot}.md"
    path = Path(root) / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    body = {"protocol": "wf-review-v1", "task-id": "t1", "round": round_no,
            "review-time": "2026-11-11T00:00:00.000000Z", "review-focus": "x",
            "check-anchor": {"check_id": "c1", "check_anchor": ANCHOR},
            "read-scope": ["pkg/**"],
            "excluded-scope": ["node_modules/**", ".env", "*.pem", ".codex/**", "../**", ".wf/tasks/**"],
            "scope-exceptions": [], "axes": {name: "pass" for name in review.REVIEW_AXES},
            "findings": findings, "verdict": "pass"}
    path.write_text(review.REPORT_MARKER + "\n\n```json\n"
                    + json.dumps(body, ensure_ascii=False) + "\n```\n", encoding="utf-8")
    return relative, records.file_digest(path)


class RegisterCloseTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = self._tmp.name
        self.ctx = Ctx(self.root)
        self.task_dir = Path(self.root) / ".wf" / "tasks" / "t1"
        self.task_dir.mkdir(parents=True)
        relative, digest = write_report(self.root, 1, "codex",
                                        [{"id": "f1", "severity": "blocking"}])
        records.write_json(self.task_dir / "task.json", {
            "id": "t1", "title": "t", "status": "in_progress", "phase": "execute",
            "revision": 1, "plan": {"complexity": "light"},
            "check": {"id": "c1", "result": "pass", "anchor": {"check_anchor": ANCHOR}},
            "entry_snapshot": {"touch_paths": []},
            "reviews": {"last_round": 1,
                        "launches": [{"round": 1, "implementation_cli": "codex",
                                      "slots": [{"slot": "s1"}]}],
                        "imported": [{"round": 1, "slot": "s1", "agent": "codex",
                                      "report_path": relative, "report_digest": digest,
                                      "anchor": {"check_anchor": ANCHOR}}],
                        "dispositions": []}})

    def tearDown(self):
        self._tmp.cleanup()

    def plan(self, dispositions):
        path = Path(self.root) / "plan.json"
        path.write_text(json.dumps(dispositions, ensure_ascii=False), encoding="utf-8")
        return str(path)

    def decide(self, plan_path, **kwargs):
        def _start(ctx, path, task, *_a, **_k):
            task = dict(task)
            task["action"] = {"id": "a1", "state": "started"}
            records.write_json(os.path.join(path, "task.json"), task)
            return task, task["action"]

        with mock.patch.object(review, "standard_drift_gate", return_value=None), \
                mock.patch("wflib.tasks._is_approved_plan", return_value=True), \
                mock.patch("wflib.gates.check_validity",
                           return_value={"valid": True, "code": None, "facts": {},
                                         "blockers": []}), \
                mock.patch.object(tasks_mod, "_start_task_action", _start), \
                mock.patch.object(tasks_mod, "_finish_task_action",
                                  lambda _ctx, _path, task, *_a, **_k: (task, {"ok": True})):
            return review.decide(self.ctx, {"id": "t1"}, 1, plan_path, **kwargs)

    def task(self):
        return records.load_json(self.task_dir / "task.json")

    def test_register_only_closes_without_producing_a_verdict(self):
        result = self.decide(self.plan([
            {"finding_id": "f1", "decision": "accepted", "reason": "已修复并复核",
             "recheck_by": "human:xzc", "round": 1, "slot": "s1"}]), register_only=True)
        self.assertEqual(result["code"], "WF_OK")
        self.assertEqual(result["facts"]["closing"], 1)
        task = self.task()
        self.assertNotIn("result", task["reviews"])        # 不产生结论
        self.assertNotIn("rounds", task["reviews"])        # 不写逐轮判定
        self.assertEqual(len(task["reviews"]["dispositions"]), 1)
        facts = review.open_findings(self.ctx, task)
        self.assertEqual(facts["blocking"], [])            # 关闭生效（唯一的派生点）

    def test_register_only_skips_eligibility(self):
        # 单 reviewer 且与实施 CLI 相同：整轮判定会因人数/异种被拒，只登记通道不受影响
        result = self.decide(self.plan([
            {"finding_id": "f1", "decision": "accepted", "reason": "已修",
             "recheck_by": "human:xzc", "round": 1, "slot": "s1"}]), register_only=True)
        self.assertEqual(result["code"], "WF_OK")

    def test_register_only_requires_a_plan(self):
        with self.assertRaises(review.ReviewError) as caught:
            review.decide(self.ctx, {"id": "t1"}, 1, register_only=True)
        self.assertEqual(caught.exception.code, "WF_SEMANTIC_DECISION")
        self.assertIn("--plan", caught.exception.facts["reason"])

    def test_register_only_rejects_unavailable(self):
        with self.assertRaises(review.ReviewError) as caught:
            review.decide(self.ctx, {"id": "t1"}, 1, self.plan([]),
                          unavailable_path="u.json", register_only=True)
        self.assertIn("不可用", caught.exception.facts["reason"])

    def test_register_only_still_rejects_self_closure(self):
        with self.assertRaises(review.ReviewError) as caught:
            self.decide(self.plan([
                {"finding_id": "f1", "decision": "accepted", "reason": "自己复核",
                 "recheck_by": "codex", "round": 1, "slot": "s1"}]), register_only=True)
        self.assertIn("不得自证", caught.exception.facts["problems"][0]["reason"])


if __name__ == "__main__":
    unittest.main()
