#!/usr/bin/env python3
"""R5（install.py 记录形态下的卸载）与 R3（锁部分标记的人工出口）。"""
import json, os, re, subprocess, sys
sys.path.insert(0, "/tmp")
import wfdrive

F5 = "/tmp/wf-fixtures/f5"
SKILLS = "/tmp/wf-fixtures/skills-f5"
REPO = "/tmp/wf-fixtures/release-repo"
results = []


def rec(name, expected, actual, ok):
    results.append({"case": name, "expected": expected, "actual": actual, "pass": bool(ok)})
    print(f"[{'PASS' if ok else 'FAIL'}] {name}: {actual}")


# ---------------- R5：install.py → 偏离 → uninstall ----------------
skill = os.path.join(SKILLS, "wf-start", "SKILL.md")
workflow = os.path.join(F5, ".wf/workflows/task-flow.md")
with open(skill, "a", encoding="utf-8") as handle:
    handle.write("\n本地修改：R5 偏离用例。\n")
with open(workflow, "a", encoding="utf-8") as handle:
    handle.write("\n本地修改：R5 偏离用例。\n")

preview = subprocess.run(["/usr/bin/python3", os.path.join(F5, ".wf/bin/uninstall.py"), "--project", F5],
                         capture_output=True, text=True)
rec("R5 正式记录下预览可运行", "输出预览且列出 2 项偏离",
    f"deviations={len(re.findall('local content differs', preview.stdout))}",
    preview.returncode == 0 and len(re.findall("local content differs", preview.stdout)) == 2)
token = re.search(r"令牌：([0-9a-f]{32})", preview.stdout)
apply_run = subprocess.run(["/usr/bin/python3", os.path.join(F5, ".wf/bin/uninstall.py"), "--project", F5,
                            "--apply", "--nonce", token.group(1) if token else "0" * 32],
                           capture_output=True, text=True,
                           input=(token.group(1) + "\n") if token else "")
rec("R5 正式记录下卸载应用", "WF_OK",
    apply_run.stdout.strip().splitlines()[-3:] if apply_run.stdout else apply_run.stderr[-200:],
    "WF_OK" in apply_run.stdout)
rec("R5 偏离默认保留", "两处本地修改仍在",
    os.path.exists(skill) and os.path.exists(workflow),
    os.path.exists(skill) and os.path.exists(workflow))
rec("R5 未改资产被移除", ".wf/bin/wf.py 已移除",
    not os.path.exists(os.path.join(F5, ".wf/bin/wf.py")),
    not os.path.exists(os.path.join(F5, ".wf/bin/wf.py")))
rec("R5 数据与安装记录保留", "安装记录仍在",
    os.path.exists(os.path.join(F5, ".wf/install/installation.json")),
    os.path.exists(os.path.join(F5, ".wf/install/installation.json")))
gitignore = open(os.path.join(F5, ".gitignore"), encoding="utf-8").read() if os.path.exists(os.path.join(F5, ".gitignore")) else ""
rec("R5 托管段移除但保留 /.wf-lock 行", "无托管标记且含 /.wf-lock",
    f"marker={'wf-managed-v1' in gitignore} lock_line={'/.wf-lock' in gitignore.splitlines()}",
    "wf-managed-v1" not in gitignore and "/.wf-lock" in gitignore.splitlines())

# ---------------- R3：锁部分标记 ----------------
F3 = "/tmp/wf-fixtures/f3"
lock_path = os.path.join(F3, ".wf-lock")
with open(lock_path, "wb") as handle:
    handle.write(b"wf-lock")  # 部分标记（缺 -v1 与换行）

proc = subprocess.run(["/usr/bin/python3", os.path.join(F3, ".wf/bin/wf.py"), "task-new", "--kind", "ordinary",
                       "--title", "R3", "--template", os.path.join(F3, ".wf/templates/task"), "--json"],
                      cwd=F3, capture_output=True, text=True,
                      input=json.dumps({"session": {"provider": "host",
                                                    "identity": {"host_id": "dsh", "session_id": "sess-R3"},
                                                    "instance_id": None,
                                                    "activation": {"enabled": True, "start_source": "test",
                                                                   "enabled_at": "2026-11-03T20:00:00.000000Z"}},
                                        "inputs": {"generation": 1}}))
rec("R3 部分标记返回能力不可用", "WF_CAPABILITY_UNAVAILABLE",
    f"code={'WF_CAPABILITY_UNAVAILABLE' in proc.stdout} rc={proc.returncode}",
    "WF_CAPABILITY_UNAVAILABLE" in proc.stdout)
preview = subprocess.run(["/usr/bin/python3", os.path.join(F3, ".wf/bin/repair.py"), "--project", F3],
                         capture_output=True, text=True)
token = re.search(r"令牌：([0-9a-f]{32})", preview.stdout)
apply_run = subprocess.run(["/usr/bin/python3", os.path.join(F3, ".wf/bin/repair.py"), "--project", F3,
                            "--apply", "--nonce", token.group(1) if token else "0" * 32],
                           capture_output=True, text=True,
                           input=(token.group(1) + "\n") if token else "")
rec("R3 修复入口在锁不可识别时拒绝应用", "WF_CAPABILITY_UNAVAILABLE",
    f"rc={apply_run.returncode} code={'WF_CAPABILITY_UNAVAILABLE' in apply_run.stdout}",
    apply_run.returncode != 0 and "WF_CAPABILITY_UNAVAILABLE" in apply_run.stdout)
flow = open(os.path.join(F3, ".wf/workflows/maintenance-flow.md"), encoding="utf-8").read()
rec("R3 清理顺序写入维护流程文档", "含锁人工清理顺序与空锁自愈说明",
    f"order={'/.wf-lock' in flow and '确认无 wf 进程' in flow} no_self_heal={'自动补写标记' not in flow}",
    "确认无 wf 进程" in flow and "自动补写标记" not in flow and "排他创建" in flow)
with open(lock_path, "wb") as handle:
    handle.write(b"wf-lock-v1\n")
proc = subprocess.run(["/usr/bin/python3", os.path.join(F3, ".wf/bin/wf.py"), "status"],
                      cwd=F3, capture_output=True, text=True)
rec("R3 人工清理后恢复正常", "status 正常输出",
    f"rc={proc.returncode}", proc.returncode == 0)

json.dump(results, open("/tmp/r35_results.json", "w"), ensure_ascii=False, indent=2)
print("saved", len(results), "cases;", sum(1 for r in results if r["pass"]), "passed")
