#!/usr/bin/env python3
"""wf_release_common.py — authoring 侧打包与开发态部署共用的同一份算法。

不是发行资产、不进发行清单（实现稿 §1.5）。`build-wf-release.py` 与
`wf-dev-deploy.py` 都从这里取同名的清单展开、模板标记与 rules_digest 计算。
"""

from __future__ import annotations

import os
import re
import subprocess
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SOURCE_ROOT = os.path.join(REPO_ROOT, "docs", "workflows", "wf")
PAYLOAD = os.path.join(SOURCE_ROOT, "payload")
LIB_DIR = os.path.join(PAYLOAD, "lib")

GITIGNORE_MANAGED = {
    "begin_marker": "# wf-managed-v1",
    "end_marker": "# wf-managed-end",
    # v42 S10 的五项：运行态与锁不进库（writer/绑定/缓存都是可丢弃重建的运行态）
    # 三轮补：.wf 内 Python 字节码是框架资产的派生文件（reviewer/dogfood 实测会把
    # .wf/lib 的 __pycache__ 当 vendor_dirty 噪声、扰动 control_plane_digest）——
    # 忽略集合唯一枚举仍是 gitignore_managed，派生文件按同一机制收口，只限 .wf/ 内。
    "lines": ["/.wf/.runtime/", "/.wf/session-bindings/", "/.wf/writer.json",
              "/.wf/.cache/", "/.wf-lock",
              "/.wf/**/__pycache__/", "/.wf/**/*.pyc"],
}

STEP_LINE = re.compile(
    r"^###\s+(?P<id>(?:task|control)\.[a-z][a-z0-9-]*(?:\.[a-z][a-z0-9-]*)*)\s+\[required\s+·\s+(?P<mode>once|repeatable)\]"
)
ENFORCEMENT_LINE = re.compile(r"^-\s+`?enforcement`?\s*[:：]\s*(?P<value>.+)$")

PROJECT_CLASSES = (
    ("payload/bin/", "project_wf", ".wf/bin/", "bin", True),
    ("payload/lib/wflib/", "project_wf", ".wf/lib/wflib/", "lib", False),
    ("payload/protocol/", "project_wf", ".wf/protocol/", "protocol", False),
    ("payload/workflows/", "project_wf", ".wf/workflows/", "workflow", False),
    ("payload/templates/", "project_wf", ".wf/templates/", "template", False),
)
SKILL_PREFIX = "skills/"


class ReleaseError(Exception):
    pass


def ensure_wflib():
    if LIB_DIR not in sys.path:
        sys.path.insert(0, LIB_DIR)
    import wflib  # noqa: F401

    return wflib


ensure_wflib()

from wflib import assets as wf_assets  # noqa: E402
from wflib import records as wf_records  # noqa: E402
from wflib import templates as wf_templates  # noqa: E402


def load_dev_manifest(source_root=SOURCE_ROOT):
    path = os.path.join(source_root, "dev-manifest.json")
    if not os.path.isfile(path):
        raise ReleaseError(f"dev-manifest.json missing: {path}")
    with open(path, "r", encoding="utf-8") as handle:
        import json

        manifest = json.load(handle)
    return manifest


def source_path_of(entry):
    path = entry.get("source_path") or entry.get("path")
    if not path:
        raise ReleaseError(f"asset entry without source_path: {entry}")
    return path


def target_of(source_path):
    """源路径 → (target_class, target_relative, kind, executable)。"""
    if source_path == "payload/install.py":
        return "release_only", None, "installer", True
    if source_path.startswith("payload/hooks/"):
        # W3-2（三轮 P0-1）：host-hook 资产——按 per-asset platform 投放声明平台
        # （目标名固定 wf-session-identity.py，命令串按该名登记所有权）。
        return "host_hook", ".codex/hooks/wf-session-identity.py", "hook", True
    for prefix, target_class, target_prefix, kind, executable in PROJECT_CLASSES:
        if source_path.startswith(prefix):
            relative = target_prefix + source_path[len(prefix):]
            return target_class, relative, kind, executable
    if source_path.startswith(SKILL_PREFIX):
        relative = source_path[len(SKILL_PREFIX):]
        if not relative.endswith("/SKILL.md"):
            raise ReleaseError(f"skill asset must be <name>/SKILL.md: {source_path}")
        return "skill_root", relative, "skill", False
    raise ReleaseError(f"unmapped source path: {source_path}")


def expand_assets(dev_manifest, source_root=SOURCE_ROOT):
    entries = []
    seen_sources = set()
    for entry in dev_manifest.get("assets") or []:
        source_path = source_path_of(entry)
        if source_path in seen_sources:
            raise ReleaseError(f"duplicate asset: {source_path}")
        seen_sources.add(source_path)
        absolute = os.path.join(source_root, *source_path.split("/"))
        if not os.path.isfile(absolute):
            raise ReleaseError(f"declared asset missing in source tree: {source_path}")
        target_class, target_relative, kind, executable = target_of(source_path)
        platform = entry.get("platform")
        # W3-2（三轮）：per-asset 平台条件——可选附加键，**仅 host_hook 类合法且必须**；
        # 须属安装器 --platform 声明集（安装器侧另核）。schema 版本不递增（可选键，
        # 对已知类的旧读取方不破坏；host_hook 类本身需新安装器，发行单元同源，见机制稿 §10.2）。
        if target_class == "host_hook":
            if not isinstance(platform, str) or not platform.strip():
                raise ReleaseError(f"host_hook asset requires a platform: {source_path}")
        elif platform is not None:
            raise ReleaseError(f"platform key only allowed on host_hook assets: {source_path}")
        item = {
            "source_path": source_path,
            "target_class": target_class,
            "target_relative": target_relative,
            "kind": entry.get("kind") or kind,
            "required": bool(entry.get("required", True)),
            "file_kind": "file",
            "executable": bool(entry.get("executable", executable)),
            "digest": wf_records.file_digest(absolute),
        }
        if platform is not None:
            item["platform"] = platform
        entries.append(item)
    entries.sort(key=lambda item: item["source_path"].encode("utf-8"))
    return entries


def source_tree_files(source_root=SOURCE_ROOT):
    """源树中应被登记的文件（用于「无未登记资产」核对）。"""
    found = []
    payload = os.path.join(source_root, "payload")
    for base, _dirs, files in os.walk(payload):
        for name in files:
            absolute = os.path.join(base, name)
            relative = os.path.relpath(absolute, source_root).replace(os.sep, "/")
            if relative.startswith("payload/__pycache__") or "/__pycache__/" in relative:
                continue
            found.append(relative)
    skills = os.path.join(source_root, "skills")
    if os.path.isdir(skills):
        for name in sorted(os.listdir(skills)):
            skill_file = os.path.join(skills, name, "SKILL.md")
            if os.path.isfile(skill_file):
                found.append(f"skills/{name}/SKILL.md")
    return sorted(found)


def parse_workflow_steps(source_root=SOURCE_ROOT):
    """解析流程文档的 `### <id> [required · once|repeatable]` 与 enforcement 行。"""
    directory = os.path.join(source_root, "payload", "workflows")
    steps = []
    if not os.path.isdir(directory):
        return steps
    for name in sorted(os.listdir(directory)):
        if not name.endswith(".md"):
            continue
        path = os.path.join(directory, name)
        with open(path, "r", encoding="utf-8") as handle:
            lines = handle.read().splitlines()
        current = None
        for line in lines:
            match = STEP_LINE.match(line)
            if match:
                current = {
                    "id": match.group("id"),
                    "mode": match.group("mode"),
                    "workflow_ref": f"wf-workflows/{name}#{match.group('id')}",
                    "enforcement": None,
                    "file": name,
                }
                steps.append(current)
                continue
            if line.startswith("### "):
                current = None
                continue
            if current and ENFORCEMENT_LINE.match(line):
                current["enforcement"] = ENFORCEMENT_LINE.match(line).group("value").strip()
    return steps


def build_required_steps(source_root=SOURCE_ROOT):
    """按固定声明表补 scope/applies/due；与流程文档双向核对。"""
    from wflib import gates

    specs = gates.required_step_specs()
    parsed = parse_workflow_steps(source_root)
    problems = []
    seen = {}
    for step in parsed:
        if step["id"] in seen:
            problems.append(f"duplicate required step id: {step['id']} ({seen[step['id']]} / {step['file']})")
            continue
        seen[step["id"]] = step["file"]
        if not step.get("enforcement"):
            problems.append(f"required step without enforcement line: {step['id']} ({step['file']})")
    for step_id in specs:
        if step_id not in seen:
            problems.append(f"declared step missing from workflow docs: {step_id}")
    for step_id in seen:
        if step_id not in specs:
            problems.append(f"workflow doc declares unregistered step id: {step_id}")
    entries = []
    for step in parsed:
        spec = specs.get(step["id"])
        if not spec:
            continue
        if spec["mode"] != step["mode"]:
            problems.append(f"mode mismatch for {step['id']}: doc={step['mode']} spec={spec['mode']}")
        entries.append(
            {
                "id": step["id"],
                "scope": spec["scope"],
                "workflow_ref": step["workflow_ref"],
                "mode": step["mode"],
                "applies": spec["applies"],
                "due": spec["due"],
                "delivery_round": spec["delivery_round"],
            }
        )
    if not parsed and not specs:
        problems = []
    return entries, problems


def build_template_markers(assets, source_root=SOURCE_ROOT):
    uses = []
    for asset in assets:
        target = asset.get("target_relative") or ""
        if asset.get("target_class") != "project_wf" or not target.startswith(".wf/templates/"):
            continue
        source = os.path.join(source_root, *asset["source_path"].split("/"))
        with open(source, "r", encoding="utf-8") as handle:
            text = handle.read()
        if source.endswith(".json"):
            import json

            try:
                value = json.loads(text)
            except ValueError:
                continue
            for pointer in wf_templates.find_value_markers(value):
                uses.append(
                    {
                        "template_path": target,
                        "selector": {"kind": "json_pointer", "value": pointer},
                        "format_id": "required-value",
                        "required": True,
                    }
                )
        else:
            for field, _offset in wf_templates.find_markers(text):
                uses.append(
                    {
                        "template_path": target,
                        "selector": {"kind": "markdown_marker", "value": f"{{{{WF_REQUIRED:{field}}}}}"},
                        "format_id": "required-field",
                        "required": True,
                    }
                )
    uses.sort(key=lambda item: (item["template_path"].encode("utf-8"), str(item["selector"]["value"]).encode("utf-8")))
    return {"formats": list(wf_templates.FORMATS), "uses": uses}


def compatibility_block(dev_manifest):
    return {
        "python_min": dev_manifest.get("python_min") or {"major": 3, "minor": 11},
        "systems": ["linux"],
        "filesystems": {
            "local_only": True,
            "advisory_flock_required": True,
            "network_or_sync_supported": False,
        },
        "record_versions": {
            key: {"read": [1], "write": 1}
            for key in (
                "task",
                "binding",
                "preparation",
                "run",
                "writer",
                "installation",
                "config",
                "spec",
            )
        },
        "workflow_versions": {"read": [1], "write": 1},
    }


def _helper_identity(role, invocation, python=None):
    """tool/SUT 身份（唯一解析点在 python_runtime_identity）——不序列化原始路径。"""
    scripts = os.path.dirname(os.path.abspath(__file__))
    if scripts not in sys.path:
        sys.path.insert(0, scripts)
    import python_runtime_identity as runtime_identity

    return runtime_identity.resolve(role, invocation, python)


def _content_manifest(paths):
    """相对路径序 + 逐文件字节摘要（必要文件缺失即报错，不签发 None）。"""
    entries = []
    for path in sorted(paths):
        if not os.path.isfile(path):
            raise ReleaseError(f"build input is missing: {path}")
        entries.append({"path": path, "digest": wf_records.file_digest(path)})
    return entries


def _canonical_digest(payload):
    import hashlib
    import json

    return "sha256:" + hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")).hexdigest()


# 协议/缓存 schema：改变输入形状时必须递增，否则旧 cache 会被当成同输入。
INPUT_PROTOCOL_SCHEMA = 2


def _scripts_root():
    return os.path.dirname(os.path.abspath(__file__))


def _build_tool_files():
    scripts = _scripts_root()
    return [
        os.path.join(scripts, "build-wf-release.py"),
        os.path.join(scripts, "wf_release_common.py"),
        os.path.join(scripts, "python_runtime_identity.py"),
        os.path.join(scripts, "wf-dev-deploy.py"),
        os.path.join(scripts, "tests", "wf_test_release.py"),
    ]


def test_release_inputs_digest(version, source_root=SOURCE_ROOT):
    """测试发行 build inputs：登记资产 + dev-manifest + build/helper 工具 + tool 身份 + 版本/schema。

    同一内容稳定；任何工具或资产字节变化（含 dirty 工作区）都改变身份。dev HEAD **不**进本函数
    ——HEAD 属于模板身份（`fixture_template_inputs_digest`），发行内容本身与提交无关。
    """
    manifest_path = os.path.join(source_root, "dev-manifest.json")
    dev_manifest = load_dev_manifest(source_root)
    assets = [{"path": entry["source_path"], "digest": entry["digest"], "kind": entry["kind"]}
              for entry in expand_assets(dev_manifest, source_root)]
    helper = _helper_identity("tool", os.path.join(_scripts_root(), "tests", "wf_test_release.py"))
    payload = {
        "schema": INPUT_PROTOCOL_SCHEMA,
        "kind": "test-release",
        "version": version,
        "assets": assets,
        "dev_manifest": wf_records.file_digest(manifest_path),
        "tools": _content_manifest(_build_tool_files()),
        "tool_identity": helper,
    }
    return _canonical_digest(payload)


def full_runner_files(full_root=None):
    """受控 full runner 子树（模板输入；测试脚本变化也可能重建模板，代价有意接受）。"""
    root = full_root or os.path.join(_scripts_root(), "tests", "wf_runtime", "full")
    found = []
    for base, dirs, names in os.walk(root):
        dirs[:] = sorted(name for name in dirs if name != "__pycache__")
        for name in sorted(names):
            if name.endswith(".pyc") or name in ("groups.json",):
                continue
            absolute = os.path.join(base, name)
            found.append(os.path.join(root, absolute[len(root) + 1:]))
    return found


def fixture_template_inputs_digest(deploy, version=None, ref=None, release_subject_digest=None,
                                   source_root=SOURCE_ROOT, candidate_commit=None):
    """模板 build inputs：发行 build inputs + full 子树 + 部署/运行时 helper + tool/SUT 身份。

    dev 另绑定完整 HEAD；candidate 另绑定实际 release subject。两者都用同一批观测构造，
    不把 deploy 标签当内容证据。
    """
    scripts = _scripts_root()
    full_root = os.path.join(scripts, "tests", "wf_runtime", "full")
    tool = _helper_identity("tool", os.path.join(scripts, "tests", "wf_test_release.py"))
    sut = _helper_identity("sut", os.path.join(full_root, "f1_init.py"))
    payload = {
        "schema": INPUT_PROTOCOL_SCHEMA,
        "kind": "fixture-template",
        "deploy": deploy,
        "release_inputs": test_release_inputs_digest(version or "", source_root),
        "full_runner": _content_manifest(full_runner_files(full_root)),
        "runtime_helpers": _content_manifest([
            os.path.join(scripts, "python_runtime_identity.py"),
            os.path.join(scripts, "wf-dev-deploy.py"),
            os.path.join(full_root, "fixture_scope.py"),
            os.path.join(full_root, "template_check.py"),
        ]),
        "tool_identity": tool,
        "sut_identity": sut,
    }
    if deploy == "dev":
        payload["dev_head"] = git_head() or ""
    else:
        # 候选模板身份 = 内容主体 + 已核 tag commit：同内容不同提交必须是不同条目，
        # 否则 B 的首跑会命中 A 的模板并用 A 的 source_commit 安装。
        payload["candidate"] = {"version": version or "", "ref": ref or "",
                                "release_subject": release_subject_digest or "",
                                "commit": candidate_commit or ""}
    return _canonical_digest(payload)


def release_subject(tree, version, ref, source_root=SOURCE_ROOT):
    """实际发行内容主体：tree 内容摘要 + manifest 摘要 + version/ref（排除 .git/pyc）。"""
    manifest_path = os.path.join(tree, "wf-release.json")
    if not os.path.isfile(manifest_path):
        raise ReleaseError(f"release manifest is missing: {manifest_path}")
    import json

    with open(manifest_path, "r", encoding="utf-8") as handle:
        manifest = json.load(handle)
    payload = {
        "tree": tree_digest(tree),
        "manifest": manifest_digest(manifest),
        "version": version,
        "ref": ref,
    }
    return {"subject": payload, "digest": _canonical_digest(payload)}


def _encode_part(value):
    import base64

    return base64.urlsafe_b64encode(value.encode("utf-8")).decode("ascii").rstrip("=") or "x"


def template_cache_slot(py_version, deploy, version=None, ref=None):
    """槽位：Python major.minor + deploy；candidate 再加 version/ref。

    每段用 urlsafe-base64 编码（可逆、无分隔符碰撞），不靠简单 sanitize。
    """
    if deploy not in ("dev", "candidate"):
        raise ReleaseError(f"unknown deploy: {deploy!r}")
    parts = [f"py{py_version}", deploy]
    if deploy == "candidate":
        parts += [version or "", ref or ""]
    return "-".join(_encode_part(part) for part in parts)


def template_cache_key(inputs_digest, py_version, deploy, version=None, ref=None):
    """交叉 run 模板条目的目录名：内容身份前 12 位 + 槽位。"""
    if not inputs_digest.startswith("sha256:") or len(inputs_digest) != 71:
        raise ReleaseError(f"inputs digest must be sha256: {inputs_digest!r}")
    return inputs_digest[7:19] + "-" + template_cache_slot(py_version, deploy, version, ref)


def tree_digest(root):
    """目录树摘要（相对路径序 + 逐文件 sha256；跳过 `.git`/`__pycache__`）。

    用于“这棵发行树在测试前后有没有被改动”和“候选仓库是否由当前候选树构建”。
    """
    import hashlib

    digest = hashlib.sha256()
    files = []
    for base, dirs, names in os.walk(root):
        dirs[:] = sorted(name for name in dirs if name not in (".git", "__pycache__"))
        for name in names:
            if name.endswith(".pyc"):
                continue
            path = os.path.join(base, name)
            files.append(os.path.relpath(path, root).replace(os.sep, "/"))
    for relative in sorted(files):
        digest.update(relative.encode("utf-8"))
        digest.update(b"\x00")
        digest.update(wf_records.file_digest(os.path.join(root, *relative.split("/"))).encode("ascii"))
        digest.update(b"\n")
    return "sha256:" + digest.hexdigest()


def source_tree_digest(source_root=SOURCE_ROOT):
    """源树摘要：按 `source_tree_files` 的登记文件逐字节算，路径序固定，不看 mtime。

    与 `build_manifest` 同源（同一份枚举 + 同一份 sha256），因此可以用它判断
    “测试发行副本是否由当前源树构建”。
    """
    import hashlib

    digest = hashlib.sha256()
    for relative in source_tree_files(source_root):
        absolute = os.path.join(source_root, *relative.split("/"))
        digest.update(relative.encode("utf-8"))
        digest.update(b"\x00")
        digest.update(wf_records.file_digest(absolute).encode("ascii"))
        digest.update(b"\n")
    return "sha256:" + digest.hexdigest()


def manifest_digest(manifest):
    """清单摘要：规范化 JSON（排序键、无空白）的 sha256。"""
    import hashlib
    import json

    canonical = json.dumps(manifest, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return "sha256:" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def build_manifest(version, dev_manifest, source_root=SOURCE_ROOT):
    from wflib import gates

    assets = expand_assets(dev_manifest, source_root)
    required_steps, problems = build_required_steps(source_root)
    if problems:
        raise ReleaseError("required_steps self-check failed:\n- " + "\n- ".join(problems))
    manifest = {
        "schema_version": 1,
        "version": version,
        # 交付轮次（2026-11-05 人裁 B）：安装自检按"清单声明的当前交付集"判可达；
        # 每步的交付轮次落在 required_steps 条目内并因此进入 rules_digest，
        # 本顶层字段只表达"这份清单交付到第几轮"，不参与摘要（改它必伴随步骤变化或版本递增）。
        "delivery_round": gates.CURRENT_DELIVERY_ROUND,
        "compatibility": compatibility_block(dev_manifest),
        "assets": assets,
        "required_steps": required_steps,
        "template_markers": build_template_markers(assets, source_root),
        "gitignore_managed": dict(GITIGNORE_MANAGED),
    }
    manifest["compatibility"]["rules_digest"] = wf_assets.compute_rules_digest(manifest)
    return manifest


def git_bin():
    """Git 可执行入口：默认 `git`；`WF_GIT_BIN` 只给测试注入失败/计数 shim（不改语义）。"""
    return os.environ.get("WF_GIT_BIN") or "git"


def git_describe(repo=REPO_ROOT):
    try:
        result = subprocess.run(
            [git_bin(), "describe", "--always", "--dirty", "--tags"],
            cwd=repo,
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError:
        return None
    if result.returncode != 0:
        return None
    return result.stdout.strip() or None


def git_head(repo=REPO_ROOT):
    try:
        result = subprocess.run(
            [git_bin(), "rev-parse", "HEAD"],
            cwd=repo,
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError:
        return None
    if result.returncode != 0:
        return None
    return result.stdout.strip() or None


def write_manifest(path, manifest):
    wf_records.write_json(path, manifest)
    return wf_records.file_digest(path)
