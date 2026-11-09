"""lock.py — 最小互斥与存活线索（机制稿 §4.1）。

锁对象固定为项目根 `.wf-lock`：只创建、不删除，内容固定 `wf-lock-v1\\n`。
"""

from __future__ import annotations

import errno
import fcntl
import os
import time
import uuid

LOCK_NAME = ".wf-lock"
LOCK_MARK = b"wf-lock-v1\n"
WAIT_LIMIT_SECONDS = 5.0
RETRY_INTERVAL_SECONDS = 0.05


class LockError(Exception):
    pass


class LockBusy(LockError):
    def __init__(self, message, path):
        super().__init__(message)
        self.path = path


class LockUnavailable(LockError):
    """锁对象不可识别/初始化未完成：交人核实处置，普通入口不认领、不覆写（机制稿 §4.1）。"""

    def __init__(self, message, path, facts=None):
        super().__init__(message)
        self.path = path
        self.facts = facts or {}


LockMismatch = LockUnavailable


class LockHandle:
    def __init__(self, path, fd):
        self.path = path
        self.fd = fd
        self._released = False

    def release(self):
        if self._released:
            return
        try:
            # 释放即撤销持锁者事实：保留标记行，避免陈旧 pid 被当成存活
            try:
                os.lseek(self.fd, 0, os.SEEK_SET)
                os.write(self.fd, LOCK_MARK)
                os.ftruncate(self.fd, len(LOCK_MARK))
                os.fsync(self.fd)
            except OSError:
                pass
            fcntl.flock(self.fd, fcntl.LOCK_UN)
        finally:
            os.close(self.fd)
            self._released = True

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.release()
        return False


def lock_path(root):
    return os.path.join(str(root), LOCK_NAME)


def _open_lock(root):
    root_real = os.path.realpath(str(root))
    path = os.path.realpath(lock_path(root_real))
    if path != os.path.join(root_real, LOCK_NAME):
        raise LockMismatch("lock object resolves outside project root", path)
    fd = os.open(path, os.O_RDWR | os.O_CREAT, 0o644)
    info = os.fstat(fd)
    if not os.path.isfile(path) or (info.st_mode & 0o170000) != 0o100000:
        os.close(fd)
        raise LockMismatch("lock object is not a regular file", path)
    return path, fd


def _read_mark(fd):
    """读首段，用于判定标记；允许其后跟持锁者事实行。"""
    os.lseek(fd, 0, os.SEEK_SET)
    return os.read(fd, len(LOCK_MARK) + 1)


def _write_mark(fd):
    """写标记行；随后追加持锁者进程事实（供只读存活探测），不改标记本身。"""
    os.lseek(fd, 0, os.SEEK_SET)
    os.write(fd, LOCK_MARK)
    os.ftruncate(fd, len(LOCK_MARK))
    detail = _holder_line()
    if detail:
        os.write(fd, detail.encode("utf-8"))
    os.fsync(fd)


def _holder_line():
    try:
        start = proc_start(os.getpid())
    except Exception:
        start = None
    return f"holder pid={os.getpid()} start={start or 'unknown'}\n"


def _open_exclusive(path):
    """首次创建用排他创建；已存在则只读打开（不创建、不截断）。"""
    try:
        return os.open(path, os.O_RDWR | os.O_CREAT | os.O_EXCL, 0o644), True
    except FileExistsError:
        return os.open(path, os.O_RDWR), False


def acquire(root, timeout=WAIT_LIMIT_SECONDS, holder_hint=None):
    """有界等待的排他获取；返回 LockHandle（机制稿 §4.1：排他创建、不认领未知内容）。"""
    import stat as stat_mod

    root_real = os.path.realpath(str(root))
    path = os.path.join(root_real, LOCK_NAME)
    deadline = time.monotonic() + timeout
    while True:
        try:
            fd, created = _open_exclusive(path)
        except OSError as exc:
            raise LockError(f"cannot open lock: {exc}") from exc
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            if exc.errno not in (errno.EACCES, errno.EAGAIN):
                os.close(fd)
                raise LockError(f"flock failed: {exc}") from exc
            os.close(fd)
            if time.monotonic() >= deadline:
                raise LockBusy(
                    f"lock busy{f' (holder: {holder_hint})' if holder_hint else ''}",
                    path,
                )
            time.sleep(RETRY_INTERVAL_SECONDS)
            continue
        info = os.fstat(fd)
        if not stat_mod.S_ISREG(info.st_mode):
            os.close(fd)
            raise LockUnavailable("lock object is not a regular file", path)
        real = os.path.realpath(path)
        if not (real == root_real or real.startswith(root_real + os.sep)):
            os.close(fd)
            raise LockUnavailable("lock object real path escapes the project root", path, {"resolved": real})
        content = _read_mark(fd)
        if created:
            if content:
                os.close(fd)
                raise LockUnavailable("lock object appeared during exclusive creation", path,
                                      {"mark": content[:32].decode("latin-1")})
            _write_mark(fd)
        elif not content.startswith(LOCK_MARK):
            os.close(fd)
            raise LockUnavailable(
                "lock mark incomplete or unknown (initialization unfinished)", path,
                {"mark": content[:32].decode("latin-1") or "<empty>"})
        else:
            # 既有锁文件：刷新持锁者事实，别把上一任的 pid 当成当前持有者
            _write_mark(fd)
        try:
            on_disk = os.stat(path)
            opened = os.fstat(fd)
            if (on_disk.st_dev, on_disk.st_ino) != (opened.st_dev, opened.st_ino):
                raise LockUnavailable("lock object replaced or removed during acquire", path)
        except FileNotFoundError as exc:
            os.close(fd)
            raise LockUnavailable("lock object removed during acquire", path) from exc
        return LockHandle(path, fd)

# --------------------------------------------------------------------------
# 存活探测（机制稿 §4.1：持锁标记 + 存活探测 + 人工确认）
# --------------------------------------------------------------------------

def holder_mark(root):
    """锁文件里登记的持锁事实（pid / 进程启动时刻），供只读探测；无登记返回 None。"""
    path = lock_path(root)
    try:
        with open(path, "r", encoding="utf-8") as handle:
            text = handle.read()
    except OSError:
        return None
    body = text.split("\n", 1)[1] if "\n" in text else ""
    if not body.startswith("holder "):
        return None
    fields = {}
    for token in body.strip().split():
        if "=" in token:
            key, value = token.split("=", 1)
            fields[key] = value
    return fields or None


def proc_start(pid):
    """该 pid 的进程启动时刻（/proc/<pid>/stat 第 22 字段）；不可得返回 None。"""
    try:
        with open(f"/proc/{int(pid)}/stat", "r", encoding="utf-8") as handle:
            fields = handle.read().split()
    except (OSError, ValueError):
        return None
    return fields[21] if len(fields) > 21 else None


def verify_holder(root, record=None):
    """只读判定：登记的持锁者是否仍是同一进程。返回 (alive, facts)。

    只用锁文件与 /proc 的只读事实，不修改任何文件、不获取锁；判定结论供人确认时参考。
    """
    mark = holder_mark(root)
    if not mark:
        return False, {"reason": "no holder mark recorded"}
    pid = mark.get("pid")
    recorded_start = mark.get("start")
    if not pid:
        return False, {"reason": "holder mark lacks pid"}
    actual_start = proc_start(pid)
    if actual_start is None:
        return False, {"reason": "holder process not running", "pid": pid, "start": recorded_start}
    if recorded_start and actual_start != recorded_start:
        return False, {"reason": "pid reused by another process", "pid": pid,
                       "recorded_start": recorded_start, "actual_start": actual_start}
    return True, {"pid": pid, "start": actual_start}
