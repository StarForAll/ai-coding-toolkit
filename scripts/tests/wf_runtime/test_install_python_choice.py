"""安装命令自带解释器选择与确认（2026-11-25）。

用户要在一条安装命令里确定 Python 解释器：`--python <abs>`，缺省用系统 python3；
系统没有 python3 且没给参数时必须拒绝安装。确认动作仍由 bootstrap 的 confirm-executor 写，
安装器只负责预检、写全局配置（仅 --python）和转交。
"""

import importlib.util
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

REPO = Path(__file__).resolve().parents[3]
INSTALL = REPO / "docs" / "workflows" / "wf" / "payload" / "install.py"


def _install_module():
    spec = importlib.util.spec_from_file_location("wf_install_python_under_test", INSTALL)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class PythonCandidateTest(unittest.TestCase):
    def setUp(self):
        self.module = _install_module()

    def test_relative_path_is_refused(self):
        self.assertIn("绝对路径", self.module.python_candidate_problems("python3"))

    def test_missing_or_non_executable_is_refused(self):
        self.assertIn("可执行", self.module.python_candidate_problems("/nonexistent/python3"))
        self.assertIn("可执行", self.module.python_candidate_problems("/etc/hostname"))

    def test_non_python_binary_is_refused(self):
        problem = self.module.python_candidate_problems("/bin/true")
        self.assertIsNotNone(problem)
        self.assertIn("Python 版本", problem)

    def test_current_python_is_accepted(self):
        self.assertIsNone(self.module.python_candidate_problems(os.path.realpath(os.sys.executable)))


class GlobalExecutorWriteTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.home = Path(self._tmp.name)
        self.module = _install_module()

    def tearDown(self):
        self._tmp.cleanup()

    def test_writes_key_and_preserves_others(self):
        config = self.home / ".wf/config.json"
        config.parent.mkdir(parents=True)
        config.write_text(json.dumps({"other": 1}), encoding="utf-8")
        with mock.patch.dict(os.environ, {"HOME": str(self.home)}):
            self.assertIsNone(self.module.write_global_executor("/usr/bin/python3"))
        data = json.loads(config.read_text(encoding="utf-8"))
        self.assertEqual(data, {"other": 1, "python_executable": "/usr/bin/python3"})

    def test_invalid_existing_config_is_refused(self):
        config = self.home / ".wf/config.json"
        config.parent.mkdir(parents=True)
        config.write_text("{not json", encoding="utf-8")
        with mock.patch.dict(os.environ, {"HOME": str(self.home)}):
            self.assertIn("JSON", self.module.write_global_executor("/usr/bin/python3"))
        self.assertEqual(config.read_text(encoding="utf-8"), "{not json")


if __name__ == "__main__":
    unittest.main()
