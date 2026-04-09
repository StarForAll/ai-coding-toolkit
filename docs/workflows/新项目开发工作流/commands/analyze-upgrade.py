#!/usr/bin/env python3
"""Analyze target-project workflow upgrade actions with baseline/expected/target comparison."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path

from workflow_assets import (
    ALL_CLI_TYPES,
    ManagedAssetSpec,
    build_managed_asset_specs,
    detect_cli_types,
)


@dataclass
class Finding:
    asset_id: str
    category: str
    action: str
    rationale: str
    baseline_exists: bool
    expected_exists: bool
    target_exists: bool


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Analyze workflow-managed files across baseline/expected/target project states."
    )
    parser.add_argument("--baseline-root", type=Path, required=True, help="A: clean Trellis baseline project root")
    parser.add_argument("--expected-root", type=Path, required=True, help="B: expected project root after latest workflow install")
    parser.add_argument("--target-root", type=Path, required=True, help="C: real target project root after Trellis official upgrade")
    parser.add_argument(
        "--cli",
        type=str,
        default=None,
        help="CLI types to analyze, comma-separated: claude,opencode,codex (default: auto-detect)",
    )
    parser.add_argument("--report", type=Path, default=None, help="Optional Markdown report output path")
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON")
    return parser


def read_text(path: Path | None) -> str | None:
    if path is None or not path.exists():
        return None
    return path.read_text(encoding="utf-8")


def load_install_record(root: Path) -> dict[str, object]:
    record_path = root / ".trellis" / "workflow-installed.json"
    if not record_path.exists():
        return {}
    try:
        data = json.loads(record_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        print(f"WARN: failed to read workflow-installed.json: {exc}", file=sys.stderr)
        return {}
    if not isinstance(data, dict):
        print("WARN: workflow-installed.json root is not an object", file=sys.stderr)
        return {}
    return data


def build_legacy_asset_specs(
    cli_types: list[str],
    install_record: dict[str, object],
    current_asset_ids: set[str],
) -> list[ManagedAssetSpec]:
    commands = install_record.get("commands")
    overlay_commands = install_record.get("overlay_commands")
    scripts = install_record.get("scripts")

    if not isinstance(commands, list):
        commands = []
    if not isinstance(overlay_commands, list):
        overlay_commands = []
    if not isinstance(scripts, list):
        scripts = []

    overlay_set = {name for name in overlay_commands if isinstance(name, str)}
    command_names = [name for name in commands if isinstance(name, str)]
    script_names = [name for name in scripts if isinstance(name, str)]

    specs: list[ManagedAssetSpec] = []
    for cli_type in cli_types:
        if cli_type in ("claude", "opencode"):
            for name in command_names:
                asset_id = f"{cli_type}:{name}"
                if asset_id in current_asset_ids:
                    continue
                category = "overlay-baseline" if name in overlay_set else "added-command"
                specs.append(
                    ManagedAssetSpec(
                        asset_id=asset_id,
                        category=category,
                        cli_type=cli_type,
                        kind="command",
                        name=name,
                    )
                )
        elif cli_type == "codex":
            for name in command_names:
                asset_id = f"codex:{name}"
                if asset_id in current_asset_ids:
                    continue
                category = "overlay-baseline" if name in overlay_set else "added-command"
                specs.append(
                    ManagedAssetSpec(
                        asset_id=asset_id,
                        category=category,
                        cli_type="codex",
                        kind="skill",
                        name=name,
                    )
                )

    for name in script_names:
        asset_id = f"shared:{name}"
        if asset_id in current_asset_ids:
            continue
        specs.append(
            ManagedAssetSpec(
                asset_id=asset_id,
                category="shared-script",
                cli_type="shared",
                kind="script",
                name=name,
            )
        )

    return specs


def classify_asset(baseline: str | None, expected: str | None, target: str | None) -> tuple[str, str]:
    if baseline is None and expected is None and target is None:
        return "ignore", "Asset is absent from baseline, expected state, and target state."

    if expected == target:
        return "keep", "Target state already matches the expected workflow-managed state."

    if expected is None:
        if target is None:
            return "ignore", "Asset is absent from both expected state and target state."
        return "delete", "Expected state no longer manages this asset, but target still has content."

    if target is None:
        if baseline is None:
            return "add", "Expected state introduces this asset and target does not have it yet."
        return "replace", "Target lacks the expected managed asset and should restore it from the latest workflow state."

    if baseline is None:
        return "merge", "Target differs from the expected managed content and there is no clean baseline to prove safe overwrite."

    if target == baseline:
        if expected == baseline:
            return "keep", "Expected state keeps the baseline content unchanged."
        return "replace", "Target still matches the baseline; it can be updated to the expected workflow-managed content."

    if expected == baseline:
        return "merge", "Target diverged from the baseline while expected state reverted to baseline; review before changing."

    return "merge", "Target differs from both the baseline and the expected managed content; manual merge review is required."


def render_report(
    findings: list[Finding],
    cli_types: list[str],
    baseline_root: Path,
    expected_root: Path,
    target_root: Path,
) -> str:
    counts = Counter(item.action for item in findings)
    lines = [
        "# 目标项目工作流兼容升级分析报告",
        "",
        "## 输入状态",
        f"- A 基线项目: `{baseline_root}`",
        f"- B 期望状态: `{expected_root}`",
        f"- C 目标项目: `{target_root}`",
        f"- CLI 范围: `{', '.join(cli_types)}`",
        "",
        "## 动作汇总",
        f"- `keep`: {counts.get('keep', 0)}",
        f"- `add`: {counts.get('add', 0)}",
        f"- `replace`: {counts.get('replace', 0)}",
        f"- `merge`: {counts.get('merge', 0)}",
        f"- `delete`: {counts.get('delete', 0)}",
        "",
        "## 明细",
        "",
        "| Asset | Category | Action | Note |",
        "|------|----------|--------|------|",
    ]
    for item in findings:
        lines.append(f"| `{item.asset_id}` | `{item.category}` | `{item.action}` | {item.rationale} |")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    roots = [args.baseline_root, args.expected_root, args.target_root]
    for root in roots:
        if not root.is_dir():
            parser.error(f"Directory does not exist: {root}")

    requested_cli_types: list[str] | None = None
    if args.cli:
        requested_cli_types = [item.strip() for item in args.cli.split(",") if item.strip()]
        invalid = [item for item in requested_cli_types if item not in ALL_CLI_TYPES]
        if invalid:
            parser.error(f"Unsupported CLI type(s): {', '.join(invalid)}")

    detected_cli_types = detect_cli_types(*roots)
    cli_types = requested_cli_types or detected_cli_types
    if not cli_types:
        parser.error("No CLI types detected; pass --cli explicitly if the roots are incomplete.")

    current_specs = build_managed_asset_specs(cli_types)
    current_asset_ids = {spec.asset_id for spec in current_specs}
    legacy_specs = build_legacy_asset_specs(cli_types, load_install_record(args.target_root), current_asset_ids)

    findings: list[Finding] = []
    for spec in [*current_specs, *legacy_specs]:
        baseline = read_text(spec.locate(args.baseline_root))
        expected = read_text(spec.locate(args.expected_root))
        target = read_text(spec.locate(args.target_root))
        action, rationale = classify_asset(baseline, expected, target)
        if action == "ignore":
            continue
        findings.append(
            Finding(
                asset_id=spec.asset_id,
                category=spec.category,
                action=action,
                rationale=rationale,
                baseline_exists=baseline is not None,
                expected_exists=expected is not None,
                target_exists=target is not None,
            )
        )

    findings.sort(key=lambda item: (item.action, item.asset_id))

    if args.report:
        args.report.write_text(
            render_report(findings, cli_types, args.baseline_root, args.expected_root, args.target_root),
            encoding="utf-8",
        )

    if args.json:
        payload = {
            "summary": dict(Counter(item.action for item in findings)),
            "findings": [asdict(item) for item in findings],
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        report = render_report(findings, cli_types, args.baseline_root, args.expected_root, args.target_root)
        print(report)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
