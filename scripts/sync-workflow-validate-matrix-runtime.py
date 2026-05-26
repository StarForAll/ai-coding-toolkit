#!/ops/softwares/python/bin/python3
"""Sync workflow-validate-matrix runtime bundle from workflow source assets."""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SKILL_DIR = PROJECT_ROOT / "skills" / "workflow-validate-matrix"

import sys

if str(SKILL_DIR) not in sys.path:
    sys.path.insert(0, str(SKILL_DIR))

from runtime_bundle_manager import (  # noqa: E402
    BUNDLE_ROOT,
    SOURCE_WORKFLOW_ROOT_REL,
    compare_source_and_bundle,
    iter_runtime_source_files,
    write_bundle_manifest,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Sync workflow-validate-matrix runtime bundle into skills/workflow-validate-matrix/runtime_bundle/workflow"
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Only check for drift; do not write files",
    )
    return parser


def _expected_bundle_files(repo_root: Path) -> list[Path]:
    workflow_root = repo_root / SOURCE_WORKFLOW_ROOT_REL
    return [workflow_root / relative_path for relative_path in iter_runtime_source_files(workflow_root)]


def sync_bundle(repo_root: Path) -> None:
    workflow_root = repo_root / SOURCE_WORKFLOW_ROOT_REL
    expected_rel_paths = iter_runtime_source_files(workflow_root)
    expected_set = set(expected_rel_paths)

    BUNDLE_ROOT.mkdir(parents=True, exist_ok=True)
    for relative_path in expected_rel_paths:
        source_path = workflow_root / relative_path
        dest_path = BUNDLE_ROOT / relative_path
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_path, dest_path)

    for existing in list(BUNDLE_ROOT.rglob("*")):
        if not existing.is_file():
            continue
        rel = existing.relative_to(BUNDLE_ROOT)
        if rel == Path("runtime-bundle-manifest.json"):
            continue
        if rel not in expected_set:
            existing.unlink()

    # Remove empty directories left by deleted files.
    for directory in sorted((path for path in BUNDLE_ROOT.rglob("*") if path.is_dir()), reverse=True):
        try:
            directory.rmdir()
        except OSError:
            pass

    write_bundle_manifest(repo_root)


def main() -> int:
    args = build_parser().parse_args()
    repo_root = PROJECT_ROOT

    if args.check:
        problems = compare_source_and_bundle(repo_root)
        if problems:
            print("ERROR: workflow-validate-matrix runtime bundle drift detected")
            for problem in problems:
                print(f"- {problem}")
            print(
                "Run `/ops/softwares/python/bin/python3 scripts/sync-workflow-validate-matrix-runtime.py` "
                "and then reinstall the global skill with `npx skills add . -g -y`."
            )
            return 1
        print("OK: workflow-validate-matrix runtime bundle is in sync")
        return 0

    sync_bundle(repo_root)
    print(f"Synced runtime bundle to {BUNDLE_ROOT}")
    print("Next: reinstall the global skill with `npx skills add . -g -y` if you use the global install.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
