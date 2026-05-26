#!/usr/bin/env python3
"""Unit tests for workflow-validate-matrix runtime bundle helpers."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

SKILL_DIR = Path(__file__).resolve().parents[1]
if str(SKILL_DIR) not in sys.path:
    sys.path.insert(0, str(SKILL_DIR))

import runtime_bundle_manager as rbm


class RuntimeBundleManagerTests(unittest.TestCase):
    def test_workflow_version_and_schema_reads_bundle_assets(self) -> None:
        workflow_version, workflow_schema_version = rbm.workflow_version_and_schema()

        self.assertEqual(workflow_version, "0.1.28")
        self.assertEqual(workflow_schema_version, "3")

    def test_assert_bundle_in_sync_raises_with_sync_and_reinstall_instructions(self) -> None:
        fake_root = Path("/tmp/fake-workflow-repo")
        with patch.object(rbm, "find_authoring_repo_root", return_value=fake_root), patch.object(
            rbm,
            "compare_source_and_bundle",
            return_value=["content drift: commands/install-workflow.py"],
        ):
            with self.assertRaisesRegex(RuntimeError, "sync-workflow-validate-matrix-runtime.py"):
                rbm.assert_bundle_in_sync_if_repo_available()

    def test_find_authoring_repo_root_resolves_current_repo(self) -> None:
        repo_root = rbm.find_authoring_repo_root(Path.cwd())

        self.assertIsNotNone(repo_root)
        self.assertTrue((repo_root / "skills" / "workflow-validate-matrix").is_dir())
        self.assertTrue((repo_root / "docs" / "workflows" / "新项目开发工作流").is_dir())


if __name__ == "__main__":
    raise SystemExit(unittest.main())
