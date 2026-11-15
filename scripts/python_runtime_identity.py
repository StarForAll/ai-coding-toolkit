#!/usr/bin/env python3
"""python_runtime_identity.py — tool/SUT 解释器身份的**单一解析点**。

身份由两部分组成，缺一不可：

- 路径身份：`SHA256(UTF8(canonical_JSON({invocation, executable_realpath, prefix, base_prefix})))`。
  `invocation` 是实际使用的启动脚本的绝对路径（保留 venv 启动位置，不先 realpath 成基础解释器），
  `sys.*` 三个字段由被探测解释器自己返回。**只哈希这些路径字符串**，不 walk
  `sys.prefix`/`site-packages`/`/usr`，也不把它当整个安装树的指纹。
- 字节身份：调用文件与真实 Python binary 各自按**文件字节**算 sha256（同 role 同文件在一次
  resolve 内去重）；另有实现名与完整版本。

对话/缓存身份用 `identity_digest()`（同一份规范 JSON 摘要），直接给 build inputs 与 proof 用。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

ROLES = ("tool", "sut")
DEFAULT_SUT = "/usr/bin/python3"
PROBE = (
    "import json,sys;"
    "print(json.dumps({'executable': sys.executable, 'prefix': sys.prefix,"
    " 'base_prefix': sys.base_prefix, 'implementation': sys.implementation.name,"
    " 'version': '{}.{}.{}'.format(*sys.version_info[:3])}))"
)


class IdentityError(Exception):
    """解析不出可信身份（缺失/不可读/探针失败）；不签发 None。"""


def _bytes_digest(path: Path) -> dict:
    digest = hashlib.sha256()
    total = 0
    try:
        with open(path, "rb") as handle:
            for chunk in iter(lambda: handle.read(1 << 20), b""):
                total += len(chunk)
                digest.update(chunk)
    except OSError as exc:
        raise IdentityError(f"cannot read {path}: {exc}") from exc
    return {"digest": "sha256:" + digest.hexdigest(), "bytes": total}


def probe(python: str) -> dict:
    """让目标解释器自报 sys.executable/sys.prefix/sys.base_prefix/实现/版本。"""
    try:
        completed = subprocess.run([python, "-c", PROBE], capture_output=True, text=True, check=False)
    except OSError as exc:
        raise IdentityError(f"cannot launch interpreter {python}: {exc}") from exc
    if completed.returncode != 0:
        raise IdentityError(
            f"interpreter probe failed for {python}: {completed.stderr.strip()[:200]}")
    try:
        value = json.loads(completed.stdout)
    except ValueError as exc:
        raise IdentityError(f"interpreter probe returned non-JSON for {python}") from exc
    for key in ("executable", "prefix", "base_prefix", "implementation", "version"):
        if not isinstance(value.get(key), str) or not value[key]:
            raise IdentityError(f"interpreter probe missing {key} for {python}")
    return value


def canonical_json(payload) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def path_identity(invocation: str, probed: dict) -> str:
    """路径字符串身份：固定四个键、排序、紧凑、UTF-8。"""
    payload = {
        "invocation": invocation,
        "executable_realpath": os.path.realpath(probed["executable"]),
        "prefix": os.path.realpath(probed["prefix"]),
        "base_prefix": os.path.realpath(probed["base_prefix"]),
    }
    return "sha256:" + hashlib.sha256(canonical_json(payload).encode("utf-8")).hexdigest()


def resolve(role: str, invocation: str, python: str | None = None, probe_fn=probe) -> dict:
    """解析一个 role 的完整身份。同 role 同解释器同调用文件在一次 resolve 内只读一次字节。"""
    if role not in ROLES:
        raise IdentityError(f"unknown role {role!r} (choose {'/'.join(ROLES)})")
    if not invocation:
        raise IdentityError("invocation is required")
    interpreter = python or (sys.executable if role == "tool" else (os.environ.get("WF_TEST_PYTHON") or DEFAULT_SUT))
    invocation_abs = os.path.abspath(invocation)
    if not os.path.isfile(invocation_abs):
        raise IdentityError(f"invocation file is missing: {invocation_abs}")
    probed = probe_fn(interpreter)
    binary_path = os.path.realpath(probed["executable"])
    if not os.path.isfile(binary_path):
        raise IdentityError(f"python binary is missing: {binary_path}")
    binary = _bytes_digest(Path(binary_path))
    invocation_file = _bytes_digest(Path(invocation_abs))
    return {
        "role": role,
        "interpreter": interpreter,
        "implementation": probed["implementation"],
        "version": probed["version"],
        "path_identity": path_identity(invocation_abs, probed),
        "binary": {"path": binary_path, "digest": binary["digest"], "bytes": binary["bytes"]},
        "invocation_file": {"path": invocation_abs, "digest": invocation_file["digest"],
                            "bytes": invocation_file["bytes"]},
    }


def identity_digest(identities) -> str:
    """多 role 身份的规范摘要（缓存/proof 的唯一入口）。"""
    ordered = sorted(identities, key=lambda item: item["role"])
    return "sha256:" + hashlib.sha256(canonical_json(ordered).encode("utf-8")).hexdigest()


class Resolver:
    """一次 barrier 内复用：同 (role, interpreter, invocation) 只解析一次。"""

    def __init__(self, probe_fn=probe):
        self._probe = probe_fn
        self._cache = {}
        self.probe_count = 0

    def resolve(self, role, invocation, python=None):
        key = (role, python, os.path.abspath(invocation))
        if key not in self._cache:
            self._cache[key] = resolve(role, invocation, python, self._counting_probe)
        return self._cache[key]

    def _counting_probe(self, python):
        self.probe_count += 1
        return self._probe(python)

    def digest(self, role, invocation, python=None) -> str:
        return identity_digest([self.resolve(role, invocation, python)])


def main(argv=None):
    parser = argparse.ArgumentParser(description="解析 tool/SUT 解释器身份（路径字符串 + 文件字节）")
    parser.add_argument("--role", choices=ROLES, default="tool")
    parser.add_argument("--invocation", required=True, help="实际被启动的脚本绝对路径")
    parser.add_argument("--python", default=None, help="解释器（默认按 role：tool=当前解释器，sut=WF_TEST_PYTHON）")
    args = parser.parse_args(argv)
    try:
        print(json.dumps(resolve(args.role, args.invocation, args.python),
                         ensure_ascii=False, indent=2, sort_keys=True))
    except IdentityError as exc:
        print(f"FAIL  {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
