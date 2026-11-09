#!/usr/bin/env python3
"""631 Trellis 互斥：人确认「已停用」的放行通道必须可达。

obligation（设计稿 §3「仅残留数据且经人核对有效指令来源已移除/停用时可继续」）：
适用配置存在时，默认仍是 `WF_SEMANTIC_DECISION`（不擅自放行）；
但人显式声明「已停用」后必须能继续启用，并把这条人判留痕——
否则该分支只能靠物理删文件实现，等于不可达。
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _harness as H
import _snapshot as S

SID = "sess-EN631"
FROM = '    if state["blocks"] or unknown or (applicable and not disabled):\n'
TO = '    if state["blocks"] or unknown or applicable:  # 注入：停用分支不可达\n'


def check():
    root, _lib, _payload = H.stage()
    project = H.deploy(root)
    H.ensure_project_config(project)
    # 当前宿主（dsh）的配置里出现 trellis 字样 → applicable
    os.makedirs(os.path.join(project, ".dsh"), exist_ok=True)
    open(os.path.join(project, ".dsh", "hooks.json"), "w", encoding="utf-8").write(
        '{"hooks":[{"name":"trellis-sync"}]}')
    if os.environ.get("WF_REPRO_INJECT") == "1":
        H.patch(os.path.join(project, ".wf/lib/wflib/cli.py"), FROM, TO)
    problems = []

    rc, payload = H.cli(project, ["enable", "--json"], sid=SID,
                        inputs={"generation": H.generation(project)})
    H.require_business_code(payload, rc)
    H.only_two_outcomes((payload or {}).get("code") if rc != 0 else "WF_OK",
                        "WF_SEMANTIC_DECISION", "631 默认不放行")
    if rc == 0:
        problems.append("未声明停用时默认放行了")

    rc, payload = H.cli(project, ["enable", "--json"], sid=SID,
                        inputs={"generation": H.generation(project), "trellis_disabled_confirmed": True})
    if rc != 0 or (payload or {}).get("code") != "WF_OK":
        problems.append(f"人确认停用后仍未放行：{(payload or {}).get('code')}")
    else:
        warnings = (payload or {}).get("warnings") or []
        if not any(item.get("reason") == "trellis_files_present_but_disabled_confirmed" for item in warnings):
            problems.append(f"未留下「人已确认停用」的留痕：{warnings}")
        if ((payload or {}).get("facts") or {}).get("trellis_disabled_confirmed") is not True:
            problems.append("facts 未记录人判依据")
    if problems:
        raise H.TargetFailure("；".join(problems))
    return None


if __name__ == "__main__":
    sys.exit(H.main(check))
