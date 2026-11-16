#!/usr/bin/env python3
"""repro_select.py — 用例选择、`--mode auto` 双身份、唯一冻结 bundle 与唯一 state writer。

三种身份分开（design §5.1 / AC7、AC8）：

- `execution_context`：本次完整 tool/SUT、平台、部署、真实 release 身份（root 身份 + candidate tag
  commit）。每次 green 结果与 green proof 都记录它。
- `red_subject`：断言/注入脚本、helper、执行协议、source/targets/build 输入、tool/SUT、平台与
  release 内容主体（**不含** deploy 标签与 release 根路径）。只有 dev red 成功才产生。
- `input_fingerprint`：case 输入 + 上面完整 context（case execution 身份）。

auto 规则：dev auto 找同 red subject 的有效 dev red，无则 both；candidate auto 只对 candidate-clean
用例要求同 red subject 且 release 内容/version/ref/runtime 全等，缺失即拒绝（出口是在 dev 用同一
内容验证 red/both）。candidate green 从不续签 red。

bundle schema 2 是唯一冻结来源（`inputs.json`），env 只传它的路径；TSV 只是派生兼容面。
公共输入（source/helpers/executor/runner）在 freeze 计算一次并冻结进 bundle；worker 只重算
case 局部输入，gate 不重算任何公共摘要，唯一 writer 在最终 barrier 各重算一次公共输入与
execution context 并与冻结值比对。旧 schema bundle 一律拒绝（每 run 产物，不迁移）。
gate 只读调用 `validate_repro()`；唯一全局 writer 是 `commit-state` 子进程。
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
FULL = os.path.dirname(HERE)
REPO = os.path.abspath(os.path.join(HERE, "..", "..", "..", "..", ".."))
GROUPS_JSON = os.path.join(HERE, "groups.json")
HELPERS = ("_harness.py", "_release.py", "_review_flow.py", "_review_launch.py",
           "_snapshot.py", "_executor_set.py", "_worker.py")
RUNNER_FILES = ("repro_select.py", "run.sh")
STATE_SCHEMA = 3
BUNDLE_SCHEMA = 2
CONTEXT_SCHEMA = 1
PHASES = {"green": ("green",), "red": ("red",), "both": ("green", "red")}


class SelectError(Exception):
    """可预期的拒绝（非零退出）。"""


def now():
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def load_groups(path=GROUPS_JSON):
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def all_cases():
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


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def digest(value):
    return "sha256:" + hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()


def file_digest(path):
    try:
        with open(path, "rb") as handle:
            return "sha256:" + hashlib.sha256(handle.read()).hexdigest()
    except OSError:
        return None


# 公共扫描计数（design §4.2）：只给测试读，不进 bundle/状态。
SCAN_COUNTS = {"source": 0, "release": 0, "helpers": 0}


def reset_scans():
    for key in SCAN_COUNTS:
        SCAN_COUNTS[key] = 0


def scans():
    return dict(SCAN_COUNTS)


def helpers_digest():
    SCAN_COUNTS["helpers"] += 1
    return digest({name: file_digest(os.path.join(HERE, name)) for name in HELPERS})


def script_digest(case):
    return file_digest(os.path.join(HERE, case + ".py"))


def source_digest():
    SCAN_COUNTS["source"] += 1
    sys.path.insert(0, os.path.join(REPO, "scripts"))
    import wf_release_common
    return wf_release_common.source_tree_digest()


def targets_digest(case, meta):
    targets = (meta or {}).get("targets") or []
    if not targets:
        return None
    values = {}
    for relative in targets:
        base = (os.path.join(REPO, "docs", "workflows", "wf")
                if relative.startswith(("payload/", "skills/")) else REPO)
        value = file_digest(os.path.join(base, *relative.split("/")))
        if value is None:
            return None
        values[relative] = value
    return digest(values)


def _runtime_identity():
    sys.path.insert(0, os.path.join(REPO, "scripts"))
    try:
        import python_runtime_identity as identity
    except ImportError:  # 假环境
        return {}
    runner = os.path.join(HERE, "_worker.py")
    sut = os.path.join(FULL, "f1_init.py")
    try:
        return {"tool": identity.resolve("tool", runner)["path_identity"],
                "sut": identity.resolve("sut", sut)["path_identity"],
                "implementation": sys.implementation.name,
                "version": "%d.%d.%d" % sys.version_info[:3]}
    except identity.IdentityError:
        return {}


def release_context():
    """已核发行身份：优先用父 runner 的 handoff，独立 repro 从 env 自算。"""
    SCAN_COUNTS["release"] += 1
    path = os.environ.get("WF_RELEASE_CONTEXT")
    if path:
        try:
            with open(path, encoding="utf-8") as handle:
                context = json.load(handle)
        except (OSError, ValueError) as exc:
            raise SelectError(f"release context unreadable: {path}") from exc
        if context.get("schema_version") != CONTEXT_SCHEMA or not context.get("release_subject"):
            raise SelectError("release context schema/subject invalid")
        return context
    root = os.environ.get("WF_RELEASE_TREE")
    version = os.environ.get("WF_RELEASE_VERSION") or ""
    ref = os.environ.get("WF_RELEASE_REF") or ""
    if not root:
        # --list 等纯计划面：无 context 时用产品发行树只读派生一个可比较的 subject。
        product = os.path.join(REPO, "docs", "workflows", "wf-release")
        if not os.path.isdir(product):
            raise SelectError("no release context and no WF_RELEASE_TREE")
        root = product
    sys.path.insert(0, os.path.join(REPO, "scripts"))
    import wf_release_common as common
    subject = common.release_subject(root, version, ref)
    return {"schema_version": CONTEXT_SCHEMA, "deploy": os.environ.get("WF_FIXTURE_DEPLOY", "dev"),
            "release_root": os.path.realpath(root), "version": version, "ref": ref,
            "release_subject": subject["digest"], "tree_digest": subject["subject"]["tree"],
            "manifest_digest": subject["subject"]["manifest"],
            "candidate": ({"commit": None} if os.environ.get("WF_FIXTURE_DEPLOY") == "candidate" else None)}


def execution_context():
    """本次真实执行身份（green 结果与 proof 用）。生产一次，随 bundle 冻结。"""
    context = release_context()
    return {
        "schema_version": 1,
        "deploy": context.get("deploy") or os.environ.get("WF_FIXTURE_DEPLOY", "dev"),
        "release_subject": context["release_subject"],
        "release_root_identity": digest({"root": context.get("release_root"),
                                         "tree": context.get("tree_digest")}),
        "candidate_commit": ((context.get("candidate") or {}).get("commit")
                             if context.get("deploy") == "candidate" else None),
        "runtime": _runtime_identity(),
        "platform": sys.platform,
    }


def public_inputs():
    """公共输入的**唯一**产生点：source/helpers/executor/runner 一次算齐并冻结进 bundle。"""
    return {"source": source_digest(),
            "helpers": helpers_digest(),
            "executor": file_digest(os.path.join(FULL, "execution.py")),
            "runner": {name: file_digest(os.path.join(HERE, name)) for name in RUNNER_FILES}}


def local_inputs(case, groups_doc):
    """case 局部输入：只含脚本/目标/用例元数据——worker 只需重算这部分。"""
    meta = (groups_doc.get("cases") or {}).get(case) or {}
    local = {"script": script_digest(case), "targets": targets_digest(case, meta),
             "case_meta": meta}
    if local["script"] is None:
        raise SelectError(f"case script is unreadable: {case}")
    return local


def red_subject(case, local, public, context):
    """red 可迁移主体：case 局部输入 + 冻结的公共输入 + 运行环境 + release 内容。

    deploy/根路径与各自 Git commit 仍被排除；公共输入不再逐 case 重算，只消费冻结值。
    """
    payload = {"schema": STATE_SCHEMA, "case": case, "local": local, "public": public,
               "runtime": context.get("runtime"), "platform": context.get("platform"),
               "release_subject": context.get("release_subject")}
    return digest(payload)


def input_fingerprint(case, local, public, context):
    """case 局部输入 + 冻结公共输入 + 本次完整 context（case execution 身份）。"""
    return digest({"schema": STATE_SCHEMA, "case": case, "local": local, "public": public,
                   "context": context})


def candidate_clean(meta):
    return bool((meta or {}).get("candidate_clean"))


def check_candidate_manifest(groups_doc):
    problems = []
    for name, meta in (groups_doc.get("cases") or {}).items():
        if not candidate_clean(meta):
            continue
        if meta.get("assertion_target") != "installed" or meta.get("stage_role") != "scaffold":
            problems.append(f"{name}: candidate_clean=true 但 assertion_target={meta.get('assertion_target')} "
                            f"stage_role={meta.get('stage_role')}")
    if problems:
        raise SelectError("候选 manifest 自相矛盾：\n- " + "\n- ".join(problems))


def _chosen(group_names, only, fixture_deploy, groups_doc):
    available = all_cases()
    known = set(available)
    unknown_groups = [name for name in group_names if name not in groups_doc["groups"]]
    if unknown_groups:
        raise SelectError("未知组：" + " ".join(unknown_groups) + "；可选：" +
                          " ".join(sorted(groups_doc["groups"])))
    if group_names:
        chosen = []
        for name in group_names:
            for case in groups_doc["groups"][name]:
                if case not in known:
                    raise SelectError(f"组 {name} 引用了不存在的用例：{case}")
                if case not in chosen:
                    chosen.append(case)
    else:
        chosen = list(available)
    if only:
        chosen = [case for case in chosen if only in case]
    if not chosen:
        raise SelectError(f"没有用例匹配（group={' '.join(group_names) or '-'} only={only!r}）；"
                          "可用组：" + " ".join(sorted(groups_doc["groups"])))
    skipped = []
    if fixture_deploy == "candidate":
        cases_meta = groups_doc.get("cases") or {}
        clean = [case for case in chosen if candidate_clean(cases_meta.get(case))]
        skipped = [case for case in chosen if case not in clean]
        if not clean:
            raise SelectError(
                "candidate 模式下这些用例都不是 candidate_clean=true：" + " ".join(chosen) +
                "；请在 dev 模式跑，或改用 f1_candidate_smoke 兜底闭环")
        chosen = clean
    return chosen, skipped


def select(group_names=(), only="", fixture_deploy="dev", mode="both", groups_doc=None):
    groups_doc = groups_doc or load_groups()
    check_candidate_manifest(groups_doc)
    chosen, skipped = _chosen(group_names, only, fixture_deploy, groups_doc)
    # freeze barrier：公共输入与执行上下文各算一次，随后逐 case 只算局部输入。
    context = execution_context()
    if context["deploy"] != fixture_deploy:
        raise SelectError(f"context deploy={context['deploy']} 与请求 {fixture_deploy} 不符")
    public = public_inputs()
    cases = {}
    for case in chosen:
        local = local_inputs(case, groups_doc)
        cases[case] = {"execution_fingerprint": input_fingerprint(case, local, public, context),
                       "red_subject_digest": red_subject(case, local, public, context),
                       "local_inputs": local}
    if mode == "auto":
        modes = auto_modes(cases, groups_doc, fixture_deploy)
    elif mode in ("green", "red", "both"):
        modes = {case: mode for case in chosen}
    else:
        raise SelectError(f"未知模式：{mode}")
    for case, value in modes.items():
        cases[case]["mode"] = value
    return {"cases": cases, "skipped_non_candidate": skipped, "mode": mode,
            "fixture_deploy": fixture_deploy, "groups": list(group_names), "only": only,
            "execution_context": context, "public_inputs": public}


def bundle_document(selection):
    return {"schema_version": BUNDLE_SCHEMA,
            "execution_context": selection["execution_context"],
            "public_inputs": selection["public_inputs"],
            "mode": selection["mode"],
            "cases": {case: {"mode": record["mode"],
                             "execution_fingerprint": record["execution_fingerprint"],
                             "red_subject_digest": record["red_subject_digest"],
                             "local_inputs": record["local_inputs"]}
                      for case, record in selection["cases"].items()},
            "skipped_non_candidate": selection["skipped_non_candidate"]}


def state_path():
    cache = os.environ.get("WF_TEST_RUN_CACHE") or os.path.join(os.path.expanduser("~"),
                                                               ".cache", "wf-test-run")
    return os.path.join(cache, "repro-state.json")


def read_state():
    path = state_path()
    try:
        with open(path, encoding="utf-8") as handle:
            state = json.load(handle)
    except FileNotFoundError:
        return {"schema_version": STATE_SCHEMA, "cases": {}}
    except (OSError, ValueError) as exc:
        raise SelectError(f"repro state is unreadable; refusing to replace it: {path}") from exc
    if not isinstance(state, dict) or not isinstance(state.get("cases"), dict):
        raise SelectError(f"repro state has an invalid shape; refusing to replace it: {path}")
    if state.get("schema_version") in (1, 2):
        # 旧内容保留但不算证明：不推导 context/subject。
        state = {"schema_version": STATE_SCHEMA,
                 "cases": {name: {"legacy": record} for name, record in state["cases"].items()}}
    elif state.get("schema_version") != STATE_SCHEMA:
        raise SelectError(f"unsupported repro state schema; refusing to replace it: {path}")
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


def auto_modes(cases, groups_doc, fixture_deploy="dev"):
    """dev：同 subject 的有效 dev red 才免注入；candidate：必须已有同主体 dev red。"""
    state = read_state()
    modes, missing = {}, []
    for case, record in cases.items():
        proof = ((state.get("cases") or {}).get(case) or {}).get("red") or {}
        usable = (proof.get("subject") == record["red_subject_digest"]
                  and record["local_inputs"]["targets"] is not None)
        if usable and fixture_deploy != "dev":
            usable = bool(proof.get("fingerprint"))
        if usable:
            modes[case] = "green"
        elif fixture_deploy == "dev":
            modes[case] = "both"
        else:
            missing.append(case)
    if missing:
        raise SelectError(
            "candidate 模式下 --mode auto 缺少同名主体的有效 dev red 证明：" + " ".join(sorted(missing)) +
            "；请先在 dev 模式用同一 release 内容/version/ref 跑 --mode red/both"
            "（例如 WF_TEST_RELEASE_VERSION=<候选版本> 后再跑），或显式 --mode green")
    return modes


def validate_bundle(bundle):
    if not isinstance(bundle, dict) or bundle.get("schema_version") != BUNDLE_SCHEMA:
        raise SelectError(
            f"bundle schema invalid: {bundle.get('schema_version') if isinstance(bundle, dict) else None}"
            f"（只接受 schema {BUNDLE_SCHEMA}；bundle 是每 run 产物，不迁移旧 schema）")
    context = bundle.get("execution_context") or {}
    for key in ("deploy", "release_subject", "runtime", "platform"):
        if not context.get(key):
            raise SelectError(f"bundle execution context missing {key}")
    public = bundle.get("public_inputs")
    if not isinstance(public, dict):
        raise SelectError("bundle has no public_inputs")
    for key in ("source", "helpers", "executor"):
        if not public.get(key):
            raise SelectError(f"bundle public_inputs missing {key}")
    runner = public.get("runner")
    if not isinstance(runner, dict) or not runner or not all(runner.values()):
        raise SelectError("bundle public_inputs.runner is incomplete")
    cases = bundle.get("cases")
    if not isinstance(cases, dict) or not cases:
        raise SelectError("bundle has no cases")
    for case, record in cases.items():
        if not isinstance(record, dict) or record.get("mode") not in PHASES:
            raise SelectError(f"{case}: invalid mode in bundle")
        for key in ("execution_fingerprint", "red_subject_digest"):
            if not record.get(key):
                raise SelectError(f"{case}: bundle missing {key}")
        local = record.get("local_inputs")
        if not isinstance(local, dict) or not local.get("script"):
            raise SelectError(f"{case}: bundle missing local_inputs")
    return context, cases


def validate_repro(root, bundle):
    """纯校验：gate 与 writer 共用同一份 PASS/phase 规则，不复制第二套。"""
    context, expected = validate_bundle(bundle)
    root = os.path.abspath(root)
    records, malformed = {}, []
    for path in sorted(glob.glob(os.path.join(root, "*.json"))):
        if os.path.basename(path) in ("inputs.json", ".wf-results-owner.json"):
            continue
        try:
            with open(path, encoding="utf-8") as handle:
                record = json.load(handle)
            case = record["case"]
            mode = record["mode"]
            phases = PHASES.get(mode)
            if (not isinstance(case, str) or os.path.basename(path) != case + ".json"
                    or case in records or case not in expected or mode != expected[case]["mode"]
                    or type(record.get("verified")) is not bool
                    or record.get("execution_fingerprint") != expected[case]["execution_fingerprint"]
                    or record.get("bundle_sha256") != bundle["__sha256"]
                    or any(record.get(p) not in ("pass", "fail") for p in phases)
                    or record["verified"] != all(record.get(p) == "pass" for p in phases)):
                raise SelectError("contradictory case/mode/phase result")
            for phase in ("green", "red"):
                seconds = record.get(phase + "_seconds", 0)
                if not isinstance(seconds, (int, float)) or seconds < 0:
                    raise SelectError("invalid duration")
            if record["verified"]:
                sys.path.insert(0, FULL)
                import execution
                for phase in phases:
                    actual = (record.get("phases") or {}).get(phase) or {}
                    log = os.path.join(root, "logs", f"{case}.{phase}.log")
                    if (actual.get("rc") != 0 or actual.get("status") != "passed"
                            or not execution.verdict(log, actual["rc"], "repro")["ok"]):
                        raise SelectError("phase evidence contradicts execution or log")
            records[case] = record
        except (OSError, ValueError, TypeError, KeyError) as exc:
            malformed.append(os.path.basename(path))
            continue
    missing = [case for case in expected if case not in records]
    return {"records": records, "malformed": malformed, "missing": missing, "expected": expected}


def commit_state(results_dir, bundle_path=None, expected_sha=None, expected_size=None):
    """唯一 writer：先验租约/输入，再重读**同一** bundle 与结果，最后原子合并 state。"""
    sys.path.insert(0, FULL)
    import fixture_scope

    fixture_scope.verify_lease()
    fixture_scope.verify_results_lock()
    release_root = os.environ.get("WF_RELEASE_TREE")
    deploy = os.environ.get("WF_FIXTURE_DEPLOY", "dev")
    if deploy == "dev" and release_root:
        sys.path.insert(0, os.path.join(REPO, "scripts"))
        import release_lock

        release_lock.verify_lease(release_root)
    elif deploy == "candidate" and release_root:
        # candidate 不走 dev release flock，改在最终 barrier 重跑完整 validator（含 tag/clean/meta/tree）。
        import subprocess

        validator = (os.environ.get("WF_CANDIDATE_VALIDATOR")
                     or os.path.join(FULL, "prepare_candidate_repo.py"))
        check = subprocess.run([sys.executable, validator, "--check", "--out", release_root,
                                "--version", os.environ.get("WF_RELEASE_VERSION", "")],
                               capture_output=True, text=True)
        if check.returncode != 0:
            raise SelectError("candidate final barrier failed: " +
                              (check.stderr.strip() or check.stdout.strip())[:200])
    path = bundle_path or os.environ.get("WF_REPRO_INPUTS_FILE")
    if not path:
        raise SelectError("bundle path is required")
    with open(path, "rb") as handle:
        data = handle.read()
    sha = hashlib.sha256(data).hexdigest()
    if expected_sha and sha != expected_sha:
        raise SelectError("bundle digest changed since freeze")
    if expected_size and len(data) != int(expected_size):
        raise SelectError("bundle size changed since freeze")
    bundle = json.loads(data)
    bundle["__sha256"] = sha
    report = validate_repro(results_dir, bundle)
    if report["malformed"] or report["missing"]:
        raise SelectError("malformed/missing repro results: " +
                          " ".join(report["malformed"] + report["missing"]))
    groups_doc = load_groups()
    # final barrier：公共输入与执行上下文各重算**一次**（不随 case 数增长），与冻结值比对。
    context = bundle["execution_context"]
    if context != execution_context():
        raise SelectError("repro execution context changed since freeze (re-run required)")
    public = public_inputs()
    if public != bundle.get("public_inputs"):
        raise SelectError("public inputs changed since freeze (re-run required)")
    state = read_state()
    updated, kept = [], []
    for case, record in report["records"].items():
        if not record.get("verified"):
            continue
        expected = report["expected"][case]
        local = local_inputs(case, groups_doc)
        if local != expected["local_inputs"]:
            raise SelectError(f"{case}: case local inputs changed since freeze")
        subject = red_subject(case, local, public, context)
        if subject != expected["red_subject_digest"]:
            raise SelectError(f"{case}: case inputs changed since freeze")
        entry = state["cases"].get(case) or {}
        if "green" in PHASES[record["mode"]]:
            entry["green"] = {"fingerprint": expected["execution_fingerprint"], "verified_at": now()}
        if "red" in PHASES[record["mode"]] and context["deploy"] == "dev":
            entry["red"] = {"subject": subject, "fingerprint": expected["execution_fingerprint"],
                            "verified_at": now()}
        state["cases"][case] = entry
        updated.append(case)
    kept = [case for case in state["cases"] if case not in updated]
    return write_state(state), updated, kept


def shell_quote(value):
    return "'" + str(value).replace("'", "'\\''") + "'"


def write_bundle(path, document):
    directory = os.path.dirname(path) or "."
    os.makedirs(directory, exist_ok=True)
    handle = tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=directory, prefix=".inputs-",
                                         delete=False, suffix=".json")
    try:
        json.dump(document, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    finally:
        handle.close()
    os.replace(handle.name, path)
    data = open(path, "rb").read()
    return hashlib.sha256(data).hexdigest(), len(data)


def emit(selection, fmt):
    if fmt == "json":
        print(json.dumps(selection, ensure_ascii=False, indent=2, sort_keys=True))
        return
    tsv = "".join(f"{case}\t{record['mode']}\n" for case, record in selection["cases"].items())
    print("REPRO_CASES_TSV=" + shell_quote(tsv))
    print("REPRO_SKIPPED_LIST=" + shell_quote(" ".join(selection["skipped_non_candidate"])))
    print("REPRO_CASE_COUNT=" + str(len(selection["cases"])))
    print("REPRO_STATE_FILE=" + shell_quote(state_path()))
    print("REPRO_SELECT_OK=1")


def main(argv=None):
    parser = argparse.ArgumentParser(description="repro 用例选择/冻结/状态")
    sub = parser.add_subparsers(dest="command", required=True)
    plan_p = sub.add_parser("plan")
    plan_p.add_argument("--group", action="append", default=[])
    plan_p.add_argument("--only", default="")
    plan_p.add_argument("--fixture-deploy", default="dev", choices=("dev", "candidate"))
    plan_p.add_argument("--mode", default="both", choices=("green", "red", "both", "auto"))
    plan_p.add_argument("--format", default="sh", choices=("sh", "json"))
    plan_p.add_argument("--bundle", default=None, help="原子写出唯一冻结 bundle")
    plan_p.add_argument("--freeze", action="store_true", help="按 --bundle 冻结并输出摘要/长度")
    commit_p = sub.add_parser("commit-state")
    commit_p.add_argument("--results", required=True)
    commit_p.add_argument("--bundle", default=None)
    commit_p.add_argument("--bundle-sha256", default=None)
    commit_p.add_argument("--bundle-size", default=None)
    commit_p.add_argument("--format", default="sh", choices=("sh", "json"))
    describe_p = sub.add_parser("describe")
    describe_p.add_argument("--group", action="append", default=[])
    describe_p.add_argument("--fixture-deploy", default="dev", choices=("dev", "candidate"))
    args = parser.parse_args(argv)
    try:
        if args.command == "plan":
            selection = select(args.group, args.only, args.fixture_deploy, args.mode)
            if args.bundle:
                sha, size = write_bundle(args.bundle, bundle_document(selection))
                print(f"REPRO_BUNDLE={shell_quote(args.bundle)}")
                print(f"REPRO_BUNDLE_SHA256={sha}")
                print(f"REPRO_BUNDLE_SIZE={size}")
            emit(selection, args.format)
            return 0
        if args.command == "commit-state":
            path, updated, kept = commit_state(args.results, args.bundle, args.bundle_sha256,
                                               args.bundle_size)
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
    except (SelectError, OSError, ValueError) as exc:
        print(f"SELECT-ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
