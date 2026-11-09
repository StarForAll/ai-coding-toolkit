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


def snapshot_digest(snapshot):
    return records.plain_digest(snapshot)


def check_anchor(parts: dict) -> str:
    """十键锚点；键名与顺序取机制稿 §3.2（C 排序后逐键进入哈希）。"""
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
    ]
    payload = {key: parts.get(key) for key in keys}
    return records.H("wf-check-anchor-v1", payload)


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
