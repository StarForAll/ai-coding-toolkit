#!/usr/bin/env python3
"""Tests for project_id_utils.py."""

from __future__ import annotations

import importlib.util
import json
import shutil
import tempfile
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parent / "project_id_utils.py"
SPEC = importlib.util.spec_from_file_location("project_id_utils_module", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
PROJECT_ID_UTILS = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PROJECT_ID_UTILS)


class ProjectIdUtilsTests(unittest.TestCase):
    def make_root(self) -> Path:
        root = Path(tempfile.mkdtemp(prefix="project-id-utils-"))
        self.addCleanup(shutil.rmtree, root, True)
        return root

    def test_find_repo_root_returns_none_when_trellis_missing(self) -> None:
        root = self.make_root()
        child = root / "nested" / "dir"
        child.mkdir(parents=True)
        self.assertIsNone(PROJECT_ID_UTILS.find_repo_root(child))

    def test_find_repo_root_returns_repo_when_trellis_exists(self) -> None:
        root = self.make_root()
        (root / ".trellis").mkdir()
        child = root / "nested" / "dir"
        child.mkdir(parents=True)
        self.assertEqual(PROJECT_ID_UTILS.find_repo_root(child), root)

    def test_normalize_project_id_accepts_single_letter(self) -> None:
        self.assertEqual(PROJECT_ID_UTILS.normalize_project_id("A"), "A")

    def test_normalize_project_id_accepts_trimmed_single_letter(self) -> None:
        self.assertEqual(PROJECT_ID_UTILS.normalize_project_id(" A "), "A")

    def test_normalize_project_id_accepts_colon_in_middle(self) -> None:
        self.assertEqual(PROJECT_ID_UTILS.normalize_project_id("a:b"), "a:b")

    def test_normalize_project_id_rejects_whitespace(self) -> None:
        self.assertIsNone(PROJECT_ID_UTILS.normalize_project_id("a b"))

    def test_normalize_project_id_rejects_digit_at_end(self) -> None:
        self.assertIsNone(PROJECT_ID_UTILS.normalize_project_id("ab1"))

    def test_workflow_install_record_exists_handles_none_repo_root(self) -> None:
        self.assertFalse(PROJECT_ID_UTILS.workflow_install_record_exists(None))

    def test_installed_workflow_project_id_returns_none_for_legacy_sentinel(self) -> None:
        root = self.make_root()
        (root / ".trellis").mkdir()
        (root / ".trellis" / "workflow-installed.json").write_text(
            json.dumps({"project_id": "_legacy_unknown_"}, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        self.assertIsNone(PROJECT_ID_UTILS.installed_workflow_project_id(root))

    def test_require_installed_project_id_reports_legacy_recovery_hint(self) -> None:
        root = self.make_root()
        (root / ".trellis").mkdir()
        (root / ".trellis" / "workflow-installed.json").write_text(
            json.dumps({"project_id": "_legacy_unknown_"}, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        with self.assertRaisesRegex(RuntimeError, "旧项目升级后的记录"):
            PROJECT_ID_UTILS.require_installed_project_id(root, "test-op")


if __name__ == "__main__":
    unittest.main()
