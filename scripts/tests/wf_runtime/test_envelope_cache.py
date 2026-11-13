"""信封缓存按会话隔离：不再共用 `unknown.json`。

防的失败（分析报告）：`provider=wf` 的信封没有 `session_id` 时，两个会话都写
`.wf/.runtime/envelopes/unknown.json`，后写者覆盖先写者；`--envelope-last` 可能读到别人的身份。
"""

import json
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "docs" / "workflows" / "wf" / "payload" / "lib"))

from wflib import cli  # noqa: E402


class EnvelopeCacheTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def _envelope(self, issued_id):
        return {"session": {"provider": "wf", "identity": {"issued_id": issued_id}},
                "inputs": {}}

    def test_wf_sessions_use_distinct_cache_files(self):
        first = "a" * 32
        second = "b" * 32
        cli.remember_envelope(self.root, self._envelope(first),
                              {"facts": {"generation": 1,
                                         "activation": {"enabled": True}}})
        cli.remember_envelope(self.root, self._envelope(second),
                              {"facts": {"generation": 2,
                                         "activation": {"enabled": True}}})
        directory = self.root / ".wf" / ".runtime" / "envelopes"
        names = sorted(item.name for item in directory.iterdir())
        self.assertNotIn("unknown.json", names)
        self.assertIn(f"{first}.json", names)
        self.assertIn(f"{second}.json", names)
        cached = json.loads((directory / f"{second}.json").read_text(encoding="utf-8"))
        self.assertEqual(cached["session"]["identity"]["issued_id"], second)
        self.assertEqual(cached["inputs"]["generation"], 2)

    def test_missing_identity_is_not_cached(self):
        cli.remember_envelope(self.root, {"session": {"provider": "wf", "identity": {}}, "inputs": {}},
                              {"facts": {"generation": 1}})
        directory = self.root / ".wf" / ".runtime" / "envelopes"
        self.assertFalse(directory.exists() and any(directory.iterdir()))


if __name__ == "__main__":
    unittest.main()
