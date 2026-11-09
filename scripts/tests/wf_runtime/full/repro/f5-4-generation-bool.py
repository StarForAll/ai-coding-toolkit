#!/usr/bin/env python3
"""F5-4：写权代次为 JSON 布尔时必须结构化拒绝（`true` 不是整数代次）。

缺陷形态：`isinstance(generation, int)` 对 Python 的 bool 也为真，
于是 `generation: true` 的写权记录能进入维护写入并被推进代次。
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _harness as H


def _fixture(root):
    target = os.path.join(root, "proj")
    source = os.path.join(root, "release")
    skill_root = os.path.join(target, ".cursor/skills")
    os.makedirs(os.path.join(source, "skills/wf-start"), exist_ok=True)
    open(os.path.join(source, "skills/wf-start/SKILL.md"), "w").write("v1\n")
    os.makedirs(os.path.join(target, ".wf/install"), exist_ok=True)
    installation = {"schema_version": 1, "release_ref": "refs/tags/wf-v0.1.0", "source_commit": "c0",
                    "version": "0.1.0", "rules_digest": H.RULES_DIGEST,
                    "platforms": ["dsh"], "roots": [".agents/skills"],
                    "assets": [{"target": ".wf/bin/wf.py", "root_ref": "project",
                                "digest": "sha256:x", "source_path": "bin/wf.py"}],
                    "decisions": [], "installed_at": "2026-11-05T00:00:00.000000Z",
                    "tool": "install.py"}
    json.dump(installation, open(os.path.join(target, ".wf/install/installation.json"), "w"),
              ensure_ascii=False, indent=2)
    writer = {"schema_version": 1, "id": "writer", "revision": 0,
              "created_at": "2026-11-05T00:00:00.000000Z", "updated_at": "2026-11-05T00:00:00.000000Z",
              "write_mark": None, "action": None, "state": "idle", "generation": True,
              "holder": None, "handover": None, "checkpoint": None, "maintenance_results": []}
    json.dump(writer, open(os.path.join(target, ".wf/writer.json"), "w"), ensure_ascii=False, indent=2)
    args = argparse.Namespace(target=target, source=source, platform=["cursor"], confirm=True,
                             json=True, release_ref="refs/tags/wf-v0.1.0")
    writes = [(skill_root, {"target_class": "skill_root", "source_path": "skills/wf-start/SKILL.md",
                            "digest": "sha256:y", "executable": False}, "wf-start/SKILL.md")]
    return target, installation, writer, args, writes, skill_root


def check():
    root, lib, payload = H.stage()
    H.load(lib)
    sys.path.insert(0, payload)
    if os.environ.get("WF_REPRO_INJECT") == "1":
        H.patch(os.path.join(payload, "install.py"),
                "if not isinstance(generation, int) or isinstance(generation, bool):",
                "if not isinstance(generation, int):  # 注入：放过 JSON 布尔")
    import install as wf_install

    target, installation, writer, args, writes, skill_root = _fixture(root)
    before = open(os.path.join(target, ".wf/writer.json"), encoding="utf-8").read()
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
                        "WF_RECORD_INVALID", "add_platforms")
    after = open(os.path.join(target, ".wf/writer.json"), encoding="utf-8").read()

    problems = []
    if rc == 0:
        problems.append("generation=true 被接受（未拒绝）")
    if "WF_RECORD_INVALID" not in out:
        problems.append(f"原因码不是 WF_RECORD_INVALID：{out.strip()[:120]}")
    if after != before:
        problems.append("拒绝路径仍改写了 writer 记录")
    if os.path.exists(os.path.join(skill_root, "wf-start/SKILL.md")):
        problems.append("拒绝路径仍投放了技能文件")
    if problems:
        raise H.TargetFailure("；".join(problems))
    return None


if __name__ == "__main__":
    sys.exit(H.main(check))
