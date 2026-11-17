#!/usr/bin/env python3
"""template_cache.py — 夹具模板的跨 run 缓存（输入身份、单槽、journal 发布与恢复）。

契约（design §3.2–§3.3 / AC1、AC2、AC4）：
- 条目名 = `<inputs_digest12>-<slot>`；slot 是 Python major.minor + deploy（candidate 再加 version/ref）。
  完整输入身份在 meta（schema 1）：资产/runner/helper 字节、tool 与 SUT 身份、dev 完整 HEAD 或候选
  release subject。dirty 变化必须 miss，纯 touch 不复建；
- 条目必须带 meta 与所有权 marker，`meta.root == realpath(条目)`、空态/身份校验通过、零 pyc；
  命中还要逐项核 build inputs 与实际 tree digest；
- 发布与恢复走有界 journal（staging → journal → backup/安装 → repoint/meta → 验证 → 提交）；
  中断后先恢复：新代可验证则前滚，否则按冻结旧代回滚；两代都不可验证时 fail closed 保留现场；
- 只迁移同一 Python/deploy/release 槽位、owner/root/身份字段完整匹配的 legacy key；其他版本、
  无主与归属不明目录不自动删除；
- 空态/身份校验、repoint 计数与 hygiene 判据仍由 `template_check.py` / `source_hygiene.py` 唯一实现。
"""
from __future__ import annotations

import argparse
import datetime
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import uuid
from pathlib import Path

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(REPO, "scripts"))
sys.path.insert(0, HERE)

import wf_release_common as common  # noqa: E402
import fixture_scope  # noqa: E402
import resource_lifecycle as lifecycle  # noqa: E402

META_SCHEMA = 1
JOURNAL_SCHEMA = 1
PY = os.environ.get("PY") or sys.executable


class CacheError(Exception):
    """可预期的拒绝（非零退出）。"""


def version_ref(args):
    if args.deploy == "candidate":
        if not args.version or not args.ref:
            raise CacheError("candidate 模板需要 --version/--ref")
        return args.version, args.ref
    return None, None


def inputs_digest(args):
    subject = args.subject or ""
    if args.deploy == "candidate" and not subject:
        subject = common.release_subject(args.release_root, args.version, args.ref)["digest"]
    return common.fixture_template_inputs_digest(args.deploy, args.version, args.ref, subject)


def key_for(args, inputs):
    version, ref = version_ref(args)
    pyver = f"{sys.version_info[0]}.{sys.version_info[1]}"
    return common.template_cache_key(inputs, pyver, args.deploy, version, ref)


def meta_path(entry):
    return entry + ".meta.json"


def journal_path(cache_root, key):
    return os.path.join(cache_root, key + ".journal.json")


def _sha(value):
    import hashlib

    return "sha256:" + hashlib.sha256(value.encode("utf-8")).hexdigest()


def _write_json(path, payload, text=None):
    directory = os.path.dirname(path) or "."
    handle = tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=directory, prefix=".tmp-",
                                         delete=False, suffix=".json")
    try:
        handle.write(text if text is not None else json.dumps(
            payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
        handle.flush()
        os.fsync(handle.fileno())
    finally:
        handle.close()
    os.replace(handle.name, path)


def _read_json(path):
    try:
        with open(path, encoding="utf-8") as handle:
            return json.load(handle)
    except (OSError, ValueError):
        return None


def _read_text(path):
    try:
        with open(path, encoding="utf-8") as handle:
            return handle.read()
    except OSError:
        return None


def _tree(entry):
    try:
        return common.tree_digest(entry)
    except (OSError, common.ReleaseError):
        return None


def _check_identity(entry, args):
    version, ref = version_ref(args)
    command = [PY, os.path.join(HERE, "template_check.py"), entry, "--quiet"]
    if version:
        command += ["--version", version, "--ref", ref]
    check = subprocess.run(command, capture_output=True, text=True)
    if check.returncode != 0:
        return f"空态/安装身份校验失败：{check.stderr.strip()[:200]}"
    hygiene = subprocess.run([PY, os.path.join(HERE, "source_hygiene.py"), "check", "--strict", entry],
                             capture_output=True, text=True)
    if hygiene.returncode != 0:
        return "条目内含字节码产物（strict 判脏）"
    return None


def _valid_meta(entry, key, inputs):
    meta = _read_json(meta_path(entry))
    if not meta or meta.get("schema_version") != META_SCHEMA:
        return "缺少 schema 1 meta（没有 meta 的条目一律无效）", None
    if meta.get("key") != key:
        return f"meta key 不符：{meta.get('key')}", None
    if meta.get("root") != os.path.realpath(entry):
        return "meta.root 与条目 realpath 不一致（缓存根被移动/条目被拷贝）", None
    if meta.get("inputs_digest") != inputs:
        return "meta 输入身份与当前输入不符", None
    actual = _tree(entry)
    if actual is None:
        return "条目不可读", None
    if meta.get("output_tree_digest") != actual:
        return "条目 tree digest 与 meta 不符（内容被改动）", None
    return None, meta


def lookup(args):
    """只读查找：发现未完成 journal 时拒绝（不恢复、不写）；miss 返回 10。"""
    inputs = inputs_digest(args)
    key = key_for(args, inputs)
    entry = os.path.join(args.cache_root, key)
    if os.path.isfile(journal_path(args.cache_root, key)):
        print(f"TEMPLATE-CACHE-RECOVERY-REQUIRED: {journal_path(args.cache_root, key)}"
              "（用 acquire 在独占锁下恢复；只读 lookup 不写）", file=sys.stderr)
        return 10
    if not os.path.isdir(entry):
        print(f"TEMPLATE-CACHE-MISS: 条目不存在 {entry}", file=sys.stderr)
        return 10
    reason, meta = _valid_meta(entry, key, inputs)
    if reason is None:
        reason = _check_identity(entry, args)
    if reason:
        print(f"TEMPLATE-CACHE-INVALID: {reason}", file=sys.stderr)
        return 10
    print(os.path.realpath(entry))
    print(key)
    print(meta["inputs_digest"])
    return 0


def _legacy_slot_of(name):
    """旧 key：`<digest12>-<pyver>-<deploy>[-<version>-<ref sanitized>]`（无法则返回 None）。"""
    match = re.fullmatch(r"[0-9a-f]{12}-(?P<py>\d+\.\d+)-(?P<deploy>dev|candidate)"
                         r"(?:-(?P<version>[^-]+)-(?P<ref>.+))?", name)
    if not match:
        return None
    return match.groupdict()


def migrate(args):
    """CLI 投影：迁移后打印 key（acquire 使用不打印的 `_migrate`，避免污染其 4 行输出）。"""
    print(_migrate(args))
    return 0


def _migrate(args):
    """只在同一 Python/deploy/release 槽位、owner/root/身份完整匹配时把 legacy key 改名到新 key。"""
    inputs = inputs_digest(args)
    key = key_for(args, inputs)
    target = os.path.join(args.cache_root, key)
    if os.path.exists(target):
        return key
    pyver = f"{sys.version_info[0]}.{sys.version_info[1]}"
    version, ref = version_ref(args)
    candidates = []
    for name in sorted(os.listdir(args.cache_root)):
        slot = _legacy_slot_of(name)
        if not slot or slot["py"] != pyver or slot["deploy"] != args.deploy:
            continue
        if args.deploy == "candidate":
            if slot["version"] != version:
                continue
            # 旧 key 用过“非 [A-Za-z0-9._-] 折叠为 '-'”的 sanitize：比较规范化后的 ref。
            sanitized = re.sub(r"[^A-Za-z0-9._-]+", "-", ref or "").strip("-")
            if slot["ref"] != sanitized:
                continue
        entry = os.path.join(args.cache_root, name)
        if not os.path.isdir(entry):
            continue
        meta = _read_json(meta_path(entry))
        if not meta or meta.get("deploy") != args.deploy or meta.get("pyver") != pyver:
            continue
        if meta.get("root") != os.path.realpath(entry) or not os.path.isfile(
                fixture_scope.marker(fixture_scope.Path(entry))):
            continue
        if args.deploy == "candidate" and (meta.get("version") != version or meta.get("ref") != ref):
            continue
        candidates.append(entry)
    if not candidates:
        return key
    source = candidates[0]
    fixture_scope.move(source, target)
    os.rename(meta_path(source), meta_path(target))
    return key


def _build(args, staging):
    fixture_scope.reset(staging)
    log = os.path.join(args.results_dir, "template.out")
    os.makedirs(args.results_dir, exist_ok=True)
    environment = {**os.environ, "WF_FIX": staging}
    steps = [[os.environ.get("BASH", "bash"), os.path.join(HERE, "wf_fixture.sh"), staging,
              "--deploy", args.deploy]]
    if args.deploy == "candidate":
        steps[0] += ["--release-root", args.release_root, "--release-ref", args.ref,
                     "--release-version", args.version]
    steps.append([PY, os.path.join(HERE, "f1_init.py")])
    with open(log, "a", encoding="utf-8") as stream:
        for step in steps:
            completed = subprocess.run(step, env=environment, capture_output=True, text=True)
            stream.write("$ " + " ".join(step) + "\n" + completed.stdout + completed.stderr)
            if completed.returncode != 0:
                raise CacheError(f"模板构建失败：{step[0]}（见 {log}）")


def _capture_old(entry):
    if not os.path.isdir(entry):
        return {"present": False}
    digest = _tree(entry)
    meta_text = _read_text(meta_path(entry))
    if digest is None or meta_text is None:
        raise CacheError(f"旧条目不可验证，拒绝在其上发布：{entry}")
    return {"present": True, "digest": digest, "meta": meta_text}


def _complete_entry(entry):
    """entry 是否是一份带完整 meta/root 且树可验证的条目（不比对当前输入/身份）。"""
    meta = _read_json(meta_path(entry))
    if not meta or meta.get("schema_version") != META_SCHEMA or meta.get("root") != os.path.realpath(entry):
        return False
    return _tree(entry) == meta.get("output_tree_digest")


def _recovery_action(entry, journal):
    """恢复状态机（design §2，与测试发行 cache 同形）：返回 (action, target)，纯判定。

    1 `roll-forward`        新代可验证（已装到 entry 或仍在 staging）→ 前滚；
    2 `rolled-back`         旧条目仍在原位且字节等于 journal 冻结摘要 → 只清 staging/journal；
    3 `roll-backup`         backup 字节等于 journal 冻结旧代 → 按冻结 meta 回滚；
    4 `rolled-back-absent`  首次发布：只撤销本事务的不完整新代；
    5 `fail-closed`         两代都不可验证 → 保留现场、非零退出。
    """
    new = journal.get("new") or {}
    old = journal.get("old") or {}
    digest = new.get("digest")
    if digest:
        for candidate in (entry, new.get("staging")):
            if candidate and os.path.isdir(candidate) and _tree(candidate) == digest:
                return "roll-forward", candidate
    if old.get("present"):
        if _tree(entry) == old.get("digest"):
            return "rolled-back", entry
        backup = new.get("backup")
        if backup and os.path.isdir(backup) and _tree(backup) == old.get("digest"):
            return "roll-backup", backup
    elif not _complete_entry(entry):
        return "rolled-back-absent", entry
    return "fail-closed", None


def _roll_forward(entry, journal, candidate):
    new = journal.get("new") or {}
    if candidate != entry:
        backup = new.get("backup")
        if os.path.isdir(entry):
            if not backup:
                raise CacheError("journal 缺少 backup 路径")
            if os.path.isdir(backup):
                shutil.rmtree(backup)
            os.rename(entry, backup)
        os.rename(candidate, entry)
    if new.get("meta") is None:
        raise CacheError("journal 缺少新条目 meta，无法前滚（保留现场）")
    _write_json(meta_path(entry), None, new["meta"])
    if _tree(entry) != new.get("digest"):
        raise CacheError("前滚后条目仍不可验证（保留现场）")
    return "rolled-forward"


def _roll_back_in_place(entry, journal):
    """旧条目仍在原位：按 journal 冻结的 meta 原文复位，不重新序列化。"""
    old = journal.get("old") or {}
    if not old.get("meta"):
        raise CacheError("journal 缺少旧条目 meta，无法确认旧条目原位完好（保留现场）")
    _write_json(meta_path(entry), None, old["meta"])
    if _tree(entry) != old.get("digest"):
        raise CacheError("恢复后旧条目仍不可验证（保留现场）")
    return "rolled-back"


def _restore_from_backup(entry, journal, path):
    old = journal.get("old") or {}
    backup = (journal.get("new") or {}).get("backup")
    if not backup or not os.path.isdir(backup):
        raise CacheError(f"无法恢复：旧条目备份缺失（保留 {path}）")
    if _tree(backup) != old.get("digest"):
        raise CacheError(f"无法恢复：旧条目备份字节不符（保留 {path}）")
    if os.path.isdir(entry):
        shutil.rmtree(entry)
    os.rename(backup, entry)
    _write_json(meta_path(entry), None, old["meta"])
    if _tree(entry) != old.get("digest"):
        raise CacheError("恢复后旧条目仍不可验证（保留现场）")
    return "rolled-back"


def _undo_first_publication(entry, journal):
    """首次发布：只撤销本事务的不完整新代（staging/backup/不完整的 entry）。"""
    new = journal.get("new") or {}
    for path in (new.get("staging"), new.get("backup"), entry):
        if path and os.path.isdir(path):
            shutil.rmtree(path, ignore_errors=True)
    return "rolled-back-absent"


def recover(entry, cache_root, key):
    path = journal_path(cache_root, key)
    journal = _read_json(path)
    if journal is None:
        raise CacheError(f"journal 不可解析：{path}（保留现场）")
    if journal.get("schema_version") != JOURNAL_SCHEMA or journal.get("key") != key:
        raise CacheError(f"journal schema/key 不符：{path}（保留现场）")
    action, target = _recovery_action(entry, journal)
    if action == "roll-forward":
        status = _roll_forward(entry, journal, target)
    elif action == "rolled-back":
        status = _roll_back_in_place(entry, journal)
    elif action == "roll-backup":
        status = _restore_from_backup(entry, journal, path)
    elif action == "rolled-back-absent":
        status = _undo_first_publication(entry, journal)
    else:
        raise CacheError(
            "无法恢复：当前条目与 journal 记录的旧代/新代均不可验证（两代都不完整）；"
            f"保留现场 {path}")
    _finish(cache_root, key, journal)
    return status


def _finish(cache_root, key, journal):
    new = journal.get("new") or {}
    for path in (new.get("staging"), new.get("backup")):
        if path and os.path.isdir(path):
            shutil.rmtree(path, ignore_errors=True)
    path = journal_path(cache_root, key)
    if os.path.isfile(path):
        os.unlink(path)


def publish(args):
    """发布一个新的模板条目；命中则直接复用。"""
    inputs = inputs_digest(args)
    key = key_for(args, inputs)
    entry = os.path.join(args.cache_root, key)
    if os.path.isfile(journal_path(args.cache_root, key)):
        status = recover(entry, args.cache_root, key)
        print(f"TEMPLATE-CACHE-RECOVERED: {status}", file=sys.stderr)
    previous = _read_json(meta_path(entry)) or {}
    reason, _ = _valid_meta(entry, key, inputs) if os.path.isdir(entry) else ("不存在", None)
    if reason is None and not _check_identity(entry, args) and not _rebuild_requested():
        print(os.path.realpath(entry))
        print(key)
        return 0
    if reason is None:
        print("TEMPLATE-CACHE-REBUILD-INJECTED: 跳过本次命中，仍走真实 build/journal/move",
              file=sys.stderr)
    transaction = uuid.uuid4().hex
    staging = entry + f".staging-{transaction}"
    backup = entry + f".backup-{transaction}"
    journal = {"schema_version": JOURNAL_SCHEMA, "key": key, "transaction": transaction,
               "old": _capture_old(entry), "new": None}
    try:
        os.makedirs(args.cache_root, exist_ok=True)
        for candidate in (staging, backup):
            if os.path.lexists(candidate) or fixture_scope.marker(Path(candidate)).exists():
                raise CacheError(f"事务材料路径/marker 已存在（碰撞拒绝，不先删除）：{candidate}")
        _build(args, staging)
        reason = _check_identity(staging, args)
        if reason:
            raise CacheError(f"新条目身份校验失败：{reason}")
        if inputs_digest(args) != inputs:
            raise CacheError("模板输入在构建期间变化；拒绝把混合产物发布成稳定输入")
        _stop("after-staging-before-journal")
        # 先落 journal（此时还没有新代摘要）：崩溃后只有摘要确认过的新代才前滚。
        journal["new"] = {"digest": None, "staging": staging, "backup": backup, "meta": None}
        _write_json(journal_path(args.cache_root, key), journal)
        _stop("after-journal")
        if os.path.isdir(entry):
            fixture_scope.move(entry, backup)
            _stop("after-old-moved")
        fixture_scope.move(staging, entry)
        _stop("after-new-installed")
        # repoint 会改写记录里的绝对路径，摘要必须在它之后算（否则永远不符）。
        repoint = [PY, os.path.join(HERE, "template_check.py"), entry, "--repoint-from", staging,
                   "--expect-repoint-min", "1", "--quiet"]
        if args.deploy == "candidate":
            repoint = [PY, os.path.join(HERE, "template_check.py"), entry, "--version", args.version,
                       "--ref", args.ref, "--repoint-from", staging, "--expect-repoint-min", "1", "--quiet"]
        done = subprocess.run(repoint, capture_output=True, text=True)
        if done.returncode != 0:
            raise CacheError(f"TEMPLATE-REPOINT-MISMATCH: 记录未指向构建路径 {done.stderr.strip()[:200]}")
        digest = _tree(entry)
        meta = {
            "schema_version": META_SCHEMA,
            "key": key,
            "inputs_digest": inputs,
            "output_tree_digest": digest,
            "deploy": args.deploy,
            "version": args.version or "",
            "ref": args.ref or "",
            "root": os.path.realpath(entry),
            "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
            # 累计构建次数（additive 诊断字段，读取方不依赖）：等同槽位重建才增长。
            "builds": int(previous.get("builds") or 0) + 1,
        }
        journal["new"]["digest"] = digest
        journal["new"]["meta"] = json.dumps(meta, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
        _write_json(journal_path(args.cache_root, key), journal)
        _write_json(meta_path(entry), None, journal["new"]["meta"])
        _stop("after-meta")
        if _check_identity(entry, args):
            raise CacheError("发布后身份校验失败")
        if _tree(entry) != digest:
            raise CacheError("发布后条目字节与冻结摘要不符")
        _finish(args.cache_root, key, journal)
        print(os.path.realpath(entry))
        print(key)
        print(inputs)
        print("TEMPLATE-CACHE-HIT=0")
        os.environ.pop(TXN_REBUILD_ENV, None)
        return 0
    except Exception:
        try:
            if os.path.isfile(journal_path(args.cache_root, key)):
                recover(entry, args.cache_root, key)
            else:
                shutil.rmtree(staging, ignore_errors=True)
        except CacheError:
            pass
        raise


def main(argv=None):
    parser = argparse.ArgumentParser(description="夹具模板缓存（身份/单槽/journal 发布）")
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("key", "lookup", "migrate", "publish", "acquire"):
        command = sub.add_parser(name)
        command.add_argument("--cache-root", required=True)
        command.add_argument("--deploy", choices=("dev", "candidate"), required=True)
        command.add_argument("--version", default=None)
        command.add_argument("--ref", default=None)
        command.add_argument("--release-root", default=None)
        command.add_argument("--subject", default=None, help="已核候选 release subject（candidate）")
        command.add_argument("--results-dir", default=None)
    inventory_parser = sub.add_parser("inventory")
    inventory_parser.add_argument("--cache-root", required=True)
    inventory_parser.add_argument("--format", choices=("json", "sh"), default="json")
    retire_parser = sub.add_parser("retire")
    retire_parser.add_argument("--cache-root", required=True)
    retire_parser.add_argument("--selection", required=True)
    retire_parser.add_argument("--retirement-mode", choices=lifecycle.RETIREMENT_MODES,
                               required=True)
    retire_parser.add_argument("--confirm-retirement", action="store_true", required=True)
    retire_parser.add_argument("--report", default=None)
    args = parser.parse_args(argv)
    try:
        if args.command == "key":
            print(key_for(args, inputs_digest(args)))
            return 0
        if args.command == "lookup":
            return lookup(args)
        if args.command == "migrate":
            return migrate(args)
        if args.command == "acquire":
            if not args.results_dir:
                raise CacheError("acquire 需要 --results-dir（构建日志落点）")
            return acquire(args)
        if args.command == "inventory":
            report = inventory(args.cache_root)
            if args.format == "json":
                print(json.dumps(report, ensure_ascii=False, sort_keys=True))
            else:
                print("TEMPLATE_CACHE_STATUS=" + report.get("status", "partial"))
                print("TEMPLATE_CACHE_ENTRIES=" + str(len(report.get("entries") or [])))
            return 0 if report.get("status") in ("complete", "absent") else 1
        if args.command == "retire":
            return retire(args)
        if not args.results_dir:
            raise CacheError("publish 需要 --results-dir")
        return publish(args)
    except (CacheError, common.ReleaseError, fixture_scope.FixtureError, OSError) as exc:
        print(f"TEMPLATE-CACHE-FAILED: {exc}", file=sys.stderr)
        return 1


# ---- C3：确定性事务窗口、acquire 收拢与维护入口（父任务 design §5/§5.1/§4.2）-----

TXN_STOP_ENV = "WF_TEMPLATE_TXN_STOP_AFTER"
TXN_REBUILD_ENV = "WF_TEMPLATE_TXN_REBUILD"
FAULT_SWITCH = "WF_TEST_FAULT_INJECTION"
CHECKPOINTS = ("after-staging-before-journal", "after-journal", "after-old-moved",
               "after-new-installed", "after-meta",
               "after-material-cleanup-before-journal-remove")


def _faults():
    return os.environ.get(FAULT_SWITCH) == "1"


def _owned_scope():
    try:
        return fixture_scope.current_scope() is not None
    except fixture_scope.FixtureError:
        return False


def validate_checkpoint():
    requested = os.environ.get(TXN_STOP_ENV)
    if not requested:
        return None
    if not _faults():
        raise CacheError(f"{TXN_STOP_ENV} 只在 {FAULT_SWITCH}=1 时生效")
    if requested not in CHECKPOINTS:
        raise CacheError(f"未知模板事务 checkpoint：{requested!r}")
    if not _owned_scope():
        raise CacheError("模板事务 checkpoint 需要有效 owned test scope")
    return requested


def _stop(point):
    if os.environ.get(TXN_STOP_ENV) != point:
        return
    sys.stderr.write(f"WF-TEMPLATE-TXN-STOP: {point} pid={os.getpid()}\n")
    sys.stderr.flush()
    sys.stdout.flush()
    os._exit(97)


def _rebuild_requested():
    return (_faults() and os.environ.get(TXN_REBUILD_ENV) == "1" and _owned_scope())


def _strict_remove(path):
    """删除材料并确认不存在；失败保留现场（不 ignore_errors、不先删 journal）。"""
    if not path or not os.path.lexists(path):
        return
    if os.path.islink(path) or os.path.isfile(path):
        os.unlink(path)
    else:
        shutil.rmtree(path)
    if os.path.lexists(path):
        raise CacheError(f"材料删除失败，保留现场：{path}")


def _remove_template_material(path):
    """材料树与其兄弟 fixture marker 一起确认删除（marker 只能在树确认不存在的路径上移除）。"""
    _strict_remove(path)
    marker = fixture_scope.marker(Path(path))
    if marker.is_symlink():
        raise CacheError(f"材料 marker 是符号链接，保留现场：{marker}")
    if marker.exists():
        os.unlink(marker)
        if marker.exists():
            raise CacheError(f"材料 marker 删除失败：{marker}")


def _finish(cache_root, key, journal):
    new = journal.get("new") or {}
    for path in (new.get("staging"), new.get("backup")):
        if path and (os.path.lexists(path) or fixture_scope.marker(Path(path)).exists()):
            try:
                _remove_template_material(path)
            except OSError as exc:
                raise CacheError(f"事务材料未清理：{path}: {exc}") from exc
    _stop("after-material-cleanup-before-journal-remove")
    path = journal_path(cache_root, key)
    try:
        os.unlink(path)
    except FileNotFoundError:
        pass
    except OSError as exc:
        raise CacheError(f"journal 删除失败（材料已清，可重试收尾）：{path}: {exc}") from exc


def _undo_first_publication(entry, journal):
    new = journal.get("new") or {}
    for path in (new.get("staging"), new.get("backup"), entry):
        if path and (os.path.lexists(path) or fixture_scope.marker(Path(path)).exists()):
            try:
                _remove_template_material(path)
            except OSError as exc:
                raise CacheError(f"撤销首次发布失败，保留 journal：{path}: {exc}") from exc
    # entry 的正式 meta 属本次新代；旧代 meta 由 journal 冻结并在回滚路径恢复。
    meta = meta_path(entry)
    if os.path.lexists(meta):
        os.unlink(meta)
    return "rolled-back-absent"


def _validate_journal_paths(cache_root, key, journal):
    entry = os.path.join(cache_root, key)
    allowed = {"entry": entry, "meta": meta_path(entry)}
    new = journal.get("new") or {}
    for field, prefix in (("staging", entry + ".staging-"), ("backup", entry + ".backup-")):
        value = new.get(field)
        if value is None:
            continue
        if not isinstance(value, str) or not value.startswith(prefix) \
                or os.path.dirname(os.path.realpath(value)) != os.path.realpath(cache_root):
            raise CacheError(f"journal {field} 路径越界/不符：{value!r}（保留现场）")
        allowed[field] = value
    staging_parent = os.path.dirname(new.get("staging") or "")
    if staging_parent and os.path.basename(staging_parent).startswith(
            os.path.basename(entry) + ".staging-"):
        allowed["staging_parent"] = staging_parent
        if os.path.dirname(os.path.realpath(staging_parent)) != os.path.realpath(cache_root):
            raise CacheError("journal staging 父目录越界（保留现场）")
    return allowed


def recover(entry, cache_root, key):
    path = journal_path(cache_root, key)
    journal = _read_json(path)
    if journal is None:
        raise CacheError(f"journal 不可解析：{path}（保留现场）")
    if journal.get("schema_version") != JOURNAL_SCHEMA or journal.get("key") != key:
        raise CacheError(f"journal schema/key 不符：{path}（保留现场）")
    _validate_journal_paths(cache_root, key, journal)
    action, target = _recovery_action(entry, journal)
    if action == "roll-forward":
        status = _roll_forward(entry, journal, target)
    elif action == "rolled-back":
        status = _roll_back_in_place(entry, journal)
    elif action == "roll-backup":
        status = _restore_from_backup(entry, journal, path)
    elif action == "rolled-back-absent":
        status = _undo_first_publication(entry, journal)
    else:
        raise CacheError(
            "无法恢复：当前条目与 journal 记录的旧代/新代均不可验证（两代都不完整）；"
            f"保留现场 {path}")
    _finish(cache_root, key, journal)
    return status


def acquire(args):
    """唯一修改型入口：恢复 → 验证/迁移/命中 → 必要时发布（shell 不再自排顺序）。"""
    validate_checkpoint()
    inputs = inputs_digest(args)
    key = key_for(args, inputs)
    entry = os.path.join(args.cache_root, key)
    if os.path.isfile(journal_path(args.cache_root, key)):
        status = recover(entry, args.cache_root, key)
        print(f"TEMPLATE-CACHE-RECOVERED: {status}", file=sys.stderr)
    _migrate(args)
    reason, meta = _valid_meta(entry, key, inputs) if os.path.isdir(entry) else ("不存在", None)
    if reason is None and not _check_identity(entry, args) and not _rebuild_requested():
        print(os.path.realpath(entry))
        print(key)
        print(meta["inputs_digest"])
        print("TEMPLATE-CACHE-HIT=1")
        return 0
    if reason is None:
        print("TEMPLATE-CACHE-REBUILD-INJECTED: 跳过本次命中，仍走真实 build/journal/move",
              file=sys.stderr)
    return publish(args)


# ---- inventory / observe ----------------------------------------------------


def _uid(path):
    try:
        return os.stat(path).st_uid
    except OSError:
        return None


def _marker_matches(path):
    marker = fixture_scope.marker(fixture_scope.Path(path))
    try:
        record = json.loads(marker.read_text())
    except (OSError, ValueError):
        return False
    return record == {"owner": fixture_scope.OWNER,
                      "root": os.path.realpath(path)} and os.stat(path).st_uid == os.getuid()


def _entry_kind(name, entry_path):
    for prefix, kind in ((".staging-", "template-staging"), (".backup-", "template-backup"),
                         (".stale-", "template-stale")):
        if prefix in name:
            return kind
    if name.endswith(".build"):
        return "template-build"
    return "template-entry"


def inventory(cache_root):
    """只读盘点：不恢复、不取修改锁、不写 pyc/sidecar，只输出 JSON 结构。"""
    cache_root = os.path.abspath(cache_root)
    root = os.path.realpath(cache_root)
    reader_fds = []
    entries, unknown = [], []
    try:
        names = sorted(os.listdir(root))
    except FileNotFoundError:
        return {"schema_version": 1, "domain": "template-cache", "root": root,
                "status": "absent", "entries": [], "unknown": []}
    except OSError as exc:
        return {"schema_version": 1, "domain": "template-cache", "root": root,
                "status": "partial", "error": f"cache root unreadable: {exc}",
                "entries": [], "unknown": []}
    for name in names:
        path = os.path.join(root, name)
        name_kind = _entry_kind(name, path)
        if os.path.islink(path):
            unknown.append({"path": path, "reason": "symlink（不跟随）"})
            continue
        if name.endswith(".journal.json"):
            key = name[:-len(".journal.json")]
            entry = os.path.join(root, key)
            journal = _read_json(path)
            blocked = None
            try:
                if journal is None:
                    blocked = "journal unreadable（需完整 key reset）"
                else:
                    _validate_journal_paths(root, key, journal)
            except CacheError as exc:
                blocked = str(exc)
            entries.append({"root": root, "path": path, "kind": "journal", "key": key,
                            "provenance": "owned", "blocked": blocked or "journal-active",
                            "matenal_root": entry, "uid": _uid(path),
                            "digest": "sha256:" + __import__("hashlib").sha256(
                                Path(path).read_bytes()).hexdigest()})
            continue
        if name.endswith(".meta.json") or name.endswith(".owner") or (
                name.startswith(".") and name.endswith(".wf-owner.json")):
            # 附属记录随所属 entry/材料处置；marker-only 壳在上面的专门扫描里识别。
            continue
        if not os.path.isdir(path):
            if os.path.isfile(path) and name.endswith(".lock"):
                unknown.append({"path": path, "reason": "固定 .lock（永不作为清单对象）"})
            else:
                unknown.append({"path": path, "reason": "未知文件"})
            continue
        kind = name_kind
        marker = fixture_scope.marker(fixture_scope.Path(path))
        if kind != "template-entry":
            provenance = "owned" if _marker_matches(path) else "unproven"
            material_key = name.split(".staging-")[0].split(".backup-")[0].split(".stale-")[0]
            entries.append({"root": root, "path": path, "kind": kind, "key": material_key,
                            "provenance": provenance, "uid": _uid(path),
                            "marker": str(marker) if marker.is_file() else None,
                            "digest": _tree(path), "blocked": None,
                            "reason": "" if provenance == "owned" else "no matching fixture marker"})
            continue
        # 正式 entry（key 目录）：journal 存在 → 恢复优先；否则按 meta 判有效/未知。
        key = name
        journal = _read_json(journal_path(root, key))
        if journal is not None:
            provenance, blocked = "owned", "journal-active（先走 acquire 恢复）"
            digest = _tree(path)
        else:
            meta = _read_json(meta_path(path))
            if meta and meta.get("schema_version") == META_SCHEMA and \
                    meta.get("root") == os.path.realpath(path) and \
                    _tree(path) == meta.get("output_tree_digest"):
                provenance, blocked = "owned", None
            else:
                provenance, blocked = "unknown-entry", "meta/树不可验证"
            digest = _tree(path)
        entries.append({"root": root, "path": path, "kind": "template-entry", "key": key,
                        "provenance": provenance, "blocked": blocked, "uid": _uid(path),
                        "digest": digest, "marker": str(marker) if marker.is_file() else None})
    # marker-only 壳：marker 存在但对应树不存在。
    for name in names:
        if name.startswith(".") and name.endswith(".wf-owner.json"):
            target = os.path.join(root, name[1:-len(".wf-owner.json")])
            if not os.path.lexists(target):
                entries.append({"root": root, "path": os.path.join(root, name),
                                "kind": "marker",
                                "key": name[1:-len(".wf-owner.json")],
                                "provenance": "owned",
                                "uid": _uid(os.path.join(root, name)), "blocked": None,
                                "digest": "sha256:" + __import__("hashlib").sha256(
                                    Path(root, name).read_bytes()).hexdigest()})
    status = "partial" if unknown or any(item.get("blocked") for item in entries) else "complete"
    return {"schema_version": 1, "domain": "template-cache", "root": root,
            "status": status, "entries": entries, "unknown": unknown,
            "capacity": "not-measured"}


def _read_control(path):
    try:
        if os.path.islink(path) or os.path.getsize(path) > 1024 * 1024:
            return None
    except OSError:
        return None
    return _read_json(path)


def observe(cache_root):
    """root 维护前的浅层观察：只读直接子项/控制记录，不递归、不算树摘要。"""
    root = os.path.abspath(cache_root)
    observed_at = datetime.datetime.now().astimezone().isoformat(timespec="seconds")
    if not os.path.exists(root):
        return {"root": root, "status": "absent", "counts": {}, "capacity": "not-measured",
                "observed_at": observed_at,
                "inventory_hint": f"python3 {os.path.abspath(__file__)} inventory "
                                  f"--cache-root {root} --format json"}
    counts, unverified = {}, []
    try:
        names = sorted(os.listdir(root))
    except OSError as exc:
        return {"root": root, "status": "unverified", "counts": {}, "error": str(exc),
                "capacity": "not-measured", "observed_at": observed_at,
                "inventory_hint": f"python3 {os.path.abspath(__file__)} inventory "
                                  f"--cache-root {root} --format json"}
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
        if name.endswith((".meta.json", ".wf-owner.json")) or name.startswith("."):
            continue
        if ".staging-" in name or ".backup-" in name or ".stale-" in name:
            counts["orphan-like"] = counts.get("orphan-like", 0) + 1
            marker = fixture_scope.marker(Path(path))
            if not _marker_matches(path) or not marker.is_file():
                counts["unproven"] = counts.get("unproven", 0) + 1
            continue
        if not os.path.isdir(path):
            counts["unknown"] = counts.get("unknown", 0) + 1
            continue
        journal = _read_control(journal_path(root, name))
        if journal is not None:
            counts["recovery-required"] = counts.get("recovery-required", 0) + 1
            continue
        meta = _read_control(meta_path(path))
        owner = _read_control(os.path.join(root, "." + name + ".wf-owner.json"))
        if meta is not None and owner is not None and \
                meta.get("schema_version") == 1 and owner.get("owner") == fixture_scope.OWNER:
            counts["valid"] = counts.get("valid", 0) + 1
        else:
            counts["unknown"] = counts.get("unknown", 0) + 1
    status = "partial" if unverified or counts.get("unknown") or counts.get("recovery-required") \
        else "complete"
    return {"root": os.path.realpath(root), "status": status, "counts": counts,
            "unverified": unverified, "capacity": "not-measured",
            "observed_at": observed_at,
            "inventory_hint": f"python3 {os.path.abspath(__file__)} inventory "
                              f"--cache-root {root} --format json"}


# ---- retire -----------------------------------------------------------------


def _guard_locks():
    inherited = os.environ.get("WF_FIXTURE_LEASE_FD")
    if inherited:
        fixture_scope.verify_lease()
        return
    import fcntl
    lock_path = Path("/tmp") / f"wf-test-fixtures-{os.getuid()}.lock"
    fd = os.open(lock_path, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError as exc:
        os.close(fd)
        raise CacheError("模板维护忙：另一个 wf harness 持有 fixture lease") from exc
    finally:
        try:
            fcntl.flock(fd, fcntl.LOCK_UN)
            os.close(fd)
        except OSError:
            pass


def _delete_selected(item):
    path = item["path"]
    if item["kind"] == "journal":
        # journal 最后删：只有同一 key 的材料已被处置时才允许（排序由调用方保证）。
        os.unlink(path)
        return
    if item["kind"] == "marker":
        os.unlink(path)
        target = os.path.join(os.path.dirname(path),
                              os.path.basename(path)[1:-len(".wf-owner.json")])
        if os.path.isdir(target) and not os.listdir(target):
            os.rmdir(target)
        return
    if os.path.islink(path) or os.path.isfile(path):
        os.unlink(path)
        return
    shutil.rmtree(path)
    marker = fixture_scope.marker(fixture_scope.Path(path))
    if marker.is_file():
        os.unlink(marker)
    if item["kind"] == "template-entry":
        meta = meta_path(path)
        if os.path.lexists(meta):
            os.unlink(meta)


def _selection_order(entries):
    order = {"template-staging": 0, "template-backup": 0, "template-stale": 0,
             "template-build": 0, "template-entry": 1,
             "template-stale": 0, "template-build": 0, "marker": 1, "journal": 2}
    return sorted(entries, key=lambda item: order.get(item["kind"], 1))


def _require_in_scope(path, label):
    scope = os.environ.get("WF_TEST_SCOPE_ROOT")
    if scope:
        fixture_scope.ensure_in_scope(Path(path))


def retire(args):
    cache_root = os.path.abspath(args.cache_root)
    _require_in_scope(args.selection, "selection")
    _require_in_scope(args.report, "report")
    document = _read_json(args.selection)
    if document is None:
        raise CacheError(f"selection 不可读：{args.selection}")
    selected = lifecycle.selection_entries(document, "template-cache")
    current = {os.path.realpath(item["path"]): item
               for item in inventory(cache_root)["entries"]}
    chosen = []
    for item in selected:
        found = current.get(os.path.realpath(item["path"]))
        if found is None:
            raise CacheError(f"selection 项已不存在/漂移：{item['path']}")
        if found["kind"] != item["kind"]:
            raise CacheError(f"selection kind 漂移：{item['path']}")
        if item.get("provenance") and found.get("provenance") != item["provenance"]:
            raise CacheError(f"selection provenance 漂移：{item['path']}")
        if found.get("blocked") == "journal-active" and found["kind"] != "journal":
            raise CacheError(f"journal 未收尾的材料必须先走 acquire 恢复：{item['path']}")
        chosen.append(found)
    for item in chosen:
        live = lifecycle.live_references(item["path"])
        if live:
            raise CacheError(f"存在活引用（{live[0]['pid']}:{live[0]['kind']}）拒绝删除：{item['path']}")
    # 坏 journal 的 cache-key reset 必须整组选中：entry/材料/marker/journal 全在集合内。
    selected = {os.path.realpath(item["path"]) for item in chosen}
    for key in {item.get("key") for item in chosen if item["kind"] == "journal"}:
        group = [item for item in current.values() if item.get("key") == key]
        missing = sorted(item["path"] for item in group
                         if os.path.realpath(item["path"]) not in selected)
        if missing:
            raise CacheError(f"cache key 重置集合不完整（缺 {missing}）；不得只删 journal 留下可命中残代")
    if args.retirement_mode == "safe-legacy":
        for item in chosen:
            if item.get("provenance") not in ("owned", "legacy-owned", "empty-shell"):
                raise CacheError(f"safe-legacy 只接受可验证归属：{item['path']} "
                                 f"({item.get('provenance')})")
            if item["kind"] == "journal":
                raise CacheError("journal 不能走 safe-legacy（需完整 key reset/manual-retained）")
            if item["kind"] == "template-entry":
                raise CacheError("有效模板条目不是 legacy 材料；请走 manual-retained 或正常替换")
    report = lifecycle.execute_retirement(
        "template-cache", os.path.realpath(cache_root), _selection_order(chosen),
        args.retirement_mode, args.report, _delete_selected, _guard_locks, True)
    print(json.dumps({"state": "retired", "mode": args.retirement_mode,
                      "report": os.path.abspath(args.report),
                      "entries": len(report["results"])}, ensure_ascii=False,
                     sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
