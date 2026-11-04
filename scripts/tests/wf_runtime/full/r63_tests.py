#!/usr/bin/env python3
"""第二十六轮 R63：P2-6 日志/facts 秘密边界 + P2-7 副本来源登记。"""
import hashlib, json, os, subprocess, sys
sys.path.insert(0, "/tmp")
sys.path.insert(0, "/home/xzc/projects/personal/ai-coding-toolkit/docs/workflows/新项目开发工作流/payload/lib")
import wfdrive
from wflib import check as wf_check

F = wfdrive.FIX
SRC = "/home/xzc/projects/personal/ai-coding-toolkit/docs/workflows/新项目开发工作流/skills"
results = []

EXTERNAL_ACK = "/tmp/wf_external_ack.json"
if not os.path.exists(EXTERNAL_ACK):
    json.dump([{"source": "human (test)", "at": "2026-11-04T00:00:00.000000Z",
                "subject": "external-changes", "object_digest": "sha256:" + "0" * 64,
                "choice": "已核对无影响", "reason": "夹具提交均为本任务改动"}],
              open(EXTERNAL_ACK, "w"), ensure_ascii=False)
AT = "2026-11-05T10:00:00.000000Z"


def rec(name, expected, actual, ok):
    results.append({"case": name, "expected": expected, "actual": actual, "pass": bool(ok)})
    print(f"[{'PASS' if ok else 'FAIL'}] {name}: {actual}")


def wf(args, inputs=None, sid="sess-H1"):
    return wfdrive.run(args, inputs=inputs, sid=sid, show=False)


def dec(subject, choice, digest="sha256:" + "0" * 64):
    return {"source": "human", "at": AT, "subject": subject, "object_digest": digest,
            "choice": choice, "reason": "R63"}



def clean():
    subprocess.run(["git", "add", "-A"], cwd=F, capture_output=True)
    subprocess.run(["git", "commit", "-qm", "cap", "--allow-empty"], cwd=F, capture_output=True)


def write_gen():
    return json.load(open(os.path.join(F, ".wf/writer.json"), encoding="utf-8")).get("generation")


rec("脱敏 key=value", "api_key=***", wf_check.redact_secrets("api_key=abc123"),
    "***" in wf_check.redact_secrets("api_key=abc123"))
rec("脱敏 sk- 形态", "Bearer ***", wf_check.redact_secrets("Bearer sk-abcdefghijklmnop"),
    "***" in wf_check.redact_secrets("Bearer sk-abcdefghijklmnop"))
rec("不误伤普通输出", "tests passed", wf_check.redact_secrets("tests passed"),
    wf_check.redact_secrets("tests passed") == "tests passed")

clean()
os.makedirs(os.path.join(F, "pkg"), exist_ok=True)
rc, payload, _ = wf(["task-new", "--kind", "ordinary", "--title", "R63 脱敏",
                     "--template", f"{F}/.wf/templates/task", "--json"], None, "sess-H1")
facts = (payload or {}).get("facts", {})
task_id, gen = facts.get("task_id"), facts.get("generation")
directory = os.path.join(F, facts["directory"])
block = {"schema_version": 1, "touch_paths": ["pkg/**"],
         "acceptance": [{"id": "a1", "statement": "x", "verification_ids": ["v1"]}],
         "verifications": [{"id": "v1", "invocation": {"kind": "argv",
                                                       "argv": ["/usr/bin/python3", "-c",
                                                                "print('ok'); print('token=supersecretvalue')"]},
                            "cwd": ".", "input_refs": [], "required": True, "consume_at": "check"}]}
prd = f"# R63\n\n<!-- wf-plan:v1 -->\n```json\n{json.dumps(block, ensure_ascii=False, indent=2)}\n```\n"
open(os.path.join(directory, "prd.md"), "w", encoding="utf-8").write(prd)
digest = "sha256:" + hashlib.sha256(prd.encode()).hexdigest()
json.dump([dec("approve", "approve", digest)], open("/tmp/r63_a.json", "w"))
wf(["task-approve", "--task", task_id, "--decision", "/tmp/r63_a.json", "--json"],
   {"generation": gen, "complexity": "light", "downgrade": {"reason": "单文件", "evidence": "不碰治理面"}}, "sess-H1")
open(os.path.join(F, "pkg/a.py"), "w").write("x\n")
wf(["task-start", "--task", task_id, "--json"], {"generation": write_gen()}, "sess-H1")
NOTES = "/tmp/r63_notes.json"
json.dump({"standard": {"conclusion": "pass", "basis": "b"}, "requirement": {"conclusion": "pass", "basis": "b"}}, open(NOTES, "w"))
wf(["task-check", "--task", task_id, "--review-notes", NOTES,
                    "--decision", EXTERNAL_ACK, "--json"], {"generation": write_gen()}, "sess-H1")
saved = json.load(open(os.path.join(directory, "task.json"), encoding="utf-8"))
command = ((saved.get("check") or {}).get("commands") or [{}])[0]
log_path = os.path.join(F, command.get("evidence_ref") or "")
log_text = open(log_path, encoding="utf-8").read() if os.path.exists(log_path) else ""
rec("日志遮罩秘密", "含 *** 且不含明文",
    f"masked={'***' in log_text} plain={'supersecretvalue' not in log_text}",
    "***" in log_text and "supersecretvalue" not in log_text)
rec("facts 摘要素遮罩", "summary 含 ***", command.get("summary"), "***" in (command.get("summary") or ""))

required = ("来源", "许可", "基线", "差异", "最近正例", "最近反例")
for name in ("wf-grilling", "wf-tdd", "wf-diagnosing-bugs", "wf-code-review", "wf-review", "wf-review-action"):
    text = open(os.path.join(SRC, name, "SKILL.md"), encoding="utf-8").read()
    missing = [item for item in required if f"| {item} |" not in text]
    rec(f"P2-7 {name} 来源登记齐全", "六项齐全", missing or "ok", not missing)

json.dump(results, open("/tmp/r63_results.json", "w"), ensure_ascii=False, indent=2)
print("saved", sum(1 for r in results if r["pass"]), "/", len(results))
