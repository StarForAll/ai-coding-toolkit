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
        # 第二个注入面：交接接受把检查点抹掉（session-flow 要求"补检查点"；旧实现即传 None）
        H.patch(os.path.join(project, ".wf/lib/wflib/writer.py"),
                '        handover=None,\n'
                '        checkpoint=checkpoint,\n'
                '    )\n'
                '\n'
                '\n'
                'def maintenance_acquire',
                '        handover=None,\n'
                '        checkpoint=None,  # 注入：接受时抹掉检查点\n'
                '    )\n'
                '\n'
                '\n'
                'def maintenance_acquire')
        # 第三个注入面：交接中间态的出口不再点名 accept（接收方路径必须能区分）
        H.patch(os.path.join(project, ".wf/lib/wflib/cli.py"),
                '        exits = ["接收方运行 `wf writer-handover accept`（只有 handover.receiver_session_key 声明的会话可接收）",\n'
                '                 "发起方已让出写权、不能继续写；交接中断由人确认后走 `wf repair` 恢复"]\n',
                '        exits = ["写权忙：按 repair 核对写者后再重入"]\n')
    sid_a, sid_b = "sess-H1", "sess-H2"
    task_id, _task_dir = F.build_task(project, root, sid=sid_a)
    old_gen = H.generation(project)

    H.cli(project, ["task-pause", "--task", task_id, "--reason", "交接", "--json"],
          sid=sid_a, inputs={"generation": old_gen})
    # 接收方先建立自己的会话并取得 session_key（begin 不核附件存在；显式信封不落附件）
    rc_enable_b, enable_b = H.cli(project, ["enable", "--json"], sid=sid_b)
    H.require_business_code(enable_b, rc_enable_b)
    if rc_enable_b != 0:
        raise H.Precondition(f"接收方 enable 失败：{(enable_b or {}).get('code')}")
    if ((enable_b or {}).get("facts") or {}).get("session_key") != _receiver_key(project, sid_b):
        raise H.Precondition(f"接收方 key 不一致：{enable_b}")
    dec_path = os.path.join(root, "handover.json")
    json.dump([F.decision(f"handover {task_id}", "handover")], open(dec_path, "w"), ensure_ascii=False)
    # 接收前更正：先用错 key 发起，再在同一 recovering 重发正确 key；不应升级为 repair。
    rc_wrong, payload_wrong = H.cli(
        project, ["writer-handover", "begin", "--to", "f" * 64,
                  "--decision", dec_path, "--json"],
        sid=sid_a, inputs={"generation": H.generation(project)})
    rc_begin, payload_begin = H.cli(
        project, ["writer-handover", "begin", "--to", _receiver_key(project, sid_b),
                  "--decision", dec_path, "--json"],
        sid=sid_a, inputs={"generation": H.generation(project)})

    problems = []
    if rc_wrong != 0 or ((payload_wrong or {}).get("facts") or {}).get("writer_state") != "recovering":
        problems.append(f"错 key 发起未进入 recovering：{payload_wrong}")
    if ((payload_begin or {}).get("facts") or {}).get("redeclared") is not True:
        problems.append(f"重发 begin 未走接收更正：{payload_begin}")
    H.require_business_code(payload_begin, rc_begin)
    if rc_begin != 0:
        raise H.Precondition(f"begin 失败：{payload_begin}")
    state = json.load(open(os.path.join(project, ".wf/writer.json"), encoding="utf-8"))
    if state.get("state") != "recovering":
        problems.append(f"begin 后状态不是 recovering：{state.get('state')}")
    receiver_key = _receiver_key(project, sid_b)

    # 接收方的真实发现路径：ready 不得把交接对象标成就绪；bind/task-new 必须点名 accept
    # （2026-11-28 终审 F1.6/F2：此前只有 require_held/acquire 有出口，接收方撞的是零出口）。
    rc_ready, ready_payload = H.cli(project, ["ready", "--json"], sid=sid_b)
    H.require_business_code(ready_payload, rc_ready)
    entry = next((item for item in ((ready_payload or {}).get("facts") or {}).get("tasks") or []
                  if item.get("id") == task_id), None)
    if not entry or entry.get("ready") or "handover_pending" not in (entry.get("blockers") or []):
        problems.append(f"ready 未把交接对象标成 handover_pending：{entry}")
    rc_bind, bind_payload = H.cli(project, ["bind", "--task", task_id, "--json"], sid=sid_b)
    H.require_business_code(bind_payload, rc_bind)
    if ((bind_payload or {}).get("code") != "WF_WRITER_BUSY"
            or "writer-handover accept" not in json.dumps(bind_payload, ensure_ascii=False)):
        problems.append(f"bind 未给 accept 出口：{bind_payload}")
    if (((bind_payload or {}).get("facts") or {}).get("you_are") != "receiver"):
        problems.append(f"bind 未告诉接收方自己的角色：{(bind_payload or {}).get('facts')}")
    rc_en2, en2 = H.cli(project, ["enable", "--json"], sid=sid_b)
    H.require_business_code(en2, rc_en2)
    if not ((en2 or {}).get("facts") or {}).get("handover_for_me") \
            or "writer-handover accept" not in ((en2 or {}).get("next") or ""):
        problems.append(f"接收方 enable 未发现交接：{en2}")
    # 接收方在 accept 前是未绑定会话：--short 也必须能看到交接投影（F7）
    rc_sh0, sh0 = H.cli(project, ["status", "--short", "--json"], sid=sid_b)
    H.require_business_code(sh0, rc_sh0)
    sh0_writer = ((sh0 or {}).get("facts") or {}).get("writer") or {}
    if (sh0_writer.get("handover") or {}).get("receiver_session_key") != receiver_key:
        problems.append(f"未绑定会话的 status --short 未投影交接：{sh0_writer}")
    rc_st, st_payload = H.cli(project, ["status", "--json"], sid=sid_b)
    H.require_business_code(st_payload, rc_st)
    projected = (((st_payload or {}).get("facts") or {}).get("handover") or {})
    if projected.get("receiver_session_key") != receiver_key:
        problems.append(f"status 未投影 handover：{projected}")

    rc_mid, mid = H.cli(project, ["task-resume", "--task", task_id, "--json"],
                        sid=sid_a, inputs={"generation": H.generation(project)})
    H.require_business_code(mid, rc_mid)
    H.only_two_outcomes((mid or {}).get("code") if rc_mid != 0 else "WF_OK",
                        "WF_WRITER_BUSY", "mid")
    if rc_mid == 0:
        problems.append("交接中间态旧会话仍可写")
    # 中间态的拒绝必须点名唯一可执行入口：接收方只看到"忙"时无从发现有人把对象交给了它
    # （2026-11-28 独立复审 F2.1/F2.2）。
    if "writer-handover accept" not in json.dumps(mid or {}, ensure_ascii=False):
        problems.append(f"中间态拒绝未给出 writer-handover accept 出口：{(mid or {}).get('next')}")
    if (((mid or {}).get("facts") or {}).get("you_are") != "initiator"):
        problems.append(f"中间态未告诉发起方自己的角色：{(mid or {}).get('facts')}")

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
    # session-flow 的「补检查点」：交接后写权归新会话，检查点必须记录这次接收而不是被抹掉
    # （2026-11-28 独立复审 F3.1）。
    accepted_state = json.load(open(os.path.join(project, ".wf/writer.json"), encoding="utf-8"))
    checkpoint = accepted_state.get("checkpoint") or {}
    if checkpoint.get("step") != "handover-accepted":
        problems.append(f"accept 未补检查点：{checkpoint}")
    rc_st2, st2_payload = H.cli(project, ["status", "--json"], sid=sid_b)
    H.require_business_code(st2_payload, rc_st2)
    projected_checkpoint = (((st2_payload or {}).get("facts") or {}).get("checkpoint") or {})
    if projected_checkpoint.get("step") != "handover-accepted":
        problems.append(f"status 未投影检查点（设计稿 §4.4 的消费者）：{projected_checkpoint}")
    # skills 默认路由用 --short：检查点/交接投影必须同样可见（不能只在全量 status 里有）
    rc_sh, sh_payload = H.cli(project, ["status", "--short", "--json"], sid=sid_b)
    H.require_business_code(sh_payload, rc_sh)
    short_writer = ((sh_payload or {}).get("facts") or {}).get("writer") or {}
    if ((short_writer.get("checkpoint") or {}).get("step") != "handover-accepted"):
        problems.append(f"status --short 未投影检查点：{short_writer}")

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
