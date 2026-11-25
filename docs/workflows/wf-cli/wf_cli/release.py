"""Release resolution for the system-level wf command.

Two identities are deliberately separate:

* the **installed command version** (from package metadata / the release manifest) is used by
  ``wf install`` for a project that has no wf yet;
* ``wf upgrade`` resolves the **newest release tag on the registered default branch** and uses
  that release, so upgrading never depends on the operator naming a version or a local checkout.

The cache is a working copy of the registered source. A per-version git worktree provides the
release root; the release installer still verifies tag -> commit -> manifest -> asset hashes.
"""

from __future__ import annotations

import fcntl
import json
import os
import re
import shutil
import subprocess
import tempfile
import urllib.parse
from dataclasses import dataclass

from .version import VERSION_RE, require_release_version, tag_name

SOURCE_URL = os.environ.get("WF_GIT_URL") or "ssh://git@forgejo.xzc.com/xzc/ai-coding-toolkit.git"
RELEASE_SUBDIR = "docs/workflows/wf-release"
MANIFEST_REL = RELEASE_SUBDIR + "/wf-release.json"
INSTALLER_REL = RELEASE_SUBDIR + "/install.py"
TAG_PREFIX = "wf-v"


class ReleaseError(Exception):
    def __init__(self, code, message, facts=None, exit_hint=None, warnings=None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.facts = facts or {}
        self.exit_hint = exit_hint
        self.warnings = list(warnings or [])


@dataclass
class Release:
    version: str
    tag: str
    commit: str
    repo: str
    root: str | None = None

    def as_facts(self):
        facts = {"version": self.version, "tag": self.tag, "commit": self.commit}
        if self.root:
            facts["source"] = self.root
        return facts


def cache_home():
    xdg = os.environ.get("XDG_CACHE_HOME")
    base = xdg if xdg and os.path.isabs(xdg) else os.path.join(os.path.expanduser("~"), ".cache")
    path = os.path.join(base, "wf")
    try:
        os.makedirs(path, mode=0o700, exist_ok=True)
    except OSError as exc:
        raise ReleaseError("WF_CAPABILITY_UNAVAILABLE", "无法创建 wf 缓存目录",
                           {"path": path, "detail": str(exc)},
                           "核对 XDG_CACHE_HOME/HOME 的写权限后重试") from exc
    return path


class _CacheLock:
    def __init__(self):
        self.path = os.path.join(cache_home(), "cache.lock")
        self.fd = None

    def __enter__(self):
        try:
            self.fd = os.open(self.path, os.O_CREAT | os.O_RDWR, 0o600)
            fcntl.flock(self.fd, fcntl.LOCK_EX)
        except OSError as exc:
            if self.fd is not None:
                os.close(self.fd)
                self.fd = None
            raise ReleaseError("WF_CAPABILITY_UNAVAILABLE", "无法持有发行缓存锁",
                               {"path": self.path, "detail": str(exc)},
                               "核对缓存目录权限；不并行重试同一缓存") from exc
        return self

    def __exit__(self, *_exc):
        if self.fd is not None:
            try:
                fcntl.flock(self.fd, fcntl.LOCK_UN)
            finally:
                os.close(self.fd)
                self.fd = None


def _git(args, cwd=None, timeout=180):
    env = os.environ.copy()
    env.setdefault("GIT_TERMINAL_PROMPT", "0")
    env.setdefault("GIT_SSH_COMMAND", "ssh -o BatchMode=yes")
    try:
        result = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True,
                                timeout=timeout, env=env, check=False)
    except FileNotFoundError as exc:
        raise ReleaseError("WF_CAPABILITY_UNAVAILABLE", "系统没有 git，无法解析发行源",
                           {"detail": str(exc)}, "安装 git 后重试") from exc
    except subprocess.TimeoutExpired as exc:
        raise ReleaseError("WF_CAPABILITY_UNAVAILABLE", "git 操作超时",
                           {"command": ["git", *args], "timeout": timeout},
                           "核对 forgejo 网络/SSH 后重试；不把超时当成功") from exc
    return result


def _git_ok(args, cwd=None, timeout=180):
    result = _git(args, cwd=cwd, timeout=timeout)
    if result.returncode != 0:
        raise ReleaseError("WF_RELEASE_CONFLICT", "git 命令失败",
                           {"command": ["git", *args], "exit": result.returncode,
                            "stderr": (result.stderr or "").strip()[-800:]},
                           "核对登记发行源可达、tag 存在后重试")
    return (result.stdout or "").strip()


def _remove(path, base):
    real = os.path.realpath(path)
    if real != os.path.realpath(base) and not real.startswith(os.path.realpath(base) + os.sep):
        raise ReleaseError("WF_PATH_INVALID", "拒绝删除缓存目录外的路径", {"path": path},
                           "核对 XDG_CACHE_HOME/HOME 后重试")
    if os.path.islink(path):
        os.unlink(path)
        return
    if os.path.isdir(path):
        shutil.rmtree(path)
    elif os.path.exists(path):
        os.unlink(path)


def _is_git_worktree(path):
    if not os.path.isdir(path):
        return False
    result = _git(["rev-parse", "--is-inside-work-tree"], cwd=path)
    return result.returncode == 0 and (result.stdout or "").strip() == "true"


def _remote_matches(path, url):
    result = _git(["remote", "get-url", "origin"], cwd=path)
    return result.returncode == 0 and (result.stdout or "").strip() == url


def _ensure_source(url, fetch=True):
    base = cache_home()
    path = os.path.join(base, "source")
    if os.path.exists(path):
        if not _is_git_worktree(path) or not _remote_matches(path, url):
            _remove(path, base)
    if not os.path.exists(path):
        parent = os.path.dirname(path)
        temporary = tempfile.mkdtemp(prefix=".source-", dir=parent)
        try:
            _git_ok(["clone", "--quiet", url, temporary])
            os.replace(temporary, path)
        except Exception:
            shutil.rmtree(temporary, ignore_errors=True)
            raise
    if fetch:
        _git_ok(["fetch", "--quiet", "--prune", "--tags", "origin",
                 "+refs/heads/*:refs/remotes/origin/*"], cwd=path)
        _git(["remote", "set-head", "origin", "--auto"], cwd=path)
    return path


def _tag_commit(repo, tag):
    result = _git(["rev-parse", "--verify", f"refs/tags/{tag}^{{commit}}"], cwd=repo)
    if result.returncode != 0:
        return None
    return (result.stdout or "").strip() or None


def _tag_manifest(repo, tag):
    result = _git(["show", f"{tag}:{MANIFEST_REL}"], cwd=repo)
    if result.returncode != 0:
        raise ReleaseError("WF_RELEASE_CONFLICT", "发行 tag 缺少可解析的发行清单",
                           {"tag": tag, "manifest": MANIFEST_REL,
                            "stderr": (result.stderr or "").strip()[-800:]},
                           "该 tag 不是有效发行：按发行流程修正 tag，不手改缓存")
    try:
        manifest = json.loads(result.stdout)
    except ValueError as exc:
        raise ReleaseError("WF_RELEASE_CONFLICT", "发行清单不是合法 JSON",
                           {"tag": tag, "detail": str(exc)},
                           "该 tag 不是有效发行：按发行流程重建发行树并重新打 tag") from exc
    if not isinstance(manifest, dict):
        raise ReleaseError("WF_RELEASE_CONFLICT", "发行清单不是 JSON 对象", {"tag": tag},
                           "该 tag 不是有效发行：按发行流程重建发行树并重新打 tag")
    return manifest


def validate_tag(repo, tag, expected_version=None):
    match = re.match(r"^" + re.escape(TAG_PREFIX) + r"(\d+)\.(\d+)\.(\d+)$", tag or "")
    if not match:
        raise ReleaseError("WF_RELEASE_CONFLICT", "发行 tag 形态非法",
                           {"tag": tag, "expected": "wf-vX.Y.Z"},
                           "只扫描 wf-vX.Y.Z 形态的发行 tag")
    version = ".".join(match.groups())
    if expected_version is not None and version != expected_version:
        raise ReleaseError("WF_RELEASE_CONFLICT", "发行 tag 与请求版本不一致",
                           {"tag": tag, "requested": expected_version},
                           "核对系统 wf 版本与发行 tag；不把相邻版本当作目标")
    commit = _tag_commit(repo, tag)
    if not commit:
        raise ReleaseError("WF_RELEASE_CONFLICT", "发行 tag 无法解析到提交",
                           {"tag": tag}, "核对 forgejo 上该 tag 是否存在且指向发行提交")
    manifest = _tag_manifest(repo, tag)
    declared = str(manifest.get("version") or "")
    if declared != version:
        raise ReleaseError("WF_RELEASE_CONFLICT", "发行清单版本与 tag 不一致",
                           {"tag": tag, "tag_version": version, "manifest_version": declared},
                           "该 tag 不是有效发行：同版重建发行树并重新打 tag")
    install = _git(["cat-file", "-e", f"{tag}:{INSTALLER_REL}"], cwd=repo)
    if install.returncode != 0:
        raise ReleaseError("WF_RELEASE_CONFLICT", "发行 tag 缺少安装入口",
                           {"tag": tag, "path": INSTALLER_REL},
                           "该 tag 不是有效发行：核对发行树完整性")
    return Release(version=version, tag=tag, commit=commit, repo=repo)


def _default_ref(repo):
    result = _git(["symbolic-ref", "--quiet", "--short", "refs/remotes/origin/HEAD"], cwd=repo)
    if result.returncode == 0 and (result.stdout or "").strip():
        return (result.stdout or "").strip()
    for candidate in ("origin/main", "origin/master"):
        check = _git(["rev-parse", "--verify", candidate], cwd=repo)
        if check.returncode == 0:
            return candidate
    raise ReleaseError("WF_RELEASE_CONFLICT", "发行源没有可解析的默认分支",
                       {"source": repo},
                       "核对登记发行源与 origin/HEAD；不按任意 tag 猜最新发行")


def latest_release(url=None):
    """Newest valid release tag reachable from the default branch, ordered by creation date."""
    url = url or SOURCE_URL
    with _CacheLock():
        repo = _ensure_source(url)
        default_ref = _default_ref(repo)
        default_commit = _git_ok(["rev-parse", default_ref], cwd=repo)
        listing = _git_ok(["for-each-ref", f"--merged={default_commit}", "--sort=-creatordate",
                           "--format=%(refname:short)", "refs/tags/wf-v*"], cwd=repo)
        tags = [line.strip() for line in listing.splitlines() if line.strip()]
        tags = [tag for tag in tags if re.match(r"^wf-v\d+\.\d+\.\d+$", tag)]
        if not tags:
            raise ReleaseError("WF_RELEASE_CONFLICT", "默认分支上没有 wf-vX.Y.Z 发行 tag",
                               {"default_ref": default_ref},
                               "先在默认分支创建并推送发行 tag；升级只认默认分支上的发行 tag")
        newest = tags[0]
        release = validate_tag(repo, newest)
        return release


def _worktree_path(version):
    return os.path.join(cache_home(), "releases", require_release_version(version))


def _worktree_valid(path, repo, release):
    if not os.path.isdir(path):
        return False
    top = _git(["rev-parse", "--show-toplevel"], cwd=path)
    if top.returncode != 0 or os.path.realpath((top.stdout or "").strip()) != os.path.realpath(path):
        return False
    check = _git(["rev-parse", "HEAD"], cwd=path)
    if check.returncode != 0 or (check.stdout or "").strip() != release.commit:
        return False
    status = _git(["status", "--porcelain", "--", RELEASE_SUBDIR], cwd=path)
    if status.returncode != 0 or (status.stdout or "").strip():
        return False
    try:
        manifest = _tag_manifest(repo, release.tag)
    except ReleaseError:
        return False
    if str(manifest.get("version") or "") != release.version:
        return False
    return os.path.isfile(os.path.join(path, RELEASE_SUBDIR, "install.py"))


def ensure_release(version, repo=None, url=None):
    """Return the release root for ``version``; fetch/refresh the cache when needed."""
    require_release_version(version)
    url = url or SOURCE_URL
    with _CacheLock():
        if repo is None:
            repo = _ensure_source(url, fetch=False)
            if _tag_commit(repo, tag_name(version)) is None:
                repo = _ensure_source(url, fetch=True)
        release = validate_tag(repo, tag_name(version), expected_version=version)
        path = _worktree_path(version)
        if _worktree_valid(path, repo, release):
            return release.root if release.root else os.path.join(path, RELEASE_SUBDIR)
        if os.path.exists(path) or os.path.islink(path):
            _git(["worktree", "remove", "--force", path], cwd=repo)
            _remove(path, cache_home())
            _git(["worktree", "prune"], cwd=repo)
        os.makedirs(os.path.dirname(path), mode=0o700, exist_ok=True)
        _git_ok(["worktree", "add", "--quiet", "--detach", path, release.tag], cwd=repo)
        if not _worktree_valid(path, repo, release):
            raise ReleaseError("WF_RELEASE_CONFLICT", "发行 worktree 校验失败",
                               {"version": version, "path": path, "commit": release.commit},
                               "删除该版本缓存后重试；不把未校验的树当发行源")
        return os.path.join(path, RELEASE_SUBDIR)


def release_root_for(version):
    return os.path.join(_worktree_path(version), RELEASE_SUBDIR)


def release_info_for(version, repo=None, url=None):
    url = url or SOURCE_URL
    with _CacheLock():
        if repo is None:
            repo = _ensure_source(url, fetch=False)
            if _tag_commit(repo, tag_name(version)) is None:
                repo = _ensure_source(url, fetch=True)
        return validate_tag(repo, tag_name(version), expected_version=version)


def current_source_url():
    return SOURCE_URL

def _tag_blob(repo, tag, path):
    result = _git(["show", f"{tag}:{path}"], cwd=repo)
    if result.returncode != 0:
        raise ReleaseError("WF_RELEASE_CONFLICT", "发行 tag 缺少系统 wf 命令内容",
                           {"tag": tag, "path": path,
                            "stderr": (result.stderr or "").strip()[-800:]},
                           "该 tag 不是可安装的系统命令发行：核对发布附件与包目录")
    return result.stdout


def validate_cli_tag(repo, tag, version):
    """系统 wf 命令必须随同一发行 tag 交付，且版本动态解析到该 tag 的清单。"""
    import posixpath
    import tomllib

    try:
        data = tomllib.loads(_tag_blob(repo, tag, "docs/workflows/wf-cli/pyproject.toml"))
    except (ValueError, tomllib.TOMLDecodeError) as exc:
        raise ReleaseError("WF_RELEASE_CONFLICT", "wf-cli pyproject 不可解析",
                           {"tag": tag, "detail": str(exc)},
                           "该 tag 不是可安装的系统命令发行") from exc
    scripts = (data.get("project") or {}).get("scripts") or {}
    if scripts.get("wf") != "wf_cli.main:entry":
        raise ReleaseError("WF_RELEASE_CONFLICT", "wf-cli 入口声明缺失",
                           {"tag": tag, "scripts": scripts},
                           "该 tag 不是可安装的系统命令发行")
    tool = (data.get("tool") or {}).get("hatch", {}).get("version") or {}
    rel = tool.get("path")
    pattern = tool.get("pattern")
    if not rel or not pattern:
        raise ReleaseError("WF_RELEASE_CONFLICT", "wf-cli 版本未动态读取发行清单",
                           {"tag": tag, "tool": tool},
                           "该 tag 不是可安装的系统命令发行")
    target = posixpath.normpath("docs/workflows/wf-cli/" + rel)
    if not target.startswith(RELEASE_SUBDIR + "/"):
        raise ReleaseError("WF_RELEASE_CONFLICT", "wf-cli 版本路径未指向发行清单",
                           {"tag": tag, "path": rel, "resolved": target},
                           "该 tag 不是可安装的系统命令发行")
    text = _tag_blob(repo, tag, target)
    match = re.search(pattern, text)
    try:
        declared = match.group("version") if match else None
    except IndexError:
        declared = None
    if declared != version:
        raise ReleaseError("WF_RELEASE_CONFLICT", "wf-cli 版本与发行 tag 不一致",
                           {"tag": tag, "declared": declared, "version": version},
                           "该 tag 不是可安装的系统命令发行")
    _tag_blob(repo, tag, "docs/workflows/wf-cli/wf_cli/main.py")
    return True


def release_asset_url(version, base):
    """Standard release asset name for the system wf command wheel."""
    return f"{base.rstrip('/')}/releases/download/{tag_name(version)}/wf_cli-{version}-py3-none-any.whl"


def http_base(url=None):
    """Derive the Forgejo web/API base from the registered git source URL."""
    override = os.environ.get("WF_FORGEJO_BASE")
    if override:
        return override.rstrip("/")
    url = url or SOURCE_URL
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in ("ssh", "git+ssh"):
        return None
    host = parsed.hostname
    path = parsed.path.strip("/")
    if path.endswith(".git"):
        path = path[:-4]
    if not host or not path:
        return None
    return f"https://{host}/{path}"

