"""templates.py — 模板占位标记集（机制稿 §2.3、§10.2）。

只检查模板声明的待填位置；讨论这些标记的普通正文不是使用位点。
"""

from __future__ import annotations

import json
import re

MARKER_PATTERN = re.compile(r"\{\{WF_REQUIRED:([A-Za-z0-9_-]+)\}\}")
VALUE_MARKER = "__WF_REQUIRED__"

FORMATS = [
    {"id": "required-field", "pattern": "{{WF_REQUIRED:<field>}}"},
    {"id": "required-value", "pattern": "__WF_REQUIRED__"},
]


class TemplateError(Exception):
    pass


def find_markers(text: str) -> list:
    """返回 [(field, offset)]；同一 field 多次出现按多次登记。"""
    return [(match.group(1), match.start()) for match in MARKER_PATTERN.finditer(text)]


def find_value_markers(value, pointer="") -> list:
    """JSON 值中已知必填字段的字符串 `__WF_REQUIRED__`。"""
    found = []
    if isinstance(value, dict):
        for key, item in value.items():
            found.extend(find_value_markers(item, f"{pointer}/{key}"))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            found.extend(find_value_markers(item, f"{pointer}/{index}"))
    elif isinstance(value, str) and VALUE_MARKER in value:
        found.append(pointer or "/")
    return found


def marker_uses(path: str, text: str, *, json_targets=()) -> list:
    """生成该模板实际使用的占位位点（供清单 template_markers.uses 双向核对）。"""
    uses = []
    for field, _offset in find_markers(text):
        uses.append(
            {
                "template_path": path,
                "selector": {"kind": "markdown_marker", "value": f"{{{{WF_REQUIRED:{field}}}}}"},
                "format_id": "required-field",
                "required": True,
            }
        )
    return uses


def check_markers(path, text, *, allow_any=False) -> list:
    """模板必填位是否仍待填；返回 violation 列表（空 = 通过）。"""
    violations = []
    for field, _offset in find_markers(text):
        violations.append({"template": path, "field": field, "kind": "required-field"})
    return violations


def json_value_marker_violations(path, value) -> list:
    return [{"template": path, "pointer": pointer, "kind": "required-value"} for pointer in find_value_markers(value)]


def load_template_json(path):
    import pathlib

    data = pathlib.Path(path).read_text(encoding="utf-8")
    try:
        return json.loads(data), data
    except ValueError as exc:
        raise TemplateError(f"template is not valid JSON: {path}: {exc}") from exc


def double_check(template_text: str, uses) -> list:
    """自检：uses 与模板实际占位标记双向核对，漏登记/悬空即拒。"""
    actual = {f"{{{{WF_REQUIRED:{field}}}}}" for field, _ in find_markers(template_text)}
    declared = {
        use["selector"]["value"]
        for use in uses
        if isinstance(use.get("selector"), dict) and use["selector"].get("kind") == "markdown_marker"
    }
    problems = []
    for marker in sorted(actual - declared):
        problems.append(f"unregistered marker: {marker}")
    for marker in sorted(declared - actual):
        problems.append(f"dangling use: {marker}")
    return problems
