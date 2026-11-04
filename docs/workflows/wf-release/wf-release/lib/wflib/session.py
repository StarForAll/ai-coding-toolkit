"""session.py — 会话身份、SessionKey 与持久绑定（机制稿 §1.4）。

身份只来自请求信封，不读环境变量或命令行。
"""

from __future__ import annotations

import os
import re
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


def new_instance_id() -> str:
    return uuid.uuid4().hex


SUPPORTED_TRANSPORTS = ("request_json",)   # 机制稿 §1.4：transport 首版只取 request_json
OBSERVATION_KINDS = ("compaction", "reentry", "new-session", "transport")


def check_profile(profile, session: dict):
    """核 session_profile.capability（机制稿 §1.4 能力状态消费）。

    返回 (code, facts)：code 为 None 表示通过。
    """
    if not isinstance(profile, dict) or not profile:
        return "WF_IDENTITY_UNRESOLVED", {"reason": "session_profile missing", "host_id": None}
    declared = profile.get("host_id")
    provider = profile.get("provider")
    transport = profile.get("transport")
    capability = profile.get("capability") or {}
    facts = {
        "declared_host_id": declared,
        "declared_provider": provider,
        "declared_transport": transport,
        "capability_status": capability.get("status"),
    }
    if session.get("provider") == "host" and declared and session["identity"].get("host_id") != declared:
        facts["reason"] = "host_id does not match installed session_profile"
        return "WF_IDENTITY_UNRESOLVED", facts
    if provider and session.get("provider") != provider:
        facts["reason"] = "provider does not match installed session_profile"
        return "WF_IDENTITY_UNRESOLVED", facts
    if capability.get("status") != "verified":
        facts["reason"] = "capability not verified"
        facts["unverified"] = ["same-session reentry/compaction", "new-session distinction", "structured request transport"]
        return "WF_IDENTITY_UNRESOLVED", facts
    # `status=verified` 是人的声明，但声明必须有结构：宿主映射、传递方式与观察依据缺一不可。
    # 这不是要求脚本认证人的真实性（那是人判语义），而是核声明本身是否成立（机制稿 §1.4）。
    missing = []
    if not declared:
        missing.append("host_id")
    if not provider:
        missing.append("provider")
    if not transport:
        missing.append("transport")
    if transport and transport not in SUPPORTED_TRANSPORTS:
        facts["reason"] = "transport is not a supported structured request channel"
        facts["transport"] = transport
        facts["supported"] = sorted(SUPPORTED_TRANSPORTS)
        return "WF_IDENTITY_UNRESOLVED", facts
    evidence = [item for item in capability.get("evidence_refs") or [] if isinstance(item, dict) and item]
    if not evidence:
        missing.append("capability.evidence_refs")
    else:
        # 每条须带可定位的观察引用（kind + ref），且 kind 属机制稿列举的观察类别；
        # 安装器转写声明的 declared-verification 不算观察（否则等于自证）
        observed = [item for item in evidence
                    if item.get("kind") in OBSERVATION_KINDS and str(item.get("ref") or "").strip()]
        if not observed:
            facts["reason"] = "capability is declarative: no actual observation evidence"
            facts["evidence_kinds"] = sorted({str(item.get("kind")) for item in evidence})
            facts["accepted_kinds"] = list(OBSERVATION_KINDS)
            return "WF_IDENTITY_UNRESOLVED", facts
    if missing:
        facts["reason"] = "capability verification is declarative but structurally incomplete"
        facts["missing"] = missing
        return "WF_IDENTITY_UNRESOLVED", facts
    return None, facts
