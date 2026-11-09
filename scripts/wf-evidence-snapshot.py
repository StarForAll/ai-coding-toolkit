#!/usr/bin/env python3
"""wf-evidence-snapshot.py — dogfood 证据的确定性归档与复核（v42 P0）。

authoring 工具，不进发行清单。证据是 v42 方案的事实基线：归档任务、4 份 Codex 会话
JSONL、`/tmp/wf-review` 审查材料树、目标侧 `.wf/lib` 与源树的差异。

打包确定性：条目按相对路径字节序、`mtime=0`、`uid/gid=0`、`gzip mtime=0`，
因此 `--verify` 可以「重打包 → 比字节」证明归档未被改动；源侧被清理后仍可用
`manifests/*.sha256` 做离线校验。

用法：
  wf-evidence-snapshot.py --pack             # 从源侧重建全部证据
  wf-evidence-snapshot.py --verify           # 重打包并比字节（需要源侧存在）
  wf-evidence-snapshot.py --offline-verify   # 只校验已存归档与其逐文件清单
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import io
import os
import sys
import tarfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SOURCE_ROOT = REPO_ROOT / "docs" / "workflows" / "新项目开发工作流"
EVIDENCE_ROOT = SOURCE_ROOT / "analysis" / "evidence"

TARGET_PROJECT = Path.home() / "projects" / "personal" / "traffic_monitor"
SOURCE_LIB = SOURCE_ROOT / "payload" / "lib" / "wflib"
TARGET_LIB = TARGET_PROJECT / ".wf" / "lib" / "wflib"

ARCHIVED_TASK = (
    TARGET_PROJECT / ".wf" / "tasks" / "archive" / "2026-11"
    / "2026-9b960d83632646deb8203c384c3beb84-task"
)
CODEX_SESSIONS = Path.home() / ".codex" / "sessions" / "2026" / "11" / "08"
SESSION_FILES = (
    "rollout-2026-11-08T16-12-24-01a1ba37-3e19-7141-bcbf-a51e3001ceb2.jsonl",
    "rollout-2026-11-08T17-00-01-01a1ba62-d3c4-79d0-bde8-52b05f88e789.jsonl",
    "rollout-2026-11-08T17-10-22-01a1ba6c-4e15-7c51-a543-23eac46ce993.jsonl",
    "rollout-2026-11-08T17-16-56-01a1ba72-525f-7991-90f3-61e4092f98db.jsonl",
)
WF_REVIEW_TREE = Path("/tmp") / "wf-review"

MANIFEST_NAME = "_manifest/files.sha256"


class SnapshotError(Exception):
    pass


# --------------------------------------------------------------------------
# 确定性打包
# --------------------------------------------------------------------------


def _walk_files(root):
    """相对路径 → 绝对路径，按相对路径字节序。"""
    root = Path(root)
    collected = {}
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        relative = path.relative_to(root).as_posix()
        collected[relative] = path
    return dict(sorted(collected.items(), key=lambda item: item[0].encode("utf-8")))


def _file_digest(data):
    return hashlib.sha256(data).hexdigest()


def _manifest_bytes(entries):
    """逐文件清单：`<sha256>  <size>  <mode>  <relpath>`，以字节序稳定。"""
    lines = [f"{digest}  {size}  {mode:04o}  {relative}"
             for relative, (digest, size, mode) in entries.items()]
    return ("\n".join(lines) + "\n").encode("utf-8")


def _read_tree(root):
    if not Path(root).is_dir():
        raise SnapshotError(f"evidence source missing: {root}")
    files = _walk_files(root)
    if not files:
        raise SnapshotError(f"evidence source is empty: {root}")
    entries = {}
    for relative, absolute in files.items():
        with open(absolute, "rb") as handle:
            data = handle.read()
        mode = 0o755 if os.access(absolute, os.X_OK) else 0o644
        entries[relative] = (_file_digest(data), len(data), mode)
    return entries


def _tar_gz(entries, reader):
    """用给定读取函数把 entries 打成确定性 tar.gz（含逐文件清单）。"""
    buffer = io.BytesIO()
    with gzip.GzipFile(fileobj=buffer, mode="wb", mtime=0, compresslevel=9) as gz:
        with tarfile.open(fileobj=gz, mode="w", format=tarfile.GNU_FORMAT) as tar:
            manifest = _manifest_bytes(entries)
            for relative in sorted(list(entries) + [MANIFEST_NAME], key=lambda item: item.encode("utf-8")):
                if relative == MANIFEST_NAME:
                    data = manifest
                    mode = 0o644
                else:
                    data = reader(relative)
                    mode = entries[relative][2]
                info = tarfile.TarInfo(relative)
                info.size = len(data)
                info.mtime = 0
                info.mode = mode
                info.uid = 0
                info.gid = 0
                info.uname = ""
                info.gname = ""
                tar.addfile(info, io.BytesIO(data))
    return buffer.getvalue()


def pack_tree(name, root):
    """把一个目录打成 `<name>.tar.gz`；返回 (sha256, bytes)。"""
    entries = _read_tree(root)
    absolute_of = _walk_files(root)

    def reader(relative):
        with open(absolute_of[relative], "rb") as handle:
            return handle.read()

    data = _tar_gz(entries, reader)
    return _file_digest(data), data


def pack_sessions():
    """4 份会话 JSONL 单独成包（体积大、与目录树分开）。"""
    entries = {}
    payload = {}
    for name in SESSION_FILES:
        absolute = CODEX_SESSIONS / name
        if not Path(absolute).is_file():
            raise SnapshotError(f"session file missing: {absolute}")
        with open(absolute, "rb") as handle:
            data = handle.read()
        entries[name] = (_file_digest(data), len(data), 0o644)
        payload[name] = data
    entries = dict(sorted(entries.items(), key=lambda item: item[0].encode("utf-8")))
    data = _tar_gz(entries, lambda relative: payload[relative])
    return _file_digest(data), data


# --------------------------------------------------------------------------
# 目标侧 lib 差异（源树 ↔ traffic_monitor/.wf/lib/wflib）
# --------------------------------------------------------------------------


def _py_files(root):
    if not Path(root).is_dir():
        raise SnapshotError(f"lib source missing: {root}")
    return {name: Path(root) / name
            for name in sorted(os.listdir(root))
            if name.endswith(".py") and (Path(root) / name).is_file()}


def build_target_lib():
    """返回 {相对文件名: bytes}；含两侧逐文件摘要与逐文件 unified diff。"""
    import difflib

    source = _py_files(SOURCE_LIB)
    target = _py_files(TARGET_LIB)
    names = sorted(set(source) | set(target), key=lambda item: item.encode("utf-8"))

    digest_lines = ["# lib-file  sha256  bytes  side"]
    patches = []
    for name in names:
        for side, root_map in (("source", source), ("target", target)):
            if name in root_map:
                with open(root_map[name], "rb") as handle:
                    data = handle.read()
                digest_lines.append(f"{name}  {_file_digest(data)}  {len(data)}  {side}")
            else:
                digest_lines.append(f"{name}  -  0  {side}-missing")
        if name in source and name in target:
            with open(source[name], "r", encoding="utf-8", errors="replace") as handle:
                left = handle.read().splitlines(keepends=True)
            with open(target[name], "r", encoding="utf-8", errors="replace") as handle:
                right = handle.read().splitlines(keepends=True)
            if left == right:
                continue
            diff = list(difflib.unified_diff(left, right, fromfile=f"source/{name}", tofile=f"target/{name}"))
            if diff:
                patches.append("".join(diff))

    files = {
        "lib-files.sha256": ("\n".join(digest_lines) + "\n").encode("utf-8"),
        "lib.diff": ("\n".join(patches)).encode("utf-8"),
    }
    return files


# --------------------------------------------------------------------------
# 写入与校验
# --------------------------------------------------------------------------


def manifests_dir():
    return EVIDENCE_ROOT / "manifests"


def _write(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def pack_all():
    manifests_dir().mkdir(parents=True, exist_ok=True)
    written = []
    for name, producer in (
        ("archived-task", lambda: pack_tree("archived-task", ARCHIVED_TASK)),
        ("sessions", pack_sessions),
        ("wf-review-tree", lambda: pack_tree("wf-review-tree", WF_REVIEW_TREE)),
    ):
        digest, data = producer()
        path = EVIDENCE_ROOT / f"{name}.tar.gz"
        _write(path, data)
        _write(manifests_dir() / f"{name}.sha256", f"{digest}  {name}.tar.gz\n".encode())
        written.append((f"{name}.tar.gz", digest, len(data)))

    target_files = build_target_lib()
    lines = []
    for name, data in sorted(target_files.items()):
        _write(EVIDENCE_ROOT / "target-lib" / name, data)
        lines.append(f"{_file_digest(data)}  {len(data)}  {name}")
        written.append((f"target-lib/{name}", _file_digest(data), len(data)))
    _write(manifests_dir() / "target-lib.sha256",
           ("\n".join(lines) + "\n").encode("utf-8"))
    return written


def verify_stored():
    """离线：校验已存归档的 sha256，并核对包内逐文件清单与内容一致。"""
    problems = []
    for name in ("archived-task", "sessions", "wf-review-tree"):
        archive = EVIDENCE_ROOT / f"{name}.tar.gz"
        sha_file = manifests_dir() / f"{name}.sha256"
        if not (Path(archive).is_file() and Path(sha_file).is_file()):
            problems.append(f"missing archive or digest: {name}")
            continue
        with open(archive, "rb") as handle:
            data = handle.read()
        expected = open(sha_file, encoding="utf-8").read().split()[0]
        if _file_digest(data) != expected:
            problems.append(f"archive digest mismatch: {name}")
            continue
        problems.extend(_verify_tar_contents(name, data))

    sha_file = manifests_dir() / "target-lib.sha256"
    if not Path(sha_file).is_file():
        problems.append("missing target-lib manifest")
    else:
        for line in open(sha_file, encoding="utf-8"):
            if not line.strip():
                continue
            digest, size, name = line.rstrip("\n").split("  ")
            path = EVIDENCE_ROOT / "target-lib" / name
            if not Path(path).is_file():
                problems.append(f"missing target-lib file: {name}")
                continue
            data = Path(path).read_bytes()
            if _file_digest(data) != digest or str(len(data)) != size:
                problems.append(f"target-lib file changed: {name}")
    return problems


def _verify_tar_contents(name, data):
    problems = []
    with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as tar:
        members = {member.name: member for member in tar.getmembers()}
        if MANIFEST_NAME not in members:
            return [f"{name}: in-archive manifest missing"]
        manifest = tar.extractfile(MANIFEST_NAME).read().decode("utf-8")
        declared = {}
        for line in manifest.splitlines():
            if not line.strip():
                continue
            digest, size, mode, relative = line.split("  ", 3)
            declared[relative] = (digest, int(size), mode)
        actual_names = {item for item in members if item != MANIFEST_NAME}
        if actual_names != set(declared):
            problems.append(f"{name}: in-archive file set differs from manifest")
        for relative, (digest, size, _mode) in declared.items():
            member = members.get(relative)
            if member is None:
                continue
            body = tar.extractfile(member).read()
            if _file_digest(body) != digest or len(body) != size:
                problems.append(f"{name}: in-archive content mismatch: {relative}")
    return problems


def verify_against_sources():
    """在线：重打包并比字节（源侧仍在时使用，证明归档就是源侧当时的字节）。

    `target-lib/` 不参与重打包比对：它是**时点快照**（dogfood 时的源树 vs 目标侧），
    源树此后还会继续演进，重算必然不同。它的完整性由 `manifests/target-lib.sha256`
    与包内内容共同保证（`--offline-verify` 覆盖）。
    """
    problems = verify_stored()
    for name, producer in (
        ("archived-task", lambda: pack_tree("archived-task", ARCHIVED_TASK)),
        ("sessions", pack_sessions),
        ("wf-review-tree", lambda: pack_tree("wf-review-tree", WF_REVIEW_TREE)),
    ):
        try:
            digest, data = producer()
        except SnapshotError as exc:
            problems.append(f"source unavailable ({name}): {exc}")
            continue
        path = EVIDENCE_ROOT / f"{name}.tar.gz"
        stored = Path(path).read_bytes() if Path(path).is_file() else b""
        if stored != data:
            problems.append(f"re-pack differs from stored archive: {name}")
    return problems


def main(argv=None):
    parser = argparse.ArgumentParser(description="dogfood 证据归档与复核（v42 P0）")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--pack", action="store_true", help="从源侧重建全部证据")
    group.add_argument("--verify", action="store_true", help="重打包并比字节（需要源侧）")
    group.add_argument("--offline-verify", action="store_true", help="只校验已存归档")
    args = parser.parse_args(argv)

    if args.pack:
        written = pack_all()
        for name, digest, size in written:
            print(f"packed {name}  {digest}  {size} bytes")
        return 0

    problems = verify_against_sources() if args.verify else verify_stored()
    if problems:
        for item in problems:
            print(f"EVIDENCE PROBLEM: {item}", file=sys.stderr)
        return 1
    print("evidence OK" + (" (sources re-packed, byte-identical)" if args.verify else " (offline digests + manifests)"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
