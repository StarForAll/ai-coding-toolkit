"""repro 选择器（`full/repro/repro_select.py`）：组、candidate 过滤、auto 新鲜度、状态写者。

断言锚在**选择结果**上：
- 组是唯一权威（显式用例名），零匹配必须报错；
- `candidate_clean` 必须同时满足 assertion_target=installed + stage_role=scaffold，否则拒绝 manifest；
- candidate 模式只跑 candidate_clean 用例，其余进 `skipped_non_candidate`（不算通过）；
- `--mode auto` 首次/变化跑 both、未变化跑 green，且状态只由父进程（commit-state）写。
"""

import importlib.util
import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parents[0]
REPRO = HERE / "full" / "repro"


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


select = _load("wf_repro_select", REPRO / "repro_select.py")


class SelectionTest(unittest.TestCase):
    def test_group_selects_exact_members(self):
        result = select.select(["review"], fixture_deploy="dev", mode="green")
        groups = select.load_groups()
        self.assertEqual(sorted(result["cases"]), sorted(groups["groups"]["review"]))
        self.assertTrue(all(mode == "green" for mode in result["modes"].values()))

    def test_unknown_group_is_refused(self):
        with self.assertRaises(select.SelectError):
            select.select(["nope"], fixture_deploy="dev", mode="green")

    def test_group_referencing_missing_case_is_refused(self):
        groups = select.load_groups()
        broken = json.loads(json.dumps(groups))
        broken["groups"]["review"].append("does-not-exist")
        with self.assertRaises(select.SelectError):
            select.select(["review"], fixture_deploy="dev", mode="green", groups_doc=broken)

    def test_only_intersects_with_group_and_zero_match_fails(self):
        result = select.select(["identity"], only="bind", fixture_deploy="dev", mode="green")
        self.assertTrue(result["cases"])
        self.assertTrue(all("bind" in case for case in result["cases"]))
        with self.assertRaises(select.SelectError):
            select.select(["review"], only="bind", fixture_deploy="dev", mode="green")

    def test_red_mode_only_red(self):
        result = select.select(["review"], fixture_deploy="dev", mode="red")
        self.assertTrue(all(mode == "red" for mode in result["modes"].values()))

    def test_manifest_cannot_mark_stage_case_as_candidate_clean(self):
        groups = select.load_groups()
        broken = json.loads(json.dumps(groups))
        broken["cases"]["review-count-reject"]["candidate_clean"] = True
        with self.assertRaises(select.SelectError):
            select.select(["review"], fixture_deploy="dev", mode="green", groups_doc=broken)


class CandidateFilterTest(unittest.TestCase):
    def test_candidate_keeps_only_clean_and_reports_skipped(self):
        result = select.select(["install"], fixture_deploy="candidate", mode="green")
        self.assertEqual(sorted(result["cases"]),
                         ["branch-source-preview", "reinstall-preserves-data", "release-identity-commit"])
        self.assertEqual(sorted(result["skipped_non_candidate"]),
                         ["install-generation-bumps", "install-lock-foreign-object",
                          "install-lock-realpath", "install-receipt-metadata",
                          "install-receipt-relative", "uninstall-records-maintenance"])

    def test_candidate_group_without_clean_case_is_refused(self):
        with self.assertRaises(select.SelectError) as caught:
            select.select(["review"], fixture_deploy="candidate", mode="green")
        self.assertIn("candidate_clean", str(caught.exception))


class AutoModeTest(unittest.TestCase):
    def setUp(self):
        self.cache = tempfile.mkdtemp(prefix="wf-repro-state-")
        self.addCleanup(lambda: shutil.rmtree(self.cache, ignore_errors=True))
        self._old = os.environ.get("WF_TEST_RUN_CACHE")
        os.environ["WF_TEST_RUN_CACHE"] = self.cache
        self.addCleanup(self._restore)

    def _restore(self):
        if self._old is None:
            os.environ.pop("WF_TEST_RUN_CACHE", None)
        else:
            os.environ["WF_TEST_RUN_CACHE"] = self._old

    def test_first_run_forces_both(self):
        result = select.select(["review"], only="review-count-reject", fixture_deploy="dev",
                               mode="auto")
        self.assertEqual(result["modes"], {"review-count-reject": "both"})

    def test_unchanged_case_runs_green_only(self):
        select.auto_modes(["review-count-reject"], select.load_groups())
        state = select.read_state()
        state["helpers_digest"] = select.helpers_digest()
        state["cases"]["review-count-reject"] = {
            "script_digest": select.script_digest("review-count-reject"),
            "targets_digest": select.targets_digest(
                "review-count-reject", (select.load_groups().get("cases") or {}).get("review-count-reject")),
            "verified_both_at": "2026-11-13T00:00:00Z",
            "mode": "both",
        }
        select.write_state(state)
        result = select.select(["review"], only="review-count-reject", fixture_deploy="dev",
                               mode="auto")
        self.assertEqual(result["modes"], {"review-count-reject": "green"})

    def test_helper_change_forces_both_everywhere(self):
        state = select.read_state()
        state["helpers_digest"] = "sha256:stale"
        select.write_state(state)
        result = select.select(["review"], only="review-count-reject", fixture_deploy="dev",
                               mode="auto")
        self.assertEqual(result["modes"]["review-count-reject"], "both")

    def test_target_change_forces_both(self):
        groups = select.load_groups()
        meta = (groups.get("cases") or {}).get("review-count-reject") or {}
        state = select.read_state()
        state["helpers_digest"] = select.helpers_digest()
        state["cases"]["review-count-reject"] = {
            "script_digest": select.script_digest("review-count-reject"),
            "targets_digest": "sha256:stale",
            "verified_both_at": "2026-11-13T00:00:00Z",
        }
        select.write_state(state)
        result = select.select(["review"], only="review-count-reject", fixture_deploy="dev",
                               mode="auto")
        self.assertEqual(result["modes"]["review-count-reject"], "both")
        self.assertIsNotNone(select.targets_digest("review-count-reject", meta))

    def test_candidate_auto_refuses_when_red_is_needed(self):
        with self.assertRaises(select.SelectError) as caught:
            select.select(["install"], fixture_deploy="candidate", mode="auto")
        self.assertIn("dev 模式", str(caught.exception))

    def test_commit_state_only_records_verified_cases(self):
        results = tempfile.mkdtemp(prefix="wf-repro-results-")
        self.addCleanup(lambda: shutil.rmtree(results, ignore_errors=True))
        with open(os.path.join(results, "review-count-reject.json"), "w", encoding="utf-8") as handle:
            json.dump({"case": "review-count-reject", "mode": "both", "verified": True}, handle)
        with open(os.path.join(results, "review-unavailable.json"), "w", encoding="utf-8") as handle:
            json.dump({"case": "review-unavailable", "mode": "both", "verified": False}, handle)
        path, updated, kept = select.commit_state(results)
        self.assertEqual(updated, ["review-count-reject"])
        state = select.read_state()
        self.assertIn("review-count-reject", state["cases"])
        self.assertNotIn("review-unavailable", state["cases"])
        self.assertTrue(path.endswith("repro-state.json"))


if __name__ == "__main__":
    unittest.main()
