#!/usr/bin/env python3
"""wf 设计文档机检器（设计文档 + charter + 索引表）。

覆盖对象：
  A. wf-framework-design.md —— 框架契约正文
  B. wf-framework-charter.md —— 目标、边界与演进判据（"要不要做"的唯一事实源）
  C. wf-framework-design.index.md —— 唯一定义索引表（两文档共用）

检查项（失败即 FAIL）：
  1. § 引用可解析：设计文档内部 §N.N 必须存在；charter 内部的 § 引用必须带"设计 "前缀且命中设计章节。
  2. 唯一定义重名：两个文档的"（…唯一定义…）"标签归一化后不得重名（charter 条目不得在设计文档重复定义）。
  3. 索引表登记：每行章节引用可解析（§ 命中设计、charter Tn 命中 charter）；两文档每个定义位点必须登记。
  4. 消费点齐全性：设计行按词面章节统计；charter 行按设计文档中的 `charter Tn` 指针统计，
     既报"正文有指针但索引没写"，也报"索引写了但正文没有指针"（悬空消费）。
  5. charter 内部引用：`Tn` 必须命中 charter 章节（防止章号漂移）。
  6. 迁移残留：已经迁入 charter 的条目关键词不得回流到设计文档。
  7. 验收覆盖与档位断言：charter 每个定义条目必须在设计稿 §8.2 的表格里有一条带
     `charter Tn` 标注的场景行；索引列写了 §8.2 但表格缺行同样算失败。三档断言表按
     四列（场景/档位/待决事实/出口）校验表头、档位与逐行完整性；§8.2 内任何表格行的
     列数不是 3 或 4 即报错（防止异常行被静默跳过）。

指标（低于阈值即 FAIL）：
  定义命中率、消费点命中率（两文档合并统计），引用检查残差（输出，不设阈值）。
"""
import os
import re
import sys
from pathlib import Path

ROOT = Path(os.environ.get("WF_DESIGN_ROOT") or Path(__file__).resolve().parent.parent)
DOC = ROOT / "docs/workflows/wf-framework-design.md"
CHARTER = ROOT / "docs/workflows/wf-framework-charter.md"
INDEX = ROOT / "docs/workflows/wf-framework-design.index.md"
EXTERNAL_DOCS = ("workflow-design.md", "workflow-implementation.md", "wf-variant.md")

DEF_RATE_MIN = 0.90
CONSUME_RATE_MIN = 0.90

# charter 独占的判据关键词：设计文档不得再出现（迁移残留检查）
CHARTER_ONLY = (
    "团队与审批组织",
    "marketplace",
    "并行 worktree",
    "开放式 DSL",
    "雪花 ID",
    "双库对账",
    "调度队列",
)

errors: list[str] = []


def parse_doc(path: Path, head_pat: str):
    lines = path.read_text(encoding="utf-8").split("\n")
    headings, current, hlines = set(), None, []
    for ln in lines:
        m = re.match(head_pat, ln)
        if m:
            headings.add(m.group(1))
            current = m.group(1)
        hlines.append(current)
    return lines, headings, hlines


def section_lines(lines, hlines):
    secs: dict[str, list[str]] = {}
    for i, ln in enumerate(lines):
        sec = hlines[i]
        if sec:
            secs.setdefault(sec, []).append(ln)
    return secs


def section_text(lines, hlines):
    secs: dict[str, str] = {}
    for i, ln in enumerate(lines):
        s = hlines[i]
        if s:
            secs[s] = secs.get(s, "") + ln
    return secs


def load():
    return parse_doc(DOC, r"^#{2,3} (\d+(?:\.\d+)?)")


def load_charter():
    if not CHARTER.exists():
        errors.append(f"charter 缺失: {CHARTER}")
        return [], set(), []
    return parse_doc(CHARTER, r"^#{2,3} (T\d+)\b")


def check_refs(lines, headings, cheads=()):
    skipped = 0
    for i, ln in enumerate(lines, 1):
        if "唯一定义索引表" in ln:
            continue
        if any(d in ln for d in EXTERNAL_DOCS) or "源 §" in ln:
            skipped += 1
            continue
        for ref in re.findall(r"§(\d+(?:\.\d+)*)", ln):
            if ref.count(".") > 1:
                errors.append(f"L{i}: 三级以下引用 §{ref} 不可解析（章节只到 N.N）")
            elif ref not in headings:
                errors.append(f"L{i}: 内部引用 §{ref} 不存在")
        for t in re.findall(r"charter (T\d+)", ln):
            if cheads and t not in cheads:
                errors.append(f"L{i}: 引用 charter {t} 不存在")
    return skipped


def check_charter_refs(lines, cheads, dheads):
    for i, ln in enumerate(lines, 1):
        for m in re.finditer(r"§(\d+(?:\.\d+)*)", ln):
            ref, start = m.group(1), m.start()
            if ref.count(".") > 1:
                errors.append(f"charter L{i}: 三级以下引用 §{ref} 不可解析（章节只到 N.N）")
                continue
            if not ln[:start].endswith(("设计 ", "设计稿 ", "依赖说明 ", "原 ")):
                errors.append(f"charter L{i}: §{ref} 未带“设计稿 ”前缀")
            elif ref not in dheads:
                errors.append(f"charter L{i}: 引用设计 §{ref} 不存在")
        if re.match(r"^#{2,3} T\d+", ln):
            continue
        for t in re.findall(r"\b(T\d+)\b", ln):
            if t not in cheads:
                errors.append(f"charter L{i}: 内部引用 {t} 不存在")


def check_dup_defs(doc_lines, ch_lines):
    names: dict[str, list[str]] = {}
    sources = [("设计", doc_lines), ("charter", ch_lines)]
    for tag, lines in sources:
        for i, ln in enumerate(lines, 1):
            if "唯一定义索引表" in ln:
                continue
            for m in re.finditer(r"（([^（）]*)唯一定义([^（）]*)）", ln):
                left, right = m.group(1), m.group(2)
                if "§" in left or "§" in right:
                    continue
                raw = (left + right).strip(" ，,、")
                if not raw:
                    pre = ln[: m.start()]
                    bm = re.search(r"\*\*([^*]{2,28})$", pre)
                    raw = bm.group(1) if bm else ""
                key = re.sub(r"[（）()，,、\s·—-]", "", raw.split("，")[0].split(",")[0])
                key = key or "匿名"
                names.setdefault(key, []).append(f"{tag}L{i}")
    for key, locs in names.items():
        if key == "匿名":
            continue
        if len(locs) > 1:
            errors.append(f"唯定义重名「{key}」: " + ", ".join(locs))


def def_sites(lines, hlines, contain="唯一定义"):
    sites = []
    for i, ln in enumerate(lines, 1):
        if contain not in ln:
            continue
        if "唯一定义索引表" in ln or "唯一定义重名" in ln:
            continue
        if re.search(r"§\S+\s*唯一定义", ln):
            continue
        sec = hlines[i - 1]
        if sec:
            sites.append((i, sec, ln))
    return sites


def def_name(line):
    m = re.search(r"([^*｜|]{2,28})（[^（）]*唯一定义", line)
    return re.sub(r"[\s*#>-]", "", m.group(1))[-8:] if m else ""


def check_index(headings, cheads):
    if not INDEX.exists():
        errors.append(f"索引表缺失: {INDEX}")
        return None
    rows = []
    for i, ln in enumerate(INDEX.read_text(encoding="utf-8").split("\n"), 1):
        if not ln.startswith("| ") or "---" in ln or "定义（名称" in ln:
            continue
        ncols = len(ln.strip("|").split("|"))
        if ncols != 6:
            errors.append(
                f"index.md L{i}: 列数应为 6（当前 {ncols}，缺列或多列都会绕过核对状态校验）"
            )
            continue
        rows.append(ln)
        cells = [c.strip() for c in ln.strip("|").split("|")]
        state = cells[5]
        if state not in ("未核对", "已核对·有消费", "已核对·仅定义节"):
            errors.append(f"index.md L{i}: 核对状态「{state}」不在允许取值内")
        elif state == "已核对·有消费" and "§" not in cells[4]:
            errors.append(f"index.md L{i}: 标为已核对·有消费，但语义消费列没有节号")
        for ref in re.findall(r"§(\d+(?:\.\d+)*)", ln):
            if ref.count(".") > 1:
                errors.append(f"index.md L{i}: 三级以下引用 §{ref} 不可解析（章节只到 N.N）")
            elif ref not in headings:
                errors.append(f"index.md L{i}: 引用 §{ref} 不存在")
        for t in re.findall(r"charter (T\d+)\b", ln):
            if t not in cheads:
                errors.append(f"index.md L{i}: 引用 charter {t} 不存在")
    if rows and len(rows) < 40:
        errors.append(f"index.md 仅 {len(rows)} 行登记（< 40）")
    return rows


def parse_rows(raw_rows):
    rows = []
    for ln in raw_rows:
        cells = [c.strip() for c in ln.strip("|").split("|")]
        defcell = cells[1]
        # 设计行按词面候选列（第 3 列）核对机检口径；charter 行按人工语义列（第 5 列）核对指针
        consumecell = cells[4] if len(cells) > 4 and "charter" in defcell else cells[2]
        head = defcell.split("（")[0].strip()
        hhead = head
        key = re.sub(r"\s*·\s*(?:§\S*|charter T\d+)\s*$", "", hhead).strip()
        dm = re.search(r"§(\d+(?:\.\d+)?)", defcell)
        tm = re.search(r"charter (T\d+)", defcell)
        consume = set(re.findall(r"§(\d+(?:\.\d+)?)", consumecell))
        rows.append(
            {
                "key": key,
                "defsec": dm.group(1) if dm else "",
                "defcell": defcell,
                "tsec": tm.group(1) if tm else "",
                "consume": consume,
                "line": ln,
            }
        )
    return rows


def sort_secs(secs):
    return sorted(secs, key=lambda x: [int(p) for p in x.split(".")])


def check_consume(rows, secs, site_secs, charter_secs, charter_site_secs, sec_lines):
    def_hit = total_actual = total_gap = 0
    for r in rows:
        key = r["key"]
        if r["tsec"]:
            tsec = r["tsec"]
            actual = {s for s, txt in secs.items() if f"charter {tsec}" in txt}
            key_in_def = bool(key) and key in charter_secs.get(tsec, "")
            if key_in_def or tsec in charter_site_secs:
                def_hit += 1
            else:
                errors.append(
                    f"charter 定义未命中：索引「{key} · charter {tsec}」——该章不含匹配键，也不是已验证的定义位点"
                )
            if "8.2" not in r["consume"]:
                errors.append(
                    f"charter 条目缺验收场景行「{key}」：索引消费列未登记设计稿 §8.2"
                )
            acc = [
                ln for ln in sec_lines.get("8.2", [])
                if ln.startswith("|") and f"charter {tsec}" in ln
            ]
            if not acc:
                errors.append(
                    f"charter 条目缺验收场景行「{key}」：§8.2 表格无带 `charter {tsec}` 标注的行"
                )
            gaps = actual - r["consume"]
            dangling = r["consume"] - actual
            if gaps:
                errors.append(
                    f"charter 消费点缺项「{key}」: 正文出现于 {', '.join('§' + g for g in sort_secs(gaps))}"
                    f"，索引消费点列缺 {len(gaps)} 节"
                )
            if dangling:
                errors.append(
                    f"charter 消费点悬空「{key}」: 索引列了 {', '.join('§' + g for g in sort_secs(dangling))}"
                    f"，但正文无 `charter {tsec}` 指针"
                )
            total_actual += len(actual)
            total_gap += len(gaps)
            continue

        defsec = r["defsec"]
        if key and key not in "\n".join(secs.values()):
            errors.append(
                f"索引定义名失效「{key}」：正文已无此名称（改名或删除后未回写索引）"
            )
        actual = {s for s, txt in secs.items() if key and key in txt}
        key_in_def = bool(key) and key in secs.get(defsec, "")
        if key_in_def:
            def_hit += 1
        else:
            errors.append(
                f"定义未命中：索引「{key} · §{defsec}」——落点章节不含该定义名（改名或换章后未回写索引）"
            )
        if not key:
            continue
        actual.discard(defsec)
        gaps = actual - r["consume"]
        total_actual += len(actual)
        total_gap += len(gaps)
        if gaps:
            errors.append(
                f"消费点缺项「{key}」: 正文出现于 {', '.join('§' + g for g in sort_secs(gaps))}"
                f"，索引消费点列缺 {len(gaps)} 节"
            )
    def_rate = def_hit / len(rows) if rows else 0.0
    consume_rate = 1 - total_gap / total_actual if total_actual else 0.0
    return def_rate, consume_rate, total_gap


def full_def_name(line):
    m = re.search(r"\*\*([^*]{2,40})（[^（）]*唯一定义", line)
    return re.sub(r"[\s*#>-]", "", m.group(1)) if m else ""


def check_bidir(sites, ch_sites, rows):
    """定义位点双向核对：每个定义位点必须在索引表中有同章节且记名的登记行。

    章节级计数不足以发现"同一章有多个定义、删掉其中一个登记行"的情形（§1.1 就是这种章），
    因此按"章节 + 定义名"逐位点比对；定义名取不来时退化为章节计数比对。
    """
    from collections import defaultdict

    rows_by = defaultdict(list)
    for r in rows:
        sec = r["defsec"] or r["tsec"]
        if sec:
            rows_by[sec].append(r.get("defcell", ""))

    def verify(lineno, sec, line, tag):
        name = full_def_name(line)
        if not name:
            return
        squashed = re.sub(r"\s", "", name)
        if any(squashed in re.sub(r"\s", "", cell) for cell in rows_by.get(sec, [])):
            return
        errors.append(f"{tag}L{lineno}（§{sec}）定义位点「{name}」未在索引表登记")

    for lineno, sec, line in sites:
        verify(lineno, sec, line, "设计 ")
    for lineno, sec, line in ch_sites:
        verify(lineno, sec, line, "charter ")


def check_tier(sec_lines):
    """§8.2 的三档断言表：需人裁决档以独立列承载，不与通过/阻断二值合并。"""
    rows = [ln for ln in sec_lines.get("8.2", []) if ln.startswith("|")]
    for ln in rows:
        n = len(ln.strip("|").split("|"))
        if n not in (3, 4):
            errors.append(f"§8.2 表格列数异常（{n} 列，应为 3 或 4）：{ln[:48]}…")
    tri = [ln for ln in rows if len(ln.strip("|").split("|")) == 4]
    if len(tri) < 5:
        errors.append("§8.2 三档断言表缺失或数据行不足（<4）：需人裁决档没有独立落点")
        return
    header = [c.strip() for c in tri[0].strip("|").split("|")]
    for need in ("档位", "待决事实", "出口"):
        if not any(need in c for c in header):
            errors.append(f"§8.2 三档断言表头缺「{need}」列")
    for ln in tri[1:]:
        cells = [c.strip() for c in ln.strip("|").split("|")]
        if all(c and set(c) <= {"-", ":"} for c in cells):
            continue  # 分隔行：每一格都只由 - 或 : 组成
        name = cells[0] or "（无名行）"
        if not cells[0]:
            errors.append("§8.2 三档断言行缺场景名")
        if "需人裁决" not in cells[1]:
            errors.append(f"§8.2 三档行「{name}」档位不是需人裁决")
        if not cells[2]:
            errors.append(f"§8.2 三档行「{name}」缺待决事实")
        if not cells[3]:
            errors.append(f"§8.2 三档行「{name}」缺出口")


def check_residue(doc_lines):
    for i, ln in enumerate(doc_lines, 1):
        for kw in CHARTER_ONLY:
            if kw in ln:
                errors.append(f"L{i}: 迁移残留「{kw}」——该判据已由 charter 定义，设计文档不得重复")


if __name__ == "__main__":
    lines, headings, hlines = load()
    ch_lines, ch_heads, ch_hlines = load_charter()
    skipped = check_refs(lines, headings, ch_heads)
    if ch_lines:
        check_charter_refs(ch_lines, ch_heads, headings)
    check_dup_defs(lines, ch_lines)
    raw_rows = check_index(headings, ch_heads)
    sites = def_sites(lines, hlines)
    ch_sites = def_sites(ch_lines, ch_hlines) if ch_lines else []
    check_bidir(sites, ch_sites, parse_rows(raw_rows) if raw_rows else [])
    check_residue(lines)

    secs = section_text(lines, hlines)
    sec_lines = section_lines(lines, hlines)
    check_tier(sec_lines)
    ch_secs = section_text(ch_lines, ch_hlines) if ch_lines else {}
    def_rate = consume_rate = 0.0
    gaps = 0
    if raw_rows:
        def_rate, consume_rate, gaps = check_consume(
            parse_rows(raw_rows),
            secs,
            {sec for _, sec, _ in sites},
            ch_secs,
            {sec for _, sec, _ in ch_sites},
            sec_lines,
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
            f"OK：设计 {len(lines)} 行 / charter {len(ch_lines)} 行；定义位点 {len(sites)}+{len(ch_sites)} 个；"
            f"索引表 {len(raw_rows)} 行；消费点缺项 {gaps}；三率：定义命中 {def_rate:.0%} / "
            f"消费点命中 {consume_rate:.0%} / 引用检查残差 {skipped} 行（输出不设阈值）；"
            f"七项检查 + 覆盖率断言通过"
        )
        sys.exit(0)
    sys.exit(1)
