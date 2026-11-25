"""P1-1/P1-2（2026-11-24）：review-context 续写不丢授权范围、轮次材料一经物化即固定。

防的失败（dogfood 首次实测 + 独立审查 N1/N2/N3）：
- 续写分支 facts 缺 submitted_scope/readable_scope/exclusions/anchor——上下文压缩后
  reviewer 恰在需要重读授权边界时拿不到它；
- facts.materials.request 指向从未写入的位置（round_dir 根，实际写在 slot_dir）；
- 同锚点重跑 Check（新 check_id）后重写共享材料——先后两个 reviewer 读到不同日志版本，
  判定无法还原各自读到的证据；
- 材料被外部改动后无身份核对，静默续写。
"""

import json
import os
import sys
import tempfile
import unittest
import uuid
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "docs" / "workflows" / "wf" / "payload" / "lib"))

from wflib import records, review  # noqa: E402

ANCHOR = "sha256:" + "c" * 64
COVERED = ["node_modules/**", ".env", "*.pem", ".codex/**", "../**", ".wf/tasks/**"]


def _complete_materials(diff_text):
    """staging 写出一套**完整**材料：缺必需文件的旧包按新语义不再是可采纳的 legacy，
    夹具必须取自真实物化形状（`write_materials` 总是写全五个顶层文件）。"""
    def _write(*args, **kwargs):
        staging = Path(args[4])
        records.atomic_write(staging / "diff.patch", diff_text)
        records.atomic_write(staging / "prd.md", "# prd\n")
        records.write_json(staging / "check.json", {"check": {"id": "c1"}})
        records.write_json(staging / "status.json", {"problems": []})
        records.write_json(staging / "tests.json", {"commands": []})
        return {}
    return _write


class MaterialFixedTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.task_id = "t1-" + uuid.uuid4().hex[:8]
        self.task_dir = self.root / ".wf" / "tasks" / self.task_id
        self.task_dir.mkdir(parents=True)
        self.task = {"id": self.task_id, "title": "t", "status": "in_progress", "phase": "check",
                     "revision": 1, "check": {"id": "c1", "result": "pass",
                                              "anchor": {"check_anchor": ANCHOR}},
                     "reviews": {"launches": [{"round": 1, "implementation_cli": "dsh",
                                               "slots": [{"slot": "s1"}, {"slot": "s2"}],
                                               "anchor": {"check_id": "c1", "check_anchor": ANCHOR},
                                               "submitted_scope": {"diff": {"paths": ["pkg/a.py"]}},
                                               "readable_scope": {"business_code": ["**"]},
                                               "exclusions": list(COVERED),
                                               "temp_paths": []}],
                                 "imported": []}}
        records.write_json(self.task_dir / "task.json", self.task)

    def tearDown(self):
        self._tmp.cleanup()

    def _ctx(self):
        return SimpleNamespace(root=str(self.root))

    def _delivery(self):
        return {"paths": ["pkg/a.py"],
                "buckets": {"e": ["pkg/a.py"], "f": [], "covered_f": [], "uncovered_f": []}}

    def _materials_dir(self):
        return Path(review.round_dir(self._ctx(), self.task_id, 1)) / "materials"

    def _stage_request_files(self):
        """真实 launch 会把 request.json 写进各槽位目录——夹具同型。"""
        for slot in ("s1", "s2"):
            path = Path(review.slot_dir(self._ctx(), self.task_id, 1, slot)) / "request.json"
            path.parent.mkdir(parents=True, exist_ok=True)
            records.write_json(path, {"task-id": self.task_id, "round": 1})

    def test_first_call_records_manifest_and_second_reuses_it(self):
        with mock.patch.object(review, "_current_anchor", return_value=(ANCHOR, {})), \
                mock.patch.object(review.scope_mod, "delivery_set",
                                  return_value=self._delivery()), \
                mock.patch.object(review, "write_materials",
                                  return_value={"material_paths": 1, "material_problems": []}) as wm:
            first = review.context(self._ctx(), self.task, 1, as_value="pi")
            second = review.context(self._ctx(), self.task, 1, as_value="pi")
        manifest_path = self._materials_dir() / "materials-manifest.json"
        self.assertTrue(manifest_path.is_file())
        manifest = records.load_json(manifest_path)
        self.assertEqual(manifest["protocol"], "wf-materials-v1")
        self.assertEqual(manifest["check_id"], "c1")
        # 首次物化调用 write_materials 一次；续写复用 manifest、不再物化。
        self.assertEqual(wm.call_count, 1)
        self.assertTrue(second["facts"]["resumed"])
        self.assertTrue(second["facts"]["materials_check"]["fixed"])
        self.assertEqual(first["facts"]["materials_check"]["check_id"], "c1")
        # 复用分支携带首轮物化时的 facts（problems 不因复用而失真）。
        self.assertEqual(second["facts"]["material_paths"],
                         first["facts"]["material_paths"])

    def test_resume_facts_carry_launch_scope_and_real_request_path(self):
        self._stage_request_files()
        with mock.patch.object(review, "_current_anchor", return_value=(ANCHOR, {})), \
                mock.patch.object(review.scope_mod, "delivery_set",
                                  return_value=self._delivery()), \
                mock.patch.object(review, "write_materials", return_value={}):
            first = review.context(self._ctx(), self.task, 1, as_value="pi")
            second = review.context(self._ctx(), self.task, 1, as_value="pi")
        for facts in (first["facts"], second["facts"]):
            # 首次与续写共用同一授权事实来源（launch 记录）——N2。
            self.assertEqual(facts["submitted_scope"], {"diff": {"paths": ["pkg/a.py"]}})
            self.assertEqual(facts["readable_scope"], {"business_code": ["**"]})
            self.assertIn(".env", facts["exclusions"])
            self.assertEqual(facts["anchor"], {"check_id": "c1", "check_anchor": ANCHOR})
            # request 路径指向发起写入的槽位目录且文件存在——N1。
            self.assertTrue(os.path.isfile(facts["materials"]["request"]),
                            facts["materials"]["request"])
            self.assertIn(os.sep + "round-1" + os.sep, facts["materials"]["request"])
            self.assertEqual(len(facts["materials"]["request_slots"]), 2)

    def test_resume_binds_request_path_to_declared_reviewer_cli(self):
        self._stage_request_files()
        launch = self.task["reviews"]["launches"][0]
        launch["slots"] = [{"slot": "s1", "reviewer_cli": "pi"}, {"slot": "s2"}]
        records.write_json(self.task_dir / "task.json", self.task)
        with mock.patch.object(review, "_current_anchor", return_value=(ANCHOR, {})), \
                mock.patch.object(review.scope_mod, "delivery_set",
                                  return_value=self._delivery()), \
                mock.patch.object(review, "write_materials", return_value={}):
            result = review.context(self._ctx(), self.task, 1, as_value="pi")
        expected = Path(review.slot_dir(self._ctx(), self.task_id, 1, "s1")) / "request.json"
        self.assertEqual(Path(result["facts"]["materials"]["request"]), expected)

    def test_tampered_material_is_rejected_not_silently_reused(self):
        with mock.patch.object(review, "_current_anchor", return_value=(ANCHOR, {})), \
                mock.patch.object(review.scope_mod, "delivery_set",
                                  return_value=self._delivery()), \
                mock.patch.object(review, "write_materials",
                                  side_effect=lambda *_a, **_kw: (
                                      records.atomic_write(
                                          Path(_a[4]) / "diff.patch", "original\n"),
                                      {})[1]):
            review.context(self._ctx(), self.task, 1, as_value="pi")
        records.atomic_write(self._materials_dir() / "diff.patch", "tampered\n")
        with mock.patch.object(review, "_current_anchor", return_value=(ANCHOR, {})), \
                mock.patch.object(review.scope_mod, "delivery_set",
                                  return_value=self._delivery()):
            with self.assertRaises(review.ReviewError) as caught:
                review.context(self._ctx(), self.task, 1, as_value="pi")
        self.assertEqual(caught.exception.code, "WF_REVIEW_INVALID")
        drift = caught.exception.facts["drift"]
        self.assertEqual(drift[0]["file"], "diff.patch")
        self.assertEqual(drift[0]["reason"], "digest mismatch")

    def test_adopted_round_can_be_contexted_again(self):
        """采纳过的轮次再取材料不得崩，且不重写字节 / 不换被审 check_id 与采纳时间。"""
        with mock.patch.object(review, "_current_anchor", return_value=(ANCHOR, {})), \
                mock.patch.object(review.scope_mod, "delivery_set",
                                  return_value=self._delivery()), \
                mock.patch.object(review, "write_materials",
                                  side_effect=_complete_materials("read\n")):
            review.context(self._ctx(), self.task, 1, as_value="pi")
        manifest_path = self._materials_dir() / "materials-manifest.json"
        manifest_path.unlink()                        # 身份丢失（官方采纳出口）
        with mock.patch.object(review, "_current_anchor", return_value=(ANCHOR, {})), \
                mock.patch.object(review.scope_mod, "delivery_set",
                                  return_value=self._delivery()), \
                mock.patch.object(review, "write_materials", return_value={}):
            first = review.context(self._ctx(), self.task, 1, as_value="pi")
        self.assertIn("legacy_materials", str(first["facts"]))
        adopted = records.load_json(manifest_path)
        # 再取一次（压缩重入 / --reset 前）：走 legacy_adopted 分支，必须还能读完
        with mock.patch.object(review, "_current_anchor", return_value=(ANCHOR, {})), \
                mock.patch.object(review.scope_mod, "delivery_set",
                                  return_value=self._delivery()), \
                mock.patch.object(review, "write_materials", return_value={}) as wm:
            second = review.context(self._ctx(), self.task, 1, as_value="pi")
        self.assertEqual(wm.call_count, 0)
        self.assertEqual((self._materials_dir() / "diff.patch").read_text(), "read\n")
        again = records.load_json(manifest_path)
        self.assertEqual(again["check_id"], adopted["check_id"])
        self.assertEqual((again["facts"] or {})["adopted_at"],
                         (adopted["facts"] or {})["adopted_at"])
        self.assertTrue(second["facts"]["legacy_materials"])

    def test_manifest_keys_use_posix_separator(self):
        records.atomic_write(self._materials_dir() / "check-logs" / "a.log", "x\n")
        review.write_materials_manifest(self._materials_dir(), "c1", ANCHOR, {})
        manifest = records.load_json(self._materials_dir() / "materials-manifest.json")
        self.assertIn("check-logs/a.log", manifest["files"])
        self.assertEqual(review.verify_materials_manifest(manifest, self._materials_dir()), [])

    def test_manifest_with_foreign_separator_still_verifies(self):
        """两侧都归一：另一平台写出的反斜杠键在本机不能变成恒 drift。

        Linux 上 `os.sep` 就是 `/`，只断"当前平台结果"拦不住归一被删，所以这里手工
        造一份 Windows 形态的 manifest（键用反斜杠、摘要正确）。
        """
        path = self._materials_dir() / "check-logs" / "a.log"
        records.atomic_write(path, "x\n")
        digest = records.file_digest(path)
        review.write_materials_manifest(self._materials_dir(), "c1", ANCHOR,
                                        {"files": {"check-logs\\a.log": digest}})
        manifest = records.load_json(self._materials_dir() / "materials-manifest.json")
        manifest["files"] = {"check-logs\\a.log": digest}
        self.assertEqual(review.verify_materials_manifest(manifest, self._materials_dir()), [])

    def test_backslash_in_filename_survives_verify(self):
        """Linux 上文件名可以真的含反斜杠（verification id 就是 `v\\1`）：键不能被归一掉。"""
        name = "check-logs/v\\1.log"
        records.atomic_write(self._materials_dir() / "check-logs" / "v\\1.log", "x\n")
        review.write_materials_manifest(self._materials_dir(), "c1", ANCHOR, {})
        manifest = records.load_json(self._materials_dir() / "materials-manifest.json")
        self.assertIn(name, manifest["files"])          # 写入侧不归一真名
        self.assertEqual(review.verify_materials_manifest(manifest, self._materials_dir()), [])

    def test_same_anchor_new_check_id_keeps_first_materials(self):
        """同内容重验（同锚点换 check_id）：旧轮续写读首轮材料，facts 标注两个 id。"""
        with mock.patch.object(review, "_current_anchor", return_value=(ANCHOR, {})), \
                mock.patch.object(review.scope_mod, "delivery_set",
                                  return_value=self._delivery()), \
                mock.patch.object(review, "write_materials",
                                  side_effect=lambda *_a, **_kw: (
                                      records.atomic_write(
                                          Path(_a[4]) / "check.json", '{"old": true}\n'),
                                      {})[1]):
            review.context(self._ctx(), self.task, 1, as_value="pi")
        # 同锚点重跑 Check：check.json 换成新 Check 的内容、id 变 c2（锚点不变）。
        self.task["check"]["id"] = "c2"
        records.write_json(self.task_dir / "task.json", self.task)
        with mock.patch.object(review, "_current_anchor", return_value=(ANCHOR, {})), \
                mock.patch.object(review.scope_mod, "delivery_set",
                                  return_value=self._delivery()), \
                mock.patch.object(review, "write_materials") as wm:
            second = review.context(self._ctx(), self.task, 1, as_value="pi")
        self.assertEqual(wm.call_count, 0)                       # 不按新 Check 重写
        self.assertEqual(json.loads((self._materials_dir() / "check.json").read_text()),
                         {"old": True})
        self.assertEqual(second["facts"]["materials_check"]["check_id"], "c1")
        self.assertEqual(second["facts"]["materials_check"]["current_check_id"], "c2")
        self.assertTrue(second["facts"]["materials_check"]["fixed"])

    def test_corrupted_manifest_adopts_existing_bytes(self):
        with mock.patch.object(review, "_current_anchor", return_value=(ANCHOR, {})), \
                mock.patch.object(review.scope_mod, "delivery_set",
                                  return_value=self._delivery()), \
                mock.patch.object(review, "write_materials",
                                  side_effect=_complete_materials("reviewer-read\n")):
            review.context(self._ctx(), self.task, 1, as_value="pi")
        (self._materials_dir() / "materials-manifest.json").write_text("{broken", encoding="utf-8")
        with mock.patch.object(review, "_current_anchor", return_value=(ANCHOR, {})), \
                mock.patch.object(review.scope_mod, "delivery_set",
                                  return_value=self._delivery()), \
                mock.patch.object(review, "write_materials", return_value={}) as wm:
            result = review.context(self._ctx(), self.task, 1, as_value="pi")
        # 身份记录丢失但材料还在：按现场字节采纳（reviewer 读过的内容不重写）
        self.assertEqual(wm.call_count, 0)                       # 采纳，不重物化
        self.assertTrue(result["facts"]["legacy_materials"])
        self.assertEqual(result["facts"]["materials_check"]["check_id"], "c1")
        manifest = records.load_json(self._materials_dir() / "materials-manifest.json")
        self.assertTrue(manifest["facts"]["legacy_materials"])

    def test_legacy_round_keeps_existing_material_bytes(self):
        """第二次调用（manifest 已被删）不得覆盖已有 diff：采纳而非重物化。"""
        with mock.patch.object(review, "_current_anchor", return_value=(ANCHOR, {})), \
                mock.patch.object(review.scope_mod, "delivery_set",
                                  return_value=self._delivery()), \
                mock.patch.object(review, "write_materials",
                                  side_effect=_complete_materials("reviewer-read\n")):
            review.context(self._ctx(), self.task, 1, as_value="pi")
        (self._materials_dir() / "materials-manifest.json").unlink()
        with mock.patch.object(review, "_current_anchor", return_value=(ANCHOR, {})), \
                mock.patch.object(review.scope_mod, "delivery_set",
                                  return_value=self._delivery()), \
                mock.patch.object(review, "write_materials") as wm:
            review.context(self._ctx(), self.task, 1, as_value="pi")
        self.assertEqual(wm.call_count, 0)
        self.assertEqual((self._materials_dir() / "diff.patch").read_text(), "reviewer-read\n")


if __name__ == "__main__":
    unittest.main()
