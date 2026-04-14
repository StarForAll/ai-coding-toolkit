#!/usr/bin/env python3
"""Run record-session with metadata closure checks and resume support."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path


READONLY_HINTS = [
    "Read-only file system",
    "只读文件系统",
    "只读文件系统",
    "Permission denied",
    "Operation not permitted",
    ".git/index.lock",
    "cannot create",
    "不能创建",
]


def find_project_root(start: Path) -> Path:
    current = start.resolve()
    if current.is_file():
        current = current.parent
    for candidate in [current, *current.parents]:
        if (candidate / ".trellis").exists() or (candidate / ".git").exists():
            return candidate
    raise SystemExit("未找到项目根目录，请使用 --project-root 指定")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="执行 record-session 并校验元数据闭环")
    parser.add_argument("--title", help="会话标题")
    parser.add_argument("--commit", default="-", help="Git commit hash，可多个逗号分隔")
    parser.add_argument("--summary", default="(Add summary)", help="会话摘要")
    parser.add_argument("--content-file", help="包含详细内容的文件路径")
    parser.add_argument("--package", help="包名标签（若项目支持）")
    parser.add_argument("--branch", help="分支名（可选）")
    parser.add_argument("--stdin", action="store_true", help="从 stdin 读取详细内容")
    parser.add_argument("--project-root", type=Path, default=None, help="项目根目录（默认自动检测）")
    parser.add_argument("--resume", type=Path, help="从 pending state 恢复 metadata commit-only 流程")
    return parser


def run_step(
    cmd: list[str],
    *,
    cwd: Path,
    step_name: str,
    input_text: str | None = None,
) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        cmd,
        cwd=cwd,
        input=input_text,
        text=True,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if result.stdout:
        print(result.stdout, end="")
    if result.stderr:
        print(result.stderr, end="", file=sys.stderr)
    if result.returncode != 0:
        print(f"❌ {step_name} 失败", file=sys.stderr)
    return result


def sanitize_title(value: str) -> str:
    cleaned = "".join(ch if ch.isalnum() or ch in "-_" else "-" for ch in value.strip())
    cleaned = "-".join(part for part in cleaned.split("-") if part)
    return cleaned or "record-session"


def detect_readonly_failure(text: str) -> bool:
    return any(hint in text for hint in READONLY_HINTS)


def load_or_capture_content(args: argparse.Namespace) -> tuple[str | None, Path | None]:
    if args.content_file:
        path = Path(args.content_file).resolve()
        return path.read_text(encoding="utf-8"), path
    if args.stdin:
        text = sys.stdin.read()
        return text, None
    return None, None


def ensure_resume_artifacts(
    repo_root: Path,
    *,
    title: str,
    commit: str,
    summary: str,
    package: str | None,
    branch: str | None,
    input_text: str | None,
) -> Path:
    pending_dir = repo_root / ".trellis" / ".pending-record-session"
    pending_dir.mkdir(parents=True, exist_ok=True)
    slug = sanitize_title(title)
    content_path: str | None = None
    if input_text is not None:
        body_file = pending_dir / f"{slug}.body.md"
        body_file.write_text(input_text, encoding="utf-8")
        content_path = str(body_file.relative_to(repo_root))
    state = {
        "title": title,
        "commit": commit,
        "summary": summary,
        "package": package,
        "branch": branch,
        "content_file": content_path,
    }
    state_file = pending_dir / f"{slug}.pending.json"
    state_file.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")
    return state_file


def print_resume_guidance(repo_root: Path, state_file: Path) -> None:
    rel = state_file.relative_to(repo_root).as_posix()
    print("", file=sys.stderr)
    print("⚠️  record-session metadata auto-commit 失败，检测到可能的只读/受限写入环境。", file=sys.stderr)
    print("请在可写环境中恢复执行 metadata commit-only 步骤：", file=sys.stderr)
    print(
        f"python3 ./.trellis/scripts/workflow/record-session-helper.py --resume {rel}",
        file=sys.stderr,
    )


def get_workspace_commit_message(repo_root: Path) -> str:
    config_path = repo_root / ".trellis" / "config.yaml"
    if not config_path.is_file():
        return "chore: record journal"
    content = config_path.read_text(encoding="utf-8")
    for line in content.splitlines():
        if line.strip().startswith("session_commit_message:"):
            _, value = line.split(":", 1)
            value = value.strip().strip("\"'")
            if value:
                return value
    return "chore: record journal"


def build_add_session_cmd(args: argparse.Namespace, repo_root: Path) -> list[str]:
    add_session_script = repo_root / ".trellis" / "scripts" / "add_session.py"
    cmd = [
        sys.executable,
        str(add_session_script),
        "--title",
        args.title,
        "--commit",
        args.commit,
        "--summary",
        args.summary,
        "--no-commit",
    ]
    if args.content_file:
        cmd.extend(["--content-file", args.content_file])
    if args.package:
        cmd.extend(["--package", args.package])
    if args.branch:
        cmd.extend(["--branch", args.branch])
    if args.stdin:
        cmd.append("--stdin")
    return cmd


def resume_from_state(state_file: Path, repo_root: Path) -> int:
    state = json.loads(state_file.read_text(encoding="utf-8"))
    script_dir = Path(__file__).resolve().parent
    guard_script = script_dir / "metadata-autocommit-guard.py"
    commit_msg = get_workspace_commit_message(repo_root)

    commit_result = run_step(
        [
            sys.executable,
            str(guard_script),
            "--mode",
            "record-session",
            "--project-root",
            str(repo_root),
            "--commit-message",
            commit_msg,
        ],
        cwd=repo_root,
        step_name="metadata commit-only",
    )
    if commit_result.returncode != 0:
        print("record-session incomplete", file=sys.stderr)
        return 1

    post_result = run_step(
        [
            sys.executable,
            str(guard_script),
            "--mode",
            "record-session",
            "--check",
            "post",
            "--project-root",
            str(repo_root),
        ],
        cwd=repo_root,
        step_name="record-session post-check",
    )
    if post_result.returncode != 0:
        print("record-session incomplete", file=sys.stderr)
        return 1

    state_file.unlink(missing_ok=True)
    content_file = state.get("content_file")
    if content_file:
        (repo_root / content_file).unlink(missing_ok=True)
    print("✅ record-session resumed and completed")
    return 0


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    repo_root = args.project_root.resolve() if args.project_root else find_project_root(Path.cwd())

    if args.resume:
        state_file = args.resume.resolve() if args.resume.is_absolute() else (repo_root / args.resume)
        return resume_from_state(state_file, repo_root)

    if not args.title:
        parser.error("--title is required unless using --resume")

    script_dir = Path(__file__).resolve().parent
    guard_script = script_dir / "metadata-autocommit-guard.py"
    input_text, content_path = load_or_capture_content(args)

    print("========================================")
    print("record-session metadata closure")
    print("========================================")

    pre_result = run_step(
        [
            sys.executable,
            str(guard_script),
            "--mode",
            "record-session",
            "--check",
            "pre",
            "--project-root",
            str(repo_root),
        ],
        cwd=repo_root,
        step_name="record-session pre-check",
    )
    if pre_result.returncode != 0:
        print("record-session incomplete", file=sys.stderr)
        return 1

    add_session_result = run_step(
        build_add_session_cmd(args, repo_root),
        cwd=repo_root,
        step_name="add_session.py",
        input_text=input_text,
    )
    if add_session_result.returncode != 0:
        print("record-session incomplete", file=sys.stderr)
        return 1

    commit_msg = get_workspace_commit_message(repo_root)
    commit_result = run_step(
        [
            sys.executable,
            str(guard_script),
            "--mode",
            "record-session",
            "--project-root",
            str(repo_root),
            "--commit-message",
            commit_msg,
        ],
        cwd=repo_root,
        step_name="metadata commit-only",
    )
    if commit_result.returncode != 0:
        combined = (commit_result.stdout or "") + "\n" + (commit_result.stderr or "")
        if detect_readonly_failure(combined):
            state_file = ensure_resume_artifacts(
                repo_root,
                title=args.title,
                commit=args.commit,
                summary=args.summary,
                package=args.package,
                branch=args.branch,
                input_text=input_text if content_path is None else None,
            )
            print_resume_guidance(repo_root, state_file)
        print("record-session incomplete", file=sys.stderr)
        return 1

    post_result = run_step(
        [
            sys.executable,
            str(guard_script),
            "--mode",
            "record-session",
            "--check",
            "post",
            "--project-root",
            str(repo_root),
        ],
        cwd=repo_root,
        step_name="record-session post-check",
    )
    if post_result.returncode != 0:
        print("record-session incomplete", file=sys.stderr)
        return 1

    print("✅ record-session completed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
