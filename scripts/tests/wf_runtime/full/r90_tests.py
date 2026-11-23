#!/usr/bin/env python3
"""第五十八轮 R93：平台清单即身份事实（无 --host-id）+ 多 agent 覆盖保护。"""
import json, os, subprocess, sys, tempfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import wfdrive
F = wfdrive.FIX
results = []


def rec(name, expected, actual, ok):
    results.append({"case": name, "expected": expected, "actual": actual, "pass": bool(ok)})
    print(f"[{'PASS' if ok else 'FAIL'}] {name}: {actual}")


def wf(args, inputs=None, sid="sess-R93", instance=None):
    return wfdrive.run(args, inputs=inputs, sid=sid, show=False, instance_id=instance)


def gen():
    return json.load(open(os.path.join(F, ".wf/writer.json"), encoding="utf-8")).get("generation")


inst_path = os.path.join(F, ".wf/install/installation.json")
installation = json.load(open(inst_path, encoding="utf-8"))
rec("R93 安装记录只有 platforms、没有 session_profile", "platforms 非空且无 session_profile",
    f"{installation.get('platforms')}/{('session_profile' in installation)}",
    bool(installation.get("platforms")) and "session_profile" not in installation)

# 1) 未安装的宿主：写操作被拒、只读放行
backup = open(inst_path, encoding="utf-8").read()
muted = json.loads(backup); muted["platforms"] = ["codex"]
json.dump(muted, open(inst_path, "w", encoding="utf-8"), ensure_ascii=False)
rc, payload, _ = wf(["enable", "--json"], sid="sess-R93-dsh")
rec("R93 未安装的宿主写操作被拒", "WF_IDENTITY_UNRESOLVED",
    (payload or {}).get("code"), (payload or {}).get("code") == "WF_IDENTITY_UNRESOLVED")
rc_ro, ro_payload, _ = wf(["status", "--json"], sid="sess-R93-dsh")
rec("R93 未安装的宿主仍可只读诊断", "WF_OK", (ro_payload or {}).get("code"),
    (ro_payload or {}).get("code") == "WF_OK")
open(inst_path, "w", encoding="utf-8").write(backup)

# 2) 平台在册后同一宿主放行
rc, payload, _ = wf(["enable", "--json"], sid="sess-R93-dsh")
rec("R93 平台在册即放行（无登记、无证据）", "WF_OK", (payload or {}).get("code"), rc == 0)

# 3) 两个 agent 交替操作同一任务：串行 + 代次保护
rc, payload, _ = wf(["task-new", "--kind", "ordinary", "--title", "R93 多 agent",
                     "--template", f"{F}/.wf/templates/task", "--json"], sid="sess-R93-A")
facts = (payload or {}).get("facts") or {}
task_id, generation_a = facts.get("task_id"), facts.get("generation")
rec("R93 A 建任务并持写权", "WF_OK 且有代次", f"{task_id}/{generation_a}",
    rc == 0 and bool(generation_a))
rc_b, payload_b, _ = wf(["bind", "--task", task_id, "--json"], sid="sess-R93-B")
rec("R93 B 在 A 持写权时拿不到对象", "WF_WRITER_BUSY 或 WF_BINDING_MISMATCH（都不得放行）",
    (payload_b or {}).get("code"),
    (payload_b or {}).get("code") in ("WF_WRITER_BUSY", "WF_BINDING_MISMATCH"))
wf(["task-pause", "--task", task_id, "--reason", "交接", "--json"], {"generation": generation_a},
   sid="sess-R93-A")
wf(["writer", "release", "--json"], {"generation": generation_a}, sid="sess-R93-A")
rc_b2, payload_b2, _ = wf(["bind", "--task", task_id, "--json"], sid="sess-R93-B")
rec("R93 释放后 B 可接续同一任务", "WF_OK", (payload_b2 or {}).get("code"), rc_b2 == 0)
# A 拿旧代次再写 → 必须被代次闸拒绝
rc_a2, payload_a2, _ = wf(["task-resume", "--task", task_id, "--json"],
                          {"generation": generation_a}, sid="sess-R93-A")
rec("R93 A 用旧代次写被拒", "WF_GENERATION_STALE 或 WF_WRITER_BUSY",
    (payload_a2 or {}).get("code"),
    (payload_a2 or {}).get("code") in ("WF_GENERATION_STALE", "WF_WRITER_BUSY"))

# 4) 重复部署：安装面向全部平台，"追加平台"这一步已不存在——重跑只做只读核对/补齐
wf(["writer", "release", "--json"], {"generation": gen()}, sid="sess-R93-B")
dev_deploy = wfdrive.REPO + "/scripts/wf-dev-deploy.py"
before_assets = len(installation.get("assets") or [])
proc = subprocess.run([wfdrive.TOOL_PYTHON, dev_deploy, "--target", F,
                       "--confirm", "--json"], capture_output=True, text=True)
after = json.load(open(inst_path, encoding="utf-8"))
if proc.returncode != 0:
    print("   redeploy stdout:", (proc.stdout or proc.stderr)[-300:])
after_assets = len(after.get("assets") or [])
_writer_after = json.load(open(os.path.join(F, ".wf/writer.json"), encoding="utf-8"))
# 重跑**按来源判定**：夹具由候选发行安装时（release_ref=refs/tags/…），开发态工具跨来源
# 重跑必须被拒；由开发态部署时（ref=dev:…）则是只读核对/补齐。两种模式都要成立。
_recorded_ref = str(installation.get("release_ref") or "")
_cross_source = bool(_recorded_ref) and not _recorded_ref.startswith("dev:")
_writer_same = _writer_after.get("state") == "idle"
if _cross_source:
    _ok = proc.returncode != 0 and "WF_ASSET_DECISION" in ((proc.stdout or "") + (proc.stderr or ""))
    _expect = "跨来源重跑被拒（WF_ASSET_DECISION）且 writer 空闲、资产不变"
else:
    _ok = (proc.returncode == 0
           and sorted(after.get("platforms") or []) == sorted(installation.get("platforms") or [])
           and after_assets == before_assets)
    _expect = "platforms 不变；assets 数量不变；writer 保持 idle"
rec("R93 重复部署按来源判定", _expect,
    f"cross_source={_cross_source} rc={proc.returncode} assets={before_assets}->{after_assets} "
    f"state={_writer_after.get('state')}",
    _ok and _writer_same and after_assets == before_assets)

# ---- R4-1/R4-2（2026-11-05 第四/五轮复审）：来源一致性、零写入、代次类型 ----
_writer_path = os.path.join(F, ".wf/writer.json")
_inst_snap = open(inst_path, encoding="utf-8").read()
_writer_snap = open(_writer_path, encoding="utf-8").read()


def _json_fact(text):
    for line in reversed((text or "").splitlines()):
        line = line.strip()
        if line.startswith("{"):
            try:
                return json.loads(line)
            except ValueError:
                return None
    return None


def _tree_snapshot():
    """目标项目内的相对路径集合（目录 + 文件），用于证明拒绝路径没有创建任何新对象。"""
    found = []
    for base, dirs, files in os.walk(F):
        dirs[:] = [d for d in dirs if d not in (".git",)]
        rel_base = os.path.relpath(base, F).replace(os.sep, "/")
        found.append(rel_base)
        for name in files:
            found.append(f"{rel_base}/{name}")
    return sorted(found)


# R4-1：篡改来源 → 拒绝；拒绝前后**逐字节**与目录树都不变
bad_inst = json.load(open(inst_path, encoding="utf-8"))
bad_inst["source_commit"] = "deadbeef" * 5
json.dump(bad_inst, open(inst_path, "w"), ensure_ascii=False, indent=2)
_tampered_inst = open(inst_path, encoding="utf-8").read()
_writer_before = open(_writer_path, encoding="utf-8").read()
_dir_before = _tree_snapshot()
proc_src = subprocess.run([wfdrive.TOOL_PYTHON, dev_deploy, "--target", F,
                           "--confirm", "--json"], capture_output=True, text=True)
_dir_after = _tree_snapshot()
rec("R4-1 不同来源追加平台被拒且零写入",
    "WF_ASSET_DECISION；安装记录/writer 逐字节不变；目录树不变",
    f"rc={proc_src.returncode} code={(_json_fact(proc_src.stdout) or {}).get('code')} "
    f"dirs_delta={sorted(set(_dir_after) - set(_dir_before))}",
    proc_src.returncode != 0
    and (_json_fact(proc_src.stdout) or {}).get("code") == "WF_ASSET_DECISION"
    and open(inst_path, encoding="utf-8").read() == _tampered_inst
    and open(_writer_path, encoding="utf-8").read() == _writer_before
    and _dir_after == _dir_before)
json.dump(json.loads(_inst_snap), open(inst_path, "w"), ensure_ascii=False, indent=2)

# R4-2：generation 非整数 → 拒绝；布尔同样不合法
for label, value in (("broken", "broken"), ("true", True), ("false", False)):
    bad_writer = json.load(open(_writer_path, encoding="utf-8"))
    bad_writer["generation"] = value
    json.dump(bad_writer, open(_writer_path, "w"), ensure_ascii=False, indent=2)
    broken_snap = open(_writer_path, encoding="utf-8").read()
    inst_before_gen = open(inst_path, encoding="utf-8").read()
    _dir_before = _tree_snapshot()
    proc_gen = subprocess.run([wfdrive.TOOL_PYTHON, dev_deploy, "--target", F,
                               "--confirm", "--json"], capture_output=True, text=True)
    _dir_after = _tree_snapshot()
    rec(f"R4-2 generation={label} 结构化拒绝且零写入",
        "WF_RECORD_INVALID；无 traceback；writer/安装记录/目录树不变",
        f"rc={proc_gen.returncode} code={(_json_fact(proc_gen.stdout) or {}).get('code')}",
        proc_gen.returncode != 0
        and (_json_fact(proc_gen.stdout) or {}).get("code") == "WF_RECORD_INVALID"
        and "Traceback" not in (proc_gen.stderr or "")
        and open(_writer_path, encoding="utf-8").read() == broken_snap
        and open(inst_path, encoding="utf-8").read() == inst_before_gen
        and _dir_after == _dir_before)
open(_writer_path, "w", encoding="utf-8").write(_writer_snap)

json.dump(results, open(wfdrive.temp("r90_results.json"), "w"), ensure_ascii=False, indent=2)
print("saved", sum(1 for r in results if r["pass"]), "/", len(results))
