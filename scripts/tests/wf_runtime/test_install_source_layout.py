"""安装器的 tag 校验必须支持「发行树在仓库子目录」（2026-11-25）。

作者仓库的发行树在 `docs/workflows/wf-release/`，而 `git show <commit>:<path>` 的路径按仓库根
解释。旧实现直接用 `source_path`（如 `wf-release/bin/wf.py`），于是从作者仓库安装必然报
`missing in tag commit tree`，只能先手工造一个根级候选仓库——这就是安装步骤反人类的根因。
这里锁两件事实：子目录 source 能读出 tag 字节；根级候选布局仍照旧可用。
"""

import importlib.util
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
INSTALL = REPO / "docs" / "workflows" / "wf" / "payload" / "install.py"


def _install_module():
    spec = importlib.util.spec_from_file_location("wf_install_layout_under_test", INSTALL)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _git(root, *argv):
    subprocess.run(["git", *argv], cwd=root, check=True, capture_output=True,
                   env={**os.environ, "GIT_CONFIG_GLOBAL": "/dev/null", "GIT_CONFIG_SYSTEM": "/dev/null"})


class SourceLayoutTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        _git(self.root, "init", "-q")
        _git(self.root, "config", "user.email", "t@t")
        _git(self.root, "config", "user.name", "t")
        self.release = self.root / "docs/workflows/wf-release"
        (self.release / "wf-release/bin").mkdir(parents=True)
        (self.release / "install.py").write_text("#!/usr/bin/env python3\n", encoding="utf-8")
        (self.release / "wf-release/bin/wf.py").write_text("payload\n", encoding="utf-8")
        _git(self.root, "add", "-A")
        _git(self.root, "commit", "-qm", "release")
        _git(self.root, "tag", "wf-v0.0.0-test")
        self.commit = subprocess.run(["git", "rev-parse", "wf-v0.0.0-test"],
                                     cwd=self.root, capture_output=True, text=True, check=True).stdout.strip()

    def tearDown(self):
        self._tmp.cleanup()

    def test_subdirectory_source_reads_tag_bytes(self):
        module = _install_module()
        self.assertEqual(module._committed_bytes(str(self.release), self.commit, "wf-release/bin/wf.py"),
                         b"payload\n")
        self.assertEqual(module._committed_bytes(str(self.release), self.commit, "install.py"),
                         b"#!/usr/bin/env python3\n")

    def test_root_level_candidate_still_works(self):
        module = _install_module()
        self.assertEqual(module._committed_bytes(str(self.root), self.commit,
                                                 "docs/workflows/wf-release/wf-release/bin/wf.py"),
                         b"payload\n")

    def test_verify_assets_passes_for_subdirectory_source(self):
        module = _install_module()
        import hashlib
        digest = "sha256:" + hashlib.sha256(b"payload\n").hexdigest()
        manifest = {
            "assets": [{"source_path": "wf-release/bin/wf.py", "target_class": "payload",
                        "target": ".wf/bin/wf.py", "digest": digest, "required": True}],
            "gitignore_managed": {"lines": [], "begin_marker": "# begin", "end_marker": "# end"},
            "required_steps": [],
            "template_markers": [],
            "schema_version": 1,
        }
        manifest["compatibility"] = {"rules_digest": module.compute_rules_digest(manifest)}
        problems = module.verify_assets(str(self.release), manifest, commit=self.commit)
        self.assertEqual(problems, [])

    def test_missing_asset_is_still_reported(self):
        module = _install_module()
        manifest = {"assets": [{"source_path": "wf-release/bin/missing.py", "target_class": "payload",
                                "target": ".wf/bin/missing.py", "digest": "sha256:" + "0" * 64,
                                "required": True}],
                    "gitignore_managed": {"lines": []}, "schema_version": 1}
        problems = module.verify_assets(str(self.release), manifest, commit=self.commit)
        self.assertEqual(problems[0]["reason"], "missing in tag commit tree")


class SelfLocatedInstallTest(unittest.TestCase):
    """系统 wf 命令只传 --target；安装器自定位发行根并从清单版本推导 tag。"""

    def test_installer_preview_without_source_or_release_ref(self):
        import json
        import shutil
        import sys

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = REPO / "docs/workflows/wf-release"
            release = root / "docs/workflows/wf-release"
            shutil.copytree(source, release)
            _git(root, "init", "-q")
            _git(root, "config", "user.email", "t@t")
            _git(root, "config", "user.name", "t")
            _git(root, "add", "-A")
            _git(root, "commit", "-qm", "release 0.0.8")
            _git(root, "tag", "wf-v0.0.8")
            target = root / "project"
            target.mkdir()
            result = subprocess.run(
                [sys.executable, str(release / "install.py"), "--target", str(target), "--json"],
                capture_output=True, text=True, timeout=120,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            payload = json.loads(result.stdout)
            self.assertTrue(payload["facts"]["preview"])
            self.assertTrue(payload["facts"]["platforms"])
            self.assertIn("wf-v0.0.8", result.stdout)


if __name__ == "__main__":
    unittest.main()
