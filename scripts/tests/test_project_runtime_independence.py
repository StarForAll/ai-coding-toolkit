"""项目运行期不依赖全局 `wf` 命令（2026-11-26 人裁）。

判据：系统级 `wf` 只是**维护面**入口与转发便利；已安装项目的控制流（`version`/`help`/`status`/
`ready` 等日常命令，以及自含的 `repair.py`/`uninstall.py` 单文件入口）必须在本机根本没有 `wf`
命令时照常可用。因此这里把 PATH 收窄到找不到 `wf` 的位置，再跑同一条控制流。

防的失败：把 `servers：系统命令是唯一入口` 的旧口径当真——全局命令一卸载，项目就停在
"command not found"，而项目自己的 `.wf/bin/wf.py` 其实完全够用。
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
PAYLOAD = REPO / "docs" / "workflows" / "wf" / "payload"
DEV_DEPLOY = REPO / "scripts" / "wf-dev-deploy.py"


def _clean_env(home, path):
    env = {key: value for key, value in os.environ.items()
           if key not in ("WF_PROJECT_ROOT", "WF_BOOTSTRAP", "WF_PROJECT", "PYTHONPATH",
                          "WF_FORGEJO_BASE", "WF_GIT_URL")}
    env["HOME"] = str(home)
    env["PATH"] = path
    return env


def _confirm_system_executor(home, python):
    """按 `wf.py confirm-executor` 写入的记录字段，预置一条 system 确认（非 TTY 下无法交互确认）。"""
    probe = subprocess.run([python, "--version"], capture_output=True, text=True)
    version_text = ((probe.stdout or "") + (probe.stderr or "")).strip()
    stat = os.stat(os.path.realpath(python))
    record = {"interpreters": [{
        "scope": "system",
        "project_id": None,
        "key": "python_executable",
        "config_value": python,
        "path_identity": os.path.realpath(python),
        "size": stat.st_size,
        "mtime_ns": stat.st_mtime_ns,
        "python_version": version_text,
        "confirmed_at": "2026-11-26T00:00:00.000000Z",
    }]}
    (home / ".wf").mkdir(exist_ok=True)
    (home / ".wf" / "interpreters.json").write_text(
        json.dumps(record, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")


class RuntimeWithoutSystemCommandTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._tmp = tempfile.TemporaryDirectory()
        root = Path(cls._tmp.name)
        cls.home = root / "home"
        cls.home.mkdir()
        cls.project = root / "project"
        cls.project.mkdir()
        # PATH 只保留系统目录：本机即使装过系统命令也不在这里，模拟 `wf self-uninstall` 之后
        cls.path = "/usr/bin:/bin"
        cls.env = _clean_env(cls.home, cls.path)
        cls.python = shutil.which("python3", path=cls.path)
        if cls.python is None:  # 环境缺少 PATH 内的 python3：跳过而不是假通过
            raise unittest.SkipTest("PATH 内没有 python3")
        subprocess.run(["git", "-C", str(cls.project), "init", "-q", "-b", "main"], check=True)
        cls.deploy = subprocess.run(
            [sys.executable, str(DEV_DEPLOY), "--target", str(cls.project), "--confirm", "--json"],
            env=cls.env, capture_output=True, text=True, check=False)
        _confirm_system_executor(cls.home, cls.python)

    @classmethod
    def tearDownClass(cls):
        cls._tmp.cleanup()

    def _run(self, *argv):
        return subprocess.run([self.python, *argv], cwd=str(self.project), env=self.env,
                              capture_output=True, text=True, check=False)

    def test_the_system_command_really_is_absent(self):
        self.assertEqual(shutil.which("wf", path=self.path), None)
        self.assertEqual(self.deploy.returncode, 0, self.deploy.stdout + self.deploy.stderr)
        self.assertTrue((self.project / ".wf/bin/wf.py").is_file())

    def test_control_flow_commands_run_without_the_system_command(self):
        for argv in (["version"], ["help"], ["status", "--json"], ["ready", "--json"]):
            with self.subTest(argv=argv):
                result = self._run(str(self.project / ".wf/bin/wf.py"), *argv)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertIn("WF_OK", result.stdout)
                self.assertNotIn("command not found", (result.stdout + result.stderr).lower())

    def test_status_reports_a_normal_project_state(self):
        result = self._run(str(self.project / ".wf/bin/wf.py"), "status", "--json")
        payload = json.loads(result.stdout.strip().splitlines()[-1])
        self.assertEqual(payload["code"], "WF_OK")
        self.assertEqual(payload["facts"]["writer_state"], "idle")

    def test_local_repair_entry_runs_without_the_system_command(self):
        result = self._run(str(self.project / ".wf/bin/repair.py"), "--json")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("WF_OK", result.stdout)
        payload = json.loads(result.stdout.strip().splitlines()[-1])
        self.assertTrue(payload["ok"])
        self.assertEqual(Path(payload["facts"]["preview"]["target_root"]).resolve(),
                         self.project.resolve())


class RuntimeGuidanceTest(unittest.TestCase):
    """运行期指引必须以项目脚本为权威入口：文档口径不得把系统命令写成运行期必需。"""

    def setUp(self):
        self.session = (PAYLOAD / "workflows" / "session-flow.md").read_text(encoding="utf-8")
        self.maintenance = (PAYLOAD / "workflows" / "maintenance-flow.md").read_text(encoding="utf-8")

    def test_session_flow_names_the_project_script_as_the_authoritative_entry(self):
        self.assertIn(".wf/bin/wf.py", self.session)
        self.assertIn("项目控制流照常可用", self.session)
        self.assertIn("系统 `wf` 只是转发便利", self.session)
        self.assertNotIn("日常命令优先用系统级", self.session)
        self.assertNotIn("系统 `wf` 是统一入口", self.session)

    def test_maintenance_flow_offers_the_local_entries(self):
        self.assertIn("直接运行已安装版本的 `.wf/bin/repair.py`", self.maintenance)
        self.assertIn("直接运行已安装版本的 `.wf/bin/uninstall.py`", self.maintenance)
        self.assertIn("系统命令卸载后仍可直接运行", self.maintenance)


if __name__ == "__main__":
    unittest.main()