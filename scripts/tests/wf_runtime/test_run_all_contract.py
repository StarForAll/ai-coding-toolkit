"""`run_all.sh` 的端到端契约（慢，默认跳过）：真子集、计划模式、失败传播。

跑法是**独占**的（`run_all.sh` 独占 `/tmp/wf-fixtures/*` 与发行副本），
所以要显式开 `WF_SLOW_TESTS=1` 才执行；默认单元层只跑快测试。
"""

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
RUN_ALL = REPO / "scripts" / "tests" / "wf_runtime" / "full" / "run_all.sh"
SLOW = os.environ.get("WF_SLOW_TESTS") == "1"


def run(args, env=None, timeout=900):
    merged = {**os.environ, **(env or {})}
    return subprocess.run(["bash", str(RUN_ALL), *args], capture_output=True, text=True,
                          env=merged, timeout=timeout, cwd=str(REPO))


@unittest.skipUnless(SLOW, "WF_SLOW_TESTS=1 才跑 run_all 端到端（独占夹具）")
class RunAllContractTest(unittest.TestCase):
    def test_conflicting_modes_exit_nonzero(self):
        result = run(["--full", "--subset"])
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("模式互斥", result.stderr)

    def test_dry_run_only_prints_plan(self):
        results = tempfile.mkdtemp(prefix="wf-run-all-plan-")
        self.addCleanup(lambda: __import__("shutil").rmtree(results, ignore_errors=True))
        result = run(["--dry-run"], {"WF_SUITES": "r70_tests", "WF_RESULTS_DIR": results})
        self.assertEqual(result.returncode, 0, result.stderr)
        # 计划摘要在 stderr：stdout 必须是可 eval 的赋值（run_all 用它执行同一份计划）
        self.assertIn("计划执行单元: 1", result.stderr)
        self.assertEqual(result.stdout.strip(), "")
        with open(os.path.join(results, "plan.json"), encoding="utf-8") as handle:
            plan = json.load(handle)
        self.assertEqual(plan["mode"], "subset")
        self.assertEqual(plan["suites_all"], ["r70_tests"])
        self.assertEqual(plan["repro_enabled"], 0)

    def test_subset_runs_exactly_one_unit(self):
        results = tempfile.mkdtemp(prefix="wf-run-all-subset-")
        self.addCleanup(lambda: __import__("shutil").rmtree(results, ignore_errors=True))
        result = run([], {"WF_SUITES": "r70_tests", "WF_RESULTS_DIR": results})
        self.assertEqual(result.returncode, 0, result.stdout[-2000:] + result.stderr[-2000:])
        self.assertIn("运行 1 项", result.stdout)
        self.assertIn("GATE-OK", result.stdout)
        self.assertNotIn("REPRO_TOTAL", result.stdout)
        self.assertNotIn("r72_tests", result.stdout)
        with open(os.path.join(results, "summary.json"), encoding="utf-8") as handle:
            summary = json.load(handle)
        self.assertEqual(summary["suite_ran"], 1)
        self.assertEqual(summary["repro_ran"], 0)
        self.assertEqual(summary["flow_ran"], 0)

    def test_failing_suite_makes_the_gate_fail(self):
        # f1_candidate_smoke 在 dev 部署下必须失败（安装记录是 0.0.0-dev）
        results = tempfile.mkdtemp(prefix="wf-run-all-fail-")
        self.addCleanup(lambda: __import__("shutil").rmtree(results, ignore_errors=True))
        result = run([], {"WF_SUITES": "f1_candidate_smoke", "WF_RESULTS_DIR": results})
        self.assertNotEqual(result.returncode, 0, result.stdout[-2000:])
        self.assertIn("GATE-FAIL", result.stdout)

    def test_stale_test_release_is_refused_with_no_build(self):
        results = tempfile.mkdtemp(prefix="wf-run-all-stale-")
        self.addCleanup(lambda: __import__("shutil").rmtree(results, ignore_errors=True))
        result = run(["--no-build"], {"WF_SUITES": "r70_tests", "WF_RESULTS_DIR": results,
                                      "WF_TEST_RELEASE_CACHE": os.path.join(results, "empty-cache")})
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("TEST-RELEASE-STALE", result.stdout)

    def test_candidate_mode_requires_a_valid_candidate_repo(self):
        results = tempfile.mkdtemp(prefix="wf-run-all-candidate-")
        self.addCleanup(lambda: __import__("shutil").rmtree(results, ignore_errors=True))
        bogus = os.path.join(results, "candidate")
        os.makedirs(bogus)
        result = run(["--representative", "--fixture-deploy", "candidate",
                      "--release-root", bogus, "--release-ref", "refs/tags/wf-v9.9.9",
                      "--release-version", "9.9.9"],
                     {"WF_RESULTS_DIR": results})
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("CANDIDATE-REPO-INVALID", result.stdout)


if __name__ == "__main__":
    unittest.main()
