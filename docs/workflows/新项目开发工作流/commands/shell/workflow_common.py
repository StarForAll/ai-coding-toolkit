#!/usr/bin/env python3
"""Shared helper utilities for workflow shell scripts."""

from __future__ import annotations

import json
import re
from pathlib import Path


MIN_KICKOFF_PAYMENT_RATIO = 30.0
PLACEHOLDER_MARKERS = ("待补充", "待定", "暂空", "后续补充", "TBD", "TODO", "FIXME", "...")


def extract_backticked_field(content: str, field_name: str) -> str | None:
    """Extract a markdown field formatted like `field`: `value`."""
    match = re.search(rf'`{re.escape(field_name)}`:\s*`?(.+?)`?(?:\n|$)', content)
    if not match:
        return None
    value = match.group(1).strip()
    return value or None


def find_assessment_in_lineage(task_dir: Path) -> Path:
    """Walk task lineage to find assessment.md; fall back to task_dir/assessment.md."""
    current = task_dir.resolve()
    visited: set[Path] = set()
    while current not in visited and current.is_dir():
        candidate = current / "assessment.md"
        if candidate.is_file():
            return candidate
        visited.add(current)
        task_json = current / "task.json"
        if not task_json.is_file():
            break
        try:
            data = json.loads(task_json.read_text(encoding="utf-8"))
            parent_name = data.get("parent")
            if not isinstance(parent_name, str) or not parent_name:
                break
            parent_dir = current.parent / parent_name
            if not parent_dir.is_dir():
                break
            current = parent_dir.resolve()
        except Exception:
            break
    return task_dir / "assessment.md"
