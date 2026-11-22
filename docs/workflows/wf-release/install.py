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


def self_check(target, manifest, skill_roots, platforms=None):
    """安装/升级后自检（§10.4）。

    W3-2（三轮）：`platforms` 是本次安装平台集（安装记录 platforms）——
    host_hook 只核声明平台一侧的落点（dsh 项目不核 .codex/hooks/，否则会把
    未投放的 hook 误报 digest mismatch）；per-asset 平台条件合法性同 plan_writes。
    """
    problems = list(_host_hook_plan_problems(manifest))
    for index, asset in enumerate(manifest.get("assets") or []):
        if not isinstance(asset, dict):
            problems.append({"reason": "asset entry is not an object", "index": index})
            continue
        if asset.get("target_class") == "release_only":
            continue
        if asset.get("target_class") == "host_hook":
            platform_set = platforms if platforms is not None else set()
            if asset.get("platform") not in platform_set:
                continue          # 非本次声明平台：未投放是预期，不核
            path = os.path.join(target, *asset["target_relative"].split("/"))
            if file_digest(path) != asset.get("digest"):
                problems.append({"target": path, "reason": "digest mismatch after deploy"})
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


HOOK_SCRIPT_RELATIVE = ".codex/hooks/wf-session-identity.py"
HOOK_COMMAND = "python3 -X utf8 .codex/hooks/wf-session-identity.py"


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


def merge_hooks_json(target, script_name=HOOK_SCRIPT_RELATIVE, command=HOOK_COMMAND):
    """W3-2：codex 平台的 hooks.json 合并——无文件则创建（仅本条目），已有则保序追加。

    幂等：已有条目引用本脚本文件名即视为已登记，不重复追加。dict 按插入序原样 dump，
    不动用户其他条目。同名脚本被用户其他命令串占用 ⇒ 报人裁决（§7.1 同名未知文件口径）。
    返回 {"created": bool, "appended": bool}。
    """
    path = hooks_json_path(target)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    data = None
    if os.path.isfile(path):
        try:
            with open(path, "r", encoding="utf-8") as handle:
                data = json.load(handle)
        except (OSError, ValueError):
            data = None
        if not isinstance(data, dict) or not isinstance(data.get("hooks"), dict):
            raise ValueError(f"hooks.json 已存在但不可解析或形状不属 Codex：{path}")
    entry = {"hooks": [{"type": "command", "command": command, "timeout": 15}]}
    if data is None:
        payload = {"hooks": {"SessionStart": [entry]}}
        _dump_json(path, payload)
        return {"created": True, "appended": False}
    session_start = data["hooks"].get("SessionStart")
    if not isinstance(session_start, list):
        session_start = []
        data["hooks"]["SessionStart"] = session_start
    for existing in session_start:
        if _hooks_entry_matches(existing, os.path.basename(script_name)):
            if any(h.get("command") != command for h in existing.get("hooks") or []):
                raise ValueError("同名 hook 脚本已被用户以不同命令串占用：交人裁决")
            return {"created": False, "appended": False}
    session_start.append(entry)
    _dump_json(path, data)
    return {"created": False, "appended": True}


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


def _platforms_of(args_platforms):
    return {PLATFORM_ALIASES.get(name, name) for name in _flatten_platforms(args_platforms)}


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
            # 项目→基址→资产的第一层/第二层边界必须在任何冲突读取与写入前复核：
            # 历史域外 root_ref 明确拒绝（不序列化成合法绝对根，也不跟随它清理外部）。
            root_problems = registered_root_problems(args.target, installation)
            if root_problems:
                return blocked("WF_ASSET_DECISION",
                               "安装记录中的技能根域外/不可解析：整批拒绝，不改历史记录、不删除外部对象",
                               {"problems": root_problems[:20]}, args.json)
            # 锁内重算计划：锁外传入的 writes 只能作为输入，不能作为写入许可。
            # 平台集 = 已装 ∪ 本次追加（host_hook 只在它声明平台被本次追加时投放）
            _combined_platforms = ({item for item in installation.get("platforms") or [] if isinstance(item, str)}
                                   | _platforms_of(args.platform))
            writes, plan_problems = plan_writes(args.target, skill_roots, manifest,
                                                 platforms=_combined_platforms)
            if plan_problems:
                return blocked("WF_ASSET_DECISION",
                               "锁内复核发现资产越界：整批拒绝，不写任何文件",
                               {"problems": plan_problems[:20]}, args.json)
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
                if asset.get("target_class") == "host_hook":
                    # W3-2（三轮）：追加平台时投放 hook 文件——只在声明平台本次新增时
                    if asset.get("platform") not in added:
                        continue
                elif asset.get("target_class") != "skill_root" or base not in new_roots:
                    continue
                source_file = os.path.join(os.path.abspath(args.source),
                                           *str(asset.get("source_path") or "").split("/"))
                if not os.path.isfile(source_file):
                    return blocked("WF_RELEASE_CONFLICT", "发行树缺该资产的源文件",
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
            hook_platforms_deployed = set()
            for entry in pending:
                os.makedirs(os.path.dirname(entry["destination"]), exist_ok=True)
                with open(entry["destination"], "wb") as handle:
                    handle.write(entry["data"])
                if entry["asset"].get("executable"):
                    os.chmod(entry["destination"], os.stat(entry["source"]).st_mode | 0o755)
                deployed.append(entry["destination"])
                if entry["asset"].get("target_class") == "host_hook":
                    hook_platforms_deployed.add(entry["asset"].get("platform"))
            # W3-2：追加平台投放 hook 后合并 hooks.json（同首装：幂等/同名冲突交人）
            for platform in sorted(hook_platforms_deployed):
                if platform != "codex":
                    continue
                try:
                    merge_hooks_json(args.target)
                except ValueError as exc:
                    return blocked("WF_ASSET_DECISION", str(exc),
                                   {"hooks_json": hooks_json_path(args.target)}, args.json)

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
                    "upstream_version": manifest.get("version"),
                    "upstream_fingerprint": entry["asset"].get("digest"),
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
            append_maintenance_journal(args.target, writer["maintenance_results"][-1])
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


def _installation_asset_problems(installation):
    if not isinstance(installation, dict):
        return ["installation record is not an object"]
    return []


def _abs_base(target, root_ref):
    if root_ref == "project" or not root_ref:
        return os.path.abspath(target)
    return root_ref if os.path.isabs(root_ref) else os.path.join(os.path.abspath(target), root_ref)


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
      非 archived 记录须 status==not_started 或（paused==true 且 suspended==false）；
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
            if record.get("status") != "not_started" and not (paused and not suspended):
                problems.append({"reason": "active task not paused/not-started",
                                 "path": os.path.relpath(record_path, target),
                                 "status": record.get("status"),
                                 "paused": paused, "suspended": suspended})
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
    if os.path.isfile(writer_path):
        writer, error = _load_task_record_safe(writer_path)
        if writer is None:
            problems.append({"reason": "writer unreadable", "detail": error})
        else:
            problem = _writer_problem(writer)
            if problem and problem != "writer is recovering; 先按 repair 核对旧写者再追加平台":
                problems.append({"reason": "writer not idle", "detail": problem})
    return problems, wip_facts, writer


def three_way_plan(target, installation, manifest, source, args_platforms, keep, restore):
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
    # N：新发行清单（host_hook 只含声明平台）
    platforms = set(args_platforms or [])
    incoming = {}
    for asset in manifest.get("assets") or []:
        if not isinstance(asset, dict) or asset.get("target_class") == "release_only":
            continue
        if asset.get("target_class") == "host_hook" and asset.get("platform") not in platforms:
            continue
        rel = asset.get("target_relative")
        if not rel:
            continue
        if asset.get("target_class") == "skill_root":
            bases = [_abs_base(target, root) for root in installation.get("roots") or []]
        else:
            bases = [os.path.abspath(target)]
        for base in bases:
            incoming[(base, rel)] = dict(asset)
    keep_rels = set(keep or [])
    restore_rels = set(restore or [])
    # ① 上游删除
    for key, o_entry in sorted(installed.items()):
        if key in incoming:
            continue
        base, rel = key
        local = file_digest(os.path.join(base, *rel.split("/")))
        if local is not None and local == o_entry.get("digest"):
            deletes.append({"base": base, "relative": rel, "kind": "delete-candidate",
                           "local": local, "upstream": o_entry.get("digest")})
        else:
            unresolved.append({"base": base, "relative": rel, "kind": "upstream-removed-local-changed",
                               "local": local, "upstream": o_entry.get("digest")})
    # ②③④⑤⑥⑦⑧：共同键与新增
    for key, n_asset in sorted(incoming.items()):
        base, rel = key
        local = file_digest(os.path.join(base, *rel.split("/")))
        o_entry = installed.get(key)
        n_digest = n_asset.get("digest")
        if o_entry is None:
            if local is None:
                actions.append({"base": base, "relative": rel, "kind": "add", "asset": n_asset,
                               "local": None, "upstream": None, "new": n_digest})
            elif local == n_digest:
                # 本地已是同字节：登记即可，不重复写
                actions.append({"base": base, "relative": rel, "kind": "register", "asset": n_asset,
                               "local": local, "upstream": None, "new": n_digest})
            else:
                unresolved.append({"base": base, "relative": rel, "kind": "add-hits-user-file",
                                   "local": local, "new": n_digest})
            continue
        if local is None:
            actions.append({"base": base, "relative": rel, "kind": "reinstall", "asset": n_asset,
                           "local": None, "upstream": o_entry.get("digest"), "new": n_digest})
            continue
        if local == n_digest:
            actions.append({"base": base, "relative": rel, "kind": "noop", "asset": n_asset,
                           "local": local, "upstream": o_entry.get("digest"), "new": n_digest})
            continue
        # 同一已接受偏离（两边指纹均同）免重复询问——判在 L==O **之前**：
        # 偏离的本义就是 L≠O（人保留本地），埋在 L==O 分支内会让"已接受偏离"被重问。
        if (o_entry.get("upstream_fingerprint") == n_digest
                and o_entry.get("local_fingerprint") == local
                and o_entry.get("decision")):
            actions.append({"base": base, "relative": rel, "kind": "deviation-kept", "asset": n_asset,
                           "local": local, "upstream": o_entry.get("digest"), "new": n_digest,
                           "decision": o_entry.get("decision")})
            continue
        if local == o_entry.get("digest"):
            actions.append({"base": base, "relative": rel, "kind": "update", "asset": n_asset,
                           "local": local, "upstream": o_entry.get("digest"), "new": n_digest})
            continue
        # 其他冲突：人选保留/恢复；人合并后重跑按表重判
        decision = None
        if rel in keep_rels:
            decision = "human (upgrade --keep)"
        elif rel in restore_rels:
            decision = "human (upgrade --restore)"
        if decision:
            actions.append({"base": base, "relative": rel, "kind": "deviation", "asset": n_asset,
                           "local": local, "upstream": o_entry.get("digest"), "new": n_digest,
                           "decision": decision,
                           "restore": decision.endswith("--restore)")})
        else:
            unresolved.append({"base": base, "relative": rel, "kind": "local-deviates",
                               "local": local, "upstream": o_entry.get("digest"), "new": n_digest,
                               "exits": [f"保留本地：重跑加 --keep {rel}",
                                         f"恢复发行内容：重跑加 --restore {rel}",
                                         "或人工合并后重跑（按表重判）"]})
    return {"actions": actions, "deletes": deletes, "unresolved": unresolved}, unresolved


def export_deviations(args, installation, plan, source, commit):
    """W4-2：`--export-deviations --out <dir>` 只读导出。

    对每个接受偏离资产生成 O→L 偏离补丁（O 字节按安装记录的可重取来源取回——
    `_committed_bytes(source_commit)` 自发行检出；取不回时如实产出摘要+说明，不伪造空补丁）
    + manifest.json 清单。写面规则：--out 不存在则创建、已存在必须为空目录（非空拒）；
    逐文件原子写；目标含符号链接拒；部分写入失败 ⇒ 停止、非零、如实报告已写清单（不自动删）。
    """
    out = args.out
    if not out:
        return blocked("WF_USAGE_INVALID", "--export-deviations 需要 --out <目录>", {}, args.json)
    out = os.path.abspath(out)
    if os.path.islink(out) or (os.path.exists(out) and not os.path.isdir(out)):
        return blocked("WF_PATH_INVALID", "--out 目标含符号链接或不是目录", {"out": out}, args.json)
    if os.path.isdir(out) and os.listdir(out):
        return blocked("WF_ASSET_DECISION", "--out 目录已存在且非空：不覆盖、不并入用户文件",
                       {"out": out, "entries": sorted(os.listdir(out))[:20]}, args.json)
    deviation_actions = [item for item in plan["actions"]
                         if item.get("kind") in ("deviation", "deviation-kept")]
    if not deviation_actions:
        return blocked("WF_ASSET_DECISION",
                       "无接受偏离的资产：导出为空（如需留档可自行记录，不伪造空补丁）",
                       {"deviations": 0}, args.json)
    os.makedirs(out, exist_ok=True)
    exported, failures = [], []
    dev_dir = os.path.join(out, "deviations")
    os.makedirs(dev_dir, exist_ok=True)
    for index, item in enumerate(sorted(deviation_actions, key=lambda x: x["relative"]), start=1):
        base, rel = item["base"], item["relative"]
        local_path = os.path.join(base, *rel.split("/"))
        source_path = (item.get("asset") or {}).get("source_path") or rel
        o_bytes = _committed_bytes(source, commit, source_path)
        l_bytes = None
        try:
            with open(local_path, "rb") as handle:
                l_bytes = handle.read()
        except OSError as exc:
            failures.append({"path": rel, "reason": f"local unreadable: {exc}"})
            continue
        name = f"{index}-{os.path.basename(rel)}.patch"
        try:
            if o_bytes is None:
                text = (f"# O（安装记录来源 {installation.get('source_commit')}）不可取回："
                        f"无补丁可生成\n"
                        f"# local_fingerprint={item.get('local')}\n"
                        f"# upstream_fingerprint={item.get('upstream')}\n"
                        f"# decision={item.get('decision')}\n")
                data = text.encode("utf-8")
            else:
                diff = difflib.unified_diff(
                    o_bytes.decode("utf-8", "replace").splitlines(keepends=True),
                    (l_bytes or b"").decode("utf-8", "replace").splitlines(keepends=True),
                    fromfile=f"a/{rel}", tofile=f"b/{rel}")
                data = "".join(diff).encode("utf-8")
            tmp = os.path.join(dev_dir, name + ".tmp")
            with open(tmp, "wb") as handle:
                handle.write(data)
            os.replace(tmp, os.path.join(dev_dir, name))
            exported.append({"path": rel, "patch": f"deviations/{name}",
                             "upstream_version": installation.get("version"),
                             "local_fingerprint": item.get("local"),
                             "upstream_fingerprint": item.get("upstream"),
                             "decision": item.get("decision")})
        except OSError as exc:
            failures.append({"path": rel, "reason": f"write failed: {exc}"})
            break                     # 停止：如实报告已写清单，不自动删已写内容
    if failures:
        return blocked("WF_PERSISTENCE_FAILED",
                       "偏离导出部分失败：停止写入，已写清单如下（不自动删除，人决定处置）",
                       {"exported": exported, "failures": failures}, args.json)
    _dump_json(os.path.join(out, "manifest.json"),
               {"exported_at": now_str(), "source_commit": installation.get("source_commit"),
                "version": installation.get("version"), "deviations": exported})
    return ok("偏离导出完成", {"out": out, "deviations": len(exported)}, args.json)


def run_upgrade(args, manifest, commit):
    """W4-1：`install.py --upgrade`（三方升级主入口）。"""
    target = os.path.abspath(args.target)
    installation_path = os.path.join(target, ".wf", "install", "installation.json")
    if not os.path.isfile(installation_path):
        return blocked("WF_RECORD_INVALID", "目标未安装 wf（缺安装记录）：先安装再升级",
                       {"installation": installation_path}, args.json)
    installation, _error = _load_task_record_safe(installation_path)
    if installation is None:
        return blocked("WF_RECORD_INVALID", "安装记录不可读", {"path": installation_path}, args.json)
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
    platforms = installation.get("platforms") or []
    plan, unresolved = three_way_plan(target, installation, manifest, os.path.abspath(args.source),
                                      platforms, getattr(args, "keep", None),
                                      getattr(args, "restore", None))
    # 必需资产缺失（reinstall 未完成即相关入口不可用）不额外设档：动作本身覆盖。
    if args.export_deviations:
        return export_deviations(args, installation, plan, os.path.abspath(args.source), commit)
    if unresolved:
        return blocked("WF_ASSET_DECISION",
                       "三方匹配存在需人裁决的路径（保留/恢复/合并后重跑按表重判）",
                       {"unresolved": unresolved[:20],
                        "upstream_removed": plan["deletes"]}, args.json)
    operation_id = f"upgrade-{uuid.uuid4().hex}"
    selected = sorted({item["relative"] for item in plan["actions"]}
                       | {item["relative"] for item in plan["deletes"]})
    before_states = [{"relative": item["relative"], "kind": item["kind"],
                     "local": item.get("local"), "upstream": item.get("upstream"),
                     "new": item.get("new")}
                     for item in plan["actions"] + plan["deletes"]]
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
        "risks": [f"{item['kind']}: {item['relative']}" for item in plan["deletes"]]
                + [f"deviation kept: {item['relative']}" for item in plan["actions"]
                   if item["kind"] in ("deviation", "deviation-kept")],
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
                platforms, getattr(args, "keep", None), getattr(args, "restore", None))
            fresh_selected = sorted({i["relative"] for i in fresh_plan["actions"]}
                                    | {i["relative"] for i in fresh_plan["deletes"]})
            if fresh_selected != selected:
                return blocked("WF_PREVIEW_STALE",
                               "预览已失效：锁内重核与预览不一致（重新预览）",
                               {"preview": selected, "current": fresh_selected}, args.json)
            if fresh_unresolved:
                return blocked("WF_ASSET_DECISION", "锁内重核出现新的需人裁决路径",
                               {"unresolved": fresh_unresolved[:20]}, args.json)
            # 维护写者
            writer = fresh_writer or {}
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
            # 安装记录：身份 + assets（偏离登记按机制稿 §10.4 字段名）
            installation["version"] = manifest.get("version")
            installation["release_ref"] = args.release_ref
            installation["source_commit"] = commit
            installation["rules_digest"] = (manifest.get("compatibility") or {}).get("rules_digest")
            installation["manifest_digest"] = file_digest(os.path.join(source, "wf-release.json"))
            _assets = []
            for item in fresh_plan["actions"]:
                entry = {"target": item["relative"],
                         "root_ref": "project" if item["base"] == target else item["base"],
                         "digest": item.get("new"),
                         "source_path": (item.get("asset") or {}).get("source_path"),
                         "upstream_version": manifest.get("version"),
                         "upstream_fingerprint": item.get("upstream")}
                if item["kind"] in ("deviation", "deviation-kept"):
                    # 偏离登记（机制稿 §10.4 字段名）：local_fingerprint=目标实际字节，
                    # upstream_fingerprint=本版发行字节，decision=人的处置
                    entry["local_fingerprint"] = item.get("local")
                    entry["upstream_fingerprint"] = item.get("new")
                    entry["decision"] = item.get("decision")
                    entry["digest"] = item.get("local")     # 实际在目标上的字节
                _assets.append(entry)
            installation["assets"] = _assets
            installation["upgraded_at"] = now_str()
            _dump_json(installation_path, installation)
            gitignore = ensure_gitignore(target, manifest)
            skill_roots = [(_abs_base(target, root)) for root in installation.get("roots") or []]
            problems = self_check(target, manifest, skill_roots, platforms=set(platforms))
            released_generation = held_generation + 1
            writer.update({"state": "idle", "holder": None, "generation": released_generation,
                           "revision": int(writer.get("revision") or 0) + 1,
                           "checkpoint": {"operation": operation_id, "phase": "upgrade-applied"},
                           "updated_at": now_str()})
            writer["maintenance_results"] = list(writer.get("maintenance_results") or []) + [{
                "operation": operation_id,
                "preview_digest": token.digest(),
                "head_before": None,
                "changes": changes,
                "receipt_git_state": {"head": None, "tracked_paths": len(changes)},
                "result": "applied_pending_commit",
                "disposition": None,
            }]
            _dump_json(os.path.join(target, ".wf/writer.json"), writer)
            if problems:
                writer["checkpoint"] = {"operation": operation_id, "phase": "self-check-failed",
                                        "problems": problems[:20]}
                _dump_json(os.path.join(target, ".wf/writer.json"), writer)
                return blocked("WF_PERSISTENCE_FAILED",
                               "升级已写入但安装自检失败：现场保留（按 §5.4 恢复语义处置）",
                               {"problems": problems[:20]}, args.json)
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
    parser.add_argument("--platform", action="append", nargs="+", default=[],
                        help="目标项目实际使用的 agent（可重复）：dsh|codex|cursor|geminicli|copilot|claudecode")
    parser.add_argument("--confirm", action="store_true")
    parser.add_argument("--strict-source", dest="strict_source", action="store_true",
                        help="发行子树必须与提交一致（脏检出即拒绝）；发行作者仓库通常不带此参数")
    parser.add_argument("--upgrade", action="store_true",
                        help="三方升级模式（W4-1）：O=安装记录/L=本地/N=新发行 逐路径匹配")
    parser.add_argument("--apply", action="store_true",
                        help="升级：应用预览（交互 TTY 输入预览指纹；同一进程完成，重跑预览即销毁）")
    parser.add_argument("--export-deviations", dest="export_deviations", action="store_true",
                        help="升级：只读导出接受偏离的 O→L 补丁与清单（不需令牌/写者）")
    parser.add_argument("--out", default=None, help="偏离导出目录（不存在则创建；已存在必须为空）")
    parser.add_argument("--keep", action="append", default=[],
                        help="人选择保留本地的冲突路径（相对项目根；记录偏离登记）")
    parser.add_argument("--restore", action="append", default=[],
                        help="人选择恢复发行内容的冲突路径（相对项目根）")
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
    managed = manifest.get("gitignore_managed") or {}
    if not managed.get("lines") or not managed.get("begin_marker") or not managed.get("end_marker"):
        # 托管段是发行规则的一部分（计入 rules_digest）：缺登记就拒绝，不猜忽略行
        return blocked("WF_ASSET_DECISION", "发行清单缺 gitignore_managed（托管段唯一来源）",
                       {"manifest": manifest_path}, args.json)
    if getattr(args, "upgrade", False):
        # W4-1：升级模式（含 --export-deviations 只读导出）。--source 必须是发行检出根
        # （load_manifest 要求 wf-release.json 直在 source 下，写成 <检出>/wf-release 即 WF_PATH_INVALID）。
        return run_upgrade(args, manifest, commit)

    skill_roots, unknown_platforms = resolve_skill_roots(args.target, args.platform)
    if unknown_platforms:
        return blocked("WF_PATH_INVALID", "未知平台，无法确定其 skill 发现层",
                       {"unknown": unknown_platforms, "supported": sorted(PLATFORMS)}, args.json)
    # 写入计划先整批核验：路径合法性、真实落点、类别白名单；任一越界即拒绝写入任何文件
    writes, plan_problems = plan_writes(args.target, skill_roots, manifest,
                                         platforms=_platforms_of(args.platform))
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
            # 锁内全批复核（首装）：路径/落点/类别必须在 mkdir .wf 与任何写入之前重新成立。
            writes, plan_problems = plan_writes(args.target, skill_roots, manifest,
                                                 platforms=_platforms_of(args.platform))
            if plan_problems:
                return blocked("WF_ASSET_DECISION",
                               "锁内复核发现资产越界：整批拒绝，不写任何文件",
                               {"problems": plan_problems[:20]}, args.json)
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
            # W3-2：host_hook 部署后合并 hooks.json（保序追加/幂等/同名冲突交人；
            # 现清单唯一 host_hook 平台是 codex——其他平台的 hook 落点随部署表扩展）
            for base, asset, relative in writes:
                if asset.get("target_class") != "host_hook":
                    continue
                if asset.get("platform") != "codex":
                    continue
                try:
                    merge_hooks_json(args.target)
                except ValueError as exc:
                    return blocked("WF_ASSET_DECISION", str(exc),
                                   {"hooks_json": hooks_json_path(args.target)}, args.json)

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
                "installed_at": now_str(),
                "tool": "install.py",
            }
            with open(os.path.join(install_dir, "installation.json"), "w", encoding="utf-8", newline="\n") as handle:
                handle.write(json.dumps(installation, indent=2, sort_keys=True, ensure_ascii=False) + "\n")
            with open(os.path.join(install_dir, "recovery.md"), "w", encoding="utf-8", newline="\n") as handle:
                handle.write(recovery_text(args.target, installation))
            gitignore = ensure_gitignore(args.target, manifest)
            problems = self_check(args.target, manifest, skill_roots,
                                 platforms=_platforms_of(args.platform))
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
            append_maintenance_journal(args.target, writer["maintenance_results"][-1])

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


def plan_writes(target, skill_roots, manifest, platforms=None):
    """把清单展开成写入计划；任一条目不合规即**整批拒绝**（不写入任何文件）。

    与 `uninstall.py` 同判据：安全相对路径 + 真实落点包含 + 目标类别白名单。
    W3-2（三轮）：host_hook 按声明平台投放（per-asset 平台条件）——`platforms` 是本次
    安装的 --platform 集（已按别名归一）；host_hook 不在声明平台的安装中被跳过（dsh
    项目不出现 .codex/hooks/），platforms 为 None 时按不投放处理（不猜）。
    per-asset 平台条件合法性三处拒之一在此（与 self_check/verify_assets 同判据）。
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
            platform_set = platforms if platforms is not None else set()
            if asset.get("platform") not in platform_set:
                continue          # 不在本次安装的声明平台：不投放（合法跳过，不是问题）
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
