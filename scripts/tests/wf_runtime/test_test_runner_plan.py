"""运行器执行计划（`full/plan.py`）：单一 plan 的模式、gating 与冲突规则。

这些断言锚在**计划对象**上（不是文案）：模式互斥、真子集、repro gating、
candidate 的发行身份与代表集兜底。`--list`/`--dry-run` 与实际执行共用同一份 `plan()`。
"""

import importlib.util
import tempfile
import unittest
from pathlib import Path

FULL = Path(__file__).resolve().parents[0] / "full"


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


plan = _load("wf_runner_plan", FULL / "plan.py")


def make(**env):
    return {key: value for key, value in env.items()}


class PlanModeTest(unittest.TestCase):
    def test_default_is_full_with_all_suites_flows_extra_and_green_repro(self):
        result = plan.plan([], make())
        self.assertEqual(result["mode"], "full")
        self.assertEqual(result["full_mode"], 1)
        self.assertEqual(len(result["suites_all"]), 59)
        self.assertEqual(result["flows"], ["f0", "p5_spec", "p5_v2v3", "p5_v5"])
        self.assertEqual(result["extra"], ["r72_tests"])
        self.assertEqual(result["repro_enabled"], 1)
        self.assertEqual(result["repro_mode"], "green")
        units = len(result["suites_all"]) + len(result["flows"]) + len(result["extra"])
        self.assertEqual(units + 85, 149)

    def test_wf_suites_implies_subset_and_drops_everything_else(self):
        result = plan.plan([], make(WF_SUITES="r70_tests"))
        self.assertEqual(result["mode"], "subset")
        self.assertEqual(result["full_mode"], 0)
        self.assertEqual(result["suites_all"], ["r70_tests"])
        self.assertEqual(result["flows"], [])
        self.assertEqual(result["extra"], [])
        self.assertEqual(result["repro_enabled"], 0)
        self.assertEqual(result["repro_mode"], "none")

    def test_explicit_modes_are_mutually_exclusive(self):
        for argv in (["--full", "--subset"], ["--full", "--representative"],
                     ["--subset", "--representative"], ["--full", "--subset", "--representative"]):
            with self.assertRaises(plan.PlanError) as caught:
                plan.plan(argv, make(WF_SUITES="r70_tests"))
            self.assertEqual(caught.exception.code, 2)

    def test_full_or_representative_with_wf_suites_is_refused(self):
        for mode in ("--full", "--representative"):
            with self.assertRaises(plan.PlanError):
                plan.plan([mode], make(WF_SUITES="r70_tests"))

    def test_subset_without_selection_lists_available_suites(self):
        with self.assertRaises(plan.PlanError) as caught:
            plan.plan(["--subset"], make())
        self.assertIn("r70_tests", str(caught.exception))

    def test_unknown_suite_and_unknown_group_are_refused(self):
        with self.assertRaises(plan.PlanError):
            plan.plan([], make(WF_SUITES="nope_tests"))
        with self.assertRaises(plan.PlanError) as caught:
            plan.plan(["--repro-group", "nope"], make())
        self.assertIn("review", str(caught.exception))

    def test_list_and_dry_run_only_produce_the_plan(self):
        for flag in ("--list", "--dry-run"):
            result = plan.plan([flag], make(WF_SUITES="r70_tests"))
            self.assertEqual(result["list_only"], 1)


class ReproGatingTest(unittest.TestCase):
    def test_subset_repro_needs_explicit_wf_with_repro(self):
        with self.assertRaises(plan.PlanError) as caught:
            plan.plan(["--repro", "green"], make(WF_SUITES="r70_tests"))
        self.assertIn("WF_WITH_REPRO", str(caught.exception))
        result = plan.plan(["--repro", "green"], make(WF_SUITES="r70_tests", WF_WITH_REPRO="1"))
        self.assertEqual(result["repro_enabled"], 1)
        self.assertEqual(result["repro_mode"], "green")

    def test_representative_runs_repro_without_wf_with_repro(self):
        result = plan.plan(["--representative"], make())
        self.assertEqual(result["repro_enabled"], 1)
        self.assertEqual(result["repro_mode"], "green")
        self.assertEqual(result["repro_groups"],
                         ["review", "archive", "identity", "writer", "install"])

    def test_representative_selects_representative_suites_and_flows(self):
        result = plan.plan(["--representative"], make())
        self.assertIn("f1_ordinary", result["suites_all"])
        self.assertNotIn("cp2_tests", result["suites_all"])
        self.assertEqual(result["flows"], ["f0", "p5_spec"])

    def test_repro_none_disables_repro_and_rejects_groups(self):
        result = plan.plan(["--repro", "none"], make())
        self.assertEqual(result["repro_enabled"], 0)
        with self.assertRaises(plan.PlanError):
            plan.plan(["--repro", "none", "--repro-group", "review"], make())

    def test_unknown_repro_mode_is_refused(self):
        with self.assertRaises(plan.PlanError):
            plan.plan(["--repro", "install"], make())


class FixtureDeployTest(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="wf-plan-candidate-")
        self.addCleanup(lambda: __import__("shutil").rmtree(self.root, ignore_errors=True))

    def candidate_args(self, **over):
        args = ["--fixture-deploy", "candidate", "--release-root", self.root,
                "--release-ref", "refs/tags/wf-v0.1.2", "--release-version", "0.1.2"]
        return args + over.pop("extra", [])

    def test_candidate_requires_release_identity(self):
        with self.assertRaises(plan.PlanError) as caught:
            plan.plan(["--fixture-deploy", "candidate"], make())
        self.assertIn("--release-root", str(caught.exception))

    def test_dev_rejects_release_arguments(self):
        with self.assertRaises(plan.PlanError):
            plan.plan(["--release-root", self.root], make())

    def test_candidate_refuses_red_and_both(self):
        for mode in ("red", "both"):
            with self.assertRaises(plan.PlanError):
                plan.plan(self.candidate_args(extra=["--repro", mode]), make())

    def test_candidate_representative_falls_back_to_candidate_smoke(self):
        result = plan.plan(["--representative"] + self.candidate_args(), make())
        self.assertEqual(result["fixture_deploy"], "candidate")
        self.assertEqual(result["suites_all"], ["f1_candidate_smoke"])
        self.assertEqual(result["candidate_smoke"], 1)
        # 没有 candidate_clean 组的组被排除，不静默拒绝整个 representative 模式
        self.assertIn("install", result["repro_groups"])

    def test_candidate_group_without_clean_case_is_refused(self):
        with self.assertRaises(plan.PlanError) as caught:
            plan.plan(["--representative"] +
                      self.candidate_args(extra=["--repro", "green", "--repro-group", "review"]),
                      make())
        self.assertIn("review", str(caught.exception))

    def test_candidate_full_refuses_when_no_candidate_clean_suite(self):
        with self.assertRaises(plan.PlanError):
            plan.plan(["--full"] + self.candidate_args(), make())


class PlanShellOutputTest(unittest.TestCase):
    def test_sh_output_is_evalable_and_matches_json(self):
        import json

        record = {}
        for key, value in plan.plan([], make(WF_SUITES="r70_tests")).items():
            if isinstance(value, list):
                value = " ".join(value)
            record["PLAN_" + key.upper()] = str(value)
        self.assertEqual(record["PLAN_MODE"], "subset")
        self.assertEqual(record["PLAN_SUITES_ALL"], "r70_tests")
        self.assertEqual(json.loads(json.dumps(record))["PLAN_REPRO_ENABLED"], "0")


if __name__ == "__main__":
    unittest.main()
