#!/usr/bin/env python3
"""wf-session-identity.py — Codex SessionStart 宿主会话标识适配层（W3-2，三轮 P0-1）。

职责（单文件标准库）：
1. 定位项目根：取本脚本落点（<project>/.codex/hooks/）的上两级——部署落点确定，
   不依赖载荷 cwd；根下无 `.wf/` ⇒ exit 0（非 wf 项目，不写任何文件）。
2. 读 stdin 载荷取 `session_id`（大小写键兼容，与 .codex 既有 hook 同型）。
3. `sys.path` 注入 `<project>/.wf/lib` → `from wflib import session` → 以自身
   /proc 祖先链调 `session.candidates()` 取锚点键（单一实现，不另写锚点推导）。
4. 对每个锚点键写 `.wf/.runtime/host-session-map/<key>.json`
   （{provider:"host", host_id:"codex", session_id, mapped_at, boot}）。
   /clear ⇒ SessionStart 再触发，新 session_id 覆盖同键映射。
5. import wflib 失败 ⇒ exit 0 但写 `.wf/.runtime/host-session-map/import-error`
   时间戳标记（不留静默黑洞）；成功写映射时同批删除该标记（恢复即自愈）。

入口只把该映射当"宿主会话标识通道"消费（等价于读信封的宿主身份，不作其他用途）。
"""

import json
import os
import sys
import time


def _project_root():
    # <project>/.codex/hooks/wf-session-identity.py → 上两级是项目根
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _read_session_id():
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return None
    if not isinstance(payload, dict):
        return None
    for key in ("session_id", "sessionId", "sessionID", "SESSION_ID"):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def main():
    root = _project_root()
    if not os.path.isdir(os.path.join(root, ".wf")):
        return 0                      # 非 wf 项目：不写任何文件
    session_id = _read_session_id()
    if not session_id:
        return 0                      # 载荷无会话标识：没有可映射的事实
    map_dir = os.path.join(root, ".wf", ".runtime", "host-session-map")
    os.makedirs(map_dir, exist_ok=True)
    error_path = os.path.join(map_dir, "import-error")
    lib_dir = os.path.join(root, ".wf", "lib")
    if lib_dir not in sys.path:
        sys.path.insert(0, lib_dir)
    try:
        from wflib import session as session_mod

        candidates = session_mod.candidates()
        keys = [session_mod.anchor_key(item) for item in candidates if item]
        if not keys:
            return 0
        boot = candidates[-1].get("boot") if candidates else None
        mapped_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        for key in keys:
            safe = "".join(ch if ch.isalnum() or ch in ".-_" else "-" for ch in str(key))
            path = os.path.join(map_dir, f"{safe}.json")
            tmp = path + ".tmp"
            with open(tmp, "w", encoding="utf-8") as handle:
                json.dump({"provider": "host", "host_id": "codex",
                          "session_id": session_id, "mapped_at": mapped_at,
                          "boot": boot}, handle, ensure_ascii=False, indent=2)
                handle.write("\n")
            os.replace(tmp, path)
        # 恢复即自愈：成功写映射时删除 import-error 标记（新映射就是恢复证据）
        if os.path.isfile(error_path):
            try:
                os.remove(error_path)
            except OSError:
                pass
    except Exception as exc:          # noqa: BLE001 — hook 不打断宿主启动
        try:
            with open(error_path, "w", encoding="utf-8") as handle:
                json.dump({"at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                           "error": f"{type(exc).__name__}: {exc}"[:300]},
                          handle, ensure_ascii=False)
                handle.write("\n")
        except OSError:
            pass                       # 连标记都写不了：只剩宿主日志可查，不崩
        return 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
