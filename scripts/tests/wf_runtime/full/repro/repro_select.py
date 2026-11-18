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
gate 只读调用 `validate_repro()`；唯一全局 writer 是 root controller 在收尾阶段调用的一次
`commit_state()`，它要求每个相位都有本代 receipt、监督清理已确认且本地清理为 `removed`。
"""
from __future__ import annotations

import argparse
import datetime
import glob
import hashlib
import json
import math
import os
import re
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
FULL = os.path.dirname(HERE)
REPO = os.path.abspath(os.path.join(HERE, "..", "..", "..", "..", ".."))
GROUPS_JSON = os.path.join(HERE, "groups.json")
HELPERS = ("cli.py", "_harness.py", "_release.py", "_review_flow.py", "_review_launch.py",
           "_snapshot.py", "_executor_set.py", "_worker.py",
           # 公共 helper 必须全部进入证明身份：这些文件改变行为（公开 argv 语义、库来源、
           # scope/layout、候选最终校验、发行上下文、结果/摘要判定、主 runner shell）时，
           # 旧 red/green 证明必须失去资格，而不是按“版本号相同”继续复用。
           "../library_source.py", "../prepare_candidate_repo.py", "../release_context.py",
           "../results_gate.py", "../results_summary.py", "../fixture_scope.py",
           "../execute_gate.py", "../resource_lifecycle.py", "../run_all.sh",
           "../../../../wf_test_paths.py")
RUNNER_FILES = ("cli.py", "repro_select.py", "run.sh")
# 协议成组升级：bundle/state/context 一次性换代，旧证明只作 legacy（不静默兼容）。
# v5 起 red/green 证明必须带清理已确认的相位证据；v1-v4 一律只读作历史。
STATE_SCHEMA = 5
LEGACY_STATE_SCHEMAS = (1, 2, 3, 4)
BUNDLE_SCHEMA = 3
# 结果根里的生命周期/摘要文件：不是 repro case 结果，禁止被 validate_repro 当记录读取。
NON_CASE_FILES = {".wf-results-owner.json", "inputs.json", "run-state.json", "summary.json",
                  "summary-metrics.json", "summary-measurements.json", "release-context.json",
                  "repro.bundle.json", "source-hygiene.before.json", "plan.json"}
CONTEXT_SCHEMA = 2
RELEASE_CONTEXT_SCHEMA = 2
PHASES = {"green": ("green",), "red": ("red",), "both": ("green", "red")}
PHASE_STATES = ("planned", "passed", "failed", "unverified")

sys.path.insert(0, os.path.join(REPO, "scripts"))
import wf_test_paths  # noqa: E402


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


def _identity_projection(resolved):
    """完整运行身份的对外投影：只留摘要与 role/version 诊断，不转存环境/路径值。"""
    return {"role": resolved["role"],
            "path_identity": resolved["path_identity"],
            "binary_digest": resolved["binary"]["digest"],
            "invocation_digest": resolved["invocation_file"]["digest"],
            "implementation": resolved["implementation"],
            "version": resolved["version"]}


def _runtime_identity():
    """tool/SUT 的完整身份（调用文件字节 + 解释器二进制字节 + 路径身份 + 实现/版本）。

    任一项解析不出即拒绝本次运行（不签发空身份，也不用“版本号相同”冒充相同运行时）。
    """
    sys.path.insert(0, os.path.join(REPO, "scripts"))
    try:
        import python_runtime_identity as identity
    except ImportError as exc:  # 假环境缺少 helper 是配置错误，不是可跳过条件
        raise SelectError(f"runtime identity helper is unavailable: {exc}") from exc
    resolver = identity.Resolver()
    try:
        return {"tool": _identity_projection(
                    resolver.resolve("tool", os.path.join(HERE, "_worker.py"))),
                "sut": _identity_projection(
                    resolver.resolve("sut", os.path.join(FULL, "f1_init.py")))}
    except identity.IdentityError as exc:
        raise SelectError(f"runtime identity is unresolved: {exc}") from exc


def release_context():
    """已核发行身份：只接受 controller 写在结果根里的 release-context。

    独立与内嵌 repro 都不再从环境变量合成发行事实：候选 commit、树摘要、runtime 身份必须
    来自同一份已核验上下文，否则旧证明/无提交猜测会冒充本代证据。
    """
    SCAN_COUNTS["release"] += 1
    path = os.environ.get("WF_RELEASE_CONTEXT")
    if not path:
        raise SelectError(
            "release context is required (controller must hand off release-context.json)")
    try:
        with open(path, encoding="utf-8") as handle:
            context = json.load(handle)
    except (OSError, ValueError) as exc:
        raise SelectError(f"release context unreadable: {path}") from exc
    if context.get("schema_version") != RELEASE_CONTEXT_SCHEMA:
        raise SelectError(
            f"release context schema must be {RELEASE_CONTEXT_SCHEMA}; "
            "old contexts are not accepted (re-run the runner)")
    if not context.get("release_subject") or not isinstance(context.get("runtime"), dict):
        raise SelectError("release context schema/subject/runtime invalid")
    if context.get("deploy") not in ("dev", "candidate"):
        raise SelectError(f"release context deploy invalid: {context.get('deploy')!r}")
    if not context.get("release_root") or not context.get("version") or not context.get("ref"):
        raise SelectError("release context release identity is incomplete")
    if context["deploy"] == "candidate":
        commit = (context.get("candidate") or {}).get("commit")
        if not commit or not isinstance(commit, str):
            raise SelectError("candidate release context has no verified commit")
    return context


def execution_context():
    """本次真实执行身份（green 结果与 proof 用）。生产一次，随 bundle 冻结。"""
    context = release_context()
    return {
        "schema_version": CONTEXT_SCHEMA,
        "deploy": context["deploy"],
        "release_subject": context["release_subject"],
        "release_root_identity": digest({"root": context.get("release_root"),
                                         "tree": context.get("tree_digest")}),
        "candidate_commit": ((context.get("candidate") or {}).get("commit")
                             if context["deploy"] == "candidate" else None),
        "runtime": _runtime_identity(),
        "platform": sys.platform,
    }


def public_inputs():
    """公共输入的**唯一**产生点：source/helpers/executor/runner 一次算齐并冻结进 bundle。"""
    return {"helper_set": "core-v2",
            "source": source_digest(),
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
    cache = os.environ.get("WF_TEST_RUN_CACHE")
    if not cache:
        cache = (str(wf_test_paths.resolve_layout()["state"])
                 if wf_test_paths.current_scope() is not None
                 else os.path.join(os.path.expanduser("~"), ".cache", "wf-test-run"))
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
    schema = state.get("schema_version")
    if schema in LEGACY_STATE_SCHEMAS:
        # 旧内容保留但不算证明：v1-v4 的 green/red 都缺少本规则要求的清理证据。
        return {"schema_version": STATE_SCHEMA,
                "cases": {name: {"legacy": record} for name, record in state["cases"].items()}}
    if schema != STATE_SCHEMA:
        raise SelectError(f"unsupported repro state schema; refusing to replace it: {path}")
    return state


def write_state(state):
    """原子写：读/写/落盘/replace 失败都保持旧文件字节，原先没有就仍不创建。"""
    path = state_path()
    try:
        wf_test_paths.require_in_scope(path)
    except wf_test_paths.PathError as exc:
        raise SelectError(f'repro state path escapes the test scope: {exc}') from exc
    directory = os.path.dirname(path) or "."
    try:
        os.makedirs(directory, exist_ok=True)
    except OSError as exc:
        raise SelectError(f"repro state directory is unusable; previous state is unchanged: "
                          f"{directory}: {exc}") from exc
    temporary = None
    failure = None
    try:
        handle = tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=directory,
                                             prefix=".state-", delete=False, suffix=".json")
        temporary = handle.name
        try:
            json.dump(state, handle, ensure_ascii=False, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        finally:
            handle.close()
        os.replace(temporary, path)
        temporary = None
    except (OSError, ValueError, TypeError) as exc:
        failure = exc
    orphan = None
    if temporary is not None:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
        except OSError as exc:
            orphan = temporary
            failure = failure or exc
    if failure is not None:
        detail = f"{failure}"
        if orphan:
            detail += f"; temporary file left behind: {orphan}"
        raise SelectError(
            f"repro state write failed; the previous state file is unchanged: {detail}") from failure
    return path


def auto_modes(cases, groups_doc, fixture_deploy="dev"):
    """dev：同 subject 且清理已确认的有效 dev red 才免注入；candidate 还要求同主体 dev red。

    v5 之前的状态只作历史：旧 red 没有本代相位清理证明，`auto` 不命中（必须重验）。
    """
    state = read_state()
    modes, missing = {}, []
    for case, record in cases.items():
        proof = ((state.get("cases") or {}).get(case) or {}).get("red") or {}
        usable = (proof.get("subject") == record["red_subject_digest"]
                  and proof.get("cleanup") == "removed"
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
    if context.get("schema_version") != CONTEXT_SCHEMA:
        raise SelectError(
            f"bundle execution context schema must be {CONTEXT_SCHEMA}（旧上下文不迁移、不混读）")
    for key in ("deploy", "release_subject", "runtime", "platform"):
        if not context.get(key):
            raise SelectError(f"bundle execution context missing {key}")
    runtime = context.get("runtime") or {}
    for role in ("tool", "sut"):
        projection = runtime.get(role)
        if not isinstance(projection, dict) or not projection.get("path_identity") \
                or not projection.get("binary_digest") or not projection.get("version"):
            raise SelectError(f"bundle runtime identity is incomplete for role {role}")
    public = bundle.get("public_inputs")
    if not isinstance(public, dict):
        raise SelectError("bundle has no public_inputs")
    if public.get("helper_set") != "core-v2":
        raise SelectError(
            "bundle public_inputs helper set is stale（公共 helper 身份已换代；重新运行以重新冻结）")
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


def _phase_verdict(root, case, phase, record, evidence_root, run_id):
    """单相位判定：断言事实、receipt 归属与清理确认同一条规则。

    返回 (state, reason)。state ∈ {passed, failed, unverified}：
    - 断言证据完整且通过、本代 receipt 终态、监督调用清理且相位目录已回收 → passed；
    - 断言证据完整且不通过 → failed；
    - 其余（缺 receipt/错代/路径或相位错配/清理未确认/显式保留）→ unverified。
    """
    log = os.path.join(root, "logs", f"{case}.{phase}.log")
    actual = (record.get("phases") or {}).get(phase)
    if not isinstance(actual, dict):
        return "unverified", f"{case}.{phase}: phase execution evidence missing"
    if not os.path.isfile(log):
        return "unverified", f"{case}.{phase}: phase log missing"
    sys.path.insert(0, FULL)
    import execution
    assertion = execution.verdict(log, actual.get("rc"), "repro", phase=phase)
    if not assertion["ok"]:
        return "failed", f"{case}.{phase}: target assertion failed ({assertion['reason'].strip()})"
    command_id = actual.get("command_id")
    if not isinstance(command_id, str) or not command_id:
        return "unverified", f"{case}.{phase}: phase command identity missing"
    if not evidence_root or not run_id:
        return "unverified", f"{case}.{phase}: phase receipt domain is not available"
    import resource_lifecycle as lifecycle
    receipt_path = lifecycle.receipt_path(evidence_root, command_id)
    try:
        receipt = lifecycle.read_receipt(receipt_path)
    except (OSError, lifecycle.LifecycleError) as exc:
        return "unverified", f"{case}.{phase}: phase receipt unusable ({exc})"
    problems = []
    if receipt.get("run_id") != run_id:
        problems.append(f"receipt belongs to run_id={receipt.get('run_id')!r}")
    if receipt.get("command_id") != command_id:
        problems.append("receipt command_id mismatch")
    if os.path.realpath(receipt.get("log_path") or "") != os.path.realpath(log):
        problems.append("receipt log path mismatch")
    if receipt.get("state") != "finished":
        problems.append(f"receipt is {receipt.get('state')!r}")
    result = receipt.get("result") or {}
    if result.get("rc") != actual.get("rc") or result.get("status") != actual.get("status"):
        problems.append("receipt result differs from the phase record")
    argv = receipt.get("argv") or []
    script = os.path.join(HERE, case + ".py")
    if script not in argv or phase not in argv:
        problems.append("receipt command identity does not name this case/phase")
    supervision = receipt.get("supervision") or {}
    if supervision.get("cleanup_state") != "cleaned":
        problems.append(f"supervision cleanup is {supervision.get('cleanup_state')!r}")
    if receipt.get("local_cleanup") != "removed":
        problems.append(f"phase cleanup is {receipt.get('local_cleanup')!r}")
    if problems:
        return "unverified", f"{case}.{phase}: " + "; ".join(problems)
    return "passed", ""


def validate_repro(root, bundle, evidence_root=None, run_id=None):
    """纯校验：gate 与 writer 共用同一份 PASS/phase/清理规则，不复制第二套。

    `evidence_root` 是本代 receipt 目录（父根或独立结果根的 `commands/`），`run_id` 是本代
    运行标识；两者缺失时相位一律记为 unverified —— 没有本代清理证据就没有 proof。
    """
    context, expected = validate_bundle(bundle)
    root = os.path.abspath(root)
    records, malformed = {}, []
    phases = {phase: {"planned": 0, "passed": 0, "failed": 0, "unverified": 0}
              for phase in ("green", "red")}
    case_states = {}
    for path in sorted(glob.glob(os.path.join(root, "*.json"))):
        # 结果根同时承载生命周期证据（schema2 owner/run-state/摘要/控制记录）；
        # 它们不是 case 结果，由 bundle 或对应 reader 单独核验。
        if os.path.basename(path) in NON_CASE_FILES:
            continue
        try:
            with open(path, encoding="utf-8") as handle:
                record = json.load(handle)
            case = record["case"]
            mode = record["mode"]
            planned = PHASES.get(mode)
            if (not isinstance(case, str) or os.path.basename(path) != case + ".json"
                    or case in records or case not in expected or mode != expected[case]["mode"]
                    or type(record.get("verified")) is not bool
                    or record.get("execution_fingerprint") != expected[case]["execution_fingerprint"]
                    or record.get("bundle_sha256") != bundle["__sha256"]
                    or any(record.get(p) not in ("pass", "fail") for p in planned)
                    or record["verified"] != all(record.get(p) == "pass" for p in planned)):
                raise SelectError("contradictory case/mode/phase result")
            for phase in ("green", "red"):
                seconds = record.get(phase + "_seconds", 0)
                if (not isinstance(seconds, (int, float)) or isinstance(seconds, bool)
                        or not math.isfinite(seconds) or seconds < 0):
                    raise SelectError("invalid duration")
                if phase not in planned and record.get(phase, "skip") != "skip":
                    raise SelectError(f"{phase} is not part of mode {mode} but carries a result")
            states = {}
            for phase in planned:
                states[phase], _reason = _phase_verdict(root, case, phase, record,
                                                        evidence_root, run_id)
                phases[phase]["passed" if states[phase] == "passed"
                              else "failed" if states[phase] == "failed" else "unverified"] += 1
            all_passed = all(states[phase] == "passed" for phase in planned)
            if record["verified"] and not all_passed:
                # 断言记录说“通过”但本代清理/收据证据不成立：不是可复用的证明。
                record["verified"] = False
                record["evidence_problem"] = "; ".join(
                    f"{phase}:{states[phase]}" for phase in planned if states[phase] != "passed")
            case_states[case] = states
            records[case] = record
        except (OSError, ValueError, TypeError, KeyError) as exc:
            malformed.append(os.path.basename(path))
            continue
    missing = [case for case in expected if case not in records]
    for case, record in expected.items():
        for phase in PHASES[record["mode"]]:
            phases[phase]["planned"] += 1
    return {"records": records, "malformed": malformed, "missing": missing,
            "expected": expected, "phases": phases, "case_states": case_states}


def commit_state(results_dir, bundle_path=None, expected_sha=None, expected_size=None,
                 run_id=None, evidence_root=None):
    """唯一 writer：先验租约/输入，再重读**同一** bundle 与结果，最后原子合并 state。

    只接收本代、相位证据齐全（receipt 终态 + 监督清理 + 本地回收）且断言通过的用例。
    """
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
    # candidate 的结束校验由 root controller 在调用本 writer 之前完成（同一只读 validator、
    # 同一身份）；这里不再重复调用，避免同一 run 出现第二个结束 barrier 判定点。
    if not run_id:
        raise SelectError("repro proof requires the current run_id")
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
    report = validate_repro(results_dir, bundle, evidence_root=evidence_root, run_id=run_id)
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
            entry["green"] = {"fingerprint": expected["execution_fingerprint"],
                              "cleanup": "removed", "verified_at": now()}
        if "red" in PHASES[record["mode"]] and context["deploy"] == "dev":
            entry["red"] = {"subject": subject, "fingerprint": expected["execution_fingerprint"],
                            "cleanup": "removed", "verified_at": now()}
        state["cases"][case] = entry
        updated.append(case)
    kept = [case for case in state["cases"] if case not in updated]
    if not updated:
        # 没有合格用例就等于没有新证明：不改写状态文件（v1-v4 也不因本次运行转格式）。
        return None, [], kept
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
    with open(path, "rb") as handle:
        data = handle.read()
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


def list_selection(group_names=(), only="", fixture_deploy="dev", groups_doc=None):
    """纯清单：只读组/用例登记，不计算 release subject，不读 proof/state/缓存。

    dev 默认两个面都跑（both），候选只跑 candidate-clean 用例的 green 面。
    """
    groups_doc = groups_doc or load_groups()
    check_candidate_manifest(groups_doc)
    chosen, skipped = _chosen(group_names, only, fixture_deploy, groups_doc)
    mode = "green" if fixture_deploy == "candidate" else "both"
    return {"cases": {case: mode for case in chosen}, "skipped_non_candidate": skipped,
            "fixture_deploy": fixture_deploy}


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
    list_p = sub.add_parser("list")
    list_p.add_argument("--group", action="append", default=[])
    list_p.add_argument("--only", default="")
    list_p.add_argument("--fixture-deploy", default="dev", choices=("dev", "candidate"))
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
        if args.command == "list":
            listed = list_selection(args.group, args.only, args.fixture_deploy)
            for case, mode in listed["cases"].items():
                print(f"{case}\t{mode}")
            if listed["skipped_non_candidate"]:
                print("repro: skipped_non_candidate: " +
                      " ".join(listed["skipped_non_candidate"]), file=sys.stderr)
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
