"""R5：`task-approve` 帮助里的取值域由 `decisions.DOMAINS` 生成。

dogfood 的病灶是帮助与登记域各写一份（帮助写 `approve-light|approve-complex|mechanical`，
登记域只接受 `approve/批准` 与 `机械修订`）。本用例要求帮助文本里出现的每个取值都能被
对应域接受，且旧写法不再出现。
"""

import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "docs" / "workflows" / "wf" / "payload" / "lib"))

from wflib import cli, decisions  # noqa: E402


def _choice_help():
    inputs = cli.COMMAND_HELP["task-approve"]["inputs"]
    entry = inputs.get("decision[]") or {}
    return str(entry.get("choice") or "")


class HelpDomainTest(unittest.TestCase):
    def test_every_listed_choice_is_registered(self):
        text = _choice_help()
        self.assertIn("批准：", text)
        self.assertIn("机械修订：", text)
        approval, _, rest = text.partition("；")
        mechanical = rest.split("（", 1)[0]
        for token in approval.split("：", 1)[1].split("|"):
            self.assertTrue(decisions.accepts("plan_approval", token.strip()), token)
        for token in mechanical.split("：", 1)[1].split("|"):
            self.assertTrue(decisions.accepts("mechanical_revision", token.strip()), token)

    def test_stale_choices_are_gone(self):
        text = _choice_help()
        for stale in ("approve-light", "approve-complex", "mechanical"):
            self.assertNotIn(stale, text)


if __name__ == "__main__":
    unittest.main()
