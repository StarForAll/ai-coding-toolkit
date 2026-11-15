"""解释器身份（`scripts/python_runtime_identity.py`）：只哈希固定路径字符串 + 文件字节。

关键契约（design §2 / AC1）：
- 路径身份只覆盖 normalized invocation 与 sys.executable/prefix/base_prefix 的 realpath，
  同 binary 不同 prefix 仍不同；不 walk prefix；
- 调用文件与 binary 按字节分别哈希，dirty 字节变化可区分；
- 缺失/不可读一律报错，不签发 None；
- 同一 barrier 内同 role/同文件只解析一次。
"""

import os
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "scripts"))

import python_runtime_identity as identity  # noqa: E402


def probe_for(prefix="/venv/a", base="/usr", executable=None):
    def fake(_python):
        return {"executable": executable or sys.executable, "prefix": prefix,
                "base_prefix": base, "implementation": "cpython", "version": "3.11.8"}
    return fake


class IdentityTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="wf-runtime-identity-")
        self.addCleanup(self.tmp.cleanup)
        self.script = Path(self.tmp.name) / "tool.py"
        self.script.write_text("print('tool')\n", encoding="utf-8")

    def resolve(self, **kwargs):
        return identity.resolve("tool", str(self.script), sys.executable,
                                kwargs.pop("probe_fn", probe_for()))

    def test_same_binary_in_different_venv_prefixes_is_distinct(self):
        first = self.resolve(probe_fn=probe_for(prefix="/venv/a"))
        second = self.resolve(probe_fn=probe_for(prefix="/venv/b"))
        self.assertNotEqual(first["path_identity"], second["path_identity"])
        self.assertEqual(first["binary"]["digest"], second["binary"]["digest"])

    def test_each_path_field_participates(self):
        base = self.resolve()
        variants = [probe_for(base="/other"), probe_for(executable="/usr/bin/python3")]
        for variant in variants:
            self.assertNotEqual(base["path_identity"], self.resolve(probe_fn=variant)["path_identity"])
        other = Path(self.tmp.name) / "other.py"
        other.write_text("x = 1\n", encoding="utf-8")
        moved = identity.resolve("tool", str(other), sys.executable, probe_for())
        self.assertNotEqual(base["path_identity"], moved["path_identity"])

    def test_path_identity_keeps_invocation_location_not_realpath(self):
        link = Path(self.tmp.name) / "link.py"
        link.symlink_to(self.script)
        direct = self.resolve()
        via_link = identity.resolve("tool", str(link), sys.executable, probe_for())
        self.assertNotIn("/link.py", direct["path_identity"])
        self.assertNotEqual(direct["invocation_file"]["path"], via_link["invocation_file"]["path"])

    def test_dirty_invocation_bytes_change_digest(self):
        before = self.resolve()["invocation_file"]["digest"]
        self.script.write_text("print('tool changed')\n", encoding="utf-8")
        self.assertNotEqual(before, self.resolve()["invocation_file"]["digest"])

    def test_missing_or_unreadable_inputs_are_refused(self):
        with self.assertRaises(identity.IdentityError):
            identity.resolve("tool", str(Path(self.tmp.name) / "nope.py"), sys.executable, probe_for())
        with self.assertRaises(identity.IdentityError):
            identity.resolve("nope", str(self.script), sys.executable, probe_for())

    def test_probe_failure_is_refused(self):
        def broken(_python):
            raise identity.IdentityError("boom")
        with self.assertRaises(identity.IdentityError):
            self.resolve(probe_fn=broken)

    def test_resolver_probes_once_per_key(self):
        resolver = identity.Resolver(probe_fn=probe_for())
        first = resolver.resolve("tool", str(self.script), sys.executable)
        second = resolver.resolve("tool", str(self.script), sys.executable)
        self.assertIs(first, second)
        self.assertEqual(resolver.probe_count, 1)
        self.assertNotEqual(resolver.digest("sut", str(self.script), "/usr/bin/python3"),
                            resolver.digest("tool", str(self.script), sys.executable))

    def test_binary_is_hashed_from_real_file_bytes(self):
        result = self.resolve()
        self.assertTrue(result["binary"]["path"].startswith(os.sep))
        self.assertGreater(result["binary"]["bytes"], 0)
        self.assertEqual(result["invocation_file"]["bytes"], self.script.stat().st_size)


class CanonicalFormTest(unittest.TestCase):
    def test_canonical_json_is_sorted_and_compact(self):
        self.assertEqual(identity.canonical_json({"b": 1, "a": "中"}), '{"a":"中","b":1}')


if __name__ == "__main__":
    unittest.main()
