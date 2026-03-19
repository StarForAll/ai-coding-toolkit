#!/usr/bin/env python3
"""
Shared checksum and asset-state helpers for trellis-library sync workflows.
"""

from __future__ import annotations

import hashlib
from pathlib import Path


KEY_FILES = {
    "overview.md",
    "scope-boundary.md",
    "normative-rules.md",
    "verification.md",
}

DEFAULT_PRIVATE_HINTS = {
    ".trellis/",
    "src/",
    "apps/",
    "packages/",
    "customer",
    "internal-only",
    "project-specific",
}

MANAGED_ROOT = ".trellis"


def sha256_for_path(path: Path) -> str:
    digest = hashlib.sha256()
    if not path.exists():
        return ""
    if path.is_file():
        digest.update(path.read_bytes())
        return digest.hexdigest()

    entries: list[tuple[str, Path]] = [
        (child.relative_to(path).as_posix(), child)
        for child in path.rglob("*")
        if child.is_file()
    ]
    for relative_path, child in sorted(entries, key=lambda item: item[0]):
        digest.update(relative_path.encode("utf-8"))
        digest.update(b"\0")
        digest.update(hashlib.sha256(child.read_bytes()).digest())
    return digest.hexdigest()


def relative_file_set(path: Path) -> set[str]:
    if not path.exists():
        return set()
    if path.is_file():
        return {path.name}
    return {
        child.relative_to(path).as_posix()
        for child in path.rglob("*")
        if child.is_file()
    }


def is_managed_target_path(target_path: str | Path) -> bool:
    path = Path(target_path)
    return not path.is_absolute() and path.parts[:1] == (MANAGED_ROOT,)


def managed_target_path_error(target_path: str | Path) -> str:
    return (
        f"Target path '{target_path}' escapes managed {MANAGED_ROOT}/ tree; "
        "manual migration review required"
    )


def path_contains_hints(
    path: Path,
    hints: set[str] | None = None,
    suffixes: set[str] | None = None,
) -> bool:
    if not path.exists():
        return False
    allowed_hints = hints or DEFAULT_PRIVATE_HINTS
    files = [path] if path.is_file() else [child for child in path.rglob("*") if child.is_file()]
    for file in files:
        if suffixes is not None and file.suffix not in suffixes:
            continue
        try:
            content = file.read_text(encoding="utf-8")
        except OSError:
            continue
        lowered = content.lower()
        if any(hint in lowered for hint in allowed_hints):
            return True
    return False


def determine_change_scope(source_path: Path, target_path: Path) -> str:
    if not source_path.exists() or not target_path.exists():
        return "structure-change"
    if source_path.is_file() != target_path.is_file():
        return "structure-change"

    if source_path.is_file():
        return "content-change" if sha256_for_path(source_path) != sha256_for_path(target_path) else "none"

    if relative_file_set(source_path) != relative_file_set(target_path):
        return "structure-change"
    return "content-change" if sha256_for_path(source_path) != sha256_for_path(target_path) else "none"


def determine_diff_status(source_path: Path, target_path: Path) -> tuple[str, str]:
    if not target_path.exists():
        return "missing", "structure-change"
    if not source_path.exists():
        return "migration-required", "structure-change"
    if source_path.is_file() != target_path.is_file():
        return "diverged", "structure-change"

    change_scope = determine_change_scope(source_path, target_path)
    if change_scope == "none":
        return "unchanged", "none"

    if source_path.is_dir():
        source_files = relative_file_set(source_path)
        target_files = relative_file_set(target_path)
        if KEY_FILES - target_files:
            return "diverged", "structure-change"
        if source_files != target_files:
            return "diverged", "structure-change"

    return "modified", "content-change" if change_scope == "content-change" else change_scope


def determine_contribution_eligibility(
    asset: dict[str, object],
    diff_status: str,
    change_scope: str,
    target_path: Path,
) -> tuple[bool, str, str]:
    if diff_status == "unchanged":
        return False, "no-local-diff", "keep-local-and-follow-upstream"
    if diff_status == "missing":
        return False, "asset-missing-locally", "restore-from-upstream"
    if diff_status == "migration-required":
        return False, "source-asset-missing-or-renamed", "migration-required"
    if diff_status == "diverged":
        return False, "asset-boundary-or-structure-changed", "manual-review-required"
    if change_scope == "structure-change":
        return False, "structure-change-not-eligible", "manual-review-required"
    if asset.get("type") != "spec":
        return False, "only-spec-assets-are-upstream-eligible-by-default", "keep-local-and-pin"
    if path_contains_hints(target_path, suffixes={".md"}):
        return False, "project-private-content-detected", "keep-local-and-pin"
    return True, "generalizable-content-change", "propose-upstream-selective"


def determine_local_state(
    import_item: dict[str, object],
    target_abs: Path,
    source_abs: Path | None = None,
) -> str:
    expected_mode = import_item.get("import_mode")
    if not target_abs.exists():
        return "missing"
    if expected_mode == "file" and not target_abs.is_file():
        return "diverged"
    if expected_mode == "directory" and not target_abs.is_dir():
        return "diverged"

    if source_abs is not None and source_abs.exists():
        diff_status, _ = determine_diff_status(source_abs, target_abs)
        if diff_status == "diverged":
            return "diverged"

    current_checksum = sha256_for_path(target_abs)
    last_local_checksum = str(import_item.get("last_local_checksum", ""))
    if last_local_checksum and current_checksum != last_local_checksum:
        return "modified"
    return "clean"
