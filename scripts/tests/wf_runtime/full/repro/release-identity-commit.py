#!/usr/bin/env python3
"""652 发行身份：资产摘要必须相对 **tag 提交** 核验，而不是相对工作树。

obligation（设计稿 §7.2「发行身份（唯一定义）」）：一个发行版本绑定不可变源提交与资产清单，
安装器解析引用到提交后**按该提交的内容**核对清单；「同版异内容」要相对提交成立，
否则脏检出（或被人一致地重算过清单）能冒充同一发行。

注入形态：退回「相对工作树核摘要」（提交树与工作树不一致时仍放行）。
"""
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _harness as H
import _release as R

FROM = '    problems = verify_assets(source, manifest, commit=commit)\n'
TO = '    problems = verify_assets(source, manifest)  # 注入：相对工作树核摘要\n'


def git(source, *args):
    return subprocess.run(["git", *args], cwd=source, capture_output=True, text=True, check=False).stdout


def check():
    root, _lib, _payload = H.stage()
    source = R.source_repo(root)
    if os.environ.get("WF_REPRO_INJECT") == "1":
        # 注入必须同时同步清单摘要与 rules_digest，否则会被 install.py 自身摘要挡住（那是另一回事）
        R.patch_asset(source, "install.py", FROM, TO)
    # 篡改工作树里的一份资产，并把清单摘要改成与工作树一致（自洽的「假同版」）
    target = os.path.join(source, "wf-release", "workflows", "task-flow.md")
    if not os.path.isfile(target):
        target = os.path.join(source, "wf-release.json")
    with open(target, "a", encoding="utf-8") as handle:
        handle.write("\n<!-- 篡改 -->\n")
    import hashlib

    digest = "sha256:" + hashlib.sha256(open(target, "rb").read()).hexdigest()
    manifest_path = os.path.join(source, "wf-release.json")
    data = json.load(open(manifest_path, encoding="utf-8"))
    rel = os.path.relpath(target, source).replace(os.sep, "/")
    for asset in data.get("assets") or []:
        if asset.get("source_path") == rel:
            asset["digest"] = digest
    import importlib.util

    spec = importlib.util.spec_from_file_location("wf_installer", os.path.join(source, "install.py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    data.setdefault("compatibility", {})["rules_digest"] = module.compute_rules_digest(data)
    json.dump(data, open(manifest_path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)

    project = os.path.join(root, "proj")
    os.makedirs(project, exist_ok=True)
    result = subprocess.run([sys.executable, os.path.join(source, "install.py"), "--target", project,
                             "--release-ref", f"refs/tags/{R.TAG}", "--source", source,
                             "--platform", "dsh", "--confirm"], capture_output=True, text=True)
    if result.returncode == 0:
        raise H.TargetFailure("工作树被篡改且清单同步后仍被当作同一发行（未按 tag 提交核内容）")
    text = f"{result.stdout}\n{result.stderr}"
    if "WF_RELEASE_CONFLICT" not in text:
        raise H.Precondition(f"拒绝码不是 WF_RELEASE_CONFLICT：{text[-200:]}")
    return None


if __name__ == "__main__":
    sys.exit(H.main(check))
