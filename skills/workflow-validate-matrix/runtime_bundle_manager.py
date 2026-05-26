"""Runtime bundle helpers for workflow-validate-matrix."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from typing import Any


SKILL_DIR = Path(__file__).resolve().parent
BUNDLE_ROOT = SKILL_DIR / "runtime_bundle" / "workflow"
SOURCE_WORKFLOW_ROOT_REL = Path("docs/workflows/新项目开发工作流")
SYNC_SCRIPT_REL = Path("scripts/sync-workflow-validate-matrix-runtime.py")
SOURCE_REPO_ROOT_ENV = "WORKFLOW_SOURCE_REPO_ROOT"
GLOBAL_REINSTALL_COMMAND = "npx skills add . -g -y"


def _load_module(module_name: str, path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load module from: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def bundle_workflow_root() -> Path:
    if not BUNDLE_ROOT.is_dir():
        raise RuntimeError(
            f"Missing runtime bundle at {BUNDLE_ROOT}. "
            f"Run `/ops/softwares/python/bin/python3 {SYNC_SCRIPT_REL}` in the repo, then reinstall the global skill with `{GLOBAL_REINSTALL_COMMAND}`."
        )
    return BUNDLE_ROOT


def find_authoring_repo_root(start: Path | None = None) -> Path | None:
    source_root_override = None
    try:
        import os

        raw = os.environ.get(SOURCE_REPO_ROOT_ENV)
        if raw:
            source_root_override = Path(raw).expanduser().resolve()
    except Exception:
        source_root_override = None

    candidates: list[Path] = []
    if source_root_override is not None:
        candidates.append(source_root_override)
    if start is not None:
        candidates.append(start.resolve())
    candidates.append(Path.cwd().resolve())

    for candidate in candidates:
        current = candidate if candidate.is_dir() else candidate.parent
        while current != current.parent:
            if (
                (current / ".trellis").is_dir()
                and (current / SOURCE_WORKFLOW_ROOT_REL).is_dir()
                and (current / "skills" / "workflow-validate-matrix").is_dir()
            ):
                return current
            current = current.parent
    return None


def require_authoring_repo_root(start: Path | None = None) -> Path:
    repo_root = find_authoring_repo_root(start)
    if repo_root is None:
        raise RuntimeError(
            "workflow-validate-matrix must run from the workflow source repository so it can validate the current workflow product. "
            "Open the authoring repo root and retry."
        )
    return repo_root


def _source_workflow_assets_module(workflow_root: Path) -> Any:
    return _load_module(
        "workflow_validate_matrix_source_assets",
        workflow_root / "commands" / "workflow_assets.py",
    )


def _top_level_runtime_docs(workflow_root: Path) -> set[Path]:
    module = _source_workflow_assets_module(workflow_root)
    docs = {"工作流嵌入执行规范.md"}
    valid_profiles = getattr(module, "VALID_PROFILES", ("outsourcing", "personal"))
    managed_docs = getattr(module, "managed_workflow_docs_for_profile")
    for profile in valid_profiles:
        docs.update(managed_docs(profile))
    return {Path(name) for name in docs}


def iter_runtime_source_files(workflow_root: Path) -> list[Path]:
    """Return workflow-root-relative files that must be synced into the skill bundle."""
    relative_files: set[Path] = set()

    commands_root = workflow_root / "commands"
    for path in commands_root.rglob("*"):
        if not path.is_file():
            continue
        rel = path.relative_to(workflow_root)
        parts = rel.parts
        if any(part in {"__pycache__", ".pytest_cache"} for part in parts):
            continue
        if path.suffix == ".pyc" or path.name.startswith("test_"):
            continue
        relative_files.add(rel)

    relative_files.update(_top_level_runtime_docs(workflow_root))
    return sorted(relative_files)


def bundle_destination_for(relative_path: Path) -> Path:
    return bundle_workflow_root() / relative_path


def _is_ignored_bundle_artifact(relative_path: Path) -> bool:
    parts = relative_path.parts
    return relative_path.suffix == ".pyc" or any(part == "__pycache__" for part in parts)


def _digest(content: bytes) -> str:
    import hashlib

    return hashlib.sha256(content).hexdigest()


def compare_source_and_bundle(repo_root: Path) -> list[str]:
    workflow_root = repo_root / SOURCE_WORKFLOW_ROOT_REL
    bundle_root = BUNDLE_ROOT
    expected = iter_runtime_source_files(workflow_root)
    expected_set = set(expected)
    problems: list[str] = []

    if not bundle_root.is_dir():
        return [f"missing bundle root: {bundle_root}"]

    for relative_path in expected:
        source_path = workflow_root / relative_path
        bundle_path = bundle_root / relative_path
        if not bundle_path.is_file():
            problems.append(f"missing bundle file: {relative_path.as_posix()}")
            continue
        source_bytes = source_path.read_bytes()
        bundle_bytes = bundle_path.read_bytes()
        if _digest(source_bytes) != _digest(bundle_bytes):
            problems.append(f"content drift: {relative_path.as_posix()}")

    actual_bundle_files = {
        path.relative_to(bundle_root)
        for path in bundle_root.rglob("*")
        if path.is_file()
        and path.name != "runtime-bundle-manifest.json"
        and not _is_ignored_bundle_artifact(path.relative_to(bundle_root))
    }
    extras = sorted(actual_bundle_files - expected_set)
    for relative_path in extras:
        problems.append(f"extra bundle file: {relative_path.as_posix()}")

    return problems


def sync_instructions(repo_root: Path) -> str:
    sync_command = f"/ops/softwares/python/bin/python3 {repo_root / SYNC_SCRIPT_REL}"
    reinstall_command = f"cd {repo_root} && {GLOBAL_REINSTALL_COMMAND}"
    return (
        "Runtime bundle drift detected.\n"
        f"1. Sync the skill payload: `{sync_command}`\n"
        f"2. Reinstall the global skill: `{reinstall_command}`"
    )


def assert_bundle_in_sync_if_repo_available(start: Path | None = None) -> None:
    repo_root = find_authoring_repo_root(start)
    if repo_root is None:
        return
    problems = compare_source_and_bundle(repo_root)
    if not problems:
        return
    raise RuntimeError(
        sync_instructions(repo_root)
        + "\nDetected differences:\n- "
        + "\n- ".join(problems[:20])
    )


def workflow_version_and_schema() -> tuple[str, str]:
    assets_file = bundle_workflow_root() / "commands" / "workflow_assets.py"
    content = assets_file.read_text(encoding="utf-8")
    workflow_version = "unknown"
    schema_version = "unknown"
    for line in content.splitlines():
        stripped = line.strip()
        if stripped.startswith("WORKFLOW_VERSION = "):
            workflow_version = stripped.split("=", 1)[1].split("#", 1)[0].strip().strip('"').strip("'")
        elif stripped.startswith("WORKFLOW_SCHEMA_VERSION = "):
            schema_version = stripped.split("=", 1)[1].split("#", 1)[0].strip().strip('"').strip("'")
    return workflow_version, schema_version


def write_bundle_manifest(repo_root: Path) -> None:
    workflow_root = repo_root / SOURCE_WORKFLOW_ROOT_REL
    manifest_path = bundle_workflow_root() / "runtime-bundle-manifest.json"
    files = [path.as_posix() for path in iter_runtime_source_files(workflow_root)]
    manifest = {
        "source-workflow-root": SOURCE_WORKFLOW_ROOT_REL.as_posix(),
        "files": files,
    }
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
