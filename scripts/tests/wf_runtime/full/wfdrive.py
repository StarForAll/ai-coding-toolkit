#!/usr/bin/env python3
import json, os, subprocess, sys

FIX = os.environ.get("WF_FIX", "/tmp/wf-fixtures/f1")
WF = os.path.join(FIX, ".wf/bin/wf.py")
# SUT 驱动解释器（启动被测 wf.py）：默认保持异解释器是既定决策——wflib/session.py 的
# l2_anchor 会跳过与自身同解释器的祖先，SUT 与驱动同解释器会把锚点推出 harness 之外
# （探针证据见任务 11-13-wf-runner-speed-quality 的 evidence/anchor-probe.txt）。
# WF_TEST_PYTHON 是可覆盖口；全库 SUT 驱动点（full/repro/单元层/manual）一律引本常量。
PYTHON = os.environ.get("WF_TEST_PYTHON") or "/usr/bin/python3"
# 工具侧解释器（启动 install.py / wf-dev-deploy.py）：与运行器同解释器，与 SUT 驱动面
# 不共用默认——install.py::runtime_support 用 sys.executable 自检，不受锚点耦合影响。
TOOL_PYTHON = sys.executable
# 仓库根与 wflib 路径（替代散落各套件的硬编码绝对路径；WF_TEST_LIB 优先=发行副本）。
# wfdrive.py 位于 <repo>/scripts/tests/wf_runtime/full/，故上溯 5 层 dirname。
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))))))
LIB = os.environ.get("WF_TEST_LIB") or os.path.join(REPO, "docs", "workflows", "wf", "payload", "lib")
TS = "2026-11-03T00:00:00.000000Z"


def deny_writes(path):
    """让 path 暂时满足 deny 契约，返回恢复令牌；契约建立不了即抛异常（fail-closed）。

    deny 契约（按行为定义，不按机制）：对 path 内**新建条目**、**改写已存在文件**、
    **删除已存在条目**都必须失败。两环境按同一契约对拍，不比较机制细节。

    双机制按探针结果选择（不按环境猜测）：
    - chmod 层：目录 0o555、文件 0o444——普通用户路径即成立；
    - root 场景 chmod 不约束（探针仍通过）→ 升级 ro bind mount
      （mount --bind + remount,bind,ro；user namespace 内可用，namespace.py 同机制）。
    任一探针在两层后仍通过 → 抛异常：注入未建立，测试不得继续，
    杜绝"注入失效但套件绿灯"。失败路径自动恢复原状，不留半拒绝状态。
    """
    path = os.path.abspath(str(path))
    if not os.path.isdir(path):
        raise RuntimeError(f"deny_writes: 不是目录：{path}")
    sentinel = os.path.join(path, ".wf-deny-sentinel")
    if not os.path.exists(sentinel):
        with open(sentinel, "w", encoding="utf-8") as handle:
            handle.write("sentinel\n")
        sentinel_created = True
    else:
        sentinel_created = False
    targets = [path]
    for base, dirs, names in os.walk(path):
        targets.extend(os.path.join(base, name) for name in names + dirs)
    original = {target: (os.stat(target).st_mode & 0o7777) for target in targets}
    token = {"path": path, "modes": original, "sentinel_created": sentinel_created,
             "mounted": False}
    try:
        for target in targets:
            os.chmod(target, 0o555 if os.path.isdir(target) else 0o444)
        problems = _probe_denied(path)
        if problems:
            # 探测残留必须在进入 mount 层前删除干净（ro 下删不掉，且会污染后续
            # fixture 空态/模板校验）：先恢复模式，兜底清理，再挂载。
            for target, mode in original.items():
                os.chmod(target, mode)
            check = os.path.join(path, ".wf-deny-check")
            if os.path.exists(check):
                os.unlink(check)
            subprocess.run(["mount", "--bind", path, path], check=True)
            subprocess.run(["mount", "-o", "remount,bind,ro", path], check=True)
            token["mounted"] = True
            problems = _probe_denied(path)
        if problems:
            raise RuntimeError(f"deny_writes: 契约未建立（探针通过：{', '.join(problems)}）")
    except Exception:
        allow_writes(token)
        raise
    return token


def allow_writes(token):
    """按 deny_writes 的令牌恢复：先 umount（若挂载），再恢复原模式，最后删助手哨兵。"""
    path = token["path"]
    if token.get("mounted"):
        subprocess.run(["umount", path], check=True)
        token["mounted"] = False
    for target, mode in token["modes"].items():
        os.chmod(target, mode)
    if token.get("sentinel_created"):
        sentinel = os.path.join(path, ".wf-deny-sentinel")
        if os.path.exists(sentinel):
            os.unlink(sentinel)
    return True


def _probe_denied(path):
    """三探针：新建/改写/删除都必须失败。返回未成立的探针名列表（空 = 契约成立）。"""
    problems = []
    check = os.path.join(path, ".wf-deny-check")
    try:
        fd = os.open(check, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
        os.close(fd)
        os.unlink(check)
        problems.append("create")
    except OSError:
        pass
    sentinel = os.path.join(path, ".wf-deny-sentinel")
    try:
        with open(sentinel, "r+b"):
            pass
        problems.append("modify")
    except OSError:
        pass
    try:
        os.unlink(sentinel)
        # unlink 成功 = 删除未被拒；重建哨兵让后续探针仍有目标（此刻目录必可写）。
        with open(sentinel, "w", encoding="utf-8") as handle:
            handle.write("sentinel\n")
        problems.append("unlink")
    except OSError:
        pass
    return problems


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

        wf(["sampling", "pick", "--task", task_id, "--freeze", "--json"], {"generation": gen}, "sess-A")
    """
    return run(["sampling", "pick", "--task", task_id, "--freeze", "--json"],
               inputs={"generation": generation}, sid=sid, instance_id=instance_id, show=False)


AXES = ("range", "acceptance", "contract", "regression", "testability")


def main_review(task_id, slots, findings=(), axes=None, round_no=1):
    """主会话复核夹具：五轴 pass、逐报告 primary、逐 finding verified。"""
    axes = axes or {axis: "pass" for axis in AXES}
    return {"task": task_id, "round": int(round_no),
            "axes": {axis: {"conclusion": axes.get(axis, "pass"), "basis": "b",
                            "sources": ["main"], "finding_refs": []} for axis in AXES},
            "report_review": [{"slot": slot, "reliance": "primary",
                               "notes": "报告覆盖与依据可用"} for slot in slots],
            "finding_review": [{"finding_id": item.get("id"), "slot": slot,
                                "check": "verified", "basis": "本地复核"}
                               for slot in slots for item in findings
                               if not item.get("slot") or item.get("slot") == slot]}


def write_main_review(path, task_id, slots, findings=(), axes=None, round_no=1):
    import json as _json
    payload = main_review(task_id, slots, findings=findings, axes=axes, round_no=round_no)
    _json.dump(payload, open(path, "w"), ensure_ascii=False)
    return path


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
