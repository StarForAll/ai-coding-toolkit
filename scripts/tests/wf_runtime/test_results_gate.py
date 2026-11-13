"""套件结果行完整性（`full/results_gate.py`）：缺行/重行/畸形/计划外/坏结果都必须计失败。

这段判定原来写在 `run_all.sh` 的并行分支里，重构时抽成唯一实现并在这里正面验证：
只统计「已写出的结果行」会让“没跑出来的套件”变成绿灯。
"""

import importlib.util
import os
import subprocess
import sys
import tempfile
import unittest
from unittest import mock
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

    def test_nonzero_exit_cannot_be_reported_as_ok(self):
        self.write(line("a", rc=1, status="ok"))
        self.assertFalse(gate_mod.gate(self.path, "a")["ok"])

    def test_invalid_duration_cannot_be_reported_as_ok(self):
        self.write(line("a", seconds="nan"))
        self.assertFalse(gate_mod.gate(self.path, "a")["ok"])

    def test_empty_assertion_summary_cannot_be_reported_as_ok(self):
        self.write(line("a", tail=""))
        self.assertFalse(gate_mod.gate(self.path, "a")["ok"])

    def test_multiple_missing_names_survive_shell_transport(self):
        self.write(line("a"))
        result = subprocess.run([sys.executable, str(FULL / "results_gate.py"),
                                 "--lines", self.path, "--expected", "a missing_one missing_two"],
                                capture_output=True, text=True)
        shell = subprocess.run(["bash", "-euc", 'eval "$1"; printf "%s" "$GATE_MISSING"',
                                "gate-test", result.stdout], capture_output=True, text=True)
        self.assertEqual(shell.returncode, 0, shell.stderr)
        self.assertEqual(shell.stdout, "missing_one missing_two")

    def test_repro_gate_requires_frozen_inputs_and_consistent_phases(self):
        repro = Path(self.dir) / "repro"
        repro.mkdir()
        (repro / "selection.tsv").write_text("case-a\tboth\n")
        (repro / "inputs.json").write_text('{"case-a":"fingerprint-a"}')
        (repro / ".wf-results-owner.json").write_text('{"owner":"wf-test-fixture-v1"}')
        (repro / 'logs').mkdir()
        for phase in ('green', 'red'):
            (repro / 'logs' / f'case-a.{phase}.log').write_text(f'PASS {phase}: target verified\n')
        result = repro / "case-a.json"
        result.write_text(
            '{"case":"case-a","mode":"both","green":"pass","red":"pass",'
            '"verified":true,"fingerprint":"fingerprint-a","green_seconds":0.1,"red_seconds":0.2,'
            '"phases":{"green":{"rc":0,"status":"passed"},"red":{"rc":0,"status":"passed"}}}')
        import importlib.util
        sys.path.insert(0, str(FULL / "repro"))
        import repro_select
        spec = importlib.util.spec_from_file_location("wf_results_gate_repro", FULL / "results_gate.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        with mock.patch.object(repro_select, "commit_state", return_value=("state", [], [])):
            self.assertEqual(module.repro_gate(repro), 0)
        result.write_text(
            '{"case":"case-a","mode":"both","green":"pass","red":"fail",'
            '"verified":true,"fingerprint":"fingerprint-a","green_seconds":0.1,"red_seconds":0.2}')
        with mock.patch.object(repro_select, "commit_state", return_value=("state", [], [])):
            self.assertEqual(module.repro_gate(repro), 1)

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
