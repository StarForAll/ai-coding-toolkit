#!/usr/bin/env python3
"""
Analyze trellis-library asset pull: 3-way comparison, local file detection, classification.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
import sys
from typing import Any

import yaml

LIBRARY_ROOT = Path(__file__).resolve().parents[2]
if str(LIBRARY_ROOT) not in sys.path:
    sys.path.insert(0, str(LIBRARY_ROOT))

from _internal.asset_state import relative_file_set, sha256_for_path  # noqa: E402
from _internal.asset_state import is_managed_target_path, managed_target_path_error  # noqa: E402
from _internal.drift_scan import scan_existing_imports as scan_existing_imports_shared  # noqa: E402


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

COPYABLE_TYPES = {"spec", "template", "checklist"}

CATEGORY_LABELS = {
    "new": "New",
    "identical": "Identical",
    "source-updated": "Source Updated",
    "target-modified": "Target Modified",
    "both-modified": "Both Modified",
    "local-conflict": "Local-Conflict",
    "existing": "Existing",
    "structural-conflict": "Structural Conflict",
}


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class LocalFile:
    path: str
    size: int = 0
    modified: str = ""


@dataclass
class AssetAnalysis:
    asset_id: str
    category: str  # new / identical / source-updated / target-modified / both-modified / local-conflict / existing / structural-conflict
    source_path: str = ""
    target_path: str = ""
    import_mode: str = ""
    has_source_change: bool = False
    has_target_change: bool = False
    source_version: str = ""
    source_changes: list[str] = field(default_factory=list)
    target_changes: list[str] = field(default_factory=list)
    local_only_files: list[LocalFile] = field(default_factory=list)
    message: str = ""
    needs_review: bool = False


@dataclass
class SimulationReport:
    timestamp: str
    target_root: str
    assets_requested: list[str] = field(default_factory=list)
    mode: str = "init"  # init or merge
    auto_handled: list[AssetAnalysis] = field(default_factory=list)
    needs_review: list[AssetAnalysis] = field(default_factory=list)
    has_conflicts: bool = False
    source_path_warning: str = ""
    drift_items: list[DriftItem] = field(default_factory=list)


@dataclass
class DriftItem:
    asset_id: str
    drift_type: str  # upstream-changed / local-changed / upstream-and-local-changed
    message: str = ""


# ---------------------------------------------------------------------------
# Utility functions
# ---------------------------------------------------------------------------

def iso_now() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def load_yaml(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise SystemExit(f"Expected YAML mapping in {path}")
    return data


# ---------------------------------------------------------------------------
# Local file detection
# ---------------------------------------------------------------------------

def collect_all_files(root: Path) -> set[str]:
    """Collect all file paths under root (relative to root)."""
    return relative_file_set(root)


def build_tracked_set(lock: dict[str, Any], target_root: Path) -> set[str]:
    """Build set of file paths tracked by lock imports (relative to .trellis/)."""
    tracked: set[str] = set()
    trellis_dir = target_root / ".trellis"
    for imp in lock.get("imports", []):
        target_path = imp.get("target_path", "")
        if not target_path:
            continue
        if not is_managed_target_path(target_path):
            continue
        # target_path is like ".trellis/spec/..." relative to target_root
        # Convert to relative to .trellis/
        try:
            rel_to_trellis = str(Path(target_path).relative_to(".trellis"))
        except ValueError:
            # target_path doesn't start with .trellis, use as-is
            rel_to_trellis = target_path

        full_path = trellis_dir / rel_to_trellis
        if imp.get("import_mode") == "directory":
            if full_path.exists() and full_path.is_dir():
                for child in full_path.rglob("*"):
                    if child.is_file():
                        tracked.add(str(child.relative_to(trellis_dir).as_posix()))
        else:
            if full_path.exists():
                tracked.add(rel_to_trellis)
    return tracked


# Files/directories to exclude from local-only detection (meta-files managed by tooling)
EXCLUDE_FROM_LOCAL_DETECTION = {
    "library-lock.yaml",
    "local-backups",
}


def detect_local_only_files(
    target_root: Path,
    lock: dict[str, Any],
    asset_target_path: str,
    import_mode: str,
) -> list[LocalFile]:
    """Detect files in asset target path that are NOT tracked by any import."""
    if not is_managed_target_path(asset_target_path):
        return []
    trellis_dir = target_root / ".trellis"
    if not trellis_dir.exists():
        return []

    all_files = collect_all_files(trellis_dir)
    tracked = build_tracked_set(lock, target_root)
    local_only = all_files - tracked

    # Exclude meta-files
    local_only = {
        f for f in local_only
        if not any(exc in f for exc in EXCLUDE_FROM_LOCAL_DETECTION)
    }

    # Normalize asset_target_path to be relative to .trellis/
    try:
        asset_target_rel = str(Path(asset_target_path).relative_to(".trellis"))
    except ValueError:
        asset_target_rel = asset_target_path

    # Filter to only files within or overlapping the asset target path
    result: list[LocalFile] = []
    asset_target = Path(asset_target_rel)

    for rel_path in local_only:
        file_path = Path(rel_path)
        is_overlap = False
        if import_mode == "directory":
            # File is inside the target directory
            try:
                file_path.relative_to(asset_target)
                is_overlap = True
            except ValueError:
                pass
        else:
            if file_path == asset_target:
                is_overlap = True

        if is_overlap:
            full = trellis_dir / rel_path
            if not full.exists():
                continue
            stat = full.stat()
            result.append(LocalFile(
                path=f".trellis/{rel_path}",
                size=stat.st_size,
                modified=datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d"),
            ))

    return sorted(result, key=lambda f: f.path)


# ---------------------------------------------------------------------------
# 3-way comparison
# ---------------------------------------------------------------------------

def simple_diff_describe(source_path: Path, target_path: Path) -> tuple[list[str], list[str]]:
    """Generate simple change descriptions between source and target."""
    source_changes: list[str] = []
    target_changes: list[str] = []

    if source_path.is_file() and target_path.is_file():
        source_text = source_path.read_text(encoding="utf-8")
        target_text = target_path.read_text(encoding="utf-8")
        if source_text != target_text:
            source_lines = set(source_text.splitlines())
            target_lines = set(target_text.splitlines())
            added_in_source = source_lines - target_lines
            removed_from_source = target_lines - source_lines
            if added_in_source:
                source_changes.append(f"+ {len(added_in_source)} line(s) added in source")
            if removed_from_source:
                target_changes.append(f"+ {len(removed_from_source)} line(s) in target not in source")
        return source_changes, target_changes

    # Directory comparison
    source_files = collect_all_files(source_path) if source_path.exists() else set()
    target_files = collect_all_files(target_path) if target_path.exists() else set()

    added_files = source_files - target_files
    removed_files = target_files - source_files
    common_files = source_files & target_files

    for f in sorted(added_files):
        source_changes.append(f"+ 新增文件: {f}")
    for f in sorted(removed_files):
        target_changes.append(f"+ 本地文件: {f} (不在源中)")

    for f in sorted(common_files):
        src_content = (source_path / f).read_text(encoding="utf-8") if (source_path / f).exists() else ""
        tgt_content = (target_path / f).read_text(encoding="utf-8") if (target_path / f).exists() else ""
        if src_content != tgt_content:
            source_changes.append(f"~ 修改文件: {f}")

    return source_changes, target_changes


def classify_asset(
    asset: dict[str, Any],
    import_item: dict[str, Any] | None,
    library_root: Path,
    target_root: Path,
    lock: dict[str, Any],
) -> AssetAnalysis:
    """Classify a single asset for pull analysis."""
    asset_id = asset["id"]
    asset_type = asset["type"]
    import_mode = asset["format"]
    source_rel = asset["path"]
    source_abs = library_root / source_rel

    # Determine target path
    if asset_type in COPYABLE_TYPES:
        target_rel = _target_relative_path(asset)
    else:
        target_rel = Path("library-assets") / source_rel

    target_abs = target_root / ".trellis" / target_rel

    analysis = AssetAnalysis(
        asset_id=asset_id,
        category="unknown",
        source_path=str(source_rel),
        target_path=str(Path(".trellis") / target_rel),
        import_mode=import_mode,
        source_version=asset.get("version", ""),
    )

    # Case 1: Already imported (existing)
    if import_item is not None:
        if not is_managed_target_path(import_item.get("target_path", "")):
            analysis.category = "structural-conflict"
            analysis.needs_review = True
            analysis.message = managed_target_path_error(import_item.get("target_path", ""))
            return analysis
        # Check if it's already in lock and unchanged
        source_checksum = sha256_for_path(source_abs)
        stored_source_checksum = import_item.get("source_checksum", "")
        target_checksum = sha256_for_path(target_abs) if target_abs.exists() else ""
        stored_local_checksum = import_item.get("last_local_checksum", "")

        source_changed = source_checksum != stored_source_checksum if stored_source_checksum else False
        target_changed = target_checksum != stored_local_checksum if stored_local_checksum else False

        analysis.has_source_change = source_changed
        analysis.has_target_change = target_changed

        if not source_changed and not target_changed and target_abs.exists():
            analysis.category = "identical"
            analysis.message = "无变更"
            return analysis

        # Get change descriptions
        if target_abs.exists():
            analysis.source_changes, analysis.target_changes = simple_diff_describe(source_abs, target_abs)

        # Check for local-only files in the target path
        analysis.local_only_files = detect_local_only_files(
            target_root, lock, str(target_rel), import_mode,
        )

        # Classify
        if analysis.local_only_files:
            analysis.category = "local-conflict"
            analysis.needs_review = True
            analysis.message = f"检测到 {len(analysis.local_only_files)} 个本地文件不在 lock 中"
        elif source_changed and not target_changed:
            analysis.category = "source-updated"
            analysis.needs_review = True
            analysis.message = "源已更新，目标未修改"
        elif not source_changed and target_changed:
            analysis.category = "target-modified"
            analysis.needs_review = True
            analysis.message = "源未变，目标已被修改"
        elif source_changed and target_changed:
            analysis.category = "both-modified"
            analysis.needs_review = True
            analysis.message = "源和目标都已修改"
        else:
            analysis.category = "existing"
            analysis.message = "已在 lock 中，无变更"

        return analysis

    # Case 2: Not yet imported
    if not target_abs.exists():
        analysis.category = "new"
        analysis.message = "目标不存在，将自动复制"
        return analysis

    # Case 3: Target exists but not in lock (local-only file at target path)
    analysis.local_only_files = detect_local_only_files(
        target_root, lock, str(target_rel), import_mode,
    )

    # Check if the target file itself is a local-only file
    # target_rel is like "spec/..." relative to .trellis/
    target_rel_str = str(target_rel)
    tracked = build_tracked_set(lock, target_root)
    if target_rel_str not in tracked:
        analysis.category = "local-conflict"
        analysis.needs_review = True
        analysis.message = f"目标文件已存在但不在 lock 中（本地创建）"
        # Add the target file itself as local-only
        if not analysis.local_only_files:
            full = target_root / ".trellis" / target_rel
            if full.exists():
                stat = full.stat()
                analysis.local_only_files.append(LocalFile(
                    path=f".trellis/{target_rel_str}",
                    size=stat.st_size,
                    modified=datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d"),
                ))
    else:
        # Target exists and is tracked - re-analyze as existing import
        analysis.category = "new"
        analysis.message = "目标存在但不在 lock 中"
        analysis.needs_review = True

    return analysis


def _target_relative_path(asset: dict[str, Any]) -> Path:
    source_rel = Path(asset["path"])
    if asset["type"] == "spec":
        parts = list(source_rel.parts)
        if parts and parts[0] == "specs":
            parts[0] = "spec"
        return Path(*parts)
    return source_rel


# ---------------------------------------------------------------------------
# Source path migration detection
# ---------------------------------------------------------------------------

def detect_source_path_change(
    lock: dict[str, Any],
    library_root: Path,
) -> str:
    """Detect if library source_path has changed since last lock update.
    Returns warning message or empty string if no issue."""
    if not lock:
        return ""

    library_info = lock.get("library", {})
    stored_source_path = library_info.get("source_path", "")

    if not stored_source_path:
        return ""

    stored_path = Path(stored_source_path).resolve()
    current_path = library_root.resolve()

    # Case 1: stored path no longer exists (library was moved/deleted)
    if not stored_path.exists():
        return (
            f"source_path 迁移检测:\n"
            f"  Lock 中记录的源路径: {stored_source_path} (不存在)\n"
            f"  当前 --library-root: {current_path}\n"
            f"  这表明 trellis-library 目录可能已迁移。\n"
            f"  分析将基于当前路径执行，lock 中的 source_path 将在执行后自动更新。"
        )

    # Case 2: stored path exists but differs from current (possible migration or wrong path)
    if stored_path != current_path:
        return (
            f"source_path 不一致检测:\n"
            f"  Lock 中记录的源路径: {stored_source_path}\n"
            f"  当前 --library-root: {current_path}\n"
            f"  两个路径都存在但不一致。这可能是:\n"
            f"    - trellis-library 目录已迁移\n"
            f"    - 使用了不同的 --library-root 参数\n"
            f"  分析将基于当前路径执行，lock 中的 source_path 将在执行后自动更新。"
        )

    return ""


# ---------------------------------------------------------------------------
# Report generation
# ---------------------------------------------------------------------------

def generate_report(report: SimulationReport) -> str:
    """Generate human-readable simulation report."""
    lines = [
        "=== 拉取模拟报告 ===",
        f"时间: {report.timestamp}",
        f"目标: {report.target_root}",
        f"待拉取: {', '.join(report.assets_requested)}",
        f"模式: {'合并' if report.mode == 'merge' else '初始化'}",
        "",
    ]

    # Source path warning
    if report.source_path_warning:
        lines.append(f"⚠️  {report.source_path_warning}")
        lines.append("")

    # Auto-handled section
    if report.auto_handled:
        lines.append(f"--- 自动处理 (无冲突): {len(report.auto_handled)} 项 ---")
        lines.append("")
        for item in report.auto_handled:
            label = CATEGORY_LABELS.get(item.category, item.category)
            lines.append(f"[{item.asset_id}] {label}")
            lines.append(f"  目标: {item.target_path}")
            lines.append(f"  → {item.message}")
            lines.append("")

    # Needs review section
    if report.needs_review:
        lines.append(f"--- 需要处理 (有冲突): {len(report.needs_review)} 项 ---")
        lines.append("")
        for item in report.needs_review:
            label = CATEGORY_LABELS.get(item.category, item.category)
            flag = "  ⚠️" if item.needs_review else ""
            lines.append(f"[{item.asset_id}] {label}{flag}")

            if item.source_changes:
                lines.append(f"  源变更:")
                for change in item.source_changes:
                    lines.append(f"    {change}")

            if item.target_changes:
                lines.append(f"  目标变更:")
                for change in item.target_changes:
                    lines.append(f"    {change}")

            if item.local_only_files:
                lines.append(f"  本地文件 (不在 lock 中):")
                for lf in item.local_only_files:
                    lines.append(f"    {lf.path}  ({lf.modified})")

            lines.append(f"  说明: {item.message}")
            lines.append("")

    # Summary
    if not report.needs_review:
        lines.append("--- 无冲突，可直接执行 ---")
    else:
        lines.append(f"--- 共 {len(report.needs_review)} 项需要确认处理方式 ---")

    # Drift scan section
    if report.drift_items:
        lines.append("")
        lines.append(f"--- 上游变更检测 (已拉取但本次未操作的资产): {len(report.drift_items)} 项 ---")
        lines.append("")
        for item in report.drift_items:
            if item.drift_type == "upstream-and-local-changed":
                flag = "⚠️"
            elif item.drift_type == "upstream-changed":
                flag = "⬆️"
            else:
                flag = "📝"
            lines.append(f"  {flag} [{item.asset_id}] {item.drift_type}")
            lines.append(f"    {item.message}")
            lines.append("")

    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Analyze trellis-library asset pull: 3-way comparison and classification",
    )
    parser.add_argument("--library-root", default="trellis-library", help="Path to trellis-library root")
    parser.add_argument("--target", required=True, help="Target project root")
    parser.add_argument("--asset", action="append", default=[], help="Asset id to analyze (repeatable)")
    parser.add_argument("--pack", action="append", default=[], help="Pack id to analyze (repeatable)")
    parser.add_argument("--scan-all-imports", action="store_true", help="Also scan existing imports for upstream/local drift")
    parser.add_argument("--no-scan-all-imports", action="store_true", help="Disable merge-mode drift scan for existing imports")
    parser.add_argument("--json", action="store_true", help="Emit JSON output")
    return parser.parse_args()


def expand_selection(
    manifest: dict[str, Any],
    pack_ids: list[str],
    asset_ids: list[str],
) -> list[str]:
    """Expand pack + asset selection into ordered asset id list."""
    asset_map = {
        a["id"]: a
        for a in manifest.get("assets", [])
        if isinstance(a, dict) and "id" in a
    }
    pack_map = {
        p["id"]: p
        for p in manifest.get("packs", [])
        if isinstance(p, dict) and "id" in p
    }

    ordered: list[str] = []
    seen: set[str] = set()

    def add_asset(aid: str) -> None:
        if aid in seen:
            return
        asset = asset_map.get(aid)
        if not asset:
            raise SystemExit(f"Unknown asset id: {aid}")
        for dep in asset.get("dependencies", []) or []:
            if dep in asset_map:
                add_asset(dep)
        seen.add(aid)
        ordered.append(aid)

    for pid in pack_ids:
        pack = pack_map.get(pid)
        if not pack:
            raise SystemExit(f"Unknown pack id: {pid}")
        for aid in pack.get("selection", {}).get("assets", []):
            add_asset(aid)

    for aid in asset_ids:
        add_asset(aid)

    return ordered


def main() -> int:
    args = parse_args()
    library_root = Path(args.library_root).resolve()
    target_root = Path(args.target).resolve()
    manifest_path = library_root / "manifest.yaml"
    lock_path = target_root / ".trellis" / "library-lock.yaml"

    manifest = load_yaml(manifest_path)
    asset_map = {
        a["id"]: a
        for a in manifest.get("assets", [])
        if isinstance(a, dict) and "id" in a
    }

    # Load lock if exists
    lock: dict[str, Any] = {}
    mode = "init"
    if lock_path.exists():
        try:
            lock = load_yaml(lock_path)
            mode = "merge"
        except yaml.YAMLError:
            raise SystemExit(f"Error: library-lock.yaml is corrupted at {lock_path}")

    # Detect source_path migration
    source_path_warning = detect_source_path_change(lock, library_root)

    # Expand selection
    selected = expand_selection(manifest, args.pack, args.asset)
    if not selected:
        raise SystemExit("No assets selected. Use --pack and/or --asset.")

    # Build import index
    import_index = {
        imp["asset_id"]: imp
        for imp in lock.get("imports", [])
        if isinstance(imp, dict) and "asset_id" in imp
    }

    # Analyze each asset
    auto_handled: list[AssetAnalysis] = []
    needs_review: list[AssetAnalysis] = []

    for asset_id in selected:
        asset = asset_map.get(asset_id)
        if not asset:
            raise SystemExit(f"Unknown asset id: {asset_id}")

        analysis = classify_asset(
            asset=asset,
            import_item=import_index.get(asset_id),
            library_root=library_root,
            target_root=target_root,
            lock=lock,
        )

        if analysis.needs_review:
            needs_review.append(analysis)
        else:
            auto_handled.append(analysis)

    # Drift scan for existing imports (merge mode only)
    drift_items: list[DriftItem] = []
    should_scan_all_imports = mode == "merge" and not args.no_scan_all_imports
    if args.scan_all_imports:
        should_scan_all_imports = True
    if should_scan_all_imports:
        drift_items = [
            DriftItem(**item)
            for item in scan_existing_imports_shared(
                lock=lock,
                library_root=library_root,
                target_root=target_root,
                exclude_ids=set(selected),
                asset_map=asset_map,
            )
        ]

    report = SimulationReport(
        timestamp=iso_now(),
        target_root=str(target_root),
        assets_requested=selected,
        mode=mode,
        auto_handled=auto_handled,
        needs_review=needs_review,
        has_conflicts=bool(needs_review),
        source_path_warning=source_path_warning,
        drift_items=drift_items,
    )

    if args.json:
        result = {
            "timestamp": report.timestamp,
            "target_root": report.target_root,
            "assets_requested": report.assets_requested,
            "mode": report.mode,
            "has_conflicts": report.has_conflicts,
            "source_path_warning": report.source_path_warning,
            "auto_handled": [asdict(a) for a in report.auto_handled],
            "needs_review": [asdict(a) for a in report.needs_review],
            "drift_items": [asdict(d) for d in report.drift_items],
        }
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print(generate_report(report))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
