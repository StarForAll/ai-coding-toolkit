"""Evidence protocol (AC03/AC04/AC05/AC06/AC11/AC12).

- a repro verdict needs the explicit phase; the opposite phase's PASS line proves nothing;
- worker/gate/writer consume the same rule (writer must not run for wrong-phase logs);
- the runtime identity carries full tool/SUT bytes: a binary change at the same path moves
  the subject and invalidates old proofs;
- results_gate gives stable attribution for missing/unreadable/non-object/malformed input
  and never raises a second exception.
"""

import hashlib
import importlib.util
import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parents[0]
FULL = HERE / "full"
REPRO = FULL / "repro"
REPO = HERE.parents[2]
sys.path.insert(0, str(REPO / "scripts"))
sys.path.insert(0, str(FULL))
sys.path.insert(0, str(REPRO))


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


select = _load("wf_evidence_select", REPRO / "repro_select.py")
gate_mod = _load("wf_evidence_gate", FULL / "results_gate.py")
execution = _load("wf_evidence_execution", FULL / "execution.py")
import fixture_scope  # noqa: E402
import release_lock  # noqa: E402


class VerdictTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="wf-verdict-")
        self.addCleanup(self.tmp.cleanup)
        self.log = Path(self.tmp.name) / "case.log"

    def test_phase_is_mandatory(self):
        self.log.write_text("PASS green: ok\n")
        with self.assertRaises(ValueError):
            execution.verdict(self.log, 0, "repro")
        with self.assertRaises(ValueError):
            execution.verdict(self.log, 0, "repro", phase="both")

    def test_opposite_phase_is_not_evidence(self):
        self.log.write_text("PASS red: injected\n")
        self.assertFalse(execution.verdict(self.log, 0, "repro", phase="green")["ok"])
        self.assertTrue(execution.verdict(self.log, 0, "repro", phase="red")["ok"])

    def test_mixed_phase_or_failure_is_rejected(self):
        self.log.write_text("PASS green: ok\nPASS red: other\n")
        self.assertFalse(execution.verdict(self.log, 0, "repro", phase="green")["ok"])
        self.log.write_text("PASS green: ok\nFAIL green: later failure\n")
        self.assertFalse(execution.verdict(self.log, 0, "repro", phase="green")["ok"])

    def test_empty_or_nonzero_log_is_not_evidence(self):
        self.log.write_text("")
        self.assertFalse(execution.verdict(self.log, 0, "repro", phase="green")["ok"])
        self.log.write_text("PASS green: ok\n")
        self.assertFalse(execution.verdict(self.log, 1, "repro", phase="green")["ok"])

    def test_multiline_detail_is_supported(self):
        self.log.write_text("PASS green: target holds\nreason line one\nreason line two\n")
        self.assertTrue(execution.verdict(self.log, 0, "repro", phase="green")["ok"])

    def test_unreadable_log_is_attributed_not_raised(self):
        result = execution.verdict(Path(self.tmp.name) / "missing.log", 0, "repro", phase="green")
        self.assertFalse(result["ok"])
        self.assertIn("unreadable", result["reason"])

    def test_worker_forces_phase_environment(self):
        worker = _load("wf_evidence_worker", REPRO / "_worker.py")
        worker.repro_select = select
        captured = {}

        def fake_run(argv, log_path, *, timeout, env=None, **kwargs):
            captured.update(env or {})
            Path(log_path).write_text(f"PASS {argv[-1]}: ok\n")
            return {"rc": 0, "status": "passed", "seconds": 0.0, "reason": ""}

        os.environ["WF_REPRO_RESULTS"] = self.tmp.name
        os.environ["WF_REPRO_INJECT"] = "1"
        self.addCleanup(os.environ.pop, "WF_REPRO_RESULTS", None)
        self.addCleanup(os.environ.pop, "WF_REPRO_INJECT", None)
        with mock.patch.object(worker.execution, "run", side_effect=fake_run):
            worker.run_phase("case-a", "green")
            self.assertNotIn("WF_REPRO_INJECT", captured)
            worker.run_phase("case-a", "red")
            self.assertEqual(captured.get("WF_REPRO_INJECT"), "1")


class WriterPhaseTest(unittest.TestCase):
    """wrong-phase 日志：gate 非零，且 writer 根本没被调用（不提交 state）。"""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="wf-evidence-writer-")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.results = self.root / "results"
        self.results.mkdir()
        self.cache = self.root / "cache"
        self.cache.mkdir()
        self._saved = {key: os.environ.get(key) for key in
                       ("WF_TEST_RUN_CACHE", "WF_RELEASE_TREE", "WF_FIXTURE_DEPLOY",
                        "WF_RELEASE_CONTEXT")}
        self.addCleanup(self._restore)
        os.environ["WF_TEST_RUN_CACHE"] = str(self.cache)
        os.environ["WF_RELEASE_TREE"] = "/tmp/fake-release"
        os.environ["WF_FIXTURE_DEPLOY"] = "dev"
        os.environ.pop("WF_RELEASE_CONTEXT", None)
        self.context = {
            "schema_version": 2, "deploy": "dev", "release_subject": "sha256:release",
            "release_root": "/tmp/fake-release", "version": "0.1.2",
            "ref": "refs/tags/wf-v0.1.2", "tree_digest": "sha256:tree",
            "manifest_digest": "sha256:manifest", "runtime": _runtime(), "candidate": None}
        for patcher in (mock.patch.object(select, "release_context",
                                          side_effect=lambda: dict(self.context)),):
            patcher.start()
            self.addCleanup(patcher.stop)
        for target in (fixture_scope, release_lock):
            for name in ("verify_lease", "verify_results_lock"):
                if hasattr(target, name):
                    patcher = mock.patch.object(target, name, return_value=True)
                    patcher.start()
                    self.addCleanup(patcher.stop)

    def _restore(self):
        for key, value in self._saved.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value

    def _bundle(self):
        selection = select.select(["review"], only="review-count-reject", fixture_deploy="dev",
                                  mode="both")
        path = self.results / "inputs.json"
        sha, size = select.write_bundle(str(path), select.bundle_document(selection))
        return selection, path, sha, size

    def _record(self, selection, sha, case="review-count-reject", log_phase="red"):
        record = {"case": case, "mode": "both", "green": "pass", "red": "pass",
                  "verified": True,
                  "execution_fingerprint": selection["cases"][case]["execution_fingerprint"],
                  "bundle_sha256": sha, "green_seconds": 0.1, "red_seconds": 0.2,
                  "phases": {}}
        (self.results / "logs").mkdir(exist_ok=True)
        for phase in ("green", "red"):
            (self.results / "logs" / f"{case}.{phase}.log").write_text(
                f"PASS {log_phase}: evidence\n")
            record["phases"][phase] = {"rc": 0, "status": "passed"}
        (self.results / (case + ".json")).write_text(json.dumps(record))

    def test_gate_and_writer_refuse_wrong_phase_evidence(self):
        selection, path, sha, size = self._bundle()
        self._record(selection, sha)
        with mock.patch.object(select, "write_state") as write_state:
            with self.assertRaises(select.SelectError):
                select.commit_state(str(self.results), str(path), sha, str(size))
            write_state.assert_not_called()
        self.assertFalse((self.cache / "repro-state.json").exists())

    def test_gate_default_bundle_path_works(self):
        selection, path, sha, size = self._bundle()
        self._record(selection, sha, log_phase="green")
        env = {key: os.environ.get(key) for key in ("WF_REPRO_INPUTS_FILE",)}
        os.environ.pop("WF_REPRO_INPUTS_FILE", None)
        self.addCleanup(lambda: [os.environ.__setitem__(k, v) if v is not None
                                 else os.environ.pop(k, None) for k, v in env.items()])
        self.assertEqual(gate_mod.repro_gate(str(self.results)), 1,
                         "missing expected digest still validates structure (no crash)")


def _runtime(tool_binary="sha256:tool-bin"):
    return {
        "tool": {"role": "tool", "path_identity": "sha256:tool-path",
                 "binary_digest": tool_binary, "invocation_digest": "sha256:tool-inv",
                 "implementation": "cpython", "version": "3.14.7"},
        "sut": {"role": "sut", "path_identity": "sha256:sut-path",
                "binary_digest": "sha256:sut-bin", "invocation_digest": "sha256:sut-inv",
                "implementation": "cpython", "version": "3.11.9"},
    }


class RuntimeIdentityTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="wf-runtime-identity-")
        self.addCleanup(self.tmp.cleanup)
        self._saved = {key: os.environ.get(key) for key in
                       ("WF_TEST_RUN_CACHE", "WF_RELEASE_TREE", "WF_FIXTURE_DEPLOY",
                        "WF_RELEASE_CONTEXT")}
        self.addCleanup(self._restore)
        os.environ["WF_TEST_RUN_CACHE"] = self.tmp.name
        os.environ["WF_RELEASE_TREE"] = "/tmp/fake-release"
        os.environ["WF_FIXTURE_DEPLOY"] = "dev"
        os.environ.pop("WF_RELEASE_CONTEXT", None)
        self.context = {
            "schema_version": 2, "deploy": "dev", "release_subject": "sha256:release",
            "release_root": "/tmp/fake-release", "version": "0.1.2",
            "ref": "refs/tags/wf-v0.1.2", "tree_digest": "sha256:tree",
            "manifest_digest": "sha256:manifest", "runtime": _runtime(), "candidate": None}
        patcher = mock.patch.object(select, "release_context",
                                    side_effect=lambda: dict(self.context))
        patcher.start()
        self.addCleanup(patcher.stop)

    def _restore(self):
        for key, value in self._saved.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value

    def test_same_path_binary_change_moves_subject_and_blocks_reuse(self):
        groups = select.load_groups()
        case = "review-count-reject"
        local = select.local_inputs(case, groups)
        first = select.execution_context()
        subject_first = select.red_subject(case, local, select.public_inputs(), first)
        with mock.patch.object(select, "_runtime_identity", return_value=_runtime("sha256:new-bin")):
            second = select.execution_context()
            subject_second = select.red_subject(case, local, select.public_inputs(), second)
        self.assertNotEqual(subject_first, subject_second,
                            "二进制变化必须改变运行身份/证明主体")
        stable = select.execution_context()["runtime"]
        self.assertEqual(stable, select.execution_context()["runtime"],
                         "相同输入身份必须稳定")


class GateAttributionTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="wf-gate-attribution-")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def test_bad_bundles_fail_stably_without_second_exception(self):
        cases = {
            "missing": None,
            "unreadable": None,
            "bad-json": b"{broken",
            "non-object": b"[1, 2, 3]",
        }
        for name, content in cases.items():
            bundle = self.root / f"{name}.json"
            if name == "unreadable":
                bundle.mkdir()
            elif content is not None:
                bundle.write_bytes(content)
            with self.subTest(name=name):
                self.assertEqual(gate_mod.repro_gate(str(self.root), str(bundle)), 1)

    def test_malformed_duration_and_wrong_phase_fail(self):
        results = self.root / "results"
        results.mkdir()
        (results / "logs").mkdir()
        context = {"schema_version": 2, "deploy": "dev", "release_subject": "sha256:r",
                   "runtime": _runtime(), "platform": "linux"}
        public = {"helper_set": "core-v2", "source": "sha256:src", "helpers": "sha256:help", "executor": "sha256:exec",
                  "runner": {"repro_select.py": "sha256:sel", "run.sh": "sha256:run"}}
        bundle = {"schema_version": 3, "execution_context": context, "public_inputs": public,
                  "mode": "green",
                  "cases": {"case-a": {"mode": "green", "execution_fingerprint": "fp",
                                       "red_subject_digest": "sha256:s",
                                       "local_inputs": {"script": "s"}}}}
        data = json.dumps(bundle).encode()
        (results / "inputs.json").write_bytes(data)
        sha = hashlib.sha256(data).hexdigest()
        (results / "logs" / "case-a.green.log").write_text("PASS green: ok\n")
        (results / "case-a.json").write_text(json.dumps(
            {"case": "case-a", "mode": "green", "green": "pass", "red": "skip",
             "verified": True, "execution_fingerprint": "fp", "bundle_sha256": sha,
             "green_seconds": float("nan"), "red_seconds": 0.0,
             "phases": {"green": {"rc": 0, "status": "passed"}}}))
        self.assertEqual(gate_mod.repro_gate(str(results), str(results / "inputs.json"), sha,
                                             str(len(data))), 1)


if __name__ == "__main__":
    unittest.main()
