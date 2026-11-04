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
SOURCE_ROOT = os.path.join(REPO_ROOT, "docs", "workflows", "新项目开发工作流")
PAYLOAD = os.path.join(SOURCE_ROOT, "payload")
LIB_DIR = os.path.join(PAYLOAD, "lib")

GITIGNORE_MANAGED = {
    "begin_marker": "# wf-managed-v1",
    "end_marker": "# wf-managed-end",
    "lines": ["/.wf/.runtime/", "/.wf-lock"],
}

STEP_LINE = re.compile(
    r"^###\s+(?P<id>(?:task|control)\.[a-z][a-z0-9-]*(?:\.[a-z][a-z0-9-]*)*)\s+\[required\s+·\s+(?P<mode>once|repeatable)\]"
)
ENFORCEMENT_LINE = re.compile(r"^-\s+`?enforcement`?\s*[:：]\s*(?P<value>.+)$")

PROJECT_CLASSES = (
    ("payload/bin/", "project_wf", ".wf/bin/", "bin", True),
    ("payload/lib/wflib/", "project_wf", ".wf/lib/wflib/", "lib", False),
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
        entries.append(
            {
                "source_path": source_path,
                "target_class": target_class,
                "target_relative": target_relative,
                "kind": entry.get("kind") or kind,
                "required": bool(entry.get("required", True)),
                "file_kind": "file",
                "executable": bool(entry.get("executable", executable)),
                "digest": wf_records.file_digest(absolute),
            }
        )
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


def build_manifest(version, dev_manifest, source_root=SOURCE_ROOT):
    assets = expand_assets(dev_manifest, source_root)
    required_steps, problems = build_required_steps(source_root)
    if problems:
        raise ReleaseError("required_steps self-check failed:\n- " + "\n- ".join(problems))
    manifest = {
        "schema_version": 1,
        "version": version,
        "compatibility": compatibility_block(dev_manifest),
        "assets": assets,
        "required_steps": required_steps,
        "template_markers": build_template_markers(assets, source_root),
        "gitignore_managed": dict(GITIGNORE_MANAGED),
    }
    manifest["compatibility"]["rules_digest"] = wf_assets.compute_rules_digest(manifest)
    return manifest


def git_describe(repo=REPO_ROOT):
    try:
        result = subprocess.run(
            ["git", "describe", "--always", "--dirty", "--tags"],
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
            ["git", "rev-parse", "HEAD"],
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
