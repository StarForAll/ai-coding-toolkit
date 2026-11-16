#!/usr/bin/env python3
"""source_coverage.py — 逐 ID 来源/覆盖表（AC17/AC18 的机器可读事实）。

输入是**运行期真实注册面**：`units.json` 的完整 `units` 数组与 repro 目录的
`all_cases()` 发现结果 + `groups.json` 元数据。输出逐 ID 行：

- units：kind、fixture、script、candidate_clean（true/false/未声明）、处置（disposition）；
- repro：分组成员关系、元数据是否存在、candidate_clean 状态、处置；
- 集合身份差集：相对 `coverage-baseline.json` 的新增/删除/改名分组。

处置是**登记事实**，不是字符串扫描的推断：`candidate-eligible` 只给注册表显式
`candidate_clean=true` 的条目；白盒/源码注入项保持 dev-only 并记录原因类别。表本身
不把未执行项计为 passed。

用法：
    source_coverage.py [--format table|json] [--out PATH]
    source_coverage.py --baseline-out PATH      # 生成/更新基线（需人工审阅）
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
REPRO = HERE / "repro"
BASELINE = HERE / "coverage-baseline.json"
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(REPRO))


class CoverageError(Exception):
    pass


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _units():
    with open(HERE / "units.json", encoding="utf-8") as handle:
        return json.load(handle)


def _groups():
    with open(REPRO / "groups.json", encoding="utf-8") as handle:
        return json.load(handle)


def _discovered():
    repro_select = _load("wf_coverage_repro_select", REPRO / "repro_select.py")
    return repro_select.all_cases()


# 真实来源证据（机械可复算）：只用于**登记事实**，不据此自动把条目标成 candidate。
AUTHOR_SOURCE_PATTERNS = (
    ("payload-path", re.compile(r"\bpayload/")),
    ("author-release-tree", re.compile(r"wf-release")),
    ("author-install-script", re.compile(r"install\.py")),
    ("author-repo-path", re.compile(r"wfdrive\.REPO|docs/workflows")),
    ("source-injection", re.compile(r"\bstage\(|\bpatch\(")),
)
INSTALLED_RUNTIME_PATTERNS = (
    ("fixture-root", re.compile(r"wfdrive\.FIX|\.wf/")),
    ("installed-lib", re.compile(r"wfdrive\.LIB")),
    ("installed-cli", re.compile(r"wfdrive\.(WF|run)\b")),
)


def _script_evidence(path):
    try:
        data = Path(path).read_bytes()
        text = data.decode("utf-8", "replace")
    except OSError as exc:
        return {"script_sha256": None, "error": str(exc), "source_layer": "unknown",
                "author_source_refs": [], "installed_refs": []}
    author = sorted({code for code, pattern in AUTHOR_SOURCE_PATTERNS if pattern.search(text)})
    installed = sorted({code for code, pattern in INSTALLED_RUNTIME_PATTERNS if pattern.search(text)})
    if author and installed:
        layer = "mixed"
    elif author:
        layer = "author-source"
    elif installed:
        layer = "installed-fixture"
    else:
        layer = "unknown"
    return {"script_sha256": "sha256:" + hashlib.sha256(data).hexdigest(),
            "source_layer": layer, "author_source_refs": author,
            "installed_refs": installed}


def _load_audit():
    path = HERE / "candidate-audit.json"
    try:
        with open(path, encoding="utf-8") as handle:
            return json.load(handle)
    except (OSError, ValueError):
        return {"units": {}}


def _unit_disposition(entry, meta_state, evidence, audit):
    kind = entry.get("kind")
    if kind == "manual":
        return {"migration_status": "manual", "can_run_installed": "not-applicable",
                "not_migratable_reason": None,
                "installed_assertion": "notes: 需真实宿主条件（见 units.json notes）"}
    if kind in ("flow", "extra"):
        return {"migration_status": "not-a-candidate-suite",
                "can_run_installed": "not-applicable",
                "not_migratable_reason": "flow/extra 由 full/representative 选择，不参与 candidate 套件过滤",
                "installed_assertion": "contract full/representative 路径"}
    record = (audit.get("units") or {}).get(entry["name"]) or {}
    # audit 必须对应当前脚本字节；脚本改动后旧 audit 自动失效。
    if record and record.get("script_sha256") != evidence.get("script_sha256"):
        record = {}
    audited = record.get("status") in ("ok", "bad")
    if entry["name"] == "f1_candidate_smoke":
        return {"migration_status": "candidate-verified", "can_run_installed": "verified",
                "not_migratable_reason": None,
                "installed_assertion": "contract candidate representative / candidate smoke 闭环"}
    if meta_state == "true":
        if record.get("status") == "ok":
            return {"migration_status": "candidate-verified",
                    "can_run_installed": "verified",
                    "not_migratable_reason": None,
                    "installed_assertion": f"candidate run {audit.get('version')}: "
                                           + (record.get("tail") or "ok")}
        return {"migration_status": "declared-candidate-unverified",
                "can_run_installed": "not-tested" if not audited else "failed",
                "not_migratable_reason": None if not audited else
                (record.get("tail") or "candidate run failed"),
                "installed_assertion": "candidate run evidence missing"}
    if record.get("status") == "ok":
        return {"migration_status": "migratable-verified-pending-promotion",
                "can_run_installed": "verified",
                "not_migratable_reason": None,
                "installed_assertion": f"candidate run {audit.get('version')}: "
                                       + (record.get("tail") or "ok")}
    note = (entry.get("notes") or "").strip()
    if audited:
        evidence = (record.get("failures") or [])
        if note and "fake-tree" in note:
            return {"migration_status": "kept-dev-only", "can_run_installed": "not-applicable",
                    "not_migratable_reason": note,
                    "installed_assertion": "none（fake-tree runner audit；非安装项目行为）"}
        reason = ("candidate run failed: " + (evidence[0] if evidence else
                  f"status={record.get('status')} rc={record.get('rc')} "
                  f"observed={record.get('observed')} expected={record.get('expected')}"))
        return {"migration_status": "kept-dev-only", "can_run_installed": "failed",
                "not_migratable_reason": reason,
                "installed_assertion": "none in candidate mode（保留源码行为断言）"}
    return {"migration_status": "not-tested", "can_run_installed": "not-tested",
            "not_migratable_reason": None,
            "installed_assertion": "candidate run evidence missing"}


def _repro_disposition(grouped, meta_state, evidence):
    if grouped and meta_state == "true":
        return {"migration_status": "candidate-verified", "can_run_installed": "verified",
                "not_migratable_reason": None,
                "installed_assertion": "contract candidate repro group（groups.json candidate_clean）"}
    if meta_state == "true":
        return {"migration_status": "declared-candidate-unverified",
                "can_run_installed": "not-tested", "not_migratable_reason": None,
                "installed_assertion": "groups.json candidate_clean 但无分组/运行证据"}
    if evidence["source_layer"] in ("author-source", "mixed"):
        reason = ("uses author source/payload or source injection（"
                  + ",".join(evidence["author_source_refs"]) + "）；源码回退在 candidate 被禁止")
    elif evidence["source_layer"] == "installed-fixture":
        reason = "installed-fixture only but candidate_clean not declared（未在本任务迁移）"
    else:
        reason = "source layer unknown"
    return {"migration_status": "kept-dev-only", "can_run_installed": "not-tested",
            "not_migratable_reason": reason,
            "installed_assertion": (" f1_candidate_smoke / contract candidate boundaries"
                                   if evidence["source_layer"] == "installed-fixture"
                                   else "none in candidate mode（保留源码行为断言）")}


def build_baseline(units_doc, groups_doc, discovered):
    grouped = {}
    for group, members in groups_doc.get("groups", {}).items():
        for case in members:
            grouped.setdefault(case, []).append(group)
    meta = groups_doc.get("cases") or {}
    baseline = {
        "schema_version": 1,
        "units": {entry["name"]: {"kind": entry.get("kind"),
                                  "script": entry.get("script", entry["name"] + ".py"),
                                  "candidate_clean": entry.get("candidate_clean", "<missing>")}
                  for entry in units_doc["units"]},
        "repro": {name: {"groups": sorted(grouped.get(name, [])),
                         "metadata": bool(name in meta),
                         "candidate_clean": (meta.get(name) or {}).get("candidate_clean", "<missing>")}
                  for name in discovered},
        "groups": {name: sorted(members) for name, members in
                   (groups_doc.get("groups") or {}).items()},
    }
    return baseline


def diff_against_baseline(current, baseline):
    differences = {"units_added": [], "units_removed": [], "units_changed": [],
                   "repro_added": [], "repro_removed": [], "repro_changed": [],
                   "groups_changed": []}
    for section, added, removed, changed in (
            ("units", differences["units_added"], differences["units_removed"],
             differences["units_changed"]),
            ("repro", differences["repro_added"], differences["repro_removed"],
             differences["repro_changed"])):
        current_rows, baseline_rows = current[section], baseline[section]
        added.extend(sorted(set(current_rows) - set(baseline_rows)))
        removed.extend(sorted(set(baseline_rows) - set(current_rows)))
        changed.extend(sorted(name for name in set(current_rows) & set(baseline_rows)
                              if current_rows[name] != baseline_rows[name]))
    if current.get("groups") != baseline.get("groups"):
        differences["groups_changed"] = sorted(set(current.get("groups") or {})
                                               ^ set(baseline.get("groups") or {}))
    differences["changed"] = any(value for value in differences.values())
    return differences


def coverage():
    units_doc = _units()
    groups_doc = _groups()
    discovered = _discovered()
    grouped = {}
    for group, members in groups_doc.get("groups", {}).items():
        for case in members:
            grouped.setdefault(case, []).append(group)
    meta = groups_doc.get("cases") or {}
    audit = _load_audit()
    rows = {"units": {}, "repro": {}}
    for entry in units_doc["units"]:
        state = entry.get("candidate_clean", "<missing>")
        meta_state = "true" if state is True else ("false" if state is False else "missing")
        script = entry.get("script", entry["name"] + ".py")
        evidence = _script_evidence(HERE / script)
        disposition = _unit_disposition(entry, meta_state, evidence, audit)
        rows["units"][entry["name"]] = {
            "kind": entry.get("kind"),
            "fixture": entry.get("fixture"),
            "script": script,
            "technical_note": (entry.get("notes") or "").strip() or None,
            **evidence,
            "candidate_clean": meta_state,
            "expect": entry.get("expect"),
            **disposition,
        }
    for name in discovered:
        entry = meta.get(name) or {}
        state = entry.get("candidate_clean", "<missing>")
        meta_state = "true" if state is True else ("false" if state is False else "missing")
        evidence = _script_evidence(REPRO / (name + ".py"))
        disposition = _repro_disposition(bool(grouped.get(name)), meta_state, evidence)
        rows["repro"][name] = {
            "groups": sorted(grouped.get(name, [])),
            "metadata": bool(name in meta),
            "candidate_clean": meta_state,
            **evidence,
            **disposition,
        }
    current = build_baseline(units_doc, groups_doc, discovered)
    baseline = None
    if BASELINE.is_file():
        with open(BASELINE, encoding="utf-8") as handle:
            baseline = json.load(handle)
    differences = diff_against_baseline(current, baseline) if baseline else None
    return {"rows": rows, "current": current, "baseline": baseline,
            "differences": differences,
            "counts": {
                "units_total": len(rows["units"]),
                "units_by_kind": {kind: sum(1 for row in rows["units"].values()
                                            if row["kind"] == kind)
                                  for kind in sorted({row["kind"] for row in rows["units"].values()})},
                "repro_discovered": len(rows["repro"]),
                "repro_grouped": sum(1 for row in rows["repro"].values() if row["groups"]),
                "repro_ungrouped": sum(1 for row in rows["repro"].values() if not row["groups"]),
                "repro_with_metadata": sum(1 for row in rows["repro"].values() if row["metadata"]),
                "repro_candidate_clean": sum(1 for row in rows["repro"].values()
                                             if row["candidate_clean"] == "true"),
                "units_candidate_verified": sum(1 for row in rows["units"].values()
                                                if row["migration_status"] == "candidate-verified"),
                "units_kept_dev_only": sum(1 for row in rows["units"].values()
                                           if row["migration_status"] == "kept-dev-only"),
                "units_pending_promotion": sum(1 for row in rows["units"].values()
                                               if row["migration_status"]
                                               == "migratable-verified-pending-promotion"),
                "units_not_tested": sum(1 for row in rows["units"].values()
                                        if row["migration_status"] == "not-tested"),
            }}


def print_table(result):
    counts = result["counts"]
    print(f"units: {counts['units_total']} {counts['units_by_kind']}")
    print(f"repro: discovered={counts['repro_discovered']} grouped={counts['repro_grouped']} "
          f"ungrouped={counts['repro_ungrouped']} metadata={counts['repro_with_metadata']} "
          f"candidate_clean={counts['repro_candidate_clean']}")
    for name, row in sorted(result["rows"]["units"].items()):
        print(f"unit\t{name}\t{row['kind']}\t{row['candidate_clean']}\t"
              f"{row['migration_status']}\t{row['source_layer']}\t"
              f"{','.join(row['author_source_refs']) or '-'}")
    for name, row in sorted(result["rows"]["repro"].items()):
        groups = ",".join(row["groups"]) or "-"
        print(f"repro\t{name}\t{groups}\t{row['candidate_clean']}\t"
              f"{row['migration_status']}\t{row['source_layer']}")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--format", default="table", choices=("table", "json"))
    parser.add_argument("--out", default=None)
    parser.add_argument("--baseline-out", default=None)
    args = parser.parse_args(argv)
    try:
        result = coverage()
    except (OSError, ValueError, CoverageError) as exc:
        print(f"COVERAGE-ERROR: {exc}", file=sys.stderr)
        return 2
    if args.baseline_out:
        with open(args.baseline_out, "w", encoding="utf-8") as handle:
            json.dump(result["current"], handle, ensure_ascii=False, indent=2, sort_keys=True)
            handle.write("\n")
        print(f"BASELINE-WRITTEN: {args.baseline_out}")
        return 0
    if args.format == "json":
        payload = json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True)
    else:
        import io
        # 单一渲染实现：先写进缓冲，再决定 stdout / --out。
        rendered = io.StringIO()
        stdout, sys.stdout = sys.stdout, rendered
        try:
            print_table(result)
        finally:
            sys.stdout = stdout
        payload = rendered.getvalue()
    if args.out:
        Path(args.out).write_text(payload, encoding="utf-8")
        print(f"COVERAGE-WRITTEN: {args.out}")
    else:
        print(payload)
    if result["differences"] and result["differences"]["changed"]:
        print("COVERAGE-DIFF: " + json.dumps(result["differences"], ensure_ascii=False,
                                             sort_keys=True), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
