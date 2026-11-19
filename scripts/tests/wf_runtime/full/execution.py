#!/usr/bin/env python3
"""Bound test commands, retain logs and interpret legacy assertion output once.

## 套件输出契约（verdict 是唯一解释点）

套件/流程脚本的人类可读输出遵循以下行文法，`verdict()` 是它们唯一的地方解释器
（run_all.sh 只消费结果 JSON 的 assertion_result，不在 shell 里复制判定）：

- PASS 行：`[PASS] ...`、`PASS ...`、`[<标签>]: PASS ...`（三种前缀形态）；
- FAIL 行：`[FAIL] ...` 或 `... FAIL ...`（作 failures 计数）；
- 汇总行（suite kind 的尾行，三种格式）：
  1. `saved <good> / <total>`；
  2. `saved <total> cases; <good> passed`；
  3. `saved <total> cases`（此时要求 passed 行计数 == total）；
- steps 型输出：逐行 `[<步骤>] exit=<rc> code=WF_OK`，尾行 `TASK_ID <id>`；
- repro 型输出：`PASS green|red: <detail>`；detail 可以跨行（随后跟着原因块），
  因此按**任一行**匹配判定，不要求它是尾行。相位必须显式给出；相反相位的 PASS
  或任何 FAIL 行都不能证明本次相位。

## 命令后代监督（C → G → S → W）

`run()` 为每个命令建立固定拓扑：调用方 C 派生专用 guardian G，G 在自己的 session 里
派生执行 supervisor S，S 再派生目标 W。G/S 都用 `PR_SET_CHILD_SUBREAPER` 成为孤儿
回收点：S 正常死亡（普通异常/os._exit/SIGKILL/卡住）后，其残留后代被内核交给 G，
G 在同一条回收算法里终止并 wait 它们，并把该次运行判为设施失败——即使 W 曾 rc=0。

控制面是两条匿名 `socketpair`（C↔G、G↔S）上的有界长度帧（4 字节大端长度 + JSON），
默认 CLOEXEC，W 不继承任何控制 FD。消息：READY、START、STARTED、CANCEL、
CANCELLED_ACK、DONE。G 在 S 正常结束时核验自己的后代已清空后才向 C 发最终 DONE；
C 收到最终 DONE 并 wait G 退出才结束调用。

## 信号隔离

C 在 spawn G 前保存 mask 并临时阻塞 INT/TERM/HUP，安装只锁存首次取消的 handler，
spawn 后恢复 mask；G/S 在各自启动窗口重新阻塞并忽略这三个信号，核验 subreaper 后
才 READY/执行。目标 W 的信号策略（三个信号的 disposition 与原始 mask）由 C 在修改
handler 之前采集，随 START 交给 S，由独立 exec 引导路径恢复后再 exec 目标正文——
不用 `preexec_fn`，也不依赖 `restore_signals`。

## 取消

正常取消只走私有控制通道：C 的 handler/超时/`WF_CANCEL_FILE` 触发一次 CANCEL，
G 幂等转交给 S；S 清理后 DONE。C 死亡由 G 看到 EOF 后取消；G 死亡由 S 看到 EOF 后
清理；C 仍存活且监督边界失效时报告 cleanup=unknown 与恢复信息，不签成功。
"""
from __future__ import annotations

import argparse
import ctypes
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import re
import select
import signal
import socket
import struct
import subprocess
import sys
import tempfile
import time


PROTOCOL_VERSION = 1
FRAME_MAX = 1 << 20
PR_SET_CHILD_SUBREAPER = 36
PR_GET_CHILD_SUBREAPER = 37
SUPERVISOR_BOOT_SECONDS = 15.0
CLEANUP_GRACE_SECONDS = 5.0
TERMINATE_GRACE_SECONDS = 2.0
FAULT_SWITCH = 'WF_TEST_FAULT_INJECTION'
FAULT_TARGET_ENV = 'WF_EXECUTION_FAULT_TARGET'
FAULT_POINT_ENV = 'WF_EXECUTION_FAULT_POINT'
FAULT_ACTION_ENV = 'WF_EXECUTION_FAULT_ACTION'
FAULT_READY_FD_ENV = 'WF_EXECUTION_FAULT_READY_FD'
FAULT_POINTS = ('supervisor-before-ready', 'supervisor-after-started', 'guardian-after-started')
FAULT_ACTIONS = ('exception', 'exit', 'kill', 'hang')
FAULT_SELECTORS = (FAULT_TARGET_ENV, FAULT_POINT_ENV, FAULT_ACTION_ENV,
                   FAULT_READY_FD_ENV)
def _faults_enabled():
    """故障注入只在显式测试开关下生效（不按普通环境变量改变生产行为）。"""
    return os.environ.get('WF_TEST_FAULT_INJECTION') == '1'


def _supervision_grace():
    """取消后监督边界的收口预算；仅测试开关允许覆盖。"""
    if not _faults_enabled():
        # 必须覆盖 G 的最坏接管：G 取消宽限 8s + 清理宽限 5s，再留 1s 收尾；
        # 否则 C 会先杀 G，把本可由 G 收口的结果误报为 cleanup=unknown。
        return 14.0
    return float(os.environ.get('WF_SUPERVISION_GRACE') or 14.0)


def _guardian_cancel_grace():
    if not _faults_enabled():
        return 8.0
    return float(os.environ.get('WF_GUARDIAN_CANCEL_GRACE') or 8.0)


class Cancelled(Exception):
    def __init__(self, signum):
        self.signum = signum


class ProtocolError(Exception):
    """控制通道/协议错误（最终按设施失败归因）。"""


# ---- 控制通道帧 -------------------------------------------------------------


def _encode_frame(message):
    data = json.dumps(message, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    if len(data) > FRAME_MAX:
        raise ProtocolError("control frame is too large")
    return struct.pack("!I", len(data)) + data


def _send(sock, message):
    sock.sendall(_encode_frame(message))


def _recv_frames(sock, buffer):
    chunk = sock.recv(65536)
    if not chunk:
        raise EOFError("control channel closed")
    buffer += chunk
    messages = []
    while len(buffer) >= 4:
        length = struct.unpack("!I", buffer[:4])[0]
        if length > FRAME_MAX:
            raise ProtocolError("control frame is too large")
        if len(buffer) < 4 + length:
            break
        payload, buffer = buffer[4:4 + length], buffer[4 + length:]
        try:
            message = json.loads(payload)
        except ValueError as exc:
            raise ProtocolError(f"control frame is not JSON: {exc}") from exc
        if (not isinstance(message, dict) or message.get("v") != PROTOCOL_VERSION
                or not isinstance(message.get("type"), str)):
            raise ProtocolError("control frame has an invalid envelope")
        messages.append(message)
    return buffer, messages


def _control_socket(fd):
    return socket.socket(fileno=int(fd))


# ---- 子进程回收（S 正常清理与 G 故障接管共用同一实现）------------------------


def _set_subreaper():
    libc = ctypes.CDLL(None, use_errno=True)
    if libc.prctl(PR_SET_CHILD_SUBREAPER, 1, 0, 0, 0) != 0:
        raise OSError(ctypes.get_errno(), "PR_SET_CHILD_SUBREAPER failed")
    value = ctypes.c_int(0)
    if libc.prctl(PR_GET_CHILD_SUBREAPER, ctypes.byref(value), 0, 0, 0) != 0 or value.value != 1:
        raise OSError(ctypes.get_errno(), "child subreaper is not active")


def _snapshot():
    """pid → (ppid, starttime) 的只读快照；读取失败的条目直接跳过。"""
    table = {}
    for entry in Path("/proc").iterdir():
        if not entry.name.isdigit():
            continue
        try:
            fields = (entry / "stat").read_text().rsplit(")", 1)[1].split()
            table[int(entry.name)] = (int(fields[1]), int(fields[19]))
        except (OSError, ValueError, IndexError):
            continue
    return table


def _descendants(table, root=None):
    """root 的真实后代（按 ppid 链）；root 缺省为当前进程。"""
    root = os.getpid() if root is None else root
    children = {}
    for pid, (ppid, start) in table.items():
        children.setdefault(ppid, []).append((pid, start))
    found = set()
    pending = [root]
    while pending:
        pid = pending.pop()
        for child, start in children.get(pid, []):
            if child in found or child == root:
                continue
            found.add(child)
            pending.append(child)
    return found


def _reap_children():
    while True:
        try:
            pid, _status = os.waitpid(-1, os.WNOHANG)
        except ChildProcessError:
            return
        if pid == 0:
            return


def _start_time(pid):
    try:
        fields = Path(f"/proc/{pid}/stat").read_text().rsplit(")", 1)[1].split()
        return int(fields[19])
    except (OSError, ValueError, IndexError):
        return None


def _kill_pids(table, pids, signum):
    """发送信号前重新核对该 PID 的启动身份，避免快照后的 PID 复用误杀。"""
    for pid in pids:
        if pid == os.getpid() or pid not in table:
            continue
        if _start_time(pid) != table[pid][1]:
            continue
        try:
            os.kill(pid, signum)
        except (ProcessLookupError, PermissionError):
            pass


def cleanup_tree(deadline, grace=TERMINATE_GRACE_SECONDS):
    """终止并回收本进程拥有的全部后代；返回 (cleanup_state, remaining, reaped)。

    - 先按目标信号策略下的 SIGTERM，再在 deadline 内 SIGKILL；每次都重新枚举，避免
      fork/重新托管的窗口漏项；
    - 以真实亲缘（subreaper 收到 reparent 的孤儿）为范围，不按进程名或历史 PID；
    - 无法在 deadline 内回收的对象使 cleanup 保持 unknown/failed，调用方禁止签成功。
    """
    reaped = 0
    while True:
        _reap_children()
        table = _snapshot()
        pids = sorted(_descendants(table))
        if not pids:
            remaining = sorted(_descendants(_snapshot()))
            return ("cleaned" if not remaining else "unknown"), remaining, reaped
        if time.monotonic() >= deadline:
            break
        _kill_pids(table, pids, signal.SIGTERM)
        wait_until = min(deadline, time.monotonic() + grace)
        while time.monotonic() < wait_until:
            _reap_children()
            if not _descendants(_snapshot()):
                break
            time.sleep(0.02)
        if time.monotonic() >= deadline:
            break
        table = _snapshot()
        pids = sorted(_descendants(table))
        if not pids:
            continue
        _kill_pids(table, pids, signal.SIGKILL)
        while time.monotonic() < deadline:
            _reap_children()
            if not _descendants(_snapshot()):
                break
            time.sleep(0.02)
        _reap_children()
        if not _descendants(_snapshot()):
            return "cleaned", [], reaped
    _reap_children()
    remaining = sorted(_descendants(_snapshot()))
    return ("unknown" if remaining else "cleaned"), remaining, reaped


# ---- 目标信号策略 -----------------------------------------------------------


def _capture_target_policy():
    dispositions = []
    for signum in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP):
        handler = signal.getsignal(signum)
        dispositions.append("ignore" if handler == signal.SIG_IGN else "default")
    original_mask = signal.pthread_sigmask(signal.SIG_BLOCK, [])
    return {"dispositions": dispositions,
            "mask": sorted(int(signum) for signum in original_mask)}


def _apply_target_policy(policy):
    dispositions = policy.get("dispositions") or ["default", "default", "default"]
    for signum, disposition in zip((signal.SIGINT, signal.SIGTERM, signal.SIGHUP), dispositions):
        signal.signal(signum, signal.SIG_IGN if disposition == "ignore" else signal.SIG_DFL)
    # 恢复目标**原始 mask**：S 启动窗口会阻塞 INT/TERM/HUP，只“unblock 列表”无法撤销
    # S 额外加入的阻塞（目标会因此连 SIGTERM 都收不到，只能等 SIGKILL）。
    original = set(int(item) for item in policy.get("mask") or [])
    signal.pthread_sigmask(signal.SIG_SETMASK, original)


def _harden_supervisor_signals():
    """G/S 启动窗口屏蔽并忽略 INT/TERM/HUP：正常取消只走私有控制通道。"""
    for signum in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP):
        signal.signal(signum, signal.SIG_IGN)
    signal.pthread_sigmask(signal.SIG_BLOCK, {signal.SIGINT, signal.SIGTERM, signal.SIGHUP})


def _target_main(argv):
    """独立 exec 引导：恢复目标信号策略后 exec 目标正文（失败则不执行目标）。"""
    if not argv or "--" not in argv:
        return 2
    index = argv.index("--")
    try:
        policy = json.loads(argv[index - 1]) if index >= 1 else {}
    except ValueError:
        return 2
    target = argv[index + 1:]
    if not target:
        return 2
    try:
        _apply_target_policy(policy)
        os.execvpe(target[0], target, os.environ.copy())
    except OSError as exc:
        sys.stderr.write(f"TARGET-EXEC-FAILED: {exc}\n")
        return 127
    return 0


# ---- supervisor S -----------------------------------------------------------


def _wait_target(pid):
    try:
        result, status = os.waitpid(pid, os.WNOHANG)
    except ChildProcessError:
        return None
    if result == 0:
        return None
    return status


def _supervisor_main(raw):
    ctrl = _control_socket(raw["ctrl_fd"])
    log_fd = int(raw["log_fd"])
    extra_fds = [int(item) for item in raw.get("fds") or []]
    _harden_supervisor_signals()
    try:
        _set_subreaper()
    except OSError as exc:
        try:
            _send(ctrl, {"v": PROTOCOL_VERSION, "type": "DONE", "target_rc": None,
                         "infrastructure_error": True, "cleanup_state": "unknown",
                         "reason": f"supervisor cannot become subreaper: {exc}"})
        except (OSError, ProtocolError):
            pass
        return 1
    if _faults_enabled():
        try:
            ready_delay = float(os.environ.get("WF_SUPERVISOR_READY_DELAY") or 0)
        except ValueError:
            ready_delay = 0
        if ready_delay > 0:
            # 测试窗口：READY 前取消必须由 READY 分支经同一协议收口，不得启动目标。
            time.sleep(ready_delay)
    _apply_fault(raw.get("fault"), 'supervisor-before-ready')
    _send(ctrl, {"v": PROTOCOL_VERSION, "type": "READY", "id": 0,
                 "pid": os.getpid(), "subreaper": True})
    buffer = b""
    boot_deadline = time.monotonic() + SUPERVISOR_BOOT_SECONDS
    start = None
    cancel = None
    try:
        while start is None and cancel is None:
            if time.monotonic() >= boot_deadline:
                return 1
            readable, _, _ = select.select([ctrl], [], [], 0.05)
            if not readable:
                continue
            buffer, messages = _recv_frames(ctrl, buffer)
            for message in messages:
                if message["type"] == "START" and start is None:
                    start = message
                elif message["type"] == "CANCEL" and cancel is None:
                    cancel = message
    except (EOFError, ProtocolError, OSError):
        # G 已消失且未发 START：没有 W，退出即可（清理仍走外层 finally）。
        return 1

    if cancel is not None:
        _send(ctrl, {"v": PROTOCOL_VERSION, "type": "CANCELLED_ACK",
                     "id": cancel.get("id", 0), "signum": cancel.get("signum")})
        _send(ctrl, {"v": PROTOCOL_VERSION, "type": "DONE", "target_rc": None,
                     "cancelled": True, "signum": cancel.get("signum"),
                     "infrastructure_error": False, "cleanup_state": "cleaned",
                     "reason": f"cancelled before start: {cancel.get('reason', 'cancel')}"})
        return 0

    policy = start.get("policy") or {}
    deadline = float(start.get("deadline") or (time.monotonic() + 3600))
    argv = [str(item) for item in start.get("argv") or []]
    if not argv:
        _send(ctrl, {"v": PROTOCOL_VERSION, "type": "DONE", "target_rc": None,
                     "infrastructure_error": True, "cleanup_state": "cleaned",
                     "reason": "START carries no argv"})
        return 1
    stdout = log_fd if log_fd >= 0 else None
    target_env = {key: value for key, value in os.environ.items()
                  if key not in FAULT_SELECTORS}
    try:
        target = subprocess.Popen([sys.executable, os.path.abspath(__file__), "_target",
                                   json.dumps(policy), "--", *argv],
                                  stdout=stdout, stderr=subprocess.STDOUT if stdout is not None else None,
                                  stdin=None, restore_signals=False, env=target_env,
                                  pass_fds=tuple([log_fd] + extra_fds) if log_fd >= 0 else tuple(extra_fds))
    except OSError as exc:
        _send(ctrl, {"v": PROTOCOL_VERSION, "type": "DONE", "target_rc": None,
                     "infrastructure_error": True, "cleanup_state": "cleaned",
                     "reason": f"cannot launch target: {exc}"})
        return 1
    _send(ctrl, {"v": PROTOCOL_VERSION, "type": "STARTED", "id": start.get("id", 0),
                 "pid": os.getpid(), "target_pid": target.pid})
    _apply_fault(start.get("fault") or raw.get("fault"), 'supervisor-after-started')
    status = None
    cleanup_state = "cleaned"
    reason = ""
    cancelled = False
    signum = None
    try:
        fault = os.environ.get("WF_SUPERVISOR_FAULT") if _faults_enabled() else None
        if fault:
            # 测试注入只在显式开关下生效；延迟让目标先完成启动（覆盖 STARTED 之后窗口）。
            try:
                time.sleep(float(os.environ.get("WF_SUPERVISOR_FAULT_DELAY") or 0.5))
            except ValueError:
                pass
        if fault == "exception":
            raise RuntimeError("injected supervisor exception")
        if fault == "os_exit":
            os._exit(9)
        if fault == "kill":
            os.kill(os.getpid(), signal.SIGKILL)
        if fault == "hang":
            while True:
                time.sleep(1)
        while True:
            if status is None:
                status = _wait_target(target.pid)
            if status is not None:
                break
            readable, _, _ = select.select([ctrl], [], [], 0.05)
            if readable:
                buffer, messages = _recv_frames(ctrl, buffer)
                for message in messages:
                    if message["type"] == "CANCEL" and cancel is None:
                        cancel = message
                        _send(ctrl, {"v": PROTOCOL_VERSION, "type": "CANCELLED_ACK",
                                     "id": message.get("id", 0),
                                     "signum": message.get("signum")})
            if cancel is not None:
                cancelled = True
                signum = cancel.get("signum")
                reason = str(cancel.get("reason") or "cancelled")
                # 正常取消先只向目标发信号：嵌套 C 会经自己的通道收口内层 G/S；
                # 目标退出后再由 cleanup_tree 回收其真实残留后代。
                try:
                    os.kill(target.pid, signal.SIGTERM)
                except ProcessLookupError:
                    pass
                status = None
                grace_deadline = time.monotonic() + TERMINATE_GRACE_SECONDS
                while time.monotonic() < grace_deadline:
                    status = _wait_target(target.pid)
                    if status is not None:
                        break
                    time.sleep(0.02)
                if status is None:
                    try:
                        os.kill(target.pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                    while status is None:
                        status = _wait_target(target.pid)
                        time.sleep(0.01)
                break
            if time.monotonic() >= deadline:
                cancelled = True
                signum = 0
                reason = f"command deadline exceeded"
                try:
                    os.kill(target.pid, signal.SIGTERM)
                except ProcessLookupError:
                    pass
                status = None
                grace_deadline = time.monotonic() + TERMINATE_GRACE_SECONDS
                while time.monotonic() < grace_deadline:
                    status = _wait_target(target.pid)
                    if status is not None:
                        break
                    time.sleep(0.02)
                if status is None:
                    try:
                        os.kill(target.pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                    while status is None:
                        status = _wait_target(target.pid)
                        time.sleep(0.01)
                break
        cleanup_deadline = time.monotonic() + CLEANUP_GRACE_SECONDS
        cleanup_state, remaining, _reaped = cleanup_tree(cleanup_deadline)
        if cleanup_state != "cleaned":
            reason = (reason + "; " if reason else "") + "owned descendants remain: " + \
                     " ".join(str(pid) for pid in remaining[:20])
        target_rc = None
        target_signal = None
        if status is not None:
            if os.WIFEXITED(status):
                target_rc = os.WEXITSTATUS(status)
            elif os.WIFSIGNALED(status):
                target_signal = os.WTERMSIG(status)
                target_rc = 128 + target_signal
        _send(ctrl, {"v": PROTOCOL_VERSION, "type": "DONE", "id": start.get("id", 0),
                     "target_rc": target_rc,
                     "target_signal": target_signal, "cancelled": cancelled,
                     "signum": signum, "reason": reason,
                     "infrastructure_error": cleanup_state != "cleaned",
                     "cleanup_state": cleanup_state, "supervisor_pid": os.getpid()})
        return 0
    except BaseException as exc:  # 可捕获的 S 异常也必须收口后再报告
        cleanup_deadline = time.monotonic() + CLEANUP_GRACE_SECONDS
        cleanup_state, remaining, _reaped = cleanup_tree(cleanup_deadline)
        try:
            _send(ctrl, {"v": PROTOCOL_VERSION, "type": "DONE", "target_rc": None,
                         "infrastructure_error": True, "cleanup_state": cleanup_state,
                         "reason": f"supervisor failed: {type(exc).__name__}: {exc}",
                         "remaining": remaining[:20]})
        except (OSError, ProtocolError):
            pass
        return 1


# ---- guardian G -------------------------------------------------------------


def _guardian_main(raw):
    ctrl = _control_socket(raw["ctrl_fd"])
    log_fd = int(raw["log_fd"])
    extra_fds = [int(item) for item in raw.get("fds") or []]
    _harden_supervisor_signals()
    try:
        _set_subreaper()
    except OSError as exc:
        try:
            _send(ctrl, {"v": PROTOCOL_VERSION, "type": "DONE", "target_rc": None,
                         "infrastructure_error": True, "cleanup_state": "unknown",
                         "reason": f"guardian cannot become subreaper: {exc}"})
        except (OSError, ProtocolError):
            pass
        return 1
    gs, s = socket.socketpair()
    forward_fds = [s.fileno(), log_fd] + extra_fds
    try:
        supervisor = subprocess.Popen([sys.executable, os.path.abspath(__file__), "_supervisor",
                                       "--ctrl-fd", str(s.fileno()), "--log-fd", str(log_fd),
                                       "--fds", ",".join(str(fd) for fd in extra_fds),
                                       "--fault", json.dumps(raw.get("fault") or {})],
                                      pass_fds=tuple(fd for fd in forward_fds if fd >= 0),
                                      start_new_session=True)
    except OSError as exc:
        gs.close()
        s.close()
        try:
            _send(ctrl, {"v": PROTOCOL_VERSION, "type": "DONE", "target_rc": None,
                         "infrastructure_error": True, "cleanup_state": "unknown",
                         "reason": f"cannot launch supervisor: {exc}"})
        except (OSError, ProtocolError):
            pass
        return 1
    s.close()
    client_buffer = b""
    child_buffer = b""
    client_alive = True
    started = False
    cancel_sent = False
    cancel_deadline = None
    supervisor_done = None
    boot_deadline = time.monotonic() + SUPERVISOR_BOOT_SECONDS

    fault_spec = raw.get("fault") or None

    def relay_to_client(message):
        nonlocal client_alive
        if not client_alive:
            return
        try:
            payload = dict(message)
            payload["guardian_pid"] = os.getpid()
            _send(ctrl, payload)
        except (OSError, ProtocolError):
            client_alive = False

    guardian_fault = os.environ.get("WF_GUARDIAN_FAULT") if _faults_enabled() else None
    try:
        guardian_fault_delay = float(os.environ.get("WF_GUARDIAN_FAULT_DELAY") or 0.3)
    except ValueError:
        guardian_fault_delay = 0.3
    guardian_fault_deadline = time.monotonic() + guardian_fault_delay
    try:
        while True:
            readable, _, _ = select.select([ctrl, gs], [], [], 0.05)
            if ctrl in readable and client_alive:
                try:
                    client_buffer, messages = _recv_frames(ctrl, client_buffer)
                except EOFError:
                    client_alive = False
                    messages = []
                    if not cancel_sent:
                        cancel_sent = True
                        cancel_deadline = time.monotonic() + _guardian_cancel_grace()
                        try:
                            _send(gs, {"v": PROTOCOL_VERSION, "type": "CANCEL",
                                       "signum": 0, "reason": "caller disappeared"})
                        except (OSError, ProtocolError):
                            pass
                except (ProtocolError, OSError):
                    client_alive = False
                    messages = []
                for message in messages:
                    if message["type"] == "START":
                        started = True
                        fault_spec = fault_spec or message.get("fault")
                        _send(gs, message)
                    elif message["type"] == "CANCEL" and not cancel_sent:
                        cancel_sent = True
                        cancel_deadline = time.monotonic() + _guardian_cancel_grace()
                        try:
                            _send(gs, message)
                        except (OSError, ProtocolError):
                            pass
            if gs in readable:
                try:
                    child_buffer, messages = _recv_frames(gs, child_buffer)
                except EOFError:
                    messages = []
                except (ProtocolError, OSError):
                    messages = []
                for message in messages:
                    kind = message["type"]
                    if kind == "DONE":
                        supervisor_done = message
                    elif kind in ("READY", "STARTED", "CANCELLED_ACK"):
                        relay_to_client(message)
                        if kind == "STARTED":
                            _apply_fault(fault_spec, 'guardian-after-started')
            exited = supervisor.poll()
            if supervisor_done is not None:
                # S 已给出内部结果：先等它退出，再由 G 做最终后代核验并只发一份最终 DONE。
                try:
                    supervisor.wait(timeout=CLEANUP_GRACE_SECONDS)
                except subprocess.TimeoutExpired:
                    try:
                        os.kill(supervisor.pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                    supervisor.wait()
                break
            if exited is not None:
                # S 在给出结果前退出：G 作为存活接管方回收其真实后代。
                cleanup_state, remaining, _reaped = cleanup_tree(
                    time.monotonic() + CLEANUP_GRACE_SECONDS)
                supervisor_done = {
                    "v": PROTOCOL_VERSION, "type": "DONE", "target_rc": None,
                    "infrastructure_error": True, "cleanup_state": cleanup_state,
                    "reason": f"supervisor exited without result (rc={exited})"
                              + ("" if cleanup_state == "cleaned" else
                                 "; remaining: " + " ".join(str(pid) for pid in remaining[:20])),
                    "supervisor_pid": supervisor.pid}
                break
            if guardian_fault and started and time.monotonic() >= guardian_fault_deadline:
                if guardian_fault == "exception":
                    raise RuntimeError("injected guardian exception")
                if guardian_fault == "kill":
                    os.kill(os.getpid(), signal.SIGKILL)
                guardian_fault = None
            if (cancel_deadline is not None and supervisor.poll() is None
                    and time.monotonic() >= cancel_deadline):
                # S 存活但失联/卡住：有界宽限后由 G 终止 S 并接管其后代。
                try:
                    os.kill(supervisor.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                supervisor.wait()
                cleanup_state, remaining, _reaped = cleanup_tree(
                    time.monotonic() + CLEANUP_GRACE_SECONDS)
                supervisor_done = {
                    "v": PROTOCOL_VERSION, "type": "DONE", "target_rc": None,
                    "infrastructure_error": True, "cleanup_state": cleanup_state,
                    "reason": "supervisor did not acknowledge cancel in time"
                              + ("" if cleanup_state == "cleaned" else
                                 "; remaining: " + " ".join(str(pid) for pid in remaining[:20])),
                    "supervisor_pid": supervisor.pid}
                break
            if not started and time.monotonic() >= boot_deadline:
                # 握手超时：C 从未发 START 时协议保证没有 W，但仍需收已派生的 S。
                try:
                    os.kill(supervisor.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                supervisor.wait()
                cleanup_state, remaining, _reaped = cleanup_tree(
                    time.monotonic() + CLEANUP_GRACE_SECONDS)
                supervisor_done = {
                    "v": PROTOCOL_VERSION, "type": "DONE", "target_rc": None,
                    "infrastructure_error": True, "cleanup_state": cleanup_state,
                    "reason": "supervisor handshake timed out"}
                break
        # G 是 S 故障时的存活接管边界：最终核验必须由 G 自己确认后代清空。
        cleanup_state, remaining, _reaped = cleanup_tree(
            time.monotonic() + CLEANUP_GRACE_SECONDS)
        final = dict(supervisor_done or {
            "v": PROTOCOL_VERSION, "type": "DONE", "target_rc": None,
            "infrastructure_error": True, "cleanup_state": "unknown",
            "reason": "guardian reached final state without a result"})
        if cleanup_state != "cleaned":
            final["cleanup_state"] = cleanup_state
            final["infrastructure_error"] = True
            final["reason"] = (str(final.get("reason") or "")
                               + "; guardian leftover: "
                               + " ".join(str(pid) for pid in remaining[:20])).strip("; ")
        final["guardian_pid"] = os.getpid()
        relay_to_client(final)
        gs.close()
        return 0
    except BaseException as exc:  # G 的可捕获异常也必须取消/等待/接管后再报告
        try:
            _send(gs, {"v": PROTOCOL_VERSION, "type": "CANCEL", "signum": 0,
                       "reason": f"guardian failure: {exc}"})
        except (OSError, ProtocolError):
            pass
        try:
            supervisor.wait(timeout=CLEANUP_GRACE_SECONDS)
        except subprocess.TimeoutExpired:
            try:
                os.kill(supervisor.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            supervisor.wait()
        cleanup_state, remaining, _reaped = cleanup_tree(
            time.monotonic() + CLEANUP_GRACE_SECONDS)
        relay_to_client({"v": PROTOCOL_VERSION, "type": "DONE", "target_rc": None,
                         "infrastructure_error": True, "cleanup_state": cleanup_state,
                         "reason": f"guardian failed: {type(exc).__name__}: {exc}"})
        gs.close()
        return 1


# ---- 调用方 C ---------------------------------------------------------------


def _read_cancel_file(path):
    if not path:
        return False
    try:
        return Path(path).exists()
    except OSError:
        return False


class EvidenceError(Exception):
    """命令证据域不可用（启动前拒绝，不 fallback 到 standalone）。"""


def _path_error_class():
    try:
        import fixture_scope
        return fixture_scope.FixtureError
    except ImportError:
        return OSError


def _local_modules():
    here = os.path.dirname(os.path.abspath(__file__))
    if here not in sys.path:
        sys.path.insert(0, here)
    import resource_lifecycle
    import runner_cleanup
    return resource_lifecycle, runner_cleanup


def resolve_command_fault(identity):
    """C 侧唯一选择器解析：总开关 + owned scope + 精确本命令身份才返回 FaultSpec。

    未知点名/动作、目标不唯一、缺 scope 都在启动前拒绝；普通环境同名变量不生效。
    """
    if os.environ.get(FAULT_SWITCH) != '1':
        return None
    target = os.environ.get(FAULT_TARGET_ENV)
    if not target:
        return None
    point = os.environ.get(FAULT_POINT_ENV)
    action = os.environ.get(FAULT_ACTION_ENV)
    if point not in FAULT_POINTS:
        raise EvidenceError(f'unknown {FAULT_POINT_ENV}: {point!r}')
    if action not in FAULT_ACTIONS:
        raise EvidenceError(f'unknown {FAULT_ACTION_ENV}: {action!r}')
    import fixture_scope
    if fixture_scope.current_scope() is None:
        raise EvidenceError('execution fault injection requires an owned test scope')
    if identity is None:
        raise EvidenceError('execution fault injection needs the command identity')
    if target != identity:
        return None
    ready_fd = os.environ.get(FAULT_READY_FD_ENV)
    spec = {'point': point, 'action': action, 'target': target}
    if ready_fd:
        try:
            spec['ready_fd'] = int(ready_fd)
        except ValueError as exc:
            raise EvidenceError(f'invalid {FAULT_READY_FD_ENV}: {ready_fd!r}') from exc
        if spec['ready_fd'] < 0:
            raise EvidenceError(f'invalid {FAULT_READY_FD_ENV}: {ready_fd!r}')
    return spec


def _wait_test_ready(spec, where):
    """测试专用 ready 管道：目标实际初始化完成后才在固定点注入，不靠 sleep 竞猜。"""
    ready_fd = (spec or {}).get('ready_fd')
    if ready_fd is None:
        return
    try:
        readable, _, _ = select.select([ready_fd], [], [], 5.0)
        if readable:
            os.read(ready_fd, 1)
    except (OSError, ValueError):
        pass


def _apply_fault(spec, where):
    """只在已被 C 选中并随内部 START 送达的固定点执行有限动作。"""
    if not spec or spec.get('point') != where:
        return
    if where in ('supervisor-after-started', 'guardian-after-started'):
        _wait_test_ready(spec, where)
    action = spec.get('action')
    if action == 'exception':
        raise RuntimeError(f'injected fault at {where}')
    if action == 'exit':
        os._exit(9)
    if action == 'kill':
        os.kill(os.getpid(), signal.SIGKILL)
    if action == 'hang':
        while True:
            time.sleep(1)
    raise EvidenceError(f'unknown fault action: {action!r}')


class FinalDecision:
    """最终成功决策边界的一次观测结果（此后只渲染/发布，不再改变结论）。"""

    def __init__(self, cancelled, signum=None, reason=None):
        self.cancelled = bool(cancelled)
        self.signum = signum
        self.reason = reason


CANCEL_SIGNALS = (signal.SIGINT, signal.SIGTERM, signal.SIGHUP)


def _pending_signals():
    """内核待处理取消信号集合（读取点唯一；测试在屏蔽生效后、读取前注入信号）。"""
    try:
        return set(signal.sigpending()) & set(CANCEL_SIGNALS)
    except (AttributeError, OSError, ValueError):
        return set()


class CancellationScope:
    """共享取消作用域：controller 建立一次，内部 run 复用同一对象。

    目标 W 的原始 signal policy 必须在安装本作用域的 latch handler **之前**采集；
    作用域退出时只在 establishing 方恢复一次 handler/mask。
    """

    def __init__(self):
        self.policy = _capture_target_policy()
        self.latched = False
        self.signum = None
        self.reason = None
        self._saved_handlers = {}
        self._saved_mask = None
        self._installed = False

    def latch(self, signum, reason):
        if not self.latched:
            self.latched = True
            self.signum = signum
            self.reason = reason

    def _handler(self, signum, _frame):
        self.latch(signum, f'cancelled by signal {signum}')

    def install(self):
        if self._installed:
            return self
        self._saved_mask = signal.pthread_sigmask(
            signal.SIG_BLOCK, {signal.SIGINT, signal.SIGTERM, signal.SIGHUP})
        for signum in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP):
            self._saved_handlers[signum] = signal.signal(signum, self._handler)
        signal.pthread_sigmask(signal.SIG_SETMASK, self._saved_mask)
        self._installed = True
        return self

    def restore(self):
        if not self._installed:
            return
        for signum, handler in self._saved_handlers.items():
            signal.signal(signum, handler)
        if self._saved_mask is not None:
            signal.pthread_sigmask(signal.SIG_SETMASK, self._saved_mask)
        self._installed = False

    def consume_cancel(self, cancel_file=None):
        """非阻塞消费：返回本代取消事实（锁存值优先，其次已发布的取消标记）。"""
        if not self.latched and _read_cancel_file(cancel_file):
            self.latch(0, f'cancelled by {cancel_file}')
        return FinalDecision(self.latched, self.signum, self.reason)

    def final_decision(self, cancel_file=None):
        """最终成功决策边界：阻塞取消信号，观测标记/锁存/待处理信号后固定结论。

        决策后在本代 handler 仍有效时恢复原屏蔽状态，调用方随后只按已定结论发布与读回。
        """
        saved = signal.pthread_sigmask(signal.SIG_BLOCK, set(CANCEL_SIGNALS))
        try:
            if _read_cancel_file(cancel_file):
                self.latch(self.signum or 0, f'cancelled by {cancel_file}')
            pending = _pending_signals()
            if pending and not self.latched:
                signum = sorted(pending)[0]
                self.latch(signum, f'cancelled by pending signal {signum}')
            return FinalDecision(self.latched, self.signum, self.reason)
        finally:
            signal.pthread_sigmask(signal.SIG_SETMASK, saved)


def _check_anchor(path):
    """log/receipt 的最终父目录必须是无链接真实目录（缺失链由调用方安全创建）。"""
    parent = Path(path).parent
    try:
        parent.mkdir(parents=True, exist_ok=True)
    except OSError:
        raise
    current = parent
    while True:
        if current.is_symlink():
            raise OSError(f'log parent contains a symlink: {current}')
        if current.parent == current:
            break
        current = current.parent
    if Path(path).is_symlink():
        raise OSError(f'log path must not be a symlink: {path}')
    return parent


def _managed_evidence(log_path):
    """已声明 managed 上下文：不完整/不可验证一律拒绝（不降级 standalone）。"""
    lifecycle, _ = _local_modules()
    run_id = os.environ.get('WF_RUN_ID')
    evidence_root = os.environ.get('WF_COMMAND_EVIDENCE_ROOT')
    results_root = os.environ.get('WF_RESULTS_DIR')
    if not (run_id or evidence_root):
        return None
    if not (run_id and evidence_root and results_root):
        raise EvidenceError('incomplete managed evidence context（拒绝 fallback 到 standalone）')
    root = lifecycle.canonical_root(results_root)
    owner = lifecycle.classify_owner(root)
    if owner['kind'] != 'schema2' or owner['payload']['intent'] != 'execution':
        raise EvidenceError('managed evidence root has no execution owner')
    if owner['payload']['run_id'] != run_id:
        raise EvidenceError('managed evidence run_id mismatches the results owner')
    state = lifecycle.classify_run_state(root)
    if state['kind'] not in ('active', 'finished') or state['payload']['run_id'] != run_id:
        raise EvidenceError('managed evidence run-state is missing or belongs to another run')
    commands = os.path.realpath(evidence_root)
    expected = os.path.join(root, lifecycle.COMMANDS_DIR)
    if commands != expected:
        raise EvidenceError(f'managed evidence root must be {expected}')
    if not os.path.isdir(commands):
        raise EvidenceError(f'managed evidence root does not exist: {commands}')
    return {'evidence_scope': 'managed-child', 'root': commands, 'run_id': run_id}


def _evidence_descriptor(log_path, *, runner_control, receipt_path):
    lifecycle, _ = _local_modules()
    if runner_control:
        if not receipt_path:
            raise EvidenceError('root-control requires an explicit receipt path')
        return {'evidence_scope': 'root-control', 'path': str(receipt_path),
                'run_id': os.environ.get('WF_RUN_ID')}
    managed = _managed_evidence(log_path)
    if managed is not None:
        return managed
    scope_root = os.environ.get('WF_TEST_SCOPE_ROOT')
    if scope_root:
        import fixture_scope
        fixture_scope.ensure_in_scope(Path(log_path).parent, Path(log_path))
    return {'evidence_scope': 'standalone-command', 'root': str(Path(log_path).parent),
            'run_id': None}


def _receipt_record(descriptor, command_id, log_path, argv, cwd, local_cleanup, retained):
    return {
        'schema_version': 1,
        'command_id': command_id,
        'run_id': descriptor.get('run_id'),
        'evidence_scope': descriptor['evidence_scope'],
        'state': 'started',
        'argv': list(map(str, argv)),
        'cwd': str(cwd),
        'log_path': str(log_path),
        'started_at': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
        'finished_at': None,
        'result': None,
        'supervision': None,
        'local_cleanup': local_cleanup,
        'retained_paths': list(retained),
    }


def _receipt_path_for(descriptor, command_id, log_path):
    lifecycle, _ = _local_modules()
    if descriptor['evidence_scope'] == 'root-control':
        return descriptor['path']
    if descriptor['evidence_scope'] == 'managed-child':
        return lifecycle.receipt_path(descriptor['root'], command_id)
    return lifecycle.standalone_receipt_path(log_path, command_id)


def _prepare_isolated_home(home):
    """本 command 唯一的 HOME：先建立 owned marker/空根，再写 bootstrap 记录。"""
    import fixture_scope
    root = fixture_scope.reset(str(home))
    spec = importlib.util.spec_from_file_location('wf_test_bootstrap',
            Path(__file__).resolve().parents[4] / 'docs/workflows/wf/payload/bin/wf.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    scope, value, error = module.resolve_candidate(str(root), 'system')
    if error:
        raise RuntimeError(error)
    candidate, error = module.candidate_path(str(root), value)
    if error:
        raise RuntimeError(error)
    size, mtime = module.stat_tuple(candidate)
    write_json(root / '.wf/interpreters.json', {'interpreters': [{
        'scope': scope, 'project_id': None, 'key': 'python_executable',
        'config_value': value, 'path_identity': module.path_identity(value, str(root)),
        'size': size, 'mtime_ns': mtime, 'python_version': module.probe_version(candidate),
        'confirmed_at': 'test-fixture'}]})
    return root


def _finish_receipt(path, command_id, updates):
    lifecycle, _ = _local_modules()
    return lifecycle.update_receipt(path, command_id, updates)


def _result_projection(result):
    return {key: result.get(key) for key in
            ('rc', 'status', 'seconds', 'reason', 'supervision')}


def _record_local(evidence_path, command_id, home, state, reason=None, origin='local'):
    lifecycle, _cleanup = _local_modules()
    updates = {'local_cleanup': state, 'retained_paths': [str(home)] if home else []}
    if reason:
        updates['local_reason'] = f'{origin}: {reason}'
    lifecycle.update_receipt(evidence_path, command_id, updates)


def run(argv, log_path, *, timeout, cwd=None, env=None, inherit_output=False, pass_fds=(),
        scope=None, isolated_user=False, runner_control=False, receipt_path=None,
        local_dirs=(), fault_identity=None, retain_local=False):
    """Run one command under the C→G→S→W supervision described in the module docstring.

    `scope` 由 controller 传入时复用同一取消作用域；`isolated_user` 在本 command 的
    command_id 下建立唯一 HOME，并在 supervision 结论之后决定删除/保留；`runner_control`
    只由 root controller 使用（证据写 `.runner.json`）。`retain_local=True` 表示调用方显式
    请求保留本 command 的局部路径（repro 的 `WF_REPRO_KEEP=1`）：supervision 清理已确认后
    仍按 `retained-keep` 登记，且该相位不进入 proof。
    """
    if not math.isfinite(timeout) or timeout <= 0:
        raise ValueError('command timeout must be positive and finite')
    lifecycle, _cleanup = _local_modules()
    log_path = Path(os.path.abspath(log_path))
    target_cwd = Path(os.path.abspath(cwd or Path.cwd()))
    _check_anchor(log_path)
    started = time.monotonic()
    deadline = started + timeout
    result = {'schema_version': 2, 'argv': list(map(str, argv)),
              'cwd': str(target_cwd), 'log_path': str(log_path),
              'rc': 1, 'status': 'failed', 'reason': '', 'protocol_version': PROTOCOL_VERSION,
              'supervision': {'cleanup_state': 'unknown', 'infrastructure_error': True}}
    command_id = lifecycle.new_command_id()
    descriptor = _evidence_descriptor(log_path, runner_control=runner_control,
                                      receipt_path=receipt_path)
    evidence_path = _receipt_path_for(descriptor, command_id, log_path)
    home = Path(str(log_path) + '.home-' + command_id) if isolated_user else None
    local_paths = ([str(home)] if home else []) + [os.path.abspath(item) for item in local_dirs]
    receipt = _receipt_record(descriptor, command_id, log_path, argv, target_cwd,
                              'pending' if local_paths else 'none', local_paths)
    fault_spec = resolve_command_fault(fault_identity)
    lifecycle.write_receipt(evidence_path, receipt)
    own_scope = scope is None
    scope = (scope or CancellationScope()).install()
    result['command_id'] = command_id
    result['evidence_path'] = evidence_path
    result['local_dirs'] = [os.path.abspath(item) for item in local_dirs]
    result['local_keep'] = bool(retain_local)
    cancel_file = os.environ.get('WF_CANCEL_FILE')
    log_fd = -1
    guardian = None
    channel = None
    parent = None
    try:
        if home is not None:
            try:
                _prepare_isolated_home(home)
            except Exception as exc:
                result.update(status='failed', rc=1,
                              reason=f'isolated home preparation failed: {exc}',
                              local_prepare_failed=True)
                return result
            env = {**(os.environ if env is None else env), 'HOME': str(home)}
        log_fd = os.open(log_path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC | os.O_NOFOLLOW, 0o600)
        # inherit_output：目标直接继承调用方控制台；日志只保留失败原因（与旧行为一致）。
        guardian_log_fd = log_fd if not inherit_output else -1
        extra_fds = [int(fd) for fd in pass_fds]
        parent, child = socket.socketpair()
        try:
            guardian = subprocess.Popen(
                [sys.executable, os.path.abspath(__file__), '_guardian',
                 '--ctrl-fd', str(child.fileno()), '--log-fd', str(guardian_log_fd),
                 '--fds', ','.join(str(fd) for fd in extra_fds),
                 '--fault', json.dumps(fault_spec or {})],
                pass_fds=tuple([child.fileno()] + ([log_fd] if guardian_log_fd >= 0 else [])
                               + extra_fds),
                start_new_session=True, cwd=cwd, env=env)
        finally:
            child.close()
        channel = parent
        os.close(log_fd)
        log_fd = -1
        buffer = b''
        ready = False
        start_sent = False
        cancel_sent = False
        supervisor_pid = None
        target_pid = None
        done = None
        cleanup_deadline = None
        while True:
            now = time.monotonic()
            if scope.latched is False and _read_cancel_file(cancel_file):
                scope.latch(signal.SIGTERM, 'cancelled by cancel file')
            if scope.latched and start_sent and not cancel_sent and channel is not None:
                # 已发 START：立即经同一通道取消（READY 之前的取消由 READY 分支发送）。
                cancel_sent = True
                cleanup_deadline = now + _supervision_grace()
                try:
                    _send(channel, {'v': PROTOCOL_VERSION, 'type': 'CANCEL', 'id': command_id,
                                    'signum': scope.signum, 'reason': scope.reason})
                except (OSError, ProtocolError):
                    channel = None
            if now >= deadline and not scope.latched:
                scope.latch(0, f'TIMEOUT after {timeout:g}s')
                cleanup_deadline = now + _supervision_grace()
                if start_sent and not cancel_sent and channel is not None:
                    cancel_sent = True
                    try:
                        _send(channel, {'v': PROTOCOL_VERSION, 'type': 'CANCEL', 'id': command_id,
                                        'signum': 0, 'reason': scope.reason})
                    except (OSError, ProtocolError):
                        channel = None
            if channel is not None:
                readable, _, _ = select.select([channel], [], [], 0.02)
            else:
                readable, _, _ = ([], [], [])
                time.sleep(0.02)
            if readable:
                try:
                    buffer, messages = _recv_frames(channel, buffer)
                except EOFError:
                    channel = None
                    messages = []
                except (ProtocolError, OSError):
                    result['reason'] = 'supervision control channel failed'
                    channel = None
                    messages = []
                for message in messages:
                    kind = message['type']
                    if kind == 'READY':
                        ready = True
                        result['supervision']['guardian_pid'] = message.get('guardian_pid')
                        if not scope.latched:
                            start_sent = True
                            try:
                                _send(channel, {'v': PROTOCOL_VERSION, 'type': 'START', 'id': command_id,
                                                'policy': scope.policy, 'argv': result['argv'],
                                                'deadline': deadline, 'fault': fault_spec})
                            except (OSError, ProtocolError):
                                channel = None
                        else:
                            # 取消先于 START：协议保证不会启动 W，但仍须经同一通道收口。
                            cancel_sent = True
                            cleanup_deadline = time.monotonic() + _supervision_grace()
                            try:
                                _send(channel, {'v': PROTOCOL_VERSION, 'type': 'CANCEL', 'id': command_id,
                                                'signum': scope.signum, 'reason': scope.reason})
                            except (OSError, ProtocolError):
                                channel = None
                    elif kind == 'STARTED':
                        supervisor_pid = message.get('pid')
                        target_pid = message.get('target_pid')
                    elif kind == 'DONE':
                        done = message
            if done is not None:
                break
            if guardian.poll() is not None and channel is None:
                break
            if guardian.poll() is not None and channel is not None:
                # G 已退出：把剩余可读帧读完再判失败（可能刚发出 DONE）。
                try:
                    deadline_read = time.monotonic() + 0.2
                    while time.monotonic() < deadline_read:
                        readable, _, _ = select.select([channel], [], [], 0.02)
                        if not readable:
                            continue
                        buffer, messages = _recv_frames(channel, buffer)
                        for message in messages:
                            if message['type'] == 'STARTED':
                                supervisor_pid = message.get('pid')
                                target_pid = message.get('target_pid')
                            elif message['type'] == 'DONE':
                                done = message
                        if done is not None:
                            break
                except (EOFError, ProtocolError, OSError):
                    pass
                break
            if cleanup_deadline is not None and time.monotonic() >= cleanup_deadline:
                result['reason'] = result['reason'] or 'cleanup deadline exceeded'
                break
        if guardian is not None:
            try:
                wait_budget = max(0.1, (cleanup_deadline or (time.monotonic() + 5.0))
                                  - time.monotonic())
                guardian_rc = guardian.wait(timeout=wait_budget)
            except subprocess.TimeoutExpired:
                guardian.kill()
                guardian.wait()
                result['supervision']['cleanup_state'] = 'unknown'
                result['supervision']['infrastructure_error'] = True
                result['reason'] = result['reason'] or 'guardian did not finish cleanup'
                guardian_rc = None
        else:
            guardian_rc = None
        if channel is not None:
            channel.close()
            channel = None
        try:
            parent.close()
        except OSError:
            pass
        supervision = result['supervision']
        supervision.update(guardian_pid=supervision.get('guardian_pid'),
                           guardian_rc=guardian_rc, supervisor_pid=supervisor_pid,
                           target_pid=target_pid)
        if done is None:
            supervision['infrastructure_error'] = True
            supervision['cleanup_state'] = supervision.get('cleanup_state', 'unknown')
            result.update(status='failed',
                          rc=124 if (scope.reason or '').startswith('TIMEOUT') else 1,
                          reason=result['reason'] or (scope.reason
                                                      or 'supervision lost before a final result'))
        else:
            supervision.update(cleanup_state=done.get('cleanup_state', 'unknown'),
                               infrastructure_error=bool(done.get('infrastructure_error')),
                               target_rc=done.get('target_rc'),
                               target_signal=done.get('target_signal'),
                               termination_reason=done.get('reason') or '',
                               guardian_pid=done.get('guardian_pid') or supervision.get('guardian_pid'))
            target_rc = done.get('target_rc')
            if done.get('infrastructure_error'):
                result.update(status='failed', rc=1,
                              reason=done.get('reason') or 'supervision infrastructure failure')
            elif done.get('cancelled'):
                signum = done.get('signum') or 0
                timed_out = (scope.reason or '').startswith('TIMEOUT') or \
                            str(done.get('reason') or '').startswith('command deadline exceeded')
                result.update(status='timeout' if timed_out else 'cancelled',
                              rc=124 if timed_out else ((128 + int(signum)) if signum
                                                        else (target_rc or 1)),
                              reason=done.get('reason') or 'cancelled')
            elif target_rc is None:
                result.update(status='failed', rc=1,
                              reason=done.get('reason') or 'target produced no exit status')
            else:
                result.update(rc=int(target_rc),
                              status='passed' if target_rc == 0 else 'failed',
                              reason='' if target_rc == 0 else (done.get('reason') or ''))
        if scope.latched and result['status'] == 'passed':
            # 取消或设施故障先于最终确认时，目标 rc=0 也不得取绿。
            signum = scope.signum or 0
            result.update(status='cancelled',
                          rc=(128 + int(signum)) if signum else 1,
                          reason=scope.reason or 'cancelled')
        if result['reason']:
            try:
                with open(log_path, 'ab') as stream:
                    stream.write(('\n' + result['reason'] + '\n').encode())
            except OSError:
                pass
        return result
    finally:
        if own_scope:
            scope.restore()
        if log_fd >= 0:
            try:
                os.close(log_fd)
            except OSError:
                pass
        if guardian is not None and guardian.poll() is None:
            try:
                guardian.kill()
            except ProcessLookupError:
                pass
            guardian.wait()
        if channel is not None:
            channel.close()
        if parent is not None:
            try:
                parent.close()
            except OSError:
                pass
        result['seconds'] = round(time.monotonic() - started, 6)
        _finalize_evidence(result, evidence_path, command_id, home, log_path)


def _remove_local_dir(path, anchor):
    """只删本 command 声明过的 local 根：有 fixture marker 的走 owned 入口，其余必须在
    log 锚点之内（worker 相位 TMPDIR），拒绝跟随链接。"""
    import fixture_scope
    path = Path(path)
    if not path.exists() and not path.is_symlink():
        return True
    if path.is_symlink():
        raise OSError(f'local resource is a symlink: {path}')
    if fixture_scope.marker(path).is_file():
        fixture_scope.remove(str(path))
        return True
    anchor = Path(anchor).absolute()
    try:
        path.relative_to(anchor)
    except ValueError:
        raise OSError(f'local resource is outside the log anchor: {path}')
    import shutil
    shutil.rmtree(path)
    return True


def _finalize_evidence(result, evidence_path, command_id, home, log_path):
    """写 finished receipt 并按 supervision 结论收口本 command 的 local 资源。"""
    lifecycle, cleanup = _local_modules()
    local_paths = ([str(home)] if home is not None else []) + list(result.get('local_dirs') or [])
    local_state = 'none' if not local_paths else 'retained-unknown'
    retained = list(local_paths)
    try:
        supervision = result.get('supervision') or {}
        if local_paths:
            if result.get('local_prepare_failed'):
                local_state, retained = 'failed', list(local_paths)
            elif result.get('local_keep'):
                # 显式 KEEP：保留真实路径，并让相位证据明确“未确认回收”。
                local_state, retained = 'retained-keep', list(local_paths)
            elif supervision.get('cleanup_state') == 'cleaned' and result.get('status') in (
                    'passed', 'failed', 'cancelled', 'timeout'):
                failed = []
                for item in local_paths:
                    try:
                        _remove_local_dir(item, Path(log_path).parent)
                    except OSError as exc:
                        failed.append(item)
                        result['local_cleanup_error'] = str(exc)
                local_state = 'failed' if failed else 'removed'
                retained = failed
            else:
                local_state = ('failed' if supervision.get('cleanup_state') == 'failed'
                               else 'retained-unknown')
                retained = list(local_paths)
        result['local_cleanup'] = local_state
        result['retained_paths'] = retained
        updates = {'state': 'finished',
                   'finished_at': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
                   'result': _result_projection(result),
                   'supervision': result.get('supervision'),
                   'local_cleanup': local_state,
                   'retained_paths': retained}
        lifecycle.update_receipt(evidence_path, command_id, updates)
    except (lifecycle.LifecycleError, OSError) as exc:
        # 写 finished 失败：保留 started，原非零 rc 保持；原 0 转非零并归因。
        result['evidence_error'] = f'receipt finish failed: {exc}'
        if result.get('rc') == 0:
            result['rc'] = 1
            result['status'] = 'failed'
        result['reason'] = (result.get('reason') or '') + '; ' + result['evidence_error']


def write_json(path, payload):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile('w', encoding='utf-8', dir=path.parent,
                                         prefix='.' + path.name, delete=False) as stream:
            temporary = Path(stream.name)
            json.dump(payload, stream, ensure_ascii=False, indent=2, sort_keys=True)
            stream.write('\n')
            stream.flush()
            os.fsync(stream.fileno())
        temporary.replace(path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def verdict(log_path, rc, kind, expected=None, phase=None):
    """Interpret actual assertions, never arbitrary occurrences of PASS.

    `repro` mode requires the explicit phase being proven (`green|red`): a log that only
    carries the opposite phase's PASS line, or contradictory PASS/FAIL lines, proves
    nothing.  Missing phase is a caller error, never a silent "any PASS counts" branch.
    """
    if kind == 'repro':
        if phase not in ('green', 'red'):
            raise ValueError('repro verdict requires an explicit green|red phase')
    elif phase is not None:
        raise ValueError('phase is only meaningful for repro verdicts')
    try:
        text = Path(log_path).read_text(encoding='utf-8', errors='replace')
    except OSError as exc:
        return {'ok': False, 'assertions': 0, 'passed': 0, 'observed': 0, 'tail': '',
                'reason': f'log is unreadable: {exc}'}
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    tail = lines[-1] if lines else ''
    failures = sum(bool(re.search(r'\[FAIL\]|(?:^|:\s*)FAIL(?:\b|$)', line)) for line in lines)
    passed = sum(bool(re.search(r'^\[PASS\](?:\s|$)|^PASS(?:\s|$)|^\[[^]]+\].*:\s*PASS(?:\s|$)', line)) for line in lines)
    if kind == 'suite' and re.fullmatch(r'TASK_ID [a-zA-Z0-9-]+', tail):
        kind = 'steps'
    evidence = passed
    # 「用例数」的唯一观测点：PASS 行形态数（raw/suite/flow/repro），步骤型输出则是
    # 通过的 step 行数——它与 `expect` 预算比较；`passed` 仍保持 PASS 行计数以兼容既有消费者。
    observed = passed
    if kind == 'suite':
        summary = re.fullmatch(r'(?:saved|total)\s+(\d+)\s*/\s*(\d+)', tail)
        alternative = re.fullmatch(r'saved\s+(\d+)\s+(?:cases|checks);\s*(\d+)\s+passed', tail)
        count = re.fullmatch(r'saved\s+(\d+)\s+cases', tail)
        if summary:
            good, total = map(int, summary.groups())
            evidence = total if total > 0 and good == total else 0
        elif alternative:
            total, good = map(int, alternative.groups())
            evidence = total if total > 0 and good == total else 0
        elif count:
            total = int(count.group(1))
            evidence = total if passed == total and total > 0 else 0
        else:
            evidence = 0
    elif kind == 'steps':
        steps = [line for line in lines if re.match(r'^\[[^]]+\] exit=', line)]
        evidence = len(steps) if steps and re.fullmatch(r'TASK_ID [a-zA-Z0-9-]+', tail) else 0
        if any(not re.fullmatch(r'\[[^]]+\] exit=0 code=WF_OK', line) for line in steps):
            evidence = 0
        observed = evidence
    elif kind == 'repro':
        # detail 之后还可能跟着多行原因块：只承认**本次相位**的 PASS 行；相反相位的
        # PASS 或任何 FAIL 行都使证据无效（不能证明本次相位成立）。
        matching = [line for line in lines if re.match(rf'^PASS {phase}: .+', line)]
        opposite = 'red' if phase == 'green' else 'green'
        contrary = [line for line in lines if re.match(rf'^PASS {opposite}: ', line)]
        evidence = 1 if matching and not contrary else 0
        if contrary:
            failures += 1
    elif kind == 'raw':
        evidence = 1
    ok = rc == 0 and failures == 0 and evidence > 0
    if expected is not None:
        ok = ok and observed == expected
    reason = '' if ok else f'rc={rc} observed={observed} failures={failures} expected={expected}'
    if kind == 'repro' and phase and not evidence:
        reason += f' phase={phase}'
    return {'ok': ok, 'assertions': evidence, 'passed': passed, 'observed': observed,
            'tail': tail, 'phase': phase, 'reason': reason}


def _controller_refuse(message):
    print(f'RUNNER-CONTROL-REFUSED: {message}', file=sys.stderr)
    return 1


def _read_plan_bytes(path, limit=1 << 20):
    """有界、拒绝符号链接地读取一次冻结计划（token 与内容必须来自同一份字节）。"""
    if not os.path.isfile(path) or os.path.islink(path):
        raise EvidenceError(f'frozen plan is not a plain file: {path}')
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        data = os.read(fd, limit)
        if os.read(fd, 1):
            raise EvidenceError(f'frozen plan exceeds {limit} bytes: {path}')
    finally:
        os.close(fd)
    return data


def _verify_controller_context(args, lifecycle):
    """核 controller 的租约/owner/run-state/冻结 plan；任何不符都拒绝，不重做初始化。

    两个 role 都必须带同一份已冻结计划：独立 repro 不再从环境合成执行请求。
    """
    import fixture_scope
    import runner_protocol
    fixture_scope.verify_lease()
    fixture_scope.verify_results_lock()
    root = lifecycle.canonical_root(args.results_root)
    if not isinstance(args.run_id, str) or not args.run_id:
        raise EvidenceError('--run-id is required for the controller')
    if args.runner_role not in lifecycle.ROLES:
        raise EvidenceError(f'--runner-role must be one of {lifecycle.ROLES}')
    owner = lifecycle.classify_owner(root)
    if owner['kind'] != 'schema2' or owner['payload']['intent'] != 'execution':
        raise EvidenceError('results root has no execution owner (begin_run missing)')
    if owner['payload']['run_id'] != args.run_id:
        raise EvidenceError('results owner run_id differs from the controller run_id')
    state = lifecycle.classify_run_state(root)
    if state['kind'] != 'active' or state['payload']['run_id'] != args.run_id:
        raise EvidenceError('run-state is not the active generation of this run_id')
    if not args.plan_file or not args.plan_sha256 or not args.plan_size:
        raise EvidenceError('controller requires the frozen plan identity')
    data = _read_plan_bytes(args.plan_file)
    digest = hashlib.sha256(data).hexdigest()
    if digest != args.plan_sha256 or str(len(data)) != str(args.plan_size):
        raise EvidenceError('frozen plan bytes do not match the controller token')
    try:
        plan = json.loads(data)
    except ValueError as exc:
        raise EvidenceError(f'frozen plan is not JSON: {exc}') from exc
    try:
        runner_protocol.validate_plan(plan, role=args.runner_role, run_id=args.run_id,
                                      results_dir=root,
                                      scope_root=os.environ.get('WF_TEST_SCOPE_ROOT') or None)
    except runner_protocol.FrameError as exc:
        raise EvidenceError(f'frozen plan rejected: {exc}') from exc
    if os.path.realpath(args.plan_file) != os.path.join(root, 'plan.json'):
        raise EvidenceError('frozen plan must live at <results root>/plan.json')
    return root, plan


def _legacy_snapshot(plan):
    """已知技术债清单：只接受注册过的单元名，快照后交给同一 gate。"""
    raw = os.environ.get('WF_KNOWN_LEGACY') or ''
    names = raw.split()
    if not names:
        return ''
    import importlib.util
    with open(Path(__file__).resolve().parent / 'units.json', encoding='utf-8') as handle:
        registry = {entry['name'] for entry in json.load(handle)['units']}
    unknown = [name for name in names if name not in registry]
    if unknown:
        raise EvidenceError('legacy debt names are not registered units: ' + ' '.join(unknown))
    planned = {entry['name'] for entry in plan.get('units') or []}
    if not set(names) & planned:
        raise EvidenceError('legacy debt names do not participate in this plan')
    return ' '.join(names)


def _repro_bundle_fact(root):
    path = Path(root) / 'repro.bundle.json'
    if not path.is_file() or path.is_symlink():
        return None, None
    try:
        record = json.loads(path.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return None, None
    return record.get('sha256'), record.get('size')


def _repro_gate_report(root, plan, run_id=None, evidence_root=None):
    """独立 repro：只用本代 bundle/records（不造 lines/units，也不读 full metrics）。"""
    import results_gate
    bundle = Path(root) / 'inputs.json'
    if not bundle.is_file():
        raise EvidenceError('repro bundle is missing')
    report = results_gate.repro_report(
        str(root), run_id=run_id,
        evidence_root=evidence_root or str(Path(root) / 'commands'))
    counts = {"suite_ran": 0, "flow_ran": 0, "repro_ran": int(report.get('total') or 0),
              "units_total": int(report.get('total') or 0),
              "fail": int(report.get('failed') or 0), "bad": 0, "extra_failures": 0,
              "repro_fail": int(report.get('failed') or 0), "legacy_debt": 0,
              "unregistered_fail": 0, "debt_failed": [], "debt_fixed": [], "debt_missing": []}
    gate = {"malformed": len(report.get('malformed') or []),
            "missing": report.get('missing') or [], "duplicate": [], "unexpected": [],
            "bad": [], "repro_fail": counts['repro_fail'],
            "extra_failures": counts['extra_failures']}
    return {"ok": bool(report.get('ok')), "gate": gate, "repro": report, "counts": counts,
            "reasons": report.get('reasons') or []}


def _gate_report(root, plan, plan_path):
    import results_gate
    lines = Path(root) / 'lines'
    # 缺 lines 是“证据不完整”，不是 controller 崩溃：交给同一 assess_run_results 归因，
    # 取消/早退仍按真实清理事实收口（不签成功）。
    legacy = _legacy_snapshot(plan)
    repro_root = Path(root) / 'repro' if plan.get('repro_enabled') else None
    bundle_sha, bundle_size = (_repro_bundle_fact(str(repro_root))
                               if repro_root else (None, None))
    return results_gate.assess_run_results(
        str(plan_path), str(lines), str(repro_root) if repro_root else None,
        bundle_sha, bundle_size, legacy, run_id=os.environ.get('WF_RUN_ID'),
        evidence_root=str(Path(root) / 'commands'))


def _unknown_assessment(gate_report, reason):
    return {"schema_version": 1, "cleanup_state": "unknown", "evidence_state": "incomplete",
            "reasons": [reason], "problems": [{"kind": "controller", "detail": reason}],
            "retained_paths": [], "commands": [], "units": [],
            "target": {"cleanup_state": "unknown", "status": None, "rc": None},
            "gate": gate_report, "repro": (gate_report or {}).get("repro")}


def _assess_with_faults(root, run_id, plan, control, gate_report, fault, cleanup):
    if fault == 'assess-exception':
        raise RuntimeError('injected assess_run exception')
    assessment = cleanup.assess_run(root, run_id, plan, control, gate_report)
    if fault == 'assess-none':
        assessment = None
    elif fault == 'assess-empty':
        assessment = {}
    elif fault == 'assess-malformed':
        assessment = {"cleanup_state": "cleaned", "problems": "not-a-list",
                      "retained_paths": [], "target": {"cleanup_state": "cleaned"}}
    elif fault == 'assess-contradictory':
        assessment = dict(assessment, cleanup_state='cleaned',
                          problems=[{"kind": "pending", "detail": "injected contradiction"}])
    try:
        return cleanup.validate_assessment(assessment)
    except cleanup.CleanupError as exc:
        return _unknown_assessment(gate_report, f"assessment rejected: {exc}")


def _summary_report(gate_report, assessment, cleanup_report, control):
    counts = dict((gate_report or {}).get('counts') or {})
    control_failed = (control.get('status') != 'passed')
    counts.setdefault('suite_ran', 0)
    counts.setdefault('flow_ran', 0)
    counts.setdefault('repro_ran', 0)
    counts.setdefault('units_total', 0)
    counts.setdefault('legacy_debt', 0)
    counts.setdefault('bad', 0)
    counts.setdefault('extra_failures', 0)
    counts.setdefault('repro_fail', 0)
    counts.setdefault('unregistered_fail', 0)
    counts['fail'] = int(counts.get('fail') or 0) + (1 if control_failed else 0)
    ok = (bool((gate_report or {}).get('ok')) and assessment['cleanup_state'] == 'cleaned'
          and assessment['evidence_state'] == 'complete'
          and cleanup_report['cleanup_state'] == 'cleaned' and not control_failed)
    reasons = list(assessment.get('reasons') or []) + list(cleanup_report.get('reasons') or [])
    if control_failed:
        reasons.append(f"control status is {control.get('status')!r} (rc={control.get('rc')})")
    cancelled = control.get('status') in ('cancelled', 'timeout')
    return {
        "ok": ok,
        "failure_kind": (None if ok else ("cancelled" if cancelled else "failed")),
        "counts": counts,
        "gate": (gate_report or {}).get('gate') or {
            "malformed": 0, "missing": [], "duplicate": [], "unexpected": [],
            "bad": [], "repro_fail": counts.get('repro_fail', 0),
            "extra_failures": counts.get('extra_failures', 0)},
        "repro": (gate_report or {}).get('repro') or {},
        "cleanup_state": cleanup_report['cleanup_state'],
        "cleanup_report": cleanup_report,
        "evidence_state": assessment['evidence_state'],
        "reasons": reasons[:50],
    }


FAULT_SELECTOR_ENV = (
    'WF_RUNNER_FINALIZE_FAULT', 'WF_RESULTS_INIT_STOP_AFTER',
    'WF_TEMPLATE_TXN_STOP_AFTER', 'WF_TEST_RELEASE_TXN_STOP_AFTER',
    'WF_EXECUTION_FAULT_TARGET', 'WF_EXECUTION_FAULT_POINT', 'WF_EXECUTION_FAULT_ACTION',
    'WF_SUPERVISOR_FAULT', 'WF_GUARDIAN_FAULT', 'WF_UNIT_FAULT', 'WF_METRICS_FAULT',
)


def _child_environment(fault, results_summary):
    """受限 fault 的交接：每个命令只按自己的身份匹配选择器；W 由 S 在 spawn 时剥离。

    controller 级别的 `WF_RUNNER_FINALIZE_FAULT` 不进子进程；execution G/S 选择器保留给
    各 C 解析（不匹配即忽略）；metrics spec 只用显式 `--fault` 交给本次 write_metrics。
    """
    env = {key: value for key, value in os.environ.items()
           if key != 'WF_RUNNER_FINALIZE_FAULT'}
    env.pop('WF_METRICS_FAULT', None)
    if fault in results_summary.METRICS_FAULTS:
        env['WF_METRICS_FAULT'] = fault
    return env


def validate_execution_selector():
    """controller 启动前的选择器预检：非法点名/缺 scope 在 root 启动前拒绝。"""
    if os.environ.get(FAULT_SWITCH) != '1':
        return
    target = os.environ.get(FAULT_TARGET_ENV)
    if not target:
        return
    point = os.environ.get(FAULT_POINT_ENV)
    action = os.environ.get(FAULT_ACTION_ENV)
    if point not in FAULT_POINTS or action not in FAULT_ACTIONS:
        raise EvidenceError(f'unknown execution fault point/action: {point!r}/{action!r}')
    import fixture_scope
    if fixture_scope.current_scope() is None:
        raise EvidenceError('execution fault injection requires an owned test scope')


def _log_json(log_path):
    """准备/终结命令从自己的监督日志读回唯一 JSON 结果行（stdout 已被监督日志捕获）。"""
    try:
        text = Path(log_path).read_text(encoding='utf-8', errors='replace')
    except OSError:
        return None
    for line in reversed(text.splitlines()):
        line = line.strip()
        if not line.startswith('{'):
            continue
        try:
            value = json.loads(line)
        except ValueError:
            continue
        if isinstance(value, dict):
            return value
    return None


def _release_identity(plan):
    """冻结计划 → 本次发行消费身份（C 是唯一解析与持有者）。"""
    if plan.get('fixture_deploy') == 'candidate':
        return {'deploy': 'candidate', 'root': plan['release_root'], 'ref': plan['release_ref'],
                'version': plan['release_version'], 'meta': plan['release_meta'],
                'rebuild': False}
    return {'deploy': 'dev', 'root': plan['test_release_root'], 'ref': plan['test_release_ref'],
            'version': plan['test_release_version'], 'meta': '',
            'rebuild': not int(plan.get('no_build') or 0)}


def _release_cli_path():
    here = os.path.dirname(os.path.abspath(__file__))
    return os.environ.get('WF_TEST_RELEASE_CLI') or os.path.normpath(
        os.path.join(here, '..', '..', 'wf_test_release.py'))


def _candidate_validator_path():
    return os.environ.get('WF_CANDIDATE_VALIDATOR') or os.path.join(
        os.path.dirname(os.path.abspath(__file__)), 'prepare_candidate_repo.py')


def _candidate_facts(meta, label):
    commit = meta.get('commit')
    tree = meta.get('tree_digest')
    if not isinstance(commit, str) or not commit:
        raise EvidenceError(f'{label}: candidate validator returned no verified commit')
    if not isinstance(tree, str) or not tree:
        raise EvidenceError(f'{label}: candidate validator returned no tree digest')
    return {'commit': commit, 'tree_digest': tree,
            'meta_digest': _meta_digest(meta.get('root') or '')}


def _meta_digest(root):
    try:
        return 'sha256:' + hashlib.sha256(
            Path(root + '.meta.json').read_bytes()).hexdigest()
    except OSError:
        return None


def _prepare_release(plan, root, args, scope):
    """C 取得的唯一发行消费锁 + 一次受监督准备 + 上下文交接。"""
    import release_context
    import release_lock
    started = time.monotonic()
    identity = _release_identity(plan)
    try:
        fd = release_lock.acquire(identity['root'], exclusive=True)
    except (release_lock.Busy, release_lock.LockError) as exc:
        raise EvidenceError(f'release lock refused: {exc}') from exc
    try:
        release_lock.write_env(fd, identity['root'])
        logs = Path(root) / 'logs'
        logs.mkdir(parents=True, exist_ok=True)
        log = logs / 'release-prepare.log'
        if identity['deploy'] == 'dev':
            command = [sys.executable, _release_cli_path(),
                       '--ensure' if identity['rebuild'] else '--check', '--no-lock',
                       '--root', identity['root'], '--version', identity['version'], '--json']
            label = 'TEST-RELEASE-BUILD-FAILED' if identity['rebuild'] else 'TEST-RELEASE-STALE'
        else:
            command = [sys.executable, _candidate_validator_path(), '--check',
                       '--out', identity['root'], '--version', identity['version'], '--json']
            label = 'CANDIDATE-REPO-INVALID'
        result = run(command, log, timeout=args.timeout, scope=scope,
                     fault_identity='release:prepare')
        if result.get('status') != 'passed':
            raise EvidenceError(
                f"{label}: {result.get('reason') or 'release preparation failed'} (see {log})")
        meta = _log_json(log) or {}
        if identity['deploy'] == 'dev':
            status = meta.get('status')
            if status not in ('built', 'reused', 'checked'):
                raise EvidenceError(f'release CLI returned unknown status: {status!r}')
            release_build, candidate = status, None
        else:
            candidate = _candidate_facts(meta, 'CANDIDATE-REPO-INVALID')
            if os.path.realpath(meta.get('root') or identity['root']) != os.path.realpath(
                    identity['root']):
                raise EvidenceError('candidate validator verified another repository root')
            release_build = 'checked'
        context = release_context.build_context(
            deploy=identity['deploy'], root=identity['root'], ref=identity['ref'],
            version=identity['version'], candidate=candidate, release_build=release_build,
            plan_sha256=args.plan_sha256, plan_size=args.plan_size, results_dir=root)
        context_path = os.path.join(root, 'release-context.json')
        digest, size = release_context.write_context_atomic(context_path, context)
        os.environ['WF_BUILD_SECONDS'] = str(int(time.monotonic() - started))
        return {'fd': fd, 'identity': identity, 'context': context,
                'context_path': context_path, 'context_sha256': digest, 'context_size': size}
    except BaseException:
        release_lock.release(fd)
        raise


def _candidate_final_check(identity, prepared, args, root, scope):
    """worker 退出后、proof/摘要/终态发布之前：同一 validator 再核一次同一身份。"""
    expected = prepared['context'].get('candidate') or {}
    log = Path(root) / 'logs' / 'candidate-final.log'
    command = [sys.executable, _candidate_validator_path(), '--check',
               '--out', identity['root'], '--version', identity['version'], '--json']
    result = run(command, log, timeout=args.timeout, scope=scope,
                 fault_identity='release:final')
    if result.get('status') != 'passed':
        cancel_request = os.path.exists(os.path.join(root, 'cancel-request'))
        if cancel_request or (scope is not None and getattr(scope, 'latched', False)):
            # 已经取消（信号或已发布请求）时，终核只归因为“未完成/取消”；不冒充候选身份漂移。
            raise EvidenceError(
                'CANDIDATE-FINAL-INCOMPLETE: cancelled before final verification completed ('
                + (result.get('reason') or 'validator interrupted') + f'); see {log}')
        raise EvidenceError(
            'CANDIDATE-REPO-CHANGED: final verification failed ('
            + (result.get('reason') or 'validator returned non-zero') + f'); see {log}')
    facts = _candidate_facts(_log_json(log) or {}, 'CANDIDATE-REPO-CHANGED')
    comparable = ('commit', 'tree_digest')
    for key in comparable:
        if facts.get(key) != expected.get(key):
            raise EvidenceError(
                f'CANDIDATE-REPO-CHANGED: persistent {key} drift during the run '
                f'({facts.get(key)!r} != {expected.get(key)!r})')


def _assert_inner_program(role, command):
    """controller 只把已冻结的 plan/context frame 交给该 role 的唯一入口脚本。"""
    here = os.path.dirname(os.path.abspath(__file__))
    expected = {'full': os.path.join(here, 'run_all.sh'),
                'repro': os.path.join(here, 'repro', 'run.sh')}[role]
    if len(command) != 2 or os.path.basename(command[0]) != 'bash':
        raise EvidenceError('controller command must be `bash <entry script>`')
    if os.path.realpath(command[1]) != os.path.realpath(expected):
        raise EvidenceError(
            f'controller entry script for role {role} must be {expected}（收到 {command[1]}）')


def _scope_field(plan):
    scope = plan.get('scope_root')
    return scope or '-'


def _inner_command(role, plan, prepared, args):
    """由 C 组装唯一的消费 frame：plan/context token 与位置只在这一处交接。"""
    import runner_protocol
    here = os.path.dirname(os.path.abspath(__file__))
    explicit = os.environ.get('WF_FRAME_RESULTS_EXPLICIT') or '1'
    if explicit not in ('0', '1'):
        raise EvidenceError(f'invalid WF_FRAME_RESULTS_EXPLICIT: {explicit!r}')
    fields = {'--entry-pid': str(os.getpid()),
              '--results-root': os.path.realpath(plan['results_dir']),
              '--results-explicit': explicit,
              '--scope-root': _scope_field(plan),
              '--plan-file': os.path.realpath(args.plan_file),
              '--plan-sha256': args.plan_sha256,
              '--plan-size': str(args.plan_size),
              '--context-file': prepared['context_path'],
              '--context-sha256': prepared['context_sha256'],
              '--context-size': str(prepared['context_size'])}
    if role == 'full':
        frame = runner_protocol.encode('execute', fields, [])
        program = os.path.join(here, 'run_all.sh')
    else:
        frame = runner_protocol.encode_repro('repro-inner', fields)
        program = os.path.join(here, 'repro', 'run.sh')
    return ['bash', program, *frame]


def _proof_root(role, plan, root):
    if role == 'full':
        return Path(root) / 'repro' if plan.get('repro_enabled') else None
    return Path(root)


def _commit_repro_proof(role, plan, root, run_id):
    """C 的唯一一次 proof 提交：结束发行核验与取消观测之后、摘要发布之前。"""
    repro_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'repro')
    if repro_dir not in sys.path:
        sys.path.insert(0, repro_dir)
    import repro_select
    proof_root = _proof_root(role, plan, root)
    if proof_root is None:
        return None
    bundle = proof_root / 'inputs.json'
    if not bundle.is_file() or bundle.is_symlink():
        raise EvidenceError(f'repro bundle is missing: {bundle}')
    sha, size = _repro_bundle_fact(str(proof_root))
    import fixture_scope
    try:
        return repro_select.commit_state(
            str(proof_root), str(bundle), sha, size, run_id=run_id,
            evidence_root=str(Path(root) / 'commands'))
    except (repro_select.SelectError, fixture_scope.FixtureError) as exc:
        raise EvidenceError(f'repro proof refused: {exc}') from exc


def _cancel_report(report, decision):
    reasons = list(report.get('reasons') or [])
    reasons.append(decision.reason or 'cancelled before the success boundary')
    return dict(report, ok=False, failure_kind='cancelled', reasons=reasons[:50])


def runner_control(args):
    """外层 controller：同 C 进程核验 → 取发行锁/准备 → root started → 监督 → 聚合 → finalize → 摘要 → 终态。"""
    lifecycle, cleanup = _local_modules()
    try:
        fault = cleanup.validate_fault_selector()
        validate_execution_selector()
    except (cleanup.CleanupError, EvidenceError) as exc:
        return _controller_refuse(str(exc))
    try:
        root, plan = _verify_controller_context(args, lifecycle)
    except (EvidenceError, lifecycle.LifecycleError, OSError, ValueError,
            _path_error_class()) as exc:
        return _controller_refuse(str(exc))
    role = args.runner_role
    command = args.command[1:] if args.command[:1] == ['--'] else args.command
    try:
        _assert_inner_program(role, command)
    except EvidenceError as exc:
        return _controller_refuse(str(exc))
    try:
        import results_summary
    except ImportError as exc:
        return _controller_refuse(f'summary module unavailable: {exc}')
    result_path = Path(args.result) if args.result else Path(root) / lifecycle.CONTROL_NAME
    cancel_path = os.path.join(root, 'cancel-request')
    os.environ['WF_CANCEL_FILE'] = cancel_path
    os.environ.setdefault('WF_RUN_ID', args.run_id)
    # 默认执行不观察/不盘点历史材料：维护只由显式入口（inventory/prune/retire）发生。
    scope = CancellationScope().install()
    import release_lock
    release_fd = None
    success = False
    publish_failure = False
    final_rc = 1
    status = 'failed'
    report = None
    assessment = None
    cleanup_report = None
    control_doc = None
    gate_report = None
    payload = None
    context = None
    try:
        try:
            prepared = _prepare_release(plan, root, args, scope)
        except (EvidenceError, lifecycle.LifecycleError, OSError, ValueError,
                release_lock.LockError) as exc:
            cancelled = scope.latched
            early_status = 'cancelled' if cancelled else 'failed'
            print(f'RUNNER-RELEASE-FAILED: {exc}', file=sys.stderr)
            try:
                lifecycle.finish_run(root, args.run_id, role, 'unknown',
                                     'incomplete', reasons=[str(exc)])
            except lifecycle.LifecycleError as state_exc:
                print(f'RUNNER-STATE-FAILED: {state_exc}', file=sys.stderr)
            print('GATE-FAIL: 发行准备未完成，worker 未启动', file=sys.stderr)
            if cancelled:
                return 128 + int(scope.signum or 0) if scope.signum else 1
            return 1
        release_fd = prepared['fd']
        import release_context
        os.environ.update(release_context.release_env(prepared['context']))
        inner = _inner_command(role, plan, prepared, args)
        pass_fds = [item for item in (args.pass_fds or '').split(',') if item]
        pass_fds.append(str(release_fd))
        control_result = run(inner, args.log, timeout=args.timeout, inherit_output=True,
                             pass_fds=pass_fds,
                             scope=scope, runner_control=True, receipt_path=str(result_path),
                             env=_child_environment(fault, results_summary))
        repro_root = _proof_root(role, plan, root)
        context_path = Path(root) / lifecycle.RELEASE_CONTEXT_NAME
        gate_report = None
        evidence_error = None
        try:
            # 结束发行校验与取消状态无关：取消时只把终核归因为“未完成/取消”；
            # 候选只有可核到的身份差异才报告漂移，且终核未通过不产生整次候选通过。
            if prepared['identity']['deploy'] == 'candidate':
                _candidate_final_check(prepared['identity'], prepared, args, root, scope)
            else:
                release_lock.verify_lease(prepared['identity']['root'])
            if role == 'full':
                gate_report = _gate_report(root, plan, args.plan_file)
            else:
                gate_report = _repro_gate_report(root, plan, run_id=args.run_id,
                                                 evidence_root=str(Path(root) / 'commands'))
        except (EvidenceError, lifecycle.LifecycleError, release_lock.LockError,
                OSError, ValueError) as exc:
            evidence_error = exc
            print(f'RUNNER-EVIDENCE-FAILED: {exc}', file=sys.stderr)
        # 清理事实与证据成败分开：本代有依据就删，现场未知就保留。终核失败、取消短路
        # 或相位报告坏损都不越过这个出口。
        try:
            assessment = _assess_with_faults(root, args.run_id, plan, control_result,
                                             gate_report, fault, cleanup)
        except Exception as exc:  # 聚合器崩溃也是“证据未知”，不跳过清理
            print(f'RUNNER-ASSESS-FAILED: {exc}', file=sys.stderr)
            assessment = _unknown_assessment(gate_report, f'assessment failed: {exc}')
            evidence_error = evidence_error or exc
        cleanup_report = cleanup.finalize(root, plan, assessment)
        payload = None
        report = None
        try:
            bundle_sha, bundle_size = (_repro_bundle_fact(str(repro_root))
                                       if repro_root else (None, None))
            if role == 'full':
                metrics, input_evidence = results_summary.read_metrics(
                    Path(root) / lifecycle.METRICS_NAME, args.run_id, root, role,
                    args.plan_file, str(context_path), str(repro_root) if repro_root else None,
                    bundle_sha, bundle_size)
            else:
                metrics = None
                input_evidence = results_summary.repro_input_evidence(
                    str(repro_root), bundle_sha, bundle_size)
            context = results_summary._json_object(
                Path(context_path).read_bytes(), 'release context')
            # 结束发行校验/清理/取消都有结论后，才提交唯一一次 proof（取消或证据失败即不提交）。
            cancel_before_proof = scope.consume_cancel(cancel_path)
            if not cancel_before_proof.cancelled and evidence_error is None:
                _commit_repro_proof(role, plan, root, args.run_id)
            report = _summary_report(gate_report, assessment, cleanup_report, control_result)
            if evidence_error is not None:
                report = dict(report, ok=False,
                              reasons=(list(report.get('reasons') or [])
                                       + [f"evidence: {evidence_error}"])[:50])
            # 最终成功决策边界：材料已备好、正式发布之前固定结论。
            decision = scope.final_decision(cancel_path)
            if decision.cancelled:
                report = _cancel_report(report, decision)
                status = 'cancelled'
            else:
                status = 'ok' if report["ok"] else (
                    'cancelled' if control_result.get('status') in ('cancelled', 'timeout')
                    else 'failed')
            # 只构造，不提交：summary 的原子替换是唯一正式提交点，必须在诊断/生命周期
            # 记录都已写入之后才发生。
            payload = results_summary.build(root, report, metrics, input_evidence,
                                            plan, role, args.run_id, fault=fault,
                                            context=context, commit=False)
        except (EvidenceError, cleanup.CleanupError, results_summary.SummaryError,
                lifecycle.LifecycleError, release_lock.LockError, OSError, ValueError) as exc:
            print(f'RUNNER-FINALIZE-FAILED: {exc}', file=sys.stderr)
            success = False
            publish_failure = True
            status = ('cancelled' if control_result.get('status') in ('cancelled', 'timeout')
                      else 'failed')
            cleanup_report = cleanup_report or {
                "cleanup_state": "unknown", "removed": [], "failed": [],
                "not_attempted": [], "retained_paths": [], "reasons": [str(exc)]}
        control_doc = {
            "schema_version": 2, "run_id": args.run_id, "role": role,
            "target": {"status": control_result.get('status'), "rc": control_result.get('rc')},
            "assessment": {"cleanup_state": assessment['cleanup_state'],
                           "evidence_state": assessment['evidence_state'],
                           "reasons": assessment.get('reasons') or [],
                           "retained_paths": assessment.get('retained_paths') or []},
            "cleanup": cleanup_report,
        }
        if evidence_error is not None:
            control_doc["failure"] = str(evidence_error)
        if (cleanup_report or {}).get('cleanup_state') != 'cleaned':
            print('CLEANUP-UNKNOWN: 本次 run 的清理未确认；'
                  f'cleanup={(cleanup_report or {}).get("cleanup_state")} '
                  f'evidence={assessment["evidence_state"]} '
                  f'reasons={" ".join((cleanup_report or {}).get("reasons") or [])[:400]}',
                  file=sys.stderr)
        # 诊断与生命周期记录先写，summary 发布是最后一步；任一步失败都不产生正式通过。
        if fault == 'control-write-oserror':
            print('RUNNER-CONTROL-FAILED: injected control write failure', file=sys.stderr)
            publish_failure = True
        else:
            try:
                _finish_receipt(str(result_path), control_result.get('command_id') or '',
                                {'control': control_doc})
            except (lifecycle.LifecycleError, OSError) as exc:
                print(f'RUNNER-CONTROL-FAILED: {exc}', file=sys.stderr)
                publish_failure = True
        state_cleanup = (cleanup_report or {}).get('cleanup_state') or 'unknown'
        cancelled = status == 'cancelled' or control_result.get('status') in ('cancelled', 'timeout')
        if publish_failure and not cancelled and state_cleanup != 'failed':
            state_cleanup = 'unknown'
        final_evidence = ('incomplete' if publish_failure else assessment['evidence_state'])
        if fault == 'state-finish-oserror':
            print('RUNNER-STATE-FAILED: injected run-state finish failure', file=sys.stderr)
            publish_failure = True
        else:
            try:
                lifecycle.finish_run(root, args.run_id, role, state_cleanup,
                                     final_evidence,
                                     retained_paths=(cleanup_report or {}).get('retained_paths') or [],
                                     reasons=(report or {}).get('reasons') or [])
            except lifecycle.LifecycleError as exc:
                print(f'RUNNER-STATE-FAILED: {exc}', file=sys.stderr)
                publish_failure = True
        success = False
        if payload is not None and not publish_failure:
            try:
                results_summary.publish(root, payload, fault=fault)
                success = payload.get('status') == 'ok'
            except (results_summary.SummaryError, OSError) as exc:
                print(f'RUNNER-SUMMARY-FAILED: {exc}', file=sys.stderr)
                publish_failure = True
        if (report or {}).get('ok') and not success:
            print('CLEANUP-UNKNOWN: 本次 run 的诊断/生命周期/摘要未全部确认；'
                  f'cleanup={state_cleanup} evidence={assessment["evidence_state"]}',
                  file=sys.stderr)
        final_rc = control_result.get('rc') or 0
        if final_rc == 0 and not success:
            final_rc = 1
        counts = (report or {}).get('counts') or {}
        print(f"---- runner-control run_id={args.run_id} status={status} "
              f"cleanup={state_cleanup} evidence={assessment['evidence_state']} "
              f"counts={counts} ----")
        if not success:
            print('GATE-FAIL: 本次运行未闭合（清理/证据/摘要任一未确认）', file=sys.stderr)
        else:
            print(f'GATE-OK: run_id={args.run_id} 清理/证据/摘要一致（fail={counts.get("fail", 0)}）')
        return final_rc if 0 <= final_rc <= 255 else 1
    finally:
        scope.restore()
        if release_fd is not None:
            try:
                release_lock.release(release_fd)
            except OSError:
                pass


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--log')
    parser.add_argument('--result')
    parser.add_argument('--name', default='command')
    parser.add_argument('--kind', choices=('raw', 'suite', 'flow', 'steps', 'repro'), default='raw')
    parser.add_argument('--expected', type=int)
    parser.add_argument('--phase', choices=('green', 'red'), default=None,
                        help='repro 判定所需相位（kind=repro 时必填）')
    parser.add_argument('--isolated-user', action='store_true',
                        help='use a unique disposable test HOME per command')
    parser.add_argument('--runner-control', action='store_true',
                        help='run as the root controller (single finalize + summary publisher)')
    parser.add_argument('--runner-role', choices=('full', 'repro'), default=None)
    parser.add_argument('--results-root', default=None)
    parser.add_argument('--run-id', default=None)
    parser.add_argument('--plan-file', default=None)
    parser.add_argument('--plan-sha256', default=None)
    parser.add_argument('--plan-size', default=None)
    parser.add_argument('--timeout', type=float, default=float(os.environ.get('WF_COMMAND_TIMEOUT', 180)))
    parser.add_argument('--pass-fds', default='', help='逗号分隔的 FD 白名单（显式继承，不依赖 Popen 默认）')
    parser.add_argument('--fault-identity', default=None,
                        help='本命令的受限故障身份（unit:<name> / repro:<case>:<phase>）')
    parser.add_argument('command', nargs=argparse.REMAINDER)
    args = parser.parse_args(argv)
    if args.kind == 'repro' and args.phase is None:
        parser.error('--kind repro requires an explicit --phase green|red（不允许“任一 PASS 都算”）')
    if args.kind != 'repro' and args.phase is not None:
        parser.error('--phase is only meaningful with --kind repro')
    if not args.log:
        parser.error('--log is required for command execution')
    command = args.command[1:] if args.command[:1] == ['--'] else args.command
    if not command:
        parser.error('command is required')
    if args.runner_control:
        return runner_control(args)
    lifecycle, _cleanup = _local_modules()
    try:
        result = run(command, args.log, timeout=args.timeout,
                     inherit_output=False, pass_fds=[item for item in
                                                     (args.pass_fds or '').split(',') if item],
                     isolated_user=args.isolated_user, fault_identity=args.fault_identity)
    except (OSError, EvidenceError, lifecycle.LifecycleError,
            _path_error_class()) as exc:
        print(f'EXECUTION-FAILED: {args.name} 启动前拒绝（证据域/路径）：{exc}', file=sys.stderr)
        return 1
    supervision = result.get('supervision') or {}
    if result['status'] == 'passed' and supervision.get('cleanup_state') != 'cleaned':
        # 清理未知/失败不得以 rc=0 签成功；保留原因注入结果。
        result.update(status='failed', rc=1,
                      reason=f"cleanup state is {supervision.get('cleanup_state') or 'unknown'}")
    check = verdict(args.log, result['rc'], args.kind, args.expected, phase=args.phase)
    result.update(name=args.name, kind=args.kind, assertion_result=check,
                  isolated_user=bool(args.isolated_user))
    if not check['ok'] and result['rc'] == 0:
        result.update(rc=1, status='failed', reason=check['reason'])
    if args.result:
        write_json(args.result, result)
    sys.stdout.write(Path(args.log).read_text(encoding='utf-8', errors='replace'))
    if not check['ok']:
        print(f'EXECUTION-FAILED: {args.name} {result["reason"] or check["reason"]}; log={args.log}',
              file=sys.stderr)
    if supervision.get('cleanup_state') != 'cleaned':
        print('CLEANUP-UNKNOWN: 最后有效监督方不可用，未声称已释放锁/夹具。'
              f' guardian={supervision.get("guardian_pid")} '
              f'supervisor={supervision.get("supervisor_pid")} '
              f'target={supervision.get("target_pid")} '
              f'command={args.name} evidence={result.get("evidence_path")}',
              file=sys.stderr)
        print('恢复步骤：核对这些 PID/启动身份后手工停止本次命令，确认无存活持有者，'
              '再用 owned 清理入口回收夹具并重新运行；不要删除锁或按历史 PID 通配 kill。',
              file=sys.stderr)
    return result['rc'] if 0 <= result['rc'] <= 255 else 1


if __name__ == '__main__':
    def _fault_arg(value):
        try:
            spec = json.loads(value or '{}')
        except ValueError:
            return None
        return spec or None

    if len(sys.argv) > 1 and sys.argv[1] == '_guardian':
        parser = argparse.ArgumentParser()
        parser.add_argument('--ctrl-fd', required=True)
        parser.add_argument('--log-fd', required=True)
        parser.add_argument('--fds', default='')
        parser.add_argument('--fault', default='')
        parsed = parser.parse_args(sys.argv[2:])
        raise SystemExit(_guardian_main({'ctrl_fd': parsed.ctrl_fd, 'log_fd': parsed.log_fd,
                                         'fds': [item for item in parsed.fds.split(',') if item],
                                         'fault': _fault_arg(parsed.fault)}))
    if len(sys.argv) > 1 and sys.argv[1] == '_supervisor':
        parser = argparse.ArgumentParser()
        parser.add_argument('--ctrl-fd', required=True)
        parser.add_argument('--log-fd', required=True)
        parser.add_argument('--fds', default='')
        parser.add_argument('--fault', default='')
        parsed = parser.parse_args(sys.argv[2:])
        raise SystemExit(_supervisor_main({'ctrl_fd': parsed.ctrl_fd, 'log_fd': parsed.log_fd,
                                           'fds': [item for item in parsed.fds.split(',') if item],
                                           'fault': _fault_arg(parsed.fault)}))
    if len(sys.argv) > 1 and sys.argv[1] == '_target':
        raise SystemExit(_target_main(sys.argv[2:]))
    raise SystemExit(main())
