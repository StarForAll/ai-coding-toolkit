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
SHARED_SKILL_DIR = _INSTALL.SHARED_SKILL_DIR
# 平台表与"装哪些平台"都只有发行侧一份：开发态部署同样装齐全部平台（2026-11-23 人裁）。
all_platforms = _INSTALL.all_platforms
resolve_skill_roots = _INSTALL.resolve_skill_roots

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
    """展开完整部署计划并整批复核边界；返回 (writes, problems)。

    **与发行安装同一套类别覆盖**：`project_wf`、`skill_root`、`host_hook` 三类都要展开——
    开发态部署此前漏了 `host_hook`，于是"平台已装齐"的项目里 `.codex/hooks*` 根本不存在
    （2026-11-23 十七轮复审 b-1）。
    """
    writes, problems = [], []
    for root in skill_roots:
        problem = boundary_problem(target, root, root)
        if problem:
            problems.append(dict(problem, reason="skill root " + problem["reason"]))
    for asset in manifest["assets"]:
        target_class = asset["target_class"]
        if target_class == "release_only":
            continue
        if target_class == "project_wf" or target_class == "host_hook":
            destination = os.path.join(os.path.abspath(target), *asset["target_relative"].split("/"))
            problem = boundary_problem(target, os.path.abspath(target), destination)
            if problem:
                problems.append(problem)
                continue
            writes.append({"target_relative": asset["target_relative"],
                           "source_path": asset["source_path"], "root": "project",
                           "digest": asset["digest"], "target_class": target_class})
        elif target_class == "skill_root":
            for root in skill_roots:
                destination = os.path.join(root, *asset["target_relative"].split("/"))
                problem = boundary_problem(target, root, destination)
                if problem:
                    problems.append(problem)
                    continue
                writes.append({"target_relative": asset["target_relative"],
                               "source_path": asset["source_path"],
                               "root": root, "digest": asset["digest"],
                               "target_class": target_class})
        else:
            problems.append({"reason": "unknown target_class", "target_class": target_class,
                             "path": asset.get("target_relative")})
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
    skill_roots = resolve_skill_roots(target)
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
        lines.append(f"平台：{json.dumps(all_platforms(), ensure_ascii=False)}（全部支持平台，一次装齐）")
        lines.append(f"技能目录（目标项目内）：{json.dumps([os.path.relpath(root, target) for root in skill_roots], ensure_ascii=False)}")
        if clues:
            lines.append("Trellis 线索（人确认后可继续安装，但本会话不得混跑两套流程）：")
            for clue in clues:
                lines.append(f"  - {clue['path']} ({clue['kind']})")
        lines.append("确认后重跑并加 --confirm。")
        return emit({"ok": True, "message": "\n".join(lines),
                     "preview": {"target": target, "files": writes, "clues": clues,
                                 "platforms": all_platforms()}})

    if not os.path.isdir(target):
        return fail("WF_PATH_INVALID", f"目标目录不存在：{target}", args.json)

    # F5-2：不在这里建目录——拒绝路径（来源不符、代次非法等）也必须保持目录树不变。
    # 需要时在通过核验后的写入阶段按 root 创建。

    writer_path = join(target, ".wf/writer.json")
    if os.path.exists(join(target, ".wf/install/installation.json")):
        # 已安装：开发态部署没有"追加平台"这一步（安装面向全部平台），只做补齐/核对：
        # 落点与本次源一致 ⇒ 幂等成功；有差异 ⇒ 提示走升级（不覆盖本地改动）。
        return verify_installed(target, args, manifest, skill_roots)

    try:
        handle = wf_lock.acquire(target, holder_hint="dev-deploy")
    except wf_lock.LockBusy as exc:
        return fail("WF_WRITER_BUSY", f"锁被占用：{exc}", args.json)
    except wf_lock.LockMismatch as exc:
        return fail("WF_ASSET_DECISION", f"锁对象异常：{exc}", args.json)
    from wflib import actions as wf_actions
    from wflib import scope as wf_scope

    head_before = wf_scope.head(target)
    hook_plans, hook_problems = _INSTALL.plan_host_hooks(target, manifest, None)
    if hook_problems:
        return fail("WF_ASSET_DECISION",
                    "hooks.json 条目需人裁决：不覆盖用户改过的命令串（未写入任何文件）",
                    args.json, {"problems": hook_problems})
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

        for plan in hook_plans:
            plan["applied"] = _INSTALL.apply_hooks_json(target, plan)

        manifest_path = join(target, ".wf/install/release-manifest.json")
        manifest_digest = common.write_manifest(manifest_path, manifest)
        installation = {
            "schema_version": 1,
            "install_id": uuid.uuid4().hex,
            "release_ref": f"dev:{common.git_describe()}",
            "source_commit": common.git_head(),
            # 内容级来源身份（F5-1）：describe --dirty + HEAD 无法区分同一 HEAD 下的两次 dirty 内容，
            # 因此把发行规则摘要一并登记，重跑核对按它判同源。
            "rules_digest": manifest["compatibility"]["rules_digest"],
            "version": DEV_VERSION,
            "manifest_digest": manifest_digest,
            "platforms": all_platforms(),
            "roots": [root_record(target, root) for root in skill_roots],
            # `target` 一律是**资产相对路径**，根由 `root_ref` 表达——此前非项目根把根拼进
            # target，升级再拼一次 root_ref，26 份技能副本被认成"新增撞用户文件"
            # （2026-11-23 十七轮复审 b-2）。
            "assets": [
                {"target": entry["target_relative"],
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
                "after": wf_records.file_digest(absolute),
            })
        receipt_changes.append({"path": ".gitignore", "before": None,
                                "after": wf_records.file_digest(os.path.join(target, ".gitignore"))})
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
        _INSTALL.record_host_hooks(installation, manifest, hook_plans, target)
        wf_records.write_json(join(target, ".wf/install/installation.json"), installation)
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
        f"平台：{json.dumps(all_platforms(), ensure_ascii=False)}（全部支持平台已装）",
        "下一步：人执行 wf.py confirm-executor --scope system，然后 /wf-start",
    ])
    return emit({"ok": True, "message": message, "installation": installation,
                 "manifest": {"version": manifest["version"],
                              "rules_digest": manifest["compatibility"]["rules_digest"],
                              "manifest_digest": manifest_digest}})


def verify_installed(target, args, manifest, skill_roots):
    """已部署项目重跑：**委托发行侧实现**（同一份补齐/核对语义，不在这里再写一套）。

    开发态部署与发行安装的差异只在"来源身份"（`dev:<describe>` + 提交）；来源一致时把
    记录/落点/回执的判定整个交给 `install.py::verify_installed`——否则两套实现必然分叉
    （十七轮 b-4 的"平台清单不刷新"就是分叉的结果）。
    """
    import argparse

    installation_path = join(target, ".wf/install/installation.json")
    installation = wf_records.load_json(installation_path) if os.path.exists(installation_path) else None
    if not isinstance(installation, dict):
        return fail("WF_RECORD_INVALID",
                    "已部署（存在写权记录）但没有可读安装记录：请用 repair 核对，或删除现场重新部署",
                    args.json, {"installation": installation_path})
    writer_record = wf_records.load_json(join(target, ".wf/writer.json"))
    writer_problem = _INSTALL._writer_problem(writer_record)
    if writer_problem:
        return fail("WF_RECORD_INVALID", "写权记录不合法：先修复记录再部署",
                    args.json, {"problems": [writer_problem]})
    current_ref = f"dev:{common.git_describe()}"
    recorded_ref = str(installation.get("release_ref") or "")
    current_commit = common.git_head()
    recorded_commit = installation.get("source_commit")
    if recorded_ref and recorded_ref != current_ref:
        return fail("WF_ASSET_DECISION",
                    "目标由另一个来源部署：不同来源不混装（重跑只核对同一来源）",
                    args.json, {"installed_ref": recorded_ref, "current_ref": current_ref})
    if recorded_commit and current_commit and recorded_commit != current_commit:
        return fail("WF_ASSET_DECISION",
                    "目标部署自另一个提交：重跑只核对同一提交（换内容请按升级/重新部署处理）",
                    args.json, {"installed_commit": recorded_commit,
                                "current_commit": current_commit})
    shim = argparse.Namespace(target=target, source=common.SOURCE_ROOT,
                              json=bool(args.json), confirm=True)
    return _INSTALL.verify_installed(shim, manifest, skill_roots)


def main(argv=None):
    parser = argparse.ArgumentParser(description="wf 开发态部署（authoring 工具）")
    parser.add_argument("--target", required=True, help="目标项目绝对路径")
    parser.add_argument("--confirm", action="store_true", help="确认预览后执行投放")
    parser.add_argument("--json", action="store_true", help="以 JSON 输出结果")
    args = parser.parse_args(argv)
    if not os.path.isabs(args.target):
        return fail("WF_PATH_INVALID", "--target 必须是绝对路径", args.json)
    return deploy(args)


if __name__ == "__main__":
    raise SystemExit(main())
