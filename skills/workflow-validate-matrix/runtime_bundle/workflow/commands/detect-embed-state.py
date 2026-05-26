#!/usr/bin/env python3
"""Detect whether a target project is eligible for a first workflow embed."""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path


def _load_module(module_name: str, filename: str):
    module_path = Path(__file__).resolve().with_name(filename)
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"无法加载模块: {module_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


INSTALL = _load_module("workflow_install_workflow", "install-workflow.py")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="检测目标项目是否处于允许首次嵌入当前 workflow 的初始态"
    )
    parser.add_argument(
        "--project-root",
        type=Path,
        default=Path.cwd(),
        help="目标项目根目录（默认当前工作目录）",
    )
    parser.add_argument(
        "--cli",
        type=str,
        default=None,
        help="指定 CLI 类型，逗号分隔: claude,opencode,codex",
    )
    parser.add_argument("--json", action="store_true", help="输出 JSON")
    return parser


def _normalize_requested(cli_arg: str | None) -> list[str] | None:
    if not cli_arg:
        return None
    requested = [item.strip() for item in cli_arg.split(",") if item.strip()]
    for item in requested:
        if item not in INSTALL._ALL_CLI_TYPES:
            raise SystemExit(f"未知 CLI 类型: {item}")
    return requested or None


def _run_upgrade_check(commands_root: Path, target_root: Path, requested: list[str] | None) -> tuple[bool, str]:
    command = [
        sys.executable,
        str(commands_root / "upgrade-compat.py"),
        "--check",
        "--project-root",
        str(target_root),
    ]
    if requested:
        command.extend(["--cli", ",".join(requested)])
    env = dict(os.environ)
    current_version = INSTALL.read_project_trellis_version(target_root)
    if current_version:
        env["TRELLIS_LATEST_VERSION"] = current_version
    result = subprocess.run(
        command,
        cwd=target_root,
        text=True,
        capture_output=True,
        check=False,
        env=env,
    )
    output = "\n".join(part for part in [result.stdout.strip(), result.stderr.strip()] if part).strip()
    return result.returncode == 0, output


def detect_state(project_root: Path, requested: list[str] | None) -> dict[str, object]:
    commands_root = Path(__file__).resolve().parent
    workflow_root = commands_root.parent
    workflow_spec_path = workflow_root / "工作流嵌入执行规范.md"
    project_root = project_root.resolve()

    blockers: list[str] = []
    try:
        cli_types = INSTALL.detect_cli_types(project_root, requested)
    except SystemExit as exc:
        cli_types = requested or []
        blockers.append(str(exc))

    prereq_ok = False
    try:
        INSTALL.ensure_project_prereqs(project_root)
        prereq_ok = True
    except SystemExit as exc:
        blockers.append(str(exc))

    traces = INSTALL.collect_workflow_embed_traces(commands_root, project_root, cli_types)

    status = INSTALL._EMBED_STATE_BLOCKED
    validation_ok = False
    validation_output = ""
    attempt_details: dict[str, object] | None = None

    if prereq_ok and not traces:
        status = INSTALL._EMBED_STATE_INITIAL
    elif traces:
        attempt_record = INSTALL.embed_attempt_record_path(project_root)
        if attempt_record.exists():
            try:
                attempt_details = json.loads(attempt_record.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, UnicodeDecodeError):
                attempt_details = {"status": "unknown", "error": "attempt record unreadable"}
            blockers.append("检测到 workflow-embed-attempt.json，说明目标项目存在未完成或失败的历史嵌入尝试。")
            if attempt_details.get("status"):
                blockers.append(f"attempt status: {attempt_details['status']}")
            if attempt_details.get("last_step"):
                blockers.append(f"attempt last_step: {attempt_details['last_step']}")
            if attempt_details.get("error"):
                blockers.append(f"attempt error: {attempt_details['error']}")
        else:
            validation_ok, validation_output = _run_upgrade_check(commands_root, project_root, requested)
            if validation_ok:
                status = INSTALL._EMBED_STATE_VALID
            else:
                blockers.append("检测到当前 workflow 的历史嵌入痕迹，但未通过完整有效性校验。")
                if validation_output:
                    blockers.append(validation_output)

    if status == INSTALL._EMBED_STATE_BLOCKED and not blockers:
        blockers.append("目标项目不满足首次嵌入所需的初始态门禁。")

    return {
        "status": status,
        "target_project_root": str(project_root),
        "workflow_spec_path": str(workflow_spec_path),
        "workflow_root": str(workflow_root),
        "cli_types": cli_types,
        "traces": traces,
        "blockers": blockers,
        "upgrade_check_passed": validation_ok,
        "attempt_details": attempt_details,
    }


def print_human(report: dict[str, object]) -> None:
    print("## Workflow Embed Status")
    print()
    print(f"- Target project: {report['target_project_root']}")
    print(f"- Workflow spec: {report['workflow_spec_path']}")
    print(f"- Workflow root: {report['workflow_root']}")
    print(f"- Status: {report['status']}")
    if report["cli_types"]:
        print(f"- CLI types: {', '.join(report['cli_types'])}")
    print()
    print("### Traces")
    traces = report["traces"]
    if traces:
        for trace in traces:
            print(f"- {trace}")
    else:
        print("- none")
    print()
    print("### Blockers")
    blockers = report["blockers"]
    if blockers:
        for blocker in blockers:
            print(f"- {blocker}")
    else:
        print("- none")
    print()
    print("### Attempt Details")
    attempt_details = report["attempt_details"]
    if attempt_details:
        for key, value in attempt_details.items():
            print(f"- {key}: {value}")
    else:
        print("- none")
    print()
    print("### Conclusion")
    status = report["status"]
    if status == INSTALL._EMBED_STATE_INITIAL:
        print("- 当前项目处于纯净初始态，可以执行首次完整嵌入。")
    elif status == INSTALL._EMBED_STATE_VALID:
        print("- 当前项目已完整有效嵌入本 workflow，不应重复执行嵌入。")
    else:
        print("- 当前项目不是允许首次嵌入的初始态。必须停止后续嵌入操作，并由用户手动处理。")


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    requested = _normalize_requested(args.cli)
    report = detect_state(args.project_root, requested)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print_human(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
