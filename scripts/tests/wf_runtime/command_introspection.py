"""委托型命令的"真实实现"定位（测试侧唯一实现）。

背景（2026-11-23，dogfood 五轮）：`cli.COMMANDS` 里大多数命令是闭包委托——
`_task_command("cmd_task_retrospect")` 生成的 handler 只用 `getattr(tasks_mod, name)`，
闭包里只含字符串，`inspect.getsource(handler)` 拿不到真正读参数的函数。于是
"帮助/注册表 ↔ handler 消费"的一致性断言对 20 余个命令**空跑**（`if not flags: continue`）。
本模块用 `__wf_target__`（`_task_command`）/`__wf_target_map__`（`_runs_command`）把
命令解析到真实模块函数，并补两类可达性：

1. **一层同模块助手**：真实函数把参数判断下沉到同模块私有助手时（如
   `runs.validate` → `_require_workflow_id(args)`、`cli.cmd_writer_handover` →
   `_handover_begin(ctx, args)`），跟随一层——不再要求每个命令都亲口读 flag；
2. **引导层**：`confirm-executor` / `upgrade` 在本层是转交桩，参数由 `.wf/bin/wf.py`
   真读；`EXTRA_SOURCES` 显式登记这些命令的补充来源（不做通用猜测）。

`FLAG_READ_RE` 之外的取值形态（拼装后的动态名）无法静态提取——调用方必须显式
allowlist 并写明理由，不允许把"提取不到"当成"没消费"。
"""

from __future__ import annotations

import inspect
import importlib
import re
from pathlib import Path

FLAG_READ_RE = re.compile(r"args\.(?:value|values|flag|required)\(\s*\"(--[a-z-]+)\"")
HELPER_CALL_RE = re.compile(r"\b(_[a-z0-9_]+)\(\s*(?:ctx,\s*)?args\b")
DYNAMIC_FLAG_RE = re.compile(r"args\.(?:value|values|flag|required)\(\s*[A-Za-z_]")

PAYLOAD = Path(__file__).resolve().parents[3] / "docs" / "workflows" / "wf" / "payload"

# 本层为转交桩、参数由引导层读取的命令（显式登记，不做通用猜测）。
EXTRA_SOURCES = {
    "confirm-executor": ["bin/wf.py"],
    "upgrade": ["bin/wf.py"],
}

# 参数不在 `args.value("--x")` 形态里被读取的命令——必须写明为什么提取不到，
# 不允许把"正则没命中"当成"没消费"（否则断言会被 allowlist 悄悄掏空）。
NON_STANDARD_READERS = {
    "confirm-executor": "参数由引导层 bin/wf.py 的 parse_scope(argv) 手解，不经 Args；"
                        "本层是 WF_CAPABILITY_UNAVAILABLE 转交桩",
    "upgrade": "参数由引导层 bin/wf.py 的 value_flags/布尔集手工转交 install.py，不经 Args",
}


def _resolve_target(handler, argv):
    """`command argv` → `(module_name, function_name)`；无法解析返回 None。"""
    target = getattr(handler, "__wf_target__", None)
    if target:
        module, _, func = target.partition(":")
        return module, func
    mapping = getattr(handler, "__wf_target_map__", None)
    if mapping:
        # 一个命令的旗标注册表是**全部子动作的并集**（dispatch 再按子命令收窄），
        # 所以消费集合也必须按并集看，不能只看示例里出现的那个子动作。
        sub = next((token for token in argv[1:] if not token.startswith("-")), None)
        target = mapping.get(sub) or next(iter(mapping.values()))
        module, _, func = target.partition(":")
        return module, func
    return None


def handler_sources(cli_module, command, argv=()):
    """该命令的**真实**源码片段列表（含一层助手与登记过的引导层来源）。"""
    handler = cli_module.COMMANDS.get(command)
    if handler is None:
        return []
    sources = []
    resolved = _resolve_target(handler, list(argv))
    if resolved:
        module_name, func_name = resolved
        module = importlib.import_module(f"wflib.{module_name}")
        func = getattr(module, func_name, None)
        if func is None:
            return []
        try:
            text = inspect.getsource(func)
        except (OSError, TypeError):
            return []
        sources.append(text)
        extra_funcs = [getattr(module, func_name, None)]
        mapping = getattr(handler, "__wf_target_map__", None)
        if mapping:
            extra_funcs = [getattr(module, name.partition(":")[2], None)
                           for name in mapping.values()]
        for func_obj in extra_funcs:
            if func_obj is None:
                continue
            try:
                text = inspect.getsource(func_obj)
            except (OSError, TypeError):
                continue
            if text not in sources:
                sources.append(text)
            for helper_name in sorted(set(HELPER_CALL_RE.findall(text))):
                helper = getattr(module, helper_name, None)
                if helper is None or not callable(helper):
                    continue
                try:
                    sources.append(inspect.getsource(helper))
                except (OSError, TypeError):
                    continue
    else:
        try:
            sources.append(inspect.getsource(handler))
        except (OSError, TypeError):
            pass
        for helper_name in sorted(set(HELPER_CALL_RE.findall(sources[0] if sources else ""))):
            helper = getattr(cli_module, helper_name, None)
            if helper is None or not callable(helper):
                continue
            try:
                sources.append(inspect.getsource(helper))
            except (OSError, TypeError):
                continue
    for relative in EXTRA_SOURCES.get(command, ()):
        path = PAYLOAD / relative
        try:
            sources.append(path.read_text(encoding="utf-8"))
        except OSError:
            continue
    return sources


def consumed_flags(cli_module, command, argv=()):
    """该命令真实实现静态消费的旗标集合 + 是否含无法静态提取的动态取值。"""
    flags = set()
    dynamic = False
    for text in handler_sources(cli_module, command, argv):
        flags |= set(FLAG_READ_RE.findall(text))
        if DYNAMIC_FLAG_RE.search(text):
            dynamic = True
    return flags, dynamic


def example_argv(cli_module, command):
    """帮助里的 `example` → 可直接 dispatch 的 argv（去掉 `wf.py` 前缀）。"""
    entry = cli_module.COMMAND_HELP.get(command) or {}
    tokens = [token for token in (entry.get("example") or "").split() if token != "wf.py"]
    return tokens or [command]