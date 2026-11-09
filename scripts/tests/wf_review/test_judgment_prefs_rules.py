"""判「沿用」/ 漂移位置 / 被驳回收口 三条机械规则（D1 采纳的 v42 独有概念）。

防的失败：判「沿用」只写一句"还能用"，不指明标准到底哪一处变了——事后无法复算它是基于哪个差异做的判断。
"""

import os
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "docs" / "workflows" / "wf" / "payload" / "lib"))

from wflib import judgments  # noqa: E402


def facts(drift=None, rejected=None):
    return {"drift_diffs": drift or [],
            "rejected": rejected or [],
            "findings": [], "verifications": [], "acceptance": [], "closures": [],
            "unaddressed_findings": [], "rejected_unresolved": []}


def entry(**overrides):
    base = {"kind": "沿用", "decision": "继续沿用", "basis": "标准只改了措辞", "outcome": "applied",
            "evidence_refs": []}
    base.update(overrides)
    return base


class ReuseNeedsDriftPositionTest(unittest.TestCase):
    def test_reuse_without_d_position_is_rejected(self):
        problems = judgments.validate(entry(), facts())
        self.assertTrue(any("沿用" in p["reason"] for p in problems), problems)

    def test_reuse_with_existing_position_passes(self):
        drift = [{"id": "d:assertions", "where": "assertions"}]
        problems = judgments.validate(entry(evidence_refs=["d:assertions"]), facts(drift))
        self.assertEqual(problems, [])

    def test_position_not_in_drift_is_rejected(self):
        drift = [{"id": "d:assertions", "where": "assertions"}]
        problems = judgments.validate(entry(evidence_refs=["d:paths"]), facts(drift))
        self.assertTrue(any("不在 drift_diffs" in p["reason"] for p in problems), problems)

    def test_other_kinds_do_not_need_a_d_position(self):
        problems = judgments.validate(entry(kind="关闭", evidence_refs=[]), facts())
        self.assertEqual([p for p in problems if "沿用" in p["reason"]], [])


class RejectedNeedsResolutionTest(unittest.TestCase):
    def test_rejected_finding_without_resolution_is_rejected(self):
        problems = judgments.validate(
            entry(kind="关闭", finding="f1", evidence_refs=[]),
            facts(rejected=[{"finding_id": "f1", "decision": "rejected"}]))
        self.assertTrue(any("resolved" in p["reason"] for p in problems), problems)

    def test_rejected_finding_with_resolution_passes(self):
        problems = judgments.validate(
            entry(kind="关闭", finding="f1", resolved_by="human:xzc", evidence_refs=[]),
            facts(rejected=[{"finding_id": "f1", "decision": "rejected"}]))
        self.assertEqual([p for p in problems if "resolved" in p["reason"]], [])


class StandardDriftTest(unittest.TestCase):
    """标准面变了却未判断 → 不能产出 pass；框架只标事实（v42 §4.7）。"""

    def test_only_standard_parts_count(self):
        from wflib import review

        diffs = [{"id": "d:spec_versions", "where": "spec_versions"},
                 {"id": "d:assertions_digest", "where": "assertions_digest"},
                 {"id": "d:paths_digest", "where": "paths_digest"},
                 {"id": "d:baseline_digest", "where": "baseline_digest"}]
        got = [item["where"] for item in review.standard_drift_positions(diffs)]
        self.assertEqual(got, ["spec_versions", "assertions_digest"])

    def test_no_standard_change_returns_empty(self):
        from wflib import review

        self.assertEqual(review.standard_drift_positions(
            [{"id": "d:paths_digest", "where": "paths_digest"}]), [])

    def test_gate_blocks_without_judgment(self):
        from wflib import check as check_mod, review

        class Ctx:
            root = str(REPO)

        original = check_mod.anchor_parts
        check_mod.anchor_parts = lambda ctx, task, check=None: {"spec_versions": [{"path": "a", "digest": "2"}],
                                                               "paths_digest": "p"}
        try:
            task = {"id": "t1", "judgments": [],
                    "check": {"anchor": {"parts": {"spec_versions": [{"path": "a", "digest": "1"}],
                                                  "paths_digest": "p"}}}}
            with self.assertRaises(Exception) as caught:
                review.standard_drift_gate(Ctx(), task)
            self.assertIn("WF_SEMANTIC_DECISION", str(caught.exception))

            task_with_judgment = dict(task, judgments=[{"kind": "标准变更", "decision": "接受"}])
            positions = review.standard_drift_gate(Ctx(), task_with_judgment)
            self.assertEqual([p["where"] for p in positions], ["spec_versions"])
        finally:
            check_mod.anchor_parts = original

    def test_gate_passes_when_nothing_on_the_standard_face_changed(self):
        from wflib import check as check_mod, review

        class Ctx:
            root = str(REPO)

        original = check_mod.anchor_parts
        check_mod.anchor_parts = lambda ctx, task, check=None: {"paths_digest": "p2"}
        try:
            task = {"id": "t1", "judgments": [],
                    "check": {"anchor": {"parts": {"paths_digest": "p1"}}}}
            self.assertEqual(review.standard_drift_gate(Ctx(), task), [])
        finally:
            check_mod.anchor_parts = original


class PreferenceTest(unittest.TestCase):
    """偏好只在本机：`ask_always` 强制交人；`ai_decides` 下越界升级必须写 why（v42 §5.3）。"""

    def test_prefs_live_in_runtime_and_round_trip(self):
        import tempfile

        with tempfile.TemporaryDirectory() as root:
            path = judgments.prefs_path(root)
            self.assertIn(os.path.join(".wf", ".runtime"), path)
            judgments.set_pref(root, "标准变更", "ask_always")
            self.assertEqual(judgments.load_prefs(root), {"标准变更": "ask_always"})
            self.assertTrue(Path(path).is_file())

    def test_unknown_kind_or_value_is_refused(self):
        import tempfile

        with tempfile.TemporaryDirectory() as root:
            with self.assertRaises(ValueError):
                judgments.set_pref(root, "不存在的类", "ask_always")
            with self.assertRaises(ValueError):
                judgments.set_pref(root, "关闭", "always")

    def test_ask_always_forces_escalation(self):
        facts = dict(base_facts(), prefs={"关闭": "ask_always"})
        problems = judgments.validate(entry(kind="关闭", evidence_refs=[]), facts)
        self.assertTrue(any("ask_always" in p["reason"] for p in problems), problems)
        ok = judgments.validate(entry(kind="关闭", outcome="escalated", escalated_question="该不该修？",
                                     evidence_refs=[]), facts)
        self.assertEqual([p for p in ok if "ask_always" in p["reason"]], [])

    def test_ai_decides_escalation_needs_why(self):
        facts = dict(base_facts(), prefs={"关闭": "ai_decides"})
        problems = judgments.validate(entry(kind="关闭", outcome="escalated",
                                           escalated_question="该不该修？", evidence_refs=[]), facts)
        self.assertTrue(any("why" in p["reason"] for p in problems), problems)
        ok = judgments.validate(entry(kind="关闭", outcome="escalated", escalated_question="该不该修？",
                                     why="缺乏该模块的历史约定", evidence_refs=[]), facts)
        self.assertEqual([p for p in ok if "why" in p["reason"]], [])


def base_facts(**extra):
    data = {"drift_diffs": [], "rejected": [], "findings": [], "verifications": [],
            "acceptance": [], "closures": [], "unaddressed_findings": [], "rejected_unresolved": []}
    data.update(extra)
    return data


class BrokenPatternTest(unittest.TestCase):
    """glob 展开为空 = 那份确认不可用，不能算覆盖（v42 同型：位置存不存在是事实）。"""

    def test_pattern_matching_nothing_is_not_coverage(self):
        import tempfile

        from wflib import authorize

        with tempfile.TemporaryDirectory() as root:
            Path(root, "src").mkdir()
            Path(root, "src/x.py").write_text("x", encoding="utf-8")
            authorize.record_authorization(root, "expand",
                                           {"choice": "expand", "paths": ["src/**", "nowhere/**"]})
            covered, uncovered = authorize.covers(root, "expand", ["src/x.py"], root=root)
        self.assertFalse(covered, "含空展开的确认不能算覆盖")

    def test_all_patterns_resolve_means_covered(self):
        import tempfile

        from wflib import authorize

        with tempfile.TemporaryDirectory() as root:
            Path(root, "src").mkdir()
            Path(root, "src/x.py").write_text("x", encoding="utf-8")
            authorize.record_authorization(root, "expand", {"choice": "expand", "paths": ["src/**"]})
            covered, uncovered = authorize.covers(root, "expand", ["src/x.py"], root=root)
        self.assertTrue(covered)
        self.assertEqual(uncovered, [])


class PathListTest(unittest.TestCase):
    """路径清单只有一处实现：字符串/数组两种形态都接受，非法类型给结构化拒绝（审查 N1）。"""

    def test_string_array_and_none(self):
        from wflib import paths

        self.assertEqual(paths.path_list({"p": ".wf/spec/a.md"}, "p"), [".wf/spec/a.md"])
        self.assertEqual(paths.path_list({"p": "a.md, b.md"}, "p"), ["a.md", "b.md"])
        self.assertEqual(paths.path_list({"p": ["a.md", "b.md"]}, "p"), ["a.md", "b.md"])
        self.assertEqual(paths.path_list({}, "p"), [])

    def test_bad_type_raises_invalid_path(self):
        from wflib import paths

        with self.assertRaises(paths.InvalidPath):
            paths.path_list({"p": 42}, "p")

    def test_no_raw_concatenation_remains(self):
        """调用链上不得再出现裸拼接（三处历史炸点都收敛到 paths.path_list）。"""
        for name in ("spec.py", "tasks.py"):
            source = (REPO / "docs" / "workflows" / "wf" / "payload" / "lib" / "wflib" / name).read_text(encoding="utf-8")
            self.assertNotIn('(change.get("old_paths") or []) + (change.get("new_paths") or [])', source)
