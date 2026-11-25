"""Project location, installation record and version comparison.

The system command runs from the project root or from an arbitrary directory. Project discovery
walks upward for `.wf/`; an explicit `--project` always wins and must be an absolute path.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass

from .version import VERSION_RE

INSTALLATION_REL = os.path.join(".wf", "install", "installation.json")
BOOTSTRAP_REL = os.path.join(".wf", "bin", "wf.py")


class ProjectError(Exception):
    def __init__(self, code, message, facts=None, exit_hint=None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.facts = facts or {}
        self.exit_hint = exit_hint


@dataclass
class Project:
    root: str
    installation: dict | None

    @property
    def installed_version(self):
        if not isinstance(self.installation, dict):
            return None
        value = self.installation.get("version")
        return str(value) if value is not None else None


def normalize_project(path):
    """Return an existing absolute directory; never guess from a relative value."""
    if not path or not os.path.isabs(path):
        raise ProjectError("WF_PATH_INVALID", "--project 必须是已存在的绝对路径",
                           {"project": path}, "用项目根绝对路径重试；不从 cwd 猜相对值")
    real = os.path.realpath(path)
    if not os.path.isdir(real):
        raise ProjectError("WF_PATH_INVALID", "--project 指向的目录不存在",
                           {"project": path, "resolved": real}, "核对项目路径后重试")
    return real


def is_project(path):
    return (
        os.path.isfile(os.path.join(path, BOOTSTRAP_REL))
        or os.path.isfile(os.path.join(path, INSTALLATION_REL))
    )


def discover_project(start=None):
    current = os.path.realpath(start or os.getcwd())
    if not os.path.isdir(current):
        raise ProjectError("WF_PATH_INVALID", "起始目录不存在", {"start": current},
                           "在项目目录内运行，或给出 --project 绝对路径")
    while True:
        if is_project(current):
            return current
        parent = os.path.dirname(current)
        if parent == current:
            return None
        current = parent


def load_installation(project):
    path = os.path.join(project, INSTALLATION_REL)
    if not os.path.isfile(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as handle:
            record = json.load(handle)
    except (OSError, ValueError) as exc:
        raise ProjectError("WF_RECORD_INVALID", "安装记录不可解析：先修复记录，不按目录形状猜版本",
                           {"path": path, "detail": str(exc)},
                           "运行已安装的 repair 入口核对记录后再重试") from exc
    if not isinstance(record, dict):
        raise ProjectError("WF_RECORD_INVALID", "安装记录不是 JSON 对象",
                           {"path": path}, "运行已安装的 repair 入口核对记录后再重试")
    return record


def open_project(path=None, *, require=False):
    """Resolve an explicit or discovered project. ``require`` makes discovery mandatory."""
    if path is not None:
        root = normalize_project(path)
    else:
        root = discover_project()
        if root is None:
            if require:
                raise ProjectError("WF_PATH_INVALID", "不在 wf 项目内",
                                   {"cwd": os.getcwd()},
                                   "在项目根运行，或给出 --project <绝对路径>")
            return None
    installation = load_installation(root)
    return Project(root=root, installation=installation)


def installed_version(project):
    value = project.installed_version
    if value is None:
        return None
    if not VERSION_RE.match(value):
        raise ProjectError("WF_RECORD_INVALID", "安装记录的版本不是 X.Y.Z",
                           {"version": value, "path": os.path.join(project.root, INSTALLATION_REL)},
                           "运行 repair 入口核对安装记录；不用猜测的版本继续")
    return value