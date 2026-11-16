"""repro 选择器与唯一 writer（`full/repro/repro_select.py`）：组、candidate 过滤、双身份、bundle。

断言锚在**冻结 bundle 与状态证明**上：
- 组是唯一权威，零匹配报错；candidate 只跑 candidate-clean；
- red subject 与 execution fingerprint 分开：candidate auto 只认同主体 + 同 release 内容/runtime 的 dev red；
- green 不续签 red，未知 targets 不可复用；
- 唯一 bundle 是冻结来源，commit-state 是唯一 writer，且写前验真实租约。
"""

import hashlib
import importlib.util
import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parents[0]
REPRO = HERE / "full" / "repro"
REPO = HERE.parents[2]
sys.path.insert(0, str(REPO / "scripts"))
sys.path.insert(0, str(REPO / "scripts" / "tests" / "wf_runtime" / "full"))


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


select = _load("wf_repro_select", REPRO / "repro_select.py")
import fixture_scope  # noqa: E402
import release_lock  # noqa: E402


def context_for(deploy="dev", subject="sha256:release"):
    return {"schema_version": 1, "deploy": deploy, "release_subject": subject,
            "release_root": "/tmp/fake-release", "version": "0.1.2", "ref": "refs/tags/wf-v0.1.2",
            "tree_digest": "sha256:tree", "manifest_digest": "sha256:manifest",
            "candidate": ({"commit": "c" * 40, "tree_digest": "sha256:tree"} if deploy == "candidate" else None)}


def subject_of(case, context):
    groups = select.load_groups()
    return select.red_subject(case, select.local_inputs(case, groups), select.public_inputs(), context)


def fingerprint_of(case, context):
    groups = select.load_groups()
    return select.input_fingerprint(case, select.local_inputs(case, groups),
                                    select.public_inputs(), context)


class Base(unittest.TestCase):
    def setUp(self):
        self.cache = tempfile.mkdtemp(prefix="wf-repro-state-")
        self.addCleanup(lambda: shutil.rmtree(self.cache, ignore_errors=True))
        self.results = Path(self.cache) / "results"
        self.results.mkdir()
        saved = {key: os.environ.get(key) for key in
                 ("WF_TEST_RUN_CACHE", "WF_RELEASE_TREE", "WF_FIXTURE_DEPLOY", "WF_RELEASE_CONTEXT")}
        os.environ["WF_TEST_RUN_CACHE"] = self.cache
        os.environ["WF_RELEASE_TREE"] = "/tmp/fake-release"
        os.environ["WF_FIXTURE_DEPLOY"] = "dev"
        os.environ.pop("WF_RELEASE_CONTEXT", None)
        self.addCleanup(self._restore, saved)
        self.context = context_for()
        patcher = mock.patch.object(select, "release_context", side_effect=lambda: dict(self.context))
        patcher.start()
        self.addCleanup(patcher.stop)
        for target in (fixture_scope, release_lock):
            for name in ("verify_lease", "verify_results_lock"):
                if hasattr(target, name):
                    patcher = mock.patch.object(target, name, return_value=True)
                    patcher.start()
                    self.addCleanup(patcher.stop)

    def _restore(self, saved):
        for key, value in saved.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value

    def bundle(self, case, mode, name="inputs.json"):
        selection = select.select([self.group_of(case)], only=case, fixture_deploy=self.context["deploy"],
                                  mode=mode)
        path = self.results / name
        select.write_bundle(str(path), select.bundle_document(selection))
        data = path.read_bytes()
        return selection, path, hashlib.sha256(data).hexdigest(), len(data)

    def record(self, case, mode, sha, fingerprint, verified=True):
        phases = select.PHASES[mode]
        record = {"case": case, "mode": mode, "verified": verified,
                  "execution_fingerprint": fingerprint,
                  "bundle_sha256": sha, "green_seconds": 0.1, "red_seconds": 0.2, "phases": {}}
        for phase in ("green", "red"):
            record[phase] = ("pass" if verified else "fail") if phase in phases else "skip"
            if phase in phases:
                (self.results / "logs").mkdir(exist_ok=True)
                (self.results / "logs" / f"{case}.{phase}.log").write_text(f"PASS {phase}: target\n")
                record["phases"][phase] = {"rc": 0, "status": "passed"}
        (self.results / (case + ".json")).write_text(json.dumps(record))
        return self.results / (case + ".json")

    def verify(self, case, mode):
        selection, path, sha, size = self.bundle(case, mode)
        self.record(case, mode, sha, selection["cases"][case]["execution_fingerprint"])
        return path, sha, size

    @staticmethod
    def group_of(case):
        for name, members in select.load_groups()["groups"].items():
            if case in members:
                return name
        raise AssertionError(case)


class SelectionTest(Base):
    def test_group_selects_exact_members(self):
        result = select.select(["review"], fixture_deploy="dev", mode="green")
        groups = select.load_groups()
        self.assertEqual(sorted(result["cases"]), sorted(groups["groups"]["review"]))
        self.assertTrue(all(record["mode"] == "green" for record in result["cases"].values()))

    def test_unknown_group_is_refused(self):
        with self.assertRaises(select.SelectError):
            select.select(["nope"], fixture_deploy="dev", mode="green")

    def test_group_referencing_missing_case_is_refused(self):
        broken = json.loads(json.dumps(select.load_groups()))
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
        self.assertTrue(all(record["mode"] == "red" for record in result["cases"].values()))

    def test_manifest_cannot_mark_stage_case_as_candidate_clean(self):
        broken = json.loads(json.dumps(select.load_groups()))
        broken["cases"]["review-count-reject"]["candidate_clean"] = True
        with self.assertRaises(select.SelectError):
            select.select(["review"], fixture_deploy="dev", mode="green", groups_doc=broken)


class CandidateFilterTest(Base):
    def test_candidate_keeps_only_clean_and_reports_skipped(self):
        self.context = context_for("candidate")
        result = select.select(["install"], fixture_deploy="candidate", mode="green")
        self.assertEqual(sorted(result["cases"]),
                         ["branch-source-preview", "reinstall-preserves-data", "release-identity-commit"])
        self.assertEqual(sorted(result["skipped_non_candidate"]),
                         ["install-generation-bumps", "install-lock-foreign-object",
                          "install-lock-realpath", "install-receipt-metadata",
                          "install-receipt-relative", "uninstall-records-maintenance"])

    def test_candidate_group_without_clean_case_is_refused(self):
        self.context = context_for("candidate")
        with self.assertRaises(select.SelectError) as caught:
            select.select(["review"], fixture_deploy="candidate", mode="green")
        self.assertIn("candidate_clean", str(caught.exception))

    def test_deploy_mismatch_between_context_and_request_is_refused(self):
        self.context = context_for("candidate")
        with self.assertRaises(select.SelectError):
            select.select(["install"], fixture_deploy="dev", mode="green")


class IdentityTest(Base):
    def test_subject_ignores_deploy_and_root_but_fingerprint_does_not(self):
        case = "review-count-reject"
        dev = select.execution_context()
        subject = subject_of(case, dev)
        fingerprint = fingerprint_of(case, dev)
        candidate = select.execution_context()
        candidate["deploy"] = "candidate"
        candidate["release_root_identity"] = "other-root"
        candidate["candidate_commit"] = "c" * 40
        self.assertEqual(subject, subject_of(case, candidate))
        self.assertNotEqual(fingerprint, fingerprint_of(case, candidate))

    def test_release_content_change_moves_the_subject(self):
        case = "review-count-reject"
        first = subject_of(case, select.execution_context())
        self.context = context_for(subject="sha256:other-release")
        self.assertNotEqual(first, subject_of(case, select.execution_context()))


class AutoModeTest(Base):
    def test_first_run_forces_both(self):
        result = select.select(["review"], only="review-count-reject", fixture_deploy="dev",
                               mode="auto")
        self.assertEqual(result["cases"]["review-count-reject"]["mode"], "both")

    def test_unchanged_case_runs_green_only(self):
        path, sha, size = self.verify("review-count-reject", "both")
        select.commit_state(str(self.results), str(path), sha, str(size))
        result = select.select(["review"], only="review-count-reject", fixture_deploy="dev",
                               mode="auto")
        self.assertEqual(result["cases"]["review-count-reject"]["mode"], "green")

    def test_green_does_not_certify_red(self):
        path, sha, size = self.verify("review-count-reject", "green")
        select.commit_state(str(self.results), str(path), sha, str(size))
        result = select.select(["review"], only="review-count-reject", fixture_deploy="dev",
                               mode="auto")
        self.assertEqual(result["cases"]["review-count-reject"]["mode"], "both")

    def test_helper_or_source_change_invalidates_red(self):
        path, sha, size = self.verify("review-count-reject", "both")
        select.commit_state(str(self.results), str(path), sha, str(size))
        with mock.patch.object(select, "helpers_digest", return_value="sha256:new-helpers"):
            result = select.select(["review"], only="review-count-reject", fixture_deploy="dev",
                                   mode="auto")
            self.assertEqual(result["cases"]["review-count-reject"]["mode"], "both")
        with mock.patch.object(select, "source_digest", return_value="sha256:new-source"):
            result = select.select(["review"], only="review-count-reject", fixture_deploy="dev",
                                   mode="auto")
            self.assertEqual(result["cases"]["review-count-reject"]["mode"], "both")

    def test_target_change_and_unknown_targets(self):
        path, sha, size = self.verify("review-count-reject", "both")
        select.commit_state(str(self.results), str(path), sha, str(size))
        with mock.patch.object(select, "targets_digest", return_value="sha256:target-v2"):
            result = select.select(["review"], only="review-count-reject", fixture_deploy="dev",
                                   mode="auto")
            self.assertEqual(result["cases"]["review-count-reject"]["mode"], "both")
        with mock.patch.object(select, "targets_digest", return_value=None):
            self.verify("review-count-reject", "both") if False else None
            result = select.select(["review"], only="review-count-reject", fixture_deploy="dev",
                                   mode="auto")
            self.assertEqual(result["cases"]["review-count-reject"]["mode"], "both")

    def test_candidate_auto_requires_matching_dev_red(self):
        # candidate-clean 用例：dev red 成功后可被同主体 candidate auto 复用。
        path, sha, size = self.verify("release-identity-commit", "both")
        select.commit_state(str(self.results), str(path), sha, str(size))
        self.context = context_for("candidate")
        result = select.select(["install"], only="release-identity-commit",
                               fixture_deploy="candidate", mode="auto")
        self.assertEqual(result["cases"]["release-identity-commit"]["mode"], "green")

    def test_candidate_auto_refuses_without_proof_or_with_other_release(self):
        self.context = context_for("candidate")
        with self.assertRaises(select.SelectError) as caught:
            select.select(["install"], only="release-identity-commit", fixture_deploy="candidate",
                          mode="auto")
        self.assertIn("dev", str(caught.exception))
        path, sha, size = self.verify("release-identity-commit", "both")
        select.commit_state(str(self.results), str(path), sha, str(size))
        self.context = context_for("candidate", subject="sha256:other-release")
        with self.assertRaises(select.SelectError):
            select.select(["install"], only="release-identity-commit", fixture_deploy="candidate",
                          mode="auto")

    def test_legacy_state_is_preserved_but_never_reused(self):
        case = "review-count-reject"
        legacy = {"schema_version": 2, "cases": {case: {"green": {"fingerprint": "old"}}}}
        Path(select.state_path()).write_text(json.dumps(legacy))
        self.assertEqual(select.auto_modes(
            {case: {"red_subject_digest": "x", "local_inputs": {"targets": "t"}}},
            select.load_groups())[case], "both")
        path, sha, size = self.verify(case, "green")
        select.commit_state(str(self.results), str(path), sha, str(size))
        self.assertIn("legacy", select.read_state()["cases"][case])

    def test_corrupt_state_is_not_silently_replaced(self):
        state = Path(select.state_path())
        state.write_text("{broken")
        before = state.read_bytes()
        with self.assertRaises(select.SelectError):
            select.read_state()
        self.assertEqual(state.read_bytes(), before)


class CommitTest(Base):
    def test_writer_barrier_scans_public_inputs_once(self):
        """唯一 writer 在最终 barrier 各重算一次 public/context（不随 case 数增长）。"""
        path, sha, size = self.verify("review-count-reject", "both")
        select.reset_scans()
        select.commit_state(str(self.results), str(path), sha, str(size))
        counts = select.scans()
        # 本 class 把 release_context 打了桩（固定 context），所以 release 计数恒为 0；
        # 真实 release 扫描次数由 ScanCountTest（用真实 context 文件）覆盖。
        self.assertEqual((counts["source"], counts["helpers"]), (1, 1),
                         "writer barrier 只重算一次 source/helpers 公共输入")
        self.assertLessEqual(counts["release"], 1)

    def test_commit_only_records_verified_cases_and_keeps_others(self):
        first, path, sha, size = self.bundle("review-count-reject", "both")
        second = select.select(["review"], only="review-unavailable", fixture_deploy="dev", mode="both")
        document = select.bundle_document(first)
        document["cases"].update(select.bundle_document(second)["cases"])
        sha, size = select.write_bundle(str(path), document)
        self.record("review-count-reject", "both", sha,
                    first["cases"]["review-count-reject"]["execution_fingerprint"])
        self.record("review-unavailable", "both", sha,
                    second["cases"]["review-unavailable"]["execution_fingerprint"], verified=False)
        path, updated, _kept = select.commit_state(str(self.results), str(path), sha, str(size))
        self.assertEqual(updated, ["review-count-reject"])
        entry = select.read_state()["cases"]["review-count-reject"]
        self.assertEqual(entry["red"]["subject"],
                         subject_of("review-count-reject", select.execution_context()))
        self.assertNotIn("review-unavailable", select.read_state()["cases"])
        self.assertTrue(path.endswith("repro-state.json"))

    def test_writer_without_lease_is_refused(self):
        path, sha, size = self.verify("review-count-reject", "both")
        with mock.patch.object(fixture_scope, "verify_lease",
                               side_effect=fixture_scope.FixtureError("no lease")):
            with self.assertRaises(fixture_scope.FixtureError):
                select.commit_state(str(self.results), str(path), sha, str(size))
        with mock.patch.object(fixture_scope, "verify_results_lock",
                               side_effect=fixture_scope.FixtureError("no lease")):
            with self.assertRaises(fixture_scope.FixtureError):
                select.commit_state(str(self.results), str(path), sha, str(size))

    def test_bundle_token_mismatch_is_refused(self):
        path, sha, size = self.verify("review-count-reject", "both")
        with self.assertRaises(select.SelectError):
            select.commit_state(str(self.results), str(path), "0" * 64, str(size))

    def test_changed_context_is_refused_at_commit(self):
        path, sha, size = self.verify("review-count-reject", "both")
        self.context = context_for(subject="sha256:other-release")
        with self.assertRaises(select.SelectError):
            select.commit_state(str(self.results), str(path), sha, str(size))

    def test_malformed_or_missing_results_block_the_writer(self):
        path, sha, size = self.verify("review-count-reject", "both")
        (self.results / "review-count-reject.json").unlink()
        with self.assertRaises(select.SelectError):
            select.commit_state(str(self.results), str(path), sha, str(size))
        self.record("review-count-reject", "both", sha, "wrong-fingerprint")
        with self.assertRaises(select.SelectError):
            select.commit_state(str(self.results), str(path), sha, str(size))


RELEASE_CONTEXT_DOC = {
    "schema_version": 1, "deploy": "dev", "release_root": "/tmp/fake-release",
    "version": "0.1.2", "ref": "refs/tags/wf-v0.1.2",
    "release_subject": "sha256:release", "tree_digest": "sha256:tree",
    "manifest_digest": "sha256:manifest", "candidate": None,
}


class ScanCountTest(unittest.TestCase):
    """AC8/R3：公共扫描次数不随 case 数增长（3 与 30 个 case 相同，各 1/1/1）。"""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="wf-repro-scan-")
        self.addCleanup(lambda: shutil.rmtree(self.tmp, ignore_errors=True))
        context = Path(self.tmp) / "context.json"
        context.write_text(json.dumps(RELEASE_CONTEXT_DOC), encoding="utf-8")
        saved = {key: os.environ.get(key) for key in ("WF_TEST_RUN_CACHE", "WF_RELEASE_CONTEXT")}
        os.environ["WF_TEST_RUN_CACHE"] = self.tmp
        os.environ["WF_RELEASE_CONTEXT"] = str(context)
        self.addCleanup(self._restore, saved)

    def _restore(self, saved):
        for key, value in saved.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value

    def freeze_synthetic(self, count):
        names = [f"synthetic-{index:02d}" for index in range(count)]
        groups = {"groups": {"synthetic": names}, "cases": {}}
        local = {"script": "sha256:script", "targets": None, "case_meta": {}}
        with mock.patch.object(select, "all_cases", return_value=names), \
                mock.patch.object(select, "local_inputs", return_value=local):
            select.reset_scans()
            selection = select.select(["synthetic"], fixture_deploy="dev", mode="green",
                                      groups_doc=groups)
        return selection, select.scans()

    def test_public_scans_are_constant_in_case_count(self):
        small, small_counts = self.freeze_synthetic(3)
        large, large_counts = self.freeze_synthetic(30)
        self.assertEqual(len(small["cases"]), 3)
        self.assertEqual(len(large["cases"]), 30)
        self.assertEqual(small_counts, {"source": 1, "release": 1, "helpers": 1})
        self.assertEqual(large_counts, small_counts)

    def test_worker_consumes_frozen_public_inputs(self):
        if str(REPRO) not in sys.path:
            sys.path.insert(0, str(REPRO))
        worker = _load("wf_repro_worker", REPRO / "_worker.py")
        worker.repro_select = select
        selection = select.select(["review"], only="review-count-reject", fixture_deploy="dev",
                                  mode="green")
        document = select.bundle_document(selection)
        select.reset_scans()
        self.assertIsNone(worker.verify_frozen_case(document, "review-count-reject", "green"))
        counts = select.scans()
        self.assertEqual(counts["source"], 0, "worker 不得重扫 source")
        self.assertEqual(counts["helpers"], 0, "worker 不得重扫 helpers")
        self.assertEqual(counts["release"], 1, "worker 只比对一次 execution context")


class BundleSchemaTest(Base):
    def test_schema_two_bundle_carries_public_and_local_inputs(self):
        selection = select.select(["review"], only="review-count-reject", fixture_deploy="dev",
                                  mode="green")
        document = select.bundle_document(selection)
        self.assertEqual(document["schema_version"], 2)
        self.assertEqual(sorted(document["public_inputs"]),
                         ["executor", "helpers", "runner", "source"])
        self.assertEqual(sorted(document["cases"]["review-count-reject"]["local_inputs"]),
                         ["case_meta", "script", "targets"])

    def test_schema_one_bundle_is_refused(self):
        selection = select.select(["review"], only="review-count-reject", fixture_deploy="dev",
                                  mode="green")
        document = select.bundle_document(selection)
        legacy = {"schema_version": 1,
                  "execution_context": document["execution_context"],
                  "mode": "green",
                  "cases": {case: {"mode": "green",
                                   "execution_fingerprint": record["execution_fingerprint"],
                                   "red_subject_digest": record["red_subject_digest"],
                                   "inputs": record["local_inputs"]}
                            for case, record in document["cases"].items()}}
        with self.assertRaises(select.SelectError) as caught:
            select.validate_bundle(legacy)
        self.assertIn("schema 2", str(caught.exception))

    def test_tampered_public_inputs_are_refused_at_the_writer_barrier(self):
        selection, path, sha, size = self.bundle("review-count-reject", "both")
        document = json.loads(Path(path).read_text())
        document["public_inputs"]["source"] = "sha256:tampered"
        data = json.dumps(document, ensure_ascii=False, indent=2, sort_keys=True).encode() + b"\n"
        Path(path).write_bytes(data)
        new_sha = hashlib.sha256(data).hexdigest()
        self.record("review-count-reject", "both", new_sha,
                    selection["cases"]["review-count-reject"]["execution_fingerprint"])
        with self.assertRaises(select.SelectError) as caught:
            select.commit_state(str(self.results), str(path), new_sha, str(len(data)))
        self.assertIn("public inputs changed", str(caught.exception))


if __name__ == "__main__":
    unittest.main()
