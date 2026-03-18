#!/usr/bin/env python3
"""
Apply an approved upstream sync proposal to trellis-library.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

import yaml

_PYTHON = (
    "/ops/softwares/python/bin/python3"
    if Path("/ops/softwares/python/bin/python3").exists()
    else sys.executable
)


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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Apply an approved upstream sync proposal")
    parser.add_argument("--library-root", default="trellis-library", help="Path to trellis-library root")
    parser.add_argument("--proposal", required=True, help="Path to approved proposal YAML/JSON")
    parser.add_argument("--patch", required=True, help="Path to unified diff patch file")
    parser.add_argument("--apply", action="store_true", help="Actually apply the patch (default is dry-run)")
    parser.add_argument("--json", action="store_true", help="Emit JSON summary")
    parser.add_argument("--skip-validate", action="store_true", help="Skip post-apply validate-library-sync.py")
    return parser.parse_args()


def normalize_patch_paths(patch_text: str) -> set[str]:
    paths: set[str] = set()
    for line in patch_text.splitlines():
        if line.startswith("--- a/"):
            paths.add(line[len("--- a/"):].strip())
        elif line.startswith("+++ b/"):
            paths.add(line[len("+++ b/"):].strip())
    return paths


def ensure_whitelisted_paths(paths: set[str], target_paths: list[str]) -> None:
    for path in paths:
        if path == "/dev/null":
            continue
        if not any(path == target or path.startswith(target + "/") for target in target_paths):
            raise SystemExit(f"Patch path خارج proposal whitelist: {path}")


def main() -> int:
    args = parse_args()
    library_root = Path(args.library_root).resolve()
    proposal_path = Path(args.proposal).resolve()
    patch_path = Path(args.patch).resolve()
    proposal = load_yaml(proposal_path)

    if proposal.get("approved") is not True:
        raise SystemExit("Proposal must be explicitly approved before apply")

    target_paths = proposal.get("target_paths", [])
    if not isinstance(target_paths, list) or not target_paths:
        raise SystemExit("Proposal must declare non-empty target_paths")

    expected_base_checksum = proposal.get("expected_base_checksum", "")
    target_asset_id = proposal.get("target_asset_id")
    proposal_id = proposal.get("proposal_id", "unknown")

    manifest = load_yaml(library_root / "manifest.yaml")
    asset_map = {asset["id"]: asset for asset in manifest.get("assets", []) if isinstance(asset, dict) and "id" in asset}
    asset = asset_map.get(target_asset_id)
    if not asset:
        raise SystemExit(f"Proposal target asset not found in manifest: {target_asset_id}")

    source_path = library_root / asset["path"]
    actual_checksum = sha256_for_path(source_path)
    if expected_base_checksum and actual_checksum != expected_base_checksum:
        raise SystemExit("Source asset checksum no longer matches proposal base checksum")

    patch_text = patch_path.read_text(encoding="utf-8")
    patch_paths = normalize_patch_paths(patch_text)
    ensure_whitelisted_paths(patch_paths, target_paths)

    summary = {
        "proposal_id": proposal_id,
        "target_asset_id": target_asset_id,
        "paths": sorted(patch_paths),
        "applied": False,
        "validated": False,
        "dry_run": not args.apply,
    }

    if not args.apply:
        if args.json:
            print(json.dumps(summary, indent=2, ensure_ascii=False))
        else:
            print(f"DRY RUN: proposal {proposal_id} ready to apply")
            for path in sorted(patch_paths):
                print(f"  {path}")
        return 0

    with tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False) as temp_patch:
        temp_patch.write(patch_text)
        temp_patch_path = Path(temp_patch.name)

    try:
        apply_cmd = ["git", "apply", str(temp_patch_path)]
        result = subprocess.run(
            apply_cmd,
            check=False,
            capture_output=True,
            text=True,
            cwd=library_root,
        )
        if result.returncode != 0:
            raise SystemExit(f"git apply failed: {result.stderr.strip() or result.stdout.strip()}")
    finally:
        try:
            temp_patch_path.unlink(missing_ok=True)
        except OSError:
            pass

    summary["applied"] = True

    if not args.skip_validate:
        validate_cmd = [
            _PYTHON,
            str(library_root / "scripts" / "validation" / "validate-library-sync.py"),
            "--library-root",
            str(library_root),
            "--strict-warnings",
        ]
        result = subprocess.run(validate_cmd, check=False, capture_output=True, text=True)
        if result.returncode != 0:
            raise SystemExit(f"Post-apply validation failed: {result.stdout.strip() or result.stderr.strip()}")
        summary["validated"] = True

    if args.json:
        print(json.dumps(summary, indent=2, ensure_ascii=False))
    else:
        print(f"APPLIED: {proposal_id}")
        for path in sorted(patch_paths):
            print(f"  {path}")
        if summary["validated"]:
            print("VALIDATED: validate-library-sync passed")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
