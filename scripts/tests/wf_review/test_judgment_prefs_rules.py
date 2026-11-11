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

        task = {"id": "t1", "entry_snapshot": {"touch_paths": ["pkg/a.py"]}, "judgments": []}
        root = self._repo([], task)
        lines = judgments.quality_comparison(root, task)
        self.assertTrue(lines[0].startswith("[判断质量]"), lines)
        self.assertIn("无同类任务可比", lines[0])

    def test_diff_counts_and_basis_side_by_side(self):
        from wflib import judgments

        previous = {"id": "old", "entry_snapshot": {"touch_paths": ["pkg/x.py", "pkg/y.py"]},
                    "judgments": [{"kind": "关闭", "decision": "d1",
                                   "basis": "v1 全量通过，覆盖 pkg/x.py 与 pkg/y.py 两个文件",
                                   "evidence_refs": ["v:1"]}]}
        current = {"id": "new", "entry_snapshot": {"touch_paths": ["pkg/x.py"]},
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


class PreviewRealFactsTest(unittest.TestCase):
    """审查第三轮：预览必须消费**真实**记录字段，否则"代码在、永不生效"。"""

    def test_unverified_comes_from_acceptance_results(self):
        from types import SimpleNamespace

        from wflib import judgments

        task = {"id": "t", "judgments": [],
                "check": {"acceptance_results": [{"acceptance_id": "a1", "conclusion": "failed"}]}}
        facts = judgments.skeleton(SimpleNamespace(root="/tmp", key=lambda required=True: "k"), task)
        ids = [item.get("id") for item in facts["unverified"]]
        self.assertIn("a1", ids, "必需的失败验收项必须出现在预览事实里")

    def test_resolved_unverified_is_dropped(self):
        from types import SimpleNamespace

        from wflib import judgments

        task = {"id": "t", "judgments": [],
                "check": {"acceptance_results": [{"acceptance_id": "a1", "conclusion": "failed"}]},
                "unverified_resolutions": {"a1": {"kind": "narrow", "reason": "无环境"}}}
        facts = judgments.skeleton(SimpleNamespace(root="/tmp", key=lambda required=True: "k"), task)
        self.assertEqual([item for item in facts["unverified"] if item.get("id") == "a1"], [])

    def test_scope_filtered_new_paths(self):
        """面内新增不进 [扩面]；批准面之外的新增才进（审查 a3/b1）。"""
        import subprocess, tempfile
        from pathlib import Path
        from types import SimpleNamespace
        from wflib import judgments

        root = tempfile.mkdtemp(prefix="wf-scope-")
        subprocess.run(["git", "init", "-q"], cwd=root, check=True)
        for key, value in (("user.email", "t@e.com"), ("user.name", "t")):
            subprocess.run(["git", "config", key, value], cwd=root, check=True)
        (Path(root) / "pkg").mkdir()
        (Path(root) / "pkg" / "a.py").write_text("a\n", encoding="utf-8")
        subprocess.run(["git", "add", "."], cwd=root, check=True)
        subprocess.run(["git", "commit", "-qm", "i"], cwd=root, check=True)
        head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=root,
                              capture_output=True, text=True).stdout.strip()

        (Path(root) / "pkg" / "new_in.py").write_text("x\n", encoding="utf-8")   # 面内新增
        (Path(root) / "other").mkdir()
        (Path(root) / "other" / "new_out.py").write_text("y\n", encoding="utf-8")  # 面外新增
        subprocess.run(["git", "add", "."], cwd=root, check=True)

        task = {"id": "t", "baseline_head": head,
                "entry_snapshot": {"touch_paths": ["pkg/**"]}}
        ctx = SimpleNamespace(root=root, key=lambda required=True: "k")
        paths = [path for path, _source in judgments._new_paths(ctx, task)]
        self.assertIn("other/new_out.py", paths)
        self.assertNotIn("pkg/new_in.py", paths, "批准面内的新增不算扩面")


class HumanAttestationTest(unittest.TestCase):
    """审查 A4（乙口径）：四处"只能由人给出"的事实都不能只靠字符串前缀。"""

    def _file(self, payload):
        import json, tempfile
        from pathlib import Path

        path = Path(tempfile.mkdtemp(prefix="wf-att-")) / "attest.json"
        path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        return str(path)

    def test_rejects_ai_self_assertion(self):
        from wflib import attestation

        problems = attestation.problems_of({"by": "ai", "at": "t", "quote": "q",
                                            "source": "user-declared"}, action="waive")
        self.assertTrue(any("human:" in item["reason"] for item in problems))

    def test_rejects_missing_fields(self):
        from wflib import attestation

        problems = attestation.problems_of({"by": "human:xzc"}, action="waive")
        self.assertEqual({item.get("field") for item in problems}, {"at", "quote", "source"})

    def test_accepts_human_declaration_and_stamps_digest(self):
        from wflib import attestation

        path = self._file({"by": "human:xzc", "at": "2026-11-10T00:00:00Z",
                           "quote": "我确认这些文件由我处置", "source": "user-declared"})
        payload, digest, problems = attestation.load(path, action="waive")
        self.assertEqual(problems, [])
        self.assertTrue(str(digest).startswith("sha256:"))
        stamped = attestation.stamp(payload, digest)
        self.assertEqual(stamped["by"], "human:xzc")
        self.assertEqual(stamped["attestation_digest"], digest)

    def test_missing_file_is_a_refusal_with_exits(self):
        from wflib import attestation

        payload, digest, problems = attestation.load(None, action="sampling.reviewed")
        self.assertIsNone(payload)
        self.assertTrue(any(item.get("exits") for item in problems))


class K4bClosureChainTest(unittest.TestCase):
    """第十一轮审查 F1/F2 的回归：关闭链必须真的能用。

    `reviews.imported[]` 只持久化 round/slot/report_path/report_digest/anchor（**没有 findings**），
    所以提出者必须**重解析报告**。此前从记录里读 `entry["findings"]` 恒为空 →
    任何带真实 finding_id 的处置都被判"不属任何已导入报告"，K4b 关闭整条走不通。
    """

    REPORT = """---
status: done
---

<!-- wf-review-report:v1 -->

```json
{"protocol": "wf-review-v1", "task-id": "t", "round": 1, "reviewer-id": "slot-a",
 "source-cli": "codex", "review-time": "2026-11-10T00:00:00Z", "review-focus": "x",
 "check-anchor": {"check_id": "c1", "check_anchor": "sha256:0"}, "read-scope": ["pkg/**"],
 "excluded-scope": ["node_modules/**", ".env", "*.pem", ".codex/**", "../**", ".wf/tasks/**"],
 "scope-exceptions": [], "axes": {"acceptance": {"conclusion": "fail", "basis": "b"}},
 "findings": [{"id": "F1", "severity": "blocker", "axis": "acceptance", "summary": "真失败"}],
 "verdict": "fail"}
```
"""

    def _fixture(self):
        import json, tempfile
        from pathlib import Path
        from types import SimpleNamespace
        from wflib import records

        root = tempfile.mkdtemp(prefix="wf-k4b-")
        rel = "review/report.md"
        path = Path(root) / rel
        path.parent.mkdir(parents=True)
        path.write_text(self.REPORT, encoding="utf-8")
        entry = {"round": 1, "slot": "slot-a", "report_path": rel,
                 "report_digest": records.file_digest(str(path)), "agent": "codex"}
        ctx = SimpleNamespace(root=root, key=lambda required=True: "k")
        return ctx, entry

    def test_proposers_come_from_reparsed_report(self):
        from wflib import review

        ctx, entry = self._fixture()
        proposers, unreadable = review.proposers_from_imported(ctx, [entry])
        self.assertEqual(proposers, {"F1": "codex"})
        self.assertEqual(unreadable, [])

    def test_disposition_with_real_finding_id_is_accepted(self):
        from wflib import review

        ctx, entry = self._fixture()
        proposers, unreadable = review.proposers_from_imported(ctx, [entry])
        problems = review.dispositions_problems(
            [{"finding_id": "F1", "decision": "accepted", "reason": "已修", "recheck_by": "pi"}],
            proposers, unreadable=unreadable)
        self.assertEqual(problems, [])

    def test_self_review_still_rejected(self):
        from wflib import review

        ctx, entry = self._fixture()
        proposers, unreadable = review.proposers_from_imported(ctx, [entry])
        problems = review.dispositions_problems(
            [{"finding_id": "F1", "decision": "accepted", "reason": "已修", "recheck_by": "codex"}],
            proposers, unreadable=unreadable)
        self.assertTrue(any("自证" in item.get("reason", "") for item in problems))

    def test_unknown_finding_still_rejected(self):
        from wflib import review

        ctx, entry = self._fixture()
        proposers, unreadable = review.proposers_from_imported(ctx, [entry])
        problems = review.dispositions_problems(
            [{"finding_id": "F9", "decision": "accepted", "reason": "x", "recheck_by": "pi"}],
            proposers, unreadable=unreadable)
        self.assertTrue(any("不属任何已导入报告" in item.get("reason", "") for item in problems))

    def test_unreadable_report_gives_accurate_exit(self):
        from wflib import review

        ctx, entry = self._fixture()
        import os
        os.remove(os.path.join(ctx.root, entry["report_path"]))
        proposers, unreadable = review.proposers_from_imported(ctx, [entry])
        self.assertTrue(unreadable)
        problems = review.dispositions_problems(
            [{"finding_id": "F1", "decision": "accepted", "reason": "已修", "recheck_by": "pi"}],
            proposers, unreadable=unreadable)
        self.assertTrue(any("无法核对" in item.get("reason", "") for item in problems),
                        "不可读不能报成'不存在'")


class ImportEvidenceIdentityTest(unittest.TestCase):
    """第十三轮 a-1：证据身份不可替换。

    "删掉报告 → 导入内容不同的另一份"曾可直接替换证据：旧 blocking 消失，
    既无 disposition 也无人裁放行（实测可复现）。导入端必须要求**幂等重入**。
    """

    def test_reimport_with_different_digest_is_rejected(self):
        from wflib import review

        reviews = {"imported": [{"round": 1, "slot": "s1", "report_path": "a.md",
                                 "report_digest": "sha256:OLD"}]}
        recorded = reviews["imported"][0]
        incoming = "sha256:NEW"
        blocked = recorded.get("report_digest") not in (None, incoming)
        self.assertTrue(blocked, "已导入记录与传入摘要不同 → 必须拒绝（证据身份不可替换）")

    def test_idempotent_reimport_is_allowed(self):
        from wflib import review

        recorded = {"round": 1, "slot": "s1", "report_digest": "sha256:SAME"}
        incoming = "sha256:SAME"
        self.assertFalse(recorded.get("report_digest") not in (None, incoming))


class StagedDiscoveryTest(unittest.TestCase):
    """第十四轮 a：发现模式下"已完成未导入"必须是 staged，不能报 missing。

    声明槽位是 s1/s2，而发现式报告按实际 reviewer 名产出（review-codex.md），
    只按槽位名找暂存文件会让 AI 去等一份已经存在的报告。
    """

    def test_discovered_staged_reports_are_counted(self):
        import os, tempfile
        from types import SimpleNamespace
        from wflib import review

        import uuid
        root = tempfile.mkdtemp(prefix="wf-staged-")
        task_id = "2026-" + uuid.uuid4().hex[:8]      # 暂存目录全局共享 → 每测唯一
        task = {"id": task_id, "check": {"id": "c1", "anchor": {"check_anchor": "sha256:0"}},
                "reviews": {"launches": [{"round": 1, "slots": [{"slot": "s1"}, {"slot": "s2"}]}],
                            "imported": [], "result": None}}
        ctx = SimpleNamespace(root=root, key=lambda required=True: "k")
        directory = review.round_dir(ctx, task_id, 1)          # 暂存目录由 review 自己决定
        os.makedirs(directory, exist_ok=True)
        for name in ("review-codex.md", "review-gemini.md"):
            with open(os.path.join(directory, name), "w", encoding="utf-8") as handle:
                handle.write("---\nstatus: done\n---\n")
        status = review.status_of_round(ctx, task)
        states = [item["state"] for item in status["slots"]]
        self.assertEqual(states, ["staged", "staged"], f"实际: {status}")
        self.assertEqual(status["arrived"], 2)
        self.assertEqual(status["missing"], [])


class SlotClaimTest(unittest.TestCase):
    """第十五轮 a/G1：同一份报告不能被"已导入"与"暂存发现"各认领一次。"""

    def _ctx(self, files):
        import os, tempfile
        from types import SimpleNamespace
        from wflib import review

        import uuid
        root = tempfile.mkdtemp(prefix="wf-claim-")
        ctx = SimpleNamespace(root=root, key=lambda required=True: "k")
        self.task_id = "2026-" + uuid.uuid4().hex[:8]   # 暂存目录全局共享 → 每测唯一
        directory = review.round_dir(ctx, self.task_id, 1)
        os.makedirs(directory, exist_ok=True)
        for name, body in files.items():
            with open(os.path.join(directory, name), "w", encoding="utf-8") as handle:
                handle.write(body)
        return ctx, review

    def _task(self, imported):
        return {"id": self.task_id, "check": {"id": "c1", "anchor": {"check_anchor": "sha256:0"}},
                "reviews": {"launches": [{"round": 1, "slots": [{"slot": "s1"}, {"slot": "s2"}]}],
                            "imported": imported, "result": None}}

    def test_imported_report_is_not_also_counted_as_staged(self):
        ctx, review = self._ctx({"review-codex.md": "---\nstatus: done\n---\n"})
        import os
        rel = os.path.relpath(os.path.join(review.round_dir(ctx, self.task_id, 1), "review-codex.md"),
                              ctx.root).replace(os.sep, "/")
        from wflib import records
        digest = records.file_digest(os.path.join(ctx.root, rel))
        task = self._task([{"round": 1, "slot": "codex", "report_path": rel,
                            "report_digest": digest, "agent": "codex"}])
        status = review.status_of_round(ctx, task)
        states = [item["state"] for item in status["slots"]]
        self.assertEqual(states.count("imported"), 1, f"实际: {status}")
        self.assertNotIn("staged", states, "同一份报告不能被再次认领为 staged")
        self.assertEqual(status["arrived"], 1)

    def test_single_provider_is_not_ready_to_decide(self):
        ctx, review = self._ctx({})
        task = {"id": self.task_id, "check": {"id": "c1", "anchor": {"check_anchor": "sha256:0"}},
                "reviews": {"launches": [{"round": 1, "slots": [{"slot": "s1"}]}],
                            "imported": [], "result": None}}
        status = review.status_of_round(ctx, task)
        self.assertFalse(status["ready_to_decide"], "单 provider 轮必然判不了")


class ReadinessSemanticsTest(unittest.TestCase):
    """第十六轮 a/H2：文件存在 ≠ 报告完成 ≠ 导入完成；unreadable 必须是真实可达的第五值。"""

    def test_staged_reports_are_not_ready_to_decide(self):
        import os, tempfile, uuid
        from types import SimpleNamespace
        from wflib import review

        root = tempfile.mkdtemp(prefix="wf-ready-")
        ctx = SimpleNamespace(root=root, key=lambda required=True: "k")
        task_id = "2026-" + uuid.uuid4().hex[:8]
        directory = review.round_dir(ctx, task_id, 1)
        os.makedirs(directory, exist_ok=True)
        for name in ("review-codex.md", "review-gemini.md"):
            with open(os.path.join(directory, name), "w", encoding="utf-8") as handle:
                handle.write("---\nstatus: in-progress\n---\n")
        task = {"id": task_id, "check": {"id": "c1", "anchor": {"check_anchor": "sha256:0"}},
                "reviews": {"launches": [{"round": 1, "slots": [{"slot": "s1"}, {"slot": "s2"}]}],
                            "imported": [], "result": None}}
        status = review.status_of_round(ctx, task)
        self.assertEqual([item["state"] for item in status["slots"]], ["staged", "staged"])
        self.assertFalse(status["ready_to_decide"], "staged 不等于可判（还没导入、锚点未核）")

    def test_unreadable_state_is_reachable(self):
        """权限/IO 故障时 status_of_round 必须归入 unreadable，而不是把入口带崩。"""
        import os, stat, tempfile, uuid
        from types import SimpleNamespace
        from wflib import records, review

        root = tempfile.mkdtemp(prefix="wf-unread-")
        ctx = SimpleNamespace(root=root, key=lambda required=True: "k")
        task_id = "2026-" + uuid.uuid4().hex[:8]
        directory = review.round_dir(ctx, task_id, 1)
        os.makedirs(directory, exist_ok=True)
        path = os.path.join(directory, "review-codex.md")
        with open(path, "w", encoding="utf-8") as handle:
            handle.write("---\nstatus: done\n---\n")
        digest = records.file_digest(path)
        os.chmod(path, 0)
        rel = os.path.relpath(path, ctx.root).replace(os.sep, "/")
        task = {"id": task_id, "check": {"id": "c1", "anchor": {"check_anchor": "sha256:0"}},
                "reviews": {"launches": [{"round": 1, "slots": [{"slot": "s1"}, {"slot": "s2"}]}],
                            "imported": [{"round": 1, "slot": "codex", "report_path": rel,
                                          "report_digest": digest, "agent": "codex"}],
                            "result": None}}
        try:
            status = review.status_of_round(ctx, task)
        finally:
            os.chmod(path, stat.S_IRUSR | stat.S_IWUSR)
        states = [item["state"] for item in status["slots"]]
        self.assertIn("unreadable", states, f"实际: {status}")


class RoundReadinessFactsTest(unittest.TestCase):
    """第十六轮的 a-3/K4/a-6：可判必须基于"该轮全部导入报告 + 锚点已核"，
    且 staged 要区分"文件在"与"可导入"。"""

    def _ctx(self, files):
        import os, tempfile, uuid
        from types import SimpleNamespace
        from wflib import review

        root = tempfile.mkdtemp(prefix="wf-round-")
        ctx = SimpleNamespace(root=root, key=lambda required=True: "k")
        self.task_id = "2026-" + uuid.uuid4().hex[:8]
        directory = review.round_dir(ctx, self.task_id, 1)
        os.makedirs(directory, exist_ok=True)
        paths = {}
        for name, body in files.items():
            paths[name] = os.path.join(directory, name)
            with open(paths[name], "w", encoding="utf-8") as handle:
                handle.write(body)
        return ctx, review, paths

    def test_extra_imported_report_blocks_readiness(self):
        import os
        from wflib import records

        ctx, review, paths = self._ctx({
            "review-codex.md": "---\nstatus: done\n---\n",
            "review-gemini.md": "---\nstatus: done\n---\n",
            "review-pi.md": "---\nstatus: done\n---\n",
        })
        imported = []
        for name in ("review-codex.md", "review-gemini.md", "review-pi.md"):
            rel = os.path.relpath(paths[name], ctx.root).replace(os.sep, "/")
            imported.append({"round": 1, "slot": name[7:-3], "report_path": rel,
                             "report_digest": records.file_digest(paths[name]),
                             "anchor": {"check_anchor": "sha256:0"}})
        # 第三份被改写 → decide 会拒绝，展示也不能说可判
        with open(paths["review-pi.md"], "a", encoding="utf-8") as handle:
            handle.write("tampered\n")
        task = {"id": self.task_id, "check": {"id": "c1", "anchor": {"check_anchor": "sha256:0"}},
                "reviews": {"launches": [{"round": 1, "slots": [{"slot": "s1"}, {"slot": "s2"}]}],
                            "imported": imported, "result": None}}
        status = review.status_of_round(ctx, task)
        self.assertTrue(status["extra_reports"], f"实际: {status}")
        self.assertFalse(status["ready_to_decide"])

    def test_staged_in_progress_is_not_importable(self):
        ctx, review, _paths = self._ctx({"review-codex.md": "---\nstatus: in-progress\n---\n"})
        task = {"id": self.task_id, "check": {"id": "c1", "anchor": {"check_anchor": "sha256:0"}},
                "reviews": {"launches": [{"round": 1, "slots": [{"slot": "s1"}, {"slot": "s2"}]}],
                            "imported": [], "result": None}}
        status = review.status_of_round(ctx, task)
        staged = [item for item in status["slots"] if item["state"] == "staged"]
        self.assertTrue(staged)
        self.assertFalse(staged[0].get("importable"), "status != done 不可导入")
