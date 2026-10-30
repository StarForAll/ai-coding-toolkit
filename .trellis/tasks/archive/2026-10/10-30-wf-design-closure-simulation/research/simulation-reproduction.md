# 模拟重建材料

仅供重建本次实验，不是正式 wf 实现。将下列同名代码块保存到一个新建的 /tmp/wf-closure-sim-<唯一后缀>/ 根；不要在作者仓库执行。

先运行 setup，再保存三个脚本至该临时根，并运行 /softwares/python/bin/python3 <临时根>/run_experiment.py。setup 隔离临时仓库的全局 ignore，不修改用户全局设置。

## setup

```python
from pathlib import Path
import json, subprocess
ROOT = Path("/tmp/wf-closure-sim-<替换唯一后缀>")
assert str(ROOT).startswith("/tmp/wf-closure-sim-")
ROOT.mkdir(exist_ok=False)
(ROOT / "evidence").mkdir()
project = ROOT / "project"
files = json.loads('{".gitignore": "__pycache__/\\n.wf/runtime/\\n", ".wf/baseline.md": "# Simulation baseline\\nInventory quantities are integers. This fixture explores negative-value validation.\\nScope: local Python module and tests; no external services or deployment.\\n", ".wf/project-config.json": "{\\"simulation_only\\": true, \\"validation_command\\": [\\"-m\\", \\"unittest\\", \\"discover\\", \\"-s\\", \\"tests\\", \\"-v\\"]}\\n", "src/quantity.py": "def validate_quantity(value):\\n    return value\\n", "tests/test_quantity.py": "import unittest\\nfrom src.quantity import validate_quantity\\n\\n\\nclass QuantityContract(unittest.TestCase):\\n    def test_zero_is_valid(self):\\n        self.assertEqual(validate_quantity(0), 0)\\n\\n    def test_positive_is_valid(self):\\n        self.assertEqual(validate_quantity(3), 3)\\n\\n    def test_negative_is_rejected(self):\\n        with self.assertRaises(ValueError):\\n            validate_quantity(-1)\\n"}')
for name, text in files.items():
    path = project / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
subprocess.run(["git", "init", "--initial-branch=main", str(project)], check=True)
subprocess.run(["git", "-C", str(project), "config", "--local", "core.excludesfile", "/dev/null"], check=True)

```

## control.py

SHA-256: 7d6cfff8a7a97d70be9a48badd7689a9c442e8782c81665241aa25fd1ebf192b

```python
#!/usr/bin/env python3
"""Disposable partial wf control simulation; not a product CLI."""
import argparse
import fnmatch
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('root', type=Path)
    parser.add_argument('operation')
    parser.add_argument('task')
    parser.add_argument('--data', default='{}')
    args = parser.parse_args()
    root = args.root.resolve()
    data = json.loads(args.data)
    tasks = root / '.wf/tasks'
    tasks.mkdir(parents=True, exist_ok=True)
    path = tasks / (args.task + '.json')
    runtime = root / '.wf/runtime'
    runtime.mkdir(exist_ok=True)
    pointer = runtime / 'current'

    def fail(code, fact, exit_hint):
        print(json.dumps({'tier': 'blocked', 'reason': code, 'fact': fact, 'next': exit_hint}))
        raise SystemExit(2)

    def git(*values):
        return subprocess.run(['git', *values], cwd=root, text=True, capture_output=True, check=True).stdout

    def digest(rel):
        p = root / rel
        if not p.exists():
            return {'exists': False}
        return {'exists': True, 'mode': p.stat().st_mode, 'sha256': hashlib.sha256(p.read_bytes()).hexdigest()}

    def snapshot(task):
        files = set(task['paths']) | {'.wf/baseline.md', '.wf/project-config.json'} | set(task.get('curation', []))
        return {rel: digest(rel) for rel in sorted(files)}

    def control_path(rel):
        return rel.startswith(('.wf/tasks/', '.wf/archive/'))

    def clean_business():
        dirty = [line[3:] for line in git('status', '--porcelain').splitlines() if not control_path(line[3:])]
        if dirty:
            fail('DIRTY_WORKSPACE', dirty, 'Handle the fixture task paths explicitly; do not stash or include other work.')

    def records():
        return [json.loads(p.read_text()) for p in tasks.glob('*.json')]

    op = args.operation
    if op == 'new':
        if path.exists():
            fail('DUPLICATE', args.task, 'Choose another fixture task id.')
        task = {'id': args.task, 'state': 'not_started', 'phase': 'Plan', 'paused': False, 'paths': data['paths'], 'approved': False, 'approval_source': None, 'curation': [], 'check': None, 'simulation_only': True}
    else:
        task = json.loads(path.read_text())
    result = {'tier': 'pass', 'operation': op, 'task': args.task, 'pid': os.getpid(), 'simulation_only': True}

    if op == 'approve':
        if data.get('authority') != 'SIMULATED_HUMAN':
            fail('AUTHORITY_REQUIRED', 'No human approval is inferred.', 'Supply explicit fixture authority; this is not real human approval.')
        task['approved'] = True
        task['approval_source'] = 'SIMULATED_HUMAN'
    elif op == 'start':
        if not task['approved']:
            fail('PLAN_UNAPPROVED', 'Urgency does not change approval.', 'Approve the current fixture plan.')
        if task['state'] != 'not_started':
            fail('BAD_STATE', task['state'], 'Resume a paused task instead.')
        if any(t['state'] == 'running' and not t['paused'] for t in records()):
            fail('EXECUTION_CANDIDATE_EXISTS', 'Another fixture task is running.', 'Pause the current task after handling its worktree.')
        clean_business()
        task.update(state='running', phase='Execute', base=git('rev-parse', 'HEAD').strip())
        pointer.write_text(args.task)
    elif op == 'load':
        index = root / '.wf/spec/index.md'
        matches = {}
        for name in re.findall(r'\[[^]]+\]\(([^)]+)\)', index.read_text()):
            rel = str(Path('.wf/spec') / name)
            content = (root / rel).read_text()
            patterns = re.findall(r'^  - (.+)$', content, re.M)
            if any(fnmatch.fnmatchcase(p, pattern) for p in task['paths'] for pattern in patterns):
                matches[rel] = digest(rel)
                print(content)
        task['curation'] = sorted(set(task['curation']) | set(matches))
        receipt = {'session': data['session'], 'files': matches, 'pid': os.getpid()}
        (runtime / (args.task + '-' + data['session'] + '.json')).write_text(json.dumps(receipt))
        result['loaded'] = sorted(matches)
    elif op == 'check':
        if task['state'] != 'running' or task['paused']:
            fail('NOT_EXECUTING', task['state'], 'Resume the fixture task first.')
        changed = set(git('diff', '--name-only').splitlines()) | set(git('diff', '--cached', '--name-only').splitlines())
        changed.update(git('ls-files', '--others', '--exclude-standard').splitlines())
        outside = sorted(p for p in changed if not control_path(p) and p not in task['paths'])
        if outside:
            fail('OUT_OF_SCOPE', outside, 'Return to Plan; do not automatically widen the allowlist.')
        receipt_path = runtime / (args.task + '-' + data['session'] + '.json')
        if task['curation']:
            if not receipt_path.exists():
                fail('SPEC_UNREAD', task['curation'], 'Read the current spec in this simulated session.')
            receipt = json.loads(receipt_path.read_text())
            if any(receipt['files'].get(p) != digest(p) for p in task['curation']):
                fail('SPEC_CHANGED', task['curation'], 'Reload the current full spec before checking.')
        before = snapshot(task)
        command = [sys.executable, '-m', 'unittest', 'discover', '-s', 'tests', '-v']
        test = subprocess.run(command, cwd=root, text=True, capture_output=True)
        result.update(command=command, test_exit=test.returncode, test_output=test.stdout + test.stderr)
        task['check'] = {'status': 'pass' if test.returncode == 0 else 'fail', 'objects': before}
        if before != snapshot(task):
            fail('OBJECT_CHANGED', 'Checked content changed during the command.', 'Run the affected check again.')
        task['phase'] = 'Check'
        if test.returncode:
            path.write_text(json.dumps(task, indent=2))
            print(json.dumps(result))
            raise SystemExit(3)
    elif op == 'pause':
        if data.get('authority') != 'SIMULATED_HUMAN':
            fail('AUTHORITY_REQUIRED', 'Pause is a fixture human decision.', 'Supply explicit fixture authority.')
        clean_business()
        task['paused'] = True
        task['handoff'] = {'goal': data['goal'], 'next': data['next'], 'head': git('rev-parse', 'HEAD').strip()}
        if pointer.exists():
            pointer.unlink()
    elif op == 'resume':
        if data.get('authority') != 'SIMULATED_HUMAN':
            fail('AUTHORITY_REQUIRED', 'Pause cannot be cleared by inference.', 'Supply explicit fixture authority.')
        clean_business()
        if any(t['id'] != args.task and t['state'] == 'running' and not t['paused'] for t in records()):
            fail('EXECUTION_CANDIDATE_EXISTS', 'Another fixture task is running.', 'Finish or pause it first.')
        task['paused'] = False
        pointer.write_text(args.task)
        result['handoff'] = task['handoff']
        result['check_valid'] = bool(task['check'] and task['check']['status'] == 'pass' and task['check']['objects'] == snapshot(task))
    elif op == 'valid':
        result['check_valid'] = bool(task['check'] and task['check']['status'] == 'pass' and task['check']['objects'] == snapshot(task))
        result['commits_since_base'] = git('log', '--format=%H%n%B', task['base'] + '..HEAD').strip()
    elif op == 'finish':
        if data.get('authority') != 'SIMULATED_HUMAN':
            fail('AUTHORITY_REQUIRED', 'Finish is a fixture human decision.', 'Supply explicit fixture authority.')
        if task['paused'] or not task['check'] or task['check']['status'] != 'pass' or task['check']['objects'] != snapshot(task):
            fail('CHECK_INVALID', 'No valid current Check.', 'Resume/recheck; do not reuse an obsolete pass.')
        clean_business()
        archive = root / '.wf/archive'
        archive.mkdir(exist_ok=True)
        dest = archive / path.name
        if dest.exists():
            fail('ARCHIVE_COLLISION', str(dest), 'Resolve before changing state.')
        task.update(state='archived', phase='Finish', completion='SIMULATED_NOT_PRODUCT_ACCEPTANCE')
        dest.write_text(json.dumps(task, indent=2))
        path.unlink()
        if pointer.exists() and pointer.read_text() == args.task:
            pointer.unlink()
        print(json.dumps(result))
        return 0
    elif op != 'new':
        fail('UNKNOWN_OPERATION', op, 'Use this experiment script only as documented.')
    path.write_text(json.dumps(task, indent=2))
    print(json.dumps(result))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

```

## consume.py

SHA-256: 2acf1c8643d3c9bc2de2e5e8741c19d740fce99b769967d752ff5f6632cf2daa

```python
#!/usr/bin/env python3
"""Scripted spec consumer in a fresh process, not an AI session."""
import json
import os
from pathlib import Path
import re
import sys

root = Path(sys.argv[1]).resolve()
index = (root / '.wf/spec/index.md').read_text()
selected = []
for name in re.findall(r'\[[^]]+\]\(([^)]+)\)', index):
    path = root / '.wf/spec' / name
    body = path.read_text()
    if '  - src/quantity.py' in body:
        selected.append((path, body))
assert len(selected) == 1, 'Fixture requires one unambiguous quantity contract'
path, body = selected[0]
api = re.search(r'API: ([a-z_]+)\(value\)', body).group(1)
with (root / 'src/quantity.py').open('a') as output:
    output.write('\n\ndef total_quantity(values):\n    return sum(' + api + '(value) for value in values)\n')
print(json.dumps({'pid': os.getpid(), 'selected': str(path.relative_to(root)), 'full_body': body, 'derived_api': api, 'simulation_only': True}))

```

## run_experiment.py

SHA-256: ee80674b0f5683c654b73eb9f6b31562aa21dc666d0a963c5e5298597093a9e9

```python
#!/usr/bin/env python3
"""Real subprocess/Git/business checks around a disposable control model."""
import json
import os
from pathlib import Path
import subprocess
import sys
import time

BASE = Path(__file__).resolve().parent
ROOT = BASE / 'project'
EVIDENCE = BASE / 'evidence'
ENV = dict(os.environ, PYTHONDONTWRITEBYTECODE='1')
LOG = []
RESULTS = []
HUMAN = {'authority': 'SIMULATED_HUMAN'}
PYTHON = sys.executable


def run(command, expected=0):
    begin = time.monotonic()
    p = subprocess.run(command, cwd=ROOT, env=ENV, text=True, capture_output=True)
    entry = {'command': command, 'exit': p.returncode, 'elapsed_seconds': round(time.monotonic() - begin, 6), 'stdout': p.stdout, 'stderr': p.stderr}
    LOG.append(entry)
    (EVIDENCE / 'commands.json').write_text(json.dumps(LOG, indent=2))
    if p.returncode != expected:
        raise AssertionError(json.dumps(entry, indent=2))
    return p


def git(*args):
    return run(['git', *args]).stdout.strip()


def commit(message, paths):
    git('add', '--', *paths)
    git('-c', 'user.name=WF Simulation', '-c', 'user.email=wf-simulation@example.invalid', 'commit', '-m', message)
    return git('rev-parse', 'HEAD')


def act(op, task, data=None, expected=0):
    p = run([PYTHON, str(BASE / 'control.py'), str(ROOT), op, task, '--data', json.dumps(data or {})], expected)
    return json.loads(p.stdout.strip().splitlines()[-1])


def write(path, content):
    p = ROOT / path
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content)


def append(path, content):
    with (ROOT / path).open('a') as f:
        f.write(content)


def record(name, **facts):
    RESULTS.append({'scenario': name, 'outcome': 'pass', **facts})
    (EVIDENCE / 'results.json').write_text(json.dumps(RESULTS, indent=2))
    print(name + ': PASS', flush=True)


def new(task, paths):
    act('new', task, {'paths': paths})
    act('approve', task, HUMAN)
    act('start', task)


def archive(task, paths):
    commit('fixture delivery\n\nwf-task: ' + task, paths + ['.wf/tasks/' + task + '.json'])
    act('finish', task, HUMAN)
    commit('fixture archive ' + task, ['.wf/tasks/' + task + '.json', '.wf/archive/' + task + '.json'])


# Existing-project fixture: genuine negative-value bug and real unit tests.
write('src/quantity.py', 'def validate_quantity(value):\n    return value\n')
git('init', '--initial-branch=main')
commit('fixture baseline', ['.gitignore', '.wf/baseline.md', '.wf/project-config.json', 'src/quantity.py', 'tests/test_quantity.py'])

# Emergency rejection must not mutate the task record.
act('new', 'emergency', {'paths': ['src/quantity.py']})
emergency = ROOT / '.wf/tasks/emergency.json'
before = emergency.read_bytes()
rejected = act('start', 'emergency', {'urgent': True}, expected=2)
assert rejected['reason'] == 'PLAN_UNAPPROVED' and emergency.read_bytes() == before
record('urgent-does-not-authorize', reason=rejected['reason'], unchanged=True)

# Producer K repairs an observed bug and persists its verified convention.
kpaths = ['src/quantity.py', '.wf/spec/index.md', '.wf/spec/quantity-contract.md']
new('K-producer', kpaths)
red = run([PYTHON, '-m', 'unittest', 'discover', '-s', 'tests', '-v'], expected=1)
assert 'ValueError not raised' in red.stderr
write('src/quantity.py', 'def validate_quantity(value):\n    if value < 0:\n        raise ValueError("negative_quantity")\n    return value\n')
spec = '''---
paths:
  - src/quantity.py
status: active
verified_at: 2026-10-30
schema_version: 1
author: ai
counterexample: negative input accepted without ValueError
---
# Quantity contract
API: validate_quantity(value)
Integer inventory quantities are nonnegative. Zero and positive quantities are accepted.
Negative input raises ValueError with negative_quantity. Aggregators call this validator for each value.
Good: [2, 3] -> 5. Bad: [2, -1] must raise rather than return 1.
Verified by: tests/test_quantity.py; the negative case failed before the fix and passed after it.
'''
write('.wf/spec/quantity-contract.md', spec)
write('.wf/spec/index.md', '# Spec index\n\n[Quantity contract](quantity-contract.md) — inventory validation.\n')
act('load', 'K-producer', {'session': 'producer'})
checked = act('check', 'K-producer', {'session': 'producer'})
assert checked['test_exit'] == 0
archive('K-producer', kpaths)
record('producer-red-green-archive', red_exit=red.returncode, green_exit=checked['test_exit'], spec_written=True)

# A's consumer is a separate process using only project files.
apaths = ['src/quantity.py', 'tests/test_quantity.py']
new('A-consumer', apaths)
act('load', 'A-consumer', {'session': 'initial'})
missing = act('check', 'A-consumer', {'session': 'fresh'}, expected=2)
assert missing['reason'] == 'SPEC_UNREAD'
record('fresh-session-requires-reread', reason=missing['reason'])
loaded = act('load', 'A-consumer', {'session': 'fresh'})
assert loaded['loaded'] == ['.wf/spec/quantity-contract.md']
append('tests/test_quantity.py', '''

class AggregationContract(unittest.TestCase):
    def test_empty_is_zero(self):
        from src.quantity import total_quantity
        self.assertEqual(total_quantity([]), 0)

    def test_sum_of_valid_quantities(self):
        from src.quantity import total_quantity
        self.assertEqual(total_quantity([2, 3]), 5)

    def test_aggregation_rejects_negative_quantity(self):
        from src.quantity import total_quantity
        with self.assertRaises(ValueError):
            total_quantity([2, -1])
''')
valid_source = (ROOT / 'src/quantity.py').read_text()
append('src/quantity.py', '\n\ndef total_quantity(values):\n    return sum(values)\n')
bad = act('check', 'A-consumer', {'session': 'fresh'}, expected=3)
assert bad['test_exit'] == 1 and 'ValueError not raised' in bad['test_output']
record('spec-violation-fails-business-check', test_exit=bad['test_exit'])
write('src/quantity.py', valid_source)
consumer = run([PYTHON, str(BASE / 'consume.py'), str(ROOT)])
consumer_fact = json.loads(consumer.stdout)
assert consumer_fact['selected'] == '.wf/spec/quantity-contract.md'
assert consumer_fact['derived_api'] == 'validate_quantity'
assert consumer_fact['pid'] != loaded['pid']
a_check = act('check', 'A-consumer', {'session': 'fresh'})
record('cross-task-spec-consumption', consumer_pid=consumer_fact['pid'], loader_pid=loaded['pid'], body=consumer_fact['full_body'], test_exit=a_check['test_exit'], warning='Scripted process; not a new AI session.')

# A's dirty delivery blocks pause and must remain untouched.
before = (ROOT / '.wf/tasks/A-consumer.json').read_bytes()
status_before = git('status', '--porcelain')
blocked = act('pause', 'A-consumer', {**HUMAN, 'goal': 'quantity aggregation', 'next': 'finish after insertion'}, expected=2)
assert blocked['reason'] == 'DIRTY_WORKSPACE'
assert (ROOT / '.wf/tasks/A-consumer.json').read_bytes() == before
assert git('status', '--porcelain') == status_before
record('dirty-pause-is-blocked', reason=blocked['reason'], worktree_preserved=True)
commit('fixture A checkpoint\n\nwf-task: A-consumer', apaths + ['.wf/tasks/A-consumer.json'])
act('pause', 'A-consumer', {**HUMAN, 'goal': 'quantity aggregation', 'next': 'finish after insertion'})
commit('fixture control pause A', ['.wf/tasks/A-consumer.json', '.wf/tasks/emergency.json'])

# B changes unrelated content, completes, and leaves A's Check intact.
new('B-docs', ['README.md'])
write('README.md', '# Inventory example\nQuantities are checked locally.\n')
act('check', 'B-docs', {'session': 'docs'})
archive('B-docs', ['README.md'])
no_authority = act('resume', 'A-consumer', {}, expected=2)
assert no_authority['reason'] == 'AUTHORITY_REQUIRED'
resumed = act('resume', 'A-consumer', HUMAN)
assert resumed['check_valid'] is True
record('pause-unrelated-insertion-resume', check_preserved=True, handoff=resumed['handoff'], implicit_resume_blocked=True)
act('load', 'A-consumer', {'session': 'after-docs'})

# C edits the same path under another task; old A Check is invalid.
act('pause', 'A-consumer', {**HUMAN, 'goal': 'quantity aggregation', 'next': 'recheck after same-path insertion'})
commit('fixture control pause A again', ['.wf/tasks/A-consumer.json'])
new('C-same-path', ['src/quantity.py'])
act('load', 'C-same-path', {'session': 'same-path'})
append('src/quantity.py', '\n# Shared path touched by task C; business behavior is unchanged.\n')
act('check', 'C-same-path', {'session': 'same-path'})
archive('C-same-path', ['src/quantity.py'])
resumed = act('resume', 'A-consumer', HUMAN)
assert resumed['check_valid'] is False
blocked = act('finish', 'A-consumer', HUMAN, expected=2)
assert blocked['reason'] == 'CHECK_INVALID'
record('same-path-insertion-invalidates-check', check_preserved=False, finish_blocked=blocked['reason'])
act('load', 'A-consumer', {'session': 'after-same-path'})
act('check', 'A-consumer', {'session': 'after-same-path'})

# A changed spec invalidates the earlier read receipt.
append('.wf/spec/quantity-contract.md', '\nPositive example: total_quantity([0, 3]) returns 3.\n')
commit('fixture external contract clarification', ['.wf/spec/quantity-contract.md'])
stale = act('check', 'A-consumer', {'session': 'after-same-path'}, expected=2)
assert stale['reason'] == 'SPEC_CHANGED'
record('changed-spec-requires-reread', reason=stale['reason'])
act('load', 'A-consumer', {'session': 'after-same-path'})
act('check', 'A-consumer', {'session': 'after-same-path'})

# Outside-workflow commit remains external and requires a content recheck.
append('src/quantity.py', '\n# External emergency maintenance, outside wf.\n')
external_sha = commit('fixture external emergency maintenance', ['src/quantity.py'])
assert 'wf-task:' not in git('show', '-s', '--format=%B', external_sha)
external = act('valid', 'A-consumer')
assert external['check_valid'] is False
assert external_sha in external['commits_since_base']
record('external-emergency-keeps-ownership', commit=external_sha, check_invalidated=True, inferred_task_ownership=False, manual_impact='Fixture comment-only change; no scope or acceptance change.')
act('load', 'A-consumer', {'session': 'after-external'})
act('check', 'A-consumer', {'session': 'after-external'})
archive('A-consumer', [])
assert git('status', '--porcelain') == ''
assert not (ROOT / '.wf/runtime/current').exists()
archive_names = sorted(p.name for p in (ROOT / '.wf/archive').glob('*.json'))
assert archive_names == ['A-consumer.json', 'B-docs.json', 'C-same-path.json', 'K-producer.json']
record('final-closure', archived=archive_names, worktree_clean=True, active_pointer_absent=True, planning_only_rejection='emergency remains unstarted; not completed')
run([PYTHON, '-m', 'unittest', 'discover', '-s', 'tests', '-v'])
(EVIDENCE / 'git-log.txt').write_text(git('log', '--format=%H%n%B', '--reverse'))
(EVIDENCE / 'git-status.txt').write_text(git('status', '--porcelain'))
(EVIDENCE / 'summary.json').write_text(json.dumps({'scenarios': len(RESULTS), 'commands': len(LOG), 'simulated_human_inputs': sum('SIMULATED_HUMAN' in ' '.join(e['command']) for e in LOG), 'controller_calls': sum(str(BASE / 'control.py') in e['command'] for e in LOG), 'elapsed_subprocess_seconds': round(sum(e['elapsed_seconds'] for e in LOG), 6), 'claims': 'Disposable control model plus real business tests and Git facts; no formal runtime, actual human gate or independent AI session proven.'}, indent=2))

```
