"""测量交接（schema1）与摘要唯一发布（schema3）的契约。

- 身份/输入快照：write_metrics 绑定本代 run_id/canonical root/role 与当前 plan/context/
  lines/unit/repro 输入的 sha256+size；read_metrics 用预期身份重算并逐项比对；
- 旧/缺/截断/错类型/错输入一律拒绝，旧 metrics 只作历史展示；
- 摘要只从当前 report + metrics + input_evidence 构造一次，原子发布并完整读回；
  status=ok 必须同时满足 gate、cleanup=cleaned、evidence=complete。
"""

import hashlib
import importlib.util
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

FULL = Path(__file__).resolve().parent / "full"
summary = importlib.util.spec_from_file_location("wf_results_summary_v3",
                                                 FULL / "results_summary.py")
module = importlib.util.module_from_spec(summary)
summary.loader.exec_module(module)


def measurements(**overrides):
    base = {"mode": "full", "full_mode": 1, "fixture_deploy": "dev", "execution_mode": "serial",
            "fallback_reason": "", "repro_mode": "none", "repro_groups": [],
            "repro_concurrent": False, "jobs": 2, "requested_jobs": 2, "effective_jobs": 2,
            "repro_jobs": 1, "pycache_root": "/tmp/pycache", "template_source": "none",
            "template_cache_hit": False, "template_cache_key": None, "template_reused": False,
            "template_build_sequences": 0, "release_build": "built", "build_seconds": 0,
            "template_seconds": 0, "init_millis": 0, "suite_millis": 0, "green_seconds": 0,
            "red_seconds": 0, "total_millis": 1000, "pool_seconds": 1, "repro_seconds": 0}
    base.update(overrides)
    return base


def report(ok=True, cleanup="cleaned", evidence="complete", fail=0):
    gate = {"malformed": 0, "missing": [], "duplicate": [], "unexpected": [], "bad": [],
            "repro_fail": 0, "extra_failures": 0}
    counts = {"suite_ran": 1, "flow_ran": 1, "repro_ran": 0, "units_total": 2, "fail": fail,
              "bad": 0, "extra_failures": 0, "repro_fail": 0, "legacy_debt": 0,
              "unregistered_fail": 0}
    return {"ok": ok, "counts": counts, "gate": gate, "repro": {"enabled": False},
            "cleanup_state": cleanup, "evidence_state": evidence, "reasons": [],
            "cleanup_report": {"removed": ["FIX"], "failed": [], "not_attempted": [],
                               "retained_paths": []}}


class Workspace:
    def __init__(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="wf-summary-v3-")
        self.root = Path(self.tmp.name)
        self.results = self.root / "results"
        self.results.mkdir()
        self.plan = self.root / "plan.json"
        self.context = self.root / "release-context.json"
        self.write_plan([("a", "suite"), ("b", "flow")])
        self.write_lines(["a\t0\t1\tok\tsaved 1 / 1\n", "b\t0\t1\tok\t[PASS] x\n"])
        self.write_units("run-1")
        self.write_metrics_file = self.results / "summary-metrics.json"

    def cleanup(self):
        self.tmp.cleanup()

    def write_plan(self, units):
        payload = {"schema_version": 2, "mode": "full", "full_mode": 1,
                   "fixture_deploy": "dev",
                   "units": [{"name": name, "kind": kind} for name, kind in units]}
        data = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True).encode() + b"\n"
        self.plan.write_bytes(data)
        self.context.write_text(json.dumps({
            "schema_version": 2, "deploy": "dev", "release_root": "/tmp/r", "version": "0.1.0",
            "ref": "refs/tags/wf-v0.1.0", "release_subject": "sha256:r",
            "plan_sha256": hashlib.sha256(data).hexdigest(), "plan_size": len(data),
            "runtime": {}, "candidate": None, "release_build": "built"}))

    def write_lines(self, lines):
        (self.results / "lines").write_text("".join(lines))

    def write_units(self, run_id):
        for name in ("a", "b"):
            (self.results / f"{name}.test.log.json").write_text(json.dumps({
                "schema_version": 2, "name": name, "status": "passed", "rc": 0,
                "unit_execution": {"schema_version": 1, "unit": name, "run_id": run_id,
                                   "invocation_id": "inv-" + name, "state": "passed",
                                   "result_row": [name, "0", "1", "ok", "x"],
                                   "command_evidence": []}}))

    def write_metrics(self, run_id="run-1", role="full", **overrides):
        return module.write_metrics(self.results, run_id, role, self.plan, measurements(**overrides),
                                    self.context)

    def read_metrics(self, run_id="run-1", role="full"):
        return module.read_metrics(self.write_metrics_file, run_id, self.results, role,
                                   self.plan, self.context)

    def build(self, report_value=None, metrics=None, evidence=None, fault=None):
        metrics = metrics or measurements()
        evidence = evidence or module.collect_inputs(self.results, "run-1", "full", self.plan,
                                                     self.context)
        plan = json.loads(self.plan.read_text())
        return module.build(self.results, report_value or report(), metrics, evidence,
                            plan, "full", "run-1", fault=fault)


class MetricsTest(unittest.TestCase):
    def setUp(self):
        self.ws = Workspace()
        self.addCleanup(self.ws.cleanup)

    def test_round_trip_binds_identity_and_inputs(self):
        path = self.ws.write_metrics()
        record = json.loads(path.read_text())
        self.assertEqual(record["schema_version"], 1)
        self.assertEqual((record["run_id"], record["role"], record["state"]),
                         ("run-1", "full", "complete"))
        for key in ("plan", "context", "lines", "units"):
            self.assertIn(key, record["inputs"])
        self.assertNotIn("cleanup_state", record)
        self.assertNotIn("gate_malformed", record)
        metrics, evidence = self.ws.read_metrics()
        self.assertEqual(metrics["effective_jobs"], 2)
        self.assertEqual(set(evidence), {"metrics", "plan", "context", "lines", "units", "repro"})

    def test_stale_run_missing_truncated_and_input_mismatch_are_refused(self):
        self.ws.write_metrics()
        with self.assertRaises(module.SummaryError):
            self.ws.read_metrics(run_id="old-run")
        self.ws.write_metrics_file.unlink()
        with self.assertRaises(module.SummaryError):
            self.ws.read_metrics()
        self.ws.write_metrics()
        data = self.ws.write_metrics_file.read_text()
        self.ws.write_metrics_file.write_text(data[: len(data) // 2])
        with self.assertRaises(module.SummaryError):
            self.ws.read_metrics()
        self.ws.write_metrics()
        (self.ws.results / "lines").write_text("a\t0\t1\tok\tchanged\n")
        with self.assertRaises(module.SummaryError):
            self.ws.read_metrics()

    def test_old_metrics_file_is_display_only(self):
        self.ws.write_metrics_file.write_text(json.dumps({"mode": "full"}))
        with self.assertRaises(module.SummaryError) as caught:
            self.ws.read_metrics()
        self.assertIn("schema", str(caught.exception))

    def test_measurements_are_typed_and_conditional(self):
        for overrides in ({"total_millis": -1}, {"effective_jobs": True},
                          {"effective_jobs": 0}, {"mode": "bogus"},
                          {"repro_mode": "none", "green_seconds": 3},
                          {"template_cache_hit": True, "template_source": "run-build"},
                          {"extra_failures": 0}, {"cleanup_state": "cleaned"}):
            with self.subTest(overrides=overrides):
                with self.assertRaises(module.SummaryError):
                    module.validate_measurements(measurements(**overrides))

    def test_units_must_belong_to_this_run(self):
        self.ws.write_units("other-run")
        with self.assertRaises(module.SummaryError):
            self.ws.write_metrics()

    def test_repro_role_reads_its_own_bundle_without_full_metrics(self):
        repro = self.ws.root / "repro"
        repro.mkdir()
        (repro / "inputs.json").write_text('{"schema_version": 3}\n')
        (repro / "case.json").write_text('{"case": "case"}\n')
        evidence = module.repro_input_evidence(str(repro))
        self.assertEqual(set(evidence), {"repro"})
        self.assertEqual(evidence["repro"]["state"], "present")
        self.assertIn("case.json", evidence["repro"]["records"])


class BuildTest(unittest.TestCase):
    def setUp(self):
        self.ws = Workspace()
        self.addCleanup(self.ws.cleanup)

    def test_status_ok_requires_gate_cleanup_and_evidence(self):
        payload = self.ws.build()
        self.assertEqual(payload["schema_version"], 3)
        self.assertEqual(payload["status"], "ok")
        written = json.loads((self.ws.results / "summary.json").read_text())
        self.assertEqual(written, payload, "读回对象必须与返回对象完全一致")
        for report_value in (report(ok=False), report(cleanup="unknown"),
                             report(evidence="incomplete")):
            payload = self.ws.build(report_value)
            self.assertEqual(payload["status"], "failed")

    def test_counts_come_from_the_report_not_from_shell_numbers(self):
        payload = self.ws.build(report(fail=2))
        self.assertEqual(payload["fail"], 2)
        self.assertEqual(payload["units_total"], 2)

    def test_publish_failure_is_nonzero_without_success(self):
        (self.ws.results / "summary.json").mkdir()
        with self.assertRaises(module.SummaryError):
            self.ws.build()

    def test_readback_mismatch_is_refused(self):
        def broken_dump(payload, stream, **kwargs):
            stream.write("{}")

        with mock.patch.object(module.json, "dump", side_effect=broken_dump):
            with self.assertRaises(module.SummaryError):
                self.ws.build()

    def test_publish_oserror_is_attributed(self):
        with mock.patch.object(module.tempfile, "NamedTemporaryFile",
                               side_effect=OSError("disk full")):
            with self.assertRaises(module.SummaryError) as caught:
                self.ws.build()
        self.assertIn("disk full", str(caught.exception))

    def test_malformed_fault_leaves_no_success(self):
        with self.assertRaises(module.SummaryError):
            self.ws.build(fault="summary-malformed")
        written = json.loads((self.ws.results / "summary.json").read_text())
        self.assertNotIn("status", written)

    def test_stale_summary_is_replaced_only_by_a_complete_new_one(self):
        (self.ws.results / "summary.json").write_text('{"schema_version": 2, "stale": true}\n')
        payload = self.ws.build(report(ok=False, fail=1))
        written = json.loads((self.ws.results / "summary.json").read_text())
        self.assertEqual(written["fail"], 1)
        self.assertNotIn("stale", written)
        self.assertEqual(payload["status"], "failed")

    def test_build_requires_input_evidence(self):
        with self.assertRaises(module.SummaryError):
            module.build(self.ws.results, report(), measurements(), None,
                         {"mode": "full"}, "full", "run-1")


if __name__ == "__main__":
    unittest.main()