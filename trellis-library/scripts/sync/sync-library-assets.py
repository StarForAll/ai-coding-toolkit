#!/usr/bin/env python3
"""
Sync trellis-library assets downstream into a target project's .trellis tree.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

LIBRARY_ROOT = Path(__file__).resolve().parents[2]
if str(LIBRARY_ROOT) not in sys.path:
    sys.path.insert(0, str(LIBRARY_ROOT))

from _internal.asset_state import determine_local_state as _determine_local_state  # noqa: E402
from _internal.asset_state import (  # noqa: E402
    is_managed_target_path,
    managed_target_path_error,
    sha256_for_path,
)
from _internal.drift_scan import scan_existing_imports as scan_existing_imports_shared  # noqa: E402


PYTHON = (
    "/ops/softwares/python/bin/python3"
    if Path("/ops/softwares/python/bin/python3").exists()
    else sys.executable
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
    parser.add_argument("--force", action="store_true", help="Skip confirmation, auto-execute all changes (CI mode)")
    parser.add_argument("--json", action="store_true", help="Emit JSON summary")
    return parser.parse_args()


def determine_local_state(
    import_item: dict[str, Any],
    target_abs: Path,
    source_abs: Path | None = None,
) -> str:
    resolved_source = source_abs
    if resolved_source is None and import_item.get("source_path"):
        resolved_source = Path(__file__).resolve().parents[2] / str(import_item["source_path"])
    return _determine_local_state(import_item, target_abs, resolved_source)


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
        if not include_pinned:
            return "skipped-pinned" if source_changed else "unchanged"
        if local_state == "diverged":
            return "blocked-diverged"
        if local_state == "modified":
            return "blocked-modified"
        if local_state == "missing":
            return "restored-missing" if restore_missing else "blocked-missing"
        if local_state == "clean":
            return "updated" if source_changed else "unchanged"
        return "error"

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


def _run_contribute(
    library_root: Path,
    target_root: Path,
    asset_ids: list[str],
) -> None:
    script = library_root / "scripts" / "contribution" / "verify-upstream-contribution.py"
    cmd = [
        PYTHON, str(script),
        "--library-root", str(library_root),
        "--target", str(target_root),
    ]
    for asset_id in asset_ids:
        cmd.extend(["--asset", asset_id])

    result = subprocess.run(cmd, check=False)
    if result.returncode != 0:
        print(f"  贡献验证返回码: {result.returncode}")


def _print_contribution_candidates(planned_actions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    candidates = [
        action for action in planned_actions
        if action.get("drift_type") in {"local-changed", "upstream-and-local-changed"}
    ]
    if candidates:
        print(f"\n  检测到 {len(candidates)} 个资产存在可贡献的本地漂移:")
        for action in candidates:
            print(f"    📝 [{action['asset_id']}] {action['drift_type']}")
    return candidates


def _emit_other_drift_items(other_drift_items: list[dict[str, str]], json_mode: bool) -> None:
    if not other_drift_items:
        return
    lines = [
        "",
        f"  检测到 {len(other_drift_items)} 个已导入但本次未操作的资产存在漂移:",
    ]
    for item in other_drift_items:
        lines.append(f"    [{item['asset_id']}] {item['drift_type']} - {item['message']}")
    output = "\n".join(lines)
    if json_mode:
        print(output, file=sys.stderr)
    else:
        print(output)


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
    restore_missing = not args.no_restore_missing

    # Phase 1: Collect all planned actions
    planned_actions: list[dict[str, Any]] = []
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
            planned_actions.append({
                "asset_id": asset_id,
                "decision": "migration-required",
                "message": "Asset no longer exists in source manifest",
                "needs_confirm": False,
                "import_item": import_item,
                "asset": None,
            })
            has_warn = True
            import_item["local_state"] = "diverged"
            continue

        source_abs = library_root / asset["path"]
        target_path_str = import_item.get("target_path", "")
        if not is_managed_target_path(target_path_str):
            planned_actions.append({
                "asset_id": asset_id,
                "decision": "unmanaged-target-path",
                "message": managed_target_path_error(target_path_str),
                "needs_confirm": False,
                "import_item": import_item,
                "asset": asset,
            })
            has_warn = True
            import_item["local_state"] = "diverged"
            continue
        target_abs = target_root / target_path_str
        upstream_sync = import_item.get("upstream_sync", "follow-upstream")
        local_state = determine_local_state(import_item, target_abs, source_abs)
        import_item["local_state"] = local_state
        import_item["last_local_scan_at"] = iso_now()
        import_item["last_observed_checksum"] = (
            sha256_for_path(target_abs) if target_abs.exists() else ""
        )

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

        # Determine if this action needs user confirmation
        needs_confirm = decision in {"updated", "restored-missing"}

        planned_actions.append({
            "asset_id": asset_id,
            "decision": decision,
            "local_state": local_state,
            "source_changed": source_changed,
            "needs_confirm": needs_confirm,
            "import_item": import_item,
            "asset": asset,
            "source_abs": source_abs,
            "target_abs": target_abs,
            "source_checksum": source_checksum,
            "drift_type": (
                "upstream-and-local-changed"
                if decision == "blocked-modified" and source_changed
                else "local-changed"
                if decision == "blocked-modified"
                else ""
            ),
        })

    # Phase 2: Show summary and ask for confirmation
    actions_to_confirm = [a for a in planned_actions if a["needs_confirm"]]
    other_drift_items: list[dict[str, str]] = []
    if selected_ids:
        other_drift_items = scan_existing_imports_shared(
            lock=lock,
            library_root=library_root,
            target_root=target_root,
            exclude_ids=selected_ids,
            asset_map=asset_map,
        )

    if actions_to_confirm:
        print("=== Sync 计划 ===\n")
        for a in actions_to_confirm:
            version_info = ""
            if a.get("asset"):
                version_info = f" ({a['asset'].get('version', '')})"
            action_label = {
                "updated": "覆盖目标 (源已更新)",
                "restored-missing": "恢复目标 (目标缺失)",
            }.get(a["decision"], a["decision"])
            print(f"  [{a['asset_id']}]{version_info} → {action_label}")

        # Show non-actionable items for awareness
        non_actionable = [a for a in planned_actions if not a["needs_confirm"] and a["decision"] not in ("unchanged", "skipped-local-only", "skipped-pinned")]
        if non_actionable:
            print(f"\n  其他状态 ({len(non_actionable)} 项):")
            for a in non_actionable:
                print(f"    [{a['asset_id']}] {a['decision']}")

        # Ask for confirmation
        if args.dry_run:
            print(f"\nDRY RUN: 以上 {len(actions_to_confirm)} 项操作不会执行")
            # Still generate results for output
            results = _build_results(planned_actions)
            if args.json:
                print(json.dumps(results, indent=2, ensure_ascii=False))
            else:
                for item in results:
                    print(f"{item['result']}: {item['asset_id']} - {item['message']}")
            _emit_other_drift_items(other_drift_items, args.json)
            _print_contribution_candidates(planned_actions)
            return 0

        if not args.force:
            print(f"\n  共 {len(actions_to_confirm)} 项操作将修改目标文件。")
            try:
                choice = input("  确认执行? [y]es / [n]o / [a]ll: ").strip().lower()
            except (EOFError, KeyboardInterrupt):
                print("\n  已取消")
                return 0

            if choice == "n":
                print("  已取消 sync。")
                return 0
            elif choice in ("y", "a"):
                pass  # proceed
            else:
                print("  无效选择，已取消。")
                return 0
        print()

    # Phase 3: Execute
    results: list[dict[str, Any]] = []

    for action in planned_actions:
        decision = action["decision"]
        import_item = action["import_item"]

        message = ""
        if decision in {"updated", "restored-missing"}:
            message = "Source asset copied to target"
            if not args.dry_run:
                copy_path(action["source_abs"], action["target_abs"])
                import_item["source_version"] = action["asset"].get("version", import_item.get("source_version", ""))
                import_item["source_checksum"] = action["source_checksum"]
                import_item["last_local_checksum"] = sha256_for_path(action["target_abs"])
                import_item["local_state"] = "clean"
        elif decision == "unchanged":
            message = "No source change detected"
            if action.get("target_abs") and action["target_abs"].exists():
                import_item["last_local_checksum"] = sha256_for_path(action["target_abs"])
        elif decision == "skipped-pinned":
            message = "Pinned asset not auto-updated"
        elif decision == "skipped-local-only":
            message = "Local-only asset excluded from downstream sync"
        elif decision == "blocked-modified":
            message = "Local modifications detected; manual review required"
            import_item["last_blocked_at"] = iso_now()
            import_item["blocked_count"] = int(import_item.get("blocked_count", 0)) + 1
            has_warn = True
        elif decision == "blocked-diverged":
            message = "Local asset diverged; manual review required"
            import_item["last_blocked_at"] = iso_now()
            import_item["blocked_count"] = int(import_item.get("blocked_count", 0)) + 1
            has_warn = True
        elif decision == "blocked-missing":
            message = "Asset missing locally and auto-restore disabled"
            import_item["last_blocked_at"] = iso_now()
            import_item["blocked_count"] = int(import_item.get("blocked_count", 0)) + 1
            has_warn = True
        elif decision == "migration-required":
            message = "Migration required due to manifest drift"
            has_warn = True
        elif decision == "unmanaged-target-path":
            message = action["message"]
            has_warn = True
        else:
            message = "Unhandled sync condition"
            has_error = True

        results.append({
            "asset_id": action["asset_id"],
            "result": decision,
            "local_state": import_item.get("local_state"),
            "upstream_sync": import_item.get("upstream_sync", "follow-upstream"),
            "source_changed": action.get("source_changed", False),
            "message": message,
        })

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

    _emit_other_drift_items(other_drift_items, args.json)
    contribution_candidates = _print_contribution_candidates(planned_actions)
    if contribution_candidates:
        if not args.dry_run and not args.force:
            try:
                choice = input("\n  [c] 贡献验证 / [i] 忽略: ").strip().lower()
            except (EOFError, KeyboardInterrupt):
                choice = "i"

            if choice == "c":
                _run_contribute(
                    library_root,
                    target_root,
                    [item["asset_id"] for item in contribution_candidates],
                )

    if has_error:
        return 1
    if has_warn:
        return 2
    return 0


def _build_results(planned_actions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Build results list from planned actions (for dry-run output)."""
    results = []
    for action in planned_actions:
        decision = action["decision"]
        message = ""
        if decision in {"updated", "restored-missing"}:
            message = "Source asset copied to target"
        elif decision == "unchanged":
            message = "No source change detected"
        elif decision == "skipped-pinned":
            message = "Pinned asset not auto-updated"
        elif decision == "skipped-local-only":
            message = "Local-only asset excluded from downstream sync"
        elif decision == "blocked-modified":
            message = "Local modifications detected; manual review required"
        elif decision == "blocked-diverged":
            message = "Local asset diverged; manual review required"
        elif decision == "blocked-missing":
            message = "Asset missing locally and auto-restore disabled"
        elif decision == "migration-required":
            message = "Migration required due to manifest drift"
        else:
            message = "Unhandled sync condition"
        results.append({
            "asset_id": action["asset_id"],
            "result": decision,
            "message": message,
        })
    return results


if __name__ == "__main__":
    raise SystemExit(main())
