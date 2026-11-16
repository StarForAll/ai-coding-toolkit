#!/usr/bin/env python3
"""host_snapshot.py — 只读目录树清单：宿主保护的**终态**证据。

为什么不是 mtime/inode：目录顶层元数据不变并不证明子树没变（深层文件改写后把顶层
mtime 恢复即可）。本模块给每个条目记录相对路径、类型、权限、regular 文件字节摘要与
符号链接目标；不跟随链接到树外，不把文件内容写进报告，也不比较读取引起的 atime。

契约：

- 缺失（missing）、空目录（present + 0 entries）与正常目录是不同状态；
- 任何读取失败都是“未验证”并抛 `SnapshotError`，不折成空集合；
- `compare()` 返回 added/removed/modified 与状态变化，路径按字典序，便于逐项报告；
- 不跟随 symlink 目录（避免把树外内容纳入清单或触发越界读取）。

CLI：

    host_snapshot.py capture <root> <out.json>
    host_snapshot.py check <root> --expect <before.json>
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import stat
import sys
import tempfile


class SnapshotError(Exception):
    """清单不可完整读取：这是“未验证”，不是“没有变化”。"""


def _file_digest(path):
    digest = hashlib.sha256()
    total = 0
    try:
        with open(path, "rb") as handle:
            for chunk in iter(lambda: handle.read(1 << 20), b""):
                total += len(chunk)
                digest.update(chunk)
    except OSError as exc:
        raise SnapshotError(f"cannot read {path}: {exc}") from exc
    return "sha256:" + digest.hexdigest(), total


def _entry(path, relative, seen):
    try:
        info = os.lstat(path)
    except OSError as exc:
        raise SnapshotError(f"cannot stat {path}: {exc}") from exc
    mode = stat.S_IMODE(info.st_mode)
    if stat.S_ISLNK(info.st_mode):
        try:
            target = os.readlink(path)
        except OSError as exc:
            raise SnapshotError(f"cannot read link {path}: {exc}") from exc
        return {"type": "symlink", "mode": mode, "target": target}
    if stat.S_ISDIR(info.st_mode):
        return {"type": "dir", "mode": mode}
    if stat.S_ISREG(info.st_mode):
        digest, size = _file_digest(path)
        return {"type": "file", "mode": mode, "digest": digest, "size": size}
    return {"type": "other", "mode": mode, "kind": oct(stat.S_IFMT(info.st_mode))}


def manifest(root):
    """One read-only tree manifest; unreadable entries raise (never silently empty)."""
    root = Path(root)
    try:
        info = os.lstat(root)
    except FileNotFoundError:
        return {"state": "missing", "root": str(root), "entries": {}}
    except OSError as exc:
        raise SnapshotError(f"cannot stat {root}: {exc}") from exc
    if stat.S_ISLNK(info.st_mode):
        # 根本身是链接：只记录链接事实，不跟随（否则会把树外内容当成宿主缓存）。
        return {"state": "symlink", "root": str(root),
                "entries": {'.': _entry(root, '.', set())}}
    if not stat.S_ISDIR(info.st_mode):
        return {"state": "not-directory", "root": str(root),
                "entries": {'.': _entry(root, '.', set())}}
    entries = {'.': {"type": "dir", "mode": stat.S_IMODE(info.st_mode)}}
    pending = [(str(root), '')]
    while pending:
        directory, relative = pending.pop()
        try:
            names = sorted(os.listdir(directory))
        except OSError as exc:
            raise SnapshotError(f"cannot list {directory}: {exc}") from exc
        for name in names:
            absolute = os.path.join(directory, name)
            child = f"{relative}/{name}" if relative else name
            entry = _entry(absolute, child, set())
            entries[child] = entry
            if entry["type"] == "dir":
                pending.append((absolute, child))
    return {"state": "present", "root": str(root), "entries": entries}


def compare(before, after):
    before_entries = before.get("entries") or {}
    after_entries = after.get("entries") or {}
    differences = {"state": [] if before.get("state") == after.get("state")
                   else [{"before": before.get("state"), "after": after.get("state")}],
                   "added": sorted(set(after_entries) - set(before_entries)),
                   "removed": sorted(set(before_entries) - set(after_entries)),
                   "modified": sorted(path for path in set(before_entries) & set(after_entries)
                                      if before_entries[path] != after_entries[path])}
    differences["changed"] = bool(differences["state"] or differences["added"]
                                  or differences["removed"] or differences["modified"])
    return differences


def write_json_atomic(path, payload):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent,
                                         prefix="." + path.name, delete=False) as stream:
            temporary = Path(stream.name)
            json.dump(payload, stream, ensure_ascii=False, indent=2, sort_keys=True)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        temporary.replace(path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="operation", required=True)
    capture = sub.add_parser("capture")
    capture.add_argument("root")
    capture.add_argument("out")
    check = sub.add_parser("check")
    check.add_argument("root")
    check.add_argument("--expect", required=True)
    args = parser.parse_args(argv)
    try:
        if args.operation == "capture":
            payload = manifest(args.root)
            write_json_atomic(args.out, payload)
            print(f"HOST-SNAPSHOT: {args.root} state={payload['state']} "
                  f"entries={len(payload['entries'])}")
            return 0
        try:
            with open(args.expect, encoding="utf-8") as handle:
                before = json.load(handle)
        except (OSError, ValueError) as exc:
            raise SnapshotError(f"expected manifest unreadable: {exc}") from exc
        differences = compare(before, manifest(args.root))
        if differences["changed"]:
            print("HOST-CHANGED: " + json.dumps(differences, ensure_ascii=False, sort_keys=True))
            return 1
        print("HOST-UNCHANGED")
        return 0
    except SnapshotError as exc:
        print(f"HOST-SNAPSHOT-UNVERIFIED: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
