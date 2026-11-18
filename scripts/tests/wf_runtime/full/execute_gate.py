#!/usr/bin/env python3
"""execute_gate.py — execute 消费阶段的门：核祖先/租约/交接令牌后才允许执行。

execute 是第三次同脚本重入、最终 consumer：不再 preflight、不再 plan、不再 ensure/check。
它必须按**同一份已冻字节**核验后再执行（design §4.1 / AC16）：

1. frame 记的 entry-pid 必须是真祖先（controller 在中间）；
2. fixture lease 与当前域 results 独占锁必须仍由祖先持有，且 mount/scope 域一致；
3. `release-context.json` 摘要/长度/schema 必 match，dev 还核 release 消费 lease、
   candidate 核已核 tag/commit 事实存在；deploy/root/version/ref 必须与 frozen plan 一致；
4. `plan.json` 用 O_NOFOLLOW 读一次，先比 sha256/长度，再解析；args/registry 冻结面必须自洽。

成功时打印可 eval 的发行环境赋值（bash 只消费，不重新推导）。任何不符即拒绝，不 fallback。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shlex
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(REPO, "scripts"))
sys.path.insert(0, HERE)

import fixture_scope  # noqa: E402
import plan as plan_mod  # noqa: E402
import runner_protocol  # noqa: E402

CONTEXT_SCHEMA = 2


class GateError(Exception):
    pass


def _read_once(path, limit=1 << 20):
    if not os.path.isfile(path) or os.path.islink(path):
        raise GateError(f"not a plain file: {path}")
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        data = os.read(fd, limit)
        if os.read(fd, 1):
            raise GateError(f"file too large: {path}")
    finally:
        os.close(fd)
    return data


def _is_ancestor(pid):
    current = os.getpid()
    while current not in (pid, 0, 1):
        with open(f"/proc/{current}/status", encoding="utf-8") as stream:
            status = stream.read()
        current = int(next(line.split()[1] for line in status.splitlines() if line.startswith("PPid:")))
    return current == pid


def _verify_ancestor(entry_pid):
    if entry_pid <= 0 or not _is_ancestor(entry_pid):
        raise GateError(f"frame entry-pid 不是本进程祖先：{entry_pid}")
    if not _is_ancestor(int(os.environ.get("WF_RUNNER_CONTROL_PID") or 0)):
        raise GateError("controller 不是本进程祖先（controller 阶段被跳过）")


def _verify_plan(plan_file, plan_sha, plan_size):
    data = _read_once(plan_file)
    if len(data) != int(plan_size):
        raise GateError(f"final plan 长度不符：{len(data)} != {plan_size}")
    if hashlib.sha256(data).hexdigest() != plan_sha:
        raise GateError("final plan digest 与内部 token 不符（被替换/篡改）")
    try:
        frozen = json.loads(data)
    except ValueError as exc:
        raise GateError(f"final plan 不是 JSON：{exc}") from exc
    for key in ("mode", "units", "results_dir", "fix", "fixture_deploy"):
        if key not in frozen:
            raise GateError(f"final plan 缺字段：{key}")
    if frozen.get("list_only") != 0:
        raise GateError("final plan 仍是计划模式（list_only=1）")
    if os.path.realpath(frozen["results_dir"]) != os.path.realpath(os.environ["WF_RESULTS_DIR"]):
        raise GateError("final plan 的 results_dir 与当前 lease 不符")
    try:
        runner_protocol.validate_plan(frozen, role="full",
                                      run_id=os.environ.get("WF_RUN_ID") or "",
                                      results_dir=os.environ["WF_RESULTS_DIR"],
                                      scope_root=os.environ.get("WF_TEST_SCOPE_ROOT") or None)
    except runner_protocol.FrameError as exc:
        raise GateError(f"final plan 身份不符：{exc}") from exc
    return frozen


def _verify_context(context_file, context_sha, context_size, frozen):
    data = _read_once(context_file)
    if len(data) != int(context_size):
        raise GateError(f"release-context 长度不符：{len(data)} != {context_size}")
    if hashlib.sha256(data).hexdigest() != context_sha:
        raise GateError("release-context digest 与内部 token 不符")
    try:
        context = json.loads(data)
    except ValueError as exc:
        raise GateError(f"release-context 不是 JSON：{exc}") from exc
    if context.get("schema_version") != CONTEXT_SCHEMA:
        raise GateError(f"release-context schema 不符：{context.get('schema_version')}")
    if not context.get("release_subject"):
        raise GateError("release-context 缺 release subject（未完成身份核验）")
    runtime = context.get("runtime") or {}
    for role in ("tool", "sut"):
        projection = runtime.get(role) or {}
        if not projection.get("path_identity") or not projection.get("binary_digest"):
            raise GateError(f"release-context runtime 身份不完整：{role}")
    deploy = frozen["fixture_deploy"]
    if context.get("deploy") != deploy:
        raise GateError(f"context deploy={context.get('deploy')} 与 plan deploy={deploy} 不符")
    if deploy == "candidate":
        for key, source, value in (("release_root", "release_root", frozen.get("release_root")),
                                   ("version", "release_version", frozen.get("release_version")),
                                   ("ref", "release_ref", frozen.get("release_ref"))):
            if context.get(key) != value:
                raise GateError(f"context {source}={context.get(key)!r} 与 frozen plan {value!r} 不符")
        candidate = context.get("candidate") or {}
        if not candidate.get("commit") or candidate.get("tree_digest") != context.get("tree_digest"):
            raise GateError("candidate context 缺已核 tag/commit 或树摘要不符")
    else:
        import release_lock

        try:
            release_lock.verify_lease(context["release_root"])
        except release_lock.LockError as exc:
            raise GateError(f"dev release 消费 lease 无效：{exc}") from exc
        if context["release_root"] != frozen.get("test_release_root"):
            raise GateError("context release_root 与 frozen plan 的测试发行根不符")
    return context


def main(argv=None):
    parser = argparse.ArgumentParser(description="execute 阶段门（祖先/租约/冻结字节）")
    parser.add_argument("--entry-pid", type=int, required=True)
    parser.add_argument("--plan-file", required=True)
    parser.add_argument("--plan-sha256", required=True)
    parser.add_argument("--plan-size", required=True)
    parser.add_argument("--context-file", required=True)
    parser.add_argument("--context-sha256", required=True)
    parser.add_argument("--context-size", required=True)
    args = parser.parse_args(argv)
    try:
        _verify_ancestor(args.entry_pid)
        fixture_scope.verify_lease()
        fixture_scope.verify_results_lock()
        if not fixture_scope.verify_lease():
            raise GateError("fixture lease 无效")
        frozen = _verify_plan(args.plan_file, args.plan_sha256, args.plan_size)
        if not frozen.get("test_release_root") and frozen["fixture_deploy"] == "dev":
            raise GateError("frozen plan 缺 test_release_root")
        context = _verify_context(args.context_file, args.context_sha256, args.context_size, frozen)
        root = context["release_root"]
        values = {
            "WF_FIXTURE_DEPLOY": context["deploy"],
            "WF_RELEASE_REPO": root,
            "WF_RELEASE_TREE": root,
            "SHARED_RELEASE": root,
            "WF_INSTALL_REF": context["ref"],
            "WF_TEST_LIB": os.path.join(root, "wf-release", "lib"),
            "WF_RELEASE_CONTEXT": args.context_file,
        }
        if context["deploy"] == "candidate":
            values.update({"WF_RELEASE_ROOT": root, "WF_RELEASE_REF": context["ref"],
                           "WF_RELEASE_VERSION": context["version"],
                           "WF_RELEASE_META": root + ".meta.json"})
        for key, value in values.items():
            print(f"{key}={shlex.quote(str(value))}")
        print("EXECUTE_GATE_OK=1")
        return 0
    except (GateError, fixture_scope.FixtureError, OSError, KeyError, ValueError) as exc:
        print(f"EXECUTE-GATE-FAILED: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
