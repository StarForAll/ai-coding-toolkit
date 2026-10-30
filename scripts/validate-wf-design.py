#!/usr/bin/env python3
"""wf-framework-design 设计文档机检器（四条检查 + 覆盖率断言，正文 §8 第 0 项）。

四条检查 + 三率输出：
  1. § 引用可解析——内部章节号必须存在；外部引用（同行点名外部文档或"源 §"）跳过，
     整行豁免的行数作为"引用检查残差"输出。
  2. 唯一定义重名——"（…唯一定义…）"标签归一化后不得重名。
  3. 索引表双向核对——索引表每行章节引用可解析；正文每个定义位点必须在表中登记。
  4. 消费点齐全性——对每个索引条目，取其匹配键（定义名"（"前主词）在正文出现的
     章节集合，与消费点列求差，非空即报（缺项清单 = 人工确认入表的候选）。

三率（低于阈值即 FAIL——校验器必须断言自己的覆盖面，R7）：
  定义命中率   = 定义位点可机械验证的索引行数 / 索引行数
  消费点命中率 = 1 - Σ缺项 / Σ正文实际出现章节
  引用检查残差 = 因整行豁免而未逐引用检查的行数（输出，不设阈值）

用法：python3 scripts/validate-wf-design.py   （退出码 0 = 通过）
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DOC = ROOT / "docs/workflows/wf-framework-design.md"
INDEX = ROOT / "docs/workflows/wf-framework-design.index.md"
EXTERNAL_DOCS = ("workflow-design.md", "workflow-implementation.md", "wf-variant.md")

DEF_RATE_MIN = 0.90
CONSUME_RATE_MIN = 0.90

errors: list[str] = []


def load():
    lines = DOC.read_text(encoding="utf-8").split("\n")
    headings, current, hlines = set(), None, []
    for i, ln in enumerate(lines, 1):
        m = re.match(r"^#{2,3} (\d+(?:\.\d+)?)", ln)
        if m:
            headings.add(m.group(1))
            current = m.group(1)
        hlines.append(current)
    return lines, headings, hlines


def check_refs(lines, headings):
    skipped = 0
    for i, ln in enumerate(lines, 1):
        if "唯一定义索引表" in ln:
            continue
        if any(d in ln for d in EXTERNAL_DOCS) or "源 §" in ln:
            skipped += 1
            continue
        for ref in re.findall(r"§(\d+(?:\.\d+)?)", ln):
            if ref not in headings:
                errors.append(f"L{i}: 内部引用 §{ref} 不存在")
    return skipped


def check_dup_defs(lines):
    names: dict[str, list[int]] = {}
    for i, ln in enumerate(lines, 1):
        if "唯一定义索引表" in ln:
            continue
        for m in re.finditer(r"（([^（）]*)唯一定义([^（）]*)）", ln):
            left, right = m.group(1), m.group(2)
            if "§" in left or "§" in right:
                continue  # 引用形态（"§X 唯一定义"），不是定义位点
            raw = (left + right).strip(" ，,、")
            if not raw:
                pre = ln[: m.start()]
                bm = re.search(r"\*\*([^*]{2,28})$", pre)
                raw = bm.group(1) if bm else ""
            key = re.sub(r"[（）()，,、\s·—-]", "", raw.split("，")[0].split(",")[0])
            key = key or "匿名"
            names.setdefault(key, []).append(i)
    for key, locs in names.items():
        if key == "匿名":
            continue  # 无法命名者由位点双向核对覆盖
        if len(locs) > 1:
            errors.append(f"唯定义重名「{key}」: L" + ", L".join(map(str, locs)))


def def_sites(lines, hlines):
    sites = []
    for i, ln in enumerate(lines, 1):
        if "唯一定义" not in ln:
            continue
        if "唯一定义索引表" in ln or "唯一定义重名" in ln:
            continue  # 表名 / 检查项名，非定义位点
        if re.search(r"§\S+\s*唯一定义", ln):
            continue  # 引用形态
        sec = hlines[i - 1]
        if sec:
            sites.append((i, sec, ln))
    return sites


def def_name(line):
    m = re.search(r"([^*｜|]{2,28})（[^（）]*唯一定义", line)
    return re.sub(r"[\s*#>-]", "", m.group(1))[-8:] if m else ""


def check_index(headings):
    if not INDEX.exists():
        errors.append(f"索引表缺失: {INDEX}")
        return None
    rows = []
    for i, ln in enumerate(INDEX.read_text(encoding="utf-8").split("\n"), 1):
        if not ln.startswith("| ") or "---" in ln or "定义（名称" in ln:
            continue
        if len(ln.strip("|").split("|")) < 4:
            errors.append(f"index.md L{i}: 列数不足")
            continue
        rows.append(ln)
        for ref in re.findall(r"§(\d+(?:\.\d+)?)", ln):
            if ref not in headings:
                errors.append(f"index.md L{i}: 引用 §{ref} 不存在")
    if rows and len(rows) < 40:
        errors.append(f"index.md 仅 {len(rows)} 行登记（< 40）")
    return rows


def parse_rows(raw_rows):
    rows = []
    for ln in raw_rows:
        cells = [c.strip() for c in ln.strip("|").split("|")]
        defcell, consumecell = cells[1], cells[2]
        head = defcell.split("（")[0].strip()
        key = re.sub(r"\s*·\s*§.*$", "", head).strip()  # 去掉"· §X"落点后缀
        m = re.search(r"§(\d+(?:\.\d+)?)", defcell)
        defsec = m.group(1) if m else ""
        consume = set(re.findall(r"§(\d+(?:\.\d+)?)", consumecell))
        rows.append({"key": key, "defsec": defsec, "consume": consume})
    return rows


def check_consume(rows, lines, hlines, site_secs):
    """检查 4：消费点齐全性 + 定义命中率。"""
    secs: dict[str, str] = {}
    for i, ln in enumerate(lines, 1):
        s = hlines[i - 1]
        if s:
            secs[s] = secs.get(s, "") + ln
    def_hit = 0
    total_actual = 0
    total_gap = 0
    for r in rows:
        key, defsec = r["key"], r["defsec"]
        actual = {s for s, txt in secs.items() if key and key in txt}
        # 定义命中 = 匹配键出现在落点章节，或落点章节是经双向核对验证的真实定义位点
        key_in_def = bool(key) and key in secs.get(defsec, "")
        if key_in_def or defsec in site_secs:
            def_hit += 1
        else:
            errors.append(
                f"定义未命中：索引「{key} · §{defsec}」——落点章节不含匹配键，也不是已验证的定义位点章节"
            )
        if not key:
            continue
        actual.discard(defsec)
        gaps = sorted(actual - r["consume"], key=lambda x: [int(p) for p in x.split(".")])
        total_actual += len(actual)
        total_gap += len(gaps)
        if gaps:
            errors.append(
                f"消费点缺项「{key}」: 正文出现于 {', '.join('§' + g for g in gaps)}"
                f"，索引消费点列缺 {len(gaps)} 节"
            )
    def_rate = def_hit / len(rows) if rows else 0.0
    consume_rate = 1 - total_gap / total_actual if total_actual else 0.0
    return def_rate, consume_rate, total_gap


def check_bidir(sites, headings):
    idx = re.sub(r"\s", "", INDEX.read_text(encoding="utf-8")) if INDEX.exists() else ""
    for lineno, sec, line in sites:
        sec_hit = re.search(rf"·§{re.escape(sec)}\b", idx)
        name = def_name(line)
        name_hit = bool(name) and name in idx
        if not (sec_hit or name_hit):
            errors.append(f"L{lineno}（§{sec}）定义位点未在索引表登记（名「{name}」）")


if __name__ == "__main__":
    lines, headings, hlines = load()
    skipped = check_refs(lines, headings)
    check_dup_defs(lines)
    raw_rows = check_index(headings)
    sites = def_sites(lines, hlines)
    check_bidir(sites, headings)
    def_rate = consume_rate = 0.0
    gaps = 0
    if raw_rows:
        site_secs = {sec for _, sec, _ in sites}
        def_rate, consume_rate, gaps = check_consume(
            parse_rows(raw_rows), lines, hlines, site_secs
        )
    metrics_fail = def_rate < DEF_RATE_MIN or consume_rate < CONSUME_RATE_MIN
    if errors:
        print(f"FAIL：{len(errors)} 处")
        for e in errors:
            print(" -", e)
    if metrics_fail:
        print(
            f"FAIL：覆盖率不达标——定义命中率 {def_rate:.0%}（阈值 {DEF_RATE_MIN:.0%}）、"
            f"消费点命中率 {consume_rate:.0%}（阈值 {CONSUME_RATE_MIN:.0%}）"
        )
    if not errors and not metrics_fail:
        print(
            f"OK：正文 {len(lines)} 行；定义位点 {len(sites)} 个；索引表 {len(raw_rows)} 行；"
            f"消费点缺项 {gaps}；三率：定义命中 {def_rate:.0%} / 消费点命中 {consume_rate:.0%}"
            f" / 引用检查残差 {skipped} 行（整行豁免，输出不设阈值）；四条检查 + 覆盖率断言通过"
        )
        sys.exit(0)
    sys.exit(1)
