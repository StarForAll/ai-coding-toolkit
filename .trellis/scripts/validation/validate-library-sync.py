#!/usr/bin/env python3
"""
Validate trellis-library manifest registration and sync consistency.

This script checks:
1. Manifest structure and duplicate IDs / paths
2. Registered asset paths exist and match the expected top-level type directory
3. Relations reference valid assets and required reverse links
4. Packs reference valid assets
5. Filesystem scan vs manifest registration drift
6. review-on-change relations where target assets may be stale

The goal is not to auto-edit content. It provides a reliable scan and
high-signal report so maintainers can sync related assets safely.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


TYPE_ROOTS = {
    "spec": "specs",
    "template": "templates",
    "checklist": "checklists",
    "example": "examples",
    "schema": "schemas",
    "script": "scripts",
}

TOP_LEVEL_DOCS = {"README.md", "taxonomy.md"}
DIRECTORY_MARKERS = {"overview.md", "README.md", "<meta>.yaml", "normative-rules.md"}
FILE_EXTENSIONS_BY_TYPE = {
    "spec": {".md"},
    "template": {".md"},
    "checklist": {".md"},
    "example": {".md"},
    "schema": {".json", ".yaml", ".yml"},
    "script": {".py", ".sh"},
}
TEXT_CONSISTENCY_SUFFIXES = {".md", ".py", ".sh", ".yaml", ".yml"}
SPEC_REQUIRED_FILES = ("overview.md", "scope-boundary.md", "normative-rules.md", "verification.md")
DIRECT_CROSS_AXIS = frozenset({"platforms", "technologies"})
CHECKLIST_ITEM_PREFIXES = ("* ", "- ")
CJK_RE = re.compile(r"[\u4e00-\u9fff]")


@dataclass
class Finding:
    level: str
    code: str
    message: str
    path: str | None = None
    details: dict[str, Any] | None = None

    def as_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "level": self.level,
            "code": self.code,
            "message": self.message,
        }
        if self.path:
            data["path"] = self.path
        if self.details:
            data["details"] = self.details
        return data


def load_yaml(path: Path) -> dict[str, Any]:
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise SystemExit(f"Manifest not found: {path}") from exc
    except yaml.YAMLError as exc:
        raise SystemExit(f"Failed to parse YAML: {path}: {exc}") from exc

    if not isinstance(data, dict):
        raise SystemExit(f"Manifest root must be a mapping: {path}")
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
        required = schema.get("required", [])
        for key in required:
            if key not in data:
                errors.append(f"{path}: missing required key '{key}'")
        properties = schema.get("properties", {})
        for key, value in data.items():
            if key in properties:
                errors.extend(validate_against_schema(value, properties[key], f"{path}.{key}"))
    elif isinstance(data, list):
        item_schema = schema.get("items")
        if item_schema:
            for index, item in enumerate(data):
                errors.extend(validate_against_schema(item, item_schema, f"{path}[{index}]"))

    return errors


def normalize_rel_path(path: str) -> str:
    return str(Path(path).as_posix()).strip("/")


def expected_root_for_type(asset_type: str) -> str | None:
    return TYPE_ROOTS.get(asset_type)


def latest_mtime(path: Path) -> float:
    if path.is_file():
        return path.stat().st_mtime

    latest = path.stat().st_mtime
    for child in path.rglob("*"):
        if child.is_file():
            latest = max(latest, child.stat().st_mtime)
    return latest


def find_top_level_docs(library_root: Path) -> list[Path]:
    found = []
    for name in TOP_LEVEL_DOCS:
        path = library_root / name
        if path.exists():
            found.append(path)
    manifest = library_root / "manifest.yaml"
    if manifest.exists():
        found.append(manifest)
    return found


def should_ignore_file(path: Path) -> bool:
    if path.name.startswith("."):
        return True
    if path.name == "__pycache__":
        return True
    if any(part == "__pycache__" for part in path.parts):
        return True
    return False


def discover_candidates(library_root: Path) -> dict[str, set[str]]:
    candidates: dict[str, set[str]] = {asset_type: set() for asset_type in TYPE_ROOTS}

    for asset_type, rel_root in TYPE_ROOTS.items():
        root = library_root / rel_root
        if not root.exists():
            continue

        if asset_type in {"schema", "script"}:
            for path in root.rglob("*"):
                if not path.is_file() or should_ignore_file(path):
                    continue
                if path.suffix in FILE_EXTENSIONS_BY_TYPE[asset_type]:
                    candidates[asset_type].add(str(path.relative_to(library_root).as_posix()))
            continue

        # Directory-style candidates first.
        for path in root.rglob("*"):
            if not path.is_dir() or should_ignore_file(path):
                continue
            children = {child.name for child in path.iterdir() if child.exists()}
            if children & DIRECTORY_MARKERS:
                candidates[asset_type].add(str(path.relative_to(library_root).as_posix()))

        # Simple single-file candidates only if not inside a directory-style asset.
        directory_candidates = sorted(candidates[asset_type], key=len)
        for path in root.rglob("*"):
            if not path.is_file() or should_ignore_file(path):
                continue
            if path.suffix not in FILE_EXTENSIONS_BY_TYPE[asset_type]:
                continue
            if path.name in TOP_LEVEL_DOCS or path.name in DIRECTORY_MARKERS:
                continue
            rel = str(path.relative_to(library_root).as_posix())
            if any(rel.startswith(parent + "/") for parent in directory_candidates):
                continue
            candidates[asset_type].add(rel)

    return candidates


def iter_registered_text_files(
    library_root: Path,
    manifest: dict[str, Any],
) -> list[tuple[str, Path]]:
    seen: set[str] = set()
    items: list[tuple[str, Path]] = []

    def add_file(path: Path) -> None:
        rel = str(path.relative_to(library_root).as_posix())
        if rel in seen or path.suffix not in TEXT_CONSISTENCY_SUFFIXES:
            return
        seen.add(rel)
        items.append((rel, path))

    for rel_path in ["README.md", "taxonomy.md", "manifest.yaml"]:
        path = library_root / rel_path
        if path.exists() and path.is_file():
            add_file(path)

    for asset in manifest.get("assets", []):
        if not isinstance(asset, dict):
            continue
        rel_path = asset.get("path")
        if not isinstance(rel_path, str):
            continue
        abs_path = library_root / normalize_rel_path(rel_path)
        if abs_path.is_file():
            add_file(abs_path)
            continue
        if abs_path.is_dir():
            for child in sorted(abs_path.rglob("*")):
                if child.is_file() and not should_ignore_file(child):
                    add_file(child)

    return items


def validate_default_language_consistency(
    library_root: Path,
    manifest: dict[str, Any],
    findings: list[Finding],
) -> None:
    default_language = manifest.get("library", {}).get("default_language")
    if default_language != "en":
        return

    for rel_path, abs_path in iter_registered_text_files(library_root, manifest):
        try:
            lines = abs_path.read_text(encoding="utf-8").splitlines()
        except OSError as exc:
            add_finding(
                findings,
                "WARN",
                "consistency-scan-read-failed",
                f"Could not read file during default-language consistency scan: {exc}",
                path=rel_path,
            )
            continue

        hit_lines = [index for index, line in enumerate(lines, start=1) if CJK_RE.search(line)]
        if not hit_lines:
            continue

        add_finding(
            findings,
            "WARN",
            "non-default-language-content",
            "File contains CJK characters even though library.default_language is 'en'",
            path=rel_path,
            details={"lines": hit_lines[:10], "total_lines": len(hit_lines)},
        )


def is_covered_by_registered_directory_asset(
    rel_path: str,
    registered: set[str],
    discovered_for_type: set[str],
) -> bool:
    parent = Path(rel_path).parent
    while str(parent) not in {"", "."}:
        parent_rel = parent.as_posix()
        if parent_rel in registered and parent_rel in discovered_for_type:
            return True
        parent = parent.parent
    return False


def relation_reverse_exists(relations: list[dict[str, Any]], source: dict[str, Any]) -> bool:
    source_from = source.get("from")
    source_to = source.get("to")
    for relation in relations:
        if relation is source:
            continue
        if relation.get("from") == source_to and relation.get("to") == source_from:
            return True
    return False


def has_markdown_heading(text: str, heading: str) -> bool:
    return any(line.strip() == heading for line in text.splitlines())


def has_checklist_items(text: str) -> bool:
    return any(line.lstrip().startswith(prefix) for line in text.splitlines() for prefix in CHECKLIST_ITEM_PREFIXES)


def allowed_direct_cross_axis_refs(manifest: dict[str, Any]) -> set[str]:
    policies = manifest.get("policies", {})
    raw_values = policies.get("allowed_direct_cross_axis_refs", []) if isinstance(policies, dict) else []
    if not isinstance(raw_values, list):
        return set()
    return {str(item) for item in raw_values if isinstance(item, str)}


def is_direct_cross_axis_reference(source_asset: dict[str, Any], target_asset: dict[str, Any]) -> bool:
    source_axis = source_asset.get("domain_axis")
    target_axis = target_asset.get("domain_axis")
    return (
        isinstance(source_axis, str)
        and isinstance(target_axis, str)
        and source_axis != target_axis
        and {source_axis, target_axis} == DIRECT_CROSS_AXIS
    )


def validate_asset_structure(
    asset_id: str,
    asset_type: str,
    fmt: str,
    abs_path: Path,
    rel_path: str,
    findings: list[Finding],
) -> None:
    if asset_type == "spec" and fmt == "directory":
        present_standard_files = [name for name in SPEC_REQUIRED_FILES if (abs_path / name).is_file()]
        if not present_standard_files:
            return

        has_nested_concerns = any(child.is_dir() and not child.name.startswith(".") for child in abs_path.iterdir())
        if has_nested_concerns and present_standard_files == ["overview.md"]:
            return

        missing = [name for name in SPEC_REQUIRED_FILES if name not in present_standard_files]
        if not missing:
            return

        add_finding(
            findings,
            "ERROR",
            "invalid-spec-structure",
            f"Spec asset '{asset_id}' is missing required standard files: {', '.join(missing)}",
            path=rel_path,
            details={"missing_files": missing},
        )
        return

    if asset_type == "template" and fmt == "file":
        text = abs_path.read_text(encoding="utf-8")
        if not text.startswith("# ") or not has_markdown_heading(text, "## Purpose"):
            add_finding(
                findings,
                "ERROR",
                "invalid-template-structure",
                f"Template asset '{asset_id}' must include a title and a '## Purpose' section",
                path=rel_path,
            )
        return

    if asset_type == "checklist" and fmt == "file":
        text = abs_path.read_text(encoding="utf-8")
        if not text.startswith("# ") or not has_checklist_items(text):
            add_finding(
                findings,
                "ERROR",
                "invalid-checklist-structure",
                f"Checklist asset '{asset_id}' must include a title and at least one checkable bullet item",
                path=rel_path,
            )


def add_finding(
    findings: list[Finding],
    level: str,
    code: str,
    message: str,
    path: str | None = None,
    details: dict[str, Any] | None = None,
) -> None:
    findings.append(Finding(level=level, code=code, message=message, path=path, details=details))


def validate_manifest_shape(manifest: dict[str, Any], findings: list[Finding]) -> None:
    required_keys = ["library", "policies", "assets", "relations", "packs"]
    for key in required_keys:
        if key not in manifest:
            add_finding(findings, "ERROR", "missing-top-level-key", f"Manifest missing top-level key '{key}'")

    for list_key in ["assets", "relations", "packs"]:
        value = manifest.get(list_key, [])
        if not isinstance(value, list):
            add_finding(findings, "ERROR", "invalid-top-level-type", f"Manifest key '{list_key}' must be a list")

    if not isinstance(manifest.get("policies", {}), dict):
        add_finding(findings, "ERROR", "invalid-top-level-type", "Manifest key 'policies' must be a mapping")


def validate_manifest_schema(library_root: Path, manifest: dict[str, Any], findings: list[Finding]) -> None:
    schema_path = library_root / "schemas" / "manifest" / "library-manifest.schema.json"
    if not schema_path.exists():
        add_finding(findings, "WARN", "missing-manifest-schema", "Manifest schema file does not exist", path=str(schema_path))
        return
    try:
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        add_finding(findings, "ERROR", "invalid-manifest-schema", f"Failed to load manifest schema: {exc}", path=str(schema_path))
        return

    for error in validate_against_schema(manifest, schema):
        add_finding(findings, "ERROR", "manifest-schema-validation-failed", error)


def validate_assets(
    manifest: dict[str, Any],
    library_root: Path,
    findings: list[Finding],
) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]], dict[str, set[str]]]:
    assets = manifest.get("assets", [])
    by_id: dict[str, dict[str, Any]] = {}
    by_path: dict[str, dict[str, Any]] = {}
    registered_by_type: dict[str, set[str]] = defaultdict(set)
    allowed_cross_axis_refs = allowed_direct_cross_axis_refs(manifest)

    id_counter = Counter()
    path_counter = Counter()

    for asset in assets:
        if not isinstance(asset, dict):
            add_finding(findings, "ERROR", "invalid-asset-entry", "Asset entry must be a mapping")
            continue

        asset_id = asset.get("id")
        asset_type = asset.get("type")
        rel_path = asset.get("path")
        fmt = asset.get("format")

        if not asset_id or not isinstance(asset_id, str):
            add_finding(findings, "ERROR", "missing-asset-id", "Asset is missing a valid 'id'")
            continue
        if not asset_type or not isinstance(asset_type, str):
            add_finding(findings, "ERROR", "missing-asset-type", f"Asset '{asset_id}' is missing a valid 'type'")
            continue
        if not rel_path or not isinstance(rel_path, str):
            add_finding(findings, "ERROR", "missing-asset-path", f"Asset '{asset_id}' is missing a valid 'path'")
            continue
        if fmt not in {"file", "directory"}:
            add_finding(findings, "ERROR", "invalid-asset-format", f"Asset '{asset_id}' has invalid format '{fmt}'")
            continue

        norm_path = normalize_rel_path(rel_path)
        id_counter[asset_id] += 1
        path_counter[norm_path] += 1

        by_id[asset_id] = asset
        by_path[norm_path] = asset
        registered_by_type[asset_type].add(norm_path)

        expected_root = expected_root_for_type(asset_type)
        if expected_root and not norm_path.startswith(expected_root + "/"):
            add_finding(
                findings,
                "ERROR",
                "asset-type-root-mismatch",
                f"Asset '{asset_id}' path does not match type root '{expected_root}'",
                path=norm_path,
                details={"type": asset_type},
            )

        abs_path = library_root / norm_path
        if not abs_path.exists():
            add_finding(findings, "ERROR", "missing-asset-path-on-disk", f"Asset '{asset_id}' path does not exist", path=norm_path)
            continue

        if fmt == "file" and not abs_path.is_file():
            add_finding(findings, "ERROR", "asset-format-mismatch", f"Asset '{asset_id}' expected a file", path=norm_path)
        if fmt == "directory" and not abs_path.is_dir():
            add_finding(findings, "ERROR", "asset-format-mismatch", f"Asset '{asset_id}' expected a directory", path=norm_path)

        if (fmt == "file" and abs_path.is_file()) or (fmt == "directory" and abs_path.is_dir()):
            validate_asset_structure(asset_id, asset_type, fmt, abs_path, norm_path, findings)

        dependencies = asset.get("dependencies", [])
        optional_dependencies = asset.get("optional_dependencies", [])
        if dependencies and not isinstance(dependencies, list):
            add_finding(findings, "ERROR", "invalid-asset-dependencies", f"Asset '{asset_id}' has non-list dependencies")
        if optional_dependencies and not isinstance(optional_dependencies, list):
            add_finding(findings, "ERROR", "invalid-asset-dependencies", f"Asset '{asset_id}' has non-list optional_dependencies")

    for asset_id, count in id_counter.items():
        if count > 1:
            add_finding(findings, "ERROR", "duplicate-asset-id", f"Asset id '{asset_id}' is duplicated", details={"count": count})
    for rel_path, count in path_counter.items():
        if count > 1:
            add_finding(findings, "ERROR", "duplicate-asset-path", f"Asset path '{rel_path}' is duplicated", path=rel_path, details={"count": count})

    # Validate declared dependencies after registry exists.
    for asset_id, asset in by_id.items():
        for dep_kind in ["dependencies", "optional_dependencies"]:
            for dependency in asset.get(dep_kind, []) or []:
                if dependency not in by_id:
                    add_finding(
                        findings,
                        "ERROR",
                        "unknown-asset-dependency",
                        f"Asset '{asset_id}' references unknown dependency '{dependency}'",
                        details={"dependency_kind": dep_kind},
                    )
                    continue

                target_asset = by_id[dependency]
                ref_key = f"{asset_id}->{dependency}"
                if is_direct_cross_axis_reference(asset, target_asset) and ref_key not in allowed_cross_axis_refs:
                    add_finding(
                        findings,
                        "WARN",
                        "cross-axis-direct-reference",
                        (
                            f"Direct {'optional dependency' if dep_kind == 'optional_dependencies' else 'dependency'} crosses 'platforms' and 'technologies': "
                            f"'{asset_id}' -> '{dependency}'. Move shared rules into universal-domains or compose through packs/examples."
                        ),
                        path=str(asset.get("path", "")) or None,
                        details={"reference_kind": dep_kind, "from": asset_id, "to": dependency},
                    )

    return by_id, by_path, registered_by_type


def validate_relations(
    manifest: dict[str, Any],
    by_id: dict[str, dict[str, Any]],
    library_root: Path,
    findings: list[Finding],
) -> None:
    relations = manifest.get("relations", [])
    policies = manifest.get("policies", {})
    require_reverse_links = bool(policies.get("require_reverse_links", False))
    allowed_cross_axis_refs = allowed_direct_cross_axis_refs(manifest)

    relation_ids = Counter()
    for relation in relations:
        if not isinstance(relation, dict):
            add_finding(findings, "ERROR", "invalid-relation-entry", "Relation entry must be a mapping")
            continue

        relation_id = relation.get("id")
        if relation_id:
            relation_ids[relation_id] += 1

        source = relation.get("from")
        target = relation.get("to")
        sync_policy = relation.get("sync_policy", "none")

        if not source or source not in by_id:
            add_finding(findings, "ERROR", "unknown-relation-source", f"Relation references unknown source asset '{source}'")
            continue
        if not target or target not in by_id:
            add_finding(findings, "ERROR", "unknown-relation-target", f"Relation references unknown target asset '{target}'")
            continue

        source_asset = by_id[source]
        target_asset = by_id[target]
        ref_key = f"{source}->{target}"
        if is_direct_cross_axis_reference(source_asset, target_asset) and ref_key not in allowed_cross_axis_refs:
            add_finding(
                findings,
                "WARN",
                "cross-axis-direct-reference",
                (
                    f"Direct relation crosses 'platforms' and 'technologies': '{source}' -> '{target}'. "
                    "Move shared rules into universal-domains or compose through packs/examples."
                ),
                path=relation_id,
                details={"reference_kind": "relation", "from": source, "to": target},
            )

        if require_reverse_links and relation.get("required", False) and not relation_reverse_exists(relations, relation):
            add_finding(
                findings,
                "WARN",
                "missing-reverse-relation",
                f"Required relation '{relation_id or source + '->' + target}' has no reverse link",
                details={"from": source, "to": target},
            )

        if sync_policy == "review-on-change":
            source_path = library_root / normalize_rel_path(by_id[source]["path"])
            target_path = library_root / normalize_rel_path(by_id[target]["path"])
            if source_path.exists() and target_path.exists():
                try:
                    source_mtime = latest_mtime(source_path)
                    target_mtime = latest_mtime(target_path)
                except OSError as exc:
                    add_finding(findings, "WARN", "mtime-read-failed", f"Failed to read mtimes for relation check: {exc}")
                    continue

                if source_mtime > target_mtime:
                    add_finding(
                        findings,
                        "INFO",
                        "stale-related-asset",
                        "Target asset appears older than source for review-on-change relation; mtime-only drift is informational",
                        details={"from": source, "to": target},
                    )

    for relation_id, count in relation_ids.items():
        if count > 1:
            add_finding(findings, "ERROR", "duplicate-relation-id", f"Relation id '{relation_id}' is duplicated", details={"count": count})


def validate_packs(
    manifest: dict[str, Any],
    by_id: dict[str, dict[str, Any]],
    findings: list[Finding],
) -> None:
    packs = manifest.get("packs", [])
    pack_ids = Counter()

    for pack in packs:
        if not isinstance(pack, dict):
            add_finding(findings, "ERROR", "invalid-pack-entry", "Pack entry must be a mapping")
            continue

        pack_id = pack.get("id")
        if not pack_id or not isinstance(pack_id, str):
            add_finding(findings, "ERROR", "missing-pack-id", "Pack is missing a valid 'id'")
            continue
        pack_ids[pack_id] += 1

        selection = pack.get("selection", {})
        assets = selection.get("assets", []) if isinstance(selection, dict) else []
        if not isinstance(assets, list):
            add_finding(findings, "ERROR", "invalid-pack-selection", f"Pack '{pack_id}' selection.assets must be a list")
            continue

        for asset_id in assets:
            if asset_id not in by_id:
                add_finding(findings, "ERROR", "unknown-pack-asset", f"Pack '{pack_id}' references unknown asset '{asset_id}'")

    for pack_id, count in pack_ids.items():
        if count > 1:
            add_finding(findings, "ERROR", "duplicate-pack-id", f"Pack id '{pack_id}' is duplicated", details={"count": count})


def validate_registration_drift(
    manifest: dict[str, Any],
    library_root: Path,
    registered_by_type: dict[str, set[str]],
    findings: list[Finding],
) -> None:
    policies = manifest.get("policies", {})
    allow_unregistered = bool(policies.get("allow_unregistered_files", False))

    discovered = discover_candidates(library_root)

    for asset_type, candidates in discovered.items():
        registered = registered_by_type.get(asset_type, set())
        for candidate in sorted(candidates - registered):
            level = "WARN" if allow_unregistered else "ERROR"
            add_finding(
                findings,
                level,
                "unregistered-asset-candidate",
                f"Filesystem asset candidate is not registered in manifest",
                path=candidate,
                details={"type": asset_type},
            )

    for asset_type, registered in registered_by_type.items():
        discovered_for_type = discovered.get(asset_type, set())
        expected_root = expected_root_for_type(asset_type)
        for rel_path in sorted(registered):
            abs_path = library_root / rel_path
            if not abs_path.exists():
                continue
            # Only compare against discovered set for roots we scan.
            if expected_root and rel_path.startswith(expected_root + "/") and rel_path not in discovered_for_type:
                if is_covered_by_registered_directory_asset(rel_path, registered, discovered_for_type):
                    continue
                # Registered path exists but did not match candidate scan heuristics.
                add_finding(
                    findings,
                    "INFO",
                    "registered-asset-not-discoverable",
                    "Registered asset exists but was not detected by scan heuristics; consider adding marker files or refining heuristics",
                    path=rel_path,
                    details={"type": asset_type},
                )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate trellis-library sync consistency.")
    parser.add_argument(
        "--library-root",
        default="trellis-library",
        help="Path to trellis-library root (default: trellis-library)",
    )
    parser.add_argument(
        "--manifest",
        default=None,
        help="Optional explicit manifest path (default: <library-root>/manifest.yaml)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit findings as JSON",
    )
    parser.add_argument(
        "--strict-warnings",
        action="store_true",
        help="Exit non-zero on warnings as well as errors",
    )
    return parser


def print_human(findings: list[Finding], library_root: Path, manifest_path: Path) -> None:
    print(f"Library root: {library_root}")
    print(f"Manifest: {manifest_path}")
    print()

    if not findings:
        print("PASS: no sync issues found")
        return

    by_level: dict[str, list[Finding]] = defaultdict(list)
    for finding in findings:
        by_level[finding.level].append(finding)

    for level in ["ERROR", "WARN", "INFO"]:
        group = by_level.get(level, [])
        if not group:
            continue
        print(f"{level} ({len(group)})")
        for item in group:
            suffix = f" [{item.path}]" if item.path else ""
            print(f"  - {item.code}: {item.message}{suffix}")
        print()


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    library_root = Path(args.library_root).resolve()
    manifest_path = Path(args.manifest).resolve() if args.manifest else library_root / "manifest.yaml"

    findings: list[Finding] = []

    if not library_root.exists():
        add_finding(findings, "ERROR", "missing-library-root", "Library root does not exist", path=str(library_root))
    if not manifest_path.exists():
        add_finding(findings, "ERROR", "missing-manifest", "Manifest file does not exist", path=str(manifest_path))

    if findings:
        if args.json:
            print(json.dumps([item.as_dict() for item in findings], indent=2, ensure_ascii=False))
        else:
            print_human(findings, library_root, manifest_path)
        return 1

    manifest = load_yaml(manifest_path)
    validate_manifest_schema(library_root, manifest, findings)
    validate_manifest_shape(manifest, findings)

    by_id, by_path, registered_by_type = validate_assets(manifest, library_root, findings)
    validate_relations(manifest, by_id, library_root, findings)
    validate_packs(manifest, by_id, findings)
    validate_registration_drift(manifest, library_root, registered_by_type, findings)
    validate_default_language_consistency(library_root, manifest, findings)

    # Root file hints.
    root_docs = {str(path.relative_to(library_root).as_posix()) for path in find_top_level_docs(library_root)}
    if "manifest.yaml" not in root_docs:
        add_finding(findings, "WARN", "missing-root-manifest", "Library root does not contain manifest.yaml")

    if args.json:
        print(json.dumps([item.as_dict() for item in findings], indent=2, ensure_ascii=False))
    else:
        print_human(findings, library_root, manifest_path)

    errors = sum(1 for item in findings if item.level == "ERROR")
    warnings = sum(1 for item in findings if item.level == "WARN")

    if errors:
        return 1
    if warnings and args.strict_warnings:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
