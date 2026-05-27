#!/usr/bin/env python3
"""Compatibility wrapper for the workflow-phase strong-gate patch helper."""

from __future__ import annotations

import argparse
import importlib.util
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


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Apply the compatibility wrapper for the strong-gate workflow_phase patch."
    )
    parser.add_argument("target_path", help="Path to the target workflow_phase.py file")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    target_path = Path(args.target_path).resolve()
    return 0 if patch_workflow_phase(target_path) else 1


if __name__ == "__main__":
    raise SystemExit(main())
