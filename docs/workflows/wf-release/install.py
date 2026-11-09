#!/usr/bin/env python3
"""install.py — 发行根安装入口（实现稿 §1.5、§4.1.1、机制稿 §10.2/§10.4）。

单文件、仅标准库、自包含：安装发生时目标项目还没有 `.wf/bin/`，不能导入 wflib。
它不投放目标项目，按 `target_class=release_only` 计入 rules_digest。
"""

from __future__ import annotations

import argparse
import datetime
import fcntl
import hashlib
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import uuid

LOCK_MARK = b"wf-lock-v1\n"
REF_RE = re.compile(r"^refs/tags/wf-v(\d+)\.(\d+)\.(\d+)$")
MIN_VERSION = (3, 11)


# --------------------------------------------------------------------------
# 规范 JSON 与哈希（与 wflib/records.py、wflib/assets.py 同一算法，但自含一份）
# --------------------------------------------------------------------------


def canonical(obj) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def H(domain: str, obj) -> str:
    payload = json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return "sha256:" + hashlib.sha256(domain.encode("utf-8") + b"\x00" + payload).hexdigest()


def plain_digest(obj) -> str:
    return "sha256:" + hashlib.sha256(canonical(obj).encode("utf-8")).hexdigest()


def file_digest(path):
    try:
        with open(path, "rb") as handle:
            digest = hashlib.sha256()
            for chunk in iter(lambda: handle.read(65536), b""):
                digest.update(chunk)
            return "sha256:" + digest.hexdigest()
    except FileNotFoundError:
        return None


def now_str():
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def compute_rules_digest(manifest):
    compatibility = {key: value for key, value in (manifest.get("compatibility") or {}).items()
                     if key != "rules_digest"}
    raw_assets = manifest.get("assets") or []
    if any(not isinstance(entry, dict) for entry in raw_assets):
        raise ValueError("asset entry is not an object")
    assets = sorted(
        raw_assets,
        key=lambda entry: (
            (entry.get("source_path") or "").encode("utf-8"),
            (entry.get("target_class") or "").encode("utf-8"),
            (entry.get("target_relative") or "").encode("utf-8"),
        ),
    )
    steps = sorted(manifest.get("required_steps") or [],
                   key=lambda entry: (entry.get("id") or "").encode("utf-8"))
    return H("wf-rules-v1", {
        "schema_version": manifest.get("schema_version"),
        "compatibility_without_rules_digest": compatibility,
        "assets": assets,
        "required_steps": steps,
        "template_markers": manifest.get("template_markers"),
        "gitignore_managed": manifest.get("gitignore_managed"),
    })


# --------------------------------------------------------------------------
# 输出
# --------------------------------------------------------------------------


def blocked(code, message, facts=None, json_mode=False):
    payload = {"ok": False, "code": code, "tier": "blocked", "facts": facts or {},
               "next": message}
    if json_mode:
        sys.stdout.write(json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n")
    else:
        sys.stdout.write(f"BLOCKED  {code}\n{message}\n")
        if facts:
            sys.stdout.write("事实: " + json.dumps(facts, ensure_ascii=False, sort_keys=True) + "\n")
    sys.stdout.flush()
    return 1


def needs_decision(code, message, facts=None, json_mode=False):
    """需人裁决档：不写入，给出待决事实与出口（设计稿 §1.5）。"""
    payload = {"ok": False, "code": code, "tier": "needs_decision", "facts": facts or {},
               "next": message}
    if json_mode:
        sys.stdout.write(json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n")
    else:
        sys.stdout.write(f"NEEDS-DECISION  {code}\n{message}\n")
        if facts:
            sys.stdout.write("事实: " + json.dumps(facts, ensure_ascii=False, sort_keys=True) + "\n")
    sys.stdout.flush()
    return 2


def local_branches(root):
    proc = subprocess.run(["git", "-c", "safe.directory=*", "for-each-ref", "--format=%(refname:short)", "refs/heads"],
                          cwd=root, capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        return []
    return [line.strip() for line in proc.stdout.splitlines() if line.strip()]


def branch_source_findings(target, relative_paths):
    """安装期分支来源核对（设计稿 §7.1）：当前分支缺失、但其他本地分支存在的同名路径。

    自含实现：`install.py` 不导入框架运行时（发行根安装时尚无 `.wf/lib`）；
    语义与 `wflib/assets.py::branch_source_check` 一致——只报「工作树缺失且其他分支存在」的路径，
    不存在于任何分支的路径不算发现（正常首次投放即如此）。
    """
    findings = []
    branches = local_branches(target)
    if not branches:
        return findings
    for relative in relative_paths:
        if os.path.exists(os.path.join(target, *relative.split("/"))):
            continue
        for branch in branches:
            proc = subprocess.run(["git", "-c", "safe.directory=*", "cat-file", "-e", f"{branch}:{relative}"],
                                  cwd=target, capture_output=True, text=True, check=False)
            if proc.returncode == 0:
                findings.append({"path": relative, "branch": branch})
                break
    return findings


def ok(message, payload=None, json_mode=False):
    if json_mode:
        sys.stdout.write(json.dumps({"ok": True, "code": "WF_OK", "message": message,
                                     "facts": payload or {}}, ensure_ascii=False, sort_keys=True) + "\n")
    else:
        sys.stdout.write(message + "\n")
    sys.stdout.flush()
    return 0


# --------------------------------------------------------------------------
# 发行解析
# --------------------------------------------------------------------------


def load_manifest(source):
    path = os.path.join(source, "wf-release.json")
    if not os.path.isfile(path):
        raise ValueError(f"wf-release.json missing in {source}")
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle), path


def resolve_tag(source, release_ref):
    match = REF_RE.match(release_ref)
    if not match:
        return None
    import subprocess

    result = subprocess.run(["git", "-c", "safe.directory=*", "rev-parse", f"{release_ref}^{{commit}}"], cwd=source,
                            capture_output=True, text=True, check=False)
    if result.returncode != 0:
        return None
    return result.stdout.strip()


def _worktree_clean(source):
    """发行源必须是干净检出：脏检出（或被人重算过摘要的树）不得冒充 tag 内容（第二十六轮复审外部 1）。"""
    import subprocess

    # 只看**发行子树**：发行树可能位于一个本身有未提交改动的仓库里（作者仓库），
    # 但发行目录自己的内容必须与提交一致，否则摘要校验相对工作树即无意义。
    top = subprocess.run(["git", "-c", "safe.directory=*", "rev-parse", "--show-toplevel"], cwd=source,
                         capture_output=True, text=True, check=False)
    if top.returncode != 0:
        return None, "not a git worktree"
    repo_top = os.path.realpath((top.stdout or "").strip())
    rel = os.path.relpath(os.path.realpath(source), repo_top)
    if rel.startswith(".."):
        return None, "source path is outside the git worktree"
    result = subprocess.run(["git", "-c", "safe.directory=*", "status", "--porcelain", "--", rel], cwd=repo_top,
                            capture_output=True, text=True, check=False)
    if result.returncode != 0:
        return None, "not a git worktree"
    dirty = [line for line in (result.stdout or "").splitlines() if line.strip()]
    if dirty:
        return False, dirty[:10]
    return True, []


def _committed_bytes(source, commit, path):
    """按 tag 提交读发行资产字节（设计稿 §7.2：提交哈希只用于核验内容）。失败返回 None。"""
    import subprocess

    result = subprocess.run(["git", "-c", "safe.directory=*", "show", f"{commit}:{path}"], cwd=source,
                            capture_output=True, check=False)
    if result.returncode != 0:
        return None
    return result.stdout


def verify_assets(source, manifest, commit=None):
    """核清单登记与发行资产一致。

    `commit` 给出时按**该提交的树**取字节（默认路径，2026-11-06 起），
    否则退回工作树（仅当无法解析提交时的降级，且必须已被上层判为冲突）。
    非对象条目按"不可解释"整批拒绝（不抛裸异常）。
    """
    root = os.path.realpath(source)
    problems = []
    for index, asset in enumerate(manifest.get("assets") or []):
        if not isinstance(asset, dict):
            problems.append({"reason": "asset entry is not an object", "index": index})
            continue
        source_path = asset.get("source_path") or ""
        target = os.path.realpath(os.path.join(root, source_path))
        if not target.startswith(root + os.sep):
            problems.append({"asset": source_path, "reason": "source path escapes release root"})
            continue
        if commit:
            blob = _committed_bytes(source, commit, source_path)
            actual = None if blob is None else "sha256:" + hashlib.sha256(blob).hexdigest()
            missing_reason = "missing in tag commit tree"
        else:
            actual = file_digest(target)
            missing_reason = "missing in release tree"
        if actual is None:
            problems.append({"asset": source_path, "reason": missing_reason})
            continue
        if actual != asset.get("digest"):
            problems.append({"asset": source_path, "reason": "digest mismatch",
                             "expected": asset.get("digest"), "actual": actual})
    if any(item.get("reason") == "asset entry is not an object" for item in problems):
        return problems  # 结构不可解释时不再算摘要：那只会把同一件事报两遍
    recomputed = compute_rules_digest(manifest)
    declared = (manifest.get("compatibility") or {}).get("rules_digest")
    if recomputed != declared:
        problems.append({"rules_digest": {"declared": declared, "recomputed": recomputed}})
    return problems


def trellis_clues(target):
    clues = []
    for name in ("AGENTS.md", "CLAUDE.md", ".codex/config.toml"):
        path = os.path.join(target, name)
        if os.path.isfile(path):
            try:
                with open(path, "r", encoding="utf-8", errors="replace") as handle:
                    if "TRELLIS:START" in handle.read():
                        clues.append({"path": name, "kind": "managed-block"})
            except OSError:
                pass
    for name in (".trellis", ".claude", ".codex/hooks.json"):
        if os.path.exists(os.path.join(target, name)):
            clues.append({"path": name, "kind": "clue"})
    return clues


# --------------------------------------------------------------------------
# 目标侧写入
# --------------------------------------------------------------------------


class LockRejected(Exception):
    """锁对象不可用（同名未知文件、越界、被替换）：按 WF_ASSET_DECISION 交人处置。"""


class LockBusy(Exception):
    """锁被占用：按 WF_WRITER_BUSY 报告持锁事实。"""


class Lock:
    """安装/追加平台的互斥。判据与 `wflib/lock.py` 同源，只是不导入运行时。

    - 只复用「存在且内容以 `wf-lock-v1\n` 开头」的对象（允许标记后有崩溃残留的持锁者行）；
    - 空文件与不匹配内容属同名未知文件 → `LockRejected`，不认领、不覆写；
    - 必须是**普通文件**且真实落点位于项目根内（防 `.wf-lock` 是指向项目外的符号链接）；
    - 获取后核 inode 未被替换。
    """

    def __init__(self, path, root=None):
        self.path = path
        self.root = root
        self.fd = None

    def __enter__(self):
        created = False
        try:
            self.fd = os.open(self.path, os.O_RDWR)
        except FileNotFoundError:
            try:
                self.fd = os.open(self.path, os.O_RDWR | os.O_CREAT | os.O_EXCL, 0o644)
                created = True
            except FileExistsError:
                self.fd = os.open(self.path, os.O_RDWR)
        except OSError as exc:
            raise LockRejected(f"cannot open lock: {exc}") from exc
        try:
            fcntl.flock(self.fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            os.close(self.fd)
            raise LockBusy(f"lock busy: {exc}") from exc
        try:
            info = os.fstat(self.fd)
            if not stat.S_ISREG(info.st_mode):
                raise LockRejected("lock object is not a regular file")
            if self.root is not None:
                real = os.path.realpath(self.path)
                root_real = os.path.realpath(str(self.root))
                if not (real == root_real or real.startswith(root_real + os.sep)):
                    raise LockRejected(f"lock object real path escapes the project root: {real}")
            content = os.pread(self.fd, len(LOCK_MARK) + 256, 0)
            if created:
                if content:
                    raise LockRejected("lock object appeared during exclusive creation")
                os.pwrite(self.fd, LOCK_MARK, 0)
                os.fsync(self.fd)
            elif not content.startswith(LOCK_MARK):
                reason = "empty" if content == b"" else "mark unknown"
                raise LockRejected(f"lock file is not a wf lock ({reason}); move it away or rename it")
            on_disk = os.stat(self.path)
            opened = os.fstat(self.fd)
            if (on_disk.st_dev, on_disk.st_ino) != (opened.st_dev, opened.st_ino):
                raise LockRejected("lock object was replaced during acquisition")
        except (LockRejected, OSError) as exc:
            fcntl.flock(self.fd, fcntl.LOCK_UN)
            os.close(self.fd)
            if isinstance(exc, LockRejected):
                raise
            raise LockRejected(f"lock object unusable: {exc}") from exc
        return self

    def __exit__(self, exc_type, exc, tb):
        if self.fd is not None:
            try:
                fcntl.flock(self.fd, fcntl.LOCK_UN)
            finally:
                os.close(self.fd)
                self.fd = None


def write_bytes(path, content):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if os.path.exists(path):
        if file_digest(path) == "sha256:" + hashlib.sha256(content).hexdigest():
            return False
        raise FileExistsError(path)
    tmp = path + ".wf-tmp"
    with open(tmp, "wb") as handle:
        handle.write(content)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(tmp, path)
    return True


def managed_segment(manifest):
    managed = manifest.get("gitignore_managed") or {}
    lines = [managed.get("begin_marker", "# wf-managed-v1")]
    lines += list(managed.get("lines") or ["/.wf/.runtime/", "/.wf-lock"])
    lines.append(managed.get("end_marker", "# wf-managed-end"))
    return "\n".join(lines)


def ensure_gitignore(target, manifest):
    path = os.path.join(target, ".gitignore")
    segment = managed_segment(manifest)
    try:
        with open(path, "r", encoding="utf-8") as handle:
            text = handle.read()
    except FileNotFoundError:
        text = ""
    lines = text.splitlines()
    begin = (manifest.get("gitignore_managed") or {}).get("begin_marker", "# wf-managed-v1")
    end = (manifest.get("gitignore_managed") or {}).get("end_marker", "# wf-managed-end")
    if begin in lines and end in lines:
        current = "\n".join(lines[lines.index(begin):lines.index(end) + 1])
        return {"action": "present" if current == segment else "conflict"}
    if text and not text.endswith("\n"):
        text += "\n"
    text += segment + "\n"
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)
    return {"action": "appended"}


def recovery_text(target, installation):
    return f"""# wf 恢复说明

- 发行引用：{installation.get('release_ref')}
- 源提交：{installation.get('source_commit')}
- 版本：{installation.get('version')}
- 清单摘要：{installation.get('manifest_digest')}
- 投放根：{json.dumps(installation.get('roots'), ensure_ascii=False)}

## 常规入口

    <python> {os.path.join(os.path.abspath(target), '.wf/bin/wf.py')} status

`<python>` 取本项目 `.wf/project-config.json` 的 `python_executable`（未设置则用任一 Python >= 3.11，
例如你自身运行时的解释器）；确认与解析顺序见设计稿的执行器解析一节。

## 独立恢复入口（自含单文件）

    <python> .wf/bin/repair.py
    <python> .wf/bin/uninstall.py

## 锁

`.wf-lock` 只创建不删除。确认无 wf 进程后可人工清理该文件与 `.gitignore` 中的 `/.wf-lock` 行。
"""




def runtime_support(target):
    """在部署后的运行时里取固定分派表与命令面（自检用；不改变目标状态）。"""
    import subprocess

    lib = os.path.join(target, ".wf/lib")
    if not os.path.isdir(lib):
        return {"error": "missing .wf/lib"}
    code = (
        "import json, sys;"
        f"sys.path.insert(0, {lib!r});"
        "from wflib import gates, cli;"
        "stubs = {name: getattr(handler, 'wf_delivery_round', None)"
        " for name, handler in cli.COMMANDS.items()};"
        "print(json.dumps({'supported': sorted(gates.supported_keys()),"
        " 'handlers': gates.HANDLERS, 'commands': sorted(cli.COMMANDS),"
        " 'delivery_round': getattr(gates, 'CURRENT_DELIVERY_ROUND', None),"
        " 'stub_rounds': {name: rnd for name, rnd in stubs.items() if isinstance(rnd, int)}}))"
    )
    try:
        result = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, check=False)
    except OSError as exc:
        return {"error": f"spawn failed: {exc}"}
    if result.returncode != 0:
        return {"error": (result.stderr or result.stdout).strip()[-800:]}
    try:
        return json.loads(result.stdout.strip().splitlines()[-1])
    except (ValueError, IndexError) as exc:
        return {"error": f"unparsable runtime report: {exc}"}


def self_check(target, manifest, skill_roots):
    problems = []
    for index, asset in enumerate(manifest.get("assets") or []):
        if not isinstance(asset, dict):
            problems.append({"reason": "asset entry is not an object", "index": index})
            continue
        if asset.get("target_class") == "release_only":
            continue
        targets = []
        if asset.get("target_class") == "project_wf":
            targets.append(os.path.join(target, *asset["target_relative"].split("/")))
        else:
            for root in skill_roots:
                targets.append(os.path.join(root, *asset["target_relative"].split("/")))
        for path in targets:
            if file_digest(path) != asset.get("digest"):
                problems.append({"target": path, "reason": "digest mismatch after deploy"})
    support = runtime_support(target)
    if support.get("error"):
        problems.append({"runtime": "not importable", "detail": support["error"]})
    else:
        declared = {step.get("id") for step in manifest.get("required_steps") or [] if step.get("id")}
        supported = set(support.get("supported") or [])
        if declared - supported:
            problems.append({"required_steps": sorted(declared - supported), "reason": "no fixed handler"})
        if supported - declared:
            problems.append({"required_steps": sorted(supported - declared), "reason": "handler not declared"})
        commands = set(support.get("commands") or [])
        bootstrap = {name for name in ("repair", "uninstall")
                     if os.path.isfile(os.path.join(target, ".wf/bin", f"{name}.py"))}
        for step in manifest.get("required_steps") or []:
            step_id = step.get("id") or ""
            if not step_id.startswith("control."):
                continue
            handler = support.get("handlers", {}).get(step_id)
            if handler is None:
                problems.append({"required_step": step_id, "reason": "no fixed handler entry"})
            elif handler not in commands | bootstrap:
                problems.append({"required_step": step_id, "reason": f"handler entry missing: {handler}"})
        # 交付轮次可达（2026-11-05）：声明的当前交付集内，承接命令不得是能力不可用桩。
        current_round = manifest.get("delivery_round")
        if (not isinstance(current_round, int) or isinstance(current_round, bool)
                or current_round <= 0):
            problems.append({"required_step": "manifest.delivery_round",
                             "reason": "missing or invalid; cannot decide delivery reachability"})
        else:
            stub_rounds = support.get("stub_rounds") or {}
            for step in manifest.get("required_steps") or []:
                step_id = step.get("id") or ""
                declared_round = step.get("delivery_round")
                if (not isinstance(declared_round, int) or isinstance(declared_round, bool)
                        or declared_round <= 0):
                    problems.append({"required_step": step_id, "reason": "delivery_round missing or invalid"})
                    continue
                if not step_id.startswith("control."):
                    continue
                handler = support.get("handlers", {}).get(step_id)
                stub_round = stub_rounds.get(handler)
                if stub_round is not None and declared_round <= current_round:
                    problems.append({
                        "required_step": step_id,
                        "reason": (f"declared delivered in round {declared_round} but `{handler}` "
                                   f"is a capability stub (round {stub_round})"),
                    })
    if not os.path.isfile(os.path.join(target, ".wf/bin/wf.py")):
        problems.append({"missing": ".wf/bin/wf.py"})
    return problems


# --------------------------------------------------------------------------
# 主流程
# --------------------------------------------------------------------------


# 各 agent 的 skill 发现层（项目内相对目录）。依据（均取自各官方文档，见 §4.5）：
#   .agents/skills   共享层：Cursor / Gemini CLI / GitHub Copilot / Codex / DSH 都会读
#   .claude/skills   仅 Claude Code 读（Cursor 与 Copilot 为兼容另读它）
#   .cursor/skills   Cursor 自有；.gemini/skills Gemini CLI 自有；.github/skills Copilot 自有
# 规则：平台能读共享层就用共享层，否则用其自有目录；同一项目可给多个平台，取并集。
# 平台 → 技能根 + 会话标识来源（设计稿 §1.2；S12 口径 A：平台知识只许出现在安装期部署表与适配层）
# `session_identity.source` 只取 official-docs / user-declared / unknown：
#   - user-declared 需记明声明者与实测事实；unknown 表示"未核实"，适配层不得据此猜（走 WF_SEMANTIC_DECISION）
#   - `clear_resets` 表示"宿主自带的 /clear（若存在）之后会话标识是否变化"；null = 未核实或该宿主无此命令
PLATFORMS = {
    "dsh": {
        "dir": ".agents/skills",
        "reads_shared": True,
        # DSH 托管 shell 注入 DSH_SESSION_ID；DSH 无 /clear 命令（2026-11-09 用户实测）
        "session_identity": {"value": "env:DSH_SESSION_ID", "source": "user-declared", "clear_resets": None},
    },
    "codex": {
        "dir": ".agents/skills",
        "reads_shared": True,
        # Codex SessionStart hook 提供会话标识；/clear 之后会话标识真实变化（2026-11-09 用户实测）
        "session_identity": {"value": "host-hook:SessionStart", "source": "user-declared", "clear_resets": True},
    },
    # v42 S12 口径 A：部署表 8 项。`zcode`/`pi` 的技能根由用户声明（读共享根），
    # 其"会话标识来源"**未核实**——按口径不猜，适配层遇到它们只能走 WF_SEMANTIC_DECISION。
    "zcode": {
        "dir": ".agents/skills",
        "reads_shared": True,
        "session_identity": {"value": None, "source": "unknown", "clear_resets": None},
    },
    "pi": {
        "dir": ".agents/skills",
        "reads_shared": True,
        "session_identity": {"value": None, "source": "unknown", "clear_resets": None},
    },
    "cursor": {"dir": ".cursor/skills", "reads_shared": True,
               "session_identity": {"value": None, "source": "unknown", "clear_resets": None}},
    "geminicli": {"dir": ".gemini/skills", "reads_shared": True,
                  "session_identity": {"value": None, "source": "unknown", "clear_resets": None}},
    "copilot": {"dir": ".github/skills", "reads_shared": True,
                "session_identity": {"value": None, "source": "unknown", "clear_resets": None}},
    "claudecode": {"dir": ".claude/skills", "reads_shared": False,
                   "session_identity": {"value": None, "source": "unknown", "clear_resets": None}},
}
PLATFORM_ALIASES = {"claude": "claudecode", "gemini": "geminicli", "ghcopilot": "copilot"}
SHARED_SKILL_DIR = ".agents/skills"


def _flatten_platforms(platforms):
    """`--platform a --platform b`、`--platform a b`、`--platform a,b` 三种写法都接受。"""
    flat = []
    for item in platforms or []:
        values = item if isinstance(item, (list, tuple)) else [item]
        for value in values:
            for part in str(value).split(","):
                part = part.strip()
                if part:
                    flat.append(part)
    return flat


def resolve_skill_roots(target, platforms):
    """把 --platform 解析成项目内技能目录（绝对路径，已去重）。

    未知名不给猜测：直接拒绝并列出支持的平台。
    """
    roots, unknown = [], []
    for name in _flatten_platforms(platforms):
        key = PLATFORM_ALIASES.get(name, name)
        entry = PLATFORMS.get(key)
        if entry is None:
            unknown.append(name)
            continue
        relative = SHARED_SKILL_DIR if entry["reads_shared"] else entry["dir"]
        root = os.path.join(os.path.abspath(target), *relative.split("/"))
        if root not in roots:
            roots.append(root)
    return roots, unknown


def _dump_json(path, payload):
    """原子替换写入：中断不会留下半截 JSON（与 uninstall.py 同标准）。"""
    text = json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    temporary = f"{path}.tmp-{os.getpid()}"
    with open(temporary, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)


def add_platforms(args, commit, manifest, writes, skill_roots, branch_findings=None):
    """已安装项目追加平台（重复安装语义）：只投放新平台的技能副本，不动 .wf 资产与项目数据。

    2026-11-05 第二轮修正（复审 #2/#3/#4/#7/#8、R1）：
    - **全部读取与冲突复核都在锁内**：锁外读到的安装记录/目录状态可能已被并发追加改变；
    - writer 记录按运行期同一判据校验（schema/状态组合/holder），不只看 `state == idle`；
    - 新根技能副本登记进 `installation.assets`；`installation.json` 自身计入回执 `changes`；
    - 回执 `changes[].path` 一律为**项目相对路径**（运行期按相对路径匹配与查 Git 树）；
    - 释放写者时再次递增代次（授予、撤销各递增）；
    - 无任何变化时返回幂等结果，不取写权、不产生空回执。
    """
    installation_path = os.path.join(args.target, ".wf/install/installation.json")
    writer_path = os.path.join(args.target, ".wf/writer.json")
    if not os.path.isfile(installation_path) or not os.path.isfile(writer_path):
        return blocked("WF_RECORD_INVALID", "安装记录或写权记录缺失，不能追加平台",
                       {"installation": os.path.isfile(installation_path),
                        "writer": os.path.isfile(writer_path)}, args.json)
    lock_path = os.path.join(args.target, ".wf-lock")
    try:
        lock = Lock(lock_path, root=args.target)
    except LockRejected as exc:
        return blocked("WF_ASSET_DECISION", f"锁对象冲突：{exc}", {"path": lock_path}, args.json)
    except LockBusy as exc:
        return blocked("WF_WRITER_BUSY", f"锁被占用：{exc}", {"path": lock_path}, args.json)

    try:
        with lock:
            # —— 锁内重读与重建计划 ——
            with open(installation_path, "r", encoding="utf-8") as handle:
                installation = json.load(handle)
            with open(writer_path, "r", encoding="utf-8") as handle:
                writer = json.load(handle)
            if installation.get("source_commit") != commit:
                return blocked("WF_ASSET_DECISION",
                               "已安装的发行引用与本次不同：追加平台只允许同引用；升级走 wf.py upgrade（第三轮）",
                               {"installed": installation.get("release_ref"), "requested": args.release_ref,
                                "installed_commit": installation.get("source_commit"),
                                "requested_commit": commit}, args.json)
            # 同 commit 不等于同内容（2026-11-05 第八轮复审 F8-4）：重建发行会让 rules_digest 变化，
            # 只比 commit 会把新技能混进旧运行时。追加前再比一次已装清单的内容摘要。
            writer_problem = _writer_problem(writer)
            if writer_problem:
                return blocked("WF_RECORD_INVALID", "写权记录不可用于维护写入：" + writer_problem,
                               {"writer": writer}, args.json)
            current = [item for item in installation.get("platforms") or [] if isinstance(item, str)]
            wanted = sorted({PLATFORM_ALIASES.get(name, name) for name in _flatten_platforms(args.platform)})
            added = [name for name in wanted if name not in current]
            known_roots = set(installation.get("roots") or [])
            new_roots = [root for root in skill_roots
                         if os.path.relpath(root, args.target).replace(os.sep, "/") not in known_roots]
            planned = []
            for base, asset, relative in writes:
                if asset.get("target_class") != "skill_root" or base not in new_roots:
                    continue
                source_file = os.path.join(os.path.abspath(args.source),
                                           *str(asset.get("source_path") or "").split("/"))
                if not os.path.isfile(source_file):
                    return blocked("WF_RELEASE_CONFLICT", "发行树缺该技能的源文件",
                                   {"source_path": asset.get("source_path")}, args.json)
                with open(source_file, "rb") as handle:
                    data = handle.read()
                planned.append({"base": base, "asset": asset, "relative": relative, "source": source_file,
                                "destination": os.path.join(base, *relative.split("/")), "data": data})
            conflicts = []
            for entry in planned:
                if not os.path.exists(entry["destination"]):
                    continue
                with open(entry["destination"], "rb") as handle:
                    if handle.read() != entry["data"]:
                        conflicts.append(entry["destination"])
            if conflicts:
                return blocked("WF_ASSET_DECISION",
                               "目标已存在且内容不同：重复安装不覆盖本地偏离，整批不写；"
                               "请人逐项决定保留/移走/删除后重试",
                               {"paths": conflicts[:20]}, args.json)
            pending = [entry for entry in planned if not os.path.exists(entry["destination"])]
            registered = {(asset.get("root_ref"), asset.get("target"))
                          for asset in installation.get("assets") or []}
            missing_assets = [entry for entry in planned
                              if ("project" if entry["base"] == args.target else entry["base"],
                                  entry["relative"]) not in registered]
            # 无任何变化时先走幂等：不得因"缺证据"把"什么都不做"拒掉（第十轮复审 N10-4）
            if not added and not pending and not missing_assets:
                return ok("\n".join([
                    "OK  WF_OK",
                    f"目标：{args.target}",
                    "新增平台：（无新增）",
                    f"现有平台：{json.dumps(current, ensure_ascii=False)}",
                    "说明：无任何变化，未取写权、未产生回执。",
                ]), {"platforms": current, "deployed": 0, "noop": True}, args.json)

            # 同 commit 不等于同内容：有实际写入前必须能确认两侧内容摘要（第九轮 N9-1）
            installed_digest = (installation.get("rules_digest")
                                or ((installation.get("manifest") or {}).get("compatibility") or {}).get("rules_digest"))
            if not installed_digest:
                installed_manifest_path = os.path.join(args.target, ".wf/install/release-manifest.json")
                try:
                    with open(installed_manifest_path, "r", encoding="utf-8") as handle:
                        installed_manifest = json.load(handle)
                    installed_digest = ((installed_manifest.get("compatibility") or {}).get("rules_digest"))
                except (OSError, ValueError):
                    installed_digest = None
            requested_digest = ((manifest or {}).get("compatibility") or {}).get("rules_digest")
            if not installed_digest or not requested_digest:
                return blocked("WF_ASSET_DECISION",
                               "无法确认已装内容摘要（缺 rules_digest 与可读的已装清单）：追加平台被拒，"
                               "请按升级/重装流程处理",
                               {"installed_rules_digest": installed_digest,
                                "requested_rules_digest": requested_digest}, args.json)
            if installed_digest != requested_digest:
                return blocked("WF_ASSET_DECISION",
                               "已安装内容摘要与本次发行不同：追加平台只允许同内容；请按升级/重装流程处理",
                               {"installed_rules_digest": installed_digest,
                                "requested_rules_digest": requested_digest}, args.json)

            operation_id = f"install-{uuid.uuid4().hex}"
            held_generation = int(writer.get("generation") or 0) + 1
            writer.update({"state": "held", "generation": held_generation, "updated_at": now_str(),
                           "holder": {"kind": "maintenance", "id": operation_id,
                                      "scope": {"operation": operation_id}, "generation": held_generation},
                           "checkpoint": {"operation": operation_id, "phase": "add-platforms"}})
            _dump_json(writer_path, writer)

            deployed = []
            for entry in pending:
                os.makedirs(os.path.dirname(entry["destination"]), exist_ok=True)
                with open(entry["destination"], "wb") as handle:
                    handle.write(entry["data"])
                if entry["asset"].get("executable"):
                    os.chmod(entry["destination"], os.stat(entry["source"]).st_mode | 0o755)
                deployed.append(entry["destination"])

            if branch_findings:
                installation.setdefault("decisions", []).append({
                    "kind": "branch-source", "findings": branch_findings,
                    "decision": "human (--confirm)", "at": now_str(),
                    "note": "人确认在本分支按新安装继续（设计稿 §7.1）",
                })
            installation["platforms"] = sorted(set(current) | set(wanted))
            installation["roots"] = sorted(known_roots | {
                os.path.relpath(root, args.target).replace(os.sep, "/") for root in skill_roots})
            for entry in planned:
                root_ref = "project" if entry["base"] == args.target else entry["base"]
                key = (root_ref, entry["relative"])
                if key in registered:
                    continue
                installation.setdefault("assets", []).append({
                    "target": entry["relative"], "root_ref": root_ref,
                    "digest": entry["asset"].get("digest"), "source_path": entry.get("asset", {}).get("source_path"),
                })
                registered.add(key)
            _dump_json(installation_path, installation)

            head_before = None
            probe = subprocess.run(["git", "-c", "safe.directory=*", "rev-parse", "HEAD"], cwd=args.target,
                                   capture_output=True, text=True, check=False)
            if probe.returncode == 0:
                head_before = probe.stdout.strip() or None
            changed = deployed + [installation_path]
            changes = [{"path": os.path.relpath(path, args.target).replace(os.sep, "/"),
                        "before": None, "after": file_digest(path)}
                       for path in changed]
            released_generation = held_generation + 1
            writer.update({
                "state": "idle",
                "holder": None,
                "generation": released_generation,
                "revision": int(writer.get("revision") or 0) + 1,
                "checkpoint": {"operation": operation_id, "phase": "platforms-added"},
                "updated_at": now_str(),
            })
            writer["maintenance_results"] = list(writer.get("maintenance_results") or []) + [{
                "operation": operation_id,
                "preview_digest": plain_digest(installation),
                "head_before": head_before,
                "changes": changes,
                "receipt_git_state": {"head": head_before, "tracked_paths": len(changes)},
                "result": "applied_pending_commit",
                "disposition": None,
            }]
            _dump_json(writer_path, writer)
    except LockRejected as exc:
        return blocked("WF_ASSET_DECISION", f"锁对象冲突：{exc}", {"path": lock_path}, args.json)
    except LockBusy as exc:
        return blocked("WF_WRITER_BUSY", f"锁被占用：{exc}", {"path": lock_path}, args.json)

    return ok("\n".join([
        "OK  WF_OK",
        f"目标：{args.target}",
        f"新增平台：{json.dumps(added, ensure_ascii=False)}" + ("（无新增）" if not added else ""),
        f"投放技能副本：{len(deployed)} 个（新根 {len(new_roots)} 个）",
        f"现有平台：{json.dumps(installation['platforms'], ensure_ascii=False)}",
        "说明：.wf 资产未改；安装记录与写权回执已更新（applied_pending_commit），写权已释放为空闲。",
    ]), {"platforms": installation["platforms"], "deployed": len(deployed),
         "assets_registered": len(planned)}, args.json)


def _writer_problem(writer):
    """按运行期同一判据校验 writer（schema/状态组合/holder）。返回问题描述或 None。"""
    if not isinstance(writer, dict):
        return "record is not an object"
    if writer.get("schema_version") != 1:
        return f"unsupported schema_version={writer.get('schema_version')!r}"
    state = writer.get("state")
    if state not in ("idle", "held", "recovering"):
        return f"unknown state={state!r}"
    holder = writer.get("holder")
    if state == "idle" and holder:
        return "idle writer must not keep a holder"
    if state == "recovering":
        return "writer is recovering; 先按 repair 核对旧写者再追加平台"
    if state != "idle":
        return f"writer state is {state!r}; 追加平台需在空闲时进行"
    generation = writer.get("generation")
    if not isinstance(generation, int) or isinstance(generation, bool):
        return "generation missing or not an integer (JSON boolean is not a generation)"
    return None


def main(argv=None):
    parser = argparse.ArgumentParser(description="wf 发行根安装入口")
    parser.add_argument("--target", required=True)
    parser.add_argument("--release-ref", required=True)
    parser.add_argument("--source", required=True)
    parser.add_argument("--platform", action="append", nargs="+", default=[],
                        help="目标项目实际使用的 agent（可重复）：dsh|codex|cursor|geminicli|copilot|claudecode")
    parser.add_argument("--confirm", action="store_true")
    parser.add_argument("--strict-source", dest="strict_source", action="store_true",
                        help="发行子树必须与提交一致（脏检出即拒绝）；发行作者仓库通常不带此参数")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    if not os.path.isabs(args.target) or not os.path.isdir(args.target):
        return blocked("WF_PATH_INVALID", "--target 必须是已存在的绝对目录", {"target": args.target}, args.json)
    source = os.path.abspath(args.source)
    if not os.path.isdir(os.path.join(source, "wf-release")):
        return blocked("WF_PATH_INVALID", "--source 必须是已检出的发行目录（含 wf-release/）", {"source": source},
                       args.json)
    try:
        manifest, manifest_path = load_manifest(source)
    except ValueError as exc:
        return blocked("WF_RELEASE_CONFLICT", str(exc), {"source": source}, args.json)
    match = REF_RE.match(args.release_ref)
    if not match:
        return blocked("WF_RELEASE_CONFLICT", "只接受已登记发行引用 refs/tags/wf-vX.Y.Z",
                       {"release_ref": args.release_ref}, args.json)
    tag_version = ".".join(match.groups())
    if str(manifest.get("version")) != tag_version:
        return blocked("WF_RELEASE_CONFLICT", "清单 version 与 tag 不一致",
                       {"version": manifest.get("version"), "tag": tag_version}, args.json)
    commit = resolve_tag(source, args.release_ref)
    if not commit:
        return blocked("WF_RELEASE_CONFLICT", "本地发行仓库无法解析该引用", {"release_ref": args.release_ref},
                       args.json)
    clean, dirty = _worktree_clean(source)
    source_dirty = bool(dirty) if clean is not None else None
    if getattr(args, "strict_source", False) and not clean:
        # 严格模式：发行子树必须与提交一致，否则"相对工作树"的摘要校验不构成 tag 绑定
        return blocked("WF_RELEASE_CONFLICT", "发行源子树与提交不一致（严格模式）",
                       {"source": source, "dirty": dirty}, args.json)
    problems = verify_assets(source, manifest, commit=commit)
    if problems:
        return blocked("WF_RELEASE_CONFLICT", "发行资产校验失败", {"problems": problems[:20]}, args.json)

    skill_roots, unknown_platforms = resolve_skill_roots(args.target, args.platform)
    if unknown_platforms:
        return blocked("WF_PATH_INVALID", "未知平台，无法确定其 skill 发现层",
                       {"unknown": unknown_platforms, "supported": sorted(PLATFORMS)}, args.json)
    # 写入计划先整批核验：路径合法性、真实落点、类别白名单；任一越界即拒绝写入任何文件
    writes, plan_problems = plan_writes(args.target, skill_roots, manifest)
    if plan_problems:
        return blocked("WF_ASSET_DECISION", "清单登记的资产越界或不可解释：整批拒绝，不写任何文件",
                       {"problems": plan_problems[:20]}, args.json)

    project_paths = []
    for base, _asset, relative in writes:
        absolute = os.path.join(base, *relative.split("/"))
        project_paths.append(os.path.relpath(absolute, args.target).replace(os.sep, "/"))
    branch_findings = branch_source_findings(args.target, project_paths)

    clues = trellis_clues(args.target)
    if not args.confirm:
        lines = [
            "wf 安装预览（未写入任何文件）",
            f"目标：{args.target}",
            f"发行引用：{args.release_ref} → {commit}",
            f"版本：{manifest.get('version')}",
            f"规则摘要：{(manifest.get('compatibility') or {}).get('rules_digest')}",
            "投放文件：",
        ]
        for base, asset, relative in writes:
            lines.append(f"  - {os.path.join(base, *relative.split('/'))}")
        lines += ["另将创建：.wf-lock、.wf/、.wf/writer.json（初始维护持有）、.wf/install/*",
                  "托管段（.gitignore）：", "  " + managed_segment(manifest).replace("\n", "\n  "),
                  f"平台：{json.dumps(sorted({PLATFORM_ALIASES.get(name, name) for name in _flatten_platforms(args.platform)}), ensure_ascii=False)}",
                  f"技能目录（目标项目内）：{json.dumps([os.path.relpath(root, args.target) for root in skill_roots], ensure_ascii=False)}"]
        if clues:
            lines.append("Trellis 线索（人确认后可继续，但本会话不得混跑两套流程）：")
            lines += [f"  - {clue['path']} ({clue['kind']})" for clue in clues]
        if branch_findings:
            lines.append("分支来源核对（设计稿 §7.1）：以下路径在当前分支缺失，但其他本地分支存在：")
            lines += [f"  - {item['path']}（分支 {item['branch']}）" for item in branch_findings]
            lines.append("出口：① 到该分支执行；② 确认在本分支按新安装继续——重跑同一条命令并加 --confirm。")
            return needs_decision("WF_ASSET_DECISION", "\n".join(lines),
                                  {"branch_source": branch_findings, "preview": True}, args.json)
        lines.append("确认后重跑并加 --confirm。")
        return ok("\n".join(lines),
                  {"preview": True, "clues": clues,
                   "platforms": sorted({PLATFORM_ALIASES.get(name, name)
                                        for name in _flatten_platforms(args.platform)})}, args.json)

    if not skill_roots:
        return blocked("WF_PATH_INVALID", "至少需要一个 --platform（技能装在目标项目内）",
                       {"supported": sorted(PLATFORMS)}, args.json)
    if os.path.exists(os.path.join(args.target, ".wf/writer.json")):
        # 已安装：同发行引用只允许"追加平台"；不同引用属升级（第三轮），不按新装覆盖
        return add_platforms(args, commit, manifest, writes, skill_roots, branch_findings)
    lock_path = os.path.join(args.target, ".wf-lock")
    try:
        lock = Lock(lock_path, root=args.target)
    except LockRejected as exc:
        return blocked("WF_ASSET_DECISION", f"锁对象冲突：{exc}", {"path": lock_path}, args.json)
    except LockBusy as exc:
        return blocked("WF_WRITER_BUSY", f"锁被占用：{exc}", {"path": lock_path}, args.json)

    try:
        with lock:
            operation_id = f"install-{uuid.uuid4().hex}"
            os.makedirs(os.path.join(args.target, ".wf"), exist_ok=True)
            writer = {
                "schema_version": 1, "id": "writer", "revision": 0, "created_at": now_str(),
                "updated_at": now_str(), "write_mark": None, "action": None, "state": "held",
                "generation": 1,
                "holder": {"kind": "maintenance", "id": operation_id,
                           "scope": {"operation": operation_id}, "generation": 1},
                "handover": None,
                "checkpoint": {"operation": operation_id, "phase": "installing"},
                "maintenance_results": [],
            }
            with open(os.path.join(args.target, ".wf/writer.json"), "w", encoding="utf-8", newline="\n") as handle:
                handle.write(json.dumps(writer, indent=2, sort_keys=True, ensure_ascii=False) + "\n")

            deployed = []
            for base, asset, relative in writes:
                source_file = os.path.join(source, *asset["source_path"].split("/"))
                with open(source_file, "rb") as handle:
                    content = handle.read()
                destination = os.path.join(base, *relative.split("/"))
                try:
                    created = write_bytes(destination, content)
                except FileExistsError:
                    return blocked("WF_ASSET_DECISION", "目标路径已存在且内容不同，未覆盖",
                                   {"path": destination}, args.json)
                if asset.get("executable"):
                    os.chmod(destination, os.stat(source_file).st_mode | 0o755)  # 清单声明 executable:true，须与事实一致
                deployed.append({"target": destination, "created": created})

            install_dir = os.path.join(args.target, ".wf/install")
            os.makedirs(install_dir, exist_ok=True)
            manifest_copy = os.path.join(install_dir, "release-manifest.json")
            shutil.copyfile(manifest_path, manifest_copy)
            manifest_digest = file_digest(manifest_copy)
            installation = {
                "schema_version": 1,
                "install_id": uuid.uuid4().hex,
                "release_ref": args.release_ref,
                "source_commit": commit,
                "version": manifest.get("version"),
                # 内容级来源身份：同 commit 重建发行会让摘要变化，追加平台据此判同源（F8-4）
                "rules_digest": (manifest.get("compatibility") or {}).get("rules_digest"),
                "manifest_digest": manifest_digest,
                "platforms": sorted({PLATFORM_ALIASES.get(name, name) for name in _flatten_platforms(args.platform)}),
                "roots": [os.path.relpath(root, args.target).replace(os.sep, "/") for root in skill_roots],
                "assets": [{"target": relative, "root_ref": "project" if base == args.target else base,
                            "digest": asset.get("digest"), "source_path": asset.get("source_path")}
                           for base, asset, relative in writes],
                "decisions": ([{"kind": "branch-source", "findings": branch_findings,
                                "decision": "human (--confirm)", "at": now_str(),
                                "note": "人确认在本分支按新安装继续（设计稿 §7.1）"}]
                              if branch_findings else []),
                "installed_at": now_str(),
                "tool": "install.py",
            }
            with open(os.path.join(install_dir, "installation.json"), "w", encoding="utf-8", newline="\n") as handle:
                handle.write(json.dumps(installation, indent=2, sort_keys=True, ensure_ascii=False) + "\n")
            with open(os.path.join(install_dir, "recovery.md"), "w", encoding="utf-8", newline="\n") as handle:
                handle.write(recovery_text(args.target, installation))
            gitignore = ensure_gitignore(args.target, manifest)
            problems = self_check(args.target, manifest, skill_roots)
            if problems:
                writer["state"] = "recovering"
                writer["checkpoint"] = {"operation": operation_id, "phase": "self-check-failed",
                                        "problems": problems[:20]}
                with open(os.path.join(args.target, ".wf/writer.json"), "w", encoding="utf-8") as handle:
                    handle.write(json.dumps(writer, indent=2, sort_keys=True, ensure_ascii=False) + "\n")
                return blocked("WF_CAPABILITY_UNAVAILABLE", "投放后自检失败，保留维护检查点",
                               {"problems": problems[:20]}, args.json)

            head_before = None
            import subprocess

            probe = subprocess.run(["git", "-c", "safe.directory=*", "rev-parse", "HEAD"], cwd=args.target, capture_output=True, text=True,
                                   check=False)
            if probe.returncode == 0:
                head_before = probe.stdout.strip() or None
            # 回执路径一律项目相对：运行期按相对路径做重叠匹配与 Git 树查证
            changes = [{"path": os.path.relpath(entry["target"], args.target).replace(os.sep, "/"),
                        "before": None, "after": file_digest(entry["target"])}
                       for entry in deployed if entry["created"]]
            writer["maintenance_results"] = [{
                "operation": operation_id,
                "preview_digest": plain_digest(installation),
                "head_before": head_before,
                "changes": changes,
                "receipt_git_state": {"head": head_before, "tracked_paths": len(changes)},
                "result": "applied_pending_commit",
                "disposition": None,
            }]
            writer["state"] = "idle"
            writer["holder"] = None
            writer["generation"] = 2
            writer["checkpoint"] = {"operation": operation_id, "phase": "installed"}
            writer["revision"] = 1
            with open(os.path.join(args.target, ".wf/writer.json"), "w", encoding="utf-8", newline="\n") as handle:
                handle.write(json.dumps(writer, indent=2, sort_keys=True, ensure_ascii=False) + "\n")

    except LockRejected as exc:
        return blocked("WF_ASSET_DECISION", f"锁对象冲突：{exc}", {"path": lock_path}, args.json)
    except LockBusy as exc:
        return blocked("WF_WRITER_BUSY", f"锁被占用：{exc}", {"path": lock_path}, args.json)
    message = "\n".join([
        "OK  WF_OK",
        f"目标：{args.target}",
        f"发行引用：{args.release_ref} → {commit}",
        f"投放：{len([item for item in deployed if item['created']])} 个新文件",
        f"清单摘要：{manifest_digest}",
        f"规则摘要：{(manifest.get('compatibility') or {}).get('rules_digest')}",
        f"托管段：{gitignore.get('action')}",
        "下一步：人执行 wf.py confirm-executor --scope system，然后 /wf-start",
    ])
    return ok(message, {"installation": installation, "gitignore": gitignore}, args.json)



ASSET_CLASSES = ("project_wf", "skill_root")
NON_DEPLOYED_CLASSES = ("release_only",)


def safe_relative(relative):
    """清单里的目标必须是仓库相对路径：无绝对、无 `..`、无空段、无反斜杠/盘符（设计稿 §7.3）。"""
    if not isinstance(relative, str) or not relative:
        return False
    if relative.startswith("/") or "\\" in relative or ":" in relative.split("/")[0]:
        return False
    for part in relative.split("/"):
        if part in ("", ".", ".."):
            return False
    return True


def inside(base, path):
    """真实落点必须仍在基址内（防符号链接逃逸）。"""
    base_real = os.path.realpath(str(base))
    path_real = os.path.realpath(str(path))
    return path_real == base_real or path_real.startswith(base_real + os.sep)


def plan_writes(target, skill_roots, manifest):
    """把清单展开成写入计划；任一条目不合规即**整批拒绝**（不写入任何文件）。

    与 `uninstall.py` 同判据：安全相对路径 + 真实落点包含 + 目标类别白名单。
    """
    problems = []
    writes = []
    for asset in manifest.get("assets") or []:
        target_class = asset.get("target_class")
        relative = asset.get("target_relative")
        if target_class in NON_DEPLOYED_CLASSES:
            continue
        if target_class not in ASSET_CLASSES:
            problems.append({"reason": "unknown target_class", "target_class": target_class,
                             "path": relative})
            continue
        if not safe_relative(relative):
            problems.append({"reason": "target_relative is not a safe relative path",
                             "target_class": target_class, "path": relative})
            continue
        bases = [target_of(target)] if target_class == "project_wf" else list(skill_roots)
        for base in bases:
            destination = os.path.join(base, *relative.split("/"))
            if not inside(base, destination):
                problems.append({"reason": "target resolves outside its base", "base": str(base),
                                 "path": relative})
                continue
            writes.append((base, asset, relative))
    if problems:
        return [], problems  # 整批拒绝：只要有一条不合规就不给出任何写入计划
    return writes, problems





def _evidence_entry(item):
    """`kind=<种类>;ref=<观察引用>;by=<声明人>` → 证据条目（与 dev-deploy 同解析）。"""
    fields = dict(part.split("=", 1) for part in str(item).split(";") if "=" in part)
    entry = {"declared_by": fields.get("by", "human preview"),
             "kind": fields.get("kind"),
             "ref": fields.get("ref")}
    return {key: value for key, value in entry.items() if value}

OBSERVATION_KINDS = ("compaction", "reentry", "new-session", "transport")


def target_of(target):
    return os.path.abspath(target)


if __name__ == "__main__":
    if sys.version_info < MIN_VERSION:
        sys.stderr.write(f"wf install.py requires Python >= {MIN_VERSION[0]}.{MIN_VERSION[1]}\n")
        raise SystemExit(1)
    raise SystemExit(main())
