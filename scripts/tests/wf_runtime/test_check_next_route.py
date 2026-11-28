"""R4：Check pass 的下一跳按复杂度分流（复杂任务先审查，不再固定指向 finish）。"""

import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "docs" / "workflows" / "wf" / "payload" / "lib"))

from wflib import tasks  # noqa: E402


class CheckNextHintTest(unittest.TestCase):
    def test_complex_task_routes_to_review_launch(self):
        hint = tasks.check_next_hint({"plan": {"complexity": "complex"}}, {"result": "pass"})
        self.assertIn("review-launch", hint)

    def test_light_task_routes_to_finish(self):
        hint = tasks.check_next_hint({"plan": {"complexity": "light"}}, {"result": "pass"})
        self.assertIn("finish", hint)
        self.assertNotIn("review-launch", hint)

    def test_finish_hint_names_the_real_command(self):
        """终验主链实测（2026-11-28）：`next_` 只写「finish（wf-finish）」会被读成命令，
        照它跑 `wf help finish` 得到 unknown subcommand。收工是宿主 skill，归档命令是
        `archive`——提示必须同时点名两者，否则读者只能靠猜。"""
        hint = tasks.check_next_hint({"plan": {"complexity": "light"}}, {"result": "pass"})
        self.assertIn("wf-finish", hint)
        self.assertIn("archive", hint)
        self.assertIn("宿主 skill", hint)

    def test_failed_check_routes_to_repair_loop(self):
        hint = tasks.check_next_hint({"plan": {"complexity": "complex"}}, {"result": "fail"})
        self.assertIn("wf-repair-loop", hint)

    def test_in_flight_mixed_materials_hint_points_at_new_round(self):
        """混合基线（还原 + 不一致的正常条目）时，提示不能再让 AI"继续这一轮"。"""
        import tempfile
        import types
        from unittest import mock

        from wflib import review

        task = {
            "id": "t1",
            "plan": {"complexity": "complex"},
            "check": {"result": "pass", "anchor": {"check_anchor": "A"}},
            "reviews": {
                "launches": [{"round": 1, "anchor": {"check_anchor": "A"}}],
                "rounds": [],
                "result": {},
                "imported": [
                    {"round": 1, "slot": "s1", "materials": {"identity": "sha256:" + "a" * 64,
                                                             "restored": True}},
                    {"round": 1, "slot": "s2", "materials": {"identity": "sha256:" + "b" * 64}},
                ],
            },
        }
        ctx = types.SimpleNamespace(root=tempfile.mkdtemp(), debug_threshold=lambda: 3)
        with mock.patch.object(review, "round_materials_identity", return_value="sha256:" + "c" * 64),                 mock.patch.object(review, "materials_identity_state",
                                  return_value={"state": "fixed", "manifest": {}, "drift": []}):
            hint = tasks.check_next_hint(task, {"result": "pass"}, ctx)
        self.assertIn("混在一轮", hint)
        self.assertIn("--restore", hint)

    def test_in_flight_round_survives_old_fail_verdict(self):
        """十四轮 b-1：旧锚点上的 fail 只是历史，不得把在途未判定轮挤成"重新发起"。"""
        task = {
            "plan": {"complexity": "complex"},
            "check": {"result": "pass", "anchor": {"check_anchor": "A"}},
            "reviews": {
                "launches": [
                    {"round": 1, "anchor": {"check_anchor": "A"}},
                    {"round": 2, "anchor": {"check_anchor": "A"}},
                ],
                "rounds": [{"round": 1, "verdict": "fail"}],
                "result": {"verdict": "fail", "anchor": {"check_anchor": "A"}},
            },
        }
        hint = tasks.check_next_hint(task, {"result": "pass"})
        self.assertIn("第 2 轮审查仍在进行", hint)
        self.assertIn("继续这一轮", hint)
        self.assertNotIn("先 review-launch", hint)

    def test_open_blocking_convergence_names_review_launch(self):
        """未关闭 blocking 时，收敛文案必须点名唯一可执行入口 review-launch。

        内容变了旧轮报告即失绑（锚点/材料冻结），`review-decide` 旧轮必被拒；
        2026-11-27 独立审查 F3 实测三处文案都只说"重新发起"，未点命令。
        """
        import types
        from unittest import mock

        from wflib import review

        task = {"id": "t1", "plan": {"complexity": "complex"},
                "check": {"result": "pass", "anchor": {"check_anchor": "A"}},
                "reviews": {"launches": [{"round": 1, "anchor": {"check_anchor": "A"}}],
                            "rounds": [], "result": {"verdict": "fail", "anchor": {"check_anchor": "A"}}}}
        ctx = types.SimpleNamespace(root="/tmp/x", debug_threshold=lambda: 3)
        with mock.patch.object(review, "open_findings",
                               return_value={"blocking": [{"round": 1, "id": "f1"}], "unaddressed": []}):
            hint = tasks.check_next_hint(task, {"result": "pass"}, ctx)
        # 断言必须能区分修复（第二轮复审 F-B）：基础文案本身已含 review-launch，
        # 旧的 blocking_fix 也含"重跑 task-check"；只有新文案独有的措辞才证明改动生效。
        self.assertIn("旧轮不可重判", hint)
        self.assertNotIn("重新发起判定", hint)

    def test_in_flight_round_hinted_without_any_verdict(self):
        task = {
            "plan": {"complexity": "complex"},
            "check": {"result": "pass", "anchor": {"check_anchor": "A"}},
            "reviews": {
                "launches": [{"round": 1, "anchor": {"check_anchor": "A"}}],
                "rounds": [],
                "result": {},
            },
        }
        hint = tasks.check_next_hint(task, {"result": "pass"})
        self.assertIn("第 1 轮审查仍在进行", hint)
        self.assertNotIn("先 review-launch", hint)

    def test_old_fail_without_open_round_still_suggests_launch(self):
        """全部轮次已判定（fail 留史）且无在途轮：仍指向发起新轮。"""
        task = {
            "plan": {"complexity": "complex"},
            "check": {"result": "pass", "anchor": {"check_anchor": "B"}},
            "reviews": {
                "launches": [{"round": 1, "anchor": {"check_anchor": "A"}}],
                "rounds": [{"round": 1, "verdict": "fail"}],
                "result": {"verdict": "fail", "anchor": {"check_anchor": "A"}},
            },
        }
        hint = tasks.check_next_hint(task, {"result": "pass"})
        self.assertIn("review-launch", hint)

    def test_in_flight_round_with_bound_pass_mentions_finish(self):
        """第四组合（pass 绑定当前锚点 + 在途轮）：继续在途轮，并附 finish 提示。

        _binding 走 gates.review_binding(ctx, task)，用最小 ctx 桩 + 补丁固定其结论。
        """
        import types
        from unittest import mock

        stub = types.SimpleNamespace(root="/nonexistent", debug_threshold=lambda: 3)
        task = {
            "id": "t-bind",
            "plan": {"complexity": "complex"},
            "check": {"result": "pass", "anchor": {"check_anchor": "A"}},
            "reviews": {
                "launches": [
                    {"round": 1, "anchor": {"check_anchor": "A"}},
                    {"round": 2, "anchor": {"check_anchor": "A"}},
                ],
                "rounds": [{"round": 1, "verdict": "pass"}],
                "result": {"verdict": "pass", "anchor": {"check_anchor": "A"}},
            },
        }
        with mock.patch("wflib.gates.review_binding", return_value={"binding": True}):
            hint = tasks.check_next_hint(task, {"result": "pass"}, ctx=stub)
        self.assertIn("第 2 轮审查仍在进行", hint)
        # 2026-11-28 终验主链：next_ 里的「finish（wf-finish）」被读成命令（`wf help finish`
        # 报 unknown subcommand）。收工入口是宿主 skill，归档命令是 archive，两处都要点名。
        self.assertIn("判定后即可", hint)
        self.assertIn("wf-finish", hint)
        self.assertIn("archive", hint)

    def test_legacy_result_only_record_not_reported_as_in_flight(self):
        """N5（2026-11-24）：存量 rounds=[] + result=pass——判据走 latest_decision 回退。

        此前本函数直读 rounds[]，同一轮会被说成"仍在进行"，而 review-status 按
        inferred_rounds 判"已判定"——两处对同一记录给出相反答案。
        """
        import types
        from unittest import mock

        stub = types.SimpleNamespace(root="/nonexistent", debug_threshold=lambda: 3)
        task = {
            "id": "t-legacy",
            "plan": {"complexity": "complex"},
            "check": {"result": "pass", "anchor": {"check_anchor": "A"}},
            "reviews": {
                "launches": [{"round": 1, "anchor": {"check_anchor": "A"}}],
                "rounds": [],
                "result": {"verdict": "pass", "round": 1, "anchor": {"check_anchor": "A"}},
            },
        }
        with mock.patch("wflib.gates.review_binding", return_value={"binding": True}):
            hint = tasks.check_next_hint(task, {"result": "pass"}, ctx=stub)
        self.assertNotIn("仍在进行", hint)
        self.assertIn("finish", hint)

    def test_bound_pass_with_open_blocking_does_not_suggest_finish(self):
        """N6（2026-11-24）：pass 绑定当前锚点 + 仍有未关闭 blocking——提示不自相矛盾。

        此前同一条 next_ 会同时出现"可请人直接 finish"与"仍有未关闭 blocking——
        修复 → 重查 → 再判"，而归档门禁会拦下 finish，前半句是必然失败的指引。
        """
        import types
        from unittest import mock

        stub = types.SimpleNamespace(root="/nonexistent", debug_threshold=lambda: 3)
        task = {
            "id": "t-conflict",
            "plan": {"complexity": "complex"},
            "check": {"result": "pass", "anchor": {"check_anchor": "A"}},
            "reviews": {
                "launches": [{"round": 1, "anchor": {"check_anchor": "A"}}],
                "rounds": [{"round": 1, "verdict": "pass"}],
                "result": {"verdict": "pass", "round": 1, "anchor": {"check_anchor": "A"}},
            },
        }
        open_finding = {"finding_id": "f1", "slot": "s1", "round": 2, "severity": "blocking"}
        with mock.patch("wflib.gates.review_binding", return_value={"binding": True}), \
                mock.patch("wflib.review.open_findings",
                           return_value={"blocking": [open_finding], "unaddressed": [],
                                         "unavailable": [], "closed": [], "ambiguous": []}):
            hint = tasks.check_next_hint(task, {"result": "pass"}, ctx=stub)
        self.assertIn("未关闭 blocking", hint)
        self.assertIn("先按处置规则关闭", hint)
        self.assertNotIn("可请人直接 finish", hint)

    def test_light_task_with_open_blocking_fixes_first(self):
        """P1：轻量任务遗留 blocking 时先收口再 finish（finish 必撞归档门禁 C2）。"""
        import types
        from unittest import mock

        stub = types.SimpleNamespace(root="/nonexistent", debug_threshold=lambda: 3)
        open_finding = {"finding_id": "f1", "slot": "s1", "round": 1, "severity": "blocking"}
        with mock.patch("wflib.review.open_findings",
                        return_value={"blocking": [open_finding], "unaddressed": [],
                                      "unavailable": [], "closed": [], "ambiguous": []}):
            hint = tasks.check_next_hint({"plan": {"complexity": "light"}},
                                         {"result": "pass"}, ctx=stub)
        self.assertIn("先按处置规则关闭", hint)
        self.assertIn("task-check", hint)
        self.assertIn("finish", hint)

    def test_in_flight_round_with_binding_and_blocking_defers_finish(self):
        """P1：在途轮 + 旧 pass 绑定 + blocking 未关——不能说"判定后即可 finish"。"""
        import types
        from unittest import mock

        stub = types.SimpleNamespace(root="/nonexistent", debug_threshold=lambda: 3)
        task = {
            "id": "t-inflight-block",
            "plan": {"complexity": "complex"},
            "check": {"result": "pass", "anchor": {"check_anchor": "A"}},
            "reviews": {
                "launches": [
                    {"round": 1, "anchor": {"check_anchor": "A"}},
                    {"round": 2, "anchor": {"check_anchor": "A"}},
                ],
                "rounds": [{"round": 1, "verdict": "pass"}],
                "result": {"verdict": "pass", "anchor": {"check_anchor": "A"}},
            },
        }
        open_finding = {"finding_id": "f1", "slot": "s1", "round": 3, "severity": "blocking"}
        with mock.patch("wflib.gates.review_binding", return_value={"binding": True}), \
                mock.patch("wflib.review.open_findings",
                           return_value={"blocking": [open_finding], "unaddressed": [],
                                         "unavailable": [], "closed": [], "ambiguous": []}):
            hint = tasks.check_next_hint(task, {"result": "pass"}, ctx=stub)
        self.assertIn("才能", hint)
        self.assertIn("wf-finish", hint)
        self.assertNotIn("判定后即可", hint)

    def test_in_flight_hint_mentions_fixed_materials(self):
        """P1-2（2026-11-24）：在途轮提示写明材料按首轮物化固定，不随 Check 重跑改写。"""
        task = {
            "plan": {"complexity": "complex"},
            "check": {"result": "pass", "anchor": {"check_anchor": "A"}},
            "reviews": {
                "launches": [{"round": 1, "anchor": {"check_anchor": "A"}}],
                "rounds": [],
                "result": {},
            },
        }
        hint = tasks.check_next_hint(task, {"result": "pass"})
        self.assertIn("材料按首轮物化固定", hint)


if __name__ == "__main__":
    unittest.main()
