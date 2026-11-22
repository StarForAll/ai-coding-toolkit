"""门禁时点：抽样只在归档前、escalated 只挂起最终结论（v42 §5.3 / §0.2）。

防的失败：抽样被跳过就直接收工；一条"判断不了"把整个流程冻住，连中途动作都做不了。
"""

import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "docs" / "workflows" / "wf" / "payload" / "lib"))

from wflib import gates  # noqa: E402


def step(name):
    for identifier, mode, condition, due in gates.TASK_STEP_SPECS:
        if identifier == name:
            return {"mode": mode, "condition": condition, "due": due}
    return None


class SamplingTimingTest(unittest.TestCase):
    """2026-11-21 降档：task.sampled 不再是归档硬门禁（试点期手段，见 gates.py 注释）。

    保留的断言改为：步骤已从 SPECS 移除（不阻断归档）、投影仍可供提示消费、
    verify_step 对残留调用防御性拒绝（触发即测试迁移有遗漏）。
    """

    def test_sampling_step_removed_from_required_specs(self):
        spec = step("task.sampled")
        self.assertIsNone(spec, "task.sampled 不应是 required 步骤（2026-11-21 降档为试点期提示）")

    def test_sampling_not_in_rule_class_steps(self):
        self.assertNotIn("task.sampled", gates.RULE_CLASS_STEPS)

    def test_sampling_selection_is_the_single_read_surface(self):
        """提示消费（check_next_hint / 收工预览 facts）唯一读取面是 sampling.selection。"""
        from wflib import sampling

        task = {"id": "t1"}
        sampling.freeze(task, {"changed_paths": ["p:a"], "closures": ["f1"]}, seed="s1")
        sampling.record_picks(task, [{"class": "关闭", "event": "f1"}])
        selection = sampling.selection(task)
        self.assertEqual(selection["seed"], "s1")
        self.assertEqual(selection["picks"][0]["event"], "f1")

    def test_compute_P_rejects_unknown_step(self):
        """task.sampled 已不在步骤体系：compute_P 对未知步骤 raise KeyError（不留死分支）。"""
        with self.assertRaises(KeyError):
            gates.compute_P(None, {"id": "t1"}, "task.sampled")

    def test_verify_step_rejects_unregistered_step(self):
        """verify_step 对不在 HANDLERS 的步骤拒绝（task.sampled 已移除，无专属分支）。"""
        class Ctx:
            root = str(REPO)

            def rule_version(self):
                return 1

        task = {"id": "t1", "sampling": {}}
        ok, code, _facts = gates.verify_step(Ctx(), task, "task.sampled")
        self.assertFalse(ok)
        self.assertEqual(code, "WF_RECORD_INVALID")

    def test_check_next_hint_mentions_pilot_sampling_when_no_picks(self):
        from wflib import tasks as tasks_mod

        task = {"id": "t1", "plan": {"complexity": "light"}}
        hint = tasks_mod.check_next_hint(task, {"result": "pass"})
        self.assertIn("sampling pick", hint)
        # 有 picks 时不再提示
        from wflib import sampling

        sampling.record_picks(task, [{"class": "关闭", "event": "f1"}])
        hint2 = tasks_mod.check_next_hint(task, {"result": "pass"})
        self.assertNotIn("sampling pick", hint2)

    def test_failed_check_hint_has_no_sampling_note(self):
        from wflib import tasks as tasks_mod

        hint = tasks_mod.check_next_hint({"plan": {"complexity": "light"}}, {"result": "fail"})
        self.assertNotIn("sampling pick", hint)


class EscalatedHangsOnlyTheEndingTest(unittest.TestCase):
    """escalated 只挂在**归档口**（final_gate），不冻结中途动作（v42 §5.3）。

    断言锚**行为**，不锚文件排版：此前用"源码里某个字符串出现在 `def final_gate` 之后"
    来判位置，重构把判定抽成 helper 就假红——断言写的是实现布局，不是契约。
    """

    def test_pending_escalations_is_the_single_concept(self):
        from wflib import judgments

        task = {"judgments": [{"id": "j1", "kind": "关闭", "outcome": "escalated"}]}
        self.assertEqual([item["id"] for item in judgments.pending_escalations(task)], ["j1"])

    def test_only_the_ending_gate_consults_escalations(self):
        import inspect

        from wflib import judgments

        # ⑥ 把归档口的 nonstep 段提取为 `final_gate_nonstep`（同一实现，供 D4 预检复用）。
        # 这里断言的是"归档口这条链"读 escalations，不是某个函数体的排版。
        ending_gate = inspect.getsource(gates.final_gate) + inspect.getsource(gates.final_gate_nonstep)
        self.assertIn("pending_escalations(", ending_gate,
                      "归档口必须按当前有效判断算待决")
        for name in ("evaluate", "_step_satisfied", "step_satisfied", "_check_step"):
            func = getattr(gates, name, None)
            if func is None:
                continue
            self.assertNotIn("escalated", inspect.getsource(func),
                             f"{name} 属中途动作判定，不得因 escalated 而挂起")


class UnchangedFactsTest(unittest.TestCase):
    """预览要照列「不影响的不变」，否则人只看见变化（v42 §5.3）。"""

    def test_preview_lists_unchanged_parts(self):
        from wflib import judgments

        facts = {"drift_diffs": [{"id": "d:spec_versions", "where": "spec_versions"}],
                 "anchor_parts": ["spec_versions", "paths_digest", "content_digest"],
                 "changed_paths": [], "closures": [], "unaddressed_findings": [],
                 "verifications": [], "waived_count": 0, "vendor_dirty": []}
        text = judgments.render_preview({"id": "t1"}, facts)
        self.assertIn("[不变]", text)
        self.assertIn("paths_digest", text)
        self.assertNotIn("spec_versions、", text.split("[不变]")[1].split("\n")[0])

    def test_no_parts_means_no_line(self):
        from wflib import judgments

        text = judgments.render_preview({"id": "t1"}, {"anchor_parts": [], "changed_paths": [],
                                                      "closures": [], "unaddressed_findings": [],
                                                      "verifications": [], "waived_count": 0})
        self.assertNotIn("[不变]", text)


class FrameworkDoesNotVerifyTest(unittest.TestCase):
    """框架不检测声明真伪：只要求"声明 + 人复核"，不假装能验证（v42 已声明边界）。"""

    def test_false_declaration_still_needs_only_human_recheck(self):
        from wflib import review

        lifted = [{"finding": "f1", "assertion_ref": "spec:x", "rule": "spec:x"}]
        # 声明内容真假框架不核：只要有人复核过就放行
        self.assertEqual(review.broken_reference_problems(
            lifted, [{"finding_id": "f1", "recheck_by": "human:xzc"}]), [])

    def test_no_human_recheck_is_rejected_even_with_declaration(self):
        from wflib import review

        lifted = [{"finding": "f1", "assertion_ref": "spec:x", "rule": "spec:x"}]
        self.assertTrue(review.broken_reference_problems(lifted, [{"finding_id": "f1", "recheck_by": "ai"}]))


class SemanticTriggerTest(unittest.TestCase):
    """K4c 的触发面：只看实质摘要，机械纠错（改排版）不触发。"""

    def test_assertion_index_compares_rule_digest_not_whole_file(self):
        """规则摘要取自 spec 的实质字段（check/clauses），不是整文件摘要。"""
        check_src = (REPO / "docs/workflows/wf/payload/lib/wflib/check.py").read_text(encoding="utf-8")
        review_src = (REPO / "docs/workflows/wf/payload/lib/wflib/review.py").read_text(encoding="utf-8")
        self.assertIn('spec_mod.rule_digest(info.get("metadata") or {})', check_src)
        self.assertIn("curation_changed(before", review_src)

    def test_formatting_only_change_does_not_change_rule_digest(self):
        from wflib import spec

        before = {"schema_version": 1, "status": "active", "author": "human", "verified_at": "2026-11-09",
                  "counterexample": "反例", "check": "grep -n x",
                  "clauses": [{"id": "c1", "status": "active", "statement": "条件一"}]}
        # 同一内容、不同键序/新增无关键 → 摘要不变（机械纠错不触发标准变更）
        after = {"clauses": [{"statement": "条件一", "status": "active", "id": "c1"}],
                 "check": "grep -n x", "counterexample": "反例", "verified_at": "2026-11-09",
                 "author": "human", "status": "active", "schema_version": 1, "note": "无关备注"}
        self.assertEqual(spec.rule_digest(before), spec.rule_digest(after),
                         "键序或无关字段不得改变实质摘要")


class SkeletonPoolsTest(unittest.TestCase):
    """扩面/标准变更两类事件池必须能从记录派生（此前硬编码 []，抽样永远抽不到它们）。"""

    def test_events_of_reads_fix_scope_and_standard_changes(self):
        from wflib import sampling

        pool = sampling.events_of({"changed_paths": ["p:a"], "closures": ["f1"],
                                   "fix_scope": [{"paths": ["src/x"]}],
                                   "standard_changes": [{"decision": "改了"}]})
        self.assertIn("扩面", pool)
        self.assertIn("标准变更", pool)

    def test_skeleton_derives_them_from_judgments(self):
        source = (REPO / "docs/workflows/wf/payload/lib/wflib/judgments.py").read_text(encoding="utf-8")
        self.assertIn('item.get("kind") == "扩面"', source)
        self.assertIn('item.get("kind") == "标准变更"', source)
        self.assertNotIn('"fix_scope": [],', source)
        self.assertNotIn('"standard_changes": [],', source)

    def test_repo_rule_files_come_from_protocol(self):
        source = (REPO / "docs/workflows/wf/payload/lib/wflib/judgments.py").read_text(encoding="utf-8")
        self.assertIn("authorize_mod.repo_rule_paths", source)


class UnavailableIsNotEmptinessTest(unittest.TestCase):
    """锚点算不出来时，预览必须说「清单不可得」，不能长得像「没有不变项」（审查 a.P2）。"""

    def test_none_renders_explicit_unavailable(self):
        from wflib import judgments

        text = judgments.render_preview({"id": "t1"}, {"anchor_parts": None, "changed_paths": [],
                                                      "closures": [], "unaddressed_findings": [],
                                                      "verifications": [], "waived_count": 0})
        self.assertIn("不可得", text)
        self.assertNotIn("[不变]    0 项", text)

    def test_empty_list_is_still_silent(self):
        from wflib import judgments

        text = judgments.render_preview({"id": "t1"}, {"anchor_parts": [], "changed_paths": [],
                                                      "closures": [], "unaddressed_findings": [],
                                                      "verifications": [], "waived_count": 0})
        self.assertNotIn("不可得", text)


class CliEntryPointsTest(unittest.TestCase):
    """P2：评价/人已看过/偏好都必须有 CLI 入口，否则强化期与降级门槛永远空转。"""

    def test_sampling_evaluate_and_reviewed_exist(self):
        from wflib import cli

        source = (REPO / "docs/workflows/wf/payload/lib/wflib/cli.py").read_text(encoding="utf-8")
        self.assertIn('sub == "evaluate"', source)
        self.assertIn('sub == "reviewed"', source)
        self.assertIn("sampling_mod.record_result", source)
        self.assertIn("sampling_mod.mark_reviewed", source)

    def test_prefs_command_exists(self):
        from wflib import cli

        self.assertIn("prefs", cli.COMMANDS)
        self.assertIn("prefs", cli.COMMAND_HELP)
        source = (REPO / "docs/workflows/wf/payload/lib/wflib/cli.py").read_text(encoding="utf-8")
        self.assertIn("judgments_mod.set_pref", source)


class PreferenceLineTest(unittest.TestCase):
    """预览要显示偏好（只在本机），否则"每次都问你"与"自己定"对人不可见。"""

    def test_prefs_are_shown(self):
        from wflib import judgments

        text = judgments.render_preview({"id": "t1"}, {"prefs": {"标准变更": "ask_always"},
                                                      "anchor_parts": [], "changed_paths": [],
                                                      "closures": [], "unaddressed_findings": [],
                                                      "verifications": [], "waived_count": 0})
        self.assertIn("[偏好]", text)
        self.assertIn("标准变更=ask_always", text)

    def test_no_prefs_means_no_line(self):
        from wflib import judgments

        text = judgments.render_preview({"id": "t1"}, {"prefs": {}, "anchor_parts": [],
                                                      "changed_paths": [], "closures": [],
                                                      "unaddressed_findings": [], "verifications": [],
                                                      "waived_count": 0})
        self.assertNotIn("[偏好]", text)


class DriftUnavailableTest(unittest.TestCase):
    """锚点算不出来时，门禁必须交人，不能折叠成"没有漂移"（审查 a-P1）。"""

    def test_missing_parts_is_a_decision_not_a_pass(self):
        from wflib import review

        class Ctx:
            root = str(REPO)

        with self.assertRaises(Exception) as caught:
            review.standard_drift_gate(Ctx(), {"id": "t1", "check": {"anchor": {}}})
        self.assertIn("WF_SEMANTIC_DECISION", str(caught.exception))

    def test_anchor_error_is_a_decision(self):
        from wflib import check as check_mod, review

        class Ctx:
            root = str(REPO)

        original = check_mod.anchor_parts
        check_mod.anchor_parts = lambda *a, **k: (_ for _ in ()).throw(RuntimeError("boom"))
        try:
            with self.assertRaises(Exception) as caught:
                review.standard_drift_gate(Ctx(), {"id": "t1",
                                                   "check": {"anchor": {"parts": {"spec_versions": []}}}})
            self.assertIn("WF_SEMANTIC_DECISION", str(caught.exception))
        finally:
            check_mod.anchor_parts = original


class SubjectAndWriterTest(unittest.TestCase):
    """多路径 subject 允许空格分隔；写权空闲未持有要给出可执行出口（审查 b-N2/N3）。"""

    def test_subject_accepts_whitespace_separated_paths(self):
        from wflib import tasks

        self.assertEqual(tasks._subject_paths("src/a.py tests/b.py"), ["src/a.py", "tests/b.py"])
        self.assertEqual(tasks._subject_paths("src/a.py, tests/b.py"), ["src/a.py", "tests/b.py"])

    def test_idle_writer_raises_with_acquire_exit(self):
        source = (REPO / "docs/workflows/wf/payload/lib/wflib/cli.py").read_text(encoding="utf-8")
        self.assertIn("先取得写权", source)
        # 2026-11-21：writer 不收 --task（对象来自绑定）；出口文案改为裸 `writer acquire`
        self.assertIn("writer acquire", source)
        self.assertNotIn("writer acquire --task", source)


class AttributionConsumptionTest(unittest.TestCase):
    """`task-attribute` 登记过的归属要能解除 external pending（否则出口 2 走不到终点）。"""

    def test_attribution_decision_counts_as_checked(self):
        from wflib import check

        task = {"attribution": {"decisions": [{"commit": "abcdef1234"}]}}
        self.assertTrue(check._external_checked({"commit": "abcdef1234"}, [], task))
        self.assertFalse(check._external_checked({"commit": "9999999"}, [], task))


class SpecPathListTest(unittest.TestCase):
    """spec-update 的 old_paths/new_paths：接受数组或分隔字符串，非法类型给结构化拒绝（审查 b-R1）。"""

    def test_string_is_split(self):
        from wflib import spec

        self.assertEqual(spec._path_list({"new_paths": ".wf/spec/a.md"}, "new_paths"),
                         [".wf/spec/a.md"])
        self.assertEqual(spec._path_list({"new_paths": ".wf/spec/a.md, .wf/spec/b.md"}, "new_paths"),
                         [".wf/spec/a.md", ".wf/spec/b.md"])

    def test_array_is_kept(self):
        from wflib import spec

        self.assertEqual(spec._path_list({"old_paths": ["a.md", "b.md"]}, "old_paths"), ["a.md", "b.md"])

    def test_bad_type_is_a_structured_rejection(self):
        from wflib import spec

        with self.assertRaises(Exception) as caught:
            spec._path_list({"new_paths": 42}, "new_paths")
        self.assertIn("WF_PATH_INVALID", str(caught.exception))
