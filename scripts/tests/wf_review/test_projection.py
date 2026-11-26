"""P5/K8·K9·S5b：可重建投影、写链与 trailer 三态、未核实项生命周期。

防的失败（dogfood F3「同一事实两处存」与 H3「手工验证永不结案」）：
投影散落在运行态缓存里 → 与记录漂移且无法区分；未处置的 blocking 与未核实项没有"结案"动作，
只能靠自由文本宣称"已处理"。
"""

import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "docs" / "workflows" / "wf" / "payload" / "lib"))

from wflib import projection  # noqa: E402


class FakeCtx:
    def __init__(self, root="."):
        self.root = str(root)


def task(**extra):
    data = {"id": "t1", "status": "in_progress", "phase": "check",
            "plan": {"acceptance": [{"id": "a1", "verification_ids": ["v1"]}],
                     "verifications": [{"id": "v1", "required": True}]},
            "check": {"acceptance_results": [{"acceptance_id": "a1", "conclusion": "pending"}]},
            "actions": [{"id": "a1", "at": "t1"}, {"id": "a2", "at": "t2"}],
            "write_mark": {"action_id": "a2"}}
    data.update(extra)
    return data


class ProjectionTest(unittest.TestCase):
    def test_projections_are_pure_functions_of_records(self):
        for kind in ("open-items", "audit", "attribution", "skeleton"):
            facts = projection.check(FakeCtx(), task(), kind)
            self.assertTrue(facts["equal"], f"{kind}: {facts['problems']}")
            self.assertFalse(facts["cached"], "投影不应落盘：没有缓存副本才对")

    def test_open_items_lists_required_unverified_and_findings(self):
        items = projection.open_items(FakeCtx(), task())
        self.assertEqual([item["acceptance_id"] for item in items["unverified"]], ["a1"])
        self.assertTrue(items["unverified"][0]["required"])

    def test_cached_copy_drift_is_detected(self):
        with tempfile.TemporaryDirectory() as tmp:
            ctx = FakeCtx(tmp)
            path = Path(projection.cache_path(tmp, "t1", "audit"))
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text('{"actions": 99}', encoding="utf-8")
            facts = projection.check(ctx, task(), "audit")
        self.assertFalse(facts["equal"])
        self.assertTrue(any("缓存" in item["reason"] for item in facts["problems"]))


class AuditChainTest(unittest.TestCase):
    def test_clean_chain_passes(self):
        self.assertEqual(projection.audit_chain(task())["problems"], [])

    def test_write_mark_pointing_nowhere_is_reported(self):
        facts = projection.audit_chain(task(write_mark={"action_id": "nope"}))
        self.assertTrue(any("write_mark" in item["reason"] for item in facts["problems"]))

    def test_time_going_backwards_is_reported(self):
        facts = projection.audit_chain(task(actions=[{"id": "a1", "at": "t2"}, {"id": "a2", "at": "t1"}]))
        self.assertTrue(any("backwards" in item["reason"] for item in facts["problems"]))

    def test_guarantee_is_limited(self):
        facts = projection.audit_chain(task())
        self.assertIn("不承诺防伪造", facts["guarantee"])


class UnverifiedLifecycleTest(unittest.TestCase):
    def test_required_item_blocks_until_resolved(self):
        data = task()
        self.assertEqual([item["acceptance_id"]
                          for item in projection.required_unverified(FakeCtx(), data)], ["a1"])

    def test_narrow_requires_all_four_parts(self):
        data = task()
        _record, problems = projection.resolve(data, "a1", kind="narrow", evidence="e", reason="缺环境")
        self.assertTrue(any("impact" in item["reason"] for item in problems))
        self.assertTrue(any("compensation" in item["reason"] for item in problems))

    def test_narrow_with_four_parts_resolves(self):
        data = task()
        record, problems = projection.resolve(data, "a1", kind="narrow", evidence="e",
                                              reason="缺 Windows 主机", impact="放弃跨平台验证",
                                              compensation="CI 矩阵待建")
        self.assertEqual(problems, [])
        self.assertEqual(record["kind"], "narrow")
        self.assertEqual(projection.required_unverified(FakeCtx(), data), [])

    def test_inspection_needs_evidence(self):
        _record, problems = projection.resolve(task(), "a1", kind="inspection", evidence="")
        self.assertTrue(any("证据" in item["reason"] for item in problems))

    def test_archive_gate_consumes_it(self):
        source = (REPO / "docs/workflows/wf/payload/lib/wflib/gates.py").read_text(encoding="utf-8")
        self.assertIn("required_unverified", source)
        self.assertIn("pending_required_unverified", source)


if __name__ == "__main__":
    unittest.main()


class ChainHeadTrailerTest(unittest.TestCase):
    """K9：归档提交带 `wf-chain-head` trailer，投影侧可比对（只承诺可检出）。"""

    def test_trailer_is_derived_from_write_mark(self):
        from wflib import tasks

        self.assertEqual(tasks._chain_trailer({"write_mark": {"action_id": "a9"}}),
                         "\nwf-chain-head: a9")
        self.assertEqual(tasks._chain_trailer({"action": {"id": "a1"}}), "\nwf-chain-head: a1")
        self.assertEqual(tasks._chain_trailer({}), "")

    def test_archive_commits_carry_the_trailer(self):
        source = (REPO / "docs/workflows/wf/payload/lib/wflib/tasks.py").read_text(encoding="utf-8")
        self.assertIn("_chain_trailer(task)", source)
        self.assertGreaterEqual(source.count("wf-chain-head"), 1)

    def test_check_reports_missing_trailer_instead_of_guessing(self):
        class Ctx:
            root = str(REPO)

        facts = projection.chain_head_check(Ctx(), {"_record_path": "scripts"})
        self.assertTrue(facts["available"])
        self.assertFalse(facts["anchored"])
        self.assertIn("wf-chain-head", facts["reason"])


class CommitClassificationTest(unittest.TestCase):
    """K9 的提交三态解析：记录分隔必须与 git 输出对齐（旧实现把多条压成一条）。"""

    RAW = ("a1b2c3\x1f"
           "feat: 有标记\n\nwf-task: t1\n\x1e"
           "d4e5f6\x1ffeat: 无标记\n\x1e"
           "0a1b2c\x1ffeat: 有裁决\n\x1e")

    def test_three_states(self):
        attributed, adjudicated, external = projection.classify_commits(
            self.RAW, "t1", {"attribution": {"decisions": [{"commit": "0a1b2c"}]}})
        self.assertEqual(attributed, ["a1b2c3"])
        self.assertEqual(adjudicated, ["0a1b2c"])
        self.assertEqual(external, ["d4e5f6"])

    def test_short_and_full_identities(self):
        """六轮复核 b.7：归属按完整提交号匹配；旧短号仅在**唯一**前缀时放行。"""
        full = "0a1b2c9d8e7f6a5b4c3d2e1f0011223344556677"
        raw = f"{full}\x1ffeat: 有裁决\n\x1e"
        # 记录短号、查询长号：唯一前缀 ⇒ 命中
        _, adjudicated, _ = projection.classify_commits(
            raw, "t1", {"attribution": {"decisions": [{"commit": "0a1b2c9"}]}})
        self.assertEqual(adjudicated, [full])
        # 记录与查询都长：精确相等
        _, adjudicated, _ = projection.classify_commits(
            raw, "t1", {"attribution": {"decisions": [{"commit": full}]}})
        self.assertEqual(adjudicated, [full])
        # 旧短号是"声明边界"：唯一前缀时按命中处理（无法分辨是能力限制，不是放行任意前缀）
        other = "0a1b2c9" + "f" * 33
        _, adjudicated, _ = projection.classify_commits(
            f"{other}\x1ffeat: 别的提交\n\x1e", "t1",
            {"attribution": {"decisions": [{"commit": "0a1b2c9"}]}})
        self.assertEqual(adjudicated, [other])
        # 两个提交共享该短前缀：分不清是哪一条 ⇒ 都不归属
        third = "0a1b2c9" + "a" * 33
        raw_two = f"{other}\x1ffeat: 1\n\x1e{third}\x1ffeat: 2\n\x1e"
        _, adjudicated, external = projection.classify_commits(
            raw_two, "t1", {"attribution": {"decisions": [{"commit": "0a1b2c9"}]}})
        self.assertEqual(adjudicated, [])
        self.assertEqual(sorted(external), sorted([other, third]))

    def test_multiple_commits_are_not_collapsed(self):
        raw = "aa\x1ffeat: 1\n\nwf-task: t1\n\x1ebb\x1ffeat: 2\n\nwf-task: t1\n\x1e"
        attributed, _adjudicated, external = projection.classify_commits(raw, "t1")
        self.assertEqual(attributed, ["aa", "bb"])
        self.assertEqual(external, [])

    def test_empty_output(self):
        self.assertEqual(projection.classify_commits("", "t1"), ([], [], []))


class ArchiveStagesContractTest(unittest.TestCase):
    """K7 + P4 退出判据：记录段要连旧位置删除一起提交，否则归档后工作树不干净。"""

    def test_record_commit_includes_only_tracked_move_out(self):
        """记录段要带上旧位置的删除，但只限 HEAD 里**已跟踪**的路径。

        首次归档的任务目录从未入库，把它当 pathspec 会让 git add 直接失败
        （"did not match any file(s) known to git"）——第三轮审查的 P1。
        """
        source = (REPO / "docs/workflows/wf/payload/lib/wflib/tasks.py").read_text(encoding="utf-8")
        self.assertIn("_tracked_under(ctx.root, old_rel)", source)
        self.assertIn("ls-tree", source)
        self.assertNotIn("commit_paths.append(old_rel)", source)


class TrackedUnderTest(unittest.TestCase):
    """首次归档的任务目录从未入库 → 记录段不能拿它当 pathspec（第三轮审查 P1）。"""

    def test_untracked_dir_yields_no_pathspec(self):
        import subprocess
        import tempfile

        from wflib import tasks

        with tempfile.TemporaryDirectory() as tmp:
            subprocess.run(["git", "init", "-q"], cwd=tmp, check=True)
            subprocess.run(["git", "config", "user.email", "t@e"], cwd=tmp, check=True)
            subprocess.run(["git", "config", "user.name", "t"], cwd=tmp, check=True)
            Path(tmp, ".wf/tasks/2026-x").mkdir(parents=True)
            Path(tmp, ".wf/tasks/2026-x/task.json").write_text("{}", encoding="utf-8")
            Path(tmp, "README.md").write_text("r\n", encoding="utf-8")
            subprocess.run(["git", "add", "README.md"], cwd=tmp, check=True)
            subprocess.run(["git", "commit", "-qm", "init"], cwd=tmp, check=True)
            self.assertEqual(tasks._tracked_under(tmp, ".wf/tasks/2026-x"), [])

    def test_tracked_dir_yields_its_paths(self):
        import subprocess
        import tempfile

        from wflib import tasks

        with tempfile.TemporaryDirectory() as tmp:
            subprocess.run(["git", "init", "-q"], cwd=tmp, check=True)
            subprocess.run(["git", "config", "user.email", "t@e"], cwd=tmp, check=True)
            subprocess.run(["git", "config", "user.name", "t"], cwd=tmp, check=True)
            Path(tmp, ".wf/tasks/2026-y").mkdir(parents=True)
            Path(tmp, ".wf/tasks/2026-y/task.json").write_text("{}", encoding="utf-8")
            subprocess.run(["git", "add", "-A"], cwd=tmp, check=True)
            subprocess.run(["git", "commit", "-qm", "init"], cwd=tmp, check=True)
            self.assertEqual(tasks._tracked_under(tmp, ".wf/tasks/2026-y"),
                             [".wf/tasks/2026-y/task.json"])
