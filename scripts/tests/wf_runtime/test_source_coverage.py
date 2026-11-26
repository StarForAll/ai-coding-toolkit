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
    "record-missing-in-worktree", "run-create-once", "run-finish",
    "run-pause-and-advance", "run-resume", "run-terminate", "skill-frontmatter-selfcheck",
    "snapshot-broken-type", "snapshot-empty-check", "snapshot-empty-stop", "snapshot-empty-write",
    "snapshot-missing-check", "snapshot-missing-stop", "snapshot-missing-write",
    "spec-three-part-index", "startup-checks-anchor-assets", "task-start-surface",
    "wf-repair-handoff",
}
CANDIDATE_CLEAN = {"branch-source-preview", "reinstall-preserves-data", "release-identity-commit"}

# 脚本字节已改、但候选审计无法在本机重跑的单元（显式登记，不伪造审计摘要）。
# 登记条件：① 改动来自本轮框架修正且必须改该脚本；② 本机候选模式证据不成立
# （`candidate_audit.py` 全量运行被 r72/r86/r87 与安装收据拒发）；③ 发行批次必须重跑审计。
DECLARED_UNVERIFIED = {
    "r17r24_tests": "六轮复核 a.5 改 R22 的红绿证据形状（跨验证项拼凑必须被拒）；"
                    "候选审计需在发行批次重跑，本机候选模式证据不成立，按 declared-candidate-unverified 登记",
    "r62_tests": "六轮复核 a.6：调查成果改由已批准验收项承载（复盘不再单独满足，解除 before_check 自循环）；"
                 "同上，候选审计待发行批次重跑",
    "r65_tests": "同上（R6 调查成果口径随 a.6 同批改写）；候选审计待发行批次重跑",
    "r71_tests": "二轮外部审查 B2：审查的正当不通过改用 `WF_REVIEW_FAILED`，该套件的 fail 断言随之改写；"
                 "同上，候选审计待发行批次重跑",
}


class CoverageTest(unittest.TestCase):
    def setUp(self):
        self.result = coverage.coverage()

    def test_registry_and_discovery_counts_match_the_baseline(self):
        counts = self.result["counts"]
        self.assertEqual(counts["units_total"], 67)
        self.assertEqual(counts["units_by_kind"],
                         {"candidate": 1, "extra": 1, "flow": 4, "manual": 2, "suite": 59})
        self.assertEqual(counts["repro_discovered"], 91)
        self.assertEqual(counts["repro_grouped"], 61)
        self.assertEqual(counts["repro_ungrouped"], 30)
        self.assertEqual(counts["repro_with_metadata"], 7)
        self.assertEqual(counts["repro_candidate_clean"], 3)
        self.assertEqual(counts["units_candidate_verified"], 64 - len(DECLARED_UNVERIFIED))
        self.assertEqual(counts["units_kept_dev_only"], 1)
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
        # 每个 flow 都按候选资格显式声明：代表链保留，未取证的显式 false。
        flows = {name: row for name, row in self.result["rows"]["units"].items()
                 if row["kind"] == "flow"}
        self.assertEqual({name for name, row in flows.items()
                          if row["candidate_clean"] == "true"},
                         {"f0", "p5_spec", "p5_v2v3", "p5_v5"})
        explicit_false = [row for row in self.result["rows"]["units"].values()
                          if row["candidate_clean"] == "false"]
        # r72（dev-only）+ manual 2；r90/p5_v1 已按候选实跑提升（2026-11-23）
        self.assertEqual(len(explicit_false), 3)
        self.assertEqual(self.result["rows"]["units"]["r72_tests"]["migration_status"],
                         "kept-dev-only")
        for name in ("r90_tests", "p5_v1"):
            self.assertEqual(self.result["rows"]["units"][name]["migration_status"],
                             "candidate-verified")
        r72 = self.result["rows"]["units"]["r72_tests"]
        self.assertIn("candidate audit status=ok", r72["not_migratable_reason"],
                      "dev-only 的实际来源证据必须可追溯")
        self.assertIn("源码安装器", r72["technical_note"] or "")

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

    def test_audit_covers_every_plannable_unit_and_matches_script_bytes(self):
        plannable = {name for name, row in self.result["rows"]["units"].items()
                     if row["kind"] in ("suite", "candidate", "flow", "extra")}
        self.assertEqual(set(self.audit["units"]), plannable,
                         "审计必须覆盖全部可计划单元（含 dev-only 的实际来源证据）")
        eligible = {name for name, row in self.result["rows"]["units"].items()
                    if row["candidate_clean"] == "true"}
        identity = self.audit["identity"]
        for name in sorted(eligible):
            if name in DECLARED_UNVERIFIED:
                continue           # 见 DECLARED_UNVERIFIED：待发行批次重跑审计
            record = self.audit["units"][name]
            self.assertEqual(record["script_sha256"],
                             self.result["rows"]["units"][name]["script_sha256"],
                             f"{name}: candidate audit 与当前脚本字节不一致")
            self.assertEqual(record["status"], "ok", f"{name}: 合格单元审计必须为 ok")
            self.assertEqual(record["installation"]["source_commit"],
                             identity["candidate_commit"],
                             f"{name}: 合格单元必须由本候选实际安装")
            self.assertEqual(record["installation"]["version"], identity["version"])

    def test_every_suite_is_verified_or_has_a_concrete_candidate_failure(self):
        for name, row in self.result["rows"]["units"].items():
            if row["kind"] != "suite":
                continue
            if name in DECLARED_UNVERIFIED:
                self.assertEqual(row["migration_status"], "declared-candidate-unverified", name)
                continue
            self.assertIn(row["migration_status"], ("candidate-verified", "kept-dev-only"), name)
            if row["migration_status"] == "kept-dev-only":
                self.assertTrue(row["not_migratable_reason"].startswith("candidate run failed"))
                self.assertTrue(row["installed_assertion"].startswith("none in candidate mode"))

    def test_failed_suites_have_concrete_assertion_evidence(self):
        """审计里状态为 bad 的单元，其失败断言必须被逐条登记且能在覆盖行里追溯。

        r90/p5_v1 曾以具体失败断言留在 dev-only；2026-11-23 修掉来源判定后经候选实跑通过，
        因此本断言改为**按实际状态**过滤（没有 bad 单元时自然成立，不写死名单）。
        """
        bad = {name: record for name, record in (self.audit.get("units") or {}).items()
               if record.get("status") == "bad"}
        for name, record in bad.items():
            self.assertTrue(record["failures"], f"{name} 的 audit 必须有具体失败断言")
            row = self.result["rows"]["units"][name]
            self.assertIn(record["failures"][0], row["not_migratable_reason"])
        # 运行器假树断言迁出后，R67 只剩产品侧断言并已通过候选实跑。
        r67 = self.result["rows"]["units"]["r67_tests"]
        self.assertEqual(r67["migration_status"], "candidate-verified")
        self.assertEqual(self.audit["units"]["r67_tests"]["status"], "ok")

    def test_audit_version_and_tree_match_the_frozen_release(self):
        import wf_release_common as common
        release_root = REPO / "docs" / "workflows" / "wf-release"
        release = json.loads((release_root / "wf-release.json").read_text())
        identity = self.audit["identity"]
        if identity["version"] != release["version"]:
            self.skipTest(f"candidate audit is frozen for {identity['version']}; "
                          f"release is now {release['version']} and needs a new candidate run")
        self.assertEqual(identity["version"], release["version"])
        self.assertEqual(identity["candidate_tree_digest"], common.tree_digest(str(release_root)))
        self.assertEqual(identity["source_tree_digest"], common.tree_digest(str(release_root)))
        self.assertEqual(identity["candidate_commit"], self.audit["units"]["cp1_tests"]
                         ["installation"]["source_commit"])
        self.assertEqual(self.audit["units"]["cp1_tests"]["installation"]["version"],
                         release["version"])


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
