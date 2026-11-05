#!/usr/bin/env python3
"""第五十七轮 R92：--platform 取代 --skill-root 的定点用例。"""
import json, os, subprocess, sys, tempfile
sys.path.insert(0, "/tmp")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import wfdrive

RELEASE = "/tmp/wf-fixtures/release-repo"
results = []


def rec(name, expected, actual, ok):
    results.append({"case": name, "expected": actual, "actual": actual, "pass": bool(ok)})
    print(f"[{'PASS' if ok else 'FAIL'}] {name}: {actual}")


def install(target, *platforms, extra=()):
    args = ["/softwares/python/bin/python3", os.path.join(RELEASE, "install.py"),
            "--target", target, "--release-ref", "refs/tags/wf-v0.1.0", "--source", RELEASE]
    for name in platforms:
        args += ["--platform", name]
    args += list(extra)
    return subprocess.run(args, capture_output=True, text=True)


def fresh(name):
    target = os.path.join(tempfile.mkdtemp(prefix=f"wf-r92-{name}-"), "p")
    os.makedirs(target)
    subprocess.run(["git", "init", "-q"], cwd=target, capture_output=True)
    subprocess.run(["git", "config", "user.email", "t@e.c"], cwd=target, capture_output=True)
    subprocess.run(["git", "config", "user.name", "t"], cwd=target, capture_output=True)
    subprocess.run(["git", "commit", "-q", "--allow-empty", "-m", "init"], cwd=target, capture_output=True)
    return target


CONFIRM = ("--confirm", "--host-id", "dsh", "--verify-capability",
           "--capability-evidence", "kind=reentry;ref=r92;by=test")

# 1) 共享层平台：dsh → 项目内 .agents/skills
t1 = fresh("dsh")
r1 = install(t1, "dsh", extra=CONFIRM)
rec("R92 dsh 装在项目内 .agents/skills", "WF_OK 且目录存在",
    f"{'WF_OK' if r1.returncode == 0 else r1.stdout[-80:]}",
    r1.returncode == 0 and os.path.isdir(os.path.join(t1, ".agents/skills/wf-start")))
record = json.load(open(os.path.join(t1, ".wf/install/installation.json"), encoding="utf-8"))
rec("R92b 记录里 roots 为相对路径、platforms 已写入", ".agents/skills + dsh",
    f"{record.get('roots')} / {record.get('platforms')}",
    record.get("roots") == [".agents/skills"] and record.get("platforms") == ["dsh"])

# 2) 仅自有目录的平台：claudecode → .claude/skills
t2 = fresh("claude")
r2 = install(t2, "claudecode", extra=CONFIRM)
rec("R92 claudecode 只落在 .claude/skills", "WF_OK 且无 .agents/skills",
    f"{r2.returncode}/{os.path.isdir(os.path.join(t2, '.agents/skills'))}",
    r2.returncode == 0 and os.path.isdir(os.path.join(t2, ".claude/skills/wf-start"))
    and not os.path.isdir(os.path.join(t2, ".agents/skills")))

# 3) 多平台并集
t3 = fresh("both")
r3 = install(t3, "dsh", "claudecode", extra=CONFIRM)
rec("R92 多平台取并集", "两个目录都有",
    f"{os.path.isdir(os.path.join(t3, '.agents/skills'))}/{os.path.isdir(os.path.join(t3, '.claude/skills'))}",
    r3.returncode == 0 and os.path.isdir(os.path.join(t3, ".agents/skills/wf-start"))
    and os.path.isdir(os.path.join(t3, ".claude/skills/wf-start")))

# 4) 未知平台拒绝
t4 = fresh("unknown")
r4 = install(t4, "sublime", extra=CONFIRM)
rec("R92 未知平台被拒", "WF_PATH_INVALID 且未投放",
    f"{'WF_PATH_INVALID' if 'WF_PATH_INVALID' in r4.stdout else r4.stdout[-60:]}/"
    f"{os.path.isdir(os.path.join(t4, '.wf'))}",
    "WF_PATH_INVALID" in r4.stdout and not os.path.isdir(os.path.join(t4, ".wf")))

# 5) 省略平台拒绝
t5 = fresh("none")
r5 = install(t5, extra=CONFIRM)
rec("R92 省略平台被拒", "WF_PATH_INVALID",
    "WF_PATH_INVALID" if "WF_PATH_INVALID" in r5.stdout else r5.stdout[-60:],
    "WF_PATH_INVALID" in r5.stdout)

# 6) --skill-root 不再被接受
t6 = fresh("legacy")
r6 = subprocess.run(["/softwares/python/bin/python3", os.path.join(RELEASE, "install.py"),
                     "--target", t6, "--release-ref", "refs/tags/wf-v0.1.0", "--source", RELEASE,
                     "--skill-root", "/tmp/whatever"], capture_output=True, text=True)
rec("R92 --skill-root 已移除", "argparse 拒绝",
    "unrecognized" in (r6.stderr + r6.stdout),
    "unrecognized" in (r6.stderr + r6.stdout))

# 7) 技能副本算框架资产：安装后 Check 不被判成未归属改动
t7 = fresh("scope")
install(t7, "dsh", extra=CONFIRM)
sys.path.insert(0, "/home/xzc/projects/personal/ai-coding-toolkit/docs/workflows/新项目开发工作流/payload/lib")
from wflib import scope as wf_scope

installed = wf_scope.installed_asset_paths(t7)
rec("R92 安装产物登记为项目内路径", "含 .agents/skills/wf-start/SKILL.md",
    sorted(installed)[:2], ".agents/skills/wf-start/SKILL.md" in installed)
task = {"id": "2026-x", "plan": {"touch_paths": ["pkg/**"]}}
buckets = wf_scope.classify_candidates(t7, task, receipts=[])["buckets"]
rec("R92b 技能副本不被算作任务交付物", "落在 b 桶",
    f"b={len(buckets['b'])} c={len(buckets['c'])}",
    not buckets["c"] and any(p.startswith(".agents/skills/") for p in buckets["b"]))

# 8) 三种写法等价：重复、空格多值、逗号分隔
for label, extra in (("重复 flag", ["--platform", "codex", "--platform", "claudecode"]),
                     ("空格多值", ["--platform", "codex", "claudecode"]),
                     ("逗号分隔", ["--platform", "codex,claudecode"])):
    t = fresh("form")
    args = ["/softwares/python/bin/python3", os.path.join(RELEASE, "install.py"),
            "--target", t, "--release-ref", "refs/tags/wf-v0.1.0", "--source", RELEASE] + extra + list(CONFIRM)
    r = subprocess.run(args, capture_output=True, text=True)
    ok = (r.returncode == 0 and os.path.isdir(os.path.join(t, ".agents/skills/wf-start"))
          and os.path.isdir(os.path.join(t, ".claude/skills/wf-start")))
    rec(f"R92 platform {label}", "两个目录都在", f"{r.returncode}/{'OK' if ok else r.stdout[-60:]}", ok)

json.dump(results, open("/tmp/r89_results.json", "w"), ensure_ascii=False, indent=2)
print("saved", sum(1 for r in results if r["pass"]), "/", len(results))
