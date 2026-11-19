"""测量交接（schema1）与摘要唯一发布（schema4）的契约。

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
        self.assertEqual(payload["schema_version"], 4)
        self.assertEqual(payload["status"], "ok")
        self.assertIsNone(payload["failure_kind"], "成功摘要不带失败归类")
        written = json.loads((self.ws.results / "summary.json").read_text())
        self.assertEqual(written, payload, "读回对象必须与返回对象完全一致")
        for report_value in (report(ok=False), report(cleanup="unknown"),
                             report(evidence="incomplete")):
            payload = self.ws.build(report_value)
            self.assertEqual(payload["status"], "failed")
            self.assertEqual(payload["failure_kind"], "failed")

    def test_cancelled_failure_kind_is_explicit(self):
        value = report(ok=False)
        value["failure_kind"] = "cancelled"
        payload = self.ws.build(value)
        self.assertEqual((payload["status"], payload["failure_kind"]), ("failed", "cancelled"))

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


class HistoricalConclusionTest(unittest.TestCase):
    """迁移表读者：新版 schema 4 与历史 schema 3 依各自事实判定，缺一即 unknown。"""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="wf-summary-history-")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        spec = importlib.util.spec_from_file_location(
            "wf_results_summary_lifecycle", FULL / "resource_lifecycle.py")
        self.lifecycle = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.lifecycle)
        self.results = self.root / "results"

    def start(self, run_id="run-1"):
        return self.lifecycle.begin_run(str(self.results), "execution", "full", run_id)

    def finish(self, run_id="run-1", cleanup="cleaned", evidence="complete"):
        return self.lifecycle.finish_run(str(self.results), run_id, "full", cleanup, evidence)

    def write_summary(self, status="ok", schema=4, failure_kind=None):
        payload = {"schema_version": schema, "run_id": "run-1", "status": status,
                   "failure_kind": failure_kind}
        (self.results / "summary.json").write_text(json.dumps(payload))

    def write_control(self, schema=2, cleanup="cleaned", evidence="complete", success=None,
                      summary_status=None):
        if schema == 2:
            control = {"schema_version": 2, "cleanup": {"cleanup_state": cleanup},
                       "assessment": {"evidence_state": evidence}}
        else:
            control = {"schema_version": 1, "success": success,
                       "summary": {"status": summary_status}}
        (self.results / ".runner.json").write_text(json.dumps({"control": control}))

    def test_new_schema_ok_requires_all_same_generation_facts(self):
        self.start()
        self.write_summary()
        self.write_control()
        self.finish()
        self.assertEqual(module.historical_conclusion(self.results)["status"], "ok")
        self.write_control(cleanup="unknown")
        self.assertEqual(module.historical_conclusion(self.results)["status"], "unknown")
        self.write_control()
        self.write_summary(status="failed", failure_kind="cancelled")
        conclusion = module.historical_conclusion(self.results)
        self.assertEqual((conclusion["status"], conclusion["failure_kind"]),
                         ("failed", "cancelled"))

    def test_historical_schema_3_reads_old_success_only_with_old_control_fact(self):
        self.start()
        state = json.loads((self.results / "run-state.json").read_text())
        state["schema_version"] = 1
        state["status"] = "ok"
        (self.results / "run-state.json").write_text(json.dumps(state))
        self.finish()
        state = json.loads((self.results / "run-state.json").read_text())
        state["schema_version"] = 1
        state["status"] = "ok"
        (self.results / "run-state.json").write_text(json.dumps(state))
        self.write_summary(schema=3)
        self.write_control(schema=1, success=True, summary_status="ok")
        self.assertEqual(module.historical_conclusion(self.results)["status"], "ok")
        self.write_control(schema=1, success=False, summary_status="ok")
        self.assertEqual(module.historical_conclusion(self.results)["status"], "unknown",
                         "缺旧控制成功事实时历史结论只能是未知")
        self.write_control(schema=1, success=True, summary_status="failed")
        self.assertEqual(module.historical_conclusion(self.results)["status"], "unknown")

    def test_finished_cleaned_without_committed_summary_is_unknown(self):
        self.start()
        self.write_control()
        self.finish()
        self.assertEqual(module.historical_conclusion(self.results)["status"], "unknown",
                         "finished+cleaned 且缺摘要不得判为成功")
        self.write_summary()
        self.assertEqual(module.historical_conclusion(self.results)["status"], "ok")
        self.write_summary(schema=2)
        self.assertEqual(module.historical_conclusion(self.results)["status"], "unknown",
                         "未知摘要 schema 不得冒充新版提交")


class SummaryProjectionTest(unittest.TestCase):
    """R4：candidate_commit / repro_phase_counts 只从已核上下文与相位核验报告投影。"""

    def setUp(self):
        self.ws = Workspace()
        self.addCleanup(self.ws.cleanup)

    def plan(self, **overrides):
        plan = {"mode": "full", "full_mode": 1, "fixture_deploy": "candidate",
                "repro_enabled": 1, "repro_mode": "green", "repro_groups": ["install"]}
        plan.update(overrides)
        return plan

    def counted_report(self, counts, ok=True):
        value = report(ok=ok)
        value["repro"] = {"enabled": True, "phase_counts": counts}
        return value

    def test_candidate_commit_comes_from_the_verified_context(self):
        counts = {"green": {"planned": 2, "passed": 2, "failed": 0, "unverified": 0},
                  "red": {"planned": 0, "passed": 0, "failed": 0, "unverified": 0}}
        payload = module.build(self.ws.results, self.counted_report(counts), None, {},
                               self.plan(), "full", "run-1",
                               context={"candidate": {"commit": "c" * 40}})
        self.assertEqual(payload["candidate_commit"], "c" * 40)
        self.assertEqual(payload["repro_phase_counts"], counts)
        self.assertEqual(payload["status"], "ok")
        missing = module.build(self.ws.results, self.counted_report(counts), None, {},
                               self.plan(), "full", "run-2", context=None)
        self.assertIsNone(missing["candidate_commit"])
        self.assertEqual(missing["status"], "failed", "候选成功摘要必须有已核提交")
        dev = module.build(self.ws.results, self.counted_report(counts), None, {},
                           self.plan(fixture_deploy="dev"), "full", "run-3", context=None)
        self.assertIsNone(dev["candidate_commit"], "dev 摘要的候选提交必须是 null")

    def test_disabled_repro_reports_zero_counts_and_no_bundle_reports_null(self):
        zeros = {phase: {"planned": 0, "passed": 0, "failed": 0, "unverified": 0}
                 for phase in ("green", "red")}
        disabled = module.build(self.ws.results, report(), None, {},
                                self.plan(repro_enabled=0, repro_mode="none"), "full", "run-1",
                                context={"candidate": {"commit": "c" * 40}})
        self.assertEqual(disabled["repro_phase_counts"], zeros)
        unbundled = module.build(self.ws.results, report(), None, {},
                                 self.plan(), "full", "run-1",
                                 context={"candidate": {"commit": "c" * 40}})
        self.assertIsNone(unbundled["repro_phase_counts"],
                          "启用 repro 但没有合法 bundle 时必须为 null，不能计零通过")

    def test_phase_counts_must_add_up_and_are_cross_checked(self):
        bad = {"green": {"planned": 3, "passed": 2, "failed": 0, "unverified": 0},
               "red": {"planned": 0, "passed": 0, "failed": 0, "unverified": 0}}
        with self.assertRaises(module.SummaryError):
            module.build(self.ws.results, self.counted_report(bad), None, {},
                         self.plan(), "full", "run-1",
                         context={"candidate": {"commit": "c" * 40}})
        negative = {"green": {"planned": 1, "passed": 1, "failed": 0, "unverified": 0},
                    "red": {"planned": 0, "passed": 0, "failed": -1, "unverified": 1}}
        with self.assertRaises(module.SummaryError):
            module.build(self.ws.results, self.counted_report(negative), None, {},
                         self.plan(), "full", "run-1",
                         context={"candidate": {"commit": "c" * 40}})


if __name__ == "__main__":
    unittest.main()