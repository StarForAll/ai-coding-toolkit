"""Coverage accounting (AC17/AC18) and the candidate library resolver.

The table is generated from the *actual* registries (units.json + all_cases()) and each
row carries its kind/group/metadata state and a registered disposition.  The baseline
file pins the ID set: adding/removing/renaming an ID is reported as a difference instead
of being hidden by equal counts.
"""

import importlib.util
import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
FULL = HERE / "full"
REPRO = FULL / "repro"
REPO = HERE.parents[2]
sys.path.insert(0, str(FULL))
sys.path.insert(0, str(REPRO))
sys.path.insert(0, str(REPO / "scripts"))


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


coverage = _load("wf_source_coverage", FULL / "source_coverage.py")
library_source = _load("wf_library_source", FULL / "library_source.py")

UNGROUPED = {
    "d21-executor-set-move", "d21-executor-set-multi-clone", "d21-executor-set-purge-reconfirm",
    "d21-executor-set-venv-rebuild", "definition-static-check", "dep-edges",
    "enable-disabled-branch", "external-change-boundary", "f7-1-touch-paths",
    "f7-3-scope-single-source", "help-covers-write-commands", "history-anchor-unreachable",
    "record-missing-in-worktree", "run-advance-creates-task", "run-create-once", "run-finish",
    "run-pause-and-advance", "run-resume", "run-terminate", "skill-frontmatter-selfcheck",
    "snapshot-broken-type", "snapshot-empty-check", "snapshot-empty-stop", "snapshot-empty-write",
    "snapshot-missing-check", "snapshot-missing-stop", "snapshot-missing-write",
    "spec-three-part-index", "startup-checks-anchor-assets", "task-start-surface",
    "wf-repair-handoff",
}
CANDIDATE_CLEAN = {"branch-source-preview", "reinstall-preserves-data", "release-identity-commit"}


class CoverageTest(unittest.TestCase):
    def setUp(self):
        self.result = coverage.coverage()

    def test_registry_and_discovery_counts_match_the_baseline(self):
        counts = self.result["counts"]
        self.assertEqual(counts["units_total"], 67)
        self.assertEqual(counts["units_by_kind"],
                         {"candidate": 1, "extra": 1, "flow": 4, "manual": 2, "suite": 59})
        self.assertEqual(counts["repro_discovered"], 85)
        self.assertEqual(counts["repro_grouped"], 54)
        self.assertEqual(counts["repro_ungrouped"], 31)
        self.assertEqual(counts["repro_with_metadata"], 10)
        self.assertEqual(counts["repro_candidate_clean"], 3)
        self.assertEqual(counts["units_candidate_verified"], 57)
        self.assertEqual(counts["units_kept_dev_only"], 3)
        self.assertEqual(counts["units_pending_promotion"], 0)
        self.assertEqual(counts["units_not_tested"], 0)

    def test_every_id_is_accounted_and_ungrouped_ids_are_exact(self):
        rows = self.result["rows"]["repro"]
        self.assertEqual(set(rows), set(self.result["current"]["repro"]))
        self.assertEqual({name for name, row in rows.items() if not row["groups"]}, UNGROUPED)
        self.assertEqual({name for name, row in rows.items()
                          if row["candidate_clean"] == "true"}, CANDIDATE_CLEAN)
        for name, row in self.result["rows"]["units"].items():
            self.assertTrue(row["script_sha256"], f"{name} 缺少脚本摘要")
            self.assertIn(row["source_layer"],
                          ("author-source", "installed-fixture", "mixed", "unknown"))
            self.assertIsInstance(row["author_source_refs"], list)
            self.assertIsInstance(row["installed_refs"], list)
            self.assertIn(row["migration_status"],
                          ("candidate-verified", "kept-dev-only", "not-a-candidate-suite",
                           "manual", "declared-candidate-unverified"))
            if row["migration_status"] == "candidate-verified":
                self.assertEqual(row["can_run_installed"], "verified")
                self.assertIsNone(row["not_migratable_reason"])
            if row["migration_status"] == "kept-dev-only":
                self.assertTrue(row["not_migratable_reason"], f"{name} 缺少不可迁移理由")
                self.assertIn(row["can_run_installed"], ("failed", "not-applicable"))
                if row["can_run_installed"] == "failed":
                    self.assertTrue(row["not_migratable_reason"].startswith("candidate run failed"))
        self.assertEqual(len(self.result["rows"]["units"]), 67)

    def test_set_identity_is_checked_not_only_counts(self):
        differences = self.result["differences"]
        self.assertIsNotNone(differences)
        self.assertFalse(differences["changed"],
                         "当前集合/元数据与 coverage-baseline.json 不一致（新增/删除/改名需逐项登记）："
                         + json.dumps(differences, ensure_ascii=False))

    def test_metadata_declaration_is_preserved_verbatim(self):
        units = {row["kind"]: 0 for row in self.result["rows"]["units"].values()}
        for row in self.result["rows"]["units"].values():
            units[row["kind"]] += 1
        self.assertEqual(units["flow"], 4)
        # 4 个 flow 未声明 candidate_clean：不得改写成显式 false。
        flows = [row for row in self.result["rows"]["units"].values() if row["kind"] == "flow"]
        self.assertTrue(all(row["candidate_clean"] == "missing" for row in flows))
        explicit_false = [row for row in self.result["rows"]["units"].values()
                          if row["candidate_clean"] == "false"]
        # 审计后只有 3 个 suite 未通过 candidate 实跑，加上 extra 1 + manual 2。
        self.assertEqual(len(explicit_false), 6)
        for name in ("r67_tests", "r90_tests", "p5_v1"):
            self.assertEqual(self.result["rows"]["units"][name]["migration_status"],
                             "kept-dev-only")

    def test_candidate_eligible_repro_cases_have_targets_in_the_release_lib(self):
        # 候选合格用例的断言对象必须是安装产物（wf-release/lib），不能是作者 payload。
        release_lib = REPO / "docs" / "workflows" / "wf-release" / "wf-release" / "lib"
        self.assertTrue((release_lib / "wflib").is_dir())
        groups = json.loads((REPRO / "groups.json").read_text())
        for name in CANDIDATE_CLEAN:
            meta = (groups.get("cases") or {}).get(name) or {}
            self.assertEqual(meta.get("assertion_target"), "installed", name)
            self.assertEqual(meta.get("stage_role"), "scaffold", name)


class CandidateAuditTest(unittest.TestCase):
    def setUp(self):
        self.result = coverage.coverage()
        self.audit = json.loads((FULL / "candidate-audit.json").read_text())

    def test_audit_covers_every_suite_and_matches_current_script_bytes(self):
        suites = [name for name, row in self.result["rows"]["units"].items()
                  if row["kind"] == "suite"]
        self.assertEqual(len(self.audit["units"]), len(suites))
        for name in suites:
            record = self.audit["units"][name]
            self.assertEqual(record["script_sha256"],
                             self.result["rows"]["units"][name]["script_sha256"],
                             f"{name}: candidate audit 与当前脚本字节不一致")

    def test_every_suite_is_verified_or_has_a_concrete_candidate_failure(self):
        for name, row in self.result["rows"]["units"].items():
            if row["kind"] != "suite":
                continue
            self.assertIn(row["migration_status"], ("candidate-verified", "kept-dev-only"), name)
            if row["migration_status"] == "kept-dev-only":
                if "fake-tree" in (row.get("technical_note") or ""):
                    self.assertEqual(row["can_run_installed"], "not-applicable")
                    self.assertIn("fake-tree", row["not_migratable_reason"])
                else:
                    self.assertTrue(row["not_migratable_reason"].startswith("candidate run failed"))
                    self.assertTrue(row["installed_assertion"].startswith("none in candidate mode"))

    def test_failed_suites_have_concrete_assertion_evidence(self):
        for name in ("r90_tests", "p5_v1"):
            record = self.audit["units"][name]
            self.assertTrue(record["failures"], f"{name} 的 audit 必须有具体失败断言")
            row = self.result["rows"]["units"][name]
            self.assertIn(record["failures"][0], row["not_migratable_reason"])
        self.assertEqual(self.result["rows"]["units"]["r67_tests"]["can_run_installed"],
                         "not-applicable")
        self.assertIn("fake-tree", self.result["rows"]["units"]["r67_tests"]["not_migratable_reason"])

    def test_audit_version_and_tree_match_the_frozen_release(self):
        import wf_release_common as common
        release_root = REPO / "docs" / "workflows" / "wf-release"
        release = json.loads((release_root / "wf-release.json").read_text())
        self.assertEqual(self.audit["version"], release["version"])
        self.assertEqual(self.audit["candidate_tree_digest"], common.tree_digest(str(release_root)))


class LibraryResolverTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="wf-library-source-")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.fixture = self.root / "fixture"
        self.fixture.mkdir()

    def _install_lib(self):
        lib = self.fixture / ".wf" / "lib" / "wflib"
        lib.mkdir(parents=True)
        (lib / "__init__.py").write_text("")
        return lib.parent

    def test_installed_library_wins_in_both_deployments(self):
        lib = self._install_lib()
        for deploy in ("dev", "candidate"):
            with self.subTest(deploy=deploy):
                self.assertEqual(library_source.resolve(str(self.fixture), deploy, {}),
                                 (str(lib), "installed"))

    def test_candidate_never_falls_back_to_the_author_payload(self):
        with self.assertRaises(library_source.SourceError):
            library_source.resolve(str(self.fixture), "candidate", {})
        self.assertFalse(library_source.candidate_available(str(self.fixture), {}))

    def test_declared_input_is_used_and_missing_is_attributed(self):
        declared = self.root / "declared"
        (declared / "wflib").mkdir(parents=True)
        self.assertEqual(library_source.resolve(str(self.fixture), "candidate",
                                                 {"WF_TEST_LIB": str(declared)}),
                         (str(declared), "declared"))
        with self.assertRaises(library_source.SourceError):
            library_source.resolve(None, "candidate", {"WF_TEST_LIB": str(self.root / "nope")})

    def test_dev_falls_back_to_the_payload_with_an_explicit_label(self):
        path, label = library_source.resolve(str(self.fixture), "dev", {})
        self.assertEqual(label, "source")
        self.assertTrue(path.endswith("payload/lib"))


if __name__ == "__main__":
    unittest.main()
