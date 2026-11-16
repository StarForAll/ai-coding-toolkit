#!/usr/bin/env python3
"""release_lock.py — 每个 canonical release root 的固定 sidecar 锁 inode（唯一实现）。

为什么独立：`wf_test_release.py` 的公开 CLI 与 runner 消费期 wrapper 必须**共用同一把锁**，
而 wrapper 还要在假环境（r67 测试树）里工作，不能依赖 `wf_test_release.py` 的完整实现。
本模块只管锁本身：

- 锁路径 `<realpath(root)>.lock`：根外、不随 tree 替换、创建后**从不 unlink**、拒绝符号链接、
  校验 regular file 与 UID；
- 取锁是**非阻塞** flock（独占/共享都支持）；竞争抛 `Busy`（明确 busy，不改 cache）；
- 消费期专用 `lease()`：同一 PID 持独占 fd 后 `exec`，env 只放定位用的 PID/FD/path/mount 域；
- `verify_lease()`：按 `/proc` 祖先链、FD target、device/inode、fdinfo 的 kernel flock 与
  mount namespace 逐项核对——env 文本不是授权证据。
"""
from __future__ import annotations

import fcntl
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import wf_test_paths  # noqa: E402  （scope 下锁路径同样必须在首次创建前核验）


class LockError(Exception):
    """可预期的拒绝。"""


class Busy(LockError):
    """锁被占用：调用方明确 busy，可稍后重试。"""


def lock_path(root):
    return os.path.realpath(root) + ".lock"


def open_lock(root):
    path = lock_path(root)
    try:
        wf_test_paths.require_in_scope(root, path)
    except wf_test_paths.PathError as exc:
        raise LockError(str(exc)) from exc
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    if os.path.islink(path):
        raise LockError(f"release lock must not be a symlink: {path}")
    fd = os.open(path, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    stat = os.fstat(fd)
    if not os.path.isfile(path) or stat.st_uid != os.getuid():
        os.close(fd)
        raise LockError(f"release lock is not a regular file owned by us: {path}")
    return fd


def acquire(root, exclusive=True):
    fd = open_lock(root)
    flags = (fcntl.LOCK_EX if exclusive else fcntl.LOCK_SH) | fcntl.LOCK_NB
    try:
        fcntl.flock(fd, flags)
    except BlockingIOError as exc:
        os.close(fd)
        kind = "exclusive" if exclusive else "shared"
        raise Busy(
            f"release lock is busy ({kind}): {lock_path(root)}；"
            "另一个 ensure/check 或消费期 runner 正持有它，稍后重试") from exc
    return fd


def release(fd):
    if fd is None:
        return
    try:
        fcntl.flock(fd, fcntl.LOCK_UN)
    finally:
        os.close(fd)


def write_env(fd, root):
    os.environ["WF_TEST_RELEASE_LEASE_FD"] = str(fd)
    os.environ["WF_TEST_RELEASE_LEASE_PID"] = str(os.getpid())
    os.environ["WF_TEST_RELEASE_ROOT"] = os.path.realpath(root)
    os.environ["WF_TEST_RELEASE_LEASE_MNT"] = os.readlink("/proc/self/ns/mnt")
    os.set_inheritable(fd, True)


def verify_lease(root=None):
    """证明祖先进程仍持本 root 的独占 flock，且 mount 域与锁 inode 一致。"""
    try:
        pid = int(os.environ["WF_TEST_RELEASE_LEASE_PID"])
        fd = int(os.environ["WF_TEST_RELEASE_LEASE_FD"])
        expected = lock_path(root or os.environ["WF_TEST_RELEASE_ROOT"])
        if os.readlink(f"/proc/{pid}/fd/{fd}") != expected:
            raise ValueError("lease descriptor points at another path")
        declared_mnt = os.environ.get("WF_TEST_RELEASE_LEASE_MNT")
        current_mnt = os.readlink("/proc/self/ns/mnt")
        if declared_mnt and declared_mnt != current_mnt:
            raise ValueError("lease was taken in another mount namespace")
        if os.readlink(f"/proc/{pid}/ns/mnt") != current_mnt:
            raise ValueError("lease holder is in another mount namespace")
        handle = os.open(f"/proc/{pid}/fd/{fd}", os.O_RDONLY)
        try:
            held = os.fstat(handle)
        finally:
            os.close(handle)
        current = os.stat(expected)
        if (held.st_dev, held.st_ino) != (current.st_dev, current.st_ino):
            raise ValueError("lease descriptor is not the canonical lock inode")
        with open(f"/proc/{pid}/fdinfo/{fd}", encoding="utf-8") as stream:
            info = stream.read()
        locks = [line for line in info.splitlines() if line.startswith("lock:")]
        if not any("FLOCK" in line and "WRITE" in line and f" {pid} " in line for line in locks):
            raise ValueError("release flock is not held by the declared ancestor")
        current_pid = os.getpid()
        while current_pid not in (pid, 0, 1):
            with open(f"/proc/{current_pid}/status", encoding="utf-8") as stream:
                status = stream.read()
            current_pid = int(next(line.split()[1] for line in status.splitlines()
                                   if line.startswith("PPid:")))
        if current_pid != pid:
            raise ValueError("lease owner is not an ancestor")
        return True
    except (KeyError, ValueError, OSError, StopIteration) as exc:
        raise LockError(f"invalid inherited release lease: {exc}") from exc


def lease(root, command):
    """同一 PID 持独占 fd 后 exec；调用方负责在此之前完成 build/check。"""
    fd = acquire(root, exclusive=True)
    write_env(fd, root)
    os.execvp(command[0], command)


def main(argv=None):
    import argparse

    parser = argparse.ArgumentParser(description="release root sidecar lock")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--acquire", action="store_true")
    group.add_argument("--verify", action="store_true")
    group.add_argument("--lease", action="store_true")
    parser.add_argument("--root", required=True)
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args(argv)
    try:
        if args.verify:
            verify_lease(args.root)
            print("OK  lease")
            return 0
        if args.lease:
            command = args.command[1:] if args.command[:1] == ["--"] else args.command
            if not command:
                parser.error("--lease requires a command after --")
            lease(args.root, command)
            return 0
        fd = acquire(args.root)
        print(fd)
        print(os.getpid())
        return 0
    except Busy as exc:
        print(f"BUSY  {exc}", file=sys.stderr)
        return 75
    except LockError as exc:
        print(f"FAIL  {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
