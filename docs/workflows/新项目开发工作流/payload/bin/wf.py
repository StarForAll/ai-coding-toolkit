#!/usr/bin/env python3
"""wf.py — 引导层（实现稿 §2.1、§3、机制稿 §8.2）。

固定顺序：定位目标 → 转交 repair/uninstall → confirm-executor → 执行器解析 → 移交语义层。
仅使用标准库；**不导入** wflib。
"""

from __future__ import annotations

import datetime
import json
import os
import re
import shutil
import subprocess
import sys

MIN_VERSION = (3, 11)
HOST_CONFIG_REL = (".wf", "config.json")
CONFIRM_REL = (".wf", "interpreters.json")
SCOPES = ("system", "global", "project")


def fail(code, facts, exit_hint, json_mode=False, exit_code=1, tier="blocked"):
    payload = {
        "tier": tier,
        "code": code,
        "object": None,
        "position": {
            "scope": None,
            "phase": None,
            "step_id": None,
            "task_id": None,
            "action_id": None,
            "action_state": None,
        },
        "next": exit_hint,
        "facts": facts,
        "exit": exit_hint,
        "prohibited_repairs": "不自动回退到低优先级解释器；不猜项目根",
        "warnings": [],
    }
    if json_mode:
        sys.stdout.write(json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n")
    else:
        sys.stdout.write(f"BLOCKED  {code}\n")
        sys.stdout.write(f"事实: {json.dumps(facts, ensure_ascii=False, sort_keys=True)}\n")
        sys.stdout.write(f"出口: {exit_hint}\n")
    sys.stdout.flush()
    return exit_code


def read_json(path):
    try:
        with open(path, "r", encoding="utf-8") as handle:
            return json.load(handle)
    except FileNotFoundError:
        return None
    except (OSError, ValueError):
        return {"__invalid__": True}


def write_json(path, value):
    directory = os.path.dirname(path) or "."
    os.makedirs(directory, exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(value, sort_keys=True, indent=2, ensure_ascii=False) + "\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(tmp, path)


def user_dir():
    return os.path.join(os.path.expanduser("~"), HOST_CONFIG_REL[0])


def confirm_path():
    return os.path.join(user_dir(), CONFIRM_REL[1])


def global_config_path():
    return os.path.join(user_dir(), HOST_CONFIG_REL[1])


def strip_project_flag(argv):
    """移除 `--project <abs>`，返回 (argv, project 或 None)。"""
    rest = []
    project = None
    index = 0
    while index < len(argv):
        token = argv[index]
        if token == "--project":
            if index + 1 >= len(argv):
                return None, "missing value"
            project = argv[index + 1]
            index += 2
            continue
        if token.startswith("--project="):
            project = token.split("=", 1)[1]
            index += 1
            continue
        rest.append(token)
        index += 1
    return rest, project


def locate_project(argv):
    """返回 (root, rest, error)。"""
    rest, project = strip_project_flag(argv)
    if rest is None:
        return None, None, ("project flag requires an absolute path", "WF_PATH_INVALID")
    if project is not None:
        if not os.path.isabs(project) or not os.path.isdir(project):
            return None, None, ("--project must be an existing absolute directory", "WF_PATH_INVALID")
        root = os.path.realpath(project)
    else:
        script = os.path.realpath(__file__)
        if os.path.basename(os.path.dirname(script)) != "bin" or os.path.basename(
            os.path.dirname(os.path.dirname(script))
        ) != ".wf":
            return None, None, ("cannot confirm layout from script location", "WF_CAPABILITY_UNAVAILABLE")
        root = os.path.dirname(os.path.dirname(os.path.dirname(script)))
    missing = []
    if not os.path.isdir(os.path.join(root, ".wf")):
        missing.append(".wf/")
    if not os.path.isfile(os.path.join(root, ".wf", "bin", "wf.py")):
        missing.append(".wf/bin/wf.py")
    if missing:
        return None, None, (f"layout or target unconfirmed: missing {missing}", "WF_CAPABILITY_UNAVAILABLE")
    return root, rest, None


def path_identity(candidate, root):
    """确认对象的身份：相对候选按**目标项目根**解析，与实际执行候选同一份解析结果。"""
    if os.path.isabs(candidate):
        return os.path.realpath(candidate)
    absolute = os.path.join(os.path.abspath(root), candidate)
    real = os.path.realpath(absolute)
    root_real = os.path.realpath(os.path.abspath(root))
    try:
        relative = os.path.relpath(real, root_real)
    except ValueError:
        return real
    if relative.startswith(".."):
        return real
    return relative


def probe_version(candidate):
    try:
        result = subprocess.run([candidate, "--version"], capture_output=True, text=True, check=False)
    except OSError:
        return None
    text = (result.stdout or "") + (result.stderr or "")
    match = re.search(r"Python\s+(\d+)\.(\d+)(?:\.(\d+))?", text)
    if not match:
        return None
    return text.strip()


def version_tuple(text):
    match = re.search(r"Python\s+(\d+)\.(\d+)", text or "")
    if not match:
        return None
    return int(match.group(1)), int(match.group(2))


def project_config_path(root):
    return os.path.join(root, ".wf", "project-config.json")


def resolve_candidate(root, scope=None):
    """解析顺序：项目键 → 全局键 → 系统 python3；返回 (scope, config_value, candidate)。

    配置非法不回退：空串、非绝对路径的全局键、损坏的 JSON 都按配置错误阻断（机制稿 §8.2）。
    """
    config = read_json(project_config_path(root))
    if isinstance(config, dict) and "__invalid__" in config:
        return None, None, ("project config is invalid JSON", "WF_EXECUTOR_UNCONFIRMED")
    if config is not None and not isinstance(config, dict):
        return None, None, ("project config is not a JSON object", "WF_EXECUTOR_UNCONFIRMED")
    project_value = (config or {}).get("python_executable")
    if project_value == "":
        return None, None, ("project python_executable is empty (invalid configuration)",
                            "WF_EXECUTOR_UNCONFIRMED")
    if project_value is not None and not isinstance(project_value, str):
        return None, None, ("project python_executable must be a string", "WF_EXECUTOR_UNCONFIRMED")
    if scope in (None, "project") and project_value:
        # 有效项目配置优先：不去读全局层，损坏的全局键也就不再阻断它
        return "project", project_value, None
    global_config = read_json(global_config_path())
    if isinstance(global_config, dict) and "__invalid__" in global_config:
        return None, None, ("global config is invalid JSON", "WF_EXECUTOR_UNCONFIRMED")
    global_value = global_config.get("python_executable") if isinstance(global_config, dict) else None
    if global_value is not None and not isinstance(global_value, str):
        return None, None, ("global python_executable must be a string", "WF_EXECUTOR_UNCONFIRMED")
    if global_value == "":
        return None, None, ("global python_executable is empty (invalid configuration)",
                            "WF_EXECUTOR_UNCONFIRMED")
    if global_value is not None and not os.path.isabs(global_value):
        return None, None, ("global python_executable must be an absolute path", "WF_EXECUTOR_UNCONFIRMED")
    if scope == "project":
        if not project_value:
            return None, None, ("project python_executable is not set", "WF_PATH_INVALID")
        return "project", project_value, None
    if scope == "global":
        if not global_value:
            return None, None, ("global python_executable is not set", "WF_PATH_INVALID")
        return "global", global_value, None
    if scope == "system":
        located = shutil.which("python3")
        if not located:
            return None, None, ("system python3 not found", "WF_CAPABILITY_UNAVAILABLE")
        return "system", located, None
    if project_value:
        return "project", project_value, None
    if global_value:
        return "global", global_value, None
    located = shutil.which("python3")
    if not located:
        return None, None, (
            "system python3 missing and neither project nor global key is set",
            "WF_CAPABILITY_UNAVAILABLE",
        )
    return "system", located, None




def candidate_path(root, config_value):
    """配置值 → 可执行路径；项目相对值不得越出项目根（设计稿 §1.1）。"""
    if not isinstance(config_value, str) or not config_value:
        return None, ("python_executable must be a non-empty string", "WF_EXECUTOR_UNCONFIRMED")
    if os.path.isabs(config_value):
        return os.path.realpath(config_value), None
    joined = os.path.realpath(os.path.join(os.path.abspath(root), config_value))
    root_real = os.path.realpath(os.path.abspath(root))
    if joined != root_real and not joined.startswith(root_real + os.sep):
        return None, ("project python_executable escapes project root", "WF_PATH_INVALID")
    return joined, None


def _task_prd_is_approved(task_record_path, prd_path):
    """任务 PRD 能作为批准证据，须「当前 PRD 内容」正是被批准的那一份（草稿/旧批准都不算）。"""
    import hashlib as _hashlib
    import json as _json

    try:
        with open(task_record_path, "r", encoding="utf-8") as handle:
            record = _json.load(handle)
        with open(prd_path, "rb") as handle:
            current = "sha256:" + _hashlib.sha256(handle.read()).hexdigest()
    except (OSError, ValueError):
        return False
    if not isinstance(record, dict):
        return False
    approval = (record.get("plan") or {}).get("approval")
    if isinstance(approval, dict) and approval:
        # 批准对象摘要即当时 PRD 的摘要：与当前内容不符说明批准后又改过（回 Plan 待重批）
        digest = approval.get("object_digest") or (approval.get("decision") or {}).get("object_digest")
        return bool(digest) and digest == current
    if record.get("terminal") == "normal":
        # 归档任务同样是历史证据，但"历史"不等于"可随意改写"：
        # 当前 PRD 摘要必须仍等于归档时的批准摘要，否则不再作为批准依据
        approval = (record.get("plan") or {}).get("approval") or {}
        digest = approval.get("object_digest") or (approval.get("decision") or {}).get("object_digest")
        return bool(digest) and digest == current
    return False


def project_key_approved(root, value):
    """核 Git 侧的键名与配置值：基线，或**已批准**任务的 PRD 中能查到同一键与值。"""
    candidates = [os.path.join(root, ".wf", "baseline.md")]
    tasks_dir = os.path.join(root, ".wf", "tasks")
    if os.path.isdir(tasks_dir):
        try:
            for name in sorted(os.listdir(tasks_dir)):
                directory = os.path.join(tasks_dir, name)
                prd = os.path.join(directory, "prd.md")
                record = os.path.join(directory, "task.json")
                if os.path.isfile(prd) and _task_prd_is_approved(record, prd):
                    candidates.append(prd)
        except OSError:
            pass
    for path in candidates:
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as handle:
                text = handle.read()
        except OSError:
            continue
        if "python_executable" in text and value in text:
            return path
    return None


def load_confirmations():
    data = read_json(confirm_path())
    if data is None:
        return []
    if isinstance(data, dict):
        items = data.get("interpreters")
    else:
        items = data
    return [item for item in (items or []) if isinstance(item, dict)]


def project_id_of(root):
    config = read_json(os.path.join(root, ".wf", "project-config.json"))
    return config.get("project_id") if isinstance(config, dict) else None


def stat_tuple(candidate):
    real = os.path.realpath(candidate)
    info = os.stat(real)
    return info.st_size, info.st_mtime_ns


def matches(entry, *, scope, config_value, identity, size, mtime_ns, project_id):
    if entry.get("scope") != scope:
        return False
    if entry.get("config_value") != config_value:
        return False
    if entry.get("path_identity") != identity:
        return False
    if entry.get("size") != size or entry.get("mtime_ns") != mtime_ns:
        return False
    if scope == "project" and entry.get("project_id") != project_id:
        return False
    return True


def parse_scope(argv, default="system"):
    for index, token in enumerate(argv):
        if token == "--scope":
            return argv[index + 1] if index + 1 < len(argv) else None
        if token.startswith("--scope="):
            return token.split("=", 1)[1]
    return default


def cmd_confirm_executor(root, argv):
    scope = parse_scope(argv)
    if scope not in SCOPES:
        return fail("WF_PATH_INVALID", {"scope": scope}, "scope 取 system/global/project", exit_code=1)
    resolved_scope, config_value, error = resolve_candidate(root, scope)
    if error:
        return fail(error[1], {"detail": error[0], "scope": scope}, "按出口修正配置后重试")
    candidate, path_error = candidate_path(root, config_value)
    if path_error:
        return fail(path_error[1], {"detail": path_error[0], "config_value": config_value},
                    "按原项目配置通道修正后再确认")
    if resolved_scope == "project":
        approved = project_key_approved(root, config_value)
        if not approved:
            return fail(
                "WF_APPROVAL_MISSING",
                {"reason": "项目键未在基线或已批准 PRD 中出现", "config_value": config_value},
                "先按基线通道把键名与配置值写入已批准提案，再执行确认",
            )
    if not os.path.isfile(candidate) or not os.access(candidate, os.X_OK):
        return fail(
            "WF_EXECUTOR_UNCONFIRMED",
            {"candidate": candidate, "reason": "not an executable file"},
            "人确认当前解释器，或换成已批准的解释器",
        )
    version_text = probe_version(candidate)
    parsed = version_tuple(version_text)
    if not parsed or parsed[0] != 3 or parsed[1] < MIN_VERSION[1]:
        return fail(
            "WF_EXECUTOR_UNCONFIRMED",
            {"candidate": candidate, "version": version_text, "required": "Python >= 3.11"},
            "改选已核实可用的 Python 3.11+ 解释器",
        )
    size, mtime_ns = stat_tuple(candidate)
    entry = {
        "scope": resolved_scope,
        "project_id": project_id_of(root) if resolved_scope == "project" else None,
        "key": "python_executable",
        "config_value": config_value,
        "path_identity": path_identity(config_value, root),
        "size": size,
        "mtime_ns": mtime_ns,
        "python_version": version_text,
        "confirmed_at": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
    }
    entries = load_confirmations()
    identical = [
        existing
        for existing in entries
        if matches(
            existing,
            scope=resolved_scope,
            config_value=config_value,
            identity=entry["path_identity"],
            size=size,
            mtime_ns=mtime_ns,
            project_id=entry["project_id"],
        )
    ]
    if not identical:
        # 确认动作必须由人在终端完成：非 TTY 一律不写记录（设计稿 §1.1、机制稿 §8.2）
        if not sys.stdin.isatty():
            return fail(
                "WF_SEMANTIC_DECISION",
                {"reason": "确认动作须由人在终端执行", "candidate": candidate,
                 "scope": resolved_scope, "config_value": config_value},
                "在终端直接运行该命令并输入确认词；不接受管道、脚本或代填",
                False, exit_code=2, tier="needs_decision",
            )
        sys.stdout.write("即将写入的执行器确认记录：\n")
        sys.stdout.write(json.dumps(entry, ensure_ascii=False, sort_keys=True, indent=2) + "\n")
        sys.stdout.write("输入 yes 确认写入（其他输入即取消）：")
        sys.stdout.flush()
        answer = sys.stdin.readline().strip()
        if answer != "yes":
            return fail(
                "WF_SEMANTIC_DECISION",
                {"reason": "人未确认写入", "answer": answer[:20]},
                "未写入确认记录；需要时在终端重新运行",
                False, exit_code=2, tier="needs_decision",
            )
        entries.append(entry)
        write_json(confirm_path(), {"interpreters": entries})
    sys.stdout.write(
        "OK  WF_OK\n"
        f"确认执行器: {candidate} ({version_text})\n"
        f"scope={resolved_scope} config_value={config_value}\n"
        "下一步: 重入原操作\n"
    )
    return 0


def executor_ready(root, scope, config_value, candidate):
    try:
        size, mtime_ns = stat_tuple(candidate)
    except OSError:
        return False
    identity = path_identity(config_value, root)
    project_id = project_id_of(root) if scope == "project" else None
    for entry in load_confirmations():
        if matches(
            entry,
            scope=scope,
            config_value=config_value,
            identity=identity,
            size=size,
            mtime_ns=mtime_ns,
            project_id=project_id,
        ):
            return True
    return False


def main(argv):
    json_mode = "--json" in argv
    root, rest, error = locate_project(argv)
    if error:
        return fail(error[1], {"detail": error[0]}, "用 --project <绝对路径> 显式给目标，或按恢复说明重取入口", json_mode)
    if rest and rest[0] in ("repair", "uninstall"):
        script = os.path.join(root, ".wf", "bin", f"{rest[0]}.py")
        if not os.path.isfile(script):
            return fail(
                "WF_CAPABILITY_UNAVAILABLE",
                {"missing": f".wf/bin/{rest[0]}.py"},
                "按恢复说明从对应发行重取该单文件入口",
                json_mode,
            )
        os.execv(sys.executable, [sys.executable, script] + rest[1:])
    if rest and rest[0] == "confirm-executor":
        return cmd_confirm_executor(root, rest[1:])
    scope, config_value, error = resolve_candidate(root)
    if error:
        return fail(error[1], {"detail": error[0]}, "按出口修正配置后重入；不静默回退低优先级解释器", json_mode)
    candidate, path_error = candidate_path(root, config_value)
    if path_error:
        return fail(path_error[1], {"detail": path_error[0], "config_value": config_value},
                    "项目键须为项目内相对路径或绝对路径；不自动改写配置", json_mode)
    if not os.path.isfile(candidate) or not os.access(candidate, os.X_OK):
        return fail(
            "WF_EXECUTOR_UNCONFIRMED",
            {"candidate": candidate, "scope": scope, "reason": "configured interpreter unusable"},
            "人执行 confirm-executor 确认当前解释器，或按原项目配置通道修复",
            json_mode,
        )
    if not executor_ready(root, scope, config_value, candidate):
        return fail(
            "WF_EXECUTOR_UNCONFIRMED",
            {
                "candidate": candidate,
                "scope": scope,
                "config_value": config_value,
                "reason": "no matching confirmation tuple",
            },
            "人执行：python3 .wf/bin/wf.py confirm-executor --scope " + scope,
            json_mode,
        )
    lib_dir = os.path.join(root, ".wf", "lib")
    entry = os.path.join(lib_dir, "wflib", "module_main.py")
    if not os.path.isfile(entry):
        return fail(
            "WF_CAPABILITY_UNAVAILABLE",
            {"missing": ".wf/lib/wflib/module_main.py"},
            "按恢复说明重取运行时包",
            json_mode,
        )
    env = dict(os.environ)
    env["PYTHONPATH"] = lib_dir
    env["WF_PROJECT_ROOT"] = root
    env["WF_BOOTSTRAP"] = "1"
    env.pop("WF_PROJECT", None)
    argv_out = [candidate, entry] + rest
    os.execve(candidate, argv_out, env)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
