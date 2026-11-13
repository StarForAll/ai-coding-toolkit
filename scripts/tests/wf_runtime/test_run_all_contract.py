"""`run_all.sh` 的端到端契约（慢，默认跳过）：真子集、计划模式、失败传播。

跑法是**独占**的（`run_all.sh` 独占 `/tmp/wf-fixtures/*` 与发行副本），
所以要显式开 `WF_SLOW_TESTS=1` 才执行；默认单元层只跑快测试。
"""

import json
import os
import subprocess
import sys
import tempfile
import unittest
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
RUN_ALL = REPO / "scripts" / "tests" / "wf_runtime" / "full" / "run_all.sh"
SLOW = os.environ.get("WF_SLOW_TESTS") == "1"


def run(args, env=None, timeout=900):
    merged = {**os.environ, **(env or {})}
    if not merged.get("WF_RESULTS_DIR"):
        with tempfile.TemporaryDirectory(prefix="wf-run-all-args-") as results:
            merged["WF_RESULTS_DIR"] = results
            return subprocess.run(["bash", str(RUN_ALL), *args], capture_output=True, text=True,
                                  env=merged, timeout=timeout, cwd=str(REPO))
    return subprocess.run(["bash", str(RUN_ALL), *args], capture_output=True, text=True,
                          env=merged, timeout=timeout, cwd=str(REPO))


@unittest.skipUnless(SLOW, "WF_SLOW_TESTS=1 才跑 run_all 端到端（独占夹具）")
class RunAllContractTest(unittest.TestCase):
    def test_candidate_representative_from_empty_state_has_owned_flow_fixtures(self):
        with tempfile.TemporaryDirectory(prefix='wf-candidate-contract-') as root:
            manifest = json.loads((REPO / 'docs/workflows/wf-release/wf-release.json').read_text())
            version = manifest['version']
            candidate = Path(root) / 'candidate'
            prepare = subprocess.run([
                sys.executable, str(RUN_ALL.parent / 'prepare_candidate_repo.py'),
                '--tree', str(REPO / 'docs/workflows/wf-release'), '--version', version,
                '--out', str(candidate)], capture_output=True, text=True)
            self.assertEqual(prepare.returncode, 0, prepare.stdout + prepare.stderr)
            result = run(['--representative', '--fixture-deploy', 'candidate',
                          '--release-root', str(candidate), '--release-version', version,
                          '--release-ref', f'refs/tags/wf-v{version}', '--repro', 'green',
                          '--repro-group', 'install'],
                         {'WF_RESULTS_DIR': str(Path(root) / 'results')})
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            summary = json.loads((Path(root) / 'results/summary.json').read_text())
            self.assertEqual(summary['flow_ran'], 2)
            self.assertEqual(summary['fail'], 0)

    def test_interrupting_root_runner_cleans_its_command_and_fixtures(self):
        with tempfile.TemporaryDirectory(prefix='wf-root-cancel-') as results:
            env = {**os.environ, 'WF_RESULTS_DIR': results, 'WF_SUITES': 'r68_tests', 'WF_JOBS': '1'}
            proc = subprocess.Popen(['bash', str(RUN_ALL)], cwd=str(REPO), env=env,
                                    stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            try:
                deadline = time.monotonic() + 15
                while not (Path(results) / 'r68_tests.test.log').exists() and time.monotonic() < deadline:
                    if proc.poll() is not None:
                        break
                    time.sleep(0.05)
                self.assertIsNone(proc.poll(), 'runner failed before cancellation probe')
                self.assertTrue((Path(results) / 'r68_tests.test.log').exists())
                proc.terminate()
                stdout, stderr = proc.communicate(timeout=5)
                self.assertNotEqual(proc.returncode, 0, stdout + stderr)
                control = json.loads((Path(results) / '.runner.json').read_text())
                self.assertEqual(control['status'], 'cancelled')
                plan = json.loads((Path(results) / 'plan.json').read_text())
                self.assertFalse(Path(plan['fix']).exists())
                self.assertFalse((Path(results) / 'template').exists())
            finally:
                if proc.poll() is None:
                    proc.kill()
                proc.communicate(timeout=5)

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
        self.assertTrue(summary["template_reused"], "默认应复用 run 内夹具模板")
        self.assertGreaterEqual(summary["template_seconds"], 0)

    def test_template_can_be_disabled_for_determinism(self):
        results = tempfile.mkdtemp(prefix="wf-run-all-notemplate-")
        self.addCleanup(lambda: __import__("shutil").rmtree(results, ignore_errors=True))
        result = run([], {"WF_SUITES": "r70_tests", "WF_RESULTS_DIR": results,
                          "WF_NO_TEMPLATE": "1"})
        self.assertEqual(result.returncode, 0, result.stdout[-2000:])
        with open(os.path.join(results, "summary.json"), encoding="utf-8") as handle:
            summary = json.load(handle)
        self.assertFalse(summary["template_reused"], "WF_NO_TEMPLATE=1 时逐套件重建夹具")
        self.assertGreater(summary["init_seconds"], 0)

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
        bogus = tempfile.mkdtemp(prefix="wf-invalid-candidate-")
        self.addCleanup(lambda: __import__("shutil").rmtree(bogus, ignore_errors=True))
        result = run(["--representative", "--fixture-deploy", "candidate",
                      "--release-root", bogus, "--release-ref", "refs/tags/wf-v9.9.9",
                      "--release-version", "9.9.9"],
                     {"WF_RESULTS_DIR": results})
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("CANDIDATE-REPO-INVALID", result.stdout)


if __name__ == "__main__":
    unittest.main()
