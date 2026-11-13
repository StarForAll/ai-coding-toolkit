#!/usr/bin/env python3
"""select.py — repro 用例选择、候选过滤、`--mode auto` 新鲜度与状态提交（唯一实现）。

`repro/run.sh` 只做编排；**选了哪些用例、每个用例跑 green 还是 both、哪些算
skipped_non_candidate** 全部在这里决定，避免 bash 里再算一遍。

子命令：
    plan         输出要跑的用例与每例模式（`--format sh|json`）
    commit-state 读取 `<results>/<case>.json`，只把“已验证”的用例写进状态（父进程唯一写者）
    describe     人读摘要（`--list` 用）

候选语义（方案稿 §5.2）：
    candidate_clean=true 当且仅当 assertion_target=installed 且 stage_role=scaffold
    且不读源码 payload/lib / codes 表。manifest 里写反了这一条 → 直接拒绝。
"""
from __future__ import annotations

import argparse
import datetime
import glob
import hashlib
import json
import os
import re
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", "..", "..", ".."))
GROUPS_JSON = os.path.join(HERE, "groups.json")
HELPERS = ("_harness.py", "_release.py", "_review_flow.py", "_review_launch.py",
           "_snapshot.py", "_executor_set.py")
STATE_SCHEMA = 1


class SelectError(Exception):
    """可预期的拒绝（非零退出）。"""


def now():
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def load_groups(path=GROUPS_JSON):
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def all_cases():
    """用例 = `repro/<name>.py` 且 import 了 `_harness`（helper/runnner 自身不算用例）。"""
    names = []
    for path in sorted(glob.glob(os.path.join(HERE, "[a-z0-9]*.py"))):
        base = os.path.basename(path)
        if base.startswith("_"):
            continue
        try:
            with open(path, encoding="utf-8") as handle:
                head = handle.read(4000)
        except OSError:
            continue
        if not re.search(r"(?m)^import _harness as H\s*$", head):
            continue
        names.append(base[:-3])
    return names


def file_digest(path):
    try:
        with open(path, "rb") as handle:
            return "sha256:" + hashlib.sha256(handle.read()).hexdigest()
    except OSError:
        return None


def helpers_digest():
    digest = hashlib.sha256()
    for name in HELPERS:
        digest.update(name.encode("utf-8"))
        digest.update(str(file_digest(os.path.join(HERE, name))).encode("ascii"))
    return "sha256:" + digest.hexdigest()


def script_digest(case):
    return file_digest(os.path.join(HERE, case + ".py"))


def targets_digest(case, meta):
    targets = (meta or {}).get("targets") or []
    if not targets:
        return None            # 未知目标：auto 按“需要 both”处理（安全默认）
    digest = hashlib.sha256()
    for relative in targets:
        digest.update(relative.encode("utf-8"))
        digest.update(str(file_digest(os.path.join(REPO, *relative.split("/")))).encode("ascii"))
    return "sha256:" + digest.hexdigest()


def candidate_clean(meta):
    return bool((meta or {}).get("candidate_clean"))


def check_candidate_manifest(groups_doc):
    """manifest 不能把 stage/source 用例标成 candidate_clean（防手滑）。"""
    problems = []
    for name, meta in (groups_doc.get("cases") or {}).items():
        if not candidate_clean(meta):
            continue
        if meta.get("assertion_target") != "installed" or meta.get("stage_role") != "scaffold":
            problems.append(f"{name}: candidate_clean=true 但 assertion_target={meta.get('assertion_target')} "
                            f"stage_role={meta.get('stage_role')}")
    if problems:
        raise SelectError("候选 manifest 自相矛盾：\n- " + "\n- ".join(problems))


def select(group_names=(), only="", fixture_deploy="dev", mode="both", groups_doc=None):
    groups_doc = groups_doc or load_groups()
    check_candidate_manifest(groups_doc)
    available = all_cases()
    known = set(available)
    unknown_groups = [name for name in group_names if name not in groups_doc["groups"]]
    if unknown_groups:
        raise SelectError("未知组：" + " ".join(unknown_groups) + "；可选：" +
                          " ".join(sorted(groups_doc["groups"])))
    chosen = list(available)
    skipped_non_candidate = []
    if group_names:
        members = []
        for name in group_names:
            for case in groups_doc["groups"][name]:
                if case not in known:
                    raise SelectError(f"组 {name} 引用了不存在的用例：{case}")
                if case not in members:
                    members.append(case)
        chosen = [case for case in members]
    if only:
        chosen = [case for case in chosen if only in case]
    if not chosen:
        raise SelectError(f"没有用例匹配（group={' '.join(group_names) or '-'} only={only!r}）；"
                          "可用组：" + " ".join(sorted(groups_doc["groups"])))
    if fixture_deploy == "candidate":
        cases_meta = groups_doc.get("cases") or {}
        clean = [case for case in chosen if candidate_clean(cases_meta.get(case))]
        skipped_non_candidate = [case for case in chosen if case not in clean]
        if not clean:
            raise SelectError(
                "candidate 模式下这些用例都不是 candidate_clean=true：" + " ".join(chosen) +
                "；请在 dev 模式跑，或改用 f1_candidate_smoke 兜底闭环")
        chosen = clean
    state_modes = {}
    if mode == "auto":
        state_modes = auto_modes(chosen, groups_doc)
        if fixture_deploy == "candidate":
            need = sorted(name for name, value in state_modes.items() if value == "both")
            if need:
                raise SelectError(
                    "candidate 模式下 --mode auto 检测到需要 red 证伪的用例：" + " ".join(need) +
                    "；请先在 dev 模式跑 --mode both/red（候选模式不执行注入）")
        modes = {name: state_modes.get(name, "both") for name in chosen}
    elif mode == "both":
        modes = {name: "both" for name in chosen}
    elif mode == "green":
        modes = {name: "green" for name in chosen}
    elif mode == "red":
        modes = {name: "red" for name in chosen}
    else:
        raise SelectError(f"未知模式：{mode}")
    return {
        "cases": chosen,
        "modes": modes,
        "skipped_non_candidate": skipped_non_candidate,
        "groups": list(group_names),
        "only": only,
        "fixture_deploy": fixture_deploy,
        "mode": mode,
    }


def state_path():
    cache = os.environ.get("WF_TEST_RUN_CACHE") or os.path.join(os.path.expanduser("~"),
                                                               ".cache", "wf-test-run")
    return os.path.join(cache, "repro-state.json")


def read_state():
    path = state_path()
    try:
        with open(path, encoding="utf-8") as handle:
            state = json.load(handle)
    except (OSError, ValueError):
        return {"schema_version": STATE_SCHEMA, "helpers_digest": None, "cases": {}}
    if not isinstance(state, dict) or state.get("schema_version") != STATE_SCHEMA:
        return {"schema_version": STATE_SCHEMA, "helpers_digest": None, "cases": {}}
    state.setdefault("cases", {})
    return state


def write_state(state):
    path = state_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    handle = tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=os.path.dirname(path),
                                         prefix=".state-", delete=False, suffix=".json")
    try:
        json.dump(state, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    finally:
        handle.close()
    os.replace(handle.name, path)
    return path


def auto_modes(cases, groups_doc):
    """首次运行 / 新用例 / helper 或脚本或被测目标变化 → both；未变化 → green。"""
    state = read_state()
    current_helpers = helpers_digest()
    stale_helpers = state.get("helpers_digest") != current_helpers
    modes = {}
    for case in cases:
        meta = (groups_doc.get("cases") or {}).get(case) or {}
        record = (state.get("cases") or {}).get(case) or {}
        if stale_helpers:
            modes[case] = "both"
            continue
        if record.get("script_digest") != script_digest(case):
            modes[case] = "both"
            continue
        if record.get("targets_digest") != targets_digest(case, meta):
            modes[case] = "both"
            continue
        if not record.get("verified_both_at"):
            modes[case] = "both"
            continue
        modes[case] = "green"
    return modes


def commit_state(results_dir, groups_doc=None):
    """父进程唯一写者：只把 `verified=true` 的用例合并进状态，其余保持原样。"""
    groups_doc = groups_doc or load_groups()
    state = read_state()
    state["helpers_digest"] = helpers_digest()
    updated, kept = [], []
    for path in sorted(glob.glob(os.path.join(results_dir, "*.json"))):
        try:
            with open(path, encoding="utf-8") as handle:
                record = json.load(handle)
        except (OSError, ValueError):
            continue
        case = record.get("case")
        if not case or not record.get("verified"):
            continue
        meta = (groups_doc.get("cases") or {}).get(case) or {}
        entry = {
            "script_digest": script_digest(case),
            "targets_digest": targets_digest(case, meta),
            "mode": record.get("mode"),
            "verified_at": now(),
        }
        if record.get("mode") == "both" or (state["cases"].get(case) or {}).get("verified_both_at"):
            entry["verified_both_at"] = now()
        else:
            entry["verified_both_at"] = (state["cases"].get(case) or {}).get("verified_both_at")
        state["cases"][case] = entry
        updated.append(case)
    for case in state["cases"]:
        if case not in updated:
            kept.append(case)
    return write_state(state), updated, kept


def shell_quote(value):
    return "'" + str(value).replace("'", "'\\''") + "'"


def emit(result, fmt):
    if fmt == "json":
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
        return
    tsv = "".join(f"{case}\t{result['modes'][case]}\n" for case in result["cases"])
    print("REPRO_CASES_TSV=" + shell_quote(tsv))
    print("REPRO_SKIPPED_LIST=" + shell_quote(" ".join(result["skipped_non_candidate"])))
    print("REPRO_CASE_COUNT=" + str(len(result["cases"])))
    print("REPRO_STATE_FILE=" + shell_quote(state_path()))
    print("REPRO_SELECT_OK=1")


def main(argv=None):
    parser = argparse.ArgumentParser(description="repro 用例选择/状态")
    sub = parser.add_subparsers(dest="command", required=True)
    plan_p = sub.add_parser("plan")
    plan_p.add_argument("--group", action="append", default=[])
    plan_p.add_argument("--only", default="")
    plan_p.add_argument("--fixture-deploy", default="dev", choices=("dev", "candidate"))
    plan_p.add_argument("--mode", default="both", choices=("green", "red", "both", "auto"))
    plan_p.add_argument("--format", default="sh", choices=("sh", "json"))
    commit_p = sub.add_parser("commit-state")
    commit_p.add_argument("--results", required=True)
    commit_p.add_argument("--format", default="sh", choices=("sh", "json"))
    describe_p = sub.add_parser("describe")
    describe_p.add_argument("--group", action="append", default=[])
    describe_p.add_argument("--fixture-deploy", default="dev", choices=("dev", "candidate"))
    args = parser.parse_args(argv)
    try:
        if args.command == "plan":
            result = select(args.group, args.only, args.fixture_deploy, args.mode)
            emit(result, args.format)
            return 0
        if args.command == "commit-state":
            path, updated, kept = commit_state(args.results)
            if args.format == "json":
                print(json.dumps({"state": path, "updated": updated, "kept": kept},
                                 ensure_ascii=False, sort_keys=True))
            else:
                print(f"REPRO_STATE={path} updated={len(updated)} kept={len(kept)}")
            return 0
        groups_doc = load_groups()
        for name in sorted(groups_doc["groups"]):
            members = groups_doc["groups"][name]
            clean = [case for case in members if candidate_clean((groups_doc["cases"] or {}).get(case))]
            print(f"{name}: {len(members)} 用例（candidate_clean={len(clean)}）")
            for case in members:
                flag = "candidate" if case in clean else "dev-only"
                print(f"  - {case} [{flag}]")
        return 0
    except SelectError as exc:
        print(f"SELECT-ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
