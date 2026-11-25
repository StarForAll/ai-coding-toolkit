"""轮次材料是一个可核身份：报告绑定它读到的那批字节。

真失败（2026-11-24 复核 F1）：报告与材料身份毫无绑定——导入只记锚点与报告摘要，判定却读当前
manifest 并把它写进结论。于是"清掉材料再同轮重物化"之后，旧报告仍过锚点校验，结论却记成新
manifest；首轮物化中断留下的半包还会被当成 `legacy` 采纳。

断言：
1. 身份只覆盖 check_id + 文件摘要（时间戳变不算变，内容变才算）；
2. 骨架携带身份；给了就必须等于当前身份，缺字段只记 unbound、不阻断；
3. 导入登记身份、`--restore` 保留原身份；
4. 材料被改 → 导入先拒（drift），登记过身份的报告在判定侧被标 `materials_stale`；
5. 结论记的是绑定身份，不是当前身份。
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

ANCHOR = "sha256:" + "b" * 64
MARKER = review.REPORT_MARKER
COVERED = ["node_modules/**", ".env", "*.pem", ".codex/**", "../**", ".wf/tasks/**"]
AXES = {name: "pass" for name in review.REVIEW_AXES}


class Ctx:
    def __init__(self, root):
        self.root = str(root)

    def require_held(self, task=None):
        return {"id": "sess-test"}, {"id": "human:test"}


def body(identity=None, **overrides):
    payload = {"protocol": "wf-review-v1", "task-id": "t1", "round": 1,
               "review-time": "2026-11-24T00:00:00.000000Z", "review-focus": "x",
               "check-anchor": {"check_id": "c1", "check_anchor": ANCHOR},
               "read-scope": ["pkg/**"], "excluded-scope": list(COVERED),
               "axes": dict(AXES), "findings": [], "verdict": "pass"}
    if identity is not None:
        payload["materials"] = {"identity": identity}
    payload.update(overrides)
    return payload


def text_of(payload, status="done"):
    head = f"<!-- wf-review-agent:v1 status={status} -->\n" if status else ""
    return head + MARKER + "\n\n```json\n" + json.dumps(payload, ensure_ascii=False) + "\n```\n"


class IdentityShapeTest(unittest.TestCase):
    def test_identity_ignores_timestamps_but_not_content(self):
        files = {"diff.patch": "sha256:" + "a" * 64}
        first = review.materials_identity({"check_id": "c1", "files": files,
                                           "generated_at": "2026-11-24T00:00:00Z",
                                           "facts": {"legacy_materials": True}})
        second = review.materials_identity({"check_id": "c1", "files": dict(files),
                                            "generated_at": "2026-11-24T09:09:09Z",
                                            "facts": {"adopted_at": "later"}})
        self.assertEqual(first, second, "时间戳/facts 不该改变身份——否则内容一样也要换轮")
        changed = review.materials_identity({"check_id": "c1",
                                             "files": {"diff.patch": "sha256:" + "c" * 64}})
        self.assertNotEqual(first, changed)
        self.assertNotEqual(first, review.materials_identity({"check_id": "c2", "files": files}))

    def test_no_manifest_means_no_identity(self):
        self.assertIsNone(review.materials_identity(None))

    def test_publish_refuses_non_empty_target(self):
        """发布只接受"不存在或空目录"：非空说明状态判断有漏，喊出来而不是混写。"""
        with tempfile.TemporaryDirectory() as tmp:
            staging = Path(tmp) / "materials.staging-x"
            target = Path(tmp) / "materials"
            staging.mkdir()
            target.mkdir()
            (target / "old.patch").write_text("old\n", encoding="utf-8")
            with self.assertRaises(review.ReviewError) as caught:
                review._publish_materials(str(staging), str(target))
            self.assertEqual(caught.exception.code, "WF_PATH_INVALID")

    def test_undecided_rounds_lists_launched_but_undecided(self):
        task = {"reviews": {"launches": [{"round": 1}, {"round": 3}],
                            "rounds": [{"round": 1, "verdict": "fail"}]}}
        self.assertEqual(review.undecided_rounds(task), [3])
        self.assertEqual(review.undecided_rounds({}), [])


class MaterialsBindingHarness(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.ctx = Ctx(self.root)
        self.task_dir = self.root / ".wf" / "tasks" / "t1"
        self.task_dir.mkdir(parents=True)
        # 材料与占位都在暂存根下（`round_dir` = staging_root/round-N），不是在任务目录。
        self.staging = self.root / "staging" / "round-1"
        self.materials = self.staging / "materials"
        self.materials.mkdir(parents=True)
        self.task = {"id": "t1", "title": "t", "status": "in_progress", "phase": "check",
                     "revision": 1, "check": {"id": "c1", "result": "pass",
                                              "anchor": {"check_anchor": ANCHOR}},
                     "entry_snapshot": {"touch_paths": []},
                     "reviews": {"launches": [{"round": 1, "implementation_cli": "dsh",
                                               "slots": [{"slot": "s1"}], "temp_paths": []}],
                                 "imported": []}}
        self.write_task()
        self.identity = self.materialize()

    def tearDown(self):
        self._tmp.cleanup()

    def write_task(self):
        records.write_json(self.task_dir / "task.json", self.task)

    def materialize(self, patch="# patch\n"):
        (self.materials / "diff.patch").write_text(patch, encoding="utf-8")
        (self.materials / "status.json").write_text('{"redacted": true}', encoding="utf-8")
        manifest = review.write_materials_manifest(self.materials, "c1", ANCHOR, {})
        return review.materials_identity(manifest)

    def write(self, payload, name="review-pi.md"):
        path = self.staging / name
        path.write_text(text_of(payload), encoding="utf-8")
        return path

    def staged(self):
        return mock.patch.object(review, "staging_root",
                                 lambda _ctx, _task: str(self.root / "staging"))

    def import_report(self, path, restore=False):
        def _start(_ctx, directory, task, *_args, **_kwargs):
            task = dict(task)
            task["action"] = {"id": "a1", "state": "started"}
            records.write_json(os.path.join(directory, "task.json"), task)
            return task, task["action"]

        with mock.patch.object(review, "_current_anchor", return_value=(ANCHOR, {})), \
                self.staged(), \
                mock.patch.object(tasks_mod, "_start_task_action", _start), \
                mock.patch.object(tasks_mod, "_finish_task_action",
                                  lambda _ctx, _path, task, *_a, **_k: (task, {"ok": True})):
            return review.import_report(self.ctx, {"id": "t1"}, 1, None, str(path),
                                        _from_discovery=True, agent="pi", restore=restore)


class SkeletonTest(MaterialsBindingHarness):
    def test_skeleton_carries_identity_and_real_state(self):
        import argparse
        args = argparse.Namespace(values={}, flags=set())
        del args
        skeleton = review.report_skeleton("t1", 1, {"id": "c1"}, ANCHOR,
                                          materials_identity=self.identity)
        declared = review.parse_report(skeleton)
        self.assertEqual(declared["materials"]["identity"], self.identity)

    def test_input_problems_catch_wrong_and_missing_identity(self):
        good = review.report_input_problems(body(self.identity), launch={},
                                            materials_identity=self.identity)
        self.assertEqual(good["checks"]["materials"], [])
        wrong = review.report_input_problems(body("sha256:" + "d" * 64), launch={},
                                             materials_identity=self.identity)
        problems = wrong["checks"]["materials"]
        self.assertTrue(any(item.get("current") == self.identity for item in problems))
        # 声明了身份但本轮没有材料：不能再拿它作证
        gone = review.report_input_problems(body(self.identity), launch={},
                                            materials_identity=None)
        self.assertTrue(gone["checks"]["materials"])
        # 老报告没有该字段：不阻断
        legacy = review.report_input_problems(body(), launch={},
                                              materials_identity=self.identity)
        self.assertEqual(legacy["checks"].get("materials", []), [])


class ImportBindingTest(MaterialsBindingHarness):
    def test_import_records_identity(self):
        result = self.import_report(self.write(body(self.identity)))
        self.assertEqual(result["code"], "WF_OK")
        entry = records.load_json(self.task_dir / "task.json")["reviews"]["imported"][0]
        self.assertEqual(entry["materials"]["identity"], self.identity)
        self.assertFalse(entry["materials"].get("unbound"))

    def test_import_refuses_mismatched_identity(self):
        path = self.write(body("sha256:" + "d" * 64))
        with self.assertRaises(review.ReviewError) as caught:
            self.import_report(path)
        self.assertEqual(caught.exception.code, "WF_REVIEW_INVALID")
        self.assertIn("materials", {item.get("check")
                                    for item in caught.exception.facts["problems"]})

    def test_import_refuses_drifted_materials(self):
        (self.materials / "diff.patch").write_text("# changed\n", encoding="utf-8")
        with self.assertRaises(review.ReviewError) as caught:
            self.import_report(self.write(body(self.identity)))
        self.assertEqual(caught.exception.code, "WF_REVIEW_INVALID")
        self.assertIn("drift", caught.exception.facts)

    def test_import_without_identity_is_refused(self):
        """入口能预填就是必填：漏填是新报告的缺口，不能冒充旧版本兼容。"""
        with self.assertRaises(review.ReviewError) as caught:
            self.import_report(self.write(body()))
        self.assertIn("materials", {item.get("check")
                                    for item in caught.exception.facts["problems"]})

    def test_restore_of_legacy_entry_is_recorded_unbound(self):
        """旧记录本来就没有身份：restore 放行，登记按现场记并标 unbound（判定会说明强度）。"""
        self.task["reviews"]["imported"] = [
            {"round": 1, "slot": "s1", "agent": "pi",
             "report_path": ".wf/tasks/t1/review/round-1/review-pi.md",
             "anchor": {"check_id": "c1", "check_anchor": ANCHOR}}]
        self.write_task()
        target = self.task_dir / "review" / "round-1" / "review-pi.md"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text_of(body()), encoding="utf-8")
        self.import_report(self.write(body()), restore=True)
        entry = records.load_json(self.task_dir / "task.json")["reviews"]["imported"][0]
        self.assertTrue(entry["materials"].get("unbound"))
        self.assertEqual(entry["materials"]["identity"], self.identity)

    def test_restore_keeps_recorded_identity(self):
        # 旧记录：有身份但没有登记摘要（restore 的唯一入口面）
        self.task["reviews"]["imported"] = [
            {"round": 1, "slot": "s1", "agent": "pi",
             "report_path": ".wf/tasks/t1/review/round-1/review-pi.md",
             "anchor": {"check_id": "c1", "check_anchor": ANCHOR},
             "materials": {"identity": self.identity}}]
        self.write_task()
        target = self.task_dir / "review" / "round-1" / "review-pi.md"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            text_of(body(self.identity, findings=[{"id": "f0", "severity": "suggestion"}])),
            encoding="utf-8")
        # 材料被重出成新身份 B：restore 导入的是一份按 B 写的报告，
        # 但登记的身份必须还是旧报告读到的那份 A。
        (self.materials / "diff.patch").write_text("# rewritten\n", encoding="utf-8")
        os.remove(self.materials / review.MANIFEST_NAME)
        new_identity = review.materials_identity(
            review.write_materials_manifest(self.materials, "c1", ANCHOR, {}))
        self.assertNotEqual(new_identity, self.identity)
        target.unlink()          # restore 的真实场景：原文件已丢，bytes 与来件不同才需要显式放行
        # 报告仍是当初那份（材料值 = 旧身份 A），当前材料已经是 B：restore 按记录还原，不被它否掉
        result = self.import_report(self.write(body(self.identity)), restore=True)
        self.assertEqual(result["code"], "WF_OK")
        entry = records.load_json(self.task_dir / "task.json")["reviews"]["imported"][0]
        self.assertEqual(entry["materials"]["identity"], self.identity,
                         "restore 还原的是原身份，不拿当前材料替旧报告作证")


class DecideCheckTest(MaterialsBindingHarness):
    def _imported(self, identity):
        return [{"round": 1, "slot": "s1", "agent": "pi",
                 "report_path": ".wf/tasks/t1/review/round-1/review-pi.md",
                 "anchor": {"check_id": "c1", "check_anchor": ANCHOR},
                 "materials": {"identity": identity}}]

    def test_bound_report_is_marked_stale_after_material_change(self):
        path = self.write(body(self.identity))
        target = self.task_dir / "review" / "round-1" / "review-pi.md"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(path.read_text(encoding="utf-8"), encoding="utf-8")
        digest = records.file_digest_state(str(target))[0]
        entry = self._imported(self.identity)[0]
        entry["report_digest"] = digest
        launch = {"slots": [{"slot": "s1"}]}
        with self.staged():
            ok = review.review_report_problems(self.ctx, self.task, round_no=1, launch=launch,
                                               imported=[entry], anchor=ANCHOR)
        self.assertNotIn("materials_stale", ok["blockers"])

        # 材料被重出（内容变化、生成新的 manifest）：报告读的那批字节已不可还原
        (self.materials / "diff.patch").write_text("# changed\n", encoding="utf-8")
        os.remove(self.materials / review.MANIFEST_NAME)
        review.write_materials_manifest(self.materials, "c1", ANCHOR, {})
        with self.staged():
            after = review.review_report_problems(self.ctx, self.task, round_no=1, launch=launch,
                                                  imported=[entry], anchor=ANCHOR)
        self.assertIn("materials_stale", after["blockers"])

    def test_restored_entry_passes_through_material_change(self):
        """restored 条目的身份取记录：现场不同只作事实，不当阻断项。"""
        path = self.write(body(self.identity))
        target = self.task_dir / "review" / "round-1" / "review-pi.md"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(path.read_text(encoding="utf-8"), encoding="utf-8")
        digest = records.file_digest_state(str(target))[0]
        entry = self._imported("sha256:" + "a" * 64)[0]
        entry["report_digest"] = digest
        entry["materials"] = {"identity": "sha256:" + "a" * 64, "restored": True}
        with self.staged():
            result = review.review_report_problems(self.ctx, self.task, round_no=1,
                                                   launch={"slots": [{"slot": "s1"}]},
                                                   imported=[entry], anchor=ANCHOR)
        self.assertNotIn("materials_stale", result["blockers"])

    def test_same_content_rematerialization_still_matches(self):
        path = self.write(body(self.identity))
        target = self.task_dir / "review" / "round-1" / "review-pi.md"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(path.read_text(encoding="utf-8"), encoding="utf-8")
        digest = records.file_digest_state(str(target))[0]
        entry = self._imported(self.identity)[0]
        entry["report_digest"] = digest
        os.remove(self.materials / review.MANIFEST_NAME)
        again = review.write_materials_manifest(self.materials, "c1", ANCHOR, {})
        self.assertEqual(review.materials_identity(again), self.identity)
        with self.staged():
            result = review.review_report_problems(self.ctx, self.task, round_no=1,
                                                   launch={"slots": [{"slot": "s1"}]},
                                                   imported=[entry], anchor=ANCHOR)
        self.assertNotIn("materials_stale", result["blockers"])


class StatusAnchorTest(MaterialsBindingHarness):
    def test_same_anchor_new_check_id_is_not_stale(self):
        """状态页与导入/判定同一判据：同锚点换 check_id 是同内容重验，报告仍然有效。"""
        path = self.write(body(self.identity))
        target = self.task_dir / "review" / "round-1" / "review-pi.md"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(path.read_text(encoding="utf-8"), encoding="utf-8")
        digest, _cause, _reason = records.file_digest_state(str(target))
        self.task["check"]["id"] = "c2"          # Check 重跑：新 id、同锚点
        self.task["reviews"]["imported"] = [
            {"round": 1, "slot": "s1", "agent": "pi",
             "report_path": ".wf/tasks/t1/review/round-1/review-pi.md",
             "report_digest": digest,
             "anchor": {"check_id": "c1", "check_anchor": ANCHOR},
             "materials": {"identity": self.identity}}]
        self.write_task()
        with self.staged(), mock.patch.object(review, "_current_anchor", return_value=(ANCHOR, {})):
            status = review.status_of_round(self.ctx, self.task, 1)
        slot = status["slots"][0]
        self.assertEqual(slot["state"], "imported")
        self.assertIn("s1", status["arrived_slots"])


    def test_mixed_round_blocks_and_says_why(self):
        """还原条目 + 对不上当前材料的正常条目：verdict 会声称覆盖同一面却两套证据基。"""
        path = self.write(body(self.identity))
        target = self.task_dir / "review" / "round-1" / "review-pi.md"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(path.read_text(encoding="utf-8"), encoding="utf-8")
        digest = records.file_digest_state(str(target))[0]
        restored = {"slot": "s1", "report_digest": digest,
                    "report_path": ".wf/tasks/t1/review/round-1/review-pi.md",
                    "anchor": {"check_id": "c1", "check_anchor": ANCHOR},
                    "materials": {"identity": "sha256:" + "a" * 64, "restored": True}}
        live = {"slot": "s2", "report_digest": digest,
                "report_path": ".wf/tasks/t1/review/round-1/review-pi.md",
                "anchor": {"check_id": "c1", "check_anchor": ANCHOR},
                "materials": {"identity": "sha256:" + "b" * 64}}
        with self.staged():
            result = review.review_report_problems(self.ctx, self.task, round_no=1,
                                                   launch={"slots": [{"slot": "s1"}, {"slot": "s2"}]},
                                                   imported=[restored, live], anchor=ANCHOR)
        self.assertIn("materials_stale", result["blockers"])
        reasons = [item.get("reason") for item in result["problems"]]
        self.assertTrue(any("mixes restored" in str(reason) for reason in reasons), reasons)

    def test_restored_entry_reports_its_own_cause(self):
        """restore 故意保留旧身份：状态页要能与"材料真被换了"分开报。"""
        path = self.write(body(self.identity))
        target = self.task_dir / "review" / "round-1" / "review-pi.md"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(path.read_text(encoding="utf-8"), encoding="utf-8")
        digest, _cause, _reason = records.file_digest_state(str(target))
        self.task["reviews"]["imported"] = [
            {"round": 1, "slot": "s1", "agent": "pi",
             "report_path": ".wf/tasks/t1/review/round-1/review-pi.md",
             "report_digest": digest,
             "anchor": {"check_id": "c1", "check_anchor": ANCHOR},
             "materials": {"identity": "sha256:" + "a" * 64, "restored": True}}]
        self.write_task()
        with self.staged(), mock.patch.object(review, "_current_anchor", return_value=(ANCHOR, {})):
            status = review.status_of_round(self.ctx, self.task, 1)
        slot = status["slots"][0]
        self.assertEqual(slot["state"], "stale")
        self.assertEqual(slot["stale_cause"], "restored-historical")

    def test_mixed_round_slot_hint_matches_round_exit(self):
        """二轮 N-2 回归锁：混合轮的 restored 槽位提示不得再说"可直接判定"——
        它必须与轮级 next_（cli.py 的 round_materials_basis 分支）指向同一处置。"""
        self.task["reviews"]["launches"][0]["slots"] = [{"slot": "s1"}, {"slot": "s2"}]
        path = self.write(body(self.identity))
        target = self.task_dir / "review" / "round-1" / "review-pi.md"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(path.read_text(encoding="utf-8"), encoding="utf-8")
        digest = records.file_digest_state(str(target))[0]
        self.task["reviews"]["imported"] = [
            {"round": 1, "slot": "s1", "agent": "pi",
             "report_path": ".wf/tasks/t1/review/round-1/review-pi.md",
             "report_digest": digest,
             "anchor": {"check_id": "c1", "check_anchor": ANCHOR},
             "materials": {"identity": "sha256:" + "a" * 64, "restored": True}},
            {"round": 1, "slot": "s2", "agent": "codex",
             "report_path": ".wf/tasks/t1/review/round-1/review-pi.md",
             "report_digest": digest,
             "anchor": {"check_id": "c1", "check_anchor": ANCHOR},
             "materials": {"identity": "sha256:" + "b" * 64}}]
        self.write_task()
        with self.staged(), mock.patch.object(review, "_current_anchor", return_value=(ANCHOR, {})):
            status = review.status_of_round(self.ctx, self.task, 1)
        restored_slot = next(slot for slot in status["slots"] if slot["slot"] == "s1")
        self.assertEqual(restored_slot["stale_cause"], "restored-historical")
        self.assertIn("混合基线", restored_slot["reason"])
        self.assertNotIn("可直接判定", restored_slot["reason"])


if __name__ == "__main__":
    unittest.main()
