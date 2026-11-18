#!/usr/bin/env python3
"""repro/run.sh 公开参数的唯一解析器，以及同代执行计划的产出/读取点。

调用方是 `repro/run.sh` 的公开入口：内部 frame 先由 `runner_protocol.py` 整体剥离，随后本
helper 只接收**用户 argv**，成功时向 stdout 输出可直接 `eval` 的 shlex 引用赋值/数组，失败
返回 2。解析发生在任何租约、layout、scope、cache、build 或 worker 之前，因此非法调用不会
产生副作用。

设计约束（父任务 design §1.1/§5）：
- 每个有值选项缺值、空值、后继选项冒充取值都确定非零；`--` 形式之外不接受 `-` 开头的值；
- 合法重复 `--group` 保留全部出现（数组），标量选项沿用最后一次取值；
- `--list` 是纯选择面，与 `--mode` 同时出现即拒绝，避免“本想只看清单却真跑一轮”；
- `--help` 只置位，usage 正文仍由 run.sh 的 heredoc 单独维护（唯一文本来源）。

除公开赋值外，本文件是独立 repro 执行计划的唯一产出点：`PLAN_B64` 随 lease frame 携带，
lease 阶段只做结构/路径校验与原子冻结（`freeze-plan`），内层只读已冻结字节（`read-plan`）。
计划里的发行字段与 full 的 `plan.py` 同名同义，身份字段由 `runner_protocol.validate_plan` 统一核验。
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import shlex
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
FULL = os.path.dirname(HERE)
REPO = os.path.abspath(os.path.join(HERE, "..", "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(REPO, "scripts"))
sys.path.insert(0, FULL)

MODES = ("green", "red", "both", "auto")
DEPLOYS = ("dev", "candidate")
JOBS_ENV = "WF_REPRO_JOBS"
DEPLOY_ENV = "WF_FIXTURE_DEPLOY"
RELEASE_ENVS = {
    "release_root": "WF_RELEASE_ROOT",
    "release_ref": "WF_RELEASE_REF",
    "release_version": "WF_RELEASE_VERSION",
    "release_meta": "WF_RELEASE_META",
}
RESULTS_ENV = "WF_REPRO_RESULTS"
PLAN_NAME = "plan.json"


class CliError(Exception):
    """可预期的参数拒绝（非零退出，不创建任何状态）。"""


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="repro/run.sh", add_help=False, allow_abbrev=False,
        description="repro/run.sh 公开参数解析 helper（成功时向 stdout 输出 shell 赋值）")
    parser.add_argument("-h", "--help", action="store_true", dest="help")
    parser.add_argument("--list", action="store_true", dest="list")
    parser.add_argument("--mode")
    parser.add_argument("--group", action="append", dest="groups")
    parser.add_argument("--only")
    parser.add_argument("--jobs")
    parser.add_argument("--fixture-deploy", dest="fixture_deploy")
    parser.add_argument("--release-root", dest="release_root")
    parser.add_argument("--release-ref", dest="release_ref")
    parser.add_argument("--release-version", dest="release_version")
    parser.add_argument("--release-meta", dest="release_meta")
    parser.add_argument("--results-dir", dest="results_dir")
    parser.add_argument("--no-build", action="store_true", dest="no_build")
    return parser


def explicit(value, name):
    """显式给出的取值：不能为空，也不能以 '-' 开头（避免选项被当成值）。"""
    if value is None:
        return None
    if value == "":
        raise CliError(f"{name} 的值不能为空")
    if value.startswith("-"):
        raise CliError(f"{name} 的值不能以 '-' 开头（选项不能冒充取值）：{value!r}")
    return value


def env_default(name):
    value = os.environ.get(name)
    return "" if value is None else value


def positive_jobs(raw):
    if not raw.isdigit() or int(raw) < 1:
        raise CliError(f"--jobs 必须是正整数（收到 {raw!r}）")
    return raw


def resolve(argv):
    """把 argv 解析成 shell 赋值序列；非法输入抛 CliError（或由 argparse 以 rc=2 退出）。"""
    args = build_parser().parse_args(list(argv))

    mode = explicit(args.mode, "--mode")
    if mode is None:
        mode = "both"
    if mode not in MODES:
        raise CliError(f"--mode 只接受 {'|'.join(MODES)}（收到 {mode!r}）")

    deploy = explicit(args.fixture_deploy, "--fixture-deploy")
    if deploy is None:
        deploy = env_default(DEPLOY_ENV) or "dev"
    if deploy not in DEPLOYS:
        raise CliError(f"--fixture-deploy 只接受 {'|'.join(DEPLOYS)}（收到 {deploy!r}）")

    jobs = explicit(args.jobs, "--jobs")
    if jobs is None:
        jobs = env_default(JOBS_ENV) or "1"
    jobs = positive_jobs(jobs)

    groups = [explicit(value, "--group") for value in (args.groups or [])]
    only = explicit(args.only, "--only") or ""
    release = {}
    for key, env_name in RELEASE_ENVS.items():
        value = explicit(getattr(args, key), f"--{key.replace('_', '-')}")
        release[key] = env_default(env_name) if value is None else value
    results = explicit(args.results_dir, "--results-dir")
    if results is None:
        results = env_default(RESULTS_ENV)

    if args.list and args.mode is not None:
        raise CliError("--list 不能与 --mode 同时使用（清单是纯选择面，不跑任何用例）")

    return [
        ("MODE", mode),
        ("GROUP_NAMES", groups),
        ("ONLY", only),
        ("JOBS", jobs),
        ("BUILD", "0" if args.no_build else "1"),
        ("DEPLOY", deploy),
        ("RELEASE_ROOT", release["release_root"]),
        ("RELEASE_REF", release["release_ref"]),
        ("RELEASE_VERSION", release["release_version"]),
        ("RELEASE_META", release["release_meta"]),
        ("RESULTS", results),
        ("LIST", "1" if args.list else "0"),
        ("HELP", "1" if args.help else "0"),
    ]


def shell_assignments(values):
    lines = []
    for name, value in values:
        if isinstance(value, list):
            lines.append(f"{name}=(" + " ".join(shlex.quote(item) for item in value) + ")")
        else:
            lines.append(f"{name}={shlex.quote(value)}")
    return "\n".join(lines) + "\n"


# ---- 执行计划（独立 repro 的唯一产出点）--------------------------------------


def _repo_plan_module():
    import importlib.util

    path = os.path.join(FULL, "plan.py")
    spec = importlib.util.spec_from_file_location("wf_repro_plan_helper", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _layout(entry_pid):
    import wf_test_paths

    try:
        return wf_test_paths.resolve_layout("repro", entry_pid, env=os.environ)
    except wf_test_paths.PathError as exc:
        raise CliError(f"scope 路径校验失败：{exc}") from exc


def _canonical(path):
    return os.path.realpath(path)


def plan_document(values, entry_pid):
    """把已解析的公开取值（CLI 优先于环境）变成规范计划对象；不写任何文件。"""
    resolved = dict(values)
    deploy = resolved["DEPLOY"]
    mode = resolved["MODE"]
    layout = _layout(entry_pid)
    plan_module = _repo_plan_module()

    results = resolved["RESULTS"] or str(layout["results_dir"])
    scope = os.environ.get("WF_TEST_SCOPE_ROOT") or None
    document = {
        "schema_version": 1,
        "role": "repro",
        "run_id": "",
        "results_dir": _canonical(results),
        "scope_root": _canonical(scope) if scope else None,
        "mode": "repro",
        "full_mode": 0,
        "fixture_deploy": deploy,
        "release_root": "",
        "release_ref": "",
        "release_version": "",
        "release_meta": "",
        "test_release_root": "",
        "test_release_version": "",
        "test_release_ref": "",
        "no_build": 0 if resolved["BUILD"] == "1" else 1,
        "repro_enabled": 1,
        "repro_mode": mode,
        "repro_groups": list(resolved["GROUP_NAMES"]),
        "only": resolved["ONLY"],
        "repro_jobs": int(resolved["JOBS"]),
        "repro_concurrent": 0,
        "repro_only": 1,
        "units": [],
        "jobs": int(resolved["JOBS"]),
    }
    if deploy == "candidate":
        root = resolved["RELEASE_ROOT"]
        ref = resolved["RELEASE_REF"]
        version = resolved["RELEASE_VERSION"]
        missing = [name for name, value in (("--release-root", root), ("--release-ref", ref),
                                            ("--release-version", version)) if not value]
        if missing:
            raise CliError("candidate 模式必须同时给出 " + " ".join(missing))
        if mode in ("red", "both"):
            raise CliError("candidate 模式只允许 --mode green|auto（red 注入针对源码，请在 dev 模式跑）")
        root = _canonical(root)
        if not os.path.isdir(root):
            raise CliError(f"--release-root 不存在：{root}")
        meta = resolved["RELEASE_META"] or os.path.join(root + ".meta.json")
        meta = _canonical(meta)
        canonical_meta = _canonical(root + ".meta.json")
        if meta != canonical_meta:
            raise CliError(
                f"候选 release-meta 必须指向 canonical sidecar：{meta} != {canonical_meta}"
                "（另一文件即使内容相同也拒绝，避免同一候选出现两份身份）")
        if not os.path.isfile(meta):
            raise CliError(f"候选 release-meta 不存在：{meta}")
        document.update({"release_root": root, "release_ref": ref,
                         "release_version": version, "release_meta": meta})
    else:
        if resolved["RELEASE_ROOT"] or resolved["RELEASE_REF"] or resolved["RELEASE_VERSION"] \
                or resolved["RELEASE_META"]:
            raise CliError("dev 模式不接受 --release-*（候选请用 --fixture-deploy candidate）")
        version = plan_module.resolve_test_release_version(env=os.environ)
        cache = os.environ.get("WF_TEST_RELEASE_CACHE") or str(layout["test_release"])
        document.update({
            "test_release_root": os.path.join(cache, version),
            "test_release_version": version,
            "test_release_ref": f"refs/tags/wf-v{version}",
        })
    return document


def plan_b64(document):
    data = json.dumps(document, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return base64.b64encode(data.encode("utf-8")).decode("ascii")


def decode_plan_b64(encoded):
    try:
        data = base64.b64decode(encoded.encode("ascii"), validate=True)
    except (ValueError, UnicodeEncodeError) as exc:
        raise CliError(f"计划对象不是合法 base64：{exc}") from exc
    try:
        document = json.loads(data)
    except ValueError as exc:
        raise CliError(f"计划对象不是 JSON：{exc}") from exc
    if not isinstance(document, dict):
        raise CliError("计划对象必须是 JSON 对象")
    return document


PLAN_ASSIGNMENTS = (
    ("PLAN_ROLE", "role"),
    ("PLAN_RUN_ID", "run_id"),
    ("PLAN_RESULTS_DIR", "results_dir"),
    ("PLAN_SCOPE_ROOT", "scope_root"),
    ("PLAN_MODE", "mode"),
    ("PLAN_FULL_MODE", "full_mode"),
    ("PLAN_DEPLOY", "fixture_deploy"),
    ("PLAN_RELEASE_ROOT", "release_root"),
    ("PLAN_RELEASE_REF", "release_ref"),
    ("PLAN_RELEASE_VERSION", "release_version"),
    ("PLAN_RELEASE_META", "release_meta"),
    ("PLAN_TEST_RELEASE_ROOT", "test_release_root"),
    ("PLAN_TEST_RELEASE_VERSION", "test_release_version"),
    ("PLAN_TEST_RELEASE_REF", "test_release_ref"),
    ("PLAN_NO_BUILD", "no_build"),
    ("PLAN_REPRO_ENABLED", "repro_enabled"),
    ("PLAN_REPRO_MODE", "repro_mode"),
    ("PLAN_REPRO_ONLY", "repro_only"),
    ("PLAN_ONLY", "only"),
)


def plan_assignments(document):
    lines = []
    for name, key in PLAN_ASSIGNMENTS:
        value = document.get(key)
        lines.append(f"{name}=" + shlex.quote("" if value is None else str(value)))
    groups = document.get("repro_groups") or []
    lines.append("PLAN_REPRO_GROUPS=(" + " ".join(shlex.quote(str(item)) for item in groups) + ")")
    lines.append("PLAN_REPRO_JOBS=" + shlex.quote(str(document.get("repro_jobs") or "")))
    return "\n".join(lines) + "\n"


def _validate_plan(document, *, role, run_id, results_dir, scope_root):
    sys.path.insert(0, FULL)
    import runner_protocol

    try:
        runner_protocol.validate_plan(document, role=role, run_id=run_id,
                                      results_dir=results_dir, scope_root=scope_root)
    except runner_protocol.FrameError as exc:
        raise CliError(f"执行计划身份不符：{exc}") from exc


def _read_plan_bytes(path, expected_sha, expected_size):
    sys.path.insert(0, FULL)
    import runner_protocol

    if not os.path.isfile(path) or os.path.islink(path):
        raise CliError(f"冻结计划不是普通文件：{path}")
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        data = os.read(fd, 1 << 20)
        if os.read(fd, 1):
            raise CliError(f"冻结计划过大：{path}")
    finally:
        os.close(fd)
    if expected_size and str(len(data)) != str(expected_size):
        raise CliError(f"冻结计划长度不符：{len(data)} != {expected_size}")
    if expected_sha and hashlib.sha256(data).hexdigest() != expected_sha:
        raise CliError("冻结计划摘要与内部 token 不符（被替换/篡改）")
    try:
        document = json.loads(data)
    except ValueError as exc:
        raise CliError(f"冻结计划不是 JSON：{exc}") from exc
    if not isinstance(document, dict):
        raise CliError("冻结计划必须是 JSON 对象")
    return data, document


def _atomic_write(path, text):
    import tempfile

    directory = os.path.dirname(path) or "."
    os.makedirs(directory, exist_ok=True)
    if os.path.islink(path):
        raise CliError(f"计划路径不得是符号链接：{path}")
    handle = tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=directory,
                                         prefix=".plan-", delete=False, suffix=".json")
    try:
        handle.write(text)
        handle.flush()
        os.fsync(handle.fileno())
    finally:
        handle.close()
    os.replace(handle.name, path)


def freeze_plan(document, results_dir, run_id):
    """lease 阶段：核对象结构/路径后，把同一对象（补 run_id）原子冻结到结果根。"""
    results_dir = _canonical(results_dir)
    document = dict(document)
    document["run_id"] = run_id
    document["results_dir"] = results_dir
    if document.get("scope_root"):
        document["scope_root"] = _canonical(document["scope_root"])
    _validate_plan(document, role="repro", run_id=run_id, results_dir=results_dir,
                   scope_root=document.get("scope_root"))
    text = json.dumps(document, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    path = os.path.join(results_dir, PLAN_NAME)
    _atomic_write(path, text)
    data, frozen = _read_plan_bytes(path, None, None)
    if frozen != document:
        raise CliError("冻结计划读回与写入对象不一致")
    return path, hashlib.sha256(data).hexdigest(), len(data)


def read_plan(path, expected_sha, expected_size, run_id, results_dir, scope_root,
              role="repro"):
    data, document = _read_plan_bytes(path, expected_sha, expected_size)
    _validate_plan(document, role=role, run_id=run_id, results_dir=results_dir,
                   scope_root=scope_root)
    if document.get("role") != role:
        raise CliError(f"冻结计划 role={document.get('role')!r} 与本次 {role!r} 不符")
    return document, hashlib.sha256(data).hexdigest(), len(data)


def _split_command(argv):
    argv = list(argv)
    if argv and argv[0] == "--":
        return argv[1:]
    return argv


def main(argv=None):
    argv = _split_command(sys.argv[1:] if argv is None else argv)
    if argv and argv[0] == "freeze-plan":
        parser = argparse.ArgumentParser(prog="repro/cli.py freeze-plan")
        parser.add_argument("--plan-b64", required=True)
        parser.add_argument("--results-root", required=True)
        parser.add_argument("--run-id", required=True)
        args = parser.parse_args(argv[1:])
        try:
            path, sha, size = freeze_plan(decode_plan_b64(args.plan_b64),
                                          args.results_root, args.run_id)
        except (CliError, OSError, ValueError) as exc:
            print(f"repro: {exc}", file=sys.stderr)
            return 2
        print("PLAN_FILE=" + shlex.quote(path))
        print("PLAN_SHA256=" + sha)
        print("PLAN_SIZE=" + str(size))
        return 0
    if argv and argv[0] == "plan-fields":
        parser = argparse.ArgumentParser(prog="repro/cli.py plan-fields")
        parser.add_argument("--plan-b64", required=True)
        args = parser.parse_args(argv[1:])
        try:
            document = decode_plan_b64(args.plan_b64)
            results = document.get("results_dir")
            scope = document.get("scope_root")
            if document.get("role") != "repro" or document.get("schema_version") != 1:
                raise CliError("计划对象不是独立 repro 计划")
            if not isinstance(results, str) or not os.path.isabs(results):
                raise CliError(f"计划 results_dir 非法：{results!r}")
            if scope is not None and (not isinstance(scope, str) or not os.path.isabs(scope)):
                raise CliError(f"计划 scope_root 非法：{scope!r}")
            if document.get("repro_mode") not in ("green", "red", "both", "auto"):
                raise CliError(f"计划 repro_mode 非法：{document.get('repro_mode')!r}")
        except (CliError, OSError, ValueError) as exc:
            print(f"repro: {exc}", file=sys.stderr)
            return 2
        print("PLAN_RESULTS_DIR=" + shlex.quote(results))
        print("PLAN_SCOPE_ROOT=" + shlex.quote(scope or ""))
        print("PLAN_DEPLOY=" + shlex.quote(str(document.get("fixture_deploy") or "")))
        print("PLAN_REPRO_MODE=" + shlex.quote(str(document.get("repro_mode") or "")))
        return 0
    if argv and argv[0] == "read-plan":
        parser = argparse.ArgumentParser(prog="repro/cli.py read-plan")
        parser.add_argument("--plan-file", required=True)
        parser.add_argument("--plan-sha256", default=None)
        parser.add_argument("--plan-size", default=None)
        parser.add_argument("--run-id", required=True)
        parser.add_argument("--results-root", required=True)
        parser.add_argument("--scope-root", default="-")
        parser.add_argument("--role", default="auto")
        args = parser.parse_args(argv[1:])
        scope = None if args.scope_root in ("-", "") else args.scope_root
        try:
            role = args.role
            if role == "auto":
                _data, peek = _read_plan_bytes(args.plan_file, args.plan_sha256, args.plan_size)
                role = peek.get("role")
                if role not in ("repro", "full"):
                    raise CliError(f"冻结计划 role 非法：{role!r}")
            document, _sha, _size = read_plan(args.plan_file, args.plan_sha256,
                                              args.plan_size, args.run_id,
                                              args.results_root, scope, role=role)
        except (CliError, OSError, ValueError) as exc:
            print(f"repro: {exc}", file=sys.stderr)
            return 2
        sys.stdout.write(plan_assignments(document))
        return 0
    try:
        values = resolve(argv)
        resolved = dict(values)
        if resolved["HELP"] == "0" and resolved["LIST"] == "0":
            values = values + [("PLAN_B64", plan_b64(plan_document(resolved, _entry_pid())))]
    except CliError as exc:
        print(f"repro: {exc}", file=sys.stderr)
        return 2
    sys.stdout.write(shell_assignments(values))
    return 0


def _entry_pid():
    """公开入口 PID：run.sh 是本进程的父进程，且随后以同一 PID 走 lease/controller 链。"""
    return os.getppid()


if __name__ == "__main__":
    raise SystemExit(main())