"""config.py — 项目配置与执行器确认记录（机制稿 §8.1、§8.2）。

本模块只读取与校验，不替人写确认记录、不做执行器匹配判定（匹配在引导层）。
"""

from __future__ import annotations

import os
import re

from . import protocol as protocol_mod
from . import records
from .paths import join

PROJECT_CONFIG_REL = ".wf/project-config.json"
GLOBAL_CONFIG_REL = (".wf", "config.json")
CONFIRMATIONS_REL = (".wf", "interpreters.json")
PROJECT_ID_RE = re.compile(r"^[0-9a-f]{32}$")

# 阈值缺省与类型不在本模块：唯一存放处是 `protocol/thresholds.json`（机制稿 §8.1）。
_THRESHOLDS = protocol_mod.thresholds()
CONFIG_SCHEMA_VERSION = _THRESHOLDS["schema_version"]["default"]
DEFAULTS = {
    name: entry["default"]
    for name, entry in _THRESHOLDS.items()
    if entry.get("in_skeleton") and name != "schema_version"
}
POSITIVE_INT_KEYS = tuple(name for name, entry in _THRESHOLDS.items() if entry.get("type") == "positive_int")
# 取值为 0 表示"不设上界"的键：其余整型键仍要求正整数（机制稿 §8.1）
ZERO_ALLOWED_KEYS = tuple(name for name, entry in _THRESHOLDS.items() if entry.get("type") == "int_zero_unbounded")
ENUM_KEYS = {name: tuple(entry.get("values") or ()) for name, entry in _THRESHOLDS.items() if entry.get("type") == "enum"}
KNOWN_KEYS = set(_THRESHOLDS)


class ConfigError(Exception):
    pass


def skeleton():
    """发行骨架：缺省值齐全；不含 project_id 与 python_executable 的键。

    `project_id` 由初始化/接入生成后才写入（机制稿 §8.1「不在骨架给值」），
    `python_executable` 未设置即回落系统 python3；两者都保留已知键名以便校验放行。
    """
    payload = {"schema_version": CONFIG_SCHEMA_VERSION}
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
    for key in ZERO_ALLOWED_KEYS:
        if key in config:
            value = config[key]
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                problems.append({"level": "field", "key": key,
                                 "message": f"{key} must be an integer >= 0 (0 = no upper bound)"})
    for key, allowed in ENUM_KEYS.items():
        if key in config and config[key] not in allowed:
            problems.append({"level": "field", "key": key,
                             "message": f"{key} must be one of {list(allowed)}"})
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
    if key in ENUM_KEYS:
        if value not in ENUM_KEYS[key]:
            return None, f"{key} must be one of {list(ENUM_KEYS[key])}"
        return value, None
    if isinstance(value, bool) or not isinstance(value, int):
        return None, f"{key} must be an integer"
    if value < 0 or (value == 0 and key not in ZERO_ALLOWED_KEYS):
        return None, (f"{key} must be an integer >= 0 (0 = no upper bound)"
                      if key in ZERO_ALLOWED_KEYS else f"{key} must be a positive integer")
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
