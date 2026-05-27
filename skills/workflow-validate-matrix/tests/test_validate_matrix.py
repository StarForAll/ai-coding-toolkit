#!/usr/bin/env python3
"""Unit tests for workflow-validate-matrix entrypoint helpers."""

from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parents[1]
if str(SKILL_DIR) not in sys.path:
    sys.path.insert(0, str(SKILL_DIR))

MODULE_PATH = SKILL_DIR / "validate-matrix.py"
SPEC = importlib.util.spec_from_file_location("workflow_validate_matrix_entry", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
vm = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(vm)


class ValidateMatrixTests(unittest.TestCase):
    def test_create_temp_dir_uses_timestamp_and_scenario(self) -> None:
        scenario = "clean-outsourcing-all-cli"
        timestamp = "20260526-123456-123456"

        temp_dir = vm.create_temp_dir(scenario, timestamp)
        self.addCleanup(lambda: temp_dir.parent.exists() and vm.cleanup_matrix_root(temp_dir.parent))

        self.assertTrue(temp_dir.exists())
        self.assertIn(timestamp, str(temp_dir))
        self.assertTrue(str(temp_dir).endswith(scenario))

    def test_cleanup_matrix_root_removes_nested_scenarios(self) -> None:
        with tempfile.TemporaryDirectory(prefix="wvm-matrix-root-") as tmp:
            matrix_root = Path(tmp) / "matrix"
            scenario_dir = matrix_root / "scenario"
            scenario_dir.mkdir(parents=True)
            (scenario_dir / "file.txt").write_text("fixture", encoding="utf-8")

            vm.cleanup_matrix_root(matrix_root)

            self.assertFalse(matrix_root.exists())


if __name__ == "__main__":
    raise SystemExit(unittest.main())
