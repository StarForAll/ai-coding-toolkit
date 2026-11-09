#!/usr/bin/env python3
"""repair.py — 独立受控修复入口（实现稿 §3.3、§4.5.1；机制稿 §5.4）。

单文件、仅标准库、**不导入 wflib**：坏运行时下仍可达。
预览 → 终端令牌 → 同锁重核 → 受控应用 → 回执。首轮只做写权/绑定/锚点最小恢复。
"""

from __future__ import annotations

import argparse
import datetime
import fcntl
import hashlib
import json
import os
import secrets
import sys

LOCK_MARK = b"wf-lock-v1\n"
SELF_FIELDS = ("schema_version", "id", "revision", "created_at", "updated_at", "write_mark", "action",
               "state", "generation", "holder", "handover", "checkpoint", "maintenance_results")


def canonical(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def digest_of(obj):
    return "sha256:" + hashlib.sha256(canonical(obj).encode("utf-8")).hexdigest()


def file_digest(path):
    try:
        with open(path, "rb") as handle:
            return "sha256:" + hashlib.sha256(handle.read()).hexdigest()
    except FileNotFoundError:
        return None


def now_str():
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


# --- 预览令牌（与 uninstall.py 逐字一致；由 build-wf-release.py --verify-token-parity 比对） ---


class PreviewToken:
    """预览令牌（机制稿 §10.3）：随机 128 位 nonce，仅本次预览有效。

    令牌只绑定「本次预览摘要 + 本次过程」；重新预览即销毁旧 nonce，跨会话不恢复许可。
    真正的漂移防护在应用路径：确认后**在同一把锁内**重算预览并比对摘要。
    """

    def __init__(self):
        self._nonce = None
        self._digest = None

    def issue(self, preview, nonce=None):
        self._digest = digest_of(preview)
        self._nonce = nonce or secrets.token_hex(16)
        return self._nonce

    def confirm(self, supplied):
        if self._nonce is None or self._digest is None:
            return False
        return secrets.compare_digest(str(supplied), self._nonce)

    def digest(self):
        return self._digest

    def invalidate(self):
        self._nonce = None
        self._digest = None

    def revalidate(self, supplied):
        return self.confirm(supplied)


PARITY_PREVIEW = {"operation": "token-parity-check", "target_root": "<parity>",
                  "selected_paths": ["a", "b"], "intended_after": "unchanged"}


def token_parity_check(nonce=None):
    token = PreviewToken()
    issued = token.issue(PARITY_PREVIEW, nonce=nonce)
    first = token.confirm(issued)
    token.invalidate()
    after = token.revalidate(issued)
    sys.stdout.write(f"nonce={issued}\n")
    sys.stdout.write(f"digest={digest_of(PARITY_PREVIEW)}\n")
    sys.stdout.write(f"first={'ok' if first else 'reject'}\n")
    sys.stdout.write(f"after={'expired' if not after else 'accepted'}\n")
    return 0


# --- 最小互斥（与 wf.py 同一锁对象语义） ---


def _proc_start(pid):
    """只读 /proc 取进程启动时刻（第 22 字段）。"""
    try:
        with open(f"/proc/{int(pid)}/stat", "r", encoding="utf-8") as handle:
            fields = handle.read().split()
    except (OSError, ValueError):
        return None
    return fields[21] if len(fields) > 21 else None


def _live_holder(path):
    """锁文件里登记的持锁者是否仍是同一进程；无登记返回 None。"""
    try:
        with open(path, "r", encoding="utf-8") as handle:
            text = handle.read()
    except OSError:
        return None
    body = text.split("\n", 1)[1] if "\n" in text else ""
    if not body.startswith("holder "):
        return None
    fields = dict(token.split("=", 1) for token in body.strip().split() if "=" in token)
    pid = fields.get("pid")
    if not pid:
        return None
    actual = _proc_start(pid)
    if actual is None:
        return {"pid": pid, "alive": False, "reason": "holder process not running"}
    if fields.get("start") not in (None, "unknown", actual):
        return {"pid": pid, "alive": False, "reason": "pid reused by another process"}
    return {"pid": pid, "alive": True, "start": actual}


class Lock:
    """最小互斥：与 wf.py 同一锁对象语义（排他创建、未知内容不认领）。"""

    def __init__(self, root):
        self.path = os.path.join(os.path.abspath(root), ".wf-lock")
        self.fd = None

    def __enter__(self):
        created = False
        try:
            self.fd = os.open(self.path, os.O_RDWR | os.O_CREAT | os.O_EXCL, 0o644)
            created = True
        except FileExistsError:
            try:
                self.fd = os.open(self.path, os.O_RDWR)
            except OSError as exc:
                raise RuntimeError(f"cannot open lock: {exc}") from exc
        except OSError as exc:
            raise RuntimeError(f"cannot open lock: {exc}") from exc
        try:
            fcntl.flock(self.fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            os.close(self.fd)
            self.fd = None
            raise RuntimeError(f"lock busy: {exc}") from exc
        content = os.pread(self.fd, len(LOCK_MARK) + 1, 0)
        if created:
            if content:
                self._abandon("lock object appeared during exclusive creation")
            os.pwrite(self.fd, LOCK_MARK, 0)
            os.fsync(self.fd)
        elif not content.startswith(LOCK_MARK):
            # 既有空锁文件属初始化未完成、未知内容属不可识别：交人核实，不认领
            self._abandon("lock mark empty or unknown (initialization unfinished)")
        return self

    def _abandon(self, reason):
        fcntl.flock(self.fd, fcntl.LOCK_UN)
        os.close(self.fd)
        self.fd = None
        raise ValueError(reason)

    def __exit__(self, exc_type, exc, tb):
        if self.fd is not None:
            try:
                fcntl.flock(self.fd, fcntl.LOCK_UN)
            finally:
                os.close(self.fd)
        return False


def read_json(path):
    try:
        with open(path, "r", encoding="utf-8") as handle:
            return json.load(handle)
    except FileNotFoundError:
        return None
    except ValueError:
        return {"__invalid__": True}


def write_json(path, value):
    tmp = path + ".wf-tmp"
    with open(tmp, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(tmp, path)


def blocker(code, message, facts=None, json_mode=False):
    payload = {"ok": False, "code": code, "next": message, "facts": facts or {}}
    if json_mode:
        sys.stdout.write(json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n")
    else:
        sys.stdout.write(f"BLOCKED  {code}\n{message}\n")
        if facts:
            sys.stdout.write("事实: " + json.dumps(facts, ensure_ascii=False, sort_keys=True) + "\n")
    return 1


def ok(message, facts=None, json_mode=False):
    if json_mode:
        sys.stdout.write(json.dumps({"ok": True, "code": "WF_OK", "message": message, "facts": facts or {}},
                                    ensure_ascii=False, sort_keys=True) + "\n")
    else:
        sys.stdout.write(message + "\n")
    return 0


def build_preview(root, action):
    writer_path = os.path.join(root, ".wf/writer.json")
    writer = read_json(writer_path)
    bindings = []
    directory = os.path.join(root, ".wf/session-bindings")
    if os.path.isdir(directory):
        for name in sorted(os.listdir(directory)):
            if name.endswith(".json"):
                bindings.append({"path": f".wf/session-bindings/{name}",
                                 "digest": file_digest(os.path.join(directory, name))})
    return {
        "operation": action,
        "target_root": os.path.abspath(root),
        "writer": {"state": (writer or {}).get("state"),
                   "generation": (writer or {}).get("generation"),
                   "holder": (writer or {}).get("holder")},
        "bindings": bindings,
        "selected_paths": [".wf/writer.json"],
        "intended_after": "writer idle（代次 +1，保留维护回执）",
    }


def dispose_plan(root, plan_path):
    plan = read_json(plan_path)
    if not isinstance(plan, dict):
        return blocker("WF_PATH_INVALID", "处置计划不可解析", {"path": plan_path})
    operation = plan.get("operation")
    disposition = plan.get("disposition")
    if not operation or not isinstance(disposition, dict):
        return blocker("WF_SEMANTIC_DECISION", "处置计划需含 operation 与 disposition")
    writer_path = os.path.join(root, ".wf/writer.json")
    writer = read_json(writer_path)
    if not isinstance(writer, dict) or "__invalid__" in writer:
        return blocker("WF_RECORD_INVALID", "writer 记录不可解析，不能写回处置")
    receipts = writer.get("maintenance_results") or []
    targets = [entry for entry in receipts if entry.get("operation") == operation]
    if not targets:
        return blocker("WF_HISTORY_UNRESOLVED", "未找到对应维护回执", {"operation": operation})
    if len(targets) > 1:
        # 同一 operation 有多条回执时，预览只展示一条而写入全改会造成"改了没看见"：
        # 交人先明确处置哪一条（预览与写入面必须同一集合）
        return blocker("WF_SEMANTIC_DECISION", "同一 operation 存在多条维护回执，无法确定处置对象",
                       {"operation": operation, "count": len(targets),
                        "exits": ["按 operation 唯一化后重新预览", "人工核对重复回执"]})
    targets[0]["disposition"] = disposition
    writer["revision"] = int(writer.get("revision", 0)) + 1
    writer["updated_at"] = now_str()
    write_json(writer_path, writer)
    return ok("OK  WF_OK\n已写回维护组处置（不改业务内容）", {"operation": operation})




def dispose_preview(root, plan_path):
    """处置回写的只读预览：核计划形状、writer 状态与目标回执。"""
    plan = read_json(plan_path)
    if not isinstance(plan, dict) or "__invalid__" in plan:
        return None, blocker("WF_PATH_INVALID", "处置计划不可解析", {"path": plan_path})
    operation = plan.get("operation")
    disposition = plan.get("disposition")
    if not operation or not isinstance(disposition, dict):
        return None, blocker("WF_SEMANTIC_DECISION", "处置计划需含 operation 与 disposition")
    writer = read_json(os.path.join(root, ".wf/writer.json"))
    if not isinstance(writer, dict) or "__invalid__" in writer:
        return None, blocker("WF_RECORD_INVALID", "writer 记录不可解析，不能写回处置")
    # 处置回写只改该回执的 disposition 字段：互斥由同一最小锁保证，不要求写权空闲
    target = [entry for entry in writer.get("maintenance_results") or []
              if entry.get("operation") == operation]
    if not target:
        return None, blocker("WF_HISTORY_UNRESOLVED", "未找到对应维护回执", {"operation": operation})
    entry = target[0]
    return {
        "operation": "dispose",
        "target_root": os.path.abspath(root),
        "receipt_operation": operation,
        "receipt_result": entry.get("result"),
        "writer_state": writer.get("state"),
        "writer_holder": writer.get("holder"),
        "receipt_paths": [change.get("path") for change in entry.get("changes") or []],
        "disposition": disposition,
        "intended_after": "只写该维护回执的 disposition 字段；不改资产、不改业务记录",
    }, None


def dispose_flow(root, plan_path, apply_now, nonce, json_mode):
    preview, error = dispose_preview(root, plan_path)
    if error is not None:
        return error
    token = PreviewToken()
    issued = token.issue(preview, nonce=nonce)
    lines = [
        "wf 维护组处置预览（未写入任何文件）",
        f"目标：{preview['target_root']}",
        f"回执：{preview['receipt_operation']}（result={preview['receipt_result']}）",
        f"当前写权：state={preview['writer_state']}（回写只改 disposition，不动 holder/代次）",
        f"回执路径：{len(preview['receipt_paths'])} 项",
        f"处置：{json.dumps(preview['disposition'], ensure_ascii=False, sort_keys=True)}",
        "写入范围：仅该回执的 disposition 字段",
        f"预览摘要：{token.digest()}",
        f"令牌：{issued}",
    ]
    sys.stdout.write("\n".join(lines) + "\n")
    sys.stdout.flush()
    if not apply_now:
        sys.stdout.write("确认后在同一个终端加 --apply 重跑并输入令牌。\n")
        sys.stdout.flush()
        return ok("", {"preview": preview, "token_digest": token.digest()}, json_mode)
    sys.stdout.write("请输入令牌确认：")
    sys.stdout.flush()
    supplied = sys.stdin.readline().strip() if sys.stdin else ""
    if not token.confirm(supplied):
        return blocker("WF_PREVIEW_STALE", "令牌不匹配或预览已失效（需在同一进程重新预览）", {}, json_mode)
    try:
        with Lock(root):
            # 确认后在同一把锁内重算处置预览：计划文件被改动即失效（机制稿 §10.3）
            fresh, fresh_error = dispose_preview(root, plan_path)
            if fresh_error is not None:
                return fresh_error
            if digest_of(fresh) != token.digest():
                return blocker("WF_PREVIEW_STALE",
                               "预览已失效：确认后处置计划与预览不一致，请重新预览",
                               {"preview_digest": token.digest(), "current_digest": digest_of(fresh)},
                               json_mode)
            return dispose_plan(root, plan_path)
    except RuntimeError as exc:
        # dispose 不要求写权空闲，只需要互斥：出口要写清"稍后重试即可"，别让人按写权抢占去处置
        return blocker("WF_WRITER_BUSY",
                       f"{exc}；该动作不要求写权空闲、只需互斥，稍后重试即可（无需交接/抢占写权）",
                       {"target": root, "lock": os.path.join(os.path.abspath(root), ".wf-lock"),
                        "guidance": "dispose 只回写维护回执的 disposition；等当前持有者释放后重试即可"},
                       json_mode)
    except ValueError as exc:
        return blocker("WF_CAPABILITY_UNAVAILABLE", f"锁对象异常：{exc}（人工核实后删除该文件再重试）",
                       {"target": root, "lock": os.path.join(os.path.abspath(root), ".wf-lock")}, json_mode)


def main(argv=None):
    parser = argparse.ArgumentParser(description="wf 受控修复（独立单文件入口）")
    parser.add_argument("--project", required=False)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--nonce", default=None, help="仅测试形态：注入固定 nonce")
    parser.add_argument("--dispose", default=None, help="维护组处置计划（预览 → 令牌 → 回写）")
    parser.add_argument("--token-parity-check", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    if args.token_parity_check:
        return token_parity_check(args.nonce)
    root = args.project or os.environ.get("WF_PROJECT_ROOT")
    if not root or not os.path.isabs(root) or not os.path.isdir(root):
        return blocker("WF_PATH_INVALID", "必须用 --project <绝对路径> 显式给目标", {"project": root}, args.json)
    if not os.path.isdir(os.path.join(root, ".wf")):
        return blocker("WF_CAPABILITY_UNAVAILABLE", "目标不是 wf 项目（缺 .wf/）", {"target": root}, args.json)

    if args.dispose:
        return dispose_flow(root, args.dispose, args.apply, args.nonce, args.json)

    preview = build_preview(root, "repair")
    token = PreviewToken()
    issued = token.issue(preview, nonce=args.nonce)
    lines = [
        "wf 受控修复预览（未写入任何文件）",
        f"目标：{os.path.abspath(root)}",
        f"writer: state={preview['writer']['state']} generation={preview['writer']['generation']}",
        f"持有者：{json.dumps(preview['writer']['holder'], ensure_ascii=False)}",
        f"绑定记录：{len(preview['bindings'])} 条",
        "候选修复：把 writer 置为 idle（代次 +1，保留 maintenance_results），不删绑定、不改业务记录。",
        f"预览摘要：{token.digest()}",
        f"令牌：{issued}",
    ]
    sys.stdout.write("\n".join(lines) + "\n")
    sys.stdout.flush()
    if not args.apply:
        sys.stdout.write("确认旧写者已停止后，在同一终端加 --apply 重跑并输入令牌。\n")
        sys.stdout.flush()
        return ok("", {"preview": preview, "token_digest": token.digest()}, args.json)
    sys.stdout.write("请输入令牌确认：")
    sys.stdout.flush()
    supplied = sys.stdin.readline().strip() if sys.stdin else ""
    if not token.confirm(supplied):
        return blocker("WF_PREVIEW_STALE", "令牌不匹配或预览已失效（需在同一进程重新预览）", {}, args.json)
    try:
        with Lock(root):
            # 消费存活探测：登记的持锁者仍活着就不能清空写权（人工确认不能替代存活事实）
            live = _live_holder(os.path.join(root, ".wf-lock"))
            if live and live.get("alive"):
                return blocker("WF_WRITER_BUSY",
                               "旧写者进程仍存活：停止该会话后重新预览",
                               {"holder": live}, args.json)
            # 确认后在同一把锁内重算预览：任何差异都使预览失效（机制稿 §10.3）
            fresh = build_preview(root, "repair")
            if digest_of(fresh) != token.digest():
                return blocker("WF_PREVIEW_STALE",
                               "预览已失效：确认后写者/文件与预览不一致，请重新预览",
                               {"preview_digest": token.digest(), "current_digest": digest_of(fresh)},
                               args.json)
            writer_path = os.path.join(root, ".wf/writer.json")
            writer = read_json(writer_path)
            if not isinstance(writer, dict) or "__invalid__" in writer:
                return blocker("WF_RECORD_INVALID", "writer 记录不可解析：保留原文，按人指定事实重建",
                               {"path": writer_path}, args.json)
            if writer.get("state") == "idle":
                return ok("OK  WF_OK\nwriter 已是 idle，无需修复", {"writer": writer}, args.json)
            before = dict(writer)
            writer["generation"] = int(writer.get("generation", 0)) + 1
            writer["state"] = "idle"
            writer["holder"] = None
            writer["handover"] = None
            writer["checkpoint"] = {"phase": "repaired", "at": now_str()}
            writer["revision"] = int(writer.get("revision", 0)) + 1
            writer["updated_at"] = now_str()
            receipts = list(writer.get("maintenance_results") or [])
            receipts.append({
                "operation": f"repair-{secrets.token_hex(8)}",
                "preview_digest": digest_of(preview),
                "head_before": None,
                "changes": [{"path": ".wf/writer.json", "before": digest_of(before),
                             "after": digest_of(writer)}],
                "receipt_git_state": {"scope": "writer-only"},
                "result": "applied_pending_commit",
                "disposition": None,
            })
            writer["maintenance_results"] = receipts
            write_json(writer_path, writer)
    except RuntimeError as exc:
        return blocker("WF_WRITER_BUSY", str(exc), {"target": root}, args.json)
    except ValueError as exc:
        return blocker("WF_CAPABILITY_UNAVAILABLE", f"锁对象异常：{exc}（人工核实后删除该文件再重试）",
                       {"target": root, "lock": os.path.join(os.path.abspath(root), ".wf-lock")}, args.json)
    return ok("OK  WF_OK\n已恢复 writer 为空闲（代次递增，回执保留）",
              {"generation": writer.get("generation"), "receipts": len(writer.get("maintenance_results") or [])},
              args.json)


if __name__ == "__main__":
    raise SystemExit(main())
