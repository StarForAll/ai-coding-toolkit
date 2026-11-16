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
from pathlib import Path

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(REPO_ROOT, "scripts"))

import wf_release_common as common  # noqa: E402
import wf_test_paths  # noqa: E402  （scope 下候选根与派生 sidecar 必须在首次写入前核验）
import release_lock  # noqa: E402  （候选根的固定 sidecar 锁：同一 canonical root 的 verify/publish 事务）

DEFAULT_TREE = os.path.join(REPO_ROOT, "docs", "workflows", "wf-release")
META_SCHEMA = 2
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
    # `git status --porcelain` 默认会刷新 .git/index（stat 缓存），这与“check 只读”矛盾。
    # GIT_OPTIONAL_LOCKS=0 禁止这类可选索引写入；verify/check 不改变候选仓库字节。
    env = {**os.environ, "GIT_OPTIONAL_LOCKS": "0"}
    return subprocess.run(["git", "-c", "safe.directory=*", *args], cwd=repo,
                          capture_output=True, text=True, check=check, env=env)


def check_out_path(out):
    if not out:
        raise CandidateError("--out is required")
    if os.path.islink(out):
        raise CandidateError(f"--out must not be a symlink: {out}")
    try:
        # 候选根、meta/owner sidecar 与 staging 父目录都必须落在 owned scope 内。
        wf_test_paths.require_in_scope(out, meta_path(out), owner_path(out),
                                       os.path.dirname(os.path.realpath(out)))
    except wf_test_paths.PathError as exc:
        raise CandidateError(str(exc)) from exc
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


def _owner_of(out):
    return read_json(owner_path(out))


def verify_repo(out, version):
    """候选仓库根的**基础**结构：结构文件、tag、干净工作树、清单版本。"""
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
    head = git(real, "rev-parse", "HEAD", check=False)
    if head.returncode != 0 or not head.stdout.strip():
        raise CandidateError(f"候选仓库根无法解析 HEAD：{real}")
    return {"commit": commit, "head": head.stdout.strip(),
            "tree_digest": common.tree_digest(real),
            "manifest": manifest}


def verify_candidate(tree, version, out):
    """ensure 命中、check 与发布后验证共用的**完整**候选身份校验。

    一致面：输入树实际摘要 = 候选实际摘要 = meta.tree_digest；meta 版本/ref/tag/commit
    与实际 tag/HEAD 对应；owner 记录本工具所有；工作树干净；清单版本与 tag 一致。
    任一不符返回可归因的拒绝——干净工作树只证明“与当前 HEAD 一致”，不能代替内容核对。
    """
    real = check_out_path(out)
    if not os.path.isdir(real):
        raise CandidateError(f"候选仓库根不存在：{real}")
    owner = _owner_of(real)
    if not owner or owner.get("owner") != OWNER_TAG or owner.get("root") != real:
        raise CandidateError(
            f"--out 已存在且不是 {OWNER_TAG} 产物：{real}（拒绝覆盖无主目录）")
    meta = read_json(meta_path(real))
    if not meta:
        raise CandidateError(f"候选 meta 缺失：{meta_path(real)}（重建或去掉 --no-build）")
    if meta.get("schema_version") != META_SCHEMA:
        raise CandidateError(
            f"候选 meta schema={meta.get('schema_version')!r}（只接受 {META_SCHEMA}；重建）")
    if meta.get("version") != version:
        raise CandidateError(f"候选 meta 版本过期：meta={meta.get('version')} expected={version}")
    facts = verify_repo(real, version)
    tree = os.path.realpath(tree or DEFAULT_TREE)
    if not os.path.isdir(tree):
        raise CandidateError(f"--tree 不存在：{tree}")
    input_digest = common.tree_digest(tree)
    for label, expected, actual in (
            ("输入树与候选内容", input_digest, facts["tree_digest"]),
            ("meta tree_digest 与候选内容", meta.get("tree_digest"), facts["tree_digest"]),
            ("meta input_tree_digest 与当前输入树", meta.get("input_tree_digest"), input_digest),
            ("meta commit 与 tag 提交", meta.get("commit"), facts["commit"]),
            ("meta commit 与 HEAD", meta.get("commit"), facts["head"]),
            ("meta ref 与 tag", meta.get("ref"), tag_ref(version)),
            ("meta tag 与版本", meta.get("tag"), f"wf-v{version}"),
            ("meta 版本与请求", meta.get("version"), version)):
        if expected != actual:
            raise CandidateError(f"候选身份不一致（{label}）：{expected!r} != {actual!r}")
    return {"root": real, "version": version, "ref": tag_ref(version), "tag": f"wf-v{version}",
            "commit": facts["commit"], "head": facts["head"],
            "tree_digest": facts["tree_digest"], "input_tree_digest": input_digest,
            "built_at": meta.get("built_at"),
            "source_tree_digest": meta.get("source_tree_digest")}


def _publish_staged(staging, real, version, meta, owner_payload):
    """原子发布：先验证新代，再替换；失败恢复旧代与旧 sidecar。"""
    old_meta = None
    old_owner = None
    try:
        old_meta = Path(meta_path(real)).read_bytes()
    except OSError:
        pass
    try:
        old_owner = Path(owner_path(real)).read_bytes()
    except OSError:
        pass
    backup = None
    try:
        if os.path.isdir(real):
            backup = os.path.join(staging, "backup")
            os.rename(real, backup)
        elif os.path.exists(real):
            os.unlink(real)
        shutil.move(os.path.join(staging, "repo"), real)
        write_json_atomic(meta_path(real), meta)
        write_json_atomic(owner_path(real), owner_payload)
    except BaseException:
        shutil.rmtree(real, ignore_errors=True) if os.path.isdir(real) else None
        if backup and os.path.isdir(backup):
            os.rename(backup, real)
        if old_meta is not None:
            Path(meta_path(real)).write_bytes(old_meta)
        if old_owner is not None:
            Path(owner_path(real)).write_bytes(old_owner)
        raise
    finally:
        if backup and os.path.isdir(backup):
            shutil.rmtree(backup, ignore_errors=True)


def _candidate_lock(real, exclusive):
    try:
        return release_lock.acquire(real, exclusive=exclusive)
    except release_lock.Busy as exc:
        raise CandidateError(f"候选仓库根正被另一个事务持有：{exc}") from exc
    except release_lock.LockError as exc:
        raise CandidateError(f"候选仓库根锁不可用：{exc}") from exc


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
    input_digest = common.tree_digest(tree)
    lock_fd = _candidate_lock(real, exclusive=True)
    try:
        return _ensure_locked(tree, version, real, input_digest)
    finally:
        release_lock.release(lock_fd)


def _ensure_locked(tree, version, real, input_digest):
    if os.path.isdir(real):
        # 已有输出：只有本工具拥有且完整身份一致时才复用；无主目录一律拒绝覆盖。
        if _owner_of(real) is None or (_owner_of(real) or {}).get("owner") != OWNER_TAG:
            raise CandidateError(
                f"--out 已存在且不是 {OWNER_TAG} 产物：{real}（换一个 --out 或手工清理）")
        try:
            facts = verify_candidate(tree, version, real)
            return real, {"schema_version": META_SCHEMA, "version": version,
                          "tag": facts["tag"], "ref": facts["ref"], "commit": facts["commit"],
                          "tree_digest": facts["tree_digest"],
                          "input_tree_digest": input_digest,
                          "source_tree_digest": facts.get("source_tree_digest"),
                          "built_at": facts.get("built_at")}, "REUSED"
        except CandidateError:
            pass  # 陈旧/被改动：重建（下面会再完整验证新代）
    elif os.path.exists(real):
        raise CandidateError(f"--out 已存在且不是目录：{real}")
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
        facts = verify_repo(repo, version)
        if facts["tree_digest"] != input_digest:
            raise CandidateError("新候选内容与输入树不一致（拒绝发布）")
        meta = {"schema_version": META_SCHEMA, "version": version, "tag": f"wf-v{version}",
                "ref": tag_ref(version), "commit": facts["commit"], "head": facts["head"],
                "tree_digest": facts["tree_digest"], "input_tree_digest": input_digest,
                "source_tree_digest": common.source_tree_digest(),
                "built_at": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")}
        owner_payload = {"schema_version": 1, "owner": OWNER_TAG, "root": real,
                         "version": version}
        _publish_staged(staging, real, version, meta, owner_payload)
        # 发布后验证：读回 meta 与实际内容/输入树全部一致才签 BUILT。
        verify_candidate(tree, version, real)
        return real, meta, "BUILT"
    finally:
        shutil.rmtree(staging, ignore_errors=True)


def check(tree, version, out):
    """只读校验：不创建/改写任何文件（含锁 sidecar），供 --no-build/最终 barrier 使用。"""
    real = check_out_path(out)
    facts = verify_candidate(tree, version, real)
    meta = read_json(meta_path(facts["root"]))
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
