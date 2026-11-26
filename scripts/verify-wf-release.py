#!/usr/bin/env python3
"""verify-wf-release.py — 发行 tag 的机械闭环核对（authoring 工具，不进发行清单）。

为什么需要它（2026-11-23，dogfood 五轮 b-P0）：
`docs/workflows/wf/README.md` §3 写"源树 version、清单 version、发行 tag 三者必须同批修改"，
但这条义务只存在于散文里。实况是仓库只有 `wf-v0.1.0` 一个 tag，README 却记载
"0.1.5 → 0.1.6 可用 upgrade 升级"——安装器的 `REF_RE` 加 `rev-parse` 只认真实存在的 tag，
于是文档承诺的升级通道在字段上**不可执行**。"写不成机械检查的义务从不履行"正是本轮要收口的
问题类型：这里把每条义务变成一次可稳定计算的核对，只报事实与出口，不创建/修改/删除任何 ref。

核对项（逐项独立，任一失败即非零退出）：
1. `tag_exists`                 `git rev-parse --verify <ref>^{commit}` 且 `git tag -l` 含该 ref；
2. `release_tree_matches_source` 源码树 → 重建发行树 == 工作树发行树（复用 builder `--verify`）；
3. `tag_tree_matches_worktree`   tag 提交内 `docs/workflows/wf-release/**` 的 blob 与工作树逐字节一致，
                                 且工作树没有该提交缺少的发行文件（多出来的文件就是"没进 tag 的发行"）；
4. `cli_package`                tag 提交内 `docs/workflows/wf-cli/` 存在、入口为 `wf_cli.main:entry`，
                                 版本动态读取的清单与 tag 版本一致；
5. `manifest_version`           tag 提交内 `wf-release.json.version == --version`；
6. `readme_version`             tag 提交内 `docs/workflows/wf/README.md` 的「目标版本」行 == --version；
7. `rules_digest`               按同一算法重算 `compatibility.rules_digest` 并与声明值相同。

用法：
    python3 scripts/verify-wf-release.py --version 0.1.7 --ref refs/tags/wf-v0.1.7 [--json]
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import wf_release_common as common  # noqa: E402

REF_RE = re.compile(r"^refs/tags/wf-v(\d+)\.(\d+)\.(\d+)$")
TARGET_VERSION_RE = re.compile(r"\|\s*目标版本\s*\|\s*`([0-9]+\.[0-9]+\.[0-9]+)`")
RELEASE_PREFIX = "docs/workflows/wf-release/"
README_PATH = "docs/workflows/wf/README.md"
MANIFEST_PATH = RELEASE_PREFIX + "wf-release.json"
CLI_PREFIX = "docs/workflows/wf-cli/"
CLI_PYPROJECT = CLI_PREFIX + "pyproject.toml"
CLI_MAIN = CLI_PREFIX + "wf_cli/main.py"
CLI_BOOTSTRAP = CLI_PREFIX + "install.py"


class VerifyError(Exception):
    pass


def _git(repo, argv, binary=False):
    result = subprocess.run(["git", "-C", repo] + argv, capture_output=True,
                            text=not binary, check=False)
    if result.returncode != 0:
        detail = result.stderr if not binary else result.stderr.decode("utf-8", "replace")
        raise VerifyError((detail or "").strip()[-400:] or f"git {' '.join(argv)} failed")
    return result.stdout


def _git_bytes(repo, argv):
    return _git(repo, argv, binary=True)


def _blob(repo, commit, path):
    return _git_bytes(repo, ["cat-file", "blob", f"{commit}:{path}"])


def _tree_paths(repo, commit, prefix):
    raw = _git(repo, ["ls-tree", "-r", "--name-only", commit, "--", prefix])
    return sorted(line for line in raw.splitlines() if line.strip())


def check_tag(repo, ref, version):
    # `git tag --list` 匹配的是 **tag 名**（不含 refs/tags/ 前缀）：拿完整 ref 去比会永远
    # 匹配不到，把"tag 存在"误判成"缺失"。
    name = ref[len("refs/tags/"):] if ref.startswith("refs/tags/") else ref
    tags = _git(repo, ["tag", "--list", name]).split()
    if name not in tags:
        return {"name": "tag_exists", "ok": False,
                "facts": {"ref": ref, "present_tags": sorted(
                    item for item in _git(repo, ["tag", "--list", "wf-v*"]).split())},
                # `git tag` 的第 1 个参数是**tag 名**，不是完整 ref：写成 `refs/tags/…`
                # 会造出重复层级（2026-11-23 九轮复审 b-6）。
                "exits": [f"人按发行流程创建 tag：git tag {ref[len('refs/tags/'):] if ref.startswith('refs/tags/') else ref} <已含发行树的提交>",
                          "或改用已存在的发行 tag（引用只认真实 ref，裸提交不算）"]}
    try:
        commit = _git(repo, ["rev-parse", "--verify", f"{ref}^{{commit}}"]).strip()
    except VerifyError as exc:
        return {"name": "tag_exists", "ok": False, "facts": {"ref": ref, "detail": str(exc)},
                "exits": ["tag 无法解析到提交：按发行流程重新打 tag"]}
    return {"name": "tag_exists", "ok": True, "commit": commit, "facts": {"ref": ref}}


def check_release_tree_matches_source(repo, version):
    builder = os.path.join(os.path.dirname(os.path.abspath(__file__)), "build-wf-release.py")
    result = subprocess.run([sys.executable, builder, "--version", version, "--verify"],
                            capture_output=True, text=True, check=False)
    ok = result.returncode == 0
    return {"name": "release_tree_matches_source", "ok": ok,
            "facts": {"version": version, "exit": result.returncode},
            "detail": (result.stdout or result.stderr or "").strip()[-800:] if not ok else None,
            "exits": ([] if ok else
                      [f"按同版源树重建：python3 scripts/build-wf-release.py --version {version}",
                       "tag wf-v%s 已存在时同版重建会被拒绝：此时按人发起的版本推进走 "
                       "python3 scripts/release-wf.py（它重建发行树并打新 tag）" % version,
                       "重建后复核差异，不手改发行树"])}


def check_tag_tree(repo, commit, version):
    tag_paths = _tree_paths(repo, commit, RELEASE_PREFIX)
    if not tag_paths:
        return {"name": "tag_tree_matches_worktree", "ok": False,
                "facts": {"paths_in_tag": 0},
                "exits": ["该 tag 提交内没有发行树：tag 打错了（不是发行提交）"]}
    worktree_root = repo
    mismatched, missing = [], []
    for path in tag_paths:
        absolute = os.path.join(worktree_root, *path.split("/"))
        if not os.path.isfile(absolute):
            missing.append(path)
            continue
        with open(absolute, "rb") as handle:
            local = handle.read()
        if local != _blob(repo, commit, path):
            mismatched.append(path)
    extra = []
    release_root = os.path.join(worktree_root, *RELEASE_PREFIX.rstrip("/").split("/"))
    for directory, _dirs, files in os.walk(release_root):
        for name in files:
            absolute = os.path.join(directory, name)
            relative = os.path.relpath(absolute, worktree_root).replace(os.sep, "/")
            if relative not in tag_paths:
                extra.append(relative)
    ok = not (mismatched or missing or extra)
    return {"name": "tag_tree_matches_worktree", "ok": ok,
            "facts": {"paths_in_tag": len(tag_paths), "mismatched": sorted(mismatched)[:20],
                      "missing_in_worktree": sorted(missing)[:20],
                      "not_in_tag": sorted(extra)[:20]},
            "exits": ([] if ok else
                      ["tag 指向的必须正是当前发行树：按同版重建并提交后重新打 tag",
                       "不手改发行树来迎合旧 tag，也不把未提交的发行树当作已发行"])}


def check_cli_package(repo, commit, version):
    """系统级 wf 命令随同一发行 tag 交付，且版本动态解析到该 tag 的清单。"""
    import posixpath
    import tomllib

    try:
        data = tomllib.loads(_blob(repo, commit, CLI_PYPROJECT).decode("utf-8"))
    except (VerifyError, ValueError, tomllib.TOMLDecodeError) as exc:
        return {"name": "cli_package", "ok": False,
                "facts": {"path": CLI_PYPROJECT, "detail": str(exc)},
                "exits": ["发行 tag 必须包含 docs/workflows/wf-cli/pyproject.toml"]}
    scripts = (data.get("project") or {}).get("scripts") or {}
    if scripts.get("wf") != "wf_cli.main:entry":
        return {"name": "cli_package", "ok": False,
                "facts": {"scripts": scripts},
                "exits": ["wf-cli 必须暴露 wf = wf_cli.main:entry"]}
    tool = (data.get("tool") or {}).get("hatch", {}).get("version") or {}
    rel = tool.get("path")
    pattern = tool.get("pattern")
    if not rel or not pattern:
        return {"name": "cli_package", "ok": False,
                "facts": {"tool": tool},
                "exits": ["wf-cli 版本必须动态读取发行清单"]}
    target = posixpath.normpath(CLI_PREFIX + rel)
    if not target.startswith(RELEASE_PREFIX):
        return {"name": "cli_package", "ok": False,
                "facts": {"path": rel, "resolved": target},
                "exits": ["wf-cli 版本路径必须指向发行清单"]}
    try:
        text = _blob(repo, commit, target).decode("utf-8")
    except VerifyError as exc:
        return {"name": "cli_package", "ok": False,
                "facts": {"path": target, "detail": str(exc)},
                "exits": ["发行 tag 必须包含 wf-cli 读取的发行清单"]}
    match = re.search(pattern, text)
    try:
        declared = match.group("version") if match else None
    except IndexError:
        declared = None
    main_ok = True
    bootstrap_ok = True
    try:
        _blob(repo, commit, CLI_MAIN)
    except VerifyError:
        main_ok = False
    try:
        _blob(repo, commit, CLI_BOOTSTRAP)
    except VerifyError:
        bootstrap_ok = False
    ok = declared == version and main_ok and bootstrap_ok
    return {"name": "cli_package", "ok": ok,
            "facts": {"declared": declared, "requested": version,
                      "main": main_ok, "bootstrap": bootstrap_ok},
            "exits": ([] if ok else
                      ["wf-cli 的版本/入口必须与发行 tag 同批：重建发行后提交包目录再打 tag"])}


def check_manifest_version(repo, commit, version):
    try:
        manifest = json.loads(_blob(repo, commit, MANIFEST_PATH).decode("utf-8"))
    except (VerifyError, ValueError) as exc:
        return {"name": "manifest_version", "ok": False,
                "facts": {"path": MANIFEST_PATH, "detail": str(exc)},
                "exits": ["tag 提交内没有可解析的发行清单：该提交不是一次发行"]}
    declared = str(manifest.get("version"))
    return {"name": "manifest_version", "ok": declared == version,
            "facts": {"declared": declared, "requested": version},
            "exits": ([] if declared == version else
                      ["清单 version 与 tag 版本必须同批修改（同版异内容按 WF_RELEASE_CONFLICT 拒）"])}


def check_readme_version(repo, commit, version):
    try:
        text = _blob(repo, commit, README_PATH).decode("utf-8", "replace")
    except VerifyError as exc:
        return {"name": "readme_version", "ok": False,
                "facts": {"path": README_PATH, "detail": str(exc)},
                "exits": ["tag 提交内没有 wf README：无法核对版本义务"]}
    match = TARGET_VERSION_RE.search(text)
    declared = match.group(1) if match else None
    return {"name": "readme_version", "ok": declared == version,
            "facts": {"declared": declared, "requested": version,
                      "path": README_PATH},
            "exits": ([] if declared == version else
                      ["README「目标版本」行与 tag 同批改（build 脚本也据此拒绝漂移）"])}


def check_rules_digest(repo, commit):
    try:
        manifest = json.loads(_blob(repo, commit, MANIFEST_PATH).decode("utf-8"))
    except (VerifyError, ValueError) as exc:
        return {"name": "rules_digest", "ok": False,
                "facts": {"path": MANIFEST_PATH, "detail": str(exc)},
                "exits": ["清单不可解析：无法重算 rules_digest"]}
    declared = (manifest.get("compatibility") or {}).get("rules_digest")
    common.ensure_wflib()
    from wflib import assets as wf_assets

    recomputed = wf_assets.compute_rules_digest(manifest)
    return {"name": "rules_digest", "ok": declared == recomputed,
            "facts": {"declared": declared, "recomputed": recomputed},
            "exits": ([] if declared == recomputed else
                      ["清单的 compatibility.rules_digest 与内容不符：按同版重建清单"])}


def verify(repo, version, ref, source_check=None):
    match = REF_RE.match(ref)
    if not match:
        return {"ok": False, "version": version, "ref": ref,
                "checks": [{"name": "ref_shape", "ok": False,
                            "facts": {"ref": ref},
                            "exits": ["发行引用形态固定为 refs/tags/wf-vX.Y.Z"]}]}
    if "%s.%s.%s" % match.groups() != version:
        return {"ok": False, "version": version, "ref": ref,
                "checks": [{"name": "ref_matches_version", "ok": False,
                            "facts": {"ref_version": "%s.%s.%s" % match.groups(),
                                      "requested": version},
                            "exits": ["--version 与 --ref 必须是同一发行版本"]}]}
    checks = []
    tag_check = check_tag(repo, ref, version)
    checks.append(tag_check)
    commit = tag_check.get("commit")
    checks.append((source_check or check_release_tree_matches_source)(repo, version))
    if commit:
        checks.append(check_tag_tree(repo, commit, version))
        checks.append(check_cli_package(repo, commit, version))
        checks.append(check_manifest_version(repo, commit, version))
        checks.append(check_readme_version(repo, commit, version))
        checks.append(check_rules_digest(repo, commit))
    return {"ok": all(item["ok"] for item in checks), "version": version, "ref": ref,
            "commit": commit, "checks": checks}


def _render(result):
    lines = [f"wf 发行核对：{result['ref']}（version={result['version']}）"]
    for item in result["checks"]:
        lines.append(f"  [{'OK  ' if item['ok'] else 'FAIL'}] {item['name']}")
        if not item["ok"]:
            facts = item.get("facts") or {}
            lines.append(f"         事实：{json.dumps(facts, ensure_ascii=False, sort_keys=True)}")
            for exit_hint in item.get("exits") or []:
                lines.append(f"         出口：{exit_hint}")
    lines.append("结论：" + ("该 tag 可作为发行引用" if result["ok"]
                            else "该 tag **不是**有效发行：按上面出口修正后重跑"))
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="核对发行 tag ↔ 源码树 ↔ 发行树 ↔ 清单 ↔ README（只读，不建/不改 tag）")
    parser.add_argument("--version", required=True, help="0.x.y（与 tag 同版本）")
    parser.add_argument("--ref", required=True, help="refs/tags/wf-vX.Y.Z")
    parser.add_argument("--repo", default=common.REPO_ROOT)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    try:
        result = verify(args.repo, args.version, args.ref)
    except VerifyError as exc:
        result = {"ok": False, "version": args.version, "ref": args.ref,
                  "checks": [{"name": "git", "ok": False, "facts": {"detail": str(exc)},
                              "exits": ["在仓库内运行；发行身份只用本地 git 事实核对"]}]}
    if args.json:
        sys.stdout.write(json.dumps(result, ensure_ascii=False, sort_keys=True) + "\n")
    else:
        sys.stdout.write(_render(result) + "\n")
    sys.stdout.flush()
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())