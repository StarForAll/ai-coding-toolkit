#!/usr/bin/env python3
"""662 审查适配副本：两副本随发行投放、进安装清单、随卸载移除。

obligation（设计稿 §7.4「审查适配交付」）：reviewer 侧与 action 侧各一份，作为**发行资产**
交付，纳入安装清单与三方升级，随卸载移除——不是"仓库存着就算交付"。

注入形态：投放时跳过审查副本（清单仍是全量）。
"""
import json
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _harness as H

SID = "sess-662"
COPIES = ("wf-review", "wf-review-action")
COPIES = ("wf-review", "wf-review-action")


def drop_copies(source):
    """注入：造一个**清单与树都不含审查副本**的发行（即"未交付适配副本"）。"""
    import hashlib
    import importlib.util
    import shutil

    manifest_path = os.path.join(source, "wf-release.json")
    data = json.load(open(manifest_path, encoding="utf-8"))
    kept = []
    for asset in data.get("assets") or []:
        if any(name in (asset.get("source_path") or "") or name in (asset.get("target_relative") or "")
               for name in COPIES):
            continue
        kept.append(asset)
    data["assets"] = kept
    for base in ("wf-release/skills", "skills"):
        for name in COPIES:
            target = os.path.join(source, base, name)
            if os.path.isdir(target):
                shutil.rmtree(target)
    spec = importlib.util.spec_from_file_location("wf_i", os.path.join(source, "install.py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    data["compatibility"]["rules_digest"] = module.compute_rules_digest(data)
    json.dump(data, open(manifest_path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    for cmd in (["git", "add", "-A"], ["git", "commit", "-qm", "without review copies"],
                ["git", "tag", "-f", "wf-v0.1.0"]):
        subprocess.run(cmd, cwd=source, check=True, capture_output=True)


def skills_root(project):
    return os.path.join(project, ".agents/skills")


def installed_assets(project):
    path = os.path.join(project, ".wf/install/installation.json")
    record = json.load(open(path, encoding="utf-8"))
    return [entry.get("target") or "" for entry in record.get("assets") or []]


def check():
    root, _lib, _payload = H.stage()
    source = H.release_source(root)
    if os.environ.get("WF_REPRO_INJECT") == "1":
        drop_copies(source)
    project = H.deploy(root)
    H.ensure_project_config(project)
    problems = []
    assets = installed_assets(project)
    for name in COPIES:
        path = os.path.join(skills_root(project), name, "SKILL.md")
        if not os.path.isfile(path):
            problems.append(f"投放后缺副本：{name}")
        if not any(name in item for item in assets):
            problems.append(f"安装清单未登记副本：{name}")
    if problems:
        raise H.TargetFailure("；".join(problems))

    # 卸载后随资产移除
    preview = subprocess.run([H.WF_PYTHON, os.path.join(project, ".wf/bin/uninstall.py"),
                              "--project", project], capture_output=True, text=True)
    token = re.search(r"令牌：([0-9a-f]{32})", preview.stdout or "")
    if not token:
        raise H.Precondition("卸载预览未给令牌")
    subprocess.run([H.WF_PYTHON, os.path.join(project, ".wf/bin/uninstall.py"), "--project", project,
                    "--apply", "--nonce", token.group(1)], capture_output=True, text=True,
                   input=token.group(1) + "\n")
    for name in COPIES:
        if os.path.exists(os.path.join(skills_root(project), name)):
            problems.append(f"卸载后副本仍在：{name}")
    if problems:
        raise H.TargetFailure("；".join(problems))
    return None


if __name__ == "__main__":
    sys.exit(H.main(check))
