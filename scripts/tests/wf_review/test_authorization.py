"""P4/K6：五类不可逆动作的确认、脱敏入库与仓库级规则文件守卫。

防的失败（dogfood F1/F2 与 v42 §2）：授权被当成"模型转录的 human:chat"塞进自由文本；
改 `.gitignore`/依赖清单这种"改变所有后续任务环境"的动作没有任何一次确认；
外发内容与删除清单的原文直接进了 commit。
"""

import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "docs" / "workflows" / "wf" / "payload" / "lib"))

from wflib import authorize, protocol  # noqa: E402


class RedactionTest(unittest.TestCase):
    DECISION = {"choice": "commit", "paths": ["src/a.py"], "content": "外发全文：客户数据",
                "items": [{"path": "x", "detail": "删除明细"}], "quote": "人已确认", "human": "xzc"}

    def test_runtime_only_fields_are_dropped(self):
        kept, _digest = authorize.redact(self.DECISION)
        self.assertNotIn("content", kept)
        self.assertNotIn("items", kept)
        self.assertEqual(kept["paths"], ["src/a.py"])
        self.assertEqual(kept["quote"], "人已确认")

    def test_kept_copy_carries_original_digest_and_redaction_record(self):
        kept, digest = authorize.redact(self.DECISION)
        self.assertEqual(kept["original_digest"], digest)
        self.assertEqual(kept["redaction"]["source"], "protocol/redaction.json")
        self.assertIn("content", kept["redaction"]["dropped_keys"])

    def test_digest_is_recomputable_from_the_original(self):
        _kept, digest = authorize.redact(self.DECISION)
        _again, second = authorize.redact(dict(self.DECISION))
        self.assertEqual(digest, second)


class AuthorizationFileTest(unittest.TestCase):
    def test_authorization_lands_in_task_dir_redacted(self):
        with tempfile.TemporaryDirectory() as tmp:
            task_dir = Path(tmp) / ".wf/tasks/2026-x"
            task_dir.mkdir(parents=True)
            runtime = Path(tmp) / ".wf/.runtime/decisions"
            info = authorize.record_authorization(task_dir, "repo_rules",
                                                  {"choice": "commit", "content": "秘密全文",
                                                   "paths": [".gitignore"]},
                                                  raw_copy_dir=runtime)
            committed = Path(info["path"]).read_text(encoding="utf-8")
            self.assertIn(".gitignore", committed)
            self.assertNotIn("秘密全文", committed)
            raw = (runtime / "authorization-repo_rules.raw.json").read_text(encoding="utf-8")
            self.assertIn("秘密全文", raw)          # 敏感原文只在 runtime
            self.assertIsNotNone(authorize.require(task_dir, "repo_rules"))
            self.assertIsNone(authorize.require(task_dir, "delete"))

    def test_unknown_action_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):
                authorize.record_authorization(tmp, "随便", {})


class RepoRuleSetTest(unittest.TestCase):
    def test_set_comes_from_protocol(self):
        rules = protocol.repo_rules()
        self.assertIn(".gitignore", rules["patterns"])
        self.assertIn("pyproject.toml", rules["patterns"])
        self.assertTrue(rules["why"].strip())

    def test_matching_uses_the_registry(self):
        self.assertTrue(authorize.is_repo_rule(None, ".gitignore"))
        self.assertTrue(authorize.is_repo_rule(None, "requirements-dev.txt"))
        self.assertTrue(authorize.is_repo_rule(None, ".github/workflows/ci.yml"))
        self.assertFalse(authorize.is_repo_rule(None, "src/app.py"))
        self.assertEqual(authorize.repo_rule_paths(None, [".gitignore", "src/app.py"]), [".gitignore"])


if __name__ == "__main__":
    unittest.main()


class CoverageTest(unittest.TestCase):
    """K6 第 2/4 类：确认必须覆盖具体路径（glob 允许），没确认就整批未覆盖。"""

    def test_no_authorization_means_nothing_covered(self):
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            covered, uncovered = authorize.covers(tmp, "expand", ["src/x.py"])
        self.assertFalse(covered)
        self.assertEqual(uncovered, ["src/x.py"])

    def test_glob_authorization_covers_the_path(self):
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            authorize.record_authorization(tmp, "expand",
                                           {"choice": "expand", "paths": ["src/**"], "quote": "人确认扩面"})
            covered, uncovered = authorize.covers(tmp, "expand", ["src/x.py", "src/deep/y.py"])
        self.assertTrue(covered)
        self.assertEqual(uncovered, [])

    def test_partial_coverage_reports_the_rest(self):
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            authorize.record_authorization(tmp, "delete",
                                           {"choice": "delete", "paths": ["docs/old.md"], "quote": "人确认删除"})
            covered, uncovered = authorize.covers(tmp, "delete", ["docs/old.md", "docs/other.md"])
        self.assertFalse(covered)
        self.assertEqual(uncovered, ["docs/other.md"])

    def test_authorization_for_another_action_does_not_count(self):
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            authorize.record_authorization(tmp, "delete", {"choice": "delete", "paths": ["src/**"]})
            covered, uncovered = authorize.covers(tmp, "expand", ["src/x.py"])
        self.assertFalse(covered)


class ArchiveContractTest(unittest.TestCase):
    def test_archive_reports_three_stages_and_guards(self):
        source = (REPO / "docs/workflows/wf/payload/lib/wflib/tasks.py").read_text(encoding="utf-8")
        self.assertIn('"stage": "business"', source)
        self.assertIn('"stage": "record"', source)
        self.assertIn('"stage": "runtime"', source)
        self.assertIn("vendor_paths", source)          # K5 守卫
        self.assertIn("repo_rule_paths", source)       # K6 第 5 类守卫
        self.assertIn("_deleted_paths", source)        # K6 第 2 类守卫


class EntryPointContractTest(unittest.TestCase):
    """确认必须有人执行入口，否则守卫会因为"永远没有确认文件"而一律阻断。"""

    def test_authorize_command_exists(self):
        from wflib import cli

        self.assertIn("authorize", cli.COMMANDS)
        self.assertIn("authorize", cli.COMMAND_HELP)
        help_entry = cli.COMMAND_HELP["authorize"]
        self.assertIn("record", help_entry["purpose"])

    def test_authorize_records_all_four_actions_from_one_file(self):
        """一条命令能落多类确认（人的一次决定覆盖多类动作），且每类单独成文件。

        W2-1（三轮裁决②）：`commit` 类已从 authorize ACTIONS 删除——提交授权唯一
        通道是 finish 决定的 commit_grants；此处按真实四类断言。
        """
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            for action in ("delete", "export", "expand", "repo_rules"):
                decision = {"choice": action, "paths": ["src/x.py"], "quote": "人确认"}
                if action == "export":
                    # 外发确认必须绑定"本次范围"：任务 + 材料类集合
                    decision.update({"task": "t1",
                                     "materials": ["diff", "requirement", "test_results"]})
                info = authorize.record_authorization(tmp, action, decision)
                self.assertTrue(Path(info["path"]).is_file())
                self.assertIsNotNone(authorize.require(tmp, action))
            self.assertEqual(sorted(authorize.ACTIONS),
                             ["delete", "expand", "export", "repo_rules"])

    def test_commit_choice_is_rejected_with_real_actions(self):
        """W2-1：choice=commit 不再是 authorize 动作类——record_authorization 直接拒绝，
        CLI record 分支按 ACTIONS 白名单给出真实四类出口。"""
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):
                authorize.record_authorization(tmp, "commit", {"choice": "commit", "paths": ["src/**"]})
        source = (REPO / "docs/workflows/wf/payload/lib/wflib/authorize.py").read_text(encoding="utf-8")
        self.assertNotIn('"commit": "提交 / 推送"', source)
        self.assertIn("commit_grants", source)   # 唯一通道句在模块 docstring 声明

    def test_export_guard_is_wired_into_launch(self):
        source = (REPO / "docs/workflows/wf/payload/lib/wflib/review.py").read_text(encoding="utf-8")
        self.assertIn('"export"', source)
        self.assertIn("export_scope_problems", source)
        self.assertIn("missing_action", source)


class DeletedPathTest(unittest.TestCase):
    """K6 第 2 类只认**真删除**（HEAD 有、工作树没有），否则每次归档都被要求补确认。

    用临时 Git 仓库做夹具：不依赖本仓库的工作区状态（否则干净 clone 里会红）。
    """

    def _repo(self, tmp):
        import subprocess

        subprocess.run(["git", "init", "-q"], cwd=tmp, check=True)
        subprocess.run(["git", "config", "user.email", "t@example.com"], cwd=tmp, check=True)
        subprocess.run(["git", "config", "user.name", "t"], cwd=tmp, check=True)
        (Path(tmp) / "keep.md").write_text("keep\n", encoding="utf-8")
        (Path(tmp) / "gone.md").write_text("gone\n", encoding="utf-8")
        subprocess.run(["git", "add", "-A"], cwd=tmp, check=True)
        subprocess.run(["git", "commit", "-qm", "init"], cwd=tmp, check=True)
        (Path(tmp) / "gone.md").unlink()
        return tmp

    def test_only_real_deletions_count(self):
        from wflib import tasks

        with tempfile.TemporaryDirectory() as tmp:
            self._repo(tmp)
            found = tasks._deleted_paths(tmp, ["keep.md", "no/such/file.md", "gone.md"])
        self.assertEqual(found, ["gone.md"])

    def test_empty_input_returns_empty(self):
        from wflib import tasks

        with tempfile.TemporaryDirectory() as tmp:
            self._repo(tmp)
            self.assertEqual(tasks._deleted_paths(tmp, []), [])
