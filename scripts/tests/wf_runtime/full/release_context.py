#!/usr/bin/env python3
"""release_context.py — 受控阶段的发行准备：持锁核验/构建 → 写 release-context.json → exec execute。

位置：`public → lease → controlled → execute` 里的 **controlled** 阶段（controller 监督下的 B）。
本进程在同一 PID 取得并保持 dev 的 release 独占 lock FD，完成发行 ensure/核验；candidate 不取
dev flock，改用完整 `prepare_candidate_repo.check()` 语义。随后：

1. 在主 results 目录原子写 `release-context.json`（assets 身份唯一来源，**不放进**内层 repro 结果目录）；
2. 把 context 的路径/sha256/长度写进内部 execute frame，exec `run_all.sh`（不再 release/plan）；
3. 宿主内嵌 repro 用同一文件与 `_wf-inherited-release` frame 交接，不需要再次 ensure/check。

内部字段只是定位信息；execute 与内嵌入口仍核验真实 fixture/result（dev 再加 release）锁、mount 域
与 context 摘要。任何缺失/冲突/校验失败一律拒绝，不回退独立 ensure。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(REPO, "scripts"))
sys.path.insert(0, HERE)

import fixture_scope  # noqa: E402
import runner_protocol  # noqa: E402

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


def _runtime_identity():
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


def ancestor_verified(pid, entry_pid):
    if pid <= 0:
        raise ContextError(f"--entry-pid 非法：{pid}")
    current = os.getpid()
    while current not in (pid, 0, 1):
        with open(f"/proc/{current}/status", encoding="utf-8") as stream:
            status = stream.read()
        current = int(next(line.split()[1] for line in status.splitlines() if line.startswith("PPid:")))
    if current != pid:
        raise ContextError("入口 PID 不是本进程的祖先（frame 被伪造）")
    if pid != entry_pid:
        raise ContextError("frame entry-pid 与当前祖先链不符")


def test_release_cli():
    """测试专用注入点：默认取仓库内真实 CLI；契约测试指向计数 shim（不劫持 PATH）。"""
    return os.environ.get("WF_TEST_RELEASE_CLI") or os.path.join(
        REPO, "scripts", "tests", "wf_test_release.py")


def candidate_validator():
    return os.environ.get("WF_CANDIDATE_VALIDATOR") or os.path.join(
        HERE, "prepare_candidate_repo.py")


def dev_prepare(root, ref, version, rebuild):
    # 本进程已持同一把 root 锁：CLI 加 --no-lock，内部 locked 实现不自撞。
    command = [PY, test_release_cli(), "--ensure" if rebuild else "--check", "--no-lock",
               "--root", root, "--version", version, "--json"]
    completed = subprocess.run(command, capture_output=True, text=True)
    if completed.returncode == 75:
        raise ContextError(f"release busy: {completed.stderr.strip()}")
    if completed.returncode != 0:
        label = "TEST-RELEASE-STALE" if "--check" in command else "TEST-RELEASE-BUILD-FAILED"
        raise ContextError(f"{label}: {completed.stderr.strip() or completed.stdout.strip()}")
    try:
        status = json.loads(completed.stdout).get("status")
    except ValueError as exc:
        raise ContextError("release CLI returned non-JSON status") from exc
    if status not in ("built", "reused", "checked"):
        raise ContextError(f"release CLI returned unknown status: {status!r}")
    return root, ref, version, None, status


def candidate_prepare(root, ref, version):
    completed = subprocess.run([PY, candidate_validator(), "--check", "--out", root,
                                "--version", version, "--json"], capture_output=True, text=True)
    if completed.returncode != 0:
        raise ContextError(f"CANDIDATE-REPO-INVALID: "
                           f"{completed.stderr.strip() or completed.stdout.strip()}")
    try:
        meta = json.loads(completed.stdout)
    except ValueError as exc:
        raise ContextError("candidate validator returned non-JSON") from exc
    meta_path = root + ".meta.json"
    meta_digest = None
    try:
        meta_digest = "sha256:" + hashlib.sha256(Path(meta_path).read_bytes()).hexdigest()
    except OSError:
        pass
    return root, ref, version, {"commit": meta.get("commit"), "tree_digest": meta.get("tree_digest"),
                                "meta_digest": meta_digest}, "checked"


def main(argv=None):
    parser = argparse.ArgumentParser(description="受控阶段：发行准备与 release-context 交接")
    parser.add_argument("--deploy", choices=("dev", "candidate"), required=True)
    parser.add_argument("--results-dir", required=True)
    parser.add_argument("--entry-pid", type=int, required=True)
    parser.add_argument("--results-root", required=True)
    parser.add_argument("--results-explicit", required=True)
    parser.add_argument("--scope-root", required=True)
    parser.add_argument("--plan-file", required=True)
    parser.add_argument("--plan-sha256", required=True)
    parser.add_argument("--plan-size", required=True)
    parser.add_argument("--release-root", default=None)
    parser.add_argument("--release-ref", default=None)
    parser.add_argument("--release-version", default=None)
    parser.add_argument("--no-build", action="store_true")
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args(argv)
    command = args.command[1:] if args.command[:1] == ["--"] else args.command
    try:
        ancestor_verified(args.entry_pid, args.entry_pid)
        fixture_scope.verify_lease()
        fixture_scope.verify_results_lock()
        if not args.release_root or not args.release_ref or not args.release_version:
            raise ContextError("controlled 阶段缺 release 身份参数")
        lock_fd = None
        started = time.monotonic()
        if args.deploy == "dev":
            import release_lock

            try:
                lock_fd = release_lock.acquire(args.release_root, exclusive=True)
            except release_lock.Busy as exc:
                raise ContextError(str(exc)) from exc
            release_lock.write_env(lock_fd, args.release_root)
            os.set_inheritable(lock_fd, True)
            root, ref, version, candidate, release_build = dev_prepare(
                args.release_root, args.release_ref, args.release_version, not args.no_build)
        else:
            root, ref, version, candidate, release_build = candidate_prepare(
                args.release_root, args.release_ref, args.release_version)
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
        try:
            runtime = _runtime_identity()
        except ContextError:
            raise
        context = {
            "schema_version": CONTEXT_SCHEMA,
            "deploy": args.deploy,
            "release_root": os.path.realpath(root),
            "version": version,
            "ref": ref,
            "release_subject": subject,
            "manifest_digest": manifest_digest,
            "tree_digest": tree_digest,
            "runtime": runtime,
            "candidate": candidate,
            # 成本账目（design §3.3）：本次是 built/reused/checked——summary 只搬运不改判。
            "release_build": release_build,
            "plan_sha256": args.plan_sha256,
            "plan_size": int(args.plan_size),
            "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }
        context_path = os.path.join(args.results_dir, CONTEXT_NAME)
        digest, size = write_context_atomic(context_path, context)
        # 发行来源 env：execute 与 unit 都消费同一批 locator（dev/candidate 都指向已核树）。
        os.environ.update({
            "WF_FIXTURE_DEPLOY": args.deploy,
            "WF_RELEASE_REPO": root,
            "WF_RELEASE_TREE": root,
            "SHARED_RELEASE": root,
            "WF_INSTALL_REF": ref,
            "WF_TEST_LIB": os.path.join(root, "wf-release", "lib"),
        })
        if args.deploy == "candidate":
            os.environ.update({"WF_RELEASE_ROOT": root, "WF_RELEASE_REF": ref,
                               "WF_RELEASE_VERSION": version,
                               "WF_RELEASE_META": root + ".meta.json"})
        os.environ["WF_RELEASE_CONTEXT"] = context_path
        os.environ["WF_BUILD_SECONDS"] = str(int(time.monotonic() - started))
        frame = runner_protocol.encode("execute", {
            "--entry-pid": str(args.entry_pid),
            "--results-root": args.results_root,
            "--results-explicit": args.results_explicit,
            "--scope-root": args.scope_root,
            "--plan-file": args.plan_file,
            "--plan-sha256": args.plan_sha256,
            "--plan-size": args.plan_size,
            "--context-file": context_path,
            "--context-sha256": digest,
            "--context-size": str(size),
        }, command)
        run_all = os.path.join(HERE, "run_all.sh")
        os.execvp("bash", ["bash", run_all, *frame])
    except (ContextError, fixture_scope.FixtureError, OSError, ValueError) as exc:
        # 两类通道都写：controller 继承控制台输出，契约测试读 stdout。
        print(f"CONTROLLED-FAILED: {exc}")
        print(f"CONTROLLED-FAILED: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
