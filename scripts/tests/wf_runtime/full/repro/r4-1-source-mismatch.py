#!/usr/bin/env python3
"""R4-1／F5-1：追加平台只允许同来源，且拒绝路径零写入（含目录树）。

缺陷形态：来源判据退回只看 `dev:<describe>` 或干脆不核，
于是换过来源的安装记录仍能追加，把新来源的技能混进旧运行时。
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _harness as H


def _tree(path):
    found = []
    for base, dirs, files in os.walk(path):
        dirs[:] = [d for d in dirs if d != ".git"]
        rel = os.path.relpath(base, path).replace(os.sep, "/")
        found.append(rel)
        # .wf-lock 是锁对象本身（获取/复用时必然存在），不算"写入产物"
        found.extend(f"{rel}/{name}" for name in files if name != ".wf-lock")
    return sorted(found)


def check():
    root, lib, payload = H.stage()
    H.load(lib)
    sys.path.insert(0, payload)
    if os.environ.get("WF_REPRO_INJECT") == "1":
        H.patch(os.path.join(payload, "install.py"),
                'if installation.get("source_commit") != commit:',
                'if False:  # 注入：不核来源')
    import install as wf_install

    target = os.path.join(root, "proj")
    source = os.path.join(root, "release")
    skill_root = os.path.join(target, ".claude/skills")
    os.makedirs(os.path.join(source, "skills/wf-start"), exist_ok=True)
    open(os.path.join(source, "skills/wf-start/SKILL.md"), "w").write("v1\n")
    os.makedirs(os.path.join(target, ".wf/install"), exist_ok=True)
    json.dump({"schema_version": 1, "release_ref": "refs/tags/wf-v0.1.0", "source_commit": "OTHER",
               "rules_digest": H.RULES_DIGEST,
               "version": "0.1.0", "platforms": ["dsh"], "roots": [".agents/skills"],
               "assets": [], "decisions": [], "installed_at": "2026-11-05T00:00:00.000000Z",
               "tool": "install.py"},
              open(os.path.join(target, ".wf/install/installation.json"), "w"), indent=2)
    json.dump({"schema_version": 1, "id": "writer", "revision": 0,
               "created_at": "2026-11-05T00:00:00.000000Z", "updated_at": "2026-11-05T00:00:00.000000Z",
               "write_mark": None, "action": None, "state": "idle", "generation": 2,
               "holder": None, "handover": None, "checkpoint": None, "maintenance_results": []},
              open(os.path.join(target, ".wf/writer.json"), "w"), indent=2)
    args = argparse.Namespace(target=target, source=source, platform=["claudecode"],
                             confirm=True, json=True,
                             release_ref="refs/tags/wf-v0.1.0")
    writes = [(skill_root, {"target_class": "skill_root", "source_path": "skills/wf-start/SKILL.md",
                            "digest": "sha256:y", "executable": False}, "wf-start/SKILL.md")]
    before_tree = _tree(target)
    before_writer = open(os.path.join(target, ".wf/writer.json"), encoding="utf-8").read()
    import contextlib
    import io

    buffer = io.StringIO()
    with contextlib.redirect_stdout(buffer):
        rc = wf_install.add_platforms(args, "c0", {"compatibility": {"rules_digest": H.RULES_DIGEST}}, writes, [skill_root])
    out = buffer.getvalue()
    if rc not in (0, 1, 2):
        raise H.Precondition(f"add_platforms 异常退出：rc={rc} out={out.strip()[:160]}")
    # 只承认两种结局：期望码（修复成立）或成功（缺陷复现）；其它码一律前置失败
    _payload = None
    for _line in reversed(out.splitlines()):
        _line = _line.strip()
        if _line.startswith("{"):
            try:
                _payload = json.loads(_line)
            except ValueError:
                _payload = None
            break
    H.only_two_outcomes((_payload or {}).get("code") if rc != 0 else "WF_OK",
                        "WF_ASSET_DECISION", "add_platforms")

    problems = []
    if rc == 0:
        problems.append("来源不同仍追加成功")
    if "WF_ASSET_DECISION" not in out:
        problems.append(f"原因码不是 WF_ASSET_DECISION：{out.strip()[:120]}")
    if _tree(target) != before_tree:
        problems.append("拒绝路径改变了目标目录树")
    if open(os.path.join(target, ".wf/writer.json"), encoding="utf-8").read() != before_writer:
        problems.append("拒绝路径改写了 writer 记录")
    if problems:
        raise H.TargetFailure("；".join(problems))
    return None


if __name__ == "__main__":
    sys.exit(H.main(check))
