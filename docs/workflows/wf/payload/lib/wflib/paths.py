"""paths.py — RepoPath 校验、glob 段匹配与可证包含（机制稿 §3.1、§3.4）。

只做结构与形状判定；不判断人的范围意图。
"""

from __future__ import annotations

import fnmatch
import os

WILDCARD_CHARS = ("*", "?", "[")


class InvalidPath(Exception):
    """非法 RepoPath / glob 条目（对应 WF_PATH_INVALID 的事实面）。"""


def _has_control(text: str) -> bool:
    return any(ord(ch) < 0x20 or ord(ch) == 0x7F for ch in text)


def _reject_shape(raw: str) -> None:
    if raw is None or raw == "":
        raise InvalidPath("empty path")
    if "\\" in raw:
        raise InvalidPath(f"backslash separator: {raw}")
    if _has_control(raw):
        raise InvalidPath(f"control character: {raw!r}")
    if raw.startswith("/") or (len(raw) > 1 and raw[1] == ":"):
        raise InvalidPath(f"absolute path: {raw}")
    if raw.split("/")[0] == "~":
        raise InvalidPath(f"home-relative path: {raw}")


def normalize(raw: str) -> str:
    """仓库相对路径规范化：消去 `.` 与重复分隔符，不改大小写/Unicode。"""
    _reject_shape(raw)
    parts = []
    for segment in raw.split("/"):
        if segment in ("", "."):
            continue
        if segment == "..":
            raise InvalidPath(f"parent segment: {raw}")
        parts.append(segment)
    if not parts:
        raise InvalidPath(f"empty path: {raw}")
    return "/".join(parts)


def validate_glob(pattern: str) -> str:
    """touch_paths / spec.paths 的条目校验与规范化。"""
    normalized = normalize(pattern)
    for segment in normalized.split("/"):
        if segment == ".":
            raise InvalidPath(f"dot segment: {pattern}")
    return normalized


def has_wild(segment: str) -> bool:
    return any(ch in segment for ch in WILDCARD_CHARS)


def seg_match(pattern: str, name: str) -> bool:
    """段内匹配：标准库 fnmatch 语义；`**` 未单独成段时按普通 `*` 处理。"""
    if pattern == "**":
        return True
    if not has_wild(pattern):
        return pattern == name
    return fnmatch.fnmatchcase(name, pattern)


def match_path(pattern: str, path: str):
    """pattern 是否匹配仓库相对 path；返回 (bool, 说明)。"""
    psegs = pattern.split("/")
    nsegs = path.split("/")
    return _match(psegs, nsegs)


def _match(psegs, nsegs) -> bool:
    if not psegs:
        return not nsegs
    head = psegs[0]
    if head == "**":
        for index in range(len(nsegs) + 1):
            if _match(psegs[1:], nsegs[index:]):
                return True
        return False
    if not nsegs:
        return False
    if not seg_match(head, nsegs[0]):
        return False
    return _match(psegs[1:], nsegs[1:])


def subsumes(p: str, g: str) -> bool:
    """可证包含 p ⊆ g（机制稿 §3.4 第 2 项唯一定义）。"""
    return _subsumes(p.split("/"), g.split("/"))


def _subsumes(psegs, gsegs) -> bool:
    if not gsegs:
        return not psegs
    g_head = gsegs[0]
    if g_head == "**":
        for count in range(len(psegs) + 1):
            if _subsumes(psegs[count:], gsegs[1:]):
                return True
        return False
    if not psegs:
        return False
    p_head = psegs[0]
    if p_head == "**":
        return g_head == "**" and _subsumes(psegs[1:], gsegs[1:])
    if has_wild(p_head):
        if not has_wild(g_head):
            return False
        return p_head == g_head and _subsumes(psegs[1:], gsegs[1:])
    if not seg_match(g_head, p_head):
        return False
    return _subsumes(psegs[1:], gsegs[1:])


def literal_prefix(pattern: str) -> list:
    """完整字面前缀段：遇首个含通配符的段（含整段 `**`）即停止。"""
    prefix = []
    for segment in pattern.split("/"):
        if segment == "**" or has_wild(segment):
            break
        prefix.append(segment)
    return prefix


def provably_disjoint(a: str, b: str) -> bool:
    """§8.5 的前缀规则：共有位置上出现不同字面段即可证明不相交。"""
    pa = literal_prefix(a)
    pb = literal_prefix(b)
    for left, right in zip(pa, pb):
        if left != right:
            return True
    return False


def join(root, rel: str):
    return os.path.join(str(root), *rel.split("/"))


def nested_repo_boundary(root, rel: str):
    """返回越界祖先（含 `.git` 的目录）路径；无越界返回 None。"""
    parts = rel.split("/")
    current = str(root)
    for segment in parts[:-1] if parts else []:
        current = os.path.join(current, segment)
        if not os.path.isdir(current):
            continue
        git_dir = os.path.join(current, ".git")
        if os.path.isdir(git_dir) or os.path.isfile(git_dir):
            return current
    return None


def nested_repo_boundary_real(root, rel: str):
    """按真实落点核对嵌套仓库边界：链接可能把目标带进项目内的嵌套仓库（设计稿 §6.1）。"""
    root_real = os.path.realpath(str(root))
    target_real = os.path.realpath(os.path.join(root_real, *rel.split("/")))
    if not (target_real == root_real or target_real.startswith(root_real + os.sep)):
        return None  # 越界由 realpath 包含性判定负责
    current = root_real
    for segment in os.path.relpath(target_real, root_real).split(os.sep)[:-1]:
        if segment in ("", "."):
            continue
        current = os.path.join(current, segment)
        if not os.path.isdir(current):
            continue
        git_dir = os.path.join(current, ".git")
        if os.path.isdir(git_dir) or os.path.isfile(git_dir):
            return current
    return None


def boundary_violation(root, rel: str):
    """统一边界判定：项目包含性 + 字面祖先 + 真实祖先的嵌套仓库检查（设计稿 §6.1）。

    返回 None 表示可用；否则返回原因字符串。读写入口共用这一份判据。
    """
    root_real = os.path.realpath(str(root))
    target_real = os.path.realpath(os.path.join(root_real, *rel.split("/")))
    if not (target_real == root_real or target_real.startswith(root_real + os.sep)):
        return "real path escapes the project root"
    nested = nested_repo_boundary(root, rel) or nested_repo_boundary_real(root, rel)
    if nested:
        return f"nested repository root: {nested}"
    return None


def real_root(root) -> str:
    return os.path.realpath(str(root))


def safe_write_target(root, rel: str) -> str:
    """核项目边界：目标或其最近存在祖先的真实位置必须仍在项目根内。"""
    root_real = real_root(root)
    target = join(root_real, normalize(rel))
    probe = target
    while not os.path.exists(probe):
        parent = os.path.dirname(probe)
        if parent == probe:
            break
        probe = parent
    probe_real = os.path.realpath(probe)
    if probe_real != root_real and not probe_real.startswith(root_real + os.sep):
        raise InvalidPath(f"escapes project root: {rel}")
    return target


def touch_path_errors(patterns, root=None):
    """批准/开工前的 touch_paths 检查；返回 [(pattern, reason)]。"""
    errors = []
    for pattern in patterns:
        try:
            normalized = validate_glob(pattern)
        except InvalidPath as exc:
            errors.append((pattern, str(exc)))
            continue
        if root is not None:
            violation = nested_repo_boundary(root, normalized)
            if violation:
                errors.append((pattern, f"nested repository root: {violation}"))
    return errors


def sorted_paths(paths):
    return sorted(set(paths), key=lambda item: item.encode("utf-8"))

# 允许经「基线/配置/spec」通道写入的路径白名单；控制记录一律不在其中（设计稿 §7.3）
WRITE_TARGET_CLASSES = (".wf/baseline.md", ".wf/project-config.json")
WRITE_TARGET_PREFIXES = (".wf/spec/",)


def write_target_allowed(normalized):
    """spec-update 与 baseline-apply 共用的目标类别判定，不各自另写判据。"""
    return normalized in WRITE_TARGET_CLASSES or normalized.startswith(WRITE_TARGET_PREFIXES)


def write_target_allowed_list():
    return list(WRITE_TARGET_CLASSES) + [f"{prefix}**" for prefix in WRITE_TARGET_PREFIXES]
