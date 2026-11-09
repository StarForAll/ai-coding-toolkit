#!/usr/bin/env python3
import json, os, subprocess, sys

FIX = os.environ.get("WF_FIX", "/tmp/wf-fixtures/f1")
WF = os.path.join(FIX, ".wf/bin/wf.py")
PYTHON = "/usr/bin/python3"
TS = "2026-11-03T00:00:00.000000Z"


def envelope(inputs=None, sid="sess-A", activation=True, instance_id=None):
    return {
        "session": {
            "provider": "host",
            "identity": {"host_id": "dsh", "session_id": sid},
            "instance_id": instance_id,
            "activation": ({"enabled": True, "start_source": "human:test", "enabled_at": TS}
                           if activation else None),
        },
        "inputs": inputs or {},
    }


def _binding_instance(sid, provider="host", issued=None):
    """扮演宿主适配层：把持久绑定里的 instance_id 随会话携带（机制稿 §1.4）。"""
    import glob

    for path in glob.glob(os.path.join(FIX, ".wf/session-bindings", "*.json")):
        try:
            data = json.load(open(path, encoding="utf-8"))
        except (OSError, ValueError):
            continue
        identity = data.get("identity") or {}
        value = identity.get("value") or {}
        if identity.get("provider") != provider:
            continue
        if provider == "host" and value.get("session_id") != sid:
            continue
        if provider == "wf" and value.get("issued_id") != issued:
            continue
        if data.get("instance_id"):
            return data["instance_id"]
    return None


def freeze_sampling(task_id, generation, sid="sess-A", instance_id=None):
    """归档前置：冻结事件集并落盘选样（`task.sampled` 门禁要求）。

    **只在套件没有自己的 wrapper 时用**：套件通常有自己的 `wf(...)`/`wfk(...)` 封装（带该套件的
    session id 与绑定）。若绕过它直接走本函数，写权会落在 sess-A 上，把套件真正的会话挡在
    `WF_WRITER_BUSY` 外面——第一次迁移就是这样踩的。优先用套件自己的 wrapper：

        wf(["sampling", "pick", "--task", task_id, "--freeze", "--json"], {"generation": gen})
    """
    return run(["sampling", "pick", "--task", task_id, "--freeze", "--json"],
               inputs={"generation": generation}, sid=sid, instance_id=instance_id, show=False)


def run(args, inputs=None, sid="sess-A", activation=True, instance_id=None, show=True):
    args = [str(item) for item in args]
    merged = {}
    if os.environ.get("WF_INPUTS"):
        merged.update(json.loads(os.environ["WF_INPUTS"]))
    merged.update(inputs or {})
    carried = instance_id if instance_id is not None else _binding_instance(sid)
    payload = json.dumps(envelope(merged, sid, activation, carried), ensure_ascii=False)
    proc = subprocess.run([PYTHON, WF] + args, input=payload, capture_output=True, text=True)
    out = proc.stdout.strip()
    parsed = None
    try:
        parsed = json.loads(out) if out.startswith("{") else None
    except ValueError:
        parsed = None
    if show:
        print(f"$ wf.py {' '.join(args)}  -> exit={proc.returncode}")
        if parsed:
            print(json.dumps(parsed, ensure_ascii=False, indent=2)[:2400])
        else:
            print(out[:2000])
        if proc.stderr.strip() and (proc.returncode != 0 or os.environ.get("WF_DEBUG")):
            print("STDERR:", proc.stderr.strip()[-3000:])
    combined = out + (("\nSTDERR:\n" + proc.stderr.strip()) if proc.stderr.strip() else "")
    return proc.returncode, parsed, combined


if __name__ == "__main__":
    run(sys.argv[1:])
