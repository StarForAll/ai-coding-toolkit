#!/usr/bin/env python3
"""六轮-8：`definition prepare` 消费**人给出的准备范围授权**，并且同范围重跑不重复索取。

obligation（设计稿 §5.7）：准备通道由人授予「仅本次预览路径」的准备权限；机制记录授权的
来源与范围（不再自报 `source=human`），`run create` 时核到可核授权。范围没变的重跑复用已签
授权（起草→复跑校验这条正常顺序只签一次）；范围变化必须新签。

红模：去掉授权要求（退回修复前自报 `source=human`）→ 无授权也能 prepare，目标断言变红。
"""
import hashlib
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _harness as H

SID = "sess-PREP"
MARKER = "<!-- wf-definition:v1 -->"

# 注入：没有 --authorization 时也退回"自报授权"（修复前的形态）
FROM = '''    previous_authorization = (previous.get("authorization") or {})
    if authorization_entries is not None:
        return authorization_entries
'''
TO = '''    previous_authorization = (previous.get("authorization") or {})
    if True:  # 注入：自报授权，不要求人给决定
        return {"source": "human", "at": records.now_str(),
                "scope_paths": [definition_rel]}
'''


def _definition(workflow_id="prep-demo"):
    doc = {"format_version": 1, "workflow_id": workflow_id, "content_version": 1,
           "purpose": "准备授权场景", "applicability": "已有基线", "inputs": {},
           "steps": [{"id": "confirm", "type": "human", "title": "确认", "required": True,
                      "skip": None, "inputs": [], "outputs": [], "question": "确认？",
                      "choices": ["yes", "no"], "human_points": []}],
           "completion": ["确认完成"]}
    body = json.dumps(doc, ensure_ascii=False, indent=2)
    return f"{MARKER}\n```json\n{body}\n```\n\n# 说明\n"


def _write_definition(project, workflow_id):
    directory = os.path.join(project, ".wf/user-workflows")
    os.makedirs(directory, exist_ok=True)
    text = _definition(workflow_id)
    with open(os.path.join(directory, f"{workflow_id}.md"), "w", encoding="utf-8") as handle:
        handle.write(text)
    return text


def _prepare(project, workflow_id, authorization=None, draft=False, sid=SID):
    argv = ["definition", "prepare", "--id", workflow_id, "--json"]
    if draft:
        argv.insert(2, "--authorization-draft")
    if authorization:
        argv += ["--authorization", authorization]
    return H.cli(project, argv, sid=sid, inputs={"generation": H.generation(project)})


def _end(project, workflow_id, disposition=None, sid=SID):
    argv = ["definition", "prepare", "--id", workflow_id, "--end", "--json"]
    if disposition:
        argv += ["--disposition", disposition]
    return H.cli(project, argv, sid=sid, inputs={"generation": H.generation(project)})


def runs_retention(project):
    """只读核对：准备记录里仍占工作区的保留草稿（用部署树里的同一实现，不自造判定）。"""
    import subprocess
    probe = ("import json,sys;sys.path.insert(0,%r);"
             "from wflib import runs;"
             "print(json.dumps(runs.retained_preparation_wip(%r), ensure_ascii=False))"
             % (os.path.join(project, ".wf/lib"), project))
    proc = subprocess.run([H.WF_PYTHON, "-c", probe], capture_output=True, text=True, cwd=project)
    text = (proc.stdout or "").strip()
    return json.loads(text) if text.startswith("[") else [{"error": text or proc.stderr}]


def _writer(project):
    return json.load(open(os.path.join(project, ".wf/writer.json"), encoding="utf-8"))


def _held_scope(project):
    return ((_writer(project).get("holder") or {}).get("scope") or {}).get("object") or {}


def check():
    root, _lib, _payload = H.stage()
    project = H.deploy(root)
    H.ensure_project_config(project)
    if os.environ.get("WF_REPRO_INJECT") == "1":
        H.patch(os.path.join(project, ".wf/lib/wflib/runs.py"), FROM, TO)

    problems = []
    text = _write_definition(project, "prep-demo")
    record_path = os.path.join(project, ".wf/preparations/prep-demo.json")

    # ① 无授权：停在需人决策、不写准备记录，**也不留下已取得的写权**（授权先定、再动写权）
    _, payload = _prepare(project, "prep-demo")
    code = (payload or {}).get("code")
    facts = (payload or {}).get("facts") or {}
    if code != "WF_SEMANTIC_DECISION":
        problems.append(f"无授权仍能 prepare：code={code} facts={facts}")
    if os.path.isfile(record_path):
        problems.append("无授权却写了准备记录")
    if _writer(project).get("state") != "idle":
        problems.append(f"无授权时留下了写权：holder={_held_scope(project)}")
    if not any("authorization-draft" in str(item) for item in (facts.get("exits") or [])):
        problems.append(f"出口未给草稿入口：{facts.get('exits')}")

    # ② 授权范围不含该定义路径：拒
    wrong = os.path.join(root, "wrong.json")
    _, payload = _prepare(project, "prep-demo", draft=True)
    draft = dict(((payload or {}).get("facts") or {}).get("draft") or {})
    if not draft:
        raise H.Precondition(f"授权草稿不可用：{(payload or {}).get('code')}")
    draft.update({"source": "human terminal (repro)", "reason": "范围写错",
                  "scope_paths": [".wf/user-workflows/other.md"]})
    json.dump([draft], open(wrong, "w"), ensure_ascii=False)
    _, payload = _prepare(project, "prep-demo", wrong)
    if (payload or {}).get("code") == "WF_OK":
        problems.append("范围不含目标定义仍被放行")
    elif "scope" not in json.dumps((payload or {}).get("facts") or {}, ensure_ascii=False):
        problems.append(f"拒绝未指向范围：{(payload or {}).get('facts')}")

    # ③ 正确授权：prepare 成功，记录 authorization.source=decision 且带范围，并持有准备写权
    auth = H.prepare_authorization(project, root, "prep-demo", sid=SID)
    _, payload = _prepare(project, "prep-demo", auth)
    if (payload or {}).get("code") != "WF_OK":
        problems.append(f"带授权仍失败：{(payload or {}).get('code')} {(payload or {}).get('facts')}")
    else:
        record = json.load(open(record_path, encoding="utf-8"))
        authorization = record.get("authorization") or {}
        if authorization.get("source") != "decision":
            problems.append(f"授权来源不是决定：{authorization.get('source')}")
        if ".wf/user-workflows/prep-demo.md" not in (authorization.get("scope_paths") or []):
            problems.append(f"授权未记范围：{authorization.get('scope_paths')}")
    scope_obj = _held_scope(project)
    if not (_writer(project).get("state") == "held" and scope_obj.get("kind") == "preparation"
            and scope_obj.get("id") == "prep-demo"):
        problems.append(f"准备期未持有准备写权：state={_writer(project).get('state')} scope={scope_obj}")

    # ④ 同范围重跑：不重复索取授权
    _, payload = _prepare(project, "prep-demo")
    if (payload or {}).get("code") != "WF_OK":
        problems.append(f"同范围重跑仍索取授权：{(payload or {}).get('code')} {(payload or {}).get('facts')}")

    # ⑤ 未处置的定义编辑不能结束准备
    _, payload = _end(project, "prep-demo")
    if (payload or {}).get("code") != "WF_WORKSPACE_UNRESOLVED":
        problems.append(f"未处置编辑仍能结束准备：code={(payload or {}).get('code')}")

    # ⑥ 只是把路径列进 disposition（未落实去向）不能换到写权
    fake = os.path.join(root, "fake-disposition.json")
    json.dump({"changes": [{"object": ".wf/user-workflows/prep-demo.md", "action": "commit",
                            "reason": "声称已处置"}]}, open(fake, "w"), ensure_ascii=False)
    _, payload = _end(project, "prep-demo", fake)
    if (payload or {}).get("code") == "WF_OK":
        problems.append("未提交却按 disposition 声明结束了准备")
    if _writer(project).get("state") != "held":
        problems.append("声明式 disposition 也释放了写权")

    # ⑦ 提交定义后可结束：ended_at 落盘、写权释放
    import subprocess
    subprocess.run(["git", "add", ".wf/user-workflows/prep-demo.md"], cwd=project, check=True,
                   capture_output=True)
    subprocess.run(["git", "commit", "-qm", "definition prep-demo"], cwd=project, check=True,
                   capture_output=True)
    _, payload = _end(project, "prep-demo")
    if (payload or {}).get("code") != "WF_OK":
        problems.append(f"处置后仍不能结束准备：{(payload or {}).get('code')} {(payload or {}).get('facts')}")
    ended = json.load(open(record_path, encoding="utf-8"))
    if not ended.get("ended_at"):
        problems.append("结束准备未记 ended_at")
    if _writer(project).get("state") != "idle":
        problems.append(f"结束准备未释放写权：state={_writer(project).get('state')}")

    # ⑦b 保留未提交草稿也是合法出路：必须记风险与待处置项，落盘 retained_wip 后释放写权
    _write_definition(project, "delta-demo")
    delta_auth = H.prepare_authorization(project, root, "delta-demo", sid=SID)
    _, payload = _prepare(project, "delta-demo", delta_auth)
    if (payload or {}).get("code") != "WF_OK":
        raise H.Precondition(f"delta 准备失败：{(payload or {}).get('code')} {(payload or {}).get('facts')}")
    with open(os.path.join(project, ".wf/user-workflows/delta-demo.md"), "a", encoding="utf-8") as handle:
        handle.write("\n<!-- 起草中的备注 -->\n")
    _, payload = _end(project, "delta-demo")
    if (payload or {}).get("code") != "WF_WORKSPACE_UNRESOLVED":
        problems.append(f"未处置草稿仍能结束准备：code={(payload or {}).get('code')}")
    retain = os.path.join(root, "delta-retain.json")
    json.dump({"changes": [{"object": ".wf/user-workflows/delta-demo.md", "action": "retain",
                            "risk": "尚未静态校验，实例不能据此启动",
                            "pending": ["补齐 steps 后重跑 definition prepare"]}]},
              open(retain, "w"), ensure_ascii=False)
    _, payload = _end(project, "delta-demo", retain)
    facts = (payload or {}).get("facts") or {}
    if (payload or {}).get("code") != "WF_OK":
        problems.append(f"按条件保留草稿仍不能结束：{(payload or {}).get('code')} {facts}")
    retained = facts.get("retained") or []
    if not retained or not (retained[0] or {}).get("content_digest"):
        problems.append(f"保留未记录内容摘要：{retained}")
    delta_record = json.load(open(os.path.join(project, ".wf/preparations/delta-demo.json"),
                                  encoding="utf-8"))
    if not (delta_record.get("retained_wip") or []):
        problems.append("保留草稿未落盘 retained_wip")
    if _writer(project).get("state") != "idle":
        problems.append(f"保留草稿后未释放写权：state={_writer(project).get('state')}")

    # ⑦c 保留的草稿仍占工作区：别的对象取写权时**指名归属**并被挡下（消费点，不再只是留痕）
    creation = {"definition_id": "prep-demo", "definition_digest":
                "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest(),
                "inputs": {}, "steps": {"confirm": "applicable"}}
    creation_path = os.path.join(root, "creation.json")
    json.dump(creation, open(creation_path, "w"), ensure_ascii=False)
    create_auth = H.creation_authorization(project, root, creation_path, sid=SID)
    rc, payload = H.cli(project, ["run", "create", "--creation", creation_path,
                                  "--authorization", create_auth, "--json"],
                        sid=SID, inputs={"generation": H.generation(project)})
    facts = (payload or {}).get("facts") or {}
    if (payload or {}).get("code") != "WF_WORKSPACE_UNRESOLVED":
        problems.append(f"保留草稿未挡住其他对象取写权：code={(payload or {}).get('code')} {facts}")
    elif not any(item.get("preparation") == "delta-demo" for item in facts.get("blocked") or []):
        problems.append(f"挡下时没有指名准备记录：{facts.get('blocked')}")

    # ⑦d 草稿提交后保留条件落实：不再挡路
    subprocess.run(["git", "add", ".wf/user-workflows/delta-demo.md"], cwd=project, check=True,
                   capture_output=True)
    subprocess.run(["git", "commit", "-qm", "delta draft"], cwd=project, check=True,
                   capture_output=True)
    remaining = runs_retention(project)
    if remaining:
        problems.append(f"草稿处置后保留仍占工作区：{remaining}")

    # ⑧ 已结束的准备记录仍可用于创建（保留条件已落实，写权可再授予）
    rc, payload = H.cli(project, ["run", "create", "--creation", creation_path,
                                  "--authorization", create_auth, "--json"],
                        sid=SID, inputs={"generation": H.generation(project)})
    if rc != 0 or (payload or {}).get("code") != "WF_OK":
        problems.append(f"已结束的准备记录不能用于创建：{(payload or {}).get('code')} {(payload or {}).get('facts')}")

    if problems:
        raise H.TargetFailure("；".join(problems))
    return None

if __name__ == "__main__":
    sys.exit(H.main(check))