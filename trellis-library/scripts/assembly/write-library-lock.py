#!/usr/bin/env python3
"""
Write .trellis/library-lock.yaml for a target project.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml


def iso_now() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def sha256_for_path(path: Path) -> str:
    digest = hashlib.sha256()
    if path.is_file():
        digest.update(path.read_bytes())
        return digest.hexdigest()

    for child in sorted(p for p in path.rglob("*") if p.is_file()):
        digest.update(str(child.relative_to(path)).encode("utf-8"))
        digest.update(child.read_bytes())
    return digest.hexdigest()


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
    return parser.parse_args()


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

    for pack_id in selected_pack_ids:
        pack = pack_map.get(pack_id)
        if not pack:
            raise SystemExit(f"Unknown pack id: {pack_id}")
        selected_asset_ids.extend(pack.get("selection", {}).get("assets", []))
    selected_asset_ids = list(dict.fromkeys(selected_asset_ids))

    imports: list[dict[str, Any]] = []
    for asset_id in selected_asset_ids:
        asset = asset_map.get(asset_id)
        if not asset:
            raise SystemExit(f"Unknown asset id: {asset_id}")

        source_rel = asset["path"]
        source_path = library_root / source_rel

        if asset["type"] in {"spec", "template", "checklist"}:
            target_path = target_root / ".trellis" / source_rel
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

    lock = {
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

    schema_path = library_root / "schemas" / "initialization" / "library-lock.schema.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    errors = validate_against_schema(lock, schema)
    if errors:
        raise SystemExit("Generated library-lock.yaml does not satisfy schema:\n" + "\n".join(errors))

    output = Path(args.output).resolve() if args.output else (target_root / ".trellis" / "library-lock.yaml")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(yaml.safe_dump(lock, sort_keys=False, allow_unicode=True), encoding="utf-8")
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
