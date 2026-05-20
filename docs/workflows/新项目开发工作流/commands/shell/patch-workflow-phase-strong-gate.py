#!/usr/bin/env python3
"""Compatibility wrapper for the workflow-phase strong-gate patch helper."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


def _load_legacy_module():
    module_path = Path(__file__).resolve().with_name("patch-workflow-phase.py")
    spec = importlib.util.spec_from_file_location("patch_workflow_phase_legacy", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"无法加载 {module_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def patch_workflow_phase(target_path: Path) -> bool:
    module = _load_legacy_module()
    return bool(module.patch_workflow_phase(target_path))


def main() -> int:
    if len(sys.argv) < 2:
        print("用法: patch-workflow-phase-strong-gate.py <target_workflow_phase.py_path>")
        return 1

    target_path = Path(sys.argv[1]).resolve()
    return 0 if patch_workflow_phase(target_path) else 1


if __name__ == "__main__":
    raise SystemExit(main())
