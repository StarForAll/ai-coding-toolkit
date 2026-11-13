"""A4：导入端不可顶替——已登记摘要就是证据身份，删档后换一份不能顶掉它。

防的失败：报告的摘要校验只对**现文件**生效；把导入后的副本删掉，再导入同轮同槽位的
另一份报告，记录就被悄悄改写，旧证据消失且无人知道。
遗留形状（记录缺 `report_digest`）同理：磁盘字节与来件不同时必须显式 `--restore`。
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


class ImportHarness(unittest.TestCase):
    """导入端夹具：真实 task 记录 + 真实锁 + 打桩的 action/anchor（只测身份判定）。"""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = self._tmp.name
        self.ctx = Ctx(self.root)
        self.task_dir = Path(self.root) / ".wf" / "tasks" / "t1"
        self.task_dir.mkdir(parents=True)
        records.write_json(self.task_dir / "task.json", {
            "id": "t1", "title": "t", "status": "in_progress", "phase": "check",
            "revision": 1, "check": {"id": "c1", "result": "pass",
                                     "anchor": {"check_anchor": ANCHOR}},
            "entry_snapshot": {"touch_paths": []},
            "reviews": {"launches": [{"round": 1, "implementation_cli": "dsh",
                                      "slots": [{"slot": "s1"}], "temp_paths": []}],
                        "imported": []}})
        self.staging = Path(self.root) / "staging" / "round-1"
        self.staging.mkdir(parents=True)
        self.report = self.staging / "review-pi.md"
        self.imported_copy = self.task_dir / "review" / "round-1" / "review-pi.md"

    def tearDown(self):
        self._tmp.cleanup()

    def write_report(self, text="正文第一版"):
        body = {"protocol": "wf-review-v1", "task-id": "t1", "round": 1,
                "review-time": "2026-11-11T00:00:00.000000Z", "review-focus": "x",
                "check-anchor": {"check_id": "c1", "check_anchor": ANCHOR},
                "read-scope": ["pkg/**"],
                "excluded-scope": ["node_modules/**", ".env", "*.pem", ".codex/**", "../**", ".wf/tasks/**"],
                "scope-exceptions": [],
                "axes": {name: "pass" for name in review.REVIEW_AXES},
                "findings": [], "verdict": "pass"}
        self.report.write_text("<!-- wf-review-agent:v1 status=done -->\n" + review.REPORT_MARKER
                               + "\n\n```json\n" + json.dumps(body, ensure_ascii=False)
                               + "\n```\n" + text, encoding="utf-8")

    def _start(self, _ctx, path, task, *_args, **_kwargs):
        task = dict(task)
        task["action"] = {"id": "a1", "state": "started"}
        records.write_json(os.path.join(path, "task.json"), task)
        return task, task["action"]

    def import_report(self, **kwargs):
        with mock.patch.object(review, "_current_anchor", return_value=(ANCHOR, {})), \
                mock.patch.object(review, "staging_root",
                                  lambda _ctx, _task: os.path.join(self.root, "staging")), \
                mock.patch.object(tasks_mod, "_start_task_action", self._start), \
                mock.patch.object(tasks_mod, "_finish_task_action",
                                  lambda _ctx, _path, task, *_a, **_k: (task, {"ok": True})):
            return review.import_report(self.ctx, {"id": "t1"}, 1, None, str(self.report),
                                        _from_discovery=True, agent="pi", **kwargs)

    def imported(self):
        task = records.load_json(self.task_dir / "task.json")
        return task["reviews"]["imported"]

    def strip_digest(self):
        task = records.load_json(self.task_dir / "task.json")
        for entry in task["reviews"]["imported"]:
            entry.pop("report_digest", None)
        records.write_json(self.task_dir / "task.json", task)

class ImportIdentityTest(ImportHarness):
    """A4：已登记摘要就是证据身份，删档后换一份不能顶掉它。"""

    def test_same_bytes_reimport_after_deletion_is_idempotent(self):
        self.write_report()
        self.import_report()
        digest = self.imported()[0]["report_digest"]
        self.imported_copy.unlink()
        self.import_report()
        self.assertEqual(len(self.imported()), 1)
        self.assertEqual(self.imported()[0]["report_digest"], digest)
        self.assertTrue(self.imported_copy.is_file())

    def test_deleted_file_cannot_be_replaced_by_another_report(self):
        self.write_report()
        self.import_report()
        digest = self.imported()[0]["report_digest"]
        self.imported_copy.unlink()
        self.write_report("正文第二版（另一份报告）")
        with self.assertRaises(review.ReviewError) as caught:
            self.import_report()
        self.assertEqual(caught.exception.code, "WF_REVIEW_INVALID")
        self.assertIn("不可替换", caught.exception.facts["reason"])
        self.assertEqual(self.imported()[0]["report_digest"], digest)
        self.assertFalse(self.imported_copy.exists())

    def test_legacy_record_gets_its_digest_when_bytes_are_unchanged(self):
        self.write_report()
        self.import_report()
        self.strip_digest()
        self.import_report()          # 磁盘上就是这份字节：补摘要，不算替换
        self.assertTrue(self.imported()[0]["report_digest"])

    def test_legacy_record_with_changed_bytes_needs_restore(self):
        self.write_report()
        self.import_report()
        self.strip_digest()
        self.imported_copy.unlink()
        self.write_report("正文第二版")
        with self.assertRaises(review.ReviewError) as caught:
            self.import_report()
        self.assertIn("--restore", caught.exception.facts["reason"])
        self.import_report(restore=True)
        self.assertTrue(self.imported()[0]["report_digest"])

    def test_restore_is_rejected_on_first_import(self):
        self.write_report()
        with self.assertRaises(review.ReviewError) as caught:
            self.import_report(restore=True)
        self.assertIn("首次导入", caught.exception.facts["reason"])
        self.assertEqual(self.imported(), [])


class RestoreSemanticsTest(ImportHarness):
    """A5：`--restore` 只还原原身份（round/slot/report_path），**不改写 anchor**。"""

    def test_restore_keeps_the_recorded_anchor(self):
        self.write_report()
        self.import_report()
        task = records.load_json(self.task_dir / "task.json")
        entry = task["reviews"]["imported"][0]
        entry.pop("report_digest", None)
        # 原记录绑定的是旧 check（同一 anchor，不同 check_id）：restore 不得把它改成当前 check
        entry["anchor"] = {"check_id": "c0", "check_anchor": ANCHOR}
        records.write_json(self.task_dir / "task.json", task)
        self.imported_copy.unlink()
        self.write_report("正文第二版")
        self.import_report(restore=True)
        restored = self.imported()[0]
        self.assertEqual(restored["anchor"], {"check_id": "c0", "check_anchor": ANCHOR})
        self.assertEqual((restored["round"], restored["slot"]), (1, "s1"))
        self.assertTrue(restored["report_digest"])

    def test_normal_import_still_binds_the_current_check(self):
        self.write_report()
        self.import_report()
        self.assertEqual(self.imported()[0]["anchor"],
                         {"check_id": "c1", "check_anchor": ANCHOR})


if __name__ == "__main__":
    unittest.main()
