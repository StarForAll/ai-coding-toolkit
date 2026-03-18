#!/ops/softwares/python/bin/python3
"""
Assemble a selected Trellis asset set into a target project.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

import yaml


COPYABLE_TYPES = {"spec", "template", "checklist"}


def load_yaml(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise SystemExit(f"Expected YAML mapping in {path}")
    return data


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Assemble trellis-library assets into a target project")
    parser.add_argument("--library-root", default="trellis-library", help="Path to trellis-library root")
    parser.add_argument("--target", required=True, help="Target project root")
    parser.add_argument("--pack", action="append", default=[], help="Pack id to include (repeatable)")
    parser.add_argument("--asset", action="append", default=[], help="Asset id to include (repeatable)")
    parser.add_argument("--include-examples", action="store_true", help="Also copy example assets into .trellis/library-assets/examples")
    parser.add_argument("--dry-run", action="store_true", help="Show actions without copying")
    return parser.parse_args()


def copy_asset(library_root: Path, target_root: Path, asset: dict[str, Any], include_examples: bool, dry_run: bool) -> None:
    asset_type = asset["type"]
    if asset_type not in COPYABLE_TYPES and not (include_examples and asset_type == "example"):
        return

    source = library_root / asset["path"]
    if asset_type in COPYABLE_TYPES:
        destination = target_root / ".trellis" / asset["path"]
    else:
        destination = target_root / ".trellis" / "library-assets" / asset["path"]

    print(f"COPY {source} -> {destination}")
    if dry_run:
        return

    destination.parent.mkdir(parents=True, exist_ok=True)
    if source.is_dir():
        if destination.exists():
            shutil.rmtree(destination)
        shutil.copytree(source, destination)
    else:
        shutil.copy2(source, destination)


def expand_selection(manifest: dict[str, Any], pack_ids: list[str], asset_ids: list[str]) -> list[str]:
    asset_map = {asset["id"]: asset for asset in manifest.get("assets", []) if isinstance(asset, dict) and "id" in asset}
    pack_map = {pack["id"]: pack for pack in manifest.get("packs", []) if isinstance(pack, dict) and "id" in pack}

    ordered: list[str] = []
    seen: set[str] = set()

    def add_asset(asset_id: str) -> None:
        if asset_id in seen:
            return
        asset = asset_map.get(asset_id)
        if not asset:
            raise SystemExit(f"Unknown asset id: {asset_id}")
        for dependency in asset.get("dependencies", []) or []:
            add_asset(dependency)
        seen.add(asset_id)
        ordered.append(asset_id)

    for pack_id in pack_ids:
        pack = pack_map.get(pack_id)
        if not pack:
            raise SystemExit(f"Unknown pack id: {pack_id}")
        for asset_id in pack.get("selection", {}).get("assets", []):
            add_asset(asset_id)

    for asset_id in asset_ids:
        add_asset(asset_id)

    return ordered


def main() -> int:
    args = parse_args()
    library_root = Path(args.library_root).resolve()
    target_root = Path(args.target).resolve()
    manifest = load_yaml(library_root / "manifest.yaml")
    asset_map = {asset["id"]: asset for asset in manifest.get("assets", []) if isinstance(asset, dict) and "id" in asset}

    selected = expand_selection(manifest, args.pack, args.asset)
    if not selected:
        raise SystemExit("No assets selected. Use --pack and/or --asset.")

    for asset_id in selected:
        copy_asset(library_root, target_root, asset_map[asset_id], args.include_examples, args.dry_run)

    if args.dry_run:
        print("DRY RUN: lock file not written")
        return 0

    lock_script = library_root / "scripts" / "assembly" / "write-library-lock.py"
    cmd = [
        str(lock_script),
        "--library-root",
        str(library_root),
        "--target",
        str(target_root),
    ]
    for pack_id in args.pack:
        cmd.extend(["--pack", pack_id])
    for asset_id in selected:
        cmd.extend(["--asset", asset_id])

    result = subprocess.run([sys.executable, *cmd], check=False, text=True)
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
