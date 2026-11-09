"""D21 执行器确认集合语义用例（`d21-executor-set-*.py`）共用脚手架。

确认集合写在用户目录（`~/.wf/interpreters.json`，见 wf.py `user_dir()`），
因此每条用例都把 `HOME` 隔离到本次夹具的临时目录，跑完恢复；
确认动作要求 TTY，用可替换 stdin 的伪终端在进程内完成（与第 27 轮审查
探针同一手法，明确不证明真人确认，只驱动实现走完整写入路径）。
"""
import contextlib
import importlib.util
import io
import json
import os
import shutil
import sys


class _Terminal(io.StringIO):
    def isatty(self):
        return True


def launcher(project):
    spec = importlib.util.spec_from_file_location("wfmod", os.path.join(project, ".wf/bin/wf.py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def set_executor(project, value):
    """写入项目键 python_executable，并把键名与配置值补进基线（project_key_approved 的证据面）。"""
    config_path = os.path.join(project, ".wf/project-config.json")
    config = json.load(open(config_path, encoding="utf-8"))
    config["python_executable"] = value
    json.dump(config, open(config_path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    with open(os.path.join(project, ".wf/baseline.md"), "a", encoding="utf-8") as handle:
        handle.write(f"\npython_executable = {value}\n")


def set_project_id(project, value):
    config_path = os.path.join(project, ".wf/project-config.json")
    config = json.load(open(config_path, encoding="utf-8"))
    config["project_id"] = value
    json.dump(config, open(config_path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)


def make_venv_python(project, relative=".venv/bin/python", mtime=None):
    """在项目内造一个可探测的『venv 解释器』：复制系统 python 并固定 mtime（可确定性重建）。"""
    path = os.path.join(project, relative)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    shutil.copy2("/usr/bin/python3", path)
    os.chmod(path, 0o755)
    if mtime is not None:
        os.utime(path, (mtime, mtime))
    return path


def confirm(module, project, scope="project"):
    """在进程内以伪终端跑 confirm-executor（输入 yes）。"""
    old = sys.stdin
    sys.stdin = _Terminal("yes\n")
    buffer = io.StringIO()
    try:
        with contextlib.redirect_stdout(buffer):
            rc = module.cmd_confirm_executor(project, ["--scope", scope])
    finally:
        sys.stdin = old
    if rc != 0:
        raise RuntimeError(f"confirm-executor 失败：{buffer.getvalue()[-300:]}")


def ready(module, project):
    scope, value, error = module.resolve_candidate(project)
    if error:
        raise RuntimeError(f"resolve_candidate 失败：{error}")
    candidate, path_error = module.candidate_path(project, value)
    if path_error:
        raise RuntimeError(f"candidate_path 失败：{path_error}")
    return module.executor_ready(project, scope, value, candidate)


class isolated_home:
    """把 HOME 指到临时目录（确认集合互不污染），退出时恢复。"""

    def __init__(self, root):
        self.home = os.path.join(root, "home")
        os.makedirs(self.home, exist_ok=True)
        self.previous = None

    def __enter__(self):
        self.previous = os.environ.get("HOME")
        os.environ["HOME"] = self.home
        return self.home

    def __exit__(self, *_exc):
        if self.previous is None:
            os.environ.pop("HOME", None)
        else:
            os.environ["HOME"] = self.previous
        return False
