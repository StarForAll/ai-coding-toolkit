#!/usr/bin/env python3
"""Validate and optionally repair protected source watermark snippets."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path


PROTECTED_SOURCES = (
    "design/source-watermark-plan.md",
    "source-watermark-plan.md",
)


@dataclass
class ProtectedSnippet:
    path: str
    snippet_id: str
    expected_text: str
    repair_mode: str
    insertion_hint: str | None
    notes: str | None


@dataclass
class Finding:
    level: str
    code: str
    message: str
    path: str | None = None
    snippet_id: str | None = None
    repaired: bool = False

    def as_dict(self) -> dict[str, object]:
        return {
            "level": self.level,
            "code": self.code,
            "message": self.message,
            "path": self.path,
            "snippet_id": self.snippet_id,
            "repaired": self.repaired,
        }


def print_human(findings: list[Finding]) -> None:
    if not findings:
        print("PASS: no watermark preservation issues found")
        return
    for finding in findings:
        suffix = []
        if finding.path:
            suffix.append(f"path={finding.path}")
        if finding.snippet_id:
            suffix.append(f"snippet={finding.snippet_id}")
        if finding.repaired:
            suffix.append("repaired=yes")
        details = f" ({', '.join(suffix)})" if suffix else ""
        print(f"{finding.level}: {finding.code}: {finding.message}{details}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="验证并可选修复源码水印保护片段")
    parser.add_argument("--task-dir", required=True, help="任务目录或项目根目录")
    parser.add_argument(
        "--mode",
        choices=["check", "repair"],
        default="check",
        help="只检查或执行受控自动修复",
    )
    parser.add_argument("--json", action="store_true", help="Emit output as JSON")
    parser.add_argument("--strict-warnings", action="store_true", help="Treat warnings as exit code 2")
    return parser


def load_plan(task_dir: Path) -> tuple[Path, str]:
    for rel_path in PROTECTED_SOURCES:
        candidate = task_dir / rel_path
        if candidate.exists():
            return candidate, candidate.read_text(encoding="utf-8")
    raise FileNotFoundError("未找到 `design/source-watermark-plan.md` 或 `source-watermark-plan.md`")


def extract_section(content: str, heading: str) -> str:
    lines = content.splitlines()
    capture = False
    collected: list[str] = []
    target = heading.lower().strip()
    for line in lines:
        normalized = line.strip().lower()
        if normalized.startswith("## "):
            if capture:
                break
            capture = normalized == target
            continue
        if capture:
            collected.append(line)
    return "\n".join(collected).strip()


def parse_protected_snippets(content: str) -> list[ProtectedSnippet]:
    section = extract_section(content, "## Protected Watermark Snippets")
    if not section:
        return []
    entries: list[ProtectedSnippet] = []
    current: dict[str, str] = {}
    current_path: str | None = None
    for raw_line in section.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith("### "):
            if current_path is not None:
                entries.append(build_entry(current_path, current))
            current_path = line[4:].strip().strip("`")
            current = {}
            continue
        if line.startswith("- ") and ":" in line:
            key, value = line[2:].split(":", 1)
            normalized_key = key.strip().strip("`").lower()
            current[normalized_key] = value.strip().strip("`")
    if current_path is not None:
        entries.append(build_entry(current_path, current))
    return entries


def build_entry(path_value: str, fields: dict[str, str]) -> ProtectedSnippet:
    snippet_id = fields.get("id")
    expected_text = fields.get("expected")
    repair_mode = fields.get("repair")
    if not snippet_id or not expected_text or not repair_mode:
        missing = [name for name in ("id", "expected", "repair") if not fields.get(name)]
        raise ValueError(f"Protected watermark snippet `{path_value}` 缺少字段: {', '.join(missing)}")
    return ProtectedSnippet(
        path=path_value,
        snippet_id=snippet_id,
        expected_text=expected_text,
        repair_mode=repair_mode,
        insertion_hint=fields.get("insert-after"),
        notes=fields.get("notes"),
    )


def apply_repair(target_path: Path, snippet: ProtectedSnippet) -> bool:
    content = target_path.read_text(encoding="utf-8")
    if snippet.expected_text in content:
        return False
    if snippet.repair_mode == "replace-if-missing":
        if not snippet.insertion_hint or snippet.insertion_hint not in content:
            raise ValueError(
                f"`{snippet.path}` 中缺少 insert-after 锚点 `{snippet.insertion_hint}`，无法自动修复片段 `{snippet.snippet_id}`"
            )
        updated = content.replace(snippet.insertion_hint, f"{snippet.insertion_hint}\n{snippet.expected_text}", 1)
        target_path.write_text(updated, encoding="utf-8")
        return True
    raise ValueError(
        f"片段 `{snippet.snippet_id}` 的 repair 模式 `{snippet.repair_mode}` 不是当前支持的自动修复模式"
    )


def evaluate_snippets(task_dir: Path, snippets: list[ProtectedSnippet], mode: str) -> list[Finding]:
    findings: list[Finding] = []
    for snippet in snippets:
        target = task_dir / snippet.path
        rel_path = snippet.path
        if not target.exists():
            findings.append(
                Finding(
                    level="ERROR",
                    code="missing-protected-file",
                    message="受保护的源码文件不存在",
                    path=rel_path,
                    snippet_id=snippet.snippet_id,
                )
            )
            continue
        content = target.read_text(encoding="utf-8")
        if snippet.expected_text in content:
            continue
        if mode == "repair":
            try:
                repaired = apply_repair(target, snippet)
            except ValueError as exc:
                findings.append(
                    Finding(
                        level="ERROR",
                        code="watermark-repair-blocked",
                        message=str(exc),
                        path=rel_path,
                        snippet_id=snippet.snippet_id,
                    )
                )
                continue
            findings.append(
                Finding(
                    level="WARN" if repaired else "INFO",
                    code="watermark-repaired" if repaired else "watermark-already-present",
                    message="已自动修复缺失的受保护水印片段" if repaired else "片段已存在，无需修复",
                    path=rel_path,
                    snippet_id=snippet.snippet_id,
                    repaired=repaired,
                )
            )
        else:
            findings.append(
                Finding(
                    level="ERROR",
                    code="watermark-preservation-broken",
                    message="受保护水印片段已缺失或被改写",
                    path=rel_path,
                    snippet_id=snippet.snippet_id,
                )
            )
    return findings


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    task_dir = Path(args.task_dir)
    if not task_dir.exists():
        print(f"路径不存在: {task_dir}", file=sys.stderr)
        return 1
    try:
        _, plan_content = load_plan(task_dir)
        snippets = parse_protected_snippets(plan_content)
    except (FileNotFoundError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    if not snippets:
        findings = [
            Finding(
                level="WARN",
                code="missing-protected-snippets",
                message="source-watermark-plan.md 未声明受保护水印片段，无法执行保持/修复检查",
            )
        ]
    else:
        findings = evaluate_snippets(task_dir, snippets, args.mode)

    if args.json:
        print(json.dumps([finding.as_dict() for finding in findings], ensure_ascii=False, indent=2))
    else:
        print_human(findings)

    errors = sum(1 for finding in findings if finding.level == "ERROR")
    warnings = sum(1 for finding in findings if finding.level == "WARN")
    if errors:
        return 1
    if warnings and args.strict_warnings:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
