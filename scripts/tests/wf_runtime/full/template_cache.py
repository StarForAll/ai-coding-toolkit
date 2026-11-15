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

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(REPO, "scripts"))
sys.path.insert(0, HERE)

import wf_release_common as common  # noqa: E402
import fixture_scope  # noqa: E402

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
    """命中打印 root 与 meta JSON；miss 打印原因并返回 10。"""
    inputs = inputs_digest(args)
    key = key_for(args, inputs)
    entry = os.path.join(args.cache_root, key)
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
    """只在同一 Python/deploy/release 槽位、owner/root/身份完整匹配时把 legacy key 改名到新 key。"""
    inputs = inputs_digest(args)
    key = key_for(args, inputs)
    target = os.path.join(args.cache_root, key)
    if os.path.exists(target):
        print(key)
        return 0
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
        print(key)
        return 0
    source = candidates[0]
    fixture_scope.move(source, target)
    os.rename(meta_path(source), meta_path(target))
    print(key)
    return 0


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


def _restore(entry, journal):
    old = journal.get("old") or {}
    new = journal.get("new") or {}
    if not old.get("present"):
        for path in (new.get("staging"), new.get("backup"), entry):
            if path and os.path.isdir(path):
                shutil.rmtree(path, ignore_errors=True)
        return "rolled-back-absent"
    backup = new.get("backup")
    if not backup or not os.path.isdir(backup) or _tree(backup) != old.get("digest"):
        raise CacheError(f"无法恢复：旧条目备份缺失或字节不符（保留 {new.get('journal')}）")
    if os.path.isdir(entry):
        shutil.rmtree(entry)
    os.rename(backup, entry)
    _write_json(meta_path(entry), None, old["meta"])
    return "rolled-back"


def recover(entry, cache_root, key):
    path = journal_path(cache_root, key)
    journal = _read_json(path)
    if journal is None:
        raise CacheError(f"journal 不可解析：{path}（保留现场）")
    if journal.get("schema_version") != JOURNAL_SCHEMA or journal.get("key") != key:
        raise CacheError(f"journal schema/key 不符：{path}（保留现场）")
    new = journal.get("new") or {}
    for candidate in ((new.get("staging"), entry) if new.get("digest") else ()):
        if candidate and os.path.isdir(candidate) and _tree(candidate) == new.get("digest"):
            if candidate != entry:
                backup = new.get("backup")
                if os.path.isdir(entry):
                    if not backup:
                        raise CacheError("journal 缺少 backup 路径")
                    if os.path.isdir(backup):
                        shutil.rmtree(backup)
                    os.rename(entry, backup)
                os.rename(candidate, entry)
            _write_json(meta_path(entry), None, new["meta"])
            if _tree(entry) != new.get("digest"):
                raise CacheError("前滚后条目仍不可验证（保留现场）")
            _finish(cache_root, key, journal)
            return "rolled-forward"
    status = _restore(entry, journal)
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
    reason, _ = _valid_meta(entry, key, inputs) if os.path.isdir(entry) else ("不存在", None)
    if reason is None and not _check_identity(entry, args):
        print(os.path.realpath(entry))
        print(key)
        return 0
    transaction = uuid.uuid4().hex
    staging = entry + f".staging-{transaction}"
    backup = entry + f".backup-{transaction}"
    journal = {"schema_version": JOURNAL_SCHEMA, "key": key, "transaction": transaction,
               "old": _capture_old(entry), "new": None}
    try:
        os.makedirs(args.cache_root, exist_ok=True)
        shutil.rmtree(staging, ignore_errors=True)
        _build(args, staging)
        reason = _check_identity(staging, args)
        if reason:
            raise CacheError(f"新条目身份校验失败：{reason}")
        if inputs_digest(args) != inputs:
            raise CacheError("模板输入在构建期间变化；拒绝把混合产物发布成稳定输入")
        # 先落 journal（此时还没有新代摘要）：崩溃后只有摘要确认过的新代才前滚。
        journal["new"] = {"digest": None, "staging": staging, "backup": backup, "meta": None}
        _write_json(journal_path(args.cache_root, key), journal)
        if os.path.isdir(entry):
            fixture_scope.move(entry, backup)
        fixture_scope.move(staging, entry)
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
        }
        journal["new"]["digest"] = digest
        journal["new"]["meta"] = json.dumps(meta, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
        _write_json(journal_path(args.cache_root, key), journal)
        _write_json(meta_path(entry), None, journal["new"]["meta"])
        if _check_identity(entry, args):
            raise CacheError("发布后身份校验失败")
        if _tree(entry) != digest:
            raise CacheError("发布后条目字节与冻结摘要不符")
        _finish(args.cache_root, key, journal)
        print(os.path.realpath(entry))
        print(key)
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
    for name in ("key", "lookup", "migrate", "publish"):
        command = sub.add_parser(name)
        command.add_argument("--cache-root", required=True)
        command.add_argument("--deploy", choices=("dev", "candidate"), required=True)
        command.add_argument("--version", default=None)
        command.add_argument("--ref", default=None)
        command.add_argument("--release-root", default=None)
        command.add_argument("--subject", default=None, help="已核候选 release subject（candidate）")
        command.add_argument("--results-dir", default=None)
    args = parser.parse_args(argv)
    try:
        if args.command == "key":
            print(key_for(args, inputs_digest(args)))
            return 0
        if args.command == "lookup":
            return lookup(args)
        if args.command == "migrate":
            return migrate(args)
        if not args.results_dir:
            raise CacheError("publish 需要 --results-dir")
        return publish(args)
    except (CacheError, common.ReleaseError, fixture_scope.FixtureError, OSError) as exc:
        print(f"TEMPLATE-CACHE-FAILED: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
