"""运行器执行计划（`full/plan.py`）：单一 plan 的模式、注册表校验、记录编码与 gating。

这些断言锚在**计划对象**上（不是文案）：模式互斥、真子集、repro gating、
candidate 的发行身份与代表集兜底、五段记录编码。`--list`/`--dry-run`/实际执行共用同一份 `plan()`。
"""

import importlib.util
import json
import os
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


def names(result):
    return [unit["name"] for unit in result["units"]]


def by_kind(result, kind):
    return [unit["name"] for unit in result["units"] if unit["kind"] == kind]


def records_by_kind(result, kind):
    return [record for record in
            [plan.unit_record(unit) for unit in result["units"]]
            if record.split(":")[1] == kind]


class PlanModeTest(unittest.TestCase):
    def test_default_is_full_with_all_units_and_green_repro(self):
        result = plan.plan([], make())
        self.assertEqual(result["mode"], "full")
        self.assertEqual(result["full_mode"], 1)
        self.assertEqual(len(by_kind(result, "suite")), 59)
        self.assertEqual(by_kind(result, "flow"), ["f0", "p5_spec", "p5_v2v3", "p5_v5"])
        self.assertEqual(by_kind(result, "extra"), ["r72_tests"])
        self.assertEqual(len(result["units"]), 64)
        self.assertEqual(result["repro_enabled"], 1)
        self.assertEqual(result["repro_mode"], "green")
        self.assertEqual(len(result["units"]) + 85, 149)

    def test_every_plannable_unit_has_a_five_segment_record(self):
        result = plan.plan([], make())
        registry = {entry["name"]: entry for entry in plan.load_units()["units"]}
        for unit in result["units"]:
            record = plan.unit_record(unit)
            parts = record.split(":")
            self.assertEqual(len(parts), 5, record)
            name, kind, expect, fixture, script = parts
            self.assertEqual(name, unit["name"])
            self.assertEqual(int(expect), registry[name]["expect"])
            self.assertEqual(fixture, registry[name].get("fixture", "template"))
            self.assertEqual(script, registry[name].get("script", name + ".py"))
        records = [plan.unit_record(unit) for unit in result["units"]]
        self.assertEqual(sorted(result["units_parallel"] + result["units_serial"]), sorted(records))
        self.assertFalse(set(result["units_parallel"]) & set(result["units_serial"]),
                         "并行/串行记录必须互斥")

    def test_f0_script_comes_from_the_registry_not_the_unit_name(self):
        result = plan.plan([], make())
        f0 = [unit for unit in result["units"] if unit["name"] == "f0"][0]
        self.assertEqual(f0["script"], "p5_f0.py")
        self.assertEqual(f0["fixture"], "install")
        self.assertIn("f0:flow:9:install:p5_f0.py", result["units_parallel"] + result["units_serial"])

    def test_wf_suites_implies_subset_and_drops_everything_else(self):
        result = plan.plan([], make(WF_SUITES="r70_tests"))
        self.assertEqual(result["mode"], "subset")
        self.assertEqual(result["full_mode"], 0)
        self.assertEqual(names(result), ["r70_tests"])
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

    def test_manual_units_are_not_plannable(self):
        with self.assertRaises(plan.PlanError) as caught:
            plan.plan([], make(WF_SUITES="d1_tests"))
        self.assertIn("manual", str(caught.exception))

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
        self.assertIn("f1_ordinary", names(result))
        self.assertNotIn("cp2_tests", names(result))
        self.assertEqual(by_kind(result, "flow"), ["f0", "p5_spec"])

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
        # 候选计划的 meta sidecar 必须真实存在且是 canonical 路径（R1）。
        with open(self.root + ".meta.json", "w", encoding="utf-8") as handle:
            handle.write("{}\n")
        self.addCleanup(lambda: os.path.exists(self.root + ".meta.json")
                        and os.unlink(self.root + ".meta.json"))

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

    def test_candidate_representative_uses_candidate_clean_suites(self):
        result = plan.plan(["--representative"] + self.candidate_args(), make())
        self.assertEqual(result["fixture_deploy"], "candidate")
        self.assertEqual(names(result), ["cp1_tests", "r7r15_tests", "r31r34_tests",
                                         "r70_tests", "r71_tests", "f1_ordinary",
                                         "f0", "p5_spec"])
        self.assertEqual(result["candidate_smoke"], 0)
        # 没有 candidate_clean 组的组被排除，不静默拒绝整个 representative 模式
        self.assertIn("install", result["repro_groups"])

    def test_candidate_group_without_clean_case_is_refused(self):
        with self.assertRaises(plan.PlanError) as caught:
            plan.plan(["--representative"] +
                      self.candidate_args(extra=["--repro", "green", "--repro-group", "review"]),
                      make())
        self.assertIn("review", str(caught.exception))

    def test_candidate_full_applies_one_qualification_to_all_units(self):
        result = plan.plan(["--full"] + self.candidate_args(), make())
        suites = [unit for unit in result["units"] if unit["kind"] == "suite"]
        self.assertEqual(len(suites), 57, "候选全量只跑经 candidate-audit 核实的 suite")
        self.assertTrue(all(unit["name"] not in ("r90_tests", "p5_v1")
                            for unit in suites))
        # flow/extra 与 suite 同一条资格：审计通过的 flow 保留，r72（源码安装器/固定旧 ref）排除。
        kinds = {unit["name"]: unit["kind"] for unit in result["units"]}
        for name in ("f0", "p5_spec", "p5_v2v3", "p5_v5"):
            self.assertEqual(kinds.get(name), "flow")
        self.assertNotIn("r72_tests", kinds)
        excluded = {item["name"]: item["reason"] for item in result["excluded_units"]}
        self.assertEqual(set(excluded), {"r90_tests", "p5_v1", "r72_tests"})
        for name, reason in excluded.items():
            self.assertIn("candidate_clean=false", reason, name)
        self.assertEqual(len(result["units"]), 61,
                         "候选全量分母 = 合格 suite + 合格 flow/extra（排除项被披露）")

    def test_candidate_subset_refuses_explicit_dev_only_units(self):
        with self.assertRaises(plan.PlanError) as caught:
            plan.plan(["--subset"] + self.candidate_args(), make(WF_SUITES="r72_tests"))
        self.assertIn("r72_tests", str(caught.exception))
        self.assertIn("candidate_clean=false", str(caught.exception))


class TagSelectionTest(unittest.TestCase):
    """`WF_TAGS`/`--tags` 选择套件；与 WF_SUITES 取交集；未知 tag 列出可选值。"""

    def test_tags_imply_subset_and_pick_tagged_suites(self):
        result = plan.plan(["--tags", "review"], make())
        self.assertEqual(result["mode"], "subset")
        self.assertEqual(result["tags"], ["review"])
        self.assertEqual(sorted(names(result)),
                         ["r68_tests", "r69_tests", "r70_tests", "r71_tests",
                          "r75_tests", "r79_tests"])
        self.assertEqual(result["repro_enabled"], 0)

    def test_wf_tags_env_is_a_selector_too(self):
        result = plan.plan([], make(WF_TAGS="archive"))
        self.assertEqual(result["mode"], "subset")
        self.assertIn("r31r34_tests", names(result))
        self.assertIn("f1_ordinary", names(result))

    def test_multiple_tags_are_union(self):
        result = plan.plan([], make(WF_TAGS="handover,instance"))
        self.assertIn("r71_tests", names(result))
        self.assertIn("r75_tests", names(result))
        self.assertIn("r76_tests", names(result))

    def test_unknown_tag_lists_available(self):
        with self.assertRaises(plan.PlanError) as caught:
            plan.plan(["--tags", "nope"], make())
        self.assertIn("review", str(caught.exception))

    def test_tags_intersect_with_wf_suites(self):
        result = plan.plan([], make(WF_SUITES="r68_tests r70_tests cp1_tests", WF_TAGS="review"))
        self.assertEqual(sorted(names(result)), ["r68_tests", "r70_tests"])

    def test_empty_intersection_is_refused(self):
        with self.assertRaises(plan.PlanError) as caught:
            plan.plan([], make(WF_SUITES="cp1_tests", WF_TAGS="review"))
        self.assertIn("交集", str(caught.exception))

    def test_full_and_representative_reject_tags(self):
        for mode in ("--full", "--representative"):
            with self.assertRaises(plan.PlanError):
                plan.plan([mode], make(WF_TAGS="review"))


class ChangedSuggestionTest(unittest.TestCase):
    """`--changed` 只给建议，不自动执行；映射规则：精确文件 → 最长目录前缀。"""

    def test_changed_without_list_is_refused(self):
        with self.assertRaises(plan.PlanError) as caught:
            plan.plan(["--changed-files", "docs/workflows/wf/payload/lib/wflib/review.py"], make())
        self.assertIn("只给建议", str(caught.exception))

    def test_changed_maps_modules_to_suites_and_repro(self):
        result = plan.plan(["--list", "--changed-files",
                            "docs/workflows/wf/payload/lib/wflib/review.py "
                            "docs/workflows/wf/payload/install.py"], make())
        self.assertIn("r68_tests", result["suggested_suites"])
        self.assertIn("r69_tests", result["suggested_suites"])
        self.assertIn("review", result["suggested_repro_groups"])
        self.assertIn("install", result["suggested_repro_groups"])
        self.assertEqual(result["unmapped_changes"], [])

    def test_unmapped_change_is_reported_not_guessed(self):
        result = plan.plan(["--list", "--changed-files", "README.md"], make())
        self.assertEqual(result["suggested_suites"], [])
        self.assertEqual(result["unmapped_changes"], ["README.md"])

    def test_directory_prefix_mapping(self):
        result = plan.plan(["--list", "--changed-files",
                            "docs/workflows/wf/payload/templates/task/prd.md"], make())
        self.assertIn("cp4_tests", result["suggested_suites"])

    def test_modules_referencing_unknown_suite_is_refused(self):
        original = plan.load_units

        def broken():
            doc = original()
            doc["modules"] = {"payload/lib/wflib/review.py": {"suites": ["ghost_tests"], "repro": []}}
            return doc

        plan.load_units = broken
        try:
            with self.assertRaises(plan.PlanError) as caught:
                plan.plan(["--list"], make())
            self.assertIn("ghost_tests", str(caught.exception))
        finally:
            plan.load_units = original


class ParallelismTest(unittest.TestCase):
    """默认并行（省墙钟），`--serial`/`WF_JOBS=1` 是确定性退路；repro 默认串行。"""

    def test_default_is_parallel_with_repro_serial(self):
        result = plan.plan([], make())
        self.assertEqual(result["jobs"], plan.DEFAULT_JOBS)
        self.assertEqual(result["repro_jobs"], plan.DEFAULT_REPRO_JOBS)
        self.assertEqual(result["parallel"], 1)
        self.assertEqual(result["repro_concurrent"], 0)

    def test_serial_flag_forces_one_worker(self):
        result = plan.plan(["--serial"], make(WF_JOBS="8"))
        self.assertEqual(result["jobs"], 1)
        self.assertEqual(result["repro_jobs"], 1)
        self.assertEqual(result["parallel"], 0)

    def test_total_jobs_overrides_default(self):
        result = plan.plan([], make(WF_TOTAL_JOBS="2", WF_REPRO_JOBS="3"))
        self.assertEqual(result["jobs"], 2)
        self.assertEqual(result["repro_jobs"], 3)

    def test_repro_concurrent_splits_the_budget(self):
        result = plan.plan(["--repro-concurrent"], make(WF_TOTAL_JOBS="8"))
        self.assertEqual(result["jobs"] + result["repro_jobs"], 8)
        self.assertEqual(result["repro_concurrent"], 1)

    def test_non_positive_jobs_is_refused(self):
        with self.assertRaises(plan.PlanError):
            plan.plan([], make(WF_TOTAL_JOBS="0"))


class TemplateSwitchesTest(unittest.TestCase):
    def test_no_template_implies_no_template_cache(self):
        for env in ({"WF_NO_TEMPLATE": "1"}, {"WF_NO_TEMPLATE_CACHE": "1"}):
            result = plan.plan([], make(**env))
            self.assertEqual(result["no_template_cache"], 1)
        self.assertEqual(plan.plan([], make())["no_template"], 0)
        self.assertEqual(plan.plan([], make(WF_NO_TEMPLATE="1"))["no_template"], 1)


class PlanShellOutputTest(unittest.TestCase):
    def test_sh_output_is_evalable_and_matches_json(self):
        result = plan.plan([], make(WF_SUITES="r70_tests"))
        record = {}
        for key, value in result.items():
            if key == "units":
                record["PLAN_UNITS"] = " ".join(plan.unit_record(unit) for unit in value)
            elif isinstance(value, list) and value and isinstance(value[0], dict):
                record["PLAN_" + key.upper()] = " ".join(plan.unit_record(unit) for unit in value)
            elif isinstance(value, list):
                record["PLAN_" + key.upper()] = " ".join(value)
            else:
                record["PLAN_" + key.upper()] = str(value)
        self.assertEqual(record["PLAN_MODE"], "subset")
        self.assertTrue(record["PLAN_UNITS"].startswith("r70_tests:suite:"))
        self.assertEqual(len(record["PLAN_UNITS"].split(":")), 5)
        self.assertEqual(record["PLAN_UNITS_PARALLEL"], record["PLAN_UNITS"])
        self.assertEqual(record["PLAN_UNITS_SERIAL"], "")
        self.assertEqual(json.loads(json.dumps(record))["PLAN_REPRO_ENABLED"], "0")


class RegistryValidationTest(unittest.TestCase):
    """`load_units` 的字段白名单与取值校验（`expect` 证据预算的防退化面）。"""

    def setUp(self):
        self.dir = tempfile.mkdtemp(prefix="wf-plan-registry-")
        self.addCleanup(lambda: __import__("shutil").rmtree(self.dir, ignore_errors=True))

    def write(self, document):
        path = os.path.join(self.dir, "units.json")
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(document, handle, ensure_ascii=False)
        return path

    def doc(self, **over):
        entry = {"name": "r70_tests", "kind": "suite", "expect": 5}
        entry.update(over.pop("entry", {}))
        document = {"schema_version": 2, "units": [entry], "modules": {},
                    "representative_flow": "p5_spec"}
        document.update(over.pop("document", {}))
        return document

    def assert_refused(self, document, needle):
        with self.assertRaises(plan.PlanError) as caught:
            plan.load_units(self.write(document))
        self.assertIn(needle, str(caught.exception))

    def test_minimal_registry_is_accepted(self):
        loaded = plan.load_units(self.write(self.doc()))
        self.assertEqual(loaded["units"][0]["name"], "r70_tests")

    def test_missing_expect_is_refused(self):
        self.assert_refused(self.doc(entry={"expect": None}), "expect")

    def test_non_positive_expect_is_refused(self):
        self.assert_refused(self.doc(entry={"expect": 0}), "expect")
        self.assert_refused(self.doc(entry={"expect": True}), "expect")

    def test_unknown_field_is_refused(self):
        self.assert_refused(self.doc(entry={"fallback_representative": True}), "未知字段")

    def test_unknown_kind_and_fixture_are_refused(self):
        self.assert_refused(self.doc(entry={"kind": "unknown"}), "kind")
        self.assert_refused(self.doc(entry={"fixture": "chroot"}), "fixture")

    def test_script_must_exist(self):
        self.assert_refused(self.doc(entry={"script": "no_such_script.py"}), "不存在")
        self.assert_refused(self.doc(entry={"script": "../escape.py"}), "相对路径")

    def test_manual_unit_needs_no_expect_or_script(self):
        document = {"schema_version": 2, "units": [
            {"name": "d1_tests", "kind": "manual", "notes": "需真实宿主压缩"}],
            "modules": {}, "representative_flow": "p5_spec"}
        loaded = plan.load_units(self.write(document))
        self.assertEqual(loaded["units"][0]["kind"], "manual")

    def test_manual_unit_without_notes_is_refused(self):
        document = {"schema_version": 2, "units": [
            {"name": "d1_tests", "kind": "manual"}],
            "modules": {}, "representative_flow": "p5_spec"}
        self.assert_refused(document, "notes")

    def test_old_schema_and_version_are_refused(self):
        self.assert_refused({"schema_version": 1, "suites": [{"name": "r70_tests"}]}, "units")
        self.assert_refused(self.doc(document={"schema_version": 1}), "schema_version")

    def test_parallel_false_requires_notes(self):
        self.assert_refused(self.doc(entry={"parallel": False}), "notes")
        loaded = plan.load_units(self.write(self.doc(entry={"parallel": False,
                                                            "notes": "pty 写入"})))
        self.assertIs(loaded["units"][0]["parallel"], False)


if __name__ == "__main__":
    unittest.main()
