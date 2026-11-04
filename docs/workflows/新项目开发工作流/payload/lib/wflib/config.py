"""config.py — 项目配置与执行器确认记录（机制稿 §8.1、§8.2）。

本模块只读取与校验，不替人写确认记录、不做执行器匹配判定（匹配在引导层）。
"""

from __future__ import annotations

import os
import re

from . import records
from .paths import join

PROJECT_CONFIG_REL = ".wf/project-config.json"
GLOBAL_CONFIG_REL = (".wf", "config.json")
CONFIRMATIONS_REL = (".wf", "interpreters.json")
PROJECT_ID_RE = re.compile(r"^[0-9a-f]{32}$")

DEFAULTS = {
    "tdd_default": False,
    "review_file_hint": 3,
    "review_line_hint": 80,
    "split_file_hint": 8,
    "split_line_hint": 400,
    "merge_line_hint": 10,
    "debug_repeat_threshold": 3,
    "spec_verify_days": 90,
    "spec_reclaim_tasks": 5,
    "inspection_every_tasks": 10,
    "spec_output_codepoints": 12000,
}

POSITIVE_INT_KEYS = (
    "review_file_hint",
    "review_line_hint",
    "split_file_hint",
    "split_line_hint",
    "merge_line_hint",
    "debug_repeat_threshold",
    "spec_verify_days",
    "spec_reclaim_tasks",
    "inspection_every_tasks",
    "spec_output_codepoints",
)

KNOWN_KEYS = set(DEFAULTS) | {"schema_version", "project_id", "python_executable"}


class ConfigError(Exception):
    pass


def skeleton():
    """发行骨架：缺省值齐全，不含 project_id 与 python_executable 的值。"""
    payload = {"schema_version": 1, "project_id": None}
    payload.update(DEFAULTS)
    return payload


def path_of(root):
    return join(root, PROJECT_CONFIG_REL)


def load_project_config(root, *, allow_missing=False):
    """返回 (config, problems)。problems 非空时依赖这些键的判断应局部阻断。"""
    raw = records.load_json(path_of(root))
    if raw is None:
        if allow_missing:
            return None, []
        return None, [{"level": "structure", "key": None,
                       "message": "missing project config: .wf/project-config.json"}]
    if not isinstance(raw, dict):
        return None, [{"level": "structure", "key": None,
                       "message": "project config is not a JSON object"}]
    # problem 分两级：structure 约束相关配置解释；field 只影响依赖该键的判断（设计稿 §3）
    problems = []
    config = dict(raw)
    if config.get("schema_version") != 1:
        problems.append({"level": "structure", "key": "schema_version",
                         "message": f"unsupported schema_version: {config.get('schema_version')!r}"})
    project_id = config.get("project_id")
    if project_id is not None and not (isinstance(project_id, str) and PROJECT_ID_RE.match(project_id)):
        problems.append({"level": "field", "key": "project_id", "message": "project_id is not a UUID4 hex"})
    for key in POSITIVE_INT_KEYS:
        if key in config:
            value = config[key]
            if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
                problems.append({"level": "field", "key": key, "message": f"{key} must be a positive integer"})
    if "tdd_default" in config and not isinstance(config["tdd_default"], bool):
        problems.append({"level": "field", "key": "tdd_default", "message": "tdd_default must be a boolean"})
    executable = config.get("python_executable")
    if executable is not None:
        if not isinstance(executable, str) or executable == "":
            problems.append({"level": "field", "key": "python_executable",
                             "message": "python_executable must be a non-empty string when set"})
    return config, problems


def value_of(config, problems, key):
    """统一取值：键缺失→发行缺省；键或结构非法→(None, problem)；合法→(值, None)。

    structure 级问题约束所有相关键的解释；field 级只影响它自己的键（设计稿 §3）。
    """
    if key not in DEFAULTS:
        raise ConfigError(f"no default for key: {key}")
    items = list(problems or [])
    structural = [item for item in items if item.get("level") == "structure"]
    own = [item for item in items if item.get("key") == key and item.get("level") != "structure"]
    if not isinstance(config, dict):
        if structural:
            return None, structural[0]["message"]
        if config is None and not items:
            return DEFAULTS[key], None  # 配置文件缺失且允许缺失：取发行缺省
        return None, f"{key} unusable: project config is not readable"
    if own:
        return None, own[0]["message"]
    if key not in config:
        if structural:
            return None, structural[0]["message"]
        return DEFAULTS[key], None
    if structural:
        return None, structural[0]["message"]
    value = config.get(key)
    default = DEFAULTS[key]
    if isinstance(default, bool):
        if not isinstance(value, bool):
            return None, f"{key} must be a boolean"
        return value, None
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        return None, f"{key} must be a positive integer"
    return value, None


def effective(config, key):
    """项目键缺省取发行缺省；非法/未知不静默当无限。"""
    if config and key in config:
        return config[key]
    if key in DEFAULTS:
        return DEFAULTS[key]
    raise ConfigError(f"no default for key: {key}")


def user_dir():
    return os.path.join(os.path.expanduser("~"), GLOBAL_CONFIG_REL[0])


def global_config_path():
    return os.path.join(user_dir(), GLOBAL_CONFIG_REL[1])


def confirmations_path():
    return os.path.join(user_dir(), CONFIRMATIONS_REL[1])


def load_global_config():
    """缺失=未设置；非法按配置错误上报（不是回退）。"""
    path = global_config_path()
    raw = records.load_json(path)
    if raw is None:
        return None, []
    if not isinstance(raw, dict):
        return None, ["global config is not a JSON object"]
    problems = []
    if raw.get("schema_version") != 1:
        problems.append("unsupported global config schema_version")
    executable = raw.get("python_executable")
    if executable is not None and (not isinstance(executable, str) or not os.path.isabs(executable)):
        problems.append("global python_executable must be an absolute path")
    return raw, problems


def load_confirmations():
    path = confirmations_path()
    raw = records.load_json(path)
    if raw is None:
        return []
    if isinstance(raw, dict):
        raw = raw.get("interpreters")
    if not isinstance(raw, list):
        return []
    return [entry for entry in raw if isinstance(entry, dict)]


def project_python_key(root, config):
    """项目键的显示形态与解析形态（不变换变量，不接 shell）。"""
    value = (config or {}).get("python_executable")
    return value
