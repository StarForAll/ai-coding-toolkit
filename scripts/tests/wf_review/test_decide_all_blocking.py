"""P1-3（2026-11-24）：pass 判定的任务级校验——全部轮次已知 blocking 须已关闭。

防的失败（dogfood 八轮审查 + 独立审查 N6）：
- decide 只拦**本轮** open blocking，旧轮 fail 报告的未处置项被 pass 覆盖，
  归档门禁再拦收工——"判定可 pass、finish 被拦"的打架让 AI 在提示间空转；
- 本次 --plan 一并给出的处置应计入（同一次判定闭合，不要求二次提交）。
"""

import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "docs" / "workflows" / "wf" / "payload" / "lib"))

from wflib import records, review, tasks as tasks_mod  # noqa: E402

ANCHOR = "sha256:" + "c" * 64
MARKER = review.REPORT_MARKER
COVERED = ["node_modules/**", ".env", "*.pem", ".codex/**", "../**", ".wf/tasks/**"]
PASS_AXES = {name: "pass" for name in review.REVIEW_AXES}
FAIL_AXES = dict(PASS_AXES, scope="fail")


class Ctx:
    def __init__(self, root):
        self.root = str(root)

    def key(self):
        return "sess-test"

    def rule_version(self):
        return "test-rule"

    def require_held(self, task=None):
        return {"id": "sess-test"}, {"id": "human:test"}


def report_text(round_no, agent, axes, findings=(), materials_identity=None):
    body = {"protocol": "wf-review-v1", "task-id": "t1", "round": round_no,
            "review-time": "2026-11-24T00:00:00.000000Z", "review-focus": "x",
            "check-anchor": {"check_id": f"c{round_no}", "check_anchor": ANCHOR},
            "read-scope": ["pkg/**"], "excluded-scope": list(COVERED),
            "axes": dict(axes), "findings": list(findings),
            "verdict": "fail" if findings else "pass"}
    if materials_identity:
        body["materials"] = {"identity": materials_identity}
    return ("<!-- wf-review-agent:v1 status=done -->\n" + MARKER
            + "\n\n```json\n" + json.dumps(body, ensure_ascii=False) + "\n```\n")


class DecideAllBlockingTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.ctx = Ctx(self.root)
        self.task_dir = self.root / ".wf" / "tasks" / "t1"
        self.task_dir.mkdir(parents=True)
        self.setUp_materials_clean()

    def tearDown(self):
        self._tmp.cleanup()

    def _materials_dir(self):
        return Path(review.round_dir(self.ctx, "t1", 2)) / "materials"

    def setUp_materials_clean(self):
        """staging 是全局 `/tmp/wf-review/<project>/t1`：不清就跑，前一条测试留下的
        被改材料会被当成"已物化"，单跑绿、连跑红。"""
        shutil.rmtree(self._materials_dir(), ignore_errors=True)

    def _stage(self):
        """第 1 轮 fail（blocking f1 未处置）→ 第 2 轮 pass。真实两轮记录形状。"""
        imported = []
        # 第 1 轮：s1 报 blocking f1。
        rel1 = ".wf/tasks/t1/review/round-1/review-pi.md"
        path1 = self.root / rel1
        path1.parent.mkdir(parents=True, exist_ok=True)
        path1.write_text(report_text(
            1, "pi", FAIL_AXES,
            [{"id": "f1", "severity": "blocking", "statement": "验收缺口",
              "assertion_ref": "a:1"}]), encoding="utf-8")
        imported.append({"round": 1, "slot": "s1", "agent": "pi", "report_path": rel1,
                         "report_digest": records.file_digest(path1),
                         "anchor": {"check_anchor": ANCHOR}})
        # 第 2 轮：两份 pass 报告。
        for slot, agent in (("s1", "pi"), ("s2", "zcode")):
            rel = f".wf/tasks/t1/review/round-2/review-{agent}.md"
            path = self.root / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(report_text(2, agent, PASS_AXES), encoding="utf-8")
            imported.append({"round": 2, "slot": slot, "agent": agent, "report_path": rel,
                             "report_digest": records.file_digest(path),
                             "anchor": {"check_anchor": ANCHOR}})
        records.write_json(self.task_dir / "task.json", {
            "id": "t1", "title": "t", "status": "in_progress", "phase": "check", "revision": 1,
            "check": {"id": "c2", "result": "pass",
                      "anchor": {"check_anchor": ANCHOR, "parts": {}},
                      "commands": [{"verification_id": "v1", "status": "passed"}]},
            "entry_snapshot": {"touch_paths": []},
            "plan": {"complexity": "complex", "acceptance": [{"id": "a:1"}],
                     "verifications": [{"id": "v1"}]},
            "reviews": {
                "launches": [{"round": 1, "implementation_cli": "dsh",
                              "slots": [{"slot": "s1"}, {"slot": "s2"}], "temp_paths": []},
                             {"round": 2, "implementation_cli": "dsh",
                              "slots": [{"slot": "s1"}, {"slot": "s2"}], "temp_paths": []}],
                "rounds": [{"round": 1, "verdict": "fail",
                            "check_id": "c1", "decided_at": "2026-11-24T00:00:00.000000Z"}],
                "imported": imported,
                "main_reviews": [
                    {"round": 1, "file_digest": "sha256:" + "1" * 64,
                     "axes": {axis: {"conclusion": ("fail" if axis == "scope" else "pass"),
                                     "basis": "旧轮复核", "sources": ["s1"], "finding_refs":
                                     (["f1"] if axis == "scope" else [])}
                              for axis in review.REVIEW_AXES},
                     "main_findings": [],
                     "report_review": [{"slot": "s1", "reliance": "primary", "notes": "x"}],
                     "finding_review": [{"finding_id": "f1", "slot": "s1", "check": "verified",
                                         "basis": "本地核实成立"}]},
                ],
            }})

    def _main_review_round2(self):
        payload = {
            "task": "t1", "round": 2,
            "axes": {axis: {"conclusion": "pass", "basis": "本轮复核依据",
                            "sources": ["main"], "finding_refs": []}
                     for axis in review.REVIEW_AXES},
            "report_review": [{"slot": "s1", "reliance": "primary", "notes": "x"},
                              {"slot": "s2", "reliance": "primary", "notes": "x"}],
            "finding_review": [],
        }
        path = self.root / "main-review.json"
        path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        return str(path)

    def _plan_file(self, plan):
        path = self.root / "plan.json"
        path.write_text(json.dumps(plan, ensure_ascii=False), encoding="utf-8")
        return str(path)

    def _decide(self, plan=None):
        def _start(_ctx, path, task, *_a, **_kw):
            task = dict(task)
            task["action"] = {"id": "a1", "state": "started"}
            records.write_json(os.path.join(path, "task.json"), task)
            return task, task["action"]

        def _finish(_ctx, path, task, *_a, **_kw):
            records.write_json(os.path.join(path, "task.json"), task)
            return task, {"ok": True}

        with mock.patch.object(review, "_current_anchor", return_value=(ANCHOR, {})), \
                mock.patch.object(review, "standard_drift_gate", return_value=[]), \
                mock.patch.object(tasks_mod, "_start_task_action", _start), \
                mock.patch.object(tasks_mod, "_finish_task_action", _finish), \
                mock.patch("wflib.gates.check_validity",
                           return_value={"valid": True, "code": None, "facts": {},
                                         "blockers": []}), \
                mock.patch("wflib.tasks._is_approved_plan", return_value=True):
            return review.decide(self.ctx, {"id": "t1"}, 2, plan_path=plan,
                                 main_review_path=self._main_review_round2())

    def test_pass_is_rejected_while_an_earlier_blocking_stays_open(self):
        self._stage()
        with self.assertRaises(review.ReviewError) as caught:
            self._decide()
        self.assertEqual(caught.exception.code, "WF_REVIEW_INVALID")
        open_items = caught.exception.facts["open_blocking"]
        self.assertEqual([(item["round"], item["finding_id"]) for item in open_items],
                         [(1, "f1")])
        # 判定未落地：result 不写 pass。
        task = records.load_json(self.task_dir / "task.json")
        self.assertNotEqual((task.get("reviews") or {}).get("result", {}).get("verdict"), "pass")

    def _stage_materials(self, tamper=False):
        """物化第 2 轮材料 + manifest；tamper 时改动物化后的字节。"""
        materials = self._materials_dir()
        shutil.rmtree(materials, ignore_errors=True)
        materials.mkdir(parents=True, exist_ok=True)
        (materials / "diff.patch").write_text("original\n", encoding="utf-8")
        (materials / "check.json").write_text("{}\n", encoding="utf-8")
        manifest = review.write_materials_manifest(materials, "c2", ANCHOR, {})
        if tamper:
            (materials / "diff.patch").write_text("tampered\n", encoding="utf-8")
        # 报告与材料绑定（真实轮次都有）：后面才有"材料被改 ⇒ 结论失效"可言。
        task = records.load_json(self.task_dir / "task.json")
        for entry in task["reviews"]["imported"]:
            if int(entry.get("round") or 0) == 2:
                entry["materials"] = {"identity": review.materials_identity(manifest)}
        records.write_json(self.task_dir / "task.json", task)
        return materials

    def test_drifted_materials_block_verdict(self):
        """P1：材料物化后被改 —— 判定必须拒，不能只把 manifest 摘要抄进结果。"""
        self._stage()
        self._stage_materials(tamper=True)
        with self.assertRaises(review.ReviewError) as caught:
            self._decide()
        self.assertEqual(caught.exception.code, "WF_REVIEW_INVALID")
        self.assertEqual(caught.exception.facts["drift"][0]["file"], "diff.patch")
        task = records.load_json(self.task_dir / "task.json")
        self.assertNotIn("result", task.get("reviews") or {})

    def test_restored_round_tolerates_drifted_materials(self):
        """restore 还原的是历史记录：现场材料漂移时仍可判，身份按记录、漂移只作事实。"""
        self._stage()
        self._stage_materials(tamper=True)
        task = records.load_json(self.task_dir / "task.json")
        identity = review.materials_identity(
            review.load_materials_manifest(str(self._materials_dir())))
        for entry in task["reviews"]["imported"]:
            if int(entry.get("round") or 0) == 2:
                entry["materials"] = {"identity": identity, "restored": True}
        records.write_json(self.task_dir / "task.json", task)
        plan = {"finding_id": "f1", "decision": "accepted", "round": 1, "slot": "s1",
                "recheck_by": "zcode", "at": "2026-11-24T00:00:00.000000Z",
                "evidence_refs": ["v:v1"], "reason": "已修复"}
        result = self._decide(plan=self._plan_file([plan]))
        self.assertEqual(result["facts"]["result"]["materials"]["state"], "drift")
        self.assertEqual(result["facts"]["result"]["verdict"], "pass")
        self.assertIn("materials_note", result["facts"]["result"]["facts"])

    def test_restored_round_judges_even_after_rematerialized_materials(self):
        """还原记录的身份来自记录本身：报告自报旧身份也照样能判（不能被输入校验再挡一次）。"""
        self._stage()
        old_identity = "sha256:" + "a" * 64
        for agent in ("pi", "zcode"):
            path = self.task_dir / f"review/round-2/review-{agent}.md"
            path.write_text(report_text(2, agent, PASS_AXES,
                                        materials_identity=old_identity), encoding="utf-8")
        self._stage_materials()
        task = records.load_json(self.task_dir / "task.json")
        for entry in task["reviews"]["imported"]:
            if int(entry.get("round") or 0) == 2:
                entry["materials"] = {"identity": old_identity, "restored": True}
                # 报告被重写：摘要按当前字节更新，否则先撞"文件已变"
                entry["report_digest"] = records.file_digest(
                    self.task_dir / entry["report_path"].replace(".wf/tasks/t1/", ""))
        records.write_json(self.task_dir / "task.json", task)
        plan = {"finding_id": "f1", "decision": "accepted", "round": 1, "slot": "s1",
                "recheck_by": "zcode", "at": "2026-11-24T00:00:00.000000Z",
                "evidence_refs": ["v:v1"], "reason": "已修复"}
        result = self._decide(plan=self._plan_file([plan]))
        self.assertEqual(result["facts"]["result"]["verdict"], "pass")
        self.assertNotIn("materials_stale", json.dumps(result["facts"]["result"]))

    def test_verdict_records_material_state(self):
        """身份强度如实上报，且结论记的是**报告绑定**的材料身份（不是当前材料冒充）。"""
        self._stage()
        self._stage_materials()
        plan = {"finding_id": "f1", "decision": "accepted", "round": 1, "slot": "s1",
                "recheck_by": "zcode", "at": "2026-11-24T00:00:00.000000Z",
                "evidence_refs": ["v:v1"], "reason": "已修复"}
        result = self._decide(plan=self._plan_file([plan]))
        identity = result["facts"]["result"]["materials"]
        self.assertEqual(identity["state"], "fixed")
        current = review.round_materials_identity(review.__dict__["_ctx"] if False else
                                                  self.ctx, {"id": "t1"}, 2)
        self.assertEqual(identity["identity"], current)
        self.assertNotIn("current", identity)

    def test_adopted_materials_stay_weak_after_rematerialized_manifest(self):
        """删 manifest 重取（官方恢复出口）之后，弱身份必须一直保留，不能升格成 fixed。"""
        from unittest import mock

        self._stage()
        materials = self._stage_materials()
        # 采纳后的状态（"删 manifest → 重取"就走成这样）：manifest 只有自采纳后的摘要
        manifest = records.load_json(materials / "materials-manifest.json")
        manifest["facts"] = {"legacy_materials": True, "adopted_files": ["diff.patch"],
                             "adopted_at": "2026-11-24T00:00:00.000000Z"}
        records.write_json(materials / "materials-manifest.json", manifest)
        self.assertEqual(review.materials_identity_state(self.ctx, "t1", 2)["state"],
                         "legacy_adopted")
        plan = {"finding_id": "f1", "decision": "accepted", "round": 1, "slot": "s1",
                "recheck_by": "zcode", "at": "2026-11-24T00:00:00.000000Z",
                "evidence_refs": ["v:v1"], "reason": "已修复"}
        result = self._decide(plan=self._plan_file([plan]))
        self.assertEqual(result["facts"]["result"]["materials"]["state"], "legacy_adopted")
        self.assertEqual(result["facts"]["result"]["facts"]["materials_state"],
                         "legacy_adopted")
        # 再次判定仍报弱身份（不会因为写了 manifest 就升格）
        again = self._decide(plan=self._plan_file([plan]))
        self.assertEqual(again["facts"]["result"]["materials"]["state"], "legacy_adopted")

    def test_new_material_file_counts_as_drift(self):
        """物化后新增的文件不属于 reviewer 读到的那一版。"""
        self._stage()
        materials = self._stage_materials()
        (materials / "extra-notes.md").write_text("x\n", encoding="utf-8")
        with self.assertRaises(review.ReviewError) as caught:
            self._decide()
        self.assertEqual(caught.exception.facts["drift"][0]["reason"], "not in manifest")

    def test_legacy_materials_pass_with_weak_identity_fact(self):
        """manifest 丢失但材料在：采纳现场字节继续，结果明确标 legacy。"""
        self._stage()
        materials = self._stage_materials()
        (materials / "materials-manifest.json").unlink()
        plan = {"finding_id": "f1", "decision": "accepted", "round": 1, "slot": "s1",
                "recheck_by": "zcode", "at": "2026-11-24T00:00:00.000000Z",
                "evidence_refs": ["v:v1"], "reason": "已修复"}
        result = self._decide(plan=self._plan_file([plan]))
        self.assertEqual(result["facts"]["result"]["materials"]["state"], "legacy")
        self.assertEqual(result["facts"]["result"]["facts"]["materials_state"], "legacy")

    def test_plan_closing_the_earlier_blocking_allows_pass(self):
        """本次 --plan 一并给出旧轮处置（accepted+verified 证据、非提出者复核）→ 可 pass。"""
        self._stage()
        self._stage_materials()
        plan = [{"finding_id": "f1", "decision": "accepted", "round": 1, "slot": "s1",
                 "recheck_by": "zcode", "at": "2026-11-24T00:00:00.000000Z",
                 "evidence_refs": ["v:v1"], "reason": "修复已在本轮交付并通过验证"}]
        result = self._decide(plan=self._plan_file(plan))
        self.assertEqual(result["code"], "WF_OK")
        self.assertEqual(result["facts"]["result"].get("verdict"), "pass")
        self.assertEqual(result["facts"]["result"]["materials"]["state"], "fixed")


if __name__ == "__main__":
    unittest.main()
