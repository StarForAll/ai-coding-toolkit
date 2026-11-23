#!/usr/bin/env python3
"""R93：平台清单即身份事实，缺注入式双模反例（`denominator.md:164` 登记的缺口）。

obligation（机制稿 §1.4、实现稿 §2.3.10.1）：安装记录的 `platforms` 就是本项目的身份事实，
运行时只做成员判定——请求的 `host_id` 不在清单里即 `WF_IDENTITY_UNRESOLVED`，
只读诊断不受此限。此前只有 `r90_tests` 的正向 9/9，没有「注入缺陷后必须变红」的双模证明。

注入形态 = 去掉成员判定（`if host not in installed:` → `if False:`）：
未安装的宿主写操作会被放行，用例必须因此变红。
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _harness as H

SID = "sess-R93FX"
FROM = '    if host not in installed:\n'
TO = '    if False:  # 注入：不看平台清单\n'


def check():
    root, _lib, _payload = H.stage()
    project = H.deploy(root)
    H.ensure_project_config(project)
    if os.environ.get("WF_REPRO_INJECT") == "1":
        H.patch(os.path.join(project, ".wf/lib/wflib/session.py"), FROM, TO)

    installation_path = os.path.join(project, ".wf/install/installation.json")
    with open(installation_path, encoding="utf-8") as handle:
        installation = json.load(handle)
    # 安装面向全部平台（2026-11-23 人裁）：记录里就是全部支持平台
    expected_platforms = sorted(installation.get("platforms") or [])
    if len(expected_platforms) < 2 or "dsh" not in expected_platforms:
        raise H.Precondition(f"安装记录不是全部平台：{expected_platforms}")
    if "session_profile" in installation:
        raise H.Precondition("安装记录里仍有 session_profile（R93 已删除）")

    # "未安装宿主"改成记录里去掉 codex：安装装齐 ≠ 身份清单不可变（清单仍是唯一事实）
    installation["platforms"] = [name for name in expected_platforms if name != "codex"]
    with open(installation_path, "w", encoding="utf-8") as handle:
        json.dump(installation, handle, ensure_ascii=False, indent=2)
    problems = []
    # ① 未安装的宿主要求写操作 → 拒绝（本用例的目标断言）
    rc, payload = H.cli(project, ["enable", "--json"], sid=SID,
                        inputs={"generation": H.generation(project)}, host_id="codex")
    code = (payload or {}).get("code")
    if code != "WF_IDENTITY_UNRESOLVED":
        problems.append(f"未安装宿主的写操作未被拒：rc={rc} code={code}")
    facts = (payload or {}).get("facts") or {}
    if code == "WF_IDENTITY_UNRESOLVED":
        if facts.get("installed_platforms") != installation["platforms"]:
            problems.append(f"facts 未列出已装平台：{facts.get('installed_platforms')}")
        if "install" not in str(facts.get("next") or ""):
            problems.append(f"facts 未给登记出口：{facts.get('next')}")

    # ② 同一会话的只读诊断不受影响
    rc_ro, payload_ro = H.cli(project, ["status", "--json"], sid=SID, host_id="codex")
    if (payload_ro or {}).get("code") != "WF_OK":
        problems.append(f"只读诊断被一并阻断：{(payload_ro or {}).get('code')}")

    if problems:
        raise H.TargetFailure("；".join(problems))
    return None


if __name__ == "__main__":
    sys.exit(H.main(check))
