"""P2-13：无锚点时的出口文案不能把「显式信封」写成可行出路（实现稿 §2.3.11）。

机制稿 §1.4：显式 `provider=wf` 信封**一律 `WF_IDENTITY_UNRESOLVED`**（没有本地证据），
自动模式下 `issued_id` 由入口在执行边界派生并落在附件里；唯一可用的显式通道是
`provider=host`（宿主能给出稳定 `session_id`）。

历史文案在四处写「用显式信封（--envelope/stdin）」而不点明 provider，等于把一条**会被拒**
的路写成出路。现在四处共用一个常量，文案本身也说明 wf 信封会被拒。

本文件是文本断言：这个缺陷就是文案，没有别的事实可核。
"""

import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
LIB = REPO / "docs" / "workflows" / "wf" / "payload" / "lib"
sys.path.insert(0, str(LIB))

from wflib import cli  # noqa: E402


class IdentityExitTextTest(unittest.TestCase):
    def setUp(self):
        self.source = (LIB / "wflib" / "cli.py").read_text(encoding="utf-8")

    def test_constant_names_the_only_viable_provider(self):
        text = cli.EXPLICIT_ENVELOPE_EXIT
        self.assertIn("provider=host", text)
        self.assertIn("session_id", text)
        self.assertIn("provider=wf", text)
        self.assertIn("会被拒", text)

    def test_no_exit_offers_the_bare_envelope_as_a_way_out(self):
        for bogus in ('"用显式信封（--envelope/stdin）"', '"无法判断时改用显式信封"',
                      '"或用显式信封"'):
            with self.subTest(text=bogus):
                self.assertNotIn(bogus, self.source)

    def test_every_no_anchor_exit_uses_the_shared_constant(self):
        """四处（identity 分支 / no execution boundary / roots 未知证据 / bind 侧）都必须引用它。"""
        self.assertGreaterEqual(self.source.count("EXPLICIT_ENVELOPE_EXIT"), 5,
                               "常量定义 1 处 + 出口引用至少 4 处")


if __name__ == "__main__":
    unittest.main()
