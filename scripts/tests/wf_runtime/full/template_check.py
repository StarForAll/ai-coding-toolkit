#!/usr/bin/env python3
"""template_check.py — 校验 `cp -a` 出来的夹具模板副本（换目录 / 新进程 / 空 TMPDIR 的空态契约）。

为什么需要它：run-scoped 模板把“夹具 + 初始化任务”构建一次、之后每套件复制。
复制本身不会搬走**绝对路径**与**外部暂存目录**，所以复制后必须机械核对：
- `.wf/bin/wf.py` 与安装记录都在（否则套件会以一个不完整项目开局）；
- `.wf/**/*.json` 里不残留模板源路径（记录指向别处的项目 = 静默串味）；
- candidate 模式下 version / release_ref 仍等于本次候选（模板不能是别的发行装的）。

只做**可判定的空态检查**：不猜测语义、不修文件。任何一项不满足 → 非零退出，
由调用方把它当成该套件的失败（而不是静默 pass）。
"""
from __future__ import annotations

import argparse
import json
import os
import sys


TEXT_SUFFIXES = (".json", ".md")


def text_files(root, suffixes=TEXT_SUFFIXES):
    for base, dirs, names in os.walk(root):
        dirs[:] = [name for name in dirs if name != "__pycache__"]
        for name in names:
            if name.endswith(suffixes):
                yield os.path.join(base, name)


def check(root, leak_from=None, version=None, ref=None):
    problems = []
    if not os.path.isdir(root):
        return [f"项目目录不存在：{root}"]
    exe = os.path.join(root, ".wf", "bin", "wf.py")
    if not os.path.isfile(exe):
        problems.append("缺少 .wf/bin/wf.py")
    install = os.path.join(root, ".wf", "install", "installation.json")
    if not os.path.isfile(install):
        problems.append("缺少 .wf/install/installation.json")
    else:
        try:
            with open(install, encoding="utf-8") as handle:
                record = json.load(handle)
        except (OSError, ValueError) as exc:
            problems.append(f"安装记录不可解析：{exc}")
            record = {}
        if version and record.get("version") != version:
            problems.append(f"安装记录 version={record.get('version')!r} 期望 {version!r}")
        if ref and record.get("release_ref") != ref:
            problems.append(f"安装记录 release_ref={record.get('release_ref')!r} 期望 {ref!r}")
        if record.get("version") == "0.0.0-dev" and version:
            problems.append("安装记录仍是 dev 占位版本 0.0.0-dev")
    if leak_from:
        needle = os.path.realpath(leak_from)
        for path in text_files(os.path.join(root, ".wf")):
            try:
                with open(path, encoding="utf-8", errors="replace") as handle:
                    text = handle.read()
            except OSError:
                continue
            if needle in text:
                problems.append(f"记录残留模板路径 {needle}：{os.path.relpath(path, root)}")
    return problems


def repoint(root, old_prefix):
    """把记录里指向模板的绝对路径改写成**当前项目**路径。

    安装记录会按安装时的绝对路径登记技能根（`root_ref`），`cp -a` 之后它仍指向模板；
    不迁移的话，后续 uninstall/reinstall 类入口会去操作模板目录（共享可变状态）。
    只改 `.json`/`.md` 文本里的这个前缀，其余字节不动。
    """
    old = os.path.realpath(old_prefix)
    new = os.path.realpath(root)
    if old == new:
        return []
    touched = []
    for path in text_files(os.path.join(root, ".wf")):
        try:
            with open(path, encoding="utf-8", errors="surrogateescape") as handle:
                text = handle.read()
        except OSError:
            continue
        if old not in text:
            continue
        with open(path, "w", encoding="utf-8", errors="surrogateescape", newline="") as handle:
            handle.write(text.replace(old, new))
        touched.append(os.path.relpath(path, root))
    return touched


def main(argv=None):
    parser = argparse.ArgumentParser(description="夹具模板副本空态校验")
    parser.add_argument("root")
    parser.add_argument("--leak-from", default=None, help="模板源路径（检查记录里是否残留）")
    parser.add_argument("--repoint-from", default=None,
                        help="把记录里指向该模板路径的绝对路径改写为当前项目路径（复制后必做）")
    parser.add_argument("--version", default=None)
    parser.add_argument("--ref", default=None)
    parser.add_argument("--expect-repoint-min", type=int, default=None,
                        help="要求 --repoint-from 至少改写 N 个文件（0 = 静默 no-op，属异常）")
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args(argv)
    if args.expect_repoint_min is not None and not args.repoint_from:
        parser.error("--expect-repoint-min 需要同时给出 --repoint-from")
    repointed = None
    if args.repoint_from:
        touched = repoint(args.root, args.repoint_from)
        repointed = len(touched)
        # 结构化改写计数：判定留在本文件一处，bash 只传参与读退出码。
        print(f"TEMPLATE-REPOINT-COUNT={repointed}")
        if touched and not args.quiet:
            print(f"TEMPLATE-REPOINT: {repointed} 个文件 → {os.path.realpath(args.root)}")
        leak = args.repoint_from
    else:
        leak = args.leak_from
    problems = check(args.root, leak, args.version, args.ref)
    if (repointed is not None and args.expect_repoint_min is not None
            and repointed < args.expect_repoint_min):
        problems.insert(0, f"改写数 {repointed} < 期望最小 {args.expect_repoint_min}"
                            "（记录未指向 --repoint-from，或路径形态不一致）")
    if problems:
        for problem in problems:
            print(f"TEMPLATE-CHECK-FAILED: {problem}")
        return 1
    if not args.quiet:
        print(f"TEMPLATE-OK: {os.path.realpath(args.root)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
