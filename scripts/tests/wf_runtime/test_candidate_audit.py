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
        (self.root / "p5_v1.test.log.json").write_text(json.dumps({
            "rc": 1, "status": "failed", "supervision": {"target_rc": 0,
                                                        "cleanup_state": "cleaned"},
            "assertion_result": {
                "ok": False, "expected": 12, "observed": 11,
                "reason": "rc=0 observed=11 failures=1 expected=12"}}))
        (self.root / "lines").write_text("p5_v1\t1\t2.0\tbad\tsaved 12 cases\n")
        record = self.audit.record_suite(entry, self.root, str(self.root))
        self.assertEqual(record["rc"], 1, "命令层退出码")
        self.assertEqual(record["suite_rc"], 0, "suite 进程自身 rc")
        self.assertEqual((record["expected"], record["observed"], record["assertion_ok"]),
                         (12, 11, False))
        self.assertIn("[V1] x: FAIL — False", record["failures"])
        self.assertEqual(record["tail"], "saved 12 cases")

    def test_committed_audit_has_a_durable_generator_and_no_environment_paths(self):
        data = json.loads((FULL / "candidate-audit.json").read_text())
        self.assertEqual(data["schema_version"], 2)
        self.assertEqual(data["generated_by"],
                         "scripts/tests/wf_runtime/full/candidate_audit.py")
        self.assertEqual(data["invocation"][0], "python3")
        self.assertNotIn("/tmp/", json.dumps(data), "审计证据不得固化临时 workdir")
        for name in ("r90_tests", "p5_v1"):
            self.assertTrue(data["units"][name]["failures"], name)
        self.assertEqual(data["units"]["p5_v1"]["rc"], 1)
        self.assertEqual(data["units"]["p5_v1"]["suite_rc"], 0)

    def test_missing_result_is_not_silently_clean(self):
        entry = {"name": "missing", "expect": 1, "script": "p5_v1.py"}
        record = self.audit.record_suite(entry, self.root)
        self.assertEqual(record["status"], "missing")
        self.assertIsNone(record["suite_rc"])
        self.assertEqual(record["failures"], [])


if __name__ == "__main__":
    unittest.main()
