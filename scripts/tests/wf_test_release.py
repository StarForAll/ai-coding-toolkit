#!/usr/bin/env python3
"""wf_test_release.py — 测试专用发行构建入口（不进发行清单、不写产品发行树）。

为什么需要它：`build-wf-release.py` 的 CLI 只写产品树 `docs/workflows/wf-release/`；
执行测试（T1/T2）要的是**与产品树解耦**的发行副本，否则每轮测试都会改写产品发行物。

契约（design §3.1–§3.2 / AC1–AC4、AC11、AC15）：
- 输出根默认 `~/.cache/wf-test-release/<version>`，`--root` 可覆盖，但必须在仓库/源码/产品树之外；
- 输出根必须是空目录，或带**输出根之外**的所有权标记 `<out>.owner`（标记不能进发行树，否则字节复现失败）；
- 每个 canonical root 一个固定 sidecar 锁 inode `<out>.lock`（根外、不随 tree 替换、不 unlink、拒绝符号链接）；
  所有公开 CLI 与库调用都经过**同一把锁**：`--ensure`/恢复/发布是非阻塞独占 flock，`--check` 是共享 flock；
  竞争返回明确 busy（退出码 75），不改 cache、不无限等候；读取方在 runner 消费期由 wrapper 持同一独占 fd；
- build inputs 是完整内容身份（资产/manifest/builder/helper/tool 身份/版本/schema）；meta schema 2 记录
  build_inputs 与实际 output tree digest，check 逐字节核实际发行树，不只信 meta 或 mtime；旧 schema 只算 miss；
- 先把输入冻结、在独立 staging 双构建比对，再走 journal→backup/安装→验证→提交→清理；
  中断后先恢复（新代可验证则前滚，否则按冻结的旧字节回滚），两代都不可验证时 fail closed 保留现场；
- `--lease` 是 runner 的持锁消费入口：同一 PID 持独占 fd 后 `exec` 进入最终消费阶段；`--verify-lease`
  按 `/proc` 祖先/FD/flock/mount 域核验继承来的 lease（环境标记只定位对象，不是授权证据）；
- `--check`（配合 `--no-build`）核 meta 与当前输入，不一致就拒绝；发现未完成 journal 返回 recovery-required。

用法：
    python3 scripts/tests/wf_test_release.py --ensure [--version X.Y.Z] [--root DIR]
    python3 scripts/tests/wf_test_release.py --check  [--root DIR]
    python3 scripts/tests/wf_test_release.py --lease --root DIR --version X.Y.Z [--no-build] -- bash cmd
    python3 scripts/tests/wf_test_release.py --verify-lease --root DIR
"""
from __future__ import annotations

import argparse
import datetime
import fcntl
import hashlib
import json
import os
import shutil
import sys
import tempfile
import uuid
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                               "wf_runtime", "full"))

import wf_release_common as common  # noqa: E402
import release_lock as lock  # noqa: E402
import wf_test_paths  # noqa: E402
import resource_lifecycle as lifecycle  # noqa: E402

REPO_ROOT = common.REPO_ROOT
SOURCE_ROOT = common.SOURCE_ROOT
PRODUCT_RELEASE = os.path.join(REPO_ROOT, "docs", "workflows", "wf-release")
DEV_PLACEHOLDER = "0.0.0-dev"
TEST_VERSION_FALLBACK = "0.1.0"
OWNER_TAG = "wf-test-release"
META_SCHEMA = 2
LEGACY_META_SCHEMA = 1
JOURNAL_SCHEMA = 1
CACHE_ROOT = os.path.join(os.path.expanduser("~"), ".cache", "wf-test-release")
BUSY_EXIT = 75


class TestReleaseError(Exception):
    """可预期的拒绝（非零退出，不打印 traceback）。"""


class TestReleaseBusy(TestReleaseError):
    """锁被占用：调用方明确 busy，可稍后重试。"""


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
    cache = os.environ.get("WF_TEST_RELEASE_CACHE")
    if not cache and wf_test_paths.current_scope() is not None:
        # scope 下默认缓存根同样派生自 scope（不得回落到用户 cache）。
        cache = str(wf_test_paths.resolve_layout()["test_release"])
    return os.path.join(cache or CACHE_ROOT, version)


def _canonical(root):
    return os.path.realpath(root)


def owner_path(root):
    return _canonical(root) + ".owner"


def meta_path(root):
    return _canonical(root) + ".meta.json"


def lock_path(root):
    return _canonical(root) + ".lock"


def journal_path(root):
    return _canonical(root) + ".journal.json"


def _forbidden_roots():
    return [("repository root", os.path.realpath(REPO_ROOT)),
            ("wf source tree", os.path.realpath(SOURCE_ROOT)),
            ("product release tree", os.path.realpath(PRODUCT_RELEASE)),
            ("python stdlib", os.path.realpath(os.path.dirname(os.__file__)))]


def check_output_root(root):
    """输出根安全边界：不越界、不符号链接、不与仓库/源码/产品树重叠。

    显式测试 scope 下还必须在首次写入前核验输出根**及其派生 sidecar/锁/staging** 都在
    scope 内——低层 CLI 不能因为“父进程已经检查过”就跳过本入口将创建的路径。
    """
    if not root:
        raise TestReleaseError("output root is empty")
    if os.path.islink(root):
        raise TestReleaseError(f"output root must not be a symlink: {root}")
    try:
        wf_test_paths.require_in_scope(root, owner_path(root), meta_path(root), lock_path(root),
                                       journal_path(root), os.path.dirname(_canonical(root)))
    except wf_test_paths.PathError as exc:
        raise TestReleaseError(str(exc)) from exc
    real = _canonical(root)
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


# ---- canonical-root 锁（唯一实现在 scripts/release_lock.py）-----------------


def lock_path(root):
    return lock.lock_path(root)


def acquire_lock(root, exclusive=True):
    """非阻塞获取锁；竞争抛 TestReleaseBusy（明确 busy，不改 cache）。"""
    try:
        return lock.acquire(root, exclusive=exclusive)
    except lock.Busy as exc:
        raise TestReleaseBusy(str(exc)) from exc
    except lock.LockError as exc:
        raise TestReleaseError(str(exc)) from exc


def release_lock(fd):
    lock.release(fd)


def verify_lease(root=None):
    """祖先进程仍持本 root 的独占 flock 且 mount 域一致（委托 release_lock）。"""
    try:
        return lock.verify_lease(root)
    except lock.LockError as exc:
        raise TestReleaseError(str(exc)) from exc


# ---- 原子写 / 读取 ---------------------------------------------------------


def write_json_atomic(path, payload, text=None):
    directory = os.path.dirname(path) or "."
    os.makedirs(directory, exist_ok=True)
    handle = tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=directory,
                                         prefix=".tmp-", delete=False, suffix=".json")
    try:
        handle.write(text if text is not None else json.dumps(
            payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
        handle.flush()
        os.fsync(handle.fileno())
    finally:
        handle.close()
    os.replace(handle.name, path)


def write_text_atomic(path, text):
    directory = os.path.dirname(path) or "."
    os.makedirs(directory, exist_ok=True)
    handle = tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=directory,
                                         prefix=".tmp-", delete=False)
    try:
        handle.write(text)
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


def read_text_or_none(path):
    try:
        with open(path, encoding="utf-8") as handle:
            return handle.read()
    except OSError:
        return None


def _sha256_text(text):
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


def _tree_digest_or_none(root):
    try:
        return common.tree_digest(root)
    except (OSError, common.ReleaseError):
        return None


def read_owner(root):
    owner = read_json(owner_path(root))
    return owner if isinstance(owner, dict) else None


def read_meta(root):
    meta = read_json(meta_path(root))
    return meta if isinstance(meta, dict) else None


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


# ---- 核验 ------------------------------------------------------------------


def _verify_tree_against_meta(real, meta, expected_version):
    """逐文件核实际发行树：manifest 摘要 + output tree digest（不只信 meta）。"""
    manifest_file = os.path.join(real, "wf-release.json")
    if not os.path.isfile(manifest_file):
        raise TestReleaseError(f"测试发行缺少 wf-release.json：{real}")
    manifest = read_json(manifest_file)
    if not manifest:
        raise TestReleaseError(f"测试发行清单不可解析：{manifest_file}")
    if common.manifest_digest(manifest) != meta.get("manifest_digest"):
        raise TestReleaseError("测试发行清单摘要与 meta 不一致（副本被改动）")
    if manifest.get("version") != expected_version:
        raise TestReleaseError(
            f"测试发行清单版本不一致：manifest={manifest.get('version')} expected={expected_version}")
    current = _tree_digest_or_none(real)
    if current is None:
        raise TestReleaseError(f"测试发行树不可读：{real}")
    if meta.get("output_tree_digest") != current:
        raise TestReleaseError(
            f"测试发行树摘要与 meta 不一致（实际文件被改动）：meta={meta.get('output_tree_digest')} current={current}")


def _hit_meta(real, expected_version, inputs):
    """只有 schema 2、输入与版本完全一致且实际树可验证的 meta 才算命中。"""
    meta = read_meta(real)
    if not meta or not os.path.isdir(real):
        return None
    if meta.get("schema_version") != META_SCHEMA:
        return None                      # 旧 schema 只算 miss（重建），不冒充命中
    if meta.get("version") != expected_version or meta.get("release_ref") != ref_for(expected_version):
        return None
    if meta.get("build_inputs") != inputs:
        return None
    try:
        _verify_tree_against_meta(real, meta, expected_version)
    except TestReleaseError:
        return None
    return meta


def check_meta_locked(root=None, version=None, dev_manifest=None):
    """只读核验（调用方已持共享/独占锁）：meta、inputs、实际树逐项核对。"""
    dev_manifest = dev_manifest if dev_manifest is not None else common.load_dev_manifest()
    expected_version = version or resolve_version(None, dev_manifest)
    real = check_output_root(root or default_root(expected_version))
    if os.path.isfile(journal_path(real)):
        raise TestReleaseError(
            f"未完成的发布 journal：{journal_path(real)}（recovery-required：在可获独占锁时用 --ensure 恢复）")
    if not os.path.isdir(real):
        raise TestReleaseError(f"测试发行副本不存在：{real}（重建或去掉 --no-build）")
    meta = read_meta(real)
    if not meta:
        raise TestReleaseError(f"测试发行 meta 缺失：{meta_path(real)}（重建或去掉 --no-build）")
    if meta.get("schema_version") != META_SCHEMA:
        raise TestReleaseError(
            f"测试发行 meta schema 过期：meta={meta.get('schema_version')} expected={META_SCHEMA}（重建或去掉 --no-build）")
    if meta.get("version") != expected_version:
        raise TestReleaseError(
            f"测试发行版本过期：meta={meta.get('version')} expected={expected_version}（测试发行副本过期，重建或去掉 --no-build）")
    if meta.get("release_ref") != ref_for(expected_version):
        raise TestReleaseError(
            f"测试发行引用过期：meta={meta.get('release_ref')} expected={ref_for(expected_version)}")
    current_inputs = common.test_release_inputs_digest(expected_version)
    if meta.get("build_inputs") != current_inputs:
        raise TestReleaseError(
            f"测试发行输入身份过期：meta={meta.get('build_inputs')} current={current_inputs}；"
            "测试发行副本过期，重建或去掉 --no-build")
    if meta.get("source_tree_digest") != common.source_tree_digest():
        raise TestReleaseError(
            f"测试发行源树摘要过期：meta={meta.get('source_tree_digest')}；"
            "测试发行副本过期，重建或去掉 --no-build")
    _verify_tree_against_meta(real, meta, expected_version)
    return meta


def check_meta(root=None, version=None, dev_manifest=None):
    """公开 check：共享锁内只读核验（runner 持独占消费期会明确 busy）。"""
    dev_manifest = dev_manifest if dev_manifest is not None else common.load_dev_manifest()
    version = version or resolve_version(None, dev_manifest)
    real = check_output_root(root or default_root(version))
    fd = acquire_lock(real, exclusive=False)
    try:
        return check_meta_locked(real, version, dev_manifest)
    finally:
        release_lock(fd)


# ---- journal 发布/恢复 -----------------------------------------------------


def _journal_for(real, transaction):
    return {
        "schema_version": JOURNAL_SCHEMA,
        "transaction": transaction,
        "root": real,
        "old": None,
        "new": None,
    }


def _capture_old(real):
    """冻结旧代（如实测字节与归属）；首次发布记录 old-absent。"""
    if not os.path.isdir(real) or not any(os.listdir(real)):
        return {"present": False}
    digest = _tree_digest_or_none(real)
    if digest is None:
        raise TestReleaseError(f"旧代不可读，拒绝在不可验证的旧代上发布：{real}")
    meta_text = read_text_or_none(meta_path(real))
    owner_text = read_text_or_none(owner_path(real))
    if meta_text is None or owner_text is None:
        raise TestReleaseError(f"旧代缺少 meta/owner，拒绝在不完整旧代上发布：{real}")
    return {"present": True, "digest": digest, "meta": meta_text, "owner": owner_text}


def _complete_generation(real):
    """real 是否是一份带本工具 meta/owner 且树可验证的完整代（不比对当前输入）。"""
    meta = read_meta(real)
    owner = read_owner(real)
    if not meta or not owner or owner.get("owner") != OWNER_TAG:
        return False
    if meta.get("schema_version") != META_SCHEMA:
        return False
    return _tree_digest_or_none(real) == meta.get("output_tree_digest")


def _recovery_action(real, journal):
    """恢复状态机（design §2）：按固定优先级判定，返回 (action, target)；纯判定、不写盘。

    1 `roll-forward`        新代可验证（已装到 real 或仍在 staging）→ 前滚；
    2 `rolled-back`         旧代仍在原位且字节等于 journal 冻结摘要 → 只清 staging/journal；
    3 `roll-backup`         backup 字节等于 journal 冻结旧代 → 按冻结 meta/owner 回滚；
    4 `rolled-back-absent`  首次发布：只撤销本事务的不完整新代；
    5 `fail-closed`         两代都不可验证 → 保留现场、非零退出。

    判定只用 journal 冻结的摘要与归属，不比 mtime、不看当前输入新鲜度。
    """
    new = journal.get("new") or {}
    old = journal.get("old") or {}
    digest = new.get("digest")
    if digest:
        for candidate in (real, new.get("staging")):
            if candidate and os.path.isdir(candidate) and _tree_digest_or_none(candidate) == digest:
                return "roll-forward", candidate
    if old.get("present"):
        if _tree_digest_or_none(real) == old.get("digest"):
            return "rolled-back", real
        backup = new.get("backup")
        if backup and os.path.isdir(backup) and _tree_digest_or_none(backup) == old.get("digest"):
            return "roll-backup", backup
    elif not _complete_generation(real):
        return "rolled-back-absent", real
    return "fail-closed", None


def _roll_forward(real, journal, candidate):
    new = journal.get("new") or {}
    if candidate != real:
        backup = new.get("backup")
        if os.path.isdir(real):
            if not backup:
                raise TestReleaseError("journal 缺少 backup 路径，无法安装新代")
            if os.path.isdir(backup):
                shutil.rmtree(backup)
            os.rename(real, backup)
        os.rename(candidate, real)
    if new.get("meta") is None or new.get("owner") is None:
        raise TestReleaseError("journal 缺少新代 meta/owner，无法前滚；保留现场")
    write_text_atomic(meta_path(real), new["meta"])
    write_text_atomic(owner_path(real), new["owner"])
    if _tree_digest_or_none(real) != new.get("digest"):
        raise TestReleaseError("前滚后新代仍不可验证；保留现场")
    return "rolled-forward"


def _roll_back_in_place(real, journal):
    """旧代仍在原位：按 journal 冻结的 meta/owner 原文复位，不重新序列化。"""
    old = journal.get("old") or {}
    if not old.get("meta") or not old.get("owner"):
        raise TestReleaseError("journal 缺少旧代 meta/owner，无法确认旧代原位完好；保留现场")
    write_text_atomic(meta_path(real), old["meta"])
    write_text_atomic(owner_path(real), old["owner"])
    if _tree_digest_or_none(real) != old.get("digest"):
        raise TestReleaseError("恢复后旧代仍不可验证；保留现场")
    return "rolled-back"


def _restore_from_backup(real, journal):
    """旧代已移走但 backup 可验证：按 journal 冻结的旧字节回滚。"""
    old = journal.get("old") or {}
    backup = (journal.get("new") or {}).get("backup")
    if not backup or not os.path.isdir(backup):
        raise TestReleaseError(
            f"无法恢复：journal 声明的旧代备份缺失（{backup}）；保留现场 {journal_path(real)}")
    if _tree_digest_or_none(backup) != old.get("digest"):
        raise TestReleaseError("无法恢复：旧代备份字节与 journal 不符；保留现场")
    if os.path.isdir(real):
        shutil.rmtree(real)
    os.rename(backup, real)
    write_text_atomic(meta_path(real), old["meta"])
    write_text_atomic(owner_path(real), old["owner"])
    if _tree_digest_or_none(real) != old.get("digest"):
        raise TestReleaseError("恢复后旧代仍不可验证；保留现场")
    return "rolled-back"


def _validate_journal_material_paths(real, journal):
    cache_root = os.path.dirname(real)
    base = os.path.basename(real)
    new = journal.get("new") or {}
    for field, prefix in (("staging", base + ".staging-"), ("backup", base + ".backup-")):
        value = new.get(field)
        if value is None:
            continue
        if not isinstance(value, str):
            raise TestReleaseError(f"journal {field} 越界/不符：{value!r}（保留现场）")
        canonical = os.path.realpath(value)
        root_real = os.path.realpath(cache_root)
        parent = os.path.dirname(canonical)
        direct = (parent == root_real and os.path.basename(canonical).startswith(prefix))
        nested = (os.path.dirname(parent) == root_real
                  and os.path.basename(parent).startswith(prefix))
        if not (direct or nested):
            raise TestReleaseError(f"journal {field} 路径越界/不符：{value!r}（保留现场）")


def recover_locked(real):
    """独占锁内处理未完成 journal：按 `_recovery_action` 判定前滚/回滚，返回状态字符串。"""
    journal = read_json(journal_path(real))
    if journal is None:
        raise TestReleaseError(f"journal 不可解析：{journal_path(real)}（保留现场）")
    if journal.get("schema_version") != JOURNAL_SCHEMA or journal.get("root") != real:
        raise TestReleaseError(f"journal schema/root 不符：{journal_path(real)}（保留现场）")
    _validate_journal_material_paths(real, journal)
    action, target = _recovery_action(real, journal)
    if action == "roll-forward":
        status = _roll_forward(real, journal, target)
    elif action == "rolled-back":
        status = _roll_back_in_place(real, journal)
    elif action == "roll-backup":
        status = _restore_from_backup(real, journal)
    elif action == "rolled-back-absent":
        status = _undo_first_publication(real, journal)
    else:
        raise TestReleaseError(
            "无法恢复：当前代与 journal 记录的旧代/新代均不可验证（两代都不完整）；"
            f"保留现场 {journal_path(real)}")
    _finish_transaction(real, journal)
    return status


def _publish_locked(real, version, dev_manifest, inputs):
    """独占锁内发布：冻结输入 → staging 双构建 → journal → 备份/安装 → 验证 → 提交。"""
    builder = _load_builder()
    transaction = uuid.uuid4().hex
    staging = real + f".staging-{transaction}"
    backup = real + f".backup-{transaction}"
    journal = _journal_for(real, transaction)
    journal["old"] = _capture_old(real)
    try:
        os.makedirs(os.path.dirname(real) or ".", exist_ok=True)
        for candidate in (staging, material_owner_path(staging), backup,
                          material_owner_path(backup)):
            if os.path.lexists(candidate):
                raise TestReleaseError(f"事务材料路径已存在（碰撞拒绝，不先删除）：{candidate}")
        _write_material_owner(staging, "staging", real, version, transaction)
        os.makedirs(staging)
        first = os.path.join(staging, "first")
        second = os.path.join(staging, "second")
        builder.build(version, first, dev_manifest)
        builder.build(version, second, dev_manifest)
        problems = builder.diff_tree(first, second)
        if problems:
            raise TestReleaseError(f"测试发行字节复现失败：{problems[:5]}")
        if common.test_release_inputs_digest(version) != inputs:
            raise TestReleaseError("测试发行输入在构建期间变化；拒绝把混合产物发布成稳定输入")
        built_manifest = os.path.join(first, "wf-release.json")
        manifest_on_disk = read_json(built_manifest)
        if not manifest_on_disk:
            raise TestReleaseError("测试发行缺少 wf-release.json")
        _make_tagged_repo(first, version)
        _stop("after-staging-before-journal")
        digest = common.tree_digest(first)
        previous = read_meta(real) or {}
        meta = {
            "schema_version": META_SCHEMA,
            "version": version,
            "release_ref": ref_for(version),
            "build_inputs": inputs,
            "output_tree_digest": digest,
            "manifest_digest": common.manifest_digest(manifest_on_disk),
            "source_tree_digest": common.source_tree_digest(),
            "built_at": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
            "root": real,
            # 累计构建次数（additive 诊断字段，读取方不依赖）：首建=1，同输入复用不增。
            "builds": int(previous.get("builds") or 0) + 1,
        }
        owner = {"schema_version": 1, "owner": OWNER_TAG, "root": real, "version": version}
        journal["new"] = {
            "digest": digest,
            "staging": first,
            "backup": backup,
            "meta": json.dumps(meta, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            "owner": json.dumps(owner, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        }
        write_json_atomic(journal_path(real), journal)
        _stop("after-journal")
        if os.path.isdir(real):
            _write_material_owner(backup, "backup", real, version, transaction)
            os.rename(real, backup)
            _stop("after-old-moved")
        os.rename(first, real)
        _stop("after-new-installed")
        shutil.rmtree(second, ignore_errors=True)
        write_text_atomic(meta_path(real), journal["new"]["meta"])
        write_text_atomic(owner_path(real), journal["new"]["owner"])
        if common.tree_digest(real) != digest:
            raise TestReleaseError("发布后发行树字节与冻结摘要不符")
        _verify_tree_against_meta(real, meta, version)
        _stop("after-meta")
        _finish_transaction(real, journal)
        os.environ.pop(REBUILD_ENV, None)
        return real, meta
    except Exception:
        # 尽力立即回滚；回滚不了就保留 journal 现场（下次 ensure 先恢复）。
        try:
            if os.path.isfile(journal_path(real)):
                recover_locked(real)
            else:
                shutil.rmtree(staging, ignore_errors=True)
        except TestReleaseError:
            pass
        raise


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


def ensure_release_locked(root=None, version=None, dev_manifest=None, rebuild=True):
    """独占锁内确保缓存根有一份与当前输入一致的测试发行。

    返回 `(root, meta, status)`；status 是 `built`（本次构建）或 `reused`（命中或只核验），
    供 `--json` 与 summary 的成本账目使用（不改变门禁语义）。
    """
    dev_manifest = dev_manifest if dev_manifest is not None else common.load_dev_manifest()
    version = version or resolve_version(None, dev_manifest)
    validate_checkpoint()
    real = check_output_root(root or default_root(version))
    if os.path.isfile(journal_path(real)):
        status = recover_locked(real)
        print(f"TEST-RELEASE-RECOVERED: {status}", file=sys.stderr)
    if not rebuild:
        return real, check_meta_locked(real, version, dev_manifest), "reused"
    inputs = common.test_release_inputs_digest(version)
    hit = _hit_meta(real, version, inputs)
    if hit is not None and not _rebuild_requested():
        return real, hit, "reused"
    if hit is not None:
        print("TEST-RELEASE-REBUILD-INJECTED: 跳过本次命中，仍走真实 build/journal/move",
              file=sys.stderr)
    _assert_owned_or_empty(real)
    root, meta = _publish_locked(real, version, dev_manifest, inputs)
    return root, meta, "built"


def ensure_release_status(root=None, version=None, dev_manifest=None, rebuild=True):
    """公开 ensure（含构建状态 `built|reused`）；竞争明确 busy。"""
    dev_manifest = dev_manifest if dev_manifest is not None else common.load_dev_manifest()
    version = version or resolve_version(None, dev_manifest)
    real = check_output_root(root or default_root(version))
    fd = acquire_lock(real, exclusive=True)
    try:
        return ensure_release_locked(real, version, dev_manifest, rebuild)
    finally:
        release_lock(fd)


def ensure_release(root=None, version=None, dev_manifest=None, rebuild=True):
    """公开 ensure：返回 `(root, meta)`（构建状态见 `ensure_release_status`）。"""
    root, meta, _status = ensure_release_status(root, version, dev_manifest, rebuild)
    return root, meta


# ---- runner 消费期 lease ---------------------------------------------------


def lease_run(root, version, command, rebuild=True, dev_manifest=None):
    """同一 PID 取得并保持独占 fd，`exec` 进入最终消费阶段（不释放、不重取、不降级）。"""
    dev_manifest = dev_manifest if dev_manifest is not None else common.load_dev_manifest()
    real = check_output_root(root)
    fd = acquire_lock(real, exclusive=True)
    ensure_release_locked(real, version, dev_manifest, rebuild)
    lock.write_env(fd, real)
    os.execvp(command[0], command)


def _print_error(exc):
    if isinstance(exc, TestReleaseBusy):
        print(f"BUSY  {exc}", file=sys.stderr)
        return BUSY_EXIT
    print(f"FAIL  {exc}", file=sys.stderr)
    return 1


def main(argv=None):
    parser = argparse.ArgumentParser(description="wf 测试发行构建（缓存根，不写产品树）")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--ensure", action="store_true", help="构建/复用缓存根里的测试发行")
    group.add_argument("--check", action="store_true", help="只核对 meta 与当前输入（共享锁）")
    group.add_argument("--lease", action="store_true", help="持独占锁后 exec 进入消费命令")
    group.add_argument("--verify-lease", action="store_true", help="核验继承来的消费期 lease")
    group.add_argument("--inventory", action="store_true", help="只读盘点测试发行缓存根")
    group.add_argument("--retire", action="store_true", help="按 selection 精确退役材料（需报告）")
    parser.add_argument("--version", default=None, help="X.Y.Z（默认按 dev-manifest/测试常量解析）")
    parser.add_argument("--root", default=None, help="输出根（默认 ~/.cache/wf-test-release/<version>）")
    parser.add_argument("--no-build", action="store_true", help="--lease 时不重建，只做新鲜度核验")
    parser.add_argument("--no-lock", action="store_true",
                        help="调用方已持同一把 root 锁（locked 实现不加锁，不自撞）")
    parser.add_argument("--json", action="store_true", help="输出机器可读结果")
    parser.add_argument("--cache-root", default=None)
    parser.add_argument("--selection", default=None)
    parser.add_argument("--retirement-mode", choices=lifecycle.RETIREMENT_MODES, default=None)
    parser.add_argument("--confirm-retirement", action="store_true")
    parser.add_argument("--report", default=None)
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args(argv)
    try:
        if args.verify_lease:
            verify_lease(args.root)
            print("OK  lease", flush=True)
            return 0
        if args.inventory:
            if not args.cache_root:
                parser.error("--inventory requires --cache-root")
            report = inventory(args.cache_root)
            print(json.dumps(report, ensure_ascii=False, sort_keys=True))
            return 0 if report.get("status") in ("complete", "absent") else 1
        if args.retire:
            if not args.cache_root or not args.selection or not args.retirement_mode \
                    or not args.confirm_retirement or not args.report:
                parser.error("--retire requires --cache-root/--selection/--retirement-mode/"
                             "--confirm-retirement/--report")
            return retire(args)
        dev_manifest = common.load_dev_manifest()
        version = resolve_version(args.version, dev_manifest)
        root = check_output_root(args.root or default_root(version))
        if args.lease:
            command = args.command[1:] if args.command[:1] == ["--"] else args.command
            if not command:
                parser.error("--lease requires a command after --")
            lease_run(root, version, command, rebuild=not args.no_build, dev_manifest=dev_manifest)
            return 0
        if args.no_lock:
            # 调用方声称持同一把 root 锁：先证真实持锁租约，再走 locked 实现（不重复开锁）。
            # 没有可核验的租约就拒绝——`--no-lock` 不是“绕过锁”的开关。
            try:
                lock.verify_lease(root)
            except lock.LockError as exc:
                raise TestReleaseError(
                    f"--no-lock 需要同根独占消费租约：{exc}") from exc
            if args.check:
                meta = check_meta_locked(root, version, dev_manifest)
                status = "checked"
            else:
                root, meta, status = ensure_release_locked(root, version, dev_manifest)
        elif args.check:
            meta = check_meta(root, version, dev_manifest)
            status = "checked"
        else:
            root, meta, status = ensure_release_status(root, version, dev_manifest)
        if args.json:
            print(json.dumps({"status": status, "root": root, "version": meta["version"],
                              "release_ref": meta["release_ref"],
                              "builds": meta.get("builds"),
                              "build_inputs": meta.get("build_inputs"),
                              "output_tree_digest": meta.get("output_tree_digest")},
                             ensure_ascii=False, sort_keys=True))
        else:
            label = {"built": "BUILT", "reused": "REUSED", "checked": "OK"}[status]
            print(f"{label}  test-release {meta['version']}  {root}")
            print(f"  release_ref: {meta['release_ref']}")
            print(f"  build_inputs: {meta.get('build_inputs')}")
        return 0
    except TestReleaseError as exc:
        return _print_error(exc)
    except (common.ReleaseError, SystemExit) as exc:  # build() 的版本一致性拒绝
        print(f"FAIL  {exc}", file=sys.stderr)
        return 1


# ---- C3：材料归属、确定性窗口与维护入口（父任务 design §5/§5.1/§4.2）-----------

MATERIAL_TAG = "wf-test-release-material"
MATERIAL_SCHEMA = 1
TXN_STOP_ENV = "WF_TEST_RELEASE_TXN_STOP_AFTER"
FAULT_SWITCH = "WF_TEST_FAULT_INJECTION"
CHECKPOINTS = ("after-staging-before-journal", "after-journal", "after-old-moved",
               "after-new-installed", "after-meta",
               "after-material-cleanup-before-journal-remove")

def material_owner_path(material):
    return os.path.abspath(material) + ".owner"


def _owned_scope():
    try:
        return wf_test_paths.current_scope() is not None
    except wf_test_paths.PathError:
        return False


def _faults():
    return os.environ.get(FAULT_SWITCH) == "1"


REBUILD_ENV = "WF_TEST_RELEASE_TXN_REBUILD"


def _rebuild_requested():
    return _faults() and os.environ.get(REBUILD_ENV) == "1" and _owned_scope()


def validate_checkpoint():
    requested = os.environ.get(TXN_STOP_ENV)
    if not requested:
        return None
    if not _faults():
        raise TestReleaseError(f"{TXN_STOP_ENV} 只在 {FAULT_SWITCH}=1 时生效")
    if requested not in CHECKPOINTS:
        raise TestReleaseError(f"未知测试发行 checkpoint：{requested!r}")
    if not _owned_scope():
        raise TestReleaseError("测试发行 checkpoint 需要有效 owned test scope")
    return requested


def _stop(point):
    if os.environ.get(TXN_STOP_ENV) != point:
        return
    sys.stderr.write(f"WF-TEST-RELEASE-TXN-STOP: {point} pid={os.getpid()}\n")
    sys.stderr.flush()
    sys.stdout.flush()
    os._exit(97)


def _write_material_owner(material, kind, real, version, transaction):
    payload = {"schema_version": MATERIAL_SCHEMA, "owner": MATERIAL_TAG,
               "material_root": os.path.realpath(material),
               "entry_root": os.path.realpath(real), "version": version,
               "transaction": transaction, "kind": kind, "uid": os.getuid()}
    path = material_owner_path(material)
    if os.path.lexists(path):
        raise TestReleaseError(f"材料 marker 已存在（碰撞拒绝）：{path}")
    write_text_atomic(path, json.dumps(payload, ensure_ascii=False, indent=2,
                                       sort_keys=True) + "\n")


def read_material_owner(material):
    try:
        with open(material_owner_path(material), encoding="utf-8") as handle:
            return json.load(handle)
    except (OSError, ValueError):
        return None


def material_owner_matches(material, kind, real):
    record = read_material_owner(material)
    if not record or record.get("schema_version") != MATERIAL_SCHEMA or \
            record.get("owner") != MATERIAL_TAG or record.get("kind") != kind:
        return False
    if record.get("material_root") != os.path.realpath(material):
        return False
    if record.get("entry_root") != os.path.realpath(real):
        return False
    try:
        return os.stat(material).st_uid == os.getuid()
    except OSError:
        return os.path.exists(material_owner_path(material))


def _strict_remove(path):
    if not path or not os.path.lexists(path):
        return
    if os.path.islink(path) or os.path.isfile(path):
        os.unlink(path)
    else:
        shutil.rmtree(path)
    if os.path.lexists(path):
        raise TestReleaseError(f"材料删除失败，保留现场：{path}")


def _remove_material_tree(material):
    _strict_remove(material)
    _strict_remove(material_owner_path(material))


def _finish_transaction(real, journal):
    """材料/ marker 确认清理后才删 journal；失败保留 journal 以便再次收尾。"""
    new = journal.get("new") or {}
    staging = new.get("staging")
    for path in (staging, new.get("backup")):
        if path and os.path.lexists(path):
            try:
                _remove_material_tree(path)
            except (OSError, TestReleaseError) as exc:
                raise TestReleaseError(f"事务材料未清理：{path}: {exc}") from exc
    parent = os.path.dirname(staging) if staging else ""
    if parent and os.path.basename(parent).startswith(os.path.basename(real) + ".staging-"):
        try:
            _strict_remove(material_owner_path(parent))
            _strict_remove(parent)
        except (OSError, TestReleaseError) as exc:
            raise TestReleaseError(f"staging 父目录/材料 marker 未清理：{parent}: {exc}") from exc
    _stop("after-material-cleanup-before-journal-remove")
    try:
        os.unlink(journal_path(real))
    except FileNotFoundError:
        pass
    except OSError as exc:
        raise TestReleaseError(f"journal 删除失败（材料已清，可重试收尾）：{exc}") from exc


def _undo_first_publication(real, journal):
    new = journal.get("new") or {}
    for path in (new.get("staging"), new.get("backup"), real):
        if path and os.path.lexists(path):
            try:
                _remove_material_tree(path)
            except (OSError, TestReleaseError) as exc:
                raise TestReleaseError(f"撤销首次发布失败，保留 journal：{path}: {exc}") from exc
    return "rolled-back-absent"


# ---- inventory / observe ----------------------------------------------------


def _material_kind(name, real):
    base = os.path.basename(real)
    if name.startswith(base + ".staging-"):
        return "release-staging"
    if name.startswith(base + ".backup-"):
        return "release-backup"
    if name.startswith(base + ".stale-") or name.endswith(".build"):
        return "release-stale"
    return None


def inventory(cache_root):
    root = os.path.realpath(os.path.abspath(cache_root))
    entries, unknown = [], []
    try:
        names = sorted(os.listdir(root))
    except FileNotFoundError:
        return {"schema_version": 1, "domain": "test-release-cache", "root": root,
                "status": "absent", "entries": [], "unknown": []}
    except OSError as exc:
        return {"schema_version": 1, "domain": "test-release-cache", "root": root,
                "status": "partial", "error": str(exc), "entries": [], "unknown": []}
    import re
    for name in names:
        path = os.path.join(root, name)
        if os.path.islink(path):
            unknown.append({"path": path, "reason": "symlink（不跟随）"})
            continue
        if name.endswith(".lock"):
            continue  # 固定 .lock 永不作为清单对象
        if name.endswith(".journal.json"):
            real = path[:-len(".journal.json")]
            journal = read_json(path)
            blocked = "journal-active"
            if journal is None:
                blocked = "journal unreadable（需完整 key reset）"
            entries.append({"root": root, "path": path, "kind": "journal",
                            "key": os.path.realpath(real),
                            "provenance": "owned", "blocked": blocked,
                            "uid": os.stat(path).st_uid,
                            "digest": "sha256:" + hashlib.sha256(Path(path).read_bytes()).hexdigest()})
            continue
        if name.endswith((".meta.json", ".owner")):
            continue  # 附属记录：随所属 entry/材料处置
        material = re.match(r"^(?P<version>\d+\.\d+\.\d+)\.(?P<kind>staging|backup|stale)-", name)
        if material or name.endswith(".build"):
            kind = ("release-build" if name.endswith(".build") else
                    "release-" + (material.group("kind") if material else "stale"))
            version = material.group("version") if material else (
                name[:-len(".build")] if name.endswith(".build") else "")
            entry_root = os.path.join(root, version)
            owned = material_owner_matches(path, "staging" if kind == "release-staging" else (
                "backup" if kind == "release-backup" else "staging"), entry_root)
            entries.append({"root": root, "path": path, "kind": kind,
                            "key": os.path.realpath(entry_root),
                            "provenance": "owned" if owned else "unproven",
                            "blocked": None, "uid": os.stat(path).st_uid
                            if os.path.exists(path) else None,
                            "digest": _tree_digest_or_none(path),
                            "marker": material_owner_path(path) if os.path.exists(
                                material_owner_path(path)) else None})
            continue
        if not os.path.isdir(path):
            unknown.append({"path": path, "reason": "未知文件"})
            continue
        real = path
        key = os.path.basename(real)
        journal = read_json(journal_path(real))
        if journal is not None:
            provenance, blocked = "owned", "journal-active（先 ensure 恢复）"
        else:
            meta = read_json(meta_path(real))
            owner = read_owner(real)
            if meta and owner and owner.get("owner") == OWNER_TAG and \
                    meta.get("schema_version") == META_SCHEMA and \
                    meta.get("root") == real and \
                    _tree_digest_or_none(real) == meta.get("output_tree_digest"):
                provenance, blocked = "owned", None
            else:
                provenance, blocked = "unknown-entry", "meta/owner/树不可验证"
        entries.append({"root": root, "path": real, "kind": "release-entry",
                        "key": os.path.realpath(real),
                        "provenance": provenance, "blocked": blocked,
                        "uid": os.stat(path).st_uid, "digest": _tree_digest_or_none(path)})
    status = "partial" if unknown or any(item.get("blocked") for item in entries) else "complete"
    return {"schema_version": 1, "domain": "test-release-cache", "root": root,
            "status": status, "entries": entries, "unknown": unknown,
            "capacity": "not-measured"}


def _read_control(path):
    try:
        if os.path.islink(path) or os.path.getsize(path) > 1024 * 1024:
            return None
    except OSError:
        return None
    return read_json(path)


def observe(cache_root):
    """root 维护前的浅层观察：只读直接子项/控制记录，不递归、不算树摘要。"""
    root = os.path.realpath(os.path.abspath(cache_root))
    observed_at = datetime.datetime.now().astimezone().isoformat(timespec="seconds")
    if not os.path.exists(root):
        return {"root": root, "status": "absent", "counts": {}, "capacity": "not-measured",
                "observed_at": observed_at,
                "inventory_hint": f"python3 {os.path.abspath(__file__)} --inventory "
                                  f"--cache-root {root} --json"}
    counts, unverified, unknown = {}, [], []
    try:
        names = sorted(os.listdir(root))
    except OSError as exc:
        return {"root": root, "status": "unverified", "counts": {}, "error": str(exc),
                "capacity": "not-measured", "observed_at": observed_at,
                "inventory_hint": f"python3 {os.path.abspath(__file__)} --inventory "
                                  f"--cache-root {root} --json"}
    import re
    for name in names:
        path = os.path.join(root, name)
        if os.path.islink(path):
            unverified.append(name)
            continue
        if name.endswith(".lock"):
            continue
        if name.endswith(".journal.json"):
            journal = _read_control(path)
            counts["journal"] = counts.get("journal", 0) + 1
            counts["recovery-required"] = counts.get("recovery-required", 0) + 1
            continue
        if name.endswith((".meta.json", ".owner")):
            continue
        if re.match(r"^\d+\.\d+\.\d+\.(staging|backup|stale)-", name) or name.endswith(".build"):
            counts["orphan-like"] = counts.get("orphan-like", 0) + 1
            if not os.path.exists(material_owner_path(path)):
                counts["unproven"] = counts.get("unproven", 0) + 1
            continue
        if not os.path.isdir(path):
            counts["unknown"] = counts.get("unknown", 0) + 1
            continue
        journal = _read_control(journal_path(path))
        if journal is not None:
            counts["recovery-required"] = counts.get("recovery-required", 0) + 1
            continue
        meta = _read_control(meta_path(path))
        owner = read_owner(path)
        if meta is not None and owner is not None and owner.get("owner") == OWNER_TAG and \
                meta.get("schema_version") == META_SCHEMA:
            counts["valid"] = counts.get("valid", 0) + 1
        else:
            counts["unknown"] = counts.get("unknown", 0) + 1
    status = "partial" if unverified or counts.get("unknown") or counts.get("recovery-required") \
        else "complete"
    return {"root": root, "status": status, "counts": counts,
            "unverified": unverified, "capacity": "not-measured",
            "observed_at": observed_at,
            "inventory_hint": f"python3 {os.path.abspath(__file__)} --inventory "
                              f"--cache-root {root} --json"}


# ---- retire -----------------------------------------------------------------


def _guard_locks():
    inherited = os.environ.get("WF_TEST_RELEASE_LEASE_FD")
    if inherited:
        verify_lease()
        return
    root = os.environ.get("WF_RETIRE_LOCK_ROOT") or CACHE_ROOT
    path = os.path.join(root, ".maintenance.lock")
    os.makedirs(root, exist_ok=True)
    fd = os.open(path, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError as exc:
        os.close(fd)
        raise TestReleaseError("测试发行为维护忙：另一个进程持有维护锁") from exc
    finally:
        try:
            fcntl.flock(fd, fcntl.LOCK_UN)
            os.close(fd)
        except OSError:
            pass


def _delete_release_entry(item):
    path = item["path"]
    if item["kind"] == "journal":
        os.unlink(path)
        return
    if os.path.islink(path) or os.path.isfile(path):
        os.unlink(path)
        return
    _remove_material_tree(path)
    # entry 的正式 meta/owner 与材料 marker 一并清除；journal 最后删。
    for sidecar in (meta_path(path), owner_path(path), material_owner_path(path)):
        _strict_remove(sidecar)


def _selection_order(entries):
    order = {"release-staging": 0, "release-backup": 0, "release-stale": 0,
             "release-build": 0, "release-entry": 1, "journal": 2}
    return sorted(entries, key=lambda item: order.get(item["kind"], 1))


def _require_in_scope(path):
    scope = os.environ.get("WF_TEST_SCOPE_ROOT")
    if scope:
        import fixture_scope
        fixture_scope.ensure_in_scope(Path(path))


def retire(args):
    cache_root = os.path.realpath(os.path.abspath(args.cache_root))
    _require_in_scope(args.selection)
    _require_in_scope(args.report)
    document = read_json(args.selection)
    if document is None:
        raise TestReleaseError(f"selection 不可读：{args.selection}")
    selected = lifecycle.selection_entries(document, "test-release-cache")
    current = {os.path.realpath(item["path"]): item
               for item in inventory(cache_root)["entries"]}
    chosen = []
    for item in selected:
        found = current.get(os.path.realpath(item["path"]))
        if found is None or found["kind"] != item["kind"]:
            raise TestReleaseError(f"selection 项不存在/漂移：{item['path']}")
        if item.get("provenance") and found.get("provenance") != item["provenance"]:
            raise TestReleaseError(f"selection provenance 漂移：{item['path']}")
        if found.get("blocked") == "journal-active" and found["kind"] != "journal":
            raise TestReleaseError(f"journal 未收尾，必须先 ensure 恢复：{item['path']}")
        chosen.append(found)
    for item in chosen:
        live = lifecycle.live_references(item["path"])
        if live:
            raise TestReleaseError(f"存在活引用（{live[0]['pid']}）拒绝删除：{item['path']}")
    selected = {os.path.realpath(item["path"]) for item in chosen}
    for key in {item.get("key") for item in chosen if item["kind"] == "journal"}:
        group = [item for item in current.values() if item.get("key") == key]
        missing = sorted(item["path"] for item in group
                         if os.path.realpath(item["path"]) not in selected)
        if missing:
            raise TestReleaseError(f"cache key 重置集合不完整（缺 {missing}）；不得只删 journal")
    if args.retirement_mode == "safe-legacy":
        for item in chosen:
            if item["kind"] in ("release-entry", "journal"):
                raise TestReleaseError(f"safe-legacy 不能退役正式代/journal：{item['path']}")
            if item.get("provenance") != "owned":
                raise TestReleaseError(f"safe-legacy 只接受可验证材料 marker：{item['path']}")
    os.environ["WF_RETIRE_LOCK_ROOT"] = cache_root
    try:
        report = lifecycle.execute_retirement(
            "test-release-cache", cache_root, _selection_order(chosen),
            args.retirement_mode, args.report, _delete_release_entry, _guard_locks, True)
    finally:
        os.environ.pop("WF_RETIRE_LOCK_ROOT", None)
    print(json.dumps({"state": "retired", "mode": args.retirement_mode,
                      "report": os.path.abspath(args.report),
                      "entries": len(report["results"])}, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
