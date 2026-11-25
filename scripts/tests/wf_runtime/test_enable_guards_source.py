"""启用前置的身份来源（2026-11-25 独立审查 M-1）。

机制稿 §1.4：显式 `provider=wf` 信封没有本地证据，`check_platforms` 只在
`source=auto`（自动身份模式）时放行。启用前置的调用点曾把**入参来源**无条件合成
`auto`，同一个显式 wf 信封在 cf09db12 之前被拒、之后被放行（fail-open）；同一份
facts 还回报 `identity.source=host`，自述面也错。

本用例锁两件事：
1. 显式信封 → 前置按 `explicit` 送检，`provider=wf` 得到 `WF_IDENTITY_UNRESOLVED`；
2. 附件/自动派生 → 仍是 `auto`，自动身份模式不受影响。
"""

import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "docs" / "workflows" / "wf" / "payload" / "lib"))

from wflib import cli  # noqa: E402


class EnableGuardSourceTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        (self.root / ".wf").mkdir()
        self.ctx = cli.Context(str(self.root), [])
        self.ctx.platforms = lambda: []

    def tearDown(self):
        self._tmp.cleanup()

    def test_explicit_wf_envelope_is_rejected_by_enable_guards(self):
        issued = "a" * 32
        shape = cli._enable_guard_session(
            {"provider": "wf", "identity": {"issued_id": issued}},
            {"provider": "wf", "identity": {"issued_id": issued}})
        self.assertEqual(shape["source"], "explicit")
        with self.assertRaises(cli.CliError) as caught:
            cli._enable_guards(self.ctx, shape)
        self.assertEqual(caught.exception.code, "WF_IDENTITY_UNRESOLVED")
        self.assertIn("显式 wf", caught.exception.facts.get("reason", ""))

    def test_auto_identity_still_passes(self):
        issued = "b" * 32
        shape = cli._enable_guard_session(None, {"provider": "wf", "identity": {"issued_id": issued}})
        self.assertEqual(shape["source"], "auto")
        guards = cli._enable_guards(self.ctx, shape)
        self.assertEqual(guards["platforms"]["identity_source"], "auto")

    def test_explicit_host_keeps_explicit_source(self):
        shape = cli._enable_guard_session(
            {"provider": "host", "identity": {"host_id": "dsh", "session_id": "s"}},
            {"provider": "host", "identity": {"host_id": "dsh", "session_id": "s"}})
        self.assertEqual(shape["source"], "explicit")
        self.assertEqual(shape["provider"], "host")


if __name__ == "__main__":
    unittest.main()
