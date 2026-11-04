#!/usr/bin/env python3
"""CP5 / B1+B2：F2 上的 Trellis 两分支与「共存 + 外部提交处置」。"""
import hashlib, json, os, subprocess, sys
sys.path.insert(0, "/tmp")
import wfdrive

F = wfdrive.FIX
results = []
AT = "2026-11-03T13:00:00.000000Z"


def rec(name, expected, actual, ok):
    results.append({"case": name, "expected": expected, "actual": actual, "pass": bool(ok)})
    print(f"[{'PASS' if ok else 'FAIL'}] {name}: {actual}")


def wf(args, inputs=None, sid="sess-F1"):
    return wfdrive.run(args, inputs=inputs, sid=sid, show=False)


def dec(subject, choice, digest="sha256:" + "0" * 64):
    return {"source": "human (test)", "at": AT, "subject": subject, "object_digest": digest,
            "choice": choice, "reason": "CP5 用例"}


def git(*args):
    return subprocess.run(["git", "-c", "core.quotePath=false", *args], cwd=F,
                          capture_output=True, text=True).stdout.strip()


# ---------------- B1：Trellis 两分支（F2 自带 .trellis/ 残留言据） ----------------
rc, payload, _ = wf(["enable", "--json"], None, "sess-F1")
rec("B1 纯残留数据可启用", "pass + 警告", f"{(payload or {}).get('code')} warnings={len((payload or {}).get('warnings') or [])}",
    rc == 0 and (payload or {}).get("warnings"))

open(os.path.join(F, "AGENTS.md"), "w").write("# AGENTS\n\n<!-- TRELLIS:START -->\nmanaged\n<!-- TRELLIS:END -->\n")
rc, payload, _ = wf(["enable", "--json"], None, "sess-F1")
rec("B1 托管指令块（适用性未知）", "needs_decision WF_SEMANTIC_DECISION",
    f"{(payload or {}).get('code')} exit={rc}", (payload or {}).get("code") == "WF_SEMANTIC_DECISION" and rc == 2)
os.remove(os.path.join(F, "AGENTS.md"))

os.makedirs(os.path.join(F, ".dsh"), exist_ok=True)
open(os.path.join(F, ".dsh", "hooks.json"), "w").write('{"hooks":[{"name":"trellis-sync"}]}')
rc, payload, _ = wf(["enable", "--json"], None, "sess-F1")
rec("B1 当前宿主有配置但未确认加载 → 待核", "needs_decision WF_SEMANTIC_DECISION",
    f"{(payload or {}).get('code')} exit={rc}", (payload or {}).get("code") == "WF_SEMANTIC_DECISION" and rc == 2)
rc, payload, _ = wf(["enable", "--json"], {"trellis_loaded": True}, "sess-F1")
rec("B1 已确认本会话加载 → 冲突阻断", "blocked WF_FLOW_CONFLICT",
    f"{(payload or {}).get('code')} exit={rc}", (payload or {}).get("code") == "WF_FLOW_CONFLICT" and rc == 1)
os.remove(os.path.join(F, ".dsh", "hooks.json"))

# ---------------- B2：共存 + 外部提交 ----------------
rc, payload, out = wf(["task-new", "--kind", "ordinary", "--title", "CP5 外部提交",
                       "--template", f"{F}/.wf/templates/task", "--json"], None, "sess-F2")
facts = (payload or {}).get("facts", {})
task_id, gen = facts.get("task_id"), facts.get("generation")
if not task_id:
    print("task-new failed:", out[:400]); raise SystemExit(1)
directory = os.path.join(F, facts["directory"])
block = {"schema_version": 1, "touch_paths": ["src/calc.py", "src/other.py"],
         "acceptance": [{"id": "a1", "statement": "calc 可加多项", "verification_ids": ["v1"]}],
         "verifications": [{"id": "v1", "invocation": {"kind": "argv",
                                                       "argv": ["/usr/bin/python3", "-c",
                                                                "from src.calc import add; assert add(1,2,3)==6"]},
                            "cwd": ".", "input_refs": [], "required": True, "consume_at": "check"}]}
prd = f"# CP5 外部提交\n\n<!-- wf-plan:v1 -->\n```json\n{json.dumps(block, ensure_ascii=False, indent=2)}\n```\n"
open(os.path.join(directory, "prd.md"), "w", encoding="utf-8").write(prd)
digest = "sha256:" + hashlib.sha256(prd.encode()).hexdigest()
inputs = {"generation": gen, "complexity": "light",
          "downgrade": {"reason": "单函数扩展", "evidence": "不碰治理面"}}
rc, payload, _ = wf(["task-approve", "--task", task_id, "--decision",
                     json.dump([dec("approve", "approve", digest)], open("/tmp/cp5_a.json", "w")) or "/tmp/cp5_a.json",
                     "--json"], inputs, "sess-F2")
rec("B2 批准", "pass", (payload or {}).get("code"), rc == 0)
open(os.path.join(F, "src/other.py"), "w").write("# other\n")
git("add", "src/other.py")
git("commit", "-qm", "外部提交：不重叠路径")
rc, payload, _ = wf(["task-start", "--task", task_id, "--json"], inputs, "sess-F2")
rec("B2 开工（含外部提交历史）", "pass", (payload or {}).get("code"), rc == 0)

# 任务实施 src/calc.py；随后另一流程提交 src/other.py（与任务触碰面相交）
calc = open(os.path.join(F, "src/calc.py"), encoding="utf-8").read()
if "args" not in calc:
    calc = calc.replace("def add(a, b):\n    return a + b\n",
                        "def add(a, b, *rest):\n    return a + b + sum(rest)\n")
open(os.path.join(F, "src/calc.py"), "w", encoding="utf-8").write(calc)
open(os.path.join(F, "src/other.py"), "a").write("# external change\n")
git("add", "src/other.py")
git("commit", "-qm", "外部提交：触碰面内、无任务标记")
external = git("rev-parse", "HEAD")
json.dump({"standard": {"conclusion": "pass", "basis": "单函数"},
           "requirement": {"conclusion": "pass", "basis": "a1 覆盖"}},
          open("/tmp/cp5_notes.json", "w"))
rc, payload, out = wf(["task-check", "--task", task_id, "--review-notes", "/tmp/cp5_notes.json", "--json"],
                      inputs, "sess-F2")
rec("B2 外部提交（触碰面内）不阻断 Check", "pass", (payload or {}).get("code"), rc == 0)
record = json.load(open(os.path.join(directory, "task.json")))
external_list = (record.get("check") or {}).get("scope_check", {}).get("external_changes") or []
rec("B2 外部提交被列入检查事实", "列出该提交",
    [item.get("commit", "")[:8] for item in external_list],
    any(item.get("commit") == external for item in external_list))
rec("B2 无交集的外部提交不入列", "只列与触碰面相交的提交", f"count={len(external_list)}", len(external_list) == 1)
wf(["writer", "release", "--json"], inputs, "sess-F2")

json.dump(results, open("/tmp/cp5_b12_results.json", "w"), ensure_ascii=False, indent=2)
print("saved", len(results), "cases;", sum(1 for r in results if r["pass"]), "passed")
