#!/usr/bin/env python3
"""
Sync trellis-library assets downstream into a target project's .trellis tree.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml


def iso_now() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def sha256_for_path(path: Path) -> str:
    digest = hashlib.sha256()
    if not path.exists():
        return ""
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


def write_yaml(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True), encoding="utf-8")


def copy_path(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    if source.is_dir():
        if destination.exists():
            shutil.rmtree(destination)
        shutil.copytree(source, destination)
    else:
        shutil.copy2(source, destination)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Sync trellis-library assets into a target project")
    parser.add_argument("--library-root", default="trellis-library", help="Path to trellis-library root")
    parser.add_argument("--target", required=True, help="Target project root")
    parser.add_argument("--asset", action="append", default=[], help="Only sync this asset id (repeatable)")
    parser.add_argument("--include-pinned", action="store_true", help="Include pinned assets in analysis (still not auto-updated)")
    parser.add_argument("--no-restore-missing", action="store_true", help="Do not auto-restore missing follow-upstream assets")
    parser.add_argument("--dry-run", action="store_true", help="Show planned actions without writing changes")
    parser.add_argument("--json", action="store_true", help="Emit JSON summary")
    return parser.parse_args()


def determine_local_state(import_item: dict[str, Any], target_abs: Path) -> str:
    expected_mode = import_item.get("import_mode")
    if not target_abs.exists():
        return "missing"
    if expected_mode == "file" and not target_abs.is_file():
        return "diverged"
    if expected_mode == "directory" and not target_abs.is_dir():
        return "diverged"

    current_checksum = sha256_for_path(target_abs)
    last_local_checksum = import_item.get("last_local_checksum", "")
    if last_local_checksum and current_checksum != last_local_checksum:
        return "modified"
    return "clean"


def sync_decision(
    upstream_sync: str,
    local_state: str,
    source_changed: bool,
    restore_missing: bool,
    include_pinned: bool,
) -> str:
    if upstream_sync == "local-only":
        return "skipped-local-only"

    if upstream_sync == "pinned":
        return "skipped-pinned" if include_pinned or source_changed else "unchanged"

    if upstream_sync != "follow-upstream":
        return "error"

    if local_state == "diverged":
        return "blocked-diverged"
    if local_state == "modified":
        return "blocked-modified"
    if local_state == "missing":
        return "restored-missing" if restore_missing else "blocked-missing"
    if local_state == "clean":
        return "updated" if source_changed else "unchanged"
    return "error"


def main() -> int:
    args = parse_args()
    library_root = Path(args.library_root).resolve()
    target_root = Path(args.target).resolve()
    manifest_path = library_root / "manifest.yaml"
    lock_path = target_root / ".trellis" / "library-lock.yaml"

    manifest = load_yaml(manifest_path)
    lock = load_yaml(lock_path)
    lock_schema = json.loads((library_root / "schemas" / "initialization" / "library-lock.schema.json").read_text(encoding="utf-8"))
    schema_errors = validate_against_schema(lock, lock_schema)
    if schema_errors:
        raise SystemExit("Target library-lock.yaml does not satisfy schema before sync:\n" + "\n".join(schema_errors))
    asset_map = {asset["id"]: asset for asset in manifest.get("assets", []) if isinstance(asset, dict) and "id" in asset}

    selected_ids = set(args.asset)
    restore_missing = not args.no_restore_mising if hasattr(args, "no_restore_mising") else not args.no_restore_missing

    results: list[dict[str, Any]] = []
    has_error = False
    has_warn = False

    for import_item in lock.get("imports", []):
        asset_id = import_item.get("asset_id")
        if not asset_id:
            continue
        if selected_ids and asset_id not in selected_ids:
            continue

        asset = asset_map.get(asset_id)
        if not asset:
            result = {
                "asset_id": asset_id,
                "result": "migration-required",
                "message": "Asset no longer exists in source manifest",
            }
            results.append(result)
            has_warn = True
            import_item["local_state"] = "diverged"
            continue

        source_abs = library_root / asset["path"]
        target_abs = target_root / import_item["target_path"]
        upstream_sync = import_item.get("upstream_sync", "follow-upstream")
        local_state = determine_local_state(import_item, target_abs)
        import_item["local_state"] = local_state
        import_item["last_local_scan_at"] = iso_now()

        source_checksum = sha256_for_path(source_abs)
        previous_source_checksum = import_item.get("source_checksum", "")
        source_changed = source_checksum != previous_source_checksum

        decision = sync_decision(
            upstream_sync=upstream_sync,
            local_state=local_state,
            source_changed=source_changed,
            restore_missing=restore_missing,
            include_pinned=args.include_pinned,
        )

        message = ""
        if decision in {"updated", "restored-missing"}:
            message = "Source asset copied to target"
            if not args.dry_run:
                copy_path(source_abs, target_abs)
                import_item["source_version"] = asset.get("version", import_item.get("source_version", ""))
                import_item["source_checksum"] = source_checksum
                import_item["last_local_checksum"] = sha256_for_path(target_abs)
                import_item["local_state"] = "clean"
        elif decision == "unchanged":
            message = "No source change detected"
            if target_abs.exists():
                import_item["last_local_checksum"] = sha256_for_path(target_abs)
        elif decision == "skipped-pinned":
            message = "Pinned asset not auto-updated"
        elif decision == "skipped-local-only":
            message = "Local-only asset excluded from downstream sync"
        elif decision == "blocked-modified":
            message = "Local modifications detected; manual review required"
            has_warn = True
        elif decision == "blocked-diverged":
            message = "Local asset diverged; manual review required"
            has_warn = True
        elif decision == "blocked-missing":
            message = "Asset missing locally and auto-restore disabled"
            has_warn = True
        elif decision == "migration-required":
            message = "Migration required due to manifest drift"
            has_warn = True
        else:
            message = "Unhandled sync condition"
            has_error = True

        results.append(
            {
                "asset_id": asset_id,
                "result": decision,
                "local_state": import_item.get("local_state"),
                "upstream_sync": upstream_sync,
                "source_changed": source_changed,
                "message": message,
            }
        )

    lock.setdefault("sync", {})
    lock["sync"]["last_sync_at"] = iso_now()
    if has_error:
        lock["sync"]["last_sync_status"] = "fail"
    elif has_warn:
        lock["sync"]["last_sync_status"] = "warn"
    else:
        lock["sync"]["last_sync_status"] = "pass"

    for item in results:
        lock.setdefault("history", []).append(
            {
                "at": iso_now(),
                "action": "sync-down",
                "asset_id": item["asset_id"],
                "status": item["result"],
                "notes": item["message"],
            }
        )

    if not args.dry_run:
        schema_errors = validate_against_schema(lock, lock_schema)
        if schema_errors:
            raise SystemExit("Updated library-lock.yaml does not satisfy schema after sync:\n" + "\n".join(schema_errors))
        write_yaml(lock_path, lock)

    if args.json:
        print(json.dumps(results, indent=2, ensure_ascii=False))
    else:
        for item in results:
            print(f"{item['result']}: {item['asset_id']} - {item['message']}")

    if has_error:
        return 1
    if has_warn:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
