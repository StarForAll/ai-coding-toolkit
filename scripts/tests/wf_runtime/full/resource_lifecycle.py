#!/usr/bin/env python3
"""resource_lifecycle.py — 结果身份、run 生命周期与产物登记的唯一实现。

职责边界（父任务 design §2.1/§2.2/§3.1/§4.1，C2 交付）：

- **owner schema 2**：`.wf-results-owner.json` 只证明“协议归属 + 已登记执行意图”，
  不证明清理完成；新代码不再写 schema 缺失的旧 owner；
- **run-state schema 1**：`run-state.json` 记录本代 run_id/root/role/state/cleanup_state，
  `active` 只表示没有完整终态，不表示仍有活进程；
- **begin_run**：lease 持锁后唯一一次调用，按顺序“核旧代 → 原子写 owner 意图 →
  原子写 active state → 按旧代许可准备产物”，三个初始化 checkpoint 只在 helper 内退出
  （os._exit(97)），shell 读到非零后原样退出，不重做/不清理；
- **产物登记**：prepare/prune/bootstrap/inventory 共用同一份顶层产物分类，不各自再加
  白名单；已知名称不等于删除许可；
- **receipt/unit_execution 原子写**：execution 只调用这里的写入口，reader 也只用这里的
  严格读取，避免“先写一半再解释”的第二套协议。

本模块不做进程监督、不杀进程、不扫描全根、不实现 C3 的 inventory/retire CLI。
"""
from __future__ import annotations

import argparse
import json
import math
import os
from pathlib import Path
import shlex
import sys
import tempfile
import time
import uuid

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

OWNER_NAME = ".wf-results-owner.json"
RUN_STATE_NAME = "run-state.json"
COMMANDS_DIR = "commands"
PLAN_NAME = "plan.json"
METRICS_NAME = "summary-metrics.json"
SUMMARY_NAME = "summary.json"
CONTROL_NAME = ".runner.json"
CONTROL_LOG_NAME = ".runner.log"
RELEASE_CONTEXT_NAME = "release-context.json"

RESULT_OWNER = "wf-test-fixture-v1"
OWNER_SCHEMA = 2
OWNER_PROTOCOL = 1
STATE_SCHEMA = 1
RECEIPT_SCHEMA = 1
UNIT_EXECUTION_SCHEMA = 1
INTENTS = ("plan-only", "execution")
ROLES = ("full", "repro")
RUN_STATES = ("active", "finished")
CLEANUP_STATES = ("unknown", "cleaned", "failed")
LOCAL_STATES = ("none", "pending", "removed", "retained-keep", "retained-unknown", "failed")
EVIDENCE_SCOPES = ("managed-child", "root-control", "standalone-command")

# 结果初始化 checkpoint（父任务 design §5.1）：只在测试开关 + owned scope 下生效。
INIT_CHECKPOINTS = ("after-owner-intent", "after-run-state-before-prepare",
                    "after-prepare-before-controller")
FAULT_ENV = "WF_RESULTS_INIT_STOP_AFTER"
FAULT_SWITCH = "WF_TEST_FAULT_INJECTION"

# 顶层产物登记（父任务 design §4.1）：唯一来源，供 prepare/prune/bootstrap/inventory 共用。
# kind: file|dir|pattern；prepare: delete|rewrite|keep；prune: protocol|report|keep。
ARTIFACTS = (
    {"name": OWNER_NAME, "kind": "file", "role": "ownership", "prepare": "rewrite",
     "prune": "protocol", "note": "schema2 归属/意图；旧 schema 只作历史格式"},
    {"name": RUN_STATE_NAME, "kind": "file", "role": "lifecycle", "prepare": "rewrite",
     "prune": "protocol", "note": "run_id/state/cleanup；必须解析身份，不能只看扩展名"},
    {"name": PLAN_NAME, "kind": "file", "role": "plan", "prepare": "delete",
     "prune": "protocol", "note": "冻结计划；plan-only 也写它"},
    {"name": "plan.err", "kind": "file", "role": "plan-diagnostic", "prepare": "delete",
     "prune": "report", "note": "计划失败诊断"},
    {"name": "plan-calls", "kind": "file", "role": "evidence", "prepare": "delete",
     "prune": "report", "note": "每 run 计划调用计数"},
    {"name": "stages", "kind": "file", "role": "evidence", "prepare": "delete",
     "prune": "report", "note": "阶段入口计数"},
    {"name": "lines", "kind": "file", "role": "results", "prepare": "delete",
     "prune": "protocol", "note": "五列结果行（唯一结果集）"},
    {"name": "selection.tsv", "kind": "file", "role": "repro", "prepare": "delete",
     "prune": "report", "note": "独立/内嵌 repro 选择"},
    {"name": "summary.json", "kind": "file", "role": "summary", "prepare": "delete",
     "prune": "protocol", "note": "schema3 摘要；与 run-state/control 同 ID 才成立"},
    {"name": METRICS_NAME, "kind": "file", "role": "metrics", "prepare": "delete",
     "prune": "report", "note": "schema1 测量交接；不是清理/成功证明"},
    {"name": CONTROL_NAME, "kind": "file", "role": "control", "prepare": "delete",
     "prune": "protocol", "note": "root controller 控制结果"},
    {"name": CONTROL_LOG_NAME, "kind": "file", "role": "control-log", "prepare": "delete",
     "prune": "report", "note": "root controller 监督日志"},
    {"name": RELEASE_CONTEXT_NAME, "kind": "file", "role": "context", "prepare": "delete",
     "prune": "report", "note": "已核发行上下文（身份唯一来源）"},
    {"name": "source-hygiene.before.json", "kind": "file", "role": "hygiene", "prepare": "delete",
     "prune": "report", "note": "运行前源码卫生快照"},
    {"name": "cleanup.err", "kind": "file", "role": "cleanup-log", "prepare": "delete",
     "prune": "report", "note": "清理错误明细"},
    {"name": "cancel-request", "kind": "file", "role": "cancel", "prepare": "delete",
     "prune": "report", "note": "一次性取消请求"},
    {"name": "template.out", "kind": "file", "role": "template-log", "prepare": "delete",
     "prune": "report", "note": "run-owned 模板构建日志"},
    {"name": "repro.raw", "kind": "file", "role": "repro-log", "prepare": "delete",
     "prune": "report", "note": "内嵌 repro 原始输出"},
    {"name": "repro.counters", "kind": "file", "role": "repro-counts", "prepare": "delete",
     "prune": "report", "note": "并发 repro 计数器"},
    {"name": COMMANDS_DIR, "kind": "dir", "role": "receipts", "prepare": "delete",
     "prune": "protocol", "note": "managed-child receipts；逐项核 run_id/终态/清理证据"},
    {"name": "logs", "kind": "dir", "role": "logs", "prepare": "delete",
     "prune": "report", "note": "命令日志与 prep CLI 结果"},
    {"name": "repro", "kind": "dir", "role": "repro-results", "prepare": "delete",
     "prune": "report", "note": "内嵌 repro 结果子树（父 run 后代）"},
    {"name": "template", "kind": "dir", "role": "run-template", "prepare": "delete",
     "prune": "protocol", "note": "run-owned 模板（有 fixture 兄弟 marker）"},
    {"name": "pycache", "kind": "dir", "role": "pycache", "prepare": "delete",
     "prune": "report", "note": "run 内 pycache 前缀（默认 $WF_RESULTS_DIR/pycache）"},
)
ARTIFACT_SUFFIXES = (".json", ".out", ".log", ".timing")
STANDALONE_RECEIPT_PREFIX = ".execution-"
STANDALONE_RECEIPT_SUFFIX = ".json"
HOME_SUFFIX_MARK = ".home-"


class LifecycleError(Exception):
    """可预期的生命周期拒绝（非零退出，不写半份状态）。"""


# ---- 原子写/严格读 ----------------------------------------------------------


def atomic_write_json(path, payload):
    path = Path(path)
    if path.is_symlink():
        raise LifecycleError(f"拒绝写符号链接记录：{path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent,
                                         prefix="." + path.name, delete=False) as stream:
            temporary = Path(stream.name)
            json.dump(payload, stream, ensure_ascii=False, indent=2, sort_keys=True)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        temporary.replace(path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    return path


def read_json_object(path, label):
    """严格读：缺失/不可读/坏 JSON/非对象都抛（调用方按 unknown 归因）。"""
    try:
        data = Path(path).read_bytes()
    except FileNotFoundError as exc:
        raise LifecycleError(f"{label} is missing: {path}") from exc
    except OSError as exc:
        raise LifecycleError(f"{label} is unreadable: {path}: {exc}") from exc
    try:
        value = json.loads(data)
    except ValueError as exc:
        raise LifecycleError(f"{label} is not JSON: {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise LifecycleError(f"{label} must be a JSON object: {path}")
    return value


def canonical_root(root):
    path = str(root)
    if not os.path.isabs(path):
        raise LifecycleError(f"结果根必须是绝对路径：{root!r}")
    real = os.path.realpath(path)
    if os.path.islink(path):
        raise LifecycleError(f"结果根不能是符号链接：{path}")
    return real


def _is_int(value):
    return isinstance(value, int) and not isinstance(value, bool)


def owner_document(root, intent, run_id):
    if intent not in INTENTS:
        raise LifecycleError(f"意图只接受 {'|'.join(INTENTS)}：{intent!r}")
    if intent == "plan-only":
        if run_id is not None:
            raise LifecycleError("plan-only owner 的 run_id 必须为 null")
    else:
        if not isinstance(run_id, str) or not run_id:
            raise LifecycleError("execution owner 必须带本代 run_id")
    return {"schema_version": OWNER_SCHEMA, "owner": RESULT_OWNER, "root": canonical_root(root),
            "lifecycle_protocol": OWNER_PROTOCOL, "intent": intent, "run_id": run_id}


def classify_owner(root):
    """返回 {'kind': schema2|legacy|absent|unknown, 'payload', 'reason'}。"""
    path = Path(root) / OWNER_NAME
    if os.path.islink(path):
        return {"kind": "unknown", "payload": None, "reason": f"owner 是符号链接：{path}"}
    if not path.exists():
        return {"kind": "absent", "payload": None, "reason": ""}
    try:
        record = read_json_object(path, "results owner")
    except LifecycleError as exc:
        return {"kind": "unknown", "payload": None, "reason": str(exc)}
    expected_root = canonical_root(root)
    legacy = {"owner": RESULT_OWNER, "root": expected_root}
    if record == legacy:
        return {"kind": "legacy", "payload": record, "reason": "旧格式 owner（schema 缺失）"}
    schema = record.get("schema_version")
    if schema != OWNER_SCHEMA or isinstance(schema, bool):
        return {"kind": "unknown", "payload": record,
                "reason": f"未知 owner schema：{schema!r}（不猜版本）"}
    exact = {"schema_version", "owner", "root", "lifecycle_protocol", "intent", "run_id"}
    if set(record) != exact:
        return {"kind": "unknown", "payload": record,
                "reason": f"owner 字段集合非法：{sorted(set(record) ^ exact)}"}
    if record["owner"] != RESULT_OWNER:
        return {"kind": "unknown", "payload": record, "reason": "owner 标签不符"}
    if record["root"] != expected_root:
        return {"kind": "unknown", "payload": record, "reason": "owner root 与当前根不符"}
    protocol = record["lifecycle_protocol"]
    if not _is_int(protocol) or protocol != OWNER_PROTOCOL:
        return {"kind": "unknown", "payload": record, "reason": "owner 协议版本非法"}
    intent = record["intent"]
    if intent not in INTENTS:
        return {"kind": "unknown", "payload": record, "reason": f"owner 意图非法：{intent!r}"}
    run_id = record["run_id"]
    if intent == "plan-only" and run_id is not None:
        return {"kind": "unknown", "payload": record, "reason": "plan-only owner 带了 run_id"}
    if intent == "execution" and (not isinstance(run_id, str) or not run_id):
        return {"kind": "unknown", "payload": record, "reason": "execution owner 缺 run_id"}
    return {"kind": "schema2", "payload": record, "reason": ""}


def classify_run_state(root):
    path = Path(root) / RUN_STATE_NAME
    if os.path.islink(path):
        return {"kind": "unknown", "payload": None, "reason": "run-state 是符号链接"}
    if not path.exists():
        return {"kind": "absent", "payload": None, "reason": ""}
    try:
        record = read_json_object(path, "run-state")
    except LifecycleError as exc:
        return {"kind": "unknown", "payload": None, "reason": str(exc)}
    if record.get("schema_version") != STATE_SCHEMA or isinstance(record.get("schema_version"), bool):
        return {"kind": "unknown", "payload": record, "reason": "未知 run-state schema"}
    if record.get("root") != canonical_root(root):
        return {"kind": "unknown", "payload": record, "reason": "run-state root 与当前根不符"}
    if record.get("role") not in ROLES:
        return {"kind": "unknown", "payload": record, "reason": "run-state role 非法"}
    state = record.get("state")
    if state not in RUN_STATES:
        return {"kind": "unknown", "payload": record, "reason": f"run-state 状态非法：{state!r}"}
    if not isinstance(record.get("run_id"), str) or not record["run_id"]:
        return {"kind": "unknown", "payload": record, "reason": "run-state 缺 run_id"}
    cleanup = record.get("cleanup_state")
    if cleanup not in CLEANUP_STATES:
        return {"kind": "unknown", "payload": record, "reason": f"cleanup_state 非法：{cleanup!r}"}
    evidence = record.get("evidence_state")
    if evidence not in ("complete", "incomplete"):
        return {"kind": "unknown", "payload": record, "reason": f"evidence_state 非法：{evidence!r}"}
    if state == "active":
        return {"kind": "active", "payload": record, "reason": ""}
    return {"kind": "finished", "payload": record, "reason": ""}


ARTIFACTS_BY_NAME = {item["name"]: item for item in ARTIFACTS}


def known_top_level(name):
    """顶层名字是否属于登记过的产物（已知名称只是分类，不是删除许可）。

    未登记条目（用户放入的 JSON 目录、初始化临时文件、未知子目录）一律返回 False：
    prepare/复用前必须拒绝，不允许按扩展名顺手删掉。
    """
    if name in ARTIFACTS_BY_NAME:
        return True
    if name.endswith(ARTIFACT_SUFFIXES):
        return True
    if name.startswith(".") and STANDALONE_RECEIPT_PREFIX in name and name.endswith(".json"):
        return True
    if HOME_SUFFIX_MARK in name:
        return True
    return False


def unknown_entries(root):
    """返回未登记的顶层条目名（prepare 复用前必须为空）。"""
    try:
        names = sorted(os.listdir(root))
    except OSError as exc:
        raise LifecycleError(f"结果根不可读：{root}: {exc}") from exc
    return [name for name in names if not known_top_level(name)]


def classify_result(root):
    """自动复用/轮转前的统一分类（父任务 design §4）。

    返回 kind ∈ absent|empty|plan-only|finished-cleaned|active|incomplete-new|
    legacy-owned|unowned|unknown|unreadable，以及 reusable/automatic_prune/reason。
    """
    from fixture_scope import validate as validate_fixture_path  # 延迟导入避免循环

    root = canonical_root(root)
    try:
        validate_fixture_path(root)
    except Exception as exc:  # FixtureError/OSError 都按拒绝归因
        return {"kind": "unreadable", "reusable": False, "automatic_prune": False,
                "reason": f"结果路径不可用：{exc}"}
    path = Path(root)
    if not path.exists():
        return {"kind": "absent", "reusable": True, "automatic_prune": False, "reason": ""}
    if path.is_symlink() or not path.is_dir():
        return {"kind": "unknown", "reusable": False, "automatic_prune": False,
                "reason": "结果根不是真实目录"}
    owner = classify_owner(root)
    state = classify_run_state(root)
    entries = unknown_entries(root)
    if entries:
        return {"kind": "unknown", "reusable": False, "automatic_prune": False,
                "reason": "存在未登记的顶层条目：" + " ".join(entries[:10]),
                "owner": owner, "state": state}
    try:
        listing = sorted(os.listdir(root))
    except OSError as exc:
        return {"kind": "unreadable", "reusable": False, "automatic_prune": False,
                "reason": f"结果根不可读：{exc}"}
    non_owner = [name for name in listing if name != OWNER_NAME]
    if not non_owner:
        if owner["kind"] in ("absent", "legacy"):
            return {"kind": "empty", "reusable": True, "automatic_prune": False,
                    "reason": "", "owner": owner, "state": state}
        if owner["kind"] == "schema2":
            if owner["payload"]["intent"] == "plan-only" and state["kind"] == "absent":
                return {"kind": "empty", "reusable": True, "automatic_prune": False,
                        "reason": "空的新协议计划目录", "owner": owner, "state": state}
            return {"kind": "incomplete-new", "reusable": False, "automatic_prune": False,
                    "reason": "只有 owner 的残缺现场（保留，换新路径）", "owner": owner, "state": state}
        return {"kind": "unknown", "reusable": False, "automatic_prune": False,
                "reason": owner["reason"], "owner": owner, "state": state}
    if owner["kind"] == "legacy":
        return {"kind": "legacy-owned", "reusable": False, "automatic_prune": False,
                "reason": "旧格式 owner：不自动复用/轮转，需维护确认退役",
                "owner": owner, "state": state}
    if owner["kind"] != "schema2":
        return {"kind": "unowned", "reusable": False, "automatic_prune": False,
                "reason": "非空目录没有可验证 owner", "owner": owner, "state": state}
    intent = owner["payload"]["intent"]
    if intent == "plan-only":
        if state["kind"] != "absent":
            return {"kind": "unknown", "reusable": False, "automatic_prune": False,
                    "reason": "plan-only owner 却带 run-state", "owner": owner, "state": state}
        plan_only_extra = set(non_owner) - {PLAN_NAME}
        if plan_only_extra:
            return {"kind": "incomplete-new", "reusable": False, "automatic_prune": False,
                    "reason": "plan-only 目录含执行痕迹：" + " ".join(sorted(plan_only_extra)),
                    "owner": owner, "state": state}
        return {"kind": "plan-only", "reusable": True, "automatic_prune": False,
                "reason": "", "owner": owner, "state": state}
    if state["kind"] == "finished":
        record = state["payload"]
        if record["run_id"] != owner["payload"]["run_id"]:
            return {"kind": "incomplete-new", "reusable": False, "automatic_prune": False,
                    "reason": "owner 与 run-state 的 run_id 不一致", "owner": owner, "state": state}
        if record["cleanup_state"] != "cleaned":
            return {"kind": "active", "reusable": False, "automatic_prune": False,
                    "reason": f"上一代清理未确认：{record['cleanup_state']}",
                    "owner": owner, "state": state}
        retained = record.get("retained_paths") or []
        if retained:
            return {"kind": "active", "reusable": False, "automatic_prune": False,
                    "reason": "上一代有显式保留/未确认现场", "owner": owner, "state": state}
        if record.get("evidence_state") != "complete":
            return {"kind": "active", "reusable": False, "automatic_prune": False,
                    "reason": "上一代证据不完整（不可复用，需盘点评定）",
                    "owner": owner, "state": state}
        return {"kind": "finished-cleaned", "reusable": True, "automatic_prune": True,
                "reason": "", "owner": owner, "state": state}
    if state["kind"] == "active":
        if state["payload"]["run_id"] != owner["payload"]["run_id"]:
            return {"kind": "incomplete-new", "reusable": False, "automatic_prune": False,
                    "reason": "owner 与 active run-state 的 run_id 不一致（初始化早死/混代）",
                    "owner": owner, "state": state}
        return {"kind": "active", "reusable": False, "automatic_prune": False,
                "reason": "上一代没有完整终态（active）", "owner": owner, "state": state}
    return {"kind": "incomplete-new", "reusable": False, "automatic_prune": False,
            "reason": "run-state 缺失/损坏（初始化早死），不降级 legacy/plan-only",
            "owner": owner, "state": state}


# ---- 初始化 checkpoint -------------------------------------------------------


def _current_scope():
    try:
        import fixture_scope
        return fixture_scope.current_scope()
    except Exception as exc:  # FixtureError / ImportError 都按不可用归因
        raise LifecycleError(f"测试 scope 不可用：{exc}") from exc


def validate_init_fault():
    """校验初始化 checkpoint 开关；非法点名在首次写前拒绝。"""
    requested = os.environ.get(FAULT_ENV)
    if not requested:
        return None
    if os.environ.get(FAULT_SWITCH) != "1":
        raise LifecycleError(f"{FAULT_ENV} 只在 {FAULT_SWITCH}=1 时生效")
    if requested not in INIT_CHECKPOINTS:
        raise LifecycleError(f"未知初始化 checkpoint：{requested!r}（可选 {'|'.join(INIT_CHECKPOINTS)}）")
    if _current_scope() is None:
        raise LifecycleError("初始化 checkpoint 需要有效 owned test scope")
    return requested


def fault_point(name):
    """命中点名时先写日志并 flush，然后只让本 helper os._exit(97)。"""
    if os.environ.get(FAULT_ENV) != name:
        return
    sys.stderr.write(f"WF-RESULTS-INIT-STOP: {name} pid={os.getpid()} "
                     f"run_id={os.environ.get('WF_FRAME_RUN_ID', '')}\n")
    sys.stderr.flush()
    sys.stdout.flush()
    os._exit(97)


# ---- begin_run / claim ------------------------------------------------------


def _write_owner(root, intent, run_id):
    atomic_write_json(Path(root) / OWNER_NAME, owner_document(root, intent, run_id))


def _write_state(root, run_id, role):
    atomic_write_json(Path(root) / RUN_STATE_NAME, {
        "schema_version": STATE_SCHEMA, "run_id": run_id, "root": canonical_root(root),
        "role": role, "state": "active", "cleanup_state": "unknown",
        "evidence_state": "incomplete", "status": "running",
        "reasons": [], "retained_paths": [], "started_at": time.strftime(
            "%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "finished_at": None,
    })


def _remove_known_top_level(root):
    """按登记逐个删除本代运行产物（owner/run-state 由调用方保留）。"""
    import shutil

    import fixture_scope

    for name in sorted(os.listdir(root)):
        if name in (OWNER_NAME, RUN_STATE_NAME):
            continue
        if not known_top_level(name):
            raise LifecycleError(f"拒绝清理未登记条目：{name}")
        path = Path(root) / name
        try:
            if path.is_symlink():
                raise LifecycleError(f"拒绝清理符号链接条目：{path}")
            if path.is_dir():
                if fixture_scope.marker(path).is_file():
                    fixture_scope.remove(path)
                else:
                    # 结果目录内的 runner 自产子树（logs/commands/repro/template）：
                    # 归属来自本目录的 owner，不额外要求每个子目录带 fixture marker。
                    if path.parent != Path(root):
                        raise LifecycleError(f"拒绝清理越界目录：{path}")
                    shutil.rmtree(path)
            else:
                path.unlink()
        except OSError as exc:
            raise LifecycleError(f"准备结果产物失败：{path}: {exc}") from exc


def prepare_results(root):
    """删除上一代已核验许可的运行产物；保留本代 owner/run-state。

    只由 begin_run 在刚核验完旧代事实后调用，不提供“传一个 run_id 即可继续清理 active
    目录”的公共入口。
    """
    root = canonical_root(root)
    _remove_known_top_level(root)
    (Path(root) / "logs").mkdir(exist_ok=True)
    (Path(root) / COMMANDS_DIR).mkdir(exist_ok=True)
    return root


def begin_run(root, intent="execution", role="full", run_id=None):
    """lease 持锁后的唯一一次初始化：旧代核验 → owner → state → prepare。"""
    from fixture_scope import validate as validate_fixture_path

    root = canonical_root(root)
    requested = validate_init_fault()
    try:
        validate_fixture_path(root)
    except Exception as exc:
        raise LifecycleError(f"结果路径不可用：{exc}") from exc
    if intent not in INTENTS:
        raise LifecycleError(f"意图只接受 {'|'.join(INTENTS)}：{intent!r}")
    if role not in ROLES:
        raise LifecycleError(f"role 只接受 {'|'.join(ROLES)}：{role!r}")
    previous = classify_result(root)
    if not previous["reusable"]:
        raise LifecycleError(
            f"上一代结果不可自动复用（{previous['kind']}）：{previous['reason']}；"
            "请换新的结果目录，旧现场按盘点/退役流程处置（本任务不做自动迁移）")
    if intent == "execution":
        if not isinstance(run_id, str) or not run_id:
            run_id = new_run_id()
        if role not in ROLES:
            raise LifecycleError(f"role 非法：{role!r}")
    else:
        run_id = None
    path = Path(root)
    path.mkdir(parents=True, exist_ok=True)
    _write_owner(root, intent, run_id)
    fault_point("after-owner-intent")
    if intent == "execution":
        _write_state(root, run_id, role)
    fault_point("after-run-state-before-prepare")
    if intent == "execution":
        prepare_results(root)
    else:
        # plan-only 只写 owner；plan.py 随后写 plan.json（不建 run-state/commands）。
        pass
    fault_point("after-prepare-before-controller")
    return {"run_id": run_id, "root": root, "intent": intent, "role": role,
            "previous": previous["kind"],
            "owner_path": str(path / OWNER_NAME), "state_path": str(path / RUN_STATE_NAME)}


def claim_plan(root):
    """plan 镜像入口：只写新空目录或精确 plan-only 目录的 owner（不建 run-state）。"""
    root = canonical_root(root)
    current = classify_result(root)
    if current["kind"] not in ("absent", "empty", "plan-only"):
        raise LifecycleError(
            f"plan 镜像只能写新空目录或精确 plan-only 目录（当前 {current['kind']}）："
            f"{current['reason']}；不把 execution 意图改成 plan-only 覆盖恢复定位")
    path = Path(root)
    path.mkdir(parents=True, exist_ok=True)
    _write_owner(root, "plan-only", None)
    return root


def new_command_id():
    """每次命令调用唯一的 command_id（receipt 文件名与身份）。"""
    return f"{int(time.time() * 1000)}-{os.getpid()}-{uuid.uuid4().hex[:12]}"


def new_run_id():
    return new_command_id()


# ---- run-state 终态 ---------------------------------------------------------


def finish_run(root, run_id, role, cleanup_state, status, evidence_state="incomplete",
               retained_paths=(), reasons=()):
    if cleanup_state not in CLEANUP_STATES:
        raise LifecycleError(f"cleanup_state 非法：{cleanup_state!r}")
    if evidence_state not in ("complete", "incomplete"):
        raise LifecycleError(f"evidence_state 非法：{evidence_state!r}")
    recorded = classify_run_state(root)
    if recorded["kind"] != "active" or recorded["payload"]["run_id"] != run_id:
        raise LifecycleError("run-state 不是本代 active 状态，拒绝改写成终态")
    record = dict(recorded["payload"])
    record.update(state="finished", cleanup_state=cleanup_state, status=status,
                  evidence_state=evidence_state,
                  retained_paths=sorted(set(retained_paths)),
                  reasons=list(reasons)[:50],
                  finished_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
    atomic_write_json(Path(root) / RUN_STATE_NAME, record)
    return record


# ---- receipt / unit_execution ----------------------------------------------


def receipt_path(evidence_root, command_id):
    return str(Path(evidence_root) / (command_id + ".json"))


def standalone_receipt_path(log_path, command_id):
    log_path = Path(log_path)
    return str(log_path.parent / f".{log_path.name}.execution-{command_id}.json")


def write_receipt(path, payload):
    atomic_write_json(path, payload)
    return str(path)


def update_receipt(path, command_id, updates):
    record = read_json_object(path, "command receipt")
    if record.get("schema_version") != RECEIPT_SCHEMA or record.get("command_id") != command_id:
        raise LifecycleError(f"receipt 身份不符：{path}")
    record.update(updates)
    atomic_write_json(path, record)
    return record


def read_receipt(path):
    record = read_json_object(path, "command receipt")
    schema = record.get("schema_version")
    if schema != RECEIPT_SCHEMA or isinstance(schema, bool):
        raise LifecycleError(f"未知 receipt schema：{schema!r}")
    if record.get("evidence_scope") not in EVIDENCE_SCOPES:
        raise LifecycleError(f"receipt 证据域非法：{record.get('evidence_scope')!r}")
    if record.get("state") not in ("started", "finished"):
        raise LifecycleError(f"receipt 状态非法：{record.get('state')!r}")
    if not isinstance(record.get("command_id"), str) or not record["command_id"]:
        raise LifecycleError("receipt 缺 command_id")
    if record.get("local_cleanup") not in LOCAL_STATES:
        raise LifecycleError(f"receipt 本地清理状态非法：{record.get('local_cleanup')!r}")
    return record


def write_unit_execution(unit_result_path, unit_execution):
    """在既有 unit 结果 JSON 上串行附加 unit_execution（唯一写入口）。"""
    path = Path(unit_result_path)
    record = read_json_object(path, "unit result")
    if "unit_execution" in record:
        raise LifecycleError(f"unit 结果已有 unit_execution，拒绝重复写：{path}")
    record["unit_execution"] = unit_execution
    atomic_write_json(path, record)
    return record


def create_unit_result(unit_result_path, payload):
    path = Path(unit_result_path)
    if path.exists():
        raise LifecycleError(f"unit 结果已存在，拒绝覆盖：{path}")
    atomic_write_json(path, payload)
    return payload


# ---- 能力交接（C2 只声明 disabled，C3 接线后切 enabled）---------------------


def observe_capability():
    """兼容入口：观察能力由各材料模块的 `observe` 适配器实现，root 只调用一次。"""
    return {"enabled": True, "status": "enabled", "calls": 1, "roots": []}


# ---- CLI -------------------------------------------------------------------


def _shell_output(values):
    lines = []
    for name, value in values:
        lines.append(f"{name}={shlex.quote(str(value))}")
    return "\n".join(lines) + "\n"


def _phase_specs(values):
    phases = []
    for item in values:
        if ":" not in item:
            raise LifecycleError(f"--phase 必须是 phase:result-path（收到 {item!r}）")
        phase, path = item.split(":", 1)
        if not phase or not path:
            raise LifecycleError(f"--phase 结构非法：{item!r}")
        phases.append((phase, path))
    return phases


def _validate_result_row(row, unit):
    parts = str(row).split("\t")
    if len(parts) != 5:
        raise LifecycleError(f"result_row 必须是五列：{row!r}")
    if parts[0] != unit:
        raise LifecycleError(f"result_row 单元名不符：{parts[0]!r} != {unit!r}")
    if not parts[1].removeprefix("-").isdigit():
        raise LifecycleError(f"result_row rc 非整数：{parts[1]!r}")
    if parts[3] not in ("ok", "bad"):
        raise LifecycleError(f"result_row 状态非法：{parts[3]!r}")
    try:
        duration = float(parts[2])
    except ValueError as exc:
        raise LifecycleError(f"result_row 秒数非法：{parts[2]!r}") from exc
    if not math.isfinite(duration) or duration < 0:
        raise LifecycleError(f"result_row 秒数非法：{parts[2]!r}")
    return parts


def cmd_unit_execution(args):
    phases = _phase_specs(args.phase or [])
    if args.state == "passed" and not phases:
        raise LifecycleError("passed unit-execution 至少需要一个 --phase")
    if args.state not in ("passed", "prep-failed"):
        raise LifecycleError(f"--state 只接受 passed|prep-failed（收到 {args.state!r}）")
    row = _validate_result_row(args.result_row, args.unit)
    evidence = []
    for phase, result_path in phases:
        record = read_json_object(result_path, f"{phase} result")
        evidence_path = record.get("evidence_path")
        if not isinstance(evidence_path, str) or not evidence_path:
            raise LifecycleError(f"{phase} 结果缺 evidence_path：{result_path}")
        receipt = read_receipt(evidence_path)
        if receipt["state"] != "finished":
            raise LifecycleError(f"{phase} receipt 未到终态：{evidence_path}")
        if receipt.get("local_cleanup") not in ("none", "removed", "retained-keep"):
            raise LifecycleError(f"{phase} 本地清理未确认：{receipt.get('local_cleanup')}")
        if receipt.get("run_id") != args.run_id:
            raise LifecycleError(f"{phase} receipt 的 run_id 与本次不符")
        if phase == "test" and record.get("status") not in ("passed", "failed", "cancelled", "timeout"):
            raise LifecycleError(f"test 结果状态非法：{record.get('status')!r}")
        evidence.append({"phase": phase, "command_id": receipt["command_id"],
                         "evidence_path": evidence_path, "result_path": os.path.abspath(result_path)})
    unit_execution = {
        "schema_version": UNIT_EXECUTION_SCHEMA,
        "unit": args.unit, "invocation_id": args.invocation,
        "run_id": args.run_id, "state": args.state,
        "result_row": row,
        "command_evidence": evidence,
    }
    if args.failure_reason:
        unit_execution["failure_reason"] = args.failure_reason
    if args.state == "prep-failed" and not phases:
        # 启动登记前就失败（preflight-failed）：没有虚假 command_id。
        unit_execution["preflight_failed"] = True
    if args.state == "passed":
        if args.create_unit_result:
            raise LifecycleError("passed 状态必须附加到实际 test 结果（--unit-result）")
        write_unit_execution(args.unit_result, unit_execution)
    else:
        if args.unit_result:
            write_unit_execution(args.unit_result, unit_execution)
        else:
            # prep 失败没有 test 结果：写明确失败对象，不伪造 test 的 supervision/断言。
            create_unit_result(args.create_unit_result, {
                "schema_version": 2, "name": args.unit, "status": "failed", "rc": 1,
                "reason": args.failure_reason or "preparation failed",
                "unit_execution": unit_execution,
            })
    return 0


def _invocation_from_env():
    value = os.environ.get("WF_UNIT_INVOCATION_ID")
    return value or uuid.uuid4().hex


def main(argv=None):
    parser = argparse.ArgumentParser(description="结果身份/生命周期/产物登记的唯一实现")
    sub = parser.add_subparsers(dest="operation", required=True)

    begin = sub.add_parser("begin-run")
    begin.add_argument("--results-root", required=True)
    begin.add_argument("--intent", choices=INTENTS, default="execution")
    begin.add_argument("--role", choices=ROLES, default="full")
    begin.add_argument("--run-id", default=None)
    begin.add_argument("--format", choices=("sh", "json"), default="sh")

    claim = sub.add_parser("claim-plan")
    claim.add_argument("root")

    unit = sub.add_parser("unit-execution")
    group = unit.add_mutually_exclusive_group(required=True)
    group.add_argument("--unit-result")
    group.add_argument("--create-unit-result")
    unit.add_argument("--unit", required=True)
    unit.add_argument("--invocation", default=None)
    unit.add_argument("--run-id", default=None)
    unit.add_argument("--state", choices=("passed", "prep-failed"), required=True)
    unit.add_argument("--result-row", required=True)
    unit.add_argument("--failure-reason", default="")
    unit.add_argument("--phase", action="append", default=[])

    finish = sub.add_parser("finish-run")
    finish.add_argument("--results-root", required=True)
    finish.add_argument("--run-id", required=True)
    finish.add_argument("--role", choices=ROLES, required=True)
    finish.add_argument("--cleanup-state", choices=CLEANUP_STATES, required=True)
    finish.add_argument("--evidence-state", choices=("complete", "incomplete"), default="incomplete")
    finish.add_argument("--status", required=True)
    finish.add_argument("--retained-path", action="append", default=[])
    finish.add_argument("--reason", action="append", default=[])

    classify = sub.add_parser("classify")
    classify.add_argument("root")

    args = parser.parse_args(argv)
    try:
        if args.operation == "begin-run":
            result = begin_run(args.results_root, args.intent, args.role, args.run_id)
            if args.format == "json":
                print(json.dumps(result, ensure_ascii=False, sort_keys=True))
            else:
                sys.stdout.write(_shell_output([
                    ("RUN_ID", result["run_id"] or ""),
                    ("OWNER_PATH", result["owner_path"]),
                    ("STATE_PATH", result["state_path"]),
                    ("PREVIOUS_KIND", result["previous"]),
                ]))
            return 0
        if args.operation == "claim-plan":
            claim_plan(args.root)
            return 0
        if args.operation == "unit-execution":
            args.invocation = args.invocation or _invocation_from_env()
            return cmd_unit_execution(args)
        if args.operation == "finish-run":
            finish_run(args.results_root, args.run_id, args.role, args.cleanup_state,
                       args.status, args.evidence_state, args.retained_path, args.reason)
            return 0
        if args.operation == "classify":
            print(json.dumps(classify_result(args.root), ensure_ascii=False, sort_keys=True))
            return 0
    except LifecycleError as exc:
        print(f"LIFECYCLE-REFUSED: {exc}", file=sys.stderr)
        return 1
    return 2


# ---- 存量盘点/退役的共用契约（父任务 design §4.2）---------------------------
# 三个材料所有者各自扫描/判定归属与锁；这里只共享“选择格式、集合摘要、TTY 确认、
# 外部报告、逐项删除/部分失败”的同一套写序，避免三份不完全相同的实现。

SELECTION_SCHEMA = 1
RETIREMENT_MODES = ("safe-legacy", "manual-retained")
PROVENANCE_LEVELS = ("owned", "legacy-owned", "unproven", "empty-shell")


class RetireError(Exception):
    """存量处置拒绝（零删除或部分完成后停止）。"""


def selection_digest(entries):
    projection = [{"root": item.get("root"), "path": item["path"], "kind": item["kind"],
                   "provenance": item.get("provenance"), "digest": item.get("digest")}
                  for item in sorted(entries, key=lambda entry: entry["path"])]
    payload = json.dumps(projection, ensure_ascii=False, sort_keys=True,
                         separators=(",", ":")).encode("utf-8")
    import hashlib
    return "sha256:" + hashlib.sha256(payload).hexdigest()


def selection_entries(document, domain):
    """校验 selection 文件结构；输入字段不是权限凭证（仍要重扫描/复验）。"""
    if not isinstance(document, dict) or document.get("schema_version") != SELECTION_SCHEMA:
        raise RetireError("selection schema 必须是 1")
    if document.get("domain") != domain:
        raise RetireError(f"selection domain 不符：{document.get('domain')!r}")
    entries = document.get("entries")
    if not isinstance(entries, list) or not entries:
        raise RetireError("selection.entries 不能为空")
    seen = set()
    for item in entries:
        if not isinstance(item, dict) or not isinstance(item.get("path"), str):
            raise RetireError("selection entry 缺 path")
        if not isinstance(item.get("kind"), str) or item.get("kind") not in (
                "result-root", "fixture", "template-entry", "template-staging",
                "template-backup", "template-stale", "template-build",
                "release-entry", "release-staging", "release-backup",
                "release-stale", "release-build", "marker", "journal",
                "material-marker", "empty-shell"):
            raise RetireError(f"selection entry kind 非法：{item.get('kind')!r}")
        if not os.path.isabs(item["path"]):
            raise RetireError(f"selection path 必须是绝对路径：{item['path']!r}")
        canonical = os.path.realpath(item["path"])
        if canonical in seen:
            raise RetireError(f"selection 重复项：{canonical}")
        seen.add(canonical)
    return entries


def live_references(path, exclude_fds=()):
    """同 UID 进程对 path 的 cwd/FD 活引用（只证明本 UID 可见范围）。"""
    path = os.path.realpath(path)
    prefix = path + os.sep
    exclude = {(os.getpid(), int(fd)) for fd in exclude_fds}
    found = []
    own = os.getpid()
    for entry in Path("/proc").iterdir():
        if not entry.name.isdigit():
            continue
        pid = int(entry.name)
        try:
            stat = entry.stat()
        except OSError:
            continue
        if stat.st_uid != os.getuid():
            continue
        if pid != own:
            try:
                cwd = os.readlink(entry / "cwd")
            except OSError:
                cwd = None
            if cwd and (cwd == path or cwd.startswith(prefix)):
                found.append({"pid": pid, "kind": "cwd", "detail": cwd})
                continue
            try:
                for fd_entry in (entry / "fd").iterdir():
                    key = (pid, int(fd_entry.name))
                    if key in exclude:
                        continue
                    try:
                        target = os.readlink(fd_entry)
                    except OSError:
                        continue
                    if target == path or target.startswith(prefix):
                        found.append({"pid": pid, "kind": "fd", "detail": target})
                        break
            except OSError:
                continue
    return found


def confirm_manual_retained(domain, root, entries, unproven):
    """真实 TTY + 精确短语 + 集合摘要；任一不符零删除。"""
    digest = selection_digest(entries)
    suffixes = ["abandon"]
    if unproven:
        suffixes.append("unproven-cache")
    expected = " ".join([domain, root, digest] + suffixes)
    if not sys.stdin.isatty():
        raise RetireError("manual-retained 需要真实 TTY 确认（非 TTY 一律零删除）")
    sys.stderr.write(f"MANUAL-RETAINED-CONFIRM: {domain} root={root} entries={len(entries)} "
                     f"digest={digest}" + (" provenance=unproven" if unproven else "") + "\n")
    sys.stderr.write("输入以下整行以确认放弃所选集合（输入错误/EOF 均零删除）：\n" + expected + "\n")
    sys.stderr.flush()
    try:
        answer = sys.stdin.readline().rstrip("\n")
    except (OSError, EOFError) as exc:
        raise RetireError(f"读取确认失败：{exc}") from exc
    if answer != expected:
        raise RetireError("确认短语/摘要不符（零删除）")
    return digest


def write_retirement_report(path, payload):
    """首删前安全排他创建外部报告：已存在/不可写则零删除。"""
    path = Path(path)
    if path.exists():
        raise RetireError(f"报告已存在，拒绝覆盖：{path}")
    data = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    try:
        with open(path, "x", encoding="utf-8") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
    except OSError as exc:
        raise RetireError(f"报告创建失败（零删除）：{path}: {exc}") from exc
    return path


def execute_retirement(domain, root, entries, mode, report_path, delete_entry,
                       guard_locks, unproven_ok):
    """共同写序：锁内复验 → 报告先建 → 逐项删除 → 部分失败停止 → 终态报告字段。

    `delete_entry(entry)` 只负责单项删除并返回 None/抛 OSError；材料/树的 marker 与
    journal 的先后顺序由调用方按条目 kind 排好传入的 entries 序。
    """
    if mode not in RETIREMENT_MODES:
        raise RetireError(f"retirement mode 只接受 {'|'.join(RETIREMENT_MODES)}")
    if not report_path:
        raise RetireError("retirement 必须给 --report（外部报告路径）")
    guard_locks()
    digest = selection_digest(entries)
    report = {"schema_version": 1, "domain": domain, "root": root, "mode": mode,
              "selection_digest": digest, "selected": [
                  {"path": item["path"], "kind": item["kind"],
                   "provenance": item.get("provenance"),
                   "digest": item.get("digest"), "uid": item.get("uid")}
                  for item in entries],
              "results": [], "started_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    if mode == "manual-retained":
        unproven = any(item.get("provenance") == "unproven" for item in entries)
        if unproven and not unproven_ok:
            raise RetireError("unproven 材料需要 owner 域明确允许 unproven-cache 确认")
        confirm_manual_retained(domain, root, entries, unproven)
    write_retirement_report(report_path, report)
    for item in entries:
        path = item["path"]
        try:
            delete_entry(item)
        except OSError as exc:
            item_result = {"path": path, "kind": item["kind"], "state": "failed",
                           "error": str(exc)}
            report["results"].append(item_result)
            report["failed_at"] = path
            try:
                atomic_write_json(Path(report_path), report)
            except OSError:
                pass
            raise RetireError(f"删除失败，已停止：{path}: {exc}") from exc
        state = "removed" if not os.path.lexists(path) else "already-absent"
        report["results"].append({"path": path, "kind": item["kind"], "state": state})
    report["finished_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    atomic_write_json(Path(report_path), report)
    return report


def observe_capability_enabled(roots):
    """C3 接线后的能力交接：只读、浅层、按材料根去重。"""
    return {"enabled": True, "status": "enabled", "calls": 1,
            "roots": sorted(set(roots)), "reason": ""}


if __name__ == "__main__":
    raise SystemExit(main())

