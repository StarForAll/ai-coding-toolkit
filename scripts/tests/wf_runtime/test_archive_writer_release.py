"""归档收尾：正常持久化成功后释放写权，释放失败只报告事实。

防的失败（dogfood / 分析报告）：任务已归档，写者仍 held，下一会话必须手工 `writer release`；
模型忘记时尾部残留。
"""

import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "docs" / "workflows" / "wf" / "payload" / "lib"))

from wflib import cli, tasks  # noqa: E402


class ArchiveReleaseTest(unittest.TestCase):
    def _ctx(self, state="held"):
        writer = {"state": state, "generation": 3,
                  "holder": {"kind": "session", "id": "sess-test", "generation": 3}}
        ctx = SimpleNamespace(root="/tmp/not-used", writer=lambda: writer,
                              key=lambda: "sess-test")
        ctx.require_held = lambda task=None: (None, writer["holder"])
        return ctx

    def test_held_writer_is_released(self):
        ctx = self._ctx()
        with mock.patch.object(cli, "_release_writer_locked",
                               return_value=({"generation": 4}, {"ok": True})) as release:
            facts = tasks._release_after_archive(ctx, "t1")
        self.assertTrue(facts["released"])
        self.assertEqual(facts["generation"], 4)
        self.assertTrue(release.called)

    def test_idle_writer_is_not_released_again(self):
        ctx = self._ctx(state="idle")
        with mock.patch.object(cli, "_release_writer_locked") as release:
            facts = tasks._release_after_archive(ctx, "t1")
        self.assertTrue(facts["released"])
        self.assertTrue(facts["already"])
        self.assertFalse(release.called)

    def test_release_is_idempotent_when_idle(self):
        ctx = self._ctx(state="idle")
        result = cli._writer_release(ctx)
        self.assertEqual(result["code"], "WF_OK")
        self.assertTrue(result["facts"]["already_idle"])

    def test_release_failure_is_a_fact_not_an_archive_failure(self):
        ctx = self._ctx()
        with mock.patch.object(cli, "_release_writer_locked",
                               side_effect=cli.CliError("WF_WRITER_BUSY", {"holder": "other"})):
            facts = tasks._release_after_archive(ctx, "t1")
        self.assertFalse(facts["released"])
        self.assertEqual(facts["code"], "WF_WRITER_BUSY")
        self.assertIn("writer release", facts["next"])


if __name__ == "__main__":
    unittest.main()
