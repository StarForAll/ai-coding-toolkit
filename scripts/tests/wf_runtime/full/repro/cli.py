#!/usr/bin/env python3
"""repro/run.sh 公开参数的唯一解析器。

调用方是 `repro/run.sh` 的公开入口：内部 frame 先由 `runner_protocol.py` 整体剥离，随后本
helper 只接收**用户 argv**，成功时向 stdout 输出可直接 `eval` 的 shlex 引用赋值/数组，失败
返回 2。解析发生在任何租约、layout、scope、cache、build 或 worker 之前，因此非法调用不会
产生副作用。

设计约束（父任务 design §6）：
- 每个有值选项缺值、空值、后继选项冒充取值都确定非零；`--` 形式之外不接受 `-` 开头的值；
- 合法重复 `--group` 保留全部出现（数组），标量选项沿用最后一次取值；
- `--list` 是纯选择面，与 `--mode` 同时出现即拒绝，避免“本想只看清单却真跑一轮”；
- `--help` 只置位，usage 正文仍由 run.sh 的 heredoc 单独维护（唯一文本来源）。

直接运行本文件（无 shell 包裹）时同样输出 shell 赋值，供调试/单测使用。
"""
from __future__ import annotations

import argparse
import os
import shlex
import sys

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


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    try:
        values = resolve(argv)
    except CliError as exc:
        print(f"repro: {exc}", file=sys.stderr)
        return 2
    sys.stdout.write(shell_assignments(values))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
