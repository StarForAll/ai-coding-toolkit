#!/usr/bin/env python3
"""Shared helper utilities for workflow shell scripts."""

from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path


MIN_KICKOFF_PAYMENT_RATIO = 30.0
PLACEHOLDER_MARKERS = ("待补充", "待定", "暂空", "后续补充", "TBD", "TODO", "FIXME", "...")
TRUE_VALUES = {"yes", "true", "on", "1", "是"}
FALSE_VALUES = {"no", "false", "off", "0", "否"}


def extract_backticked_field(content: str, field_name: str) -> str | None:
    """Extract a markdown field formatted like `field`: `value`."""
    match = re.search(rf'`{re.escape(field_name)}`:\s*`?(.+?)`?(?:\n|$)', content)
    if not match:
        return None
    value = match.group(1).strip()
    return value or None


def extract_markdown_field(content: str, field_name: str) -> str | None:
    """Extract a markdown list-style field value, with or without backticks."""
    pattern = re.compile(
        rf"(?:`)?{re.escape(field_name)}(?:`)?\s*:\s*(.+?)(?:\n|$)",
        re.IGNORECASE,
    )
    match = pattern.search(content)
    if not match:
        return None
    value = match.group(1).strip().strip("`").strip()
    return value or None


def normalize_yes_no_field(value: str | None) -> bool | None:
    """Normalize a yes/no-like field to bool, returning None for invalid input."""
    if value is None:
        return None
    lowered = value.strip().strip("`").lower()
    if lowered in TRUE_VALUES:
        return True
    if lowered in FALSE_VALUES:
        return False
    return None


def parse_channels(raw: str | None) -> set[str]:
    """Parse comma-separated channel names into the normalized internal set."""
    if not raw:
        return set()
    parts = re.split(r"[,\uFF0C/\s]+", raw.lower())
    channels = {part for part in parts if part}
    normalized = set()
    for channel in channels:
        if channel in {"visible", "可见", "可见水印", "comment", "comments"}:
            normalized.add("visible")
        elif channel in {"zero-width", "zero", "zw", "零宽", "zero_width"}:
            normalized.add("zero-width")
        elif channel in {"subtle", "subtle-marker", "subtle-markers", "marker", "markers", "隐蔽", "不起眼"}:
            normalized.add("subtle-markers")
        elif channel in {"zero-watermark", "zero-watermarks", "fingerprint", "fingerprints", "零水印", "指纹"}:
            normalized.add("zero-watermark")
        else:
            normalized.add(channel)
    return normalized


def is_placeholder_like(text: str | None) -> bool:
    """Return True when text is empty or still a placeholder-style value."""
    if text is None:
        return True
    normalized = text.strip().lstrip("-").strip().strip("`*_ \t\r\n")
    if not normalized:
        return True
    lowered = normalized.lower()
    for marker in PLACEHOLDER_MARKERS:
        lowered_marker = marker.lower()
        if not lowered.startswith(lowered_marker):
            continue
        if len(lowered) == len(lowered_marker):
            return True
        next_char = normalized[len(marker)]
        if next_char.isspace():
            return True
        if unicodedata.category(next_char).startswith("P"):
            return True
    return normalized in {"...", ".", "例如"}


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
