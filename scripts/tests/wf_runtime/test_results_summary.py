"""Summary publication (AC07): success means the summary was written, synced and read back.

Any failure to create/write/fsync/replace/read back must be non-zero and must not let the
caller print GATE-OK.  Counts are derived from the actual result set and the frozen plan,
never from numbers exported by the shell.
"""

import hashlib
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

FULL = Path(__file__).resolve().parent / "full"
summary = None


def _load():
    spec = importlib.util.spec_from_file_location("wf_results_summary", FULL / "results_summary.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _plan(units):
    return {"schema_version": 2, "mode": "full", "full_mode": 1,
            "fixture_deploy": "dev", "units": [{"name": name, "kind": kind}
                                               for name, kind in units]}


class SummaryTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="wf-summary-")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.results = self.root / "results"
        self.results.mkdir()
        self.plan = self.root / "plan.json"
        self.context = self.root / "release-context.json"
        self.lines = self.root / "lines"
        self.metrics = self.root / "metrics.json"
        self.write_plan([("a", "suite"), ("b", "flow")])
        self.write_lines(["a\t0\t1\tok\tsaved 1 / 1\n", "b\t0\t1\tok\t[PASS] x\n"])
        self.write_metrics()
        self.module = _load()

    def write_plan(self, units):
        plan = _plan(units)
        data = json.dumps(plan, ensure_ascii=False, indent=2, sort_keys=True).encode() + b"\n"
        self.plan.write_bytes(data)
        self.context.write_text(json.dumps(
            {"schema_version": 2, "deploy": "dev", "release_root": "/tmp/r", "version": "0.1.0",
             "ref": "refs/tags/wf-v0.1.0", "release_subject": "sha256:r",
             "plan_sha256": hashlib.sha256(data).hexdigest(), "plan_size": len(data),
             "runtime": {}, "candidate": None}))

    def write_lines(self, lines):
        self.lines.write_text("".join(lines))

    def write_metrics(self, **overrides):
        metrics = {"mode": "full", "full_mode": 1, "fixture_deploy": "dev",
                   "repro_ran": 0, "repro_fail": 0, "legacy_debt": 0, "build_seconds": 0,
                   "template_seconds": 0, "init_millis": 0, "suite_millis": 0,
                   "green_seconds": 0, "red_seconds": 0, "total_seconds": 1.0,
                   "effective_jobs": 1, "jobs": 1, "repro_jobs": 1,
                   "repro_groups": [], "pool_seconds": 0, "repro_seconds": 0,
                   "extra_failures": 0, "cleanup_state": "cleaned", "gate_malformed": 0,
                   "gate_missing": 0, "gate_duplicate": 0, "gate_unexpected": 0}
        metrics.update(overrides)
        self.metrics.write_text(json.dumps(metrics))

    def build(self):
        return self.module.build(self.results, self.plan, self.context, self.lines,
                                 self.metrics)

    def test_success_is_derived_published_and_read_back(self):
        payload = self.build()
        self.assertEqual((payload["suite_ran"], payload["flow_ran"], payload["units_total"]),
                         (1, 1, 2))
        self.assertEqual(payload["fail"], 0)
        self.assertEqual(payload["status"], "ok")
        written = json.loads((self.results / "summary.json").read_text())
        for key in ("schema_version", "mode", "fixture_deploy", "suite_ran", "flow_ran",
                    "repro_ran", "units_total", "fail", "status", "gate", "cleanup_state"):
            self.assertIn(key, written)
        self.assertEqual(written["units_total"], 2)
        self.assertEqual(written["cleanup_state"], "cleaned")

    def test_counts_come_from_lines_not_from_shell_numbers(self):
        self.write_metrics(extra_failures=2)
        payload = self.build()
        self.assertEqual(payload["suite_ran"], 1)
        self.assertEqual(payload["fail"], 2)

    def test_missing_or_extra_result_rows_block_publication(self):
        self.write_lines(["a\t0\t1\tok\tsaved 1 / 1\n"])
        with self.assertRaises(self.module.SummaryError):
            self.build()
        self.assertFalse((self.results / "summary.json").exists())
        self.write_lines(["a\t0\t1\tok\tsaved 1 / 1\n", "b\t0\t1\tok\tx\n",
                          "intruder\t0\t1\tok\tx\n"])
        with self.assertRaises(self.module.SummaryError):
            self.build()
        self.assertFalse((self.results / "summary.json").exists())

    def test_non_finite_or_negative_metrics_are_refused(self):
        for overrides in ({"total_seconds": float("nan")}, {"green_seconds": -1},
                          {"repro_ran": 1.5}, {"extra_failures": None}):
            with self.subTest(overrides=overrides):
                self.write_metrics(**overrides)
                with self.assertRaises(self.module.SummaryError):
                    self.build()

    def test_context_must_bind_the_frozen_plan(self):
        self.context.write_text(json.dumps(
            {"schema_version": 2, "deploy": "dev", "release_subject": "sha256:r",
             "plan_sha256": "0" * 64, "plan_size": 1, "runtime": {}}))
        with self.assertRaises(self.module.SummaryError):
            self.build()

    def test_publish_failure_is_nonzero_without_summary(self):
        target = self.results / "summary.json"
        target.mkdir()  # 目录占位：replace 必然失败
        proc = subprocess.run([sys.executable, str(FULL / "results_summary.py"),
                               "--results-dir", str(self.results), "--plan-file", str(self.plan),
                               "--context-file", str(self.context), "--lines", str(self.lines),
                               "--metrics", str(self.metrics)],
                              capture_output=True, text=True)
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("SUMMARY-FAILED", proc.stderr)

    def test_readback_mismatch_is_refused(self):
        # 写入阶段被破坏（字节不完整）→ 读回必需字段失败 → 不得返回成功。
        def broken_dump(payload, stream, **kwargs):
            stream.write("{}")

        with mock.patch.object(self.module.json, "dump", side_effect=broken_dump):
            with self.assertRaises(self.module.SummaryError):
                self.build()

    def test_publish_oserror_is_attributed_as_summary_error(self):
        with mock.patch.object(self.module.tempfile, "NamedTemporaryFile",
                               side_effect=OSError("disk full")):
            with self.assertRaises(self.module.SummaryError) as caught:
                self.build()
        self.assertIn("disk full", str(caught.exception))

    def test_stale_summary_is_replaced_only_by_a_complete_new_one(self):
        (self.results / "summary.json").write_text('{"schema_version": 2, "stale": true}\n')
        self.write_metrics(extra_failures=1)
        payload = self.build()
        written = json.loads((self.results / "summary.json").read_text())
        self.assertEqual(written["fail"], 1)
        self.assertEqual(payload["status"], "failed")
        self.assertNotIn("stale", written)


if __name__ == "__main__":
    unittest.main()
