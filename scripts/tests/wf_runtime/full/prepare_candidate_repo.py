#!/usr/bin/env python3
"""prepare_candidate_repo.py — 把候选发行树引导成「干净、带 tag 的候选仓库根」。

为什么需要它：`install.py` 的 `resolve_tag()` / `_committed_bytes()` / `_worktree_clean()`
要求 `--source` 是一个**含 `refs/tags/wf-vX.Y.Z` 的干净 git 仓库根**；
`docs/workflows/wf-release` 只是作者仓库里的普通目录，直接拿它当 `--source` 会失败。

契约（方案稿 §3.5）：
- 复制 `--tree`（默认 `docs/workflows/wf-release`）到 `--out`，`git init`/`add`/`commit`/`tag wf-v<version>`；
- 校验：tag 可解析、`git status --porcelain` 干净、`wf-release.json.version` 与 tag 一致、
  `install.py` + `wf-release.json` + `wf-release/` 都在；
- meta 写 `<out>.meta.json`（**仓库根外**，否则 `_worktree_clean()` 会判脏）；
- 按 `tree_digest + version` 缓存：树或版本变化就重建，不复用陈旧仓库；
- `--check` 只校验（配合 `--no-build`），不重建。

用法：
    python3 scripts/tests/wf_runtime/full/prepare_candidate_repo.py \
        --tree docs/workflows/wf-release --version 0.1.2 --out ~/.cache/wf-candidate-repo/0.1.2
    python3 scripts/tests/wf_runtime/full/prepare_candidate_repo.py --check --out <候选根> --version 0.1.2
"""
from __future__ import annotations

import argparse
import datetime
import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(REPO_ROOT, "scripts"))

import wf_release_common as common  # noqa: E402

DEFAULT_TREE = os.path.join(REPO_ROOT, "docs", "workflows", "wf-release")
META_SCHEMA = 1
OWNER_TAG = "wf-candidate-repo"


class CandidateError(Exception):
    """可预期的拒绝（非零退出）。"""


def tag_ref(version):
    return f"refs/tags/wf-v{version}"


def meta_path(out):
    return os.path.realpath(out) + ".meta.json"


def owner_path(out):
    return os.path.realpath(out) + ".owner"


def write_json_atomic(path, payload):
    directory = os.path.dirname(path) or "."
    os.makedirs(directory, exist_ok=True)
    handle = tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=directory, prefix=".tmp-",
                                         delete=False, suffix=".json")
    try:
        json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    finally:
        handle.close()
    os.replace(handle.name, path)


def read_json(path):
    try:
        with open(path, encoding="utf-8") as handle:
            return json.load(handle)
    except (OSError, ValueError):
        return None


def git(repo, *args, check=True):
    return subprocess.run(["git", "-c", "safe.directory=*", *args], cwd=repo,
                          capture_output=True, text=True, check=check)


def check_out_path(out):
    if not out:
        raise CandidateError("--out is required")
    if os.path.islink(out):
        raise CandidateError(f"--out must not be a symlink: {out}")
    real = os.path.realpath(out)
    if real == os.sep or real == os.path.realpath(os.path.expanduser("~")):
        raise CandidateError(f"--out must not be {real}")
    for label, forbidden in (("repository root", os.path.realpath(REPO_ROOT)),
                             ("product release tree", os.path.realpath(DEFAULT_TREE))):
        if real == forbidden or real.startswith(forbidden + os.sep):
            raise CandidateError(f"--out overlaps {label}: {real}")
        if forbidden.startswith(real + os.sep):
            raise CandidateError(f"--out is an ancestor of {label}: {real}")
    return real


def copy_tree(tree, dest):
    def ignore(_directory, names):
        return [name for name in names if name in (".git", "__pycache__") or name.endswith(".pyc")]

    shutil.copytree(tree, dest, ignore=ignore)


def verify_repo(out, version):
    """校验候选仓库根：tag/干净/版本/结构；返回 (commit, tree_digest)。"""
    real = check_out_path(out)
    if not os.path.isdir(real):
        raise CandidateError(f"候选仓库根不存在：{real}（重建或去掉 --no-build）")
    if not os.path.isdir(os.path.join(real, ".git")):
        raise CandidateError(f"候选仓库根不是 git 仓库：{real}")
    for name in ("install.py", "wf-release.json", "wf-release"):
        if not os.path.exists(os.path.join(real, name)):
            raise CandidateError(f"候选仓库根缺少 {name}：{real}")
    result = git(real, "rev-parse", f"{tag_ref(version)}^{{commit}}", check=False)
    if result.returncode != 0:
        raise CandidateError(f"候选仓库根没有可解析的 tag {tag_ref(version)}：{real}")
    commit = result.stdout.strip()
    status = git(real, "status", "--porcelain", check=False)
    if status.returncode != 0:
        raise CandidateError(f"候选仓库根不是 git 工作树：{real}")
    dirty = [line for line in status.stdout.splitlines() if line.strip()]
    if dirty:
        raise CandidateError("候选仓库根工作树不干净：" + "; ".join(dirty[:5]))
    manifest = read_json(os.path.join(real, "wf-release.json"))
    if not manifest:
        raise CandidateError(f"候选仓库根缺少可解析的 wf-release.json：{real}")
    if manifest.get("version") != version:
        raise CandidateError(
            f"候选版本与 tag 不一致：wf-release.json version={manifest.get('version')!r} tag={version!r}")
    return commit, common.tree_digest(real)


def ensure(tree, version, out):
    if not version or version.count(".") != 2:
        raise CandidateError(f"--version must be X.Y.Z：{version!r}")
    tree = os.path.realpath(tree or DEFAULT_TREE)
    if not os.path.isdir(tree):
        raise CandidateError(f"--tree 不存在：{tree}")
    manifest = read_json(os.path.join(tree, "wf-release.json"))
    if not manifest:
        raise CandidateError(f"--tree 缺少 wf-release.json：{tree}")
    if manifest.get("version") != version:
        raise CandidateError(
            f"--tree 的 wf-release.json version={manifest.get('version')!r} 与 --version {version!r} 不一致"
            "（先用 build-wf-release.py --version <X.Y.Z> 构建候选树）")
    real = check_out_path(out)
    current_tree = common.tree_digest(tree)
    meta = read_json(meta_path(real))
    if (meta and meta.get("version") == version and meta.get("tree_digest") == current_tree
            and os.path.isdir(real)):
        try:
            commit, digest = verify_repo(real, version)
            return real, {"schema_version": META_SCHEMA, "version": version,
                          "tag": f"wf-v{version}", "ref": tag_ref(version), "commit": commit,
                          "tree_digest": digest, "built_at": meta.get("built_at")}, "REUSED"
        except CandidateError:
            pass  # 仓库被改动：重建
    if os.path.exists(real):
        owner = read_json(owner_path(real))
        if not owner or owner.get("owner") != OWNER_TAG:
            raise CandidateError(
                f"--out 已存在且不是 {OWNER_TAG} 产物：{real}（换一个 --out 或手工清理）")
    parent = os.path.dirname(real) or "."
    os.makedirs(parent, exist_ok=True)
    staging = tempfile.mkdtemp(prefix=".wf-candidate-", dir=parent)
    try:
        repo = os.path.join(staging, "repo")
        copy_tree(tree, repo)
        for cmd in (["init", "-q"], ["config", "user.email", "tests@example.com"],
                    ["config", "user.name", "wf-candidate"], ["add", "-A"],
                    ["commit", "-qm", f"wf release {version}"], ["tag", f"wf-v{version}"]):
            git(repo, *cmd)
        commit, digest = verify_repo(repo, version)
        if os.path.isdir(real):
            shutil.rmtree(real)
        elif os.path.exists(real):
            os.unlink(real)
        shutil.move(repo, real)
        meta = {"schema_version": META_SCHEMA, "version": version, "tag": f"wf-v{version}",
                "ref": tag_ref(version), "commit": commit, "tree_digest": digest,
                "source_tree_digest": common.source_tree_digest(),
                "built_at": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")}
        write_json_atomic(meta_path(real), meta)
        write_json_atomic(owner_path(real), {"schema_version": 1, "owner": OWNER_TAG, "root": real,
                                             "version": version})
        return real, meta, "BUILT"
    finally:
        shutil.rmtree(staging, ignore_errors=True)


def check(tree, version, out):
    real = check_out_path(out)
    meta = read_json(meta_path(real))
    if not meta:
        raise CandidateError(f"候选 meta 缺失：{meta_path(real)}（重建或去掉 --no-build）")
    if meta.get("version") != version:
        raise CandidateError(f"候选 meta 版本过期：meta={meta.get('version')} expected={version}")
    commit, digest = verify_repo(real, version)
    if meta.get("tree_digest") != digest:
        raise CandidateError(
            f"候选仓库树摘要与 meta 不一致（候选被改动）：meta={meta.get('tree_digest')} current={digest}")
    if meta.get("commit") != commit:
        raise CandidateError(f"候选 tag 提交与 meta 不一致：meta={meta.get('commit')} current={commit}")
    tree = os.path.realpath(tree or DEFAULT_TREE)
    if os.path.isdir(tree) and meta.get("tree_digest") != common.tree_digest(tree):
        raise CandidateError(
            "候选仓库与当前候选树不一致（先重建候选仓库）："
            f"repo={meta.get('tree_digest')} tree={common.tree_digest(tree)}")
    return meta, "OK"


def main(argv=None):
    parser = argparse.ArgumentParser(description="候选仓库引导（复制 → commit → tag → 校验）")
    parser.add_argument("--tree", default=DEFAULT_TREE, help="候选发行树（默认 docs/workflows/wf-release）")
    parser.add_argument("--version", required=True, help="X.Y.Z（与 tag wf-vX.Y.Z 一致）")
    parser.add_argument("--out", required=True, help="候选仓库根（缓存目录）")
    parser.add_argument("--check", action="store_true", help="只校验（配合 --no-build）")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    try:
        if args.check:
            meta, status = check(args.tree, args.version, args.out)
        else:
            out, meta, status = ensure(args.tree, args.version, args.out)
        payload = {"status": status, "root": os.path.realpath(args.out), "version": meta["version"],
                   "ref": meta["ref"], "commit": meta["commit"], "tree_digest": meta["tree_digest"]}
        if args.json:
            print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
        else:
            print(f"{status}  candidate {meta['version']}  {payload['root']}")
            print(f"  ref: {meta['ref']}  commit: {meta['commit'][:12]}")
            print(f"  tree_digest: {meta['tree_digest']}")
        return 0
    except CandidateError as exc:
        print(f"FAIL  {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
