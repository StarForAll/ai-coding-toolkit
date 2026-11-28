"""run 族代次面（2026-11-28 人裁 §47）：五个写入口统一 `ctx.require_held(run=…)"。

入口先核代次再读/写实例记录；旧代次或不携带代次都判 `WF_GENERATION_STALE`（与 task 面同码）。
区分力：删掉任一入口的 require_held 调用，本用例的对应断言即变红。
"""

import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "docs" / "workflows" / "wf" / "payload" / "lib"))

from wflib import cli, runs  # noqa: E402


class RunGenerationTest(unittest.TestCase):
    def _args(self, **flags):
        args = mock.Mock()
        args.value = lambda name: {"--run": "2026-" + "a" * 32, "--reason": "r",
                                   "--plan": "/tmp/p", "--decision": None}.get(name)
        args.flag = lambda name: False
        return args

    def test_five_entries_require_generation(self):
        stale = cli.CliError("WF_GENERATION_STALE", {"reason": "generation not carried"})
        root = tempfile.mkdtemp()
        (Path(root) / ".wf").mkdir(exist_ok=True)
        ctx = mock.Mock(root=root)
        ctx.key = lambda required=True: "s-k"
        ctx.require_held = mock.Mock(side_effect=stale)
        for entry in (runs.advance, runs.pause, runs.finish, runs.resume):
            ctx.require_held.reset_mock()
            with self.assertRaises(cli.CliError) as caught:
                entry(ctx, self._args())
            self.assertEqual(caught.exception.code, "WF_GENERATION_STALE",
                             f"{entry.__name__} must check generation first")
            ctx.require_held.assert_called_with(run="2026-" + "a" * 32)
        # terminate 的代次核在"写权不可核 → 只读收停止请求"之后（机制稿 §7.4 的窄例外）：
        # 该路径先回执请求、不核代次；这是设计顺序，不是漏检。
        plan_file = Path(root) / "plan.json"
        plan_file.write_text("[]", encoding="utf-8")
        targs = mock.Mock()
        targs.value = lambda name: {"--run": "2026-" + "a" * 32, "--plan": str(plan_file)}.get(name)
        targs.flag = lambda name: False
        # 写路径：holder 是本会话且 scope 指向该实例 → 走到 require_held，旧代次即拒。
        ctx.writer = mock.Mock(return_value={"state": "held",
                                             "holder": {"id": "s-k", "generation": 1,
                                                        "scope": {"object": {"kind": "run",
                                                                             "id": "2026-" + "a" * 32}}},
                                             "generation": 1})
        ctx.require_held = mock.Mock(side_effect=stale)
        with self.assertRaises(cli.CliError) as caught:
            runs.terminate(ctx, targs)
        self.assertEqual(caught.exception.code, "WF_GENERATION_STALE")
        ctx.require_held.assert_called_with(run="2026-" + "a" * 32)


if __name__ == "__main__":
    unittest.main()
