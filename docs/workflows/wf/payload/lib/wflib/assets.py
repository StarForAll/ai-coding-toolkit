"""assets.py — 清单读取、rules_digest 与三方比较入口（机制稿 §10.2、§10.4）。"""

from __future__ import annotations

import os
import subprocess

from . import records
from .paths import join

MANIFEST_REL = ".wf/install/release-manifest.json"
INSTALLATION_REL = ".wf/install/installation.json"
RECOVERY_REL = ".wf/install/recovery.md"


class AssetError(Exception):
    def __init__(self, message, code="WF_ASSET_DECISION"):
        super().__init__(message)
        self.code = code


class CapabilityUnavailable(Exception):
    """该轮次未交付的能力（WF_CAPABILITY_UNAVAILABLE）。"""

    def __init__(self, capability, round_no, facts=None):
        super().__init__(f"{capability} not delivered (round {round_no})")
        self.capability = capability
        self.round_no = round_no
        self.facts = facts or {}


def path_of(root, rel):
    return join(root, rel)


def load_installation(root):
    return records.load_json(path_of(root, INSTALLATION_REL), None)


def load_installed_manifest(root):
    """运行期清单的唯一读取入口；一致性不符按 WF_ASSET_DECISION 上报。"""
    manifest = records.load_json(path_of(root, MANIFEST_REL), None)
    if manifest is None:
        raise AssetError("installed manifest missing: .wf/install/release-manifest.json")
    installation = load_installation(root)
    if not isinstance(installation, dict):
        raise AssetError("installation record missing")
    expected = installation.get("manifest_digest")
    actual = records.file_digest(path_of(root, MANIFEST_REL))
    if expected != actual:
        raise AssetError(
            f"manifest_digest mismatch (recorded {expected}, actual {actual})",
        )
    return manifest


def _compat_without_rules(compatibility: dict) -> dict:
    return {key: value for key, value in (compatibility or {}).items() if key != "rules_digest"}


def compute_rules_digest(manifest: dict) -> str:
    assets = sorted(
        manifest.get("assets") or [],
        key=lambda entry: (
            entry.get("source_path", "").encode("utf-8"),
            entry.get("target_class", "").encode("utf-8"),
            (entry.get("target_relative") or "").encode("utf-8"),
        ),
    )
    steps = sorted(manifest.get("required_steps") or [], key=lambda entry: entry.get("id", "").encode("utf-8"))
    payload = {
        "schema_version": manifest.get("schema_version"),
        "compatibility_without_rules_digest": _compat_without_rules(manifest.get("compatibility")),
        "assets": assets,
        "required_steps": steps,
        "template_markers": manifest.get("template_markers"),
        "gitignore_managed": manifest.get("gitignore_managed"),
    }
    return records.H("wf-rules-v1", payload)


def installed_asset_entries(manifest: dict, installation: dict, root: str) -> list:
    """按安装登记与清单计算 installed_assets（§1.1 的排序与去重）。"""
    roots = (installation or {}).get("roots") or []
    resolved = [(item, item if os.path.isabs(item) else join(root, item)) for item in roots]
    entries = []
    for asset in manifest.get("assets") or []:
        target_class = asset.get("target_class")
        if target_class == "release_only":
            continue
        relative = asset.get("target_relative")
        if not relative:
            continue
        if target_class == "project_wf" or not resolved:
            # 项目内资产：只有项目根一份
            bases = [("project", root)]
        else:
            # skill 类资产：**每个**已登记根各算一项，任一副本改动都要反映到指纹上
            bases = list(resolved)
        for root_ref, base in bases:
            target = os.path.join(str(base), *relative.split("/"))
            exists = os.path.exists(target)
            entries.append(
                {
                    "root_ref": root_ref,
                    "target_relative": relative,
                    "kind": asset.get("kind"),
                    "executable": bool(asset.get("executable")),
                    "exists": exists,
                    "digest": records.file_digest(target) if exists else None,
                }
            )
    entries.sort(key=lambda entry: (entry["root_ref"].encode("utf-8"), entry["target_relative"].encode("utf-8")))
    deduped = []
    seen = set()
    for entry in entries:
        key = (entry["root_ref"], entry["target_relative"])
        if key in seen:
            continue
        seen.add(key)
        deduped.append(entry)
    return deduped


def effective_rule_version(manifest: dict, installed_entries) -> str:
    rules_digest = (manifest.get("compatibility") or {}).get("rules_digest") or compute_rules_digest(manifest)
    return records.H("wf-effective-rules-v1", {"rules_digest": rules_digest, "installed_assets": installed_entries})


def required_steps(manifest: dict) -> list:
    return list(manifest.get("required_steps") or [])


def manifest_assets(manifest: dict) -> list:
    return list(manifest.get("assets") or [])


def load_required_steps(root) -> list:
    return required_steps(load_installed_manifest(root))


def parse_release(*_args, **_kwargs):
    """第三轮交付：发行引用与清单解析。"""
    raise CapabilityUnavailable("release reference resolution (D22)", 3)


def compare(*_args, **_kwargs):
    """第三轮交付：三方比较的完整适用分支。"""
    raise CapabilityUnavailable("full asset compare matrix (D31/D33)", 3)


def git_ref_exists(root, ref: str):
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--verify", "--quiet", ref],
            cwd=str(root),
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError:
        return None
    return result.returncode == 0


def local_branches(root):
    try:
        result = subprocess.run(
            ["git", "for-each-ref", "--format=%(refname:short)", "refs/heads"],
            cwd=str(root),
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError:
        return []
    if result.returncode != 0:
        return []
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def branch_source_check(root, relative_paths) -> list:
    """只读核对：当前分支缺失但其他本地分支存在的路径（WF_ASSET_DECISION 事实面）。"""
    findings = []
    branches = local_branches(root)
    if not branches:
        return findings
    for path in relative_paths:
        if os.path.exists(join(root, path)):
            continue
        for branch in branches:
            try:
                result = subprocess.run(
                    ["git", "cat-file", "-e", f"{branch}:{path}"],
                    cwd=str(root),
                    capture_output=True,
                    text=True,
                    check=False,
                )
            except OSError:
                break
            if result.returncode == 0:
                findings.append({"path": path, "branch": branch})
                break
    return findings
