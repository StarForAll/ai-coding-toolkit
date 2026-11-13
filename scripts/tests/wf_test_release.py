#!/usr/bin/env python3
"""wf_test_release.py — 测试专用发行构建入口（不进发行清单、不写产品发行树）。

为什么需要它：`build-wf-release.py` 的 CLI 只写产品树 `docs/workflows/wf-release/`；
执行测试（T1/T2）要的是**与产品树解耦**的发行副本，否则每轮测试都会改写产品发行物。

契约（方案稿 §4.4）：
- 输出根默认 `~/.cache/wf-test-release/<version>`，`--root` 可覆盖，但必须在仓库/源码/产品树之外；
- 输出根必须是空目录，或带**输出根之外**的所有权标记 `<out>.owner`（标记不能进发行树，否则字节复现失败）；
- 先在同级临时目录构建 + 重放比对成功，再原子替换；失败保留旧产物；
- 写 `<out>.meta.json`（输出根外）：version / release_ref / source_tree_digest / manifest_digest / built_at；
- `--check`（配合 `--no-build`）核对 meta 与当前源树摘要，不一致就拒绝。

用法：
    python3 scripts/tests/wf_test_release.py --ensure [--version X.Y.Z] [--root DIR]
    python3 scripts/tests/wf_test_release.py --check  [--root DIR]
"""
from __future__ import annotations

import argparse
import datetime
import json
import os
import shutil
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import wf_release_common as common  # noqa: E402

REPO_ROOT = common.REPO_ROOT
SOURCE_ROOT = common.SOURCE_ROOT
PRODUCT_RELEASE = os.path.join(REPO_ROOT, "docs", "workflows", "wf-release")
DEV_PLACEHOLDER = "0.0.0-dev"
TEST_VERSION_FALLBACK = "0.1.0"
OWNER_TAG = "wf-test-release"
META_SCHEMA = 1
CACHE_ROOT = os.path.join(os.path.expanduser("~"), ".cache", "wf-test-release")


class TestReleaseError(Exception):
    """可预期的拒绝（非零退出，不打印 traceback）。"""


def ref_for(version):
    return f"refs/tags/wf-v{version}"


def _load_builder():
    """按路径加载 `scripts/build-wf-release.py`（文件名带连字符，不能直接 import）。"""
    import importlib.util

    path = os.path.join(REPO_ROOT, "scripts", "build-wf-release.py")
    spec = importlib.util.spec_from_file_location("wf_release_builder", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def resolve_version(explicit=None, dev_manifest=None):
    """显式 → 环境 → dev-manifest（真实版本）→ 测试常量；与 dev-manifest 冲突时明确失败。"""
    dev_manifest = dev_manifest if dev_manifest is not None else common.load_dev_manifest()
    declared = (dev_manifest or {}).get("version")
    requested = explicit or os.environ.get("WF_TEST_RELEASE_VERSION") or None
    if requested:
        if not requested.count(".") == 2:
            raise TestReleaseError(f"版本必须是 X.Y.Z：{requested!r}")
        if declared and declared != DEV_PLACEHOLDER and declared != requested:
            raise TestReleaseError(
                f"测试版本与 dev-manifest 不一致：dev-manifest={declared} requested={requested}；"
                "测试版本需与 dev-manifest 一致或显式更新 dev-manifest（不得静默构建别的版本）")
        return requested
    if declared and declared != DEV_PLACEHOLDER:
        return declared
    return TEST_VERSION_FALLBACK


def default_root(version):
    return os.path.join(os.environ.get("WF_TEST_RELEASE_CACHE") or CACHE_ROOT, version)


def owner_path(root):
    return os.path.realpath(root) + ".owner"


def meta_path(root):
    return os.path.realpath(root) + ".meta.json"


def _forbidden_roots():
    return [("repository root", os.path.realpath(REPO_ROOT)),
            ("wf source tree", os.path.realpath(SOURCE_ROOT)),
            ("product release tree", os.path.realpath(PRODUCT_RELEASE)),
            ("python stdlib", os.path.realpath(os.path.dirname(os.__file__)))]


def check_output_root(root):
    """输出根安全边界：不越界、不符号链接、不与仓库/源码/产品树重叠。"""
    if not root:
        raise TestReleaseError("output root is empty")
    if os.path.islink(root):
        raise TestReleaseError(f"output root must not be a symlink: {root}")
    real = os.path.realpath(root)
    if real == os.sep:
        raise TestReleaseError("output root must not be filesystem root")
    if real == os.path.realpath(os.path.expanduser("~")):
        raise TestReleaseError("output root must not be the home directory")
    for label, forbidden in _forbidden_roots():
        if real == forbidden or real.startswith(forbidden + os.sep):
            raise TestReleaseError(f"output root overlaps {label}: {real}")
        if forbidden.startswith(real + os.sep):
            raise TestReleaseError(f"output root is an ancestor of {label}: {real}")
    return real


def read_owner(root):
    path = owner_path(root)
    if not os.path.isfile(path):
        return None
    try:
        with open(path, encoding="utf-8") as handle:
            return json.load(handle)
    except (OSError, ValueError):
        return None


def write_json_atomic(path, payload):
    directory = os.path.dirname(path) or "."
    os.makedirs(directory, exist_ok=True)
    handle = tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=directory,
                                         prefix=".tmp-", delete=False, suffix=".json")
    try:
        json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    finally:
        handle.close()
    os.replace(handle.name, path)


def read_meta(root):
    path = meta_path(root)
    if not os.path.isfile(path):
        return None
    try:
        with open(path, encoding="utf-8") as handle:
            return json.load(handle)
    except (OSError, ValueError):
        return None


def _assert_owned_or_empty(real):
    if not os.path.exists(real):
        return
    if not os.path.isdir(real):
        raise TestReleaseError(f"output root exists and is not a directory: {real}")
    entries = [name for name in os.listdir(real) if name != "__pycache__"]
    if not entries:
        return
    owner = read_owner(real)
    if not owner or owner.get("owner") != OWNER_TAG or owner.get("root") != real:
        raise TestReleaseError(
            f"output root is not empty and carries no {OWNER_TAG} ownership marker: {real}；"
            "拒绝覆盖非本工具产物（请换一个 --root 或手工清理）")


def check_meta(root=None, version=None, dev_manifest=None):
    """核对 meta 与当前源树/版本；返回 meta。任何不一致都抛 TestReleaseError。"""
    dev_manifest = dev_manifest if dev_manifest is not None else common.load_dev_manifest()
    expected_version = version or resolve_version(None, dev_manifest)
    real = check_output_root(root or default_root(expected_version))
    if not os.path.isdir(real):
        raise TestReleaseError(f"测试发行副本不存在：{real}（重建或去掉 --no-build）")
    meta = read_meta(real)
    if not meta:
        raise TestReleaseError(f"测试发行 meta 缺失：{meta_path(real)}（重建或去掉 --no-build）")
    if meta.get("version") != expected_version:
        raise TestReleaseError(
            f"测试发行版本过期：meta={meta.get('version')} expected={expected_version}（测试发行副本过期，重建或去掉 --no-build）")
    if meta.get("release_ref") != ref_for(expected_version):
        raise TestReleaseError(
            f"测试发行引用过期：meta={meta.get('release_ref')} expected={ref_for(expected_version)}")
    current = common.source_tree_digest()
    if meta.get("source_tree_digest") != current:
        raise TestReleaseError(
            f"测试发行源树摘要过期：meta={meta.get('source_tree_digest')} current={current}；"
            "测试发行副本过期，重建或去掉 --no-build")
    manifest_file = os.path.join(real, "wf-release.json")
    if not os.path.isfile(manifest_file):
        raise TestReleaseError(f"测试发行缺少 wf-release.json：{real}")
    with open(manifest_file, encoding="utf-8") as handle:
        manifest = json.load(handle)
    if common.manifest_digest(manifest) != meta.get("manifest_digest"):
        raise TestReleaseError("测试发行清单摘要与 meta 不一致（副本被改动）")
    if manifest.get("version") != expected_version:
        raise TestReleaseError(
            f"测试发行清单版本不一致：manifest={manifest.get('version')} expected={expected_version}")
    return meta


def ensure_release(root=None, version=None, dev_manifest=None, rebuild=True):
    """确保缓存根有一份与当前源树一致的测试发行；返回 (root, meta)。"""
    dev_manifest = dev_manifest if dev_manifest is not None else common.load_dev_manifest()
    version = version or resolve_version(None, dev_manifest)
    real = check_output_root(root or default_root(version))
    if not rebuild:
        return real, check_meta(real, version, dev_manifest)
    current = common.source_tree_digest()
    existing = read_meta(real)
    if (existing and existing.get("version") == version
            and existing.get("source_tree_digest") == current
            and os.path.isdir(real)):
        try:
            return real, check_meta(real, version, dev_manifest)
        except TestReleaseError:
            pass  # meta 在但副本被改动：重建
    _assert_owned_or_empty(real)
    parent = os.path.dirname(real) or "."
    os.makedirs(parent, exist_ok=True)
    staging = tempfile.mkdtemp(prefix=".wf-test-release-", dir=parent)
    try:
        builder = _load_builder()
        first = os.path.join(staging, "first")
        second = os.path.join(staging, "second")
        builder.build(version, first, dev_manifest)
        builder.build(version, second, dev_manifest)
        problems = builder.diff_tree(first, second)
        if problems:
            raise TestReleaseError(f"测试发行字节复现失败：{problems[:5]}")
        built_manifest = os.path.join(first, "wf-release.json")
        if not os.path.isfile(built_manifest):
            raise TestReleaseError("测试发行缺少 wf-release.json")
        with open(built_manifest, encoding="utf-8") as handle:
            manifest_on_disk = json.load(handle)
        meta = {
            "schema_version": META_SCHEMA,
            "version": version,
            "release_ref": ref_for(version),
            "source_tree_digest": current,
            "manifest_digest": common.manifest_digest(manifest_on_disk),
            "built_at": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
            "root": real,
        }
        if os.path.isdir(real):
            shutil.rmtree(real)
        elif os.path.exists(real):
            os.unlink(real)
        shutil.move(first, real)
        shutil.rmtree(second, ignore_errors=True)
        _make_tagged_repo(real, version)
        write_json_atomic(meta_path(real), meta)
        write_json_atomic(owner_path(real), {"schema_version": 1, "owner": OWNER_TAG, "root": real,
                                             "version": version})
        return real, meta
    finally:
        shutil.rmtree(staging, ignore_errors=True)


def _make_tagged_repo(root, version):
    """把测试发行副本做成**带 tag 的干净仓库**：安装器要求 `--source` 能解析 refs/tags/wf-vX.Y.Z。

    `.git` 不参与发行字节比对（`tree_digest`/`diff_tree` 都跳过它），也不进 meta。
    """
    import subprocess

    for cmd in (["init", "-q"], ["config", "user.email", "tests@example.com"],
                ["config", "user.name", "wf-test-release"], ["add", "-A"],
                ["commit", "-qm", f"wf test release {version}"], ["tag", f"wf-v{version}"]):
        subprocess.run(["git", "-c", "safe.directory=*", *cmd], cwd=root, check=True,
                       capture_output=True)


def main(argv=None):
    parser = argparse.ArgumentParser(description="wf 测试发行构建（缓存根，不写产品树）")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--ensure", action="store_true", help="构建/复用缓存根里的测试发行")
    group.add_argument("--check", action="store_true", help="只核对 meta 与当前源树")
    parser.add_argument("--version", default=None, help="X.Y.Z（默认按 dev-manifest/测试常量解析）")
    parser.add_argument("--root", default=None, help="输出根（默认 ~/.cache/wf-test-release/<version>）")
    parser.add_argument("--json", action="store_true", help="输出机器可读结果")
    args = parser.parse_args(argv)
    try:
        dev_manifest = common.load_dev_manifest()
        version = resolve_version(args.version, dev_manifest)
        root = check_output_root(args.root or default_root(version))
        if args.check:
            meta = check_meta(root, version, dev_manifest)
            status = "OK"
        else:
            root, meta = ensure_release(root, version, dev_manifest)
            status = "BUILT"
        if args.json:
            print(json.dumps({"status": status, "root": root, "version": meta["version"],
                              "release_ref": meta["release_ref"],
                              "source_tree_digest": meta["source_tree_digest"]},
                             ensure_ascii=False, sort_keys=True))
        else:
            print(f"{status}  test-release {meta['version']}  {root}")
            print(f"  release_ref: {meta['release_ref']}")
            print(f"  source_tree_digest: {meta['source_tree_digest']}")
        return 0
    except TestReleaseError as exc:
        print(f"FAIL  {exc}", file=sys.stderr)
        return 1
    except (common.ReleaseError, SystemExit) as exc:  # build() 的版本一致性拒绝
        print(f"FAIL  {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
