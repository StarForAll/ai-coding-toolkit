#!/usr/bin/env python3
"""run-probes.py — spec 探针全量实跑（既有 77 条 + v50 收口新增 5 条 = 82 条）。

从 .trellis/spec/docs/index.md 的两个 bash 代码块中解析全部 rg 探针行，
逐条实跑并把命中行数与注释中的数字期望比对。注释期望分几类：
- `# N hits` / `# N lines` / `# N matching lines` / `# N occurrences`：精确命中数
- `# 0 hits`：零命中墓碑
- 无数字或说明性文本（`inspect` / `location scan` / 判域类）：登记实际命中数，不判失败
期望不适用（与现文事实不符）的按 verify 阶段修正原则处理：只在报告里登记，
不改期望值迁就旧文本；期望写错的已在本轮修正并注明原因。
"""

import re
import subprocess
import sys

SPEC = '.trellis/spec/docs/index.md'
lines = open(SPEC, encoding='utf-8').read().split('\n')

probes = []
in_block = False
for i, l in enumerate(lines, 1):
    if l.startswith('```bash'):
        in_block = True
        continue
    if l.startswith('```'):
        if in_block:
            in_block = False
        continue
    if in_block and l.startswith('rg '):
        probes.append((i, l))

print(f'parsed probes: {len(probes)}')
assert len(probes) == 84, f'expected 84 probes, got {len(probes)}'

fails, notes = [], []
for ln, probe in probes:
    m = re.match(r'^rg (-[nobs]+) ("[^"]*"|\'[^\']*\')\s+(.*)$', probe)
    if not m:
        fails.append(f'spec:{ln} cannot parse: {probe[:80]}')
        continue
    flags, pattern, rest = m.group(1), m.group(2), m.group(3)
    paths = []
    comment_at = None
    for tok in re.findall(r'"[^"]*"|\'[^\']*\'|[^\s]+', rest):
        if tok.startswith('#'):
            comment_at = rest.index('#')
            break
        paths.append(tok)
    # comment = rest[comment_at:]
    comment = rest[comment_at:] if comment_at is not None else ''
    # strip paths out of the "rest" to get comment: paths are tokens before '#'
    # run rg
    pat = pattern[1:-1]
    cmd = ['rg', flags, pat] + [p.strip('"\'') for p in paths]
    r = subprocess.run(cmd, capture_output=True, text=True)
    hits = [h for h in r.stdout.split('\n') if h]
    n = len(hits)
    if r.returncode not in (0, 1):
        fails.append(f'spec:{ln} rg error: {r.stderr.strip()[:100]}')
        continue
    # expectations with digits
    em = re.search(r'#\s*(\d+)\s*(hits?|lines|matching lines|occurrences)', comment)
    zero = re.search(r'#\s*0\s*hits', comment)
    if zero and not re.search(r'#\s*[1-9]', comment):
        status = 'OK(0)' if n == 0 else f'MISMATCH(got {n})'
        if n != 0:
            fails.append(f'spec:{ln} expected 0 hits, got {n}: {probe[:100]}')
    elif em:
        exp = int(em.group(1))
        if n != exp:
            fails.append(f'spec:{ln} expected {exp} hits, got {n}: {probe[:100]}')
        else:
            status = f'OK({n})'
    else:
        status = f'INFO({n})'  # judgement-type probe: record only
    print(f'  spec:{ln} {status:12s} {probe[:90]}')

print()
if fails:
    print(f'FAILED: {len(fails)}')
    for f in fails:
        print(' -', f)
    sys.exit(1)
print('ALL PROBES PASS')
