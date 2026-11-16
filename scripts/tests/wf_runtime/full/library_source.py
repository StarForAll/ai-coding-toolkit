#!/usr/bin/env python3
"""library_source.py — 测试库来源的唯一 resolver（candidate 禁止源码回退）。

规则（design §9）：

- **dev**：夹具项目 `.wf/lib` → `WF_TEST_LIB` → 作者 payload `lib`（仅 dev 回退）；
- **candidate**：只接受本次安装项目的 `.wf/lib` 或该证明明确声明的 `WF_TEST_LIB`
  发行输入；缺失/漂移非零拒绝，绝不自动退回作者 payload；
- 返回路径必须是含 `wflib/` 的目录；返回来源标签（installed/declared/source），
  供覆盖表与失败归因使用。

`wfdrive` 与 repro `_harness.test_lib()` 都委托本模块，禁止各自再写一套候选回退。
"""
from __future__ import annotations

import os
from pathlib import Path


class SourceError(Exception):
    """库来源缺失/漂移（不得静默回退）。"""


def repo_root():
    return Path(__file__).resolve().parents[4]


def payload_lib():
    return repo_root() / "docs" / "workflows" / "wf" / "payload" / "lib"


def _valid(path):
    if not path:
        return False
    return os.path.isdir(os.path.join(str(path), "wflib"))


def resolve(fixture=None, deploy=None, env=None):
    """Return (lib_path, source_label). Raise SourceError when no allowed source exists."""
    env = os.environ if env is None else env
    deploy = deploy or env.get("WF_FIXTURE_DEPLOY") or "dev"
    fixture = fixture or env.get("WF_FIX")
    declared = env.get("WF_TEST_LIB")
    installed = os.path.join(fixture, ".wf", "lib") if fixture else None
    if _valid(installed):
        return installed, "installed"
    if _valid(declared):
        return declared, "declared"
    if deploy == "candidate":
        raise SourceError(
            "candidate 部署没有已安装的 .wf/lib，也没有声明可见的 WF_TEST_LIB；"
            "candidate 禁止回退作者 payload 源码（请用安装产物或声明发行输入）")
    if _valid(payload_lib()):
        return str(payload_lib()), "source"
    raise SourceError(f"no usable wflib source (fixture={fixture!r}, declared={declared!r})")


def candidate_available(fixture=None, env=None):
    """候选模式是否已有安装库（覆盖表用；不抛异常）。"""
    try:
        resolve(fixture, "candidate", env)
        return True
    except SourceError:
        return False
