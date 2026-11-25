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


def append_maintenance_journal(target: str, receipt: dict) -> None:
    """把回执写进**提交层**账本 `.wf/install/maintenance.jsonl`（机制稿 §4.5）。

    自含实现：本文件不 import wflib（安装前就要能跑），算法与 `wflib.maintenance.append` 同一形状。
    `.wf/writer.json` 是运行态（v42 S10 忽略），不能拿它当"已持久化"的证据。
    """
    record = {
        "operation": receipt.get("operation"),
        "preview_digest": receipt.get("preview_digest"),
        "head_before": receipt.get("head_before"),
        "changes": [dict(item) for item in receipt.get("changes") or [] if isinstance(item, dict)],
        "at": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
    }
    path = os.path.join(target, ".wf", "install", "maintenance.jsonl")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")


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
               "object": None,
               "position": {"scope": "maintenance", "phase": None, "step_id": None,
                            "task_id": None, "action_id": None, "action_state": None},
               "next": message,
               "exit": (facts or {}).get("exit") or message,
               "prohibited_repairs": "不自动改写安装记录/不绕过参数与边界校验",
               "warnings": []}
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
               "object": None,
               "position": {"scope": "maintenance", "phase": None, "step_id": None,
                            "task_id": None, "action_id": None, "action_state": None},
               "next": message,
               "exit": (facts or {}).get("exit") or message,
               "prohibited_repairs": "不代为选择/不伪造批准或写权",
               "warnings": []}
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
        sys.stdout.write(json.dumps({"ok": True, "code": "WF_OK", "tier": "pass",
                                     "object": None,
                                     "position": {"scope": "maintenance", "phase": None, "step_id": None,
                                                  "task_id": None, "action_id": None, "action_state": None},
                                     "next": message, "exit": None,
                                     "prohibited_repairs": None, "warnings": [],
                                     "message": message,
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


def global_config_path():
    return os.path.join(os.path.expanduser("~"), ".wf", "config.json")


def probe_python_version(path):
    """返回 "Python 3.x.y" 或 None；只用于安装期人面预检。"""
    try:
        result = subprocess.run([path, "--version"], capture_output=True, text=True, check=False)
    except OSError:
        return None
    text = (result.stdout or result.stderr or "").strip()
    if result.returncode != 0:
        return None
    return text or None


def python_candidate_problems(path):
    """安装期解释器候选的预检：存在、可执行、CPython>=3.11。返回问题文本或 None。"""
    if not os.path.isabs(path):
        return "解释器路径必须是绝对路径"
    if not os.path.isfile(path) or not os.access(path, os.X_OK):
        return "不是可执行文件"
    version = probe_python_version(path)
    match = re.match(r"Python\s+(\d+)\.(\d+)", version or "")
    if not match:
        return "探测不到 Python 版本"
    major, minor = int(match.group(1)), int(match.group(2))
    if major != 3 or minor < 11:
        return f"需要 Python >= 3.11（实际 {version}）"
    return None


def write_global_executor(path):
    """把安装时人选的解释器写入本机用户级配置（保留其它键）。返回问题文本或 None。"""
    config = global_config_path()
    directory = os.path.dirname(config)
    os.makedirs(directory, exist_ok=True)
    data = {}
    if os.path.exists(config):
        try:
            with open(config, "r", encoding="utf-8") as handle:
                data = json.load(handle)
        except (OSError, ValueError) as exc:
            return f"全局配置不可读/不是合法 JSON：{exc}"
        if not isinstance(data, dict):
            return "全局配置不是 JSON 对象"
    data["python_executable"] = path
    temporary = config + ".tmp-install"
    with open(temporary, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False) + "\n")
    os.replace(temporary, config)
    return None


def confirm_executor(target, candidate, scope):
    """在安装进程的终端里转交 bootstrap 的确认动作：提示与写入都只由那一个实现做。"""
    command = [candidate, os.path.join(target, ".wf/bin/wf.py"), "confirm-executor", "--scope", scope]
    try:
        result = subprocess.run(command)
    except OSError as exc:
        return None, {"reason": f"无法启动解释器确认：{exc}", "command": command}
    return result.returncode, {"scope": scope, "candidate": candidate, "rc": result.returncode}


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


def _repo_root_and_rel(source):
    """返回 (repo_top, rel)；source 不在 git 工作树内返回 (None, 原因)。"""
    import subprocess

    top = subprocess.run(["git", "-c", "safe.directory=*", "rev-parse", "--show-toplevel"], cwd=source,
                         capture_output=True, text=True, check=False)
    if top.returncode != 0:
        return None, "not a git worktree"
    repo_top = os.path.realpath((top.stdout or "").strip())
    rel = os.path.relpath(os.path.realpath(source), repo_top)
    if rel.startswith(".."):
        return None, "source path is outside the git worktree"
    return repo_top, rel


def _worktree_clean(source):
    """发行源必须是干净检出：脏检出（或被人重算过摘要的树）不得冒充 tag 内容（第二十六轮复审外部 1）。"""
    import subprocess

    # 只看**发行子树**：发行树可能位于一个本身有未提交改动的仓库里（作者仓库），
    # 但发行目录自己的内容必须与提交一致，否则摘要校验相对工作树即无意义。
    repo_top, rel = _repo_root_and_rel(source)
    if repo_top is None:
        return None, rel
    result = subprocess.run(["git", "-c", "safe.directory=*", "status", "--porcelain", "--", rel], cwd=repo_top,
                            capture_output=True, text=True, check=False)
    if result.returncode != 0:
        return None, "not a git worktree"
    dirty = [line for line in (result.stdout or "").splitlines() if line.strip()]
    if dirty:
        return False, dirty[:10]
    return True, []


def _committed_bytes(source, commit, path):
    """按 tag 提交读发行资产字节（设计稿 §7.2：提交哈希只用于核验内容）。失败返回 None。

    `source` 是**发行检出目录**，可能位于仓库的子目录（作者仓库就是 `docs/workflows/wf-release/`）。
    `git show <commit>:<path>` 的路径按仓库根解释，所以这里必须把 source 相对仓库根的前缀
    拼在 `path` 前——否则子目录布局会被误报「missing in tag commit tree」，只能先另建一个
    根级候选仓库才能安装（2026-11-25 安装步骤反人类的根因）。
    """
    import subprocess

    repo_top, rel = _repo_root_and_rel(source)
    if repo_top is None:
        return None
    prefix = "" if rel in (".", "", os.sep) else rel.replace(os.sep, "/").rstrip("/") + "/"
    result = subprocess.run(["git", "-c", "safe.directory=*", "show", f"{commit}:{prefix}{path}"],
                            cwd=repo_top, capture_output=True, check=False)
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
        if asset.get("target_class") == "host_hook" and not (isinstance(asset.get("platform"), str)
                                                            and asset.get("platform").strip()):
            problems.append({"asset": asset.get("source_path"),
                             "reason": "host_hook asset requires a platform"})
        if asset.get("target_class") != "host_hook" and asset.get("platform") is not None:
            problems.append({"asset": asset.get("source_path"),
                             "reason": "platform key only allowed on host_hook assets"})
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
    """安装/维护动作的互斥。判据与 `wflib/lock.py` 同源，只是不导入运行时。

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
    """托管段正文**只来自清单** `gitignore_managed`：这是忽略集合的唯一枚举。

    此前这里留了一份两行回退，与发行清单的五条不同源；回退值会静默写出半个托管段，
    因此改为缺登记即抛错，由安装主流程转成 `WF_ASSET_DECISION`。
    """
    managed = manifest.get("gitignore_managed") or {}
    lines = [managed.get("begin_marker"), *list(managed.get("lines") or []),
             managed.get("end_marker")]
    if not all(isinstance(item, str) and item.strip() for item in lines):
        raise ValueError("gitignore_managed incomplete (begin_marker/lines/end_marker required)")
    return "\n".join(lines)


def plan_gitignore(target, manifest):
    """**只读**判定 `.gitignore` 托管段该做什么（2026-11-23 五轮复审 a-P2）。

    与 hooks.json 同一处置形状：`.gitignore` 也是**用户文件**，写它之前必须能判、能预览、
    能进回执。旧实现把"判定 + 写入"耦在一个函数里，于是首装既无法在 `--confirm` 前显示
    托管段会怎么变，也无法在冲突时不写而先报——只能先写后由自检兜底。
    """
    path = os.path.join(target, ".gitignore")
    segment = managed_segment(manifest)
    before = file_digest(path)
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
        return {"path": path, "action": "present" if current == segment else "conflict",
                "before_digest": before, "segment": segment,
                "current_segment": current if current != segment else None}
    return {"path": path, "action": "appended", "before_digest": before, "segment": segment,
            "current_segment": None}


def apply_gitignore(target, manifest, plan=None):
    """按 `plan_gitignore` 的动作落地（`appended` 才写；`present/conflict` 不动用户文件）。"""
    plan = plan or plan_gitignore(target, manifest)
    if plan["action"] != "appended":
        return dict(plan, after_digest=file_digest(plan["path"]))
    path = plan["path"]
    text = ""
    try:
        with open(path, "r", encoding="utf-8") as handle:
            text = handle.read()
    except FileNotFoundError:
        text = ""
    if text and not text.endswith("\n"):
        text += "\n"
    text += plan["segment"] + "\n"
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)
    return dict(plan, after_digest=file_digest(path))


def ensure_gitignore(target, manifest):
    """判定 + 落地（升级路径沿用的既有入口；判据本身在 `plan_gitignore`）。"""
    plan = plan_gitignore(target, manifest)
    applied = apply_gitignore(target, manifest, plan)
    applied.pop("segment", None)
    applied.pop("current_segment", None)
    return applied


def stage_release_manifest(target, source):
    """把本次发行清单复制到 `.wf/install/release-manifest.json` 的临时位。

    升级必须更新这个副本：运行期 `assets.load_installed_manifest` 与卸载都用
    `installation.manifest_digest` 核它。旧实现只改 installation 里的摘要、
    不动副本，升级后运行时/卸载直接判清单失配。复制后先比摘要，不等写安装记录。
    返回 (staged, problem)；staged = {tmp, path, digest}。
    """
    path = os.path.join(target, ".wf/install/release-manifest.json")
    tmp = path + ".wf-upgrade-tmp"
    source_manifest = os.path.join(source, "wf-release.json")
    try:
        project = _resolve_location(target)
        if not (_contains(project, _resolve_location(path)) and _contains(project, _resolve_location(tmp))):
            return None, {"reason": "release-manifest path resolves outside project root",
                          "path": path, "tmp": tmp}
        if os.path.islink(tmp):
            return None, {"reason": "staged manifest path is a symlink", "tmp": tmp}
        shutil.copyfile(source_manifest, tmp)
    except OSError as exc:
        return None, {"reason": "manifest copy failed", "detail": str(exc), "source": source_manifest}
    copy_digest = file_digest(tmp)
    source_digest = file_digest(source_manifest)
    if copy_digest != source_digest:
        return None, {"reason": "manifest digest changed after copy",
                      "copy": copy_digest, "source": source_digest}
    return {"tmp": tmp, "path": path, "digest": copy_digest}, None


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


SKILL_REQUIRED_FIELDS = ("name", "description")


def skill_frontmatter_problems(path):
    """投放后的 `SKILL.md` frontmatter 必须可解析（设计稿 §1.2）。

    只核**结构与必填**：起止 `---` 成对、`name`/`description` 非空。
    不核语义（写得对不对是人的判断），也不改文件——问题一律返回给调用方汇总。
    """
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as handle:
            lines = handle.read().splitlines()
    except OSError as exc:
        return [f"unreadable: {exc}"]
    if not lines or lines[0].strip() != "---":
        return ["frontmatter missing"]
    fields = {}
    problems = []
    for line in lines[1:]:
        if line.strip() == "---":
            break
        if not line.strip() or line.strip().startswith("#"):
            continue
        if ":" not in line:
            problems.append(f"invalid frontmatter line: {line[:40]!r}")
            continue
        key, raw = line.split(":", 1)
        key = key.strip()
        if key in fields:
            problems.append(f"duplicate key: {key}")
            continue
        fields[key] = raw.strip()
    else:
        problems.append("frontmatter not closed")
    for field in SKILL_REQUIRED_FIELDS:
        if not fields.get(field):
            problems.append(f"frontmatter field missing or empty: {field}")
    return problems


def accepted_local_digests(target, installation):
    """人确认保留（`--keep`）的偏离：绝对路径 → 登记的本地指纹。

    `self_check` 与重复安装核对共用这一处，避免"自检认、核对不认"的分叉。
    """
    accepted = {}
    for entry in (installation or {}).get("assets") or []:
        if not isinstance(entry, dict) or not entry.get("decision"):
            continue
        local = entry.get("local_fingerprint")
        if not local or not entry.get("target"):
            continue
        base = _abs_base(target, entry.get("root_ref"))
        accepted[os.path.normpath(os.path.join(base, *entry["target"].split("/")))] = local
    return accepted


def self_check(target, manifest, skill_roots, installation=None, intentional_missing=None):
    """安装/升级后自检（§10.4）。

    安装面向全部平台，自检因此**核全部平台根与全部 hook 资产**：没有"未声明的平台"
    这一说，缺一份就是缺（2026-11-23 人裁）。

    2026-11-23：升级传入 `installation`——已接受偏离（deviation-kept/--keep）的
    目标字节等于登记 `local_fingerprint` 时不算失配；`intentional_missing` 是
    人确认保留删除/退出托管的路径（设计稿 §7.2 表首行与新增撞用户文件），
    自检不把它当“升级已恢复/已管理”。
    """
    intentional_missing = set(intentional_missing or ())
    accepted = accepted_local_digests(target, installation)
    problems = list(_host_hook_plan_problems(manifest))
    for index, asset in enumerate(manifest.get("assets") or []):
        if not isinstance(asset, dict):
            problems.append({"reason": "asset entry is not an object", "index": index})
            continue
        if asset.get("target_class") == "release_only":
            continue
        relative = asset.get("target_relative") or ""
        if asset.get("target_class") == "host_hook":
            path = os.path.join(target, *relative.split("/"))
            if path in intentional_missing:
                continue
            actual = file_digest(path)
            accepted_ok = actual is not None and accepted.get(os.path.normpath(path)) == actual
            if actual != asset.get("digest") and not accepted_ok:
                problems.append({"target": path, "reason": "digest mismatch after deploy"})
            elif asset.get("platform") == "codex":
                # W3（2026-11-23）：脚本字节对不等于部署面生效——宿主 `hooks.json` 的条目
                # 才是会话标识真正被调用的地方。条目缺失/命令串漂移必须在此报出，
                # 否则"改落点/命令串"的发行会让已升级项目带着失效条目运行且自检报绿。
                expected = host_hook_command(relative)
                hook_plan = plan_hooks_json(target, relative, expected)
                if hook_plan["action"] == "unreadable":
                    problems.append({"target": hook_plan["path"],
                                     "reason": "hooks.json unreadable",
                                     "detail": (hook_plan.get("problem") or {}).get("reason")})
                elif hook_plan["action"] in ("absent", "appended", "conflict", "updated"):
                    problems.append({"target": hook_plan["path"],
                                     "reason": "host hook entry missing or drifted",
                                     "action": hook_plan["action"],
                                     "expected_command": expected,
                                     "observed": hook_plan.get("observed"),
                                     "previous_command": hook_plan.get("previous_command")})
            continue
        targets = []
        if asset.get("target_class") == "project_wf":
            targets.append(os.path.join(target, *relative.split("/")))
        else:
            for root in skill_roots:
                targets.append(os.path.join(root, *relative.split("/")))
        for path in targets:
            if path in intentional_missing:
                continue
            actual = file_digest(path)
            accepted_ok = actual is not None and accepted.get(os.path.normpath(path)) == actual
            if actual != asset.get("digest") and not accepted_ok:
                problems.append({"target": path, "reason": "digest mismatch after deploy"})
            elif asset.get("kind") == "skill":
                # 设计稿 §1.2 要求投放后 frontmatter 可解析；此前自检只核摘要与运行时
                for detail in skill_frontmatter_problems(path):
                    problems.append({"target": path, "reason": f"skill frontmatter: {detail}"})
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
#   - **`env:` 前缀 ≠ 已实现**（2026-11-23 五轮）：它只表示"该值在适配层/显式信封可见"。
#     未交付适配层的宿主（今天除 codex 外全部）在运行期等同 `unknown`——入口不读环境变量，
#     可区分性由 `enable --new-session` 覆盖；不得把该声明读成"宿主会话标识已可用"。
PLATFORMS = {
    "dsh": {
        "dir": ".agents/skills",
        "reads_shared": True,
        # DSH 托管 shell 注入 DSH_SESSION_ID；DSH 无 /clear 命令（2026-11-09 用户实测）
        # **`env:` 声明 ≠ 已交付适配层**：入口不读该环境变量，运行期等同 `unknown`，
        # 可区分性由 `enable --new-session` 覆盖（2026-11-23 人裁后全平台一次装齐，
        # 这条限定尤其要读清：装齐 ≠ 该宿主的会话标识已可用）
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
SHARED_SKILL_DIR = ".agents/skills"


def all_platforms():
    """安装面向的**全部**平台：`PLATFORMS` 是唯一来源，新增平台即自动纳入。

    2026-11-23 人裁：安装不再让人选平台（`--platform` 已移除）——目标项目一次装齐
    当前支持的全部平台根与宿主 hook；将来扩平台只改这张表，重跑安装/升级即补齐。
    """
    return sorted(PLATFORMS)


def resolve_skill_roots(target):
    """项目内技能目录全集（绝对路径，已去重）：所有平台的有读根的并集。"""
    roots = []
    for name in all_platforms():
        entry = PLATFORMS[name]
        relative = SHARED_SKILL_DIR if entry["reads_shared"] else entry["dir"]
        root = os.path.join(os.path.abspath(target), *relative.split("/"))
        if root not in roots:
            roots.append(root)
    return roots


def _dump_json(path, payload):
    """原子替换写入：中断不会留下半截 JSON（与 uninstall.py 同标准）。"""
    text = json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    temporary = f"{path}.tmp-{os.getpid()}"
    with open(temporary, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)


HOOK_SCRIPT_RELATIVE = ".codex/hooks/wf-session-identity.py"


def host_hook_command(script_relative):
    """宿主 hook 的命令串：**只由落点派生**（唯一来源）。

    升级要判断 hooks.json 里的条目"是不是本框架的旧串"，判据必须是可重算的同一形态；
    把命令串写成第二份常量会让落点一改就与派生值分叉。
    """
    return f"python3 -X utf8 {script_relative}"



def hooks_json_path(target):
    return os.path.join(os.path.abspath(target), ".codex", "hooks.json")


def _hooks_entry_matches(entry, script_name):
    """所有权判定：命令串引用本脚本文件名即属我们（无标记段机制可借，
    命令串含唯一脚本路径是确定性归属）。"""
    hooks = entry.get("hooks") if isinstance(entry, dict) else None
    if not isinstance(hooks, list):
        return False
    for hook in hooks:
        if isinstance(hook, dict) and script_name in str(hook.get("command") or ""):
            return True
    return False


def read_hooks_json(target):
    """读 `.codex/hooks.json`：`(data, problem)`；缺失返回 `(None, None)`（≠ 损坏）。"""
    path = hooks_json_path(target)
    if not os.path.isfile(path):
        return None, None
    try:
        with open(path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, ValueError) as exc:
        return None, {"path": path, "reason": f"hooks.json 不可解析: {exc}"}
    if not isinstance(data, dict) or not isinstance(data.get("hooks"), dict):
        return None, {"path": path, "reason": "hooks.json 形状不属 Codex（缺 hooks 对象）"}
    return data, None


def _hook_entries(data, script_name):
    """所有事件下"命令串引用本脚本名"的条目（所有权判定的单一实现）。"""
    found = []
    for event, entries in ((data or {}).get("hooks") or {}).items():
        if not isinstance(entries, list):
            continue
        for index, entry in enumerate(entries):
            if _hooks_entry_matches(entry, script_name):
                found.append((event, index, entry))
    return found


HOOK_EVENT = "SessionStart"


def plan_hooks_json(target, script_relative, command, previous_command=None, event=HOOK_EVENT):
    """**只读**判定 hooks.json 该做什么（升级预览与锁内重核共用，W3 2026-11-23）。

    **事件也是部署面的一部分**（2026-11-23 五轮复审 b-4）：命令串挂在别的事件下，
    会话启动时根本不会触发，"条目存在"不等于"适配面生效"——所以只在 `event`
    （默认 `SessionStart`）里找本脚本；出现在其它事件里按 `conflict` 交人。

    `host_hook` 是随发行投放的资产类，它的部署面包含宿主 `hooks.json` 条目——只替换脚本
    字节而不维护条目，会让"改落点/命令串"的发行在已升级项目上留下失效条目，而自检只核
    脚本 digest 仍报绿（dogfood 五轮 b-P1 的事实面）。

    动作取值（判定顺序唯一）：
    - `absent`：`.codex/hooks.json` 不存在 ⇒ 投放时会创建（首装语义）；
    - `appended`：文件在、没有引用本脚本的条目 ⇒ 追加；
    - `unchanged`：条目命令串已是当前值；
    - `updated`：条目命令串等于**上一版登记**的命令串（本框架旧条目）⇒ 替换；
    - `conflict`：条目引用本脚本但既非当前也非上一版（用户改过）⇒ 交人，不覆盖；
    - `unreadable`：文件不可解析 ⇒ 交人（不自作主张重写用户文件）。
    """
    data, problem = read_hooks_json(target)
    plan = {"path": hooks_json_path(target), "script_relative": script_relative,
            "command": command, "previous_command": previous_command, "event": event}
    if problem:
        return dict(plan, action="unreadable", problem=problem)
    if data is None:
        return dict(plan, action="absent")
    found = _hook_entries(data, os.path.basename(script_relative))
    misplaced = [(found_event, index, entry) for found_event, index, entry in found
                 if found_event != event]
    found = [(found_event, index, entry) for found_event, index, entry in found
             if found_event == event]
    # `matcher` 同样是触发条件的一部分：条目挂在 SessionStart 上、命令串也对，但 matcher
    # 限定成 `compact`（或其它不匹配的表达式）时，会话启动根本不会调用它——"条目存在"
    # 不等于"适配面生效"（2026-11-23 九轮复审 b-4）。我们的条目由本安装器写入、不带 matcher；
    # 发现 matcher 即按偏离交人，不猜它的语义。
    matcher_entry = None
    for found_event, index, entry in found:
        matcher = entry.get("matcher")
        if matcher not in (None, "", {}):
            matcher_entry = entry
            break
    if matcher_entry is not None:
        return dict(plan, action="conflict", matcher=matcher_entry.get("matcher"),
                    reason=f"本脚本条目带 matcher（限定触发条件，应在 {event} 无条件触发）：交人")
    if not found and misplaced:
        return dict(plan, action="conflict", observed_events=[item[0] for item in misplaced],
                    reason=f"本脚本条目挂在其它事件下（应在 {event}）：交人，不自动搬动")
    if not found:
        return dict(plan, action="appended")
    current = [(event, index, entry) for event, index, entry in found
               if all(str(hook.get("command")) == command
                      for hook in (entry.get("hooks") or []) if isinstance(hook, dict))]
    if current:
        return dict(plan, action="unchanged", event=current[0][0])
    if previous_command and previous_command != command:
        stale = [(event, index, entry) for event, index, entry in found
                 if all(str(hook.get("command")) == previous_command
                        for hook in (entry.get("hooks") or []) if isinstance(hook, dict))]
        if stale:
            return dict(plan, action="updated", event=stale[0][0],
                        observed_command=previous_command)
    observed = [str((entry.get("hooks") or [{}])[0].get("command")) for _e, _i, entry in found]
    return dict(plan, action="conflict", observed=observed)


def apply_hooks_json(target, plan):
    """按 `plan_hooks_json` 的动作落地（升级应用段）。返回实际动作（幂等）。"""
    action = plan["action"]
    if action in ("unchanged", "conflict", "unreadable"):
        return action
    script_relative = plan["script_relative"]
    command = plan["command"]
    path = hooks_json_path(target)
    event = plan.get("event") or HOOK_EVENT
    if action == "absent":
        os.makedirs(os.path.dirname(path), exist_ok=True)
        _dump_json(path, {"hooks": {event: [
            {"hooks": [{"type": "command", "command": command, "timeout": 15}]}]}})
        return "created"
    data, problem = read_hooks_json(target)
    if problem:
        raise ValueError(problem["reason"])
    session_start = data["hooks"].get(event)
    if not isinstance(session_start, list):
        session_start = []
        data["hooks"][event] = session_start
    if action == "appended":
        session_start.append({"hooks": [{"type": "command", "command": command, "timeout": 15}]})
        _dump_json(path, data)
        return "appended"
    if action == "updated":
        for _event, _index, entry in _hook_entries(data, os.path.basename(script_relative)):
            for hook in entry.get("hooks") or []:
                if isinstance(hook, dict) and str(hook.get("command")) == plan["previous_command"]:
                    hook["command"] = command
        _dump_json(path, data)
        return "updated"
    raise ValueError(f"未知 hooks.json 动作：{action}")


def remove_hooks_json_entry(target, script_name=HOOK_SCRIPT_RELATIVE):
    """卸载对称移除：只删命令串引用本脚本的条目；空列表/空 hooks 保留文件结构（用户文件不删）。

    返回移除的条目数。
    """
    path = hooks_json_path(target)
    if not os.path.isfile(path):
        return 0
    try:
        with open(path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, ValueError):
        return 0
    if not isinstance(data, dict) or not isinstance(data.get("hooks"), dict):
        return 0
    removed = 0
    for event, entries in list(data["hooks"].items()):
        if not isinstance(entries, list):
            continue
        kept = [item for item in entries
                if not (_hooks_entry_matches(item, os.path.basename(script_name)))]
        removed += len(entries) - len(kept)
        if kept:
            data["hooks"][event] = kept
        else:
            data["hooks"][event] = kept      # 空列表保留结构：用户文件不删
    if removed:
        _dump_json(path, data)
    return removed


def _first_install_takeover(writer_record):
    """能否把既有 writer 记录当作"未完成首装"重入（返回 None=可接管，否则给原因）。

    可接管只有两类（2026-11-23 六轮复审 a-1）：
    - 无持有者（`holder is None`）：idle 或 recovering——没有活会话在等这份写权；
    - 持有者是**本框架的维护动作**且检查点属于安装阶段：进程崩溃后留下的装维护记录。
    会话持有（`holder.kind=session`）、交接中间态、未知检查点一律不可接管：那是在途的
    合法权益，接管它等于越过 §4.4 的持有边界。
    """
    holder = (writer_record or {}).get("holder")
    if holder is None:
        return None
    if not isinstance(holder, dict):
        return "holder 字段形状不可识别"
    if holder.get("kind") != "maintenance":
        return f"写权由 {holder.get('kind')!r} 持有（非维护动作）"
    phase = ((writer_record.get("checkpoint") or {}).get("phase") or "")
    if phase.startswith("install") or phase in ("deploy-assets", "hooks-json-apply",
                                                "self-check-failed"):
        return None
    return f"维护检查点不是安装阶段（phase={phase!r}）"


def maintenance_abort(writer_path, writer, operation_id, phase, code, message, facts=None,
                     json_mode=False):
    """维护动作在**已开始写入**之后失败时的唯一出口（2026-11-23，五轮复审 P1）。

    维护写者一旦置为 held，任何"直接 return"都会把项目留在两个坏状态之一：
    写权 held 无人释放（后续入口全被 WF_WRITER_BUSY 挡住），或半套资产没有对应记录。
    与"投放后自检失败"同一处置：写 recovering 检查点、递增代次、保留现场，并给出
    「按 problems 修正后重跑 / repair 核对恢复后重跑」两个出口——不把 PID 消失当空闲，
    也不假装成功。来源：安装自检失败分支的既有语义（`self-check-failed`）。
    """
    problems = list((facts or {}).get("problems") or [])
    writer.update({
        "state": "recovering",
        "holder": None,
        "generation": int(writer.get("generation") or 0) + 1,
        "revision": int(writer.get("revision") or 0) + 1,
        "updated_at": now_str(),
        "checkpoint": {"operation": operation_id, "phase": phase, "problems": problems[:20]},
    })
    try:
        _dump_json(writer_path, writer)
    except OSError:
        pass                      # 写权记录写不下去也不掩盖真正的失败原因
    payload = dict(facts or {})
    payload.setdefault("exits", [
        "按 problems 修正后重跑同一条命令（已落盘事实按 §5.4 核对，不重复写入）",
        "或运行 .wf/bin/repair.py 核对恢复后再重跑",
    ])
    payload.setdefault("writer", {"state": "recovering", "checkpoint": writer.get("checkpoint")})
    return blocked(code, message, payload, json_mode)


def deployed_host_hooks(manifest):
    """本次投放会出现的 host_hook 条目：清单里声明的**全部** hook 资产。"""
    out = []
    for asset in manifest.get("assets") or []:
        if not isinstance(asset, dict) or asset.get("target_class") != "host_hook":
            continue
        relative = asset.get("target_relative")
        if not relative:
            continue
        out.append({"platform": asset["platform"], "script_relative": relative,
                    "command": host_hook_command(relative)})
    return out


def recorded_host_hooks(installation):
    """安装记录里的 `host_hook_entries`（上一版命令串的唯一来源，不靠猜）。"""
    out = {}
    for entry in (installation or {}).get("host_hook_entries") or []:
        if isinstance(entry, dict) and entry.get("script_relative"):
            out[str(entry["script_relative"])] = entry
    return out


def plan_host_hooks(target, manifest, installation):
    """逐 host_hook 资产给出 hooks.json 动作；`problems` 为需人裁决项。

    升级在**写入前**调用：`conflict`/`unreadable` 必须整批拒绝，不能先替换脚本字节再报错。
    """
    recorded = recorded_host_hooks(installation)
    plans, problems = [], []
    for item in deployed_host_hooks(manifest):
        if item["platform"] != "codex":
            # 只有 codex 声明了 hooks.json 部署面；其他平台的 host_hook 只投放脚本
            continue
        previous = (recorded.get(item["script_relative"]) or {}).get("command")
        plan = plan_hooks_json(target, item["script_relative"], item["command"], previous)
        plans.append(plan)
        if plan["action"] == "conflict":
            problems.append(dict(plan, reason="同名 hook 脚本的命令串既非当前也非上一版登记值："
                                              "用户改过，交人裁决（不覆盖）"))
        elif plan["action"] == "unreadable":
            problems.append(dict(plan, reason="hooks.json 不可解析：交人处置，不重写用户文件"))
    return plans, problems


def record_host_hooks(installation, manifest, applied, target=None):
    """把本次投放/应用的 host_hook 命令串写进安装记录（升级下次据此判"我们的旧串"）。"""
    recorded = recorded_host_hooks(installation)
    for item in deployed_host_hooks(manifest):
        entry = dict(item)
        entry["updated_at"] = now_str()
        if target:
            # 落点文件的项目相对路径：分类侧据此把"安装器投放/维护的配置文件"认作控制面，
            # 不让它每次都以未提交改动出现在 c 档（全部平台安装后 hooks.json 恒存在）。
            entry["hooks_json_path"] = os.path.relpath(hooks_json_path(target), target).replace(os.sep, "/")
        if item["script_relative"] in {plan["script_relative"] for plan in applied}:
            entry["hooks_json_action"] = next(
                plan.get("applied") or plan["action"] for plan in applied
                if plan["script_relative"] == item["script_relative"])
        recorded[item["script_relative"]] = entry
    installation["host_hook_entries"] = [recorded[key] for key in sorted(recorded)]
    return installation


def _host_hook_plan_problems(manifest):
    """per-asset 平台条件的合法性（三处拒之一，与 self_check/plan_writes 同判据）：
    platform 键只允许出现在 host_hook 资产；host_hook 必须带平台且属已知平台。"""
    problems = []
    for asset in manifest.get("assets") or []:
        if not isinstance(asset, dict):
            continue
        target_class = asset.get("target_class")
        platform = asset.get("platform")
        if target_class == "host_hook":
            if not isinstance(platform, str) or not platform.strip():
                problems.append({"reason": "host_hook asset requires a platform",
                                 "path": asset.get("target_relative") or asset.get("source_path")})
            elif platform not in PLATFORMS:
                problems.append({"reason": "host_hook platform is not a known platform",
                                 "platform": platform, "known": sorted(PLATFORMS),
                                 "path": asset.get("target_relative")})
        elif platform is not None:
            problems.append({"reason": "platform key only allowed on host_hook assets",
                            "target_class": target_class, "path": asset.get("target_relative")})
    return problems


def verify_installed(args, manifest, skill_roots, branch_findings=None):
    """目标已安装：重复执行同一条安装命令时的**补齐/核对**。

    安装面向全部平台（`all_platforms()`），"追加平台"这一步不再存在（2026-11-23 人裁）。
    三条边界：
    - hooks.json 冲突/不可解析 ⇒ `needs_decision`（先于任何写入，写权保持空闲）；
    - 落点**缺失**（上次中断/被删）⇒ 补写缺失文件与缺失的 hook 条目（只创建，不覆盖）；
    - 落点**有内容差异**（本地改过）⇒ 拒绝并指向 `--upgrade`（三方匹配能保留/恢复）。
    补写是维护动作：取写权、产回执、释放；无缺失时只读核对，不取写权、不产生空回执。
    """
    installation_path = os.path.join(args.target, ".wf/install/installation.json")
    writer_path = os.path.join(args.target, ".wf/writer.json")
    if not os.path.isfile(installation_path) or not os.path.isfile(writer_path):
        return blocked("WF_RECORD_INVALID", "安装记录或写权记录缺失，无法核对已安装状态",
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
            with open(installation_path, "r", encoding="utf-8") as handle:
                installation = json.load(handle)
            if not isinstance(installation, dict):
                return blocked("WF_RECORD_INVALID", "installation.json 不是对象", {}, args.json)
            recorded_version = installation.get("version")
            if recorded_version and str(recorded_version) != str(manifest.get("version")):
                return blocked(
                    "WF_ASSET_DECISION",
                    "目标装的是另一个版本：重跑安装只补本发行的缺失，跨版本请走升级",
                    {"installed_version": recorded_version,
                     "release_version": manifest.get("version"),
                     "exits": ["按升级流程处理：install.py --upgrade（先看预览，再 --apply）"]}, args.json)
            writes, plan_problems = plan_writes(args.target, skill_roots, manifest)
            if plan_problems:
                return blocked("WF_ASSET_DECISION",
                               "发行资产越界或不可解释：整批拒绝（未写入任何文件）",
                               {"problems": plan_problems[:20]}, args.json)
            hook_plans, hook_problems = plan_host_hooks(args.target, manifest, installation)
            if hook_problems:
                return needs_decision(
                    "WF_ASSET_DECISION",
                    "hooks.json 条目需人裁决：不覆盖用户改过的命令串（未写入任何文件、写权保持空闲）",
                    {"problems": hook_problems,
                     "exits": ["把 .codex/hooks.json 的该条目恢复成本框架条目后重跑",
                               "或人工确认该条目归用户所有、由人移走后再重跑"]}, args.json)
            accepted = accepted_local_digests(args.target, installation)
            pending, drifted = [], []
            for base, asset, relative in writes:
                path = os.path.join(base, *relative.split("/"))
                actual = file_digest(path)
                if actual is None:
                    pending.append((base, asset, relative))
                elif actual != asset.get("digest") and accepted.get(os.path.normpath(path)) != actual:
                    # 人确认保留的偏离（--keep）不是"本地改过"：与自检同一判据
                    drifted.append(os.path.relpath(path, args.target).replace(os.sep, "/"))
            stale_metadata = (sorted(installation.get("platforms") or []) != all_platforms()
                              or sorted(installation.get("roots") or [])
                              != sorted(os.path.relpath(root, args.target).replace(os.sep, "/")
                                        for root in skill_roots))
            hook_repairs = [plan for plan in hook_plans if plan["action"] in ("absent", "appended")]
            facts_base = {"platforms": all_platforms(),
                          "roots": [os.path.relpath(root, args.target).replace(os.sep, "/")
                                    for root in skill_roots]}
            if drifted:
                return blocked(
                    "WF_ASSET_DECISION",
                    "目标已安装，但落点内容与本发行不一致：这里不覆盖用户改动，改动请走升级（三方匹配）",
                    dict(facts_base, drifted=drifted[:20],
                         exits=["按升级流程处理：install.py --upgrade（先看预览，再 --apply）",
                                "只想确认现场：运行 .wf/bin/repair.py 核对"]), args.json)
            if pending or hook_repairs or stale_metadata:
                repaired_facts, abort = _repair_missing(args, manifest, writes, pending,
                                                        installation, hook_repairs)
                if abort is not None:
                    return abort
                facts_base = repaired_facts
    except (OSError, ValueError) as exc:
        return blocked("WF_RECORD_INVALID", f"读取安装记录失败：{exc}", {}, args.json)

    problems = self_check(args.target, manifest, skill_roots, installation=installation)
    if problems:
        return blocked(
            "WF_CAPABILITY_UNAVAILABLE",
            "落点与发行一致，但安装自检未通过：这次不是「什么都不用做」，而是安装仍未成立",
            dict(facts_base, self_check="problems", problems=problems[:20],
                 exits=["按 problems 修复（缺资产/落点/hook 条目）后重跑同一条命令",
                        "或用 .wf/bin/repair.py 核对恢复后重跑"]), args.json)
    lines = [
        "OK  WF_OK",
        f"目标：{args.target}",
        f"平台：{json.dumps(all_platforms(), ensure_ascii=False)}（全部支持平台已装）",
        f"说明：{facts_base.get('note', '无任何变化：落点与发行一致，未取写权、未产生回执')}；安装自检=clean。",
    ]
    if branch_findings:
        lines.append(f"分支来源：{len(branch_findings)} 条路径在当前分支缺失（已装内容不受影响）")
    payload = dict(facts_base, deployed=len(facts_base.get("restored") or []),
                   noop=not facts_base.get("restored"), self_check="clean")
    return ok("\n".join(lines), payload, args.json)


def _repair_missing(args, manifest, writes, pending, installation, hook_repairs):
    """补写缺失落点与缺失 hook 条目（只创建、不覆盖）。

    返回 `(facts, None)` 或 `(None, blocked_payload)`——调用方据此区分"补齐完成"与"中断"。
    """
    writer_path = os.path.join(args.target, ".wf/writer.json")
    with open(writer_path, "r", encoding="utf-8") as handle:
        writer = json.load(handle)
    if not isinstance(writer, dict):
        return None, blocked("WF_RECORD_INVALID", "写权记录不是对象：先用 repair 核对",
                             {"problems": ["record is not an object"]}, args.json)
    if writer.get("state") != "idle":
        # 合法的"忙"（held/recovering）不是坏记录：归因到写权边界，不误报记录非法
        return None, blocked("WF_WRITER_BUSY",
                       "补齐缺失落点需要空闲写权：当前写权不是空闲（先按 §4.4 释放/交接）",
                       {"writer": writer.get("state"), "holder": writer.get("holder")}, args.json)
    schema_problem = _writer_problem(writer)
    if schema_problem:
        return None, blocked("WF_RECORD_INVALID",
                             "写权记录不合法：补齐前必须先修记录（repair）",
                             {"problems": [schema_problem]}, args.json)
    operation_id = f"install-repair-{uuid.uuid4().hex}"
    import subprocess
    _probe = subprocess.run(["git", "-c", "safe.directory=*", "rev-parse", "HEAD"],
                            cwd=args.target, capture_output=True, text=True, check=False)
    head_before = _probe.stdout.strip() or None if _probe.returncode == 0 else None
    generation = int(writer.get("generation") or 0) + 1
    writer.update({
        "updated_at": now_str(), "state": "held", "generation": generation,
        "holder": {"kind": "maintenance", "id": operation_id,
                   "scope": {"operation": operation_id}, "generation": generation},
        "checkpoint": {"operation": operation_id, "phase": "install-repair"},
    })
    writer.setdefault("maintenance_results", [])
    with open(writer_path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(writer, indent=2, sort_keys=True, ensure_ascii=False) + "\n")

    source = os.path.abspath(args.source)
    restored, changes = [], []
    for base, asset, relative in pending:
        source_file = os.path.join(source, *asset["source_path"].split("/"))
        with open(source_file, "rb") as handle:
            content = handle.read()
        destination = os.path.join(base, *relative.split("/"))
        try:
            write_bytes(destination, content)
        except FileExistsError:
            return None, maintenance_abort(
                writer_path, writer, operation_id, "install-repair", "WF_ASSET_DECISION",
                "补齐时目标路径已被创建且内容不同：未覆盖，写者转入待恢复",
                {"path": destination,
                 "problems": [{"path": destination,
                               "reason": "target exists with different content"}]}, args.json)
        if asset.get("executable"):
            os.chmod(destination, os.stat(source_file).st_mode | 0o755)
        restored.append(os.path.relpath(destination, args.target).replace(os.sep, "/"))
        changes.append({"path": os.path.relpath(destination, args.target).replace(os.sep, "/"),
                        "before": None, "after": file_digest(destination)})
    hooks_path = hooks_json_path(args.target)
    hooks_before = file_digest(hooks_path)
    for plan in hook_repairs:
        try:
            plan["applied"] = apply_hooks_json(args.target, plan)
        except (ValueError, OSError) as exc:
            return None, maintenance_abort(
                writer_path, writer, operation_id, "install-repair", "WF_ASSET_DECISION",
                f"hooks.json 落地失败：{exc}",
                {"hooks_json": hooks_json_path(args.target),
                 "problems": [{"path": hooks_json_path(args.target), "reason": str(exc)}]}, args.json)
        changes.append({"path": os.path.relpath(hooks_path, args.target).replace(os.sep, "/"),
                        "before": hooks_before, "after": file_digest(hooks_path)})
    record_host_hooks(installation, manifest, hook_repairs, args.target)
    registered = {(str(entry.get("root_ref")), entry.get("target"))
                  for entry in installation.get("assets") or [] if isinstance(entry, dict)}
    assets = list(installation.get("assets") or [])
    for base, asset, relative in writes:
        key = ("project" if base == args.target else base, relative)
        if key in registered:
            continue
        assets.append({"target": relative, "root_ref": key[0], "digest": asset.get("digest"),
                       "source_path": asset.get("source_path"),
                       "upstream_version": manifest.get("version"),
                       "upstream_fingerprint": asset.get("digest")})
        registered.add(key)
    installation["assets"] = assets
    installation["roots"] = [os.path.relpath(root, args.target).replace(os.sep, "/")
                             for root in resolve_skill_roots(args.target)]
    installation["platforms"] = all_platforms()
    staged_manifest = os.path.join(args.target, ".wf/install/release-manifest.json")
    if os.path.isfile(staged_manifest):
        installation["manifest_digest"] = file_digest(staged_manifest)
    installation_path = os.path.join(args.target, ".wf/install/installation.json")
    changes.append({"path": ".wf/install/installation.json",
                    "before": file_digest(installation_path), "after": None})
    with open(installation_path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(installation, indent=2, sort_keys=True, ensure_ascii=False) + "\n")
    changes[-1]["after"] = file_digest(installation_path)
    # 回执与其它维护动作同一契约：head_before + 提交层账本登记，才算"可核的维护变更"
    # （运行期 `maintenance_persisted_probe` 按账本 + 可达提交核验；缺一即永远 pending_check）
    receipt = {"operation": operation_id, "kind": "install-repair",
               "at": now_str(), "generation": generation,
               "preview_digest": plain_digest(installation),
               "head_before": head_before,
               "changes": changes,
               "receipt_git_state": {"head": head_before, "tracked_paths": len(changes)},
               "result": "applied_pending_commit", "disposition": None,
               "hooks_json": [plan.get("applied") for plan in hook_repairs]}
    append_maintenance_journal(args.target, receipt)
    writer["maintenance_results"].append(receipt)
    writer.update({"state": "idle", "holder": None, "checkpoint": None,
                   "generation": generation + 1, "updated_at": now_str()})
    with open(writer_path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(writer, indent=2, sort_keys=True, ensure_ascii=False) + "\n")
    return ({"platforms": all_platforms(), "restored": sorted(restored),
             "receipt": receipt, "note": f"补齐 {len(restored)} 个缺失落点"
                                        + (f"、{len(hook_repairs)} 个 hooks 条目" if hook_repairs else "")},
            None)


def _writer_problem(writer, allow_recovering=False):
    """按运行期同一判据校验 writer（schema/状态组合/holder）。返回问题描述或 None。

    `allow_recovering=True` 仅供升级重入：自检失败留下的 recovering 允许再跑一次
    upgrade 作为恢复路径，不按字符串文案耦合。
    """
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
        return None if allow_recovering else "writer is recovering; 先按 repair 核对旧写者"
    if state != "idle":
        return f"writer state is {state!r}; 维护动作需在空闲时进行"
    generation = writer.get("generation")
    if not isinstance(generation, int) or isinstance(generation, bool):
        return "generation missing or not an integer (JSON boolean is not a generation)"
    return None




# ==========================================================================
# W4（三轮 P0-2）：--upgrade 三方升级 / --export-deviations 偏离导出
# 运行时无关：不经 wflib（与 repair/uninstall 同理——坏运行时也要能升级）。
# ==========================================================================

import difflib  # noqa: E402  （仅偏离导出用；标准库）


class PreviewToken:
    """预览确认（E1/E2：短指纹，不再打印随机长串）。

    指纹 = 本次预览摘要的前 8 位十六进制：同一份预览得同一个指纹，预览一变指纹就变。
    它只绑「本次预览摘要 + 本次过程」，重新预览即销毁；跨会话不恢复许可。
    真正的漂移防护仍在应用路径：确认后**在同一把锁内**重算预览并比对摘要
    （指纹只回答"确认的是哪一版预览"，不冒充防伪）。
    与 repair.py 的 PreviewToken 逐字一致；由 build-wf-release.py --verify-token-parity 比对。
    """

    def __init__(self):
        self._fingerprint = None
        self._digest = None

    def issue(self, preview, nonce=None):
        self._digest = _preview_digest(preview)
        derived = self._digest.split(":", 1)[-1][:8]
        self._fingerprint = str(nonce) if nonce else derived
        return self._fingerprint

    def confirm(self, supplied):
        if self._fingerprint is None or self._digest is None:
            return False
        import secrets
        return secrets.compare_digest(str(supplied).strip().lower(), self._fingerprint)

    def digest(self):
        return self._digest

    def invalidate(self):
        self._fingerprint = None
        self._digest = None

    def revalidate(self, supplied):
        return self.confirm(supplied)


PARITY_PREVIEW = {"operation": "token-parity-check", "target_root": "<parity>",
                  "selected_paths": ["a", "b"], "intended_after": "unchanged"}


def token_parity_check(nonce=None):
    token = PreviewToken()
    issued = token.issue(PARITY_PREVIEW, nonce=nonce)
    first = token.confirm(issued)
    token.invalidate()
    after = token.revalidate(issued)
    sys.stdout.write(f"fingerprint={issued}\n")
    sys.stdout.write(f"digest={_preview_digest(PARITY_PREVIEW)}\n")
    sys.stdout.write(f"first={'ok' if first else 'reject'}\n")
    sys.stdout.write(f"after={'expired' if not after else 'accepted'}\n")
    return 0


def _preview_digest(obj):
    text = json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


def _abs_base(target, root_ref):
    if root_ref == "project" or not root_ref:
        return os.path.abspath(target)
    return root_ref if os.path.isabs(root_ref) else os.path.join(os.path.abspath(target), root_ref)


def _asset_token(target, base, rel):
    """人面路径 token：**项目相对路径**（POSIX），W1（2026-11-23）。

    三方匹配的内部身份是 `(base, rel)`——`skill_root` 资产会在安装记录的每个根下各有一份
    同名副本，所以 `rel` 单独不能标识一份资产。所有给人看的/由人回填的路径（升级预览、
    `--keep/--restore`、导出清单、安装记录的处置留痕）统一用本函数产出的 token。

    `base` 落在目标项目之外（本框架不允许的新根）时退回绝对路径：它不可被 token 匹配，
    升级前置的 `registered_root_problems` 会整批拒绝这种记录。
    """
    base = os.path.abspath(base)
    target = os.path.abspath(target)
    if base == target:
        prefix = ""
    else:
        relative_base = os.path.relpath(base, target)
        if relative_base == os.pardir or relative_base.startswith(os.pardir + os.sep):
            return os.path.join(base, *rel.split("/")).replace(os.sep, "/")
        prefix = relative_base.replace(os.sep, "/") + "/"
    return prefix + rel


def _load_task_record_safe(path):
    try:
        with open(path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
        return data if isinstance(data, dict) else None, None
    except (OSError, ValueError) as exc:
        return None, str(exc)


def upgrade_prerequisites(target):
    """升级前置（W4-1）：机器判据写死——纯读取固定字段，不导入运行时、不解析任务正文。

    判据字段集（机制稿 §10.4 升级前置段）：
    - 活动任务 task.json {status, paused, suspended, handoff.wip}：
      非 archived 记录须 status==not_started 或 paused==true（suspended 只是附加标记，不把已暂停读成未暂停）；
      handoff.wip 存在且 resolved 为空 ⇒ 未处置 ⇒ 阻断（wip_paths 是唯一语义实现）；
      记录不可读 ⇒ 阻断（含路径与原因）。
    - 实例 workflow-runs {terminal, paused}：terminal==null 须 paused==true；不可读即阻断。
    - 写权：writer 记录可解释且 state==idle（_writer_problem 同一判据）。
    返回 (problems, wip_facts)；problems 非空即整批拒绝。
    """
    problems, wip_facts = [], []
    tasks_dir = os.path.join(target, ".wf", "tasks")
    if os.path.isdir(tasks_dir):
        for name in sorted(os.listdir(tasks_dir)):
            record_path = os.path.join(tasks_dir, name, "task.json")
            if not os.path.isfile(record_path):
                continue
            record, error = _load_task_record_safe(record_path)
            if record is None:
                problems.append({"reason": "unreadable-record", "path": os.path.relpath(record_path, target),
                                 "detail": error})
                continue
            if record.get("status") == "archived":
                continue
            paused = bool(record.get("paused"))
            suspended = bool(record.get("suspended"))
            if record.get("status") != "not_started" and not paused:
                problems.append({"reason": "active task not paused/not-started",
                                 "path": os.path.relpath(record_path, target),
                                 "status": record.get("status"),
                                 "paused": paused, "suspended": suspended,
                                 "exit": "先 task-pause；suspended 残留按任务入口清理后再重跑"})
            handoff = record.get("handoff") or {}
            wip = handoff.get("wip")
            if isinstance(wip, dict) and not wip.get("resolved"):
                paths = [item.get("path") if isinstance(item, dict) else str(item)
                         for item in (wip.get("paths") or wip.get("wip_paths") or [])]
                problems.append({"reason": "handoff wip unresolved",
                                 "path": os.path.relpath(record_path, target),
                                 "wip_paths": [p for p in paths if p],
                                 "exit": "先处置保留 WIP（提交/反向修正/承接）再重跑 upgrade 预览"})
                wip_facts.append({"task": record.get("id"), "paths": [p for p in paths if p]})
    runs_dir = os.path.join(target, ".wf", "workflow-runs")
    if os.path.isdir(runs_dir):
        for name in sorted(os.listdir(runs_dir)):
            if not name.endswith(".json"):
                continue
            record, error = _load_task_record_safe(os.path.join(runs_dir, name))
            if record is None:
                problems.append({"reason": "unreadable-record",
                                 "path": os.path.relpath(os.path.join(runs_dir, name), target),
                                 "detail": error})
                continue
            if record.get("terminal") is None and not bool(record.get("paused")):
                problems.append({"reason": "run not terminal and not paused",
                                 "path": os.path.relpath(os.path.join(runs_dir, name), target)})
    writer_path = os.path.join(target, ".wf", "writer.json")
    writer = None
    if not os.path.isfile(writer_path):
        # 升级必须取得具名维护写者；缺文件不是“空闲”，伪造 writer 会掩盖损坏。
        problems.append({"reason": "writer missing", "path": ".wf/writer.json",
                         "exit": "先按恢复说明运行 .wf/bin/repair.py 重建/核对写权，再重跑 upgrade"})
    else:
        writer, error = _load_task_record_safe(writer_path)
        if writer is None:
            problems.append({"reason": "writer unreadable", "detail": error})
        else:
            problem = _writer_problem(writer, allow_recovering=True)
            if problem:
                problems.append({"reason": "writer not idle", "detail": problem})
    return problems, wip_facts, writer


def three_way_plan(target, installation, manifest, source, keep=None, restore=None):
    """三方逐路径匹配（O=安装记录 / L=本地 / N=新发行），按机制稿 §10.4 顺序表。

    返回 (plan, unresolved)；plan.actions 为逐路径动作，unresolved 为需人裁决项
    （--keep/--restore 显式处置后重判）。上游删除只对 L=O 且无用户内容给可删候选。
    """
    actions, unresolved, deletes = [], [], []
    # O：安装记录 assets（含既有偏离登记 {local_fingerprint, upstream_fingerprint, decision}）
    installed = {}
    for entry in installation.get("assets") or []:
        if not isinstance(entry, dict):
            continue
        base = _abs_base(target, entry.get("root_ref"))
        rel = entry.get("target")
        if not rel:
            continue
        installed[(base, rel)] = dict(entry)
    # N：新发行清单（host_hook 全部纳入：安装面向全部平台，没有"未声明平台"）
    incoming = {}
    for asset in manifest.get("assets") or []:
        if not isinstance(asset, dict) or asset.get("target_class") == "release_only":
            continue
        rel = asset.get("target_relative")
        if not rel:
            continue
        if asset.get("target_class") == "skill_root":
            # 全部平台的根（含老装只装了子集时新增的根）：升级负责补齐，不沿用记录里的子集
            bases = list(resolve_skill_roots(target))
        else:
            bases = [os.path.abspath(target)]
        for base in bases:
            incoming[(base, rel)] = dict(asset)
    keep_tokens = set(keep or [])
    restore_tokens = set(restore or [])
    unmanaged = []
    # ① 上游删除
    for key, o_entry in sorted(installed.items()):
        if key in incoming:
            continue
        base, rel = key
        token = _asset_token(target, base, rel)
        local = file_digest(os.path.join(base, *rel.split("/")))
        if local is None:
            # 本地已无内容、上游也删除：没有可冲突的对象，直接退出托管记录。
            continue
        if local == o_entry.get("digest"):
            deletes.append({"base": base, "relative": rel, "path": token, "kind": "delete-candidate",
                           "local": local, "upstream": o_entry.get("digest")})
        elif token in keep_tokens:
            unmanaged.append({"base": base, "relative": rel, "path": token, "kind": "unmanaged-keep",
                              "asset": o_entry, "local": local, "upstream": o_entry.get("digest"),
                              "decision": "human (upgrade --keep)"})
        elif token in restore_tokens:
            deletes.append({"base": base, "relative": rel, "path": token, "kind": "delete-candidate",
                            "local": local, "upstream": o_entry.get("digest"),
                            "restore": True, "decision": "human (upgrade --restore)"})
        else:
            unresolved.append({"base": base, "relative": rel, "path": token,
                               "kind": "upstream-removed-local-changed",
                               "asset": o_entry, "local": local, "upstream": o_entry.get("digest"),
                               "exits": [f"保留本地并退出托管：重跑加 --keep {token}",
                                         f"删除本地以跟随上游删除：重跑加 --restore {token}",
                                         "或人工合并/重新立项后重跑"]})
    # ②③④⑤⑥⑦⑧：共同键与新增
    for key, n_asset in sorted(incoming.items()):
        base, rel = key
        token = _asset_token(target, base, rel)
        local = file_digest(os.path.join(base, *rel.split("/")))
        o_entry = installed.get(key)
        n_digest = n_asset.get("digest")
        if o_entry is None:
            if local is None:
                actions.append({"base": base, "relative": rel, "path": token, "kind": "add",
                               "asset": n_asset,
                               "local": None, "upstream": None, "new": n_digest})
            else:
                # 设计稿 §7.2：新版新增路径在本地已存在、未属旧托管清单时，即使
                # 内容等于 N 也须人确认，不自动认领用户文件。--restore 才是认领/
                # 恢复，--keep 是保留为我的文件（退出托管）。
                same = local == n_digest
                if token in keep_tokens:
                    unmanaged.append({"base": base, "relative": rel, "path": token,
                                      "kind": "unmanaged-keep",
                                      "asset": n_asset, "local": local, "new": n_digest,
                                      "decision": "human (upgrade --keep)"})
                elif token in restore_tokens:
                    actions.append({"base": base, "relative": rel, "path": token,
                                    "kind": "register" if same else "add",
                                    "asset": n_asset, "local": local, "upstream": None,
                                    "new": n_digest, "restore": True,
                                    "decision": "human (upgrade --restore)"})
                else:
                    unresolved.append({"base": base, "relative": rel, "path": token,
                                       "kind": "add-hits-user-file",
                                       "local": local, "new": n_digest,
                                       "same_content": same,
                                       "exits": [f"保留为我的文件（不纳入托管）：重跑加 --keep {token}",
                                                 (f"认领为框架资产（内容已相同）：重跑加 --restore {token}"
                                                  if same else
                                                  f"恢复发行内容：重跑加 --restore {token}"),
                                                 "或移走/改名该文件后重跑"]})
            continue
        if local is None:
            # 设计稿 §7.2 首行：本地缺失先核分支来源并确认删除；确认用户删除后尊重
            # 删除、不恢复，后续同态不重复。旧实现直接 reinstall 会把人有意的删除
            # 静默复活，且与"不恢复"的契约相反。
            branch_sources = branch_source_findings(target, [rel])
            kept = (token in keep_tokens
                    or o_entry.get("decision") in ("human (upgrade --keep)", "human (deleted)"))
            if token in restore_tokens:
                # 人显式 restore 优先于既有删除决定：否则“保留删除”会变成不可撤销。
                actions.append({"base": base, "relative": rel, "path": token, "kind": "reinstall",
                               "asset": n_asset, "local": None, "upstream": o_entry.get("digest"),
                               "new": n_digest, "decision": "human (upgrade --restore)",
                               "restore": True, "branch_sources": branch_sources})
            elif kept:
                actions.append({"base": base, "relative": rel, "path": token, "kind": "deleted-kept",
                               "asset": n_asset, "local": None, "upstream": o_entry.get("digest"),
                               "new": n_digest,
                               "decision": o_entry.get("decision") or "human (upgrade --keep)",
                               "branch_sources": branch_sources})
            else:
                unresolved.append({"base": base, "relative": rel, "path": token,
                                   "kind": "local-missing",
                                   "asset": n_asset, "local": None,
                                   "upstream": o_entry.get("digest"), "new": n_digest,
                                   "branch_sources": branch_sources,
                                   "exits": [f"确认是用户删除后尊重删除：重跑加 --keep {token}",
                                             f"恢复发行内容：重跑加 --restore {token}",
                                             "分支来源核对发现其他分支存在该路径时，先确认是不是切分支造成的缺失"]})
            continue
        if local == n_digest:
            actions.append({"base": base, "relative": rel, "path": token, "kind": "noop",
                           "asset": n_asset,
                           "local": local, "upstream": o_entry.get("digest"), "new": n_digest})
            continue
        # 同一已接受偏离（两边指纹均同）免重复询问——判在 L==O **之前**：
        # 偏离的本义就是 L≠O（人保留本地），埋在 L==O 分支内会让"已接受偏离"被重问。
        if (o_entry.get("upstream_fingerprint") == n_digest
                and o_entry.get("local_fingerprint") == local
                and o_entry.get("decision")):
            actions.append({"base": base, "relative": rel, "path": token, "kind": "deviation-kept",
                           "asset": n_asset,
                           "local": local, "upstream": o_entry.get("digest"), "new": n_digest,
                           "decision": o_entry.get("decision")})
            continue
        if local == o_entry.get("digest"):
            actions.append({"base": base, "relative": rel, "path": token, "kind": "update",
                           "asset": n_asset,
                           "local": local, "upstream": o_entry.get("digest"), "new": n_digest})
            continue
        # 其他冲突：人选保留/恢复；人合并后重跑按表重判
        decision = None
        if token in keep_tokens:
            decision = "human (upgrade --keep)"
        elif token in restore_tokens:
            decision = "human (upgrade --restore)"
        if decision:
            actions.append({"base": base, "relative": rel, "path": token, "kind": "deviation",
                           "asset": n_asset,
                           "local": local, "upstream": o_entry.get("digest"), "new": n_digest,
                           "decision": decision,
                           "restore": decision.endswith("--restore)")})
        else:
            unresolved.append({"base": base, "relative": rel, "path": token, "kind": "local-deviates",
                               "asset": n_asset, "local": local,
                               "upstream": o_entry.get("digest"), "new": n_digest,
                               "exits": [f"保留本地：重跑加 --keep {token}",
                                         f"恢复发行内容：重跑加 --restore {token}",
                                         "或人工合并后重跑（按表重判）"]})
    return {"actions": actions, "deletes": deletes, "unresolved": unresolved,
            "unmanaged": unmanaged}, unresolved


def _plan_fingerprint(plan):
    """三方匹配计划的可比较指纹：`(kind, path, local, upstream, new)` 逐项。

    只比路径集合会漏掉"同一路径内容变了"——那正是 `--restore` 覆盖新修改的入口。
    """
    items = []
    for item in (plan.get("actions") or []) + (plan.get("deletes") or []) \
            + (plan.get("unmanaged") or []):
        items.append((item.get("kind"), item.get("path"), item.get("local"),
                      item.get("upstream"), item.get("new")))
    return sorted(items, key=lambda entry: (str(entry[1]), str(entry[0])))


def export_deviations(args, installation, manifest, plan, source, commit):
    """W4-2：`--export-deviations --out <dir>` 只读导出（2026-11-23 语义收口）。

    范围：**所有本地偏离**，不只已登记 decision 的项。dogfood 的真实场景是业务任务
    内现场改了 `.wf/**` 后回源——那些改动从未走 `--keep` 登记，只导出"已接受偏离"
    会让通道对唯一要解决的场景不可用。未接受项在清单标 `status=pending`，不冒充
    已接受；已登记项标 `accepted`。

    补丁基线是**本次发行 N**（`--source` 的 tag 提交），不是安装记录里的旧版 O；
    O 只作原版指纹记录。这样补丁可直接在源仓库当前发行上应用。写面规则不变：
    --out 不存在则创建、已存在必须为空目录（非空拒）；逐文件原子写；符号链接拒；
    部分写入失败 ⇒ 停止、非零、如实报告已写清单（不自动删）。
    """
    out = args.out
    if not out:
        return blocked("WF_USAGE_INVALID", "--export-deviations 需要 --out <目录>", {}, args.json)
    out = os.path.abspath(out)
    try:
        project = _resolve_location(args.target)
    except ValueError:
        project = os.path.realpath(args.target)
    out_real = os.path.realpath(out)
    if out_real == project or out_real.startswith(project + os.sep):
        return blocked("WF_PATH_INVALID", "--out 必须在项目树外（导出物不进入项目交付/审查面）",
                       {"out": out, "target": project}, args.json)
    if os.path.islink(out) or (os.path.exists(out) and not os.path.isdir(out)):
        return blocked("WF_PATH_INVALID", "--out 目标含符号链接或不是目录", {"out": out}, args.json)
    if os.path.isdir(out) and os.listdir(out):
        return blocked("WF_ASSET_DECISION", "--out 目录已存在且非空：不覆盖、不并入用户文件",
                       {"out": out, "entries": sorted(os.listdir(out))[:20]}, args.json)
    candidates = []
    for item in plan["actions"]:
        if item.get("kind") in ("deviation", "deviation-kept") and not item.get("restore"):
            candidates.append((item, "accepted"))
    for item in plan.get("unresolved") or []:
        if item.get("kind") == "local-deviates":
            candidates.append((item, "pending"))
    not_exported = []
    for item in plan["actions"]:
        if item.get("kind") == "deleted-kept":
            not_exported.append({"target_path": item.get("path"), "kind": "deleted-kept",
                                 "reason": "人确认保留删除，无本地内容可导出"})
    for item in plan.get("unmanaged") or []:
        not_exported.append({"target_path": item.get("path"), "kind": "unmanaged-keep",
                             "reason": "已退出托管，不是框架偏离；无补丁基线"})
    for item in plan.get("unresolved") or []:
        if item.get("kind") == "local-deviates":
            continue
        reason = {
            "upstream-removed-local-changed": "上游已删除该路径，当前发行没有可对照字节；需在源仓库按旧版本人工合并",
            "add-hits-user-file": "本地文件不是已托管的框架资产（新增路径撞用户文件），不按偏离导出",
            "local-missing": "本地缺失，无本地内容可导出（先决定保留删除或恢复）",
        }.get(item.get("kind"), "该冲突项没有可导出的上游基线")
        not_exported.append({"target_path": item.get("path"), "kind": item.get("kind"),
                             "reason": reason})
    if not candidates:
        return ok("无本地偏离可导出", {
            "out": out, "deviations": 0, "not_exported": not_exported,
            "note": "本地与发行 N 一致，或只有缺失/用户文件冲突；未创建导出目录",
        }, args.json)
    os.makedirs(out, exist_ok=True)
    exported, failures = [], []
    dev_dir = os.path.join(out, "deviations")
    os.makedirs(dev_dir, exist_ok=True)
    for index, (item, status) in enumerate(sorted(candidates, key=lambda pair: pair[0]["path"]), start=1):
        base, rel = item["base"], item["relative"]
        local_path = os.path.join(base, *rel.split("/"))
        source_path = (item.get("asset") or {}).get("source_path") or rel
        base_bytes = _committed_bytes(source, commit, source_path)
        l_bytes = None
        try:
            with open(local_path, "rb") as handle:
                l_bytes = handle.read()
        except OSError as exc:
            failures.append({"target_path": item["path"], "reason": f"local unreadable: {exc}"})
            continue
        name = f"{index}-{os.path.basename(rel)}.patch"
        try:
            if base_bytes is None:
                text = (f"# 本次发行 N（提交 {commit}）的 {source_path} 不可取回："
                        f"无补丁可生成\n"
                        f"# local_fingerprint={item.get('local')}\n"
                        f"# original_fingerprint={item.get('upstream')}\n"
                        f"# decision={item.get('decision')}\n")
                data = text.encode("utf-8")
            else:
                diff = difflib.unified_diff(
                    base_bytes.decode("utf-8", "replace").splitlines(keepends=True),
                    (l_bytes or b"").decode("utf-8", "replace").splitlines(keepends=True),
                    fromfile=f"a/{source_path}", tofile=f"b/{source_path}")
                data = "".join(diff).encode("utf-8")
            tmp = os.path.join(dev_dir, name + ".tmp")
            with open(tmp, "wb") as handle:
                handle.write(data)
            os.replace(tmp, os.path.join(dev_dir, name))
            exported.append({"target_path": item["path"], "source_path": source_path,
                             "patch": f"deviations/{name}",
                             "status": status,
                             "target_version": installation.get("version"),
                             "release_version": manifest.get("version"),
                             "base_fingerprint": item.get("new") or item.get("upstream"),
                             "original_fingerprint": item.get("upstream"),
                             "local_fingerprint": item.get("local"),
                             "decision": item.get("decision")})
        except OSError as exc:
            failures.append({"target_path": item["path"], "reason": f"write failed: {exc}"})
            break                     # 停止：如实报告已写清单，不自动删已写内容
    if failures:
        return blocked("WF_PERSISTENCE_FAILED",
                       "偏离导出部分失败：停止写入，已写清单如下（不自动删除，人决定处置）",
                       {"exported": exported, "failures": failures}, args.json)
    try:
        _dump_json(os.path.join(out, "manifest.json"),
                   {"exported_at": now_str(), "source_commit": commit,
                    "release_version": manifest.get("version"),
                    "target_version": installation.get("version"),
                    "patch_base": "release",
                    "deviations": exported, "not_exported": not_exported})
    except OSError as exc:
        return blocked("WF_PERSISTENCE_FAILED", "偏离清单写入失败：补丁已写，清单未落盘",
                       {"out": out, "detail": str(exc), "exported": exported}, args.json)
    return ok("偏离导出完成", {"out": out, "deviations": len(exported),
                               "accepted": sum(1 for item in exported if item["status"] == "accepted"),
                               "pending": sum(1 for item in exported if item["status"] == "pending"),
                               "not_exported": not_exported}, args.json)


def upgrade_flag_problems(args):
    """升级模式参数组合校验（2026-11-23）。

    安装/升级是同一个 install.py：不带 --upgrade 时 --apply/--export-deviations/
    --out/--keep/--restore 原本会被静默忽略并走首次安装路径——这是"参数看似生效"的
    危险形态。这里把模式/组合错误一次列全，入口在任何路径检查之前拒绝。
    """
    problems = []
    if not args.upgrade:
        for flag, present in (("--apply", args.apply),
                              ("--export-deviations", args.export_deviations),
                              ("--out", args.out),
                              ("--keep", args.keep),
                              ("--restore", args.restore)):
            if present:
                problems.append({"flag": flag, "reason": "requires --upgrade"})
        return problems
    if args.confirm:
        problems.append({"flag": "--confirm", "reason": "upgrade uses --apply + preview token, not --confirm"})
    if args.export_deviations:
        if args.apply:
            problems.append({"flag": "--apply", "reason": "conflicts with --export-deviations（导出只读）"})
        if args.keep:
            problems.append({"flag": "--keep", "reason": "export exports every local deviation; no keep needed"})
        if args.restore:
            problems.append({"flag": "--restore", "reason": "export is read-only; restore is an upgrade decision"})
        if not args.out:
            problems.append({"flag": "--out", "reason": "required with --export-deviations"})
    elif args.out:
        problems.append({"flag": "--out", "reason": "only valid with --export-deviations"})
    both = sorted(set(args.keep or []) & set(args.restore or []))
    if both:
        problems.append({"flag": "--keep/--restore", "reason": "same path cannot be both kept and restored",
                         "paths": both})
    return problems


def run_upgrade(args, manifest, commit):
    """W4-1：`install.py --upgrade`（三方升级主入口）。"""
    target = os.path.abspath(args.target)
    source = os.path.abspath(args.source)
    installation_path = os.path.join(target, ".wf", "install", "installation.json")
    if not os.path.isfile(installation_path):
        return blocked("WF_RECORD_INVALID", "目标未安装 wf（缺安装记录）：先安装再升级",
                       {"installation": installation_path}, args.json)
    installation, _error = _load_task_record_safe(installation_path)
    if installation is None:
        return blocked("WF_RECORD_INVALID", "安装记录不可读", {"path": installation_path}, args.json)
    # 只读导出不受升级前置约束：它不取写权、不改安装记录、不应用版本。
    # 同版也允许导出——补丁基线是本次发行 N，与目标版本是否相等无关。
    if not args.export_deviations:
        if str(manifest.get("version")) == str(installation.get("version")):
            return blocked("WF_RELEASE_CONFLICT", "同版非升级：目标已是该版本",
                          {"installed": installation.get("version"),
                           "requested": manifest.get("version")}, args.json)
        problems, wip_facts, writer = upgrade_prerequisites(target)
        if problems:
            return blocked("WF_SEMANTIC_DECISION",
                           "升级前置不满足（机器判据，见机制稿 §10.4 升级前置段）",
                           {"problems": problems[:20],
                            "exit": "三步处置：task-pause → writer release → 重跑 upgrade 预览"
                                    "（writer release 自身在保留 WIP 未处置时被 WF_WORKSPACE_UNRESOLVED 拦——"
                                    "先处置 WIP：提交/反向修正/承接）"}, args.json)
    # 技能根以**安装记录**为准（老装可能是子集）：升级负责补齐到全部平台
    skill_roots = resolve_skill_roots(target)
    plan, unresolved = three_way_plan(target, installation, manifest, source,
                                      getattr(args, "keep", None),
                                      getattr(args, "restore", None))
    # 导出先返回；必需资产保留删除在下面写前拦截，其余缺失由自检/动作覆盖。
    if args.export_deviations:
        return export_deviations(args, installation, manifest, plan, source, commit)
    if unresolved:
        return blocked("WF_ASSET_DECISION",
                       "三方匹配存在需人裁决的路径（保留/恢复/合并后重跑按表重判）",
                       {"unresolved": unresolved[:20],
                        "upstream_removed": plan["deletes"]}, args.json)
    # keep/restore 都是人显式给出的处置；拼错/已不再是冲突的路径必须报出来，
    # 不能静默无匹配后仍按旧计划继续（否则人以为按自己的选择执行了）。
    keep_requested = set(getattr(args, "keep", None) or [])
    restore_requested = set(getattr(args, "restore", None) or [])
    keep_used = {item["path"] for item in plan["actions"]
                 if item["kind"] in ("deviation", "deviation-kept", "deleted-kept")}
    keep_used |= {item["path"] for item in plan.get("unmanaged") or []}
    restore_used = {item["path"] for item in plan["actions"]
                    if item["kind"] in ("reinstall", "deviation", "register", "add")
                    and item.get("restore")}
    restore_used |= {item["path"] for item in plan["deletes"] if item.get("restore")}
    unknown_keep = sorted(keep_requested - keep_used)
    unknown_restore = sorted(restore_requested - restore_used)
    if unknown_keep or unknown_restore:
        return blocked("WF_USAGE_INVALID", "keep/restore 指定的路径没有对应的待决冲突", {
            "unknown_keep": unknown_keep, "unknown_restore": unknown_restore,
            "known_tokens": sorted(set(keep_used) | set(restore_used)
                                   | {item["path"] for item in unresolved}),
            "exits": ["按 preview 的 unresolved[].path（项目相对路径）逐字重传",
                      "拼写/路径错误不按旧计划继续",
                      "已不再冲突的路径无需 keep/restore"],
        }, args.json)
    # 必需资产不能靠“保留删除”把运行集打残：这在写入前就能判定，必须交人改决定/清单。
    required_kept = [item["path"] for item in plan["actions"]
                     if item["kind"] == "deleted-kept"
                     and (item.get("asset") or {}).get("required")]
    required_kept += [item["path"] for item in plan.get("unmanaged") or []
                      if (item.get("asset") or {}).get("required")]
    if required_kept:
        return needs_decision(
            "WF_SEMANTIC_DECISION",
            "必需资产被选择保留删除/不纳入托管：升级不会把运行集改成不可用；请改决定或先调整清单",
            {"required_deleted": required_kept,
             "exits": ["对每条路径改传 --restore <路径> 恢复发行内容",
                       "或在源仓库把该资产改为可选/移出清单后再发版",
                       "保留删除只适用于可选资产"]}, args.json)
    # 落点边界：升级与首装同判据——root_ref 域外、路径符号链接越界都整批拒绝。
    root_problems = registered_root_problems(target, installation)
    boundary = []
    for item in plan["actions"] + plan["deletes"]:
        destination = os.path.join(item["base"], *item["relative"].split("/"))
        problem = boundary_problem(target, item["base"], destination)
        if problem:
            boundary.append(problem)
    if root_problems or boundary:
        return blocked("WF_PATH_INVALID", "升级写入/删除路径越界：整批拒绝", {
            "root_problems": root_problems[:20], "boundary": boundary[:20],
            "exits": ["修正安装记录中的 root_ref 或工作树符号链接", "不按越界路径继续升级"],
        }, args.json)
    # .gitignore 托管段冲突在应用前的锁内重核处拦截（预览不写、不要求清单段）。
    operation_id = f"upgrade-{uuid.uuid4().hex}"
    # W3：host_hook 的部署面包含宿主 hooks.json 条目——只换脚本字节会让"改落点/命令串"的
    # 发行在已升级项目留下失效条目（自检只核脚本 digest 仍绿）。写入前判定、写入后落地。
    hooks_plans, hooks_problems = plan_host_hooks(target, manifest, installation)
    if hooks_problems:
        return needs_decision(
            "WF_ASSET_DECISION",
            "hooks.json 条目需人裁决：升级不会覆盖用户改过的命令串，也不会重写不可解析文件",
            {"problems": hooks_problems,
             "exits": ["把 .codex/hooks.json 的该条目恢复成本框架条目（命令串为 problems 的 command）后重跑",
                       "或人工确认该条目归用户所有、由人移走后再重跑",
                       "不改写用户文件继续升级"]}, args.json)
    selected = sorted({item["path"] for item in plan["actions"]}
                       | {item["path"] for item in plan["deletes"]}
                       | {item["path"] for item in plan.get("unmanaged") or []})
    # 预览→确认之间可能有人改动工作区：**只有路径集合相等不算没变**。
    # 同一路径的本地摘要从 L1 变成 L2 时，`--restore` 会静默覆盖确认后新增的修改——
    # 违反 §4.4「预览后状态变更不得带旧许可径直写入」。这里固定逐路径动作+三端摘要。
    preview_fingerprint = _plan_fingerprint(plan)
    before_states = [{"path": item["path"], "kind": item["kind"],
                      "local": item.get("local"), "upstream": item.get("upstream"),
                      "new": item.get("new")}
                     for item in plan["actions"] + plan["deletes"] + (plan.get("unmanaged") or [])]
    preview = {
        "operation": f"upgrade:{manifest.get('version')}",
        "target_root": target,
        "release_identity": {"version": manifest.get("version"),
                             "release_ref": args.release_ref,
                             "source_commit": commit,
                             "rules_digest": (manifest.get("compatibility") or {}).get("rules_digest"),
                             "installed_version": installation.get("version")},
        "selected_paths": selected,
        "before_states": before_states,
        "intended_after": "按三方匹配结果写入/删除/保留；安装记录与偏离登记同批更新",
        "writer_observation": {"state": (writer or {}).get("state"),
                               "problem": _writer_problem(writer) if writer else "missing"},
        "wip_observation": {"unresolved_wip": wip_facts},
        "risks": [f"{item['kind']}: {item['path']}" for item in plan["deletes"]]
                + [f"deviation kept: {item['path']}" for item in plan["actions"]
                   if item["kind"] in ("deviation", "deviation-kept")]
                + [f"unmanaged keep: {item['path']}" for item in plan.get("unmanaged") or []],
        "hooks_json": hooks_plans,
        "backup_ref": installation.get("source_commit"),
    }
    token = PreviewToken()
    issued = token.issue(preview)
    if not getattr(args, "apply", False):
        lines = ["wf 升级预览（未写入任何文件）",
                 f"目标：{target}",
                 f"发行：{args.release_ref}（version={manifest.get('version')}，"
                 f"commit={commit}）",
                 f"已装版本：{installation.get('version')}",
                 f"选中路径：{len(selected)} 项",
                 f"动作：update/add/reinstall/register {len(plan['actions'])}，"
                 f"delete-candidate {len(plan['deletes'])}",
                 f"偏离保持：{sum(1 for a in plan['actions'] if a['kind'] in ('deviation', 'deviation-kept'))} 项",
                 ("宿主 hooks.json：" + "；".join(
                     f"{os.path.relpath(p['path'], target)} {p['action']}" for p in hooks_plans))
                 if hooks_plans else "宿主 hooks.json：无需维护（未声明 codex host_hook）",
                 f"预览摘要：{token.digest()}",
                 f"预览指纹：{issued}",
                 "确认后在同一个终端加 --apply 重跑并输入预览指纹。"]
        sys.stdout.write("\n".join(lines) + "\n")
        sys.stdout.flush()
        return ok("", {"preview": preview, "token_digest": token.digest()}, args.json)
    sys.stdout.write("请输入预览指纹确认：")
    sys.stdout.flush()
    if not sys.stdin or not sys.stdin.isatty():
        return blocked("WF_PREVIEW_STALE",
                       "非交互终端：预览→令牌→应用须在同一交互入口进程完成；"
                       "请在 TTY 重跑（重跑预览即销毁，进程退出不恢复）", {}, args.json)
    supplied = sys.stdin.readline().strip()
    if not token.confirm(supplied):
        return blocked("WF_PREVIEW_STALE", "预览指纹不匹配或预览已失效（同一进程重新预览）",
                       {}, args.json)
    lock_path = os.path.join(target, ".wf-lock")
    try:
        lock = Lock(lock_path, root=target)
    except LockRejected as exc:
        return blocked("WF_ASSET_DECISION", f"锁对象冲突：{exc}", {"path": lock_path}, args.json)
    except LockBusy as exc:
        return blocked("WF_WRITER_BUSY", f"锁被占用：{exc}", {"path": lock_path}, args.json)
    try:
        with lock:
            fresh_problems, _wip, fresh_writer = upgrade_prerequisites(target)
            if fresh_problems:
                return blocked("WF_SEMANTIC_DECISION", "锁内重核：升级前置已变化",
                               {"problems": fresh_problems[:20]}, args.json)
            fresh_plan, fresh_unresolved = three_way_plan(
                target, installation, manifest, os.path.abspath(args.source),
                getattr(args, "keep", None), getattr(args, "restore", None))
            fresh_fingerprint = _plan_fingerprint(fresh_plan)
            if fresh_fingerprint != preview_fingerprint:
                changed = sorted(
                    f"{item[1]}:{item[0]}" for item in fresh_fingerprint
                    if item not in preview_fingerprint)
                return blocked(
                    "WF_PREVIEW_STALE",
                    "预览已失效：锁内重核的三方匹配与预览不一致（逐路径动作或本地/上游/新版摘要变了）",
                    {"changed": changed[:20],
                     "explanations": ["确认期间工作区被改动（含 AI/人在另处编辑）",
                                      "安装记录/发行清单在等待期间变化"],
                     "exits": ["重新预览并复核后再确认", "不在旧预览上继续写入"]}, args.json)
            if fresh_unresolved:
                return blocked("WF_ASSET_DECISION", "锁内重核出现新的需人裁决路径",
                               {"unresolved": fresh_unresolved[:20]}, args.json)
            fresh_hooks, fresh_hook_problems = plan_host_hooks(target, manifest,
                                                               installation)
            if fresh_hook_problems:
                return needs_decision("WF_ASSET_DECISION", "锁内重核：hooks.json 需人裁决",
                                      {"problems": fresh_hook_problems}, args.json)
            if [(p["script_relative"], p["action"]) for p in fresh_hooks] != \
                    [(p["script_relative"], p["action"]) for p in hooks_plans]:
                return blocked("WF_PREVIEW_STALE",
                               "预览已失效：锁内重核的 hooks.json 动作与预览不一致（重新预览）",
                               {"preview": hooks_plans, "current": fresh_hooks}, args.json)
            lock_boundary = []
            for item in fresh_plan["actions"] + fresh_plan["deletes"]:
                destination = os.path.join(item["base"], *item["relative"].split("/"))
                problem = boundary_problem(target, item["base"], destination)
                if problem:
                    lock_boundary.append(problem)
            lock_root_problems = registered_root_problems(target, installation)
            if lock_boundary or lock_root_problems:
                return blocked("WF_PATH_INVALID", "锁内重核发现写入/删除路径越界：整批拒绝",
                               {"boundary": lock_boundary[:20],
                                "root_problems": lock_root_problems[:20]}, args.json)
            try:
                gitignore_state = ensure_gitignore(target, manifest)
            except ValueError as exc:
                return blocked("WF_ASSET_DECISION", "发行清单缺 gitignore_managed", {"detail": str(exc)}, args.json)
            if gitignore_state.get("action") == "conflict":
                return needs_decision("WF_ASSET_DECISION", ".gitignore 托管段与发行登记不符（按偏离处理）",
                               {"gitignore": gitignore_state,
                                "exits": ["人核对托管段后按 --keep/--restore 语义处置",
                                          "不覆盖用户段外内容"]}, args.json)
            # 维护写者
            writer = fresh_writer
            if not isinstance(writer, dict):
                return blocked("WF_RECORD_INVALID", "锁内重核缺写权记录：先 repair 再升级",
                               {"writer": ".wf/writer.json"}, args.json)
            held_generation = int(writer.get("generation") or 0) + 1
            writer.update({"state": "held", "generation": held_generation,
                           "updated_at": now_str(),
                           "holder": {"kind": "maintenance", "id": operation_id,
                                      "scope": {"operation": operation_id},
                                      "generation": held_generation},
                           "checkpoint": {"operation": operation_id, "phase": "upgrading"}})
            _dump_json(os.path.join(target, ".wf/writer.json"), writer)
            changes = []
            source = os.path.abspath(args.source)

            def _write_new(item):
                source_file = os.path.join(source, *item["asset"]["source_path"].split("/"))
                with open(source_file, "rb") as handle:
                    content = handle.read()
                destination = os.path.join(item["base"], *item["relative"].split("/"))
                os.makedirs(os.path.dirname(destination), exist_ok=True)
                # 升级的 update/reinstall 是**覆盖写**（目标已存在是常态）：
                # 原子替换（tmp+rename），不复用首装的只创建 write_bytes——
                # 那会把"更新已存在资产"变成 FileExistsError 崩溃（自举验证实测抓到）。
                tmp = destination + ".wf-upgrade-tmp"
                with open(tmp, "wb") as handle:
                    handle.write(content)
                os.replace(tmp, destination)
                if item["asset"].get("executable"):
                    os.chmod(destination, os.stat(source_file).st_mode | 0o755)
                changes.append({"path": os.path.relpath(destination, target).replace(os.sep, "/")
                                if destination.startswith(target) else destination,
                                "before": item.get("local"), "after": item.get("new")})

            for item in fresh_plan["actions"]:
                if item["kind"] in ("update", "add", "reinstall"):
                    _write_new(item)
                elif item["kind"] == "deviation" and item.get("restore"):
                    _write_new(item)
                # noop/register/deviation(-kept)：不写内容
            for item in fresh_plan["deletes"]:
                path = os.path.join(item["base"], *item["relative"].split("/"))
                before = file_digest(path)
                os.remove(path)
                changes.append({"path": os.path.relpath(path, target).replace(os.sep, "/")
                                if path.startswith(target) else path,
                                "before": before, "after": None})
            # W3：资产字节已就位 ⇒ 落地已判定（且锁内已重核）的 hooks.json 动作。
            # 它属维护变更：逐路径进 changes，人与后续写者据此审计（不是发行托管路径）。
            for hook_plan in fresh_hooks:
                before_digest = file_digest(hook_plan["path"])
                applied = apply_hooks_json(target, hook_plan)
                hook_plan["applied"] = applied
                if applied in ("created", "appended", "updated"):
                    changes.append({"path": os.path.relpath(hook_plan["path"], target).replace(os.sep, "/"),
                                    "before": before_digest,
                                    "after": file_digest(hook_plan["path"])})
            # 安装记录：身份 + assets（偏离登记按机制稿 §10.4 字段名）。
            # 先构造候选记录、跑自检，通过后才落盘——自检失败时安装版本不递增，
            # 重跑不会被“同版非升级”挡住（旧实现先写 version 再自检，失败即死路）。
            candidate = dict(installation)
            # 退出托管的本地内容不再出现在 assets；把人的 keep 决定记进 decisions，
            # 否则路径直接从记录里消失、只剩预览 risks，无法审计。
            for item in fresh_plan.get("unmanaged") or []:
                candidate.setdefault("decisions", []).append({
                    "kind": "unmanaged-keep", "path": item["path"],
                    "root_ref": "project" if item["base"] == target else item["base"],
                    "target": item["relative"],
                    "local_fingerprint": item.get("local"),
                    "decision": item.get("decision"), "at": now_str(),
                })
            candidate["version"] = manifest.get("version")
            candidate["release_ref"] = args.release_ref
            candidate["source_commit"] = commit
            candidate["rules_digest"] = (manifest.get("compatibility") or {}).get("rules_digest")
            staged_manifest, manifest_problem = stage_release_manifest(target, source)
            if manifest_problem:
                return blocked("WF_PERSISTENCE_FAILED",
                               "发行清单复制/摘要核对失败：停止应用（不写入安装记录）",
                               manifest_problem, args.json)
            candidate["manifest_digest"] = staged_manifest["digest"]
            _assets = []
            for item in fresh_plan["actions"]:
                entry = {"target": item["relative"],
                         "root_ref": "project" if item["base"] == target else item["base"],
                         "digest": item.get("new"),
                         "source_path": (item.get("asset") or {}).get("source_path"),
                         "upstream_version": manifest.get("version"),
                         "upstream_fingerprint": item.get("new")}
                if item["kind"] in ("deviation", "deviation-kept"):
                    if item.get("restore"):
                        # restore 写的是 N：升级后就是正常发行字节，不能把被丢弃的
                        # 本地指纹记成当前 digest（否则下一版会被误判为 local-deviates）。
                        entry["digest"] = item.get("new")
                    else:
                        # 偏离登记（机制稿 §10.4 字段名）：digest 保持**旧模板 O**语义
                        # （=本版发行字节 N），local_fingerprint 才是目标实际字节。
                        # 旧实现把 digest 记成 L，下一版会被误判为 L=O 的安全 update
                        # 而静默覆盖人保留的本地内容。
                        entry["local_fingerprint"] = item.get("local")
                        entry["upstream_fingerprint"] = item.get("new")
                        entry["decision"] = item.get("decision")
                        entry["digest"] = item.get("new")
                elif item["kind"] == "deleted-kept":
                    # 人确认保留删除（仅可选资产；required 已在写前拦截）：
                    # 登记 digest=None，后续同态不再询问。
                    entry["digest"] = None
                    entry["local_fingerprint"] = None
                    entry["upstream_fingerprint"] = item.get("new")
                    entry["decision"] = item.get("decision")
                _assets.append(entry)
            candidate["assets"] = _assets
            record_host_hooks(candidate, manifest, fresh_hooks, target)
            candidate["upgraded_at"] = now_str()
            kept_deleted = [os.path.join(item["base"], *item["relative"].split("/"))
                            for item in fresh_plan["actions"] if item["kind"] == "deleted-kept"]
            unmanaged_paths = [os.path.join(item["base"], *item["relative"].split("/"))
                               for item in fresh_plan.get("unmanaged") or []]
            all_roots = resolve_skill_roots(target)
            candidate["roots"] = [os.path.relpath(root, target).replace(os.sep, "/")
                                  for root in all_roots]
            candidate["platforms"] = all_platforms()
            skill_roots = all_roots
            problems = self_check(target, manifest, skill_roots,
                                  installation=candidate,
                                  intentional_missing=kept_deleted + unmanaged_paths)
            if problems:
                try:
                    if os.path.exists(staged_manifest["tmp"]):
                        os.remove(staged_manifest["tmp"])
                except OSError:
                    pass
                released_generation = held_generation + 1
                writer.update({"state": "recovering", "holder": None,
                               "generation": released_generation,
                               "updated_at": now_str(),
                               "checkpoint": {"operation": operation_id,
                                              "phase": "self-check-failed",
                                              "problems": problems[:20]}})
                writer["revision"] = int(writer.get("revision") or 0) + 1
                _dump_json(os.path.join(target, ".wf/writer.json"), writer)
                return blocked("WF_PERSISTENCE_FAILED",
                               "升级已写入资产但安装自检失败：安装版本未递增（可修复后重跑），"
                               "现场保留按 §5.4 处置",
                               {"problems": problems[:20],
                                "exits": ["按 problems 修复后重跑 upgrade（同版重跑仍可用）",
                                          "或运行 .wf/bin/repair.py 核对恢复后再重跑"]}, args.json)
            os.replace(staged_manifest["tmp"], staged_manifest["path"])
            installation = candidate
            _dump_json(installation_path, installation)
            with open(os.path.join(target, ".wf/install/recovery.md"), "w",
                      encoding="utf-8", newline="\n") as handle:
                handle.write(recovery_text(target, installation))
            released_generation = held_generation + 1
            writer.update({"state": "idle", "holder": None, "generation": released_generation,
                           "revision": int(writer.get("revision") or 0) + 1,
                           "checkpoint": {"operation": operation_id, "phase": "upgrade-applied"},
                           "updated_at": now_str()})
            receipt = {
                "operation": operation_id,
                "preview_digest": token.digest(),
                "head_before": None,
                "changes": changes,
                "receipt_git_state": {"head": None, "tracked_paths": len(changes)},
                "result": "applied_pending_commit",
                "disposition": None,
            }
            writer["maintenance_results"] = list(writer.get("maintenance_results") or []) + [receipt]
            _dump_json(os.path.join(target, ".wf/writer.json"), writer)
            append_maintenance_journal(target, receipt)
            return ok("\n".join([
                "OK  WF_OK",
                f"目标：{target}",
                f"已升级：{installation.get('version')} ← {args.release_ref}",
                f"变更路径：{len(changes)} 项（applied_pending_commit：持久化提交由人另行授权）",
                f"偏离保持：{sum(1 for a in fresh_plan['actions'] if a['kind'] in ('deviation', 'deviation-kept'))} 项",
            ]), {"version": installation.get("version"), "changes": len(changes),
                 "result": "applied_pending_commit"}, args.json)
    except RuntimeError as exc:
        return blocked("WF_WRITER_BUSY", f"锁被占用：{exc}", {"path": lock_path}, args.json)
    except ValueError as exc:
        return blocked("WF_CAPABILITY_UNAVAILABLE", f"锁对象异常：{exc}", {"path": lock_path}, args.json)
    except OSError as exc:
        return blocked("WF_PERSISTENCE_FAILED", "升级写入失败：现场保留，按恢复说明核对写权与安装记录",
                       {"detail": str(exc), "exits": ["运行 .wf/bin/repair.py 核对写权/安装记录",
                                                      "确认现场后重跑同一 upgrade（同版重跑仍可用）"]}, args.json)

class _InstalledMeanwhile(Exception):
    """锁内发现目标已安装：释放锁后改走 `verify_installed`（只读核对，不取写权）。"""


def main(argv=None):
    if argv is None:
        argv = sys.argv[1:]
    # W4-1：parity 自检必须在 argparse 三必填之前（parity 调用不带 --target/--release-ref/--source，
    # 先过 required 校验会被拒掉）——与 repair/uninstall 的前置分支同型。
    if "--token-parity-check" in argv:
        # parity 调用可带 --nonce <value>（与 repair/uninstall 的比对输入一致）
        nonce = None
        if "--nonce" in argv:
            index = argv.index("--nonce")
            if index + 1 < len(argv):
                nonce = argv[index + 1]
        return token_parity_check(nonce=nonce)
    parser = argparse.ArgumentParser(description="wf 发行根安装入口")
    parser.add_argument("--target", required=True)
    parser.add_argument("--release-ref", required=True)
    parser.add_argument("--source", required=True,
                        help="发行检出根（其下直接有 install.py、wf-release.json 与 wf-release/ 子树）")

    parser.add_argument("--confirm", action="store_true")
    parser.add_argument("--python", default=None,
                        help="安装时确定用于运行 wf 的 Python 解释器（绝对路径，>=3.11）；"
                             "缺省用系统 python3，系统没有则拒绝安装。安装成功后由同一条命令"
                             "在终端完成解释器确认（人输入 yes），不再单独跑 confirm-executor")
    parser.add_argument("--strict-source", dest="strict_source", action="store_true",
                        help="发行子树必须与提交一致（脏检出即拒绝）；发行作者仓库通常不带此参数")
    parser.add_argument("--upgrade", action="store_true",
                        help="三方升级模式（W4-1）：O=安装记录/L=本地/N=新发行 逐路径匹配")
    parser.add_argument("--apply", action="store_true",
                        help="升级：应用预览（交互 TTY 输入预览指纹；同一进程完成，重跑预览即销毁）")
    parser.add_argument("--export-deviations", dest="export_deviations", action="store_true",
                        help="升级：只读导出本地偏离的补丁与清单（不取写权、不暂停任务、不应用升级）")
    parser.add_argument("--out", default=None, help="偏离导出目录（不存在则创建；已存在必须为空）")
    parser.add_argument("--keep", action="append", default=[],
                        help="人选择保留本地的冲突路径（**项目相对路径**，与预览 "
                             "unresolved[].path 逐字一致；记录偏离登记）")
    parser.add_argument("--restore", action="append", default=[],
                        help="人选择恢复发行内容的冲突路径（**项目相对路径**，同上）")
    parser.add_argument("--json", action="store_true")
    args, unknown = parser.parse_known_args(argv)
    if unknown:
        return blocked("WF_USAGE_INVALID", "未知参数", {
            "unknown": unknown,
            "known": ["--target", "--release-ref", "--source", "--confirm",
                      "--strict-source", "--upgrade", "--apply", "--export-deviations",
                      "--out", "--keep", "--restore", "--python", "--json"],
            "exits": ["按 wf help upgrade / install.py --help 修正参数后重试",
                      "未知参数不继续投放或升级"],
        }, args.json)

    if args.python and args.upgrade:
        return blocked("WF_USAGE_INVALID", "--python 只用于首装", {
            "exits": ["升级沿用已确认的执行器；要换解释器先改配置并用 confirm-executor 重新确认",
                      "去掉 --python 后重试"],
            "known": ["--python"], }, args.json)
    python_candidate = None
    if not args.upgrade:
        python_candidate = os.path.abspath(args.python) if args.python else shutil.which("python3")
        if not python_candidate:
            return blocked("WF_EXECUTOR_UNCONFIRMED", "系统没有 python3，且未指定 --python", {
                "exits": ["用 --python <绝对路径> 指定一个已核实可用的 Python 3.11+ 解释器",
                          "或先在本机安装/暴露系统 python3 后重试"], }, args.json)
        problem = python_candidate_problems(python_candidate)
        if problem:
            return blocked("WF_EXECUTOR_UNCONFIRMED", f"解释器候选不可用：{problem}", {
                "candidate": python_candidate,
                "exits": ["换成已核实可用的 Python 3.11+ 解释器后重试"], }, args.json)

    problems = upgrade_flag_problems(args)
    if problems:
        return blocked("WF_USAGE_INVALID", "升级参数组合非法", {
            "problems": problems,
            "known": ["--upgrade", "--apply", "--export-deviations", "--out", "--keep", "--restore"],
            "exits": ["按 wf help upgrade 修正参数后再运行",
                      "--export-deviations 与 --apply 互斥；导出不写安装记录",
                      "不使用 --upgrade 时不要传升级专用参数"],
        }, args.json)

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
    managed = manifest.get("gitignore_managed") or {}
    if not managed.get("lines") or not managed.get("begin_marker") or not managed.get("end_marker"):
        # 托管段是发行规则的一部分（计入 rules_digest）：缺登记就拒绝，不猜忽略行
        return blocked("WF_ASSET_DECISION", "发行清单缺 gitignore_managed（托管段唯一来源）",
                       {"manifest": manifest_path}, args.json)
    if getattr(args, "upgrade", False):
        # W4-1：升级模式（含 --export-deviations 只读导出）。--source 必须是发行检出根
        # （load_manifest 要求 wf-release.json 直在 source 下，写成 <检出>/wf-release 即 WF_PATH_INVALID）。
        return run_upgrade(args, manifest, commit)

    # 安装面向**全部支持平台**（`PLATFORMS` 是唯一来源；新增平台重跑即补齐）。
    skill_roots = resolve_skill_roots(args.target)
    install_platforms = all_platforms()
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

    # 宿主 hook 配置是**用户共享文件**上的变更（`.codex/hooks.json`），必须在人确认前可见；
    # 冲突也要在确认前给出，而不是等人 --confirm 之后才被拒（五轮复审 a-P2）。
    previous_record = None
    if os.path.isfile(os.path.join(args.target, ".wf/install/installation.json")):
        previous_record, _problem = _load_task_record_safe(
            os.path.join(args.target, ".wf/install/installation.json"))
    hook_preview, hook_preview_problems = plan_host_hooks(
        args.target, manifest, previous_record)
    gitignore_preview = plan_gitignore(args.target, manifest)
    if gitignore_preview["action"] == "conflict":
        return needs_decision(
            "WF_ASSET_DECISION",
            ".gitignore 托管段与发行登记不符：不覆盖用户段外内容（未确认、未写入任何文件）",
            {"gitignore": gitignore_preview,
             "exits": ["人核对托管段后手工修正为本次发行内容，或移走该文件后重跑",
                       "不覆盖用户段外内容"]}, args.json)
    if hook_preview_problems:
        return needs_decision(
            "WF_ASSET_DECISION",
            "hooks.json 条目需人裁决：不覆盖用户改过的命令串（未确认、未写入任何文件）",
            {"problems": hook_preview_problems,
             "exits": ["把 .codex/hooks.json 的该条目恢复成本框架条目后重跑",
                       "或人工确认该条目归用户所有、由人移走后再重跑"]}, args.json)

    clues = trellis_clues(args.target)
    if not args.confirm:
        lines = [
            "wf 安装预览（未写入任何文件）",
            f"目标：{args.target}",
            f"发行引用：{args.release_ref} → {commit}",
            f"版本：{manifest.get('version')}",
            f"规则摘要：{(manifest.get('compatibility') or {}).get('rules_digest')}",
            f"解释器：{python_candidate}（确认后写入本机记录）",
            "投放文件：",
        ]
        for base, asset, relative in writes:
            lines.append(f"  - {os.path.join(base, *relative.split('/'))}")
        lines += ["另将创建：.wf-lock、.wf/、.wf/writer.json（初始维护持有）、.wf/install/*",
                  "宿主 hook 配置（用户共享文件 .codex/hooks.json）："]
        if hook_preview:
            lines += [f"  - {os.path.relpath(item['path'], args.target)} {item['action']}"
                      for item in hook_preview]
        else:
            lines.append("  无需修改（本发行没有声明了宿主 hook 的资产）")
        lines += [f"托管段（.gitignore）：{gitignore_preview['action']}",
                  "  " + managed_segment(manifest).replace("\n", "\n  "),
                  f"平台：{json.dumps(install_platforms, ensure_ascii=False)}（全部支持平台，一次装齐）",
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
                  {"preview": True, "clues": clues, "platforms": install_platforms}, args.json)


    installation_path = os.path.join(args.target, ".wf/install/installation.json")
    if os.path.exists(installation_path):
        # 已安装：重跑只做补齐/核对（内容差异或版本不同转升级），不按新装覆盖
        return verify_installed(args, manifest, skill_roots, branch_findings)
    # 没有安装记录但 `.wf/` 里已有 writer.json ⇒ 上一次首装中断（写权 recovering/held、
    # 资产可能已部分落盘）。按**首装重入**处理：写权被上次持有不是"已安装"的证据。
    # 重入的写入本身是安全的（`write_bytes` 只创建、内容不同即 FileExistsError 中止），
    # 但必须沿用既有 writer 记录（保住代次与维护回执），不能当成全新首装覆盖它。
    lock_path = os.path.join(args.target, ".wf-lock")
    try:
        lock = Lock(lock_path, root=args.target)
    except LockRejected as exc:
        return blocked("WF_ASSET_DECISION", f"锁对象冲突：{exc}", {"path": lock_path}, args.json)
    except LockBusy as exc:
        return blocked("WF_WRITER_BUSY", f"锁被占用：{exc}", {"path": lock_path}, args.json)

    try:
        with lock:
            # 锁内重判"是否已安装"（2026-11-23 七轮复审 a-2）：锁外判断可能已过期——
            # 两个进程都看到"未安装"时，后拿到锁的那个会把前者刚写完的安装记录当首装重试，
            # 重新生成安装身份并用自己的平台/技能根覆盖原记录（已有副本随即脱离升级/卸载管理）。
            # 这里**在锁内**再判一次；已装则先释放锁、改走 `verify_installed` 只读核对。
            if os.path.isfile(os.path.join(args.target, ".wf/install/installation.json")):
                raise _InstalledMeanwhile()
            # 锁内全批复核（首装）：路径/落点/类别必须在 mkdir .wf 与任何写入之前重新成立。
            writes, plan_problems = plan_writes(args.target, skill_roots, manifest)
            if plan_problems:
                return blocked("WF_ASSET_DECISION",
                               "锁内复核发现资产越界：整批拒绝，不写任何文件",
                               {"problems": plan_problems[:20]}, args.json)
            # W3 复核（2026-11-23 五轮复审 P1）：hooks.json 判定必须先于任何写入。
            # 旧顺序在写完全部资产之后才判——冲突时直接 return 会留下
            # 「.wf/ 已创建 + 资产已投放 + 无安装记录 + 写权 held」的半安装态。
            hook_plans, hook_problems = plan_host_hooks(args.target, manifest, None)
            if hook_problems:
                return needs_decision(
                    "WF_ASSET_DECISION",
                    "hooks.json 条目需人裁决：不覆盖用户改过的命令串（本次未写入任何文件）",
                    {"problems": hook_problems,
                     "exits": ["把 .codex/hooks.json 的该条目恢复成本框架条目后重跑安装",
                               "或人工确认该条目归用户所有、由人移走后再重跑"]}, args.json)

            fresh_gitignore = plan_gitignore(args.target, manifest)
            if fresh_gitignore["action"] == "conflict":
                return needs_decision(
                    "WF_ASSET_DECISION",
                    "锁内重核：.gitignore 托管段与发行登记不符（尚未写入任何文件）",
                    {"gitignore": fresh_gitignore}, args.json)

            operation_id = f"install-{uuid.uuid4().hex}"
            os.makedirs(os.path.join(args.target, ".wf"), exist_ok=True)
            writer_path = os.path.join(args.target, ".wf/writer.json")
            existing_writer = None
            if os.path.isfile(writer_path):
                try:
                    with open(writer_path, "r", encoding="utf-8") as handle:
                        existing_writer = json.load(handle)
                except (OSError, ValueError):
                    existing_writer = None
                if not isinstance(existing_writer, dict):
                    return blocked("WF_RECORD_INVALID",
                                   "首装重入：既有 .wf/writer.json 不可解析，先 repair 核对",
                                   {"writer": writer_path,
                                    "exits": ["运行 .wf/bin/repair.py 核对恢复后重跑安装"]}, args.json)
                takeover = _first_install_takeover(existing_writer)
                if takeover is not None:
                    # "没有安装记录"不等于"没人持有"：写权被会话持有时接管，等于绕过 §4.4 的
                    # 持有边界（六轮复审 a-1 的纯内存复现已证）。只有**无持有者**或**本框架安装
                    # 维护**留下的检查点才可按首装重试。
                    return blocked(
                        "WF_WRITER_BUSY",
                        "首装重入被拒：既有写权记录看起来不是未完成的首装",
                        {"writer": writer_path, "state": existing_writer.get("state"),
                         "holder": existing_writer.get("holder"),
                         "checkpoint": existing_writer.get("checkpoint"),
                         "problem": takeover,
                         "exits": ["让该持有者按 §4.4 正常释放或交接后重跑安装",
                                   "或运行 .wf/bin/repair.py 核对写权记录与现场后再重跑"]}, args.json)
            retry_generation = int((existing_writer or {}).get("generation") or 0) + 1
            writer = dict(existing_writer or {}) if existing_writer else {
                "schema_version": 1, "id": "writer", "revision": 0, "created_at": now_str(),
                "write_mark": None, "action": None, "handover": None,
                "maintenance_results": [],
            }
            writer.update({
                "updated_at": now_str(), "state": "held",
                "generation": retry_generation,
                "holder": {"kind": "maintenance", "id": operation_id,
                           "scope": {"operation": operation_id}, "generation": retry_generation},
                "checkpoint": {"operation": operation_id,
                               "phase": "installing-retry" if existing_writer else "installing"},
            })
            writer.setdefault("maintenance_results", [])
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
                    return maintenance_abort(
                        os.path.join(args.target, ".wf/writer.json"), writer, operation_id,
                        "deploy-assets", "WF_ASSET_DECISION",
                        "目标路径已存在且内容不同：未覆盖，维护写者转入待恢复",
                        {"path": destination,
                         "problems": [{"path": destination,
                                       "reason": "target exists with different content"}]},
                        args.json)
                if asset.get("executable"):
                    os.chmod(destination, os.stat(source_file).st_mode | 0o755)  # 清单声明 executable:true，须与事实一致
                deployed.append({"target": destination, "created": created})
            # W3-2：资产已落盘 ⇒ 落地前面已判定（且冲突已在写入前拦住）的 hooks.json 动作；
            # 动作与"上一版命令串"同批登记进安装记录（升级判定靠它区分"我们的旧串"与"用户改过的串"）。
            for plan in hook_plans:
                try:
                    plan["applied"] = apply_hooks_json(args.target, plan)
                except (ValueError, OSError) as exc:
                    return maintenance_abort(
                        os.path.join(args.target, ".wf/writer.json"), writer, operation_id,
                        "hooks-json-apply", "WF_ASSET_DECISION",
                        f"hooks.json 落地失败：{exc}",
                        {"hooks_json": hooks_json_path(args.target),
                         "problems": [{"path": hooks_json_path(args.target), "reason": str(exc)}]},
                        args.json)

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
                # 内容级来源身份：同 commit 重建发行会让摘要变化（F8-4）
                "rules_digest": (manifest.get("compatibility") or {}).get("rules_digest"),
                "manifest_digest": manifest_digest,
                # 记录为**事实**：本次装齐的全部支持平台（不再是人选的子集）
                "platforms": install_platforms,
                "roots": [os.path.relpath(root, args.target).replace(os.sep, "/") for root in skill_roots],
                # W4-1 写入侧：O 哈希=digest + 可重取来源引用（upstream_version/指纹）——
                # 升级的"偏离保持/同一已接受偏离"行依赖这些字段，此前从未落盘
                "assets": [{"target": relative, "root_ref": "project" if base == args.target else base,
                            "digest": asset.get("digest"), "source_path": asset.get("source_path"),
                            "upstream_version": manifest.get("version"),
                            "upstream_fingerprint": asset.get("digest")}
                           for base, asset, relative in writes],
                "decisions": ([{"kind": "branch-source", "findings": branch_findings,
                                "decision": "human (--confirm)", "at": now_str(),
                                "note": "人确认在本分支按新安装继续（设计稿 §7.1）"}]
                              if branch_findings else []),
                "host_hook_entries": [],
                "installed_at": now_str(),
                "tool": "install.py",
            }
            record_host_hooks(installation, manifest, hook_plans, args.target)
            with open(os.path.join(install_dir, "installation.json"), "w", encoding="utf-8", newline="\n") as handle:
                handle.write(json.dumps(installation, indent=2, sort_keys=True, ensure_ascii=False) + "\n")
            with open(os.path.join(install_dir, "recovery.md"), "w", encoding="utf-8", newline="\n") as handle:
                handle.write(recovery_text(args.target, installation))
            gitignore = apply_gitignore(args.target, manifest, fresh_gitignore)
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
            # 本次操作改到的**用户共享文件**也必须进回执（设计稿 §4.4 维护变更持久化：
            # 逐路径记前后状态），否则人无从核对"安装到底动了哪些不属于 .wf 的文件"。
            for plan in hook_plans:
                if plan.get("applied") in ("created", "appended", "updated"):
                    changes.append({
                        "path": os.path.relpath(plan["path"], args.target).replace(os.sep, "/"),
                        "before": plan.get("before_digest"),
                        "after": file_digest(plan["path"])})
            if gitignore.get("action") == "appended":
                changes.append({"path": ".gitignore",
                                "before": gitignore.get("before_digest"),
                                "after": gitignore.get("after_digest")})
            writer["maintenance_results"] = list(writer.get("maintenance_results") or []) + [{
                "operation": operation_id,
                "preview_digest": plain_digest(installation),
                "head_before": head_before,
                "changes": changes,
                "receipt_git_state": {"head": head_before, "tracked_paths": len(changes)},
                "result": "applied_pending_commit",
                "disposition": None,
            }]
            # 代次与修订号按既有记录递增：首装重入不能把上一次中断的代次"归零"，
            # 否则旧代次持有者会与新代次同时有效（§4.4 的旧代次失效语义被绕过）。
            writer["state"] = "idle"
            writer["holder"] = None
            writer["generation"] = int(writer.get("generation") or 0) + 1
            writer["checkpoint"] = {"operation": operation_id, "phase": "installed"}
            writer["revision"] = int(writer.get("revision") or 0) + 1
            with open(os.path.join(args.target, ".wf/writer.json"), "w", encoding="utf-8", newline="\n") as handle:
                handle.write(json.dumps(writer, indent=2, sort_keys=True, ensure_ascii=False) + "\n")
            append_maintenance_journal(args.target, writer["maintenance_results"][-1])

    except LockRejected as exc:
        return blocked("WF_ASSET_DECISION", f"锁对象冲突：{exc}", {"path": lock_path}, args.json)
    except LockBusy as exc:
        return blocked("WF_WRITER_BUSY", f"锁被占用：{exc}", {"path": lock_path}, args.json)
    except _InstalledMeanwhile:
        # 锁内已确认存在安装记录（并发安装刚完成）：交回补齐/核对分支，
        # 不改既有安装身份、不覆盖记录（2026-11-23 七轮复审 a-2）。
        return verify_installed(args, manifest, skill_roots, branch_findings)
    # 解释器确认由这条安装命令一并完成：--python 提供时写本机用户级配置并按 global 确认，
    # 缺省按 system 确认系统 python3。提示与写入仍只在 bootstrap 的 confirm-executor 一处。
    scope = "global" if args.python else "system"
    if args.python:
        problem = write_global_executor(python_candidate)
        if problem:
            return blocked("WF_EXECUTOR_UNCONFIRMED", "全局配置无法写入人选解释器", {
                "candidate": python_candidate, "reason": problem,
                "installed": True,
                "exits": ["修正 ~/.wf/config.json 后重跑 confirm-executor --scope global"], }, args.json)
    confirm_rc, confirm_facts = confirm_executor(args.target, python_candidate, scope)
    if confirm_rc != 0:
        return blocked("WF_EXECUTOR_UNCONFIRMED",
                       "文件已投放，但解释器确认未完成（确认须人在终端输入 yes）", {
                           "confirmation": confirm_facts, "installed": True,
                           "exits": [f"在终端运行：{python_candidate} .wf/bin/wf.py confirm-executor --scope {scope}",
                                     "确认后重跑原安装命令（幂等补齐）或直接 /wf-start"], }, args.json)
    message = "\n".join([
        "OK  WF_OK",
        f"目标：{args.target}",
        f"发行引用：{args.release_ref} → {commit}",
        f"投放：{len([item for item in deployed if item['created']])} 个新文件",
        f"清单摘要：{manifest_digest}",
        f"规则摘要：{(manifest.get('compatibility') or {}).get('rules_digest')}",
        f"托管段：{gitignore.get('action')}",
        f"解释器：{python_candidate}（scope={scope}，已写入本机确认记录）",
        "下一步：/wf-start",
    ])
    return ok(message, {"installation": installation, "gitignore": gitignore}, args.json)



ASSET_CLASSES = ("project_wf", "skill_root", "host_hook")
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


def _resolve_location(path):
    """规范落点：解析现有祖先符号链接与 `..`，尚不存在的末段按组件拼接。

    不以“目标是否已存在”决定是否解析——否则先建好 symlink 再重跑就能绕过边界。
    """
    raw = os.path.abspath(str(path))
    current = os.sep
    for part in [item for item in raw.split(os.sep) if item]:
        if part == ".":
            continue
        if part == "..":
            current = os.path.dirname(current)
            continue
        nxt = os.path.join(current, part)
        if os.path.islink(nxt):
            if not os.path.exists(nxt):
                raise ValueError(f"path component is a broken symlink: {nxt}")
            current = os.path.realpath(nxt)
        else:
            current = nxt
    return os.path.normpath(current)


def _contains(base, path):
    return path == base or path.startswith(base + os.sep)


def boundary_problem(project_root, base, destination):
    """两层包含关系：项目→基址、基址/项目→资产实际落点（任一失败即整批拒绝）。"""
    try:
        project = _resolve_location(project_root)
        base_real = _resolve_location(base)
        dest_real = _resolve_location(destination)
    except ValueError as exc:
        return {"reason": "path contains a broken symlink", "detail": str(exc),
                "base": str(base), "path": str(destination)}
    if not _contains(project, base_real):
        return {"reason": "asset base resolves outside the project root",
                "base": str(base), "resolved": base_real, "project": project}
    if not _contains(base_real, dest_real):
        return {"reason": "target resolves outside its base", "base": str(base),
                "path": str(destination), "resolved": dest_real}
    if not _contains(project, dest_real):
        return {"reason": "target resolves outside the project root", "path": str(destination),
                "resolved": dest_real, "project": project}
    return None


def inside(base, path):
    """兼容旧调用：真实落点必须仍在基址内（防符号链接逃逸）。"""
    base_real = os.path.realpath(str(base))
    path_real = os.path.realpath(str(path))
    return path_real == base_real or path_real.startswith(base_real + os.sep)


def registered_root_problems(target, installation):
    """历史 root_ref：项目内相对/绝对根可用；域外绝对根明确拒绝（不改历史记录、不删外部）。"""
    problems = []
    project = _resolve_location(target)
    for root_ref in installation.get("roots") or []:
        if not isinstance(root_ref, str) or not root_ref:
            problems.append({"reason": "skill root reference invalid", "root": root_ref})
            continue
        base = root_ref if os.path.isabs(root_ref) else os.path.join(os.path.abspath(target), root_ref)
        try:
            resolved = _resolve_location(base)
        except ValueError as exc:
            problems.append({"reason": "skill root has a broken symlink", "root": root_ref,
                             "detail": str(exc)})
            continue
        if not _contains(project, resolved):
            problems.append({"reason": "registered skill root resolves outside the project root",
                             "root": root_ref, "resolved": resolved, "project": project})
    return problems


def plan_writes(target, skill_roots, manifest):
    """把清单展开成写入计划；任一条目不合规即**整批拒绝**（不写入任何文件）。

    与 `uninstall.py` 同判据：安全相对路径 + 真实落点包含 + 目标类别白名单。
    安装面向全部平台：清单里的每个 host_hook 资产都投放（platform 键只表示"它属于哪个
    宿主"，不再是筛选条件）；per-asset 平台条件合法性仍在此核（与 self_check/verify_assets 同判据）。
    """
    problems = list(_host_hook_plan_problems(manifest))
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
        if target_class == "host_hook":
            bases = [target_of(target)]
        else:
            bases = [target_of(target)] if target_class == "project_wf" else list(skill_roots)
        for base in bases:
            destination = os.path.join(base, *relative.split("/"))
            problem = boundary_problem(target, base, destination)
            if problem:
                problem = dict(problem, path=relative, target_class=target_class)
                problems.append(problem)
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
