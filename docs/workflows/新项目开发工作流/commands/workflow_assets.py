#!/usr/bin/env python3
"""Shared workflow asset definitions for installation, upgrade, and analysis."""

from __future__ import annotations

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

PATCH_BASELINE_COMMANDS = ["start", "finish-work", "record-session"]
OVERLAY_BASELINE_COMMANDS = ["brainstorm", "check"]
ADDED_COMMANDS = ["feasibility", "design", "plan", "test-first", "review-gate", "delivery"]
DISTRIBUTED_COMMANDS = [
    "feasibility",
    "brainstorm",
    "design",
    "plan",
    "test-first",
    "check",
    "review-gate",
    "delivery",
]
HELPER_SCRIPTS = [
    "feasibility-check.py",
    "design-export.py",
    "plan-validate.py",
    "check-quality.py",
    "delivery-control-validate.py",
    "metadata-autocommit-guard.py",
    "record-session-helper.py",
]


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
