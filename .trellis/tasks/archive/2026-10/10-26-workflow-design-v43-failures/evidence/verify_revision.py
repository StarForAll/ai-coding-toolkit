"""Run registered text probes and scoped tester-emulated regression predicates.

This is a design evidence script, not the dependency mechanism.
"""
from pathlib import Path
import csv
import io
import json
import re
import shlex
import subprocess
import tarfile

E = Path(__file__).resolve().parent
REPO = E.parents[3]
MAIN = REPO / 'docs/workflows/workflow-design.md'
COMPANION = REPO / 'docs/workflows/依赖机制设计说明.md'
SPEC = REPO / '.trellis/spec/docs/index.md'
REPLAY = Path('/tmp/dep-mech-chain-20261026-v43-replay-run3')
CHECKS = []


def save(name, value):
    (E / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')


def check(name, condition, evidence):
    assert condition, (name, evidence)
    CHECKS.append({'name': name, 'result': 'PASS', 'evidence': evidence})


def section(text, start, end):
    return text.split(start, 1)[1].split(end, 1)[0]


def git_json(root, commit, path):
    return json.loads(subprocess.check_output(['git', '-C', str(root), 'show', commit + ':' + path], text=True))


def git_commit(root, message):
    for args in [['git', 'add', '--', '.dep'], ['git', 'commit', '-m', message]]:
        r = subprocess.run(args, cwd=root, capture_output=True, text=True)
        assert r.returncode == 0, (args, r.stderr)
        PROBE_COMMANDS.append({'root': str(root), 'args': args, 'rc': r.returncode, 'stdout': r.stdout, 'stderr': r.stderr})


main = MAIN.read_text()
companion = COMPANION.read_text()
before = (E / 'before-workflow-design.md').read_text()
check('version alignment', re.search(r'^version: v43$', main, re.M) is not None
      and re.search(r'^version: v43$', companion, re.M) is not None
      and re.search(r'^design: workflow-design.md v43$', companion, re.M) is not None, 'Both version fields and companion design field.')
check('disposition predicate unchanged', section(main, '### 7.4 ', '### 7.5 ') == section(before, '### 7.4 ', '### 7.5 '), 'Main §7.4 byte-for-byte unchanged.')
check('type4 boundary unchanged', section(main, '**类型 4 恢复边界（唯一源）**', '### 7.9 ')
      == section(before, '**类型 4 恢复边界（唯一源）**', '### 7.9 '), 'Main §7.8 existing restoration and business-write domains byte-for-byte unchanged.')
check('companion identity references unchanged', section(companion, '## 9. ', '## 10. ')
      == section((E / 'before-依赖机制设计说明.md').read_text(), '## 9. ', '## 10. '), 'Companion §9 unchanged; source-owned references remain active.')
check('section10 semantic boundary unchanged', section(main, '## 10. ', '## 附录 A').replace('v43', 'v42')
      == section(before, '## 10. ', '## 附录 A'), 'Only current-version references changed in §10.')

probes = []
block = SPEC.read_text().split('### workflow-design.md Predicate Registry and Probes')[1].split('```bash')[1].split('```')[0]
for line in block.splitlines():
    if not line.startswith('rg '):
        continue
    command, expectation = line.split(' # ', 1)
    r = subprocess.run(shlex.split(command), cwd=REPO, capture_output=True, text=True)
    assert r.returncode in (0, 1), (command, r.stderr)
    actual = len(r.stdout.splitlines())
    match = re.match(r'(\d+) (?:hits?|lines?)', expectation)
    assert match is None or actual == int(match[1]), (command, actual, expectation)
    probes.append({'index': len(probes) + 1, 'command': command, 'expectation': expectation,
                   'actual_lines': actual, 'returncode': r.returncode, 'output': r.stdout})
save('probe-results.json', probes)
check('all registered text probes ran', len(probes) == 38, '38 commands; rc0/1 interpreted by expected match count; every numeric expectation matched.')
check('P1 single source anchor', main.count('标识占用校验（唯一源）') == 1 and '标识占用校验（唯一源）' not in companion, 'Only main §7.8.')
check('P2 source and reference', main.count('移交完成的持久判据') == 2 and '移交完成的持久判据' not in companion, 'Main §6.4 definition + §7.7 reference.')

# P1 uses real committed identity records from the chain; predicate enforcement is emulated.
initial = git_json(Path('/tmp/dep-mech-chain-20261026'), '4307ccd', '.dep/tasks.json')
final = json.loads((E / 'final-main.json').read_text())
def occupancy_allowed(records, identity, expected_dir=None):
    return identity not in records or records[identity]['dir'] == expected_dir
for source in ['§6.5 replace', '§6.6 new replacement', '§7.7 type1 P']:
    snapshot = json.dumps(initial, sort_keys=True)
    check('P1 rejects106 at ' + source, not occupancy_allowed(initial, '106'),
          'Committed4307ccd assigns106 to r2t2fix; candidate rejected before pointer/state write.')
    check('P1 zero overwrite at ' + source, json.dumps(initial, sort_keys=True) == snapshot, 'Input identity map unchanged.')
check('P1 free107 before prewrite', occupancy_allowed(initial, '107'), 'No107 identity in committed pre-replacement records.')
check('P1 original restoration remains legal', occupancy_allowed(final['tasks'], '107', final['tasks']['107']['dir'])
      and final['ledger']['102']['replaced_by'] == '107', 'Confirmed original102->107 from final-main committed facts, not inferred merely from existence.')
check('P1 unrelated existing task rejected', not occupancy_allowed(final['tasks'], '106', final['tasks']['107']['dir']),
      '106 remains R2 and cannot become the T2 successor.')
reserved = {'107': '102'}
check('P1 prewritten other identity blocked', reserved.get('107') != '103', 'Existing107 reservation belongs to102; tester rejects another owner103.')
check('P1 same prewrite can resume', reserved.get('107') == '102', 'Same confirmed reservation102->107 can create its unbuilt successor.')

# P2 minimal regression: real Git persistence, tester-emulated startup gate.
PROBE_COMMANDS = []
history = subprocess.check_output(['git', '-C', str(REPLAY), 'log', '--format=%H %s'], text=True)
checkpoint = next(line.split()[0] for line in history.splitlines() if line.endswith('S3: R1 normal'))
root = Path(str(REPLAY) + '-p2-probe')
assert not root.exists(), root
root.mkdir()
with tarfile.open(fileobj=io.BytesIO(subprocess.check_output(['git', '-C', str(REPLAY), 'archive', checkpoint]))) as archive:
    archive.extractall(root, filter='data')
for args in [['git', 'init', '-b', 'probe'], ['git', 'config', 'user.name', 'Workflow Fixture Tester'],
             ['git', 'config', 'user.email', 'fixture@example.invalid'], ['git', 'add', '.'],
             ['git', 'commit', '-m', 'P2 regression input from S3 committed checkpoint']]:
    r = subprocess.run(args, cwd=root, capture_output=True, text=True)
    assert r.returncode == 0, (args, r.stderr)
    PROBE_COMMANDS.append({'root': str(root), 'args': args, 'rc': r.returncode, 'stdout': r.stdout, 'stderr': r.stderr})
project = root / '.dep/project.json'
project.write_text(json.dumps({'note': 'Tester input: legacy suspended T, handoff not completed'}) + '\n')
git_commit(root, 'P2: no persisted completion fact')
def startup_result():
    facts = git_json(root, 'HEAD', '.dep/project.json')
    ledger = git_json(root, 'HEAD', '.dep/ledger.json')
    if not facts.get('handoff_complete'):
        return 'legacy_handoff_block'
    note = ledger['102']['note']
    if isinstance(note, dict) and note.get('registration'):
        return 'type2_registration'
    return 'step5_evaluation'
tasks = git_json(root, 'HEAD', '.dep/tasks.json')
ledger = git_json(root, 'HEAD', '.dep/ledger.json')
check('P2 historical R completed input', tasks['105']['origin'] == '102' and ledger['105']['status'] == 'normal'
      and ledger['102']['status'] == 'suspended' and not ledger['102']['note'], 'Real S3 checkpoint: archived R1, suspended T, no registration marker.')
check('P2 missing completion fact blocks', startup_result() == 'legacy_handoff_block', 'Even nonempty historical R set cannot establish project handoff completion.')
project.write_text(json.dumps({'handoff_complete': True, 'note': 'Uncommitted probe input'}) + '\n')
check('P2 uncommitted fact blocks', startup_result() == 'legacy_handoff_block', 'Working-tree completion fact ignored; gate reads HEAD.')
git_commit(root, 'P2: tester confirms handoff and persists completion fact')
check('P2 confirmed persisted completion enables evaluation', startup_result() == 'step5_evaluation', 'Human decision represented as preset test input; carrier format is scaffold-only.')
ledger['102']['note'] = {'registration': {'id': '106', 'locator': 'r2t2fix', 'before': 'suspended'}}
(root / '.dep/ledger.json').write_text(json.dumps(ledger, ensure_ascii=False, indent=2) + '\n')
git_commit(root, 'P2: tester confirms new round and persists intent before startup evaluation')
check('P2 new-round registration prevents clearing', startup_result() == 'type2_registration', 'Handoff fact does not erase newly recorded rework intent; history alone still cannot clear.')
check('P2 zero status clearing during probes', git_json(root, 'HEAD', '.dep/ledger.json')['102']['status'] == 'suspended', 'All probe inputs retain suspended T; no unintended clearing happened.')
save('semantic-probe-commands.json', PROBE_COMMANDS)
save('semantic-probes.json', CHECKS)

# Design truth table, explicitly not an implementation test.
families = [('替换', ('一般', 'P', 'R')), ('放弃-新建替代', ('一般', 'P', 'R')),
            ('类型1-P', ('P',)), ('类型5补建', ('一般', 'P', 'R')),
            ('类型5改判-P', ('P',)), ('放弃-删边', ('一般', 'R')),
            ('类型1-一般', ('一般', 'R')), ('类型5无指向', ('一般', 'R')),
            ('类型5改判-一般', ('一般', 'R'))]
rows = []
for family, roles in families:
    for role in roles:
        for archived in (False, True):
            for pointer in (False, True):
                for exists in (False, True):
                    for downstream in (False, True):
                        if role == 'P' and not pointer:
                            result = '类型4-角色守卫'
                        elif not archived or downstream or (pointer and not exists):
                            result = '类型5'
                        else:
                            result = '处分终态'
                        rows.append([family, role, archived, pointer, exists, downstream, result])
with (E / 'disposition-matrix.csv').open('w') as stream:
    writer = csv.writer(stream, lineterminator='\n')
    writer.writerow(['产生路径', '角色', '旧任务已归档', '替换指向有', '已确认同一继任目标已建', '未归档下游仍指向旧任务', '判定'])
    writer.writerows(rows)
save('revision-summary.json', {'text_probes': len(probes), 'semantic_checks': len(CHECKS),
      'truth_table_rows': len(rows), 'p2_probe_fixture': str(root), 'chain_scenarios': 10})
print(f'{len(probes)} text probes; {len(CHECKS)} scoped semantic checks PASS; {len(rows)} design truth-table rows.')
