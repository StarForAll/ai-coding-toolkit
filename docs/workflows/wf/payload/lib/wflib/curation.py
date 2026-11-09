"""curation.py — 任务策展清单（机制稿 §8.3）。"""

from __future__ import annotations

from . import records
from .paths import join


def active_entries(task):
    return [entry for entry in (task.get("curation") or []) if not entry.get("released")]


def add(task, path, digest, purpose):
    entries = [entry for entry in (task.get("curation") or []) if entry.get("path") != path]
    entries.append(
        {
            "path": path,
            "digest": digest,
            "purpose": purpose,
            "selected_at": records.now_str(),
            "released": None,
        }
    )
    task["curation"] = entries
    return task


def release(task, path, *, decision, old_digest, replacement):
    for entry in task.get("curation") or []:
        if entry.get("path") != path:
            continue
        entry["released"] = {
            "decision": decision,
            "old_path": path,
            "old_digest": old_digest,
            "replacement": replacement,
        }
        return task
    return task


def selection_digests(root, task):
    return [
        {"path": entry.get("path"), "digest": records.file_digest(join(root, entry.get("path")))}
        for entry in active_entries(task)
    ]
