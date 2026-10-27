#!/usr/bin/env python3
"""M11 mechanical verifier for the workflow-design v48 fix round (incl. the
independent-review correction round, fix-manifest-r2.tsv).

Groups:
  1. manifest rows (both rounds): count(old)==0 after execution (except rows
     whose new text contains old — M1 — where count(old)==1), count(new)==1.
     Rows superseded by r2 rows (marked in SUPERSEDED) must have
     count(new)==0 instead. Prints each live row's new-text line number.
  2. fix-notes 已同步 gate: every backticked phrase in fix-notes.md must occur
     at least once in the main design or the companion.
  3. Invariants: matrix data rows = 14, combo-table data rows = 12, 表 4-2
     data rows = 7, §6.4 window rows = 9, the pre-existing 11 combo rows are
     byte-identical to HEAD, no bare `| — |` cell in the matrix, and every
     changed line (vs HEAD) has balanced full-width and half-width parens.
  4. Full probe run against the spec block: two-document scope only (no task
     path, so probes survive task archival); record-domain hits are judged by
     context. Hard-asserted expected values; location scans report only.
  5. § label check: every "§X.Y … （docs/workflows/<doc>.md:LINE" assertion in
     fix-notes / appendix C v48 / companion §36 must have LINE inside §X.Y's
     actual section range of that document.

Exit code 0 only when every hard check passes.
"""
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path("/home/xzc/projects/personal/ai-coding-toolkit")
MAIN = ROOT / "docs/workflows/workflow-design.md"
COMP = ROOT / "docs/workflows/依赖机制设计说明.md"
REC = Path(__file__).resolve().parent
FIXNOTES = REC / "fix-notes.md"
MANIFESTS = [REC / "fix-manifest.tsv", REC / "fix-manifest-r2.tsv"]

# 初轮 M 行被复核修正轮 R 行进一步改写的，其新文断言改为 ==0（由取代行承载 ==1）
SUPERSEDED = {"M1", "M3a", "M3c", "M3d", "M3e", "M3f", "M3g", "M3h", "M6", "R1", "R2", "R6b"}  # r2 的 R1/R2/R6b 由 r3 的 R2a/R2b/R10b 取代

main_text = MAIN.read_text(encoding="utf-8")
comp_text = COMP.read_text(encoding="utf-8")

failures: list[str] = []


def hard_fail(msg: str) -> None:
    failures.append(msg)


def line_of(text: str, needle: str) -> int:
    return text[: text.index(needle)].count("\n") + 1


# ---------- 1. manifest rows ----------
print("== 1. manifest rows ==")
for manifest in MANIFESTS:
    print(f"-- {manifest.name}")
    for ln in manifest.read_text(encoding="utf-8").splitlines():
        if not ln.strip() or ln.startswith("ID\t"):
            continue
        cols = ln.split("\t")
        rid, fname, old, new = cols[0], cols[1], cols[3].replace("\\n", "\n"), cols[4].replace("\\n", "\n")
        paths = {
            "主稿": MAIN, "配套": COMP,
            "spec": ROOT / ".trellis/spec/docs/index.md",
            "guide": ROOT / ".trellis/spec/guides/design-review-thinking-guide.md",
            "residuals": REC / "residuals.md",
        }
        texts = {k: v.read_text(encoding="utf-8") for k, v in paths.items()}
        path = paths[fname]
        text = texts[fname]
        if rid in SUPERSEDED:
            c_new = text.count(new)
            if c_new != 0:
                hard_fail(f"{rid} (superseded): count(new)={c_new}, expected 0")
            else:
                print(f"{rid}\t{path.name}\tsuperseded")
            continue
        expected_old = 1 if old in new else 0
        c_old = text.count(old)
        if c_old != expected_old:
            hard_fail(f"{rid}: count(old)={c_old}, expected {expected_old}")
            continue
        c_new = text.count(new)
        if c_new != 1:
            hard_fail(f"{rid}: count(new)={c_new}, expected 1")
            continue
        print(f"{rid}\t{path.name}\t{line_of(text, new)}")

# ---------- 2. fix-notes 已同步 gate ----------
print("== 2. fix-notes backtick-phrase gate ==")
notes = FIXNOTES.read_text(encoding="utf-8")
phrases = re.findall(r"`([^`\n]+)`", notes)
bad = [p for p in phrases if p not in main_text and p not in comp_text]
if bad:
    for p in bad:
        hard_fail(f"fix-notes backtick phrase not found in 主稿/配套: {p}")
else:
    print(f"ok: {len(phrases)} backticked phrases all found in 主稿/配套")

# ---------- 3. invariants ----------
print("== 3. invariants ==")


def table_rows(text: str, header: str) -> list[str]:
    lines = text.splitlines()
    for i, ln in enumerate(lines):
        if ln.strip() == header:
            out = []
            j = i + 2  # skip separator row
            while j < len(lines) and lines[j].lstrip().startswith("|"):
                out.append(lines[j].strip())
                j += 1
            return out
    hard_fail(f"table header not found: {header}")
    return []


def check_count(name: str, got: int, expected: int) -> None:
    print(f"{name} = {got} (expect {expected})")
    if got != expected:
        hard_fail(f"{name} = {got}, expected {expected}")


check_count("matrix data rows", len(table_rows(main_text, "| 写入路径 | 写入时点 | 指向终值 | 说明 / 原因终值 | 依据 |")), 14)
check_count("combo table data rows", len(table_rows(main_text, "| 组合 | 判定 | 出口 |")), 12)
check_count("表 4-2 data rows", len(table_rows(main_text, "| # | 从 | 到 | 触发 | 写入者 / 说明 |")), 7)
check_count("§6.4 window data rows", len(table_rows(main_text, "| 窗口 | 已提交识别项 / 残留 | 恢复 |")), 9)
check_count("§4.4 family table data rows", len(table_rows(main_text, "| 族 | 内容 | 受 §7.5 建边限制 |")), 4)

# 「三族」残留检查：规范位 0，历史记录域按域判定（主稿 status v46 段 + 附录 v46、配套 §34；spec 经 R8 后为 0）
_spec_text = (ROOT / ".trellis/spec/docs/index.md").read_text(encoding="utf-8")
def _cnt(pattern, *texts):
    rx = re.compile(pattern)
    return sum(1 for t2 in texts for ln in t2.splitlines() if rx.search(ln))
san = _cnt("三族", main_text)
sac = _cnt("三族", comp_text)
sas = _cnt("三族", _spec_text)
print(f"三族 hits: 主稿={san}（status v46 段 + 附录 v46，记录域）/ 配套={sac}（§34 v46 条目，记录域）/ spec={sas}（R8 后应为 0）")
if (san, sac, sas) != (2, 1, 0):
    hard_fail(f"三族 残留分布异常: 主稿={san} 配套={sac} spec={sas}（期望 2/1/0，全部记录域）")

head_main = subprocess.run(
    ["git", "-C", str(ROOT), "show", "HEAD:docs/workflows/workflow-design.md"],
    capture_output=True, text=True, check=True,
).stdout
head_combo = table_rows(head_main, "| 组合 | 判定 | 出口 |")[:11]
cur_combo = table_rows(main_text, "| 组合 | 判定 | 出口 |")[:11]
if head_combo == cur_combo:
    print("ok: pre-existing 11 combo rows byte-identical to HEAD")
else:
    hard_fail("pre-existing 11 combo rows drifted from HEAD")

matrix_start = main_text.index("| 写入路径 | 写入时点 | 指向终值 | 说明 / 原因终值 | 依据 |")
matrix_end = main_text.index("状态值不变的字段维护不触发表 4-2", matrix_start)
bare = main_text[matrix_start:matrix_end].count("| — |")
check_count("bare '| — |' cells in matrix", bare, 0)

# 改动行括号平衡（新增机械检查，复核三.7）
for name, path, head_text in (("主稿", MAIN, head_main), ("配套", COMP, None)):
    head_comp = ""
    if name == "配套":
        head_comp = subprocess.run(
            ["git", "-C", str(ROOT), "show", "HEAD:docs/workflows/依赖机制设计说明.md"],
            capture_output=True, text=True, check=True,
        ).stdout
    cur_lines = (main_text if name == "主稿" else comp_text).splitlines()
    head_lines = (head_main if name == "主稿" else head_comp).splitlines()
    changed = {i for i in range(min(len(cur_lines), len(head_lines))) if cur_lines[i] != head_lines[i]}
    changed |= set(range(len(head_lines), len(cur_lines)))
    unbalanced = []
    for i in sorted(changed):
        ln = cur_lines[i]
        if ln.count("（") != ln.count("）") or ln.count("(") != ln.count(")"):
            unbalanced.append((i + 1, ln[:60]))
    if unbalanced:
        for no, prev in unbalanced:
            hard_fail(f"{name}:{no} 括号不平衡: {prev}…")
    else:
        print(f"ok: {name} changed lines paren-balanced ({len(changed)} lines)")

# ---------- 4. probes（双文档范围，记录域命中判域不计数） ----------
print("== 4. probes ==")


def probe(pattern: str, texts) -> int:
    rx = re.compile(pattern)
    return sum(1 for t in texts for ln in t.splitlines() if rx.search(ln))


def probe_both(pattern: str) -> int:
    return probe(pattern, [main_text, comp_text])


def probe_main(pattern: str) -> int:
    return probe(pattern, [main_text])


def probe_comp(pattern: str) -> int:
    return probe(pattern, [comp_text])


HARD = [
    ("按 §3 有效（", probe_main, 0),
    (r"有当前任务，且该任务未归档、账本为|有当前任务，但该任务未归档、账本为|有当前任务，但该任务已归档", probe_main, 0),
    (r"按 §3 有效|按 §3 无效", probe_main, 9),
    (r"依赖满足 =|就绪.*前置集合全部为", 3),
    (r"满足判定按 §4.3|按主设计 §4.3", 5),
    ("指向已归档、规划中且前置未满足", probe_comp, 0),
    ("或为“正常但未归档”的任务|前置未完工（或为", 0),
    ("视为无当前任务", probe_main, 14),
    ("继任者即新的 P", probe_main, 2),
    ("异常前置走替换|前置为异常时按删边或替换", 0),
    (r"或删边后不再等待$", 0),
    ("两种处置由人决定", 0),
    ("旧任务未归档 → 归档旧任务|边已重连但旧任务未归档", 0),
    ("先补建 / 重连、后归档", 2),
    ("继任任务", 4),
    ("无当前任务时：T 进行中或规划中但前置含非正常", 0),
    ("无当前任务时按 §9.1", 2),
    ("唯一 / 不再 / 一律 / 只」", 2),
    ("下游范围为未归档下游|类型 4 恢复边界（唯一源）|返工登记（动作序列与窗口的唯一源）", 3),
    ("标识占用校验（唯一源）", 1),
    ("移交完成的持久判据", 2),
    (r"重新生成后重校验|已落盘的替换指向|原预写标识已被其他身份占用|按 §7.8 标识占用规则", probe_main, 7),
    # v48 修正后十五条（双文档规范位；记录域命中判域不计数）
    ("重连目标可为异常", 0),  # r3 墓碑：原许可短语被指称固定取代，非零即旧副本回流
    ("重连目标为异常时按", 7),
    (r"建边目标\*\*账本为“异常”", 2),  # 加粗标记在字段中间，探针按原文匹配
    (r"\*\*重连类\*\*", 1),
    ("类型 1 补建的继任者重连", 1),  # 族 4 的类型 1 路径单列，防止族 4 只覆盖替换 / 放弃
    ("建边 / 重连四类", 1),  # :72 的路径族第二份枚举，防只改 :66
    ("被重连的未归档下游", 2),
    ("重连只要求两端存在", 3),
    ("先按类型 5 补建", 2),  # 规范位 1（:910 自检）+ 记录域 1（:953 v47 附录）；自检位丢失即降为 1，判域见 spec 注释
    ("自成一个提交组", 2),
    ("重连目标为“异常”仍补齐重连", 1),
    ("回指产生者位置", 1),
    ("字段矩阵行义务", 4),
    ("回指产生者（依据", 0),
    ("v46 同步", 0),
    ("含已预写标识", 6),  # 规范位 5（主稿 3 + 配套 2）+ 记录域 1（配套 §36）；判域见 spec 注释
]
SOFT = [
    ("预生成.{0,4}新 P",),
    ("修复的写入纪律",),
    ("下游仍指向该任务、该任务未归档",),
    ("替换指向为空",),
    ("新建替代",),
    ("继任者已建",),
    ("唯一清空点",),
    ("写入矩阵",),
    ("P 的指向不得置空",),
    ("已确立的 P 继任关系不得置空|类型 4 恢复边界",),
    ("当前登记标记|返工登记准备|返工登记发布|返工登记取消",),
    ("P 角色解析|正常完成的 P 终点|角色完整性守卫",),
    (r"机制持久化范围（唯一源）|提交范围.*按.*§3|持久化.*主设计 §3",),
    (r"账本 / 前置集合 / 替换指向 / 返工来源|账本与前置集合.*持久化|提交范围含账本",),
]
for entry in HARD:
    pattern, fn, expected = entry if len(entry) == 3 else (entry[0], probe_both, entry[1])
    n = fn(pattern)
    mark = "ok" if n == expected else "FAIL"
    print(f"[{mark}] {pattern[:48]} = {n} (expect {expected})")
    if n != expected:
        hard_fail(f"probe {pattern[:48]} = {n}, expected {expected}")
for (pattern,) in SOFT:
    print(f"[scan] {pattern[:48]} = {probe_both(pattern)}")

# ---------- 5. § 标签-章节范围核对（新增机械检查，复核三.7） ----------
print("== 5. § label vs section range ==")


def section_ranges(text: str) -> dict:
    ranges = {}
    marks = []
    for i, ln in enumerate(text.splitlines(), start=1):
        m = re.match(r"^#{2,3} (\d+(?:\.\d+)?)[\.．]?\s", ln)
        if m:
            marks.append((m.group(1), i))
    for idx, (label, start) in enumerate(marks):
        end = marks[idx + 1][1] - 1 if idx + 1 < len(marks) else len(text.splitlines())
        ranges[label] = (start, end)
    return ranges


main_ranges = section_ranges(main_text)
comp_ranges = section_ranges(comp_text)
pair_rx = re.compile(r"§(\d+(?:\.\d+)?)([^（）]{0,40})（docs/workflows/([^：]+?)\.md:(\d+)")
scan_targets = [("fix-notes", notes)]
main_lines = main_text.splitlines()
v48_start = next(i for i, ln in enumerate(main_lines, start=1) if ln.strip() == "### v48")
v47_start = next(i for i, ln in enumerate(main_lines, start=1) if ln.strip() == "### v47")
for i in range(v48_start, v47_start):  # 附录 C v48 条目（动态范围）
    scan_targets.append((f"主稿附录:{i}", main_lines[i - 1]))
comp_lines = comp_text.splitlines()
s36 = next(i for i, ln in enumerate(comp_lines, start=1) if ln.startswith("## 36"))
for i in range(s36, len(comp_lines) + 1):  # 配套 §36 至文末（动态范围）
    scan_targets.append((f"配套§36:{i}", comp_lines[i - 1]))
checked = 0
bad_labels = []
for where, chunk in scan_targets:
    if "\n" in chunk:
        lines = chunk.splitlines()
    else:
        lines = [chunk]
    for ln in lines:
        for m in pair_rx.finditer(ln):
            label, _, doc, line_no = m.group(1), m.group(2), m.group(3), int(m.group(4))
            ranges = main_ranges if "workflow-design" in doc else comp_ranges
            if label not in ranges:
                continue  # 未在标题表中的标签（如 §0 简写差异）不判
            lo, hi = ranges[label]
            checked += 1
            if not (lo <= line_no <= hi):
                bad_labels.append(f"{where}: §{label} 不含 {doc}.md:{line_no}（实际范围 {lo}–{hi}）")
if bad_labels:
    for b in bad_labels:
        hard_fail(f"§ 标签与章节不符: {b}")
else:
    print(f"ok: {checked} § label / line pairs all inside their section ranges")

print()
if failures:
    print(f"RESULT: {len(failures)} failure(s)")
    for f in failures:
        print(f"  - {f}")
    sys.exit(1)
print("RESULT: all green")
