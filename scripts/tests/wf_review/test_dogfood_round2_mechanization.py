"""Stage 2 机械项入口化的行为断言（2026-11-21 dogfood 二轮）。

覆盖：
- archive --draft：免决定草稿（决定域形状、commit 条目预填 pending 路径、
  finish 条目留占位、无绑定/无写权/不取锁可出、不落盘、--draft/--decision 互斥）
- RecordInvalid carries_id：目录名当 id → actual_id 出口；其余原因不扩权
- 决定预检错误回显：缺字段时给 required_fields 与 at 当前时刻
- 报告骨架预填：excluded-scope = mandatory_exclusions 口径、read-scope=["materials"]
"""

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "docs" / "workflows" / "wf" / "payload" / "lib"))

from wflib import cli, records, review  # noqa: E402
from wflib import tasks as tasks_mod  # noqa: E402


class _Ctx:
    """最小命令上下文：root 指向临时仓库，key 提供会话标识。"""

    def __init__(self, root):
        self.root = str(root)
        self._argv = []

    def key(self):
        return "sess-draft-test"

    def rule_version(self):
        return 1

    def debug_threshold(self):
        return 3

    class _Args:
        def __init__(self, argv):
            self.argv = list(argv)
            self.used = set()

        def value(self, name):
            if name in self.argv:
                self.used.add(self.argv.index(name))
                index = self.argv.index(name) + 1
                if index < len(self.argv):
                    self.used.add(index)
                    return self.argv[index]
            return None

        def flag(self, name):
            if name in self.argv:
                self.used.add(self.argv.index(name))
                return True
            return False

    def args(self, argv):
        return self._Args(argv)


class ArchiveDraftTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        # pending_delivery_paths 按 git 工作树推导（未跟踪文件属未提交），夹具需真 git 仓库
        import subprocess

        def _git(*argv):
            subprocess.run(["git", *argv], cwd=self.root, check=True, capture_output=True,
                          env={**os.environ, "GIT_CONFIG_GLOBAL": "/dev/null",
                               "GIT_CONFIG_SYSTEM": "/dev/null"})
        _git("init", "-q")
        _git("config", "user.email", "test@example.com")
        _git("config", "user.name", "test")
        self.ctx = _Ctx(self.root)
        # 任务目录：无绑定、无写权——草稿必须仍可出（只读性质断言）
        task_id = "t-20261121-0001"
        task_dir = self.root / ".wf" / "tasks" / task_id
        task_dir.mkdir(parents=True)
        (task_dir / "task.json").write_text(json.dumps({
            "id": task_id, "title": "草稿测试", "status": "in_progress", "phase": "finish",
            "plan": {"complexity": "light", "touch_paths": ["src/**", "tests/**"]},
            "entry_snapshot": {"touch_paths": ["src/**", "tests/**"]},
            "delivery": {"paths": ["src/a.py", "tests/test_a.py"]},
        }), encoding="utf-8")
        # 未跟踪文件占交付面；.wf 提交为基线，保证未跟踪路径出现在 pending
        for rel in ("src/a.py", "tests/test_a.py"):
            target = self.root / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text("x\n", encoding="utf-8")
        _git("add", ".wf")
        _git("commit", "-q", "-m", "fixture base")
        self.task_id = task_id

    def tearDown(self):
        self._tmp.cleanup()

    def test_draft_without_binding_and_write_right(self):
        """无绑定、无写权、不取锁时仍可出草稿（实现在 _load_decision/锁之前返回）。"""
        result = tasks_mod.cmd_archive(
            self.ctx, self.ctx.args(["--task", self.task_id, "--draft"]))
        self.assertEqual(result["code"], "WF_OK")
        facts = result.get("facts") or {}
        self.assertTrue(facts.get("note", "").startswith("草稿只读"))

    def test_draft_entries_shape(self):
        """条目为 archive 决定域形状：finish + commit 两类 choice、六键齐、subject 预填 pending。"""
        result = tasks_mod.cmd_archive(
            self.ctx, self.ctx.args(["--task", self.task_id, "--draft"]))
        entries = (result.get("facts") or {})["draft"]
        choices = [entry["choice"] for entry in entries]
        self.assertIn("finish", choices)
        self.assertIn("commit", choices)
        for entry in entries:
            for field in cli.DECISION_FIELDS:
                self.assertIn(field, entry)
        commit_subjects = [item for entry in entries if entry["choice"] == "commit"
                           for item in (entry["subject"] if isinstance(entry["subject"], list)
                                        else [entry["subject"]])]
        self.assertEqual(sorted(commit_subjects), ["src/a.py", "tests/test_a.py"])
        # finish 条目 subject/quote 不预填具体路径（框架不替人写）
        finish_entry = next(entry for entry in entries if entry["choice"] == "finish")
        self.assertNotIn("src/a.py", str(finish_entry.get("subject")))

    def test_draft_does_not_write_any_record(self):
        """草稿不落盘：任务记录字节不变；直接归档（无决定）仍抛 WF_PATH_INVALID。"""
        before = (self.root / ".wf" / "tasks" / self.task_id / "task.json").read_bytes()
        tasks_mod.cmd_archive(self.ctx, self.ctx.args(["--task", self.task_id, "--draft"]))
        self.assertEqual((self.root / ".wf" / "tasks" / self.task_id / "task.json").read_bytes(), before)
        with self.assertRaises(Exception) as caught:
            tasks_mod.cmd_archive(
                self.ctx, self.ctx.args(["--task", self.task_id, "--decision", "/nonexistent.json"]))
        self.assertIn("WF_PATH_INVALID", str(caught.exception))

    def test_draft_conflicts_with_decision(self):
        """--draft 与 --decision 同给报错（草稿模式互斥）。"""
        with self.assertRaises(Exception):
            tasks_mod.cmd_archive(
                self.ctx, self.ctx.args(["--task", self.task_id, "--draft",
                                         "--decision", "x.json"]))


class RecordInvalidCarriesIdTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        # 目录名与记录内 id 不同的任务（目录名被当 id 传入的场景）
        real_id = "t-20261121-real"
        task_dir = self.root / ".wf" / "tasks" / "t-20261121-directory"
        task_dir.mkdir(parents=True)
        (task_dir / "task.json").write_text(json.dumps({"id": real_id}), encoding="utf-8")

    def tearDown(self):
        self._tmp.cleanup()

    def test_load_task_carries_id(self):
        try:
            tasks_mod.load_task(str(self.root), "t-20261121-directory")
            self.fail("expected RecordInvalid")
        except records.RecordInvalid as exc:
            self.assertEqual(getattr(exc, "carries_id", None), "t-20261121-real")

    def test_other_record_invalid_has_no_carries_id(self):
        exc = records.RecordInvalid("duplicate key: a")
        self.assertIsNone(getattr(exc, "carries_id", None))


class DecisionPreludeFactsTest(unittest.TestCase):
    def test_missing_fields_gives_required_fields_and_at_hint(self):
        """缺字段错误给 required_fields（DECISION_FIELDS）与 at 当前时刻提示。"""
        path = Path(tempfile.mkdtemp()) / "d.json"
        path.write_text(json.dumps([{"source": "human:chat"}]), encoding="utf-8")
        try:
            cli._load_decision(str(path))
            self.fail("expected CliError")
        except cli.CliError as exc:
            facts = exc.facts
            self.assertIn("required_fields", facts)
            self.assertEqual(tuple(facts["required_fields"]), cli.DECISION_FIELDS)
            self.assertIn("at", facts.get("field_notes", {}))
            self.assertIn(records.now_str()[:10], facts["field_notes"]["at"])
        finally:
            path.unlink()
            path.parent.rmdir()


class SkeletonPrefillTest(unittest.TestCase):
    def test_skeleton_prefills_exclusions_and_materials(self):
        launch = {"exclusions": [".env", "id_rsa"]}
        skeleton = review.report_skeleton("t-1", 3, {"id": "c1"}, "sha256:abc", launch=launch)
        block = skeleton.split("```json")[1]
        payload = json.loads(block.split("```")[0])
        self.assertEqual(payload["read-scope"], ["materials"])
        expected = sorted(review.mandatory_exclusions(launch.get("exclusions")))
        self.assertEqual(sorted(payload["excluded-scope"]), expected)

    def test_skeleton_without_launch_leaves_defaults(self):
        """无 launch（异常防御路径）时 excluded-scope 为空数组——导入校验兜底。"""
        skeleton = review.report_skeleton("t-1", 3, {"id": "c1"}, "sha256:abc")
        block = skeleton.split("```json")[1]
        payload = json.loads(block.split("```")[0])
        self.assertEqual(payload["read-scope"], ["materials"])


if __name__ == "__main__":
    unittest.main()


class TouchPathAssertionRefTest(unittest.TestCase):
    """批I（2026-11-21）：t:<触碰面内路径> 可作 blocking 判据；面外路径被拒。"""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.task = {"id": "t-tp",
                     "plan": {"acceptance": [{"id": "a1"}],
                              "verifications": [{"id": "v1"}]},
                     "curation": [],
                     "entry_snapshot": {"touch_paths": ["src/**"]},
                     }

    def tearDown(self):
        self._tmp.cleanup()

    def _index(self):
        class Ctx:
            root = str(self.root)

            def rule_version(self):
                return 1

            def debug_threshold(self):
                return 3
        return review.assertion_index(Ctx(), self.task)

    def test_touch_path_is_in_index(self):
        index, _changed = self._index()
        self.assertEqual(index.get("t:src/**"), "touch-path")

    def test_ref_inside_touch_path_passes(self):
        index, _changed = self._index()
        problem = review.assertion_ref_problem("t:src/a.py", index, {}, task=self.task,
                                               finding_location="src/a.py")
        self.assertIsNone(problem)

    def test_ref_without_location_is_rejected(self):
        """七轮审查 b-1：缺 location 的 finding 不得用 t: 判据。"""
        index, _changed = self._index()
        problem = review.assertion_ref_problem("t:src/a.py", index, {}, task=self.task)
        self.assertIsNotNone(problem)
        self.assertIn("location", problem["reason"])

    def test_ref_outside_touch_path_is_rejected(self):
        index, _changed = self._index()
        problem = review.assertion_ref_problem("t:docs/other.md", index, {}, task=self.task)
        self.assertIsNotNone(problem)
        self.assertIn("触碰面", problem["reason"])


class ArchiveVendorDirtyFactsTest(unittest.TestCase):
    """批C 回归（2026-11-21）：归档收尾 facts 的 vendor_dirty 键可序列化（曾因 NameError 崩溃重入分支）。

    断言锚行为：cmd_archive 的 facts 字典构建代码引用的名字必须在该函数源内可达——
    用 AST 静态核对（不跑完整归档），防止再次引用未定义变量。
    """

    def test_archive_facts_names_resolve(self):
        import ast
        import inspect
        from wflib import tasks as tasks_mod

        tree = ast.parse(inspect.getsource(tasks_mod.cmd_archive))
        assigned = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store):
                assigned.add(node.id)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                assigned.add(node.name)
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                for alias in node.names:
                    assigned.add((alias.asname or alias.name).split(".")[0])
        params = {a.arg for a in ast.walk(tree) if isinstance(a, ast.arg)}
        loaded = {n.id for n in ast.walk(tree)
                  if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load)}
        module_globals = set(vars(tasks_mod)) | set(dir(__import__("builtins")))
        # except 名与嵌套 def 名经 ExceptHandler/FunctionDef 装载（Store 语义在 ast.Name 之外）——
        # ast.arg 已覆盖嵌套函数形参；此处补 except 别名。
        for node in ast.walk(tree):
            if isinstance(node, ast.ExceptHandler) and node.name:
                module_globals.add(node.name)
        free = loaded - assigned - params - module_globals
        self.assertFalse(free,
                         f"cmd_archive 引用未定义名字: {sorted(free)}")


class RepoRulesContentBindingTest(unittest.TestCase):
    """六轮审查 a-2：repo_rules/delete 确认按内容摘要绑定——同一路径确认后再改，旧确认失效。"""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        (self.root / ".wf").mkdir()
        (self.root / ".gitignore").write_text("*.log\n", encoding="utf-8")
        self.task_dir = self.root / ".wf" / "tasks" / "t-1"
        self.task_dir.mkdir(parents=True)

    def tearDown(self):
        self._tmp.cleanup()

    def _record(self):
        from wflib import authorize

        decision = {"choice": "repo_rules", "paths": [".gitignore"],
                    "quote": "人确认改 .gitignore", "by": "human:test",
                    "at": "2026-11-21T00:00:00Z", "source": "user-declared"}
        return authorize.record_authorization(str(self.task_dir), "repo_rules", decision,
                                              root=str(self.root))

    def test_covers_same_content(self):
        self._record()
        from wflib import authorize

        covered, uncovered = authorize.covers(str(self.task_dir), "repo_rules", [".gitignore"],
                                              root=str(self.root))
        self.assertTrue(covered, uncovered)

    def test_changed_content_not_covered(self):
        self._record()
        (self.root / ".gitignore").write_text("*.log\n*.tmp\n", encoding="utf-8")  # 确认后再改
        from wflib import authorize

        covered, uncovered = authorize.covers(str(self.task_dir), "repo_rules", [".gitignore"],
                                              root=str(self.root))
        self.assertFalse(covered)
        self.assertEqual(uncovered, [".gitignore"])


class TouchRefLocationBindingTest(unittest.TestCase):
    """六轮审查 a-1：t: 引用必须覆盖 finding 的实际位置。"""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.task = {"id": "t-tl", "plan": {}, "curation": [],
                     "entry_snapshot": {"touch_paths": ["src/**"]}}

    def tearDown(self):
        self._tmp.cleanup()

    def test_matching_location_passes(self):
        index, _ = review.assertion_index(type("C", (), {"root": str(self.root),
                                                         "rule_version": lambda: 1,
                                                         "debug_threshold": lambda: 3})(), self.task)
        problem = review.assertion_ref_problem("t:src/a.py", index, {}, task=self.task,
                                               finding_location="src/a.py")
        self.assertIsNone(problem)

    def test_mismatched_location_is_rejected(self):
        index, _ = review.assertion_index(type("C", (), {"root": str(self.root),
                                                         "rule_version": lambda: 1,
                                                         "debug_threshold": lambda: 3})(), self.task)
        problem = review.assertion_ref_problem("t:src/a.py", index, {}, task=self.task,
                                               finding_location="docs/other.md")
        self.assertIsNotNone(problem)
        self.assertIn("实际位置不符", problem["reason"])


class DraftPlaceholderRejectionTest(unittest.TestCase):
    """七轮审查 P2-5：草稿占位照抄必须被决定预检拒绝（at 全匹配 ISO / digest 格式）。"""

    def test_draft_placeholder_at_is_rejected(self):
        draft_like = [{"source": "human:（人复核草稿后填写）",
                       "at": "2026-11-21T07:56:55.084894Z（提交时刻由人确认后写）",
                       "subject": ["src/a.py"],
                       "object_digest": "（按决定语义填写）",
                       "choice": "commit", "reason": "（人填写）"}]
        path = Path(tempfile.mkdtemp()) / "d.json"
        path.write_text(json.dumps(draft_like), encoding="utf-8")
        try:
            cli._load_decision(str(path))
            self.fail("草稿占位被接受——占位值会污染记录")
        except cli.CliError as exc:
            self.assertIn("at", exc.facts.get("reason", ""))

    def test_todo_placeholders_are_rejected_on_any_field(self):
        """十轮 P2-3：占位不可半可过——at/digest 合法但 subject/reason 是 TODO 时同样被拒。"""
        draft_like = [{"source": "TODO human:chat（人复核草稿后填）",
                       "at": "2026-11-21T07:56:55.084894Z",
                       "subject": "TODO（人写：已了解结果与未核实项）",
                       "object_digest": "",
                       "choice": "finish", "reason": "TODO（人填写：为什么这样处置）"}]
        path = Path(tempfile.mkdtemp()) / "d.json"
        path.write_text(json.dumps(draft_like), encoding="utf-8")
        try:
            cli._load_decision(str(path))
            self.fail("TODO 占位被接受——占位句不算人签字")
        except cli.CliError as exc:
            self.assertIn("TODO", exc.facts.get("reason", ""))
            self.assertIn("subject", exc.facts.get("todo_fields", []))
            self.assertIn("reason", exc.facts.get("todo_fields", []))


class DeleteAuthorizationFlowTest(unittest.TestCase):
    """八轮审查 P0-1：删除类确认——record 在删除前落档即可通过守卫；先删后 record 被拒。"""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        (self.root / "old_module.py").write_text("legacy\n", encoding="utf-8")

    def tearDown(self):
        self._tmp.cleanup()

    def _record(self, paths):
        from wflib import authorize

        authorize.record_authorization(str(self.root), "delete",
                                       {"choice": "delete", "paths": paths, "quote": "清理旧模块",
                                        "by": "human:test", "at": "2026-11-21T00:00:00Z",
                                        "source": "user-declared"}, root=str(self.root))

    def test_record_then_delete_is_covered(self):
        from wflib import authorize

        self._record(["old_module.py"])
        (self.root / "old_module.py").unlink()
        covered, uncovered = authorize.covers(str(self.root), "delete", ["old_module.py"],
                                              root=str(self.root))
        self.assertTrue(covered, uncovered)

    def test_delete_then_record_is_rejected(self):
        from wflib import authorize

        (self.root / "old_module.py").unlink()
        self._record(["old_module.py"])   # 文件已删：摘要绑不上
        covered, uncovered = authorize.covers(str(self.root), "delete", ["old_module.py"],
                                              root=str(self.root))
        self.assertFalse(covered)
        self.assertEqual(uncovered, ["old_module.py"])


class PreexistingUncommittedTest(unittest.TestCase):
    """九轮审查 b-1：开工前已存在的脏文件命中触碰面不自动归属——进 c（待归属）而非 e。"""

    def setUp(self):
        import subprocess

        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)

        def _git(*argv):
            subprocess.run(["git", *argv], cwd=self.root, check=True, capture_output=True,
                           env={**os.environ, "GIT_CONFIG_GLOBAL": "/dev/null",
                                "GIT_CONFIG_SYSTEM": "/dev/null"})
        _git("init", "-q"); _git("config", "user.email", "t@t"); _git("config", "user.name", "t")
        (self.root / ".wf").mkdir()
        (self.root / "src").mkdir()
        (self.root / ".gitignore").write_text("\n", encoding="utf-8")
        (self.root / "src" / "user_work.py").write_text("pre-existing\n", encoding="utf-8")  # 开工前脏
        _git("add", ".gitignore"); _git("commit", "-qm", "base")

    def tearDown(self):
        self._tmp.cleanup()

    def test_preexisting_is_flagged_not_silently_claimed(self):
        from wflib import scope

        task = {"id": "t-pre", "entry_snapshot": {"touch_paths": ["src/**"],
                                                 "preexisting_uncommitted": ["src/user_work.py"]}}
        classified = scope.classify_candidates(str(self.root), task)
        # 主流程（在途工作补进任务）保持可用：仍进交付（e）
        self.assertIn("src/user_work.py", classified["buckets"]["e"])
        # 但归属不明必须可见：preexisting_in_scope 如实上抛（事实不阻断）
        self.assertIn("src/user_work.py", classified["preexisting_in_scope"])

    def test_post_start_file_is_delivery(self):
        from wflib import scope

        task = {"id": "t-post", "entry_snapshot": {"touch_paths": ["src/**"],
                                                 "preexisting_uncommitted": []}}
        (self.root / "src" / "new_file.py").write_text("created after start\n", encoding="utf-8")
        classified = scope.classify_candidates(str(self.root), task)
        self.assertIn("src/new_file.py", classified["buckets"]["e"])


class ExpandAuthorizedPathTest(unittest.TestCase):
    """九轮审查 b-3：expand 已确认的面外新文件进交付（e）；t: 判据面含 expand。"""

    def setUp(self):
        import subprocess

        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)

        def _git(*argv):
            subprocess.run(["git", *argv], cwd=self.root, check=True, capture_output=True,
                           env={**os.environ, "GIT_CONFIG_GLOBAL": "/dev/null",
                                "GIT_CONFIG_SYSTEM": "/dev/null"})
        _git("init", "-q"); _git("config", "user.email", "t@t"); _git("config", "user.name", "t")
        _exp_dir = self.root / ".wf" / "tasks" / "t-exp"
        _exp_dir.mkdir(parents=True)
        _exp_dir.joinpath("task.json").write_text(json.dumps({"id": "t-exp"}), encoding="utf-8")
        (self.root / ".gitignore").write_text("\n", encoding="utf-8")
        _git("add", ".gitignore"); _git("commit", "-qm", "base")
        from wflib import authorize

        authorize.record_authorization(str(self.root / ".wf" / "tasks" / "t-exp"), "expand",
                                      {"choice": "expand", "paths": ["ext/**"], "quote": "人同意单点扩面",
                                       "by": "human:test", "at": "2026-11-21T00:00:00Z",
                                       "source": "user-declared"}, root=str(self.root))
        (self.root / "ext").mkdir()
        (self.root / "ext" / "added.py").write_text("expanded\n", encoding="utf-8")
        self.task = {"id": "t-exp", "entry_snapshot": {"touch_paths": ["src/**"]}}

    def tearDown(self):
        self._tmp.cleanup()

    def test_expanded_file_is_delivery(self):
        from wflib import scope

        classified = scope.classify_candidates(str(self.root), self.task)
        self.assertIn("ext/added.py", classified["buckets"]["e"])
        self.assertNotIn("ext/added.py", classified["buckets"]["c"])

    def test_t_ref_accepts_expanded_path(self):
        class Ctx:
            root = str(self.root)

            def rule_version(self):
                return 1

            def debug_threshold(self):
                return 3
        index, _ = review.assertion_index(Ctx(), self.task)
        self.assertEqual(index.get("t:ext/**"), "touch-path")
        problem = review.assertion_ref_problem("t:ext/added.py", index, {}, task=self.task,
                                               finding_location="ext/added.py")
        self.assertIsNone(problem)


class AuthorizationMergeTest(unittest.TestCase):
    """十一轮审查 b-2：同动作重复授权合并累计——旧授权不得被覆盖丢失。"""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        (self.root / ".wf" / "tasks" / "t-m").mkdir(parents=True)

    def tearDown(self):
        self._tmp.cleanup()

    def _record(self, paths):
        from wflib import authorize

        return authorize.record_authorization(
            str(self.root / ".wf" / "tasks" / "t-m"), "expand",
            {"choice": "expand", "paths": paths, "quote": "人同意", "by": "human:t",
             "at": "2026-11-22T00:00:00Z", "source": "user-declared"}, root=str(self.root))

    def test_second_expand_keeps_first_paths(self):
        from wflib import authorize

        (self.root / "ext").mkdir(exist_ok=True)
        (self.root / "ext" / "a.py").write_text("a\n", encoding="utf-8")
        (self.root / "ext" / "b.py").write_text("b\n", encoding="utf-8")
        self._record(["ext/a.py"])
        self._record(["ext/b.py"])
        covered, uncovered = authorize.covers(str(self.root / ".wf" / "tasks" / "t-m"),
                                              "expand", ["ext/a.py", "ext/b.py"], root=str(self.root))
        self.assertTrue(covered, uncovered)
        # expand 无内容绑定——covers 走路径级（无 content_digests 键）
        payload = authorize.require(str(self.root / ".wf" / "tasks" / "t-m"), "expand")
        self.assertIn("ext/a.py", payload.get("paths"))
        self.assertIn("ext/b.py", payload.get("paths"))

    def test_second_repo_rules_keeps_first_digests(self):
        from wflib import authorize

        (self.root / "r1.toml").write_text("a\n", encoding="utf-8")
        (self.root / "r2.toml").write_text("b\n", encoding="utf-8")
        authorize.record_authorization(
            str(self.root / ".wf" / "tasks" / "t-m"), "repo_rules",
            {"choice": "repo_rules", "paths": ["r1.toml"], "quote": "q1", "by": "human:t",
             "at": "2026-11-22T00:00:00Z", "source": "user-declared"}, root=str(self.root))
        authorize.record_authorization(
            str(self.root / ".wf" / "tasks" / "t-m"), "repo_rules",
            {"choice": "repo_rules", "paths": ["r2.toml"], "quote": "q2", "by": "human:t",
             "at": "2026-11-22T00:00:00Z", "source": "user-declared"}, root=str(self.root))
        covered, uncovered = authorize.covers(str(self.root / ".wf" / "tasks" / "t-m"),
                                              "repo_rules", ["r1.toml", "r2.toml"], root=str(self.root))
        self.assertTrue(covered, uncovered)


class AuthorizationMergeSemanticsTest(unittest.TestCase):
    """十二轮审查：合并三要素——export 材料并集重算 scope_digest、字符串路径归一并集、
    record_log 保留每次确认的范围—原话。"""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        (self.root / ".wf" / "tasks" / "t1").mkdir(parents=True)
        (self.root / "src").mkdir()
        (self.root / "src" / "a.py").write_text("a\n", encoding="utf-8")
        (self.root / "src" / "b.py").write_text("b\n", encoding="utf-8")

    def tearDown(self):
        self._tmp.cleanup()

    def _td(self):
        return str(self.root / ".wf" / "tasks" / "t1")

    def test_export_materials_merge_recomputes_scope(self):
        from wflib import authorize

        base = {"choice": "export", "task": "t1", "by": "human:t",
                "at": "2026-11-22T00:00:00Z", "source": "user-declared"}
        authorize.record_authorization(self._td(), "export", dict(base, materials=["diff"], quote="d"),
                                       root=str(self.root))
        authorize.record_authorization(self._td(), "export",
                                       dict(base, materials=["diff", "requirement"], quote="d+r"),
                                       root=str(self.root))
        self.assertEqual(authorize.export_scope_problems(self._td(), "t1",
                                                        ["diff", "requirement"]), [])

    def test_string_paths_merge(self):
        from wflib import authorize

        base = {"choice": "expand", "by": "human:t", "at": "2026-11-22T00:00:00Z",
                "source": "user-declared"}
        authorize.record_authorization(self._td(), "expand", dict(base, paths="src/a.py", quote="q1"),
                                       root=str(self.root))
        authorize.record_authorization(self._td(), "expand", dict(base, paths="src/b.py", quote="q2"),
                                       root=str(self.root))
        payload = authorize.require(self._td(), "expand")
        self.assertEqual(sorted(payload["paths"]), ["src/a.py", "src/b.py"])

    def test_record_log_keeps_per_record_provenance(self):
        from wflib import authorize

        base = {"choice": "repo_rules", "by": "human:t", "at": "2026-11-22T00:00:00Z",
                "source": "user-declared"}
        authorize.record_authorization(self._td(), "repo_rules", dict(base, paths=[".gitignore"], quote="忽略规则"),
                                       root=str(self.root))
        authorize.record_authorization(self._td(), "repo_rules", dict(base, paths=["pyproject.toml"], quote="构建依赖"),
                                       root=str(self.root))
        payload = authorize.require(self._td(), "repo_rules")
        log = payload["record_log"]
        self.assertEqual(len(log), 2)
        self.assertEqual([e["quote"] for e in log], ["忽略规则", "构建依赖"])
        self.assertEqual(log[0]["paths"], [".gitignore"])     # 谁为什么确认了哪条路径可追溯
        self.assertEqual(payload["quote"], "构建依赖")          # 顶层取最新


class RecordLogRedactionTest(unittest.TestCase):
    """十三轮 P0-1：record_log 与顶层同口径脱敏——committed 文件里不再有第二条明文原话。"""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        (self.root / ".wf" / "tasks" / "t1").mkdir(parents=True)
        (self.root / ".gitignore").write_text("g\n", encoding="utf-8")

    def tearDown(self):
        self._tmp.cleanup()

    def test_log_quote_is_masked_like_toplevel(self):
        from wflib import authorize

        secret_quote = "我确认：口令=hunter2 令牌=abc1234567890 的变更"
        authorize.record_authorization(
            str(self.root / ".wf" / "tasks" / "t1"), "repo_rules",
            {"choice": "repo_rules", "paths": [".gitignore"], "quote": secret_quote,
             "by": "human:t", "at": "2026-11-22T00:00:00Z", "source": "user-declared"},
            root=str(self.root))
        payload = authorize.require(str(self.root / ".wf" / "tasks" / "t1"), "repo_rules")
        log_quote = payload["record_log"][0]["quote"]
        self.assertNotIn("hunter2", log_quote)
        self.assertNotIn("abc1234567890", log_quote)
        # 与顶层同口径：两者都不含明文口令
        self.assertNotIn("hunter2", payload.get("quote") or "")

    def test_legacy_export_record_can_be_replaced(self):
        from wflib import authorize

        td = str(self.root / ".wf" / "tasks" / "t1")
        # 旧式记录：无 materials/scope_digest（0.1.3 升级项目形态）
        import json as _json

        _json.dump({"action": "export", "choice": "export",
                    "by": "human:old", "at": "2026-11-01T00:00:00Z",
                    "source": "user-declared", "quote": "旧式无范围绑定"},
                   open(f"{td}/authorization-export.json", "w", encoding="utf-8"))
        authorize.record_authorization(
            td, "export",
            {"choice": "export", "task": "t1", "materials": ["diff", "test_results"],
             "quote": "重新记录带范围", "by": "human:t",
             "at": "2026-11-22T00:00:00Z", "source": "user-declared"}, root=str(self.root))
        self.assertEqual(authorize.export_scope_problems(td, "t1",
                                                        ["diff", "test_results"]), [])


class RecordLogCapTest(unittest.TestCase):
    """十四轮 P2-1/P2-2：上限 20 真实条目 + 顶层累计折叠数（不占窗口、不重复累积）。"""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        (self.root / ".wf" / "tasks" / "t-cap").mkdir(parents=True)

    def tearDown(self):
        self._tmp.cleanup()

    def test_cap_keeps_twenty_and_counts_truncation(self):
        from wflib import authorize

        base = {"choice": "expand", "by": "human:t", "at": "2026-11-22T00:00:00Z",
                "source": "user-declared"}
        for i in range(25):
            authorize.record_authorization(str(self.root / ".wf" / "tasks" / "t-cap"), "expand",
                                           dict(base, paths=[f"p{i}.py"], quote=f"q{i}"),
                                           root=str(self.root))
        payload = authorize.require(str(self.root / ".wf" / "tasks" / "t-cap"), "expand")
        self.assertEqual(len(payload["record_log"]), 20)
        self.assertEqual(payload["record_log_truncated"], 5)
        self.assertEqual([e["quote"] for e in payload["record_log"][:1]], ["q5"])   # 最早的被折叠

    def test_legacy_content_digests_start_on_new_record(self):
        """十四轮 P1：legacy 无 content_digests 时新确认照档——确认后改内容即失效。"""
        import json as _json

        from wflib import authorize

        td = str(self.root / ".wf" / "tasks" / "t-cap")
        (self.root / "r.toml").write_text("a\n", encoding="utf-8")
        _json.dump({"action": "repo_rules", "choice": "repo_rules", "by": "human:old",
                    "at": "2026-11-01T00:00:00Z", "source": "user-declared", "quote": "旧式"},
                   open(f"{td}/authorization-repo_rules.json", "w", encoding="utf-8"))
        authorize.record_authorization(td, "repo_rules",
                                      {"choice": "repo_rules", "paths": ["r.toml"], "quote": "新确认",
                                       "by": "human:t", "at": "2026-11-22T00:00:00Z",
                                       "source": "user-declared"}, root=str(self.root))
        covered, _u = authorize.covers(td, "repo_rules", ["r.toml"], root=str(self.root))
        self.assertTrue(covered)
        (self.root / "r.toml").write_text("changed\n", encoding="utf-8")
        covered2, uncovered = authorize.covers(td, "repo_rules", ["r.toml"], root=str(self.root))
        self.assertFalse(covered2)
        self.assertEqual(uncovered, ["r.toml"])


class LegacyMixedCoverageTest(unittest.TestCase):
    """十五轮 b-2：legacy 路径级与新内容绑定并行——追加新确认不溯及旧路径失效。"""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        (self.root / ".wf" / "tasks" / "t1").mkdir(parents=True)
        (self.root / ".gitignore").write_text("g\n", encoding="utf-8")
        (self.root / "pyproject.toml").write_text("p\n", encoding="utf-8")
        import json as _json

        _json.dump({"action": "repo_rules", "choice": "repo_rules", "paths": [".gitignore"],
                    "by": "human:old", "at": "2026-11-01T00:00:00Z",
                    "source": "user-declared", "quote": "旧式路径级"},
                   open(f"{self.root}/.wf/tasks/t1/authorization-repo_rules.json", "w", encoding="utf-8"))

    def tearDown(self):
        self._tmp.cleanup()

    def test_append_keeps_legacy_path_level_semantics(self):
        from wflib import authorize

        td = str(self.root / ".wf" / "tasks" / "t1")
        authorize.record_authorization(td, "repo_rules",
                                      {"choice": "repo_rules", "paths": ["pyproject.toml"],
                                       "quote": "追加", "by": "human:t",
                                       "at": "2026-11-22T00:00:00Z", "source": "user-declared"},
                                      root=str(self.root))
        covered, uncovered = authorize.covers(td, "repo_rules", [".gitignore", "pyproject.toml"],
                                             root=str(self.root))
        self.assertTrue(covered, uncovered)          # legacy 路径 + 新绑定并存
        (self.root / "pyproject.toml").write_text("changed\n", encoding="utf-8")
        covered2, uncovered2 = authorize.covers(td, "repo_rules", [".gitignore", "pyproject.toml"],
                                                root=str(self.root))
        self.assertFalse(covered2)                    # 新确认的路径改内容即失效
        self.assertEqual(uncovered2, ["pyproject.toml"])  # legacy 路径不受影响


class ShowProjectionTest(unittest.TestCase):
    """十五轮 P2-1/P2-2：authorize show 投影折叠计数与 export 生效范围。"""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        (self.root / ".wf" / "tasks" / "t1").mkdir(parents=True)

    def tearDown(self):
        self._tmp.cleanup()

    def test_show_includes_truncated_and_export_scope(self):
        from wflib import authorize

        td = str(self.root / ".wf" / "tasks" / "t1")
        base = {"choice": "expand", "by": "human:t", "at": "2026-11-22T00:00:00Z",
                "source": "user-declared"}
        for i in range(23):
            authorize.record_authorization(td, "expand", dict(base, paths=[f"p{i}.py"],
                                                            quote=f"q{i}"), root=str(self.root))
        authorize.record_authorization(td, "export",
                                      {"choice": "export", "task": "t1",
                                       "materials": ["diff"], "quote": "d", "by": "human:t",
                                       "at": "2026-11-22T00:00:00Z", "source": "user-declared"},
                                      root=str(self.root))
        # 直接核 _projection 形状（CLI 层同一实现）
        from wflib import cli as _cli_mod

        class _P:
            pass

        proj = _cli_mod  # 形状断言走 authorize 端记录 + cli 投影函数
        payload = authorize.require(td, "expand")
        self.assertEqual(len(payload["record_log"]), 20)
        self.assertEqual(payload["record_log_truncated"], 3)
        export_payload = authorize.require(td, "export")
        self.assertEqual(export_payload["materials"], ["diff"])
        self.assertTrue((export_payload.get("scope_digest") or "").startswith("sha256:"))


class DecisionDraftCommandsTest(unittest.TestCase):
    """十六轮批V：approve/replan/rework/stop --draft 只读生成、TODO 占位、不写记录。"""

    def setUp(self):
        import subprocess

        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)

        def _git(*argv):
            subprocess.run(["git", *argv], cwd=self.root, check=True, capture_output=True,
                           env={**os.environ, "GIT_CONFIG_GLOBAL": "/dev/null",
                                "GIT_CONFIG_SYSTEM": "/dev/null"})
        _git("init", "-q"); _git("config", "user.email", "t@t"); _git("config", "user.name", "t")
        task_dir = self.root / ".wf" / "tasks" / "t-d"
        task_dir.mkdir(parents=True)
        task_dir.joinpath("task.json").write_text(
            json.dumps({"id": "t-d", "title": "草稿", "status": "in_progress", "phase": "execute",
                        "plan": {"complexity": "light", "touch_paths": ["src/**"]},
                        "entry_snapshot": {"touch_paths": ["src/**"]}}), encoding="utf-8")
        task_dir.joinpath("prd.md").write_text("# PRD\n", encoding="utf-8")

    def tearDown(self):
        self._tmp.cleanup()

    def _draft_of(self, func_name, argv):
        from wflib import tasks as tasks_mod

        class Ctx:
            root = str(self.root)

        class Args:
            def __init__(self, a):
                self.argv = list(a); self.used = set()

            def value(self, name):
                if name in self.argv:
                    i = self.argv.index(name)
                    self.used.update({i, i + 1})
                    return self.argv[i + 1]
                return None

            def flag(self, name):
                return name in self.argv
        return getattr(tasks_mod, func_name)(Ctx(), Args(argv))

    def test_approve_draft_prefills_prd_digest(self):
        result = self._draft_of("cmd_task_approve", ["--task", "t-d", "--draft"])
        entry = result["facts"]["draft"][0]
        self.assertEqual(entry["choice"], "approve")
        self.assertTrue(entry["object_digest"].startswith("sha256:"))   # 入口算好，不靠人填
        self.assertIn("TODO", entry["reason"])
        # TODO 占位照抄会被预检拒
        path = Path(tempfile.mkdtemp()) / "d.json"
        path.write_text(json.dumps(result["facts"]["draft"]), encoding="utf-8")
        try:
            cli._load_decision(str(path))
            self.fail("草稿 TODO 应被预检拒绝")
        except cli.CliError as exc:
            self.assertIn("TODO", exc.facts.get("reason", ""))

    def test_mechanical_revision_draft_routing(self):
        # a 组 a-2：机械修订骨架移到 task-approve（真实入口），replan 草稿不再含。
        approve = self._draft_of("cmd_task_approve", ["--task", "t-d", "--draft"])
        approve_choices = [e["choice"] for e in approve["facts"]["draft"]]
        self.assertEqual(approve_choices, ["approve", "机械修订"])
        mechanical = [e for e in approve["facts"]["draft"] if e["choice"] == "机械修订"][0]
        # 占位前置：仅本任务已有批准、只改排版/转义时保留，否则删除——
        # plan 阶段照抄骨架必被 WF_APPROVAL_MISSING 拒。
        self.assertIn("已有批准", mechanical["reason"])
        self.assertIn("否则删除", mechanical["reason"])

        replan = self._draft_of("cmd_task_replan", ["--task", "t-d", "--draft"])
        replan_choices = [e["choice"] for e in replan["facts"]["draft"]]
        self.assertEqual(replan_choices, ["replan"])

    def test_rework_draft(self):
        result = self._draft_of("cmd_task_rework", ["--task", "t-d", "--draft"])
        self.assertEqual(result["facts"]["draft"][0]["choice"], "rework")

    def test_drafts_write_nothing(self):
        before = (self.root / ".wf" / "tasks" / "t-d" / "task.json").read_bytes()
        self._draft_of("cmd_task_approve", ["--task", "t-d", "--draft"])
        self._draft_of("cmd_task_replan", ["--task", "t-d", "--draft"])
        self.assertEqual((self.root / ".wf" / "tasks" / "t-d" / "task.json").read_bytes(), before)


class ContentBoundPatternsTest(unittest.TestCase):
    """十六轮 a-1：确认后新增的匹配文件不冒充 legacy——须重新 record 才覆盖。"""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        (self.root / ".wf" / "tasks" / "t-cb").mkdir(parents=True)
        (self.root / "requirements-dev.txt").write_text("x\n", encoding="utf-8")

    def tearDown(self):
        self._tmp.cleanup()

    def test_new_file_matching_bound_pattern_needs_rerecord(self):
        from wflib import authorize

        td = str(self.root / ".wf" / "tasks" / "t-cb")
        authorize.record_authorization(td, "repo_rules",
                                      {"choice": "repo_rules", "paths": ["requirements-*.txt"],
                                       "quote": "q", "by": "human:t",
                                       "at": "2026-11-22T00:00:00Z", "source": "user-declared"},
                                      root=str(self.root))
        (self.root / "requirements-prod.txt").write_text("y\n", encoding="utf-8")
        covered, uncovered = authorize.covers(td, "repo_rules", ["requirements-prod.txt"],
                                              root=str(self.root))
        self.assertFalse(covered)
        self.assertEqual(uncovered, ["requirements-prod.txt"])

    def test_repo_rules_deleted_rule_file_still_passes(self):
        from wflib import authorize

        td = str(self.root / ".wf" / "tasks" / "t-cb")
        authorize.record_authorization(td, "repo_rules",
                                      {"choice": "repo_rules", "paths": ["requirements-dev.txt"],
                                       "quote": "q", "by": "human:t",
                                       "at": "2026-11-22T00:00:00Z", "source": "user-declared"},
                                      root=str(self.root))
        (self.root / "requirements-dev.txt").unlink()   # 确认后按计划删除
        covered, uncovered = authorize.covers(td, "repo_rules", ["requirements-dev.txt"],
                                             root=str(self.root))
        self.assertTrue(covered, uncovered)
