"""Verify v50 against the frozen v49 hashes and explicit review axes."""
import csv
import difflib
import hashlib
import json
import re
import shlex
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
REC = Path(__file__).resolve().parent
MAIN = 'docs/workflows/workflow-design.md'
COMP = 'docs/workflows/依赖机制设计说明.md'
SPEC = '.trellis/spec/docs/index.md'
GUIDE = '.trellis/spec/guides/design-review-thinking-guide.md'
FILES = (MAIN, COMP, SPEC, GUIDE)
BASE = json.loads((REC / 'followup-v50-baseline.json').read_text())
CURRENT = {p: (ROOT / p).read_text() for p in FILES}
ROWS = list(csv.DictReader((REC / 'fix-manifest-v50.tsv').open(), delimiter='\t'))
FAIL = []


def check(ok, message):
    print(('PASS ' if ok else 'FAIL ') + message)
    if not ok:
        FAIL.append(message)


def ln(path, phrase):
    hits = [n for n, line in enumerate(CURRENT[path].splitlines(), 1) if phrase in line]
    if not hits:
        raise AssertionError((path, phrase))
    return hits[0]


def table(text, header):
    lines = text.splitlines()
    start = lines.index(header) + 2
    out = []
    while start < len(lines) and lines[start].startswith('|'):
        out.append(lines[start])
        start += 1
    return out


def manifest_and_reconstruct():
    check(len({x['ID'] for x in ROWS}) == len(ROWS), 'manifest IDs unique')
    restored = dict(CURRENT)
    for row in ROWS:
        path, old, new = row['文件'], row['old'], row['new']
        text = CURRENT[path]
        insertion = old.startswith('<INSERTION')
        check(bool(row['验收位']) and bool(new), row['ID'] + ' has concrete acceptance position')
        # An old prefix can survive only as part of the verified complete new text.
        count_new = text.count(new)
        old_masked = 0 if insertion else text.replace(new, '', 1).count(old)
        check(count_new == 1 and old_masked == 0,
              f"{row['ID']} {path}:{ln(path, new.splitlines()[0])} new={count_new} masked-old={old_masked}")
    # A byte-for-byte reverse replay must recover all four frozen v49 source hashes.
    # This detects omitted edits, stale new strings and record/probe drift.
    for row in reversed(ROWS):
        path, old, new = row['文件'], row['old'], row['new']
        if restored[path].count(new) != 1:
            check(False, 'reverse replay cannot uniquely locate ' + row['ID'])
            continue
        restored[path] = restored[path].replace(new, '' if old.startswith('<INSERTION') else old, 1)
    for path in FILES:
        actual = hashlib.sha256(restored[path].encode()).hexdigest()
        check(actual == BASE['sha256'][path], f'frozen v49 reverse SHA-256 {path}: {actual}')
    return restored


def structural_checks(before):
    headers = {
        'family': ('| 族 | 内容 | 受 §7.5 建边限制 |', 4),
        'matrix': ('| 写入路径 | 写入时点 | 指向终值 | 说明 / 原因终值 | 依据 |', 14),
        'combination': ('| 组合 | 判定 | 出口 |', 12),
        'transition': ('| # | 从 | 到 | 触发 | 写入者 / 说明 |', 7),
        'window': ('| 窗口 | 已提交识别项 / 残留 | 恢复 |', 9),
    }
    for name, (header, number) in headers.items():
        rows = table(CURRENT[MAIN], header)
        check(len(rows) == number, f'{name} data rows={len(rows)} expected={number}')
        if name in ('matrix', 'transition', 'window'):
            check(rows == table(before[MAIN], header), f'{name} rows byte-identical to v49')
    for path in (MAIN, COMP):
        a, b = table(before[path], headers['combination'][0]), table(CURRENT[path], headers['combination'][0])
        changed = [i + 1 for i, (x, y) in enumerate(zip(a, b)) if x != y]
        target = next(i + 1 for i, row in enumerate(a) if '未归档 + 挂起（任意前置）' in row)
        check(len(a) == len(b) == 12 and changed == [target], f'{path} combination changes={changed}; only hanging row={target}')
        check(all(x == y for i, (x, y) in enumerate(zip(a, b), 1) if i != target), f'{path} other 11 combination rows unchanged')
    check('version: v50\n' in CURRENT[MAIN] and 'version: v50\n' in CURRENT[COMP], 'two versions v50')
    check(CURRENT[COMP].splitlines()[3] == 'design: workflow-design.md v50', 'companion current design pin v50')
    check('### v50\n' in CURRENT[MAIN] and '## 38. 本版修订（v50）' in CURRENT[COMP], 'version histories present')
    bad = []
    for path in FILES:
        a, b = before[path].splitlines(), CURRENT[path].splitlines()
        for tag, _, _, start, end in difflib.SequenceMatcher(a=a, b=b, autojunk=False).get_opcodes():
            if tag in ('insert', 'replace'):
                for n in range(start, end):
                    if b[n].count('（') != b[n].count('）') or b[n].count('(') != b[n].count(')'):
                        bad.append(f'{path}:{n + 1}')
    check(not bad, 'changed-line parentheses balanced: ' + repr(bad))


def archive_sites():
    text = CURRENT[MAIN]
    start = text.index('  5. **替换/放弃未完成**')
    end = text.index('- **“正常”的写入者**', start)
    block = text[start:end]
    build = block[block.index('**补建**'):block.index('**改判为放弃**')]
    change = block[block.index('**改判为放弃**'):block.index('**无替换指向**')]
    general, project = change.split('**项目层任务 P**', 1)
    no_pointer = block[block.index('**无替换指向**'):block.index('**逐窗口**')]
    cases = [
        ('补建', build, '最后归档旧任务'),
        ('改判放弃-一般', general, '最后归档旧任务'),
        ('改判放弃-P', project, '最后归档旧任务'),
        ('无替换指向', no_pointer, '补齐下游删边与旧任务归档'),
    ]
    out = ['branch\tcall_count\tguarded_count\tposition']
    for name, section, action in cases:
        calls, guards = section.count(action), section.count(action + '（已归档者不重复归档）')
        check(calls == guards == 1, f'archive site {name}: action={calls} guard={guards}')
        branch_anchor = {'补建': '**补建**', '改判放弃-一般': '**改判为放弃**',
                         '改判放弃-P': '**改判为放弃**', '无替换指向': '**无替换指向**'}[name]
        position = text.count('\n', 0, start + block.index(branch_anchor)) + 1
        check(action + '（已归档者不重复归档）' in text.splitlines()[position - 1],
              f'archive site source row {name}: {MAIN}:{position}')
        out.append(f'{name}\t{calls}\t{guards}\t{MAIN}:{position}')
    check(len(re.findall('最后归档旧任务|补齐下游删边与旧任务归档', block)) == 4, 'type-5 terminal archive action set exactly four sites')
    check(text.count('已归档者不重复归档') == 5, 'four type-5 guards plus type-1 counterpart=5 occurrences')
    (REC / 'archive-sites-v50.tsv').write_text('\n'.join(out) + '\n')


def probes(before):
    text = CURRENT[SPEC]
    block = text[text.index('Probes — run after'):text.index('\n#### v46 probe table')]
    commands = [x.strip() for x in block.splitlines() if re.match(r'^rg -(n|o) ', x.strip())]
    result = ['spec_line\tmode\tpattern\texpected\tactual\texit\tjudgment']
    new_start = text.index('# v50 additions')
    new_block = text[new_start:text.index(chr(96)*3, new_start)]
    check(len([x for x in new_block.splitlines() if x.startswith('rg ')]) == 16, 'v50 probe group contains exactly 16 probes')
    for line in commands:
        lex = shlex.shlex(line, posix=True)
        lex.whitespace_split, lex.commenters = True, '#'
        args = list(lex)
        mode, pattern, paths = args[1], args[2], args[3:]
        check(all(p in (MAIN, COMP) for p in paths), 'probe scope limited to two design documents')
        proc = subprocess.run(args[:2] + ['--'] + args[2:], cwd=ROOT, capture_output=True, text=True)
        actual = len(proc.stdout.splitlines())
        comment = line.split('#', 1)[1]
        match = re.search(r'\b(\d+)\s+(?:matching\s+)?(?:hits?|lines?|occurrences?)\b|=\s*(\d+)', comment)
        if match:
            expected = int(match.group(1) or match.group(2))
            judgment = 'numeric-comment'
        else:
            # Location/domain probes have no numeric claim. Require the inspected
            # v49 hit count to stay unchanged, and emit every hit for domain review.
            rx = re.compile(pattern)
            expected = sum(bool(rx.search(x)) for p in paths for x in before[p].splitlines())
            judgment = 'location/domain; unchanged vs frozen v49'
        check(proc.returncode in (0, 1) and actual == expected, f'probe {ln(SPEC, line)} {mode} actual={actual} expected={expected}: {pattern}')
        result.append(f'{ln(SPEC, line)}\t{mode}\t{pattern}\t{expected}\t{actual}\t{proc.returncode}\t{judgment}')
    (REC / 'probe-results-v50.tsv').write_text('\n'.join(result) + '\n')
    check(len(commands) >= 70, f'all registered probes executed: {len(commands)}')


def reference_and_scenario_checks():
    main = CURRENT[MAIN]
    second = main[main.index('**第二段 挂起**。'):main.index('**第三段 非挂起**。')]
    rows = table(second, '| 当前情况 | 下一步 |')
    check(len(rows) == 4, 'second-stage table remains four rows')
    check('R 自身挂起时以 R 为“对应 T”回到本段并匹配各行' in rows[0], 'row1 recursive rework context hits same table')
    for phrase in ['前置本身挂起时，以它为“对应 T”回到本段并完整匹配本表',
                   '有未归档 R 按第 1 行进入 R',
                   '满足 §6.4 第 5 步按第 2 行清除该前置的挂起',
                   '无返工任务记录按第 4 行处理',
                   '递归处理后仍无就绪任务时报告阻塞']:
        check(phrase in rows[2], 'row3 reference/action: ' + phrase)
    check('找不到返工任务记录' in rows[3] and '类型 2' in rows[3], 'recursive no-record input hits row4/type2')
    source = main[main.index('### 6.4 返工'):main.index('### 6.5 替换')]
    check('5. **挂起清除（唯一判据）**' in source and '无未完成返工登记' in source and 'T 前置集合全部正常' in source, 'recursive clearing points to unchanged §6.4 step5 guard')
    check('递归只切换本次判定上下文，不据此改写当前任务指针' in second, 'recursive context leaves pointer contract explicit')
    scenario = next(x for x in main.splitlines() if x.startswith('**自检**：'))
    steps = ['Q 自身挂起且有未归档 R_Q', 'R_T 完成后不清 T 挂起', '以 Q 为上下文进入 R_Q',
             'R_Q 完成后按 §6.4 第 5 步清 Q 挂起', 'Q 完成后按 §6.4 第 5 步评估清 T 挂起']
    places = [scenario.index(x) for x in steps]
    check(places == sorted(places), 'self-check orders Q suspension → R_T end → R_Q → Q clear → Q complete → T evaluation')
    check('开工该未完成前置' not in scenario, 'self-check does not open suspended Q before routing its R_Q')
    report = (REC / 'review-report-v50.md').read_text()
    s3 = report[report.index('## S3 '):report.index('## 修改面')]
    state_rows = table(s3, '| T 的前置状态 | 有未归档 R_T（返工未结束） | 无未归档 R_T（返工已结束） |')
    check(len(state_rows) == 6 and all(len(r.split('|')) == 5 and all(c.strip() for c in r.split('|')[1:-1]) for r in state_rows), 'S3 six states × two rework contexts = 12 populated cells')
    required = [('不可达', '第 5 步'), ('R_T', '下沉'), ('§7.4', '§7.4'),
                ('类型 3', '类型 3'), ('§4.3', '第 5 步'), ('行 1', '类型 2')]
    for index, (row, expected) in enumerate(zip(state_rows, required), 1):
        cells = row.split('|')[2:4]
        check(all(token in cell for token, cell in zip(expected, cells)),
              f'S3 state row {index}: both cells name an action or unreachable condition')


def section_ranges(path):
    lines = CURRENT[path].splitlines()
    out = {}
    for i, line in enumerate(lines):
        match = re.match(r'^(#{2,3}) (\d+(?:\.\d+)?)(?:\.\s|\s)', line)
        if not match:
            continue
        level, section = len(match.group(1)), match.group(2)
        end = next((j for j in range(i+1, len(lines)) if re.match(r'^#{1,'+str(level)+r'} ', lines[j])), len(lines))
        out[section] = (i + 1, end)
    return out


def record_checks():
    main, comp = CURRENT[MAIN], CURRENT[COMP]
    segments = [(MAIN, main[main.index('### v50\n'):main.index('### v49\n')]),
                (COMP, comp[comp.index('## 38. 本版修订（v50）'):]),
                (MAIN, main[main.index('### v49\n'):main.index('### v48\n')]),
                (COMP, comp[comp.index('## 37. 本版修订（v49）'):comp.index('## 38. 本版修订（v50）')])]
    locations, claims = [], []
    ranges = {p: section_ranges(p) for p in (MAIN, COMP)}
    for record_path, segment in segments:
        for line in segment.splitlines():
            match = re.search(r'已同步（([^:]+\.md):(\d+)）', line)
            if not match:
                continue
            path, number = match.group(1), int(match.group(2))
            source = CURRENT[path].splitlines()
            check(1 <= number <= len(source), f'record line exists {path}:{number}')
            label = line[:match.start()]
            sec = re.search(r'§(\d+(?:\.\d+)?)', label)
            if sec and path in ranges:
                bounds = ranges[path].get(sec.group(1))
                check(bool(bounds) and bounds[0] <= number <= bounds[1], f'record section §{sec.group(1)} contains {path}:{number}')
            locations.append((record_path, label, path, number))
            # Use the actual non-record source line as the exact grep-F claim.
            claim = source[number - 1]
            proc = subprocess.run(['rg', '-n', '-F', '--', claim, path], cwd=ROOT, capture_output=True, text=True)
            check(proc.returncode == 0, f'D4 literal source claim {path}:{number}')
            claims.append((path, number, claim))
    check(len(claims) >= 20, f'D4 record/body literal claims={len(claims)}')
    notes = (REC / 'fix-notes-v50.md').read_text()
    for row in ROWS:
        record = next((l for l in notes.splitlines() if l.startswith('| ' + row['ID'] + ' |')), '')
        match = re.search(r'\| ([^ |]+\.md):(\d+) \|', record)
        check(bool(match), f'fix-notes generated location {row["ID"]}')
        if match:
            path, number = match.group(1), int(match.group(2))
            first = row['new'].splitlines()[0]
            check(path == row['文件'] and (first in CURRENT[path].splitlines()[number-1] or row['锚点'] == 'v50 regression probes'), f'fix-notes anchor resolves {row["ID"]}')
    (REC / 'd4-record-claims-v50.tsv').write_text('path\tline\tclaim\n' + '\n'.join(f'{p}\t{n}\t{c}' for p, n, c in claims) + '\n')
    check('§9.1第二段（M5，唯一规则源）' in main and '§8.4（M6）为引用式接手摘要' in main, 'v49 source/copy role corrected')


def final_checks():
    proc = subprocess.run(['git', 'diff', '--check'], cwd=ROOT, capture_output=True, text=True)
    check(proc.returncode == 0, 'git diff --check: ' + (proc.stdout + proc.stderr).strip())
    status = subprocess.check_output(['git', '-c', 'core.quotepath=false', 'status', '--porcelain=v1', '--untracked-files=all'], cwd=ROOT, text=True)
    prefix = str(REC.relative_to(ROOT)) + '/'
    preexisting = {'check.jsonl', 'design.md', 'implement.jsonl', 'implement.md', 'prd.md', 'task.json'}
    metadata = {str(REC.parent.relative_to(ROOT) / p) for p in preexisting}
    baseline_time = (REC / 'followup-v50-baseline.json').stat().st_mtime_ns
    older = all((ROOT / p).stat().st_mtime_ns <= baseline_time for p in metadata)
    check(older and ('?? ' + str(REC.parent.relative_to(ROOT)) + '/') in BASE['git_status'],
          'six untracked task metadata files predate frozen v50 baseline (timestamp evidence)')
    outside = [line[3:] for line in status.splitlines() if line[3:] not in FILES
               and not line[3:].startswith(prefix) and line[3:] not in metadata]
    check(not outside, 'source/research writes scoped; pre-existing metadata enumerated separately: ' + repr(outside))
    for file, expected in [('review-report.md', BASE['review_v1_sha256']), ('review-report-v2.md', BASE['review_v2_sha256'])]:
        check(hashlib.sha256((REC/file).read_bytes()).hexdigest() == expected, file + ' preserved byte-for-byte')
    task = json.loads((REC.parent / 'task.json').read_text())
    check(task.get('status') == 'in_progress', 'Active task remains in_progress')
    check(subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip() == BASE['head'], 'HEAD unchanged; no commit performed')
    digests = {p: hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in FILES}
    (REC/'final-sha256-v50.json').write_text(json.dumps(digests, ensure_ascii=False, indent=2) + '\n')
    (REC/'final-stat-v50.txt').write_text(subprocess.check_output(['git','diff','--stat'],cwd=ROOT,text=True))


def main():
    before = manifest_and_reconstruct()
    structural_checks(before)
    archive_sites()
    probes(before)
    reference_and_scenario_checks()
    record_checks()
    final_checks()
    print('RESULT ' + (f'FAIL ({len(FAIL)})' if FAIL else 'all checks passed'))
    (REC/'verify-v50-failures.txt').write_text('\n'.join(FAIL) + '\n' if FAIL else 'none\n')
    raise SystemExit(bool(FAIL))


if __name__ == '__main__':
    main()
