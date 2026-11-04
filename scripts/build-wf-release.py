#!/usr/bin/env python3
"""build-wf-release.py — 确定性打包与发行前自检（实现稿 §1.5、§4.4）。

authoring 工具，不进发行清单。产物：`docs/workflows/wf-release/`（清单 + install.py + wf-release/**）。
打包脚本不提交、不建 tag、不推送。
"""

from __future__ import annotations

import argparse
import filecmp
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import wf_release_common as common  # noqa: E402

DEV_VERSION_PLACEHOLDER = "0.0.0-dev"
from wflib import records as wf_records  # noqa: E402

RELEASE_ROOT = os.path.join(common.REPO_ROOT, "docs", "workflows", "wf-release")
PAYLOAD_TREE = os.path.join(RELEASE_ROOT, "wf-release")


class BuildError(Exception):
    pass


def release_source_path(source_path: str) -> str:
    if source_path == "payload/install.py":
        return "install.py"
    if source_path.startswith("payload/"):
        return "wf-release/" + source_path[len("payload/"):]
    if source_path.startswith("skills/"):
        return "wf-release/" + source_path
    raise BuildError(f"unmapped source path for release: {source_path}")


def copy_into(destination_root, release_path, absolute_source):
    destination = os.path.join(destination_root, *release_path.split("/"))
    os.makedirs(os.path.dirname(destination), exist_ok=True)
    shutil.copyfile(absolute_source, destination)
    os.chmod(destination, os.stat(absolute_source).st_mode)
    return destination


def _assert_version_consistency(dev_manifest, version):
    """版本只允许一处定义；dev-manifest 写了就必须与发行版本一致（否则 --verify 掩盖分叉）。"""
    declared = (dev_manifest or {}).get("version")
    if declared and declared == DEV_VERSION_PLACEHOLDER and declared != version:
        return      # dev-manifest 只放占位符：版本源唯一在 --version
    if declared and declared != version:
        raise SystemExit(f"version mismatch: dev-manifest={declared} release={version}")


def file_digest(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 16), b""):
            digest.update(chunk)
    return "sha256:" + digest.hexdigest()


def build(version, destination_root):
    dev_manifest = common.load_dev_manifest()
    _assert_version_consistency(dev_manifest, version)
    manifest = common.build_manifest(version, dev_manifest)

    declared = {entry["source_path"] for entry in dev_manifest.get("assets") or []}
    actual = set(common.source_tree_files())
    unlisted = sorted(actual - declared)
    missing = sorted(declared - actual)
    if unlisted:
        raise BuildError("source tree has unlisted files:\n- " + "\n- ".join(unlisted))
    if missing:
        raise BuildError("dev manifest declares missing files:\n- " + "\n- ".join(missing))

    os.makedirs(destination_root, exist_ok=True)
    rewritten = []
    for asset in manifest["assets"]:
        release_path = release_source_path(asset["source_path"])
        absolute = os.path.join(common.SOURCE_ROOT, *asset["source_path"].split("/"))
        copied = copy_into(destination_root, release_path, absolute)
        entry = dict(asset)
        entry["source_path"] = release_path
        entry["digest"] = wf_records.file_digest(copied)
        rewritten.append(entry)
    manifest["assets"] = rewritten
    from wflib import assets as wf_assets

    manifest["compatibility"]["rules_digest"] = wf_assets.compute_rules_digest(manifest)
    verify_rules_digest_parity(manifest)
    manifest_path = os.path.join(destination_root, "wf-release.json")
    wf_records.write_json(manifest_path, manifest)
    return manifest, manifest_path




def verify_rules_digest_parity(manifest):
    """install.py 自含一份 rules_digest 实现；打包时与运行时实现比对，防止分叉。"""
    import importlib.util

    from wflib import assets as wf_assets

    path = os.path.join(common.PAYLOAD, "install.py")
    spec = importlib.util.spec_from_file_location("wf_install_parity", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    theirs = module.compute_rules_digest(manifest)
    ours = wf_assets.compute_rules_digest(manifest)
    if theirs != ours:
        raise BuildError(f"rules_digest implementations diverge: install={theirs} runtime={ours}")
    return ours


def diff_tree(left, right):
    """逐文件 sha256 比对（dircmp 默认按 stat 判同，等长同 mtime 的差异会被漏掉）。"""
    problems = []
    left_files, right_files = {}, {}
    for base, dirs, files in os.walk(left):
        dirs[:] = [name for name in dirs if name != "__pycache__"]
        for name in files:
            path = os.path.join(base, name)
            left_files[os.path.relpath(path, left)] = path
    for base, dirs, files in os.walk(right):
        dirs[:] = [name for name in dirs if name != "__pycache__"]
        for name in files:
            path = os.path.join(base, name)
            right_files[os.path.relpath(path, right)] = path
    for relative, path in sorted(left_files.items()):
        if relative not in right_files:
            problems.append({"only_in_existing": path})
            continue
        try:
            same = file_digest(path) == file_digest(right_files[relative])
        except OSError as exc:
            problems.append({"unreadable": path, "error": str(exc)})
            continue
        if not same:
            problems.append({"differs": path})
    for relative, path in sorted(right_files.items()):
        if relative not in left_files:
            problems.append({"only_in_rebuild": path})
    return problems


def verify_byte_reproduction():
    if not os.path.isdir(RELEASE_ROOT):
        raise BuildError("no existing release tree to verify: docs/workflows/wf-release/")
    with open(os.path.join(RELEASE_ROOT, "wf-release.json"), "r", encoding="utf-8") as handle:
        existing = json.load(handle)
    version = existing.get("version")
    if not version:
        raise BuildError("existing wf-release.json has no version")
    temp_root = tempfile.mkdtemp(prefix="wf-release-verify-")
    try:
        rebuild_root = os.path.join(temp_root, "wf-release")
        manifest, _path = build(version, rebuild_root)
        problems = diff_tree(RELEASE_ROOT, rebuild_root)
        return version, problems, manifest
    finally:
        shutil.rmtree(temp_root, ignore_errors=True)


def verify_token_parity(nonce="0123456789abcdef0123456789abcdef"):
    outputs = {}
    for name in ("repair.py", "uninstall.py"):
        script = os.path.join(common.PAYLOAD, "bin", name)
        result = subprocess.run([sys.executable, script, "--token-parity-check", "--nonce", nonce],
                                capture_output=True, text=True, check=False)
        if result.returncode != 0:
            raise BuildError(f"{name} token parity check failed: {result.stderr.strip()}")
        outputs[name] = result.stdout.strip().splitlines()
    first = outputs["repair.py"]
    second = outputs["uninstall.py"]
    if first != second:
        raise BuildError("token parity mismatch:\n" + "\n".join(
            f"- repair: {a} | uninstall: {b}" for a, b in zip(first, second)) + (
            f"\n  length {len(first)} vs {len(second)}" if len(first) != len(second) else ""))
    if "first=ok" not in first or "after=expired" not in first:
        raise BuildError("token lifecycle assertion failed: " + " / ".join(first))
    return first


def print_summary(manifest, manifest_path):
    print(f"version: {manifest['version']}")
    print(f"assets: {len(manifest['assets'])}")
    print(f"required_steps: {len(manifest['required_steps'])}")
    print(f"template uses: {len(manifest['template_markers']['uses'])}")
    print(f"rules_digest: {manifest['compatibility']['rules_digest']}")
    print(f"manifest: {os.path.relpath(manifest_path, common.REPO_ROOT)}")
    print("hashes:")
    for asset in manifest["assets"]:
        print(f"  {asset['digest']}  {asset['source_path']}")


def main(argv=None):
    parser = argparse.ArgumentParser(description="wf 发行打包（authoring）")
    parser.add_argument("--version", default=None, help="0.x.y；与 tag wf-vX.Y.Z 一致")
    parser.add_argument("--verify", action="store_true", help="重建并与现有发行树字节比对")
    parser.add_argument("--verify-token-parity", action="store_true", help="比对 repair/uninstall 的令牌实现")
    args = parser.parse_args(argv)

    try:
        if args.verify_token_parity:
            lines = verify_token_parity()
            print("OK  token parity")
            for line in lines:
                print(f"  {line}")
        if args.verify:
            version, problems, manifest = verify_byte_reproduction()
            if problems:
                print("FAIL  byte reproduction differs:")
                for problem in problems[:40]:
                    print(f"  {problem}")
                return 1
            print(f"OK  byte reproduction ({version}, {len(manifest['assets'])} assets)")
        if args.version:
            if not args.version.count(".") == 2:
                print("FAIL  --version must be 0.x.y")
                return 1
            if os.path.isdir(RELEASE_ROOT):
                shutil.rmtree(RELEASE_ROOT)
            manifest, manifest_path = build(args.version, RELEASE_ROOT)
            print_summary(manifest, manifest_path)
            print("OK  release tree written（提交与 tag 由人执行）")
        if not (args.version or args.verify or args.verify_token_parity):
            parser.print_help()
            return 1
    except BuildError as exc:
        print(f"FAIL  {exc}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
