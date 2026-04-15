#!/usr/bin/env python3
"""Shared workflow asset definitions for installation, upgrade, and analysis."""

from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass
from pathlib import Path


CLI_DIRS = {
    "claude": ".claude",
    "opencode": ".opencode",
    "codex": ".codex",
}
CLI_ALT_DIRS = {
    "codex": ".agents",
}
ALL_CLI_TYPES = ["claude", "opencode", "codex"]
WORKFLOW_VERSION = "1.1.22"

PATCH_BASELINE_COMMANDS = ["start", "finish-work", "record-session"]
OVERLAY_BASELINE_COMMANDS = ["brainstorm", "check"]
OPTIONAL_DISABLED_BASELINE_COMMANDS = ["parallel"]
ADDED_COMMANDS = ["feasibility", "design", "plan", "test-first", "project-audit", "review-gate", "delivery"]
DISTRIBUTED_COMMANDS = [
    "feasibility",
    "brainstorm",
    "design",
    "plan",
    "test-first",
    "project-audit",
    "check",
    "review-gate",
    "delivery",
]
HELPER_SCRIPTS = [
    "feasibility-check.py",
    "design-export.py",
    "workflow-state.py",
    "plan-validate.py",
    "check-quality.py",
    "delivery-control-validate.py",
    "metadata-autocommit-guard.py",
    "record-session-helper.py",
]
LATEST_TRELLIS_VERSION_ENV = "TRELLIS_LATEST_VERSION"


@dataclass(frozen=True)
class ManagedAssetSpec:
    asset_id: str
    category: str
    cli_type: str
    kind: str
    name: str

    def locate(self, root: Path) -> Path | None:
        if self.kind == "script":
            return root / ".trellis" / "scripts" / "workflow" / self.name
        if self.kind == "command":
            return root / CLI_DIRS[self.cli_type] / "commands" / "trellis" / f"{self.name}.md"
        if self.kind == "skill":
            skills_dir = resolve_codex_skills_dir(root)
            if skills_dir is None:
                return None
            return skills_dir / self.name / "SKILL.md"
        raise ValueError(f"Unsupported asset kind: {self.kind}")


def resolve_codex_skills_dir(root: Path) -> Path | None:
    skills_dir = root / ".agents" / "skills"
    if skills_dir.is_dir():
        return skills_dir
    skills_dir = root / ".codex" / "skills"
    if skills_dir.is_dir():
        return skills_dir
    return None


def detect_cli_types(*roots: Path) -> list[str]:
    found: list[str] = []
    for cli_type in ALL_CLI_TYPES:
        for root in roots:
            if cli_type in ("claude", "opencode") and (root / CLI_DIRS[cli_type]).is_dir():
                found.append(cli_type)
                break
            if cli_type == "codex":
                if resolve_codex_skills_dir(root) is not None:
                    found.append(cli_type)
                    break
                if (root / CLI_DIRS[cli_type]).is_dir() or (root / CLI_ALT_DIRS[cli_type]).is_dir():
                    found.append(cli_type)
                    break
    return found


def build_managed_asset_specs(cli_types: list[str]) -> list[ManagedAssetSpec]:
    specs: list[ManagedAssetSpec] = []

    for cli_type in cli_types:
        if cli_type in ("claude", "opencode"):
            for name in PATCH_BASELINE_COMMANDS:
                specs.append(
                    ManagedAssetSpec(
                        asset_id=f"{cli_type}:{name}",
                        category="patch-baseline",
                        cli_type=cli_type,
                        kind="command",
                        name=name,
                    )
                )
            for name in DISTRIBUTED_COMMANDS:
                category = "overlay-baseline" if name in OVERLAY_BASELINE_COMMANDS else "added-command"
                specs.append(
                    ManagedAssetSpec(
                        asset_id=f"{cli_type}:{name}",
                        category=category,
                        cli_type=cli_type,
                        kind="command",
                        name=name,
                    )
                )
        elif cli_type == "codex":
            for name in DISTRIBUTED_COMMANDS:
                category = "overlay-baseline" if name in OVERLAY_BASELINE_COMMANDS else "added-command"
                specs.append(
                    ManagedAssetSpec(
                        asset_id=f"codex:{name}",
                        category=category,
                        cli_type="codex",
                        kind="skill",
                        name=name,
                    )
                )
            specs.append(
                ManagedAssetSpec(
                    asset_id="codex:finish-work",
                    category="patch-baseline",
                    cli_type="codex",
                    kind="skill",
                    name="finish-work",
                )
            )

    if cli_types:
        for name in HELPER_SCRIPTS:
            specs.append(
                ManagedAssetSpec(
                    asset_id=f"shared:{name}",
                    category="shared-script",
                    cli_type="shared",
                    kind="script",
                    name=name,
                )
            )

    return specs


def read_project_trellis_version(root: Path) -> str | None:
    version_path = root / ".trellis" / ".version"
    if not version_path.exists():
        return None
    try:
        content = version_path.read_text(encoding="utf-8").strip()
    except UnicodeDecodeError:
        return None
    return content or None


def resolve_latest_trellis_version() -> tuple[str | None, str]:
    overridden = os.environ.get(LATEST_TRELLIS_VERSION_ENV, "").strip()
    if overridden:
        return overridden, LATEST_TRELLIS_VERSION_ENV

    try:
        result = subprocess.run(
            ["trellis", "-v"],
            text=True,
            capture_output=True,
            check=False,
        )
    except OSError as exc:
        return None, f"trellis -v failed: {exc}"

    output = (result.stdout or result.stderr).strip()
    if result.returncode != 0:
        detail = output or f"exit {result.returncode}"
        return None, f"trellis -v failed: {detail}"
    if not output:
        return None, "trellis -v returned empty output"
    return output.splitlines()[-1].strip(), "trellis -v"


def check_latest_trellis_prerequisite(target_root: Path) -> tuple[bool, str]:
    target_version = read_project_trellis_version(target_root)
    if target_version is None:
        return (
            False,
            "目标项目缺少 .trellis/.version，无法确认是否已升级到当前最新 Trellis；"
            "禁止执行当前步骤（包含只读 A/B/C 分析与兼容升级）。",
        )

    latest_version, source = resolve_latest_trellis_version()
    if latest_version is None:
        return (
            False,
            "无法解析当前最新 Trellis 版本，不能确认兼容升级前置条件。"
            f"版本来源检查失败：{source}。",
        )

    if target_version != latest_version:
        return (
            False,
            "目标项目尚未升级到当前最新 Trellis。"
            f"目标项目版本: {target_version}；当前最新版本: {latest_version}（来源: {source}）。"
            "必须先完成 Trellis 官方升级；禁止执行当前步骤（包含只读 A/B/C 分析与兼容升级）。",
        )

    return True, f"目标项目已升级到当前最新 Trellis: {target_version}（来源: {source}）。"
