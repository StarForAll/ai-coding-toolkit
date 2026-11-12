"""session.py — 会话身份、SessionKey 与持久绑定（机制稿 §1.4）。

身份只来自请求信封，不读环境变量或命令行。
"""

from __future__ import annotations

import os
import re
import sys
import uuid

from . import records
from .paths import join

HOST_ID_RE = re.compile(r"^[a-z][a-z0-9-]{0,63}$")
UUID4_HEX_RE = re.compile(r"^[0-9a-f]{32}$")

PROVIDERS = ("host", "wf")


class IdentityError(Exception):
    """身份字段缺失/非法（对应 WF_IDENTITY_UNRESOLVED 的事实面）。"""


def _identity_value(session: dict) -> dict:
    provider = session.get("provider")
    identity = session.get("identity")
    if provider not in PROVIDERS:
        raise IdentityError(f"unknown provider: {provider!r}")
    if not isinstance(identity, dict):
        raise IdentityError("identity missing")
    if provider == "host":
        host_id = identity.get("host_id")
        session_id = identity.get("session_id")
        if not isinstance(host_id, str) or not HOST_ID_RE.match(host_id):
            raise IdentityError("host_id missing or invalid")
        if not isinstance(session_id, str) or not session_id.strip():
            raise IdentityError("session_id missing")
        return {"host_id": host_id, "session_id": session_id}
    issued_id = identity.get("issued_id")
    if not isinstance(issued_id, str) or not UUID4_HEX_RE.match(issued_id):
        raise IdentityError("issued_id missing or not a UUID4 hex")
    return {"issued_id": issued_id}


def validate_session(session) -> dict:
    if not isinstance(session, dict):
        raise IdentityError("session object missing")
    value = _identity_value(session)
    instance_id = session.get("instance_id")
    if instance_id is not None and not isinstance(instance_id, str):
        raise IdentityError("instance_id must be a string or null")
    activation = session.get("activation")
    if activation is not None:
        if not isinstance(activation, dict) or activation.get("enabled") is not True:
            raise IdentityError("activation invalid")
    return {
        "provider": session["provider"],
        "identity": value,
        "instance_id": instance_id,
        "activation": activation,
    }


def session_key(session: dict) -> str:
    value = _identity_value(session)
    return records.sha256_hex(records.canonical_bytes({"provider": session["provider"], "identity": value}))


def binding_path(root, key: str):
    return join(root, f".wf/session-bindings/{key}.json")


def load_binding(root, key: str, default=None):
    return records.load_json(binding_path(root, key), default)


def save_binding(root, key: str, payload: dict):
    records.write_json(binding_path(root, key), payload)
    return payload


def runtime_path(root, key: str):
    return join(root, f".wf/.runtime/sessions/{key}.json")


def write_runtime(root, key: str, payload: dict):
    """可丢弃定位缓存；写失败只降级可见。"""
    try:
        records.write_json(runtime_path(root, key), payload)
        return True
    except OSError:
        return False


def load_runtime(root, key: str):
    """读本会话侧车（可丢弃定位缓存）；缺失或不可解析返回 None，不阻断读取。"""
    try:
        return records.load_json(runtime_path(root, key))
    except OSError:
        return None


def new_instance_id() -> str:
    return uuid.uuid4().hex


def check_platforms(platforms, session: dict):
    """运行期身份判定：只看**宿主是否在本项目已安装的平台里**。

    机制稿 §1.4 修订后：能力由平台表静态声明，不再要求人现场提供证据，也不要求
    "与安装时那一个宿主逐字相等"——项目不属于任何单个 agent。
    真实异常（实例丢失、绑定不符、代次过期、检查锚点失效）由各自路径即时报错，fail-closed。
    """
    provider = session.get("provider")
    host = (session.get("identity") or {}).get("host_id")
    installed = [item for item in (platforms or []) if isinstance(item, str)]
    facts = {"host_id": host, "provider": provider, "installed_platforms": installed}
    if provider == "wf":
        # 自动身份模式（R3）：身份由锚点派生、`issued_id` 落附件，本地已自校验；
        # 显式传 wf 信封（无 source=auto 标记）仍按原语义拒绝——那条路没有本地证据。
        if session.get("source") == "auto":
            return None, {**facts, "identity_source": "auto"}
        facts["reason"] = "显式 wf 信封未被本地证据支持；自动模式请留空信封由锚点派生"
        return "WF_IDENTITY_UNRESOLVED", facts
    if not installed:
        facts["reason"] = "installation declares no platforms"
        facts["next"] = "install --platform <agent>"
        return "WF_IDENTITY_UNRESOLVED", facts
    if host not in installed:
        facts["reason"] = "host not installed for this project"
        facts["next"] = f"install --platform {host}"
        return "WF_IDENTITY_UNRESOLVED", facts
    return None, facts


# --------------------------------------------------------------------------
# 锚点与唯一裁决（R1，见 identity-redesign.md v3.31 §2.2/§2.2a/§2.2b/§2.3d）
#
# 支持范围以 R0 结论为准（r0-results.md §九）：Linux；P1 覆盖终端/单聊天与
# 多聊天宿主（须为每聊天派生独立 shell/pty），tmux 仅 L1（P3），
# 容器逐命令与 leader 先死无锚（fail loud）。
# --------------------------------------------------------------------------

BOOT_ID_PATH = "/proc/sys/kernel/random/boot_id"

# 通用工具分类：不是 agent 名单。口径见 §2.2c——basename(readlink(exe)) 全等匹配。
SHELLS_OR_UTILS = frozenset({
    "bash", "sh", "zsh", "dash", "fish", "env", "timeout", "xargs", "setsid",
    "nohup", "sudo", "runuser", "script", "stdbuf", "nice", "ionice", "unshare",
    "tmux", "screen",
})

PATHS = ("P1", "P2", "P3")

# 三值证据
MATCH, GONE, UNVERIFIED = "match", "gone", "unverified"
ALIVE, DEAD = "alive", "dead"

# 裁决结果
USE, NEW = "USE", "NEW"
BLOCK_EVIDENCE = "evidence_unknown"
BLOCK_AMBIGUOUS = "ambiguous_shared_root"
BLOCK_OTHER_BOUNDARY = "other_boundary_alive"
BLOCK_OTHER_ROOT = "other_root_alive"


def boot_id() -> str:
    try:
        with open(BOOT_ID_PATH, "r", encoding="utf-8") as handle:
            return handle.read().strip()
    except OSError:
        return ""


class Probe:
    """读取进程事实的唯一入口；测试可替换 ``stat_of``/``exe_of``/``boot``。"""

    def __init__(self, boot: str | None = None):
        self.boot = boot if boot is not None else boot_id()

    def stat_of(self, pid: int):
        """返回 None（**确认不存在**）或 dict；读不到时抛 OSError（unverified）。

        `ENOENT`/`ProcessLookupError` 必须映射成 None（= dead/gone），不能与 `EACCES`
        等读取失败混为一谈——否则"进程已死"会被当成"证据未知"，续接路径被永久阻断
        （identity-redesign §2.3d 的三值要求）。
        """
        try:
            with open(f"/proc/{int(pid)}/stat", "r", encoding="utf-8", errors="replace") as handle:
                raw = handle.read()
        except (FileNotFoundError, ProcessLookupError):
            return None
        comm = raw[raw.index("(") + 1: raw.rindex(")")]
        fields = raw[raw.rindex(")") + 2:].split()
        return {
            "pid": int(pid),
            "comm": comm,
            "state": fields[0],
            "ppid": int(fields[1]),
            "session": int(fields[3]),
            "tty_nr": int(fields[4]),
            "start": fields[19],
        }

    def exe_of(self, pid: int):
        try:
            return os.path.basename(os.readlink(f"/proc/{int(pid)}/exe"))
        except OSError:
            return None

    def name_of(self, pid: int):
        """basename(readlink(exe))；readlink 失败时退化为 comm（仍不参与"是否 agent"的推断）。"""
        return self.exe_of(pid) or (self.stat_of(pid) or {}).get("comm")


def _anchor_key(payload: dict) -> str:
    return records.sha256_hex(records.canonical_bytes(payload))


def l1_anchor(probe: Probe | None = None):
    """会话锚：getsid(0) 指向的会话 leader（§2.2）。

    不再用 tty（R0 实测 pty 编号与 inode 都会复用），tty 仅作审计。
    """
    probe = probe or Probe()
    sid = os.getsid(0)
    if sid <= 1:
        return None
    try:
        leader = probe.stat_of(sid)
    except OSError:
        return None
    if leader is None:
        return None
    if leader["state"] == "Z":
        return None
    return {
        "kind": "sid",
        "boot": probe.boot,
        "sid": sid,
        "sid_start": leader["start"],
        "leader": probe.name_of(sid) or leader["comm"],
    }


def _is_kernel_thread(probe: Probe, pid: int) -> bool:
    try:
        info = probe.stat_of(pid)
    except OSError:
        return False
    return bool(info) and info["ppid"] == 2


def l2_anchor(probe: Probe | None = None):
    """进程锚：最近的长命非工具祖先（§2.2）。

    规则（逐条对应文档）：
    - 跳过自身与**同一解释器可执行文件**的祖先（不按名字前缀跳过，避免跳过 python 系 agent）；
    - 跳过 SHELLS_OR_UTILS；
    - 排除 pid 1 / 内核线程 / **init 的直接子进程**（服务进程）；
    - start 必须早于调用者。
    """
    probe = probe or Probe()
    try:
        me = probe.stat_of(os.getpid())
    except OSError:
        return None
    if me is None:
        return None
    interpreters = set()
    try:
        interpreters.add(os.path.realpath(sys.executable))
    except OSError:
        pass
    pid = me["ppid"]
    seen = 0
    while pid > 1 and seen < 32:
        seen += 1
        try:
            info = probe.stat_of(pid)
        except OSError:
            return None
        if info is None:
            return None
        if _is_kernel_thread(probe, pid):
            return None
        if info["ppid"] == 1:
            return None
        try:
            real = os.path.realpath(f"/proc/{pid}/exe")
        except OSError:
            real = ""
        if real and real in interpreters:
            pid = info["ppid"]
            continue
        name = probe.name_of(pid) or info["comm"]
        if name in SHELLS_OR_UTILS:
            pid = info["ppid"]
            continue
        if int(info["start"]) >= int(me["start"]):
            pid = info["ppid"]
            continue
        return {
            "kind": "pid",
            "boot": probe.boot,
            "exe": name,
            "pid": pid,
            "start": info["start"],
        }
    return None


def candidates(probe: Probe | None = None):
    """返回 [L1?, L2?]（不判定命中，见 §2.2b）。"""
    probe = probe or Probe()
    found = []
    for anchor in (l1_anchor(probe), l2_anchor(probe)):
        if anchor:
            found.append(anchor)
    return found


def anchor_key(anchor: dict):
    if not anchor:
        return None
    if anchor["kind"] == "sid":
        payload = {"boot": anchor["boot"], "kind": "sid", "sid": anchor["sid"],
                   "sid_start": anchor["sid_start"]}
    else:
        payload = {"boot": anchor["boot"], "kind": "pid", "exe": anchor["exe"],
                   "pid": anchor["pid"], "start": anchor["start"]}
    return _anchor_key(payload)


def state_of_l1(recorded, current_boot: str, probe: Probe | None = None) -> str:
    """attached_l1 的三值：null=gone、boot 不同=gone、ENOENT=gone、start 不符=gone、读不到=unverified。"""
    if recorded is None:
        return GONE
    if not isinstance(recorded, dict):
        return UNVERIFIED
    if recorded.get("boot") and recorded.get("boot") != current_boot:
        return GONE
    sid = recorded.get("sid")
    sid_start = recorded.get("sid_start")
    if not isinstance(sid, int) or sid_start is None:
        return UNVERIFIED
    probe = probe or Probe(current_boot)
    try:
        leader = probe.stat_of(sid)
    except OSError:
        return UNVERIFIED
    if leader is None:
        return GONE
    if leader["state"] == "Z":
        return GONE
    return MATCH if leader["start"] == str(sid_start) else GONE


def state_of_root(root, current_boot: str, probe: Probe | None = None) -> str:
    """根的三值：pid 型 alive/dead/unverified；sid 型按 (boot,sid,sid_start) 全等。"""
    if not isinstance(root, dict):
        return UNVERIFIED
    kind = root.get("kind")
    if root.get("boot") and root.get("boot") != current_boot:
        return DEAD
    if kind == "sid":
        return ALIVE if root.get("sid_start") is not None else UNVERIFIED
    pid = root.get("pid")
    if not isinstance(pid, int):
        return UNVERIFIED
    probe = probe or Probe(current_boot)
    try:
        info = probe.stat_of(pid)
    except OSError:
        return UNVERIFIED
    if info is None:
        return DEAD
    if info["state"] == "Z":
        return DEAD
    return ALIVE if info["start"] == str(root.get("start")) else DEAD


def _same_root(left, right) -> bool:
    if not isinstance(left, dict) or not isinstance(right, dict):
        return False
    if left.get("kind") != right.get("kind"):
        return False
    if left.get("boot") != right.get("boot"):
        return False
    if left["kind"] == "sid":
        return left.get("sid") == right.get("sid") and \
            str(left.get("sid_start")) == str(right.get("sid_start"))
    return left.get("pid") == right.get("pid") and \
        str(left.get("start")) == str(right.get("start"))


def other_roots(session_state: dict, current_root) -> list:
    """other_roots(S) = S.roots − {current_root}（§2.3d 的唯一定义）。"""
    roots = (session_state or {}).get("roots") or []
    return [root for root in roots if not _same_root(root, current_root)]


def adjudicate(candidates_state, current_root, path: str = "P1", probe: Probe | None = None) -> dict:
    """唯一裁决函数（§2.3d）。

    candidates_state：[{session_key, attached_l1, roots}]；命中分支传 owners，
    miss 分支传"有效会话 ∩ roots 含当前 root"。
    """
    if path not in PATHS:
        raise ValueError(f"unknown identity path: {path!r}")
    probe = probe or Probe()
    boot = probe.boot
    cands = [item for item in (candidates_state or []) if isinstance(item, dict)]

    if not cands:
        return {"verdict": NEW, "reason": None, "session_key": None, "facts": {}}

    l1_states = {id(item): state_of_l1(item.get("attached_l1"), boot, probe) for item in cands}
    other_state = {}
    alive_any = False
    unknown_any = False
    for item in cands:
        states = []
        for root in other_roots(item, current_root):
            state = state_of_root(root, boot, probe)
            states.append(state)
            if state == ALIVE:
                alive_any = True
            elif state == UNVERIFIED:
                unknown_any = True
        other_state[id(item)] = states

    l1_unknown_any = (path != "P2") and any(s == UNVERIFIED for s in l1_states.values())
    evidence_unknown = l1_unknown_any or unknown_any

    if path == "P2":
        gone = list(cands)
    else:
        gone = [item for item in cands if l1_states[id(item)] == GONE]

    single_gone = len(cands) == 1 and len(gone) == 1

    if single_gone and not alive_any and not evidence_unknown:
        return {"verdict": USE, "reason": None, "session_key": cands[0].get("session_key"),
                "facts": {"anchor_degraded": "l2-only" if path != "P2" else "l1-drift"}}

    if single_gone and not alive_any and evidence_unknown:
        return {"verdict": BLOCK_EVIDENCE, "reason": BLOCK_EVIDENCE,
                "session_key": None, "facts": {"l1_unknown": l1_unknown_any, "roots_unknown": unknown_any}}

    if len(gone) > 1:
        return {"verdict": BLOCK_AMBIGUOUS, "reason": BLOCK_AMBIGUOUS, "session_key": None,
                "facts": {"candidates": len(cands), "gone": len(gone)}}

    if not gone and l1_unknown_any:
        return {"verdict": BLOCK_EVIDENCE, "reason": BLOCK_EVIDENCE, "session_key": None,
                "facts": {"l1_unknown": True}}

    if not gone:
        return {"verdict": BLOCK_OTHER_BOUNDARY, "reason": BLOCK_OTHER_BOUNDARY,
                "session_key": None, "facts": {"candidates": len(cands)}}

    if len(cands) > len(gone):
        return {"verdict": BLOCK_OTHER_BOUNDARY, "reason": BLOCK_OTHER_BOUNDARY,
                "session_key": None, "facts": {"candidates": len(cands), "gone": len(gone)}}

    if alive_any:
        return {"verdict": BLOCK_OTHER_ROOT, "reason": BLOCK_OTHER_ROOT,
                "session_key": None, "facts": {}}

    return {"verdict": BLOCK_AMBIGUOUS, "reason": BLOCK_AMBIGUOUS, "session_key": None, "facts": {}}
