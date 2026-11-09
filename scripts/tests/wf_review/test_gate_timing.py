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
    def test_sampling_step_exists_and_is_due_before_archive(self):
        spec = step("task.sampled")
        self.assertIsNotNone(spec, "缺 task.sampled 步骤：抽样没有门禁时点")
        self.assertEqual(spec["due"], "before_archive")

    def test_sampling_step_is_not_due_before_execute_or_check(self):
        dues = [item["due"] for item in [step("task.sampled")]]
        self.assertNotIn("before_execute", dues)
        self.assertNotIn("before_check", dues)

    def test_sampling_projection_comes_from_the_production_writer(self):
        """用生产的写入口造状态，不手搓 dict（P1 的教训：手搓的形状没人写得出）。"""
        from wflib import sampling

        task = {"id": "t1"}
        sampling.freeze(task, {"changed_paths": ["p:a"], "closures": ["f1"]}, seed="s1")
        sampling.record_picks(task, [{"class": "关闭", "event": "f1"}])
        projection = gates.compute_P(None, task, "task.sampled")
        self.assertEqual(projection["seed"], "s1")
        self.assertEqual(projection["picks"][0]["event"], "f1")

    def test_missing_selection_blocks_with_an_exit(self):
        class Ctx:
            root = str(REPO)

            def rule_version(self):
                return 1

        task = {"id": "t1", "sampling": {}}
        ok, code, facts = gates.verify_step(Ctx(), task, "task.sampled")
        self.assertFalse(ok)
        self.assertEqual(code, "WF_SEMANTIC_DECISION")
        self.assertTrue(any("sampling" in str(item) for item in facts.get("exits") or []))

    def test_frozen_selection_satisfies_the_step(self):
        class Ctx:
            root = str(REPO)

            def rule_version(self):
                return 1

        from wflib import sampling

        task = {"id": "t1"}
        sampling.freeze(task, {"changed_paths": ["p:a"]}, seed="s")
        sampling.record_picks(task, [{"class": "关闭", "event": "f1"}])
        ok, code, _facts = gates.verify_step(Ctx(), task, "task.sampled")
        self.assertTrue(ok, code)

    @staticmethod
    def _via_internal(task):
        for name in ("_step_satisfied", "step_satisfied", "_check_step"):
            func = getattr(gates, name, None)
            if func:
                return func(None, task, "task.sampled")
        raise unittest.SkipTest("找不到单步判定入口")


class EscalatedHangsOnlyTheEndingTest(unittest.TestCase):
    def test_escalated_judgment_is_visible_in_gate_source(self):
        source = (REPO / "docs/workflows/wf/payload/lib/wflib/gates.py").read_text(encoding="utf-8")
        self.assertIn('item.get("outcome") == "escalated"', source)
        self.assertIn("最终结论挂起", source)

    def test_escalated_does_not_appear_in_mid_action_gates(self):
        """escalated 只出现在 final_gate（归档口），不进入 before_execute/before_check 的判定。"""
        source = (REPO / "docs/workflows/wf/payload/lib/wflib/gates.py").read_text(encoding="utf-8")
        escalate_index = source.index('item.get("outcome") == "escalated"')
        final_gate_index = source.index("def final_gate")
        self.assertGreater(escalate_index, final_gate_index, "escalated 判定必须落在 final_gate 内")


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
