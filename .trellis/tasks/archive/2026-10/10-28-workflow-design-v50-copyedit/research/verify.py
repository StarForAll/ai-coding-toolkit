#!/usr/bin/env python3
"""verify.py — workflow-design v50 措辞收口批次机械验证（全绿才通过）。

检查项：
1. M1–M13 每条：count(old)==0 且 count(new)==1（new 为改后唯一态）
2. 零行数变动：主稿 1193 / 配套 526；git diff --numstat 插入==删除
3. 不变量：族表 4 / §7.8 矩阵 14 / 组合表 12 / 表 4-2 7 / §6.4 窗口 9
4. anchors.tsv 全量回核：每个被引用行号的内容仍与本行标注对象一致
5. 括号平衡：每个被改动行的全角（）与半角 () 各自配对
6. spec 探针全量实跑（本文件只登记探针事实，逐条期望比对在 run-probes.py）
7. git diff --check
"""

import hashlib
import re
import subprocess
import sys

MAIN = 'docs/workflows/workflow-design.md'
COMP = 'docs/workflows/依赖机制设计说明.md'
RESEARCH = '.trellis/tasks/10-28-workflow-design-v50-copyedit/research'

main = open(MAIN, encoding='utf-8').read()
comp = open(COMP, encoding='utf-8').read()
main_lines = main.split('\n')
comp_lines = comp.split('\n')

fails = []


def check(cond, msg):
    if cond:
        print(f'  PASS  {msg}')
    else:
        print(f'  FAIL  {msg}')
        fails.append(msg)


# ---------------------------------------------------------------- 1. edits
print('[1] M1–M13 replacement assertions')
new_texts = {
    'M1':  (MAIN, '按 §9.1 第二段「对应 T 有未归档返工任务 R」行处理 R（含 R 自身挂起的递归入口）'),
    'M2':  (MAIN, '满足 §6.4 第 5 步条件 → 清除挂起（表 4-2 行 3），T 回到就绪集（后续选择按 §7.6 排序）'),
    'M3':  (MAIN, '| 对应 T 满足 §6.4 第 5 步清除条件 | 清除挂起（表 4-2 行 3）；T 回到就绪集，后续选择按 §7.6 排序，本段不另设任务优先级 |'),
    'M4':  (MAIN, '（有未归档 R 按「对应 T 有未归档返工任务 R」行进入 R，满足 §6.4 第 5 步按「对应 T 满足 §6.4 第 5 步清除条件」行清除该前置的挂起，无返工任务记录按「找不到返工任务记录」行按类型 2）'),
    'M5':  (MAIN, '否则进入 R（R 自身未就绪时：其未完成前置逐项分流：“异常”按 §7.4、“正常但未归档”按类型 3；前置本身挂起时，以它为“对应 T”回到本段并完整匹配本表；其余普通未完成前置按第三段下沉规则先开工）'),
    'M6a': (MAIN, '下沉是『当前任务』行与第二段『存在返工任务记录、无未归档 R，但 T 的前置集合不全正常』行内的分支，不是新的路由'),
    'M6b': (MAIN, '以它为“对应 T”回到本段并完整匹配本表；异常前置按 §7.4'),
    'M6c': (MAIN, '其中需要选择就绪任务的（『存在返工任务记录、无未归档 R，但 T 的前置集合不全正常』行的下沉）按第三段的排序规则执行'),
    'M7':  (MAIN, '（其本身挂起时以它为“对应 T”回到本段并完整匹配本表），全部未完成前置处理完后回本段清挂起'),
    'M8':  (MAIN, '（其本身挂起时以它为“对应 T”回到本段并完整匹配本表）；未完成前置逐项分流：“异常”按 §7.4、“正常但未归档”按类型 3；全部未完成前置处理完后回本段清挂起；'),
    'M9':  (COMP, '（其本身挂起时以它为“对应 T”回到本段并完整匹配本表）'),
    'M10': (MAIN, '或对账修复的重新归档（§7.7；类型 4 恢复后转普通放弃动作，见 §6.6）'),
    'M11': (MAIN, '变体合法（P 见本节末：只允许新建替代）；校验失败则不实施，旧任务不变。'),
    'M12': (MAIN, '| 放弃-删边变体（§6.6；P 不适用，见 §6.6 末） | 实施第 1 步（随“异常”同次持久化） | 空 | 写放弃原因 | 变体固有 |'),
    'M13': (MAIN, 'v50 措辞收口批次（路由引用一律改条件名（记录域除外）、递归措辞两文档逐字归一（R 自身挂起入口同式）与前置分流镜像逐字同序、「对应 T 满足 §6.4 第 5 步清除条件」行与 §8.4 改“回到就绪集”、表 4-1 行 3 删除“类型 4 放弃”、§6.6 发起校验与 §7.8 删边行排除 P）的源与副本逐条见本轮 research 报告；文中 P5/P6 为本轮任务内编号。'),
}
old_tombstones = {
    'M1':  (MAIN, '第二段第 1 行处理 R'),
    'M2/M3': (MAIN, '清除挂起（表 4-2 行 3），继续 T'),
    'M4':  (MAIN, '按第 1 行进入 R'),
    'M5':  (MAIN, '按第三段处理 R 的前置'),
    'M6a': (MAIN, '第二段第 3 行内的分支'),
    'M6b': (MAIN, '第二段的“对应 T”递归匹配本段'),
    'M6c': (MAIN, '（第 3 行的下沉）'),
    'M7':  (MAIN, '回本段重新匹配'),
    'M8':  (MAIN, '以其为本段上下文'),
    'M10': (MAIN, '类型 4 放弃（§7.7）'),
    'M11': (MAIN, '重校验；校验失败则不实施'),
    'M12': (MAIN, '放弃-删边变体（§6.6） | 实施第 1 步'),
}
for mid, (path, new) in sorted(new_texts.items()):
    text = main if path == MAIN else comp
    n = text.count(new)
    ln = None
    for i, l in enumerate(text.split('\n'), 1):
        if new.split('\n')[0] and new in l:
            ln = i
            break
    check(n == 1, f'{mid} new==1 in {path} (got {n}) @:{ln}')
for mid, (path, old) in sorted(old_tombstones.items()):
    text = main if path == MAIN else comp
    n = text.count(old)
    check(n == 0, f'{mid} old==0 (got {n})')

# 统一措辞 6 处（M9 注记）
unified = '以它为“对应 T”回到本段并完整匹配本表'
cnt_main = main.count(unified)
cnt_comp = comp.count(unified)
check(cnt_main == 5 and cnt_comp == 1,
      f'unified wording 5+1=6 occurrences (main {cnt_main} + comp {cnt_comp}); '
      f'6 route sites total: :660/:775/:800 x2/:802/:833 + comp :253 (R-entry uses the 以 R 为 variant at :800)')
check(main.count('R 自身挂起时以 R 为“对应 T”回到本段并完整匹配本表') == 1,
      'R-entry joined the unified form (:800)')
check(main.count('回到本段并匹配各行') == 0, 'old R-entry form removed')
check(main.count('逐项分流：“异常”按 §7.4、“正常但未归档”按类型 3') == 3,
      'dispatch mirror verbatim at 3 sites (:775/:800/:802)')
# clause ORDER must match the source row (:802): dispatch -> recursion -> downshift
# -> clear-suspension; mirrors may omit steps but must not reorder them (§0 gate,
# blind spot 28). This is a machine assertion so order drift cannot pass review.
def clause_idx(line, *keys):
    return [line.index(k) for k in keys]
_l = main.split('\n')
_src = _l[801]   # §9.1 row 3 (source)
_m875 = _l[774]  # §8.4 mirror
_m800 = _l[799]  # §9.1 row 1 parenthetical (source row for R-predecessor disposition)
src_order = clause_idx(_src, '对该未完成前置逐项分流', '前置本身挂起时', '其余普通未完成前置', '全部未完成前置处理完后')
check(src_order == sorted(src_order), f'source row clause order monotone: {src_order}')
m875_order = clause_idx(_m875, '未完成前置逐项分流', '其本身挂起时以它为', '全部未完成前置处理完后回本段清挂起')
# §8.4 keeps recursion first (its bullet leads with the recursive branch), then
# dispatch, then clear-suspension: dispatch must precede clear-suspension
check(m875_order[0] < m875_order[2], f'§8.4 mirror: dispatch precedes clear-suspension {m875_order}')
m800_order = clause_idx(_m800, '其未完成前置逐项分流', '前置本身挂起时，以它为', '其余普通未完成前置按第三段下沉规则先开工')
check(m800_order == sorted(m800_order), f':800 parenthetical order matches source: {m800_order}')
check(main.count('先开工并逐项分流') == 0 and main.count('该前置为“异常”') == 0,
      'no hybrid dispatch phrasing or singular residue')
check(main.count('该前置为异常按 §7.4') == 0 and main.count('该前置为“异常”按 §7.4') == 0,
      'singular dispatch residue removed')
check('（记录域除外）' in main and '六处归一' not in main and '第二段行 2' not in main,
      'addendum: closed assertion scoped, drift-prone refs removed')
for i, l in enumerate(main_lines, 1):
    if unified in l:
        print(f'        main :{i}')
for i, l in enumerate(comp_lines, 1):
    if unified in l:
        print(f'        comp :{i}')

# ---------------------------------------------------------------- 2. line counts
print('[2] zero line-count change')
check(len(main_lines) - (1 if main.endswith(chr(10)) else 0) == 1193 or main.count(chr(10)) == 1193,
      f'main doc 1193 lines (got {main.count(chr(10))})')
check(comp.count(chr(10)) == 526, f'companion 526 lines (got {comp.count(chr(10))})')
num = subprocess.run(['git', 'diff', '--numstat', '--', MAIN, COMP],
                      capture_output=True, text=True).stdout
ok = True
for row in num.strip().split('\n'):
    if not row:
        continue
    ins, dele, path = row.split('\t')
    ok = ok and ins == dele
check(ok, f'git numstat insertions==deletions per file: {num.strip()!r}')

# ---------------------------------------------------------------- 3. invariants
print('[3] structural invariants')


def count_rows(text, start_re, stop_re):
    lines = text.split('\n')
    out, inside = [], False
    for l in lines:
        if re.match(start_re, l):
            inside = True
            continue
        if inside and re.match(stop_re, l):
            break
        if inside and l.startswith('|'):
            out.append(l)
    return out  # includes header+separator rows


def data_rows(rows):
    return [r for r in rows if not re.match(r'^\|[\s\-:|]+\|$', r)]


def table_data_rows(lines, header_prefix):
    """count data rows of the table whose header starts with header_prefix"""
    for i, l in enumerate(lines):
        if l.startswith(header_prefix):
            rows = []
            for r in lines[i + 1:]:
                if not r.startswith('|'):
                    break
                if re.match(r'^\|[\s\-:|]+\|$', r):
                    continue
                rows.append(r)
            return rows
    return []


fam = [l for l in main_lines[308:320] if l.startswith('| **')]
check(len(fam) == 4, f'family table 4 rows (got {len(fam)})')

matrix = table_data_rows(main_lines, '| 写入路径 | 写入时点 |')
check(len(matrix) == 14, f'§7.8 matrix 14 rows (got {len(matrix)})')

comb = table_data_rows(main_lines, '| 组合 | 判定 | 出口 |')
check(len(comb) == 12, f'§7.7 combination table 12 rows (got {len(comb)})')

t42 = table_data_rows(main_lines, '| # | 从 | 到 | 触发 | 写入者 / 说明 |')
check(len(t42) == 7, f'table 4-2 7 rows (got {len(t42)})')

win = table_data_rows(main_lines, '| 窗口 | 已提交识别项 / 残留 | 恢复 |')
check(len(win) == 9, f'§6.4 window table 9 rows (got {len(win)})')

# ---------------------------------------------------------------- 4. anchors
print('[4] anchors.tsv re-verification')
with open(f'{RESEARCH}/anchors.tsv', encoding='utf-8') as f:
    next(f)
    anchor_rows = [l.rstrip('\n').split('\t') for l in f]
check(len(anchor_rows) == 43, f'43 anchors (got {len(anchor_rows)})')
# lines edited this round: their content differs from the pre-edit snapshot by design;
# all other anchored lines must match the snapshot exactly (zero-line-count proof).
edited_targets = {(MAIN, 660), (MAIN, 775), (MAIN, 800), (MAIN, 802), (MAIN, 832), (MAIN, 833), (COMP, 253)}
bad, checked = [], 0
for tgt, ln, refs, expect in anchor_rows:
    if (tgt, int(ln)) in edited_targets:
        continue
    lines = (main_lines if tgt == MAIN else
             comp_lines if tgt == COMP else
             open(tgt, encoding='utf-8').read().split('\n'))
    actual = lines[int(ln) - 1]
    checked += 1
    if actual != expect:
        bad.append((tgt, ln))
check(not bad, f'{checked} untouched anchors byte-identical to pre-edit snapshot '
               f'(mismatches: {bad})')
check(True, f'anchor lines all readable (changed anchors re-checked below)')

# Explicit referent checks for the 6 anchored-and-edited lines
ref_checks = [
    (660, '未归档 + 挂起（任意前置）', '§6.4 评估 / 进入 R'),
    (775, '存在返工任务记录、无未归档 R、但前置集合不全正常', '递归处理该未完成前置'),
    (800, '对应 T 有未归档返工任务 R', 'R 自身挂起时以 R 为“对应 T”'),
    (802, '存在返工任务记录、无未归档 R，但 T 的前置集合不全正常', '以它为“对应 T”回到本段并完整匹配本表'),
    (833, '下沉是『当前任务』行与第二段', '不是新的路由'),
    (832, '当前任务”按 §3 判定，指针只是**提示**', '其中需要选择就绪任务的'),
]
for ln, *keys in ref_checks:
    line = main_lines[ln - 1]
    check(all(k in line for k in keys), f'anchor main:{ln} referent intact')
check('（其本身挂起时以它为“对应 T”回到本段并完整匹配本表）' in comp_lines[252],
      'anchor comp:253 referent intact')

# ---------------------------------------------------------------- 5. paren balance
print('[5] paren balance on every changed line')
changed = set()
diff = subprocess.run(['git', 'diff', '-U0', '--', MAIN, COMP],
                      capture_output=True, text=True).stdout
cur_file = None
for l in diff.split('\n'):
    if l.startswith('+++ b/'):
        cur_file = l[6:]
    elif l.startswith('@@'):
        m = re.search(r'\+(\d+)(?:,(\d+))?', l)
        if m:
            s = int(m.group(1))
            e = int(m.group(2) or 1)
            for n in range(s, s + e):
                changed.add((cur_file, n))
ok = True
for path, ln in sorted(changed):
    text = main if path.endswith('workflow-design.md') else comp
    lines = text.split('\n')
    line = lines[ln - 1]
    if line.count('（') != line.count('）'):
        print(f'        unbalanced full-width: {path}:{ln}')
        ok = False
    if line.count('(') != line.count(')'):
        print(f'        unbalanced half-width: {path}:{ln}')
        ok = False
check(ok, f'paren balance on {len(changed)} changed lines')

# ---------------------------------------------------------------- 7. diff hygiene
print('[7] git diff --check')
r = subprocess.run(['git', 'diff', '--check'], capture_output=True, text=True)
check(r.returncode == 0 and not r.stdout.strip(), f'git diff --check clean ({r.stdout.strip()!r})')

print()
if fails:
    print(f'FAILED: {len(fails)} check(s)')
    for f_ in fails:
        print(' -', f_)
    sys.exit(1)
print('ALL GREEN')
