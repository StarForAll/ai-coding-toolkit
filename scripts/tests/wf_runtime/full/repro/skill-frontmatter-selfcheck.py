#!/usr/bin/env python3
"""P2-4：投放后的自检必须解析 `SKILL.md` frontmatter（设计稿 §1.2）。

历史状态：`install.py::self_check` 核了清单摘要、运行时导入、步骤/处理器/命令面/桩轮次，
但不解析投放后的 `SKILL.md` frontmatter——「frontmatter 可解析」这一半从未被机检。

本用例把**摘要改坏之外**的那条路单独隔离出来：故意删掉某个 `SKILL.md` 的 `description`，
并把清单里该资产的摘要改成与新内容一致（于是摘要检查通过），只有 frontmatter 检查能抓到。
注入形态 = 关掉 frontmatter 分支（`kind == "skill"` 恒假）→ 该问题必须消失。
"""

import hashlib
import importlib.util
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _harness as H


def _digest(path):
    with open(path, "rb") as handle:
        return "sha256:" + hashlib.sha256(handle.read()).hexdigest()


def _load_installer(payload):
    spec = importlib.util.spec_from_file_location("wf_install_under_test",
                                                 os.path.join(payload, "install.py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def check():
    root, _lib, payload = H.stage()
    project = H.deploy(root)
    installer_path = os.path.join(payload, "install.py")
    if os.environ.get("WF_REPRO_INJECT") == "1":
        H.patch(installer_path,
                'elif asset.get("kind") == "skill":',
                'elif False:  # 注入：自检不解析 frontmatter\n                pass\n            elif False:')

    manifest_path = os.path.join(project, ".wf/install/release-manifest.json")
    with open(manifest_path, encoding="utf-8") as handle:
        manifest = json.load(handle)
    skills_root = os.path.join(project, ".agents/skills")

    # 找一个真实投放的 skill 资产，删掉它的 description 并把清单摘要改成一致
    target = None
    for asset in manifest.get("assets") or []:
        if asset.get("kind") != "skill" or asset.get("target_class") == "release_only":
            continue
        path = os.path.join(skills_root, *asset["target_relative"].split("/"))
        if os.path.isfile(path):
            target = (asset, path)
            break
    if target is None:
        raise H.Precondition("没有可用的已投放 skill 资产")
    asset, path = target
    with open(path, encoding="utf-8") as handle:
        lines = handle.read().splitlines()
    kept = [line for line in lines if not line.startswith("description:")]
    if len(kept) == len(lines):
        raise H.Precondition("该 SKILL.md 没有 description 行，夹具不成立")
    with open(path, "w", encoding="utf-8") as handle:
        handle.write("\n".join(kept) + "\n")
    asset["digest"] = _digest(path)

    installer = _load_installer(payload)
    problems = installer.self_check(project, manifest, [skills_root])
    frontmatter = [item for item in problems if "frontmatter" in str(item.get("reason") or "")]
    if not frontmatter:
        raise H.TargetFailure(f"frontmatter 已损坏但自检没有报告：problems={problems[:3]}")
    return None


if __name__ == "__main__":
    sys.exit(H.main(check))
