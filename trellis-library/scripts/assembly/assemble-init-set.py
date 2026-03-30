#!/usr/bin/env python3
"""
Assemble a selected Trellis asset set into a target project.

Supports two-phase flow:
  Phase 1: Simulate — analyze all assets, detect conflicts
  Phase 2: Execute — apply user decisions
"""

from __future__ import annotations

import argparse
import difflib
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

import yaml


COPYABLE_TYPES = {"spec", "template", "checklist"}


def _sha256(path: Path) -> str:
    """Compute SHA256 checksum for a file or directory."""
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

PYTHON = (
    "/ops/softwares/python/bin/python3"
    if Path("/ops/softwares/python/bin/python3").exists()
    else sys.executable
)


# ---------------------------------------------------------------------------
# Utility functions
# ---------------------------------------------------------------------------

def load_yaml(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise SystemExit(f"Expected YAML mapping in {path}")
    return data


def target_relative_path(asset: dict[str, Any]) -> Path:
    source_rel = Path(asset["path"])
    if asset["type"] == "spec":
        parts = list(source_rel.parts)
        if parts and parts[0] == "specs":
            parts[0] = "spec"
        return Path(*parts)
    return source_rel


def should_auto_include_dependency(asset: dict[str, Any], include_examples: bool) -> bool:
    asset_type = asset["type"]
    if asset_type in COPYABLE_TYPES:
        return True
    if include_examples and asset_type == "example":
        return True
    return False


# ---------------------------------------------------------------------------
# Selection expansion
# ---------------------------------------------------------------------------

def expand_selection(
    manifest: dict[str, Any],
    pack_ids: list[str],
    asset_ids: list[str],
    include_examples: bool,
) -> list[str]:
    asset_map = {
        asset["id"]: asset
        for asset in manifest.get("assets", [])
        if isinstance(asset, dict) and "id" in asset
    }
    pack_map = {
        pack["id"]: pack
        for pack in manifest.get("packs", [])
        if isinstance(pack, dict) and "id" in pack
    }

    ordered: list[str] = []
    seen: set[str] = set()

    def add_asset(asset_id: str, is_dependency: bool = False) -> None:
        if asset_id in seen:
            return
        asset = asset_map.get(asset_id)
        if not asset:
            raise SystemExit(f"Unknown asset id: {asset_id}")
        if is_dependency and not should_auto_include_dependency(asset, include_examples):
            return
        for dependency in asset.get("dependencies", []) or []:
            add_asset(dependency, is_dependency=True)
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


# ---------------------------------------------------------------------------
# File operations
# ---------------------------------------------------------------------------

def copy_asset(
    library_root: Path,
    target_root: Path,
    asset: dict[str, Any],
    include_examples: bool,
    dry_run: bool,
) -> None:
    asset_type = asset["type"]
    if asset_type not in COPYABLE_TYPES and not (include_examples and asset_type == "example"):
        return

    source = library_root / asset["path"]
    if asset_type in COPYABLE_TYPES:
        destination = target_root / ".trellis" / target_relative_path(asset)
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


def backup_local_files(
    target_root: Path,
    local_files: list[dict[str, Any]],
    dry_run: bool,
) -> str:
    """Backup local-only files to .trellis/local-backups/{timestamp}/."""
    from datetime import datetime
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    backup_dir = target_root / ".trellis" / "local-backups" / timestamp

    for lf in local_files:
        src = target_root / lf["path"]
        dst = backup_dir / lf["path"]
        print(f"BACKUP {src} -> {dst}")
        if not dry_run and src.exists():
            dst.parent.mkdir(parents=True, exist_ok=True)
            if src.is_dir():
                shutil.copytree(src, dst)
            else:
                shutil.copy2(src, dst)

    return str(backup_dir.relative_to(target_root))


# ---------------------------------------------------------------------------
# Phase 1: Simulation
# ---------------------------------------------------------------------------

def run_analysis(
    library_root: Path,
    target_root: Path,
    asset_ids: list[str],
    pack_ids: list[str],
    scan_all_imports: bool = False,
) -> dict[str, Any]:
    """Run analyze-library-pull.py and return JSON result."""
    script = library_root / "scripts" / "assembly" / "analyze-library-pull.py"
    cmd = [
        PYTHON, str(script),
        "--library-root", str(library_root),
        "--target", str(target_root),
        "--json",
    ]
    for aid in asset_ids:
        cmd.extend(["--asset", aid])
    for pid in pack_ids:
        cmd.extend(["--pack", pid])
    if scan_all_imports:
        cmd.append("--scan-all-imports")

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise SystemExit(f"Analysis failed: {result.stderr.strip() or result.stdout.strip()}")

    return json.loads(result.stdout)


def run_analysis_human(
    library_root: Path,
    target_root: Path,
    asset_ids: list[str],
    pack_ids: list[str],
) -> None:
    """Run analyze-library-pull.py in human-readable mode and print."""
    script = library_root / "scripts" / "assembly" / "analyze-library-pull.py"
    cmd = [
        PYTHON, str(script),
        "--library-root", str(library_root),
        "--target", str(target_root),
    ]
    for aid in asset_ids:
        cmd.extend(["--asset", aid])
    for pid in pack_ids:
        cmd.extend(["--pack", pid])

    result = subprocess.run(cmd, capture_output=False, text=True)
    if result.returncode != 0:
        raise SystemExit(f"Analysis failed")


# ---------------------------------------------------------------------------
# Phase 1.5: User interaction
# ---------------------------------------------------------------------------

USER_OPTIONS_FILE_CONFLICT = {
    "m": "manual-review",
    "o": "overwrite",
    "k": "keep-local",
    "s": "skip",
}

USER_OPTIONS_LOCAL_CONFLICT = {
    "p": "preserve",
    "b": "backup",
    "c": "convert",
    "o": "overwrite",
    "s": "skip",
}


def _read_text_lines(path: Path) -> list[str]:
    if not path.exists() or not path.is_file():
        return []
    return path.read_text(encoding="utf-8").splitlines(keepends=True)


def _render_unified_diff(source_path: Path, target_path: Path) -> list[str]:
    if source_path.is_file() and target_path.is_file():
        return list(difflib.unified_diff(
            _read_text_lines(target_path),
            _read_text_lines(source_path),
            fromfile=f"target/{target_path.name}",
            tofile=f"source/{source_path.name}",
        ))

    diff_lines: list[str] = []
    source_files = {
        p.relative_to(source_path).as_posix()
        for p in source_path.rglob("*")
        if p.is_file()
    } if source_path.exists() and source_path.is_dir() else set()
    target_files = {
        p.relative_to(target_path).as_posix()
        for p in target_path.rglob("*")
        if p.is_file()
    } if target_path.exists() and target_path.is_dir() else set()

    for rel_path in sorted(source_files | target_files):
        src_file = source_path / rel_path
        tgt_file = target_path / rel_path
        file_diff = list(difflib.unified_diff(
            _read_text_lines(tgt_file),
            _read_text_lines(src_file),
            fromfile=f"target/{rel_path}",
            tofile=f"source/{rel_path}",
        ))
        if file_diff:
            diff_lines.extend(file_diff)
    return diff_lines


def _print_manual_review_diff(
    library_root: Path,
    target_root: Path,
    analysis: dict[str, Any],
) -> None:
    source_abs = library_root / analysis["source_path"]
    target_abs = target_root / analysis["target_path"]
    diff_lines = _render_unified_diff(source_abs, target_abs)

    print("\n  --- unified diff ---")
    if diff_lines:
        for line in diff_lines:
            print(f"    {line.rstrip()}")
    else:
        print("    (no line-level diff to show; this may be a structural difference or the current file content may already match)")


def _prompt_after_manual_review() -> str:
    print("\n  Choose an action after manual review:")
    print("    [o] Overwrite  — replace the target with the source version")
    print("    [k] Keep Local — keep the local version and update the baseline")
    print("    [s] Skip       — skip this asset")

    followup_options = {
        "o": "overwrite",
        "k": "keep-local",
        "s": "skip",
    }

    while True:
        try:
            choice = input("\n  Choice after review: ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print("\n  Cancelled")
            sys.exit(1)

        if choice in followup_options:
            return followup_options[choice]
        print(f"  Invalid choice. Enter: {', '.join(followup_options.keys())}")


def prompt_user_for_asset(
    analysis: dict[str, Any],
    library_root: Path,
    target_root: Path,
) -> str:
    """Prompt user to choose action for a non-trivial asset. Returns action key."""
    asset_id = analysis["asset_id"]
    category = analysis["category"]
    local_files = analysis.get("local_only_files", [])
    import_mode = analysis.get("import_mode", "file")

    print(f"\n--- Needs Confirmation: [{asset_id}] {category} ---")

    if analysis.get("source_changes"):
        print("  Source changes:")
        for change in analysis["source_changes"]:
            print(f"    {change}")

    if analysis.get("target_changes"):
        print("  Target changes:")
        for change in analysis["target_changes"]:
            print(f"    {change}")

    if local_files:
        print("  Local-only files (not tracked in lock):")
        for lf in local_files:
            print(f"    {lf['path']}  ({lf.get('modified', '')})")

    if local_files:
        print("\n  Choose an action:")
        print("    [b] Backup    — back up to .trellis/local-backups/ and then pull everything")
        print("    [c] Convert   — mark local files as local-only in the lock and then pull everything")
        print("    [o] Overwrite — overwrite directly (local files will be lost)")
        print("    [s] Skip      — skip this asset")
        if import_mode == "file":
            print("    [p] Preserve  — keep the local file and do not import this asset in this run")
            options = USER_OPTIONS_LOCAL_CONFLICT
        else:
            print("    [note] Directory assets do not support preserve; that option would not make any changes")
            options = {k: v for k, v in USER_OPTIONS_LOCAL_CONFLICT.items() if k != "p"}
    else:
        print("\n  Choose an action:")
        print("    [m] Manual Review — show the unified diff before deciding (default)")
        print("    [o] Overwrite     — replace the target with the source version")
        print("    [k] Keep Local    — keep the local version")
        print("    [s] Skip          — skip this asset")
        options = USER_OPTIONS_FILE_CONFLICT

    while True:
        try:
            choice = input("\n  Choice: ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print("\n  Cancelled")
            sys.exit(1)

        if not choice and "m" in options:
            _print_manual_review_diff(library_root, target_root, analysis)
            return _prompt_after_manual_review()
        if choice == "m" and "m" in options:
            _print_manual_review_diff(library_root, target_root, analysis)
            return _prompt_after_manual_review()
        if choice in options:
            return options[choice]
        print(f"  Invalid choice. Enter: {', '.join(options.keys())}")


def collect_user_decisions(
    report: dict[str, Any],
    library_root: Path,
    target_root: Path,
) -> dict[str, str]:
    """Collect user decisions for all needs_review assets."""
    decisions: dict[str, str] = {}

    needs_review = report.get("needs_review", [])
    if not needs_review:
        return decisions

    print(f"\n{'='*50}")
    print(f"  {len(needs_review)} asset(s) require a decision")
    print(f"{'='*50}")

    for analysis in needs_review:
        asset_id = analysis["asset_id"]
        decision = prompt_user_for_asset(analysis, library_root, target_root)
        decisions[asset_id] = decision
        print(f"  -> [{asset_id}] selected: {decision}")

    return decisions


# ---------------------------------------------------------------------------
# Phase 2: Execute
# ---------------------------------------------------------------------------

def execute_pull(
    library_root: Path,
    target_root: Path,
    manifest: dict[str, Any],
    report: dict[str, Any],
    decisions: dict[str, str],
    include_examples: bool,
    dry_run: bool,
) -> list[dict[str, Any]]:
    """Execute the pull based on analysis report and user decisions."""
    asset_map = {
        a["id"]: a
        for a in manifest.get("assets", [])
        if isinstance(a, dict) and "id" in a
    }

    results: list[dict[str, Any]] = []

    # Handle auto-handled assets
    for analysis in report.get("auto_handled", []):
        asset_id = analysis["asset_id"]
        category = analysis["category"]
        asset = asset_map.get(asset_id)
        if not asset:
            results.append({"asset_id": asset_id, "action": "error", "category": category, "message": "asset not found in manifest"})
            continue

        if category == "new":
            copy_asset(library_root, target_root, asset, include_examples, dry_run)
            results.append({"asset_id": asset_id, "action": "copy", "category": category})
        elif category in ("identical", "existing"):
            results.append({"asset_id": asset_id, "action": "skip", "category": category})
        else:
            results.append({"asset_id": asset_id, "action": "skip", "category": category})

    # Handle user-decided assets
    for analysis in report.get("needs_review", []):
        asset_id = analysis["asset_id"]
        asset = asset_map.get(asset_id)
        if not asset:
            results.append({"asset_id": asset_id, "action": "error", "category": analysis["category"], "message": "asset not found in manifest"})
            continue
        decision = decisions.get(asset_id, "skip")
        local_files = analysis.get("local_only_files", [])

        if decision == "skip":
            results.append({"asset_id": asset_id, "action": "skip", "category": analysis["category"]})
            continue

        if decision == "keep-local":
            # Record checksum update: accept current state as new baseline
            target_path_str = analysis["target_path"]
            target_abs = target_root / target_path_str
            source_abs = library_root / asset["path"]
            results.append({
                "asset_id": asset_id,
                "action": "keep-local",
                "category": analysis["category"],
                "checksum_update": {
                    "last_local_checksum": _sha256(target_abs) if target_abs.exists() else "",
                    "source_checksum": _sha256(source_abs) if source_abs.exists() else "",
                    "local_state": "clean",
                },
            })
            continue

        if decision == "backup" and local_files:
            backup_path = backup_local_files(target_root, local_files, dry_run)
            copy_asset(library_root, target_root, asset, include_examples, dry_run)
            results.append({
                "asset_id": asset_id,
                "action": "backup+copy",
                "backup_path": backup_path,
                "category": analysis["category"],
            })
            continue

        if decision == "convert" and local_files:
            copy_asset(library_root, target_root, asset, include_examples, dry_run)
            results.append({
                "asset_id": asset_id,
                "action": "convert+copy",
                "converted_files": [f["path"] for f in local_files],
                "category": analysis["category"],
            })
            continue

        if decision == "preserve" and local_files:
            import_mode = asset.get("format", "file")
            if import_mode == "file":
                results.append({"asset_id": asset_id, "action": "preserve", "category": analysis["category"]})
            else:
                results.append({
                    "asset_id": asset_id,
                    "action": "skip",
                    "category": analysis["category"],
                    "note": "Directory assets do not support preserve; no changes were applied and manual handling is required",
                })
            continue

        # Default: overwrite (decision == "overwrite" or "merge" or "manual-review")
        copy_asset(library_root, target_root, asset, include_examples, dry_run)
        results.append({"asset_id": asset_id, "action": "overwrite", "category": analysis["category"]})

    return results


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Assemble trellis-library assets into a target project (two-phase flow)",
    )
    parser.add_argument("--library-root", default="trellis-library", help="Path to trellis-library root")
    parser.add_argument("--target", required=True, help="Target project root")
    parser.add_argument("--pack", action="append", default=[], help="Pack id to include (repeatable)")
    parser.add_argument("--asset", action="append", default=[], help="Asset id to include (repeatable)")
    parser.add_argument("--include-examples", action="store_true", help="Also copy example assets")
    parser.add_argument("--dry-run", action="store_true", help="Show planned actions without writing changes")
    parser.add_argument("--analyze-only", action="store_true", help="Only run simulation analysis, do not execute")
    parser.add_argument("--auto", action="store_true", help="Auto-proceed without user prompts (CI mode)")
    parser.add_argument("--force", action="store_true", help="Skip analysis, directly overwrite all")
    parser.add_argument("--json", action="store_true", help="Emit JSON output")
    return parser.parse_args()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    args = parse_args()
    library_root = Path(args.library_root).resolve()
    target_root = Path(args.target).resolve()
    lock_path = target_root / ".trellis" / "library-lock.yaml"

    manifest = load_yaml(library_root / "manifest.yaml")

    selected = expand_selection(manifest, args.pack, args.asset, args.include_examples)
    if not selected:
        raise SystemExit("No assets selected. Use --pack and/or --asset.")

    # --- Force mode: skip analysis, direct copy ---
    if args.force:
        asset_map = {
            a["id"]: a
            for a in manifest.get("assets", [])
            if isinstance(a, dict) and "id" in a
        }
        for asset_id in selected:
            copy_asset(library_root, target_root, asset_map[asset_id], args.include_examples, args.dry_run)

        if not args.dry_run:
            _run_lock_writer(library_root, target_root, args.asset, args.pack, merge=lock_path.exists())
        print("FORCE: all assets were overwritten directly")
        return 0

    # --- Phase 1: Simulation ---
    print("=== Phase 1: Simulation Analysis ===\n")

    is_merge_mode = lock_path.exists()
    report = run_analysis(library_root, target_root, args.asset, args.pack, scan_all_imports=is_merge_mode)

    # Print human-readable report
    if not args.json:
        _print_simulation_summary(report)

    # Analyze-only mode: stop here
    if args.analyze_only:
        if args.json:
            print(json.dumps(report, indent=2, ensure_ascii=False))
        return 0

    # JSON mode with execution: output report to stderr, results to stdout
    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False), file=sys.stderr)

    # --- Decision point ---
    has_conflicts = report.get("has_conflicts", False)
    decisions: dict[str, str] = {}

    if has_conflicts:
        if args.auto:
            # Auto mode: use defaults (overwrite for file conflicts, backup for local conflicts)
            for analysis in report.get("needs_review", []):
                if analysis.get("local_only_files"):
                    decisions[analysis["asset_id"]] = "backup"
                else:
                    decisions[analysis["asset_id"]] = "overwrite"
            print("\n--auto mode: using default conflict handling --")
            for aid, dec in decisions.items():
                print(f"  [{aid}] → {dec}")
        else:
            # Interactive mode
            decisions = collect_user_decisions(report, library_root, target_root)

    # --- Phase 2: Execute ---
    print("\n=== Phase 2: Execute ===\n")

    results = execute_pull(
        library_root=library_root,
        target_root=target_root,
        manifest=manifest,
        report=report,
        decisions=decisions,
        include_examples=args.include_examples,
        dry_run=args.dry_run,
    )

    if args.dry_run:
        print("DRY RUN: lock file was not updated")
        return 0

    # --- Update lock ---
    _run_lock_writer(library_root, target_root, args.asset, args.pack, merge=lock_path.exists())

    # --- Post-process: Apply checksum updates for keep-local decisions ---
    checksum_updates = {
        r["asset_id"]: r["checksum_update"]
        for r in results
        if r.get("checksum_update")
    }
    if checksum_updates and lock_path.exists():
        _apply_checksum_updates(lock_path, checksum_updates)

    # --- Summary ---
    print("\n--- Execution Complete ---")
    for r in results:
        print(f"  {r['asset_id']}: {r['action']} ({r['category']})")

    # --- Offer contribution for drift items ---
    drift_items = report.get("drift_items", [])
    local_changed = [
        d for d in drift_items
        if d.get("drift_type") in ("local-changed", "upstream-and-local-changed")
    ]
    if local_changed and not args.auto and not args.dry_run:
        print(f"\n  Detected {len(local_changed)} asset(s) with local changes that can be proposed upstream:")
        for item in local_changed:
            print(f"    📝 [{item['asset_id']}] {item['drift_type']}")
        try:
            choice = input("\n  [c] contribution verification / [i] ignore: ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            choice = "i"

        if choice == "c":
            _run_contribute(library_root, target_root, [d["asset_id"] for d in local_changed])

    if args.json:
        print(json.dumps(results, indent=2, ensure_ascii=False))

    return 0


def _run_lock_writer(
    library_root: Path,
    target_root: Path,
    asset_ids: list[str],
    pack_ids: list[str],
    merge: bool,
) -> None:
    """Run write-library-lock.py with appropriate flags."""
    script = library_root / "scripts" / "assembly" / "write-library-lock.py"
    cmd = [
        PYTHON, str(script),
        "--library-root", str(library_root),
        "--target", str(target_root),
    ]
    for aid in asset_ids:
        cmd.extend(["--asset", aid])
    for pid in pack_ids:
        cmd.extend(["--pack", pid])
    if merge:
        cmd.append("--merge")

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise SystemExit(f"Lock update failed: {result.stderr.strip() or result.stdout.strip()}")
    if result.stdout.strip():
        print(f"Lock: {result.stdout.strip()}")


def _run_contribute(
    library_root: Path,
    target_root: Path,
    asset_ids: list[str],
) -> None:
    """Run verify-upstream-contribution.py for the given assets."""
    script = library_root / "scripts" / "contribution" / "verify-upstream-contribution.py"
    cmd = [
        PYTHON, str(script),
        "--library-root", str(library_root),
        "--target", str(target_root),
    ]
    for aid in asset_ids:
        cmd.extend(["--asset", aid])

    result = subprocess.run(cmd, check=False)
    if result.returncode != 0:
        print(f"  Contribution verification exit code: {result.returncode}")


def _apply_checksum_updates(
    lock_path: Path,
    checksum_updates: dict[str, dict[str, str]],
) -> None:
    """Apply checksum updates to lock file for keep-local decisions."""
    lock = load_yaml(lock_path)
    modified = False

    for imp in lock.get("imports", []):
        asset_id = imp.get("asset_id", "")
        if asset_id in checksum_updates:
            update = checksum_updates[asset_id]
            if "last_local_checksum" in update:
                imp["last_local_checksum"] = update["last_local_checksum"]
            if "source_checksum" in update:
                imp["source_checksum"] = update["source_checksum"]
            if "local_state" in update:
                imp["local_state"] = update["local_state"]
            modified = True

    if modified:
        lock_path.write_text(
            yaml.safe_dump(lock, sort_keys=False, allow_unicode=True),
            encoding="utf-8",
        )


def _print_simulation_summary(report: dict[str, Any]) -> None:
    """Print a concise simulation summary."""
    # Source path warning
    warning = report.get("source_path_warning", "")
    if warning:
        print(f"  ⚠️  {warning}")
        print()

    auto = report.get("auto_handled", [])
    review = report.get("needs_review", [])

    if auto:
        print(f"  Auto-handled (no conflicts): {len(auto)} item(s)")
        for a in auto:
            print(f"    [{a['asset_id']}] {a['category']} → {a['message']}")

    if review:
        print(f"  Needs review (has conflicts): {len(review)} item(s)")
        for a in review:
            print(f"    [{a['asset_id']}] {a['category']} ⚠️ → {a['message']}")
    else:
        print("  No conflicts detected; ready to execute")

    # Drift scan results
    drift_items = report.get("drift_items", [])
    if drift_items:
        print()
        print(f"  --- Upstream drift detected for imported assets not touched in this run: {len(drift_items)} item(s) ---")
        for item in drift_items:
            flag = "⚠️" if item["drift_type"] == "upstream-and-local-changed" else ("⬆️" if item["drift_type"] == "upstream-changed" else "📝")
            print(f"    {flag} [{item['asset_id']}] {item['drift_type']}")
            print(f"      {item['message']}")

    print()


if __name__ == "__main__":
    raise SystemExit(main())
