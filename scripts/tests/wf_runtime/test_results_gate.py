"""套件结果行完整性（`full/results_gate.py`）：缺行/重行/畸形/计划外/坏结果都必须计失败。

这段判定原来写在 `run_all.sh` 的并行分支里，重构时抽成唯一实现并在这里正面验证：
只统计「已写出的结果行」会让“没跑出来的套件”变成绿灯。
"""

import importlib.util
import os
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parents[0]
FULL = HERE / "full"


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


gate_mod = _load("wf_results_gate", FULL / "results_gate.py")


def line(suite, rc=0, seconds=1, status="ok", tail="saved 1 / 1"):
    return f"{suite}\t{rc}\t{seconds}\t{status}\t{tail}\n"


class GateTest(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp(prefix="wf-gate-")
        self.addCleanup(lambda: __import__("shutil").rmtree(self.dir, ignore_errors=True))
        self.path = os.path.join(self.dir, "lines")

    def write(self, *lines):
        with open(self.path, "w", encoding="utf-8") as handle:
            handle.writelines(lines)

    def test_complete_result_set_is_ok(self):
        self.write(line("a"), line("b"))
        result = gate_mod.gate(self.path, "a b")
        self.assertTrue(result["ok"])
        self.assertEqual(result["unique"], 2)

    def test_missing_result_line_is_failure(self):
        self.write(line("a"))
        result = gate_mod.gate(self.path, "a b")
        self.assertFalse(result["ok"])
        self.assertEqual(result["missing"], ["b"])

    def test_duplicate_result_line_is_failure(self):
        self.write(line("a"), line("a"), line("b"))
        result = gate_mod.gate(self.path, "a b")
        self.assertFalse(result["ok"])
        self.assertEqual(result["duplicate"], ["a"])

    def test_malformed_line_is_failure(self):
        self.write(line("a"), "b\n", "c\tnotanint\t1\tok\tx\n", "d\t0\t1\tweird\tx\n", line("e"))
        result = gate_mod.gate(self.path, "a e")
        self.assertFalse(result["ok"])
        self.assertEqual(result["malformed"], 3)

    def test_unexpected_suite_is_failure(self):
        self.write(line("a"), line("intruder"))
        result = gate_mod.gate(self.path, "a")
        self.assertFalse(result["ok"])
        self.assertEqual(result["unexpected"], ["intruder"])

    def test_bad_status_is_failure(self):
        self.write(line("a"), line("b", rc=1, status="bad"))
        result = gate_mod.gate(self.path, "a b")
        self.assertFalse(result["ok"])
        self.assertEqual(result["bad"], ["b"])

    def test_missing_lines_file_counts_as_failure(self):
        result = gate_mod.gate(os.path.join(self.dir, "nope"), "a")
        self.assertFalse(result["ok"])
        self.assertEqual(result["missing"], ["a"])


if __name__ == "__main__":
    unittest.main()
