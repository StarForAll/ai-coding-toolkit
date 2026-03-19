#!/usr/bin/env python3
"""
Verify upstream contribution: check upstream status, validate format,
summarize changes, interactive per-file approval, generate proposals.
"""

from __future__ import annotations

import argparse
import difflib
import hashlib
import json
import sys
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

PRIVATE_HINTS = {
    ".trellis/",
    "src/",
    "apps/",
    "packages/",
    "customer",
    "internal-only",
    "project-specific",
}

COPYABLE_TYPES = {"spec", "template", "checklist"}

REQUIRED_SPEC_FILES = {"overview.md"}
RECOMMENDED_SPEC_FILES = {"scope-boundary.md", "normative-rules.md", "verification.md"}


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class FileVerification:
    relative_path: str
    upstream_status: str  # new / identical / different
    line_added: int = 0
    line_removed: int = 0
    has_private_hints: bool = False
    private_hint_details: list[str] = field(default_factory=list)
    format_issues: list[str] = field(default_factory=list)
    approved: bool = False
    user_action: str = ""  # approve / reject / skip


@dataclass
class AssetVerification:
    asset_id: str
    source_path: str = ""
    target_path: str = ""
    files: list[FileVerification] = field(default_factory=list)
    approved_count: int = 0
    total_count: int = 0


# ---------------------------------------------------------------------------
# Utility
# ---------------------------------------------------------------------------

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


def relative_file_set(path: Path) -> set[str]:
    if not path.exists():
        return set()
    if path.is_file():
        return {path.name}
    return {str(child.relative_to(path).as_posix()) for child in path.rglob("*") if child.is_file()}


# ---------------------------------------------------------------------------
# Upstream check
# ---------------------------------------------------------------------------

def collect_changed_files(source_path: Path, target_path: Path) -> list[str]:
    """Find files that differ between source and target."""
    if not target_path.exists():
        return []
    if not source_path.exists():
        # All target files are new relative to upstream
        return sorted(relative_file_set(target_path))

    if source_path.is_file() and target_path.is_file():
        if sha256_for_path(source_path) != sha256_for_path(target_path):
            return [source_path.name]
        return []

    source_files = relative_file_set(source_path)
    target_files = relative_file_set(target_path)

    result: list[str] = []
    for rel in sorted(source_files | target_files):
        sf = source_path / rel
        tf = target_path / rel
        if not sf.exists() or not tf.exists():
            result.append(rel)
            continue
        if sha256_for_path(sf) != sha256_for_path(tf):
            result.append(rel)
    return result


def check_upstream_status(source_path: Path, file_rel: str) -> str:
    """Check if a specific file exists in upstream and compare."""
    source_file = source_path / file_rel
    if not source_file.exists():
        return "new"
    # We know it's different if it's in the changed set, but double-check
    return "different"


def file_has_private_hints(file_path: Path) -> tuple[bool, list[str]]:
    """Check if file contains private hints. Returns (has_hints, hint_list)."""
    if not file_path.exists():
        return False, []
    try:
        content = file_path.read_text(encoding="utf-8")
    except OSError:
        return False, []
    lowered = content.lower()
    found = [hint for hint in PRIVATE_HINTS if hint in lowered]
    return bool(found), found


def count_diff_lines(source_file: Path, target_file: Path) -> tuple[int, int]:
    """Count added and removed lines. Returns (added, removed)."""
    source_lines = source_file.read_text(encoding="utf-8").splitlines() if source_file.exists() else []
    target_lines = target_file.read_text(encoding="utf-8").splitlines() if target_file.exists() else []

    diff = list(difflib.unified_diff(source_lines, target_lines, lineterm=""))
    added = sum(1 for line in diff if line.startswith("+") and not line.startswith("+++"))
    removed = sum(1 for line in diff if line.startswith("-") and not line.startswith("---"))
    return added, removed


# ---------------------------------------------------------------------------
# Format validation
# ---------------------------------------------------------------------------

def validate_format(target_file: Path, source_path: Path, is_new: bool) -> list[str]:
    """Validate that target file conforms to upstream format conventions."""
    issues: list[str] = []

    if not target_file.exists():
        return issues

    if target_file.is_file() and target_file.suffix == ".md":
        content = target_file.read_text(encoding="utf-8")

        # Check frontmatter consistency with upstream
        if source_path.exists():
            if source_path.is_file():
                source_content = source_path.read_text(encoding="utf-8")
                source_has_fm = source_content.startswith("---")
                target_has_fm = content.startswith("---")
                if source_has_fm and not target_has_fm:
                    issues.append("缺少 frontmatter（上游文件有 frontmatter）")
                if not source_has_fm and target_has_fm:
                    issues.append("新增了 frontmatter（上游文件无 frontmatter）")

        # Check section structure for overview.md
        if target_file.name == "overview.md":
            if "## " not in content:
                issues.append("overview.md 缺少 ## 章节结构")

        # Check private references
        lowered = content.lower()
        for hint in PRIVATE_HINTS:
            if hint in lowered:
                issues.append(f"检测到私有引用: '{hint}'")

    return issues


# ---------------------------------------------------------------------------
# Summary generation
# ---------------------------------------------------------------------------

def generate_summary(av: AssetVerification) -> str:
    """Generate brief summary for an asset verification."""
    lines = [
        f"  {av.asset_id}: {av.total_count} 文件待验证",
    ]
    for fv in av.files:
        status_label = {
            "new": "全新",
            "different": "不同",
            "identical": "相同",
        }.get(fv.upstream_status, fv.upstream_status)

        diff_str = f"+{fv.line_added}/-{fv.line_removed}" if fv.upstream_status == "different" else f"+{fv.line_added}"
        private_str = " ⚠️有私有标记" if fv.has_private_hints else ""
        format_str = f" ⚠️格式问题:{len(fv.format_issues)}" if fv.format_issues else ""

        lines.append(
            f"    {fv.relative_path:<40s} {diff_str:<12s} 上游:{status_label}{private_str}{format_str}"
        )
    return "\n".join(lines)


def generate_aggregate_summary(verifications: list[AssetVerification]) -> str:
    """Generate aggregate summary across all assets."""
    total_files = sum(av.total_count for av in verifications)
    new_count = sum(
        1 for av in verifications for fv in av.files if fv.upstream_status == "new"
    )
    different_count = sum(
        1 for av in verifications for fv in av.files if fv.upstream_status == "different"
    )
    private_count = sum(
        1 for av in verifications for fv in av.files if fv.has_private_hints
    )

    lines = [
        "--- 概略 ---",
    ]
    for av in verifications:
        lines.append(generate_summary(av))

    lines.append("")
    lines.append(f"总计: {total_files} 文件 (全新:{new_count}, 不同:{different_count}, 含私有标记:{private_count})")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Interactive verification
# ---------------------------------------------------------------------------

def show_file_detail(fv: FileVerification, source_path: Path, target_path: Path) -> None:
    """Show detailed diff for a file."""
    source_file = source_path / fv.relative_path
    target_file = target_path / fv.relative_path

    source_lines = source_file.read_text(encoding="utf-8").splitlines(keepends=True) if source_file.exists() else []
    target_lines = target_file.read_text(encoding="utf-8").splitlines(keepends=True) if target_file.exists() else []

    diff = difflib.unified_diff(
        source_lines,
        target_lines,
        fromfile=f"上游/{fv.relative_path}",
        tofile=f"本地/{fv.relative_path}",
    )
    print("".join(diff))


def verify_file_interactive(
    fv: FileVerification,
    source_path: Path,
    target_path: Path,
    index: int,
    total: int,
) -> str:
    """Interactive verification for a single file. Returns action: approve/reject/skip."""
    status_label = {
        "new": "全新文件 (上游不存在)",
        "different": "上游存在且不同",
        "identical": "上游存在且相同",
    }.get(fv.upstream_status, fv.upstream_status)

    print(f"\n[{index}/{total}] {fv.relative_path} — {status_label}")

    if fv.upstream_status == "different":
        diff_str = f"+{fv.line_added}行/-{fv.line_removed}行"
        print(f"  变更: {diff_str}")
    else:
        print(f"  内容: {fv.line_added}行")

    if fv.has_private_hints:
        print(f"  ⚠️ 私有标记: {', '.join(fv.private_hint_details)}")

    if fv.format_issues:
        print(f"  ⚠️ 格式问题:")
        for issue in fv.format_issues:
            print(f"    - {issue}")

    if fv.upstream_status == "different":
        print(f"\n  ⚠️ 上游已存在此文件且内容不同，需人工判断")
        print(f"  操作: [a]pprove / [r]eject / [v]iew diff")
    else:
        print(f"\n  操作: [a]pprove / [r]eject / [v]iew content")

    while True:
        try:
            choice = input("  选择: ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print("\n  已取消")
            return "skip"

        if choice in ("a", ""):
            return "approve"
        elif choice == "r":
            return "reject"
        elif choice == "v":
            if fv.upstream_status == "new":
                target_file = target_path / fv.relative_path
                if target_file.exists():
                    print(f"\n--- 内容预览: {fv.relative_path} ---")
                    print(target_file.read_text(encoding="utf-8")[:2000])
                    print("--- 预览结束 ---\n")
            else:
                print(f"\n--- Diff: {fv.relative_path} ---")
                show_file_detail(fv, source_path, target_path)
                print("--- Diff 结束 ---\n")
            print(f"  操作: [a]pprove / [r]eject")
        else:
            print(f"  无效选择，请输入: a / r / v")


def verify_asset_interactive(av: AssetVerification, source_path: Path, target_path: Path) -> None:
    """Interactive verification for all files in an asset."""
    print(f"\n=== 验证: {av.asset_id} ===")

    for i, fv in enumerate(av.files, 1):
        action = verify_file_interactive(fv, source_path, target_path, i, av.total_count)
        fv.user_action = action
        if action == "approve":
            fv.approved = True
            av.approved_count += 1

    print(f"\n  结果: {av.approved_count}/{av.total_count} 文件已批准")


# ---------------------------------------------------------------------------
# Proposal generation
# ---------------------------------------------------------------------------

def generate_proposal(
    av: AssetVerification,
    library_root: Path,
    target_root: Path,
    manifest: dict[str, Any],
    lock: dict[str, Any],
    output_dir: Path,
) -> list[dict[str, Any]]:
    """Generate proposal files for approved files. Returns list of generated artifacts."""
    approved_files = [fv for fv in av.files if fv.approved]
    if not approved_files:
        return []

    asset_map = {
        a["id"]: a
        for a in manifest.get("assets", [])
        if isinstance(a, dict) and "id" in a
    }
    asset = asset_map.get(av.asset_id)
    if not asset:
        return []

    source_rel = asset["path"]
    source_path = library_root / source_rel

    # Determine target path
    if asset["type"] in COPYABLE_TYPES:
        parts = list(Path(source_rel).parts)
        if parts and parts[0] == "specs":
            parts[0] = "spec"
        target_path = target_root / ".trellis" / Path(*parts)
    else:
        target_path = target_root / ".trellis" / "library-assets" / source_rel

    # Get import item for checksum
    import_item = next(
        (imp for imp in lock.get("imports", []) if imp.get("asset_id") == av.asset_id),
        None,
    )

    proposal_id = f"proposal.{av.asset_id}.{datetime.now().strftime('%Y%m%d%H%M%S')}"

    # Generate unified diff
    patch_parts: list[str] = []
    for fv in approved_files:
        sf = source_path / fv.relative_path
        tf = target_path / fv.relative_path
        source_lines = sf.read_text(encoding="utf-8").splitlines(keepends=True) if sf.exists() else []
        target_lines = tf.read_text(encoding="utf-8").splitlines(keepends=True) if tf.exists() else []
        patch_parts.append(
            "".join(difflib.unified_diff(
                source_lines,
                target_lines,
                fromfile=f"a/{source_rel}/{fv.relative_path}",
                tofile=f"b/{source_rel}/{fv.relative_path}",
            ))
        )

    patch_text = "".join(patch_parts)

    # Write patch
    patch_dir = output_dir / "contribution-patches"
    patch_dir.mkdir(parents=True, exist_ok=True)
    patch_file = patch_dir / f"{av.asset_id}.patch"
    patch_file.write_text(patch_text, encoding="utf-8")

    # Write report
    report_dir = output_dir / "contribution-reports"
    report_dir.mkdir(parents=True, exist_ok=True)
    report_file = report_dir / f"{av.asset_id}.md"

    report_lines = [
        f"# Contribution Proposal: {av.asset_id}",
        "",
        f"- Proposal ID: `{proposal_id}`",
        f"- Generated At: `{iso_now()}`",
        f"- Approved Files: {av.approved_count}/{av.total_count}",
        "",
        "## Approved Files",
    ]
    for fv in approved_files:
        if fv.upstream_status == "new":
            report_lines.append(f"- `{fv.relative_path}` (全新文件, +{fv.line_added}行)")
        else:
            report_lines.append(f"- `{fv.relative_path}` (+{fv.line_added}/-{fv.line_removed}行)")
    report_lines.append("")

    rejected_files = [fv for fv in av.files if not fv.approved]
    if rejected_files:
        report_lines.append("## Rejected Files")
        for fv in rejected_files:
            reason = "用户拒绝"
            if fv.has_private_hints:
                reason += f" (私有标记: {', '.join(fv.private_hint_details)})"
            report_lines.append(f"- `{fv.relative_path}` — {reason}")
        report_lines.append("")

    report_lines.extend([
        "## Patch",
        f"See: `{patch_file}`",
        "",
        "## Next Steps",
        "Review the patch and apply with:",
        f"```bash",
        f"python3 trellis-library/cli.py sync --mode apply --proposal {report_file} --patch {patch_file} --apply",
        f"```",
    ])

    report_file.write_text("\n".join(report_lines) + "\n", encoding="utf-8")

    # Write proposal YAML
    proposal_data = {
        "proposal_id": proposal_id,
        "target_asset_id": av.asset_id,
        "target_paths": [source_rel],
        "scope": "file",
        "approved": True,
        "source_library_version": manifest.get("version", 1),
        "source_asset_version": asset.get("version", ""),
        "expected_base_checksum": import_item.get("source_checksum", "") if import_item else "",
        "generated_at": iso_now(),
        "source_project": str(target_root),
        "selected_items": [fv.relative_path for fv in approved_files],
        "excluded_items": [fv.relative_path for fv in rejected_files],
        "private_hint_detected": any(fv.has_private_hints for fv in approved_files),
    }

    proposal_dir = output_dir / "contribution-proposals"
    proposal_dir.mkdir(parents=True, exist_ok=True)
    proposal_file = proposal_dir / f"{av.asset_id}.yaml"

    proposal_dir = output_dir / "contribution-proposals"
    proposal_dir.mkdir(parents=True, exist_ok=True)
    proposal_file = proposal_dir / f"{av.asset_id}.yaml"

    proposal_file.parent.mkdir(parents=True, exist_ok=True)
    proposal_file.write_text(
        yaml.safe_dump(proposal_data, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )

    return [
        {"type": "report", "path": str(report_file)},
        {"type": "patch", "path": str(patch_file)},
        {"type": "proposal", "path": str(proposal_file)},
    ]


# ---------------------------------------------------------------------------
# Main verification flow
# ---------------------------------------------------------------------------

def verify_asset(
    asset_id: str,
    library_root: Path,
    target_root: Path,
    manifest: dict[str, Any],
    lock: dict[str, Any],
) -> AssetVerification:
    """Run full verification for one asset."""
    asset_map = {
        a["id"]: a
        for a in manifest.get("assets", [])
        if isinstance(a, dict) and "id" in a
    }
    asset = asset_map.get(asset_id)
    if not asset:
        raise SystemExit(f"Unknown asset id: {asset_id}")

    source_rel = asset["path"]
    source_path = library_root / source_rel

    # Determine target path
    if asset["type"] in COPYABLE_TYPES:
        parts = list(Path(source_rel).parts)
        if parts and parts[0] == "specs":
            parts[0] = "spec"
        target_path = target_root / ".trellis" / Path(*parts)
    else:
        target_path = target_root / ".trellis" / "library-assets" / source_rel

    # Collect changed files
    changed_files = collect_changed_files(source_path, target_path)

    av = AssetVerification(
        asset_id=asset_id,
        source_path=str(source_rel),
        target_path=str(target_path.relative_to(target_root)),
        total_count=len(changed_files),
    )

    for file_rel in changed_files:
        upstream_status = check_upstream_status(source_path, file_rel)
        target_file = target_path / file_rel
        source_file = source_path / file_rel

        added, removed = count_diff_lines(source_file, target_file)
        has_hints, hint_list = file_has_private_hints(target_file)
        format_issues = validate_format(target_file, source_path, upstream_status == "new")

        av.files.append(FileVerification(
            relative_path=file_rel,
            upstream_status=upstream_status,
            line_added=added,
            line_removed=removed,
            has_private_hints=has_hints,
            private_hint_details=hint_list,
            format_issues=format_issues,
        ))

    return av


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Verify upstream contribution: check, validate, summarize, approve, propose",
    )
    parser.add_argument("--library-root", default="trellis-library", help="Path to trellis-library root")
    parser.add_argument("--target", required=True, help="Target project root")
    parser.add_argument("--asset", action="append", default=[], help="Asset id to verify (repeatable)")
    parser.add_argument("--output-dir", default=None, help="Output directory for proposals (default: target/.trellis)")
    parser.add_argument("--json", action="store_true", help="Emit JSON output")
    parser.add_argument("--non-interactive", action="store_true", help="Skip interactive approval (for CI/testing)")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    library_root = Path(args.library_root).resolve()
    target_root = Path(args.target).resolve()
    manifest_path = library_root / "manifest.yaml"
    lock_path = target_root / ".trellis" / "library-lock.yaml"
    output_dir = Path(args.output_dir).resolve() if args.output_dir else target_root / ".trellis"

    if not lock_path.exists():
        raise SystemExit("No library-lock.yaml found. Cannot verify upstream contribution without existing imports.")

    manifest = load_yaml(manifest_path)
    lock = load_yaml(lock_path)

    asset_ids = list(dict.fromkeys(args.asset))
    if not asset_ids:
        # Auto-detect local-changed assets from lock
        for imp in lock.get("imports", []):
            if imp.get("local_state") in ("modified",):
                asset_ids.append(imp["asset_id"])
        if not asset_ids:
            print("没有检测到本地变更的资产。")
            return 0

    # Phase 1: Verify each asset
    verifications: list[AssetVerification] = []
    for asset_id in asset_ids:
        av = verify_asset(asset_id, library_root, target_root, manifest, lock)
        if av.total_count == 0:
            print(f"  [{asset_id}] 无变更文件，跳过")
            continue
        verifications.append(av)

    if not verifications:
        print("没有需要验证的变更。")
        return 0

    # Phase 2: Show summary
    print("\n=== 贡献验证 ===\n")
    print(generate_aggregate_summary(verifications))

    # Phase 3: Interactive verification
    if args.non_interactive:
        print("\n--non-interactive 模式: 跳过人工验证，所有文件默认 reject")
    else:
        print()
        try:
            choice = input("  [v] 逐项验证 / [s] 退出: ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print("\n  已取消")
            return 0

        if choice != "v":
            print("  已退出验证。")
            return 0

        for av in verifications:
            source_path = library_root / manifest.get("assets", [{}])[0].get("path", "")
            # Re-resolve paths
            asset_map = {
                a["id"]: a
                for a in manifest.get("assets", [])
                if isinstance(a, dict) and "id" in a
            }
            asset = asset_map.get(av.asset_id)
            if not asset:
                continue
            source_rel = asset["path"]
            sp = library_root / source_rel
            if asset["type"] in COPYABLE_TYPES:
                parts = list(Path(source_rel).parts)
                if parts and parts[0] == "specs":
                    parts[0] = "spec"
                tp = target_root / ".trellis" / Path(*parts)
            else:
                tp = target_root / ".trellis" / "library-assets" / source_rel
            verify_asset_interactive(av, sp, tp)

    # Phase 4: Generate proposals for approved files
    artifacts: list[dict[str, Any]] = []
    for av in verifications:
        if av.approved_count > 0:
            result = generate_proposal(av, library_root, target_root, manifest, lock, output_dir)
            artifacts.extend(result)

    if artifacts:
        print(f"\n--- Proposal 已生成 ---")
        for art in artifacts:
            print(f"  {art['type']}: {art['path']}")
        print(f"\n运行以下命令 apply 到上游:")
        for av in verifications:
            if av.approved_count > 0:
                yaml_path = output_dir / "contribution-proposals" / f"{av.asset_id}.yaml"
                patch_path = output_dir / "contribution-patches" / f"{av.asset_id}.patch"
                print(f"  cli.py sync --mode apply --proposal {yaml_path} --patch {patch_path} --apply")
    else:
        print("\n没有文件被批准，未生成 proposal。")

    if args.json:
        result = {
            "verifications": [asdict(av) for av in verifications],
            "artifacts": artifacts,
        }
        print(json.dumps(result, indent=2, ensure_ascii=False))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
