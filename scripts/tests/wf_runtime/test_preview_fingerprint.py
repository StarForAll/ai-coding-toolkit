"""E1+E2：维护入口的预览确认改为 8 位短指纹，且不再打印 32 位随机串。

历史缺陷（backlog E1/E2 · 人裁乙）：
- E1：`repair --dispose` 与 `uninstall --purge` 要求人抄 32 位随机令牌，正常路径没有免抄通道；
- E2：这串随机令牌被打印到 stdout，进日志/滚动缓冲，等于把"确认"变成一个可复制粘贴的字符串。

现在：指纹 = **本次预览摘要的前 8 位**，预览一变指纹就变；漂移防护仍在应用路径——
确认后在同一把锁内重算预览并比对摘要（指纹只回答"确认的是哪一版预览"）。
"""

import hashlib
import importlib.util
import json
import re
import subprocess
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
BIN = REPO / "docs" / "workflows" / "wf" / "payload" / "bin"


def load(name):
    spec = importlib.util.spec_from_file_location(f"wf_{name}", BIN / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class PreviewFingerprintTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.repair = load("repair")

    def test_fingerprint_is_the_first_8_hex_of_the_preview_digest(self):
        preview = {"operation": "x", "paths": ["a"]}
        token = self.repair.PreviewToken()
        issued = token.issue(preview)
        self.assertRegex(issued, r"^[0-9a-f]{8}$")
        self.assertTrue(token.digest().startswith("sha256:"))
        self.assertEqual(issued, token.digest().split(":", 1)[1][:8])
        self.assertTrue(token.confirm(issued))
        self.assertFalse(token.confirm("00000000"))

    def test_same_preview_same_fingerprint_and_different_preview_differs(self):
        first = self.repair.PreviewToken().issue({"paths": ["a"]})
        second = self.repair.PreviewToken().issue({"paths": ["a"]})
        other = self.repair.PreviewToken().issue({"paths": ["b"]})
        self.assertEqual(first, second)          # 派生值，不是随机串
        self.assertNotEqual(first, other)

    def test_invalidated_preview_no_longer_accepts_the_fingerprint(self):
        token = self.repair.PreviewToken()
        issued = token.issue({"paths": ["a"]})
        token.invalidate()
        self.assertFalse(token.confirm(issued))
        self.assertFalse(token.revalidate(issued))

    def test_no_random_long_token_is_printed_or_generated(self):
        for name in ("repair.py", "uninstall.py"):
            source = (BIN / name).read_text(encoding="utf-8")
            self.assertNotIn("令牌", source, f"{name} 仍在打印令牌")
            self.assertNotIn("secrets.token_hex(16)", source,
                             f"{name} 仍在生成 32 位随机令牌")
        # 也不允许在 issue() 里留随机源：指纹必须是预览摘要的派生值
        source = (BIN / "repair.py").read_text(encoding="utf-8")
        issue_body = source[source.index("    def issue(self, preview, nonce=None):"):]
        issue_body = issue_body[:issue_body.index("    def confirm(self")]
        self.assertNotIn("token_hex", issue_body)

    def test_parity_check_prints_an_8_hex_fingerprint(self):
        for name in ("repair.py", "uninstall.py"):
            result = subprocess.run([sys.executable, str(BIN / name), "--token-parity-check"],
                                    capture_output=True, text=True, check=False)
            self.assertEqual(result.returncode, 0, result.stderr)
            match = re.search(r"^fingerprint=([0-9a-f]{8})$", result.stdout, re.M)
            self.assertIsNotNone(match, result.stdout)
            self.assertIn("first=ok", result.stdout)
            self.assertIn("after=expired", result.stdout)


if __name__ == "__main__":
    unittest.main()
