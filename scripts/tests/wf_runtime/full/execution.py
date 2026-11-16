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
    try:
        target = subprocess.Popen([sys.executable, os.path.abspath(__file__), "_target",
                                   json.dumps(policy), "--", *argv],
                                  stdout=stdout, stderr=subprocess.STDOUT if stdout is not None else None,
                                  stdin=None, restore_signals=False,
                                  pass_fds=tuple([log_fd] + extra_fds) if log_fd >= 0 else tuple(extra_fds))
    except OSError as exc:
        _send(ctrl, {"v": PROTOCOL_VERSION, "type": "DONE", "target_rc": None,
                     "infrastructure_error": True, "cleanup_state": "cleaned",
                     "reason": f"cannot launch target: {exc}"})
        return 1
    _send(ctrl, {"v": PROTOCOL_VERSION, "type": "STARTED", "id": start.get("id", 0),
                 "pid": os.getpid(), "target_pid": target.pid})
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
                                       "--fds", ",".join(str(fd) for fd in extra_fds)],
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


def run(argv, log_path, *, timeout, cwd=None, env=None, inherit_output=False, pass_fds=()):
    """Run one command under the C→G→S→W supervision described in the module docstring."""
    if not math.isfinite(timeout) or timeout <= 0:
        raise ValueError('command timeout must be positive and finite')
    log_path = Path(log_path).absolute()
    log_path.parent.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    deadline = started + timeout
    result = {'schema_version': 2, 'argv': list(map(str, argv)),
              'cwd': str(Path(cwd or Path.cwd()).absolute()), 'log_path': str(log_path),
              'rc': 1, 'status': 'failed', 'reason': '', 'protocol_version': PROTOCOL_VERSION,
              'supervision': {'cleanup_state': 'unknown', 'infrastructure_error': True}}
    policy = _capture_target_policy()
    cancel = {'latched': False, 'signum': None, 'reason': None}
    cancel_file = os.environ.get('WF_CANCEL_FILE')
    command_id = 1
    log_fd = os.open(log_path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC | os.O_NOFOLLOW, 0o600)
    # inherit_output：目标直接继承调用方控制台；日志只保留失败原因（与旧行为一致）。
    guardian_log_fd = log_fd if not inherit_output else -1
    extra_fds = [int(fd) for fd in pass_fds]
    saved_handlers = {}
    saved_mask = None
    guardian = None
    channel = None
    try:
        saved_mask = signal.pthread_sigmask(
            signal.SIG_BLOCK, {signal.SIGINT, signal.SIGTERM, signal.SIGHUP})

        def on_signal(signum, _frame):
            if not cancel['latched']:
                cancel.update(latched=True, signum=signum,
                              reason=f'cancelled by signal {signum}')

        for signum in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP):
            saved_handlers[signum] = signal.signal(signum, on_signal)
        parent, child = socket.socketpair()
        try:
            guardian = subprocess.Popen(
                [sys.executable, os.path.abspath(__file__), '_guardian',
                 '--ctrl-fd', str(child.fileno()), '--log-fd', str(guardian_log_fd),
                 '--fds', ','.join(str(fd) for fd in extra_fds)],
                pass_fds=tuple([child.fileno()] + ([log_fd] if guardian_log_fd >= 0 else [])
                               + extra_fds),
                start_new_session=True, cwd=cwd, env=env)
        finally:
            child.close()
        channel = parent
        os.close(log_fd)
        log_fd = -1
        signal.pthread_sigmask(signal.SIG_SETMASK, saved_mask)
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
            if cancel['latched'] is False and _read_cancel_file(cancel_file):
                cancel.update(latched=True, signum=signal.SIGTERM,
                              reason='cancelled by cancel file')
            if cancel['latched'] and start_sent and not cancel_sent and channel is not None:
                # 已发 START：立即经同一通道取消（READY 之前的取消由 READY 分支发送）。
                cancel_sent = True
                cleanup_deadline = now + _supervision_grace()
                try:
                    _send(channel, {'v': PROTOCOL_VERSION, 'type': 'CANCEL', 'id': command_id,
                                    'signum': cancel['signum'], 'reason': cancel['reason']})
                except (OSError, ProtocolError):
                    channel = None
            if now >= deadline and not cancel['latched']:
                cancel.update(latched=True, signum=0, reason=f'TIMEOUT after {timeout:g}s')
                cleanup_deadline = now + _supervision_grace()
                if start_sent and not cancel_sent and channel is not None:
                    cancel_sent = True
                    try:
                        _send(channel, {'v': PROTOCOL_VERSION, 'type': 'CANCEL', 'id': command_id,
                                        'signum': 0, 'reason': cancel['reason']})
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
                        if not cancel['latched']:
                            start_sent = True
                            try:
                                _send(channel, {'v': PROTOCOL_VERSION, 'type': 'START', 'id': command_id,
                                                'policy': policy, 'argv': result['argv'],
                                                'deadline': deadline})
                            except (OSError, ProtocolError):
                                channel = None
                        else:
                            # 取消先于 START：协议保证不会启动 W，但仍须经同一通道收口。
                            cancel_sent = True
                            cleanup_deadline = time.monotonic() + _supervision_grace()
                            try:
                                _send(channel, {'v': PROTOCOL_VERSION, 'type': 'CANCEL', 'id': command_id,
                                                'signum': cancel['signum'],
                                                'reason': cancel['reason']})
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
                          rc=124 if (cancel['reason'] or '').startswith('TIMEOUT') else 1,
                          reason=result['reason'] or (cancel['reason']
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
                timed_out = (cancel['reason'] or '').startswith('TIMEOUT') or \
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
        if cancel['latched'] and result['status'] == 'passed':
            # 取消或设施故障先于最终确认时，目标 rc=0 也不得取绿。
            signum = cancel['signum'] or 0
            result.update(status='cancelled',
                          rc=(128 + int(signum)) if signum else 1,
                          reason=cancel['reason'] or 'cancelled')
        if result['reason']:
            try:
                with open(log_path, 'ab') as stream:
                    stream.write(('\n' + result['reason'] + '\n').encode())
            except OSError:
                pass
    finally:
        for signum, handler in saved_handlers.items():
            signal.signal(signum, handler)
        if saved_mask is not None:
            signal.pthread_sigmask(signal.SIG_SETMASK, saved_mask)
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
        try:
            parent.close()
        except (OSError, UnboundLocalError):
            pass
        result['seconds'] = round(time.monotonic() - started, 6)
    return result


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


def isolated_user(log_path):
    """Test-only user state: real bootstrap validation, synthetic fixture consent."""
    import fixture_scope
    root = fixture_scope.reset(str(log_path) + '.home')
    spec = importlib.util.spec_from_file_location('wf_test_bootstrap',
            Path(__file__).resolve().parents[4] / 'docs/workflows/wf/payload/bin/wf.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    # These are fixture records, never copies of the real user's confirmation set.
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


def cleanup_cancelled_run(results):
    import fixture_scope
    root = Path(results)
    plan_path = root / 'plan.json'
    if plan_path.is_file():
        plan = json.loads(plan_path.read_text())
        if plan.get('fix'):
            fixture_scope.remove(plan['fix'])
            fixture_scope.remove(plan['fix'] + '.legacy')
    for path in root.iterdir():
        if path.is_dir() and fixture_scope.marker(path).is_file():
            fixture_scope.remove(path)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--log')
    parser.add_argument('--result')
    parser.add_argument('--name', default='command')
    parser.add_argument('--kind', choices=('raw', 'suite', 'flow', 'steps', 'repro'), default='raw')
    parser.add_argument('--expected', type=int)
    parser.add_argument('--phase', choices=('green', 'red'), default=None,
                        help='repro 判定所需相位（kind=repro 时必填）')
    parser.add_argument('--isolated-user', action='store_true', help='use disposable test user configuration')
    parser.add_argument('--runner-control', action='store_true',
                        help='inherit console output and clean runner fixtures on cancellation')
    parser.add_argument('--timeout', type=float, default=float(os.environ.get('WF_COMMAND_TIMEOUT', 180)))
    parser.add_argument('--pass-fds', default='', help='逗号分隔的 FD 白名单（显式继承，不依赖 Popen 默认）')
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
    user_root = isolated_user(args.log) if args.isolated_user else None
    try:
        env = {**os.environ, 'HOME': str(user_root)} if user_root else None
        pass_fds = [item for item in (args.pass_fds or '').split(',') if item]
        result = run(command, args.log, timeout=args.timeout, env=env,
                     inherit_output=args.runner_control, pass_fds=pass_fds)
    finally:
        if user_root:
            import fixture_scope
            fixture_scope.remove(user_root)
    supervision = result.get('supervision') or {}
    if result['status'] == 'passed' and supervision.get('cleanup_state') != 'cleaned':
        # 清理未知/失败不得以 rc=0 签成功；保留原因注入结果。
        result.update(status='failed', rc=1,
                      reason=f"cleanup state is {supervision.get('cleanup_state') or 'unknown'}")
    check = verdict(args.log, result['rc'], args.kind, args.expected, phase=args.phase)
    result.update(name=args.name, kind=args.kind, assertion_result=check,
                  isolated_user=bool(user_root))
    if not check['ok'] and result['rc'] == 0:
        result.update(rc=1, status='failed', reason=check['reason'])
    if args.result:
        write_json(args.result, result)
    if args.runner_control and result['status'] in ('cancelled', 'timeout'):
        try:
            cleanup_cancelled_run(Path(args.log).parent)
        except (OSError, ValueError) as exc:
            print(f'RUNNER-CLEANUP-FAILED: {exc}', file=sys.stderr)
    sys.stdout.write(Path(args.log).read_text(encoding='utf-8', errors='replace'))
    if not check['ok']:
        print(f'EXECUTION-FAILED: {args.name} {result["reason"] or check["reason"]}; log={args.log}',
              file=sys.stderr)
    supervision = result.get('supervision') or {}
    if supervision.get('cleanup_state') != 'cleaned':
        print('CLEANUP-UNKNOWN: 最后有效监督方不可用，未声称已释放锁/夹具。'
              f' guardian={supervision.get("guardian_pid")} '
              f'supervisor={supervision.get("supervisor_pid")} '
              f'target={supervision.get("target_pid")} '
              f'command={args.name} results={Path(args.log).parent}',
              file=sys.stderr)
        print('恢复步骤：核对这些 PID/启动身份后手工停止本次命令，确认无存活持有者，'
              '再用 owned 清理入口回收夹具并重新运行；不要删除锁或按历史 PID 通配 kill。',
              file=sys.stderr)
    return result['rc'] if 0 <= result['rc'] <= 255 else 1


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == '_guardian':
        parser = argparse.ArgumentParser()
        parser.add_argument('--ctrl-fd', required=True)
        parser.add_argument('--log-fd', required=True)
        parser.add_argument('--fds', default='')
        parsed = parser.parse_args(sys.argv[2:])
        raise SystemExit(_guardian_main({'ctrl_fd': parsed.ctrl_fd, 'log_fd': parsed.log_fd,
                                         'fds': [item for item in parsed.fds.split(',') if item]}))
    if len(sys.argv) > 1 and sys.argv[1] == '_supervisor':
        parser = argparse.ArgumentParser()
        parser.add_argument('--ctrl-fd', required=True)
        parser.add_argument('--log-fd', required=True)
        parser.add_argument('--fds', default='')
        parsed = parser.parse_args(sys.argv[2:])
        raise SystemExit(_supervisor_main({'ctrl_fd': parsed.ctrl_fd, 'log_fd': parsed.log_fd,
                                           'fds': [item for item in parsed.fds.split(',') if item]}))
    if len(sys.argv) > 1 and sys.argv[1] == '_target':
        raise SystemExit(_target_main(sys.argv[2:]))
    raise SystemExit(main())
