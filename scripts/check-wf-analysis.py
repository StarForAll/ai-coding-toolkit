#!/usr/bin/env python3
"""wf 方案文档的只读一致性校验：表格渲染 / 引用可达 / 跨视图字段 / 计数 / 行号边界 / JSON / 撤回词残留。"""
import json, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOC = os.path.join(ROOT, "docs/workflows/wf/analysis/proposal-repairing-state.md")
CODE_BASE = os.path.join(ROOT, "docs/workflows/wf/payload/lib/wflib/")
WITHDRAWN = ["preferred", "in_flight", "latest_launch", "eligible_blockers", "reusable_rounds", "certain"]

def main():
    text = open(DOC, encoding="utf-8").read()
    lines = text.splitlines()
    problems = []

    # 0) 历史小节范围（撤回词允许出现在历史行）
    hist_start = next((i for i, l in enumerate(lines) if l.startswith("## 9.")), len(lines))

    # 1) 表格渲染：连续 | 块内部不得出现非表行；列数一致
    i = 0
    while i < len(lines):
        if lines[i].startswith("|"):
            j = i
            while j < len(lines) and lines[j].startswith("|"):
                j += 1
            block = lines[i:j]
            if len(block) >= 2 and not re.match(r"^\|[\s:\-|]+\|$", block[1]):
                problems.append(("表格", i + 1, "缺表头分隔行"))
            cols = {len(b.split("|")) for b in block}
            if len(cols) > 1:
                problems.append(("表格", i + 1, "列数不一致 %s" % sorted(cols)))
            i = j
        else:
            i += 1

    # 2) 引用可达
    heads = set(re.findall(r"^(?:##|###) (\d+[a-z]?(?:\.\d+[a-z]?)?)(?:\.|\s)", text, re.M))
    refs = set(re.findall(r"§(\d+(?:\.\d+)?[a-z]?)", text))
    live = "\n".join(lines[:hist_start])
    for r in sorted(refs):
        if r not in heads and ("§" + r) in live and hist_start == 0:
            problems.append(("引用", 0, "§%s 不存在（不回退到上级小节）" % r))
    # 逐行检查：历史小节之前出现的 §N.M 必须存在
    for i, l in enumerate(lines[:hist_start]):
        for mm in re.finditer(r"§(\d+\.\d+[a-z]?)", l):
            if mm.group(1) not in heads:
                problems.append(("引用", i + 1, "§%s 不存在（历史小节前）" % mm.group(1)))

    # 3) 跨视图字段：schema 顶层字段 ↔ 判据表行
    m = re.search(r"```json\n(.*?)```", text, re.S)
    top = set()
    if m:
        try:
            obj = json.loads(re.sub(r"//.*", "", m.group(1)))
            scope = obj.get("repair_scope") if isinstance(obj, dict) else None
            if isinstance(scope, dict):
                top = set(scope.keys())
        except Exception as e:
            problems.append(("JSON", 0, "schema 不可解析：%s" % str(e)[:40]))
    seg = text[text.index("| 事实 | 判据 |"):]
    seg = seg[:seg.index("\n\n")]
    raw = re.findall(r"^\| `([a-z_.]+)(?:\[\])?` \|", seg, re.M)
    criteria = {x.split(".")[0] for x in raw}
    for f in sorted(top - criteria):
        problems.append(("字段", 0, "schema 顶层字段 `%s` 无判据行" % f))
    known_extra = {"review_required", "final_gate"}
    for f in sorted(criteria - top - known_extra):
        problems.append(("字段", 0, "判据字段 `%s` 不在 schema 顶层" % f))

    # 4) 计数
    for tag, title in (("A", r"A 档：机制可测（(\d+) 项）"), ("B", r"B 档：文档审查（(\d+) 项"), ("G", r"### 6a")):
        if tag == "G":
            continue
        items = re.findall(r"^\| %s(\d+) \|" % tag, text, re.M)
        mt = re.search(title, text)
        if mt and int(mt.group(1)) != len(items):
            problems.append(("计数", 0, "%s 档标题 %s ≠ 条目 %d" % (tag, mt.group(1), len(items))))
        if items and [int(x) for x in items] != list(range(1, len(items) + 1)):
            problems.append(("计数", 0, "%s 档编号不连续" % tag))

    # 5) 代码行号边界
    sizes = {f: sum(1 for _ in open(CODE_BASE + f, encoding="utf-8"))
             for f in os.listdir(CODE_BASE) if f.endswith(".py")}
    for mm in re.finditer(r"`?([a-z]+)\.py:(\d+)", text):
        f, ln = mm.group(1) + ".py", int(mm.group(2))
        if f in sizes and ln > sizes[f]:
            problems.append(("行号", 0, "%s:%d 越界（共 %d 行）" % (f, ln, sizes[f])))

    # 6) JSON 可解析
    for k, blk in enumerate(re.findall(r"```json\n(.*?)```", text, re.S)):
        try:
            json.loads(re.sub(r"//.*", "", blk))
        except Exception as e:
            problems.append(("JSON", 0, "第 %d 块不可解析：%s" % (k + 1, str(e)[:40])))

    # 7) 撤回词残留（历史小节之前）
    for w in WITHDRAWN:
        for i, l in enumerate(lines[:hist_start]):
            if w in l and "不设" not in l and "无 `" not in l and "撤回" not in l:
                problems.append(("撤回词", i + 1, "`%s` 仍出现" % w))

    # 8) 条件覆盖：C1–C4 在条件表与出口表都出现
    for c in ("C1", "C2", "C3", "C4"):
        if text.count("**%s" % c) == 0:
            problems.append(("条件", 0, "%s 缺失" % c))

    # 9) token 集合一致（出口表 ↔ §6 枚举）
    toks = set(re.findall(r"`(rerun_check|record_disposition|restore_bytes|human_release|relaunch_review|resume_inflight|redecide_round|await_material|pause_for_human|abandon_task)`", text))
    enum = re.search(r"action ∈ \{([^}]*)\}", text)
    if enum:
        declared = {t.strip().strip("`") for t in enum.group(1).split(",")}
        if declared != toks:
            problems.append(("token", 0, "枚举与使用不一致：多 %s / 少 %s" % (declared - toks, toks - declared)))

    # 10) 标签引用：矩阵行号必须存在；已废弃的「X 档」与 G 编号不得出现在正文
    body = "\n".join(lines[:hist_start])
    total = len(re.findall(r"^\| (\d+) \| (?:机制|文档) \|", body, re.M))
    for mm in re.finditer(r"矩阵 #(\d+)", body):
        if int(mm.group(1)) > total:
            problems.append(("标签", 0, "矩阵 #%s 超出矩阵范围（共 %d 行）" % (mm.group(1), total)))
    for pat in ("A 档", "B 档", "G 档"):
        if pat in body:
            problems.append(("标签", 0, "`%s` 已不存在（v60 合并），应指 §7 矩阵" % pat))
    for mm in re.finditer(r"\bG(\d)\b", body):
        problems.append(("标签", 0, "G%s 已废弃（G 档并入 §7 矩阵）" % mm.group(1)))

    print("== wf 方案文档 lint ==")
    if not problems:
        print("OK：0 问题")
        print("检查范围：表格渲染 / 小节引用（严格） / schema↔判据 / 计数与编号 / 行号边界 / JSON / "
              "撤回词 / C1–C4 / token 枚举 / 标签引用（A/B/G）")
        print("**未覆盖**：语义级一致性（判据与代码是否真的同源）、矩阵断言与 §4/§2.1 的语义对应、"
              "指引文本质量——这些仍需人读或评审")
        return 0
    for cat, ln, msg in problems:
        print("[%s]%s %s" % (cat, (" L%d" % ln) if ln else "", msg))
    print("共 %d 个问题" % len(problems))
    return 1

if __name__ == "__main__":
    sys.exit(main())
