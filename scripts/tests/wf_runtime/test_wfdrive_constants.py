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
        """既定决策（D4.3）：默认保持异解释器，不是 sys.executable。

        "异解释器"是**交付纪律**（SUT 驱动换一个解释器才能暴露路径/环境耦合），不是恒等式。
        单解释器机器（`sys.executable` 就是 `/usr/bin/python3`）上这条不变量无法在本机核实：
        跳过并说明，而不是把环境事实记成红（四轮审查 b-4：该红与改动无关却挡住整个套件）。
        """
        wfdrive = _load("wf_default", FULL / "wfdrive.py")
        self.assertEqual(wfdrive.PYTHON, "/usr/bin/python3")
        if os.path.realpath(wfdrive.PYTHON) == os.path.realpath(sys.executable):
            self.skipTest(f"本机 sys.executable 即 {wfdrive.PYTHON}：异解释器不变量无法在本机核实；"
                          "设 WF_TEST_PYTHON 指向另一个解释器后可核")
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
        if os.path.realpath(wfdrive.PYTHON) == os.path.realpath(sys.executable):
            self.skipTest("本机只有一个解释器：工具侧与驱动侧的差异不可核（同上）")
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
