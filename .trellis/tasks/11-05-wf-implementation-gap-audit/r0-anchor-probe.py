#!/usr/bin/env python3
"""R0 锚点探针：在任何 agent 环境里手动跑，判断"一个执行边界 = 一个稳定锚"是否成立。

用法（在**同一个终端/同一个执行边界**里连跑两次）：
    python3 r0-anchor-probe.py

判据：
  - 同一边界内两次调用 ⇒ L1 键相同（若 L1 可用）；L2 键相同（若 L2 可用）；
  - 不同边界（另开一个终端/tmux pane）⇒ 键不同；
  - 二者皆不可用 ⇒ 该环境"无锚"，按方案应 fail loud（可用显式模式）。

输出仅用于记录，不写任何项目文件、不改任何状态。
"""
import hashlib
import json
import os
import time

SHELLS_UTILS = {
    "bash", "sh", "zsh", "dash", "fish", "env", "timeout", "xargs", "setsid", "nohup",
    "sudo", "runuser", "script", "stdbuf", "nice", "ionice", "unshare", "tmux", "screen",
}


def _stat(pid):
    try:
        raw = open(f"/proc/{pid}/stat").read()
    except OSError:
        return None
    comm = raw[raw.index("(") + 1: raw.rindex(")")]
    f = raw[raw.rindex(")") + 2:].split()
    exe = ""
    try:
        exe = os.path.basename(os.readlink(f"/proc/{pid}/exe"))
    except OSError:
        pass
    return {"pid": pid, "comm": comm, "ppid": int(f[1]), "session": int(f[3]),
            "tty_nr": int(f[4]), "start": f[19], "exe": exe or comm}


def _key(payload):
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonical.encode()).hexdigest()[:16]


def probe():
    boot = open("/proc/sys/kernel/random/boot_id").read().strip()
    me = _stat(os.getpid())
    sid = os.getsid(0)
    leader = _stat(sid)
    l1 = None
    if sid > 1 and leader is not None:
        l1 = {"boot": boot[:8], "kind": "session", "sid": sid, "sid_start": leader["start"],
              "leader": leader["exe"]}
    l2 = None
    chain = []
    pid = os.getpid()
    while pid > 1:
        info = _stat(pid)
        if info is None:
            break
        chain.append((info["exe"], info["pid"], info["start"]))
        if len(chain) > 1 and info["exe"] not in SHELLS_UTILS and not info["exe"].startswith("python"):
            if _stat(info["ppid"]) and info["ppid"] != 1:
                l2 = {"boot": boot[:8], "kind": "proc", "exe": info["exe"],
                      "pid": info["pid"], "start": info["start"]}
                break
        pid = info["ppid"]
    return {
        "l1": l1, "l2": l2,
        "l1_key": _key(l1) if l1 else None,
        "l2_key": _key(l2) if l2 else None,
        "tty_nr": me["tty_nr"],
        "chain": chain[:6],
        "sid_alive": leader is not None,
    }


if __name__ == "__main__":
    first = probe()
    time.sleep(0.2)
    second = probe()
    print(json.dumps({"first": first, "second": second,
                      "l1_stable": first["l1_key"] == second["l1_key"],
                      "l2_stable": first["l2_key"] == second["l2_key"]},
                     ensure_ascii=False, indent=2))
