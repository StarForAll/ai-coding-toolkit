#!/usr/bin/env python3
"""plan.py — `run_all.sh` 的**单一执行计划**（唯一权威）。

`--list` / `--dry-run` / 真实执行都消费同一份 `plan()` 的结果：没有第二处选择逻辑。

用法（run_all.sh 会把整串参数原样转进来）：
    python3 plan.py --format sh --full --repro green
    python3 plan.py --format json --dry-run
    python3 plan.py --list

退出码：0 = 计划成立；2 = 选项冲突/未知套件/未知组/注册表非法（stderr 说明）。
"""
from __future__ import annotations

import argparse
import json
import os
import shlex
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
UNITS_JSON = os.path.join(HERE, "units.json")
LEGACY_SUITES_JSON = os.path.join(HERE, "suites.json")
GROUPS_JSON = os.path.join(HERE, "repro", "groups.json")


def _repo_root():
    return os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))


# 作者侧路径/scope 唯一所有者（假树必须复制它，不提供“缺 helper 就跳过校验”的兼容）。
sys.path.insert(0, os.path.join(_repo_root(), "scripts"))
import wf_test_paths  # noqa: E402

DEFAULT_FIX = os.path.join(  # 无 scope 时的历史默认（scope 下由 wf_test_paths 派生）
    "/tmp", "wf-fixtures", f"run-{os.getpid()}")
DEFAULT_JOBS = min(8, os.cpu_count() or 4)   # 执行单元默认并行数（不超过物理核，防少核机器超订）
DEFAULT_REPRO_JOBS = min(8, os.cpu_count() or 4)  # repro 用例层默认并行数（同上）
DEV_VERSION_PLACEHOLDER = "0.0.0-dev"
TEST_RELEASE_FALLBACK = "0.1.0"
REPRO_MODES = ("green", "red", "both", "none", "auto")
UNIT_KINDS = ("suite", "flow", "extra", "candidate", "manual")
PLANNABLE_KINDS = ("suite", "flow", "extra", "candidate")
FIXTURE_KINDS = ("template", "install")
# 条目字段白名单：未知字段一律拒绝（防下一个死字段悄无声息地长回来）。
UNIT_FIELDS = {
    "name", "script", "kind", "expect", "fixture", "tags", "representative",
    "candidate_clean", "isolated_user", "parallel", "notes",
}
TOP_FIELDS = {"schema_version", "units", "modules", "representative_flow"}
SCHEMA_VERSION = 2

# 假树清单（三桶，单一来源）：r67_tests 的假运行器树按它复制/桩化。
# - COPY：纯工具 + plan.py 无条件依赖的数据，原样复制；
# - STUB：复制真实文件会改变假环境语义（假树没有真夹具/真 worker 契约），由 r67 写桩；
# - SPECIAL：run_all.sh 自身（复制，不做归类推导）。
# G8（test_runner_hygiene）扫描 run_all.sh 的静态 `"$HERE/<相对路径>"` 引用：
# 每个命中必须属于 COPY ∪ STUB ∪ SPECIAL ∪ 注册表每个可计划单元的 script。
# 注意 `repro/groups.json` 由 plan.py 的常量引用（不出现在 run_all.sh 的静态引用里），
# G8 扫不到——它的正确性由 r67 冒烟保证。
FAKE_TREE_COPY = (
    "plan.py",
    "units.json",
    "repro/groups.json",
    "repro/repro_select.py",
    "results_gate.py",
    "execution.py",
    "fixture_scope.py",
    "prepare_candidate_repo.py",
    "source_hygiene.py",
    "template_check.py",
    "template_cache.py",
    "runner_protocol.py",
    "release_context.py",
    "execute_gate.py",
    "results_summary.py",
    "library_source.py",
    "runner_cleanup.py",
)
FAKE_TREE_STUB = (
    "run_one.sh",
    "wf_fixture.sh",
    "f1_init.py",
    "repro/run.sh",
)
FAKE_TREE_SPECIAL = ("run_all.sh",)


class PlanError(Exception):
    """可预期的计划冲突（非零退出、不打印 traceback）。"""

    def __init__(self, message, code=2):
        super().__init__(message)
        self.code = code


def _is_positive_int(value):
    return isinstance(value, int) and not isinstance(value, bool) and value > 0


def _validate_entry(entry, seen):
    if not isinstance(entry, dict):
        raise PlanError(f"units.json 的条目必须是对象：{entry!r}")
    unknown = sorted(set(entry) - UNIT_FIELDS)
    name = entry.get("name")
    if not isinstance(name, str) or not name.strip():
        raise PlanError(f"units.json 条目缺 name：{entry!r}")
    if unknown:
        raise PlanError(f"{name}: 未知字段 {' '.join(unknown)}（字段白名单见 plan.py::UNIT_FIELDS）")
    if name in seen:
        raise PlanError(f"{name}: 条目重复")
    seen.add(name)
    kind = entry.get("kind")
    if kind not in UNIT_KINDS:
        raise PlanError(f"{name}: kind 非法 {kind!r}（可选 {' '.join(UNIT_KINDS)}）")
    script = entry.get("script", f"{name}.py")
    if not isinstance(script, str) or not script or os.path.isabs(script) or ".." in script.split("/"):
        raise PlanError(f"{name}: script 必须是 HERE 下的相对路径：{script!r}")
    if kind in PLANNABLE_KINDS:
        expect = entry.get("expect")
        if not _is_positive_int(expect):
            raise PlanError(f"{name}: expect 必须是正整数（当前 {expect!r}）")
        fixture = entry.get("fixture", "template")
        if fixture not in FIXTURE_KINDS:
            raise PlanError(f"{name}: fixture 非法 {fixture!r}（可选 {' '.join(FIXTURE_KINDS)}）")
        if not os.path.isfile(os.path.join(HERE, script)):
            raise PlanError(f"{name}: script 指向的文件不存在：HERE/{script}")
    elif entry.get("expect") is not None or entry.get("fixture") is not None:
        raise PlanError(f"{name}: manual 单元不接受 expect/fixture（不在任何执行面内）")
    if kind == "manual" and not (entry.get("notes") or "").strip():
        raise PlanError(f"{name}: manual 单元必须在 notes 说明为何手动")
    # 串行是例外不是默认：parallel:false 必须携带 notes 理由，防无理由串行悄悄回潮。
    if entry.get("parallel") is False and not (entry.get("notes") or "").strip():
        raise PlanError(f"{name}: parallel:false 必须在 notes 登记不可并行理由")
    if "tags" in entry and not isinstance(entry["tags"], list):
        raise PlanError(f"{name}: tags 必须是数组")


def load_units(path=UNITS_JSON):
    if not os.path.exists(path) and os.path.exists(LEGACY_SUITES_JSON):
        raise PlanError(
            "检测到旧注册表 suites.json：请迁移为 units.json（顶层 units 数组 + 每条 expect/fixture/script），"
            "旧 schema 不再兼容（不静默并存两套真相）")
    with open(path, encoding="utf-8") as handle:
        doc = json.load(handle)
    if not isinstance(doc, dict) or not isinstance(doc.get("units"), list):
        raise PlanError("units.json 必须使用顶层 units 数组（旧 suites.json schema 不再兼容）")
    unknown = sorted(set(doc) - TOP_FIELDS)
    if unknown:
        raise PlanError(f"units.json 未知顶层字段：{' '.join(unknown)}")
    if doc.get("schema_version") != SCHEMA_VERSION:
        raise PlanError(f"units.json schema_version 必须是 {SCHEMA_VERSION}（当前 {doc.get('schema_version')!r}）")
    seen = set()
    for entry in doc["units"]:
        _validate_entry(entry, seen)
    return doc


def load_groups(path=GROUPS_JSON):
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


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
    parser.add_argument("--serial", action="store_true", help="执行单元层串行（确定性/排障）")
    parser.add_argument("--list", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--no-build", action="store_true")
    parser.add_argument("--no-template", action="store_true",
                        help="关闭整套模板机制（含跨 run 缓存）：逐单元重建夹具")
    parser.add_argument("--no-template-cache", action="store_true",
                        help="只关跨 run 模板缓存（run 内模板照旧构建复用）")
    parser.add_argument("--repro", dest="repro_mode", default=None)
    parser.add_argument("--repro-group", dest="repro_groups", action="append", default=[])
    parser.add_argument("--repro-concurrent", action="store_true",
                        help="主池与 repro 并发（显式实验通道，不进默认路径）")
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
    parser.add_argument("--plan-file", default=None,
                        help="不再计算计划：读取已冻结的 final plan 字节并输出 sh 赋值")
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


def _validate_modules(units_doc, by_name):
    """modules 映射的完整性校验（四个方向，防 --changed 建议静默缺失）。

    ① 模块 → 套件：引用的套件必须存在（原有校验）；
    ② 套件 → 模块：每个可计划套件（kind ∈ suite/extra/candidate）必须被 ≥1 模块覆盖
       ——新增套件漏映射在计划期即被拒，不再静默漏建议；
    ③ 键 → 仓库：每个 modules 键必须真实存在——解析基准与 `_normalize_change` 同构
       （键按 docs/workflows/wf/ 前缀剥除后的相对路径解析，不按仓库根裸解析），
       防"永不命中的假键"让 ② 变纸面门；
    ④ 命中 → 非空：map_changes 命中键时该条目的 suites 不得为空（空条目 = 建议静默缺失）。

    flow 单元（f0/p5_*）不参与 `--changed` 建议：它们不是源码映射的套件，只由
    full/representative 选择（或显式 WF_SUITES），因此不要求在 modules 里覆盖。
    """
    problems = []
    modules = units_doc.get("modules") or {}
    for key, entry in modules.items():
        unknown = [name for name in (entry.get("suites") or []) if name not in by_name]
        if unknown:
            problems.append(f"{key}: 未知套件 {' '.join(unknown)}")
        if not (entry.get("suites") or []):
            problems.append(f"{key}: suites 为空（命中该键时建议会静默缺失）")
        base = os.path.join(_repo_root(), "docs", "workflows", "wf", key)
        if not os.path.exists(base):
            problems.append(f"{key}: 仓库中不存在（解析基准 docs/workflows/wf/<key>）")
    covered = set()
    for entry in modules.values():
        covered.update(entry.get("suites") or [])
    plannable = {name for name, entry in by_name.items()
                 if entry.get("kind") in ("suite", "extra", "candidate")}
    uncovered = sorted(plannable - covered)
    if uncovered:
        problems.append("未被任何模块覆盖的可计划套件（--changed 会漏建议）：" + " ".join(uncovered))
    if problems:
        raise PlanError("units.json 的 modules 校验失败：\n- " + "\n- ".join(problems))


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


def unit_record(entry):
    """执行记录编码：`name:kind:expect:fixture:script`（五段固定顺序，冒号分隔、无空格）。"""
    return ":".join((entry["name"], entry["kind"], str(entry["expect"]),
                     entry.get("fixture", "template"), entry.get("script", entry["name"] + ".py")))


def plan(argv=None, env=None):
    env = os.environ if env is None else env
    args = parse_args(list(sys.argv[1:] if argv is None else argv))
    if args.help:
        raise PlanError("help", code=0)
    units_doc = load_units()
    groups_doc = load_groups()
    entries = units_doc["units"]
    by_name = {entry["name"]: entry for entry in entries}

    _validate_modules(units_doc, by_name)

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

    # ---- 单元选择 ---------------------------------------------------------
    if mode == "subset":
        if args.changed:
            raise PlanError("--changed 只给建议，不自动执行：用 `--list --changed` 看建议后再显式选择")
        if not selected_env and not wanted_tags:
            raise PlanError("--subset 没有选择项：用 WF_SUITES='<suite> ...' 或 WF_TAGS='<tag> ...' 指定；可选套件："
                            + " ".join(entry["name"] for entry in entries if entry["kind"] != "manual"))
        unknown = [name for name in selected_env if name not in by_name]
        if unknown:
            raise PlanError(f"未知套件：{' '.join(unknown)}；可选："
                            + " ".join(entry["name"] for entry in entries if entry["kind"] != "manual"))
        manual = [name for name in selected_env if by_name[name]["kind"] == "manual"]
        if manual:
            raise PlanError(f"manual 单元不参与计划（需真实宿主条件，见 notes）：{' '.join(manual)}")
        available_tags = sorted({tag for entry in entries for tag in entry.get("tags") or []})
        unknown_tags = [tag for tag in wanted_tags if tag not in available_tags]
        if unknown_tags:
            raise PlanError(f"未知 tag：{' '.join(unknown_tags)}；可选：" + " ".join(available_tags))
        chosen = list(entries) if not selected_env else [by_name[name] for name in selected_env]
        chosen = [entry for entry in chosen if entry["kind"] != "manual"]
        if wanted_tags:
            chosen = [entry for entry in chosen
                      if set(wanted_tags) & set(entry.get("tags") or [])]
        if not chosen:
            raise PlanError("选择为空：WF_SUITES 与 tags 没有交集（"
                            f"suites={' '.join(selected_env) or '-'} tags={' '.join(wanted_tags) or '-'}）")
    elif mode == "representative":
        chosen = [entry for entry in entries if entry["kind"] == "suite" and entry.get("representative")]
        if not chosen:
            raise PlanError("代表集为空：units.json 里没有 representative=true 的套件")
    else:
        chosen = [entry for entry in entries if entry["kind"] == "suite"]
        if not chosen:
            raise PlanError("units.json 里没有 kind=suite 的套件")

    # ---- 改动 → 建议（只建议，不执行）------------------------------------
    suggestion = {"changed_files": [], "suggested_suites": [],
                  "suggested_repro_groups": [], "unmapped_changes": []}
    if args.changed or args.changed_files:
        files = changed_files(args.changed_base, args.changed_files)
        suites_hint, repro_hint, unmapped = map_changes(files, units_doc.get("modules") or {})
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
            fallback = [entry for entry in entries if entry["kind"] == "candidate"]
            if not fallback:
                raise PlanError("candidate 模式下没有 candidate_clean 套件，也没有 f1_candidate_smoke 兜底")
            chosen = fallback
            candidate_smoke = True
        else:
            raise PlanError(
                "candidate 模式下没有 candidate_clean=true 的套件可跑（代表集请用 --representative 走兜底闭环）")

    # ---- 流程 / extra（四类可计划单元同池）--------------------------------
    if mode == "subset":
        unit_entries = list(chosen)
    elif mode == "representative":
        flow_names = ["f0", units_doc.get("representative_flow") or "p5_spec"]
        unit_entries = list(chosen) + [by_name[name] for name in flow_names if name in by_name]
    else:
        flows = [entry for entry in entries if entry["kind"] == "flow"]
        extra = [entry for entry in entries if entry["kind"] == "extra"]
        unit_entries = list(chosen) + flows + extra
    # 去重（同名单元只执行一次）并保持顺序
    deduped, seen_names = [], set()
    for entry in unit_entries:
        if entry["name"] in seen_names:
            continue
        seen_names.add(entry["name"])
        deduped.append(entry)
    unit_entries = deduped

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

    # ---- 并发预算（单一来源：本函数）-------------------------------------
    # 默认 repro 与主池串行（决策 #3）：总并发全部给主池。`--repro-concurrent`
    # 打开时才按 实测工作比 主池 298s : repro 190s ≈ 5/3 分摊。
    if args.serial:
        jobs = 1
        repro_jobs = 1
    else:
        total_jobs = int(env.get("WF_TOTAL_JOBS") or env.get("WF_JOBS") or DEFAULT_JOBS)
        if total_jobs < 1:
            raise PlanError("WF_TOTAL_JOBS / WF_JOBS 必须是正整数")
        if args.repro_concurrent or env.get("WF_REPRO_CONCURRENT") == "1":
            jobs = max(1, round(total_jobs * 5 / 8))
            repro_jobs = max(1, total_jobs - jobs)
        else:
            jobs = total_jobs
            repro_jobs = int(env.get("WF_REPRO_JOBS") or DEFAULT_REPRO_JOBS)
        if repro_jobs < 1:
            raise PlanError("WF_REPRO_JOBS 必须是正整数")
    repro_concurrent = bool(args.repro_concurrent or env.get("WF_REPRO_CONCURRENT") == "1")
    if mode == "subset" and not repro_enabled:
        repro_concurrent = False

    # ---- 开关（模板机制）--------------------------------------------------
    no_template = bool(args.no_template or env.get("WF_NO_TEMPLATE") == "1")
    no_template_cache = bool(args.no_template_cache or env.get("WF_NO_TEMPLATE_CACHE") == "1")
    if no_template:
        no_template_cache = True   # WF_NO_TEMPLATE = 关闭整套模板机制（含缓存）

    # ---- 测试发行（仅 dev）-----------------------------------------------
    try:
        # 管理路径的唯一规则：scope 下的默认值从 scope 派生；显式域外路径在计划期拒绝。
        layout = wf_test_paths.resolve_layout("run", os.getpid(), env=env)
    except wf_test_paths.PathError as exc:
        raise PlanError(f"scope 路径校验失败（首次写前拒绝）：{exc}")
    if fixture_deploy == "dev":
        version = resolve_test_release_version(env=env)
        cache = env.get("WF_TEST_RELEASE_CACHE") or str(layout["test_release"])
        test_release_root = os.path.join(cache, version)
        test_release_ref = f"refs/tags/wf-v{version}"
    else:
        version, test_release_root, test_release_ref = None, None, None

    records = [unit_record(entry) for entry in unit_entries]
    parallel_records = [unit_record(entry) for entry in unit_entries
                        if (entry["kind"] in PLANNABLE_KINDS and entry.get("parallel") is not False)]
    serial_records = [unit_record(entry) for entry in unit_entries
                      if (entry["kind"] in PLANNABLE_KINDS and entry.get("parallel") is False)]
    # isolated-user 的唯一来源：units.json 的 isolated_user 字段（run_all/run_one 消费
    # PLAN_ISOLATED_UNITS 做成员判定——套件特判不进 bash 分支）。
    isolated_units = [entry["name"] for entry in unit_entries if entry.get("isolated_user")]

    results_dir = env.get("WF_RESULTS_DIR") or str(layout["results_dir"])
    fix = env.get("WF_FIX") or str(layout["fixture"])
    list_only = bool(args.list or args.dry_run)
    return {
        "mode": mode,
        "full_mode": 1 if mode == "full" else 0,
        "parallel": 1 if jobs > 1 else 0,
        "jobs": jobs,
        "fix": fix,
        "units": [{"name": entry["name"], "kind": entry["kind"],
                   "expect": entry.get("expect"), "fixture": entry.get("fixture", "template"),
                   "script": entry.get("script", entry["name"] + ".py")}
                  for entry in unit_entries],
        "units_parallel": parallel_records,
        "units_serial": serial_records,
        "isolated_units": isolated_units,
        "no_template": 1 if no_template else 0,
        "no_template_cache": 1 if no_template_cache else 0,
        "repro_enabled": 1 if repro_enabled else 0,
        "repro_mode": repro_mode if repro_enabled else "none",
        "repro_groups": repro_groups if repro_enabled else [],
        "repro_jobs": repro_jobs,
        "repro_concurrent": 1 if (repro_concurrent and repro_enabled) else 0,
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
    units = result["units"]
    kinds = {}
    for unit in units:
        kinds[unit["kind"]] = kinds.get(unit["kind"], 0) + 1
    summary = " ".join(f"{kind}={count}" for kind, count in sorted(kinds.items())) or "-"
    lines.append(f"units({len(units)}): {summary}")
    lines.append("单元: " + (" ".join(unit["name"] for unit in units) or "-"))
    if result["repro_enabled"]:
        parallel_note = "并发" if result["repro_concurrent"] else "串行"
        lines.append(f"repro: {result['repro_mode']} groups={' '.join(result['repro_groups']) or '(all)'} "
                     f"jobs={result['repro_jobs']}（主池{parallel_note}）")
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
    suffix = " + repro" if result["repro_enabled"] else ""
    lines.append(f"计划执行单元: {len(units)}{suffix}")
    return "\n".join(lines)


def note_plan_call(result, argv):
    """计划调用计数（design §5.2 的合同计数）：只在本进程真的计算了计划时记一行。

    唯一写入位置是 `WF_PLAN_LOG`（claim 之后由 lease 阶段指向结果目录）；没有该定位就不写，
    绝不为了计数创建 bootstrap 文件或让 list/dry-run 产生副作用。
    """
    if "--plan-file" in argv:
        return
    path = os.environ.get("WF_PLAN_LOG")
    if not path:
        return
    directory = os.path.dirname(path) or "."
    if not os.path.isdir(directory):
        return
    try:
        with open(path, "a", encoding="utf-8") as handle:
            handle.write("%s %d\n" % (result["mode"], result["list_only"]))
    except OSError:
        return


def emit(result, fmt):
    if fmt == "json":
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
        return
    for key, value in result.items():
        if key == "units":
            print(f"PLAN_UNITS={shlex.quote(' '.join(unit_record(entry) for entry in value))}")
            continue
        name = "PLAN_" + key.upper()
        if isinstance(value, dict):
            value = " ".join(f"{key}:{'' if item is None else item}" for key, item in value.items())
        elif isinstance(value, list) and value and isinstance(value[0], dict):
            value = " ".join(unit_record(entry) for entry in value)
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
  --repro-concurrent                     主池与 repro 并发（显式实验通道，默认串行）
  --fixture-deploy dev|candidate         candidate 需同时给 --release-root/--release-ref/--release-version
  --list | --dry-run                     只输出计划，不执行
  --no-build                             不重建测试发行（必须已有新鲜 meta）
  --no-template                          关闭整套模板机制（含跨 run 缓存）
  --no-template-cache                    只关跨 run 模板缓存
  --parallel | --serial                  执行单元层并行 / 串行（确定性、排障）
                                         WF_TOTAL_JOBS 覆盖总并发；WF_REPRO_JOBS 覆盖 repro 并发数
  --format sh|json
"""


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if "-h" in argv or "--help" in argv:
        print(USAGE)
        return 0
    try:
        if "--plan-file" in argv:
            path = argv[argv.index("--plan-file") + 1]
            with open(path, encoding="utf-8") as handle:
                frozen = json.load(handle)
            emit(frozen, "sh")
            return 0
        result = plan(argv)
    except (PlanError, OSError, ValueError) as exc:
        if not isinstance(exc, PlanError):
            print(f"PLAN-ERROR: frozen plan is unreadable: {exc}", file=sys.stderr)
            return 2
        if exc.code == 0:
            print(USAGE)
            return 0
        print(f"PLAN-ERROR: {exc}", file=sys.stderr)
        return exc.code
    note_plan_call(result, argv)
    fmt = parse_args(argv).format
    if result["list_only"]:
        # 人类可读摘要一律送 stderr：stdout 必须保持“可 eval 的赋值”（sh）或**单一 JSON**（json），
        # 否则 run_all.sh 的 eval 与消费者解析都会被摘要污染。
        print(describe(result), file=sys.stderr)
        emit(result, fmt)
        # plan.json 只在“显式给出结果目录”时镜像写入：run_all 全路径（含 --dry-run/
        # 契约测试）都先 export WF_RESULTS_DIR 并 claim 目录，行为不变；直接 `--list`
        # 未显式给目录则不建不写——旧逻辑每泄漏一个无主 run-<pid> 空目录（D5.1）。
        if os.environ.get("WF_RESULTS_DIR"):
            os.makedirs(result["results_dir"], exist_ok=True)
            with open(os.path.join(result["results_dir"], "plan.json"), "w", encoding="utf-8") as handle:
                json.dump(result, handle, ensure_ascii=False, indent=2, sort_keys=True)
                handle.write("\n")
        return 0
    emit(result, fmt)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
