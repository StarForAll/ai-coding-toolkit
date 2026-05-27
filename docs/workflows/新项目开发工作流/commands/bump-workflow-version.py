#!/usr/bin/env python3
"""Bump the active workflow version and synchronize current-version references."""

from __future__ import annotations

import argparse
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_REPO_ROOT = SCRIPT_DIR.parents[3]
WORKFLOW_ROOT = DEFAULT_REPO_ROOT / "docs" / "workflows" / "新项目开发工作流"
WORKFLOW_ASSETS = WORKFLOW_ROOT / "commands" / "workflow_assets.py"
WORKFLOW_OVERVIEW = WORKFLOW_ROOT / "工作流总纲.md"
COMMAND_MAPPING = WORKFLOW_ROOT / "命令映射.md"
EMBED_SPEC = WORKFLOW_ROOT / "工作流嵌入执行规范.md"
MINDMAP_HTML = WORKFLOW_ROOT / "工作流思维导图.html"
UPGRADE_GUIDE = WORKFLOW_ROOT / "目标项目兼容升级方案指导.md"
INSTALLER_TESTS = WORKFLOW_ROOT / "commands" / "test_workflow_installers.py"
UPGRADE_ANALYSIS_TESTS = WORKFLOW_ROOT / "commands" / "test_upgrade_analysis.py"

VERSION_RE = re.compile(r'WORKFLOW_VERSION = "(?P<version>\d+\.\d+\.\d+)"')


@dataclass(frozen=True)
class VersionUpdateResult:
    old_version: str
    new_version: str
    changed_files: tuple[Path, ...]


def read_current_version(workflow_assets_path: Path) -> str:
    content = workflow_assets_path.read_text(encoding="utf-8")
    match = VERSION_RE.search(content)
    if match is None:
        raise RuntimeError(f"Could not locate WORKFLOW_VERSION in {workflow_assets_path}")
    return match.group("version")


def bump_patch_version(version: str) -> str:
    parts = version.split(".")
    if len(parts) != 3 or not all(part.isdigit() for part in parts):
        raise ValueError(f"Unsupported workflow version format: {version}")
    major, minor, patch = parts
    return f"{major}.{minor}.{int(patch) + 1}"


def replace_once(content: str, old: str, new: str, *, path: Path) -> str:
    if old not in content:
        raise RuntimeError(f"Expected snippet not found in {path}: {old}")
    return content.replace(old, new, 1)


def update_workflow_assets(path: Path, old_version: str, new_version: str) -> str:
    content = path.read_text(encoding="utf-8")
    old = f'WORKFLOW_VERSION = "{old_version}"'
    new = f'WORKFLOW_VERSION = "{new_version}"'
    return replace_once(content, old, new, path=path)


def update_workflow_overview(path: Path, old_version: str, new_version: str, *, date_text: str, summary: str) -> str:
    content = path.read_text(encoding="utf-8")
    content = replace_once(
        content,
        f"# AI 辅助开发实战工作流 V{old_version}",
        f"# AI 辅助开发实战工作流 V{new_version}",
        path=path,
    )
    content = replace_once(
        content,
        f"**当前 workflow 版本**：`{old_version}`",
        f"**当前 workflow 版本**：`{new_version}`",
        path=path,
    )

    old_row = None
    for line in content.splitlines():
        if line.startswith(f"| V{old_version} |"):
            old_row = line
            break
    if old_row is None:
        raise RuntimeError(f"Could not locate current version history row in {path}")
    new_row = f"| V{new_version} | {date_text} | {summary} |"
    if new_row not in content:
        content = content.replace(old_row, new_row + "\n" + old_row, 1)
    return content


def update_command_mapping(path: Path, old_version: str, new_version: str) -> str:
    content = path.read_text(encoding="utf-8")
    replacements = [
        (
            f"> 将《AI 辅助开发实战工作流 V{old_version}》映射为可执行的 Trellis 命令体系。",
            f"> 将《AI 辅助开发实战工作流 V{new_version}》映射为可执行的 Trellis 命令体系。",
        ),
        (
            f"├── 工作流总纲.md                    # 权威规则层（V{old_version}）",
            f"├── 工作流总纲.md                    # 权威规则层（V{new_version}）",
        ),
        (
            f"| `工作流总纲.md` | 完整工作流定义（V{old_version}） |",
            f"| `工作流总纲.md` | 完整工作流定义（V{new_version}） |",
        ),
    ]
    for old, new in replacements:
        content = replace_once(content, old, new, path=path)
    return content


def update_embed_spec(path: Path, old_version: str, new_version: str) -> str:
    content = path.read_text(encoding="utf-8")
    return replace_once(
        content,
        f"> 当前 workflow 版本：`{old_version}`",
        f"> 当前 workflow 版本：`{new_version}`",
        path=path,
    )


def update_mindmap(path: Path, old_version: str, new_version: str) -> str:
    content = path.read_text(encoding="utf-8")
    replacements = [
        (
            f"<title>AI 辅助开发实战工作流 V{old_version} - 思维导图</title>",
            f"<title>AI 辅助开发实战工作流 V{new_version} - 思维导图</title>",
        ),
        (
            f"html: 'AI 辅助开发实战工作流<br>V{old_version}',",
            f"html: 'AI 辅助开发实战工作流<br>V{new_version}',",
        ),
    ]
    for old, new in replacements:
        content = replace_once(content, old, new, path=path)
    return content


def update_upgrade_guide(path: Path, old_version: str, new_version: str) -> str:
    content = path.read_text(encoding="utf-8")
    return replace_once(
        content,
        f"- `workflow_version`：当前 workflow 功能版本（例如 `{old_version}`）",
        f"- `workflow_version`：当前 workflow 功能版本（例如 `{new_version}`）",
        path=path,
    )


def update_installer_tests(path: Path, old_version: str, new_version: str) -> str:
    content = path.read_text(encoding="utf-8")
    replacements = [
        (
            f'self.assertEqual(record_data["workflow_version"], "{old_version}")',
            f'self.assertEqual(record_data["workflow_version"], "{new_version}")',
        ),
        (
            f'self.assertEqual(updated["workflow_version"], "{old_version}")',
            f'self.assertEqual(updated["workflow_version"], "{new_version}")',
        ),
    ]
    for old, new in replacements:
        while old in content:
            content = replace_once(content, old, new, path=path)
    return content


def update_upgrade_analysis_tests(path: Path, old_version: str, new_version: str) -> str:
    content = path.read_text(encoding="utf-8")
    return replace_once(
        content,
        f'{{"workflow_version":"{old_version}","cli_types":["claude"]}}',
        f'{{"workflow_version":"{new_version}","cli_types":["claude"]}}',
        path=path,
    )


def bump_workflow_version(
    *,
    repo_root: Path,
    expected_current: str | None,
    new_version: str | None,
    summary: str,
    date_text: str,
    dry_run: bool,
) -> VersionUpdateResult:
    workflow_assets_path = repo_root / WORKFLOW_ASSETS.relative_to(DEFAULT_REPO_ROOT)
    old_version = read_current_version(workflow_assets_path)
    if expected_current is not None and old_version != expected_current:
        raise RuntimeError(
            f"Current workflow version {old_version} does not match expected {expected_current}"
        )
    resolved_new_version = new_version or bump_patch_version(old_version)
    if resolved_new_version == old_version:
        raise RuntimeError("New workflow version must differ from current version")

    updates = {
        repo_root / WORKFLOW_ASSETS.relative_to(DEFAULT_REPO_ROOT): update_workflow_assets,
        repo_root / WORKFLOW_OVERVIEW.relative_to(DEFAULT_REPO_ROOT): update_workflow_overview,
        repo_root / COMMAND_MAPPING.relative_to(DEFAULT_REPO_ROOT): update_command_mapping,
        repo_root / EMBED_SPEC.relative_to(DEFAULT_REPO_ROOT): update_embed_spec,
        repo_root / MINDMAP_HTML.relative_to(DEFAULT_REPO_ROOT): update_mindmap,
        repo_root / UPGRADE_GUIDE.relative_to(DEFAULT_REPO_ROOT): update_upgrade_guide,
        repo_root / INSTALLER_TESTS.relative_to(DEFAULT_REPO_ROOT): update_installer_tests,
        repo_root / UPGRADE_ANALYSIS_TESTS.relative_to(DEFAULT_REPO_ROOT): update_upgrade_analysis_tests,
    }

    changed_files: list[Path] = []
    for path, updater in updates.items():
        if not path.exists():
            raise RuntimeError(f"Required version-sync target is missing: {path}")
        if updater is update_workflow_overview:
            new_content = updater(path, old_version, resolved_new_version, date_text=date_text, summary=summary)
        else:
            new_content = updater(path, old_version, resolved_new_version)
        old_content = path.read_text(encoding="utf-8")
        if new_content != old_content:
            changed_files.append(path)
            if not dry_run:
                path.write_text(new_content, encoding="utf-8")

    return VersionUpdateResult(
        old_version=old_version,
        new_version=resolved_new_version,
        changed_files=tuple(changed_files),
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Bump the active workflow version and synchronize current-version references."
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=DEFAULT_REPO_ROOT,
        help="Repository root containing docs/workflows/新项目开发工作流/",
    )
    parser.add_argument(
        "--expected-current",
        type=str,
        default=None,
        help="Fail unless WORKFLOW_VERSION matches this value before bumping.",
    )
    parser.add_argument(
        "--new-version",
        type=str,
        default=None,
        help="Explicit new version. Defaults to incrementing the last numeric segment.",
    )
    parser.add_argument(
        "--summary",
        required=True,
        help="Version history summary for the new row in 工作流总纲.md",
    )
    parser.add_argument(
        "--date",
        default=datetime.now().date().isoformat(),
        help="Date text for the inserted version history row (default: today).",
    )
    parser.add_argument("--dry-run", action="store_true", help="Show planned changes without writing files.")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    result = bump_workflow_version(
        repo_root=args.repo_root.resolve(),
        expected_current=args.expected_current,
        new_version=args.new_version,
        summary=args.summary,
        date_text=args.date,
        dry_run=args.dry_run,
    )
    action = "Would update" if args.dry_run else "Updated"
    print(f"{action} workflow version: {result.old_version} -> {result.new_version}")
    for path in result.changed_files:
        print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
