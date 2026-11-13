"""C1：摘要读取统一归因——读不到 ≠ 被改写，也不该把只读查询打成异常栈。

防的失败：`records.file_digest` 只捕 `FileNotFoundError`，权限/IO 故障（含"路径是目录"）
会以裸 `OSError` 冒出来：`review-status` 直接崩、`review-import` 抛非协议异常，同一个故障
在不同命令里被说成不同的事。审计断言保证 review/gates 里不再有裸的摘要读取。
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


class FakeCtx:
    def __init__(self, root):
        self.root = str(root)

    def require_held(self, task=None):
        return {"id": "sess-test"}, {"id": "human:test"}


def write_report(root, relative, findings=()):
    path = Path(root) / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    body = {"protocol": "wf-review-v1", "task-id": "t1", "round": 1,
            "review-time": "2026-11-11T00:00:00.000000Z", "review-focus": "x",
            "check-anchor": {"check_id": "c1", "check_anchor": ANCHOR},
            "read-scope": ["pkg/**"],
            "excluded-scope": ["node_modules/**", ".env", "*.pem", ".codex/**", "../**", ".wf/tasks/**"],
            "scope-exceptions": [], "axes": {name: "pass" for name in review.REVIEW_AXES},
            "findings": list(findings), "verdict": "pass"}
    path.write_text("<!-- wf-review-agent:v1 status=done -->\n" + review.REPORT_MARKER
                    + "\n\n```json\n"
                    + json.dumps(body, ensure_ascii=False) + "\n```\n", encoding="utf-8")
    return relative, records.file_digest(path)


def break_path(path):
    """把文件换成同名目录：存在但**读不了**（`IsADirectoryError`，不是 NotFound）。"""
    Path(path).unlink()
    Path(path).mkdir()


class DigestStateTest(unittest.TestCase):
    def test_three_states(self):
        with tempfile.TemporaryDirectory() as tmp:
            missing = os.path.join(tmp, "nope")
            digest, cause, _reason = records.file_digest_state(missing)
            self.assertIsNone(digest)
            self.assertEqual(cause, "missing")
            blocked = os.path.join(tmp, "blocked")
            os.makedirs(blocked)
            digest, cause, reason = records.file_digest_state(blocked)
            self.assertIsNone(digest)
            self.assertEqual(cause, "unreadable")
            self.assertTrue(reason)
            ok = os.path.join(tmp, "file.txt")
            Path(ok).write_text("x", encoding="utf-8")
            digest, cause, reason = records.file_digest_state(ok)
            self.assertTrue(digest.startswith("sha256:"))
            self.assertIsNone(cause)
            self.assertIsNone(reason)


class ReadAttributionTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = self._tmp.name
        self.ctx = FakeCtx(self.root)

    def tearDown(self):
        self._tmp.cleanup()

    def task(self, relative, digest):
        return {"id": "t1", "reviews": {
            "launches": [{"round": 1, "slots": [{"slot": "s1"}]}],
            "imported": [{"round": 1, "slot": "s1", "agent": "pi", "report_path": relative,
                          "report_digest": digest, "anchor": {"check_anchor": ANCHOR}}],
            "dispositions": []}}

    def test_status_reports_unreadable_instead_of_crashing(self):
        relative, digest = write_report(self.root, "review/round-1/review-pi.md")
        task = self.task(relative, digest)
        break_path(Path(self.root) / relative)
        with mock.patch.object(review, "_current_anchor", return_value=(ANCHOR, {})):
            facts = review.status_of_round(self.ctx, task, 1)   # 只读查询，不得抛栈
        slot = facts["slots"][0]
        self.assertEqual(slot["state"], "unreadable")
        self.assertEqual(slot["cause"], "unreadable")
        self.assertIn("无法读取", slot["reason"])

    def test_open_findings_attributes_unreadable(self):
        relative, digest = write_report(self.root, "review/round-1/review-pi.md",
                                        findings=[{"id": "f1", "severity": "blocking"}])
        task = self.task(relative, digest)
        break_path(Path(self.root) / relative)
        facts = review.open_findings(self.ctx, task)
        self.assertEqual(facts["unavailable"][0]["cause"], "unreadable")
        self.assertEqual(facts["blocking"], [])

    def test_import_rejects_unreadable_target_with_protocol_error(self):
        task_dir = Path(self.root) / ".wf" / "tasks" / "t1"
        task_dir.mkdir(parents=True)
        records.write_json(task_dir / "task.json", {
            "id": "t1", "title": "t", "status": "in_progress", "phase": "check",
            "revision": 1, "check": {"id": "c1", "result": "pass",
                                     "anchor": {"check_anchor": ANCHOR}},
            "entry_snapshot": {"touch_paths": []},
            "reviews": {"launches": [{"round": 1, "implementation_cli": "dsh",
                                      "slots": [{"slot": "s1"}], "temp_paths": []}],
                        "imported": []}})
        staging = Path(self.root) / "staging" / "round-1"
        staging.mkdir(parents=True)
        report = staging / "review-pi.md"
        write_report(self.root, "unused.md")          # 只为拿一份合法正文
        report.write_text((Path(self.root) / "unused.md").read_text(encoding="utf-8"),
                          encoding="utf-8")
        target = task_dir / "review" / "round-1" / "review-pi.md"
        target.mkdir(parents=True)                   # 目标路径是目录 ⇒ 读不到

        def _start(_ctx, path, task, *_args, **_kwargs):
            task = dict(task)
            task["action"] = {"id": "a1", "state": "started"}
            records.write_json(os.path.join(path, "task.json"), task)
            return task, task["action"]

        with mock.patch.object(review, "_current_anchor", return_value=(ANCHOR, {})), \
                mock.patch.object(review, "staging_root",
                                  lambda _ctx, _task: os.path.join(self.root, "staging")), \
                mock.patch.object(tasks_mod, "_start_task_action", _start), \
                mock.patch.object(tasks_mod, "_finish_task_action",
                                  lambda _ctx, _path, task, *_a, **_k: (task, {"ok": True})):
            with self.assertRaises(review.ReviewError) as caught:
                review.import_report(self.ctx, {"id": "t1"}, 1, None, str(report),
                                     _from_discovery=True, agent="pi")
        self.assertEqual(caught.exception.code, "WF_REVIEW_INVALID")
        self.assertIn("无法读取", caught.exception.facts["reason"])


class AuditTest(unittest.TestCase):
    """审计断言：报告/规格的摘要读取只走 `records.file_digest_state`。"""

    def test_no_bare_digest_reads_in_review_paths(self):
        lib = REPO / "docs" / "workflows" / "wf" / "payload" / "lib" / "wflib"
        for name in ("review.py", "gates.py"):
            source = (lib / name).read_text(encoding="utf-8")
            self.assertNotIn("records.file_digest(", source,
                             f"{name} 仍有裸的摘要读取：统一走 records.file_digest_state")


if __name__ == "__main__":
    unittest.main()
