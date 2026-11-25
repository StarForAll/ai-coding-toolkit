"""review-status 的轮级 next_ 与槽位提示必须指向同一处置（2026-11-25 独立审查 M-4/M-5）。

两处真实分叉：
- M-4：混合基线 + 另一槽位有 done 待导入报告时，槽位说"处置见轮级 next_"，轮级 next_
  却只报"先 review-import"，通篇不提混合基线（A-3 要消的"同一页两句话"在该分支重现）。
- M-5：材料目录整体消失（材料在系统临时目录下）而报告已导入时，status 回落成
  "材料未齐，等 reviewer 产出"——一个永远等不到的出口；decide 侧其实按
  "round has none" 拒绝。
"""

import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "docs" / "workflows" / "wf" / "payload" / "lib"))

from wflib import cli, records, review  # noqa: E402

ANCHOR = "sha256:" + "a" * 64
RESTORED = "sha256:" + "d" * 64
LIVE = "sha256:" + "b" * 64


class ReviewStatusNextTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.stage = self.root / "staging"
        self.task_dir = self.root / ".wf/tasks/t1"
        for agent in ("pi", "zcode"):
            path = self.task_dir / "review" / "round-1" / f"review-{agent}.md"
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("<!-- wf-review-agent:v1 status=done -->\n", encoding="utf-8")
        staged = self.stage / "round-1" / "review-dsh.md"
        staged.parent.mkdir(parents=True, exist_ok=True)
        staged.write_text("<!-- wf-review-agent:v1 status=done -->\n", encoding="utf-8")
        self._write_task()

    def tearDown(self):
        self._tmp.cleanup()

    def _write_task(self):
        imported = [
            {"round": 1, "slot": "s1", "agent": "pi",
             "report_path": ".wf/tasks/t1/review/round-1/review-pi.md",
             "report_digest": records.file_digest(self.task_dir / "review/round-1/review-pi.md"),
             "anchor": {"check_anchor": ANCHOR},
             "materials": {"identity": RESTORED, "restored": True}},
            {"round": 1, "slot": "s2", "agent": "zcode",
             "report_path": ".wf/tasks/t1/review/round-1/review-zcode.md",
             "report_digest": records.file_digest(self.task_dir / "review/round-1/review-zcode.md"),
             "anchor": {"check_anchor": ANCHOR},
             "materials": {"identity": LIVE}},
        ]
        records.write_json(self.task_dir / "task.json", {
            "id": "t1", "title": "t", "status": "in_progress", "phase": "check",
            "check": {"id": "c1", "result": "pass", "anchor": {"check_anchor": ANCHOR}},
            "plan": {"complexity": "complex"},
            "reviews": {
                "launches": [{"round": 1, "implementation_cli": "dsh",
                              "slots": [{"slot": "s1"}, {"slot": "s2"}, {"slot": "s3"}],
                              "anchor": {"check_anchor": ANCHOR}, "temp_paths": []}],
                "imported": imported, "dispositions": []}})

    def _write_current_materials(self):
        materials = self.stage / "round-1" / "materials"
        materials.mkdir(parents=True, exist_ok=True)
        for name, content in (("diff.patch", "x\n"), ("prd.md", "# prd\n"),
                              ("check.json", "{}\n"), ("status.json", "{}\n"),
                              ("tests.json", "{}\n")):
            records.atomic_write(materials / name, content)
        review.write_materials_manifest(materials, "c2", ANCHOR, {})

    def _status(self):
        ctx = SimpleNamespace(root=str(self.root))
        args = cli.Args(["--task", "t1"])
        with mock.patch.object(review, "_current_anchor", return_value=(ANCHOR, {})), \
                mock.patch.object(review, "staging_root", lambda _ctx, _task: str(self.stage)):
            return cli.cmd_review_status(ctx, args)

    def test_mixed_baseline_outranks_ready_to_import(self):
        self._write_current_materials()
        result = self._status()
        next_ = result["next"]
        self.assertIn("混合基线", next_)
        self.assertIn("另有报告已写完待导入（s3）", next_)
        slots = {item["slot"]: item for item in result["facts"]["slots"]}
        self.assertIn("见轮级 next_", slots["s1"]["reason"])

    def test_missing_materials_does_not_ask_to_wait_for_reviewers(self):
        result = self._status()
        next_ = result["next"]
        self.assertIn("材料目录已不在", next_)
        self.assertNotIn("等 reviewer 产出", next_)
        slots = {item["slot"]: item for item in result["facts"]["slots"]}
        self.assertIn("无材料身份", slots["s1"]["reason"])

    def test_restored_entry_without_materials_points_to_rebuild(self):
        """restore 记录 + 当前无材料：应说"重建材料（同 Check 身份复现）后仍可判定"，不是新轮。"""
        task = records.load_json(self.task_dir / "task.json")
        task["reviews"]["launches"][0]["slots"] = [{"slot": "s1"}, {"slot": "s2"}]
        task["reviews"]["imported"] = [task["reviews"]["imported"][0]]   # 只剩 restored 的 s1
        records.write_json(self.task_dir / "task.json", task)
        result = self._status()
        self.assertIn("材料目录已不在", result["next"])
        slots = {item["slot"]: item for item in result["facts"]["slots"]}
        self.assertIn("重建材料", slots["s1"]["reason"])
        self.assertIn("仍可直接判定", slots["s1"]["reason"])
        self.assertNotIn("同轮无法恢复", slots["s1"]["reason"])

    def test_restored_round_with_missing_slot_waits_before_decide(self):
        """还原记录 + 另一槽位未到：不能说"可直接判定"（人数不足必拒），要说等齐。"""
        task = records.load_json(self.task_dir / "task.json")
        task["reviews"]["imported"] = [task["reviews"]["imported"][0]]   # s2 未到
        records.write_json(self.task_dir / "task.json", task)
        (self.stage / "round-1" / "review-dsh.md").unlink()              # 也不在暂存区
        self._write_current_materials()
        result = self._status()
        self.assertIn("槽位未到", result["next"])
        self.assertIn("不必重导", result["next"])
        self.assertNotIn("可直接 review-decide", result["next"])

    def test_no_launch_points_to_review_launch(self):
        """尚未发起任何轮次时，"等 reviewer 产出"永远等不到：先 review-launch。"""
        task = records.load_json(self.task_dir / "task.json")
        task["reviews"] = {"launches": [], "imported": [], "dispositions": []}
        records.write_json(self.task_dir / "task.json", task)
        result = self._status()
        self.assertIn("review-launch", result["next"])
        self.assertNotIn("等 reviewer 产出", result["next"])

    def test_legacy_launch_without_slots_is_not_reported_as_unlaunched(self):
        """旧 launch 没有 slots 时 required=0 不等于"没发起"：不能让 AI 重复 launch。"""
        task = records.load_json(self.task_dir / "task.json")
        task["reviews"]["launches"][0].pop("slots")
        task["reviews"]["imported"] = []
        records.write_json(self.task_dir / "task.json", task)
        (self.stage / "round-1" / "review-dsh.md").unlink()
        result = self._status()
        self.assertIn("已发起但未声明槽位", result["next"])
        self.assertNotIn("尚未发起审查", result["next"])

    def test_drift_with_live_report_marks_restored_slot_as_blocked(self):
        """drift + restored + live：restored 槽位不能声称可直接判定（整轮被 drift 阻断）。"""
        self._write_current_materials()
        materials = self.stage / "round-1" / "materials"
        manifest = records.load_json(materials / "materials-manifest.json")
        task = records.load_json(self.task_dir / "task.json")
        task["reviews"]["imported"][1]["materials"] = {"identity": review.materials_identity(manifest)}
        records.write_json(self.task_dir / "task.json", task)
        (materials / "diff.patch").write_text("changed\n", encoding="utf-8")
        result = self._status()
        slots = {item["slot"]: item for item in result["facts"]["slots"]}
        self.assertIn("drift 会阻断整轮判定", slots["s1"]["reason"])

    def test_legacy_slots_point_to_adoption_not_missing_directory(self):
        """legacy（只丢 manifest）：槽位应说采纳现场字节，不是目录已不在。"""
        self._write_current_materials()
        (self.stage / "round-1" / "materials" / "materials-manifest.json").unlink()
        result = self._status()
        slots = {item["slot"]: item for item in result["facts"]["slots"]}
        self.assertIn("采纳现场字节", slots["s1"]["reason"])
        self.assertNotIn("目录已不在", slots["s1"]["reason"])

    def test_legacy_package_without_manifest_is_adoptable_not_missing(self):
        """只丢 manifest、材料文件仍在：应说"采纳现场字节"，不能说"目录已不在"。"""
        self._write_current_materials()
        (self.stage / "round-1" / "materials" / "materials-manifest.json").unlink()
        result = self._status()
        self.assertIn("采纳现场字节", result["next"])
        self.assertNotIn("目录已不在", result["next"])

    def test_drift_with_live_reports_points_to_restore_not_decide(self):
        """材料 drift 时 live 报告必被 decide 拒：status 不能再说"下一步 review-decide"。"""
        task = records.load_json(self.task_dir / "task.json")
        task["reviews"]["imported"] = [task["reviews"]["imported"][1]]   # 只剩 live 的 s2
        records.write_json(self.task_dir / "task.json", task)
        self._write_current_materials()
        materials = self.stage / "round-1" / "materials"
        (materials / "diff.patch").write_text("v1\n", encoding="utf-8")
        records.write_json(materials / "materials-manifest.json", {
            "protocol": "wf-materials-v1", "check_id": "c2", "check_anchor": ANCHOR,
            "generated_at": "2026-11-25T00:00:00.000000Z",
            "files": {"diff.patch": records.file_digest(materials / "diff.patch")}, "facts": {}})
        (materials / "diff.patch").write_text("v2\n", encoding="utf-8")
        result = self._status()
        self.assertIn("drift", result["next"])
        self.assertNotIn("下一步 review-decide", result["next"])

    def test_restored_only_without_materials_can_rematerialize_and_decide(self):
        """只有还原记录、材料目录不在：重建材料后同轮可判定，不该直接推去开新一轮。"""
        task = records.load_json(self.task_dir / "task.json")
        task["reviews"]["imported"] = [task["reviews"]["imported"][0]]   # 只剩 restored s1
        records.write_json(self.task_dir / "task.json", task)
        result = self._status()
        self.assertIn("重建材料", result["next"])
        self.assertIn("review-decide", result["next"])
        self.assertNotIn("开新一轮重新出材料", result["next"])

    def test_decided_round_reports_verdict_even_if_materials_gone(self):
        """已判定轮优先：材料不在也不能把 AI 劝去"重新出材料/开新一轮"而不提已有结论。"""
        task = records.load_json(self.task_dir / "task.json")
        task["reviews"]["result"] = {"round": 1, "verdict": "pass",
                                     "anchor": {"check_anchor": ANCHOR}}
        records.write_json(self.task_dir / "task.json", task)
        result = self._status()
        self.assertIn("已产生判定", result["next"])


if __name__ == "__main__":
    unittest.main()
