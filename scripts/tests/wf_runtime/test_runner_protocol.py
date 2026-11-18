"""内部 frame 协议（`full/runner_protocol.py`）：保留前缀剥离、字段校验与 argv 保真（AC16）。

断言锚在**编解码结果**上：同一 encoder 组装的 frame 能被对应 decoder 还原（含空格/中文），
未知/重复/漏字段、缺分隔符、用户 argv 注入保留选项都必须拒绝；repro 内部 frame 不接受用户
argv；冻结计划身份由 `validate_plan` 统一核验。
"""

import base64
import importlib.util
import json
import os
import subprocess
import sys
import unittest
from pathlib import Path

FULL = Path(__file__).resolve().parents[0] / "full"
spec = importlib.util.spec_from_file_location("wf_runner_protocol", FULL / "runner_protocol.py")
protocol = importlib.util.module_from_spec(spec)
spec.loader.exec_module(protocol)

SHA = "a" * 64
USER = ["--full", "路径 带 空格", "中文参数", "--repro", "green"]


def fields():
    return {
        "--entry-pid": "1234",
        "--results-root": "/tmp/wf results/run-1",
        "--results-explicit": "1",
        "--scope-root": "-",
    }


def execute_fields():
    value = fields()
    value.update({"--plan-file": "/tmp/results/plan.json", "--plan-sha256": SHA, "--plan-size": "42",
                  "--context-file": "/tmp/results/release-context.json",
                  "--context-sha256": SHA, "--context-size": "7"})
    return value


def repro_lease_fields():
    return {"--entry-pid": "1234",
            "--plan-b64": base64.b64encode(b'{"schema_version":1}').decode("ascii")}


def repro_inner_fields():
    return execute_fields()


def plan_document(**overrides):
    document = {
        "schema_version": 1, "role": "repro", "run_id": "run-1",
        "results_dir": "/tmp/results", "scope_root": None,
        "mode": "repro", "full_mode": 0, "fixture_deploy": "dev",
        "release_root": "", "release_ref": "", "release_version": "", "release_meta": "",
        "test_release_root": "/tmp/cache/0.1.0", "test_release_version": "0.1.0",
        "test_release_ref": "refs/tags/wf-v0.1.0", "no_build": 0,
        "repro_enabled": 1, "repro_mode": "both", "repro_groups": [], "only": "",
        "repro_jobs": 1, "repro_concurrent": 0, "repro_only": 1, "units": [], "jobs": 1,
    }
    document.update(overrides)
    return document


class RoundTripTest(unittest.TestCase):
    def test_lease_frame_round_trips_user_argv_verbatim(self):
        frame = protocol.encode("lease", fields(), USER)
        stage, values, user = protocol.decode(frame)
        self.assertEqual(stage, "lease")
        self.assertEqual(values, fields())
        self.assertEqual(user, USER)

    def test_each_stage_carries_its_required_prefix(self):
        for stage in ("lease", "execute"):
            value = {name: execute_fields()[name] for name in protocol.STAGE_FIELDS[stage]}
            frame = protocol.encode(stage, value, [])
            self.assertEqual(protocol.decode(frame)[0], stage)

    def test_public_call_has_no_frame(self):
        stage, values, user = protocol.decode(["--full", "--repro", "green"])
        self.assertIsNone(stage)
        self.assertEqual(values, {})
        self.assertEqual(user, ["--full", "--repro", "green"])

    def test_repro_frames_round_trip_without_user_argv(self):
        frame = protocol.encode_repro("repro-lease", repro_lease_fields())
        self.assertEqual(frame[0], "--_wf-repro-lease")
        stage, values, user = protocol.decode_repro(frame)
        self.assertEqual((stage, values, user), ("repro-lease", repro_lease_fields(), []))
        frame = protocol.encode_repro("repro-inner", repro_inner_fields())
        stage, values, user = protocol.decode_repro(frame)
        self.assertEqual(stage, "repro-inner")
        self.assertEqual(values, repro_inner_fields())
        self.assertEqual(user, [])

    def test_public_repro_call_has_no_frame(self):
        stage, values, user = protocol.decode_repro(["--mode", "green"])
        self.assertIsNone(stage)
        self.assertEqual(values, {})
        self.assertEqual(user, ["--mode", "green"])


class RejectTest(unittest.TestCase):
    def assert_invalid(self, argv):
        with self.assertRaises(protocol.FrameError):
            protocol.decode(argv)

    def test_unknown_and_duplicate_fields(self):
        self.assert_invalid([protocol.INTERNAL, "lease", *sum(fields().items(), ()), "--bogus", "1", "--"])
        frame = protocol.encode("lease", fields(), [])
        frame.insert(3, "--entry-pid")
        frame.insert(4, "99")
        self.assert_invalid(frame)

    def test_missing_field_and_missing_separator(self):
        value = fields()
        value.pop("--results-explicit")
        parts = [protocol.INTERNAL, "lease", *sum(value.items(), ())]
        self.assert_invalid(parts)
        self.assert_invalid(parts + ["--", "--full"])

    def test_stage_escalation_is_rejected(self):
        # lease 阶段收到 execute 字段
        self.assert_invalid([protocol.INTERNAL, "lease", *sum(execute_fields().items(), ()), "--"])

    def test_unknown_stage_and_bad_values(self):
        self.assert_invalid([protocol.INTERNAL, "later", "--"])
        self.assert_invalid([protocol.INTERNAL, "lease", *sum(
            {**fields(), "--entry-pid": "0"}.items(), ()), "--"])
        self.assert_invalid([protocol.INTERNAL, "lease", *sum(
            {**fields(), "--results-root": "relative/path"}.items(), ()), "--"])
        self.assert_invalid([protocol.INTERNAL, "execute", *sum(
            {**fields(), "--plan-file": "/x", "--plan-sha256": "short", "--plan-size": "1"}.items(), ()), "--"])

    def test_reserved_option_in_user_argv_is_rejected(self):
        frame = protocol.encode("lease", fields(), ["--full"])
        self.assert_invalid(frame + ["--_wf-internal", "execute"])
        self.assert_invalid(["--full", "--_wf-internal"])

    def test_scope_root_accepts_only_dash_or_absolute(self):
        frame = protocol.encode("lease", fields(), [])
        self.assertEqual(protocol.decode(frame)[1]["--scope-root"], "-")
        self.assert_invalid([protocol.INTERNAL, "lease", *sum(
            {**fields(), "--scope-root": "scope/rel"}.items(), ()), "--"])

    def test_repro_frames_reject_user_argv_and_bad_base64(self):
        frame = protocol.encode_repro("repro-lease", repro_lease_fields())
        with self.assertRaises(protocol.FrameError):
            protocol.decode_repro(frame + ["--mode", "green"])
        with self.assertRaises(protocol.FrameError):
            protocol.decode_repro(["--_wf-repro-lease", "--entry-pid", "1234",
                                   "--plan-b64", "not base64!", "--"])
        with self.assertRaises(protocol.FrameError):
            protocol.decode_repro(["--_wf-repro-inner", "--entry-pid", "1234", "--"])


class PlanValidationTest(unittest.TestCase):
    def validate(self, document, **overrides):
        values = {"role": "repro", "run_id": "run-1", "results_dir": "/tmp/results",
                  "scope_root": None}
        values.update(overrides)
        return protocol.validate_plan(document, **values)

    def test_repro_plan_binds_identity_and_release_fields(self):
        self.assertTrue(self.validate(plan_document()))
        with self.assertRaises(protocol.FrameError):
            self.validate(plan_document(run_id="other"))
        with self.assertRaises(protocol.FrameError):
            self.validate(plan_document(results_dir="/tmp/other"))
        with self.assertRaises(protocol.FrameError):
            self.validate(plan_document(repro_only=0))
        with self.assertRaises(protocol.FrameError):
            self.validate(plan_document(units=[{"name": "x"}]))
        with self.assertRaises(protocol.FrameError):
            self.validate(plan_document(only=None))

    def test_dev_plan_requires_its_test_release_identity(self):
        with self.assertRaises(protocol.FrameError):
            self.validate(plan_document(test_release_root=""))
        with self.assertRaises(protocol.FrameError):
            self.validate(plan_document(test_release_ref=""))

    def test_candidate_plan_requires_canonical_meta_sidecar(self):
        with self.assertRaises(protocol.FrameError):
            self.validate(plan_document(fixture_deploy="candidate"))
        with self.assertRaises(protocol.FrameError):
            # meta 指向另一文件（即使绝对路径）也拒绝
            self.validate(plan_document(
                fixture_deploy="candidate", release_root="/tmp/cand",
                release_ref="refs/tags/wf-v0.1.0", release_version="0.1.0",
                release_meta="/tmp/other.meta.json"))


class CliTest(unittest.TestCase):
    def cli(self, *argv, script=None):
        return subprocess.run([sys.executable, str(script or FULL / "runner_protocol.py"), *argv],
                              capture_output=True, text=True)

    def eval_shell(self, output):
        return subprocess.run(["bash", "-euc", 'eval "$1"; declare -p USER_ARGV; printf "%s" "$WF_STAGE"',
                               "protocol", output], capture_output=True, text=True)

    def test_strip_outputs_evaluable_assignments(self):
        frame = protocol.encode("lease", fields(), USER)
        result = self.cli("strip", "--", *frame)
        self.assertEqual(result.returncode, 0, result.stderr)
        shell = self.eval_shell(result.stdout)
        self.assertEqual(shell.returncode, 0, shell.stderr)
        self.assertIn("WF_FRAME_ENTRY_PID", result.stdout)
        self.assertIn("中文参数", shell.stdout)
        self.assertTrue(shell.stdout.rstrip().endswith("lease"))

    def test_encode_outputs_array(self):
        result = self.cli("encode", "--stage", "lease", "--", *sum(fields().items(), ()), "--", *USER)
        self.assertEqual(result.returncode, 0, result.stderr)
        shell = subprocess.run(["bash", "-c", 'eval "$1"; declare -p FRAME', "protocol", result.stdout],
                               capture_output=True, text=True)
        self.assertEqual(shell.returncode, 0, shell.stderr)
        self.assertIn("--_wf-internal", shell.stdout)

    def test_strip_repro_outputs_evaluable_assignments(self):
        frame = protocol.encode_repro("repro-inner", repro_inner_fields())
        result = self.cli("strip-repro", "--", *frame)
        self.assertEqual(result.returncode, 0, result.stderr)
        shell = self.eval_shell(result.stdout)
        self.assertEqual(shell.returncode, 0, shell.stderr)
        self.assertTrue(shell.stdout.rstrip().endswith("repro-inner"))
        self.assertIn("WF_FRAME_CONTEXT_FILE", result.stdout)

    def test_invalid_frame_exits_two(self):
        result = self.cli("strip", "--", protocol.INTERNAL, "nope", "--")
        self.assertEqual(result.returncode, 2)
        self.assertIn("FRAME-INVALID", result.stderr)


if __name__ == "__main__":
    unittest.main()