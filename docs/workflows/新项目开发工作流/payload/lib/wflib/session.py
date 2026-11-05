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
        facts["reason"] = "wf 签发路径在第二轮交付；本轮只支持 host 身份"
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
