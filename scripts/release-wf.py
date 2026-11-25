#!/usr/bin/env python3
"""One-shot wf release with automatic version bump.

Default: patch bump x.x.y -> x.x.(y+1). ``--minor`` bumps x.(x+1).0; ``--major`` bumps (x+1).0.0.
If the current manifest version has no local tag yet, that prepared version is released as-is
(so a pending release is not skipped); once it is tagged, the next invocation bumps.

After a successful release Forgejo keeps only the newest three wf-v* tags; older remote tags are
deleted. Local old tags are kept unless ``--prune-local-tags`` is given. ``--prune-tags`` performs
the retention pass without publishing.

The script reads FORGEJO_TOKEN and WF_FORGEJO_BASE from the environment. If either is absent it
prompts interactively; in a non-interactive process it fails instead of hanging. The token is read
with getpass and is never printed or passed as an argument.
"""

from __future__ import annotations

import argparse
import getpass
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
FORGEJO_REMOTE = "backup"
README = REPO_ROOT / "docs" / "workflows" / "wf" / "README.md"
CLI_README = REPO_ROOT / "docs" / "workflows" / "wf-cli" / "README.md"
RELEASE_ROOT = REPO_ROOT / "docs" / "workflows" / "wf-release"
MANIFEST = RELEASE_ROOT / "wf-release.json"
VERSION_RE = re.compile(r"^\d+\.\d+\.\d+$")
TAG_RE = re.compile(r"^wf-v(\d+)\.(\d+)\.(\d+)$")
KEEP_TAGS = 3
TARGET_ROW_RE = re.compile(r"^(\|\s*目标版本\s*\|.*)$", re.MULTILINE)


class ReleaseError(Exception):
    pass


def run(command, *, capture=False, env=None):
    if capture:
        return subprocess.run(command, cwd=str(REPO_ROOT), env=env, text=True,
                              capture_output=True, check=False)
    return subprocess.run(command, cwd=str(REPO_ROOT), env=env, check=False)


def git(*args, capture=False, env=None):
    located = shutil.which("git")
    if not located:
        raise ReleaseError("找不到 git")
    return run([located, *args], capture=capture, env=env)


def current_version():
    try:
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise ReleaseError(f"无法读取发行清单：{exc}") from exc
    version = str(manifest.get("version") or "")
    if not VERSION_RE.match(version):
        raise ReleaseError(f"发行清单版本不是 X.Y.Z: {version!r}")
    text = README.read_text(encoding="utf-8")
    match = TARGET_ROW_RE.search(text)
    if not match or f"`{version}`" not in match.group(1):
        raise ReleaseError("README「目标版本」行与发行清单版本不一致；先同步版本")
    return version


def next_version(version, mode):
    if not VERSION_RE.match(version or ""):
        raise ReleaseError(f"非法版本：{version!r}")
    major, minor, patch = (int(part) for part in version.split("."))
    if mode == "minor":
        return f"{major}.{minor + 1}.0"
    if mode == "major":
        return f"{major + 1}.0.0"
    return f"{major}.{minor}.{patch + 1}"


def select_version(old, mode, *, explicit=False, already_tagged=False):
    """Default patch releases an untagged prepared version; explicit flags always bump."""
    return next_version(old, mode) if explicit or already_tagged else old


def tag_commit(tag):
    result = git("rev-parse", "--verify", f"refs/tags/{tag}^{{commit}}", capture=True)
    return (result.stdout or "").strip() if result.returncode == 0 else None


def head_commit():
    result = git("rev-parse", "HEAD", capture=True)
    if result.returncode != 0:
        raise ReleaseError("无法读取 HEAD")
    return (result.stdout or "").strip()


def tag_key(tag):
    match = TAG_RE.match(tag or "")
    if not match:
        raise ReleaseError(f"非法 wf tag：{tag!r}")
    return tuple(int(part) for part in match.groups())


def prune_candidates(tags, *, keep=KEEP_TAGS, protect=()):
    """Return tags outside the newest `keep` versions; `protect` tags are never returned."""
    protected = set(protect)
    ordered = sorted({tag for tag in tags if TAG_RE.match(tag or "")},
                     key=tag_key, reverse=True)
    return [tag for tag in ordered[keep:] if tag not in protected]


def remote_tags():
    result = git("ls-remote", "--tags", "--refs", FORGEJO_REMOTE, "refs/tags/wf-v*", capture=True)
    if result.returncode != 0:
        raise ReleaseError("无法读取 Forgejo 远端 tag 列表")
    tags = []
    for line in (result.stdout or "").splitlines():
        fields = line.split("\t")
        if len(fields) == 2 and fields[1].startswith("refs/tags/"):
            tags.append(fields[1][len("refs/tags/"):])
    return tags


def local_tags():
    result = git("tag", "--list", "wf-v*", capture=True)
    if result.returncode != 0:
        raise ReleaseError("无法读取本地 wf tag 列表")
    return [line.strip() for line in (result.stdout or "").splitlines() if line.strip()]


def prune_remote_tags(current_tag, env):
    old = prune_candidates(remote_tags(), protect={current_tag})
    for tag in old:
        print(f"release-wf: prune Forgejo tag {tag}", file=sys.stderr)
        result = git("push", FORGEJO_REMOTE, f":refs/tags/{tag}", env=env)
        if result.returncode != 0:
            raise ReleaseError(f"删除 Forgejo 旧 tag {tag} 失败；release 已完成，按需重试")
    return old


def prune_local_tags(current_tag):
    old = prune_candidates(local_tags(), protect={current_tag})
    for tag in old:
        print(f"release-wf: prune local tag {tag}", file=sys.stderr)
        result = git("tag", "-d", tag, capture=True)
        if result.returncode != 0:
            raise ReleaseError(f"删除本地旧 tag {tag} 失败")
    return old


def current_branch():
    result = git("rev-parse", "--abbrev-ref", "HEAD", capture=True)
    branch = (result.stdout or "").strip() if result.returncode == 0 else ""
    if not branch or branch == "HEAD":
        raise ReleaseError("当前不是命名分支（detached HEAD）；不能推送项目内容")
    return branch


def project_remotes():
    result = git("remote", capture=True)
    if result.returncode != 0:
        raise ReleaseError("无法读取 git remote 列表")
    remotes = [line.strip() for line in (result.stdout or "").splitlines() if line.strip()]
    if not remotes:
        raise ReleaseError("没有配置任何 git remote")
    return remotes


def push_project_branch(env):
    branch = current_branch()
    for remote in project_remotes():
        print(f"release-wf: push project branch {branch} -> {remote}", file=sys.stderr)
        pushed = git("push", remote, f"HEAD:refs/heads/{branch}", env=env)
        if pushed.returncode != 0:
            raise ReleaseError(f"项目分支推送到 {remote} 失败；未创建 tag")
    return branch


def update_docs(old, new):
    if old == new:
        return False
    text = README.read_text(encoding="utf-8")
    match = TARGET_ROW_RE.search(text)
    if not match:
        raise ReleaseError("README 缺少「目标版本」行")
    row = match.group(1)
    updated = row.replace(f"`{old}`", f"`{new}`").replace(f"**{old}**", f"**{new}**")
    if f"`{new}`" not in updated:
        raise ReleaseError("无法在 README 目标版本行替换版本")
    text = text[:match.start()] + updated + text[match.end():]
    text = text.replace(f"当前 {old} 仍属预正式发行", f"当前 {new} 仍属预正式发行")
    README.write_text(text, encoding="utf-8", newline="\n")

    cli = CLI_README.read_text(encoding="utf-8")
    cli = cli.replace(f"wf-v{old}", f"wf-v{new}").replace(f"wf_cli-{old}", f"wf_cli-{new}")
    CLI_README.write_text(cli, encoding="utf-8", newline="\n")
    return True


def resolve_environment():
    base = (os.environ.get("WF_FORGEJO_BASE") or "").strip()
    token = (os.environ.get("FORGEJO_TOKEN") or "").strip()
    interactive = sys.stdin.isatty()
    if not base:
        if not interactive:
            raise ReleaseError("缺少 WF_FORGEJO_BASE；请在环境中设置或在交互终端输入")
        base = input("WF_FORGEJO_BASE（Forgejo Web/API 基址）: ").strip()
    if not token:
        if not interactive:
            raise ReleaseError("缺少 FORGEJO_TOKEN；请在环境中设置或在交互终端输入")
        token = getpass.getpass("FORGEJO_TOKEN（输入不显示）: ").strip()
    if not base or not token:
        raise ReleaseError("WF_FORGEJO_BASE / FORGEJO_TOKEN 不能为空")
    env = dict(os.environ)
    env["WF_FORGEJO_BASE"] = base.rstrip("/")
    env["FORGEJO_TOKEN"] = token
    return env


def commit_release_files(version):
    paths = ["docs/workflows/wf/README.md", "docs/workflows/wf-cli/README.md",
             "docs/workflows/wf-release"]
    status = git("status", "--porcelain", "--", *paths, capture=True)
    if status.returncode != 0:
        raise ReleaseError("无法读取 Git 状态")
    if not (status.stdout or "").strip():
        return False
    added = git("add", "--", *paths)
    if added.returncode != 0:
        raise ReleaseError("git add 失败")
    committed = git("commit", "-m", f"chore(wf): release {version}")
    if committed.returncode != 0:
        raise ReleaseError("提交发行版本失败")
    return True


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="wf 一次性发布：版本递增、构建、tag、push、release 附件")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--minor", action="store_true",
                       help="常规版本 x.x.y -> x.(x+1).0（默认是小版本 +1）")
    group.add_argument("--major", action="store_true",
                       help="正式版本 x.x.y -> (x+1).0.0")
    parser.add_argument("--prune-local-tags", action="store_true",
                        help="同时删除本地超过最新 3 个的 wf tag（默认保留本地 tag）")
    parser.add_argument("--prune-tags", action="store_true",
                        help="只清理旧 tag（Forgejo 保留最新 3 个），不发布")
    args = parser.parse_args(argv)

    try:
        if args.prune_tags and (args.minor or args.major):
            raise ReleaseError("--prune-tags 不能和 --minor/--major 同时使用")
        if args.prune_tags:
            current_tag = f"wf-v{current_version()}"
            protect = current_tag if tag_commit(current_tag) else None
            removed = prune_remote_tags(protect, dict(os.environ))
            if args.prune_local_tags:
                prune_local_tags(protect)
            print(f"OK  Forgejo 保留最新 {KEEP_TAGS} 个 wf tag"
                  + (f"，删除远端 {len(removed)} 个" if removed else ""))
            return 0

        status = git("status", "--porcelain", capture=True)
        if status.returncode != 0:
            raise ReleaseError("无法读取 Git 状态")
        if (status.stdout or "").strip():
            raise ReleaseError("工作区不干净；先提交或清理后再发布，脚本不会自动收编改动")

        env = resolve_environment()
        old = current_version()
        tag = f"wf-v{old}"
        mode = "minor" if args.minor else "major" if args.major else "patch"
        # 默认 patch 时，如果当前清单版本尚未打 tag，它就是待发布版本（不跳过 0.0.9 这类已准备好的版本）；
        # 显式 --minor/--major 总是从当前版本递增。
        explicit = args.minor or args.major
        new = select_version(old, mode, explicit=explicit,
                             already_tagged=tag_commit(tag) is not None)
        print(f"release-wf: {old} -> {new} ({mode})", file=sys.stderr)

        update_docs(old, new)
        built = run([sys.executable, "scripts/build-wf-release.py", "--version", new], env=env)
        if built.returncode != 0:
            raise ReleaseError("发行树构建失败；未创建 tag")
        verified = run([sys.executable, "scripts/build-wf-release.py", "--version", new,
                        "--verify"], env=env)
        if verified.returncode != 0:
            raise ReleaseError("发行树字节复现失败；未创建 tag")
        commit_release_files(new)
        push_project_branch(env)

        tag = f"wf-v{new}"
        created_tag = False
        pushed = False
        try:
            existing = tag_commit(tag)
            if existing:
                if existing != head_commit():
                    raise ReleaseError(f"{tag} 已存在但不在 HEAD；不能复用已发布版本")
            else:
                made = git("tag", tag)
                if made.returncode != 0:
                    raise ReleaseError(f"创建 tag {tag} 失败")
                created_tag = True

            checked = run([sys.executable, "scripts/verify-wf-release.py",
                           "--version", new, "--ref", f"refs/tags/{tag}"], env=env)
            if checked.returncode != 0:
                raise ReleaseError(f"{tag} 未通过发行校验；未推送")

            wheel = run([sys.executable, "scripts/build-wf-cli-wheel.py",
                         "--version", new, "--out", "tmp/wf-cli-dist"], env=env)
            if wheel.returncode != 0:
                raise ReleaseError("系统命令 wheel 构建失败；未推送")

            pushed = True  # 推送一旦尝试就保留本地 tag，避免远端可能已存在而本地被删
            pushed_result = git("push", FORGEJO_REMOTE, f"refs/tags/{tag}", env=env)
            if pushed_result.returncode != 0:
                raise ReleaseError(f"推送 {tag} 失败；本地 tag 保留")

            wheel_path = f"tmp/wf-cli-dist/wf_cli-{new}-py3-none-any.whl"
            attached = run([sys.executable, "scripts/attach-wf-cli-asset.py",
                            "--create-release", "--tag", tag, "--wheel", wheel_path], env=env)
            if attached.returncode != 0:
                raise ReleaseError(
                    f"tag 已推送，但 release 附件失败；重试：python3 scripts/attach-wf-cli-asset.py "
                    f"--create-release --tag {tag} --wheel {wheel_path}")

            prune_remote_tags(tag, env)
            if args.prune_local_tags:
                prune_local_tags(tag)
        finally:
            if created_tag and not pushed:
                git("tag", "-d", tag, capture=True)

        print(f"OK  {tag} 已发布：tag、release wheel 与 install.py 均完成")
        print("项目分支已推送到所有 git remote；tag 只推送了 Forgejo；"
              f"Forgejo 保留最新 {KEEP_TAGS} 个 wf tag。")
        print(f"安装：curl -fsSL \"${{WF_FORGEJO_BASE}}/xzc/ai-coding-toolkit/"
              f"releases/download/latest/install.py\" | python3 -")
        return 0
    except ReleaseError as exc:
        sys.stderr.write(f"BLOCKED  {exc}\n")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
