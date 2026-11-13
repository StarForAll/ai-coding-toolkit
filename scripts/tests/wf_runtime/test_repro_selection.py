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
from unittest import mock
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
    def _record_result(self, case, mode):
        root = os.path.join(self.cache, "results")
        os.makedirs(root, exist_ok=True)
        with open(os.path.join(root, case + ".json"), "w", encoding="utf-8") as handle:
            json.dump({"case": case, "mode": mode, "verified": True,
                       "green": "pass" if mode in ("green", "both") else "skip",
                       "red": "pass" if mode in ("red", "both") else "skip",
                       "fingerprint": select.input_fingerprint(case)}, handle)
        select.commit_state(root)
        os.unlink(os.path.join(root, case + ".json"))

    def test_green_does_not_certify_red_for_changed_target(self):
        case = "review-count-reject"
        with mock.patch.object(select, "targets_digest", return_value="target-v1"):
            self._record_result(case, "both")
        with mock.patch.object(select, "targets_digest", return_value="target-v2"):
            self.assertEqual(select.auto_modes([case], select.load_groups())[case], "both")
            self._record_result(case, "green")
            self.assertEqual(select.auto_modes([case], select.load_groups())[case], "both")

    def test_partial_verification_does_not_refresh_other_helper_evidence(self):
        first, second = "review-count-reject", "install-receipt-relative"
        with mock.patch.object(select, "helpers_digest", return_value="helpers-v1"):
            self._record_result(first, "both")
            self._record_result(second, "both")
        with mock.patch.object(select, "helpers_digest", return_value="helpers-v2"):
            self._record_result(first, "both")
            self.assertEqual(select.auto_modes([second], select.load_groups())[second], "both")

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

    def test_legacy_evidence_is_preserved_but_never_reused(self):
        case = "review-count-reject"
        legacy = {"schema_version": 1, "helpers_digest": "old-helper", "cases": {
            case: {"script_digest": "old-script", "verified_both_at": "old-proof"}}}
        Path(select.state_path()).write_text(json.dumps(legacy))
        self.assertEqual(select.auto_modes([case], select.load_groups())[case], "both")
        self._record_result(case, "green")
        saved = select.read_state()["cases"][case]
        self.assertEqual(saved["legacy"], legacy["cases"][case])
        self.assertEqual(select.auto_modes([case], select.load_groups())[case], "both")

    def test_corrupt_state_is_not_silently_replaced(self):
        state = Path(select.state_path())
        state.write_text('{broken')
        before = state.read_bytes()
        with self.assertRaises(select.SelectError):
            select.read_state()
        self.assertEqual(state.read_bytes(), before)

    def test_red_only_proves_current_red_but_unknown_targets_never_reuse_it(self):
        case = 'review-count-reject'
        self._record_result(case, 'red')
        self.assertEqual(select.auto_modes([case], select.load_groups())[case], 'green')
        with mock.patch.object(select, 'targets_digest', return_value=None):
            self._record_result(case, 'both')
            self.assertEqual(select.auto_modes([case], select.load_groups())[case], 'both')

    def test_dependency_changes_invalidate_reusable_red_evidence(self):
        case = 'review-count-reject'
        self.assertTrue(hasattr(select, 'source_digest'), 'source inputs are not fingerprinted')
        with mock.patch.object(select, 'source_digest', return_value='source-v1'):
            self._record_result(case, 'both')
        with mock.patch.object(select, 'source_digest', return_value='source-v2'):
            self.assertEqual(select.auto_modes([case], select.load_groups())[case], 'both')

    def test_unchanged_case_runs_green_only(self):
        self._record_result("review-count-reject", "both")
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
            json.dump({"case": "review-count-reject", "mode": "both", "verified": True,
                       "green": "pass", "red": "pass",
                       "fingerprint": select.input_fingerprint("review-count-reject")}, handle)
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
