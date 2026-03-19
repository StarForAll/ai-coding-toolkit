#!/usr/bin/env python3
"""
Diff target-project Trellis assets against trellis-library source assets.
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

from _internal.asset_state import (  # noqa: E402
    determine_contribution_eligibility,
    determine_diff_status,
    is_managed_target_path,
    managed_target_path_error,
    sha256_for_path,
)


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


def write_yaml(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Diff target-project assets against trellis-library source assets")
    parser.add_argument("--library-root", default="trellis-library", help="Path to trellis-library root")
    parser.add_argument("--target", required=True, help="Target project root")
    parser.add_argument("--asset", action="append", default=[], help="Only diff this asset id (repeatable)")
    parser.add_argument("--only-modified", action="store_true", help="Only print non-unchanged assets")
    parser.add_argument("--only-eligible", action="store_true", help="Only print upstream-eligible assets")
    parser.add_argument("--json", action="store_true", help="Emit JSON summary")
    parser.add_argument("--update-lock", action="store_true", help="Write diff results back into .trellis/library-lock.yaml")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    library_root = Path(args.library_root).resolve()
    target_root = Path(args.target).resolve()
    manifest = load_yaml(library_root / "manifest.yaml")
    lock_path = target_root / ".trellis" / "library-lock.yaml"
    lock = load_yaml(lock_path)
    lock_schema = json.loads((library_root / "schemas" / "initialization" / "library-lock.schema.json").read_text(encoding="utf-8"))
    schema_errors = validate_against_schema(lock, lock_schema)
    if schema_errors:
        raise SystemExit("Target library-lock.yaml does not satisfy schema before diff:\n" + "\n".join(schema_errors))

    asset_map = {asset["id"]: asset for asset in manifest.get("assets", []) if isinstance(asset, dict) and "id" in asset}
    selected = set(args.asset)

    results: list[dict[str, Any]] = []
    has_warn = False
    has_error = False

    for import_item in lock.get("imports", []):
        asset_id = import_item.get("asset_id")
        if not asset_id:
            continue
        if selected and asset_id not in selected:
            continue

        asset = asset_map.get(asset_id)
        if not asset:
            result = {
                "asset_id": asset_id,
                "diff_status": "migration-required",
                "change_scope": "structure-change",
                "contribution_eligible": False,
                "contribution_reason": "source-asset-missing-or-renamed",
                "recommended_action": "migration-required",
            }
            results.append(result)
            has_warn = True
            import_item["local_state"] = "diverged"
            continue

        source_path = library_root / asset["path"]
        target_path_str = import_item.get("target_path", "")
        if not is_managed_target_path(target_path_str):
            result = {
                "asset_id": asset_id,
                "diff_status": "diverged",
                "change_scope": "structure-change",
                "contribution_eligible": False,
                "contribution_reason": "asset-boundary-or-structure-changed",
                "recommended_action": "manual-review-required",
            }
            results.append(result)
            has_warn = True
            import_item["local_state"] = "diverged"
            import_item["notes"] = managed_target_path_error(target_path_str)
            continue
        target_path = target_root / target_path_str
        diff_status, change_scope = determine_diff_status(source_path, target_path)
        eligible, reason, action = determine_contribution_eligibility(asset, diff_status, change_scope, target_path)

        current_checksum = sha256_for_path(target_path)
        if diff_status == "unchanged":
            import_item["local_state"] = "clean"
        elif diff_status == "modified":
            import_item["local_state"] = "modified"
            has_warn = True
        elif diff_status == "diverged":
            import_item["local_state"] = "diverged"
            has_warn = True
        elif diff_status == "missing":
            import_item["local_state"] = "missing"
            has_warn = True
        else:
            import_item["local_state"] = "diverged"
            has_warn = True

        import_item["last_local_scan_at"] = iso_now()
        import_item["last_local_checksum"] = current_checksum
        import_item.setdefault("contribution", {})
        import_item["contribution"]["eligible"] = eligible

        result = {
            "asset_id": asset_id,
            "diff_status": diff_status,
            "change_scope": change_scope,
            "contribution_eligible": eligible,
            "contribution_reason": reason,
            "recommended_action": action,
        }
        results.append(result)

    if args.only_modified:
        results = [item for item in results if item["diff_status"] != "unchanged"]
    if args.only_eligible:
        results = [item for item in results if item["contribution_eligible"]]

    lock.setdefault("sync", {})
    lock["sync"]["last_diff_at"] = iso_now()
    if has_error:
        lock["sync"]["last_diff_status"] = "fail"
    elif has_warn:
        lock["sync"]["last_diff_status"] = "warn"
    else:
        lock["sync"]["last_diff_status"] = "pass"
    lock["sync"]["local_overrides"] = sorted(
        [
            item["asset_id"]
            for item in lock.get("imports", [])
            if item.get("local_state") in {"modified", "diverged"}
        ]
    )

    if args.update_lock:
        schema_errors = validate_against_schema(lock, lock_schema)
        if schema_errors:
            raise SystemExit("Updated library-lock.yaml does not satisfy schema after diff:\n" + "\n".join(schema_errors))
        write_yaml(lock_path, lock)

    if args.json:
        print(json.dumps(results, indent=2, ensure_ascii=False))
    else:
        for item in results:
            print(
                f"{item['diff_status']}: {item['asset_id']} "
                f"(scope={item['change_scope']}, eligible={str(item['contribution_eligible']).lower()}, action={item['recommended_action']})"
            )

    if has_error:
        return 1
    if has_warn:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
