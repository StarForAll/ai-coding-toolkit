"""writer.py — 项目写入权记录与维护回执派生（机制稿 §4.2、§4.5）。

所有函数假定调用方已在同一最小互斥（`lock.acquire`）内。
"""

from __future__ import annotations

import os
import uuid

from . import records
from .paths import join

WRITER_REL = ".wf/writer.json"
WRITER_FIELDS = (
    "schema_version",
    "id",
    "revision",
    "created_at",
    "updated_at",
    "write_mark",
    "action",
    "state",
    "generation",
    "holder",
    "handover",
    "checkpoint",
    "maintenance_results",
)


class WriterError(Exception):
    pass


def path_of(root):
    return join(root, WRITER_REL)


def initial_record():
    timestamp = records.now_str()
    return {
        "schema_version": 1,
        "id": "writer",
        "revision": 0,
        "created_at": timestamp,
        "updated_at": timestamp,
        "write_mark": None,
        "action": None,
        "state": "idle",
        "generation": 0,
        "holder": None,
        "handover": None,
        "checkpoint": None,
        "maintenance_results": [],
    }


SUPPORTED_SCHEMA = 1
WRITER_STATES = ("idle", "held", "recovering")


def require_supported(record, error_cls=Exception):
    """未知 schema 或状态组合矛盾时阻断依赖它的写入（机制稿 §1.2）。"""
    if not isinstance(record, dict):
        raise error_cls("WF_RECORD_INVALID", {"reason": "writer record is not an object"})
    schema = record.get("schema_version")
    if schema != SUPPORTED_SCHEMA:
        raise error_cls("WF_RECORD_INVALID",
                        {"reason": "unsupported writer schema", "schema_version": schema,
                         "supported": SUPPORTED_SCHEMA})
    state = record.get("state")
    if state not in WRITER_STATES:
        raise error_cls("WF_RECORD_INVALID", {"reason": "unknown writer state", "state": state})
    holder = record.get("holder")
    if state == "idle" and holder:
        raise error_cls("WF_RECORD_INVALID",
                        {"reason": "idle writer must not keep a holder", "holder": holder})
    if state == "held" and not isinstance(holder, dict):
        raise error_cls("WF_RECORD_INVALID", {"reason": "held writer requires a holder"})
    if isinstance(holder, dict):
        if not isinstance(holder.get("generation"), int):
            raise error_cls("WF_RECORD_INVALID",
                            {"reason": "holder generation missing", "holder": holder})
        if record.get("generation") != holder.get("generation"):
            # 所有权事实矛盾：任何读写入口都不得据此判断有效写入权
            raise error_cls("WF_RECORD_INVALID",
                            {"reason": "writer generation inconsistent",
                             "writer_generation": record.get("generation"),
                             "holder_generation": holder.get("generation")},
                            )
    return record


def load(root, default=None):
    return records.load_json(path_of(root), default)


def save(root, record):
    record = dict(record)
    record["updated_at"] = records.now_str()
    records.write_json(path_of(root), record)
    return record


def bump(record, **changes):
    updated = dict(record)
    updated.update(changes)
    updated["revision"] = int(record.get("revision", 0)) + 1
    return updated


def holder_ref(kind, ident, scope, generation):
    return {"kind": kind, "id": ident, "scope": scope, "generation": generation}


def acquire(record, *, kind, ident, scope, checkpoint=None):
    """idle → held，generation 严格递增。"""
    if record.get("state") != "idle":
        raise WriterError(f"writer not idle: {record.get('state')}")
    generation = int(record.get("generation", 0)) + 1
    updated = bump(
        record,
        state="held",
        generation=generation,
        holder=holder_ref(kind, ident, scope, generation),
        handover=None,
        checkpoint=checkpoint or record.get("checkpoint"),
    )
    return updated


def release(record):
    if record.get("state") != "held":
        raise WriterError(f"writer not held: {record.get('state')}")
    generation = int(record.get("generation", 0)) + 1
    return bump(record, state="idle", generation=generation, holder=None, handover=None)


def checkpoint(record, detail):
    if record.get("state") != "held":
        raise WriterError("writer not held")
    return bump(record, checkpoint=detail)


def handover_begin(record, *, to_session_key, object_ref, decision):
    if record.get("state") != "held":
        raise WriterError("handover requires held writer")
    generation = int(record.get("generation", 0)) + 1
    return bump(
        record,
        state="recovering",
        generation=generation,
        handover={
            "from": (record.get("holder") or {}).get("id"),
            "receiver_session_key": to_session_key,
            "object_or_preparation": object_ref,
            "decision": decision,
            "invalidated_generation": record.get("generation"),
        },
        holder=None,
    )


def handover_accept(record, *, session_key, scope, checkpoint=None):
    if record.get("state") != "recovering":
        raise WriterError("writer not recovering")
    handover = record.get("handover") or {}
    if handover.get("receiver_session_key") != session_key:
        raise WriterError("receiver does not match handover")
    generation = int(record.get("generation", 0)) + 1
    return bump(
        record,
        state="held",
        generation=generation,
        holder=holder_ref("session", session_key, scope, generation),
        handover=None,
        checkpoint=checkpoint,
    )


def maintenance_acquire(record, *, operation_id, scope, preview_digest):
    if record.get("state") != "idle":
        raise WriterError(f"writer not idle: {record.get('state')}")
    generation = int(record.get("generation", 0)) + 1
    return bump(
        record,
        state="held",
        generation=generation,
        holder=holder_ref("maintenance", operation_id, scope, generation),
        checkpoint={"operation": operation_id, "preview_digest": preview_digest},
    )


def owner_ref(kind, ident, scope_ref):
    return {"kind": kind, "id": ident, "scope_ref": scope_ref}


# --------------------------------------------------------------------------
# 维护回执派生（只读；首个写者读取时不回写 writer）
# --------------------------------------------------------------------------

DISPOSED_KINDS = ("commit", "reverse", "transfer")


def _disposition_complete(entry):
    disposition = entry.get("disposition") or {}
    decision = disposition.get("decision")
    evidence = disposition.get("evidence")
    kind = disposition.get("kind")
    if not isinstance(decision, dict) or not decision.get("choice"):
        return False
    if not evidence:
        return False
    if kind not in DISPOSED_KINDS:
        return False
    if decision.get("choice") != kind:
        # 处置决定必须明确授权这一种去向；reject 之类的答复不能当结案依据
        return False
    if kind == "transfer" and not disposition.get("target_task"):
        return False
    return True


def receipt_state(record, *, probe=None, disposition_probe=None):
    """把每一项 maintenance_results 派生为 persisted/applied_pending_commit/disposed/pending_check。

    disposed 需要同时满足「字段齐」与「事实可核」：`disposition_probe` 不给就按待核对处理，
    不允许只凭非空字段结案（机制稿 §4.5、D27）。
    """
    results = []
    for entry in record.get("maintenance_results") or []:
        operation = entry.get("operation")
        if not isinstance(entry, dict) or not operation:
            results.append({"operation": operation, "state": "pending_check",
                            "facts": {"reason": "unparseable receipt", "paths": _receipt_paths(entry)}})
            continue
        if _disposition_complete(entry):
            if disposition_probe is None:
                results.append({"operation": operation, "state": "pending_check",
                                "facts": {"reason": "disposition cannot be verified without a fact probe",
                                          "paths": _receipt_paths(entry)}})
                continue
            try:
                verified = disposition_probe(entry)
            except Exception as exc:  # 只读探测失败按待核对
                results.append({"operation": operation, "state": "pending_check",
                                "facts": {"reason": f"disposition probe failed: {exc}",
                                          "paths": _receipt_paths(entry)}})
                continue
            if not verified:
                results.append({"operation": operation, "state": "pending_check",
                                "facts": {"reason": "disposition facts cannot be verified",
                                          "disposition": entry.get("disposition"),
                                          "paths": _receipt_paths(entry)}})
                continue
            results.append(
                {
                    "operation": operation,
                    "state": "disposed",
                    "facts": {"disposition": entry.get("disposition")},
                }
            )
            continue
        if probe is not None:
            try:
                persisted = bool(probe(entry))
            except Exception as exc:  # 只读探测失败按待核对
                results.append(
                    {"operation": operation, "state": "pending_check",
                     "facts": {"reason": f"probe failed: {exc}", "paths": _receipt_paths(entry)}}
                )
                continue
            if persisted:
                results.append(
                    {
                        "operation": operation,
                        "state": "persisted",
                        "facts": {"head_before": entry.get("head_before")},
                    }
                )
                continue
        if entry.get("result") == "applied_pending_commit":
            results.append(
                {
                    "operation": operation,
                    "state": "applied_pending_commit",
                    "facts": {"paths": _receipt_paths(entry)},
                }
            )
        else:
            results.append(
                {"operation": operation, "state": "pending_check",
                 "facts": {"result": entry.get("result"), "paths": _receipt_paths(entry)}}
            )
    return results


def _receipt_paths(entry):
    paths = []
    for change in entry.get("changes") or []:
        if isinstance(change, dict) and change.get("path"):
            paths.append(change["path"])
    return sorted(set(paths))


def blocking_receipts(receipts, requested_paths):
    """与请求对象/路径重叠的未处置回执（WF_WIP_UNRESOLVED 的事实面）。"""
    overlaps = []
    for receipt in receipts:
        if receipt["state"] != "applied_pending_commit":
            continue
        paths = receipt["facts"].get("paths") or []
        if not paths or not requested_paths:
            overlaps.append(receipt)
            continue
        for path in requested_paths:
            if any(path == item or path.startswith(item.rstrip("/") + "/") for item in paths):
                overlaps.append(receipt)
                break
    return overlaps


def new_holder_id():
    return uuid.uuid4().hex


def exists(root):
    return os.path.exists(path_of(root))
