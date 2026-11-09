#!/usr/bin/env python3
"""687 分支来源未确认：目标在其他分支存在时必须待裁，且预览零写入。

obligation（设计稿 §7.1「分支来源核对」）：投放前若同名资产在当前分支缺失、但在其他分支存在，
必须报告具体分支并交人确认；未确认前**不继续投放**（预览不写任何文件）。

注入形态：跳过分支来源核对（直接按缺失继续）。
"""
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _harness as H

TARGET = ".agents/skills/wf-start/SKILL.md"


def git(project, *args):
    return subprocess.run(["git", *args], cwd=project, capture_output=True, text=True,
                          check=False).stdout.strip()


def check():
    root, _lib, _payload = H.stage()
    source = H.release_source(root)
    if os.environ.get("WF_REPRO_INJECT") == "1":
        H.patch(os.path.join(source, "install.py"),
                '    branch_findings = branch_source_findings(args.target, project_paths)\n',
                '    branch_findings = []  # 注入：跳过分支来源核对\n')
        import hashlib

        manifest_path = os.path.join(source, "wf-release.json")
        data = json.load(open(manifest_path, encoding="utf-8"))
        digest = "sha256:" + hashlib.sha256(open(os.path.join(source, "install.py"), "rb").read()).hexdigest()
        for asset in data.get("assets") or []:
            if asset.get("source_path") == "install.py":
                asset["digest"] = digest
        import importlib.util

        spec = importlib.util.spec_from_file_location("wf_i", os.path.join(source, "install.py"))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        data["compatibility"]["rules_digest"] = module.compute_rules_digest(data)
        json.dump(data, open(manifest_path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
        for cmd in (["git", "add", "-A"], ["git", "commit", "-qm", "patched"], ["git", "tag", "-f", "wf-v0.1.0"]):
            subprocess.run(cmd, cwd=source, check=True, capture_output=True)

    project = os.path.join(root, "proj")
    os.makedirs(project, exist_ok=True)
    git(project, "init", "-q")
    git(project, "config", "user.email", "r@example.com")
    git(project, "config", "user.name", "r")
    open(os.path.join(project, "README.md"), "w").write("x\n")
    git(project, "add", "-A")
    git(project, "commit", "-qm", "base")
    git(project, "checkout", "-q", "-b", "feature")
    os.makedirs(os.path.join(project, os.path.dirname(TARGET)), exist_ok=True)
    open(os.path.join(project, TARGET), "w").write("on feature\n")
    git(project, "add", "-A")
    git(project, "commit", "-qm", "skill on feature")
    current = git(project, "rev-parse", "--abbrev-ref", "HEAD")
    base = "master" if git(project, "branch", "--list", "master") else "main"
    git(project, "checkout", "-q", base)

    result = subprocess.run([sys.executable, os.path.join(source, "install.py"), "--target", project,
                             "--release-ref", "refs/tags/wf-v0.1.0", "--source", source,
                             "--platform", "dsh"], capture_output=True, text=True)
    problems = []
    text = f"{result.stdout}\n{result.stderr}"
    if result.returncode == 0:
        problems.append("分支来源未确认却继续投放")
    if "WF_ASSET_DECISION" not in text:
        problems.append(f"未以待裁码报告：{text[-160:]}")
    if "feature" not in text:
        problems.append("未报告存在该资产的分支名")
    if os.path.isdir(os.path.join(project, ".wf")):
        problems.append("待裁路径写了文件（预览应零写入）")
    if problems:
        raise H.TargetFailure("；".join(problems))
    return None


if __name__ == "__main__":
    sys.exit(H.main(check))
