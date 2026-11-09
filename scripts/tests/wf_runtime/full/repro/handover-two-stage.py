#!/usr/bin/env python3
"""F7-4：两段显式交接——begin 进 recovering、中间态双方不可写、accept 换新代次后旧代次失效。

缺陷形态：交接只看"谁是接收者"，接受时递增代次这一环被省掉，
于是旧会话仍能以旧代次继续写入（"交接"变成了"复制"）。
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _harness as H
import _review_flow as F


def _receiver_key(project, sid):
    lib = os.path.join(project, ".wf/lib")
    if lib not in sys.path:
        sys.path.insert(0, lib)
    from wflib import session as wf_session

    return wf_session.session_key({"provider": "host",
                                   "identity": {"host_id": "dsh", "session_id": sid}})


def check():
    root, _lib, _payload = H.stage()
    project = H.deploy(root)
    if os.environ.get("WF_REPRO_INJECT") == "1":
        # 注入点必须唯一：`generation = ... + 1` 在 acquire/handover_accept 各有一处，
        # 连同 handover 前置判断一起替换，避免打错到 acquire（本轮实际踩过）。
        H.patch(os.path.join(project, ".wf/lib/wflib/writer.py"),
                '    if handover.get("receiver_session_key") != session_key:\n'
                '        raise WriterError("receiver does not match handover")\n'
                '    generation = int(record.get("generation", 0)) + 1',
                '    if handover.get("receiver_session_key") != session_key:\n'
                '        raise WriterError("receiver does not match handover")\n'
                '    generation = int(record.get("generation", 0))  # 注入：接受不动代次')
    sid_a, sid_b = "sess-H1", "sess-H2"
    task_id, _task_dir = F.build_task(project, root, sid=sid_a)
    old_gen = H.generation(project)

    H.cli(project, ["task-pause", "--task", task_id, "--reason", "交接", "--json"],
          sid=sid_a, inputs={"generation": old_gen})
    dec_path = os.path.join(root, "handover.json")
    json.dump([F.decision(f"handover {task_id}", "handover")], open(dec_path, "w"), ensure_ascii=False)
    rc_begin, payload_begin = H.cli(
        project, ["writer-handover", "begin", "--to", _receiver_key(project, sid_b),
                  "--decision", dec_path, "--json"],
        sid=sid_a, inputs={"generation": H.generation(project)})

    problems = []
    H.require_business_code(payload_begin, rc_begin)
    if rc_begin != 0:
        raise H.Precondition(f"begin 失败：{(payload_begin or {}).get('code')}")
    state = json.load(open(os.path.join(project, ".wf/writer.json"), encoding="utf-8"))
    if state.get("state") != "recovering":
        problems.append(f"begin 后状态不是 recovering：{state.get('state')}")

    rc_mid, mid = H.cli(project, ["task-resume", "--task", task_id, "--json"],
                        sid=sid_a, inputs={"generation": H.generation(project)})
    H.require_business_code(mid, rc_mid)
    H.only_two_outcomes((mid or {}).get("code") if rc_mid != 0 else "WF_OK",
                        "WF_WRITER_BUSY", "mid")
    if rc_mid == 0:
        problems.append("交接中间态旧会话仍可写")

    rc_pre, pre = H.cli(project, ["task-resume", "--task", task_id, "--json"],
                        sid=sid_b, inputs={"generation": H.generation(project)})
    H.require_business_code(pre, rc_pre)
    H.only_two_outcomes((pre or {}).get("code") if rc_pre != 0 else "WF_OK",
                        "WF_BINDING_MISMATCH", "pre")
    if rc_pre == 0:
        problems.append("接收者 accept 前即可写")

    # 必须以"accept 前"为基线：begin 本身就会递增一次代次，拿最初的代次比会误判
    mid_gen = H.generation(project)
    rc_accept, accept = H.cli(project, ["writer-handover", "accept", "--json"], sid=sid_b)
    H.require_business_code(accept, rc_accept)
    if rc_accept != 0:
        raise H.Precondition(f"accept 失败：{(accept or {}).get('code')}")

    new_gen = H.generation(project)
    if not isinstance(new_gen, int) or new_gen <= mid_gen:
        problems.append(f"accept 未换新代次：begin 后 {mid_gen} -> accept 后 {new_gen}")

    rc_old, old_payload = H.cli(project, ["task-resume", "--task", task_id, "--json"],
                                sid=sid_a, inputs={"generation": old_gen})
    H.require_business_code(old_payload, rc_old)
    H.only_two_outcomes((old_payload or {}).get("code") if rc_old != 0 else "WF_OK",
                        "WF_WRITER_BUSY", "old_payload")
    if rc_old == 0:
        problems.append("accept 后旧会话仍可写")
    if problems:
        raise H.TargetFailure("；".join(problems))
    return None


if __name__ == "__main__":
    sys.exit(H.main(check))
