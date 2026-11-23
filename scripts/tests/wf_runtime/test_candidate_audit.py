"""candidate_audit.py: failure extraction and record fields are deterministic."""

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

FULL = Path(__file__).resolve().parent / "full"


def _load():
    spec = importlib.util.spec_from_file_location("wf_candidate_audit",
                                                  FULL / "candidate_audit.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class CandidateAuditTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="wf-candidate-audit-")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root / "lines").write_text("")
        self.audit = _load()

    def test_failure_formats_are_extracted(self):
        text = ("[V1] 追加平台: FAIL — False\n"
                "[FAIL] 4 有失败时脚本非零退出: exit=1\n"
                "[PASS] ok\n"
                "FAIL something\n")
        self.assertEqual(self.audit.parse_failures(text),
                         ["[V1] 追加平台: FAIL — False",
                          "[FAIL] 4 有失败时脚本非零退出: exit=1",
                          "FAIL something"])

    def test_record_keeps_command_rc_and_suite_rc_apart(self):
        entry = {"name": "p5_v1", "expect": 12, "script": "p5_v1.py"}
        (self.root / "p5_v1.out").write_text("[V1] x: FAIL — False\nsaved 12 cases\n")
        receipt = self.root / "logs" / "p5_v1.test.inv-1.json"
        receipt.parent.mkdir()
        receipt.write_text(json.dumps({"schema_version": 1, "command_id": "c1",
                                       "run_id": None, "evidence_scope": "standalone-command",
                                       "state": "finished", "local_cleanup": "none",
                                       "retained_paths": []}))
        (self.root / "p5_v1.test.log.json").write_text(json.dumps({
            "rc": 1, "status": "failed", "supervision": {"target_rc": 0,
                                                        "cleanup_state": "cleaned"},
            "unit_execution": {"schema_version": 1, "unit": "p5_v1", "invocation_id": "inv-1",
                               "run_id": None, "state": "passed",
                               "result_row": ["p5_v1", "1", "2.0", "bad", "saved 12 cases"],
                               "command_evidence": [
                                   {"phase": "test", "command_id": "c1",
                                    "evidence_path": str(receipt),
                                    "result_path": str(self.root / "p5_v1.test.log.json")}]},
            "assertion_result": {
                "ok": False, "expected": 12, "observed": 11,
                "reason": "rc=0 observed=11 failures=1 expected=12"}}))
        (self.root / "lines").write_text("p5_v1\t1\t2.0\tbad\tsaved 12 cases\n")
        record = self.audit.record_suite(entry, self.root, str(self.root), "inv-1")
        self.assertEqual(record["unit_execution_state"], "passed")
        self.assertEqual(record["command_evidence"], 1)
        self.assertIsNone(record["evidence_problem"])
        self.assertEqual(record["rc"], 1, "命令层退出码")
        self.assertEqual(record["suite_rc"], 0, "suite 进程自身 rc")
        self.assertEqual((record["expected"], record["observed"], record["assertion_ok"]),
                         (12, 11, False))
        self.assertIn("[V1] x: FAIL — False", record["failures"])
        self.assertEqual(record["tail"], "saved 12 cases")

    def test_committed_audit_has_a_durable_generator_and_no_environment_paths(self):
        data = json.loads((FULL / "candidate-audit.json").read_text())
        self.assertEqual(data["schema_version"], 3)
        self.assertEqual(data["generated_by"],
                         "scripts/tests/wf_runtime/full/candidate_audit.py")
        self.assertEqual(data["invocation"][0], "python3")
        self.assertIn(data["audit"]["kind"], ("full", "incremental"))
        self.assertIn(data["audit"]["status"], ("complete", "failed"))
        identity = data["identity"]
        for key in ("version", "release_ref", "candidate_commit", "candidate_tree_digest",
                    "source_tree_digest", "release_subject", "manifest_digest",
                    "rules_digest", "units_registry_digest", "helpers", "runtime",
                    "interpreter"):
            self.assertIn(key, identity, key)
        self.assertTrue(identity["helpers"])
        self.assertNotIn("/tmp/", json.dumps(data), "审计证据不得固化临时 workdir")
        # r90/p5_v1 曾在候选实跑里以具体失败断言留作 dev-only；2026-11-23 修掉来源判定后
        # 通过并提升，因此这里按**实际状态**核：失败的单元必须有失败证据，通过的单元
        # 必须绑定本候选身份（不写死名单）。
        for name, record in data["units"].items():
            if record.get("status") == "bad":
                self.assertTrue(record["failures"], name)
            self.assertEqual(record["installation"]["source_commit"],
                             identity["candidate_commit"],
                             f"{name}: 实际安装身份必须是本候选")
        for name in ("r90_tests", "p5_v1"):
            self.assertEqual(data["units"][name]["status"], "ok", name)
            self.assertEqual(data["units"][name]["suite_rc"], 0)
        for name, record in data["units"].items():
            for key in ("script_sha256", "kind", "expect", "fixture", "isolated_user",
                        "template", "installation", "input_identity", "input_digest"):
                self.assertIn(key, record, name)

    def test_malformed_previous_report_is_refused_cleanly(self):
        audit = _load()
        entries = {"a": {"name": "a", "kind": "suite", "expect": 1, "fixture": "template"}}
        identity = {"candidate_commit": "c"}
        for document in ({"schema_version": 3, "identity": identity, "units": []},
                         {"schema_version": 3, "identity": identity,
                          "units": {"a": "not-a-record"}}):
            with self.subTest(document=document):
                with self.assertRaises(audit.AuditError):
                    audit._validate_incremental(document, identity, entries,
                                                {"a": "sha256:" + "1" * 64},
                                                set(), {"source": "run-build",
                                                        "install": {}})

    def test_failed_atomic_publish_leaves_no_temp_and_old_bytes(self):
        audit = _load()
        out = self.root / "report.json"
        out.write_text('{"old": true}\n')
        with self.assertRaises(TypeError):
            audit._atomic_write_json(out, {"bad": object()})
        self.assertEqual(out.read_text(), '{"old": true}\n')
        self.assertEqual(sorted(self.root.glob(".report.json.tmp-*")), [])

    def test_only_selection_is_normalized_and_rejected_before_any_run(self):
        audit = _load()
        entries = audit._registry()
        self.assertIsNone(audit.normalize_only(None, entries), "未传 --only 表示完整审计")
        self.assertEqual(audit.normalize_only(["cp1_tests", "cp1_tests"], entries),
                         ["cp1_tests"])
        for values in ([""], ["   "], ["no-such-unit"], ["cp1_tests", "no-such-unit"],
                       ["d1_tests"]):
            with self.subTest(values=values):
                with self.assertRaises(audit.AuditError):
                    audit.normalize_only(values, entries)
        # 空/未知/混合选择都在建 workdir 或启动套件前被拒（rc=1，输出 unchanged）。
        import contextlib
        import io
        for values in (["--only", ""], ["--only", "no-such-unit"],
                       ["--only", "cp1_tests", "--only", "no-such-unit"]):
            stderr = io.StringIO()
            with contextlib.redirect_stderr(stderr):
                rc = audit.main(["--version", "0.1.0"] + values)
            self.assertEqual(rc, 1, values)
            self.assertIn("AUDIT-REFUSED", stderr.getvalue())

    def test_incremental_validation_requires_full_matching_identity(self):
        audit = _load()
        entries = {"a": {"name": "a", "kind": "suite", "expect": 1, "fixture": "template"}}
        scripts = {"a": "sha256:" + "1" * 64}
        template = {"source": "run-build", "install": {"version": "0.1.0", "release_ref": "r",
                                                       "source_commit": "c",
                                                       "rules_digest": "sha256:r"}}
        identity = {"candidate_commit": "c"}

        def previous(**overrides):
            row = {"status": "ok", "isolated_user": False, "template": template}
            row["input_identity"] = audit._row_identity(entries["a"], scripts["a"],
                                                        template, False)
            row["input_digest"] = audit._canonical_digest(row["input_identity"])
            row.update(overrides)
            return {"schema_version": 3, "identity": identity, "units": {"a": row}}

        audit._validate_incremental(previous(), identity, entries, scripts, set(), template)
        with self.assertRaises(audit.AuditError):
            audit._validate_incremental(previous(status="missing"), identity, entries,
                                        scripts, set(), template)
        cases = [
            # 旧 schema：不可验证。
            ({"schema_version": 2, "identity": identity, "units": previous()["units"]},
             identity, scripts),
            # 身份/候选变化。
            (previous(), {"candidate_commit": "other"}, scripts),
            # 旧报告缺 ID。
            ({"schema_version": 3, "identity": identity, "units": {}}, identity, scripts),
            # 待保留行脚本字节变化。
            (previous(), identity, {"a": "sha256:" + "2" * 64}),
        ]
        for document, current, current_scripts in cases:
            with self.subTest(document=document):
                with self.assertRaises(audit.AuditError):
                    audit._validate_incremental(document, current, entries,
                                                current_scripts, set(), template)
        # 外部模板树漂移也必须拒绝增量。
        external = dict(template, source="external", tree_digest="sha256:old")
        external_row_identity = audit._row_identity(entries["a"], scripts["a"], external, False)
        document = {"schema_version": 3, "identity": identity,
                    "units": {"a": dict(previous()["units"]["a"], template=external,
                                        input_identity=external_row_identity,
                                        input_digest=audit._canonical_digest(
                                            external_row_identity))}}
        with self.assertRaises(audit.AuditError):
            audit._validate_incremental(document, identity, entries, scripts, set(),
                                        dict(external, tree_digest="sha256:new"))

    def test_stale_invocation_or_managed_run_id_is_not_accepted(self):
        entry = {"name": "p5_v1", "expect": 12, "script": "p5_v1.py"}
        receipt = self.root / "logs" / "phase.json"
        receipt.parent.mkdir()
        receipt.write_text(json.dumps({"schema_version": 1, "command_id": "c1",
                                       "run_id": None, "evidence_scope": "standalone-command",
                                       "state": "finished", "local_cleanup": "none",
                                       "retained_paths": []}))
        base = {"unit_execution": {"schema_version": 1, "unit": "p5_v1",
                                   "invocation_id": "old-inv", "run_id": None,
                                   "state": "passed",
                                   "result_row": ["p5_v1", "0", "1", "ok", "x"],
                                   "command_evidence": [
                                       {"phase": "test", "command_id": "c1",
                                        "evidence_path": str(receipt),
                                        "result_path": str(self.root / "x.json")}]}}
        (self.root / "p5_v1.test.log.json").write_text(json.dumps(base))
        (self.root / "lines").write_text("p5_v1\t0\t1\tok\tx\n")
        record = self.audit.record_suite(entry, self.root, str(self.root), "new-inv")
        self.assertEqual(record["status"], "stale-evidence")
        base["unit_execution"]["invocation_id"] = "new-inv"
        base["unit_execution"]["run_id"] = "run-1"
        (self.root / "p5_v1.test.log.json").write_text(json.dumps(base))
        record = self.audit.record_suite(entry, self.root, str(self.root), "new-inv")
        self.assertEqual(record["status"], "stale-evidence")
        self.assertIn("managed run_id", record["evidence_problem"])

    def test_missing_result_is_not_silently_clean(self):
        entry = {"name": "missing", "expect": 1, "script": "p5_v1.py"}
        record = self.audit.record_suite(entry, self.root)
        self.assertEqual(record["status"], "missing")
        self.assertIsNone(record["suite_rc"])
        self.assertEqual(record["failures"], [])


if __name__ == "__main__":
    unittest.main()
