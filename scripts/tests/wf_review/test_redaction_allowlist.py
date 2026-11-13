"""D5：授权原件脱敏是**保留白名单**，不是顶层字段黑名单。

防的失败（dogfood）：`redact()` 只按顶层键黑名单丢弃，`quote`、嵌套字典与未知字符串字段里的
敏感原文原样进入 committed（任务目录）。

断言：
1. 未知字段（含嵌套字典）一律丢弃并记进 `dropped_keys`；
2. `quote` 只保留遮罩后的摘要（超长截断）；
3. 路径类保留项仍可核对（不因遮罩丢信息）；
4. `original_digest` 仍按**原文**计算，可复算。
"""

import sys
import unittest

REPO = Path = __import__("pathlib").Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "docs" / "workflows" / "wf" / "payload" / "lib"))

from wflib import authorize, records  # noqa: E402


DECISION = {
    "choice": "export",
    "task": "t1",
    "materials": ["diff", "requirement", "test_results"],
    "paths": ["pkg/a.py", "--token=leaked-in-path-form"],
    "by": "human:xzc",
    "at": "2026-11-12T00:00:00Z",
    "quote": "Authorization: Bearer abcdef123456 我同意把材料发给两个 reviewer",
    "source": "user-declared",
    "notes": "临时口令 hunter2 只在本机用过",
    "context": {"token": "sk-abcdefghijklmnop", "nested": {"password": "hunter3"}},
    "content": "外发材料全文",
}


class RedactionAllowlistTest(unittest.TestCase):
    def setUp(self):
        self.kept, self.digest = authorize.redact(DECISION)

    def test_unknown_and_nested_fields_are_dropped(self):
        self.assertNotIn("notes", self.kept)
        self.assertNotIn("context", self.kept)
        self.assertNotIn("content", self.kept)
        dropped = self.kept["redaction"]["dropped_keys"]
        self.assertTrue({"notes", "context", "content"} <= set(dropped))

    def test_no_sensitive_original_in_the_committed_copy(self):
        import json

        text = json.dumps(self.kept, ensure_ascii=False)
        for secret in ("hunter2", "hunter3", "sk-abcdefghijklmnop", "abcdef123456"):
            self.assertNotIn(secret, text)
        self.assertIn("***", self.kept["quote"])

    def test_reason_is_kept_but_masked(self):
        kept, _digest = authorize.redact(dict(DECISION, reason="删除旧配置，口令 hunter4 已作废"))
        self.assertIn("删除旧配置", kept["reason"])
        self.assertNotIn("hunter4", kept["reason"])

    def test_paths_stay_checkable(self):
        self.assertEqual(self.kept["paths"][0], "pkg/a.py")
        # 路径里的 token 片段不构成键值对时原样保留；写成 `--token=...` 形态则按秘密遮罩（已知取舍）
        kept, _digest = authorize.redact(dict(DECISION, paths=["pkg/tokenizer.py",
                                                               "--token=leaked-in-path-form"]))
        self.assertEqual(kept["paths"][0], "pkg/tokenizer.py")
        self.assertNotIn("leaked-in-path-form", kept["paths"][1])

    def test_quote_is_summarized_not_stored_raw(self):
        self.assertLessEqual(len(self.kept["quote"]), authorize.QUOTE_MAX_CHARS + len("…<truncated>"))
        long_quote = dict(DECISION, quote="x" * (authorize.QUOTE_MAX_CHARS + 50))
        kept, _digest = authorize.redact(long_quote)
        self.assertIn("truncated", kept["quote"])

    def test_original_digest_is_computed_over_the_raw_decision(self):
        self.assertEqual(self.digest, records.H("wf-authorization-original-v1", DECISION))
        self.assertEqual(self.kept["original_digest"], self.digest)


if __name__ == "__main__":
    unittest.main()
