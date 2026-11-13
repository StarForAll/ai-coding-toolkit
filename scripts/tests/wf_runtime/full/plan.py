#!/usr/bin/env python3
"""plan.py — `run_all.sh` 的**单一执行计划**（唯一权威）。

`--list` / `--dry-run` / 真实执行都消费同一份 `plan()` 的结果：没有第二处选择逻辑。

用法（run_all.sh 会把整串参数原样转进来）：
    python3 plan.py --format sh --full --repro green
    python3 plan.py --format json --dry-run
    python3 plan.py --list

退出码：0 = 计划成立；2 = 选项冲突/未知套件/未知组（stderr 说明）。
"""
from __future__ import annotations

import argparse
import json
import os
import shlex
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SUITES_JSON = os.path.join(HERE, "suites.json")
GROUPS_JSON = os.path.join(HERE, "repro", "groups.json")
DEFAULT_FIX = "/tmp/wf-fixtures/rerun"
DEFAULT_JOBS = 4          # 套件层默认并行数（实测 8 套件 68s → 29s）
DEFAULT_REPRO_JOBS = 4    # repro 用例层默认并行数（实测结果与 jobs=1 逐项一致）
DEV_VERSION_PLACEHOLDER = "0.0.0-dev"
TEST_RELEASE_FALLBACK = "0.1.0"
REPRO_MODES = ("green", "red", "both", "none", "auto")
# 这些套件必须串行（改成不可写目录模拟写入失败：user namespace 里是 root，chmod 不生效）
PARALLEL_SERIAL = {
    "cp3_tests", "cp4_a8", "cp5_b12", "r1r2_tests", "r7r15_tests", "r35_tests",
    "r67_tests", "r68_tests", "r69_tests", "r70_tests", "r71_tests", "r89_tests", "r90_tests",
}


class PlanError(Exception):
    """可预期的计划冲突（非零退出、不打印 traceback）。"""

    def __init__(self, message, code=2):
        super().__init__(message)
        self.code = code


def load_suites(path=SUITES_JSON):
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def load_groups(path=GROUPS_JSON):
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def _repo_root():
    return os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))


def _dev_manifest_version():
    path = os.path.join(_repo_root(), "docs", "workflows", "wf", "dev-manifest.json")
    try:
        with open(path, encoding="utf-8") as handle:
            return (json.load(handle) or {}).get("version")
    except (OSError, ValueError):
        return None


def resolve_test_release_version(explicit=None, dev_version=None, env=None):
    """测试发行版本：显式 → 环境 → dev-manifest 真实版本 → 常量 0.1.0。"""
    env = os.environ if env is None else env
    declared = dev_version if dev_version is not None else _dev_manifest_version()
    requested = explicit or env.get("WF_TEST_RELEASE_VERSION") or None
    if requested:
        if declared and declared != DEV_VERSION_PLACEHOLDER and declared != requested:
            raise PlanError(
                f"测试版本与 dev-manifest 不一致：dev-manifest={declared} requested={requested}"
                "（测试版本需与 dev-manifest 一致或显式更新 dev-manifest）")
        return requested
    if declared and declared != DEV_VERSION_PLACEHOLDER:
        return declared
    return TEST_RELEASE_FALLBACK


def parse_args(argv):
    # run_all.sh 用 `--` 分隔自己的参数与本脚本参数；argparse 不接受裸 `--` 之后的 switch
    argv = [item for item in argv if item != "--"]
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--full", action="store_true")
    parser.add_argument("--subset", action="store_true")
    parser.add_argument("--representative", action="store_true")
    parser.add_argument("--parallel", action="store_true", help="显式并行（现在是默认）")
    parser.add_argument("--serial", action="store_true", help="套件层串行（确定性/排障）")
    parser.add_argument("--list", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--no-build", action="store_true")
    parser.add_argument("--repro", dest="repro_mode", default=None)
    parser.add_argument("--repro-group", dest="repro_groups", action="append", default=[])
    parser.add_argument("--fixture-deploy", dest="fixture_deploy", default=None)
    parser.add_argument("--release-root", default=None)
    parser.add_argument("--release-ref", default=None)
    parser.add_argument("--release-version", default=None)
    parser.add_argument("--release-meta", default=None)
    parser.add_argument("--tags", action="append", default=[], help="按 tag 选择套件（可重复/逗号分隔）")
    parser.add_argument("--changed", action="store_true",
                        help="只给建议：按改动文件映射套件与 repro 组（必须配合 --list）")
    parser.add_argument("--changed-base", default=None, help="--changed 的比较基线（默认 HEAD）")
    parser.add_argument("--changed-files", default=None,
                        help="显式给出改动文件列表（空格分隔；CI 用，免 git）")
    parser.add_argument("--format", default="sh", choices=("sh", "json"))
    parser.add_argument("-h", "--help", action="store_true")
    return parser.parse_args(argv)


def _explicit_mode(args):
    chosen = [name for name, flag in (("full", args.full), ("subset", args.subset),
                                      ("representative", args.representative)) if flag]
    if len(chosen) > 1:
        raise PlanError("模式互斥：--" + " / --".join(chosen) + " 不能同时给出")
    return chosen[0] if chosen else None


def _split_tags(values):
    tags = []
    for value in values:
        for item in str(value).replace(",", " ").split():
            if item and item not in tags:
                tags.append(item)
    return tags


def _normalize_change(path):
    """把仓库路径映射到 `modules` 的键：去掉 `docs/workflows/wf/` 前缀。"""
    prefix = "docs/workflows/wf/"
    return path[len(prefix):] if path.startswith(prefix) else path


def map_changes(files, modules):
    """改动文件 → (suites, repro 组, 未映射文件)。

    规则只有一条：先精确匹配文件键，再取**最长**的目录前缀（键以 `/` 结尾）。
    没有两套并存的通配规则（方案稿 §5.2 的要求）。
    """
    suites, repro, unmapped = set(), set(), []
    directory_keys = sorted((key for key in modules if key.endswith("/")), key=len, reverse=True)
    for path in files:
        key = _normalize_change(path.strip())
        if not key:
            continue
        hit = key if key in modules else next((cand for cand in directory_keys if key.startswith(cand)), None)
        if hit is None:
            unmapped.append(path)
            continue
        entry = modules[hit] or {}
        suites.update(entry.get("suites") or [])
        repro.update(entry.get("repro") or [])
    return sorted(suites), sorted(repro), sorted(unmapped)


def changed_files(base=None, explicit=None):
    """改动文件：显式列表优先，否则 `git diff <base>` + 未跟踪文件。"""
    if explicit:
        return [item for item in explicit.split() if item]
    import subprocess

    repo = _repo_root()
    base = base or "HEAD"
    files = []
    result = subprocess.run(["git", "-C", repo, "diff", "--name-only", base],
                            capture_output=True, text=True, check=False)
    if result.returncode != 0:
        raise PlanError(f"--changed 无法执行 git diff {base}：{result.stderr.strip()[:200]}")
    files.extend(line.strip() for line in result.stdout.splitlines() if line.strip())
    status = subprocess.run(["git", "-C", repo, "status", "--porcelain"],
                            capture_output=True, text=True, check=False)
    for line in status.stdout.splitlines():
        if not line.strip():
            continue
        path = line[3:].strip()
        if " -> " in path:
            path = path.split(" -> ", 1)[1]
        files.append(path.strip('"'))
    return sorted(set(files))


def _validate_modules(suites_doc, by_name):
    problems = []
    for key, entry in (suites_doc.get("modules") or {}).items():
        unknown = [name for name in (entry.get("suites") or []) if name not in by_name]
        if unknown:
            problems.append(f"{key}: 未知套件 {' '.join(unknown)}")
    if problems:
        raise PlanError("suites.json 的 modules 引用了不存在的套件：\n- " + "\n- ".join(problems))


def _repro_candidate_groups(groups_doc, names):
    """保留仍有 candidate_clean 用例的组，返回 (kept, dropped)。"""
    cases = groups_doc.get("cases") or {}
    kept, dropped = [], []
    for name in names:
        members = groups_doc["groups"][name]
        if any((cases.get(case) or {}).get("candidate_clean") for case in members):
            kept.append(name)
        else:
            dropped.append(name)
    return kept, dropped


def plan(argv=None, env=None):
    env = os.environ if env is None else env
    args = parse_args(list(sys.argv[1:] if argv is None else argv))
    if args.help:
        raise PlanError("help", code=0)
    suites_doc = load_suites()
    groups_doc = load_groups()
    entries = suites_doc["suites"]
    by_name = {entry["name"]: entry for entry in entries}

    _validate_modules(suites_doc, by_name)

    # ---- 模式 -------------------------------------------------------------
    mode = _explicit_mode(args)
    selected_env = (env.get("WF_SUITES") or "").split()
    wanted_tags = _split_tags(args.tags) or _split_tags([env.get("WF_TAGS") or ""])
    if mode is None:
        mode = "subset" if (selected_env or wanted_tags) else "full"
    if mode in ("full", "representative"):
        for label, values in (("WF_SUITES", selected_env), ("--tags/WF_TAGS", wanted_tags)):
            if values:
                raise PlanError(
                    f"--{mode} 与 {label} 冲突：清空 {label} 或改用 --subset（当前 {' '.join(values)}）")

    # ---- 套件选择 ---------------------------------------------------------
    if mode == "subset":
        if args.changed:
            raise PlanError("--changed 只给建议，不自动执行：用 `--list --changed` 看建议后再显式选择")
        if not selected_env and not wanted_tags:
            raise PlanError("--subset 没有选择项：用 WF_SUITES='<suite> ...' 或 WF_TAGS='<tag> ...' 指定；可选套件："
                            + " ".join(entry["name"] for entry in entries))
        unknown = [name for name in selected_env if name not in by_name]
        if unknown:
            raise PlanError(f"未知套件：{' '.join(unknown)}；可选：" + " ".join(entry["name"] for entry in entries))
        available_tags = sorted({tag for entry in entries for tag in entry.get("tags") or []})
        unknown_tags = [tag for tag in wanted_tags if tag not in available_tags]
        if unknown_tags:
            raise PlanError(f"未知 tag：{' '.join(unknown_tags)}；可选：" + " ".join(available_tags))
        chosen = list(entries) if not selected_env else [by_name[name] for name in selected_env]
        if wanted_tags:
            chosen = [entry for entry in chosen
                      if set(wanted_tags) & set(entry.get("tags") or [])]
        if not chosen:
            raise PlanError("选择为空：WF_SUITES 与 tags 没有交集（"
                            f"suites={' '.join(selected_env) or '-'} tags={' '.join(wanted_tags) or '-'}）")
    elif mode == "representative":
        chosen = [entry for entry in entries if entry.get("kind") == "suite" and entry.get("representative")]
        if not chosen:
            raise PlanError("代表集为空：suites.json 里没有 representative=true 的套件")
    else:
        chosen = [entry for entry in entries if entry.get("kind") == "suite"]
        if not chosen:
            raise PlanError("suites.json 里没有 kind=suite 的套件")

    # ---- 改动 → 建议（只建议，不执行）------------------------------------
    suggestion = {"changed_files": [], "suggested_suites": [],
                  "suggested_repro_groups": [], "unmapped_changes": []}
    if args.changed or args.changed_files:
        files = changed_files(args.changed_base, args.changed_files)
        suites_hint, repro_hint, unmapped = map_changes(files, suites_doc.get("modules") or {})
        suggestion = {"changed_files": files, "suggested_suites": suites_hint,
                      "suggested_repro_groups": repro_hint, "unmapped_changes": unmapped}
        if not args.list and not args.dry_run:
            raise PlanError(
                "--changed 只给建议，不自动执行：先 `--list --changed` 看建议，再显式用 "
                "WF_SUITES=... / WF_TAGS=... 选择要跑的东西")

    # ---- 夹具部署来源 -----------------------------------------------------
    fixture_deploy = args.fixture_deploy or env.get("WF_FIXTURE_DEPLOY") or "dev"
    if fixture_deploy not in ("dev", "candidate"):
        raise PlanError(f"--fixture-deploy 只接受 dev|candidate：{fixture_deploy!r}")
    release_root = args.release_root or env.get("WF_RELEASE_ROOT")
    release_ref = args.release_ref or env.get("WF_RELEASE_REF")
    release_version = args.release_version or env.get("WF_RELEASE_VERSION")
    release_meta = args.release_meta or env.get("WF_RELEASE_META")
    if fixture_deploy == "candidate":
        missing = [name for name, value in (("--release-root", release_root),
                                            ("--release-ref", release_ref),
                                            ("--release-version", release_version)) if not value]
        if missing:
            raise PlanError("candidate 模式必须同时给出 " + " ".join(missing))
        release_root = os.path.realpath(release_root)
        release_meta = release_meta or release_root + ".meta.json"
        if not os.path.isdir(release_root):
            raise PlanError(f"--release-root 不存在：{release_root}")
    else:
        if release_root or release_ref or release_version or release_meta:
            raise PlanError("dev 模式不接受 --release-root/--release-ref/--release-version/--release-meta")

    # ---- candidate 的套件过滤 --------------------------------------------
    candidate_smoke = False
    if fixture_deploy == "candidate":
        clean = [entry for entry in chosen if entry.get("candidate_clean")]
        if clean:
            chosen = clean
        elif mode == "representative":
            fallback = [entry for entry in entries if entry.get("kind") == "candidate"]
            if not fallback:
                raise PlanError("candidate 模式下没有 candidate_clean 套件，也没有 f1_candidate_smoke 兜底")
            chosen = fallback
            candidate_smoke = True
        else:
            raise PlanError(
                "candidate 模式下没有 candidate_clean=true 的套件可跑（代表集请用 --representative 走兜底闭环）")

    # ---- 流程 / extra -----------------------------------------------------
    if mode == "full":
        flows = list(suites_doc.get("flows") or [])
        extra = [entry["name"] for entry in entries if entry.get("kind") == "extra"]
    elif mode == "representative":
        flow = suites_doc.get("representative_flow") or "p5_spec"
        flows = ["f0"] + ([flow] if flow and flow != "f0" else [])
        extra = []
    else:
        flows = []
        extra = [entry["name"] for entry in chosen if entry.get("kind") == "extra"]
    chosen = [entry for entry in chosen if entry.get("kind") != "extra"]

    # ---- repro gating -----------------------------------------------------
    repro_mode = args.repro_mode or env.get("WF_REPRO_MODE") or None
    if repro_mode is not None and repro_mode not in REPRO_MODES:
        raise PlanError(f"--repro 只接受 {'|'.join(REPRO_MODES)}：{repro_mode!r}")
    with_repro = env.get("WF_WITH_REPRO") == "1"
    repro_args_given = bool(args.repro_groups) or (repro_mode not in (None, "none"))
    if mode == "subset":
        if repro_args_given and not with_repro:
            raise PlanError("子集模式要跑 repro 必须显式开 WF_WITH_REPRO=1（或改用 --full/--representative）")
        repro_enabled = with_repro and repro_mode != "none"
    else:
        repro_enabled = repro_mode != "none"
    if not repro_enabled:
        if args.repro_groups:
            raise PlanError("--repro none 不接受 --repro-group")
        repro_mode = "none"
        repro_groups = []
    else:
        repro_mode = repro_mode or "green"
        if fixture_deploy == "candidate" and repro_mode in ("red", "both"):
            raise PlanError("candidate 模式只允许 --repro green|auto（red 注入针对源码，请在 dev 模式跑）")
        explicit_groups = list(args.repro_groups) or (env.get("WF_REPRO_GROUP") or "").split()
        unknown = [name for name in explicit_groups if name not in groups_doc["groups"]]
        if unknown:
            raise PlanError(f"未知 repro 组：{' '.join(unknown)}；可选：" + " ".join(sorted(groups_doc["groups"])))
        if explicit_groups:
            repro_groups = explicit_groups
            if fixture_deploy == "candidate":
                kept, dropped = _repro_candidate_groups(groups_doc, repro_groups)
                if dropped:
                    raise PlanError("candidate 模式下这些组没有 candidate_clean 用例：" + " ".join(dropped))
                repro_groups = kept
        elif mode == "representative":
            default_key = "candidate_representative" if fixture_deploy == "candidate" else "representative"
            defaults = list(groups_doc.get(default_key) or [])
            if fixture_deploy == "candidate":
                kept, dropped = _repro_candidate_groups(groups_doc, defaults)
                repro_groups = kept
                if dropped:
                    print(f"（candidate 模式：无 candidate_clean 用例的组已排除：{' '.join(dropped)}）",
                          file=sys.stderr)
                if not kept:
                    candidate_smoke = True
                    print("（candidate 模式：没有 candidate_clean repro 组，退回 f1_candidate_smoke 闭环）",
                          file=sys.stderr)
            else:
                repro_groups = defaults
        else:
            repro_groups = []      # full/subset 默认跑全部用例（不给组过滤）

    # ---- 并行 -------------------------------------------------------------
    # 默认并行（省墙钟）；`--serial` 或 `WF_JOBS=1` 退回串行（确定性/排障）。
    if args.serial:
        jobs = 1
    else:
        jobs = int(env.get("WF_JOBS") or DEFAULT_JOBS)
    repro_jobs = int(env.get("WF_REPRO_JOBS") or DEFAULT_REPRO_JOBS)
    if jobs < 1 or repro_jobs < 1:
        raise PlanError("WF_JOBS / WF_REPRO_JOBS 必须是正整数")

    # ---- 测试发行（仅 dev）-----------------------------------------------
    if fixture_deploy == "dev":
        version = resolve_test_release_version(env=env)
        cache = env.get("WF_TEST_RELEASE_CACHE") or os.path.join(os.path.expanduser("~"), ".cache",
                                                                 "wf-test-release")
        test_release_root = os.path.join(cache, version)
        test_release_ref = f"refs/tags/wf-v{version}"
    else:
        version, test_release_root, test_release_ref = None, None, None

    parallel_names = [entry["name"] for entry in chosen if entry["name"] not in PARALLEL_SERIAL]
    serial_names = [entry["name"] for entry in chosen if entry["name"] in PARALLEL_SERIAL]

    flow_expect = {name: (suites_doc.get("flow_expect") or {}).get(name) for name in flows}
    extra_expect = {name: (suites_doc.get("extra_expect") or {}).get(name) for name in extra}
    results_dir = env.get("WF_RESULTS_DIR") or os.path.join(
        os.path.expanduser("~"), ".cache", "wf-test-run", f"run-{os.getpid()}")
    list_only = bool(args.list or args.dry_run)
    return {
        "mode": mode,
        "full_mode": 1 if mode == "full" else 0,
        "parallel": 1 if jobs > 1 else 0,
        "jobs": jobs,
        "fix": env.get("WF_FIX") or DEFAULT_FIX,
        "suites_all": [entry["name"] for entry in chosen],
        "suites_parallel": parallel_names,
        "suites_serial": serial_names,
        "flows": flows,
        "extra": extra,
        "flow_expect": flow_expect,
        "extra_expect": extra_expect,
        "repro_enabled": 1 if repro_enabled else 0,
        "repro_mode": repro_mode if repro_enabled else "none",
        "repro_groups": repro_groups if repro_enabled else [],
        "repro_jobs": repro_jobs,
        "fixture_deploy": fixture_deploy,
        "release_root": release_root or "",
        "release_ref": release_ref or "",
        "release_version": release_version or "",
        "release_meta": release_meta or "",
        "test_release_root": test_release_root or "",
        "test_release_version": version or "",
        "test_release_ref": test_release_ref or "",
        "results_dir": results_dir,
        "no_build": 1 if args.no_build else 0,
        "list_only": 1 if list_only else 0,
        "candidate_smoke": 1 if candidate_smoke else 0,
        "tags": wanted_tags,
        **suggestion,
    }


def describe(result):
    lines = [f"mode: {result['mode']}（full_mode={result['full_mode']}）"]
    if result.get("tags"):
        lines.append(f"tags: {' '.join(result['tags'])}")
    lines.append(f"suites({len(result['suites_all'])}): {' '.join(result['suites_all']) or '-'}")
    lines.append(f"flows: {' '.join(result['flows']) or '-'}")
    lines.append(f"extra: {' '.join(result['extra']) or '-'}")
    if result["repro_enabled"]:
        lines.append(f"repro: {result['repro_mode']} groups={' '.join(result['repro_groups']) or '(all)'} "
                     f"jobs={result['repro_jobs']}")
    else:
        lines.append("repro: none")
    lines.append(f"fixture_deploy: {result['fixture_deploy']}")
    if result["fixture_deploy"] == "candidate":
        lines.append(f"release: {result['release_root']} {result['release_ref']} {result['release_version']}")
    else:
        lines.append(f"test-release: {result['test_release_root']} ({result['test_release_version']})")
    lines.append(f"jobs: {result['jobs']}  results_dir: {result['results_dir']}")
    if result["candidate_smoke"]:
        lines.append("candidate_smoke: f1_candidate_smoke 兜底")
    if result.get("changed_files") or result.get("suggested_suites") or result.get("unmapped_changes"):
        lines.append(f"changed({len(result.get('changed_files') or [])}): "
                     f"{' '.join(result.get('changed_files') or []) or '-'}")
        lines.append("建议套件: " + (" ".join(result.get("suggested_suites") or []) or "（无映射）"))
        lines.append("建议 repro 组: " + (" ".join(result.get("suggested_repro_groups") or []) or "（无映射）"))
        if result.get("unmapped_changes"):
            lines.append("未映射改动（需人工判断）: " + " ".join(result["unmapped_changes"]))
    units = len(result["suites_all"]) + len(result["flows"]) + len(result["extra"])
    suffix = " + repro" if result["repro_enabled"] else ""
    lines.append(f"计划执行单元: {units}{suffix}")
    return "\n".join(lines)


def emit(result, fmt):
    if fmt == "json":
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
        return
    for key, value in result.items():
        name = "PLAN_" + key.upper()
        if isinstance(value, dict):
            value = " ".join(f"{key}:{'' if item is None else item}" for key, item in value.items())
        elif isinstance(value, list):
            value = " ".join(value)
        elif isinstance(value, int):
            value = str(value)
        print(f"{name}={shlex.quote(str(value))}")
    print("PLAN_OK=1")


USAGE = """run_all.sh 执行计划（plan.py）

  --full | --subset | --representative   互斥模式（无显式模式时：WF_SUITES 非空→subset，否则 full）
  --repro green|red|both|none|auto       repro 模式（不是组名）
  --repro-group NAME                      repro 组（可重复；组定义见 repro/groups.json）
  --fixture-deploy dev|candidate         candidate 需同时给 --release-root/--release-ref/--release-version
  --list | --dry-run                     只输出计划，不执行
  --no-build                             不重建测试发行（必须已有新鲜 meta）
  --parallel | --serial                  套件层并行（默认 4）/ 串行（确定性、排障）
                                         WF_JOBS 覆盖并发数；WF_REPRO_JOBS 覆盖 repro 并发数
  --format sh|json
"""


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if "-h" in argv or "--help" in argv:
        print(USAGE)
        return 0
    try:
        result = plan(argv)
    except PlanError as exc:
        if exc.code == 0:
            print(USAGE)
            return 0
        print(f"PLAN-ERROR: {exc}", file=sys.stderr)
        return exc.code
    fmt = parse_args(argv).format
    if result["list_only"]:
        # sh 模式下把人类可读摘要送 stderr：stdout 必须保持“可 eval 的赋值”，
        # 否则 run_all.sh 的 `eval "$plan_out"` 会把摘要当成命令执行。
        print(describe(result), file=sys.stderr if fmt == "sh" else sys.stdout)
        emit(result, fmt)
        os.makedirs(result["results_dir"], exist_ok=True)
        with open(os.path.join(result["results_dir"], "plan.json"), "w", encoding="utf-8") as handle:
            json.dump(result, handle, ensure_ascii=False, indent=2, sort_keys=True)
            handle.write("\n")
        return 0
    emit(result, fmt)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
