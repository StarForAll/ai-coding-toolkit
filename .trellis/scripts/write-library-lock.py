#!/usr/bin/env python3
"""
Write .trellis/library-lock.yaml for a target project.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

LIBRARY_ROOT = Path(__file__).resolve().parents[2]
if str(LIBRARY_ROOT) not in sys.path:
    sys.path.insert(0, str(LIBRARY_ROOT))

from _internal.asset_state import sha256_for_path  # noqa: E402


COPYABLE_TYPES = {"spec", "template", "checklist"}


def iso_now() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def load_yaml(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise SystemExit(f"Expected YAML mapping in {path}")
    return data


def _type_matches(expected: str | list[str], value: Any) -> bool:
    types = expected if isinstance(expected, list) else [expected]
    mapping = {
        "object": dict,
        "array": list,
        "string": str,
        "integer": int,
        "boolean": bool,
        "null": type(None),
        "number": (int, float),
    }
    for item in types:
        py_type = mapping[item]
        if item == "integer" and isinstance(value, bool):
            continue
        if item == "number" and isinstance(value, bool):
            continue
        if isinstance(value, py_type):
            return True
    return False


def validate_against_schema(data: Any, schema: dict[str, Any], path: str = "$") -> list[str]:
    errors: list[str] = []
    expected_type = schema.get("type")
    if expected_type is not None and not _type_matches(expected_type, data):
        return [f"{path}: expected type {expected_type}, got {type(data).__name__}"]
    if "enum" in schema and data not in schema["enum"]:
        errors.append(f"{path}: value {data!r} not in enum {schema['enum']}")
    if isinstance(data, (int, float)) and not isinstance(data, bool) and "minimum" in schema:
        if data < schema["minimum"]:
            errors.append(f"{path}: value {data} below minimum {schema['minimum']}")
    if isinstance(data, str) and "minLength" in schema:
        if len(data) < schema["minLength"]:
            errors.append(f"{path}: string shorter than minLength {schema['minLength']}")
    if isinstance(data, dict):
        for key in schema.get("required", []):
            if key not in data:
                errors.append(f"{path}: missing required key '{key}'")
        for key, value in data.items():
            if key in schema.get("properties", {}):
                errors.extend(validate_against_schema(value, schema["properties"][key], f"{path}.{key}"))
    elif isinstance(data, list) and "items" in schema:
        for index, item in enumerate(data):
            errors.extend(validate_against_schema(item, schema["items"], f"{path}[{index}]"))
    return errors


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Write .trellis/library-lock.yaml")
    parser.add_argument("--library-root", default="trellis-library", help="Path to trellis-library root")
    parser.add_argument("--target", required=True, help="Target project root")
    parser.add_argument("--asset", action="append", default=[], help="Selected asset id (repeatable)")
    parser.add_argument("--pack", action="append", default=[], help="Selected pack id (repeatable)")
    parser.add_argument("--output", default=None, help="Optional explicit lock file path")
    parser.add_argument("--merge", action="store_true", help="Merge with existing lock instead of overwriting")
    return parser.parse_args()


def target_relative_path(asset: dict[str, Any]) -> Path:
    source_rel = Path(asset["path"])
    if asset["type"] == "spec":
        parts = list(source_rel.parts)
        if parts and parts[0] == "specs":
            parts[0] = "spec"
        return Path(*parts)
    return source_rel


def should_auto_include_dependency(asset: dict[str, Any]) -> bool:
    return asset["type"] in COPYABLE_TYPES


def expand_selected_asset_ids(
    asset_map: dict[str, dict[str, Any]],
    pack_map: dict[str, dict[str, Any]],
    selected_asset_ids: list[str],
    selected_pack_ids: list[str],
) -> list[str]:
    explicit_ids = list(dict.fromkeys(selected_asset_ids))
    ordered: list[str] = []
    seen: set[str] = set()

    def add_asset(asset_id: str, is_dependency: bool = False) -> None:
        if asset_id in seen:
            return
        asset = asset_map.get(asset_id)
        if not asset:
            raise SystemExit(f"Unknown asset id: {asset_id}")
        if is_dependency and not should_auto_include_dependency(asset):
            return
        for dependency in asset.get("dependencies", []) or []:
            add_asset(dependency, is_dependency=True)
        seen.add(asset_id)
        ordered.append(asset_id)

    for pack_id in selected_pack_ids:
        pack = pack_map.get(pack_id)
        if not pack:
            raise SystemExit(f"Unknown pack id: {pack_id}")
        for asset_id in pack.get("selection", {}).get("assets", []):
            add_asset(asset_id)

    for asset_id in explicit_ids:
        add_asset(asset_id)

    return ordered


def merge_locks(existing: dict[str, Any], new: dict[str, Any]) -> dict[str, Any]:
    """Merge new lock data into existing lock. Existing data takes priority for preserved fields."""
    merged = dict(new)

    # Preserve original library.imported_at
    merged["library"]["imported_at"] = existing.get("library", {}).get("imported_at", new["library"]["imported_at"])

    # Update library.source_path to current (handles library migration)
    # source_path, manifest_version, manifest_checksum always reflect current state
    # (these are updated from new lock which uses current library_root)

    # Merge selection (union)
    existing_packs = set(existing.get("selection", {}).get("packs", []))
    existing_assets = set(existing.get("selection", {}).get("assets", []))
    new_packs = set(new.get("selection", {}).get("packs", []))
    new_assets = set(new.get("selection", {}).get("assets", []))
    merged["selection"]["packs"] = sorted(existing_packs | new_packs)
    merged["selection"]["assets"] = sorted(existing_assets | new_assets)

    # Merge imports (by asset_id: existing entries preserved, new entries added, updated entries refreshed)
    existing_imports = {
        imp["asset_id"]: dict(imp)
        for imp in existing.get("imports", [])
        if isinstance(imp, dict) and "asset_id" in imp
    }
    for imp in new.get("imports", []):
        asset_id = imp.get("asset_id")
        if not asset_id:
            continue
        if asset_id in existing_imports:
            # Update existing entry with new checksums/version, preserve other fields
            existing_imports[asset_id]["source_version"] = imp.get("source_version", existing_imports[asset_id].get("source_version", ""))
            existing_imports[asset_id]["source_checksum"] = imp.get("source_checksum", existing_imports[asset_id].get("source_checksum", ""))
            existing_imports[asset_id]["last_local_checksum"] = imp.get("last_local_checksum", existing_imports[asset_id].get("last_local_checksum", ""))
            existing_imports[asset_id]["local_state"] = imp.get("local_state", existing_imports[asset_id].get("local_state", "clean"))
            existing_imports[asset_id]["last_local_scan_at"] = imp.get("last_local_scan_at", existing_imports[asset_id].get("last_local_scan_at"))
            existing_imports[asset_id]["last_observed_checksum"] = imp.get(
                "last_observed_checksum",
                existing_imports[asset_id].get("last_observed_checksum", ""),
            )
            existing_imports[asset_id]["last_blocked_at"] = imp.get(
                "last_blocked_at",
                existing_imports[asset_id].get("last_blocked_at"),
            )
            existing_imports[asset_id]["blocked_count"] = imp.get(
                "blocked_count",
                existing_imports[asset_id].get("blocked_count", 0),
            )
        else:
            existing_imports[asset_id] = imp
    merged["imports"] = list(existing_imports.values())

    # Preserve history
    merged["history"] = existing.get("history", []) + new.get("history", [])

    # Preserve sync state
    merged["sync"] = existing.get("sync", new["sync"])

    # Preserve compiled state
    merged["compiled"] = existing.get("compiled", new["compiled"])

    return merged


def build_fresh_lock(
    manifest: dict[str, Any],
    library_root: Path,
    target_root: Path,
    asset_map: dict[str, dict[str, Any]],
    selected_asset_ids: list[str],
    selected_pack_ids: list[str],
) -> dict[str, Any]:
    """Build a fresh lock from scratch."""
    manifest_path = library_root / "manifest.yaml"

    imports: list[dict[str, Any]] = []
    for asset_id in selected_asset_ids:
        asset = asset_map.get(asset_id)
        if not asset:
            raise SystemExit(f"Unknown asset id: {asset_id}")

        source_rel = asset["path"]
        source_path = library_root / source_rel

        if asset["type"] in {"spec", "template", "checklist"}:
            target_path = target_root / ".trellis" / target_relative_path(asset)
        else:
            target_path = target_root / ".trellis" / "library-assets" / source_rel

        imports.append(
            {
                "asset_id": asset_id,
                "type": asset["type"],
                "source_path": source_rel,
                "target_path": str(target_path.relative_to(target_root).as_posix()),
                "import_mode": asset["format"],
                "source_version": asset.get("version", ""),
                "source_checksum": sha256_for_path(source_path) if source_path.exists() else "",
                "imported_at": iso_now(),
                "upstream_sync": "follow-upstream",
                "local_state": "clean",
                "last_local_scan_at": None,
                "last_local_checksum": sha256_for_path(target_path) if target_path.exists() else "",
                "last_observed_checksum": sha256_for_path(target_path) if target_path.exists() else "",
                "last_blocked_at": None,
                "blocked_count": 0,
                "contribution": {
                    "eligible": asset["type"] == "spec",
                    "mode": "selective" if asset["type"] == "spec" else "none",
                    "reviewed": False,
                    "proposed": False,
                    "last_proposed_at": None,
                },
                "relations": {
                    "depends_on": asset.get("dependencies", []),
                    "sync_targets": asset.get("change_impact", {}).get("sync_targets", []),
                },
                "notes": "",
            }
        )

    return {
        "version": 1,
        "library": {
            "id": manifest.get("library", {}).get("id", "trellis-library"),
            "source": "local",
            "source_path": str(library_root),
            "manifest_version": manifest.get("version", 1),
            "manifest_checksum": sha256_for_path(manifest_path),
            "imported_at": iso_now(),
        },
        "project": {
            "target_root": str(target_root),
            "trellis_root": str((target_root / ".trellis").resolve()),
        },
        "selection": {
            "packs": selected_pack_ids,
            "assets": selected_asset_ids,
        },
        "imports": imports,
        "compiled": {
            "enabled": False,
            "last_built_at": None,
            "outputs": [],
        },
        "sync": {
            "last_sync_at": None,
            "last_sync_status": "never",
            "last_diff_at": None,
            "last_diff_status": "never",
            "local_overrides": [],
        },
        "history": [],
    }


def main() -> int:
    args = parse_args()
    library_root = Path(args.library_root).resolve()
    target_root = Path(args.target).resolve()
    manifest_path = library_root / "manifest.yaml"
    manifest = load_yaml(manifest_path)

    assets = manifest.get("assets", [])
    asset_map = {asset["id"]: asset for asset in assets if isinstance(asset, dict) and "id" in asset}
    pack_map = {pack["id"]: pack for pack in manifest.get("packs", []) if isinstance(pack, dict) and "id" in pack}

    selected_asset_ids = list(dict.fromkeys(args.asset))
    selected_pack_ids = list(dict.fromkeys(args.pack))
    selected_asset_ids = expand_selected_asset_ids(
        asset_map,
        pack_map,
        selected_asset_ids,
        selected_pack_ids,
    )

    output = Path(args.output).resolve() if args.output else (target_root / ".trellis" / "library-lock.yaml")
    schema_path = library_root / "schemas" / "initialization" / "library-lock.schema.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))

    # Build new lock data
    new_lock = build_fresh_lock(
        manifest, library_root, target_root,
        asset_map, selected_asset_ids, selected_pack_ids,
    )

    # Merge mode: load existing lock and merge
    if args.merge and output.exists():
        try:
            existing_lock = load_yaml(output)
        except yaml.YAMLError as exc:
            raise SystemExit(f"Error: existing library-lock.yaml is corrupted: {exc}")
        lock = merge_locks(existing_lock, new_lock)
    else:
        lock = new_lock

    errors = validate_against_schema(lock, schema)
    if errors:
        raise SystemExit("Generated library-lock.yaml does not satisfy schema:\n" + "\n".join(errors))

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(yaml.safe_dump(lock, sort_keys=False, allow_unicode=True), encoding="utf-8")
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
