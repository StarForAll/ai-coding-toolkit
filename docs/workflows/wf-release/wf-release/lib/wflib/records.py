"""records.py — 规范 JSON、哈希域与记录读写（机制稿 §1.1）。

仅使用标准库；本模块不定义任何判定，只提供编码与原子落盘原语。
"""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from datetime import datetime, timezone

# --------------------------------------------------------------------------
# 规范 JSON（C(x)）与哈希域（H(domain, payload)）
# --------------------------------------------------------------------------


class RecordInvalid(Exception):
    """记录语法/必需字段不可解析（对应 WF_RECORD_INVALID 的事实面）。"""


class DuplicateKeyError(RecordInvalid):
    pass


def canonical(obj) -> str:
    """C(x)：键按 Unicode 顺序排序，分隔符 `,`/`:`，不转义非 ASCII，无尾换行。"""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def canonical_bytes(obj) -> bytes:
    return canonical(obj).encode("utf-8")


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def H(domain: str, obj) -> str:
    """H(domain, payload) = "sha256:" + SHA256(UTF8(domain) ‖ 0x00 ‖ C(payload))."""
    payload = obj if isinstance(obj, (bytes, bytearray)) else canonical_bytes(obj)
    return "sha256:" + sha256_hex(domain.encode("utf-8") + b"\x00" + bytes(payload))


def sorted_unique(items) -> list:
    """集合型数组：按元素规范 JSON 的 UTF-8 字节序排序去重。"""
    seen = {}
    for item in items:
        encoded = canonical_bytes(item)
        seen[encoded] = item
    return [seen[key] for key in sorted(seen)]


def plain_digest(obj) -> str | None:
    """结构的规范 JSON 摘要（用于 entry_snapshot_digest 等既有定义）。"""
    if obj is None:
        return None
    return "sha256:" + sha256_hex(canonical_bytes(obj))


def file_digest(path) -> str | None:
    """文件原始字节哈希；不存在返回 None。"""
    try:
        with open(path, "rb") as handle:
            digest = hashlib.sha256()
            for chunk in iter(lambda: handle.read(65536), b""):
                digest.update(chunk)
            return "sha256:" + digest.hexdigest()
    except FileNotFoundError:
        return None


# --------------------------------------------------------------------------
# 严格读取：拒绝重复键、NaN/Infinity 与语法损坏
# --------------------------------------------------------------------------


def _pairs_hook(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise DuplicateKeyError(f"duplicate key: {key}")
        result[key] = value
    return result


def _reject_constant(token):
    raise RecordInvalid(f"non-finite number: {token}")


def loads(text: str):
    """语法损坏与常量非法都归一成 RecordInvalid（消费端只认这一个出口，不泄漏 JSONDecodeError）。"""
    try:
        return json.loads(
            text,
            object_pairs_hook=_pairs_hook,
            parse_constant=_reject_constant,
        )
    except RecordInvalid:
        raise
    except ValueError as exc:
        raise RecordInvalid(f"invalid json: {exc}") from exc


def load_json(path, default=None):
    """读取 JSON 记录；文件缺失返回 default（不伪造记录）。"""
    try:
        with open(path, "r", encoding="utf-8") as handle:
            text = handle.read()
    except FileNotFoundError:
        return default
    except OSError as exc:  # 不可读按结构损坏上报，不静默当缺失
        raise RecordInvalid(f"unreadable: {path}: {exc}") from exc
    try:
        return loads(text)
    except RecordInvalid:
        raise
    except ValueError as exc:
        raise RecordInvalid(f"invalid json: {path}: {exc}") from exc


def dumps(obj) -> str:
    """记录文件的可读形态（排序键、缩进、保留 Unicode、带尾换行）。"""
    return json.dumps(obj, sort_keys=True, indent=2, ensure_ascii=False) + "\n"


# --------------------------------------------------------------------------
# 原子落盘
# --------------------------------------------------------------------------


def atomic_write(path, text: str, *, exclusive: bool = False) -> None:
    """同目录临时文件 + flush/fsync + 原子替换/排他发布，随后读回核对。"""
    path = str(path)
    directory = os.path.dirname(path) or "."
    os.makedirs(directory, exist_ok=True)
    if exclusive and os.path.exists(path):
        raise FileExistsError(path)
    fd, tmp = tempfile.mkstemp(prefix=".wf-tmp-", dir=directory)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        if exclusive:
            try:
                os.link(tmp, path)  # 排他发布：目标已存在即失败
            except FileExistsError:
                raise
            except OSError:
                if os.path.exists(path):
                    raise FileExistsError(path)
                os.replace(tmp, path)
            else:
                os.unlink(tmp)
                tmp = None
        else:
            os.replace(tmp, path)
            tmp = None
        try:
            dir_fd = os.open(directory, os.O_RDONLY)
        except OSError:
            dir_fd = None
        if dir_fd is not None:
            try:
                os.fsync(dir_fd)
            finally:
                os.close(dir_fd)
        with open(path, "r", encoding="utf-8") as handle:
            actual = handle.read()
        if actual != text:
            raise OSError(f"read-back mismatch: {path}")
    finally:
        if tmp is not None and os.path.exists(tmp):
            os.unlink(tmp)


def write_json(path, obj, *, exclusive: bool = False) -> dict:
    atomic_write(path, dumps(obj), exclusive=exclusive)
    return obj


def merge_unknown(current: dict, updated: dict, owned) -> dict:
    """写回时保留本操作不拥有的未知字段（D10）。"""
    owned = set(owned)
    merged = dict(updated)
    for key, value in (current or {}).items():
        if key not in owned and key not in merged:
            merged[key] = value
    return merged


def update_record(path, mutate, *, owned) -> dict:
    """读-改-写：保留未知字段、bump revision、刷新 updated_at。"""
    record = load_json(path)
    if record is None:
        raise RecordInvalid(f"missing record: {path}")
    current = dict(record)
    mutate(record)
    record = merge_unknown(current, record, owned)
    record["revision"] = int(current.get("revision", 0)) + 1
    record["updated_at"] = now_str()
    write_json(path, record)
    return record


# --------------------------------------------------------------------------
# 时间（UTC 固定微秒六位 + Z）
# --------------------------------------------------------------------------

TIME_FORMAT = "%Y-%m-%dT%H:%M:%S.%fZ"


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def fmt_time(moment: datetime) -> str:
    return moment.astimezone(timezone.utc).strftime(TIME_FORMAT)


def now_str() -> str:
    return fmt_time(utc_now())


def today_str() -> str:
    return utc_now().strftime("%Y-%m-%d")


def parse_time(text: str) -> datetime:
    return datetime.strptime(text, TIME_FORMAT).replace(tzinfo=timezone.utc)
