"""A14（裁定：甲）：`--unavailable` 与 `--plan` 不能同批。

历史缺陷：`--unavailable` 只决定 `verdict`，而 disposition 校验与写入在分支之后**无条件执行**
——于是"审查做不成"可以被顺手用来登记关闭，绕开审查事实；而 ⑥ 的 C3 阻断越强，这条路的
激励越强（乘积关系）。

现在两者必须分开登记：先 `--register-only --plan` 登记复核关闭（A8），再 `--unavailable`
声明本轮审查不可用。拒绝发生在任何写入之前。
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


def write_report(root):
    relative = "review/round-1/review-codex.md"
    path = Path(root) / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    body = {"protocol": "wf-review-v1", "task-id": "t1", "round": 1,
            "review-time": "2026-11-11T00:00:00.000000Z", "review-focus": "x",
            "check-anchor": {"check_id": "c1", "check_anchor": ANCHOR},
            "read-scope": ["pkg/**"],
            "excluded-scope": ["node_modules/**", ".env", "*.pem", ".codex/**", "../**"],
            "scope-exceptions": [], "axes": {name: "pass" for name in review.REVIEW_AXES},
            "findings": [{"id": "f1", "severity": "blocking"}], "verdict": "pass"}
    path.write_text(review.REPORT_MARKER + "\n\n```json\n"
                    + json.dumps(body, ensure_ascii=False) + "\n```\n", encoding="utf-8")
    return relative, records.file_digest(path)


class UnavailableExclusiveTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = self._tmp.name
        self.ctx = Ctx(self.root)
        self.task_dir = Path(self.root) / ".wf" / "tasks" / "t1"
        self.task_dir.mkdir(parents=True)
        relative, digest = write_report(self.root)
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

    def files(self, name, payload):
        path = Path(self.root) / name
        path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        return str(path)

    def test_unavailable_with_plan_is_rejected_before_any_write(self):
        before = (self.task_dir / "task.json").read_text(encoding="utf-8")
        plan = self.files("plan.json", [{"finding_id": "f1", "decision": "accepted",
                                         "reason": "已修", "recheck_by": "human:xzc",
                                         "round": 1, "slot": "s1"}])
        declaration = self.files("unavailable.json", {"evidence": "机器不可用，无法取材料"})
        with self.assertRaises(review.ReviewError) as caught:
            review.decide(self.ctx, {"id": "t1"}, 1, plan, declaration)
        self.assertEqual(caught.exception.code, "WF_SEMANTIC_DECISION")
        self.assertIn("不能同批", caught.exception.facts["reason"])
        self.assertTrue(caught.exception.facts["exits"])        # 给了两步出口
        self.assertEqual((self.task_dir / "task.json").read_text(encoding="utf-8"), before)

    def test_register_only_remains_the_closing_path(self):
        plan = self.files("plan.json", [{"finding_id": "f1", "decision": "accepted",
                                         "reason": "已修", "recheck_by": "human:xzc",
                                         "round": 1, "slot": "s1"}])

        def _start(_ctx, path, task, *_a, **_k):
            task = dict(task)
            task["action"] = {"id": "a1", "state": "started"}
            records.write_json(os.path.join(path, "task.json"), task)
            return task, task["action"]

        with mock.patch.object(review, "standard_drift_gate", return_value=None), \
                mock.patch.object(tasks_mod, "_start_task_action", _start), \
                mock.patch.object(tasks_mod, "_finish_task_action",
                                  lambda _c, _p, task, *_a, **_k: (task, {"ok": True})):
            result = review.decide(self.ctx, {"id": "t1"}, 1, plan, register_only=True)
        self.assertEqual(result["code"], "WF_OK")
        task = records.load_json(self.task_dir / "task.json")
        self.assertEqual(len(task["reviews"]["dispositions"]), 1)
        self.assertNotIn("result", task["reviews"])              # 关闭不产生结论


if __name__ == "__main__":
    unittest.main()
