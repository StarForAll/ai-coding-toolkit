"""repro 用例共用脚手架。

契约（方案 A）：
- `--expect green`：在**当前树**上跑 check，必须成立；
- `--expect red`  ：把改动复制到临时目录、注入"退回修复前"的那一处，再跑同一 check，**必须失败**。

这样"断言有效"不靠声明，而是靠"注入原缺陷后必然变红"来证明；
空断言、弱断言在这里过不去（注入后它不会红）。
"""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import tempfile

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))))
PAYLOAD = os.path.join(REPO, "docs", "workflows", "wf", "payload")

# ---- 发行身份：由 runner 通过环境注入（dev=测试发行副本；candidate=候选仓库根）----------
# 缺省值只为“直接手跑某个用例”保留开发态语义。
DEFAULT_RELEASE = os.path.join(REPO, "docs", "workflows", "wf-release")
RELEASE = os.environ.get("WF_RELEASE_TREE") or DEFAULT_RELEASE
RELEASE_VERSION = os.environ.get("WF_RELEASE_VERSION") or "0.1.0"
RELEASE_REF = os.environ.get("WF_RELEASE_REF") or f"refs/tags/wf-v{RELEASE_VERSION}"


def release_tag(ref=None):
    """`refs/tags/wf-vX.Y.Z` → `wf-vX.Y.Z`（install.py 需要 tag 名，记录要完整 ref）。"""
    ref = RELEASE_REF if ref is None else ref
    return ref.split("refs/tags/", 1)[-1]


def test_lib():
    """wflib 来源：夹具项目 `.wf/lib` → `WF_TEST_LIB` → 源码 payload/lib（仅 dev）。

    唯一 resolver 在 `full/library_source.py`：candidate 部署禁止源码回退；stage 注入类
    白盒用例的 `candidate_clean` 必须是 false（见 repro/groups.json）。
    """
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    import library_source
    return library_source.resolve(env=os.environ)[0]


_STAGED = []


def stage():
    """把 payload 复制到临时目录，返回 (根, lib, payload)。注入与运行都在副本上做。"""
    root = tempfile.mkdtemp(prefix="wf-repro-")
    _STAGED.append(root)
    dest = os.path.join(root, "payload")
    shutil.copytree(PAYLOAD, dest, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    return root, os.path.join(dest, "lib"), dest


def patch(path, old, new):
    """把修复点退回缺陷形态；找不到就说明脚本已过期（要显式失败）。"""
    with open(path, encoding="utf-8") as handle:
        text = handle.read()
    if old not in text:
        raise SystemExit(f"repro stale: pattern not found in {path}: {old[:60]!r}")
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(text.replace(old, new, 1))


def load(lib):
    if lib not in sys.path:
        sys.path.insert(0, lib)


INTERNAL_CODES = {"WF_INTERNAL_ERROR"}


def require_business_code(payload, rc):
    """目标调用必须返回**已知业务原因码**，否则按前置失败处理。

    - 没有载荷/没有 code（解析失败、未捕获异常、脚本崩溃）→ 前置失败；
    - code 是内部错误或不在码表 → 前置失败（第十一轮复审 N11-3：`WF_BOGUS` 也曾被放过）。
    """
    code = (payload or {}).get("code")
    if code in INTERNAL_CODES:
        raise Precondition(f"目标调用内部错误：code={code}")
    if not isinstance(code, str) or not code.startswith("WF_"):
        raise Precondition(f"目标调用未返回业务原因码：rc={rc} code={code}")
    lib = test_lib()
    if lib not in sys.path:
        sys.path.insert(0, lib)
    try:
        from wflib import codes as _codes
        known = set(_codes.CODES)
    except Exception:  # noqa: BLE001 — 码表不可读时不放过任何未知码
        known = set()
    if code not in known:
        raise Precondition(f"未知原因码（不在码表）：code={code}")


def require_success(payload, rc, context=""):
    """目标调用必须**成功**；非成功即前置失败（不能拿来当"目标断言被击中"）。"""
    code = (payload or {}).get("code")
    if code != "WF_OK":
        raise Precondition(f"{context} 未成功：rc={rc} code={code}")


def only_two_outcomes(code, expected_code, context=""):
    """用例只承认两种结局：命中期望码（修复成立），或缺陷复现（成功）。

    其它任何原因码（含内部码、未知码、无关业务码）都属前置问题，不能让 red 通过
    （第十四轮复审 F14-2）。
    """
    if code == expected_code:
        return "expected"
    if code == "WF_OK":
        return "defect"
    raise Precondition(f"{context} 出现第三种结果：code={code}")


def code_problem(payload, expected_codes):
    """把一次调用的结果归类：命中期望码 → None；内部/未知码 → Precondition；其它业务码 → 目标失败原因。"""
    code = (payload or {}).get("code")
    if code in expected_codes:
        return None
    if code in INTERNAL_CODES or not isinstance(code, str) or not code.startswith("WF_"):
        raise Precondition(f"目标调用非业务失败：code={code}")
    lib = test_lib()
    if lib not in sys.path:
        sys.path.insert(0, lib)
    from wflib import codes as _codes
    if code not in set(_codes.CODES):
        raise Precondition(f"未知原因码：code={code}")
    raise TargetFailure(f"原因码不是期望值 {sorted(expected_codes)}：{code}")


def git_repo(path):
    os.makedirs(path, exist_ok=True)
    for cmd in (["git", "init", "-q"], ["git", "config", "user.email", "r@example.com"],
                ["git", "config", "user.name", "r"]):
        subprocess.run(cmd, cwd=path, check=True, capture_output=True)
    return path


def commit_all(path, message="init"):
    subprocess.run(["git", "add", "-A"], cwd=path, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-qm", message, "--allow-empty"],
                   cwd=path, check=True, capture_output=True)


class TargetFailure(Exception):
    """目标断言被击中：red 模式下的"通过"，green 模式下的"失败"。

    只有它能在 red 模式里算通过——运行期内部错误、夹具错误都不得冒充目标失败
    （第十轮复审 N10-2）。
    """


class Precondition(Exception):
    """夹具/环境前置不成立：既不算"通过"，也不算"目标断言被击中"。

    red 模式只接受"目标断言失败"（返回字符串），前置失败必须显式失败，
    否则无关的运行错误会让 red 假通过（第九轮复审 N9-4）。
    """


def _cleanup():
    """staged 目录的回收许可来自真实监督结论：
    - WF_REPRO_KEEP=1：显式保留并报告路径；
    - WF_REPRO_DEFER_CLEANUP=1：托管 worker 在 supervision 核验后统一回收相位目录；
    - 两者都没有（手工直接 case）：不假装清理成功，保留并报告 staged 路径。"""
    if os.environ.get("WF_REPRO_KEEP") == "1":
        for path in _STAGED:
            print(f"STAGED-KEPT: {path}", file=__import__("sys").stderr)
        _STAGED.clear()
        return
    if os.environ.get("WF_REPRO_DEFER_CLEANUP") == "1":
        for path in _STAGED:
            print(f"STAGED-DEFERRED: {path}", file=__import__("sys").stderr)
        _STAGED.clear()
        return
    kept = []
    for path in _STAGED:
        shutil.rmtree(path, ignore_errors=True)
        if os.path.exists(path):
            kept.append(path)
    if kept:
        print("STAGED-RETAINED: " + " ".join(kept), file=__import__("sys").stderr)
    _STAGED.clear()


def main(check):
    """argparse + 结论输出：check() 返回 None 表示成立，返回字符串表示不成立的原因。"""
    parser = argparse.ArgumentParser()
    parser.add_argument("--expect", choices=("green", "red"), required=True)
    args = parser.parse_args()
    if args.expect == "red":
        os.environ["WF_REPRO_INJECT"] = "1"   # check() 内的 patch 分支据此生效
    try:
        return _run(args, check)
    finally:
        _cleanup()


def _run(args, check):
    target = False
    try:
        problem = check()
    except Precondition as exc:
        print(f"FAIL {args.expect}: 前置失败：{exc}")
        return 1
    except TargetFailure as exc:
        problem, target = str(exc), True
    if problem is not None and not target:
        # 返回字符串但没标成目标失败：按前置/未归类失败处理，两种模式都不算通过
        print(f"FAIL {args.expect}: 未归类的失败（应以 TargetFailure 抛出）：{problem}")
        return 1
    if args.expect == "green":
        if target:
            print(f"FAIL green: 目标断言在未注入时也失败：{problem}")
            return 1
        print("PASS green: check holds on current tree")
        return 0
    if target:
        print(f"PASS red: 注入缺陷后目标断言变红：{problem}")
        return 0
    print("FAIL red: 注入缺陷后目标断言仍未变红（断言无效）")
    return 1

RULES_DIGEST = "sha256:" + "a" * 64


def install_fixture(root, *, source_commit="c0", generation=2, platform="claudecode",
                    installed_platforms=("dsh",), roots=(".agents/skills",),
                    rules_digest=RULES_DIGEST, release_ref=None, version=None):
    """最小可用的"已安装项目"：安装记录 + 写权记录 + 一份技能源。

    返回 dict：target / source / skill_root / args / writes / installation / writer。
    """
    import argparse
    import json

    target = os.path.join(root, "proj")
    source = os.path.join(root, "release")
    skill_root = os.path.join(target, f".{platform}/skills")
    os.makedirs(os.path.join(source, "skills/wf-start"), exist_ok=True)
    open(os.path.join(source, "skills/wf-start/SKILL.md"), "w").write("v1\n")
    os.makedirs(os.path.join(target, ".wf/install"), exist_ok=True)
    release_ref = release_ref or RELEASE_REF
    version = version or RELEASE_VERSION
    installation = {"schema_version": 1, "release_ref": release_ref,
                    "source_commit": source_commit, "version": version,
                    "rules_digest": rules_digest,
                    "platforms": list(installed_platforms), "roots": list(roots),
                    "assets": [{"target": ".wf/bin/wf.py", "root_ref": "project",
                                "digest": "sha256:x", "source_path": "bin/wf.py"}],
                    "decisions": [], "installed_at": "2026-11-05T00:00:00.000000Z",
                    "tool": "install.py"}
    with open(os.path.join(target, ".wf/install/installation.json"), "w") as handle:
        json.dump(installation, handle, ensure_ascii=False, indent=2)
    writer = {"schema_version": 1, "id": "writer", "revision": 0,
              "created_at": "2026-11-05T00:00:00.000000Z",
              "updated_at": "2026-11-05T00:00:00.000000Z",
              "write_mark": None, "action": None, "state": "idle", "generation": generation,
              "holder": None, "handover": None, "checkpoint": None, "maintenance_results": []}
    with open(os.path.join(target, ".wf/writer.json"), "w") as handle:
        json.dump(writer, handle, ensure_ascii=False, indent=2)
    args = argparse.Namespace(target=target, source=source, platform=[platform], confirm=True,
                              json=True, release_ref=release_ref)
    writes = [(skill_root, {"target_class": "skill_root", "source_path": "skills/wf-start/SKILL.md",
                            "digest": "sha256:y", "executable": False}, "wf-start/SKILL.md")]
    manifest = {"compatibility": {"rules_digest": rules_digest}, "assets": []}
    return {"target": target, "source": source, "skill_root": skill_root, "args": args,
            "writes": writes, "installation": installation, "writer": writer,
            "manifest": manifest}


def run_quietly(func, *args, **kwargs):
    """捕获 stdout，返回 (rc, 输出)。"""
    import contextlib
    import io

    buffer = io.StringIO()
    with contextlib.redirect_stdout(buffer):
        rc = func(*args, **kwargs)
    return rc, buffer.getvalue()

# SUT 驱动解释器：默认保持异解释器（与 full/wfdrive.PYTHON 同式同默认——两处字面量
# 必须一致，test_wfdrive_readonly 的常量断言守卫）。理由同 wfdrive.PYTHON 的注释：
# wflib/session.py 的 l2_anchor 跳过同解释器祖先，统一会把锚点推出 harness 之外。
WF_PYTHON = os.environ.get("WF_TEST_PYTHON") or "/usr/bin/python3"


_RELEASE_SRC = {}


def release_source(root):
    """把发行树复制成**自带 tag 的独立仓库**（2026-11-06：安装器改为按提交树核内容，
    因此源必须是一个包含这些路径的仓库根，不能用仓库内的子目录当前工作树冒充）。"""
    if root in _RELEASE_SRC:
        return _RELEASE_SRC[root]
    dest = os.path.join(root, "release-src")
    shutil.copytree(RELEASE, dest,
                    ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".git"))
    for cmd in (["git", "init", "-q"],
                ["git", "config", "user.email", "r@example.com"],
                ["git", "config", "user.name", "r"],
                ["git", "add", "-A"],
                ["git", "commit", "-qm", "release snapshot"],
                ["git", "tag", release_tag()]):
        subprocess.run(cmd, cwd=dest, check=True, capture_output=True)
    _RELEASE_SRC[root] = dest
    return dest


def deploy(root, platforms=("dsh",)):
    """用**真实发行树**部署一个最小项目，返回项目根（CLI 级用例需要真实部署）。"""
    project = os.path.join(root, "proj")
    os.makedirs(project, exist_ok=True)
    source = release_source(root)
    cmd = [sys.executable, os.path.join(source, "install.py"), "--target", project,
           "--release-ref", RELEASE_REF, "--source", source,
           "--confirm"]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise SystemExit(f"deploy failed: {(proc.stdout or proc.stderr)[-400:]}")
    for cmd in (["git", "init", "-q"], ["git", "config", "user.email", "r@example.com"],
                ["git", "config", "user.name", "r"], ["git", "add", "-A"],
                ["git", "commit", "-qm", "install", "--allow-empty"]):
        subprocess.run(cmd, cwd=project, check=True, capture_output=True)
    return project


def binding_instance(project, sid):
    """扮演宿主适配层：把持久绑定里的 instance_id 随会话携带（机制稿 §1.4）。"""
    import glob
    import json

    pattern = os.path.join(project, ".wf/session-bindings", "*.json")
    for path in glob.glob(pattern):
        try:
            with open(path, encoding="utf-8") as handle:
                data = json.load(handle)
        except (OSError, ValueError):
            continue
        value = (data.get("identity") or {}).get("value") or {}
        if value.get("session_id") == sid and data.get("instance_id"):
            return data["instance_id"]
    return None


def cli(project, args, sid="sess-R", inputs=None, instance_id=None, host_id="dsh",
        use_envelope=True):
    """跑项目内的 wf.py（真实 CLI），返回 (rc, 载荷)。"""
    import json

    if instance_id is None:
        instance_id = binding_instance(project, sid)

    envelope = {"session": {"provider": "host",
                            "identity": {"host_id": host_id, "session_id": sid},
                            "instance_id": instance_id,
                            "activation": {"enabled": True, "start_source": "human:repro",
                                           "enabled_at": "2026-11-05T00:00:00.000000Z"}},
                "inputs": inputs or {}}
    proc = subprocess.run([WF_PYTHON, os.path.join(project, ".wf/bin/wf.py")] + list(args),
                          input=(json.dumps(envelope, ensure_ascii=False) if use_envelope else ""),
                          capture_output=True, text=True)
    out = (proc.stdout or "").strip()
    try:
        payload = json.loads(out) if out.startswith("{") else None
    except ValueError:
        payload = None
    if payload is None:
        # 解析失败时不要把原因丢掉：调用方的 "failed: None" 无法归因（第十二轮复审 M-2）
        tail = (proc.stderr or "").strip()[-400:]
        raise Precondition(f"命令未返回 JSON：rc={proc.returncode} stdout={out[:120]!r} stderr={tail!r}")
    return proc.returncode, payload


def generation(project):
    import json

    with open(os.path.join(project, ".wf/writer.json"), encoding="utf-8") as handle:
        return json.load(handle).get("generation")

def ensure_project_config(project):
    """普通任务开工要求 `.wf/project-config.json`；用项目内 wflib 的骨架生成并提交。"""
    import json
    import uuid

    lib = os.path.join(project, ".wf/lib")
    if lib not in sys.path:
        sys.path.insert(0, lib)
    from wflib import config as wf_config

    payload = wf_config.skeleton()
    payload.setdefault("schema_version", 1)
    payload["project_id"] = uuid.uuid4().hex
    path = os.path.join(project, ".wf/project-config.json")
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
    # 开工前置：活基线必须存在（由 initialize 任务生成；这里给最小可用内容）
    baseline = ("# 活基线\n\n- 建立时间：2026-11-05\n- 范围：repro 夹具\n\n"
                "<!-- wf-governance:v1 -->\n```json\n"
                + json.dumps({"paths": [], "reason": "repro 夹具保持空治理面",
                              "decided_by": "human (repro)",
                              "decided_at": "2026-11-05T00:00:00.000000Z"},
                             ensure_ascii=False, indent=2)
                + "\n```\n")
    with open(os.path.join(project, ".wf/baseline.md"), "w", encoding="utf-8") as handle:
        handle.write(baseline)
    subprocess.run(["git", "add", "-A"], cwd=project, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-qm", "project config", "--allow-empty"],
                   cwd=project, check=True, capture_output=True)
