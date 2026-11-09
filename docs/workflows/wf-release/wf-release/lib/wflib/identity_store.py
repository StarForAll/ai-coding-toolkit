"""identity_store.py — 执行会话的路由与会话状态（R2，identity-redesign.md §2.2a/§3.3/§3.4/§3.5）。

设计要点（缺一不可）：

1. **路由与状态分离**：`anchors.json` 只存 `key → owners[]`；会话状态（`roots`、
   `activation`、`activation_stale`、`instance_expected`、`declared_implementation_cli`）
   只有一份，存在 `attachments/<session_key>.json`。
2. **L1 单主 / L2 多主**：L1 键登记时若已有别的 owner ⇒ 记录损坏；L2 键**追加**，不覆盖。
3. **roots 维护顺序不可换**：`snapshot → 判定 → 维护`，且
   - `unverified` 且判定需要旧根证据 ⇒ 立即返回，**不 upsert**；
   - `!known ∧ 有存活兄弟根` ⇒ **C2 阻断**，**不 upsert**；
   - 旧根全部确认 dead ⇒ 置 `activation_stale`，然后 upsert。
4. **轮换 = 组更新**：`replace_owner(old, new)` 遍历**所有**路由条目，只替换该 owner。

本模块只做记录层；CLI 接线在 R3。
"""

from __future__ import annotations

import os

from . import records
from . import session as session_mod
from .paths import join

ROUTES_REL = ".wf/.runtime/anchors.json"
ATTACHMENTS_REL = ".wf/.runtime/attachments"
CLAIMS_REL = ".wf/.runtime/review-claims"

# C2 分级的阻断原因
CONCURRENT_CALLER = "concurrent_unregistered_caller"
EVIDENCE_UNKNOWN = "evidence_unknown"

# 会话租约状态（K2 的投影，不落盘）
LIVE, SUPERSEDED, GONE, UNKNOWN = "live", "superseded", "gone", "unknown"
LEASE_STATES = (LIVE, SUPERSEDED, GONE, UNKNOWN)


class StoreError(Exception):
    """记录层不变量被破坏（对应 WF_HISTORY_UNRESOLVED 的事实面）。"""

    def __init__(self, reason: str, facts: dict | None = None):
        super().__init__(reason)
        self.reason = reason
        self.facts = facts or {}


# --------------------------------------------------------------------------
# 路由
# --------------------------------------------------------------------------

def routes_path(root):
    return join(root, ROUTES_REL)


def load_routes(root) -> dict:
    data = records.load_json(routes_path(root), None)
    if data is None:
        return {}
    if not isinstance(data, dict):
        raise StoreError("routes record is not an object")
    cleaned = {}
    for key, entry in data.items():
        if not isinstance(entry, dict):
            raise StoreError("route entry is not an object", {"key": key})
        owners = entry.get("owners")
        if not isinstance(owners, list) or not owners:
            raise StoreError("route entry has no owners", {"key": key})
        cleaned[key] = {
            "owners": [owner for owner in owners if isinstance(owner, str)],
            "attached_at": entry.get("attached_at"),
            "via": entry.get("via"),
            "boot": entry.get("boot"),
        }
    return cleaned


def save_routes(root, routes: dict):
    records.write_json(routes_path(root), routes)
    return routes


def owners_of(routes: dict, key):
    entry = (routes or {}).get(key)
    return list(entry.get("owners") or []) if isinstance(entry, dict) else []


def register(routes: dict, key: str, session_key: str, via: str, boot: str, at: str):
    """登记一个路由键。

    L1（via="session"）**单主**：已有其它 owner ⇒ 记录损坏；
    L2（via="proc"）**多主**：追加（去重），不覆盖。
    """
    entry = routes.get(key)
    if entry is None:
        routes[key] = {"owners": [session_key], "attached_at": at, "via": via, "boot": boot}
        return routes
    owners = list(entry.get("owners") or [])
    if via == "session":
        others = [owner for owner in owners if owner != session_key]
        if others:
            raise StoreError("L1 key already owned by another session",
                             {"key": key, "owners": owners, "session_key": session_key})
        entry["owners"] = [session_key]
        entry["via"] = via
        entry["attached_at"] = at
        entry["boot"] = boot
        return routes
    if session_key not in owners:
        owners.append(session_key)
    entry["owners"] = owners
    entry["via"] = via
    entry["attached_at"] = at
    entry["boot"] = boot
    return routes


def replace_owner(routes: dict, old: str, new: str):
    """轮换：把所有条目里的 old 换成 new，**保留其它 owner**（§3.3）。"""
    for entry in (routes or {}).values():
        owners = list(entry.get("owners") or [])
        if old not in owners:
            continue
        replaced = [new if owner == old else owner for owner in owners]
        # 去重并保序
        seen, ordered = set(), []
        for owner in replaced:
            if owner not in seen:
                seen.add(owner)
                ordered.append(owner)
        entry["owners"] = ordered
    return routes


def routes_of_session(routes: dict, session_key: str) -> list:
    return [key for key, entry in (routes or {}).items()
            if session_key in (entry.get("owners") or [])]


def sessions_of_root(routes: dict, attachment_loader) -> list:
    """路由里出现过的全部会话（去重保序）。"""
    seen, ordered = set(), []
    for entry in (routes or {}).values():
        for owner in entry.get("owners") or []:
            if owner not in seen:
                seen.add(owner)
                ordered.append(owner)
    return ordered


# --------------------------------------------------------------------------
# 会话状态（附件）
# --------------------------------------------------------------------------

def attachments_dir(root):
    return join(root, ATTACHMENTS_REL)


def attachment_path(root, session_key: str):
    return os.path.join(attachments_dir(root), f"{session_key}.json")


def load_attachment(root, session_key: str):
    data = records.load_json(attachment_path(root, session_key), None)
    return data if isinstance(data, dict) else None


def save_attachment(root, session_key: str, payload: dict):
    records.write_json(attachment_path(root, session_key), payload)
    return payload


def new_attachment(identity_value: dict, provider: str, session_key: str, current_root,
                   activation: dict, at: str) -> dict:
    """建立/轮换时的附件构造（身份原文与 `session_key` 同存，可自校验）。"""
    return {
        "schema_version": 1,
        "provider": provider,
        "identity": identity_value,
        "session_key": session_key,
        "instance_expected": None,
        "activation": activation,
        "activation_stale": False,
        "attached_l1": None,
        "attached_root": current_root,
        "roots": [current_root],
        "declared_implementation_cli": None,
        "session_created_at": at,
        "rotation_id": None,
        "superseded_by": None,
    }


def sync_attachment_instance(root, session_key: str, instance_id):
    """§3.6：把（首次）绑定的 `instance_id` 写回附件；已有的不同值保留不覆盖。

    返回更新后的附件（没有附件则 None）。显式模式没有附件 ⇒ 直接 None。
    """
    attachment = load_attachment(root, session_key)
    if not isinstance(attachment, dict):
        return None
    current = attachment.get("instance_expected")
    if current in (None, "", instance_id):
        attachment["instance_expected"] = instance_id
        save_attachment(root, session_key, attachment)
    return attachment


def verify_attachment_identity(attachment: dict) -> bool:
    """`SHA256(C({provider, identity})) == session_key`（不变量 I5）。"""
    if not isinstance(attachment, dict):
        return False
    provider = attachment.get("provider")
    identity_value = attachment.get("identity")
    key = attachment.get("session_key")
    if provider not in session_mod.PROVIDERS or not isinstance(identity_value, dict) or not key:
        return False
    computed = records.sha256_hex(
        records.canonical_bytes({"provider": provider, "identity": identity_value}))
    return computed == key


# --------------------------------------------------------------------------
# roots 维护（§3.4）
# --------------------------------------------------------------------------

def maintain_roots(attachment: dict, current_root, path: str = "P1",
                   probe=None, at: str | None = None) -> dict:
    """按 §3.4 的顺序维护 roots。返回 `{action, reason?, facts?}`，并就地更新 attachment。

    action ∈ {"normal", "disclose", "stale", "block"}
    """
    probe = probe or session_mod.Probe()
    boot = probe.boot
    snapshot = [root for root in (attachment.get("roots") or []) if isinstance(root, dict)]

    known = any(session_mod._same_root(root, current_root) for root in snapshot)
    others = [root for root in snapshot if not session_mod._same_root(root, current_root)]
    states = [session_mod.state_of_root(root, boot, probe) for root in others]
    others_alive = [root for root, state in zip(others, states) if state == session_mod.ALIVE]
    others_unknown = [root for root, state in zip(others, states) if state == session_mod.UNVERIFIED]
    others_dead = [root for root, state in zip(others, states) if state == session_mod.DEAD]

    # 1) 需要旧根证据的判定：不认识当前 root，且没有存活兄弟根
    if others_unknown and not known and not others_alive:
        return {"action": "block", "reason": EVIDENCE_UNKNOWN,
                "facts": {"roots_unverified": others_unknown}}

    # 2) C2 分级：未登记的调用者 + 有存活兄弟根 ⇒ 阻断（**先于任何 upsert**）
    if not known and others_alive:
        return {"action": "block", "reason": CONCURRENT_CALLER,
                "facts": {"concurrent_callers": others_alive, "unknown": others_unknown}}

    # 3) 旧根全部确认 dead ⇒ 降级（仍需登记当前 root）
    stale = False
    if not known and snapshot and not others_alive and not others_unknown \
            and len(others_dead) == len(others):
        attachment["activation_stale"] = True
        stale = True

    # 4) 维护：upsert 当前 root；只剪 confirmed dead；unverified 一律保留
    kept = []
    for root in snapshot:
        if session_mod._same_root(root, current_root):
            kept.append(current_root)          # 刷新记录（last_seen 由此更新）
            continue
        if session_mod.state_of_root(root, boot, probe) == session_mod.DEAD:
            continue                            # 只剪 confirmed dead
        kept.append(root)                       # alive / unverified 一律保留
    if not known:
        kept.append(current_root)
    attachment["roots"] = kept
    attachment["last_maintained_at"] = at

    if stale:
        return {"action": "stale", "reason": "activation_stale",
                "facts": {"roots": kept}}
    if others_alive:
        return {"action": "disclose", "reason": None,
                "facts": {"concurrent_callers": others_alive}}
    return {"action": "normal", "reason": None, "facts": {"roots": kept}}


# --------------------------------------------------------------------------
# 会话租约状态（K2 的投影，不落盘）
# --------------------------------------------------------------------------


def boundary_alive(attachment, probe=None):
    """执行边界是否仍存活：L1 锚或任一 root 存活。读不到不当作存活。"""
    probe = probe or session_mod.Probe()
    boot = probe.boot
    l1 = (attachment or {}).get("attached_l1")
    if isinstance(l1, dict) and session_mod.state_of_l1(l1, boot, probe) == session_mod.ALIVE:
        return True
    for root in (attachment or {}).get("roots") or []:
        if isinstance(root, dict) and session_mod.state_of_root(root, boot, probe) == session_mod.ALIVE:
            return True
    return False


def lease_state(writer, session_key, attachment=None, binding=None, probe=None):
    """会话租约状态：live / superseded / gone / unknown（派生值，不落盘）。

    判据顺序固定（先"记录是否可解释"，再"谁持有"，最后"边界是否还活着"）：

    1. writer 记录不可解释 → unknown（写入侧不得据此判有效写入权）；
    2. holder 是别的会话 → superseded（本会话的旧代次已被接管，其写入按 WF_GENERATION_STALE 失效）；
    3. 有附件且执行边界已不存活 → gone（可经人确认接管，接管 bump generation）；
    4. holder 是本会话 → live（显式模式下没有附件也成立：身份由信封承载）；
    5. 有绑定、附件缺失、且持有者不是本会话 → unknown（无从核对边界，不猜）；
    6. 其余 → live。

    这条取代 v42 §4 要删的五态/轮换：失效由 generation 比较表达，状态本身只作投影。
    """
    from . import writer as writer_mod

    writer = writer or {}
    try:
        writer_mod.require_supported(writer)
    except Exception:
        return UNKNOWN
    holder = writer.get("holder")
    holder = holder if isinstance(holder, dict) else {}
    if holder.get("kind") == "session" and holder.get("id") != session_key:
        return SUPERSEDED
    if attachment is not None and not boundary_alive(attachment, probe):
        return GONE
    if holder.get("id") == session_key:
        return LIVE
    if attachment is None and binding:
        return UNKNOWN
    return LIVE


def conflicting_owners(routes, anchor_keys, session_key):
    """宿主标识与进程锚不一致时，返回锚点指向、但不含本会话的 owner。

    空列表＝无冲突（锚点没登记过会话，或登记的就是本会话）；非空即"多源冲突"，
    不得猜，交人钉住（`enable --identity`）。
    """
    owners = []
    for key in anchor_keys or ():
        for owner in owners_of(routes, key):
            if owner != session_key and owner not in owners:
                owners.append(owner)
    return owners
