#!/usr/bin/env python3
"""第五十七轮 R92 → 2026-11-23 改写：安装不再选平台（`--platform` 已移除），一次装齐全部。"""
import json, os, subprocess, sys, tempfile
import wfdrive
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

RELEASE = os.environ.get("WF_RELEASE_REPO") or ""
INSTALL_REF = os.environ.get("WF_INSTALL_REF") or ""
if not RELEASE or not INSTALL_REF:
    raise SystemExit("r89: 托管 runner 必须提供 WF_RELEASE_REPO 与 WF_INSTALL_REF"
                     "（候选/发行安装不能回退固定旧目录）")
results = []


def rec(name, expected, actual, ok):
    results.append({"case": name, "expected": actual, "actual": actual, "pass": bool(ok)})
    print(f"[{'PASS' if ok else 'FAIL'}] {name}: {actual}")


def install(target, *extra):
    args = [wfdrive.TOOL_PYTHON, os.path.join(RELEASE, "install.py"),
            "--target", target, "--release-ref", INSTALL_REF, "--source", RELEASE]
    args += [str(item) for item in extra]
    if "--json" not in args:
        args.append("--json")
    return subprocess.run(args, capture_output=True, text=True)


def fresh(name):
    target = os.path.join(tempfile.mkdtemp(prefix=f"wf-r92-{name}-"), "p")
    os.makedirs(target)
    subprocess.run(["git", "init", "-q"], cwd=target, capture_output=True)
    subprocess.run(["git", "config", "user.email", "t@e.c"], cwd=target, capture_output=True)
    subprocess.run(["git", "config", "user.name", "t"], cwd=target, capture_output=True)
    subprocess.run(["git", "commit", "-q", "--allow-empty", "-m", "init"], cwd=target, capture_output=True)
    return target


CONFIRM = ("--confirm",)
EXPECTED_ROOTS = [".agents/skills", ".claude/skills"]
EXPECTED_PLATFORMS = ["claudecode", "codex", "copilot", "cursor", "dsh", "geminicli", "pi", "zcode"]

# 1) 无平台参数即装齐：两个根都有副本
t1 = fresh("all")
r1 = install(t1, *CONFIRM)
record = json.load(open(os.path.join(t1, ".wf/install/installation.json"), encoding="utf-8"))
rec("R92 无参数安装即成功", "WF_OK", "WF_OK" if r1.returncode == 0 else r1.stdout[-120:],
    r1.returncode == 0)
rec("R92 全部支持平台一次装齐", json.dumps(EXPECTED_ROOTS),
    f"{record.get('roots')}",
    sorted(record.get("roots") or []) == EXPECTED_ROOTS)
rec("R92 记录把平台记成事实", json.dumps(EXPECTED_PLATFORMS),
    f"{record.get('platforms')}", record.get("platforms") == EXPECTED_PLATFORMS)
rec("R92 共享根与自有根都有技能副本", "两处 wf-start 都在",
    f"{os.path.isdir(os.path.join(t1, '.agents/skills/wf-start'))}/"
    f"{os.path.isdir(os.path.join(t1, '.claude/skills/wf-start'))}",
    os.path.isdir(os.path.join(t1, ".agents/skills/wf-start"))
    and os.path.isdir(os.path.join(t1, ".claude/skills/wf-start")))
_identity_problems = wfdrive.install_identity_problems(t1)
rec("R92c 安装来源为本次发行", "installation.json 的 version/ref/commit 与本发行一致",
    f"problems={_identity_problems or 'none'}", not _identity_problems)

# 2) 平台参数已移除：argparse 拒绝（与已删的 --skill-root 同型）
t2 = fresh("legacy_flag")
r2 = subprocess.run([wfdrive.TOOL_PYTHON, os.path.join(RELEASE, "install.py"),
                     "--target", t2, "--release-ref", INSTALL_REF, "--source", RELEASE,
                     "--platform", "dsh"], capture_output=True, text=True)
_r2_out = r2.stdout + r2.stderr
rec("R92 --platform 已移除", "WF_USAGE_INVALID 且未投放",
    f"{'WF_USAGE_INVALID' in _r2_out}/{os.path.isdir(os.path.join(t2, '.wf'))}/rc={r2.returncode}",
    r2.returncode != 0 and "WF_USAGE_INVALID" in _r2_out
    and not os.path.isdir(os.path.join(t2, ".wf")))
r3 = subprocess.run([wfdrive.TOOL_PYTHON, os.path.join(RELEASE, "install.py"),
                     "--target", t2, "--release-ref", INSTALL_REF, "--source", RELEASE,
                     "--skill-root", wfdrive.temp("whatever")], capture_output=True, text=True)
_r3_out = r3.stdout + r3.stderr
rec("R92 --skill-root 仍被移除", "WF_USAGE_INVALID",
    "WF_USAGE_INVALID" in _r3_out or "unrecognized" in _r3_out,
    r3.returncode != 0 and ("WF_USAGE_INVALID" in _r3_out or "unrecognized" in _r3_out))

# 3) 同一条命令重复执行：幂等成功、不取写权、不产生回执
before = json.load(open(os.path.join(t1, ".wf/writer.json"), encoding="utf-8"))
t3 = t1
r4 = install(t3, *CONFIRM)
after = json.load(open(os.path.join(t3, ".wf/writer.json"), encoding="utf-8"))
payload4 = json.loads(r4.stdout) if r4.stdout.strip().startswith("{") else {}
rec("R92 重复安装幂等", "WF_OK+noop+自检 clean",
    f"rc={r4.returncode} {(payload4.get('facts') or {}).get('noop')}/"
    f"{(payload4.get('facts') or {}).get('self_check')} out={r4.stdout[:120]}",
    r4.returncode == 0 and (payload4.get("facts") or {}).get("noop") is True
    and (payload4.get("facts") or {}).get("self_check") == "clean")
rec("R92 重复安装不取写权", "writer 记录逐字段不变", before == after, before == after)

# 4) 落点被改：拒绝覆盖并指向升级
t5 = fresh("drift")
install(t5, *CONFIRM)
victim = os.path.join(t5, ".agents/skills/wf-start/SKILL.md")
open(victim, "a", encoding="utf-8").write("\n本地改动\n")
r5 = install(t5, *CONFIRM)
rec("R92 落点与发行不一致时不覆盖", "WF_ASSET_DECISION 且文件保持本地内容",
    f"{(json.loads(r5.stdout).get('code') if r5.stdout.strip().startswith(chr(123)) else r5.returncode)}/"
    f"{'本地改动' in open(victim, encoding='utf-8').read()}",
    r5.returncode != 0 and "WF_ASSET_DECISION" in r5.stdout
    and "本地改动" in open(victim, encoding="utf-8").read())

# 5) 技能副本算框架资产：安装后 Check 不被判成未归属改动
t7 = fresh("scope")
install(t7, *CONFIRM)
sys.path.insert(0, wfdrive.LIB)
from wflib import scope as wf_scope

installed = wf_scope.installed_asset_paths(t7)
rec("R92 安装产物登记为项目内路径", "含 .agents/skills/wf-start/SKILL.md",
    sorted(installed)[:2], ".agents/skills/wf-start/SKILL.md" in installed)
task = {"id": "2026-x", "plan": {"touch_paths": ["pkg/**"]}}
buckets = wf_scope.classify_candidates(t7, task, receipts=[])["buckets"]
rec("R92b 技能副本不被算作任务交付物", "落在 b 桶",
    f"b={len(buckets['b'])} c={len(buckets['c'])}",
    not buckets["c"] and any(p.startswith(".agents/skills/") for p in buckets["b"]))

json.dump(results, open(wfdrive.temp("r89_results.json"), "w"), ensure_ascii=False, indent=2)
print("saved", sum(1 for r in results if r["pass"]), "/", len(results))
