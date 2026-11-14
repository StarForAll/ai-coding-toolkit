#!/usr/bin/env python3
"""source_hygiene.py — 源树字节码卫生的**唯一实现**（运行期 delta + 缓存条目 strict）。

为什么需要它：``r64_tests.py`` 旧 P3-1 先 ``rmtree`` 所有 ``__pycache__`` 再断言“没有”，
恒真且会改写作者源树。运行期卫生必须由运行器承载，而不是由某个套件自证。

两种模式共用同一份扫描：

- delta（run_all 前后快照对拍）：只对**新增**失败（本地存量不算本次回归），
  存量以警告 + 可直接执行的清理命令呈现；
- strict（模板缓存条目）：条目内出现任何 ``__pycache__``/``*.pyc`` 即脏。

扫描根不存在时按空集合处理并在输出里标注 ``absent``（r67 的假树没有
``docs/workflows/wf``；让缺根崩溃等于把本不该失败的假环境判红）。
"""
from __future__ import annotations

import argparse
import json
import os
import sys

DEFAULT_ROOTS = ("docs/workflows/wf", "scripts/tests")


def _walk(root):
    pyc, cache_dirs = [], []
    for base, dirs, names in os.walk(root):
        dirs[:] = sorted(name for name in dirs if name != ".git")
        for name in dirs:
            if name == "__pycache__":
                path = os.path.join(base, name)
                cache_dirs.append(path)
        for name in names:
            if name.endswith(".pyc"):
                pyc.append(os.path.join(base, name))
    return {"pyc": sorted(pyc), "pycache_dirs": sorted(cache_dirs)}


def scan(roots):
    """返回 {'pyc': [...], 'pycache_dirs': [...], 'absent': [...]}（绝对路径，稳定排序）。"""
    found = {"pyc": [], "pycache_dirs": [], "absent": []}
    for root in roots:
        absolute = os.path.abspath(root)
        if not os.path.isdir(absolute):
            found["absent"].append(absolute)
            continue
        result = _walk(absolute)
        found["pyc"].extend(result["pyc"])
        found["pycache_dirs"].extend(result["pycache_dirs"])
    for key in ("pyc", "pycache_dirs", "absent"):
        found[key] = sorted(set(found[key]))
    return found


def default_roots(repo):
    return [os.path.join(repo, relative) for relative in DEFAULT_ROOTS]


def snapshot(repo, out):
    found = scan(default_roots(repo))
    with open(out, "w", encoding="utf-8") as handle:
        json.dump(found, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
    for path in found["absent"]:
        print(f"HYGIENE-ABSENT: {path}（按空集合处理）")
    print(f"HYGIENE-SNAPSHOT: pyc={len(found['pyc'])} pycache_dirs={len(found['pycache_dirs'])} "
          f"absent={len(found['absent'])}")
    return 0


def _load_snapshot(path):
    try:
        with open(path, encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, ValueError) as exc:
        print(f"HYGIENE-SNAPSHOT-INVALID: {exc}", file=sys.stderr)
        return None
    if not isinstance(data, dict):
        print("HYGIENE-SNAPSHOT-INVALID: 顶层不是对象", file=sys.stderr)
        return None
    for key in ("pyc", "pycache_dirs"):
        if not isinstance(data.get(key), list):
            print(f"HYGIENE-SNAPSHOT-INVALID: 缺 {key}", file=sys.stderr)
            return None
    return data


def _cleanup_hint(roots):
    quoted = " ".join(roots)
    return (f"清理：find {quoted} \\( -name '*.pyc' -o -name '__pycache__' \\) "
            f"-prune -exec rm -rf {{}} +")


def check_delta(repo, snapshot_path):
    expected = _load_snapshot(snapshot_path)
    if expected is None:
        return 2
    roots = default_roots(repo)
    current = scan(roots)
    for path in current["absent"]:
        print(f"HYGIENE-ABSENT: {path}（按空集合处理）")
    known = set(expected.get("pyc") or []) | set(expected.get("pycache_dirs") or [])
    new = sorted((set(current["pyc"]) | set(current["pycache_dirs"])) - known)
    if new:
        print("SOURCE-TREE-POLLUTED: 本次运行在源树新增了字节码产物（不允许）")
        for path in new:
            print(f"  + {path}")
        print(_cleanup_hint([root for root in roots if os.path.isdir(root)]))
        return 1
    existing = sorted((set(current["pyc"]) | set(current["pycache_dirs"])) & known)
    if existing:
        print(f"HYGIENE-WARNING: 源树有 {len(existing)} 个存量字节码产物（不是本次运行造成的）")
        for path in existing[:10]:
            print(f"  = {path}")
        if len(existing) > 10:
            print(f"  ... 另有 {len(existing) - 10} 个")
        print(_cleanup_hint([root for root in roots if os.path.isdir(root)]))
    print(f"HYGIENE-OK: 本次运行未新增（pyc={len(current['pyc'])} "
          f"pycache_dirs={len(current['pycache_dirs'])}）")
    return 0


def check_strict(root):
    absolute = os.path.abspath(root)
    if not os.path.isdir(absolute):
        print(f"HYGIENE-ABSENT: {absolute}（按空集合处理）")
        print("HYGIENE-OK: 0 个字节码产物")
        return 0
    found = scan([absolute])
    dirty = found["pyc"] + found["pycache_dirs"]
    if dirty:
        print(f"TEMPLATE-CACHE-DIRTY: {absolute} 含字节码产物（缓存条目必须绝对干净）")
        for path in dirty:
            print(f"  + {path}")
        return 1
    print("HYGIENE-OK: 0 个字节码产物")
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description="源树字节码卫生检查（单一实现）")
    sub = parser.add_subparsers(dest="operation", required=True)
    snap = sub.add_parser("snapshot", help="记录扫描快照")
    snap.add_argument("repo")
    snap.add_argument("out")
    check = sub.add_parser("check", help="delta 或 strict 判定")
    check.add_argument("root")
    check.add_argument("--expect", default=None, help="snapshot 产物；给出即 delta 模式")
    check.add_argument("--strict", action="store_true", help="绝对判据：任何产物即非零")
    args = parser.parse_args(argv)
    if args.operation == "snapshot":
        return snapshot(args.repo, args.out)
    if args.strict:
        return check_strict(args.root)
    if not args.expect:
        parser.error("check 需要 --expect <snapshot> 或 --strict")
    return check_delta(args.root, args.expect)


if __name__ == "__main__":
    raise SystemExit(main())
