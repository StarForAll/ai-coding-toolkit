#!/usr/bin/env python3
"""
Generate upstream sync proposals from target-project Trellis asset changes.
"""

from __future__ import annotations

import argparse
import difflib
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
    DEFAULT_PRIVATE_HINTS,
    determine_contribution_eligibility,
    determine_diff_status,
    is_managed_target_path,
    managed_target_path_error,
    path_contains_hints,
    relative_file_set,
)


ALLOWED_SCOPES = {"asset", "file", "fragment"}


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


def collect_changed_files(source_path: Path, target_path: Path) -> list[str]:
    if source_path.is_file() and target_path.is_file():
        return [target_path.name]

    source_files = relative_file_set(source_path)
    target_files = relative_file_set(target_path)
    changed = sorted(source_files | target_files)
    result: list[str] = []
    for rel in changed:
        source_file = source_path / rel
        target_file = target_path / rel
        source_text = source_file.read_text(encoding="utf-8").splitlines(keepends=True) if source_file.exists() else []
        target_text = target_file.read_text(encoding="utf-8").splitlines(keepends=True) if target_file.exists() else []
        if source_text != target_text:
            result.append(rel)
    return result


def unified_diff_for_file(source_file: Path, target_file: Path, source_label: str, target_label: str) -> str:
    source_text = source_file.read_text(encoding="utf-8").splitlines(keepends=True) if source_file.exists() else []
    target_text = target_file.read_text(encoding="utf-8").splitlines(keepends=True) if target_file.exists() else []
    return "".join(
        difflib.unified_diff(
            source_text,
            target_text,
            fromfile=source_label,
            tofile=target_label,
        )
    )


def build_report(
    proposal: dict[str, Any],
    changed_files: list[str],
    selected_items: list[str],
    excluded_items: list[str],
    private_hint_detected: bool,
) -> str:
    lines = [
        f"# Proposal: {proposal['proposal_id']}",
        "",
        f"- Asset: `{proposal['target_asset_id']}`",
        f"- Scope: `{proposal['scope']}`",
        f"- Generated At: `{proposal['generated_at']}`",
        f"- Source Project: `{proposal['source_project']}`",
        f"- Contribution Eligible: `{str(proposal['contribution_eligible']).lower()}`",
        f"- Contribution Reason: `{proposal['contribution_reason']}`",
        f"- Recommended Action: `{proposal['recommended_action']}`",
        "",
        "## Selected Items",
    ]
    lines.extend([f"- `{item}`" for item in selected_items] or ["- `(none)`"])
    lines.extend(["", "## Excluded Items"])
    lines.extend([f"- `{item}`" for item in excluded_items] or ["- `(none)`"])
    lines.extend(["", "## Changed Files"])
    lines.extend([f"- `{item}`" for item in changed_files] or ["- `(none)`"])
    lines.extend(
        [
            "",
            "## Generalization Notes",
            "- Ensure project-private terms are removed before applying upstream.",
            "- Keep platform-specific and technology-specific details out of universal domains.",
            "- Preserve the existing concern boundary and file responsibilities.",
            "",
            "## Risks",
            f"- Project-private content detected: `{str(private_hint_detected).lower()}`",
            "- File-level or fragment-level selection should be preferred over whole-asset replacement unless the change is fully generalizable.",
        ]
    )
    return "\n".join(lines) + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate upstream sync proposals from target-project changes")
    parser.add_argument("--library-root", default="trellis-library", help="Path to trellis-library root")
    parser.add_argument("--target", required=True, help="Target project root")
    parser.add_argument("--asset", required=True, help="Asset id to propose upstream")
    parser.add_argument("--scope", default="file", choices=sorted(ALLOWED_SCOPES), help="Proposal scope")
    parser.add_argument("--file", action="append", default=[], help="Specific relative file to include (repeatable)")
    parser.add_argument("--report-out", default=None, help="Markdown report output path")
    parser.add_argument("--patch-out", default=None, help="Unified diff patch output path")
    parser.add_argument("--json", action="store_true", help="Emit proposal metadata as JSON")
    parser.add_argument("--update-lock", action="store_true", help="Write contribution proposal status back into library-lock.yaml")
    return parser.parse_args()


def proposal_diff_error(asset_id: str, diff_status: str, change_scope: str) -> str:
    if diff_status == "unchanged":
        return f"Asset '{asset_id}' has no local diff to propose"
    if diff_status == "missing":
        return f"Asset '{asset_id}' is missing locally; proposal generation requires an existing local diff"
    if diff_status == "migration-required":
        return (
            f"Asset '{asset_id}' no longer exists in the source library; "
            "proposal generation cannot proceed"
        )
    if diff_status == "diverged":
        if change_scope == "structure-change":
            return (
                f"Asset '{asset_id}' has structural drift (added/removed files or a file-vs-directory mismatch); "
                "proposal generation only supports modified content diffs"
            )
        return f"Asset '{asset_id}' is diverged; proposal generation only supports modified content diffs"
    return (
        f"Asset '{asset_id}' has diff status '{diff_status}' ({change_scope}); "
        "proposal generation only supports modified content diffs"
    )


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
        raise SystemExit("Target library-lock.yaml does not satisfy schema before proposal:\n" + "\n".join(schema_errors))

    asset_map = {asset["id"]: asset for asset in manifest.get("assets", []) if isinstance(asset, dict) and "id" in asset}
    asset = asset_map.get(args.asset)
    if not asset:
        raise SystemExit(f"Unknown asset id: {args.asset}")

    import_item = next((item for item in lock.get("imports", []) if item.get("asset_id") == args.asset), None)
    if not import_item:
        raise SystemExit(f"Asset '{args.asset}' is not imported into target project")

    if asset.get("type") != "spec":
        raise SystemExit("Only spec assets are proposal-eligible in the current implementation")

    source_path = library_root / asset["path"]
    target_path = target_root / import_item["target_path"]
    if not is_managed_target_path(import_item.get("target_path", "")):
        raise SystemExit(managed_target_path_error(import_item.get("target_path", "")))
    diff_status, change_scope = determine_diff_status(source_path, target_path)
    if diff_status != "modified":
        raise SystemExit(proposal_diff_error(args.asset, diff_status, change_scope))

    eligible, reason, recommended_action = determine_contribution_eligibility(
        asset,
        diff_status,
        change_scope,
        target_path,
    )
    if not eligible:
        raise SystemExit(f"Asset '{args.asset}' is not marked as contribution eligible")

    if not source_path.exists() or not target_path.exists():
        raise SystemExit("Source or target asset path does not exist")

    if source_path.is_file() != target_path.is_file():
        raise SystemExit("Structure-changing assets are not supported for proposal generation")

    changed_files = collect_changed_files(source_path, target_path)
    if not changed_files:
        raise SystemExit("No local changes found to propose")

    selected_items = sorted(set(args.file)) if args.file else changed_files
    if args.scope == "asset":
        selected_items = changed_files
    excluded_items = [item for item in changed_files if item not in selected_items]

    if args.scope in {"file", "fragment"} and not selected_items:
        raise SystemExit("At least one changed file must be selected")

    private_hint_detected = path_contains_hints(target_path, hints=DEFAULT_PRIVATE_HINTS)

    proposal_id = f"proposal.{args.asset}.{datetime.now().strftime('%Y%m%d%H%M%S')}"
    proposal = {
        "proposal_id": proposal_id,
        "target_asset_id": args.asset,
        "target_paths": [asset["path"]],
        "scope": args.scope,
        "approved": False,
        "source_library_version": manifest.get("version", 1),
        "source_asset_version": asset.get("version", ""),
        "expected_base_checksum": import_item.get("source_checksum", ""),
        "generated_at": iso_now(),
        "source_project": str(target_root),
        "diff_status": diff_status,
        "contribution_eligible": eligible,
        "contribution_reason": reason,
        "recommended_action": recommended_action,
        "selected_scope": args.scope,
        "selected_items": selected_items,
        "excluded_items": excluded_items,
        "private_hint_detected": private_hint_detected,
        "requires_manifest_update": False,
        "requires_relation_review": False,
        "requires_pack_review": False,
    }

    report = build_report(proposal, changed_files, selected_items, excluded_items, private_hint_detected)
    if args.report_out:
        Path(args.report_out).resolve().write_text(report, encoding="utf-8")

    patch_text = ""
    if args.patch_out:
        parts: list[str] = []
        if source_path.is_file():
            parts.append(
                unified_diff_for_file(
                    source_path,
                    target_path,
                    f"a/{asset['path']}",
                    f"b/{asset['path']}",
                )
            )
        else:
            for rel in selected_items:
                parts.append(
                    unified_diff_for_file(
                        source_path / rel,
                        target_path / rel,
                        f"a/{asset['path']}/{rel}",
                        f"b/{asset['path']}/{rel}",
                    )
                )
        patch_text = "".join(parts)
        Path(args.patch_out).resolve().write_text(patch_text, encoding="utf-8")

    if args.update_lock:
        import_item.setdefault("contribution", {})
        import_item["local_state"] = diff_status
        import_item["contribution"]["eligible"] = eligible
        import_item["contribution"]["reviewed"] = True
        import_item["contribution"]["proposed"] = True
        import_item["contribution"]["last_proposed_at"] = proposal["generated_at"]
        schema_errors = validate_against_schema(lock, lock_schema)
        if schema_errors:
            raise SystemExit("Updated library-lock.yaml does not satisfy schema after proposal update:\n" + "\n".join(schema_errors))
        write_yaml(lock_path, lock)

    if args.json:
        print(json.dumps(proposal, indent=2, ensure_ascii=False))
    else:
        print(f"proposal_id: {proposal_id}")
        if args.report_out:
            print(f"report: {Path(args.report_out).resolve()}")
        if args.patch_out:
            print(f"patch: {Path(args.patch_out).resolve()}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
