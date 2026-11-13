"""D8：验证日志保留完整（遮罩后）输出，截断必须可见。

防的失败（dogfood 第 3 轮）：日志只写最后一行 summary，reviewer 无法确认新测试实际发现了什么；
复核能力取决于人是否另外保留了终端输出。

断言：
1. 小输出：日志含完整输出，无截断标记；
2. 超限输出：保留头尾 + 可见截断标记（含丢弃字节数），记录里仍只有摘要；
3. 秘密边界：`token=` 值在日志里被遮罩（走同一 `redact_text`）。
"""

import os
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "docs" / "workflows" / "wf" / "payload" / "lib"))

from wflib import check  # noqa: E402


class Ctx:
    def __init__(self, root):
        self.root = str(root)


def _verification(code):
    return {"id": "v1", "invocation": {"argv": [sys.executable, "-c", code]},
            "cwd": ".", "input_refs": [], "required": True}


class VerificationLogTest(unittest.TestCase):
    def run_one(self, code):
        root = tempfile.mkdtemp(prefix="wf-vlog-")
        log_dir = os.path.join(root, "logs")
        record = check._run_argv(Ctx(root), {"id": "t1"}, _verification(code), log_dir)
        path = os.path.join(root, record["evidence_ref"])
        with open(path, "r", encoding="utf-8") as handle:
            text = handle.read()
        return record, text

    def test_small_output_is_kept_in_full(self):
        record, text = self.run_one("print('first line\\nsecond line')")
        self.assertFalse(record["log_truncated"])
        self.assertIn("first line", text)
        self.assertIn("second line", text)
        self.assertNotIn("wf-log-truncated", text)
        self.assertIn("exit_code: 0", text)
        self.assertEqual(record["summary"], "second line")

    def test_large_output_is_truncated_visibly(self):
        record, text = self.run_one(
            "print('HEAD-MARK')\nprint('x' * (400 * 1024))\nprint('TAIL-MARK')")
        self.assertTrue(record["log_truncated"])
        self.assertIn("HEAD-MARK", text)
        self.assertIn("TAIL-MARK", text)
        self.assertIn("wf-log-truncated", text)
        self.assertIn("dropped=", text)
        self.assertGreater(record["log_bytes"], check.LOG_HEAD_BYTES + check.LOG_TAIL_BYTES)
        self.assertTrue(record["log_digest"].startswith("sha256:"))
        # 记录里只留摘要，不塞全文
        self.assertLess(len(record["summary"]), 200)

    def test_secrets_are_masked_in_the_log(self):
        _record, text = self.run_one("print('token=super-secret-value')")
        self.assertNotIn("super-secret-value", text)
        self.assertIn("***", text)

    def test_masking_stays_linear_on_long_lines(self):
        """回归守卫：无限长键名扫描会让 400KB 日志挂死（实测 >10 分钟）。"""
        import time

        text = "x" * 1_000_000
        start = time.monotonic()
        self.assertEqual(check.redact_text(text), text)
        self.assertLess(time.monotonic() - start, 5.0)
        dense = ("token=" + "y" * 200 + "\n") * 500
        masked = check.redact_text(dense)
        self.assertNotIn("token=" + "y" * 200, masked)


if __name__ == "__main__":
    unittest.main()
