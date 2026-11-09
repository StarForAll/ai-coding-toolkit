#!/usr/bin/env python3
"""wf-protocol-docs.py — 从 `protocol/` 生成文档片段，并反向核对上位文档的机器事实。

authoring 工具，不进发行清单（v42 P0：纪律 #4「单一事实源」与不变量⑤）。

两种用法：
  wf-protocol-docs.py                 # 渲染文档片段到 stdout（码表/状态转移/阈值/阶段句）
  wf-protocol-docs.py --check         # 反向核对机制稿 §2.2/§8.1/§11.1 与设计稿 §1.3/§4.1
  wf-protocol-docs.py --out <dir>     # 把片段写进目录（四份 .md）

`--check` 只读上位文档，不改写它们：改写 charter/设计稿/机制稿属 T7 人审动作。
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SOURCE_ROOT = REPO_ROOT / "docs" / "workflows" / "新项目开发工作流"
PROTOCOL_DIR = SOURCE_ROOT / "payload" / "protocol"
MECHANISM = REPO_ROOT / "docs" / "workflows" / "wf-framework-mechanism.md"
DESIGN = REPO_ROOT / "docs" / "workflows" / "wf-framework-design.md"

sys.path.insert(0, str(SOURCE_ROOT / "payload" / "lib"))

CODE_ROW = re.compile(r"^\|\s*`(?P<code>WF_[A-Z_]+)`\s*\|\s*(?P<tier>[a-z_]+)\s*\|")
CONFIG_ROW = re.compile(r"^\|\s*(?P<keys>[^|]+?)\s*\|\s*(?P<types>[^|]+?)\s*\|\s*(?P<consumer>[^|]+?)\s*\|")
PHASE_SENTENCE = re.compile(r"phase 对应\s*(?P<phases>[A-Za-z]+(?:/[A-Za-z]+)*)")
INITIAL_SENTENCE = re.compile(r"初始为\s*(?P<status>[a-z_]+)/(?P<phase>[a-z]+)")
STATUS_SENTENCE = re.compile(r"status 的编码对应\s*(?P<labels>[^；;。]+)")


def _read(path):
    return Path(path).read_text(encoding="utf-8")


def _sections(text, pattern):
    """按二级/三级标题切段：返回 [(标题行, 正文行列表)]。"""
    blocks = []
    current = None
    for line in text.splitlines():
        if re.match(pattern, line):
            current = (line, [])
            blocks.append(current)
            continue
        if current is not None:
            current[1].append(line)
    return blocks


def _load_protocol():
    payload = {}
    for name in ("states", "codes", "thresholds", "redaction"):
        payload[name] = json.loads((PROTOCOL_DIR / f"{name}.json").read_text(encoding="utf-8"))
    return payload


# --------------------------------------------------------------------------
# 渲染
# --------------------------------------------------------------------------


def render_codes(protocol):
    lines = [
        "<!-- generated from protocol/codes.json；不要手改 -->",
        "",
        "| 原因码 | 档位 | 出口 | 禁止的错误修复 |",
        "|---|---|---|---|",
    ]
    for name in sorted(protocol["codes"]["codes"]):
        entry = protocol["codes"]["codes"][name]
        prohibited = entry.get("prohibited_repairs") or "—"
        lines.append(f"| `{name}` | {entry['tier']} | {entry['exit']} | {prohibited} |")
    return "\n".join(lines) + "\n"


def render_states(protocol):
    states = protocol["states"]
    lines = [
        "<!-- generated from protocol/states.json；不要手改 -->",
        "",
        states["phase_model"],
        "",
        f"- status：{'、'.join(f'`{item}`' for item in states['status']['enum'])}",
        f"- phase：{' → '.join(f'`{item}`' for item in states['phase']['enum'])}",
        f"- 执行候选：{states['execution_candidate']}",
        "",
        "| 动作 | 源 | 目标 | 失败码 |",
        "|---|---|---|---|",
    ]
    for entry in states["transitions"]:
        source = "、".join(_position_text(item) for item in entry.get("from") or []) or "—"
        target = "、".join(_position_text(item) for item in entry.get("to") or []) or "（位置不变）"
        codes = "、".join(f"`{code}`" for code in entry.get("fail_codes") or []) or "—"
        lines.append(f"| `{entry['action']}`（{entry['id']}） | {source} | {target} | {codes} |")
    return "\n".join(lines) + "\n"


def _position_text(position):
    status = position.get("status")
    phase = position.get("phase")
    terminal = position.get("terminal")
    text = f"{status}/{phase}" if phase else str(status)
    if terminal:
        text += f"（terminal={terminal}）"
    return text


def render_thresholds(protocol):
    lines = [
        "<!-- generated from protocol/thresholds.json；不要手改 -->",
        "",
        "| 键 | 类型 | 缺省 | 消费 |",
        "|---|---|---|---|",
    ]
    for name, entry in protocol["thresholds"]["keys"].items():
        default = entry.get("default")
        shown = "（生成）" if entry.get("generated") else ("（未设置）" if default is None else json.dumps(default))
        lines.append(f"| `{name}` | {entry['type']} | {shown} | {entry['consumer']} |")
    return "\n".join(lines) + "\n"


def render_redaction(protocol):
    redaction = protocol["redaction"]
    lines = [
        "<!-- generated from protocol/redaction.json；不要手改 -->",
        "",
        f"方向：`{redaction['direction']}`（只可加严，放松须按改不变量走人审）",
        "",
        "| 规则 | 作用 | 范围 | 项 |",
        "|---|---|---|---|",
    ]
    for rule in redaction["rules"]:
        items = "、".join(rule.get("items") or [])
        lines.append(f"| `{rule['id']}` | {rule['effect']} | {rule['scope']} | {items} |")
    return "\n".join(lines) + "\n"


RENDERERS = {
    "codes.md": render_codes,
    "states.md": render_states,
    "thresholds.md": render_thresholds,
    "redaction.md": render_redaction,
}


# --------------------------------------------------------------------------
# 反向核对
# --------------------------------------------------------------------------


def check_codes(protocol, mechanism):
    problems = []
    blocks = _sections(mechanism, r"^### 11\.1 ")
    if not blocks:
        return [{"doc": "mechanism", "section": "11.1", "problem": "section not found"}]
    declared = {}
    for line in blocks[0][1]:
        match = CODE_ROW.match(line)
        if match:
            declared[match.group("code")] = match.group("tier")
    if not declared:
        return [{"doc": "mechanism", "section": "11.1", "problem": "code table not parsed"}]
    actual = {name: entry["tier"] for name, entry in protocol["codes"]["codes"].items()}
    for name in sorted(set(declared) | set(actual)):
        if name not in actual:
            problems.append({"doc": "mechanism", "section": "11.1", "problem": "code missing in protocol", "code": name})
        elif name not in declared:
            problems.append({"doc": "mechanism", "section": "11.1", "problem": "code missing in doc", "code": name})
        elif declared[name] != actual[name]:
            problems.append({"doc": "mechanism", "section": "11.1", "problem": "tier mismatch", "code": name,
                             "doc": declared[name], "protocol": actual[name]})
    return problems


def _parse_default(cell):
    """把机制稿 §8.1 的「类型/缺省」单元解析成 [{kind, default, values}]（支持 `a、b` 合并行）。"""
    entries = []
    kind = None
    for part in [item.strip() for item in cell.split("、") if item.strip()]:
        if part.startswith("正整数"):
            kind = "positive_int"
        elif part.startswith("布尔"):
            kind = "bool"
        elif part.startswith("整数"):
            kind = "int_zero_unbounded"
        elif part.startswith("可选路径"):
            kind = "optional_path"
        elif part.startswith("UUID4"):
            kind = "uuid4_hex"
        elif part.startswith("枚举"):
            kind = "enum"
        entry = {"kind": kind, "default": None, "values": None}
        if kind == "bool":
            entry["default"] = "true" in part
        elif kind in ("positive_int", "int_zero_unbounded"):
            match = re.search(r"(-?\d+)", part)
            entry["default"] = int(match.group(1)) if match else None
        elif kind == "enum":
            values = re.search(r"([A-Za-z0-9]+(?:/[A-Za-z0-9]+)+)", part)
            entry["values"] = values.group(1).split("/") if values else None
            default = re.search(r"缺省\s*([A-Za-z0-9]+)", part)
            entry["default"] = default.group(1) if default else None
        entries.append(entry)
    return entries


def check_thresholds(protocol, mechanism):
    problems = []
    blocks = _sections(mechanism, r"^### 8\.1 ")
    if not blocks:
        return [{"doc": "mechanism", "section": "8.1", "problem": "section not found"}]
    declared = {}
    for line in blocks[0][1]:
        match = CONFIG_ROW.match(line)
        if not match:
            continue
        keys = re.findall(r"`([a-z_]+)`", match.group("keys"))
        if not keys:
            continue
        types = _parse_default(match.group("types"))
        if len(keys) != len(types):
            problems.append({"doc": "mechanism", "section": "8.1", "problem": "row arity mismatch",
                             "keys": keys, "types": types})
            continue
        for key, entry in zip(keys, types):
            declared[key] = entry
    if not declared:
        return [{"doc": "mechanism", "section": "8.1", "problem": "config table not parsed"}]
    actual = protocol["thresholds"]["keys"]
    for name in sorted(set(declared) | set(actual)):
        if name not in actual:
            problems.append({"doc": "mechanism", "section": "8.1", "problem": "key missing in protocol", "key": name})
            continue
        if name not in declared:
            problems.append({"doc": "mechanism", "section": "8.1", "problem": "key missing in doc", "key": name})
            continue
        entry = declared[name]
        kind = entry["kind"]
        if kind is None:
            problems.append({"doc": "mechanism", "section": "8.1", "problem": "row type unparsed", "key": name})
            continue
        if kind != actual[name].get("type"):
            problems.append({"doc": "mechanism", "section": "8.1", "problem": "type mismatch", "key": name,
                             "doc": kind, "protocol": actual[name].get("type")})
        if entry["default"] != actual[name].get("default"):
            problems.append({"doc": "mechanism", "section": "8.1", "problem": "default mismatch", "key": name,
                             "doc": entry["default"], "protocol": actual[name].get("default")})
        if kind == "enum" and entry["values"] != actual[name].get("values"):
            problems.append({"doc": "mechanism", "section": "8.1", "problem": "enum values mismatch", "key": name,
                             "doc": entry["values"], "protocol": actual[name].get("values")})
    return problems


def check_states(protocol, mechanism, design):
    problems = []
    states = protocol["states"]
    blocks = _sections(mechanism, r"^### 2\.2 ")
    if not blocks:
        return [{"doc": "mechanism", "section": "2.2", "problem": "section not found"}]
    body = "\n".join(blocks[0][1])
    match = PHASE_SENTENCE.search(body)
    if not match:
        problems.append({"doc": "mechanism", "section": "2.2", "problem": "phase sentence not parsed"})
    else:
        doc_phases = [item.strip().lower() for item in match.group("phases").split("/")]
        if doc_phases != list(states["phase"]["enum"]):
            problems.append({"doc": "mechanism", "section": "2.2", "problem": "phase enum mismatch",
                             "doc": doc_phases, "protocol": list(states["phase"]["enum"])})
    match = INITIAL_SENTENCE.search(body)
    if not match:
        problems.append({"doc": "mechanism", "section": "2.2", "problem": "initial position not parsed"})
    else:
        if match.group("status") != states["status"]["initial"]:
            problems.append({"doc": "mechanism", "section": "2.2", "problem": "initial status mismatch",
                             "doc": match.group("status"), "protocol": states["status"]["initial"]})
        if match.group("phase") != states["phase"]["initial"]:
            problems.append({"doc": "mechanism", "section": "2.2", "problem": "initial phase mismatch",
                             "doc": match.group("phase"), "protocol": states["phase"]["initial"]})
    match = STATUS_SENTENCE.search(body)
    if not match:
        problems.append({"doc": "mechanism", "section": "2.2", "problem": "status sentence not parsed"})
    else:
        doc_labels = [item.strip() for item in match.group("labels").split("、") if item.strip()]
        protocol_labels = [states["status"]["display"][item] for item in states["status"]["enum"]]
        if doc_labels != protocol_labels:
            problems.append({"doc": "mechanism", "section": "2.2", "problem": "status display mismatch",
                             "doc": doc_labels, "protocol": protocol_labels})

    expected = "Plan → Execute → Check → Finish"
    for path, pattern in ((DESIGN, r"^### 4\.1 "), (DESIGN, r"^### 1\.3 ")):
        blocks = _sections(_read(path), pattern)
        if not blocks:
            problems.append({"doc": "design", "section": pattern, "problem": "section not found"})
            continue
        body = "\n".join(blocks[0][1])
        if expected not in body:
            problems.append({"doc": "design", "section": pattern, "problem": "phase chain text missing",
                             "expected": expected})
    return problems


def check(verbose=True):
    protocol = _load_protocol()
    mechanism = _read(MECHANISM)
    design = _read(DESIGN)
    problems = []
    problems.extend(check_codes(protocol, mechanism))
    problems.extend(check_thresholds(protocol, mechanism))
    problems.extend(check_states(protocol, mechanism, design))
    if verbose:
        if problems:
            for item in problems:
                print(f"PROTOCOL/DOCTRINE DRIFT: {json.dumps(item, ensure_ascii=False)}", file=sys.stderr)
        else:
            print(f"OK: protocol 与上位文档机器事实一致"
                  f"（{len(protocol['codes']['codes'])} 码 / {len(protocol['thresholds']['keys'])} 配置键 / "
                  f"{len(protocol['states']['transitions'])} 条转移）")
    return problems


def main(argv=None):
    parser = argparse.ArgumentParser(description="protocol 文档片段生成与一致性核对")
    parser.add_argument("--check", action="store_true", help="反向核对机制稿/设计稿的机器事实")
    parser.add_argument("--out", help="把片段写入该目录")
    parser.add_argument("--json", action="store_true", help="以 JSON 输出核对结果")
    args = parser.parse_args(argv)

    if args.check:
        problems = check(verbose=not args.json)
        if args.json:
            print(json.dumps({"ok": not problems, "problems": problems}, ensure_ascii=False))
        return 0 if not problems else 1

    protocol = _load_protocol()
    if args.out:
        out = Path(args.out)
        out.mkdir(parents=True, exist_ok=True)
        for name, render in RENDERERS.items():
            (out / name).write_text(render(protocol), encoding="utf-8")
            print(out / name)
        return 0

    for name, render in RENDERERS.items():
        header = name.replace(".md", "").upper()
        print(f"===== {header} =====")
        print(render(protocol))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
