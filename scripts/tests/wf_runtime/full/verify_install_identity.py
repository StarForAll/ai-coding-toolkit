#!/usr/bin/env python3
"""verify_install_identity.py — 候选安装记录与 `.wf/lib` 内容的唯一核验点。

`wf_fixture.sh`、`f2_setup.sh` 与候选审计都消费同一条规则：安装记录必须是**本次候选**
（version / release_ref / source_commit / rules_digest），且安装后的 `.wf/lib` 字节必须
等于 `<release-root>/wf-release/lib`。只读；失败时打印差异并以 1 退出（调用方不得继续）。

    python3 verify_install_identity.py --target <project> --release-root <root> \
        --ref refs/tags/wf-v0.1.0 --version 0.1.0 [--json]
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
sys.path.insert(0, str(REPO / "scripts"))
import wf_release_common as common  # noqa: E402


def resolve_commit(release_root, ref):
    proc = subprocess.run(["git", "-c", "safe.directory=*", "rev-parse", f"{ref}^{{commit}}"],
                          cwd=release_root, capture_output=True, text=True)
    return proc.stdout.strip() if proc.returncode == 0 else None


def verify(target, release_root, ref, version, check_lib=True):
    """返回 (record, problems)：problems 为空才表示安装身份成立。"""
    problems = []
    install_path = Path(target) / ".wf" / "install" / "installation.json"
    try:
        record = json.loads(install_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return None, [f"安装记录不可读：{exc}"]
    try:
        manifest = json.loads((Path(release_root) / "wf-release.json").read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return record, [f"发行清单不可读：{exc}"]
    commit = resolve_commit(release_root, ref)
    if record.get("version") != version:
        problems.append(f"version={record.get('version')!r} expected={version!r}")
    if record.get("release_ref") != ref:
        problems.append(f"release_ref={record.get('release_ref')!r} expected={ref!r}")
    if not commit:
        problems.append(f"发行引用不可解析：{ref}")
    elif record.get("source_commit") != commit:
        problems.append(f"source_commit={record.get('source_commit')!r} expected={commit!r}")
    rules = (manifest.get("compatibility") or {}).get("rules_digest")
    if record.get("rules_digest") != rules:
        problems.append(f"rules_digest={record.get('rules_digest')!r} expected={rules!r}")
    if record.get("version") == "0.0.0-dev":
        problems.append("安装记录仍是 dev 占位版本 0.0.0-dev")
    if check_lib:
        installed = Path(target) / ".wf" / "lib"
        expected = Path(release_root) / "wf-release" / "lib"
        if not installed.is_dir():
            problems.append("安装后缺少 .wf/lib")
        elif common.tree_digest(str(installed)) != common.tree_digest(str(expected)):
            problems.append("安装后的 .wf/lib 内容不是本次候选发行")
    return record, problems


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target", required=True)
    parser.add_argument("--release-root", required=True)
    parser.add_argument("--ref", required=True)
    parser.add_argument("--version", required=True)
    parser.add_argument("--no-lib-check", action="store_true",
                        help="只核安装记录（用于只有安装记录的静态对象）")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    record, problems = verify(args.target, args.release_root, args.ref, args.version,
                              check_lib=not args.no_lib_check)
    projection = {key: (record or {}).get(key) for key in
                  ("version", "release_ref", "source_commit", "rules_digest")}
    if args.json:
        print(json.dumps({"ok": not problems, "record": projection,
                          "problems": problems}, ensure_ascii=False, sort_keys=True))
    if problems:
        print("INSTALL-IDENTITY-MISMATCH: " + "; ".join(problems), file=sys.stderr)
        return 1
    if not args.json:
        print(f"install identity ok: version={projection['version']} "
              f"ref={projection['release_ref']} commit={projection['source_commit'][:12]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
