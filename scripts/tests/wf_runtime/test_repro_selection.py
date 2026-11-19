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


RUNTIME = {
    "tool": {"role": "tool", "path_identity": "sha256:tool-path",
             "binary_digest": "sha256:tool-bin", "invocation_digest": "sha256:tool-inv",
             "implementation": "cpython", "version": "3.14.7"},
    "sut": {"role": "sut", "path_identity": "sha256:sut-path",
            "binary_digest": "sha256:sut-bin", "invocation_digest": "sha256:sut-inv",
            "implementation": "cpython", "version": "3.11.9"},
}


def context_for(deploy="dev", subject="sha256:release"):
    return {"schema_version": 2, "deploy": deploy, "release_subject": subject,
            "runtime": RUNTIME,
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
        self.run_id = "run-test-0001"
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
        commands = self.results / "commands"
        commands.mkdir(exist_ok=True)
        for phase in ("green", "red"):
            record[phase] = ("pass" if verified else "fail") if phase in phases else "skip"
            if phase in phases:
                (self.results / "logs").mkdir(exist_ok=True)
                log = self.results / "logs" / f"{case}.{phase}.log"
                log.write_text(f"PASS {phase}: target\n")
                command_id = f"{case}-{phase}-{sha[:8]}"
                receipt = {"schema_version": 1, "command_id": command_id,
                           "run_id": self.run_id, "evidence_scope": "managed-child",
                           "state": "finished", "log_path": str(log),
                           "argv": [sys.executable, str(REPRO / (case + ".py")), "--expect", phase],
                           "result": {"rc": 0, "status": "passed" if verified else "failed"},
                           "supervision": {"cleanup_state": "cleaned"},
                           "local_cleanup": "removed", "retained_paths": []}
                (commands / (command_id + ".json")).write_text(json.dumps(receipt))
                record["phases"][phase] = {"rc": 0,
                                           "status": "passed" if verified else "failed",
                                           "command_id": command_id}
        (self.results / (case + ".json")).write_text(json.dumps(record))
        return self.results / (case + ".json")

    def commit(self, path, sha, size, **overrides):
        values = {"run_id": self.run_id, "evidence_root": str(self.results / "commands")}
        values.update(overrides)
        return select.commit_state(str(self.results), str(path), sha, str(size), **values)

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
        self.commit(path, sha, size)
        result = select.select(["review"], only="review-count-reject", fixture_deploy="dev",
                               mode="auto")
        self.assertEqual(result["cases"]["review-count-reject"]["mode"], "green")

    def test_green_does_not_certify_red(self):
        path, sha, size = self.verify("review-count-reject", "green")
        self.commit(path, sha, size)
        result = select.select(["review"], only="review-count-reject", fixture_deploy="dev",
                               mode="auto")
        self.assertEqual(result["cases"]["review-count-reject"]["mode"], "both")

    def test_helper_or_source_change_invalidates_red(self):
        path, sha, size = self.verify("review-count-reject", "both")
        self.commit(path, sha, size)
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
        self.commit(path, sha, size)
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
        self.commit(path, sha, size)
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
        self.commit(path, sha, size)
        self.context = context_for("candidate", subject="sha256:other-release")
        with self.assertRaises(select.SelectError):
            select.select(["install"], only="release-identity-commit", fixture_deploy="candidate",
                          mode="auto")

    def test_legacy_state_is_preserved_but_never_reused(self):
        case = "review-count-reject"
        for schema in (1, 2, 3):
            with self.subTest(schema=schema):
                legacy = {"schema_version": schema,
                          "cases": {case: {"green": {"fingerprint": "old"},
                                           "red": {"subject": "old", "fingerprint": "old"}}}}
                Path(select.state_path()).write_text(json.dumps(legacy))
                self.assertEqual(select.auto_modes(
                    {case: {"red_subject_digest": "x", "local_inputs": {"targets": "t"}}},
                    select.load_groups())[case], "both")
        legacy = {"schema_version": 2, "cases": {case: {"green": {"fingerprint": "old"}}}}
        Path(select.state_path()).write_text(json.dumps(legacy))
        self.assertEqual(select.auto_modes(
            {case: {"red_subject_digest": "x", "local_inputs": {"targets": "t"}}},
            select.load_groups())[case], "both")
        path, sha, size = self.verify(case, "green")
        self.commit(path, sha, size)
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
        self.commit(path, sha, size)
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
        path, updated, _kept = self.commit(path, sha, size)
        self.assertEqual(updated, ["review-count-reject"])
        entry = select.read_state()["cases"]["review-count-reject"]
        self.assertEqual(entry["red"]["subject"],
                         subject_of("review-count-reject", select.execution_context()))
        self.assertNotIn("review-unavailable", select.read_state()["cases"])
        self.assertTrue(path.endswith("repro-state.json"))

    def test_phase_answers_cover_every_frozen_phase(self):
        first, path, sha, size = self.bundle("review-count-reject", "both")
        second = select.select(["review"], only="review-unavailable", fixture_deploy="dev",
                               mode="both")
        document = select.bundle_document(first)
        document["cases"].update(select.bundle_document(second)["cases"])
        sha, size = select.write_bundle(str(path), document)
        self.record("review-count-reject", "both", sha,
                    first["cases"]["review-count-reject"]["execution_fingerprint"])
        bundle = json.loads(path.read_text())
        bundle["__sha256"] = sha
        # 缺记录：只影响该 case 的相位，被记为 unverified。
        report = select.validate_repro(
            str(self.results), bundle, evidence_root=str(self.results / "commands"),
            run_id=self.run_id)
        self.assertEqual(report["missing"], ["review-unavailable"])
        self.assertIn("review-unavailable", report["case_states"])
        for phase in ("green", "red"):
            counts = report["phases"][phase]
            self.assertEqual(counts["planned"],
                             counts["passed"] + counts["failed"] + counts["unverified"])
        self.assertTrue(report["records"]["review-count-reject"]["verified"])
        # 坏记录：同样只影响它自己的相位，报告不中断。
        (self.results / "review-unavailable.json").write_text("{broken")
        report = select.validate_repro(
            str(self.results), bundle, evidence_root=str(self.results / "commands"),
            run_id=self.run_id)
        self.assertEqual(report["malformed"], ["review-unavailable.json"])
        self.assertEqual(report["missing"], [])
        for phase in ("green", "red"):
            counts = report["phases"][phase]
            self.assertEqual(counts["planned"],
                             counts["passed"] + counts["failed"] + counts["unverified"])
        self.assertTrue(report["records"]["review-count-reject"]["verified"])

    def test_writer_without_lease_is_refused(self):
        path, sha, size = self.verify("review-count-reject", "both")
        with mock.patch.object(fixture_scope, "verify_lease",
                               side_effect=fixture_scope.FixtureError("no lease")):
            with self.assertRaises(fixture_scope.FixtureError):
                self.commit(path, sha, size)
        with mock.patch.object(fixture_scope, "verify_results_lock",
                               side_effect=fixture_scope.FixtureError("no lease")):
            with self.assertRaises(fixture_scope.FixtureError):
                self.commit(path, sha, size)

    def test_bundle_token_mismatch_is_refused(self):
        path, sha, size = self.verify("review-count-reject", "both")
        with self.assertRaises(select.SelectError):
            self.commit(path, "0" * 64, size)

    def test_changed_context_is_refused_at_commit(self):
        path, sha, size = self.verify("review-count-reject", "both")
        self.context = context_for(subject="sha256:other-release")
        with self.assertRaises(select.SelectError):
            self.commit(path, sha, size)

    def test_missing_or_malformed_results_only_affect_their_phases(self):
        path, sha, size = self.verify("review-count-reject", "both")
        (self.results / "review-count-reject.json").unlink()
        # 缺失记录不再中断整份报告/写证明：该 case 的相位记为 unverified，其余证书照常。
        self.commit(path, sha, size)
        self.assertNotIn("review-count-reject", select.read_state()["cases"])
        self.record("review-count-reject", "both", sha, "wrong-fingerprint")
        self.commit(path, sha, size)
        self.assertNotIn("review-count-reject", select.read_state()["cases"],
                         "错代/矛盾记录不得冒充可复用证明")
        # 计划外记录仍是结构问题（不进入任何相位）。
        (self.results / "unexpected-case.json").write_text(
            json.dumps({"case": "unexpected-case", "mode": "both"}))
        with self.assertRaises(select.SelectError):
            self.commit(path, sha, size)


RELEASE_CONTEXT_DOC = {
    "schema_version": 2, "deploy": "dev", "release_root": "/tmp/fake-release",
    "version": "0.1.2", "ref": "refs/tags/wf-v0.1.2",
    "release_subject": "sha256:release", "tree_digest": "sha256:tree",
    "manifest_digest": "sha256:manifest", "runtime": RUNTIME, "candidate": None,
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


class PublicHelperIdentityTest(Base):
    def test_helper_set_covers_core_proof_inputs(self):
        for name in ("cli.py", "../resource_lifecycle.py", "../library_source.py",
                     "../prepare_candidate_repo.py",
                     "../release_context.py", "../results_gate.py", "../results_summary.py",
                     "../fixture_scope.py", "../execute_gate.py", "../run_all.sh",
                     "../../../../wf_test_paths.py"):
            self.assertIn(name, select.HELPERS, f"{name} 必须进入公共 helper 身份")
        selection = select.select(["review"], only="review-count-reject",
                                  fixture_deploy="dev", mode="green")
        document = select.bundle_document(selection)
        self.assertEqual(document["public_inputs"]["helper_set"], "core-v2")

    def test_stale_helper_set_bundle_is_refused(self):
        selection = select.select(["review"], only="review-count-reject",
                                  fixture_deploy="dev", mode="green")
        document = select.bundle_document(selection)
        document["public_inputs"].pop("helper_set")
        with self.assertRaises(select.SelectError) as caught:
            select.validate_bundle(document)
        self.assertIn("helper set", str(caught.exception))

    def test_core_helper_change_moves_the_subject(self):
        case = "review-count-reject"
        public = select.public_inputs()
        groups = select.load_groups()
        local = select.local_inputs(case, groups)
        context = select.execution_context()
        first = select.red_subject(case, local, public, context)
        changed = dict(public)
        changed["helpers"] = "sha256:changed-helper"
        self.assertNotEqual(first, select.red_subject(case, local, changed, context))


class BundleSchemaTest(Base):
    def test_schema_three_bundle_carries_public_and_local_inputs(self):
        selection = select.select(["review"], only="review-count-reject", fixture_deploy="dev",
                                  mode="green")
        document = select.bundle_document(selection)
        self.assertEqual(document["schema_version"], 3)
        self.assertEqual(sorted(document["public_inputs"]),
                         ["executor", "helper_set", "helpers", "runner", "source"])
        self.assertEqual(sorted(document["cases"]["review-count-reject"]["local_inputs"]),
                         ["case_meta", "script", "targets"])

    def test_schema_one_bundle_is_refused(self):
        selection = select.select(["review"], only="review-count-reject", fixture_deploy="dev",
                                  mode="green")
        document = select.bundle_document(selection)
        legacy = {"schema_version": 2,
                  "execution_context": document["execution_context"],
                  "mode": "green",
                  "cases": {case: {"mode": "green",
                                   "execution_fingerprint": record["execution_fingerprint"],
                                   "red_subject_digest": record["red_subject_digest"],
                                   "inputs": record["local_inputs"]}
                            for case, record in document["cases"].items()}}
        with self.assertRaises(select.SelectError) as caught:
            select.validate_bundle(legacy)
        self.assertIn("schema 3", str(caught.exception))

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
            self.commit(path, new_sha, len(data))
        self.assertIn("public inputs changed", str(caught.exception))



class ProofGateTest(Base):
    """R2：proof 只接收本代、相位证据齐全且清理已确认的用例。"""

    def bundle_for(self, case="review-count-reject", mode="both"):
        selection, path, sha, size = self.bundle(case, mode)
        self.record(case, mode, sha, selection["cases"][case]["execution_fingerprint"])
        bundle = json.loads(path.read_bytes())
        bundle["__sha256"] = sha
        return bundle, path, sha, size

    def phase_report(self, bundle):
        return select.validate_repro(str(self.results), bundle,
                                     evidence_root=str(self.results / "commands"),
                                     run_id=self.run_id)

    def receipt_path(self, case, phase):
        record = json.loads((self.results / (case + ".json")).read_text())
        return self.results / "commands" / (record["phases"][phase]["command_id"] + ".json")

    def mutate_receipt(self, case, phase, **fields):
        path = self.receipt_path(case, phase)
        record = json.loads(path.read_text())
        record.update(fields)
        path.write_text(json.dumps(record))
        return path

    def test_clean_case_is_eligible_and_proof_is_written(self):
        bundle, bundle_path, sha, size = self.bundle_for()
        report = self.phase_report(bundle)
        self.assertEqual(report["phases"]["green"]["passed"], 1)
        self.assertEqual(report["phases"]["red"]["passed"], 1)
        path, updated, _kept = self.commit(bundle_path, sha, size)
        self.assertEqual(updated, ["review-count-reject"])
        self.assertTrue(str(path).endswith("repro-state.json"))
        entry = select.read_state()["cases"]["review-count-reject"]
        self.assertEqual(set(entry), {"green", "red"},
                         "both 模式记录两相位各自的清理确认")

    def test_red_only_proof_does_not_claim_an_unrun_green_phase(self):
        bundle, bundle_path, sha, size = self.bundle_for(mode="red")
        _path, updated, _kept = self.commit(bundle_path, sha, size)
        self.assertEqual(updated, ["review-count-reject"])
        entry = select.read_state()["cases"]["review-count-reject"]
        self.assertIn("red", entry)
        self.assertNotIn("green", entry, "red-only 运行不得写未运行的 green 证明")

    def test_local_cleanup_failure_keeps_the_phase_unverified(self):
        bundle, bundle_path, sha, size = self.bundle_for()
        self.mutate_receipt("review-count-reject", "green", local_cleanup="failed")
        report = self.phase_report(bundle)
        self.assertEqual(report["phases"]["green"]["unverified"], 1)
        self.assertEqual(report["phases"]["red"]["passed"], 1)
        path, updated, _kept = self.commit(bundle_path, sha, size)
        self.assertEqual(updated, [], "清理未确认的相位不得进入 proof")
        self.assertIsNone(path)
        self.assertFalse(Path(select.state_path()).exists(), "没有新证明就不创建状态文件")

    def test_explicit_keep_is_never_proof_eligible(self):
        bundle, bundle_path, sha, size = self.bundle_for()
        self.mutate_receipt("review-count-reject", "red", local_cleanup="retained-keep")
        report = self.phase_report(bundle)
        self.assertEqual(report["phases"]["red"]["unverified"], 1)
        _path, updated, _kept = self.commit(bundle_path, sha, size)
        self.assertEqual(updated, [])

    def test_mixed_phase_outcome_has_no_case_proof(self):
        # both 模式的部分通过：green 成立、red 断言失败 → 该 case 没有任何可复用证明。
        selection, path, sha, size = self.bundle("review-count-reject", "both")
        fingerprint = selection["cases"]["review-count-reject"]["execution_fingerprint"]
        record = json.loads(self.record("review-count-reject", "both", sha, fingerprint).read_text())
        record["red"] = "fail"
        record["verified"] = False
        (self.results / "review-count-reject.json").write_text(json.dumps(record))
        (self.results / "logs" / "review-count-reject.red.log").write_text(
            "FAIL red: target assertion still green\n")
        bundle = json.loads(path.read_bytes())
        bundle["__sha256"] = sha
        report = self.phase_report(bundle)
        self.assertEqual(report["phases"]["green"]["passed"], 1)
        self.assertEqual(report["phases"]["red"]["failed"], 1)
        _path, updated, _kept = self.commit(path, sha, size)
        self.assertEqual(updated, [], "部分通过的 case 不得留下半套证明")

    def test_missing_or_foreign_receipt_is_unverified(self):
        bundle, bundle_path, sha, size = self.bundle_for()
        self.receipt_path("review-count-reject", "green").unlink()
        report = self.phase_report(bundle)
        self.assertEqual(report["phases"]["green"]["unverified"], 1)
        self.mutate_receipt("review-count-reject", "red", run_id="another-run")
        report = self.phase_report(bundle)
        self.assertEqual(report["phases"]["red"]["unverified"], 1)
        _path, updated, _kept = self.commit(bundle_path, sha, size)
        self.assertEqual(updated, [])

    def test_state_write_failure_keeps_the_previous_bytes(self):
        state = Path(select.state_path())
        state.parent.mkdir(parents=True, exist_ok=True)
        state.write_text('{"schema_version": 5, "cases": {}}\n')
        before = state.read_bytes()
        with mock.patch.object(select.os, "replace", side_effect=OSError("disk full")):
            with self.assertRaises(select.SelectError) as caught:
                select.write_state({"schema_version": 5, "cases": {}})
        self.assertIn("previous state file is unchanged", str(caught.exception))
        self.assertEqual(state.read_bytes(), before)
        self.assertEqual(sorted(name for name in os.listdir(state.parent)
                                if name.startswith(".state-")), [],
                         "写入失败不得留下临时文件")

    def test_temp_file_or_fsync_failure_keeps_the_previous_bytes(self):
        state = Path(select.state_path())
        state.parent.mkdir(parents=True, exist_ok=True)
        state.write_text('{"schema_version": 5, "cases": {}}\n')
        before = state.read_bytes()
        with mock.patch.object(select.tempfile, "NamedTemporaryFile",
                               side_effect=OSError("no space")):
            with self.assertRaises(select.SelectError):
                select.write_state({"schema_version": 5, "cases": {}})
        self.assertEqual(state.read_bytes(), before)
        with mock.patch.object(select.os, "fsync", side_effect=OSError("io error")):
            with self.assertRaises(select.SelectError):
                select.write_state({"schema_version": 5, "cases": {}})
        self.assertEqual(state.read_bytes(), before)
        self.assertEqual(sorted(name for name in os.listdir(state.parent)
                                if name.startswith(".state-")), [])

    def test_v4_state_is_legacy_and_converts_only_on_a_successful_write(self):
        case = "review-count-reject"
        legacy = {"schema_version": 4,
                  "cases": {case: {"green": {"fingerprint": "old"},
                                   "red": {"subject": "old", "fingerprint": "old"}}}}
        Path(select.state_path()).parent.mkdir(parents=True, exist_ok=True)
        Path(select.state_path()).write_text(json.dumps(legacy))
        self.assertEqual(select.auto_modes(
            {case: {"red_subject_digest": "x", "local_inputs": {"targets": "t"}}},
            select.load_groups())[case], "both", "v4 证明不能直接命中 auto")
        # 升级写入必须由含 red 相位的合格证明触发；green-only 不读写共享 proof。
        state_before = Path(select.state_path()).read_bytes()
        bundle, bundle_path, sha, size = self.bundle_for(mode="green")
        path, updated, kept = self.commit(bundle_path, sha, size)
        self.assertEqual(updated, [], "green-only 不得写 proof")
        self.assertEqual(Path(select.state_path()).read_bytes(), state_before,
                         "green-only 不得改写共享状态字节")
        _, bundle_path, sha, size = self.bundle_for(mode="both")
        path, updated, kept = self.commit(bundle_path, sha, size)
        self.assertEqual(updated, [case])
        self.assertEqual(kept, [], "被重新验证的用例由本代证据替换，不再单列保留")
        stored = json.loads(Path(select.state_path()).read_text())
        self.assertEqual(stored["schema_version"], 5)
        self.assertIn("legacy", stored["cases"][case])
        self.assertEqual(stored["cases"][case]["green"]["cleanup"], "removed")

    def test_list_selection_needs_no_release_context(self):
        with mock.patch.object(select, "release_context",
                               side_effect=AssertionError("must not read")):
            listed = select.list_selection(["install"], "", "dev")
            self.assertEqual(listed["cases"]["install-lock-realpath"], "both")
            candidate = select.list_selection(["install"], "release-identity", "candidate")
            self.assertEqual(candidate["cases"]["release-identity-commit"], "green")


if __name__ == "__main__":
    unittest.main()
