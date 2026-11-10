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


class QualityComparisonTest(unittest.TestCase):
    """v42 §5.3：判断质量对照与依据对照（提示，不算分、不设阈值）。"""

    def _repo(self, archived, current):
        import json, os, tempfile
        from pathlib import Path

        root = tempfile.mkdtemp(prefix="wf-qc-")
        month = Path(root) / ".wf" / "tasks" / "archive" / "2026-11"
        month.mkdir(parents=True)
        for record in archived:
            slot = month / record["id"]
            slot.mkdir()
            (slot / "task.json").write_text(json.dumps(record, ensure_ascii=False), encoding="utf-8")
        (Path(root) / "current.json").write_text(json.dumps(current, ensure_ascii=False), encoding="utf-8")
        return root

    def test_no_history_is_stated_not_faked(self):
        from wflib import judgments

        root = self._repo([], {"id": "t1", "changed_paths": ["pkg/a.py"], "judgments": []})
        lines = judgments.quality_comparison(root, {"id": "t1", "changed_paths": ["pkg/a.py"]})
        self.assertTrue(lines[0].startswith("[判断质量]"), lines)
        self.assertIn("无同类任务可比", lines[0])

    def test_diff_counts_and_basis_side_by_side(self):
        from wflib import judgments

        previous = {"id": "old", "changed_paths": ["pkg/x.py", "pkg/y.py"],
                    "judgments": [{"kind": "关闭", "decision": "d1",
                                   "basis": "v1 全量通过，覆盖 pkg/x.py 与 pkg/y.py 两个文件",
                                   "evidence_refs": ["v:1"]}]}
        current = {"id": "new", "changed_paths": ["pkg/x.py"],
                   "judgments": [{"kind": "关闭", "decision": "d2", "basis": "已通过", "evidence_refs": []},
                                 {"kind": "扩面", "decision": "d3", "basis": "新增文件", "evidence_refs": []}]}
        root = self._repo([previous], current)
        lines = judgments.quality_comparison(root, current)
        text = "\n".join(lines)
        self.assertIn("上次同类任务（old", text)
        self.assertIn("新增 1 类", text)          # 扩面 是本次新增的类别
        self.assertIn("依据变弱 1 条", text)       # 上次有引用、这次没有 → 依据变弱（可核事实）
        self.assertIn("上次 basis：v1 全量通过", text)
        self.assertIn("本次 basis：已通过", text)
        self.assertIn("v:1", text)                 # evidence_refs 对照
        self.assertIn("不算分、不设阈值", text)     # 明确只是提示


class PreviewBlocksTest(unittest.TestCase):
    """§5.3 预览的 13 段：缺的段落要么给事实，要么明说不可得，不能长得像"没有问题"。"""

    def _facts(self, **over):
        base = {"changed_paths": ["pkg/a.py"], "closures": [], "verifications": [], "waived_count": 0,
                "drift_diffs": [], "anchor_parts": ["anchor"], "prefs": {}, "vendor_dirty": [],
                "rejected_unresolved": [], "new_paths": [], "repo_rule_files": [], "unverified": []}
        base.update(over)
        return base

    def test_blocks_present_with_facts(self):
        from wflib import judgments

        task = {"id": "t", "judgments": [{"kind": "扩面", "decision": "d1", "basis": "b1", "refs": []}]}
        text = judgments.render_preview(task, self._facts(
            new_paths=[{"path": "pkg/b.py", "from": "扩面"}],
            repo_rule_files=[".gitignore"],
            unverified=[{"id": "v2", "reason": "无 Windows", "compensation": "CI 矩阵"}],
        ))
        for marker in ("[扩面]", "[规则文件]", "[缺口]", "[未核实]", "[归属]", "[关闭]", "[不变]"):
            self.assertIn(marker, text, marker)
        self.assertIn("pkg/b.py←扩面", text)
        self.assertIn("需你复核", text)      # 规则文件/未核实都要人看
        self.assertIn("[缺口]    无", text)  # 没有缺口要显式写"无"，不是省略

    def test_rounds_validity_reported(self):
        from wflib import judgments

        task = {"id": "t", "judgments": [],
                "reviews": {"launches": [{"round": 1}, {"round": 2, "invalidated": True}]}}
        text = judgments.render_preview(task, self._facts())
        self.assertIn("[有效性]  2 轮报告；作废 1 轮", text)


class EscalatedSupersedeTest(unittest.TestCase):
    """审查 a1：人被回答过的 escalated 判断不能继续挡归档（诚实求助不是死路）。"""

    def test_superseded_escalation_no_longer_blocks(self):
        from wflib import judgments

        task = {"judgments": [
            {"id": "j1", "kind": "关闭", "outcome": "escalated", "escalated_question": "算不算关闭？"},
            {"id": "j2", "kind": "关闭", "outcome": "applied", "supersedes": "j1", "decision": "算"}]}
        self.assertEqual(judgments.pending_escalations(task), [], "回答过的不应再算待决")
        self.assertEqual(len(task["judgments"]), 2, "历史必须保留（append-only）")

    def test_unanswered_escalation_still_blocks(self):
        from wflib import judgments

        task = {"judgments": [{"id": "j1", "kind": "关闭", "outcome": "escalated",
                               "escalated_question": "算不算关闭？"}]}
        self.assertEqual(len(judgments.pending_escalations(task)), 1)

    def test_supersede_only_closes_the_named_item(self):
        from wflib import judgments

        task = {"judgments": [
            {"id": "j1", "kind": "关闭", "outcome": "escalated"},
            {"id": "j2", "kind": "标准变更", "outcome": "escalated"},
            {"id": "j3", "kind": "关闭", "outcome": "applied", "supersedes": "j1"}]}
        pending = judgments.pending_escalations(task)
        self.assertEqual([item["id"] for item in pending], ["j2"], "只关掉被指向的那条")


class SamplingUnevaluatedTest(unittest.TestCase):
    """审查 a2：没评价的抽样不能算成功样本。"""

    def test_unevaluated_pick_is_not_a_sample(self):
        from wflib import sampling

        task = {}
        picks = [{"class": "关闭", "event": "e1"}]
        state = sampling.record_result(task, picks, evaluations={})   # 空评价
        self.assertEqual(len(state["results"]), 1)
        self.assertIs(state["results"][0].get("evaluated"), False)
        history = sampling.history_from_tasks([task])
        self.assertEqual(history["关闭"]["samples"], 0, "未评价不能计入样本")
        self.assertEqual(history["关闭"]["consecutive_ok"], 0)

    def test_evaluated_ok_counts(self):
        from wflib import sampling

        task = {}
        sampling.record_result(task, [{"class": "关闭", "event": "e1"}], evaluations={"关闭:e1": "ok"})
        history = sampling.history_from_tasks([task])
        self.assertEqual(history["关闭"]["samples"], 1)
        self.assertEqual(history["关闭"]["consecutive_ok"], 1)


class ScaleUntrackedLinesTest(unittest.TestCase):
    """审查 a3：未跟踪新文件的内容行数要计入规模。"""

    def test_untracked_file_lines_counted(self):
        import json, os, subprocess, tempfile
        from pathlib import Path
        from types import SimpleNamespace
        from wflib import scale

        root = tempfile.mkdtemp(prefix="wf-scale-")
        subprocess.run(["git", "init", "-q"], cwd=root, check=True)
        subprocess.run(["git", "config", "user.email", "t@example.com"], cwd=root, check=True)
        subprocess.run(["git", "config", "user.name", "t"], cwd=root, check=True)
        (Path(root) / "a.txt").write_text("a\n", encoding="utf-8")
        subprocess.run(["git", "add", "."], cwd=root, check=True)
        subprocess.run(["git", "commit", "-qm", "init"], cwd=root, check=True)
        head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=root, capture_output=True,
                              text=True).stdout.strip()
        (Path(root) / "big.txt").write_text("x\n" * 1000, encoding="utf-8")

        facts = scale.changes_since(SimpleNamespace(root=root), {"baseline_head": head})
        self.assertTrue(facts["available"], facts)
        self.assertEqual(facts["new_files"], 1)
        self.assertEqual(facts["added"], 1000, "未跟踪文件的 1000 行必须计入 added")
        self.assertEqual(facts["net"], 1000)


class SpecStringPathsTest(unittest.TestCase):
    """审查 b-F2：字符串形态的 old_paths/new_paths 必须在入口归一，不能被逐字符迭代。"""

    def test_normalize_turns_strings_into_arrays(self):
        from wflib import spec

        changes = [{"operation": "add", "new_paths": ".wf/spec/rules/calc.md", "content": "x"},
                   {"operation": "rename", "old_paths": "a.md", "new_paths": "b.md"}]
        normalized = spec.normalize_changes(changes)
        self.assertEqual(normalized[0]["new_paths"], [".wf/spec/rules/calc.md"])
        self.assertEqual(normalized[1]["old_paths"], ["a.md"])
        # 关键：不再是无 . 前缀时把字符串拆成单字符（静默垃圾校验的来源）
        self.assertEqual(normalized[1]["new_paths"], ["b.md"],
                         "字符串必须整体作为一个路径，而不是逐字符")

    def test_validate_does_not_iterate_characters(self):
        import tempfile
        from pathlib import Path
        from wflib import spec

        root = tempfile.mkdtemp(prefix="wf-spec-")
        (Path(root) / ".wf" / "spec").mkdir(parents=True)
        (Path(root) / ".wf" / "spec" / "index.md").write_text("---\nschema_version: 1\n---\n", encoding="utf-8")
        changes = [{"operation": "add", "new_paths": "wf/spec/x.md", "content": "---\nschema_version: 1\n---\n"}]
        try:
            spec.validate_changes(root, changes)
        except spec.SpecError as exc:                      # 允许"目录不存在"这类正常拒绝
            self.assertNotIn("empty path", str(exc.facts))
        except Exception as exc:                           # 但不许出 TypeError/单字符垃圾
            self.fail(f"字符串形态不应导致非结构化异常：{exc!r}")


class AskAlwaysAcceptsHumanTest(unittest.TestCase):
    """审查 a1：ask_always 只约束"AI 不得自己定"，不能拒绝人给出的有效答复。"""

    def _entry(self, **over):
        entry = {"kind": "关闭", "decision": "算关闭", "basis": "人判断", "outcome": "applied",
                 "evidence_refs": []}
        entry.update(over)
        return entry

    def test_ai_self_decision_still_rejected_under_ask_always(self):
        from wflib import judgments

        problems = judgments.validate(self._entry(by="ai"), {"prefs": {"关闭": "ask_always"}})
        self.assertTrue(any("ask_always" in item.get("reason", "") for item in problems), problems)

    def test_human_answer_passes_under_ask_always(self):
        from wflib import judgments

        problems = judgments.validate(self._entry(by="human", supersedes="j1"),
                                      {"prefs": {"关闭": "ask_always"}})
        self.assertEqual([item for item in problems if "ask_always" in item.get("reason", "")], [],
                         "人的答复就是该偏好的目的，不能反过来拦住它")


class NoProjectionRecursionTest(unittest.TestCase):
    """审查 a2：open_items 不得回头调用 skeleton（环会让"未核实"算 199 层再返回空）。"""

    def test_open_items_does_not_depend_on_skeleton(self):
        from types import SimpleNamespace

        from wflib import judgments, projection

        called = {"skeleton": 0}
        original = judgments.skeleton

        def boom(*args, **kwargs):
            called["skeleton"] += 1
            raise AssertionError("open_items 不应调用 skeleton（会形成环）")

        judgments.skeleton = boom
        try:
            facts = projection.open_items(SimpleNamespace(root="/tmp", key=lambda required=True: "k"),
                                          {"id": "t", "judgments": []})
        finally:
            judgments.skeleton = original
        self.assertEqual(called["skeleton"], 0)
        self.assertIn("rejected_unresolved", facts)
