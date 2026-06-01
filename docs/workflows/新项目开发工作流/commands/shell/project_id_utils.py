#!/usr/bin/env python3
"""Project-id validation helpers shared by workflow install/runtime entrypoints."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


INSTALL_RECORD = ".trellis/workflow-installed.json"
PROJECT_ID_RE = re.compile(r"^[A-Za-z](?:[A-Za-z0-9:_-]*[A-Za-z])?$")


def read_json(path: Path) -> dict[str, Any] | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None
    except json.JSONDecodeError:
        return None
    if not isinstance(data, dict):
        return None
    return data


def find_repo_root(start: Path) -> Path | None:
    current = start.resolve()
    if current.is_file():
        current = current.parent
    while current != current.parent:
        if (current / ".trellis").is_dir():
            return current
        current = current.parent
    return None


def normalize_project_id(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    project_id = value.strip()
    if not project_id:
        return None
    if not PROJECT_ID_RE.fullmatch(project_id):
        return None
    return project_id


def installed_workflow_project_id(repo_root: Path) -> str | None:
    install_record = read_json(repo_root / INSTALL_RECORD)
    if not isinstance(install_record, dict):
        return None
    return normalize_project_id(install_record.get("project_id"))


def workflow_install_record_exists(repo_root: Path | None) -> bool:
    return repo_root is not None and (repo_root / INSTALL_RECORD).is_file()


def require_installed_project_id(repo_root: Path, operation_label: str = "workflow operation") -> str:
    project_id = installed_workflow_project_id(repo_root)
    if project_id is None:
        raise RuntimeError(
            f"{operation_label} 被禁止：{INSTALL_RECORD} 缺少有效 project_id。"
            "新项目首次嵌入 workflow 时必须传入 --project-id；"
            "project_id 需 strip() 后非空，首尾为英文字母，"
            "非首尾字符仅允许英文字母、数字、冒号、连字符和下划线。"
            " 若这是旧项目升级后的记录，请重新嵌入 workflow 或人工修正安装记录。"
        )
    return project_id
