#!/usr/bin/env python3
"""C6：审查参与者身份的声明与交叉核对（review-identity-protocol.md §1–§3）。

obligation（2026-11-08 C6 交付）：
- 实施 CLI 必须在 `review-launch --implementation-cli` 时**声明**；缺失即拒绝（不能等判定时从会话猜）；
- reviewer 用 `--as <cli>` 声明身份，**它优先于信封里的 host_id**（同一会话不能靠换信封冒充另一个 CLI）；
- `--as` 必须等于本轮报告文件名 token；从未调用过 `review-context --as X` ⇒ `no_claim`；
- 实施 CLI 实质变化 ⇒ 既有 `reviews.result.verdict` 同批改 `invalidated`（不新增第二状态字段）。

注入形态：让 `context` 忽略 `--as`、退回 host_id（旧的"身份取自信封"行为）。
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _harness as H
import _review_launch as L

SID = "sess-main"
FROM = "    agent = participant_cli(ctx, as_value)\n"
TO = ("    agent = review_cli(((ctx.session() or {}).get('identity') or {}).get('host_id'))  "
      "# 注入：忽略 --as\n")
COVERED = ["node_modules/**", ".env", "*.pem", ".codex/**", "../**", ".wf/tasks/**"]


def launch(project, task_id, root, impl):
    request = os.path.join(root, "c6-launch.json")
    json.dump({"export_decision": {"source": "human", "at": "2026-11-08T00:00:00.000000Z",
                                   "subject": ["授权外发"], "choice": "export"},
               "submitted_scope": {"diff": True, "requirement": True, "test_results": True}},
              open(request, "w", encoding="utf-8"), ensure_ascii=False)
    args = ["review-launch", "--task", task_id, "--launch-request", request, "--json"]
    if impl:
        args += ["--implementation-cli", impl]
    return H.cli(project, args, sid=SID, inputs={"generation": H.generation(project)})


def context(project, task_id, round_no, agent):
    return H.cli(project, ["review-context", "--task", task_id, "--round", str(round_no),
                           "--as", agent, "--json"], sid=SID, host_id="dsh",
                 inputs={"generation": H.generation(project)})


def write_report(path, task_id, round_no, agent, anchor, check_id):
    axes = {name: {"conclusion": "pass", "basis": "人工审查"}
            for name in ("range", "acceptance", "contract", "regression", "testability")}
    body = {"protocol": "wf-review-v1", "task-id": task_id, "round": round_no,
            "review-time": "2026-11-08T00:00:00.000000Z", "review-focus": "范围/验收",
            "check-anchor": {"check_id": check_id, "check_anchor": anchor},
            "read-scope": ["pkg/**"], "excluded-scope": COVERED,
            "scope-exceptions": [], "axes": axes, "findings": [], "verdict": "pass"}
    text = ("<!-- wf-review-agent:v1 status=done -->\n<!-- wf-review-report:v1 -->\n```json\n"
            + json.dumps(body, ensure_ascii=False, indent=2) + "\n```\n")
    open(path, "w", encoding="utf-8").write(text)


def result_of(project, task_id):
    import glob

    path = glob.glob(os.path.join(project, ".wf/tasks", f"{task_id}-*", "task.json"))[0]
    record = json.load(open(path, encoding="utf-8"))
    return (record.get("reviews") or {}).get("result") or {}


def check():
    root, _lib, _payload = H.stage()
    project = H.deploy(root)
    H.ensure_project_config(project)
    if os.environ.get("WF_REPRO_INJECT") == "1":
        H.patch(os.path.join(project, ".wf/lib/wflib/review.py"), FROM, TO)
    task_id, task_dir = L.prepare(project, root, SID)
    problems = []

    # ① 未声明实施 CLI ⇒ 直接拒绝
    rc, payload = launch(project, task_id, root, None)
    facts = (payload or {}).get("facts") or {}
    if (payload or {}).get("code") != "WF_REVIEW_INVALID" or \
            facts.get("reason") != "implementation CLI must be declared":
        problems.append(f"未声明实施 CLI 未被拒：{(payload or {}).get('code')}/{facts.get('reason')}")

    # ② 声明后开一轮
    rc, payload = launch(project, task_id, root, "codex")
    if rc != 0 or (payload or {}).get("code") != "WF_OK":
        raise H.Precondition(f"声明式 launch 失败：{payload}")
    round_no = (payload.get("facts") or {}).get("round") or 1

    # ③ --as 优先于信封 host_id（信封 host 仍是 dsh）
    report_dirs, agents = [], []
    for agent in ("pi", "zcode"):
        rc, payload = context(project, task_id, round_no, agent)
        if (payload or {}).get("code") != "WF_OK":
            # 这是**目标断言**的一部分（注入后身份塌成 host_id ⇒ 第二个 reviewer 被占位拦），
            # 不能算前置失败，否则 red 用例会被判成"夹具坏了"而不是"缺陷被抓到"。
            problems.append(f"review-context --as {agent} 失败：{(payload or {}).get('code')}/"
                            f"{((payload or {}).get('facts') or {}).get('reason')}")
            continue
        agents.append((payload.get("facts") or {}).get("agent"))
        report_dirs.append(os.path.dirname((payload.get("facts") or {}).get("report_path") or ""))
    if len(agents) == 2 and agents != ["pi", "zcode"]:
        problems.append(f"--as 未优先于 host_id：{agents}")
    if problems:
        raise H.TargetFailure("；".join(problems))

    # ④ 从未调用过 context 的 --as ⇒ no_claim
    rc, payload = H.cli(project, ["review-import", "--task", task_id, "--as", "claude", "--json"],
                        sid=SID, inputs={"generation": H.generation(project)})
    facts = (payload or {}).get("facts") or {}
    if (payload or {}).get("code") != "WF_REVIEW_INVALID" or facts.get("reason") != "no_claim":
        problems.append(f"无占位的 --as 未报 no_claim：{(payload or {}).get('code')}/{facts.get('reason')}")

    # ⑤ 写两份报告 → 导入 → 判定
    record = json.load(open(os.path.join(task_dir, "task.json"), encoding="utf-8"))
    check_now = record.get("check") or {}
    anchor = (check_now.get("anchor") or {}).get("check_anchor")
    for agent, directory in zip(("pi", "zcode"), report_dirs):
        write_report(os.path.join(directory, f"review-{agent}.md"), task_id, round_no,
                     agent, anchor, check_now.get("id"))
    rc, payload = H.cli(project, ["review-import", "--task", task_id, "--json"],
                        sid=SID, inputs={"generation": H.generation(project)})
    if (payload or {}).get("code") != "WF_OK":
        raise H.Precondition(f"导入失败：{payload}")
    rc, payload = H.cli(project, ["review-decide", "--task", task_id, "--json"],
                        sid=SID, inputs={"generation": H.generation(project)})
    if (payload or {}).get("code") != "WF_OK":
        raise H.Precondition(f"判定失败：{payload}")
    if result_of(project, task_id).get("verdict") != "pass":
        problems.append(f"判定未给出 pass：{result_of(project, task_id).get('verdict')}")

    # ⑥ 实施 CLI 实质变化 ⇒ 结论失效；且只能有 verdict 一个状态字段
    rc, payload = launch(project, task_id, root, "pi")
    if (payload or {}).get("code") != "WF_OK":
        problems.append(f"补录式 relaunch 失败：{(payload or {}).get('code')}")
    result = result_of(project, task_id)
    if result.get("verdict") != "invalidated":
        problems.append(f"实施 CLI 变化未使结论失效：{result.get('verdict')}")
    if "status" in result:
        problems.append("引入了第二状态字段 status（协议要求只保留 verdict）")

    if problems:
        raise H.TargetFailure("；".join(problems))
    return None


if __name__ == "__main__":
    sys.exit(H.main(check))
