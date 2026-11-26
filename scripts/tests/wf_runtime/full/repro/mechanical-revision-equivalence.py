#!/usr/bin/env python3
"""六轮-A2：机械修订的等价核验必须覆盖 plan 版本绑定的全部语义域。

obligation（设计稿 §4.2 的机械修订纪律）：`choice=机械修订` 的人签只承载"只是排版/转义"。
机制必须能证明这一句——触碰面、验收摘要、**验证声明**（argv/cwd/required/consumeAt）与
`tdd_applicability` 全都不变。此前只比前两项，改验证命令或关掉红绿硬要求都能走这条通道
（六轮复核 A2）。

红模：把等价域退回"触碰面 + 验收摘要" → 改过 argv 的 PRD 也能"机械修订"通过，目标断言变红。
"""
import hashlib
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _harness as H
import _review_flow as F

SID = "sess-MECH"

# 注入点必须落在**唯一实现**上：等价核验有两处调用（批准入口的机械修订分支与门禁投影），
# 只关掉其中一处的比较会被另一处拦住，red 面永远变不红（假的证伪）。
FROM = '''    return records.H("wf-verifications-v1", list(verifications or []))
'''
TO = '''    return "sha256:" + "0" * 64  # 注入：验证声明摘要恒等（两处比较同时失效）
'''


def _block(argv=("print(1)",), applicability=None):
    block = {"schema_version": 1, "touch_paths": ["pkg/a.py"],
             "acceptance": [{"id": "a1", "statement": "a1", "verification_ids": ["v1"]}],
             "verifications": [{"id": "v1", "invocation": {"kind": "argv",
                                                           "argv": [H.WF_PYTHON, "-c", argv[0]]},
                                "cwd": ".", "input_refs": [], "required": True,
                                "consume_at": "check"}]}
    if applicability:
        block["tdd_applicability"] = applicability
    return block


def _prd(block, extra=""):
    return ("# 机械修订\n\n" + extra + "<!-- wf-plan:v1 -->\n```json\n"
            + json.dumps(block, ensure_ascii=False, indent=2) + "\n```\n")


def check():
    root, _lib, _payload = H.stage()
    project = H.deploy(root)
    H.ensure_project_config(project)
    os.makedirs(os.path.join(project, "pkg"), exist_ok=True)
    open(os.path.join(project, "pkg/a.py"), "w").write("a\n")
    if os.environ.get("WF_REPRO_INJECT") == "1":
        H.patch(os.path.join(project, ".wf/lib/wflib/fingerprint.py"), FROM, TO)

    rc, payload = H.cli(project, ["task-new", "--kind", "ordinary", "--title", "机械修订",
                                  "--template", os.path.join(project, ".wf/templates/task"), "--json"],
                        sid=SID)
    if rc != 0:
        raise H.Precondition(f"task-new 失败：{payload}")
    task_id = payload["facts"]["task_id"]
    task_dir = os.path.join(project, payload["facts"]["directory"])

    prd = _prd(_block())
    open(os.path.join(task_dir, "prd.md"), "w", encoding="utf-8").write(prd)
    digest = "sha256:" + hashlib.sha256(prd.encode()).hexdigest()
    decision = os.path.join(root, "approve.json")
    json.dump([dict(F.decision(f"approve {task_id}", "approve", digest),
                    artifacts=H.plan_artifacts(project, f"approve {task_id}"))],
              open(decision, "w"), ensure_ascii=False)
    rc, payload = H.cli(project, ["task-approve", "--task", task_id, "--decision", decision, "--json"],
                        sid=SID, inputs={"generation": H.generation(project)})
    if rc != 0:
        raise H.Precondition(f"首次批准失败：{(payload or {}).get('code')} {(payload or {}).get('facts')}")

    def mechanical(new_prd, label):
        open(os.path.join(task_dir, "prd.md"), "w", encoding="utf-8").write(new_prd)
        new_digest = "sha256:" + hashlib.sha256(new_prd.encode()).hexdigest()
        path = os.path.join(root, f"mech-{label}.json")
        # 机械修订同样要绑当前产物集（否则先被 artifact_drift 拦住，考不到等价域）
        json.dump([dict(F.decision(f"机械修订 {task_id}", "机械修订", new_digest),
                        reason="只手写排版/转义",
                        artifacts=H.plan_artifacts(project, f"机械修订 {task_id}"))],
                  open(path, "w"), ensure_ascii=False)
        return H.cli(project, ["task-approve", "--task", task_id, "--decision", path, "--json"],
                     sid=SID, inputs={"generation": H.generation(project)})

    problems = []
    # ① 改验证命令：不是排版/转义，必须拒
    rc, payload = mechanical(_prd(_block(argv=("print(2)",))), "argv")
    code = (payload or {}).get("code")
    facts = (payload or {}).get("facts") or {}
    if code == "WF_OK":
        problems.append("改了验证命令仍按机械修订通过")
    elif (facts.get("same_verifications") is not False
          and facts.get("current_verifications") == facts.get("approved_verifications")):
        problems.append(f"拒绝事实未点名验证声明差异：{facts}")

    # ② 改 TDD 适用性：等于关掉红绿硬要求，必须拒
    block = _block()
    block["tdd_applicability"] = "docs"
    rc, payload = mechanical(_prd(block), "applicability")
    code = (payload or {}).get("code")
    facts = (payload or {}).get("facts") or {}
    if code == "WF_OK":
        problems.append("改 tdd_applicability 仍按机械修订通过")
    elif (facts.get("same_tdd_applicability") is not False
          and facts.get("current_tdd_applicability") == facts.get("approved_tdd_applicability")):
        problems.append(f"拒绝事实未点名适用性差异：{facts}")

    # ③ 只改块外文字（机读块一字不动）：可走机械修订
    prd_text = _prd(_block())
    rc, payload = mechanical(prd_text.replace("# 机械修订\n\n", "# 机械修订（排版调整）\n\n"), "typo")
    if (payload or {}).get("code") != "WF_OK":
        problems.append(f"纯块外排版改动被拒：{(payload or {}).get('code')} {(payload or {}).get('facts')}")

    if problems:
        raise H.TargetFailure("；".join(problems))
    return None


if __name__ == "__main__":
    sys.exit(H.main(check))