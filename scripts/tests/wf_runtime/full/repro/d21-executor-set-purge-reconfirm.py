#!/usr/bin/env python3
"""D21／设计稿 §1.1：purge 后重建得到新项目标识、须重新确认；
同一路径换成另一个项目（项目标识不同）时旧记录不套用。

说明：`uninstall --purge` 入口属第三轮（实现稿 §2.3.11），本用例不跑真实
purge 链路，按同一语义做等价构造：确认后把项目配置的 project_id 换成
purge 重建会得到的新标识，旧确认不得套用（ready 不成立）；恢复原标识后沿用。
注入形态：比对时不核项目标识——换项目后旧记录仍被套用。
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _harness as H
import _executor_set as E

PY = "/usr/bin/python3"


def check():
    root, _lib, _payload = H.stage()
    with E.isolated_home(root):
        project = H.deploy(root)
        H.ensure_project_config(project)
        E.set_executor(project, PY)
        if os.environ.get("WF_REPRO_INJECT") == "1":
            # 注入：不核项目标识（换项目后旧记录仍套用的缺陷形态）
            H.patch(os.path.join(project, ".wf/bin/wf.py"),
                    "    if scope == \"project\" and entry.get(\"project_id\") != project_id:",
                    "    if False:  # 注入：不核项目标识")
        module = E.launcher(project)
        E.confirm(module, project)
        if not E.ready(module, project):
            raise H.Precondition("重建前 ready 不成立（夹具未生效）")

        # purge 重建（等价构造）：新 project_id → 旧确认不得套用
        E.set_project_id(project, "f" * 32)
        if E.ready(module, project):
            raise H.TargetFailure("purge 重建（新 project_id）后旧确认仍被套用")
        return None


if __name__ == "__main__":
    sys.exit(H.main(check))
