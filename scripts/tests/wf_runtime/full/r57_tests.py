#!/usr/bin/env python3
"""第二十轮 R57：配置非法一律阻断依赖判断（统一取值器 + 全消费者回扫）。"""
import datetime, hashlib, json, os, subprocess, sys
sys.path.insert(0, "/tmp")
sys.path.insert(0, "/home/xzc/projects/personal/ai-coding-toolkit/docs/workflows/新项目开发工作流/payload/lib")
import wfdrive
from wflib import config as wf_config

F = wfdrive.FIX
results = []
AT = "2026-11-04T17:00:00.000000Z"


def rec(name, expected, actual, ok):
    results.append({"case": name, "expected": expected, "actual": actual, "pass": bool(ok)})
    print(f"[{'PASS' if ok else 'FAIL'}] {name}: {actual}")


def wf(args, inputs=None, sid="sess-B1"):
    return wfdrive.run(args, inputs=inputs, sid=sid, show=False)


def dec(subject, choice, digest="sha256:" + "0" * 64):
    return {"source": "human", "at": AT, "subject": subject, "object_digest": digest,
            "choice": choice, "reason": "R57"}
def dfile(path, items):
    json.dump(items, open(path, "w"), ensure_ascii=False, indent=2); return path



def clean():
    subprocess.run(["git", "add", "-A"], cwd=F, capture_output=True)
    subprocess.run(["git", "commit", "-qm", "cap", "--allow-empty"], cwd=F, capture_output=True)


def write_gen():
    return json.load(open(os.path.join(F, ".wf/writer.json"), encoding="utf-8")).get("generation")


# ---------- 单元：统一取值器 ----------
rec("R57 键缺失取缺省", 90, wf_config.value_of({}, [], "spec_verify_days")[0],
    wf_config.value_of({}, [], "spec_verify_days") == (90, None))
bad_problem = [{"level": "field", "key": "spec_verify_days", "message": "spec_verify_days must be a positive integer"}]
rec("R57 非法正整数报问题", "must be a positive integer",
    wf_config.value_of({"spec_verify_days": "bad"}, bad_problem, "spec_verify_days")[1],
    wf_config.value_of({"spec_verify_days": "bad"}, bad_problem, "spec_verify_days")[0] is None)
rec("R57 0 也是非法", None, wf_config.value_of({"spec_output_codepoints": 0}, [], "spec_output_codepoints")[0],
    wf_config.value_of({"spec_output_codepoints": 0}, [], "spec_output_codepoints")[0] is None)
rec("R57 字符串布尔非法", None, wf_config.value_of({"tdd_default": "false"}, [], "tdd_default")[0],
    wf_config.value_of({"tdd_default": "false"}, [], "tdd_default")[0] is None)
struct = [{"level": "structure", "key": None, "message": "project config is not a JSON object"}]
rec("R57 配置整体非对象→依赖键非法", None, wf_config.value_of(None, struct, "spec_verify_days")[0],
    wf_config.value_of(None, struct, "spec_verify_days")[0] is None)

# ---------- 入口：配置为数组时 Check 不再按缺省放行 ----------
clean()
os.makedirs(os.path.join(F, "pkg"), exist_ok=True)
config_path = os.path.join(F, ".wf/project-config.json")
backup = open(config_path, encoding="utf-8").read()
open(config_path, "w").write("[]\n")
clean()
rc, payload, _ = wf(["task-new", "--kind", "ordinary", "--title", "R57 数组配置",
                     "--template", f"{F}/.wf/templates/task", "--json"], None, "sess-B1")
rec("R57 配置为数组→入口被拒", "非 WF_OK",
    f"{(payload or {}).get('code')} facts={json.dumps((payload or {}).get('facts'), ensure_ascii=False)[:120]}",
    (payload or {}).get("code") != "WF_OK")
open(config_path, "w", encoding="utf-8").write(backup)
clean()

# spec 输出预算非法 → spec 读取拒绝
cfg = json.loads(backup); cfg["spec_output_codepoints"] = 0
json.dump(cfg, open(config_path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
clean()
rc, payload, _ = wf(["spec", "--file", ".wf/spec/index.md", "--json"], {"generation": write_gen()}, "sess-B2")
rec("R57 预算 0 → spec 读取被拒", "WF_CAPABILITY_UNAVAILABLE", (payload or {}).get("code"),
    (payload or {}).get("code") == "WF_CAPABILITY_UNAVAILABLE")
open(config_path, "w", encoding="utf-8").write(backup)

json.dump(results, open("/tmp/r57_results.json", "w"), ensure_ascii=False, indent=2)
print("saved", sum(1 for r in results if r["pass"]), "/", len(results))
