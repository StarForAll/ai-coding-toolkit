"""A1：`slot`（声明名）与 `agent`（reviewer 名）是两个身份域，不得互相顶替。

防的失败：launch 声明 `s1/s2`，而导入记录把 reviewer 名写进 `slot` → `review-status`
按声明槽位找不到报告，明明两份都到位却报 `missing [s1, s2]`；放行/撤销按 `slot` 匹配，
两种身份混用就会误配（⑥ 裁定 B 已把放行键固定为 `(round, slot, report_digest)`）。

用例不依赖任何特定 task id 的全局暂存目录：`staging_root` 一律指向临时目录。
"""

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "docs" / "workflows" / "wf" / "payload" / "lib"))

from wflib import records, review  # noqa: E402

DIGEST = "sha256:" + "0" * 64


class FakeCtx:
    def __init__(self, root):
        self.root = str(root)


def write(root, relative, text):
    path = Path(root) / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def task_record(slots, imported=()):
    return {"id": "t1", "title": "t", "reviews": {
        "launches": [{"round": 1, "slots": list(slots)}],
        "imported": list(imported)}}


class SlotStatusTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = self._tmp.name
        self.ctx = FakeCtx(self.root)

    def tearDown(self):
        self._tmp.cleanup()

    def _status(self, record):
        with mock.patch.object(review, "staging_root",
                               lambda _ctx, _task_id: os.path.join(self.root, "staging")):
            return review.status_of_round(self.ctx, record)

    def test_staged_reports_fill_declared_slots(self):
        """声明 `s1/s2` + 两份 reviewer 报告 → 按位置分配，不缺槽位。"""
        staging = Path(self.root) / "staging" / "round-1"
        staging.mkdir(parents=True)
        for agent in ("pi", "zcode"):
            (staging / f"review-{agent}.md").write_text(
                "<!-- wf-review-agent:v1 status=done -->\n", encoding="utf-8")
        facts = self._status(task_record([{"slot": "s1"}, {"slot": "s2"}]))
        by_slot = {item["slot"]: item for item in facts["slots"]}
        self.assertEqual(sorted(by_slot), ["s1", "s2"])
        self.assertEqual(facts["missing"], [])
        self.assertEqual(facts["arrived"], 2)
        self.assertEqual(by_slot["s1"]["state"], "staged")
        self.assertEqual(by_slot["s1"]["agent"], "pi")
        self.assertEqual(by_slot["s2"]["agent"], "zcode")
        self.assertTrue(facts["material_ready"])

    def test_legacy_entries_are_derived_positionally_without_rewrite(self):
        """旧记录（`slot` 记的是 reviewer 名）读取时推导到声明槽位，不回写。"""
        entries = []
        for agent in ("zcode", "dsh"):
            relative = f"review/round-1/review-{agent}.md"
            path = write(self.root, relative, "报告正文")
            digest = records.file_digest(path)
            entries.append({"round": 1, "slot": agent, "agent": agent,
                            "report_path": relative, "report_digest": digest,
                            "anchor": {"check_anchor": DIGEST}})
        record = task_record([{"slot": "s1"}, {"slot": "s2"}], imported=entries)
        facts = self._status(record)
        by_slot = {item["slot"]: item for item in facts["slots"]}
        self.assertEqual(facts["missing"], [])
        self.assertEqual(facts["arrived"], 2)
        # 位置分配顺序 = 名字排序 dsh < zcode
        self.assertEqual(by_slot["s1"]["recorded_slot"], "dsh")
        self.assertEqual(by_slot["s2"]["recorded_slot"], "zcode")
        self.assertTrue(by_slot["s1"]["slot_derived"])
        self.assertTrue(by_slot["s2"]["slot_derived"])
        # 记录本身没被改写：放行键仍取原值
        self.assertEqual(record["reviews"]["imported"][0]["slot"], "zcode")
        self.assertEqual(review.release_key(record["reviews"]["imported"][0]),
                         (1, "zcode", record["reviews"]["imported"][0]["report_digest"]))

    def test_reviewer_cli_declaration_wins_over_position(self):
        """声明 `reviewer_cli` 时按声明绑定，不按名字顺序。"""
        staging = Path(self.root) / "staging" / "round-1"
        staging.mkdir(parents=True)
        for agent in ("pi", "zcode"):
            (staging / f"review-{agent}.md").write_text(
                "<!-- wf-review-agent:v1 status=done -->\n", encoding="utf-8")
        facts = self._status(task_record([{"slot": "s1", "reviewer_cli": "zcode"},
                                          {"slot": "s2", "reviewer_cli": "pi"}]))
        by_slot = {item["slot"]: item for item in facts["slots"]}
        self.assertEqual(by_slot["s1"]["agent"], "zcode")
        self.assertEqual(by_slot["s2"]["agent"], "pi")


class SlotAssignmentTest(unittest.TestCase):
    def test_imported_slot_is_sticky(self):
        """已导入记录的槽位是粘性的：再出现同名报告也不换槽位。"""
        imported = [{"round": 1, "slot": "s2", "agent": "pi"}]
        bound = review.slot_assignment({"slots": [{"slot": "s1"}, {"slot": "s2"}]},
                                       imported, ["pi", "zcode"])
        self.assertEqual(bound["s2"]["agent"], "pi")
        self.assertEqual(bound["s1"]["agent"], "zcode")

    def test_no_declared_slots_falls_back_to_recorded_value(self):
        """没有声明槽位（旧记录/未 launch）时退化为「槽位 = 记录原值」，不猜。"""
        imported = [{"round": 1, "slot": "zcode", "agent": "zcode"}]
        bound = review.slot_assignment(None, imported)
        self.assertEqual(sorted(bound), ["zcode"])
        self.assertFalse(bound["zcode"]["derived"])


if __name__ == "__main__":
    unittest.main()
