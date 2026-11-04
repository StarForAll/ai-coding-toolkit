#!/usr/bin/env python3
"""第三十六轮 R72：卸载入口的清单一致性与资产边界。"""
import json, os, re, shutil, subprocess, sys
F_BASE = "/tmp/wf-fixtures/r72"
results = []


def rec(name, expected, actual, ok):
    results.append({"case": name, "expected": expected, "actual": actual, "pass": bool(ok)})
    print(f"[{'PASS' if ok else 'FAIL'}] {name}: {actual}")


def make_project(name):
    target = os.path.join(F_BASE, name)
    shutil.rmtree(target, ignore_errors=True)
    os.makedirs(target)
    subprocess.run(["git", "init", "-q"], cwd=target, capture_output=True)
    subprocess.run(["/softwares/python/bin/python3",
                    "/home/xzc/projects/personal/ai-coding-toolkit/docs/workflows/新项目开发工作流/payload/install.py",
                    "--target", target, "--release-ref", "refs/tags/wf-v0.1.0",
                    "--source", "/tmp/wf-fixtures/release-repo",
                    "--skill-root", os.path.join(target, "skills"),
                    "--confirm", "--host-id", "dsh", "--verify-capability",
                "--capability-evidence", "kind=reentry;ref=夹具内同会话重入观察;by=test fixture"],
                   capture_output=True, text=True)
    return target


def run_uninstall(target):
    """同进程：读到令牌提示后输入该令牌。"""
    proc = subprocess.Popen(["/usr/bin/python3", os.path.join(target, ".wf/bin/uninstall.py"),
                             "--project", target, "--apply"],
                            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    buffer = ""
    while "请输入令牌确认" not in buffer:
        char = proc.stdout.read(1)
        if not char:
            break
        buffer += char
    token = re.search(r"令牌：([0-9a-f]{32})", buffer)
    if proc.poll() is not None:
        return proc.returncode if proc.returncode is not None else 1, buffer
    try:
        proc.stdin.write((token.group(1) if token else "0" * 32) + "\n")
        proc.stdin.flush()
    except BrokenPipeError:
        pass
    rest = proc.stdout.read()
    proc.wait(timeout=120)
    return proc.returncode, buffer + rest


os.makedirs(F_BASE, exist_ok=True)

# ① 正常项目仍可卸载
clean = make_project("clean")
rc, out = run_uninstall(clean)
rec("1 正常项目可卸载", "WF_OK", f"rc={rc}", rc == 0 and "WF_OK" in out)

# ② 清单路径越界（../outside.txt）→ 整批拒绝
escaped = make_project("escaped")
manifest_path = os.path.join(escaped, ".wf/install/release-manifest.json")
manifest = json.load(open(manifest_path, encoding="utf-8"))
victim = os.path.join(F_BASE, "outside-user.txt")
open(victim, "w").write("用户文件\n")
manifest["assets"].append({"target_class": "project_wf", "target_relative": "../outside-user.txt",
                           "digest": None})
json.dump(manifest, open(manifest_path, "w", encoding="utf-8"), ensure_ascii=False)
rc, out = run_uninstall(escaped)
rec("2 越界条目整批拒绝", "WF_ASSET_DECISION", f"rc={rc}",
    "WF_ASSET_DECISION" in out)
rec("2b 目标外文件未被删", "仍在", os.path.exists(victim), os.path.exists(victim))

# ③ 清单被改动（摘要不符）→ 拒绝
tampered = make_project("tampered")
manifest_path = os.path.join(tampered, ".wf/install/release-manifest.json")
manifest = json.load(open(manifest_path, encoding="utf-8"))
manifest["assets"] = [asset for asset in manifest["assets"] if asset.get("target_class") != "skill_root"]
json.dump(manifest, open(manifest_path, "w", encoding="utf-8"), ensure_ascii=False)
rc, out = run_uninstall(tampered)
rec("3 清单摘要不符即拒绝", "WF_ASSET_DECISION", f"rc={rc}", "WF_ASSET_DECISION" in out)

# ④ 未知资产类别 → 拒绝
weird = make_project("weird")
manifest_path = os.path.join(weird, ".wf/install/release-manifest.json")
manifest = json.load(open(manifest_path, encoding="utf-8"))
manifest["assets"].append({"target_class": "outside_root", "target_relative": "x", "digest": None})
json.dump(manifest, open(manifest_path, "w", encoding="utf-8"), ensure_ascii=False)
rc, out = run_uninstall(weird)
rec("4 未知资产类别被拒", "WF_ASSET_DECISION", f"rc={rc}", "WF_ASSET_DECISION" in out)


# ⑤ 安装记录缺 summary_digest / 空值 → 拒绝
for label, mutate in (("missing", "drop"), ("empty", "blank")):
    target = make_project(f"digest-{label}")
    install_path = os.path.join(target, ".wf/install/installation.json")
    install = json.load(open(install_path, encoding="utf-8"))
    if mutate == "drop":
        install.pop("manifest_digest", None)
    else:
        install["manifest_digest"] = ""
    json.dump(install, open(install_path, "w", encoding="utf-8"), ensure_ascii=False)
    rc, out = run_uninstall(target)
    removed = not os.path.exists(os.path.join(target, ".wf/templates/spec/index.md"))
    rec(f"5 安装记录摘要{label} → 拒绝且不删", "WF_ASSET_DECISION 且资产仍在",
        f"rc={rc} removed={removed}", "WF_ASSET_DECISION" in out and not removed)

json.dump(results, open("/tmp/r72_results.json", "w"), ensure_ascii=False, indent=2)
print("saved", sum(1 for r in results if r["pass"]), "/", len(results))

