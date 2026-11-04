#!/usr/bin/env python3
"""CP4 / A8：卸载列出并保留本地偏离。"""
import json, os, re, subprocess, sys

F = "/tmp/wf-fixtures/fu"
SKILLS = "/tmp/wf-fixtures/skills-u"
results = []


def rec(name, expected, actual, ok):
    results.append({"case": name, "expected": expected, "actual": actual, "pass": bool(ok)})
    print(f"[{'PASS' if ok else 'FAIL'}] {name}: {actual}")


skill = os.path.join(SKILLS, "wf-start", "SKILL.md")
workflow = os.path.join(F, ".wf/workflows/task-flow.md")
with open(skill, "a", encoding="utf-8") as handle:
    handle.write("\n本地修改：仅用于 CP4 偏离用例。\n")
with open(workflow, "a", encoding="utf-8") as handle:
    handle.write("\n本地修改：仅用于 CP4 偏离用例。\n")

preview = subprocess.run(["/usr/bin/python3", os.path.join(F, ".wf/bin/uninstall.py"),
                          "--project", F], capture_output=True, text=True)
rec("A8 预览列出本地偏离", "列 2 项偏离",
    f"count={len(re.findall('local content differs', preview.stdout))}",
    len(re.findall("local content differs", preview.stdout)) == 2)
token = re.search(r"令牌：([0-9a-f]{32})", preview.stdout)
rec("A8 预览给出令牌", "32 位十六进制", token.group(1)[:8] if token else None, bool(token))

apply_run = subprocess.run(["/usr/bin/python3", os.path.join(F, ".wf/bin/uninstall.py"),
                            "--project", F, "--apply", "--nonce", token.group(1)],
                           capture_output=True, text=True, input=token.group(1) + "\n")
rec("A8 卸载应用成功", "WF_OK", apply_run.stdout.splitlines()[0] if apply_run.stdout else apply_run.stderr[-200:],
    "WF_OK" in apply_run.stdout)
rec("A8 偏离的 skill 未被删除", "文件仍存在且含本地修改",
    os.path.exists(skill) and "本地修改" in open(skill, encoding="utf-8").read(),
    os.path.exists(skill) and "本地修改" in open(skill, encoding="utf-8").read())
rec("A8 偏离的项目资产未被删除", "文件仍存在",
    os.path.exists(workflow), os.path.exists(workflow))
rec("A8 未修改的资产被移除", ".wf/bin/wf.py 已移除",
    not os.path.exists(os.path.join(F, ".wf/bin/wf.py")),
    not os.path.exists(os.path.join(F, ".wf/bin/wf.py")))
rec("A8 保留项写入报告", "preserved 含 2 项",
    re.search(r"保留本地偏离：(\d+) 项", apply_run.stdout).group(1),
    "保留本地偏离：2 项" in apply_run.stdout)
rec("A8 数据与安装记录保留", ".wf/install/installation.json 与 writer.json 仍在",
    os.path.exists(os.path.join(F, ".wf/install/installation.json"))
    and os.path.exists(os.path.join(F, ".wf/writer.json")),
    os.path.exists(os.path.join(F, ".wf/install/installation.json"))
    and os.path.exists(os.path.join(F, ".wf/writer.json")))
rec("A8 托管段移除且保留 /.wf-lock 裸行", ".gitignore 无标记串但含 /wf-lock 行",
    open(os.path.join(F, ".gitignore"), encoding="utf-8").read().splitlines(),
    "# wf-managed-v1" not in open(os.path.join(F, ".gitignore"), encoding="utf-8").read()
    and "/.wf-lock" in open(os.path.join(F, ".gitignore"), encoding="utf-8").read().splitlines())

json.dump(results, open("/tmp/cp4_a8_results.json", "w"), ensure_ascii=False, indent=2)
print("saved", len(results), "cases;", sum(1 for r in results if r["pass"]), "passed")
