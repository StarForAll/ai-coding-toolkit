"""protocol.py — `protocol/*.json` 的唯一加载与校验入口（v42 P0；单一口径见任务 design §2）。

`protocol/` 是状态、转移、阶段模型句、原因码、阈值与脱敏口径的机器事实源；
本模块只做加载、结构校验和派生查询，**不持有第二份枚举**。码值语义的权属仍在
机制稿 §11.1（`scripts/wf-protocol-docs.py --check` 负责反向核对）。

落点：`<root>/protocol/`，与 `lib/wflib/` 同级（源树 `payload/protocol`，
安装后 `.wf/protocol`）。
"""

from __future__ import annotations

import json
import os

SCHEMA_VERSION = 1
DIR_NAME = "protocol"

STATUS_VALUES = ("not_started", "in_progress", "archived")
PHASE_VALUES = ("plan", "execute", "check", "finish")
TIER_VALUES = ("pass", "blocked", "needs_decision")


class ProtocolError(Exception):
    """protocol 资产缺失或结构非法：属资产能力问题，不给业务判断。"""

    code = "WF_CAPABILITY_UNAVAILABLE"

    def __init__(self, message, facts=None):
        super().__init__(message)
        self.facts = facts or {}


def directory():
    """`lib/wflib/protocol.py` → 同级两层之上的 `protocol/`。"""
    here = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(os.path.dirname(os.path.dirname(here)), DIR_NAME)


def _load(name, root=None):
    path = os.path.join(root or directory(), f"{name}.json")
    try:
        with open(path, "r", encoding="utf-8") as handle:
            payload = json.load(handle)
    except OSError as exc:
        raise ProtocolError(f"protocol asset missing: {path}", {"asset": name, "path": path, "reason": str(exc)}) from exc
    except ValueError as exc:
        raise ProtocolError(f"protocol asset unreadable: {path}", {"asset": name, "path": path, "reason": str(exc)}) from exc
    if not isinstance(payload, dict):
        raise ProtocolError(f"protocol asset is not an object: {path}", {"asset": name, "path": path})
    version = payload.get("schema_version")
    if version != SCHEMA_VERSION:
        raise ProtocolError(
            f"protocol asset schema_version mismatch: {path}",
            {"asset": name, "path": path, "expected": SCHEMA_VERSION, "actual": version},
        )
    return payload


# --------------------------------------------------------------------------
# 状态与转移
# --------------------------------------------------------------------------


class States:
    def __init__(self, payload):
        status = payload.get("status") or {}
        phase = payload.get("phase") or {}
        self.status_enum = tuple(status.get("enum") or ())
        self.status_initial = status.get("initial")
        self.status_display = dict(status.get("display") or {})
        self.phase_enum = tuple(phase.get("enum") or ())
        self.phase_initial = phase.get("initial")
        self.phase_display = dict(phase.get("display") or {})
        self.phase_model = payload.get("phase_model") or ""
        self.execution_candidate = payload.get("execution_candidate") or ""
        self.terminal = dict(payload.get("terminal") or {})
        self.transitions = tuple(payload.get("transitions") or ())
        self.legal_positions = dict(payload.get("legal_positions") or {})
        self.next_by_position = dict(payload.get("next_by_position") or {})
        self.next_by_mark = dict(payload.get("next_by_mark") or {})
        self._validate()

    def _validate(self):
        problems = []
        if self.status_enum != STATUS_VALUES:
            problems.append({"kind": "status_enum", "expected": list(STATUS_VALUES), "actual": list(self.status_enum)})
        if self.phase_enum != PHASE_VALUES:
            problems.append({"kind": "phase_enum", "expected": list(PHASE_VALUES), "actual": list(self.phase_enum)})
        if self.status_initial not in self.status_enum:
            problems.append({"kind": "status_initial", "actual": self.status_initial})
        if self.phase_initial not in self.phase_enum:
            problems.append({"kind": "phase_initial", "actual": self.phase_initial})
        if self.terminal.get("status") not in self.status_enum:
            problems.append({"kind": "terminal_status", "actual": self.terminal.get("status")})
        if not self.phase_model.strip():
            problems.append({"kind": "phase_model", "reason": "empty"})
        if not self.transitions:
            problems.append({"kind": "transitions", "reason": "empty"})
        required_next = {"session", "archived"}
        for status in self.status_enum:
            if status not in self.legal_positions:
                problems.append({"kind": "legal_positions", "missing_status": status})
        for entry in self.transitions:
            for position in list(entry.get("from") or ()) + list(entry.get("to") or ()):
                status = position.get("status")
                if status in self.status_enum and "phase" in position:
                    required_next.add(f"{status}/{position['phase']}")
                allowed = self.legal_positions.get(status)
                if allowed is None:
                    problems.append({"kind": "legal_positions", "missing_status": status})
                elif "phase" in position and position["phase"] not in allowed:
                    problems.append({"kind": "illegal_position", "id": entry.get("id"),
                                     "status": status, "phase": position.get("phase")})
        for key in sorted(required_next):
            if key not in self.next_by_position:
                problems.append({"kind": "next_by_position", "missing": key})
        for entry in self.transitions:
            name = entry.get("id") or "<unnamed>"
            if not entry.get("id") or not entry.get("action"):
                problems.append({"kind": "transition_shape", "id": name})
            for position in list(entry.get("from") or ()) + list(entry.get("to") or ()):
                if position.get("status") not in self.status_enum:
                    problems.append({"kind": "transition_status", "id": name, "actual": position.get("status")})
                if "phase" in position and position["phase"] not in self.phase_enum:
                    problems.append({"kind": "transition_phase", "id": name, "actual": position.get("phase")})
            for position in entry.get("to") or ():
                terminal = position.get("terminal")
                if terminal is not None and terminal not in (self.terminal.get("enum") or ()):
                    problems.append({"kind": "transition_terminal", "id": name, "actual": terminal})
        if problems:
            raise ProtocolError("protocol/states.json failed its own schema check", {"problems": problems})

    def next_for(self, status=None, phase=None, *, paused=False, suspended=False):
        """`wf status` 的 `next` 唯一来源：挂起 > 暂停 > 位置 > 会话。"""
        if suspended and "suspended" in self.next_by_mark:
            return self.next_by_mark["suspended"]
        if paused and "paused" in self.next_by_mark:
            return self.next_by_mark["paused"]
        if status == self.terminal.get("status"):
            return self.next_by_position["archived"]
        if status is not None and phase is not None:
            key = f"{status}/{phase}"
            if key in self.next_by_position:
                return self.next_by_position[key]
        return self.next_by_position["session"]


# --------------------------------------------------------------------------
# 原因码、阈值、脱敏
# --------------------------------------------------------------------------


def _codes(payload):
    raw = payload.get("codes") or {}
    if not raw:
        raise ProtocolError("protocol/codes.json has no codes", {"asset": "codes"})
    table = {}
    problems = []
    for name, entry in raw.items():
        tier = (entry or {}).get("tier")
        if tier not in TIER_VALUES:
            problems.append({"code": name, "reason": "tier", "actual": tier})
            continue
        if not (entry.get("exit") or "").strip():
            problems.append({"code": name, "reason": "exit empty"})
        if tier != "pass" and not (entry.get("prohibited_repairs") or "").strip():
            problems.append({"code": name, "reason": "prohibited_repairs empty"})
        table[name] = (tier, entry.get("exit") or "", entry.get("prohibited_repairs"))
    if problems:
        raise ProtocolError("protocol/codes.json failed its own schema check", {"problems": problems})
    return table


def _thresholds(payload):
    raw = payload.get("keys") or {}
    if not raw:
        raise ProtocolError("protocol/thresholds.json has no keys", {"asset": "thresholds"})
    problems = []
    for name, entry in raw.items():
        entry = entry or {}
        kind = entry.get("type")
        if kind not in ("positive_int", "bool", "int_zero_unbounded", "optional_path", "uuid4_hex", "enum"):
            problems.append({"key": name, "reason": "type", "actual": kind})
        if kind in ("positive_int", "int_zero_unbounded", "bool") and "default" not in entry:
            problems.append({"key": name, "reason": "default missing"})
        if kind == "enum":
            values = entry.get("values")
            if not isinstance(values, list) or not values or len(set(values)) != len(values):
                problems.append({"key": name, "reason": "enum values must be a non-empty unique list"})
            elif entry.get("default") not in values:
                problems.append({"key": name, "reason": "enum default must be one of values"})
    if problems:
        raise ProtocolError("protocol/thresholds.json failed its own schema check", {"problems": problems})
    return dict(raw)


def _redaction(payload):
    rules = payload.get("rules") or []
    if payload.get("direction") != "strictly-tighten":
        raise ProtocolError(
            "protocol/redaction.json direction must stay 'strictly-tighten'",
            {"direction": payload.get("direction")},
        )
    if not rules:
        raise ProtocolError("protocol/redaction.json has no rules", {"asset": "redaction"})
    return dict(payload)


_REPO_RULES = None


def repo_rules(root=None):
    """仓库级规则文件的初始集合（K6 第 5 类）：唯一存放处是 `protocol/repo_rules.json`。"""
    global _REPO_RULES
    if _REPO_RULES is None or root is not None:
        payload = _load("repo_rules", root)
        patterns = payload.get("patterns")
        if not isinstance(patterns, list) or not patterns:
            raise ProtocolError("protocol/repo_rules.json has no patterns", {"asset": "repo_rules"})
        value = {"patterns": tuple(str(item) for item in patterns),
                 "source": payload.get("source") or "",
                 "why": payload.get("why") or ""}
        if root is not None:
            return value
        _REPO_RULES = value
    return _REPO_RULES


_STATES = None
_CODES = None
_THRESHOLDS = None
_REDACTION = None


def states(root=None):
    global _STATES
    if _STATES is None or root is not None:
        value = States(_load("states", root))
        if root is not None:
            return value
        _STATES = value
    return _STATES


def codes(root=None):
    global _CODES
    if _CODES is None or root is not None:
        value = _codes(_load("codes", root))
        if root is not None:
            return value
        _CODES = value
    return _CODES


def thresholds(root=None):
    global _THRESHOLDS
    if _THRESHOLDS is None or root is not None:
        value = _thresholds(_load("thresholds", root))
        if root is not None:
            return value
        _THRESHOLDS = value
    return _THRESHOLDS


def project_data(root=None):
    """项目数据（不是框架自有资产）的路径集合：前缀 + 具体文件。

    集合只在本文件声明一次——此前散在 `scope.vendor_assets` 的前缀元组里，
    已因此漏过 `.wf/spec/`（第二轮审查）。新增一类项目数据只改 protocol，不改代码。
    """
    payload = _load("project_data", root) or {}
    return {
        "prefixes": tuple(payload.get("prefixes") or ()),
        "files": tuple(payload.get("files") or ()),
    }


def redaction(root=None):
    global _REDACTION
    if _REDACTION is None or root is not None:
        value = _redaction(_load("redaction", root))
        if root is not None:
            return value
        _REDACTION = value
    return _REDACTION


def threshold_defaults(root=None):
    """项目配置缺省值：只取带 `default` 且非生成值的键（与机制稿 §8.1 骨架一致）。"""
    defaults = {}
    for name, entry in thresholds(root).items():
        if entry.get("in_skeleton") and "default" in entry:
            defaults[name] = entry["default"]
    return defaults
