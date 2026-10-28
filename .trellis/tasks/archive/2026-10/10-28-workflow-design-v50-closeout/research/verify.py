#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""verify.py — v50 收口批次全量验证（§5）。只写 stdout。"""
import hashlib
import importlib.util
import re
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent.parent.parent.parent
OUT = Path(__file__).resolve().parent
MAIN = 'docs/workflows/workflow-design.md'
COMP = 'docs/workflows/依赖机制设计说明.md'
SPEC = '.trellis/spec/docs/index.md'

FAILS = []


def ok(cond, msg):
    print(('PASS ' if cond else 'FAIL ') + msg)
    if not cond:
        FAILS.append(msg)
    return cond


def rd(p):
    return (REPO / p).read_text(encoding='utf-8')


def git_show(p):
    r = subprocess.run(['git', 'show', f'HEAD:{p}'], cwd=REPO,
                       capture_output=True, text=True, encoding='utf-8')
    if r.returncode != 0:
        raise SystemExit(f'git show 失败: {p}: {r.stderr}')
    return r.stdout


print('== 1. E1–E8 落位（count(old)==0, count(new)==1）==')
# R1 轮注：E1–E8 的 new 串已被 R1（新建替代继任面）整句替换；
# 此处直接核对 R1 后的现行串，逐处恰 1、且 R1 前形态（E1 轮串）残留 0。
R1_STRINGS = [
    ('R1a', MAIN, '收尾任务自身被替换时继任者即收尾对象（由人按新范围细化其收尾内容）、被放弃且无继任者（删边变体）时由人重新定义收尾任务；',
     '收尾任务被替换、或被放弃且留有继任者（新建替代）时，继任者即收尾对象（替换由人按新范围细化其收尾内容）、被放弃且无继任者（删边变体）时由人重新定义收尾任务；'),
    ('R1b', MAIN, '收尾任务被替换时继任者即收尾对象（按新范围细化收尾内容）、被放弃且无继任者时由人重定义，',
     '收尾任务被替换、或被放弃且留有继任者（新建替代）时继任者即收尾对象（替换按新范围细化收尾内容）、被放弃且无继任者（删边变体）时由人重定义，'),
    ('R1c', COMP, '收尾任务自身被替换时继任者即收尾对象、被放弃且无继任者时由人重新定义，',
     '收尾任务被替换、或被放弃且留有继任者（新建替代）时继任者即收尾对象、被放弃且无继任者（删边变体）时由人重新定义，'),
]
edited_lines = {}  # path -> set(line numbers)
for rid, p, old, new in R1_STRINGS:
    t = rd(p)
    ok(t.count(old) == 0, f'{rid} 前形态残留 0（实际 {t.count(old)}） @ {p}')
    ok(t.count(new) == 1, f'{rid} 现行串恰 1（实际 {t.count(new)}） @ {p}')
    if t.count(new) == 1:
        ln = t.split('\n').index(next(l for l in t.split('\n') if new in l)) + 1
        print(f'     {rid} {p}:{ln}')
        edited_lines.setdefault(p, set()).add(ln)
# 其余 E 项（E4–E8）串未被 R1 改动，沿用原核对
EDITS = [
    ('E4', MAIN, '其他未完成替换/放弃或类型 1 后续处分走类型 5。',
     '其他未完成替换/放弃或类型 1 后续处分走类型 5；已归档但账本无记录 / 挂起（新发生的类型 1）同样在本段阻断，待人确认后按类型 1 修复。'),
    ('E5', MAIN, '不视为本版承诺被推翻。',
     '不视为本版承诺被推翻。**文本措辞（同义表述、子句顺序、行号指称、词汇标签）不参与「是否完成」的判定**：只要不改变任何判定格的动作，一律登记为已知精度项、单点受理，不重开收尾判定。'),
    ('E6', MAIN, '①连续两版无骨架级 / 角色级缺陷；',
     '①状态枚举门 D1 全绿（每个可达格有唯一向前动作；文档表行数与已编码行数一致；脚本 scripts/design-statecheck.py）；'),
    ('E7', MAIN, '文中 P5/P6 为本轮任务内编号。',
     '文中 P5/P6 为本轮任务内编号。收口批次（F1 收尾继任面、第一段类型 1 补齐、§10 收口标准 ① 改 D1 状态枚举门、§0 措辞范围声明）的源与验收位见 scripts/design-statecheck.py 与本轮报告；v41 记录中的旧 ① 为历史文本。'),
    ('E8', SPEC, '(16 probes;', '(17 probes;'),
]
for eid, p, old, new in EDITS:
    t = rd(p)
    if old in new:
        residual = t.count(old) - t.count(new)
    elif eid == 'E6':
        residual = t.count(old) - 1
    else:
        residual = t.count(old)
    ok(residual == 0, f'{eid} old 残留 0 处（实际 {residual}） @ {p}')
    ok(t.count(new) == 1, f'{eid} new 恰 1 处（实际 {t.count(new)}） @ {p}')
    if t.count(new) == 1:
        ln = t.split('\n').index(next(l for l in t.split('\n') if new in l)) + 1
        print(f'     {eid} {p}:{ln}')
        edited_lines.setdefault(p, set()).add(ln)
# R1 轮新增文档位（不在原 E 台账内）：§10 ① 脚本位置短语 + §10 自检新建替代场景
t = rd(MAIN)
ok(t.count('脚本 scripts/design-statecheck.py）；') == 1, 'R2 §10 ① 脚本位置短语恰 1')
ln = t.split('\n').index(next(l for l in t.split('\n') if '脚本 scripts/design-statecheck.py）；' in l)) + 1
print(f'     R2a {MAIN}:{ln}')
ok(t.count('一次放弃收尾任务（新建替代变体）') == 1, 'R2 §10 自检新建替代场景恰 1')
ln = t.split('\n').index(next(l for l in t.split('\n') if '一次放弃收尾任务（新建替代变体）' in l)) + 1
print(f'     R2b {MAIN}:{ln}')
# E6 历史位核验（v41 记录保留 1 处旧 ①，预期）
mt = rd(MAIN)
ok(mt.count('①连续两版无骨架级 / 角色级缺陷；') == 1,
   f'E6 old 串余 1 处（v41 历史记录，预期）: 实际 {mt.count("①连续两版无骨架级 / 角色级缺陷；")}')

print('== 2. 零行数变动 ==')
for p, exp_lines in [(MAIN, 1193), (COMP, 526)]:
    n = (REPO / p).read_bytes().count(b'\n')
    ok(n == exp_lines, f'{p} 行数 {n} == {exp_lines}')
r = subprocess.run(['git', 'diff', '--numstat', '--', MAIN, COMP],
                   cwd=REPO, capture_output=True, text=True)
for line in r.stdout.strip().splitlines():
    ins, dele, path = line.split('\t')
    ok(ins == dele, f'numstat 插入==删除: {path} ({ins}/{dele})')

print('== 3. heading 集合与九张表行数 ==')
def headings(t):
    return [l.rstrip() for l in t.split('\n') if l.startswith('#')]
base_hm = (OUT / 'headings-main.txt').read_text(encoding='utf-8').strip().split('\n')
base_hc = (OUT / 'headings-comp.txt').read_text(encoding='utf-8').strip().split('\n')
ok(headings(rd(MAIN)) == base_hm, '主稿 heading 集合不变')
ok(headings(rd(COMP)) == base_hc, '配套 heading 集合不变')

spec = importlib.util.spec_from_file_location('dsc', REPO / 'scripts/design-statecheck.py')
dsc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(dsc)
tables = dsc.CURRENT_TABLES
BASE_TABLES = {'第一段': 4, '第二段': 4, '未收尾': 7, '已收尾': 5, '表4-2': 7,
               '组合表': 12, '族表': 4, '§7.4': 4, '§6.4窗口': 9, '§7.8矩阵': 14}
for k, v in BASE_TABLES.items():
    ok(tables[k] == v, f'表 {k} 行数 {tables[k]} == 基线 {v}')

print('== 4. anchors 全量回核（除被编辑行外 0 变化、0 缺失）==')
# 本批次全部被编辑行（E 轮 + R1 轮 + R2 轮），由上面的落位核对动态收集；
# 另补 §10 自检行（R2b 场景插入所在行，含 path:line 引用，anchors 快照须比对）。
R2_LINES = {}
t = rd(MAIN)
for needle in ('一次放弃收尾任务（新建替代变体）',):
    ln = t.split('\n').index(next(l for l in t.split('\n') if needle in l)) + 1
    R2_LINES[ln] = needle
all_edited = {p: set(edited_lines.get(p, set())) for p in (MAIN, COMP)}
all_edited[MAIN] |= set(R2_LINES.keys())
for p in (MAIN, COMP):
    old_lines = git_show(p).split('\n')
    new_lines = rd(p).split('\n')
    ok(len(old_lines) == len(new_lines), f'{p} 行数不变（anchors 不漂移前提）')
    changed = [i + 1 for i, (a, b) in enumerate(zip(old_lines, new_lines)) if a != b]
    expect_changed = sorted(all_edited[p])
    ok(changed == expect_changed,
       f'{p} 变化行 {changed} == 被编辑行 {expect_changed}')
    # anchors.tsv 里的每个引用行的内容仍逐字相同（或属被编辑行）
    anchors = (OUT / 'anchors.tsv').read_text(encoding='utf-8').strip().split('\n')
    bad = 0
    for row in anchors:
        parts = row.split('\t')
        if parts[0] != p:
            continue
        ln = int(parts[1].replace('line', ''))
        if ln <= len(new_lines) and old_lines[ln - 1] != new_lines[ln - 1]:
            if ln not in expect_changed:
                bad += 1
    ok(bad == 0, f'{p} anchors 引用行除被编辑行外 0 变化（异常 {bad}）')

print('== 5. 括号平衡（被改动行全角/半角各自配对）==')
for p in (MAIN, COMP):
    for ln in sorted(all_edited[p]):
        l = rd(p).split('\n')[ln - 1]
        ok(l.count('（') == l.count('）'), f'{p}:{ln} 全角括号配对（{l.count("（")}/{l.count("）")}）')
        ok(l.count('(') == l.count(')'), f'{p}:{ln} 半角括号配对（{l.count("(")}/{l.count(")")}）')

print('== 6. spec 探针全量实跑 ==')
spec_text = rd(SPEC)
bash_blocks = re.findall(r'```bash\n(.*?)```', spec_text, re.S)
probes = []
for blk in bash_blocks:
    for line in blk.split('\n'):
        s = line.strip()
        if s.startswith('rg ') and not s.startswith('rg -n "'):
            probes.append(s)
        elif s.startswith('rg '):
            probes.append(s)
probe_no_num = 0
probe_mismatch = []
probe_expected_ok = 0
NUM_RE = re.compile(r'#\s*(\d+)\s*(hits?\b|lines?\b|occurrences?\b|matching\b)', re.I)
v50_block_probes = 0
for cmd in probes:
    r = subprocess.run(cmd, cwd=REPO, shell=True, capture_output=True, text=True)
    actual = len([l for l in r.stdout.splitlines() if l.strip()])
    m = NUM_RE.search(cmd)
    if '# v50 additions' in cmd:
        pass
    if m:
        exp = int(m.group(1))
        if actual == exp:
            probe_expected_ok += 1
        else:
            probe_mismatch.append((cmd[:70], exp, actual))
    else:
        probe_no_num += 1
print(f'     探针总数 {len(probes)}（数值期望比对通过 {probe_expected_ok}，'
      f'非数值/上下文判定 {probe_no_num}）')
for c, e, a in probe_mismatch:
    print(f'     MISMATCH exp={e} actual={a} :: {c}')
ok(not probe_mismatch, f'探针数值期望全部一致（{len(probe_mismatch)} 处不符）')
# v50 块探针计数 == 注释 (17 probes;)（E8 计数改对）
# v50 additions 标记位于大代码块内部；按注释行切出其后的连续 rg 行直到块尾或下一注释
marker = next((l for l in spec_text.split('\n') if '(17 probes;' in l), None)
ok(marker is not None, 'spec 含 v50 additions (17 probes; 标记行')
v50_cnt = 0
if marker:
    lines = spec_text.split('\n')
    started = False
    for l in lines[lines.index(marker):]:
        if l.strip().startswith('#'):
            if started:
                break
            continue
        if l.strip().startswith('rg '):
            started = True
            v50_cnt += 1
        elif started and l.strip() and not l.strip().startswith('rg '):
            break
ok(v50_cnt == 17, f'v50 块探针实测 {v50_cnt} == 注释 (17 probes;)（E8 计数改对）')

print('== 7. D1 三条命令 ==')
t0 = time.time()
r = subprocess.run([sys.executable, 'scripts/design-statecheck.py', '--check'],
                   cwd=REPO, capture_output=True, text=True)
t1 = time.time()
ok(r.returncode == 0 and 'D1 GREEN' in r.stdout, f'--check D1 GREEN（{t1 - t0:.3f}s < 2s）')
ok(t1 - t0 < 2, f'--check 运行时间 {t1 - t0:.3f}s < 2s')
r = subprocess.run([sys.executable, 'scripts/design-statecheck.py', '--mutate=ALL'],
                   cwd=REPO, capture_output=True, text=True)
ok(r.returncode == 0 and '/1 detected' not in r.stdout and 'MISSED' not in r.stdout,
   '--mutate=ALL 全部检出（清单驱动，数目以 MUTATIONS 为唯一源，不手写）')
mut_total = r.stdout.count('DETECTED')
ok(mut_total >= 1 and f'mutations: {mut_total}/{mut_total} detected' in r.stdout,
   f'--mutate=ALL 检出计数自洽（{mut_total}）')
r = subprocess.run([sys.executable, '-m', 'unittest', 'scripts/tests/test_design_statecheck.py'],
                   cwd=REPO, capture_output=True, text=True)
ok(r.returncode == 0, 'unittest OK')

print('== 7b. 账目层守卫（手写数字零容忍）==')
# 复核轮根因修正：spec/脚本/测试内不得出现会随清单增长过期的手写数字注释。
# 探针头 (17 probes;) 是唯一例外：它由 §6 的 17 == 17 生成回填断言锁住。
bads = {
    'scripts/design-statecheck.py': ['M1' + '–M' + '5', 'S1' + '–S' + '6', '个历史缺陷变异必须'],
    'scripts/tests/test_design_statecheck.py': ['M1' + '–M' + '5', 'S1' + '–S' + '6'],
    SPEC: ['5 个历史缺陷变异', '6 个历史缺陷变异', '(18 probes;', '(15 probes;'],
}
for p, needles in bads.items():
    t = (REPO / p).read_text(encoding='utf-8') if not p.startswith('scripts') else (REPO / p).read_text(encoding='utf-8')
    for n in needles:
        ok(n not in t, f'{p} 无手写数字注释 «{n}»')
# 变异清单一致性：spec 注册块只允许数字无关措辞；MUTATIONS 清单全量可执行
spec_t = rd(SPEC)
dsc_mut = subprocess.run([sys.executable, '-c',
                          'import importlib.util,pathlib;'
                          's=importlib.util.spec_from_file_location("m","scripts/design-statecheck.py");'
                          'm=importlib.util.module_from_spec(s);s.loader.exec_module(m);'
                          'print(len(m.MUTATIONS))'],
                         cwd=REPO, capture_output=True, text=True)
ok(dsc_mut.returncode == 0, 'MUTATIONS 可从脚本导出')
print(f'     MUTATIONS 清单长度 = {dsc_mut.stdout.strip()}（唯一源，报告引用此值不手写）')

print('== 7c. 验证代码不得写被验证物 ==')
# R3 轮修正：上轮同类面未扫净——单测的写入真实主稿修了，verify.py 的反向验证
# write_text 留下同型。本守卫用 AST 解析调用点（注释/字符串字面量不误报），
# 断言验证脚本与单测内零文件写入调用。
import ast as _ast

def _write_calls(path):
    src = Path(path).read_text(encoding='utf-8')
    tree = _ast.parse(src)
    hits = []
    for node in _ast.walk(tree):
        if isinstance(node, (_ast.FunctionDef,)):
            continue
        if isinstance(node, _ast.Call):
            fn = node.func
            name = fn.attr if isinstance(fn, _ast.Attribute) else (
                fn.id if isinstance(fn, _ast.Name) else '')
            if name in ('write_text', 'write_bytes', 'write', 'open'):
                hits.append(f'{name}@line{node.lineno}')
    return hits

for path in (Path(__file__), REPO / 'scripts/tests/test_design_statecheck.py'):
    calls = _write_calls(path)
    ok(not calls, f'{path.name} 无文件写入调用（AST 扫描）'
       + (f'：{calls}' if calls else ''))

print('== 8. git diff --check 与逐 hunk 清点 ==')
r = subprocess.run(['git', 'diff', '--check'], cwd=REPO, capture_output=True, text=True)
ok(r.stdout.strip() == '', f'git diff --check 干净（{r.stdout.strip()[:80]}）')
r = subprocess.run(['git', 'diff', '-U0', '--', MAIN, COMP, SPEC], cwd=REPO,
                   capture_output=True, text=True)
hunks = [l for l in r.stdout.splitlines() if l.startswith('@@')]
print(f'     diff hunk 数: {len(hunks)}（主稿 6 + 配套 1 + spec 3）')
for h in hunks:
    print('     ' + h)
r = subprocess.run(['git', 'status', '--porcelain'], cwd=REPO, capture_output=True, text=True)
print('     新增未跟踪文件:')
for l in r.stdout.splitlines():
    if l.startswith('??'):
        print('     ' + l)

print('== 9. 反向验证（把 §6.7 改回旧句必须红；全程内存注入，不写真实文档）==')
# R1 轮：回退目标为「E1 时代串」（删去新建替代继任半句）。
# 该形态下 S1 仍绿（替换继任句保留），必须由 S7（新建替代继任面）与
# S8（处置形态全集：放弃-新建替代缺出口）抓住——证明 R1 修正被门锁住。
# R3 轮修正：与单测同法，验证代码不得写被验证物——回退文本只进内存（Doc 注入），
# 真实主稿全程零写入；并用前后快照逐字节相等断言这一点。
main_text = (REPO / MAIN).read_text(encoding='utf-8')
before_snapshot = (REPO / MAIN).read_bytes()
NEW_R1 = R1_STRINGS[0][3]
OLD_R1 = R1_STRINGS[0][2]
assert main_text.count(NEW_R1) == 1
reverted = main_text.replace(NEW_R1, OLD_R1)
import importlib.util as _ilu
_spec = _ilu.spec_from_file_location('dsc_rv', REPO / 'scripts' / 'design-statecheck.py')
dsc = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(dsc)
d2 = dsc.Doc(reverted)
dele_bad = dsc.build_delegations(d2)
rows = dsc.build_rows()
scen_bad = dsc.run_scenarios(rows, d2, dele_bad)
reds = [s for s in scen_bad if not s['ok']]
red = any(s['scenario'] == 'S7' for s in reds) and any(
    s['scenario'] == 'S8_处置形态全集' for s in reds)
ok(red, '回退 §6.7 至 E1 时代串（内存注入）→ S7/S8 红')
for s in reds:
    print(f"     RED scenario {s['scenario']}: {s['detail'][:110]}")
# 对照：现行文档同一路径全绿（真实文件只读）
scen_good = dsc.run_scenarios(rows, dsc.Doc(main_text), dsc.build_delegations(dsc.Doc(main_text)))
ok(all(s['ok'] for s in scen_good), '现行文档同一路径（只读）全绿')
after_snapshot = (REPO / MAIN).read_bytes()
ok(after_snapshot == before_snapshot, '反向验证全程未写真实主稿（前后字节快照相等）')

print()
if FAILS:
    print(f'VERIFY FAIL（{len(FAILS)} 项）:')
    for f in FAILS:
        print(' -', f)
    sys.exit(1)
print('VERIFY ALL GREEN')
