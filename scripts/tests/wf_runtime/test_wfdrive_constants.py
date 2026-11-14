"""wfdrive / _harness 的解释器与路径常量：显式契约的最小断言（交付纪律 §6）。

SUT 驱动解释器默认保持异解释器（session 锚点拓扑耦合，见任务
11-13-wf-runner-speed-quality 的 design D4.3）；两处默认字面量（wfdrive 与
repro/_harness，后者不 import 前者）必须一致——本断言是防漂移守卫。
"""

import importlib.util
import os
import sys
import unittest
from pathlib import Path
from unittest import mock

FULL = Path(__file__).resolve().parents[0] / "full"


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ConstantsTest(unittest.TestCase):
    def test_wf_test_python_override_takes_effect(self):
        with mock.patch.dict(os.environ, {"WF_TEST_PYTHON": "/custom/python3"}):
            wfdrive = _load("wf_override", FULL / "wfdrive.py")
            self.assertEqual(wfdrive.PYTHON, "/custom/python3")

    def test_default_is_divergent_interpreter(self):
        """既定决策（D4.3）：默认保持异解释器，不是 sys.executable。"""
        wfdrive = _load("wf_default", FULL / "wfdrive.py")
        self.assertEqual(wfdrive.PYTHON, "/usr/bin/python3")
        self.assertNotEqual(wfdrive.PYTHON, sys.executable)

    def test_harness_default_matches_wfdrive(self):
        """两处默认字面量必须一致（_harness 不 import wfdrive，唯一守卫在此）。"""
        wfdrive = _load("wf_a", FULL / "wfdrive.py")
        harness = _load("wf_b", FULL / "repro" / "_harness.py")
        self.assertEqual(wfdrive.PYTHON, harness.WF_PYTHON)

    def test_tool_python_is_sys_executable(self):
        """工具侧（install.py / wf-dev-deploy.py 启动）：与运行器同解释器，无行为变化。"""
        wfdrive = _load("wf_tool", FULL / "wfdrive.py")
        self.assertEqual(wfdrive.TOOL_PYTHON, sys.executable)
        self.assertNotEqual(wfdrive.TOOL_PYTHON, wfdrive.PYTHON)

    def test_repo_resolves_to_repository_root(self):
        """REPO 上溯层数守卫：wfdrive.py 位于
        <repo>/scripts/tests/wf_runtime/full/，差一层就会得到 <repo>/scripts。"""
        wfdrive = _load("wf_repo", FULL / "wfdrive.py")
        expected_root = str(Path(__file__).resolve().parents[3])
        self.assertEqual(wfdrive.REPO, expected_root)
        self.assertTrue(os.path.isdir(os.path.join(wfdrive.REPO, "docs", "workflows", "wf", "payload", "lib")))


if __name__ == "__main__":
    unittest.main()
