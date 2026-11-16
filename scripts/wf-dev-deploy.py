#!/usr/bin/env python3
"""wf-dev-deploy.py — 首轮开发态部署（实现稿 §4.6）。

authoring 开发工具，不进发行清单。预览 → 人确认 → 首装契约 → 投放 → 自检 → 释放为空闲。
身份来源固定为 `dev-manifest.json`，清单生成算法与 build-wf-release.py 同名同源。
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import uuid

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import wf_release_common as common  # noqa: E402
from wflib import assets as wf_assets  # noqa: E402
from wflib import config as wf_config  # noqa: E402
from wflib import lock as wf_lock  # noqa: E402
from wflib import records as wf_records  # noqa: E402
from wflib import fingerprint as wf_fingerprint
from wflib import maintenance as wf_maintenance  # noqa: E402
from wflib import writer as wf_writer  # noqa: E402
from wflib.paths import join, safe_write_target  # noqa: E402

DEV_VERSION = "0.0.0-dev"
GITIGNORE = common.GITIGNORE_MANAGED


def emit(payload, json_mode=False):
    if json_mode:
        sys.stdout.write(json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n")
    else:
        sys.stdout.write(payload.get("message", "") + "\n")
    sys.stdout.flush()
    return 0 if payload.get("ok") else 1


def fail(code, message, json_mode=False, facts=None):
    return emit({"ok": False, "code": code, "message": f"BLOCKED {code}\n{message}",
                 "facts": facts or {}}, json_mode)


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


# 部署表只有一份：直接取发行侧 install.py 的表，避免开发态与发行态各写一份（纪律 #4）。
def _load_install_table():
    import importlib.util

    spec = importlib.util.spec_from_file_location("wf_install_table",
                                                  os.path.join(common.PAYLOAD, "install.py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_INSTALL = _load_install_table()
PLATFORMS = _INSTALL.PLATFORMS
PLATFORM_ALIASES = _INSTALL.PLATFORM_ALIASES
SHARED_SKILL_DIR = _INSTALL.SHARED_SKILL_DIR


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

def _resolve_location(path):
    """规范落点：解析现有祖先符号链接与 `..`，尚不存在的末段按组件拼接。"""
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


def boundary_problem(target, base, destination):
    """项目→基址→资产的两层包含关系（与 install/uninstall 同判据）。"""
    try:
        project = _resolve_location(target)
        base_real = _resolve_location(base)
        dest_real = _resolve_location(destination)
    except ValueError as exc:
        return {"reason": "path contains a broken symlink", "base": str(base),
                "path": str(destination), "detail": str(exc)}
    if not _contains(project, base_real):
        return {"reason": "asset base resolves outside the project root", "base": str(base),
                "resolved": base_real, "project": project}
    if not _contains(base_real, dest_real):
        return {"reason": "target resolves outside its base", "base": str(base),
                "path": str(destination), "resolved": dest_real}
    if not _contains(project, dest_real):
        return {"reason": "target resolves outside the project root", "path": str(destination),
                "resolved": dest_real, "project": project}
    return None


def validate_registered_roots(target, installation):
    """历史 root 记录：项目内可用；项目外/坏链明确拒绝（不序列化成合法绝对根）。"""
    problems = []
    project = _resolve_location(target)
    for root in installation.get("roots") or []:
        if not isinstance(root, str) or not root:
            problems.append({"reason": "skill root reference invalid", "root": root})
            continue
        base = root if os.path.isabs(root) else os.path.join(os.path.abspath(target), root)
        try:
            resolved = _resolve_location(base)
        except ValueError as exc:
            problems.append({"reason": "skill root has a broken symlink", "root": root,
                             "detail": str(exc)})
            continue
        if not _contains(project, resolved):
            problems.append({"reason": "registered skill root resolves outside the project root",
                             "root": root, "resolved": resolved, "project": project})
    return problems


def plan_deployment(target, skill_roots, manifest):
    """展开完整部署计划并整批复核边界；返回 (writes, problems)。"""
    writes, problems = [], []
    for root in skill_roots:
        problem = boundary_problem(target, root, root)
        if problem:
            problems.append(dict(problem, reason="skill root " + problem["reason"]))
    for asset in manifest["assets"]:
        if asset["target_class"] == "project_wf":
            destination = os.path.join(os.path.abspath(target), *asset["target_relative"].split("/"))
            problem = boundary_problem(target, os.path.abspath(target), destination)
            if problem:
                problems.append(problem)
                continue
            writes.append({"target_relative": asset["target_relative"], "source_path": asset["source_path"],
                           "root": "project", "digest": asset["digest"]})
        elif asset["target_class"] == "skill_root":
            for root in skill_roots:
                destination = os.path.join(root, *asset["target_relative"].split("/"))
                problem = boundary_problem(target, root, destination)
                if problem:
                    problems.append(problem)
                    continue
                writes.append({"target_relative": asset["target_relative"],
                               "source_path": asset["source_path"],
                               "root": root, "digest": asset["digest"]})
    if problems:
        return [], problems
    return writes, problems


def is_inside(target, path):
    real_target = os.path.realpath(target)
    real_path = os.path.realpath(path)
    return real_path == real_target or real_path.startswith(real_target + os.sep)


def root_record(target, root):
    """只序列化通过校验的项目内根；域外根不是“合法绝对根”（拒绝而不是照抄）。"""
    problem = boundary_problem(target, root, root)
    if problem:
        raise ValueError(f"refusing to record a skill root outside the project: {problem}")
    return os.path.relpath(root, target).replace(os.sep, "/")


def managed_segment():
    return "\n".join([GITIGNORE["begin_marker"]] + GITIGNORE["lines"] + [GITIGNORE["end_marker"]])


def ensure_gitignore(target):
    path = os.path.join(target, ".gitignore")
    segment = managed_segment()
    try:
        with open(path, "r", encoding="utf-8") as handle:
            text = handle.read()
    except FileNotFoundError:
        text = ""
    lines = text.splitlines()
    begin, end = GITIGNORE["begin_marker"], GITIGNORE["end_marker"]
    if begin in lines and end in lines:
        start = lines.index(begin)
        stop = lines.index(end)
        current = "\n".join(lines[start:stop + 1])
        if current != segment:
            return {"action": "conflict", "detail": "managed segment content differs from release登记"}
        return {"action": "present"}
    if begin in lines or end in lines:
        return {"action": "conflict", "detail": "managed marker present without its pair"}
    if text and not text.endswith("\n"):
        text += "\n"
    text += segment + "\n"
    wf_records.atomic_write(path, text)
    return {"action": "appended"}


def write_recovery(target, installation):
    body = f"""# wf 恢复说明

本文件由开发态部署入口写入，属本机投放事实（默认卸载保留）。

- 发行引用：{installation.get('release_ref')}
- 版本：{installation.get('version')}
- 清单摘要：{installation.get('manifest_digest')}
- 投放根：{json.dumps(installation.get('roots'), ensure_ascii=False)}

## 常规入口

```
python3 {os.path.join(os.path.abspath(target), '.wf/bin/wf.py')} status
```

## 独立恢复入口（自含单文件，不导入运行时）

```
python3 .wf/bin/repair.py              # 预览 + 终端令牌后受控修复
python3 .wf/bin/uninstall.py           # 默认卸载（保留数据与安装记录）
```

## 锁

`.wf-lock` 只创建不删除。确认无 wf 进程后可人工清理该文件与 `.gitignore` 中保留的 `/.wf-lock` 行。
"""
    wf_records.atomic_write(join(target, ".wf/install/recovery.md"), body)


def self_check(target, manifest, skill_roots, installation):
    problems = []
    for asset in manifest["assets"]:
        targets = []
        if asset["target_class"] == "project_wf":
            targets.append(join(target, asset["target_relative"]))
        elif asset["target_class"] == "skill_root":
            for root in skill_roots:
                targets.append(os.path.join(root, *asset["target_relative"].split("/")))
        elif asset["target_class"] == "release_only":
            continue
        for path in targets:
            actual = wf_records.file_digest(path)
            if actual != asset["digest"]:
                problems.append({"asset": asset["source_path"], "target": path, "reason": "digest mismatch"})
    from wflib import cli as wf_cli
    from wflib import gates as wf_gates

    bootstrap = [name for name in wf_gates.BOOTSTRAP_ENTRIES
                 if os.path.isfile(join(target, f".wf/bin/{name}.py"))]
    problems.extend(wf_gates.support_report(manifest, wf_cli.COMMANDS, bootstrap))
    if not os.path.isfile(join(target, ".wf/bin/wf.py")):
        problems.append({"missing": ".wf/bin/wf.py"})
    if not os.path.isfile(join(target, ".wf/lib/wflib/module_main.py")):
        problems.append({"missing": ".wf/lib/wflib/module_main.py"})
    ignore = check_ignore(target)
    if ignore.get("applicable") and not ignore.get("ok"):
        problems.append({"gitignore": ignore})
    writer = wf_writer.load(target)
    if not writer or writer.get("state") not in ("held", "idle"):
        problems.append({"writer": "record missing or unreadable after deploy"})
    return problems


def check_ignore(target):
    if not os.path.isdir(os.path.join(target, ".git")):
        return {"applicable": False}
    import subprocess

    probes = [".wf/.runtime/sessions/probe.json", ".wf-lock"]
    details = []
    ok = True
    for probe in probes:
        result = subprocess.run(["git", "check-ignore", "-v", "--no-index", probe], cwd=target,
                                capture_output=True, text=True, check=False)
        if result.returncode != 0:
            ok = False
            details.append({"path": probe, "reason": "not ignored"})
        elif "!" in result.stdout.split(":")[0]:
            ok = False
            details.append({"path": probe, "rule": result.stdout.strip(), "reason": "negated by later rule"})
    return {"applicable": True, "ok": ok, "details": details}



DEV_OBSERVATION_KINDS = ("compaction", "reentry", "new-session", "transport")


def deploy(args):
    target = os.path.abspath(args.target)
    skill_roots, unknown_platforms = resolve_skill_roots(args.target, args.platform)
    if unknown_platforms:
        return fail("WF_PATH_INVALID",
                    f"未知平台：{unknown_platforms}；支持 {sorted(PLATFORMS)}", args.json)
    dev_manifest = common.load_dev_manifest()
    manifest = common.build_manifest(DEV_VERSION, dev_manifest)
    writes, plan_problems = plan_deployment(target, skill_roots, manifest)
    if plan_problems:
        return fail("WF_ASSET_DECISION",
                    "技能根/资产落点越界或不可解析：整批拒绝，不写任何文件",
                    args.json, {"problems": plan_problems[:20]})

    clues = trellis_clues(target)

    if not args.confirm:
        lines = ["wf 开发态部署预览（未写入任何文件）", f"目标：{target}", f"版本：{DEV_VERSION}"]
        lines.append(f"发行引用：dev:{common.git_describe()}")
        lines.append("投放文件：")
        for entry in writes:
            base = target if entry["root"] == "project" else entry["root"]
            lines.append(f"  - {os.path.join(base, *entry['target_relative'].split('/'))}")
        lines.append("另将创建：.wf-lock、.wf/、.wf/writer.json（初始维护持有）、.wf/install/*")
        lines.append("托管段（.gitignore）：")
        for line in managed_segment().splitlines():
            lines.append(f"  {line}")
        lines.append(f"平台：{json.dumps(sorted({PLATFORM_ALIASES.get(n, n) for n in _flatten_platforms(args.platform)}), ensure_ascii=False)}")
        lines.append(f"技能目录（目标项目内）：{json.dumps([os.path.relpath(root, target) for root in skill_roots], ensure_ascii=False)}")
        if clues:
            lines.append("Trellis 线索（人确认后可继续安装，但本会话不得混跑两套流程）：")
            for clue in clues:
                lines.append(f"  - {clue['path']} ({clue['kind']})")
        lines.append("确认后重跑并加 --confirm。")
        return emit({"ok": True, "message": "\n".join(lines),
                     "preview": {"target": target, "files": writes, "clues": clues,
                                 "platforms": sorted({PLATFORM_ALIASES.get(n, n)
                                                      for n in _flatten_platforms(args.platform)})}})

    if not os.path.isdir(target):
        return fail("WF_PATH_INVALID", f"目标目录不存在：{target}", args.json)
    if not skill_roots:
        return fail("WF_PATH_INVALID",
                    f"至少需要一个 --platform（技能装在目标项目内）；支持 {sorted(PLATFORMS)}", args.json)
    # F5-2：不在这里建目录——拒绝路径（来源不符、代次非法等）也必须保持目录树不变。
    # 需要时在通过核验后的写入阶段按 root 创建。

    writer_path = join(target, ".wf/writer.json")
    existing = wf_records.load_json(writer_path)
    if existing is not None:
        # 已安装：只允许"追加平台"（同发行引用）；资产与项目数据不动
        return add_platforms(target, args, manifest)

    try:
        handle = wf_lock.acquire(target, holder_hint="dev-deploy")
    except wf_lock.LockBusy as exc:
        return fail("WF_WRITER_BUSY", f"锁被占用：{exc}", args.json)
    except wf_lock.LockMismatch as exc:
        return fail("WF_ASSET_DECISION", f"锁对象异常：{exc}", args.json)
    from wflib import actions as wf_actions
    from wflib import scope as wf_scope

    head_before = wf_scope.head(target)
    try:
        # 锁内重算完整计划：mkdir .wf / writer 初始记录 / 技能根 mkdir / 资产写入之前复核。
        writes, plan_problems = plan_deployment(target, skill_roots, manifest)
        if plan_problems:
            return fail("WF_ASSET_DECISION",
                        "锁内复核发现技能根/资产落点越界：整批拒绝，不写任何文件",
                        args.json, {"problems": plan_problems[:20]})
        os.makedirs(join(target, ".wf"), exist_ok=True)
        operation_id = f"dev-deploy-{uuid.uuid4().hex}"
        writer_record = wf_writer.initial_record()
        writer_record = wf_writer.maintenance_acquire(
            writer_record, operation_id=operation_id, scope={"paths": sorted(
                {entry["target_relative"] for entry in writes}
            )}, preview_digest=wf_records.plain_digest(manifest))
        wf_writer.save(target, writer_record)

        deployed = []
        for root in skill_roots:
            os.makedirs(root, exist_ok=True)
        for entry in writes:
            base = target if entry["root"] == "project" else entry["root"]
            destination = safe_write_target(base, entry["target_relative"])
            source = os.path.join(common.SOURCE_ROOT, *entry["source_path"].split("/"))
            with open(source, "rb") as handle_src:
                content = handle_src.read()
            os.makedirs(os.path.dirname(destination), exist_ok=True)
            if os.path.exists(destination):
                if wf_records.file_digest(destination) != wf_records.file_digest(source):
                    raise RuntimeError(f"target occupied with different content: {destination}")
                deployed.append({"target": destination, "skipped": True})
                continue
            with open(destination, "wb") as handle_dst:
                handle_dst.write(content)
            mode = os.stat(source).st_mode
            os.chmod(destination, mode | 0o755)  # 清单声明 executable:true，须与事实一致
            deployed.append({"target": destination, "digest": wf_records.file_digest(destination)})

        manifest_path = join(target, ".wf/install/release-manifest.json")
        manifest_digest = common.write_manifest(manifest_path, manifest)
        installation = {
            "schema_version": 1,
            "install_id": uuid.uuid4().hex,
            "release_ref": f"dev:{common.git_describe()}",
            "source_commit": common.git_head(),
            # 内容级来源身份（F5-1）：describe --dirty + HEAD 无法区分同一 HEAD 下的两次 dirty 内容，
            # 因此把发行规则摘要一并登记，追加平台按它判同源。
            "rules_digest": manifest["compatibility"]["rules_digest"],
            "version": DEV_VERSION,
            "manifest_digest": manifest_digest,
            "platforms": sorted({PLATFORM_ALIASES.get(n, n) for n in _flatten_platforms(args.platform)}),
            "roots": [root_record(target, root) for root in skill_roots],
            "assets": [
                {"target": (entry["target_relative"] if entry["root"] == "project"
                            else os.path.join(root_record(target, entry["root"]),
                                              *entry["target_relative"].split("/"))),
                 "root_ref": "project" if entry["root"] == "project" else root_record(target, entry["root"]),
                 "digest": entry["digest"], "source_path": entry["source_path"]}
                for entry in writes
            ],
            "decisions": [],
            "installed_at": wf_records.now_str(),
            "tool": "scripts/wf-dev-deploy.py",
        }
        wf_records.write_json(join(target, ".wf/install/installation.json"), installation)
        write_recovery(target, installation)
        gitignore = ensure_gitignore(target)
        problems = self_check(target, manifest, skill_roots, installation)
        receipt_changes = []
        for item in deployed:
            absolute = item["target"]
            if not is_inside(target, absolute):
                continue
            receipt_changes.append({
                "path": os.path.relpath(absolute, os.path.abspath(target)).replace(os.sep, "/"),
                "before": None,
                "after": wf_fingerprint.item(target, os.path.relpath(absolute, os.path.abspath(target))
                                             .replace(os.sep, "/")),
            })
        receipt_changes.append({"path": ".gitignore", "before": None,
                                "after": wf_fingerprint.item(target, ".gitignore")})
        writer_record = wf_writer.load(target)
        receipts = list(writer_record.get("maintenance_results") or [])
        receipts.append({
            "operation": operation_id,
            "preview_digest": wf_records.plain_digest(installation),
            "head_before": head_before,
            "changes": receipt_changes,
            "receipt_git_state": {"head": head_before, "tracked_paths": len(receipt_changes)},
            "result": "applied_pending_commit",
            "disposition": None,
        })
        writer_record = wf_writer.bump(writer_record, maintenance_results=receipts)
        wf_writer.save(target, writer_record)
        # 回执账本写进**提交层**（`.wf/install/maintenance.jsonl`）：writer.json 是运行态，
        # 拿它当持久化证据会让探针永远 pending（实测 r59–r61）
        wf_maintenance.append(target, receipts[-1])
        if problems:
            wf_writer.save(target, wf_writer.bump(writer_record, checkpoint={"phase": "self-check-failed",
                                                                            "problems": problems}))
            return fail("WF_CAPABILITY_UNAVAILABLE", "投放后自检失败，已保留维护检查点",
                        args.json, {"problems": problems})
        released = wf_writer.release(wf_writer.load(target))
        wf_writer.save(target, released)
    finally:
        handle.release()

    message = "\n".join([
        "OK  WF_OK",
        f"目标：{target}",
        f"版本：{DEV_VERSION}  引用：{installation['release_ref']}",
        f"投放：{len([item for item in deployed if not item.get('skipped')])} 个文件"
        f"（跳过 {len([item for item in deployed if item.get('skipped')])} 个已存在且一致的文件）",
        f"清单摘要：{manifest_digest}",
        f"规则摘要：{manifest['compatibility']['rules_digest']}",
        f"托管段：{gitignore.get('action')}",
        f"平台：{json.dumps(sorted({PLATFORM_ALIASES.get(n, n) for n in _flatten_platforms(args.platform)}), ensure_ascii=False)}",
        "下一步：人执行 wf.py confirm-executor --scope system，然后 /wf-start",
    ])
    return emit({"ok": True, "message": message, "installation": installation,
                 "manifest": {"version": manifest["version"],
                              "rules_digest": manifest["compatibility"]["rules_digest"],
                              "manifest_digest": manifest_digest}})


def skill_roots_for(target, platforms):
    roots, _unknown = resolve_skill_roots(target, platforms)
    return roots


def add_platforms(target, args, manifest):
    """已安装项目追加平台（与发行入口 install.py::add_platforms 同语义）。

    2026-11-05 第二轮修正（复审 R1，与 install.py A1 同源）：
    - 新根技能副本登记进 `installation.assets`，否则会落未归属路径挡住开工/Check；
    - 登记维护持有/新代次/回执（写入 `writer.json`），释放时再次递增代次；
    - 目标已存在且内容不同 → 整批报冲突、不写任何文件（不覆盖本地偏离）；
    - 无变化时幂等返回，不取写权、不产生空回执。
    """
    try:
        handle = wf_lock.acquire(target, holder_hint="dev-deploy-platform")
    except wf_lock.LockBusy as exc:
        return fail("WF_WRITER_BUSY", f"锁被占用：{exc}", args.json)
    except wf_lock.LockUnavailable as exc:
        return fail("WF_ASSET_DECISION", f"锁对象不可用：{exc}", args.json)
    try:
        writer_record = wf_writer.load(target)
        try:
            wf_writer.require_supported(writer_record, wf_writer.WriterError)
        except wf_writer.WriterError as exc:
            code = getattr(exc, "code", None) or "WF_RECORD_INVALID"
            detail = getattr(exc, "facts", None) or {"reason": str(exc)}
            return fail(code, f"写权记录不可用于维护写入：{str(exc)}", args.json, detail)
        if writer_record.get("state") != "idle":
            return fail("WF_WRITER_BUSY", "写权非空闲，不能追加平台", args.json,
                        {"holder": writer_record.get("holder")})
        _gen = writer_record.get("generation")
        if not isinstance(_gen, int) or isinstance(_gen, bool):
            return fail("WF_RECORD_INVALID", "写权代次缺失或非整数，不能安全递增", args.json,
                        {"generation": writer_record.get("generation")})
        path = join(target, ".wf/install/installation.json")
        installation = wf_records.load_json(path)
        if installation is None:
            return fail("WF_ASSET_DECISION", "安装记录缺失，不能追加平台", args.json)
        # 2026-11-05 第四轮复审 R4-1：追加平台只允许同一来源。
        # 开发态来源由 git describe + HEAD 固定；源码已变（提交或脏改）即属"不同引用"，
        # 按升级/重装处理，不能把新来源的技能副本混进旧运行时。
        # 同源判据 = 提交身份 + 投放内容摘要；`dev:<describe>[-dirty]` 只是描述性标记，
        # 不参与判定（否则同一 HEAD 下无关文件变脏也会阻断追加平台，F6-2）。
        current_ref = f"dev:{common.git_describe()}"
        current_commit = common.git_head()
        current_rules = manifest["compatibility"]["rules_digest"]
        if (installation.get("source_commit") != current_commit
                or installation.get("rules_digest") != current_rules):
            return fail("WF_ASSET_DECISION",
                        "已安装的开发态来源与当前源码不同：追加平台只允许同来源，请按升级/重装流程处理",
                        args.json,
                        {"installed_ref": installation.get("release_ref"),
                         "installed_commit": installation.get("source_commit"),
                         "installed_rules_digest": installation.get("rules_digest"),
                         "requested_ref": current_ref, "requested_commit": current_commit,
                         "requested_rules_digest": current_rules,
                         "note": "规则摘要按已投放资产的内容计算；同一 HEAD 下的 dirty 内容变化也会体现"})
        # —— 锁内的完整计划：历史根校验 → 重算根/落点 → 再读内容与冲突 ——
        root_problems = validate_registered_roots(target, installation)
        if root_problems:
            return fail("WF_ASSET_DECISION",
                        "安装记录中的技能根域外/不可解析：整批拒绝，不改历史记录、不清理外部对象",
                        args.json, {"problems": root_problems[:20]})
        current = [item for item in installation.get("platforms") or [] if isinstance(item, str)]
        wanted = sorted({PLATFORM_ALIASES.get(n, n) for n in _flatten_platforms(args.platform)})
        added = [name for name in wanted if name not in current]
        roots = list(installation.get("roots") or [])
        rollout_roots = skill_roots_for(target, wanted)
        planned_writes, plan_problems = plan_deployment(target, rollout_roots, manifest)
        if plan_problems:
            return fail("WF_ASSET_DECISION",
                        "追加平台的技能根/资产落点越界或不可解析：整批拒绝，不写任何文件",
                        args.json, {"problems": plan_problems[:20]})
        try:
            new_roots = [root for root in rollout_roots
                         if root_record(target, root) not in roots]
        except ValueError as exc:
            return fail("WF_ASSET_DECISION", str(exc), args.json)
        planned = []
        for entry in planned_writes:
            if entry["root"] == "project":
                continue  # .wf 资产不动
            if entry["root"] not in new_roots:
                continue
            destination = os.path.join(entry["root"], *entry["target_relative"].split("/"))
            source_file = os.path.join(common.SOURCE_ROOT, *entry["source_path"].split("/"))
            with open(source_file, "rb") as src:
                data = src.read()
            planned.append({"root": entry["root"], "entry": entry, "destination": destination,
                            "target_relative": entry["target_relative"], "data": data,
                            "digest": entry.get("digest")})
        conflicts = []
        for item in planned:
            if not os.path.exists(item["destination"]):
                continue
            with open(item["destination"], "rb") as existing_handle:
                if existing_handle.read() != item["data"]:
                    conflicts.append(item["destination"])
        if conflicts:
            return fail("WF_ASSET_DECISION",
                        "目标已存在且内容不同：重复安装不覆盖本地偏离，整批不写；请人逐项决定后重试",
                        args.json, {"paths": conflicts[:20]})
        pending = [item for item in planned if not os.path.exists(item["destination"])]
        registered = {(asset.get("root_ref"), asset.get("target"))
                      for asset in installation.get("assets") or []}
        missing_assets = [item for item in planned
                          if (item["root"], item["target_relative"]) not in registered]
        if not added and not pending and not missing_assets:
            return emit({"ok": True, "message": "\n".join([
                "OK  WF_OK", f"目标：{target}", "新增平台：（无新增）",
                f"现有平台：{json.dumps(current, ensure_ascii=False)}",
                "说明：无任何变化，未取写权、未产生回执。",
            ]), "installation": installation, "noop": True})

        operation_id = f"dev-deploy-platform-{uuid.uuid4().hex}"
        held = wf_writer.acquire(writer_record, kind="maintenance", ident=operation_id,
                                 scope={"operation": operation_id},
                                 checkpoint={"operation": operation_id, "phase": "add-platforms"})
        wf_writer.save(target, held)
        deployed = []
        try:
            for item in pending:
                os.makedirs(os.path.dirname(item["destination"]), exist_ok=True)
                with open(item["destination"], "wb") as out:
                    out.write(item["data"])
                deployed.append(item["destination"])
            installation["platforms"] = sorted(set(current) | set(wanted))
            installation["roots"] = sorted(set(roots) | {
                root_record(target, root) for root in new_roots})
            for item in planned:
                key = (item["root"], item["target_relative"])
                if key in registered:
                    continue
                installation.setdefault("assets", []).append({
                    "target": item["target_relative"], "root_ref": item["root"],
                    "digest": item["digest"], "source_path": item["entry"].get("source_path"),
                })
                registered.add(key)
            wf_records.write_json(path, installation)
        except OSError as exc:
            wf_writer.save(target, wf_writer.release(held))
            raise SystemExit(f"追加平台写入失败：{exc}")
        changed = deployed + [path]
        head_probe = subprocess.run(["git", "rev-parse", "HEAD"], cwd=target,
                                    capture_output=True, text=True, check=False)
        head_before = head_probe.stdout.strip() or None if head_probe.returncode == 0 else None
        receipt = {
            "operation": operation_id,
            "preview_digest": wf_records.plain_digest(installation),
            "head_before": head_before,
            "changes": [{"path": os.path.relpath(item, target).replace(os.sep, "/"),
                         "before": None, "after": wf_records.file_digest(item)} for item in changed],
            "receipt_git_state": {"head": head_before, "tracked_paths": len(changed)},
            "result": "applied_pending_commit",
            "disposition": None,
        }
        updated = wf_writer.release(held)
        updated.setdefault("maintenance_results", []).append(receipt)
        wf_writer.save(target, updated)
    finally:
        handle.release()
    return emit({"ok": True, "message": "\n".join([
        "OK  WF_OK",
        f"目标：{target}",
        f"新增平台：{json.dumps(added, ensure_ascii=False)}"
        + ("（无新增：已安装过这些平台）" if not added else ""),
        f"投放技能副本：{len(deployed)} 个（新根 {len(new_roots)} 个）",
        f"现有平台：{json.dumps(installation['platforms'], ensure_ascii=False)}",
        "说明：.wf 资产未改动；写权回执已登记（applied_pending_commit）。",
    ]), "installation": installation, "receipt": receipt})


def main(argv=None):
    parser = argparse.ArgumentParser(description="wf 开发态部署（authoring 工具）")
    parser.add_argument("--target", required=True, help="目标项目绝对路径")
    parser.add_argument("--platform", action="append", nargs="+", default=[],
                        help="目标项目实际使用的 agent（可重复）：dsh|codex|cursor|geminicli|copilot|claudecode")
    parser.add_argument("--confirm", action="store_true", help="确认预览后执行投放")
    parser.add_argument("--json", action="store_true", help="以 JSON 输出结果")
    args = parser.parse_args(argv)
    if not os.path.isabs(args.target):
        return fail("WF_PATH_INVALID", "--target 必须是绝对路径", args.json)
    return deploy(args)


if __name__ == "__main__":
    raise SystemExit(main())
