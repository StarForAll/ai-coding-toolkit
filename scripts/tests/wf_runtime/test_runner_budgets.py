"""产品热路径性能守护（G5）：`wf.py status`（pyc 预热）5 次中位数 < 500ms。

阈值只有一处定义（PRD R5.4 = design D5-G5）：≈8× 当前实测（~62ms），用于尽早抓
`task-check 1.87s` 那类 30× 级回归。允许 `WF_PERF_GUARD=0` 关闭（关闭原因必须写在
断言消息/注释里：例如在低性能共享 CI 机上，墙钟阈值会假红）。

setUpClass 只建一次夹具（wf_fixture.sh + f1_init.py），测试本身不重复部署。
"""

import os
import shutil
import statistics
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
FULL = Path(__file__).resolve().parent / "full"
PYTHON = "/softwares/python/bin/python3"   # 项目声明解释器（AGENTS.md §4）
THRESHOLD_SECONDS = 0.5                    # 唯一阈值：5 次中位数 < 500ms
GUARD_OFF = os.environ.get("WF_PERF_GUARD") == "0"


@unittest.skipIf(GUARD_OFF, "WF_PERF_GUARD=0：显式关闭热路径性能守护（低性能/共享 CI 机）")
class ProductHotPathBudgetTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = tempfile.mkdtemp(prefix="wf-budget-fixture-")
        cls.pycache = tempfile.mkdtemp(prefix="wf-budget-pycache-")
        env = {key: value for key, value in os.environ.items()
               if key not in ("WF_RELEASE_ROOT", "WF_RELEASE_REF", "WF_RELEASE_VERSION",
                              "WF_RELEASE_META", "WF_FIXTURE_DEPLOY")}
        env["PYTHONPYCACHEPREFIX"] = cls.pycache
        fixture = subprocess.run(["bash", str(FULL / "wf_fixture.sh"), cls.root, "--deploy", "dev"],
                                 capture_output=True, text=True, env=env, cwd=str(REPO), timeout=180)
        if fixture.returncode != 0:
            shutil.rmtree(cls.root, ignore_errors=True)
            shutil.rmtree(cls.pycache, ignore_errors=True)
            raise unittest.SkipTest(f"夹具构建失败（无法测量热路径）：{(fixture.stderr or fixture.stdout)[-400:]}")
        init = subprocess.run([PYTHON, str(FULL / "f1_init.py")], capture_output=True, text=True,
                              env={**env, "WF_FIX": cls.root}, cwd=str(REPO), timeout=180)
        if init.returncode != 0:
            shutil.rmtree(cls.root, ignore_errors=True)
            shutil.rmtree(cls.pycache, ignore_errors=True)
            raise unittest.SkipTest(f"f1_init 失败（无法测量热路径）：{(init.stderr or init.stdout)[-400:]}")

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.root, ignore_errors=True)
        shutil.rmtree(cls.pycache, ignore_errors=True)

    def measure(self):
        command = [PYTHON, os.path.join(self.root, ".wf/bin/wf.py"), "status", "--json"]
        started = time.monotonic()
        result = subprocess.run(command, capture_output=True, text=True, timeout=60)
        elapsed = time.monotonic() - started
        self.assertEqual(result.returncode, 0, result.stderr[-500:] + result.stdout[-500:])
        return elapsed

    def test_status_median_is_under_budget(self):
        self.measure()   # 预热：首次运行包含一次编译（pyc 落 $PYTHONPYCACHEPREFIX）
        samples = [self.measure() for _ in range(5)]
        median = statistics.median(samples)
        self.assertLess(
            median, THRESHOLD_SECONDS,
            f"wf.py status 5 次中位数 {median * 1000:.0f}ms 超过阈值 {THRESHOLD_SECONDS * 1000:.0f}ms"
            f"（samples={[round(value * 1000) for value in samples]}ms）；"
            "关闭方式：WF_PERF_GUARD=0（需在任务记录写明关闭原因）")


if __name__ == "__main__":
    unittest.main()
