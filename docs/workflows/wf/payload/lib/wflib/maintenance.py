"""maintenance.py — 维护回执的**提交层账本**（机制稿 §4.5）。

为什么需要独立账本：`.wf/writer.json` 是运行态（v42 S10 明确忽略），把它当"回执是否已持久化"
的证据，会让所有回执永远停在 `applied_pending_commit`（实测：探针读不到它 → 永远 pending）。
账本放到 `.wf/install/`——它已是 protocol 里的**项目数据**（committed 层），与
`release-manifest.json` / `installation.json` 同层，不新增层、不改 S10。

一行一条 append-only 记录：
`{operation, preview_digest, head_before, changes: [{path, before, after}], at}`
"""

from __future__ import annotations

import json
import os

from . import records

JOURNAL_REL = ".wf/install/maintenance.jsonl"


def append(root, entry):
    """把一次维护操作的结果追加进账本（调用方负责把它纳入同一次提交）。"""
    record = {
        "operation": entry.get("operation"),
        "preview_digest": entry.get("preview_digest"),
        "head_before": entry.get("head_before"),
        "changes": [dict(item) for item in entry.get("changes") or [] if isinstance(item, dict)],
        "at": entry.get("at") or records.now_str(),
    }
    path = os.path.join(str(root), JOURNAL_REL)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
    return record


def parse(text):
    """解析账本文本；坏行**跳过并计数**（不因一行坏了就当整本没有）。"""
    entries, problems = [], []
    for number, line in enumerate((text or "").splitlines(), 1):
        line = line.strip()
        if not line:
            continue
        try:
            item = json.loads(line)
        except ValueError:
            problems.append({"line": number, "reason": "unparsable journal line"})
            continue
        if isinstance(item, dict) and item.get("operation"):
            entries.append(item)
        else:
            problems.append({"line": number, "reason": "journal line lacks operation"})
    return entries, problems


def load(root):
    """读工作树里的账本（用于展示与统计；判定持久化要读**提交树**那份）。"""
    path = os.path.join(str(root), JOURNAL_REL)
    try:
        with open(path, "r", encoding="utf-8") as handle:
            return parse(handle.read())
    except FileNotFoundError:
        return [], []


def find(entries, operation):
    """按 `operation` 找最后一条记录（同一操作可能重入多次，以最后一次为准）。"""
    found = None
    for entry in entries:
        if entry.get("operation") == operation:
            found = entry
    return found
