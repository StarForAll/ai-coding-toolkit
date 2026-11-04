#!/usr/bin/env python3
"""uninstall.py — 独立卸载入口（实现稿 §3.3、§4.5.1；机制稿 §10.5）。

单文件、仅标准库、**不导入 wflib**。默认卸载只移除精确登记的发行资产与托管段，
保留项目数据、安装记录与 `/.wf-lock` 忽略行；`--purge` 属第三轮。
"""

from __future__ import annotations

import argparse
import datetime
import fcntl
import hashlib
import json
import os
import secrets
import sys

LOCK_MARK = b"wf-lock-v1\n"


def canonical(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def digest_of(obj):
    return "sha256:" + hashlib.sha256(canonical(obj).encode("utf-8")).hexdigest()


def file_digest(path):
    try:
        with open(path, "rb") as handle:
            return "sha256:" + hashlib.sha256(handle.read()).hexdigest()
    except FileNotFoundError:
        return None


def now_str():
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


# --- 预览令牌（与 repair.py 逐字一致；由 build-wf-release.py --verify-token-parity 比对） ---


class PreviewToken:
    """预览令牌（机制稿 §10.3）：随机 128 位 nonce，仅本次预览有效。

    令牌只绑定「本次预览摘要 + 本次过程」；重新预览即销毁旧 nonce，跨会话不恢复许可。
    真正的漂移防护在应用路径：确认后**在同一把锁内**重算预览并比对摘要。
    """

    def __init__(self):
        self._nonce = None
        self._digest = None

    def issue(self, preview, nonce=None):
        self._digest = digest_of(preview)
        self._nonce = nonce or secrets.token_hex(16)
        return self._nonce

    def confirm(self, supplied):
        if self._nonce is None or self._digest is None:
            return False
        return secrets.compare_digest(str(supplied), self._nonce)

    def digest(self):
        return self._digest

    def invalidate(self):
        self._nonce = None
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
    sys.stdout.write(f"nonce={issued}\n")
    sys.stdout.write(f"digest={digest_of(PARITY_PREVIEW)}\n")
    sys.stdout.write(f"first={'ok' if first else 'reject'}\n")
    sys.stdout.write(f"after={'expired' if not after else 'accepted'}\n")
    return 0


def _proc_start(pid):
    """只读 /proc 取进程启动时刻（第 22 字段）。"""
    try:
        with open(f"/proc/{int(pid)}/stat", "r", encoding="utf-8") as handle:
            fields = handle.read().split()
    except (OSError, ValueError):
        return None
    return fields[21] if len(fields) > 21 else None


def _live_holder(path):
    """锁文件里登记的持锁者是否仍是同一进程；无登记返回 None。"""
    try:
        with open(path, "r", encoding="utf-8") as handle:
            text = handle.read()
    except OSError:
        return None
    body = text.split("\n", 1)[1] if "\n" in text else ""
    if not body.startswith("holder "):
        return None
    fields = dict(token.split("=", 1) for token in body.strip().split() if "=" in token)
    pid = fields.get("pid")
    if not pid:
        return None
    actual = _proc_start(pid)
    if actual is None:
        return {"pid": pid, "alive": False, "reason": "holder process not running"}
    if fields.get("start") not in (None, "unknown", actual):
        return {"pid": pid, "alive": False, "reason": "pid reused by another process"}
    return {"pid": pid, "alive": True, "start": actual}


class Lock:
    """最小互斥：与 wf.py 同一锁对象语义（排他创建、未知内容不认领）。"""

    def __init__(self, root):
        self.path = os.path.join(os.path.abspath(root), ".wf-lock")
        self.fd = None

    def __enter__(self):
        created = False
        try:
            self.fd = os.open(self.path, os.O_RDWR | os.O_CREAT | os.O_EXCL, 0o644)
            created = True
        except FileExistsError:
            try:
                self.fd = os.open(self.path, os.O_RDWR)
            except OSError as exc:
                raise RuntimeError(f"cannot open lock: {exc}") from exc
        except OSError as exc:
            raise RuntimeError(f"cannot open lock: {exc}") from exc
        try:
            fcntl.flock(self.fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            os.close(self.fd)
            self.fd = None
            raise RuntimeError(f"lock busy: {exc}") from exc
        content = os.pread(self.fd, len(LOCK_MARK) + 1, 0)
        if created:
            if content:
                self._abandon("lock object appeared during exclusive creation")
            os.pwrite(self.fd, LOCK_MARK, 0)
            os.fsync(self.fd)
        elif not content.startswith(LOCK_MARK):
            # 既有空锁文件属初始化未完成、未知内容属不可识别：交人核实，不认领
            self._abandon("lock mark empty or unknown (initialization unfinished)")
        return self

    def _abandon(self, reason):
        fcntl.flock(self.fd, fcntl.LOCK_UN)
        os.close(self.fd)
        self.fd = None
        raise ValueError(reason)

    def __exit__(self, exc_type, exc, tb):
        if self.fd is not None:
            try:
                fcntl.flock(self.fd, fcntl.LOCK_UN)
            finally:
                os.close(self.fd)
        return False


def read_json(path):
    try:
        with open(path, "r", encoding="utf-8") as handle:
            return json.load(handle)
    except FileNotFoundError:
        return None
    except ValueError:
        return {"__invalid__": True}


def write_json(path, value):
    tmp = path + ".wf-tmp"
    with open(tmp, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(tmp, path)


def blocker(code, message, facts=None, json_mode=False):
    payload = {"ok": False, "code": code, "next": message, "facts": facts or {}}
    if json_mode:
        sys.stdout.write(json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n")
    else:
        sys.stdout.write(f"BLOCKED  {code}\n{message}\n")
        if facts:
            sys.stdout.write("事实: " + json.dumps(facts, ensure_ascii=False, sort_keys=True) + "\n")
    return 1


def ok(message, facts=None, json_mode=False):
    if json_mode:
        sys.stdout.write(json.dumps({"ok": True, "code": "WF_OK", "message": message, "facts": facts or {}},
                                    ensure_ascii=False, sort_keys=True) + "\n")
    else:
        sys.stdout.write(message + "\n")
    return 0


def resolve(root, relative):
    return os.path.join(os.path.abspath(root), *relative.split("/"))


# release_only 只存在于发行树、不落目标项目：出现在待删集合里属清单异常之外的正常登记
ASSET_CLASSES = ("project_wf", "skill_root")
NON_DEPLOYED_CLASSES = ("release_only",)


class AssetBoundary(Exception):
    """清单登记的资产越界或不可解释：整批拒绝（设计稿 §7.3）。"""

    def __init__(self, problems):
        super().__init__("asset boundary rejected")
        self.problems = problems


def _safe_relative(relative):
    """清单里的目标必须是仓库相对路径：无绝对、无 ..、无空段（设计稿 §7.3）。"""
    if not isinstance(relative, str) or not relative:
        return False
    if relative.startswith("/") or "\\" in relative or ":" in relative.split("/")[0]:
        return False
    for part in relative.split("/"):
        if part in ("", ".", ".."):
            return False
    return True


def _inside(base, path):
    base_real = os.path.realpath(base)
    path_real = os.path.realpath(path)
    return path_real == base_real or path_real.startswith(base_real + os.sep)


def collect_targets(root, installation, manifest):
    """按清单精确登记返回 (project 路径, skill 根路径) 两组；任一越界条目不解释直接拒绝。"""
    project = []
    skills = []
    problems = []
    roots = installation.get("roots") or []
    project_root = os.path.abspath(root)
    for asset in manifest.get("assets") or []:
        if not isinstance(asset, dict):
            problems.append({"reason": "asset entry is not an object"})
            continue
        target_class = asset.get("target_class")
        relative = asset.get("target_relative")
        if target_class in NON_DEPLOYED_CLASSES:
            continue  # 发行侧资产，目标项目无对应落点
        if target_class not in ASSET_CLASSES:
            problems.append({"reason": "unknown asset class", "target_class": target_class})
            continue
        if not _safe_relative(relative):
            problems.append({"reason": "asset path is not a safe relative path", "path": relative})
            continue
        if target_class == "project_wf":
            resolved = resolve(project_root, relative)
            if not _inside(project_root, resolved):
                problems.append({"reason": "asset resolves outside the project root", "path": relative})
                continue
            project.append(relative)
        else:
            for root_ref in roots:
                if not isinstance(root_ref, str) or not root_ref:
                    problems.append({"reason": "skill root reference invalid", "root": root_ref})
                    continue
                base = root_ref if os.path.isabs(root_ref) else os.path.join(project_root, root_ref)
                candidate = os.path.join(base, *relative.split("/"))
                if not _inside(base, candidate):
                    problems.append({"reason": "asset resolves outside its skill root",
                                     "path": relative, "root": root_ref})
                    continue
                skills.append(candidate)
    if problems:
        raise AssetBoundary(problems)
    return sorted(set(project)), sorted(set(skills))


def managed_bounds(manifest, text):
    managed = manifest.get("gitignore_managed") or {}
    begin = managed.get("begin_marker", "# wf-managed-v1")
    end = managed.get("end_marker", "# wf-managed-end")
    lines = text.splitlines()
    if begin not in lines or end not in lines:
        return None
    return lines.index(begin), lines.index(end)


def main(argv=None):
    parser = argparse.ArgumentParser(description="wf 独立卸载（默认保留数据）")
    parser.add_argument("--project", required=False)
    parser.add_argument("--purge", action="store_true")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--nonce", default=None, help="仅测试形态：注入固定 nonce")
    parser.add_argument("--token-parity-check", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    if args.token_parity_check:
        return token_parity_check(args.nonce)
    root = args.project or os.environ.get("WF_PROJECT_ROOT")
    if not root or not os.path.isabs(root) or not os.path.isdir(root):
        return blocker("WF_PATH_INVALID", "必须用 --project <绝对路径> 显式给目标", {"project": root}, args.json)
    if args.purge:
        return blocker("WF_CAPABILITY_UNAVAILABLE",
                       "purge 属第三轮交付；当前只做开发态退出（保留数据）",
                       {"round": 3, "capability": "uninstall --purge (D37)"}, args.json)

    installation = read_json(os.path.join(root, ".wf/install/installation.json"))
    if not isinstance(installation, dict) or "__invalid__" in installation:
        return blocker("WF_ASSET_DECISION", "安装记录缺失或不可解析：不按目录形状猜删", {"target": root}, args.json)
    manifest_path = os.path.join(root, ".wf/install/release-manifest.json")
    manifest = read_json(manifest_path)
    if not isinstance(manifest, dict) or "__invalid__" in manifest:
        return blocker("WF_ASSET_DECISION", "运行期清单缺失或不可解析：不猜删", {"target": root}, args.json)
    # 清单须与安装登记一致：独立入口自带一次核对，不依赖运行时兜底（设计稿 §7.2）
    recorded = installation.get("manifest_digest")
    actual = file_digest(manifest_path)
    if not isinstance(recorded, str) or not recorded:
        # 缺少摘要就没有"该清单确为本机安装清单"的依据：不猜所有权，直接阻断
        return blocker("WF_ASSET_DECISION", "安装记录缺少清单摘要：无法确认清单归属，不删除任何资产",
                       {"recorded": recorded, "manifest": manifest_path}, args.json)
    if recorded != actual:
        return blocker("WF_ASSET_DECISION", "清单摘要与安装登记不一致：不按被改动的清单删",
                       {"recorded": recorded, "actual": actual}, args.json)

    try:
        project_targets, skill_targets = collect_targets(root, installation, manifest)
    except AssetBoundary as exc:
        return blocker("WF_ASSET_DECISION", "清单登记的资产越界或不可解释：整批拒绝，不删任何文件",
                       {"problems": exc.problems}, args.json)
    expected = {}
    for asset in manifest.get("assets") or []:
        target_class = asset.get("target_class")
        if target_class == "project_wf":
            expected[asset["target_relative"]] = asset.get("digest")
        elif target_class == "skill_root":
            for root_ref in installation.get("roots") or []:
                base = root_ref if os.path.isabs(root_ref) else os.path.join(os.path.abspath(root), root_ref)
                expected[os.path.join(base, *asset["target_relative"].split("/"))] = asset.get("digest")
    existing_project = [rel for rel in project_targets if os.path.exists(resolve(root, rel))]
    existing_skills = [path for path in skill_targets if os.path.exists(path)]
    deviations = []
    for rel in existing_project:
        path = resolve(root, rel)
        if expected.get(rel) and file_digest(path) != expected[rel]:
            deviations.append({"path": rel, "reason": "local content differs from release"})
    for path in existing_skills:
        if expected.get(path) and file_digest(path) != expected[path]:
            deviations.append({"path": path, "reason": "local content differs from release"})
    registered = set(existing_project) | set(existing_skills)
    unknown = []
    for directory in {os.path.dirname(item) for item in list(registered) if not os.path.isabs(item)}:
        absolute = resolve(root, directory) if directory else os.path.abspath(root)
        if not os.path.isdir(absolute):
            continue
        for name in sorted(os.listdir(absolute)):
            candidate = os.path.join(directory, name) if directory else name
            if candidate not in registered and os.path.isfile(resolve(root, candidate)):
                unknown.append(candidate)
    gitignore_path = os.path.join(os.path.abspath(root), ".gitignore")
    gitignore_text = ""
    if os.path.isfile(gitignore_path):
        with open(gitignore_path, "r", encoding="utf-8") as handle:
            gitignore_text = handle.read()
    bounds = managed_bounds(manifest, gitignore_text)

    preview_digests = {}
    for rel in existing_project:
        preview_digests[rel] = file_digest(resolve(root, rel))
    for path in existing_skills:
        preview_digests[path] = file_digest(path)

    preview = {
        "operation": "uninstall",
        "target_root": os.path.abspath(root),
        "release_identity": {"release_ref": installation.get("release_ref"),
                             "version": installation.get("version"),
                             "manifest_digest": installation.get("manifest_digest")},
        "selected_paths": existing_project + existing_skills,
        "deviations": deviations,
        "unknown_files": sorted(unknown),
        "intended_after": "移除与发行一致的登记资产与托管段；本地偏离与未知文件默认保留并逐项报告",
        "writer_observation": (read_json(os.path.join(root, ".wf/writer.json")) or {}).get("state"),
        "gitignore_segment": "present" if bounds else "absent",
        "lock_retained": os.path.exists(os.path.join(os.path.abspath(root), ".wf-lock")),
    }
    token = PreviewToken()
    issued = token.issue(preview, nonce=args.nonce)
    lines = [
        "wf 卸载预览（未写入任何文件）",
        f"目标：{os.path.abspath(root)}",
        f"发行：{installation.get('release_ref')} / {installation.get('version')}",
        f"将移除的 .wf/ 资产：{len(existing_project) - len([d for d in deviations if not os.path.isabs(d['path'])])} 个",
        f"将移除的 skill 副本：{len(existing_skills) - len([d for d in deviations if os.path.isabs(d['path'])])} 个",
        f"本地偏离（默认保留，不删除）：{len(deviations)} 项",
        *[f"  - {item['path']}（{item['reason']}）" for item in deviations[:20]],
        f"同目录未知文件（不认领、不删除）：{len(unknown)} 项",
        *[f"  - {item}" for item in sorted(unknown)[:20]],
        f"托管段：{'将移除（保留 /.wf-lock 裸行）' if bounds else '不存在'}",
        "保留：.wf/ 项目数据、.wf/install/、.wf-lock、/.wf-lock 忽略行",
    f"预览摘要：{token.digest()}",
    f"令牌：{issued}",    ]
    sys.stdout.write("\n".join(lines) + "\n")
    sys.stdout.flush()
    if not args.apply:
        sys.stdout.write("确认无 wf 进程后，在同一终端加 --apply 重跑并输入令牌。\n")
        sys.stdout.flush()
        return ok("", {"preview": preview, "token_digest": token.digest()}, args.json)
    sys.stdout.write("请输入令牌确认：")
    sys.stdout.flush()
    supplied = sys.stdin.readline().strip() if sys.stdin else ""
    if not token.confirm(supplied):
        return blocker("WF_PREVIEW_STALE", "令牌不匹配或预览已失效（需在同一进程重新预览）", {}, args.json)

    try:
        with Lock(root):
            # 消费存活探测：登记的持锁者仍活着就不能清空写权（人工确认不能替代存活事实）
            live = _live_holder(os.path.join(root, ".wf-lock"))
            if live and live.get("alive"):
                return blocker("WF_WRITER_BUSY",
                               "旧写者进程仍存活：停止该会话后重新预览",
                               {"holder": live}, args.json)
            # 确认后在同一把锁内复核预览事实：选中集合或写者状态变了即失效（机制稿 §10.3）
            now_project = [rel for rel in project_targets if os.path.exists(resolve(root, rel))]
            now_skills = [path for path in skill_targets if os.path.exists(path)]
            now_writer = (read_json(os.path.join(root, ".wf/writer.json")) or {}).get("state")
            if sorted(now_project + now_skills) != sorted(preview["selected_paths"]) \
                    or now_writer != preview["writer_observation"]:
                return blocker("WF_PREVIEW_STALE",
                               "预览已失效：确认后资产集合或写者状态与预览不一致，请重新预览",
                               {"preview_selected": len(preview["selected_paths"]),
                                "current_selected": len(now_project + now_skills),
                                "preview_writer": preview["writer_observation"],
                                "current_writer": now_writer},
                               args.json)
            # 内容也要重核：删除/保留的判断基于预览时的指纹，确认期间被改动就不能按旧计划删
            now_expected = {}
            for asset in manifest.get("assets") or []:
                target_class = asset.get("target_class")
                if target_class == "project_wf":
                    now_expected[asset["target_relative"]] = asset.get("digest")
                elif target_class == "skill_root":
                    for root_ref in installation.get("roots") or []:
                        base = root_ref if os.path.isabs(root_ref) else os.path.join(os.path.abspath(root), root_ref)
                        now_expected[os.path.join(base, *asset["target_relative"].split("/"))] = asset.get("digest")
            changed = []
            for rel in now_project + now_skills:
                path = resolve(root, rel) if not os.path.isabs(rel) else rel
                if not os.path.exists(path):
                    continue
                # 只判「确认期间是否变过」：拿预览时的指纹比，不拿发行摘要（否则既有偏离会被误判）
                if preview_digests.get(rel) != file_digest(path):
                    changed.append({"path": rel, "reason": "content changed after preview"})
            gitignore_now = ""
            gitignore_path = os.path.join(os.path.abspath(root), ".gitignore")
            if os.path.isfile(gitignore_path):
                with open(gitignore_path, "r", encoding="utf-8") as handle:
                    gitignore_now = handle.read()
            if changed or gitignore_now != gitignore_text:
                return blocker("WF_PREVIEW_STALE",
                               "预览已失效：确认后文件内容或 .gitignore 与预览不一致，请重新预览",
                               {"changed_content": changed,
                                "gitignore_changed": gitignore_now != gitignore_text},
                               args.json)
            writer = read_json(os.path.join(root, ".wf/writer.json"))
            if isinstance(writer, dict) and writer.get("state") in ("held", "recovering"):
                return blocker("WF_WRITER_BUSY", "写权仍被持有：先确认旧写者停止并走 repair，或等其释放",
                               {"holder": writer.get("holder")}, args.json)
            removed = []
            preserved = []
            deviating = {item["path"] for item in deviations}
            for rel in existing_project:
                if rel in deviating:
                    preserved.append({"path": rel, "reason": "local deviation"})
                    continue
                path = resolve(root, rel)
                expected_digest = file_digest(path)
                os.remove(path)
                removed.append({"path": rel, "digest": expected_digest})
            for path in existing_skills:
                if path in deviating:
                    preserved.append({"path": path, "reason": "local deviation"})
                    continue
                digest = file_digest(path)
                os.remove(path)
                try:
                    os.rmdir(os.path.dirname(path))
                except OSError:
                    pass
                removed.append({"path": path, "digest": digest})
            # 托管段：移除整段，保留 /.wf-lock 裸行
            if bounds:
                lines = gitignore_text.splitlines()
                start, end = bounds
                kept = lines[:start] + lines[end + 1:]
                has_bare = any(line.strip() == "/.wf-lock" for line in kept)
                if not has_bare:
                    kept.insert(start, "/.wf-lock")
                with open(gitignore_path, "w", encoding="utf-8", newline="\n") as handle:
                    handle.write("\n".join(kept).rstrip("\n") + "\n")
            # 空目录清理（只清空目录，不删数据）
            for rel in sorted({os.path.dirname(item) for item in existing_project}, key=len, reverse=True):
                directory = resolve(root, rel) if rel else None
                if directory and os.path.isdir(directory) and not os.listdir(directory):
                    try:
                        os.rmdir(directory)
                    except OSError:
                        pass
            note_path = os.path.join(root, ".wf/install/recovery.md")
            if os.path.isfile(note_path):
                with open(note_path, "a", encoding="utf-8") as handle:
                    handle.write(f"\n\n卸载记录：{now_str()} 已移除 {len(removed)} 个发行资产；"
                                 "数据、安装记录与锁保留。\n")
    except RuntimeError as exc:
        return blocker("WF_WRITER_BUSY", str(exc), {"target": root}, args.json)
    except ValueError as exc:
        return blocker("WF_CAPABILITY_UNAVAILABLE", f"锁对象异常：{exc}（人工核实后删除该文件再重试）",
                       {"target": root, "lock": os.path.join(os.path.abspath(root), ".wf-lock")}, args.json)

    message = "\n".join([
        "OK  WF_OK",
        f"已移除发行资产：{len(removed)} 个",
        f"保留本地偏离：{len(preserved)} 项（逐项见报告；如需删除请先备份后手工处理）",
        "已保留：.wf/ 项目数据、.wf/install/、.wf-lock",
        "已保留 .gitignore 中的 /.wf-lock 裸行（段外）",
        "已列出但未认领：同目录未知文件（不删除、不改名）",
        "人工清理顺序：确认无 wf 进程 → 删除 .wf-lock → 移除 /.wf-lock 忽略行",
    ])
    return ok(message, {"removed": removed, "preserved": preserved,
                        "unknown_files": sorted(unknown), "lock_retained": True}, args.json)


if __name__ == "__main__":
    raise SystemExit(main())
