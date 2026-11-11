"""⑥ 修复态（v66）的可执行复现：一条「机制」断言至少一个用例，编号对应提案 §7 矩阵。

这些用例只读事实与门禁行为：`repair_scope` / `exits_for` 是派生，`final_gate_nonstep` 是门禁，
`check_validity` / `review_binding` 是共享子判定。凡是需要"任务目录/写权/动作"的部分用
`mock` 把锚点与回执来源定住，避免把单测变成端到端夹具。
"""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "docs" / "workflows" / "wf" / "payload" / "lib"))

from wflib import cli, gates, judgments, records, review  # noqa: E402
from wflib import tasks as tasks_mod  # noqa: E402

RULE = "wf-rules-test"
CHECK_ID = "c1"
ANCHOR = "sha256:a1"
COVERED = ["node_modules/**", ".env", "*.pem", ".codex/**", "../**", ".wf/tasks/**"]
SKILLS = REPO / "docs" / "workflows" / "wf" / "skills"


class Ctx:
    def __init__(self, root):
        self.root = str(root)

    def rule_version(self):
        return RULE

    def debug_threshold(self):
        return 3


def write_report(root, rel="review/round-1/review-zcode.md", findings=(), *, anchor=ANCHOR,
                 check_id=CHECK_ID, round_no=1, task_id="t1", verdict="pass", axes=None):
    payload = {"protocol": review.PROTOCOL, "task-id": task_id, "round": round_no,
               "review-time": "2026-11-11T00:00:00Z", "review-focus": "f",
               "check-anchor": {"check_id": check_id, "check_anchor": anchor},
               "read-scope": ["pkg/**"], "excluded-scope": COVERED,
               "axes": axes or {name: "pass" for name in review.REVIEW_AXES},
               "findings": list(findings), "verdict": verdict}
    path = Path(root) / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"{review.REPORT_MARKER}\n\n```json\n{json.dumps(payload)}\n```\n", encoding="utf-8")
    return path


def make_task(root, *, complexity="light", check_result="pass", findings=(), dispositions=(),
              verdict="pass", cited=True, launches=None, rounds=None, acceptances=None,
              round_no=1):
    write_report(root, findings=findings, round_no=round_no)
    digest = records.file_digest(Path(root) / "review/round-1/review-zcode.md")
    reviews = {"imported": [{"round": round_no, "slot": "zcode", "agent": "zcode",
                             "report_path": "review/round-1/review-zcode.md",
                             "report_digest": digest,
                             "anchor": {"check_id": CHECK_ID, "check_anchor": ANCHOR}}],
               "dispositions": list(dispositions)}
    if launches is not None:
        reviews["launches"] = launches
    if rounds is not None:
        reviews["rounds"] = rounds
    if acceptances is not None:
        reviews["unknown_acceptances"] = acceptances
    if verdict:
        reviews["result"] = {"verdict": verdict, "round": round_no, "check_id": CHECK_ID,
                             "imported": ([{"slot": "zcode", "report_digest": digest}]
                                          if cited else [])}
    return {"id": "t1", "title": "t", "plan": {"complexity": complexity},
            "check": {"id": CHECK_ID, "result": check_result,
                      "anchor": {"check_anchor": ANCHOR, "rule_version": RULE}},
            "reviews": reviews}


def anchor_patch(anchor=ANCHOR, error=None):
    value = {"error": error} if error else {"anchor": anchor, "parts": {}}
    return mock.patch.object(tasks_mod, "current_check_anchor", return_value=value)


def launch(round_no=1, cli_name="codex", slots=2, **extra):
    entry = {"round": round_no, "implementation_cli": cli_name,
             "slots": [{"slot": f"s{index + 1}"} for index in range(slots)]}
    entry.update(extra)
    return entry


class RepairScopeTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = self._tmp.name
        self.ctx = Ctx(self.root)

    def tearDown(self):
        self._tmp.cleanup()

    # 1：open_blocking 与 final_gate 的 unaddressed_blocking 逐项一致，且每条带 round
    def test_01_open_blocking_matches_gate(self):
        task = make_task(self.root, findings=[{"id": "f1", "severity": "blocking"}], verdict=None)
        scope = review.repair_scope(self.ctx, task)
        ok, code, facts = gates.final_gate_nonstep(self.ctx, task)
        self.assertFalse(ok)
        self.assertEqual(code, "WF_UNRESOLVED_BLOCKING")
        self.assertEqual(scope["open_blocking"], facts["unaddressed_blocking"])
        self.assertEqual({item["round"] for item in scope["open_blocking"]}, {1})

    # 2：binding 是子判定（fail + 未换代 + 摘要一致 ⇒ true）
    def test_02_binding_true_for_fail(self):
        task = make_task(self.root, verdict="fail",
                         findings=[{"id": "f1", "severity": "blocking"}])
        with anchor_patch():
            binding = gates.review_binding(self.ctx, task)
        self.assertTrue(binding["binding"], binding)
        self.assertEqual(binding["blockers"], [])

    # 3：空引用 ⇒ binding false（与门禁的独立拒绝一致）
    def test_03_binding_false_without_cited(self):
        task = make_task(self.root, cited=False)
        with anchor_patch():
            binding = gates.review_binding(self.ctx, task)
        self.assertFalse(binding["binding"])
        self.assertIn("no_cited_reports", binding["blockers"])

    # 4：check_valid 逐分支
    def test_04_check_valid_branches(self):
        cases = [
            ("rule_version", {"check": {"id": CHECK_ID, "result": "pass",
                                        "anchor": {"check_anchor": ANCHOR, "rule_version": "old"}}},
             None, "rule_version"),
            ("anchor_unavailable", {"check": {"id": CHECK_ID, "result": "pass",
                                              "anchor": {"check_anchor": ANCHOR, "rule_version": RULE}}},
             ("WF_CHECK_FAILED", {"reason": "no anchor"}), "anchor_unavailable"),
            ("invalidated", {"check": {"id": CHECK_ID, "result": "pass",
                                       "anchor": {"check_anchor": ANCHOR, "rule_version": RULE},
                                       "invalidated": {"at": "2026-11-11T00:00:00Z"}}},
             None, "invalidated"),
            ("result_not_pass", {"check": {"id": CHECK_ID, "result": "fail",
                                           "anchor": {"check_anchor": ANCHOR, "rule_version": RULE}}},
             None, "result_not_pass"),
            ("anchor_missing", {"check": {"id": CHECK_ID, "result": "pass",
                                          "anchor": {"rule_version": RULE}}},
             None, "anchor_missing"),
            ("anchor_drift", {"check": {"id": CHECK_ID, "result": "pass",
                                        "anchor": {"check_anchor": "sha256:old", "rule_version": RULE}}},
             None, "anchor_drift"),
        ]
        for name, overlay, error, blocker in cases:
            with self.subTest(name):
                task = make_task(self.root)
                task.update(overlay)
                with anchor_patch(error=error), \
                        mock.patch.object(gates, "check_result_problems", return_value=[]):
                    verdict = gates.check_validity(self.ctx, task)
                self.assertFalse(verdict["valid"])
                self.assertEqual(verdict["blockers"], [blocker])
        task = make_task(self.root)
        with anchor_patch(), mock.patch.object(gates, "check_result_problems", return_value=[]):
            self.assertTrue(gates.check_validity(self.ctx, task)["valid"])
        with anchor_patch(), mock.patch.object(gates, "check_result_problems",
                                               return_value=[{"reason": "x"}]):
            verdict = gates.check_validity(self.ctx, task)
        self.assertEqual(verdict["blockers"], ["structure_problems"])

    # 5：内容漂移 ⇒ C1 未满足且 blocker 是 anchor_drift
    def test_05_content_change_blocks_c1(self):
        task = make_task(self.root)
        with anchor_patch(anchor="sha256:changed"), \
                mock.patch.object(gates, "check_result_problems", return_value=[]):
            scope = review.repair_scope(self.ctx, task)
        self.assertFalse(scope["conclusion"]["check_valid"])
        self.assertIn("anchor_drift", scope["conclusion"]["check_blockers"])
        self.assertIn({"condition": "C1", "action": "rerun_check", "round": None}, scope["exits"])

    # 6：重查产生新 check ⇒ binding false 且 blocker 是 check_id_changed
    def test_06_new_check_unbinds(self):
        task = make_task(self.root)
        task["check"]["id"] = "c2"
        with anchor_patch(anchor="sha256:a2"), \
                mock.patch.object(gates, "check_result_problems", return_value=[]):
            scope = review.repair_scope(self.ctx, task)
        self.assertFalse(scope["conclusion"]["binding"])
        self.assertIn("check_id_changed", scope["conclusion"]["binding_blockers"])

    # 7：只有 accepted 清零；amended 不关闭且有 disposition 标注；rejected 同
    def test_07_only_accepted_closes(self):
        findings = [{"id": "f1", "severity": "blocking"}]
        accepted = make_task(self.root,
                             findings=findings,
                             dispositions=[{"finding_id": "f1", "decision": "accepted",
                                            "reason": "已修复", "recheck_by": "pi"}])
        self.assertEqual(review.open_findings(self.ctx, accepted)["blocking"], [])
        for decision in ("amended", "rejected"):
            task = make_task(self.root, findings=findings,
                             dispositions=[{"finding_id": "f1", "decision": decision,
                                            "reason": "不关闭", "recheck_by": "pi"}])
            blocking = review.open_findings(self.ctx, task)["blocking"]
            self.assertEqual([item["finding_id"] for item in blocking], ["f1"], decision)
            self.assertEqual(blocking[0]["disposition"], decision)

    # 8：fail + binding + 无 open blocking ⇒ C4 未满足；exits 含 relaunch_review / resume_inflight
    def test_08_fail_round_needs_pass(self):
        task = make_task(self.root, complexity="complex", verdict="fail",
                         launches=[launch(1, slots=1), launch(2, slots=2)])
        for agent in ("pi", "omega"):
            rel = f"review/round-2/review-{agent}.md"
            write_report(self.root, rel, round_no=2)
            task["reviews"]["imported"].append(
                {"round": 2, "slot": agent, "agent": agent, "report_path": rel,
                 "report_digest": records.file_digest(Path(self.root) / rel),
                 "anchor": {"check_id": CHECK_ID, "check_anchor": ANCHOR}})
        with anchor_patch():
            scope = review.repair_scope(self.ctx, task)
        actions = {(item["condition"], item["action"], item["round"]) for item in scope["exits"]}
        self.assertIn(("C4", "relaunch_review", None), actions)
        self.assertIn(("C4", "resume_inflight", 2), actions)
        self.assertNotIn(("C2", "record_disposition", None), actions)

    # 9 + 60：C3 只统计仍承载未完义务的证据（引用 / 未 pass 轮 / result 轮）
    def test_09_c3_coverage(self):
        task = make_task(self.root, complexity="complex", verdict=None,
                         rounds=[{"round": 1, "verdict": "pass", "check_id": CHECK_ID,
                                  "decided_at": "2026-11-11T00:00:00Z"}])
        path = Path(self.root) / "review/round-1/review-zcode.md"
        path.unlink()
        with anchor_patch():
            # round 1 最新 verdict = pass、未被引用、也不在 result 轮 → 不阻断
            self.assertEqual(review.exiting_evidence(self.ctx, task), [])
            # 属于当前 result 那一轮的任何报告（即使未被引用）→ 阻断
            # （结论引用的报告必然属于结论那一轮：`review_binding` 的键就是 result.round + slot）
            task["reviews"]["result"] = {"verdict": "pass", "round": 1, "check_id": CHECK_ID,
                                         "imported": []}
            self.assertEqual(len(review.exiting_evidence(self.ctx, task)), 1)
            write_report(self.root, "review/round-2/review-pi.md", round_no=2)
            round2 = Path(self.root) / "review/round-2/review-pi.md"
            task["reviews"]["imported"].append(
                {"round": 2, "slot": "pi", "agent": "pi", "report_path": "review/round-2/review-pi.md",
                 "report_digest": records.file_digest(round2),
                 "anchor": {"check_id": CHECK_ID, "check_anchor": ANCHOR}})
            task["reviews"]["result"] = {"verdict": "pass", "round": 2, "check_id": CHECK_ID,
                                         "imported": [{"slot": "zcode", "report_digest": "sha256:x"}]}
            round2.unlink()
            # 只有 result 那一轮（round 2）的损坏报告阻断；round 1 已 pass 且不再被引用 → 豁免
            self.assertEqual(len(review.exiting_evidence(self.ctx, task)), 1)
            # 未判定轮（最新 verdict 缺）→ 阻断
            task["reviews"]["result"] = {"verdict": "pass", "round": 3, "check_id": CHECK_ID,
                                         "imported": []}
            task["reviews"]["rounds"] = []
            self.assertEqual(len(review.exiting_evidence(self.ctx, task)), 2)

    # 10：light 的引用损坏仍阻断，且 release_allowed=true；放行后 C3 满足
    def test_10_light_cited_damage_releasable(self):
        task = make_task(self.root, complexity="light")
        digest = task["reviews"]["imported"][0]["report_digest"]
        (Path(self.root) / "review/round-1/review-zcode.md").unlink()
        with anchor_patch():
            scope = review.repair_scope(self.ctx, task)
            entry = scope["unverifiable"][0]
            self.assertTrue(entry["cited"])
            self.assertTrue(entry["release_allowed"])
            self.assertEqual(entry["cause"], "missing")
            self.assertIn(("C3", "human_release", None),
                          {(item["condition"], item["action"], item["round"]) for item in scope["exits"]})
            task["reviews"]["unknown_acceptances"] = [
                {"batch": "b1", "round": 1, "slot": "zcode", "report_digest": digest,
                 "by": "human:x", "at": "now", "quote": "q", "source": "user-declared",
                 "waive_unknown_findings": True}]
            scope2 = review.repair_scope(self.ctx, task)
        self.assertTrue(scope2["unverifiable"][0]["released"])
        self.assertEqual(scope2["unverifiable"][0]["state"], "accepted-risk")
        self.assertEqual(review.exiting_evidence(self.ctx, task), [])

    # 11：三元组全等才匹配；撤销后恢复阻断
    def test_11_triple_match_and_revoke(self):
        task = make_task(self.root)
        digest = task["reviews"]["imported"][0]["report_digest"]
        (Path(self.root) / "review/round-1/review-zcode.md").unlink()
        task["reviews"]["unknown_acceptances"] = [
            {"batch": "b1", "round": 1, "slot": "zcode", "report_digest": "sha256:other",
             "by": "human:x", "at": "now", "quote": "q", "source": "user-declared"}]
        with anchor_patch():
            self.assertFalse(review.repair_scope(self.ctx, task)["unverifiable"][0]["released"])
            task["reviews"]["unknown_acceptances"][0]["report_digest"] = digest
            self.assertTrue(review.repair_scope(self.ctx, task)["unverifiable"][0]["released"])
            task["reviews"]["unknown_acceptances"][0]["revoked"] = True
            self.assertFalse(review.repair_scope(self.ctx, task)["unverifiable"][0]["released"])

    # 12 + 27：决定文件 schema（digest 权威来源、四件套、waive 必填）
    def test_12_decision_schema(self):
        task = make_task(self.root)
        digest = task["reviews"]["imported"][0]["report_digest"]
        current = {(1, "zcode", digest): {"release_allowed": True, "cited": True}}
        good = {"round": 1, "slot": "zcode", "report_digest": digest, "quote": "q",
                "by": "human:x", "at": "2026-11-11T00:00:00Z", "source": "user-declared",
                "waive_unknown_findings": True}
        bad, accepted = review.acceptance_problems(task, {"batch": "b1", "acceptances": [good]}, current)
        self.assertEqual((bad, len(accepted)), ([], 1))
        for field in ("quote", "by", "at", "source"):
            item = dict(good)
            item[field] = ""
            bad, accepted = review.acceptance_problems(
                task, {"batch": "b1", "acceptances": [item]}, current)
            self.assertEqual(accepted, [])
        for mutate, reason in ((lambda item: item.update(report_digest="sha256:typo"), "report_digest"),
                               (lambda item: item.update(by="ai:x"), "by"),
                               (lambda item: item.pop("waive_unknown_findings"), "waive_unknown_findings")):
            item = dict(good)
            mutate(item)
            bad, accepted = review.acceptance_problems(
                task, {"batch": "b1", "acceptances": [item]}, current)
            self.assertEqual(accepted, [])
            self.assertTrue(any(problem.get("field") == reason
                                for entry in bad for problem in entry.get("problems") or []))
        # 不在当前 unverifiable 里 ⇒ 不做预放行
        bad, accepted = review.acceptance_problems(task, {"batch": "b1", "acceptances": [good]}, {})
        self.assertEqual(accepted, [])
        # complex 的引用证据不可放行（release_allowed == false）⇒ 拒绝（B2 强制，不只是展示）
        task["plan"]["complexity"] = "complex"
        bad, accepted = review.acceptance_problems(
            task, {"batch": "b1", "acceptances": [good]},
            {(1, "zcode", digest): {"release_allowed": False, "cited": True}})
        self.assertEqual(accepted, [])
        self.assertTrue(any("不可放行" in problem.get("reason", "")
                            for entry in bad for problem in entry.get("problems") or []))

    # 13：撤销后可重新批准；幂等只在「同键 ∧ 未撤销 ∧ 未消费」
    def test_13_revoke_then_reapprove(self):
        item = {"round": 1, "slot": "zcode", "report_digest": "sha256:d", "quote": "q",
                "by": "human:x", "at": "now", "source": "user-declared"}
        kept = []
        added, already = review.merge_acceptances(kept, [item], "b1", "t1")
        self.assertEqual((len(added), already), (1, []))
        added, already = review.merge_acceptances(kept, [item], "b2", "t2")
        self.assertEqual((added, len(already)), ([], 1))
        kept[0]["revoked"] = True
        added, already = review.merge_acceptances(kept, [item], "b3", "t3")
        self.assertEqual((len(added), already), (1, []))
        self.assertEqual(len(kept), 2)
        kept[1]["consumed"] = True
        self.assertEqual(review.active_acceptances({"reviews": {"unknown_acceptances": kept}}), [])

    # 14：恢复原字节 → 离开 unverifiable
    def test_14_restore_clears_unverifiable(self):
        task = make_task(self.root)
        path = Path(self.root) / "review/round-1/review-zcode.md"
        text = path.read_text(encoding="utf-8")
        path.unlink()
        with anchor_patch():
            self.assertEqual(len(review.repair_scope(self.ctx, task)["unverifiable"]), 1)
            path.write_text(text, encoding="utf-8")
            self.assertEqual(review.repair_scope(self.ctx, task)["unverifiable"], [])

    # 15 + 45：cause 三分只由 open_findings 产出，repair_scope 逐项一致
    def test_15_cause_three_way(self):
        task = make_task(self.root)
        path = Path(self.root) / "review/round-1/review-zcode.md"
        path.unlink()
        with anchor_patch():
            self.assertEqual(review.open_findings(self.ctx, task)["unavailable"][0]["cause"], "missing")
            scope = review.repair_scope(self.ctx, task)
            self.assertEqual([item["cause"] for item in scope["unverifiable"]], ["missing"])
            path.write_text("tampered", encoding="utf-8")
            self.assertEqual(review.open_findings(self.ctx, task)["unavailable"][0]["cause"], "changed")
            with mock.patch.object(records, "file_digest", side_effect=OSError("boom")):
                findings = review.open_findings(self.ctx, task)
        self.assertEqual(findings["unavailable"][0]["cause"], "unreadable")

    # 16：权限/IO 故障不崩：open_findings 与 review_binding 都走归因分支
    def test_16_read_failure_is_attributed(self):
        task = make_task(self.root)
        with anchor_patch(), mock.patch.object(records, "file_digest", side_effect=OSError("denied")):
            findings = review.open_findings(self.ctx, task)
            binding = gates.review_binding(self.ctx, task)
        self.assertEqual(findings["unavailable"][0]["cause"], "unreadable")
        self.assertFalse(binding["binding"])
        self.assertEqual(binding["blockers"], ["unreadable"])

    # 17：并存无遮蔽：open_blocking 与未放行 unverifiable 同时出现
    def test_17_coexistence(self):
        task = make_task(self.root, complexity="complex")
        write_report(self.root, "review/round-1/review-pi.md",
                     findings=[{"id": "f1", "severity": "blocking"}])
        task["reviews"]["imported"].append(
            {"round": 1, "slot": "pi", "agent": "pi", "report_path": "review/round-1/review-pi.md",
             "report_digest": records.file_digest(Path(self.root) / "review/round-1/review-pi.md"),
             "anchor": {"check_id": CHECK_ID, "check_anchor": ANCHOR}})
        (Path(self.root) / "review/round-1/review-zcode.md").unlink()
        with anchor_patch():
            scope = review.repair_scope(self.ctx, task)
        self.assertTrue(scope["open_blocking"])
        self.assertTrue(scope["unverifiable"])
        actions = {item["action"] for item in scope["exits"]}
        self.assertIn("record_disposition", actions)
        self.assertIn("restore_bytes", actions)

    # 18：light 不承担 C4（fail / unavailable / invalidated 都不产生"新审查"义务）
    def test_18_light_has_no_c4(self):
        for verdict in ("fail", "unavailable"):
            task = make_task(self.root, complexity="light", verdict=verdict)
            with anchor_patch():
                scope = review.repair_scope(self.ctx, task)
            self.assertFalse(scope["review_required"])
            self.assertFalse([item for item in scope["exits"] if item["condition"] == "C4"], verdict)

    # 19：light 的 C2/C3 仍成立
    def test_19_light_c2_c3_apply(self):
        task = make_task(self.root, findings=[{"id": "f1", "severity": "blocking"}], verdict=None)
        ok, code, _facts = gates.final_gate_nonstep(self.ctx, task)
        self.assertEqual((ok, code), (False, "WF_UNRESOLVED_BLOCKING"))
        (Path(self.root) / "review/round-1/review-zcode.md").unlink()
        task["reviews"]["dispositions"] = [{"finding_id": "f1", "decision": "accepted",
                                            "reason": "ok", "recheck_by": "pi"}]
        with anchor_patch():
            ok, code, facts = gates.final_gate_nonstep(self.ctx, task)
        self.assertEqual((ok, code), (False, "WF_REVIEW_INVALID"))
        self.assertEqual(facts["reason"], "unverifiable_evidence")

    # 20：不含"等待评审/待评审"类状态
    def test_20_no_waiting_state(self):
        task = make_task(self.root, complexity="complex", verdict="fail")
        with anchor_patch():
            scope = review.repair_scope(self.ctx, task)
        self.assertEqual(set(scope), {"review_required", "rounds", "launches", "open_blocking",
                                      "unverifiable", "conclusion", "exits"})
        self.assertEqual(set(scope["conclusion"]), {
            "decided", "verdict", "round", "check_id", "binding", "binding_blockers",
            "check_valid", "check_blockers", "stale_extra", "applicable"})
        self.assertFalse([key for key in scope if "status" in key or "state" in key])

    # 21：--short 输出四条件 + exits，不输出完整事实集
    def test_21_short_projection(self):
        task = make_task(self.root, complexity="complex", verdict="pass",
                         launches=[launch(1)])
        with anchor_patch(), mock.patch.object(gates, "check_result_problems", return_value=[]):
            scope = review.repair_scope(self.ctx, task)
        precheck = {"ok": False, "blocking": [{"stage": "steps", "id": "task.sampled"}]}
        short = cli._short_repair(scope, precheck, ["acceptance"])
        self.assertEqual(set(short["conditions"]),
                         {"C1_check_valid", "C2_no_open_blocking",
                          "C3_no_unreleased_evidence", "C4_review_bound_pass"})
        self.assertEqual(short["exits"], scope["exits"])
        self.assertNotIn("launches", short)
        self.assertNotIn("conclusion", short)
        self.assertEqual(short["blocking"], precheck["blocking"])
        self.assertEqual(short["unknown_acceptances"], ["acceptance"])   # #46：--short 也强制回显

    # 22：协议零改动（phase.enum / 迁移数 / next_by_position 逐字节）
    def test_22_protocol_untouched(self):
        result = subprocess.run(["git", "diff", "--name-only", "8da2f23", "--",
                                 "docs/workflows/wf/protocol"], cwd=str(REPO),
                                capture_output=True, text=True)
        self.assertEqual(result.stdout.strip(), "", result.stdout)

    # 23：C4 未满足时 pause_for_human / abandon_task 始终出现，且 abandon 不是推荐
    def test_23_terminal_actions_always_listed(self):
        task = make_task(self.root, complexity="complex", verdict="fail")
        with anchor_patch():
            scope = review.repair_scope(self.ctx, task)
        actions = [item["action"] for item in scope["exits"]]
        self.assertIn("pause_for_human", actions)
        self.assertIn("abandon_task", actions)
        for item in scope["exits"]:
            self.assertEqual(set(item), {"condition", "action", "round"})

    # 25 / 47：exits 形状与单点产出
    def test_25_exits_shape_single_source(self):
        task = make_task(self.root, complexity="complex", verdict="pass",
                         launches=[launch(1)])
        with anchor_patch(), mock.patch.object(gates, "check_result_problems", return_value=[]):
            scope = review.repair_scope(self.ctx, task)
        for item in scope["exits"]:
            self.assertEqual(set(item), {"condition", "action", "round"})
            self.assertIn(item["condition"], {"C1", "C2", "C3", "C4"})
        source = (REPO / "docs/workflows/wf/payload/lib/wflib/review.py").read_text(encoding="utf-8")
        self.assertEqual(source.count("def exits_for("), 1)
        self.assertNotIn('"preferred"', source)
        gates_source = (REPO / "docs/workflows/wf/payload/lib/wflib/gates.py").read_text(encoding="utf-8")
        self.assertNotIn("def exits_for", gates_source)

    # 26：无 launch 时不含 await_material/resume_inflight；blocked 仅 material_missing 才 await
    def test_26_no_launch_no_resume(self):
        task = make_task(self.root, complexity="complex", verdict="fail")
        with anchor_patch():
            scope = review.repair_scope(self.ctx, task)
        actions = {item["action"] for item in scope["exits"]}
        self.assertFalse({"await_material", "resume_inflight"} & actions)
        task["reviews"]["launches"] = [launch(1, slots=2)]
        with anchor_patch():
            scope = review.repair_scope(self.ctx, task)
        self.assertIn("await_material", {item["action"] for item in scope["exits"]})

    # 28：共享函数二分，两通道不合并
    def test_28_channels_separate(self):
        task = make_task(self.root)
        with anchor_patch(anchor="sha256:other"):
            report_facts = review.review_report_problems(
                self.ctx, task, round_no=1, launch=launch(1),
                imported=task["reviews"]["imported"], anchor="sha256:other", proposers={})
        self.assertEqual(report_facts["blockers"], ["anchor_stale"])
        eligibility = review.review_eligibility(["codex"], {"codex"}, imported_count=2, declared_slots=2)
        self.assertEqual(eligibility["blockers"], ["implementer_overlap", "insufficient_reviewers"])
        self.assertEqual([item["reason"].startswith("审查 CLI 与实施 CLI 重叠")
                          for item in eligibility["problems"]], [False, True])

    # 29：部分导入 + 硬失败 ⇒ blocked 含硬失败，不因材料未齐报空
    def test_29_partial_import_hard_failure(self):
        task = make_task(self.root)
        task["reviews"]["launches"] = [launch(1, slots=2)]
        with anchor_patch(anchor="sha256:other"), \
                mock.patch.object(review, "_current_anchor",
                                  return_value=("sha256:other", {})):
            facts = review.launch_facts(self.ctx, task)
        self.assertIn("anchor_stale", facts[0]["blocked"])

    # 30 + 42：发现式 2/3 可判；只到 1 位 ⇒ material_missing
    def test_30_discovered_two_of_three(self):
        task = make_task(self.root)
        digest = task["reviews"]["imported"][0]["report_digest"]
        task["reviews"]["launches"] = [launch(1, slots=3)]
        task["reviews"]["imported"].append({"round": 1, "slot": "pi", "agent": "pi",
                                            "report_path": "review/round-1/review-zcode.md",
                                            "report_digest": digest,
                                            "anchor": {"check_id": CHECK_ID, "check_anchor": ANCHOR}})
        with anchor_patch():
            self.assertNotIn("material_missing", review.launch_facts(self.ctx, task)[0]["blocked"])
            task["reviews"]["imported"] = task["reviews"]["imported"][:1]
            self.assertIn("material_missing", review.launch_facts(self.ctx, task)[0]["blocked"])

    # 31：恢复后 findings 重新枚举，此前的 waive 不覆盖新 findings
    def test_31_waiver_does_not_cover_new_findings(self):
        task = make_task(self.root, findings=[{"id": "f1", "severity": "blocking"}])
        digest = task["reviews"]["imported"][0]["report_digest"]
        path = Path(self.root) / "review/round-1/review-zcode.md"
        saved = path.read_text(encoding="utf-8")
        path.unlink()
        task["reviews"]["unknown_acceptances"] = [
            {"batch": "b1", "round": 1, "slot": "zcode", "report_digest": digest,
             "by": "human:x", "at": "now", "quote": "q", "source": "user-declared"}]
        with anchor_patch():
            self.assertEqual(review.exiting_evidence(self.ctx, task), [])
            path.write_text(saved, encoding="utf-8")
            self.assertEqual(len(review.open_findings(self.ctx, task)["blocking"]), 1)
            write_report(self.root, findings=[{"id": "f1", "severity": "blocking"},
                                              {"id": "f2", "severity": "blocking"}])
            task["reviews"]["imported"][0]["report_digest"] = records.file_digest(path)
            self.assertEqual(len(review.open_findings(self.ctx, task)["blocking"]), 2)

    # 32 + 34：一次一事件：恢复即消费；再次损坏时旧放行不再生效
    def test_32_one_event_consumed(self):
        task = make_task(self.root)
        digest = task["reviews"]["imported"][0]["report_digest"]
        path = Path(self.root) / "review/round-1/review-zcode.md"
        saved = path.read_text(encoding="utf-8")
        path.unlink()
        task["reviews"]["unknown_acceptances"] = [
            {"batch": "b1", "round": 1, "slot": "zcode", "report_digest": digest,
             "by": "human:x", "at": "now", "quote": "q", "source": "user-declared"}]
        with anchor_patch():
            self.assertEqual(review.exiting_evidence(self.ctx, task), [])
            path.write_text(saved, encoding="utf-8")
            consumed = review.consume_recovered(self.ctx, task)
            self.assertEqual(len(consumed), 1)
            self.assertTrue(task["reviews"]["unknown_acceptances"][0]["consumed"])
            path.unlink()
            self.assertEqual(len(review.exiting_evidence(self.ctx, task)), 1)
            self.assertEqual(review.repair_scope(self.ctx, task)["unverifiable"][0]["state"], "consumed")

    # 33：资格拆两类（重叠即使材料未齐也立即记硬失败）
    def test_33_eligibility_split(self):
        eligibility = review.review_eligibility(["codex"], {"codex"}, imported_count=1, declared_slots=3)
        self.assertEqual(eligibility["blockers"], ["implementer_overlap", "material_missing"])
        eligibility = review.review_eligibility(["codex"], {"pi"}, imported_count=3, declared_slots=3)
        self.assertEqual(eligibility["blockers"], ["insufficient_reviewers"])

    # 35：decided 语义（无决策记录 ⇒ 未判定）
    def test_35_decided_semantics(self):
        task = make_task(self.root, complexity="complex", verdict=None)
        self.assertIsNone(review.latest_decision(task, 1))
        task["reviews"]["rounds"] = [{"round": 1, "verdict": "fail", "check_id": CHECK_ID,
                                      "decided_at": "2026-11-11T00:00:00Z"},
                                     {"round": 1, "verdict": "pass", "check_id": CHECK_ID,
                                      "decided_at": "2026-11-11T02:00:00Z"}]
        self.assertEqual(review.latest_decision(task, 1)["verdict"], "pass")

    # 36 + 51：失效判定唯一落点是 binding 的 CLI 校验
    def test_36_invalidation_only_in_binding(self):
        source = (REPO / "docs/workflows/wf/payload/lib/wflib/review.py").read_text(encoding="utf-8")
        self.assertNotIn('result_now["verdict"] = "invalidated"', source)
        task = make_task(self.root, complexity="complex", verdict="pass",
                         launches=[launch(1, "codex"), launch(2, "pi")])
        with anchor_patch(), mock.patch.object(gates, "check_result_problems", return_value=[]):
            binding = gates.review_binding(self.ctx, task)
        self.assertFalse(binding["binding"])
        self.assertEqual(binding["blockers"], ["implementation_cli_changed"])
        self.assertEqual(task["reviews"]["result"]["verdict"], "pass")

    # 37：D4 预检契约（不调 final_gate、evaluate 只传 rule_version、按 id 过滤 changes-persisted）
    def test_37_d4_contract(self):
        task = make_task(self.root)
        task["action"] = {"id": "a1", "state": "applying"}
        calls = {}

        def fake_nonstep(ctx, tsk, ignore_action_id=None):
            calls["ignore"] = ignore_action_id
            return True, None, {}

        def fake_evaluate(ctx, tsk, due, *, rule_version=None):
            calls["due"] = due
            calls["rule_version"] = rule_version
            return [{"id": "task.changes-persisted", "status": "missing", "code": "WF_WIP_UNRESOLVED"},
                    {"id": "task.sampled", "status": "completed", "code": None}]

        with mock.patch.object(gates, "final_gate_nonstep", side_effect=fake_nonstep), \
                mock.patch.object(gates, "evaluate", side_effect=fake_evaluate), \
                mock.patch.object(gates, "final_gate", side_effect=AssertionError("不得只调一次 final_gate")), \
                mock.patch.object(tasks_mod, "task_receipts", return_value=[]), \
                mock.patch("wflib.scope.classify_candidates",
                           return_value={"buckets": {"e": []}}), \
                mock.patch("wflib.scope.uncommitted_paths", return_value=[]):
            result = tasks_mod.archive_precheck(self.ctx, task)
        self.assertTrue(result["ok"], result)
        self.assertEqual(calls, {"ignore": "a1", "due": "before_archive", "rule_version": RULE})

    # 38：released 三条件（未撤销 **且** 未消费）
    def test_38_released_requires_active(self):
        task = make_task(self.root)
        digest = task["reviews"]["imported"][0]["report_digest"]
        (Path(self.root) / "review/round-1/review-zcode.md").unlink()
        base = {"batch": "b", "round": 1, "slot": "zcode", "report_digest": digest,
                "by": "human:x", "at": "now", "quote": "q", "source": "user-declared"}
        with anchor_patch():
            for overlay, expected in (({}, True), ({"revoked": True}, False), ({"consumed": True}, False)):
                task["reviews"]["unknown_acceptances"] = [dict(base, **overlay)]
                self.assertEqual(
                    review.repair_scope(self.ctx, task)["unverifiable"][0]["released"], expected, overlay)

    # 39：消费写点三处（archive 预检前 / review-import / review-decide）
    def test_39_consume_write_points(self):
        review_src = (REPO / "docs/workflows/wf/payload/lib/wflib/review.py").read_text(encoding="utf-8")
        tasks_src = (REPO / "docs/workflows/wf/payload/lib/wflib/tasks.py").read_text(encoding="utf-8")
        self.assertEqual(review_src.count("        consume_recovered(ctx, task)\n"), 2)   # import + decide
        self.assertEqual(tasks_src.count("review_mod.consume_recovered(ctx, task)"), 1)   # archive 预检前
        self.assertEqual(review_src.count("def consume_recovered("), 1)

    # 40：存量回填：rounds 空时按 result 推断一条（inferred、decided_at=null）
    def test_40_legacy_rounds_inferred(self):
        task = make_task(self.root, verdict="pass")
        rounds = review.decision_rounds(task)
        self.assertEqual(len(rounds), 1)
        self.assertTrue(rounds[0]["inferred"])
        self.assertIsNone(rounds[0]["decided_at"])
        task["reviews"]["rounds"] = [{"round": 1, "verdict": "pass", "check_id": CHECK_ID,
                                      "decided_at": "2026-11-11T00:00:00Z"}]
        self.assertNotIn("inferred", review.decision_rounds(task)[0])

    # 41：A6 裁定：缺登记摘要不计入 C3 阻断，单列 legacy_unverifiable
    def test_41_legacy_missing_digest(self):
        task = make_task(self.root)
        task["reviews"]["imported"][0]["report_digest"] = None
        (Path(self.root) / "review/round-1/review-zcode.md").unlink()
        with anchor_patch():
            self.assertEqual(review.exiting_evidence(self.ctx, task), [])
            scope = review.repair_scope(self.ctx, task)
            legacy = review.legacy_unverifiable(self.ctx, task)
        self.assertEqual(len(legacy), 1)
        self.assertIn("缺登记摘要", legacy[0]["note"])
        # A6 需要的产出：明确出口（补摘要 / 另开新一轮 / abandon）
        self.assertEqual(len(legacy[0]["exits"]), 3)
        self.assertIn("review-import", legacy[0]["exits"][0])
        self.assertIn("review-launch", legacy[0]["exits"][1])
        self.assertIn("task-abandon", legacy[0]["exits"][2])
        # 既不进 unverifiable，也不产生做不到的出口
        self.assertEqual(scope["unverifiable"], [])
        actions = {item["action"] for item in scope["exits"]}
        self.assertFalse({"restore_bytes", "human_release"} & actions)

    # 43：inferred 属 rounds[]，不属于 launches[]
    def test_43_inferred_boundary(self):
        task = make_task(self.root, complexity="complex", verdict="pass", launches=[launch(1)])
        with anchor_patch(), mock.patch.object(gates, "check_result_problems", return_value=[]):
            scope = review.repair_scope(self.ctx, task)
        self.assertTrue(scope["rounds"][0]["inferred"])
        self.assertNotIn("inferred", scope["launches"][0])
        short = cli._short_repair(scope, {"blocking": []})
        self.assertTrue(short["rounds"][0]["inferred"])

    # 44：release_allowed 随 complexity 漂移
    def test_44_release_allowed_drift(self):
        task = make_task(self.root, complexity="light")
        (Path(self.root) / "review/round-1/review-zcode.md").unlink()
        with anchor_patch():
            self.assertTrue(review.repair_scope(self.ctx, task)["unverifiable"][0]["release_allowed"])
            task["plan"]["complexity"] = "complex"
            self.assertFalse(review.repair_scope(self.ctx, task)["unverifiable"][0]["release_allowed"])

    # 46：归档回显 + 抽样冻结集含放行记录
    def test_46_echo_and_sampling(self):
        task = make_task(self.root)
        digest = task["reviews"]["imported"][0]["report_digest"]
        task["reviews"]["unknown_acceptances"] = [
            {"batch": "b1", "round": 1, "slot": "zcode", "report_digest": digest,
             "by": "human:x", "at": "now", "quote": "q", "source": "user-declared"}]
        echo = review.acceptance_echo(task)
        self.assertEqual(echo[0]["by"], "human:x")
        skeleton = judgments.skeleton(self.ctx, task)
        events = [item for item in skeleton["unverified"] if item.get("id") == "accept:1:zcode"]
        self.assertEqual(len(events), 1)

    # 49：提取行为等价：paused 与 action_incomplete 的交织顺序不变
    def test_49_paused_action_interleaving(self):
        task = make_task(self.root, complexity="light", verdict=None)
        task["paused"] = True
        task["action"] = {"id": "a1", "state": "applying"}
        ok, code, facts = gates.final_gate_nonstep(self.ctx, task)
        self.assertEqual((ok, code, facts), (False, "WF_ACTION_INCOMPLETE",
                                             {"action": "a1", "state": "applying"}))
        ok, code, facts = gates.final_gate_nonstep(self.ctx, task, ignore_action_id="a1")
        self.assertEqual((ok, code, facts), (False, "WF_SEMANTIC_DECISION",
                                             {"reason": "task still paused or suspended",
                                              "paused": True, "suspended": None}))

    # 50：C3 分支位于 final_gate_nonstep 内（预检在提交前即可看到）
    def test_50_c3_inside_nonstep(self):
        task = make_task(self.root, complexity="light", verdict=None)
        (Path(self.root) / "review/round-1/review-zcode.md").unlink()
        with anchor_patch():
            ok, code, facts = gates.final_gate_nonstep(self.ctx, task)
        self.assertEqual((ok, code), (False, "WF_REVIEW_INVALID"))
        self.assertEqual(facts["reason"], "unverifiable_evidence")

    # 16 的补充：摘要一致但正文结构坏了 → 归因为报告问题，status/预检不抛栈
    def test_16b_unparseable_report_is_attributed(self):
        task = make_task(self.root)
        path = Path(self.root) / "review/round-1/review-zcode.md"
        path.write_text("not a report", encoding="utf-8")
        task["reviews"]["imported"][0]["report_digest"] = records.file_digest(path)
        task["reviews"]["launches"] = [launch(1)]
        with anchor_patch(), \
                mock.patch.object(review, "_current_anchor", return_value=(ANCHOR, {})):
            facts = review.review_report_problems(
                self.ctx, task, round_no=1, launch=launch(1),
                imported=task["reviews"]["imported"], anchor=ANCHOR, proposers={})
            scope = review.repair_scope(self.ctx, task)
        self.assertIn("report_invalid", facts["blockers"])
        self.assertIn("report_invalid", scope["launches"][0]["blocked"])

    # 58：launches[].blocked 只列事实 token
    def test_58_blocked_is_fact_tokens(self):
        task = make_task(self.root, complexity="complex")
        task["reviews"]["launches"] = [launch(1, slots=2)]
        with anchor_patch():
            blocked = review.launch_facts(self.ctx, task)[0]["blocked"]
        self.assertTrue(set(blocked) <= {"report_invalid", "anchor_stale", "implementer_overlap",
                                         "insufficient_reviewers", "material_missing"})
        self.assertFalse([token for token in blocked if ":" in token])

    # 59 + 61：C4 出口与 blocked/decided 一致；重判不设「check 换代」门槛
    def test_59_61_c4_exit_rules(self):
        task = make_task(self.root, complexity="complex", verdict="pass",
                         launches=[launch(1, "codex", slots=2), launch(2, "codex", slots=2)],
                         rounds=[{"round": 1, "verdict": "pass", "check_id": CHECK_ID,
                                  "decided_at": "2026-11-11T00:00:00Z"}])
        write_report(self.root, "review/round-1/review-pi.md")
        task["reviews"]["imported"].append(
            {"round": 1, "slot": "pi", "agent": "pi", "report_path": "review/round-1/review-pi.md",
             "report_digest": records.file_digest(Path(self.root) / "review/round-1/review-pi.md"),
             "anchor": {"check_id": CHECK_ID, "check_anchor": ANCHOR}})
        task["check"]["id"] = "c2"          # check 已换代（旧结论因此不绑定）
        with anchor_patch(anchor="sha256:a2"), \
                mock.patch.object(gates, "check_result_problems", return_value=[]):
            scope = review.repair_scope(self.ctx, task)
        actions = {(item["action"], item["round"]) for item in scope["exits"]}
        self.assertIn(("redecide_round", 1), actions)
        self.assertIn(("relaunch_review", None), actions)


class SkillDocTest(unittest.TestCase):
    """文档类断言（#48、#52–#57 与 #24 的提示口径）。"""

    def text(self, name):
        return (SKILLS / name / "SKILL.md").read_text(encoding="utf-8")

    def test_48_c2_semantics(self):
        body = self.text("wf-review-action")
        self.assertIn("只有 `accepted` 清零", body)
        self.assertIn("不得写 `accepted`", body)

    def test_52_54_review_action_and_repair_loop(self):
        action = self.text("wf-review-action")
        self.assertIn("必须显式传 --round", action)
        self.assertIn("误报也写 `accepted`", action)
        loop = self.text("wf-repair-loop")
        for token in ("rerun_check", "record_disposition", "restore_bytes", "human_release",
                      "resume_inflight", "redecide_round", "await_material", "relaunch_review",
                      "pause_for_human", "abandon_task"):
            self.assertIn(token, loop)
        self.assertIn("inferred", loop)
        self.assertIn("fail 轮重判仍是 fail", loop)
        self.assertIn("你的否定只清 C2", loop)
        self.assertIn("stale_extra", loop)
        self.assertIn("先 `review-launch`", loop)

    def test_53_timing_table(self):
        action = self.text("wf-review-action")
        self.assertIn("处置时机与类型的对应", action)
        self.assertIn("误报 / 重分类", action)
        self.assertIn("已修复", action)

    def test_55_continue_finish_read_scope(self):
        for name in ("wf-continue", "wf-finish"):
            body = self.text(name)
            self.assertIn("repair_scope", body)
            self.assertIn("不要", body)
            self.assertIn("探路", body)

    def test_56_accept_unknown_skill(self):
        body = self.text("wf-review-accept-unknown")
        for needle in ("release_allowed", "降级", "未知 findings", "quote", "cause"):
            self.assertIn(needle, body)

    def test_57_stale_extra_judgement(self):
        self.assertIn("先读这些新报告", self.text("wf-repair-loop"))

    def test_24_c4_hint_accuracy(self):
        loop = self.text("wf-repair-loop")
        self.assertIn("结论写入后再重查会让结论失绑", loop)
        self.assertIn("不是\"发起早就会失绑\"", loop)


if __name__ == "__main__":
    unittest.main()
