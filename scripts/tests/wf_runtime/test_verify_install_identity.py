"""`verify_install_identity.py` 是候选安装身份的唯一核验点（R1/A1 反例）。

覆盖：记录/清单缺失、version/release_ref/source_commit/rules_digest 不符、`.wf/lib`
字节不符与 `--no-lib-check` 的显式收窄；成功路径与 CLI 退出码。
"""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

FULL = Path(__file__).resolve().parent / "full"
SPEC = importlib.util.spec_from_file_location("wf_verify_install_identity",
                                              FULL / "verify_install_identity.py")
verifier = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(verifier)

VERSION = "0.1.1"
REF = "refs/tags/wf-v0.1.1"


class VerifyInstallIdentityTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="wf-verify-install-")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.release = self.root / "release"
        self.project = self.root / "project"
        self.lib_text = "LIB = 'candidate'\n"
        (self.release / "wf-release" / "lib" / "wflib").mkdir(parents=True)
        (self.release / "wf-release" / "lib" / "wflib" / "__init__.py").write_text(self.lib_text)
        rules = "sha256:" + "a" * 64
        (self.release / "wf-release.json").write_text(json.dumps({
            "version": VERSION, "compatibility": {"rules_digest": rules}}))
        self.rules = rules
        subprocess.run(["git", "init", "-q"], cwd=self.release, check=True)
        subprocess.run(["git", "config", "user.email", "t@e.c"], cwd=self.release, check=True)
        subprocess.run(["git", "config", "user.name", "t"], cwd=self.release, check=True)
        subprocess.run(["git", "add", "-A"], cwd=self.release, check=True)
        subprocess.run(["git", "commit", "-qm", "release"], cwd=self.release, check=True)
        subprocess.run(["git", "tag", "wf-v" + VERSION], cwd=self.release, check=True)
        self.commit = subprocess.run(["git", "rev-parse", f"{REF}^{{commit}}"],
                                     cwd=self.release, capture_output=True, text=True,
                                     check=True).stdout.strip()
        (self.project / ".wf" / "install").mkdir(parents=True)
        (self.project / ".wf" / "lib" / "wflib").mkdir(parents=True)
        (self.project / ".wf" / "lib" / "wflib" / "__init__.py").write_text(self.lib_text)
        self.write_record()

    def write_record(self, **overrides):
        record = {"version": VERSION, "release_ref": REF, "source_commit": self.commit,
                  "rules_digest": self.rules}
        record.update(overrides)
        (self.project / ".wf" / "install" / "installation.json").write_text(
            json.dumps(record))

    def test_matching_identity_has_no_problems(self):
        record, problems = verifier.verify(str(self.project), str(self.release), REF, VERSION)
        self.assertEqual(problems, [])
        self.assertEqual(record["source_commit"], self.commit)

    def test_every_identity_field_mismatch_is_reported(self):
        for overrides in ({"version": "0.1.0"}, {"release_ref": "refs/tags/wf-v0.1.0"},
                          {"source_commit": "0" * 40},
                          {"rules_digest": "sha256:" + "b" * 64},
                          {"version": "0.0.0-dev"}):
            with self.subTest(overrides=overrides):
                self.write_record(**overrides)
                _record, problems = verifier.verify(str(self.project), str(self.release),
                                                    REF, VERSION)
                self.assertTrue(problems, overrides)
        self.write_record()

    def test_missing_record_or_lib_content_drift_is_refused(self):
        (self.project / ".wf" / "install" / "installation.json").unlink()
        _record, problems = verifier.verify(str(self.project), str(self.release), REF, VERSION)
        self.assertIn("安装记录不可读", problems[0])
        self.write_record()
        (self.project / ".wf" / "lib" / "wflib" / "__init__.py").write_text("other\n")
        _record, problems = verifier.verify(str(self.project), str(self.release), REF, VERSION)
        self.assertIn("安装后的 .wf/lib 内容不是本次候选发行", problems)
        _record, problems = verifier.verify(str(self.project), str(self.release), REF, VERSION,
                                           check_lib=False)
        self.assertEqual(problems, [], "显式 --no-lib-check 只核安装记录")

    def test_unknown_ref_is_reported(self):
        self.write_record()
        _record, problems = verifier.verify(str(self.project), str(self.release),
                                            "refs/tags/wf-v9.9.9", VERSION)
        self.assertTrue(any("发行引用不可解析" in item for item in problems), problems)

    def test_cli_exit_code_and_output(self):
        good = subprocess.run([sys.executable, str(FULL / "verify_install_identity.py"),
                               "--target", str(self.project), "--release-root",
                               str(self.release), "--ref", REF, "--version", VERSION],
                              capture_output=True, text=True)
        self.assertEqual(good.returncode, 0, good.stdout + good.stderr)
        self.assertIn("install identity ok", good.stdout)
        self.write_record(source_commit="0" * 40)
        bad = subprocess.run([sys.executable, str(FULL / "verify_install_identity.py"),
                              "--target", str(self.project), "--release-root",
                              str(self.release), "--ref", REF, "--version", VERSION],
                             capture_output=True, text=True)
        self.assertEqual(bad.returncode, 1)
        self.assertIn("INSTALL-IDENTITY-MISMATCH", bad.stderr)


if __name__ == "__main__":
    unittest.main()