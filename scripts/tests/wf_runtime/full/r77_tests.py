#!/usr/bin/env python3
"""第四十一轮 R77：巡检治理面的未知处理（未知不当零、非法配置、畸形条目、改名映射）。"""
import json, os, subprocess, sys
sys.path.insert(0, "/tmp")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, "/home/xzc/projects/personal/ai-coding-toolkit/docs/workflows/新项目开发工作流/payload/lib")
import wfdrive
from wflib import tasks as wf_tasks

F = wfdrive.FIX
results = []
CONFIG = os.path.join(F, ".wf/project-config.json")


def rec(name, expected, actual, ok):
    results.append({"case": name, "expected": expected, "actual": actual, "pass": bool(ok)})
    print(f"[{'PASS' if ok else 'FAIL'}] {name}: {actual}")


def governance():
    return wf_tasks._governance_summary(F, list(wf_tasks.iter_tasks(F)), wf_tasks._task_dirs(F)[1])


def reset_samples():
    root = os.path.join(F, ".wf/tasks/archive")
    for base, dirs, files in os.walk(root, topdown=False):
        for name in files:
            if name == "task.json":
                record = json.load(open(os.path.join(base, name), encoding="utf-8"))
                if str(record.get("title", "")).startswith("样本"):
                    os.remove(os.path.join(base, name))
    return


def archive_task(tid, archived_at, terminal, curated, title="样本"):
    directory = os.path.join(F, ".wf/tasks/archive/2026-11", f"{tid}-{title}")
    os.makedirs(directory, exist_ok=True)
    json.dump({"schema_version": 1, "id": tid, "title": title, "status": "archived",
               "terminal": terminal, "archived_at": archived_at, "curation": curated},
              open(os.path.join(directory, "task.json"), "w", encoding="utf-8"), ensure_ascii=False)
    return directory


def set_config(**values):
    config = json.load(open(CONFIG, encoding="utf-8"))
    for key, value in values.items():
        if value is None:
            config.pop(key, None)
        else:
            config[key] = value
    json.dump(config, open(CONFIG, "w", encoding="utf-8"), ensure_ascii=False, indent=2)


backup = open(CONFIG, encoding="utf-8").read()
os.makedirs(os.path.join(F, ".wf/spec/rules"), exist_ok=True)
open(os.path.join(F, ".wf/spec/rules/keep.md"), "w").write("# keep\n")

# 基线：样本充足且可解释 → 允许给候选
reset_samples()
for index in range(6):
    archive_task(f"2026-{index:032x}", f"2026-11-0{index + 1}T00:00:00.000000Z", "normal",
                 [{"path": ".wf/spec/rules/keep.md", "digest": "sha256:" + "1" * 64,
                   "purpose": "x", "released": None}])
base = governance()
rec("0 基线：样本完整才给候选", "statistic_complete=True 且候选非空",
    f"complete={base['spec_usage']['statistic_complete']} candidates={len(base['spec_usage']['reclaim_candidates'])}",
    base["spec_usage"]["statistic_complete"] is True and base["spec_usage"]["reclaim_candidates"])

# ① 样本不足 → 只报 unknown，不给候选
reset_samples()
for index in range(2):
    archive_task(f"2026-{index:032x}", f"2026-11-0{index + 1}T00:00:00.000000Z", "normal", [])
short = governance()
rec("1 样本不足不给候选", "候选为空且 unknown 含样本不足",
    f"candidates={len(short['spec_usage']['reclaim_candidates'])} unknown={len(short['spec_usage']['unknown'])}",
    not short["spec_usage"]["reclaim_candidates"]
    and any("not enough" in item.get("reason", "") for item in short["spec_usage"]["unknown"]))

# ② 样本缺 curation → unknown 且不给候选
reset_samples()
for index in range(6):
    curated = None if index == 3 else []
    archive_task(f"2026-{index:032x}", f"2026-11-0{index + 1}T00:00:00.000000Z", "normal", curated)
missing = governance()
rec("2 样本缺清单不给候选", "候选为空且 unknown 指出缺清单",
    f"candidates={len(missing['spec_usage']['reclaim_candidates'])}",
    not missing["spec_usage"]["reclaim_candidates"]
    and any("curation list" in item.get("reason", "") for item in missing["spec_usage"]["unknown"]))

# ③ 畸形条目（字符串）不抛异常，报 unknown
reset_samples()
for index in range(6):
    curated = ["not-an-object"] if index == 2 else []
    archive_task(f"2026-{index:032x}", f"2026-11-0{index + 1}T00:00:00.000000Z", "normal", curated)
try:
    broken = governance()
    crashed = None
except Exception as exc:  # noqa: BLE001
    broken, crashed = None, type(exc).__name__
rec("3 畸形策展条目不致异常", "正常返回并报 unknown",
    crashed or f"candidates={len(broken['spec_usage']['reclaim_candidates'])}",
    crashed is None and not broken["spec_usage"]["reclaim_candidates"]
    and any("unparsable" in item.get("reason", "") for item in broken["spec_usage"]["unknown"]))

# ④ 改名/合并：样本引用过但已不存在的路径 → unknown
reset_samples()
for index in range(6):
    curated = ([{"path": ".wf/spec/rules/gone.md", "digest": "sha256:" + "9" * 64,
                 "purpose": "x", "released": None}] if index == 5 else [])
    archive_task(f"2026-{index:032x}", f"2026-11-0{index + 1}T00:00:00.000000Z", "normal", curated)
renamed = governance()
rec("4 改名/合并无法映射报 unknown", "unknown 指明路径已不存在",
    [item.get("reason", "")[:40] for item in renamed["spec_usage"]["unknown"]][:2],
    any("no longer exists" in item.get("reason", "") for item in renamed["spec_usage"]["unknown"]))

# ⑤ 非法配置 → 不给候选、不给 due
set_config(spec_reclaim_tasks="bad", inspection_every_tasks=0)
invalid = governance()
rec("5 非法配置不给候选", "候选为空且 unknown 指出配置非法",
    f"candidates={len(invalid['spec_usage']['reclaim_candidates'])} unknown={len(invalid['spec_usage']['unknown'])}",
    not invalid["spec_usage"]["reclaim_candidates"]
    and any("invalid" in item.get("reason", "") for item in invalid["spec_usage"]["unknown"]))
rec("5b 非法配置不给触发结论", "due=None", invalid["inspection"]["due"],
    invalid["inspection"]["due"] is None)

# ⑥ 真实入口：inspect 仍返回结构且带 unknown 事实
open(CONFIG, "w", encoding="utf-8").write(backup)
rc, payload, _ = wfdrive.run(["inspect", "--json"], {"generation": 1}, "sess-A1", show=False)
facts = ((payload or {}).get("facts") or {}).get("governance") or {}
rec("6 inspect 输出治理面事实", "含 spec_usage.unknown",
    sorted(facts.get("spec_usage") or {}),
    "unknown" in (facts.get("spec_usage") or {}))


# ⑦ 活动任务策展不完整 → unknown 且不给候选（依赖优先保护）
def make_active(tid, curated, status="in_progress", include_field=True):
    directory = os.path.join(F, ".wf/tasks", f"{tid}-活动")
    os.makedirs(directory, exist_ok=True)
    record = {"schema_version": 1, "id": tid, "title": "活动", "status": status}
    if include_field:
        record["curation"] = curated
    json.dump(record, open(os.path.join(directory, "task.json"), "w", encoding="utf-8"), ensure_ascii=False)
    return directory


def clear_active():
    root = os.path.join(F, ".wf/tasks")
    for name in os.listdir(root):
        full = os.path.join(root, name)
        if os.path.isdir(full) and name.endswith("-活动"):
            for base, dirs, files in os.walk(full, topdown=False):
                for item in files:
                    os.remove(os.path.join(base, item))
                for item in dirs:
                    os.rmdir(os.path.join(base, item))
            os.rmdir(full)


# 先造完整样本，再让活动任务各自不完整
reset_samples()
clear_active()
open(CONFIG, "w", encoding="utf-8").write(backup)
for index in range(6):
    archive_task(f"2026-{index:032x}", f"2026-11-0{index + 1}T00:00:00.000000Z", "normal", [])

complete = governance()
rec("7 无活动任务时样本完整可给候选", "statistic_complete=True",
    complete["spec_usage"]["statistic_complete"], complete["spec_usage"]["statistic_complete"] is True)

for label, curated, include, reason_key in (
    ("缺 curation 字段", None, False, "active task lacks curation"),
    ("curation 非列表", {"path": "x"}, True, "active task lacks curation"),
    ("条目非对象", ["broken"], True, "active task curation entry unparsable"),
):
    clear_active()
    make_active("2026-" + "b" * 32, curated, include_field=include)
    summary = governance()
    hit = any(reason_key in item.get("reason", "") for item in summary["spec_usage"]["unknown"])
    rec(f"7 {label} → unknown 压制候选", "无候选且含对应未知",
        f"candidates={len(summary['spec_usage']['reclaim_candidates'])} hit={hit}",
        not summary["spec_usage"]["reclaim_candidates"] and hit)

# 活动任务引用已消失的 spec
clear_active()
make_active("2026-" + "c" * 32, [{"path": ".wf/spec/rules/vanished.md", "digest": "sha256:" + "7" * 64,
                                  "purpose": "x", "released": None}])
summary = governance()
rec("7 活动任务引用已消失 spec → unknown", "无候选且含 no longer exists",
    f"candidates={len(summary['spec_usage']['reclaim_candidates'])}",
    not summary["spec_usage"]["reclaim_candidates"]
    and any("no longer exists" in item.get("reason", "") for item in summary["spec_usage"]["unknown"]))

clear_active()
reset_samples()


# ⑧ 归档记录事实不完整 → unknown 压制候选与触发
def clear_samples_titles():
    root = os.path.join(F, ".wf/tasks/archive")
    for base, dirs, files in os.walk(root, topdown=False):
        for name in files:
            if name == "task.json":
                full = os.path.join(base, name)
                record = json.load(open(full, encoding="utf-8"))
                if str(record.get("title", "")).startswith("样本"):
                    os.remove(full)


def archive_raw(tid, **fields):
    directory = os.path.join(F, ".wf/tasks/archive/2026-11", f"{tid}-样本")
    os.makedirs(directory, exist_ok=True)
    record = {"schema_version": 1, "id": tid, "title": "样本"}
    record.update(fields)
    json.dump(record, open(os.path.join(directory, "task.json"), "w", encoding="utf-8"), ensure_ascii=False)
    return directory


clear_active()
clear_samples_titles()
open(CONFIG, "w", encoding="utf-8").write(backup)
set_config(spec_reclaim_tasks=2, inspection_every_tasks=2)

# 完整记录 → 有候选、due 有结论
for index in range(4):
    archive_raw(f"2026-{index:032x}", status="archived", terminal="normal",
                archived_at=f"2026-11-0{index + 1}T00:00:00.000000Z", curation=[])
ok_summary = governance()
rec("8 完整归档记录可统计", "complete=True 且 due 有结论",
    f"complete={ok_summary['spec_usage']['statistic_complete']} due={ok_summary['inspection']['due']}",
    ok_summary["spec_usage"]["statistic_complete"] is True and ok_summary["inspection"]["due"] is not None)

# 缺 archived_at → unknown 且不给候选/不给 due
clear_samples_titles()
for index in range(4):
    fields = {"status": "archived", "terminal": "normal", "curation": []}
    if index != 1:
        fields["archived_at"] = f"2026-11-0{index + 1}T00:00:00.000000Z"
    archive_raw(f"2026-{index:032x}", **fields)
missing_at = governance()
rec("8 缺 archived_at → unknown 压制", "候选 0 且 due=None",
    f"candidates={len(missing_at['spec_usage']['reclaim_candidates'])} due={missing_at['inspection']['due']}",
    not missing_at["spec_usage"]["reclaim_candidates"] and missing_at["inspection"]["due"] is None
    and any("archived_at" in item.get("reason", "") for item in missing_at["spec_usage"]["unknown"]))

# 记录仍非 archived 状态 → unknown
clear_samples_titles()
for index in range(4):
    archive_raw(f"2026-{index:032x}", status="in_progress", terminal="normal",
                archived_at=f"2026-11-0{index + 1}T00:00:00.000000Z", curation=[])
state_bad = governance()
rec("8 目录在归档区但 status 非 archived → unknown", "候选 0 且给状态未知",
    f"candidates={len(state_bad['spec_usage']['reclaim_candidates'])}",
    not state_bad["spec_usage"]["reclaim_candidates"]
    and any("status=archived" in item.get("reason", "") for item in state_bad["spec_usage"]["unknown"]))

# terminal 非法 → unknown
clear_samples_titles()
for index in range(4):
    archive_raw(f"2026-{index:032x}", status="archived", terminal=None,
                archived_at=f"2026-11-0{index + 1}T00:00:00.000000Z", curation=[])
terminal_bad = governance()
rec("8 terminal 非法 → unknown", "候选 0 且给 terminal 未知",
    f"candidates={len(terminal_bad['spec_usage']['reclaim_candidates'])}",
    not terminal_bad["spec_usage"]["reclaim_candidates"]
    and any("legal terminal" in item.get("reason", "") for item in terminal_bad["spec_usage"]["unknown"]))

clear_samples_titles()
open(CONFIG, "w", encoding="utf-8").write(backup)

json.dump(results, open("/tmp/r77_results.json", "w"), ensure_ascii=False, indent=2)
print("saved", sum(1 for r in results if r["pass"]), "/", len(results))


