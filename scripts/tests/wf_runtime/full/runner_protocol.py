#!/usr/bin/env python3
"""runner_protocol.py — `run_all.sh` 内部阶段 frame 的唯一 encoder/decoder。

语法（只识别最前面的一个 frame，其余都是**原始用户参数**）：

```text
bash run_all.sh --_wf-internal <lease|controlled|execute> [该阶段固定键值对] -- <原始用户参数...>
bash repro/run.sh --_wf-inherited-release --context <path> --sha256 <hex> --size <N> -- <公开 repro 参数...>
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
    runner_protocol.py encode-inherited --context ... --sha256 ... --size N -- user-args
    runner_protocol.py strip-inherited -- user-args     （repro 入口）
`strip*` 输出可 eval 的 shell 赋值（USER_ARGV 数组 + WF_STAGE/字段）；非法返回 2。
"""
from __future__ import annotations

import argparse
import os
import re
import shlex
import sys

INTERNAL = "--_wf-internal"
INHERITED = "--_wf-inherited-release"
RESERVED_PREFIX = "--_wf-"
STAGES = ("lease", "controlled", "execute")
SHA256 = re.compile(r"^[0-9a-f]{64}$")
STAGE_FIELDS = {
    "lease": ("--entry-pid", "--results-root", "--results-explicit", "--scope-root"),
    "controlled": ("--entry-pid", "--results-root", "--results-explicit", "--scope-root",
                   "--plan-file", "--plan-sha256", "--plan-size"),
    "execute": ("--entry-pid", "--results-root", "--results-explicit", "--scope-root",
                "--plan-file", "--plan-sha256", "--plan-size",
                "--context-file", "--context-sha256", "--context-size"),
}
INHERITED_FIELDS = ("--context", "--sha256", "--size")
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
    "--context": "WF_INHERITED_CONTEXT",
    "--sha256": "WF_INHERITED_SHA256",
    "--size": "WF_INHERITED_SIZE",
}


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


def decode(argv, inherited=False):
    """解析 frame；没有 frame 时返回 (stage/None, {}, argv)。"""
    argv = list(argv)
    marker = INHERITED if inherited else INTERNAL
    if not argv or argv[0] != marker:
        _reject_reserved(argv)
        return None, {}, argv
    head, user = _split(argv[1:])
    if len(user) == 0 and "--" not in argv[1:]:
        pass  # 允许没有用户参数（但下面按字段完整性校验）
    if inherited:
        head_fields = dict(zip(head[::2], head[1::2]))
        if head[0::2] and any(not name.startswith("--") for name in head[0::2]):
            raise FrameError("inherited frame 结构错位（键值必须成对）")
        _validate_fields(head, INHERITED_FIELDS, required=INHERITED_FIELDS)
        return "inherited", head_fields, user
    if not head:
        raise FrameError("内部 frame 缺 stage")
    stage = head[0]
    if stage not in STAGES:
        raise FrameError(f"未知内部 stage：{stage!r}（可选 {'|'.join(STAGES)}）")
    _validate_fields(head[1:], STAGE_FIELDS[stage], required=STAGE_FIELDS[stage])
    fields = dict(zip(head[1::2], head[2::2]))
    _reject_reserved(user)
    return stage, fields, user


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
    order = STAGE_FIELDS[stage]
    unknown = set(fields) - set(order)
    if unknown:
        raise FrameError("stage 不接受字段：" + " ".join(sorted(unknown)))
    argv = [INTERNAL, stage]
    for name in order:
        if name not in fields:
            raise FrameError(f"缺字段：{name}")
        _validate(name, fields[name])
        argv += [name, fields[name]]
    return argv + ["--", *user_argv]


def encode_inherited(context, sha256, size, user_argv):
    for name, value in (("--context", context), ("--sha256", sha256), ("--size", size)):
        _validate(name, value)
    return [INHERITED, "--context", context, "--sha256", sha256, "--size", size, "--", *user_argv]


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
                raise FrameError("encode requires --stage <lease|controlled|execute>")
            stage, rest = rest[1], rest[2:]
            if rest[:1] == ["--"]:
                rest = rest[1:]
            head, user = _split(rest)
            if len(head) % 2:
                raise FrameError("字段必须成对给出")
            frame = encode(stage, dict(zip(head[0::2], head[1::2])), user)
            print("FRAME=(" + " ".join(shlex.quote(item) for item in frame) + ")")
            return 0
        if command == "encode-inherited":
            head, user = _split(rest)
            if len(head) != 6:
                raise FrameError("inherited frame 需要 --context/--sha256/--size 三个字段")
            values = dict(zip(head[0::2], head[1::2]))
            frame = encode_inherited(values["--context"], values["--sha256"], values["--size"], user)
            print("FRAME=(" + " ".join(shlex.quote(item) for item in frame) + ")")
            return 0
        if command == "token":
            if rest[:1] != ["--file"]:
                raise FrameError("token requires --file <path>")
            print(_token(rest[1]))
            return 0
        if command in ("strip", "strip-inherited"):
            stage, fields, user = decode(rest, inherited=command == "strip-inherited")
            print("USER_ARGV=(" + " ".join(shlex.quote(item) for item in user) + ")")
            return _assignments(stage, fields)
        raise FrameError(f"unknown command: {command}")
    except FrameError as exc:
        print(f"FRAME-INVALID: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
