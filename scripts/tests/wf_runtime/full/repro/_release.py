"""发行源副本脚手架（供需要「注入安装器」的用例使用）。

`install.py` 不在项目内，而在发行源里；`--release-ref` 又要求源仓库带 tag，
所以注入只能落在**源仓库副本**上。本文件把 `docs/workflows/wf-release/` 复制到临时目录、
初始化成带同样 tag 的仓库，返回可注入的源路径。
"""
import os
import shutil
import subprocess
import sys

import _harness as H

TAG = "wf-v0.1.0"


def source_repo(root, tag=TAG):
    dest = os.path.join(root, "release-src")
    shutil.copytree(H.RELEASE, dest,
                    ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    for cmd in (["git", "init", "-q"],
                ["git", "config", "user.email", "r@example.com"],
                ["git", "config", "user.name", "r"],
                ["git", "add", "-A"],
                ["git", "commit", "-qm", "release snapshot"],
                ["git", "tag", tag]):
        subprocess.run(cmd, cwd=dest, check=True, capture_output=True)
    return dest


def installer(source, project):
    """用给定源仓库安装/重装到 project，返回 CompletedProcess。"""
    return subprocess.run([sys.executable, os.path.join(source, "install.py"),
                           "--target", project, "--release-ref", f"refs/tags/{TAG}",
                           "--source", source, "--platform", "dsh", "--confirm"],
                          capture_output=True, text=True)


def patch_asset(source, rel_path, old, new):
    """改源仓库里的文件，并同步它在清单中的摘要（模拟「一个自洽的另一版发行」）。

    `.wf/install` 侧只核资产摘要，所以两处必须一起改；`release_only` 资产（如 install.py）
    不进目标项目，因此不会破坏「重装无变化」。
    """
    import hashlib
    import json

    path = os.path.join(source, rel_path)
    H.patch(path, old, new)
    manifest_path = os.path.join(source, "wf-release.json")
    data = json.load(open(manifest_path, encoding="utf-8"))
    digest = "sha256:" + hashlib.sha256(open(path, "rb").read()).hexdigest()
    for asset in data.get("assets") or []:
        if asset.get("source_path") == rel_path:
            asset["digest"] = digest
    # rules_digest 覆盖全部资产与兼容声明：改一处必须重算，否则安装器会判「声明≠重算」
    import importlib.util

    spec = importlib.util.spec_from_file_location("wf_installer", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    data.setdefault("compatibility", {})["rules_digest"] = module.compute_rules_digest(data)
    json.dump(data, open(manifest_path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    # 2026-11-06：安装器改为按 **tag 提交树** 核内容，因此注入必须进提交并移动 tag，
    # 否则「工作树改了但提交没改」会先被发行身份校验挡住（那不是我们要测的东西）。
    for cmd in (["git", "add", "-A"], ["git", "commit", "-qm", "patched asset"],
                ["git", "tag", "-f", TAG]):
        subprocess.run(cmd, cwd=source, check=True, capture_output=True)
