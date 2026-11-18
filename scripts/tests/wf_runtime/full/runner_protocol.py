#!/usr/bin/env python3
"""runner_protocol.py — `run_all.sh` 内部阶段 frame 的唯一 encoder/decoder。

语法（只识别最前面的一个 frame，其余都是**原始用户参数**）：

```text
bash run_all.sh --_wf-internal <lease|execute> [该阶段固定键值对] -- <原始用户参数...>
bash repro/run.sh --_wf-repro-lease --entry-pid <pid> --plan-b64 <base64> --
bash repro/run.sh --_wf-repro-inner <plan/context 固定键值对> --
```

规则（design §4.1 / AC16）：
- 内部 frame 必须先整体剥离并校验（stage、固定键、类型、重复/未知键、必需 `--` 分隔符），
  校验完成才轮到用户 argv；内部键不会漏进 `plan.parse_args()` 或 repro 公开解析器；
- 用户 argv 中的保留 `--_wf-*` 选项一律拒绝（不静默穿透）；
- 只用 argv 数组传递，不 eval 拼接；`--` 之后的用户参数原样保留（含空格/中文）；
- 内部字段只是定位信息，不是授权：每次入口仍验证祖先与真实持锁 FD。

CLI：
    runner_protocol.py encode --stage lease --entry-pid 123 ... -- user-args...
    runner_protocol.py strip -- user-args...            （普通 run_all 入口）
    runner_protocol.py encode-repro --stage repro-lease --entry-pid 123 --plan-b64 ... --
    runner_protocol.py encode-repro --stage repro-inner <plan/context 字段...> --
    runner_protocol.py strip-repro -- repro 内部 frame   （repro 内部阶段）
`strip*` 输出可 eval 的 shell 赋值（USER_ARGV 数组 + WF_STAGE/字段）；非法返回 2。
"""
from __future__ import annotations

import argparse
import os
import re
import shlex
import sys

INTERNAL = "--_wf-internal"
RESERVED_PREFIX = "--_wf-"
STAGES = ("lease", "execute")
SHA256 = re.compile(r"^[0-9a-f]{64}$")
BASE64 = re.compile(r"^[A-Za-z0-9+/]+={0,2}$")
STAGE_FIELDS = {
    "lease": ("--entry-pid", "--results-root", "--results-explicit", "--scope-root"),
    "execute": ("--entry-pid", "--results-root", "--results-explicit", "--scope-root",
                "--plan-file", "--plan-sha256", "--plan-size",
                "--context-file", "--context-sha256", "--context-size"),
}
# repro 入口的两种内部 frame：lease（公开参数已解析成规范计划对象，随 frame 冻结）与
# inner（只消费已冻结的 plan/context token）。两者都禁止携带用户 argv。
REPRO_MARKERS = {"--_wf-repro-lease": "repro-lease", "--_wf-repro-inner": "repro-inner"}
REPRO_FIELDS = {
    "repro-lease": ("--entry-pid", "--plan-b64"),
    "repro-inner": ("--entry-pid", "--results-root", "--results-explicit", "--scope-root",
                    "--plan-file", "--plan-sha256", "--plan-size",
                    "--context-file", "--context-sha256", "--context-size"),
}
ENV_NAMES = {
    "--entry-pid": "WF_FRAME_ENTRY_PID",
    "--results-root": "WF_FRAME_RESULTS_ROOT",
    "--results-explicit": "WF_FRAME_RESULTS_EXPLICIT",
    "--scope-root": "WF_FRAME_SCOPE_ROOT",
    "--plan-file": "WF_FRAME_PLAN_FILE",
    "--plan-sha256": "WF_FRAME_PLAN_SHA256",
    "--plan-size": "WF_FRAME_PLAN_SIZE",
    "--context-file": "WF_FRAME_CONTEXT_FILE",
    "--context-sha256": "WF_FRAME_CONTEXT_SHA256",
    "--context-size": "WF_FRAME_CONTEXT_SIZE",
    "--plan-b64": "WF_FRAME_PLAN_B64",
}

# 执行计划 schema：full（plan.py）与独立 repro（repro/cli.py）产出的同一代冻结对象。
# 字段分布不同，但身份字段（role/run_id/results_dir/scope_root）与发行字段同名同义。
PLAN_SCHEMA = 1
PLAN_MODES_FULL = ("full", "subset", "representative")
PLAN_MODES_REPRO = ("green", "red", "both", "auto")
PLAN_DEPLOYS = ("dev", "candidate")


class FrameError(Exception):
    """非法 frame（非零退出，不 fallback）。"""


def _positive_int(value, name):
    if not re.fullmatch(r"[1-9][0-9]*", str(value)):
        raise FrameError(f"{name} 必须是正整数：{value!r}")


def _absolute(value, name, allow_dash=False):
    if allow_dash and value == "-":
        return
    if not value.startswith(os.sep):
        raise FrameError(f"{name} 必须是规范绝对路径：{value!r}")
    if os.path.normpath(value) != value:
        raise FrameError(f"{name} 必须是规范路径（无 ./ 或重复分隔符）：{value!r}")


def _validate(name, value):
    if name == "--entry-pid" or name.endswith("-size"):
        _positive_int(value, name)
    elif name == "--results-explicit":
        if value not in ("0", "1"):
            raise FrameError(f"--results-explicit 只接受 0/1：{value!r}")
    elif name == "--scope-root":
        _absolute(value, name, allow_dash=True)
    elif name.endswith("-sha256"):
        if not SHA256.fullmatch(value):
            raise FrameError(f"{name} 必须是 64 位小写 hex：{value!r}")
    elif name == "--plan-b64":
        if not BASE64.fullmatch(value):
            raise FrameError(f"{name} 必须是单行 base64：{value[:32]!r}...")
    else:
        _absolute(value, name)


def _split(argv):
    if "--" in argv:
        index = argv.index("--")
        return argv[:index], argv[index + 1:]
    return argv, []


def _reject_reserved(user_argv):
    for item in user_argv:
        if item.startswith(RESERVED_PREFIX):
            raise FrameError(f"用户参数不能带保留选项 {item}（内部 frame 只能由入口生成）")


def decode(argv):
    """解析 run_all 内部 frame；没有 frame 时返回 (None, {}, argv)。"""
    argv = list(argv)
    if not argv or argv[0] != INTERNAL:
        _reject_reserved(argv)
        return None, {}, argv
    head, user = _split(argv[1:])
    if not head:
        raise FrameError("内部 frame 缺 stage")
    stage = head[0]
    if stage not in STAGES:
        raise FrameError(f"未知内部 stage：{stage!r}（可选 {'|'.join(STAGES)}）")
    _validate_fields(head[1:], STAGE_FIELDS[stage], required=STAGE_FIELDS[stage])
    fields = dict(zip(head[1::2], head[2::2]))
    _reject_reserved(user)
    return stage, fields, user


def decode_repro(argv):
    """解析 repro 内部 frame；公开入口（无 frame）返回 (None, {}, argv)。

    内部 frame 不接受用户 argv：内层只消费已冻结的 plan/context，公开参数只在入口解析一次。
    """
    argv = list(argv)
    stage = REPRO_MARKERS.get(argv[0]) if argv else None
    if stage is None:
        _reject_reserved(argv)
        return None, {}, argv
    head, user = _split(argv[1:])
    if user:
        raise FrameError("repro 内部 frame 不接受用户参数（计划已在入口解析并冻结）")
    _validate_fields(head, REPRO_FIELDS[stage], required=REPRO_FIELDS[stage])
    return stage, dict(zip(head[0::2], head[1::2])), []


def _validate_fields(parts, allowed, required=()):
    names = parts[0::2]
    if len(parts) % 2:
        raise FrameError("内部字段结构错位（键值必须成对）")
    seen = set()
    for name in names:
        if name not in allowed:
            raise FrameError(f"未知/不属于该阶段的字段：{name}")
        if name in seen:
            raise FrameError(f"重复字段：{name}")
        seen.add(name)
    missing = [name for name in required if name not in seen]
    if missing:
        raise FrameError("缺必需字段：" + " ".join(missing))
    for name, value in zip(parts[0::2], parts[1::2]):
        if value == "" or value.startswith("--"):
            raise FrameError(f"{name} 的值非法（空或像选项）：{value!r}")
        _validate(name, value)


def encode(stage, fields, user_argv):
    """按固定字段顺序组装 argv（由 encoder 唯一决定顺序与格式）。"""
    if stage not in STAGES:
        raise FrameError(f"未知 stage：{stage!r}")
    return _encode_fields(STAGE_FIELDS[stage], [INTERNAL, stage], fields, user_argv)


def encode_repro(stage, fields):
    if stage not in REPRO_FIELDS:
        raise FrameError(f"未知 repro stage：{stage!r}")
    marker = next(name for name, value in REPRO_MARKERS.items() if value == stage)
    return _encode_fields(REPRO_FIELDS[stage], [marker], fields, [])


def _encode_fields(order, prefix, fields, user_argv):
    unknown = set(fields) - set(order)
    if unknown:
        raise FrameError("stage 不接受字段：" + " ".join(sorted(unknown)))
    argv = list(prefix)
    for name in order:
        if name not in fields:
            raise FrameError(f"缺字段：{name}")
        _validate(name, fields[name])
        argv += [name, fields[name]]
    return argv + ["--", *user_argv]


def validate_plan(plan, *, role, run_id, results_dir, scope_root):
    """核冻结执行计划的身份与发行字段（full 与独立 repro 两条产出链共用同一份规则）。"""
    if not isinstance(plan, dict):
        raise FrameError("冻结计划必须是 JSON 对象")
    if plan.get("schema_version") != PLAN_SCHEMA or isinstance(plan.get("schema_version"), bool):
        raise FrameError(f"冻结计划 schema 必须是 {PLAN_SCHEMA}：{plan.get('schema_version')!r}")
    if plan.get("role") != role:
        raise FrameError(f"冻结计划 role={plan.get('role')!r} 与本次 {role!r} 不符")
    if not isinstance(run_id, str) or not run_id or plan.get("run_id") != run_id:
        raise FrameError("冻结计划 run_id 与本次运行不符")
    planned_root = plan.get("results_dir")
    if not isinstance(planned_root, str) or not os.path.isabs(planned_root) \
            or planned_root != os.path.normpath(planned_root):
        raise FrameError(f"冻结计划 results_dir 必须是规范绝对路径：{planned_root!r}")
    if os.path.realpath(planned_root) != os.path.realpath(results_dir):
        raise FrameError("冻结计划 results_dir 与本次运行结果根不符")
    planned_scope = plan.get("scope_root")
    if planned_scope is not None:
        if not isinstance(planned_scope, str) or not os.path.isabs(planned_scope) \
                or planned_scope != os.path.normpath(planned_scope):
            raise FrameError(f"冻结计划 scope_root 非法：{planned_scope!r}")
    expected_scope = os.path.realpath(scope_root) if scope_root else None
    if (os.path.realpath(planned_scope) if planned_scope else None) != expected_scope:
        raise FrameError("冻结计划 scope_root 与本次运行的 scope 不符")
    deploy = plan.get("fixture_deploy")
    if deploy not in PLAN_DEPLOYS:
        raise FrameError(f"冻结计划 fixture_deploy 非法：{deploy!r}")
    if plan.get("no_build") not in (0, 1) or isinstance(plan.get("no_build"), bool):
        raise FrameError("冻结计划 no_build 必须是 0/1")
    if role == "full":
        if plan.get("mode") not in PLAN_MODES_FULL:
            raise FrameError(f"冻结计划 mode 非法：{plan.get('mode')!r}")
        units = plan.get("units")
        if not isinstance(units, list) or not units:
            raise FrameError("冻结计划没有执行单元")
        for unit in units:
            if not isinstance(unit, dict) or not isinstance(unit.get("name"), str) \
                    or not unit["name"]:
                raise FrameError("冻结计划的执行单元格式非法")
    else:
        if plan.get("mode") != "repro" or plan.get("full_mode") != 0:
            raise FrameError("独立 repro 的冻结计划必须是 mode=repro/full_mode=0")
        if plan.get("units") != []:
            raise FrameError("独立 repro 的冻结计划不能携带执行单元")
        if plan.get("repro_only") != 1:
            raise FrameError("独立 repro 的冻结计划必须标记 repro_only=1")
        if plan.get("repro_enabled") != 1:
            raise FrameError("独立 repro 的冻结计划必须启用 repro")
        if plan.get("repro_mode") not in PLAN_MODES_REPRO:
            raise FrameError(f"冻结计划 repro_mode 非法：{plan.get('repro_mode')!r}")
        groups = plan.get("repro_groups")
        if not isinstance(groups, list) or any(not isinstance(item, str) for item in groups):
            raise FrameError("冻结计划 repro_groups 必须是字符串数组")
        if not isinstance(plan.get("only"), str):
            raise FrameError("冻结计划 only 必须是字符串（无过滤时为空串）")
        jobs = plan.get("repro_jobs")
        if not isinstance(jobs, int) or isinstance(jobs, bool) or jobs < 1:
            raise FrameError("冻结计划 repro_jobs 必须是正整数")
    if deploy == "candidate":
        root = plan.get("release_root")
        if not isinstance(root, str) or not os.path.isabs(root):
            raise FrameError(f"候选冻结计划 release_root 非法：{root!r}")
        for key in ("release_ref", "release_version"):
            if not isinstance(plan.get(key), str) or not plan[key]:
                raise FrameError(f"候选冻结计划缺 {key}")
        meta = plan.get("release_meta")
        canonical = os.path.realpath(root) + ".meta.json"
        if not isinstance(meta, str) or not os.path.isabs(meta) \
                or os.path.realpath(meta) != canonical:
            raise FrameError(
                f"候选 release_meta 必须是 canonical sidecar：{meta!r} != {canonical}")
        if not os.path.isfile(meta):
            raise FrameError(f"候选 release_meta 不存在：{meta}")
    else:
        for key in ("test_release_root", "test_release_version", "test_release_ref"):
            if not isinstance(plan.get(key), str) or not plan[key]:
                raise FrameError(f"dev 冻结计划缺 {key}")
        if not os.path.isabs(plan["test_release_root"]):
            raise FrameError("dev 冻结计划 test_release_root 必须是绝对路径")
    return True


def _token(path):
    """读一次冻结字节，输出 sha256 与长度（供内部 argv 携带；不产生 sidecar）。"""
    import hashlib

    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        data = os.read(fd, 1 << 20)
        if os.read(fd, 1):
            raise FrameError(f"token carrier is too large or not a plain file: {path}")
    finally:
        os.close(fd)
    return "TOKEN_SHA256={}\nTOKEN_SIZE={}".format(hashlib.sha256(data).hexdigest(), len(data))


def _assignments(stage, fields):
    print("WF_STAGE=" + shlex.quote(stage or "public"))
    for name, value in fields.items():
        print(f"{ENV_NAMES[name]}=" + shlex.quote(value))
    return 0


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv:
        print("FRAME-INVALID: command is required", file=sys.stderr)
        return 2
    command, rest = argv[0], argv[1:]
    rest = rest[1:] if rest[:1] == ["--"] else rest
    try:
        if command == "encode":
            if rest[:1] != ["--stage"]:
                raise FrameError("encode requires --stage <lease|execute>")
            stage, rest = rest[1], rest[2:]
            if rest[:1] == ["--"]:
                rest = rest[1:]
            head, user = _split(rest)
            if len(head) % 2:
                raise FrameError("字段必须成对给出")
            frame = encode(stage, dict(zip(head[0::2], head[1::2])), user)
            print("FRAME=(" + " ".join(shlex.quote(item) for item in frame) + ")")
            return 0
        if command == "encode-repro":
            if rest[:1] != ["--stage"]:
                raise FrameError("encode-repro requires --stage <repro-lease|repro-inner>")
            stage, rest = rest[1], rest[2:]
            if rest[:1] == ["--"]:
                rest = rest[1:]
            if rest[-1:] == ["--"]:
                rest = rest[:-1]
            if len(rest) % 2:
                raise FrameError("字段必须成对给出")
            frame = encode_repro(stage, dict(zip(rest[0::2], rest[1::2])))
            print("FRAME=(" + " ".join(shlex.quote(item) for item in frame) + ")")
            return 0
        if command == "token":
            if rest[:1] != ["--file"]:
                raise FrameError("token requires --file <path>")
            print(_token(rest[1]))
            return 0
        if command == "strip":
            stage, fields, user = decode(rest)
            print("USER_ARGV=(" + " ".join(shlex.quote(item) for item in user) + ")")
            return _assignments(stage, fields)
        if command == "strip-repro":
            stage, fields, _user = decode_repro(rest)
            print("USER_ARGV=()")
            return _assignments(stage, fields)
        raise FrameError(f"unknown command: {command}")
    except FrameError as exc:
        print(f"FRAME-INVALID: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
