"""C2 的启用登记通道。

C2 阻断的出口写"人调 /wf-start 显式登记当前调用者"，但启用入口既不参与 roots 维护，
也从不写 roots——照出口跑一次仍然被同一判据拦下。设计稿 §1.3 规定"仅人调启用入口可登记"。
"""

import sys
import unittest
from pathlib import Path
from unittest import mock

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "docs" / "workflows" / "wf" / "payload" / "lib"))

from wflib import identity_store, session  # noqa: E402

OTHER = {"kind": "pid", "boot": "b", "pid": 111, "start": "1"}
CURRENT = {"kind": "pid", "boot": "b", "pid": 222, "start": "2"}


class ConcurrentRegistrationTest(unittest.TestCase):
    def _attachment(self):
        return {"roots": [dict(OTHER)], "activation_stale": False}

    def _state(self, root, boot, probe=None):
        return session.ALIVE if root.get("pid") == 111 else session.DEAD

    def test_plain_command_blocks_before_upsert(self):
        attachment = self._attachment()
        with mock.patch.object(session, "state_of_root", side_effect=self._state):
            verdict = identity_store.maintain_roots(attachment, CURRENT)
        self.assertEqual(verdict["action"], "block")
        self.assertEqual(verdict["reason"], identity_store.CONCURRENT_CALLER)
        # 阻断先于 upsert：附件里仍只有旧根
        self.assertEqual(attachment["roots"], [OTHER])

    def test_enable_registers_current_root(self):
        attachment = self._attachment()
        with mock.patch.object(session, "state_of_root", side_effect=self._state):
            verdict = identity_store.maintain_roots(attachment, CURRENT, allow_concurrent=True)
        self.assertEqual(verdict["action"], "disclose")
        self.assertTrue((verdict.get("facts") or {}).get("registered"))
        pids = sorted(root["pid"] for root in attachment["roots"])
        self.assertIn(222, pids)
        self.assertIn(111, pids)

    def test_enable_is_a_roots_command(self):
        from wflib import cli
        self.assertIn("enable", cli.Context.ROOTS_COMMANDS)


class AuthorizeRequiresByTest(unittest.TestCase):
    def test_record_does_not_synthesize_by_from_source(self):
        import inspect
        from wflib import cli
        source = inspect.getsource(cli.cmd_authorize)
        self.assertNotIn('"human:" + str(entry.get("source"))', source)
        self.assertIn('"by": entry.get("by")', source)


if __name__ == "__main__":
    unittest.main()
