"""`--project` 可选的定位契约：缺省用当前目录。

判据（2026-11-26 人裁）：项目内三个入口不再要求显式 `--project`——
`.wf/bin/wf.py` 先按脚本安装位置确认 `.wf/bin` 布局，布局确认不了（重取/复制出来的入口）
就用当前目录；`repair.py` / `uninstall.py` 取 `--project` → `WF_PROJECT_ROOT` → 当前目录。
缺省路径同样要过 `.wf/` 布局与记录核对，所以"不在项目里"仍然给结构化阻断，而不是静默继续。
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
BIN = REPO / "docs" / "workflows" / "wf" / "payload" / "bin"
PYTHON = sys.executable


def _env(home):
    env = {key: value for key, value in os.environ.items()
           if key not in ("WF_PROJECT_ROOT", "WF_BOOTSTRAP", "WF_PROJECT")}
    env["HOME"] = str(home)
    env.pop("PYTHONPATH", None)
    return env


def _run(script, args, *, cwd, home):
    return subprocess.run([PYTHON, str(script), *args], cwd=str(cwd), env=_env(home),
                          stdin=subprocess.DEVNULL, capture_output=True, text=True, check=False)


def _code_of(output):
    for line in output.splitlines():
        line = line.strip()
        if line.startswith("{"):
            try:
                payload = json.loads(line)
            except ValueError:
                continue
            return payload.get("code")
    for line in output.splitlines():
        if line.startswith("BLOCKED"):
            return line.split(maxsplit=1)[1].strip() if len(line.split(maxsplit=1)) > 1 else ""
    return None


class OptionalProjectTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)
        self.home = self.root / "home"
        self.home.mkdir()
        self.project = self.root / "project"
        (self.project / ".wf" / "bin").mkdir(parents=True)

    def test_repair_reads_current_directory_as_project_root(self):
        result = _run(BIN / "repair.py", ["--json"], cwd=self.project, home=self.home)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        payload = json.loads(result.stdout.strip().splitlines()[-1])
        self.assertTrue(payload["ok"])
        self.assertEqual(Path(payload["facts"]["preview"]["target_root"]).resolve(),
                         self.project.resolve())

    def test_repair_outside_a_project_blocks_instead_of_guessing(self):
        outside = self.root / "outside"
        outside.mkdir()
        result = _run(BIN / "repair.py", ["--json"], cwd=outside, home=self.home)
        self.assertEqual(result.returncode, 1)
        self.assertEqual(_code_of(result.stdout), "WF_CAPABILITY_UNAVAILABLE")
        self.assertIn("不是 wf 项目", result.stdout)

    def test_uninstall_reads_current_directory_as_project_root(self):
        # 没有安装记录 → 记录类阻断（WF_ASSET_DECISION）；若定位失败会先报 WF_PATH_INVALID
        result = _run(BIN / "uninstall.py", ["--json"], cwd=self.project, home=self.home)
        self.assertEqual(result.returncode, 1)
        self.assertEqual(_code_of(result.stdout), "WF_ASSET_DECISION")

    def test_wf_bootstrap_falls_back_to_current_directory(self):
        # 复制出来的入口没有 `.wf/bin/` 布局：缺省应当用当前目录（项目根），并继续走执行器解析
        tool = self.root / "tool" / "bin"
        tool.mkdir(parents=True)
        copied = tool / "wf.py"
        shutil.copyfile(BIN / "wf.py", copied)
        shutil.copyfile(BIN / "wf.py", self.project / ".wf" / "bin" / "wf.py")
        result = _run(copied, ["confirm-executor", "--json"], cwd=self.project, home=self.home)
        self.assertEqual(_code_of(result.stdout), "WF_SEMANTIC_DECISION", result.stdout)
        self.assertEqual(result.returncode, 2)

    def test_wf_bootstrap_prefers_its_installed_layout_over_cwd(self):
        shutil.copyfile(BIN / "wf.py", self.project / ".wf" / "bin" / "wf.py")
        elsewhere = self.root / "elsewhere"
        elsewhere.mkdir()
        result = _run(self.project / ".wf" / "bin" / "wf.py", ["confirm-executor", "--json"],
                      cwd=elsewhere, home=self.home)
        self.assertEqual(_code_of(result.stdout), "WF_SEMANTIC_DECISION", result.stdout)


if __name__ == "__main__":
    unittest.main()