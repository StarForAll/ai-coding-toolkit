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

    result = subprocess.run(["git", "rev-parse", f"{release_ref}^{{commit}}"], cwd=source,
                            capture_output=True, text=True, check=False)
    if result.returncode != 0:
        return None
    return result.stdout.strip()


def verify_assets(source, manifest):
    """核清单登记与发行树字节一致；非对象条目按"不可解释"整批拒绝（不抛裸异常）。"""
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
        actual = file_digest(target)
        if actual is None:
            problems.append({"asset": source_path, "reason": "missing in release tree"})
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


class Lock:
    def __init__(self, path):
        self.path = path
        self.fd = None

    def __enter__(self):
        self.fd = os.open(self.path, os.O_RDWR | os.O_CREAT, 0o644)
        try:
            fcntl.flock(self.fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            os.close(self.fd)
            raise RuntimeError(f"lock busy: {exc}") from exc
        content = os.pread(self.fd, len(LOCK_MARK) + 1, 0)
        if content == b"":
            os.pwrite(self.fd, LOCK_MARK, 0)
            os.fsync(self.fd)
        elif content != LOCK_MARK:
            fcntl.flock(self.fd, fcntl.LOCK_UN)
            os.close(self.fd)
            raise ValueError("lock mark unknown (initialization unfinished or foreign file)")
        return self

    def __exit__(self, exc_type, exc, tb):
        if self.fd is not None:
            try:
                fcntl.flock(self.fd, fcntl.LOCK_UN)
            finally:
                os.close(self.fd)
        return False


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

    python3 {os.path.join(os.path.abspath(target), '.wf/bin/wf.py')} status

## 独立恢复入口（自含单文件）

    python3 .wf/bin/repair.py
    python3 .wf/bin/uninstall.py

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
        "print(json.dumps({'supported': sorted(gates.supported_keys()),"
        " 'handlers': gates.HANDLERS, 'commands': sorted(cli.COMMANDS)}))"
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
PLATFORMS = {
    "dsh": {"dir": ".agents/skills", "reads_shared": True},
    "codex": {"dir": ".agents/skills", "reads_shared": True},
    "cursor": {"dir": ".cursor/skills", "reads_shared": True},
    "geminicli": {"dir": ".gemini/skills", "reads_shared": True},
    "copilot": {"dir": ".github/skills", "reads_shared": True},
    "claudecode": {"dir": ".claude/skills", "reads_shared": False},
}
PLATFORM_ALIASES = {"claude": "claudecode", "gemini": "geminicli", "ghcopilot": "copilot"}
SHARED_SKILL_DIR = ".agents/skills"


def resolve_skill_roots(target, platforms):
    """把 --platform 解析成项目内技能目录（绝对路径，已去重）。

    未知名不给猜测：直接拒绝并列出支持的平台。
    """
    roots, unknown = [], []
    for name in platforms:
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


def main(argv=None):
    parser = argparse.ArgumentParser(description="wf 发行根安装入口")
    parser.add_argument("--target", required=True)
    parser.add_argument("--release-ref", required=True)
    parser.add_argument("--source", required=True)
    parser.add_argument("--platform", action="append", default=[],
                        help="目标项目实际使用的 agent（可重复）：dsh|codex|cursor|geminicli|copilot|claudecode")
    parser.add_argument("--confirm", action="store_true")
    parser.add_argument("--host-id", default=None)
    parser.add_argument("--verify-capability", action="store_true")
    parser.add_argument("--provider", choices=("host", "wf"), default=None)
    parser.add_argument("--capability-evidence", action="append", default=[],
                        metavar="kind", help="人给出的实际观察种类（压缩/重入/新会话/传递），可重复")
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
    problems = verify_assets(source, manifest)
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
        # R50-11：预览必须展示将写入的完整 session_profile（身份来源声明要经人确认）
        preview_evidence = _profile_evidence(args)
        preview_status = ("verified" if args.verify_capability and _has_observation(args.capability_evidence)
                          else ("unknown" if args.verify_capability else "unknown"))
        lines += ["另将创建：.wf-lock、.wf/、.wf/writer.json（初始维护持有）、.wf/install/*",
                  "会话身份（session_profile）：",
                  f"  host_id={args.host_id}",
                  f"  provider={getattr(args, 'provider', None) or ('host' if args.host_id else None)}",
                  "  transport=request_json",
                  f"  capability.status={preview_status}"
                  + ("" if preview_status == "verified" else
                     "（声明式：需人给出实际观察证据才转 verified）"),
                  f"  evidence_refs={json.dumps(preview_evidence, ensure_ascii=False)}",
                  "托管段（.gitignore）：", "  " + managed_segment(manifest).replace("\n", "\n  "),
                  f"平台：{json.dumps(sorted({PLATFORM_ALIASES.get(name, name) for name in args.platform}), ensure_ascii=False)}",
                  f"技能目录（目标项目内）：{json.dumps([os.path.relpath(root, args.target) for root in skill_roots], ensure_ascii=False)}"]
        if clues:
            lines.append("Trellis 线索（人确认后可继续，但本会话不得混跑两套流程）：")
            lines += [f"  - {clue['path']} ({clue['kind']})" for clue in clues]
        lines.append("确认后重跑并加 --confirm。")
        return ok("\n".join(lines),
                  {"preview": True, "clues": clues,
                   "session_profile": {"host_id": args.host_id,
                                       "provider": getattr(args, "provider", None) or ("host" if args.host_id else None),
                                       "transport": "request_json",
                                       "capability_status": preview_status,
                                       "evidence_refs": preview_evidence}}, args.json)

    if not skill_roots:
        return blocked("WF_PATH_INVALID", "至少需要一个 --platform（技能装在目标项目内）",
                       {"supported": sorted(PLATFORMS)}, args.json)
    if os.path.exists(os.path.join(args.target, ".wf/writer.json")):
        return blocked("WF_ASSET_DECISION",
                       "目标已有 wf 项目数据（writer.json 存在）：升级走 wf.py upgrade（第三轮），不按新装覆盖",
                       {"target": args.target}, args.json)
    lock_path = os.path.join(args.target, ".wf-lock")
    try:
        lock = Lock(lock_path)
    except ValueError as exc:
        return blocked("WF_ASSET_DECISION", f"锁对象冲突：{exc}", {"path": lock_path}, args.json)
    except RuntimeError as exc:
        return blocked("WF_WRITER_BUSY", f"锁被占用：{exc}", {"path": lock_path}, args.json)

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
                os.chmod(destination, os.stat(source_file).st_mode | 0o600)
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
            "manifest_digest": manifest_digest,
            "platforms": sorted({PLATFORM_ALIASES.get(name, name) for name in args.platform}),
            "roots": [os.path.relpath(root, args.target).replace(os.sep, "/") for root in skill_roots],
            "assets": [{"target": relative, "root_ref": "project" if base == args.target else base,
                        "digest": asset.get("digest"), "source_path": asset.get("source_path")}
                       for base, asset, relative in writes],
            "decisions": [],
            "session_profile": {
                "host_id": args.host_id,
                "provider": getattr(args, "provider", None) or ("host" if args.host_id else None),
                "transport": "request_json",
                "capability": {
                    # 只有人给出机制稿列举的观察证据（压缩/重入/新会话/传递）才算 verified；
                    # 仅勾选 --verify-capability 属声明，落 unknown 并保留声明记录
                    "status": ("verified"
                               if args.verify_capability and _has_observation(getattr(args, "capability_evidence", None))
                               else "unknown"),
                    "verified_version": None,
                    "evidence_refs": _profile_evidence(args, stamp=now_str()),
                },
            },
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

        probe = subprocess.run(["git", "rev-parse", "HEAD"], cwd=args.target, capture_output=True, text=True,
                               check=False)
        if probe.returncode == 0:
            head_before = probe.stdout.strip() or None
        changes = [{"path": entry["target"], "before": None, "after": file_digest(entry["target"])}
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




def _profile_evidence(args, stamp=None):
    """预览与落盘共用的证据清单：声明记录 + 人给的观察（同一构造，避免两处不一致）。"""
    entries = []
    if getattr(args, "verify_capability", False):
        entry = {"declared_by": "installer preview", "kind": "declared-verification",
                 "ref": f"preview: host_id={args.host_id}"}
        if stamp:
            entry["at"] = stamp
        entries.append(entry)
    for item in getattr(args, "capability_evidence", None) or []:
        entry = _evidence_entry(item)
        if stamp:
            entry["at"] = stamp
        entries.append(entry)
    return entries

def _evidence_entry(item):
    """`kind=<种类>;ref=<观察引用>;by=<声明人>` → 证据条目（与 dev-deploy 同解析）。"""
    fields = dict(part.split("=", 1) for part in str(item).split(";") if "=" in part)
    entry = {"declared_by": fields.get("by", "human preview"),
             "kind": fields.get("kind"),
             "ref": fields.get("ref")}
    return {key: value for key, value in entry.items() if value}

OBSERVATION_KINDS = ("compaction", "reentry", "new-session", "transport")


def _has_observation(items):
    """按 `kind=…;ref=…` 判断是否有人给出的实际观察（不是"谁在何时声明"）。"""
    for item in items or []:
        fields = dict(part.split("=", 1) for part in str(item).split(";") if "=" in part)
        if fields.get("kind") in OBSERVATION_KINDS and str(fields.get("ref") or "").strip():
            return True
    return False

def target_of(target):
    return os.path.abspath(target)


if __name__ == "__main__":
    if sys.version_info < MIN_VERSION:
        sys.stderr.write(f"wf install.py requires Python >= {MIN_VERSION[0]}.{MIN_VERSION[1]}\n")
        raise SystemExit(1)
    raise SystemExit(main())
