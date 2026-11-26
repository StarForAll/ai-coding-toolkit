"""准备通道的生命周期不变量（四轮审查：跨定义误释放 + 授权前不占写权）。

- `_end_preparation` 只在"持有的正是这份定义的 preparation 作用域"时释放写权；
  结束 A 的定义不能顺手放掉 B 的准备写权（那会让另一份准备失去单写者保护）。
- 缺授权在**取写权之前**拒绝：请求不成立时不该先占住写权（准备记录也没建立）。
"""

import json
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "docs" / "workflows" / "wf" / "payload" / "lib"))

from wflib import records, runs  # noqa: E402


class _Ctx:
    def __init__(self, root):
        self.root = str(root)

    def key(self):
        return "sess-test"

    def writer(self):
        return records.load_json(str(Path(self.root) / ".wf" / "writer.json"), {}) or {}


class _Args:
    def __init__(self, flags=(), values=None):
        self._flags = set(flags)
        self._values = dict(values or {})

    def flag(self, name):
        return name in self._flags

    def value(self, name):
        return self._values.get(name)


def _preparation(root, workflow_id="alpha"):
    return records.load_json(runs.preparation_path(str(root), workflow_id), None)


class EndPreparationScopeTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="wf-prep-life-")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root / ".wf" / "preparations").mkdir(parents=True)
        (self.root / ".wf" / "user-workflows").mkdir(parents=True)
        # 定义已提交（干净）：收口只考作用域，不考处置
        (self.root / ".wf" / "user-workflows" / "alpha.md").write_text("# alpha\n", encoding="utf-8")
        records.write_json(runs.preparation_path(str(self.root), "alpha"), {
            "schema_version": 1, "id": "alpha", "session_key": "sess-test",
            "scope_paths": [".wf/user-workflows/alpha.md"],
            "authorization": {"source": "decision", "at": records.now_str(),
                              "scope_paths": [".wf/user-workflows/alpha.md"]},
            "validation": {"ok": True, "problems": []}, "ended_at": None,
        })
        self.writer_path = self.root / ".wf" / "writer.json"
        self.held = {"state": "held", "generation": 3,
                     "holder": {"kind": "session", "id": "sess-test",
                                "scope": {"object": {"kind": "preparation", "id": "beta"},
                                          "preparation": {"id": "beta",
                                                          "scope_paths": [".wf/user-workflows/beta.md"]}}}}
        records.write_json(str(self.writer_path), self.held)

    def _end(self, held_scope):
        holder = self.held["holder"]
        return runs._end_preparation(_Ctx(self.root), _Args(), "alpha",
                                     ".wf/user-workflows/alpha.md", self.held, holder, True,
                                     held_scope, _preparation(self.root))

    def test_retain_declaration_for_clean_path_is_refused(self):
        """声明 retain 但路径其实没未提交改动：声明与事实不符，不能静默忽略（自查 F6）。"""
        disposition = self.root / "clean-retain.json"
        disposition.write_text(json.dumps({"changes": [
            {"object": ".wf/user-workflows/alpha.md", "action": "retain",
             "risk": "x", "pending": ["y"]}]}), encoding="utf-8")
        with self.assertRaises(runs.DefinitionError) as caught:
            runs._end_preparation(_Ctx(self.root), _Args(values={"--disposition": str(disposition)}),
                                  "alpha", ".wf/user-workflows/alpha.md", self.held,
                                  self.held["holder"], True, {"kind": "preparation", "id": "alpha"},
                                  _preparation(self.root))
        # 与"声明 commit/delete 却没落实"同一类：工作区事实未成立，统一用 WORKSPACE_UNRESOLVED
        self.assertEqual(caught.exception.code, "WF_WORKSPACE_UNRESOLVED")
        self.assertIn("retain", json.dumps(caught.exception.facts, ensure_ascii=False))

    def test_ending_another_definition_does_not_release_this_scope(self):
        payload = self._end({"kind": "preparation", "id": "beta"})
        facts = payload.get("facts") or {}
        self.assertFalse(facts.get("released"), facts)
        self.assertEqual(((facts.get("held_scope") or {}).get("id")), "beta")
        self.assertTrue((_preparation(self.root) or {}).get("ended_at"), "alpha 记录应已结束")
        writer = records.load_json(str(self.writer_path), {}) or {}
        self.assertEqual(writer.get("state"), "held", "beta 的准备写权被误释放")
        self.assertEqual((((writer.get("holder") or {}).get("scope") or {}).get("object") or {}).get("id"),
                         "beta")

    def test_ending_the_matching_definition_reports_release(self):
        # 只验"作用域匹配才走释放路径"：真实释放（writer 落盘 + 动作登记）由 repro 覆盖，
        # 这里把释放桩掉，断言它确实被调用过一次。
        from wflib import cli as cli_mod

        calls = []
        original = cli_mod._release_writer_locked

        def _stub(ctx, holder):
            calls.append(holder)
            return {"state": "idle"}, {"stub": True}

        cli_mod._release_writer_locked = _stub
        try:
            payload = self._end({"kind": "preparation", "id": "alpha"})
        finally:
            cli_mod._release_writer_locked = original
        facts = payload.get("facts") or {}
        self.assertTrue(facts.get("released"), facts)
        self.assertEqual(len(calls), 1)
        self.assertIsNone(facts.get("held_scope"))

    def test_retain_without_risk_or_pending_is_refused(self):
        """保留草稿是合法出路，但必须记未验证风险与待处置项（设计稿 §1.3）。"""
        import subprocess

        subprocess.run(["git", "init", "-q"], cwd=str(self.root), check=True, capture_output=True)
        subprocess.run(["git", "config", "user.email", "t@example.com"], cwd=str(self.root), check=True,
                       capture_output=True)
        subprocess.run(["git", "config", "user.name", "t"], cwd=str(self.root), check=True,
                       capture_output=True)
        subprocess.run(["git", "add", "."], cwd=str(self.root), check=True, capture_output=True)
        subprocess.run(["git", "commit", "-qm", "base"], cwd=str(self.root), check=True,
                       capture_output=True)
        (self.root / ".wf" / "user-workflows" / "alpha.md").write_text("# alpha 改过\n", encoding="utf-8")
        disposition = self.root / "disposition.json"
        disposition.write_text(json.dumps({"changes": [
            {"object": ".wf/user-workflows/alpha.md", "action": "retain", "risk": "未验证"}]}),
            encoding="utf-8")
        with self.assertRaises(runs.DefinitionError) as caught:
            runs._end_preparation(_Ctx(self.root), _Args(values={"--disposition": str(disposition)}),
                                  "alpha", ".wf/user-workflows/alpha.md", self.held,
                                  self.held["holder"], True, {"kind": "preparation", "id": "alpha"},
                                  _preparation(self.root))
        self.assertEqual(caught.exception.code, "WF_WORKSPACE_UNRESOLVED")
        self.assertIsNone((_preparation(self.root) or {}).get("ended_at"))

    def test_interrupted_end_self_heals_the_write_right(self):
        """上次写完 ended_at 却中断在释放前：重试必须补做释放，不能永久占着写权。

        （准备会话没有 task/run 绑定，通用 `writer release` 拒绝这种对象——写权只能由本入口放。）
        """
        from wflib import cli as cli_mod

        record = _preparation(self.root)
        record["ended_at"] = records.now_str()
        records.write_json(runs.preparation_path(str(self.root), "alpha"), record)
        calls = []
        original = cli_mod._release_writer_locked
        cli_mod._release_writer_locked = lambda ctx, holder: (calls.append(holder),
                                                             ({"state": "idle"}, {"stub": True}))[1]
        try:
            payload = self._end({"kind": "preparation", "id": "alpha"})
        finally:
            cli_mod._release_writer_locked = original
        facts = payload.get("facts") or {}
        self.assertTrue(facts.get("released"), facts)
        self.assertEqual(len(calls), 1, "已结束但写权仍在时没有补做释放")

    def test_uncommitted_edits_block_ending(self):
        import subprocess

        subprocess.run(["git", "init", "-q"], cwd=str(self.root), check=True, capture_output=True)
        subprocess.run(["git", "config", "user.email", "t@example.com"], cwd=str(self.root), check=True,
                       capture_output=True)
        subprocess.run(["git", "config", "user.name", "t"], cwd=str(self.root), check=True,
                       capture_output=True)
        subprocess.run(["git", "add", "."], cwd=str(self.root), check=True, capture_output=True)
        subprocess.run(["git", "commit", "-qm", "base"], cwd=str(self.root), check=True,
                       capture_output=True)
        (self.root / ".wf" / "user-workflows" / "alpha.md").write_text("# alpha 改过\n", encoding="utf-8")
        with self.assertRaises(runs.DefinitionError) as caught:
            self._end({"kind": "preparation", "id": "alpha"})
        self.assertEqual(caught.exception.code, "WF_WORKSPACE_UNRESOLVED")
        self.assertIsNone((_preparation(self.root) or {}).get("ended_at"))


class RetainedPreparationWipTest(unittest.TestCase):
    """保留记录的**消费侧**：内容变了就不能再算已处置（六轮审查 a-1/b-3）。"""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="wf-prep-retain-")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root / ".wf" / "preparations").mkdir(parents=True)
        (self.root / ".wf" / "user-workflows").mkdir(parents=True)
        self.draft = self.root / ".wf" / "user-workflows" / "alpha.md"
        # 真的在 Git 工作区里判"是否仍占着工作区"：保留只对**未提交**的草稿成立
        import subprocess

        self.draft.write_text("# alpha 基线\n", encoding="utf-8")
        for command in (["init", "-q"], ["config", "user.email", "t@example.com"],
                        ["config", "user.name", "t"], ["add", "-A"], ["commit", "-qm", "base"]):
            subprocess.run(["git", *command], cwd=str(self.root), check=True, capture_output=True)
        self.draft.write_text("# alpha 草稿\n", encoding="utf-8")
        digest = "sha256:" + records.sha256_hex(self.draft.read_bytes())
        records.write_json(runs.preparation_path(str(self.root), "alpha"), {
            "schema_version": 1, "id": "alpha", "session_key": "sess-test",
            "scope_paths": [".wf/user-workflows/alpha.md"],
            "authorization": {"source": "decision", "at": records.now_str(),
                              "scope_paths": [".wf/user-workflows/alpha.md"]},
            "validation": {"ok": True, "problems": []},
            "ended_at": records.now_str(),
            "retained_wip": [{"path": ".wf/user-workflows/alpha.md",
                              "preparation_scope": [".wf/user-workflows/alpha.md"],
                              "exists": True, "content_digest": digest,
                              "staged": False, "uncommitted": True,
                              "risk": "未静态校验", "pending": ["补齐 steps"],
                              "recorded_at": records.now_str()}],
        })

    def test_matching_content_is_reported_as_owned(self):
        found = runs.retained_preparation_wip(str(self.root))
        self.assertEqual(len(found), 1, found)
        self.assertEqual([item["path"] for item in found[0]["verified"]],
                         [".wf/user-workflows/alpha.md"])
        self.assertEqual(found[0]["stale"], [])

    def test_changed_content_is_stale(self):
        self.draft.write_text("# alpha 又被改过\n", encoding="utf-8")
        found = runs.retained_preparation_wip(str(self.root))
        self.assertEqual(len(found[0]["stale"]), 1, found)
        self.assertEqual(found[0]["verified"], [])

    def test_uncommitted_deletion_is_stale(self):
        """已入库的草稿被删（删除未提交）仍是"占着工作区"，且内容不复存在 → stale。"""
        self.draft.unlink()
        found = runs.retained_preparation_wip(str(self.root))
        self.assertEqual(len(found), 1, found)
        self.assertFalse(found[0]["stale"][0]["exists"])

    def test_committed_draft_clears_the_retention(self):
        """草稿被提交/移走后保留条件落实，不再挡别的对象取写权。"""
        import subprocess

        subprocess.run(["git", "add", ".wf/user-workflows/alpha.md"], cwd=str(self.root),
                       check=True, capture_output=True)
        subprocess.run(["git", "commit", "-qm", "draft"], cwd=str(self.root), check=True,
                       capture_output=True)
        self.assertEqual(runs.retained_preparation_wip(str(self.root)), [])

    def test_repreparing_closes_the_retention_with_drift_record(self):
        """重新准备＝重新占有草稿：保留关闭，并把"离开期间的改动"记进审计。"""
        self.draft.write_text("# alpha 被外部改过\n", encoding="utf-8")
        previous = records.load_json(runs.preparation_path(str(self.root), "alpha"), {})
        drift = runs._retention_drift(self.root, previous["retained_wip"])
        self.assertEqual([item["path"] for item in drift], [".wf/user-workflows/alpha.md"])


class RecoveringWriterTest(unittest.TestCase):
    """写权在交接中间态（recovering）时不能准备定义（六轮审查 b-4）。"""

    def test_prepare_refuses_recovering(self):
        tmp = tempfile.TemporaryDirectory(prefix="wf-prep-recov-")
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        (root / ".wf" / "preparations").mkdir(parents=True)
        (root / ".wf" / "user-workflows").mkdir(parents=True)
        (root / ".wf" / "user-workflows" / "alpha.md").write_text("# a\n", encoding="utf-8")
        records.write_json(str(root / ".wf" / "writer.json"),
                           {"state": "recovering", "generation": 4,
                            "holder": {"kind": "session", "id": "other",
                                       "scope": {"object": {"kind": "preparation", "id": "alpha"}}}})
        with self.assertRaises(runs.DefinitionError) as caught:
            runs.prepare(_Ctx(root), _Args(values={"--id": "alpha"}))
        self.assertEqual(caught.exception.code, "WF_WRITER_BUSY")
        self.assertEqual((caught.exception.facts or {}).get("state"), "recovering")


if __name__ == "__main__":
    unittest.main()
