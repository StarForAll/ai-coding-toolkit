"""fingerprint.py — 指纹项、内容摘要与检查锚点（机制稿 §3.2）。"""

from __future__ import annotations

import os
import stat

from . import records
from .paths import join


def item(root, rel: str) -> dict:
    """单项指纹：{path, exists, kind, executable, digest}。"""
    target = join(root, rel)
    try:
        info = os.lstat(target)
    except FileNotFoundError:
        return {"path": rel, "exists": False, "kind": "deleted", "executable": False, "digest": None}
    except OSError as exc:
        raise records.RecordInvalid(f"cannot stat {rel}: {exc}") from exc
    if stat.S_ISLNK(info.st_mode):
        target_value = os.readlink(target)
        digest = "sha256:" + records.sha256_hex(target_value.encode("utf-8"))
        return {"path": rel, "exists": True, "kind": "symlink", "executable": False, "digest": digest}
    if not stat.S_ISREG(info.st_mode):
        raise records.RecordInvalid(f"unsupported file type (cannot verify): {rel}")
    return {
        "path": rel,
        "exists": True,
        "kind": "file",
        "executable": bool(info.st_mode & (stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)),
        "digest": records.file_digest(target),
    }


def items(root, rels) -> list:
    """按路径去重排序的指纹集合。"""
    return [item(root, rel) for rel in sorted(set(rels), key=lambda value: value.encode("utf-8"))]


def content_digest(fingerprints) -> str:
    ordered = sorted(fingerprints, key=lambda entry: entry["path"].encode("utf-8"))
    return records.H("wf-content-v1", ordered)


def paths_digest(rels) -> str:
    ordered = sorted(set(rels), key=lambda value: value.encode("utf-8"))
    return records.H("wf-check-paths-v1", ordered)


def touch_paths_digest(patterns) -> str:
    ordered = sorted(set(patterns), key=lambda value: value.encode("utf-8"))
    return records.H("wf-check-paths-v1", ordered)


def acceptance_digest(acceptance) -> str:
    return records.H("wf-acceptance-v1", acceptance)


def verifications_digest(verifications) -> str:
    """验证声明的内容身份（唯一实现）：id / invocation / cwd / input_refs / required / consume_at。

    消费点：机械修订的等价核验（同一批验证命令是否真没变）与 TDD 红绿配对
    （历史红运行是否属于**同一个**验证定义）。
    """
    return records.H("wf-verifications-v1", list(verifications or []))


def verification_digest(verification) -> str:
    """单条验证声明的身份（红绿配对的第二端：同 id 但改了 argv 不算同一定义）。"""
    entry = verification if isinstance(verification, dict) else {}
    return records.H("wf-verification-v1", {
        "id": entry.get("id"),
        "invocation": entry.get("invocation"),
        "cwd": entry.get("cwd") or ".",
        "input_refs": list(entry.get("input_refs") or []),
        "required": bool(entry.get("required", True)),
        "consume_at": entry.get("consume_at"),
    })


def snapshot_digest(snapshot):
    return records.plain_digest(snapshot)


def check_anchor(parts: dict) -> str:
    """十一键锚点；键名与顺序取机制稿 §3.2（C 排序后逐键进入哈希）。

    W2-2（三轮裁决③）：新增常开键 control_plane_digest（vendor 脏路径集合的内容
    指纹，v 桶空时为常量摘要）——既有 Check 因新增锚点输入一次性全量失效，升级后
    需重跑 Check（WF_CHECK_STALE 既有语义）。
    """
    keys = [
        "plan_version",
        "entry_snapshot_digest",
        "touch_paths_digest",
        "paths_digest",
        "content_digest",
        "acceptance_digest",
        "spec_versions",
        "baseline_digest",
        "config_digest",
        "workflow_snapshot_digest",
        "control_plane_digest",
    ]
    payload = {key: parts.get(key) for key in keys}
    return records.H("wf-check-anchor-v1", payload)


def control_plane_digest(v_paths, root):
    """控制面非交付维度事实（W2-2）：vendor 脏路径集合的内容指纹。

    键值恒非 None：v 桶空 ⇒ 常量摘要（空集合的哈希），vendor 内容变化即改变。
    逐路径 file_digest_state 归因（digest/cause/reason 原样入摘要——读取归因是
    锚点事实，不折 None）；v 桶唯一来源是 scope.classify_candidates(...)["buckets"]["v"]
    （与 vendor_dirty facts 同源单一实现）。
    """
    entries = {}
    for path in sorted(v_paths or []):
        digest, cause, reason = records.file_digest_state(join(root, path))
        entries[path] = {"digest": digest, "cause": cause, "reason": reason}
    return records.H("wf-control-plane-v1", entries)


def anchor_rule_version(rules_digest: str, installed_assets) -> str:
    ordered = sorted(
        installed_assets,
        key=lambda entry: (entry.get("root_ref", "").encode("utf-8"), entry.get("target_relative", "").encode("utf-8")),
    )
    deduped = []
    seen = set()
    for entry in ordered:
        key = (entry.get("root_ref"), entry.get("target_relative"))
        if key in seen:
            continue
        seen.add(key)
        deduped.append(entry)
    return records.H("wf-effective-rules-v1", {"rules_digest": rules_digest, "installed_assets": deduped})
