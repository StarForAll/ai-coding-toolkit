#!/usr/bin/env python3
"""release_context.py — root controller 的发行准备与 release-context 交接 helper。

位置变化（父任务 design §1.1/§2）：发行消费锁现在由 root controller（`execution.py
--runner-control`）自己取得并贯穿整次运行；准备命令（dev 的 `wf_test_release.py
--ensure/--check --no-lock`、候选的只读 validator）也由 controller 通过同一监督器各调用一次。
本模块只保留**纯 helper**：

1. `build_context`：把已核验的发行身份组装成 schema2 上下文（候选含已核 tag commit 与树摘要）；
2. `write_context_atomic`：在结果根原子写 `release-context.json`（计划摘要/长度一并绑定）；
3. `release_env`：把上下文投影成子进程消费的定位变量（shell 只消费，不重新推导）。

旧的“在受监督子链里再次取锁/再次 exec”路径已删除：锁与准备都只在 controller 一处发生。
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
import tempfile
import time
from pathlib import Path

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(REPO, "scripts"))
sys.path.insert(0, HERE)

import fixture_scope  # noqa: E402  （context helper 仍按 scope 边界拒绝域外路径）

PY = os.environ.get("PY") or sys.executable
CONTEXT_SCHEMA = 2
CONTEXT_NAME = "release-context.json"


class ContextError(Exception):
    pass


def _common():
    sys.path.insert(0, os.path.join(REPO, "scripts"))
    import wf_release_common as common

    return common


def _identity_projection(resolved):
    """完整运行身份的对外投影：只留摘要与 role/version 诊断，不转存路径/环境值。"""
    return {"role": resolved["role"],
            "path_identity": resolved["path_identity"],
            "binary_digest": resolved["binary"]["digest"],
            "invocation_digest": resolved["invocation_file"]["digest"],
            "implementation": resolved["implementation"],
            "version": resolved["version"]}


def runtime_identity():
    """tool/SUT 完整身份；解析不出即失败（不签发空身份）。"""
    sys.path.insert(0, os.path.join(REPO, "scripts"))
    try:
        import python_runtime_identity as identity
    except ImportError as exc:
        raise ContextError(f"runtime identity helper is unavailable: {exc}") from exc
    resolver = identity.Resolver()
    try:
        return {"tool": _identity_projection(
                    resolver.resolve("tool", os.path.join(HERE, "run_all.sh"))),
                "sut": _identity_projection(
                    resolver.resolve("sut", os.path.join(HERE, "f1_init.py")))}
    except identity.IdentityError as exc:
        raise ContextError(f"runtime identity is unresolved: {exc}") from exc


def write_context_atomic(path, payload):
    directory = os.path.dirname(path)
    handle = tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=directory, prefix=".ctx-",
                                         delete=False)
    try:
        json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    finally:
        handle.close()
    os.replace(handle.name, path)
    data = Path(path).read_bytes()
    return hashlib.sha256(data).hexdigest(), len(data)


def build_context(*, deploy, root, ref, version, candidate, release_build, plan_sha256,
                  plan_size, results_dir):
    """组装 schema2 上下文（不落盘）；候选身份缺 commit/树摘要时直接拒绝。"""
    if deploy not in ("dev", "candidate"):
        raise ContextError(f"unknown deploy: {deploy!r}")
    common = _common()
    subject = None
    manifest_digest = None
    tree_digest = None
    try:
        subject = common.release_subject(root, version, ref)["digest"]
        manifest_digest = common.manifest_digest(
            json.loads(Path(root, "wf-release.json").read_text()))
        tree_digest = common.tree_digest(root)
    except (OSError, ValueError, AttributeError):
        try:
            tree_digest = common.tree_digest(root)
        except Exception:
            pass
    if deploy == "candidate":
        if not isinstance(candidate, dict) or not candidate.get("commit"):
            raise ContextError("candidate context requires the verified tag commit")
        if candidate.get("tree_digest") != tree_digest:
            raise ContextError("candidate tree digest differs from the verified tree")
    context = {
        "schema_version": CONTEXT_SCHEMA,
        "deploy": deploy,
        "release_root": os.path.realpath(root),
        "version": version,
        "ref": ref,
        "release_subject": subject,
        "manifest_digest": manifest_digest,
        "tree_digest": tree_digest,
        "runtime": runtime_identity(),
        "candidate": candidate,
        # 成本账目：本次是 built/reused/checked——summary 只搬运不改判。
        "release_build": release_build,
        "plan_sha256": plan_sha256,
        "plan_size": int(plan_size),
        "results_dir": os.path.realpath(results_dir),
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    return context


def release_env(context):
    """上下文 → 子进程定位变量（execute 与内嵌 repro 都消费同一批值）。"""
    root = context["release_root"]
    values = {
        "WF_FIXTURE_DEPLOY": context["deploy"],
        "WF_RELEASE_REPO": root,
        "WF_RELEASE_TREE": root,
        "SHARED_RELEASE": root,
        "WF_INSTALL_REF": context["ref"],
        "WF_TEST_LIB": os.path.join(root, "wf-release", "lib"),
        "WF_RELEASE_CONTEXT": os.path.join(context["results_dir"], CONTEXT_NAME),
        "WF_BUILD_SECONDS": os.environ.get("WF_BUILD_SECONDS", "0"),
    }
    if context["deploy"] == "candidate":
        values.update({"WF_RELEASE_ROOT": root, "WF_RELEASE_REF": context["ref"],
                       "WF_RELEASE_VERSION": context["version"],
                       "WF_RELEASE_META": root + ".meta.json",
                       "WF_RELEASE_COMMIT": (context.get("candidate") or {}).get("commit") or ""})
    return values


def require_scope_path(path):
    """结果根下的 context 路径必须仍在 owned scope 内（域外写前拒绝）。"""
    try:
        fixture_scope.ensure_in_scope(Path(path))
    except fixture_scope.FixtureError as exc:
        raise ContextError(str(exc)) from exc


def main(argv=None):
    print("release_context.build_context is the controller helper; "
          "there is no separate preparation entry point", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())