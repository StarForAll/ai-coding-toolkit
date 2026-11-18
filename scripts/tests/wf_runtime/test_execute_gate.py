"""execute 阶段门（`full/execute_gate.py`）：祖先/租约/冻结字节都要过（AC12/AC16）。

execute 是最终 consumer，不再 plan/ensure。它必须读**同一份**冻结字节先核 token 再解析；
缺失/替换/坏 schema/deploy 不符都拒绝。租约与 ancestor 用桩模拟（真实 flock 由契约层覆盖）。
"""

import hashlib
import importlib.util
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

FULL = Path(__file__).resolve().parents[0] / "full"
REPO = FULL.parents[2]
sys.path.insert(0, str(REPO / "scripts"))
sys.path.insert(0, str(FULL))

spec = importlib.util.spec_from_file_location("wf_execute_gate", FULL / "execute_gate.py")
gate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gate)
import fixture_scope  # noqa: E402
import release_lock  # noqa: E402


RUN_ID = "run-gate-1"
CANDIDATE_ROOT = "/tmp/candidate"


def plan_document(results_dir, deploy="dev", candidate_root=CANDIDATE_ROOT):
    candidate = deploy == "candidate"
    return {"schema_version": 1, "role": "full", "run_id": RUN_ID,
            "results_dir": str(results_dir), "scope_root": None,
            "mode": "subset", "full_mode": 0, "list_only": 0,
            "units": [{"name": "r70_tests", "kind": "suite"}], "fix": "/tmp/fix",
            "fixture_deploy": deploy, "no_build": 1,
            "test_release_root": "/tmp/release", "test_release_version": "0.1.2",
            "test_release_ref": "refs/tags/wf-v0.1.2",
            "release_root": candidate_root if candidate else "",
            "release_version": "0.1.2" if candidate else "",
            "release_ref": "refs/tags/wf-v0.1.2" if candidate else "",
            "release_meta": candidate_root + ".meta.json" if candidate else ""}


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="wf-execute-gate-")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        saved = {key: os.environ.get(key) for key in ("WF_RESULTS_DIR", "WF_RUNNER_CONTROL_PID",
                                                      "WF_FIXTURE_DEPLOY", "WF_RUN_ID")}
        self.addCleanup(lambda: [os.environ.pop(key, None) if value is None else
                                 os.environ.__setitem__(key, value) for key, value in saved.items()])
        os.environ["WF_RESULTS_DIR"] = str(self.root)
        os.environ["WF_RUNNER_CONTROL_PID"] = str(os.getpid())
        os.environ["WF_RUN_ID"] = RUN_ID
        self.candidate = self.root / "candidate"
        self.candidate.mkdir()
        (self.root / "candidate.meta.json").write_text("{}\n", encoding="utf-8")
        for module in (fixture_scope, release_lock):
            for name in ("verify_lease", "verify_results_lock"):
                if hasattr(module, name):
                    patcher = mock.patch.object(module, name, return_value=True)
                    patcher.start()
                    self.addCleanup(patcher.stop)

    def write(self, name, payload):
        data = json.dumps(payload, sort_keys=True).encode()
        (self.root / name).write_bytes(data)
        return hashlib.sha256(data).hexdigest(), len(data)

    def context(self, deploy="dev", **overrides):
        payload = {"schema_version": 2, "deploy": deploy,
                   "release_root": str(self.candidate) if deploy == "candidate" else "/tmp/release",
                   "version": "0.1.2", "ref": "refs/tags/wf-v0.1.2",
                   "release_subject": "sha256:subject", "tree_digest": "sha256:tree",
                   "runtime": {"tool": {"role": "tool", "path_identity": "sha256:t",
                                        "binary_digest": "sha256:tb"},
                               "sut": {"role": "sut", "path_identity": "sha256:s",
                                       "binary_digest": "sha256:sb"}},
                   "candidate": ({"commit": "c" * 40, "tree_digest": "sha256:tree"}
                                 if deploy == "candidate" else None)}
        payload.update(overrides)
        return payload

    def run_gate(self, plan, context, plan_sha=None, plan_size=None):
        plan_file = self.root / "plan.json"
        if plan is not None:
            if plan_file.exists():
                plan_file.unlink()
            sha, size = self.write("plan.json", plan)
        else:
            sha, size = "0" * 64, 1
        ctx_sha, ctx_size = self.write("release-context.json", context)
        return gate.main(["--entry-pid", str(os.getpid()), "--plan-file", str(plan_file),
                          "--plan-sha256", plan_sha or sha, "--plan-size", str(plan_size or size),
                          "--context-file", str(self.root / "release-context.json"),
                          "--context-sha256", ctx_sha, "--context-size", str(ctx_size)])

    def test_valid_dev_handoff_passes_and_emits_release_env(self):
        code = self.run_gate(plan_document(self.root), self.context())
        self.assertEqual(code, 0)
        code = self.run_gate(plan_document(self.root, "candidate", str(self.candidate)),
                             self.context("candidate"))
        self.assertEqual(code, 0)

    def test_tampered_or_truncated_plan_is_refused(self):
        self.assertEqual(self.run_gate(plan_document(self.root), self.context(),
                                       plan_sha="0" * 64), 2)
        self.assertEqual(self.run_gate(plan_document(self.root), self.context(),
                                       plan_size=1), 2)

    def test_missing_or_list_only_plan_is_refused(self):
        self.assertEqual(self.run_gate(None, self.context()), 2)
        plan = plan_document(self.root)
        plan["list_only"] = 1
        self.assertEqual(self.run_gate(plan, self.context()), 2)

    def test_context_mismatch_is_refused(self):
        base = plan_document(self.root, "candidate", str(self.candidate))
        self.assertEqual(self.run_gate(base, self.context("candidate", version="9.9.9")), 2)
        self.assertEqual(self.run_gate(base, self.context("candidate", release_subject="")), 2)
        self.assertEqual(self.run_gate(base, self.context(**{"deploy": "dev"})), 2)

    def test_forged_lease_or_wrong_ancestor_is_refused(self):
        with mock.patch.object(fixture_scope, "verify_results_lock", side_effect=fixture_scope.FixtureError("x")):
            self.assertEqual(self.run_gate(plan_document(self.root), self.context()), 2)
        self.assertEqual(gate.main(["--entry-pid", "1", "--plan-file", str(self.root / "plan.json"),
                                    "--plan-sha256", "0" * 64, "--plan-size", "1",
                                    "--context-file", "/nope", "--context-sha256", "0" * 64,
                                    "--context-size", "1"]), 2)


if __name__ == "__main__":
    unittest.main()
