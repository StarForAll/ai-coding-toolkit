"""System command wheel builder guards (no uv build in the unit test)."""

from __future__ import annotations

import importlib.util
import subprocess
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "scripts" / "build-wf-cli-wheel.py"


def _module():
    spec = importlib.util.spec_from_file_location("wf_build_cli_wheel", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class BuildCliWheelTest(unittest.TestCase):
    def setUp(self):
        self.module = _module()
        self.version = self.module.release_version()

    def test_version_mismatch_is_refused_before_building(self):
        major, minor, patch = (int(part) for part in self.version.split("."))
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(self.module.BuildError):
                self.module.build_wheel(tmp, f"{major}.{minor}.{patch + 1}")

    def test_wheel_name_pattern_matches_uv_output(self):
        name = f"wf_cli-{self.version}-py3-none-any.whl"
        match = self.module.WHEEL_RE.match(name)
        self.assertIsNotNone(match)
        self.assertEqual(match.group(1), self.version)

    def test_release_version_is_x_y_z(self):
        self.assertRegex(self.version, r"^\d+\.\d+\.\d+$")

    def test_tagged_build_requires_clean_tree_at_tag_commit(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "docs/workflows/wf-cli").mkdir(parents=True)
            (root / "docs/workflows/wf-release").mkdir(parents=True)
            (root / "docs/workflows/wf-cli/file.txt").write_text("clean\n", encoding="utf-8")
            (root / "docs/workflows/wf-release/file.txt").write_text("clean\n", encoding="utf-8")
            subprocess.run(["git", "-C", tmp, "init", "-q"], check=True)
            subprocess.run(["git", "-C", tmp, "config", "user.email", "t@e"], check=True)
            subprocess.run(["git", "-C", tmp, "config", "user.name", "t"], check=True)
            subprocess.run(["git", "-C", tmp, "add", "-A"], check=True)
            subprocess.run(["git", "-C", tmp, "commit", "-qm", "release"], check=True)
            subprocess.run(["git", "-C", tmp, "tag", "wf-v0.0.8"], check=True)
            self.module.assert_release_identity("0.0.8", repo_root=tmp)
            (root / "docs/workflows/wf-cli/file.txt").write_text("dirty\n", encoding="utf-8")
            with self.assertRaises(self.module.BuildError):
                self.module.assert_release_identity("0.0.8", repo_root=tmp)


if __name__ == "__main__":
    unittest.main()