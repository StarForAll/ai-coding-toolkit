#!/usr/bin/env python3
"""
Shared drift scanning helpers for imported trellis-library assets.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from _internal.asset_state import (
    is_managed_target_path,
    managed_target_path_error,
    sha256_for_path,
)


def scan_existing_imports(
    lock: dict[str, Any],
    library_root: Path,
    target_root: Path,
    exclude_ids: set[str],
    asset_map: dict[str, dict[str, Any]],
) -> list[dict[str, str]]:
    items: list[dict[str, str]] = []

    for imp in lock.get("imports", []):
        asset_id = imp.get("asset_id", "")
        if not asset_id or asset_id in exclude_ids:
            continue

        asset = asset_map.get(asset_id)
        if not asset:
            items.append(
                {
                    "asset_id": asset_id,
                    "drift_type": "upstream-and-local-changed",
                    "message": "Asset was removed from the manifest",
                }
            )
            continue

        target_path_str = imp.get("target_path", "")
        if not is_managed_target_path(target_path_str):
            items.append(
                {
                    "asset_id": asset_id,
                    "drift_type": "structural-conflict",
                    "message": managed_target_path_error(target_path_str),
                }
            )
            continue

        source_abs = library_root / asset["path"]
        current_source_checksum = sha256_for_path(source_abs)
        stored_source_checksum = imp.get("source_checksum", "")

        target_abs = target_root / target_path_str
        current_target_checksum = sha256_for_path(target_abs) if target_abs.exists() else ""
        stored_local_checksum = imp.get("last_local_checksum", "")

        source_changed = bool(stored_source_checksum) and current_source_checksum != stored_source_checksum
        target_changed = bool(stored_local_checksum) and current_target_checksum != stored_local_checksum

        if not source_changed and not target_changed:
            continue

        source_version = asset.get("version", "")
        stored_version = imp.get("source_version", "")

        if source_changed and target_changed:
            items.append(
                {
                    "asset_id": asset_id,
                    "drift_type": "upstream-and-local-changed",
                    "message": (
                        f"Upstream changed ({stored_version} -> {source_version}) and local content also changed. "
                        f"Recommendation: run assemble --asset {asset_id} separately to review the update"
                    ),
                }
            )
        elif source_changed:
            items.append(
                {
                    "asset_id": asset_id,
                    "drift_type": "upstream-changed",
                    "message": (
                        f"Upstream changed ({stored_version} -> {source_version}) while the local copy stayed unmodified. "
                        f"Recommendation: run assemble --asset {asset_id} separately to apply the update"
                    ),
                }
            )
        elif target_changed:
            items.append(
                {
                    "asset_id": asset_id,
                    "drift_type": "local-changed",
                    "message": "Local content changed while upstream stayed the same. Run diff/propose if you want to contribute upstream.",
                }
            )

    return items
